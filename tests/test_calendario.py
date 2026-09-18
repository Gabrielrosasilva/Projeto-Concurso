"""Export .ics: os prazos no calendario do celular.

O prazo de inscricao e a unica coisa do radar que nao pode ser vista tarde
demais. O aviso do Telegram chega uma vez; o calendario lembra de novo na
vespera.
"""
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from radar import calendario, servico
from radar.db import sessao
from radar.models import Concurso
from radar.web.app import app


def _evento(**mudancas) -> calendario.Evento:
    base = dict(
        identificador="inscricao:https://x.test/1",
        titulo="Ultimo dia de inscricao: Prefeitura de Palhoca",
        quando=date(2026, 10, 5),
        descricao="Palhoca. Banca: FEPESE.",
        url="https://x.test/1",
    )
    base.update(mudancas)
    return calendario.Evento(**base)


def _concurso(url: str, **mudancas) -> Concurso:
    base = dict(
        url=url,
        fonte="teste",
        titulo="Prefeitura de Palhoca abre concurso",
        municipio="Palhoca",
        relevancia="nucleo",
        tipo="concurso",
        inscricoes_ate=datetime.now(timezone.utc) + timedelta(days=10),
    )
    base.update(mudancas)
    return Concurso(**base)


def _semear(*concursos):
    with sessao() as s:
        for c in concursos:
            s.add(c)


@pytest.fixture
def cliente(banco_temporario):
    return TestClient(app)


def _desdobrar(ics: str) -> list[str]:
    """Junta as linhas que o formato quebrou em 75 bytes."""
    linhas, atual = [], ""
    for linha in ics.split("\r\n"):
        if linha.startswith(" "):
            atual += linha[1:]
        else:
            if atual:
                linhas.append(atual)
            atual = linha
    if atual:
        linhas.append(atual)
    return linhas


# --- o formato --------------------------------------------------------------

def test_o_arquivo_abre_e_fecha_o_calendario():
    ics = calendario.montar([_evento()])

    assert ics.startswith("BEGIN:VCALENDAR")
    assert ics.rstrip().endswith("END:VCALENDAR")


def test_toda_linha_termina_em_crlf():
    """A especificacao exige CRLF. Com LF sozinho, o Outlook recusa."""
    ics = calendario.montar([_evento()])

    assert ics.endswith("\r\n")
    assert "\n" not in ics.replace("\r\n", "")


def test_linha_longa_e_dobrada_em_75_bytes():
    """Sem dobrar, um titulo longo de concurso faz o Google Agenda recusar o
    arquivo inteiro."""
    ics = calendario.montar([_evento(titulo="Concurso " + "muito longo " * 12)])

    assert all(len(linha.encode("utf-8")) <= 75 for linha in ics.split("\r\n"))


def test_a_continuacao_da_linha_comeca_com_espaco():
    ics = calendario.montar([_evento(titulo="Concurso " + "longo " * 20)])
    dobradas = [l for l in ics.split("\r\n") if l.startswith(" ")]

    assert dobradas, "a linha longa precisa ter continuacao"


def test_acento_sobrevive_a_dobra():
    """Dobrar por caractere quebraria o UTF-8 no meio de uma letra acentuada."""
    ics = calendario.montar([_evento(titulo="Concurso de Palhoça " + "x" * 80)])

    assert "Palhoça" in "".join(_desdobrar(ics))


def test_ponto_e_virgula_e_escapado():
    """Tem significado no formato: sem escapar, corta o campo ali."""
    ics = calendario.montar([_evento(descricao="Palhoca; FEPESE, superior")])
    descricao = next(l for l in _desdobrar(ics) if l.startswith("DESCRIPTION"))

    assert r"\;" in descricao and r"\," in descricao


# --- o evento ---------------------------------------------------------------

def test_o_dia_inteiro_termina_no_dia_seguinte():
    """E como o formato define dia inteiro. Com o mesmo dia nos dois, o
    compromisso some da agenda."""
    ics = calendario.montar([_evento(quando=date(2026, 10, 5))])
    linhas = _desdobrar(ics)

    assert "DTSTART;VALUE=DATE:20261005" in linhas
    assert "DTEND;VALUE=DATE:20261006" in linhas


def test_o_mesmo_concurso_gera_sempre_o_mesmo_uid():
    """E assim que o calendario ATUALIZA o compromisso quando o prazo e
    retificado, em vez de criar um duplicado."""
    primeiro = _desdobrar(calendario.montar([_evento()]))
    segundo = _desdobrar(calendario.montar([_evento(quando=date(2026, 11, 1))]))

    uid = lambda linhas: next(l for l in linhas if l.startswith("UID:"))  # noqa: E731

    assert uid(primeiro) == uid(segundo)


def test_concursos_diferentes_tem_uid_diferente():
    def uid(identificador):
        linhas = _desdobrar(calendario.montar([_evento(identificador=identificador)]))
        return next(l for l in linhas if l.startswith("UID:"))

    assert uid("a") != uid("b")


def test_o_evento_avisa_antes_da_vespera():
    """Um dia antes ja e tarde para juntar documento e pagar boleto."""
    ics = calendario.montar([_evento()])

    assert "BEGIN:VALARM" in ics
    assert f"TRIGGER:-P{calendario.DIAS_DE_AVISO}D" in ics


def test_calendario_vazio_continua_valido():
    ics = calendario.montar([])

    assert "BEGIN:VCALENDAR" in ics and "BEGIN:VEVENT" not in ics


# --- o que entra ------------------------------------------------------------

def test_entra_o_que_esta_perto_de_casa(banco_temporario):
    _semear(_concurso("https://x.test/perto"))

    assert len(servico.eventos_do_calendario()) == 1


def test_entra_o_favorito_ainda_que_longe(banco_temporario):
    """Favorito e escolha minha, e nenhum filtro o esconde."""
    _semear(_concurso("https://x.test/longe", relevancia="remoto",
                      interesse=servico.FAVORITO))

    assert len(servico.eventos_do_calendario()) == 1


def test_longe_e_sem_favorito_fica_de_fora(banco_temporario):
    _semear(_concurso("https://x.test/longe", relevancia="remoto"))

    assert servico.eventos_do_calendario() == []


def test_prazo_vencido_nao_vira_compromisso(banco_temporario):
    """Compromisso no passado so atrapalha quem abre a agenda."""
    _semear(_concurso("https://x.test/velho",
                      inscricoes_ate=datetime.now(timezone.utc) - timedelta(days=5)))

    assert servico.eventos_do_calendario() == []


def test_sem_prazo_conhecido_nao_entra(banco_temporario):
    _semear(_concurso("https://x.test/sem", inscricoes_ate=None))

    assert servico.eventos_do_calendario() == []


def test_noticia_nao_entra(banco_temporario):
    _semear(_concurso("https://x.test/noticia", tipo="noticia"))

    assert servico.eventos_do_calendario() == []


def test_a_data_da_prova_vira_um_segundo_compromisso(banco_temporario):
    _semear(_concurso("https://x.test/comprova",
                      data_prova=datetime.now(timezone.utc) + timedelta(days=60)))

    titulos = [e.titulo for e in servico.eventos_do_calendario()]

    assert any(t.startswith("Ultimo dia") for t in titulos)
    assert any(t.startswith("Prova:") for t in titulos)


def test_a_descricao_leva_o_que_eu_preciso_saber(banco_temporario):
    _semear(_concurso("https://x.test/desc", banca="FEPESE", salario=5200))

    descricao = servico.eventos_do_calendario()[0].descricao

    assert "Palhoca" in descricao and "FEPESE" in descricao and "5.200" in descricao


# --- a rota -----------------------------------------------------------------

def test_a_rota_serve_como_arquivo(cliente):
    _semear(_concurso("https://x.test/rota"))

    resposta = cliente.get("/calendario.ics")

    assert resposta.status_code == 200
    assert resposta.headers["content-type"].startswith("text/calendar")
    assert "radar.ics" in resposta.headers["content-disposition"]


def test_a_rota_traz_os_compromissos(cliente):
    _semear(_concurso("https://x.test/rota"))

    assert "Ultimo dia de inscricao" in cliente.get("/calendario.ics").text


# --- a pagina que explica ---------------------------------------------------

def test_a_pagina_explica_para_que_serve(cliente):
    """Antes, o link da barra baixava o arquivo direto - e um .ics que aparece
    do nada nao diz o que e nem o que fazer com ele."""
    _semear(_concurso("https://x.test/pagina"))

    texto = cliente.get("/calendario").text

    assert "Para que serve" in texto
    assert "dois dias antes" in texto


def test_a_pagina_mostra_o_que_vai_entrar_na_agenda(cliente):
    _semear(_concurso("https://x.test/pagina"))

    texto = cliente.get("/calendario").text

    assert "Prefeitura de Palhoca" in texto


def test_a_pagina_ensina_a_importar(cliente):
    _semear(_concurso("https://x.test/pagina"))

    texto = cliente.get("/calendario").text

    assert "Google Agenda" in texto and "Outlook" in texto


def test_sem_prazo_nenhum_a_pagina_explica_o_que_entra(cliente):
    assert "Nenhum prazo em pe" in cliente.get("/calendario").text


def test_a_pagina_leva_ao_arquivo(cliente):
    _semear(_concurso("https://x.test/pagina"))

    assert 'href="/calendario.ics"' in cliente.get("/calendario").text


def test_o_link_da_barra_abre_a_pagina_e_nao_o_arquivo(cliente):
    _semear(_concurso("https://x.test/pagina"))

    assert 'href="/calendario"' in cliente.get("/").text
