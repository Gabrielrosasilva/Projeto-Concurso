"""Os criterios de aceite da secao 23 do novo.md (Etapa 8), um por um.

Cada teste e um item da §23, com dado fixo: nenhum vai a internet nem depende
de hoje. O banco e montado no proprio teste - o "banco de fixture" -, com os
mesmos construtores que as etapas ja usavam (a ficha do Art. 5º da 6B, a
arvore da 5, o acervo complementar da 3B, o banco antigo da 2, o cronograma
real da 6A, a varredura da 7A): o aceite confere o CONJUNTO, e o mesmo dado
tem de passar por todas as promessas de uma vez.

O resultado com o banco real, item por item, esta no docs/auditoria_final.md.
"""
import re
from datetime import date
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from radar import cronograma, migracoes, origem
from radar.cli import app as cli
from radar.models import Conteudo
from radar.db import sessao
from radar.servico import estudo, geradas, manual, materias, metricas
from radar.servico import complementar as servico_complementar
from radar.servico import incidencia as servico_da_incidencia
from radar.web.app import app
from tests.test_complementar import acervo  # noqa: F401 - fixture
from tests.test_fichas import (  # noqa: F401 - fixtures
    CASA_XI,
    arvore_no_banco,
    com_ficha_real,
    _montar,
)
from tests.test_geracao_por_conteudo import _gravar, _importar, _item, _questao
from tests.test_metricas import _as_21h
from tests.test_migracoes import _tabelas, banco_antigo  # noqa: F401 - fixture
from tests.test_foco import com_quadro_do_edital  # noqa: F401 - fixture da varredura
from tests.test_varredura_das_telas import (  # noqa: F401 - fixture
    ENUNCIADO_DE_IA,
    PREVISAO,
    _tem_amostra,
    _visivel,
    telas,
)

SEG = date(2026, 9, 28)


# =============================================================================
# 1. A ficha responde as 12 perguntas da §23
# =============================================================================
#
# "Hoje preciso estudar Direito Constitucional -> Direitos Fundamentais ->
# Art. 5º -> incisos I a XVI": a ficha do tema, montada com a arvore, o acervo
# (alvo e complementar), o plano e o texto escrito da fixture da 6B, com uma
# gerada e um erro para revisar no escopo.

@pytest.fixture
def ficha():
    gerada = SimpleNamespace(conteudo=CASA_XI, enunciado="gerada sobre a casa como asilo")
    refazer = estudo.Refazer(do_radar=[101],
                             do_caderno=[SimpleNamespace(regra="de dia, só com ordem judicial")])
    return _montar(data=date(2026, 10, 6), geradas=[gerada], refazer=lambda dentro: refazer)


#: (a pergunta da §23, o que a ficha responde)
PERGUNTAS_DA_FICHA = [
    ("exatamente o que ler", lambda f: f.ler_exatamente.texto),
    ("onde ler", lambda f: f.fonte.link),
    ("como procurar", lambda f: f.como_pesquisar),
    ("o que preciso entender", lambda f: f.entender),
    ("o que preciso memorizar", lambda f: f.memorizar),
    ("quais pegadinhas observar", lambda f: f.pegadinhas_do_acervo and f.pegadinhas_escritas),
    ("como a FEPESE cobrou", lambda f: f.linha_do_alvo.amostra and f.linha_complementar),
    ("quais questões reais estão relacionadas", lambda f: f.questoes_reais),
    ("quantas questões devo fazer", lambda f: f.meta_de_questoes),
    ("quais questões geradas posso fazer", lambda f: f.geradas),
    ("quais erros devo revisar depois", lambda f: f.refazer.do_radar and f.refazer.do_caderno),
    ("por que esse conteúdo foi priorizado hoje", lambda f: f.por_que_agora),
]


def test_sao_as_doze_perguntas_da_secao_23():
    assert len(PERGUNTAS_DA_FICHA) == 12


@pytest.mark.parametrize("pergunta, resposta", PERGUNTAS_DA_FICHA,
                         ids=[p for p, _r in PERGUNTAS_DA_FICHA])
def test_a_ficha_responde(ficha, pergunta, resposta):
    assert resposta(ficha), pergunta


def test_a_ficha_responde_com_a_origem_de_cada_resposta(ficha):
    """Cada resposta diz de onde veio (secao 20): a lei e oficial, o acervo e
    estatistica, o texto e da IA, o porque mistura plano e conta."""
    assert ficha.fonte.origem == origem.OFICIAL
    assert ficha.ler_exatamente.origem == origem.IA
    assert ficha.origens["questoes_reais"] == origem.ACERVO
    assert ficha.origens["geradas"] == origem.IA
    assert {m.origem for m in ficha.por_que_agora} >= {origem.PLANO, origem.OFICIAL,
                                                        origem.ACERVO, origem.AUTOMATICO}


def test_o_porque_de_hoje_e_o_dia_do_cronograma(ficha):
    assert ficha.por_que_agora[0].texto.startswith("O cronograma de 06/10 traz este tema")


def test_a_tela_da_ficha_mostra_as_doze_partes(com_ficha_real):
    """A mesma ficha, na tela, com o cronograma real: cada pergunta tem a sua
    parte, e nenhuma fala em previsao."""
    html = TestClient(app).get("/fichas/art-5o-caput-e-incisos-i-a-xvi?data=2026-10-06").text
    for parte in ("Ler exatamente", "Fonte principal", "Como pesquisar",
                  "Você precisa entender", "Você precisa memorizar", "Pegadinhas",
                  "Como a FEPESE cobrou", "Questões reais relacionadas",
                  "Quantas questões fazer", "Questões geradas por IA neste conteúdo",
                  "Erros para revisar depois", "Por que agora"):
        assert parte in html, parte
    assert not PREVISAO.search(_visivel(html))


# =============================================================================
# 2. Selecionar materia > assunto > subassunto > elemento para gerar
# =============================================================================
#
# Os dois exemplos da §23, numa arvore de fixture que tem os dois caminhos e,
# ao lado de cada um, um vizinho com questao real - para provar que o vizinho
# nao entra. (Na arvore real os dois caminhos nao existem: ver o
# docs/auditoria_final.md.)

PENAL = "Direito Penal"
APLICACAO = f"{PENAL} > Aplicação da lei penal"
NO_TEMPO = f"{APLICACAO} > Lei penal no tempo"
NO_ESPACO = f"{APLICACAO} > Lei penal no espaço"
IMPUTABILIDADE = f"{PENAL} > Imputabilidade penal"
LEP = "Lei de Execução Penal"
PROGRESSAO = f"{LEP} > Progressão de regime"
ART_112 = f"{PROGRESSAO} > LEP, art. 112"
REMICAO = f"{LEP} > Remição"


@pytest.fixture
def arvore_da_secao_23(banco_temporario):
    with sessao() as s:
        for caminho, nivel in [(PENAL, "materia"), (APLICACAO, "assunto"),
                               (NO_TEMPO, "subassunto"), (NO_ESPACO, "subassunto"),
                               (IMPUTABILIDADE, "assunto"), (LEP, "materia"),
                               (PROGRESSAO, "assunto"), (ART_112, "elemento"),
                               (REMICAO, "assunto")]:
            partes = caminho.split(" > ")
            s.add(Conteudo(caminho=caminho, pai=" > ".join(partes[:-1]) or None,
                           nivel=nivel, nome=partes[-1], origem="edital",
                           procedencia="teste"))
    # Uma questao real em cada no: os pedidos tem base dos dois lados.
    for numero, (no, materia) in enumerate([(NO_TEMPO, PENAL), (NO_ESPACO, PENAL),
                                            (IMPUTABILIDADE, PENAL), (ART_112, LEP),
                                            (REMICAO, LEP)], start=1):
        _gravar(_questao(numero, materia=materia,
                         texto=f"questão real {numero} de {materia}?"), no)


def _escopo(materia, assunto=None, subassunto=None, elementos=None):
    from radar import conteudos as arvore
    from radar.servico import conteudos as servico_conteudos

    return arvore.resolver_escopo(servico_conteudos.caminhos(), materia, assunto,
                                  subassunto, elementos)


@pytest.mark.parametrize("materia, assunto, subassunto, elementos, dentro", [
    (PENAL, "Aplicação da lei penal", "Lei penal no tempo", None, {NO_TEMPO}),
    (LEP, "Progressão de regime", None, ["LEP, art. 112"], {PROGRESSAO, ART_112}),
], ids=["20 questões: Direito Penal > Aplicação da lei penal > Lei penal no tempo",
        "20 questões: LEP > Progressão de regime > Art. 112"])
def test_os_dois_pedidos_da_secao_23_nao_saem_do_escopo(
        arvore_da_secao_23, materia, assunto, subassunto, elementos, dentro):
    escopo = _escopo(materia, assunto, subassunto, elementos)

    plano = geradas.preparar(quantas=20, escopo=escopo, semente=1)

    assert plano["quantas"] == 20
    # Toda questao pedida e de dentro do escopo, e a base real tambem.
    assert {p["conteudo"] for p in plano["pedidos"]} <= dentro
    reais = [p for p in plano["pedidos"] if p["base"] == "questao_real"]
    assert reais, "a questao real do no tinha de servir de base"
    lote = manual.pedido_de_questoes(quantas=20, escopo=escopo)
    assert all("ESCOPO FECHADO" in p["instrucao"] for p in lote["pedidos"])


def test_a_resposta_fora_do_escopo_nao_entra(arvore_da_secao_23, tmp_path):
    """Mesmo que a IA mande questao do vizinho, a importacao recusa."""
    escopo = _escopo(PENAL, "Aplicação da lei penal", "Lei penal no tempo")
    lote = manual.pedido_de_questoes(quantas=3, escopo=escopo)

    resultado = _importar(tmp_path, lote, [
        _item(conteudo=NO_TEMPO, artigo="CP, art. 2º",
              enunciado="Dentro: a lei nova mais benéfica retroage?"),
        _item(conteudo=NO_ESPACO, artigo="CP, art. 5º",
              enunciado="Fora: a territorialidade vale para o navio?"),
        _item(conteudo=IMPUTABILIDADE, artigo="CP, art. 26",
              enunciado="Fora: o inimputável por doença mental responde?"),
    ])

    assert resultado["gravadas"] == 1
    assert len(resultado["recusas"]) == 2


def test_nome_que_a_arvore_nao_tem_nao_alarga_o_escopo(arvore_da_secao_23):
    from radar import conteudos as arvore

    with pytest.raises(arvore.EscopoInvalido, match="Você quis dizer"):
        _escopo(PENAL, "Aplicacao da lei", "Lei penal no tempo")


# =============================================================================
# 3. Os seis itens finais da §23
# =============================================================================

# --- os numeros de questoes, acertos e erros sao iguais em todas as telas ----

def _linha_da_conta(texto: str) -> str:
    """A linha "N questões = A acertos + E erros + ...", como a tela escreve."""
    achado = re.search(r"\d+ questões = \d+ acertos \+ \d+ erros(?: \+ [^+·.]+?)*(?=\s*[·.]|\s*$)",
                       _visivel(texto))
    assert achado, "a tela nao escreveu a linha da conta"
    return achado.group(0).strip()


def test_os_numeros_sao_iguais_em_todas_as_telas(banco_temporario, monkeypatch):
    """O mesmo dia (28/09, o primeiro do Ciclo 1) na tela Hoje, no `radar
    hoje`, na tela Semanas e na soma dos cartoes de Minhas materias."""
    from radar.servico import cronograma as diario
    from radar.util import fuso_local
    from tests.test_materias_na_tela import _anotar as anotar_na_materia
    from tests.test_materias_na_tela import _responder as responder_na_materia

    monkeypatch.setattr(diario, "agora_local",
                        lambda: _as_21h(date(2026, 10, 1)).astimezone(fuso_local()))
    real = cronograma.carregar()
    anotar_na_materia(real, SEG, "Direito Penal", 11, 6)
    anotar_na_materia(real, SEG, "Língua Portuguesa", 10, 7)
    for n in range(10):
        responder_na_materia("Direito Penal", n < 7, _as_21h(minuto=n), gerada=True)
    responder_na_materia("Língua Portuguesa", False, _as_21h(minuto=20))

    cliente = TestClient(app)
    hoje = _linha_da_conta(cliente.get("/hoje?data=2026-09-28").text)
    semanas = _linha_da_conta(cliente.get("/semanas").text)
    terminal = CliRunner().invoke(cli, ["hoje", "--data", "2026-09-28"], env={"COLUMNS": "200"})
    assert terminal.exit_code == 0, terminal.output

    assert hoje == "32 questões = 13 acertos + 9 erros + 10 de treino de IA"
    assert semanas == hoje
    assert hoje in terminal.output
    cartoes, _ = materias.montar(real, hoje=date(2026, 10, 1))
    soma = metricas.Numeros()
    for cartao in cartoes:
        soma = soma + cartao.geral
    assert metricas.frase_da_conta(soma) == hoje


# --- a incidencia do alvo nunca muda por causa de prova complementar --------

def test_a_incidencia_do_alvo_nao_muda_com_a_prova_complementar(acervo):
    antes = {m.materia: (m.topo.amostra, m.topo.rotulo) for m in servico_da_incidencia.mapa()}

    servico_complementar.aplicar(hoje=date(2026, 10, 1))     # a prova entra no acervo

    depois = {m.materia: (m.topo.amostra, m.topo.rotulo) for m in servico_da_incidencia.mapa()}
    assert servico_complementar.provas_aceitas()              # entrou mesmo
    assert depois == antes


# --- nenhum dado antigo foi perdido ------------------------------------------

def test_nenhum_dado_antigo_e_perdido_na_migracao(banco_antigo):
    antes = _tabelas(banco_antigo)

    relatorio = migracoes.migrar()

    depois = _tabelas(banco_antigo)
    assert {tabela: depois[tabela] for tabela in antes} == antes
    assert relatorio.perdidas == {}


# --- o ANKI desativado, mas reativavel ---------------------------------------

def test_o_anki_esta_desativado_e_religa_no_arquivo_real(tmp_path):
    """No config/cronograma.yml real a chave diz desativado; trocada por
    ativado, numa copia, a faixa do Anki volta com o tempo dela."""
    from radar import config

    real = config.diretorio_config() / "cronograma.yml"
    texto = real.read_text(encoding="utf-8")
    # A chave, no comeco da linha - um comentario do arquivo tambem cita o nome.
    assert len(re.findall(r"(?m)^anki: desativado$", texto)) == 1
    dia = date(2026, 10, 5)                           # um dia util depois da 6A

    desligado = cronograma.montar_dia(cronograma.carregar(real), dia, 1)
    copia = tmp_path / "cronograma.yml"
    copia.write_text(re.sub(r"(?m)^anki: desativado$", "anki: ativado", texto), encoding="utf-8")
    religado = cronograma.montar_dia(cronograma.carregar(copia), dia, 1)

    anki_desligado = [f for f in desligado.pos22 if f.tipo == "anki"]
    anki_religado = [f for f in religado.pos22 if f.tipo == "anki"]
    assert anki_desligado and all(f.desligada for f in anki_desligado)
    assert anki_religado and not any(f.desligada for f in anki_religado)
    assert all(f.duracao > 0 for f in anki_religado)


# --- nenhuma estatistica sem amostra -----------------------------------------

def test_nenhuma_estatistica_aparece_sem_amostra(telas):
    sem_amostra = []
    for endereco, html in telas.items():
        texto = _visivel(html)
        for achado in re.finditer(r"\d+(?:,\d+)?\s?%", texto):
            if not _tem_amostra(texto, achado.start(), achado.end()):
                sem_amostra.append((endereco, achado.group(0)))
    assert not sem_amostra, sem_amostra


# --- nenhuma questao gerada aparece como oficial ------------------------------

def test_nenhuma_questao_gerada_aparece_como_oficial(telas):
    com_gerada = [e for e, html in telas.items() if ENUNCIADO_DE_IA in html]
    assert com_gerada
    for endereco in com_gerada:
        html = telas[endereco]
        assert "🟣" in html and origem.FRASE_DA_QUESTAO_DE_IA in html, endereco
        # E a resposta dela nunca leva o selo do gabarito oficial.
        assert "Gabarito definitivo" not in html, endereco
