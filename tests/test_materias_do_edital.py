"""O bloco `materias` do config/cronograma.yml: a prova e a minha meta.

As questoes de cada materia sao do edital de 2019, o ultimo; a meta e minha, e
a soma delas e a meta da prova inteira. O que se testa aqui e a LEITURA e as
tres regras de conferencia - nao o conteudo: trocar uma meta nao pode quebrar
teste nenhum.
"""
from datetime import date
from pathlib import Path

import pytest
import yaml

from radar import config, cronograma

REAL = config.RAIZ / "config" / "cronograma.yml"
MINI = Path(__file__).parent / "fixtures" / "cronograma_mini.yml"


def _com_materias(tmp_path, materias, mistas=None, mudar_dias=None):
    """Grava uma copia do mini com outro bloco `materias`."""
    dados = yaml.safe_load(MINI.read_text(encoding="utf-8"))
    dados["materias"] = materias
    if mistas is not None:
        dados["materias_mistas"] = mistas
    if mudar_dias:
        mudar_dias(dados["dias"])
    arquivo = tmp_path / "cronograma.yml"
    arquivo.write_text(yaml.safe_dump(dados, allow_unicode=True), encoding="utf-8")
    return arquivo


def _tres():
    return [
        {"nome": "Direito Penal", "questoes": 5, "meta": 4},
        {"nome": "Língua Portuguesa", "questoes": 15, "meta": 12},
        {"nome": "Raciocínio Lógico", "questoes": 10, "meta": 9},
    ]


# --- o arquivo de verdade -----------------------------------------------------

def test_a_prova_tem_100_questoes_e_a_meta_e_a_soma():
    plano = cronograma.carregar(REAL)
    assert len(plano.materias) == 11
    assert plano.questoes_da_prova == 100
    assert plano.meta_total == 79
    assert plano.meta_total == sum(m.meta for m in plano.materias)


def test_acha_a_materia_pelo_nome_e_calcula_a_porcentagem():
    plano = cronograma.carregar(REAL)
    lep = plano.materia("Lei de Execução Penal")
    assert (lep.questoes, lep.meta) == (10, 8)
    assert lep.porcentagem_da_meta == 80
    assert plano.materia("Direito Tributário") is None
    assert plano.materia(None) is None


def test_toda_materia_das_faixas_existe_no_bloco():
    """E o que o carregamento confere; aqui eu confiro que o arquivo obedece."""
    plano = cronograma.carregar(REAL)
    conhecidas = {m.nome for m in plano.materias} | set(plano.materias_mistas)
    usadas = {f.materia for dia in plano.dias for f in dia.faixas() if f.materia}
    assert usadas <= conhecidas


def test_a_faixa_mista_nao_e_materia_do_edital():
    """O R+7 dos diagnosticos refaz Raciocinio Logico e Portugues juntos: ele
    conta no geral e em nenhuma materia, como o simulado misto de sabado."""
    plano = cronograma.carregar(REAL)
    assert plano.materias_mistas == ["Diagnósticos"]
    assert plano.e_mista("Diagnósticos")
    assert plano.materia("Diagnósticos") is None
    assert not plano.e_mista("Direito Penal")


# --- a conferencia ------------------------------------------------------------

def test_arquivo_sem_o_bloco_continua_valendo(tmp_path):
    """O mini nao tem `materias`: nada que ja existia pode depender dele."""
    plano = cronograma.carregar(MINI)
    assert plano.materias == []
    assert plano.meta_total == 0


def test_nome_repetido_e_recusado(tmp_path):
    materias = _tres() + [{"nome": "Direito Penal", "questoes": 5, "meta": 3}]
    with pytest.raises(cronograma.ErroNoCronograma, match="aparece duas vezes"):
        cronograma.carregar(_com_materias(tmp_path, materias))


def test_meta_maior_que_as_questoes_e_recusada(tmp_path):
    materias = _tres()
    materias[0]["meta"] = 6           # a prova so tem 5 de Direito Penal
    with pytest.raises(cronograma.ErroNoCronograma, match="maior que as questoes"):
        cronograma.carregar(_com_materias(tmp_path, materias))


def test_meta_igual_as_questoes_pode(tmp_path):
    """Administracao Publica e assim no arquivo real: 5 questoes, meta 5."""
    materias = _tres()
    materias[0]["meta"] = 5
    plano = cronograma.carregar(_com_materias(tmp_path, materias))
    assert plano.materia("Direito Penal").meta == 5


@pytest.mark.parametrize("mudanca, erro", [
    ({"nome": ""}, "falta o `nome`"),
    ({"questoes": "cinco"}, "numeros inteiros"),
    ({"questoes": 0}, "maior que zero"),
    ({"meta": -1}, "nao pode ser negativa"),
])
def test_item_estragado_e_recusado(tmp_path, mudanca, erro):
    materias = _tres()
    materias[0].update(mudanca)
    with pytest.raises(cronograma.ErroNoCronograma, match=erro):
        cronograma.carregar(_com_materias(tmp_path, materias))


def test_materia_de_faixa_que_nao_esta_na_lista_e_recusada(tmp_path):
    """O erro de digitacao que ninguem veria: a materia sumiria de toda conta."""
    def digitar_errado(dias):
        dias[0]["manha"][0]["materia"] = "Direito Penall"

    with pytest.raises(cronograma.ErroNoCronograma, match="Direito Penall"):
        cronograma.carregar(_com_materias(tmp_path, _tres(), mudar_dias=digitar_errado))


def test_faixa_sem_materia_nao_e_conferida(tmp_path):
    """Pausa, correcao e simulado misto nao tem materia - e esta tudo certo."""
    def tirar_a_materia(dias):
        dias[0]["manha"][0].pop("materia")

    plano = cronograma.carregar(
        _com_materias(tmp_path, _tres(), mudar_dias=tirar_a_materia))
    assert plano.dia(date(2026, 9, 28)).manha[0].materia is None


def test_materia_declarada_como_mista_e_aceita(tmp_path):
    def rotular(dias):
        dias[0]["manha"][0]["materia"] = "Diagnósticos"

    plano = cronograma.carregar(
        _com_materias(tmp_path, _tres(), mistas=["Diagnósticos"], mudar_dias=rotular))
    assert plano.e_mista("Diagnósticos")
