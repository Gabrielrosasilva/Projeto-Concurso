"""O caderno do NC-UFPR: o gabarito marcado com "►" e a materia no titulo.

A fixture e o texto real (como o pypdf o le) de tres trechos do caderno 304A
da Policia Civil PR 2020, Investigador / Papiloscopista, versao "definitivo":
o quadro de respostas e as questoes 1 a 12 (Penal, Processo Penal e o comeco
de Legislacao Penal Especial), a pagina de Portugues com a anulada 28, e o
fim do caderno.
"""
from pathlib import Path

import pytest

from radar import questoes_ncufpr

FIXTURE = Path(__file__).parent / "fixtures" / "ncufpr" / "pcpr2020_304A.txt"


@pytest.fixture
def lidas():
    return questoes_ncufpr.dividir_em_questoes(FIXTURE.read_text(encoding="utf-8"))


def _questao(lidas, numero):
    return next(q for q in lidas if q.numero == numero)


def test_le_as_questoes_e_o_quadro_de_respostas_nao_vira_questao(lidas):
    assert [q.numero for q in lidas] == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12,
                                         26, 27, 28, 29]
    assert _questao(lidas, 1).enunciado.startswith("Suponha que um sujeito")


def test_cinco_alternativas_de_a_a_e(lidas):
    for questao in lidas:
        assert sorted(questao.alternativas) == list("abcde"), questao.numero


def test_a_resposta_e_a_marcada_com_a_seta(lidas):
    assert [_questao(lidas, n).resposta for n in (1, 2, 3, 6, 11)] == ["b", "e", "d", "a", "b"]


def test_a_anulada_tem_asterisco_e_fica_sem_resposta(lidas):
    anulada = _questao(lidas, 28)
    assert anulada.anulada and anulada.resposta is None
    # A nota "*Questao anulada, portanto..." nao fica colada na alternativa.
    assert all("anulada" not in texto for texto in anulada.alternativas.values())
    assert not any(q.anulada for q in lidas if q.numero != 28)


def test_a_materia_e_o_titulo_de_cima(lidas):
    assert _questao(lidas, 1).materia == "Noções de Direito Penal"
    assert _questao(lidas, 6).materia == "Noções de Direito Processual Penal"
    assert _questao(lidas, 11).materia == "Noções de Legislação Penal Especial"
    assert _questao(lidas, 27).materia == "Língua Portuguesa"


def test_sem_tab_e_a_ultima_alternativa_nao_leva_a_questao_de_baixo(lidas):
    primeira = _questao(lidas, 1)
    assert primeira.alternativas["c"] == "corrupção passiva."
    assert primeira.alternativas["e"] == "apropriação indébita."
    assert all("\t" not in t for q in lidas for t in [q.enunciado, *q.alternativas.values()])


def test_o_titulo_da_materia_fica_no_jeito_do_acervo():
    assert questoes_ncufpr.nome_da_materia("NOÇÕES DE DIREITO PENAL") == "Noções de Direito Penal"
    assert questoes_ncufpr.nome_da_materia("LÍNGUA PORTUGUESA") == "Língua Portuguesa"


# --- do config ao banco (decisao 168) ---------------------------------------

def test_a_lista_do_config_so_traz_banca_que_o_radar_sabe_ler(tmp_path):
    from radar.servico import provas as servico_provas

    lista = servico_provas.carregar_provas_de_outras_bancas()
    assert lista and {p["banca"] for p in lista} == {"NC-UFPR", "Selecon", "Cebraspe",
                                                      "FGV", "Access"}
    # Sempre o link do site oficial da banca.
    assert all(p["caderno"].startswith(("https://servicos.nc.ufpr.br/",
                                        "https://selecon.org.br/",
                                        "https://cdn.cebraspe.org.br/",
                                        "https://conhecimento.fgv.br/",
                                        "https://anexos.cdn.selecao.net.br/")) for p in lista)
    # O que o robo nao pode baixar (os termos da FGV, o robots.txt do CDN da
    # Selecon e da Access) so entra baixado a mao, e com a versao do caderno
    # (decisao 172).
    a_mao = [p for p in lista if p["caderno"].startswith(
        ("https://conhecimento.fgv.br/", "https://anexos.cdn.selecao.net.br/"))]
    assert a_mao and all(p.get("arquivo") and p.get("arquivo_do_gabarito") and p.get("versao")
                         for p in a_mao)
    # O Cebraspe diz quais questoes sao de lei; a SERES responde pela justificativa.
    seres = next(p for p in lista if "SERES_PE_21" in p["caderno"])
    assert seres["ler"] == ["21-60"] and seres["resposta"] == "justificativas"
    sejusp = next(p for p in lista if p["banca"] == "Selecon")
    assert sejusp["gabarito"] and sejusp["materias"]["26-30"] == "Direito Penal"

    outra = tmp_path / "lista.yml"
    outra.write_text("provas:\n- banca: Banca Sem Leitor\n  caderno: https://x.test/a.pdf\n",
                     encoding="utf-8")
    assert servico_provas.carregar_provas_de_outras_bancas(outra) == []


def test_baixa_le_e_grava_como_outra_banca(banco_temporario, monkeypatch):
    from sqlalchemy import select

    from radar import provas, servico
    from radar.db import sessao
    from radar.models import QuestaoDeProva

    class BuscadorDePdf:
        def get(self, url):
            class Resposta:
                text = ""
                content = b"%PDF-1.4 caderno\n%%EOF"
            return Resposta()

    monkeypatch.setattr(servico.provas, "Buscador", BuscadorDePdf)
    monkeypatch.setattr(servico.provas, "carregar_provas_de_outras_bancas", lambda: [{
        "banca": "NC-UFPR", "ano": 2021, "orgao": "Polícia Civil do Paraná", "uf": "PR",
        "cargo": "Investigador de Polícia / Papiloscopista",
        "pagina": "https://servicos.nc.ufpr.br/PortalNC/Concurso?concurso=PCPR2020",
        "caderno": "https://servicos.nc.ufpr.br/documentos/pcpr2020/prova/definitivo/304A.pdf"}])

    resultado = servico.montar_acervo_de_outras_bancas()
    assert resultado.provas == 1
    (registro,) = [r for r in provas.carregar_manifesto() if r["tipo"] == "prova"]
    assert registro["banca"] == "NC-UFPR" and registro["cargo"].startswith("Investigador")
    # A segunda vez nao baixa de novo.
    assert servico.montar_acervo_de_outras_bancas().provas == 0

    monkeypatch.setattr(questoes_ncufpr, "extrair_texto",
                        lambda caminho, layout=False: FIXTURE.read_text(encoding="utf-8"))
    lidas = servico.extrair_questoes(limite=5, banca="NC-UFPR")
    assert lidas.questoes == 16
    with sessao() as s:
        gravadas = list(s.scalars(select(QuestaoDeProva)))
    assert {q.evidencia for q in gravadas} == {"fora"}
    assert {q.banca for q in gravadas} == {"NC-UFPR"}
    primeira = next(q for q in gravadas if q.numero == 1)
    assert primeira.resposta == "b" and primeira.materia == "Noções de Direito Penal"
