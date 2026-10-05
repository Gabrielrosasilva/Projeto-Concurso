"""A linha do tempo de cada concurso.

O resto do banco guarda so o AGORA: quando a situacao muda, o valor antigo e
sobrescrito. Estes testes garantem que a mudanca vira linha antes de o valor
antigo sumir.

Nenhum teste vai a internet: os itens coletados sao montados a mao.
"""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from radar import eventos, servico
from radar.collectors.base import ItemColetado
from radar.db import sessao
from radar.models import Concurso, Evento, agora
from radar.util import formatar_data

URL = "https://exemplo.test/policia-penal"

# Datas fixas, e a data esperada sai sempre de `formatar_data` - a mesma
# funcao que monta a frase. Escrever "31/10/2026" a mao aqui seria supor
# que UTC e o fuso da tela caem no mesmo dia, que e a suposicao que ja
# derrubou um teste desta pasta.
ABRE = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)
FECHA = datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)
PROVA = datetime(2027, 3, 14, 13, 0, tzinfo=timezone.utc)


def _item(**mudancas) -> ItemColetado:
    base = dict(
        titulo="Concurso Policia Penal SC abre 600 vagas",
        url=URL,
        uf="SC",
        situacao="edital_publicado",
        tipo="concurso",
    )
    base.update(mudancas)
    return ItemColetado(**base)


def _coletar(*itens, fonte: str = "fepese") -> None:
    """Passa os itens pelo upsert, como a coleta de verdade faz."""
    with sessao() as s:
        for item in itens:
            servico._gravar(s, item, fonte)


def _eventos(url: str = URL) -> list[Evento]:
    with sessao() as s:
        return eventos.do_concurso(s, url)


def _tipos(url: str = URL) -> list[str]:
    return [e.tipo for e in _eventos(url)]


# --- o concurso aparece -----------------------------------------------------

def test_o_concurso_que_aparece_vira_evento(banco_temporario):
    _coletar(_item())

    linha = _eventos()
    assert len(linha) == 1
    assert linha[0].tipo == eventos.APARECEU
    assert "fepese" in linha[0].descricao
    assert linha[0].link == URL


def test_aparecer_e_uma_vez_so(banco_temporario):
    """A coleta de amanha passa pelo mesmo item e nao pode registrar de novo."""
    _coletar(_item())
    _coletar(_item())

    assert _tipos() == [eventos.APARECEU]


# --- muda de situacao -------------------------------------------------------

def test_mudanca_de_situacao_vira_evento(banco_temporario):
    _coletar(_item(situacao="edital_publicado"))
    _coletar(_item(situacao="banca_definida"))

    linha = _eventos()
    assert _tipos() == [eventos.APARECEU, eventos.MUDOU_SITUACAO]
    assert "edital_publicado" in linha[-1].descricao
    assert "banca_definida" in linha[-1].descricao


def test_a_descricao_guarda_o_valor_antigo(banco_temporario):
    """E o motivo de a tabela existir: o campo do concurso ja foi sobrescrito,
    e sem isto ninguem lembra de onde ele veio."""
    _coletar(_item(situacao="autorizado"))
    _coletar(_item(situacao="edital_publicado"))

    with sessao() as s:
        concurso = s.scalar(select(Concurso))
    assert concurso.situacao == "edital_publicado"      # o antigo se perdeu
    assert "autorizado -> edital_publicado" in _eventos()[-1].descricao


def test_situacao_que_nao_muda_nao_vira_evento(banco_temporario):
    _coletar(_item(situacao="edital_publicado"))
    _coletar(_item(situacao="edital_publicado"))

    assert _tipos() == [eventos.APARECEU]


def test_desconhecida_da_fonte_nao_vira_evento(banco_temporario):
    """"desconhecida" e o valor de quem NAO sabe: o upsert ja o ignora, e a
    linha do tempo nao pode registrar um retrocesso que nao aconteceu."""
    _coletar(_item(situacao="edital_publicado"))
    _coletar(_item(situacao="inscricoes_abertas"))
    _coletar(_item(situacao="desconhecida"))

    assert _tipos() == [eventos.APARECEU, eventos.INSCRICOES_ABERTAS]


def test_quem_ja_nasce_aberto_so_tem_o_apareceu(banco_temporario):
    """Concurso raramente entra no radar no comeco da vida: quando o radar
    liga, muita coisa ja esta com a inscricao aberta. Isso e UM acontecimento,
    e nao dois."""
    _coletar(_item(situacao="inscricoes_abertas"))

    assert _tipos() == [eventos.APARECEU]
    assert "inscricoes_abertas" in _eventos()[0].descricao


# --- a inscricao abre e fecha -----------------------------------------------

def test_inscricao_que_abre_tem_evento_proprio(banco_temporario):
    """Abrir inscricao nao e um passo qualquer do ciclo: e o que eu preciso
    achar depois na linha do tempo."""
    _coletar(_item(situacao="edital_publicado"))
    _coletar(_item(situacao="inscricoes_abertas"))

    assert _tipos()[-1] == eventos.INSCRICOES_ABERTAS


def test_inscricao_que_fecha_tem_evento_proprio(banco_temporario):
    _coletar(_item(situacao="inscricoes_abertas"))
    _coletar(_item(situacao="encerrado"))

    assert _tipos()[-1] == eventos.INSCRICOES_ENCERRADAS


def test_o_prazo_vencendo_sozinho_vira_evento(banco_temporario):
    """O unico evento que acontece sem ninguem tocar em nada: o tempo passa e
    a inscricao fecha."""
    _coletar(_item())
    with sessao() as s:
        concurso = s.scalar(select(Concurso))
        concurso.situacao = "inscricoes_abertas"
        concurso.inscricoes_de = agora() - timedelta(days=30)
        concurso.inscricoes_ate = agora() - timedelta(days=1)

    servico.atualizar_situacoes()

    assert _tipos()[-1] == eventos.INSCRICOES_ENCERRADAS
    assert "encerrado" in _eventos()[-1].descricao


def test_atualizar_situacoes_duas_vezes_nao_duplica(banco_temporario):
    _coletar(_item())
    with sessao() as s:
        concurso = s.scalar(select(Concurso))
        concurso.inscricoes_ate = agora() - timedelta(days=1)

    servico.atualizar_situacoes()
    servico.atualizar_situacoes()

    assert _tipos().count(eventos.INSCRICOES_ENCERRADAS) == 1


# --- a prova e marcada ------------------------------------------------------

def test_data_de_prova_conhecida_vira_evento(banco_temporario):
    """Hoje nenhuma fonte preenche data_prova. O gancho fica no upsert, que e
    por onde ela vai chegar quando alguma passar a mandar."""
    _coletar(_item())
    with sessao() as s:
        s.scalar(select(Concurso)).data_prova = datetime(
            2027, 3, 14, 13, 0, tzinfo=timezone.utc
        )

    # a coleta seguinte enxerga o campo ja preenchido e nao registra de novo
    _coletar(_item())
    assert eventos.PROVA_MARCADA not in _tipos()


def test_registrar_prova_marcada_monta_a_frase(banco_temporario):
    with sessao() as s:
        eventos.registrar_prova_marcada(
            s, URL, PROVA, URL
        )

    linha = _eventos()
    assert linha[0].tipo == eventos.PROVA_MARCADA
    assert formatar_data(PROVA) in linha[0].descricao


def test_sem_data_nao_registra_prova(banco_temporario):
    with sessao() as s:
        assert eventos.registrar_prova_marcada(s, URL, None) is None
    assert _eventos() == []


# --- o edital e retificado --------------------------------------------------

def test_retificacao_vira_evento(banco_temporario):
    with sessao() as s:
        eventos.registrar_retificacao(
            s, URL, "2019_SAP_Edital_1.pdf", "https://sap.test/edital.pdf"
        )

    linha = _eventos()
    assert linha[0].tipo == eventos.EDITAL_RETIFICADO
    assert "2019_SAP_Edital_1.pdf" in linha[0].descricao
    assert linha[0].link == "https://sap.test/edital.pdf"


def test_retificar_duas_vezes_da_dois_eventos(banco_temporario):
    """Ao contrario de "apareceu", retificar de novo E um fato novo."""
    with sessao() as s:
        eventos.registrar_retificacao(s, URL, "edital.pdf")
        eventos.registrar_retificacao(s, URL, "edital.pdf")

    assert _tipos() == [eventos.EDITAL_RETIFICADO, eventos.EDITAL_RETIFICADO]


# --- o prazo descoberto na pagina -------------------------------------------

def test_prazo_com_inicio_e_fim_na_descricao(banco_temporario):
    with sessao() as s:
        eventos.registrar_prazo(
            s, URL,
            ABRE, FECHA,
        )

    assert formatar_data(ABRE) in _eventos()[0].descricao
    assert formatar_data(FECHA) in _eventos()[0].descricao


def test_prazo_so_com_fim(banco_temporario):
    """A FEPESE nem sempre informa quando a inscricao comecou."""
    with sessao() as s:
        eventos.registrar_prazo(
            s, URL, None, FECHA
        )

    descricao = _eventos()[0].descricao
    assert f"ate {formatar_data(FECHA)}" in descricao


def test_prazo_que_ja_venceu_nao_vira_inscricao_abrindo(banco_temporario):
    """O radar le o edital de um concurso cuja inscricao ja fechou - a
    docstring de `registrar_prazo` sempre soube disso. O que faltava era o
    tipo do evento seguir a data: desde a etapa 8 um "inscricoes abertas"
    verde vira mensagem no celular, e para concurso fechado isso e o tipo de
    aviso que faz eu parar de confiar nos avisos."""
    with sessao() as s:
        eventos.registrar_prazo(s, URL, None, agora() - timedelta(days=3))

    evento = _eventos()[0]
    assert evento.tipo == eventos.INSCRICOES_ENCERRADAS
    assert "ja encerrado" in evento.descricao


def test_prazo_que_ainda_corre_vira_inscricao_abrindo(banco_temporario):
    with sessao() as s:
        eventos.registrar_prazo(s, URL, None, agora() + timedelta(days=10))

    assert _eventos()[0].tipo == eventos.INSCRICOES_ABERTAS


def test_sem_prazo_nao_registra(banco_temporario):
    with sessao() as s:
        assert eventos.registrar_prazo(s, URL, None, None) is None
    assert _eventos() == []


# --- a ordem da linha do tempo ----------------------------------------------

def test_a_linha_do_tempo_vem_do_mais_antigo_para_o_mais_novo(banco_temporario):
    ontem = agora() - timedelta(days=1)
    with sessao() as s:
        eventos.registrar(s, URL, eventos.MUDOU_SITUACAO, "o de hoje")
        eventos.registrar(s, URL, eventos.APARECEU, "o de ontem", data=ontem)

    assert [e.descricao for e in _eventos()] == ["o de ontem", "o de hoje"]


def test_eventos_do_mesmo_instante_saem_na_ordem_em_que_entraram(banco_temporario):
    """Uma coleta que descobre prazo e situacao de uma vez grava os dois com o
    mesmo carimbo de tempo. O id desempata."""
    momento = agora()
    with sessao() as s:
        eventos.registrar(s, URL, eventos.APARECEU, "primeiro", data=momento)
        eventos.registrar(s, URL, eventos.MUDOU_SITUACAO, "segundo", data=momento)

    assert [e.descricao for e in _eventos()] == ["primeiro", "segundo"]


def test_evento_de_um_concurso_nao_aparece_no_outro(banco_temporario):
    _coletar(_item())
    _coletar(_item(url="https://exemplo.test/outro", titulo="Outro concurso"))

    assert len(_eventos(URL)) == 1
    assert len(_eventos("https://exemplo.test/outro")) == 1


# --- a consulta que a CLI usa -----------------------------------------------

def test_eventos_do_concurso_devolve_o_concurso_junto(banco_temporario):
    """Uma lista de datas sem dizer de que concurso e nao serve para nada."""
    _coletar(_item())
    with sessao() as s:
        concurso_id = s.scalar(select(Concurso)).id

    concurso, linha = servico.eventos_do_concurso(concurso_id)
    assert concurso.url == URL
    assert len(linha) == 1


def test_id_que_nao_existe_devolve_nada(banco_temporario):
    assert servico.eventos_do_concurso(9999) is None


def test_a_descricao_nao_estoura_a_coluna(banco_temporario):
    """A coluna tem 300 caracteres; texto de terceiro pode ser maior."""
    with sessao() as s:
        eventos.registrar(s, URL, eventos.APARECEU, "x" * 500)

    assert len(_eventos()[0].descricao) == 300


# --- a coleta nao pode desmentir o prazo (conserto da etapa 8) --------------

def test_coleta_repetida_nao_faz_a_situacao_piscar(banco_temporario):
    """O bug que isto impede: o coletor do Concursos no Brasil marca
    "edital_publicado" em TODO item, porque o feed dele nao distingue fase.
    Gravando isso por cima de um concurso encerrado, o `atualizar_situacoes`
    do fim da mesma rodada desfazia - e sobravam dois eventos por coleta, dia
    apos dia. Desde a etapa 8 os dois sao dos tipos que avisam no Telegram.
    """
    with sessao() as s:
        s.add(Concurso(
            url=URL, fonte="concursosnobrasil",
            titulo="Concurso Policia Penal SC abre 600 vagas",
            uf="SC", tipo="concurso", situacao="encerrado",
            inscricoes_de=agora() - timedelta(days=40),
            inscricoes_ate=agora() - timedelta(days=5),
        ))

    for _ in range(3):
        _coletar(_item(), fonte="concursosnobrasil")
        servico.atualizar_situacoes()

    assert _tipos() == []
    with sessao() as s:
        assert s.scalar(select(Concurso)).situacao == "encerrado"


def test_sem_prazo_conhecido_a_fonte_continua_mandando(banco_temporario):
    """A trava vale so onde a data prova alguma coisa. Sem prazo no banco, o
    que a fonte diz e o melhor que existe."""
    _coletar(_item(situacao="prevista"))
    _coletar(_item(situacao="inscricoes_abertas"))

    with sessao() as s:
        assert s.scalar(select(Concurso)).situacao == "inscricoes_abertas"
    assert eventos.INSCRICOES_ABERTAS in _tipos()


# --- como o evento aparece na tela (etapa 1B, pendencia A2) -----------------
#
# O banco guarda "Situacao: a -> b" e continua guardando: a traducao e so na
# exibicao. Estes testes conferem a frase, e que o dado gravado nao mudou.

@pytest.mark.parametrize("antes, depois, frase", [
    ("prevista", "autorizado", "O concurso foi autorizado"),
    ("autorizado", "banca_definida", "A banca foi definida"),
    ("banca_definida", "edital_publicado", "O edital foi publicado"),
    ("edital_publicado", "inscricoes_abertas", "As inscrições abriram"),
    ("inscricoes_abertas", "encerrado", "As inscrições encerraram"),
    ("desconhecida", "prevista", "O concurso passou a constar como previsto"),
    ("prevista", "desconhecida", "A fonte deixou de informar a situação"),
])
def test_cada_transicao_vira_uma_frase(antes, depois, frase):
    assert eventos.para_tela(f"Situacao: {antes} -> {depois}") == frase


def test_situacao_que_volta_no_ciclo_nao_diz_que_avancou():
    """O banco real tem "inscricoes_abertas -> edital_publicado": dizer "O
    edital foi publicado" seria inventar um segundo edital."""
    assert eventos.para_tela("Situacao: inscricoes_abertas -> edital_publicado") == (
        "A situação voltou de inscrições abertas para edital publicado"
    )


def test_a_frase_sai_da_descricao_que_a_coleta_grava(banco_temporario):
    """Ponta a ponta: o que o servico grava e o que a tela traduz casam - e o
    banco continua com o texto cru."""
    _coletar(_item(situacao="inscricoes_abertas"))
    _coletar(_item(situacao="encerrado"))

    gravada = _eventos()[-1].descricao
    assert gravada == "Situacao: inscricoes_abertas -> encerrado"
    assert eventos.para_tela(gravada) == "As inscrições encerraram"


def test_o_apareceu_diz_a_situacao_com_nome_de_gente(banco_temporario):
    _coletar(_item(situacao="edital_publicado"))

    (apareceu,) = _eventos()
    assert eventos.para_tela(apareceu.descricao) == (
        "Entrou no radar pela fonte fepese (situação: edital publicado)"
    )


def test_prazo_e_retificacao_saem_com_acento(banco_temporario):
    # O primeiro prazo tem de estar no FUTURO: passado, a frase vira "já
    # encerrado". Com o FECHA fixo (31/10/2026) o teste quebrava em 01/11 e
    # parava o Actions - por isso a data sai de agora().
    ainda_aberto = agora() + timedelta(days=30)
    with sessao() as s:
        eventos.registrar_prazo(s, URL, None, ainda_aberto)
        eventos.registrar_prazo(s, URL, ABRE, agora() - timedelta(days=1))
        eventos.registrar_retificacao(s, URL, "edital.pdf")

    textos = [eventos.para_tela(e.descricao) for e in _eventos()]
    assert textos[0] == f"Prazo de inscrição: até {formatar_data(ainda_aberto)}"
    assert textos[1].startswith("Prazo de inscrição, já encerrado: de ")
    assert textos[2] == ("Edital retificado: edital.pdf. Retificação muda "
                         "prazo, vaga e requisito - vale reler.")


@pytest.mark.parametrize("texto", [
    "Governo estuda novo concurso da Policia Penal SC",   # titulo de noticia
    "Prova marcada para 14/03/2027",
    "Alguma descricao antiga, de formato desconhecido",
])
def test_texto_que_nao_e_da_coleta_passa_como_veio(texto):
    assert eventos.para_tela(texto) == texto


def test_nenhuma_frase_de_situacao_deixa_valor_cru():
    from radar.models import SITUACOES

    for antes in SITUACOES:
        for depois in SITUACOES:
            if antes == depois:
                continue
            frase = eventos.para_tela(f"Situacao: {antes} -> {depois}")
            assert "_" not in frase and "->" not in frase, frase


@pytest.mark.parametrize("tipo, rotulo", [
    (eventos.INSCRICOES_ENCERRADAS, "inscrições encerradas"),
    (eventos.INSCRICOES_ABERTAS, "inscrições abertas"),
    (eventos.MUDOU_SITUACAO, "mudou a situação"),
    ("noticia", "notícia"),
])
def test_o_tipo_do_evento_tem_acento(tipo, rotulo):
    assert eventos.rotulo_do_tipo(tipo) == rotulo
