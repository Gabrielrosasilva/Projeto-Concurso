"""Revisao espacada 1-7-30: os intervalos e a rodada das revisoes de hoje.

A fila do que revisar e uma so, a do `servico/estudo.py` (decisao 128): o no
da arvore volta por erro recente, por acerto abaixo do corte ou pelo prazo do
1-7-30 vencido. Este arquivo guarda os intervalos da regra e monta a rodada
do botao "Fazer as revisoes de hoje" com os nos dessa fila.

A regra do prazo, para um no:

  * conta do ultimo estudo dele ou, sem estudo, do primeiro contato pratico;
  * acertar questao dele (ou marcar revisao fora do radar) NA DATA do
    vencimento ou depois passa para a proxima etapa: 7 dias depois daquilo, e
    entao 30. Feita a de 30, o prazo acaba;
  * acertar ANTES do vencimento nao conta como revisao: e treino, e o
    espacamento existe justamente para testar o que ficou depois de um tempo.

**Nada disso mora numa tabela: sai do historico.** Nao ha estado para
dessincronizar, e descartar um simulado de teste apaga sozinho o que ele
tinha agendado.

So questao real. A gerada nao mede o que a banca cobra, e o no dela e o que
a IA disse que era.
"""
import random
from datetime import date

from sqlalchemy import select

from radar.db import criar_tabelas, sessao
from radar.models import QuestaoDeProva, RespostaDeSimulado, Simulado

#: Os intervalos da especificacao, em dias, um por etapa.
INTERVALOS = (1, 7, 30)

# Quantas questoes de cada no a rodada de revisao traz. Tres testam o
# conteudo sem transformar a revisao num simulado inteiro.
POR_ASSUNTO = 3


def criar_simulado_de_revisao(hoje: date | None = None, plano=None) -> Simulado | None:
    """A rodada das revisoes de hoje. None quando a fila esta vazia.

    Por ponta da fila (o no mais fundo; a materia e o assunto acima dele
    seriam a mesma revisao), primeiro as questoes que eu errei nele; se
    faltar, outras questoes reais do mesmo no, ou de um no abaixo dele, que eu
    ainda nao respondi - a mesma pergunta de novo nao testa se o conteudo
    ficou, testa se a letra ficou.
    """
    from radar import conteudos as arvore
    from radar.servico import desempenho_por_conteudo as por_conteudo
    from radar.servico import estudo
    from radar.servico.classificacoes import chave_de

    vencidos = estudo.pontas(estudo.para_revisar(plano=plano, hoje=hoje))
    if not vencidos:
        return None

    no_da_questao = por_conteudo.nos_das_questoes()
    criar_tabelas()
    with sessao() as s:
        respondidas = set(s.scalars(
            select(RespostaDeSimulado.questao_id)
            .where(RespostaDeSimulado.escolhida.is_not(None))
            .where(RespostaDeSimulado.gerada.is_(False))
        ))
        ids: list[int] = []
        for r in vencidos:
            do_no = list(r.erradas[-POR_ASSUNTO:])
            if len(do_no) < POR_ASSUNTO:
                materia = arvore.partes(r.caminho)[0]
                candidatas = list(s.scalars(
                    select(QuestaoDeProva)
                    .where(QuestaoDeProva.materia.in_(arvore.grafias_da_materia(materia)))
                    .where(QuestaoDeProva.resposta.is_not(None))
                    .where(QuestaoDeProva.anulada.is_not(True))
                ))
                random.shuffle(candidatas)
                for q in candidatas:
                    if len(do_no) >= POR_ASSUNTO:
                        break
                    if q.id in respondidas or q.id in do_no or q.id in ids:
                        continue
                    caminho = no_da_questao.get(chave_de(q)) or ""
                    if caminho != r.caminho and not caminho.startswith(
                            r.caminho + arvore.SEPARADOR):
                        continue
                    do_no.append(q.id)
            ids.extend(i for i in do_no if i not in ids)
        if not ids:
            # O no venceu so pelo prazo e o acervo nao tem questao nova dele:
            # uma rodada vazia nao revisa nada.
            return None

        simulado = Simulado(filtros={
            "quantidade": len(ids),
            "revisao": [
                {"no": r.caminho, "etapa": r.etapa, "motivos": list(r.motivos)}
                for r in vencidos
            ],
        })
        s.add(simulado)
        s.flush()
        for ordem, questao_id in enumerate(ids, start=1):
            s.add(RespostaDeSimulado(
                simulado_id=simulado.id, questao_id=questao_id, ordem=ordem
            ))
        return simulado
