"""Fonte 4: o Diario Oficial do Estado de SC, pela busca da propria tela.

A fixture (`fixtures/doe_sc/`) e um recorte das respostas reais de 11/10/2026:
a busca com os atos que importam - os que entram e os que tem de ficar de
fora - e o comeco do texto integral de cada um. Os trechos foram encurtados e
nenhum traz nome de candidato.
"""
import json
from datetime import date
from pathlib import Path

import pytest
import requests

from radar.collectors import doe_sc
from radar.collectors.base import ColetorBloqueadoPeloRobots

PASTA = Path(__file__).parent / "fixtures" / "doe_sc"


# --- o que o ato e ----------------------------------------------------------
#
# Os textos abaixo sao o comeco de atos reais do DOE.

CONTRATO_PM = (
    "POLÍCIA MILITAR - EXTRATO CONTRATO CONTRATO 098/PMSC/2026. Origem: Dispensa "
    "de Licitação 059/PMSC/2026. Contratante: Polícia Militar de Santa Catarina. "
    "Contratada: Instituto AOCP. Objeto do Contrato: contratação de banca "
    "organizadora especializada para o planejamento, organização, execução e "
    "operacionalização do concurso público destinado ao ingresso no Curso de "
    "Formação de Praças (CFP)."
)
RESULTADO_DA_DISPENSA_PM = (
    "POLÍCIA MILITAR DO ESTADO DE SANTA CATARINA EXTRATO DO RESULTADO A Diretoria "
    "de Apoio Logistico e Finanças comunica o resultado da Dispensa Licitação nº "
    "0059/2026. Objeto: Contratação de banca organizadora especializada para o "
    "planejamento, organização, execução e operacionalização do concurso público "
    "destinado ao ingresso no Curso de Formação de Praças (CFP) da PMSC. "
    "Item(ns): 1 - INSTITUTO AOCP, Valor Adjudicado: R$ 1.390.000,00."
)
# O contrato de 2025 da PM com o Idecan era de processo seletivo, e nao de
# concurso: nao pode virar "banca definida" da carreira.
CONTRATO_DE_SELETIVO = (
    "POLÍCIA MILITAR – EXTRATO CONTRATO CONTRATO 276 /PMSC/2025 . Origem : Dispensa "
    "de Licitação 211/PMSC/2025. Contratante : Polícia Militar de Santa Catarina. "
    "Contratada Instituto de Desenvolvimento Educacional, Cultural e Assistencial "
    "Nacional - IDECAN. Objeto do Contrato : Contratação dos serviços de "
    "planejamento, administração e operacionalização de processo seletivo "
    "simplificado para o Serviço Militar Temporário da Polícia Militar de Santa Catarina."
)
SANCAO = (
    "CORPO DE BOMBEIROS MILITAR APLICAÇÃO DE SANÇÃO Decisão: O Diretor de Logística "
    "e Finanças [...] der causa à execução parcial contrato nº 0327/2025/CBMSC [...] "
    "RESOLVE aplicar à empresa INSTITUTO DE DESENVOLVIMENTO INSTITUCIONAL BRASILEIRO "
    "– IDIB, CNPJ n° 22.513.518/0001-61, a penalidade de ADVERTÊNCIA [...] do "
    "Contrato nº 0327/2025/CMSC – Dispensa de Licitação nº 43/2025 [...] concurso"
)
COMISSAO = (
    "PORTARIA Nº 71/2026/CBMSC, de 04/02/2026. Constituir a Comissão de Concurso "
    "Público do Corpo de Bombeiros Militar de Santa Catarina (CBMSC)."
)
COORDENADORES = (
    "PORTARIA Nº 74/2026/CBMSC, de 05/ 02/ 2026. Designa Bombeiros Militares para "
    "atuarem como Coordenadores Técnicos e membros da Comissão de Avaliação de "
    "Recursos do Teste de Aptidão Física (TAF) do Concurso Público para o Curso de "
    "Formação de Oficiais (CFO) [...] O PRESIDENTE DA COMISSÃO DE CONCURSO PÚBLICO "
    "DO CORPO DE BOMBEIROS MILITAR DO ESTADO DE SANTA CATARINA"
)
EDITAL_PC = (
    "EDITAL DE CONCURSO PÚBLICO N. 01/2025 ABERTURA DE CONCURSO PÚBLICO PARA "
    "PROVIMENTO DE VAGAS NA CARREIRA DE AGENTE DE POLÍCIA CIVIL O DELEGADO-GERAL DA "
    "POLÍCIA CIVIL DO ESTADO DE SANTA CATARINA, no uso de suas atribuições"
)
RETIFICACAO_PC = (
    "Edital nº 01/2025 (3ª Retificação) O DELEGADO GERAL DA POLÍCIA CIVIL DO ESTADO "
    "DE SANTA CATARINA , no uso de suas atribuições legais, torna pública a "
    "retificação do Edital de Concurso Público"
)
# A errata diz que e errata depois de quase 200 letras de orgao e de curso.
ERRATA_CBMSC = (
    "GOVERNO DO ESTADO DE SANTA CATARINA CORPO DE BOMBEIROS MILITAR DO ESTADO DE "
    "SANTA CATARINA CONCURSO PÚBLICO PARA O PREENCHIMENTO DE VAGAS NO CURSO DE "
    "FORMAÇÃO DE OFICIAIS EDITAL 002-2026/DP/CBMSC - CFO ERRATA Nº 1"
)
NOMEACAO = (
    "PORTARIA Nº 08/PMSC/2026, de 08/01/2026. INCLUO no serviço ativo da Polícia "
    "Militar do Estado de Santa Catarina, como Cadete, os candidatos partícipe do "
    "Edital de Concurso Público"
)


@pytest.mark.parametrize("texto,assunto,ato", [
    (CONTRATO_PM, "CONTRATOS", doe_sc.CONTRATO),
    (RESULTADO_DA_DISPENSA_PM, "LICITAÇÃO", doe_sc.CONTRATO),
    (COMISSAO, "PORTARIA DE RESOLVE", doe_sc.COMISSAO),
    (EDITAL_PC, "EDITAL", doe_sc.EDITAL),
    (RETIFICACAO_PC, "EDITAL", doe_sc.RETIFICACAO),
    (ERRATA_CBMSC, "ERRATA", doe_sc.RETIFICACAO),
])
def test_o_ato_que_entra(texto, assunto, ato):
    assert doe_sc.que_ato_e(texto, assunto) == ato


@pytest.mark.parametrize("texto,assunto", [
    (CONTRATO_DE_SELETIVO, "CONTRATOS"),     # processo seletivo, nao concurso
    (SANCAO, "CONTRATOS"),                   # fala do contrato para punir
    (COORDENADORES, "PORTARIA DE RESOLVE"),  # quem assina e o presidente dela
    (NOMEACAO, "PORTARIA DE ADMISSÃO"),      # quem ja passou
])
def test_o_ato_que_fica_de_fora(texto, assunto):
    assert doe_sc.que_ato_e(texto, assunto) is None


def test_a_autorizacao_pede_a_realizacao_ou_a_abertura():
    """Exemplos escritos para o teste (o DOE de 2025-26 nao teve autorizacao
    de concurso das forcas): autorizar a nomear aprovado nao e autorizar o
    concurso."""
    assert doe_sc.que_ato_e(
        "Fica autorizada a realização de concurso público para o cargo de Policial Penal"
    ) == doe_sc.AUTORIZACAO
    assert doe_sc.que_ato_e(
        "autoriza a CIDASC a contratar 2 candidatos aprovados no concurso público"
    ) is None


# --- a banca, como o ato escreve -------------------------------------------

@pytest.mark.parametrize("texto,banca", [
    (CONTRATO_PM, "Instituto AOCP"),
    (RESULTADO_DA_DISPENSA_PM, "INSTITUTO AOCP"),
    # sem os dois-pontos, e o nome por extenso com a sigla no fim
    ("Contratada Instituto de Desenvolvimento Educacional, Cultural e Assistencial "
     "Nacional - IDECAN. Objeto do Contrato",
     "Instituto de Desenvolvimento Educacional, Cultural e Assistencial Nacional - IDECAN"),
    # para no CNPJ
    ("Contratada:  FUNDACAO DE ESTUDOS  E  PESQUISAS  SOCIO  ECONOMICAS  (FEPESE),  "
     "CNPJ  83.566.299/0001-73.",
     "FUNDACAO DE ESTUDOS E PESQUISAS SOCIO ECONOMICAS (FEPESE)"),
])
def test_a_banca_sai_como_o_ato_escreve(texto, banca):
    assert doe_sc.banca_do_ato(texto) == banca


def test_sem_contratada_nao_ha_banca():
    assert doe_sc.banca_do_ato(EDITAL_PC) is None


# --- o titulo ----------------------------------------------------------------

def test_o_titulo_junta_o_cabecalho_ate_o_nome_do_ato():
    paragrafos = ["CORPO DE BOMBEIROS MILITAR", "EXTRATO DE CONTRATO",
                  "Termo de Contrato nº 0327/2025/CBMSC . Processo : Dispensa de "
                  "Licitação nº 43/2025/CBMSC. Contratante : CORPO DE BOMBEIROS "
                  "MILITAR DE SANTA CATARINA. Contratada : INSTITUTO DE DESENVOLVIMENTO"]
    assert doe_sc.titulo_do_ato(paragrafos) == (
        "CORPO DE BOMBEIROS MILITAR - EXTRATO DE CONTRATO - "
        "Termo de Contrato nº 0327/2025/CBMSC"
    )


def test_o_titulo_do_extrato_de_um_paragrafo_so_e_a_primeira_frase():
    assert doe_sc.titulo_do_ato([CONTRATO_PM]) == (
        "POLÍCIA MILITAR - EXTRATO CONTRATO CONTRATO 098/PMSC/2026"
    )


def test_o_titulo_da_portaria_leva_a_ementa():
    paragrafos = ["PORTARIA Nº 71/2026/CBMSC, de 04/02/2026.",
                  "Constituir a Comissão de Concurso Público do Corpo de Bombeiros "
                  "Militar de Santa Catarina (CBMSC).",
                  "O COMANDANTE-GERAL DO CORPO DE BOMBEIROS MILITAR"]
    assert doe_sc.titulo_do_ato(paragrafos) == (
        "PORTARIA Nº 71/2026/CBMSC, de 04/02/2026 - Constituir a Comissão de "
        "Concurso Público do Corpo de Bombeiros Militar de Santa Catarina (CBMSC)"
    )


def test_o_titulo_pula_o_governo_do_estado_e_pega_a_errata():
    paragrafos = ["GOVERNO DO ESTADO DE SANTA CATARINA",
                  "CORPO DE BOMBEIROS MILITAR DO ESTADO DE SANTA CATARINA",
                  "CONCURSO PÚBLICO PARA O PREENCHIMENTO DE VAGAS NO CURSO DE "
                  "FORMAÇÃO DE OFICIAIS",
                  "EDITAL 002-2026/DP/CBMSC - CFO",
                  "ERRATA Nº 1",
                  "O COMANDANTE-GERAL"]
    titulo = doe_sc.titulo_do_ato(paragrafos)
    assert titulo.startswith("CORPO DE BOMBEIROS MILITAR DO ESTADO")
    assert titulo.endswith("EDITAL 002-2026/DP/CBMSC - CFO - ERRATA Nº 1")


# --- a data -----------------------------------------------------------------

def test_a_data_e_o_dia_da_edicao_e_nao_a_vespera():
    """O portal manda a data com hora zero em UTC. Lida como UTC, o ato de
    02/07 viraria 21h de 01/07 aqui."""
    data = doe_sc._data("2026-07-02T00:00:00.000Z")
    assert (data.year, data.month, data.day, data.hour) == (2026, 7, 2, 0)


def test_data_estranha_vira_nada():
    assert doe_sc._data("ontem") is None
    assert doe_sc._data(None) is None


# --- o POST da base (existe por causa desta fonte) --------------------------

class _RespostaPost:
    status_code = 200
    is_redirect = False
    encoding = "utf-8"
    headers: dict = {}
    content = b"{}"

    def raise_for_status(self):
        pass

    def json(self):
        return {}


def test_o_post_respeita_o_robots(monkeypatch):
    coletor = doe_sc.DoeSc()
    monkeypatch.setattr(coletor, "_robots_permite", lambda url: False)
    with pytest.raises(ColetorBloqueadoPeloRobots):
        coletor.post(doe_sc.API, {})


def test_o_post_manda_json_e_nao_segue_redirecionamento(monkeypatch):
    coletor = doe_sc.DoeSc()
    monkeypatch.setattr(coletor, "_robots_permite", lambda url: True)
    monkeypatch.setattr("radar.config.ATRASO_ENTRE_REQUISICOES", 0)
    pedidos = []

    def post_falso(url, **kwargs):
        pedidos.append((url, kwargs))
        return _RespostaPost()

    monkeypatch.setattr(coletor.http, "post", post_falso)
    coletor.post(doe_sc.API, {"busca": "x"})

    url, kwargs = pedidos[0]
    assert kwargs["json"] == {"busca": "x"}
    assert kwargs["allow_redirects"] is False


def test_o_post_redirecionado_e_erro(monkeypatch):
    coletor = doe_sc.DoeSc()
    monkeypatch.setattr(coletor, "_robots_permite", lambda url: True)
    monkeypatch.setattr("radar.config.ATRASO_ENTRE_REQUISICOES", 0)

    class _Redirecionada(_RespostaPost):
        status_code = 302
        is_redirect = True
        headers = {"Location": "https://outro.test/"}

    monkeypatch.setattr(coletor.http, "post", lambda url, **k: _Redirecionada())
    with pytest.raises(requests.HTTPError):
        coletor.post(doe_sc.API, {})


# --- a coleta, com a fixture -------------------------------------------------

class _Resposta:
    def __init__(self, texto: str):
        self.text = texto

    def json(self):
        return json.loads(self.text)


def _cd(url: str) -> str:
    """O codigo do ato no endereco do texto integral (.../Materias/<cd>/<cd>_final.html)."""
    return url.rstrip("/").split("/")[-2]


@pytest.fixture
def coletor(monkeypatch):
    """Um DoeSc que le a fixture em vez de ir a internet."""
    busca = (PASTA / "busca.json").read_text(encoding="utf-8")
    pedidos = {"post": [], "get": []}

    def post_falso(self, url, corpo):
        pedidos["post"].append(corpo)
        return _Resposta(busca)

    def get_falso(self, url):
        pedidos["get"].append(_cd(url))
        arquivo = PASTA / f"{_cd(url)}.html"
        if not arquivo.exists():
            raise requests.ConnectionError(url)
        return _Resposta(arquivo.read_text(encoding="utf-8"))

    monkeypatch.setattr(doe_sc.DoeSc, "post", post_falso)
    monkeypatch.setattr(doe_sc.DoeSc, "get", get_falso)
    c = doe_sc.DoeSc(hoje=date(2026, 10, 11))
    c.pedidos = pedidos
    return c


def _por_codigo(itens) -> dict:
    return {i.extra["cd_materia"]: i for i in itens}


def test_entram_o_contrato_a_dispensa_a_comissao_e_o_edital(coletor):
    assert set(_por_codigo(coletor.coletar())) == {
        1203313, 1190736, 1155941, 1143884, 1149079,
    }


def test_os_campos_do_contrato_da_banca(coletor):
    item = _por_codigo(coletor.coletar())[1203313]

    assert item.titulo == "2026 - POLÍCIA MILITAR - EXTRATO CONTRATO CONTRATO 098/PMSC/2026"
    assert item.url == "https://portal.doe.sea.sc.gov.br/#/portal/edicao/4580/materia/1203313"
    assert item.situacao == "banca_definida"
    assert item.banca == "Instituto AOCP"
    assert item.uf == "SC"
    assert item.municipio is None
    assert item.tipo == "concurso"
    assert (item.publicado_em.year, item.publicado_em.month, item.publicado_em.day) == (2026, 7, 2)
    assert item.extra["ato"] == "contrato"
    assert item.extra["categoria"] == "Secretarias de Estado"
    assert item.extra["texto_integral"].endswith("/1203313/1203313_final.html")
    assert item.resumo is None


def test_o_texto_juridico_nao_vira_fase_no_classificador(coletor):
    """O edital da Policia Cientifica tem "previsto" no comeco do texto; com o
    texto no resumo, o classificador o marcava como concurso previsto. A
    situacao do ato e a que o coletor diz."""
    from dataclasses import replace

    from radar.classificador import classificar

    itens = _por_codigo(coletor.coletar())
    for item in itens.values():
        resultado = classificar(item)
        assert resultado.fase in (None, item.situacao), item.titulo
        assert resultado.alvo, item.titulo        # o titulo basta para o alvo

    # E o defeito que a falta do resumo evita, com o texto real do ato:
    pagina = (PASTA / "1149079.html").read_text(encoding="utf-8")
    texto = " ".join(doe_sc._paragrafos(pagina))[:700]
    assert classificar(replace(itens[1149079], resumo=texto)).fase == "prevista"


def test_o_resultado_da_dispensa_ja_define_a_banca(coletor):
    """Saiu em 27/05, um mes antes do contrato."""
    item = _por_codigo(coletor.coletar())[1190736]
    assert item.situacao == "banca_definida"
    assert item.banca == "INSTITUTO AOCP"
    assert item.titulo == "2026 - POLÍCIA MILITAR DO ESTADO DE SANTA CATARINA - EXTRATO DO RESULTADO"


def test_a_situacao_de_cada_ato():
    """Decisao 162: o edital de abertura e fato; a correcao e a comissao nao
    dizem a fase."""
    assert doe_sc.SITUACAO_DO_ATO[doe_sc.EDITAL] == "edital_publicado"
    assert doe_sc.SITUACAO_DO_ATO[doe_sc.RETIFICACAO] == "desconhecida"
    assert doe_sc.SITUACAO_DO_ATO[doe_sc.COMISSAO] == "desconhecida"


def test_o_edital_de_abertura_e_publicado_e_a_comissao_nao_diz_a_fase(coletor):
    itens = _por_codigo(coletor.coletar())

    edital = itens[1143884]
    assert edital.situacao == "edital_publicado"
    assert edital.banca is None
    assert itens[1149079].situacao == "edital_publicado"    # "Abrem-se inscricoes"
    assert edital.titulo == (
        "2025 - EDITAL DE CONCURSO PÚBLICO N. 01/2025 - ABERTURA DE CONCURSO PÚBLICO "
        "PARA PROVIMENTO DE VAGAS NA CARREIRA DE AGENTE DE POLÍCIA CIVIL"
    )

    comissao = itens[1155941]
    assert comissao.extra["ato"] == "comissao"
    assert comissao.situacao == "desconhecida"


def test_todo_ato_e_de_sc_e_o_de_fora_do_alvo_nao_entra(coletor):
    """No diario do estado nao ha item de outro estado: o que fica de fora e o
    orgao que nao e do alvo - a CIDASC tambem contratou banca de concurso."""
    itens = coletor.coletar()
    assert {i.uf for i in itens} == {"SC"}
    assert 1140801 not in _por_codigo(itens)


def test_so_busca_o_texto_de_quem_passou_na_peneira(coletor):
    coletor.coletar()
    buscados = set(coletor.pedidos["get"])
    # nomeacao, coordenadores, seletivo da PM, CIDASC: o trecho ja basta
    for cd in ("1148986", "1156332", "1139959", "1140801"):
        assert cd not in buscados
    assert "1203313" in buscados


def test_pede_a_janela_e_a_busca_de_sempre(coletor):
    coletor.coletar()
    pedidos = coletor.pedidos["post"]

    assert len(pedidos) == len(doe_sc.CONSULTAS)
    for corpo in pedidos:
        assert corpo["dtIni"] == "2026-10-01"
        assert corpo["dtFim"] == "2026-10-11"
        assert corpo["busca"] == "concurso público"
        assert corpo["tipoBusca"] == "1"
        assert corpo["resumo"] is False      # true devolve resumo de maquina


def test_pagina_vazia(monkeypatch):
    pedidos = []

    def post_vazio(self, url, corpo):
        pedidos.append(corpo)
        return _Resposta('{"total": 0, "materias": []}')

    monkeypatch.setattr(doe_sc.DoeSc, "post", post_vazio)
    assert doe_sc.DoeSc(hoje=date(2026, 10, 11)).coletar() == []
    assert len(pedidos) == len(doe_sc.CONSULTAS)


def test_a_pagina_curta_nao_encerra_quando_o_total_diz_que_ha_mais(monkeypatch):
    """A API junta os acertos do mesmo ato: 100 acertos podem vir como 28
    atos. Quem diz se acabou e o total."""
    inicios = []

    def post_paginado(self, url, corpo):
        inicios.append(corpo["pagination"]["from"])
        return _Resposta(json.dumps({"total": 250, "materias": [{"cdMateria": len(inicios)}]}))

    monkeypatch.setattr(doe_sc.DoeSc, "post", post_paginado)
    monkeypatch.setattr(doe_sc, "CONSULTAS", ({"aCdAssunto": [63]},))
    doe_sc.DoeSc(hoje=date(2026, 10, 11)).coletar()

    assert inicios == [0, 100, 200]


def test_fonte_fora_do_ar_sobe_o_erro(monkeypatch):
    """Quem registra a fonte que caiu e o coletar_tudo; o coletor so nao pode
    engolir o erro e devolver lista vazia, como se nao houvesse ato."""
    def post_fora(self, url, corpo):
        raise requests.ConnectionError("portal fora do ar")

    monkeypatch.setattr(doe_sc.DoeSc, "post", post_fora)
    with pytest.raises(requests.ConnectionError):
        doe_sc.DoeSc(hoje=date(2026, 10, 11)).coletar()


def test_resposta_com_erro_e_falha_da_fonte(monkeypatch):
    monkeypatch.setattr(doe_sc.DoeSc, "post",
                        lambda self, url, corpo: _Resposta('{"error": "timeout"}'))
    with pytest.raises(RuntimeError):
        doe_sc.DoeSc(hoje=date(2026, 10, 11)).coletar()


def test_sem_o_texto_integral_o_trecho_segura_o_ato(coletor, monkeypatch):
    def get_fora(self, url):
        raise requests.ConnectionError(url)

    monkeypatch.setattr(doe_sc.DoeSc, "get", get_fora)
    item = _por_codigo(coletor.coletar())[1203313]

    assert item.banca == "Instituto AOCP"
    assert item.titulo == "2026 - POLÍCIA MILITAR - EXTRATO CONTRATO CONTRATO 098/PMSC/2026"


def test_o_edital_escaneado_decide_pelo_comeco_do_trecho(coletor):
    """O edital da Saude de 10/2025 e so imagem; o trecho dele e o OCR, e o
    "delegado de policia" esta num requisito la do fim. Nao e do alvo."""
    assert 1124522 not in _por_codigo(coletor.coletar())


# --- o lugar dela no radar ----------------------------------------------------

def test_esta_entre_os_coletores():
    from radar.servico.coleta import COLETORES
    assert doe_sc.DoeSc in COLETORES


def test_a_carga_inicial_traz_o_ano_e_nao_enche_a_fila_de_avisos(
    banco_temporario, coletor, monkeypatch
):
    from sqlalchemy import select

    from radar import servico
    from radar.db import sessao
    from radar.models import Concurso

    janelas = []
    original = doe_sc.DoeSc.__init__

    def init_espiao(self, dias=doe_sc.JANELA_EM_DIAS, hoje=None):
        janelas.append(dias)
        original(self, dias=dias, hoje=date(2026, 10, 11))

    monkeypatch.setattr(doe_sc.DoeSc, "__init__", init_espiao)
    resultado = servico.carga_inicial(dias=365, fonte="doe_sc")

    assert janelas == [365]
    assert resultado.erro is None and resultado.novos == 5
    with sessao() as s:
        do_doe = list(s.scalars(select(Concurso).where(Concurso.fonte == "doe_sc")))
    assert len(do_doe) == 5
    assert all(c.avisado_em is not None for c in do_doe)


def test_refazer_a_carga_nao_avisa_a_fase_que_mudou(banco_temporario, coletor, monkeypatch):
    """O edital da PC SC entrou em 11/10 como "desconhecida"; refeita a carga,
    vira "edital publicado". O evento da mudanca e de hoje, mas o edital e de
    dezembro: nao pode ir para o Telegram das carreiras (decisao 162)."""
    from sqlalchemy import select

    from radar import servico
    from radar.collectors.base import ItemColetado
    from radar import eventos as linha_do_tempo
    from radar.db import sessao
    from radar.models import Evento

    url = "https://portal.doe.sea.sc.gov.br/#/portal/edicao/4379/materia/1143884"
    with sessao() as s:
        servico._gravar(s, ItemColetado(
            titulo="2025 - EDITAL DE CONCURSO PÚBLICO N. 01/2025 - AGENTE DE POLÍCIA CIVIL",
            url=url, uf="SC", tipo="concurso", situacao="desconhecida",
        ), fonte="doe_sc")

    original = doe_sc.DoeSc.__init__
    monkeypatch.setattr(doe_sc.DoeSc, "__init__",
                        lambda self, dias=10, hoje=None: original(self, dias, date(2026, 10, 11)))
    servico.carga_inicial(dias=365, fonte="doe_sc")

    with sessao() as s:
        eventos = list(s.scalars(select(Evento).where(Evento.concurso_url == url)))
    publicou = [e for e in eventos if e.tipo == linha_do_tempo.EDITAL_PUBLICADO]
    assert publicou, [e.tipo for e in eventos]
    assert all(e.avisado_em is not None for e in eventos)


def test_a_carga_so_marca_como_avisado_o_que_e_dela(banco_temporario, coletor, monkeypatch):
    """O concurso de outra fonte que ainda espera aviso continua esperando."""
    from radar import servico
    from radar.collectors.base import ItemColetado
    from radar.db import sessao
    from radar.models import Concurso

    with sessao() as s:
        servico._gravar(s, ItemColetado(
            titulo="2026 - Prefeitura Municipal de Palhoca",
            url="https://fepese.org.br/concurso/palhoca-2026/", banca="FEPESE",
        ), fonte="fepese")

    original = doe_sc.DoeSc.__init__
    monkeypatch.setattr(doe_sc.DoeSc, "__init__",
                        lambda self, dias=10, hoje=None: original(self, dias, date(2026, 10, 11)))
    servico.carga_inicial(dias=365, fonte="doe_sc")

    with sessao() as s:
        palhoca = s.query(Concurso).filter_by(fonte="fepese").one()
        assert palhoca.avisado_em is None


def test_carga_inicial_de_fonte_que_nao_tem():
    from radar import servico
    with pytest.raises(ValueError):
        servico.carga_inicial(dias=30, fonte="fepese")


def test_a_linha_de_comando_recusa_fonte_sem_carga():
    from typer.testing import CliRunner

    from radar import cli

    resultado = CliRunner().invoke(cli.app, ["carga-inicial", "--fonte", "fepese", "--sim"])
    assert resultado.exit_code == 1
    assert "doe_sc" in resultado.output
