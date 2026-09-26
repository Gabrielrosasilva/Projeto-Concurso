"""O cronograma de estudo: o que fazer em cada dia, e a que horas.

O conteudo mora em config/cronograma.yml, que e DADO e pode ser editado a
mao. Este arquivo so le, confere e faz a conta dos horarios - nao fala com
banco nem com rede, como o `onde_estudar`.

Os horarios NAO estao gravados no arquivo, de proposito. Cada faixa diz
quanto dura (ou quantas questoes tem), e o horario sai da soma a partir do
inicio do bloco. Assim, quando a rampa troca 15 questoes por 20, tudo o que
vem depois anda junto, sem ninguem reescrever horario a mao.
"""
import math
from dataclasses import dataclass, field, replace
from datetime import date, datetime, time, timedelta
from pathlib import Path

import yaml

from radar import config

# A ordem aqui e a ordem do dia.
BLOCOS = ("manha", "noite", "pos22")

# Os tipos que existem no arquivo. Tipo fora desta lista quase sempre e erro
# de digitacao, e erro de digitacao aqui vira icone errado ou faixa sumida
# na tela - melhor parar no carregamento.
TIPOS = {
    "teoria", "lei_seca", "portugues", "raciocinio", "pausa", "questoes",
    "revisao", "revisao_semanal", "correcao", "simulado", "diagnostico",
    "anki", "bonus",
}

# Arredondamento da duracao das faixas de questoes. 15 questoes x 2,5 min dao
# 37,5 min; ninguem marca 18:37, entao vira 40.
ARREDONDA_MINUTOS = 5

DIAS_DA_SEMANA = ("segunda-feira", "terça-feira", "quarta-feira",
                  "quinta-feira", "sexta-feira", "sábado", "domingo")
MESES = ("janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro")

DOMINGO = 6

# As tres regras do gatilho, que moram no YAML. Sem elas o nivel nao tem
# como ser calculado, entao faltar uma e erro de carregamento.
REGRAS_DO_GATILHO = ("sobe_com_dias_na_ideal", "semana_ruim_com_dias_abaixo",
                     "desce_apos_semanas_ruins")

# O nome da rampa na frase da tela ("Direito 20, Português 15").
NOME_DA_RAMPA = {"direito": "Direito", "portugues": "Português"}

# Meta que o feriado precisa bater para contar como "na Ideal".
METAS_QUE_SALVAM_O_FERIADO = {"ideal", "reduzida", "minima"}


class ErroNoCronograma(ValueError):
    """O arquivo tem um problema. A mensagem diz onde."""


@dataclass
class Faixa:
    """Uma linha do dia.

    No Plano, `duracao` e o que esta gravado (pode ser None, quando a faixa
    e de questoes) e `inicio`/`fim` ficam vazios. Quem preenche os tres e o
    `montar_dia`.
    """
    bloco: str
    tipo: str
    titulo: str
    detalhe: str | None = None
    materia: str | None = None
    questoes: int | None = None
    duracao: int | None = None
    inicio: time | None = None
    fim: time | None = None
    rampa: str | None = None
    filtro: str | None = None
    link: str | None = None
    baralho: str | None = None
    rotulo: str | None = None
    origem: str | None = None
    onde: str | None = None
    cronometrado: bool = False
    opcional: bool = False
    # So o simulado usa: la a conta e 3 min por questao, e nao o padrao.
    min_por_questao: float | None = None


@dataclass
class Dia:
    data: date
    semana: int
    feriado: str | None = None
    reduzida: str | None = None
    minima: str | None = None
    manha: list[Faixa] = field(default_factory=list)
    noite: list[Faixa] = field(default_factory=list)
    pos22: list[Faixa] = field(default_factory=list)

    def faixas(self) -> list[Faixa]:
        """Todas as faixas, na ordem do dia."""
        return self.manha + self.noite + self.pos22

    @property
    def total_questoes(self) -> int:
        # O bonus aparece na tela, mas nao e meta: se contasse, o dia em que
        # o trabalho aperta viraria dia "abaixo" sem motivo.
        return sum(f.questoes or 0 for f in self.faixas() if not f.opcional)

    @property
    def minutos_de_estudo(self) -> int:
        return sum(f.duracao or 0 for f in self.manha if f.tipo != "pausa")


@dataclass
class Bloco:
    chave: str
    nome: str
    inicio: time


@dataclass
class Plano:
    ciclo: int
    titulo: str
    inicio: date
    fim: date
    meta_da_prova: dict
    blocos: dict[str, Bloco]
    minutos_por_questao: float
    rampa: dict[int, dict[str, int]]
    gatilho: dict
    semanas: dict[int, str]
    dias: list[Dia]

    def dia(self, data: date) -> Dia | None:
        for dia in self.dias:
            if dia.data == data:
                return dia
        return None


# --- leitura -----------------------------------------------------------------

def _data(valor, onde: str) -> date:
    try:
        return date.fromisoformat(str(valor))
    except ValueError:
        raise ErroNoCronograma(f"{onde}: data invalida {valor!r} (use AAAA-MM-DD)")


def _horario(valor, bloco: str) -> time:
    try:
        return datetime.strptime(str(valor), "%H:%M").time()
    except ValueError:
        raise ErroNoCronograma(
            f"Bloco {bloco}: horario de inicio invalido {valor!r} (use HH:MM)"
        )


def _faixa(bruta: dict, bloco: str, data: date, chaves_da_rampa: set) -> Faixa:
    onde = f"Dia {data.isoformat()}, bloco {bloco}"
    tipo = bruta.get("tipo")
    if tipo not in TIPOS:
        raise ErroNoCronograma(f"{onde}: tipo desconhecido {tipo!r}")
    if bruta.get("duracao") is None and bruta.get("questoes") is None:
        raise ErroNoCronograma(
            f"{onde}: a faixa {bruta.get('titulo')!r} nao tem duracao nem questoes"
        )
    rampa = bruta.get("rampa")
    if rampa is not None and rampa not in chaves_da_rampa:
        raise ErroNoCronograma(
            f"{onde}: rampa {rampa!r} nao existe (conheco: "
            f"{', '.join(sorted(chaves_da_rampa))})"
        )
    return Faixa(
        bloco=bloco,
        tipo=tipo,
        titulo=bruta.get("titulo") or "",
        detalhe=bruta.get("detalhe"),
        materia=bruta.get("materia"),
        questoes=bruta.get("questoes"),
        duracao=bruta.get("duracao"),
        rampa=rampa,
        filtro=bruta.get("filtro"),
        link=bruta.get("link"),
        baralho=bruta.get("baralho"),
        rotulo=bruta.get("rotulo"),
        origem=bruta.get("origem"),
        onde=bruta.get("onde"),
        cronometrado=bool(bruta.get("cronometrado")),
        opcional=bool(bruta.get("opcional")),
        min_por_questao=bruta.get("min_por_questao"),
    )


def carregar(caminho: Path | None = None) -> Plano:
    """Le o cronograma e confere. Erro de conteudo vira ErroNoCronograma."""
    arquivo = caminho or (config.diretorio_config() / "cronograma.yml")
    dados = yaml.safe_load(Path(arquivo).read_text(encoding="utf-8")) or {}

    blocos = {}
    for chave in BLOCOS:
        bruto = (dados.get("blocos") or {}).get(chave)
        if not bruto:
            raise ErroNoCronograma(f"Falta o bloco {chave!r} em `blocos`")
        blocos[chave] = Bloco(chave, bruto.get("nome") or chave,
                              _horario(bruto.get("inicio"), chave))

    rampa = {int(nivel): dict(questoes)
             for nivel, questoes in (dados.get("rampa") or {}).items()}
    chaves_da_rampa = {chave for nivel in rampa.values() for chave in nivel}

    gatilho = dados.get("gatilho") or {}
    for regra in REGRAS_DO_GATILHO:
        if not isinstance(gatilho.get(regra), int):
            raise ErroNoCronograma(f"`gatilho` precisa de {regra} (numero inteiro)")

    dias = []
    vistas = set()
    for bruto in dados.get("dias") or []:
        data = _data(bruto.get("data"), "Dia")
        if data in vistas:
            raise ErroNoCronograma(f"Dia {data.isoformat()}: data repetida")
        if data.weekday() == DOMINGO:
            raise ErroNoCronograma(
                f"Dia {data.isoformat()}: e domingo, e domingo e descanso"
            )
        vistas.add(data)
        dia = Dia(
            data=data,
            semana=int(bruto.get("semana") or 0),
            feriado=bruto.get("feriado"),
            reduzida=bruto.get("reduzida"),
            minima=bruto.get("minima"),
        )
        for chave in BLOCOS:
            faixas = [_faixa(f, chave, data, chaves_da_rampa)
                      for f in bruto.get(chave) or []]
            setattr(dia, chave, faixas)
        dias.append(dia)

    return Plano(
        ciclo=dados.get("ciclo"),
        titulo=dados.get("titulo") or "",
        inicio=_data(dados.get("inicio"), "inicio do ciclo"),
        fim=_data(dados.get("fim"), "fim do ciclo"),
        meta_da_prova=dados.get("meta_da_prova") or {},
        blocos=blocos,
        minutos_por_questao=float(dados.get("minutos_por_questao") or 2.5),
        rampa=rampa,
        gatilho=gatilho,
        semanas={int(k): v for k, v in (dados.get("semanas") or {}).items()},
        dias=sorted(dias, key=lambda d: d.data),
    )


# --- a conta dos horarios ----------------------------------------------------

def duracao_de_questoes(questoes: int, min_por_questao: float) -> int:
    """Minutos para N questoes, arredondado PARA CIMA de 5 em 5."""
    # O round tira o lixo de ponto flutuante (ex.: 7.000000001) antes do
    # ceil, senao uma conta exata subiria 5 minutos sem motivo.
    blocos_de_5 = math.ceil(round(questoes * min_por_questao / ARREDONDA_MINUTOS, 6))
    return blocos_de_5 * ARREDONDA_MINUTOS


def montar_dia(plano: Plano, data: date, nivel: int | None = None) -> Dia | None:
    """O dia com o horario de cada faixa. None em domingo e fora do plano.

    Com `nivel`, a faixa de rampa usa o numero de questoes daquele nivel, e
    nao o gravado - e os horarios seguintes andam junto.
    """
    if data.weekday() == DOMINGO:
        return None
    gravado = plano.dia(data)
    if gravado is None:
        return None
    if nivel is not None and nivel not in plano.rampa:
        raise ErroNoCronograma(
            f"Nivel {nivel} nao existe na rampa (vai de {min(plano.rampa)} "
            f"a {max(plano.rampa)})"
        )

    dia = replace(gravado)
    for chave in BLOCOS:
        # datetime, e nao time, para a soma poder passar da meia-noite sem erro.
        relogio = datetime.combine(data, plano.blocos[chave].inicio)
        montadas = []
        for faixa in getattr(gravado, chave):
            questoes = faixa.questoes
            if nivel is not None and faixa.rampa:
                questoes = plano.rampa[nivel][faixa.rampa]
            duracao = faixa.duracao
            if duracao is None:
                duracao = duracao_de_questoes(
                    questoes, faixa.min_por_questao or plano.minutos_por_questao
                )
            fim = relogio + timedelta(minutes=duracao)
            montadas.append(replace(faixa, questoes=questoes, duracao=duracao,
                                    inicio=relogio.time(), fim=fim.time()))
            relogio = fim
        setattr(dia, chave, montadas)
    return dia


def faixa_atual(dia: Dia, agora: time) -> tuple[Faixa | None, Faixa | None]:
    """(o que esta acontecendo agora, o que vem depois).

    Entre dois blocos nao ha faixa atual, so a proxima. Depois da ultima, nada.
    """
    atual = None
    for faixa in dia.faixas():
        if faixa.inicio <= agora < faixa.fim:
            atual = faixa
        elif faixa.inicio > agora:
            return atual, faixa
    return atual, None


# --- o gatilho: o nivel da semana ---------------------------------------------

@dataclass
class Nivel:
    semana: int
    planejado: int            # o do plano, quando tudo vai bem: a semana N e o nivel N
    calculado: int            # o que o gatilho deu, olhando as semanas fechadas
    efetivo: int              # o que vale: o menor dos dois
    situacao: str             # primeira | subiu | neutra | ruim | desceu | aguardando
    motivo: str               # a frase pronta para a tela


@dataclass
class _Balanco:
    """Como fechou uma semana."""
    na_ideal: int = 0
    abaixo: int = 0
    zerados: int = 0
    sem_marcacao: int = 0


def _balanco(dias: list[Dia], metas: dict[date, str]) -> _Balanco:
    balanco = _Balanco()
    for dia in dias:
        meta = metas.get(dia.data)
        # A planilha pede pelo menos a minima no feriado; cumprir isso nao
        # pode derrubar a semana.
        if meta == "ideal" or (dia.feriado and meta in METAS_QUE_SALVAM_O_FERIADO):
            balanco.na_ideal += 1
            continue
        balanco.abaixo += 1
        if meta == "nao_fiz":
            balanco.zerados += 1
        elif meta is None:
            balanco.sem_marcacao += 1
    return balanco


def carga(plano: Plano, nivel: int) -> str:
    """'Direito 20, Português 15': o que o nivel significa na noite."""
    return ", ".join(f"{NOME_DA_RAMPA.get(chave, chave.capitalize())} {questoes}"
                     for chave, questoes in plano.rampa[nivel].items())


def _plural(n: int, uma: str, varias: str) -> str:
    return f"{n} {uma if n == 1 else varias}"


def _ordinal(n: int) -> str:
    nomes = {2: "Segunda", 3: "Terceira", 4: "Quarta", 5: "Quinta"}
    return nomes.get(n, f"{n}ª")


def _motivo(plano: Plano, situacao: str, anterior: int, b: _Balanco | None,
            efetivo: int, desce_apos: int) -> str:
    """A frase da tela, com os numeros que levaram ao nivel."""
    nivel = f"nível {efetivo} ({carga(plano, efetivo)})"
    if situacao == "primeira":
        return f"Primeira semana: nível {efetivo}."
    if situacao == "aguardando":
        return f"A semana {anterior} ainda não fechou: por ora, {nivel}."
    if situacao == "subiu":
        return (f"A semana {anterior} fechou com {_plural(b.na_ideal, 'dia', 'dias')} "
                f"na Ideal e nenhum zerado: {nivel}.")
    if situacao == "desceu":
        return f"{_ordinal(desce_apos)} semana ruim seguida: desce para o {nivel}."
    if situacao == "ruim":
        sem_marca = f" ({b.sem_marcacao} sem marcação)" if b.sem_marcacao else ""
        return (f"A semana {anterior} fechou com {_plural(b.abaixo, 'dia', 'dias')} "
                f"abaixo da Ideal{sem_marca}: repete o {nivel}.")
    # neutra
    resto = (f", mas {_plural(b.zerados, 'dia zerado', 'dias zerados')}"
             if b.zerados else f" e {b.abaixo} abaixo")
    return (f"A semana {anterior} fechou com {_plural(b.na_ideal, 'dia', 'dias')} "
            f"na Ideal{resto}: repete o {nivel}.")


def niveis(plano: Plano, metas: dict[date, str], hoje: date) -> dict[int, Nivel]:
    """O nivel de cada semana do ciclo, a partir do que eu marquei.

    `metas` e {data: meta} dos registros do diario. `hoje` decide quais
    semanas ja fecharam: so a semana com TODOS os dias no passado e avaliada.
    Os numeros das regras vem de `plano.gatilho`, nunca daqui.
    """
    sobe = plano.gatilho["sobe_com_dias_na_ideal"]
    ruim_com = plano.gatilho["semana_ruim_com_dias_abaixo"]
    desce_apos = plano.gatilho["desce_apos_semanas_ruins"]
    teto = max(plano.rampa)

    por_semana: dict[int, list[Dia]] = {}
    for dia in plano.dias:
        por_semana.setdefault(dia.semana, []).append(dia)

    resultado = {}
    calculado = 1
    ruins_seguidas = 0
    # O fechamento da semana anterior: None se ela ainda nao fechou. Semana
    # aberta trava todas as seguintes em "aguardando" - o gatilho nao chuta.
    fechamento = None
    alguma_aberta = False

    for semana in sorted(por_semana):
        planejado = min(max(semana, 1), teto)

        if not resultado:
            situacao = "primeira"
        elif fechamento is None:
            situacao = "aguardando"
        elif fechamento.abaixo >= ruim_com:
            ruins_seguidas += 1
            if ruins_seguidas >= desce_apos:
                calculado = max(calculado - 1, 1)
                ruins_seguidas = 0
                situacao = "desceu"
            else:
                situacao = "ruim"
        elif fechamento.na_ideal >= sobe and fechamento.zerados == 0:
            calculado = min(calculado + 1, teto)
            ruins_seguidas = 0
            situacao = "subiu"
        else:
            # "Seguidas" quer dizer uma logo depois da outra: a neutra no
            # meio separa duas ruins, e a contagem recomeca.
            ruins_seguidas = 0
            situacao = "neutra"

        efetivo = min(planejado, calculado)
        resultado[semana] = Nivel(
            semana, planejado, calculado, efetivo, situacao,
            _motivo(plano, situacao, semana - 1, fechamento, efetivo, desce_apos),
        )

        dias = por_semana[semana]
        if not alguma_aberta and all(d.data < hoje for d in dias):
            fechamento = _balanco(dias, metas)
        else:
            fechamento = None
            alguma_aberta = True

    return resultado


def data_por_extenso(data: date) -> str:
    """'segunda-feira, 28 de setembro de 2026'. Sem depender do locale do SO."""
    return (f"{DIAS_DA_SEMANA[data.weekday()]}, {data.day} de "
            f"{MESES[data.month - 1]} de {data.year}")
