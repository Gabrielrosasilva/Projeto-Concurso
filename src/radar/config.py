"""Configuracao central: tudo que muda entre a sua maquina e o GitHub Actions.

Regra desta camada: NADA acontece quando o modulo e importado. Criar pasta,
abrir arquivo ou conectar no banco em tempo de import quebra teste e CI de
formas dificeis de depurar. Aqui so existem funcoes; quem chama e quem age.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # le o .env, se existir. Nao cria nem escreve nada.

RAIZ = Path(__file__).resolve().parents[2]

# Quanto tempo esperar entre duas requisicoes ao mesmo site, em segundos.
# Nao e frescura: e o que separa "coletor educado" de "robo abusivo".
ATRASO_ENTRE_REQUISICOES = float(os.getenv("RADAR_REQUEST_DELAY", "1.5"))
TIMEOUT_REQUISICAO = int(os.getenv("RADAR_REQUEST_TIMEOUT", "30"))

USER_AGENT = os.getenv(
    "RADAR_USER_AGENT",
    "radar-concursos/0.1 (projeto pessoal de estudo; contato via GitHub)",
)


def diretorio_dados() -> Path:
    """Pasta data/. Cria na hora do uso, nunca no import."""
    caminho = Path(os.getenv("RADAR_DATA_DIR") or (RAIZ / "data"))
    caminho.mkdir(parents=True, exist_ok=True)
    return caminho


def diretorio_config() -> Path:
    return Path(os.getenv("RADAR_CONFIG_DIR") or (RAIZ / "config"))


def url_do_banco() -> str:
    """SQLite por padrao. Postgres opcional via RADAR_DATABASE_URL."""
    definida = os.getenv("RADAR_DATABASE_URL")
    if definida:
        return definida
    return f"sqlite:///{diretorio_dados() / 'radar.db'}"
