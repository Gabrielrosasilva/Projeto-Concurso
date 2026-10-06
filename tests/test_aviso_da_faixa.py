"""A faixa avisa o que ja foi respondido no radar por ela (06/10/2026).

O caso que motivou: o 05/10. As questoes das faixas foram respondidas no
radar - reais e geradas - e anotadas de novo no "fiz X, acertei Y", com o
numero do plano ja preenchido: 26 questoes contadas duas vezes, e 23 de IA
entrando como acerto real. Estes testes seguram o conserto (avisar, e nao
bloquear, por escolha sua):

  * o `metricas` conta, por faixa, o que foi respondido nas rodadas que ela
    abriu - a das reais (`faixa`) e a de geradas (`da_faixa`);
  * a rodada de geradas aberta pelo botao da faixa guarda a faixa numa chave
    propria, e nao toma o lugar da rodada que mede;
  * a tela avisa, e o "fiz" nao vem com o numero do plano.

As datas sao fixas: nada aqui depende do dia em que o teste roda.
"""
import re
from datetime import date, datetime
from types import SimpleNamespace

from fastapi.testclient import TestClient
from markupsafe import escape
from sqlalchemy import select

from radar import cronograma
from radar.db import sessao
from radar.models import QuestaoGerada, RespostaDeSimulado, Simulado
from radar.servico import composicao, geradas, metricas
from radar.servico import cronograma as diario
from radar.util import fuso_local
from radar.web.app import app

SEG = date(2026, 9, 28)
NO = "Língua Portuguesa > Vozes do verbo"


def _identidade(bloco="manha", indice=6, titulo="Fixação: Vozes do verbo", data=SEG):
    return {"data": data.isoformat(), "bloco": bloco, "indice": indice, "titulo": titulo}


def _rodada(filtros, respostas):
    """Uma rodada com as respostas dadas: [(acertou, gerada)]; None = em branco."""
    quando = datetime(2026, 9, 28, 21, 0, tzinfo=fuso_local())
    with sessao() as s:
        simulado = Simulado(filtros=filtros)
        s.add(simulado)
        s.flush()
        for ordem, resposta in enumerate(respostas, start=1):
            acertou, gerada = resposta if resposta else (None, False)
            s.add(RespostaDeSimulado(
                simulado_id=simulado.id, questao_id=ordem, gerada=gerada, ordem=ordem,
                escolhida="a" if resposta else None, acertou=acertou,
                respondida_em=quando if resposta else None,
            ))
        return simulado.id


def test_conta_por_faixa_as_reais_e_as_de_ia(banco_temporario):
    # As reais da faixa de Portugues: 2 respondidas (1 certa) e 1 em branco.
    _rodada({"faixa": _identidade()}, [(True, False), (False, False), None])
    # As geradas que a mesma faixa abriu: 3, 2 certas.
    _rodada({"geradas": True, "da_faixa": _identidade()},
            [(True, True), (True, True), (False, True)])
    # A de outra faixa do dia, e uma de outro dia e uma sem faixa: nao entram nesta.
    _rodada({"geradas": True, "da_faixa": _identidade("noite", 0, "R+7: outro tema")},
            [(True, True)])
    _rodada({"da_faixa": _identidade(data=date(2026, 9, 29))}, [(True, True)])
    _rodada({}, [(True, False)])

    por_faixa = metricas.no_radar_por_faixa(SEG)

    vozes = por_faixa[("manha", 6, "Fixação: Vozes do verbo")]
    assert (vozes.questoes, vozes.acertos, vozes.erros, vozes.ia, vozes.ia_acertos) == (5, 1, 1, 3, 2)
    assert por_faixa[("noite", 0, "R+7: outro tema")].ia == 1
    assert len(por_faixa) == 2
    assert metricas.no_radar_por_faixa(date(2026, 9, 30)) == {}


def _geradas_no_no(quantas=3):
    with sessao() as s:
        for i in range(quantas):
            s.add(QuestaoGerada(modo="do_zero", enunciado=f"gerada {i}", impressao=f"g{i}",
                                resposta="a", conteudo=NO, materia="Língua Portuguesa"))


def test_a_rodada_de_geradas_guarda_a_faixa_sem_tomar_o_lugar_da_que_mede(banco_temporario):
    _geradas_no_no()

    rodada = geradas.criar_simulado(quantidade=2, conteudo=NO, da_faixa=_identidade())

    assert rodada.filtros["da_faixa"] == _identidade()
    assert "faixa" not in rodada.filtros
    # O `rodada_da_faixa` acha a rodada que mede pela chave `faixa`: a de
    # geradas nao pode aparecer ali.
    faixa = SimpleNamespace(titulo="Fixação: Vozes do verbo")
    assert composicao.rodada_da_faixa(SEG, "manha", 6, faixa) is None
    # Sem faixa, a rodada continua como era.
    assert "da_faixa" not in geradas.criar_simulado(quantidade=1, conteudo=NO).filtros


def test_o_botao_treinar_da_faixa_manda_a_faixa(banco_temporario):
    _geradas_no_no()

    resposta = TestClient(app).post("/geradas/treinar", data={
        "conteudo": NO, "quantidade": "2", "data": "2026-09-28", "bloco": "manha",
        "indice": "6", "titulo": "Fixação: Vozes do verbo"}, follow_redirects=False)

    assert resposta.status_code == 303
    with sessao() as s:
        (simulado,) = s.scalars(select(Simulado))
        assert simulado.filtros["da_faixa"] == _identidade()


def test_o_botao_sem_faixa_ou_com_indice_torto_nao_guarda_faixa(banco_temporario):
    _geradas_no_no()
    cliente = TestClient(app)

    cliente.post("/geradas/treinar", data={"conteudo": NO, "quantidade": "1"},
                 follow_redirects=False)
    cliente.post("/geradas/treinar", data={
        "conteudo": NO, "quantidade": "1", "data": "2026-09-28", "bloco": "manha",
        "indice": "seis", "titulo": "x"}, follow_redirects=False)

    with sessao() as s:
        assert all("da_faixa" not in sim.filtros for sim in s.scalars(select(Simulado)))


def _primeira_faixa_de_questoes(plano, data):
    dia = cronograma.montar_dia(plano, data, 1)
    for bloco in cronograma.TODOS_OS_BLOCOS:
        for indice, faixa in enumerate(getattr(dia, bloco)):
            if cronograma.tem_acerto(faixa) and faixa.questoes:
                return bloco, indice, faixa
    raise AssertionError("o 28/09 do plano real nao tem faixa de questoes")


def _o_campo_fiz(texto, bloco, indice, titulo) -> str:
    """O valor do "fiz" no formulario da faixa."""
    achado = re.search(
        rf'name="bloco" value="{bloco}">\s*<input type="hidden" name="indice" value="{indice}">'
        rf'\s*<input type="hidden" name="titulo" value="{re.escape(str(escape(titulo)))}">'
        rf'\s*<label>fiz\s*<input type="number" name="questoes"[^>]*?value="([^"]*)"',
        texto)
    assert achado, "o formulario da faixa nao apareceu"
    return achado.group(1)


def test_a_tela_avisa_e_o_fiz_nao_vem_com_o_numero_do_plano(banco_temporario, monkeypatch):
    plano = cronograma.carregar()
    bloco, indice, faixa = _primeira_faixa_de_questoes(plano, SEG)
    monkeypatch.setattr(diario, "agora_local",
                        lambda: datetime(2026, 9, 30, 12, 0, tzinfo=fuso_local()))
    cliente = TestClient(app)

    # Sem nada no radar: sem aviso, e o "fiz" com o numero do plano, como sempre.
    antes = cliente.get("/hoje?data=2026-09-28").text
    assert "desta faixa no radar" not in antes
    assert _o_campo_fiz(antes, bloco, indice, faixa.titulo) == str(faixa.questoes)

    _rodada({"geradas": True, "da_faixa": _identidade(bloco, indice, faixa.titulo)},
            [(True, True), (False, True)])
    depois = cliente.get("/hoje?data=2026-09-28").text

    assert ("Você já respondeu <b>2 questões</b> desta faixa no radar (de IA):"
            in depois)
    assert "anote só as que fez fora do radar, no Qconcursos" in depois
    assert _o_campo_fiz(depois, bloco, indice, faixa.titulo) == ""
