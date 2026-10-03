"""O sabado: a revisao semanal, o R+7 dos diagnosticos e a comparacao de 07/11
(subetapa 2B, decisao 70).

O que estes testes seguram:
  - a revisao semanal diz os temas da semana do plano, os erros anotados nela
    (por tema) e os artigos-chave dos dias;
  - o R+7 dos diagnosticos refaz so as questoes reais que eu errei nas rodadas
    de 03/10, no maximo o numero do plano, e nao recria a rodada;
  - a comparacao de 07/11 mostra o diagnostico, o fechamento e o ciclo
    separados - nunca somados -, com "Amostra insuficiente" abaixo do minimo.

Nenhum teste depende da data de hoje: o botao de criar rodada so aparece no
dia da faixa, e por isso a tela e conferida pelo que nao muda com a data.
"""
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from radar import cronograma
from radar.db import sessao
from radar.models import QuestaoDeProva, RespostaDeSimulado, Simulado
from radar.servico import composicao, sabado
from radar.servico import erros as caderno
from radar.servico import simulado as servico_simulado
from radar.web.app import app
from tests.test_composicao import CONFIG, PESOS_DO_EDITAL, acervo  # noqa: F401 - fixture

R7 = date(2026, 10, 10)
FECHAMENTO = date(2026, 11, 7)


@pytest.fixture
def plano():
    return cronograma.carregar(CONFIG / "cronograma.yml")


def _responder(simulado_id: int, errar: int) -> list[int]:
    """Responde a rodada inteira errando as `errar` primeiras; devolve os ids
    das erradas."""
    with sessao() as s:
        respostas = list(s.scalars(select(RespostaDeSimulado).where(
            RespostaDeSimulado.simulado_id == simulado_id).order_by(RespostaDeSimulado.ordem)))
        questoes = [s.get(QuestaoDeProva, r.questao_id) for r in respostas]
    erradas = []
    for i, q in enumerate(questoes):
        if i < errar:
            servico_simulado.responder(simulado_id, q.id,
                                       next(letra for letra in q.alternativas if letra != q.resposta))
            erradas.append(q.id)
        else:
            servico_simulado.responder(simulado_id, q.id, q.resposta)
    return erradas


def _diagnosticos(errar_rl: int, errar_pt: int) -> list[int]:
    """As duas rodadas de 03/10, criadas como o botao cria e respondidas. No
    acervo do teste, Raciocinio tem 2 questoes e Portugues 7."""
    rl = composicao.criar_rodada_do_dia(date(2026, 10, 3), "manha", 0)
    pt = composicao.criar_rodada_do_dia(date(2026, 10, 3), "noite", 0)
    return _responder(rl.id, errar_rl) + _responder(pt.id, errar_pt)


def _faixa_do_r7(plano):
    dia = plano.dia(R7)
    indice = next(i for i, f in enumerate(dia.manha) if sabado.refaz_rodadas(f))
    return indice, dia.manha[indice]


# --- a revisao semanal --------------------------------------------------------------

def test_a_revisao_semanal_traz_os_temas_os_erros_e_os_artigos(banco_temporario, plano):
    caderno.anotar(date(2026, 9, 28), "Direito Penal",
                   "Aprendizagem: Aplicação da lei penal (arts. 1º a 12)", "nao_sabia",
                   "A lei mais benéfica retroage.", hoje=date(2026, 9, 28))
    caderno.anotar(date(2026, 9, 29), "Língua Portuguesa",
                   "Substantivo e adjetivo (flexão nominal)", "confundi",
                   "Plural dos compostos.", hoje=date(2026, 9, 29))
    caderno.anotar(date(2026, 9, 30), "Direito Penal", "Uma questão solta", "chutei",
                   "Ler o enunciado inteiro.", hoje=date(2026, 9, 30))
    # De outra semana: nao entra.
    caderno.anotar(date(2026, 10, 5), "Direito Penal", "Fato típico e nexo causal (art. 13)",
                   "chutei", "Omissão relevante.", hoje=date(2026, 10, 5))

    r = sabado.revisao_da_semana(date(2026, 10, 3), plano)

    assert (r.inicio, r.fim) == (date(2026, 9, 28), date(2026, 10, 2))
    assert r.erros == 3 and r.sem_tema == 1
    assert len(r.temas) == 10
    assert [(t.tema, t.erros) for t in r.mais_erros] == [
        ("Aplicação da lei penal (arts. 1º a 12)", 1),
        ("Substantivo e adjetivo (flexão nominal)", 1)]
    assert {m.nome for m in r.motivos} == {"Não sabia", "Confundi", "Chutei"}
    assert any(a.artigos == "CP art. 1º" for a in r.artigos)
    assert all(r.inicio <= a.data <= r.fim for a in r.artigos)


def test_a_revisao_semanal_sem_erro_anotado_diz_zero(banco_temporario, plano):
    r = sabado.revisao_da_semana(date(2026, 10, 10), plano)
    assert (r.inicio, r.fim) == (date(2026, 10, 5), date(2026, 10, 9))
    assert r.erros == 0 and not r.mais_erros


# --- o R+7 dos diagnosticos -----------------------------------------------------------

def test_so_o_r7_dos_diagnosticos_refaz_rodadas(plano):
    refazem = [(d.data, f.titulo) for d in plano.dias for f in d.faixas()
               if sabado.refaz_rodadas(f)]
    assert refazem == [(R7, "R+7: refazer os erros dos diagnósticos")]


def test_o_r7_refaz_so_os_erros_reais_dos_diagnosticos(acervo, plano):
    erradas = _diagnosticos(errar_rl=1, errar_pt=2)
    indice, faixa = _faixa_do_r7(plano)

    r = sabado.erros_das_rodadas(R7, "manha", indice, faixa, plano)

    assert len(r.rodadas) == 2
    assert sorted(e.questao_id for e in r.erros) == sorted(erradas)
    assert len(r.escolhidos) == 3          # 3 erros, o plano pede 5: refaz todos


def test_o_r7_refaz_no_maximo_o_numero_do_plano_pelo_assunto_com_mais_erro(acervo, plano):
    """9 erros (2 de conjuntos, 4 de interpretacao, 2 de crase, 1 de
    ortografia) para 5 questoes: o assunto em que mais errei volta mais."""
    _diagnosticos(errar_rl=2, errar_pt=7)
    indice, faixa = _faixa_do_r7(plano)

    r = sabado.erros_das_rodadas(R7, "manha", indice, faixa, plano)

    assert len(r.erros) == 9
    assert len(r.escolhidos) == faixa.questoes == 5
    assunto, erros, refeitos = r.por_assunto[0]
    assert assunto.endswith("Compreensão e interpretação de texto (s)")
    assert (erros, refeitos) == (4, 2)
    assert sum(linha[2] for linha in r.por_assunto) == 5


def test_a_rodada_do_r7_so_tem_os_erros_e_nao_e_recriada(acervo, plano):
    erradas = _diagnosticos(errar_rl=1, errar_pt=2)
    indice, faixa = _faixa_do_r7(plano)

    rodada = sabado.criar_rodada_dos_erros(R7, "manha", indice, faixa, plano)
    de_novo = sabado.criar_rodada_dos_erros(R7, "manha", indice, faixa, plano)

    assert rodada.id == de_novo.id
    with sessao() as s:
        simulado = s.get(Simulado, rodada.id)
        respostas = list(s.scalars(select(RespostaDeSimulado).where(
            RespostaDeSimulado.simulado_id == rodada.id)))
    assert sorted(r.questao_id for r in respostas) == sorted(erradas)
    assert all(not r.gerada for r in respostas)            # so questao real
    assert simulado.filtros["erros"] is True
    assert simulado.filtros["origem"]["dia"] == "2026-10-03"
    assert sabado.erros_das_rodadas(R7, "manha", indice, faixa, plano).rodada_id == rodada.id


def test_sem_rodada_nos_diagnosticos_o_r7_nao_cria_nada(acervo, plano):
    indice, faixa = _faixa_do_r7(plano)
    r = sabado.erros_das_rodadas(R7, "manha", indice, faixa, plano)
    assert r.rodadas == [] and r.erros == []
    assert sabado.criar_rodada_dos_erros(R7, "manha", indice, faixa, plano) is None


# --- a comparacao de 07/11 --------------------------------------------------------------

def test_a_comparacao_separa_diagnostico_e_fechamento_e_marca_a_amostra(
        acervo, plano, monkeypatch):
    """Raciocinio Logico: 1 erro em 2 no diagnostico, nenhum em 2 no
    fechamento. Os dois numeros ficam lado a lado, e nenhum vira 3 de 4."""
    monkeypatch.setattr(composicao, "_pesos_do_edital", lambda materias: {
        **PESOS_DO_EDITAL, "Raciocínio Lógico": 10})
    _diagnosticos(errar_rl=1, errar_pt=0)
    dia = plano.dia(FECHAMENTO)
    indice = next(i for i, f in enumerate(dia.noite) if composicao.mede(f))
    fechamento = composicao.criar_rodada(FECHAMENTO, "noite", indice, dia.noite[indice])
    _responder(fechamento.id, errar=0)
    correcao = next(f for f in dia.noite if f.compara_com)

    c = sabado.comparacao(FECHAMENTO, correcao, plano)

    assert c.com == date(2026, 10, 3) and c.minimo == 20
    assert len(c.linhas) == 6
    linhas = {linha.materia: linha for linha in c.linhas}
    rl = linhas["Raciocínio Lógico"]
    assert (rl.diagnostico.acertos, rl.diagnostico.respondidas) == (1, 2)
    assert (rl.fechamento.acertos, rl.fechamento.respondidas) == (2, 2)
    assert not rl.diagnostico.suficiente and not rl.fechamento.suficiente
    assert linhas["Direitos Humanos"].diagnostico is None


# --- a tela ---------------------------------------------------------------------------

def test_o_sabado_10_10_mostra_a_revisao_e_os_erros_dos_diagnosticos(acervo, monkeypatch):
    monkeypatch.setattr(composicao, "_pesos_do_edital", lambda materias: PESOS_DO_EDITAL)
    _diagnosticos(errar_rl=1, errar_pt=2)
    pagina = TestClient(app).get("/hoje?data=2026-10-10").text

    assert "A semana de 05/10 a 09/10." in pagina
    assert "(3) Os artigos-chave da semana" in pagina
    assert "3 erros nos diagnósticos de 03/10." in pagina
    assert "Esta faixa refaz todos." in pagina


def test_o_botao_do_r7_cria_a_rodada_e_a_faixa_passa_a_abrir_ela(acervo, plano, monkeypatch):
    monkeypatch.setattr(composicao, "_pesos_do_edital", lambda materias: PESOS_DO_EDITAL)
    _diagnosticos(errar_rl=1, errar_pt=2)
    indice, _faixa = _faixa_do_r7(plano)
    cliente = TestClient(app)

    resposta = cliente.post("/hoje/rodada", data={"data": R7.isoformat(), "bloco": "manha",
                                                  "indice": str(indice)},
                            follow_redirects=False)

    assert resposta.status_code == 303
    assert resposta.headers["location"].startswith("/simulado/")
    assert "Abrir a rodada desta faixa" in cliente.get("/hoje?data=2026-10-10").text


def test_o_07_11_mostra_a_tabela_da_comparacao(acervo, monkeypatch):
    monkeypatch.setattr(composicao, "_pesos_do_edital", lambda materias: {
        **PESOS_DO_EDITAL, "Raciocínio Lógico": 10})
    _diagnosticos(errar_rl=1, errar_pt=0)
    pagina = TestClient(app).get("/hoje?data=2026-11-07").text

    assert "Diagnóstico de 03/10" in pagina and "Fechamento de 07/11" in pagina
    assert "1 de 2 · 50%" in pagina
    assert "Amostra insuficiente" in pagina
    assert "sem diagnóstico" in pagina                 # Direitos Humanos
    assert "três medidas separadas, que não se somam" in pagina
