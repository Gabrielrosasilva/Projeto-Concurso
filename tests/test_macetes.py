"""Macetes: o que a banca tem costume de cobrar, tirado das provas.

Tudo aqui e contagem em cima do acervo. A regra que vale para o arquivo
inteiro: onde a conta nao alcanca, a pagina nao inventa.
"""
import pytest
from fastapi.testclient import TestClient

from radar import macetes, servico
from radar.db import sessao
from radar.models import QuestaoDeProva
from radar.web.app import app


def _questao(numero: int, **mudancas) -> QuestaoDeProva:
    base = dict(
        prova_url=f"https://x.test/prova{numero}.pdf",
        banca="FEPESE",
        ano=2024,
        municipio="Palhoca",
        cargo="Guarda Municipal",
        numero=numero,
        materia="Lingua Portuguesa",
        enunciado=f"Enunciado da questao {numero} sobre concordancia verbal?",
        alternativas={"a": "um", "b": "dois", "c": "tres", "d": "quatro", "e": "cinco"},
        resposta="c",
        impressao=f"impressao{numero}",
    )
    base.update(mudancas)
    return QuestaoDeProva(**base)


def _semear(*questoes):
    with sessao() as s:
        for q in questoes:
            s.add(q)


@pytest.fixture
def cliente(banco_temporario):
    return TestClient(app)


# --- como a banca pergunta --------------------------------------------------

def test_acha_quem_pede_a_incorreta():
    """E o jeito classico de fazer quem le rapido marcar a certa e errar."""
    achados = macetes.contar_comandos([
        _questao(1, enunciado="Assinale a alternativa INCORRETA sobre o tema."),
        _questao(2, enunciado="Assinale a alternativa correta sobre o tema."),
    ])
    nomes = {c.nome: c for c in achados}

    assert nomes["pede a INCORRETA"].quantas == 1
    assert nomes["pede a INCORRETA"].porcentagem == 50


def test_o_comando_vem_com_conselho():
    """Nome do padrao sozinho nao ajuda em nada na hora da prova."""
    achados = macetes.contar_comandos([
        _questao(1, enunciado="Assinale a alternativa INCORRETA.")
    ])

    assert "ERRO" in achados[0].conselho


def test_acha_verdadeiro_ou_falso():
    achados = macetes.contar_comandos([
        _questao(1, enunciado="Analise: ( V ) primeira ( F ) segunda.")
    ])

    assert any(c.nome == "verdadeiro ou falso" for c in achados)


def test_acha_questao_de_lacuna():
    achados = macetes.contar_comandos([
        _questao(1, enunciado="Complete: ____ medida que chegava ____ hora.")
    ])

    assert any(c.nome == "completa as lacunas" for c in achados)


def test_comando_que_nao_aparece_fica_de_fora():
    achados = macetes.contar_comandos([_questao(1, enunciado="Quanto e 2 + 2?")])

    assert achados == []


def test_o_padrao_ignora_acento_e_caixa():
    """"INCORRETA", "incorreta" e "nao e correta" sao a mesma armadilha."""
    achados = macetes.contar_comandos([
        _questao(1, enunciado="Assinale a alternativa que NÃO É CORRETA.")
    ])

    assert any(c.nome == "pede a INCORRETA" for c in achados)


# --- sobre o chute ----------------------------------------------------------

def test_gabarito_equilibrado_desmente_o_chute_na_c():
    """Com as cinco letras perto de 20%, nao existe letra mais provavel."""
    questoes = []
    for i in range(100):
        letra = "abcde"[i % 5]
        questoes.append(_questao(i, resposta=letra, impressao=f"i{i}"))

    _, veredito = macetes.distribuicao_do_gabarito(questoes)

    assert veredito == "equilibrado"


def test_poucas_questoes_nao_autorizam_afirmar_nada():
    """Buscando "crase" saem 59 questoes mas so 7 enunciados diferentes: o que
    parece tendencia ali e sorteio."""
    questoes = [_questao(i, resposta="d", impressao=f"i{i}") for i in range(7)]

    _, veredito = macetes.distribuicao_do_gabarito(questoes)

    assert veredito == "amostra_pequena"


def test_desequilibrio_de_verdade_e_apontado():
    questoes = [
        _questao(i, resposta="a" if i < 60 else "b", impressao=f"i{i}")
        for i in range(100)
    ]

    _, veredito = macetes.distribuicao_do_gabarito(questoes)

    assert veredito == "tendencia"


# --- a repeticao nao pode mentir --------------------------------------------

def test_questao_repetida_conta_uma_vez_no_gabarito():
    """A mesma questao de crase aparece em 38 cadernos e a resposta e "d".
    Contando todas, o gabarito dizia "letra d em 64%"."""
    repetida = [_questao(i, resposta="d", impressao="a-mesma") for i in range(38)]
    outras = [
        _questao(100 + i, resposta="abcde"[i % 5], impressao=f"outra{i}")
        for i in range(60)
    ]

    analise = macetes.analisar(repetida + outras)
    fatia_do_d = next(pct for letra, _, pct in analise.gabarito if letra == "d")

    assert analise.total == 98
    assert analise.distintas == 61
    assert fatia_do_d < 30


def test_termo_de_questao_repetida_nao_domina_os_assuntos():
    repetida = [
        _questao(i, enunciado="Sobre ginastica ritmica na Olimpiada.",
                 impressao="a-mesma")
        for i in range(38)
    ]
    outras = [
        _questao(100 + i, enunciado="Sobre concordancia verbal na frase.",
                 impressao=f"outra{i}")
        for i in range(10)
    ]

    termos = {t.palavra: t.quantas for t in macetes.analisar(repetida + outras).termos}

    assert termos["ginastica"] == 1
    assert termos["concordancia"] == 10


def test_a_materia_conta_todas_as_questoes():
    """Questao repetida em 38 cadernos pesa mesmo mais na prova que eu vou
    fazer: aqui a repeticao e informacao, e nao ruido."""
    questoes = [_questao(i, impressao="a-mesma") for i in range(38)]

    assert macetes.analisar(questoes).materias == [("Lingua Portuguesa", 38)]


def test_mostra_as_questoes_mais_reaproveitadas():
    questoes = (
        [_questao(i, impressao="campea") for i in range(5)]
        + [_questao(100 + i, impressao="segunda") for i in range(2)]
        + [_questao(200, impressao="unica")]
    )

    repetidas = macetes.mais_repetidas(questoes)

    assert [r.cadernos for r in repetidas] == [5, 2]


# --- palavras que mais aparecem ---------------------------------------------

def test_palavra_sem_conteudo_fica_de_fora():
    """Sem a lista de palavras vazias, o topo dos assuntos seria "que",
    "alternativa" e "sobre"."""
    termos = {t.palavra for t in macetes.termos_frequentes([
        _questao(1, enunciado="Assinale a alternativa correta sobre a crase.")
    ])}

    assert "crase" in termos
    assert "alternativa" not in termos and "sobre" not in termos


def test_palavra_repetida_no_mesmo_enunciado_conta_uma_vez():
    termos = {t.palavra: t.quantas for t in macetes.termos_frequentes([
        _questao(1, enunciado="Crase, crase e mais crase no texto.")
    ])}

    assert termos["crase"] == 1


# --- a busca ----------------------------------------------------------------

def test_busca_por_tema_livre_olha_o_enunciado(banco_temporario):
    """Eu escrevo "crase", e nao "Lingua Portuguesa": o nome que a banca usa
    raramente e a palavra que eu penso."""
    _semear(
        _questao(1, enunciado="Sobre o uso da crase na frase abaixo."),
        _questao(2, enunciado="Sobre concordancia verbal.", impressao="outra"),
    )

    assert servico.analisar_banca(tema="crase").total == 1


def test_busca_por_tema_ignora_acento(banco_temporario):
    _semear(_questao(1, enunciado="Sobre a oração subordinada."))

    assert servico.analisar_banca(tema="oracao").total == 1


def test_busca_por_materia_tambem_funciona(banco_temporario):
    _semear(
        _questao(1, materia="Nocoes de Informatica"),
        _questao(2, materia="Lingua Portuguesa", impressao="outra"),
    )

    assert servico.analisar_banca(tema="informatica").total == 1


def test_busca_por_cargo(banco_temporario):
    _semear(
        _questao(1, cargo="Guarda Municipal"),
        _questao(2, cargo="Professor de Matematica", impressao="outra"),
    )

    assert servico.analisar_banca(cargo="Guarda").total == 1


def test_recorte_sem_questao_devolve_analise_vazia(banco_temporario):
    _semear(_questao(1))

    vazia = servico.analisar_banca(tema="seguranca da informacao")

    assert vazia.total == 0 and vazia.comandos == []


# --- a tela -----------------------------------------------------------------

def test_a_tela_abre_sem_filtro_nenhum(cliente):
    _semear(_questao(1))

    resposta = cliente.get("/macetes")

    assert resposta.status_code == 200
    assert "Macetes" in resposta.text


def test_a_tela_mostra_o_recorte_pedido(cliente):
    _semear(*[
        _questao(i, enunciado=f"Sobre a crase na frase {i}.", impressao=f"i{i}")
        for i in range(3)
    ])

    texto = cliente.get("/macetes?tema=crase").text

    assert "3</b> questoes no recorte" in texto


def test_a_tela_explica_quando_nao_acha_nada(cliente):
    """O acervo e de cargo municipal de SC: tema de TI nao existe ali, e dizer
    isso e melhor que uma tela vazia."""
    _semear(_questao(1))

    texto = cliente.get("/macetes?tema=seguranca+da+informacao").text

    assert "Nenhuma questao no acervo" in texto


def test_a_tela_diz_o_que_ainda_nao_esta_la(cliente):
    """Pegadinha e macete de memorizacao nao saem de contagem, e a pagina nao
    pode dar a entender que saem."""
    assert "nao inventa nada" in cliente.get("/macetes").text


def test_campo_vazio_no_formulario_nao_vira_filtro(cliente):
    """Formulario HTML manda todo campo, inclusive o que ficou em branco."""
    _semear(_questao(1))

    assert cliente.get("/macetes?banca=&cargo=&tema=").status_code == 200


def test_o_radar_tem_link_para_os_macetes(cliente):
    _semear(_questao(1))

    assert 'href="/macetes"' in cliente.get("/").text
