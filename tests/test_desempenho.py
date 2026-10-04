"""O desempenho por NO da arvore: os dois recortes, e o estado de cada um.

O que estes testes seguram:

  * os dois recortes (radar e anotado) nunca somados num numero so na tela,
    e somados para o ESTADO - que e o meu desempenho naquele conteudo;
  * so o sem consulta conta para o estado; IA nunca conta;
  * o anotado entra no no que eu escolhi, e sobe para os pais;
  * questao sem classificacao conta no dia e em no nenhum;
  * o recorte de tempo: o ciclo, ou desde o inicio.

O cronograma e o mini (tests/fixtures) com a chave `conteudo`, e as datas sao
fixas: nada aqui depende do dia em que o teste roda.
"""
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
import yaml

from radar import amostra as regua
from radar import cronograma
from radar.db import sessao
from radar.models import Conteudo, QuestaoDeProva, RespostaDeSimulado, Simulado
from radar.servico import classificacoes
from radar.servico import conteudos as servico_conteudos
from radar.servico import cronograma as diario
from radar.servico import desempenho_por_conteudo as por_conteudo
from radar.servico import extra as estudo_extra
from radar.util import fuso_local

MINI = Path(__file__).parent / "fixtures" / "cronograma_mini.yml"
SEG = date(2026, 9, 28)
TER = date(2026, 9, 29)
HOJE = date(2026, 10, 3)

PENAL = "Direito Penal"
APLICACAO = "Direito Penal > Aplicação da lei penal"
NO_TEMPO = "Direito Penal > Aplicação da lei penal > Lei penal no tempo"
PORTUGUES = "Língua Portuguesa"


@pytest.fixture
def arvore(banco_temporario):
    """Uma arvore pequena: duas materias, um assunto e um subassunto."""
    with sessao() as s:
        for caminho, pai, nivel, nome in [
            (PENAL, None, "materia", PENAL),
            (APLICACAO, PENAL, "assunto", "Aplicação da lei penal"),
            (NO_TEMPO, APLICACAO, "subassunto", "Lei penal no tempo"),
            (PORTUGUES, None, "materia", PORTUGUES),
        ]:
            s.add(Conteudo(caminho=caminho, pai=pai, nivel=nivel, nome=nome,
                           origem="edital", procedencia="teste"))


@pytest.fixture
def plano(arvore, tmp_path):
    """O cronograma mini, com `conteudo` nas duas faixas de questoes de 28/09.

    O arquivo e reescrito no tmp_path para o teste nao depender do
    config/cronograma.yml real, e a arvore e exportada para o JSON que o
    carregamento confere.
    """
    servico_conteudos.exportar()
    dados = yaml.safe_load(MINI.read_text(encoding="utf-8"))
    dados["dias"][0]["noite"][0]["conteudo"] = APLICACAO
    dados["dias"][0]["manha"][0]["conteudo"] = APLICACAO
    arquivo = tmp_path / "cronograma_com_conteudo.yml"
    arquivo.write_text(yaml.safe_dump(dados, allow_unicode=True), encoding="utf-8")
    return cronograma.carregar(arquivo)


def _anotar(plano, bloco, indice, questoes, acertos, consulta=False, data=SEG,
            conteudo=None):
    faixa = getattr(cronograma.montar_dia(plano, data, 1), bloco)[indice]
    diario.anotar_faixa(data, bloco, indice, faixa.titulo, questoes=questoes,
                        acertos=acertos, consulta=consulta, conteudo=conteudo,
                        plano=plano, hoje=HOJE)


def _questao(numero: int, materia: str = PENAL) -> QuestaoDeProva:
    return QuestaoDeProva(
        prova_url="https://fepese.test/ap2019.pdf", banca="FEPESE",
        concurso_url="https://fepese.test/concurso", ano=2019,
        cargo="Agente Penitenciário", numero=numero, materia=materia,
        enunciado=f"questão {numero}?",
        alternativas={"a": f"x{numero}", "b": f"y{numero}"},
        resposta="a", impressao=f"q{numero}",
    )


def _responder(numero: int, acertou: bool, quando: date, gerada: bool = False,
               materia: str = PENAL, classificar_em: str | None = None) -> None:
    """Grava a questao, a resposta, e (se pedido) a classificacao dela."""
    with sessao() as s:
        questao = _questao(numero, materia)
        s.add(questao)
        s.flush()
        questao_id, chave = questao.id, classificacoes.chave_de(questao)
        simulado = Simulado(filtros={})
        s.add(simulado)
        s.flush()
        s.add(RespostaDeSimulado(
            simulado_id=simulado.id, questao_id=questao_id, gerada=gerada,
            ordem=1, escolhida="a" if acertou else "b", acertou=acertou,
            respondida_em=datetime.combine(quando, datetime.min.time(),
                                           tzinfo=fuso_local()) + timedelta(hours=20),
        ))
    if classificar_em:
        classificacoes.classificar(chave, classificar_em, "teste")


# --- os dois recortes -----------------------------------------------------------

def test_a_resposta_do_radar_conta_no_no_e_nos_de_cima(plano):
    _responder(1, True, SEG, classificar_em=NO_TEMPO)

    nos = por_conteudo.por_no(plano=plano, hoje=HOJE)

    assert set(nos) == {PENAL, APLICACAO, NO_TEMPO}
    for caminho in (PENAL, APLICACAO, NO_TEMPO):
        assert nos[caminho].radar.respostas == 1
        assert nos[caminho].radar.acertos == 1
    assert nos[NO_TEMPO].nivel == "subassunto"


def test_o_anotado_entra_no_no_escolhido(plano):
    """O ponto da decisao 7: o Qconcursos chega ao conteudo, e nao so a
    materia e ao titulo da faixa."""
    _anotar(plano, "noite", 0, 15, 11, conteudo=NO_TEMPO)

    nos = por_conteudo.por_no(plano=plano, hoje=HOJE)

    assert nos[NO_TEMPO].anotado.respostas == 15
    assert nos[NO_TEMPO].anotado.acertos == 11
    assert nos[PENAL].anotado.respostas == 15        # sobe para a materia
    assert nos[NO_TEMPO].radar.respostas == 0


def test_a_divisao_mostra_as_duas_metades_e_nunca_a_soma(plano):
    _responder(1, True, SEG, classificar_em=NO_TEMPO)
    _responder(2, False, SEG, classificar_em=NO_TEMPO)
    _anotar(plano, "noite", 0, 10, 8, conteudo=NO_TEMPO)

    no = por_conteudo.por_no(plano=plano, hoje=HOJE)[NO_TEMPO]

    assert no.divisao() == "radar 50% em 2 · anotado 80% em 10"
    # O estado, sim, olha as duas: e o meu desempenho naquele conteudo.
    assert no.respostas == 12 and no.acertos == 9


def test_a_divisao_escreve_o_travessao_na_metade_vazia(plano):
    _responder(1, True, SEG, classificar_em=NO_TEMPO)

    assert por_conteudo.por_no(plano=plano, hoje=HOJE)[NO_TEMPO].divisao() == (
        "radar 100% em 1 · anotado —")


# --- o que NAO conta ------------------------------------------------------------

def test_com_consulta_fica_no_volume_e_fora_do_estado(plano):
    _anotar(plano, "noite", 0, 12, 12, consulta=True, conteudo=NO_TEMPO)

    no = por_conteudo.por_no(plano=plano, hoje=HOJE)[NO_TEMPO]

    assert no.anotado.respostas == 0 and no.anotado.acertos == 0
    assert no.anotado.com_consulta == 12
    assert no.anotado.volume == 12
    assert no.estado().nome == regua.INSUFICIENTE


def test_questao_de_ia_nunca_conta(plano):
    """Ela treina e nao mede. A resposta a uma gerada nao chega aqui."""
    _responder(1, True, SEG, gerada=True, classificar_em=NO_TEMPO)

    assert por_conteudo.por_no(plano=plano, hoje=HOJE) == {}


def test_questao_sem_classificacao_conta_em_no_nenhum(plano):
    _responder(1, True, SEG)        # sem classificar_em

    assert por_conteudo.por_no(plano=plano, hoje=HOJE) == {}


def test_anotacao_sem_conteudo_conta_em_no_nenhum(plano):
    """A faixa de Portugues do mini nao tem `conteudo`: o que eu anoto nela
    conta no dia (o `metricas` ja contou) e em no nenhum."""
    _anotar(plano, "noite", 2, 10, 7)

    assert por_conteudo.por_no(plano=plano, hoje=HOJE) == {}


def test_fiz_e_nao_anotei_quantas_acertei_e_volume_sem_acerto(plano):
    _anotar(plano, "noite", 0, 15, None, conteudo=NO_TEMPO)

    no = por_conteudo.por_no(plano=plano, hoje=HOJE)[NO_TEMPO]

    assert no.anotado.sem_resultado == 15
    assert no.anotado.respostas == 0
    assert no.anotado.volume == 15


def test_a_classificacao_para_um_no_que_nao_existe_nao_inventa_no(plano):
    _responder(1, True, SEG, classificar_em=NO_TEMPO)
    with sessao() as s:
        no = s.query(Conteudo).filter_by(caminho=NO_TEMPO).one()
        s.delete(no)

    # A classificacao continua apontando para o caminho apagado; o no nao
    # renasce, e os de cima continuam contando.
    nos = por_conteudo.por_no(plano=plano, hoje=HOJE)
    assert NO_TEMPO not in nos
    assert nos[APLICACAO].radar.respostas == 1


# --- o estado -------------------------------------------------------------------

def test_o_estado_sai_do_nivel_do_no(plano):
    """O subassunto mede com 6; a materia, com 20."""
    for numero in range(1, 7):
        _responder(numero, numero <= 5, SEG, classificar_em=NO_TEMPO)

    nos = por_conteudo.por_no(plano=plano, hoje=HOJE)

    assert nos[NO_TEMPO].estado().suficiente          # 6 >= 6
    assert nos[NO_TEMPO].estado().minimo == 6
    assert not nos[PENAL].estado().suficiente         # 6 < 20
    assert nos[PENAL].estado().minimo == 20


def test_a_meta_do_no_e_a_da_materia_no_cronograma(plano):
    """Direito Penal no mini nao esta no bloco `materias`: vale a da prova."""
    _responder(1, True, SEG, classificar_em=NO_TEMPO)

    assert por_conteudo.por_no(plano=plano, hoje=HOJE)[NO_TEMPO].meta in (
        None, regua.META_DA_PROVA)


def test_dias_diferentes_contam_para_o_estado_mais_alto(plano):
    """12 respostas no subassunto, 11 certas, em dois dias: o dobro do minimo
    (6) com 2 dias e "bom desempenho"."""
    for numero in range(1, 7):
        _responder(numero, True, SEG, classificar_em=NO_TEMPO)
    for numero in range(7, 13):
        _responder(numero, numero < 12, TER, classificar_em=NO_TEMPO)

    no = por_conteudo.por_no(plano=plano, hoje=HOJE)[NO_TEMPO]

    assert no.dias == 2 and no.respostas == 12
    assert no.estado(regua.Minimos(por_nivel={"subassunto": 6},
                                   meta_padrao=79)).nome == regua.BOM_COM_AMOSTRA


# --- o recorte de tempo ---------------------------------------------------------

def test_o_padrao_e_o_ciclo_em_andamento(plano):
    """Resposta de antes do ciclo nao entra no recorte padrao, e entra no
    "desde o inicio"."""
    _responder(1, True, date(2026, 9, 1), classificar_em=NO_TEMPO)

    assert por_conteudo.por_no(por_conteudo.CICLO, plano, HOJE) == {}
    desde_sempre = por_conteudo.por_no(por_conteudo.SEMPRE, plano, HOJE)
    assert desde_sempre[NO_TEMPO].radar.respostas == 1


# --- a tela ---------------------------------------------------------------------

def test_a_tela_vem_em_ordem_de_arvore_e_com_o_recuo(plano):
    _responder(1, True, SEG, classificar_em=NO_TEMPO)
    _responder(2, True, SEG, materia=PORTUGUES, classificar_em=PORTUGUES)

    linhas = por_conteudo.tela(plano=plano, hoje=HOJE)

    assert [l.caminho for l in linhas] == [PENAL, APLICACAO, NO_TEMPO, PORTUGUES]
    assert [l.profundidade for l in linhas] == [0, 1, 2, 0]


def test_a_tela_filtra_por_materia(plano):
    _responder(1, True, SEG, classificar_em=NO_TEMPO)
    _responder(2, True, SEG, materia=PORTUGUES, classificar_em=PORTUGUES)

    linhas = por_conteudo.tela(materia=PORTUGUES, plano=plano, hoje=HOJE)

    assert [l.caminho for l in linhas] == [PORTUGUES]


def test_o_filtro_de_materia_ignora_acento_e_caixa(plano):
    """F3: "lingua portuguesa", digitado no terminal sem acento, e a materia
    "Língua Portuguesa" da arvore - antes, "Nada respondido"."""
    _responder(2, True, SEG, materia=PORTUGUES, classificar_em=PORTUGUES)

    linhas = por_conteudo.tela(materia="lingua portuguesa", plano=plano, hoje=HOJE)

    assert [l.caminho for l in linhas] == [PORTUGUES]


def test_abaixo_do_minimo_a_tela_escreve_a_frase_e_nao_a_conclusao(plano):
    _responder(1, True, SEG, classificar_em=NO_TEMPO)

    (linha,) = [l for l in por_conteudo.tela(plano=plano, hoje=HOJE)
                if l.caminho == NO_TEMPO]

    assert linha.estado.nome == regua.INSUFICIENTE
    assert "Amostra insuficiente" in linha.frase
    assert "abaixo das 6" in linha.frase
    # O numero continua a vista: a tela mostra o que eu fiz.
    assert linha.estado.porcentagem == 100


def test_o_no_sem_resposta_nenhuma_nao_entra_na_tela(plano):
    _responder(1, True, SEG, classificar_em=NO_TEMPO)

    assert PORTUGUES not in [l.caminho for l in
                             por_conteudo.tela(plano=plano, hoje=HOJE)]


def test_do_no_devolve_um_so_e_none_quando_nunca_respondi(plano):
    _responder(1, True, SEG, classificar_em=NO_TEMPO)

    assert por_conteudo.do_no(NO_TEMPO, plano=plano, hoje=HOJE).caminho == NO_TEMPO
    assert por_conteudo.do_no(PORTUGUES, plano=plano, hoje=HOJE) is None


# --- o anotado no vocabulario das outras telas ----------------------------------

def test_o_anotado_sai_por_materia_e_por_assunto(plano):
    _anotar(plano, "noite", 0, 15, 11, conteudo=NO_TEMPO)

    por_materia = por_conteudo.anotado_por_materia(plano=plano, hoje=HOJE)
    por_assunto = por_conteudo.anotado_por_assunto(plano=plano, hoje=HOJE)

    assert por_materia[PENAL].respostas == 15 and por_materia[PENAL].acertos == 11
    assert por_materia[PENAL].porcentagem == 73
    assert por_assunto[(PENAL, "Aplicação da lei penal")].respostas == 15


def test_o_no_que_para_na_materia_nao_vira_assunto(plano):
    """Distribuir "Direito Penal" por um assunto qualquer seria inventar.

    Vai pelo estudo extra: a faixa de 28/09 aponta para o assunto, e descer
    dela para a materia seria sair do ramo - o que a faixa recusa.
    """
    estudo_extra.anotar(data=SEG, o_que="questoes", minutos=30, questoes=10,
                        acertos=7, conteudo=PENAL, plano=plano, hoje=HOJE)

    assert por_conteudo.anotado_por_assunto(plano=plano, hoje=HOJE) == {}
    assert por_conteudo.anotado_por_materia(plano=plano, hoje=HOJE)[PENAL].respostas == 10


def test_o_anotado_com_consulta_nao_sai_em_lugar_nenhum(plano):
    _anotar(plano, "noite", 0, 10, 10, consulta=True, conteudo=NO_TEMPO)

    assert por_conteudo.anotado_por_materia(plano=plano, hoje=HOJE) == {}


# --- o seletor recusa o que nao cabe --------------------------------------------

def test_a_faixa_recusa_no_de_fora_do_ramo_dela(plano):
    with pytest.raises(diario.RegistroInvalido, match="não está dentro de"):
        _anotar(plano, "noite", 0, 10, 7, conteudo=PORTUGUES)


def test_a_faixa_recusa_no_que_nao_existe(plano):
    with pytest.raises(diario.RegistroInvalido, match="não está na árvore"):
        _anotar(plano, "noite", 0, 10, 7, conteudo="Direito Penal > Inventado")


def test_sem_escolher_nada_vale_o_no_da_faixa(plano):
    _anotar(plano, "noite", 0, 10, 7)

    assert por_conteudo.por_no(plano=plano, hoje=HOJE)[APLICACAO].anotado.respostas == 10


def test_o_estudo_extra_recusa_no_que_nao_existe(plano):
    with pytest.raises(estudo_extra.RegistroInvalido, match="não está na árvore"):
        estudo_extra.anotar(data=SEG, o_que="questoes", minutos=30, questoes=10,
                            acertos=7, conteudo="Nada > Disso",
                            plano=plano, hoje=HOJE)


def test_o_estudo_extra_entra_no_no_escolhido(plano):
    estudo_extra.anotar(data=SEG, o_que="questoes", minutos=30, questoes=10,
                        acertos=7, conteudo=NO_TEMPO, plano=plano, hoje=HOJE)

    assert por_conteudo.por_no(plano=plano, hoje=HOJE)[NO_TEMPO].anotado.respostas == 10


# --- a tela web e o comando -----------------------------------------------------

def test_a_pagina_mostra_o_estado_a_divisao_e_a_amostra(plano, monkeypatch):
    from fastapi.testclient import TestClient

    from radar.web.app import app

    monkeypatch.setattr("radar.cronograma.carregar", lambda *a, **k: plano)
    _responder(1, True, SEG, classificar_em=NO_TEMPO)
    _anotar(plano, "noite", 0, 10, 8, conteudo=NO_TEMPO)

    texto = TestClient(app).get("/analises/desempenho").text

    assert "Meu desempenho por conteúdo" in texto
    assert "radar 100% em 1 · anotado 80% em 10" in texto
    assert "Amostra insuficiente" in texto
    assert "respostas sem consulta" in texto
    # A divisao nunca e somada num numero so na frase da tela.
    assert "11 respostas no radar" not in texto


def test_a_pagina_sem_nada_convida_em_vez_de_mostrar_zero(plano, monkeypatch):
    from fastapi.testclient import TestClient

    from radar.web.app import app

    monkeypatch.setattr("radar.cronograma.carregar", lambda *a, **k: plano)

    texto = TestClient(app).get("/analises/desempenho").text

    assert "Ainda não respondi nada neste recorte" in texto
    # Nenhum zero por cento na TABELA: ela nem existe sem dado.
    assert "<tbody>" not in texto


def test_a_pagina_nao_tem_texto_com_cara_de_previsao(plano, monkeypatch):
    from fastapi.testclient import TestClient

    from radar.web.app import app

    monkeypatch.setattr("radar.cronograma.carregar", lambda *a, **k: plano)
    _responder(1, True, SEG, classificar_em=NO_TEMPO)

    texto = TestClient(app).get("/analises/desempenho").text.lower()

    for proibido in ("vai cair", "certamente", "sempre cobra", "você é fraco"):
        assert proibido not in texto, proibido


def test_a_pagina_nao_usa_javascript(plano, monkeypatch):
    """O cronometro continua sendo o unico JS do projeto."""
    from fastapi.testclient import TestClient

    from radar.web.app import app

    monkeypatch.setattr("radar.cronograma.carregar", lambda *a, **k: plano)

    texto = TestClient(app).get("/analises/desempenho").text

    assert "<script" not in texto and "onchange=" not in texto
