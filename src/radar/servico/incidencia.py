"""O mapa de incidencia do alvo a partir do banco. A conta mora no
`radar.incidencia`, que e puro; aqui so se junta o que ele precisa."""
from sqlalchemy import select

from radar import conteudos as arvore
from radar import incidencia
from radar.db import criar_tabelas, sessao
from radar.models import Classificacao, Conteudo, QuestaoDeProva
from radar.regioes import normalizar
from radar.servico import conteudos, evidencia
from radar.servico.classificacoes import chave_de


def _materia_do_caderno(caminhos: list[str], taxonomia):
    """f(nome da materia no caderno) -> no da materia, lembrando o que ja achou.

    Sao milhares de questoes e uns vinte nomes de materia: procurar o mesmo
    nome na arvore a cada questao era o que deixava a leitura do complementar
    em segundos (o `arvore.achar` normaliza cada caminho a cada chamada). O
    resultado e o mesmo de antes, so que perguntado uma vez por nome.
    """
    achados: dict[str | None, str | None] = {}

    def achar(nome: str | None) -> str | None:
        if nome not in achados:
            achados[nome] = (arvore.achar(caminhos, nome)
                             or arvore.achar(caminhos, taxonomia.materia_do_texto(nome)))
        return achados[nome]

    return achar


def ocorrencias() -> list[incidencia.Ocorrencia]:
    """Uma por questao do ALVO, com a classificacao principal dela.

    A materia em que a questao conta e a da classificacao (a de 2013 que foi
    para um assunto de 2019 conta em 2019); sem classificacao, a do caderno.
    """
    taxonomia = arvore.carregar_taxonomia()
    criar_tabelas()
    with sessao() as s:
        caminhos = list(s.scalars(select(Conteudo.caminho)))
        principais = {c.chave: c for c in s.scalars(
            select(Classificacao).where(Classificacao.principal.is_(True)))}
        # Os conceitos associados (§14, item 7): os outros nos da questao.
        associados: dict[str, list] = {}
        for c in s.scalars(select(Classificacao)
                           .where(Classificacao.principal.is_(False))
                           .where(Classificacao.status != "pendente")):
            associados.setdefault(c.chave, []).append(c.conteudo)
        questoes = list(s.scalars(
            select(QuestaoDeProva).where(QuestaoDeProva.evidencia == evidencia.ALVO)))

    do_caderno = _materia_do_caderno(caminhos, taxonomia)
    resultado = []
    for q in questoes:
        chave = chave_de(q)
        c = principais.get(chave)
        resultado.append(incidencia.Ocorrencia(
            prova=q.prova_url, ano=q.ano,
            materia=arvore.partes(c.conteudo)[0] if c else do_caderno(q.materia),
            conteudo=c.conteudo if c else None,
            status=c.status if c else "pendente",
            anulada=bool(q.anulada),
            tipo_de_questao=c.tipo_de_questao if c else None,
            pegadinha=c.pegadinha if c else None,
            enunciado=q.enunciado or "", resposta=q.resposta, impressao=chave,
            numero=q.numero, conferida=bool(c and c.conferida_em),
            associados=tuple(sorted(associados.get(chave, [])))))
    return resultado


def associacoes(mapas: list[incidencia.MapaDaMateria],
                ocorrencias_do_alvo: list | None = None) -> dict:
    """{materia: [Associacao]}: os conceitos que caem juntos nas questoes do
    alvo, para os mapas pedidos (§14, item 7)."""
    if ocorrencias_do_alvo is None:
        ocorrencias_do_alvo = ocorrencias()
    return {m.materia: incidencia.associacoes(ocorrencias_do_alvo, m.materia)
            for m in mapas}


def mapa(materia: str | None = None) -> list[incidencia.MapaDaMateria]:
    mapas = incidencia.montar(conteudos.nos(), ocorrencias())
    if materia:
        # Sem acento e sem caixa, como o `radar desempenho --materia`.
        procurada = normalizar(materia)
        mapas = [m for m in mapas if normalizar(m.materia) == procurada]
    return mapas


def ocorrencias_complementares() -> list[incidencia.Ocorrencia]:
    """Uma por questao das provas ACEITAS no acervo complementar (Etapa 3B).

    Prova que nao esta no `data/acervo_complementar.json` como aceita nao
    entra: validacao reprovada ou lista nao aplicada, a questao fica de fora
    da estatistica, e o relatorio diz por que.

    Sem classificacao, a questao conta na materia que o CADERNO declara - e
    so nela. Nunca num assunto adivinhado.
    """
    from radar.servico import complementar as acervo

    aceitas = acervo.provas_aceitas()
    if not aceitas:
        return []
    taxonomia = arvore.carregar_taxonomia()
    criar_tabelas()
    with sessao() as s:
        caminhos = list(s.scalars(select(Conteudo.caminho)))
        principais = {c.chave: c for c in s.scalars(
            select(Classificacao).where(Classificacao.principal.is_(True)))}
        questoes = list(s.scalars(
            select(QuestaoDeProva)
            .where(QuestaoDeProva.evidencia == evidencia.COMPLEMENTAR,
                   QuestaoDeProva.prova_url.in_(aceitas))))

    do_caderno = _materia_do_caderno(caminhos, taxonomia)
    resultado = []
    for q in questoes:
        chave = chave_de(q)
        c = principais.get(chave)
        conteudo = c.conteudo if c else do_caderno(q.materia)
        if conteudo is None:
            continue              # bloco generico sem classificacao: nao da para contar
        resultado.append(incidencia.Ocorrencia(
            prova=q.prova_url, ano=q.ano, materia=arvore.partes(conteudo)[0],
            conteudo=conteudo, status=c.status if c else "pendente",
            anulada=bool(q.anulada),
            tipo_de_questao=c.tipo_de_questao if c else None,
            pegadinha=c.pegadinha if c else None,
            enunciado=q.enunciado or "", resposta=q.resposta, impressao=chave,
            numero=q.numero, conferida=bool(c and c.conferida_em)))
    return resultado


def linhas_complementares(ocorrencias: list | None = None) -> dict:
    """{caminho do no: LinhaComplementar}. Nunca somada a do alvo.

    `ocorrencias` e para quem ja leu o complementar (a leitura e a parte cara
    da tela) nao ler de novo."""
    if ocorrencias is None:
        ocorrencias = ocorrencias_complementares()
    return incidencia.complementar_por_no(conteudos.nos(), ocorrencias)


def ocorrencias_dos_padroes(ocorrencias: list | None = None) -> list[incidencia.Ocorrencia]:
    """As ocorrencias complementares que entram nos padroes de cobranca: so as
    das provas aceitas com gabarito DEFINITIVO (Etapa 3B, decisao 78)."""
    from radar.servico import complementar as acervo

    das_provas = acervo.provas_dos_padroes()
    if ocorrencias is None:
        ocorrencias = ocorrencias_complementares()
    return [o for o in ocorrencias if o.prova in das_provas]


def padroes_complementares(mapas: list[incidencia.MapaDaMateria],
                           minimos: incidencia.Minimos,
                           ocorrencias: list | None = None) -> dict:
    """{caminho do no: Padroes} do acervo complementar, para as linhas dos
    mapas pedidos. Separados dos do alvo, e nunca somados a eles."""
    dos_padroes = ocorrencias_dos_padroes(ocorrencias)
    return {l.caminho: incidencia.padroes_complementares(l.caminho, dos_padroes, minimos)
            for m in mapas for l in m.linhas}
