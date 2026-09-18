"""O parser entende o formato do feed?

Usa um XML fixo em arquivo, entao roda rapido, funciona sem rede e nao quebra
quando o site sai do ar.
"""
from pathlib import Path

import pytest

from radar.collectors.base import Coletor
from radar.collectors.concursos_no_brasil import ConcursosNoBrasil

FIXTURE = Path(__file__).parent / "fixtures" / "concursos_no_brasil.xml"


@pytest.fixture
def itens(monkeypatch):
    coletor = ConcursosNoBrasil()

    class RespostaFalsa:
        text = FIXTURE.read_text(encoding="utf-8")

    monkeypatch.setattr(coletor, "get", lambda url: RespostaFalsa())
    return coletor.coletar()


def test_le_todos_os_itens(itens):
    assert len(itens) == 3


def test_extrai_uf_pela_url(itens):
    assert itens[0].uf == "SC"


def test_extrai_uf_pela_categoria_quando_a_url_nao_tem(itens):
    # este link nao segue o padrao /concursos/sc/ANO/, entao a UF precisa vir
    # da categoria "Santa Catarina"
    assert "/concursos/sc/" not in itens[1].url
    assert itens[1].uf == "SC"


def test_data_vem_com_fuso(itens):
    publicado = itens[0].publicado_em
    assert publicado.year == 2026
    assert publicado.tzinfo is not None


def test_resumo_sem_html_e_sem_rodape(itens):
    resumo = itens[0].resumo
    assert "<p>" not in resumo
    assert "apareceu primeiro" not in resumo
    assert "nivel superior" in resumo


def test_guarda_as_categorias_no_extra(itens):
    assert itens[0].extra["categorias"] == ["Santa Catarina"]


# --- robots.txt: o que e restricao e o que nao e ----------------------------

class _ColetorDeTeste(Coletor):
    nome = "teste"

    def coletar(self):
        return []


def _com_resposta(monkeypatch, status: int, texto: str = ""):
    """Um coletor cujo robots.txt responde o que o teste mandar."""
    coletor = _ColetorDeTeste()

    class _Resposta:
        status_code = status
        text = texto

    monkeypatch.setattr(coletor.http, "get", lambda *a, **k: _Resposta())
    return coletor


def test_robots_que_proibe_e_respeitado(monkeypatch):
    coletor = _com_resposta(monkeypatch, 200, "User-agent: *\nDisallow: /\n")

    assert coletor._robots_permite("https://exemplo.test/algo") is False


def test_robots_que_libera_e_respeitado(monkeypatch):
    coletor = _com_resposta(monkeypatch, 200, "User-agent: *\nDisallow: /painel\n")

    assert coletor._robots_permite("https://exemplo.test/publico") is True


def test_403_no_robots_nao_e_proibicao(monkeypatch):
    """O leitor do Python trata 403 como "proibido tudo", e isso bloqueou o
    acervo inteiro da IESES: o CDN dela e um balde de arquivos que responde 403
    a qualquer caminho inexistente, inclusive /robots.txt. Pela RFC 9309, 4xx
    quer dizer que nao ha robots.txt."""
    coletor = _com_resposta(monkeypatch, 403, "<Error><Code>AccessDenied</Code></Error>")

    assert coletor._robots_permite("https://cdn.test/prova.pdf") is True


def test_404_no_robots_tambem_libera(monkeypatch):
    coletor = _com_resposta(monkeypatch, 404)

    assert coletor._robots_permite("https://exemplo.test/algo") is True


def test_robots_vazio_nao_restringe(monkeypatch):
    coletor = _com_resposta(monkeypatch, 200, "   \n")

    assert coletor._robots_permite("https://exemplo.test/algo") is True


def test_site_fora_do_ar_nao_derruba_a_coleta(monkeypatch):
    coletor = _ColetorDeTeste()

    def explode(*a, **k):
        raise OSError("sem rede")

    monkeypatch.setattr(coletor.http, "get", explode)

    assert coletor._robots_permite("https://exemplo.test/algo") is True


def test_o_robots_e_lido_uma_vez_por_host(monkeypatch):
    """Sem o cache, cada PDF do acervo pediria o robots.txt de novo."""
    coletor = _ColetorDeTeste()
    pedidos = []

    class _Resposta:
        status_code = 200
        text = "User-agent: *\nDisallow: /nada\n"

    monkeypatch.setattr(coletor.http, "get",
                        lambda url, **k: (pedidos.append(url), _Resposta())[1])

    for caminho in ("/a", "/b", "/c"):
        coletor._robots_permite(f"https://exemplo.test{caminho}")

    assert len(pedidos) == 1
