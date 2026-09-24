"""A coleta: rodar as fontes, gravar sem duplicar, e classificar o que veio.

Este e o unico lugar que sabe QUE fontes existem (`COLETORES`) e como um item
vira linha no banco. Nada aqui consulta: quem pergunta "o que existe?" e o
`servico` propriamente dito.

A regra que manda no arquivo: a coleta escreve so o que e dela. Os campos que
sao meus - favorito, notas, salario digitado, municipio confirmado - passam
intactos por cima de qualquer coleta.
"""
import logging
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import select

from radar import eventos as linha_do_tempo
from radar import regioes
from radar.classificador import classificar
from radar.collectors.base import Coletor, ItemColetado
from radar.collectors.concursos_no_brasil import MAXIMO_DE_PAGINAS, ConcursosNoBrasil
from radar.collectors.fepese import Fepese
from radar.collectors.ieses import Ieses
from radar.db import criar_tabelas, sessao
from radar.models import Concurso, agora

log = logging.getLogger(__name__)


# Registre aqui cada coletor novo. E o unico lugar que precisa saber a lista.
COLETORES: list[type[Coletor]] = [ConcursosNoBrasil, Fepese, Ieses]

# Campos que a coleta manda. O que NAO esta aqui e seu e nunca e sobrescrito:
# interesse, notas, e o que voce corrigir a mao no banco.
CAMPOS_DA_FONTE = (
    "titulo", "resumo", "orgao", "municipio", "uf", "banca", "situacao",
    "escolaridade", "publicado_em",
)

# O que a fonte manda quando NAO sabe. Tratado como se fosse nulo: nao
# sobrescreve o que ja descobrimos por outro caminho.
VALORES_SEM_INFORMACAO = {
    "situacao": ("desconhecida",),
}

# Campos que o classificador calcula. Sao derivados do titulo, entao podem ser
# recalculados a qualquer momento - e por isso que existe `reclassificar()`:
# se eu editar config/regioes.yml, o banco inteiro se corrige sem recoletar.
CAMPOS_CALCULADOS = ("municipio", "salario", "tipo", "relevancia",
                     "motivo_relevancia", "alvo", "motivo_alvo")


def _anel_da_lotacao(municipio: str | None) -> tuple[str, str]:
    """(anel, motivo) para o municipio que a pagina do edital confirmou.

    O motivo diz de onde veio o municipio - e a informacao que me permite
    auditar a classificacao depois, e a pagina do edital e fonte melhor que o
    titulo. O anel sai da regra de hoje, e nao de quando a pagina foi lida.
    """
    nome = regioes.nome_canonico(municipio) or municipio
    anel = regioes.anel_de(municipio)

    if anel:
        return anel, (
            f"{nome} aparece como lotação na página do edital, "
            f"e está no anel {regioes.NOME_DO_ANEL.get(anel, anel)}."
        )

    # Municipio conhecido e fora dos aneis: a pagina disse onde e, e o lugar
    # simplesmente nao me serve. Isso e `remoto`, e nao `indefinida` - nao ha
    # duvida nenhuma sobre onde fica.
    return regioes.REMOTO, (
        f"{nome} aparece como lotação na página do edital, "
        f"e fica fora dos anéis de config/regioes.yml."
    )


def _aplicar_classificacao(destino, item: ItemColetado) -> None:
    """Aplica o que da para saber pelo TITULO, sem pisar em fonte melhor.

    Duas coisas o classificador nao encosta, porque vieram de onde se sabe
    mais: o salario que eu digitei, e o MUNICIPIO que saiu da pagina do
    edital. Sem essa trava, um `radar reclassificar` desfazia o trabalho do
    `radar detalhar` - a SEFAZ SC voltava de `nucleo` para `indefinida`,
    porque "Concurso SEFAZ (SC)" nao tem municipio no titulo.

    A trava para no municipio. O anel e o motivo sao CONTA feita em cima dele,
    e conta se refaz: eles saem do `config/regioes.yml` de hoje, mesmo quando
    o municipio veio da pagina.
    """
    resultado = classificar(item)
    destino.tipo = resultado.tipo

    # A marca de alvo sai so do texto, e nao existe fonte melhor para ela:
    # nenhum edital diz se o cargo e o que eu quero. Por isso ela e sempre
    # reescrita, sem a trava de municipio_confirmado.
    destino.alvo = resultado.alvo
    destino.motivo_alvo = resultado.motivo_alvo

    if not destino.salario_manual:
        destino.salario = resultado.salario

    if destino.municipio_confirmado:
        # A trava protege o MUNICIPIO, e so ele: ele veio da pagina do edital,
        # que sabe mais que o titulo. O anel e o motivo sao conta, e conta se
        # refaz - com o `config/regioes.yml` de hoje.
        #
        # Protege-los junto era demais: tirar Blumenau do anel `proximo` nao
        # mexia nos concursos cuja lotacao a pagina tinha confirmado, e eles
        # ficavam `proximo` para sempre, com o motivo da regra antiga.
        destino.relevancia, destino.motivo_relevancia = _anel_da_lotacao(
            destino.municipio
        )
    else:
        destino.municipio = resultado.municipio
        destino.relevancia = resultado.relevancia
        destino.motivo_relevancia = resultado.motivo
    # O coletor marca tudo como edital_publicado porque nao sabe distinguir.
    # Se nem concurso e, nao da para afirmar que ha edital.
    if resultado.tipo == "noticia":
        destino.situacao = "desconhecida"
    elif resultado.fase and destino.inscricoes_ate is None:
        # Fase anterior ao edital, dita pelo titulo. So vale enquanto nao ha
        # prazo conhecido: data de inscricao e fato, titulo e interpretacao.
        destino.situacao = resultado.fase


@dataclass
class ResultadoColeta:
    fonte: str
    novos: int = 0
    atualizados: int = 0
    erro: str | None = None

    def __str__(self) -> str:
        if self.erro:
            return f"{self.fonte}: FALHOU ({self.erro})"
        return f"{self.fonte}: {self.novos} novo(s), {self.atualizados} atualizado(s)"


def _gravar(s, item: ItemColetado, fonte: str) -> str:
    """Insere ou atualiza um item. Devolve 'novo' ou 'atualizado'.

    A url e a chave: se ela ja existe, e o mesmo concurso e o registro e
    atualizado. O esboco antigo so pulava - e ai um concurso que mudasse de
    'inscricoes_abertas' para 'encerrado' ficava errado no banco para sempre.
    """
    existente = s.scalar(select(Concurso).where(Concurso.url == item.url))

    if existente is None:
        novo = Concurso(url=item.url, fonte=fonte, extra=item.extra or {})
        for campo in CAMPOS_DA_FONTE:
            setattr(novo, campo, getattr(item, campo))
        _aplicar_classificacao(novo, item)
        s.add(novo)
        # A situacao vai junto porque o concurso raramente aparece no
        # comeco da vida: quando o radar liga, muita coisa ja esta com a
        # inscricao aberta. Sem isso a linha do tempo comecaria dizendo so
        # "apareceu", sem dizer em que pe.
        linha_do_tempo.registrar(
            s, novo.url, linha_do_tempo.APARECEU,
            f"Entrou no radar pela fonte {fonte}, como {novo.situacao}",
            novo.url,
        )
        return "novo"

    # Guardado ANTES de qualquer escrita: a situacao pode mudar por dois
    # caminhos daqui para baixo - o valor que a fonte manda, e a fase que o
    # classificador le no titulo. Comparar no fim pega os dois de uma vez,
    # sem espalhar registro de evento pelo meio da funcao.
    situacao_antes = existente.situacao
    prova_antes = existente.data_prova

    mudou = False
    for campo in CAMPOS_DA_FONTE:
        valor = getattr(item, campo)
        # None da fonte nao apaga dado que ja temos: uma coleta incompleta nao
        # pode piorar o registro. "desconhecida" na situacao e a mesma coisa -
        # e o valor padrao de quem NAO sabe, e nao pode rebaixar um status que
        # ja tinhamos descoberto por outro caminho.
        if valor is None or valor in VALORES_SEM_INFORMACAO.get(campo, ()):
            continue
        # A situacao que a fonte manda nao desmente o PRAZO, pela mesma regra
        # que ja vale para a fase lida do titulo: data de inscricao e fato.
        #
        # Sem isto o radar entrava em looping: o coletor do Concursos no
        # Brasil marca "edital_publicado" em TODO item, porque o feed dele nao
        # distingue fase; a coleta gravava isso por cima de um concurso ja
        # encerrado, e o `atualizar_situacoes` do fim da mesma rodada
        # desfazia. Dois eventos por coleta, todo dia, para sempre - e desde a
        # etapa 8 os dois viram mensagem no Telegram.
        if campo == "situacao" and existente.inscricoes_ate is not None:
            continue
        if valor == getattr(existente, campo):
            continue
        setattr(existente, campo, valor)
        mudou = True

    if item.extra and item.extra != (existente.extra or {}):
        existente.extra = {**(existente.extra or {}), **item.extra}
        mudou = True

    _aplicar_classificacao(existente, item)

    linha_do_tempo.registrar_mudanca_de_situacao(
        s, existente.url, situacao_antes, existente.situacao, existente.url
    )
    if existente.data_prova and existente.data_prova != prova_antes:
        linha_do_tempo.registrar_prova_marcada(
            s, existente.url, existente.data_prova, existente.url
        )

    if mudou:
        existente.atualizado_em = agora()
    return "atualizado" if mudou else "sem_mudanca"


def coletar_tudo() -> list[ResultadoColeta]:
    """Roda todos os coletores.

    Se uma fonte cair ou mudar de formato, ela e registrada como erro e as
    outras seguem. Uma fonte fora do ar nunca derruba a coleta inteira.
    """
    criar_tabelas()
    resultados: list[ResultadoColeta] = []

    for classe in COLETORES:
        resultado = ResultadoColeta(fonte=classe.nome)
        try:
            itens = classe().coletar()
            with sessao() as s:
                for item in itens:
                    situacao = _gravar(s, item, classe.nome)
                    if situacao == "novo":
                        resultado.novos += 1
                    elif situacao == "atualizado":
                        resultado.atualizados += 1
        except Exception as erro:  # noqa: BLE001 - de proposito: loga e segue
            # Uma linha no log normal; o traceback inteiro so em modo debug.
            # Fonte fora do ar e rotina, nao merece 40 linhas todo dia.
            log.warning("coletor %s falhou: %s", classe.nome, erro)
            log.debug("detalhe da falha em %s", classe.nome, exc_info=True)
            resultado.erro = f"{type(erro).__name__}: {erro}"

        resultados.append(resultado)

    atualizar_situacoes()
    return resultados


def _tem_acento(nome: str) -> bool:
    return regioes.normalizar(nome) != nome.lower()


def _nota_da_grafia(nome: str, vezes: int) -> tuple:
    """Quanto essa grafia merece ser a escolhida. Maior ganha.

    A ordem das notas e a regra, escrita uma vez: acento vale mais que tudo,
    porque ele e informacao - "Caçador" sem cedilha e a mesma cidade escrita
    pior. Depois vem a caixa normal, que descarta o "GASPAR" que a fonte
    manda em maiuscula. So entao o desempate pelo que aparece mais vezes, e
    por fim a ordem alfabetica, para duas execucoes darem o mesmo resultado.
    """
    return (_tem_acento(nome), not nome.isupper() and not nome.islower(),
            vezes, nome)


def melhor_grafia(nomes) -> dict[str, str]:
    """{normalizado: a grafia que vale} para os municipios que aparecem aqui.

    A mesma cidade chega escrita de varios jeitos - "Caçador" e "Cacador",
    "GASPAR" e "Gaspar", "Araranguá" e "Ararangua" - porque cada fonte digita
    de um jeito. Para quem esta nos aneis, `config/regioes.yml` resolve; para
    o resto nao ha lista, entao quem decide e o proprio banco: entre as
    grafias que existem, vale a melhor.

    E so cosmetico. Duas grafias do mesmo lugar nunca confundiram a
    classificacao, porque toda comparacao passa por `normalizar`.
    """
    from collections import Counter

    vezes = Counter(n for n in nomes if n)
    escolhidas: dict[str, str] = {}
    for nome, quantas in vezes.items():
        chave = regioes.normalizar(nome)
        atual = escolhidas.get(chave)
        if atual is None or _nota_da_grafia(nome, quantas) > _nota_da_grafia(
            atual, vezes[atual]
        ):
            escolhidas[chave] = nome
    return escolhidas


def reclassificar() -> dict[str, int]:
    """Roda o classificador de novo em todo o banco, sem ir a internet.

    Use depois de editar config/regioes.yml: os registros antigos passam a
    respeitar a regra nova na hora.
    """
    criar_tabelas()
    contagem: dict[str, int] = {}

    with sessao() as s:
        # A melhor grafia sai do banco inteiro, e por isso e decidida ANTES do
        # laco: dentro dele eu so veria os municipios ja visitados.
        grafias = melhor_grafia(
            regioes.nome_canonico(m)
            for (m,) in s.execute(select(Concurso.municipio).distinct())
            if m
        )

        for concurso in s.scalars(select(Concurso)):
            item = ItemColetado(
                titulo=concurso.titulo,
                url=concurso.url,
                resumo=concurso.resumo,
                uf=concurso.uf,
                # O municipio e o tipo ja conhecidos vao junto. Sem eles, os
                # concursos da FEPESE perdiam o municipio a cada reclassificar:
                # o titulo dela e "2026 - Prefeitura Municipal de Sao Jose",
                # sem "(SC)", e o extrator do classificador precisa da UF entre
                # parenteses. "Perto de mim" caia de 176 para 69.
                #
                # Reclassificar existe para reaplicar a regra do ANEL, e nao
                # para reextrair o que outra fonte ja extraiu melhor.
                municipio=concurso.municipio,
                tipo=concurso.tipo if concurso.tipo != "desconhecido" else None,
                # A banca vai junto so para o motivo do alvo poder dizer que
                # e a mesma das edicoes anteriores. Ela nao marca nada.
                banca=concurso.banca,
            )
            _aplicar_classificacao(concurso, item)

            # Grafia canonica mesmo no municipio confirmado pela pagina do
            # edital: trocar "Palhoca" por "Palhoca" com cedilha nao e
            # reclassificar, e escrever o mesmo municipio de um jeito so.
            #
            # Para quem esta nos aneis, quem manda e o regioes.yml. Para o
            # resto nao ha lista, e ai vale a melhor grafia que o proprio
            # banco tem: e o que faz "Cacador" e "Caçador" pararem de ser
            # duas cidades na tela.
            canonico = regioes.nome_canonico(concurso.municipio)
            if concurso.municipio:
                concurso.municipio = grafias.get(
                    regioes.normalizar(concurso.municipio), canonico
                )

            contagem[concurso.relevancia] = contagem.get(concurso.relevancia, 0) + 1

    return contagem


# --- carga inicial (fase 1.6) -----------------------------------------------

# Medido no site real em 17/09/2026: 15 itens por pagina, e paged=60 chegou a
# 37 dias atras - cerca de 1,6 pagina por dia. Usamos 3 por dia, que da o
# dobro de folga caso o site publique mais num periodo movimentado. Quem manda
# de verdade na parada e a data; isto aqui e so o teto.
PAGINAS_POR_DIA = 3


def _marcar_historico_como_avisado() -> int:
    """Encerra a fila de avisos depois da carga inicial.

    Sem isto, trazer 90 dias de historico enche a fila com centenas de
    concursos antigos, e o `radar avisar` seguinte manda 10 mensagens sobre
    editais de junho - a maioria com inscricao ja encerrada - mais o alerta de
    excesso, que soaria como erro de regra sem ser.

    Carga inicial e historico, nao novidade: quem chega por ela se ve na
    pagina e na lista. A partir daqui, so a coleta diaria gera aviso.
    """
    consulta = select(Concurso).where(Concurso.avisado_em.is_(None))
    marcados = 0
    with sessao() as s:
        for concurso in s.scalars(consulta):
            concurso.avisado_em = agora()
            marcados += 1
    return marcados


def carga_inicial(dias: int = 90) -> ResultadoColeta:
    """Anda para tras no feed e traz o historico que a coleta diaria perdeu.

    O RSS e um fluxo: ele so mostra o que e recente. Quem liga o radar hoje ve
    os concursos de hoje, e nada do que foi publicado antes. Esta funcao
    resolve isso uma vez, lendo o feed pagina por pagina.

    Roda uma vez so, na mao. Nao entra na coleta diaria.
    """
    criar_tabelas()

    desde = agora() - timedelta(days=dias)
    paginas = min(dias * PAGINAS_POR_DIA, MAXIMO_DE_PAGINAS)

    resultado = ResultadoColeta(fonte=ConcursosNoBrasil.nome)
    try:
        itens = ConcursosNoBrasil(paginas=paginas, desde=desde).coletar()
        with sessao() as s:
            for item in itens:
                situacao = _gravar(s, item, ConcursosNoBrasil.nome)
                if situacao == "novo":
                    resultado.novos += 1
                elif situacao == "atualizado":
                    resultado.atualizados += 1

        _marcar_historico_como_avisado()
    except Exception as erro:  # noqa: BLE001 - de proposito: loga e segue
        log.warning("carga inicial falhou: %s", erro)
        log.debug("detalhe da falha na carga inicial", exc_info=True)
        resultado.erro = f"{type(erro).__name__}: {erro}"

    return resultado


# --- a situacao que as datas comprovam ---------------------------------------

def _situacao_pelas_datas(concurso: Concurso, momento) -> str | None:
    """A situacao que as datas de inscricao permitem afirmar.

    Antes disto, TODO registro ficava como `edital_publicado`, porque e o
    unico palpite que o titulo permite - ou seja, o campo nao dizia nada. Com
    o prazo em maos da para ser preciso, e sem chutar: so mexe em quem tem
    data, e so entre os tres estados que a data comprova.
    """
    if concurso.tipo == "noticia" or concurso.inscricoes_ate is None:
        return None
    if momento > concurso.inscricoes_ate:
        return "encerrado"
    if concurso.inscricoes_de is None or momento >= concurso.inscricoes_de:
        return "inscricoes_abertas"
    return "edital_publicado"          # edital saiu, inscricao ainda vai abrir


def atualizar_situacoes() -> dict[str, int]:
    """Recalcula a situacao de quem tem prazo conhecido.

    Roda sozinho ao fim da coleta e do `detalhar`, e de novo quando eu chamo
    na mao - porque o tempo passa e "aberto" vira "encerrado" sem ninguem
    tocar em nada.
    """
    criar_tabelas()
    momento = agora()
    contagem: dict[str, int] = {}

    with sessao() as s:
        consulta = select(Concurso).where(Concurso.inscricoes_ate.is_not(None))
        for concurso in s.scalars(consulta):
            nova = _situacao_pelas_datas(concurso, momento)
            if nova and nova != concurso.situacao:
                # Aqui mora o unico evento que acontece sem ninguem tocar em
                # nada: o prazo vence e a inscricao fecha sozinha.
                linha_do_tempo.registrar_mudanca_de_situacao(
                    s, concurso.url, concurso.situacao, nova, concurso.url
                )
                concurso.situacao = nova
                contagem[nova] = contagem.get(nova, 0) + 1

    return contagem
