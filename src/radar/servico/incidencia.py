"""O mapa de incidencia do alvo a partir do banco. A conta mora no
`radar.incidencia`, que e puro; aqui so se junta o que ele precisa."""
from sqlalchemy import select

from radar import conteudos as arvore
from radar import incidencia
from radar.db import criar_tabelas, sessao
from radar.models import Classificacao, Conteudo, QuestaoDeProva
from radar.servico import conteudos, evidencia
from radar.servico.classificacoes import chave_de


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
        questoes = list(s.scalars(
            select(QuestaoDeProva).where(QuestaoDeProva.evidencia == evidencia.ALVO)))

    resultado = []
    for q in questoes:
        chave = chave_de(q)
        c = principais.get(chave)
        do_caderno = (arvore.achar(caminhos, q.materia)
                      or arvore.achar(caminhos, taxonomia.materia_do_texto(q.materia)))
        resultado.append(incidencia.Ocorrencia(
            prova=q.prova_url, ano=q.ano,
            materia=arvore.partes(c.conteudo)[0] if c else do_caderno,
            conteudo=c.conteudo if c else None,
            status=c.status if c else "pendente",
            anulada=bool(q.anulada),
            tipo_de_questao=c.tipo_de_questao if c else None,
            pegadinha=c.pegadinha if c else None,
            enunciado=q.enunciado or "", resposta=q.resposta, impressao=chave))
    return resultado


def mapa(materia: str | None = None) -> list[incidencia.MapaDaMateria]:
    mapas = incidencia.montar(conteudos.nos(), ocorrencias())
    if materia:
        mapas = [m for m in mapas if m.materia == materia]
    return mapas
