"""O link para o texto oficial da lei, de config/leis.yml.

Os assuntos usados aqui sao os do conteudo programatico REAL do edital
001/SAP/2019, copiados como o PDF os escreve - com "n.o", com parentese e com
a frase inteira. E o que o `radar assuntos --so-alvo` grava na coluna, e e
sobre esse texto que o casamento tem que funcionar.

Nenhum teste vai a internet: que cada endereco abre de verdade foi conferido
uma vez, na mao, antes de o YAML ser gravado. O que estes testes guardam e
outra coisa - que o link certo chega no assunto certo, e que nao aparece link
onde nao ha lei.
"""
from urllib.parse import urlparse

import pytest

from radar import leis

# As duas unicas fontes que este projeto aceita: quem publica lei federal e a
# Constituicao, e quem publica lei estadual de Santa Catarina.
FONTES = ("www.planalto.gov.br", "leis.alesc.sc.gov.br")


@pytest.fixture(autouse=True)
def yaml_de_verdade():
    """O config/leis.yml do projeto, e nao um de mentira: o conteudo dele E o
    que estes testes conferem."""
    leis.recarregar()
    yield
    leis.recarregar()


# --- o casamento ------------------------------------------------------------

def test_a_lei_de_execucao_penal_chega_pelo_nome_da_materia():
    lei = leis.do_assunto(
        "Lei de Execução Penal",
        "Lei de Execução Penal (Lei nº 7.210 de 11 de julho de 1984)",
    )

    assert lei is not None
    assert "7.210" in lei.titulo
    assert lei.url.endswith("/l7210.htm")


def test_lei_estadual_vai_para_a_alesc_e_nao_para_o_planalto():
    """Lei de SC nao esta no Planalto, e esta e a materia que faz esta prova
    ser so de quem presta em Santa Catarina."""
    lei = leis.do_assunto(
        "Legislação Estadual",
        "Lei n.º 6.745, de 28 de dezembro de 1985 "
        "(Estatuto do Servidor do Estado de Santa Catarina)",
    )

    assert urlparse(lei.url).netloc == "leis.alesc.sc.gov.br"


def test_cada_lei_avulsa_da_legislacao_especial_tem_a_sua():
    """Cinco leis diferentes na mesma materia: nenhuma pode cair na do vizinho."""
    def url(assunto: str) -> str:
        return leis.do_assunto("Legislação Especial", assunto).url

    desarmamento = url("Estatuto do Desarmamento (Lei nº 10.826 de 22 de dezembro de 2003)")
    tortura = url("Crimes de tortura (Lei nº 9.455 de 7 de abril de 1997)")
    drogas = url("Lei nº 11.343, de 23 de agosto de 2006 (SISNAD)")
    penha = url("Lei dos Crimes contra Violência Doméstica ou "
                "“Lei Maria da Penha” (Lei nº 11.340/2006)")

    assert "10.826" in desarmamento
    assert "9455" in tortura
    assert "11343" in drogas
    assert "11340" in penha
    assert len({desarmamento, tortura, drogas, penha}) == 4


def test_assunto_sem_lei_propria_cai_na_lei_da_materia():
    """"Crimes contra a Administracao Publica" nao e uma lei: e um titulo do
    Codigo Penal, que e o link da materia inteira."""
    lei = leis.do_assunto("Direito Penal", "Crimes contra a Administração Pública")

    assert "del2848" in lei.url


def test_todo_assunto_de_direito_constitucional_vai_para_a_constituicao():
    for assunto in ("nacionalidade", "direitos sociais",
                    "Ordem social: base e objetivos da ordem social"):
        assert "constituicao" in leis.do_assunto("Direito Constitucional", assunto).url


def test_acento_e_caixa_nao_atrapalham():
    com = leis.do_assunto("Legislação Especial", "Crimes de tortura (Lei nº 9.455)")
    sem = leis.do_assunto("LEGISLACAO ESPECIAL", "CRIMES DE TORTURA (LEI 9.455)")

    assert com == sem is not None


# --- o que ela se recusa a fazer --------------------------------------------

def test_documento_da_onu_fica_sem_link():
    """As Regras de Mandela nao sao lei brasileira: nao estao no Planalto nem
    na ALESC, e apontar para qualquer outro lugar seria inventar a fonte."""
    assert leis.do_assunto(
        "Direitos Humanos",
        "Regras mínimas da ONU para o tratamento de pessoas presas",
    ) is None


def test_assunto_de_doutrina_fica_sem_link():
    """Teoria geral nao tem texto oficial para abrir."""
    assert leis.do_assunto(
        "Direitos Humanos", "Afirmação histórica dos direitos humanos"
    ) is None


def test_materia_que_nao_e_de_direito_nao_tem_lei():
    assert leis.do_assunto("Língua Portuguesa", "Emprego da crase") is None
    assert leis.da_materia("Raciocínio Lógico") is None


def test_materia_desconhecida_nao_quebra():
    assert leis.do_assunto("Materia que nao existe", "qualquer coisa") is None
    assert leis.do_assunto(None, None) is None


def test_yaml_ausente_vira_lista_vazia_e_nao_erro(tmp_path, monkeypatch):
    monkeypatch.setenv("RADAR_CONFIG_DIR", str(tmp_path))
    leis.recarregar()

    assert leis.do_assunto("Direito Penal", "Imputabilidade penal") is None


# --- as ressalvas -----------------------------------------------------------

def test_a_lei_revogada_vem_com_a_ressalva_junto():
    """O edital de 2019 cobra a Lei 4.898, revogada naquele mesmo ano. O link
    e o que o edital pede, e a nota existe para eu nao estudar uma lei
    revogada sem saber."""
    lei = leis.do_assunto(
        "Legislação Especial",
        "Lei de Abuso de autoridade (Lei nº 4.898 de 9 de dezembro de 1965)",
    )

    assert "4.898" in lei.titulo
    assert "13.869" in lei.nota


def test_lei_sem_ressalva_nao_inventa_uma():
    lei = leis.do_assunto("Direito Processual Penal", "Ação penal")

    assert lei.nota is None


# --- as duas fontes ---------------------------------------------------------

def test_so_existem_planalto_e_alesc_no_arquivo():
    """A regra do arquivo, guardada por teste: lei federal e Constituicao no
    Planalto, lei estadual de SC na ALESC, e nada alem disso. Um link para um
    site de resumo de lei entraria sem ninguem perceber."""
    enderecos = []
    for bloco in leis._carregar():
        enderecos.extend(
            item["url"] for item in [bloco, *(bloco.get("assuntos") or [])]
            if item.get("url")
        )

    assert enderecos
    for endereco in enderecos:
        assert urlparse(endereco).scheme == "https"
        assert urlparse(endereco).netloc in FONTES, endereco
