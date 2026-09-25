"""Exportar e importar o banco como JSON.

Por que isto existe: a coleta diaria roda no GitHub Actions e precisa guardar
o resultado em algum lugar. Commitar o arquivo .db do SQLite funcionaria, mas
git guarda uma copia inteira de cada arquivo binario a cada commit — em um ano
seriam 365 copias do banco dentro do repositorio.

O JSON resolve os dois lados: e texto, entao o git guarda so a diferenca, e o
diff do commit diario fica legivel — da para abrir e ver exatamente quais
concursos entraram naquele dia.

Fluxo no Actions:  importar -> coletar -> exportar -> commit do JSON
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select

from radar import config
from radar.db import criar_tabelas, sessao
from radar.models import (
    Concurso,
    DataHoraUTC,
    Evento,
    QuestaoDeProva,
    QuestaoGerada,
)

# Colunas exportadas, em ordem fixa. Ordem fixa e chave ordenada deixam o
# arquivo estavel: mudou o diff, mudou o dado de verdade.
COLUNAS = [c.name for c in Concurso.__table__.columns if c.name != "id"]

# Quais delas sao data, perguntado ao PROPRIO modelo.
#
# Isto ja foi uma lista escrita a mao, e ela envelheceu calada: `avisado_em`
# entrou na fase 2 e `detalhado_em` na 2.5, nenhuma das duas foi acrescentada
# ali, e o `radar importar` passou a quebrar com "'str' object has no attribute
# 'tzinfo'" - a data voltava do JSON como texto. Na minha maquina isso nao
# aparecia, porque o banco ja existia; no GitHub Actions, que comeca sem banco
# todo dia, a coleta diaria falhava.
COLUNAS_DE_DATA = frozenset(
    c.name for c in Concurso.__table__.columns if isinstance(c.type, DataHoraUTC)
)


# O mesmo para a linha do tempo. Ela vive em arquivo proprio porque e outra
# coisa: `concursos.json` e o AGORA de cada concurso, e este aqui e o caminho
# que ele percorreu. Juntar os dois num arquivo so faria cada evento novo
# reescrever a linha do concurso inteira no diff.
COLUNAS_DE_EVENTO = [c.name for c in Evento.__table__.columns if c.name != "id"]

DATAS_DE_EVENTO = frozenset(
    c.name for c in Evento.__table__.columns if isinstance(c.type, DataHoraUTC)
)

# Como se reconhece que dois eventos sao o mesmo. O `id` nao serve: ele e
# autoincremental e cada maquina numera do seu jeito, entao o meu evento 7 e o
# do robo sao coisas diferentes. Estes quatro campos juntos sao o que descreve
# o acontecimento - e eventos gerados pela mesma coleta em maquinas diferentes
# coincidem nos quatro.
CHAVE_DO_EVENTO = ("concurso_url", "tipo", "data", "descricao")


def caminho_padrao() -> Path:
    return config.diretorio_dados() / "concursos.json"


def caminho_dos_eventos() -> Path:
    return config.diretorio_dados() / "eventos.json"


def _serializar(valor: Any) -> Any:
    return valor.isoformat() if isinstance(valor, datetime) else valor


def _desserializar(coluna: str, valor: Any, datas=None) -> Any:
    if valor is None:
        return None
    if coluna in (COLUNAS_DE_DATA if datas is None else datas):
        return datetime.fromisoformat(valor)
    return valor


def exportar(caminho: Path | None = None) -> int:
    """Escreve o banco inteiro no JSON. Devolve quantos registros gravou."""
    criar_tabelas()
    destino = caminho or caminho_padrao()

    with sessao() as s:
        # ordenado pela url para o diff nao embaralhar a cada execucao
        concursos = list(s.scalars(select(Concurso).order_by(Concurso.url)))
        linhas = [
            {coluna: _serializar(getattr(c, coluna)) for coluna in COLUNAS}
            for c in concursos
        ]

    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps(linhas, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return len(linhas)


# Estes dois campos tem DONO, e o dono e esta maquina. So eu mexo neles, pela
# web ou pela CLI; o robo do GitHub nunca escreve um favorito nem uma nota -
# ele so carrega os meus de um lado para o outro.
#
# Por isso o importar nao os atualiza: em concurso que ja existe aqui, o que
# esta no banco e a verdade, e o JSON e uma copia possivelmente velha. A
# primeira versao desta regra era mais fraca - "valor vazio nao apaga" - e
# tornava IMPOSSIVEL desmarcar: eu tirava a estrela, o sincronizar importava o
# JSON que ainda a tinha, e ela voltava.
#
# Eles sao escritos numa unica situacao: quando o concurso nao existe no banco
# local. E o computador novo, ou a reinstalacao - ali o JSON e tudo que existe,
# e e dele que os meus favoritos voltam.
CAMPOS_SO_MEUS = ("interesse", "notas")

# Estes dois tambem sao meus, mas eles acompanham um campo que a coleta
# escreve - o salario e o municipio. Para eles continua valendo a regra mais
# fraca: valor vazio no JSON nao apaga a marca que esta no banco.
CAMPOS_MEUS = ("salario_manual", "municipio_confirmado")

#: O que conta como "o JSON nao trouxe nada aqui".
VAZIOS = (None, "", False)


def importar(caminho: Path | None = None) -> int:
    """Recria o banco a partir do JSON. Devolve quantos registros leu.

    Nao apaga o que ja existe: casa pela url e atualiza. Rodar duas vezes da
    no mesmo resultado.

    O favorito e a nota (`CAMPOS_SO_MEUS`) so entram em concurso que AINDA NAO
    existe aqui - computador novo, ou reinstalacao. Em concurso que ja existe,
    o banco local manda e o JSON nao encosta: e isso que permite desmarcar.
    """
    origem = caminho or caminho_padrao()
    if not origem.exists():
        return 0

    criar_tabelas()
    linhas = json.loads(origem.read_text(encoding="utf-8"))

    with sessao() as s:
        for linha in linhas:
            concurso = s.scalar(select(Concurso).where(Concurso.url == linha["url"]))
            ja_existia = concurso is not None
            if concurso is None:
                concurso = Concurso(url=linha["url"])
                s.add(concurso)

            for coluna in COLUNAS:
                if coluna == "url" or coluna not in linha:
                    continue

                # Favorito e nota de concurso que ja esta aqui: o banco manda.
                if coluna in CAMPOS_SO_MEUS and ja_existia:
                    continue

                valor = _desserializar(coluna, linha[coluna])

                # Campo meu com o JSON vazio: o que esta no banco fica.
                if (
                    coluna in CAMPOS_MEUS
                    and valor in VAZIOS
                    and getattr(concurso, coluna) not in VAZIOS
                ):
                    continue
                setattr(concurso, coluna, valor)

    return len(linhas)


def exportar_eventos(caminho: Path | None = None) -> int:
    """Escreve a linha do tempo inteira no JSON. Devolve quantos gravou.

    Existe porque o robo do GitHub reconstroi o banco a partir do JSON a cada
    execucao: sem este arquivo ele nasce sem linha do tempo nenhuma, e nao tem
    como saber o que ja mudou - nem o que ja avisou.
    """
    criar_tabelas()
    destino = caminho or caminho_dos_eventos()

    with sessao() as s:
        # A ordem e a da leitura: por concurso, e dentro dele do mais antigo
        # para o mais novo. Ordem fixa faz o diff do commit diario mostrar so
        # as linhas que entraram.
        eventos = list(s.scalars(
            select(Evento).order_by(Evento.concurso_url, Evento.data, Evento.id)
        ))
        linhas = [
            {coluna: _serializar(getattr(e, coluna)) for coluna in COLUNAS_DE_EVENTO}
            for e in eventos
        ]

    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps(linhas, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return len(linhas)


def _chave(linha: dict) -> tuple:
    """A identidade do evento, para saber se ele ja esta no banco."""
    return tuple(
        _desserializar(coluna, linha.get(coluna), DATAS_DE_EVENTO)
        for coluna in CHAVE_DO_EVENTO
    )


def importar_eventos(caminho: Path | None = None) -> int:
    """Traz a linha do tempo do JSON. Devolve quantos eventos ENTRARAM.

    Evento que ja existe nao entra de novo - a comparacao e pelos quatro
    campos de `CHAVE_DO_EVENTO`, e nao pelo id, que cada maquina numera do
    seu jeito. Rodar duas vezes da no mesmo resultado.

    Do que ja existe, uma coisa e aproveitada: o `avisado_em`. Se o outro lado
    ja mandou aquele evento no Telegram e eu ainda nao, a marca dele vale -
    e assim que a fila de avisos passa a ser uma so em vez de duas.
    """
    origem = caminho or caminho_dos_eventos()
    if not origem.exists():
        return 0

    criar_tabelas()
    linhas = json.loads(origem.read_text(encoding="utf-8"))
    novos = 0

    with sessao() as s:
        existentes = {
            tuple(getattr(e, coluna) for coluna in CHAVE_DO_EVENTO): e
            for e in s.scalars(select(Evento))
        }

        for linha in linhas:
            ja_tenho = existentes.get(_chave(linha))
            if ja_tenho is not None:
                avisado = _desserializar(
                    "avisado_em", linha.get("avisado_em"), DATAS_DE_EVENTO
                )
                if avisado and ja_tenho.avisado_em is None:
                    ja_tenho.avisado_em = avisado
                continue

            evento = Evento(**{
                coluna: _desserializar(coluna, linha.get(coluna), DATAS_DE_EVENTO)
                for coluna in COLUNAS_DE_EVENTO
            })
            s.add(evento)
            existentes[_chave(linha)] = evento
            novos += 1

    return novos


# --- o assunto pago (etapa 14) ----------------------------------------------
#
# Este e o unico dado do projeto que custou dinheiro para existir. Ate aqui ele
# morava so no banco local: refazer o banco, ou trocar de computador, e eu
# pagaria de novo pela mesma questao. O arquivo existe para isso nao acontecer
# nunca - pago uma vez na vida por enunciado.
#
# A chave e a IMPRESSAO do enunciado, e nao o id nem a url da prova. O id muda
# quando o banco e reconstruido, e a mesma pergunta aparece em varios cadernos:
# a impressao e o que diz que duas questoes sao a mesma pergunta, e e por ela
# que uma classificacao paga rotula todas as copias.

def caminho_dos_assuntos() -> Path:
    return config.diretorio_dados() / "assuntos.json"


def exportar_assuntos(caminho: Path | None = None) -> int:
    """Grava o assunto pago de cada enunciado. Devolve quantos gravou."""
    criar_tabelas()
    destino = caminho or caminho_dos_assuntos()

    with sessao() as s:
        achados = s.execute(
            select(
                QuestaoDeProva.impressao,
                QuestaoDeProva.assunto,
                QuestaoDeProva.materia,
            )
            .where(QuestaoDeProva.assunto.is_not(None))
            .distinct()
        ).all()

    # Um enunciado, um assunto. Ordenado para o diff do commit ficar estavel, e
    # com o primeiro vencendo se o banco discordar de si mesmo - duas execucoes
    # tem que escrever o mesmo arquivo.
    por_enunciado: dict[str, dict] = {}
    for impressao, assunto, materia in sorted(achados):
        por_enunciado.setdefault(
            impressao,
            {"impressao": impressao, "assunto": assunto, "materia": materia},
        )

    linhas = list(por_enunciado.values())
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps(linhas, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return len(linhas)


def importar_assuntos(caminho: Path | None = None) -> int:
    """Devolve ao banco o assunto que ja foi pago. Quantas linhas mudaram.

    Vale para TODAS as questoes de mesmo enunciado, como na hora de gravar: o
    que foi pago uma vez rotula todas as copias daquela pergunta no acervo.

    O arquivo manda: ele e o registro do que foi comprado, e o banco local
    pode ter sido refeito do zero minutos atras.
    """
    origem = caminho or caminho_dos_assuntos()
    if not origem.exists():
        return 0

    criar_tabelas()
    linhas = json.loads(origem.read_text(encoding="utf-8"))
    if not linhas:
        return 0

    mudadas = 0
    with sessao() as s:
        for linha in linhas:
            impressao, assunto = linha.get("impressao"), linha.get("assunto")
            if not impressao or not assunto:
                continue
            for questao in s.scalars(
                select(QuestaoDeProva).where(QuestaoDeProva.impressao == impressao)
            ):
                if questao.assunto != assunto:
                    questao.assunto = assunto
                    mudadas += 1

    return mudadas


# --- as questoes que a IA escreveu ------------------------------------------
#
# Arquivo proprio, versionado, pelo mesmo motivo do assunto pago: elas
# custaram dinheiro e moravam so no banco local, que e reconstruivel e
# descartavel. Perder o arquivo e pagar de novo pela mesma questao.
#
# A chave e a IMPRESSAO do enunciado, e nao o id: o id muda quando o banco e
# refeito, e a impressao e o que diz que duas perguntas sao a mesma pergunta.
#
# O `rejeitada` vai junto de proposito. Ele e meu, nao da IA: e o registro de
# que eu li aquela questao e disse que estava errada. Sem ele no arquivo, um
# banco refeito me devolveria ao sorteio tudo que eu ja tinha descartado.

COLUNAS_DE_GERADA = [
    c.name for c in QuestaoGerada.__table__.columns if c.name != "id"
]

DATAS_DE_GERADA = frozenset(
    c.name for c in QuestaoGerada.__table__.columns
    if isinstance(c.type, DataHoraUTC)
)


def caminho_das_geradas() -> Path:
    return config.diretorio_dados() / "questoes_geradas.json"


def exportar_geradas(caminho: Path | None = None) -> int:
    """Grava as questoes geradas no JSON. Devolve quantas gravou."""
    criar_tabelas()
    destino = caminho or caminho_das_geradas()

    with sessao() as s:
        questoes = list(s.scalars(
            select(QuestaoGerada).order_by(QuestaoGerada.impressao)
        ))
        linhas = [
            {coluna: _serializar(getattr(q, coluna)) for coluna in COLUNAS_DE_GERADA}
            for q in questoes
        ]

    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps(linhas, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return len(linhas)


def importar_geradas(caminho: Path | None = None) -> int:
    """Devolve ao banco as questoes que ja foram geradas. Quantas entraram.

    O arquivo manda: ele e o registro do que foi comprado, e o banco local
    pode ter sido refeito do zero minutos atras. Questao que ja existe aqui
    tem so o `rejeitada` atualizado - o resto do texto nao muda mais depois de
    escrito, e reescrever seria arriscar perder o que esta na tela.
    """
    origem = caminho or caminho_das_geradas()
    if not origem.exists():
        return 0

    criar_tabelas()
    linhas = json.loads(origem.read_text(encoding="utf-8"))
    if not linhas:
        return 0

    novas = 0
    with sessao() as s:
        existentes = {
            q.impressao: q for q in s.scalars(select(QuestaoGerada))
        }
        for linha in linhas:
            impressao = linha.get("impressao")
            if not impressao or not linha.get("enunciado"):
                continue

            ja = existentes.get(impressao)
            if ja is not None:
                if linha.get("rejeitada") and not ja.rejeitada:
                    ja.rejeitada = True
                continue

            valores = {
                coluna: _desserializar(coluna, linha.get(coluna), DATAS_DE_GERADA)
                for coluna in COLUNAS_DE_GERADA
            }
            s.add(QuestaoGerada(**valores))
            novas += 1

    return novas
