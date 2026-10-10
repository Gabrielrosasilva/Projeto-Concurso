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
from radar.questoes import chave_da_questao

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
        # O nivel que o pedido exige desde a decisao 151.
        "nivel": "media", "por_que_o_nivel": "a letra do art. 41 com uma troca",
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


# --- a base pela CHAVE, e nao so pelo enunciado (F3) -----------------------

COMANDO = "De acordo com a Lei de Execucao Penal, e correto"
OUTRAS = {l: f"outra alternativa {l}" for l in "abcde"}


def _duas_com_o_mesmo_comando():
    """A FEPESE repete o comando com alternativas diferentes na mesma prova."""
    _semear(_concurso(),
            _real(1, enunciado=COMANDO, impressao="repetida"),
            _real(2, enunciado=COMANDO, impressao="repetida", alternativas=OUTRAS))


def test_a_origem_e_achada_pela_chave_quando_o_comando_se_repete(banco_temporario):
    _duas_com_o_mesmo_comando()
    questao = _gravar_uma(origem_impressao="repetida",
                          origem_chave=chave_da_questao(COMANDO, OUTRAS))

    origem = servico.geradas.origem_de(servico.geradas.buscar(questao.id))

    assert origem.numero == 2


def test_sem_a_chave_o_comando_repetido_nao_vira_chute(banco_temporario):
    """A variacao de antes do F3 nao guardou a chave: entre duas questoes
    diferentes, nao ha como saber qual foi, e o selo nao aponta nenhuma."""
    _duas_com_o_mesmo_comando()
    questao = _gravar_uma(origem_impressao="repetida")

    assert servico.geradas.origem_de(servico.geradas.buscar(questao.id)) is None


def test_sem_a_chave_a_mesma_questao_em_dois_cadernos_ainda_serve(banco_temporario):
    """Reaproveitada em outro caderno, e a mesma questao: a chave e uma so."""
    _semear(_concurso(),
            _real(1, impressao="reaproveitada"),
            _real(1, impressao="reaproveitada", prova_url="https://fepese.test/outra.pdf"))
    questao = _gravar_uma(origem_impressao="reaproveitada")

    assert servico.geradas.origem_de(servico.geradas.buscar(questao.id)) is not None


def test_as_variacoes_antigas_ganham_a_chave_so_sem_duvida(banco_temporario):
    """O passo 5 da migracao: chave onde a impressao aponta uma questao so;
    nula onde aponta questoes diferentes."""
    _semear(_real(3))
    _duas_com_o_mesmo_comando()
    sem_duvida = _gravar_uma(origem_impressao="real3", impressao="g1")
    com_duvida = _gravar_uma(origem_impressao="repetida", impressao="g2",
                             enunciado="Outra questao gerada, sobre outro comando.")

    assert servico.geradas.preencher_origem_chave() == 1

    real3 = _real(3)
    with sessao() as s:
        assert (s.get(QuestaoGerada, sem_duvida.id).origem_chave
                == chave_da_questao(real3.enunciado, real3.alternativas))
        assert s.get(QuestaoGerada, com_duvida.id).origem_chave is None


def test_a_variacao_pela_api_guarda_a_chave_da_base(banco_temporario):
    falsa = _SessaoFalsa([_resposta_com(_questao_boa())])
    base = _real(1)

    novas, _entrada, _saida = gerador.variar(base, "chave", 1, falsa)

    assert novas[0].origem_chave == chave_da_questao(base.enunciado, base.alternativas)


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
    blocos, _recusadas = servico.incidencia_por_evidencia()
    assert sum(bloco.questoes for bloco in blocos) == 1

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


# --- a tela -----------------------------------------------------------------
#
# A tela tem duas obrigacoes, e as duas sao testadas: dizer em cada questao
# que ela foi criada por IA e em que questao real se baseia, e nunca mostrar
# o meu acerto num numero so.


@pytest.fixture
def cliente(banco_temporario):
    from fastapi.testclient import TestClient
    from radar.web.app import app

    return TestClient(app)


def test_a_aba_gerar_questoes_fica_ao_lado_do_simulado(cliente):
    pagina = cliente.get("/simulado").text

    assert 'href="/geradas"' in pagina


def test_a_tela_avisa_que_isto_treina_e_nao_mede(cliente):
    """O aviso e a razao de ser da etapa, e fica no topo da tela."""
    _semear(_concurso(), _real(1))

    pagina = cliente.get("/geradas").text

    assert "treina, não mede" in pagina
    assert "nunca somado" in pagina
    # Regra 5 do novo.md, no topo da tela que so mostra questao de IA.
    assert "🟣" in pagina
    assert "Gerada por IA: não é questão oficial da FEPESE." in pagina


def test_o_botao_que_gasta_traz_o_preco_nele_mesmo(cliente):
    """Nenhum botao que gasta sem o numero do gasto escrito nele.

    O preco e o custo daquela escolha, renderizado junto do botao: escolher a
    materia recarrega a pagina antes, entao nao existe botao com preco velho.
    """
    _semear(_concurso(), _real(1))

    pagina = cliente.get("/geradas?quantas=3").text

    assert "Ver o custo disto" in pagina
    assert "Gerar e treinar — gasta US$" in pagina
    # O custo e estimativa, e o selo dele sai do plano (Etapa 7A).
    assert '<span aria-hidden="true">🟡</span> Estimativa</span>' in pagina


def test_gerar_sem_chave_volta_dizendo_o_que_falta(cliente, monkeypatch):
    monkeypatch.delenv("RADAR_ANTHROPIC_KEY", raising=False)
    _semear(_concurso(), _real(1))

    resposta = cliente.post(
        "/geradas/gerar", data={"materia": "", "quantas": "3"},
        follow_redirects=False,
    )

    assert resposta.status_code == 303
    assert "recado=sem_chave" in resposta.headers["location"]
    assert "RADAR_ANTHROPIC_KEY" in cliente.get("/geradas?recado=sem_chave").text


def test_treinar_com_as_de_casa_cai_no_simulado_de_sempre(cliente):
    """Nao ha segunda tela de responder questao."""
    _gravar_uma()

    resposta = cliente.post(
        "/geradas/treinar", data={"materia": "", "quantidade": "1"},
        follow_redirects=False,
    )

    assert resposta.status_code == 303
    assert resposta.headers["location"].startswith("/simulado/")


def test_a_questao_gerada_chega_com_selo_e_com_a_origem(cliente):
    """Selo visivel, dizendo que foi criada por IA e em que questao real ela
    se baseia - antes do enunciado, e nao depois de responder."""
    _semear(_concurso(), _real(1))
    _gravar_uma()
    rodada = servico.geradas.criar_simulado(quantidade=1)

    pagina = cliente.get(f"/simulado/{rodada.id}").text

    assert "Questão criada por IA" in pagina
    assert "Variação da questão 1" in pagina
    assert "FEPESE 2019" in pagina
    # Regra 5 do novo.md, sempre visivel: o 🟣 e a frase, antes do enunciado.
    assert "🟣" in pagina
    assert "Gerada por IA: não é questão oficial da FEPESE." in pagina
    assert pagina.index("não é questão oficial da FEPESE") < pagina.index('class="enunciado"')


def test_variacao_sem_base_identificada_nao_diz_que_foi_do_zero(cliente):
    """F3: quando o acervo nao diz qual questao foi a base, a tela nao chuta
    uma - e tambem nao diz que a questao foi escrita do zero, porque nao foi."""
    _duas_com_o_mesmo_comando()
    _gravar_uma(origem_impressao="repetida")
    rodada = servico.geradas.criar_simulado(quantidade=1)

    pagina = cliente.get(f"/simulado/{rodada.id}").text

    assert "não consegue identificar" in pagina
    assert "Escrita do zero" not in pagina
    assert "Variação da questão" not in pagina


def test_o_relatorio_da_rodada_de_ia_diz_que_nao_e_questao_oficial(cliente):
    """Regra 5 do novo.md no relatorio: a pagina diz a frase, e cada erro, o
    resultado e a resposta levam o 🟣 - a resposta da IA nunca parece o
    gabarito definitivo."""
    _gravar_uma()
    rodada = servico.geradas.criar_simulado(quantidade=1)
    _resposta, questao = servico.questao_atual(rodada.id)
    servico.responder(rodada.id, questao.id, "a")            # errou: a certa e c

    pagina = cliente.get(f"/simulado/{rodada.id}").text

    assert "Gerada por IA: não é questão oficial da FEPESE." in pagina
    assert '<span aria-hidden="true">🟣</span> Treino com IA' in pagina
    assert '<span aria-hidden="true">🟣</span> criada por IA' in pagina
    assert '<span aria-hidden="true">🟣</span> Resposta da IA c)' in pagina
    assert "Gabarito definitivo" not in pagina


def test_a_questao_real_da_rodada_nao_leva_o_aviso_de_ia(cliente):
    """O selo sai da questao: a real e 🟢, e o aviso de IA nao aparece nela."""
    _semear(_concurso(), _real(1))
    rodada = servico.criar_simulado(quantidade=1)

    pagina = cliente.get(f"/simulado/{rodada.id}").text

    assert "🟢</span> Extraída da prova" in pagina
    assert "🟣" not in pagina
    assert "não é questão oficial da FEPESE" not in pagina


def test_o_artigo_aparece_com_o_link_da_lei(cliente):
    """E o que me deixa conferir em 10 segundos."""
    _semear(_concurso(), _real(1))
    _gravar_uma()
    rodada = servico.geradas.criar_simulado(quantidade=1)

    pagina = cliente.get(f"/simulado/{rodada.id}").text

    assert "art. 41 da Lei 7.210/1984" in pagina
    assert "planalto.gov.br/ccivil_03/leis/l7210.htm" in pagina
    assert "ler a lei" in pagina


def test_sem_artigo_a_tela_diz_que_nao_sabe(cliente):
    """Vazio e melhor que inventado, e a tela precisa dizer qual dos dois e."""
    _gravar_uma(artigo=None)
    rodada = servico.geradas.criar_simulado(quantidade=1)

    pagina = cliente.get(f"/simulado/{rodada.id}").text

    assert "não soube dizer em que artigo" in pagina


def test_um_clique_marca_a_questao_como_errada_e_a_rodada_anda(cliente):
    """Ela sai do sorteio para sempre, e a rodada nao trava na questao que eu
    acabei de recusar."""
    _gravar_uma()
    rodada = servico.geradas.criar_simulado(quantidade=1)
    _resposta, questao = servico.questao_atual(rodada.id)

    resposta = cliente.post(
        f"/geradas/{questao.id}/errada",
        data={"voltar": f"/simulado/{rodada.id}"},
        follow_redirects=False,
    )

    assert resposta.status_code == 303
    assert servico.geradas.contar()["valem"] == 0
    assert servico.questao_atual(rodada.id) is None


def test_a_questao_recusada_nao_deixa_resto_no_meu_acerto(cliente):
    """Se ela nao vale como questao, nao vale como acerto nem como erro."""
    _gravar_uma()
    rodada = servico.geradas.criar_simulado(quantidade=1)
    _resposta, questao = servico.questao_atual(rodada.id)
    servico.responder(rodada.id, questao.id, "a")
    assert servico.desempenho_das_geradas() != []

    cliente.post(f"/geradas/{questao.id}/errada", data={"voltar": "/geradas"})

    assert servico.desempenho_das_geradas() == []


def test_a_tela_do_simulado_mostra_os_dois_numeros_separados(cliente):
    """Nunca um numero so."""
    _semear(_concurso(), _real(1))
    _gravar_uma()

    real = servico.criar_simulado(quantidade=1, materia="Lei de Execução Penal")
    _resposta, questao = servico.questao_atual(real.id)
    servico.responder(real.id, questao.id, "a")

    gerada = servico.geradas.criar_simulado(quantidade=1)
    _resposta, questao = servico.questao_atual(gerada.id)
    servico.responder(gerada.id, questao.id, "a")

    pagina = cliente.get("/simulado").text

    assert "Como você vai até agora" in pagina
    assert "Nas questões geradas" in pagina
    # Cada numero com o selo da sua origem, lido do dado (Etapa 7A): o das
    # reais e conta do sistema; o das geradas, da IA - com a frase da regra 5.
    assert '<span aria-hidden="true">🟡</span> Análise automática</span> Em questão real' in pagina
    assert '<span aria-hidden="true">🟣</span> Gerado por IA</span> Nas questões geradas' in pagina
    assert "Gerada por IA: não é questão oficial da FEPESE." in pagina
    # E a rodada de IA, na lista, leva o 🟣.
    assert '<span aria-hidden="true">🟣</span> IA</span>' in pagina


def test_o_resultado_da_rodada_gerada_nao_vem_vazio(cliente):
    """O `desempenho` comum nao enxerga a tabela das geradas: sem o desvio, o
    fim da rodada mostraria uma tabela em branco."""
    _gravar_uma()
    rodada = servico.geradas.criar_simulado(quantidade=1)
    _resposta, questao = servico.questao_atual(rodada.id)
    servico.responder(rodada.id, questao.id, "c")

    pagina = cliente.get(f"/simulado/{rodada.id}").text

    assert "Lei de Execução Penal" in pagina
    assert "criada por IA" in pagina


# --- o modo simulado e o peso do edital (item 4 da secao F, 03/10/2026) ---------

def test_o_simulado_sem_materia_divide_pelo_peso_do_edital(banco_temporario, monkeypatch):
    """A §8 pede que o modo simulado respeite "o edital, o peso das materias".
    Antes ele sorteava as bases sem olhar o peso; agora as questoes se dividem
    pelo quadro do edital, como o compilado e a composicao (decisao 67)."""
    from radar.servico import compilado

    _semear(_concurso(),
            *[_real(n, impressao=f"lep{n}") for n in range(1, 5)],
            *[_real(n, materia="Língua Portuguesa", impressao=f"port{n}",
                    enunciado=f"Questao de portugues {n}?") for n in range(5, 9)])
    monkeypatch.setattr(compilado, "_pesos", lambda escolhidas: (
        {"Língua Portuguesa": 15, "Lei de Execução Penal": 10}, None, None))

    plano = servico.geradas.preparar(None, 10, modo="simulado", semente=1)

    assert plano["distribuicao"] == {"Língua Portuguesa": 6, "Lei de Execução Penal": 4}
    por_materia: dict[str, int] = {}
    for pedido in plano["pedidos"]:
        materia = pedido["questao"].materia
        por_materia[materia] = por_materia.get(materia, 0) + pedido["quantas"]
    assert por_materia == {"Língua Portuguesa": 6, "Lei de Execução Penal": 4}


def test_o_simulado_com_materia_escolhida_nao_se_divide(banco_temporario, monkeypatch):
    """Com a materia escolhida nao ha o que dividir: o caminho de sempre."""
    from radar.servico import compilado

    _semear(_concurso(), *[_real(n, impressao=f"lep{n}") for n in range(1, 5)])
    monkeypatch.setattr(compilado, "_pesos", lambda escolhidas: (
        {"Lei de Execução Penal": 10}, None, None))

    plano = servico.geradas.preparar("Lei de Execução Penal", 6, modo="simulado")

    assert plano["distribuicao"] is None
    assert plano["quantas"] == 6
