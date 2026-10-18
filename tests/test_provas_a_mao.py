"""O PDF que voce baixa a mao entra no acervo pela lista (decisao 172): o
radar registra o arquivo salvo em data/provas/manual/, com o link original, e
nunca vai a internet atras dele."""
from radar import config, provas, servico

PROVA = {
    "banca": "Access", "ano": 2023, "orgao": "Prefeitura de Exemplo (SP)",
    "cargo": "Guarda Civil", "pagina": "https://concursos.exemplo.org/informacoes/1/",
    "caderno": "https://cdn.exemplo.org/caderno.pdf",
    "gabarito": "https://cdn.exemplo.org/gabarito.pdf",
    "arquivo": "caderno da guarda.pdf", "arquivo_do_gabarito": "gabarito da guarda.pdf",
    "versao": "TIPO 1",
}


class SemInternet:
    def get(self, url):
        raise AssertionError(f"o radar foi buscar {url}")


def _salvar(nome: str, conteudo: bytes = b"%PDF-1.4 caderno\n%%EOF"):
    pasta = config.diretorio_dados() / "provas" / "manual"
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / nome).write_bytes(conteudo)


def test_o_pdf_baixado_a_mao_entra_com_o_link_original(banco_temporario, monkeypatch):
    monkeypatch.setattr(servico.provas, "Buscador", SemInternet)
    monkeypatch.setattr(servico.provas, "carregar_provas_de_outras_bancas", lambda: [PROVA])
    _salvar("caderno da guarda.pdf")
    _salvar("gabarito da guarda.pdf")

    resultado = servico.montar_acervo_de_outras_bancas()

    assert (resultado.provas, resultado.gabaritos, resultado.falhas) == (1, 1, 0)
    registros = {r["url"]: r for r in provas.carregar_manifesto()}
    caderno = registros["https://cdn.exemplo.org/caderno.pdf"]
    assert caderno["caminho"] == "provas/manual/caderno da guarda.pdf"
    assert caderno["concurso_url"] == "https://concursos.exemplo.org/informacoes/1/"
    assert registros["https://cdn.exemplo.org/gabarito.pdf"]["tipo"] == "gabarito"


def test_sem_o_arquivo_ou_com_o_pdf_cortado_nada_entra(banco_temporario, monkeypatch):
    monkeypatch.setattr(servico.provas, "Buscador", SemInternet)
    monkeypatch.setattr(servico.provas, "carregar_provas_de_outras_bancas", lambda: [PROVA])
    _salvar("gabarito da guarda.pdf", b"%PDF-1.4 cortado no meio")

    resultado = servico.montar_acervo_de_outras_bancas()

    assert resultado.falhas == 2 and provas.carregar_manifesto() == []
