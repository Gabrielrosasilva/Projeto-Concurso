"""Regras do sistema: rodar os coletores, gravar sem duplicar, consultar."""
import logging
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import func, select

from radar import avisos
from radar.classificador import classificar
from radar.collectors.base import Coletor, ItemColetado
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
    limite: int = 30,
) -> list[Concurso]:
    """Consulta o que ja foi coletado, com filtros opcionais."""
    criar_tabelas()
    consulta = select(Concurso).order_by(Concurso.publicado_em.desc().nullslast())

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
