"""Os aneis vem do arquivo de configuracao real, nao de lista no codigo."""
from radar import regioes


def test_florianopolis_no_nucleo():
    assert regioes.anel_de("Florianopolis") == "nucleo"


def test_acento_e_caixa_nao_importam():
    assert regioes.anel_de("Florianópolis") == "nucleo"
    assert regioes.anel_de("FLORIANOPOLIS") == "nucleo"
    assert regioes.anel_de("  florianopolis  ") == "nucleo"


def test_itajai_no_proximo():
    assert regioes.anel_de("Itajai") == "proximo"


def test_municipio_de_fora_nao_esta_em_anel_nenhum():
    assert regioes.anel_de("Tunapolis") is None
    assert regioes.anel_de("Bauru") is None


def test_sao_jose_do_cerrito_nao_e_sao_jose():
    """A pegadinha da coleta real: nome que comeca igual, cidade bem diferente.

    Sao Jose e vizinho de Florianopolis; Sao Jose do Cerrito fica na serra,
    a umas 3 horas. Comparar por pedaco do nome colocaria os dois no nucleo.
    """
    assert regioes.anel_de("Sao Jose") == "nucleo"
    assert regioes.anel_de("Sao Jose do Cerrito") is None


def test_sem_municipio():
    assert regioes.anel_de(None) is None
    assert regioes.anel_de("") is None
