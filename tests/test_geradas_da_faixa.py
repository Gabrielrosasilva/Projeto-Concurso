"""As geradas da faixa de questoes e a tela de gerar (R6, 05/10/2026).

O que estes testes seguram: a faixa diz o tema e o no; primeiro o Qconcursos,
depois as geradas, que so treinam; sem gerada, os 3 passos com o N certo (a
faixa dividida entre os nos, no minimo 5); com gerada bastante, so o botao;
sem no, "sem no na arvore" e nenhum comando; o --elemento so quando o no e um
elemento; e nenhum comando com --valendo. Sem data de hoje e sem Windows.
"""
from datetime import date
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from radar import fichas
from radar.db import sessao
from radar.models import QuestaoGerada
from radar.servico import cronograma as diario
from radar.servico import geradas
from radar.web.app import app

PENAL = "Direito Penal"
INFRACAO = f"{PENAL} > Infração penal: elementos, espécies"
ABOLITIO = f"{PENAL} > Tipicidade > Abolitio criminis"
ART_2 = f"{ABOLITIO} > CP, art. 2º"
TEMA = "Fato típico e nexo causal (art. 13)"


def _faixa(titulo=f"Fixação: {TEMA}", questoes=8, materia=PENAL, **mais):
    base = dict(tipo="questoes", titulo=titulo, materia=materia, questoes=questoes,
                filtro="Direito Penal > fato típico", nos=(), conteudo=None, desligada=False)
    base.update(mais)
    return SimpleNamespace(**base)


def _ficha(nos=(INFRACAO,), **mais):
    base = dict(tema=TEMA, materia=PENAL, nos=list(nos),
                assunto="Infração penal: elementos, espécies",
                modelo="Claude Code, de teste", criado_em="2026-10-02T12:00:00+00:00")
    base.update(mais)
    return fichas.FichaEscrita(**base)


def test_no_com_zero_gerada_mostra_o_aviso_e_os_3_passos_com_o_n_certo():
    gf = fichas.geradas_da_faixa(_faixa(questoes=8), _ficha(), {})
    (n,) = gf.nos
    assert (n.no, n.geradas, n.pedir) == (INFRACAO, 0, 8)
    assert gf.precisa_gerar
    assert gf.passos == [
        r'.venv\Scripts\radar.exe gerar --pedido --modo treino --materia "Direito Penal" '
        r'--assunto "Infração penal: elementos, espécies" --quantas 8 --nivel misturada',
        fichas.PASSO_NO_CLAUDE_CODE, fichas.COMANDO_DE_IMPORTAR]
    assert fichas.COMANDO_DE_IMPORTAR == r".venv\Scripts\radar.exe gerar --importar data/resposta_ia.json"


def test_o_n_e_a_faixa_menos_as_geradas_com_o_minimo_de_5():
    (n,) = fichas.geradas_da_faixa(_faixa(questoes=20), _ficha(), {INFRACAO: 17}).nos
    assert n.pedir == fichas.PEDIDO_MINIMO_DE_GERADAS == 5


def test_no_com_gerada_suficiente_mostra_so_o_botao():
    gf = fichas.geradas_da_faixa(_faixa(questoes=8), _ficha(), {INFRACAO: 12})
    (n,) = gf.nos
    assert (n.geradas, n.pedir, n.comando) == (12, 0, None)
    assert not gf.precisa_gerar and gf.passos == []


def test_varios_nos_dividem_a_faixa_por_igual():
    nos = [f"{PENAL} > A", f"{PENAL} > B", f"{PENAL} > C", f"{PENAL} > D"]
    gf = fichas.geradas_da_faixa(_faixa(questoes=10), _ficha(nos=nos), {nos[0]: 3})
    assert [n.cota for n in gf.nos] == [3, 3, 2, 2]
    assert [n.pedir for n in gf.nos] == [0, 5, 5, 5]


def test_titulo_diferente_do_no_guarda_os_dois_nomes():
    gf = fichas.geradas_da_faixa(_faixa(), _ficha(), {})
    assert gf.tema == TEMA
    assert gf.nos[0].no == INFRACAO and gf.nos[0].nome == "Infração penal: elementos, espécies"


def test_ficha_sem_no_e_sem_no_na_arvore_sem_comando():
    """A ficha sem no escreve o assunto (na LEP, a lei inteira): contar as
    geradas dele seria aproximar."""
    gf = fichas.geradas_da_faixa(_faixa(), _ficha(nos=()), {INFRACAO: 30})
    assert gf.sem_no and gf.nos == () and gf.passos == []


def test_sem_ficha_vale_os_nos_do_plano_ou_o_conteudo():
    pelo_plano = fichas.geradas_da_faixa(_faixa(nos=(INFRACAO,)), None, {})
    assert [n.no for n in pelo_plano.nos] == [INFRACAO]
    pelo_conteudo = fichas.geradas_da_faixa(_faixa(conteudo=INFRACAO), None, {})
    assert [n.no for n in pelo_conteudo.nos] == [INFRACAO]
    assert fichas.geradas_da_faixa(_faixa(), None, {}).sem_no


def test_o_elemento_so_entra_quando_o_no_e_um_elemento():
    assert '--elemento "CP, art. 2º"' in fichas.comando_de_gerar(ART_2, 5)
    assert '--subassunto "Abolitio criminis"' in fichas.comando_de_gerar(ART_2, 5)
    assert "--elemento" not in fichas.comando_de_gerar(ABOLITIO, 5)
    assert "--elemento" not in fichas.comando_de_gerar(INFRACAO, 5)


def test_nenhum_comando_mostrado_tem_valendo():
    gf = fichas.geradas_da_faixa(_faixa(), _ficha(), {})
    for texto in gf.passos + [fichas.comando_de_gerar(ART_2)]:
        assert "--valendo" not in texto and "python -m radar" not in texto


# --- o banco: a contagem e as telas ------------------------------------------------

def _gerada(conteudo, impressao, *, rejeitada=False, resposta="a"):
    with sessao() as s:
        s.add(QuestaoGerada(modo="do_zero", materia=PENAL, conteudo=conteudo,
                            enunciado=f"Enunciado gerado {impressao}, com tamanho bastante.",
                            alternativas={l: l for l in "abcde"}, resposta=resposta,
                            impressao=impressao, rejeitada=rejeitada))


def test_a_contagem_por_no_pega_o_que_esta_abaixo_ate_o_elemento(banco_temporario):
    _gerada(ART_2, "g1")
    _gerada(ABOLITIO, "g2")
    _gerada(ABOLITIO, "g3", rejeitada=True)
    _gerada(INFRACAO, "g4", resposta=None)
    assert geradas.contagem_por_no([ABOLITIO, ART_2, INFRACAO]) == {
        ABOLITIO: 2, ART_2: 1, INFRACAO: 0}


@pytest.fixture
def em_05_10(banco_temporario, monkeypatch):
    """O cronograma real, com o dado vazio do banco de teste (nenhuma ficha):
    a faixa do bonus tem `nos` no plano, e a fixacao do art. 13 nao tem no."""
    monkeypatch.setattr(diario, "hoje_local", lambda: date(2026, 10, 5))


def test_a_tela_hoje_diz_o_no_e_os_passos_e_sem_no_nao_da_comando(em_05_10):
    html = TestClient(app).get("/hoje?data=2026-10-05").text
    assert "Você estudou:" in html and "na árvore:" in html
    # O bonus: tres nos do plano, 10 questoes divididas, no minimo 5 cada.
    assert "Raciocínio Lógico &gt; Tabelas-verdade" in html or "Raciocínio Lógico > Tabelas-verdade" in html
    assert '--assunto &#34;Tabelas-verdade&#34; --quantas 5' in html or '--assunto "Tabelas-verdade" --quantas 5' in html
    assert "Não há questão gerada deste assunto ainda" in html
    # A fixacao do art. 13 sem ficha e sem nos: sem no, e nenhum comando dela.
    assert "<b>sem nó na árvore</b>" in html
    assert "Infração penal" not in html
    assert "--valendo" not in html and "python -m radar" not in html


def test_a_tela_de_gerar_lista_o_no_do_cronograma_com_zero(em_05_10):
    itens = geradas.nos_do_cronograma(date(2026, 10, 5))
    tabelas = next(i for i in itens if i["geradas"].no == "Raciocínio Lógico > Tabelas-verdade")
    assert tabelas["geradas"].geradas == 0 and tabelas["geradas"].pedir >= 5
    html = TestClient(app).get("/geradas").text
    assert "Os assuntos do cronograma" in html
    assert "sem questão gerada" in html
    assert "--valendo" not in html.split("Os assuntos do cronograma")[1].split("</section>")[0]
