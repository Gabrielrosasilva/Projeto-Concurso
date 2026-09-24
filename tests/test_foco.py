"""A tela de Meu foco, e o leitor do quadro de materias do edital.

A regra que estes testes existem para proteger: **a tela nunca inventa**. Onde
o dado nao existe ela diz "não sei ainda", e a banca e hipotese enquanto nao
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
    assert banca.como_hipotese == "hipótese: FEPESE, que fez 2013 e 2019"


def test_banca_confirmada_perde_o_hipotese():
    banca = foco.Banca(nome="FEPESE", confirmada=True)
    assert banca.como_hipotese == "FEPESE"


def test_sem_banca_a_frase_e_nao_sei_ainda():
    assert foco.Banca().como_hipotese == "não sei ainda"


def test_hipotese_sem_anos_nao_inventa_ano():
    banca = foco.Banca(nome="FEPESE", confirmada=False)
    assert banca.como_hipotese == "hipótese: FEPESE"


# --- o painel ---------------------------------------------------------------

CONCURSO_DE_2019 = "https://fepese.org.br/concurso/sap-2019"


def _concurso(**mudancas) -> Concurso:
    base = dict(
        url=CONCURSO_DE_2019,
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
    assert "não sei ainda" in resposta.text


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
    assert "hipótese" in painel.banca.como_hipotese


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

def _questao(
    numero: int,
    cargo: str,
    ano: int,
    materia: str,
    concurso_url: str = CONCURSO_DE_2019,
) -> QuestaoDeProva:
    """Uma questao do acervo, ligada ao concurso que a originou.

    O concurso vem junto porque e dele que sai a UF, e desde a etapa 14 prova
    sem estado provado nao conta como minha.
    """
    return QuestaoDeProva(
        prova_url=f"https://fepese.test/{ano}/{cargo}.pdf",
        concurso_url=concurso_url,
        banca="FEPESE", ano=ano, cargo=cargo, numero=numero, materia=materia,
        enunciado=f"Pergunta {numero} de {ano}?",
        alternativas={"a": "x", "b": "y"}, resposta="a",
        impressao=f"{ano}-{numero:03d}",
    )


def test_o_acento_do_cargo_nao_esconde_as_questoes(banco_temporario):
    """O cargo vem acentuado do hotsite ("Agente Penitenciario") e o termo do
    YAML vem sem. Com ilike puro, as questoes do cargo davam ZERO."""
    with sessao() as s:
        s.add(_concurso())
        for n in range(1, 6):
            s.add(_questao(n, "Agente Penitenciário", 2019, "Direitos Humanos"))

    painel = foco.montar()
    assert painel.questoes_para_treinar == 5
    assert painel.anos_das_provas == [2019]


def test_a_incidencia_separa_por_ano(banco_temporario):
    with sessao() as s:
        s.add(_concurso())
        s.add(_questao(1, "Agente Penitenciário", 2013, "Direito Penal"))
        s.add(_questao(2, "Agente Penitenciário", 2019, "Direito Penal"))
        s.add(_questao(3, "Agente Penitenciário", 2019, "Direito Penal"))

    painel = foco.montar()
    assert painel.incidencia["Direito Penal"] == {2013: 1, 2019: 2}
    assert painel.anos_das_provas == [2013, 2019]


def test_prova_de_outro_cargo_nao_entra_na_conta(banco_temporario):
    with sessao() as s:
        s.add(_concurso())
        s.add(_questao(1, "Agente Penitenciário", 2019, "Direito Penal"))
        s.add(_questao(2, "Monitor de Transporte Escolar", 2024, "Portugues"))

    painel = foco.montar()
    assert painel.questoes_para_treinar == 1
    assert painel.anos_das_provas == [2019]


# --- so a MINHA prova conta: o cargo certo, no estado certo (etapa 14) ------
#
# O cargo sozinho nunca bastou, e a tela contava como se bastasse. "Policial
# Penal Federal" contem "policial penal" e e outro concurso; "Policia Penal do
# Parana" e o mesmo cargo em outro estado, com outra banca e outro programa.
# Estudar pelo peso de uma prova que nao e a minha e estudar a materia errada.

CONCURSO_FEDERAL = "https://concursosnobrasil.com/policia-penal-federal-2026"
CONCURSO_DO_PARANA = "https://concursosnobrasil.com/policia-penal-pr-2026"


def test_prova_de_policia_penal_federal_nao_e_minha(banco_temporario):
    """A lista `exclui` do alvo.yml vale aqui como vale no resto do projeto."""
    with sessao() as s:
        s.add(_concurso())
        s.add(_concurso(
            url=CONCURSO_FEDERAL,
            titulo="Concurso Policia Penal Federal",
            uf="DF",
        ))
        s.add(_questao(1, "Agente Penitenciário", 2019, "Direito Penal"))
        s.add(_questao(
            2, "Policial Penal Federal", 2026, "Direito Penal",
            concurso_url=CONCURSO_FEDERAL,
        ))

    painel = foco.montar()
    assert painel.questoes_para_treinar == 1
    assert painel.anos_das_provas == [2019]


def test_o_mesmo_cargo_em_outro_estado_nao_e_minha(banco_temporario):
    """O alvo principal e de Santa Catarina. Policia Penal do Parana e o mesmo
    cargo e outro concurso - outra banca, outro programa, outra prova."""
    with sessao() as s:
        s.add(_concurso())
        s.add(_concurso(
            url=CONCURSO_DO_PARANA,
            titulo="Concurso Policia Penal do Parana",
            uf="PR",
        ))
        s.add(_questao(1, "Agente Penitenciário", 2019, "Direito Penal"))
        s.add(_questao(
            2, "Policial Penal", 2026, "Direito Penal",
            concurso_url=CONCURSO_DO_PARANA,
        ))

    painel = foco.montar()
    assert painel.questoes_para_treinar == 1
    assert painel.anos_das_provas == [2019]


def test_sem_uf_a_palavra_de_sc_ainda_decide(banco_temporario):
    """A FEPESE nao informa a UF. Quando ela falta, quem decide e uma palavra
    que so existe aqui - a mesma regra que marca o alvo na coleta."""
    with sessao() as s:
        s.add(_concurso(uf=None, titulo="Policia Penal de Santa Catarina"))
        for n in range(1, 4):
            s.add(_questao(n, "Agente Penitenciário", 2019, "Direito Penal"))

    assert foco.montar().questoes_para_treinar == 3


def test_prova_sem_concurso_conhecido_nao_conta(banco_temporario):
    """Nunca chutar: sem o concurso nao da para provar o estado, e contar
    assim mesmo seria inventar que a prova e minha."""
    with sessao() as s:
        for n in range(1, 4):
            s.add(_questao(
                n, "Agente Penitenciário", 2019, "Direito Penal",
                concurso_url=None,
            ))

    painel = foco.montar()
    assert painel.questoes_para_treinar == 0
    assert painel.anos_das_provas == []


def test_a_banca_so_conta_o_ano_da_prova_que_e_minha(banco_temporario):
    """A hipotese de banca diz "a FEPESE fez 2013 e 2019". Se uma prova de
    outro estado entrasse na conta, ela passaria a citar um ano que nao e do
    meu concurso."""
    with sessao() as s:
        s.add(_concurso())
        s.add(_concurso(
            url=CONCURSO_DO_PARANA,
            titulo="Concurso Policia Penal do Parana",
            uf="PR",
        ))
        s.add(_questao(1, "Agente Penitenciário", 2019, "Direito Penal"))
        s.add(_questao(
            2, "Policial Penal", 2026, "Direito Penal",
            concurso_url=CONCURSO_DO_PARANA,
        ))

    assert foco.montar().banca.anos == [2019]


# --- o edital e lido uma vez so (etapa 14) ---------------------------------
#
# A tela abria em quatro segundos e meio porque relia o PDF do edital inteiro
# a cada vez, duas vezes por abertura. O que foi lido agora fica guardado, e o
# sha256 do manifesto e quem diz quando vale a pena ler de novo.

class _PdfFalso:
    """Um edital que conta quantas vezes foi aberto."""

    def __init__(self, caminho: Path, sha: str = "sha-do-edital"):
        self.caminho = caminho
        self.sha = sha
        self.leituras = 0

    def manifesto(self) -> list[dict]:
        """O edital, e a prova que faz aquela edicao contar como edicao."""
        return [
            {
                "tipo": "edital",
                "concurso_url": CONCURSO_DE_2019,
                "arquivo": "2019_SAP_Edital_1.pdf",
                "caminho": self.caminho.name,
                "sha256": self.sha,
            },
            {
                "tipo": "prova",
                "concurso_url": CONCURSO_DE_2019,
                "arquivo": "AP.pdf",
                "caminho": "AP.pdf",
                "sha256": "sha-da-prova",
            },
        ]

    def extrair_texto(self, caminho):
        self.leituras += 1
        return QUADRO_2019 + "\nO concurso tera validade de 2 (dois) anos"


@pytest.fixture
def edital_no_disco(banco_temporario, tmp_path, monkeypatch):
    """Um edital de mentira no acervo, com manifesto e PDF no disco."""
    pdf = tmp_path / "edital.pdf"
    pdf.write_bytes(b"%PDF-1.4 nao e lido de verdade")
    falso = _PdfFalso(pdf)

    monkeypatch.setattr(foco.provas, "carregar_manifesto", falso.manifesto)
    monkeypatch.setattr(foco, "extrair_texto", falso.extrair_texto)
    with sessao() as s:
        s.add(_concurso())
    return falso


def _edicao_de_2019():
    return Concurso(
        url=CONCURSO_DE_2019,
        titulo="2019 - Secretaria de Estado da Administracao Prisional",
        fonte="fepese", tipo="concurso", situacao="encerrado",
    )


def test_o_edital_e_lido_uma_vez_por_abertura(edital_no_disco):
    """Antes eram duas leituras do mesmo PDF: uma para o quadro de materias e
    outra para a validade."""
    painel = foco.montar()

    assert edital_no_disco.leituras == 1
    assert len(painel.materias_do_edital) == 11
    assert painel.total_do_edital == 100
    assert painel.validade.startswith("2 anos a contar")


def test_a_segunda_abertura_nao_abre_mais_o_pdf(edital_no_disco):
    foco.montar()
    painel = foco.montar()

    assert edital_no_disco.leituras == 1
    assert len(painel.materias_do_edital) == 11
    assert painel.ano_do_edital == 2019


def test_pdf_trocado_e_lido_de_novo(edital_no_disco):
    """O sha256 e quem manda: arquivo novo, leitura nova. Sem isso, uma
    retificacao do edital ficaria invisivel para sempre."""
    foco.montar()
    edital_no_disco.sha = "sha-depois-da-retificacao"

    foco.montar()
    assert edital_no_disco.leituras == 2


def test_guardado_corrompido_nao_quebra_a_tela(edital_no_disco):
    foco.montar()
    foco._caminho_do_edital_lido().write_text("isto nao e json", encoding="utf-8")

    painel = foco.montar()
    assert edital_no_disco.leituras == 2
    assert len(painel.materias_do_edital) == 11


def test_sem_sha256_no_manifesto_nada_e_guardado(edital_no_disco):
    """Guardar o que nao da para conferir depois e o mesmo que chutar."""
    edital_no_disco.sha = None

    foco.montar()
    foco.montar()
    assert edital_no_disco.leituras == 2
    assert not foco._caminho_do_edital_lido().exists()


def test_edital_fora_do_acervo_nao_inventa_quadro(banco_temporario, monkeypatch):
    monkeypatch.setattr(foco.provas, "carregar_manifesto", lambda: [])

    lido = foco._ler_edital(_edicao_de_2019())
    assert lido.materias == []
    assert lido.total == 0
    assert lido.validade is None


# O treino deixou de escolher UM termo de cargo para filtrar o sorteio: quem
# monta a rodada agora e `servico.criar_simulado_do_alvo`, que trata os termos
# do YAML como nomes do mesmo cargo. Os testes disso estao em
# tests/test_treino_do_alvo.py.


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
    assert "hipótese: FEPESE" in texto


def test_o_botao_de_treino_aparece_quando_ha_questao(cliente):
    with sessao() as s:
        for n in range(1, 25):
            s.add(_questao(n, "Agente Penitenciário", 2019, "Direitos Humanos"))

    texto = cliente.get("/").text
    assert f"Treinar {foco.QUESTOES_DO_TREINO} questões" in texto
    assert 'action="/foco/treinar"' in texto


def test_sem_questao_o_botao_da_lugar_a_explicacao(cliente):
    texto = cliente.get("/").text
    assert "Nenhuma questão do cargo no acervo" in texto
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


# --- o peso do edital contra o meu acerto (etapa 9) -------------------------

def _desempenho(materia: str, respondidas: int, acertos: int):
    from radar.servico import DesempenhoDaMateria

    return DesempenhoDaMateria(materia, respondidas, acertos)


def test_as_materias_de_maior_peso_sao_as_acima_da_media():
    """No edital de 2019 sao sete: as duas de 15 questoes e as cinco de 10,
    que juntas valem 80 das 100. As quatro de 5 ficam de fora."""
    materias = edital_materias.ler_quadro(QUADRO_2019)
    pesadas = foco.materias_de_maior_peso(materias, 100)

    assert len(pesadas) == 7
    assert "Língua Portuguesa" in pesadas          # 15 questoes
    assert "Lei de Execução Penal" in pesadas      # 10 questoes
    assert "Direito Penal" not in pesadas          # 5 questoes


def test_o_corte_e_a_media_da_propria_prova():
    """Nao e um numero que eu escolhi: com o edital mudando, o corte muda
    junto. Quatro materias iguais nao tem nenhuma "de maior peso"."""
    materias = edital_materias.ler_quadro(QUADRO_2019)

    assert foco.materias_de_maior_peso([], 100) == set()
    assert foco.materias_de_maior_peso(materias, 0) == set()


def test_a_pior_e_a_de_menor_acerto_entre_as_pesadas():
    pior = foco._pior_das_pesadas(
        {"Direitos Humanos", "Língua Portuguesa"},
        {
            "Direitos Humanos": _desempenho("Direitos Humanos", 20, 8),   # 40%
            "Língua Portuguesa": _desempenho("Língua Portuguesa", 20, 16),  # 80%
        },
    )

    assert pior == "Direitos Humanos"


def test_ir_mal_numa_materia_leve_nao_muda_por_onde_comecar():
    """Errar numa materia de 5 questoes custa 5 questoes; errar numa de 15
    decide a prova. O destaque segue o peso, e nao so o acerto."""
    pior = foco._pior_das_pesadas(
        {"Direitos Humanos"},
        {
            "Direitos Humanos": _desempenho("Direitos Humanos", 20, 12),  # 60%
            "Direito Penal": _desempenho("Direito Penal", 10, 1),         # 10%
        },
    )

    assert pior == "Direitos Humanos"


def test_materia_que_eu_nunca_treinei_nao_vira_a_pior():
    """Apontar a pior entre as que eu nunca fiz seria inventar um numero."""
    pior = foco._pior_das_pesadas(
        {"Direitos Humanos", "Sociologia Aplicada"},
        {"Direitos Humanos": _desempenho("Direitos Humanos", 20, 12)},
    )

    assert pior == "Direitos Humanos"


def test_sem_nenhuma_pesada_treinada_nao_ha_destaque():
    assert foco._pior_das_pesadas({"Direitos Humanos"}, {}) is None
    assert foco._pior_das_pesadas(set(), {}) is None


def test_empate_de_acerto_desempata_pela_mais_feita():
    """Entre 50% em duas questoes e 50% em trinta, a segunda e a que eu sei
    que e verdade."""
    pior = foco._pior_das_pesadas(
        {"Direitos Humanos", "Língua Portuguesa"},
        {
            "Direitos Humanos": _desempenho("Direitos Humanos", 2, 1),
            "Língua Portuguesa": _desempenho("Língua Portuguesa", 30, 15),
        },
    )

    assert pior == "Língua Portuguesa"


# --- na tela ----------------------------------------------------------------

@pytest.fixture
def com_quadro_do_edital(monkeypatch):
    """A tela com o quadro real de 2019, sem depender do PDF estar no disco."""
    materias = edital_materias.ler_quadro(QUADRO_2019)
    monkeypatch.setattr(
        foco, "_ler_edital",
        lambda concurso: foco.EditalLido(materias, 100, 2019, None),
    )
    # O quadro so existe quando existe uma edicao que virou prova: em
    # producao, os dois andam juntos porque saem do mesmo PDF.
    monkeypatch.setattr(
        foco, "_edital_com_prova", lambda concursos: concursos[0] if concursos else None
    )
    return materias


def _treinar(materia: str, acertos: int, erros: int) -> None:
    """Responde questoes de uma materia, para haver acerto medido."""
    from radar import servico

    with sessao() as s:
        for n in range(acertos + erros):
            # A prova e uma por materia: duas questoes numero 1 no mesmo
            # caderno violam a unicidade, como na vida real.
            s.add(QuestaoDeProva(
                prova_url=f"https://fepese.test/{materia}.pdf", banca="FEPESE",
                concurso_url=CONCURSO_DE_2019, ano=2019,
                cargo="Agente Penitenciário", numero=n + 1, materia=materia,
                enunciado=f"{materia} {n}?", alternativas={"a": "x", "b": "y"},
                resposta="a", impressao=f"{materia}-{n}",
            ))

    simulado = servico.criar_simulado(quantidade=acertos + erros, materia=materia)
    for n in range(acertos + erros):
        atual = servico.questao_atual(simulado.id)
        _resposta, questao = atual
        servico.responder(simulado.id, questao.id, "a" if n < acertos else "b")


def test_a_tabela_mostra_o_acerto_ao_lado_do_peso(cliente, com_quadro_do_edital):
    with sessao() as s:
        s.add(_concurso())
    _treinar("Direitos Humanos", acertos=2, erros=8)      # 20%

    texto = cliente.get("/").text

    assert "Meu acerto" in texto
    assert "20%" in texto
    assert "de 10" in texto


def test_a_materia_sem_treino_nao_aparece_como_zero(cliente, com_quadro_do_edital):
    """Zero diria que eu errei tudo; o que houve foi eu nao ter treinado."""
    with sessao() as s:
        s.add(_concurso())

    assert "não treinei" in cliente.get("/").text


def test_a_pior_das_pesadas_e_destacada_na_tela(cliente, com_quadro_do_edital):
    with sessao() as s:
        s.add(_concurso())
    _treinar("Direitos Humanos", acertos=2, erros=8)      # 20%, 15 questoes
    _treinar("Língua Portuguesa", acertos=9, erros=1)     # 90%, 15 questoes

    texto = cliente.get("/").text

    assert "comece por aqui" in texto
    assert "<strong>Direitos Humanos</strong> é onde eu vou pior" in texto


def test_sem_treino_nenhum_a_tela_nao_aponta_materia(cliente, com_quadro_do_edital):
    with sessao() as s:
        s.add(_concurso())

    assert "comece por aqui" not in cliente.get("/").text
