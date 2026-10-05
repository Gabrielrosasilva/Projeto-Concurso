"""A redistribuicao do Ciclo 1 pela classe de cada tema (R4, 05/10/2026).

O que estes testes seguram: a chave `teto` e a faixa com `sobra_da_rampa`
dividem a rampa sem mudar o total do dia em nivel nenhum; e, no
config/cronograma.yml real, contra a fotografia de antes da R4
(tests/fixtures/cronograma_antes_da_r4.json): os dias ate 05/10 identicos,
nenhum titulo nem data de tema mudou, o total de minutos de cada dia nao
aumentou, o R+7 e o R+30 apontam o tema certo, e a faixa nova tem o botao
do resumo.
"""
import hashlib
import json
from dataclasses import asdict
from datetime import date
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from radar import cronograma as pl
from radar import fichas

RAIZ = Path(__file__).resolve().parents[1]
ANTES = json.loads((Path(__file__).parent / "fixtures" / "cronograma_antes_da_r4.json")
                   .read_text(encoding="utf-8"))


def _plano_mini(tmp_path, teto=10, sobra=True):
    """Um dia com a aprendizagem de rampa com teto e a Extra com a sobra."""
    noite = [{"tipo": "questoes", "rampa": "direito", "questoes": 20, "teto": teto,
              "materia": "Direito Penal", "titulo": "Aprendizagem: Tema que não caiu"}]
    if sobra:
        noite.append({"tipo": "revisao", "rotulo": "Extra", "sobra_da_rampa": "direito",
                      "materia": "Direito Penal", "titulo": "Extra: Tema que caiu"})
    dados = {
        "inicio": "2026-10-05", "fim": "2026-10-05", "minutos_por_questao": 2.5,
        "blocos": {"manha": {"nome": "Manhã", "inicio": "10:15"},
                   "noite": {"nome": "Noite", "inicio": "18:00"},
                   "pos22": {"nome": "Depois", "inicio": "22:00"}},
        "rampa": {n: {"direito": d} for n, d in ((1, 15), (2, 20), (3, 20), (4, 25),
                                                (5, 25), (6, 25))},
        "gatilho": {"sobe_com_dias_na_ideal": 5, "semana_ruim_com_dias_abaixo": 3,
                    "desce_apos_semanas_ruins": 2},
        "dias": [{"data": "2026-10-05", "semana": 1, "noite": noite}],
    }
    arquivo = tmp_path / "cronograma.yml"
    arquivo.write_text(yaml.safe_dump(dados, allow_unicode=True), encoding="utf-8")
    return pl.carregar(arquivo)


@pytest.mark.parametrize("teto", [10, 14])
def test_o_teto_e_a_sobra_dividem_a_rampa_sem_mudar_o_total(tmp_path, teto):
    plano = _plano_mini(tmp_path, teto)
    for nivel, direito in ((None, 20), (1, 15), (2, 20), (4, 25)):
        dia = pl.montar_dia(plano, date(2026, 10, 5), nivel)
        aprendizagem, extra = dia.noite
        assert aprendizagem.questoes == min(direito, teto)
        assert extra.questoes == max(direito - teto, 0)
        total = aprendizagem.duracao + extra.duracao
        assert total == pl.duracao_de_questoes(direito, 2.5), (nivel, teto)


def test_a_sobra_sem_a_faixa_com_teto_e_recusada(tmp_path):
    plano_ok = _plano_mini(tmp_path, sobra=True)
    assert plano_ok.dia(date(2026, 10, 5)).noite[0].teto == 10
    dados = yaml.safe_load((tmp_path / "cronograma.yml").read_text(encoding="utf-8"))
    del dados["dias"][0]["noite"][0]["teto"]
    (tmp_path / "cronograma.yml").write_text(yaml.safe_dump(dados, allow_unicode=True),
                                             encoding="utf-8")
    with pytest.raises(pl.ErroNoCronograma, match="sobra da rampa"):
        pl.carregar(tmp_path / "cronograma.yml")


def test_o_prefixo_extra_diz_o_tema():
    assert fichas.tema_da_faixa("Extra: Vozes do verbo") == "Vozes do verbo"


# --- o cronograma real, contra a fotografia de antes da R4 -----------------------

@pytest.fixture(scope="module")
def plano_real():
    return pl.carregar(RAIZ / "config" / "cronograma.yml")


def test_os_dias_ate_05_10_estao_identicos(plano_real):
    for dia in plano_real.dias:
        if dia.data > date(2026, 10, 5):
            continue
        bruto = json.dumps([asdict(f) for b in pl.BLOCOS for f in getattr(dia, b)],
                           ensure_ascii=False, sort_keys=True, default=str)
        assert hashlib.sha256(bruto.encode("utf-8")).hexdigest() == \
            ANTES["dias"][dia.data.isoformat()]["impressao"], dia.data


def test_nenhum_titulo_nem_data_de_tema_mudou(plano_real):
    for dia in plano_real.dias:
        titulos = [f.titulo for b in pl.BLOCOS for f in getattr(dia, b) if f.rotulo != "Extra"]
        assert titulos == ANTES["dias"][dia.data.isoformat()]["titulos"], dia.data
    estudo = {f"{t.materia} | {t.tema}": t.estudo().data.isoformat()
              for t in fichas.temas_do_plano(plano_real) if t.estudo()}
    assert estudo == ANTES["estudo_dos_temas"]


def test_o_total_de_minutos_de_cada_dia_nao_aumentou(plano_real):
    for dia in plano_real.dias:
        for nivel, antes in ANTES["dias"][dia.data.isoformat()]["minutos"].items():
            montado = pl.montar_dia(plano_real, dia.data,
                                    None if nivel == "None" else int(nivel))
            depois = sum(f.duracao or 0 for f in montado.faixas() if not f.opcional)
            assert depois <= antes, (dia.data, nivel, antes, depois)


def test_r7_e_r30_apontam_o_tema_estudado_na_origem(plano_real):
    for dia in plano_real.dias:
        for f in dia.faixas():
            if f.tipo != "revisao" or f.rotulo not in ("R+7", "R+30") or not f.origem:
                continue
            if f.materia and plano_real.e_mista(f.materia):
                continue          # o R+7 dos diagnosticos refaz erros, nao um tema
            origem = plano_real.dia(date.fromisoformat(str(f.origem)))
            tema = fichas.chave_do_tema(fichas.tema_da_faixa(f.titulo, f.materia))
            assert any(fichas.chave_do_tema(fichas.tema_da_faixa(g.titulo, g.materia)) == tema
                       for g in origem.faixas()), (dia.data, f.titulo)


def test_a_extra_e_de_tema_da_mesma_materia_estudado_antes(plano_real):
    estudo = {(t.materia, fichas.chave_do_tema(t.tema)): t.estudo().data
              for t in fichas.temas_do_plano(plano_real) if t.estudo()}
    extras = [(dia.data, f) for dia in plano_real.dias for f in dia.faixas()
              if f.rotulo == "Extra"]
    assert extras, "a R4 nao gravou nenhuma faixa Extra"
    for data, f in extras:
        tema = fichas.chave_do_tema(fichas.tema_da_faixa(f.titulo, f.materia))
        assert estudo[(f.materia, tema)] < data, (data, f.titulo)
        assert f.tipo == "revisao" and not pl.consulta_por_padrao(f)


def test_a_faixa_redistribuida_tem_o_botao_do_resumo(banco_temporario, monkeypatch):
    """20/10: a Extra de manha (Art. 5º, I a XVI) abre o resumo do tema dela."""
    from radar.servico import cronograma as diario
    from radar.servico import fichas as servico_fichas
    from radar.web.app import app

    monkeypatch.setattr(diario, "hoje_local", lambda: date(2026, 10, 20))
    servico_fichas.gravar([fichas.FichaEscrita(
        tema="Art. 5º, caput e incisos I a XVI", materia="Direito Constitucional",
        modelo="m", criado_em="x")])
    html = TestClient(app).get("/hoje?data=2026-10-20").text
    assert "Extra: Art. 5º, caput e incisos I a XVI" in html
    assert 'href="#resumo-art-5o-caput-e-incisos-i-a-xvi"' in html
