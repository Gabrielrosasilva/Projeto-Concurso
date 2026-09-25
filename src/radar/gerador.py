"""Escreve questoes novas com a API da Claude, para eu TREINAR.

Esta e a segunda parte do radar que custa dinheiro, e a regra que vale para
ela inteira esta escrita aqui porque e dela que tudo depende:

    **questao gerada serve para treinar, nunca para medir o que a banca
    cobra.** Ela nao entra na incidencia, no peso das materias, na aba Macetes
    nem nas questoes esperadas do "Onde estudar primeiro".

Quem garante isso nao e este arquivo: e a tabela `questoes_geradas`, separada
da `questoes`. Filtro em consulta depende de alguem lembrar; tabela separada
nao depende de ninguem.

DOIS MODOS, E O PADRAO E O SEGURO

  * **variacao** (padrao) parte de uma questao REAL da FEPESE, com o gabarito
    definitivo ja conferido, e pede que mude o cenario e os numeros mantendo a
    regra juridica. O estilo e o da banca de verdade, e a resposta esta
    ancorada numa questao cujo gabarito a propria banca publicou;
  * **do_zero** e a excecao, e so para assunto que nao tem NENHUMA questao
    real no acervo. Sem questao embaixo, o unico apoio sao questoes reais da
    mesma materia servindo de exemplo de estilo, mais o assunto do edital.

POR QUE O TEXTO DA LEI NAO VAI NO PEDIDO

O plano era baixar o artigo do Planalto e mandar junto, para reduzir o risco
de gabarito errado. Conferido em 24/09/2026, e nao da:

  * `planalto.gov.br/robots.txt` responde **404**. Pela convencao, isso quer
    dizer que nada esta proibido - o robots nao e o impedimento;
  * o impedimento e outro: o servidor **recusa a conexao** para qualquer
    User-Agent que nao seja de navegador. Com o UA honesto do projeto
    ("radar-concursos/0.1 ..."), e tambem com "curl/8.4.0", a conexao e
    derrubada; com um UA de Chrome, responde 200. Testado alternando os dois,
    varias vezes seguidas.

Baixar a lei exigiria o radar se disfarcar de navegador, e o CLAUDE.md manda
identificar-se no User-Agent. Entao nao se baixa. O que sobra no lugar e mais
honesto do que parece: no modo variacao a ancora e o gabarito oficial da
questao de origem, e em todo caso a IA diz em QUE ARTIGO se apoiou - a tela
mostra o artigo com o link de config/leis.yml, e eu confiro em 10 segundos.
Artigo que a IA nao souber vem vazio, e vazio e melhor que inventado.

Nao entra biblioteca nova: a API e REST e `requests` ja e dependencia desde a
primeira fase, que e a mesma decisao ja tomada em `radar.assuntos`. Ter dois
jeitos de chamar a mesma API num projeto deste tamanho seria pior.
"""
import json
import logging
import re
from dataclasses import dataclass, field

import requests

from radar import config
from radar.questoes import impressao_de

log = logging.getLogger(__name__)

API = "https://api.anthropic.com/v1/messages"
VERSAO_DA_API = "2023-06-01"

# O intermediario, e nao o mais barato. Questao de Direito com modelo fraco
# erra mais, e aqui o erro nao e um rotulo torto como no `radar assuntos` - e
# um gabarito errado que eu estudaria como se fosse certo.
MODELO = "claude-sonnet-5"

# Precos por milhao de tokens, em dolar. Confira em anthropic.com/pricing
# antes de confiar no numero.
PRECO_ENTRADA = 2.00
PRECO_SAIDA = 10.00

# Teto de gasto padrao, em dolar: uns R$ 5, a 5,50. E por EXECUCAO, e nao por
# mes - o radar nao conta o mes. Cinco reais e o tamanho de um erro aceitavel
# se eu digitar um numero grande sem pensar.
TETO_PADRAO = 0.90

# Quantas variacoes por questao real. Tres muda o cenario o bastante para eu
# nao reconhecer a pergunta de cor, e cabe numa resposta so.
VARIACOES_POR_QUESTAO = 3

# Quantas questoes reais viram exemplo de estilo no modo do_zero.
EXEMPLOS_DO_ZERO = 8

# As letras que a FEPESE usa. Resposta com outro numero de alternativas nao e
# do feitio da banca, e e descartada.
LETRAS = ("a", "b", "c", "d", "e")

# Quanto de cada questao vai no pedido. O exemplo serve para mostrar o ESTILO
# da banca; mandar o caderno inteiro so encarece.
LIMITE_DO_EXEMPLO = 600


INSTRUCAO_VARIACAO = """Voce recebe UMA questao real de concurso publico brasileiro, da banca FEPESE, com o gabarito oficial ja conferido.

Escreva variacoes dela para treino.

Regras:
- MANTENHA a regra juridica testada pela questao original. O que muda e o
  cenario, os nomes e os numeros - nao o que esta sendo cobrado;
- mesmo estilo da original: mesmo tipo de comando, cinco alternativas de "a" a
  "e", uma unica correta;
- nao copie o enunciado original: se a variacao so troca uma palavra, ela nao
  serve;
- diga o ARTIGO da lei em que a variacao se apoia, assim: "art. 41, XV, da Lei
  7.210/1984". Se voce nao tiver certeza do artigo, responda "" no campo - um
  artigo inventado e pior que nenhum;
- nao explique, nao comente, nao repita a questao original.

Responda SOMENTE um JSON, no formato:
{"questoes": [{"enunciado": "...", "alternativas": {"a": "...", "b": "...", "c": "...", "d": "...", "e": "..."}, "resposta": "c", "artigo": "art. 41, XV, da Lei 7.210/1984"}]}"""


INSTRUCAO_DO_ZERO = """Voce recebe exemplos de questoes reais de concurso publico brasileiro, da banca FEPESE, e um assunto do conteudo programatico de um edital.

Escreva questoes INEDITAS sobre esse assunto, no estilo dos exemplos.

Regras:
- os exemplos estao ali para mostrar o ESTILO da banca - o tipo de comando, o
  tamanho do enunciado, o jeito das alternativas. Nao copie o conteudo deles;
- cinco alternativas de "a" a "e", uma unica correta;
- cobre o que a lei diz, e nao opiniao: a questao precisa ter uma resposta
  certa que se confira no texto legal;
- diga o ARTIGO da lei em que a questao se apoia, assim: "art. 41, XV, da Lei
  7.210/1984". Se voce nao tiver certeza do artigo, responda "" no campo - um
  artigo inventado e pior que nenhum;
- nao explique, nao comente.

Responda SOMENTE um JSON, no formato:
{"questoes": [{"enunciado": "...", "alternativas": {"a": "...", "b": "...", "c": "...", "d": "...", "e": "..."}, "resposta": "c", "artigo": "art. 41, XV, da Lei 7.210/1984"}]}"""


@dataclass
class Uso:
    """Quanto foi gasto de verdade, pelo que a propria API informou."""

    entrada: int = 0
    saida: int = 0
    chamadas: int = 0

    @property
    def custo(self) -> float:
        return (self.entrada / 1e6 * PRECO_ENTRADA
                + self.saida / 1e6 * PRECO_SAIDA)

    def somar(self, entrada: int, saida: int) -> None:
        self.entrada += entrada
        self.saida += saida
        self.chamadas += 1


@dataclass
class QuestaoNova:
    """Uma questao escrita pela IA, ja conferida na FORMA (nao no conteudo)."""

    enunciado: str
    alternativas: dict[str, str]
    resposta: str
    artigo: str | None = None
    modo: str = "variacao"
    materia: str | None = None
    assunto: str | None = None
    origem_impressao: str | None = None
    modelo: str = MODELO

    @property
    def impressao(self) -> str:
        return impressao_de(self.enunciado)


@dataclass
class Resultado:
    questoes: list[QuestaoNova] = field(default_factory=list)
    uso: Uso = field(default_factory=Uso)
    parou_no_teto: bool = False
    falhas: int = 0
    descartadas: int = 0


def _encurtar(texto: str, limite: int = LIMITE_DO_EXEMPLO) -> str:
    return " ".join((texto or "")[:limite].split())


def _questao_por_extenso(questao, com_gabarito: bool = True) -> str:
    """A questao real do jeito que ela vai no pedido.

    As alternativas vao junto, ao contrario do `radar assuntos`: la bastava o
    enunciado para dizer o assunto, e aqui a IA precisa ver a alternativa
    certa - e ela que carrega a regra juridica que a variacao tem que manter.
    """
    linhas = [_encurtar(questao.enunciado)]
    for letra, texto in (questao.alternativas or {}).items():
        linhas.append(f"{letra}) {_encurtar(texto, 300)}")
    if com_gabarito and questao.resposta:
        linhas.append(f"GABARITO OFICIAL: {questao.resposta}")
    return "\n".join(linhas)


def _montar_pedido_variacao(questao, quantas: int = VARIACOES_POR_QUESTAO) -> str:
    cabecalho = f"MATERIA: {questao.materia or 'nao informada'}"
    if getattr(questao, "assunto", None):
        cabecalho += f"\nASSUNTO: {questao.assunto}"
    return (
        f"{cabecalho}\n\nQUESTAO ORIGINAL\n\n"
        f"{_questao_por_extenso(questao)}\n\n"
        f"Escreva {quantas} variacoes."
    )


def _montar_pedido_do_zero(
    materia: str, assunto: str | None, exemplos: list, quantas: int
) -> str:
    blocos = [
        f"EXEMPLO {numero}\n{_questao_por_extenso(exemplo, com_gabarito=False)}"
        for numero, exemplo in enumerate(exemplos, start=1)
    ]
    alvo = f"MATERIA: {materia}"
    if assunto:
        alvo += f"\nASSUNTO: {assunto}"
    return (
        "EXEMPLOS DE ESTILO DA BANCA\n\n"
        + "\n\n".join(blocos)
        + f"\n\n{alvo}\n\nEscreva {quantas} questoes ineditas sobre esse assunto."
    )


def _max_tokens(quantas: int) -> int:
    """Teto de tokens da resposta, com folga para o raciocinio.

    O modelo pensa antes de responder, e o que ele pensa conta como saida.
    Apertar isto nao economiza: corta a resposta no meio e o pedido inteiro se
    perde, tendo sido cobrado do mesmo jeito.
    """
    return 2000 + 1400 * max(1, quantas)


def estimar(
    quantos_pedidos: int, caracteres: int, quantas_por_pedido: int
) -> tuple[int, int, float]:
    """(tokens de entrada, tokens de saida, custo em dolar) antes de gastar.

    A conta de entrada usa a regra pratica de ~3,5 caracteres por token em
    portugues, a mesma do `radar assuntos`.

    A de SAIDA e mais grosseira, e vale dizer por que: o modelo pensa antes de
    escrever, o raciocinio e cobrado como saida, e quanto ele vai pensar
    depende da questao. Os 900 tokens por questao sao uma media com folga.
    Por isso a estimativa serve para decidir se vale rodar, e quem impede o
    susto e o TETO, conferido antes de cada chamada com o gasto real que a
    API informou.
    """
    if quantos_pedidos <= 0:
        return 0, 0, 0.0

    entrada = int(caracteres / 3.5)
    saida = quantos_pedidos * quantas_por_pedido * 900
    custo = entrada / 1e6 * PRECO_ENTRADA + saida / 1e6 * PRECO_SAIDA
    return entrada, saida, custo


def _ler_resposta(texto: str) -> list[dict]:
    """O JSON que o modelo respondeu, tolerando o que ele costuma acrescentar.

    Mesma tolerancia do `radar assuntos`: as vezes vem cercado de crase tripla,
    ou com uma frase antes, entao o JSON e recortado do meio do texto.
    """
    achado = re.search(r"\{.*\}", texto or "", re.DOTALL)
    if not achado:
        return []

    try:
        cru = json.loads(achado.group(0))
    except json.JSONDecodeError:
        return []

    itens = cru.get("questoes") if isinstance(cru, dict) else cru
    return [item for item in (itens or []) if isinstance(item, dict)]


def _conferir(item: dict) -> dict | None:
    """A questao com a FORMA certa, ou None.

    Confere forma, e so forma: cinco alternativas de "a" a "e", nenhuma vazia,
    e uma resposta que aponta para uma delas. Se o CONTEUDO esta certo e outra
    pergunta, e quem responde e o botao "essa questao esta errada" na tela -
    nao ha como um programa conferir Direito.

    Questao torta e descartada em vez de consertada: uma alternativa faltando
    quer dizer que o modelo se perdeu no meio, e o resto dela nao merece
    confianca.
    """
    enunciado = " ".join(str(item.get("enunciado") or "").split())
    if len(enunciado) < 20:
        return None

    cruas = item.get("alternativas")
    if not isinstance(cruas, dict):
        return None

    alternativas = {}
    for letra in LETRAS:
        texto = " ".join(str(cruas.get(letra) or "").split())
        if not texto:
            return None
        alternativas[letra] = texto

    resposta = str(item.get("resposta") or "").strip().lower()[:1]
    if resposta not in alternativas:
        return None

    artigo = " ".join(str(item.get("artigo") or "").split())[:200] or None
    return {
        "enunciado": enunciado,
        "alternativas": alternativas,
        "resposta": resposta,
        "artigo": artigo,
    }


def _chamar(
    instrucao: str, pedido: str, chave: str, quantas: int, sessao=None
) -> tuple[list[dict], int, int]:
    """Manda um pedido e devolve (questoes cruas, entrada, saida)."""
    sessao = sessao or requests.Session()
    resposta = sessao.post(
        API,
        headers={
            "x-api-key": chave,
            "anthropic-version": VERSAO_DA_API,
            "content-type": "application/json",
        },
        json={
            "model": MODELO,
            "max_tokens": _max_tokens(quantas),
            # Pensar antes de responder e o que este modelo tem de melhor para
            # questao de Direito, e sai barato perto de um gabarito errado.
            "thinking": {"type": "adaptive"},
            # Esforco medio: o alto pensa mais do que uma questao de concurso
            # precisa, e o raciocinio e cobrado como saida.
            "output_config": {"effort": "medium"},
            "system": instrucao,
            "messages": [{"role": "user", "content": pedido}],
        },
        timeout=config.TIMEOUT_REQUISICAO * 10,
    )
    resposta.raise_for_status()
    corpo = resposta.json()

    # So os blocos de texto: os de raciocinio vem no mesmo `content`, com o
    # texto em outro campo, e este `get` os ignora de graca.
    texto = "".join(
        parte.get("text", "") for parte in corpo.get("content") or []
    )
    uso = corpo.get("usage") or {}
    return (
        _ler_resposta(texto),
        uso.get("input_tokens", 0),
        uso.get("output_tokens", 0),
    )


def variar(
    questao,
    chave: str,
    quantas: int = VARIACOES_POR_QUESTAO,
    sessao=None,
) -> tuple[list[QuestaoNova], int, int]:
    """Variacoes de UMA questao real. Devolve (questoes, entrada, saida)."""
    cruas, entrada, saida = _chamar(
        INSTRUCAO_VARIACAO,
        _montar_pedido_variacao(questao, quantas),
        chave,
        quantas,
        sessao,
    )

    novas = []
    for item in cruas[:quantas]:
        conferida = _conferir(item)
        if conferida is None:
            continue
        novas.append(QuestaoNova(
            modo="variacao",
            materia=questao.materia,
            assunto=getattr(questao, "assunto", None),
            origem_impressao=questao.impressao,
            **conferida,
        ))
    return novas, entrada, saida


def do_zero(
    materia: str,
    assunto: str | None,
    exemplos: list,
    chave: str,
    quantas: int = VARIACOES_POR_QUESTAO,
    sessao=None,
) -> tuple[list[QuestaoNova], int, int]:
    """Questoes ineditas de um assunto sem questao real no acervo."""
    cruas, entrada, saida = _chamar(
        INSTRUCAO_DO_ZERO,
        _montar_pedido_do_zero(materia, assunto, exemplos, quantas),
        chave,
        quantas,
        sessao,
    )

    novas = []
    for item in cruas[:quantas]:
        conferida = _conferir(item)
        if conferida is None:
            continue
        novas.append(QuestaoNova(
            modo="do_zero",
            materia=materia,
            assunto=assunto,
            origem_impressao=None,
            **conferida,
        ))
    return novas, entrada, saida


def gerar(
    pedidos: list[dict],
    chave: str,
    teto_em_dolar: float = TETO_PADRAO,
    sessao=None,
    ja_existentes: set[str] | None = None,
) -> Resultado:
    """Roda a lista de pedidos, parando ao chegar no teto de gasto.

    Cada pedido e um dicionario: `{"modo": "variacao", "questao": <real>}` ou
    `{"modo": "do_zero", "materia": ..., "assunto": ..., "exemplos": [...]}`.

    O teto e conferido ANTES de cada chamada, com o custo real acumulado que a
    API informou - e nao com a estimativa. Assim a conta nunca passa do que
    foi autorizado por mais de uma chamada.

    Questao repetida e descartada aqui, e nao no banco: `ja_existentes` traz a
    impressao do que ja foi gerado antes, e duas variacoes iguais dentro da
    mesma execucao tambem se anulam. Pagar de novo pela mesma pergunta e o
    desperdicio que este arquivo inteiro tenta evitar.
    """
    resultado = Resultado()
    sessao = sessao or requests.Session()
    vistas = set(ja_existentes or ())

    for pedido in pedidos:
        if resultado.uso.custo >= teto_em_dolar:
            resultado.parou_no_teto = True
            break

        quantas = pedido.get("quantas", VARIACOES_POR_QUESTAO)
        try:
            if pedido.get("modo") == "do_zero":
                novas, entrada, saida = do_zero(
                    pedido["materia"], pedido.get("assunto"),
                    pedido.get("exemplos") or [], chave, quantas, sessao,
                )
            else:
                novas, entrada, saida = variar(
                    pedido["questao"], chave, quantas, sessao
                )
        except Exception as erro:  # noqa: BLE001 - API fora do ar e rotina
            log.warning("pedido falhou (%s)", type(erro).__name__)
            resultado.falhas += 1
            continue

        resultado.uso.somar(entrada, saida)
        resultado.descartadas += max(0, quantas - len(novas))

        for questao in novas:
            if questao.impressao in vistas:
                log.info("questao gerada repetida, descartada")
                resultado.descartadas += 1
                continue
            vistas.add(questao.impressao)
            resultado.questoes.append(questao)

    return resultado
