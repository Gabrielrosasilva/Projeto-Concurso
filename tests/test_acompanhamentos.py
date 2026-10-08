"""As carreiras da aba Concursos > Acompanhando (decisao 141).

O pedido de 06/10/2026: acompanhar a carreira inteira (Policia Penal SC, as
Guardas de Florianopolis e de BC, Policia Civil, PM e Bombeiros de SC) mesmo
antes de sair noticia; um 🔔 so para FATO, com data, link e selo; o botao
"Verificar atualizacoes" rodando a coleta das fontes permitidas; a pesquisa do
Claude Code para o que o robo nao ve, entrando por conferir; e o Telegram so
no critico.

Nada aqui vai a internet: a coleta do botao e uma funcao falsa, e o Telegram
guarda o que teria mandado. As datas de corte do YAML de teste ficam no
passado distante, para nenhum teste depender do dia de hoje.
"""
import json
import shutil
from pathlib import Path
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from radar import acompanhamentos as carreiras
from radar import alvo, avisos, config, servico
from radar import eventos as linha_do_tempo
from radar.db import sessao
from radar.models import Concurso, agora
from radar.origem import IA, NOTICIA, OFICIAL
from radar.servico import acompanhamentos as cartoes
from radar.web.app import app

YAML_DE_TESTE = """
intervalo_minimo_minutos: 30
janela_da_edicao_em_dias: 365
novidades_desde: '2000-01-01'
telegram_desde: '2000-01-01'
fontes_oficiais: [fepese, ieses]
dominios_oficiais: [fepese.org.br, ieses.org]
fontes_de_sc: [fepese]
prova_de_sc: [santa catarina]
acompanhamentos:
  - nome: Polícia Penal SC
    cargo: principal
  - nome: Guarda Municipal de Balneário Camboriú
    cargo: Guarda Municipal
    local: [balneario camboriu, pmbc]
    uf: SC
  - nome: Polícia Civil SC
    cargo: Policia Civil
    termos_extras: [pc sc]
    uf: SC
  - nome: Polícia Militar SC
    cargo: Policia Militar
    termos_extras: [pm sc]
    uf: SC
"""


@pytest.fixture
def ambiente(banco_temporario, tmp_path, monkeypatch):
    """O config de verdade (alvo.yml, regioes.yml), com um acompanhamentos.yml
    de teste por cima."""
    pasta = tmp_path / "config"
    shutil.copytree(config.diretorio_config(), pasta)
    (pasta / "acompanhamentos.yml").write_text(YAML_DE_TESTE, encoding="utf-8")
    monkeypatch.setenv("RADAR_CONFIG_DIR", str(pasta))
    carreiras.recarregar()
    yield pasta
    carreiras.recarregar()


def _item(url, titulo, **mudancas) -> Concurso:
    base = dict(url=url, fonte="concursosnobrasil", titulo=titulo, uf="SC",
                tipo="concurso", relevancia="indefinida", situacao="desconhecida",
                publicado_em=agora() - timedelta(days=3))
    base.update(mudancas)
    return Concurso(**base)


def _semear(*itens):
    with sessao() as s:
        for item in itens:
            s.add(item)


def _evento(url, tipo, descricao, quando=None):
    with sessao() as s:
        linha_do_tempo.registrar(s, url, tipo, descricao, url, quando)


def _cartao(nome):
    return next(c for c in cartoes.cartoes() if c.nome == nome)


# --- o YAML e a regra de quem e de qual carreira -------------------------------

def test_o_yaml_de_verdade_carrega_as_sete_carreiras(monkeypatch):
    """O arquivo que vai para o Actions: sete carreiras, todas apontando para
    um bloco que existe no alvo.yml."""
    monkeypatch.delenv("RADAR_CONFIG_DIR", raising=False)
    carreiras.recarregar()
    nomes = [a.nome for a in carreiras.todos()]
    assert nomes == [
        "Polícia Penal SC", "Guarda Municipal de Florianópolis",
        "Guarda Municipal de Balneário Camboriú", "Polícia Civil SC",
        "Polícia Militar SC", "Oficial do Corpo de Bombeiros SC", "Bombeiro Militar SC",
    ]
    carreiras.recarregar()


def test_cargo_que_nao_existe_no_alvo_para_com_erro(ambiente):
    (ambiente / "acompanhamentos.yml").write_text(
        "acompanhamentos:\n  - nome: X\n    cargo: Policia Rodoviaria\n", encoding="utf-8")
    carreiras.recarregar()
    with pytest.raises(carreiras.ErroNosAcompanhamentos, match="Policia Rodoviaria"):
        carreiras.regras()


def test_a_pm_entrou_no_alvo_sem_roubar_os_bombeiros():
    alvo.recarregar()
    assert alvo.marcar("Concurso PMSC abre vagas para Soldado da Polícia Militar").nome \
        == "Policia Militar"
    # "Corpo de Bombeiros" vem antes na lista: o titulo dos dois e dos Bombeiros.
    assert alvo.marcar("Concurso Polícia Militar e Corpo de Bombeiros de SC").nome \
        == "Bombeiro Militar"
    # "PM" sozinha e Prefeitura Municipal no titulo da FEPESE.
    assert alvo.marcar("2014 – PMBC – Edital de Professor") is None


@pytest.mark.parametrize("titulo, campos, carreira", [
    # A FEPESE escreve "PMBC" e nao manda UF: ser da FEPESE conta como SC.
    ("2014 – PMBC – Guarda Municipal – Concurso Público", dict(fonte="fepese", uf=None),
     "Guarda Municipal de Balneário Camboriú"),
    ("Concurso Guarda Municipal de Balneário Camboriú (SC) abre 50 vagas", {},
     "Guarda Municipal de Balneário Camboriú"),
    ("Concurso PC SC: edital autorizado para 600 vagas", {}, "Polícia Civil SC"),
    ("Concurso PMSC: inscrições para Soldado", {}, "Polícia Militar SC"),
])
def test_o_item_cai_no_cartao_certo(ambiente, titulo, campos, carreira):
    item = _item("https://x.test/1", titulo, **campos)
    assert [a.nome for a in carreiras.de_quais(item)] == [carreira]


@pytest.mark.parametrize("titulo, campos", [
    # Outra cidade com "Balneario" no nome.
    ("Concurso Balneário Piçarras (SC) abre vagas para Guarda Municipal", {}),
    # A carreira certa, o estado errado.
    ("Concurso Polícia Civil (AL) tem edital publicado", dict(uf="AL")),
    # Sem UF e sem nada que prove SC: nunca chutar.
    ("Concurso Polícia Civil tem edital publicado", dict(uf=None, fonte="ieses")),
])
def test_o_que_nao_e_da_carreira_fica_fora(ambiente, titulo, campos):
    assert carreiras.de_quais(_item("https://x.test/1", titulo, **campos)) == []


def test_policia_penal_usa_a_marca_do_classificador(ambiente):
    marcado = _item("https://x.test/1", "SEJURI abre concurso", alvo="principal")
    sem_marca = _item("https://x.test/2", "Concurso Polícia Penal PR", alvo="principal_fora")
    assert [a.nome for a in carreiras.de_quais(marcado)] == ["Polícia Penal SC"]
    assert carreiras.de_quais(sem_marca) == []


# --- o cartao: situacao e marcos ---------------------------------------------

def test_sem_item_recente_tudo_e_aguardando(ambiente):
    _semear(_item("https://x.test/velho", "2019 – Concurso Polícia Civil SC",
                  situacao="edital_publicado", fonte="fepese",
                  publicado_em=agora() - timedelta(days=30)))
    cartao = _cartao("Polícia Civil SC")
    # Data recente, mas o titulo diz 2019: e a pagina de outra edicao.
    assert cartao.situacao.startswith("nenhum concurso desta carreira")
    assert cartao.referencia is None
    assert {m.valor for m in cartao.marcos} == {"aguardando"}
    assert cartao.itens == 1


def test_item_fora_da_janela_nao_diz_a_situacao(ambiente):
    _semear(_item("https://x.test/1", "Concurso PC SC tem edital", situacao="edital_publicado",
                  publicado_em=agora() - timedelta(days=400)))
    assert _cartao("Polícia Civil SC").referencia is None


def test_o_item_recente_diz_a_situacao_e_os_marcos(ambiente):
    _semear(_item("https://fepese.test/pc", "2026 – Concurso Polícia Civil SC", fonte="fepese",
                  situacao="inscricoes_abertas", banca="FEPESE",
                  inscricoes_de=agora() + timedelta(days=1),
                  inscricoes_ate=agora() + timedelta(days=20)))
    cartao = _cartao("Polícia Civil SC")
    assert cartao.situacao == "inscrições abertas"
    assert cartao.referencia.selo == OFICIAL
    marcos = {m.nome: m for m in cartao.marcos}
    assert marcos["Banca"].valor == "FEPESE" and marcos["Banca"].selo == OFICIAL
    assert marcos["Edital"].valor.startswith("publicado")
    assert " a " in marcos["Inscrições"].valor
    assert marcos["Prova"].valor == "aguardando" and not marcos["Prova"].sabido


def test_noticia_nao_diz_situacao(ambiente):
    _semear(_item("https://x.test/1", "PC SC: governador fala sobre segurança",
                  tipo="noticia"))
    assert _cartao("Polícia Civil SC").referencia is None


def test_marco_so_do_site_de_noticias_diz_por_extenso(ambiente):
    """Pendencia J: o 🟡 sozinho passa batido, e o site de noticias marca
    quase tudo como edital publicado. A banca e a pesquisa nao levam."""
    _semear(_item("https://x.test/pc", "Concurso PC SC tem edital publicado",
                  situacao="edital_publicado", banca="FGV"))
    marcos = {m.nome: m for m in _cartao("Polícia Civil SC").marcos}

    assert marcos["Edital"].selo == NOTICIA
    assert marcos["Edital"].ressalva == "segundo site de notícias"
    assert marcos["Banca"].ressalva == "segundo site de notícias"
    # O que ainda nao se sabe nao tem de quem ser "segundo".
    assert marcos["Prova"].ressalva is None


def test_marco_da_banca_e_da_pesquisa_nao_tem_ressalva(ambiente):
    _semear(_item("https://fepese.test/pc", "2026 – Concurso Polícia Civil SC",
                  fonte="fepese", situacao="edital_publicado", banca="FEPESE"))
    marcos = {m.nome: m for m in _cartao("Polícia Civil SC").marcos}
    assert marcos["Edital"].selo == OFICIAL and marcos["Edital"].ressalva is None
    assert cartoes.Marco("Banca", "IBFC", IA).ressalva is None


def test_a_ressalva_sai_no_cartao_e_no_terminal(ambiente):
    from typer.testing import CliRunner

    from radar.cli import app as cli

    _semear(_item("https://x.test/pc", "Concurso PC SC tem edital publicado",
                  situacao="edital_publicado"))

    assert "· segundo site de notícias" in TestClient(app).get("/acompanhando").text
    # O Rich quebra a linha na largura do terminal: compara sem as quebras.
    saida = " ".join(CliRunner().invoke(cli, ["acompanhar"]).output.split())
    assert "🟡 (segundo site de notícias)" in saida


# --- o sino: so fato, e some quando eu marco visto ------------------------------

def test_fato_acende_o_sino_e_o_visto_apaga(ambiente):
    _semear(_item("https://x.test/1", "Concurso PC SC tem banca definida"))
    _evento("https://x.test/1", linha_do_tempo.MUDOU_SITUACAO,
            "Situacao: autorizado -> banca_definida")
    cartao = _cartao("Polícia Civil SC")
    assert len(cartao.novidades) == 1
    assert cartao.novidades[0].selo == NOTICIA

    assert cartoes.marcar_visto("Polícia Civil SC")
    assert _cartao("Polícia Civil SC").novidades == []


def test_noticia_vai_para_o_historico_sem_sino(ambiente):
    _semear(_item("https://x.test/1", "PC SC: entrevista com o delegado-geral", tipo="noticia"))
    _evento("https://x.test/1", linha_do_tempo.APARECEU, "Entrou no radar")
    cartao = _cartao("Polícia Civil SC")
    assert cartao.novidades == []
    assert [linha.estado for linha in cartao.historico] == ["notícia"]


def test_tres_eventos_do_mesmo_item_sao_uma_novidade(ambiente):
    _semear(_item("https://x.test/1", "Concurso PC SC tem edital publicado"))
    for tipo, texto in [(linha_do_tempo.APARECEU, "Entrou no radar"),
                        (linha_do_tempo.EDITAL_PUBLICADO, "Situacao: banca_definida -> edital_publicado"),
                        (linha_do_tempo.PROVA_MARCADA, "Prova marcada para 10/12/2026")]:
        _evento("https://x.test/1", tipo, texto)
    assert len(_cartao("Polícia Civil SC").novidades) == 1


def test_marcar_visto_de_carreira_que_nao_existe_nao_grava(ambiente):
    assert not cartoes.marcar_visto("Polícia Rodoviária")
    assert not cartoes.caminho().exists()


def test_a_principal_vem_primeiro_e_quem_tem_sino_depois(ambiente):
    _semear(_item("https://x.test/1", "Concurso PMSC abre edital"))
    _evento("https://x.test/1", linha_do_tempo.EDITAL_PUBLICADO, "Situacao: a -> edital_publicado")
    nomes = [c.nome for c in cartoes.cartoes()]
    assert nomes[:2] == ["Polícia Penal SC", "Polícia Militar SC"]


# --- o botao "Verificar atualizacoes" -----------------------------------------------

def test_verificar_roda_a_coleta_e_grava_quando(ambiente):
    rodou = []
    situacao = cartoes.iniciar_verificacao(
        executar=lambda: rodou.append(1) or ["fepese: 0 novo(s)"], em_segundo_plano=False)
    assert situacao == "iniciada" and rodou == [1]
    ultima = cartoes.verificacao()
    assert ultima["fim"] is not None and ultima["resumo"] == ["fepese: 0 novo(s)"]
    assert not ultima["rodando"]


def test_o_botao_espera_o_intervalo_do_yaml(ambiente):
    momento = agora()
    cartoes.iniciar_verificacao(executar=lambda: [], em_segundo_plano=False, momento=momento)
    assert cartoes.iniciar_verificacao(
        executar=lambda: [], em_segundo_plano=False,
        momento=momento + timedelta(minutes=10)) == "cedo"
    assert cartoes.minutos_para_liberar(momento + timedelta(minutes=10)) == 20
    assert cartoes.iniciar_verificacao(
        executar=lambda: [], em_segundo_plano=False,
        momento=momento + timedelta(minutes=31)) == "iniciada"


def test_coleta_que_falha_fica_escrita_e_libera_o_botao(ambiente):
    def quebra():
        raise RuntimeError("fonte fora do ar")

    cartoes.iniciar_verificacao(executar=quebra, em_segundo_plano=False)
    ultima = cartoes.verificacao()
    assert "fonte fora do ar" in ultima["erro"]
    assert not ultima["rodando"]


# --- a pesquisa do Claude Code ---------------------------------------------------

def _id_no_lote(lote, nome="Polícia Civil SC"):
    """O id do pedido desta carreira. A ordem dos pedidos e a da tela, e a
    tela poe primeiro quem tem 🔔: o id nao e fixo."""
    return next(p["id"] for p in lote["pedidos"] if p["acompanhamento"] == nome)


def _resposta(lote, *novidades):
    return [{"id": _id_no_lote(lote), "novidades": list(novidades)}]


def _novidade(**mudancas):
    base = dict(data=(date.today() - timedelta(days=5)).isoformat(), marco="banca",
                descricao="O governo de SC contratou a FEPESE para o concurso.",
                valor="FEPESE", link="https://doe.sc.gov.br/ato-1",
                fonte="Diário Oficial de SC", tipo_de_fonte="oficial", confirmado=True)
    base.update(mudancas)
    return base


def _importar(*novidades, hoje=None):
    lote = cartoes.pedido_de_pesquisa()
    return cartoes.importar_novidades(lote, _resposta(lote, *novidades), "Claude Code, em teste",
                                      hoje=hoje or date.today())


def test_o_pedido_leva_uma_carreira_por_item_e_o_que_ja_sei(ambiente):
    _semear(_item("https://x.test/pc", "Concurso PC SC autorizado"))
    lote = cartoes.pedido_de_pesquisa()
    assert lote["tipo"] == "novidades"
    pedido = next(p for p in lote["pedidos"] if p["id"] == _id_no_lote(lote))
    assert len(lote["pedidos"]) == 4
    assert "https://x.test/pc" in pedido["ja_sei"]["links"]
    assert "Nunca invente link" in lote["pedidos"][0]["instrucao"]


def test_o_pedido_de_uma_carreira_so_acha_o_nome_sem_acento(ambiente):
    lote = cartoes.pedido_de_pesquisa(["policia civil sc"])
    assert [p["acompanhamento"] for p in lote["pedidos"]] == ["Polícia Civil SC"]
    assert [p["id"] for p in lote["pedidos"]] == ["a1"]


def test_carreira_que_nao_existe_e_recusada_com_a_lista(ambiente):
    with pytest.raises(cartoes.CarreiraDesconhecida) as erro:
        cartoes.pedido_de_pesquisa(["Polícia Rodoviária SC"])
    assert "Polícia Rodoviária SC" in str(erro.value)
    assert "Polícia Penal SC" in str(erro.value) and "Polícia Militar SC" in str(erro.value)


def test_o_comando_pede_uma_carreira_so(ambiente):
    from typer.testing import CliRunner

    from radar.cli import app as cli
    from radar.servico import manual

    saida = CliRunner().invoke(cli, ["acompanhar", "--pedido", "--carreira",
                                     "Policia Penal SC"])

    assert saida.exit_code == 0, saida.output
    lote = json.loads(manual.caminho_do_pedido().read_text(encoding="utf-8"))
    assert [p["acompanhamento"] for p in lote["pedidos"]] == ["Polícia Penal SC"]


def test_o_comando_recusa_carreira_desconhecida_sem_gravar(ambiente):
    from typer.testing import CliRunner

    from radar.cli import app as cli
    from radar.servico import manual

    runner = CliRunner()
    sem_pedido = runner.invoke(cli, ["acompanhar", "--carreira", "Polícia Civil SC"])
    errada = runner.invoke(cli, ["acompanhar", "--pedido", "--carreira", "Guarda de Itajaí"])

    assert sem_pedido.exit_code == 1 and "--pedido" in sem_pedido.output
    assert errada.exit_code == 1
    assert "Não há carreira" in " ".join(errada.output.split())
    assert not manual.caminho_do_pedido().exists()


def test_novidade_boa_entra_por_conferir_e_acende_o_sino(ambiente):
    resultado = _importar(_novidade())
    assert resultado["gravadas"] == 1 and not resultado["recusas"]
    cartao = _cartao("Polícia Civil SC")
    assert len(cartao.novidades) == 1
    novidade = cartao.novidades[0]
    assert novidade.selo == IA and novidade.estado == "por conferir"
    # Sem conferir, nao preenche marco.
    assert {m.nome: m.valor for m in cartao.marcos}["Banca"] == "aguardando"


def test_conferida_preenche_o_marco_com_o_selo_da_ia(ambiente):
    _importar(_novidade())
    pesquisa = _cartao("Polícia Civil SC").novidades[0].pesquisa
    assert cartoes.conferir(pesquisa, confere=True)
    banca = {m.nome: m for m in _cartao("Polícia Civil SC").marcos}["Banca"]
    assert banca.valor == "FEPESE" and banca.selo == IA


# --- a banca do alvo principal liga ao estudo (pendencia J) --------------------

PENAL = "Polícia Penal SC"


def _pesquisa_da_penal(banca="Instituto AOCP"):
    """Uma pesquisa de banca da Policia Penal, importada e ainda por conferir."""
    lote = cartoes.pedido_de_pesquisa([PENAL])
    cartoes.importar_novidades(
        lote, [{"id": _id_no_lote(lote, PENAL), "novidades": [
            _novidade(valor=banca, descricao=f"A SAP contratou o {banca}.")]}],
        "Claude Code, em teste", hoje=date.today())
    return _cartao(PENAL).novidades[0].pesquisa


def test_banca_do_item_liga_o_cartao_da_principal_ao_estudo(ambiente):
    _semear(_item("https://x.test/pp", "Concurso Polícia Penal SC: banca definida",
                  alvo="principal", situacao="banca_definida", banca="FGV"))

    banca = _cartao(PENAL).banca_para_estudar

    assert banca is not None and banca.valor == "FGV"
    # O item veio do site de noticias: a ressalva do marco vai junto.
    assert banca.ressalva == "segundo site de notícias"


def test_so_a_pesquisa_conferida_liga(ambiente):
    pesquisa = _pesquisa_da_penal()
    assert _cartao(PENAL).banca_para_estudar is None

    cartoes.conferir(pesquisa, confere=True)

    banca = _cartao(PENAL).banca_para_estudar
    assert banca.valor == "Instituto AOCP" and banca.selo == IA


def test_outra_carreira_com_banca_nao_liga(ambiente):
    _semear(_item("https://fepese.test/pc", "2026 – Concurso Polícia Civil SC",
                  fonte="fepese", situacao="edital_publicado", banca="FEPESE"))
    assert _cartao("Polícia Civil SC").banca_para_estudar is None
    assert _cartao(PENAL).banca_para_estudar is None


def test_banca_com_prova_no_acervo_ganha_o_link_do_padrao(ambiente):
    """O marco por extenso acha a banca do acervo pelo nome curto."""
    from tests.test_simulado import _questao, _semear as _semear_questoes

    _semear_questoes(_questao(1, banca="FEPESE"))
    cartoes.conferir(_pesquisa_da_penal(
        "Fundação de Estudos e Pesquisas Sócio-Econômicos (FEPESE)"), confere=True)

    assert _cartao(PENAL).banca_no_acervo == "FEPESE"
    pagina = TestClient(app).get("/acompanhando").text
    assert "📚 Estudar a banca" in pagina
    assert 'href="/analises">Análises &gt; Edital</a>' in pagina
    assert 'href="/macetes?banca=FEPESE">Padrão da FEPESE</a>' in pagina


def test_banca_sem_prova_no_acervo_diz_isso_em_vez_do_link(ambiente):
    from tests.test_simulado import _questao, _semear as _semear_questoes

    _semear_questoes(_questao(1, banca="FEPESE"))
    cartoes.conferir(_pesquisa_da_penal("Instituto AOCP"), confere=True)

    assert _cartao(PENAL).banca_no_acervo is None
    pagina = TestClient(app).get("/acompanhando").text
    assert 'href="/analises">Análises &gt; Edital</a>' in pagina
    assert "/macetes?banca=" not in pagina
    assert "o acervo ainda não tem prova dessa banca" in pagina


def test_a_banca_casa_por_palavra_inteira(ambiente):
    from tests.test_simulado import _questao, _semear as _semear_questoes

    _semear_questoes(_questao(1, banca="IBFC"))
    assert cartoes.banca_no_acervo("Instituto Brasileiro de Formação (IBFC)") == "IBFC"
    assert cartoes.banca_no_acervo("IBFCX Consultoria") is None


def test_sem_banca_o_cartao_nao_manda_estudar(ambiente):
    assert "Estudar a banca" not in TestClient(app).get("/acompanhando").text


def test_nao_confere_sai_do_sino(ambiente):
    _importar(_novidade())
    pesquisa = _cartao("Polícia Civil SC").novidades[0].pesquisa
    cartoes.conferir(pesquisa, confere=False)
    cartao = _cartao("Polícia Civil SC")
    assert cartao.novidades == []
    assert cartao.historico[0].estado == "não confere"


@pytest.mark.parametrize("mudanca, motivo", [
    (dict(link=""), "sem link"),
    (dict(link="doe.sc.gov.br/ato"), "sem link"),
    (dict(data="ontem"), "sem data"),
    (dict(marco="governador"), "marco fora da lista"),
    (dict(tipo_de_fonte="blog"), "tipo_de_fonte"),
    (dict(descricao="curta"), "descrição"),
])
def test_novidade_torta_e_recusada_e_contada(ambiente, mudanca, motivo):
    resultado = _importar(_novidade(**mudanca))
    assert resultado["gravadas"] == 0
    assert motivo in resultado["recusas"][0]


@pytest.mark.parametrize("link, oficial", [
    ("https://doe.sc.gov.br/ato-1", True),
    ("https://www.cmf.sc.gov.br/lei.pdf", True),
    ("https://www.alesc.sc.leg.br/x", True),
    ("https://www.tjsc.jus.br/x", True),
    ("https://www.mpsc.mp.br/x", True),
    ("https://sap.fepese.org.br", True),
    ("https://FEPESE.org.br./edital", True),
    ("https://www.ieses.org/x", True),
    ("https://cdn.direcaoconcursos.com.br/uploads/diarioOficial.pdf", False),
    ("https://gov.br.qualquer.com/x", False),
    ("https://naofepese.org.br/x", False),
    ("https://ieses.org.falso.com/x", False),
])
def test_oficial_e_o_dominio_do_link(ambiente, link, oficial):
    assert cartoes.link_oficial(link) is oficial


def test_oficial_com_link_de_curso_vira_noticia_e_e_contada(ambiente):
    """A pesquisa de 07/10: a copia do Diario Oficial no CDN de um curso veio
    como "oficial". Entra, mas como noticia, e o importar diz por que."""
    fixture = Path(__file__).parent / "fixtures" / "acompanhamentos_oficiais_0710.json"
    novidades = json.loads(fixture.read_text(encoding="utf-8"))["novidades"]

    resultado = _importar(*novidades, hoje=date(2026, 10, 7))

    assert resultado["gravadas"] == 4 and not resultado["recusas"]
    assert len(resultado["rebaixadas"]) == 2
    assert all("cdn.direcaoconcursos.com.br" in r for r in resultado["rebaixadas"])
    gravadas = json.loads(cartoes.caminho().read_text(encoding="utf-8"))["pesquisas"]
    tipos = {p["link"].split("/")[2]: p["tipo_de_fonte"] for p in gravadas}
    assert tipos == {"sap.fepese.org.br": "oficial", "www.cmf.sc.gov.br": "oficial",
                     "cdn.direcaoconcursos.com.br": "noticia"}


def test_noticia_nunca_sobe_a_oficial(ambiente):
    resultado = _importar(_novidade(tipo_de_fonte="noticia"))
    assert resultado["gravadas"] == 1 and resultado["rebaixadas"] == []
    gravada = json.loads(cartoes.caminho().read_text(encoding="utf-8"))["pesquisas"][0]
    assert gravada["tipo_de_fonte"] == "noticia"


def test_o_comando_diz_quantas_rebaixou(ambiente):
    from typer.testing import CliRunner

    from radar.cli import app as cli
    from radar.servico import manual

    lote = cartoes.pedido_de_pesquisa()
    manual.salvar_pedido(lote)
    resposta = ambiente.parent / "resposta.json"
    resposta.write_text(json.dumps({
        "lote": lote["lote"], "modelo": "Claude Code, em teste",
        "respostas": _resposta(lote, _novidade(link="https://cdn.curso.com.br/doe.pdf")),
    }), encoding="utf-8")

    saida = CliRunner().invoke(cli, ["acompanhar", "--importar", str(resposta)])

    texto = " ".join(saida.output.split())
    assert saida.exit_code == 0, saida.output
    assert "1 declarada(s) oficial" in texto and "cdn.curso.com.br" in texto


def test_data_no_futuro_e_fato_antigo_sao_recusados(ambiente):
    hoje = date(2026, 10, 6)
    resultado = _importar(_novidade(data="2026-10-07"),
                          _novidade(data="2025-01-01", link="https://doe.sc.gov.br/2"),
                          hoje=hoje)
    assert resultado["gravadas"] == 0
    assert "futuro" in resultado["recusas"][0]
    assert "antigo" in resultado["recusas"][1]


def test_previsao_vira_rumor_e_nao_acende_o_sino(ambiente):
    resultado = _importar(_novidade(descricao="O edital deve sair em dezembro, diz o secretário.",
                                    marco="edital"))
    assert resultado["gravadas"] == 1 and resultado["rumores"] == 1
    cartao = _cartao("Polícia Civil SC")
    assert cartao.novidades == []
    assert cartao.historico[0].estado == "não confirmado"
    # Rumor nao se confere: conferir uma previsao nao a torna ato publicado.
    assert not cartoes.conferir(cartao.historico[0].pesquisa, confere=True)


def test_o_que_ja_se_sabe_nao_entra_de_novo(ambiente):
    _semear(_item("https://x.test/pc", "Concurso PC SC autorizado"))
    _importar(_novidade())
    resultado = _importar(_novidade(), _novidade(link="https://x.test/pc"))
    assert resultado["gravadas"] == 0 and resultado["repetidas"] == 2


def test_a_resposta_volta_pelo_importar_comum(ambiente, tmp_path):
    """`radar acompanhar --importar` passa pelo mesmo `manual.importar` dos
    outros pedidos: o lote confere, e o tipo manda para o lugar certo."""
    lote = cartoes.pedido_de_pesquisa()
    cartoes.salvar_pedido(lote)
    resposta = tmp_path / "resposta.json"
    resposta.write_text(json.dumps({"lote": lote["lote"], "modelo": "claude-teste",
                                    "respostas": _resposta(lote, _novidade())}),
                         encoding="utf-8")
    resultado = servico.manual.importar(resposta)
    assert resultado["tipo"] == "novidades" and resultado["gravadas"] == 1
    assert "claude-teste" in resultado["modelo"]
    gravado = json.loads(cartoes.caminho().read_text(encoding="utf-8"))
    assert gravado["pesquisas"][0]["procedencia"] == resultado["modelo"]


def test_a_pesquisa_nao_mexe_no_banco(ambiente):
    _semear(_item("https://x.test/pc", "Concurso PC SC autorizado", situacao="autorizado"))
    _importar(_novidade(marco="edital", descricao="Saiu o edital do concurso da PC SC."))
    with sessao() as s:
        assert s.query(Concurso).one().situacao == "autorizado"


# --- o Telegram: so o critico ----------------------------------------------------

@pytest.fixture
def telegram(monkeypatch):
    monkeypatch.setenv("RADAR_TELEGRAM_TOKEN", "token-de-teste")
    monkeypatch.setenv("RADAR_TELEGRAM_CHAT_ID", "123456")
    enviadas: list[str] = []
    monkeypatch.setattr(avisos, "enviar", lambda texto: enviadas.append(texto) or True)
    monkeypatch.setattr(avisos, "PAUSA_ENTRE_MENSAGENS", 0)
    return enviadas


def test_critico_de_carreira_vai_ao_telegram_uma_vez(ambiente, telegram):
    _semear(_item("https://x.test/1", "Concurso PC SC tem edital publicado"))
    _evento("https://x.test/1", linha_do_tempo.EDITAL_PUBLICADO,
            "Situacao: banca_definida -> edital_publicado")
    _evento("https://x.test/1", linha_do_tempo.MUDOU_SITUACAO,
            "Situacao: prevista -> banca_definida")
    resultado = servico.avisar_acompanhamentos()
    assert resultado.enviados == 2
    assert "Polícia Civil SC" in telegram[0]
    assert "Banca contratada" in telegram[1]
    # A segunda rodada nao repete.
    assert servico.avisar_acompanhamentos().enviados == 0


@pytest.mark.parametrize("tipo, descricao, campos", [
    # Andar de prevista para autorizado nao e critico.
    (linha_do_tempo.MUDOU_SITUACAO, "Situacao: prevista -> autorizado", {}),
    # Item que entrou no radar nao e critico.
    (linha_do_tempo.APARECEU, "Entrou no radar", {}),
    # Noticia nunca vira mensagem.
    (linha_do_tempo.EDITAL_PUBLICADO, "Situacao: a -> edital_publicado", dict(tipo="noticia")),
])
def test_o_que_nao_e_critico_fica_so_na_tela(ambiente, telegram, tipo, descricao, campos):
    _semear(_item("https://x.test/1", "Concurso PC SC", **campos))
    _evento("https://x.test/1", tipo, descricao)
    assert servico.avisar_acompanhamentos().enviados == 0


def test_antes_da_data_do_yaml_nao_avisa(ambiente, telegram):
    yaml = (ambiente / "acompanhamentos.yml").read_text(encoding="utf-8")
    amanha = (agora() + timedelta(days=1)).date().isoformat()
    (ambiente / "acompanhamentos.yml").write_text(
        yaml.replace("telegram_desde: '2000-01-01'", f"telegram_desde: '{amanha}'"),
        encoding="utf-8")
    carreiras.recarregar()
    _semear(_item("https://x.test/1", "Concurso PC SC tem edital"))
    _evento("https://x.test/1", linha_do_tempo.EDITAL_PUBLICADO, "Situacao: a -> edital_publicado")
    assert servico.avisar_acompanhamentos().enviados == 0


# --- a tela ---------------------------------------------------------------------

@pytest.fixture
def cliente(ambiente):
    return TestClient(app)


def test_a_tela_mostra_um_cartao_por_carreira_e_os_favoritos(cliente):
    pagina = cliente.get("/acompanhando").text
    for nome in ("Polícia Penal SC", "Polícia Civil SC", "Polícia Militar SC"):
        assert nome in pagina
    assert "Verificar atualizações" in pagina
    assert "Favoritos" in pagina
    assert "acompanhar --pedido" in pagina
    # Sem verificacao rodando, a pagina nao se recarrega sozinha.
    assert 'http-equiv="refresh"' not in pagina


def test_o_botao_inicia_e_a_tela_se_recarrega_enquanto_roda(cliente, monkeypatch):
    chamadas = []
    monkeypatch.setattr(servico.acompanhamentos, "iniciar_verificacao",
                        lambda: chamadas.append(1) or "iniciada")
    resposta = cliente.post("/acompanhando/verificar", follow_redirects=False)
    assert resposta.status_code == 303 and chamadas == [1]
    assert "Verificação iniciada" in cliente.get(resposta.headers["location"]).text

    monkeypatch.setattr(servico.acompanhamentos, "verificacao",
                        lambda: {"rodando": True, "inicio": agora(), "fim": None})
    assert 'http-equiv="refresh"' in cliente.get("/acompanhando").text


def test_visto_e_conferencia_pela_tela(cliente):
    _semear(_item("https://x.test/1", "Concurso PC SC tem edital"))
    _evento("https://x.test/1", linha_do_tempo.EDITAL_PUBLICADO, "Situacao: a -> edital_publicado")
    _importar(_novidade())
    pagina = cliente.get("/acompanhando").text
    assert "🔔 2" in pagina and "Confere" in pagina

    pesquisa = _cartao("Polícia Civil SC").novidades[0].pesquisa or \
        _cartao("Polícia Civil SC").novidades[1].pesquisa
    cliente.post(f"/acompanhando/pesquisa/{pesquisa}", data={"confere": "sim"})
    assert "conferida" in cliente.get("/acompanhando").text

    cliente.post("/acompanhando/visto", data={"nome": "Polícia Civil SC"})
    assert "🔔" not in cliente.get("/acompanhando").text.split("Favoritos")[0].split(
        "Polícia Civil SC")[1].split("</article>")[0]
