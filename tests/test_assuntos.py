"""Assunto fino da questao, pela API da Claude.

Esta e a unica parte do radar que custa dinheiro, e por isso os testes aqui
guardam sobretudo o que controla o gasto: uma questao por enunciado, teto
conferido antes de cada lote, e simulacao por padrao.

Nenhum teste fala com a API: a resposta e de mentira.
"""
import json

import pytest

from radar import assuntos, servico
from radar.db import sessao
from radar.models import QuestaoDeProva


def _questao(numero: int, **mudancas) -> QuestaoDeProva:
    base = dict(
        prova_url=f"https://x.test/p{numero}.pdf",
        banca="FEPESE",
        ano=2024,
        municipio="Palhoca",
        cargo="Assistente Social",
        numero=numero,
        materia="Conhecimentos Específicos",
        enunciado=f"Sobre politicas sociais no Brasil, questao {numero}?",
        alternativas={"a": "um", "b": "dois"},
        resposta="a",
        impressao=f"i{numero}",
    )
    base.update(mudancas)
    return QuestaoDeProva(**base)


def _semear(*questoes):
    with sessao() as s:
        for q in questoes:
            s.add(q)


class _Resposta:
    def __init__(self, texto, entrada=100, saida=20):
        self._texto = texto
        self._uso = {"input_tokens": entrada, "output_tokens": saida}

    def raise_for_status(self):
        return None

    def json(self):
        return {
            "content": [{"type": "text", "text": self._texto}],
            "usage": self._uso,
        }


class _SessaoFalsa:
    """Responde o que o teste mandar e anota o que foi enviado."""

    def __init__(self, respostas, entrada=100, saida=20):
        self.respostas = list(respostas)
        self.pedidos = []
        self.entrada = entrada
        self.saida = saida

    def post(self, url, headers=None, json=None, timeout=None):
        self.pedidos.append(json or {})
        texto = self.respostas.pop(0) if self.respostas else "{}"
        return _Resposta(texto, self.entrada, self.saida)


# --- o que e enviado --------------------------------------------------------

def test_o_pedido_leva_o_enunciado_numerado():
    pedido = assuntos._montar_pedido([_questao(1), _questao(2)])

    assert pedido.startswith("1. ")
    assert "\n\n2. " in pedido


def test_o_enunciado_vai_cortado():
    """O assunto aparece nas primeiras linhas; o resto so encarece."""
    longa = _questao(1, enunciado="palavra " * 500)

    pedido = assuntos._montar_pedido([longa])

    assert len(pedido) < assuntos.LIMITE_DO_ENUNCIADO + 60


def test_as_alternativas_nao_sao_enviadas():
    """Elas sao a maior parte do texto e nao ajudam a dizer o assunto."""
    questao = _questao(1, alternativas={"a": "ALTERNATIVA SECRETA"})

    assert "SECRETA" not in assuntos._montar_pedido([questao])


# --- o que volta ------------------------------------------------------------

def test_le_o_json_da_resposta():
    lido = assuntos._ler_resposta('{"1": "Etica profissional"}', 1)

    assert lido == {1: "Etica profissional"}


def test_json_cercado_de_texto_ainda_e_lido():
    """O modelo as vezes responde com ```json ... ``` ou uma frase antes."""
    lido = assuntos._ler_resposta('Claro!\n```json\n{"1": "Crase"}\n```', 1)

    assert lido == {1: "Crase"}


def test_resposta_sem_json_nao_quebra():
    assert assuntos._ler_resposta("nao consegui", 3) == {}


def test_numero_fora_do_lote_e_ignorado():
    """O modelo as vezes inventa item alem do que foi pedido."""
    lido = assuntos._ler_resposta('{"1": "Etica", "99": "Inventado"}', 1)

    assert lido == {1: "Etica"}


def test_indefinido_nao_vira_assunto(banco_temporario):
    """Melhor sem assunto que com rotulo vazio de sentido."""
    sessao_falsa = _SessaoFalsa(['{"1": "indefinido", "2": "Politicas sociais"}'])
    _semear(_questao(1), _questao(2))
    with sessao() as s:
        questoes = list(s.scalars(servico.select(QuestaoDeProva)))

    por_id, _, _ = assuntos.classificar_lote(questoes, "chave", sessao_falsa)

    assert len(por_id) == 1


# --- o gasto ----------------------------------------------------------------

def test_a_estimativa_cresce_com_a_quantidade():
    _, _, pouco = assuntos.estimar([_questao(n) for n in range(5)])
    _, _, muito = assuntos.estimar([_questao(n) for n in range(50)])

    assert muito > pouco > 0


def test_estimativa_de_lista_vazia_e_zero():
    assert assuntos.estimar([]) == (0, 0, 0.0)


def test_o_custo_usa_o_que_a_api_informou():
    uso = assuntos.Uso()
    uso.somar(1_000_000, 0)

    assert uso.custo == pytest.approx(assuntos.PRECO_ENTRADA)


def test_para_no_teto_de_gasto(banco_temporario):
    """O teto e conferido ANTES de cada chamada, com o custo real acumulado."""
    questoes = [_questao(n, impressao=f"i{n}") for n in range(100)]
    _semear(*questoes)
    with sessao() as s:
        todas = list(s.scalars(servico.select(QuestaoDeProva)))

    # cada chamada "gasta" 1 milhao de tokens de entrada = US$ 1
    sessao_falsa = _SessaoFalsa(['{"1": "Etica"}'] * 10, entrada=1_000_000)

    resultado = assuntos.classificar(todas, "chave", teto_em_dolar=1.5,
                                     sessao=sessao_falsa)

    assert resultado.parou_no_teto
    assert len(sessao_falsa.pedidos) == 2, "para na chamada seguinte a estourar"


def test_lote_que_falha_nao_derruba_os_outros(banco_temporario):
    class _MeioQuebrada(_SessaoFalsa):
        def post(self, *a, **k):
            if len(self.pedidos) == 0:
                self.pedidos.append({})
                raise OSError("timeout")
            return super().post(*a, **k)

    questoes = [_questao(n, impressao=f"i{n}") for n in range(assuntos.POR_LOTE + 5)]
    _semear(*questoes)
    with sessao() as s:
        todas = list(s.scalars(servico.select(QuestaoDeProva)))

    resultado = assuntos.classificar(
        todas, "chave", teto_em_dolar=99, sessao=_MeioQuebrada(['{"1": "Etica"}'])
    )

    assert resultado.falhas == 1
    assert resultado.classificados


# --- quem entra na fila -----------------------------------------------------

def test_so_entra_materia_que_o_catalogo_nao_cobre(banco_temporario):
    """Portugues, Raciocinio, Informatica e Gerais ja tem assunto de graca."""
    _semear(
        _questao(1, materia="Língua Portuguesa"),
        _questao(2, materia="Conhecimentos Específicos", impressao="b"),
    )

    pendentes = servico.questoes_sem_assunto()

    assert [q.materia for q in pendentes] == ["Conhecimentos Específicos"]


def test_uma_questao_por_enunciado(banco_temporario):
    """Das 2.673 questoes de especificos, so 1.763 tem enunciado diferente.
    Classificar a mesma pergunta duas vezes seria pagar duas vezes."""
    _semear(*[_questao(n, impressao="a-mesma") for n in range(5)])

    assert len(servico.questoes_sem_assunto()) == 1


def test_questao_que_ja_tem_assunto_fica_de_fora(banco_temporario):
    _semear(_questao(1, assunto="Etica profissional"))

    assert servico.questoes_sem_assunto() == []


def test_o_limite_e_respeitado(banco_temporario):
    _semear(*[_questao(n, impressao=f"i{n}") for n in range(10)])

    assert len(servico.questoes_sem_assunto(limite=3)) == 3


# --- gravar -----------------------------------------------------------------

def test_o_assunto_se_espalha_para_as_copias(banco_temporario):
    """Uma classificacao paga rotula todas as copias daquela pergunta - e o
    que faz o gasto valer mais."""
    _semear(*[_questao(n, impressao="a-mesma") for n in range(4)])
    with sessao() as s:
        alvo = s.scalars(servico.select(QuestaoDeProva)).first().id

    servico.gravar_assuntos({alvo: "Politicas sociais"})

    with sessao() as s:
        todas = list(s.scalars(servico.select(QuestaoDeProva)))
    assert all(q.assunto == "Politicas sociais" for q in todas)


def test_gravar_nada_nao_quebra(banco_temporario):
    assert servico.gravar_assuntos({}) == 0


def test_sem_chave_o_servico_avisa_em_vez_de_tentar(banco_temporario, monkeypatch):
    """Nao adianta chamar a API sem chave: melhor dizer o que falta."""
    from radar import config

    monkeypatch.setattr(config, "chave_da_anthropic", lambda: None)
    _semear(_questao(1))

    assert servico.classificar_assuntos()["erro"] == "sem chave"
