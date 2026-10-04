"""O caderno de erros: anotar, rever em 1-7-30, filtrar e guardar no JSON.

O caderno e DIARIO, como o "Como foi o dia": o que esta escrito nele nao mede
o que a banca cobra - mede o que eu aprendi. Por isso um dos testes daqui
confere justamente que ele NAO aparece em acerto medido nenhum.

Nenhum teste vai a internet nem toca o banco de verdade: todos rodam no
`banco_temporario`, que aponta o radar para um SQLite descartavel.
"""
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from radar import acervo, servico
from radar.db import sessao
from radar.models import ErroAnotado
from radar.web.app import app

HOJE = date(2026, 10, 20)      # uma terca-feira da semana 4 do Ciclo 1


@pytest.fixture
def cliente(banco_temporario):
    return TestClient(app)


def _anotar(**mudancas):
    """Um erro com tudo preenchido, para o teste mudar so o que interessa."""
    dados = {
        "data_estudo": HOJE,
        "materia": "LEP",
        "assunto": "Progressão de regime",
        "motivo": "pegadinha",
        "regra": "O prazo conta da data da prisão, não da condenação.",
        "fonte": "qconcursos",
        "referencia": "Q123456",
        "hoje": HOJE,
    }
    dados.update(mudancas)
    return servico.erros.anotar(**dados)


# --- anotar -------------------------------------------------------------------

def test_anotar_grava_e_marca_para_amanha(banco_temporario):
    erro = _anotar()

    assert erro.id is not None
    assert erro.etapa == 1
    assert erro.proxima_revisao == HOJE + timedelta(days=1)
    assert erro.arquivado is False
    assert erro.historico == []


def test_sem_a_regra_o_erro_nao_entra(banco_temporario):
    """A regra e o coracao disto: erro sem ela e so um erro anotado."""
    with pytest.raises(servico.erros.ErroInvalido, match="regra certa"):
        _anotar(regra="   ")

    with sessao() as s:
        assert s.scalars(select(ErroAnotado)).all() == []


def test_sem_materia_o_erro_nao_entra(banco_temporario):
    with pytest.raises(servico.erros.ErroInvalido, match="matéria"):
        _anotar(materia="")


@pytest.mark.parametrize("campo, valor", [
    ("motivo", "esqueci"),
    ("fonte", "papel"),
])
def test_motivo_e_fonte_fora_da_lista_sao_recusados(banco_temporario, campo, valor):
    with pytest.raises(servico.erros.ErroInvalido):
        _anotar(**{campo: valor})


def test_o_assunto_e_a_referencia_sao_opcionais(banco_temporario):
    erro = _anotar(assunto="", referencia="")
    assert erro.assunto is None and erro.referencia is None


def test_sem_data_o_erro_e_de_hoje(banco_temporario):
    erro = _anotar(data_estudo=None)
    assert erro.data_estudo == HOJE


# --- o ciclo 1-7-30 -----------------------------------------------------------

def test_ja_sei_tres_vezes_arquiva(banco_temporario):
    """1 -> 7 -> 30 -> arquivo. Os intervalos sao os do `servico.espacada`."""
    erro = _anotar()
    assert servico.erros.INTERVALOS == (1, 7, 30)

    erro = servico.erros.revisar(erro.id, "ja_sei", hoje=HOJE + timedelta(days=1))
    assert erro.etapa == 2
    assert erro.proxima_revisao == HOJE + timedelta(days=1 + 7)
    assert erro.arquivado is False

    erro = servico.erros.revisar(erro.id, "ja_sei", hoje=HOJE + timedelta(days=8))
    assert erro.etapa == 3
    assert erro.proxima_revisao == HOJE + timedelta(days=8 + 30)

    erro = servico.erros.revisar(erro.id, "ja_sei", hoje=HOJE + timedelta(days=38))
    assert erro.arquivado is True
    assert erro.proxima_revisao is None


def test_ainda_erro_volta_para_a_etapa_1(banco_temporario):
    erro = _anotar()
    erro = servico.erros.revisar(erro.id, "ja_sei", hoje=HOJE + timedelta(days=1))
    erro = servico.erros.revisar(erro.id, "ja_sei", hoje=HOJE + timedelta(days=8))
    assert erro.etapa == 3

    erro = servico.erros.revisar(erro.id, "ainda_erro", hoje=HOJE + timedelta(days=38))
    assert erro.etapa == 1
    assert erro.proxima_revisao == HOJE + timedelta(days=39)
    assert erro.arquivado is False


def test_ainda_erro_desarquiva(banco_temporario):
    """Se eu apertei "ainda erro" num arquivado, ele nao estava aprendido."""
    erro = _anotar()
    for i, dia in enumerate((1, 8, 38)):
        erro = servico.erros.revisar(erro.id, "ja_sei", hoje=HOJE + timedelta(days=dia))
    assert erro.arquivado is True

    erro = servico.erros.revisar(erro.id, "ainda_erro", hoje=HOJE + timedelta(days=40))
    assert erro.arquivado is False
    assert erro.etapa == 1


def test_o_historico_guarda_cada_revisao(banco_temporario):
    erro = _anotar()
    erro = servico.erros.revisar(erro.id, "ja_sei", hoje=HOJE + timedelta(days=1))
    erro = servico.erros.revisar(erro.id, "ainda_erro", hoje=HOJE + timedelta(days=9))

    assert erro.historico == [
        {"data": "2026-10-21", "resultado": "ja_sei", "etapa": 1},
        {"data": "2026-10-29", "resultado": "ainda_erro", "etapa": 2},
    ]


def test_resultado_desconhecido_e_recusado(banco_temporario):
    erro = _anotar()
    with pytest.raises(servico.erros.ErroInvalido):
        servico.erros.revisar(erro.id, "mais_ou_menos")


def test_revisar_erro_que_nao_existe_e_recusado(banco_temporario):
    with pytest.raises(servico.erros.ErroInvalido, match="#404"):
        servico.erros.revisar(404, "ja_sei")


# --- o que esta para rever ----------------------------------------------------

def test_erro_de_hoje_nao_esta_para_rever_hoje(banco_temporario):
    """Anotei agora: ele volta AMANHA, e nao aparece na fila de hoje."""
    _anotar()
    assert servico.erros.quantos_para_rever(HOJE) == 0
    assert servico.erros.quantos_para_rever(HOJE + timedelta(days=1)) == 1


def test_atrasado_tambem_esta_para_rever(banco_temporario):
    _anotar()
    assert servico.erros.quantos_para_rever(HOJE + timedelta(days=30)) == 1


def test_arquivado_nunca_volta_para_a_fila(banco_temporario):
    erro = _anotar()
    for dia in (1, 8, 38):
        servico.erros.revisar(erro.id, "ja_sei", hoje=HOJE + timedelta(days=dia))
    assert servico.erros.quantos_para_rever(HOJE + timedelta(days=365)) == 0


# --- os filtros ---------------------------------------------------------------

def _tres_erros():
    _anotar(materia="LEP", motivo="pegadinha")
    _anotar(materia="LEP", motivo="nao_sabia")
    _anotar(materia="Direito Penal", motivo="pegadinha",
            data_estudo=HOJE + timedelta(days=14))


def test_filtro_por_materia_e_por_motivo(banco_temporario):
    _tres_erros()
    todos = servico.erros.listar(situacao="todos", hoje=HOJE)
    assert len(todos) == 3
    assert len(servico.erros.listar(materia="LEP", situacao="todos", hoje=HOJE)) == 2
    assert len(servico.erros.listar(motivo="pegadinha", situacao="todos", hoje=HOJE)) == 2
    assert len(servico.erros.listar(materia="LEP", motivo="nao_sabia",
                                    situacao="todos", hoje=HOJE)) == 1


def test_filtro_por_semana_pega_de_segunda_a_sabado(banco_temporario):
    """A semana do cronograma: domingo nao esta no plano, e nao entra."""
    segunda = date(2026, 10, 19)
    _anotar(data_estudo=segunda)
    _anotar(data_estudo=segunda + timedelta(days=5))       # sabado
    _anotar(data_estudo=segunda + timedelta(days=6))       # domingo: fora
    _anotar(data_estudo=segunda - timedelta(days=1))       # domingo anterior

    da_semana = servico.erros.listar(situacao="todos", semana=HOJE, hoje=HOJE)
    assert len(da_semana) == 2
    assert servico.erros.semana_de(HOJE) == (segunda, segunda + timedelta(days=5))


def test_a_lista_de_arquivados_mostra_so_arquivado(banco_temporario):
    erro = _anotar()
    _anotar(materia="Direito Penal")
    for dia in (1, 8, 38):
        servico.erros.revisar(erro.id, "ja_sei", hoje=HOJE + timedelta(days=dia))

    arquivados = servico.erros.listar(situacao="arquivados", hoje=HOJE)
    assert [e.id for e in arquivados] == [erro.id]


def test_o_atrasado_vem_primeiro_na_lista(banco_temporario):
    antigo = _anotar(materia="LEP", hoje=HOJE - timedelta(days=10))
    novo = _anotar(materia="Direito Penal")

    lista = servico.erros.listar(situacao="todos", hoje=HOJE)
    assert [e.id for e in lista] == [antigo.id, novo.id]


def test_as_materias_do_filtro_sao_as_que_tem_erro(banco_temporario):
    _tres_erros()
    assert servico.erros.materias_do_caderno() == ["Direito Penal", "LEP"]


# --- o que mais te derruba ----------------------------------------------------

def test_contagem_por_materia_e_por_motivo(banco_temporario):
    for _ in range(4):
        _anotar(materia="LEP", motivo="pegadinha")
    for _ in range(6):
        _anotar(materia="LEP", motivo="nao_sabia")
    _anotar(materia="Direito Penal", motivo="li_errado")

    erros = servico.erros.listar(situacao="todos", hoje=HOJE)
    por_materia, por_motivo = servico.erros.o_que_mais_derruba(erros)

    assert (por_materia[0].nome, por_materia[0].quantos) == ("LEP", 10)
    # O motivo que mais aparece DENTRO da materia, com a porcentagem.
    assert por_materia[0].motivo == "Não sabia"
    assert por_materia[0].porcentagem == 60
    assert (por_motivo[0].nome, por_motivo[0].quantos) == ("Não sabia", 6)


def test_a_porcentagem_so_sai_com_base_minima(banco_temporario):
    """De dois erros, um e 50% - e 50% de dois nao e padrao nenhum."""
    _anotar(materia="LEP", motivo="pegadinha")
    _anotar(materia="LEP", motivo="chutei")

    por_materia, _ = servico.erros.o_que_mais_derruba(
        servico.erros.listar(situacao="todos", hoje=HOJE))
    assert por_materia[0].quantos == 2
    assert por_materia[0].porcentagem is None


def test_sem_erro_nenhum_nao_ha_contagem(banco_temporario):
    assert servico.erros.o_que_mais_derruba([]) == ([], [])


# --- o backup em JSON ---------------------------------------------------------

def test_exportar_e_importar_ida_e_volta(banco_temporario, tmp_path):
    erro = _anotar()
    servico.erros.revisar(erro.id, "ja_sei", hoje=HOJE + timedelta(days=1))
    arquivo = tmp_path / "caderno_erros.json"

    assert acervo.exportar_erros(arquivo) == 1

    # O banco esquece tudo, e o arquivo traz de volta igual.
    with sessao() as s:
        s.delete(s.get(ErroAnotado, erro.id))
    assert acervo.importar_erros(arquivo) == 1

    with sessao() as s:
        voltou = s.scalars(select(ErroAnotado)).one()
    assert voltou.materia == "LEP"
    assert voltou.regra.startswith("O prazo conta da data da prisão")
    assert voltou.motivo == "pegadinha"
    assert voltou.referencia == "Q123456"
    assert voltou.etapa == 2
    assert voltou.proxima_revisao == HOJE + timedelta(days=8)
    assert voltou.historico == [{"data": "2026-10-21", "resultado": "ja_sei",
                                 "etapa": 1}]
    assert voltou.criado_em == erro.criado_em


def test_importar_duas_vezes_da_no_mesmo(banco_temporario, tmp_path):
    _anotar()
    arquivo = tmp_path / "caderno_erros.json"
    acervo.exportar_erros(arquivo)

    assert acervo.importar_erros(arquivo) == 0       # o banco ja esta em dia
    with sessao() as s:
        assert len(s.scalars(select(ErroAnotado)).all()) == 1


def test_o_arquivo_so_cresce(banco_temporario, tmp_path):
    """Erro que esta no arquivo e nao esta no banco fica no arquivo: o JSON e
    a copia de todas as maquinas, e nao o retrato desta."""
    _anotar()
    arquivo = tmp_path / "caderno_erros.json"
    acervo.exportar_erros(arquivo)

    with sessao() as s:
        s.delete(s.scalars(select(ErroAnotado)).one())
    assert acervo.exportar_erros(arquivo) == 1


def test_sem_arquivo_o_importar_nao_reclama(banco_temporario, tmp_path):
    assert acervo.importar_erros(tmp_path / "nao_existe.json") == 0


def test_o_caminho_do_backup_fica_junto_do_diario(banco_temporario):
    assert (acervo.caminho_dos_erros().parent
            == acervo.caminho_dos_registros().parent)
    assert acervo.caminho_dos_erros().name == "caderno_erros.json"


# --- o caderno nao mede nada --------------------------------------------------

def test_o_caderno_nao_entra_em_acerto_medido(banco_temporario):
    """A regra do CLAUDE.md: so o que eu respondi DENTRO do radar mede.

    O caderno e digitado a mao e vem quase todo do Qconcursos. Se ele contasse,
    o "acerto medido" deixaria de significar o que significa.
    """
    for _ in range(5):
        _anotar()

    # Nenhuma questao respondida: as contas do radar continuam vazias.
    assert servico.espacada.pendentes() == []
    with sessao() as s:
        from radar.models import RespostaDeSimulado
        assert s.scalars(select(RespostaDeSimulado)).all() == []


# --- as telas -----------------------------------------------------------------

def test_a_aba_revisao_abre_no_caderno(cliente):
    resposta = cliente.get("/revisao", follow_redirects=False)
    assert resposta.status_code == 303
    assert resposta.headers["location"] == "/erros"


def test_as_subabas_da_revisao_tem_as_duas_telas(cliente):
    texto = cliente.get("/erros").text
    assert 'href="/erros"' in texto
    assert 'href="/macetes"' in texto


def test_a_tela_vazia_ensina_o_que_fazer(cliente):
    texto = cliente.get("/erros").text
    assert "Nada para rever hoje" in texto
    assert "Anotar um erro" in texto


def test_o_formulario_vazio_abre_com_o_dia_de_hoje(cliente, monkeypatch):
    monkeypatch.setattr(servico.cronograma, "hoje_local", lambda: HOJE)
    texto = cliente.get("/erros/novo").text
    assert 'value="2026-10-20"' in texto
    # E avisa em que dia ele volta, com a conta do servico.
    assert "Volta em 21/10" in texto


def test_o_formulario_aceita_tudo_pre_preenchido(cliente):
    texto = cliente.get(
        "/erros/novo?data=2026-10-20&materia=LEP&assunto=Progress%C3%A3o"
        "&volta=%2Fhoje%3Fdata%3D2026-10-20%23faixa-noite-0"
    ).text
    assert 'value="2026-10-20"' in texto
    assert 'value="LEP"' in texto
    assert 'value="Progressão"' in texto
    assert 'value="/hoje?data=2026-10-20#faixa-noite-0"' in texto


def test_gravar_pela_tela_volta_para_onde_eu_estava(cliente):
    resposta = cliente.post("/erros/novo", data={
        "data_estudo": "2026-10-20", "materia": "LEP", "assunto": "Progressão",
        "motivo": "pegadinha", "regra": "Conta da prisão.",
        "fonte": "qconcursos", "referencia": "",
        "volta": "/hoje?data=2026-10-20#faixa-noite-0",
    }, follow_redirects=False)

    assert resposta.status_code == 303
    assert resposta.headers["location"] == "/hoje?data=2026-10-20#faixa-noite-0"
    with sessao() as s:
        assert s.scalars(select(ErroAnotado)).one().materia == "LEP"


def test_volta_para_fora_do_site_e_recusada(cliente):
    """A mesma regra do botao de tema: `volta` e caminho deste site, e so."""
    resposta = cliente.post("/erros/novo", data={
        "data_estudo": "2026-10-20", "materia": "LEP", "motivo": "chutei",
        "regra": "x", "volta": "//exemplo.com",
    }, follow_redirects=False)
    assert resposta.headers["location"] == "/"


def test_a_recusa_aparece_na_propria_tela(cliente):
    resposta = cliente.post("/erros/novo", data={
        "data_estudo": "2026-10-20", "materia": "LEP", "motivo": "chutei",
        "regra": "   ", "volta": "/erros",
    })
    assert resposta.status_code == 400
    assert "regra certa" in resposta.text
    # E o que eu havia digitado continua na tela.
    assert 'value="LEP"' in resposta.text


def test_data_invalida_no_formulario_nao_quebra(cliente):
    resposta = cliente.get("/erros/novo?data=ontem")
    assert resposta.status_code == 200
    assert "Data inválida" in resposta.text


def test_os_botoes_aparecem_so_no_erro_vencido(cliente, monkeypatch):
    monkeypatch.setattr(servico.cronograma, "hoje_local", lambda: HOJE)
    _anotar()

    hoje = cliente.get("/erros?situacao=todos").text
    assert "Já sei" not in hoje         # ele volta amanha

    monkeypatch.setattr(servico.cronograma, "hoje_local",
                        lambda: HOJE + timedelta(days=1))
    amanha = cliente.get("/erros?situacao=todos").text
    assert "Já sei" in amanha and "Ainda erro" in amanha


def test_o_botao_ja_sei_avanca_pela_tela(cliente, monkeypatch):
    monkeypatch.setattr(servico.cronograma, "hoje_local",
                        lambda: HOJE + timedelta(days=1))
    erro = _anotar()

    resposta = cliente.post(f"/erros/{erro.id}/revisar",
                            data={"resultado": "ja_sei", "volta": "/erros"},
                            follow_redirects=False)

    assert resposta.status_code == 303
    with sessao() as s:
        assert s.get(ErroAnotado, erro.id).etapa == 2


def test_apertar_o_botao_de_um_erro_apagado_nao_da_500(cliente):
    resposta = cliente.post("/erros/404/revisar",
                            data={"resultado": "ja_sei", "volta": "/erros"},
                            follow_redirects=False)
    assert resposta.status_code == 303


def test_a_tela_mostra_o_que_mais_derruba(cliente):
    for _ in range(3):
        _anotar(materia="LEP", motivo="pegadinha")

    texto = cliente.get("/erros?situacao=todos").text
    assert "O que mais te derruba" in texto
    assert "LEP" in texto
    assert "100% dos erros são <b>pegadinha</b>" in texto


def test_o_selo_do_que_mais_derruba_sai_do_dado(cliente, monkeypatch):
    """A tela nao escolhe a cor (Etapa 7A): trocada a origem da Contagem, os
    selos dos dois cartoes trocam junto."""
    from radar.servico import erros

    _anotar(materia="LEP", motivo="pegadinha")
    monkeypatch.setattr(erros.Contagem, "origem", "acervo")

    texto = cliente.get("/erros?situacao=todos").text

    assert texto.count('class="ds-selo ds-selo--acervo"') == 2
    assert "ds-selo--automatico" not in texto


def test_o_filtro_de_semana_aparece_escrito_na_tela(cliente):
    _anotar()
    texto = cliente.get("/erros?semana=2026-10-20&situacao=todos").text
    assert "Semana de 19/10 a 24/10" in texto


def test_semana_invalida_avisa_e_mostra_tudo(cliente):
    _anotar()
    texto = cliente.get("/erros?semana=ontem&situacao=todos").text
    assert "Data inválida" in texto
    assert "LEP" in texto


# --- a tela Hoje --------------------------------------------------------------

def test_as_subabas_da_tela_hoje(cliente):
    texto = cliente.get("/hoje?data=2026-10-20").text
    assert "subabas-do-hoje" in texto
    assert "Caderno de erros" in texto
    # As tres abas, desde a etapa E3: o dia, as semanas e o caderno.
    assert ">Semanas<" in texto
    assert 'href="/semanas"' in texto


def test_a_faixa_de_questoes_tem_o_botao_de_anotar_com_tudo_pronto(cliente):
    texto = cliente.get("/hoje?data=2026-10-20").text
    assert "📓</span> Anotar erro" in texto
    # A data, a materia e o assunto da faixa, e a volta para a propria faixa.
    assert "data=2026-10-20" in texto
    assert "materia=Direito+Constitucional" in texto
    assert "volta=%2Fhoje%3Fdata%3D2026-10-20%23faixa-noite-0" in texto


def test_a_teoria_da_manha_nao_tem_o_botao(cliente):
    """Anotar erro so onde eu respondo questao: na teoria nao ha o que errar."""
    texto = cliente.get("/hoje?data=2026-10-20").text
    # Desde a 6A a manha tem questoes (a fixacao, logo depois da teoria): o
    # botao aparece nelas, e continua fora da teoria.
    teoria = texto.split('id="faixa-manha-0"')[1].split('id="faixa-manha-1"')[0]
    fixacao = texto.split('id="faixa-manha-1"')[1].split('id="faixa-manha-2"')[0]
    assert "Teoria" in teoria and "Anotar erro" not in teoria
    assert "Fixação:" in fixacao and "Anotar erro" in fixacao


def test_o_sabado_abre_os_erros_da_semana(cliente):
    texto = cliente.get("/hoje?data=2026-10-24").text      # sabado da semana 4
    assert "abrir os erros da semana" in texto
    assert "/erros?semana=2026-10-24" in texto


def test_o_cartao_da_lateral_some_com_zero(cliente, monkeypatch):
    monkeypatch.setattr(servico.cronograma, "hoje_local", lambda: HOJE)
    assert "erros para rever hoje" not in cliente.get("/hoje?data=2026-10-20").text

    _anotar(hoje=HOJE - timedelta(days=5))
    _anotar(hoje=HOJE - timedelta(days=5), materia="Direito Penal")
    texto = cliente.get("/hoje?data=2026-10-20").text
    assert '<p class="erros-n">2</p>' in texto
    assert "erros para rever hoje" in texto


def test_o_cartao_da_lateral_fala_no_singular(cliente, monkeypatch):
    monkeypatch.setattr(servico.cronograma, "hoje_local", lambda: HOJE)
    _anotar(hoje=HOJE - timedelta(days=5))
    assert "erro para rever hoje" in cliente.get("/hoje?data=2026-10-20").text


def test_a_volta_do_botao_nao_perde_o_tema(cliente):
    """O link_do_dia escreve "&amp;" (certo no HTML). Essa volta e codificada
    de novo, e o "&amp;" viraria um parametro chamado "amp;cor"."""
    texto = cliente.get("/hoje?data=2026-10-20&cor=claro").text
    assert "volta=%2Fhoje%3Fdata%3D2026-10-20%26cor%3Dclaro%23faixa-noite-0" in texto
