"""Le o titulo de um concurso e decide se ele interessa.

Tres perguntas, nesta ordem:
  1. isso e concurso mesmo, ou e noticia que veio junto no feed?
  2. de que municipio e?
  3. esse municipio esta em qual anel de distancia?

A regra de ouro, que vale mais que acertar muito: **nunca chutar**. Quando
nao da para saber, o registro fica `indefinida` e espera a leitura do edital.
Um palpite errado me faria perder um concurso bom achando que era longe.
"""
import re
from dataclasses import dataclass

from radar import alvo as alvos
from radar import regioes
from radar.collectors.base import ItemColetado

# --- tipo -------------------------------------------------------------------

TIPO_CONCURSO, TIPO_SELETIVO = "concurso", "seletivo"
TIPO_DESCONHECIDO, TIPO_NOTICIA = "desconhecido", "noticia"

# Processo seletivo e contratacao temporaria; concurso e efetivo. Como sao
# coisas diferentes, o tipo fica guardado e voce filtra como preferir.
# Os termos sao comparados contra o texto ja normalizado (sem acento, em
# minusculas), entao escreva-os sem acento aqui. Plural conta: "editais" nao
# contem "edital", diferente de "vagas", que contem "vaga".
TERMOS_SELETIVO = ("processo seletivo", "seletivo", "selecao", "selecoes")
TERMOS_CONCURSO = ("concurso", "edital", "editais")
# Sinais de que ha vaga aberta, mesmo sem dizer de que tipo.
TERMOS_VAGA = ("vaga", "inscric", "cargo", "contrata", "oportunidade",
               "chamamento")


# A propria URL ja diz muito. Conferido no site real: post de concurso mora em
# /concursos/UF/ANO/..., enquanto noticia sobre auxilio mora em outro caminho,
# tipo /beneficios-sociais/. Isso e sinal muito mais firme que palavra no
# titulo, e vale ainda mais na carga inicial, que traz milhares de posts.
CAMINHO_DE_CONCURSO = "/concurso"
CAMINHOS_DE_NOTICIA = ("/beneficios-sociais/", "/artigo/", "/escola/", "/dicas/")


def detectar_tipo(
    titulo: str, resumo: str | None = None, url: str | None = None
) -> str:
    """concurso, seletivo, desconhecido ou noticia."""
    endereco = (url or "").lower()

    # Caminho de noticia manda mais que qualquer palavra do titulo: uma
    # materia sobre Bolsa Familia pode citar "vagas" e enganar o filtro.
    if any(caminho in endereco for caminho in CAMINHOS_DE_NOTICIA):
        return TIPO_NOTICIA

    texto = regioes.normalizar(f"{titulo} {resumo or ''}")

    if any(termo in texto for termo in TERMOS_SELETIVO):
        return TIPO_SELETIVO
    if any(termo in texto for termo in TERMOS_CONCURSO):
        return TIPO_CONCURSO
    if any(termo in texto for termo in TERMOS_VAGA):
        # ha vaga, mas o titulo nao diz se e concurso ou seletivo
        return TIPO_DESCONHECIDO
    if CAMINHO_DE_CONCURSO in endereco:
        # o titulo nao deu pista nenhuma, mas o post esta na secao de
        # concursos do site. E melhor tratar como candidato do que descartar.
        return TIPO_DESCONHECIDO
    return TIPO_NOTICIA


# --- em que fase o concurso esta --------------------------------------------
#
# O ciclo de vida do CLAUDE.md so era preenchido depois do edital, pelas datas
# de inscricao. Mas boa parte do que interessa acontece ANTES: o governo
# autoriza, a comissao e formada, a banca e contratada. Tudo isso sai no
# titulo da noticia, e ficava se perdendo como "edital_publicado".
#
# Exemplos reais colhidos no banco:
#   "Policia Militar de Sao Paulo tem novo concurso autorizado com 4 mil vagas"
#   "Concurso DPE SP define FCC como banca para proximo edital"
#   "PGE BA vai contratar banca para novo concurso com 135 vagas"
#   "Concurso Coren SP tem edital previsto para 76 vagas"
#
# A ordem importa: o estado mais adiantado vence. Um titulo que fala de banca
# E de autorizacao esta na fase da banca, que vem depois.
FASES_PELO_TITULO = (
    ("banca_definida", (
        "define banca", "definiu banca", "define a banca", "banca definida",
        "banca sera", "banca e a", "escolhe banca", "escolheu banca",
        "contrata banca", "contratar banca", "banca organizadora",
        "banca contratada", "como banca", "banca do concurso e",
    )),
    ("autorizado", (
        "autorizado", "autorizada", "autoriza concurso", "autoriza novo",
        "tem autorizacao", "recebe autorizacao", "aprovado pelo governo",
    )),
    ("prevista", (
        "previsto", "prevista", "previsao de", "deve sair", "pode sair",
        "expectativa de", "e esperado", "solicita concurso", "pede concurso",
        "estuda concurso", "em estudo", "sem data definida",
    )),
)


def detectar_fase(titulo: str, resumo: str | None = None) -> str | None:
    """A fase que o titulo permite afirmar, ou None se ele nao disser.

    So devolve fase ANTERIOR ao edital. Depois que o edital sai, quem manda
    sao as datas de inscricao, que sao fato e nao interpretacao.
    """
    texto = regioes.normalizar(f"{titulo} {resumo or ''}")

    # "edital publicado" vence qualquer pista de fase anterior: se o edital
    # saiu, nao interessa que a noticia tambem lembre da autorizacao.
    if "edital publicado" in texto or "publica edital" in texto:
        return None

    for fase, marcas in FASES_PELO_TITULO:
        if any(marca in texto for marca in marcas):
            return fase
    return None


# --- orgao estadual ---------------------------------------------------------

# Orgao que serve o estado inteiro: nao tem municipio no titulo, e a prova
# costuma ser aplicada em varios polos - nenhum deles garantido. Reconhece-lo
# evita dois erros opostos: chutar `nucleo` porque a sede e em Florianopolis,
# e enterrar em `indefinida` justamente as carreiras que eu mais quero.
#
# A lista e curta de proposito, so o que eu sei nomear com certeza. Autarquia
# (Celesc, Casan, Udesc, TJSC) continua em `indefinida` ate eu ler o edital:
# incluir por semelhanca seria o mesmo chute que a regra existe para impedir.
# Os termos sao comparados contra o texto normalizado, entao va sem acento.
ORGAOS_ESTADUAIS = (
    "secretaria de estado",
    "governo do estado",
    "policia civil",
    "policia militar",
    "policia penal",
    "policia cientifica",
    "corpo de bombeiros",
)


def e_orgao_estadual(titulo: str) -> bool:
    """O titulo nomeia um orgao de governo estadual?

    Diz so isso - NAO diz de qual estado. Quem sabe a UF e a fonte: a FEPESE
    so organiza concurso estadual em SC, e o feed nacional escreve "(SC)".

    Sao duas listas, porque cada fonte escreve de um jeito. A de cima pega o
    nome por extenso, que e como a FEPESE titula ("Secretaria de Estado da
    Administracao Prisional"). A de config/alvo.yml pega a SIGLA, que e como o
    agregador titula ("SEJURI SC divulga novo edital") - e sigla nenhuma casa
    com "secretaria de estado", entao os dois concursos da SEJURI ficavam em
    `indefinida` mesmo tendo uf=SC.
    """
    texto = regioes.normalizar(titulo)
    if any(termo in texto for termo in ORGAOS_ESTADUAIS):
        return True
    return alvos.nomeia_orgao_do_principal(titulo)


# --- municipio --------------------------------------------------------------

# O feed escreve o municipio antes da sigla entre parenteses:
#   "Concurso Prefeitura de Tunapolis (SC) tem salario de R$ 5.832"
PADRAO_ANTES_DA_UF = re.compile(r"([^()]{3,70}?)\s*\(([A-Z]{2})\)")

# Palavras que abrem o titulo e nao fazem parte do nome do orgao.
RUIDO_INICIAL = re.compile(
    r"^(concurso|edital|seletivo|processo seletivo|novo concurso|vagas?|"
    r"inscricoes|inscrições)\s+",
    re.IGNORECASE,
)

# "Prefeitura de X", "Camara Municipal de X", "EMDURB de X" -> X.
# O `.*?` e preguicoso para casar o PRIMEIRO "de/da/do": sem isso,
# "Prefeitura de Sao Lourenco do Oeste" viraria so "Oeste".
SEPARADOR_ORGAO = re.compile(r"^.*?\s+(?:de|da|do)\s+(.+)$", re.IGNORECASE)


def extrair_municipio(titulo: str) -> str | None:
    """O municipio escrito no titulo, ou None se nao der para ter certeza."""
    achado = PADRAO_ANTES_DA_UF.search(titulo or "")
    if not achado:
        return None

    trecho = achado.group(1).strip()
    trecho = RUIDO_INICIAL.sub("", trecho).strip()

    partes = SEPARADOR_ORGAO.match(trecho)
    if not partes:
        # Sobrou so o nome do orgao, sem "de": FUNCAMP, AgSUS e afins.
        # Nao ha municipio a extrair, e inventar um seria pior que nao ter.
        return None

    municipio = partes.group(1).strip(" -–—,")
    return municipio or None


# --- salario ----------------------------------------------------------------

PADRAO_SALARIO = re.compile(r"R\$\s*(\d[\d.,]*)\s*(mil)?", re.IGNORECASE)


def _para_numero(bruto: str, tem_mil: bool) -> float | None:
    texto = bruto.strip().rstrip(".,")
    try:
        if tem_mil:
            # "4,5 mil" -> 4.5 * 1000
            return float(texto.replace(".", "").replace(",", ".")) * 1000
        if "," in texto:
            # "1.234,56" -> ponto e milhar, virgula e decimal
            return float(texto.replace(".", "").replace(",", "."))
        if re.fullmatch(r"\d{1,3}(\.\d{3})+", texto):
            # "5.832" -> ponto e separador de milhar
            return float(texto.replace(".", ""))
        return float(texto)
    except ValueError:
        return None


def extrair_salario(titulo: str) -> float | None:
    """O maior valor em R$ citado no titulo.

    E so uma estimativa para ordenar a lista: o titulo costuma trazer o teto
    ("ate R$ 6,2 mil"). O valor que vale e o do edital, lido na fase 2.5.
    """
    valores = [
        valor
        for bruto, mil in PADRAO_SALARIO.findall(titulo or "")
        if (valor := _para_numero(bruto, bool(mil))) is not None
    ]
    return max(valores) if valores else None


# --- a decisao --------------------------------------------------------------

@dataclass
class Classificacao:
    relevancia: str
    motivo: str
    municipio: str | None = None
    salario: float | None = None
    tipo: str = TIPO_DESCONHECIDO
    # Fase anterior ao edital, quando o titulo deixa claro. Nulo quer dizer
    # "o titulo nao disse", e ai o que valia antes continua valendo.
    fase: str | None = None
    # O cargo e meu alvo? Sai de config/alvo.yml. Nulo = nao e cargo meu.
    alvo: str | None = None
    motivo_alvo: str | None = None
    # Fura o teto de avisos por si so. Hoje so a lista `de_olho` liga isto.
    alvo_prioritario: bool = False


def classificar(item: ItemColetado) -> Classificacao:
    # Fonte que sabe manda: a FEPESE publica concurso num tipo de post
    # proprio, entao nao ha o que adivinhar pelo titulo.
    tipo = item.tipo or detectar_tipo(item.titulo, item.resumo, item.url)
    # Sempre na grafia do YAML: fonte diferente escreve o mesmo municipio de
    # jeito diferente, e agrupar por municipio depois nao fecharia.
    municipio = regioes.nome_canonico(
        item.municipio or extrair_municipio(item.titulo)
    )
    salario = extrair_salario(item.titulo)
    uf = (item.uf or "").upper()

    # A marca de alvo e independente do anel: ela responde "e o cargo que eu
    # quero?", e o anel responde "da para chegar la?". Por isso ela e
    # calculada aqui em cima e vale para todas as saidas, inclusive a de
    # noticia - noticia sobre a Policia Penal SC e justamente o que eu quero
    # saber antes de todo mundo.
    # O municipio ja canonizado vai junto por causa da lista `de_olho`: e o
    # unico lugar em que a CIDADE decide alguma coisa na marca de alvo, e o
    # titulo nem sempre a repete ("Prefeitura de Florianopolis abre concurso
    # para Guarda Municipal" traz a cidade so aqui).
    marca = alvos.marcar(
        item.titulo,
        item.resumo,
        uf=item.uf,
        banca=item.banca,
        municipio=municipio,
    )

    comum = dict(
        municipio=municipio,
        salario=salario,
        tipo=tipo,
        fase=detectar_fase(item.titulo, item.resumo),
        alvo=marca.alvo if marca else None,
        motivo_alvo=marca.motivo if marca else None,
        alvo_prioritario=bool(marca and marca.prioritario),
    )

    if tipo == TIPO_NOTICIA:
        return Classificacao(
            regioes.INDEFINIDA,
            "Não parece concurso: o título não fala em vaga, edital nem inscrição.",
            **comum,
        )

    # O anel decide antes da UF quando o municipio e conhecido. A lista de
    # config/regioes.yml so tem municipio catarinense, entao achar um nome ali
    # ja prova que e SC - mesmo que a fonte nao tenha dito a UF, como acontece
    # com a API da FEPESE. So nao vale se a fonte afirmar OUTRO estado: "Sao
    # Jose" e nome de municipio em varios lugares do Brasil.
    if uf in ("", "SC"):
        anel = regioes.anel_de(municipio)
        if anel:
            return Classificacao(
                anel,
                f"{municipio} (SC) está no anel "
                f"{regioes.NOME_DO_ANEL.get(anel, anel)}.",
                **comum,
            )

    # Orgao estadual de SC: nao tem municipio, e o edital e que dira onde sao
    # os polos de prova. Fica num anel proprio em vez de `indefinida` - eu
    # presto concurso estadual onde for, entao ele nao pode sumir da lista.
    if uf == "SC" and e_orgao_estadual(item.titulo):
        return Classificacao(
            regioes.ESTADUAL,
            "Órgão estadual de SC; polos de prova a confirmar no edital.",
            **comum,
        )

    if uf == "SC":
        if municipio:
            return Classificacao(
                regioes.REMOTO,
                f"{municipio} fica em SC mas fora dos anéis de config/regioes.yml.",
                **comum,
            )
        return Classificacao(
            regioes.INDEFINIDA,
            "Concurso de SC, mas não identifiquei o município no título.",
            **comum,
        )

    if uf:
        if municipio:
            return Classificacao(
                regioes.REMOTO,
                f"Órgão de {municipio} ({uf}): prova aplicada fora de SC.",
                **comum,
            )
        return Classificacao(
            regioes.INDEFINIDA,
            f"Concurso de {uf} sem município no título; depende de ler o edital.",
            **comum,
        )

    return Classificacao(
        regioes.INDEFINIDA,
        "Sem UF: pode ser federal com prova em Florianópolis. Depende do edital.",
        **comum,
    )
