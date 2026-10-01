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

O arquivo versionado e o `data/classificacoes.json`, pela impressao do
enunciado e pelo caminho do no - os dois sobrevivem a reconstrucao do banco.
"""
import json
from datetime import datetime
from pathlib import Path

from sqlalchemy import select

from radar import config
from radar import conteudos as arvore
from radar.db import criar_tabelas, sessao
from radar.models import Classificacao, Conteudo, agora

STATUS = ("completa", "parcial", "pendente")
PENDENTE = "pendente"

CAMPOS_DO_ARQUIVO = ("impressao", "conteudo", "principal", "status", "trecho",
                     "item_do_edital", "dispositivo", "procedencia",
                     "classificada_em", "conferida_em")


class ClassificacaoInvalida(ValueError):
    """A classificacao nao entra. A mensagem diz por que."""


def caminho_do_arquivo() -> Path:
    return config.diretorio_dados() / "classificacoes.json"


def _status_do_no(s, no: Conteudo) -> str:
    """Materia sozinha nao e classificacao; no com filho e parcial; folha e
    completa."""
    if no.nivel == "materia":
        return PENDENTE
    tem_filho = s.scalar(select(Conteudo.id).where(Conteudo.pai == no.caminho).limit(1))
    return "parcial" if tem_filho is not None else "completa"


def classificar(impressao: str, conteudo: str, procedencia: str | None, *,
                principal: bool = True, status: str | None = None,
                trecho: str | None = None, item_do_edital: str | None = None,
                dispositivo: str | None = None,
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
    if not impressao:
        raise ClassificacaoInvalida("Classificação sem a impressão da questão.")
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
            # continua la como associada.
            for outra in s.scalars(select(Classificacao)
                                   .where(Classificacao.impressao == impressao)
                                   .where(Classificacao.principal.is_(True))
                                   .where(Classificacao.conteudo != conteudo)):
                outra.principal = False
        linha = s.scalar(select(Classificacao)
                         .where(Classificacao.impressao == impressao)
                         .where(Classificacao.conteudo == conteudo))
        if linha is None:
            linha = Classificacao(impressao=impressao, conteudo=conteudo)
            s.add(linha)
        linha.principal = principal
        linha.status = status
        linha.trecho, linha.item_do_edital, linha.dispositivo = (
            trecho, item_do_edital, dispositivo)
        linha.procedencia = procedencia.strip()
        linha.classificada_em = classificada_em or agora()
        linha.conferida_em = conferida_em
    return linha


def do_texto_antigo(impressao: str, materia: str | None, assunto: str | None,
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
        return classificar(impressao, no, procedencia, classificada_em=classificada_em)
    return classificar(impressao, no_da_materia, procedencia, status=PENDENTE,
                       trecho=f"texto antigo que não casa com o edital: {assunto}",
                       classificada_em=classificada_em)


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
            select(Classificacao).order_by(Classificacao.impressao,
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
        quando = (datetime.fromisoformat(linha["classificada_em"])
                  if linha.get("classificada_em") else None)
        conferida = (datetime.fromisoformat(linha["conferida_em"])
                     if linha.get("conferida_em") else None)
        try:
            classificar(linha.get("impressao"), linha.get("conteudo"),
                        linha.get("procedencia"),
                        principal=bool(linha.get("principal", True)),
                        status=PENDENTE if linha.get("status") == PENDENTE else None,
                        trecho=linha.get("trecho"),
                        item_do_edital=linha.get("item_do_edital"),
                        dispositivo=linha.get("dispositivo"),
                        classificada_em=quando, conferida_em=conferida)
            entraram += 1
        except ClassificacaoInvalida:
            recusadas += 1
    return entraram, recusadas
