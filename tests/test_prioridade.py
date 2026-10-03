"""A prioridade de estudo das fichas (Etapa 6B, secao 15 do novo.md).

O que estes testes seguram: a regra mora no config/prioridade.yml e mudar um
peso la muda a conta; a conta e reproduzivel; o acervo complementar entra
SEPARADO e com o peso declarado - com peso 0 ele nao mexe na ordem -; tema que
nao apareceu no alvo nao zera, mas fica abaixo de quem apareceu; o desempenho e
o tempo so pesam com amostra suficiente; e nenhum texto fala como previsao.
"""
import re
from dataclasses import dataclass
from datetime import date

import pytest

from radar import amostra, prioridade

HOJE = date(2026, 10, 20)
PREVISAO = re.compile(r"(?i)vai cair|certamente|sempre cobra|cairá")


def _calcular(**mudar):
    base = dict(materia="Direito Constitucional", questoes_da_materia=5,
                questoes_da_prova=100, alvo_no_escopo=1, alvo_na_materia=10,
                complementar_no_escopo=0, complementar_na_materia=0,
                estado=None, ultima=None, motivos_da_revisao=[], hoje=HOJE,
                regra=prioridade.Regra())
    base.update(mudar)
    return prioridade.calcular(**base)


def _estado(respostas, acertos, nivel="subassunto"):
    return amostra.estado(respostas, acertos, nivel=nivel, meta=80, dias=2)


# --- a regra mora no YAML ---------------------------------------------------------

def test_a_regra_vem_do_config_real():
    regra = prioridade.carregar()
    assert regra.piso_em_questoes == 0.5
    assert regra.peso_do_complementar == 0.25
    assert (regra.dias_para_dobrar, regra.fator_maximo) == (30, 2.0)
    assert regra.multiplicador_da_revisao == 1.5


def test_mudar_o_peso_no_yaml_muda_a_conta(tmp_path):
    arquivo = tmp_path / "prioridade.yml"
    arquivo.write_text("incidencia:\n  peso_do_complementar: 0.5\n", encoding="utf-8")
    com_meio = prioridade.carregar(arquivo)
    assert com_meio.peso_do_complementar == 0.5
    assert com_meio.piso_em_questoes == 0.5          # o resto fica no padrao

    a = _calcular(complementar_no_escopo=2, complementar_na_materia=10)
    b = _calcular(complementar_no_escopo=2, complementar_na_materia=10, regra=com_meio)
    assert b.valor > a.valor


def test_sem_o_arquivo_vale_o_padrao(tmp_path):
    assert prioridade.carregar(tmp_path / "nao-existe.yml") == prioridade.Regra()


# --- a conta ----------------------------------------------------------------------

def test_a_conta_e_reproduzivel_e_escrita_inteira():
    a = _calcular(complementar_no_escopo=2, complementar_na_materia=34)
    b = _calcular(complementar_no_escopo=2, complementar_na_materia=34)
    assert a.valor == b.valor
    # 5 x (1/10 + 0,25 x 2/34) x 1 x 1 x 1
    assert a.valor == pytest.approx(5 * (0.1 + 0.25 * 2 / 34))
    assert a.conta.endswith(f"= {prioridade.numero(a.valor, 2)}")
    assert len(a.fatores) == 6


def test_cada_fator_diz_a_origem():
    p = _calcular(complementar_no_escopo=1, complementar_na_materia=4)
    assert p.peso.origem == prioridade.OFICIAL
    assert p.alvo.origem == prioridade.ACERVO
    assert p.complementar.origem == prioridade.ACERVO
    assert {p.desempenho.origem, p.tempo.origem, p.revisao.origem} == {prioridade.AUTOMATICO}


# --- o complementar, separado e com peso menor (§15) -------------------------------

def test_o_complementar_vem_em_fator_proprio_com_o_peso_escrito():
    p = _calcular(complementar_no_escopo=2, complementar_na_materia=34)
    assert "separado do alvo" in p.complementar.texto
    assert "0,25" in p.complementar.texto
    assert "complementar" not in p.alvo.texto


@dataclass
class _Tema:
    tema: str
    p: object


def test_com_peso_zero_o_complementar_nao_muda_a_ordem():
    sem_peso = prioridade.Regra(peso_do_complementar=0)
    # A tem mais alvo; B tem pouco alvo e MUITO complementar.
    a = dict(alvo_no_escopo=2, alvo_na_materia=10)
    b = dict(alvo_no_escopo=1, alvo_na_materia=10,
             complementar_no_escopo=30, complementar_na_materia=30)

    so_alvo = [_Tema("A", _calcular(**a, regra=sem_peso)),
               _Tema("B", _calcular(alvo_no_escopo=1, alvo_na_materia=10, regra=sem_peso))]
    com_complementar_peso_zero = [_Tema("A", _calcular(**a, regra=sem_peso)),
                                  _Tema("B", _calcular(**b, regra=sem_peso))]
    ordem = lambda itens: [t.tema for t in prioridade.ordenar(itens, lambda t: t.p)]
    assert ordem(so_alvo) == ordem(com_complementar_peso_zero) == ["A", "B"]

    # Com o peso declarado, o complementar pesa - e e por isso que ele e
    # declarado, e nao escondido.
    com_peso = [_Tema("A", _calcular(**a)), _Tema("B", _calcular(**b))]
    assert ordem(com_peso) == ["B", "A"]


def test_peso_zero_escreve_que_o_complementar_nao_entra():
    p = _calcular(complementar_no_escopo=3, complementar_na_materia=3,
                  regra=prioridade.Regra(peso_do_complementar=0))
    assert p.complementar.valor == 0
    assert "peso 0" in p.complementar.texto


# --- o piso -----------------------------------------------------------------------

def test_tema_que_nao_apareceu_nao_zera_e_fica_abaixo_de_quem_apareceu():
    nunca = _calcular(alvo_no_escopo=0)
    uma_vez = _calcular(alvo_no_escopo=1)
    assert nunca.valor > 0
    assert nunca.valor < uma_vez.valor
    assert "não apareceu nas provas analisadas" in nunca.alvo.texto
    assert "piso" in nunca.alvo.texto


def test_tema_sem_no_vale_o_piso_mas_nao_diz_que_nao_apareceu():
    """Sem no, o acervo nao foi contado: dizer "nao apareceu nas provas" seria
    afirmar o que ninguem verificou."""
    sem_no = _calcular(alvo_no_escopo=0, sem_no=True,
                       complementar_no_escopo=0, complementar_na_materia=40)
    nunca = _calcular(alvo_no_escopo=0)
    assert sem_no.alvo.valor == nunca.alvo.valor == 0.5 / 10
    assert "não tem nó na árvore" in sem_no.alvo.texto
    assert "não apareceu" not in sem_no.alvo.texto
    assert sem_no.complementar.valor == 0.0
    assert "não tem nó na árvore" in sem_no.complementar.texto


def test_materia_sem_questao_do_alvo_e_neutra_e_diz_isso():
    p = _calcular(alvo_no_escopo=0, alvo_na_materia=0)
    assert p.alvo.valor == 1.0
    assert "não medida" in p.alvo.texto


def test_materia_fora_do_quadro_tem_peso_neutro():
    p = _calcular(questoes_da_materia=None)
    assert p.peso.valor == 1.0
    assert "não está no quadro" in p.peso.texto


# --- desempenho, tempo e revisao ---------------------------------------------------

def test_o_desempenho_so_conta_com_amostra_suficiente():
    pequena = _calcular(estado=_estado(3, 0))            # 0% em 3: sorte, nao medida
    assert pequena.desempenho.valor == 1.0
    assert "amostra insuficiente" in pequena.desempenho.texto

    medida = _calcular(estado=_estado(10, 7))            # 70% em 10
    assert medida.desempenho.valor == pytest.approx(0.3)
    assert "70%" in medida.desempenho.texto

    nunca = _calcular(estado=None)
    assert nunca.desempenho.valor == 1.0


def test_o_tempo_vai_de_1_a_2_e_so_com_amostra():
    medido = _estado(10, 7)
    assert _calcular(estado=medido, ultima=HOJE).tempo.valor == 1.0
    assert _calcular(estado=medido, ultima=date(2026, 10, 5)).tempo.valor == pytest.approx(1.5)
    assert _calcular(estado=medido, ultima=date(2026, 7, 1)).tempo.valor == 2.0
    # Sem amostra nao ha pratica que conte dias.
    assert _calcular(estado=_estado(2, 1), ultima=date(2026, 7, 1)).tempo.valor == 1.0


def test_a_fila_de_revisao_multiplica_e_diz_o_motivo():
    fora = _calcular()
    dentro = _calcular(motivos_da_revisao=["erro recente"])
    assert dentro.valor == pytest.approx(fora.valor * 1.5)
    assert "erro recente" in dentro.revisao.texto
    assert "fora da fila" in fora.revisao.texto


# --- a ordem ----------------------------------------------------------------------

def test_ordenar_escreve_a_posicao_e_desempata_pelo_nome():
    itens = [_Tema("B", _calcular()), _Tema("A", _calcular()),
             _Tema("C", _calcular(alvo_no_escopo=5))]
    ordenados = prioridade.ordenar(itens, lambda t: t.p)
    assert [t.tema for t in ordenados] == ["C", "A", "B"]
    assert [(t.p.posicao, t.p.de) for t in ordenados] == [(1, 3), (2, 3), (3, 3)]


def test_nenhum_texto_com_cara_de_previsao():
    casos = [_calcular(), _calcular(alvo_no_escopo=0), _calcular(estado=_estado(10, 7),
             ultima=date(2026, 10, 1), motivos_da_revisao=["erro recente"],
             complementar_no_escopo=2, complementar_na_materia=8)]
    for p in casos:
        for fator in p.fatores:
            assert not PREVISAO.search(fator.texto), fator.texto
