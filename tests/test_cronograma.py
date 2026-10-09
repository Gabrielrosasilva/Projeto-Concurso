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
    # 1690 ate a 6A, mais as 14 questoes da manha nos 26 dias uteis a partir
    # de 02/10 (8 de fixacao + 6 de Portugues): 1690 + 26 x 14 = 2054. Os
    # diagnosticos em 10/10 e o R+7 deles em 17/10 (decisao 105): -5 do R+7
    # e -10 de contagem em 10/10, +20 +20 dos diagnosticos, +40 do R+7.
    # A redistribuicao da R4 (decisao 124): a teoria e a lei seca que sairam
    # dos temas que nao cairam viraram questoes de revisao - +2 em 07, 13 e
    # 21/10 e +8 em 20/10. Os minutos do dia nao mudaram. 2119 + 14 = 2133.
    assert total == 2133


def test_arquivo_real_horarios_conferidos(real):
    assert cronograma.montar_dia(real, date(2026, 9, 28)).noite[-1].fim == time(19, 35)
    # 28/10 tem o R+7 e o R+30 divididos em Direito e Portugues (P04): as 3
    # de Portugues arredondam para 10 min, e a noite acaba 10 min depois.
    assert cronograma.montar_dia(real, date(2026, 10, 28)).noite[-1].fim == time(21, 25)
    # Em 10/10 o diagnostico de Portugues abre a noite, antes do simulado
    # (decisao 134): a medicao sem o cansaco de 90 minutos de prova.
    noite = cronograma.montar_dia(real, date(2026, 10, 10)).noite
    assert noite[0].tipo == "diagnostico"
    assert (noite[0].inicio, noite[0].fim) == (time(18, 0), time(18, 50))
    assert noite[2].tipo == "simulado"
    assert (noite[2].inicio, noite[2].fim) == (time(19, 0), time(20, 30))


def test_revisao_nao_mistura_portugues_com_direito(real):
    """P04: o "fiz" grava tudo na materia da faixa; as 3 de Portugues do R+7
    e do R+30 iam para o acerto de Direito. De 08/10 em diante elas sao uma
    faixa propria (o 07/10 ja estava anotado e ficou como era)."""
    for dia in real.dias:
        if dia.data < date(2026, 10, 8):
            continue
        for bloco in cronograma.BLOCOS:
            faixas = getattr(dia, bloco)
            for i, f in enumerate(faixas):
                if f.tipo != "revisao":
                    continue
                assert "de Português:" not in (f.detalhe or ""), (dia.data, f.titulo)
                if f.materia == "Língua Portuguesa" and f.rotulo in ("R+7", "R+30"):
                    # Logo depois da de Direito, com a mesma origem.
                    anterior = faixas[i - 1]
                    assert anterior.rotulo == f.rotulo
                    assert anterior.origem == f.origem
                    assert f.questoes == 3


def test_r7_de_09_10_tem_as_duas_linhas(real):
    noite = cronograma.montar_dia(real, date(2026, 10, 9)).noite
    assert (noite[0].materia, noite[0].questoes) == ("Lei de Execução Penal", 7)
    assert (noite[1].materia, noite[1].questoes) == ("Língua Portuguesa", 3)
    assert noite[1].titulo == "R+7: Verbo 2: emprego dos tempos e modos"
    assert (noite[0].duracao, noite[1].duracao) == (20, 10)


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


# --- o mapa do ano -----------------------------------------------------------
#
# O mapa e DADO: estes testes conferem a leitura e as tres regras de ordem, e
# nao o conteudo do plano - trocar um ciclo de data nao pode quebrar teste.

def _mapa_de_teste():
    return [
        {"nome": "Ciclo 1", "inicio": "2026-09-28", "fim": "2026-11-07",
         "foco": "A base"},
        {"nome": "Ciclo 2", "inicio": "2026-11-09", "fim": "2026-12-19",
         "foco": "O resto do programa"},
        {"nome": "Ciclo 4+", "inicio": "2027-03-01", "foco": "Reforço"},
        {"nome": "Pós-edital", "quando": "quando sair", "foco": "Ajustado ao edital"},
    ]


def _com_mapa(tmp_path, mapa):
    return _com_mudanca(tmp_path, lambda d: d.update(mapa=mapa))


def test_o_mapa_do_arquivo_real_tem_as_etapas_na_ordem():
    plano = cronograma.carregar(REAL)
    assert [e.nome for e in plano.mapa] == [
        "Ciclo 1", "Ciclo 2", "Pausa de fim de ano", "Ciclo 3", "Ciclo 4+",
        "Pós-edital",
    ]
    assert all(e.foco for e in plano.mapa)


@pytest.mark.parametrize("dia, esperada", [
    (date(2026, 9, 28), "Ciclo 1"),              # o primeiro dia dele
    (date(2026, 10, 20), "Ciclo 1"),
    (date(2026, 11, 7), "Ciclo 1"),              # o ultimo dia dele
    (date(2026, 11, 10), "Ciclo 2"),
    (date(2026, 12, 25), "Pausa de fim de ano"),
    (date(2027, 1, 20), "Ciclo 3"),
    (date(2027, 3, 1), "Ciclo 4+"),              # etapa em aberto, no 1o dia
    (date(2028, 5, 5), "Ciclo 4+"),              # e um ano depois, ainda ela
])
def test_o_ciclo_de_cada_data(dia, esperada):
    assert cronograma.carregar(REAL).etapa_do_mapa(dia).nome == esperada


@pytest.mark.parametrize("dia", [
    date(2026, 9, 1),     # antes de tudo comecar
    date(2026, 11, 8),    # o domingo entre o Ciclo 1 e o 2
    date(2027, 2, 28),    # o domingo entre o Ciclo 3 e o 4+
])
def test_data_fora_de_qualquer_etapa_nao_inventa_ciclo(dia):
    assert cronograma.carregar(REAL).etapa_do_mapa(dia) is None


def test_a_etapa_sem_data_nunca_e_a_de_agora():
    plano = cronograma.carregar(REAL)
    pos_edital = plano.mapa[-1]
    assert pos_edital.inicio is None
    assert not pos_edital.contem(date(2027, 7, 1))
    assert not pos_edital.terminou(date(2027, 7, 1))


def test_como_o_periodo_se_le_na_tela(tmp_path):
    mapa = cronograma.carregar(_com_mapa(tmp_path, _mapa_de_teste())).mapa
    assert mapa[0].periodo == "28/09/2026 a 07/11/2026"
    assert mapa[2].periodo == "a partir de 01/03/2027"
    assert mapa[3].periodo == "quando sair"


def test_arquivo_sem_mapa_continua_valendo(plano):
    """O mapa e enfeite util: sem ele a tela Hoje inteira nao pode parar."""
    assert plano.mapa == []
    assert plano.etapa_do_mapa(date(2026, 9, 28)) is None


def test_etapa_que_comeca_antes_da_anterior_acabar_e_recusada(tmp_path):
    mapa = _mapa_de_teste()
    mapa[1]["inicio"] = "2026-11-07"          # o ultimo dia do Ciclo 1
    with pytest.raises(cronograma.ErroNoCronograma, match="antes de Ciclo 1 acabar"):
        cronograma.carregar(_com_mapa(tmp_path, mapa))


def test_etapa_fora_de_ordem_e_recusada(tmp_path):
    mapa = _mapa_de_teste()
    mapa[0], mapa[1] = mapa[1], mapa[0]
    with pytest.raises(cronograma.ErroNoCronograma, match="antes de Ciclo 2 acabar"):
        cronograma.carregar(_com_mapa(tmp_path, mapa))


def test_fim_antes_do_inicio_e_recusado(tmp_path):
    mapa = _mapa_de_teste()
    mapa[0]["fim"] = "2026-09-01"
    with pytest.raises(cronograma.ErroNoCronograma, match="vem antes do inicio"):
        cronograma.carregar(_com_mapa(tmp_path, mapa))


def test_fim_sem_inicio_e_recusado(tmp_path):
    mapa = _mapa_de_teste()
    del mapa[0]["inicio"]
    with pytest.raises(cronograma.ErroNoCronograma, match="`fim` sem ter `inicio`"):
        cronograma.carregar(_com_mapa(tmp_path, mapa))


def test_nada_pode_vir_depois_de_uma_etapa_em_aberto(tmp_path):
    """Ciclo 4+ nao tem fim: outra etapa com data depois dele se sobreporia."""
    mapa = _mapa_de_teste()
    mapa.insert(3, {"nome": "Ciclo 5", "inicio": "2027-06-01", "foco": "x"})
    with pytest.raises(cronograma.ErroNoCronograma, match="fica em aberto"):
        cronograma.carregar(_com_mapa(tmp_path, mapa))


def test_etapa_com_data_depois_de_etapa_sem_data_e_recusada(tmp_path):
    mapa = _mapa_de_teste()
    mapa.append({"nome": "Ciclo 6", "inicio": "2028-01-03", "foco": "x"})
    with pytest.raises(cronograma.ErroNoCronograma, match="ultima da lista"):
        cronograma.carregar(_com_mapa(tmp_path, mapa))


@pytest.mark.parametrize("campo, erro", [
    ("nome", "falta o `nome`"),
    ("foco", "falta o `foco`"),
])
def test_etapa_sem_nome_ou_sem_foco_e_recusada(tmp_path, campo, erro):
    mapa = _mapa_de_teste()
    del mapa[0][campo]
    with pytest.raises(cronograma.ErroNoCronograma, match=erro):
        cronograma.carregar(_com_mapa(tmp_path, mapa))


def test_o_leitor_rapido_le_o_plano_igual_ao_leitor_em_python():
    """O cronograma e lido com a libyaml quando ela existe (F6): o resultado
    tem de ser o mesmo do leitor em Python."""
    texto = MINI.read_text(encoding="utf-8")

    assert yaml.load(texto, Loader=cronograma.LEITOR_DO_YAML) == yaml.safe_load(texto)
