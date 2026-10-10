"""Gerar com nivel: o `--nivel` do pedido, a mistura e o comando (decisao 151).

Misturada sao partes iguais, a sobra na media (10 = 3/4/3), repartidas entre
os pedidos do lote. A importacao recusa a questao sem nivel, com nivel fora
da lista ou sem o porque, e conta a mistura ("pedi 3/4/3, veio 5/3/2") sem
completar nada. E todo lugar que mostra o `gerar --pedido` leva o `--nivel`.
"""
import html
import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from radar import cli, fichas, niveis, servico
from radar.servico import manual
from radar.web.app import app
from tests.test_fichas import CASA, DC, DIREITOS, arvore_no_banco, com_ficha_real  # noqa: F401
from tests.test_geradas_da_faixa import em_05_10  # noqa: F401
from tests.test_ia_manual import acervo_do_alvo  # noqa: F401
from tests.test_treinar_pelo_no import DOLO, _gerada

runner = CliRunner()
LEP = "Lei de Execução Penal"


# --- a mistura ----------------------------------------------------------------

@pytest.mark.parametrize("quantas, esperado", [
    (10, "3/4/3"), (11, "3/5/3"), (19, "6/7/6"), (20, "6/8/6"),
    (5, "1/3/1"), (4, "1/2/1"), (1, "0/1/0"),
])
def test_misturada_e_partes_iguais_com_a_sobra_na_media(quantas, esperado):
    assert niveis.descrever(niveis.dividir(quantas)) == esperado


def test_um_nivel_so_leva_tudo_e_nivel_que_nao_existe_para():
    assert niveis.dividir(10, "dificil") == {"facil": 0, "media": 0, "dificil": 10}
    with pytest.raises(ValueError):
        niveis.dividir(10, "medio")


def test_a_mistura_do_lote_e_repartida_entre_os_pedidos():
    """O lote do abolitio: 19 em pedidos de 3 e um de 1. Cada pedido de 3
    sai 1/1/1, o de 1 leva a media, e a soma e 6/7/6."""
    partes = niveis.repartir([3, 3, 3, 3, 3, 3, 1], niveis.dividir(19))
    assert partes[:6] == [{"facil": 1, "media": 1, "dificil": 1}] * 6
    assert partes[6] == {"facil": 0, "media": 1, "dificil": 0}
    # 10 em 3+3+3+1: a soma bate com o 3/4/3.
    soma = {c: 0 for c in niveis.NIVEIS}
    for parte in niveis.repartir([3, 3, 3, 1], niveis.dividir(10)):
        for chave, n in parte.items():
            soma[chave] += n
    assert niveis.descrever(soma) == "3/4/3"


# --- o pedido -----------------------------------------------------------------

def test_o_pedido_leva_o_nivel_de_cada_pedido_e_os_criterios(acervo_do_alvo):
    lote = manual.pedido_de_questoes(LEP, 5)            # 3 + 2, misturada

    assert lote["nivel"] == "misturada"
    assert [p["niveis"] for p in lote["pedidos"]] == [
        {"facil": 1, "media": 1, "dificil": 1}, {"facil": 0, "media": 2, "dificil": 0}]
    primeiro = lote["pedidos"][0]["instrucao"]
    assert "escreva exatamente: 1 facil, 1 media e 1 dificil." in primeiro
    for nivel in niveis.NIVEIS.values():
        assert nivel.criterio in primeiro
    assert niveis.CRITERIO_FORA_DO_DIREITO in primeiro
    assert "`radar gerar --pedido --nivel misturada`" in lote["como_responder"]
    assert "por_que_o_nivel" in lote["como_responder"]
    [item] = lote["formato_da_resposta"]["respostas"][0]["questoes"]
    assert item["nivel"] and item["por_que_o_nivel"]


def test_o_pedido_de_um_nivel_so(acervo_do_alvo):
    lote = manual.pedido_de_questoes(LEP, 5, nivel="dificil")

    assert [p["niveis"]["dificil"] for p in lote["pedidos"]] == [3, 2]
    assert "escreva exatamente: 3 dificil." in lote["pedidos"][0]["instrucao"]


# --- a importacao -------------------------------------------------------------

def _questao(numero: int, nivel: str | None = "media", por_que="pelo criterio") -> dict:
    item = {"enunciado": f"Questao gerada de numero {numero}, sobre a LEP?",
            "alternativas": {l: f"alternativa {l}" for l in "abcde"},
            "resposta": "a", "artigo": "LEP, art. 41"}
    if nivel is not None:
        item["nivel"] = nivel
    if por_que is not None:
        item["por_que_o_nivel"] = por_que
    return item


def _lote_10(tmp_path) -> Path:
    """Um lote amplo de 10 do zero (3+3+3+1), com a mistura 3/4/3."""
    partes = niveis.repartir([3, 3, 3, 1], niveis.dividir(10))
    pedidos = [{"id": f"p{n}", "modo": "do_zero", "quantas": tamanho,
                "materia": LEP, "assunto": None, "origem_impressao": None,
                "origem_chave": None, "niveis": parte}
               for n, (tamanho, parte) in enumerate(zip([3, 3, 3, 1], partes), start=1)]
    arquivo = tmp_path / "pedido.json"
    arquivo.write_text(json.dumps({"lote": "questoes-1", "tipo": "questoes",
                                   "nivel": "misturada", "pedidos": pedidos}),
                       encoding="utf-8")
    return arquivo


def _responder(tmp_path, respostas: dict) -> Path:
    arquivo = tmp_path / "resposta.json"
    arquivo.write_text(json.dumps({"lote": "questoes-1", "modelo": "claude-opus-5-5",
                                   "respostas": [{"id": i, "questoes": q}
                                                 for i, q in respostas.items()]}),
                       encoding="utf-8")
    return arquivo


def test_a_importacao_conta_a_mistura_e_nao_completa(banco_temporario, tmp_path):
    """Pedi 3/4/3 e veio 5/3/2: as 10 entram, e a saida diz a diferenca."""
    pedido = _lote_10(tmp_path)
    veio = ["facil"] * 5 + ["media"] * 3 + ["dificil"] * 2
    resposta = _responder(tmp_path, {
        "p1": [_questao(1, veio[0]), _questao(2, veio[1]), _questao(3, veio[2])],
        "p2": [_questao(4, veio[3]), _questao(5, veio[4]), _questao(6, veio[5])],
        "p3": [_questao(7, veio[6]), _questao(8, veio[7]), _questao(9, veio[8])],
        "p4": [_questao(10, veio[9])]})

    resultado = manual.importar(resposta, pedido)

    assert resultado["gravadas"] == 10 and not resultado["recusas"]
    assert niveis.descrever(resultado["niveis"]["pedi"]) == "3/4/3"
    assert niveis.descrever(resultado["niveis"]["veio"]) == "5/3/2"
    with servico.geradas.sessao() as s:
        from sqlalchemy import select

        from radar.models import QuestaoGerada

        gravadas = list(s.scalars(select(QuestaoGerada)))
    assert all(q.nivel_procedencia == "Claude Code (claude-opus-5-5), importado "
               f"manualmente, em {q.nivel_procedencia[-10:]}" for q in gravadas)
    assert {q.nivel for q in gravadas} == {"facil", "media", "dificil"}


def test_a_resposta_torta_e_recusada_e_dita(banco_temporario, tmp_path):
    pedido = _lote_10(tmp_path)
    resposta = _responder(tmp_path, {"p1": [
        _questao(1, nivel=None),                 # sem nivel
        _questao(2, nivel="muito dificil"),      # fora da lista
        _questao(3, por_que=None),               # sem o porque
    ], "p2": [_questao(4, nivel="Difícil")]})    # caixa e acento passam

    resultado = manual.importar(resposta, pedido)

    assert resultado["gravadas"] == 1
    motivos = " | ".join(resultado["recusas"])
    assert "p1, questao 1: sem o nivel" in motivos
    assert "p1, questao 2: nivel 'muito dificil' fora da lista" in motivos
    assert "p1, questao 3: sem o por_que_o_nivel" in motivos


def test_o_pedido_de_antes_do_nivel_continua_entrando_sem_nivel(banco_temporario, tmp_path):
    arquivo = tmp_path / "pedido.json"
    arquivo.write_text(json.dumps({"lote": "questoes-1", "tipo": "questoes", "pedidos": [
        {"id": "p1", "modo": "do_zero", "quantas": 1, "materia": LEP,
         "origem_impressao": None}]}), encoding="utf-8")
    resposta = _responder(tmp_path, {"p1": [_questao(1, nivel=None, por_que=None)]})

    resultado = manual.importar(resposta, arquivo)

    assert resultado["gravadas"] == 1 and "niveis" not in resultado


def test_a_cli_diz_a_mistura_na_importacao(banco_temporario, tmp_path, monkeypatch):
    pedido = _lote_10(tmp_path)
    monkeypatch.setattr(manual, "caminho_do_pedido", lambda: pedido)
    resposta = _responder(tmp_path, {"p1": [_questao(1, "facil"), _questao(2, "facil")]})

    saida = runner.invoke(cli.app, ["gerar", "--importar", str(resposta)])

    assert saida.exit_code == 0, saida.output
    assert "Nível: pedi 3/4/3 (fácil/média/difícil), veio 2/0/0." in saida.output


# --- o comando ----------------------------------------------------------------

def test_o_comando_leva_sempre_o_nivel():
    no = f"{CASA}"
    assert fichas.comando_de_gerar(no, 5).endswith("--quantas 5 --nivel misturada")
    assert fichas.comando_de_gerar(no, 5, "dificil").endswith("--nivel dificil")
    # So a materia e o simulado amplo, escrito pela mesma funcao.
    assert fichas.comando_de_gerar(DC, 10) == (
        r'.venv\Scripts\radar.exe gerar --pedido --modo simulado '
        '--materia "Direito Constitucional" --quantas 10 --nivel misturada')
    with pytest.raises(ValueError):
        fichas.comando_de_gerar(no, 5, "medio")


def test_o_terminal_aceita_o_nivel_e_recusa_o_que_nao_existe(acervo_do_alvo):
    errado = runner.invoke(cli.app, ["gerar", "--pedido", "--nivel", "medio"])
    assert errado.exit_code == 1 and "não existe" in errado.output

    certo = runner.invoke(cli.app, ["gerar", "--pedido", "--quantas", "5",
                                    "--nivel", "dificil"])
    assert certo.exit_code == 0, certo.output
    assert "Nível: Difícil" in certo.output and "0/0/5" in certo.output
    salvo = json.loads(manual.caminho_do_pedido().read_text(encoding="utf-8"))
    assert salvo["nivel"] == "dificil"


def test_a_simulacao_mostra_o_bloco_do_nivel(acervo_do_alvo):
    """A simulacao mostra o pedido palavra por palavra: com o nivel, porque
    o --valendo manda o mesmo bloco."""
    saida = runner.invoke(cli.app, ["gerar", "--nivel", "facil"],
                          env={"COLUMNS": "200"})

    assert saida.exit_code == 0, saida.output
    assert "NIVEL - cada questao tem um nivel" in saida.output
    assert "--nivel facil" in saida.output


# --- todo lugar que mostra o comando leva o --nivel ------------------------------

#: `gerar --pedido` que nao escreve questao: estes nao levam nivel.
SEM_NIVEL = re.compile(r"--(macetes|explicacoes|classificar-nivel)\b")
COMANDO = re.compile(r"gerar --pedido[^\n<]*")


def _comandos_sem_nivel(texto: str) -> list[str]:
    texto = html.unescape(texto)
    return [c for c in COMANDO.findall(texto)
            if not SEM_NIVEL.search(c) and "--nivel " not in c]


def _comandos(texto: str) -> list[str]:
    return [c for c in COMANDO.findall(html.unescape(texto)) if not SEM_NIVEL.search(c)]


def test_a_faixa_e_a_tela_de_gerar_levam_o_nivel(em_05_10):
    cliente = TestClient(app)
    hoje = cliente.get("/hoje?data=2026-10-05").text
    gerar = cliente.get("/geradas").text

    for tela in (hoje, gerar):
        assert _comandos(tela), "a tela deveria mostrar algum comando"
        assert _comandos_sem_nivel(tela) == []
        assert all("--nivel misturada" in c for c in _comandos(tela))
        assert fichas.TROQUE_O_NIVEL in html.unescape(tela)


def test_a_ficha_e_o_terminal_levam_o_nivel(com_ficha_real):
    ficha = TestClient(app).get("/fichas/art-5o-caput-e-incisos-i-a-xvi?data=2026-10-29").text
    tema = runner.invoke(cli.app, ["fichas", "--tema", "art-5o-caput-e-incisos-i-a-xvi",
                                   "--data", "2026-10-29"], env={"COLUMNS": "400"}).output
    hoje = runner.invoke(cli.app, ["hoje", "--data", "2026-10-06"],
                         env={"COLUMNS": "400"}).output

    for texto in (ficha, tema, hoje):
        assert _comandos(texto), "deveria mostrar algum comando"
        assert _comandos_sem_nivel(texto) == []
        assert fichas.TROQUE_O_NIVEL in html.unescape(texto)


def test_o_topo_da_tela_de_gerar_mostra_os_3_passos_com_o_nivel_escolhido(com_ficha_real):
    tela = TestClient(app).get("/geradas", params={
        "materia": DC, "assunto": DIREITOS.split(" > ")[1],
        "subassunto": CASA.split(" > ")[2], "quantas": 7, "nivel": "dificil"}).text

    # O do topo; "Os assuntos do cronograma" mostra os seus, com a misturada.
    do_topo = [c for c in _comandos(tela) if c.endswith("--quantas 7 --nivel dificil")]
    assert len(do_topo) == 1 and '--subassunto "Inviolabilidade do domicílio"' in do_topo[0]
    assert "Sem API, pelo Claude Code" in tela
    assert "radar gerar --quantas" not in tela          # a dica que simulava outro pedido


def test_o_resultado_da_rodada_leva_o_nivel(banco_temporario):
    """Com todas as geradas do no feitas, o resultado pede mais (decisao 142)
    - com o nivel no comando."""
    _gerada(1, DOLO)
    rodada = servico.geradas.criar_simulado(quantidade=1, conteudo=DOLO)
    cliente = TestClient(app)
    from tests.test_nivel_das_geradas import _do_banco

    cliente.post(f"/simulado/{rodada.id}/responder",
                 data={"questao_id": _do_banco("gerada1").id, "letra": "c"})
    tela = cliente.get(f"/simulado/{rodada.id}").text

    assert "Resultado da rodada" in tela
    assert _comandos(tela) and _comandos_sem_nivel(tela) == []
    assert fichas.TROQUE_O_NIVEL in html.unescape(tela)


def test_nenhum_template_escreve_o_comando_a_mao():
    """O comando de gerar questao sai so da `comando_de_gerar`: template
    nenhum o escreve, a nao ser os de macete e de explicacao."""
    pasta = Path(__file__).parents[1] / "src" / "radar" / "web" / "templates"
    for arquivo in pasta.glob("*.html"):
        assert _comandos(arquivo.read_text(encoding="utf-8")) == [], arquivo.name
