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
import hashlib
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
                     "pegadinha", "procedencia", "classificada_em", "conferida_em",
                     "conferida_por")


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
                conferida_em: datetime | None = None,
                conferida_por: str | None = None) -> Classificacao:
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
            # nenhum a associar: ela so dizia "ainda sem classificacao". E
            # menos a proposta do catalogo: palavra-chave casada no enunciado
            # nao e conceito que a questao cobra, e trocada ela foi reprovada
            # (B.8, em 04/10 o catalogo errou quase metade da amostra).
            for outra in s.scalars(select(Classificacao)
                                   .where(Classificacao.chave == chave)
                                   .where(Classificacao.principal.is_(True))
                                   .where(Classificacao.conteudo != conteudo)):
                if outra.status == PENDENTE or outra.procedencia == PROCEDENCIA_DO_CATALOGO:
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
        linha.conferida_por = conferida_por if conferida_em else None
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

class PendenteSemMateria(Exception):
    """Pendente num bloco generico: nao ha materia onde grava-la, e a questao
    fica sem linha - o mesmo estado de quem nunca foi classificado. Nao e
    erro: e o resultado esperado da maioria das questoes de bloco generico."""


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


def aplicar_associados(item: dict, pedido: dict, procedencia: str) -> int:
    """Grava os conceitos ASSOCIADOS de uma questao (§14, item 7; decisao 86).
    Devolve quantos gravou.

    O associado e outro no que a questao tambem cobra: da arvore, de assunto
    para baixo, fora do ramo da principal, e com o trecho em que aparece.
    Levanta PropostaRecusada com o motivo, sem gravar nada pela metade - todos
    os nos sao conferidos antes do primeiro gravado. Nunca vira principal e
    nunca entra na incidencia; o que eu ja conferi nao e sobrescrito.
    """
    codigo = item.get("questao")
    chave = (pedido.get("questoes") or {}).get(codigo)
    if chave is None:
        raise PropostaRecusada(f"{codigo}: a questão não estava no pedido")
    principal = (pedido.get("principais") or {}).get(codigo) or ""

    criar_tabelas()
    with sessao() as s:
        caminhos = set(s.scalars(select(Conteudo.caminho)))
        conferidas = set(s.scalars(
            select(Classificacao.conteudo).where(Classificacao.chave == chave)
            .where(Classificacao.conferida_em.is_not(None))))

    aceitos: dict[str, str] = {}
    for entrada in item.get("nos") or []:
        if not isinstance(entrada, dict):
            raise PropostaRecusada(f"{codigo}: cada associado é um no com o trecho")
        no = (entrada.get("no") or "").strip()
        trecho = (entrada.get("trecho") or "").strip()
        if no not in caminhos:
            raise PropostaRecusada(f"{codigo}: {no!r} não está na árvore")
        if len(arvore.partes(no)) < 2:
            raise PropostaRecusada(f"{codigo}: {no!r} é a matéria inteira, e não um conceito")
        if _mesmo_ramo(no, principal):
            raise PropostaRecusada(f"{codigo}: {no!r} está no ramo da principal ({principal})")
        if not trecho:
            raise PropostaRecusada(f"{codigo}: {no!r} sem o trecho em que aparece")
        aceitos.setdefault(no, trecho)

    # O associado que saiu da resposta sai do banco - menos o que eu ja
    # conferi, que e meu. Sem isto, refazer o pedido so acrescentava.
    with sessao() as s:
        for velho in s.scalars(
                select(Classificacao).where(Classificacao.chave == chave)
                .where(Classificacao.principal.is_(False))
                .where(Classificacao.conferida_em.is_(None))):
            if velho.conteudo not in aceitos:
                s.delete(velho)

    gravados = 0
    for no, trecho in aceitos.items():
        if no in conferidas:
            continue
        classificar(chave, no, procedencia, principal=False, trecho=trecho)
        gravados += 1
    return gravados


def _associado(s, chave: str, conteudo: str) -> Classificacao:
    linha = s.scalar(select(Classificacao).where(Classificacao.chave == chave)
                     .where(Classificacao.conteudo == conteudo)
                     .where(Classificacao.principal.is_(False)))
    if linha is None:
        raise ClassificacaoInvalida("Essa questão não tem esse conceito associado.")
    return linha


def conferir_associado(chave: str, conteudo: str) -> None:
    """Confirma um conceito associado: ele continua fora da contagem, e uma
    importacao nova nao o tira nem o sobrescreve."""
    criar_tabelas()
    with sessao() as s:
        _associado(s, chave, conteudo).conferida_em = agora()


def tirar_associado(chave: str, conteudo: str) -> None:
    """Apaga um conceito associado que a questao nao cobra. A principal nao
    muda."""
    criar_tabelas()
    with sessao() as s:
        s.delete(_associado(s, chave, conteudo))


def _mesmo_ramo(um: str, outro: str) -> bool:
    """Um no e o outro, ou um debaixo do outro: o mesmo conceito."""
    return (um == outro or um.startswith(outro + arvore.SEPARADOR)
            or outro.startswith(um + arvore.SEPARADOR))


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
    if pedido.get("bloco_generico"):
        # No bloco generico a materia e RESPOSTA, nao premissa: o caderno so
        # diz "Conhecimentos Especificos", e o lote agrupa pela suspeita do
        # termo.
        escolhida = (item.get("materia") or "").strip()
        if item.get("status") != PENDENTE and not escolhida:
            raise PropostaRecusada(f"{codigo}: bloco genérico sem a matéria escolhida")
        materia = escolhida or materia

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
            if pedido.get("bloco_generico"):
                # Sem materia no caderno nao ha onde pendurar a pendente: a
                # questao fica sem linha, que ja e o estado de quem nao tem
                # classificacao (Etapa 2).
                raise PendenteSemMateria(f"{codigo}: {motivo}")
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
        if pedido.get("bloco_generico"):
            # A materia escolhida tem que ser do edital de agora, e o assunto
            # tem que ser dela. Fora disso a resposta devia ser pendente.
            no_do_destino = _no(s, materia)
            if no_do_destino is None or no_do_destino.fora_do_edital:
                raise PropostaRecusada(
                    f"{codigo}: {materia!r} não é matéria do edital de agora")
            caminho_do_assunto = _assunto_do_edital(s, materia, assunto)
            if caminho_do_assunto is None:
                raise PropostaRecusada(
                    f"{codigo}: assunto fora do edital de {materia}: {assunto!r}")
        elif destino != materia:
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
        if subassunto:
            # Subassunto novo com o nome de um que ja existe na materia (igual,
            # contido ou quase igual): e o mesmo conceito em outro galho, como
            # o complementar fez em 02/10 (auditoria de 04/10, BUG-3). Recusa e
            # aponta o que existe, em vez de criar o paralelo.
            novo = arvore.caminho(caminho_do_assunto, subassunto)
            if _no(s, novo) is None:
                parecido = arvore.no_parecido(
                    s.scalars(select(Conteudo)), arvore.partes(caminho_do_assunto)[0],
                    "subassunto", subassunto)
                if parecido is not None:
                    raise PropostaRecusada(
                        f"{codigo}: o subassunto {subassunto!r} parece o que já existe "
                        f"em {parecido!r}; use esse caminho")

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


# --- a proposta automatica pelo catalogo (Etapa 3B, lote 3) --------------------

PROCEDENCIA_DO_CATALOGO = "catálogo automático (macetes.py), conferir por amostra"

#: O que a conferencia acrescenta ao trecho quando corrige (ou deixa
#: pendente) uma proposta do catalogo. A procedencia vira "manual", e sem
#: este rastro a amostra perderia justamente as que eu corrigi - que sao a
#: taxa de erro do catalogo.
ERA_DO_CATALOGO = "a proposta era do catálogo automático"


def veio_do_catalogo(c: Classificacao) -> bool:
    """A proposta e do catalogo, ou foi corrigida a partir de uma."""
    return c.procedencia == PROCEDENCIA_DO_CATALOGO or ERA_DO_CATALOGO in (c.trecho or "")


@dataclass
class ResultadoDoCatalogo:
    """O que uma passada do catalogo fez, para o comando mostrar."""

    propostas: int = 0
    sem_assunto: int = 0        # o catalogo nao casou nada
    ambiguas: int = 0           # casou mais de um assunto: nao se escolhe
    sem_par_no_edital: int = 0  # casou, mas o nome nao tem par no config
    ja_classificadas: int = 0   # tinham linha, e nao se mexe por cima
    por_assunto: dict = field(default_factory=dict)


def propor_pelo_catalogo(materia: str, chaves_das_questoes: dict) -> ResultadoDoCatalogo:
    """Propoe o assunto das questoes de UMA materia pelo catalogo de palavras.

    `chaves_das_questoes` e {chave: enunciado}. A proposta e automatica e sai
    marcada como tal na procedencia: ela vale depois da conferencia POR
    AMOSTRA (o roteiro pede 20 por materia). Nada e forcado:

    - enunciado que nao casa palavra nenhuma fica SEM LINHA;
    - enunciado que casa dois assuntos tambem: escolher um seria chute;
    - nome do catalogo sem par no `config/complementar.yml` idem;
    - questao que ja tem classificacao nao e sobrescrita.
    """
    from radar import macetes
    from radar.servico import complementar as acervo

    mapa = acervo.carregar_mapa_do_catalogo().get(materia, {})
    chave_do_catalogo = macetes.chave_da_materia(materia)
    resultado = ResultadoDoCatalogo()
    if not mapa or chave_do_catalogo is None:
        return resultado

    criar_tabelas()
    with sessao() as s:
        ja_tem = set(s.scalars(select(Classificacao.chave)
                               .where(Classificacao.principal.is_(True))))

    for chave, enunciado in chaves_das_questoes.items():
        if chave in ja_tem:
            resultado.ja_classificadas += 1
            continue
        nomes = macetes.assuntos_do_enunciado(enunciado, chave_do_catalogo)
        if not nomes:
            resultado.sem_assunto += 1
            continue
        assuntos = {mapa[nome] for nome in nomes if nome in mapa}
        if not assuntos:
            resultado.sem_par_no_edital += 1
            continue
        if len(assuntos) > 1:
            resultado.ambiguas += 1
            continue
        assunto = assuntos.pop()
        caminho = arvore.caminho(materia, assunto)
        classificar(chave, caminho, PROCEDENCIA_DO_CATALOGO,
                    trecho=f"catálogo: {', '.join(nomes)}", item_do_edital=assunto)
        resultado.propostas += 1
        resultado.por_assunto[assunto] = resultado.por_assunto.get(assunto, 0) + 1
    if resultado.propostas:
        exportar()
    return resultado


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
    rastro = f"; {ERA_DO_CATALOGO}" if atual is not None and veio_do_catalogo(atual) else ""
    if corrigir_para is not None:
        return classificar(chave, corrigir_para, "manual",
                           trecho="corrigida na conferência" + rastro,
                           tipo_de_questao=atual.tipo_de_questao if atual else None,
                           pegadinha=atual.pegadinha if atual else None,
                           conferida_em=quando)
    if pendente is not None:
        materia = arvore.partes(atual.conteudo)[0]
        return classificar(chave, materia, "manual", status=PENDENTE,
                           trecho=f"pendente: {pendente.strip() or 'sem motivo escrito'}{rastro}",
                           tipo_de_questao=atual.tipo_de_questao,
                           pegadinha=atual.pegadinha, conferida_em=quando)
    with sessao() as s:
        linha = s.get(Classificacao, atual.id)
        linha.conferida_em = quando
        linha.conferida_por = None
    return linha


#: Quem confere na reanalise as cegas (decisao 104).
REANALISE = "Claude Code, reanálise às cegas"


def confirmar_pela_reanalise(chave: str, no_da_reanalise: str,
                             quem: str = REANALISE) -> bool:
    """Marca como conferida a classificacao que uma segunda leitura, feita sem
    ver a primeira, pôs EXATAMENTE no mesmo no (decisao 104).

    Voce pediu em 05/10 para nao conferir a mao o que duas leituras
    independentes ja concordam. No diferente - outro assunto, outro
    subassunto, ou o mesmo assunto num nivel acima ou abaixo - fica sem marca,
    para voce. A conferida (por voce ou antes) nao e tocada. Devolve se marcou.
    """
    criar_tabelas()
    with sessao() as s:
        atual = s.scalar(select(Classificacao)
                         .where(Classificacao.chave == chave)
                         .where(Classificacao.principal.is_(True)))
        if (atual is None or atual.status == PENDENTE or atual.conferida_em is not None
                or atual.conteudo != no_da_reanalise):
            return False
        atual.conferida_em = agora()
        atual.conferida_por = quem
        return True


# --- quando a releitura do caderno muda o texto ------------------------------------

#: O que uma classificacao leva consigo quando muda de chave.
CAMPOS_QUE_MUDAM_DE_CHAVE = ("conteudo", "principal", "status", "trecho",
                             "item_do_edital", "dispositivo", "tipo_de_questao",
                             "pegadinha", "procedencia", "classificada_em",
                             "conferida_em", "conferida_por")


def rechavear(trocas: dict[str, set[str]], em_uso: set[str]) -> dict[str, int]:
    """Leva as classificacoes da chave antiga para a nova.

    A chave e o hash do texto da questao, e o `radar questoes --refazer` com o
    leitor consertado muda o texto - o "e cor-" que vira "e correto afirmar:",
    o titulo da secao seguinte que sai da alternativa (B.7). Sem isto, a
    classificacao conferida ficaria presa a um texto que nao existe mais.

    `trocas` e {chave antiga: chaves novas}; `em_uso`, as chaves que ainda
    existem no acervo depois da releitura. A antiga que ainda esta em uso (a
    mesma questao em outro caderno, que nao mudou) e COPIADA; a que nao esta
    mais, levada. Se a chave nova ja tem linha no mesmo no, fica uma so - a
    conferida, quando so uma das duas foi conferida. E continua valendo uma
    principal por questao: sobrando duas, fica a conferida (ou a que ja
    estava la), e a outra vira associada - ou sai, se era pendente.
    """
    resumo = {"levadas": 0, "juntadas": 0, "principais_desfeitas": 0}
    if not trocas:
        return resumo
    criar_tabelas()
    with sessao() as s:
        tocadas: set[str] = set()
        for antiga, novas in trocas.items():
            linhas = list(s.scalars(select(Classificacao)
                                   .where(Classificacao.chave == antiga)))
            if not linhas:
                continue
            for nova in sorted(novas - {antiga}):
                tocadas.add(nova)
                for linha in linhas:
                    ja = s.scalar(select(Classificacao)
                                  .where(Classificacao.chave == nova)
                                  .where(Classificacao.conteudo == linha.conteudo))
                    if ja is None:
                        s.add(Classificacao(chave=nova, **{
                            campo: getattr(linha, campo)
                            for campo in CAMPOS_QUE_MUDAM_DE_CHAVE}))
                        resumo["levadas"] += 1
                    else:
                        if linha.conferida_em and not ja.conferida_em:
                            for campo in CAMPOS_QUE_MUDAM_DE_CHAVE:
                                setattr(ja, campo, getattr(linha, campo))
                        resumo["juntadas"] += 1
            if antiga not in em_uso:
                for linha in linhas:
                    s.delete(linha)
        s.flush()
        for nova in tocadas:
            principais = list(s.scalars(select(Classificacao)
                                        .where(Classificacao.chave == nova)
                                        .where(Classificacao.principal.is_(True))
                                        .order_by(Classificacao.id)))
            if len(principais) < 2:
                continue
            fica = next((c for c in principais if c.conferida_em), principais[0])
            for outra in principais:
                if outra is fica:
                    continue
                if outra.status == PENDENTE:
                    s.delete(outra)
                else:
                    outra.principal = False
                resumo["principais_desfeitas"] += 1
    if resumo["levadas"] or resumo["juntadas"]:
        exportar()
    return resumo


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
    #: No complementar, a mesma questao em outros cadernos do concurso (um
    #: por cargo): a classificacao e uma so, e vale para todos.
    outros_cadernos: int = 0
    #: Proposta do catalogo que caiu na amostra da materia.
    na_amostra: bool = False
    #: Os conceitos associados (classificacoes NAO principais), com o trecho.
    associados: list = field(default_factory=list)

    @property
    def associados_abertos(self) -> int:
        return sum(1 for a in self.associados if a.conferida_em is None)

    @property
    def conferida(self) -> bool:
        return self.classificacao is not None and self.classificacao.conferida_em is not None


@dataclass
class AmostraDoCatalogo:
    """A conferencia por amostra das propostas do catalogo numa materia."""

    materia: str
    propostas: int      # o que o catalogo propos (contando as que eu corrigi)
    tamanho: int        # quantas estao na amostra: o config, ou todas se forem menos
    conferidas: int
    corrigidas: int     # corrigidas ou deixadas pendentes: o erro do catalogo


@dataclass
class Conferencia:
    itens: list[ItemDeConferencia]
    total: int = 0
    validas: int = 0
    conferidas: int = 0
    conferidas_validas: int = 0
    materias: list[str] = field(default_factory=list)
    evidencia: str = "alvo"
    #: A amostra de cada materia (so no complementar) e o tamanho dela.
    amostras: list[AmostraDoCatalogo] = field(default_factory=list)
    tamanho_da_amostra: int = 0
    #: Os conceitos associados do recorte inteiro, e quantos ja conferi.
    associados: int = 0
    associados_conferidos: int = 0


def conferencia(materia: str | None = None, so_abertas: bool = False,
                com_anuladas: bool = False, evidencia_escolhida: str = "alvo",
                so_amostra: bool = False,
                so_associados_abertos: bool = False) -> Conferencia:
    """As questoes com a proposta ao lado, para eu conferir uma a uma.

    `materia` filtra pelo no da materia (o do caderno ou o da classificacao);
    `so_abertas` esconde as ja conferidas; `com_anuladas` traz de volta as que
    a banca anulou, que por padrao ficam FORA da lista - elas nao entram em
    conta nenhuma (nem na incidencia), e conferi-las nao muda numero algum.
    Os totais sao sempre do recorte inteiro, com e sem as anuladas: e eles que
    dizem quanto falta.

    `evidencia_escolhida` e o recorte: o alvo (o padrao) ou o complementar
    aceito, nunca os dois juntos (regra inviolavel 1). `so_amostra` so vale no
    complementar: a amostra das propostas do catalogo. `so_associados_abertos`
    deixa so as questoes do alvo com conceito associado por conferir.
    """
    from radar import amostra as regua
    from radar.servico import evidencia

    if evidencia_escolhida == evidencia.COMPLEMENTAR:
        return _conferencia_do_complementar(materia, so_abertas, com_anuladas, so_amostra)

    taxonomia = arvore.carregar_taxonomia()
    criar_tabelas()
    with sessao() as s:
        caminhos = list(s.scalars(select(Conteudo.caminho)))
        principais = {c.chave: c for c in s.scalars(
            select(Classificacao).where(Classificacao.principal.is_(True)))}
        associados: dict[str, list] = {}
        for c in s.scalars(select(Classificacao).where(Classificacao.principal.is_(False))
                           .order_by(Classificacao.conteudo)):
            associados.setdefault(c.chave, []).append(c)
        questoes = list(s.scalars(
            select(QuestaoDeProva).where(QuestaoDeProva.evidencia == evidencia.ALVO)
            .order_by(QuestaoDeProva.ano, QuestaoDeProva.numero)))

    resultado = Conferencia(itens=[], total=len(questoes),
                            tamanho_da_amostra=regua.carregar().amostra_do_catalogo)
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
        dela = associados.get(chave_de(q), [])
        resultado.associados += len(dela)
        resultado.associados_conferidos += sum(1 for a in dela if a.conferida_em)
        if materia and materia not in (do_caderno, da_classificacao):
            continue
        if so_abertas and conferida:
            continue
        if so_associados_abertos and not any(a.conferida_em is None for a in dela):
            continue
        if q.anulada and not com_anuladas:
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
            anulada=bool(q.anulada), classificacao=c, opcoes=opcoes,
            associados=dela))
    resultado.materias = sorted(materias)
    return resultado


def _conferencia_do_complementar(materia, so_abertas, com_anuladas,
                                 so_amostra) -> Conferencia:
    """O complementar ACEITO, uma linha por classificacao.

    A mesma questao aparece em varios cadernos do mesmo concurso (um por
    cargo), e a classificacao e uma so, pela chave: conferir uma vez vale para
    todos. Questao sem classificacao nao entra - sao milhares, quase todas
    conteudo do cargo daquele concurso, e aqui se confere a PROPOSTA.
    """
    from radar import amostra as regua
    from radar.servico import complementar, evidencia

    taxonomia = arvore.carregar_taxonomia()
    aceitas = complementar.provas_aceitas()
    criar_tabelas()
    with sessao() as s:
        caminhos = list(s.scalars(select(Conteudo.caminho)))
        principais = {c.chave: c for c in s.scalars(
            select(Classificacao).where(Classificacao.principal.is_(True)))}
        questoes = list(s.scalars(
            select(QuestaoDeProva)
            .where(QuestaoDeProva.evidencia == evidencia.COMPLEMENTAR)
            .where(QuestaoDeProva.prova_url.in_(aceitas))
            .order_by(QuestaoDeProva.ano, QuestaoDeProva.municipio,
                      QuestaoDeProva.cargo, QuestaoDeProva.numero)))

    por_chave: dict[str, list] = {}
    for q in questoes:
        chave = chave_de(q)
        if chave in principais:
            por_chave.setdefault(chave, []).append(q)

    tamanho = regua.carregar().amostra_do_catalogo
    amostras, escolhidas = _amostras_do_catalogo(por_chave, principais, tamanho)
    resultado = Conferencia(itens=[], total=len(por_chave),
                            evidencia=evidencia.COMPLEMENTAR, amostras=amostras,
                            tamanho_da_amostra=tamanho)
    na_amostra = set(escolhidas)
    materias = set()
    for chave, mesma in por_chave.items():
        q, c = mesma[0], principais[chave]
        da_classificacao = arvore.partes(c.conteudo)[0]
        do_caderno = (arvore.achar(caminhos, q.materia)
                      or arvore.achar(caminhos, taxonomia.materia_do_texto(q.materia)))
        materias.add(da_classificacao)
        conferida = c.conferida_em is not None
        resultado.validas += not q.anulada
        resultado.conferidas += conferida
        resultado.conferidas_validas += conferida and not q.anulada
        if materia and materia not in (do_caderno, da_classificacao):
            continue
        if so_amostra and chave not in na_amostra:
            continue
        if so_abertas and conferida:
            continue
        if q.anulada and not com_anuladas:
            continue
        raizes = {r for r in (do_caderno, da_classificacao) if r}
        opcoes = [cam for cam in caminhos
                  if any(cam == r or cam.startswith(r + arvore.SEPARADOR) for r in raizes)]
        resultado.itens.append(ItemDeConferencia(
            codigo=(f"{q.banca} {q.ano} · {q.municipio or 'sem município'} · "
                    f"{q.cargo or 'sem cargo'} · q{q.numero}"),
            chave=chave, materia_do_caderno=q.materia, enunciado=q.enunciado,
            alternativas=q.alternativas or {}, gabarito=q.resposta,
            anulada=bool(q.anulada), classificacao=c, opcoes=opcoes,
            outros_cadernos=len(mesma) - 1, na_amostra=chave in na_amostra))
    if so_amostra:
        # Na ordem da amostra: a mesma a cada abertura da tela.
        ordem = {chave: i for i, chave in enumerate(escolhidas)}
        resultado.itens.sort(key=lambda item: ordem[item.chave])
    resultado.materias = sorted(materias)
    return resultado


def _amostras_do_catalogo(chaves, principais: dict, tamanho: int):
    """A amostra de cada materia: as `tamanho` primeiras pelo hash da chave.

    O hash embaralha sem sorteio: a amostra e a mesma a cada abertura da tela,
    e corrigir uma questao nao a tira dela (a correcao guarda o
    ERA_DO_CATALOGO). Devolve ([AmostraDoCatalogo], chaves da amostra).
    """
    por_materia: dict[str, list[str]] = {}
    for chave in chaves:
        c = principais[chave]
        if veio_do_catalogo(c):
            por_materia.setdefault(arvore.partes(c.conteudo)[0], []).append(chave)
    amostras, escolhidas = [], []
    for materia in sorted(por_materia):
        todas = sorted(por_materia[materia],
                       key=lambda k: hashlib.sha256(k.encode("utf-8")).hexdigest())
        amostra = todas[:tamanho]
        escolhidas += amostra
        linhas = [principais[k] for k in amostra]
        amostras.append(AmostraDoCatalogo(
            materia=materia, propostas=len(todas), tamanho=len(amostra),
            conferidas=sum(1 for c in linhas if c.conferida_em is not None),
            corrigidas=sum(1 for c in linhas if c.conferida_em is not None
                           and c.procedencia != PROCEDENCIA_DO_CATALOGO)))
    return amostras, escolhidas


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
                       classificada_em=quando, conferida_em=conferida,
                       conferida_por=linha.get("conferida_por"))
