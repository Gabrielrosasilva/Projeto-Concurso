"""Classifica o ASSUNTO fino de cada questao, com a API da Claude.

Por que esta e a unica parte do radar que custa dinheiro: as materias
universais foram resolvidas de graca, com um catalogo de palavras-chave escrito
a mao - ele cobre 76% dos enunciados de Portugues. Isso funciona porque
Portugues e sempre Portugues. Ja "Conhecimentos Especificos" muda com o cargo,
e o acervo tem 134 cargos diferentes: Servico Social, Psicologia,
Contabilidade, Enfermagem, cada area de professor. Um catalogo teria que cobrir
todas, e ai nao e mais catalogo, e adivinhacao.

Como o gasto e mantido pequeno:

  * **uma questao por enunciado.** Das 2.673 questoes de Conhecimentos
    Especificos, so 1.763 tem enunciado diferente - a banca repete muito;
  * **em lote.** Varias questoes por chamada, com a instrucao enviada uma vez
    so em vez de uma vez por questao;
  * **so o enunciado, sem as alternativas.** Para dizer o assunto, o enunciado
    basta, e as alternativas sao a maior parte do texto;
  * **teto de gasto**, conferido antes de cada chamada. O comando para quando
    chega nele, em vez de descobrir a conta depois.

Nao entra biblioteca nova por causa disto: a API e REST, e `requests` ja e
dependencia do projeto desde a primeira fase.
"""
import json
import logging
import re
import unicodedata
from dataclasses import dataclass, field

import requests

from radar import config

log = logging.getLogger(__name__)

API = "https://api.anthropic.com/v1/messages"
VERSAO_DA_API = "2023-06-01"

# O barato. Dizer o assunto de uma questao e tarefa de rotulagem, e nao de
# raciocinio - nao vale pagar por um modelo maior.
MODELO = "claude-haiku-4-5-20251001"

# Precos por milhao de tokens, em dolar. Estao aqui para o comando poder dizer
# quanto gastou; confira em anthropic.com/pricing antes de confiar no numero.
PRECO_ENTRADA = 1.00
PRECO_SAIDA = 5.00

# Quantas questoes por chamada. Com muitas, a resposta fica longa e o modelo
# comeca a pular item; com poucas, a instrucao e reenviada toda hora.
POR_LOTE = 25

# Quanto texto de cada enunciado vai junto. O assunto aparece nas primeiras
# linhas; o resto e enunciado de apoio e so encarece.
LIMITE_DO_ENUNCIADO = 400

INSTRUCAO = """Voce recebe questoes de concurso publico brasileiro, cada uma com um numero.

Para cada questao, responda o ASSUNTO especifico dela dentro da area, em no
maximo 4 palavras, em portugues.

Regras:
- seja especifico: "Etica profissional" e melhor que "Conhecimentos gerais";
- use o termo que um edital usaria, nao uma frase;
- se a questao for generica demais para ter assunto, responda "indefinido";
- nao explique, nao comente, nao repita a questao.

Responda SOMENTE um JSON, no formato:
{"1": "Etica profissional", "2": "Politicas sociais"}"""


# A instrucao muda inteira quando ha lista: de "invente um nome curto" para
# "escolha um destes". E a diferenca entre um rotulo que so existe aqui dentro
# e um que bate com o que o edital promete cobrar - e so o segundo serve para
# eu comparar o que caiu com o que vai cair.
INSTRUCAO_COM_LISTA = """Voce recebe questoes de concurso publico brasileiro, cada uma com um numero e a materia dela.

Para cada questao, ESCOLHA o assunto dela na lista da materia daquela questao.

Regras:
- so vale assunto que esteja na lista da materia da propria questao;
- copie o texto do assunto exatamente como esta escrito na lista: nao abrevie,
  nao corrija, nao reescreva;
- se nenhum assunto da lista servir para a questao, responda "indefinido";
- nao explique, nao comente, nao repita a questao.

Responda SOMENTE um JSON, no formato:
{"1": "Ortografia oficial", "2": "indefinido"}"""


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
class Resultado:
    classificados: dict[int, str] = field(default_factory=dict)
    uso: Uso = field(default_factory=Uso)
    parou_no_teto: bool = False
    falhas: int = 0


def _sem_acento(texto: str) -> str:
    normal = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in normal if not unicodedata.combining(c))


def _chave(texto: str) -> str:
    """Como dois nomes de assunto (ou de materia) sao comparados.

    Sem acento, sem caixa e sem espaco duplo: o modelo devolve o texto que a
    lista mandou, mas nem sempre com a mesma pontuacao no fim.
    """
    return re.sub(r"[^a-z0-9 ]", " ", _sem_acento(texto).lower()).strip()


def _lista_da_materia(permitidos: dict, materia: str | None) -> list[str]:
    """Os assuntos que valem para essa materia, comparando sem acento."""
    if not permitidos or not materia:
        return []
    procurado = _chave(materia)
    for nome, itens in permitidos.items():
        if _chave(nome) == procurado:
            return list(itens)
    return []


def _catalogo(questoes: list, permitidos: dict) -> str:
    """O trecho do pedido que lista os assuntos validos de cada materia.

    So entram as materias das questoes DESTE lote: mandar o programa inteiro a
    cada chamada seria pagar por 85 linhas para classificar 25 questoes de
    duas materias.
    """
    materias: list[str] = []
    for questao in questoes:
        nome = questao.materia or ""
        if nome and nome not in materias:
            materias.append(nome)

    blocos = []
    for nome in materias:
        itens = _lista_da_materia(permitidos, nome)
        if itens:
            blocos.append(f"{nome}:\n" + "\n".join(f"- {i}" for i in itens))
    return "ASSUNTOS PERMITIDOS\n\n" + "\n\n".join(blocos) if blocos else ""


def _montar_pedido(questoes: list, permitidos: dict | None = None) -> str:
    if permitidos:
        linhas = [
            f"{numero}. [{q.materia or 'sem materia'}] "
            f"{' '.join(q.enunciado[:LIMITE_DO_ENUNCIADO].split())}"
            for numero, q in enumerate(questoes, start=1)
        ]
        catalogo = _catalogo(questoes, permitidos)
        return f"{catalogo}\n\nQUESTOES\n\n" + "\n\n".join(linhas)

    linhas = [
        f"{numero}. {' '.join(q.enunciado[:LIMITE_DO_ENUNCIADO].split())}"
        for numero, q in enumerate(questoes, start=1)
    ]
    return "\n\n".join(linhas)


def estimar(questoes: list, permitidos: dict | None = None) -> tuple[int, int, float]:
    """(tokens de entrada, tokens de saida, custo em dolar) antes de gastar.

    A conta de tokens usa a regra pratica de ~3,5 caracteres por token em
    portugues. Serve para decidir se vale rodar, e nao para fechar conta.

    Com lista de assuntos o pedido cresce: alem da instrucao, cada lote leva a
    lista das materias que aparecem nele. A conta soma lote por lote porque e
    assim que o gasto acontece - um lote so de Portugues nao paga pela lista
    de Direito Penal.
    """
    if not questoes:
        return 0, 0, 0.0

    instrucao = INSTRUCAO_COM_LISTA if permitidos else INSTRUCAO
    caracteres = len(instrucao) * max(1, -(-len(questoes) // POR_LOTE))
    for inicio in range(0, len(questoes), POR_LOTE):
        lote = questoes[inicio:inicio + POR_LOTE]
        caracteres += len(_montar_pedido(lote, permitidos))

    entrada = int(caracteres / 3.5)
    # A resposta com lista e mais comprida: o modelo copia o texto do edital
    # inteiro ("Regras minimas da ONU para o tratamento de pessoas presas"),
    # em vez de escrever duas palavras.
    saida = len(questoes) * (40 if permitidos else 12)
    custo = entrada / 1e6 * PRECO_ENTRADA + saida / 1e6 * PRECO_SAIDA
    return entrada, saida, custo


def _ler_resposta(texto: str, quantas: int) -> dict[int, str]:
    """O JSON que o modelo respondeu, tolerando o que ele costuma acrescentar.

    As vezes vem cercado de ```json ... ```, ou com uma frase antes. Em vez de
    exigir resposta limpa, o JSON e recortado do meio do texto.
    """
    achado = re.search(r"\{.*\}", texto or "", re.DOTALL)
    if not achado:
        return {}

    try:
        cru = json.loads(achado.group(0))
    except json.JSONDecodeError:
        return {}

    lido: dict[int, str] = {}
    for chave, valor in cru.items():
        try:
            numero = int(str(chave).strip())
        except ValueError:
            continue
        # 200 porque o assunto agora pode ser a linha do edital inteira - a
        # LC 529/2011 do programa de 2019 tem 126 caracteres.
        rotulo = " ".join(str(valor).split())[:200]
        if 1 <= numero <= quantas and rotulo:
            lido[numero] = rotulo
    return lido


def _so_o_que_esta_na_lista(
    questoes: list, lido: dict[int, str], permitidos: dict
) -> dict[int, str]:
    """Descarta o que o modelo respondeu fora da lista da materia.

    A instrucao ja manda escolher dentro da lista, e este e o lugar onde isso
    para de ser pedido e vira garantia. Com o texto conferido aqui, o assunto
    que chega ao banco e sempre o do edital - palavra por palavra, inclusive
    a caixa e o acento que a lista usa.

    Resposta fora da lista vira "nao sei", e nao um assunto novo: um rotulo
    inventado no meio dos do edital seria pior do que a questao ficar sem
    assunto nenhum, porque eu nao teria como distinguir os dois na tela.
    """
    escolhidos: dict[int, str] = {}
    for numero, resposta in lido.items():
        questao = questoes[numero - 1]
        oficiais = {
            _chave(item): item
            for item in _lista_da_materia(permitidos, questao.materia)
        }
        certo = oficiais.get(_chave(resposta))
        if certo:
            escolhidos[numero] = certo
        else:
            log.info("assunto fora da lista descartado: %r", resposta)
    return escolhidos


def classificar_lote(
    questoes: list, chave: str, sessao=None, permitidos: dict | None = None
) -> tuple[dict, int, int]:
    """Manda um lote e devolve ({id da questao: assunto}, entrada, saida)."""
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
            # Com lista, a resposta copia o texto do edital e ocupa mais.
            "max_tokens": (60 if permitidos else 40) * len(questoes) + 300,
            "system": INSTRUCAO_COM_LISTA if permitidos else INSTRUCAO,
            "messages": [
                {"role": "user", "content": _montar_pedido(questoes, permitidos)}
            ],
        },
        timeout=config.TIMEOUT_REQUISICAO * 3,
    )
    resposta.raise_for_status()
    corpo = resposta.json()

    texto = "".join(
        parte.get("text", "") for parte in corpo.get("content") or []
    )
    uso = corpo.get("usage") or {}
    lido = _ler_resposta(texto, len(questoes))
    lido = {
        numero: assunto for numero, assunto in lido.items()
        if assunto.lower() != "indefinido"
    }
    if permitidos:
        lido = _so_o_que_esta_na_lista(questoes, lido, permitidos)

    # O numero do pedido volta para o id da questao no banco.
    por_id = {questoes[numero - 1].id: assunto for numero, assunto in lido.items()}
    return por_id, uso.get("input_tokens", 0), uso.get("output_tokens", 0)


def classificar(
    questoes: list,
    chave: str,
    teto_em_dolar: float = 1.0,
    sessao=None,
    permitidos: dict | None = None,
) -> Resultado:
    """Classifica as questoes em lotes, parando ao chegar no teto de gasto.

    O teto e conferido ANTES de cada chamada, com o custo real acumulado que a
    API informou - e nao com a estimativa. Assim a conta nunca passa do que foi
    autorizado por um lote inteiro.
    """
    resultado = Resultado()
    sessao = sessao or requests.Session()

    for inicio in range(0, len(questoes), POR_LOTE):
        if resultado.uso.custo >= teto_em_dolar:
            resultado.parou_no_teto = True
            break

        lote = questoes[inicio:inicio + POR_LOTE]
        try:
            classificados, entrada, saida = classificar_lote(
                lote, chave, sessao, permitidos
            )
        except Exception as erro:  # noqa: BLE001 - API fora do ar e rotina
            log.warning("lote falhou (%s)", type(erro).__name__)
            resultado.falhas += 1
            continue

        resultado.classificados.update(classificados)
        resultado.uso.somar(entrada, saida)

    return resultado
