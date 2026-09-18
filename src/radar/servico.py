"""Regras do sistema: rodar os coletores, gravar sem duplicar, consultar."""
import logging
import re
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import func, select

from radar import avisos
from radar import detalhes, provas, questoes as leitor_de_questoes, regioes
from radar.classificador import classificar
from radar.collectors.base import Buscador, Coletor, ItemColetado
from radar.collectors.concursos_no_brasil import MAXIMO_DE_PAGINAS, ConcursosNoBrasil
from radar.collectors.fepese import Fepese
from radar import config
from radar.db import criar_tabelas, sessao
from radar.models import Concurso, QuestaoDeProva, agora

log = logging.getLogger(__name__)

# Registre aqui cada coletor novo. E o unico lugar que precisa saber a lista.
COLETORES: list[type[Coletor]] = [ConcursosNoBrasil, Fepese]

# Campos que a coleta manda. O que NAO esta aqui e seu e nunca e sobrescrito:
# interesse, notas, e o que voce corrigir a mao no banco.
CAMPOS_DA_FONTE = (
    "titulo", "resumo", "orgao", "municipio", "uf", "banca", "situacao",
    "escolaridade", "publicado_em",
)

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
        # pode piorar o registro.
        if valor is None or valor == getattr(existente, campo):
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
            )
            _aplicar_classificacao(concurso, item)
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

            # Municipio novo muda o anel: e o caminho da SEFAZ SC sair de
            # indefinida para nucleo.
            if achado.municipio and not concurso.municipio:
                anel_antes = concurso.relevancia
                concurso.municipio = achado.municipio
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
    return (concurso.extra or {}).get("hotsite")


# Ordem de prioridade para gastar requisicao. Prova de concurso encerrado perto
# de casa vale mais que qualquer outra: e o padrao da banca na minha regiao.
PRIORIDADE_ACERVO = (
    lambda: Concurso.relevancia.in_(("nucleo", "proximo")),
    lambda: Concurso.relevancia == "indefinida",
)


def _concursos_com_prova(limite: int) -> list[Concurso]:
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
                .where(Concurso.fonte == "fepese")
                # so concurso ja realizado tem prova publicada
                .where(Concurso.situacao == "encerrado")
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


def montar_acervo(limite: int = 20) -> ResultadoAcervo:
    """Le os hotsites e baixa edital, prova e gabarito.

    Uma requisicao por pagina do hotsite e uma por PDF, todas com a pausa da
    classe Coletor. Por isso o limite: ler os 520 concursos de uma vez levaria
    horas e a maior parte nao interessa.
    """
    criar_tabelas()
    resultado = ResultadoAcervo()

    escolhidos = _concursos_com_prova(limite)
    if not escolhidos:
        return resultado

    registros = provas.carregar_manifesto()
    conhecidos = {r.get("url") for r in registros}
    buscador = Buscador()

    for concurso in escolhidos:
        hotsite = _hotsite(concurso).rstrip("/")
        encontrados: list[provas.Documento] = []

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
    repetidas: int = 0
    vazias: int = 0

    def __str__(self) -> str:
        if not self.provas:
            return "Nenhuma prova nova para ler."
        texto = f"{self.provas} prova(s) lida(s), {self.questoes} questao(oes)"
        if self.repetidas:
            texto += f", {self.repetidas} ja vista(s) em outra prova"
        if self.vazias:
            texto += f", {self.vazias} sem questao"
        return texto


def _provas_por_ler(limite: int) -> list[dict]:
    """Provas do manifesto que ainda nao viraram questao no banco."""
    with sessao() as s:
        ja_lidas = set(s.scalars(select(QuestaoDeProva.prova_url).distinct()))

    pendentes = [
        registro for registro in provas.carregar_manifesto()
        if registro.get("tipo") == provas.PROVA
        and registro.get("caminho")
        and registro["url"] not in ja_lidas
    ]
    return pendentes[:limite]


def extrair_questoes(limite: int = 30) -> ResultadoExtracao:
    """Le os cadernos do acervo e guarda as questoes.

    Nao vai a internet: trabalha em cima dos PDFs que `radar provas` ja baixou.
    """
    criar_tabelas()
    resultado = ResultadoExtracao()

    pendentes = _provas_por_ler(limite)
    if not pendentes:
        return resultado

    for registro in pendentes:
        caminho = config.diretorio_dados() / registro["caminho"]
        if not caminho.exists():
            continue

        lidas = leitor_de_questoes.ler_prova(caminho)
        resultado.provas += 1
        if not lidas:
            resultado.vazias += 1
            continue

        with sessao() as s:
            conhecidas = set(s.scalars(select(QuestaoDeProva.impressao)))

            for questao in lidas:
                if questao.impressao in conhecidas:
                    resultado.repetidas += 1
                conhecidas.add(questao.impressao)

                s.add(QuestaoDeProva(
                    prova_url=registro["url"],
                    concurso_url=registro.get("concurso_url"),
                    banca=registro.get("banca"),
                    ano=registro.get("ano"),
                    municipio=registro.get("municipio"),
                    cargo=registro.get("cargo"),
                    numero=questao.numero,
                    materia=questao.materia,
                    enunciado=questao.enunciado,
                    alternativas=questao.alternativas,
                    resposta=questao.resposta,
                    impressao=questao.impressao,
                ))
                resultado.questoes += 1

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
