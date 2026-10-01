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
import logging
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


def _tabela_das_provas(por_materia, validadas) -> list[str]:
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
        "| Ano | Cargo | Questões minhas | Gabarito | Situação | Por quê |",
        "|---|---|---|---|---|---|",
    ]
    for url, dados in sorted(interessantes.items(),
                             key=lambda item: (-item[1]["total"], item[1]["ano"] or 0)):
        v = validadas[url]
        linhas.append(
            f"| {dados['ano'] or '—'} | {dados['cargo'] or '—'} | "
            f"{dados['total']} ({'; '.join(dados['materias'])}) | {v.gabarito} | "
            f"{v.situacao} | {v.motivo or '—'} |")
    return linhas + [""]


def relatorio(por_materia, validadas, lista) -> str:
    """O docs/complementar.md inteiro, em texto."""
    com_definitivo = sum(1 for v in validadas.values() if v.entra_nos_padroes)
    so_classificar = sum(1 for v in validadas.values()
                         if v.pode_classificar and not v.entra_nos_padroes)
    recusadas = sum(1 for v in validadas.values() if not v.pode_classificar)
    questoes = sum(len(c.questoes) for c in lista)

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
        "## O que ainda não foi feito",
        "",
        "Este relatório é o **levantamento**. Nada entrou em estatística "
        "nenhuma por causa dele. O que vem depois, na ordem, e só com a sua "
        "aprovação: você escolhe as provas, elas passam pela validação que lê "
        "o PDF, são classificadas por matéria (com conferência por amostra) e "
        "só então ganham a linha própria na incidência.",
        "",
    ]
    linhas += _tabela_das_materias(por_materia)
    linhas += _tabela_das_provas(por_materia, validadas)
    linhas += ["## As perguntas da seção 5 do pedido", "",
               "Respondidas **só com o que o acervo tem**. \"Não há prova com "
               "LEP no acervo\" é diferente de \"a FEPESE nunca cobrou LEP\": "
               "o relatório nunca diz a segunda coisa.", ""]
    for r in complementar.responder(por_materia):
        linhas += [f"**{r.pergunta}**", "", r.resposta, ""]
    return "\n".join(linhas)


def escrever(caminho: Path | None = None):
    """Gera o relatorio e devolve (por_materia, validacoes, cadernos)."""
    destino = Path(caminho) if caminho else caminho_do_relatorio()
    por_materia, validadas, lista = levantamento()
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(relatorio(por_materia, validadas, lista), encoding="utf-8")
    return por_materia, validadas, lista
