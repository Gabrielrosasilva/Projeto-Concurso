"""A composicao das rodadas que medem: o diagnostico e o simulado (decisao 67).

O que estes testes seguram, um por um, o que foi pedido:
  - a composicao soma o total da faixa;
  - so questao REAL da FEPESE entra - do alvo e do complementar ACEITO -, uma
    por enunciado, sem anulada, com gabarito; questao de IA nunca;
  - assunto sem amostra no alvo cai na frase padrao e na divisao por igual
    entre os assuntos do edital;
  - a composicao e deterministica, e a rodada grava a que usou;
  - os dias passados e os titulos de hoje ficaram intactos no cronograma;
  - o sabado 03/10 mostra a composicao na tela Hoje.

O banco e de fixture: a arvore nasce do programa real do edital de 2019 (o
mesmo arquivo do test_incidencia), e as questoes sao escritas aqui.
"""
import hashlib
import json
from datetime import date
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient
from sqlalchemy import select

from radar import cronograma, edital_programa
from radar.cronograma import Faixa
from radar.db import sessao
from radar.models import QuestaoDeProva, QuestaoGerada, RespostaDeSimulado, Simulado
from radar.origem import FRASE_SEM_EVIDENCIA
from radar.servico import classificacoes, complementar, composicao, conteudos
from radar.servico import fichas as servico_fichas
from radar.web.app import app

PROGRAMA = edital_programa.ler_programa(
    (Path(__file__).parent / "fixtures" / "provas" / "edital_sap_2019_programa.txt")
    .read_text(encoding="utf-8"))

CONFIG = Path(__file__).resolve().parent.parent / "config"

PORTUGUES = "Língua Portuguesa"
RACIOCINIO = "Raciocínio Lógico"
INTERPRETACAO = "Língua Portuguesa > Compreensão e interpretação de texto (s)"
ORTOGRAFIA = "Língua Portuguesa > Ortografia oficial"
CRASE = "Língua Portuguesa > Emprego da crase"
CONJUNTOS = "Raciocínio Lógico > Operações com conjuntos"

ALVO_2013 = "https://fepese.test/ap2013.pdf"
ALVO_2019 = "https://fepese.test/ap2019.pdf"
ACEITA = "https://fepese.test/prefeitura-aceita.pdf"
RECUSADA = "https://fepese.test/prefeitura-recusada.pdf"


def _questao(numero, materia, caminho, prova, *, evidencia="alvo", anulada=False,
             resposta="a", enunciado=None):
    """Grava a questao e a classifica no no `caminho`."""
    with sessao() as s:
        q = QuestaoDeProva(
            prova_url=prova, banca="FEPESE", ano=2019 if "2019" in prova else 2013,
            numero=numero, materia=materia,
            enunciado=enunciado or f"Questão {numero} sobre {caminho}?",
            alternativas={"a": f"certa {numero}", "b": f"errada {numero}"},
            resposta=None if anulada else resposta, anulada=anulada,
            impressao=f"imp-{numero}", evidencia=evidencia)
        s.add(q)
        s.flush()
        chave = classificacoes.chave_de(q)
    classificacoes.classificar(chave, caminho, "manual")


@pytest.fixture
def acervo(banco_temporario):
    """Portugues com amostra so em Interpretacao (3 questoes em 2 provas);
    Raciocinio Logico so de 2019 (uma prova: nenhum assunto tem amostra)."""
    conteudos.semear(programa=PROGRAMA)
    # Interpretacao: 3 do alvo nas duas provas -> tem amostra.
    _questao(1, PORTUGUES, INTERPRETACAO, ALVO_2013)
    _questao(2, PORTUGUES, INTERPRETACAO, ALVO_2013)
    _questao(3, PORTUGUES, INTERPRETACAO, ALVO_2019)
    # A anulada e a sem gabarito nunca entram.
    _questao(4, PORTUGUES, INTERPRETACAO, ALVO_2019, anulada=True)
    # Ortografia: 1 do alvo -> sem amostra.
    _questao(5, PORTUGUES, ORTOGRAFIA, ALVO_2019)
    # O complementar aceito soma estoque; o recusado nao.
    _questao(6, PORTUGUES, CRASE, ACEITA, evidencia="complementar")
    _questao(7, PORTUGUES, CRASE, ACEITA, evidencia="complementar")
    _questao(8, PORTUGUES, INTERPRETACAO, ACEITA, evidencia="complementar")
    _questao(9, PORTUGUES, ORTOGRAFIA, RECUSADA, evidencia="complementar")
    _questao(10, PORTUGUES, ORTOGRAFIA, RECUSADA, evidencia="complementar")
    # Raciocinio Logico: so 2019, dois de conjuntos.
    _questao(11, RACIOCINIO, CONJUNTOS, ALVO_2019)
    _questao(12, RACIOCINIO, CONJUNTOS, ALVO_2019)
    complementar.caminho_do_registro().write_text(json.dumps(
        {"provas": [{"prova_url": ACEITA, "aceita": True},
                    {"prova_url": RECUSADA, "aceita": False}]}), encoding="utf-8")


def _faixa(materia=PORTUGUES, questoes=4, tipo="diagnostico", onde="radar", **mais):
    return Faixa(bloco="noite", tipo=tipo, titulo=f"Diagnóstico de {materia}",
                 materia=materia, questoes=questoes, onde=onde, **mais)


def _assunto(c, caminho):
    return next(a for m in c.materias for a in m.assuntos if a.caminho == caminho)


# --- a conta -------------------------------------------------------------------

def test_a_composicao_soma_o_total_da_faixa(acervo):
    c = composicao.compor([PORTUGUES], 4)
    assert c.pedidas == 4 and c.faltaram == 0


def test_assunto_com_amostra_entra_pela_incidencia_e_o_resto_por_igual(acervo):
    """Das 4 do alvo validas em Portugues, 3 sao de Interpretacao: ela leva 3
    das 4 da rodada; a quarta vai para os assuntos sem amostra, por igual, e
    o desempate e a ordem do edital (Ortografia vem logo depois)."""
    c = composicao.compor([PORTUGUES], 4)
    interpretacao = _assunto(c, INTERPRETACAO)
    assert interpretacao.grupo == composicao.COM_AMOSTRA
    assert interpretacao.alvo == "3 questões · 2 provas"
    assert interpretacao.pedidas == 3
    assert _assunto(c, ORTOGRAFIA).grupo == composicao.SEM_AMOSTRA
    assert _assunto(c, ORTOGRAFIA).pedidas == 1


def test_sem_amostra_e_tudo_pelo_edital_com_a_frase(acervo):
    """Raciocinio Logico so caiu em uma prova: nenhum assunto tem amostra, e
    todos pesam igual (o edital nao da peso dentro da materia)."""
    c = composicao.compor([RACIOCINIO], 2)
    (materia,) = c.materias
    assert not materia.com_amostra
    assert all(a.peso == 1.0 for a in materia.sem_amostra)
    assert materia.alvo == "2 questões · 1 prova"


def test_o_que_falta_num_assunto_vai_para_os_outros_da_materia(acervo):
    """Pelo edital, as 2 iriam para os 2 primeiros assuntos, que nao tem
    questao real classificada: elas vao para Conjuntos, que tem."""
    c = composicao.compor([RACIOCINIO], 2)
    assert _assunto(c, CONJUNTOS).pedidas == 2
    assert c.pedidas == 2 and c.faltaram == 0


def test_sem_questao_na_materia_inteira_falta_mesmo(acervo):
    c = composicao.compor([RACIOCINIO], 5)
    assert c.pedidas == 2 and c.faltaram == 3


def test_o_complementar_recusado_nao_entra_no_estoque(acervo):
    """A Ortografia tem 1 do alvo e 2 de uma prova RECUSADA na 3B: o estoque e 1."""
    c = composicao.compor([PORTUGUES], 4)
    assert _assunto(c, ORTOGRAFIA).estoque == 1
    assert _assunto(c, CRASE).estoque == 2          # o aceito entra


def test_a_composicao_e_deterministica(acervo):
    primeira = composicao.planejar(date(2026, 10, 3), "noite", 0, _faixa())
    segunda = composicao.planejar(date(2026, 10, 3), "noite", 0, _faixa())
    assert (primeira.composicao.como_dicionario()
            == segunda.composicao.como_dicionario())
    contexto = composicao.Contexto.ler()
    c1 = composicao.compor([PORTUGUES], 4, contexto=contexto)
    c2 = composicao.compor([PORTUGUES], 4, contexto=contexto)
    ids1 = [q.id for q in composicao.escolher(c1, contexto.estoque, "03/10|noite|0")]
    ids2 = [q.id for q in composicao.escolher(c2, contexto.estoque, "03/10|noite|0")]
    assert ids1 == ids2


def test_varias_materias_se_dividem_pelo_peso_do_edital(acervo):
    """A conta do 07/11: o total se divide entre as materias pelo quadro."""
    c = composicao.compor([PORTUGUES, RACIOCINIO], 5,
                          pesos={PORTUGUES: 15, RACIOCINIO: 10})
    por_materia = {m.materia: m.total for m in c.materias}
    assert por_materia == {PORTUGUES: 3, RACIOCINIO: 2}


# --- a rodada --------------------------------------------------------------------

def _rodada(simulado_id):
    with sessao() as s:
        simulado = s.get(Simulado, simulado_id)
        respostas = list(s.scalars(select(RespostaDeSimulado)
                                   .where(RespostaDeSimulado.simulado_id == simulado_id)))
        questoes = [s.get(QuestaoDeProva, r.questao_id) for r in respostas]
        return simulado, respostas, questoes


def test_so_questao_real_da_fepese_aceita_entra_na_rodada(acervo):
    simulado = composicao.criar_rodada(date(2026, 10, 3), "noite", 0, _faixa(questoes=6))
    _, respostas, questoes = _rodada(simulado.id)

    assert len(respostas) == 6
    assert all(not r.gerada for r in respostas)
    assert all(q.banca == "FEPESE" for q in questoes)
    assert all(q.prova_url != RECUSADA for q in questoes)
    assert all(not q.anulada and q.resposta for q in questoes)
    assert len({q.impressao for q in questoes}) == len(questoes)   # um por enunciado


def test_questao_de_ia_nunca_entra_na_rodada_que_mede(acervo):
    """A gerada existe, na mesma materia, e mesmo assim nao entra: a rodada que
    mede so le a tabela das questoes reais."""
    with sessao() as s:
        s.add(QuestaoGerada(materia=PORTUGUES, enunciado="Questão da IA?",
                            alternativas={"a": "x", "b": "y"}, resposta="a",
                            impressao="ia-1", modelo="teste", modo="do_zero"))
    simulado = composicao.criar_rodada(date(2026, 10, 3), "noite", 0, _faixa(questoes=4))
    _, respostas, questoes = _rodada(simulado.id)
    assert all(not r.gerada for r in respostas)
    assert "Questão da IA?" not in {q.enunciado for q in questoes}


def test_a_rodada_grava_a_composicao_e_nao_e_recriada(acervo):
    faixa = _faixa(questoes=4)
    primeira = composicao.criar_rodada(date(2026, 10, 3), "noite", 0, faixa)
    segunda = composicao.criar_rodada(date(2026, 10, 3), "noite", 0, faixa)
    assert primeira.id == segunda.id
    simulado, _, _ = _rodada(primeira.id)
    gravada = simulado.filtros["composicao"]
    assert gravada["regra"] == composicao.REGRA
    assert sum(a["pedidas"] for m in gravada["materias"] for a in m["assuntos"]) == 4
    assert simulado.filtros["faixa"]["titulo"] == faixa.titulo


def test_faixa_que_nao_mede_nao_cria_rodada(acervo):
    """O simulado do Qconcursos e a revisao que refaz erros nao saem por aqui."""
    assert not composicao.mede(_faixa(tipo="simulado", onde="qconcursos"))
    assert not composicao.mede(_faixa(tipo="revisao"))
    assert composicao.criar_rodada(
        date(2026, 10, 3), "noite", 0, _faixa(tipo="revisao")) is None


# --- o cronograma real ----------------------------------------------------------

# A impressao dos dias ANTES de 03/10, tirada do arquivo antes desta etapa: os
# checks sao reconhecidos por bloco, posicao e titulo, e mudar um dia passado
# apagaria o que foi feito.
IMPRESSAO_ANTES_DE_03_10 = "88b9cee0fe10d8a2a537eb8daf076f9fb589e36c5362b9eb2cf221697007c417"

TITULOS = {
    "2026-10-03": [("manha", ["Diagnóstico de Raciocínio Lógico", "Pausa", "Revisão semanal"]),
                   ("noite", ["Diagnóstico de Português", "Pausa",
                              "Mini-simulado da semana", "Correção"]),
                   ("pos22", ["Anki: só os vencidos"])],
    # Os diagnosticos de 03/10 passaram para 10/10, e o R+7 deles para 17/10
    # (decisao 105).
    "2026-10-10": [("manha", ["Princípios de contagem", "Pausa", "Revisão semanal",
                              "Diagnóstico de Raciocínio Lógico"]),
                   ("noite", ["Simulado da semana", "Pausa", "Diagnóstico de Português",
                              "Correção do simulado e dos diagnósticos"]),
                   ("pos22", ["Anki: só os vencidos"])],
    "2026-10-17": [("manha", ["Probabilidade", "Pausa", "Revisão semanal",
                              "R+7: princípios de contagem",
                              "R+7: refazer os erros dos diagnósticos"]),
                   ("noite", ["Simulado da semana", "Pausa", "Raciocínio Lógico: probabilidade",
                              "Correção do simulado"]),
                   ("pos22", ["Anki: só os vencidos"])],
    "2026-10-24": [("manha", ["Conjuntos e diagramas lógicos", "Pausa", "Revisão semanal",
                              "R+7: probabilidade"]),
                   ("noite", ["Simulado da semana", "Pausa",
                              "Raciocínio Lógico: conjuntos e diagramas lógicos",
                              "Correção do simulado"]),
                   ("pos22", ["Anki: só os vencidos"])],
    "2026-10-31": [("manha", ["Argumentação e quantificadores", "Pausa", "Revisão semanal",
                              "R+7: conjuntos e diagramas lógicos", "R+30: Teoria geral"]),
                   ("noite", ["Simulado da semana", "Pausa",
                              "Raciocínio Lógico: argumentação e quantificadores",
                              "Correção do simulado"]),
                   ("pos22", ["Anki: só os vencidos"])],
    "2026-11-07": [("manha", ["Problemas aritméticos e geométricos", "Pausa",
                              "Revisão semanal", "R+7: argumentação e quantificadores",
                              "R+30: Afirmação histórica e dimensões (gerações)"]),
                   ("noite", ["Simulado de fechamento do Ciclo 1", "Correção"]),
                   ("pos22", ["Anki: só os vencidos"])],
}


def test_os_dias_antes_de_hoje_nao_mudaram():
    dados = yaml.safe_load((CONFIG / "cronograma.yml").read_text(encoding="utf-8"))
    antes = [d for d in dados["dias"] if str(d["data"]) < "2026-10-03"]
    impressao = hashlib.sha256(json.dumps(
        antes, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()
    assert impressao == IMPRESSAO_ANTES_DE_03_10


def test_os_titulos_dos_sabados_nao_mudaram():
    dados = yaml.safe_load((CONFIG / "cronograma.yml").read_text(encoding="utf-8"))
    for data, blocos in TITULOS.items():
        dia = next(d for d in dados["dias"] if str(d["data"]) == data)
        for bloco, titulos in blocos:
            assert [f["titulo"] for f in dia[bloco]] == titulos, (data, bloco)


def test_o_cronograma_real_tem_as_tres_faixas_que_medem_e_sem_numero_a_mao():
    plano = cronograma.carregar(CONFIG / "cronograma.yml")
    medem = [(d.data, f) for d in plano.dias for f in d.faixas() if composicao.mede(f)]
    assert [(d.isoformat(), f.titulo) for d, f in medem] == [
        ("2026-10-03", "Diagnóstico de Raciocínio Lógico"),
        ("2026-10-03", "Diagnóstico de Português"),
        ("2026-10-10", "Diagnóstico de Raciocínio Lógico"),
        ("2026-10-10", "Diagnóstico de Português"),
        ("2026-11-07", "Simulado de fechamento do Ciclo 1")]
    for _, faixa in medem:
        assert "Radar > Simulado" not in (faixa.detalhe or "")
    fechamento = medem[-1][1]
    assert len(fechamento.materias_da_rodada) == 6


def test_materia_desconhecida_na_rodada_e_erro(tmp_path):
    texto = (CONFIG / "cronograma.yml").read_text(encoding="utf-8").replace(
        "    - Direito Penal\n    - Lei de Execução Penal\n",
        "    - Direito Penal\n    - Lei de Execucao Penall\n", 1)
    arquivo = tmp_path / "cronograma.yml"
    arquivo.write_text(texto, encoding="utf-8")
    with pytest.raises(cronograma.ErroNoCronograma, match="materias_da_rodada"):
        cronograma.carregar(arquivo)


# --- a tela ---------------------------------------------------------------------

def test_o_sabado_03_10_mostra_a_composicao_e_o_botao(acervo):
    pagina = TestClient(app).get("/hoje?data=2026-10-03").text

    assert pagina.count('class="composicao"') == 2          # os dois diagnosticos
    assert "Só questões: não há o que estudar nesta faixa." in pagina
    assert "Compreensão e interpretação de texto" in pagina
    assert FRASE_SEM_EVIDENCIA in pagina                    # Raciocinio Logico
    assert "Criar a rodada com esta composição" in pagina
    assert "ds-selo--automatico" in pagina and "ds-selo--acervo" in pagina


def test_o_botao_cria_a_rodada_e_a_faixa_passa_a_abrir_ela(acervo):
    cliente = TestClient(app)
    resposta = cliente.post("/hoje/rodada", data={"data": "2026-10-03", "bloco": "noite",
                                                  "indice": "0"}, follow_redirects=False)
    assert resposta.status_code == 303
    assert resposta.headers["location"].startswith("/simulado/")

    pagina = cliente.get("/hoje?data=2026-10-03").text
    assert "Abrir a rodada desta faixa" in pagina


# --- o simulado do Qconcursos (decisao 69) ----------------------------------------

DO_SABADO = ["Direito Penal", "Direito Constitucional", "Lei de Execução Penal",
             "Direitos Humanos", PORTUGUES]
PESOS_DO_EDITAL = {PORTUGUES: 15, "Direitos Humanos": 15, "Direito Constitucional": 5,
                   "Direito Penal": 5, "Lei de Execução Penal": 10}


@pytest.fixture
def plano():
    return cronograma.carregar(CONFIG / "cronograma.yml")


def test_o_simulado_do_qconcursos_soma_o_total_pelo_peso_do_edital(acervo, plano):
    c = composicao.compor_por_tema(date(2026, 10, 10), DO_SABADO, 30, plano,
                                   pesos=PESOS_DO_EDITAL)
    assert c.pedidas == 30
    assert sorted(m.total for m in c.materias) == [3, 3, 6, 9, 9]
    assert all(m.pedidas == m.total for m in c.materias)
    assert c.regra == composicao.REGRA_DO_QCONCURSOS


def test_so_entram_os_temas_estudados_antes_do_dia(acervo, plano):
    """No 03/10, Penal so tem a aplicacao da lei penal (28/09): o fato tipico
    e de 05/10, depois do sabado."""
    c = composicao.compor_por_tema(date(2026, 10, 3), ["Direito Penal"], 2, plano)
    (materia,) = c.materias
    assert [a.nome for a in materia.assuntos] == ["Aplicação da lei penal (arts. 1º a 12)"]
    assert materia.assuntos[0].pedidas == 2
    assert materia.assuntos[0].filtro.startswith("Direito Penal > ")


def test_tema_sem_no_cai_na_frase_e_no_empate_vai_o_mais_recente(acervo, plano):
    """Sem ficha no banco do teste, nenhum tema tem no: todos ficam sem amostra
    e pesam igual. Sao 10 temas de Portugues antes de 10/10 para 9 questoes, e
    o que fica sem questao e o mais antigo."""
    c = composicao.compor_por_tema(date(2026, 10, 10), [PORTUGUES], 9, plano)
    (materia,) = c.materias
    assert not materia.com_amostra
    assert all(a.peso == 1.0 and "não tem nó" in a.alvo for a in materia.sem_amostra)
    datas = [a.estudado_em for a in materia.assuntos]
    assert datas == sorted(datas, reverse=True)
    assert [a.estudado_em for a in materia.assuntos if not a.pedidas] == [min(datas)]


def test_tema_com_ficha_e_amostra_entra_pela_incidencia(acervo, plano):
    """A ficha da Interpretacao 1 aponta para o no de Interpretacao, com 3
    questoes do alvo em 2 provas: o tema tem amostra. Das 4 validas do alvo em
    Portugues, 3 caem nele e 1 fica para os temas sem amostra - o resto da
    incidencia da materia: das 9 questoes, 7 e 2."""
    servico_fichas.caminho_do_arquivo().write_text(json.dumps([{
        "tema": "Interpretação 1: o método", "materia": PORTUGUES,
        "nos": [INTERPRETACAO], "modelo": "teste", "criado_em": "2026-09-27"}]),
        encoding="utf-8")
    c = composicao.compor_por_tema(date(2026, 10, 10), [PORTUGUES], 9, plano)
    (materia,) = c.materias
    (interpretacao,) = materia.com_amostra
    assert interpretacao.nome == "Interpretação 1: o método"
    assert interpretacao.alvo == "3 questões · 2 provas"
    assert interpretacao.pedidas == 7
    assert sum(a.pedidas for a in materia.sem_amostra) == 2


def test_materia_sem_tema_estudado_fica_fora_da_divisao(acervo, plano):
    """Direitos Humanos so comeca em 01/10: no 30/09 ela nao divide nada."""
    c = composicao.compor_por_tema(date(2026, 9, 30), ["Direito Penal", "Direitos Humanos"],
                                   4, plano, pesos={"Direito Penal": 5, "Direitos Humanos": 15})
    assert c.fora == ["Direitos Humanos"]
    assert [m.total for m in c.materias] == [4] and c.pedidas == 4


def test_a_composicao_do_qconcursos_e_deterministica(acervo, plano):
    def pares():
        c = composicao.compor_por_tema(date(2026, 10, 31), DO_SABADO, 40, plano,
                                       pesos=PESOS_DO_EDITAL)
        return [(a.nome, a.pedidas) for m in c.materias for a in m.assuntos]
    assert pares() == pares()


def test_os_simulados_de_sabado_nao_tem_numero_escrito_a_mao(plano):
    no_site = [(d.data, f) for d in plano.dias for f in d.faixas()
               if f.tipo == "simulado" and f.onde == "qconcursos"]
    assert [d.isoformat() for d, _ in no_site] == [
        "2026-10-03", "2026-10-10", "2026-10-17", "2026-10-24", "2026-10-31"]
    for _, faixa in no_site:
        assert composicao.no_qconcursos(faixa)
        assert not any(c.isdigit() for c in faixa.detalhe), faixa.detalhe


def test_o_sabado_10_10_mostra_a_composicao_do_qconcursos_sem_botao(acervo, monkeypatch):
    monkeypatch.setattr(composicao, "_pesos_do_edital", lambda materias: PESOS_DO_EDITAL)
    pagina = TestClient(app).get("/hoje?data=2026-10-10").text
    inicio = pagina.index('class="composicao no-qconcursos"')
    bloco = pagina[inicio:pagina.index("</div>", inicio)]
    assert "Só questões: não há o que estudar nesta faixa." in bloco
    assert "30 questões divididas entre as matérias pelo peso do edital" in bloco
    assert "Filtro: Direito Penal &gt; fato típico" in bloco
    assert FRASE_SEM_EVIDENCIA in bloco
    assert "Criar a rodada" not in bloco
