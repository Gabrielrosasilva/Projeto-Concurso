"""A rotina nova do Ciclo 1 e o Anki desativado (Etapa 6A).

Duas partes. A chave `anki` e a `consulta` por faixa sao testadas no
cronograma mini (tests/fixtures), com a chave escrita numa copia dele. A
rotina nova e testada no config/cronograma.yml de verdade: e ele que foi
reescrito, e o que se confere e que os dias antes de 02/10 nao mudaram e que
os de depois tem questoes de manha, sem o dia crescer.
"""
import hashlib
import json
from datetime import date, datetime
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from radar import config, cronograma, servico
from radar.cli import app as cli
from radar.servico import cronograma as diario
from radar.util import fuso_local
from radar.web.app import app

MINI = Path(__file__).parent / "fixtures" / "cronograma_mini.yml"
SEG = date(2026, 9, 28)
HOJE = date(2026, 10, 3)
APLICACAO = date(2026, 10, 2)

# A impressao dos dias ANTES da aplicacao, tirada do arquivo antes da 6A
# reescreve-lo. Se mudar, um dia que ja passou foi editado - e os checks
# dele (reconhecidos por bloco, posicao e titulo) deixariam de valer.
IMPRESSAO_DOS_DIAS_ANTERIORES = (
    "7baa33540cb42e3d053e2b62c552717d473177d0ef9984aefe01c363e2489447")


def _mini(tmp_path, topo: str = "", troca: tuple[str, str] | None = None) -> Path:
    """Uma copia do mini com `topo` no comeco e, se pedido, um trecho trocado."""
    texto = MINI.read_text(encoding="utf-8")
    if troca:
        assert texto.count(troca[0]) == 1
        texto = texto.replace(*troca)
    caminho = tmp_path / "cronograma.yml"
    caminho.write_text(topo + texto, encoding="utf-8")
    return caminho


@pytest.fixture
def sem_anki(tmp_path):
    return cronograma.carregar(_mini(tmp_path, "anki: desativado\n"))


# --- a chave anki ---------------------------------------------------------------

def test_sem_a_chave_o_anki_continua_ativado():
    plano = cronograma.carregar(MINI)
    assert plano.anki
    dia = cronograma.montar_dia(plano, SEG, 1)
    assert not any(f.desligada for f in dia.pos22)
    assert dia.manha[0].baralho == "[1] Direito Penal"


def test_desativado_a_faixa_fica_no_lugar_sem_tempo_e_sem_baralho(sem_anki):
    dia = cronograma.montar_dia(sem_anki, SEG, 1)

    anki, bonus = dia.pos22
    assert anki.tipo == "anki" and anki.desligada
    assert anki.duracao == 0
    # O Bonus continua na posicao 1 e comeca as 22h, sem esperar o Anki.
    assert bonus.tipo == "bonus" and f"{bonus.inicio:%H:%M}" == "22:00"
    assert anki not in dia.faixas()
    assert all(f.baralho is None for f in dia.manha)


def test_desativado_o_total_nao_muda_e_a_sugestao_ignora_o_anki(sem_anki):
    plano_com = cronograma.carregar(MINI)
    com = cronograma.montar_dia(plano_com, SEG, 1)
    sem = cronograma.montar_dia(sem_anki, SEG, 1)
    assert sem.total_questoes == com.total_questoes

    # Tudo o que conta feito, menos o Anki: com ele desligado, e Ideal.
    def todas_menos_o_anki(dia):
        return {(b, i) for b in cronograma.BLOCOS
                for i, f in enumerate(getattr(dia, b))
                if f.tipo not in ("pausa", "anki") and not f.opcional}
    assert diario.sugerir_meta(sem, todas_menos_o_anki(sem)).meta == "ideal"
    assert diario.sugerir_meta(com, todas_menos_o_anki(com)).meta != "ideal"


def test_desativado_o_anki_nao_se_marca(banco_temporario, sem_anki):
    with pytest.raises(diario.RegistroInvalido, match="temporariamente desativado"):
        diario.marcar_faixa(SEG, "pos22", 0, "Anki", plano=sem_anki, hoje=HOJE)


def test_religar_volta_igual_a_antes(tmp_path):
    sem_chave = cronograma.carregar(MINI)
    religado = cronograma.carregar(_mini(tmp_path, "anki: ativado\n"))
    assert religado.anki
    assert (cronograma.montar_dia(religado, SEG, 1)
            == cronograma.montar_dia(sem_chave, SEG, 1))


def test_valor_desconhecido_na_chave_e_erro(tmp_path):
    with pytest.raises(cronograma.ErroNoCronograma, match="`anki`"):
        cronograma.carregar(_mini(tmp_path, "anki: talvez\n"))


# --- a chave consulta -------------------------------------------------------------

def test_a_chave_consulta_manda_na_caixa(tmp_path):
    plano = cronograma.carregar(_mini(tmp_path, troca=(
        "    titulo: Substantivo\n  noite:",
        "    titulo: Substantivo\n    consulta: true\n  noite:")))
    dia = cronograma.montar_dia(plano, SEG, 1)
    portugues_da_manha = dia.manha[2]
    assert cronograma.consulta_por_padrao(portugues_da_manha)
    # Sem a chave, a regra de sempre: so a rampa de Direito vem marcada.
    assert cronograma.consulta_por_padrao(dia.noite[0])
    assert not cronograma.consulta_por_padrao(dia.noite[2])


def test_consulta_false_desmarca_ate_a_rampa_de_direito(tmp_path):
    plano = cronograma.carregar(_mini(tmp_path, troca=(
        "    rampa: direito\n", "    rampa: direito\n    consulta: false\n")))
    assert not cronograma.consulta_por_padrao(cronograma.montar_dia(plano, SEG, 1).noite[0])


# --- a tela e o terminal ------------------------------------------------------------

def test_a_tela_mostra_a_linha_minimizada(banco_temporario, monkeypatch):
    momento = datetime(2026, 10, 2, 9, 0, tzinfo=fuso_local())
    monkeypatch.setattr(servico.cronograma, "agora_local", lambda: momento)

    texto = TestClient(app).get("/hoje?data=2026-10-02").text

    assert "ANKI temporariamente desativado" in texto
    assert 'class="faixa-desligada"' in texto
    assert "🃏 [" not in texto                     # o chip do baralho
    assert "Depois das 22h — Anki" not in texto
    assert "Fixação:" in texto                    # as questoes da manha


def test_o_radar_hoje_mostra_a_linha_minimizada():
    saida = CliRunner().invoke(cli, ["hoje", "--data", "2026-10-02"],
                               env={"COLUMNS": "200"})
    assert saida.exit_code == 0, saida.output
    assert "ANKI temporariamente desativado" in saida.output
    assert "Fixação:" in saida.output


# --- o config/cronograma.yml reescrito ------------------------------------------------

@pytest.fixture(scope="module")
def real():
    return cronograma.carregar()


def _uteis_depois(plano):
    return [d.data for d in plano.dias
            if d.data >= APLICACAO and d.data.weekday() < cronograma.SABADO]


def test_o_arquivo_real_esta_com_o_anki_desativado(real):
    assert not real.anki
    texto = (config.diretorio_config() / "cronograma.yml").read_text(encoding="utf-8")
    assert "\nanki: desativado\n" in texto
    # Nada do Anki foi apagado: as faixas e os baralhos continuam la.
    assert texto.count("- tipo: anki") == 36
    assert texto.count("baralho:") == 30
    assert "baralho: '[3] LEP'" in texto


def test_nenhum_dia_antes_da_aplicacao_mudou():
    dados = yaml.safe_load(
        (config.diretorio_config() / "cronograma.yml").read_text(encoding="utf-8"))
    antes = [d for d in dados["dias"] if str(d["data"]) < APLICACAO.isoformat()]
    impressao = hashlib.sha256(json.dumps(
        antes, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()
    assert impressao == IMPRESSAO_DOS_DIAS_ANTERIORES


def test_toda_manha_de_dia_util_tem_questoes(real):
    uteis = _uteis_depois(real)
    assert len(uteis) == 26
    for data in uteis:
        manha = cronograma.montar_dia(real, data, 1).manha
        assert sum(f.questoes or 0 for f in manha) == 14, data
        fixacao, portugues = [f for f in manha if f.tipo == "questoes"]
        assert fixacao.questoes == 8 and cronograma.consulta_por_padrao(fixacao), data
        assert portugues.questoes == 6 and not cronograma.consulta_por_padrao(portugues), data


def test_o_dia_util_nao_cresceu(real):
    """Manha de 2h15 (era 2h20) e o Anki fora: 20 min a menos que antes."""
    for data in _uteis_depois(real):
        dia = cronograma.montar_dia(real, data, 1)
        assert sum(f.duracao for f in dia.manha) == 135, data
        assert sum(f.duracao for f in dia.pos22 if not f.opcional) == 0, data
        lei = next(f for f in dia.manha if f.tipo == "lei_seca")
        assert lei.duracao == 20
        assert all(a.artigos in lei.titulo for a in dia.essencial.chave), data


def test_o_anki_saiu_dos_textos_dos_dias_novos(real):
    for dia in real.dias:
        if dia.data < APLICACAO:
            continue
        for faixa in dia.faixas():
            assert "Anki" not in (faixa.detalhe or "") + faixa.titulo, (dia.data, faixa.titulo)


def test_o_plano_b_continua_montando(real):
    for data in _uteis_depois(real):
        for minutos in (30, 60):
            dia = cronograma.montar_plano_b(real, data, minutos, 1)
            (essencial, direito, *_) = dia.plano_b
            assert essencial.tipo == "essencial"
            # As questoes do Plano B sao as da noite, e nao a fixacao da manha.
            assert not direito.titulo.startswith("Fixação"), data
