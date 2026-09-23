"""A marca de alvo, que responde "e o cargo que eu quero?".

Os titulos aqui sao REAIS: sairam do banco da coleta de verdade. E por isso
que eles cobrem as armadilhas - Sapezal, SAPE/SC e SAP SP existem mesmo, e os
tres casam com a sigla "SAP" se ninguem tomar cuidado.

A regra vem de config/alvo.yml, o arquivo de verdade. Nada de lista de cargo
escrita dentro do teste: se o YAML mudar e o teste continuar passando, o teste
nao estava testando o YAML.
"""
import pytest

from radar import alvo


@pytest.fixture(autouse=True)
def yaml_limpo():
    """Cada teste le o YAML de novo: o modulo guarda o arquivo em memoria."""
    alvo.recarregar()
    yield
    alvo.recarregar()


# --- o alvo principal -------------------------------------------------------

@pytest.mark.parametrize("titulo,uf", [
    ("2013 - Secretaria de Estado da Justica e CidadaniaAgente Penitenciario "
     "(masculino)", "SC"),
    ("2016 - Governo do Estado de Santa Catarina Secretaria de Estado da "
     "Justica e Cidadania", "SC"),
    ("SEJURI SC divulga novo edital com vaga para Medico", "SC"),
    ("Concurso Policia Penal SC e autorizado com 600 vagas", "SC"),
    ("Policial Penal SC: governo confirma banca para o proximo edital", "SC"),
    ("SAP SC abre concurso para Agente Penitenciario", "SC"),
])
def test_marca_o_alvo_principal(titulo, uf):
    marca = alvo.marcar(titulo, uf=uf)
    assert marca is not None
    assert marca.alvo == alvo.PRINCIPAL
    assert marca.nome == "Policia Penal SC"


def test_os_tres_nomes_da_secretaria_valem_igual():
    """O orgao e o mesmo; o nome mudou duas vezes. O concurso de 2013 esta
    indexado como SJC e o de 2019 como SAP, e hoje a casa chama SEJURI."""
    for nome in ("Secretaria de Estado da Justica e Cidadania",
                 "Secretaria de Estado da Administracao Prisional e Socioeducativa",
                 "Secretaria de Estado de Justica e Reintegracao Social"):
        marca = alvo.marcar(f"Concurso {nome} abre vagas", uf="SC")
        assert marca is not None and marca.alvo == alvo.PRINCIPAL, nome


def test_acento_nao_atrapalha():
    """O feed escreve com acento e o YAML sem. Os dois lados sao normalizados."""
    marca = alvo.marcar("Concurso Polícia Penal (SC) abre 600 vagas", uf="SC")
    assert marca is not None and marca.alvo == alvo.PRINCIPAL


def test_o_motivo_diz_o_que_bateu():
    """Eu preciso poder auditar a marca, como faco com o anel."""
    marca = alvo.marcar("Concurso Policia Penal SC autorizado", uf="SC")
    assert "policia penal" in marca.motivo
    assert "Policia Penal SC" in marca.motivo


def test_banca_conhecida_entra_no_motivo():
    marca = alvo.marcar("Concurso Policia Penal SC", uf="SC", banca="FEPESE")
    assert "FEPESE" in marca.motivo


def test_a_banca_sozinha_nao_marca_nada():
    """A FEPESE faz dezenas de concursos de prefeitura por ano. Se a banca
    marcasse alvo, metade de Santa Catarina viraria alvo principal."""
    marca = alvo.marcar(
        "Concurso Prefeitura de Tunapolis (SC) tem salario de R$ 5.832",
        uf="SC",
        banca="FEPESE",
    )
    assert marca is None


# --- o que NAO pode virar alvo principal ------------------------------------

@pytest.mark.parametrize("titulo,uf", [
    # a sigla SAP dentro de outra palavra: os quatro estao no banco de verdade
    ("Prefeitura de Sapezal (MT) oferece ate R$ 13 mil em novo edital", "MT"),
    ("Prefeitura de Sapiranga (RS) libera edital com salario de R$ 3,2 mil", "RS"),
    ("Concurso Camara de Massape (CE) abre 26 vagas", "CE"),
    # SAPE/SC e a Secretaria da Agricultura, e ate a UF bate
    ("Concurso SAPE SC tem edital publicado para 20 vagas", "SC"),
    ("2026 - Secretaria de Estado da Agricultura e Pecuaria de Santa Catarina "
     "(SAPE/SC)", "SC"),
])
def test_sigla_dentro_de_outra_palavra_nao_marca(titulo, uf):
    assert alvo.marcar(titulo, uf=uf) is None


def test_sap_de_sao_paulo_nao_e_o_meu_alvo():
    """Sao Paulo tem uma secretaria de mesma sigla, e ela esta no feed."""
    marca = alvo.marcar("SAP SP abre estagio com bolsa mensal", uf="SP")
    assert marca is None


def test_policia_penal_de_outro_estado_nao_e_o_meu_alvo():
    """O alvo principal e estadual de SC. Parana e outro concurso."""
    assert alvo.marcar("Concurso Policia Penal do Parana autorizado", uf="PR") is None


def test_penitenciario_de_outro_estado_nao_marca():
    """O caso real do feed: o Maranhao publica seletivo de Auxiliar
    Penitenciario toda semana."""
    assert alvo.marcar(
        "SEAP MA divulga seletivos para Auxiliar e Especialista Penitenciario",
        uf="MA",
    ) is None


def test_sem_uf_so_marca_com_prova_de_sc():
    """A FEPESE e a IESES nao informam UF. Sem prova no texto, nao se chuta."""
    assert alvo.marcar("Concurso para Agente Penitenciario") is None
    marca = alvo.marcar("Agente Penitenciario em Santa Catarina")
    assert marca is not None and marca.alvo == alvo.PRINCIPAL


def test_policia_penal_federal_cai_no_secundario():
    """Policia Penal Federal casa com "policia penal" e e outro concurso."""
    marca = alvo.marcar("Concurso Policia Penal Federal deve sair em 2027")
    assert marca.alvo == alvo.SECUNDARIO
    assert marca.nome == "Policia Penal Federal"


def test_federal_com_prova_em_sc_continua_secundario():
    """Nem citar Santa Catarina promove o federal a alvo principal."""
    marca = alvo.marcar(
        "Concurso Policia Penal Federal tera provas em Santa Catarina", uf=None
    )
    assert marca.alvo == alvo.SECUNDARIO


# --- os alvos secundarios ---------------------------------------------------

@pytest.mark.parametrize("titulo,nome", [
    ("Concurso Prefeitura de Guarulhos (SP) abre 200 vagas para Guarda Municipal",
     "Guarda Municipal"),
    ("2023 - Guarda Municipal de Sao Jose", "Guarda Municipal"),
    ("Concurso Policia Civil SC abre vagas para Escrivao", "Policia Civil"),
    ("Concurso Bombeiro Militar SC tem edital publicado", "Bombeiro Militar"),
    ("Concurso Policia Cientifica SC abre vagas para Perito Criminal",
     "Policia Cientifica"),
])
def test_marca_o_alvo_secundario(titulo, nome):
    marca = alvo.marcar(titulo)
    assert marca is not None
    assert marca.alvo == alvo.SECUNDARIO
    assert marca.nome == nome


def test_a_ordem_do_yaml_decide_o_empate():
    """Um titulo que cite oficial E bombeiro militar e sobre o curso de
    oficial, que vem antes na minha lista."""
    marca = alvo.marcar("Inscricoes abertas para Oficial Bombeiro Militar em SC")
    assert marca.nome == "Oficial de Bombeiros"


def test_o_que_nao_e_cargo_meu_fica_sem_marca():
    """A marca nao descarta nada: quem nao bate so continua sem ela."""
    assert alvo.marcar(
        "Concurso Prefeitura de Ascurra (SC) oferta salarios de ate R$ 6,2 mil"
    ) is None
    assert alvo.marcar("Bolsa Familia passa a ter novo valor em outubro") is None


# --- o YAML e quem manda ----------------------------------------------------

def test_a_regra_vem_do_arquivo_e_nao_do_codigo(tmp_path, monkeypatch):
    """Trocar o YAML tem que trocar o resultado. Se este teste passar com o
    arquivo de verdade, e porque o cargo esta escrito no codigo."""
    (tmp_path / "alvo.yml").write_text(
        "principal:\n"
        "  nome: Fiscal de Rua\n"
        "  termos: [fiscal de rua]\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("RADAR_CONFIG_DIR", str(tmp_path))
    alvo.recarregar()

    assert alvo.marcar("Concurso Policia Penal SC", uf="SC") is None
    marca = alvo.marcar("Prefeitura abre vaga para Fiscal de Rua")
    assert marca.alvo == alvo.PRINCIPAL and marca.nome == "Fiscal de Rua"


def test_sem_arquivo_nenhum_nao_quebra(tmp_path, monkeypatch):
    """Arquivo ausente vira "nenhum alvo", e nao erro na coleta diaria."""
    monkeypatch.setenv("RADAR_CONFIG_DIR", str(tmp_path))
    alvo.recarregar()
    assert alvo.marcar("Concurso Policia Penal SC", uf="SC") is None


# --- a marca chega ao banco -------------------------------------------------
# O modulo acima decide a marca; aqui a gente confere que ela e gravada, e que
# `radar reclassificar` a recalcula - e assim que eu corrijo config/alvo.yml
# sem ter que recoletar nada.

def _semear(**mudancas):
    from radar.db import sessao
    from radar.models import Concurso

    base = dict(
        url="https://exemplo.test/pp",
        fonte="fepese",
        titulo="Concurso Policia Penal SC e autorizado com 600 vagas",
        uf="SC",
        tipo="concurso",
    )
    base.update(mudancas)
    with sessao() as s:
        s.add(Concurso(**base))


def _do_banco():
    from sqlalchemy import select

    from radar.db import sessao
    from radar.models import Concurso

    with sessao() as s:
        return s.scalar(select(Concurso))


def test_reclassificar_grava_a_marca(banco_temporario):
    from radar import servico

    _semear()
    servico.reclassificar()

    concurso = _do_banco()
    assert concurso.alvo == alvo.PRINCIPAL
    assert "Policia Penal SC" in concurso.motivo_alvo


def test_reclassificar_tira_a_marca_de_quem_deixou_de_bater(banco_temporario):
    """A marca e calculada, como o anel: se eu apertar a regra no YAML, o
    banco inteiro se corrige na hora, sem ir a internet."""
    from radar import servico

    _semear(titulo="Concurso Prefeitura de Ascurra (SC) abre vagas",
            alvo="principal", motivo_alvo="marca velha, de regra antiga")
    servico.reclassificar()

    concurso = _do_banco()
    assert concurso.alvo is None
    assert concurso.motivo_alvo is None


def test_a_contagem_por_alvo_inclui_noticia(banco_temporario):
    """Noticia sobre a Policia Penal SC e sinal, nao ruido: e o que avisa que
    o concurso vem antes de existir edital."""
    from radar import servico

    _semear(tipo="noticia",
            titulo="Governo anuncia concurso da Policia Penal SC para 2027")
    servico.reclassificar()

    assert servico.contar_por_alvo().get("principal") == 1
    assert len(servico.concursos_do_alvo("principal")) == 1


# --- os outros nomes do mesmo cargo (etapa 9) -------------------------------

def test_sinonimos_do_principal_saem_do_yaml():
    """O cargo mudou de nome: "Policial Penal" hoje, "Agente Penitenciario"
    nas duas provas que existem. A lista de termos ja sabia disso."""
    sinonimos = alvo.sinonimos_do_cargo("Policial Penal")

    assert "agente penitenciario" in sinonimos
    assert "policia penal" in sinonimos


def test_o_nome_como_o_hotsite_escreve_tambem_acha():
    """"Agente Penitenciario - Feminino (AP)" e o rotulo real do hotsite de
    2019: ele CONTEM o termo, em vez de ser igual a ele."""
    assert alvo.sinonimos_do_cargo("Agente Penitenciario - Feminino (AP)")


def test_secundario_tambem_tem_sinonimo():
    """Metade dos editais escreve "Guarda Civil Municipal"."""
    assert "guarda civil municipal" in alvo.sinonimos_do_cargo("Guarda Municipal")


def test_cargo_fora_do_yaml_nao_tem_sinonimo():
    """Sem invencao: o que nao esta anotado nao ganha parente."""
    assert alvo.sinonimos_do_cargo("Merendeira") == []
    assert alvo.sinonimos_do_cargo("") == []
