"""A arvore de conteudos e as classificacoes (Etapa 2).

A semente e a fixture do edital de 2019 (`edital_sap_2019_programa.txt`), o
texto real do anexo de programas. Nada aqui vai a internet nem le o banco
real: o banco e o temporario, e o data/ tambem.
"""
import json
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import select

from radar import acervo, cronograma, edital_programa
from radar import conteudos as arvore
from radar.db import sessao
from radar.models import Classificacao, Conteudo, ErroAnotado, QuestaoDeProva, QuestaoGerada
from radar.servico import classificacoes, conteudos
from radar.servico import cronograma as diario

FIXTURES = Path(__file__).parent / "fixtures"
PROGRAMA = edital_programa.ler_programa(
    (FIXTURES / "provas" / "edital_sap_2019_programa.txt").read_text(encoding="utf-8"))
MINI = FIXTURES / "cronograma_mini.yml"

PENAL = "Direito Penal"
IMPUTABILIDADE = "Direito Penal > Imputabilidade penal"
DH_ONU = "Direitos Humanos > Regras mínimas da ONU para o tratamento de pessoas presas"


@pytest.fixture
def semeada(banco_temporario):
    conteudos.semear(programa=PROGRAMA)


# --- a semente ---------------------------------------------------------------------

def test_a_semente_da_as_onze_materias_e_os_assuntos_literais():
    nos = arvore.semente(PROGRAMA, arvore.carregar_taxonomia())

    do_edital = [n for n in nos if n.nivel == "materia" and not n.fora_do_edital]
    assert len(do_edital) == 11
    assuntos = [n for n in nos if n.nivel == "assunto"]
    assert len(assuntos) == sum(len(v) for v in PROGRAMA.values()) == 85
    onu = next(n for n in assuntos if n.caminho == DH_ONU)
    assert onu.texto_do_edital == "Regras mínimas da ONU para o tratamento de pessoas presas"
    assert onu.origem == "edital" and "2019" in onu.procedencia
    # Os defeitos do edital ficam: ele escreveu "espécies" como item sozinho.
    assert "Direito Processual Penal > espécies" in {n.caminho for n in assuntos}


def test_as_materias_de_2013_fora_do_edital_entram_marcadas():
    nos = arvore.semente(PROGRAMA, arvore.carregar_taxonomia())
    fora = {n.nome: n for n in nos if n.fora_do_edital}
    assert set(fora) == {"Noções de Informática", "Direito Administrativo"}
    assert all(n.origem == "manual" and "2013" in n.procedencia for n in fora.values())


def test_semear_de_novo_nao_duplica_e_o_json_reconstroi(semeada, tmp_path):
    assert conteudos.semear(programa=PROGRAMA) == 0
    antes = conteudos.caminhos()
    assert len(antes) == 98

    # Banco refeito do zero: a arvore volta do data/conteudos.json.
    with sessao() as s:
        s.execute(Conteudo.__table__.delete())
    assert conteudos.caminhos() == []
    assert conteudos.semear() == 98
    assert conteudos.caminhos() == antes


# --- os niveis e a taxonomia ---------------------------------------------------------

def test_os_niveis_de_baixo_sao_opcionais_e_o_elemento_tem_tipo(semeada):
    sub = conteudos.adicionar(IMPUTABILIDADE, "Inimputáveis")
    assert sub.nivel == "subassunto"
    elemento = conteudos.adicionar(sub.caminho, "CP, art. 26", tipo_elemento="artigo",
                                   referencia="CP, art. 26")
    assert elemento.nivel == "elemento"
    assert elemento.caminho == IMPUTABILIDADE + " > Inimputáveis > CP, art. 26"

    with pytest.raises(arvore.ConteudoInvalido, match="precisa de tipo"):
        conteudos.adicionar(sub.caminho, "CP, art. 27")
    with pytest.raises(arvore.ConteudoInvalido, match="último nível"):
        conteudos.adicionar(elemento.caminho, "abaixo do elemento")
    with pytest.raises(arvore.ConteudoInvalido, match="já existe"):
        conteudos.adicionar(IMPUTABILIDADE, "Inimputáveis")
    with pytest.raises(arvore.ConteudoInvalido, match="não pode ter"):
        conteudos.adicionar(PENAL, "Um > dois")


def test_o_tipo_de_elemento_segue_a_familia_da_materia(semeada):
    sub = conteudos.adicionar("Língua Portuguesa > Emprego da crase", "Casos proibidos")
    conteudos.adicionar(sub.caminho, "Antes de verbo", tipo_elemento="crase")
    with pytest.raises(arvore.ConteudoInvalido, match="não é tipo de elemento"):
        # "artigo" e do Direito, nao do Portugues.
        conteudos.adicionar(sub.caminho, "Art. 5º", tipo_elemento="artigo")


def test_tipo_novo_no_yml_funciona_sem_migracao(semeada, tmp_path):
    original = (Path(__file__).parents[1] / "config" / "taxonomia.yml").read_text(encoding="utf-8")
    nova = tmp_path / "taxonomia.yml"
    nova.write_text(original.replace("    - procedimento\n",
                                     "    - procedimento\n    - macete de prova\n"),
                    encoding="utf-8")
    taxonomia = arvore.carregar_taxonomia(nova)
    sub = conteudos.adicionar(IMPUTABILIDADE, "Menoridade")

    no = conteudos.adicionar(sub.caminho, "Idade do art. 27", tipo_elemento="macete de prova",
                             taxonomia=taxonomia)
    assert no.tipo_elemento == "macete de prova"


# --- as classificacoes ------------------------------------------------------------------

def test_classificacao_sem_procedencia_e_recusada(semeada):
    for vazia in (None, "", "   "):
        with pytest.raises(classificacoes.ClassificacaoInvalida, match="procedência"):
            classificacoes.classificar("q1", IMPUTABILIDADE, vazia)


def test_o_status_sai_da_arvore(semeada):
    assert classificacoes.classificar("q1", IMPUTABILIDADE, "manual").status == "completa"
    conteudos.adicionar(IMPUTABILIDADE, "Inimputáveis")
    assert classificacoes.classificar("q2", IMPUTABILIDADE, "manual").status == "parcial"
    assert classificacoes.classificar("q3", PENAL, "manual").status == "pendente"
    with pytest.raises(classificacoes.ClassificacaoInvalida, match="completa e parcial"):
        classificacoes.classificar("q4", IMPUTABILIDADE, "manual", status="completa")
    with pytest.raises(classificacoes.ClassificacaoInvalida, match="não está na árvore"):
        classificacoes.classificar("q5", PENAL + " > Inventado", "manual")


def test_uma_principal_por_questao_e_a_outra_fica_associada(semeada):
    classificacoes.classificar("q1", IMPUTABILIDADE, "manual")
    classificacoes.classificar("q1", "Direito Penal > Crimes contra a Administração Pública",
                               "manual")
    with sessao() as s:
        linhas = {c.conteudo: c.principal for c in s.scalars(select(Classificacao))}
    assert linhas == {IMPUTABILIDADE: False,
                      "Direito Penal > Crimes contra a Administração Pública": True}


def test_a_pendente_trocada_sai_mesmo_por_outra_pendente(semeada):
    """Pendente nao e no a associar: trocada - ate por outra pendente, de
    outra materia, como nas 8 do Socioeducativo (B.10) -, ela sai."""
    classificacoes.classificar("q1", PENAL, "manual", status="pendente")
    classificacoes.classificar("q1", "Direito Processual Penal", "manual", status="pendente")
    with sessao() as s:
        linhas = {c.conteudo: c.principal for c in s.scalars(select(Classificacao))}
    assert linhas == {"Direito Processual Penal": True}


def test_a_proposta_do_catalogo_trocada_sai_e_nao_vira_associada(semeada):
    """Palavra-chave casada no enunciado nao e conceito que a questao cobra:
    a proposta do catalogo, quando outra classificacao toma o lugar dela, foi
    reprovada, e nao fica como associada (B.8)."""
    classificacoes.classificar("q1", IMPUTABILIDADE, classificacoes.PROCEDENCIA_DO_CATALOGO)
    classificacoes.classificar("q1", "Direito Penal > Crimes contra a Administração Pública",
                               "Claude Code")
    with sessao() as s:
        linhas = {c.conteudo: c.principal for c in s.scalars(select(Classificacao))}
    assert linhas == {"Direito Penal > Crimes contra a Administração Pública": True}


def test_texto_antigo_que_nao_casa_fica_pendente(semeada):
    casou = classificacoes.do_texto_antigo("q1", "Direito Penal", "Imputabilidade penal",
                                           "claude-x")
    assert (casou.conteudo, casou.status) == (IMPUTABILIDADE, "completa")

    nao = classificacoes.do_texto_antigo("q2", "Direito Penal",
                                         "Aplicação da lei penal", "claude-x")
    assert (nao.conteudo, nao.status) == (PENAL, "pendente")
    assert "Aplicação da lei penal" in nao.trecho

    assert classificacoes.do_texto_antigo("q3", "Matéria inventada", "x", "claude-x") is None


def test_o_json_das_classificacoes_vai_e_volta(semeada):
    quando = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)
    classificacoes.classificar("q1", IMPUTABILIDADE, "claude-x", trecho="o menor de 18",
                               classificada_em=quando)
    classificacoes.exportar()
    with sessao() as s:
        s.execute(Classificacao.__table__.delete())

    assert classificacoes.importar() == (1, 0)
    with sessao() as s:
        volta = s.scalar(select(Classificacao))
    assert (volta.conteudo, volta.procedencia, volta.trecho, volta.status) == (
        IMPUTABILIDADE, "claude-x", "o menor de 18", "completa")


def test_o_json_recusa_linha_sem_procedencia(semeada):
    classificacoes.caminho_do_arquivo().write_text(json.dumps([
        {"chave": "q1", "conteudo": IMPUTABILIDADE, "procedencia": "manual"},
        {"chave": "q2", "conteudo": IMPUTABILIDADE},
        {"chave": "q3", "conteudo": "Não existe", "procedencia": "manual"},
    ]), encoding="utf-8")
    assert classificacoes.importar() == (1, 2)


def test_o_assunto_antigo_vira_classificacao(semeada):
    with sessao() as s:
        s.add(QuestaoDeProva(prova_url="p.pdf", numero=1, materia="Direito Penal",
                             enunciado="?", impressao="q1"))
    acervo.caminho_dos_assuntos().write_text(json.dumps([
        {"impressao": "q1", "materia": "Direito Penal", "assunto": "Imputabilidade penal",
         "modelo": "claude-x", "classificado_em": "2026-09-20T10:00:00+00:00"},
        {"impressao": "q2", "materia": "Direito Penal", "assunto": "Imputabilidade penal"},
    ]), encoding="utf-8")

    acervo.importar_assuntos()

    with sessao() as s:
        linhas = list(s.scalars(select(Classificacao)))
    chave = classificacoes.chave_da_questao("?", None)
    assert [(c.chave, c.conteudo, c.procedencia) for c in linhas] == [
        (chave, IMPUTABILIDADE, "claude-x")]      # a sem procedencia nao entra


# --- os textos antigos ------------------------------------------------------------------

def _gerada(impressao, materia, assunto=None):
    return QuestaoGerada(modo="do_zero", materia=materia, assunto=assunto, enunciado="?",
                         alternativas={"a": "x"}, resposta="a", impressao=impressao,
                         modelo="m")


def test_ligar_os_textos_antigos(semeada):
    with sessao() as s:
        s.add(_gerada("g1", "Aplicação da lei penal (arts. 1º a 12)"))
        s.add(_gerada("g2", "Língua Portuguesa", "Substantivo e adjetivo (flexão nominal)"))
        s.add(_gerada("g3", "Língua Portuguesa", "Emprego da crase"))
        s.add(_gerada("g4", "Matéria inventada"))
        s.add(ErroAnotado(data_estudo=date(2026, 9, 28), materia="Direito Processo Penal",
                          motivo="nao_sabia", regra="A regra."))

    previa = conteudos.ligar_textos_antigos(aplicar=False)
    with sessao() as s:
        assert all(g.conteudo is None for g in s.scalars(select(QuestaoGerada)))

    assert conteudos.ligar_textos_antigos()
    with sessao() as s:
        ligadas = {g.impressao: g.conteudo for g in s.scalars(select(QuestaoGerada))}
        erro = s.scalar(select(ErroAnotado))
    assert ligadas == {
        "g1": PENAL,                                  # o titulo da faixa
        "g2": "Língua Portuguesa",                    # o assunto nao casa: pendente
        "g3": "Língua Portuguesa > Emprego da crase",
        "g4": None,
    }
    assert erro.conteudo == "Direito Processual Penal"
    # A previa diz por que: a de Portugues casou so na materia.
    (portugues,) = [l for l in previa if "Substantivo" in l.texto]
    assert "pendente" in portugues.motivo


# --- a chave conteudo no cronograma ----------------------------------------------------

def _mini_com_conteudo(tmp_path, caminho_do_no):
    texto = MINI.read_text(encoding="utf-8").replace(
        "    titulo: Substantivo\n  noite:",
        f"    titulo: Substantivo\n    conteudo: '{caminho_do_no}'\n  noite:")
    arquivo = tmp_path / "cronograma.yml"
    arquivo.write_text(texto, encoding="utf-8")
    return arquivo


NO_DA_MANHA = "Língua Portuguesa > Classes gramaticais variáveis: substantivo, adjetivo, artigo, numeral, pronome, verbo"


def test_a_chave_conteudo_e_conferida_contra_a_arvore(semeada, tmp_path):
    plano = cronograma.carregar(_mini_com_conteudo(tmp_path, NO_DA_MANHA))
    faixa = cronograma.montar_dia(plano, date(2026, 9, 28), 1).manha[2]
    assert faixa.conteudo == NO_DA_MANHA

    with pytest.raises(cronograma.ErroNoCronograma, match="não está na árvore"):
        cronograma.carregar(_mini_com_conteudo(tmp_path, "Língua Portuguesa > Inventado"))


def test_o_check_da_faixa_guarda_o_conteudo(semeada, tmp_path):
    plano = cronograma.carregar(_mini_com_conteudo(tmp_path, NO_DA_MANHA))
    faixa = cronograma.montar_dia(plano, date(2026, 9, 28), 1).manha[2]
    diario.marcar_faixa(date(2026, 9, 28), "manha", 2, faixa.titulo, plano=plano,
                        hoje=date(2026, 10, 3))
    (check,) = diario.estado_do_dia(date(2026, 9, 28)).faixas_feitas
    assert check["conteudo"] == NO_DA_MANHA


def test_sem_a_arvore_nao_ha_o_que_conferir(banco_temporario, tmp_path):
    plano = cronograma.carregar(_mini_com_conteudo(tmp_path, "Qualquer > coisa"))
    assert plano.dias


# --- pendentes ------------------------------------------------------------------------

def test_pendente_e_a_questao_sem_classificacao_principal(semeada):
    with sessao() as s:
        for n, ev in enumerate(("alvo", "alvo", "complementar"), start=1):
            s.add(QuestaoDeProva(prova_url="p.pdf", numero=n, materia="Direito Penal",
                                 enunciado=f"Q{n}?", impressao=f"q{n}", evidencia=ev, ano=2019,
                                 cargo="Agente Penitenciário"))
        s.add(QuestaoDeProva(prova_url="p.pdf", numero=9, enunciado="?", impressao="q9",
                             evidencia="alvo", anulada=True))
    assert conteudos.pendentes().por_evidencia == {"alvo": 2, "complementar": 1}

    classificacoes.classificar(classificacoes.chave_da_questao("Q1?", None), IMPUTABILIDADE, "manual")
    # so a materia: pendente
    classificacoes.classificar(classificacoes.chave_da_questao("Q2?", None), PENAL, "manual")
    situacao = conteudos.pendentes()
    assert situacao.por_evidencia == {"alvo": 1, "complementar": 1}
    assert situacao.por_prova == [("alvo", 2019, "Agente Penitenciário", 1),
                                  ("complementar", 2019, "Agente Penitenciário", 1)]


# --- o comando ------------------------------------------------------------------------

def test_o_comando_mostra_a_arvore_e_os_pendentes(semeada):
    from typer.testing import CliRunner
    from radar.cli import app

    saida = CliRunner().invoke(app, ["conteudos", "--pendentes"], env={"COLUMNS": "200"})

    assert saida.exit_code == 0, saida.output
    assert "Regras mínimas da ONU para o tratamento de pessoas presas" in saida.output
    assert "Noções de Informática (fora do edital atual)" in saida.output
    assert "11 matéria(s) do edital · 2 fora do edital atual · 85 assunto(s)" in saida.output
    assert "Sem classificação (pendentes)" in saida.output


def test_o_json_antigo_pela_impressao_vira_chave(semeada):
    """Linha de antes da chave: igual quando o enunciado e de uma questao so;
    pendente em cada uma quando ele se repete - nao da para saber de qual."""
    with sessao() as s:
        s.add(QuestaoDeProva(prova_url="p.pdf", numero=1, enunciado="Único?",
                             alternativas={"a": "x"}, impressao="unica"))
        for n, letra in ((2, "x"), (3, "y")):
            s.add(QuestaoDeProva(prova_url="p.pdf", numero=n, enunciado="É correto",
                                 alternativas={"a": letra}, impressao="repetida"))
    classificacoes.caminho_do_arquivo().write_text(json.dumps([
        {"impressao": "unica", "conteudo": IMPUTABILIDADE, "procedencia": "manual"},
        {"impressao": "repetida", "conteudo": IMPUTABILIDADE, "procedencia": "manual"},
    ]), encoding="utf-8")

    assert classificacoes.importar() == (3, 0)

    with sessao() as s:
        por_chave = {c.chave: c for c in s.scalars(select(Classificacao))}
    unica = por_chave[classificacoes.chave_da_questao("Único?", {"a": "x"})]
    assert (unica.conteudo, unica.status) == (IMPUTABILIDADE, "completa")
    for letra in "xy":
        c = por_chave[classificacoes.chave_da_questao("É correto", {"a": letra})]
        assert (c.conteudo, c.status) == (PENAL, "pendente")
        assert "ambígua" in c.trecho

