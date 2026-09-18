"""Regras do sistema: rodar os coletores, gravar sem duplicar, consultar."""
import logging
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import func, select

from radar import avisos
from radar import detalhes, regioes
from radar.classificador import classificar
from radar.collectors.base import Buscador, Coletor, ItemColetado
from radar.collectors.concursos_no_brasil import MAXIMO_DE_PAGINAS, ConcursosNoBrasil
from radar import config
from radar.db import criar_tabelas, sessao
from radar.models import Concurso, agora

log = logging.getLogger(__name__)

# Registre aqui cada coletor novo. E o unico lugar que precisa saber a lista.
COLETORES: list[type[Coletor]] = [ConcursosNoBrasil]

# Campos que a coleta manda. O que NAO esta aqui e seu e nunca e sobrescrito:
# interesse, notas, e o que voce corrigir a mao no banco.
CAMPOS_DA_FONTE = (
    "titulo", "resumo", "orgao", "municipio", "uf", "banca", "situacao",
    "publicado_em",
)

# Campos que o classificador calcula. Sao derivados do titulo, entao podem ser
# recalculados a qualquer momento - e por isso que existe `reclassificar()`:
# se eu editar config/regioes.yml, o banco inteiro se corrige sem recoletar.
CAMPOS_CALCULADOS = ("municipio", "salario", "tipo", "relevancia", "motivo_relevancia")


def _aplicar_classificacao(destino, item: ItemColetado) -> None:
    resultado = classificar(item)
    destino.municipio = resultado.municipio
    destino.salario = resultado.salario
    destino.tipo = resultado.tipo
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

    if salario_min is not None:
        # Filtro filtra: quem nao tem salario conhecido fica de fora.
        #
        # A primeira versao deixava os sem valor passarem, para nao esconder
        # concurso bom - mas 1.115 dos 2.185 nao trazem salario no titulo, e o
        # resultado era um filtro que nao filtrava nada. Quem usa precisa
        # saber do ponto cego, e nao adivinhar: a tela avisa quantos ficaram
        # de fora por falta de valor, e `contar_sem_salario` da esse numero.
        consulta = consulta.where(Concurso.salario >= salario_min).order_by(
            None
        ).order_by(Concurso.salario.desc())

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
        consulta = consulta.where(Concurso.banca.ilike(f"%{banca}%"))
    if situacao:
        consulta = consulta.where(Concurso.situacao == situacao)
    if termo:
        like = f"%{termo}%"
        consulta = consulta.where(
            Concurso.titulo.ilike(like) | Concurso.resumo.ilike(like)
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


def _nao_avisados() -> list[Concurso]:
    """Concursos que interessam e que ainda nao viraram mensagem."""
    consulta = (
        select(Concurso)
        .where(Concurso.avisado_em.is_(None))
        .where(Concurso.tipo != "noticia")
        .where(Concurso.relevancia.in_(RELEVANCIA_AVISO))
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
