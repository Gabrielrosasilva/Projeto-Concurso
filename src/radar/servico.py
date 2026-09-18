"""Regras do sistema: rodar os coletores, gravar sem duplicar, consultar."""
import logging
import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from statistics import median

from sqlalchemy import case, func, select

from radar import avisos
from radar import (
    calendario,
    detalhes,
    edital_ieses,
    elegibilidade as leitor_de_elegibilidade,
    perfil as meu_perfil,
    macetes,
    provas,
    provas_ieses,
    questoes as leitor_de_questoes,
    questoes_ieses,
    regioes,
    substituta,
)
from radar.classificador import classificar
from radar.collectors.base import Buscador, Coletor, ItemColetado
from radar.collectors.concursos_no_brasil import MAXIMO_DE_PAGINAS, ConcursosNoBrasil
from radar.collectors.fepese import Fepese
from radar.collectors.ieses import Ieses
from radar import config
from radar.util import fuso_local
from radar.db import criar_tabelas, sessao
from radar.models import (
    Concurso,
    QuestaoDeProva,
    RespostaDeSimulado,
    Simulado,
    agora,
)

log = logging.getLogger(__name__)

# Registre aqui cada coletor novo. E o unico lugar que precisa saber a lista.
COLETORES: list[type[Coletor]] = [ConcursosNoBrasil, Fepese, Ieses]

# Campos que a coleta manda. O que NAO esta aqui e seu e nunca e sobrescrito:
# interesse, notas, e o que voce corrigir a mao no banco.
CAMPOS_DA_FONTE = (
    "titulo", "resumo", "orgao", "municipio", "uf", "banca", "situacao",
    "escolaridade", "publicado_em",
)

# O que a fonte manda quando NAO sabe. Tratado como se fosse nulo: nao
# sobrescreve o que ja descobrimos por outro caminho.
VALORES_SEM_INFORMACAO = {
    "situacao": ("desconhecida",),
}

# Campos que o classificador calcula. Sao derivados do titulo, entao podem ser
# recalculados a qualquer momento - e por isso que existe `reclassificar()`:
# se eu editar config/regioes.yml, o banco inteiro se corrige sem recoletar.
CAMPOS_CALCULADOS = ("municipio", "salario", "tipo", "relevancia", "motivo_relevancia")


def _aplicar_classificacao(destino, item: ItemColetado) -> None:
    """Aplica o que da para saber pelo TITULO, sem pisar em fonte melhor.

    Duas coisas o classificador nao encosta, porque vieram de onde se sabe
    mais: o salario que eu digitei, e o municipio que saiu da pagina do
    edital. Sem essa trava, um `radar reclassificar` desfazia o trabalho do
    `radar detalhar` - a SEFAZ SC voltava de `nucleo` para `indefinida`,
    porque "Concurso SEFAZ (SC)" nao tem municipio no titulo.
    """
    resultado = classificar(item)
    destino.tipo = resultado.tipo

    if not destino.salario_manual:
        destino.salario = resultado.salario

    if not destino.municipio_confirmado:
        destino.municipio = resultado.municipio
        destino.relevancia = resultado.relevancia
        destino.motivo_relevancia = resultado.motivo
    # O coletor marca tudo como edital_publicado porque nao sabe distinguir.
    # Se nem concurso e, nao da para afirmar que ha edital.
    if resultado.tipo == "noticia":
        destino.situacao = "desconhecida"
    elif resultado.fase and destino.inscricoes_ate is None:
        # Fase anterior ao edital, dita pelo titulo. So vale enquanto nao ha
        # prazo conhecido: data de inscricao e fato, titulo e interpretacao.
        destino.situacao = resultado.fase


@dataclass
class ResultadoColeta:
    fonte: str
    novos: int = 0
    atualizados: int = 0
    erro: str | None = None

    def __str__(self) -> str:
        if self.erro:
            return f"{self.fonte}: FALHOU ({self.erro})"
        return f"{self.fonte}: {self.novos} novo(s), {self.atualizados} atualizado(s)"


def _gravar(s, item: ItemColetado, fonte: str) -> str:
    """Insere ou atualiza um item. Devolve 'novo' ou 'atualizado'.

    A url e a chave: se ela ja existe, e o mesmo concurso e o registro e
    atualizado. O esboco antigo so pulava - e ai um concurso que mudasse de
    'inscricoes_abertas' para 'encerrado' ficava errado no banco para sempre.
    """
    existente = s.scalar(select(Concurso).where(Concurso.url == item.url))

    if existente is None:
        novo = Concurso(url=item.url, fonte=fonte, extra=item.extra or {})
        for campo in CAMPOS_DA_FONTE:
            setattr(novo, campo, getattr(item, campo))
        _aplicar_classificacao(novo, item)
        s.add(novo)
        return "novo"

    mudou = False
    for campo in CAMPOS_DA_FONTE:
        valor = getattr(item, campo)
        # None da fonte nao apaga dado que ja temos: uma coleta incompleta nao
        # pode piorar o registro. "desconhecida" na situacao e a mesma coisa -
        # e o valor padrao de quem NAO sabe, e nao pode rebaixar um status que
        # ja tinhamos descoberto por outro caminho.
        if valor is None or valor in VALORES_SEM_INFORMACAO.get(campo, ()):
            continue
        if valor == getattr(existente, campo):
            continue
        setattr(existente, campo, valor)
        mudou = True

    if item.extra and item.extra != (existente.extra or {}):
        existente.extra = {**(existente.extra or {}), **item.extra}
        mudou = True

    _aplicar_classificacao(existente, item)

    if mudou:
        existente.atualizado_em = agora()
    return "atualizado" if mudou else "sem_mudanca"


def coletar_tudo() -> list[ResultadoColeta]:
    """Roda todos os coletores.

    Se uma fonte cair ou mudar de formato, ela e registrada como erro e as
    outras seguem. Uma fonte fora do ar nunca derruba a coleta inteira.
    """
    criar_tabelas()
    resultados: list[ResultadoColeta] = []

    for classe in COLETORES:
        resultado = ResultadoColeta(fonte=classe.nome)
        try:
            itens = classe().coletar()
            with sessao() as s:
                for item in itens:
                    situacao = _gravar(s, item, classe.nome)
                    if situacao == "novo":
                        resultado.novos += 1
                    elif situacao == "atualizado":
                        resultado.atualizados += 1
        except Exception as erro:  # noqa: BLE001 - de proposito: loga e segue
            # Uma linha no log normal; o traceback inteiro so em modo debug.
            # Fonte fora do ar e rotina, nao merece 40 linhas todo dia.
            log.warning("coletor %s falhou: %s", classe.nome, erro)
            log.debug("detalhe da falha em %s", classe.nome, exc_info=True)
            resultado.erro = f"{type(erro).__name__}: {erro}"

        resultados.append(resultado)

    atualizar_situacoes()
    return resultados


def contar_por_relevancia(incluir_noticias: bool = False) -> dict[str, int]:
    """Quantos concursos em cada anel. Alimenta os atalhos da pagina web."""
    criar_tabelas()
    consulta = select(Concurso.relevancia, func.count()).group_by(Concurso.relevancia)
    if not incluir_noticias:
        consulta = consulta.where(Concurso.tipo != "noticia")

    with sessao() as s:
        contagem = dict(s.execute(consulta).all())

    # garante as quatro chaves, mesmo zeradas, para a pagina nao ter que checar
    return {anel: contagem.get(anel, 0)
            for anel in ("nucleo", "proximo", "remoto", "indefinida")}


def contar() -> int:
    """Quantos concursos existem no banco, sem filtro nenhum."""
    criar_tabelas()
    with sessao() as s:
        return s.scalar(select(func.count()).select_from(Concurso)) or 0


# O que aparece quando voce nao pede nada: o que esta perto. O resto continua
# no banco e sai com --relevancia ou --todos.
RELEVANCIA_PADRAO = ("nucleo", "proximo")


def listar(
    uf: str | None = None,
    banca: str | None = None,
    termo: str | None = None,
    situacao: str | None = None,
    relevancia: str | None = None,
    incluir_noticias: bool = False,
    todas_relevancias: bool = False,
    abertas: bool = False,
    favoritos: bool = False,
    salario_min: float | None = None,
    salario_max: float | None = None,
    limite: int = 30,
) -> list[Concurso]:
    """Consulta o que ja foi coletado, com filtros opcionais."""
    criar_tabelas()

    if abertas:
        # Ordena pelo prazo, nao pela data de publicacao: aqui o que importa
        # e o que fecha primeiro.
        consulta = select(Concurso).where(_inscricao_aberta()).order_by(
            Concurso.inscricoes_ate.asc()
        )
    elif favoritos:
        # Meus favoritos primeiro pelo que fecha antes; o que nao tem prazo
        # conhecido vai para o fim da lista, nao some.
        consulta = select(Concurso).order_by(
            Concurso.inscricoes_ate.asc().nullslast(),
            Concurso.publicado_em.desc().nullslast(),
        )
    else:
        consulta = select(Concurso).order_by(Concurso.publicado_em.desc().nullslast())

    if favoritos:
        # Favorito e escolha minha: nenhum outro filtro pode esconder um.
        # Quem eu marquei, eu vejo, mesmo que seja longe ou ganhe pouco.
        consulta = consulta.where(Concurso.interesse == FAVORITO)
        with sessao() as s:
            return list(s.scalars(consulta.limit(limite)))

    if salario_min is not None or salario_max is not None:
        # Filtro filtra: quem nao tem salario conhecido fica de fora.
        #
        # A primeira versao deixava os sem valor passarem, para nao esconder
        # concurso bom - mas 1.115 dos 2.185 nao trazem salario no titulo, e o
        # resultado era um filtro que nao filtrava nada. Quem usa precisa
        # saber do ponto cego, e nao adivinhar: a tela avisa quantos ficaram
        # de fora por falta de valor, e `contar_sem_salario` da esse numero.
        consulta = consulta.where(Concurso.salario.is_not(None))
        if salario_min is not None:
            consulta = consulta.where(Concurso.salario >= salario_min)
        if salario_max is not None:
            consulta = consulta.where(Concurso.salario <= salario_max)
        consulta = consulta.order_by(None).order_by(Concurso.salario.desc())

    # Noticia que veio junto no feed nao e concurso: fica de fora por padrao.
    if not incluir_noticias:
        consulta = consulta.where(Concurso.tipo != "noticia")

    if relevancia:
        consulta = consulta.where(Concurso.relevancia == relevancia)
    elif not todas_relevancias:
        consulta = consulta.where(Concurso.relevancia.in_(RELEVANCIA_PADRAO))

    if uf:
        consulta = consulta.where(Concurso.uf == uf.upper())
    if banca:
        # Aceita o nome curto e o por extenso: quem digita "Fundacao Carlos
        # Chagas" quer os mesmos concursos de quem digita "FCC".
        nomes = expandir_banca(banca)
        if nomes:
            consulta = consulta.where(
                Concurso.banca.in_(nomes) | Concurso.banca.ilike(f"%{banca}%")
            )
        else:
            consulta = consulta.where(Concurso.banca.ilike(f"%{banca}%"))
    if situacao:
        consulta = consulta.where(Concurso.situacao == situacao)
    if termo:
        # Busca ignorando acento: quem digita no campo raramente poe cedilha,
        # e "Palhoca" precisa achar "Palhoca" acentuada.
        procurado = f"%{_sem_acento(termo)}%"
        sem_acento_sql = func.sem_acento
        consulta = consulta.where(
            sem_acento_sql(Concurso.titulo).ilike(procurado)
            | sem_acento_sql(func.coalesce(Concurso.resumo, "")).ilike(procurado)
            | sem_acento_sql(func.coalesce(Concurso.municipio, "")).ilike(procurado)
        )

    with sessao() as s:
        return list(s.scalars(consulta.limit(limite)))


def reclassificar() -> dict[str, int]:
    """Roda o classificador de novo em todo o banco, sem ir a internet.

    Use depois de editar config/regioes.yml: os registros antigos passam a
    respeitar a regra nova na hora.
    """
    criar_tabelas()
    contagem: dict[str, int] = {}

    with sessao() as s:
        for concurso in s.scalars(select(Concurso)):
            item = ItemColetado(
                titulo=concurso.titulo,
                url=concurso.url,
                resumo=concurso.resumo,
                uf=concurso.uf,
                # O municipio e o tipo ja conhecidos vao junto. Sem eles, os
                # concursos da FEPESE perdiam o municipio a cada reclassificar:
                # o titulo dela e "2026 - Prefeitura Municipal de Sao Jose",
                # sem "(SC)", e o extrator do classificador precisa da UF entre
                # parenteses. "Perto de mim" caia de 176 para 69.
                #
                # Reclassificar existe para reaplicar a regra do ANEL, e nao
                # para reextrair o que outra fonte ja extraiu melhor.
                municipio=concurso.municipio,
                tipo=concurso.tipo if concurso.tipo != "desconhecido" else None,
            )
            _aplicar_classificacao(concurso, item)

            # Grafia canonica mesmo no municipio confirmado pela pagina do
            # edital: trocar "Palhoca" por "Palhoca" com cedilha nao e
            # reclassificar, e escrever o mesmo municipio de um jeito so.
            concurso.municipio = regioes.nome_canonico(concurso.municipio)

            contagem[concurso.relevancia] = contagem.get(concurso.relevancia, 0) + 1

    return contagem


# --- avisos (fase 2) --------------------------------------------------------

# O que merece uma mensagem no celular. `indefinida` entra de proposito: e o
# concurso federal ou sem UF, que PODE aplicar prova em Florianopolis. Melhor
# receber dois avisos a toa do que perder o unico que interessava.
RELEVANCIA_AVISO = ("nucleo", "proximo", "indefinida")

# Teto de mensagens por coleta. Nao e economia: e protecao. Se uma regra de
# classificacao quebrar, o estrago fica em 10 mensagens e um alerta, em vez de
# 200 notificacoes as 6h da manha.
LIMITE_DE_AVISOS = 10


@dataclass
class ResultadoAviso:
    enviados: int = 0
    pendentes: int = 0     # passaram no filtro mas ficaram fora do limite
    configurado: bool = True

    def __str__(self) -> str:
        if not self.configurado:
            return "Telegram nao configurado: nenhum aviso enviado."
        if not self.enviados and not self.pendentes:
            return "Nada novo para avisar."
        texto = f"{self.enviados} aviso(s) enviado(s)"
        if self.pendentes:
            texto += f", {self.pendentes} acima do limite"
        return texto


# Aviso e sobre NOVIDADE. Sem esta janela, ligar uma fonte nova enche a fila
# com o historico inteiro dela: a FEPESE entrou com 520 concursos, 464 deles ja
# encerrados, e o `radar avisar` seguinte mandaria mensagem sobre edital de
# anos atras mais o alerta de excesso, que soaria como erro de regra sem ser.
JANELA_DE_NOVIDADE_EM_DIAS = 30


def _e_novidade():
    """Condicao SQL de "isto merece uma mensagem no celular agora".

    Vale se foi publicado ha pouco, ou se a inscricao continua aberta - um
    edital de 40 dias atras com prazo em pe ainda e util. Nunca vale se ja
    encerrou. Sem data de publicacao entra, porque ai nao da para afirmar que
    e velho, e o teto de 10 mensagens segura o estrago.
    """
    recente = agora() - timedelta(days=JANELA_DE_NOVIDADE_EM_DIAS)
    return (Concurso.situacao != "encerrado") & (
        # a banca diz que da para se inscrever agora: isso basta, e a data de
        # publicacao nao importa. Foi assim que o concurso da Celesc quase
        # passou batido - aberto, mas publicado ha mais de 30 dias, e a FEPESE
        # nao informa prazo.
        (Concurso.situacao == "inscricoes_abertas")
        | Concurso.publicado_em.is_(None)
        | (Concurso.publicado_em >= recente)
        | (Concurso.inscricoes_ate >= agora())
    )


def _nao_avisados() -> list[Concurso]:
    """Concursos que interessam e que ainda nao viraram mensagem."""
    consulta = (
        select(Concurso)
        .where(Concurso.avisado_em.is_(None))
        .where(Concurso.tipo != "noticia")
        .where(Concurso.relevancia.in_(RELEVANCIA_AVISO))
        .where(_e_novidade())
        .order_by(Concurso.publicado_em.desc().nullslast())
    )
    with sessao() as s:
        return list(s.scalars(consulta))


def avisar(limite: int = LIMITE_DE_AVISOS) -> ResultadoAviso:
    """Manda no Telegram os concursos novos que interessam.

    Cada concurso vira uma mensagem e e marcado como avisado, para a coleta de
    amanha nao repetir o aviso de hoje.
    """
    criar_tabelas()

    if not config.telegram_configurado():
        return ResultadoAviso(configurado=False)

    candidatos = _nao_avisados()
    if not candidatos:
        return ResultadoAviso()

    escolhidos = candidatos[:limite]
    sobraram = len(candidatos) - len(escolhidos)

    enviados = avisos.enviar_varios([avisos.formatar(c) for c in escolhidos])

    # So marca como avisado o que realmente saiu. Se o Telegram estava fora do
    # ar, o concurso continua pendente e a proxima coleta tenta de novo.
    if enviados:
        urls = [c.url for c in escolhidos[:enviados]]
        with sessao() as s:
            for concurso in s.scalars(select(Concurso).where(Concurso.url.in_(urls))):
                concurso.avisado_em = agora()

    if sobraram:
        avisos.enviar(
            f"⚠️ Mais {sobraram} concurso(s) passaram no filtro nesta "
            f"coleta.\n\nIsso costuma indicar erro de regra de "
            f"classificacao. Veja todos com <code>radar listar --todos</code>."
        )

    return ResultadoAviso(enviados=enviados, pendentes=sobraram)


# --- carga inicial (fase 1.6) -----------------------------------------------

# Medido no site real em 17/09/2026: 15 itens por pagina, e paged=60 chegou a
# 37 dias atras - cerca de 1,6 pagina por dia. Usamos 3 por dia, que da o
# dobro de folga caso o site publique mais num periodo movimentado. Quem manda
# de verdade na parada e a data; isto aqui e so o teto.
PAGINAS_POR_DIA = 3


def _marcar_historico_como_avisado() -> int:
    """Encerra a fila de avisos depois da carga inicial.

    Sem isto, trazer 90 dias de historico enche a fila com centenas de
    concursos antigos, e o `radar avisar` seguinte manda 10 mensagens sobre
    editais de junho - a maioria com inscricao ja encerrada - mais o alerta de
    excesso, que soaria como erro de regra sem ser.

    Carga inicial e historico, nao novidade: quem chega por ela se ve na
    pagina e na lista. A partir daqui, so a coleta diaria gera aviso.
    """
    consulta = select(Concurso).where(Concurso.avisado_em.is_(None))
    marcados = 0
    with sessao() as s:
        for concurso in s.scalars(consulta):
            concurso.avisado_em = agora()
            marcados += 1
    return marcados


def carga_inicial(dias: int = 90) -> ResultadoColeta:
    """Anda para tras no feed e traz o historico que a coleta diaria perdeu.

    O RSS e um fluxo: ele so mostra o que e recente. Quem liga o radar hoje ve
    os concursos de hoje, e nada do que foi publicado antes. Esta funcao
    resolve isso uma vez, lendo o feed pagina por pagina.

    Roda uma vez so, na mao. Nao entra na coleta diaria.
    """
    criar_tabelas()

    desde = agora() - timedelta(days=dias)
    paginas = min(dias * PAGINAS_POR_DIA, MAXIMO_DE_PAGINAS)

    resultado = ResultadoColeta(fonte=ConcursosNoBrasil.nome)
    try:
        itens = ConcursosNoBrasil(paginas=paginas, desde=desde).coletar()
        with sessao() as s:
            for item in itens:
                situacao = _gravar(s, item, ConcursosNoBrasil.nome)
                if situacao == "novo":
                    resultado.novos += 1
                elif situacao == "atualizado":
                    resultado.atualizados += 1

        _marcar_historico_como_avisado()
    except Exception as erro:  # noqa: BLE001 - de proposito: loga e segue
        log.warning("carga inicial falhou: %s", erro)
        log.debug("detalhe da falha na carga inicial", exc_info=True)
        resultado.erro = f"{type(erro).__name__}: {erro}"

    return resultado


# --- inscricoes abertas (fase 2.5) ------------------------------------------

def _inscricao_aberta():
    """Condicao SQL de "da para se inscrever hoje".

    Exige `inscricoes_ate` preenchido: sem prazo conhecido nao da para afirmar
    que esta aberto. O comeco e opcional - se eu sei que fecha dia 30 mas nao
    sei quando abriu, ainda assim vale mostrar.
    """
    hoje = agora()
    return (
        Concurso.inscricoes_ate.is_not(None)
        & (Concurso.inscricoes_ate >= hoje)
        & (Concurso.inscricoes_de.is_(None) | (Concurso.inscricoes_de <= hoje))
        & (Concurso.tipo != "noticia")
    )


def contar_abertas() -> int:
    criar_tabelas()
    with sessao() as s:
        return s.scalar(
            select(func.count()).select_from(Concurso).where(_inscricao_aberta())
        ) or 0


# --- leitura da pagina de detalhe -------------------------------------------

# Ordem de prioridade para gastar requisicao. Ler a pagina de todos os 2.200
# levaria quase uma hora e nao serviria para nada: 1.400 sao de outro estado.
PRIORIDADE_DETALHE = (
    # 1. o que ja sei que esta perto
    lambda: Concurso.relevancia.in_(("nucleo", "proximo")),
    # 2. concurso de SC que ficou indefinido - e aqui que mora o caso da
    #    SEFAZ SC: orgao estadual nao tem "Prefeitura de X" no titulo, entao
    #    o classificador nao acha municipio e marca indefinida
    lambda: (Concurso.relevancia == "indefinida") & (Concurso.uf == "SC"),
    # 3. federal ou nacional: pode aplicar prova em Florianopolis
    lambda: (Concurso.relevancia == "indefinida") & Concurso.uf.is_(None),
)


@dataclass
class ResultadoDetalhe:
    lidos: int = 0
    com_prazo: int = 0
    com_banca: int = 0
    reclassificados: int = 0
    erros: int = 0

    def __str__(self) -> str:
        if not self.lidos:
            return "Nada novo para detalhar."
        texto = (
            f"{self.lidos} pagina(s) lida(s): {self.com_prazo} com prazo de "
            f"inscricao, {self.com_banca} com banca"
        )
        if self.reclassificados:
            texto += f", {self.reclassificados} mudaram de anel"
        if self.erros:
            texto += f", {self.erros} falharam"
        return texto


def _pendentes_de_detalhe(limite: int) -> list[Concurso]:
    """Quem ainda nao teve a pagina lida, na ordem de prioridade."""
    escolhidos: list[Concurso] = []
    vistos: set[int] = set()

    with sessao() as s:
        for condicao in PRIORIDADE_DETALHE:
            if len(escolhidos) >= limite:
                break
            consulta = (
                select(Concurso)
                .where(Concurso.detalhado_em.is_(None))
                .where(Concurso.tipo != "noticia")
                .where(condicao())
                .order_by(Concurso.publicado_em.desc().nullslast())
                .limit(limite - len(escolhidos))
            )
            for concurso in s.scalars(consulta):
                if concurso.id not in vistos:
                    vistos.add(concurso.id)
                    escolhidos.append(concurso)

    return escolhidos


def detalhar_pendentes(limite: int = 150) -> ResultadoDetalhe:
    """Le a pagina de cada concurso que interessa e completa o registro.

    Traz prazo de inscricao, banca e - quando a pagina deixa claro - o
    municipio de lotacao. O municipio novo faz o registro ser reclassificado,
    que e como um concurso estadual sai de `indefinida` para `nucleo`.
    """
    criar_tabelas()
    resultado = ResultadoDetalhe()

    pendentes = _pendentes_de_detalhe(limite)
    if not pendentes:
        return resultado

    municipios = regioes.nomes_originais()
    buscador = Buscador()

    for pendente in pendentes:
        try:
            html = buscador.get(pendente.url).text
        except Exception as erro:  # noqa: BLE001 - pagina fora do ar e rotina
            log.warning("nao consegui ler %s: %s", pendente.url, type(erro).__name__)
            resultado.erros += 1
            continue

        ano = pendente.publicado_em.year if pendente.publicado_em else agora().year
        achado = detalhes.extrair(html, ano, municipios)
        resultado.lidos += 1

        with sessao() as s:
            concurso = s.get(Concurso, pendente.id)
            concurso.detalhado_em = agora()

            if achado.inscricoes_ate:
                concurso.inscricoes_de = achado.inscricoes_de
                concurso.inscricoes_ate = achado.inscricoes_ate
                resultado.com_prazo += 1
            if achado.banca and not concurso.banca:
                concurso.banca = achado.banca
                resultado.com_banca += 1
            if achado.hotsite and not _hotsite(concurso):
                # E o que liga o concurso ao acervo: sem hotsite, quem vem do
                # feed de noticias nunca rende edital nem prova.
                extra = dict(concurso.extra or {})
                extra["hotsite"] = achado.hotsite
                concurso.extra = extra

            # Municipio novo muda o anel: e o caminho da SEFAZ SC sair de
            # indefinida para nucleo.
            if achado.municipio and not concurso.municipio:
                anel_antes = concurso.relevancia
                concurso.municipio = regioes.nome_canonico(achado.municipio)
                # veio da pagina, que e fonte melhor que o titulo
                concurso.municipio_confirmado = True
                anel = regioes.anel_de(achado.municipio)
                if anel:
                    concurso.relevancia = anel
                    concurso.motivo_relevancia = (
                        f"{achado.municipio} aparece como lotacao na pagina do "
                        f"edital, e esta no anel {anel}."
                    )
                if concurso.relevancia != anel_antes:
                    resultado.reclassificados += 1

    atualizar_situacoes()
    return resultado


def expandir_banca(termo: str) -> list[str]:
    """Os nomes de banca que casam com o que foi digitado.

    Banca tem nome curto e nome por extenso, e quem busca usa qualquer um dos
    dois: "FCC" e "Fundacao Carlos Chagas" sao a mesma coisa. A tabela de
    apelidos ja existia em `detalhes.BANCAS`, usada para reconhecer a banca na
    pagina do edital; aqui ela serve ao contrario.
    """
    procurado = _sem_acento(termo).strip().lower()
    if not procurado:
        return []

    achados = [
        nome for nome, apelidos in detalhes.BANCAS.items()
        if procurado in _sem_acento(nome).lower()
        or any(procurado in apelido or apelido.strip() in procurado
               for apelido in apelidos)
    ]
    return achados


def _sem_acento(texto: str) -> str:
    import unicodedata

    normal = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in normal if not unicodedata.combining(c))


# --- favoritos (fase 1.55) --------------------------------------------------

# A coluna `interesse` e minha, nao da fonte: a coleta nunca a sobrescreve.
FAVORITO = "favorito"


def favoritar(concurso_id: int, favorito: bool = True) -> Concurso | None:
    """Marca ou desmarca um concurso como favorito."""
    criar_tabelas()
    with sessao() as s:
        concurso = s.get(Concurso, concurso_id)
        if concurso is None:
            return None
        concurso.interesse = FAVORITO if favorito else None
        return concurso


def alternar_favorito(concurso_id: int) -> Concurso | None:
    """Favorita se nao for, desfavorita se for. E o que o botao da tela faz."""
    criar_tabelas()
    with sessao() as s:
        concurso = s.get(Concurso, concurso_id)
        if concurso is None:
            return None
        concurso.interesse = None if concurso.interesse == FAVORITO else FAVORITO
        return concurso


def contar_sem_salario() -> int:
    """Quantos concursos nao trazem salario no titulo.

    E o ponto cego do filtro de remuneracao, e a tela mostra este numero para
    eu saber o tamanho do que estou deixando de ver.
    """
    criar_tabelas()
    with sessao() as s:
        return s.scalar(
            select(func.count()).select_from(Concurso)
            .where(Concurso.salario.is_(None))
            .where(Concurso.tipo != "noticia")
        ) or 0


def contar_favoritos() -> int:
    criar_tabelas()
    with sessao() as s:
        return s.scalar(
            select(func.count()).select_from(Concurso)
            .where(Concurso.interesse == FAVORITO)
        ) or 0


# --- status derivado das datas ----------------------------------------------

def _situacao_pelas_datas(concurso: Concurso, momento) -> str | None:
    """A situacao que as datas de inscricao permitem afirmar.

    Antes disto, TODO registro ficava como `edital_publicado`, porque e o
    unico palpite que o titulo permite - ou seja, o campo nao dizia nada. Com
    o prazo em maos da para ser preciso, e sem chutar: so mexe em quem tem
    data, e so entre os tres estados que a data comprova.
    """
    if concurso.tipo == "noticia" or concurso.inscricoes_ate is None:
        return None
    if momento > concurso.inscricoes_ate:
        return "encerrado"
    if concurso.inscricoes_de is None or momento >= concurso.inscricoes_de:
        return "inscricoes_abertas"
    return "edital_publicado"          # edital saiu, inscricao ainda vai abrir


def atualizar_situacoes() -> dict[str, int]:
    """Recalcula a situacao de quem tem prazo conhecido.

    Roda sozinho ao fim da coleta e do `detalhar`, e de novo quando eu chamo
    na mao - porque o tempo passa e "aberto" vira "encerrado" sem ninguem
    tocar em nada.
    """
    criar_tabelas()
    momento = agora()
    contagem: dict[str, int] = {}

    with sessao() as s:
        consulta = select(Concurso).where(Concurso.inscricoes_ate.is_not(None))
        for concurso in s.scalars(consulta):
            nova = _situacao_pelas_datas(concurso, momento)
            if nova and nova != concurso.situacao:
                concurso.situacao = nova
                contagem[nova] = contagem.get(nova, 0) + 1

    return contagem


def definir_notas(concurso_id: int, texto: str | None) -> Concurso | None:
    """Grava a minha anotacao sobre o concurso.

    Este campo e MEU: a coleta nunca o sobrescreve, como acontece com
    `interesse`. E onde fica o que nenhuma fonte sabe - "conversei com quem
    fez em 2022", "prova cai no mesmo dia da outra", "conferir se aceita
    Sistemas de Informacao".
    """
    criar_tabelas()
    limpo = (texto or "").strip()
    with sessao() as s:
        concurso = s.get(Concurso, concurso_id)
        if concurso is None:
            return None
        concurso.notas = limpo or None
        return concurso


def definir_salario(concurso_id: int, valor: float | None) -> Concurso | None:
    """Grava o salario que eu digitei, e trava contra a proxima coleta.

    Existe porque 1.115 dos 2.185 concursos nao trazem valor no titulo. Sem
    isto, eles ficariam para sempre sem remuneracao conhecida e fora do filtro
    - inclusive os bons, como o de 300 vagas de Sao Jose.

    Passar None limpa o valor e devolve o campo ao classificador.
    """
    criar_tabelas()
    with sessao() as s:
        concurso = s.get(Concurso, concurso_id)
        if concurso is None:
            return None
        concurso.salario = valor
        concurso.salario_manual = valor is not None
        return concurso


# --- acervo de provas (fase 3) ----------------------------------------------

# Cada hotsite da FEPESE tem estas duas paginas, e e so o que precisamos ler.
PAGINAS_DO_HOTSITE = ("provas", "edital")


@dataclass
class ResultadoAcervo:
    concursos: int = 0
    provas: int = 0
    gabaritos: int = 0
    editais: int = 0
    falhas: int = 0

    @property
    def documentos(self) -> int:
        return self.provas + self.gabaritos + self.editais

    def __str__(self) -> str:
        if not self.concursos:
            return "Nada novo para o acervo."
        return (
            f"{self.concursos} concurso(s) lido(s): {self.provas} prova(s), "
            f"{self.gabaritos} gabarito(s), {self.editais} edital(is)"
            + (f", {self.falhas} falha(s)" if self.falhas else "")
        )


def _ano_do_concurso(concurso: Concurso) -> int | None:
    # o titulo da FEPESE comeca com o ano: "2024 - Prefeitura Municipal de..."
    achado = re.match(r"\s*(\d{4})", concurso.titulo or "")
    if achado:
        return int(achado.group(1))
    return concurso.publicado_em.year if concurso.publicado_em else None


def _hotsite(concurso: Concurso) -> str | None:
    """Onde a banca publica os documentos daquele concurso.

    A FEPESE guarda o endereco num campo a parte; na IESES a propria url do
    concurso JA e o hotsite.
    """
    if concurso.fonte == "ieses":
        return concurso.url
    return (concurso.extra or {}).get("hotsite")


# De que fontes da para montar acervo hoje. Cada uma publica os PDFs de um
# jeito, e por isso a leitura da pagina e por banca.
FONTES_COM_ACERVO = ("fepese", "ieses")


# Ordem de prioridade para gastar requisicao. Prova de concurso encerrado perto
# de casa vale mais que qualquer outra: e o padrao da banca na minha regiao.
PRIORIDADE_ACERVO = (
    lambda: Concurso.relevancia.in_(("nucleo", "proximo")),
    lambda: Concurso.relevancia == "indefinida",
)


def _concursos_com_prova(limite: int, abertos: bool = False) -> list[Concurso]:
    """Quem ainda nao esta no acervo, na ordem de prioridade.

    O manifesto e a memoria: concurso cuja url ja aparece la nao e lido de
    novo. Assim nao precisa de coluna no banco so para marcar isso.
    """
    ja_no_acervo = {r.get("concurso_url") for r in provas.carregar_manifesto()}

    escolhidos: list[Concurso] = []
    with sessao() as s:
        for condicao in PRIORIDADE_ACERVO:
            if len(escolhidos) >= limite:
                break
            consulta = (
                select(Concurso)
                .where(Concurso.fonte.in_(FONTES_COM_ACERVO))
                # So concurso ja realizado tem prova publicada. A IESES nao
                # informa status nenhum, entao para ela vale a data: o hotsite
                # de quem ja fez a prova traz os cadernos, e o de quem nao fez
                # ainda simplesmente nao rende documento.
                .where(
                    (Concurso.situacao == "encerrado")
                    | (Concurso.fonte == "ieses")
                    # Concurso que ainda nao aconteceu nao tem prova, mas TEM
                    # edital - e o edital e o que diz se eu posso prestar.
                    | (abertos and Concurso.situacao != "encerrado")
                )
                .where(condicao())
                .order_by(Concurso.publicado_em.desc().nullslast())
            )
            for concurso in s.scalars(consulta):
                if len(escolhidos) >= limite:
                    break
                if concurso.url in ja_no_acervo or not _hotsite(concurso):
                    continue
                escolhidos.append(concurso)

    return escolhidos


def _documentos_do_hotsite(
    concurso: Concurso, hotsite: str, buscador, resultado
) -> list[provas.Documento]:
    """Os PDFs que o hotsite oferece. Cada banca publica de um jeito.

    A FEPESE tem uma pagina por assunto (`?go=provas`, `?go=edital`); a IESES
    poe tudo numa pagina so, com os arquivos num CDN.
    """
    encontrados: list[provas.Documento] = []

    if concurso.fonte == "ieses":
        try:
            html = buscador.get(hotsite + "/").text
        except Exception as erro:  # noqa: BLE001 - hotsite fora do ar e rotina
            # Medido: 10 dos 26 hotsites da IESES ja sairam do ar, quase todos
            # de 2023 para tras. Falhar um nao pode parar os outros.
            log.warning("hotsite %s: %s", hotsite, type(erro).__name__)
            resultado.falhas += 1
            return []
        return provas_ieses.ler_hotsite(html, hotsite + "/")

    for pagina in PAGINAS_DO_HOTSITE:
        try:
            html = buscador.get(f"{hotsite}/?go={pagina}&edital=1").text
        except Exception as erro:  # noqa: BLE001 - hotsite fora do ar e rotina
            log.warning("hotsite %s, pagina %s: %s", hotsite, pagina,
                        type(erro).__name__)
            resultado.falhas += 1
            continue

        leitor = (provas.ler_pagina_de_provas if pagina == "provas"
                  else provas.ler_pagina_de_edital)
        encontrados.extend(leitor(html, hotsite + "/"))

    return encontrados


def montar_acervo(limite: int = 20, abertos: bool = False) -> ResultadoAcervo:
    """Le os hotsites e baixa edital, prova e gabarito.

    Uma requisicao por pagina do hotsite e uma por PDF, todas com a pausa da
    classe Coletor. Por isso o limite: ler os 520 concursos de uma vez levaria
    horas e a maior parte nao interessa.
    """
    criar_tabelas()
    resultado = ResultadoAcervo()

    escolhidos = _concursos_com_prova(limite, abertos)
    if not escolhidos:
        return resultado

    registros = provas.carregar_manifesto()
    conhecidos = {r.get("url") for r in registros}
    buscador = Buscador()

    for concurso in escolhidos:
        hotsite = _hotsite(concurso).rstrip("/")
        encontrados = _documentos_do_hotsite(concurso, hotsite, buscador, resultado)
        resultado.concursos += 1

        for documento in encontrados:
            if documento.url in conhecidos:
                continue

            documento.concurso_url = concurso.url
            documento.banca = concurso.banca or "FEPESE"
            documento.orgao = concurso.orgao or concurso.titulo
            documento.municipio = concurso.municipio
            documento.ano = _ano_do_concurso(concurso)

            baixado = provas.baixar(documento, buscador)
            if baixado is None:
                resultado.falhas += 1
                continue

            registros.append(provas.para_registro(baixado))
            conhecidos.add(baixado.url)

            if baixado.tipo == provas.PROVA:
                resultado.provas += 1
            elif baixado.tipo == provas.GABARITO:
                resultado.gabaritos += 1
            else:
                resultado.editais += 1

        # Grava a cada concurso, e nao so no fim. O comando leva minutos: se
        # ele for interrompido no meio - Ctrl+C, queda de rede, maquina
        # desligando - o que ja foi baixado fica catalogado, e a proxima
        # rodada continua de onde parou em vez de recomecar.
        provas.gravar_manifesto(registros)

    return resultado


def baixar_do_manifesto(forcar: bool = False) -> dict[str, int]:
    """Reconstroi o acervo em disco a partir do manifesto versionado.

    E o que torna os PDFs descartaveis: eles nao vao para o git, mas qualquer
    maquina refaz a pasta inteira a partir do JSON.
    """
    registros = provas.carregar_manifesto()
    if not registros:
        return {"total": 0, "baixados": 0, "ja_tinha": 0, "falhas": 0}

    buscador = Buscador()
    contagem = {"total": len(registros), "baixados": 0, "ja_tinha": 0, "falhas": 0}

    for registro in registros:
        documento = provas.Documento(**{
            campo: registro.get(campo)
            for campo in ("tipo", "url", "arquivo", "cargo", "concurso_url",
                          "banca", "orgao", "municipio", "ano")
        })
        caminho = provas.destino(documento)
        if caminho.exists() and not forcar:
            contagem["ja_tinha"] += 1
            continue

        if provas.baixar(documento, buscador, forcar=forcar):
            contagem["baixados"] += 1
        else:
            contagem["falhas"] += 1

    return contagem


# --- padrao da banca (fase 4) -----------------------------------------------

@dataclass
class ResultadoExtracao:
    provas: int = 0
    questoes: int = 0
    atualizadas: int = 0
    repetidas: int = 0
    vazias: int = 0

    def __str__(self) -> str:
        if not self.provas:
            return "Nenhuma prova nova para ler."
        texto = f"{self.provas} prova(s) lida(s), {self.questoes} questao(oes)"
        if self.atualizadas:
            texto += f", {self.atualizadas} atualizada(s)"
        if self.repetidas:
            texto += f", {self.repetidas} ja vista(s) em outra prova"
        if self.vazias:
            texto += f", {self.vazias} sem questao"
        return texto


def _provas_por_ler(limite: int, refazer: bool = False) -> list[dict]:
    """Provas do manifesto que ainda nao viraram questao no banco.

    Com `refazer`, devolve todas de novo: e o que permite passar um parser
    melhorado por cima do acervo inteiro.
    """
    with sessao() as s:
        ja_lidas = (
            set() if refazer
            else set(s.scalars(select(QuestaoDeProva.prova_url).distinct()))
        )

    pendentes = [
        registro for registro in provas.carregar_manifesto()
        if registro.get("tipo") == provas.PROVA
        and registro.get("caminho")
        and registro["url"] not in ja_lidas
    ]
    return pendentes[:limite]


def _companheiros(registro: dict) -> tuple[dict | None, dict | None]:
    """O gabarito e o edital do mesmo concurso que este caderno.

    So a IESES precisa dos dois: la o gabarito e um PDF a parte, e a materia de
    cada questao vem do edital. O caderno da FEPESE traz as duas coisas dentro.
    """
    do_concurso = [
        r for r in provas.carregar_manifesto()
        if r.get("concurso_url") == registro.get("concurso_url")
    ]
    # O codigo do cargo e o mesmo nos dois arquivos: prova-1016, gabarito-1016.
    codigo = Path(registro.get("arquivo", "")).stem.split("_")[-1]

    gabarito = next(
        (r for r in do_concurso
         if r.get("tipo") == provas.GABARITO
         and Path(r.get("arquivo", "")).stem.split("_")[-1] == codigo),
        None,
    )
    edital = next((r for r in do_concurso if r.get("tipo") == provas.EDITAL), None)
    return gabarito, edital


def _caminho(registro: dict | None) -> Path | None:
    if not registro or not registro.get("caminho"):
        return None
    caminho = config.diretorio_dados() / registro["caminho"]
    return caminho if caminho.exists() else None


def _ler_caderno(registro: dict, caminho: Path) -> list:
    """As questoes de um caderno. Cada banca imprime o dela de um jeito."""
    if (registro.get("banca") or "").upper() != "IESES":
        return leitor_de_questoes.ler_prova(caminho)

    gabarito_registro, edital_registro = _companheiros(registro)

    gabarito = {}
    caminho_gabarito = _caminho(gabarito_registro)
    if caminho_gabarito:
        gabarito = questoes_ieses.ler_gabarito(caminho_gabarito)

    texto_do_caderno = leitor_de_questoes.extrair_texto(caminho)
    lidas = questoes_ieses.dividir_em_questoes(texto_do_caderno, gabarito=gabarito)

    caminho_edital = _caminho(edital_registro)
    codigo, _ = questoes_ieses.codigo_e_cargo(texto_do_caderno)
    if caminho_edital and codigo and lidas:
        # Quantas questoes o caderno tem importa: o que passa das materias
        # listadas no edital e Conhecimentos Especificos.
        materias = edital_ieses.materias_do_cargo(
            leitor_de_questoes.extrair_texto(caminho_edital),
            codigo,
            max(q.numero for q in lidas),
        )
        for questao in lidas:
            questao.materia = materias.get(questao.numero)

    return lidas


def extrair_questoes(limite: int = 30, refazer: bool = False) -> ResultadoExtracao:
    """Le os cadernos do acervo e guarda as questoes.

    Nao vai a internet: trabalha em cima dos PDFs que `radar provas` ja baixou.
    """
    criar_tabelas()
    resultado = ResultadoExtracao()

    pendentes = _provas_por_ler(limite, refazer)
    if not pendentes:
        return resultado

    # "Repetida" e a questao que a banca reaproveitou de outra prova. Refazendo
    # o acervo inteiro, o banco ja tem todas: comparar com ele acusaria as 5021
    # como repetidas de si mesmas. Ai a conta e so entre as provas da rodada.
    conhecidas: set[str] | None = set() if refazer else None

    for registro in pendentes:
        caminho = config.diretorio_dados() / registro["caminho"]
        if not caminho.exists():
            continue

        lidas = _ler_caderno(registro, caminho)
        resultado.provas += 1
        if not lidas:
            resultado.vazias += 1
            continue

        with sessao() as s:
            if conhecidas is None:
                conhecidas = set(s.scalars(select(QuestaoDeProva.impressao)))

            for questao in lidas:
                if questao.impressao in conhecidas:
                    resultado.repetidas += 1
                conhecidas.add(questao.impressao)

                # Upsert pela chave natural (prova_url, numero). Apagar e
                # gravar de novo seria mais simples, mas o simulado guarda o id
                # da questao: o historico ficaria apontando para o nada.
                existente = s.scalar(
                    select(QuestaoDeProva)
                    .where(QuestaoDeProva.prova_url == registro["url"])
                    .where(QuestaoDeProva.numero == questao.numero)
                )
                destino = existente or QuestaoDeProva(
                    prova_url=registro["url"], numero=questao.numero
                )
                destino.concurso_url = registro.get("concurso_url")
                destino.banca = registro.get("banca")
                destino.ano = registro.get("ano")
                destino.municipio = registro.get("municipio")
                destino.cargo = registro.get("cargo")
                destino.materia = questao.materia
                destino.enunciado = questao.enunciado
                destino.alternativas = questao.alternativas
                destino.resposta = questao.resposta
                destino.impressao = questao.impressao

                if existente is None:
                    s.add(destino)
                    resultado.questoes += 1
                else:
                    resultado.atualizadas += 1

    return resultado


def incidencia_por_materia(
    cargo: str | None = None, banca: str | None = None, ano: int | None = None
) -> list[tuple[str, int]]:
    """Quantas questoes de cada materia, da mais cobrada para a menos.

    E a resposta para "o que a banca mais cobra", que e o motivo de o acervo
    existir.
    """
    criar_tabelas()
    consulta = (
        select(QuestaoDeProva.materia, func.count())
        .group_by(QuestaoDeProva.materia)
        .order_by(func.count().desc())
    )
    if cargo:
        consulta = consulta.where(QuestaoDeProva.cargo.ilike(f"%{cargo}%"))
    if banca:
        consulta = consulta.where(QuestaoDeProva.banca.ilike(f"%{banca}%"))
    if ano:
        consulta = consulta.where(QuestaoDeProva.ano == ano)

    with sessao() as s:
        return [(materia or "sem materia", n) for materia, n in s.execute(consulta)]


def questoes_repetidas(minimo: int = 2) -> list[tuple[str, int, str]]:
    """Enunciados que aparecem em mais de uma prova.

    Banca que reaproveita questao entrega o padrao de graca: essas sao as que
    mais valem estudar.
    """
    criar_tabelas()
    consulta = (
        select(
            QuestaoDeProva.impressao,
            func.count().label("vezes"),
            func.min(QuestaoDeProva.enunciado),
        )
        .group_by(QuestaoDeProva.impressao)
        .having(func.count() >= minimo)
        .order_by(func.count().desc())
    )
    with sessao() as s:
        return [(imp, vezes, enunciado) for imp, vezes, enunciado in s.execute(consulta)]


def contar_questoes() -> int:
    criar_tabelas()
    with sessao() as s:
        return s.scalar(select(func.count()).select_from(QuestaoDeProva)) or 0


# --- aba de noticias --------------------------------------------------------

# Quanto mais adiantado, maior o numero. Serve para ordenar do que esta mais
# proximo de acontecer para o que ja passou.
ORDEM_DAS_FASES = {
    "inscricoes_abertas": 0,
    "banca_definida": 1,
    "autorizado": 2,
    "prevista": 3,
    "edital_publicado": 4,
    "desconhecida": 5,
    "encerrado": 6,
}


def buscar_noticias(termo: str | None = None, limite: int = 60) -> list[Concurso]:
    """Busca em TUDO: qualquer anel, qualquer fase, inclusive o que virou
    noticia.

    As outras abas filtram para nao afogar o que importa. Aqui e o contrario:
    quem procura "PM" quer saber de qualquer concurso de policia militar, esteja
    ele onde estiver e na fase que estiver - inclusive os que ja passaram, que
    e o que diz se o orgao costuma abrir.

    A ordem nao e por data: e pelo ANDAMENTO. O que esta com inscricao aberta
    vem primeiro, depois o que tem banca contratada, depois o autorizado, e o
    encerrado por ultimo.
    """
    criar_tabelas()
    consulta = select(Concurso)

    if termo:
        procurado = f"%{_sem_acento(termo)}%"
        consulta = consulta.where(
            func.sem_acento(Concurso.titulo).ilike(procurado)
            | func.sem_acento(func.coalesce(Concurso.resumo, "")).ilike(procurado)
            | func.sem_acento(func.coalesce(Concurso.municipio, "")).ilike(procurado)
            | func.sem_acento(func.coalesce(Concurso.orgao, "")).ilike(procurado)
        )

    with sessao() as s:
        achados = list(s.scalars(consulta.limit(limite * 4)))

    achados.sort(key=lambda c: (
        ORDEM_DAS_FASES.get(c.situacao, 9),
        -(c.publicado_em.timestamp() if c.publicado_em else 0),
    ))
    return achados[:limite]


def contar_por_fase(termo: str | None = None) -> dict[str, int]:
    """Quantos concursos em cada fase, para o resumo da aba de noticias."""
    criar_tabelas()
    contagem: dict[str, int] = {}
    for concurso in buscar_noticias(termo=termo, limite=10000):
        contagem[concurso.situacao] = contagem.get(concurso.situacao, 0) + 1
    return contagem


# --- modo simulado (fase 5) -------------------------------------------------

# Materias que caem em QUALQUER concurso, independente do cargo. Sao as que
# valem treinar mesmo sem haver prova do cargo que eu quero no acervo.
def materias_universais() -> list[str]:
    """As materias que caem em QUALQUER concurso, do jeito que cada banca as
    escreve.

    Nao vale uma lista fixa de nomes: a FEPESE escreve "Raciocinio Logico" e
    "Nocoes de Informatica", a IESES escreve "Matematica e Raciocinio Logico" e
    "Informatica". Com a lista fixa, o simulado sem materia escolhida so trazia
    Portugues das provas da IESES. Quem decide e o catalogo de apelidos, que ja
    sabe que as duas coisas sao a mesma materia.
    """
    criar_tabelas()
    with sessao() as s:
        nomes = s.scalars(
            select(QuestaoDeProva.materia).where(QuestaoDeProva.materia.is_not(None))
            .group_by(QuestaoDeProva.materia)
        )
        return [nome for nome in nomes if macetes.chave_da_materia(nome)]

QUANTIDADE_PADRAO = 10


def materias_disponiveis() -> list[tuple[str, int]]:
    """[(materia, quantas questoes distintas)], da maior para a menor."""
    criar_tabelas()
    consulta = (
        select(QuestaoDeProva.materia, func.count(func.distinct(QuestaoDeProva.impressao)))
        .group_by(QuestaoDeProva.materia)
        .order_by(func.count(func.distinct(QuestaoDeProva.impressao)).desc())
    )
    with sessao() as s:
        return [(m or "sem materia", n) for m, n in s.execute(consulta)]


def _sortear_questoes(
    quantidade: int,
    materia: str | None = None,
    cargo: str | None = None,
    banca: str | None = None,
    universais: bool = False,
) -> list[int]:
    """Ids de questoes sorteadas, SEM repetir enunciado.

    A banca reaproveita muito: das 5.021 questoes, so 1.815 tem enunciado
    diferente, e uma delas aparece em 44 cadernos. Sortear sem cuidado daria um
    simulado com a mesma pergunta varias vezes.
    """
    consulta = select(QuestaoDeProva).where(QuestaoDeProva.resposta.is_not(None))

    if materia:
        consulta = consulta.where(QuestaoDeProva.materia == materia)
    elif universais:
        consulta = consulta.where(QuestaoDeProva.materia.in_(materias_universais()))
    if cargo:
        consulta = consulta.where(QuestaoDeProva.cargo.ilike(f"%{cargo}%"))
    if banca:
        consulta = consulta.where(QuestaoDeProva.banca.ilike(f"%{banca}%"))

    with sessao() as s:
        candidatas = list(s.scalars(consulta))

    # uma questao por enunciado
    por_enunciado: dict[str, QuestaoDeProva] = {}
    for questao in candidatas:
        por_enunciado.setdefault(questao.impressao, questao)

    import random

    escolhidas = list(por_enunciado.values())
    random.shuffle(escolhidas)
    return [q.id for q in escolhidas[:quantidade]]


def criar_simulado(
    quantidade: int = QUANTIDADE_PADRAO,
    materia: str | None = None,
    cargo: str | None = None,
    banca: str | None = None,
    universais: bool = False,
) -> Simulado | None:
    """Monta uma rodada. Devolve None se nao houver questao que sirva."""
    criar_tabelas()

    ids = _sortear_questoes(quantidade, materia, cargo, banca, universais)
    if not ids:
        return None

    with sessao() as s:
        simulado = Simulado(filtros={
            "quantidade": quantidade, "materia": materia, "cargo": cargo,
            "banca": banca, "universais": universais,
        })
        s.add(simulado)
        s.flush()                      # precisa do id antes de ligar as questoes

        for ordem, questao_id in enumerate(ids, start=1):
            s.add(RespostaDeSimulado(
                simulado_id=simulado.id, questao_id=questao_id, ordem=ordem
            ))
        return simulado


def _respostas(simulado_id: int) -> list[RespostaDeSimulado]:
    with sessao() as s:
        return list(s.scalars(
            select(RespostaDeSimulado)
            .where(RespostaDeSimulado.simulado_id == simulado_id)
            .order_by(RespostaDeSimulado.ordem)
        ))


def questao_atual(simulado_id: int) -> tuple[RespostaDeSimulado, QuestaoDeProva] | None:
    """A proxima questao sem resposta, ou None quando acabou.

    E isso que permite fechar a pagina no meio e voltar depois: o lugar onde
    eu parei esta no banco, nao na sessao do navegador.
    """
    criar_tabelas()
    with sessao() as s:
        resposta = s.scalar(
            select(RespostaDeSimulado)
            .where(RespostaDeSimulado.simulado_id == simulado_id)
            .where(RespostaDeSimulado.escolhida.is_(None))
            .order_by(RespostaDeSimulado.ordem)
            .limit(1)
        )
        if resposta is None:
            return None
        return resposta, s.get(QuestaoDeProva, resposta.questao_id)


def responder(simulado_id: int, questao_id: int, letra: str) -> bool | None:
    """Grava a resposta e devolve se acertou. None se a questao nao e desta
    rodada, ou se ja foi respondida - recarregar a pagina nao pode contar
    duas vezes."""
    criar_tabelas()
    letra = (letra or "").strip().lower()[:1]

    with sessao() as s:
        resposta = s.scalar(
            select(RespostaDeSimulado)
            .where(RespostaDeSimulado.simulado_id == simulado_id)
            .where(RespostaDeSimulado.questao_id == questao_id)
        )
        if resposta is None or resposta.escolhida is not None:
            return None

        questao = s.get(QuestaoDeProva, questao_id)
        if questao is None or letra not in (questao.alternativas or {}):
            return None

        resposta.escolhida = letra
        resposta.acertou = letra == questao.resposta
        resposta.respondida_em = agora()

        # acabou? marca o fim da rodada
        faltam = s.scalar(
            select(func.count()).select_from(RespostaDeSimulado)
            .where(RespostaDeSimulado.simulado_id == simulado_id)
            .where(RespostaDeSimulado.escolhida.is_(None))
        )
        if not faltam:
            simulado = s.get(Simulado, simulado_id)
            if simulado:
                simulado.finalizado_em = agora()

        return resposta.acertou


@dataclass
class DesempenhoDaMateria:
    materia: str
    respondidas: int = 0
    acertos: int = 0

    @property
    def porcentagem(self) -> float:
        return (self.acertos / self.respondidas * 100) if self.respondidas else 0.0


def desempenho(simulado_id: int | None = None) -> list[DesempenhoDaMateria]:
    """Acerto por materia. Sem id, soma TODOS os simulados ja feitos.

    O acumulado e o que responde a pergunta que importa: em que materia eu
    estou pior e preciso estudar.
    """
    criar_tabelas()
    consulta = (
        select(
            QuestaoDeProva.materia,
            func.count(),
            # Somar a coluna booleana direto NAO funciona: o SQLAlchemy
            # devolve a soma com o tipo da coluna, entao 2 acertos voltam
            # como True e viram 1. O case transforma em inteiro antes.
            func.sum(case((RespostaDeSimulado.acertou.is_(True), 1), else_=0)),
        )
        .join(QuestaoDeProva, QuestaoDeProva.id == RespostaDeSimulado.questao_id)
        .where(RespostaDeSimulado.escolhida.is_not(None))
        .group_by(QuestaoDeProva.materia)
    )
    if simulado_id is not None:
        consulta = consulta.where(RespostaDeSimulado.simulado_id == simulado_id)

    with sessao() as s:
        linhas = s.execute(consulta).all()

    resultado = [
        DesempenhoDaMateria(m or "sem materia", int(total), int(acertos or 0))
        for m, total, acertos in linhas
    ]
    # pior primeiro: e onde vale gastar tempo de estudo
    resultado.sort(key=lambda d: d.porcentagem)
    return resultado


def simulados_recentes(limite: int = 10) -> list[Simulado]:
    criar_tabelas()
    with sessao() as s:
        return list(s.scalars(
            select(Simulado).order_by(Simulado.criado_em.desc()).limit(limite)
        ))


def resumo_do_simulado(simulado_id: int) -> dict:
    """Quantas questoes, quantas respondidas e quantos acertos."""
    respostas = _respostas(simulado_id)
    respondidas = [r for r in respostas if r.escolhida]
    return {
        "total": len(respostas),
        "respondidas": len(respondidas),
        "acertos": sum(1 for r in respondidas if r.acertou),
        "terminou": bool(respostas) and len(respondidas) == len(respostas),
    }


def buscar_simulado(simulado_id: int) -> Simulado | None:
    criar_tabelas()
    with sessao() as s:
        return s.get(Simulado, simulado_id)


@dataclass
class ItemDeRevisao:
    enunciado: str
    escolhida: str | None
    correta: str | None
    texto_escolhido: str
    texto_correto: str
    acertou: bool
    materia: str | None = None


def revisao(simulado_id: int) -> list[ItemDeRevisao]:
    """O que eu marquei e qual era a correta, questao a questao.

    Errar sem ver a correta nao ensina nada; e a revisao que faz o simulado
    valer mais que um numero no fim.
    """
    criar_tabelas()
    with sessao() as s:
        linhas = s.execute(
            select(RespostaDeSimulado, QuestaoDeProva)
            .join(QuestaoDeProva, QuestaoDeProva.id == RespostaDeSimulado.questao_id)
            .where(RespostaDeSimulado.simulado_id == simulado_id)
            .where(RespostaDeSimulado.escolhida.is_not(None))
            .order_by(RespostaDeSimulado.ordem)
        ).all()

    itens = []
    for resposta, questao in linhas:
        alternativas = questao.alternativas or {}
        itens.append(ItemDeRevisao(
            enunciado=questao.enunciado,
            escolhida=resposta.escolhida,
            correta=questao.resposta,
            texto_escolhido=alternativas.get(resposta.escolhida, ""),
            texto_correto=alternativas.get(questao.resposta, ""),
            acertou=bool(resposta.acertou),
            materia=questao.materia,
        ))
    # errado primeiro: e o que eu preciso rever
    itens.sort(key=lambda i: i.acertou)
    return itens


# --- previsao de abertura (fase 6) ------------------------------------------

# A Constituicao da ao concurso validade de ate 2 anos, prorrogavel uma vez por
# igual periodo. Isso da o chao e o teto da previsao: antes de 2 anos o orgao
# ainda tem candidato aprovado na fila, e passados 4 quem precisa de gente tem
# de abrir outro. O historico so escolhe DENTRO dessa faixa.
#
# Sem a faixa, buraco de cobertura virava previsao absurda: de Tubarao eu so
# conheco 2011 e 2026, e a conta crua dizia "um a cada 15 anos, proximo em
# 2041". O buraco e o que eu nao coletei, nao concurso que deixou de existir.
VALIDADE_MINIMA = 2
VALIDADE_MAXIMA = 4

# Anos de folga aceitos antes de chamar de atrasado. Concurso escorrega:
# licitacao da banca, orcamento, ano eleitoral.
FOLGA = 1


def _ano_do_concurso(concurso: Concurso) -> int | None:
    """O ano do concurso, do titulo quando ele diz, senao da publicacao.

    O titulo da FEPESE comeca com o ano ("2020 - Prefeitura Municipal de ..."),
    e isso vale mais que a data do post: na migracao do site dela 345 concursos
    antigos ficaram todos com data de dezembro de 2020.
    """
    achado = re.match(r"\s*((?:19|20)\d{2})\s*[-\u2013\u2014]", concurso.titulo)
    if achado:
        return int(achado.group(1))

    # "Edital 003/2018" tambem diz o ano, e cobre o resto dos titulos antigos.
    achado = re.search(r"[Ee]dital[^/]{0,30}/\s*((?:19|20)\d{2})", concurso.titulo)
    if achado:
        return int(achado.group(1))

    return concurso.publicado_em.year if concurso.publicado_em else None


@dataclass
class PrevisaoDeAbertura:
    municipio: str
    anos: list[int]
    ultimo_ano: int
    proximo_previsto: int
    situacao: str            # atrasado | esperado | em_dia
    motivo: str

    @property
    def anos_parado(self) -> int:
        return date.today().year - self.ultimo_ano


def _prever(municipio: str, anos: set[int]) -> PrevisaoDeAbertura:
    """Quando o proximo concurso deste municipio deve sair.

    Com dois ou mais concursos no historico, vale o RITMO do proprio orgao: se
    ele abre a cada tres anos, a conta e essa. Com um so, vale a validade legal
    de 4 anos - nao da para tirar ritmo de um ponto.
    """
    ordenados = sorted(anos)
    ultimo = ordenados[-1]
    este_ano = date.today().year

    if len(ordenados) >= 2:
        vaos = [b - a for a, b in zip(ordenados, ordenados[1:]) if b > a]
        # Mediana, e nao media: um unico buraco de cobertura no meio do
        # historico puxa a media inteira e nao mexe na mediana.
        bruto = round(median(vaos)) if vaos else VALIDADE_MAXIMA
        intervalo = min(VALIDADE_MAXIMA, max(VALIDADE_MINIMA, bruto))
        base = (f"{len(ordenados)} concursos conhecidos ({ordenados[0]} a "
                f"{ultimo}), um a cada {intervalo} ano(s)")
    else:
        intervalo = VALIDADE_MAXIMA
        base = f"um unico concurso conhecido ({ultimo}), sem ritmo para medir"

    previsto = ultimo + intervalo
    if este_ano > previsto + FOLGA:
        situacao = "atrasado"
        conclusao = f"passou {este_ano - previsto} ano(s) do previsto"
    elif este_ano >= previsto - FOLGA:
        situacao = "esperado"
        conclusao = "e a janela de agora"
    else:
        situacao = "em_dia"
        conclusao = f"so em {previsto}"

    return PrevisaoDeAbertura(
        municipio=municipio,
        anos=ordenados,
        ultimo_ano=ultimo,
        proximo_previsto=previsto,
        situacao=situacao,
        motivo=f"{base}. O ultimo foi ha {este_ano - ultimo} ano(s), {conclusao}.",
    )


def previsao_de_abertura(
    aneis: tuple[str, ...] = ("nucleo", "proximo"),
) -> list[PrevisaoDeAbertura]:
    """Municipios perto de casa, do mais atrasado para o menos.

    Cuidado com o que isto NAO sabe: o historico vem da FEPESE (2006 a 2026) e
    do feed (so 2026). Municipio que contratou outra banca entre 2021 e 2025
    tem concurso que nao esta aqui, e vai aparecer mais atrasado do que e.
    """
    criar_tabelas()
    with sessao() as s:
        concursos = list(s.scalars(
            select(Concurso)
            .where(Concurso.relevancia.in_(aneis))
            .where(Concurso.tipo != "noticia")
            .where(Concurso.municipio.is_not(None))
        ))

    anos_por_municipio: dict[str, set[int]] = {}
    for concurso in concursos:
        ano = _ano_do_concurso(concurso)
        if ano:
            anos_por_municipio.setdefault(concurso.municipio, set()).add(ano)

    previsoes = [_prever(m, anos) for m, anos in anos_por_municipio.items()]
    # Atrasado primeiro, e dentro dele o que esta parado ha mais tempo.
    ordem = {"atrasado": 0, "esperado": 1, "em_dia": 2}
    previsoes.sort(key=lambda p: (ordem[p.situacao], -p.anos_parado))
    return previsoes


# --- macetes: o costume da banca (fase 7) -----------------------------------

def bancas_com_questao() -> list[str]:
    """As bancas que tem prova no acervo, da que tem mais questoes para a que
    tem menos. Hoje so a FEPESE: o coletor de provas e por banca."""
    criar_tabelas()
    consulta = (
        select(QuestaoDeProva.banca)
        .where(QuestaoDeProva.banca.is_not(None))
        .group_by(QuestaoDeProva.banca)
        .order_by(func.count().desc())
    )
    with sessao() as s:
        return list(s.scalars(consulta))


def bancas_sem_acervo() -> list[str]:
    """Bancas que aparecem nos meus concursos mas ainda nao tem prova aqui.

    Serve para a tela explicar por que o menu e curto, em vez de parecer que o
    radar so conhece uma banca.
    """
    criar_tabelas()
    com_prova = {b.lower() for b in bancas_com_questao()}
    consulta = (
        select(Concurso.banca)
        .where(Concurso.banca.is_not(None))
        .group_by(Concurso.banca)
        .order_by(func.count().desc())
    )
    with sessao() as s:
        citadas = list(s.scalars(consulta))
    return [b for b in citadas if b.lower() not in com_prova]


def composicao_do_caderno(banca: str | None = None) -> list[macetes.FatiaDoCaderno]:
    """Quantas questoes de cada materia caem num caderno tipico da banca."""
    criar_tabelas()
    return macetes.composicao_do_caderno(_questoes_filtradas(banca=banca))


def _questoes_filtradas(
    banca: str | None = None,
    cargo: str | None = None,
    tema: str | None = None,
) -> list[QuestaoDeProva]:
    """As questoes do recorte pedido.

    O `tema` e texto livre de proposito: eu escrevo "crase" ou "primeiros
    socorros", e nao o nome exato da materia. A busca olha a materia E o
    enunciado, sem acento, porque o nome que a banca usa ("Lingua Portuguesa")
    raramente e a palavra que eu penso ("crase").
    """
    consulta = select(QuestaoDeProva)

    if banca:
        consulta = consulta.where(QuestaoDeProva.banca.ilike(f"%{banca}%"))
    if cargo:
        consulta = consulta.where(QuestaoDeProva.cargo.ilike(f"%{cargo}%"))
    if tema:
        procurado = f"%{_sem_acento(tema)}%"
        consulta = consulta.where(
            func.sem_acento(func.coalesce(QuestaoDeProva.materia, "")).ilike(procurado)
            | func.sem_acento(QuestaoDeProva.enunciado).ilike(procurado)
        )

    with sessao() as s:
        return list(s.scalars(consulta))


def analisar_banca(
    banca: str | None = None,
    cargo: str | None = None,
    tema: str | None = None,
) -> macetes.Analise:
    """O que a banca costuma cobrar no recorte pedido.

    Quando o tema aponta para uma materia so - "crase" e Lingua Portuguesa em
    56 de 59 questoes -, a analise traz junto o retrato daquela materia inteira
    na banca: quanto ela cai por caderno e de que assuntos e feita. E a
    pergunta seguinte natural de quem procurou por um assunto.
    """
    criar_tabelas()
    questoes = _questoes_filtradas(banca, cargo, tema)
    analise = macetes.analisar(questoes)

    if not questoes:
        return analise

    dominante = macetes.materia_dominante(questoes)
    analise.materia_dominante = dominante
    if dominante and tema:
        # O retrato e da materia INTEIRA na banca, e nao do recorte: a pergunta
        # e "quanto isso cai nas provas", e nao "quanto isso cai no que eu
        # acabei de filtrar".
        da_materia = [
            q for q in _questoes_filtradas(banca, cargo)
            if q.materia == dominante
        ]
        analise.retrato = macetes.retratar_materia(da_materia, dominante)
        analise.assunto_procurado = macetes.assunto_do_tema(tema, analise.retrato)

    return analise


# --- elegibilidade: o que o edital exige de mim (fase 2.5) ------------------

@dataclass
class ResultadoElegibilidade:
    concursos: int = 0
    lidos: int = 0
    ilegiveis: int = 0
    sem_edital: int = 0

    def __str__(self) -> str:
        if not self.concursos:
            return "Nenhum concurso com edital no acervo para ler."
        texto = f"{self.concursos} concurso(s), {self.lidos} com exigencias lidas"
        if self.ilegiveis:
            texto += f", {self.ilegiveis} com edital so em imagem"
        if self.sem_edital:
            texto += f", {self.sem_edital} sem edital no acervo"
        return texto


def _editais_por_concurso() -> dict[str, list[dict]]:
    """{url do concurso: [registros de edital]}, do manifesto.

    O edital principal vem primeiro: e o maior arquivo. Termo aditivo e
    retificacao sao curtos e costumam mudar so um item, entao servem de
    segunda tentativa quando o principal nao rende nada.
    """
    por_concurso: dict[str, list[dict]] = {}
    for registro in provas.carregar_manifesto():
        if registro.get("tipo") != provas.EDITAL or not registro.get("concurso_url"):
            continue
        por_concurso.setdefault(registro["concurso_url"], []).append(registro)

    for registros in por_concurso.values():
        registros.sort(key=lambda r: -(r.get("tamanho") or 0))
    return por_concurso


def _exigencias_do_concurso(registros: list[dict]) -> leitor_de_elegibilidade.Exigencias:
    """Le os editais daquele concurso ate um deles dizer alguma coisa."""
    melhor = leitor_de_elegibilidade.Exigencias(legivel=False)

    for registro in registros:
        caminho = _caminho(registro)
        if caminho is None:
            continue
        achado = leitor_de_elegibilidade.ler(
            leitor_de_questoes.extrair_texto(caminho)
        )
        if achado.niveis:
            return achado
        if achado.legivel:
            melhor = achado

    return melhor


def ler_elegibilidade(limite: int = 50, refazer: bool = False) -> ResultadoElegibilidade:
    """Le os editais do acervo e grava o que cada concurso exige.

    Nao vai a internet: trabalha nos PDFs que `radar provas` ja baixou.
    """
    criar_tabelas()
    resultado = ResultadoElegibilidade()
    por_concurso = _editais_por_concurso()
    if not por_concurso:
        return resultado

    with sessao() as s:
        consulta = select(Concurso).where(Concurso.url.in_(list(por_concurso)))
        if not refazer:
            consulta = consulta.where(Concurso.elegibilidade == "a_confirmar")

        for concurso in s.scalars(consulta.limit(limite)):
            resultado.concursos += 1
            exigencias = _exigencias_do_concurso(por_concurso[concurso.url])

            if not exigencias.legivel:
                resultado.ilegiveis += 1
                concurso.motivo_elegibilidade = leitor_de_elegibilidade.resumir(exigencias)
                continue

            _gravar_exigencias(concurso, exigencias)
            resultado.lidos += 1

    return resultado


def _gravar_exigencias(concurso: Concurso, exigencias) -> None:
    """Passa o que o edital diz para as colunas do concurso.

    `elegivel` aqui quer dizer uma coisa so: o concurso TEM vaga de nivel
    superior, que e o que eu posso prestar. Nao e promessa de que eu sirvo para
    todas as vagas dele - isso muda de cargo para cargo, e o radar guarda um
    registro por concurso.
    """
    if exigencias.niveis:
        concurso.escolaridade = ", ".join(exigencias.niveis)
    concurso.idade_maxima = exigencias.idade_maxima

    # O veredito cruza o edital com config/perfil.yml. Sem perfil preenchido
    # ele fica em "a confirmar", que e o certo: campo em branco quer dizer
    # "nao sei", e nao "nao tenho".
    veredito = meu_perfil.avaliar(exigencias)
    concurso.elegibilidade = veredito.situacao
    resumo = leitor_de_elegibilidade.resumir(exigencias)
    if veredito.motivo:
        resumo = f"{resumo} | {veredito.motivo}"
    concurso.motivo_elegibilidade = resumo[:300]

    # CNH e teste fisico nao tem coluna propria, e nao vale criar uma agora: o
    # que interessa e ver na tela, e o `extra` ja guarda o que a fonte manda.
    extra = dict(concurso.extra or {})
    extra["exigencias"] = {
        "cnh": exigencias.cnh,
        "taf": exigencias.taf,
        "idade_minima": exigencias.idade_minima,
        "trechos": exigencias.trechos,
    }
    concurso.extra = extra


# --- calendario (fase 2.2) --------------------------------------------------

def eventos_do_calendario() -> list[calendario.Evento]:
    """Os prazos que valem entrar na minha agenda.

    Entra o que e meu interesse declarado (favorito) e o que esta perto de
    casa. Fica de fora o que ja venceu: compromisso no passado so atrapalha
    quem abre a agenda.

    O prazo de inscricao e o unico dado do radar que nao pode ser visto tarde
    demais - por isso ele vai para o celular, e nao so para a tela.
    """
    criar_tabelas()
    hoje = agora().astimezone(fuso_local()).date()

    consulta = (
        select(Concurso)
        .where(Concurso.tipo != "noticia")
        .where(Concurso.inscricoes_ate.is_not(None))
        .where(
            (Concurso.interesse == FAVORITO)
            | Concurso.relevancia.in_(("nucleo", "proximo"))
        )
        .order_by(Concurso.inscricoes_ate)
    )

    eventos: list[calendario.Evento] = []
    with sessao() as s:
        for concurso in s.scalars(consulta):
            fim = concurso.inscricoes_ate.astimezone(fuso_local()).date()
            if fim < hoje:
                continue

            onde = concurso.municipio or concurso.uf or "local a confirmar"
            detalhe = [f"{onde}."]
            if concurso.banca:
                detalhe.append(f"Banca: {concurso.banca}.")
            if concurso.salario:
                detalhe.append(f"Salario: R$ {concurso.salario:,.0f}."
                               .replace(",", "."))
            if concurso.motivo_elegibilidade:
                detalhe.append(concurso.motivo_elegibilidade)

            eventos.append(calendario.Evento(
                # A url e a chave natural do concurso: o mesmo concurso gera
                # sempre o mesmo evento, e o calendario atualiza em vez de
                # duplicar quando o prazo muda.
                identificador=f"inscricao:{concurso.url}",
                titulo=f"Ultimo dia de inscricao: {concurso.titulo}",
                quando=fim,
                descricao=" ".join(detalhe),
                url=concurso.url,
            ))

            if concurso.data_prova:
                prova = concurso.data_prova.astimezone(fuso_local()).date()
                if prova >= hoje:
                    eventos.append(calendario.Evento(
                        identificador=f"prova:{concurso.url}",
                        titulo=f"Prova: {concurso.titulo}",
                        quando=prova,
                        descricao=" ".join(detalhe),
                        url=concurso.url,
                    ))

    return eventos


def calendario_ics() -> str:
    """O arquivo .ics pronto, com os prazos que valem a minha agenda."""
    return calendario.montar(eventos_do_calendario())


# --- prova substituta (fase 3) ----------------------------------------------

def provas_parecidas(
    cargo: str,
    banca: str | None = None,
    municipio: str | None = None,
    quantas: int = 8,
) -> list[substituta.Parecida]:
    """As provas do acervo mais parecidas com o cargo que eu quero.

    Existe porque os cargos que eu mais quero - Guarda Municipal, Policia
    Penal - nao tem prova nenhuma no acervo. Em vez de tela vazia, a lista
    mostra o que existe e EM CIMA DE QUE a semelhanca foi medida.
    """
    criar_tabelas()
    if not (cargo or "").strip():
        return []

    consulta = (
        select(
            QuestaoDeProva.cargo,
            QuestaoDeProva.banca,
            QuestaoDeProva.municipio,
            QuestaoDeProva.ano,
            func.count(),
        )
        .where(QuestaoDeProva.cargo.is_not(None))
        .group_by(
            QuestaoDeProva.cargo,
            QuestaoDeProva.banca,
            QuestaoDeProva.municipio,
            QuestaoDeProva.ano,
        )
    )
    with sessao() as s:
        candidatas = [
            substituta.Parecida(cargo=c, banca=b, municipio=m, ano=a, questoes=n)
            for c, b, m, a, n in s.execute(consulta)
        ]

    ano_recente = agora().year - 2
    return substituta.ordenar(
        candidatas, cargo, banca, municipio, ano_recente
    )[:quantas]


def recado_sobre_o_cargo(cargo: str, parecidas: list) -> str:
    """O que dizer quando nao ha prova parecida o bastante."""
    if parecidas:
        return ""
    return substituta.explicar_ausencia(cargo, materias_universais())


# --- retificacao de edital (fase 2.5) ---------------------------------------

@dataclass
class Retificacao:
    """Um edital que mudou depois de eu ter baixado."""

    concurso_url: str
    titulo: str
    arquivo: str
    url: str
    sha_antigo: str
    sha_novo: str


@dataclass
class ResultadoRetificacao:
    conferidos: int = 0
    mudaram: list[Retificacao] = field(default_factory=list)
    falhas: int = 0

    def __str__(self) -> str:
        if not self.conferidos:
            return "Nenhum edital em pe para conferir."
        texto = f"{self.conferidos} edital(is) conferido(s)"
        if self.mudaram:
            texto += f", [bold red]{len(self.mudaram)} mudou(ram)[/]"
        else:
            texto += ", nenhum mudou"
        if self.falhas:
            texto += f", {self.falhas} fora do ar"
        return texto


def _editais_em_pe() -> list[tuple[dict, Concurso]]:
    """Editais de concurso cuja inscricao ainda nao encerrou.

    So esses valem reconferir: edital de concurso encerrado nao vai mais ser
    retificado, e cada conferencia custa uma requisicao e um download.
    """
    por_concurso = _editais_por_concurso()
    if not por_concurso:
        return []

    agora_ = agora()
    pares: list[tuple[dict, Concurso]] = []
    with sessao() as s:
        for concurso in s.scalars(
            select(Concurso).where(Concurso.url.in_(list(por_concurso)))
        ):
            if concurso.inscricoes_ate and concurso.inscricoes_ate < agora_:
                continue
            if concurso.situacao == "encerrado":
                continue
            for registro in por_concurso[concurso.url]:
                if registro.get("sha256"):
                    pares.append((registro, concurso))
    return pares


def conferir_retificacoes(limite: int = 20) -> ResultadoRetificacao:
    """Baixa de novo os editais em pe e ve se o conteudo mudou.

    O manifesto ja guarda o sha256 de cada arquivo desde a fase 3 - ele existia
    para reconstruir o acervo noutra maquina. Serve tambem para isto: se o
    mesmo endereco passa a devolver bytes diferentes, o edital foi retificado.

    Retificacao muda prazo, vaga e requisito. Descobrir isso tarde e o tipo de
    erro que nao da para corrigir depois.
    """
    criar_tabelas()
    resultado = ResultadoRetificacao()
    buscador = Buscador()

    for registro, concurso in _editais_em_pe()[:limite]:
        documento = provas.Documento(
            tipo=provas.EDITAL,
            url=registro["url"],
            arquivo=registro.get("arquivo", ""),
            banca=registro.get("banca"),
            municipio=registro.get("municipio"),
            ano=registro.get("ano"),
            concurso_url=registro.get("concurso_url"),
        )

        # `forcar` porque o arquivo ja esta em disco: sem isso, `baixar`
        # devolveria o sha do que eu tenho e nunca acusaria mudanca.
        baixado = provas.baixar(documento, buscador, forcar=True)
        if baixado is None:
            resultado.falhas += 1
            continue

        resultado.conferidos += 1
        if baixado.sha256 == registro["sha256"]:
            continue

        resultado.mudaram.append(Retificacao(
            concurso_url=concurso.url,
            titulo=concurso.titulo,
            arquivo=registro.get("arquivo", ""),
            url=registro["url"],
            sha_antigo=registro["sha256"],
            sha_novo=baixado.sha256,
        ))

        # O manifesto passa a valer o arquivo novo, senao a proxima conferencia
        # acusaria a mesma retificacao de novo.
        todos = provas.carregar_manifesto()
        for linha in todos:
            if linha.get("url") == registro["url"]:
                linha.update(provas.para_registro(baixado))
        provas.gravar_manifesto(todos)

    return resultado
