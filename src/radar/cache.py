"""Guardar o que nao muda, para nao refazer a conta (pedido de 22/10).

A tela Hoje levava 6 s, e o Estudar 7: a mesma conta, com o mesmo resultado,
refeita muitas vezes na mesma abertura - o estoque de questoes 3 vezes, o
mesmo nome de materia comparado 88 mil vezes, o cronograma.yml lido 9 vezes.
Dois jeitos de guardar, e nenhum muda resultado:

- `do_arquivo`: o que sai de um arquivo de configuracao. Ele so e
  interpretado de novo quando o CONTEUDO muda (o arquivo e lido e comparado,
  o que custa menos de 1 ms; o caro e interpretar o YAML): editar o
  cronograma.yml continua valendo na proxima abertura, sem reiniciar nada;
- `por_requisicao`: dentro de UMA abertura de tela (um GET), a mesma funcao
  com os mesmos argumentos e feita uma vez so. Acabou a requisicao, o que foi
  guardado some. Fora de uma requisicao - o terminal, o robo, um POST que
  grava - nada e guardado, e a funcao roda como sempre.

Quem usa precisa devolver dado que ninguem altera depois: o que e guardado e
o MESMO objeto para todos os que pedem.
"""
from __future__ import annotations

import functools
import hashlib
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path

#: O que esta guardado na requisicao de agora; None fora de uma requisicao.
_da_requisicao: ContextVar[dict | None] = ContextVar("radar_cache_da_requisicao", default=None)

#: {(nome, caminho): (resumo do conteudo, valor)}.
_dos_arquivos: dict = {}


@contextmanager
def requisicao():
    """Abre a guarda de uma requisicao; ao sair, tudo o que foi guardado some."""
    marca = _da_requisicao.set({})
    try:
        yield
    finally:
        _da_requisicao.reset(marca)


def _chave(valor):
    """Lista vira tupla, para a lista de materias poder ser chave."""
    if isinstance(valor, list):
        return tuple(_chave(v) for v in valor)
    if isinstance(valor, (set, frozenset)):
        return frozenset(valor)
    return valor


def por_requisicao(funcao):
    """A funcao feita uma vez por requisicao, para cada combinacao de
    argumentos. Fora de uma requisicao, roda direto."""
    @functools.wraps(funcao)
    def guardada(*args, **kwargs):
        guarda = _da_requisicao.get()
        if guarda is None:
            return funcao(*args, **kwargs)
        chave = (funcao.__module__, funcao.__qualname__,
                 _chave(list(args)), tuple(sorted((k, _chave(v)) for k, v in kwargs.items())))
        if chave not in guarda:
            guarda[chave] = funcao(*args, **kwargs)
        return guarda[chave]
    return guardada


def do_arquivo(caminho: Path, ler, *, nome: str):
    """O valor que `ler()` tira do arquivo, feito de novo so quando o
    conteudo do arquivo muda. Arquivo que nao existe nao e guardado: `ler`
    decide o que fazer."""
    try:
        conteudo = Path(caminho).read_bytes()
    except OSError:
        return ler()
    marca = hashlib.sha256(conteudo).digest()
    chave = (nome, str(Path(caminho).resolve()))
    guardado = _dos_arquivos.get(chave)
    if guardado is not None and guardado[0] == marca:
        return guardado[1]
    valor = ler()
    _dos_arquivos[chave] = (marca, valor)
    return valor


def esquecer() -> None:
    """Joga fora tudo o que foi guardado dos arquivos (para os testes)."""
    _dos_arquivos.clear()
