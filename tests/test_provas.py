"""Acervo de provas: descoberta, download e manifesto.

As fixtures em tests/fixtures/hotsite/ sao paginas REAIS do hotsite do
concurso de 2024 da Prefeitura de Palhoca, baixadas em 18/09/2026. Nenhum
teste vai a internet.
"""
import json
from pathlib import Path

import pytest

from radar import provas

FIXTURES = Path(__file__).parent / "fixtures" / "hotsite"
BASE = "https://2024cpeducapalhoca.fepese.org.br/"


def pagina(nome: str) -> str:
    return (FIXTURES / f"{nome}.html").read_text(encoding="utf-8")


@pytest.fixture
def acervo_temporario(tmp_path, monkeypatch):
    """Manda o acervo e o manifesto para uma pasta descartavel."""
    monkeypatch.setenv("RADAR_DATA_DIR", str(tmp_path))
    return tmp_path


# --- descoberta -------------------------------------------------------------

def test_acha_o_caderno_de_prova_de_cada_cargo():
    documentos = provas.ler_pagina_de_provas(pagina("provas"), BASE)
    cadernos = [d for d in documentos if d.tipo == provas.PROVA]

    assert {d.arquivo for d in cadernos} == {"M1.pdf", "S1.pdf"}


def test_o_cargo_vem_junto_com_a_prova():
    """E o que importa: o padrao da banca NO MEU cargo, nao a media de todos."""
    cadernos = {
        d.arquivo: d.cargo
        for d in provas.ler_pagina_de_provas(pagina("provas"), BASE)
        if d.tipo == provas.PROVA
    }

    assert cadernos["M1.pdf"] == "Monitor de Transporte Escolar"
    assert cadernos["S1.pdf"] == "Supervisor Escolar"


def test_gabarito_e_separado_da_prova():
    gabaritos = [
        d for d in provas.ler_pagina_de_provas(pagina("provas"), BASE)
        if d.tipo == provas.GABARITO
    ]
    assert len(gabaritos) == 2
    assert all("gabarito" in d.arquivo for d in gabaritos)


def test_rotulo_descritivo_nao_vira_nome_de_cargo():
    """A pagina repete o link: uma vez com o cargo, outra com "Caderno de
    Prova (S1)". O cargo e o que sobra depois de tirar os descritivos."""
    assert provas._cargo(["Caderno de Prova (S1)", "Supervisor Escolar"]) == "Supervisor Escolar"
    assert provas._cargo(["Gabarito Provisório"]) is None
    assert provas._cargo(["Download", "PDF"]) is None


def test_acha_o_edital():
    documentos = provas.ler_pagina_de_edital(pagina("edital"), BASE)
    assert len(documentos) == 1
    assert documentos[0].tipo == provas.EDITAL
    assert documentos[0].arquivo.endswith(".pdf")


def test_url_fica_absoluta():
    """O href do hotsite e relativo; sem juntar com a base nao da para baixar."""
    for documento in provas.ler_pagina_de_provas(pagina("provas"), BASE):
        assert documento.url.startswith("https://")


def test_pagina_sem_pdf_nao_inventa_documento():
    assert provas.ler_pagina_de_provas("<html><body>nada</body></html>", BASE) == []


# --- onde o arquivo fica ----------------------------------------------------

def test_caminho_organizado_por_banca_ano_e_municipio(acervo_temporario):
    documento = provas.Documento(
        tipo=provas.PROVA, url="https://x.test/M1.pdf", arquivo="M1.pdf",
        banca="FEPESE", ano=2024, municipio="Palhoça",
    )
    caminho = provas.destino(documento)

    assert "fepese" in str(caminho)
    assert "2024" in str(caminho)
    assert "palhoca" in str(caminho)


def test_nome_de_pasta_funciona_no_windows(acervo_temporario):
    """Acento e barra em nome de pasta quebram no Windows."""
    documento = provas.Documento(
        tipo=provas.PROVA, url="https://x.test/a.pdf", arquivo="a.pdf",
        banca="FEPESE", ano=2024, municipio="Balneário Camboriú / SC",
    )
    caminho = str(provas.destino(documento))

    assert "á" not in caminho and "ú" not in caminho


# --- download ---------------------------------------------------------------

class BuscadorFalso:
    def __init__(self, conteudo: bytes):
        self.conteudo = conteudo
        self.pedidos = 0

    def get(self, url: str):
        self.pedidos += 1

        class Resposta:
            content = self.conteudo

        return Resposta()


def test_baixa_e_calcula_o_hash(acervo_temporario):
    documento = provas.Documento(
        tipo=provas.PROVA, url="https://x.test/M1.pdf", arquivo="M1.pdf",
        banca="FEPESE", ano=2024, municipio="Palhoca",
    )
    baixado = provas.baixar(documento, BuscadorFalso(b"%PDF-1.4 conteudo"))

    assert baixado is not None
    assert len(baixado.sha256) == 64
    assert baixado.tamanho == len(b"%PDF-1.4 conteudo")
    assert (acervo_temporario / "provas").exists()


def test_pagina_de_erro_nao_entra_como_prova(acervo_temporario):
    """Servidor devolvendo HTML com HTTP 200 e comum, e nao pode virar prova."""
    documento = provas.Documento(
        tipo=provas.PROVA, url="https://x.test/M1.pdf", arquivo="M1.pdf",
        banca="FEPESE", ano=2024,
    )
    assert provas.baixar(documento, BuscadorFalso(b"<html>404</html>")) is None


def test_nao_baixa_de_novo_o_que_ja_existe(acervo_temporario):
    documento = provas.Documento(
        tipo=provas.PROVA, url="https://x.test/M1.pdf", arquivo="M1.pdf",
        banca="FEPESE", ano=2024,
    )
    buscador = BuscadorFalso(b"%PDF-1.4 conteudo")

    provas.baixar(documento, buscador)
    provas.baixar(documento, buscador)

    assert buscador.pedidos == 1


def test_erro_de_rede_nao_sobe(acervo_temporario):
    class BuscadorQuebrado:
        def get(self, url):
            raise ConnectionError("sem rede")

    documento = provas.Documento(
        tipo=provas.PROVA, url="https://x.test/M1.pdf", arquivo="M1.pdf"
    )
    assert provas.baixar(documento, BuscadorQuebrado()) is None


# --- manifesto --------------------------------------------------------------

def test_manifesto_vazio_quando_nao_ha_arquivo(acervo_temporario):
    assert provas.carregar_manifesto() == []


def test_manifesto_e_ordenado_para_o_diff_ficar_estavel(acervo_temporario):
    provas.gravar_manifesto([
        {"url": "https://x.test/z.pdf"},
        {"url": "https://x.test/a.pdf"},
    ])
    urls = [r["url"] for r in provas.carregar_manifesto()]
    assert urls == ["https://x.test/a.pdf", "https://x.test/z.pdf"]


def test_manifesto_guarda_o_que_permite_reconstruir(acervo_temporario):
    documento = provas.Documento(
        tipo=provas.PROVA, url="https://x.test/M1.pdf", arquivo="M1.pdf",
        cargo="Supervisor Escolar", banca="FEPESE", ano=2024,
        municipio="Palhoca", concurso_url="https://fepese.org.br/concurso/x",
    )
    baixado = provas.baixar(documento, BuscadorFalso(b"%PDF-1.4 x"))
    registro = provas.para_registro(baixado)

    for campo in ("url", "tipo", "arquivo", "cargo", "banca", "ano",
                  "municipio", "sha256", "concurso_url"):
        assert campo in registro, f"falta {campo} no manifesto"


def test_manifesto_nao_guarda_campo_vazio(acervo_temporario):
    """Nulo em toda linha polui o diff sem informar nada."""
    documento = provas.Documento(
        tipo=provas.EDITAL, url="https://x.test/e.pdf", arquivo="e.pdf"
    )
    assert "cargo" not in provas.para_registro(documento)


def test_manifesto_e_json_legivel(acervo_temporario):
    provas.gravar_manifesto([{"url": "https://x.test/a.pdf", "cargo": "Fiscal"}])
    texto = provas.caminho_do_manifesto().read_text(encoding="utf-8")

    assert "Fiscal" in texto
    assert texto.count("\n") > 2          # indentado
    json.loads(texto)                     # e JSON valido


def test_pdf_com_linha_em_branco_antes_do_cabecalho_vale(acervo_temporario):
    """O servidor da FEPESE manda "\n\n%PDF-1.4". O arquivo abre normalmente;
    exigir %PDF no byte zero rejeitava o acervo inteiro."""
    documento = provas.Documento(
        tipo=provas.PROVA, url="https://x.test/M1.pdf", arquivo="M1.pdf",
        banca="FEPESE", ano=2024,
    )
    assert provas.baixar(documento, BuscadorFalso(b"\n\n%PDF-1.4 conteudo")) is not None


def test_html_no_lugar_do_pdf_continua_sendo_recusado(acervo_temporario):
    documento = provas.Documento(
        tipo=provas.PROVA, url="https://x.test/M1.pdf", arquivo="M1.pdf"
    )
    pagina_de_erro = b"<html><head><title>Erro 404</title></head><body>" + b"x" * 2000
    assert provas.baixar(documento, BuscadorFalso(pagina_de_erro)) is None


def test_caminho_do_manifesto_usa_barra_normal(acervo_temporario):
    """O manifesto e versionado e serve para reconstruir o acervo em qualquer
    maquina. Contrabarra do Windows dentro dele quebraria isso no Linux."""
    documento = provas.Documento(
        tipo=provas.PROVA, url="https://x.test/M1.pdf", arquivo="M1.pdf",
        banca="FEPESE", ano=2024, municipio="Palhoca",
    )
    baixado = provas.baixar(documento, BuscadorFalso(b"%PDF-1.4 x"))

    assert "\\" not in baixado.caminho
    assert baixado.caminho.startswith("provas/")


def test_manifesto_sobrevive_a_interrupcao(banco_temporario, monkeypatch):
    """O comando leva minutos. Se parar no meio, o que ja baixou tem que
    ficar catalogado - senao a proxima rodada recomeca do zero."""
    from radar import servico
    from radar.db import sessao
    from radar.models import Concurso

    with sessao() as s:
        for i in (1, 2):
            s.add(Concurso(
                url=f"https://fepese.org.br/concurso/{i}",
                fonte="fepese", titulo=f"2024 - Prefeitura Municipal de Palhoca {i}",
                municipio="Palhoca", relevancia="nucleo", situacao="encerrado",
                tipo="concurso", extra={"hotsite": f"https://h{i}.test"},
            ))

    paginas = 0

    class BuscadorTeimoso:
        """Serve o primeiro concurso e desiste no segundo."""

        def get(self, url):
            nonlocal paginas
            if "h2.test" in url:
                raise ConnectionError("parou aqui")
            paginas += 1

            class Resposta:
                text = (
                    '<a href="?go=download&arquivo=M1.pdf">Agente de Portaria</a>'
                    '<a href="?go=download&arquivo=M1.pdf">Caderno de Prova (M1)</a>'
                )
                content = b"%PDF-1.4 x"

            return Resposta()

    monkeypatch.setattr(servico, "Buscador", BuscadorTeimoso)
    servico.montar_acervo(limite=2)

    # o primeiro concurso ficou catalogado, apesar de o segundo ter falhado
    registros = provas.carregar_manifesto()
    assert registros
    assert any(r.get("cargo") == "Agente de Portaria" for r in registros)


# --- o alvo principal entra no acervo esteja onde estiver -------------------
#
# As fixtures policia_penal_2013_provas.html e policia_penal_2019_provas.html
# sao as paginas REAIS de secjustica.fepese.org.br e sap.fepese.org.br,
# baixadas em 22/09/2026. Sao as duas unicas provas de Agente Penitenciario de
# SC que existem, e ate aqui elas ficavam de fora do acervo por serem
# `estadual` - nem `nucleo`, nem `indefinida`.

BASE_2019 = "https://sap.fepese.org.br/"
BASE_2013 = "http://secjustica.fepese.org.br/"


def test_acha_o_caderno_de_agente_penitenciario_de_2019():
    documentos = provas.ler_pagina_de_provas(pagina("policia_penal_2019_provas"),
                                             BASE_2019)
    cadernos = [d for d in documentos if d.tipo == provas.PROVA]

    assert {d.arquivo for d in cadernos} == {"AP.pdf"}
    assert "Agente Penitenci" in cadernos[0].cargo


def test_masculino_e_feminino_sao_o_mesmo_caderno():
    """A pagina de 2019 lista dois cargos, mas os dois links apontam para o
    mesmo AP.pdf: e um caderno so. Agrupar por URL evita baixar duas vezes."""
    cadernos = [
        d for d in provas.ler_pagina_de_provas(pagina("policia_penal_2019_provas"),
                                               BASE_2019)
        if d.tipo == provas.PROVA
    ]
    assert len(cadernos) == 1


def test_acha_os_dois_cargos_de_2013():
    """Em 2013 os cargos tem caderno proprio: AP e AS sao arquivos diferentes."""
    cadernos = {
        d.arquivo: d.cargo
        for d in provas.ler_pagina_de_provas(pagina("policia_penal_2013_provas"),
                                             BASE_2013)
        if d.tipo == provas.PROVA
    }

    assert set(cadernos) == {"AP.pdf", "AS.pdf"}
    assert "Agente Penitenci" in cadernos["AP.pdf"]
    assert "Socioeducativo" in cadernos["AS.pdf"]


def test_o_gabarito_dos_dois_anos_e_um_arquivo_so():
    for fixture, base in ((("policia_penal_2013_provas"), BASE_2013),
                          (("policia_penal_2019_provas"), BASE_2019)):
        gabaritos = [
            d for d in provas.ler_pagina_de_provas(pagina(fixture), base)
            if d.tipo == provas.GABARITO
        ]
        assert len(gabaritos) == 1, fixture
        assert "gabarito" in gabaritos[0].arquivo


def _concurso_alvo(**mudancas):
    from radar.models import Concurso

    base = dict(
        url="https://fepese.org.br/concurso/2013-sjc",
        fonte="fepese",
        titulo="2013 - Secretaria de Estado da Justica e Cidadania",
        uf="SC",
        tipo="concurso",
        situacao="encerrado",
        relevancia="estadual",
        alvo="principal",
        motivo_alvo="Alvo principal (Policia Penal SC).",
        extra={"hotsite": "http://secjustica.fepese.org.br/"},
    )
    base.update(mudancas)
    return Concurso(**base)


def test_alvo_principal_entra_no_acervo_mesmo_sendo_estadual(banco_temporario):
    """A regra antiga so olhava distancia, e `estadual` nao passava por ela.
    As duas provas que eu mais preciso ficavam de fora."""
    from radar import servico
    from radar.db import sessao

    with sessao() as s:
        s.add(_concurso_alvo())

    escolhidos = servico._concursos_com_prova(limite=10)
    assert [c.url for c in escolhidos] == ["https://fepese.org.br/concurso/2013-sjc"]


def test_alvo_principal_entra_no_acervo_mesmo_sendo_remoto(banco_temporario):
    """Concurso estadual e prestado onde a prova for: a distancia nao decide
    o que vale estudar."""
    from radar import servico
    from radar.db import sessao

    with sessao() as s:
        s.add(_concurso_alvo(relevancia="remoto", municipio="Chapeco"))

    assert len(servico._concursos_com_prova(limite=10)) == 1


def test_alvo_principal_vem_antes_do_que_esta_perto(banco_temporario):
    """A ordem importa porque o limite de requisicoes e curto: se so couber
    um concurso na rodada, tem que ser o meu."""
    from radar import servico
    from radar.db import sessao
    from radar.models import Concurso

    with sessao() as s:
        s.add(Concurso(
            url="https://fepese.org.br/concurso/palhoca",
            fonte="fepese", titulo="2024 - Prefeitura Municipal de Palhoca",
            municipio="Palhoca", relevancia="nucleo", situacao="encerrado",
            tipo="concurso", extra={"hotsite": "https://palhoca.test"},
        ))
        s.add(_concurso_alvo())

    escolhidos = servico._concursos_com_prova(limite=1)
    assert [c.url for c in escolhidos] == ["https://fepese.org.br/concurso/2013-sjc"]


def test_concurso_longe_sem_alvo_continua_fora(banco_temporario):
    """A regra nova abre a porta para o alvo principal, e so para ele."""
    from radar import servico
    from radar.db import sessao

    with sessao() as s:
        s.add(_concurso_alvo(
            url="https://fepese.org.br/concurso/outro",
            titulo="2020 - Prefeitura de Chapeco",
            relevancia="remoto", municipio="Chapeco",
            alvo=None, motivo_alvo=None,
        ))

    assert servico._concursos_com_prova(limite=10) == []


def test_nome_de_pasta_nao_estoura_o_limite_do_windows():
    """Bug real: o titulo de 2013 na FEPESE gruda os quatro cargos num campo
    so, dava 160 caracteres de pasta e derrubava o download no meio."""
    titulo = (
        "2013 - Secretaria de Estado da Justica e CidadaniaAgente Penitenciario "
        "(masculino)Agente Penitenciario (feminino)Agente de Seguranca "
        "Socioeducativo (masculino)Agente de Seguranca Socioeducativo (feminino)"
    )
    nome = provas._nome_seguro(titulo)

    assert len(nome) <= provas.TAMANHO_MAXIMO_DO_NOME
    assert not nome.endswith("-")       # nao corta deixando hifen solto
    assert nome.startswith("2013-secretaria")


def test_nome_curto_fica_intacto():
    assert provas._nome_seguro("Palhoca") == "palhoca"
