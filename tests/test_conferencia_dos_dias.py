"""A conferencia dos dias gravados (Etapa 1D): o banco contra a regra.

Os dados entram direto no banco, e nao pela tela, de proposito: a conferencia
existe para achar o que foi gravado ANTES da regra de hoje - o Bonus marcado
com 0 questoes, que a tela agora recusa, so existe assim.

O cronograma e o mini (tests/fixtures) e as datas sao fixas: nada aqui depende
do dia em que o teste roda.
"""
import json
import sqlite3
from contextlib import closing
from datetime import date, datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

from radar import acervo, cronograma
from radar.cli import app
from radar.db import sessao
from radar.models import (
    EstadoDoDia,
    EstudoExtra,
    QuestaoDeProva,
    RegistroDoDia,
    RespostaDeSimulado,
    Simulado,
)
from radar.servico import conferencia
from radar.servico import cronograma as diario
from radar.servico import metricas
from radar.util import fuso_local

MINI = Path(__file__).parent / "fixtures" / "cronograma_mini.yml"
SEG = date(2026, 9, 28)
TER = date(2026, 9, 29)
HOJE = date(2026, 10, 3)


@pytest.fixture
def plano():
    return cronograma.carregar(MINI)


def _as_21h(minuto=0, data=SEG):
    return datetime(data.year, data.month, data.day, 21, minuto, tzinfo=fuso_local())


def _check(plano, bloco, indice, questoes, acertos, titulo=None):
    """Um check como a tela gravava: com os numeros e o titulo da faixa."""
    faixa = getattr(cronograma.montar_dia(plano, SEG, 1), bloco)[indice]
    return {"bloco": bloco, "indice": indice, "titulo": titulo or faixa.titulo,
            "minutos": faixa.duracao or 0, "questoes": questoes,
            "acertos": acertos, "consulta": False, "materia": faixa.materia,
            "assunto": faixa.titulo}


def _gravar_checks(*checks, data=SEG):
    with sessao() as s:
        s.add(EstadoDoDia(data=data, faixas_feitas=list(checks),
                          atualizado_em=_as_21h(data=data)))


def _responder(acertou, quando, gerada=False, questao_id=1):
    with sessao() as s:
        simulado = Simulado(filtros={})
        s.add(simulado)
        s.flush()
        s.add(RespostaDeSimulado(
            simulado_id=simulado.id, questao_id=questao_id, gerada=gerada,
            ordem=1, escolhida="a", acertou=acertou, respondida_em=quando))


def _o_dia_28(plano):
    """O 28/09 como esta no banco real: Penal 11/6, Portugues 10/7, o Bonus
    marcado com 0 questoes, 10 de IA (7 certas) e a copia 31/13 no registro."""
    _gravar_checks(_check(plano, "noite", 0, 11, 6),
                   _check(plano, "noite", 2, 10, 7),
                   _check(plano, "pos22", 1, 0, None))
    for n in range(10):
        _responder(n < 7, _as_21h(n), gerada=True, questao_id=n + 1)
    with sessao() as s:
        s.add(RegistroDoDia(data=SEG, meta="reduzida", questoes_feitas=31,
                            acertos=13, anotado_em=_as_21h(30)))


def _dia(dias, data=SEG):
    (dia,) = [d for d in dias if d.data == data]
    return dia


def _tipos(dia):
    return [a.tipo for a in dia.achados]


def _conferir(plano):
    return conferencia.conferir(SEG, TER, plano=plano, hoje=HOJE)


# --- a conferencia acha cada anomalia ------------------------------------------

def test_dia_sem_nada_gravado(banco_temporario, plano):
    dias = _conferir(plano)

    assert [d.data for d in dias] == [SEG, TER]
    assert all(not d.gravado and not d.achados for d in dias)


def test_o_28_09_bonus_com_zero_questoes_e_a_unica_correcao(banco_temporario, plano):
    _o_dia_28(plano)

    dia = _dia(_conferir(plano))

    (zero,) = [a for a in dia.achados if a.tipo == conferencia.ZERO]
    assert zero.corrige
    assert zero.check["titulo"] == "Bônus: lógica"
    assert "saem 25 min" in zero.proposta
    assert dia.conta == "31 questões = 13 acertos + 8 erros + 10 de treino de IA"
    # Nao ha erro em dado nenhum alem dele (e do JSON, que ainda nao existe).
    assert {a.tipo for a in dia.a_corrigir} == {conferencia.ZERO, conferencia.JSON}


def test_a_copia_do_registro_que_bate_nao_pede_nada(banco_temporario, plano):
    _o_dia_28(plano)

    (registro,) = [a for a in _dia(_conferir(plano)).achados
                   if a.tipo == conferencia.REGISTRO]
    assert registro.gravado == "meta reduzida, 31 questões, 13 acertos"
    assert registro.proposta == "nada: a cópia bate com a regra"
    assert not registro.corrige


def test_a_copia_do_registro_que_nao_bate_e_mostrada(banco_temporario, plano):
    _gravar_checks(_check(plano, "noite", 0, 11, 6))
    with sessao() as s:
        s.add(RegistroDoDia(data=SEG, meta="ideal", questoes_feitas=20,
                            acertos=6, anotado_em=_as_21h()))

    (registro,) = [a for a in _dia(_conferir(plano)).achados
                   if a.tipo == conferencia.REGISTRO]
    assert registro.regra == "11 questões = 6 acertos + 5 erros"
    assert "não aparece; vale a regra" in registro.proposta
    assert not registro.corrige


def test_o_treino_de_ia_aparece_como_volume(banco_temporario, plano):
    _o_dia_28(plano)

    (ia,) = [a for a in _dia(_conferir(plano)).achados
             if a.tipo == conferencia.TREINO_IA]
    assert ia.gravado == "10 respostas a questão de IA (7 certas)"
    assert not ia.corrige


def test_acertos_maiores_que_as_questoes_na_faixa_e_no_extra(banco_temporario, plano):
    _gravar_checks(_check(plano, "noite", 0, 5, 8))
    with sessao() as s:
        s.add(EstudoExtra(data=SEG, o_que="questoes", minutos=30, questoes=4,
                          acertos=6, onde="qconcursos"))

    dia = _dia(_conferir(plano))

    maiores = [a for a in dia.achados if a.tipo == conferencia.ACERTO_MAIOR]
    assert len(maiores) == 2
    assert not any(a.corrige for a in maiores)
    # A conta do dia nao fecha, e a conferencia diz isso em vez de parar.
    assert dia.conta.startswith("a conta não fecha")


def test_resposta_a_questao_anulada(banco_temporario, plano):
    with sessao() as s:
        s.add(QuestaoDeProva(id=7, prova_url="p.pdf", numero=11, ano=2019,
                             enunciado="?", impressao="x", anulada=True))
    _responder(True, _as_21h(), questao_id=7)

    (anulada,) = [a for a in _dia(_conferir(plano)).achados
                  if a.tipo == conferencia.ANULADA]
    assert "questão 11 de 2019, certa" in anulada.gravado
    assert not anulada.corrige


def test_check_orfao(banco_temporario, plano):
    _gravar_checks(_check(plano, "noite", 0, 10, 5, titulo="Outra faixa"))

    dia = _dia(_conferir(plano))

    (orfao,) = [a for a in dia.achados if a.tipo == conferencia.ORFAO]
    assert "'Outra faixa'" in orfao.gravado
    assert not orfao.corrige
    assert dia.conta == "0 questões = 0 acertos + 0 erros"


def test_dia_fora_do_json_e_proposto_para_exportar(banco_temporario, plano):
    _o_dia_28(plano)

    (json,) = [a for a in _dia(_conferir(plano)).achados
               if a.tipo == conferencia.JSON]
    assert json.corrige
    assert "o registro não está no JSON" in json.gravado
    assert "os checks não estão no JSON" in json.gravado

    acervo.exportar_registros()
    acervo.exportar_estados()
    assert conferencia.JSON not in _tipos(_dia(_conferir(plano)))


def test_a_faixa_com_zero_da_tela_e_recusada(banco_temporario, plano):
    """A regra decidida na 1D: faixa de questoes sem questao nao e feita."""
    bonus = getattr(cronograma.montar_dia(plano, SEG, 1), "pos22")[1]
    for questoes in (0, "0", ""):
        with pytest.raises(diario.RegistroInvalido, match="desmarque a faixa"):
            diario.anotar_faixa(SEG, "pos22", 1, bonus.titulo, questoes=questoes,
                                acertos="", plano=plano, hoje=HOJE)
    assert diario.estado_do_dia(SEG) is None


# --- nada muda sem --aplicar ---------------------------------------------------

def _foto_do_banco():
    with sessao() as s:
        estados = [(e.data, e.faixas_feitas, e.plano_b) for e in s.query(EstadoDoDia)]
        registros = [(r.data, r.meta, r.questoes_feitas, r.acertos)
                     for r in s.query(RegistroDoDia)]
    return estados, registros


def test_conferir_nao_muda_nada(banco_temporario, plano, tmp_path):
    _o_dia_28(plano)
    antes = _foto_do_banco()

    _conferir(plano)

    assert _foto_do_banco() == antes
    assert not acervo.caminho_dos_registros().exists()
    assert not acervo.caminho_dos_estados().exists()
    assert not conferencia.caminho_das_copias().exists()


# --- com --aplicar ---------------------------------------------------------------

def test_aplicar_copia_antes_e_so_tira_o_bonus(banco_temporario, plano):
    _o_dia_28(plano)
    # O que nao e correcao automatica tem que sobreviver ao aplicar.
    orfao = _check(plano, "noite", 0, 10, 5, titulo="Outra faixa")
    with sessao() as s:
        estado = s.query(EstadoDoDia).one()
        estado.faixas_feitas = list(estado.faixas_feitas) + [orfao]
    antes = _conferir(plano)
    checks_antes = diario.estado_do_dia(SEG).faixas_feitas

    pasta = conferencia.aplicar(antes)

    # A copia tem o banco como estava, com o Bonus ainda la.
    copia = pasta / "teste.db"
    assert copia.exists()
    with closing(sqlite3.connect(copia)) as banco:
        (faixas,) = banco.execute("select faixas_feitas from estados_do_dia").fetchone()
    assert "Bônus: lógica" in [c["titulo"] for c in json.loads(faixas)]

    # So o Bonus saiu; o resto, orfao inclusive, ficou.
    checks_depois = diario.estado_do_dia(SEG).faixas_feitas
    assert [c for c in checks_antes if c not in checks_depois] == [
        _check(plano, "pos22", 1, 0, None)]
    assert len(checks_depois) == len(checks_antes) - 1
    (registro,) = diario.registros(SEG, SEG).values()
    assert (registro.questoes_feitas, registro.acertos) == (31, 13)

    # E a conferencia de novo bate: o numero de questoes nao muda, os
    # minutos perdem os 25 do Bonus, e o JSON esta igual ao banco.
    depois = _conferir(plano)
    assert not any(d.a_corrigir for d in depois)
    assert _dia(depois).conta == _dia(antes).conta
    assert _dia(antes).minutos - _dia(depois).minutos == 25
    assert acervo.estados_no_arquivo()["2026-09-28"]["faixas_feitas"] == checks_depois


def test_aplicar_sem_nada_a_corrigir_nao_grava_nada(banco_temporario, plano):
    _gravar_checks(_check(plano, "noite", 0, 11, 6))
    acervo.exportar_estados()

    assert conferencia.aplicar(_conferir(plano)) is None
    assert not conferencia.caminho_das_copias().exists()


# --- o comando ---------------------------------------------------------------------

@pytest.fixture
def com_o_mini(banco_temporario, tmp_path, monkeypatch):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "cronograma.yml").write_text(MINI.read_text(encoding="utf-8"),
                                               encoding="utf-8")
    monkeypatch.setenv("RADAR_CONFIG_DIR", str(config_dir))
    monkeypatch.setattr(diario, "hoje_local", lambda: TER)


def test_o_comando_so_le_e_com_aplicar_corrige(com_o_mini, plano):
    _o_dia_28(plano)
    antes = _foto_do_banco()
    runner = CliRunner()

    saida = runner.invoke(app, ["conferir-dias"], env={"COLUMNS": "250"})
    assert saida.exit_code == 0, saida.output
    assert "faixa feita com 0 questões" in saida.output
    assert "Nada mudou" in saida.output
    assert _foto_do_banco() == antes

    saida = runner.invoke(app, ["conferir-dias", "--aplicar"], env={"COLUMNS": "250"})
    assert saida.exit_code == 0, saida.output
    assert "Cópia de segurança em" in saida.output
    assert "Totais antes x depois" in saida.output
    # A linha do 28/09 nos totais: os mesmos minutos do metricas, menos 25.
    minutos = metricas.do_dia(SEG, plano).minutos
    assert cronograma.duracao_legivel(minutos + 25) in saida.output
    assert cronograma.duracao_legivel(minutos) in saida.output
    assert _foto_do_banco() != antes

    saida = runner.invoke(app, ["conferir-dias"], env={"COLUMNS": "250"})
    assert "Nada a corrigir" in saida.output


def test_a_conta_do_dia_e_a_mesma_do_metricas(banco_temporario, plano):
    """A conferencia nao tem conta propria: le a do `servico.metricas`."""
    _o_dia_28(plano)
    dia = _dia(_conferir(plano))
    conta = metricas.do_dia(SEG, plano)
    assert dia.conta == metricas.frase_da_conta(conta.total)
    assert dia.minutos == conta.minutos
