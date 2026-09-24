"""A conta de "por qual assunto comecar", e a frase que ela monta.

O que estes testes existem para proteger e a mesma regra do resto do projeto:
**a tela nunca inventa**. Assunto que eu nunca treinei nao vale zero por cento,
e a conclusao nunca diz nada que nao esteja nos numeros.

Nada aqui toca banco nem rede: o `onde_estudar` recebe contagem e devolve
numero, como o `macetes`.
"""
from radar import onde_estudar
from radar.edital_materias import MateriaDoEdital


LEP = MateriaDoEdital(nome="Lei de Execução Penal", questoes=10)
PORTUGUES = MateriaDoEdital(nome="Língua Portuguesa", questoes=15)


def _linhas(contagens, acertos=None, materias=None, origens=None):
    return onde_estudar.montar(
        materias or [LEP, PORTUGUES],
        contagens,
        acertos or {},
        origens or {},
    )


# --- a conta ----------------------------------------------------------------

def test_questoes_esperadas_e_o_peso_do_edital_vezes_a_fatia():
    """Metade das marcas da materia num assunto, numa materia de 10 questoes,
    sao 5 questoes esperadas. E a conta inteira, e ela e so isso."""
    linhas = _linhas({
        ("Lei de Execução Penal", "Progressão de regime"): (5, 5),
        ("Lei de Execução Penal", "Faltas disciplinares"): (5, 5),
    })

    assert [l.esperadas for l in linhas] == [5.0, 5.0]


def test_a_fatia_e_dentro_da_materia_e_nao_do_acervo():
    """Portugues vale 15 e a LEP vale 10: o assunto que domina a materia menor
    nao pode passar na frente por causa do tamanho do acervo."""
    linhas = _linhas({
        ("Lei de Execução Penal", "Progressão de regime"): (10, 0),
        ("Língua Portuguesa", "Crase"): (10, 0),
    })

    por_assunto = {l.assunto: l.esperadas for l in linhas}
    assert por_assunto["Progressão de regime"] == 10.0     # 10/10 de 10
    assert por_assunto["Crase"] == 15.0                    # 10/10 de 15


def test_pontos_a_ganhar_descontam_o_que_eu_ja_acerto():
    """10 questoes esperadas com 40% de acerto sao 6 pontos a ganhar."""
    linhas = _linhas(
        {("Lei de Execução Penal", "Progressão de regime"): (10, 0)},
        acertos={("Lei de Execução Penal", "Progressão de regime"): (10, 4)},
    )

    assert linhas[0].acerto == 40.0
    assert linhas[0].pontos == 6.0


def test_acertar_tudo_deixa_o_assunto_sem_pontos_a_ganhar():
    """Nao ha o que ganhar onde eu ja acerto tudo - e o grafico tem que dizer
    isso, e nao esconder o assunto."""
    linhas = _linhas(
        {("Lei de Execução Penal", "Progressão de regime"): (10, 0)},
        acertos={("Lei de Execução Penal", "Progressão de regime"): (8, 8)},
    )

    assert linhas[0].pontos == 0.0


# --- o que ela se recusa a fazer --------------------------------------------

def test_assunto_sem_simulado_nao_vale_zero_por_cento():
    """Zero diria que eu errei tudo; o que houve foi eu nao ter treinado."""
    linhas = _linhas({("Lei de Execução Penal", "Progressão de regime"): (10, 0)})

    assert linhas[0].acerto is None
    assert linhas[0].pontos is None
    assert linhas[0].respondidas == 0


def test_sem_simulado_a_ordem_e_a_das_questoes_esperadas():
    """Sem acerto medido nao ha pontos a ganhar para ordenar. A linha entra
    pelo tamanho esperado, que e o maximo que ela poderia valer."""
    linhas = _linhas({
        ("Lei de Execução Penal", "Assunto pequeno"): (2, 0),
        ("Lei de Execução Penal", "Assunto grande"): (8, 0),
    })

    assert [l.assunto for l in linhas] == ["Assunto grande", "Assunto pequeno"]
    assert linhas[0].ordem == linhas[0].esperadas


def test_materia_fora_do_quadro_do_edital_nao_entra():
    """Sem peso no edital nao ha o que multiplicar, e inventar um peso e o que
    faria eu estudar a materia errada por meses."""
    linhas = _linhas({("Noções de Informática", "Planilha"): (10, 0)})

    assert linhas == []


def test_assunto_sem_nenhuma_marca_nao_vira_barra_de_zero():
    linhas = _linhas({("Lei de Execução Penal", "Nunca caiu"): (0, 0)})

    assert linhas == []


# --- a ordem ----------------------------------------------------------------

def test_o_assunto_pequeno_em_que_eu_vou_mal_passa_na_frente_do_grande():
    """E a razao de a secao existir: 10 questoes com 90% de acerto valem 1
    ponto a recuperar, e 4 questoes com 25% valem 3."""
    linhas = _linhas(
        {
            ("Lei de Execução Penal", "Grande"): (9, 0),
            ("Lei de Execução Penal", "Pequeno"): (1, 0),
        },
        acertos={
            ("Lei de Execução Penal", "Grande"): (20, 18),   # 90% de 9 questoes
            ("Lei de Execução Penal", "Pequeno"): (20, 0),   # 0% de 1 questao
        },
    )

    assert [l.assunto for l in linhas] == ["Pequeno", "Grande"]


def test_a_ordem_nao_muda_entre_duas_aberturas():
    contagens = {
        ("Lei de Execução Penal", "A"): (5, 0),
        ("Lei de Execução Penal", "B"): (5, 0),
        ("Lei de Execução Penal", "C"): (5, 0),
    }
    assert [l.assunto for l in _linhas(contagens)] == \
           [l.assunto for l in _linhas(contagens)]


# --- o reforco --------------------------------------------------------------

def test_o_reforco_conta_na_fatia_mas_fica_separado_na_linha():
    """Os dois numeros somam na conta e nunca aparecem somados na tela: uma
    questao da minha prova nao vale o mesmo que uma de outro concurso."""
    linhas = _linhas({("Lei de Execução Penal", "Progressão de regime"): (2, 8)})

    assert linhas[0].proprias == 2
    assert linhas[0].reforco == 8
    assert linhas[0].apoio == 10
    assert linhas[0].base_da_materia == 10


# --- a conclusao ------------------------------------------------------------

def test_a_conclusao_sai_dos_numeros_da_primeira_linha():
    linhas = _linhas(
        {("Lei de Execução Penal", "Lei de Execução Penal"): (10, 0)},
        acertos={("Lei de Execução Penal", "Lei de Execução Penal"): (10, 4)},
    )
    frase = onde_estudar.conclusao(linhas)

    assert "10 questões" in frase
    assert "40%" in frase
    assert "6 pontos a ganhar" in frase


def test_a_conclusao_de_assunto_nunca_treinado_nao_promete_pontos():
    linhas = _linhas({("Lei de Execução Penal", "Progressão de regime"): (10, 0)})
    frase = onde_estudar.conclusao(linhas)

    assert "pontos a ganhar" not in frase
    assert "não respondi nenhuma" in frase


def test_sem_linha_nenhuma_nao_ha_conclusao():
    """Sem numero nao ha conclusao, e escrever uma mesmo assim seria inventar."""
    assert onde_estudar.conclusao([]) is None


def test_o_numero_sai_com_virgula_e_sem_zero_a_toa():
    assert onde_estudar.numero(4.82) == "4,8"
    assert onde_estudar.numero(10.0) == "10"
    assert onde_estudar.numero(40.0, casas=0) == "40"


def test_o_assunto_que_repete_a_materia_nao_a_escreve_duas_vezes():
    """A LEP e uma materia de uma lei so, e o assunto do programa repete o nome
    dela. "Lei de Execucao Penal (Lei 7.210) (Lei de Execucao Penal)" e uma
    frase que se gagueja."""
    linhas = _linhas({
        ("Lei de Execução Penal", "Lei de Execução Penal (Lei nº 7.210)"): (8, 0),
    })

    assert linhas[0].repete_a_materia
    assert onde_estudar.conclusao(linhas).count("Lei de Execução Penal") == 1


def test_o_assunto_de_nome_proprio_leva_a_materia_junto():
    """"Afirmacao historica" sozinho nao diz de que materia e."""
    linhas = _linhas({
        ("Língua Portuguesa", "Crase"): (8, 0),
    })

    assert not linhas[0].repete_a_materia
    assert "Crase (Língua Portuguesa)" in onde_estudar.conclusao(linhas)
