"""Cruzar quem eu sou com o que o edital exige.

A regra que vale para o arquivo inteiro: campo em branco quer dizer "nao sei",
e nao "nao tenho". Falta de informacao nunca vira barreira.
"""
import pytest

from radar import perfil
from radar.elegibilidade import Exigencias


def _exigencias(**mudancas) -> Exigencias:
    base = dict(niveis=["superior", "medio"], legivel=True)
    base.update(mudancas)
    return Exigencias(**base)


EU = perfil.Perfil(ano_de_nascimento=1990, escolaridade="superior",
                   formacao="Sistemas de Informacao", cnh=["B"])


# --- escolaridade -----------------------------------------------------------

def test_tenho_o_nivel_que_a_vaga_pede():
    veredito = perfil.avaliar(_exigencias(niveis=["superior"]), EU)

    assert veredito.situacao == "elegivel"
    assert "superior" in veredito.motivo


def test_quem_tem_superior_atende_vaga_de_medio():
    """Escolaridade e piso, e nao teto."""
    assert perfil.avaliar(_exigencias(niveis=["medio"]), EU).situacao == "elegivel"


def test_vaga_so_de_superior_barra_quem_tem_medio():
    so_medio = perfil.Perfil(escolaridade="medio")

    veredito = perfil.avaliar(_exigencias(niveis=["superior"]), so_medio)

    assert veredito.situacao == "inelegivel"


def test_sem_escolaridade_informada_fica_a_confirmar():
    """Nao ter dito qual e a minha escolaridade nao me torna inelegivel."""
    vazio = perfil.Perfil()

    veredito = perfil.avaliar(_exigencias(), vazio)

    assert veredito.situacao == "a_confirmar"
    assert "a confirmar" in veredito.motivo


def test_edital_sem_nivel_identificado_fica_a_confirmar():
    assert perfil.avaliar(_exigencias(niveis=[]), EU).situacao == "a_confirmar"


# --- idade ------------------------------------------------------------------

def test_idade_acima_do_teto_barra():
    velho = perfil.Perfil(ano_de_nascimento=1960, escolaridade="superior")

    veredito = perfil.avaliar(_exigencias(idade_maxima=30), velho)

    assert veredito.situacao == "inelegivel"
    assert "teto" in veredito.motivo


def test_idade_dentro_do_teto_nao_barra():
    veredito = perfil.avaliar(_exigencias(idade_maxima=99), EU)

    assert veredito.situacao == "elegivel"


def test_teto_de_idade_sem_eu_ter_informado_a_minha():
    """O certo aqui e avisar, e nao concluir. Campo vazio nao e "nao tenho"."""
    sem_idade = perfil.Perfil(escolaridade="superior")

    veredito = perfil.avaliar(_exigencias(idade_maxima=30), sem_idade)

    assert veredito.situacao == "elegivel"
    assert "nao informei" in veredito.motivo


# --- CNH --------------------------------------------------------------------

def test_cnh_que_eu_nao_tenho_e_avisada_mas_nao_barra():
    """Um edital pede CNH em algumas vagas e nao em outras, e o radar guarda um
    registro por concurso: barrar o concurso inteiro seria errado."""
    veredito = perfil.avaliar(_exigencias(cnh="D"), EU)

    assert veredito.situacao == "elegivel"
    assert "CNH D" in veredito.motivo


def test_cnh_que_eu_tenho_nao_gera_aviso():
    veredito = perfil.avaliar(_exigencias(cnh="A OU B"), EU)

    assert "CNH" not in veredito.motivo


def test_cnh_sem_categoria_dita_nao_gera_aviso():
    """"exige CNH" sem dizer qual nao da para comparar com a minha."""
    veredito = perfil.avaliar(_exigencias(cnh="sim"), EU)

    assert "CNH" not in veredito.motivo


# --- edital ilegivel --------------------------------------------------------

def test_edital_ilegivel_nao_vira_veredito():
    veredito = perfil.avaliar(Exigencias(legivel=False), EU)

    assert veredito.situacao == "a_confirmar"
    assert "nao pode ser lido" in veredito.motivo


# --- o arquivo de perfil ----------------------------------------------------

def test_le_o_perfil_do_yaml(tmp_path, monkeypatch):
    from radar import config

    (tmp_path / "perfil.yml").write_text(
        "ano_de_nascimento: 1990\nescolaridade: Superior\n"
        "formacao: Sistemas de Informacao\ncnh: [b, D]\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(config, "diretorio_config", lambda: tmp_path)
    perfil.recarregar()

    quem = perfil.carregar()

    assert quem.ano_de_nascimento == 1990
    assert quem.escolaridade == "superior", "a escolaridade e comparada em minusculo"
    assert quem.cnh == ["B", "D"], "a categoria e comparada em maiusculo"
    perfil.recarregar()


def test_perfil_em_branco_nao_e_erro(tmp_path, monkeypatch):
    """O arquivo nasce com os campos vazios, para eu preencher quando quiser."""
    from radar import config

    (tmp_path / "perfil.yml").write_text(
        "ano_de_nascimento:\nescolaridade:\ncnh: []\n", encoding="utf-8"
    )
    monkeypatch.setattr(config, "diretorio_config", lambda: tmp_path)
    perfil.recarregar()

    quem = perfil.carregar()

    assert quem.idade is None and quem.escolaridade is None and quem.cnh == []
    perfil.recarregar()


def test_sem_arquivo_nenhum_nao_quebra(tmp_path, monkeypatch):
    from radar import config

    monkeypatch.setattr(config, "diretorio_config", lambda: tmp_path)
    perfil.recarregar()

    assert perfil.carregar().escolaridade is None
    perfil.recarregar()
