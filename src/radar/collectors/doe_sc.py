"""Fonte 4: Diario Oficial do Estado de SC, pela busca que a propria tela usa.

Por que esta fonte: o contrato da banca sai aqui primeiro, meses antes do
edital, e `banca_definida` e o sinal mais valioso do ciclo de vida. Estavam
aqui o resultado da dispensa (27/05/2026) e o contrato (02/07/2026) da PM SC
com o Instituto AOCP, e os contratos da PC SC (04/12/2025), do CBMSC
(16/12/2025) e da Policia Cientifica (12/12/2025).

Nao e o DOM/SC, o diario dos MUNICIPIOS, que proibe robo no robots.txt. O DOE
nao tem robots.txt de verdade: o /robots.txt devolve a pagina HTML que
redireciona para o portal, e so o que se consegue LER vira restricao.

Como foi achada: o portal (portal.doe.sea.sc.gov.br) e uma tela em Angular, e
o JavaScript dela pergunta a `POST /apis/busca-materia`, sem login - o token
so vai quando ha usuario logado. Os codigos de tipo de ato e de categoria
abaixo sairam das listas que a mesma tela usa (`/apis/assunto/list` e
`/apis/select/categoria/categoria`), em 11/10/2026.

O recorte, porque o diario e um rio: "concurso publico" aparece em uns 1.800
atos por mes, quase todos nomeacao, posse e convocacao de quem ja passou.
Daqui so sai o ato que e um destes quatro, e que fala de um cargo do
`config/alvo.yml`:

  1. **a contratacao da banca** (extrato de contrato, resultado da dispensa)
     cujo objeto e um concurso -> `banca_definida`, com a banca escrita como
     o ato escreve;
  2. **a autorizacao** para realizar ou abrir o concurso -> `autorizado`;
  3. **a comissao** do concurso -> `desconhecida`;
  4. **o edital** de abertura, a retificacao ou a errata -> `desconhecida`.

O "resto desconhecida" e de proposito: o diario diz o que o ato e, e nao em
que pe o concurso esta. O classificador ainda le o titulo.

A lista de cargos NAO mora aqui: e a do `alvo.yml`, lida pelo `alvo.marcar`.
Somar uma carreira la passa a trazer os atos dela daqui, sem codigo.

Nunca use `resumo: true` na busca: a API devolve entao um resumo GERADO POR
MAQUINA pelo proprio portal ("O documento e o Edital..."), e nao o texto do
ato. Com `false`, o `resumo` e um trecho do texto de verdade.
"""
import html
import logging
import re
from datetime import date, datetime, timedelta

from radar import alvo
from radar.collectors.base import Coletor, ItemColetado
from radar.regioes import normalizar

log = logging.getLogger(__name__)

API = "https://portal.doe.sea.sc.gov.br/apis/busca-materia"

# A coleta de todo dia olha os ultimos 10 dias: sobra folga para o robo que
# ficou uns dias sem rodar. O historico de 12 meses entra uma vez, pela
# `radar carga-inicial --fonte doe_sc`.
JANELA_EM_DIAS = 10

# A tela pede 10 por vez; 100 faz a janela de 10 dias caber numa pagina.
POR_PAGINA = 100

# Teto por consulta. A carga de 365 dias da contratacao teve 7.970 acertos
# (80 paginas) em 11/10/2026; a coleta de 10 dias, uns 220 (3 paginas). Daqui
# para cima, algo mudou na API.
MAXIMO_DE_PAGINAS = 80

BUSCA = "concurso público"

# Tipos de ato (assunto) e categorias, com o nome que a lista do portal da.
CONSULTAS = (
    # A contratacao da banca: CONTRATOS 63, EXTRATO DE CONTRATO 64, ATO DE
    # DISPENSA 26, EDITAL DE DISPENSA 67, EXTRATO 230, LICITACAO 42 e
    # RESULTADO DE LICITACAO 157. O resultado da dispensa da PM SC saiu como
    # LICITACAO, um mes antes do contrato.
    {"aCdAssunto": [63, 64, 26, 67, 230, 42, 157]},
    # As categorias das forcas e a de concursos: Concursos 4704262, Justica e
    # Reintegracao Social 4704912, Seguranca Publica 4704926, Policia Civil
    # 4704929, Policia Militar 4704928, Corpo de Bombeiros Militar 4704930,
    # Policia Cientifica 4704932.
    {"aCdCategoria": [4704262, 4704912, 4704926, 4704929, 4704928, 4704930, 4704932]},
    # A autorizacao, que pode sair em qualquer categoria: ATO DE AUTORIZAR 91,
    # AUTORIZACAO 149, PORTARIA DE AUTORIZAR 18 e RESOLUCAO 40 (a do Grupo
    # Gestor de Governo).
    {"aCdAssunto": [91, 149, 18, 40]},
)

# Quanto do comeco do texto integral decide o que o ato e. O edital tem
# 270 mil caracteres; o que ele e esta escrito no cabecalho.
INICIO = 1500
# E quanto dele diz de quem o ato e: o orgao, o cargo, o objeto.
CABECALHO_DO_ALVO = 600

# --- o que o ato e ----------------------------------------------------------
#
# Tudo comparado no texto normalizado (sem acento, minusculo, um espaco so).

CONTRATO, AUTORIZACAO, COMISSAO, EDITAL = "contrato", "autorizacao", "comissao", "edital"

SITUACAO_DO_ATO = {
    CONTRATO: "banca_definida",
    AUTORIZACAO: "autorizado",
    COMISSAO: "desconhecida",
    EDITAL: "desconhecida",
}

# Ato de contratacao: o extrato do contrato ("Contratada: ...") ou o
# resultado da dispensa ("Valor Adjudicado").
CONTRATACAO = re.compile(r"\bcontratad[ao]\b|\bvalor adjudicado\b")

# O que fala da banca sem contrata-la: a advertencia ao IDIB e ao Idecan
# (2026) cita o contrato inteiro, e a rescisao tambem.
NAO_E_CONTRATACAO = re.compile(
    r"\bsancao\b|\bpenalidade\b|\badvertencia\b|\brescis\w*|\bdistrato\b|"
    r"\bcitacao\b|\bintimacao\b|\baditivo\b"
)

# "autoriza a realizacao do concurso publico", "autorizada a abertura de
# concurso". Sem a realizacao ou a abertura, e autorizacao de outra coisa:
# "autoriza a CIDASC a contratar 2 candidatos aprovados no concurso publico".
AUTORIZA = re.compile(
    r"\bautoriz\w*\b(?:\W+\w+){0,8}?\W+(?:realizacao|abertura|deflagracao)\b"
    r"(?:\W+\w+){0,4}?\W+concurso\b"
)

# O ato que CRIA ou compoe a comissao: "Constituir a Comissao de Concurso
# Publico do CBMSC" (Portaria 71/2026). Sem o verbo, nao: as portarias que
# designam coordenadores de prova sao assinadas pelo "PRESIDENTE DA COMISSAO
# DE CONCURSO PUBLICO", e a "Comissao de Avaliacao de Recursos do TAF" e de
# uma etapa, nao do concurso.
COMISSAO_DO_CONCURSO = re.compile(
    r"\b(?:constitu|institu|cria|compo|design)\w*\b(?:\W+\w+){0,3}?\W+comissao\b"
    r"(?:\W+\w+){0,2}?\W+(?:do|de|para o)\W+concurso\b"
)

# O cabecalho do edital que interessa: abertura, retificacao, errata.
EDITAL_NO_CABECALHO = re.compile(r"\b(?:edital|errata|retificacao)\b")
EDITAL_QUE_INTERESSA = re.compile(r"\b(?:abertura|retifica\w*|errata|alteracao)\b")
# Edital de quem ja passou, ou de etapa: nao e novidade de concurso.
EDITAL_DE_ETAPA = re.compile(
    r"\b(?:convoca\w*|resultado|homologa\w*|classifica\w*|nomea\w*|gabarito|"
    r"aprovad\w*|inaptos?|aptos?)\b"
)
# Os tipos de ato do portal que sao edital, mesmo quando o cabecalho e o nome
# do orgao ("GOVERNO DO ESTADO ... CORPO DE BOMBEIROS ... CONCURSO PUBLICO").
ASSUNTOS_DE_EDITAL = {
    "edital", "edital de concurso", "errata", "extrato de edital",
    "ato de retificar", "termo de retificar",
}
CABECALHO = 200

# --- a banca, como o ato escreve -------------------------------------------

# "Contratada: Instituto AOCP." / "Contratada Instituto ... - IDECAN." /
# "Contratada:  FUNDACAO ... (FEPESE),  CNPJ ...". Para no CNPJ, no ponto
# seguido de espaco ou no ponto e virgula.
CONTRATADA = re.compile(
    r"\bContratad[ao]\s*:?\s+(.+?)(?=\s*,?\s*CNPJ\b|\.\s|;|\.$|$)", re.IGNORECASE
)
# O resultado da dispensa: "Item(ns): 1 - INSTITUTO AOCP, Valor Adjudicado".
ADJUDICADO = re.compile(
    r"\bItem\(?ns\)?\s*:\s*\d+\s*-\s*(.+?),\s*Valor Adjudicado", re.IGNORECASE
)


def _limpar(texto: str) -> str:
    return " ".join(html.unescape(texto or "").split())


def que_ato_e(texto: str, assunto: str | None = None) -> str | None:
    """contrato, autorizacao, comissao, edital - ou None, que fica de fora.

    `texto` e o comeco do ato; `assunto` e o tipo de ato que o portal da.
    A ordem importa: o extrato do contrato cita o concurso e o edital, e e
    contrato que ele e.
    """
    t = normalizar(texto)
    if not re.search(r"\bconcurso\b", t):
        return None
    # O edital de militar temporario do CBMSC cita o concurso publico no
    # corpo, mas e processo seletivo: o cabecalho diz.
    if re.search(r"\bprocesso seletivo\b", t[:CABECALHO]):
        return None

    if CONTRATACAO.search(t) and not NAO_E_CONTRATACAO.search(t):
        return CONTRATO
    if AUTORIZA.search(t):
        return AUTORIZACAO
    if COMISSAO_DO_CONCURSO.search(t):
        return COMISSAO

    cabecalho = t[:CABECALHO]
    eh_edital = (EDITAL_NO_CABECALHO.search(cabecalho)
                 or normalizar(assunto) in ASSUNTOS_DE_EDITAL)
    if (eh_edital and "concurso publico" in t
            and EDITAL_QUE_INTERESSA.search(t[:INICIO])
            and not EDITAL_DE_ETAPA.search(cabecalho)):
        return EDITAL
    return None


def banca_do_ato(texto: str) -> str | None:
    """A banca como o ato escreve: "Instituto AOCP", ou o nome por extenso.

    O nome por extenso nao vira sigla aqui: "INSTITUTO DE DESENVOLVIMENTO
    INSTITUCIONAL BRASILEIRO" e o IDIB, mas afirmar isso e coisa para
    conferir, nao para o coletor deduzir.
    """
    limpo = _limpar(texto)
    achado = ADJUDICADO.search(limpo) or CONTRATADA.search(limpo)
    if not achado:
        return None
    banca = achado.group(1).strip(" -–—,.:")
    return banca or None


def _paragrafos(pagina: str) -> list[str]:
    """Os paragrafos do texto integral (o `preview` do portal)."""
    corpo = pagina[pagina.find("<body"):] if "<body" in pagina else pagina
    brutos = re.findall(r"<p\b[^>]*>(.*?)</p>", corpo, re.S | re.I)
    paragrafos = [_limpar(re.sub(r"<[^>]+>", " ", p)) for p in brutos]
    return [p for p in paragrafos if p]


# O nome do ato no cabecalho: e ate ele que o titulo vai.
NOME_DE_ATO = re.compile(
    r"\b(?:extrato|contrato|edital|portaria|resultado|errata|retificacao|"
    r"dispensa|aviso|resolucao|decreto|lei)\b"
)
# Abre muito ato e nao diz nada.
CABECALHO_VAZIO = "governo do estado de santa catarina"


def _primeira_frase(paragrafo: str) -> str:
    """O extrato do contrato vem num paragrafo so, com tudo dentro: fica a
    primeira frase. Paragrafo curto ("PORTARIA N. 71/2026/CBMSC, de
    04/02/2026.") fica inteiro."""
    if len(paragrafo) > 120:
        ponto = paragrafo.find(". ", 20)
        if ponto != -1:
            paragrafo = paragrafo[:ponto]
    return paragrafo.strip(" .")


def titulo_do_ato(paragrafos: list[str], limite: int = 200) -> str:
    """O cabecalho do ato, como ele se apresenta.

    "CORPO DE BOMBEIROS MILITAR - EXTRATO DE CONTRATO - Termo de Contrato n.
    0327/2025/CBMSC"; "PORTARIA N. 71/2026/CBMSC, de 04/02/2026 - Constituir
    a Comissao de Concurso Publico...". Junta os paragrafos do comeco ate
    aparecer o nome do ato com pelo menos 60 letras, e pega a errata que vem
    logo atras do numero do edital.
    """
    partes: list[str] = []
    restantes = [p for p in paragrafos if normalizar(p) != CABECALHO_VAZIO]
    for indice, paragrafo in enumerate(restantes[:4]):
        partes.append(_primeira_frase(paragrafo))
        junto = " - ".join(partes)
        if NOME_DE_ATO.search(normalizar(junto)) and len(junto) >= 60:
            seguinte = restantes[indice + 1] if indice + 1 < len(restantes) else ""
            if len(seguinte) < 40 and re.search(r"\b(?:errata|retificacao)\b",
                                                normalizar(seguinte)):
                partes.append(seguinte.strip(" ."))
            break

    titulo = " - ".join(p for p in partes if p)
    if len(titulo) > limite:
        titulo = titulo[:limite].rsplit(" ", 1)[0] + "…"
    return titulo


def _data(texto: str | None) -> datetime | None:
    """"2026-07-02T00:00:00.000Z" -> 02/07/2026, meia-noite daqui.

    O portal manda a DATA da edicao com hora zero em UTC. Ler como UTC jogaria
    o ato para as 21h do dia anterior.
    """
    if not texto:
        return None
    from radar.util import fuso_local

    try:
        dia = date.fromisoformat(texto[:10])
    except ValueError:
        return None
    return datetime(dia.year, dia.month, dia.day, tzinfo=fuso_local())


class DoeSc(Coletor):
    nome = "doe_sc"

    def __init__(self, dias: int = JANELA_EM_DIAS, hoje: date | None = None) -> None:
        super().__init__()
        self.dias = max(1, dias)
        self.hoje = hoje

    def coletar(self) -> list[ItemColetado]:
        from radar.util import fuso_local

        fim = self.hoje or datetime.now(fuso_local()).date()
        inicio = fim - timedelta(days=self.dias)

        vistos: dict[int, dict] = {}
        for filtros in CONSULTAS:
            for materia in self._buscar(filtros, inicio, fim):
                codigo = materia.get("cdMateria") or materia.get("id")
                if codigo is not None:
                    vistos.setdefault(codigo, materia)

        itens: list[ItemColetado] = []
        for materia in vistos.values():
            item = self._para_item(materia)
            if item:
                itens.append(item)
        return itens

    def _buscar(self, filtros: dict, inicio: date, fim: date) -> list[dict]:
        materias: list[dict] = []
        for pagina in range(MAXIMO_DE_PAGINAS):
            corpo = {
                "busca": BUSCA,
                "dtIni": inicio.isoformat(),
                "dtFim": fim.isoformat(),
                "tipoBusca": "1",
                "resumo": False,
                "pagination": {"from": pagina * POR_PAGINA, "size": POR_PAGINA},
                **filtros,
            }
            dados = self.post(API, corpo).json() or {}
            if dados.get("error"):
                raise RuntimeError(f"a busca do DOE respondeu erro: {dados.get('error')}")

            # O `total` e o `size` contam ACERTOS da busca, e a API junta os
            # acertos do mesmo ato: 100 acertos podem vir como 28 atos. Pagina
            # curta, entao, nao quer dizer que acabou - o total diz.
            lote = dados.get("materias") or []
            materias.extend(lote)
            total = int(dados.get("total") or 0)
            if not lote or (pagina + 1) * POR_PAGINA >= total:
                break
        return materias

    def _para_item(self, materia: dict) -> ItemColetado | None:
        if materia.get("cancelada") or materia.get("publicada") is False:
            return None
        url = materia.get("extrato")
        if not url:
            return None

        categoria = _limpar(materia.get("categoria"))
        assunto = _limpar(materia.get("assunto"))
        trecho = _limpar(materia.get("resumo"))
        e_edital = normalizar(assunto) in ASSUNTOS_DE_EDITAL

        # Peneira barata, antes de buscar o texto integral: o trecho que a
        # busca devolveu (com a categoria, que diz "Policia Civil" quando o
        # trecho nao diz) tem de falar de concurso e de um cargo do alvo, e
        # ja parecer um dos quatro atos - ou ser, pelo tipo, um edital, cujo
        # trecho costuma vir do meio. Sem isto, cada portaria de nomeacao de
        # "aprovado em concurso publico" da PM custaria uma pagina.
        #
        # O que fica de fora por aqui, medido em 11/10/2026: o edital
        # escaneado so em imagem cujo trecho nao cita o cargo (o de abertura
        # do CBMSC, 27/01/2026, que chega pelo site do IDIB) e as
        # retificacoes de etapa sem a palavra "concurso". Afrouxar a peneira
        # para eles custou 81 paginas por ano e nao trouxe nenhum ato a mais.
        if not re.search(r"\bconcurso\b", normalizar(trecho)):
            return None
        if not alvo.marcar(f"{categoria} {trecho}", uf="SC"):
            return None
        if not (e_edital or que_ato_e(trecho, assunto)):
            return None

        # O texto integral; sem ele (o ato escaneado vem so em imagem), o
        # trecho - que entao e o texto do OCR inteiro.
        paragrafos = self._texto_integral(materia.get("preview"))
        inicio = (" ".join(paragrafos) if paragrafos else trecho)[:INICIO]
        ato = que_ato_e(inicio, assunto)
        if not ato:
            return None
        # O cargo tem de estar no CABECALHO, onde o ato diz de quem e: o
        # edital da Secretaria da Saude de 10/2025 fala em "delegado de
        # policia" la pela pagina 30, num requisito.
        if not alvo.marcar(f"{categoria} {inicio[:CABECALHO_DO_ALVO]}", uf="SC"):
            return None

        publicado = _data(materia.get("publicacao"))
        cabecalho = titulo_do_ato(paragrafos) if paragrafos else titulo_do_ato([trecho])
        titulo = f"{publicado.year} - {cabecalho}" if publicado else cabecalho

        return ItemColetado(
            titulo=titulo,
            url=url,
            # Sem resumo, de proposito. O classificador procura a fase no
            # titulo E no resumo ("previsto", "autorizada"), e o texto de um
            # ato e juridico: "conforme previsto no art. ..." fez do edital da
            # Policia Cientifica um concurso "previsto". O titulo ja diz o
            # orgao e o cargo; o texto integral fica no link do `extra`.
            resumo=None,
            # O diario e do estado: o ato e de SC, sempre. Municipio fica para
            # o classificador, que le o titulo e o resumo.
            uf="SC",
            banca=banca_do_ato(inicio) if ato == CONTRATO else None,
            situacao=SITUACAO_DO_ATO[ato],
            # So passa o que fala de concurso publico; processo seletivo
            # temporario (o da PM com o Idecan, 2025) nao tem a palavra.
            tipo="concurso",
            publicado_em=publicado,
            extra={
                "ato": ato,
                "categoria": categoria,
                "assunto": assunto,
                "edicao": materia.get("nrJornal"),
                "cd_materia": materia.get("cdMateria"),
                "texto_integral": materia.get("preview"),
            },
        )

    def _texto_integral(self, endereco: str | None) -> list[str]:
        """Os paragrafos do ato. Vazio se a pagina nao vier: o trecho da busca
        segura o item."""
        if not endereco:
            return []
        try:
            return _paragrafos(self.get(endereco).text)
        except Exception as erro:  # noqa: BLE001 - uma pagina nao derruba a fonte
            log.debug("texto integral do DOE indisponivel (%s): %s", endereco, erro)
            return []
