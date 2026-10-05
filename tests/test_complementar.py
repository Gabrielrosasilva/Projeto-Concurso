"""O levantamento do acervo complementar FEPESE (Etapa 3B, passo 1).

O que estes testes seguram:

- **os numeros do alvo nao mudam** quando prova complementar entra (secao 4
  do pedido): nem a incidencia, nem o levantamento tocam no alvo;
- o **hash repetido** com outro nome de arquivo e recusado;
- prova que nao valida fica **fora da estatistica, com o motivo escrito**;
- gabarito **provisorio** classifica mas nao entra nos padroes (decisao A da
  3B);
- as duas colunas (nome da materia x termo no texto) **nao se somam**, e a de
  termo e marcada como indicio;
- as **perguntas da secao 5** sao respondidas a partir da fixture, sem
  afirmar o que o acervo nao tem;
- o comando **so le**: nao grava questao, nao muda evidencia.

Nenhum teste vai a internet, le o banco real nem depende da data de hoje.
"""
import json
import re
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from radar import complementar, edital_programa
from radar import provas as arquivos_de_prova
from radar.cli import app as cli
from radar.db import sessao
from radar.models import Classificacao, QuestaoDeProva
from radar.servico import classificacoes, conteudos
from radar.servico import complementar as servico
from radar.servico import incidencia as servico_da_incidencia
from radar.web.app import app

PROGRAMA = edital_programa.ler_programa(
    (Path(__file__).parent / "fixtures" / "provas" / "edital_sap_2019_programa.txt")
    .read_text(encoding="utf-8"))

PREVISAO = re.compile(r"(?i)vai cair|certamente|sempre cobra|cairá")

ALTERNATIVAS = {letra: f"texto {letra}" for letra in complementar.LETRAS}


# --- a validacao (puro) ------------------------------------------------------------

def _caderno(url="https://fepese.test/socio.pdf", quantas=3, gabarito=complementar.DEFINITIVO,
             sha256="aaa", **mudanca):
    questoes = [complementar.QuestaoDoCaderno(
        numero=n, materia_no_edital="Direito Penal", texto="Pergunta.",
        letras=complementar.LETRAS, resposta="a") for n in range(1, quantas + 1)]
    for campo, valor in mudanca.items():
        setattr(questoes[0], campo, valor)
    return complementar.Caderno(prova_url=url, cargo="Agente", ano=2016,
                                questoes=questoes, sha256=sha256, gabarito=gabarito)


def test_prova_inteira_com_definitivo_passa_na_validacao():
    v = complementar.validar(_caderno())
    assert (v.problemas, v.motivo) == ([], "")
    assert v.pode_classificar and v.entra_nos_padroes
    assert v.situacao == "validada"
    # O quadro do edital NAO foi conferido, e o relatorio nunca diz que bate.
    assert v.quadro_do_edital == "não lido"


def test_gabarito_provisorio_classifica_mas_fica_fora_dos_padroes():
    v = complementar.validar(_caderno(gabarito=complementar.PROVISORIO))
    assert v.pode_classificar and not v.entra_nos_padroes
    assert v.situacao == "só para classificar"
    assert "provisório" in v.motivo and "letra certa" in v.motivo


def test_gabarito_ausente_tambem_classifica_e_nao_entra_nos_padroes():
    v = complementar.validar(_caderno(gabarito=complementar.AUSENTE))
    assert v.pode_classificar and not v.entra_nos_padroes


def test_numeracao_com_buraco_e_pega():
    caderno = _caderno(quantas=3)
    caderno.questoes[2].numero = 7
    v = complementar.validar(caderno)
    assert not v.pode_classificar
    assert "3 questões extraídas, e o caderno vai até a 7" in v.motivo
    assert "falta 3, 4, 5, 6" in v.motivo


def test_numero_repetido_e_pego():
    caderno = _caderno(quantas=3)
    caderno.questoes[2].numero = 2
    assert "repete 2" in complementar.validar(caderno).motivo


def test_alternativa_faltando_e_pega():
    v = complementar.validar(_caderno(letras=("a", "b", "c", "d")))
    assert not v.pode_classificar
    assert "alternativas diferentes de a-e nas questões 1" in v.motivo


def test_questao_sem_gabarito_e_pega_e_a_anulada_nao():
    v = complementar.validar(_caderno(resposta=None))
    assert "sem letra no gabarito nas questões 1" in v.motivo

    caderno = _caderno()
    caderno.questoes[0].resposta, caderno.questoes[0].anulada = None, True
    assert complementar.validar(caderno).pode_classificar


def test_caderno_vazio_e_recusado():
    vazio = complementar.Caderno(prova_url="x", cargo=None, ano=None, questoes=[])
    assert complementar.validar(vazio).motivo == "nenhuma questão extraída"


def test_hash_repetido_com_outro_nome_e_recusado():
    """A mesma prova baixada com outro nome de arquivo nao entra duas vezes."""
    primeira = _caderno(url="https://fepese.test/AS.pdf", sha256="igual")
    segunda = _caderno(url="https://fepese.test/outro-nome.pdf", sha256="igual")

    validadas = servico.validacoes([primeira, segunda])

    assert validadas[primeira.prova_url].pode_classificar
    recusada = validadas[segunda.prova_url]
    assert not recusada.pode_classificar
    assert recusada.motivo == "o mesmo PDF já está no acervo em https://fepese.test/AS.pdf"


def test_sha256_diferente_nao_e_repeticao():
    duas = [_caderno(url="https://fepese.test/a.pdf", sha256="a"),
            _caderno(url="https://fepese.test/b.pdf", sha256="b")]
    assert all(v.pode_classificar for v in servico.validacoes(duas).values())


# --- as duas colunas (puro) --------------------------------------------------------

TERMOS = {"Direito Penal": ["Código Penal"], "Lei de Execução Penal": ["execução penal"]}


def _generica(numero, texto):
    return complementar.QuestaoDoCaderno(numero=numero, materia_no_edital=None,
                                         texto=texto, resposta="a")


def _levantar(cadernos, materias=("Direito Penal", "Lei de Execução Penal")):
    validadas = servico.validacoes(cadernos)
    return {m.materia: m for m in
            complementar.montar(list(materias), cadernos, TERMOS, validadas)}


def test_o_nome_da_materia_conta_e_o_termo_e_indicio_a_parte():
    caderno = complementar.Caderno(
        prova_url="https://fepese.test/guarda.pdf", cargo="Guarda Municipal", ano=2024,
        sha256="g", gabarito=complementar.PROVISORIO,
        questoes=[
            complementar.QuestaoDoCaderno(1, "Direito Penal", "Sobre o crime.", resposta="a"),
            _generica(2, "Nos termos do Código Penal brasileiro, o dolo..."),
            _generica(3, "Sobre a jornada de trabalho do servidor."),
        ])
    penal = _levantar([caderno])["Direito Penal"]

    assert (penal.pelo_nome, penal.por_termo) == (1, 1)
    assert penal.provas[0].questoes == 2        # as duas colunas nao se sobrepoem
    assert "1 questão · 1 prova pelo nome da matéria" in penal.amostra()
    assert "1 indício(s) por termo em 1 prova" in penal.amostra()


def test_questao_que_ja_tem_materia_propria_nao_vira_indicio_de_outra():
    """Questao do bloco "Lei de Execução Penal" que cita o Codigo Penal conta
    em LEP, e nao vira indicio de Direito Penal."""
    caderno = complementar.Caderno(
        prova_url="u", cargo=None, ano=2016, sha256="s",
        questoes=[complementar.QuestaoDoCaderno(
            1, "Lei de Execução Penal", "Conforme o Código Penal e a execução penal...",
            resposta="a")])
    mapa = _levantar([caderno])

    assert (mapa["Lei de Execução Penal"].pelo_nome, mapa["Lei de Execução Penal"].por_termo) == (1, 0)
    assert mapa["Direito Penal"].provas == []


def test_materia_sem_nada_no_acervo_diz_isso_sem_afirmar_o_que_nao_sabe():
    vazio = complementar.Caderno(prova_url="u", cargo=None, ano=2024, sha256="s",
                                 questoes=[_generica(1, "Sobre pedagogia.")])
    lep = _levantar([vazio])["Lei de Execução Penal"]

    assert not lep.tem_alguma_coisa
    assert lep.amostra() == "nenhuma questão no acervo complementar"


# --- do banco: o acervo da fixture -------------------------------------------------

MANIFESTO = [
    {"tipo": "prova", "url": "https://fepese.test/2016/AS.pdf", "sha256": "socio-2016",
     "concurso_url": "https://fepese.test/2016", "arquivo": "AS.pdf"},
    {"tipo": "gabarito_definitivo", "url": "https://fepese.test/2016/gab.pdf",
     "sha256": "gab-2016", "concurso_url": "https://fepese.test/2016"},
    {"tipo": "prova", "url": "https://fepese.test/2024/guarda.pdf", "sha256": "guarda",
     "concurso_url": "https://fepese.test/2024", "arquivo": "GM.pdf"},
    {"tipo": "gabarito", "url": "https://fepese.test/2024/gab.pdf", "sha256": "gab-2024",
     "concurso_url": "https://fepese.test/2024"},
]


def _questao(prova, numero, materia, evidencia, ano, cargo, enunciado="Pergunta?",
             concurso=None, resposta="a"):
    return QuestaoDeProva(
        prova_url=prova, concurso_url=concurso, banca="FEPESE", ano=ano, cargo=cargo,
        numero=numero, materia=materia, enunciado=enunciado, alternativas=dict(ALTERNATIVAS),
        resposta=resposta, impressao=f"{prova}-{numero}", evidencia=evidencia)


@pytest.fixture
def acervo(banco_temporario, tmp_path):
    """Duas provas do alvo, o Socioeducativo 2016 e uma Guarda Municipal 2024."""
    (tmp_path / "provas.json").write_text(json.dumps(MANIFESTO), encoding="utf-8")
    conteudos.semear(programa=PROGRAMA)
    with sessao() as s:
        # O alvo: 2013 e 2019. Enunciados diferentes de proposito - a chave da
        # classificacao e enunciado + alternativas, e duas questoes iguais
        # seriam a mesma questao para ela.
        for ano, numero in ((2013, 47), (2019, 51)):
            s.add(_questao(f"https://fepese.test/{ano}.pdf", numero, "Direito Penal",
                           "alvo", ano, "Agente Penitenciário",
                           enunciado=f"Pergunta {numero} de {ano}?"))
        # Complementar com gabarito definitivo: o Socioeducativo 2016.
        for numero, materia in ((1, "Direito Penal"), (2, "Direito Penal"),
                                (3, "Direitos Humanos")):
            # Enunciados diferentes: a chave e enunciado + alternativas, e
            # questoes iguais seriam a MESMA questao para a classificacao.
            s.add(_questao("https://fepese.test/2016/AS.pdf", numero, materia,
                           "complementar", 2016, "Agente de Segurança Socioeducativo",
                           enunciado=f"Questão {numero} de 2016 sobre {materia}?",
                           concurso="https://fepese.test/2016"))
        # Complementar so com provisorio, e com bloco generico: a Guarda 2024.
        s.add(_questao("https://fepese.test/2024/guarda.pdf", 1, "Conhecimentos Específicos",
                       "complementar", 2024, "Guarda Municipal",
                       enunciado="De acordo com o Código Penal, o dolo...",
                       concurso="https://fepese.test/2024"))
        s.add(_questao("https://fepese.test/2024/guarda.pdf", 2, "Conhecimentos Específicos",
                       "complementar", 2024, "Guarda Municipal",
                       enunciado="Sobre postura urbana...",
                       concurso="https://fepese.test/2024"))
    with sessao() as s:
        alvo = next(q for q in s.query(QuestaoDeProva).filter_by(numero=47))
        chave = classificacoes.chave_de(alvo)
    classificacoes.classificar(chave, "Direito Penal > Imputabilidade penal", "manual")
    return tmp_path


def test_o_levantamento_so_le_o_complementar(acervo):
    por_materia, validadas, cadernos = servico.levantamento()

    assert {c.prova_url for c in cadernos} == {"https://fepese.test/2016/AS.pdf",
                                               "https://fepese.test/2024/guarda.pdf"}
    penal = next(m for m in por_materia if m.materia == "Direito Penal")
    # As 2 do Socioeducativo pelo nome; a 1 da Guarda por termo. As do alvo
    # (2013 e 2019) nao estao aqui.
    assert (penal.pelo_nome, penal.por_termo) == (2, 1)


def test_o_tipo_do_gabarito_vem_do_manifesto(acervo):
    _, validadas, _ = servico.levantamento()

    socio = validadas["https://fepese.test/2016/AS.pdf"]
    guarda = validadas["https://fepese.test/2024/guarda.pdf"]
    assert (socio.gabarito, socio.entra_nos_padroes) == (complementar.DEFINITIVO, True)
    assert (guarda.gabarito, guarda.entra_nos_padroes) == (complementar.PROVISORIO, False)
    assert guarda.pode_classificar


def test_os_numeros_do_alvo_nao_mudam_com_prova_complementar(acervo):
    """Secao 4 do pedido: a incidencia do alvo e a mesma antes e depois."""
    antes = {m.materia: (m.topo.amostra, m.topo.rotulo)
             for m in servico_da_incidencia.mapa()}

    servico.levantamento()
    with sessao() as s:
        for numero in range(1, 30):
            s.add(_questao("https://fepese.test/2024/outra.pdf", numero, "Direito Penal",
                           "complementar", 2024, "Procurador do Município"))
    depois = {m.materia: (m.topo.amostra, m.topo.rotulo)
              for m in servico_da_incidencia.mapa()}

    assert antes == depois
    assert antes["Direito Penal"][0] == "1 questão · 1 prova"


def test_as_perguntas_da_secao_5_sao_respondidas_pela_fixture(acervo):
    por_materia, _, _ = servico.levantamento()
    respostas = {r.pergunta[:2]: r.resposta for r in complementar.responder(por_materia)}

    assert "Direito Penal (2 em 1 prova)" in respostas["1."]
    # LEP nao tem nada no acervo da fixture - e o texto diz isso sem afirmar
    # que a FEPESE nunca cobrou.
    assert "Nenhuma questão de Lei de Execução Penal" in respostas["3."]
    assert complementar.FRASE_SEM_EVIDENCIA in respostas["3."]
    assert "Sociologia Aplicada" in respostas["4."]
    # So a prova com definitivo conta como reforco pronto.
    assert "Direito Penal (2 em 1 prova)" in respostas["6."]
    assert "Direitos Humanos (1 em 1 prova)" in respostas["6."]


def test_o_relatorio_mostra_o_motivo_de_cada_prova_fora(acervo):
    texto = servico.relatorio(*servico.levantamento())

    assert "só para classificar" in texto and "validada" in texto
    assert "fora dos padrões de cobrança" in texto
    assert "não lido" in texto                      # o quadro do edital
    assert complementar.FRASE_SEM_EVIDENCIA in texto
    assert not PREVISAO.search(texto)


def test_o_relatorio_diz_que_as_evidencias_nunca_se_somam(acervo):
    texto = servico.relatorio(*servico.levantamento())
    assert "nunca" in texto and "incidência da Polícia Penal SC" in texto
    assert "2 provas complementares" in texto


def test_antes_de_aplicar_o_relatorio_e_so_o_levantamento(acervo):
    texto = servico.relatorio(*servico.levantamento())
    assert "Nada entrou em estatística nenhuma" in texto
    assert "Onde isto está" not in texto


def test_depois_de_aplicar_o_relatorio_nao_diz_que_nada_entrou(acervo):
    """O docs/complementar.md dizia "nada entrou" com 122 provas ja na
    incidencia (achado da varredura de 03/10/2026)."""
    servico.aplicar(hoje=date(2026, 10, 1))

    texto = servico.relatorio(*servico.levantamento())

    assert "Nada entrou" not in texto
    assert "**1 provas** estão aceitas" in texto
    assert "linha própria na incidência" in texto


def test_o_comando_escreve_o_relatorio_e_nao_muda_o_banco(acervo, tmp_path):
    def fotografia():
        with sessao() as s:
            return sorted((q.prova_url, q.numero, q.evidencia, q.materia)
                          for q in s.query(QuestaoDeProva))

    antes = fotografia()
    destino = tmp_path / "complementar.md"
    saida = CliRunner().invoke(cli, ["complementar", "--caminho", str(destino)],
                               env={"COLUMNS": "200"})

    assert saida.exit_code == 0, saida.output
    assert fotografia() == antes
    assert destino.exists()
    assert "Direito Penal" in destino.read_text(encoding="utf-8")
    assert "1 validada(s)" in saida.output and "1 só para classificar" in saida.output
    assert not PREVISAO.search(saida.output)


def test_sem_prova_complementar_o_comando_avisa(banco_temporario, tmp_path):
    (tmp_path / "provas.json").write_text("[]", encoding="utf-8")
    conteudos.semear(programa=PROGRAMA)

    saida = CliRunner().invoke(cli, ["complementar", "--caminho",
                                     str(tmp_path / "vazio.md")])

    assert saida.exit_code == 1
    assert "Nenhuma prova complementar" in saida.output


def test_os_termos_vem_do_config():
    termos = servico.carregar_termos()
    assert "código penal" in [t.lower() for t in termos["Direito Penal"]]
    assert "execução penal" in [t.lower() for t in termos["Lei de Execução Penal"]]


def test_o_manifesto_de_verdade_tem_o_sha256_de_cada_caderno():
    """O hash e o que recusa a mesma prova duas vezes: sem ele, nada feito."""
    com_hash = [r for r in arquivos_de_prova.carregar_manifesto()
                if r.get("tipo") == arquivos_de_prova.PROVA and r.get("sha256")]
    assert len(com_hash) > 100


# --- quem entra no acervo, e a linha complementar da incidencia -------------------

def test_prova_sem_materia_do_edital_nao_entra():
    """Nocoes de Informatica e Temas de Educacao nao estao no edital de 2019:
    nao servem de motivo para a prova entrar."""
    validacao = complementar.validar(_caderno())
    assert complementar.decidir(validacao, []) == (
        False, "nenhuma matéria do edital de 2019 neste caderno")


def test_prova_com_materia_do_edital_e_extracao_inteira_entra():
    assert complementar.decidir(complementar.validar(_caderno()),
                                ["Direito Penal"]) == (True, "")


def test_prova_com_materia_minha_mas_extracao_furada_nao_entra():
    caderno = _caderno(quantas=3)
    caderno.questoes[2].numero = 9
    entra, motivo = complementar.decidir(complementar.validar(caderno), ["Direito Penal"])
    assert not entra and "a numeração não fecha" in motivo


def test_prova_com_gabarito_provisorio_entra_com_o_aviso():
    entra, motivo = complementar.decidir(
        complementar.validar(_caderno(gabarito=complementar.PROVISORIO)), ["Direito Penal"])
    assert entra and "fora dos padrões de cobrança" in motivo


def test_aplicar_grava_o_arquivo_de_status(acervo):
    registros, mudanca = servico.aplicar(hoje=date(2026, 10, 1))

    gravado = servico.carregar_registro()
    assert set(gravado) == {"https://fepese.test/2016/AS.pdf",
                            "https://fepese.test/2024/guarda.pdf"}
    socio = gravado["https://fepese.test/2016/AS.pdf"]
    assert socio["aceita"] and socio["entra_nos_padroes"]
    assert socio["incluida_em"] == "2026-10-01"
    assert socio["sha256"] == "socio-2016" and socio["arquivo"] == "AS.pdf"
    assert sorted(socio["materias_do_edital"]) == ["Direito Penal", "Direitos Humanos"]
    # A Guarda so tem bloco generico: nenhuma materia do edital pelo nome.
    guarda = gravado["https://fepese.test/2024/guarda.pdf"]
    assert not guarda["aceita"] and guarda["incluida_em"] is None
    assert guarda["motivo"] == "nenhuma matéria do edital de 2019 neste caderno"
    assert len(mudanca["entraram"]) == 1 and mudanca["sairam"] == []


def test_a_data_de_inclusao_nao_muda_quando_o_comando_roda_de_novo(acervo):
    servico.aplicar(hoje=date(2026, 10, 1))
    servico.aplicar(hoje=date(2026, 12, 25))

    gravado = servico.carregar_registro()
    assert gravado["https://fepese.test/2016/AS.pdf"]["incluida_em"] == "2026-10-01"


def test_sem_o_arquivo_de_status_nenhuma_prova_entra_na_estatistica(acervo):
    """Levantar nao e aprovar: sem a lista aplicada, o complementar e zero."""
    assert servico.provas_aceitas() == set()
    assert servico_da_incidencia.ocorrencias_complementares() == []
    linhas = servico_da_incidencia.linhas_complementares()
    assert linhas["Direito Penal"].questoes == 0
    assert linhas["Direito Penal"].frase == "Acervo complementar FEPESE: nada no acervo"


def test_a_linha_complementar_aparece_depois_de_aplicar(acervo):
    servico.aplicar(hoje=date(2026, 10, 1))

    linhas = servico_da_incidencia.linhas_complementares()
    penal = linhas["Direito Penal"]
    assert (penal.questoes, penal.provas, penal.classificadas) == (2, 1, 0)
    assert penal.frase == ("Acervo complementar FEPESE: 2 questões · 1 prova "
                           "(2 sem classificação ainda)")
    # Sem classificacao, nada conta abaixo da materia: assunto nenhum e
    # adivinhado a partir do nome do caderno.
    assert linhas["Direito Penal > Imputabilidade penal"].questoes == 0


def test_a_prova_recusada_fica_fora_da_linha_complementar(acervo):
    servico.aplicar(hoje=date(2026, 10, 1))
    # A Guarda 2024 nao entrou: o indicio por termo dela nao vira estatistica.
    assert servico.provas_aceitas() == {"https://fepese.test/2016/AS.pdf"}
    assert {o.prova for o in servico_da_incidencia.ocorrencias_complementares()} == {
        "https://fepese.test/2016/AS.pdf"}


def test_a_linha_do_alvo_nao_muda_quando_o_complementar_entra(acervo):
    antes = {m.materia: (m.topo.amostra, m.topo.rotulo)
             for m in servico_da_incidencia.mapa()}

    servico.aplicar(hoje=date(2026, 10, 1))

    depois = {m.materia: (m.topo.amostra, m.topo.rotulo)
              for m in servico_da_incidencia.mapa()}
    assert antes == depois
    # E o numero do complementar nao e o do alvo: 2 contra 1, lado a lado.
    assert depois["Direito Penal"][0] == "1 questão · 1 prova"
    assert servico_da_incidencia.linhas_complementares()["Direito Penal"].questoes == 2


def test_a_tela_e_o_terminal_mostram_as_duas_linhas_sem_somar(acervo):
    servico.aplicar(hoje=date(2026, 10, 1))

    texto = TestClient(app).get("/analises/incidencia").text
    assert "Polícia Penal SC" in texto and "Acervo complementar FEPESE" in texto
    assert "as duas nunca se somam" in texto
    assert not PREVISAO.search(texto)

    saida = CliRunner().invoke(cli, ["incidencia"], env={"COLUMNS": "250"})
    assert saida.exit_code == 0, saida.output
    assert "Complementar FEPESE" in saida.output
    assert "as duas nunca se somam" in saida.output
    assert not PREVISAO.search(saida.output)


def test_a_questao_anulada_fica_fora_da_linha_complementar(acervo):
    with sessao() as s:
        q = next(x for x in s.query(QuestaoDeProva)
                 .filter_by(prova_url="https://fepese.test/2016/AS.pdf", numero=1))
        q.anulada = True
    servico.aplicar(hoje=date(2026, 10, 1))

    assert servico_da_incidencia.linhas_complementares()["Direito Penal"].questoes == 1


def test_o_comando_com_aplicar_grava_e_sem_aplicar_nao(acervo, tmp_path):
    destino = str(tmp_path / "rel.md")
    sem = CliRunner().invoke(cli, ["complementar", "--caminho", destino],
                             env={"COLUMNS": "200"})
    assert sem.exit_code == 0, sem.output
    assert "Nada foi gravado" in sem.output
    assert not servico.caminho_do_registro().exists()

    com = CliRunner().invoke(cli, ["complementar", "--caminho", destino, "--aplicar"],
                             env={"COLUMNS": "200"})
    assert com.exit_code == 0, com.output
    assert servico.caminho_do_registro().exists()
    assert "1 prova(s) no acervo complementar" in com.output


# --- classificar o complementar (Etapa 3B, passo 4) ------------------------------

def test_o_pedido_do_complementar_so_traz_prova_aceita(acervo):
    from radar.servico import manual

    # Sem o arquivo de status, nao ha o que pedir: nenhuma prova foi aceita.
    assert manual.pedido_de_classificacao(de_evidencia="complementar")["pedidos"] == []

    servico.aplicar(hoje=date(2026, 10, 1))
    lote = manual.pedido_de_classificacao(de_evidencia="complementar")

    provas = {c.split("-")[0] for p in lote["pedidos"] for c in p["questoes"]}
    assert provas == {"2016"}                   # a Guarda 2024 nao entrou no acervo
    assert {p["materia"] for p in lote["pedidos"]} == {"Direito Penal", "Direitos Humanos"}
    assert all(p["evidencia"] == "complementar" for p in lote["pedidos"])


def test_o_pedido_do_complementar_avisa_que_nao_e_a_prova_do_meu_cargo(acervo):
    from radar.servico import manual

    servico.aplicar(hoje=date(2026, 10, 1))
    lote = manual.pedido_de_classificacao(de_evidencia="complementar")

    instrucao = lote["pedidos"][0]["instrucao"]
    assert "OUTRO concurso da FEPESE" in instrucao
    assert "NUNCA e somado a incidencia da Policia Penal" in instrucao


def test_o_pedido_do_alvo_continua_so_com_o_alvo(acervo):
    from radar.servico import manual

    servico.aplicar(hoje=date(2026, 10, 1))
    lote = manual.pedido_de_classificacao()

    provas = {c.split("-")[0] for p in lote["pedidos"] for c in p["questoes"]}
    assert provas == {"2013", "2019"}
    assert all(p["evidencia"] == "alvo" for p in lote["pedidos"])
    assert "prova do meu cargo" in lote["pedidos"][0]["instrucao"]


def test_evidencia_que_nao_existe_e_recusada(acervo):
    from radar.servico import manual

    with pytest.raises(ValueError, match="alvo ou complementar"):
        manual.pedido_de_classificacao(de_evidencia="fora")


def test_classificar_o_complementar_nao_mexe_na_conta_do_alvo(acervo):
    """O numero do alvo e o mesmo antes e depois de classificar o acervo
    complementar inteiro (secao 4 do pedido)."""
    servico.aplicar(hoje=date(2026, 10, 1))
    antes = {m.materia: (m.topo.amostra, m.pendentes)
             for m in servico_da_incidencia.mapa()}

    with sessao() as s:
        questoes = [q for q in s.query(QuestaoDeProva)
                    .filter_by(prova_url="https://fepese.test/2016/AS.pdf")
                    if q.materia == "Direito Penal"]
        chaves = [classificacoes.chave_de(q) for q in questoes]
    for chave in chaves:
        classificacoes.classificar(chave, "Direito Penal > Imputabilidade penal",
                                   "Claude Code, teste")

    depois = {m.materia: (m.topo.amostra, m.pendentes)
              for m in servico_da_incidencia.mapa()}
    assert antes == depois

    # E agora o complementar conta ABAIXO da materia, onde antes nao contava.
    linhas = servico_da_incidencia.linhas_complementares()
    assert linhas["Direito Penal > Imputabilidade penal"].questoes == 2
    assert linhas["Direito Penal"].classificadas == 2
    assert linhas["Direito Penal"].frase == "Acervo complementar FEPESE: 2 questões · 1 prova"


# --- bloco generico, catalogo automatico e contagem de distintas ----------------

def _generica_no_banco(s, prova, numero, enunciado, ano=2016,
                       cargo="Agente de Segurança Socioeducativo",
                       materia="Conhecimentos Específicos",
                       concurso="https://fepese.test/2016"):
    s.add(_questao(prova, numero, materia, "complementar", ano, cargo,
                   enunciado=enunciado, concurso=concurso))


def test_o_pedido_generico_so_pega_bloco_sem_materia_minha(acervo):
    from radar.servico import manual

    servico.aplicar(hoje=date(2026, 10, 1))
    with sessao() as s:
        _generica_no_banco(s, "https://fepese.test/2016/AS.pdf", 9,
                           "Sobre o Código Penal e o dolo, assinale...")
    lote = manual.pedido_de_classificacao(de_evidencia="complementar", genericos=True)

    assert [p["materia"] for p in lote["pedidos"]] == ["Direito Penal"]
    pedido = lote["pedidos"][0]
    assert pedido["bloco_generico"]
    assert pedido["materia_sugerida_pelo_termo"] == "Direito Penal"
    assert "o caderno não diz a matéria" in pedido["pedido"]
    # As questoes que o caderno JA nomeia nao entram no pedido generico.
    assert len(pedido["questoes"]) == 1


def test_o_termo_casa_palavra_inteira_e_nao_pedaco(acervo):
    """O termo dolo dentro de dolorosa enchia o indicio de questao de saude."""
    from radar.servico import manual

    servico.aplicar(hoje=date(2026, 10, 1))
    with sessao() as s:
        _generica_no_banco(s, "https://fepese.test/2016/AS.pdf", 9,
                           "Sobre a experiência dolorosa do paciente, assinale...")
    lote = manual.pedido_de_classificacao(de_evidencia="complementar", genericos=True)

    assert lote["pedidos"] == []


def _pedido_generico():
    from radar.servico import manual

    return manual.pedido_de_classificacao(
        de_evidencia="complementar", genericos=True)["pedidos"][0]


def test_no_bloco_generico_a_materia_vem_na_resposta(acervo):
    servico.aplicar(hoje=date(2026, 10, 1))
    with sessao() as s:
        _generica_no_banco(s, "https://fepese.test/2016/AS.pdf", 9,
                           "De acordo com o Código Penal, o peculato...")
    pedido = _pedido_generico()
    codigo = next(iter(pedido["questoes"]))

    with pytest.raises(classificacoes.PropostaRecusada, match="sem a matéria escolhida"):
        classificacoes.aplicar_proposta(
            {"questao": codigo, "status": "classificada",
             "assunto": "Imputabilidade penal", "tipo_de_questao": "conceito",
             "trecho": "x", "item_do_edital": "y"}, pedido, "teste")

    caminho = classificacoes.aplicar_proposta(
        {"questao": codigo, "status": "classificada", "materia": "Direito Penal",
         "assunto": "Crimes contra a Administração Pública",
         "tipo_de_questao": "conceito", "trecho": "peculato",
         "item_do_edital": "Crimes contra a Administração Pública"}, pedido, "teste")
    assert caminho == "Direito Penal > Crimes contra a Administração Pública"


def test_bloco_generico_so_aceita_materia_do_edital_de_agora(acervo):
    servico.aplicar(hoje=date(2026, 10, 1))
    with sessao() as s:
        _generica_no_banco(s, "https://fepese.test/2016/AS.pdf", 9,
                           "De acordo com o Código Penal, o peculato...")
    pedido = _pedido_generico()
    codigo = next(iter(pedido["questoes"]))

    with pytest.raises(classificacoes.PropostaRecusada, match="não é matéria do edital"):
        classificacoes.aplicar_proposta(
            {"questao": codigo, "status": "classificada",
             "materia": "Noções de Informática", "assunto": "qualquer",
             "tipo_de_questao": "conceito", "trecho": "x", "item_do_edital": "y"},
            pedido, "teste")


def test_pendente_em_bloco_generico_fica_sem_linha(acervo):
    """Sem materia no caderno nao ha onde pendurar a pendente: ela nao vira
    linha, que ja e o estado de quem nao tem classificacao."""
    servico.aplicar(hoje=date(2026, 10, 1))
    with sessao() as s:
        _generica_no_banco(s, "https://fepese.test/2016/AS.pdf", 9,
                           "De acordo com o Código Penal, o peculato...")
    pedido = _pedido_generico()
    codigo = next(iter(pedido["questoes"]))

    with pytest.raises(classificacoes.PendenteSemMateria):
        classificacoes.aplicar_proposta(
            {"questao": codigo, "status": "pendente", "motivo": "é de enfermagem"},
            pedido, "teste")
    assert servico_da_incidencia.linhas_complementares()["Direito Penal"].classificadas == 0


def test_o_catalogo_propoe_assunto_e_marca_a_procedencia(acervo):
    servico.aplicar(hoje=date(2026, 10, 1))
    with sessao() as s:
        for numero, enunciado in (
                (10, "Assinale a alternativa em que o sinal indicativo de crase está correto."),
                (11, "Analise a concordância verbal do trecho destacado."),
                (12, "Sobre o texto 1, assinale a alternativa correta.")):
            s.add(_questao("https://fepese.test/2016/AS.pdf", numero,
                           "Língua Portuguesa", "complementar", 2016,
                           "Agente de Segurança Socioeducativo", enunciado=enunciado,
                           concurso="https://fepese.test/2016"))

    r = servico.classificar_pelo_catalogo("Língua Portuguesa")

    # A da concordância verbal casa DOIS assuntos do catálogo (concordância e
    # verbos): fica sem linha, que é o certo.
    assert (r.propostas, r.ambiguas) == (2, 1)
    assert r.por_assunto["Emprego da crase"] == 1
    with sessao() as s:
        linha = next(c for c in s.query(Classificacao)
                     if c.conteudo.endswith("Emprego da crase"))
    assert linha.procedencia == classificacoes.PROCEDENCIA_DO_CATALOGO
    assert "conferir por amostra" in linha.procedencia
    assert linha.trecho.startswith("catálogo:")


def test_o_catalogo_nao_chuta_quando_casa_dois_assuntos_ou_nenhum(acervo):
    servico.aplicar(hoje=date(2026, 10, 1))
    with sessao() as s:
        for numero, enunciado in (
                (10, "Sobre a crase e a regência verbal do trecho, assinale."),
                (11, "Assinale a alternativa que indica o nome do autor do poema.")):
            s.add(_questao("https://fepese.test/2016/AS.pdf", numero,
                           "Língua Portuguesa", "complementar", 2016,
                           "Agente de Segurança Socioeducativo", enunciado=enunciado,
                           concurso="https://fepese.test/2016"))

    r = servico.classificar_pelo_catalogo("Língua Portuguesa")

    assert r.propostas == 0
    assert (r.ambiguas, r.sem_assunto) == (1, 1)


def test_o_catalogo_nao_sobrescreve_classificacao_que_ja_existe(acervo):
    servico.aplicar(hoje=date(2026, 10, 1))
    with sessao() as s:
        s.add(_questao("https://fepese.test/2016/AS.pdf", 10, "Língua Portuguesa",
                       "complementar", 2016, "Agente de Segurança Socioeducativo",
                       enunciado="Assinale a alternativa sobre o emprego da crase.",
                       concurso="https://fepese.test/2016"))
    with sessao() as s:
        q = next(x for x in s.query(QuestaoDeProva).filter_by(numero=10))
        chave = classificacoes.chave_de(q)
    classificacoes.classificar(chave, "Língua Portuguesa > Pontuação", "manual")

    r = servico.classificar_pelo_catalogo("Língua Portuguesa")

    assert (r.propostas, r.ja_classificadas) == (0, 1)


def test_a_mesma_questao_em_varios_cadernos_conta_uma_vez(acervo):
    """A FEPESE repete o caderno de Portugues em dezenas de cargos: no acervo
    real as 993 ocorrencias sao 184 questoes. Contar 993 inflaria o acervo."""
    # A numeração de cada caderno tem de fechar, senão a prova é recusada na
    # validação: a 4 completa o AS.pdf (1 a 3 vêm da fixture), e o AS2.pdf
    # nasce com a 1.
    with sessao() as s:
        for prova, numero in (("https://fepese.test/2016/AS.pdf", 4),
                              ("https://fepese.test/2016/AS2.pdf", 1)):
            s.add(_questao(prova, numero, "Direito Penal", "complementar", 2016,
                           "Agente de Segurança Socioeducativo",
                           enunciado="A mesma questão, nos dois cadernos.",
                           concurso="https://fepese.test/2016"))
    servico.aplicar(hoje=date(2026, 10, 1))

    linha = servico_da_incidencia.linhas_complementares()["Direito Penal"]
    assert linha.ocorrencias == linha.questoes + 1
    assert "ocorrências em cadernos diferentes" in linha.frase


# --- o `radar padrao`: um bloco por evidencia (auditoria de 04/10) ----------------

def test_o_padrao_da_banca_separa_alvo_complementar_aceito_e_outra_banca(acervo):
    """O `radar padrao` somava o alvo, o complementar, as provas recusadas e a
    outra banca num numero so, chamado "incidencia" - o que a regra
    inviolavel 1 proibe. Agora cada evidencia e um bloco com a sua amostra, a
    prova recusada fica de fora e e contada."""
    from radar import servico as fachada

    with sessao() as s:
        s.add(QuestaoDeProva(
            prova_url="https://ieses.test/prova.pdf", banca="IESES", ano=2020,
            cargo="Agente", numero=1, materia="Língua Portuguesa",
            enunciado="Pergunta da outra banca?", alternativas=dict(ALTERNATIVAS),
            resposta="a", impressao="ieses-1", evidencia="fora"))
    servico.aplicar(hoje=date(2026, 10, 1))   # aceita o 2016; recusa a Guarda

    blocos, recusadas = fachada.incidencia_por_evidencia()

    por_evidencia = {b.evidencia: b for b in blocos}
    assert list(por_evidencia) == ["alvo", "complementar", "fora"]
    assert (por_evidencia["alvo"].questoes, por_evidencia["alvo"].provas) == (2, 2)
    assert dict(por_evidencia["complementar"].linhas) == {"Direito Penal": 2,
                                                          "Direitos Humanos": 1}
    assert por_evidencia["fora"].questoes == 1
    # As 2 da Guarda 2024 (recusada na validacao) nao entram em bloco nenhum.
    assert recusadas == 2
