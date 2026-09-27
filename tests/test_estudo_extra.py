"""O estudo extra: o que eu estudei fora das faixas do plano (etapa E2).

Duas regras que sao do assunto, e nao da tela:

  * `onde = radar` nao guarda questao nem acerto - o radar ja contou cada uma
    delas, uma por uma, e somar aqui contaria o mesmo acerto duas vezes;
  * o extra NAO muda a meta do dia nem a sugestao dela: fazer mais do que o
    plano pedia nao transforma um dia reduzido em ideal.
"""
import json
from datetime import date, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from radar import acervo, cronograma, servico
from radar.db import sessao
from radar.models import EstudoExtra
from radar.servico import cronograma as diario
from radar.util import fuso_local
from radar.web.app import app

MINI = Path(__file__).parent / "fixtures" / "cronograma_mini.yml"
SEG = date(2026, 9, 28)
HOJE = date(2026, 10, 3)


@pytest.fixture
def plano():
    return cronograma.carregar(MINI)


@pytest.fixture
def cliente(banco_temporario, monkeypatch):
    """A tela, no cronograma de verdade, com o relogio parado em 30/09."""
    monkeypatch.setattr(
        diario, "agora_local",
        lambda: datetime(2026, 9, 30, 12, 0, tzinfo=fuso_local()),
    )
    return TestClient(app)


def _anotar(plano, **mudancas):
    dados = {
        "data": SEG, "o_que": "questoes", "materia": "Direito Penal",
        "assunto": "Aplicação da lei penal", "minutos": 30, "questoes": 20,
        "acertos": 16, "onde": "qconcursos", "plano": plano, "hoje": HOJE,
    }
    dados.update(mudancas)
    return servico.extra.anotar(**dados)


# --- anotar -------------------------------------------------------------------

def test_anotar_guarda_tudo(banco_temporario, plano):
    extra = _anotar(plano)

    assert extra.id is not None
    assert (extra.data, extra.o_que, extra.materia) == (SEG, "questoes", "Direito Penal")
    assert (extra.minutos, extra.questoes, extra.acertos) == (30, 20, 16)
    assert extra.consulta is False
    assert extra.onde == "qconcursos"


def test_varios_no_mesmo_dia(banco_temporario, plano):
    _anotar(plano, minutos=30)
    _anotar(plano, minutos=45, o_que="teoria", questoes=None, acertos=None)
    assert len(servico.extra.do_dia(SEG)) == 2


def test_o_extra_do_radar_nao_guarda_questao_nem_acerto(banco_temporario, plano):
    """O radar ja contou cada questao: do extra dele vale o TEMPO."""
    extra = _anotar(plano, onde="radar", questoes=20, acertos=16, consulta=True)

    assert (extra.questoes, extra.acertos) == (None, None)
    assert extra.consulta is False
    assert extra.minutos == 30


def test_sem_minutos_e_recusado(banco_temporario, plano):
    with pytest.raises(diario.RegistroInvalido, match="quantos minutos"):
        _anotar(plano, minutos="")
    with pytest.raises(diario.RegistroInvalido, match="quantos minutos"):
        _anotar(plano, minutos=0)


def test_tempo_absurdo_e_recusado(banco_temporario, plano):
    """720 em vez de 72: erro de digitacao que viraria uma semana falsa."""
    with pytest.raises(diario.RegistroInvalido, match="horas num dia"):
        _anotar(plano, minutos=720)


def test_acertos_maior_que_questoes_e_recusado(banco_temporario, plano):
    with pytest.raises(diario.RegistroInvalido, match="maior que as questões"):
        _anotar(plano, questoes=10, acertos=12)


def test_acertos_sem_questoes_e_recusado(banco_temporario, plano):
    with pytest.raises(diario.RegistroInvalido, match="diga quantas"):
        _anotar(plano, questoes=None, acertos=5)


def test_dia_futuro_e_recusado(banco_temporario, plano):
    with pytest.raises(diario.RegistroInvalido, match="ainda não chegou"):
        _anotar(plano, data=date(2026, 10, 3), hoje=SEG)


def test_dia_fora_do_plano_e_recusado(banco_temporario, plano):
    with pytest.raises(diario.RegistroInvalido, match="não está no cronograma"):
        _anotar(plano, data=date(2026, 9, 30))


@pytest.mark.parametrize("campo, valor", [
    ("o_que", "assistir"),
    ("onde", "papel"),
])
def test_o_que_e_onde_fora_da_lista_sao_recusados(banco_temporario, plano, campo, valor):
    with pytest.raises(diario.RegistroInvalido):
        _anotar(plano, **{campo: valor})


def test_materia_fora_do_edital_e_recusada(banco_temporario):
    """Aceitar calado faria o extra somar numa materia que nao existe."""
    real = cronograma.carregar()
    with pytest.raises(diario.RegistroInvalido, match="não é uma das matérias"):
        servico.extra.anotar(data=SEG, o_que="teoria", materia="Direito Tributário",
                             minutos=30, plano=real, hoje=HOJE)


def test_extra_sem_materia_pode(banco_temporario, plano):
    """Uma videoaula solta, um resumo geral: nem tudo tem materia."""
    assert _anotar(plano, materia="").materia is None


# --- editar e apagar ----------------------------------------------------------

def test_editar_troca_os_numeros(banco_temporario, plano):
    extra = _anotar(plano)
    mudado = servico.extra.editar(extra.id, minutos=50, questoes=25, acertos=20,
                                  plano=plano, hoje=HOJE)
    assert (mudado.minutos, mudado.questoes, mudado.acertos) == (50, 25, 20)
    assert len(servico.extra.do_dia(SEG)) == 1


def test_editar_para_o_radar_limpa_as_questoes(banco_temporario, plano):
    extra = _anotar(plano)
    mudado = servico.extra.editar(extra.id, onde="radar", plano=plano, hoje=HOJE)
    assert (mudado.questoes, mudado.acertos) == (None, None)


def test_editar_confere_como_o_anotar(banco_temporario, plano):
    extra = _anotar(plano)
    with pytest.raises(diario.RegistroInvalido, match="maior que as questões"):
        servico.extra.editar(extra.id, questoes=5, acertos=9, plano=plano, hoje=HOJE)


def test_editar_o_que_nao_existe_e_recusado(banco_temporario, plano):
    with pytest.raises(diario.RegistroInvalido, match="#404"):
        servico.extra.editar(404, minutos=10, plano=plano, hoje=HOJE)


def test_apagar(banco_temporario, plano):
    extra = _anotar(plano)
    assert servico.extra.apagar(extra.id) is True
    assert servico.extra.do_dia(SEG) == []
    # Apagar duas vezes nao estoura: F5 na pagina nao pode dar 500.
    assert servico.extra.apagar(extra.id) is False


def test_entre_duas_datas(banco_temporario, plano):
    _anotar(plano, data=SEG)
    _anotar(plano, data=date(2026, 9, 29))
    assert len(servico.extra.entre(SEG, date(2026, 9, 29))) == 2
    assert len(servico.extra.entre(SEG, SEG)) == 1


# --- o extra nao muda a meta ---------------------------------------------------

def test_o_extra_nao_muda_a_sugestao_da_meta(banco_temporario, plano):
    dia = cronograma.montar_dia(plano, SEG, 1)
    antes = diario.sugerir_meta(dia, diario.faixas_feitas(dia, diario.estado_do_dia(SEG)))
    _anotar(plano, minutos=120, questoes=100, acertos=90)
    depois = diario.sugerir_meta(dia, diario.faixas_feitas(dia, diario.estado_do_dia(SEG)))
    assert (antes.meta, antes.feitas) == (depois.meta, depois.feitas)


# --- o backup em JSON ---------------------------------------------------------

def test_exportar_e_importar_ida_e_volta(banco_temporario, plano, tmp_path):
    extra = _anotar(plano, consulta=True, anotacao="na fila do banco")
    arquivo = tmp_path / "estudo_extra.json"

    assert acervo.exportar_extras(arquivo) == 1

    with sessao() as s:
        s.delete(s.get(EstudoExtra, extra.id))
    assert acervo.importar_extras(arquivo) == 1

    with sessao() as s:
        voltou = s.scalars(select(EstudoExtra)).one()
    assert (voltou.data, voltou.o_que, voltou.materia) == (SEG, "questoes", "Direito Penal")
    assert (voltou.minutos, voltou.questoes, voltou.acertos) == (30, 20, 16)
    assert voltou.consulta is True
    assert voltou.anotacao == "na fila do banco"
    assert voltou.criado_em == extra.criado_em


def test_importar_duas_vezes_da_no_mesmo(banco_temporario, plano, tmp_path):
    _anotar(plano)
    arquivo = tmp_path / "estudo_extra.json"
    acervo.exportar_extras(arquivo)

    assert acervo.importar_extras(arquivo) == 0
    with sessao() as s:
        assert len(s.scalars(select(EstudoExtra)).all()) == 1


def test_o_arquivo_so_cresce(banco_temporario, plano, tmp_path):
    _anotar(plano)
    arquivo = tmp_path / "estudo_extra.json"
    acervo.exportar_extras(arquivo)
    with sessao() as s:
        s.delete(s.scalars(select(EstudoExtra)).one())
    assert acervo.exportar_extras(arquivo) == 1


def test_sem_arquivo_o_importar_nao_reclama(banco_temporario, tmp_path):
    assert acervo.importar_extras(tmp_path / "nao_existe.json") == 0


def test_o_arquivo_entra_no_sincronizar():
    from radar.cli import ARQUIVOS_DO_RADAR
    assert "data/estudo_extra.json" in ARQUIVOS_DO_RADAR


def test_o_caminho_fica_junto_dos_outros(banco_temporario):
    assert (acervo.caminho_dos_extras().parent
            == acervo.caminho_dos_registros().parent)
    assert acervo.caminho_dos_extras().name == "estudo_extra.json"


# --- a tela -------------------------------------------------------------------

def test_o_formulario_aparece_no_dia(cliente):
    texto = cliente.get("/hoje?data=2026-09-28").text
    assert "➕ Estudo extra" in texto
    assert 'name="minutos"' in texto
    assert "não muda a meta" in texto


def test_anotar_pela_tela_e_voltar_para_a_lista(cliente):
    resposta = cliente.post("/hoje/extra", data={
        "data": "2026-09-28", "o_que": "lei_seca", "materia": "Direito Penal",
        "assunto": "Art. 33", "minutos": "40", "onde": "outro"},
        follow_redirects=False)

    assert resposta.status_code == 303
    assert resposta.headers["location"] == "/hoje?data=2026-09-28#extras"
    texto = cliente.get("/hoje?data=2026-09-28").text
    assert "Lei seca" in texto and "Art. 33" in texto and "40 min" in texto


def test_editar_pela_tela(cliente):
    cliente.post("/hoje/extra", data={
        "data": "2026-09-28", "o_que": "teoria", "minutos": "30", "onde": "outro"})
    (extra,) = servico.extra.do_dia(SEG)

    cliente.post(f"/hoje/extra/{extra.id}", data={
        "data": "2026-09-28", "o_que": "teoria", "minutos": "45", "onde": "outro"})

    (mudado,) = servico.extra.do_dia(SEG)
    assert mudado.minutos == 45


def test_apagar_pela_tela(cliente):
    cliente.post("/hoje/extra", data={
        "data": "2026-09-28", "o_que": "teoria", "minutos": "30", "onde": "outro"})
    (extra,) = servico.extra.do_dia(SEG)

    resposta = cliente.post(f"/hoje/extra/{extra.id}", data={
        "data": "2026-09-28", "apagar": "1"}, follow_redirects=False)

    assert resposta.status_code == 303
    assert servico.extra.do_dia(SEG) == []


def test_a_recusa_do_extra_aparece_na_tela_com_o_que_eu_digitei(cliente):
    resposta = cliente.post("/hoje/extra", data={
        "data": "2026-09-28", "o_que": "questoes", "minutos": "",
        "assunto": "Progressão", "onde": "outro"})

    assert resposta.status_code == 400
    assert "quantos minutos" in resposta.text
    assert 'value="Progressão"' in resposta.text


def test_o_dia_futuro_nao_tem_formulario_de_extra(cliente):
    texto = cliente.get("/hoje?data=2026-10-01").text
    assert 'action="/hoje/extra' not in texto


def test_a_materia_do_formulario_vem_do_edital(cliente):
    texto = cliente.get("/hoje?data=2026-09-28").text
    for materia in ("Lei de Execução Penal", "Sociologia Aplicada"):
        assert f'value="{materia}"' in texto
