"""Revisao espacada simples, sem IA: assunto errado volta em 1, 7 e 30 dias.

A regra inteira, para um assunto:

  * errei uma questao dele -> revisao 1, para daqui a 1 dia;
  * acertei uma questao dele NA DATA da revisao ou depois -> passa para a
    proxima: 7 dias depois daquele acerto, e entao 30. Passou da de 30 dias,
    o assunto sai da agenda;
  * errei de novo, em qualquer etapa -> volta para a revisao 1;
  * acertar ANTES do vencimento nao conta como revisao: e treino, e o
    espacamento existe justamente para testar o que ficou depois de um tempo.

**A agenda nao mora numa tabela: e calculada do historico de respostas.**
Duas vantagens que valem o recalculo: nao ha estado para dessincronizar, e
descartar um simulado de teste apaga sozinho o que ele tinha agendado - a
resposta sumiu, e a agenda que dependia dela tambem.

O "assunto" e o mesmo do "Onde estudar primeiro": o do catalogo de
palavras-chave para Portugues e Raciocinio Logico, e o do edital para o
resto. Questao sem assunto nenhum - hoje, toda questao de Direito, que ainda
nao foi classificada - agenda a MATERIA inteira, e a tela diz isso: e melhor
revisar "Direito Penal" do que nao revisar nada.

So questao real. Errar uma questao gerada nao agenda nada: ela nao mede o que
a banca cobra, e o assunto dela e o que a IA disse que era.
"""
import random
from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy import select

from radar import macetes
from radar.db import criar_tabelas, sessao
from radar.models import QuestaoDeProva, RespostaDeSimulado, Simulado
from radar.util import para_local

#: Os intervalos da especificacao, em dias, um por etapa.
INTERVALOS = (1, 7, 30)

# Quantas questoes de cada assunto a rodada de revisao traz. Tres testam o
# assunto sem transformar a revisao num simulado inteiro.
POR_ASSUNTO = 3


@dataclass
class Revisao:
    materia: str
    #: None quando a questao nao tem assunto: a revisao e da materia inteira.
    assunto: str | None
    etapa: int                       # 1, 2 ou 3 - qual das revisoes vem agora
    vence_em: date
    #: As questoes deste assunto que eu errei, para a rodada comecar por elas.
    erradas: list[int] = field(default_factory=list)

    @property
    def intervalo(self) -> int:
        return INTERVALOS[self.etapa - 1]

    @property
    def nome(self) -> str:
        return self.assunto or f"{self.materia} (sem assunto)"

    def pendente(self, hoje: date) -> bool:
        return self.vence_em <= hoje

    def atraso(self, hoje: date) -> int:
        return max(0, (hoje - self.vence_em).days)


def assuntos_da_questao(questao) -> list[str | None]:
    """Os assuntos de uma questao, pela mesma regra do Onde estudar primeiro.

    [None] quando nao ha assunto nenhum: a revisao cai na materia.
    """
    chave = macetes.chave_da_materia(questao.materia)
    if chave:
        nomes = macetes.assuntos_do_enunciado(questao.enunciado, chave)
    else:
        nomes = [questao.assunto] if questao.assunto else []
    return nomes or [None]


def agenda(hoje: date | None = None) -> list[Revisao]:
    """Todas as revisoes em aberto, da mais atrasada para a mais distante."""
    criar_tabelas()
    with sessao() as s:
        linhas = s.execute(
            select(QuestaoDeProva, RespostaDeSimulado)
            .join(RespostaDeSimulado, RespostaDeSimulado.questao_id == QuestaoDeProva.id)
            .where(RespostaDeSimulado.escolhida.is_not(None))
            .where(RespostaDeSimulado.gerada.is_(False))
            .where(RespostaDeSimulado.respondida_em.is_not(None))
            # Anulada nao agenda: a banca desfez a pergunta.
            .where(QuestaoDeProva.anulada.is_not(True))
            .order_by(RespostaDeSimulado.respondida_em)
        ).all()

    estado: dict[tuple, Revisao] = {}
    for questao, resposta in linhas:
        dia = para_local(resposta.respondida_em).date()
        for assunto in assuntos_da_questao(questao):
            chave = (questao.materia or "sem materia", assunto)
            atual = estado.get(chave)
            if not resposta.acertou:
                erradas = (atual.erradas if atual else []) + [questao.id]
                estado[chave] = Revisao(chave[0], assunto, 1,
                                        dia + timedelta(days=INTERVALOS[0]),
                                        list(dict.fromkeys(erradas)))
            elif atual is not None and dia >= atual.vence_em:
                if atual.etapa == len(INTERVALOS):
                    del estado[chave]            # passou da ultima: aprendido
                else:
                    atual.etapa += 1
                    atual.vence_em = dia + timedelta(days=atual.intervalo)

    return sorted(estado.values(), key=lambda r: (r.vence_em, r.materia, r.nome))


def pendentes(hoje: date | None = None) -> list[Revisao]:
    """As revisoes que vencem hoje ou ja venceram."""
    hoje = hoje or date.today()
    return [r for r in agenda(hoje) if r.pendente(hoje)]


def criar_simulado_de_revisao(hoje: date | None = None) -> Simulado | None:
    """A rodada das revisoes de hoje. None quando nao ha nenhuma vencida.

    Por assunto, primeiro as questoes que eu errei nele; se faltar, outras
    questoes reais do mesmo assunto que eu ainda nao respondi - e a mesma
    pergunta de novo nao testa se o assunto ficou, testa se a letra ficou.
    """
    vencidas = pendentes(hoje)
    if not vencidas:
        return None

    criar_tabelas()
    with sessao() as s:
        respondidas = set(s.scalars(
            select(RespostaDeSimulado.questao_id)
            .where(RespostaDeSimulado.escolhida.is_not(None))
            .where(RespostaDeSimulado.gerada.is_(False))
        ))
        ids: list[int] = []
        for r in vencidas:
            do_assunto = list(r.erradas[-POR_ASSUNTO:])
            if len(do_assunto) < POR_ASSUNTO:
                candidatas = list(s.scalars(
                    select(QuestaoDeProva)
                    .where(QuestaoDeProva.materia == r.materia)
                    .where(QuestaoDeProva.resposta.is_not(None))
                    .where(QuestaoDeProva.anulada.is_not(True))
                ))
                random.shuffle(candidatas)
                for q in candidatas:
                    if len(do_assunto) >= POR_ASSUNTO:
                        break
                    if q.id in respondidas or q.id in do_assunto or q.id in ids:
                        continue
                    if r.assunto is not None and r.assunto not in assuntos_da_questao(q):
                        continue
                    do_assunto.append(q.id)
            ids.extend(i for i in do_assunto if i not in ids)

        simulado = Simulado(filtros={
            "quantidade": len(ids),
            "revisao": [
                {"materia": r.materia, "assunto": r.assunto, "etapa": r.etapa}
                for r in vencidas
            ],
        })
        s.add(simulado)
        s.flush()
        for ordem, questao_id in enumerate(ids, start=1):
            s.add(RespostaDeSimulado(
                simulado_id=simulado.id, questao_id=questao_id, ordem=ordem
            ))
        return simulado
