"""O levantamento do acervo complementar FEPESE a partir do banco.

A conta mora no `radar.complementar`, que e puro; aqui so se junta o que ele
precisa: as questoes marcadas `complementar` pela regra do
`servico/evidencia.py`, os nomes das materias do meu edital (a arvore da
Etapa 2) e o manifesto `data/provas.json`, que guarda o sha256 de cada PDF.

Este modulo SO LE. Ele nao grava questao, nao muda evidencia e nao cria no:
escolher quais provas entram e decisao sua, e vem depois do relatorio.

**Sobre o tipo do gabarito:** o manifesto diz que gabaritos o CONCURSO tem,
nao qual grade e de qual caderno - saber isso exige reler o PDF, e o
relatorio cobre 183 provas. Entao `definitivo` aqui quer dizer "o concurso
desta prova publicou gabarito definitivo, e ele esta no acervo". Qual grade
e desta prova se confere na validacao da prova escolhida, que le o PDF.
"""
import json
import logging
from dataclasses import asdict
from datetime import date
from pathlib import Path

import yaml
from sqlalchemy import select

from radar import complementar, config
from radar import conteudos as arvore
from radar import provas as arquivos_de_prova
from radar.db import criar_tabelas, sessao
from radar.models import Conteudo, QuestaoDeProva
from radar.servico import evidencia

log = logging.getLogger(__name__)


def caminho_do_relatorio() -> Path:
    return Path(__file__).resolve().parents[3] / "docs" / "complementar.md"


def carregar_termos(caminho: Path | None = None) -> dict[str, list[str]]:
    """Os termos de busca por materia (`config/complementar.yml`)."""
    arquivo = caminho or (config.diretorio_config() / "complementar.yml")
    if not Path(arquivo).exists():
        return {}
    dados = yaml.safe_load(Path(arquivo).read_text(encoding="utf-8")) or {}
    return {str(m): [str(t) for t in (termos or [])]
            for m, termos in (dados.get("termos") or {}).items()}


def carregar_mapa_do_catalogo(caminho: Path | None = None) -> dict[str, dict[str, str]]:
    """{materia: {nome no catalogo: assunto do edital}} do config."""
    arquivo = caminho or (config.diretorio_config() / "complementar.yml")
    if not Path(arquivo).exists():
        return {}
    dados = yaml.safe_load(Path(arquivo).read_text(encoding="utf-8")) or {}
    return {str(m): {str(k): str(v) for k, v in (pares or {}).items()}
            for m, pares in (dados.get("catalogo_para_edital") or {}).items()}


def _gabarito_por_concurso() -> dict[str, str]:
    """{concurso_url: o melhor gabarito que o acervo tem dele}."""
    melhor: dict[str, str] = {}
    for registro in arquivos_de_prova.carregar_manifesto():
        concurso = registro.get("concurso_url")
        if not concurso:
            continue
        tipo = registro.get("tipo")
        if tipo == arquivos_de_prova.GABARITO_DEFINITIVO:
            melhor[concurso] = complementar.DEFINITIVO
        elif tipo == arquivos_de_prova.GABARITO:
            melhor.setdefault(concurso, complementar.PROVISORIO)
    return melhor


def _hash_por_prova() -> dict[str, str]:
    """{url do caderno: sha256 do PDF}, do manifesto."""
    return {r["url"]: r.get("sha256") for r in arquivos_de_prova.carregar_manifesto()
            if r.get("tipo") == arquivos_de_prova.PROVA and r.get("url")}


def materias_do_edital() -> list[str]:
    """Os nomes das materias da arvore, na ordem dela."""
    criar_tabelas()
    with sessao() as s:
        return [c.caminho for c in s.scalars(
            select(Conteudo).where(Conteudo.nivel == "materia")
            .order_by(Conteudo.ordem, Conteudo.caminho))]


def cadernos() -> list[complementar.Caderno]:
    """Uma entrada por prova complementar do banco, com as questoes dela."""
    taxonomia = arvore.carregar_taxonomia()
    nomes = {complementar.normalizar(m): m for m in materias_do_edital()}
    gabaritos = _gabarito_por_concurso()
    hashes = _hash_por_prova()

    criar_tabelas()
    with sessao() as s:
        questoes = list(s.scalars(
            select(QuestaoDeProva)
            .where(QuestaoDeProva.evidencia == evidencia.COMPLEMENTAR)
            .order_by(QuestaoDeProva.prova_url, QuestaoDeProva.numero)))

    por_prova: dict[str, complementar.Caderno] = {}
    for q in questoes:
        caderno = por_prova.get(q.prova_url)
        if caderno is None:
            caderno = complementar.Caderno(
                prova_url=q.prova_url, cargo=q.cargo, ano=q.ano,
                sha256=hashes.get(q.prova_url),
                gabarito=gabaritos.get(q.concurso_url or "", complementar.AUSENTE))
            por_prova[q.prova_url] = caderno
        # O nome do caderno vale como materia minha so quando e IGUAL ao nome
        # do no (ou o sinonimo declarado aponta para ele): "Conhecimentos
        # Especificos" nao vira materia nenhuma por aproximacao.
        do_edital = taxonomia.materia_do_texto(q.materia) or q.materia
        alternativas = q.alternativas or {}
        caderno.questoes.append(complementar.QuestaoDoCaderno(
            numero=q.numero,
            materia_no_edital=nomes.get(complementar.normalizar(do_edital)),
            texto=" ".join([q.enunciado or ""] + [str(v) for v in alternativas.values()]),
            letras=tuple(sorted(alternativas)),
            resposta=q.resposta, anulada=bool(q.anulada)))
    return list(por_prova.values())


def validacoes(lista: list[complementar.Caderno]) -> dict[str, complementar.Validacao]:
    """A validacao de cada caderno. A primeira prova com um sha256 fica com
    ele; a seguinte que repetir o hash e recusada."""
    vistos: dict[str, str] = {}
    resultado = {}
    for caderno in sorted(lista, key=lambda c: (c.ano or 0, c.prova_url)):
        resultado[caderno.prova_url] = complementar.validar(caderno, vistos)
        if caderno.sha256:
            vistos.setdefault(caderno.sha256, caderno.prova_url)
    return resultado


def levantamento() -> tuple[list[complementar.MateriaComplementar],
                            dict[str, complementar.Validacao],
                            list[complementar.Caderno]]:
    """O levantamento inteiro: por materia, as validacoes e os cadernos."""
    lista = cadernos()
    validadas = validacoes(lista)
    por_materia = complementar.montar(materias_do_edital(), lista,
                                      carregar_termos(), validadas)
    return por_materia, validadas, lista


# --- o arquivo de status: quais provas estao no acervo complementar -------------
#
# O que a secao 5 do pedido manda guardar de cada prova: fonte, concurso,
# cargo, ano, hash, tipo de evidencia, status de validacao e data de
# inclusao. Fica num JSON versionado, como o `data/classificacoes.json`: o
# banco e reconstruivel, e esta decisao nao pode se perder com ele.


def caminho_do_registro() -> Path:
    return config.diretorio_dados() / "acervo_complementar.json"


def carregar_registro() -> dict[str, dict]:
    """{prova_url: registro gravado}. Vazio quando o arquivo nao existe."""
    arquivo = caminho_do_registro()
    if not arquivo.exists():
        return {}
    dados = json.loads(arquivo.read_text(encoding="utf-8"))
    return {r["prova_url"]: r for r in dados.get("provas", [])}


def _do_manifesto() -> dict[str, dict]:
    return {r["url"]: r for r in arquivos_de_prova.carregar_manifesto()
            if r.get("tipo") == arquivos_de_prova.PROVA and r.get("url")}


def decidir_todas(hoje: date | None = None,
                  levantado: tuple | None = None) -> list[complementar.Registro]:
    """A decisao de cada prova complementar, sem gravar nada.

    A data de inclusao de quem ja estava no arquivo e PRESERVADA: ela conta
    desde quando a prova esta no acervo, e nao desde a ultima vez que o
    comando rodou. `levantado` evita refazer o levantamento quem ja o tem.
    """
    hoje = hoje or date.today()
    por_materia, validadas, lista = levantado or levantamento()
    gravado = carregar_registro()
    manifesto = _do_manifesto()

    minhas: dict[str, list[str]] = {}
    for m in por_materia:
        for p in m.provas:
            if p.pelo_nome:
                minhas.setdefault(p.prova_url, []).append(m.materia)

    registros = []
    for caderno in sorted(lista, key=lambda c: (-(c.ano or 0), c.cargo or "")):
        validacao = validadas[caderno.prova_url]
        materias = minhas.get(caderno.prova_url, [])
        aceita, motivo = complementar.decidir(validacao, materias)
        antes = gravado.get(caderno.prova_url, {})
        do_manifesto = manifesto.get(caderno.prova_url, {})
        registros.append(complementar.Registro(
            prova_url=caderno.prova_url, cargo=caderno.cargo, ano=caderno.ano,
            concurso_url=do_manifesto.get("concurso_url"),
            arquivo=do_manifesto.get("arquivo"), sha256=caderno.sha256,
            questoes=len(caderno.questoes), materias_do_edital=materias,
            gabarito=validacao.gabarito, quadro_do_edital=validacao.quadro_do_edital,
            aceita=aceita, motivo=motivo,
            entra_nos_padroes=aceita and validacao.entra_nos_padroes,
            incluida_em=(antes.get("incluida_em") or f"{hoje:%Y-%m-%d}") if aceita else None,
        ))
    return registros


def aplicar(hoje: date | None = None,
            levantado: tuple | None = None) -> tuple[list[complementar.Registro], dict]:
    """Grava o arquivo de status. Devolve (registros, o que mudou)."""
    antes = carregar_registro()
    registros = decidir_todas(hoje, levantado)
    mudanca = {
        "entraram": [r.prova_url for r in registros
                     if r.aceita and not antes.get(r.prova_url, {}).get("aceita")],
        "sairam": [r.prova_url for r in registros
                   if not r.aceita and antes.get(r.prova_url, {}).get("aceita")],
    }
    caminho_do_registro().write_text(
        json.dumps({"provas": [asdict(r) for r in registros]},
                   ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return registros, mudanca


def provas_aceitas() -> set[str]:
    """Os cadernos que o arquivo de status aceita. Sem arquivo, conjunto
    vazio: nenhuma prova complementar entra em estatistica por acidente."""
    return {url for url, r in carregar_registro().items() if r.get("aceita")}


def provas_dos_padroes() -> set[str]:
    """Os cadernos que entram nos padroes de cobranca: os aceitos com gabarito
    DEFINITIVO (`entra_nos_padroes`). O provisorio serve para classificar, mas
    muda depois dos recursos, e o padrao se mede sobre a letra certa."""
    return {url for url, r in carregar_registro().items()
            if r.get("aceita") and r.get("entra_nos_padroes")}


# --- o relatorio ------------------------------------------------------------

def _tabela_das_materias(por_materia) -> list[str]:
    linhas = [
        "## O que o acervo complementar tem de cada matéria do meu edital",
        "",
        "Duas colunas, **que nunca se somam**: *pelo nome* é o que o caderno "
        "chama com o nome da matéria (é certo); *por termo* 🟡 é indício — o "
        "caderno só diz \"Conhecimentos Específicos\" e um termo do "
        "`config/complementar.yml` apareceu no texto. Indício não é evidência: "
        "quem diz qual conteúdo caiu é a classificação, questão a questão.",
        "",
        "| Matéria | Pelo nome | Provas | Por termo 🟡 | Provas |",
        "|---|---|---|---|---|",
    ]
    for m in por_materia:
        linhas.append(f"| {m.materia} | {m.pelo_nome} | {m.provas_pelo_nome} | "
                      f"{m.por_termo} | {m.provas_por_termo} |")
    return linhas + [""]


def _tabela_das_provas(por_materia, validadas, registros) -> list[str]:
    """Uma linha por prova que tem alguma coisa de alguma materia minha."""
    interessantes: dict[str, dict] = {}
    for m in por_materia:
        for p in m.provas:
            dados = interessantes.setdefault(p.prova_url, {
                "cargo": p.cargo, "ano": p.ano, "materias": [], "total": 0})
            dados["materias"].append(f"{m.materia} ({p.questoes})")
            dados["total"] += p.questoes

    linhas = [
        "## As provas que interessam, e o que cada uma permite",
        "",
        "A validação é a mínima da seção 5 do pedido, feita **sem reler o "
        "PDF**: numeração de 1 a N sem buraco, cinco alternativas em toda "
        "questão, gabarito em toda questão e sha256 do PDF (a mesma prova com "
        "outro nome de arquivo é recusada). O quadro do edital fica "
        f"\"{complementar.QUADRO_NAO_LIDO}\": o leitor de quadro só dá conta "
        "dos editais do Estado, e nas provas de prefeitura ele não acha o "
        "quadro. Isso se confere na validação da prova escolhida, que lê o PDF.",
        "",
        "| Ano | Cargo | Questões minhas | Gabarito | Situação | No acervo | Por quê |",
        "|---|---|---|---|---|---|---|",
    ]
    por_url = {r.prova_url: r for r in registros}
    for url, dados in sorted(interessantes.items(),
                             key=lambda item: (-item[1]["total"], item[1]["ano"] or 0)):
        v = validadas[url]
        r = por_url.get(url)
        no_acervo = "—"
        if r is not None:
            no_acervo = f"sim, desde {r.incluida_em}" if r.aceita else "não"
        linhas.append(
            f"| {dados['ano'] or '—'} | {dados['cargo'] or '—'} | "
            f"{dados['total']} ({'; '.join(dados['materias'])}) | {v.gabarito} | "
            f"{v.situacao} | {no_acervo} | {v.motivo or '—'} |")
    return linhas + [""]


def relatorio(por_materia, validadas, lista, registros=None) -> str:
    """O docs/complementar.md inteiro, em texto."""
    com_definitivo = sum(1 for v in validadas.values() if v.entra_nos_padroes)
    so_classificar = sum(1 for v in validadas.values()
                         if v.pode_classificar and not v.entra_nos_padroes)
    recusadas = sum(1 for v in validadas.values() if not v.pode_classificar)
    questoes = sum(len(c.questoes) for c in lista)
    registros = registros if registros is not None else []
    no_acervo = sum(1 for r in registros if r.aceita)

    linhas = [
        "# Acervo complementar FEPESE",
        "",
        "> Gerado por `radar complementar`. **Não edite à mão**: rode o comando "
        "de novo. É uma consulta ao que já está no banco — nada foi baixado, "
        "importado nem alterado.",
        "",
        "## O que é isto",
        "",
        "Complementar é toda prova de uma banca do alvo (a FEPESE) que **não** "
        "é do meu cargo no meu estado. Ela serve para entender o estilo da "
        "banca — e **nunca** entra na incidência da Polícia Penal SC. Os dois "
        "números vivem em linhas separadas e jamais são somados (regra "
        "inviolável 1): a incidência do alvo continua sendo só 2013 e 2019, "
        "e adicionar prova complementar não muda nenhum número dela.",
        "",
        f"No acervo de hoje: **{len(lista)} provas complementares**, "
        f"{questoes} questões. Delas, **{com_definitivo}** passam na validação "
        f"inteira (extração sem defeito e gabarito definitivo), "
        f"**{so_classificar}** servem para classificar mas ficam fora dos "
        f"padrões de cobrança, e **{recusadas}** são recusadas.",
        "",
    ]
    # O texto depende de o acervo ja ter sido aplicado: antes do `--aplicar`,
    # isto e so o levantamento; depois, as provas aceitas ja tem a linha
    # propria na incidencia - e dizer "nada entrou" seria mentir.
    aplicadas = len(provas_aceitas())
    if aplicadas:
        linhas += [
            "## Onde isto está",
            "",
            f"O levantamento já virou acervo (Etapa 3B): **{aplicadas} provas** "
            "estão aceitas no `data/acervo_complementar.json` e têm a **linha "
            "própria na incidência**, sempre separada da do alvo e contada em "
            "questão distinta. Parte das questões delas foi classificada por "
            "conteúdo, com procedência; o resto conta só na matéria que o "
            "caderno declara. O que falta é a sua conferência das "
            "classificações, na tela Análises > Conferência, com o filtro do "
            "complementar aceito. A proposta automática do catálogo se confere "
            "por amostra; a de 04/10 errou o assunto em quase metade dela, e o "
            "lote foi refeito (decisão 87). Os padrões de cobrança do "
            "complementar (tipo de questão, pegadinha) saem à parte dos do "
            "alvo, só das provas com gabarito definitivo (decisão 78).",
            "",
        ]
    else:
        linhas += [
            "## O que ainda não foi feito",
            "",
            "Este relatório é o **levantamento**. Nada entrou em estatística "
            "nenhuma por causa dele. O que vem depois, na ordem, e só com a sua "
            "aprovação: você escolhe as provas, elas passam pela validação que "
            "lê o PDF, são classificadas por matéria (com conferência por "
            "amostra) e só então ganham a linha própria na incidência.",
            "",
        ]
    if registros:
        linhas += [
            "## Quem entra no acervo, pela regra do edital de 2019",
            "",
            "Entra a prova que tem **ao menos uma matéria do edital de 2019** "
            "pelo nome no caderno e que passa na validação mínima. Matéria que "
            "não está no edital de agora (Noções de Informática, Direito "
            "Administrativo, Temas de Educação) **não serve de motivo** para a "
            "prova entrar. A decisão de cada prova, com a data de inclusão e o "
            "hash, fica em `data/acervo_complementar.json`, gravado por "
            "`radar complementar --aplicar`.",
            "",
            f"Hoje: **{no_acervo} provas no acervo**, de {len(lista)}.",
            "",
        ]
    linhas += _tabela_das_materias(por_materia)
    linhas += _tabela_das_provas(por_materia, validadas, registros)
    linhas += ["## As perguntas da seção 5 do pedido", "",
               "Respondidas **só com o que o acervo tem**. \"Não há prova com "
               "LEP no acervo\" é diferente de \"a FEPESE nunca cobrou LEP\": "
               "o relatório nunca diz a segunda coisa.", ""]
    from radar.servico import incidencia as servico_incidencia

    linhas_por_no = servico_incidencia.linhas_complementares() if registros else {}
    classificadas = {caminho: linha.classificadas for caminho, linha in linhas_por_no.items()
                     if " > " not in caminho}
    for r in complementar.responder(por_materia, classificadas if registros else None):
        linhas += [f"**{r.pergunta}**", "", r.resposta, ""]
    return "\n".join(linhas)


def escrever(caminho: Path | None = None):
    """Gera o relatorio e devolve (por_materia, validacoes, cadernos)."""
    destino = Path(caminho) if caminho else caminho_do_relatorio()
    levantado = levantamento()
    registros = decidir_todas(levantado=levantado)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(relatorio(*levantado, registros=registros), encoding="utf-8")
    return levantado


def classificar_pelo_catalogo(materia: str):
    """Roda o catalogo nas questoes DESTA materia nas provas aceitas.

    So o complementar: no alvo a classificacao e lida uma a uma, com
    conferencia de todas - e o que a 3A fez. Aqui sao milhares de questoes de
    Portugues e Raciocinio Logico, e o caminho e o que o roteiro pede:
    proposta automatica 🟡 conferida por amostra.
    """
    from radar.servico import classificacoes, evidencia

    aceitas = provas_aceitas()
    if not aceitas:
        return classificacoes.ResultadoDoCatalogo()
    criar_tabelas()
    with sessao() as s:
        questoes = list(s.scalars(
            select(QuestaoDeProva)
            .where(QuestaoDeProva.evidencia == evidencia.COMPLEMENTAR,
                   QuestaoDeProva.prova_url.in_(aceitas),
                   QuestaoDeProva.materia.in_(arvore.grafias_da_materia(materia)))))
    # Uma por CHAVE: a mesma questao em dois cadernos e uma so.
    por_chave = {classificacoes.chave_de(q): (q.enunciado or "") for q in questoes}
    return classificacoes.propor_pelo_catalogo(materia, por_chave)
