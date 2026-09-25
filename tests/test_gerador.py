"""Questao escrita pela IA: o que e enviado, o que e aceito, e o que ela nao
pode contaminar.

O teste mais importante deste arquivo nao e sobre a IA: e o
`test_questao_gerada_nao_entra_em_nada_que_meca`. Questao gerada serve para
TREINAR, nunca para MEDIR o que a banca cobra, e se um dia alguem apagar essa
separacao e aqui que vai estourar.

Nenhum teste fala com a API: a resposta e de mentira.
"""
import json

import pytest

from radar import acervo, gerador, servico
from radar.db import sessao
from radar.models import Concurso, QuestaoDeProva, QuestaoGerada

CONCURSO = "https://fepese.test/concurso/sap-2019"
DO_ALVO = "Agente Penitenciário"


def _concurso() -> Concurso:
    return Concurso(
        url=CONCURSO,
        fonte="fepese",
        titulo="2019 - Secretaria de Estado da Administracao Prisional",
        uf="SC",
        tipo="concurso",
        situacao="encerrado",
        relevancia="estadual",
        alvo="principal",
    )


def _real(numero: int, **mudancas) -> QuestaoDeProva:
    base = dict(
        prova_url="https://fepese.test/sap2019.pdf",
        concurso_url=CONCURSO,
        banca="FEPESE",
        ano=2019,
        cargo=DO_ALVO,
        numero=numero,
        materia="Lei de Execução Penal",
        enunciado=f"De acordo com a Lei de Execucao Penal, questao {numero}?",
        alternativas={l: f"alternativa {l}" for l in "abcde"},
        resposta="a",
        impressao=f"real{numero}",
        assunto="Lei de Execução Penal (Lei nº 7.210 de 11 de julho de 1984)",
    )
    base.update(mudancas)
    return QuestaoDeProva(**base)


def _semear(*linhas):
    with sessao() as s:
        for linha in linhas:
            s.add(linha)


def _questao_boa(enunciado: str = "Sobre a execucao penal, assinale a correta.") -> dict:
    return {
        "enunciado": enunciado,
        "alternativas": {l: f"texto {l}" for l in "abcde"},
        "resposta": "c",
        "artigo": "art. 41, XV, da Lei 7.210/1984",
    }


class _Resposta:
    def __init__(self, texto, entrada=1000, saida=500):
        self._texto = texto
        self._uso = {"input_tokens": entrada, "output_tokens": saida}

    def raise_for_status(self):
        return None

    def json(self):
        return {
            # O bloco de raciocinio vem junto na resposta real, e nao pode
            # entrar no texto lido.
            "content": [
                {"type": "thinking", "thinking": "pensando..."},
                {"type": "text", "text": self._texto},
            ],
            "usage": self._uso,
        }


class _SessaoFalsa:
    """Responde o que o teste mandar e anota o que foi enviado."""

    def __init__(self, respostas, entrada=1000, saida=500):
        self.respostas = list(respostas)
        self.pedidos = []
        self.entrada = entrada
        self.saida = saida

    def post(self, url, headers=None, json=None, timeout=None):
        self.pedidos.append(json or {})
        texto = self.respostas.pop(0) if self.respostas else "{}"
        return _Resposta(texto, self.entrada, self.saida)


def _resposta_com(*questoes) -> str:
    return json.dumps({"questoes": list(questoes)})


# --- o que e enviado --------------------------------------------------------

def test_o_pedido_de_variacao_leva_o_gabarito_oficial():
    """E o gabarito que ancora a variacao: sem ele a IA teria que adivinhar
    qual regra a questao original estava cobrando."""
    pedido = gerador._montar_pedido_variacao(_real(1))

    assert "GABARITO OFICIAL: a" in pedido


def test_o_pedido_de_variacao_leva_as_alternativas():
    """Diferente do `radar assuntos`: la o enunciado bastava, aqui a
    alternativa certa e que carrega a regra juridica."""
    pedido = gerador._montar_pedido_variacao(_real(1))

    for letra in "abcde":
        assert f"{letra}) alternativa {letra}" in pedido


def test_o_exemplo_do_modo_do_zero_vai_sem_gabarito():
    """No modo do zero a questao real e exemplo de ESTILO, e nao de conteudo -
    mandar o gabarito convidaria a IA a copiar a resposta."""
    pedido = gerador._montar_pedido_do_zero(
        "Direitos Humanos", "Regras de Mandela", [_real(1)], 3
    )

    assert "GABARITO OFICIAL" not in pedido


def test_o_modelo_e_o_intermediario_e_nao_o_mais_barato():
    """Questao de Direito com modelo fraco erra mais, e aqui o erro e um
    gabarito errado que eu estudaria como certo."""
    assert gerador.MODELO == "claude-sonnet-5"


def test_a_chamada_manda_a_chave_e_pede_raciocinio(banco_temporario):
    falsa = _SessaoFalsa([_resposta_com(_questao_boa())])

    gerador.variar(_real(1), "chave-de-teste", quantas=1, sessao=falsa)

    enviado = falsa.pedidos[0]
    assert enviado["model"] == "claude-sonnet-5"
    assert enviado["thinking"] == {"type": "adaptive"}
    # Sem folga de tokens a resposta sai cortada, e o pedido inteiro se perde
    # tendo sido cobrado.
    assert enviado["max_tokens"] > 1000


# --- o que e aceito de volta ------------------------------------------------

def test_questao_com_menos_de_cinco_alternativas_e_descartada():
    """Alternativa faltando quer dizer que o modelo se perdeu no meio, e o
    resto dela nao merece confianca."""
    torta = _questao_boa()
    del torta["alternativas"]["e"]

    assert gerador._conferir(torta) is None


def test_alternativa_vazia_e_descartada():
    vazia = _questao_boa()
    vazia["alternativas"]["d"] = "   "

    assert gerador._conferir(vazia) is None


def test_resposta_que_nao_aponta_para_alternativa_e_descartada():
    perdida = _questao_boa()
    perdida["resposta"] = "z"

    assert gerador._conferir(perdida) is None


def test_artigo_vazio_vira_nulo_e_nao_texto_vazio():
    """A IA foi instruida a responder "" quando nao souber o artigo, e vazio
    tem que virar "nao sei" - nao um artigo em branco na tela."""
    sem_artigo = _questao_boa()
    sem_artigo["artigo"] = ""

    assert gerador._conferir(sem_artigo)["artigo"] is None


def test_o_json_e_recortado_do_meio_da_conversa():
    """O modelo as vezes cerca a resposta de texto, e isso nao pode perder o
    lote inteiro."""
    texto = "Claro! Aqui estao:\n```json\n" + _resposta_com(_questao_boa()) + "\n```"

    assert len(gerador._ler_resposta(texto)) == 1


def test_o_bloco_de_raciocinio_nao_entra_no_texto_lido(banco_temporario):
    """O raciocinio volta no mesmo `content` da resposta; se ele entrasse no
    texto, o recorte do JSON pegaria a chave errada."""
    falsa = _SessaoFalsa([_resposta_com(_questao_boa())])

    novas, _entrada, _saida = gerador.variar(_real(1), "chave", 1, falsa)

    assert len(novas) == 1
    assert "pensando" not in novas[0].enunciado


# --- o teto de gasto --------------------------------------------------------

def test_o_teto_e_conferido_antes_de_cada_chamada():
    """Mesma regra do `radar assuntos`: o teto vale contra o gasto REAL ja
    acumulado, e nao contra a estimativa."""
    falsa = _SessaoFalsa(
        [_resposta_com(_questao_boa(f"Questao numero {n} sobre execucao penal."))
         for n in range(5)],
        entrada=1_000_000, saida=1_000_000,   # uma chamada ja estoura o teto
    )
    pedidos = [{"modo": "variacao", "questao": _real(n), "quantas": 1}
               for n in range(1, 4)]

    resultado = gerador.gerar(pedidos, "chave", teto_em_dolar=0.50, sessao=falsa)

    assert resultado.uso.chamadas == 1
    assert resultado.parou_no_teto


def test_lote_que_falha_nao_derruba_os_outros():
    class _Explode(_SessaoFalsa):
        def post(self, *argumentos, **nomeados):
            if not self.pedidos:
                self.pedidos.append({})
                raise OSError("a rede caiu")
            return super().post(*argumentos, **nomeados)

    falsa = _Explode([_resposta_com(_questao_boa())])
    pedidos = [{"modo": "variacao", "questao": _real(n), "quantas": 1}
               for n in (1, 2)]

    resultado = gerador.gerar(pedidos, "chave", sessao=falsa)

    assert resultado.falhas == 1
    assert len(resultado.questoes) == 1


def test_questao_repetida_nao_entra_duas_vezes():
    """Duas variacoes iguais, ou uma igual ao que ja existe, sao descartadas:
    pagar de novo pela mesma pergunta e o desperdicio a evitar."""
    mesma = _questao_boa("Sobre a remicao de pena, assinale a alternativa correta.")
    falsa = _SessaoFalsa([_resposta_com(mesma, mesma)])

    resultado = gerador.gerar(
        [{"modo": "variacao", "questao": _real(1), "quantas": 2}], "chave",
        sessao=falsa,
    )

    assert len(resultado.questoes) == 1
    assert resultado.descartadas == 1


# --- montar o plano, sem gastar ---------------------------------------------

def test_cinco_questoes_viram_duas_chamadas(banco_temporario):
    """Tres variacoes por questao real: 5 pedidas sao 3 + 2."""
    _semear(_concurso(), _real(1), _real(2), _real(3))

    plano = servico.geradas.preparar(quantas=5)

    assert [p["quantas"] for p in plano["pedidos"]] == [3, 2]
    assert plano["quantas"] == 5


def test_a_base_e_so_a_prova_do_meu_cargo(banco_temporario):
    """Variar uma questao de Merendeira daria uma questao de Merendeira."""
    _semear(
        _concurso(),
        _real(1),
        _real(2, cargo="Merendeira", prova_url="https://fepese.test/outra.pdf",
              impressao="outra2"),
    )

    plano = servico.geradas.preparar(quantas=9)

    assert plano["base_disponivel"] == 1


def test_questao_anulada_nao_serve_de_base(banco_temporario):
    """A banca disse que ela nao tem resposta certa: variar seria multiplicar
    o problema."""
    _semear(_concurso(), _real(1, anulada=True), _real(2))

    plano = servico.geradas.preparar(quantas=3)

    assert plano["base_disponivel"] == 1
    assert plano["pedidos"][0]["questao"].numero == 2


def test_a_escolha_prefere_a_questao_que_nunca_foi_variada(banco_temporario):
    """Variar de novo a mesma questao daria uma quarta versao da mesma
    pergunta, com outra ainda sem treino nenhum."""
    _semear(_concurso(), _real(1), _real(2))
    with sessao() as s:
        s.add(QuestaoGerada(
            modo="variacao", origem_impressao="real1", materia="Lei de Execução Penal",
            enunciado="ja gerada", alternativas={l: "t" for l in "abcde"},
            resposta="a", impressao="gerada1",
        ))

    plano = servico.geradas.preparar(quantas=3)

    assert plano["pedidos"][0]["questao"].impressao == "real2"


def test_sem_chave_nao_gera_e_diz_por_que(banco_temporario, monkeypatch):
    monkeypatch.delenv("RADAR_ANTHROPIC_KEY", raising=False)
    _semear(_concurso(), _real(1))

    assert servico.geradas.gerar(quantas=3)["erro"] == "sem chave"


# --- guardar, rejeitar, sortear ---------------------------------------------

def _gravar_uma(**mudancas) -> QuestaoGerada:
    base = dict(
        modo="variacao",
        origem_impressao="real1",
        modelo=gerador.MODELO,
        materia="Lei de Execução Penal",
        assunto=None,
        artigo="art. 41 da Lei 7.210/1984",
        enunciado="Enunciado gerado sobre execucao penal, com tamanho bastante.",
        alternativas={l: f"texto {l}" for l in "abcde"},
        resposta="c",
        impressao="gerada1",
        rejeitada=False,
    )
    base.update(mudancas)
    questao = QuestaoGerada(**base)
    with sessao() as s:
        s.add(questao)
    return questao


def test_o_arquivo_versionado_vai_e_volta(banco_temporario, tmp_path):
    """Perder o arquivo e pagar de novo pela mesma questao."""
    _gravar_uma()
    destino = tmp_path / "questoes_geradas.json"

    assert acervo.exportar_geradas(destino) == 1

    with sessao() as s:
        for q in s.query(QuestaoGerada).all():
            s.delete(q)

    assert acervo.importar_geradas(destino) == 1
    assert servico.geradas.contar()["total"] == 1


def test_a_rejeicao_volta_no_arquivo(banco_temporario, tmp_path):
    """O `rejeitada` e meu, e nao da IA: um banco refeito nao pode me devolver
    ao sorteio tudo que eu ja disse que estava errado."""
    questao = _gravar_uma()
    servico.geradas.rejeitar(questao.id)
    destino = tmp_path / "questoes_geradas.json"
    acervo.exportar_geradas(destino)

    with sessao() as s:
        for q in s.query(QuestaoGerada).all():
            s.delete(q)
    acervo.importar_geradas(destino)

    assert servico.geradas.contar()["rejeitadas"] == 1


def test_questao_rejeitada_sai_do_sorteio_para_sempre(banco_temporario):
    questao = _gravar_uma()
    _gravar_uma(impressao="gerada2", enunciado="Outro enunciado gerado, bem maior.")

    servico.geradas.rejeitar(questao.id)
    rodada = servico.geradas.criar_simulado(quantidade=10)

    assert rodada is not None
    assert servico.resumo_do_simulado(rodada.id)["total"] == 1


def test_a_rodada_gerada_usa_a_mesma_tela_do_simulado(banco_temporario):
    """Nao ha segunda tela de responder questao: a rodada gerada anda pelo
    mesmo `questao_atual` / `responder` das reais."""
    _gravar_uma()
    rodada = servico.geradas.criar_simulado(quantidade=1)

    atual = servico.questao_atual(rodada.id)
    assert atual is not None
    _resposta, questao = atual
    assert isinstance(questao, QuestaoGerada)

    assert servico.responder(rodada.id, questao.id, "c") is True


def test_a_origem_da_variacao_e_recuperavel(banco_temporario):
    """O selo da tela precisa dizer em que questao real ela se baseia."""
    _semear(_concurso(), _real(1))
    questao = _gravar_uma(origem_impressao="real1")

    origem = servico.geradas.origem_de(servico.geradas.buscar(questao.id))

    assert origem is not None
    assert origem.numero == 1


# --- a regra que sustenta a etapa -------------------------------------------

def test_questao_gerada_nao_entra_em_nada_que_meca(banco_temporario):
    """O teste que importa. Questao gerada treina, nao mede.

    Se um dia alguem juntar as duas tabelas, ou esquecer um filtro, e aqui
    que vai estourar - antes de eu passar a estudar pelo que a IA inventou em
    vez do que a FEPESE cobra.
    """
    _semear(_concurso(), _real(1))
    _gravar_uma()

    # o acervo continua com uma questao so
    assert servico.contar_questoes() == 1

    # a incidencia por materia nao ve a gerada
    incidencia = servico.incidencia_por_materia()
    assert sum(quantas for _materia, quantas in incidencia) == 1

    # e o simulado comum nao sorteia gerada
    with sessao() as s:
        assert len(servico._sortear_questoes(50)) <= 1


def test_o_acerto_sai_em_dois_numeros_separados(banco_temporario):
    """Nunca um numero so: acertar uma variacao que a IA escreveu nao e a
    mesma coisa que acertar o que a banca cobrou."""
    _semear(_concurso(), _real(1))
    _gravar_uma()

    real = servico.criar_simulado(quantidade=1, materia="Lei de Execução Penal")
    _resposta, questao = servico.questao_atual(real.id)
    servico.responder(real.id, questao.id, "a")           # acertou

    gerada = servico.geradas.criar_simulado(quantidade=1)
    _resposta, questao = servico.questao_atual(gerada.id)
    servico.responder(gerada.id, questao.id, "a")         # errou (a certa e c)

    nas_reais = servico.desempenho()
    nas_geradas = servico.desempenho_das_geradas()

    assert [(d.respondidas, d.acertos) for d in nas_reais] == [(1, 1)]
    assert [(d.respondidas, d.acertos) for d in nas_geradas] == [(1, 0)]


def test_responder_uma_gerada_nao_tira_a_real_de_mesmo_id_do_sorteio(
    banco_temporario,
):
    """As duas tabelas numeram a partir do 1. Sem a coluna `gerada`, responder
    a questao gerada 1 esconderia a questao real 1 - um erro que so apareceria
    como pergunta que nunca mais aparece."""
    _semear(_concurso(), _real(1))
    _gravar_uma()

    rodada = servico.geradas.criar_simulado(quantidade=1)
    _resposta, questao = servico.questao_atual(rodada.id)
    servico.responder(rodada.id, questao.id, "c")

    with sessao() as s:
        assert servico._impressoes_ja_respondidas(s) == set()


def test_a_revisao_diz_que_a_questao_e_gerada(banco_temporario):
    """Rever uma questao gerada achando que e da banca e o erro que esta etapa
    inteira evita."""
    _gravar_uma()
    rodada = servico.geradas.criar_simulado(quantidade=1)
    _resposta, questao = servico.questao_atual(rodada.id)
    servico.responder(rodada.id, questao.id, "a")

    item = servico.revisao(rodada.id)[0]

    assert item.gerada is True
    assert item.artigo == "art. 41 da Lei 7.210/1984"
