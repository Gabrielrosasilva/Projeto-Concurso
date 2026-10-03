"""Onde a faixa esta na arvore: o assunto, o subassunto e o elemento na propria
faixa (subetapa 2C, decisao 71).

O que estes testes seguram:
  - pela ficha: os nos agrupados por assunto, com os subassuntos; sem no, o
    assunto que ela escreveu e a frase de que nao ha subassunto para o tema;
  - "o assunto inteiro" so quando o no escolhido e o proprio assunto e a
    arvore tem subassunto nele;
  - sem ficha, os nos que o plano da para a faixa (📌), e nenhum no e criado;
  - a chave `nos` do cronograma e conferida contra a arvore e a materia;
  - o bonus e a interpretacao cronometrada tem nos de hoje em diante, e os
    dias passados nao ganharam nada;
  - a tela Hoje mostra a linha.
"""
import json
from datetime import date

import pytest
from fastapi.testclient import TestClient

from radar import cronograma, fichas
from radar.cronograma import Faixa
from radar.fichas import FichaEscrita
from radar.origem import IA, PLANO
from radar.servico import conteudos
from radar.servico import fichas as servico_fichas
from radar.web.app import app
from tests.test_composicao import CONFIG, PROGRAMA

LEP = "Lei de Execução Penal"
ASSUNTO_LEP = "Lei de Execução Penal (Lei nº 7.210 de 11 de julho de 1984)"
GARANTIAS = "Direito Constitucional > Direitos e garantias"
CAMINHOS = {
    "Língua Portuguesa", "Língua Portuguesa > Vozes do verbo",
    "Língua Portuguesa > Vozes do verbo > Voz passiva analítica e sintética",
    "Língua Portuguesa > Ortografia oficial",
    "Direito Constitucional", GARANTIAS,
    f"{GARANTIAS} > Inviolabilidade do domicílio", f"{GARANTIAS} > Remédios constitucionais",
    "Direito Constitucional > direitos sociais",
    LEP, f"{LEP} > {ASSUNTO_LEP}", f"{LEP} > {ASSUNTO_LEP} > Remição",
}
HOJE = date(2026, 10, 3)


def _ficha(tema, materia, **campos):
    return FichaEscrita(tema=tema, materia=materia, modelo="teste",
                        criado_em="2026-09-27", **campos)


def _faixa(materia=None, **campos):
    return Faixa(bloco="noite", tipo="questoes", titulo="Questões", materia=materia,
                 questoes=10, **campos)


# --- pela ficha ---------------------------------------------------------------------

def test_pela_ficha_os_nos_se_agrupam_por_assunto():
    ficha = _ficha("Art. 5º", "Direito Constitucional", nos=[
        f"{GARANTIAS} > Inviolabilidade do domicílio", f"{GARANTIAS} > Remédios constitucionais",
        "Direito Constitucional > direitos sociais"],
        elemento="CF, art. 5º", tipo_elemento="inciso")

    onde = fichas.onde_na_arvore(_faixa("Direito Constitucional"), ficha, CAMINHOS)

    assert onde.origem == IA and not onde.sem_no
    garantias, sociais = onde.assuntos
    assert garantias.nome == "Direitos e garantias"
    assert garantias.subassuntos == ("Inviolabilidade do domicílio", "Remédios constitucionais")
    assert not sociais.subassuntos and not sociais.inteiro    # a arvore nao tem subassunto ali
    assert (onde.elemento, onde.tipo_elemento) == ("CF, art. 5º", "inciso")


def test_o_assunto_inteiro_so_quando_o_no_e_o_assunto_e_a_arvore_tem_subassunto():
    ficha = _ficha("Vozes do verbo", "Língua Portuguesa",
                   nos=["Língua Portuguesa > Vozes do verbo"])
    (vozes,) = fichas.onde_na_arvore(_faixa(), ficha, CAMINHOS).assuntos
    assert vozes.inteiro and not vozes.subassuntos


def test_ficha_sem_no_diz_que_nao_ha_subassunto_para_o_tema():
    """A LEP tem subassunto na arvore (Remicao), mas nao para o trabalho do
    preso: a ficha nao aponta no, e a faixa nao e "o assunto inteiro"."""
    ficha = _ficha("Trabalho do preso (arts. 28 a 37)", LEP, assunto=ASSUNTO_LEP,
                   elemento="LEP, arts. 28 a 37", tipo_elemento="artigo")

    onde = fichas.onde_na_arvore(_faixa(LEP), ficha, CAMINHOS)

    (assunto,) = onde.assuntos
    assert onde.sem_no and onde.origem == IA
    assert assunto.nome == ASSUNTO_LEP
    assert not assunto.subassuntos and not assunto.inteiro
    assert onde.elemento == "LEP, arts. 28 a 37"


def test_ficha_sem_no_com_subassunto_mostra_o_subassunto():
    ficha = _ficha("Remição", LEP, assunto=ASSUNTO_LEP, subassunto="Remição")
    (assunto,) = fichas.onde_na_arvore(_faixa(LEP), ficha, CAMINHOS).assuntos
    assert assunto.subassuntos == ("Remição",)


# --- sem ficha --------------------------------------------------------------------------

def test_sem_ficha_valem_os_nos_do_plano():
    faixa = _faixa("Língua Portuguesa", nos=("Língua Portuguesa > Vozes do verbo",
                                             "Língua Portuguesa > Ortografia oficial"))
    onde = fichas.onde_na_arvore(faixa, None, CAMINHOS)
    assert onde.origem == PLANO and onde.elemento is None
    assert [a.nome for a in onde.assuntos] == ["Vozes do verbo", "Ortografia oficial"]


def test_sem_nos_vale_o_conteudo_e_sem_nada_nao_diz_nada():
    pelo_conteudo = fichas.onde_na_arvore(
        _faixa(conteudo="Língua Portuguesa > Ortografia oficial"), None, CAMINHOS)
    assert [a.nome for a in pelo_conteudo.assuntos] == ["Ortografia oficial"]
    assert fichas.onde_na_arvore(_faixa(), None, CAMINHOS) is None


# --- o cronograma ---------------------------------------------------------------------

def _plano_com(tmp_path, antigo, novo):
    texto = (CONFIG / "cronograma.yml").read_text(encoding="utf-8")
    assert antigo in texto
    arquivo = tmp_path / "cronograma.yml"
    arquivo.write_text(texto.replace(antigo, novo, 1), encoding="utf-8")
    return arquivo


def test_no_que_nao_esta_na_arvore_e_erro(tmp_path):
    arquivo = _plano_com(tmp_path, "    - Raciocínio Lógico > Tabelas-verdade\n",
                         "    - Raciocínio Lógico > Tabelas-verdadi\n")
    with pytest.raises(cronograma.ErroNoCronograma, match="Tabelas-verdadi"):
        cronograma.carregar(arquivo)


def test_no_de_outra_materia_e_erro(tmp_path):
    arquivo = _plano_com(tmp_path, "    - Raciocínio Lógico > Tabelas-verdade\n",
                         "    - Língua Portuguesa > Ortografia oficial\n")
    with pytest.raises(cronograma.ErroNoCronograma, match="outra matéria"):
        cronograma.carregar(arquivo)


def test_o_bonus_e_a_interpretacao_tem_nos_de_hoje_em_diante():
    plano = cronograma.carregar(CONFIG / "cronograma.yml")
    bonus = [(d.data, f) for d in plano.dias for f in d.faixas()
             if f.titulo == "Bônus: lógica proposicional"]
    interpretacao = [(d.data, f) for d in plano.dias for f in d.faixas()
                     if f.titulo == "Interpretação de texto (cronometrada)"]

    for data, faixa in bonus + interpretacao:
        assert bool(faixa.nos) == (data >= HOJE), data       # o passado nao muda
    assert sum(1 for data, _ in bonus if data >= HOJE) == 25
    assert sum(1 for data, _ in interpretacao if data >= HOJE) == 5
    assert bonus[-1][1].nos == ("Raciocínio Lógico > Lógica proposicional (ou sentencial)",
                                "Raciocínio Lógico > Tabelas-verdade",
                                "Raciocínio Lógico > Equivalências")
    assert interpretacao[-1][1].nos == (
        "Língua Portuguesa > Compreensão e interpretação de texto (s)",)


# --- a tela ------------------------------------------------------------------------------

def test_a_tela_hoje_mostra_o_assunto_na_faixa(banco_temporario):
    conteudos.semear(programa=PROGRAMA)
    servico_fichas.caminho_do_arquivo().write_text(json.dumps([{
        "tema": "Trabalho do preso (arts. 28 a 37)", "materia": LEP, "assunto": ASSUNTO_LEP,
        "elemento": "LEP, arts. 28 a 37", "tipo_elemento": "artigo",
        "modelo": "teste", "criado_em": "2026-09-27"}]), encoding="utf-8")

    pagina = TestClient(app).get("/hoje?data=2026-10-07").text

    assert 'class="na-arvore"' in pagina
    assert "não há subassunto na árvore para este tema" in pagina
    assert "Elemento: LEP, arts. 28 a 37" in pagina
    assert "A ficha não aponta nó da árvore" in pagina
    assert "Assunto: <b>Tabelas-verdade</b>" in pagina          # o bonus, pelo plano
    assert "ds-selo--plano" in pagina and "ds-selo--ia" in pagina
