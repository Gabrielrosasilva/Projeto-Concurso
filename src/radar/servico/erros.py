"""O caderno de erros: o que eu errei, a regra certa, e quando ela volta.

A regra da revisao, inteira:

  * anotei um erro -> etapa 1, volta AMANHA;
  * "ja sei" -> proxima etapa: 7 dias, depois 30. Respondido "ja sei" na
    etapa 3, o erro esta aprendido e vai para o arquivo;
  * "ainda erro" -> volta para a etapa 1, e volta amanha. Sem meio termo:
    errar de novo depois de 30 dias e errar do zero.

Os intervalos sao os mesmos do `servico.espacada` (1-7-30), e vem de la para
nao existirem dois numeros diferentes para a mesma ideia. O que muda e a
ORIGEM: a agenda do `espacada` e calculada das respostas gravadas no radar, e
esta sai do meu julgamento - "ja sei" nao esta escrito em lugar nenhum a nao
ser aqui, e por isso aqui tem tabela.

Nada deste arquivo entra em acerto medido do radar. O caderno e diario, como
o "Como foi o dia": ele conta o que eu aprendi, nao o que a banca cobra.
"""
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import select

from radar import cronograma as plano_de_estudo
from radar.db import criar_tabelas, sessao
from radar.models import ErroAnotado, agora
from radar.servico import cronograma as diario_do_cronograma
from radar.servico.espacada import INTERVALOS

# Por que eu errei. A ordem e a da tela, e ela nao e alfabetica de proposito:
# comeca no que se resolve estudando e termina no que se resolve com calma.
MOTIVOS = {
    "nao_sabia": "Não sabia",
    "confundi": "Confundi",
    "li_errado": "Li errado",
    "pegadinha": "Pegadinha",
    "chutei": "Chutei",
}

# De onde veio a questao. O radar e o simulado sao separados porque so o
# segundo tem rodada gravada; "outro" e o PDF solto, o caderno de papel.
FONTES = {
    "qconcursos": "Qconcursos",
    "radar": "Radar",
    "simulado": "Simulado",
    "outro": "Outro",
}

# Os resultados que uma revisao pode ter. Sao os dois botoes da tela.
JA_SEI = "ja_sei"
AINDA_ERRO = "ainda_erro"
RESULTADOS = (JA_SEI, AINDA_ERRO)

# O que a lista pode mostrar. "hoje" e o padrao da tela: o caderno serve para
# rever, e nao para colecionar.
SITUACOES = {
    "hoje": "Para rever hoje",
    "todos": "Todos",
    "arquivados": "Arquivados",
}
SITUACAO_PADRAO = "hoje"

# Quantas materias e motivos o "O que mais te derruba" mostra. Mais que isso
# deixa de ser um aviso e vira tabela para estudar - e ja existe tela para isso.
NO_QUE_DERRUBA = 5

# Abaixo disto, a porcentagem por motivo nao diz nada: um erro de dois e 50%.
#
# ESTE NUMERO FICA AQUI DE PROPOSITO, e nao no config/amostra.yml com os
# minimos de desempenho (Etapa 4). Ele mede outra coisa: a FATIA de cada
# motivo dentro dos meus erros ("3 dos meus 10 erros foram por pressa"), e nao
# o meu acerto num conteudo. Sao duas perguntas com riscos diferentes - errar
# a fatia de um motivo nao me faz estudar a materia errada por meses -, e
# juntar as duas na mesma regua tornaria as duas erradas. Avaliado e mantido na
# Etapa 4; esta escrito tambem no src/radar/amostra.py.
MINIMO_PARA_A_PORCENTAGEM = 3


class ErroInvalido(ValueError):
    """O que eu mandei nao da para gravar. A mensagem diz o que falta."""


@dataclass
class Contagem:
    """Uma linha do "O que mais te derruba"."""
    nome: str
    quantos: int
    #: O motivo mais frequente DENTRO desta materia, e quantos por cento.
    motivo: str | None = None
    porcentagem: int | None = None


def _texto(valor, campo: str, obrigatorio: bool = False, limite: int = 0) -> str | None:
    texto = (valor or "").strip()
    if not texto:
        if obrigatorio:
            raise ErroInvalido(f"{campo} não pode ficar em branco.")
        return None
    return texto[:limite] if limite else texto


def anotar(
    data_estudo: date | None = None,
    materia: str = "",
    assunto: str | None = None,
    motivo: str = "",
    regra: str = "",
    fonte: str = "qconcursos",
    referencia: str | None = None,
    hoje: date | None = None,
) -> ErroAnotado:
    """Grava um erro novo. Ele volta AMANHA, na etapa 1.

    A `regra` e obrigatoria e e o coracao disto: anotar "errei a 42" nao ensina
    nada, e "prazo de progressao conta da data da prisao, nao da condenacao"
    ensina. Por isso a recusa e em voz alta, e nao um campo vazio no banco.
    """
    hoje = hoje or diario_do_cronograma.hoje_local()
    materia = _texto(materia, "A matéria", obrigatorio=True, limite=80)
    regra = _texto(regra, "A regra certa", obrigatorio=True)
    if motivo not in MOTIVOS:
        raise ErroInvalido(
            f"Motivo desconhecido: {motivo!r}. Escolha um destes: "
            f"{', '.join(MOTIVOS)}."
        )
    if fonte not in FONTES:
        raise ErroInvalido(
            f"Fonte desconhecida: {fonte!r}. Escolha uma destas: {', '.join(FONTES)}."
        )

    criar_tabelas()
    erro = ErroAnotado(
        data_estudo=data_estudo or hoje,
        materia=materia,
        assunto=_texto(assunto, "O assunto", limite=200),
        motivo=motivo,
        regra=regra,
        fonte=fonte,
        referencia=_texto(referencia, "A referência"),
        etapa=1,
        proxima_revisao=hoje + timedelta(days=INTERVALOS[0]),
        historico=[],
    )
    with sessao() as s:
        s.add(erro)
    return erro


def revisar(ident: int, resultado: str, hoje: date | None = None) -> ErroAnotado:
    """Os dois botoes da tela: "Ja sei" avanca, "Ainda erro" volta ao comeco.

    O resultado fica no `historico` junto da etapa em que eu estava. Isso e o
    que deixa ver o erro que ja voltou tres vezes para a etapa 1 - esse nao e
    problema de memoria, e regra que eu entendi errado.
    """
    hoje = hoje or diario_do_cronograma.hoje_local()
    if resultado not in RESULTADOS:
        raise ErroInvalido(f"Resultado desconhecido: {resultado!r}.")

    criar_tabelas()
    with sessao() as s:
        erro = s.get(ErroAnotado, ident)
        if erro is None:
            raise ErroInvalido(f"Não achei o erro #{ident}.")

        historico = list(erro.historico or [])
        historico.append({"data": hoje.isoformat(), "resultado": resultado,
                          "etapa": erro.etapa})
        erro.historico = historico

        if resultado == AINDA_ERRO:
            # Volta ao comeco, e desarquiva: se eu apertei "ainda erro" num
            # erro arquivado, ele nao estava aprendido.
            erro.etapa = 1
            erro.arquivado = False
            erro.proxima_revisao = hoje + timedelta(days=INTERVALOS[0])
        elif erro.etapa >= len(INTERVALOS):
            # Passou da terceira: aprendido. Sem proxima data, para ele nunca
            # mais aparecer em "para rever hoje".
            erro.arquivado = True
            erro.proxima_revisao = None
        else:
            erro.etapa += 1
            erro.proxima_revisao = hoje + timedelta(days=INTERVALOS[erro.etapa - 1])

        erro.atualizado_em = agora()
        s.add(erro)
    return erro


def semana_de(data: date) -> tuple[date, date]:
    """A segunda e o sabado da semana de `data` - a semana do cronograma.

    Domingo nao entra porque domingo nao esta no plano, e o filtro da tela
    existe para eu abrir "os erros desta semana" a partir da Revisao semanal
    do sabado.
    """
    segunda = data - timedelta(days=data.weekday())
    return segunda, segunda + timedelta(days=5)


def listar(
    materia: str | None = None,
    motivo: str | None = None,
    situacao: str = SITUACAO_PADRAO,
    semana: date | None = None,
    hoje: date | None = None,
) -> list[ErroAnotado]:
    """Os erros do caderno, filtrados como a tela pede.

    O padrao e "para rever hoje": erro com data marcada para hoje ou para
    tras (atrasado tambem e para rever) e nao arquivado. "todos" e
    "arquivados" sao as outras duas visoes.
    """
    hoje = hoje or diario_do_cronograma.hoje_local()
    criar_tabelas()

    consulta = select(ErroAnotado)
    if materia:
        consulta = consulta.where(ErroAnotado.materia == materia)
    if motivo:
        consulta = consulta.where(ErroAnotado.motivo == motivo)
    if semana is not None:
        segunda, sabado = semana_de(semana)
        consulta = consulta.where(ErroAnotado.data_estudo >= segunda,
                                  ErroAnotado.data_estudo <= sabado)

    if situacao == "arquivados":
        consulta = consulta.where(ErroAnotado.arquivado.is_(True))
    elif situacao == "hoje":
        consulta = consulta.where(
            ErroAnotado.arquivado.is_(False),
            ErroAnotado.proxima_revisao.is_not(None),
            ErroAnotado.proxima_revisao <= hoje,
        )

    with sessao() as s:
        erros = list(s.scalars(consulta))

    # O atrasado primeiro, e depois o mais novo: e a ordem em que eu quero
    # atacar. `date.max` poe o arquivado (sem data) no fim.
    return sorted(
        erros,
        key=lambda e: (e.proxima_revisao or date.max, -(e.id or 0)),
    )


def para_rever(hoje: date | None = None) -> list[ErroAnotado]:
    """O que esta vencido hoje. E o que ganha os dois botoes na tela."""
    return listar(situacao="hoje", hoje=hoje)


def quantos_para_rever(hoje: date | None = None) -> int:
    """So o numero, para o cartao da tela Hoje. Some quando e zero."""
    return len(para_rever(hoje))


def esta_para_rever(erro: ErroAnotado, hoje: date) -> bool:
    """Este erro esta vencido? E o que decide os botoes de cada linha."""
    return (not erro.arquivado and erro.proxima_revisao is not None
            and erro.proxima_revisao <= hoje)


def o_que_mais_derruba(erros: list[ErroAnotado]) -> tuple[list[Contagem], list[Contagem]]:
    """As duas contagens do topo da tela: por materia e por motivo.

    Na contagem por materia vai junto o motivo que mais aparece DENTRO dela,
    que e a frase que eu quero ler: "LEP: 40% dos erros sao pegadinha". A
    porcentagem so sai com base minima - de dois erros, um e 50%, e 50% de
    dois nao e um padrao.
    """
    por_materia: dict[str, dict[str, int]] = {}
    por_motivo: dict[str, int] = {}
    for erro in erros:
        motivos = por_materia.setdefault(erro.materia, {})
        motivos[erro.motivo] = motivos.get(erro.motivo, 0) + 1
        por_motivo[erro.motivo] = por_motivo.get(erro.motivo, 0) + 1

    materias = []
    for nome, motivos in por_materia.items():
        quantos = sum(motivos.values())
        principal, vezes = max(motivos.items(), key=lambda item: (item[1], item[0]))
        mostra = quantos >= MINIMO_PARA_A_PORCENTAGEM
        materias.append(Contagem(
            nome=nome,
            quantos=quantos,
            motivo=MOTIVOS.get(principal, principal) if mostra else None,
            porcentagem=round(100 * vezes / quantos) if mostra else None,
        ))

    materias.sort(key=lambda c: (-c.quantos, c.nome))
    motivos = sorted(
        (Contagem(MOTIVOS.get(chave, chave), quantos)
         for chave, quantos in por_motivo.items()),
        key=lambda c: (-c.quantos, c.nome),
    )
    return materias[:NO_QUE_DERRUBA], motivos[:NO_QUE_DERRUBA]


def materias_do_caderno() -> list[str]:
    """As materias que JA tem erro anotado, para o filtro da lista."""
    criar_tabelas()
    with sessao() as s:
        nomes = s.scalars(select(ErroAnotado.materia).distinct()).all()
    return sorted(nome for nome in nomes if nome)


def materias_sugeridas() -> list[str]:
    """As materias do cronograma, para o formulario sugerir em vez de exigir.

    Sai do config/cronograma.yml porque e la que moram as materias que eu
    estudo de verdade. Arquivo faltando ou com problema nao pode derrubar o
    formulario: sem sugestao, o campo continua sendo texto livre.
    """
    try:
        plano = plano_de_estudo.carregar()
    except (FileNotFoundError, plano_de_estudo.ErroNoCronograma):
        return []
    nomes = {f.materia for dia in plano.dias for f in dia.faixas() if f.materia}
    return sorted(nomes)
