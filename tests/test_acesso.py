"""Usuario e senha para entrar pela rede (decisao 185).

O que estes testes seguram:

  * neste PC (localhost) o radar abre direto, sem senha;
  * pela rede, sem senha definida, o acesso fica fechado (403) e a pagina diz
    como definir;
  * pela rede, com senha, o navegador e pedido (401 + WWW-Authenticate), e so
    o usuario e a senha certos entram;
  * a senha nunca e guardada: o .env tem o resumo, e trocar vale na hora.

Nada aqui depende do dia nem da internet.
"""
import base64

from fastapi import FastAPI
from fastapi.testclient import TestClient

from radar.web import acesso


def _app():
    app = FastAPI()

    @app.get("/hoje")
    def hoje():
        return {"ok": True}

    return app


def _deste_pc(app):
    """O TestClient chega como "testclient"; aqui ele vira o proprio PC."""
    async def embrulho(scope, receive, send):
        scope = dict(scope, client=("127.0.0.1", 50000))
        await app(scope, receive, send)
    return embrulho


def _basic(usuario, senha):
    return {"Authorization": "Basic " + base64.b64encode(f"{usuario}:{senha}".encode()).decode()}


def _env(tmp_path, usuario="gabriel", senha="minha-senha"):
    arquivo = tmp_path / ".env"
    arquivo.write_text(f'OUTRA="fica"\n{acesso.USUARIO}="{usuario}"\n'
                       f'{acesso.RESUMO}="{acesso.resumir(senha, iteracoes=1000)}"\n',
                       encoding="utf-8")
    return arquivo


def test_o_resumo_confere_a_senha_certa_e_so_ela():
    resumo = acesso.resumir("segredo123", iteracoes=1000)

    assert "segredo123" not in resumo
    assert acesso.confere("segredo123", resumo)
    assert not acesso.confere("segredo124", resumo)
    assert not acesso.confere("segredo123", "lixo")


def test_neste_pc_abre_direto_mesmo_sem_senha(tmp_path):
    protegido = acesso.Protegido(_app(), caminho_do_env=tmp_path / ".env")

    resposta = TestClient(_deste_pc(protegido)).get("/hoje")

    assert resposta.status_code == 200


def test_pela_rede_sem_senha_definida_fica_fechado(tmp_path):
    protegido = acesso.Protegido(_app(), caminho_do_env=tmp_path / ".env")

    resposta = TestClient(protegido).get("/hoje")

    assert resposta.status_code == 403
    assert "radar senha" in resposta.text


def test_pela_rede_pede_a_senha_e_so_a_certa_entra(tmp_path):
    protegido = acesso.Protegido(_app(), caminho_do_env=_env(tmp_path))
    cliente = TestClient(protegido)

    sem = cliente.get("/hoje")
    errada = cliente.get("/hoje", headers=_basic("gabriel", "outra"))
    outro_usuario = cliente.get("/hoje", headers=_basic("joao", "minha-senha"))
    certa = cliente.get("/hoje", headers=_basic("gabriel", "minha-senha"))

    assert sem.status_code == 401
    assert sem.headers["www-authenticate"].startswith("Basic")
    assert (errada.status_code, outro_usuario.status_code) == (401, 401)
    assert certa.status_code == 200 and certa.json() == {"ok": True}


def test_trocar_a_senha_vale_na_hora(tmp_path):
    arquivo = _env(tmp_path, senha="primeira1")
    cliente = TestClient(acesso.Protegido(_app(), caminho_do_env=arquivo))
    assert cliente.get("/hoje", headers=_basic("gabriel", "primeira1")).status_code == 200

    _env(tmp_path, senha="segunda2")

    assert cliente.get("/hoje", headers=_basic("gabriel", "primeira1")).status_code == 401
    assert cliente.get("/hoje", headers=_basic("gabriel", "segunda2")).status_code == 200


def test_o_cabecalho_torto_nao_derruba_nada():
    assert acesso.do_cabecalho(None) is None
    assert acesso.do_cabecalho("Bearer xyz") is None
    assert acesso.do_cabecalho("Basic !!!nao-e-base64") is None
    assert acesso.do_cabecalho("Basic " + base64.b64encode(b"sem-dois-pontos").decode()) is None
