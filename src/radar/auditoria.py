"""Auditoria automatica das provas do alvo: o banco confere com os PDFs?

Tres perguntas, uma por prova, e todas respondidas lendo o PDF oficial de
novo - nada conferido a mao, nada digitado aqui:

  1. **a contagem por materia** do banco bate com o quadro do edital?
  2. **o gabarito que vale** (o ultimo definitivo publicado) e o que esta no
     banco, letra por letra?
  3. **as anuladas** do definitivo estao marcadas no banco, e so elas?

O que esta auditoria NAO prova, e precisa estar escrito: ela usa o mesmo
leitor de PDF que montou o banco (`questoes.extrair_texto` e a grade do
`gabarito`). Se o leitor errar do mesmo jeito nas duas pontas, os dois lados
batem e o erro passa. O que ela pega e o banco velho, a grade errada
aplicada, a retificacao que nao entrou e a materia que ganhou ou perdeu
questao na separacao do caderno.
"""
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from sqlalchemy import select

from radar import alvo, config, gabarito
from radar import provas as arquivos_de_prova
from radar.db import criar_tabelas, sessao
from radar.edital_materias import MateriaDoEdital, arrumar_nome
from radar.models import QuestaoDeProva


def caminho_padrao() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "docs" / "auditoria.md"


# A linha que o `relatorio` escreve no topo: "> Gerado por `radar auditar` em
# 25/09/2026. ...". E dela que a tela Mais tira a data.
DATA_DO_RELATORIO = re.compile(r"Gerado por .*? em (\d{2}/\d{2}/\d{4})")


def data_do_relatorio(caminho: Path | None = None) -> str | None:
    """"DD/MM/AAAA" de quando o relatorio foi gerado, ou None.

    Lida do cabecalho do proprio arquivo, e nao da data de modificacao: um
    `git pull` muda a data do arquivo sem ninguem ter auditado nada.
    """
    origem = caminho or caminho_padrao()
    if not origem.exists():
        return None
    for linha in origem.read_text(encoding="utf-8").splitlines()[:5]:
        achado = DATA_DO_RELATORIO.search(linha)
        if achado:
            return achado.group(1)
    return None


def _normalizar(texto: str | None) -> str:
    normal = unicodedata.normalize("NFKD", texto or "")
    sem_acento = "".join(c for c in normal if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", sem_acento).strip().lower()


# --- o quadro do edital, em qualquer dos dois formatos ----------------------
#
# O `edital_materias.ler_quadro` le o quadro de 2019 e o de 2016, e nao o de
# 2013: la o valor da questao vem sem os dois decimais ("0,1" e "1"), o nome
# da materia quebra em duas linhas ("Noções de\nInformática"), e o mesmo
# edital traz DOIS quadros, um por cargo. Mexer no leitor do Meu foco para
# isso seria arriscar a tela que funciona; a auditoria tem o seu.

# "Língua Portuguesa 10 0,1 1" com o texto ja numa linha so: nome sem digito,
# questoes, valor da questao, total da materia.
LINHA = re.compile(
    r"([^\d]{3,160}?)\s+(\d{1,3})\s+(\d{1,2},\d{1,2})\s+(\d{1,3}(?:,\d{1,2})?)"
    r"(?=\s|$)"
)

# Onde o quadro comeca: o cabecalho das colunas. Os tres editais escrevem
# "N° DE QUESTÕES VALOR DA QUESTÃO TOTAL".
CABECALHO_DO_QUADRO = re.compile(r"(?i)valor\s+da\s+quest[aã]o\s+total")

# O fecho, quando o edital escreve: "TOTAL 100 10,00" ou "TOTAIS 70 10". O de
# 2016 nao escreve, e ai a unica conferencia e o numero de questoes.
FECHO = re.compile(r"\s*\bTOTA(?:L|IS)\s+(\d{1,3})\b")

# Entre uma linha e a seguinte pode cair um rodape de pagina ("[10]",
# "Página | 12"). Mais do que isto de distancia ja e outro trecho do edital.
SALTO_MAXIMO = 160

# O que gruda antes do nome da materia: o resto do cabecalho, o grupo
# ("CONHECIMENTOS GERAIS", "Conhecimentos específicos") e o cabecalho de
# pagina ("ESTADO DE SANTA CATARINA SECRETARIA ..."), todo em maiuscula.
# Materia e escrita em caixa normal, e e isso que as separa.
LIXO_ANTES_DO_NOME = re.compile(
    r"^(?:.*\bTOTAL\b)?[\s|:\]]*"
    r"(?:[A-ZÀ-Ý°º]+(?=[\s|:])[\s|:]*)*"
    r"(?:(?i:conhecimentos\s+(?:gerais|espec\w+))\s+(?=\S))?"
)


@dataclass
class Quadro:
    """Um quadro de distribuicao de questoes, e o texto que vem antes dele."""

    materias: list[MateriaDoEdital]
    total: int
    #: O trecho logo antes do quadro. E nele que o edital de varios cargos
    #: diz de qual cargo o quadro e ("Para o cargo de Agente Penitenciário").
    contexto: str


def ler_quadros(texto: str, quantas: int) -> list[Quadro]:
    """Os quadros do edital que somam exatamente `quantas` questoes.

    Quem garante que o quadro foi lido certo e a conta: a partir do
    cabecalho, as linhas sao somadas ate dar o numero de questoes do caderno.
    Passou do numero, ou acabaram as linhas antes, o quadro e descartado
    inteiro; e se o edital escreve o TOTAL logo depois, ele tambem tem que
    bater. Nunca chutar - um peso errado aqui diria que o banco esta errado
    quando nao esta, ou o contrario.
    """
    corrido = re.sub(r"\s+", " ", texto or "")
    quadros = []
    for cabecalho in CABECALHO_DO_QUADRO.finditer(corrido):
        posicao, soma, materias = cabecalho.end(), 0, []
        while soma < quantas:
            linha = LINHA.search(corrido, posicao, posicao + SALTO_MAXIMO + 160)
            if linha is None or linha.start() - posicao > SALTO_MAXIMO:
                break
            nome = arrumar_nome(LIXO_ANTES_DO_NOME.sub("", linha.group(1)))
            materias.append(MateriaDoEdital(nome=nome, questoes=int(linha.group(2))))
            soma += int(linha.group(2))
            posicao = linha.end()
        if soma != quantas:
            continue
        fecho = FECHO.match(corrido, posicao)
        if fecho and int(fecho.group(1)) != soma:
            continue
        quadros.append(Quadro(
            materias=materias, total=soma,
            contexto=corrido[max(0, cabecalho.start() - 300):cabecalho.start()],
        ))
    return quadros


def _nucleo_do_cargo(cargo: str | None) -> str:
    """"Agente Penitenciário - Feminino (AP)" -> "agente penitenciario"."""
    sem_sigla = re.sub(r"\(.*?\)", "", cargo or "")
    return _normalizar(sem_sigla.split(" - ")[0])


def quadro_do_cargo(quadros: list[Quadro], cargo: str | None) -> Quadro | None:
    """O quadro do caderno: o total bate e, havendo mais de um, o cargo tambem.

    O edital de 2013 tem dois quadros de 70 questoes, AP e AS. So o total nao
    separa os dois; o nome do cargo no trecho antes do quadro separa.
    """
    candidatos = quadros
    if len(candidatos) <= 1:
        return candidatos[0] if candidatos else None
    nucleo = _nucleo_do_cargo(cargo)
    do_cargo = [q for q in candidatos if nucleo and nucleo in _normalizar(q.contexto)]
    return do_cargo[-1] if len(do_cargo) >= 1 else None


# --- a prova auditada -------------------------------------------------------

@dataclass
class LinhaDaContagem:
    edital: str | None
    no_edital: int | None
    caderno: str | None
    no_caderno: int | None
    ordem_edital: int | None = None
    ordem_caderno: int | None = None

    @property
    def bate(self) -> bool:
        return self.no_edital == self.no_caderno

    @property
    def nome_bate(self) -> bool:
        """O nome, sem acento, caixa nem espaco. "Direito P rocessual" e
        "Direito Processual" sao o mesmo; "Processo" e "Processual" nao."""
        return _chave(self.edital) == _chave(self.caderno)


@dataclass
class ProvaAuditada:
    prova_url: str
    ano: int | None
    cargo: str | None
    reforco: bool
    questoes: int
    edital_lido: str | None = None
    contagem: list[LinhaDaContagem] = field(default_factory=list)
    gabarito_que_vale: str | None = None
    gabarito_publicado_em: str | None = None
    definitivos_lidos: list[str] = field(default_factory=list)
    #: (numero, o que o banco diz, o que o definitivo diz)
    divergencias: list[tuple[int, str, str]] = field(default_factory=list)
    anuladas_oficiais: list[int] = field(default_factory=list)
    anuladas_no_banco: list[int] = field(default_factory=list)
    trocadas_pelo_definitivo: list[int] = field(default_factory=list)
    materia_da_questao: dict[int, str] = field(default_factory=dict)

    @property
    def problemas(self) -> list[str]:
        """Onde os numeros nao batem, em frases. Vazio quando tudo bate."""
        achados = []
        if not self.edital_lido:
            achados.append("nenhum edital do acervo tem um quadro que feche "
                           f"{self.questoes} questoes para este cargo")
        for linha in self.contagem:
            if not linha.bate:
                achados.append(
                    f"{linha.edital or linha.caderno}: edital promete "
                    f"{linha.no_edital if linha.no_edital is not None else '-'}, "
                    f"o banco tem {linha.no_caderno if linha.no_caderno is not None else '-'}"
                )
        if not self.gabarito_que_vale:
            achados.append("nenhum gabarito definitivo do acervo e deste caderno")
        for numero, banco, oficial in self.divergencias:
            achados.append(f"questao {numero}: banco diz {banco}, definitivo diz {oficial}")
        return achados

    @property
    def nomes_diferentes(self) -> list[LinhaDaContagem]:
        return [l for l in self.contagem if l.bate and not l.nome_bate]

    @property
    def fora_de_ordem(self) -> list[LinhaDaContagem]:
        """Materia que o caderno poe em outra posicao que a do edital."""
        return [l for l in self.contagem
                if l.ordem_edital and l.ordem_caderno
                and l.ordem_edital != l.ordem_caderno]


def _caminho(registro: dict) -> Path | None:
    if not registro.get("caminho"):
        return None
    caminho = config.diretorio_dados() / registro["caminho"]
    return caminho if caminho.exists() else None


def _do_mesmo_concurso(registros: list[dict], tipo: str) -> list[dict]:
    """Os documentos de um tipo, sem repetir o mesmo PDF baixado duas vezes.

    O concurso de 2019 aparece com dois enderecos no hotsite, e o manifesto
    tem o mesmo arquivo em duas pastas. O sha256 diz que e um so.
    """
    vistos, unicos = set(), []
    for r in registros:
        if r.get("tipo") != tipo or not _caminho(r):
            continue
        if r.get("sha256") in vistos:
            continue
        vistos.add(r.get("sha256"))
        unicos.append(r)
    return unicos


def _auditar_contagem(prova: ProvaAuditada, editais: list[dict],
                      questoes: list) -> None:
    from radar.questoes import extrair_texto

    quadro = None
    for registro in sorted(editais, key=lambda r: (r.get("publicado_em") or "",
                                                   r.get("arquivo") or "")):
        quadro = quadro_do_cargo(
            ler_quadros(extrair_texto(_caminho(registro)), prova.questoes),
            prova.cargo,
        )
        if quadro:
            prova.edital_lido = registro.get("arquivo")
            break

    # O caderno em blocos de materia, na ordem das questoes.
    blocos: list[list] = []
    for q in sorted(questoes, key=lambda q: q.numero):
        if blocos and blocos[-1][0] == q.materia:
            blocos[-1][1] += 1
        else:
            blocos.append([q.materia, 1])

    do_edital = list(quadro.materias) if quadro else []
    pares = _parear(do_edital, blocos)
    for m, b in pares:
        prova.contagem.append(LinhaDaContagem(
            edital=m.nome if m else None,
            no_edital=m.questoes if m else None,
            caderno=b[0] if b else None,
            no_caderno=b[1] if b else None,
            ordem_edital=do_edital.index(m) + 1 if m else None,
            ordem_caderno=blocos.index(b) + 1 if b else None,
        ))


def _chave(nome: str | None) -> str:
    return re.sub(r"[^a-z]", "", _normalizar(nome))


# Quao parecidos dois nomes precisam ser para serem a mesma materia.
# "Direito Processo Penal" x "Direito Processual Penal" da 0,90;
# "Legislacao Estadual" x "Legislacao Especial" da 0,78 e NAO pode casar.
PARECIDO_O_BASTANTE = 0.85


def _parear(do_edital: list, blocos: list) -> list[tuple]:
    """Cada materia do edital com o bloco do caderno que e ela.

    Pelo NOME, e nao pela ordem: em 2016 o caderno poe Legislacao Estadual
    antes de Processual Penal, e parear pela posicao acusaria duas
    contagens erradas que estao certas. Tres passadas, da mais exigente para
    a mais frouxa: nome igual; um nome termina com o outro ("Direito da
    Criança e do Adolescente- Lei do Sinase" e "Lei do Sinase"); e nome quase
    igual ("Processo" e "Processual"). O que sobrar fica sozinho na linha -
    e isso e um achado, nao um erro do pareamento.
    """
    from difflib import SequenceMatcher

    livres = list(blocos)
    pares = []

    def casa(m, criterio):
        for b in livres:
            if criterio(_chave(m.nome), _chave(b[0])):
                livres.remove(b)
                return b
        return None

    criterios = [
        lambda a, b: a == b,
        lambda a, b: bool(a and b) and (a.endswith(b) or b.endswith(a)),
        lambda a, b: SequenceMatcher(None, a, b).ratio() >= PARECIDO_O_BASTANTE,
    ]
    achado = {id(m): None for m in do_edital}
    for criterio in criterios:
        for m in do_edital:
            if achado[id(m)] is None:
                achado[id(m)] = casa(m, criterio)

    pares = [(m, achado[id(m)]) for m in do_edital]
    pares += [(None, b) for b in livres]
    return pares


def _grade_do_caderno(caminho: Path, registro: dict, quantas: int):
    return next(
        (g for g in gabarito.ler_grades_do_pdf(caminho)
         if gabarito.e_deste_caderno(g, registro.get("cargo") or registro.get("_cargo"),
                                     registro.get("arquivo") or "", quantas)),
        None,
    )


def _auditar_gabarito(prova: ProvaAuditada, registro_da_prova: dict,
                      definitivos: list[dict], provisorios: list[dict],
                      questoes: list) -> None:
    quantas = len(questoes)
    vale = None
    for registro in sorted(definitivos, key=lambda r: r.get("publicado_em") or ""):
        grade = _grade_do_caderno(_caminho(registro), registro_da_prova, quantas)
        if grade is None:
            continue
        prova.definitivos_lidos.append(
            f"{registro.get('arquivo')} ({registro.get('publicado_em') or 'sem data'})"
        )
        vale = grade
        prova.gabarito_que_vale = registro.get("arquivo")
        prova.gabarito_publicado_em = registro.get("publicado_em")

    prova.anuladas_no_banco = sorted(q.numero for q in questoes if q.anulada)
    if vale is None:
        return
    prova.anuladas_oficiais = sorted(vale.anuladas)

    for q in sorted(questoes, key=lambda q: q.numero):
        banco = "anulada" if q.anulada else (q.resposta or "sem resposta")
        oficial = ("anulada" if q.numero in vale.anuladas
                   else vale.respostas.get(q.numero, "ausente da grade"))
        if banco != oficial:
            prova.divergencias.append((q.numero, banco, oficial))

    # Quanto o definitivo mudou do provisorio. Nao e erro - e o tamanho do
    # estrago que treinar pelo caderno teria feito.
    for registro in provisorios:
        provisoria = _grade_do_caderno(_caminho(registro), registro_da_prova, quantas)
        if provisoria is None:
            continue
        prova.trocadas_pelo_definitivo = sorted(
            n for n, letra in vale.respostas.items()
            if provisoria.respostas.get(n) not in (None, letra)
        )
        break


def auditar() -> list[ProvaAuditada]:
    """As provas do cargo no meu estado, e as de reforco, conferidas."""
    # A mesma pergunta que o Meu foco faz: e o meu cargo E o meu estado?
    # Reusar e o que garante que a auditoria olha as provas que a tela usa.
    from radar.foco import _provas_do_alvo

    criar_tabelas()
    manifesto = arquivos_de_prova.carregar_manifesto()

    with sessao() as s:
        do_alvo = _provas_do_alvo(s)
        todas = list(s.scalars(select(QuestaoDeProva)))

    por_prova: dict[str, list] = {}
    for q in todas:
        por_prova.setdefault(q.prova_url, []).append(q)

    auditadas = []
    for url, questoes in por_prova.items():
        exemplo = questoes[0]
        reforco = alvo.e_reforco(exemplo.cargo, exemplo.ano)
        if url not in do_alvo and not reforco:
            continue

        prova = ProvaAuditada(
            prova_url=url, ano=exemplo.ano, cargo=exemplo.cargo,
            reforco=reforco, questoes=len(questoes),
            materia_da_questao={q.numero: q.materia for q in questoes},
        )
        registros_da_prova = [r for r in manifesto if r.get("url") == url]
        concursos = {r.get("concurso_url") for r in registros_da_prova}
        do_concurso = [r for r in manifesto if r.get("concurso_url") in concursos]
        registro_da_prova = dict(registros_da_prova[0]) if registros_da_prova else {}
        registro_da_prova["_cargo"] = exemplo.cargo

        _auditar_contagem(
            prova, _do_mesmo_concurso(do_concurso, arquivos_de_prova.EDITAL),
            questoes,
        )
        _auditar_gabarito(
            prova, registro_da_prova,
            _do_mesmo_concurso(do_concurso, arquivos_de_prova.GABARITO_DEFINITIVO),
            _do_mesmo_concurso(do_concurso, arquivos_de_prova.GABARITO),
            questoes,
        )
        auditadas.append(prova)

    return sorted(auditadas, key=lambda p: (p.reforco, p.ano or 0))


# --- o relatorio ------------------------------------------------------------

def _numeros(lista: list[int], materias: dict[int, str]) -> str:
    if not lista:
        return "nenhuma"
    return ", ".join(f"{n} ({materias.get(n) or '?'})" for n in lista)


def _secao(prova: ProvaAuditada) -> list[str]:
    marca = " — REFORCO (outro cargo; nunca somada as do alvo)" if prova.reforco else ""
    linhas = [
        f"## {prova.ano} · {prova.cargo}{marca}",
        "",
        f"Caderno: <{prova.prova_url}> — {prova.questoes} questoes no banco.",
        "",
        "### Contagem por materia",
        "",
    ]
    if prova.edital_lido:
        linhas.append(f"Quadro lido de `{prova.edital_lido}`. A linha do edital "
                      "e a do caderno se encontram pelo NOME; as colunas de "
                      "posicao dizem onde cada materia esta em cada um.")
    else:
        linhas.append("**Nenhum quadro de edital fechou a conta para este cargo.**")
    linhas += [
        "",
        "| Posicao edital / caderno | Edital | Questoes | Banco (caderno) | Questoes | Bate? |",
        "|---|---|---|---|---|---|",
    ]
    for l in prova.contagem:
        posicao = f"{l.ordem_edital or '—'} / {l.ordem_caderno or '—'}"
        bate = "sim" if l.bate else "**NAO**"
        if l.bate and not l.nome_bate:
            bate += " (nome difere)"
        linhas.append(
            f"| {posicao} | {l.edital or '—'} | {l.no_edital if l.no_edital is not None else '—'} "
            f"| {l.caderno or '—'} | {l.no_caderno if l.no_caderno is not None else '—'} | {bate} |"
        )
    total_edital = sum(l.no_edital or 0 for l in prova.contagem)
    total_banco = sum(l.no_caderno or 0 for l in prova.contagem)
    linhas += [f"| | **Total** | **{total_edital}** | | **{total_banco}** | |", ""]

    linhas += ["### Gabarito definitivo e anuladas", ""]
    if prova.gabarito_que_vale:
        linhas += [
            "Definitivos deste caderno no acervo, do mais velho ao mais novo "
            "(o ultimo e o que vale):",
            "",
            *[f"- `{d}`" for d in prova.definitivos_lidos],
            "",
            f"- anuladas no definitivo que vale: {_numeros(prova.anuladas_oficiais, prova.materia_da_questao)}",
            f"- anuladas marcadas no banco: {_numeros(prova.anuladas_no_banco, prova.materia_da_questao)}",
            f"- letras que o definitivo trocou em relacao ao provisorio: "
            f"{_numeros(prova.trocadas_pelo_definitivo, prova.materia_da_questao)}",
            f"- questoes em que o banco discorda do definitivo: "
            f"**{len(prova.divergencias)}** de {prova.questoes}",
            "",
        ]
    else:
        linhas += ["**Nenhum gabarito definitivo do acervo e deste caderno.** "
                   "O banco esta com o gabarito do caderno, que e o provisorio.", ""]
    return linhas


def relatorio(provas: list[ProvaAuditada], hoje: date | None = None) -> str:
    """O docs/auditoria.md inteiro, em texto."""
    hoje = hoje or date.today()
    do_alvo = [p for p in provas if not p.reforco]
    linhas = [
        "# Auditoria dos dados de estudo",
        "",
        f"> Gerado por `radar auditar` em {hoje:%d/%m/%Y}. **Nao edite a mao**: "
        "rode o comando de novo. Tudo aqui foi lido dos PDFs oficiais do "
        "acervo e do banco, nada foi digitado.",
        "",
        "## O que foi conferido",
        "",
        "- **contagem por materia**: o quadro de distribuicao de questoes do "
        "edital contra o que o banco separou do caderno;",
        "- **gabarito**: cada questao do banco contra o ultimo gabarito "
        "definitivo publicado (retificacao inclusive), letra por letra;",
        "- **anuladas**: as do definitivo contra as marcadas no banco.",
        "",
        "**O que isto nao prova:** a auditoria le os PDFs com o mesmo leitor que "
        "montou o banco. Um erro do leitor que se repita nas duas pontas passa "
        "batido. A conferencia de enunciado e alternativa, questao a questao, "
        "nao e feita aqui.",
        "",
        "## Onde os numeros nao batem",
        "",
    ]
    algum = False
    for p in provas:
        for problema in p.problemas:
            algum = True
            linhas.append(f"- **{p.ano} {p.cargo}**: {problema}")
    if not algum:
        linhas.append("- nenhum lugar: contagem, gabarito e anuladas batem nas "
                      f"{len(provas)} provas.")
    nomes = [(p, l) for p in provas for l in p.nomes_diferentes]
    if nomes:
        linhas += ["", "Contagem certa com o nome escrito diferente (nao e erro "
                   "de numero, mas a tela mostra o nome do caderno):", ""]
        linhas += [f"- {p.ano}: edital \"{l.edital}\", caderno \"{l.caderno}\""
                   for p, l in nomes]
    ordem = [(p, l) for p in provas for l in p.fora_de_ordem]
    if ordem:
        linhas += ["", "Materia em outra posicao no caderno que no edital (a "
                   "contagem nao muda; vale conferir se o caderno e mesmo "
                   "assim ou se a separacao por materia trocou os blocos):", ""]
        linhas += [f"- {p.ano}: {l.edital} - {l.ordem_edital}a no edital, "
                   f"{l.ordem_caderno}a no caderno" for p, l in ordem]

    linhas += [
        "",
        "## Resumo",
        "",
        "| Prova | Papel | Questoes | Anuladas | Definitivo que vale | Divergencias |",
        "|---|---|---|---|---|---|",
    ]
    for p in provas:
        papel = "reforco" if p.reforco else "alvo"
        linhas.append(
            f"| {p.ano} {p.cargo} | {papel} | {p.questoes} | "
            f"{len(p.anuladas_no_banco)} | {p.gabarito_que_vale or '—'} "
            f"({p.gabarito_publicado_em or 'sem data'}) | {len(p.divergencias)} |"
        )
    validas = sum(p.questoes - len(p.anuladas_no_banco) for p in do_alvo)
    linhas += [
        "",
        f"Provas do alvo: {len(do_alvo)}, com {validas} questoes validas "
        "(sem as anuladas). As de reforco nao entram nesta soma.",
        "",
    ]
    for p in provas:
        linhas += _secao(p)

    linhas += [
        "## Questoes com lei posterior",
        "",
        "Pendente: a lista de temas afetados por lei posterior "
        "(`config/leis.yml`) ainda nao foi conferida. Quando for, esta secao "
        "passa a listar as questoes que ganham o aviso.",
        "",
    ]
    return "\n".join(linhas)


def escrever(caminho: Path | None = None) -> list[ProvaAuditada]:
    destino = caminho or caminho_padrao()
    provas = auditar()
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(relatorio(provas), encoding="utf-8")
    return provas
