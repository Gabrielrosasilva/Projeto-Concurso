"""Exportar e importar preserva o conteudo e produz arquivo estavel."""
import json
from datetime import datetime, timezone

from sqlalchemy import func, select

from radar import acervo
from radar.db import sessao
from radar.models import Concurso


def _semear():
    with sessao() as s:
        s.add(
            Concurso(
                url="https://exemplo.test/palhoca",
                fonte="teste",
                titulo="Guarda Municipal de Palhoca",
                uf="SC",
                situacao="edital_publicado",
                publicado_em=datetime(2026, 9, 17, 12, 0, tzinfo=timezone.utc),
                interesse="quero",
                extra={"categorias": ["Santa Catarina"]},
            )
        )


def test_exporta_e_importa_sem_perder_dado(banco_temporario, tmp_path):
    _semear()
    arquivo = tmp_path / "concursos.json"
    assert acervo.exportar(arquivo) == 1

    # apaga tudo e reconstroi so a partir do JSON
    with sessao() as s:
        s.query(Concurso).delete()
    assert acervo.importar(arquivo) == 1

    with sessao() as s:
        concurso = s.scalar(select(Concurso))

    assert concurso.titulo == "Guarda Municipal de Palhoca"
    assert concurso.uf == "SC"
    assert concurso.interesse == "quero"
    assert concurso.extra == {"categorias": ["Santa Catarina"]}
    assert concurso.publicado_em == datetime(2026, 9, 17, 12, 0, tzinfo=timezone.utc)


def test_exportar_duas_vezes_gera_arquivo_identico(banco_temporario, tmp_path):
    """Se o dado nao mudou, o commit diario nao deve ter diff nenhum."""
    _semear()
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    acervo.exportar(a)
    acervo.exportar(b)
    assert a.read_text() == b.read_text()


def test_json_e_legivel_por_humano(banco_temporario, tmp_path):
    _semear()
    arquivo = tmp_path / "concursos.json"
    acervo.exportar(arquivo)

    texto = arquivo.read_text(encoding="utf-8")
    assert "Guarda Municipal de Palhoca" in texto   # nao escapou em \u...
    assert texto.count("\n") > 5                    # esta indentado

    linhas = json.loads(texto)
    assert "id" not in linhas[0]                    # id e interno, nao exportado


def test_importar_arquivo_inexistente_nao_quebra(banco_temporario, tmp_path):
    assert acervo.importar(tmp_path / "nao-existe.json") == 0


# --- toda coluna de data precisa voltar como data ---------------------------

def test_toda_coluna_de_data_do_modelo_e_convertida():
    """A lista de colunas de data ja foi escrita a mao, e envelheceu calada:
    `avisado_em` entrou na fase 2 e `detalhado_em` na 2.5, nenhuma das duas foi
    acrescentada ali. O `radar importar` passou a quebrar com "'str' object has
    no attribute 'tzinfo'", e a coleta diaria do GitHub Actions falhava todo
    dia - na maquina local nao aparecia, porque o banco ja existia.

    Agora a lista vem do proprio modelo. Este teste guarda isso.
    """
    from radar.models import DataHoraUTC

    do_modelo = {
        c.name for c in Concurso.__table__.columns
        if isinstance(c.type, DataHoraUTC)
    }

    assert do_modelo == set(acervo.COLUNAS_DE_DATA)


def test_importar_num_banco_vazio_com_todas_as_datas(banco_temporario, tmp_path):
    """O caso do GitHub Actions: banco inexistente, JSON com todas as datas
    preenchidas."""
    quando = datetime(2026, 9, 17, 12, 0, tzinfo=timezone.utc)
    with sessao() as s:
        s.add(Concurso(
            url="https://exemplo.test/completo",
            fonte="teste",
            titulo="Concurso com todas as datas",
            publicado_em=quando,
            inscricoes_de=quando,
            inscricoes_ate=quando,
            data_prova=quando,
            detalhado_em=quando,
            avisado_em=quando,
        ))

    arquivo = tmp_path / "concursos.json"
    acervo.exportar(arquivo)

    # apaga tudo e reimporta, como o Actions faz todo dia
    with sessao() as s:
        for c in s.scalars(select(Concurso)):
            s.delete(c)

    assert acervo.importar(arquivo) == 1

    with sessao() as s:
        lido = s.scalars(select(Concurso)).first()
    for coluna in acervo.COLUNAS_DE_DATA:
        valor = getattr(lido, coluna)
        assert valor is None or valor.tzinfo is not None, coluna


def test_data_volta_como_datetime_e_nao_como_texto(banco_temporario, tmp_path):
    """O sintoma exato do defeito: o valor chegava ao banco como str."""
    valor = acervo._desserializar("avisado_em", "2026-09-17T12:00:00+00:00")

    assert isinstance(valor, datetime)


# --- o que e meu nao volta apagado (etapa 11) -------------------------------

def _json_do_robo(arquivo, **campos) -> None:
    """O JSON como o robo do GitHub exporta: ele nao sabe dos meus campos."""
    linha = {
        "url": "https://exemplo.test/palhoca",
        "fonte": "teste",
        "titulo": "Guarda Municipal de Palhoca",
        "uf": "SC",
        "situacao": "inscricoes_abertas",
        "interesse": None,
        "notas": None,
        "salario_manual": False,
        "municipio_confirmado": False,
    }
    linha.update(campos)
    arquivo.write_text(json.dumps([linha]), encoding="utf-8")


def test_importar_nao_apaga_o_favorito_que_eu_marquei(banco_temporario, tmp_path):
    """O caso real: eu marco a estrela na web, o robo exporta o banco dele -
    que nao sabe do meu favorito - e o meu `radar importar` seguinte devolvia
    `interesse: null` por cima da minha marca."""
    with sessao() as s:
        s.add(Concurso(
            url="https://exemplo.test/palhoca", fonte="teste",
            titulo="Guarda Municipal de Palhoca",
            interesse="favorito", notas="conversei com quem fez em 2022",
        ))

    arquivo = tmp_path / "concursos.json"
    _json_do_robo(arquivo)
    acervo.importar(arquivo)

    with sessao() as s:
        concurso = s.scalar(select(Concurso))
    assert concurso.interesse == "favorito"
    assert concurso.notas == "conversei com quem fez em 2022"
    # e o que e da coleta continua chegando
    assert concurso.situacao == "inscricoes_abertas"


def test_o_salario_que_eu_digitei_sobrevive(banco_temporario, tmp_path):
    with sessao() as s:
        s.add(Concurso(
            url="https://exemplo.test/palhoca", fonte="teste", titulo="Guarda",
            salario=7000.0, salario_manual=True, municipio_confirmado=True,
        ))

    arquivo = tmp_path / "concursos.json"
    _json_do_robo(arquivo)
    acervo.importar(arquivo)

    with sessao() as s:
        concurso = s.scalar(select(Concurso))
    assert concurso.salario_manual is True
    assert concurso.municipio_confirmado is True


def test_no_computador_novo_o_favorito_volta_do_JSON(banco_temporario, tmp_path):
    """A unica situacao em que o JSON escreve favorito e nota: o concurso nao
    existe aqui. E a reinstalacao, ou a maquina nova - ali o JSON e tudo que
    existe, e e dele que os meus favoritos voltam."""
    arquivo = tmp_path / "concursos.json"
    _json_do_robo(arquivo, interesse="favorito", notas="anotei la")

    acervo.importar(arquivo)

    with sessao() as s:
        concurso = s.scalar(select(Concurso))
    assert concurso.interesse == "favorito"
    assert concurso.notas == "anotei la"


def test_da_para_DESMARCAR_um_favorito(banco_temporario, tmp_path):
    """O caminho completo, que antes voltava atras sozinho: marcar, exportar,
    desmarcar, importar. O `radar sincronizar` faz exatamente esta sequencia,
    e com a regra antiga a estrela ressuscitava a cada sincronizacao."""
    from radar import servico

    with sessao() as s:
        s.add(Concurso(url="https://exemplo.test/palhoca", fonte="teste",
                       titulo="Guarda Municipal de Palhoca"))
    with sessao() as s:
        ident = s.scalar(select(Concurso)).id

    servico.favoritar(ident)
    arquivo = tmp_path / "concursos.json"
    acervo.exportar(arquivo)                    # o JSON leva a estrela

    servico.favoritar(ident, favorito=False)    # eu desmarco aqui
    acervo.importar(arquivo)                    # e o sincronizar importa

    with sessao() as s:
        assert s.scalar(select(Concurso)).interesse is None


def test_da_para_APAGAR_uma_nota(banco_temporario, tmp_path):
    from radar import servico

    with sessao() as s:
        s.add(Concurso(url="https://exemplo.test/palhoca", fonte="teste",
                       titulo="Guarda Municipal de Palhoca"))
    with sessao() as s:
        ident = s.scalar(select(Concurso)).id

    servico.definir_notas(ident, "conversei com quem fez em 2022")
    arquivo = tmp_path / "concursos.json"
    acervo.exportar(arquivo)

    servico.definir_notas(ident, "")            # campo vazio apaga
    acervo.importar(arquivo)

    with sessao() as s:
        assert s.scalar(select(Concurso)).notas is None


def test_a_nota_trocada_nao_volta_a_antiga(banco_temporario, tmp_path):
    """Nao e so o apagar: o JSON nao pode desfazer edicao nenhuma minha."""
    from radar import servico

    with sessao() as s:
        s.add(Concurso(url="https://exemplo.test/palhoca", fonte="teste",
                       titulo="Guarda Municipal de Palhoca"))
    with sessao() as s:
        ident = s.scalar(select(Concurso)).id

    servico.definir_notas(ident, "nota velha")
    arquivo = tmp_path / "concursos.json"
    acervo.exportar(arquivo)

    servico.definir_notas(ident, "nota nova")
    acervo.importar(arquivo)

    with sessao() as s:
        assert s.scalar(select(Concurso)).notas == "nota nova"


def test_o_que_e_da_coleta_continua_chegando(banco_temporario, tmp_path):
    """A trava e so nos dois campos meus: o resto do JSON manda, como sempre."""
    with sessao() as s:
        s.add(Concurso(url="https://exemplo.test/palhoca", fonte="teste",
                       titulo="Guarda", situacao="prevista"))

    arquivo = tmp_path / "concursos.json"
    _json_do_robo(arquivo)                      # situacao=inscricoes_abertas
    acervo.importar(arquivo)

    with sessao() as s:
        assert s.scalar(select(Concurso)).situacao == "inscricoes_abertas"


# --- a linha do tempo tambem viaja (etapa 11) -------------------------------
#
# Sem isto o robo do GitHub reconstroi o banco todo dia sem historico nenhum:
# ele nao tem como saber o que ja mudou, nem o que ja avisou.

from radar.models import Evento


def _evento(**mudancas) -> Evento:
    base = dict(
        concurso_url="https://exemplo.test/palhoca",
        tipo="edital_publicado",
        descricao="Situacao: prevista -> edital_publicado",
        data=datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc),
        link="https://exemplo.test/palhoca",
    )
    base.update(mudancas)
    return Evento(**base)


def test_exporta_e_importa_a_linha_do_tempo(banco_temporario, tmp_path):
    with sessao() as s:
        s.add(_evento())
        s.add(_evento(tipo="inscricoes_abertas", descricao="Prazo: ate 30/10"))

    arquivo = tmp_path / "eventos.json"
    assert acervo.exportar_eventos(arquivo) == 2

    with sessao() as s:
        for evento in s.scalars(select(Evento)):
            s.delete(evento)

    assert acervo.importar_eventos(arquivo) == 2
    with sessao() as s:
        assert {e.tipo for e in s.scalars(select(Evento))} == {
            "edital_publicado", "inscricoes_abertas"
        }


def test_importar_duas_vezes_nao_duplica_evento(banco_temporario, tmp_path):
    """O robo importa a cada execucao: sem esta trava, a linha do tempo
    dobraria de tamanho todo dia."""
    with sessao() as s:
        s.add(_evento())

    arquivo = tmp_path / "eventos.json"
    acervo.exportar_eventos(arquivo)

    assert acervo.importar_eventos(arquivo) == 0   # ja esta no banco
    assert acervo.importar_eventos(arquivo) == 0

    with sessao() as s:
        assert s.scalar(select(func.count()).select_from(Evento)) == 1


def test_o_id_nao_e_a_identidade_do_evento(banco_temporario, tmp_path):
    """Cada maquina numera do seu jeito: o meu evento 7 e o do robo sao coisas
    diferentes. Quem diz que sao o mesmo sao os quatro campos da chave."""
    arquivo = tmp_path / "eventos.json"
    arquivo.write_text(json.dumps([{
        "concurso_url": "https://exemplo.test/palhoca",
        "tipo": "edital_publicado",
        "descricao": "Situacao: prevista -> edital_publicado",
        "data": "2026-09-20T12:00:00+00:00",
        "link": None,
        "avisado_em": None,
    }]), encoding="utf-8")

    with sessao() as s:
        s.add(_evento(link="https://outro-link.test"))   # mesmo fato, outro id

    assert acervo.importar_eventos(arquivo) == 0


def test_o_aviso_ja_dado_do_outro_lado_vale_aqui(banco_temporario, tmp_path):
    """E isto que faz a fila de avisos ser uma so: se o robo ja mandou aquele
    evento no Telegram, eu nao mando de novo."""
    with sessao() as s:
        s.add(_evento())

    arquivo = tmp_path / "eventos.json"
    acervo.exportar_eventos(arquivo)
    linhas = json.loads(arquivo.read_text(encoding="utf-8"))
    linhas[0]["avisado_em"] = "2026-09-21T09:00:00+00:00"
    arquivo.write_text(json.dumps(linhas), encoding="utf-8")

    acervo.importar_eventos(arquivo)

    with sessao() as s:
        assert s.scalar(select(Evento)).avisado_em is not None


def test_o_meu_aviso_nao_e_apagado_pelo_JSON(banco_temporario, tmp_path):
    """O contrario tambem vale: eu ja avisei, o robo nao sabe disso ainda, e o
    import dele nao pode reabrir a fila."""
    with sessao() as s:
        s.add(_evento(avisado_em=datetime(2026, 9, 21, 9, 0, tzinfo=timezone.utc)))

    arquivo = tmp_path / "eventos.json"
    arquivo.write_text(json.dumps([{
        "concurso_url": "https://exemplo.test/palhoca",
        "tipo": "edital_publicado",
        "descricao": "Situacao: prevista -> edital_publicado",
        "data": "2026-09-20T12:00:00+00:00",
        "link": None,
        "avisado_em": None,
    }]), encoding="utf-8")

    acervo.importar_eventos(arquivo)

    with sessao() as s:
        assert s.scalar(select(Evento)).avisado_em is not None


def test_sem_arquivo_de_eventos_nao_quebra(banco_temporario, tmp_path):
    """Quem atualiza de uma versao sem eventos.json roda o importar normal."""
    assert acervo.importar_eventos(tmp_path / "nao-existe.json") == 0
