"""A tela de Meu foco, e o leitor do quadro de materias do edital.

A regra que estes testes existem para proteger: **a tela nunca inventa**. Onde
o dado nao existe ela diz "nao sei ainda", e a banca e hipotese enquanto nao
houver edital novo dizendo quem e.

A fixture edital_sap_2019_quadro.txt e o texto REAL do edital 001/SAP/2019 -
o recorte que contem o item 9.7, onde mora o quadro de distribuicao de
questoes. Nenhum teste vai a internet.
"""
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from radar import edital_materias, foco
from radar.db import sessao
from radar.models import Concurso, QuestaoDeProva, agora
from radar.web.app import app

QUADRO_2019 = (
    Path(__file__).parent / "fixtures" / "provas" / "edital_sap_2019_quadro.txt"
).read_text(encoding="utf-8")


@pytest.fixture
def cliente(banco_temporario):
    return TestClient(app)


# --- o quadro de materias do edital -----------------------------------------

def test_le_as_onze_materias_do_edital_de_2019():
    materias = edital_materias.ler_quadro(QUADRO_2019)
    assert len(materias) == 11


def test_o_quadro_fecha_em_cem_questoes():
    """O edital diz 100 no rodape do quadro. Se a soma nao bater, o quadro foi
    lido pela metade - e estudar com peso errado e pior que nao ter peso."""
    materias = edital_materias.ler_quadro(QUADRO_2019)
    assert edital_materias.total_de_questoes(materias) == 100


def test_os_pesos_batem_com_o_edital():
    por_nome = {m.nome: m.questoes for m in edital_materias.ler_quadro(QUADRO_2019)}

    assert por_nome["Língua Portuguesa"] == 15
    assert por_nome["Direitos Humanos"] == 15
    assert por_nome["Lei de Execução Penal"] == 10
    assert por_nome["Direito Penal"] == 5


def test_a_caixa_do_nome_e_padronizada():
    """O edital escreve "Direito constitucional" em caixa baixa no meio do
    quadro e "Lingua Portuguesa" em caixa alta. Sem padronizar, a mesma
    materia apareceria duas vezes na tela."""
    nomes = [m.nome for m in edital_materias.ler_quadro(QUADRO_2019)]
    assert "Direito Constitucional" in nomes
    assert "Direito constitucional" not in nomes


def test_o_total_nao_entra_como_materia():
    nomes = [m.nome.lower() for m in edital_materias.ler_quadro(QUADRO_2019)]
    assert "total" not in nomes


def test_texto_sem_quadro_devolve_vazio():
    """Nunca chutar: edital sem quadro nao vira peso inventado."""
    assert edital_materias.ler_quadro("Edital de abertura. Sao 100 vagas.") == []
    assert edital_materias.ler_quadro("") == []


def test_quadro_que_nao_fecha_e_recusado():
    """Ler metade do quadro e pior que nao ler: eu estudaria com pesos errados
    sem nunca desconfiar."""
    truncado = (
        "distribuicao das questoes\n"
        "Lingua Portuguesa 15 0,10 1,50\n"
        "Direitos Humanos 15 0,10 1,50\n"
        "Direito Penal 5 0,10 0,50\n"
        "TOTAL 100  10,00\n"
    )
    assert edital_materias.ler_quadro(truncado) == []


# --- a banca e sempre hipotese ate sair edital ------------------------------

def test_a_banca_aparece_como_hipotese_com_os_anos():
    banca = foco.Banca(nome="FEPESE", confirmada=False, anos=[2013, 2019])
    assert banca.como_hipotese == "hipotese: FEPESE, que fez 2013 e 2019"


def test_banca_confirmada_perde_o_hipotese():
    banca = foco.Banca(nome="FEPESE", confirmada=True)
    assert banca.como_hipotese == "FEPESE"


def test_sem_banca_a_frase_e_nao_sei_ainda():
    assert foco.Banca().como_hipotese == "nao sei ainda"


def test_hipotese_sem_anos_nao_inventa_ano():
    banca = foco.Banca(nome="FEPESE", confirmada=False)
    assert banca.como_hipotese == "hipotese: FEPESE"


# --- o painel ---------------------------------------------------------------

def _concurso(**mudancas) -> Concurso:
    base = dict(
        url="https://fepese.org.br/concurso/sap-2019",
        fonte="fepese",
        titulo="2019 - Secretaria de Estado da Administracao Prisional",
        uf="SC",
        tipo="concurso",
        situacao="encerrado",
        relevancia="estadual",
        alvo="principal",
        motivo_alvo="Alvo principal (Policia Penal SC).",
        publicado_em=agora() - timedelta(days=100),
    )
    base.update(mudancas)
    return Concurso(**base)


def test_banco_vazio_nao_quebra_a_tela(cliente):
    """Sem nenhum concurso do alvo, a tela abre e diz o que nao sabe."""
    resposta = cliente.get("/")
    assert resposta.status_code == 200
    assert "nao sei ainda" in resposta.text


def test_sem_edital_aberto_a_tela_diz_isso(banco_temporario):
    with sessao() as s:
        s.add(_concurso())

    painel = foco.montar()
    assert painel.aberto is None


def test_edital_aberto_do_cargo_conta(banco_temporario):
    with sessao() as s:
        s.add(_concurso(
            url="https://fepese.org.br/concurso/pp-2027",
            titulo="2027 - Concurso Policia Penal SC",
            situacao="inscricoes_abertas",
        ))

    painel = foco.montar()
    assert painel.aberto is not None
    assert painel.aberto.ano == 2027


def test_vaga_de_outro_cargo_na_mesma_secretaria_nao_e_edital_aberto(banco_temporario):
    """O caso real: "SEJURI SC divulga novo edital com vaga para Medico" bate
    no alvo pelo nome do orgao, e e certo que bata - mas anunciar "edital
    aberto" por causa disso seria dizer o que nao e."""
    with sessao() as s:
        s.add(_concurso(
            url="https://concursosnobrasil.com/sejuri-medico",
            titulo="SEJURI SC divulga novo edital com vaga para Medico",
            fonte="concursosnobrasil",
            situacao="inscricoes_abertas",
        ))

    painel = foco.montar()
    assert painel.aberto is None
    assert painel.aberto_no_orgao is not None
    assert "Medico" in painel.aberto_no_orgao.titulo


def test_vaga_de_outro_cargo_nao_confirma_a_banca(banco_temporario):
    """A banca do seletivo de medico nao diz nada sobre a minha prova."""
    with sessao() as s:
        s.add(_concurso(
            url="https://concursosnobrasil.com/sejuri-medico",
            titulo="SEJURI SC divulga edital com vaga para Medico",
            situacao="inscricoes_abertas",
            banca="Instituto Qualquer",
        ))

    painel = foco.montar()
    assert painel.banca.confirmada is False
    assert "hipotese" in painel.banca.como_hipotese


def test_edital_aberto_do_cargo_confirma_a_banca(banco_temporario):
    with sessao() as s:
        s.add(_concurso(
            url="https://fepese.org.br/concurso/pp-2027",
            titulo="2027 - Concurso Policia Penal SC",
            situacao="inscricoes_abertas",
            banca="FEPESE",
        ))

    painel = foco.montar()
    assert painel.banca.confirmada is True
    assert painel.banca.como_hipotese == "FEPESE"


# --- as questoes do cargo ---------------------------------------------------

def _questao(numero: int, cargo: str, ano: int, materia: str) -> QuestaoDeProva:
    return QuestaoDeProva(
        prova_url=f"https://fepese.test/{ano}/{cargo}.pdf",
        banca="FEPESE", ano=ano, cargo=cargo, numero=numero, materia=materia,
        enunciado=f"Pergunta {numero} de {ano}?",
        alternativas={"a": "x", "b": "y"}, resposta="a",
        impressao=f"{ano}-{numero:03d}",
    )


def test_o_acento_do_cargo_nao_esconde_as_questoes(banco_temporario):
    """O cargo vem acentuado do hotsite ("Agente Penitenciario") e o termo do
    YAML vem sem. Com ilike puro, as questoes do cargo davam ZERO."""
    with sessao() as s:
        for n in range(1, 6):
            s.add(_questao(n, "Agente Penitenciário", 2019, "Direitos Humanos"))

    painel = foco.montar()
    assert painel.questoes_para_treinar == 5
    assert painel.anos_das_provas == [2019]


def test_a_incidencia_separa_por_ano(banco_temporario):
    with sessao() as s:
        s.add(_questao(1, "Agente Penitenciário", 2013, "Direito Penal"))
        s.add(_questao(2, "Agente Penitenciário", 2019, "Direito Penal"))
        s.add(_questao(3, "Agente Penitenciário", 2019, "Direito Penal"))

    painel = foco.montar()
    assert painel.incidencia["Direito Penal"] == {2013: 1, 2019: 2}
    assert painel.anos_das_provas == [2013, 2019]


def test_prova_de_outro_cargo_nao_entra_na_conta(banco_temporario):
    with sessao() as s:
        s.add(_questao(1, "Agente Penitenciário", 2019, "Direito Penal"))
        s.add(_questao(2, "Monitor de Transporte Escolar", 2024, "Portugues"))

    painel = foco.montar()
    assert painel.questoes_para_treinar == 1
    assert painel.anos_das_provas == [2019]


def test_o_cargo_de_treino_e_o_que_acha_prova_no_acervo(banco_temporario):
    """"policia penal" nao casa caderno nenhum: as duas provas que existem sao
    anteriores a mudanca de nome do cargo."""
    with sessao() as s:
        s.add(_questao(1, "Agente Penitenciário", 2019, "Direito Penal"))

    assert foco.cargo_para_treinar() == "agente penitenciario"


def test_sem_prova_no_acervo_nao_ha_cargo_para_treinar(banco_temporario):
    assert foco.cargo_para_treinar() is None


# --- a tela -----------------------------------------------------------------

def test_meu_foco_e_a_home(cliente):
    assert cliente.get("/").status_code == 200
    assert "Meu foco" in cliente.get("/").text


def test_a_tela_mostra_a_banca_como_hipotese(cliente):
    with sessao() as s:
        s.add(_concurso())
        for n in range(1, 4):
            s.add(_questao(n, "Agente Penitenciário", 2019, "Direitos Humanos"))

    texto = cliente.get("/").text
    assert "hipotese: FEPESE" in texto


def test_o_botao_de_treino_aparece_quando_ha_questao(cliente):
    with sessao() as s:
        for n in range(1, 25):
            s.add(_questao(n, "Agente Penitenciário", 2019, "Direitos Humanos"))

    texto = cliente.get("/").text
    assert f"Treinar {foco.QUESTOES_DO_TREINO} questoes" in texto
    assert 'action="/foco/treinar"' in texto


def test_sem_questao_o_botao_da_lugar_a_explicacao(cliente):
    texto = cliente.get("/").text
    assert "Nenhuma questao do cargo no acervo" in texto
    assert 'action="/foco/treinar"' not in texto


def test_treinar_monta_a_rodada_e_leva_para_ela(cliente):
    with sessao() as s:
        for n in range(1, 31):
            s.add(_questao(n, "Agente Penitenciário", 2019, "Direitos Humanos"))

    resposta = cliente.post("/foco/treinar", follow_redirects=False)
    assert resposta.status_code == 303
    assert resposta.headers["location"].startswith("/simulado/")


def test_treinar_sem_questao_devolve_para_o_simulado(cliente):
    """Sem acervo do cargo nao da para montar a rodada, e a tela do simulado e
    quem sabe explicar isso."""
    resposta = cliente.post("/foco/treinar", follow_redirects=False)
    assert resposta.headers["location"] == "/simulado"


def test_os_sinais_juntam_evento_e_noticia(cliente):
    from radar import eventos

    with sessao() as s:
        s.add(_concurso())
        s.add(_concurso(
            url="https://concursosnobrasil.com/noticia-pp",
            titulo="Governo estuda novo concurso da Policia Penal SC",
            tipo="noticia",
            publicado_em=agora() - timedelta(days=2),
        ))
    with sessao() as s:
        eventos.registrar(
            s, "https://fepese.org.br/concurso/sap-2019",
            eventos.MUDOU_SITUACAO, "Situacao: prevista -> autorizado",
            "https://fepese.org.br/concurso/sap-2019",
        )

    painel = foco.montar()
    tipos = {s_["tipo"] for s_ in painel.sinais}
    assert "noticia" in tipos
    assert eventos.MUDOU_SITUACAO in tipos


def test_sem_sinal_a_tela_diz_que_nao_sabe(cliente):
    with sessao() as s:
        s.add(_concurso())

    texto = cliente.get("/").text
    assert "Nada recente" in texto
