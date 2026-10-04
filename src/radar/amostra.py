"""Ja da para acreditar neste numero? Os minimos de amostra, num lugar so.

Antes desta etapa a mesma pergunta tinha tres respostas diferentes no codigo:
5 na materia e 3 no assunto do "Onde estudar", 20 em "Minhas materias", e um
3 no caderno de erros que media outra coisa. Tres reguas para a mesma duvida
davam tres leituras do mesmo dia.

Agora a regua e uma, vem do `config/amostra.yml` e muda sem tocar em codigo.
Os valores sao os da decisao 6 da Etapa 0 (docs/decisoes.md):

    materia      20 respostas sem consulta
    assunto      10
    subassunto    6
    elemento      6

**Por que estes numeros.** Com 10 questoes a margem de uma porcentagem ainda
e de uns 30 pontos: 7 de 10 pode ser 55% ou 85% de verdade. Com 20 ela cai
para uns 22. Nenhum dos dois e certeza; o que o minimo faz e impedir o sistema
de dizer "voce e fraco em X" porque eu respondi duas questoes (novo.md, §16).
No subassunto e no elemento o minimo e menor por necessidade: ha subassunto
com 6 questoes no acervo inteiro, e exigir 10 ali seria nunca medir nada -
nao por falta de estudo meu, mas por falta de prova.

**O 3 do caderno de erros fica onde esta, de proposito.** Ele nao mede acerto:
mede a fatia de cada motivo de erro ("3 dos meus 10 erros foram por pressa").
E outra pergunta, com outro risco, e misturar as duas na mesma regua tornaria
as duas erradas. Esta anotado no `servico/erros.py`.

**Os tres que tinham ficado no codigo vieram para ca em 04/10** (decisao 83):
a evolucao da home (20 respostas por metade), a tendencia de letra no
gabarito (50 questoes) e o "base pequena" (menos de 3 provas). E o tamanho da
amostra com que se confere a classificacao do catalogo (20 por materia) nasceu
aqui, na mesma data.

Modulo puro: recebe contagem e devolve estado. Quem varre o banco e o
`servico/desempenho.py`.
"""
from dataclasses import dataclass
from pathlib import Path

import yaml

from radar import config

# Os niveis da arvore de conteudos, do mais largo ao mais fundo. O mesmo
# vocabulario do `radar.conteudos`, para o estado de um no sair do nivel dele
# sem ninguem traduzir nome.
NIVEIS = ("materia", "assunto", "subassunto", "elemento")

# Os cinco estados pedidos na §16 do novo.md, na ordem em que eles pioram -
# do que nao da para ler ao que esta bom. O nome e o que a tela escreve.
INSUFICIENTE = "Amostra insuficiente"
PRECISA_REVISAR = "Precisa revisar"
EM_APRENDIZADO = "Em aprendizado"
CONSISTENTE = "Desempenho consistente"
BOM_COM_AMOSTRA = "Bom desempenho com amostra suficiente"

#: A meta da prova inteira do edital de 2019: 79 de 100. E o que vale para a
#: materia que nao tem meta propria no config/cronograma.yml.
META_DA_PROVA = 79


@dataclass(frozen=True)
class Minimos:
    """Quantas respostas sem consulta cada nivel precisa, e os cortes."""

    por_nivel: dict[str, int]

    #: Abaixo disto o no "precisa revisar", mesmo que a meta dele seja menor.
    precisa_revisar_abaixo_de: int = 60

    #: Quantas vezes o minimo, para o estado virar "bom desempenho".
    vezes_o_minimo: int = 2

    #: Em quantos dias diferentes, para o mesmo estado. Um dia so pode ter
    #: sido a tarde em que o assunto estava fresco na cabeca.
    dias_distintos: int = 2

    #: A meta de quem nao tem meta propria.
    meta_padrao: int = META_DA_PROVA

    #: A evolucao do meu acerto (a home): respostas em cada metade da
    #: comparacao dos ultimos 30 dias (secao `desempenho`).
    evolucao: int = 20

    #: Estes dois falam da BANCA, e nao de mim (secao `acervo`): questoes com
    #: gabarito para falar de tendencia de letra nos Macetes, e provas abaixo
    #: das quais o que sai delas leva o aviso "base pequena".
    tendencia_de_gabarito: int = 50
    provas_para_tendencia: int = 3

    #: Quantas propostas do catalogo eu confiro por materia (a amostra da
    #: pendencia B.8). Tambem da secao `acervo`: fala da classificacao dele.
    amostra_do_catalogo: int = 20

    def do_nivel(self, nivel: str) -> int:
        """O minimo daquele nivel. Nivel que eu nao conheco usa o da materia,
        que e o mais exigente: na duvida, medir menos e nao medir errado."""
        return int(self.por_nivel.get(nivel, self.por_nivel.get("materia", 20)))


#: Os valores da decisao 6, para o caso de o arquivo nao existir (teste que
#: monta um config so com a secao do acervo, por exemplo).
PADRAO = Minimos(por_nivel={"materia": 20, "assunto": 10,
                            "subassunto": 6, "elemento": 6})


def carregar(caminho: Path | None = None) -> Minimos:
    """Os minimos do `config/amostra.yml`, secao `desempenho`."""
    arquivo = caminho or (config.diretorio_config() / "amostra.yml")
    if not Path(arquivo).exists():
        return PADRAO
    dados = yaml.safe_load(Path(arquivo).read_text(encoding="utf-8")) or {}
    secao = dados.get("desempenho") or {}

    por_nivel = dict(PADRAO.por_nivel)
    for nivel, valor in (secao.get("minimos") or {}).items():
        if nivel in NIVEIS:
            por_nivel[nivel] = int(valor)

    bom = secao.get("bom_desempenho") or {}
    acervo = dados.get("acervo") or {}
    return Minimos(
        por_nivel=por_nivel,
        precisa_revisar_abaixo_de=int(
            secao.get("precisa_revisar_abaixo_de", PADRAO.precisa_revisar_abaixo_de)),
        vezes_o_minimo=int(bom.get("vezes_o_minimo", PADRAO.vezes_o_minimo)),
        dias_distintos=int(bom.get("dias_distintos", PADRAO.dias_distintos)),
        meta_padrao=int(secao.get("meta_padrao", PADRAO.meta_padrao)),
        evolucao=int(secao.get("evolucao", PADRAO.evolucao)),
        tendencia_de_gabarito=int(
            acervo.get("tendencia_de_gabarito", PADRAO.tendencia_de_gabarito)),
        provas_para_tendencia=int(
            acervo.get("provas_para_tendencia", PADRAO.provas_para_tendencia)),
        amostra_do_catalogo=int(
            acervo.get("amostra_do_catalogo", PADRAO.amostra_do_catalogo)),
    )


@dataclass(frozen=True)
class Estado:
    """Em que pe esta um no, e com que amostra se disse isso."""

    nome: str
    respostas: int
    acertos: int
    minimo: int
    nivel: str
    meta: int
    dias: int

    @property
    def suficiente(self) -> bool:
        return self.respostas >= self.minimo

    @property
    def porcentagem(self) -> int | None:
        """None sem resposta nenhuma - e NAO zero, que diria que eu errei
        tudo quando o que houve foi eu nao ter treinado."""
        if not self.respostas:
            return None
        return round(100 * self.acertos / self.respostas)

    @property
    def entra_na_ordenacao(self) -> bool:
        """Abaixo do minimo o numero aparece na tela e nao ordena nada
        (decisao 6): sem isto um unico erro joga o no para o topo com "0%"."""
        return self.suficiente

    @property
    def amostra(self) -> str:
        """"7 de 10 respostas sem consulta": o que toda linha leva ao lado."""
        palavra = "resposta" if self.respostas == 1 else "respostas"
        return f"{self.acertos} de {self.respostas} {palavra} sem consulta"

    @property
    def falta_para_o_minimo(self) -> int:
        return max(0, self.minimo - self.respostas)


def estado(
    respostas: int,
    acertos: int,
    *,
    nivel: str = "materia",
    meta: int | None = None,
    dias: int = 0,
    minimos: Minimos | None = None,
) -> Estado:
    """O estado de um no, pelos limites do `config/amostra.yml`.

    - `respostas` e `acertos`: so o que foi respondido SEM CONSULTA. Com a lei
      aberta eu acerto o que na prova eu nao acertaria, e o estado existe para
      falar da prova;
    - `meta`: a da materia (`config/cronograma.yml`); sem ela, a da prova;
    - `dias`: em quantos dias diferentes eu respondi. So pesa no estado mais
      alto.
    """
    minimos = minimos or PADRAO
    minimo = minimos.do_nivel(nivel)
    alvo = minimos.meta_padrao if meta is None else meta

    bruto = Estado(nome=INSUFICIENTE, respostas=respostas, acertos=acertos,
                   minimo=minimo, nivel=nivel, meta=alvo, dias=dias)
    if not bruto.suficiente:
        return bruto

    taxa = bruto.porcentagem
    if taxa < minimos.precisa_revisar_abaixo_de:
        nome = PRECISA_REVISAR
    elif taxa < alvo:
        nome = EM_APRENDIZADO
    elif (respostas >= minimo * minimos.vezes_o_minimo
          and dias >= minimos.dias_distintos):
        nome = BOM_COM_AMOSTRA
    else:
        nome = CONSISTENTE
    return Estado(nome=nome, respostas=respostas, acertos=acertos,
                  minimo=minimo, nivel=nivel, meta=alvo, dias=dias)


def frase_da_amostra_pequena(estado_do_no: Estado) -> str:
    """O que a tela escreve em vez de uma porcentagem em que nao se acredita."""
    if not estado_do_no.respostas:
        return "Ainda não respondi nenhuma questão sem consulta deste conteúdo."
    palavra = "resposta" if estado_do_no.respostas == 1 else "respostas"
    return (
        f"Amostra insuficiente: {estado_do_no.respostas} {palavra} sem consulta, "
        f"abaixo das {estado_do_no.minimo} que fazem o número valer neste nível."
    )
