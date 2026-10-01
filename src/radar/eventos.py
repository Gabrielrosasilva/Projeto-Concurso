"""A linha do tempo de cada concurso.

O resto do banco guarda so o AGORA: quando a situacao muda, o valor antigo e
sobrescrito. Isso responde "como esta este concurso?", mas nao responde nada
sobre o caminho ate aqui - e o caminho e o que ensina. Saber que a inscricao
da FEPESE costuma abrir tres semanas depois do edital vale mais do que saber
que hoje ela esta aberta.

Aqui cada mudanca vira uma linha, e a linha fica. Quem grava sao os pontos do
servico onde o campo muda de valor; este arquivo so sabe montar a frase e
guardar.

Regra que vale para o arquivo inteiro: **evento e fato observado, nao
interpretacao**. Se o radar nao viu a mudanca acontecer, ele nao inventa a
data - grava o momento em que percebeu, e a descricao diz o que mudou.
"""
import logging
import re

from sqlalchemy import select

from radar.models import SITUACOES, Evento, agora

log = logging.getLogger(__name__)

APARECEU = "apareceu"
MUDOU_SITUACAO = "mudou_situacao"
EDITAL_PUBLICADO = "edital_publicado"
INSCRICOES_ABERTAS = "inscricoes_abertas"
INSCRICOES_ENCERRADAS = "inscricoes_encerradas"
EDITAL_RETIFICADO = "edital_retificado"
PROVA_MARCADA = "prova_marcada"

# Situacao nova que tem evento proprio, em vez do generico `mudou_situacao`.
# Sair o edital, abrir e fechar inscricao sao os momentos que eu de fato
# preciso achar depois na linha do tempo; o resto do ciclo e passo de tramite.
EVENTO_DA_SITUACAO = {
    "edital_publicado": EDITAL_PUBLICADO,
    "inscricoes_abertas": INSCRICOES_ABERTAS,
    "encerrado": INSCRICOES_ENCERRADAS,
}

# O que merece tocar o celular, e so quando o concurso e FAVORITO.
#
# O corte e por consequencia, nao por raridade: estes cinco mudam o que eu
# tenho que FAZER. Saiu edital, eu leio; retificou, eu releio; abriu, eu me
# inscrevo; fechou, eu paro de contar com ele; marcou prova, eu marco na
# agenda. "Apareceu" e "mudou de prevista para autorizado" nao mudam nada hoje
# - eles ficam na linha do tempo, para eu ler quando quiser.
EVENTOS_IMPORTANTES = (
    EDITAL_PUBLICADO,
    EDITAL_RETIFICADO,
    INSCRICOES_ABERTAS,
    INSCRICOES_ENCERRADAS,
    PROVA_MARCADA,
)


def registrar(
    s,
    concurso_url: str,
    tipo: str,
    descricao: str,
    link: str | None = None,
    data=None,
) -> Evento:
    """Grava um evento na sessao aberta de quem chamou.

    Recebe a sessao em vez de abrir a propria: o evento tem que entrar no mesmo
    commit da mudanca que o gerou. Se a coleta falhar no meio, nao pode sobrar
    evento de uma mudanca que nao foi gravada.
    """
    evento = Evento(
        concurso_url=concurso_url,
        tipo=tipo,
        descricao=descricao[:300],
        link=link,
        data=data or agora(),
    )
    s.add(evento)
    return evento


def registrar_mudanca_de_situacao(
    s, concurso_url: str, antes: str | None, depois: str, link: str | None = None
) -> Evento | None:
    """O concurso andou no ciclo de vida. None quando nao andou.

    Abrir e fechar inscricao ganham tipo proprio; o resto fica no generico.
    A descricao carrega os dois valores porque e ela que responde "veio de
    onde?" - sem isso, a linha do tempo diria que algo mudou sem dizer o que.
    """
    if not depois or antes == depois:
        return None

    tipo = EVENTO_DA_SITUACAO.get(depois, MUDOU_SITUACAO)
    de = antes or "desconhecida"
    return registrar(
        s, concurso_url, tipo, f"Situacao: {de} -> {depois}", link
    )


def registrar_prazo(
    s,
    concurso_url: str,
    inscricoes_de,
    inscricoes_ate,
    link: str | None = None,
) -> Evento | None:
    """O prazo de inscricao ficou conhecido.

    E evento separado da situacao de proposito: descobrir o prazo lendo o
    edital e uma coisa, e a inscricao abrir de fato e outra. Costumam
    acontecer em dias diferentes, e as vezes na ordem inversa - o radar le o
    edital de um concurso cuja inscricao ja fechou.
    """
    if not inscricoes_ate:
        return None

    from radar.util import formatar_data

    if inscricoes_de:
        quando = f"de {formatar_data(inscricoes_de)} a {formatar_data(inscricoes_ate)}"
    else:
        quando = f"ate {formatar_data(inscricoes_ate)}"

    # O tipo segue a DATA, e nao a ordem em que eu fiquei sabendo. Descobrir
    # hoje um prazo que venceu semana passada e a leitura de um edital
    # atrasado, e nao uma inscricao abrindo - desde a etapa 8 isso vira
    # mensagem no Telegram, e um "inscricoes abertas" verde para concurso
    # fechado e o tipo de aviso que faz eu parar de confiar nos avisos.
    if inscricoes_ate < agora():
        return registrar(
            s, concurso_url, INSCRICOES_ENCERRADAS,
            f"Prazo de inscricao, ja encerrado: {quando}", link,
        )

    return registrar(
        s, concurso_url, INSCRICOES_ABERTAS, f"Prazo de inscricao: {quando}", link
    )


def registrar_prova_marcada(
    s, concurso_url: str, data_prova, link: str | None = None
) -> Evento | None:
    """A data da prova ficou conhecida."""
    if not data_prova:
        return None

    from radar.util import formatar_data

    return registrar(
        s,
        concurso_url,
        PROVA_MARCADA,
        f"Prova marcada para {formatar_data(data_prova)}",
        link,
    )


def registrar_retificacao(
    s, concurso_url: str, arquivo: str, link: str | None = None
) -> Evento:
    """O PDF do edital passou a devolver bytes diferentes.

    A descricao NAO diz o que mudou, porque o sha256 nao sabe: ele so prova
    que mudou. Dizer mais seria inventar.
    """
    return registrar(
        s,
        concurso_url,
        EDITAL_RETIFICADO,
        f"Edital retificado: {arquivo}. Retificacao muda prazo, vaga e "
        f"requisito - vale reler.",
        link,
    )


# --- como o evento aparece na tela ------------------------------------------
#
# A descricao gravada continua a de sempre ("Situacao: a -> b"): ela e chave
# de deduplicacao no acervo (CHAVE_DO_EVENTO) e vai assim para o eventos.json.
# Reescrever o banco por causa de texto de tela mudaria a chave e duplicaria
# eventos na proxima importacao. A traducao e so aqui, na hora de mostrar.

NOME_DA_SITUACAO = {
    "prevista": "previsto",
    "autorizado": "autorizado",
    "banca_definida": "banca contratada",
    "edital_publicado": "edital publicado",
    "inscricoes_abertas": "inscrições abertas",
    "encerrado": "encerrado",
    "desconhecida": "sem informação",
}

# A frase diz para onde o concurso FOI: de onde ele veio quase sempre e o passo
# anterior do ciclo, e repetir isso so alonga a linha do tempo.
FRASE_DA_SITUACAO = {
    "prevista": "O concurso passou a constar como previsto",
    "autorizado": "O concurso foi autorizado",
    "banca_definida": "A banca foi definida",
    "edital_publicado": "O edital foi publicado",
    "inscricoes_abertas": "As inscrições abriram",
    "encerrado": "As inscrições encerraram",
    "desconhecida": "A fonte deixou de informar a situação",
}

ROTULO_DO_TIPO = {
    APARECEU: "apareceu",
    MUDOU_SITUACAO: "mudou a situação",
    EDITAL_PUBLICADO: "edital publicado",
    INSCRICOES_ABERTAS: "inscrições abertas",
    INSCRICOES_ENCERRADAS: "inscrições encerradas",
    EDITAL_RETIFICADO: "edital retificado",
    PROVA_MARCADA: "prova marcada",
    # Nao e evento gravado, mas divide a lista de sinais com eles (foco.py).
    "noticia": "notícia",
}

_SITUACAO = re.compile(r"^Situacao: (\S+) -> (\S+)$")
_APARECEU = re.compile(r"^Entrou no radar pela fonte (.+), como (\S+)$")
_PRAZO = re.compile(r"^Prazo de inscricao(, ja encerrado)?: (?:(de .+ a .+)|ate (.+))$")
_RETIFICADO = re.compile(
    r"^Edital retificado: (.+)\. Retificacao muda prazo, vaga e requisito - vale reler\.$"
)


def _nome(situacao: str) -> str:
    return NOME_DA_SITUACAO.get(situacao, situacao.replace("_", " "))


def _frase_da_mudanca(antes: str, depois: str) -> str:
    """A frase de uma transicao de situacao.

    Andar para tras acontece (a fonte reabre ou corrige: o banco real tem
    "inscricoes_abertas -> edital_publicado"), e ai a frase do destino mentiria
    - o edital nao foi publicado de novo. Evento e fato observado: diz que
    voltou, e de onde para onde.
    """
    ciclo = [s for s in SITUACOES if s != "desconhecida"]
    if antes in ciclo and depois in ciclo and ciclo.index(depois) < ciclo.index(antes):
        return f"A situação voltou de {_nome(antes)} para {_nome(depois)}"
    if depois in FRASE_DA_SITUACAO:
        return FRASE_DA_SITUACAO[depois]
    return f"A situação mudou de {_nome(antes)} para {_nome(depois)}"


def para_tela(descricao: str | None) -> str:
    """A descricao gravada, em frase de gente.

    So reconhece as frases que este arquivo monta, e inteiras: qualquer outro
    texto (titulo de noticia, descricao antiga de formato desconhecido) passa
    como veio, em vez de ser remendado pela metade.
    """
    if not descricao:
        return ""

    if m := _SITUACAO.match(descricao):
        return _frase_da_mudanca(m.group(1), m.group(2))

    if m := _APARECEU.match(descricao):
        return f"Entrou no radar pela fonte {m.group(1)} (situação: {_nome(m.group(2))})"

    if m := _PRAZO.match(descricao):
        quando = m.group(2) or f"até {m.group(3)}"
        if m.group(1):
            return f"Prazo de inscrição, já encerrado: {quando}"
        return f"Prazo de inscrição: {quando}"

    if m := _RETIFICADO.match(descricao):
        return (f"Edital retificado: {m.group(1)}. Retificação muda prazo, "
                f"vaga e requisito - vale reler.")

    return descricao


def rotulo_do_tipo(tipo: str | None) -> str:
    """O nome curto do tipo de evento, com acento."""
    if not tipo:
        return ""
    return ROTULO_DO_TIPO.get(tipo, tipo.replace("_", " "))


def do_concurso(s, concurso_url: str) -> list[Evento]:
    """A linha do tempo de um concurso, do mais antigo para o mais novo.

    Ordem crescente porque e assim que se le uma historia. O `id` desempata
    eventos gravados no mesmo instante - uma coleta que descobre o prazo e a
    situacao de uma vez grava os dois com o mesmo carimbo de tempo.
    """
    consulta = (
        select(Evento)
        .where(Evento.concurso_url == concurso_url)
        .order_by(Evento.data.asc(), Evento.id.asc())
    )
    return list(s.scalars(consulta))
