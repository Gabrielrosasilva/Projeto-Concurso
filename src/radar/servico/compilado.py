"""O simulado compilado: uma prova de 40, 50 ou 100 questoes com a cara da real.

A distribuicao segue o QUADRO DO EDITAL de 2019, lido do PDF pelo
`foco.quadro_do_edital` - e nunca digitado aqui. Se o proximo edital mudar o
quadro, o compilado muda junto, sem ninguem mexer neste arquivo.

As regras, na ordem em que valem:

  * **so questao real.** Questao gerada nao entra no compilado, e ponto: ele
    quer ser a prova, e prova da banca nao tem questao escrita por IA;
  * **o peso e o do edital**, restrito as materias que eu escolher. Com
    todas, 40 questoes viram 6 de Portugues, 4 de LEP, 2 de Direito Penal...
    A divisao e pelo maior resto: cada materia leva a parte inteira da sua
    fatia, e as questoes que sobram vao para as de maior resto;
  * **de onde vem**: primeiro a prova do meu cargo, depois a mesma banca nas
    mesmas materias - a mesma ordem do "Treinar" da home - e so entao o que
    eu ja respondi;
  * **faltou questao numa materia, falta mesmo.** O compilado entrega o que
    ha e diz quanto faltou. Completar com outra materia desfiguraria o peso,
    que e o motivo inteiro de ele existir.
"""
import random
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from radar import foco
from radar.db import criar_tabelas, sessao
from radar.models import RespostaDeSimulado, Simulado
from radar.regioes import normalizar
from radar.servico import simulado as treino

#: Os tamanhos que a tela oferece, os da especificacao. Sao opcoes de tela, e
#: nao dado: o peso de cada materia sai do edital.
TAMANHOS = (40, 50, 100)

# O caderno de 2013 escreve "Direito Processo Penal" e o edital de 2019
# "Direito Processual Penal". Parecidos a partir disto sao a mesma materia -
# o mesmo limite da auditoria, que ja separa "Estadual" de "Especial" (0,78).
PARECIDO_O_BASTANTE = 0.85


def _chave(nome: str | None) -> str:
    return "".join(c for c in normalizar(nome or "") if c.isalpha())


def mesma_materia(do_edital: str, da_questao: str | None) -> bool:
    a, b = _chave(do_edital), _chave(da_questao)
    if not a or not b:
        return False
    return a == b or SequenceMatcher(None, a, b).ratio() >= PARECIDO_O_BASTANTE


def distribuir(pesos: dict[str, int], tamanho: int) -> dict[str, int]:
    """{materia: quantas questoes}, proporcional ao peso, somando `tamanho`.

    Maior resto: a parte inteira de cada fatia primeiro; o que sobrar vai
    para as maiores fracoes. Empate de fracao vai para a materia de maior
    peso - e a que mais decide a prova.
    """
    total = sum(pesos.values())
    if not total or tamanho <= 0:
        return {}
    exatas = {m: tamanho * p / total for m, p in pesos.items()}
    inteiras = {m: int(x) for m, x in exatas.items()}
    sobra = tamanho - sum(inteiras.values())
    ordem = sorted(pesos, key=lambda m: (-(exatas[m] - inteiras[m]), -pesos[m], m))
    for m in ordem[:sobra]:
        inteiras[m] += 1
    return inteiras


@dataclass
class LinhaDoCompilado:
    materia: str
    peso_no_edital: int
    pedidas: int
    entregues: int = 0
    disponiveis: int = 0

    @property
    def faltaram(self) -> int:
        return max(0, self.pedidas - self.entregues)


@dataclass
class Plano:
    tamanho: int
    arquivo_do_edital: str | None
    ano_do_edital: int | None
    linhas: list[LinhaDoCompilado] = field(default_factory=list)

    @property
    def faltaram(self) -> int:
        return sum(l.faltaram for l in self.linhas)


def _pesos(escolhidas: list[str] | None) -> tuple[dict[str, int], foco.EditalLido, str | None]:
    edital, arquivo = foco.quadro_do_edital()
    pesos = {m.nome: m.questoes for m in edital.materias}
    if escolhidas:
        chaves = {_chave(e) for e in escolhidas}
        pesos = {m: p for m, p in pesos.items() if _chave(m) in chaves}
    return pesos, edital, arquivo


def _por_materia(questoes: list, materia: str) -> list:
    return [q for q in questoes if mesma_materia(materia, q.materia)]


def planejar(tamanho: int, escolhidas: list[str] | None = None) -> Plano | None:
    """Quantas de cada materia, e quantas o acervo tem. NAO cria nada.

    None quando nao ha quadro do edital: sem peso lido, nao ha compilado.
    """
    pesos, edital, arquivo = _pesos(escolhidas)
    if not pesos:
        return None

    criar_tabelas()
    with sessao() as s:
        proprias, da_banca = treino._questoes_para_o_alvo(s)
    plano = Plano(tamanho=tamanho, arquivo_do_edital=arquivo, ano_do_edital=edital.ano)
    for materia, pedidas in distribuir(pesos, tamanho).items():
        impressoes = {q.impressao for q in _por_materia(proprias + da_banca, materia)}
        plano.linhas.append(LinhaDoCompilado(
            materia=materia, peso_no_edital=pesos[materia], pedidas=pedidas,
            disponiveis=len(impressoes),
        ))
    return plano


def criar_simulado_compilado(
    tamanho: int, escolhidas: list[str] | None = None
) -> tuple[Simulado, Plano] | None:
    """Monta a rodada compilada. None sem quadro do edital ou sem questao."""
    plano = planejar(tamanho, escolhidas)
    if plano is None:
        return None

    criar_tabelas()
    escolhidos: list[int] = []
    origem = treino.OrigemDasQuestoes()
    with sessao() as s:
        proprias, da_banca = treino._questoes_para_o_alvo(s)
        respondidas = treino._impressoes_ja_respondidas(s)
        vistas: set[str] = set()

        # Na ordem do edital, como a prova real: materia por materia, e
        # embaralhado so dentro de cada uma.
        for linha in plano.linhas:
            minhas = _por_materia(proprias, linha.materia)
            da_mesma_banca = _por_materia(da_banca, linha.materia)
            camadas = []
            for questoes, campo in ((minhas, "proprias"), (da_mesma_banca, "da_banca")):
                novas = [q for q in questoes if q.impressao not in respondidas]
                random.shuffle(novas)
                camadas.append((novas, campo))
            for questoes in (minhas, da_mesma_banca):
                velhas = [q for q in questoes if q.impressao in respondidas]
                random.shuffle(velhas)
                camadas.append((velhas, "repetidas"))

            da_materia: list[int] = []
            for questoes, campo in camadas:
                for q in questoes:
                    if len(da_materia) >= linha.pedidas:
                        break
                    if q.impressao in vistas:
                        continue
                    vistas.add(q.impressao)
                    da_materia.append(q.id)
                    setattr(origem, campo, getattr(origem, campo) + 1)
            linha.entregues = len(da_materia)
            escolhidos.extend(da_materia)

        if not escolhidos:
            return None

        simulado = Simulado(filtros={
            "quantidade": len(escolhidos),
            "compilado": tamanho,
            "edital": plano.arquivo_do_edital,
            "ano_do_edital": plano.ano_do_edital,
            "distribuicao": [
                {"materia": l.materia, "pedidas": l.pedidas, "entregues": l.entregues}
                for l in plano.linhas
            ],
            **origem.como_dicionario(),
        })
        s.add(simulado)
        s.flush()
        for ordem, questao_id in enumerate(escolhidos, start=1):
            # So questao real: `gerada` fica no padrao, falso. O compilado
            # nunca alcanca a tabela das geradas.
            s.add(RespostaDeSimulado(
                simulado_id=simulado.id, questao_id=questao_id, ordem=ordem
            ))
    return simulado, plano
