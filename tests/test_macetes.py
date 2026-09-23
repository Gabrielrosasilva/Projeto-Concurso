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


def test_sem_banca_escolhida_nao_mostra_analise(cliente):
    """O retrato do acervo inteiro misturava bancas e nao respondia pergunta
    nenhuma. A pagina so calcula depois que eu escolho a banca."""
    _semear(_questao(1))

    texto = cliente.get("/macetes").text

    assert "Escolha uma banca acima" in texto
    assert "questoes no recorte" not in texto


def test_o_menu_de_banca_nao_mostra_numero(cliente):
    """O numero de questoes ao lado do nome parecia um codigo interno."""
    _semear(_questao(1))

    assert ">FEPESE</option>" in cliente.get("/macetes").text


def test_a_tela_mostra_o_recorte_pedido(cliente):
    _semear(*[
        _questao(i, enunciado=f"Sobre a crase na frase {i}.", impressao=f"i{i}")
        for i in range(3)
    ])

    texto = cliente.get("/macetes?banca=FEPESE&tema=crase").text

    assert "3</b> questões no recorte" in texto


def test_a_tela_explica_quando_nao_acha_nada(cliente):
    """O acervo e de cargo municipal de SC: tema de TI nao existe ali, e dizer
    isso e melhor que uma tela vazia."""
    _semear(_questao(1))

    texto = cliente.get("/macetes?banca=FEPESE&tema=seguranca+da+informacao").text

    assert "Nenhuma questão no acervo" in texto


def test_a_tela_diz_o_que_ainda_nao_esta_la(cliente):
    """Pegadinha e macete de memorizacao nao saem de contagem, e a pagina nao
    pode dar a entender que saem."""
    _semear(_questao(1))

    assert "não inventa nada" in cliente.get("/macetes?banca=FEPESE").text


def test_a_tela_destaca_o_assunto_procurado(cliente):
    _semear(*[
        _questao(i, enunciado=f"Sobre o uso da crase na frase {i}.",
                 impressao=f"i{i}", prova_url=f"https://x.test/p{i}.pdf")
        for i in range(3)
    ])

    texto = cliente.get("/macetes?banca=FEPESE&tema=crase").text

    assert "Crase nas provas da FEPESE" in texto


def test_a_tela_mostra_os_dois_graficos(cliente):
    _semear(*[
        _questao(i, enunciado=f"Sobre a crase na frase {i}.", impressao=f"i{i}",
                 prova_url=f"https://x.test/p{i}.pdf")
        for i in range(3)
    ])

    texto = cliente.get("/macetes?banca=FEPESE&tema=crase").text

    assert "Quantas questões caem numa prova" in texto
    assert "O que mais cai em" in texto


def test_campo_vazio_no_formulario_nao_vira_filtro(cliente):
    """Formulario HTML manda todo campo, inclusive o que ficou em branco."""
    _semear(_questao(1))

    assert cliente.get("/macetes?banca=&cargo=&tema=").status_code == 200


def test_o_radar_tem_link_para_os_macetes(cliente):
    """Macetes e a primeira das duas paginas de Estudar: ver o que a banca
    cobra e o passo que decide o que treinar depois."""
    _semear(_questao(1))

    assert 'href="/estudar"' in cliente.get("/concursos").text
    assert cliente.get("/estudar", follow_redirects=False).headers["location"] == (
        "/macetes"
    )



# --- assuntos dentro da materia ---------------------------------------------

def test_a_materia_do_catalogo_e_reconhecida_pelo_apelido():
    """A banca escreve "Lingua Portuguesa"; o catalogo e organizado por
    "portugues"."""
    assert macetes.chave_da_materia("L\u00edngua Portuguesa") == "portugues"
    assert macetes.chave_da_materia("Nocoes de Inform\u00e1tica") == "informatica"


def test_materia_fora_do_catalogo_nao_e_forcada():
    """Conhecimentos Especificos muda com o cargo: nao ha catalogo que sirva."""
    assert macetes.chave_da_materia("Conhecimentos Espec\u00edficos") is None


def test_detecta_o_assunto_da_questao():
    achados, _ = macetes.assuntos_de([
        _questao(1, enunciado="Sobre o uso da crase antes de palavra feminina."),
        _questao(2, enunciado="Sobre concordancia verbal.", impressao="b"),
    ], "portugues")
    nomes = {a.nome for a in achados}

    assert "Crase" in nomes and "Concordancia" in nomes


def test_questao_sem_assunto_conhecido_e_contada_a_parte():
    """Melhor deixar de fora do que empurrar para um assunto qualquer."""
    _, sem_assunto = macetes.assuntos_de([
        _questao(1, enunciado="Uma pergunta que o catalogo nao cobre.")
    ], "portugues")

    assert sem_assunto == 1


def test_o_assunto_conta_em_quantos_cadernos_caiu():
    achados, _ = macetes.assuntos_de([
        _questao(1, enunciado="Sobre a crase.", prova_url="https://x.test/1.pdf"),
        _questao(2, enunciado="Sobre a crase.", prova_url="https://x.test/2.pdf",
                 impressao="b"),
    ], "portugues")

    assert achados[0].cadernos == 2


# --- a materia dominante ----------------------------------------------------

def test_a_materia_da_maioria_e_a_dominante():
    """Procurar "crase" traz 56 questoes de Portugues e 3 de Especificos: a
    materia e Portugues, e nao "as duas"."""
    questoes = (
        [_questao(i, materia="Lingua Portuguesa", impressao=f"p{i}") for i in range(9)]
        + [_questao(50, materia="Conhecimentos Especificos", impressao="e1")]
    )

    assert macetes.materia_dominante(questoes) == "Lingua Portuguesa"


def test_sem_maioria_clara_nao_escolhe_materia():
    """Recorte que mistura materias nao tem materia: afirmar uma seria escolher
    por escolher."""
    questoes = (
        [_questao(i, materia="Lingua Portuguesa", impressao=f"p{i}") for i in range(5)]
        + [_questao(50 + i, materia="Conhecimentos Gerais", impressao=f"g{i}")
           for i in range(5)]
    )

    assert macetes.materia_dominante(questoes) is None


# --- o caderno tipico -------------------------------------------------------

def test_quantas_questoes_de_cada_materia_caem_por_caderno():
    """Duas provas, com 3 questoes de portugues cada: 3 por caderno."""
    questoes = []
    for prova in range(2):
        for n in range(3):
            questoes.append(_questao(
                prova * 10 + n, prova_url=f"https://x.test/p{prova}.pdf",
                impressao=f"i{prova}-{n}",
            ))

    fatia = macetes.composicao_do_caderno(questoes)[0]

    assert fatia.materia == "Lingua Portuguesa"
    assert fatia.por_caderno == 3


def test_materia_que_nao_cai_em_todo_caderno_nao_e_diluida():
    """Temas de Educacao so cai em prova de professor. Dividir pelo total de
    cadernos faria parecer que cai pouco, quando cai muito onde cai."""
    questoes = [
        _questao(1, prova_url="https://x.test/a.pdf"),
        _questao(2, prova_url="https://x.test/b.pdf", impressao="b"),
        _questao(3, prova_url="https://x.test/a.pdf", materia="Temas de Educacao",
                 impressao="c"),
        _questao(4, prova_url="https://x.test/a.pdf", materia="Temas de Educacao",
                 impressao="d"),
    ]

    por_materia = {f.materia: f for f in macetes.composicao_do_caderno(questoes)}

    assert por_materia["Temas de Educacao"].por_caderno == 2


# --- bancas -----------------------------------------------------------------

def test_so_lista_banca_que_tem_prova(banco_temporario):
    _semear(_questao(1, banca="FEPESE"))

    assert servico.bancas_com_questao() == ["FEPESE"]


def test_banca_citada_sem_prova_aparece_a_parte(banco_temporario):
    """Para a tela poder explicar por que o menu e curto, em vez de parecer que
    o radar so conhece uma banca."""
    from radar.models import Concurso

    _semear(_questao(1, banca="FEPESE"))
    with sessao() as s:
        s.add(Concurso(url="https://x.test/c", fonte="teste", titulo="Concurso",
                       banca="IESES"))

    assert servico.bancas_sem_acervo() == ["IESES"]


# --- o que conta como materia universal -------------------------------------

def test_o_mesmo_grupo_reconhece_o_nome_de_cada_banca():
    """A FEPESE escreve "Nocoes de Informatica" e a IESES escreve so
    "Informatica". Sao a mesma materia."""
    assert macetes.chave_da_materia("Nocoes de Informatica") == "informatica"
    assert macetes.chave_da_materia("Informatica") == "informatica"
    assert macetes.chave_da_materia("Matematica e Raciocinio Logico") == "raciocinio"


def test_materia_de_uma_area_so_nao_e_universal():
    """"Conhecimentos Gerais sobre Educacao" so cai em prova de professor, e o
    apelido "gerais" a puxava para o simulado de qualquer concurso."""
    assert macetes.chave_da_materia("Conhecimentos Gerais sobre Educacao") is None
    assert macetes.chave_da_materia("Legislacao e Conhecimentos Gerais sobre Educacao") is None


def test_questao_sem_materia_fica_fora_do_caderno_tipico():
    """Ela apareceria em primeiro lugar no grafico de "quantas questoes caem
    numa prova", que e sobre materia."""
    questoes = [
        _questao(1, materia=None, prova_url="https://x.test/a.pdf"),
        _questao(2, materia="Lingua Portuguesa", prova_url="https://x.test/b.pdf",
                 impressao="b"),
    ]

    materias = {f.materia for f in macetes.composicao_do_caderno(questoes)}

    assert materias == {"Lingua Portuguesa"}


# --- grafico de pizza -------------------------------------------------------

def test_as_fatias_fecham_o_circulo():
    """Fresta branca no fim do circulo e o defeito classico de somar
    porcentagens arredondadas."""
    fatias = macetes.fatias([("a", 1), ("b", 1), ("c", 1)])

    assert fatias[0].inicio == 0
    assert fatias[-1].fim == 100


def test_cada_fatia_comeca_onde_a_anterior_terminou():
    fatias = macetes.fatias([("a", 3), ("b", 1)])

    assert fatias[0].fim == fatias[1].inicio


def test_a_maior_fatia_vem_primeiro():
    fatias = macetes.fatias([("pequena", 1), ("grande", 9)])

    assert fatias[0].rotulo == "grande"


def test_a_porcentagem_e_a_participacao_no_total():
    fatias = macetes.fatias([("a", 3), ("b", 1)])

    assert fatias[0].porcentagem == 75


def test_acima_de_oito_categorias_o_resto_vira_uma_fatia_so():
    """Legenda com vinte linhas vira parede de texto."""
    fatias = macetes.fatias([(f"m{n}", 10 - n) for n in range(12)])

    assert len(fatias) == macetes.MAXIMO_DE_FATIAS
    assert fatias[-1].rotulo == macetes.ROTULO_DO_RESTO


def test_o_resto_soma_o_que_ficou_de_fora():
    fatias = macetes.fatias([("a", 10)] * 1 + [("b", 1)] * 10)
    resto = fatias[-1]

    assert resto.rotulo == macetes.ROTULO_DO_RESTO
    assert resto.valor == 4, "as quatro menores somadas"


def test_cada_fatia_tem_cor_propria():
    fatias = macetes.fatias([(f"m{n}", 1) for n in range(5)])

    assert len({f.cor for f in fatias}) == 5


def test_valor_zerado_nao_vira_fatia():
    """Fatia de 0% nao aparece no desenho e so ocupa linha na legenda."""
    fatias = macetes.fatias([("tem", 5), ("nao tem", 0)])

    assert [f.rotulo for f in fatias] == ["tem"]


def test_lista_vazia_nao_quebra():
    assert macetes.fatias([]) == []


def test_o_numero_por_prova_acompanha_a_fatia():
    """A fatia e a participacao no total; o numero ao lado e quanto a materia
    cai por prova. Os dois nao andam juntos porque nem toda materia cai em
    todo cargo."""
    fatias = macetes.fatias([("Portugues", 1000)], extras={"Portugues": 9.0})

    assert fatias[0].por_caderno == 9.0


def test_a_tela_desenha_a_pizza(cliente):
    _semear(*[
        _questao(i, enunciado=f"Sobre a crase na frase {i}.", impressao=f"i{i}",
                 prova_url=f"https://x.test/p{i}.pdf")
        for i in range(3)
    ])

    texto = cliente.get("/macetes?banca=FEPESE&tema=crase").text

    assert "conic-gradient" in texto
    assert "legenda-pizza" in texto
