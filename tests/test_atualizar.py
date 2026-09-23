"""`radar atualizar`: a rotina inteira, na ordem certa.

Existe porque manter o radar em dia exigia seis comandos numa sequencia que so
fazia sentido para quem a escreveu: coletar antes de detalhar, detalhar antes
de baixar edital, edital antes de elegibilidade.
"""
import pytest
from typer.testing import CliRunner

from radar import servico
from radar.cli import app

executor = CliRunner()


class _Resultado:
    """Um resultado de etapa que so sabe virar texto."""

    def __init__(self, texto="feito"):
        self.texto = texto

    def __str__(self):
        return self.texto


@pytest.fixture
def etapas_falsas(monkeypatch, banco_temporario):
    """Troca cada etapa por uma que so anota que foi chamada."""
    chamadas = []

    def anotar(nome, devolve=None):
        def acao(*a, **k):
            chamadas.append(nome)
            return devolve if devolve is not None else _Resultado()
        return acao

    monkeypatch.setattr(servico, "coletar_tudo", anotar("coletar", []))
    monkeypatch.setattr(servico, "detalhar_pendentes", anotar("detalhar"))
    monkeypatch.setattr(servico, "montar_acervo", anotar("acervo"))
    monkeypatch.setattr(servico, "ler_elegibilidade", anotar("elegibilidade"))
    monkeypatch.setattr(servico, "conferir_retificacoes", anotar("retificacoes"))
    monkeypatch.setattr(servico, "avisar", anotar("avisar"))
    monkeypatch.setattr(servico, "extrair_questoes", anotar("questoes"))
    monkeypatch.setattr(servico, "listar", lambda **k: [])
    return chamadas


def test_roda_as_etapas_na_ordem(etapas_falsas):
    """A ordem nao e detalhe: sem detalhar nao ha hotsite, sem hotsite nao ha
    edital, e sem edital nao ha o que exige."""
    executor.invoke(app, ["atualizar", "--sem-avisar"])

    assert etapas_falsas == [
        "coletar", "detalhar", "acervo", "elegibilidade", "retificacoes",
    ]


def test_nao_avisa_no_telegram_por_padrao(etapas_falsas):
    """Quem manda mensagem e o robo do GitHub, e ele e o unico. Com os dois
    avisando, o mesmo concurso chegava duas vezes no celular: cada um guardava
    a sua propria lista do que ja tinha avisado."""
    executor.invoke(app, ["atualizar"])

    assert "avisar" not in etapas_falsas


def test_da_para_avisar_daqui_quando_eu_pedir(etapas_falsas):
    executor.invoke(app, ["atualizar", "--avisar"])

    assert "avisar" in etapas_falsas


def test_o_completo_inclui_provas_e_questoes(etapas_falsas):
    """Baixar prova e ler caderno demora, entao fica fora do dia a dia."""
    executor.invoke(app, ["atualizar", "--completo", "--sem-avisar"])

    assert "questoes" in etapas_falsas


def test_o_padrao_nao_inclui_provas_e_questoes(etapas_falsas):
    executor.invoke(app, ["atualizar", "--sem-avisar"])

    assert "questoes" not in etapas_falsas


def test_etapa_que_falha_nao_para_a_rotina(monkeypatch, etapas_falsas):
    """Mesma regra que vale para fonte fora do ar desde a primeira fase."""
    def explode(*a, **k):
        raise OSError("sem rede")

    monkeypatch.setattr(servico, "detalhar_pendentes", explode)

    resultado = executor.invoke(app, ["atualizar", "--sem-avisar"])

    assert "retificacoes" in etapas_falsas, "as etapas seguintes rodaram"
    assert "1 etapa(s) com problema" in resultado.output


def test_o_resumo_diz_quando_esta_tudo_certo(etapas_falsas):
    resultado = executor.invoke(app, ["atualizar", "--sem-avisar"])

    assert "Tudo em dia" in resultado.output


def test_o_resumo_conta_as_inscricoes_abertas(monkeypatch, etapas_falsas):
    monkeypatch.setattr(servico, "listar", lambda **k: [1, 2, 3])

    resultado = executor.invoke(app, ["atualizar", "--sem-avisar"])

    assert "3 concurso(s) com inscricao aberta" in resultado.output
