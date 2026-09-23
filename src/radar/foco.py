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
import logging
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import select

from radar import alvo as alvos
from radar import edital_materias, provas
from radar.db import criar_tabelas, sessao
from radar.eventos import Evento
from radar.models import Concurso, QuestaoDeProva, agora
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
            return "nao sei ainda"
        if self.confirmada:
            return self.nome
        if self.anos:
            anos = " e ".join(str(a) for a in self.anos)
            return f"hipotese: {self.nome}, que fez {anos}"
        return f"hipotese: {self.nome}"


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
    import re

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


def _banca_do_alvo(concursos: list[Concurso]) -> Banca:
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
    anos = _anos_com_prova(nomes[0])
    return Banca(nome=nomes[0], confirmada=False, anos=anos)


def _e_do_cargo(cargo: str | None) -> bool:
    """Esta questao e de uma prova do cargo que eu quero?

    A comparacao e feita em Python, e nao no SQL, por causa do acento: o LIKE
    do SQLite ignora maiuscula mas NAO ignora acento, e o cargo gravado e
    "Agente Penitenciario" com acento enquanto o termo do YAML vem sem. Com
    ilike, as 170 questoes do cargo davam zero.
    """
    if not cargo:
        return False
    alvo_do_texto = normalizar(cargo)
    return any(
        normalizar(termo) in alvo_do_texto
        for termo in alvos.termos_do_principal()
    )


def _anos_com_prova(banca: str) -> list[int]:
    """Em que anos essa banca deixou prova do CARGO no acervo.

    Do cargo, e nao da banca: a FEPESE deixou prova de dezenas de concursos,
    e so as do meu cargo contam como "ja fez este aqui".
    """
    with sessao() as s:
        linhas = s.execute(
            select(QuestaoDeProva.cargo, QuestaoDeProva.ano, QuestaoDeProva.banca)
            .distinct()
        ).all()

    alvo_banca = normalizar(banca)
    return sorted({
        ano for cargo, ano, banca_da_prova in linhas
        if ano and _e_do_cargo(cargo)
        and alvo_banca in normalizar(banca_da_prova or "")
    })


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


def _materias_do_ultimo_edital(concurso: Concurso | None) -> tuple[list, int, int | None]:
    """O quadro de distribuicao de questoes do edital daquela edicao.

    Le o PDF que `radar provas` ja baixou - nao vai a internet. Devolve lista
    vazia quando o edital nao esta no acervo ou nao tem quadro legivel.
    """
    if concurso is None:
        return [], 0, None

    caminho = _caminho_do_edital(concurso.url)
    if caminho is None:
        return [], 0, None

    try:
        texto = extrair_texto(caminho)
    except Exception as erro:  # noqa: BLE001 - PDF ilegivel e possivel
        log.warning("nao li o edital %s (%s)", caminho, type(erro).__name__)
        return [], 0, None

    materias = edital_materias.ler_quadro(texto)
    return materias, edital_materias.total_de_questoes(materias), _ano(concurso)


def _caminho_do_edital(concurso_url: str):
    """O PDF de edital daquele concurso que esta no disco.

    Quando ha varios - o de abertura mais os termos aditivos - vale o de
    abertura, que e o unico que traz o quadro de materias. Ele e o de nome
    mais curto: "2019_SAP_Edital_1.pdf" contra "TA_5_ed_1.pdf"... nao serve.
    Vale o que NAO tem marca de retificacao no nome.
    """
    from radar import config

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
    caminho = config.diretorio_dados() / abertura[0]["caminho"]
    return caminho if caminho.exists() else None


def _incidencia_do_cargo() -> tuple[dict, list[int]]:
    """Quantas questoes de cada materia, por ano, nas provas do alvo.

    E o contraponto do quadro do edital: o edital diz o que promete cobrar, e
    isto diz o que caiu de verdade.
    """
    por_materia: dict[str, dict[int, int]] = {}
    anos: set[int] = set()

    with sessao() as s:
        linhas = s.execute(
            select(QuestaoDeProva.cargo, QuestaoDeProva.materia, QuestaoDeProva.ano)
        ).all()

    for cargo, materia, ano in linhas:
        if not materia or not ano or not _e_do_cargo(cargo):
            continue
        anos.add(ano)
        por_materia.setdefault(materia, {}).setdefault(ano, 0)
        por_materia[materia][ano] += 1

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


def _contar_questoes_do_alvo() -> int:
    """Quantas questoes do cargo existem para treinar."""
    with sessao() as s:
        linhas = s.execute(
            select(QuestaoDeProva.id, QuestaoDeProva.cargo)
        ).all()
    return sum(1 for _ident, cargo in linhas if _e_do_cargo(cargo))


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

    painel.banca = _banca_do_alvo(concursos)

    materias, total, ano = _materias_do_ultimo_edital(ultimo)
    painel.materias_do_edital = materias
    painel.total_do_edital = total
    painel.ano_do_edital = ano

    if materias:
        painel.validade = _validade_do_edital(ultimo)

    painel.incidencia, painel.anos_das_provas = _incidencia_do_cargo()
    painel.questoes_para_treinar = _contar_questoes_do_alvo()

    # O quadro do edital diz o que vale mais; o simulado diz como eu vou. Os
    # dois juntos respondem a pergunta que o quadro sozinho nao responde: por
    # onde comecar hoje.
    painel.acerto_por_materia = _acerto_por_materia(materias)
    painel.materias_pesadas = materias_de_maior_peso(materias, total)
    painel.pior_materia = _pior_das_pesadas(
        painel.materias_pesadas, painel.acerto_por_materia
    )
    return painel


# O texto da validade e copiado do edital, e nao resumido: "2 anos" sem o "a
# contar da homologacao" seria meia verdade, e a homologacao e justamente a
# data que eu nao tenho.
import re as _re  # noqa: E402 - usado so pela funcao abaixo

VALIDADE_NO_EDITAL = _re.compile(
    r"(?i)valida?de\s+de\s+(\d+)\s*\(\s*\w+\s*\)\s*anos?"
    r"(?:[^.]{0,200}?prorrogad[ao]\s+por\s+igual\s+per[ií]odo)?",
    _re.DOTALL,
)


def _validade_do_edital(concurso: Concurso) -> str | None:
    """O prazo de validade, como o edital escreve.

    Devolve None quando o edital nao diz. Note que saber o PRAZO nao e saber
    ate quando: ele conta da homologacao do resultado, publicada no Diario
    Oficial do Estado - que este projeto nao le, por causa do robots.txt.
    """
    caminho = _caminho_do_edital(concurso.url)
    if caminho is None:
        return None

    try:
        texto = extrair_texto(caminho)
    except Exception:  # noqa: BLE001
        return None

    achado = VALIDADE_NO_EDITAL.search(texto)
    if not achado:
        return None

    anos = int(achado.group(1))
    prorroga = "prorrogad" in achado.group(0).lower()
    frase = f"{anos} anos a contar da homologacao do resultado"
    if prorroga:
        frase += f", prorrogaveis por mais {anos}"
    return frase


# O botao de treino nao escolhe mais um termo de cargo para filtrar: quem
# monta a rodada e `servico.criar_simulado_do_alvo`, que trata os termos do
# YAML como a lista de nomes do mesmo cargo - e nao como filtros concorrentes.
