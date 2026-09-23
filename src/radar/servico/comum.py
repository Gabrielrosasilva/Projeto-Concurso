"""Os poucos ajudantes que mais de um assunto do servico usa.

Este arquivo existe para evitar a unica coisa pior que um arquivo de 2.700
linhas: dois arquivos com a mesma funcao copiada dentro. Ele so recebe o que
JA era usado por mais de uma parte - nao e lugar para guardar o que ainda nao
tem casa.
"""
import re

from sqlalchemy import func

from radar.models import Concurso, QuestaoDeProva


def sem_acento(texto: str) -> str:
    import unicodedata

    normal = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in normal if not unicodedata.combining(c))


def cargo_parecido(cargo: str):
    """Condicao SQL de "o cargo da questao parece com este texto".

    Ignora acento pelo mesmo motivo que a busca por titulo ignora: o cargo vem
    acentuado do rotulo do hotsite ("Agente Penitenciario"), e o termo com que
    eu procuro - o de config/alvo.yml, ou o que eu digito na CLI - vem sem.
    Com ilike puro, `--cargo "agente penitenciario"` devolvia zero questao das
    170 que existem.
    """
    return func.sem_acento(QuestaoDeProva.cargo).ilike(f"%{sem_acento(cargo)}%")


def ano_do_concurso(concurso: Concurso) -> int | None:
    """O ano do concurso, do titulo quando ele diz, senao da publicacao.

    O titulo da FEPESE comeca com o ano ("2020 - Prefeitura Municipal de ..."),
    e isso vale mais que a data do post: na migracao do site dela 345 concursos
    antigos ficaram todos com data de dezembro de 2020.

    O acervo e a previsao usam esta mesma funcao, e ate a etapa 10 isso era um
    acidente: havia DUAS `_ano_do_concurso` no mesmo arquivo, e a segunda
    apagava a primeira em silencio. Quem rodava era sempre esta.
    """
    achado = re.match(r"\s*((?:19|20)\d{2})\s*[-–—]", concurso.titulo)
    if achado:
        return int(achado.group(1))

    # "Edital 003/2018" tambem diz o ano, e cobre o resto dos titulos antigos.
    achado = re.search(r"[Ee]dital[^/]{0,30}/\s*((?:19|20)\d{2})", concurso.titulo)
    if achado:
        return int(achado.group(1))

    return concurso.publicado_em.year if concurso.publicado_em else None
