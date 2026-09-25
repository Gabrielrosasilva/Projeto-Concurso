"""As provas: montar o acervo, ler os cadernos, e o que eles ensinam.

Um assunto so, em quatro passos que vao um atras do outro:

1. **o acervo** - achar o hotsite do concurso, baixar edital, prova e
   gabarito, e gravar no manifesto versionado;
2. **as questoes** - separar o caderno em questoes, com materia e gabarito;
3. **o padrao da banca** - o que ela mais cobra, o que ela repete, e o assunto
   fino de cada questao;
4. **a prova substituta** - qual prova do acervo mais se parece com o cargo
   que eu quero, quando nao existe prova dele.

O que este arquivo NAO faz e ir atras do PDF sozinho: quem fala com o site e
o `radar.provas`, que aqui entra como `arquivos_de_prova` para nao se
confundir com o proprio modulo.
"""
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sqlalchemy import func, select

from radar import alvo as alvos
from radar import assuntos as classificador_de_assunto
from radar import config
from radar import edital_ieses, macetes, substituta
from radar import gabarito as gabarito_oficial
from radar import provas as arquivos_de_prova
from radar import provas_ieses
from radar import questoes as leitor_de_questoes
from radar import questoes_ieses
from radar.collectors.base import Buscador
from radar.db import criar_tabelas, sessao
from radar.models import Concurso, QuestaoDeProva, agora
from radar.servico.comum import (
    ano_do_concurso as _ano_do_concurso,
    cargo_parecido as _cargo_parecido,
    sem_acento as _sem_acento,
)
from radar.servico.simulado import materias_universais

log = logging.getLogger(__name__)


# Cada hotsite da FEPESE tem estas duas paginas, e e so o que precisamos ler.
PAGINAS_DO_HOTSITE = ("provas", "edital")


@dataclass
class ResultadoAcervo:
    concursos: int = 0
    provas: int = 0
    gabaritos: int = 0
    editais: int = 0
    falhas: int = 0

    @property
    def documentos(self) -> int:
        return self.provas + self.gabaritos + self.editais

    def __str__(self) -> str:
        if not self.concursos:
            return "Nada novo para o acervo."
        return (
            f"{self.concursos} concurso(s) lido(s): {self.provas} prova(s), "
            f"{self.gabaritos} gabarito(s), {self.editais} edital(is)"
            + (f", {self.falhas} falha(s)" if self.falhas else "")
        )


def _hotsite(concurso: Concurso) -> str | None:
    """Onde a banca publica os documentos daquele concurso.

    A FEPESE guarda o endereco num campo a parte; na IESES a propria url do
    concurso JA e o hotsite.
    """
    if concurso.fonte == "ieses":
        return concurso.url
    return (concurso.extra or {}).get("hotsite")


# De que fontes da para montar acervo hoje. Cada uma publica os PDFs de um
# jeito, e por isso a leitura da pagina e por banca.
FONTES_COM_ACERVO = ("fepese", "ieses")


# Ordem de prioridade para gastar requisicao.
#
# O alvo principal vem na frente e NAO olha distancia. O acervo existe para me
# mostrar o padrao da banca no cargo que eu vou prestar, e o cargo que eu vou
# prestar e a Policia Penal SC - concurso estadual, onde a prova for. Enquanto
# a regra era so geografica, as duas unicas provas de Agente Penitenciario que
# existem (2013 e 2019) ficavam de fora do acervo por serem `estadual`, que
# nao e nem `nucleo` nem `indefinida`. Era o acervo contrariando o motivo de
# ele existir.
#
# Depois dele continua valendo o de sempre: prova de concurso encerrado perto
# de casa, que e o padrao da banca na minha regiao.
PRIORIDADE_ACERVO = (
    lambda: Concurso.alvo == alvos.PRINCIPAL,
    lambda: Concurso.relevancia.in_(("nucleo", "proximo")),
    lambda: Concurso.relevancia == "indefinida",
)


def _concursos_com_prova(
    limite: int, abertos: bool = False, revisitar: bool = False
) -> list[Concurso]:
    """Quem ainda nao esta no acervo, na ordem de prioridade.

    O manifesto e a memoria: concurso cuja url ja aparece la nao e lido de
    novo. Assim nao precisa de coluna no banco so para marcar isso.

    Com `revisitar`, a memoria e ignorada de proposito. Ela parte de que o
    hotsite nao muda depois da prova, e isso e falso: o gabarito DEFINITIVO do
    concurso de 2019 foi publicado dias depois do caderno, e a retificacao
    dele um mes depois disso. Documento novo em concurso velho so aparece
    passando por cima de novo.
    """
    ja_no_acervo = (
        set() if revisitar
        else {r.get("concurso_url") for r in arquivos_de_prova.carregar_manifesto()}
    )

    escolhidos: list[Concurso] = []
    with sessao() as s:
        for condicao in PRIORIDADE_ACERVO:
            if len(escolhidos) >= limite:
                break
            consulta = (
                select(Concurso)
                .where(Concurso.fonte.in_(FONTES_COM_ACERVO))
                # So concurso ja realizado tem prova publicada. A IESES nao
                # informa status nenhum, entao para ela vale a data: o hotsite
                # de quem ja fez a prova traz os cadernos, e o de quem nao fez
                # ainda simplesmente nao rende documento.
                .where(
                    (Concurso.situacao == "encerrado")
                    | (Concurso.fonte == "ieses")
                    # Concurso que ainda nao aconteceu nao tem prova, mas TEM
                    # edital - e o edital e o que diz se eu posso prestar.
                    | (abertos and Concurso.situacao != "encerrado")
                )
                .where(condicao())
                .order_by(Concurso.publicado_em.desc().nullslast())
            )
            for concurso in s.scalars(consulta):
                if len(escolhidos) >= limite:
                    break
                if concurso.url in ja_no_acervo or not _hotsite(concurso):
                    continue
                escolhidos.append(concurso)

    return escolhidos


def _documentos_do_hotsite(
    concurso: Concurso, hotsite: str, buscador, resultado
) -> list[arquivos_de_prova.Documento]:
    """Os PDFs que o hotsite oferece. Cada banca publica de um jeito.

    A FEPESE tem uma pagina por assunto (`?go=provas`, `?go=edital`); a IESES
    poe tudo numa pagina so, com os arquivos num CDN.
    """
    encontrados: list[arquivos_de_prova.Documento] = []

    if concurso.fonte == "ieses":
        try:
            html = buscador.get(hotsite + "/").text
        except Exception as erro:  # noqa: BLE001 - hotsite fora do ar e rotina
            # Medido: 10 dos 26 hotsites da IESES ja sairam do ar, quase todos
            # de 2023 para tras. Falhar um nao pode parar os outros.
            log.warning("hotsite %s: %s", hotsite, type(erro).__name__)
            resultado.falhas += 1
            return []
        return provas_ieses.ler_hotsite(html, hotsite + "/")

    for pagina in PAGINAS_DO_HOTSITE:
        try:
            html = buscador.get(f"{hotsite}/?go={pagina}&edital=1").text
        except Exception as erro:  # noqa: BLE001 - hotsite fora do ar e rotina
            log.warning("hotsite %s, pagina %s: %s", hotsite, pagina,
                        type(erro).__name__)
            resultado.falhas += 1
            continue

        leitor = (arquivos_de_prova.ler_pagina_de_provas if pagina == "provas"
                  else arquivos_de_prova.ler_pagina_de_edital)
        encontrados.extend(leitor(html, hotsite + "/"))

    # A pagina inicial e a terceira, e ela existe por um motivo so: o gabarito
    # DEFINITIVO nao esta em `?go=provas`. La fica o provisorio, publicado no
    # dia seguinte a prova; o definitivo, com as questoes anuladas e as letras
    # trocadas, e anunciado na lista de avisos da capa.
    try:
        capa = buscador.get(hotsite + "/").text
    except Exception as erro:  # noqa: BLE001 - hotsite fora do ar e rotina
        log.warning("hotsite %s, capa: %s", hotsite, type(erro).__name__)
        resultado.falhas += 1
    else:
        encontrados.extend(arquivos_de_prova.ler_pagina_inicial(capa, hotsite + "/"))

    return encontrados


def montar_acervo(
    limite: int = 20, abertos: bool = False, revisitar: bool = False
) -> ResultadoAcervo:
    """Le os hotsites e baixa edital, prova e gabarito.

    Uma requisicao por pagina do hotsite e uma por PDF, todas com a pausa da
    classe Coletor. Por isso o limite: ler os 520 concursos de uma vez levaria
    horas e a maior parte nao interessa.
    """
    criar_tabelas()
    resultado = ResultadoAcervo()

    escolhidos = _concursos_com_prova(limite, abertos, revisitar)
    if not escolhidos:
        return resultado

    registros = arquivos_de_prova.carregar_manifesto()
    conhecidos = {r.get("url") for r in registros}
    buscador = Buscador()

    for concurso in escolhidos:
        hotsite = _hotsite(concurso).rstrip("/")
        encontrados = _documentos_do_hotsite(concurso, hotsite, buscador, resultado)
        resultado.concursos += 1

        for documento in encontrados:
            if documento.url in conhecidos:
                continue

            documento.concurso_url = concurso.url
            documento.banca = concurso.banca or "FEPESE"
            documento.orgao = concurso.orgao or concurso.titulo
            documento.municipio = concurso.municipio
            documento.ano = _ano_do_concurso(concurso)

            baixado = arquivos_de_prova.baixar(documento, buscador)
            if baixado is None:
                resultado.falhas += 1
                continue

            registros.append(arquivos_de_prova.para_registro(baixado))
            conhecidos.add(baixado.url)

            if baixado.tipo == arquivos_de_prova.PROVA:
                resultado.provas += 1
            elif baixado.tipo in (arquivos_de_prova.GABARITO,
                                  arquivos_de_prova.GABARITO_DEFINITIVO):
                resultado.gabaritos += 1
            else:
                resultado.editais += 1

        # Grava a cada concurso, e nao so no fim. O comando leva minutos: se
        # ele for interrompido no meio - Ctrl+C, queda de rede, maquina
        # desligando - o que ja foi baixado fica catalogado, e a proxima
        # rodada continua de onde parou em vez de recomecar.
        arquivos_de_prova.gravar_manifesto(registros)

    return resultado


def baixar_do_manifesto(forcar: bool = False) -> dict[str, int]:
    """Reconstroi o acervo em disco a partir do manifesto versionado.

    E o que torna os PDFs descartaveis: eles nao vao para o git, mas qualquer
    maquina refaz a pasta inteira a partir do JSON.
    """
    registros = arquivos_de_prova.carregar_manifesto()
    if not registros:
        return {"total": 0, "baixados": 0, "ja_tinha": 0, "falhas": 0}

    buscador = Buscador()
    contagem = {"total": len(registros), "baixados": 0, "ja_tinha": 0, "falhas": 0}

    for registro in registros:
        documento = arquivos_de_prova.Documento(**{
            campo: registro.get(campo)
            for campo in ("tipo", "url", "arquivo", "cargo", "concurso_url",
                          "banca", "orgao", "municipio", "ano")
        })
        caminho = arquivos_de_prova.destino(documento)
        if caminho.exists() and not forcar:
            contagem["ja_tinha"] += 1
            continue

        if arquivos_de_prova.baixar(documento, buscador, forcar=forcar):
            contagem["baixados"] += 1
        else:
            contagem["falhas"] += 1

    return contagem


# --- padrao da banca (fase 4) -----------------------------------------------

@dataclass
class ResultadoExtracao:
    provas: int = 0
    questoes: int = 0
    atualizadas: int = 0
    repetidas: int = 0
    vazias: int = 0

    def __str__(self) -> str:
        if not self.provas:
            return "Nenhuma prova nova para ler."
        texto = f"{self.provas} prova(s) lida(s), {self.questoes} questao(oes)"
        if self.atualizadas:
            texto += f", {self.atualizadas} atualizada(s)"
        if self.repetidas:
            texto += f", {self.repetidas} ja vista(s) em outra prova"
        if self.vazias:
            texto += f", {self.vazias} sem questao"
        return texto


def _provas_por_ler(limite: int, refazer: bool = False) -> list[dict]:
    """Provas do manifesto que ainda nao viraram questao no banco.

    Com `refazer`, devolve todas de novo: e o que permite passar um parser
    melhorado por cima do acervo inteiro.
    """
    with sessao() as s:
        ja_lidas = (
            set() if refazer
            else set(s.scalars(select(QuestaoDeProva.prova_url).distinct()))
        )

    pendentes = [
        registro for registro in arquivos_de_prova.carregar_manifesto()
        if registro.get("tipo") == arquivos_de_prova.PROVA
        and registro.get("caminho")
        and registro["url"] not in ja_lidas
    ]
    return pendentes[:limite]


def _companheiros(registro: dict) -> tuple[dict | None, dict | None]:
    """O gabarito e o edital do mesmo concurso que este caderno.

    So a IESES precisa dos dois: la o gabarito e um PDF a parte, e a materia de
    cada questao vem do edital. O caderno da FEPESE traz as duas coisas dentro.
    """
    do_concurso = [
        r for r in arquivos_de_prova.carregar_manifesto()
        if r.get("concurso_url") == registro.get("concurso_url")
    ]
    # O codigo do cargo e o mesmo nos dois arquivos: prova-1016, gabarito-1016.
    codigo = Path(registro.get("arquivo", "")).stem.split("_")[-1]

    gabarito = next(
        (r for r in do_concurso
         if r.get("tipo") == arquivos_de_prova.GABARITO
         and Path(r.get("arquivo", "")).stem.split("_")[-1] == codigo),
        None,
    )
    edital = next(
        (r for r in do_concurso if r.get("tipo") == arquivos_de_prova.EDITAL),
        None,
    )
    return gabarito, edital


def _caminho(registro: dict | None) -> Path | None:
    if not registro or not registro.get("caminho"):
        return None
    caminho = config.diretorio_dados() / registro["caminho"]
    return caminho if caminho.exists() else None


def _definitivos_do_concurso(registro: dict) -> list[dict]:
    """Os gabaritos definitivos do mesmo concurso, do mais velho ao mais novo.

    A ordem e a data de publicacao porque cada um substitui o anterior: em
    2019 saiu o definitivo em 13/12 e, em 23/01 do ano seguinte, a retificacao
    que anulou mais uma questao. Aplicando na ordem, o ultimo e o que fica.
    """
    return sorted(
        (
            r for r in arquivos_de_prova.carregar_manifesto()
            if r.get("concurso_url") == registro.get("concurso_url")
            and r.get("tipo") == arquivos_de_prova.GABARITO_DEFINITIVO
            and r.get("caminho")
        ),
        key=lambda r: r.get("publicado_em") or "",
    )


def _aplicar_gabarito_definitivo(registro: dict, lidas: list) -> None:
    """Poe o gabarito que VALE por cima do que veio no caderno.

    O caderno da FEPESE traz a resposta marcada dentro do PDF, e e comodo -
    mas ele e publicado no dia seguinte a prova, antes dos recursos. E o
    gabarito PROVISORIO. No concurso de 2019 o definitivo anulou 5 questoes e
    trocou a letra de outras 4, em 100: treinar pelo caderno significava
    marcar como erro 4 respostas certas minhas e perseguir 5 questoes que nao
    tem resposta.

    Grade que nao passa em `e_deste_caderno` e ignorada em silencio, e isso e
    de proposito: aplicar a grade do cargo errado trocaria as 100 respostas de
    uma vez, e ficar com o provisorio e menos pior do que isso.
    """
    for gabarito in _definitivos_do_concurso(registro):
        caminho = _caminho(gabarito)
        if not caminho:
            continue

        # Um PDF traz a grade de varios cargos; a minha e a que passa nas tres
        # conferencias de `e_deste_caderno`.
        minha = next(
            (
                grade for grade in gabarito_oficial.ler_grades_do_pdf(caminho)
                if gabarito_oficial.e_deste_caderno(
                    grade, registro.get("cargo"),
                    registro.get("arquivo") or "", len(lidas),
                )
            ),
            None,
        )
        if minha is None:
            continue

        trocadas, anuladas = gabarito_oficial.aplicar(lidas, minha)
        log.info(
            "gabarito definitivo %s: %d resposta(s) trocada(s), %d anulada(s)",
            gabarito.get("arquivo"), trocadas, anuladas,
        )


def _ler_caderno(registro: dict, caminho: Path) -> list:
    """As questoes de um caderno. Cada banca imprime o dela de um jeito."""
    if (registro.get("banca") or "").upper() != "IESES":
        lidas = leitor_de_questoes.ler_prova(caminho)
        if lidas:
            _aplicar_gabarito_definitivo(registro, lidas)
        return lidas

    gabarito_registro, edital_registro = _companheiros(registro)

    gabarito = {}
    caminho_gabarito = _caminho(gabarito_registro)
    if caminho_gabarito:
        gabarito = questoes_ieses.ler_gabarito(caminho_gabarito)

    texto_do_caderno = leitor_de_questoes.extrair_texto(caminho)
    lidas = questoes_ieses.dividir_em_questoes(texto_do_caderno, gabarito=gabarito)

    caminho_edital = _caminho(edital_registro)
    codigo, _ = questoes_ieses.codigo_e_cargo(texto_do_caderno)
    if caminho_edital and codigo and lidas:
        # Quantas questoes o caderno tem importa: o que passa das materias
        # listadas no edital e Conhecimentos Especificos.
        materias = edital_ieses.materias_do_cargo(
            leitor_de_questoes.extrair_texto(caminho_edital),
            codigo,
            max(q.numero for q in lidas),
        )
        for questao in lidas:
            questao.materia = materias.get(questao.numero)

    return lidas


def extrair_questoes(limite: int = 30, refazer: bool = False) -> ResultadoExtracao:
    """Le os cadernos do acervo e guarda as questoes.

    Nao vai a internet: trabalha em cima dos PDFs que `radar provas` ja baixou.
    """
    criar_tabelas()
    resultado = ResultadoExtracao()

    pendentes = _provas_por_ler(limite, refazer)
    if not pendentes:
        return resultado

    # "Repetida" e a questao que a banca reaproveitou de outra prova. Refazendo
    # o acervo inteiro, o banco ja tem todas: comparar com ele acusaria as 5021
    # como repetidas de si mesmas. Ai a conta e so entre as provas da rodada.
    conhecidas: set[str] | None = set() if refazer else None

    for registro in pendentes:
        caminho = config.diretorio_dados() / registro["caminho"]
        if not caminho.exists():
            continue

        lidas = _ler_caderno(registro, caminho)
        resultado.provas += 1
        if not lidas:
            resultado.vazias += 1
            continue

        with sessao() as s:
            if conhecidas is None:
                conhecidas = set(s.scalars(select(QuestaoDeProva.impressao)))

            for questao in lidas:
                if questao.impressao in conhecidas:
                    resultado.repetidas += 1
                conhecidas.add(questao.impressao)

                # Upsert pela chave natural (prova_url, numero). Apagar e
                # gravar de novo seria mais simples, mas o simulado guarda o id
                # da questao: o historico ficaria apontando para o nada.
                existente = s.scalar(
                    select(QuestaoDeProva)
                    .where(QuestaoDeProva.prova_url == registro["url"])
                    .where(QuestaoDeProva.numero == questao.numero)
                )
                destino = existente or QuestaoDeProva(
                    prova_url=registro["url"], numero=questao.numero
                )
                destino.concurso_url = registro.get("concurso_url")
                destino.banca = registro.get("banca")
                destino.ano = registro.get("ano")
                destino.municipio = registro.get("municipio")
                destino.cargo = registro.get("cargo")
                destino.materia = questao.materia
                destino.enunciado = questao.enunciado
                destino.alternativas = questao.alternativas
                destino.resposta = questao.resposta
                destino.anulada = questao.anulada
                destino.impressao = questao.impressao

                if existente is None:
                    s.add(destino)
                    resultado.questoes += 1
                else:
                    resultado.atualizadas += 1

    return resultado


def incidencia_por_materia(
    cargo: str | None = None, banca: str | None = None, ano: int | None = None
) -> list[tuple[str, int]]:
    """Quantas questoes de cada materia, da mais cobrada para a menos.

    E a resposta para "o que a banca mais cobra", que e o motivo de o acervo
    existir.
    """
    criar_tabelas()
    consulta = (
        select(QuestaoDeProva.materia, func.count())
        # Questao anulada nao conta como questao cobrada: a propria banca
        # desfez a pergunta depois dos recursos.
        .where(QuestaoDeProva.anulada.is_not(True))
        .group_by(QuestaoDeProva.materia)
        .order_by(func.count().desc())
    )
    if cargo:
        consulta = consulta.where(_cargo_parecido(cargo))
    if banca:
        consulta = consulta.where(QuestaoDeProva.banca.ilike(f"%{banca}%"))
    if ano:
        consulta = consulta.where(QuestaoDeProva.ano == ano)

    with sessao() as s:
        return [(materia or "sem materia", n) for materia, n in s.execute(consulta)]


def questoes_repetidas(minimo: int = 2) -> list[tuple[str, int, str]]:
    """Enunciados que aparecem em mais de uma prova.

    Banca que reaproveita questao entrega o padrao de graca: essas sao as que
    mais valem estudar.
    """
    criar_tabelas()
    consulta = (
        select(
            QuestaoDeProva.impressao,
            func.count().label("vezes"),
            func.min(QuestaoDeProva.enunciado),
        )
        .group_by(QuestaoDeProva.impressao)
        .having(func.count() >= minimo)
        .order_by(func.count().desc())
    )
    with sessao() as s:
        return [(imp, vezes, enunciado) for imp, vezes, enunciado in s.execute(consulta)]


def contar_questoes() -> int:
    criar_tabelas()
    with sessao() as s:
        return s.scalar(select(func.count()).select_from(QuestaoDeProva)) or 0


# --- macetes: o costume da banca (fase 7) -----------------------------------

def bancas_com_questao() -> list[str]:
    """As bancas que tem prova no acervo, da que tem mais questoes para a que
    tem menos. Hoje so a FEPESE: o coletor de provas e por banca."""
    criar_tabelas()
    consulta = (
        select(QuestaoDeProva.banca)
        .where(QuestaoDeProva.banca.is_not(None))
        .group_by(QuestaoDeProva.banca)
        .order_by(func.count().desc())
    )
    with sessao() as s:
        return list(s.scalars(consulta))


def bancas_sem_acervo() -> list[str]:
    """Bancas que aparecem nos meus concursos mas ainda nao tem prova aqui.

    Serve para a tela explicar por que o menu e curto, em vez de parecer que o
    radar so conhece uma banca.
    """
    criar_tabelas()
    com_prova = {b.lower() for b in bancas_com_questao()}
    consulta = (
        select(Concurso.banca)
        .where(Concurso.banca.is_not(None))
        .group_by(Concurso.banca)
        .order_by(func.count().desc())
    )
    with sessao() as s:
        citadas = list(s.scalars(consulta))
    return [b for b in citadas if b.lower() not in com_prova]


def composicao_do_caderno(banca: str | None = None) -> list[macetes.FatiaDoCaderno]:
    """Quantas questoes de cada materia caem num caderno tipico da banca."""
    criar_tabelas()
    return macetes.composicao_do_caderno(_questoes_filtradas(banca=banca))


def _questoes_filtradas(
    banca: str | None = None,
    cargo: str | None = None,
    tema: str | None = None,
) -> list[QuestaoDeProva]:
    """As questoes do recorte pedido.

    O `tema` e texto livre de proposito: eu escrevo "crase" ou "primeiros
    socorros", e nao o nome exato da materia. A busca olha a materia E o
    enunciado, sem acento, porque o nome que a banca usa ("Lingua Portuguesa")
    raramente e a palavra que eu penso ("crase").
    """
    consulta = select(QuestaoDeProva)

    if banca:
        consulta = consulta.where(QuestaoDeProva.banca.ilike(f"%{banca}%"))
    if cargo:
        consulta = consulta.where(QuestaoDeProva.cargo.ilike(f"%{cargo}%"))
    if tema:
        procurado = f"%{_sem_acento(tema)}%"
        consulta = consulta.where(
            func.sem_acento(func.coalesce(QuestaoDeProva.materia, "")).ilike(procurado)
            | func.sem_acento(QuestaoDeProva.enunciado).ilike(procurado)
        )

    with sessao() as s:
        return list(s.scalars(consulta))


def analisar_banca(
    banca: str | None = None,
    cargo: str | None = None,
    tema: str | None = None,
) -> macetes.Analise:
    """O que a banca costuma cobrar no recorte pedido.

    Quando o tema aponta para uma materia so - "crase" e Lingua Portuguesa em
    56 de 59 questoes -, a analise traz junto o retrato daquela materia inteira
    na banca: quanto ela cai por caderno e de que assuntos e feita. E a
    pergunta seguinte natural de quem procurou por um assunto.
    """
    criar_tabelas()
    questoes = _questoes_filtradas(banca, cargo, tema)
    analise = macetes.analisar(questoes)

    if not questoes:
        return analise

    dominante = macetes.materia_dominante(questoes)
    analise.materia_dominante = dominante
    if dominante and tema:
        # O retrato e da materia INTEIRA na banca, e nao do recorte: a pergunta
        # e "quanto isso cai nas provas", e nao "quanto isso cai no que eu
        # acabei de filtrar".
        da_materia = [
            q for q in _questoes_filtradas(banca, cargo)
            if q.materia == dominante
        ]
        analise.retrato = macetes.retratar_materia(da_materia, dominante)
        analise.assunto_procurado = macetes.assunto_do_tema(tema, analise.retrato)

    return analise


# --- prova substituta (fase 3) ----------------------------------------------

def provas_parecidas(
    cargo: str,
    banca: str | None = None,
    municipio: str | None = None,
    quantas: int = 8,
) -> list[substituta.Parecida]:
    """As provas do acervo mais parecidas com o cargo que eu quero.

    Existe porque o cargo que eu quero costuma nao ter prova no acervo:
    Guarda Municipal ainda nao tem nenhuma. A Policia Penal tinha o mesmo
    problema ate o alvo principal passar a entrar no acervo esteja onde
    estiver. Em vez de tela vazia, a lista mostra o que existe e EM CIMA DE
    QUE a semelhanca foi medida.
    """
    criar_tabelas()
    if not (cargo or "").strip():
        return []

    consulta = (
        select(
            QuestaoDeProva.cargo,
            QuestaoDeProva.banca,
            QuestaoDeProva.municipio,
            QuestaoDeProva.ano,
            func.count(),
        )
        .where(QuestaoDeProva.cargo.is_not(None))
        .group_by(
            QuestaoDeProva.cargo,
            QuestaoDeProva.banca,
            QuestaoDeProva.municipio,
            QuestaoDeProva.ano,
        )
    )
    with sessao() as s:
        candidatas = [
            substituta.Parecida(cargo=c, banca=b, municipio=m, ano=a, questoes=n)
            for c, b, m, a, n in s.execute(consulta)
        ]

    ano_recente = agora().year - 2
    return substituta.ordenar(
        candidatas,
        cargo,
        banca,
        municipio,
        ano_recente,
        # Os outros nomes do mesmo cargo, quando `config/alvo.yml` conhece
        # algum. Sem isso, procurar "Policial Penal" nao achava as duas provas
        # de "Agente Penitenciario" que existem no acervo - o cargo mudou de
        # nome e os dois nomes nao dividem palavra nenhuma.
        sinonimos=alvos.sinonimos_do_cargo(cargo),
    )[:quantas]


def recado_sobre_o_cargo(cargo: str, parecidas: list) -> str:
    """O que dizer quando nao ha prova parecida o bastante."""
    if parecidas:
        return ""
    return substituta.explicar_ausencia(cargo, materias_universais())


# --- assunto fino da questao (fase 4) ---------------------------------------

def questoes_sem_assunto(
    limite: int | None = None, so_alvo: bool = False
) -> list[QuestaoDeProva]:
    """As questoes de Conhecimentos Especificos que ainda nao tem assunto.

    Uma por ENUNCIADO: das 2.673 questoes, so 1.763 tem enunciado diferente, e
    classificar a mesma pergunta duas vezes seria pagar duas vezes pelo mesmo
    rotulo.

    Com `so_alvo`, entram apenas as questoes das provas do MEU cargo no MEU
    estado - as mesmas que o Meu foco conta. E o recorte que faz a conta
    caber, e e tambem o unico em que o assunto fino muda alguma coisa para
    mim: assunto de prova de Merendeira e da mesma banca e nao me serve.
    """
    criar_tabelas()
    with sessao() as s:
        consulta = (
            select(QuestaoDeProva)
            .where(QuestaoDeProva.assunto.is_(None))
            .where(QuestaoDeProva.materia.is_not(None))
            # Nao se paga para classificar questao que a banca anulou.
            .where(QuestaoDeProva.anulada.is_not(True))
        )
        if so_alvo:
            # Import aqui dentro, e nao no topo: o `foco` e uma tela, e monta
            # a resposta dela em cima deste pacote. Importar la de cima
            # fecharia o circulo.
            from radar import foco

            consulta = consulta.where(
                QuestaoDeProva.prova_url.in_(foco._provas_do_alvo(s))
            )
        candidatas = list(s.scalars(consulta))

    # So o que o catalogo de materias NAO cobre: o resto ja tem assunto de
    # graca, pelas palavras-chave. E o que mantem Portugues e Raciocinio
    # Logico fora da conta paga, inclusive na prova do alvo.
    especificas = [
        q for q in candidatas if macetes.chave_da_materia(q.materia) is None
    ]

    if so_alvo:
        # Materia que o edital de hoje nao lista nao tem em que escolher, e
        # pagar por ela seria pagar por "indefinido". E o caso das materias
        # que sairam do programa entre uma edicao e outra: 2013 cobrou
        # Direito Administrativo e Nocoes de Informatica, e 2019 nao cobra.
        permitidas = {_chave_de_materia(m) for m in assuntos_permitidos(True)}
        especificas = [
            q for q in especificas if _chave_de_materia(q.materia) in permitidas
        ]

    por_enunciado: dict[str, QuestaoDeProva] = {}
    for questao in especificas:
        por_enunciado.setdefault(questao.impressao, questao)

    escolhidas = sorted(
        por_enunciado.values(), key=lambda q: (q.materia or "", q.numero)
    )
    return escolhidas[:limite] if limite else escolhidas


def gravar_assuntos(
    por_id: dict[int, str], modelo: str, quando: datetime | None = None
) -> int:
    """Grava o assunto e propaga para as questoes de enunciado igual.

    Propagar e o que faz o gasto valer mais: uma classificacao paga rotula
    todas as copias daquela pergunta no acervo.

    `modelo` e OBRIGATORIO, e sem ele nao se grava nada. Em 24/09/2026
    descobrimos 93 assuntos no banco que nunca passaram pela API - escritos a
    mao na sessao e exportados como se fossem pagos. Nao havia campo que
    mostrasse isso, e por isso nao havia como auditar. Agora ha, e a porta de
    entrada e esta: assunto sem procedencia nao entra.
    """
    if not modelo or not str(modelo).strip():
        raise ValueError(
            "assunto sem modelo nao e gravado: diga qual modelo classificou"
        )
    if not por_id:
        return 0

    criar_tabelas()
    agora_mesmo = quando or agora()
    gravados = 0
    with sessao() as s:
        for ident, assunto in por_id.items():
            questao = s.get(QuestaoDeProva, ident)
            if questao is None:
                continue
            iguais = list(s.scalars(
                select(QuestaoDeProva).where(
                    QuestaoDeProva.impressao == questao.impressao
                )
            ))
            for copia in iguais:
                copia.assunto = assunto
                copia.assunto_modelo = modelo
                copia.assunto_em = agora_mesmo
                gravados += 1
    return gravados


def _chave_de_materia(nome: str | None) -> str:
    """Como dois nomes de materia sao comparados: sem acento e sem caixa.

    O edital escreve "LEI DE EXECUÇÃO PENAL" no anexo e o caderno escreve "Lei
    de Execução Penal" no cabecalho da secao. Sao a mesma materia.
    """
    return classificador_de_assunto._chave(nome or "")


def assuntos_permitidos(so_alvo: bool) -> dict:
    """A lista de assuntos que a IA pode escolher, ou {} quando nao ha lista.

    So existe para o recorte do alvo, e isso e proposital: a lista sai do
    CONTEUDO PROGRAMATICO do edital do MEU concurso, e ele nao diz nada sobre
    a prova de Merendeira de outra prefeitura.
    """
    if not so_alvo:
        return {}

    from radar import foco

    return foco.programa_do_alvo()


def classificar_assuntos(
    limite: int | None = None,
    teto_em_dolar: float = 1.0,
    so_alvo: bool = False,
) -> dict:
    """Classifica o assunto das questoes de Conhecimentos Especificos.

    Custa dinheiro: e a unica parte do radar que fala com uma API paga. O teto
    e conferido antes de cada lote, com o custo real que a API informou.

    O que foi pago sai do banco na mesma hora e vai para `data/assuntos.json`,
    que e versionado. Sem isso, refazer o banco - ou trocar de computador -
    faria eu pagar de novo pela mesma questao.
    """
    chave = config.chave_da_anthropic()
    if not chave:
        return {"erro": "sem chave", "classificados": 0}

    # A lista vem antes da fila, e nao depois: sem o programa do edital nao ha
    # em que escolher, e sem isso a IA voltaria a inventar nome de assunto.
    # Nao gastar e a resposta certa, e dizer por que e melhor do que devolver
    # fila vazia sem explicacao.
    permitidos = assuntos_permitidos(so_alvo)
    if so_alvo and not permitidos:
        return {"erro": "sem programa do edital", "classificados": 0,
                "pendentes": 0}

    pendentes = questoes_sem_assunto(limite, so_alvo=so_alvo)
    if not pendentes:
        return {"classificados": 0, "pendentes": 0}

    resultado = classificador_de_assunto.classificar(
        pendentes, chave, teto_em_dolar=teto_em_dolar, permitidos=permitidos
    )
    # O modelo que respondeu vai junto do rotulo, e nao so no log: e ele que
    # diz, meses depois, que aquele assunto saiu de uma chamada de verdade.
    gravados = gravar_assuntos(
        resultado.classificados, classificador_de_assunto.MODELO
    )

    guardados = 0
    if gravados:
        from radar import acervo

        guardados = acervo.exportar_assuntos()

    return {
        "pendentes": len(pendentes),
        "classificados": len(resultado.classificados),
        "gravados": gravados,
        "guardados": guardados,
        "custo": resultado.uso.custo,
        "chamadas": resultado.uso.chamadas,
        "parou_no_teto": resultado.parou_no_teto,
        "falhas": resultado.falhas,
    }


@dataclass
class CoberturaDaMateria:
    """Quantas questoes de uma materia ja tem assunto, e por qual caminho."""

    materia: str
    questoes: int
    com_assunto: int
    #: "catalogo" (de graca, por palavra-chave), "edital" (pago, escolhendo
    #: dentro do programa) ou "fora" (materia que o edital de hoje nao cobra
    #: mais, e por isso nao tem lista em que escolher).
    origem: str

    @property
    def porcentagem(self) -> float:
        return (self.com_assunto / self.questoes * 100) if self.questoes else 0.0


def cobertura_de_assunto(so_alvo: bool = True) -> list[CoberturaDaMateria]:
    """Quanto de cada materia ja tem assunto, da pior para a melhor.

    As duas origens entram na mesma tabela porque a pergunta e uma so - "esta
    questao tem assunto?" - mas elas nao sao a mesma coisa, e a coluna diz
    qual e qual. Portugues e Raciocinio Logico saem do catalogo de
    palavras-chave, de graca; as outras nove saem do programa do edital, e
    cada uma delas foi paga uma vez.
    """
    criar_tabelas()
    with sessao() as s:
        consulta = (
            select(QuestaoDeProva)
            .where(QuestaoDeProva.materia.is_not(None))
            .where(QuestaoDeProva.anulada.is_not(True))
        )
        if so_alvo:
            from radar import foco

            consulta = consulta.where(
                QuestaoDeProva.prova_url.in_(foco._provas_do_alvo(s))
            )
        questoes = list(s.scalars(consulta))

    por_materia: dict[str, list] = {}
    for questao in questoes:
        por_materia.setdefault(questao.materia, []).append(questao)

    no_programa = {_chave_de_materia(m) for m in assuntos_permitidos(so_alvo)}

    cobertura = []
    for materia, lista in por_materia.items():
        chave = macetes.chave_da_materia(materia)
        if chave:
            # De graca: quem responde e o catalogo de palavras-chave, que
            # trabalha por ENUNCIADO distinto. A proporcao volta para numero
            # de questoes porque e isso que a prova tem.
            _, sem = macetes.assuntos_de(lista, chave)
            distintos = len({q.impressao for q in lista})
            com = (round((distintos - sem) / distintos * len(lista))
                   if distintos else 0)
            origem = "catalogo"
        else:
            com = sum(1 for q in lista if q.assunto)
            # Materia que saiu do programa entre uma edicao e outra nao tem em
            # que escolher, e nunca vai ser classificada: 2013 cobrou Direito
            # Administrativo e Nocoes de Informatica, e 2019 nao cobra.
            origem = ("edital" if not so_alvo or _chave_de_materia(materia)
                      in no_programa else "fora")

        cobertura.append(CoberturaDaMateria(
            materia=materia, questoes=len(lista), com_assunto=com, origem=origem
        ))

    return sorted(cobertura, key=lambda c: (c.porcentagem, c.materia))
