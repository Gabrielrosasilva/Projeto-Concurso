"""A letra do gabarito fica escondida ate eu responder no radar (P05, decisao 148).

O que estes testes seguram:

  * a ficha mostra a questao real sem a letra, sem o ✓, sem a explicacao e sem
    a pegadinha enquanto eu nao a respondi no radar; respondida, tudo aparece;
  * o resumo (na ficha e na janela da tela Hoje) troca "(gabarito C)" por
    "(gabarito depois de responder no radar)" - e o dado continua com a letra;
  * a gerada nao conta como questao respondida: ela nao tem codigo de prova.
"""

from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import select

from radar import fichas
from radar.db import sessao
from radar.models import QuestaoDeProva, RespostaDeSimulado, Simulado
from radar.servico import fichas as servico_fichas
from radar.web.app import app
from tests.test_resumo import TEMA, com_resumo, vozes_no_banco  # noqa: F401 - fixtures

ESCONDIDO = fichas.GABARITO_ESCONDIDO


def _responder(ano: int, numero: int, evidencia: str = "alvo", gerada: bool = False,
               letra: str | None = "a"):
    """Grava a resposta a questao (criando-a se ainda nao existe)."""
    with sessao() as s:
        q = s.scalar(select(QuestaoDeProva).where(QuestaoDeProva.ano == ano)
                     .where(QuestaoDeProva.numero == numero))
        if q is None:
            q = QuestaoDeProva(prova_url=f"p{ano}", ano=ano, numero=numero, materia="X",
                               enunciado=f"q{ano}-{numero}?", alternativas={"a": "1", "b": "2"},
                               resposta="a", impressao=f"i{ano}-{numero}", evidencia=evidencia)
            s.add(q)
            s.flush()
        simulado = Simulado(filtros={"quantidade": 1})
        s.add(simulado)
        s.flush()
        s.add(RespostaDeSimulado(simulado_id=simulado.id, questao_id=q.id, ordem=1,
                                 escolhida=letra, acertou=letra == q.resposta, gerada=gerada,
                                 respondida_em=datetime(2026, 10, 5, 15, 0, tzinfo=timezone.utc)
                                 if letra else None))


def test_esconder_gabarito_so_troca_a_letra_da_que_nao_respondi():
    texto = "Cobrou a lei: 2019-q53 (gabarito C) e FEPESE-2024-q8 (gabarito D)."
    assert fichas.esconder_gabarito(texto, {"FEPESE-2024-q8"}) == (
        f"Cobrou a lei: 2019-q53 ({ESCONDIDO}) e FEPESE-2024-q8 (gabarito D).")
    assert fichas.esconder_gabarito(texto, {"2019-q53", "FEPESE-2024-q8"}) == texto
    assert fichas.esconder_gabarito("", set()) == ""


def test_os_codigos_respondidos_separam_alvo_e_complementar(banco_temporario):
    _responder(2019, 53)
    _responder(2024, 8, evidencia="complementar")
    _responder(2013, 1, letra=None)            # aberta e nao respondida
    _responder(2013, 2, gerada=True)           # resposta marcada como gerada

    assert servico_fichas.codigos_respondidos() == {"2019-q53", "FEPESE-2024-q8"}


def test_a_ficha_esconde_a_questao_que_eu_nao_respondi(vozes_no_banco):
    cliente = TestClient(app)

    html = cliente.get("/fichas/vozes-do-verbo?data=2026-10-05").text
    assert f"2013-q7</b> · {ESCONDIDO}" in html
    assert "Gabarito oficial: <b>C</b>" not in html
    assert "</b> ✓" not in html
    assert "aparecem depois que você responder esta questão no radar" in html

    _responder(2013, 7)
    html = cliente.get("/fichas/vozes-do-verbo?data=2026-10-05").text
    assert "2013-q7</b> · gabarito C" in html
    assert "Gabarito oficial: <b>C</b>" in html
    assert "Onde estava a pegadinha" in html


def test_o_resumo_esconde_a_letra_na_ficha_e_na_janela(com_resumo):
    cliente = TestClient(app)
    ident = fichas.id_do_tema(TEMA)

    for url in (f"/fichas/{ident}?data=2026-10-05", "/hoje?data=2026-10-05"):
        html = cliente.get(url).text
        assert f"2019-q53 ({ESCONDIDO})" in html, url
        assert "2019-q53 (gabarito C)" not in html, url
    # O dado continua com a letra: e com ela que a importacao confere.
    (escrita,) = servico_fichas.carregar()
    assert "2019-q53 (gabarito C)" in str(escrita.resumo)

    _responder(2019, 53)
    assert "2019-q53 (gabarito C)" in cliente.get(f"/fichas/{ident}?data=2026-10-05").text


def test_a_questao_real_sabe_se_foi_respondida():
    o = SimpleNamespace(ano=2019, numero=53, conteudo="X", resposta="c", enunciado="e",
                        pegadinha=None, tipo_de_questao=None, conferida=False,
                        alternativas={}, materia="X", prova="p", impressao_do_enunciado="")
    ctx = SimpleNamespace(mudancas_da_questao=None, explicacoes={}, respondidos={"2019-q53"})
    assert fichas._questao_real(o, "alvo", ctx).respondida
    assert not fichas._questao_real(o, "complementar", ctx).respondida   # FEPESE-2019-q53
    assert not fichas._questao_real(o, "alvo", SimpleNamespace(
        mudancas_da_questao=None, explicacoes={}, respondidos=set())).respondida
