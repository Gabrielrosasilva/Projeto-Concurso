"""Avisos no Telegram.

Nenhum teste aqui vai a internet: o envio e substituido por uma funcao falsa
que so guarda o que teria sido mandado.
"""
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from radar import avisos, servico
from radar.db import sessao
from radar.models import Concurso


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


def _concurso(**mudancas) -> Concurso:
    base = dict(
        url="https://exemplo.test/palhoca",
        fonte="concursosnobrasil",
        titulo="Prefeitura de Palhoca (SC) abre concurso para Guarda Municipal",
        uf="SC",
        municipio="Palhoca",
        situacao="edital_publicado",
        tipo="concurso",
        relevancia="nucleo",
        motivo_relevancia="Palhoca (SC) esta no anel nucleo.",
        salario=5200.0,
        publicado_em=datetime(2026, 9, 17, 12, 0, tzinfo=timezone.utc),
    )
    base.update(mudancas)
    return Concurso(**base)


def _semear(*concursos):
    with sessao() as s:
        for c in concursos:
            s.add(c)


# --- a mensagem -------------------------------------------------------------

def test_mensagem_traz_o_link_da_fonte(banco_temporario):
    """O motivo de existir do aviso: nao ter que abrir o computador."""
    texto = avisos.formatar(_concurso())
    assert "https://exemplo.test/palhoca" in texto


def test_mensagem_traz_titulo_salario_local_e_motivo(banco_temporario):
    texto = avisos.formatar(_concurso())
    assert "Guarda Municipal" in texto
    assert "R$ 5.200" in texto
    assert "Palhoca/SC" in texto
    assert "esta no anel nucleo" in texto


def test_emoji_muda_conforme_o_anel(banco_temporario):
    verde = avisos.formatar(_concurso(relevancia="nucleo"))
    amarelo = avisos.formatar(_concurso(relevancia="proximo"))
    azul = avisos.formatar(_concurso(relevancia="indefinida"))
    assert verde[0] != amarelo[0] != azul[0]


def test_titulo_com_caractere_especial_nao_quebra_o_html(banco_temporario):
    """Titulo vem de site de terceiro: < e & precisam virar entidade."""
    texto = avisos.formatar(_concurso(titulo="Concurso <b>P&D</b> & Seguranca"))
    assert "&lt;b&gt;" in texto
    assert "P&amp;D" in texto


def test_concurso_sem_salario_nao_mostra_valor_vazio(banco_temporario):
    texto = avisos.formatar(_concurso(salario=None))
    assert "R$" not in texto


# --- quem e avisado ---------------------------------------------------------

def test_avisa_o_que_esta_perto(banco_temporario, telegram):
    _semear(_concurso())
    resultado = servico.avisar()

    assert resultado.enviados == 1
    assert "Guarda Municipal" in telegram[0]


def test_avisa_indefinida(banco_temporario, telegram):
    """Federal sem UF pode aplicar prova em Floripa: melhor avisar a toa."""
    _semear(_concurso(relevancia="indefinida", uf=None, municipio=None))
    assert servico.avisar().enviados == 1


def test_avisa_orgao_estadual_de_sc(banco_temporario, telegram):
    """Policia Penal SC e o alvo principal: nao pode ficar sem notificacao so
    porque o edital ainda nao disse onde sao os polos de prova."""
    _semear(_concurso(
        relevancia="estadual",
        municipio=None,
        titulo="2019 - Secretaria de Estado da Administracao Prisional",
        motivo_relevancia=(
            "Orgao estadual de SC; polos de prova a confirmar no edital."
        ),
    ))
    assert servico.avisar().enviados == 1
    assert "Prisional" in telegram[0]


def test_nao_avisa_o_que_e_longe(banco_temporario, telegram):
    _semear(_concurso(relevancia="remoto", municipio="Capinzal"))
    assert servico.avisar().enviados == 0
    assert telegram == []


def test_nao_avisa_noticia(banco_temporario, telegram):
    """O "Bolsa Familia" do feed nao pode virar notificacao no celular."""
    _semear(_concurso(tipo="noticia", titulo="Bolsa Familia tem novo valor"))
    assert servico.avisar().enviados == 0


def test_nao_avisa_duas_vezes_o_mesmo_concurso(banco_temporario, telegram):
    """A coleta de amanha nao pode repetir o aviso de hoje."""
    _semear(_concurso())

    assert servico.avisar().enviados == 1
    assert servico.avisar().enviados == 0
    assert len(telegram) == 1


def test_marca_a_data_do_aviso(banco_temporario, telegram):
    _semear(_concurso())
    servico.avisar()

    with sessao() as s:
        concurso = s.scalar(select(Concurso))
    assert concurso.avisado_em is not None


# --- o limite de seguranca --------------------------------------------------

def test_limite_por_coleta(banco_temporario, telegram):
    """Regra quebrada nao pode virar 200 notificacoes as 6h da manha."""
    _semear(*[
        _concurso(url=f"https://exemplo.test/{i}", titulo=f"Concurso {i}")
        for i in range(25)
    ])

    resultado = servico.avisar(limite=10)

    assert resultado.enviados == 10
    assert resultado.pendentes == 15
    # 10 avisos + 1 mensagem dizendo quantos ficaram de fora
    assert len(telegram) == 11
    assert "Mais 15" in telegram[-1]


def test_sem_excesso_nao_manda_mensagem_de_alerta(banco_temporario, telegram):
    _semear(_concurso())
    servico.avisar(limite=10)
    assert len(telegram) == 1


def test_o_que_passou_do_limite_fica_para_a_proxima(banco_temporario, telegram):
    _semear(*[
        _concurso(url=f"https://exemplo.test/{i}", titulo=f"Concurso {i}")
        for i in range(12)
    ])

    servico.avisar(limite=10)
    telegram.clear()

    # os 2 que sobraram continuam pendentes
    assert servico.avisar(limite=10).enviados == 2


# --- o alvo principal fura a fila -------------------------------------------
# Policia Penal SC e o concurso que eu espero. Para ele o cargo manda: nem a
# distancia, nem o teto de mensagens, nem o filtro de noticia podem segurar o
# aviso.

def _alvo_principal(**mudancas) -> Concurso:
    base = dict(
        url="https://exemplo.test/policia-penal",
        titulo="Concurso Policia Penal SC e autorizado com 600 vagas",
        municipio=None,
        relevancia="estadual",
        motivo_relevancia="Orgao estadual de SC; polos a confirmar no edital.",
        alvo="principal",
        motivo_alvo=(
            'Alvo principal (Policia Penal SC): o texto fala em "policia penal".'
        ),
    )
    base.update(mudancas)
    return _concurso(**base)


def test_alvo_principal_leva_sirene_na_frente(banco_temporario):
    texto = avisos.formatar(_alvo_principal())
    assert texto.startswith(avisos.SIRENE)
    assert "Alvo principal" in texto


def test_aviso_comum_nao_leva_sirene(banco_temporario):
    assert not avisos.formatar(_concurso()).startswith(avisos.SIRENE)


def test_alvo_principal_avisa_mesmo_longe(banco_temporario, telegram):
    """Concurso estadual: eu presto onde a prova for. A distancia nao segura."""
    _semear(_alvo_principal(relevancia="remoto", municipio="Chapeco"))
    assert servico.avisar().enviados == 1


def test_alvo_principal_avisa_mesmo_sendo_noticia(banco_temporario, telegram):
    """"Governo autoriza concurso da Policia Penal" nao e edital, e e
    exatamente o aviso que eu quero receber primeiro."""
    _semear(_alvo_principal(tipo="noticia", situacao="desconhecida"))
    assert servico.avisar().enviados == 1


def test_alvo_principal_passa_por_fora_do_teto(banco_temporario, telegram):
    """O teto existe para segurar regra quebrada, nao para segurar o meu
    concurso: se sairem 12 avisos da Policia Penal no mesmo dia, eu quero os
    12, e os outros continuam limitados a 10."""
    _semear(*[
        _alvo_principal(url=f"https://exemplo.test/pp-{i}", titulo=f"Policia Penal SC {i}")
        for i in range(12)
    ])
    _semear(*[
        _concurso(url=f"https://exemplo.test/outro-{i}", titulo=f"Concurso {i}")
        for i in range(25)
    ])

    resultado = servico.avisar(limite=10)

    assert resultado.enviados == 22      # 12 do alvo + 10 do teto
    assert resultado.pendentes == 15     # so o resto entra na conta do teto


def test_noticia_sem_alvo_continua_fora(banco_temporario, telegram):
    """A regra nova nao pode abrir a porta para o "Bolsa Familia" do feed."""
    _semear(_concurso(tipo="noticia", titulo="Bolsa Familia tem novo valor"))
    assert servico.avisar().enviados == 0


def test_alvo_secundario_segue_as_regras_normais(banco_temporario, telegram):
    """Secundario ganha a marca, e so. Longe continua sendo longe."""
    _semear(_concurso(
        url="https://exemplo.test/guarda-guarulhos",
        titulo="Concurso Prefeitura de Guarulhos (SP) abre 200 vagas para Guarda Municipal",
        uf="SP",
        municipio="Guarulhos",
        relevancia="remoto",
        alvo="secundario",
        motivo_alvo='Alvo secundario (Guarda Municipal): o texto fala em "guarda municipal".',
    ))
    assert servico.avisar().enviados == 0


def test_alvo_principal_encerrado_nao_vira_mensagem(banco_temporario, telegram):
    """Furar o teto nao e furar a janela de novidade: ligar uma fonte nova
    traz o historico dela, e o concurso de 2013 nao pode tocar o celular."""
    from datetime import timedelta

    from radar.models import agora

    _semear(_alvo_principal(
        url="https://exemplo.test/pp-2013",
        titulo="2013 - Secretaria de Estado da Justica e Cidadania",
        situacao="encerrado",
        publicado_em=agora() - timedelta(days=4000),
    ))
    assert servico.avisar().enviados == 0


# --- quando da errado -------------------------------------------------------

def test_sem_configuracao_nao_quebra(banco_temporario, monkeypatch):
    """Coleta sem aviso e melhor que coleta quebrada."""
    monkeypatch.delenv("RADAR_TELEGRAM_TOKEN", raising=False)
    monkeypatch.delenv("RADAR_TELEGRAM_CHAT_ID", raising=False)
    _semear(_concurso())

    resultado = servico.avisar()

    assert resultado.configurado is False
    assert resultado.enviados == 0


def test_telegram_fora_do_ar_mantem_o_concurso_pendente(banco_temporario, monkeypatch):
    """Se a mensagem nao saiu, a proxima coleta precisa tentar de novo."""
    monkeypatch.setenv("RADAR_TELEGRAM_TOKEN", "token-de-teste")
    monkeypatch.setenv("RADAR_TELEGRAM_CHAT_ID", "123456")
    monkeypatch.setattr(avisos, "enviar", lambda texto: False)
    monkeypatch.setattr(avisos, "PAUSA_ENTRE_MENSAGENS", 0)

    _semear(_concurso())
    assert servico.avisar().enviados == 0

    with sessao() as s:
        assert s.scalar(select(Concurso)).avisado_em is None


def test_erro_de_rede_nao_sobe(banco_temporario, monkeypatch):
    """requests.post estourando nao pode derrubar a coleta diaria."""
    monkeypatch.setenv("RADAR_TELEGRAM_TOKEN", "token-de-teste")
    monkeypatch.setenv("RADAR_TELEGRAM_CHAT_ID", "123456")

    def explode(*args, **kwargs):
        raise ConnectionError("sem rede")

    monkeypatch.setattr(avisos.requests, "post", explode)

    assert avisos.enviar("teste") is False


def test_o_token_nunca_aparece_no_log(banco_temporario, monkeypatch, caplog):
    """A URL da API carrega o token. Ela nao pode vazar para o log."""
    monkeypatch.setenv("RADAR_TELEGRAM_TOKEN", "token-secreto-123")
    monkeypatch.setenv("RADAR_TELEGRAM_CHAT_ID", "123456")

    def explode(*args, **kwargs):
        raise ConnectionError("falhou em https://api.telegram.org/bottoken-secreto-123/x")

    monkeypatch.setattr(avisos.requests, "post", explode)

    with caplog.at_level("DEBUG"):
        avisos.enviar("teste")

    assert "token-secreto-123" not in caplog.text


# --- so novidade vira mensagem ----------------------------------------------
# Ligar uma fonte nova traz o historico dela junto. A FEPESE entrou com 520
# concursos, 464 ja encerrados - sem esta regra, o aviso seguinte falaria de
# edital de anos atras.

def test_concurso_antigo_nao_vira_mensagem(banco_temporario, telegram):
    from datetime import timedelta

    from radar.models import agora

    _semear(_concurso(
        url="https://exemplo.test/velho",
        publicado_em=agora() - timedelta(days=400),
        situacao="edital_publicado",
    ))

    assert servico.avisar().enviados == 0


def test_concurso_encerrado_nunca_vira_mensagem(banco_temporario, telegram):
    from radar.models import agora

    _semear(_concurso(
        url="https://exemplo.test/fechado",
        publicado_em=agora(),          # publicado hoje, mas ja encerrado
        situacao="encerrado",
    ))

    assert servico.avisar().enviados == 0


def test_antigo_com_inscricao_aberta_vira_mensagem(banco_temporario, telegram):
    """Edital de 40 dias atras com prazo em pe ainda e util para mim."""
    from datetime import timedelta

    from radar.models import agora

    _semear(_concurso(
        url="https://exemplo.test/aberto",
        publicado_em=agora() - timedelta(days=40),
        inscricoes_ate=agora() + timedelta(days=10),
        situacao="inscricoes_abertas",
    ))

    assert servico.avisar().enviados == 1


def test_recem_publicado_vira_mensagem(banco_temporario, telegram):
    from radar.models import agora

    _semear(_concurso(url="https://exemplo.test/novo", publicado_em=agora()))
    assert servico.avisar().enviados == 1


def test_sem_data_de_publicacao_ainda_avisa(banco_temporario, telegram):
    """Sem data nao da para afirmar que e velho; o teto de 10 segura o resto."""
    _semear(_concurso(url="https://exemplo.test/sem-data", publicado_em=None))
    assert servico.avisar().enviados == 1


def test_inscricao_aberta_vale_mesmo_sem_prazo_e_sem_ser_recente(banco_temporario, telegram):
    """O caso da Celesc: a FEPESE marcou "Inscricoes abertas" mas nao informa
    data-limite, e o post e de mais de 30 dias atras. Se a banca diz que da
    para se inscrever, isso basta."""
    from datetime import timedelta

    from radar.models import agora

    _semear(_concurso(
        url="https://exemplo.test/celesc",
        titulo="2026 - Celesc Distribuicao S.A",
        municipio=None,
        uf=None,
        relevancia="indefinida",
        situacao="inscricoes_abertas",
        inscricoes_ate=None,
        publicado_em=agora() - timedelta(days=60),
    ))

    assert servico.avisar().enviados == 1


# --- um comando so manda mensagem (etapa 11) --------------------------------

def _runner():
    from typer.testing import CliRunner

    return CliRunner()


def test_o_comando_avisar_manda_favorito_e_concurso_novo(banco_temporario,
                                                         telegram):
    """Um lugar so manda mensagem, e e este: o robo do GitHub chama `radar
    avisar` e com isso cobre as duas coisas."""
    from radar import eventos, servico
    from radar.cli import app

    _semear(_concurso())
    with sessao() as s:
        concurso = s.scalar(select(Concurso))
        concurso.interesse = servico.FAVORITO
        eventos.registrar(
            s, concurso.url, eventos.EDITAL_PUBLICADO, "Saiu o edital",
            concurso.url,
        )

    resultado = _runner().invoke(app, ["avisar"])

    assert resultado.exit_code == 0
    assert "Favoritos" in resultado.output
    assert "Concursos novos" in resultado.output
    # a mudanca do favorito vai na frente do concurso novo
    assert "Edital publicado" in telegram[0]
    assert len(telegram) == 2


def test_da_para_pedir_so_os_concursos_novos(banco_temporario, telegram):
    from radar import eventos, servico
    from radar.cli import app

    _semear(_concurso())
    with sessao() as s:
        concurso = s.scalar(select(Concurso))
        concurso.interesse = servico.FAVORITO
        eventos.registrar(
            s, concurso.url, eventos.EDITAL_PUBLICADO, "Saiu o edital",
            concurso.url,
        )

    resultado = _runner().invoke(app, ["avisar", "--sem-favoritos"])

    assert "Favoritos" not in resultado.output
    assert len(telegram) == 1


def test_sem_telegram_configurado_o_comando_explica(banco_temporario,
                                                    monkeypatch):
    from radar.cli import app

    monkeypatch.delenv("RADAR_TELEGRAM_TOKEN", raising=False)
    monkeypatch.delenv("RADAR_TELEGRAM_CHAT_ID", raising=False)

    resultado = _runner().invoke(app, ["avisar"])

    assert resultado.exit_code == 0
    assert "Telegram nao configurado" in resultado.output
