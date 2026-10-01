"""A arvore de conteudos no banco: semear, mostrar, exportar e ligar.

A regra da arvore mora no `radar.conteudos`, que e puro; aqui fica o que fala
com o banco e com os arquivos. O arquivo versionado e o
`data/conteudos.json`: o banco e reconstruivel, e a arvore tem que voltar
igual - inclusive o no que um dia eu criar a mao.
"""
import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path

from sqlalchemy import func, select

from radar import config
from radar import conteudos as arvore
from radar import cronograma as plano_de_estudo
from radar.db import criar_tabelas, sessao
from radar.models import (
    Classificacao,
    Conteudo,
    ErroAnotado,
    EstudoExtra,
    QuestaoDeProva,
    QuestaoGerada,
    agora,
)
from radar.regioes import normalizar
from radar.servico import evidencia

log = logging.getLogger(__name__)

CAMPOS = [campo for campo in arvore.No.__dataclass_fields__]


def caminho_do_arquivo() -> Path:
    return config.diretorio_dados() / "conteudos.json"


def _no_do_banco(c: Conteudo) -> arvore.No:
    return arvore.No(**{campo: getattr(c, campo) for campo in CAMPOS})


def _gravar(s, no: arvore.No) -> bool:
    """Grava o no se o caminho ainda nao existe. True quando gravou."""
    if s.scalar(select(Conteudo.id).where(Conteudo.caminho == no.caminho)) is not None:
        return False
    s.add(Conteudo(**asdict(no)))
    return True


def nos() -> list[arvore.No]:
    """Todos os nos, na ordem da arvore: cada pai seguido dos filhos dele."""
    criar_tabelas()
    with sessao() as s:
        todos = [_no_do_banco(c) for c in s.scalars(select(Conteudo))]
    filhos: dict[str | None, list[arvore.No]] = {}
    for no in todos:
        filhos.setdefault(no.pai, []).append(no)
    for lista in filhos.values():
        lista.sort(key=lambda n: (n.ordem, n.nome))

    ordenados: list[arvore.No] = []

    def descer(pai):
        for no in filhos.get(pai, []):
            ordenados.append(no)
            descer(no.caminho)
    descer(None)
    return ordenados


def caminhos() -> list[str]:
    return [no.caminho for no in nos()]


# --- semear, exportar, importar ---------------------------------------------------

def semear(programa: dict[str, list[str]] | None = None,
           taxonomia: arvore.Taxonomia | None = None) -> int:
    """Poe a arvore no banco. Devolve quantos nos entraram.

    Com o `data/conteudos.json` no disco, e dele que ela vem: e a arvore como
    estava, com o que foi criado depois do edital. Sem ele, vem do edital
    (`programa`, ou o do alvo no acervo) e o arquivo e escrito. Rodar de novo
    nao duplica nada: o caminho e unico.
    """
    if caminho_do_arquivo().exists() and programa is None:
        return importar()
    if programa is None:
        from radar import foco
        programa = foco.programa_do_alvo()
    if not programa:
        log.warning("Sem o programa do edital no acervo: a árvore fica vazia. "
                    "Rode `radar conteudos --semear` depois de baixar o edital.")
        return 0
    taxonomia = taxonomia or arvore.carregar_taxonomia()

    criar_tabelas()
    entraram = 0
    with sessao() as s:
        for no in arvore.semente(programa, taxonomia):
            entraram += _gravar(s, no)
    exportar()
    return entraram


def exportar(caminho: Path | None = None) -> int:
    destino = caminho or caminho_do_arquivo()
    linhas = [asdict(no) for no in nos()]
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(linhas, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")
    return len(linhas)


def importar(caminho: Path | None = None) -> int:
    """Traz do JSON os nos que o banco nao tem. Devolve quantos entraram."""
    origem = caminho or caminho_do_arquivo()
    if not origem.exists():
        return 0
    linhas = json.loads(origem.read_text(encoding="utf-8")) or []
    criar_tabelas()
    entraram = 0
    with sessao() as s:
        # Pai antes de filho: o arquivo ja vem nessa ordem, mas ordenar pelo
        # tamanho do caminho garante isso mesmo se alguem editar a mao.
        for linha in sorted(linhas, key=lambda l: len(arvore.partes(l["caminho"]))):
            no = arvore.No(**{campo: linha.get(campo) for campo in CAMPOS
                              if campo in linha})
            entraram += _gravar(s, no)
    return entraram


def adicionar(pai: str | None, nome: str, *, origem: str = "manual",
              procedencia: str | None = None, tipo_elemento: str | None = None,
              referencia: str | None = None,
              taxonomia: arvore.Taxonomia | None = None) -> arvore.No:
    """Cria um no debaixo de `pai`. Recusa o que nao cabe na arvore."""
    if origem not in arvore.ORIGENS:
        raise arvore.ConteudoInvalido(f"Origem {origem!r} não existe.")
    criar_tabelas()
    with sessao() as s:
        nivel_do_pai = None
        if pai is not None:
            do_pai = s.scalar(select(Conteudo).where(Conteudo.caminho == pai))
            if do_pai is None:
                raise arvore.ConteudoInvalido(f"O pai {pai!r} não está na árvore.")
            nivel_do_pai = do_pai.nivel
        nivel = arvore.nivel_do_filho(nivel_do_pai)
        if nivel == "elemento":
            arvore.conferir_elemento(taxonomia or arvore.carregar_taxonomia(),
                                     arvore.partes(pai)[0], tipo_elemento)
        elif tipo_elemento is not None:
            raise arvore.ConteudoInvalido("Só o elemento tem tipo.")
        irmaos = s.scalar(select(func.count(Conteudo.id)).where(Conteudo.pai == pai)) or 0
        no = arvore.No(caminho=arvore.caminho(pai, nome), pai=pai, nivel=nivel,
                       nome=" ".join(nome.split()), ordem=irmaos, origem=origem,
                       procedencia=procedencia, tipo_elemento=tipo_elemento,
                       referencia=referencia)
        if not _gravar(s, no):
            raise arvore.ConteudoInvalido(f"{no.caminho!r} já existe.")
    exportar()
    return no


def garantir(pai: str | None, nome: str, **campos) -> str:
    """O caminho do filho `nome` de `pai`: o que ja existe, ou um novo.

    E o que a classificacao usa para o subassunto e o elemento que ela
    propoe: a segunda questao do mesmo subassunto cai no no da primeira.
    """
    alvo = arvore.caminho(pai, nome)
    criar_tabelas()
    with sessao() as s:
        if s.scalar(select(Conteudo.id).where(Conteudo.caminho == alvo)) is not None:
            return alvo
    return adicionar(pai, nome, **campos).caminho


# --- os textos antigos -------------------------------------------------------------

@dataclass
class Ligacao:
    """Um texto antigo e o no em que ele casou (ou None: pendente)."""
    onde: str
    texto: str
    conteudo: str | None
    motivo: str


def _no_do_texto(todos: list[str], taxonomia: arvore.Taxonomia,
                 materia: str | None, assunto: str | None,
                 titulos_de_faixa: dict[str, str]) -> tuple[str | None, str]:
    """O no mais fundo que casa EXATAMENTE com a materia e o assunto.

    Casar e ser igual, sem diferenca de maiuscula nem de acento. A materia
    pode vir pelo sinonimo declarado no config/taxonomia.yml, ou pelo titulo
    de uma faixa do cronograma (as 20 geradas de Penal tem o titulo da faixa
    no lugar da materia: vale a materia da faixa). Nada e aproximado.
    """
    no = arvore.achar(todos, materia)
    motivo = "matéria igual"
    if no is None and taxonomia.materia_do_texto(materia):
        no = arvore.achar(todos, taxonomia.materia_do_texto(materia))
        motivo = "matéria pelo sinônimo do config/taxonomia.yml"
    if no is None and normalizar(materia or "") in titulos_de_faixa:
        no = arvore.achar(todos, titulos_de_faixa[normalizar(materia)])
        motivo = "o texto é o título de uma faixa: vale a matéria da faixa"
    if no is None:
        return None, "nenhuma matéria igual"
    mais_fundo = arvore.achar(todos, assunto, pai=no)
    if mais_fundo:
        return mais_fundo, motivo + " e assunto igual"
    if assunto:
        return no, motivo + "; o assunto não casa com nenhum do edital (pendente)"
    return no, motivo


def _titulos_de_faixa() -> dict[str, str]:
    """{titulo normalizado: materia} das faixas do cronograma."""
    try:
        plano = plano_de_estudo.carregar()
    except (FileNotFoundError, plano_de_estudo.ErroNoCronograma):
        return {}
    return {normalizar(f.titulo): f.materia
            for dia in plano.dias for f in dia.faixas() if f.materia}


def ligar_textos_antigos(aplicar: bool = True) -> list[Ligacao]:
    """Liga a um no a materia e o assunto de texto da questao gerada, do erro
    anotado e do estudo extra. Com `aplicar=False`, so diz o que faria.

    O texto antigo nao muda: ganha so o `conteudo` ao lado. Quem ja tem
    `conteudo` nao e tocado.
    """
    todos = caminhos()
    if not todos:
        return []
    taxonomia = arvore.carregar_taxonomia()
    titulos = _titulos_de_faixa()
    ligacoes = []
    with sessao() as s:
        for tabela, rotulo in ((QuestaoGerada, "questão gerada"),
                               (ErroAnotado, "erro anotado"),
                               (EstudoExtra, "estudo extra")):
            for linha in s.scalars(select(tabela).where(tabela.conteudo.is_(None))):
                no, motivo = _no_do_texto(todos, taxonomia, linha.materia,
                                          linha.assunto, titulos)
                texto = " · ".join(t for t in (linha.materia, linha.assunto) if t)
                ligacoes.append(Ligacao(f"{rotulo} #{linha.id}", texto, no, motivo))
                if aplicar and no is not None:
                    linha.conteudo = no
                    # O export do caderno e do extra so troca a linha do JSON
                    # quando ela e mais nova: sem isto a ligacao nao saia do
                    # banco. A gerada nao tem a data (o arquivo dela e
                    # reescrito inteiro).
                    if hasattr(linha, "atualizado_em"):
                        linha.atualizado_em = agora()
    return ligacoes


# --- pendentes ----------------------------------------------------------------------

@dataclass
class Pendentes:
    """As questoes sem classificacao principal, por evidencia e por prova."""
    #: {evidencia: quantas}
    por_evidencia: dict[str, int] = field(default_factory=dict)
    #: [(evidencia, ano, cargo, quantas)], so do alvo e do complementar.
    por_prova: list[tuple] = field(default_factory=list)


def pendentes() -> Pendentes:
    """Questao sem classificacao principal completa ou parcial e pendente.

    Inclusive a que nunca foi classificada: e o estado de todas hoje. Anulada
    fica de fora - a banca desfez a pergunta, e nao ha o que classificar.
    """
    from radar.questoes import chave_da_questao

    criar_tabelas()
    with sessao() as s:
        classificadas = set(s.scalars(
            select(Classificacao.chave)
            .where(Classificacao.principal.is_(True))
            .where(Classificacao.status != "pendente")))
        linhas = s.execute(
            select(QuestaoDeProva.evidencia, QuestaoDeProva.ano,
                   QuestaoDeProva.cargo, QuestaoDeProva.enunciado,
                   QuestaoDeProva.alternativas)
            .where(QuestaoDeProva.anulada.is_not(True))).all()

    resultado = Pendentes()
    por_prova: dict[tuple, int] = {}
    for ev, ano, cargo, enunciado, alternativas in linhas:
        if chave_da_questao(enunciado, alternativas) in classificadas:
            continue
        ev = ev or "sem evidência"
        resultado.por_evidencia[ev] = resultado.por_evidencia.get(ev, 0) + 1
        if ev in (evidencia.ALVO, evidencia.COMPLEMENTAR):
            chave = (ev, ano, cargo)
            por_prova[chave] = por_prova.get(chave, 0) + 1
    ordem = {evidencia.ALVO: 0, evidencia.COMPLEMENTAR: 1}
    resultado.por_prova = sorted(
        ((ev, ano, cargo, n) for (ev, ano, cargo), n in por_prova.items()),
        key=lambda linha: (ordem[linha[0]], -(linha[1] or 0), linha[2] or ""))
    return resultado
