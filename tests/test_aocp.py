"""Fonte 5: o Instituto AOCP, pela API da propria pagina de concursos.

A fixture (`fixtures/aocp/`) e um recorte das respostas reais de 11/10/2026:
a lista de cada status com os concursos que cobrem os casos - inscricao
aberta, edital novo, em andamento de SC, o seletivo da SAP/SC, a Policia
Penal do Parana, a data com erro do CBMGO e o registro de teste - e o detalhe
de cada um, so com as publicacoes mais antigas.
"""
import json
from pathlib import Path

import pytest
import requests

from radar.collectors import aocp

PASTA = Path(__file__).parent / "fixtures" / "aocp"


# --- o que o nome do orgao afirma ------------------------------------------

@pytest.mark.parametrize("nome,uf", [
    ("CASAN - COMPANHIA CATARINENSE DE ÁGUAS E SANEAMENTO - SC", "SC"),
    ("SAD/PE - SECRETARIA DE ADMINISTRAÇÃO DO ESTADO DE PERNAMBUCO", "PE"),
    ("IGP-RS - INSTITUTO-GERAL DE PERÍCIAS - RS", "RS"),
    ("PPMG - Secretaria de Estado de Justiça e Segurança Pública - SEJUSP/MG", "MG"),
    ("PPPR - POLÍCIA PENAL DO PARANÁ", "PR"),
    ("CBMERJ - CORPO DE BOMBEIROS MILITAR DO ESTADO DO RIO DE JANEIRO", "RJ"),
    ("IFPA - INSTITUTO FEDERAL DE EDUCAÇÃO, CIÊNCIA E TECNOLOGIA DO PARÁ", "PA"),
])
def test_a_uf_que_o_nome_afirma(nome, uf):
    assert aocp.extrair_uf(nome) == uf


@pytest.mark.parametrize("nome", [
    "IPSM - Instituto de Previdência do Servidor Municipal",  # de onde? nao diz
    "PREFEITURA MUNICIPAL DE CURITIBA",                       # diz a cidade
    "IRGA - INSTITUTO RIO GRANDENSE DO ARROZ",                # "rio grandense" nao e estado
])
def test_sem_uf_escrita_nao_ha_uf(nome):
    assert aocp.extrair_uf(nome) is None


def test_o_municipio_da_prefeitura():
    assert aocp.extrair_municipio("PREFEITURA MUNICIPAL DE SERRA - ES") == "SERRA"
    assert aocp.extrair_municipio("PREFEITURA MUNICIPAL DE CURITIBA") == "CURITIBA"
    assert aocp.extrair_municipio("CASAN - COMPANHIA CATARINENSE DE ÁGUAS E SANEAMENTO - SC") is None


# --- o titulo nao muda a cada etapa ----------------------------------------

@pytest.mark.parametrize("chamada,comeco", [
    ("Concurso Público nº 001/2026 - Polícia Militar de Pernambuco (PMPE) - Divulgado "
     "o Edital de Abertura.",
     "Concurso Público nº 001/2026 - Polícia Militar de Pernambuco (PMPE)"),
    ("Edital de Abertura nº 2/2025. Divulgado o Edital de Convocação para Investigação Social.",
     "Edital de Abertura nº 2/2025"),
    ("Concurso Público nº 004/2025 – Breve, divulgação do Procedimento de Heteroidenticação",
     "Concurso Público nº 004/2025"),
    ("Concurso Público nº 5/2026 - Cargos de Nível Médio, Técnico e Superior - Edital de "
     "Abertura publicado, inscrições abertas do dia 23/09 à 20/10",
     "Concurso Público nº 5/2026 - Cargos de Nível Médio, Técnico e Superior"),
    ("Concurso Público Nº 03/2026 - Corpo de Bombeiros e Polícia Militar do Estado da "
     "Bahia - Concurso suspenso, em breve novas atualizações",
     "Concurso Público Nº 03/2026 - Corpo de Bombeiros e Polícia Militar do Estado da Bahia"),
])
def test_a_identificacao_tira_o_andamento(chamada, comeco):
    assert aocp.identificacao(chamada) == comeco


def test_chamada_que_e_so_andamento_nao_identifica():
    """A do Amapa comeca em "Divulgado...": o titulo usa o tipo e o numero."""
    assert aocp.identificacao("Divulgado o Edital de deferimento das solicitações") is None


def test_o_tipo_escrito_vence_o_texto():
    assert aocp.detectar_tipo("Concurso para Emprego Público", "processo seletivo") == "concurso"
    assert aocp.detectar_tipo("Processo Seletivo Simplificado") == "seletivo"
    # vazio, como no da SAP/SC de 2024: vale o texto
    assert aocp.detectar_tipo("", "TORNA PÚBLICA a realização do PROCESSO SELETIVO") == "seletivo"
    assert aocp.detectar_tipo(None, "Concurso Público nº 01/2026") == "concurso"


def test_a_data_do_edital_e_a_publicacao_mais_antiga():
    publicacoes = [{"nome": "08/10/2026 - Comunicado"},
                   {"nome": "30/09/2026 - Concurso Público 001/2026 - Edital de Abertura"},
                   {"nome": "sem data"}]
    data = aocp.data_do_edital(publicacoes)
    assert (data.year, data.month, data.day) == (2026, 9, 30)


def test_a_data_com_erro_de_digitacao_fica_de_fora():
    """O Cadete do CBMGO (edital 004/2022) tem uma publicacao de "26/09/2002"."""
    publicacoes = [{"nome": "26/09/2002 - Anexo Único do Deferimento"},
                   {"nome": "21/07/2022 - Edital de Abertura Concurso Público nº004/2022"}]
    assert aocp.data_do_edital(publicacoes).year == 2002          # sem o ano: o erro vence
    assert aocp.data_do_edital(publicacoes, ano=2022).year == 2022


# --- a coleta, com a fixture -----------------------------------------------

class _Resposta:
    def __init__(self, texto: str):
        self.text = texto

    def json(self):
        return json.loads(self.text)


def _arquivo(url: str) -> Path:
    if "status=" in url:
        return PASTA / f"lista_{url.rsplit('=', 1)[1]}.json"
    return PASTA / f"detalhe_{url.rstrip('/').rsplit('/', 1)[1]}.json"


@pytest.fixture
def coletor(monkeypatch):
    pedidos = []

    def get_falso(self, url):
        pedidos.append(url)
        return _Resposta(_arquivo(url).read_text(encoding="utf-8"))

    monkeypatch.setattr(aocp.InstitutoAocp, "get", get_falso)
    c = aocp.InstitutoAocp()
    c.pedidos = pedidos
    return c


def _por_id(itens) -> dict:
    return {int(i.url.rsplit("/", 1)[1]): i for i in itens}


def test_traz_os_tres_status_e_descarta_o_teste(coletor):
    itens = _por_id(coletor.coletar())
    assert set(itens) == {714, 720, 723, 712, 620, 604, 418}
    assert not any("teste" in i.titulo.lower() for i in itens.values())


def test_os_campos(coletor):
    item = _por_id(coletor.coletar())[714]

    assert item.titulo == ("2026 - PMPE - POLÍCIA MILITAR DE PERNAMBUCO - Concurso Público "
                           "nº 001/2026 - Polícia Militar de Pernambuco (PMPE)")
    assert item.url == "https://www.institutoaocp.org.br/concursos/714"
    assert item.banca == "Instituto AOCP"
    assert item.uf == "PE"
    assert item.situacao == "inscricoes_abertas"
    assert item.tipo == "concurso"
    assert (item.publicado_em.year, item.publicado_em.month, item.publicado_em.day) == (2026, 9, 30)
    assert item.resumo.startswith("A Secretária de Administração")
    assert item.extra["inscricoes_ate"] == "2026-11-05 23:59:59"
    assert item.extra["edital"] == "pmpe2026"


def test_o_status_vira_a_situacao(coletor):
    itens = _por_id(coletor.coletar())
    assert itens[723].situacao == "edital_publicado"      # NEW: edital saiu, inscricao em breve
    assert itens[712].situacao == "edital_publicado"      # IN_PROGRESS


def test_o_item_de_fora_de_sc_nao_cai_no_cartao_da_pm_sc(banco_temporario, coletor):
    """A PM de Pernambuco e cargo do alvo, mas o cartao e o da PM de SC."""
    from radar import acompanhamentos as carreiras
    from radar import servico
    from radar.db import sessao
    from radar.models import Concurso

    with sessao() as s:
        for item in coletor.coletar():
            servico._gravar(s, item, fonte="aocp")
    with sessao() as s:
        pmpe = s.query(Concurso).filter_by(url="https://www.institutoaocp.org.br/concursos/714").one()
        assert pmpe.alvo == "secundario"
        assert carreiras.de_quais(pmpe) == []
        casan = s.query(Concurso).filter_by(url="https://www.institutoaocp.org.br/concursos/712").one()
        assert casan.uf == "SC"


def test_o_seletivo_da_sap_sc_nao_e_o_concurso_da_policia_penal(coletor):
    """Mesmo orgao do alvo principal; a chamada do detalhe diz "PROCESSO
    SELETIVO SIMPLIFICADO", e o alvo.yml exclui."""
    from radar.classificador import classificar

    item = _por_id(coletor.coletar())[620]
    assert item.tipo == "seletivo"
    assert item.uf == "SC"
    assert classificar(item).alvo is None


def test_a_policia_penal_de_outro_estado_tem_a_data_de_2024(coletor):
    """Sem a data, a regra do aviso a deixaria passar como novidade."""
    from radar.classificador import classificar

    item = _por_id(coletor.coletar())[604]
    assert (item.publicado_em.year, item.publicado_em.month, item.publicado_em.day) == (2024, 2, 19)
    assert classificar(item).alvo == "principal_fora"


def test_a_data_com_erro_nao_entra(coletor):
    item = _por_id(coletor.coletar())[418]
    assert item.publicado_em.year == 2022
    assert item.titulo.startswith("2022 - CBMGO")


def test_prefeitura_sem_uf_e_seletivo(coletor):
    item = _por_id(coletor.coletar())[723]
    assert item.municipio == "CURITIBA"
    assert item.uf is None
    assert item.tipo == "seletivo"


def test_pagina_vazia(monkeypatch):
    pedidos = []

    def get_vazio(self, url):
        pedidos.append(url)
        return _Resposta("[]")

    monkeypatch.setattr(aocp.InstitutoAocp, "get", get_vazio)
    assert aocp.InstitutoAocp().coletar() == []
    assert len(pedidos) == len(aocp.SITUACAO_POR_STATUS)    # nenhum detalhe


def test_fonte_fora_do_ar_sobe_o_erro(monkeypatch):
    def get_fora(self, url):
        raise requests.ConnectionError("fora do ar")

    monkeypatch.setattr(aocp.InstitutoAocp, "get", get_fora)
    with pytest.raises(requests.ConnectionError):
        aocp.InstitutoAocp().coletar()


def test_sem_o_detalhe_o_concurso_entra_sem_data(monkeypatch):
    def get_sem_detalhe(self, url):
        if "status=" not in url:
            raise requests.ConnectionError(url)
        return _Resposta(_arquivo(url).read_text(encoding="utf-8"))

    monkeypatch.setattr(aocp.InstitutoAocp, "get", get_sem_detalhe)
    item = _por_id(aocp.InstitutoAocp().coletar())[714]
    assert item.publicado_em is None
    assert item.titulo.startswith("2026 - PMPE")    # o ano vem do numero do edital


# --- o lugar dela no radar ----------------------------------------------------

def test_esta_entre_os_coletores():
    from radar.servico.coleta import COLETORES
    assert aocp.InstitutoAocp in COLETORES


def test_a_carga_inicial_liga_a_fonte_sem_aviso(banco_temporario, coletor):
    """Sem municipio, concurso de outro estado e `indefinida`, e `indefinida`
    avisa: ligar a fonte sem a carga mandaria a lista inteira."""
    from sqlalchemy import select

    from radar import servico
    from radar.db import sessao
    from radar.models import Concurso

    resultado = servico.carga_inicial(fonte="aocp")
    assert resultado.erro is None and resultado.novos == 7
    with sessao() as s:
        da_aocp = list(s.scalars(select(Concurso).where(Concurso.fonte == "aocp")))
    assert len(da_aocp) == 7 and all(c.avisado_em is not None for c in da_aocp)
