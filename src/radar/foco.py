"""A situacao do alvo principal, reunida num lugar so.

O resto do radar responde "o que existe?". Esta tela responde a unica pergunta
que eu faco todo dia: **e agora, o que esta acontecendo com a Policia Penal
SC?** Quem e o alvo sai de `config/alvo.yml`, e nada aqui e escrito no codigo.

A regra que manda no arquivo inteiro: **nunca inventar**. Toda funcao daqui
devolve None, lista vazia ou um campo nulo quando o dado nao existe, e a tela
diz "nao sei ainda". Dado errado sobre o meu proprio concurso e pior do que
tela vazia: eu estudaria a materia errada, ou deixaria de estudar achando que
ainda ha tempo.

A banca e o exemplo disso. Ate sair edital novo, ela e HIPOTESE - a FEPESE fez
2013 e 2019, e isso e historia, nao promessa. O campo carrega essa diferenca
para que a tela nunca escreva "banca: FEPESE" como se fosse fato.
"""
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from sqlalchemy import func, select

from radar import alvo as alvos
from radar import config, edital_materias, edital_programa, macetes, onde_estudar, provas
from radar.db import criar_tabelas, sessao
from radar.eventos import Evento
from radar.models import Concurso, QuestaoDeProva, RespostaDeSimulado
from radar.questoes import extrair_texto
from radar.regioes import normalizar

log = logging.getLogger(__name__)

# Situacoes em que existe inscricao para fazer AGORA.
SITUACOES_ABERTAS = ("inscricoes_abertas",)

# Quantos sinais recentes cabem na tela sem ela virar um log.
SINAIS_NA_TELA = 8

# Quantas questoes o botao de treino sorteia. Vinte e o que cabe num intervalo
# de estudo sem virar sessao longa.
QUESTOES_DO_TREINO = 20


@dataclass
class Banca:
    """Quem organiza o concurso - ou quem organizou, quando ainda e palpite."""

    nome: str | None = None
    #: False enquanto nao ha edital novo dizendo quem e. Ai o nome e historia.
    confirmada: bool = False
    #: Os anos em que essa banca ja fez o concurso. Vazio = nao sei.
    anos: list[int] = field(default_factory=list)

    @property
    def como_hipotese(self) -> str:
        """A frase que a tela usa. Ela NUNCA afirma o que nao esta confirmado."""
        if not self.nome:
            return "não sei ainda"
        if self.confirmada:
            return self.nome
        if self.anos:
            anos = " e ".join(str(a) for a in self.anos)
            return f"hipótese: {self.nome}, que fez {anos}"
        return f"hipótese: {self.nome}"


@dataclass
class Edicao:
    """Uma vez em que o concurso saiu."""

    ano: int | None
    titulo: str
    url: str
    situacao: str
    banca: str | None = None
    inscricoes_ate: datetime | None = None


@dataclass
class DeOlho:
    """Uma vaga da lista `de_olho` do config/alvo.yml, e como ela esta hoje.

    Nao e o alvo principal e nao finge ser: e um cargo secundario numa cidade
    que eu escolhi a dedo. Campo vazio quer dizer que nada dela apareceu no
    radar ainda - e nao que nao ha concurso.
    """

    cargo: str
    cidade: str
    situacao: str | None = None
    titulo: str | None = None
    url: str | None = None
    inscricoes_ate: datetime | None = None

    @property
    def nome(self) -> str:
        return f"{self.cargo} de {self.cidade}"


@dataclass
class Painel:
    """Tudo que a tela de foco mostra. Campo vazio = nao sei ainda."""

    nome_do_alvo: str = "alvo principal"
    configurado: bool = True

    #: Edital aberto agora PARA O CARGO. None = nao ha, ou nao sei.
    aberto: Edicao | None = None
    #: Edital aberto na mesma secretaria, mas de outro cargo. Fica separado
    #: porque anunciar "edital aberto" por causa de uma vaga de medico seria
    #: dizer o que nao e.
    aberto_no_orgao: Edicao | None = None
    #: A ultima vez que o concurso saiu. None = nunca vi sair.
    ultima: Edicao | None = None
    banca: Banca = field(default_factory=Banca)

    #: O que o edital diz sobre validade. Texto do proprio edital, nao resumo.
    validade: str | None = None
    #: A data em que a validade comeca a contar. Quase sempre None: ela sai na
    #: homologacao, publicada no Diario Oficial, que este projeto nao le.
    validade_desde: datetime | None = None

    sinais: list = field(default_factory=list)
    materias_do_edital: list = field(default_factory=list)
    total_do_edital: int = 0
    ano_do_edital: int | None = None
    incidencia: dict = field(default_factory=dict)
    anos_das_provas: list[int] = field(default_factory=list)
    questoes_para_treinar: int = 0

    #: Como eu vou em cada materia, pelo nome que o EDITAL usa. Materia que eu
    #: nunca treinei nao aparece aqui - ela nao tem acerto, e nao tem zero.
    acerto_por_materia: dict = field(default_factory=dict)
    #: As materias que puxam mais nota. Ver `materias_de_maior_peso`.
    materias_pesadas: set = field(default_factory=set)
    #: A pior das pesadas. None quando nenhuma delas foi treinada ainda.
    pior_materia: str | None = None

    #: As vagas da lista `de_olho`, uma linha por cidade. Vazia quando o
    #: config/alvo.yml nao pede nenhuma.
    de_olho: list = field(default_factory=list)

    #: Por qual ASSUNTO comecar, ordenado por quanto ha para ganhar em cada
    #: um. Vazia quando nenhuma questao do acervo tem assunto ainda.
    onde_comecar: list = field(default_factory=list)
    #: A frase montada dos numeros da primeira linha acima. None = sem linha.
    conclusao_do_estudo: str | None = None
    #: Quantos assuntos ficaram fora da tela por nao caberem no grafico.
    assuntos_fora_da_tela: int = 0
    #: Quantas questoes do cargo ainda nao tem assunto nenhum. E o que separa
    #: "este assunto nao cai" de "eu ainda nao classifiquei esta questao".
    questoes_sem_assunto: int = 0
    #: As materias do edital em que NENHUMA questao minha tem assunto. Elas
    #: nao podem apenas sumir do grafico: uma materia que vale 10 questoes
    #: desaparecer da tela e a tela escondendo o que nao sabe. Cada uma vira
    #: uma linha "nao sei ainda", com o peso que ela tem no edital.
    materias_sem_assunto: list = field(default_factory=list)


def _concursos_do_alvo(s) -> list[Concurso]:
    """Todo concurso marcado como alvo principal, do mais novo para o velho."""
    return list(s.scalars(
        select(Concurso)
        .where(Concurso.alvo == alvos.PRINCIPAL)
        .order_by(Concurso.publicado_em.desc().nullslast())
    ))


def _ano(concurso: Concurso) -> int | None:
    """O ano do concurso pelo titulo da FEPESE ("2019 - Secretaria...").

    Sem ano no titulo, cai para o ano da publicacao. Sem nenhum dos dois,
    devolve None - e a tela mostra o concurso sem ano em vez de inventar um.
    """
    achado = re.match(r"\s*(\d{4})", concurso.titulo or "")
    if achado:
        return int(achado.group(1))
    return concurso.publicado_em.year if concurso.publicado_em else None


def _como_edicao(concurso: Concurso) -> Edicao:
    return Edicao(
        ano=_ano(concurso),
        titulo=concurso.titulo,
        url=concurso.url,
        situacao=concurso.situacao,
        banca=concurso.banca,
        inscricoes_ate=concurso.inscricoes_ate,
    )


def _edital_com_prova(concursos: list[Concurso]) -> Concurso | None:
    """A ultima edicao que de fato virou prova.

    Nao e simplesmente a mais recente: o feed traz noticia e seletivo do mesmo
    orgao, e "SEJURI abre vaga para Medico" nao e uma edicao do concurso que
    eu espero. Vale quem tem prova no acervo - so quem fez prova deixa prova.
    """
    com_prova = {
        r.get("concurso_url")
        for r in provas.carregar_manifesto()
        if r.get("tipo") == provas.PROVA
    }
    for concurso in concursos:
        if concurso.url in com_prova:
            return concurso
    return None


def _banca_do_alvo(s, concursos: list[Concurso], provas_do_alvo: set[str]) -> Banca:
    """Quem faz o concurso, ou quem fez - a diferenca fica registrada.

    Enquanto nao ha edital aberto, o nome vem de `config/alvo.yml`, onde eu
    anotei quem organizou as edicoes anteriores. Isso e HIPOTESE, e o campo
    `confirmada` existe para a tela nunca escrever isso como fato.
    """
    # So edital aberto DO CARGO confirma banca. O seletivo de medico da mesma
    # secretaria pode ter outra banca, e ela nao diz nada sobre a minha prova.
    aberto = next(
        (
            c for c in concursos
            if c.situacao in SITUACOES_ABERTAS and c.banca
            and alvos.nomeia_cargo_do_principal(c.titulo, c.resumo)
        ),
        None,
    )
    if aberto:
        return Banca(nome=aberto.banca, confirmada=True)

    nomes = alvos.bancas_do_principal()
    if not nomes:
        return Banca()

    # Os anos vem do acervo, e nao do YAML: e prova que aquela banca fez aquele
    # ano, e nao anotacao minha que pode ter envelhecido.
    anos = _anos_com_prova(s, provas_do_alvo, nomes[0])
    return Banca(nome=nomes[0], confirmada=False, anos=anos)


def _e_do_cargo(cargo: str | None) -> bool:
    """Esta questao e de uma prova do cargo que eu quero?

    Quem responde e `alvo.sinonimos_do_cargo`, que ja trata os `termos` do
    YAML como os varios nomes do MESMO cargo e ja aplica a lista `exclui`.
    Antes esta funcao comparava so os `termos`, e por isso uma prova de
    "Policial Penal Federal" - que contem "policial penal" - entrava nas
    contas da tela como se fosse minha. Ela e outro concurso, e tem bloco
    proprio nos alvos secundarios.

    A comparacao e feita em Python, e nao no SQL, por causa do acento: o LIKE
    do SQLite ignora maiuscula mas NAO ignora acento, e o cargo gravado e
    "Agente Penitenciario" com acento enquanto o termo do YAML vem sem. Com
    ilike, as 170 questoes do cargo davam zero.
    """
    return bool(alvos.sinonimos_do_cargo(cargo or ""))


def _anos_com_prova(s, provas_do_alvo: set[str], banca: str) -> list[int]:
    """Em que anos essa banca deixou prova do CARGO no acervo.

    Do cargo, e nao da banca: a FEPESE deixou prova de dezenas de concursos,
    e so as do meu cargo contam como "ja fez este aqui".
    """
    if not provas_do_alvo:
        return []

    linhas = s.execute(
        select(QuestaoDeProva.ano, QuestaoDeProva.banca)
        .where(QuestaoDeProva.prova_url.in_(provas_do_alvo))
        .distinct()
    ).all()

    alvo_banca = normalizar(banca)
    return sorted({
        ano for ano, banca_da_prova in linhas
        if ano and alvo_banca in normalizar(banca_da_prova or "")
    })


def _de_olho(s) -> list[DeOlho]:
    """Como esta cada vaga da lista `de_olho` do config/alvo.yml.

    Uma linha por cidade pedida, SEMPRE - mesmo a que nao tem nada no radar.
    Sumir com a linha vazia seria responder "nao ha concurso" a uma pergunta
    que ninguem fez: o que eu sei e que nada apareceu, que e outra coisa.

    A consulta so alcanca quem ja esta marcado como prioritario, que e um
    punhado de linhas: a conta de qual cartao cada concurso preenche e feita
    em Python, com o mesmo `alvo.par_de_olho` que decidiu a marca.
    """
    pedidas = alvos.de_olho()
    if not pedidas:
        return []

    marcados = list(s.scalars(
        select(Concurso)
        .where(Concurso.alvo_prioritario.is_(True))
        .order_by(Concurso.publicado_em.desc().nullslast())
    ))

    cartoes = []
    for pedida in pedidas:
        par = (pedida["cargo"], pedida["cidade"])
        dessa = [
            c for c in marcados
            if alvos.par_de_olho(c.titulo, c.resumo, c.municipio) == par
        ]
        # Concurso em pe vale mais que o ultimo publicado: uma noticia de
        # ontem sobre a edicao encerrada nao pode esconder a inscricao aberta.
        # Dentro de cada grupo continua valendo a ordem da consulta.
        atual = next(
            (c for c in dessa if c.situacao != "encerrado"),
            dessa[0] if dessa else None,
        )
        cartoes.append(DeOlho(
            cargo=pedida["cargo"],
            cidade=pedida["cidade"],
            situacao=atual.situacao if atual else None,
            titulo=atual.titulo if atual else None,
            url=atual.url if atual else None,
            inscricoes_ate=atual.inscricoes_ate if atual else None,
        ))
    return cartoes


def _sinais(s, concursos: list[Concurso], limite: int) -> list[dict]:
    """O que mexeu ultimamente: eventos gravados e noticias do alvo.

    Os dois juntos porque respondem a mesma pergunta por caminhos diferentes.
    O evento e o que o radar VIU mudar; a noticia e o que alguem escreveu. Uma
    noticia de "governo autoriza" chega antes de qualquer campo mudar.
    """
    urls = {c.url for c in concursos}
    if not urls:
        return []

    titulos = {c.url: c.titulo for c in concursos}
    sinais = [
        {
            "quando": e.data,
            "tipo": e.tipo,
            "texto": e.descricao,
            "link": e.link or e.concurso_url,
            "de": titulos.get(e.concurso_url, ""),
        }
        for e in s.scalars(
            select(Evento)
            .where(Evento.concurso_url.in_(urls))
            .order_by(Evento.data.desc(), Evento.id.desc())
            .limit(limite)
        )
    ]

    # A noticia entra pelo que ela e: um texto publicado numa data. Ela nao
    # vira evento no banco porque nao houve mudanca de campo nenhuma.
    for concurso in concursos:
        if concurso.tipo == "noticia" and concurso.publicado_em:
            sinais.append({
                "quando": concurso.publicado_em,
                "tipo": "noticia",
                "texto": concurso.titulo,
                "link": concurso.url,
                "de": "",
            })

    sinais.sort(key=lambda x: x["quando"], reverse=True)
    return sinais[:limite]


# --- o edital ---------------------------------------------------------------
#
# O PDF do edital de 2019 tem 30 paginas e leva dois segundos para ser lido -
# e a tela precisava dele DUAS vezes, uma para o quadro de materias e outra
# para a validade. Agora ele e lido uma vez so, e o que saiu de la fica
# guardado em disco: edital publicado nao se reescreve, entao mesmo arquivo e
# mesma resposta. Quem diz se o arquivo continua o mesmo e o sha256 que o
# manifesto ja guarda - trocou o PDF, muda o hash, e a leitura acontece de
# novo.


@dataclass
class EditalLido:
    """O que o PDF do edital respondeu. Campo vazio = o edital nao diz."""

    materias: list = field(default_factory=list)
    total: int = 0
    ano: int | None = None
    validade: str | None = None
    #: {materia: [assunto que o edital promete cobrar, ...]}. E o que o
    #: `radar assuntos --so-alvo` deixa a IA escolher, para ela nunca
    #: inventar nome de assunto.
    programa: dict = field(default_factory=dict)


ARQUIVO_DO_EDITAL_LIDO = "edital_do_alvo.json"


def _registro_do_edital(concurso_url: str) -> dict | None:
    """O edital de abertura daquele concurso, como o manifesto o registra.

    Quando ha varios - o de abertura mais os termos aditivos - vale o de
    abertura, que e o unico que traz o quadro de materias. Ele e o de nome
    mais curto: "2019_SAP_Edital_1.pdf" contra "TA_5_ed_1.pdf"... nao serve.
    Vale o que NAO tem marca de retificacao no nome.
    """
    candidatos = [
        r for r in provas.carregar_manifesto()
        if r.get("tipo") == provas.EDITAL
        and r.get("concurso_url") == concurso_url
        and r.get("caminho")
    ]
    if not candidatos:
        return None

    def e_aditivo(registro) -> bool:
        nome = (registro.get("arquivo") or "").lower()
        return any(m in nome for m in ("ta_", "aditivo", "retifica", "errata"))

    abertura = [r for r in candidatos if not e_aditivo(r)] or candidatos
    return abertura[0]


def _ler_edital(concurso: Concurso | None) -> EditalLido:
    """O quadro de materias e a validade do edital daquela edicao.

    Le o PDF que `radar provas` ja baixou - nao vai a internet - e so abre o
    arquivo quando o que esta guardado nao serve mais. Devolve campos vazios
    quando o edital nao esta no acervo ou nao tem quadro legivel: a tela diz
    "nao sei ainda", e nunca um peso inventado.
    """
    if concurso is None:
        return EditalLido()

    registro = _registro_do_edital(concurso.url)
    if registro is None:
        return EditalLido()

    ano = _ano(concurso)
    guardado = _edital_guardado(registro.get("sha256"))
    if guardado is not None:
        guardado.ano = ano
        return guardado

    caminho = config.diretorio_dados() / registro["caminho"]
    if not caminho.exists():
        return EditalLido(ano=ano)

    try:
        texto = extrair_texto(caminho)
    except Exception as erro:  # noqa: BLE001 - PDF ilegivel e possivel
        log.warning("nao li o edital %s (%s)", caminho, type(erro).__name__)
        return EditalLido(ano=ano)

    materias = edital_materias.ler_quadro(texto)
    lido = EditalLido(
        materias=materias,
        total=edital_materias.total_de_questoes(materias),
        ano=ano,
        validade=_validade_no_texto(texto),
        # O anexo de programas e lido do MESMO arquivo, e por isso entra
        # aqui: e mais uma pergunta respondida pela unica abertura do PDF.
        # Ele exige o outro modo de extracao, entao vai pelo caminho proprio.
        programa=edital_programa.ler_programa_do_pdf(caminho),
    )
    _guardar_edital(registro, lido)
    return lido


def programa_do_alvo() -> dict[str, list[str]]:
    """{materia: [assunto que o edital promete cobrar]} da ultima edicao.

    E a lista que o `radar assuntos --so-alvo` entrega para a IA escolher.
    Sem ela a classificacao paga inventava o nome do assunto, e o nome
    inventado nao se encontra com nada: o edital diz "Regras minimas da ONU
    para o tratamento de pessoas presas", e nenhum modelo chega nessa
    formulacao sozinho.

    Devolve {} quando nao ha edital no acervo - e quem chama nao classifica,
    em vez de deixar a IA escolher por conta propria.
    """
    criar_tabelas()
    with sessao() as s:
        concursos = _concursos_do_alvo(s)
    return _ler_edital(_edital_com_prova(concursos)).programa


def _caminho_do_edital_lido() -> Path:
    return config.diretorio_dados() / ARQUIVO_DO_EDITAL_LIDO


def _edital_guardado(sha256: str | None) -> EditalLido | None:
    """O que ja foi lido deste MESMO arquivo, ou None quando nao serve.

    A chave e o sha256 do PDF, e nao o nome nem a data da leitura: uma
    retificacao que troque o arquivo tem hash novo, e ai o que esta guardado
    fala de um edital que nao existe mais.

    Arquivo corrompido, ou escrito por uma versao antiga do programa, nao
    quebra a tela: vale como "nao tenho", e o PDF e lido de novo.
    """
    arquivo = _caminho_do_edital_lido()
    if not sha256 or not arquivo.exists():
        return None

    try:
        guardado = json.loads(arquivo.read_text(encoding="utf-8"))
        if guardado.get("sha256") != sha256:
            return None
        # Guardado por uma versao que ainda nao lia o anexo de programas: o
        # PDF e o mesmo, mas a resposta que eu preciso nao esta ali. Edital
        # sem programa nenhum grava `{}`, entao a chave existir ja diz que a
        # leitura foi feita.
        if "programa" not in guardado:
            return None
        materias = [
            edital_materias.MateriaDoEdital(nome=m["nome"], questoes=m["questoes"])
            for m in guardado.get("materias") or []
        ]
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as erro:
        log.warning("nao aproveitei %s (%s)", arquivo.name, type(erro).__name__)
        return None

    return EditalLido(
        materias=materias,
        # Somado agora, e nao guardado: um total que discordasse das materias
        # seria numero orfao, e o quadro so vale quando fecha a conta.
        total=edital_materias.total_de_questoes(materias),
        validade=guardado.get("validade"),
        programa=guardado.get("programa") or {},
    )


def _guardar_edital(registro: dict, lido: EditalLido) -> None:
    """Escreve o que foi lido, para a proxima abertura nao reabrir o PDF.

    Sem sha256 no manifesto nao ha como conferir depois se o arquivo continua
    o mesmo - e guardar o que nao da para conferir e o mesmo que chutar.
    """
    if not registro.get("sha256"):
        return

    conteudo = {
        "sha256": registro["sha256"],
        # So para eu abrir este arquivo e saber de que edital ele fala.
        "arquivo": registro.get("arquivo"),
        "materias": [
            {"nome": m.nome, "questoes": m.questoes} for m in lido.materias
        ],
        "validade": lido.validade,
        "programa": lido.programa,
    }
    try:
        _caminho_do_edital_lido().write_text(
            json.dumps(conteudo, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError as erro:  # noqa: BLE001 - disco cheio nao pode apagar a tela
        log.warning("nao guardei o edital lido (%s)", type(erro).__name__)


# O texto da validade e copiado do edital, e nao resumido: "2 anos" sem o "a
# contar da homologacao" seria meia verdade, e a homologacao e justamente a
# data que eu nao tenho.
VALIDADE_NO_EDITAL = re.compile(
    r"(?i)valida?de\s+de\s+(\d+)\s*\(\s*\w+\s*\)\s*anos?"
    r"(?:[^.]{0,200}?prorrogad[ao]\s+por\s+igual\s+per[ií]odo)?",
    re.DOTALL,
)


def _validade_no_texto(texto: str) -> str | None:
    """O prazo de validade, como o edital escreve.

    Devolve None quando o edital nao diz. Note que saber o PRAZO nao e saber
    ate quando: ele conta da homologacao do resultado, publicada no Diario
    Oficial do Estado - que este projeto nao le, por causa do robots.txt.
    """
    achado = VALIDADE_NO_EDITAL.search(texto or "")
    if not achado:
        return None

    anos = int(achado.group(1))
    prorroga = "prorrogad" in achado.group(0).lower()
    frase = f"{anos} anos a contar da homologação do resultado"
    if prorroga:
        frase += f", prorrogáveis por mais {anos}"
    return frase


def _provas_do_alvo(s) -> set[str]:
    """O endereco dos cadernos do acervo que sao a MINHA prova.

    Duas perguntas, e as duas precisam de sim. **E o meu cargo?** - com a
    lista `exclui` valendo, senao "Policial Penal Federal" entra. **E do meu
    estado?** - o cargo sozinho nao diz: "Policia Penal do Parana" e o mesmo
    cargo e outro concurso, com outra banca e outro programa. Quem sabe a UF e
    o concurso que originou a prova, e e por isso que a consulta o alcanca.

    Prova que nao chega a um concurso conhecido fica de fora: sem ele nao ha
    como provar o estado, e contar assim mesmo seria chutar - a mesma regra do
    anel de distancia.

    Existe tambem por causa do tempo de abertura da tela: cada conta daqui
    varria as 8 mil questoes do acervo inteiro, em Python, para ficar com as
    170 que sao minhas - e eram tres varreduras por abertura. Aqui a pergunta
    e feita UMA vez, sobre as ~200 provas distintas, e o resto do arquivo
    consulta o banco so por elas.
    """
    linhas = s.execute(
        select(
            QuestaoDeProva.prova_url,
            QuestaoDeProva.cargo,
            Concurso.uf,
            Concurso.titulo,
            Concurso.resumo,
        )
        .join(Concurso, Concurso.url == QuestaoDeProva.concurso_url, isouter=True)
        .distinct()
    ).all()

    return {
        url for url, cargo, uf, titulo, resumo in linhas
        if _e_do_cargo(cargo)
        and alvos.e_do_estado_do_principal(uf, titulo, resumo)
    }


def _incidencia_do_cargo(s, provas_do_alvo: set[str]) -> tuple[dict, list[int]]:
    """Quantas questoes de cada materia, por ano, nas provas do alvo.

    E o contraponto do quadro do edital: o edital diz o que promete cobrar, e
    isto diz o que caiu de verdade.
    """
    if not provas_do_alvo:
        return {}, []

    linhas = s.execute(
        select(QuestaoDeProva.materia, QuestaoDeProva.ano, func.count())
        .where(QuestaoDeProva.prova_url.in_(provas_do_alvo))
        .where(QuestaoDeProva.materia.is_not(None))
        .where(QuestaoDeProva.ano.is_not(None))
        # Questao anulada nao conta: a banca disse que ela nao existe. O
        # `is_not(True)` e por causa das linhas antigas, que ficaram com nulo
        # ate a coluna nova ser preenchida.
        .where(QuestaoDeProva.anulada.is_not(True))
        .group_by(QuestaoDeProva.materia, QuestaoDeProva.ano)
    ).all()

    por_materia: dict[str, dict[int, int]] = {}
    anos: set[int] = set()
    for materia, ano, quantas in linhas:
        anos.add(ano)
        por_materia.setdefault(materia, {})[ano] = quantas

    return por_materia, sorted(anos)


def materias_de_maior_peso(materias: list, total: int) -> set[str]:
    """As materias que puxam mais nota que a media, pelo quadro do edital.

    O corte e a media da propria prova (total dividido pelo numero de
    materias), e nao um numero que eu escolhi. Ele se ajusta sozinho quando o
    edital muda, e e o que separa "materia que decide a prova" de "materia que
    tem duas questoes".

    No edital de 2019 sao sete: as duas de 15 questoes e as cinco de 10, que
    juntas valem 80 das 100 questoes. As quatro de 5 questoes ficam de fora.
    """
    if not materias or not total:
        return set()

    media = total / len(materias)
    return {m.nome for m in materias if m.questoes >= media}


def _acerto_por_materia(materias: list) -> dict:
    """Quanto eu acerto em cada materia do edital, pelo nome que ele usa.

    Vem do simulado - de TODOS os simulados, nao so do ultimo: uma rodada de
    20 questoes nao diz se eu sei a materia, e o acumulado diz.

    A chave e o nome do edital porque e ele que manda na tela, e os dois lados
    escrevem diferente: o edital diz "Lingua Portuguesa" e o cabecalho do
    caderno pode dizer "Língua Portuguesa". Comparar normalizado resolve isso
    sem precisar de tabela de apelidos.

    Materia que eu nunca respondi simplesmente nao esta no dicionario. Ela nao
    vale zero por cento: zero seria dizer que eu errei tudo, quando o que
    aconteceu foi eu nao ter treinado.
    """
    from radar import servico

    medido = {
        normalizar(d.materia): d for d in servico.desempenho() if d.respondidas
    }
    return {
        m.nome: medido[normalizar(m.nome)]
        for m in materias
        if normalizar(m.nome) in medido
    }


def _pior_das_pesadas(pesadas: set[str], acerto: dict) -> str | None:
    """A materia de maior peso em que eu vou pior. None se nenhuma foi feita.

    E a resposta para "por onde eu comeco a estudar hoje": errar muito numa
    materia de 2 questoes custa 2 questoes; errar numa de 15 decide a prova.

    So entra materia que eu ja treinei. Apontar a pior entre as que eu nunca
    fiz seria inventar um numero - e a materia pesada que ainda nao tem acerto
    aparece na tela do jeito dela, dizendo que falta treinar.
    """
    medidas = [(nome, acerto[nome]) for nome in pesadas if nome in acerto]
    if not medidas:
        return None

    # Empate de porcentagem desempata pela materia mais feita: entre 50% em
    # duas questoes e 50% em trinta, a segunda e a que eu sei que e verdade.
    pior = min(medidas, key=lambda par: (par[1].porcentagem, -par[1].respondidas))
    return pior[0]


def _contar_questoes_do_alvo(s, provas_do_alvo: set[str]) -> int:
    """Quantas questoes do cargo existem para treinar."""
    if not provas_do_alvo:
        return 0

    return s.scalar(
        select(func.count())
        .select_from(QuestaoDeProva)
        .where(QuestaoDeProva.prova_url.in_(provas_do_alvo))
        # Anulada nao da para treinar: ela ficou sem resposta certa.
        .where(QuestaoDeProva.anulada.is_not(True))
    ) or 0


# --- onde estudar primeiro --------------------------------------------------
#
# A tabela de materias diz qual materia pesa mais. Esta parte desce um andar:
# dentro da materia, QUAL ASSUNTO. "Estudar Direitos Humanos" nao e um plano de
# tarde; "estudar as Regras de Mandela" e.
#
# O assunto vem de dois lugares, e a tela diz qual e qual porque um custou
# dinheiro e o outro nao:
#
#   * CATALOGO - Portugues e Raciocinio Logico saem do catalogo de
#     palavras-chave do `macetes`, de graca, e ja funcionam hoje;
#   * EDITAL - as outras nove materias saem da coluna `assunto`, escolhida
#     dentro do conteudo programatico pelo `radar assuntos --so-alvo`. Sem
#     rodar esse comando elas nao aparecem aqui, e a tela diz isso.
#
# Sao so DUAS provas do cargo, e duas provas nao sustentam uma fatia. Por isso
# entra o reforco: a mesma banca, nas MESMAS materias, em outros concursos - a
# FEPESE cobra crase do mesmo jeito em qualquer caderno que faca. A tela separa
# os dois numeros sempre, porque eles nao valem a mesma coisa.


def _materias_do_acervo_no_edital(s, materias_do_edital: list) -> dict[str, str]:
    """{nome como a prova escreve: nome como o EDITAL escreve}.

    Os dois lados escrevem diferente - o edital diz "Lei de Execucao Penal" e o
    cabecalho do caderno pode dizer "LEI DE EXECUCAO PENAL" - e a conta so
    fecha quando os dois viram a mesma chave. O nome que vale e o do edital,
    porque e dele que sai o peso.

    Materia que o edital de hoje nao lista fica de fora de proposito: 2013
    cobrou Nocoes de Informatica e 2019 nao cobra, e questao dela nao tem peso
    nenhum para multiplicar.
    """
    do_edital = {normalizar(m.nome): m.nome for m in materias_do_edital}
    if not do_edital:
        return {}

    nomes = s.scalars(
        select(QuestaoDeProva.materia)
        .where(QuestaoDeProva.materia.is_not(None))
        .distinct()
    )
    return {
        nome: do_edital[normalizar(nome)]
        for nome in nomes
        if normalizar(nome) in do_edital
    }


def _questoes_para_a_fatia(s, minhas_provas: set[str], nomes: list[str]) -> list:
    """As questoes que sustentam a fatia de cada assunto: as minhas e o reforco.

    O reforco e a mesma banca nas mesmas materias, em outros concursos. Nao e a
    mesma coisa que a minha prova, e a tela nunca finge que e - mas centenas de
    enunciados dizem do costume da banca o que 170 nao dizem.
    """
    if not nomes:
        return []

    bancas = [normalizar(b) for b in alvos.bancas_do_principal()]
    questoes = s.scalars(
        select(QuestaoDeProva)
        .where(QuestaoDeProva.materia.in_(nomes))
        # Anulada nao entra em conta nenhuma: a banca disse que ela nao existe.
        .where(QuestaoDeProva.anulada.is_not(True))
    )
    return [
        q for q in questoes
        if q.prova_url in minhas_provas
        or any(banca in normalizar(q.banca or "") for banca in bancas)
    ]


def _marcas_de_assunto(
    questoes: list, chave: str | None
) -> tuple[list[tuple[str, int]], int]:
    """([(assunto, em quantos enunciados distintos ele cai)], quantos sem assunto).

    Em enunciado distinto, e nao em questao, dos dois lados da conta. O reforco
    vem de duzias de cadernos, e la a banca reaproveita muito: uma questao que
    aparece em 38 provas decidiria o grafico sozinha. E o mesmo motivo que fez
    o `macetes.uma_por_enunciado` existir.

    A conta dos "sem assunto" sai junto, e nao numa segunda passada, porque ela
    custa o mesmo trabalho: sao 18 expressoes regulares sobre cada enunciado, e
    rodar tudo duas vezes botava meio segundo na abertura da home.
    """
    unicas = macetes.uma_por_enunciado(questoes)
    if chave:
        achados, fora = macetes.assuntos_de(unicas, chave)
        return [(a.nome, a.distintas) for a in achados], fora

    marcas: dict[str, int] = {}
    fora = 0
    for questao in unicas:
        if questao.assunto:
            marcas[questao.assunto] = marcas.get(questao.assunto, 0) + 1
        else:
            fora += 1
    return list(marcas.items()), fora


def _contagens_de_assunto(
    questoes: list, para_o_edital: dict[str, str], minhas_provas: set[str]
) -> tuple[dict, dict, int]:
    """({(materia, assunto): (proprias, reforco)}, {materia: origem}, sem assunto)."""
    por_materia: dict[str, list] = {}
    for questao in questoes:
        por_materia.setdefault(para_o_edital[questao.materia], []).append(questao)

    contagens: dict[tuple[str, str], list[int]] = {}
    origens: dict[str, str] = {}
    sem_assunto = 0

    for materia, lista in por_materia.items():
        chave = macetes.chave_da_materia(materia)
        origens[materia] = onde_estudar.CATALOGO if chave else onde_estudar.EDITAL

        minhas = [q for q in lista if q.prova_url in minhas_provas]
        reforco = [q for q in lista if q.prova_url not in minhas_provas]

        for coluna, grupo in ((0, minhas), (1, reforco)):
            marcas, fora = _marcas_de_assunto(grupo, chave)
            for nome, quantas in marcas:
                contagens.setdefault((materia, nome), [0, 0])[coluna] += quantas
            # So as MINHAS contam como "falta classificar": o reforco esta la
            # para sustentar a fatia, e nao para eu estudar por ele.
            if coluna == 0:
                sem_assunto += fora

    return (
        {par: (proprias, reforco) for par, (proprias, reforco) in contagens.items()},
        origens,
        sem_assunto,
    )


def _acerto_por_assunto(s, para_o_edital: dict[str, str]) -> dict:
    """{(materia, assunto): (respondidas, acertos)}, de TODOS os simulados.

    Do acumulado e nao do ultimo, pelo mesmo motivo do acerto por materia: uma
    rodada de 20 questoes nao diz se eu sei o assunto, e o somado diz.

    Assunto nunca respondido simplesmente nao esta no dicionario. Ele nao vale
    zero por cento - zero diria que eu errei tudo.
    """
    if not para_o_edital:
        return {}

    linhas = s.execute(
        select(QuestaoDeProva, RespostaDeSimulado.acertou)
        .join(RespostaDeSimulado, RespostaDeSimulado.questao_id == QuestaoDeProva.id)
        .where(RespostaDeSimulado.escolhida.is_not(None))
        .where(QuestaoDeProva.materia.in_(list(para_o_edital)))
    ).all()

    medido: dict[tuple[str, str], list[int]] = {}
    for questao, acertou in linhas:
        materia = para_o_edital[questao.materia]
        chave = macetes.chave_da_materia(materia)
        if chave:
            nomes = macetes.assuntos_do_enunciado(questao.enunciado, chave)
        else:
            nomes = [questao.assunto] if questao.assunto else []

        for nome in nomes:
            conta = medido.setdefault((materia, nome), [0, 0])
            conta[0] += 1
            conta[1] += 1 if acertou else 0

    return {par: (feitas, certas) for par, (feitas, certas) in medido.items()}


def _onde_comecar(s, minhas_provas: set[str], materias_do_edital: list):
    """(linhas do grafico, questoes sem assunto, materias sem assunto nenhum).

    Lista vazia quando nenhum assunto foi detectado: a tela diz que falta
    classificar, e nao inventa uma ordem de estudo em cima de nada.
    """
    para_o_edital = _materias_do_acervo_no_edital(s, materias_do_edital)
    questoes = _questoes_para_a_fatia(s, minhas_provas, list(para_o_edital))
    if not questoes:
        return [], 0, list(materias_do_edital)

    contagens, origens, sem_assunto = _contagens_de_assunto(
        questoes, para_o_edital, minhas_provas
    )
    linhas = onde_estudar.montar(
        materias_do_edital,
        contagens,
        _acerto_por_assunto(s, para_o_edital),
        origens,
    )

    # A materia que nao rendeu nenhum assunto nao pode so sumir do grafico.
    # Ela cai no edital valendo questao, e sumir diria "nao cai" - quando o
    # que aconteceu foi eu nao ter classificado nada dela.
    com_assunto = {materia for materia, _assunto in contagens}
    mudas = [m for m in materias_do_edital if m.nome not in com_assunto]
    return linhas, sem_assunto, mudas


def montar() -> Painel:
    """O painel inteiro. Campo vazio quer dizer "nao sei ainda"."""
    criar_tabelas()

    principal = alvos.principal()
    if not principal:
        return Painel(configurado=False)

    painel = Painel(nome_do_alvo=principal.get("nome") or "alvo principal")

    with sessao() as s:
        concursos = _concursos_do_alvo(s)
        painel.sinais = _sinais(s, concursos, SINAIS_NA_TELA)
        painel.de_olho = _de_olho(s)

        # As provas do cargo sao a base de tres contas da tela. Perguntar uma
        # vez, e na mesma sessao, e o que faz a tela abrir rapido.
        minhas_provas = _provas_do_alvo(s)
        painel.banca = _banca_do_alvo(s, concursos, minhas_provas)
        painel.incidencia, painel.anos_das_provas = _incidencia_do_cargo(
            s, minhas_provas
        )
        painel.questoes_para_treinar = _contar_questoes_do_alvo(s, minhas_provas)

    abertos = [c for c in concursos if c.situacao in SITUACOES_ABERTAS]
    do_cargo = [
        c for c in abertos
        if alvos.nomeia_cargo_do_principal(c.titulo, c.resumo)
    ]
    if do_cargo:
        painel.aberto = _como_edicao(do_cargo[0])
    elif abertos:
        # Ha inscricao aberta na secretaria, mas para outro cargo. Isso e
        # noticia - a casa esta contratando - sem ser o meu concurso.
        painel.aberto_no_orgao = _como_edicao(abertos[0])

    ultimo = _edital_com_prova(concursos)
    if ultimo:
        painel.ultima = _como_edicao(ultimo)

    edital = _ler_edital(ultimo)
    materias = edital.materias
    painel.materias_do_edital = materias
    painel.total_do_edital = edital.total
    painel.ano_do_edital = edital.ano

    # A validade so e afirmada junto com o quadro: quadro ilegivel quer dizer
    # que o PDF nao foi lido direito, e ai o prazo tambem nao vale.
    if materias:
        painel.validade = edital.validade

    # O quadro do edital diz o que vale mais; o simulado diz como eu vou. Os
    # dois juntos respondem a pergunta que o quadro sozinho nao responde: por
    # onde comecar hoje.
    painel.acerto_por_materia = _acerto_por_materia(materias)
    painel.materias_pesadas = materias_de_maior_peso(materias, edital.total)
    painel.pior_materia = _pior_das_pesadas(
        painel.materias_pesadas, painel.acerto_por_materia
    )

    # Sessao nova, e nao a de cima, porque esta parte so existe depois do
    # edital lido: e o peso de cada materia que transforma "fatia do assunto"
    # em "questoes esperadas", e o edital sai de um PDF, nao do banco. O que
    # ela reaproveita e o `minhas_provas`, que ja e so um punhado de enderecos.
    if materias:
        with sessao() as s:
            linhas, sem_assunto, mudas = _onde_comecar(s, minhas_provas, materias)
        painel.onde_comecar = linhas[:onde_estudar.NA_TELA]
        painel.assuntos_fora_da_tela = max(0, len(linhas) - onde_estudar.NA_TELA)
        painel.conclusao_do_estudo = onde_estudar.conclusao(linhas)
        painel.questoes_sem_assunto = sem_assunto
        # Da maior para a menor: se so uma materia vai ser classificada, que
        # seja a que mais vale na prova.
        painel.materias_sem_assunto = sorted(
            mudas, key=lambda m: -(m.questoes or 0)
        )

    return painel


# O botao de treino nao escolhe mais um termo de cargo para filtrar: quem
# monta a rodada e `servico.criar_simulado_do_alvo`, que trata os termos do
# YAML como a lista de nomes do mesmo cargo - e nao como filtros concorrentes.
