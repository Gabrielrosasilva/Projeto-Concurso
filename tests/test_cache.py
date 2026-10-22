"""Guardar o que nao muda, sem mudar resultado (pedido de 22/10).

O que estes testes seguram:

  * `por_requisicao` guarda so dentro de uma requisicao, e so dentro de um
    GET - o POST grava, e a conta depois dele tem de ver o que ele gravou;
  * `do_arquivo` le o arquivo de novo quando o conteudo muda;
  * o cronograma guardado nao muda na mao de quem o recebe: cada um ganha a
    sua copia.

Nada aqui depende do dia nem da internet.
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from radar import cache, cronograma
from radar.web.app import uma_conta_por_abertura

MINI = Path(__file__).parent / "fixtures" / "cronograma_mini.yml"


def test_fora_de_uma_requisicao_nada_e_guardado():
    vezes = []

    @cache.por_requisicao
    def conta(x):
        vezes.append(x)
        return x * 2

    assert (conta(2), conta(2)) == (4, 4)
    assert vezes == [2, 2]


def test_dentro_da_requisicao_a_mesma_conta_e_feita_uma_vez_e_some_no_fim():
    vezes = []

    @cache.por_requisicao
    def conta(materias):
        vezes.append(list(materias))
        return len(materias)

    with cache.requisicao():
        assert conta(["a", "b"]) == conta(["a", "b"]) == 2   # a lista vira chave
        assert conta(["c"]) == 1
    with cache.requisicao():
        conta(["a", "b"])

    assert vezes == [["a", "b"], ["c"], ["a", "b"]]


def test_so_o_get_guarda_e_o_post_ve_o_que_gravou():
    vezes = []

    @cache.por_requisicao
    def conta():
        vezes.append(1)
        return len(vezes)

    teste = FastAPI()
    teste.middleware("http")(uma_conta_por_abertura)

    @teste.get("/ver")
    def ver():
        return [conta(), conta()]

    @teste.post("/gravar")
    def gravar():
        return [conta(), conta()]

    cliente = TestClient(teste)

    assert cliente.get("/ver").json() == [1, 1]          # uma vez no GET
    assert cliente.post("/gravar").json() == [2, 3]      # sem guardar no POST
    assert cliente.get("/ver").json() == [4, 4]          # e o GET seguinte refaz


def test_o_arquivo_e_lido_de_novo_quando_o_conteudo_muda(tmp_path):
    arquivo = tmp_path / "x.yml"
    arquivo.write_text("um", encoding="utf-8")
    lidas = []

    def ler():
        lidas.append(arquivo.read_text(encoding="utf-8"))
        return lidas[-1]

    assert cache.do_arquivo(arquivo, ler, nome="t") == "um"
    assert cache.do_arquivo(arquivo, ler, nome="t") == "um"
    arquivo.write_text("do", encoding="utf-8")   # mesmo tamanho, outro conteudo

    assert cache.do_arquivo(arquivo, ler, nome="t") == "do"
    assert lidas == ["um", "do"]


def test_o_cronograma_guardado_nao_muda_na_mao_de_quem_recebe(tmp_path, monkeypatch):
    pasta = tmp_path / "config"
    pasta.mkdir()
    (pasta / "cronograma.yml").write_text(MINI.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setenv("RADAR_CONFIG_DIR", str(pasta))

    primeiro = cronograma.carregar()
    primeiro.dias.clear()
    segundo = cronograma.carregar()

    assert primeiro is not segundo
    assert segundo.dias, "a copia de quem alterou nao pode valer para o proximo"
