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

    servico.gravar_assuntos({alvo: "Politicas sociais"}, assuntos.MODELO)

    with sessao() as s:
        todas = list(s.scalars(servico.select(QuestaoDeProva)))
    assert all(q.assunto == "Politicas sociais" for q in todas)


def test_gravar_nada_nao_quebra(banco_temporario):
    assert servico.gravar_assuntos({}, assuntos.MODELO) == 0


def test_a_procedencia_e_gravada_junto_do_assunto(banco_temporario):
    """Qual modelo, e quando. Sem os dois nao ha como auditar depois."""
    _semear(_questao(1))
    with sessao() as s:
        alvo = s.scalars(servico.select(QuestaoDeProva)).first().id

    servico.gravar_assuntos({alvo: "Politicas sociais"}, assuntos.MODELO)

    with sessao() as s:
        questao = s.get(QuestaoDeProva, alvo)
    assert questao.assunto_modelo == assuntos.MODELO
    assert questao.assunto_em is not None


def test_nao_se_grava_assunto_sem_dizer_qual_modelo(banco_temporario):
    """A porta de entrada. Em 24/09/2026 entraram 93 assuntos no banco sem
    nunca terem passado pela API, e nao havia nada que impedisse.

    O erro e levantado, e nao registrado em log: gravar silenciosamente sem
    procedencia e justamente o que nao pode voltar a acontecer.
    """
    _semear(_questao(1))
    with sessao() as s:
        alvo = s.scalars(servico.select(QuestaoDeProva)).first().id

    with pytest.raises(ValueError, match="sem modelo"):
        servico.gravar_assuntos({alvo: "Politicas sociais"}, "")

    with sessao() as s:
        assert s.get(QuestaoDeProva, alvo).assunto is None


def test_sem_chave_o_servico_avisa_em_vez_de_tentar(banco_temporario, monkeypatch):
    """Nao adianta chamar a API sem chave: melhor dizer o que falta."""
    from radar import config

    monkeypatch.setattr(config, "chave_da_anthropic", lambda: None)
    _semear(_questao(1))

    assert servico.classificar_assuntos()["erro"] == "sem chave"


# --- a lista fechada do edital (etapa 14) ----------------------------------
#
# Sem lista, o modelo inventava o nome do assunto - e nome inventado nao se
# encontra com nada. Com ela, ele ESCOLHE dentro do que o edital do meu
# concurso promete cobrar, e o que vier de fora e descartado aqui dentro.

PROGRAMA = {
    "Direitos Humanos": [
        "Teoria geral dos direitos humanos",
        "Regras mínimas da ONU para o tratamento de pessoas presas",
    ],
    "Lei de Execução Penal": [
        "Lei de Execução Penal (Lei nº 7.210 de 11 de julho de 1984)",
    ],
}


def _questao_do_alvo(numero: int, materia: str) -> QuestaoDeProva:
    return _questao(
        numero,
        materia=materia,
        cargo="Agente Penitenciário - Feminino (AP)",
        enunciado=f"Questao {numero} de {materia}?",
    )


def test_o_pedido_leva_a_lista_da_materia():
    pedido = assuntos._montar_pedido(
        [_questao_do_alvo(1, "Direitos Humanos")], PROGRAMA
    )

    assert "ASSUNTOS PERMITIDOS" in pedido
    assert "Regras mínimas da ONU para o tratamento de pessoas presas" in pedido
    assert "[Direitos Humanos]" in pedido


def test_o_pedido_so_leva_a_materia_que_esta_no_lote():
    """Mandar o programa inteiro a cada chamada seria pagar por 85 linhas
    para classificar 25 questoes de duas materias."""
    pedido = assuntos._montar_pedido(
        [_questao_do_alvo(1, "Direitos Humanos")], PROGRAMA
    )
    assert "Lei de Execução Penal" not in pedido


def test_a_instrucao_muda_quando_ha_lista(banco_temporario):
    sessao_falsa = _SessaoFalsa(['{"1": "Teoria geral dos direitos humanos"}'])
    _semear(_questao_do_alvo(1, "Direitos Humanos"))
    with sessao() as s:
        questoes = list(s.scalars(servico.select(QuestaoDeProva)))

    assuntos.classificar_lote(questoes, "chave", sessao_falsa, PROGRAMA)

    assert sessao_falsa.pedidos[0]["system"] == assuntos.INSTRUCAO_COM_LISTA


def test_o_assunto_da_lista_e_aceito(banco_temporario):
    sessao_falsa = _SessaoFalsa(['{"1": "Teoria geral dos direitos humanos"}'])
    _semear(_questao_do_alvo(1, "Direitos Humanos"))
    with sessao() as s:
        questoes = list(s.scalars(servico.select(QuestaoDeProva)))

    por_id, _, _ = assuntos.classificar_lote(questoes, "chave", sessao_falsa, PROGRAMA)

    assert list(por_id.values()) == ["Teoria geral dos direitos humanos"]


def test_o_que_o_modelo_inventa_e_descartado(banco_temporario):
    """A instrucao pede para escolher na lista; aqui e onde isso deixa de ser
    pedido e vira garantia. Rotulo inventado no meio dos do edital seria pior
    que a questao ficar sem assunto: eu nao distinguiria os dois na tela."""
    sessao_falsa = _SessaoFalsa(['{"1": "Dignidade da pessoa humana"}'])
    _semear(_questao_do_alvo(1, "Direitos Humanos"))
    with sessao() as s:
        questoes = list(s.scalars(servico.select(QuestaoDeProva)))

    por_id, _, _ = assuntos.classificar_lote(questoes, "chave", sessao_falsa, PROGRAMA)

    assert por_id == {}


def test_o_assunto_de_outra_materia_nao_vale(banco_temporario):
    """A lista e da materia da PROPRIA questao: um assunto de Lei de Execucao
    Penal numa questao de Direitos Humanos e resposta errada."""
    sessao_falsa = _SessaoFalsa([
        '{"1": "Lei de Execução Penal (Lei nº 7.210 de 11 de julho de 1984)"}'
    ])
    _semear(_questao_do_alvo(1, "Direitos Humanos"))
    with sessao() as s:
        questoes = list(s.scalars(servico.select(QuestaoDeProva)))

    por_id, _, _ = assuntos.classificar_lote(questoes, "chave", sessao_falsa, PROGRAMA)

    assert por_id == {}


def test_acento_e_caixa_nao_reprovam_a_resposta(banco_temporario):
    """O que chega ao banco e sempre o texto do edital, palavra por palavra -
    mesmo quando o modelo devolve sem acento."""
    sessao_falsa = _SessaoFalsa(['{"1": "teoria geral dos direitos humanos"}'])
    _semear(_questao_do_alvo(1, "Direitos Humanos"))
    with sessao() as s:
        questoes = list(s.scalars(servico.select(QuestaoDeProva)))

    por_id, _, _ = assuntos.classificar_lote(questoes, "chave", sessao_falsa, PROGRAMA)

    assert list(por_id.values()) == ["Teoria geral dos direitos humanos"]


def test_indefinido_continua_valendo_com_lista(banco_temporario):
    sessao_falsa = _SessaoFalsa(['{"1": "indefinido"}'])
    _semear(_questao_do_alvo(1, "Direitos Humanos"))
    with sessao() as s:
        questoes = list(s.scalars(servico.select(QuestaoDeProva)))

    por_id, _, _ = assuntos.classificar_lote(questoes, "chave", sessao_falsa, PROGRAMA)

    assert por_id == {}


def test_a_estimativa_com_lista_e_maior():
    """O pedido cresce: alem da instrucao, cada lote leva a lista das materias
    que aparecem nele. Eu preciso ver isso ANTES de rodar valendo."""
    questoes = [_questao_do_alvo(n, "Direitos Humanos") for n in range(10)]
    _, _, sem_lista = assuntos.estimar(questoes)
    _, _, com_lista = assuntos.estimar(questoes, PROGRAMA)

    assert com_lista > sem_lista


# --- so as questoes do MEU cargo (etapa 14) --------------------------------
#
# Classificar o acervo inteiro sao 2.802 questoes, e quase todas sao de cargo
# que eu nunca vou prestar: assunto fino de prova de Merendeira e da mesma
# banca e nao me serve de nada. Com `--so-alvo` sao as 99 das minhas provas.

@pytest.fixture
def programa_do_edital(monkeypatch):
    """Finge que o edital do alvo ja foi lido, com duas materias no programa."""
    from radar import foco

    monkeypatch.setattr(foco, "programa_do_alvo", lambda: PROGRAMA)
    return PROGRAMA


def _concurso_do_alvo():
    from radar.models import Concurso

    return Concurso(
        url="https://fepese.org.br/2019-sap/",
        fonte="fepese",
        titulo="2019 - Secretaria de Estado da Administracao Prisional",
        uf="SC",
        tipo="concurso",
        situacao="encerrado",
        alvo="principal",
    )


def _questao_no_acervo(numero: int, materia: str, minha: bool) -> QuestaoDeProva:
    return _questao(
        numero,
        materia=materia,
        impressao=f"imp{numero}",
        prova_url="https://x.test/ap.pdf" if minha else "https://x.test/outra.pdf",
        concurso_url="https://fepese.org.br/2019-sap/" if minha else None,
        cargo="Agente Penitenciário - Feminino (AP)" if minha else "Merendeira",
    )


def test_so_alvo_deixa_de_fora_a_prova_dos_outros(banco_temporario,
                                                  programa_do_edital):
    with sessao() as s:
        s.add(_concurso_do_alvo())
    _semear(
        _questao_no_acervo(1, "Direitos Humanos", minha=True),
        _questao_no_acervo(2, "Direitos Humanos", minha=False),
    )

    pendentes = servico.questoes_sem_assunto(so_alvo=True)

    assert [q.numero for q in pendentes] == [1]
    assert len(servico.questoes_sem_assunto()) == 2


def test_so_alvo_deixa_de_fora_materia_que_saiu_do_programa(banco_temporario,
                                                            programa_do_edital):
    """2013 cobrou Nocoes de Informatica e Direito Administrativo; 2019 nao
    cobra. Sem lista em que escolher, pagar seria pagar por "indefinido"."""
    with sessao() as s:
        s.add(_concurso_do_alvo())
    _semear(
        _questao_no_acervo(1, "Direitos Humanos", minha=True),
        _questao_no_acervo(2, "Direito Administrativo", minha=True),
    )

    pendentes = servico.questoes_sem_assunto(so_alvo=True)

    assert [q.materia for q in pendentes] == ["Direitos Humanos"]


def test_sem_programa_do_edital_o_servico_nao_gasta(banco_temporario, monkeypatch):
    """Sem a lista a IA voltaria a inventar nome. Nao gastar e a resposta."""
    from radar import foco

    monkeypatch.setattr(foco, "programa_do_alvo", dict)
    monkeypatch.setenv("RADAR_ANTHROPIC_KEY", "chave-de-teste")
    with sessao() as s:
        s.add(_concurso_do_alvo())
    _semear(_questao_no_acervo(1, "Direitos Humanos", minha=True))

    resultado = servico.classificar_assuntos(so_alvo=True)

    assert resultado["classificados"] == 0
    assert "programa" in resultado["erro"]


# --- a cobertura ------------------------------------------------------------

def test_a_cobertura_separa_o_que_e_de_graca_do_que_foi_pago(banco_temporario,
                                                             programa_do_edital):
    with sessao() as s:
        s.add(_concurso_do_alvo())
    _semear(
        _questao_no_acervo(1, "Direitos Humanos", minha=True),
        _questao_no_acervo(2, "Língua Portuguesa", minha=True),
        _questao_no_acervo(3, "Direito Administrativo", minha=True),
    )

    por_materia = {c.materia: c for c in servico.cobertura_de_assunto()}

    assert por_materia["Direitos Humanos"].origem == "edital"
    assert por_materia["Língua Portuguesa"].origem == "catalogo"
    # Materia que o edital de hoje nao cobra mais nunca vai ser classificada.
    assert por_materia["Direito Administrativo"].origem == "fora"


def test_a_cobertura_conta_quem_ja_tem_assunto(banco_temporario,
                                               programa_do_edital):
    with sessao() as s:
        s.add(_concurso_do_alvo())
    _semear(
        _questao_no_acervo(1, "Direitos Humanos", minha=True),
        _questao_no_acervo(2, "Direitos Humanos", minha=True),
    )
    with sessao() as s:
        primeira = s.scalars(servico.select(QuestaoDeProva)).first()
        primeira.assunto = "Teoria geral dos direitos humanos"

    humanos = next(
        c for c in servico.cobertura_de_assunto() if c.materia == "Direitos Humanos"
    )

    assert (humanos.com_assunto, humanos.questoes) == (1, 2)
    assert humanos.porcentagem == 50.0


def test_questao_anulada_nao_entra_na_cobertura(banco_temporario,
                                                programa_do_edital):
    """A banca desfez a pergunta: ela nao conta em lugar nenhum."""
    with sessao() as s:
        s.add(_concurso_do_alvo())
    _semear(
        _questao_no_acervo(1, "Direitos Humanos", minha=True),
        _questao_no_acervo(2, "Direitos Humanos", minha=True),
    )
    with sessao() as s:
        primeira = s.scalars(servico.select(QuestaoDeProva)).first()
        primeira.anulada = True

    humanos = next(
        c for c in servico.cobertura_de_assunto() if c.materia == "Direitos Humanos"
    )

    assert humanos.questoes == 1


def test_questao_anulada_nao_e_classificada(banco_temporario, programa_do_edital):
    """Nao se paga para classificar questao que nao existe mais."""
    with sessao() as s:
        s.add(_concurso_do_alvo())
    _semear(
        _questao_no_acervo(1, "Direitos Humanos", minha=True),
        _questao_no_acervo(2, "Direitos Humanos", minha=True),
    )
    with sessao() as s:
        primeira = s.scalars(servico.select(QuestaoDeProva)).first()
        primeira.anulada = True

    assert [q.numero for q in servico.questoes_sem_assunto(so_alvo=True)] == [2]
