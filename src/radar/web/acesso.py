"""Usuario e senha para entrar pela rede (decisao 185, pedido de 22/10).

Desde a decisao 184 o radar atende o celular no Wi-Fi de casa, sem senha:
qualquer pessoa no Wi-Fi abria. Agora:

- **neste PC** (`localhost`), nada muda: abre direto;
- **pela rede** (o celular), o navegador pede usuario e senha - a janela do
  proprio navegador (HTTP Basic), que o iPhone guarda no chaveiro;
- **sem senha definida**, o acesso pela rede fica fechado, com a pagina
  dizendo como definir: `radar senha`, no PC.

A senha nunca e guardada: o `.env` (fora do git) tem o usuario e o RESUMO
dela (PBKDF2-SHA256, com sal). O `.env` e lido de novo quando muda: trocar a
senha vale na hora, sem reiniciar o servidor.

E um embrulho ASGI em volta do app, ligado pelo `radar web` (e por isso pelo
`radar subir` e pela tarefa do logon). O app em si nao sabe de senha: os
testes que o usam direto continuam sem ela.

Um limite que vale saber: no Wi-Fi de casa a conexao e HTTP, sem cadeado - a
senha atravessa a rede so codificada, e nao cifrada. Ela segura quem esta no
Wi-Fi sem saber a senha; nao segura quem consegue ler o trafego da rede.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import secrets
from pathlib import Path

from dotenv import dotenv_values

from radar import cache, config

USUARIO = "RADAR_USUARIO"
RESUMO = "RADAR_SENHA_RESUMO"
#: As iteracoes do PBKDF2: lento de proposito para quem tenta adivinhar; a
#: conferencia de cada navegador e feita uma vez e lembrada (abaixo).
ITERACOES = 200_000
ALGORITMO = "pbkdf2_sha256"
#: Quem e "este PC": o servidor atende o proprio PC pelo localhost.
DESTE_PC = {"127.0.0.1", "::1", "localhost"}


def caminho_do_env() -> Path:
    return config.RAIZ / ".env"


def resumir(senha: str, sal: bytes | None = None, iteracoes: int = ITERACOES) -> str:
    """O resumo que vai para o `.env`: "pbkdf2_sha256$iteracoes$sal$resumo"."""
    sal = sal or secrets.token_bytes(16)
    feito = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), sal, iteracoes)
    return f"{ALGORITMO}${iteracoes}${sal.hex()}${feito.hex()}"


def confere(senha: str, resumo: str) -> bool:
    """A senha bate com o resumo guardado? Comparacao em tempo constante."""
    try:
        algoritmo, iteracoes, sal, esperado = resumo.split("$")
        if algoritmo != ALGORITMO:
            return False
        feito = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"),
                                    bytes.fromhex(sal), int(iteracoes))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(feito.hex(), esperado)


def credenciais(caminho: Path | None = None) -> tuple[str, str] | None:
    """(usuario, resumo) do `.env`, ou None quando a senha nao foi definida."""
    arquivo = caminho or caminho_do_env()
    if not arquivo.exists():
        return None
    valores = cache.do_arquivo(arquivo, lambda: dict(dotenv_values(arquivo)), nome="env")
    usuario, resumo = valores.get(USUARIO), valores.get(RESUMO)
    return (usuario, resumo) if usuario and resumo else None


def do_cabecalho(cabecalho: str | None) -> tuple[str, str] | None:
    """(usuario, senha) de um "Authorization: Basic ...", ou None."""
    if not cabecalho or not cabecalho.lower().startswith("basic "):
        return None
    try:
        texto = base64.b64decode(cabecalho[6:].strip(), validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError, ValueError):
        return None
    usuario, separador, senha = texto.partition(":")
    return (usuario, senha) if separador else None


class Protegido:
    """O app atras da senha, para quem vem pela rede."""

    def __init__(self, app, caminho_do_env: Path | None = None):
        self.app = app
        self.caminho_do_env = caminho_do_env
        #: Os cabecalhos ja conferidos, por resumo guardado: o PBKDF2 e lento de
        #: proposito, e o navegador manda a senha em toda requisicao (cada CSS,
        #: cada imagem). Trocou a senha, o resumo muda e tudo e conferido de novo.
        self._conferidos: dict[str, set[str]] = {}

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or self._deste_pc(scope):
            return await self.app(scope, receive, send)
        guardado = credenciais(self.caminho_do_env)
        if guardado is None:
            return await self._responder(send, 403, SEM_SENHA)
        cabecalho = _cabecalho(scope, b"authorization")
        if self._vale(cabecalho, guardado):
            return await self.app(scope, receive, send)
        return await self._responder(send, 401, PEDE_SENHA, pedir=True)

    @staticmethod
    def _deste_pc(scope) -> bool:
        cliente = scope.get("client")
        return bool(cliente) and cliente[0] in DESTE_PC

    def _vale(self, cabecalho: str | None, guardado: tuple[str, str]) -> bool:
        usuario, resumo = guardado
        ja = self._conferidos.setdefault(resumo, set())
        if cabecalho and cabecalho in ja:
            return True
        par = do_cabecalho(cabecalho)
        if par is None or not hmac.compare_digest(par[0], usuario) or not confere(par[1], resumo):
            return False
        ja.add(cabecalho)
        return True

    @staticmethod
    async def _responder(send, status: int, corpo: str, pedir: bool = False):
        cabecalhos = [(b"content-type", b"text/html; charset=utf-8")]
        if pedir:
            cabecalhos.append((b"www-authenticate", b'Basic realm="Radar", charset="UTF-8"'))
        await send({"type": "http.response.start", "status": status, "headers": cabecalhos})
        await send({"type": "http.response.body", "body": corpo.encode("utf-8")})


def _cabecalho(scope, nome: bytes) -> str | None:
    for chave, valor in scope.get("headers") or []:
        if chave.lower() == nome:
            return valor.decode("latin-1")
    return None


_PAGINA = ('<!doctype html><html lang="pt-BR"><meta charset="utf-8">'
           '<meta name="viewport" content="width=device-width, initial-scale=1">'
           '<title>Radar</title><body style="font-family:system-ui,sans-serif;'
           'max-width:30rem;margin:3rem auto;padding:0 1rem;line-height:1.5">{}</body></html>')
PEDE_SENHA = _PAGINA.format("<h1>Radar</h1><p>Entre com o usuário e a senha do radar.</p>")
SEM_SENHA = _PAGINA.format(
    "<h1>Radar</h1><p>O acesso pela rede está fechado: ainda não há senha.</p>"
    "<p>No PC, rode <code>radar senha</code> e abra de novo.</p>")


def protegido():
    """O app do radar atras da senha: o que o `radar web` sobe."""
    from radar.web.app import app

    return Protegido(app)
