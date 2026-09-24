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


# --- uma grafia so para cada municipio ---------------------------------------

def test_grafia_canonica_vem_do_yaml():
    """Cada fonte escreve de um jeito, e o banco acabava com o mesmo municipio
    como se fossem cidades diferentes."""
    for escrito in ("Florianopolis", "FLORIANOPOLIS", "florianopolis",
                    "Florian\u00f3polis", " Florianopolis "):
        assert regioes.nome_canonico(escrito) == "Florianópolis"


def test_acento_e_cedilha_no_mesmo_municipio():
    """O caso real: a FEPESE gravava Palhoca e o feed gravava Palhoca com
    cedilha, e o historico do municipio ficava partido em dois."""
    assert regioes.nome_canonico("Palho" + chr(0xE7) + "a") == "Palhoça"
    assert regioes.nome_canonico("S\u00e3o Jos\u00e9") == "São José"


def test_municipio_de_fora_volta_como_veio():
    """Inventar grafia para cidade de fora de SC seria pior que manter a da
    fonte: o YAML so tem municipio catarinense."""
    assert regioes.nome_canonico("Ribeirao Preto") == "Ribeirao Preto"


def test_sem_municipio_continua_sem():
    assert regioes.nome_canonico(None) is None
    assert regioes.nome_canonico("") is None


# --- a grafia de quem esta fora dos aneis (cosmetico) -----------------------
#
# Para quem esta nos aneis, quem manda e o config/regioes.yml. Para o resto
# nao ha lista, e cada fonte digita de um jeito: o banco de verdade tinha
# "Caçador" e "Cacador", "GASPAR" e "Gaspar", "Araranguá" e "Ararangua".

def test_o_acento_vence_a_falta_dele():
    from radar.servico.coleta import melhor_grafia

    assert melhor_grafia(["Cacador", "Caçador"])["cacador"] == "Caçador"
    assert melhor_grafia(["Araranguá", "Ararangua"])["ararangua"] == "Araranguá"


def test_o_acento_vence_mesmo_sendo_minoria():
    """No banco real "Chapeco" aparecia 15 vezes e "Chapecó" uma so. Vale a
    grafia certa, e nao a mais repetida."""
    from radar.servico.coleta import melhor_grafia

    nomes = ["Chapeco"] * 15 + ["Chapecó"]
    assert melhor_grafia(nomes)["chapeco"] == "Chapecó"


def test_caixa_normal_vence_o_maiusculo():
    from radar.servico.coleta import melhor_grafia

    assert melhor_grafia(["GASPAR", "Gaspar"])["gaspar"] == "Gaspar"
    assert melhor_grafia(["GASPAR", "GASPAR", "Gaspar"])["gaspar"] == "Gaspar"


def test_empate_desempata_pela_mais_comum_e_e_estavel():
    """Duas execucoes tem que dar o mesmo resultado."""
    from radar.servico.coleta import melhor_grafia

    nomes = ["Conquista D’Oeste", "Conquista d’Oeste", "Conquista d’Oeste"]
    assert melhor_grafia(nomes)["conquista d’oeste"] == "Conquista d’Oeste"
    assert melhor_grafia(nomes) == melhor_grafia(list(reversed(nomes)))


def test_uma_grafia_so_continua_como_esta():
    from radar.servico.coleta import melhor_grafia

    assert melhor_grafia(["Curitiba"])["curitiba"] == "Curitiba"


def test_o_reclassificar_unifica_a_grafia_no_banco(banco_temporario):
    """De ponta a ponta: o banco para de ter a mesma cidade de dois jeitos."""
    from sqlalchemy import select

    from radar import servico
    from radar.db import sessao
    from radar.models import Concurso

    with sessao() as s:
        for n, grafia in enumerate(["Cacador", "Caçador", "GASPAR", "Gaspar"]):
            s.add(Concurso(
                url=f"https://a.test/{n}", fonte="teste", tipo="concurso",
                titulo=f"Concurso Prefeitura de {grafia} (SC) abre vagas",
                uf="SC", municipio=grafia, municipio_confirmado=True,
            ))

    servico.reclassificar()

    with sessao() as s:
        gravados = {c.municipio for c in s.scalars(select(Concurso))}
    assert gravados == {"Caçador", "Gaspar"}
