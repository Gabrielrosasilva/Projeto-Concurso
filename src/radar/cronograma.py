"""O cronograma de estudo: o que fazer em cada dia, e a que horas.

O conteudo mora em config/cronograma.yml, que e DADO e pode ser editado a
mao. Este arquivo so le, confere e faz a conta dos horarios - nao fala com
banco nem com rede, como o `onde_estudar`.

Os horarios NAO estao gravados no arquivo, de proposito. Cada faixa diz
quanto dura (ou quantas questoes tem), e o horario sai da soma a partir do
inicio do bloco. Assim, quando a rampa troca 15 questoes por 20, tudo o que
vem depois anda junto, sem ninguem reescrever horario a mao.
"""
import json
import math
from dataclasses import dataclass, field, replace
from datetime import date, datetime, time, timedelta
from pathlib import Path

import yaml

from radar import config
from radar.conteudos import SEPARADOR
from radar.origem import AUTOMATICO

# A ordem aqui e a ordem do dia.
BLOCOS = ("manha", "noite", "pos22")
# O Plano B nao e um bloco do arquivo: e o dia inteiro trocado por um bloco
# so, montado a partir do dia (montar_plano_b). Os checks da tela usam este
# nome como se fosse um bloco a mais.
BLOCO_DO_PLANO_B = "plano_b"
TODOS_OS_BLOCOS = BLOCOS + (BLOCO_DO_PLANO_B,)

# Os tipos que existem no arquivo. Tipo fora desta lista quase sempre e erro
# de digitacao, e erro de digitacao aqui vira icone errado ou faixa sumida
# na tela - melhor parar no carregamento.
TIPOS = {
    "teoria", "lei_seca", "portugues", "raciocinio", "pausa", "questoes",
    "revisao", "revisao_semanal", "correcao", "simulado", "diagnostico",
    "anki", "bonus", "essencial",
}

# O nome e o icone do tipo na tela, no terminal e na web. O cru (lei_seca) e
# para o arquivo.
TIPO_LEGIVEL = {
    "teoria": "Teoria", "lei_seca": "Lei seca", "portugues": "Português",
    "raciocinio": "Raciocínio", "pausa": "Pausa", "questoes": "Questões",
    "revisao": "Revisão", "revisao_semanal": "Revisão semanal",
    "correcao": "Correção", "simulado": "Simulado",
    "diagnostico": "Diagnóstico", "anki": "Anki", "bonus": "Bônus",
    "essencial": "Essencial",
}
ICONE_DO_TIPO = {
    "teoria": "📖", "lei_seca": "⚖️", "portugues": "✍️", "raciocinio": "🧩",
    "pausa": "☕", "questoes": "🎯", "revisao": "🔁", "revisao_semanal": "🗂️",
    "correcao": "📝", "simulado": "🏁", "diagnostico": "🩺", "anki": "🃏",
    "bonus": "⭐", "essencial": "📌",
}

# As faixas em que eu respondo questao, e portanto as que guardam "fiz X,
# acertei Y". As outras (teoria, lei seca, pausa, correcao, Anki) so se marcam
# como feitas. `revisao_semanal` fica fora de proposito: ela e "refaca os seus
# erros da semana", sem numero de questoes proprio.
TIPOS_COM_ACERTO = {"questoes", "revisao", "simulado", "diagnostico", "bonus"}

# As faixas que REVISAM o que ja foi estudado. Marcadas num conteudo, sao elas
# que dao a data da ultima revisao dele no Meu desempenho (decisao 79).
TIPOS_DE_REVISAO = {"revisao", "revisao_semanal"}


def tem_acerto(faixa) -> bool:
    """Esta faixa guarda acerto? E a pergunta que decide o formulario na tela."""
    return faixa.tipo in TIPOS_COM_ACERTO


def consulta_por_padrao(faixa) -> bool:
    """A caixa "com consulta" ja vem marcada nesta faixa?

    Manda a chave `consulta` da faixa, quando o arquivo a tem - e o caso da
    fixacao da manha (Etapa 6A), feita logo depois de ler o tema. Sem a chave,
    vem marcada so na faixa de APRENDIZAGEM de Direito - a `rampa: direito`,
    cujo proprio detalhe diz "PODE consultar a lei". As duas treinam e nao
    medem, e por isso ficam fora da comparacao com a meta (docs/decisoes.md).
    Todas as outras vem desmarcadas: sem consulta e o padrao da prova.
    """
    if faixa.consulta is not None:
        return faixa.consulta
    return faixa.tipo == "questoes" and faixa.rampa == "direito"


# A chave `anki` do topo do cronograma.yml. Desativado, o Anki some do dia sem
# sair do arquivo: as faixas e os baralhos continuam la, e religar e trocar
# uma palavra (README, "Religar o Anki").
ANKI_ATIVADO = "ativado"
ANKI_DESATIVADO = "desativado"
FRASE_DO_ANKI_DESATIVADO = "ANKI temporariamente desativado"


# Arredondamento da duracao das faixas de questoes. 15 questoes x 2,5 min dao
# 37,5 min; ninguem marca 18:37, entao vira 40.
ARREDONDA_MINUTOS = 5

DIAS_CURTOS = ("Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom")
DIAS_DA_SEMANA = ("segunda-feira", "terça-feira", "quarta-feira",
                  "quinta-feira", "sexta-feira", "sábado", "domingo")
MESES = ("janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro")

DOMINGO = 6

# Na meta Reduzida, o lugar do numero de questoes de Direito. O numero muda
# com o nivel, entao ele nao pode estar escrito no texto: quem preenche e o
# montar_dia, com a faixa `rampa: direito` do dia ja montado.
MARCA_DO_DIREITO = "{direito}"

# As tres regras do gatilho, que moram no YAML. Sem elas o nivel nao tem
# como ser calculado, entao faltar uma e erro de carregamento.
REGRAS_DO_GATILHO = ("sobe_com_dias_na_ideal", "semana_ruim_com_dias_abaixo",
                     "desce_apos_semanas_ruins")

# O nome da rampa na frase da tela ("Direito 20, Português 15").
NOME_DA_RAMPA = {"direito": "Direito", "portugues": "Português"}

# Meta que o feriado precisa bater para contar como "na Ideal".
METAS_QUE_SALVAM_O_FERIADO = {"ideal", "reduzida", "minima"}


SABADO = 5

# Os campos de cada opcao do Plano B. Faltar um e erro de carregamento: sem
# ele o botao nao sabe quanto dura nem quantas questoes pedir.
CAMPOS_DA_OPCAO = ("minutos", "essencial_minutos", "questoes_direito",
                   "questoes_portugues", "com_apoio")


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
    # So a faixa "essencial" do Plano B usa: os artigos a ler e o aviso.
    artigos: list = field(default_factory=list)
    aviso: str | None = None
    # A chave `consulta` da faixa. None = a regra do `consulta_por_padrao`.
    consulta: bool | None = None
    # O no da arvore de conteudos, pelo caminho ("Direito Penal > ..."). E a
    # chave `conteudo` da faixa (Etapa 2), conferida no carregamento contra o
    # data/conteudos.json. Opcional: o titulo continua dizendo o tema.
    conteudo: str | None = None
    # Os nos que a faixa COBRE, quando ela nao tem ficha e um no so nao basta
    # (o bonus de tabelas-verdade e equivalencias sao dois assuntos do
    # edital). Como os `nos` da ficha: so dizem onde a faixa esta na arvore,
    # na tela. O `conteudo` continua sendo o no em que o acerto e anotado.
    nos: tuple = ()
    # As materias de uma rodada que mede mais de uma (o simulado de fechamento
    # de 07/11). A composicao das questoes sai do `servico/composicao.py`; aqui
    # so a lista, conferida contra o bloco `materias` - nunca numero (dec. 67).
    materias_da_rodada: tuple = ()
    # O dia com que a faixa compara as rodadas do proprio dia (a correcao do
    # fechamento de 07/11 compara com o diagnostico de 03/10). AAAA-MM-DD,
    # como a `origem`; quem compara e o `servico/sabado.py`.
    compara_com: str | None = None
    # A redistribuicao do Ciclo 1 (R4, decisao 108): a faixa de rampa de um
    # tema que nao caiu fica com no maximo `teto` questoes, e a faixa com
    # `sobra_da_rampa` (a "Extra" de um tema que caiu) recebe o resto - a
    # rampa do nivel menos o teto. O total do dia nao muda em nivel nenhum.
    teto: int | None = None
    sobra_da_rampa: str | None = None
    # A faixa do Anki com `anki: desativado`. Ela continua na lista, na mesma
    # posicao: os checks sao reconhecidos por bloco e posicao, e tira-la
    # mudaria a posicao do Bonus que vem depois. Desligada, ela nao tem
    # duracao, nao entra em total nem na sugestao de meta, e nao se marca.
    desligada: bool = False


@dataclass
class ArtigoEssencial:
    artigos: str        # "LEP art. 112"
    porque: str         # a frase que diz o que o artigo manda


@dataclass
class Essencial:
    """Os artigos-chave do tema do dia, para o Plano B.

    Selecao do plano, feita a partir do texto da lei - NAO e o que a banca
    mais cobra: o Direito ainda nao tem assunto no acervo para medir isso.
    """
    chave: list[ArtigoEssencial]
    apoio: list[ArtigoEssencial] = field(default_factory=list)
    aviso: str | None = None


@dataclass
class OpcaoDoPlanoB:
    minutos: int
    essencial_minutos: int
    questoes_direito: int
    questoes_portugues: int
    com_apoio: bool


@dataclass
class PlanoB:
    opcoes: dict[int, OpcaoDoPlanoB]     # pelos minutos: 30, 60
    sabado: str
    sabado_questoes: int


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
    essencial: Essencial | None = None
    # So o dia devolvido pelo montar_plano_b tem isto; os tres de cima ficam
    # vazios nele.
    plano_b: list[Faixa] = field(default_factory=list)

    def faixas(self) -> list[Faixa]:
        """Todas as faixas que valem, na ordem do dia.

        A desligada (o Anki com `anki: desativado`) fica de fora: ela nao e
        "a proxima faixa", nao soma e nao tem materia. Quem precisa dela - a
        tela, que mostra a linha minimizada, e os checks, que contam posicao -
        le o bloco direto (`dia.pos22`).
        """
        todas = self.manha + self.noite + self.pos22 + self.plano_b
        return [f for f in todas if not f.desligada]

    @property
    def total_questoes(self) -> int:
        # O bonus aparece na tela, mas nao e meta: se contasse, o dia em que
        # o trabalho aperta viraria dia "abaixo" sem motivo.
        return sum(f.questoes or 0 for f in self.faixas() if not f.opcional)

    @property
    def minutos_de_estudo(self) -> int:
        return sum(f.duracao or 0 for f in self.manha if f.tipo != "pausa")


@dataclass
class MateriaDoEdital:
    """Uma materia da prova: quantas questoes ela tem e quantas eu quero acertar.

    Os numeros sao do edital de 2019 (o ultimo), e a meta e minha - a soma
    delas e a meta total da prova. Isto e DADO, em config/cronograma.yml.
    """
    nome: str
    questoes: int
    meta: int

    @property
    def porcentagem_da_meta(self) -> int:
        """Quantos por cento eu preciso acertar nesta materia."""
        return round(100 * self.meta / self.questoes) if self.questoes else 0


@dataclass
class EtapaDoMapa:
    """Uma linha do mapa do ano: um ciclo, a pausa de fim de ano, o pos-edital.

    E so para eu me situar - nada do dia a dia sai daqui. A etapa sem
    `inicio` e a que depende de coisa que ainda nao aconteceu, e por isso ela
    nunca e a de agora.
    """
    nome: str
    foco: str
    inicio: date | None = None
    fim: date | None = None
    quando: str | None = None     # o "quando sair", quando nao ha data

    def contem(self, data: date) -> bool:
        """`data` cai nesta etapa? Sem `fim`, a etapa vale dali em diante."""
        if self.inicio is None or data < self.inicio:
            return False
        return self.fim is None or data <= self.fim

    def terminou(self, data: date) -> bool:
        """Ja acabou nesta data? Etapa em aberto nunca acaba."""
        return self.fim is not None and self.fim < data

    @property
    def periodo(self) -> str:
        """O periodo como ele se le na tela."""
        if self.quando:
            return self.quando
        if self.inicio is None:
            return "sem data"
        if self.fim is None:
            return f"a partir de {self.inicio:%d/%m/%Y}"
        return f"{self.inicio:%d/%m/%Y} a {self.fim:%d/%m/%Y}"


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
    plano_b: PlanoB | None = None
    # O ano inteiro, em seis linhas. Vazio quando o arquivo nao tem `mapa`:
    # o mapa e enfeite util, e a tela Hoje nao pode depender dele.
    mapa: list[EtapaDoMapa] = field(default_factory=list)
    # As materias da prova, com a meta de acertos de cada uma.
    materias: list[MateriaDoEdital] = field(default_factory=list)
    # Os rotulos que aparecem em `materia` de faixa e NAO sao materia do
    # edital, porque a faixa e mista. Ver `_materias_das_faixas`.
    materias_mistas: list[str] = field(default_factory=list)
    # A chave `anki` do arquivo. Sem ela, ativado: e como o arquivo era antes.
    anki: bool = True

    def dia(self, data: date) -> Dia | None:
        for dia in self.dias:
            if dia.data == data:
                return dia
        return None

    def etapa_do_mapa(self, data: date) -> EtapaDoMapa | None:
        """Em que etapa do ano cai `data`. None no vao entre duas etapas."""
        return next((etapa for etapa in self.mapa if etapa.contem(data)), None)

    def materia(self, nome: str | None) -> MateriaDoEdital | None:
        """A materia do edital com esse nome, ou None (inclusive nas mistas)."""
        if not nome:
            return None
        return next((m for m in self.materias if m.nome == nome), None)

    def e_mista(self, nome: str | None) -> bool:
        """Este rotulo cobre mais de uma materia? Ai ele nao pontua em nenhuma."""
        return bool(nome) and nome in self.materias_mistas

    @property
    def meta_total(self) -> int:
        """A soma das metas: quantos acertos eu quero na prova inteira."""
        return sum(m.meta for m in self.materias)

    @property
    def questoes_da_prova(self) -> int:
        return sum(m.questoes for m in self.materias)


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
    sobra = bruta.get("sobra_da_rampa")
    if bruta.get("duracao") is None and bruta.get("questoes") is None and not sobra:
        raise ErroNoCronograma(
            f"{onde}: a faixa {bruta.get('titulo')!r} nao tem duracao nem questoes"
        )
    rampa = bruta.get("rampa")
    if rampa is not None and rampa not in chaves_da_rampa:
        raise ErroNoCronograma(
            f"{onde}: rampa {rampa!r} nao existe (conheco: "
            f"{', '.join(sorted(chaves_da_rampa))})"
        )
    if sobra is not None and sobra not in chaves_da_rampa:
        raise ErroNoCronograma(f"{onde}: sobra_da_rampa {sobra!r} nao e chave da rampa")
    teto = bruta.get("teto")
    if teto is not None and (not isinstance(teto, int) or teto <= 0 or not rampa):
        raise ErroNoCronograma(f"{onde}: `teto` e um inteiro positivo, so em faixa de rampa")
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
        consulta=(bool(bruta["consulta"]) if bruta.get("consulta") is not None
                  else None),
        conteudo=bruta.get("conteudo"),
        nos=tuple(bruta.get("nos") or ()),
        materias_da_rodada=tuple(bruta.get("materias_da_rodada") or ()),
        # Conferida no carregamento: data errada aqui faria a comparacao sumir
        # da tela sem aviso nenhum.
        compara_com=(_data(bruta["compara_com"], f"{onde}, compara_com").isoformat()
                     if bruta.get("compara_com") else None),
        teto=teto,
        sobra_da_rampa=sobra,
    )


def _artigos(brutos, onde: str) -> list[ArtigoEssencial]:
    if not isinstance(brutos, list):
        raise ErroNoCronograma(f"{onde}: precisa ser uma lista de artigos")
    lidos = []
    for bruto in brutos:
        bruto = bruto or {}
        for campo in ("artigos", "porque"):
            if not bruto.get(campo):
                raise ErroNoCronograma(f"{onde}: um item esta sem `{campo}`")
        lidos.append(ArtigoEssencial(str(bruto["artigos"]), str(bruto["porque"])))
    return lidos


def _essencial(bruto, data: date) -> Essencial | None:
    if bruto is None:
        return None
    onde = f"Dia {data.isoformat()}, essencial"
    if not bruto.get("chave"):
        raise ErroNoCronograma(f"{onde}: falta a lista `chave` (os artigos do Plano B de 30 min)")
    return Essencial(
        chave=_artigos(bruto["chave"], f"{onde}, chave"),
        apoio=_artigos(bruto.get("apoio") or [], f"{onde}, apoio"),
        aviso=bruto.get("aviso"),
    )


def _plano_b(bruto) -> PlanoB | None:
    if bruto is None:
        return None
    opcoes = {}
    for opcao in bruto.get("opcoes") or []:
        opcao = opcao or {}
        for campo in CAMPOS_DA_OPCAO:
            if opcao.get(campo) is None:
                raise ErroNoCronograma(
                    f"`plano_b`: uma opcao esta sem `{campo}` "
                    f"(cada uma precisa de {', '.join(CAMPOS_DA_OPCAO)})"
                )
        minutos = int(opcao["minutos"])
        opcoes[minutos] = OpcaoDoPlanoB(
            minutos, int(opcao["essencial_minutos"]), int(opcao["questoes_direito"]),
            int(opcao["questoes_portugues"]), bool(opcao["com_apoio"]),
        )
    if not opcoes:
        raise ErroNoCronograma("`plano_b`: falta a lista `opcoes` (30 min e 1 hora)")
    for campo in ("sabado", "sabado_questoes"):
        if bruto.get(campo) is None:
            raise ErroNoCronograma(f"`plano_b`: falta `{campo}`")
    return PlanoB(opcoes, str(bruto["sabado"]), int(bruto["sabado_questoes"]))


def _etapa_do_mapa(cru: dict, ordem: int) -> EtapaDoMapa:
    """Uma etapa, ja conferida por dentro."""
    onde = f"`mapa`, etapa {ordem}"
    nome = str(cru.get("nome") or "").strip()
    if not nome:
        raise ErroNoCronograma(f"{onde}: falta o `nome`")
    foco = str(cru.get("foco") or "").strip()
    if not foco:
        raise ErroNoCronograma(f"{onde} ({nome}): falta o `foco` (uma linha)")

    inicio = _data(cru["inicio"], f"{onde} ({nome}), inicio") if cru.get("inicio") else None
    fim = _data(cru["fim"], f"{onde} ({nome}), fim") if cru.get("fim") else None
    if inicio is None and fim is not None:
        raise ErroNoCronograma(f"{onde} ({nome}): tem `fim` sem ter `inicio`")
    if inicio and fim and fim < inicio:
        raise ErroNoCronograma(
            f"{onde} ({nome}): o fim ({fim.isoformat()}) vem antes do inicio "
            f"({inicio.isoformat()})"
        )
    return EtapaDoMapa(nome, foco, inicio, fim, str(cru["quando"]) if cru.get("quando") else None)


def _mapa(bruto) -> list[EtapaDoMapa]:
    """Le o bloco `mapa` e confere a ordem da lista.

    As tres regras existem para eu nao me enganar editando o arquivo a mao:
    as datas em ordem, sem sobreposicao (uma etapa comeca DEPOIS do fim da
    anterior, e nao no mesmo dia), e etapa sem data so no fim da lista.

    Vao entre duas etapas e permitido de proposito: entre o Ciclo 1 e o 2 ha
    um domingo, e esse domingo nao pertence a nenhum dos dois.
    """
    etapas = [_etapa_do_mapa(cru, ordem)
              for ordem, cru in enumerate(bruto or [], start=1)]

    for anterior, etapa in zip(etapas, etapas[1:]):
        if etapa.inicio is None:
            continue          # sem data: so pode vir depois, e vem
        if anterior.inicio is None:
            raise ErroNoCronograma(
                f"`mapa`: {etapa.nome} tem data e vem depois de {anterior.nome}, "
                f"que nao tem - etapa sem data e a ultima da lista"
            )
        if anterior.fim is None:
            raise ErroNoCronograma(
                f"`mapa`: {anterior.nome} fica em aberto (sem `fim`), entao nada "
                f"pode vir depois dela - e {etapa.nome} vem"
            )
        if etapa.inicio <= anterior.fim:
            raise ErroNoCronograma(
                f"`mapa`: {etapa.nome} comeca em {etapa.inicio.isoformat()}, "
                f"antes de {anterior.nome} acabar ({anterior.fim.isoformat()})"
            )
    return etapas


def _materias(bruto) -> list[MateriaDoEdital]:
    """Le o bloco `materias` e confere o que so se descobre lendo tudo junto.

    Duas regras, e as duas sao para eu nao me enganar editando a mao: nome
    repetido (eu duplicaria a linha e dividiria a materia em duas) e meta
    maior que o numero de questoes (querer 12 acertos numa materia de 10).
    """
    materias = []
    vistos = set()
    for ordem, cru in enumerate(bruto or [], start=1):
        onde = f"`materias`, item {ordem}"
        nome = str(cru.get("nome") or "").strip()
        if not nome:
            raise ErroNoCronograma(f"{onde}: falta o `nome`")
        if nome in vistos:
            raise ErroNoCronograma(f"`materias`: {nome} aparece duas vezes")
        vistos.add(nome)
        try:
            questoes = int(cru["questoes"])
            meta = int(cru["meta"])
        except (KeyError, TypeError, ValueError):
            raise ErroNoCronograma(
                f"{onde} ({nome}): `questoes` e `meta` precisam ser numeros inteiros"
            )
        if questoes <= 0:
            raise ErroNoCronograma(f"{onde} ({nome}): `questoes` precisa ser maior que zero")
        if meta < 0:
            raise ErroNoCronograma(f"{onde} ({nome}): `meta` nao pode ser negativa")
        if meta > questoes:
            raise ErroNoCronograma(
                f"`materias`: a meta de {nome} ({meta}) e maior que as questoes "
                f"que a prova tem dela ({questoes})"
            )
        materias.append(MateriaDoEdital(nome, questoes, meta))
    return materias


def _conferir_materias_das_faixas(dias: list[Dia], materias: list[MateriaDoEdital],
                                  mistas: list[str]) -> None:
    """Toda materia escrita numa faixa precisa existir no bloco `materias`.

    E isto que pega o erro de digitacao: "Direito Penall" numa faixa passaria
    despercebido para sempre, e as questoes daquele dia nao entrariam na conta
    de materia nenhuma. Faixa SEM materia (pausa, correcao, simulado misto) nao
    e conferida - ela conta no geral e em nenhuma materia.

    `materias_mistas` e a saida para a faixa que tem rotulo de materia mas
    cobre mais de uma (o R+7 dos diagnosticos, que refaz Raciocinio Logico e
    Portugues juntos). Ela vale como faixa sem materia.
    """
    if not materias:
        return          # sem o bloco, nao ha o que conferir
    conhecidas = {m.nome for m in materias} | set(mistas)
    do_edital = {m.nome for m in materias}
    for dia in dias:
        for faixa in dia.faixas():
            if faixa.materia and faixa.materia not in conhecidas:
                raise ErroNoCronograma(
                    f"Dia {dia.data.isoformat()}: a faixa {faixa.titulo!r} e de "
                    f"{faixa.materia!r}, que nao esta em `materias`. Se for "
                    f"materia mesmo, some ela la; se a faixa cobrir mais de uma, "
                    f"some o nome em `materias_mistas`."
                )
            # A rodada que mede varias materias so aceita materia do edital: e
            # do peso dela no edital que sai a divisao das questoes.
            for nome in faixa.materias_da_rodada:
                if nome not in do_edital:
                    raise ErroNoCronograma(
                        f"Dia {dia.data.isoformat()}: a faixa {faixa.titulo!r} "
                        f"tem {nome!r} em `materias_da_rodada`, que nao esta em "
                        f"`materias`."
                    )


def _conferir_conteudos_das_faixas(dias: list[Dia]) -> None:
    """Toda chave `conteudo`, e todo caminho da lista `nos`, precisa ser um no
    da arvore - e os `nos`, da materia da faixa.

    Pela mesma razao da materia: um caminho digitado errado nunca ligaria a
    faixa a nada, e ninguem perceberia. A arvore vem do data/conteudos.json,
    e nao do banco - este arquivo nao fala com banco.
    """
    usados = [(dia, f) for dia in dias for f in dia.faixas() if f.conteudo or f.nos]
    if not usados:
        return
    arquivo = config.diretorio_dados() / "conteudos.json"
    if not arquivo.exists():
        return          # sem a arvore, nao ha contra o que conferir
    conhecidos = {linha["caminho"] for linha in
                  json.loads(arquivo.read_text(encoding="utf-8")) or []}
    for dia, faixa in usados:
        for caminho in ([faixa.conteudo] if faixa.conteudo else []) + list(faixa.nos):
            if caminho not in conhecidos:
                raise ErroNoCronograma(
                    f"Dia {dia.data.isoformat()}: a faixa {faixa.titulo!r} aponta para o "
                    f"conteúdo {caminho!r}, que não está na árvore "
                    f"(data/conteudos.json). Confira com `radar conteudos`."
                )
        for caminho in faixa.nos:
            if faixa.materia and not caminho.startswith(faixa.materia + SEPARADOR):
                raise ErroNoCronograma(
                    f"Dia {dia.data.isoformat()}: a faixa {faixa.titulo!r} é de "
                    f"{faixa.materia!r}, e o nó {caminho!r} é de outra matéria."
                )


# O cronograma.yml tem uns 180 mil caracteres, e uma pagina do painel o le
# varias vezes. O leitor em C do PyYAML (a libyaml) le o mesmo arquivo uns 8
# vezes mais rapido, com o mesmo resultado; sem ela, fica o leitor em Python.
LEITOR_DO_YAML = getattr(yaml, "CSafeLoader", yaml.SafeLoader)


def carregar(caminho: Path | None = None) -> Plano:
    """Le o cronograma e confere. Erro de conteudo vira ErroNoCronograma."""
    arquivo = caminho or (config.diretorio_config() / "cronograma.yml")
    dados = yaml.load(Path(arquivo).read_text(encoding="utf-8"),
                      Loader=LEITOR_DO_YAML) or {}

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

    plano_b = _plano_b(dados.get("plano_b"))
    anki = _anki(dados.get("anki"))

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
            essencial=_essencial(bruto.get("essencial"), data),
        )
        # Com Plano B no arquivo, todo dia util precisa dos artigos-chave: sem
        # eles o botao abriria um Plano B vazio justo no dia corrido.
        if plano_b and data.weekday() < SABADO and dia.essencial is None:
            raise ErroNoCronograma(
                f"Dia {data.isoformat()}: falta `essencial` (os artigos-chave "
                f"do Plano B) - todo dia util precisa dele"
            )
        for chave in BLOCOS:
            faixas = [_faixa(f, chave, data, chaves_da_rampa)
                      for f in bruto.get(chave) or []]
            if not anki:
                faixas = [_sem_anki(f) for f in faixas]
            setattr(dia, chave, faixas)
        for faixa in dia.faixas():
            if faixa.sobra_da_rampa and _faixa_com_teto(dia, faixa.sobra_da_rampa) is None:
                raise ErroNoCronograma(
                    f"Dia {data.isoformat()}: a faixa {faixa.titulo!r} recebe a sobra da "
                    f"rampa {faixa.sobra_da_rampa!r}, mas o dia nao tem faixa dessa "
                    f"rampa com `teto`")
        if (MARCA_DO_DIREITO in (dia.reduzida or "")
                and _faixa_do_direito(dia) is None):
            raise ErroNoCronograma(
                f"Dia {data.isoformat()}: a Reduzida usa {MARCA_DO_DIREITO}, "
                f"mas o dia nao tem faixa com `rampa: direito`"
            )
        dias.append(dia)

    materias = _materias(dados.get("materias"))
    mistas = [str(nome).strip() for nome in (dados.get("materias_mistas") or [])]
    _conferir_materias_das_faixas(dias, materias, mistas)
    _conferir_conteudos_das_faixas(dias)

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
        plano_b=plano_b,
        mapa=_mapa(dados.get("mapa")),
        materias=materias,
        materias_mistas=mistas,
        anki=anki,
    )


def _anki(valor) -> bool:
    """A chave `anki`: ativado (o padrao, sem a chave) ou desativado."""
    if valor is None:
        return True
    if valor not in (ANKI_ATIVADO, ANKI_DESATIVADO):
        raise ErroNoCronograma(
            f"`anki` e {ANKI_ATIVADO!r} ou {ANKI_DESATIVADO!r} (veio {valor!r})"
        )
    return valor == ANKI_ATIVADO


def _sem_anki(faixa: Faixa) -> Faixa:
    """A faixa como ela aparece com o Anki desativado: a do Anki desligada, e
    o chip do baralho fora de todas. O arquivo nao muda."""
    return replace(faixa, baralho=None, desligada=faixa.tipo == "anki")


# --- a conta dos horarios ----------------------------------------------------

def duracao_de_questoes(questoes: int, min_por_questao: float) -> int:
    """Minutos para N questoes, arredondado PARA CIMA de 5 em 5."""
    # O round tira o lixo de ponto flutuante (ex.: 7.000000001) antes do
    # ceil, senao uma conta exata subiria 5 minutos sem motivo.
    blocos_de_5 = math.ceil(round(questoes * min_por_questao / ARREDONDA_MINUTOS, 6))
    return blocos_de_5 * ARREDONDA_MINUTOS


def _faixa_do_direito(dia: Dia) -> Faixa | None:
    return next((f for f in dia.faixas() if f.rampa == "direito"), None)


def _faixa_com_teto(dia: Dia, chave: str) -> Faixa | None:
    """A faixa da rampa `chave` que tem `teto` (a do tema que nao caiu)."""
    return next((f for f in dia.faixas() if f.rampa == chave and f.teto), None)


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

    def da_rampa(faixa: Faixa) -> int:
        """O numero da rampa no nivel; sem nivel, o que o arquivo grava."""
        if nivel is not None and faixa.rampa:
            return plano.rampa[nivel][faixa.rampa]
        return faixa.questoes or 0

    for chave in BLOCOS:
        # datetime, e nao time, para a soma poder passar da meia-noite sem erro.
        relogio = datetime.combine(data, plano.blocos[chave].inicio)
        montadas = []
        for faixa in getattr(gravado, chave):
            if faixa.desligada:
                # Sem duracao: o relogio nao anda, e o Bonus que vem depois
                # comeca as 22h em vez de esperar um Anki que nao existe.
                montadas.append(replace(faixa, duracao=0, inicio=relogio.time(),
                                        fim=relogio.time()))
                continue
            questoes = faixa.questoes
            if nivel is not None and faixa.rampa:
                questoes = plano.rampa[nivel][faixa.rampa]
            if faixa.teto:
                questoes = min(da_rampa(faixa), faixa.teto)
            if faixa.sobra_da_rampa:
                com_teto = _faixa_com_teto(gravado, faixa.sobra_da_rampa)
                questoes = max(da_rampa(com_teto) - com_teto.teto, 0)
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

    direito = _faixa_do_direito(dia)
    if dia.reduzida and direito is not None:
        dia.reduzida = dia.reduzida.replace(MARCA_DO_DIREITO, str(direito.questoes))
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


# --- o Plano B -------------------------------------------------------------------
# O dia corrido: sem teoria, sem Anki, sem pausa e sem horario. So o essencial
# do tema do dia e questoes de prova dele. A lista de artigos e selecao do
# plano (config/cronograma.yml), e nao o que a banca mais cobra; e nao ha
# resumo escrito por IA - resumo de lei feito por modelo erra artigo.

def montar_plano_b(plano: Plano, data: date, minutos: int,
                   nivel: int | None = None) -> Dia | None:
    """O Dia do Plano B: as faixas ficam em `plano_b`, sem horario.

    None em domingo e fora do plano. `nivel` so serve para montar o dia de
    onde saem o tema e o filtro - o numero de questoes e o do `plano_b`.
    """
    if plano.plano_b is None:
        raise ErroNoCronograma("O config/cronograma.yml nao tem o bloco `plano_b`")
    opcao = plano.plano_b.opcoes.get(minutos)
    if opcao is None:
        raise ErroNoCronograma(
            f"Plano B de {minutos} min nao existe (ha: "
            f"{', '.join(str(m) for m in sorted(plano.plano_b.opcoes))})"
        )
    dia = montar_dia(plano, data, nivel)
    if dia is None:
        return None
    b = Dia(data=dia.data, semana=dia.semana, feriado=dia.feriado,
            reduzida=dia.reduzida, minima=dia.minima, essencial=dia.essencial)

    if data.weekday() == SABADO:
        b.plano_b = [Faixa(
            bloco=BLOCO_DO_PLANO_B, tipo="revisao",
            titulo="Refazer as questões erradas da semana",
            detalhe=plano.plano_b.sabado, questoes=plano.plano_b.sabado_questoes,
            duracao=duracao_de_questoes(plano.plano_b.sabado_questoes,
                                        plano.minutos_por_questao),
            onde="qconcursos",
        )]
        return b

    if dia.essencial is None:
        raise ErroNoCronograma(f"Dia {data.isoformat()}: falta `essencial` para o Plano B")
    teoria = next((f for f in dia.manha if f.tipo == "teoria"), None)
    direito = _faixa_do_direito(dia)
    portugues = next((f for f in dia.faixas() if f.rampa == "portugues"), None)
    tema = teoria.titulo if teoria else (direito.titulo if direito else "o tema do dia")

    artigos = list(dia.essencial.chave)
    if opcao.com_apoio:
        artigos += dia.essencial.apoio
    faixas = [Faixa(
        bloco=BLOCO_DO_PLANO_B, tipo="essencial",
        titulo=f"Artigos-chave: {tema}",
        materia=teoria.materia if teoria else (direito.materia if direito else None),
        duracao=opcao.essencial_minutos,
        link=teoria.link if teoria else None,
        detalhe="Leia no texto oficial, só estes artigos.",
        artigos=artigos, aviso=dia.essencial.aviso,
    )]
    if direito is not None:
        faixas.append(Faixa(
            bloco=BLOCO_DO_PLANO_B, tipo="questoes",
            titulo=f"Questões de prova: {tema}",
            materia=direito.materia, filtro=direito.filtro, onde=direito.onde,
            questoes=opcao.questoes_direito,
            duracao=duracao_de_questoes(opcao.questoes_direito, plano.minutos_por_questao),
        ))
    if opcao.questoes_portugues > 0 and portugues is not None:
        faixas.append(Faixa(
            bloco=BLOCO_DO_PLANO_B, tipo="questoes",
            titulo=portugues.titulo, materia=portugues.materia,
            filtro=portugues.filtro, onde=portugues.onde,
            questoes=opcao.questoes_portugues, opcional=True,
            duracao=duracao_de_questoes(opcao.questoes_portugues, plano.minutos_por_questao),
        ))
    b.plano_b = faixas
    return b


# --- o gatilho: o nivel da semana ---------------------------------------------

@dataclass
class Nivel:
    #: A origem do selo (Etapa 7A): o gatilho e conta do sistema.
    origem = AUTOMATICO

    semana: int
    planejado: int            # o do plano, quando tudo vai bem: a semana N e o nivel N
    calculado: int            # o que o gatilho deu, olhando as semanas fechadas
    efetivo: int              # o que vale: o menor dos dois
    situacao: str             # primeira | subiu | neutra | ruim | desceu | futura
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


def balanco_da_semana(dias: list[Dia], metas: dict[date, str]) -> _Balanco:
    """Como uma semana fechou: dias na Ideal, abaixo, zerados e sem marcacao.

    A MESMA conta do gatilho, e de proposito a mesma funcao: a tela de Semanas
    nao pode dizer "4 dias completos" enquanto o gatilho conta 3. O feriado
    cumprido na minima tambem conta como completo aqui, pelo mesmo motivo de la.
    """
    return _balanco(dias, metas)


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
    if situacao == "futura":
        return (f"Semana futura: carga do plano ({carga(plano, efetivo)}). O nível "
                f"de verdade sai quando a semana {anterior} fechar.")
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

    Semana cuja anterior ainda nao fechou e "futura": fica na carga do
    PLANO. Sem isso, olhar um dia de novembro em
    setembro contava as semanas do meio como fechadas sem marcacao - ruins -
    e mostrava uma carga que nenhum fato justificava. O `hoje` certo para
    isso e o de `servico.cronograma.hoje_do_gatilho`.
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
    # aberta deixa todas as seguintes em "futura" - o gatilho nao chuta.
    fechamento = None
    alguma_aberta = False

    for semana in sorted(por_semana):
        planejado = min(max(semana, 1), teto)
        dias = por_semana[semana]

        if resultado and fechamento is None:
            # A anterior ainda nao fechou: o gatilho nao tem o que dizer, e a
            # semana fica na carga do plano. Nao mexe em `calculado` nem na
            # contagem de ruins - o que nao aconteceu nao pesa na conta.
            resultado[semana] = Nivel(
                semana, planejado, calculado, planejado, "futura",
                _motivo(plano, "futura", semana - 1, None, planejado, desce_apos),
            )
            alguma_aberta = True
            continue

        if not resultado:
            situacao = "primeira"
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

        if not alguma_aberta and all(d.data < hoje for d in dias):
            fechamento = _balanco(dias, metas)
        else:
            fechamento = None
            alguma_aberta = True

    return resultado


def duracao_legivel(minutos: int) -> str:
    """120 -> '2h', 110 -> '1h50', 40 -> '40 min'."""
    horas, resto = divmod(minutos, 60)
    if not horas:
        return f"{resto} min"
    return f"{horas}h{resto:02d}" if resto else f"{horas}h"


def data_por_extenso(data: date) -> str:
    """'segunda-feira, 28 de setembro de 2026'. Sem depender do locale do SO."""
    return (f"{DIAS_DA_SEMANA[data.weekday()]}, {data.day} de "
            f"{MESES[data.month - 1]} de {data.year}")
