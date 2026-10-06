"""O diario do cronograma: como foi cada dia, anotado a mao.

A meta do dia e uma das quatro do plano - ideal, reduzida, minima, ou nao
fiz. O registro do dia guarda so a meta e o recado: o numero do dia e
CALCULADO, das faixas, dos extras e do radar, pelo `servico.metricas` - o
unico lugar que conta questao (Etapa 1C). O Meu foco, o Onde estudar e a home
contam so o que eu respondi dentro do radar, e dizem isso na tela.
"""
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

from sqlalchemy import select

from radar import acervo
from radar import alvo
from radar import conteudos as arvore
from radar import cronograma as plano_de_estudo
from radar.db import criar_tabelas, sessao
from radar.models import EstadoDoDia, RegistroDoDia, agora
from radar.servico import extra as estudo_extra
# A excecao vem do comum porque o estudo extra recusa pelos mesmos motivos, e
# continua sendo lida como `servico.cronograma.RegistroInvalido`.
from radar.servico.comum import RegistroInvalido    # noqa: F401 - reexportada
from radar.util import fuso_local

METAS = ("ideal", "reduzida", "minima", "nao_fiz")


def agora_local() -> datetime:
    """O relogio de Florianopolis.

    UM lugar so, e e por isso que ele fica aqui e nao no comum: o teste para o
    tempo trocando este nome, e o `hoje_local` logo abaixo tem que passar por
    ele. Com os dois em arquivos diferentes, parar o relogio parava metade do
    radar e a outra metade continuava em 2026 de verdade.
    """
    return datetime.now(fuso_local())


def hoje_local() -> date:
    return agora_local().date()


def registrar(
    data: date,
    meta: str,
    anotacao: str | None = None,
    *,
    plano: plano_de_estudo.Plano | None = None,
    hoje: date | None = None,
) -> RegistroDoDia:
    """Cria ou atualiza o registro daquela data: a meta e o recado.

    Nao guarda numero nenhum (Etapa 1C). Antes, salvar a meta gravava uma
    COPIA do total do dia, e a tela mostrava as duas - o calculado e a copia
    -, que divergem no dia em que eu corrijo uma faixa. As copias ja gravadas
    ficam no banco e no JSON como estao: nada e apagado, so deixam de ser o
    numero do dia. A 1D confere uma a uma.

    `plano` e `hoje` existem para o teste: o ciclo real comeca no futuro, e
    sem eles nenhum teste conseguiria marcar um dia "passado" do plano.
    """
    if meta not in METAS:
        raise RegistroInvalido(
            f"Meta {meta!r} não existe. Use uma destas: {', '.join(METAS)}"
        )

    hoje = hoje or hoje_local()
    if data > hoje:
        # Marcar o futuro seria anotar o que eu PRETENDO fazer, e o diario e
        # do que eu fiz.
        raise RegistroInvalido(
            f"{data:%d/%m/%Y} ainda não chegou: só se marca hoje ou dia passado"
        )
    plano = plano or plano_de_estudo.carregar()
    if plano.dia(data) is None:
        raise RegistroInvalido(f"{data:%d/%m/%Y} não está no cronograma")

    criar_tabelas()
    with sessao() as s:
        registro = s.scalar(select(RegistroDoDia).where(RegistroDoDia.data == data))
        if registro is None:
            registro = RegistroDoDia(data=data)
            s.add(registro)
        registro.meta = meta
        registro.anotacao = anotacao
        registro.anotado_em = agora()
    return registro


def registrar_o_dia(
    data: date,
    meta: str,
    anotacao: str | None = None,
    *,
    plano: plano_de_estudo.Plano | None = None,
    hoje: date | None = None,
) -> RegistroDoDia:
    """O "Como foi o dia" da tela: eu escolho a meta, o radar faz a conta.

    A conta nao e gravada: ela e feita na hora pelo `servico.metricas`, das
    faixas, dos extras e do que eu respondi no radar.
    """
    return registrar(data, meta, anotacao, plano=plano, hoje=hoje)


def registros(inicio: date, fim: date) -> dict[date, RegistroDoDia]:
    """Os registros entre as duas datas, inclusive, pela data."""
    criar_tabelas()
    with sessao() as s:
        achados = s.scalars(
            select(RegistroDoDia)
            .where(RegistroDoDia.data >= inicio)
            .where(RegistroDoDia.data <= fim)
        )
        return {r.data: r for r in achados}


def apagar(data: date) -> bool:
    """Apaga o dia inteiro do diario: o registro e os checks das faixas.

    Do banco E dos arquivos (data/registro_estudo.json e
    data/estado_do_dia.json), pelo mesmo motivo do descartar simulado: o
    arquivo so cresce, e o que saisse so do banco voltaria no proximo
    `importar`.
    """
    criar_tabelas()
    with sessao() as s:
        registro = s.scalar(select(RegistroDoDia).where(RegistroDoDia.data == data))
        if registro is not None:
            s.delete(registro)
        estado = s.scalar(select(EstadoDoDia).where(EstadoDoDia.data == data))
        if estado is not None:
            s.delete(estado)
    saiu_do_arquivo = (acervo.esquecer_registros([data])
                       + acervo.esquecer_estados([data]))
    return registro is not None or estado is not None or saiu_do_arquivo > 0


# --- os checks de cada faixa ---------------------------------------------------
# A faixa e reconhecida por bloco + indice + TITULO. So a posicao nao basta:
# se o cronograma.yml mudar, a faixa 2 da noite pode virar outra, e o check
# antigo marcaria como feita uma faixa que eu nao fiz. Com o titulo junto, o
# check que nao bate mais e simplesmente ignorado.

def _faixa_do_plano(plano, data: date, bloco: str, indice: int):
    """A faixa daquela posicao, MONTADA: com o horario, a duracao e o numero
    de questoes do nivel daquele dia.

    Montada, e nao crua do arquivo, porque e dela que saem os numeros que o
    check guarda: a faixa crua de questoes nao tem duracao (ela sai da conta
    questoes x minutos por questao) e tem o numero de questoes do plano, nao o
    do nivel em que a semana estava.
    """
    if plano.dia(data) is None:
        raise RegistroInvalido(f"{data:%d/%m/%Y} não está no cronograma")
    if bloco not in plano_de_estudo.TODOS_OS_BLOCOS:
        raise RegistroInvalido(f"Bloco {bloco!r} não existe")
    nivel = nivel_do_dia(plano, data)
    if bloco == plano_de_estudo.BLOCO_DO_PLANO_B:
        # As faixas do Plano B nao estao no arquivo: saem do dia, com o Plano
        # B que esta ativo. Sem ele ativo, nao ha o que marcar.
        estado = estado_do_dia(data)
        if estado is None or not estado.plano_b:
            raise RegistroInvalido("O Plano B não está ativo neste dia.")
        montado = plano_de_estudo.montar_plano_b(plano, data, estado.plano_b,
                                                 nivel.efetivo)
    else:
        montado = plano_de_estudo.montar_dia(plano, data, nivel.efetivo)
    faixas = getattr(montado, bloco)
    if not 0 <= indice < len(faixas):
        raise RegistroInvalido(f"O bloco {bloco} não tem a faixa {indice}")
    return faixas[indice]


def _faixa_para_marcar(data: date, bloco: str, indice: int, titulo: str,
                       plano, hoje: date):
    """A faixa que a tela mandou marcar, conferida. Comum aos tres comandos."""
    if data > hoje:
        raise RegistroInvalido(
            f"{data:%d/%m/%Y} ainda não chegou: só se marca faixa de hoje ou de dia passado"
        )
    faixa = _faixa_do_plano(plano, data, bloco, indice)
    if faixa.titulo != titulo:
        raise RegistroInvalido(
            "Essa faixa mudou no config/cronograma.yml desde que a tela abriu. "
            "Recarregue a página e marque de novo."
        )
    if faixa.tipo == "pausa":
        raise RegistroInvalido("Pausa não se marca.")
    if faixa.desligada:
        raise RegistroInvalido(
            f"{plano_de_estudo.FRASE_DO_ANKI_DESATIVADO}: a faixa não se marca."
        )
    return faixa


def _gravar_check(data: date, bloco: str, indice: int, titulo: str,
                  check: dict | None) -> bool:
    """Troca o check daquela posicao pelo novo (ou tira, com None).

    Devolve True quando a faixa ficou FEITA. Check velho na mesma posicao com
    outro titulo sai junto: ele nao vale mais nada e so atrapalharia a leitura
    do arquivo.
    """
    criar_tabelas()
    with sessao() as s:
        estado = s.scalar(select(EstadoDoDia).where(EstadoDoDia.data == data))
        if estado is None:
            estado = EstadoDoDia(data=data, faixas_feitas=[])
            s.add(estado)
        antes = list(estado.faixas_feitas or [])
        mesma_posicao = [c for c in antes
                         if c.get("bloco") == bloco and c.get("indice") == indice]
        ficam = [c for c in antes if c not in mesma_posicao]
        if check is not None:
            ficam.append(check)
        # Lista nova, e nao append na velha: o SQLAlchemy so percebe que a
        # coluna JSON mudou quando o valor e trocado.
        estado.faixas_feitas = ficam
        estado.atualizado_em = agora()
    return check is not None


def _check_da_faixa(bloco: str, indice: int, faixa, questoes=None, acertos=None,
                    consulta: bool | None = None,
                    conteudo: str | None = None) -> dict:
    """O que fica gravado de uma faixa feita.

    Os numeros vao TODOS para o JSON - minutos, questoes, acertos, consulta,
    materia e assunto - e nao so a posicao. O motivo e o Ciclo 2: quando o
    cronograma.yml mudar, a faixa 2 da noite de 20/10 sera outra coisa, e o
    historico tem que continuar contando o que eu fiz naquele dia. Posicao no
    arquivo nao e historico; numero gravado e.
    """
    check = {
        "bloco": bloco,
        "indice": indice,
        "titulo": faixa.titulo,
        "minutos": faixa.duracao or 0,
        "questoes": questoes,
        "acertos": acertos,
        "consulta": bool(consulta if consulta is not None
                         else plano_de_estudo.consulta_por_padrao(faixa)),
        "materia": faixa.materia,
        # O tema da faixa. "assunto" e o nome que o caderno de erros e o
        # estudo extra usam para a mesma coisa.
        "assunto": faixa.titulo,
    }
    # O no da arvore. O padrao e a chave `conteudo` da faixa (Etapa 2); o
    # formulario pode descer para um no mais fundo dela (Etapa 4) - e assim
    # que o anotado do Qconcursos chega ao subassunto. So entra com valor: os
    # checks gravados antes continuam com o mesmo formato.
    escolhido = _conferir_o_no(conteudo, faixa)
    if escolhido:
        check["conteudo"] = escolhido
    return check


def _conferir_o_no(caminho: str | None, faixa) -> str | None:
    """O no escolhido no formulario, ou o da faixa quando nao escolhi nenhum.

    Duas recusas, as duas em voz alta:

      * no que nao existe na arvore - senao o check ficaria pendurado num
        caminho que ninguem le;
      * no de fora do ramo da faixa, quando a faixa aponta para um no. Anotar
        Portugues dentro da faixa de LEP nao e detalhar, e trocar de materia -
        e para isso existe o estudo extra.
    """
    caminho = (caminho or "").strip()
    if not caminho:
        return faixa.conteudo
    from radar import servico

    if caminho not in servico.conteudos.caminhos():
        raise RegistroInvalido(
            f"O conteúdo {caminho!r} não está na árvore (data/conteudos.json). "
            f"Confira com `radar conteudos`."
        )
    if faixa.conteudo and not (caminho == faixa.conteudo
                               or caminho.startswith(faixa.conteudo + arvore.SEPARADOR)):
        raise RegistroInvalido(
            f"O conteúdo {caminho!r} não está dentro de {faixa.conteudo!r}, "
            f"que é o da faixa {faixa.titulo!r}. Para anotar outro conteúdo, "
            f"use o estudo extra."
        )
    return caminho


def marcar_faixa(
    data: date,
    bloco: str,
    indice: int,
    titulo: str,
    *,
    plano: plano_de_estudo.Plano | None = None,
    hoje: date | None = None,
) -> bool:
    """Marca a faixa se estava aberta, desmarca se estava feita.

    E o circulo das faixas SEM acerto (teoria, lei seca, correcao, Anki). As de
    questao passam pelo `anotar_faixa`, que tem numero para guardar.

    Devolve True quando ela ficou FEITA. `plano` e `hoje` existem para o
    teste, como no `registrar`.
    """
    hoje = hoje or hoje_local()
    plano = plano or plano_de_estudo.carregar()
    faixa = _faixa_para_marcar(data, bloco, indice, titulo, plano, hoje)

    estado = estado_do_dia(data)
    estava_feita = any(
        c.get("bloco") == bloco and c.get("indice") == indice
        and c.get("titulo") == titulo
        for c in (estado.faixas_feitas if estado else []) or []
    )
    check = None if estava_feita else _check_da_faixa(bloco, indice, faixa,
                                                     questoes=faixa.questoes)
    return _gravar_check(data, bloco, indice, titulo, check)


def anotar_faixa(
    data: date,
    bloco: str,
    indice: int,
    titulo: str,
    questoes=None,
    acertos=None,
    consulta: bool = False,
    conteudo: str | None = None,
    *,
    plano: plano_de_estudo.Plano | None = None,
    hoje: date | None = None,
) -> bool:
    """Marca uma faixa de questoes com "fiz X, acertei Y".

    Chamar de novo corrige os numeros - e o que faz a faixa feita reabrir o
    formulario com os valores em vez de virar duas linhas no historico.

    `acertos` vazio e normal e nao e erro: as questoes contam no VOLUME e nao
    entram em acerto nenhum. Foi o que aconteceu de verdade - eu fiz, e nao
    anotei quantas acertei.

    `questoes` vazio so vale na faixa que eu fiz no radar (decisao 138): o
    check fica com 0 questoes e o tempo, e marcado `no_radar`.
    """
    hoje = hoje or hoje_local()
    plano = plano or plano_de_estudo.carregar()
    faixa = _faixa_para_marcar(data, bloco, indice, titulo, plano, hoje)
    if not plano_de_estudo.tem_acerto(faixa):
        raise RegistroInvalido(
            f"A faixa {faixa.titulo!r} não é de questões: nela eu só marco que fiz."
        )

    feitas = _inteiro_do_check(questoes, "As questões feitas")
    certas = _inteiro_do_check(acertos, "Os acertos")
    if certas is not None:
        if feitas is None:
            raise RegistroInvalido("Acertos sem questões: diga quantas você fez.")
        if certas > feitas:
            raise RegistroInvalido(
                f"Acertos ({certas}) maior que as questões feitas ({feitas})."
            )
    if not feitas:
        # Regra da 1D: faixa de questoes sem questao nao foi feita. Aceitar o
        # 0 contava os minutos dela no dia - foi o Bonus de 28 e 29/09, 25 min
        # cada, de um estudo que nao aconteceu. A excecao e a faixa feita no
        # radar (decisao 138): as questoes dela ja contam sozinhas, e o check
        # guarda so o tempo. Sem ela, eu digitava um numero, e as mesmas
        # questoes contavam duas vezes (05 e 06/10).
        from radar.servico import metricas

        no_radar = metricas.no_radar_por_faixa(data).get((bloco, indice, titulo))
        if not (no_radar and no_radar.questoes):
            raise RegistroInvalido(
                "Faixa de questões com 0 questões não conta como feita: "
                "se não fez nenhuma, desmarque a faixa. Se treinou no radar, "
                "abra o treino pelo botão desta faixa: aí o ✓ vazio vale."
            )
        check = _check_da_faixa(bloco, indice, faixa, 0, None, consulta, conteudo)
        check["no_radar"] = True
        return _gravar_check(data, bloco, indice, titulo, check)

    return _gravar_check(data, bloco, indice, titulo,
                         _check_da_faixa(bloco, indice, faixa, feitas, certas,
                                         consulta, conteudo))


def desmarcar_faixa(
    data: date,
    bloco: str,
    indice: int,
    titulo: str,
    *,
    plano: plano_de_estudo.Plano | None = None,
    hoje: date | None = None,
) -> bool:
    """Tira o check da faixa, com os numeros que estavam nele. Sempre False."""
    hoje = hoje or hoje_local()
    plano = plano or plano_de_estudo.carregar()
    _faixa_para_marcar(data, bloco, indice, titulo, plano, hoje)
    return _gravar_check(data, bloco, indice, titulo, None)


def _inteiro_do_check(valor, campo: str) -> int | None:
    """Campo numerico do formulario da faixa: vazio vira None, lixo e recusado."""
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        return None
    try:
        numero = int(str(valor).strip())
    except ValueError:
        raise RegistroInvalido(f"{campo} precisa ser um número inteiro (veio {valor!r})")
    if numero < 0:
        raise RegistroInvalido(f"{campo} não pode ser negativo ({numero})")
    return numero


def estado_do_dia(data: date) -> EstadoDoDia | None:
    criar_tabelas()
    with sessao() as s:
        return s.scalar(select(EstadoDoDia).where(EstadoDoDia.data == data))


def faixas_feitas(dia, estado: EstadoDoDia | None) -> set[tuple[str, int]]:
    """As posicoes (bloco, indice) feitas que ainda batem com o dia do
    cronograma.yml. Check cujo titulo nao bate e ignorado, sem erro."""
    if dia is None or estado is None:
        return set()
    feitas = set()
    for check in estado.faixas_feitas or []:
        bloco, indice = check.get("bloco"), check.get("indice")
        if bloco not in plano_de_estudo.TODOS_OS_BLOCOS or not isinstance(indice, int):
            continue
        faixas = getattr(dia, bloco)
        if not 0 <= indice < len(faixas):
            continue
        faixa = faixas[indice]
        if faixa.titulo == check.get("titulo") and faixa.tipo != "pausa":
            feitas.add((bloco, indice))
    return feitas


@dataclass
class FaixaFeita:
    """Uma faixa marcada, com o que eu anotei nela.

    `do_plano` diz que os numeros sairam do cronograma.yml, e nao de mim: e o
    caso dos checks antigos, gravados antes de a faixa ter formulario. Eles
    continuam valendo - o que eu fiz naquele dia foi o que o plano pedia.
    """
    bloco: str
    indice: int
    titulo: str
    minutos: int = 0
    questoes: int | None = None
    acertos: int | None = None
    consulta: bool = False
    materia: str | None = None
    assunto: str | None = None
    #: O no da arvore de conteudos, pelo caminho de nomes. Vem do check (o que
    #: eu escolhi ao anotar) ou, sem ele, da chave `conteudo` da faixa no
    #: cronograma.yml. None quando a faixa nao aponta para no nenhum - e ai o
    #: que eu fiz conta no dia e em no nenhum (Etapa 4).
    conteudo: str | None = None
    do_plano: bool = False
    #: O tipo da faixa no plano (teoria, questoes, revisao...): e ele que diz
    #: se o que eu fiz ali foi uma revisao.
    tipo: str = ""
    #: Feita no radar, com o "fiz" vazio (decisao 138): as questoes contam
    #: pelas respostas, e a faixa guarda so o tempo.
    no_radar: bool = False

    @property
    def porcentagem(self) -> int | None:
        """73, de "11 de 15 - 73%". None quando eu nao anotei os acertos."""
        if not self.questoes or self.acertos is None:
            return None
        return round(100 * self.acertos / self.questoes)


def valores_das_faixas(dia, estado: EstadoDoDia | None) -> dict:
    """O que esta gravado em cada faixa feita, por posicao (bloco, indice).

    Check sem os numeros (os gravados antes desta etapa) e preenchido pelo
    plano, se a faixa ainda existir nele: o dia foi feito como o plano pedia, e
    mostrar vazio ali seria perder a informacao que eu tinha.
    """
    if dia is None or estado is None:
        return {}
    valores = {}
    for check in estado.faixas_feitas or []:
        bloco, indice = check.get("bloco"), check.get("indice")
        if bloco not in plano_de_estudo.TODOS_OS_BLOCOS or not isinstance(indice, int):
            continue
        faixas = getattr(dia, bloco)
        if not 0 <= indice < len(faixas):
            continue
        faixa = faixas[indice]
        if faixa.titulo != check.get("titulo") or faixa.tipo == "pausa":
            continue
        antigo = "questoes" not in check
        valores[(bloco, indice)] = FaixaFeita(
            bloco=bloco,
            indice=indice,
            titulo=faixa.titulo,
            minutos=check.get("minutos") if check.get("minutos") is not None
                    else (faixa.duracao or 0),
            questoes=faixa.questoes if antigo else check.get("questoes"),
            acertos=check.get("acertos"),
            consulta=bool(check["consulta"]) if "consulta" in check
                     else plano_de_estudo.consulta_por_padrao(faixa),
            materia=check.get("materia") or faixa.materia,
            assunto=check.get("assunto") or faixa.titulo,
            conteudo=check.get("conteudo") or faixa.conteudo,
            do_plano=antigo,
            tipo=faixa.tipo,
            no_radar=bool(check.get("no_radar")),
        )
    return valores


@dataclass
class Sugestao:
    """O que os checks sugerem para o "Como foi o dia". So sugere: quem
    escolhe a meta e salva sou eu."""
    meta: str | None            # ideal | reduzida | minima | None (sem sugestao)
    feitas: int                 # faixas que contam, feitas
    total: int                  # faixas que contam: nem pausa, nem opcional
    questoes: int               # soma das questoes das faixas marcadas


def sugerir_meta(dia, feitas: set[tuple[str, int]]) -> Sugestao:
    """A regra, em ordem:

    - todas as faixas que contam (nem pausa, nem bonus) = Ideal;
    - a manha inteira + a faixa de Direito da noite = Reduzida;
    - pelo menos uma faixa de questoes (fora o bonus) = Minima;
    - nada marcado, ou so o que nao fecha nenhuma regra = sem sugestao.

    As questoes somam TODA faixa marcada, bonus inclusive: e o que eu fiz.
    O numero e o do dia montado, ou seja, o do nivel efetivo.
    """
    def contam(bloco):
        return [(bloco, i) for i, f in enumerate(getattr(dia, bloco))
                if f.tipo != "pausa" and not f.opcional and not f.desligada]

    def faixa(posicao):
        bloco, indice = posicao
        return getattr(dia, bloco)[indice]

    todas = [p for bloco in plano_de_estudo.TODOS_OS_BLOCOS for p in contam(bloco)]
    feitas_que_contam = [p for p in todas if p in feitas]
    questoes = sum(faixa(p).questoes or 0 for p in feitas)
    sugestao = Sugestao(None, len(feitas_que_contam), len(todas), questoes)
    if not feitas:
        return sugestao

    manha_inteira = all(p in feitas for p in contam("manha"))
    direito_feito = any(f.rampa == "direito" and ("noite", i) in feitas
                        for i, f in enumerate(dia.noite))
    alguma_de_questoes = any(faixa(p).questoes and not faixa(p).opcional for p in feitas)
    if todas and len(feitas_que_contam) == len(todas):
        sugestao.meta = "ideal"
    elif manha_inteira and direito_feito:
        sugestao.meta = "reduzida"
    elif alguma_de_questoes:
        sugestao.meta = "minima"
    return sugestao


# --- o Plano B ---------------------------------------------------------------

def faixas_que_medem(dia) -> list[str]:
    """Os titulos das faixas do dia que medem: o diagnostico e o simulado no
    radar (`composicao.mede`) e o R+7 que refaz os erros deles
    (`sabado.refaz_rodadas`). Sao a linha de base que decide o Ciclo 2, e por
    isso o Plano B nao as troca (decisao 135)."""
    # Import aqui: composicao e sabado leem o cronograma do servico.
    from radar.servico import composicao, sabado
    if dia is None:
        return []
    return [f.titulo for f in dia.faixas()
            if composicao.mede(f) or sabado.refaz_rodadas(f)]


def ativar_plano_b(
    data: date,
    minutos: int | None,
    *,
    plano: plano_de_estudo.Plano | None = None,
    hoje: date | None = None,
) -> None:
    """Grava o Plano B escolhido no dia (30 ou 60). `None` volta ao plano
    completo. Os checks das faixas ficam como estao: voltar ao completo nao
    apaga o que eu ja tinha riscado."""
    hoje = hoje or hoje_local()
    plano = plano or plano_de_estudo.carregar()
    if minutos is not None:
        if data > hoje:
            raise RegistroInvalido(
                f"{data:%d/%m/%Y} ainda não chegou: Plano B é para o dia que apertou"
            )
        if plano.plano_b is None:
            raise RegistroInvalido("O config/cronograma.yml não tem o bloco `plano_b`.")
        if minutos not in plano.plano_b.opcoes:
            raise RegistroInvalido(
                f"Plano B de {minutos} min não existe (há: "
                f"{', '.join(str(m) for m in sorted(plano.plano_b.opcoes))})"
            )
        if data.weekday() == plano_de_estudo.DOMINGO:
            raise RegistroInvalido("Domingo é descanso: não tem Plano B.")
        if plano.dia(data) is None:
            raise RegistroInvalido(f"{data:%d/%m/%Y} não está no cronograma")
        medem = faixas_que_medem(plano.dia(data))
        if medem:
            raise RegistroInvalido(
                f"{data:%d/%m/%Y} é dia de medir ({', '.join(medem)}): o Plano B não "
                f"troca as faixas que medem. Se o dia apertar, faça só elas.")

    criar_tabelas()
    with sessao() as s:
        estado = s.scalar(select(EstadoDoDia).where(EstadoDoDia.data == data))
        if estado is None:
            if minutos is None:
                return
            estado = EstadoDoDia(data=data, faixas_feitas=[])
            s.add(estado)
        estado.plano_b = minutos
        estado.atualizado_em = agora()


# --- a tela "Hoje" -----------------------------------------------------------
# Tudo o que a pagina precisa, montado aqui: o template so desenha. Nenhuma
# conta de horario ou de nivel mora no HTML.

@dataclass
class Pilula:
    """Um dia na faixa da semana."""
    data: date
    rotulo: str                 # "Seg"
    meta: str | None            # o que marquei; None = sem marcacao
    futuro: bool
    aberta: bool                # e o dia que esta na tela


@dataclass
class BlocoNaTela:
    chave: str
    nome: str
    faixas: list
    inicio: time | None = None
    fim: time | None = None
    questoes: int = 0


@dataclass
class PontoDoMapa:
    """Uma etapa do mapa do ano com o "voce esta aqui" ja decidido."""
    etapa: object
    atual: bool
    passada: bool


@dataclass
class Agora:
    """O cartao AGORA: so existe quando o dia aberto e hoje."""
    situacao: str               # antes | faixa | entre | fim
    atual: object = None        # a Faixa em andamento
    proxima: object = None      # a Faixa que vem depois


@dataclass
class TelaDoDia:
    # dia | domingo | antes | depois | fora | sem_arquivo | erro
    estado: str
    data: date
    hoje: date
    mensagem: str | None = None
    plano: object = None
    dia: object = None
    nivel: object = None
    total_semanas: int = 0
    pilulas: list[Pilula] = field(default_factory=list)
    blocos: list[BlocoNaTela] = field(default_factory=list)
    fim_do_dia: time | None = None
    agora: Agora | None = None
    hora: time | None = None    # a hora de agora, so quando o dia e hoje
    registro: RegistroDoDia | None = None
    # O dia que o estado vazio mostra: amanha (domingo) ou o primeiro (antes).
    outro_dia: object = None
    # O cartao "Objetivo": o nome do alvo sai do config/alvo.yml, nunca daqui.
    nome_do_alvo: str | None = None
    # Dias seguidos sem zerar (ideal, reduzida ou minima), contados de hoje.
    sequencia: int | None = None
    # A frase animadora do cartao "Esta semana". None: a frase some.
    frase: str | None = None
    # Os checks: as posicoes (bloco, indice) feitas, e o que elas sugerem.
    feitas: set = field(default_factory=set)
    sugestao: object = None
    # O que esta anotado em cada faixa feita, por posicao: fiz, acertei, minutos.
    valores: dict = field(default_factory=dict)
    # O estudo extra do dia, e a conta dele (`metricas.Conta`: faixas + extra
    # + radar + treino de IA), da fonte unica.
    extras: list = field(default_factory=list)
    totais: object = None
    # O Plano B ativo (30 ou 60 minutos), e as opcoes que o botao oferece.
    plano_b: int | None = None
    opcoes_do_plano_b: list[int] = field(default_factory=list)
    # As faixas que medem no dia (diagnostico, simulado e R+7 dos diagnosticos
    # no radar). Com elas, o dia nao tem Plano B (decisao 135).
    faixas_que_medem: list[str] = field(default_factory=list)
    # O mapa do ano, com a etapa de hoje marcada. Vazio quando o arquivo nao
    # tem o bloco `mapa` - ai o cartao nao aparece.
    mapa: list[PontoDoMapa] = field(default_factory=list)

    def faixas_em_ordem(self) -> list:
        """As faixas da tela, na ordem em que aparecem (o dia, ou o Plano B)."""
        return [f for bloco in self.blocos for f in bloco.faixas]

    def proxima_de(self, faixa):
        """A faixa que vem depois desta na tela, ou None se ela e a ultima.

        O cronometro usa: e o que ele anuncia quando a faixa acaba ("pausa de
        10 min", "proximo: Correcao"). Atravessa os blocos - depois da ultima
        da manha vem a primeira da noite.
        """
        ordem = self.faixas_em_ordem()
        for i, f in enumerate(ordem):
            if f is faixa:
                return ordem[i + 1] if i + 1 < len(ordem) else None
        return None

    @property
    def pode_ativar_plano_b(self) -> bool:
        # Um Plano B que ja estava ativo continua podendo ser desfeito.
        return (bool(self.opcoes_do_plano_b) and self.dia is not None and not self.futuro
                and (not self.faixas_que_medem or bool(self.plano_b)))

    @property
    def e_hoje(self) -> bool:
        return self.data == self.hoje

    @property
    def futuro(self) -> bool:
        return self.data > self.hoje

    @property
    def dias_para_o_fim(self) -> int | None:
        """Quantos dias faltam, contados de HOJE (e nao do dia na tela), para
        o fim do ciclo. Negativo quando ja acabou; None sem plano."""
        if self.plano is None:
            return None
        return (self.plano.fim - self.hoje).days

    @property
    def anterior(self) -> date:
        return self.data - timedelta(days=1)

    @property
    def proximo(self) -> date:
        return self.data + timedelta(days=1)


# --- a sequencia e a frase da semana -------------------------------------------

# As metas que nao zeram o dia: qualquer uma delas mantem a sequencia.
METAS_QUE_MANTEM = {"ideal", "reduzida", "minima"}


def sequencia(plano, metas: dict[date, str], hoje: date) -> int:
    """Quantos dias do plano seguidos, de ontem para tras, nao zeraram.

    Hoje entra so se ja estiver marcado - o dia ainda nao acabou, e nao
    marcar ate agora nao e zerar. Domingo nao esta no plano, entao nao quebra
    nada; dia sem marcacao ou "nao fiz" quebra.
    """
    ultimo = hoje if hoje in metas else hoje - timedelta(days=1)
    contados = 0
    for dia in sorted(plano.dias, key=lambda d: d.data, reverse=True):
        if dia.data > ultimo:
            continue
        if metas.get(dia.data) not in METAS_QUE_MANTEM:
            break
        contados += 1
    return contados


def _o_que_sobe(plano, atual: int, proximo: int) -> str:
    """'20 questões de Direito': o que muda na noite do nivel de cima."""
    mudou = [(chave, questoes) for chave, questoes in plano.rampa[proximo].items()
             if plano.rampa[atual].get(chave) != questoes]
    if not mudou:
        return f"o nível {proximo}"
    partes = [f"{questoes} de {plano_de_estudo.NOME_DA_RAMPA.get(chave, chave)}"
              for chave, questoes in mudou]
    partes[0] = partes[0].replace(" de ", " questões de ", 1)
    return " e ".join(partes)


def frase_da_semana(plano, metas: dict[date, str], data: date, hoje: date,
                    nivel) -> str | None:
    """A frase animadora do cartao "Esta semana", para a semana de `data`.

    A MESMA regra do gatilho (cronograma.niveis), com os numeros do YAML: a
    semana sobe com `sobe_com_dias_na_ideal` dias completos e nenhum zerado,
    e feriado feito como Minima ou melhor conta como completo. "Dia completo"
    e o nome na tela do que o codigo chama de "ideal".

    Dia que ja passou sem marcacao conta como perdido: "restantes" sao os
    dias ainda sem marcacao de hoje em diante. Semana futura, fora do ciclo
    ou a ultima do ciclo abaixo do teto (nao ha "semana que vem" para subir):
    None, e a frase some.
    """
    gravado = plano.dia(data)
    if gravado is None or nivel is None:
        return None
    dias = [d for d in plano.dias if d.semana == gravado.semana]
    if min(d.data for d in dias) > hoje:
        return None

    teto = max(plano.rampa)
    if nivel.efetivo >= teto:
        return "💪 Você está na carga máxima do ciclo. Mantenha!"
    if gravado.semana >= max(d.semana for d in plano.dias):
        return None

    sobe = plano.gatilho["sobe_com_dias_na_ideal"]
    completos = zerados = restantes = 0
    for dia in dias:
        meta = metas.get(dia.data)
        if meta == "ideal" or (dia.feriado and meta in plano_de_estudo.METAS_QUE_SALVAM_O_FERIADO):
            completos += 1
        elif meta == "nao_fiz":
            zerados += 1
        elif meta is None and dia.data >= hoje:
            restantes += 1

    proximo = nivel.efetivo + 1
    faltam = sobe - completos
    if faltam <= 0 and not zerados:
        return f"✅ Semana garantida! A próxima sobe para o nível {proximo}."
    if zerados or faltam > restantes:
        return ("Essa semana não sobe mais, mas cada dia feito mantém a sua "
                "sequência. Bora!")
    carga_de_cima = _o_que_sobe(plano, nivel.efetivo, proximo)
    if not completos:
        # Segunda de manha, nada marcado: "0 dias completos!" nao anima ninguem.
        return f"🔥 Faça {sobe} dias completos e a semana que vem sobe para {carga_de_cima}."
    dias_completos = f"{completos} dia completo" if completos == 1 else f"{completos} dias completos"
    return f"🔥 {dias_completos}! Mais {faltam} e a semana que vem sobe para {carga_de_cima}."


def _metas(plano) -> dict[date, str]:
    return {d: r.meta for d, r in registros(plano.inicio, plano.fim).items()}


def metas_do_plano(plano) -> dict[date, str]:
    """{data: meta} do ciclo inteiro. O que o gatilho e a tela de Semanas leem."""
    return _metas(plano)


def hoje_do_gatilho(data: date) -> date:
    """O "hoje" que o gatilho usa para ver o dia `data`.

    Dia passado: a propria data, para mostrar a carga que valia naquele dia.
    Dia futuro: o hoje de verdade - o gatilho so sabe o que ja aconteceu, e
    as semanas que ainda nao chegaram ficam na carga do plano.
    """
    return min(data, hoje_local())


def nivel_do_dia(plano, data: date, metas: dict[date, str] | None = None):
    """O nivel da semana de `data`, ou None se o dia nao esta no plano.

    O lugar unico da conta, para a tela e o `radar hoje` nunca divergirem.
    """
    gravado = plano.dia(data)
    if gravado is None:
        return None
    if metas is None:
        metas = _metas(plano)
    return plano_de_estudo.niveis(plano, metas, hoje_do_gatilho(data))[gravado.semana]


def _montado(plano, data: date, metas: dict[date, str]):
    """O dia com o nivel efetivo da semana dele, como o `radar hoje` mostra."""
    nivel = nivel_do_dia(plano, data, metas)
    if nivel is None:
        return None, None
    return plano_de_estudo.montar_dia(plano, data, nivel.efetivo), nivel


def _agora(dia, hora: time) -> Agora:
    faixas = dia.faixas()
    if not faixas or hora < faixas[0].inicio:
        return Agora("antes", proxima=faixas[0] if faixas else None)
    atual, proxima = plano_de_estudo.faixa_atual(dia, hora)
    if atual is not None:
        return Agora("faixa", atual=atual, proxima=proxima)
    if proxima is not None:
        return Agora("entre", proxima=proxima)
    return Agora("fim")


def mapa_do_ano(plano, hoje: date) -> list[PontoDoMapa]:
    """O mapa do ano sabendo onde eu estou hoje.

    "Passada" e a etapa que JA TERMINOU, e nao "a que vem antes da atual". A
    diferenca aparece no vao entre dois ciclos (o domingo entre eles): ali
    nenhuma etapa e a atual, e nem por isso a proxima virou passado.

    E sempre de HOJE, nunca do dia aberto na tela: navegar para uma
    quinta-feira de dezembro nao me move no ano.
    """
    return [PontoDoMapa(etapa, etapa.contem(hoje), etapa.terminou(hoje))
            for etapa in plano.mapa]


def tela_do_dia(data: date | None = None, caminho=None) -> TelaDoDia:
    """O que a tela "Hoje" mostra para `data` (padrao: hoje, no fuso local)."""
    relogio = agora_local()
    hoje = relogio.date()
    data = data or hoje

    try:
        plano = plano_de_estudo.carregar(caminho)
    except FileNotFoundError as erro:
        return TelaDoDia("sem_arquivo", data, hoje, mensagem=str(erro.filename))
    except plano_de_estudo.ErroNoCronograma as erro:
        return TelaDoDia("erro", data, hoje, mensagem=str(erro))

    tela = TelaDoDia("dia", data, hoje, plano=plano,
                     total_semanas=max((d.semana for d in plano.dias), default=0),
                     nome_do_alvo=alvo.principal().get("nome"))
    tela.mapa = mapa_do_ano(plano, hoje)
    metas = _metas(plano)
    # De HOJE, e nao do dia na tela: e a sequencia de verdade.
    tela.sequencia = sequencia(plano, metas, hoje)

    if data < plano.inicio:
        tela.estado = "antes"
        tela.outro_dia, _ = _montado(plano, plano.inicio, metas)
        return tela
    if data > plano.fim:
        tela.estado = "depois"
        return tela
    if data.weekday() == plano_de_estudo.DOMINGO:
        tela.estado = "domingo"
        tela.outro_dia, _ = _montado(plano, data + timedelta(days=1), metas)
        return tela

    dia, nivel = _montado(plano, data, metas)
    if dia is None:
        tela.estado = "fora"
        return tela
    tela.dia, tela.nivel = dia, nivel
    tela.frase = frase_da_semana(plano, metas, data, hoje, nivel)

    segunda = data - timedelta(days=data.weekday())
    for i in range(6):
        d = segunda + timedelta(days=i)
        if plano.dia(d) is None:
            continue
        tela.pilulas.append(Pilula(d, plano_de_estudo.DIAS_CURTOS[i],
                                   metas.get(d), d > hoje, d == data))

    for chave in plano_de_estudo.BLOCOS:
        faixas = getattr(dia, chave)
        bloco = BlocoNaTela(chave, plano.blocos[chave].nome, faixas)
        # O horario do bloco sai das faixas que valem: o Anki desligado nao
        # tem duracao, e um bloco so com ele fica sem horario.
        ativas = [f for f in faixas if not f.desligada]
        if ativas:
            bloco.inicio, bloco.fim = ativas[0].inicio, ativas[-1].fim
            bloco.questoes = sum(f.questoes or 0 for f in ativas if not f.opcional)
        tela.blocos.append(bloco)

    noite = dia.noite or dia.faixas()
    tela.fim_do_dia = noite[-1].fim if noite else None
    if tela.e_hoje:
        tela.hora = relogio.time().replace(second=0, microsecond=0)
        tela.agora = _agora(dia, tela.hora)
    tela.registro = registros(data, data).get(data)
    estado = estado_do_dia(data)
    if plano.plano_b is not None:
        tela.opcoes_do_plano_b = sorted(plano.plano_b.opcoes)
    tela.faixas_que_medem = faixas_que_medem(dia)
    if estado and estado.plano_b in tela.opcoes_do_plano_b:
        # Plano B ativo: a tela mostra SO ele. O dia vira um bloco so, e a
        # meta sugerida e sempre a Minima - e o que o Plano B e.
        tela.plano_b = estado.plano_b
        do_plano_b = plano_de_estudo.montar_plano_b(plano, data, estado.plano_b,
                                                    nivel.efetivo)
        tela.blocos = [BlocoNaTela(plano_de_estudo.BLOCO_DO_PLANO_B,
                                   "Plano B — o mínimo de hoje", do_plano_b.plano_b,
                                   questoes=do_plano_b.total_questoes)]
        tela.agora = None
        tela.feitas = faixas_feitas(do_plano_b, estado)
        tela.valores = valores_das_faixas(do_plano_b, estado)
        tela.sugestao = sugerir_meta(do_plano_b, tela.feitas)
        tela.sugestao.meta = "minima"
        tela.extras = estudo_extra.do_dia(data)
        tela.totais = _conta_do_dia(data, plano)
        return tela
    tela.feitas = faixas_feitas(dia, estado)
    tela.valores = valores_das_faixas(dia, estado)
    tela.sugestao = sugerir_meta(dia, tela.feitas)
    tela.extras = estudo_extra.do_dia(data)
    tela.totais = _conta_do_dia(data, plano)
    return tela


def _conta_do_dia(data: date, plano):
    """O "Fiz hoje", pelo `metricas` - importado aqui dentro porque ele le
    as faixas por este modulo, e os dois se importando no topo dariam um
    ciclo."""
    from radar.servico import metricas
    return metricas.do_dia(data, plano)
