"""A aba Concursos > Acompanhando: um cartao por carreira (decisao 141).

Quem e de qual carreira sai do `radar/acompanhamentos.py`; este arquivo
monta o resto - a situacao, os marcos, as novidades com o 🔔, o "visto", o
botao "Verificar atualizacoes" e a pesquisa do Claude Code - e guarda o que
nao cabe no banco em `data/acompanhamentos.json`.

As regras de precisao, que valem para o arquivo inteiro:

  * **novidade e FATO, nao noticia.** So acende o 🔔 o que a linha do tempo
    registrou como mudanca (o concurso apareceu, mudou de situacao, saiu
    edital, abriu inscricao, marcou prova, retificou) ou o que a pesquisa do
    Claude Code trouxe como fato confirmado, com link. Item que o
    classificador chamou de noticia vai para o historico, sem 🔔;
  * **todo fato tem data, link e selo.** 🟢 quando veio da propria banca,
    🟡 quando veio do site de noticias, 🟣 quando veio da pesquisa do Claude
    Code - e ai ele diz "por conferir" ate eu conferir;
  * **rumor nunca muda nada.** Texto de previsao ("deve sair", "pode abrir")
    entra como "nao confirmado": fica no historico, nao acende o 🔔, nao
    preenche marco e nao vai para o Telegram;
  * **nada de data chutada.** Marco sem fonte e "aguardando";
  * **a pesquisa nunca mexe no banco.** Ela nao muda a situacao de concurso
    nenhum: so o que a coleta le na fonte faz isso.
"""
import hashlib
import json
import logging
import re
import threading
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from pathlib import Path

from sqlalchemy import select

from radar import acompanhamentos as carreiras
from radar import config
from radar import eventos as linha_do_tempo
from radar.db import criar_tabelas, sessao
from radar.models import Concurso, Evento, agora
from radar.origem import IA, NOTICIA, OFICIAL
from radar.regioes import normalizar
from radar.util import formatar_data, fuso_local

log = logging.getLogger(__name__)


def caminho() -> Path:
    return config.diretorio_dados() / "acompanhamentos.json"


# O botao roda a coleta numa thread, e a tela pode ler o arquivo no meio.
# Uma trava so para as duas coisas: escrever o arquivo e rodar a verificacao.
_TRAVA_DO_ARQUIVO = threading.Lock()
_VERIFICANDO = threading.Lock()


def _ler() -> dict:
    arquivo = caminho()
    if not arquivo.exists():
        return {}
    try:
        return json.loads(arquivo.read_text(encoding="utf-8")) or {}
    except json.JSONDecodeError:
        # Arquivo quebrado nao pode derrubar a aba: ela mostra o que a coleta
        # sabe, sem o "visto" e sem a pesquisa, e o log diz o que houve.
        log.warning("data/acompanhamentos.json ilegivel; seguindo sem ele")
        return {}


def _alterar(mudanca) -> dict:
    """Le, aplica `mudanca(dados)` e grava, tudo dentro da trava."""
    with _TRAVA_DO_ARQUIVO:
        dados = _ler()
        mudanca(dados)
        arquivo = caminho()
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        arquivo.write_text(
            json.dumps(dados, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return dados


def _momento(texto) -> datetime | None:
    if not texto:
        return None
    try:
        valor = datetime.fromisoformat(str(texto))
    except ValueError:
        return None
    return valor if valor.tzinfo else valor.replace(tzinfo=fuso_local())


def _inicio_do_dia(dia: date | None) -> datetime | None:
    if dia is None:
        return None
    return datetime.combine(dia, time(0), tzinfo=fuso_local())


def _quando(concurso: Concurso) -> datetime:
    return concurso.publicado_em or concurso.coletado_em


# --- o que vai na tela ----------------------------------------------------------

#: Os tipos de evento que sao FATO de concurso. `apareceu` entra so quando o
#: item e concurso (o site publicou o concurso); de noticia, ele e historico.
FATOS = (
    linha_do_tempo.APARECEU,
    linha_do_tempo.MUDOU_SITUACAO,
    linha_do_tempo.EDITAL_PUBLICADO,
    linha_do_tempo.EDITAL_RETIFICADO,
    linha_do_tempo.INSCRICOES_ABERTAS,
    linha_do_tempo.INSCRICOES_ENCERRADAS,
    linha_do_tempo.PROVA_MARCADA,
)

#: O que a coleta chama de "nao e concurso". Nao diz situacao de edicao
#: nenhuma, e nao acende o 🔔.
TIPOS_SEM_SITUACAO = ("noticia", "seletivo")

#: As situacoes em que o edital ja saiu.
COM_EDITAL = ("edital_publicado", "inscricoes_abertas", "encerrado")

#: "2019 – Secretaria de Estado..." - o titulo da FEPESE comeca pelo ano do
#: concurso, e a pagina de 2019 foi republicada em 2024. Sem olhar o ano, ela
#: passava por edicao atual so por ter data recente.
ANO_NO_TITULO = re.compile(r"^\s*(\d{4})\s*[–—-]")


@dataclass
class Linha:
    """Uma linha de novidade ou de historico: um fato, com data, selo e link."""

    data: datetime
    texto: str
    selo: str
    link: str | None = None
    #: O titulo do item da coleta, quando o fato e de um item.
    item: str | None = None
    #: So na pesquisa do Claude Code: o id, para os botoes de conferir.
    pesquisa: str | None = None
    #: "por conferir", "conferida", "não confere" ou "não confirmado".
    estado: str | None = None
    #: Fato (acende o 🔔) ou so historico.
    fato: bool = True
    #: Quando o radar ficou sabendo, se for diferente de `data`: a pesquisa
    #: traz fato de semana passada, e ela e novidade no dia em que chega.
    chegou: datetime | None = None

    @property
    def momento_da_novidade(self) -> datetime:
        return self.chegou or self.data


@dataclass
class Marco:
    """Banca, edital, inscricoes ou prova: o valor, ou "aguardando"."""

    nome: str
    valor: str = "aguardando"
    selo: str | None = None
    link: str | None = None

    @property
    def sabido(self) -> bool:
        return self.selo is not None


@dataclass
class Cartao:
    nome: str
    #: A situacao em palavras, ou a frase de quando nao ha item recente.
    situacao: str
    #: O item que disse a situacao (None quando nao ha).
    referencia: Linha | None = None
    marcos: list[Marco] = field(default_factory=list)
    #: O que eu ainda nao vi, do mais novo para o mais velho.
    novidades: list[Linha] = field(default_factory=list)
    historico: list[Linha] = field(default_factory=list)
    itens: int = 0
    visto_em: datetime | None = None


def _selo_do_item(concurso: Concurso) -> str:
    oficiais = carreiras.regras().fontes_oficiais
    return OFICIAL if (concurso.fonte or "").lower() in oficiais else NOTICIA


def _edicao_antiga(concurso: Concurso, hoje: date) -> bool:
    achado = ANO_NO_TITULO.match(concurso.titulo or "")
    return bool(achado) and int(achado.group(1)) < hoje.year - 1


def _referencia(itens: list[Concurso], hoje: date) -> Concurso | None:
    """O item que diz a situacao da edicao de agora, ou None.

    O mais recente que e concurso, dentro da janela do YAML e sem ano velho
    no titulo. Item mais antigo e de outra edicao: o edital de 2019 nao diz
    nada sobre o proximo, e dizer "edital publicado" por causa dele seria
    exatamente o chute que a tela nao pode dar.
    """
    janela = _inicio_do_dia(hoje) - timedelta(
        days=carreiras.regras().janela_da_edicao_em_dias)
    candidatos = [
        c for c in itens
        if c.tipo not in TIPOS_SEM_SITUACAO
        and _quando(c) >= janela
        and not _edicao_antiga(c, hoje)
    ]
    return max(candidatos, key=_quando) if candidatos else None


def _pesquisas_que_valem(pesquisas: list[dict], marco: str) -> dict | None:
    """A pesquisa CONFERIDA e confirmada mais nova deste marco, ou None."""
    validas = [p for p in pesquisas
               if p.get("marco") == marco and p.get("confirmado")
               and p.get("conferida") == "ok"]
    return max(validas, key=lambda p: p.get("data") or "") if validas else None


def _marco_da_pesquisa(nome: str, pesquisa: dict | None) -> Marco:
    if pesquisa is None:
        return Marco(nome)
    valor = (pesquisa.get("valor") or pesquisa.get("descricao") or "").strip()
    return Marco(nome, valor, IA, pesquisa.get("link"))


def _marcos(ref: Concurso | None, pesquisas: list[dict]) -> list[Marco]:
    """Os quatro marcos. O item de referencia manda; sem ele, a pesquisa que
    eu ja conferi; sem as duas, "aguardando"."""
    selo = _selo_do_item(ref) if ref else None
    link = ref.url if ref else None

    if ref and ref.banca:
        banca = Marco("Banca", ref.banca, selo, link)
    else:
        banca = _marco_da_pesquisa("Banca", _pesquisas_que_valem(pesquisas, "banca"))

    if ref and ref.situacao in COM_EDITAL:
        quando = f" em {formatar_data(ref.publicado_em)}" if ref.publicado_em else ""
        edital = Marco("Edital", f"publicado{quando}", selo, link)
    else:
        edital = _marco_da_pesquisa("Edital", _pesquisas_que_valem(pesquisas, "edital"))

    if ref and ref.inscricoes_ate:
        if ref.inscricoes_de:
            prazo = f"{formatar_data(ref.inscricoes_de)} a {formatar_data(ref.inscricoes_ate)}"
        else:
            prazo = f"até {formatar_data(ref.inscricoes_ate)}"
        inscricoes = Marco("Inscrições", prazo, selo, link)
    else:
        inscricoes = _marco_da_pesquisa(
            "Inscrições", _pesquisas_que_valem(pesquisas, "inscricoes"))

    if ref and ref.data_prova:
        prova = Marco("Prova", formatar_data(ref.data_prova), selo, link)
    else:
        prova = _marco_da_pesquisa("Prova", _pesquisas_que_valem(pesquisas, "prova"))

    return [banca, edital, inscricoes, prova]


def _linha_do_evento(evento: Evento, concurso: Concurso) -> Linha:
    fato = (evento.tipo in FATOS and concurso.tipo != "noticia")
    return Linha(
        data=evento.data,
        texto=linha_do_tempo.para_tela(evento.descricao) or evento.descricao,
        selo=_selo_do_item(concurso),
        link=evento.link or concurso.url,
        item=concurso.titulo,
        fato=fato,
        estado=None if fato else "notícia",
    )


def _estado_da_pesquisa(p: dict) -> str:
    if not p.get("confirmado"):
        return "não confirmado"
    if p.get("conferida") == "ok":
        return "conferida"
    if p.get("conferida") == "recusada":
        return "não confere"
    return "por conferir"


def _linha_da_pesquisa(p: dict) -> Linha:
    estado = _estado_da_pesquisa(p)
    data = _momento(p.get("data")) or _momento(p.get("criado_em")) or agora()
    fonte = p.get("fonte") or "fonte não informada"
    tipo = "oficial" if p.get("tipo_de_fonte") == "oficial" else "notícia"
    return Linha(
        data=data,
        texto=f"{p.get('descricao', '')} ({fonte}, {tipo})",
        selo=IA,
        link=p.get("link"),
        pesquisa=p.get("id"),
        estado=estado,
        fato=estado in ("por conferir", "conferida"),
        chegou=_momento(p.get("criado_em")),
    )


def _sem_repetir(linhas: list[Linha]) -> list[Linha]:
    """Uma linha por link, a mais nova: o mesmo item com tres eventos no dia
    em que apareceu e UMA novidade, e nao tres."""
    vistos: set[str] = set()
    unicas = []
    for linha in sorted(linhas, key=lambda x: x.data, reverse=True):
        chave = linha.link or f"{linha.texto}|{linha.data.isoformat()}"
        if chave in vistos:
            continue
        vistos.add(chave)
        unicas.append(linha)
    return unicas


#: Quantas linhas o historico de um cartao mostra. O resto continua no banco
#: e na aba Concursos; o cartao e para o que importa agora.
LINHAS_NO_HISTORICO = 30


def cartoes(hoje: date | None = None) -> list[Cartao]:
    """Um cartao por carreira do YAML, na ordem: a principal, depois quem tem
    novidade, depois a ordem do arquivo."""
    criar_tabelas()
    hoje = hoje or agora().astimezone(fuso_local()).date()
    regras = carreiras.regras()
    dados = _ler()
    vistos = dados.get("visto") or {}
    pesquisas = dados.get("pesquisas") or []
    desde = _inicio_do_dia(regras.novidades_desde)

    with sessao() as s:
        todos = list(s.scalars(select(Concurso)))
        por_carreira = {a.nome: [c for c in todos if carreiras.casa(a, c)]
                        for a in regras.acompanhamentos}
        urls = {c.url for itens in por_carreira.values() for c in itens}
        eventos_por_url: dict[str, list[Evento]] = {}
        if urls:
            for evento in s.scalars(select(Evento).where(Evento.concurso_url.in_(urls))):
                eventos_por_url.setdefault(evento.concurso_url, []).append(evento)

        montados = []
        for ordem, acompanhamento in enumerate(regras.acompanhamentos):
            itens = por_carreira[acompanhamento.nome]
            minhas = [p for p in pesquisas if p.get("acompanhamento") == acompanhamento.nome]
            visto = _momento(vistos.get(acompanhamento.nome))
            corte = max([m for m in (visto, desde) if m is not None], default=None)

            linhas: list[Linha] = []
            for concurso in itens:
                eventos = eventos_por_url.get(concurso.url, [])
                if not eventos:
                    # Item que entrou antes de existir linha do tempo: aparece
                    # no historico pela data dele, e nunca como novidade.
                    texto = ("Publicado pela fonte" if concurso.publicado_em
                             else "Entrou no radar")
                    linhas.append(Linha(
                        data=_quando(concurso), texto=texto,
                        selo=_selo_do_item(concurso), link=concurso.url,
                        item=concurso.titulo, fato=False))
                for evento in eventos:
                    linhas.append(_linha_do_evento(evento, concurso))
            linhas += [_linha_da_pesquisa(p) for p in minhas]

            novidades = _sem_repetir([
                linha for linha in linhas
                if linha.fato and (corte is None or linha.momento_da_novidade > corte)
            ])
            ref = _referencia(itens, hoje)
            if ref:
                situacao = linha_do_tempo.NOME_DA_SITUACAO.get(ref.situacao, ref.situacao)
                referencia = Linha(_quando(ref), ref.titulo, _selo_do_item(ref), ref.url)
            else:
                meses = round(regras.janela_da_edicao_em_dias / 30)
                situacao = f"nenhum concurso desta carreira no radar nos últimos {meses} meses"
                referencia = None

            cartao = Cartao(
                nome=acompanhamento.nome,
                situacao=situacao,
                referencia=referencia,
                marcos=_marcos(ref, minhas),
                novidades=novidades,
                historico=sorted(linhas, key=lambda x: x.data, reverse=True)[:LINHAS_NO_HISTORICO],
                itens=len(itens),
                visto_em=visto,
            )
            principal = acompanhamento.cargo == carreiras.PRINCIPAL
            montados.append(((0 if principal else 1, 0 if novidades else 1, ordem), cartao))

    return [cartao for _, cartao in sorted(montados, key=lambda par: par[0])]


def marcar_visto(nome: str, quando: datetime | None = None) -> bool:
    """O 🔔 deste cartao zera: o que aconteceu ate agora eu ja vi."""
    if carreiras.por_nome(nome) is None:
        return False
    momento = (quando or agora()).isoformat()
    _alterar(lambda dados: dados.setdefault("visto", {}).__setitem__(nome, momento))
    return True


# --- o botao "Verificar atualizacoes" ----------------------------------------------

def _executar_coleta() -> list[str]:
    """A mesma coleta do `radar atualizar` (as duas primeiras etapas), sem
    mandar mensagem: quem avisa no Telegram e o robo do GitHub."""
    from radar import servico

    linhas = [str(r) for r in servico.coletar_tudo()]
    linhas.append(f"Páginas lidas: {servico.detalhar_pendentes(limite=15)}")
    return linhas


def verificacao() -> dict:
    """A ultima verificacao ({inicio, fim, resumo, erro}) e se ha uma rodando."""
    ultima = dict(_ler().get("ultima_verificacao") or {})
    ultima["rodando"] = _VERIFICANDO.locked()
    for chave in ("inicio", "fim"):
        ultima[chave] = _momento(ultima.get(chave))
    return ultima


def minutos_para_liberar(momento: datetime | None = None) -> int:
    """Quantos minutos faltam para o botao valer de novo. 0 = pode clicar."""
    inicio = _momento((_ler().get("ultima_verificacao") or {}).get("inicio"))
    if inicio is None:
        return 0
    passou = (momento or agora()) - inicio
    falta = timedelta(minutes=carreiras.regras().intervalo_minimo_minutos) - passou
    return max(0, -(-int(falta.total_seconds()) // 60))


def _rodar(executar) -> None:
    try:
        resumo, erro = executar(), None
    except Exception as falha:  # noqa: BLE001 - a tela mostra, e a aba segue
        log.warning("a verificacao falhou", exc_info=True)
        resumo, erro = [], f"{type(falha).__name__}: {falha}"
    fim = agora().isoformat()

    def gravar(dados):
        ultima = dados.setdefault("ultima_verificacao", {})
        ultima.update(fim=fim, resumo=resumo, erro=erro)

    try:
        _alterar(gravar)
    finally:
        _VERIFICANDO.release()


def iniciar_verificacao(executar=None, em_segundo_plano: bool = True,
                        momento: datetime | None = None) -> str:
    """Roda a coleta agora. Devolve "iniciada", "rodando" ou "cedo".

    Em segundo plano porque a coleta leva minutos (o atraso de cortesia do
    Coletor entre uma pagina e outra), e a tela nao pode ficar presa nesse
    tempo. Os testes rodam na hora, com uma coleta falsa.
    """
    if minutos_para_liberar(momento):
        return "cedo"
    if not _VERIFICANDO.acquire(blocking=False):
        return "rodando"

    inicio = (momento or agora()).isoformat()
    _alterar(lambda dados: dados.__setitem__(
        "ultima_verificacao", {"inicio": inicio, "fim": None, "resumo": [], "erro": None}))

    executar = executar or _executar_coleta
    if em_segundo_plano:
        threading.Thread(target=_rodar, args=(executar,), daemon=True,
                         name="verificar-acompanhamentos").start()
    else:
        _rodar(executar)
    return "iniciada"


def novidades_desde(momento: datetime | None, cartoes_: list[Cartao]) -> int:
    """Quantas novidades da tela sao de depois deste momento."""
    if momento is None:
        return 0
    return sum(1 for c in cartoes_ for linha in c.novidades
               if linha.momento_da_novidade >= momento)


# --- a pesquisa do Claude Code (o que o robo nao enxerga) ----------------------------

MARCOS = ("autorizacao", "comissao", "banca", "edital", "inscricoes", "prova",
          "retificacao", "outro")
TIPOS_DE_FONTE = ("oficial", "noticia")

#: Palavra de quem ainda nao sabe. Fato com ela vira "nao confirmado".
ESPECULACAO = re.compile(
    r"\b(deve|devem|devera|deverao|pode|podem|podera|poderao|previsao|previsto|"
    r"prevista|expectativa|promete|prometido|em breve|estuda|estudam|cogita|"
    r"rumor|boato|possivel|possibilidade|especula)\b"
)

INSTRUCAO_DA_PESQUISA = """Voce recebe UMA carreira de concurso publico que eu acompanho, com o que o meu radar ja sabe dela (a situacao, os marcos e os links que ele ja tem).

Pesquise na internet o que aconteceu de NOVO com o concurso desta carreira, de SANTA CATARINA (o nome do pedido diz a cidade, quando e de uma prefeitura): autorizacao do governo, comissao organizadora, contratacao da banca, edital, inscricoes, data de prova, retificacao.

Regras - a resposta que fugir delas e recusada:
- So FATO com data e link: o ato publicado, a pagina da banca, o diario oficial, a noticia que relata um fato. Nunca invente link: copie a URL que voce abriu.
- Prefira a fonte oficial (diario oficial do estado ou do municipio, site do orgao, site da banca). Noticia de site de concurso vale, com tipo_de_fonte "noticia".
- Previsao, expectativa, "deve sair", "pode abrir", promessa de politico: e RUMOR. Se mesmo assim valer registrar, ponha "confirmado": false.
- Nao repita o que esta em `ja_sei` (os links e os fatos que o radar ja tem).
- So o que aconteceu nos ultimos 12 meses. Concurso de outro estado nao entra.
- Se nao achar nada novo, devolva a lista `novidades` vazia. Lista vazia e uma resposta certa.

Cada novidade: `data` (AAAA-MM-DD, o dia do fato), `marco` (um de: autorizacao, comissao, banca, edital, inscricoes, prova, retificacao, outro), `descricao` (uma frase, o fato), `valor` (curto e opcional: o nome da banca, a data da prova, o periodo de inscricao), `link`, `fonte` (o nome do site ou do orgao), `tipo_de_fonte` ("oficial" ou "noticia") e `confirmado` (true ou false)."""


def _ja_sei(cartao: Cartao) -> dict:
    """O que o radar ja sabe, para a pesquisa nao trazer de volta."""
    return {
        "situacao": cartao.situacao,
        "marcos": {m.nome: m.valor for m in cartao.marcos},
        "links": sorted({linha.link for linha in cartao.historico if linha.link}),
    }


def pedido_de_pesquisa(nomes: list[str] | None = None) -> dict:
    """O lote para o Claude Code do VS Code: um pedido por carreira."""
    escolhidos = [c for c in cartoes() if not nomes or c.nome in nomes]
    pedidos = [
        {"id": f"a{numero}", "acompanhamento": cartao.nome,
         "instrucao": INSTRUCAO_DA_PESQUISA, "ja_sei": _ja_sei(cartao)}
        for numero, cartao in enumerate(escolhidos, start=1)
    ]
    agora_ = agora()
    return {
        "lote": f"novidades-{agora_:%Y%m%d-%H%M%S}",
        "tipo": "novidades",
        "criado_em": agora_.isoformat(),
        "como_responder": (
            "Este arquivo foi gerado por `radar acompanhar --pedido`. Para cada "
            "item de `pedidos`, siga a `instrucao` com a internet aberta e use o "
            "`ja_sei` do item para nao repetir o que o radar ja tem. Responda "
            "TODOS num unico arquivo JSON, no formato de `formato_da_resposta`: o "
            "mesmo `lote`, o `modelo` que escreveu e o `id` de cada pedido com a "
            "lista `novidades` dele (vazia quando nao houver nada novo). Salve "
            "como data/resposta_ia.json e rode `radar acompanhar --importar "
            "data/resposta_ia.json`. Novidade sem link, sem data, com marco fora "
            "da lista, de mais de 12 meses ou ja conhecida sera RECUSADA; texto "
            "de previsao entra como nao confirmado."
        ),
        "formato_da_resposta": {
            "lote": "<o lote deste arquivo>", "modelo": "<o modelo que escreveu>",
            "respostas": [{"id": "a1", "novidades": [{
                "data": "2026-10-01", "marco": "banca",
                "descricao": "O governo contratou a banca do concurso.",
                "valor": "<o nome da banca>", "link": "https://...",
                "fonte": "Diário Oficial de SC", "tipo_de_fonte": "oficial",
                "confirmado": True}]}],
        },
        "pedidos": pedidos,
    }


def salvar_pedido(lote: dict) -> Path:
    """O mesmo data/pedido_ia.json dos outros pedidos: pedido novo substitui
    o que estiver la sem resposta."""
    from radar.servico import manual

    return manual.salvar_pedido(lote)


def _id_da_pesquisa(acompanhamento: str, link: str) -> str:
    return hashlib.sha256(f"{acompanhamento}|{link}".encode()).hexdigest()[:12]


def _recusa(pedido_id: str, motivo: str) -> str:
    return f"{pedido_id}: {motivo}"


def importar_novidades(lote: dict, respostas: list[dict], modelo: str,
                       hoje: date | None = None) -> dict:
    """Confere a resposta e grava o que presta em data/acompanhamentos.json.

    Devolve {"gravadas", "repetidas", "rumores", "recusas"}. Nada aqui toca o
    banco: a pesquisa nunca muda a situacao de um concurso.
    """
    hoje = hoje or agora().astimezone(fuso_local()).date()
    mais_velha = hoje - timedelta(days=carreiras.regras().janela_da_edicao_em_dias)
    pedidos = {p["id"]: p for p in lote.get("pedidos") or []}
    existentes = _ler().get("pesquisas") or []
    links_conhecidos = {
        (p.get("acompanhamento"), p.get("link")) for p in existentes
    }
    fatos_conhecidos = {
        (p.get("acompanhamento"), p.get("marco"), p.get("data"),
         normalizar(p.get("descricao") or "")) for p in existentes
    }

    novas, recusas, repetidas, rumores = [], [], 0, 0
    criado_em = agora().isoformat()

    for resposta in respostas:
        pedido = pedidos.get(str(resposta.get("id")))
        if pedido is None:
            recusas.append(_recusa(str(resposta.get("id")), "id que não estava no pedido"))
            continue
        nome = pedido["acompanhamento"]
        ja_no_radar = set((pedido.get("ja_sei") or {}).get("links") or [])
        for item in resposta.get("novidades") or []:
            if not isinstance(item, dict):
                recusas.append(_recusa(pedido["id"], "novidade que não é objeto"))
                continue
            link = str(item.get("link") or "").strip()
            descricao = " ".join(str(item.get("descricao") or "").split())
            marco = str(item.get("marco") or "").strip().lower()
            tipo_de_fonte = str(item.get("tipo_de_fonte") or "").strip().lower()
            valor = " ".join(str(item.get("valor") or "").split())[:80]
            try:
                dia = date.fromisoformat(str(item.get("data") or "").strip())
            except ValueError:
                recusas.append(_recusa(pedido["id"], f"sem data AAAA-MM-DD: {descricao[:60]!r}"))
                continue

            if not re.match(r"^https?://\S+$", link):
                recusas.append(_recusa(pedido["id"], f"sem link: {descricao[:60]!r}"))
                continue
            if not 10 <= len(descricao) <= 300:
                recusas.append(_recusa(pedido["id"], f"descrição vazia ou longa demais ({link})"))
                continue
            if marco not in MARCOS:
                recusas.append(_recusa(pedido["id"], f"marco fora da lista: {marco!r}"))
                continue
            if tipo_de_fonte not in TIPOS_DE_FONTE:
                recusas.append(_recusa(pedido["id"], f"tipo_de_fonte fora da lista: {tipo_de_fonte!r}"))
                continue
            if dia > hoje:
                recusas.append(_recusa(pedido["id"], f"data no futuro: {dia.isoformat()} ({link})"))
                continue
            if dia < mais_velha:
                recusas.append(_recusa(pedido["id"], f"fato antigo: {dia.isoformat()} ({link})"))
                continue

            chave_do_fato = (nome, marco, dia.isoformat(), normalizar(descricao))
            if (link in ja_no_radar or (nome, link) in links_conhecidos
                    or chave_do_fato in fatos_conhecidos):
                repetidas += 1
                continue

            confirmado = item.get("confirmado") is True
            if confirmado and ESPECULACAO.search(normalizar(descricao)):
                # A IA disse que e fato e escreveu como previsao: vale o texto.
                confirmado = False
            if not confirmado:
                rumores += 1

            links_conhecidos.add((nome, link))
            fatos_conhecidos.add(chave_do_fato)
            novas.append({
                "id": _id_da_pesquisa(nome, link),
                "acompanhamento": nome,
                "data": dia.isoformat(),
                "marco": marco,
                "descricao": descricao,
                "valor": valor,
                "link": link,
                "fonte": " ".join(str(item.get("fonte") or "").split())[:120],
                "tipo_de_fonte": tipo_de_fonte,
                "confirmado": confirmado,
                "procedencia": modelo,
                "lote": lote.get("lote"),
                "criado_em": criado_em,
                "conferida": None,
            })

    if novas:
        _alterar(lambda dados: dados.setdefault("pesquisas", []).extend(novas))
    return {"gravadas": len(novas), "repetidas": repetidas, "rumores": rumores,
            "recusas": recusas}


def conferir(pesquisa_id: str, confere: bool) -> bool:
    """Eu li a fonte: confere (vale para o marco) ou nao confere (sai do 🔔).

    So fato confirmado se confere. Rumor continua rumor: conferir uma
    previsao nao a transforma em ato publicado.
    """
    achou = {"ok": False}

    def mudar(dados):
        for p in dados.get("pesquisas") or []:
            if p.get("id") == pesquisa_id and p.get("confirmado"):
                p["conferida"] = "ok" if confere else "recusada"
                p["conferida_em"] = agora().isoformat()
                achou["ok"] = True

    _alterar(mudar)
    return achou["ok"]


# --- o Telegram: so o critico ------------------------------------------------------

#: O que muda a minha vida, nas palavras do pedido: banca definida, edital,
#: inscricoes, data da prova e retificacao.
CRITICOS = (
    linha_do_tempo.EDITAL_PUBLICADO,
    linha_do_tempo.INSCRICOES_ABERTAS,
    linha_do_tempo.PROVA_MARCADA,
    linha_do_tempo.EDITAL_RETIFICADO,
)

#: A mesma janela do aviso de favorito: aviso e sobre o que mudou agora.
JANELA_DO_TELEGRAM_EM_DIAS = 30


def _e_critico(evento: Evento) -> bool:
    if evento.tipo in CRITICOS:
        return True
    return (evento.tipo == linha_do_tempo.MUDOU_SITUACAO
            and (evento.descricao or "").rstrip().endswith("-> banca_definida"))


def eventos_a_avisar() -> list[tuple[Evento, Concurso, str]]:
    """Os eventos criticos das carreiras que ainda nao viraram mensagem.

    O mesmo `avisado_em` do aviso de favorito: um evento de concurso que e
    favorito E de uma carreira acompanhada sai uma vez so, por quem chegar
    primeiro.
    """
    criar_tabelas()
    regras = carreiras.regras()
    if not regras.acompanhamentos:
        return []
    desde = agora() - timedelta(days=JANELA_DO_TELEGRAM_EM_DIAS)
    corte = _inicio_do_dia(regras.telegram_desde)
    if corte and corte > desde:
        desde = corte

    consulta = (
        select(Evento, Concurso)
        .join(Concurso, Concurso.url == Evento.concurso_url)
        .where(Evento.avisado_em.is_(None))
        .where(Evento.tipo.in_(CRITICOS + (linha_do_tempo.MUDOU_SITUACAO,)))
        .where(Evento.data >= desde)
        .order_by(Evento.data.asc(), Evento.id.asc())
    )
    fila = []
    with sessao() as s:
        for evento, concurso in s.execute(consulta).all():
            if concurso.tipo == "noticia" or not _e_critico(evento):
                continue
            donos = carreiras.de_quais(concurso)
            if donos:
                fila.append((evento, concurso, donos[0].nome))
    return fila
