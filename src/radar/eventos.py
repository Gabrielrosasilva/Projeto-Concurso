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

from sqlalchemy import select

from radar.models import Evento, agora

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
