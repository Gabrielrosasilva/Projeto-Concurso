"""Classificador de relevancia.

Todos os titulos aqui sao REAIS: sairam da primeira coleta de verdade,
17/09/2026. E por isso que eles cobrem os casos chatos.
"""
import pytest

from radar.classificador import (
    classificar,
    detectar_tipo,
    extrair_municipio,
    extrair_salario,
)
from radar.collectors.base import ItemColetado


def item(titulo: str, uf: str | None = None) -> ItemColetado:
    return ItemColetado(titulo=titulo, url="https://exemplo.test/x", uf=uf)


# --- o que e concurso e o que e noticia ------------------------------------

@pytest.mark.parametrize("titulo,esperado", [
    ("Concurso Prefeitura de Tunapolis (SC) tem salario de R$ 5.832", "concurso"),
    ("Camara de Capinzal (SC) oferece ate R$ 4,5 mil em novo concurso", "concurso"),
    ("Edital Prefeitura de Ascurra (SC) oferta salarios de ate R$ 6,2 mil", "concurso"),
    ("FUNCAMP (SP) tem quatro editais abertos com salarios de ate R$ 6 mil", "concurso"),
    ("Prefeitura de Sao Jose do Cerrito (SC) abre processo seletivo", "seletivo"),
    ("Seletivo Prefeitura de Ponte Nova (MG) abre vagas", "seletivo"),
    ("Prefeitura da Serra (ES) oferta salarios de R$ 4,1 mil em selecao", "seletivo"),
    ("Prefeitura de Sao Lourenco do Oeste (SC) abre vaga para Psicologo", "desconhecido"),
])
def test_detecta_tipo(titulo, esperado):
    assert detectar_tipo(titulo) == esperado


def test_noticia_nao_e_concurso():
    """O caso que motivou este filtro: veio no feed e nao tem nada a ver."""
    titulo = "Bolsa Familia passa a ter novo valor em outubro, com reajuste de 15,04%"
    assert detectar_tipo(titulo) == "noticia"


# --- municipio --------------------------------------------------------------

@pytest.mark.parametrize("titulo,esperado", [
    ("Concurso Prefeitura de Tunapolis (SC) tem salario de R$ 5.832", "Tunapolis"),
    ("Camara de Capinzal (SC) oferece ate R$ 4,5 mil", "Capinzal"),
    ("Prefeitura de Sao Lourenco do Oeste (SC) abre vaga", "Sao Lourenco do Oeste"),
    ("Prefeitura da Serra (ES) oferta salarios", "Serra"),
    ("Concurso Camara de Dois Corregos (SP) oferece salario", "Dois Corregos"),
    ("EMDURB de Bauru (SP) oferta iniciais", "Bauru"),
    ("Seletivo Prefeitura de Ponte Nova (MG) abre vagas", "Ponte Nova"),
])
def test_extrai_municipio(titulo, esperado):
    assert extrair_municipio(titulo) == esperado


def test_sem_municipio_no_titulo():
    # FUNCAMP e fundacao, nao municipio: nao ha o que extrair
    assert extrair_municipio("FUNCAMP (SP) tem quatro editais abertos") is None
    assert extrair_municipio("AgSUS anuncia novo edital de seletivo") is None


# --- salario ----------------------------------------------------------------

@pytest.mark.parametrize("titulo,esperado", [
    ("Concurso Prefeitura de Tunapolis (SC) tem salario de R$ 5.832", 5832.0),
    ("Camara de Capinzal (SC) oferece ate R$ 4,5 mil", 4500.0),
    ("Prefeitura de Piratuba (SC) abre vagas com inicial de R$ 2 mil", 2000.0),
    ("Prefeitura de Montenegro (RS) oferta iniciais de R$ 9,5 mil", 9500.0),
    ("Edital Prefeitura de Ascurra (SC) oferta salarios de ate R$ 6,2 mil", 6200.0),
])
def test_extrai_salario(titulo, esperado):
    assert extrair_salario(titulo) == esperado


def test_titulo_sem_salario():
    assert extrair_salario("Prefeitura de Sao Jose do Cerrito (SC) abre seletivo") is None


def test_pega_o_maior_valor_quando_ha_faixa():
    titulo = "Concurso oferece de R$ 2 mil a R$ 8 mil"
    assert extrair_salario(titulo) == 8000.0


# --- relevancia: a regra dos tres aneis -------------------------------------

def test_nucleo():
    r = classificar(item("Prefeitura de Palhoca (SC) abre concurso", uf="SC"))
    assert r.relevancia == "nucleo"
    assert "Palhoca" in r.motivo


def test_proximo():
    r = classificar(item("Concurso Prefeitura de Itajai (SC) oferece vagas", uf="SC"))
    assert r.relevancia == "proximo"


def test_sc_fora_dos_aneis_e_remoto():
    r = classificar(item("Camara de Capinzal (SC) oferece concurso", uf="SC"))
    assert r.relevancia == "remoto"
    assert r.municipio == "Capinzal"


def test_a_pegadinha_sao_jose_do_cerrito():
    """Comecar igual a um municipio do nucleo nao pode colocar no nucleo."""
    r = classificar(item("Prefeitura de Sao Jose do Cerrito (SC) abre seletivo", uf="SC"))
    assert r.relevancia == "remoto"
    assert r.municipio == "Sao Jose do Cerrito"


def test_municipio_de_outro_estado_e_remoto():
    r = classificar(item("Concurso Camara de Dois Corregos (SP) oferece vagas", uf="SP"))
    assert r.relevancia == "remoto"


def test_concurso_sem_uf_fica_indefinido():
    """Pode ser federal com prova em Florianopolis. Nunca chutar."""
    r = classificar(item("Concurso TRF-1 abre vagas em todo o pais", uf=None))
    assert r.relevancia == "indefinida"
    assert "edital" in r.motivo.lower()


def test_sc_sem_municipio_identificado_fica_indefinido():
    r = classificar(item("Governo de Santa Catarina anuncia concurso", uf="SC"))
    assert r.relevancia == "indefinida"


def test_todo_resultado_tem_motivo():
    """O motivo e obrigatorio: sem ele nao da para auditar a decisao."""
    for titulo, uf in [
        ("Prefeitura de Palhoca (SC) abre concurso", "SC"),
        ("Camara de Capinzal (SC) oferece concurso", "SC"),
        ("Concurso TRF-1 abre vagas", None),
    ]:
        assert classificar(item(titulo, uf=uf)).motivo.strip()


# --- a URL como sinal (fase 1.6) --------------------------------------------
# Conferido no site real: post de concurso mora em /concursos/UF/ANO/..., e
# noticia sobre auxilio mora em /beneficios-sociais/. Isso importa mais na
# carga inicial, que traz milhares de posts de uma vez.

def test_caminho_de_noticia_vence_a_palavra_do_titulo():
    """Este titulo tem "vagas" e enganaria o filtro por palavra-chave."""
    tipo = detectar_tipo(
        "INSS paga hoje com vagas para todos os beneficiarios",
        url="https://concursosnobrasil.com/beneficios-sociais/2026/09/inss-paga/",
    )
    assert tipo == "noticia"


def test_bolsa_familia_pelo_caminho_da_url():
    tipo = detectar_tipo(
        "Bolsa Familia passa a ter novo valor em outubro",
        url="https://concursosnobrasil.com/beneficios-sociais/2026/06/calendario/",
    )
    assert tipo == "noticia"


def test_caminho_de_concurso_salva_titulo_sem_palavra_chave():
    """Titulo vago, mas o post esta na secao de concursos: vale investigar."""
    tipo = detectar_tipo(
        "Prefeitura de Garuva (SC) oferta 29 oportunidades",
        url="https://concursosnobrasil.com/concursos/sc/2026/09/garuva/",
    )
    assert tipo != "noticia"


def test_sem_url_continua_funcionando():
    """A URL e um sinal a mais, nao um requisito."""
    assert detectar_tipo("Concurso Prefeitura de Palhoca abre vagas") == "concurso"
    assert detectar_tipo("Bolsa Familia tem novo valor") == "noticia"


def test_classificar_usa_a_url_do_item():
    resultado = classificar(
        ItemColetado(
            titulo="INSS paga hoje com vagas para todos",
            url="https://concursosnobrasil.com/beneficios-sociais/2026/09/inss/",
            uf="SC",
        )
    )
    assert resultado.tipo == "noticia"


# --- orgao estadual de SC ----------------------------------------------------
#
# Bug real: "2019 - Secretaria de Estado da Administracao Prisional e
# Socioeducativa" (o concurso da Policia Penal SC, o meu alvo principal) caia
# em `indefinida` com o motivo "pode ser federal". Orgao estadual nao tem
# municipio no titulo, entao nao havia o que o classificador achasse.

@pytest.mark.parametrize("titulo", [
    "2013 – Secretaria de Estado da Justiça e CidadaniaAgente Penitenciário "
    "(masculino)Agente Penitenciário (feminino)Agente de Segurança "
    "Socioeducativo (masculino)Agente de Segurança Socioeducativo (feminino)",
    "2019 – Secretaria de Estado da Administração Prisional e Socioeducativa",
    "2016 – Governo do Estado de Santa Catarina Secretaria de Estado da "
    "Justiça e Cidadania Concurso Público Edital 001/2016-SJC/SC",
    "2025 – Polícia Científica do Estado de Santa Catarina – PCISC",
    "Concurso Polícia Penal SC abre inscricoes",
    "Corpo de Bombeiros Militar de Santa Catarina abre concurso",
])
def test_orgao_estadual_de_sc_vira_relevancia_estadual(titulo):
    # tipo vem preenchido porque e assim que a FEPESE manda: o titulo dela e
    # so o nome do orgao, sem a palavra "concurso" para o detector achar.
    resultado = classificar(
        ItemColetado(titulo=titulo, url=f"https://exemplo.test/{hash(titulo)}",
                     uf="SC", tipo="concurso")
    )
    assert resultado.relevancia == "estadual"
    assert resultado.motivo == (
        "Orgao estadual de SC; polos de prova a confirmar no edital."
    )


def test_estadual_nunca_vira_nucleo_por_palpite():
    """A sede fica em Florianopolis, mas a prova pode ser em qualquer polo.
    Chutar `nucleo` aqui e exatamente o erro que a regra existe para evitar."""
    resultado = classificar(
        ItemColetado(
            titulo="2019 – Secretaria de Estado da Administração Prisional "
                   "e Socioeducativa",
            url="https://exemplo.test/sap",
            uf="SC",
            tipo="concurso",
        )
    )
    assert resultado.relevancia != "nucleo"
    assert resultado.municipio is None


def test_orgao_estadual_de_outro_estado_nao_e_estadual():
    """"Estadual" aqui quer dizer "do MEU estado". A PM de Sao Paulo e
    estadual tambem, e continua sendo longe."""
    resultado = classificar(
        ItemColetado(
            titulo="Policia Militar de Sao Paulo (SP) tem concurso autorizado",
            url="https://exemplo.test/pmsp",
            uf="SP",
        )
    )
    assert resultado.relevancia != "estadual"


def test_municipio_conhecido_ainda_manda_no_orgao_estadual():
    """Se a pagina do edital ja disse a lotacao, isso e fato e vence a regra
    do orgao - que e so a ausencia de municipio."""
    resultado = classificar(
        ItemColetado(
            titulo="Secretaria de Estado da Saude abre vagas",
            url="https://exemplo.test/ses",
            uf="SC",
            municipio="Florianopolis",
        )
    )
    assert resultado.relevancia == "nucleo"


def test_autarquia_de_sc_continua_indefinida():
    """A lista de orgaos e curta de proposito: Celesc e estatal, nao
    secretaria. Incluir por semelhanca seria o chute de sempre."""
    resultado = classificar(
        ItemColetado(titulo="2026 – Celesc Distribuição S.A",
                     url="https://exemplo.test/celesc", uf="SC",
                     tipo="concurso")
    )
    assert resultado.relevancia == "indefinida"


def test_orgao_estadual_sem_uf_nenhuma_continua_indefinida():
    """Sem a UF nao da para saber de que estado e a secretaria. Quem sabe e a
    fonte, e e la que a UF e preenchida."""
    resultado = classificar(
        ItemColetado(titulo="Secretaria de Estado da Fazenda abre concurso",
                     url="https://exemplo.test/sef")
    )
    assert resultado.relevancia == "indefinida"


# --- orgao estadual reconhecido pela SIGLA ----------------------------------
# Cada fonte titula de um jeito: a FEPESE escreve o nome por extenso
# ("Secretaria de Estado da Administracao Prisional"), e o agregador escreve a
# sigla ("SEJURI SC divulga novo edital"). Sigla nenhuma casa com "secretaria
# de estado", entao os dois concursos da SEJURI ficavam em `indefinida` mesmo
# tendo uf=SC - justamente o orgao do meu alvo principal.

def test_sigla_da_secretaria_do_alvo_e_orgao_estadual():
    """Os titulos sao REAIS, do agregador."""
    for titulo in (
        "SEJURI SC divulga novo edital com vaga para Medico e inicial de R$ 15 mil",
        "SEJURI (SC) publica edital de selecao com salario de R$ 8,7 mil",
    ):
        assert classificar(item(titulo, uf="SC")).relevancia == "estadual", titulo


def test_o_nome_por_extenso_continua_valendo():
    """A lista do codigo nao foi trocada pela do YAML: as duas somam."""
    titulo = ("2019 - Secretaria de Estado da Administracao Prisional - "
              "Concurso Publico - Edital 001/2019")
    assert classificar(item(titulo, uf="SC")).relevancia == "estadual"


def test_sigla_de_secretaria_parecida_nao_vira_estadual():
    """SAPE/SC e a Secretaria da Agricultura, e "SAP" esta no alvo.yml. A
    comparacao e por palavra inteira justamente para nao confundir as duas."""
    titulo = "Concurso SAPE SC tem edital publicado para 20 vagas"
    assert classificar(item(titulo, uf="SC")).relevancia != "estadual"


def test_a_sigla_do_alvo_fora_de_sc_nao_vira_estadual_de_sc():
    """Sao Paulo tem uma secretaria SAP. Sem uf=SC, a regra nao se aplica."""
    titulo = "Concurso SAP SP abre vagas para Agente de Seguranca"
    assert classificar(item(titulo, uf="SP")).relevancia != "estadual"
