"""Deteccao de retificacao: o edital mudou depois que eu baixei?

O manifesto ja guardava o sha256 de cada arquivo desde a fase 3, para
reconstruir o acervo noutra maquina. Serve tambem para isto: se o mesmo
endereco passa a devolver bytes diferentes, o edital foi retificado.

Retificacao muda prazo, vaga e requisito. Descobrir tarde e o tipo de erro que
nao da para corrigir depois.
"""
import hashlib
import json
from datetime import timedelta

import pytest

from radar import provas, servico
from radar.db import sessao
from radar.models import Concurso, agora

PDF_ORIGINAL = b"%PDF-1.4 edital original"
PDF_RETIFICADO = b"%PDF-1.4 edital com a retificacao"


class _RespostaFalsa:
    def __init__(self, conteudo: bytes):
        self.content = conteudo


@pytest.fixture
def acervo(tmp_path, monkeypatch, banco_temporario):
    """Um acervo de mentira com um edital ja baixado e catalogado."""
    from radar import config

    monkeypatch.setattr(config, "diretorio_dados", lambda: tmp_path)
    pasta = tmp_path / "provas" / "fepese" / "2026" / "palhoca"
    pasta.mkdir(parents=True)
    arquivo = pasta / "edital.pdf"
    arquivo.write_bytes(PDF_ORIGINAL)

    registro = {
        "tipo": "edital",
        "url": "https://x.test/edital.pdf",
        "arquivo": "edital.pdf",
        "caminho": "provas/fepese/2026/palhoca/edital.pdf",
        "concurso_url": "https://x.test/concurso",
        "banca": "FEPESE",
        "municipio": "Palhoca",
        "ano": 2026,
        "sha256": hashlib.sha256(PDF_ORIGINAL).hexdigest(),
        "tamanho": len(PDF_ORIGINAL),
    }
    (tmp_path / "provas.json").write_text(
        json.dumps([registro], ensure_ascii=False), encoding="utf-8"
    )

    with sessao() as s:
        s.add(Concurso(
            url="https://x.test/concurso",
            fonte="teste",
            titulo="2026 - Prefeitura Municipal de Palhoca",
            municipio="Palhoca",
            relevancia="nucleo",
            tipo="concurso",
            situacao="inscricoes_abertas",
            inscricoes_ate=agora() + timedelta(days=10),
        ))
    return tmp_path


def _servir(monkeypatch, conteudo: bytes):
    """Faz o download devolver o conteudo que o teste quiser."""
    monkeypatch.setattr(
        servico.Buscador, "get", lambda self, url: _RespostaFalsa(conteudo)
    )


# --- o essencial ------------------------------------------------------------

def test_edital_que_nao_mudou_nao_acusa_nada(acervo, monkeypatch):
    _servir(monkeypatch, PDF_ORIGINAL)

    resultado = servico.conferir_retificacoes()

    assert resultado.conferidos == 1
    assert resultado.mudaram == []


def test_edital_que_mudou_e_acusado(acervo, monkeypatch):
    _servir(monkeypatch, PDF_RETIFICADO)

    resultado = servico.conferir_retificacoes()

    assert len(resultado.mudaram) == 1
    assert resultado.mudaram[0].titulo.endswith("Palhoca")


def test_a_retificacao_diz_qual_arquivo_mudou(acervo, monkeypatch):
    _servir(monkeypatch, PDF_RETIFICADO)

    mudou = servico.conferir_retificacoes().mudaram[0]

    assert mudou.arquivo == "edital.pdf"
    assert mudou.url == "https://x.test/edital.pdf"
    assert mudou.sha_antigo != mudou.sha_novo


def test_a_mesma_retificacao_nao_e_acusada_duas_vezes(acervo, monkeypatch):
    """Depois de avisar, o manifesto passa a valer o arquivo novo - senao toda
    conferencia seguinte repetiria o mesmo alarme."""
    _servir(monkeypatch, PDF_RETIFICADO)
    servico.conferir_retificacoes()

    segunda = servico.conferir_retificacoes()

    assert segunda.mudaram == []


def test_o_arquivo_novo_fica_em_disco(acervo, monkeypatch):
    """Nao adianta so avisar: o acervo precisa ficar com o edital valido."""
    _servir(monkeypatch, PDF_RETIFICADO)

    servico.conferir_retificacoes()

    caminho = acervo / "provas" / "fepese" / "2026" / "palhoca" / "edital.pdf"
    assert caminho.read_bytes() == PDF_RETIFICADO


# --- o que nao vale conferir ------------------------------------------------

def test_concurso_encerrado_nao_e_conferido(acervo, monkeypatch):
    """Edital de concurso encerrado nao vai mais ser retificado, e cada
    conferencia custa uma requisicao e um download."""
    _servir(monkeypatch, PDF_RETIFICADO)
    with sessao() as s:
        s.scalars(servico.select(Concurso)).first().situacao = "encerrado"

    assert servico.conferir_retificacoes().conferidos == 0


def test_prazo_vencido_nao_e_conferido(acervo, monkeypatch):
    _servir(monkeypatch, PDF_RETIFICADO)
    with sessao() as s:
        s.scalars(servico.select(Concurso)).first().inscricoes_ate = (
            agora() - timedelta(days=1)
        )

    assert servico.conferir_retificacoes().conferidos == 0


# --- quando algo da errado --------------------------------------------------

def test_edital_fora_do_ar_nao_derruba_a_conferencia(acervo, monkeypatch):
    def explode(self, url):
        raise OSError("sem rede")

    monkeypatch.setattr(servico.Buscador, "get", explode)

    resultado = servico.conferir_retificacoes()

    assert resultado.falhas == 1
    assert resultado.mudaram == []


def test_pagina_de_erro_no_lugar_do_pdf_nao_vira_retificacao(acervo, monkeypatch):
    """Pagina de erro devolvida com HTTP 200 e comum. Se ela entrasse, o
    acervo trocaria o edital por HTML e ainda acusaria retificacao."""
    _servir(monkeypatch, b"<html>erro 500</html>")

    resultado = servico.conferir_retificacoes()

    assert resultado.mudaram == []
    assert resultado.falhas == 1


def test_sem_edital_nenhum_nao_quebra(banco_temporario, tmp_path, monkeypatch):
    from radar import config

    monkeypatch.setattr(config, "diretorio_dados", lambda: tmp_path)
    (tmp_path / "provas.json").write_text("[]", encoding="utf-8")

    assert servico.conferir_retificacoes().conferidos == 0


# --- o aviso ----------------------------------------------------------------

def test_a_mensagem_diz_o_que_mudou_e_leva_o_link():
    """Dizer QUANTO mudou seria mentira: o sha256 so diz que mudou. Por isso a
    mensagem manda reler, com o link junto."""
    from radar import avisos

    mensagem = avisos.formatar_retificacao(servico.Retificacao(
        concurso_url="https://x.test/c",
        titulo="2026 - Prefeitura Municipal de Palhoca",
        arquivo="edital.pdf",
        url="https://x.test/edital.pdf",
        sha_antigo="a" * 8,
        sha_novo="b" * 8,
    ))

    assert "retificado" in mensagem.lower()
    assert "Palhoca" in mensagem
    assert "https://x.test/edital.pdf" in mensagem


# --- o resumo tem que contar a falha (etapa 11) -----------------------------

def test_o_resumo_diz_quando_nao_consegui_baixar():
    """Antes, edital nenhum conferido dava "Nenhum edital em pe para
    conferir" - que e outra coisa, e a unica que eu nao precisaria fazer nada
    a respeito. Site fora do ar e justamente o caso de rodar de novo."""
    resultado = servico.ResultadoRetificacao(conferidos=0, falhas=3)

    assert "nao consegui baixar 3" in str(resultado)
    assert "Nenhum edital em pe" not in str(resultado)


def test_o_resumo_soma_o_que_deu_certo_e_o_que_falhou():
    resultado = servico.ResultadoRetificacao(conferidos=5, falhas=2)

    texto = str(resultado)
    assert "5 edital(is) conferido(s)" in texto
    assert "nenhum mudou" in texto
    assert "nao consegui baixar 2" in texto


def test_sem_edital_em_pe_continua_dizendo_isso():
    """Sem nada para conferir nao ha o que consertar - e outra frase."""
    assert str(servico.ResultadoRetificacao()) == "Nenhum edital em pe para conferir."


def test_edital_fora_do_ar_aparece_no_resumo(banco_temporario, tmp_path,
                                             monkeypatch, acervo):
    """De ponta a ponta: o download falha e o resumo conta."""
    _servir(monkeypatch, b"<html>erro 500</html>")

    assert "nao consegui baixar 1" in str(servico.conferir_retificacoes())
