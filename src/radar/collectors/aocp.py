"""Fonte 5: Instituto AOCP, pela API que a propria pagina de concursos usa.

Por que esta banca: e a contratada pela PM SC para o concurso do Curso de
Formacao de Pracas (extrato do contrato 098/PMSC/2026, no Diario Oficial do
Estado de 02/07/2026). E banca nacional, entao a lista dela e quase toda de
fora - quem separa o que e de SC e o classificador e o `config/alvo.yml`.

Como foi achada: a pagina /concursos/status/<status> e uma tela em Next.js que
carrega a lista por JavaScript. O codigo dela chama `GET /api/concursos?status=`
(SUBSCRIBE, NEW, IN_PROGRESS, RESULT_AVAILABLE, FINISHED) e, para o detalhe de
um concurso, `GET https://link.institutoaocp.org.br/api/concursos/<id>`. Os dois
devolvem JSON limpo. Nenhum dos dois dominios tem robots.txt (404).

O recorte e o do pedido: so os concursos abertos e em andamento - inscricoes
abertas, novos (edital saiu, inscricao em breve) e em andamento. Os
finalizados e os com resultado ficam de fora: e historico, nao novidade.

O detalhe e um pedido por concurso (uns 35 por coleta) e existe por uma razao:
a lista nao tem DATA. Sem data, a regra do aviso deixa o concurso passar (nao
da para afirmar que e velho), e a primeira coleta mandaria para o celular a
Policia Penal do Parana de 2024, ja com resultado. O detalhe traz as
publicacoes, cada uma com a data no nome, e a mais antiga e o edital de
abertura.
"""
import logging
import re
from datetime import datetime

from radar.collectors.base import Coletor, ItemColetado
from radar.collectors.concursos_no_brasil import ESTADO_PARA_UF, UFS
from radar.regioes import normalizar

log = logging.getLogger(__name__)

LISTA = "https://www.institutoaocp.org.br/api/concursos?status={}"
DETALHE = "https://link.institutoaocp.org.br/api/concursos/{}"
PAGINA = "https://www.institutoaocp.org.br/concursos/{}"

# O status da AOCP e a situacao do radar. "NEW" e o edital que saiu com a
# inscricao para depois ("Divulgado o Edital de Abertura (em breve
# inscricoes)"); "IN_PROGRESS" e o que a FEPESE chama de em andamento.
SITUACAO_POR_STATUS = {
    "SUBSCRIBE": "inscricoes_abertas",
    "NEW": "edital_publicado",
    "IN_PROGRESS": "edital_publicado",
}

BANCA = "Instituto AOCP"

# A chamada da lista e "o concurso" + "o andamento": "Concurso Publico n.
# 001/2026 - Divulgado o Edital de Abertura". O andamento muda a cada etapa;
# o titulo fica so com o comeco, que nao muda. As palavras sairam das 35
# chamadas de 11/10/2026 ("Breve, divulgacao...", "Concurso suspenso...",
# "Edital de Abertura publicado, inscricoes abertas..."); a do Amapa comeca
# direto no andamento, e ai o titulo usa o tipo e o numero.
ANDAMENTO = re.compile(
    r"(?:^|\s*[-–.]\s*)(?:divulgad|em breve|breve|inscri|publicad|resultado|"
    r"convoca|homologa|concurso suspens|suspens|edital de abertura publicad)",
    re.IGNORECASE,
)

# "PREFEITURA MUNICIPAL DE SERRA - ES" -> "SERRA".
PADRAO_MUNICIPIO = re.compile(
    r"^\s*(?:prefeitura\s+municipal\s+de\s+|prefeitura\s+de\s+|"
    r"camara\s+municipal\s+de\s+|municipio\s+de\s+)(.+?)\s*(?:-\s*[a-z]{2}\s*)?$",
    re.IGNORECASE,
)

# A sigla do estado como a AOCP escreve: colada no orgao ("SAD/PE", "IGP-RS")
# ou no fim ("CASAN - ... - SC").
SIGLA_COLADA = re.compile(r"[/-]([A-Z]{2})\b")
SIGLA_NO_FIM = re.compile(r"\s-\s([A-Z]{2})\s*$")

# Nome do estado por extenso, do mais longo para o mais curto: "mato grosso do
# sul" antes de "mato grosso". Exige o "de/do/da" na frente, para "para"
# (preposicao) nao virar o Para.
ESTADOS = sorted(ESTADO_PARA_UF, key=len, reverse=True)
ESTADO_POR_EXTENSO = re.compile(
    r"\bd[eoa]\s+(?:estado\s+d[eoa]\s+)?(" + "|".join(map(re.escape, ESTADOS)) + r")\b"
)


def extrair_uf(nome: str) -> str | None:
    """A UF que o nome do orgao afirma. None quando nao afirma - nunca chute.

    "IPSM - Instituto de Previdencia do Servidor Municipal" nao diz de onde e,
    e "PREFEITURA MUNICIPAL DE CURITIBA" diz a cidade, nao o estado: o
    classificador e quem sabe o que fazer com o municipio.
    """
    for padrao in (SIGLA_NO_FIM, SIGLA_COLADA):
        for achado in padrao.finditer(nome or ""):
            if achado.group(1).lower() in UFS:
                return achado.group(1)
    achado = ESTADO_POR_EXTENSO.search(normalizar(nome))
    return ESTADO_PARA_UF[achado.group(1)] if achado else None


def extrair_municipio(nome: str) -> str | None:
    """O municipio, quando o orgao e prefeitura ou camara. None no resto."""
    achado = PADRAO_MUNICIPIO.match(normalizar(nome))
    if not achado:
        return None
    return achado.group(1).strip(" -,.").upper() or None


def identificacao(chamada: str | None) -> str | None:
    """O comeco da chamada, sem o andamento.

    "Concurso Publico n. 001/2026 - Policia Militar de Pernambuco (PMPE) -
    Divulgado o Edital de Abertura." -> "Concurso Publico n. 001/2026 - Policia
    Militar de Pernambuco (PMPE)".
    """
    texto = " ".join((chamada or "").split())
    if not texto:
        return None
    achado = ANDAMENTO.search(texto)
    comeco = texto[:achado.start()] if achado else texto
    return comeco.strip(" -–.") or None


def detectar_tipo(tipo_escrito: str | None, *textos: str | None) -> str:
    """concurso ou seletivo, pelo que a banca escreveu.

    O `tipoProcesso` manda quando vem ("Concurso para Emprego Publico",
    "Processo Seletivo Simplificado"); vazio - como no da SAP/SC de 2024 -,
    vale o texto da chamada.
    """
    escrito = normalizar(tipo_escrito)
    if escrito:
        return "seletivo" if "seletivo" in escrito else "concurso"
    junto = normalizar(" ".join(t for t in textos if t))
    return "seletivo" if "processo seletivo" in junto else "concurso"


def _data_de(texto: str | None) -> datetime | None:
    """"30/09/2026 - Concurso Publico 001/2026 - Edital de Abertura" -> 30/09/2026."""
    achado = re.match(r"\s*(\d{2})/(\d{2})/(\d{4})\b", texto or "")
    if not achado:
        return None
    from radar.util import fuso_local

    dia, mes, ano = (int(g) for g in achado.groups())
    try:
        return datetime(ano, mes, dia, tzinfo=fuso_local())
    except ValueError:
        return None


def data_do_edital(publicacoes: list[dict] | None, ano: int | None = None) -> datetime | None:
    """A data da publicacao mais antiga, que e o edital de abertura.

    Com o ano do numero do edital, descarta a data de mais de um ano antes
    dele: o Cadete do CBMGO (edital 004/2022) tem uma publicacao datada
    "26/09/2002", que e erro de digitacao.
    """
    datas = [d for d in (_data_de(p.get("nome")) for p in publicacoes or []) if d]
    if ano:
        datas = [d for d in datas if d.year >= ano - 1]
    return min(datas) if datas else None


def _ano(*textos: str | None) -> int | None:
    """O ano do numero do edital: "001/2026" -> 2026."""
    for texto in textos:
        achado = re.search(r"/\s*(\d{4})\b", texto or "")
        if achado:
            return int(achado.group(1))
    return None


class InstitutoAocp(Coletor):
    nome = "aocp"

    def coletar(self) -> list[ItemColetado]:
        itens: list[ItemColetado] = []
        vistos: set[str] = set()

        for status, situacao in SITUACAO_POR_STATUS.items():
            registros = self.get(LISTA.format(status)).json() or []
            for registro in registros:
                item = self._para_item(registro, situacao)
                if item and item.url not in vistos:
                    vistos.add(item.url)
                    itens.append(item)
        return itens

    def _detalhe(self, codigo) -> dict:
        """O detalhe do concurso, ou vazio: sem ele, o item entra sem data."""
        if not isinstance(codigo, int):
            return {}
        try:
            dados = self.get(DETALHE.format(codigo)).json() or []
        except Exception as erro:  # noqa: BLE001 - um detalhe nao derruba a fonte
            log.debug("detalhe %s da AOCP indisponivel: %s", codigo, erro)
            return {}
        return dados[0] if isinstance(dados, list) and dados else {}

    def _para_item(self, registro: dict, situacao: str) -> ItemColetado | None:
        codigo = registro.get("id")
        nome = " ".join((registro.get("nome") or "").split())
        if codigo is None or not nome:
            return None
        # A lista traz um concurso de teste do sistema novo deles
        # ("proseleta-1 | Concurso Publico - 001/2017 - Cliente de Teste").
        if re.search(r"\bteste\b", normalizar(f"{nome} {registro.get('chamada')}")):
            return None

        detalhe = self._detalhe(codigo)
        chamada = registro.get("chamada")
        numero = (registro.get("numeroEdital") or "").strip()
        tipo_escrito = (registro.get("tipoProcesso") or "").strip()

        nome_do_concurso = identificacao(chamada)
        if not nome_do_concurso and (tipo_escrito or numero):
            nome_do_concurso = " ".join(p for p in (tipo_escrito, f"nº {numero}" if numero else "") if p)

        ano_do_numero = _ano(numero, nome_do_concurso)
        publicado = data_do_edital(detalhe.get("publicacoes"), ano_do_numero)
        ano = ano_do_numero or (publicado.year if publicado else None)
        titulo = " - ".join(p for p in (str(ano) if ano else None, nome, nome_do_concurso) if p)

        # A chamada do detalhe diz o que o concurso e ("TORNA PUBLICA a
        # realizacao do PROCESSO SELETIVO SIMPLIFICADO..."), e e com ela que o
        # alvo.yml separa o seletivo da SAP/SC de 2024 do concurso da Policia
        # Penal.
        resumo = " ".join((detalhe.get("chamada") or chamada or "").split()) or None

        return ItemColetado(
            titulo=titulo,
            url=PAGINA.format(codigo),
            resumo=resumo,
            orgao=nome,
            municipio=extrair_municipio(nome),
            uf=extrair_uf(nome),
            banca=BANCA,
            situacao=situacao,
            tipo=detectar_tipo(tipo_escrito, nome_do_concurso, resumo),
            publicado_em=publicado,
            extra={
                "edital": registro.get("edital"),
                "numero_edital": numero or None,
                "status_aocp": registro.get("status"),
                "andamento": " ".join((chamada or "").split()) or None,
                "inscricoes_de": detalhe.get("dataInicioInscricao"),
                "inscricoes_ate": detalhe.get("dataFinalInscricao"),
            },
        )
