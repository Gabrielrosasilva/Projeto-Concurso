"""Onde ler o texto oficial de cada materia e assunto, de config/leis.yml.

Este modulo devolve ENDERECO, e nada mais. O radar nao baixa, nao copia e nao
guarda o texto de lei nenhuma: quem publica lei e o Planalto e a ALESC, e a
versao vigente so esta certa la. Guardar uma copia aqui seria guardar a lei de
hoje para ler daqui a dois anos.

A regra do projeto vale igual: **nunca chutar**. Assunto sem marca no YAML e
materia sem `url` devolvem None, e a tela simplesmente nao mostra o "ler a
lei". Um link errado e pior que link nenhum - eu estudaria a lei errada
achando que era a certa.
"""
from dataclasses import dataclass
from functools import cache

import yaml

from radar import config
from radar.regioes import normalizar


@dataclass(frozen=True)
class Lei:
    """Onde ler o texto oficial de um assunto."""

    titulo: str
    url: str
    #: O que eu preciso saber ANTES de abrir: lei revogada, data divergente.
    #: None quando nao ha ressalva nenhuma.
    nota: str | None = None


@cache
def _arquivo() -> dict:
    """Le config/leis.yml inteiro. Arquivo ausente vira {}, e nao erro."""
    arquivo = config.diretorio_config() / "leis.yml"
    if not arquivo.exists():
        return {}
    return yaml.safe_load(arquivo.read_text(encoding="utf-8")) or {}


def _carregar() -> list[dict]:
    return _arquivo().get("materias") or []


def recarregar() -> None:
    """Esquece o que foi lido. Usado pelos testes e se voce editar o YAML."""
    _arquivo.cache_clear()


def exige_artigo(materia: str | None) -> bool:
    """Texto de IA desta materia tem que citar artigo de lei?

    Sim, a menos que a materia esteja em `sem_lei`. O padrao e exigir: uma
    materia de Direito escrita de outro jeito escaparia de uma lista do que
    exige, e nao escapa de uma lista do que nao exige.
    """
    procurada = normalizar(materia or "")
    return procurada not in {
        normalizar(str(nome)) for nome in _arquivo().get("sem_lei") or []
    }


def _bloco_da_materia(materia: str | None) -> dict | None:
    procurada = normalizar(materia or "")
    if not procurada:
        return None
    for bloco in _carregar():
        if normalizar(bloco.get("materia") or "") == procurada:
            return bloco
    return None


def _como_lei(item: dict | None) -> Lei | None:
    """A entrada do YAML virada em Lei, ou None quando falta o endereco.

    Sem `url` nao ha link, e nao adianta ter titulo: o bloco existe so para
    eu documentar a materia no YAML.
    """
    if not item or not item.get("url"):
        return None
    return Lei(
        titulo=item.get("lei") or item["url"],
        url=item["url"],
        nota=item.get("nota") or None,
    )


def da_materia(materia: str | None) -> Lei | None:
    """O texto oficial que cobre a materia inteira, quando existe um so.

    Direito Penal tem: e o Codigo Penal, e todo assunto dela esta la dentro.
    Legislacao Especial nao tem: sao cinco leis avulsas, e cada assunto aponta
    para a sua.
    """
    return _como_lei(_bloco_da_materia(materia))


def do_assunto(materia: str | None, assunto: str | None) -> Lei | None:
    """O texto oficial daquele assunto, caindo no da materia quando nao ha.

    A marca `quando` do YAML e procurada DENTRO do nome que o edital usa, e
    nao comparada com ele: o edital escreve "Lei Complementar n.o 529 de 17 de
    dezembro de 2011 (Regimento Interno dos estabelecimentos penais do Estado
    de Santa Catarina)", e copiar essa frase para o YAML seria copiar um texto
    que a proxima edicao do edital reescreve.
    """
    bloco = _bloco_da_materia(materia)
    if bloco is None:
        return None

    procurado = normalizar(assunto or "")
    if procurado:
        for item in bloco.get("assuntos") or []:
            marca = normalizar(item.get("quando") or "")
            if marca and marca in procurado:
                return _como_lei(item)

    return _como_lei(bloco)
