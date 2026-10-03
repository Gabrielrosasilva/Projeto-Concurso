"""A prioridade de estudo de um tema: por que estudar isto agora (Etapa 6B).

A secao 15 do novo.md pede que o cronograma considere o peso da materia, a
incidencia, o meu desempenho e a necessidade de revisao - como REGRA DE
PRIORIZACAO, nunca como previsao de prova -, e que a regra seja documentada e
facil de ajustar. A regra mora no config/prioridade.yml; a conta, aqui. Puro:
recebe numeros ja contados (pelo mapa de incidencia, pelo desempenho por
conteudo, pela fila de revisao) e devolve o numero e os fatores.

    prioridade = peso da materia no edital (questoes)
               x incidencia (fatia do ALVO + peso declarado x fatia do complementar)
               x desempenho (1 - meu acerto, so com amostra suficiente)
               x tempo (1 a 2, pelos dias desde a ultima pratica)
               x revisao (o multiplicador, quando o conteudo esta na fila)

Cada fator sai com o NUMERO e a ORIGEM (oficial, acervo, automatico), para a
ficha dizer "voce esta estudando isto agora porque..." sem esconder nada. O
complementar fica num fator proprio, separado do alvo: a §15 deixa usa-lo,
desde que separado e com peso menor e declarado.
"""
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import yaml

from radar import config
from radar.onde_estudar import fator_de_tempo, numero
# As origens de cada fator: as mesmas do resto do site (Etapa 7A).
from radar.origem import ACERVO, AUTOMATICO, OFICIAL


@dataclass(frozen=True)
class Regra:
    """Os numeros do config/prioridade.yml. Sem o arquivo, valem estes."""

    piso_em_questoes: float = 0.5
    peso_do_complementar: float = 0.25
    dias_para_dobrar: int = 30
    fator_maximo: float = 2.0
    multiplicador_da_revisao: float = 1.5


def carregar(caminho: Path | None = None) -> Regra:
    """Le a regra. Arquivo ausente ou secao faltando: o padrao da classe."""
    arquivo = Path(caminho or (config.diretorio_config() / "prioridade.yml"))
    if not arquivo.exists():
        return Regra()
    dados = yaml.safe_load(arquivo.read_text(encoding="utf-8")) or {}
    incidencia = dados.get("incidencia") or {}
    tempo = dados.get("tempo") or {}
    revisao = dados.get("revisao") or {}
    padrao = Regra()
    return Regra(
        piso_em_questoes=float(incidencia.get("piso_em_questoes", padrao.piso_em_questoes)),
        peso_do_complementar=float(
            incidencia.get("peso_do_complementar", padrao.peso_do_complementar)),
        dias_para_dobrar=int(tempo.get("dias_para_dobrar", padrao.dias_para_dobrar)),
        fator_maximo=float(tempo.get("fator_maximo", padrao.fator_maximo)),
        multiplicador_da_revisao=float(
            revisao.get("multiplicador", padrao.multiplicador_da_revisao)),
    )


@dataclass(frozen=True)
class Fator:
    """Um fator da conta: o que ele vale, o que quer dizer, e de onde veio."""

    nome: str
    valor: float
    texto: str
    origem: str


@dataclass
class Prioridade:
    """O numero e os fatores que o explicam. Nunca o numero sozinho."""

    valor: float
    peso: Fator
    alvo: Fator
    complementar: Fator
    desempenho: Fator
    tempo: Fator
    revisao: Fator
    #: A posicao entre todos os temas com ficha (1 = o que mais pede agora).
    #: Quem preenche e quem ordena; sozinha, a conta nao sabe.
    posicao: int | None = None
    de: int | None = None
    fatores: list = field(default_factory=list)

    def __post_init__(self):
        self.fatores = [self.peso, self.alvo, self.complementar,
                        self.desempenho, self.tempo, self.revisao]

    @property
    def conta(self) -> str:
        """"5 × (0,1 + 0,015) × 1 × 1 × 1 = 0,58": a conta escrita inteira."""
        return (f"{_n(self.peso.valor)} × ({_n(self.alvo.valor, 3)} + "
                f"{_n(self.complementar.valor, 3)}) × {_n(self.desempenho.valor)} "
                f"× {_n(self.tempo.valor)} × {_n(self.revisao.valor)} = "
                f"{_n(self.valor)}")


def _n(valor: float, casas: int = 2) -> str:
    return numero(valor, casas)


def calcular(
    *,
    materia: str,
    questoes_da_materia: int | None,
    questoes_da_prova: int,
    alvo_no_escopo: int,
    alvo_na_materia: int,
    complementar_no_escopo: int,
    complementar_na_materia: int,
    estado=None,
    ultima: date | None = None,
    motivos_da_revisao: list[str] | None = None,
    hoje: date | None = None,
    regra: Regra | None = None,
    sem_no: bool = False,
) -> Prioridade:
    """A prioridade de um tema, com cada fator explicado.

    - `questoes_da_materia`: o peso no edital (None = a materia nao esta no
      quadro, e o peso fica neutro, dito assim);
    - `sem_no`: a ficha nao tem no na arvore, e o acervo nao foi contado para
      ela. Vale o mesmo piso, mas o texto nao pode dizer "nao apareceu nas
      provas": isso ninguem verificou (regra inviolavel 4);
    - `alvo_*`: questoes que CONTAM (sem anulada, sem pendente) no escopo da
      ficha e na materia inteira, nas provas do alvo;
    - `complementar_*`: o mesmo no acervo complementar, em questao distinta e
      classificada;
    - `estado`: o `amostra.Estado` do escopo, ou None se eu nunca respondi;
    - `ultima`: o dia da ultima pratica no escopo;
    - `motivos_da_revisao`: os motivos da fila (vazio = fora da fila).
    """
    regra = regra or Regra()
    hoje = hoje or date.today()

    # --- o peso no edital (oficial) ------------------------------------------
    if questoes_da_materia:
        peso = Fator("peso no edital", float(questoes_da_materia),
                     f"{materia}: {questoes_da_materia} de {questoes_da_prova} "
                     f"questões da prova (quadro do edital de 2019)", OFICIAL)
    else:
        peso = Fator("peso no edital", 1.0,
                     f"{materia} não está no quadro do edital: peso neutro (1)",
                     OFICIAL)

    # --- a incidencia do alvo (acervo) ----------------------------------------
    if not alvo_na_materia:
        alvo = Fator("incidência no alvo", 1.0,
                     "a matéria não tem questão nas provas do alvo: incidência "
                     "não medida, fator neutro (1)", ACERVO)
    elif sem_no:
        fatia = regra.piso_em_questoes / alvo_na_materia
        alvo = Fator("incidência no alvo", fatia,
                     f"o tema não tem nó na árvore, e o acervo não é contado para "
                     f"ele: vale o piso de {_n(regra.piso_em_questoes, 1)} questão "
                     f"(de {alvo_na_materia} da matéria), {_n(fatia, 3)}", ACERVO)
    elif not alvo_no_escopo:
        fatia = regra.piso_em_questoes / alvo_na_materia
        alvo = Fator("incidência no alvo", fatia,
                     f"não apareceu nas provas analisadas (0 de {alvo_na_materia} "
                     f"questões da matéria): vale o piso de "
                     f"{_n(regra.piso_em_questoes, 1)} questão, "
                     f"{_n(fatia, 3)}", ACERVO)
    else:
        fatia = alvo_no_escopo / alvo_na_materia
        palavra = "questão" if alvo_no_escopo == 1 else "questões"
        alvo = Fator("incidência no alvo", fatia,
                     f"{alvo_no_escopo} {palavra} de {alvo_na_materia} da matéria "
                     f"nas provas do alvo: fatia de {_n(fatia, 3)}", ACERVO)

    # --- o complementar, em linha propria e com peso menor (acervo) -----------
    if sem_no:
        termo = 0.0
        texto = "o tema não tem nó na árvore: o acervo complementar não é contado"
    elif not complementar_na_materia or not regra.peso_do_complementar:
        termo = 0.0
        if not regra.peso_do_complementar:
            texto = "acervo complementar com peso 0 no config/prioridade.yml: não entra"
        else:
            texto = ("acervo complementar sem questão classificada nesta matéria: "
                     "não entra")
    else:
        fatia_c = complementar_no_escopo / complementar_na_materia
        termo = regra.peso_do_complementar * fatia_c
        texto = (f"acervo complementar FEPESE, separado do alvo: "
                 f"{complementar_no_escopo} de {complementar_na_materia} questões "
                 f"classificadas da matéria (fatia {_n(fatia_c, 3)}) × peso declarado "
                 f"{_n(regra.peso_do_complementar)} = {_n(termo, 3)}")
    complementar = Fator("acervo complementar (peso menor)", termo, texto, ACERVO)

    # --- o meu desempenho (automatico) ----------------------------------------
    medido = estado is not None and estado.suficiente
    if medido:
        acerto = estado.porcentagem / 100
        desempenho = Fator(
            "meu desempenho", 1 - acerto,
            f"{estado.porcentagem}% em {estado.respostas} respostas sem consulta "
            f"({estado.nome}): 1 − {_n(acerto)} = {_n(1 - acerto)}", AUTOMATICO)
    elif estado is not None and estado.respostas:
        desempenho = Fator(
            "meu desempenho", 1.0,
            f"amostra insuficiente ({estado.respostas} de {estado.minimo} respostas "
            f"sem consulta): a porcentagem não entra na conta, vale 1", AUTOMATICO)
    else:
        desempenho = Fator("meu desempenho", 1.0,
                           "ainda sem resposta sem consulta neste conteúdo: vale 1",
                           AUTOMATICO)

    # --- o tempo (automatico), so com amostra ---------------------------------
    if medido and ultima is not None:
        valor = fator_de_tempo(ultima, hoje, regra.dias_para_dobrar, regra.fator_maximo)
        dias = max(0, (hoje - ultima).days)
        tempo = Fator("tempo sem praticar", valor,
                      f"{dias} dia(s) desde a última prática: 1 + {dias}/"
                      f"{regra.dias_para_dobrar}, teto {_n(regra.fator_maximo, 1)} "
                      f"= {_n(valor)}", AUTOMATICO)
    else:
        tempo = Fator("tempo sem praticar", 1.0,
                      "sem amostra suficiente não há prática para contar dias: vale 1",
                      AUTOMATICO)

    # --- a revisao (automatico) -----------------------------------------------
    if motivos_da_revisao:
        revisao = Fator("fila de revisão", regra.multiplicador_da_revisao,
                        f"na fila de revisão ({' · '.join(motivos_da_revisao)}): "
                        f"× {_n(regra.multiplicador_da_revisao)}", AUTOMATICO)
    else:
        revisao = Fator("fila de revisão", 1.0, "fora da fila de revisão: vale 1",
                        AUTOMATICO)

    valor = (peso.valor * (alvo.valor + complementar.valor) * desempenho.valor
             * tempo.valor * revisao.valor)
    return Prioridade(valor=valor, peso=peso, alvo=alvo, complementar=complementar,
                      desempenho=desempenho, tempo=tempo, revisao=revisao)


def ordenar(itens: list, chave_da_prioridade) -> list:
    """Ordena do que mais pede para o que menos pede, e escreve a posicao.

    `chave_da_prioridade(item)` devolve a `Prioridade` do item. O empate
    desempata pelo nome do tema (`item.tema`): duas aberturas seguidas da tela
    tem que dar a mesma ordem.
    """
    ordenados = sorted(itens, key=lambda i: (-chave_da_prioridade(i).valor,
                                             getattr(i, "tema", "")))
    for posicao, item in enumerate(ordenados, start=1):
        p = chave_da_prioridade(item)
        p.posicao, p.de = posicao, len(ordenados)
    return ordenados
