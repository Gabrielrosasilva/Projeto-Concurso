"""O cronograma: leitura, conferencia e a conta dos horarios."""
from datetime import date, time, timedelta
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from radar import config, cronograma
from radar.cli import app

MINI = Path(__file__).parent / "fixtures" / "cronograma_mini.yml"
REAL = config.RAIZ / "config" / "cronograma.yml"


@pytest.fixture
def plano():
    return cronograma.carregar(MINI)


def _com_mudanca(tmp_path, mudar):
    """Grava uma copia do mini com uma alteracao, para testar a conferencia."""
    dados = yaml.safe_load(MINI.read_text(encoding="utf-8"))
    mudar(dados)
    arquivo = tmp_path / "cronograma.yml"
    arquivo.write_text(yaml.safe_dump(dados, allow_unicode=True), encoding="utf-8")
    return arquivo


# --- a conta dos horarios ----------------------------------------------------

def test_15_questoes_viram_40_minutos(plano):
    dia = cronograma.montar_dia(plano, date(2026, 9, 28))
    primeira = dia.noite[0]
    assert primeira.duracao == 40          # 15 x 2,5 = 37,5, sobe para 40
    assert (primeira.inicio, primeira.fim) == (time(18, 0), time(18, 40))


def test_horarios_saem_da_soma_a_partir_do_bloco(plano):
    dia = cronograma.montar_dia(plano, date(2026, 9, 28))
    assert [(f.inicio, f.fim) for f in dia.manha] == [
        (time(10, 15), time(11, 5)),
        (time(11, 5), time(11, 15)),
        (time(11, 15), time(11, 45)),
    ]
    # 40 + 10 + 25 (10 x 2,5) + 20
    assert dia.noite[-1].fim == time(19, 35)


def test_nivel_troca_a_rampa_e_empurra_os_horarios(plano):
    dia = cronograma.montar_dia(plano, date(2026, 9, 28), nivel=2)
    direito, pausa, portugues, correcao = dia.noite
    assert direito.questoes == 20
    assert (direito.inicio, direito.fim) == (time(18, 0), time(18, 50))
    assert pausa.inicio == time(18, 50)
    assert portugues.questoes == 10
    assert correcao.fim == time(19, 45)


def test_nivel_nao_mexe_no_plano_gravado(plano):
    cronograma.montar_dia(plano, date(2026, 9, 28), nivel=2)
    assert plano.dia(date(2026, 9, 28)).noite[0].questoes == 15


def test_nivel_que_nao_existe_da_erro(plano):
    with pytest.raises(cronograma.ErroNoCronograma, match="Nivel 7"):
        cronograma.montar_dia(plano, date(2026, 9, 28), nivel=7)


def test_min_por_questao_da_faixa_vence_o_padrao(plano):
    simulado = cronograma.montar_dia(plano, date(2026, 10, 3)).noite[0]
    assert (simulado.inicio, simulado.fim) == (time(18, 0), time(19, 30))
    assert simulado.cronometrado


def test_opcional_nao_entra_no_total(plano):
    dia = cronograma.montar_dia(plano, date(2026, 9, 28))
    assert dia.pos22[-1].opcional
    assert dia.total_questoes == 25        # 15 + 10, sem as 10 do bonus


def test_minutos_de_estudo_sao_a_manha_sem_pausa(plano):
    dia = cronograma.montar_dia(plano, date(2026, 9, 28))
    assert dia.minutos_de_estudo == 80


def test_campos_de_exibicao_chegam(plano):
    dia = cronograma.montar_dia(plano, date(2026, 9, 29))
    assert dia.feriado == "Feriado de teste"
    revisao = dia.noite[0]
    assert (revisao.rotulo, revisao.origem) == ("R+7", "2026-09-22")
    assert plano.dia(date(2026, 9, 28)).manha[0].baralho == "[1] Direito Penal"


def test_domingo_e_fora_do_plano_devolvem_none(plano):
    assert cronograma.montar_dia(plano, date(2026, 10, 4)) is None   # domingo
    assert cronograma.montar_dia(plano, date(2026, 9, 1)) is None
    assert cronograma.montar_dia(plano, date(2026, 10, 1)) is None   # buraco


# --- faixa_atual -------------------------------------------------------------

def test_faixa_atual_no_meio_de_uma_faixa(plano):
    dia = cronograma.montar_dia(plano, date(2026, 9, 28))
    atual, proxima = cronograma.faixa_atual(dia, time(10, 30))
    assert atual.titulo == "Aplicação da lei penal"
    assert proxima.tipo == "pausa"


def test_faixa_atual_entre_blocos(plano):
    dia = cronograma.montar_dia(plano, date(2026, 9, 28))
    atual, proxima = cronograma.faixa_atual(dia, time(14, 0))
    assert atual is None
    assert proxima.inicio == time(18, 0)


def test_faixa_atual_depois_da_ultima(plano):
    dia = cronograma.montar_dia(plano, date(2026, 9, 28))
    assert cronograma.faixa_atual(dia, time(23, 30)) == (None, None)


# --- a conferencia do arquivo ------------------------------------------------

def test_data_repetida(tmp_path):
    def mudar(d):
        d["dias"][1]["data"] = "2026-09-28"
    with pytest.raises(cronograma.ErroNoCronograma, match="2026-09-28.*repetida"):
        cronograma.carregar(_com_mudanca(tmp_path, mudar))


def test_domingo_no_plano(tmp_path):
    def mudar(d):
        d["dias"][2]["data"] = "2026-10-04"
    with pytest.raises(cronograma.ErroNoCronograma, match="2026-10-04.*domingo"):
        cronograma.carregar(_com_mudanca(tmp_path, mudar))


def test_faixa_sem_duracao_nem_questoes(tmp_path):
    def mudar(d):
        del d["dias"][1]["manha"][0]["duracao"]
    with pytest.raises(cronograma.ErroNoCronograma,
                       match="2026-09-29.*nem questoes"):
        cronograma.carregar(_com_mudanca(tmp_path, mudar))


def test_tipo_desconhecido(tmp_path):
    def mudar(d):
        d["dias"][0]["manha"][0]["tipo"] = "teorai"
    with pytest.raises(cronograma.ErroNoCronograma, match="2026-09-28.*teorai"):
        cronograma.carregar(_com_mudanca(tmp_path, mudar))


def test_rampa_com_chave_que_nao_existe(tmp_path):
    def mudar(d):
        d["dias"][0]["noite"][0]["rampa"] = "constitucional"
    with pytest.raises(cronograma.ErroNoCronograma,
                       match="2026-09-28.*constitucional"):
        cronograma.carregar(_com_mudanca(tmp_path, mudar))


def test_horario_de_bloco_invalido(tmp_path):
    def mudar(d):
        d["blocos"]["noite"]["inicio"] = "18h"
    with pytest.raises(cronograma.ErroNoCronograma, match="noite.*18h"):
        cronograma.carregar(_com_mudanca(tmp_path, mudar))


def test_data_por_extenso():
    assert (cronograma.data_por_extenso(date(2026, 9, 28))
            == "segunda-feira, 28 de setembro de 2026")


# --- o arquivo de verdade ----------------------------------------------------

@pytest.fixture(scope="module")
def real():
    return cronograma.carregar(REAL)


def test_arquivo_real_cobre_o_ciclo(real):
    datas = [d.data for d in real.dias]
    assert len(datas) == 36
    assert datas[0] == date(2026, 9, 28)
    assert datas[-1] == date(2026, 11, 7)
    assert all(d.weekday() != cronograma.DOMINGO for d in datas)


def test_arquivo_real_total_de_questoes(real):
    total = sum(cronograma.montar_dia(real, d.data).total_questoes
                for d in real.dias)
    assert total == 1690


def test_arquivo_real_horarios_conferidos(real):
    assert cronograma.montar_dia(real, date(2026, 9, 28)).noite[-1].fim == time(19, 35)
    assert cronograma.montar_dia(real, date(2026, 10, 28)).noite[-1].fim == time(21, 15)
    simulado = cronograma.montar_dia(real, date(2026, 10, 10)).noite[0]
    assert simulado.tipo == "simulado"
    assert (simulado.inicio, simulado.fim) == (time(18, 0), time(19, 30))


# --- o comando ---------------------------------------------------------------

@pytest.fixture
def config_mini(tmp_path, monkeypatch):
    (tmp_path / "cronograma.yml").write_text(MINI.read_text(encoding="utf-8"),
                                             encoding="utf-8")
    monkeypatch.setenv("RADAR_CONFIG_DIR", str(tmp_path))


def test_comando_hoje_mostra_o_dia(config_mini):
    saida = CliRunner().invoke(app, ["hoje", "--data", "2026-09-28"])
    assert saida.exit_code == 0, saida.output
    assert "Segunda-feira, 28 de setembro de 2026" in saida.output
    assert "18:00-18:40" in saida.output
    assert "Total do dia: 25 questões" in saida.output
    assert "Mínima: Só o Anki." in saida.output


def test_comando_hoje_domingo_e_fora_do_ciclo(config_mini):
    runner = CliRunner()
    assert "Domingo é descanso total." in runner.invoke(
        app, ["hoje", "--data", "2026-10-04"]).output
    assert "começa em 28/09/2026" in runner.invoke(
        app, ["hoje", "--data", "2026-09-01"]).output
    assert "terminou em 03/10/2026" in runner.invoke(
        app, ["hoje", "--data", "2026-12-01"]).output


# --- o gatilho: o nivel da semana --------------------------------------------

SEGUNDA = date(2026, 9, 28)


def _plano_de_semanas(n_semanas=5, feriados=(), niveis_da_rampa=6):
    """Plano sintetico: n semanas de segunda a sabado, uma faixa de rampa por noite."""
    dias = []
    for semana in range(1, n_semanas + 1):
        for i in range(6):
            data = SEGUNDA + timedelta(days=7 * (semana - 1) + i)
            dias.append(cronograma.Dia(
                data=data, semana=semana,
                feriado="Feriado" if data in feriados else None,
                noite=[cronograma.Faixa(bloco="noite", tipo="questoes", titulo="q",
                                        rampa="direito", questoes=15)],
            ))
    return cronograma.Plano(
        ciclo=1, titulo="teste", inicio=dias[0].data, fim=dias[-1].data,
        meta_da_prova={},
        blocos={c: cronograma.Bloco(c, c, time(18)) for c in cronograma.BLOCOS},
        minutos_por_questao=2.5,
        rampa={n: {"direito": 10 + 5 * n, "portugues": 10}
               for n in range(1, niveis_da_rampa + 1)},
        gatilho={"sobe_com_dias_na_ideal": 5, "semana_ruim_com_dias_abaixo": 3,
                 "desce_apos_semanas_ruins": 2},
        semanas={}, dias=dias,
    )


def _dias_da_semana(semana):
    inicio = SEGUNDA + timedelta(days=7 * (semana - 1))
    return [inicio + timedelta(days=i) for i in range(6)]


def _marcas(semana, *metas):
    """{data: meta} para os dias da semana, na ordem; None = sem marcacao."""
    return {d: m for d, m in zip(_dias_da_semana(semana), metas) if m}


def _depois_da_semana(semana):
    return _dias_da_semana(semana)[-1] + timedelta(days=1)   # o domingo


def test_primeira_semana_e_nivel_1():
    n = cronograma.niveis(_plano_de_semanas(), {}, SEGUNDA)[1]
    assert (n.planejado, n.calculado, n.efetivo) == (1, 1, 1)
    assert n.motivo == "Primeira semana: nível 1."


def test_semana_boa_sobe():
    metas = _marcas(1, *["ideal"] * 6)
    n = cronograma.niveis(_plano_de_semanas(), metas, _depois_da_semana(1))[2]
    assert (n.situacao, n.calculado, n.efetivo) == ("subiu", 2, 2)
    assert n.motivo == ("A semana 1 fechou com 6 dias na Ideal e nenhum zerado: "
                        "nível 2 (Direito 20, Português 10).")


def test_4_na_ideal_e_2_reduzidas_e_neutra():
    metas = _marcas(1, "ideal", "ideal", "ideal", "ideal", "reduzida", "reduzida")
    n = cronograma.niveis(_plano_de_semanas(), metas, _depois_da_semana(1))[2]
    assert (n.situacao, n.efetivo) == ("neutra", 1)
    assert "4 dias na Ideal e 2 abaixo: repete o nível 1" in n.motivo


def test_3_abaixo_e_ruim_e_repete():
    metas = _marcas(1, "ideal", "ideal", "ideal", "minima", "reduzida", "minima")
    n = cronograma.niveis(_plano_de_semanas(), metas, _depois_da_semana(1))[2]
    assert (n.situacao, n.efetivo) == ("ruim", 1)
    assert n.motivo == ("A semana 1 fechou com 3 dias abaixo da Ideal: repete o "
                        "nível 1 (Direito 15, Português 10).")


def test_duas_ruins_seguidas_descem():
    ruim = ("ideal", "ideal", "ideal", "minima", "minima", "minima")
    metas = {**_marcas(1, *["ideal"] * 6), **_marcas(2, *["ideal"] * 6),
             **_marcas(3, *ruim), **_marcas(4, *ruim)}
    n = cronograma.niveis(_plano_de_semanas(), metas, _depois_da_semana(4))
    assert [n[s].efetivo for s in (1, 2, 3, 4, 5)] == [1, 2, 3, 3, 2]
    assert n[4].situacao == "ruim"
    assert n[5].situacao == "desceu"
    assert n[5].motivo.startswith("Segunda semana ruim seguida: desce para o nível 2")


def test_neutra_no_meio_separa_as_ruins():
    ruim = ("minima",) * 6
    neutra = ("ideal",) * 4 + ("minima",) * 2
    metas = {**_marcas(1, *["ideal"] * 6), **_marcas(2, *ruim),
             **_marcas(3, *neutra), **_marcas(4, *ruim)}
    n = cronograma.niveis(_plano_de_semanas(), metas, _depois_da_semana(4))
    assert n[5].situacao == "ruim"          # a 2a ruim, mas nao seguida
    assert n[5].efetivo == 2


def test_nunca_abaixo_de_1():
    metas = {**_marcas(1, *["nao_fiz"] * 6), **_marcas(2, *["nao_fiz"] * 6)}
    n = cronograma.niveis(_plano_de_semanas(), metas, _depois_da_semana(2))[3]
    assert (n.situacao, n.calculado, n.efetivo) == ("desceu", 1, 1)


def test_nunca_acima_do_planejado_nem_da_rampa():
    plano = _plano_de_semanas(n_semanas=4, niveis_da_rampa=2)
    metas = {d: "ideal" for s in (1, 2, 3) for d in _dias_da_semana(s)}
    n = cronograma.niveis(plano, metas, _depois_da_semana(3))
    assert [n[s].planejado for s in (1, 2, 3, 4)] == [1, 2, 2, 2]
    assert [n[s].efetivo for s in (1, 2, 3, 4)] == [1, 2, 2, 2]


def test_efetivo_e_o_menor_entre_planejado_e_calculado():
    ruim = ("minima",) * 6
    metas = {**_marcas(1, *ruim), **_marcas(2, *["ideal"] * 6)}
    n = cronograma.niveis(_plano_de_semanas(), metas, _depois_da_semana(2))[3]
    assert (n.planejado, n.calculado, n.efetivo) == (3, 2, 2)


def test_semana_em_andamento_nao_e_avaliada():
    # Quinta da semana 1, e tudo ideal ate aqui: ainda nao conta. As semanas
    # que nem comecaram ficam na carga do plano.
    metas = _marcas(1, "ideal", "ideal", "ideal")
    n = cronograma.niveis(_plano_de_semanas(), metas, SEGUNDA + timedelta(days=3))
    assert (n[2].situacao, n[2].efetivo) == ("futura", 2)
    assert n[2].motivo == ("Semana futura: carga do plano (Direito 20, Português "
                           "10). O nível de verdade sai quando a semana 1 fechar.")
    assert (n[3].situacao, n[3].efetivo) == ("futura", 3)
    # No sabado ainda nao fechou; no domingo, sim.
    sabado = _dias_da_semana(1)[-1]
    assert cronograma.niveis(_plano_de_semanas(), metas, sabado)[2].situacao == "futura"
    assert cronograma.niveis(_plano_de_semanas(), metas,
                             _depois_da_semana(1))[2].situacao == "ruim"


def test_semana_futura_nao_mexe_na_conta_das_outras():
    # Semana 1 ruim e fechada; "hoje" e a segunda da semana 2.
    metas = _marcas(1, *["minima"] * 6)
    n = cronograma.niveis(_plano_de_semanas(), metas, _depois_da_semana(1) + timedelta(days=1))
    assert (n[2].situacao, n[2].efetivo) == ("ruim", 1)
    assert [n[s].situacao for s in (3, 4, 5)] == ["futura"] * 3
    assert [n[s].efetivo for s in (3, 4, 5)] == [3, 4, 5]


def test_dia_sem_marcacao_conta_como_abaixo():
    metas = _marcas(1, "ideal", "ideal", "ideal", None, None, None)
    n = cronograma.niveis(_plano_de_semanas(), metas, _depois_da_semana(1))[2]
    assert n.situacao == "ruim"
    assert "3 dias abaixo da Ideal (3 sem marcação)" in n.motivo


def test_sem_marcacao_nao_e_zerado():
    # 5 na Ideal e 1 dia esquecido: sobe. So o nao_fiz trava a subida.
    metas = _marcas(1, *["ideal"] * 5, None)
    n = cronograma.niveis(_plano_de_semanas(), metas, _depois_da_semana(1))[2]
    assert n.situacao == "subiu"


def test_feriado_com_minima_conta_como_ideal():
    feriado = _dias_da_semana(1)[0]
    metas = _marcas(1, "minima", "ideal", "ideal", "ideal", "ideal", "reduzida")
    com = cronograma.niveis(_plano_de_semanas(feriados={feriado}), metas,
                            _depois_da_semana(1))[2]
    sem = cronograma.niveis(_plano_de_semanas(), metas, _depois_da_semana(1))[2]
    assert com.situacao == "subiu"
    assert sem.situacao == "neutra"


def test_feriado_sem_marcacao_continua_abaixo():
    feriado = _dias_da_semana(1)[0]
    metas = _marcas(1, None, "ideal", "ideal", "ideal", "ideal", "reduzida")
    n = cronograma.niveis(_plano_de_semanas(feriados={feriado}), metas,
                          _depois_da_semana(1))[2]
    assert n.situacao == "neutra"


def test_nao_fiz_impede_subir_mesmo_com_5_na_ideal():
    metas = _marcas(1, *["ideal"] * 5, "nao_fiz")
    n = cronograma.niveis(_plano_de_semanas(), metas, _depois_da_semana(1))[2]
    assert (n.situacao, n.efetivo) == ("neutra", 1)
    assert "5 dias na Ideal, mas 1 dia zerado" in n.motivo


def test_horarios_da_noite_andam_quando_o_nivel_muda(real):
    segunda_da_semana_2 = date(2026, 10, 5)
    semana_1 = [d.data for d in real.dias if d.semana == 1]

    def noite(metas):
        n = cronograma.niveis(real, metas, segunda_da_semana_2)[2]
        return cronograma.montar_dia(real, segunda_da_semana_2, n.efetivo).noite

    parada = noite({})                                  # nivel 1: Direito 15
    subiu = noite({d: "ideal" for d in semana_1})       # nivel 2: Direito 20
    direito_parada = next(f for f in parada if f.rampa == "direito")
    direito_subiu = next(f for f in subiu if f.rampa == "direito")
    assert (direito_parada.questoes, direito_subiu.questoes) == (15, 20)
    # 15 questoes = 40 min, 20 = 50 min: tudo depois anda 10 minutos.
    minutos = lambda t: t.hour * 60 + t.minute          # noqa: E731
    assert minutos(direito_subiu.fim) == minutos(direito_parada.fim) + 10
    assert minutos(subiu[-1].fim) == minutos(parada[-1].fim) + 10


def test_gatilho_incompleto_da_erro(tmp_path):
    def mudar(d):
        del d["gatilho"]["desce_apos_semanas_ruins"]
    with pytest.raises(cronograma.ErroNoCronograma, match="desce_apos_semanas_ruins"):
        cronograma.carregar(_com_mudanca(tmp_path, mudar))


# --- a Reduzida acompanha o nivel --------------------------------------------

def test_reduzida_diz_as_questoes_de_direito_do_nivel(real):
    dia = date(2026, 10, 28)
    assert "{direito}" in real.dia(dia).reduzida        # no arquivo, a marca
    nivel_1 = cronograma.montar_dia(real, dia, 1).reduzida
    nivel_5 = cronograma.montar_dia(real, dia, 5).reduzida
    assert nivel_1 == "A manhã inteira + só as 15 questões de Lei de Execução Penal à noite."
    assert "só as 25 questões" in nivel_5
    # Sem nivel, vale o numero gravado na faixa.
    assert "só as 25 questões" in cronograma.montar_dia(real, dia).reduzida


def test_nenhuma_reduzida_sobra_com_a_marca(real):
    for d in real.dias:
        texto = cronograma.montar_dia(real, d.data).reduzida or ""
        assert "{" not in texto, d.data


def test_marca_sem_faixa_de_direito_da_erro(tmp_path):
    def mudar(d):
        d["dias"][1]["reduzida"] = "Só as {direito} questões."
    with pytest.raises(cronograma.ErroNoCronograma, match="2026-09-29.*rampa: direito"):
        cronograma.carregar(_com_mudanca(tmp_path, mudar))
