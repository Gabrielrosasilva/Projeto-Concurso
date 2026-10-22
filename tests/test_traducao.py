"""A traducao de cada artigo (decisao 161, T2): o perfil, o pedido e a importacao.

O que estes testes seguram: a traducao boa passa e grava na ficha, fora do
resumo; os termos novos vao para o glossario sem duplicar; a importacao recusa
linha sem texto ou sem fonte, "na real" ou "exemplo" com fonte que nao e o
proprio artigo, artigo que nao e do tema, questao fora do tema ou com o
gabarito trocado, e palavrao (palavra inteira: "disputa" nao e palavrao); a
traducao conferida nao e sobrescrita; o pedido so sai para materia de lei; e a
traducao orfa (o resumo refeito perdeu o artigo) some da tela e o
--verificar-resumos avisa.
"""
import copy
import json
from pathlib import Path

import pytest

from radar import artigos, fichas, traducao
from radar.servico import fichas as servico_fichas
from radar.servico import manual

FIXTURES = Path(__file__).parent / "fixtures"
BOA = json.loads((FIXTURES / "traducao_exemplo.json").read_text(encoding="utf-8"))
RESUMO = json.loads((FIXTURES / "resumo_enxuto.json").read_text(encoding="utf-8"))
PENAL, TEMA = RESUMO["materia"], RESUMO["tema"]
CODIGOS = {"2013-q49": "e", "2019-q53": "d", "2019-q55": "e"}
DO_TEMA = artigos.do_tema(TEMA, "CP, arts. 14 a 21, no texto oficial.", PENAL)
PALAVROES = ("porra", "puta")


def _conferir(bruto=None, **mudar):
    regras = dict(tema=DO_TEMA, codigos=CODIGOS, lista_de_palavroes=PALAVROES)
    regras.update(mudar)
    return traducao.conferir_traducao(copy.deepcopy(BOA) if bruto is None else bruto, **regras)


def _mudada(caminho, valor):
    """A traducao boa com uma mudanca: caminho = ("itens", 0, "na_real", "fontes")."""
    bruto = copy.deepcopy(BOA)
    alvo = bruto
    for passo in caminho[:-1]:
        alvo = alvo[passo]
    alvo[caminho[-1]] = valor
    return bruto


def test_a_traducao_boa_passa_com_as_tres_linhas_e_o_glossario():
    partes, termos = _conferir()
    assert [i["artigo"] for i in partes["itens"]] == ["CP, art. 14", "CP, art. 15"]
    assert list(partes["itens"][0]) == ["artigo", "na_real", "exemplo", "na_prova"]
    assert len(partes["nao_confunda"]) == 2
    assert [t["termo"] for t in termos] == ["tentativa", "atos já praticados"]


@pytest.mark.parametrize("caminho, valor, motivo", [
    (("itens", 0, "na_real", "texto"), "", "linha sem texto"),
    (("itens", 0, "exemplo", "fontes"), [], "linha sem fonte"),
    (("itens", 0, "na_real", "fontes"), ["CP, art. 15"], "não é o próprio artigo"),
    (("itens", 0, "exemplo", "fontes"), ["CP, art. 14", "doutrina"], "não é o próprio artigo"),
    (("itens", 1, "exemplo", "texto"), "Como na 2019-q55, desistiu no meio do furto.",
     "cita só o próprio artigo"),
    (("itens", 0, "artigo"), "CP, art. 22", "não é do tema"),
    (("itens", 0, "artigo"), "CP, arts. 14 e 15", "dispositivo só"),
    (("itens", 1, "artigo"), "CP, art. 14", "aparece duas vezes"),
    (("itens", 0, "na_prova", "fontes"), ["CP, art. 14", "2013-q99"], "não é deste tema"),
    (("itens", 0, "na_prova", "fontes"), ["2019-q55 (gabarito A)"], "gabarito oficial"),
    (("itens", 0, "na_prova", "fontes"), ["CP, art. 33"], "não é do tema"),
    (("itens", 0, "na_prova", "fontes"), ["doutrina (Greco)"], "súmula nem questão real"),
    (("nao_confunda", 0, "fontes"), [], "linha sem fonte"),
    (("nao_confunda", 1, "o_que_acontece"), "", "linha sem texto"),
    (("itens", 1, "exemplo", "texto"), "Desistiu do furto, que porra de dia.", "palavrão"),
    (("glossario", 0, "significado"), "Coisa de puta azar no jogo.", "palavrão"),
    (("glossario", 1, "fontes"), [], "sem fonte"),
    (("itens", 0, "na_real", "texto"), "Isto certamente vai cair na prova.", "previsão"),
])
def test_a_traducao_e_recusada(caminho, valor, motivo):
    with pytest.raises(fichas.FichaRecusada, match=motivo):
        _conferir(_mudada(caminho, valor))


def test_o_palavrao_e_por_palavra_inteira_sem_acento_e_sem_caixa():
    assert traducao.palavrao_em("Uma disputa de pênaltis.", PALAVROES) is None
    assert traducao.palavrao_em("Que PÔRRA foi essa.", PALAVROES) == "porra"
    _conferir(_mudada(("itens", 1, "exemplo", "texto"),
                      "Na disputa da bola, desistiu do furto no meio."))


def test_o_perfil_vem_do_config_linguagem_e_vai_para_a_instrucao():
    traducao.recarregar()
    perfil = traducao.perfil()
    assert perfil["linhas"]["na_real"] and "frases curtas" in perfil["jeito"]
    assert "porra" in traducao.palavroes()
    texto = manual.texto_do_perfil(perfil)
    assert "exemplos de futebol e do dia a dia" in texto and "NAO copie" in texto


# --- a importacao, no banco de teste ---------------------------------------------

def _ficha(resumo_partes=None, traducao_=None):
    escrita = fichas.FichaEscrita(
        tema=TEMA, materia=PENAL, modelo="Claude Code, de teste",
        ler_exatamente="CP, arts. 14 a 21, no texto oficial.",
        criado_em="2026-10-02T12:00:00+00:00",
        resumo={"partes": resumo_partes or RESUMO["partes"], "modelo": "m",
                "criado_em": "2026-10-05T12:00:00+00:00", "conferido_em": None},
        traducao=traducao_)
    servico_fichas.gravar([escrita])
    return escrita


def _pedido(escrita):
    return [{"id": "t1", "tema": TEMA, "materia": PENAL, "ficha": escrita.id,
             "codigos": CODIGOS,
             "artigos_do_tema": traducao.faixas_para_o_pedido(DO_TEMA)}]


def test_importar_grava_a_traducao_na_ficha_e_os_termos_no_glossario(banco_temporario,
                                                                       tmp_path):
    escrita = _ficha()
    modelo = "Claude Code (claude-opus-5-5), importado manualmente, em 12/10/2026"
    resultado = servico_fichas.importar_traducoes(
        _pedido(escrita), [{"id": "t1", "traducao": BOA}], modelo)
    assert resultado["gravadas"] == 1 and not resultado["recusas"]
    assert resultado["termos_novos"] == 2
    (gravada,) = servico_fichas.carregar()
    assert gravada.traducao["modelo"] == modelo and gravada.traducao["conferido_em"] is None
    assert gravada.traducao["itens"][1]["artigo"] == "CP, art. 15"
    # O resumo nao mudou: a traducao mora fora dele.
    assert gravada.resumo["partes"] == RESUMO["partes"]
    termos = servico_fichas.carregar_glossario()
    assert [t["termo"] for t in termos] == ["atos já praticados", "tentativa"]
    assert all(t["modelo"] == modelo and t["criado_em"] for t in termos)
    # De novo (a nao conferida e substituida): o glossario nao duplica.
    de_novo = servico_fichas.importar_traducoes(
        _pedido(escrita), [{"id": "t1", "traducao": BOA}], modelo)
    assert de_novo["gravadas"] == 1 and de_novo["termos_novos"] == 0
    assert len(servico_fichas.carregar_glossario()) == 2


def test_a_ficha_sem_traducao_nao_ganha_a_chave(banco_temporario, tmp_path):
    _ficha()
    bruto = json.loads((tmp_path / "fichas.json").read_text(encoding="utf-8"))
    assert "traducao" not in bruto[0] and "resumo" in bruto[0]


def test_a_traducao_conferida_nao_e_sobrescrita(banco_temporario):
    escrita = _ficha(traducao_={**BOA, "modelo": "m", "criado_em": "x",
                                "conferido_em": "2026-10-13"})
    resultado = servico_fichas.importar_traducoes(
        _pedido(escrita), [{"id": "t1", "traducao": BOA}], "m")
    assert resultado["gravadas"] == 0 and "já conferiu esta tradução" in resultado["recusas"][0]


def test_a_recusa_diz_o_motivo_e_nao_grava(banco_temporario):
    escrita = _ficha()
    ruim = _mudada(("itens", 0, "na_real", "fontes"), ["CP, art. 15"])
    resultado = servico_fichas.importar_traducoes(
        _pedido(escrita), [{"id": "t1", "traducao": ruim}], "m")
    assert resultado["gravadas"] == 0
    assert "não é o próprio artigo" in resultado["recusas"][0]
    assert servico_fichas.carregar()[0].traducao is None


def test_o_importar_do_manual_reconhece_o_lote_de_traducoes(banco_temporario, tmp_path):
    escrita = _ficha()
    lote = manual._novo_lote("traducoes", _pedido(escrita))
    pedido = tmp_path / "pedido_ia.json"
    pedido.write_text(json.dumps(lote, ensure_ascii=False), encoding="utf-8")
    resposta = tmp_path / "resposta_ia.json"
    resposta.write_text(json.dumps({"lote": lote["lote"], "modelo": "claude-opus-5-5",
                                    "respostas": [{"id": "t1", "traducao": BOA}]},
                                   ensure_ascii=False), encoding="utf-8")
    resultado = manual.importar(resposta, pedido)
    assert resultado["tipo"] == "traducoes" and resultado["gravadas"] == 1
    assert "(claude-opus-5-5)" in resultado["modelo"]


# --- o pedido -----------------------------------------------------------------------

def test_o_pedido_so_sai_para_materia_de_lei_e_leva_o_que_a_traducao_precisa(
        banco_temporario):
    penal = _ficha()
    portugues = fichas.FichaEscrita(
        tema="Vozes do verbo", materia="Língua Portuguesa", modelo="m", criado_em="x",
        resumo={"partes": {"artigos": [{"texto": "VTD + se + plural.", "fontes": ["regra"]}]},
                "modelo": "m", "criado_em": "x", "conferido_em": None})
    servico_fichas.gravar([penal, portugues])
    lote = manual.pedido_de_traducoes()
    (p,) = lote["pedidos"]
    assert lote["tipo"] == "traducoes" and p["ficha"] == penal.id
    assert p["artigos_do_tema"] == [{"lei": "CP", "inicio": [14, ""], "fim": [21, ""]}]
    assert ("OS ARTIGOS QUE O TEMA COBRE (pelo titulo, pelo 'ler exatamente' e pelos "
            "blocos do resumo): CP, arts. 14 a 21") in p["pedido"]
    assert "\nCP, art. 15\n  - Desistência voluntária" in p["pedido"]
    assert "COMO A BANCA COBROU" in p["pedido"] and "AS PEGADINHAS" in p["pedido"]
    assert "TERMOS JA NO GLOSSARIO (nao repita): nenhum ainda" in p["pedido"]
    assert "exemplos de futebol" in p["instrucao"]
    # Por tema e por materia; e a traduzida so volta com --refazer.
    assert manual.pedido_de_traducoes(materia="Língua Portuguesa")["pedidos"] == []
    assert len(manual.pedido_de_traducoes(tema=TEMA)["pedidos"]) == 1
    # O banco de teste nao tem as questoes: o pedido nao deixa citar nenhuma.
    assert p["codigos"] == {} and "QUESTOES QUE O NA PROVA PODE CITAR (codigo e gabarito " \
        "oficial): nenhuma" in p["pedido"]
    importada = servico_fichas.importar_traducoes(
        _pedido(penal), [{"id": "t1", "traducao": BOA}], "m")
    assert importada["gravadas"] == 1, importada["recusas"]
    assert manual.pedido_de_traducoes()["pedidos"] == []
    assert len(manual.pedido_de_traducoes(refazer=True)["pedidos"]) == 1
    # O termo que ja esta no glossario vai na lista do "nao repita".
    assert "tentativa" in manual.pedido_de_traducoes(refazer=True)["pedidos"][0]["pedido"]


# --- a traducao orfa ----------------------------------------------------------------

def test_o_artigo_que_sumiu_do_resumo_refeito_fica_orfao_e_o_verificador_avisa(
        banco_temporario):
    escrita = _ficha()
    servico_fichas.importar_traducoes(_pedido(escrita), [{"id": "t1", "traducao": BOA}], "m")
    gravada = servico_fichas.carregar()[0]
    assert traducao.orfas(gravada.traducao, gravada.resumo, DO_TEMA) == []
    # O resumo refeito sem nenhuma frase do art. 15.
    sem_15 = {chave: [f for f in frases if not any("art. 15" in x for x in f["fontes"])]
              for chave, frases in RESUMO["partes"].items()}
    gravada.resumo = {**gravada.resumo, "partes": sem_15}
    servico_fichas.gravar([gravada])
    (orfa,) = traducao.orfas(gravada.traducao, gravada.resumo, DO_TEMA)
    assert orfa.artigo == "CP, art. 15" and "sumiu" in orfa.motivo
    assert [i["artigo"] for i in traducao.visiveis(gravada.traducao, gravada.resumo, DO_TEMA)] \
        == ["CP, art. 14"]
    problemas = [p for t, p in servico_fichas.verificar_resumos() if "órfã" in p]
    assert problemas and "CP, art. 15" in problemas[0]


def test_o_artigo_que_o_resumo_nunca_citou_nao_e_orfao():
    """O artigo traduzido sem frase no resumo ganha o bloco so com o numero e
    a traducao: ele nunca esteve no resumo, entao nao "sumiu"."""
    item = {"artigo": "CP, art. 21"}
    gravada = {"itens": [item], "artigos_do_resumo": [{"lei": "CP", "inicio": [14, ""],
                                                       "fim": [14, ""]}]}
    resumo = {"partes": {"dominar": [{"texto": "x" * 12, "fontes": ["CP, art. 14"]}]}}
    assert traducao.orfas(gravada, resumo, DO_TEMA) == []
    assert traducao.visiveis(gravada, resumo, DO_TEMA) == [item]
    fora = {"itens": [{"artigo": "CP, art. 30"}], "artigos_do_resumo": []}
    (orfa,) = traducao.orfas(fora, resumo, DO_TEMA)
    assert "não é mais do tema" in orfa.motivo


def test_o_artigo_com_bloco_proprio_no_resumo_e_do_tema(banco_temporario):
    """Aprovado em 12/10 (decisao 161): o artigo que tem bloco proprio no
    resumo conta como do tema, mesmo fora do titulo e do "ler exatamente" -
    o caso de Viena, § 5, na Afirmacao historica. A frase de dois artigos
    nao e bloco, e nao conta."""
    partes = copy.deepcopy(RESUMO["partes"])
    partes["artigos"].append({"texto": "Art. 22: coação irresistível e obediência.",
                              "fontes": ["CP, art. 22"]})
    partes["dominar"].append({"texto": "Arts. 23 e 24: duas excludentes de ilicitude.",
                              "fontes": ["CP, art. 23", "CP, art. 24"]})
    escrita = _ficha(partes)
    cobre = servico_fichas.artigos_do_tema(escrita)
    assert artigos.do_tema_contem(cobre, artigos.Artigo("CP", 22))
    assert not artigos.do_tema_contem(cobre, artigos.Artigo("CP", 23))
    item = copy.deepcopy(BOA["itens"][1])
    item["artigo"] = "CP, art. 22"
    for chave in ("na_real", "exemplo"):
        item[chave]["fontes"] = ["CP, art. 22"]
    item["na_prova"]["fontes"] = ["CP, art. 22"]
    pedido = _pedido(escrita)
    pedido[0]["artigos_do_tema"] = traducao.faixas_para_o_pedido(cobre)
    resultado = servico_fichas.importar_traducoes(
        pedido, [{"id": "t1", "traducao": {**BOA, "itens": BOA["itens"] + [item]}}], "m")
    assert resultado["gravadas"] == 1, resultado["recusas"]
    # O pedido diz os artigos do tema sem repetir o que a faixa ja cobre.
    lote = manual.pedido_de_traducoes(tema=TEMA, refazer=True)
    assert "CP, arts. 14 a 21; CP, art. 22" in lote["pedidos"][0]["pedido"]


# --- a letra da lei em todo bloco (decisao 182) ---------------------------------------

def _art_15_so_junto_do_14():
    """O resumo em que nenhuma frase cita o art. 15 sozinho: a do "dominar"
    vira uma que cita os arts. 14 e 15 juntos - o caso dos arts. 1º e 4º da CF
    em "Na Constituicao e o status dos tratados", que o usuario achou em 22/10."""
    partes = copy.deepcopy(RESUMO["partes"])
    partes["dominar"] = [f for f in partes["dominar"] if f["fontes"] != ["CP, art. 15"]]
    partes["dominar"].append({"texto": "Tentativa (art. 14) e desistência voluntária "
                                       "(art. 15) não se confundem.",
                              "fontes": ["CP, art. 14", "CP, art. 15"]})
    return partes


def test_o_bloco_so_com_a_traducao_e_o_que_esta_sem_a_letra():
    assert fichas.resumo_enxuto(RESUMO["partes"], PENAL, BOA).sem_letra == []
    enxuto = fichas.resumo_enxuto(_art_15_so_junto_do_14(), PENAL, BOA)
    (bloco,) = [b for b in enxuto.blocos if b.rotulo == "CP, art. 15"]
    assert bloco.traducao and not bloco.frases
    assert enxuto.sem_letra == ["CP, art. 15"]
    # O artigo sem traducao e sem frase nem ganha bloco: nao ha o que avisar.
    assert fichas.resumo_enxuto(_art_15_so_junto_do_14(), PENAL, None).sem_letra == []


def test_o_verificador_avisa_o_artigo_que_aparece_so_com_a_traducao(banco_temporario):
    escrita = _ficha(_art_15_so_junto_do_14())
    resultado = servico_fichas.importar_traducoes(
        _pedido(escrita), [{"id": "t1", "traducao": BOA}], "m")
    assert resultado["gravadas"] == 1, resultado["recusas"]

    problemas = [p for _, p in servico_fichas.verificar_resumos() if "letra da lei" in p]
    assert problemas == ["CP, art. 15 aparece só com a tradução: falta a letra da lei no "
                         "resumo (uma frase dos artigos que cite só ele)"]

    (gravada,) = servico_fichas.carregar()
    gravada.resumo["partes"]["artigos"].append(
        {"texto": "Art. 15: o agente que, voluntariamente, desiste de prosseguir na execução "
                  "ou impede que o resultado se produza, só responde pelos atos já praticados.",
         "fontes": ["CP, art. 15"]})
    servico_fichas.gravar([gravada])
    assert not [p for _, p in servico_fichas.verificar_resumos() if "letra da lei" in p]


def test_no_arquivo_real_nenhum_artigo_fica_so_com_a_traducao():
    """O data/fichas.json de verdade (decisao 182): em 22/10 havia 59 blocos
    so com o "Traduz pra mim", sem a letra da lei; todos ganharam a letra, e
    o artigo traduzido que vier depois sem ela quebra aqui."""
    from radar import leis

    real = Path(__file__).parent.parent / "data" / "fichas.json"
    sem_letra = []
    for escrita in servico_fichas.carregar(real):
        if not escrita.traducao or not leis.exige_artigo(escrita.materia):
            continue
        visiveis = traducao.visiveis(escrita.traducao, escrita.resumo,
                                     servico_fichas.artigos_do_tema(escrita))
        enxuto = fichas.resumo_enxuto((escrita.resumo or {}).get("partes"), escrita.materia,
                                      {"itens": visiveis})
        sem_letra += [f"{escrita.tema}: {rotulo}" for rotulo in enxuto.sem_letra]
    assert sem_letra == []
