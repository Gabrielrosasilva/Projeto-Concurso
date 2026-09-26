"""`radar web --rede`: abrir o radar no celular, na rede de casa.

Nenhum teste sobe servidor: o uvicorn.run e trocado por um que so anota
onde ele ia escutar.
"""
import socket

import pytest
import uvicorn
from typer.testing import CliRunner

from radar import cli, util


@pytest.fixture
def subiu(monkeypatch):
    """Anota o host e a porta que o comando mandaria para o uvicorn."""
    chamadas = []
    monkeypatch.setattr(uvicorn, "run", lambda app, **kw: chamadas.append(kw))
    monkeypatch.setattr(cli, "porta_ocupada", lambda host, porta: False)
    return chamadas


def _rodar(*args):
    return CliRunner().invoke(cli.app, ["web", *args], env={"COLUMNS": "200"})


def test_host_do_servidor():
    assert cli.host_do_servidor(True, "127.0.0.1") == "0.0.0.0"
    assert cli.host_do_servidor(False, "127.0.0.1") == "127.0.0.1"
    # O --host explicito continua valendo sem o --rede.
    assert cli.host_do_servidor(False, "192.168.0.5") == "192.168.0.5"


def test_sem_rede_continua_so_neste_pc(subiu):
    saida = _rodar()
    assert saida.exit_code == 0, saida.output
    assert subiu == [{"host": "127.0.0.1", "port": 8000}]
    assert "celular" not in saida.output


def test_com_rede_escuta_em_todas_as_placas_e_mostra_o_endereco(subiu, monkeypatch):
    monkeypatch.setattr(cli, "ip_local", lambda: "192.168.0.10")
    saida = _rodar("--rede", "--porta", "8123")
    assert saida.exit_code == 0, saida.output
    assert subiu == [{"host": "0.0.0.0", "port": 8123}]
    assert "Abra no celular (mesmo Wi-Fi): http://192.168.0.10:8123/hoje" in saida.output
    assert "Sem senha" in saida.output


def test_sem_achar_o_ip_manda_rodar_ipconfig(subiu, monkeypatch):
    monkeypatch.setattr(cli, "ip_local", lambda: None)
    saida = _rodar("--rede")
    assert subiu[0]["host"] == "0.0.0.0"
    assert "ipconfig" in saida.output


# --- descobrir o IP sem ir a internet ------------------------------------------

class _SocketFalso:
    """Um socket UDP que 'conecta' e diz qual placa usaria. Nao manda nada."""

    def __init__(self, ip=None, erro=False):
        self.ip, self.erro = ip, erro

    def __call__(self, *args, **kwargs):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def connect(self, endereco):
        if self.erro:
            raise OSError("sem rota")

    def getsockname(self):
        return (self.ip, 50000)


def test_ip_pela_rota(monkeypatch):
    monkeypatch.setattr(socket, "socket", _SocketFalso("192.168.1.42"))
    assert util.ip_local() == "192.168.1.42"


def test_sem_rota_tenta_o_nome_da_maquina(monkeypatch):
    monkeypatch.setattr(socket, "socket", _SocketFalso(erro=True))
    monkeypatch.setattr(socket, "gethostbyname", lambda nome: "10.0.0.7")
    assert util.ip_local() == "10.0.0.7"


def test_so_loopback_e_none(monkeypatch):
    monkeypatch.setattr(socket, "socket", _SocketFalso(erro=True))
    monkeypatch.setattr(socket, "gethostbyname", lambda nome: "127.0.1.1")
    assert util.ip_local() is None
