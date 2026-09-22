"""Fonte 2: FEPESE, pela API REST do WordPress dela.

Por que esta fonte, e por que ela e diferente da primeira:

A FEPESE e a banca que mais faz concurso em Santa Catarina, e o site dela expoe
os concursos como JSON estruturado em /wp-json/wp/v2/concurso. Isso e melhor
que agregador em tres pontos:

  1. **a banca ja e conhecida** - nao precisa adivinhar lendo pagina;
  2. **o status vem da propria banca**, numa taxonomia fechada ("Inscricoes
     abertas", "Em andamento", "Encerrados"), em vez de ser deduzido de datas
     que alguem escreveu em texto corrido;
  3. **a escolaridade exigida vem junto**, que e um dos meus criterios.

De quebra, cada concurso traz o `link_hotsite` - o endereco onde a FEPESE
publica edital, provas e gabaritos. E dali que a fase 3 vai montar o acervo.

Sobre o diario oficial, que era o plano original desta fase: o DOM/SC proibe
robo no robots.txt ("User-agent: * / Disallow: /", so o Bingbot passa), entao
esta fora. O detalhe esta no README.
"""
import html
import logging
import re
from datetime import datetime

from radar.classificador import e_orgao_estadual
from radar.collectors.base import Coletor, ItemColetado

log = logging.getLogger(__name__)

API = "https://fepese.org.br/wp-json/wp/v2"

# O WordPress aceita ate 100 por pagina. Sao ~520 concursos no total, entao a
# coleta inteira sai em 6 requisicoes.
POR_PAGINA = 100

# Teto de seguranca, caso o site passe a devolver paginacao sem fim.
MAXIMO_DE_PAGINAS = 20

# Como o status da FEPESE vira o `situacao` do radar. O que nao estiver aqui
# fica `desconhecida` - inventar um estado seria pior que admitir que nao sei.
SITUACAO_POR_STATUS = {
    "inscricoes abertas": "inscricoes_abertas",
    "reinscricoes abertas": "inscricoes_abertas",
    "em andamento": "edital_publicado",
    "encerrados": "encerrado",
    "encerrado": "encerrado",
}

# Os titulos seguem "2026 - Prefeitura Municipal de Sao Jose". O municipio vem
# depois do nome do orgao.
PADRAO_ORGAO = re.compile(
    r"^\s*(?:\d{4}\s*[-–]\s*)?"                  # o ano, quando tem
    r"(?:prefeitura\s+municipal\s+de\s+|prefeitura\s+de\s+|"
    r"camara\s+municipal\s+de\s+|camara\s+de\s+|"
    r"municipio\s+de\s+)"
    r"(.+?)\s*$",
    re.IGNORECASE,
)


def _limpar(texto: str) -> str:
    """Tira entidade HTML e tag do titulo que o WordPress devolve."""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", texto or ""))).strip()


def _sem_acento(texto: str) -> str:
    import unicodedata

    normal = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in normal if not unicodedata.combining(c))


def extrair_municipio(titulo: str) -> str | None:
    """O municipio do titulo, quando o orgao e uma prefeitura ou camara.

    "2026 - Prefeitura Municipal de Sao Jose" -> "Sao Jose".

    Orgao que nao e municipal (Celesc, UFSC, governo do estado) nao tem
    municipio no titulo, e ai devolve None em vez de chutar.
    """
    achado = PADRAO_ORGAO.match(_sem_acento(_limpar(titulo)))
    if not achado:
        return None

    municipio = achado.group(1).strip(" -–—,.")
    # sobra de subtitulo: "Sao Jose - Processo Seletivo 2026"
    municipio = re.split(r"\s+[-–]\s+", municipio)[0].strip()
    return municipio or None


def _data(texto: str | None) -> datetime | None:
    if not texto:
        return None
    try:
        # o WordPress manda "2026-09-16T10:30:00" sem fuso; e horario local
        from radar.util import fuso_local

        return datetime.fromisoformat(texto).replace(tzinfo=fuso_local())
    except ValueError:
        return None


class Fepese(Coletor):
    nome = "fepese"

    def __init__(self, paginas: int = MAXIMO_DE_PAGINAS) -> None:
        super().__init__()
        self.paginas = max(1, min(paginas, MAXIMO_DE_PAGINAS))

    def _termos(self, taxonomia: str) -> dict[int, str]:
        """{id: nome} de uma taxonomia. Sao poucos termos e mudam quase nunca."""
        resposta = self.get(f"{API}/{taxonomia}?per_page=100")
        return {termo["id"]: termo["name"] for termo in resposta.json()}

    def coletar(self) -> list[ItemColetado]:
        status = self._termos("tax_concurso_status")
        escolaridades = self._termos("tax_escolaridade")

        itens: list[ItemColetado] = []
        for pagina in range(1, self.paginas + 1):
            resposta = self.get(f"{API}/concurso?per_page={POR_PAGINA}&page={pagina}")
            registros = resposta.json()
            if not registros:
                break

            for registro in registros:
                item = self._para_item(registro, status, escolaridades)
                if item:
                    itens.append(item)

            # O proprio WordPress diz quantas paginas existem.
            total = int(resposta.headers.get("X-WP-TotalPages", 0) or 0)
            if total and pagina >= total:
                break

        return itens

    def _para_item(
        self, registro: dict, status: dict[int, str], escolaridades: dict[int, str]
    ) -> ItemColetado | None:
        titulo = _limpar(registro.get("title", {}).get("rendered", ""))
        url = registro.get("link")
        if not titulo or not url:
            return None

        nomes_status = [
            _sem_acento(status[i]).lower()
            for i in registro.get("tax_concurso_status", [])
            if i in status
        ]
        # "Inscricoes abertas" vence "Em andamento" quando os dois vem juntos:
        # o estado mais adiantado e o que vale.
        situacao = "desconhecida"
        for nome in ("inscricoes abertas", "reinscricoes abertas", "em andamento",
                     "encerrados"):
            if nome in nomes_status:
                situacao = SITUACAO_POR_STATUS[nome]
                break

        escolaridade = ", ".join(
            escolaridades[i]
            for i in registro.get("tax_escolaridade", [])
            if i in escolaridades
        ) or None

        # Isto veio do tipo de post `concurso` da FEPESE: nunca e noticia. So
        # falta separar concurso efetivo de processo seletivo temporario.
        texto = _sem_acento(f"{titulo} {registro.get('slug', '')}").lower()
        tipo = "seletivo" if "seletivo" in texto or "selecao" in texto else "concurso"

        # A API nao manda UF nenhuma, e o titulo de orgao estadual nao tem
        # municipio para o classificador achar - "2019 - Secretaria de Estado
        # da Administracao Prisional e Socioeducativa" ficava como "pode ser
        # federal". Aqui a UF e dedutivel da fonte: a FEPESE e a fundacao da
        # UFSC e so organiza concurso estadual em SC. Conferido nos 520
        # concursos do historico dela: os 16 de orgao estadual sao todos de
        # SC, e o unico concurso fora do estado e municipal (Paraiso do
        # Tocantins, 2023). Prefeitura continua sem UF de proposito - o nome
        # do municipio e que decide o anel.
        uf = "SC" if e_orgao_estadual(titulo) else None

        return ItemColetado(
            titulo=titulo,
            url=url,
            tipo=tipo,
            # A banca vem de graca: e o site dela.
            banca="FEPESE",
            municipio=extrair_municipio(titulo),
            uf=uf,
            situacao=situacao,
            escolaridade=escolaridade,
            publicado_em=_data(registro.get("date")),
            extra={
                # Onde a FEPESE publica edital, prova e gabarito. E daqui que a
                # fase 3 vai montar o acervo.
                "hotsite": (registro.get("acf") or {}).get("link_hotsite"),
                "escolaridade": escolaridade,
                "status_fepese": nomes_status,
            },
        )
