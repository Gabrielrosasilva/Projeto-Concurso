"""O link do Qconcursos de cada tema (decisao 140).

O radar nao consulta o site: os numeros dos assuntos moram no
config/qconcursos.yml, tirados das listas que o usuario copiou, e aqui so se
monta o endereco. Os testes seguram o formato do link (o mesmo que o site
gera), a leitura do arquivo e a cobertura do cronograma real.

Nada aqui depende do dia em que o teste roda.
"""
from datetime import datetime
from types import SimpleNamespace

from fastapi.testclient import TestClient

from radar import cronograma, fichas, qconcursos
from radar.servico import cronograma as diario
from radar.util import fuso_local
from radar.web.app import app

#: O link que o usuario copiou do site em 06/10/2026: Direito Constitucional,
#: FEPESE, sem anuladas nem desatualizadas, "5 Direitos Individuais".
DO_SITE = ("https://www.qconcursos.com/questoes-de-concursos/questoes?"
           "discipline_ids%5B%5D=3&examining_board_ids%5B%5D=61&exclude_nullified=true"
           "&exclude_outdated=true&per_page=20&subject_ids%5B%5D=16321")

#: Os temas sem assunto no site: falta a lista da disciplina Redacao Oficial.
SEM_ASSUNTO = {"Redação oficial 1: atributos e tratamento", "Redação oficial 2: o padrão ofício"}


def test_o_link_e_o_mesmo_que_o_site_gera():
    link = qconcursos.LinkDoTema(tema="x", banca=61, disciplina=3,
                                 assuntos=((16321, "5 Direitos Individuais"),))
    assert link.url == DO_SITE


def test_varios_assuntos_vao_repetidos_no_link():
    link = qconcursos.LinkDoTema(tema="x", banca=61, disciplina=3,
                                 assuntos=((16323, "a"), (16327, "b")))
    assert link.url.endswith("&subject_ids%5B%5D=16323&subject_ids%5B%5D=16327")
    assert link.nomes == ["a", "b"]


def _arquivo(tmp_path):
    caminho = tmp_path / "qconcursos.yml"
    caminho.write_text(
        "banca: 61\n"
        "temas:\n"
        '  - tema: "Vozes do verbo"\n'
        "    disciplina: 1\n"
        "    assuntos:\n"
        '      16180: "3.6 Flexão de voz (ativa, passiva, reflexiva)"\n'
        '  - tema: "Trabalho do preso (arts. 28 a 37)"\n'
        "    disciplina: 9\n"
        "    assuntos:\n"
        '      17467: "40.3 Lei de Execução Penal"\n'
        '    aviso: "O Qconcursos não divide a LEP."\n',
        encoding="utf-8")
    return caminho


def test_le_o_arquivo_e_acha_o_tema_sem_acento_nem_caixa(tmp_path):
    links = qconcursos.carregar(_arquivo(tmp_path))

    vozes = qconcursos.do_tema("VOZES do verbo", links)
    assert vozes.disciplina == 1 and vozes.banca == 61
    assert vozes.assuntos == ((16180, "3.6 Flexão de voz (ativa, passiva, reflexiva)"),)
    assert vozes.aviso is None
    assert qconcursos.do_tema("Trabalho do preso (arts. 28 a 37)", links).aviso == \
        "O Qconcursos não divide a LEP."
    assert qconcursos.do_tema("Tema que não está", links) is None


def test_sem_o_arquivo_nenhum_tema_tem_link(tmp_path):
    assert qconcursos.carregar(tmp_path / "nao_existe.yml") == {}


def test_a_faixa_pelo_titulo_e_so_a_do_qconcursos(tmp_path):
    links = qconcursos.carregar(_arquivo(tmp_path))

    def faixa(titulo, onde="qconcursos"):
        return SimpleNamespace(titulo=titulo, onde=onde, materia="Língua Portuguesa")

    # O prefixo sai, como na ficha: a revisao do tema ganha o mesmo link.
    assert qconcursos.da_faixa(faixa("R+7: Vozes do verbo"), links).disciplina == 1
    # A teoria do mesmo tema nao e no Qconcursos: sem link.
    assert qconcursos.da_faixa(faixa("Vozes do verbo", onde="lei"), links) is None
    assert qconcursos.da_faixa(None, links) is None


def test_o_arquivo_real_cobre_todo_tema_do_cronograma_que_vai_ao_qconcursos():
    links = qconcursos.carregar()
    plano = cronograma.carregar()
    faltam = set()
    for dia in plano.dias:
        for faixa in dia.faixas():
            if faixa.onde == "qconcursos" and faixa.tipo in ("questoes", "revisao"):
                tema = fichas.tema_da_faixa(faixa.titulo, faixa.materia)
                if qconcursos.do_tema(tema, links) is None:
                    faltam.add(tema)
    assert faltam == SEM_ASSUNTO


def test_o_arquivo_real_tem_numero_e_nome_em_todo_assunto():
    links = qconcursos.carregar()
    assert len(links) == 62
    for link in links.values():
        assert link.banca == 61
        assert link.assuntos, link.tema
        for numero, nome in link.assuntos:
            assert isinstance(numero, int) and nome.strip(), link.tema


def test_a_faixa_do_art_5_abre_o_filtro_pronto(banco_temporario, monkeypatch):
    monkeypatch.setattr(diario, "agora_local",
                        lambda: datetime(2026, 10, 6, 12, 0, tzinfo=fuso_local()))

    pagina = TestClient(app).get("/hoje?data=2026-10-06").text

    assert "Abrir no Qconcursos" in pagina
    assert ("subject_ids%5B%5D=16323&amp;subject_ids%5B%5D=16327"
            "&amp;subject_ids%5B%5D=16265") in pagina
    assert "5.6 Direito de Propriedade e Função Social da Propriedade" in pagina
    assert "traz também as liberdades dos incisos I a XVI" in pagina
    assert "pelo botão “Abrir no Qconcursos” acima" in pagina
