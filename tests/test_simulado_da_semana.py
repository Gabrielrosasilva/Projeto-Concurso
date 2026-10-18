"""O Simulado da semana e os sabados leves (decisao 170).

O que estes testes seguram:
  - a faixa com `treino` nunca mede, mesmo no radar: nao vira rodada que mede,
    nao reserva questao, nao entra na comparacao e deixa o Plano B do sabado;
  - o carregamento so aceita `treino` em simulado, e `anteriores` so com ele;
  - a composicao e a da decisao 69 em duas partes: os temas de segunda a sexta
    da semana do plano e, a parte, os de antes;
  - cada tema sai primeiro do radar, so questao real: a FEPESE fora da
    reserva, depois outras bancas, as nunca feitas primeiro; o que falta fica
    no Qconcursos; uma questao uma vez so;
  - a rodada criada corrige no fim, guarda a faixa e nao e recriada;
  - a Revisao rapida nao mostra as "5 regras" nem os artigos-chave;
  - a tela e o `radar hoje` mostram a composicao.

Os dias sao fixos (24/10 do plano real); o "hoje" da tela e trocado pelo teste.
"""
import json
from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from typer.testing import CliRunner

from radar import cronograma
from radar.cli import app as cli
from radar.cronograma import Faixa
from radar.db import sessao
from radar.models import QuestaoDeProva, RespostaDeSimulado
from radar.servico import composicao, outras_bancas, sabado, simulado_da_semana
from radar.servico import cronograma as diario
from radar.servico import fichas as servico_fichas
from radar.servico import simulado as servico_simulado
from radar.web.app import app
from tests.test_composicao import (CONFIG, CONJUNTOS, INTERPRETACAO,  # noqa: F401
                                   PESOS_DO_EDITAL, PORTUGUES, RACIOCINIO, acervo)
from tests.test_outras_bancas import _de_outra

SABADO = date(2026, 10, 24)
SEGUNDA = date(2026, 10, 19)
PESOS = {**PESOS_DO_EDITAL, RACIOCINIO: 10}


@pytest.fixture
def plano():
    return cronograma.carregar(CONFIG / "cronograma.yml")


def _faixa(**extra):
    base = dict(bloco="manha", tipo="simulado", titulo="Simulado da semana", questoes=25,
                onde="radar", treino=True, anteriores=5,
                materias_da_rodada=(PORTUGUES, RACIOCINIO))
    base.update(extra)
    return Faixa(**base)


def _parte(parte, temas):
    """Uma Composicao com um tema por linha: (materia, nome, pedidas, nos)."""
    materias = {}
    for ordem, (materia, nome, pedidas, nos) in enumerate(temas):
        materias.setdefault(materia, []).append(composicao.AssuntoNaComposicao(
            ordem=ordem, caminho=f"tema:{nome}", nome=nome, grupo=composicao.SEM_AMOSTRA,
            peso=1.0, alvo="", complementar=None, estoque=composicao.SEM_LIMITE,
            pedidas=pedidas, estudado_em=SEGUNDA, nos=list(nos)))
    return (parte, composicao.Composicao(
        materias=[composicao.MateriaNaComposicao(materia=m, total=sum(a.pedidas for a in a_),
                                                 alvo="", assuntos=a_)
                  for m, a_ in materias.items()],
        total=sum(t[2] for t in temas), peso_do_complementar=0.25))


def _escolher(partes, reserva=None, feitas_reais=(), feitas_outras=(), semente="s"):
    estoque = composicao.estoque_real()
    nos = sorted({n for _p, c in partes for m in c.materias for a in m.assuntos for n in a.nos})
    return simulado_da_semana.escolher(
        partes, reserva or composicao.Reserva(), estoque, outras_bancas.estoque(nos),
        set(feitas_reais), set(feitas_outras), semente)


# --- nunca mede ------------------------------------------------------------------

def test_a_faixa_de_treino_nao_mede_nem_no_radar():
    assert simulado_da_semana.aceita(_faixa())
    assert not composicao.mede(_faixa())
    # Sem `treino`, a mesma faixa no radar mediria: e a guarda que segura.
    assert composicao.mede(_faixa(treino=False, anteriores=None))
    assert not simulado_da_semana.aceita(_faixa(treino=False))


def test_o_sabado_leve_tem_plano_b_e_nada_que_meca(plano):
    dia = cronograma.montar_dia(plano, SABADO)
    assert diario.faixas_que_medem(dia) == []
    assert [f.titulo for f in dia.manha] == [
        "R+7: probabilidade", "Revisão rápida", "Pausa", "Simulado da semana",
        "Correção do simulado"]
    assert dia.noite == []
    # Umas 2 horas, num bloco so.
    assert sum(f.duracao for f in dia.manha) == 135


def test_treino_so_em_simulado_e_anteriores_so_com_treino(tmp_path):
    texto = (CONFIG / "cronograma.yml").read_text(encoding="utf-8")
    casos = [
        (texto.replace("    anteriores: 5\n", "    anteriores: 25\n", 1), "anteriores"),
        (texto.replace("    treino: true\n", "", 1), "anteriores"),
        (texto.replace("  - tipo: correcao\n    duracao: 20\n",
                       "  - tipo: correcao\n    treino: true\n    duracao: 20\n", 1), "treino"),
    ]
    for errado, chave in casos:
        arquivo = tmp_path / "cronograma.yml"
        arquivo.write_text(errado, encoding="utf-8")
        with pytest.raises(cronograma.ErroNoCronograma, match=chave):
            cronograma.carregar(arquivo)


# --- a composicao em duas partes ---------------------------------------------------

def test_a_semana_e_as_anteriores_pela_regra_da_69(acervo, plano, monkeypatch):
    monkeypatch.setattr(composicao, "_pesos_do_edital",
                        lambda materias: {m: PESOS[m] for m in materias})
    faixa = next(f for f in plano.dia(SABADO).manha if f.treino)
    inicio, partes = simulado_da_semana._partes(
        SABADO, faixa, plano, composicao.Contexto.ler(com_estoque=False))
    assert inicio == SEGUNDA
    (_, semana), (_, antes) = partes
    assert (semana.pedidas, antes.pedidas) == (20, 5)
    da_semana = [a for m in semana.materias for a in m.assuntos]
    assert all(SEGUNDA <= a.estudado_em < SABADO for a in da_semana)
    assert all(a.estudado_em < SEGUNDA for m in antes.materias for a in m.assuntos)
    # A aula de Raciocinio de sexta e tema da semana.
    assert ("Conjuntos e diagramas lógicos", date(2026, 10, 23)) in [
        (a.nome, a.estudado_em) for a in da_semana]


# --- o radar primeiro ----------------------------------------------------------------

def test_a_fepese_livre_primeiro_depois_outras_bancas_e_o_resto_no_qconcursos(acervo):
    """Interpretacao: 1, 2, 3 do alvo e 8 do complementar aceito. Com a 1
    reservada para o fechamento e 6 pedidas: 3 da FEPESE, 2 de outra banca e
    1 no Qconcursos. O tema sem no fica todo no Qconcursos."""
    _de_outra(41, INTERPRETACAO)
    _de_outra(42, INTERPRETACAO)
    fepese = [c for lista in composicao.estoque_real().values() for c in lista
              if c.conteudo == INTERPRETACAO]
    reservada = min(fepese, key=lambda c: c.id)
    partes = [_parte(simulado_da_semana.SEMANA, [
        (PORTUGUES, "Interpretação 1: o método", 6, [INTERPRETACAO]),
        (PORTUGUES, "Sem nó", 2, [])])]
    temas, escolhidas = _escolher(partes, composicao.Reserva({reservada.chave}))
    interpretacao, sem_no = temas
    assert (interpretacao.fepese, interpretacao.outras, interpretacao.no_qconcursos) == (3, 2, 1)
    assert reservada.id not in {e.questao_id for e in escolhidas}
    assert [e.origem for e in escolhidas] == ["fepese"] * 3 + ["outra_banca"] * 2
    assert sem_no.sem_no and (sem_no.do_radar, sem_no.no_qconcursos) == (0, 2)


def test_a_nunca_feita_de_outra_banca_vem_antes_da_fepese_ja_feita(acervo):
    _de_outra(41, INTERPRETACAO)
    fepese = [c for lista in composicao.estoque_real().values() for c in lista
              if c.conteudo == INTERPRETACAO]
    partes = [_parte(simulado_da_semana.SEMANA, [
        (PORTUGUES, "Interpretação 1: o método", len(fepese), [INTERPRETACAO])])]
    temas, escolhidas = _escolher(partes, feitas_reais={c.impressao for c in fepese})
    assert escolhidas[0].origem == "outra_banca"
    assert temas[0].do_radar == len(fepese)


def test_dois_temas_no_mesmo_no_nao_repetem_questao_e_a_escolha_se_repete(acervo):
    partes = [_parte(simulado_da_semana.SEMANA, [
        (PORTUGUES, "Interpretação 1", 3, [INTERPRETACAO]),
        (PORTUGUES, "Interpretação 2", 3, [INTERPRETACAO])])]
    temas, escolhidas = _escolher(partes)
    ids = [e.questao_id for e in escolhidas]
    assert len(ids) == len(set(ids)) == 4                 # so ha 4 da FEPESE no no
    assert [t.no_qconcursos for t in temas] == [0, 2]
    assert ids == [e.questao_id for e in _escolher(partes)[1]]


# --- a rodada --------------------------------------------------------------------

@pytest.fixture
def com_partes(acervo, monkeypatch):
    """O 24/10 com uma composicao fixa: 4 de Interpretacao e 2 de Conjuntos.
    Sem o quadro do edital no banco de teste, o fechamento nao reserva nada."""
    partes = [_parte(simulado_da_semana.SEMANA, [
        (PORTUGUES, "Interpretação 1: o método", 4, [INTERPRETACAO])]),
        _parte(simulado_da_semana.ANTERIORES, [
            (RACIOCINIO, "Conjuntos e diagramas lógicos", 2, [CONJUNTOS])])]
    monkeypatch.setattr(simulado_da_semana, "_partes",
                        lambda data, faixa, plano, contexto: (SEGUNDA, partes))


def test_a_rodada_treina_corrige_no_fim_e_nao_e_recriada(com_partes, plano):
    faixa = _faixa()
    rodada = simulado_da_semana.criar_rodada(SABADO, "manha", 3, faixa, plano)
    assert rodada.filtros["rodada"] == simulado_da_semana.RODADA
    assert rodada.filtros["rodada"] not in servico_simulado.RODADAS_QUE_MEDEM
    assert rodada.filtros["faixa"] == composicao.identidade_da_faixa(SABADO, "manha", 3, faixa)
    assert rodada.filtros["quantidade"] == 6
    assert not servico_simulado.corrige_na_hora(rodada)
    assert simulado_da_semana.criar_rodada(SABADO, "manha", 3, faixa, plano).id == rodada.id
    # Criada, a faixa mostra o que foi gravado.
    gravado = simulado_da_semana.planejar(SABADO, "manha", 3, faixa, plano)
    assert gravado.rodada_id == rodada.id
    assert [(t.tema, t.do_radar) for t in gravado.temas] == [
        ("Interpretação 1: o método", 4), ("Conjuntos e diagramas lógicos", 2)]


def test_a_rodada_nao_conta_como_das_que_medem(com_partes, plano):
    """Criada e nao respondida, ela nao reserva nada; respondida, nao e
    estoque usado por rodada que mede (decisao 145)."""
    rodada = simulado_da_semana.criar_rodada(SABADO, "manha", 3, _faixa(), plano)
    assert composicao.reserva_das_que_medem(date(2026, 11, 8), plano).chaves == set()
    gravado = simulado_da_semana.planejar(SABADO, "manha", 3, _faixa(), plano)
    assert gravado.rodada_id == rodada.id
    with sessao() as s:
        primeira = s.scalar(select(RespostaDeSimulado).where(
            RespostaDeSimulado.simulado_id == rodada.id).order_by(RespostaDeSimulado.ordem))
        questao = s.get(QuestaoDeProva, primeira.questao_id)
    servico_simulado.responder(rodada.id, questao.id, questao.resposta)
    assert composicao.usadas_pelas_que_medem(plano) == set()


# --- a revisao rapida ---------------------------------------------------------------

def test_a_revisao_rapida_e_so_a_dos_sabados_leves(banco_temporario, plano):
    tela = diario.tela_do_dia(SABADO)
    (rapida,) = [r for r in sabado.das_faixas(tela.blocos, SABADO, plano).values()
                 if r.tipo == "revisao_semanal"]
    assert rapida.rapida
    tela = diario.tela_do_dia(date(2026, 10, 17))
    (semanal,) = [r for r in sabado.das_faixas(tela.blocos, date(2026, 10, 17), plano).values()
                  if r.tipo == "revisao_semanal"]
    assert not semanal.rapida


# --- a tela e o terminal ------------------------------------------------------------

@pytest.fixture
def no_dia(acervo, monkeypatch):
    """24/10 e hoje; a ficha de Conjuntos aponta para o no das 2 questoes do
    alvo de Raciocinio Logico, e nada esta reservado."""
    monkeypatch.setattr(diario, "agora_local", lambda: datetime(2026, 10, 24, 10, 0))
    monkeypatch.setattr(composicao, "_pesos_do_edital",
                        lambda materias: {m: PESOS[m] for m in materias})
    monkeypatch.setattr(composicao, "reserva_das_que_medem",
                        lambda data, plano=None: composicao.Reserva())
    servico_fichas.caminho_do_arquivo().write_text(json.dumps([{
        "tema": "Conjuntos e diagramas lógicos", "materia": RACIOCINIO,
        "nos": [CONJUNTOS], "modelo": "teste", "criado_em": "2026-10-01"}]),
        encoding="utf-8")


def test_a_tela_mostra_a_composicao_e_o_botao_cria_a_rodada(no_dia):
    cliente = TestClient(app)
    html = cliente.get("/hoje?data=2026-10-24").text
    inicio = html.index('class="composicao simulado-da-semana"')
    bloco = html[inicio:html.index("</div>", inicio)]
    assert "20 dos temas da semana (19/10 a 23/10) e 5 dos temas de semanas anteriores" in bloco
    assert "Conjuntos e diagramas lógicos" in bloco and "radar 2" in bloco
    assert "Treina, não mede" in bloco
    assert "Criar a rodada com as 2 do radar" in bloco
    # A Revisao rapida sem as regras nem os artigos-chave, e o sabado com Plano B.
    assert "Os artigos-chave da semana" not in html and "Onde mais errou" not in html
    assert "Hoje mede" not in html

    resposta = cliente.post("/hoje/rodada", data={"data": "2026-10-24", "bloco": "manha",
                                                  "indice": "3"}, follow_redirects=False)
    assert resposta.status_code == 303 and resposta.headers["location"].startswith("/simulado/")
    questao = cliente.get(resposta.headers["location"], follow_redirects=True).text
    assert "Simulado da semana" in questao and "rodada que mede" not in questao
    assert "Abrir a rodada desta faixa" in cliente.get("/hoje?data=2026-10-24").text


def test_o_radar_hoje_mostra_a_composicao(no_dia):
    saida = CliRunner().invoke(cli, ["hoje", "--data", "2026-10-24"],
                               env={"COLUMNS": "400"}).output
    assert "20 dos temas de 19/10 a 23/10 e 5 de semanas anteriores" in saida
    assert "Treina, não mede" in saida and "Da semana:" in saida
    assert "Conjuntos e diagramas lógicos" in saida
