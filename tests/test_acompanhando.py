"""A aba Acompanhando, e o aviso de mudanca no que eu sigo.

O pedido da etapa 8: "um bloco por favorito, com a linha do tempo dos eventos
(data e link), a proxima acao e a contagem de dias. O Telegram avisa so as
mudancas importantes de favorito: edital, retificacao, inscricao abre ou
fecha, prova marcada. Nenhum filtro esconde favorito."

Nada aqui vai a internet: o envio do Telegram e substituido por uma funcao
falsa que so guarda o que teria sido mandado.
"""
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from radar import acompanhando, avisos, servico
from radar import eventos as linha_do_tempo
from radar.db import sessao
from radar.models import Concurso, Evento, agora
from radar.util import formatar_data
from radar.web.app import app


def dias(n: int):
    return agora() + timedelta(days=n)


def _concurso(url: str, **mudancas) -> Concurso:
    base = dict(
        url=url,
        fonte="teste",
        titulo="Concurso Prefeitura de Palhoca (SC) para Guarda Municipal",
        uf="SC",
        municipio="Palhoca",
        tipo="concurso",
        relevancia="nucleo",
        situacao="edital_publicado",
    )
    base.update(mudancas)
    return Concurso(**base)


def _semear(*concursos) -> list[int]:
    with sessao() as s:
        for c in concursos:
            s.add(c)
    with sessao() as s:
        return [c.id for c in s.scalars(select(Concurso).order_by(Concurso.id))]


def _evento(url: str, tipo: str, descricao: str, link=None, data=None):
    with sessao() as s:
        linha_do_tempo.registrar(s, url, tipo, descricao, link, data)


@pytest.fixture
def cliente(banco_temporario):
    return TestClient(app)


@pytest.fixture
def telegram(monkeypatch):
    """Finge que o Telegram esta configurado e captura o que seria enviado."""
    monkeypatch.setenv("RADAR_TELEGRAM_TOKEN", "token-de-teste")
    monkeypatch.setenv("RADAR_TELEGRAM_CHAT_ID", "123456")

    enviadas: list[str] = []

    def falso_enviar(texto: str) -> bool:
        enviadas.append(texto)
        return True

    monkeypatch.setattr(avisos, "enviar", falso_enviar)
    monkeypatch.setattr(avisos, "PAUSA_ENTRE_MENSAGENS", 0)  # teste nao espera
    return enviadas


# --- a proxima acao ---------------------------------------------------------

def test_prazo_correndo_manda_inscrever():
    acao = acompanhando.proxima_acao(
        _concurso("https://a.test/1", situacao="inscricoes_abertas"), dias=5
    )
    assert "Inscrever-se" in acao.texto
    assert "5 dia" in acao.texto
    assert acao.urgente


def test_prazo_folgado_nao_e_urgente():
    acao = acompanhando.proxima_acao(
        _concurso("https://a.test/1", situacao="inscricoes_abertas"), dias=40
    )
    assert not acao.urgente


def test_ultimo_dia_grita():
    acao = acompanhando.proxima_acao(
        _concurso("https://a.test/1", situacao="inscricoes_abertas"), dias=0
    )
    assert "HOJE" in acao.texto
    assert acao.urgente


def test_aberta_sem_data_limite_manda_conferir_na_fonte():
    """Situacao diz aberta, mas eu nao sei ate quando: isso e urgente, e a
    tela nao pode inventar uma data para preencher o espaco."""
    acao = acompanhando.proxima_acao(
        _concurso("https://a.test/1", situacao="inscricoes_abertas"), dias=None
    )
    assert acao.urgente
    assert "não sei" in acao.texto


def test_registro_que_se_contradiz_manda_conferir():
    """Diz aberta e a data ja venceu: quem manda e a data, e eu quero saber
    que o registro esta velho em vez de ver "faltam -3 dias"."""
    acao = acompanhando.proxima_acao(
        _concurso("https://a.test/1", situacao="inscricoes_abertas"), dias=-3
    )
    assert "Conferir na fonte" in acao.texto


def test_banca_definida_manda_estudar_o_padrao():
    acao = acompanhando.proxima_acao(
        _concurso("https://a.test/1", situacao="banca_definida"), dias=None
    )
    assert "padrão da banca" in acao.texto


@pytest.mark.parametrize("situacao,pedaco", [
    ("edital_publicado", "Ler o edital"),
    ("prevista", "Só acompanhar"),
    ("autorizado", "Só acompanhar"),
    ("encerrado", "encerrada"),
])
def test_cada_situacao_tem_a_sua_acao(situacao, pedaco):
    acao = acompanhando.proxima_acao(
        _concurso("https://a.test/1", situacao=situacao), dias=None
    )
    assert pedaco in acao.texto
    assert acao.sei


def test_situacao_desconhecida_diz_que_nao_sabe():
    """Nunca chutar: a tela prefere admitir que nao sabe."""
    acao = acompanhando.proxima_acao(
        _concurso("https://a.test/1", situacao=None), dias=None
    )
    assert not acao.sei


# --- os blocos --------------------------------------------------------------

def test_so_entra_quem_eu_marquei(banco_temporario):
    ids = _semear(
        _concurso("https://a.test/1", titulo="O que eu sigo"),
        _concurso("https://a.test/2", titulo="O que eu nao sigo"),
    )
    servico.favoritar(ids[0])

    titulos = [b.concurso.titulo for b in acompanhando.blocos()]
    assert titulos == ["O que eu sigo"]


def test_o_que_fecha_antes_vem_antes(banco_temporario):
    """E quem nao tem prazo conhecido vai para o fim, nao some: e justamente
    o que falta descobrir."""
    ids = _semear(
        _concurso("https://a.test/1", titulo="Fecha depois", inscricoes_ate=dias(30)),
        _concurso("https://a.test/2", titulo="Sem prazo", inscricoes_ate=None),
        _concurso("https://a.test/3", titulo="Fecha logo", inscricoes_ate=dias(3)),
    )
    for id_ in ids:
        servico.favoritar(id_)

    assert [b.concurso.titulo for b in acompanhando.blocos()] == [
        "Fecha logo", "Fecha depois", "Sem prazo"
    ]


def test_a_linha_do_tempo_vem_do_mais_novo_para_o_mais_velho(banco_temporario):
    """Ao contrario de `radar eventos`, que conta a historia desde o comeco:
    aqui eu quero saber o que mudou por ultimo."""
    (id_,) = _semear(_concurso("https://a.test/1"))
    servico.favoritar(id_)
    _evento("https://a.test/1", "apareceu", "Entrou no radar", data=dias(-20))
    _evento("https://a.test/1", "edital_publicado",
            "Situacao: prevista -> edital_publicado", data=dias(-2))

    (bloco,) = acompanhando.blocos()
    assert [e.tipo for e in bloco.eventos] == ["edital_publicado", "apareceu"]


def test_a_contagem_de_dias_sai_do_prazo(banco_temporario):
    """4 e nao 5: `dias(5)` cai daqui a cinco dias menos as horas de hoje, e
    a conta e em dias inteiros."""
    (id_,) = _semear(_concurso("https://a.test/1", inscricoes_ate=dias(5)))
    servico.favoritar(id_)

    (bloco,) = acompanhando.blocos()
    assert bloco.dias_ate_fechar == 4
    assert not bloco.fechou


def test_prazo_vencido_e_marcado_como_fechado(banco_temporario):
    (id_,) = _semear(_concurso("https://a.test/1", inscricoes_ate=dias(-2)))
    servico.favoritar(id_)

    (bloco,) = acompanhando.blocos()
    assert bloco.fechou


def test_sem_prazo_a_contagem_e_nula(banco_temporario):
    (id_,) = _semear(_concurso("https://a.test/1", inscricoes_ate=None))
    servico.favoritar(id_)

    (bloco,) = acompanhando.blocos()
    assert bloco.dias_ate_fechar is None
    assert not bloco.fechou


# --- a tela -----------------------------------------------------------------

def test_a_aba_mostra_o_bloco_inteiro(cliente):
    (id_,) = _semear(_concurso(
        "https://a.test/1",
        titulo="Guarda Municipal de Palhoca",
        situacao="inscricoes_abertas",
        inscricoes_ate=dias(6),
    ))
    servico.favoritar(id_)
    _evento("https://a.test/1", "edital_retificado",
            "Edital retificado: edital.pdf", link="https://a.test/edital.pdf")

    texto = cliente.get("/acompanhando").text

    assert "Guarda Municipal de Palhoca" in texto      # o concurso
    assert "inscrição fecha em" in texto               # a contagem de dias
    assert "Próxima ação" in texto                     # o que fazer
    assert "Inscrever-se" in texto
    assert "edital retificado" in texto                # a linha do tempo
    assert "https://a.test/edital.pdf" in texto        # com o link do evento


def test_a_data_do_evento_aparece_na_tela(cliente):
    (id_,) = _semear(_concurso("https://a.test/1"))
    servico.favoritar(id_)
    _evento("https://a.test/1", "apareceu", "Entrou no radar", data=dias(-3))

    # Pela MESMA funcao que a tela usa. Comparar com um strftime aqui passava
    # o dia inteiro e falhava entre 21h e meia-noite: o teste monta a data em
    # UTC e a tela mostra em horario local, que nessa faixa ja e outro dia.
    esperada = formatar_data(dias(-3))
    assert esperada in cliente.get("/acompanhando").text


def test_favorito_sem_evento_explica_o_vazio(cliente):
    """Concurso que ja estava no banco antes da tabela `eventos` existir
    aparece sem historico - e a tela diz por que, em vez de so calar."""
    (id_,) = _semear(_concurso("https://a.test/1"))
    servico.favoritar(id_)

    assert "Nada registrado ainda" in cliente.get("/acompanhando").text


def test_aba_vazia_explica_como_usar(cliente):
    _semear(_concurso("https://a.test/1"))

    texto = cliente.get("/acompanhando").text
    assert "Clique na estrela" in texto


# --- o que vira mensagem no Telegram ----------------------------------------

def test_avisa_a_mudanca_do_favorito(banco_temporario, telegram):
    (id_,) = _semear(_concurso("https://a.test/1", inscricoes_ate=dias(10)))
    servico.favoritar(id_)
    _evento("https://a.test/1", "edital_publicado",
            "Situacao: prevista -> edital_publicado",
            link="https://a.test/edital.pdf")

    assert servico.avisar_favoritos().enviados == 1
    assert "Edital publicado" in telegram[0]
    assert "https://a.test/edital.pdf" in telegram[0]
    assert "faltam" in telegram[0]


@pytest.mark.parametrize("tipo", list(linha_do_tempo.EVENTOS_IMPORTANTES))
def test_os_cinco_tipos_importantes_avisam(banco_temporario, telegram, tipo):
    """Edital, retificacao, inscricao abrindo, inscricao fechando e prova
    marcada: os cinco que mudam o que eu tenho que fazer."""
    (id_,) = _semear(_concurso("https://a.test/1"))
    servico.favoritar(id_)
    _evento("https://a.test/1", tipo, "Alguma coisa mudou")

    assert servico.avisar_favoritos().enviados == 1


@pytest.mark.parametrize("tipo", ["apareceu", "mudou_situacao"])
def test_tramite_nao_toca_o_celular(banco_temporario, telegram, tipo):
    """Eles ficam na linha do tempo, para eu ler quando quiser."""
    (id_,) = _semear(_concurso("https://a.test/1"))
    servico.favoritar(id_)
    _evento("https://a.test/1", tipo, "Situacao: prevista -> autorizado")

    assert servico.avisar_favoritos().enviados == 0
    assert telegram == []


def test_nao_avisa_mudanca_de_quem_eu_nao_sigo(banco_temporario, telegram):
    """Sem a estrela, e ruido: sao centenas de concursos no banco."""
    _semear(_concurso("https://a.test/1"))
    _evento("https://a.test/1", "edital_publicado", "Saiu o edital")

    assert servico.avisar_favoritos().enviados == 0


def test_favorito_longe_avisa_do_mesmo_jeito(banco_temporario, telegram):
    """Aqui nao ha filtro de distancia: eu marquei a estrela, eu quero saber.

    E a diferenca entre este aviso e o de concurso novo - aquele responde
    "apareceu algo que pode me interessar?", e por isso filtra."""
    (id_,) = _semear(_concurso(
        "https://a.test/1", relevancia="remoto", municipio="Capinzal"
    ))
    servico.favoritar(id_)
    _evento("https://a.test/1", "inscricoes_abertas", "Prazo de inscricao aberto")

    assert servico.avisar_favoritos().enviados == 1


def test_nao_avisa_duas_vezes_o_mesmo_evento(banco_temporario, telegram):
    """A coleta de amanha nao pode repetir o aviso de hoje."""
    (id_,) = _semear(_concurso("https://a.test/1"))
    servico.favoritar(id_)
    _evento("https://a.test/1", "prova_marcada", "Prova marcada para 10/05/2026")

    assert servico.avisar_favoritos().enviados == 1
    assert servico.avisar_favoritos().enviados == 0
    assert len(telegram) == 1


def test_marca_a_data_do_aviso(banco_temporario, telegram):
    (id_,) = _semear(_concurso("https://a.test/1"))
    servico.favoritar(id_)
    _evento("https://a.test/1", "prova_marcada", "Prova marcada para 10/05/2026")
    servico.avisar_favoritos()

    with sessao() as s:
        assert s.scalar(select(Evento)).avisado_em is not None


def test_telegram_fora_do_ar_deixa_a_fila_em_pe(banco_temporario, telegram,
                                                monkeypatch):
    """Sem isso, a mudanca que eu mais queria saber sumia de vez."""
    (id_,) = _semear(_concurso("https://a.test/1"))
    servico.favoritar(id_)
    _evento("https://a.test/1", "edital_publicado", "Saiu o edital")

    monkeypatch.setattr(avisos, "enviar", lambda texto: False)
    assert servico.avisar_favoritos().enviados == 0

    with sessao() as s:
        assert s.scalar(select(Evento)).avisado_em is None


def test_sem_telegram_configurado_nao_quebra(banco_temporario, monkeypatch):
    monkeypatch.delenv("RADAR_TELEGRAM_TOKEN", raising=False)
    monkeypatch.delenv("RADAR_TELEGRAM_CHAT_ID", raising=False)

    resultado = servico.avisar_favoritos()
    assert not resultado.configurado
    assert resultado.enviados == 0


# --- a fila: o que ela nao pode fazer (revisao das etapas 8 a 10) -----------

def test_evento_velho_nao_vira_mensagem(banco_temporario, telegram):
    """Marcar a estrela hoje num concurso cujo edital saiu ha tres semanas nao
    pode despejar a historia dele no celular. Ela fica na linha do tempo, que
    e onde eu leio historia."""
    (id_,) = _semear(_concurso("https://a.test/1"))
    servico.favoritar(id_)
    _evento("https://a.test/1", "edital_publicado", "Saiu o edital",
            data=dias(-40))

    assert servico.avisar_favoritos().enviados == 0
    assert telegram == []


def test_evento_dentro_da_janela_avisa(banco_temporario, telegram):
    (id_,) = _semear(_concurso("https://a.test/1"))
    servico.favoritar(id_)
    _evento("https://a.test/1", "edital_publicado", "Saiu o edital",
            data=dias(-3))

    assert servico.avisar_favoritos().enviados == 1


def test_falha_no_meio_marca_so_o_que_saiu(banco_temporario, telegram,
                                           monkeypatch):
    """O erro que isto impede: marcando as N primeiras, a mensagem que falhou
    ficava marcada como enviada - some para sempre - e a que saiu voltava
    amanha."""
    (id_,) = _semear(_concurso("https://a.test/1"))
    servico.favoritar(id_)
    for n, tipo in enumerate(("edital_publicado", "edital_retificado",
                              "prova_marcada")):
        _evento("https://a.test/1", tipo, f"Mudanca {n}", data=dias(-n))

    saiu = []

    def falha_na_segunda(texto: str) -> bool:
        saiu.append(texto)
        return len(saiu) != 2

    monkeypatch.setattr(avisos, "enviar", falha_na_segunda)
    assert servico.avisar_favoritos().enviados == 2

    with sessao() as s:
        pendentes = [
            e.tipo for e in s.scalars(
                select(Evento).where(Evento.avisado_em.is_(None))
            )
        ]
    assert pendentes == ["edital_retificado"]   # a que falhou, e so ela


def test_o_que_sobrou_do_teto_e_contado_de_verdade(banco_temporario, telegram):
    """O numero existe para eu desconfiar de regra quebrada; contar so ate o
    teto mais um o deixaria sempre em 1."""
    (id_,) = _semear(_concurso("https://a.test/1"))
    servico.favoritar(id_)
    for n in range(8):
        _evento("https://a.test/1", "prova_marcada", f"Prova {n}", data=dias(-n))

    resultado = servico.avisar_favoritos(limite=3)

    assert resultado.enviados == 3
    assert resultado.pendentes == 5
