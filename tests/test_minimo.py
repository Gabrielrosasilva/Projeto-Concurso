"""Um minimo de respostas so, nas tres telas.

Abaixo do minimo o acerto e sorte: aparece com "Amostra insuficiente", e nao entra
em conta nenhuma. Antes, 1 erro jogava o assunto para o topo por "0%", 1
acerto o jogava para o fim, e a home e o Meu foco podiam apontar materias
diferentes para comecar.
"""
from datetime import date, timedelta

from radar import amostra, foco, onde_estudar
from radar.db import sessao
from radar.edital_materias import MateriaDoEdital
from radar.servico import inicio
from radar.servico.simulado import DesempenhoDaMateria

from tests.test_foco import _concurso, _treinar, com_quadro_do_edital  # noqa: F401

HOJE = date(2026, 10, 1)
EDITAL = [MateriaDoEdital("Direito Penal", 10)]

# Os minimos agora saem do config/amostra.yml (Etapa 4), e nao de um numero
# escrito no codigo: o teste le o mesmo lugar que a conta le.
MINIMOS = amostra.carregar()
MINIMO_NA_MATERIA = MINIMOS.do_nivel("materia")
MINIMO_NO_ASSUNTO = MINIMOS.do_nivel("assunto")


def _linhas(acertos, ultimas=None):
    """Tres assuntos de Direito Penal: A e B do mesmo tamanho, C maior."""
    contagens = {
        ("Direito Penal", "A"): (3, 0),
        ("Direito Penal", "B"): (3, 0),
        ("Direito Penal", "C"): (4, 0),
    }
    linhas = onde_estudar.montar(EDITAL, contagens, acertos,
                                 {"Direito Penal": onde_estudar.EDITAL},
                                 ultimas, hoje=HOJE, minimos=MINIMOS)
    return {l.assunto: l for l in linhas}, [l.assunto for l in linhas]


# --- onde estudar, conta pura -----------------------------------------------

def test_duas_respostas_sao_amostra_pequena():
    por, _ = _linhas({("Direito Penal", "A"): (2, 1)})
    a = por["A"]
    assert a.pontos is None and a.fator == 1.0
    assert a.ordem == a.esperadas
    # O numero continua na linha, para a tela mostrar "acertei 1 de 2".
    assert (a.acertos, a.respondidas, a.amostra_pequena) == (1, 2, True)


def test_com_o_minimo_ganha_pontos():
    por, _ = _linhas({("Direito Penal", "A"): (MINIMO_NO_ASSUNTO, 1)})
    assert por["A"].pontos is not None and not por["A"].amostra_pequena


def test_um_acerto_nao_joga_o_assunto_para_o_fim():
    """Antes: 1 de 1 virava 100%, pontos 0, e o assunto caia para o fim."""
    por, _ = _linhas({("Direito Penal", "A"): (1, 1)})
    assert por["A"].pontos is None
    assert por["A"].ordem == por["B"].ordem       # vale o mesmo que o nao treinado


def test_um_erro_nao_joga_o_assunto_para_o_topo():
    """Antes: 1 de 1 errada virava 0% e, com um mes sem revisar, o fator x2
    passava o assunto na frente do maior. Agora ele e so "nao treinado"."""
    antigo = HOJE - timedelta(days=60)
    _, ordem = _linhas({("Direito Penal", "A"): (1, 0)},
                       {("Direito Penal", "A"): antigo})
    assert ordem[0] == "C"


def test_a_conclusao_nao_cita_porcentagem_de_amostra_pequena():
    por, _ = _linhas({("Direito Penal", "C"): (2, 0)})
    frase = onde_estudar.conclusao(sorted(por.values(), key=lambda l: -l.ordem))
    assert "%" not in frase
    assert "amostra insuficiente" in frase


# --- Meu foco ---------------------------------------------------------------

def test_pior_das_pesadas_ignora_quem_tem_menos_do_minimo():
    abaixo, no_minimo = MINIMO_NA_MATERIA - 1, MINIMO_NA_MATERIA
    acerto = {
        "Direitos Humanos": DesempenhoDaMateria("Direitos Humanos", abaixo, 0),
        "Língua Portuguesa": DesempenhoDaMateria("Língua Portuguesa",
                                                 no_minimo, no_minimo - 1),
    }
    pesadas = {"Direitos Humanos", "Língua Portuguesa"}
    assert foco._pior_das_pesadas(pesadas, acerto) == "Língua Portuguesa"

    del acerto["Língua Portuguesa"]
    assert foco._pior_das_pesadas(pesadas, acerto) is None


def test_a_tabela_mostra_amostra_pequena_e_sem_comece_por_aqui(
    banco_temporario, com_quadro_do_edital
):
    from fastapi.testclient import TestClient

    from radar.web.app import app

    with sessao() as s:
        s.add(_concurso())
    _treinar("Direitos Humanos", acertos=1, erros=1)

    texto = TestClient(app).get("/analises").text

    assert f"2 de {MINIMO_NA_MATERIA} · Amostra insuficiente" in texto
    assert "comece por aqui" not in texto
    assert "é onde eu vou pior" not in texto


# --- home -------------------------------------------------------------------

def test_a_home_diz_amostra_pequena(banco_temporario, com_quadro_do_edital):
    with sessao() as s:
        s.add(_concurso())
    _treinar("Direitos Humanos", acertos=1, erros=1)

    dh = next(p for p in inicio.prioridades(foco.montar())
              if p.materia == "Direitos Humanos")
    assert not dh.treinada and dh.fator == 1.0
    assert dh.porque.endswith(f"Amostra insuficiente (2 de {MINIMO_NA_MATERIA})")


def test_a_home_e_o_meu_foco_apontam_a_mesma_materia(banco_temporario,
                                                     com_quadro_do_edital):
    """Direitos Humanos no minimo e com 0%: e a primeira da home e o "comece
    por aqui". Sociologia fica uma resposta abaixo do minimo: nao conta em
    nenhuma das duas."""
    with sessao() as s:
        s.add(_concurso())
    _treinar("Direitos Humanos", acertos=0, erros=MINIMO_NA_MATERIA)
    _treinar("Sociologia Aplicada", acertos=0, erros=MINIMO_NA_MATERIA - 1)

    painel = foco.montar()
    assert painel.pior_materia == "Direitos Humanos"
    assert inicio.prioridades(painel)[0].materia == "Direitos Humanos"
