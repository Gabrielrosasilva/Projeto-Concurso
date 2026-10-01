"""A questao ligada a um no da arvore, com o status e o porque.

Tres status (secao 2 do pedido):

- **completa**: chegou ao no mais fundo que a arvore tem ali;
- **parcial**: parou num no que tem filhos (o assunto, sem o subassunto);
- **pendente**: sem classificacao segura. Questao que nunca foi classificada
  tambem e pendente, sem precisar de linha aqui.

Toda linha diz QUEM classificou e QUANDO (`procedencia`): sem isso ela e
recusada, como o assunto pago e a questao gerada. Uma questao tem uma
classificacao principal, a que conta na incidencia; as outras sao associadas
e nunca somadas.

A questao e reconhecida pela CHAVE: o hash da questao inteira, enunciado e
alternativas (`questoes.chave_da_questao`). A impressao, so do enunciado,
juntava questoes diferentes de enunciado igual - em 2019, quatro de Penal
comecam "De acordo com o Codigo Penal Brasileiro, e correto". O arquivo
versionado e o `data/classificacoes.json`, pela chave e pelo caminho do no: os
dois sobrevivem a reconstrucao do banco.
"""
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from sqlalchemy import select

from radar import config
from radar import conteudos as arvore
from radar.db import criar_tabelas, sessao
from radar.models import Classificacao, Conteudo, QuestaoDeProva, agora
from radar.questoes import chave_da_questao

STATUS = ("completa", "parcial", "pendente")
PENDENTE = "pendente"

CAMPOS_DO_ARQUIVO = ("chave", "conteudo", "principal", "status", "trecho",
                     "item_do_edital", "dispositivo", "tipo_de_questao",
                     "pegadinha", "procedencia", "classificada_em", "conferida_em")


class ClassificacaoInvalida(ValueError):
    """A classificacao nao entra. A mensagem diz por que."""


def chave_de(questao) -> str:
    """A chave de uma questao do banco (enunciado + alternativas)."""
    return chave_da_questao(questao.enunciado, questao.alternativas)


def chaves_da_impressao(impressao: str) -> list[str]:
    """As chaves das questoes de um enunciado: e a ponte do formato antigo,
    que guardava so a impressao. Mais de uma quando o enunciado se repete."""
    criar_tabelas()
    with sessao() as s:
        questoes = list(s.scalars(
            select(QuestaoDeProva).where(QuestaoDeProva.impressao == impressao)))
    return sorted({chave_de(q) for q in questoes})


def caminho_do_arquivo() -> Path:
    return config.diretorio_dados() / "classificacoes.json"


def _status_do_no(s, no: Conteudo) -> str:
    """Materia sozinha nao e classificacao; no com filho e parcial; folha e
    completa."""
    if no.nivel == "materia":
        return PENDENTE
    tem_filho = s.scalar(select(Conteudo.id).where(Conteudo.pai == no.caminho).limit(1))
    return "parcial" if tem_filho is not None else "completa"


def classificar(chave: str, conteudo: str, procedencia: str | None, *,
                principal: bool = True, status: str | None = None,
                trecho: str | None = None, item_do_edital: str | None = None,
                dispositivo: str | None = None,
                tipo_de_questao: str | None = None, pegadinha: str | None = None,
                classificada_em: datetime | None = None,
                conferida_em: datetime | None = None) -> Classificacao:
    """Grava (ou corrige) a ligacao da questao a um no.

    `status` so pode ser dado como "pendente" - quando quem classifica nao
    tem certeza. Completa e parcial saem da arvore, e nao da opiniao de quem
    classificou.
    """
    if not (procedencia or "").strip():
        raise ClassificacaoInvalida(
            "Classificação sem procedência: diga o modelo (ou \"manual\") que classificou.")
    if not chave:
        raise ClassificacaoInvalida("Classificação sem a chave da questão.")
    if status is not None and status != PENDENTE:
        raise ClassificacaoInvalida(
            "Só \"pendente\" se dá à mão: completa e parcial saem da árvore.")

    criar_tabelas()
    with sessao() as s:
        no = s.scalar(select(Conteudo).where(Conteudo.caminho == conteudo))
        if no is None:
            raise ClassificacaoInvalida(f"{conteudo!r} não está na árvore.")
        # Antes de qualquer `add`: a consulta do status descarregaria uma linha
        # ainda sem status no banco.
        status = status or _status_do_no(s, no)
        if principal:
            # Uma principal por questao: a nova tira o posto da antiga, que
            # continua la como associada - menos a pendente, que nao e no
            # nenhum a associar: ela so dizia "ainda sem classificacao".
            for outra in s.scalars(select(Classificacao)
                                   .where(Classificacao.chave == chave)
                                   .where(Classificacao.principal.is_(True))
                                   .where(Classificacao.conteudo != conteudo)):
                if outra.status == PENDENTE and status != PENDENTE:
                    s.delete(outra)
                else:
                    outra.principal = False
        linha = s.scalar(select(Classificacao)
                         .where(Classificacao.chave == chave)
                         .where(Classificacao.conteudo == conteudo))
        if linha is None:
            linha = Classificacao(chave=chave, conteudo=conteudo)
            s.add(linha)
        linha.principal = principal
        linha.status = status
        linha.trecho, linha.item_do_edital, linha.dispositivo = (
            trecho, item_do_edital, dispositivo)
        linha.tipo_de_questao, linha.pegadinha = tipo_de_questao, pegadinha
        linha.procedencia = procedencia.strip()
        linha.classificada_em = classificada_em or agora()
        linha.conferida_em = conferida_em
    return linha


def do_texto_antigo(chave: str, materia: str | None, assunto: str | None,
                    procedencia: str | None,
                    classificada_em: datetime | None = None) -> Classificacao | None:
    """O formato antigo (`data/assuntos.json`: materia e assunto de texto)
    vira classificacao. O que casa exatamente com um no e ligado; o resto
    fica PENDENTE na materia, com o texto antigo guardado no trecho - nunca
    aproximado. Sem a materia na arvore, nao ha onde pendurar: None."""
    criar_tabelas()
    with sessao() as s:
        todos = list(s.scalars(select(Conteudo.caminho)))
    taxonomia = arvore.carregar_taxonomia()
    no_da_materia = (arvore.achar(todos, materia)
                     or arvore.achar(todos, taxonomia.materia_do_texto(materia)))
    if no_da_materia is None:
        return None
    no = arvore.achar(todos, assunto, pai=no_da_materia)
    if no is not None:
        return classificar(chave, no, procedencia, classificada_em=classificada_em)
    return classificar(chave, no_da_materia, procedencia, status=PENDENTE,
                       trecho=f"texto antigo que não casa com o edital: {assunto}",
                       classificada_em=classificada_em)


# --- a proposta do pedido de classificacao (Etapa 3A) --------------------------
#
# O Claude Code classifica as questoes do alvo pelo pedido em arquivo
# (`radar classificar --pedido`), e a resposta volta por aqui. Ela so entra
# inteira e justificada: o assunto tem que ser um item do edital da materia,
# o tipo tem que estar no config/taxonomia.yml, e quem nao tem seguranca
# responde "pendente" - que fica pendente, sem no forcado.

class PropostaRecusada(ValueError):
    """Uma classificacao da resposta que nao entra. A mensagem diz por que."""


def _no(s, caminho_do_no: str | None) -> Conteudo | None:
    if not caminho_do_no:
        return None
    return s.scalar(select(Conteudo).where(Conteudo.caminho == caminho_do_no))


def _assunto_do_edital(s, materia: str, assunto: str | None) -> str | None:
    """O caminho do assunto do EDITAL da materia com esse nome, ou None."""
    filhos = [c.caminho for c in s.scalars(
        select(Conteudo).where(Conteudo.pai == materia)
        .where(Conteudo.origem == "edital"))]
    return arvore.achar(filhos, assunto, pai=materia)


def aplicar_proposta(item: dict, pedido: dict, procedencia: str) -> str:
    """Grava UMA classificacao proposta. Devolve o caminho do no gravado.

    `pedido` e o item do lote: a materia, as questoes que foram mandadas
    (codigo -> chave) e se a materia esta fora do edital atual.
    Levanta PropostaRecusada com o motivo, sem gravar nada pela metade: tudo
    e conferido antes do primeiro no criado.
    """
    from radar.servico import conteudos

    codigo = item.get("questao")
    chave = (pedido.get("questoes") or {}).get(codigo)
    if chave is None:
        raise PropostaRecusada(f"{codigo}: a questão não estava no pedido")
    materia = pedido["materia"]

    with sessao() as s:
        ja = s.scalar(select(Classificacao)
                      .where(Classificacao.chave == chave)
                      .where(Classificacao.principal.is_(True)))
        if ja is not None and ja.conferida_em is not None:
            raise PropostaRecusada(f"{codigo}: já conferida por você; fica como está")

        if item.get("status") == PENDENTE:
            motivo = (item.get("motivo") or "").strip()
            if not motivo:
                raise PropostaRecusada(f"{codigo}: pendente sem motivo")
            # O dispositivo vai junto mesmo na pendente: "caiu o art. 8º do CP"
            # e verdade mesmo quando o assunto do edital nao cobre o artigo.
            classificar(chave, materia, procedencia, status=PENDENTE,
                        trecho=f"pendente: {motivo}",
                        dispositivo=item.get("dispositivo"),
                        tipo_de_questao=item.get("tipo_de_questao"),
                        pegadinha=item.get("pegadinha"))
            return materia

        trecho = (item.get("trecho") or "").strip()
        item_do_edital = (item.get("item_do_edital") or "").strip()
        if not trecho or not item_do_edital:
            raise PropostaRecusada(
                f"{codigo}: sem justificativa (o trecho e o item do edital)")
        taxonomia = arvore.carregar_taxonomia()
        tipo = item.get("tipo_de_questao")
        if tipo not in taxonomia.tipos_de_questao:
            raise PropostaRecusada(f"{codigo}: tipo de questão {tipo!r} fora do "
                                   f"config/taxonomia.yml")
        assunto = (item.get("assunto") or "").strip()
        if not assunto:
            raise PropostaRecusada(f"{codigo}: classificada sem assunto")

        # Onde o assunto mora: no edital da materia; ou, na materia fora do
        # edital atual, num assunto do edital de outra materia (quando o item
        # do edital justifica) ou num assunto novo debaixo dela.
        destino = item.get("materia") or materia
        assunto_novo = False
        if destino != materia:
            if not pedido.get("fora_do_edital"):
                raise PropostaRecusada(f"{codigo}: matéria trocada ({destino!r}) "
                                       f"numa matéria que está no edital")
            no_do_destino = _no(s, destino)
            if no_do_destino is None or no_do_destino.fora_do_edital:
                raise PropostaRecusada(f"{codigo}: {destino!r} não é matéria do edital")
            caminho_do_assunto = _assunto_do_edital(s, destino, assunto)
            if caminho_do_assunto is None:
                raise PropostaRecusada(f"{codigo}: assunto fora do edital de {destino}")
        elif pedido.get("fora_do_edital"):
            caminho_do_assunto = (_assunto_do_edital(s, materia, assunto)
                                  or arvore.caminho(materia, assunto))
            assunto_novo = _no(s, caminho_do_assunto) is None
        else:
            caminho_do_assunto = _assunto_do_edital(s, materia, assunto)
            if caminho_do_assunto is None:
                raise PropostaRecusada(
                    f"{codigo}: assunto fora do edital da matéria: {assunto!r}")

        subassunto = (item.get("subassunto") or "").strip()
        elemento = (item.get("elemento") or "").strip()
        if elemento and not subassunto:
            raise PropostaRecusada(f"{codigo}: elemento sem subassunto")
        if elemento:
            try:
                arvore.conferir_elemento(taxonomia, arvore.partes(caminho_do_assunto)[0],
                                         item.get("tipo_elemento"))
            except arvore.ConteudoInvalido as erro:
                raise PropostaRecusada(f"{codigo}: {erro}") from erro

    # Conferido tudo: agora os nos que faltam, e a classificacao.
    origem = {"origem": "classificacao", "procedencia": procedencia}
    caminho_do_no = caminho_do_assunto
    if assunto_novo:
        caminho_do_no = conteudos.garantir(materia, assunto, **origem)
    if subassunto:
        caminho_do_no = conteudos.garantir(caminho_do_no, subassunto, **origem)
    if elemento:
        caminho_do_no = conteudos.garantir(
            caminho_do_no, elemento, tipo_elemento=item.get("tipo_elemento"),
            referencia=item.get("referencia"), **origem)
    classificar(chave, caminho_do_no, procedencia, trecho=trecho,
                item_do_edital=item_do_edital, dispositivo=item.get("dispositivo"),
                tipo_de_questao=tipo, pegadinha=item.get("pegadinha"))
    return caminho_do_no


def conferir(chave: str, *, corrigir_para: str | None = None,
             pendente: str | None = None) -> Classificacao:
    """O que a tela de conferencia grava: confirmar, corrigir ou pendente.

    Confirmar so marca a data. Corrigir troca o no e a procedencia vira
    "manual". Pendente guarda o meu motivo. Os tres marcam como conferida.
    """
    criar_tabelas()
    with sessao() as s:
        atual = s.scalar(select(Classificacao)
                         .where(Classificacao.chave == chave)
                         .where(Classificacao.principal.is_(True)))
    if atual is None and corrigir_para is None:
        raise ClassificacaoInvalida("Essa questão ainda não tem classificação.")
    quando = agora()
    if corrigir_para is not None:
        return classificar(chave, corrigir_para, "manual",
                           trecho="corrigida na conferência",
                           tipo_de_questao=atual.tipo_de_questao if atual else None,
                           pegadinha=atual.pegadinha if atual else None,
                           conferida_em=quando)
    if pendente is not None:
        materia = arvore.partes(atual.conteudo)[0]
        return classificar(chave, materia, "manual", status=PENDENTE,
                           trecho=f"pendente: {pendente.strip() or 'sem motivo escrito'}",
                           tipo_de_questao=atual.tipo_de_questao,
                           pegadinha=atual.pegadinha, conferida_em=quando)
    with sessao() as s:
        linha = s.get(Classificacao, atual.id)
        linha.conferida_em = quando
    return linha


# --- a tela de conferencia -----------------------------------------------------

@dataclass
class ItemDeConferencia:
    codigo: str                     # "2019-q51"
    chave: str
    materia_do_caderno: str | None
    enunciado: str
    alternativas: dict
    gabarito: str | None
    anulada: bool
    #: A classificacao principal, ou None quando ainda nao ha.
    classificacao: Classificacao | None
    #: Os nos em que ela pode ser corrigida: a materia dela e tudo abaixo.
    opcoes: list[str] = field(default_factory=list)

    @property
    def conferida(self) -> bool:
        return self.classificacao is not None and self.classificacao.conferida_em is not None


@dataclass
class Conferencia:
    itens: list[ItemDeConferencia]
    total: int = 0
    validas: int = 0
    conferidas: int = 0
    conferidas_validas: int = 0
    materias: list[str] = field(default_factory=list)


def conferencia(materia: str | None = None, so_abertas: bool = False) -> Conferencia:
    """As questoes do alvo com a proposta ao lado, para eu conferir uma a uma.

    `materia` filtra pelo no da materia (o do caderno ou o da classificacao);
    `so_abertas` esconde as ja conferidas. Os totais sao sempre do alvo
    inteiro: e eles que dizem quanto falta para a 3A fechar.
    """
    from radar.servico import evidencia

    taxonomia = arvore.carregar_taxonomia()
    criar_tabelas()
    with sessao() as s:
        caminhos = list(s.scalars(select(Conteudo.caminho)))
        principais = {c.chave: c for c in s.scalars(
            select(Classificacao).where(Classificacao.principal.is_(True)))}
        questoes = list(s.scalars(
            select(QuestaoDeProva).where(QuestaoDeProva.evidencia == evidencia.ALVO)
            .order_by(QuestaoDeProva.ano, QuestaoDeProva.numero)))

    resultado = Conferencia(itens=[], total=len(questoes))
    materias = set()
    for q in questoes:
        c = principais.get(chave_de(q))
        do_caderno = (arvore.achar(caminhos, q.materia)
                      or arvore.achar(caminhos, taxonomia.materia_do_texto(q.materia)))
        da_classificacao = arvore.partes(c.conteudo)[0] if c else None
        raiz = da_classificacao or do_caderno
        if raiz:
            materias.add(raiz)
        conferida = c is not None and c.conferida_em is not None
        resultado.validas += not q.anulada
        resultado.conferidas += conferida
        resultado.conferidas_validas += conferida and not q.anulada
        if materia and materia not in (do_caderno, da_classificacao):
            continue
        if so_abertas and conferida:
            continue
        # A materia do caderno e a da classificacao (quando a de 2013 foi para
        # um assunto de 2019): corrigir pode ir para qualquer uma das duas.
        raizes = {r for r in (do_caderno, da_classificacao) if r}
        opcoes = [cam for cam in caminhos
                  if any(cam == r or cam.startswith(r + arvore.SEPARADOR) for r in raizes)]
        resultado.itens.append(ItemDeConferencia(
            codigo=f"{q.ano}-q{q.numero}", chave=chave_de(q),
            materia_do_caderno=q.materia, enunciado=q.enunciado,
            alternativas=q.alternativas or {}, gabarito=q.resposta,
            anulada=bool(q.anulada), classificacao=c, opcoes=opcoes))
    resultado.materias = sorted(materias)
    return resultado


# --- o arquivo ----------------------------------------------------------------

def _como_linha(c: Classificacao) -> dict:
    linha = {campo: getattr(c, campo) for campo in CAMPOS_DO_ARQUIVO}
    for campo in ("classificada_em", "conferida_em"):
        if linha[campo] is not None:
            linha[campo] = linha[campo].isoformat()
    return linha


def exportar(caminho: Path | None = None) -> int:
    criar_tabelas()
    destino = caminho or caminho_do_arquivo()
    with sessao() as s:
        linhas = [_como_linha(c) for c in s.scalars(
            select(Classificacao).order_by(Classificacao.chave,
                                           Classificacao.conteudo))]
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(linhas, ensure_ascii=False, indent=2,
                                  sort_keys=True) + "\n", encoding="utf-8")
    return len(linhas)


def importar(caminho: Path | None = None) -> tuple[int, int]:
    """Traz as classificacoes do JSON. Devolve (entraram, recusadas).

    Recusada e a linha sem procedencia, ou com um no que a arvore nao tem: ela
    nao entra pela metade, e a contagem diz quantas ficaram de fora.
    """
    origem = caminho or caminho_do_arquivo()
    if not origem.exists():
        return 0, 0
    entraram = recusadas = 0
    for linha in json.loads(origem.read_text(encoding="utf-8")) or []:
        for convertida in _das_linhas_antigas(linha):
            try:
                _classificar_da_linha(convertida)
                entraram += 1
            except ClassificacaoInvalida:
                recusadas += 1
    return entraram, recusadas


def _das_linhas_antigas(linha: dict) -> list[dict]:
    """A linha do arquivo, ja com a chave. Linha de antes da chave (so com a
    impressao do enunciado) vira uma por questao daquele enunciado: igual,
    quando ha uma so; PENDENTE na materia, quando o enunciado se repete - nao
    da para saber de qual delas a classificacao era, e chutar e o que a
    regra 9 proibe. Sem questao no banco, a linha nao tem onde entrar."""
    if linha.get("chave") or not linha.get("impressao"):
        return [linha]
    chaves = chaves_da_impressao(linha["impressao"])
    if len(chaves) == 1:
        return [{**linha, "chave": chaves[0]}]
    materia = arvore.partes(linha.get("conteudo") or "")[0]
    return [{**linha, "chave": chave, "conteudo": materia, "status": PENDENTE,
             "principal": True, "conferida_em": None,
             "trecho": ("classificação antiga ambígua: o enunciado se repete em "
                        "outra questão; classificar de novo")}
            for chave in chaves]


def _classificar_da_linha(linha: dict) -> Classificacao:
    quando = (datetime.fromisoformat(linha["classificada_em"])
              if linha.get("classificada_em") else None)
    conferida = (datetime.fromisoformat(linha["conferida_em"])
                 if linha.get("conferida_em") else None)
    return classificar(linha.get("chave"), linha.get("conteudo"),
                       linha.get("procedencia"),
                       principal=bool(linha.get("principal", True)),
                       status=PENDENTE if linha.get("status") == PENDENTE else None,
                       trecho=linha.get("trecho"),
                       item_do_edital=linha.get("item_do_edital"),
                       dispositivo=linha.get("dispositivo"),
                       tipo_de_questao=linha.get("tipo_de_questao"),
                       pegadinha=linha.get("pegadinha"),
                       classificada_em=quando, conferida_em=conferida)
