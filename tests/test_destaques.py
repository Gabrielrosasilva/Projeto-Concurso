"""O sublinhado e o negrito do caderno (decisao 178).

O PDF dos testes e montado aqui, byte a byte, com texto inventado: um trecho
com a linha ondulada da FEPESE embaixo, uma palavra em Helvetica-Bold, um
tachado (o traco no meio da letra, que nao e sublinhado) e uma regua entre as
questoes (longe da letra, tambem nao). Nada depende do dia nem da internet.
"""
from markupsafe import Markup

from radar import destaques
from radar.db import sessao
from radar.models import QuestaoDeProva


def _pdf(conteudo: str) -> bytes:
    """Um PDF de uma pagina, com Helvetica (F1) e Helvetica-Bold (F2)."""
    fluxo = conteudo.encode("latin-1")
    objetos = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R "
         b"/Resources << /Font << /F1 5 0 R /F2 6 0 R >> >> >>"),
        b"<< /Length %d >>\nstream\n" % len(fluxo) + fluxo + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        (b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold "
         b"/Encoding /WinAnsiEncoding >>"),
    ]
    saida = bytearray(b"%PDF-1.4\n")
    posicoes = []
    for numero, corpo in enumerate(objetos, start=1):
        posicoes.append(len(saida))
        saida += b"%d 0 obj\n" % numero + corpo + b"\nendobj\n"
    inicio_do_indice = len(saida)
    saida += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objetos) + 1)
    for posicao in posicoes:
        saida += b"%010d 00000 n \n" % posicao
    saida += (b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
              % (len(objetos) + 1, inicio_do_indice))
    return bytes(saida)


# "no qual" em Helvetica 10 tem 32,8 pontos: de x=50 a x=82,8, na linha de
# base 688. A linha ondulada passa 2 pontos abaixo, como na CINCATARINA 2024.
CADERNO = """
BT /F1 10 Tf 1 0 0 1 50 700 Tm (Em "O grupo optou por usar o conceito de 15 minutos,) Tj ET
BT /F1 10 Tf 1 0 0 1 50 688 Tm (no qual) Tj ET
BT /F1 10 Tf 1 0 0 1 82.8 688 Tm ( os moradores devem ser capazes de se deslocar",) Tj ET
BT /F1 10 Tf 1 0 0 1 50 676 Tm (o termo sublinhado pode ser substitu\\355do por:) Tj ET
0.4 w 50 686 m 55 687.2 60 684.8 66 686 c 72 687.2 77 684.8 82.8 686 c S
4 w 50 660 m 300 660 l S
BT /F2 10 Tf 1 0 0 1 50 640 Tm (2.) Tj ET
BT /F1 10 Tf 1 0 0 1 65 640 Tm (Assinale a alternativa ) Tj ET
BT /F2 10 Tf 1 0 0 1 166.2 640 Tm (correta) Tj ET
BT /F1 10 Tf 1 0 0 1 199.6 640 Tm (.) Tj ET
BT /F1 10 Tf 1 0 0 1 50 600 Tm (Um termo riscado sem sublinhado nenhum aqui.) Tj ET
0.6 w 50 603.5 m 120 603.5 l S
BT /F1 10 Tf 1 0 0 1 50 560 Tm (Conforme a Lei n) Tj ET
BT /F1 6 Tf 1 0 0 1 125.6 564 Tm (o) Tj ET
BT /F1 10 Tf 1 0 0 1 130 560 Tm ( 223, de 1973, que trata do assunto.) Tj ET
0.4 w 125.6 562.6 m 128.9 562.6 l S
BT /F1 10 Tf 1 0 0 1 50 520 Tm (Linha curta) Tj ET
0.5 w 50 518 m 300 518 l S
"""


def _caderno(tmp_path):
    caminho = tmp_path / "caderno.pdf"
    caminho.write_bytes(_pdf(CADERNO))
    return caminho


def _marcados(blocos):
    return [(b.texto[i:f].strip(), tipo) for b in blocos for i, f, tipo in b.marcas]


# --- 1. ler o caderno -----------------------------------------------------------------

def test_a_linha_ondulada_embaixo_e_sublinhado_e_a_fonte_bold_e_negrito(tmp_path):
    marcados = _marcados(destaques.ler_marcas(_caderno(tmp_path)))

    assert ("no qual", destaques.SUBLINHADO) in marcados
    assert ("correta", destaques.NEGRITO) in marcados


def test_o_traco_no_meio_da_letra_e_a_regua_longe_dela_nao_sublinham(tmp_path):
    marcados = _marcados(destaques.ler_marcas(_caderno(tmp_path)))

    sublinhados = [t for t, tipo in marcados if tipo == destaques.SUBLINHADO]
    assert sublinhados == ["no qual"]


def test_o_o_elevado_do_ordinal_e_a_regua_debaixo_da_linha_curta_nao_sublinham(tmp_path):
    # O "nº" da FEPESE e um "o" pequeno com o traco embaixo; e a regua fina do
    # Cebraspe passa debaixo da ultima linha, muito alem da ultima palavra.
    marcados = _marcados(destaques.ler_marcas(_caderno(tmp_path)))

    assert ("o", destaques.SUBLINHADO) not in marcados
    assert ("Linha curta", destaques.SUBLINHADO) not in marcados


def test_o_nome_da_fonte_diz_o_negrito():
    assert destaques.eh_negrito("ABCDEF+MyriadPro-Bold")
    assert destaques.eh_negrito("NeoSansPro-Black")
    assert not destaques.eh_negrito("MyriadPro-Regular")
    assert not destaques.eh_negrito(None)


# --- 2. achar o trecho na questao -----------------------------------------------------

ENUNCIADO_1 = ('Em "O grupo optou por usar o conceito de 15 minutos, no qual os moradores '
               'devem ser capazes de se deslocar", o termo sublinhado pode ser substituído por:')


def _bloco(texto: str, trecho: str, tipo=destaques.SUBLINHADO, vez: int = 1):
    inicio = -1
    for _ in range(vez):
        inicio = texto.index(trecho, inicio + 1)
    return destaques.BlocoMarcado(texto=texto, marcas=((inicio, inicio + len(trecho), tipo),))


def test_o_trecho_vai_para_o_campo_em_que_o_texto_em_volta_e_o_mesmo():
    bloco = _bloco('2. Em "O grupo optou por usar o conceito de 15 minutos,\nno qual os '
                   'moradores devem ser capazes de se deslocar",\no termo sublinhado', "no qual")
    campos = {1: {"enunciado": ENUNCIADO_1, "a": "ao qual", "b": "pelo qual"},
              7: {"enunciado": "Outra questão qualquer, sem nada disso.", "a": "no qual"}}

    achadas = destaques.localizar([bloco], campos)

    assert achadas == {1: [{"campo": "enunciado", "inicio": ENUNCIADO_1.index("no qual"),
                            "fim": ENUNCIADO_1.index("no qual") + 7, "tipo": "sublinhado",
                            "trecho": "no qual"}]}


def test_o_mesmo_trecho_no_texto_de_apoio_e_na_questao_vai_para_onde_o_contexto_casa():
    texto_base = ("Estudiosos aplicaram a IA. O grupo optou por usar o conceito de 15 "
                  "minutos, no qual os moradores devem ser capazes de se deslocar de suas casas.")
    # O sublinhado esta no texto de apoio, que segue alem do trecho citado.
    bloco = _bloco("minutos, no qual os moradores devem ser capazes de se deslocar de suas\ncasas.",
                   "no qual")
    campos = {1: {"enunciado": ENUNCIADO_1, "texto_base": texto_base},
              2: {"enunciado": "Sobre o texto, é correto:", "texto_base": texto_base}}

    achadas = destaques.localizar([bloco], campos)

    # O mesmo texto de apoio e um lugar so: vai para as duas questoes.
    assert set(achadas) == {1, 2}
    assert achadas[1][0]["campo"] == "texto_base"


def test_o_trecho_que_cai_em_dois_lugares_fica_sem_marca():
    bloco = _bloco("no qual os moradores", "no qual")
    campos = {1: {"enunciado": "Em 1, no qual os moradores vivem."},
              2: {"enunciado": "Em 2, no qual os moradores votam."}}

    assert destaques.localizar([bloco], campos) == {}


def test_o_numero_da_questao_em_negrito_nao_vira_marca():
    bloco = _bloco("2. Assinale a alternativa correta.", "2.", tipo=destaques.NEGRITO)
    campos = {1: {"enunciado": "Assinale a alternativa correta.", "a": "Lei 2. de 2020"}}

    assert destaques.localizar([bloco], campos) == {}


def test_a_alternativa_inteira_marcada_se_acha_sem_texto_em_volta():
    bloco = _bloco("a.  ao qual\nb.  pelo qual", "ao qual")
    campos = {1: {"enunciado": ENUNCIADO_1, "a": "ao qual", "b": "pelo qual"}}

    achadas = destaques.localizar([bloco], campos)

    assert achadas[1] == [{"campo": "a", "inicio": 0, "fim": 7, "tipo": "sublinhado",
                           "trecho": "ao qual"}]


def test_a_palavra_partida_no_fim_da_linha_e_achada_inteira():
    bloco = _bloco("o termo pode ser substi-\ntuído adequadamente por", "substi-\ntuído")
    campos = {1: {"enunciado": "Em 1, o termo pode ser substituído adequadamente por:"}}

    achadas = destaques.localizar([bloco], campos)

    assert achadas[1][0]["trecho"] == "substituído"


def test_juntar_tira_a_repetida_e_emenda_os_pedacos_vizinhos():
    marcas = [
        {"campo": "enunciado", "inicio": 0, "fim": 4, "tipo": "sublinhado", "trecho": "subs"},
        {"campo": "enunciado", "inicio": 4, "fim": 11, "tipo": "sublinhado", "trecho": "tituído"},
        {"campo": "enunciado", "inicio": 0, "fim": 4, "tipo": "sublinhado", "trecho": "subs"},
    ]

    assert destaques.juntar(marcas) == [
        {"campo": "enunciado", "inicio": 0, "fim": 11, "tipo": "sublinhado",
         "trecho": "substituído"}]


# --- 3. a tela ------------------------------------------------------------------------

def test_partes_corta_o_texto_e_ignora_a_marca_que_nao_e_mais_do_texto():
    marcas = [{"campo": "enunciado", "inicio": 3, "fim": 10, "tipo": "sublinhado",
               "trecho": "no qual"},
              {"campo": "enunciado", "inicio": 0, "fim": 2, "tipo": "negrito",
               "trecho": "XX"}]  # o texto mudou: "Em" nao e "XX"

    assert destaques.partes("Em no qual os", marcas, "enunciado") == [
        ("Em ", frozenset()), ("no qual", frozenset({"sublinhado"})), (" os", frozenset())]
    assert destaques.partes("Em no qual os", marcas, "a") == [("Em no qual os", frozenset())]
    assert destaques.partes("", marcas, "enunciado") == []


def test_a_letra_da_alternativa_vale_em_maiuscula_ou_minuscula():
    marcas = [{"campo": "A", "inicio": 0, "fim": 2, "tipo": "negrito", "trecho": "ao"}]

    assert destaques.partes("ao qual", marcas, "a")[0] == ("ao", frozenset({"negrito"}))


def test_a_tela_escapa_o_texto_e_poe_a_marca():
    from radar.web.app import com_destaques

    questao = {"destaques": [{"campo": "enunciado", "inicio": 7, "fim": 14,
                              "tipo": "sublinhado", "trecho": "no qual"}]}

    html = com_destaques("<b>Em, no qual os", questao, "enunciado")

    assert isinstance(html, Markup)
    assert html == '&lt;b&gt;Em, <u class="sublinhado">no qual</u> os'
    assert com_destaques("sem marca", object(), "enunciado") == "sem marca"


# --- o servico: o caderno inteiro, sem mudar o texto ----------------------------------

PROVA = "https://fepese.test/AT41.pdf"


def test_guardar_destaques_grava_a_marca_e_nao_mexe_no_texto(banco_temporario,
                                                            monkeypatch, tmp_path):
    from radar.servico import provas as servico_provas

    caminho = _caderno(tmp_path)
    with sessao() as s:
        s.add(QuestaoDeProva(prova_url=PROVA, banca="FEPESE", ano=2024, numero=2,
                             materia="Língua Portuguesa", enunciado=ENUNCIADO_1,
                             alternativas={"a": "ao qual", "b": "pelo qual"}, resposta="a",
                             impressao="i2"))
        s.add(QuestaoDeProva(prova_url=PROVA, banca="FEPESE", ano=2024, numero=5,
                             materia="Língua Portuguesa",
                             enunciado="Assinale a alternativa em que o termo sublinhado é um verbo.",
                             alternativas={"a": "x", "b": "y"}, resposta="b", impressao="i5"))
    monkeypatch.setattr(servico_provas.arquivos_de_prova, "carregar_manifesto",
                        lambda: [{"url": PROVA, "caminho": "caderno.pdf"}])
    monkeypatch.setattr(servico_provas, "_caminho", lambda registro: caminho)

    feito = servico_provas.guardar_destaques()

    assert (feito.provas, feito.questoes, feito.sublinhados) == (1, 1, 1)
    # A q5 fala de um termo sublinhado e o caderno nao tem: a lista diz.
    assert [q[3] for q in feito.sem_o_sublinhado] == [5]
    with sessao() as s:
        q2 = s.query(QuestaoDeProva).filter_by(numero=2).one()
        assert q2.enunciado == ENUNCIADO_1
        assert [(m["campo"], m["trecho"]) for m in q2.destaques] == [("enunciado", "no qual")]
