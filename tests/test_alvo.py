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


def test_policia_penal_de_outro_estado_avisa_mas_nao_e_o_meu_concurso():
    """Parana e o mesmo cargo e outro concurso. As duas coisas sao verdade ao
    mesmo tempo, e por isso ele tem marca propria: eu quero o aviso na hora
    (outra banca abrindo o cargo e noticia), e nao quero a prova dele no meu
    estudo (outra banca, outro programa, outra lei estadual)."""
    marca = alvo.marcar("Concurso Policia Penal do Parana autorizado", uf="PR")

    assert marca.alvo == alvo.PRINCIPAL_FORA
    assert marca.alvo in alvo.PRINCIPAIS       # avisa como o principal
    assert marca.alvo != alvo.PRINCIPAL        # e nao entra no estudo
    assert "fora do estado" in marca.motivo


def test_cargo_parecido_com_o_meu_nao_marca():
    """O caso real do feed: o Maranhao publica seletivo de Auxiliar
    Penitenciario toda semana. Quem barra aqui nao e o estado - e o cargo:
    "Auxiliar Penitenciario" nao e nenhum dos nomes que eu anotei."""
    assert alvo.marcar(
        "SEAP MA divulga seletivos para Auxiliar e Especialista Penitenciario",
        uf="MA",
    ) is None


def test_sem_uf_o_cargo_avisa_mas_nao_vira_o_alvo_de_sc():
    """A FEPESE e a IESES nao informam UF. Sem prova no texto o cargo continua
    valendo aviso - nao saber de onde e nao e motivo para perder a noticia -
    mas nao vira o meu concurso, que essa e a parte que exige prova."""
    assert alvo.marcar("Concurso para Agente Penitenciario").alvo == (
        alvo.PRINCIPAL_FORA
    )
    marca = alvo.marcar("Agente Penitenciario em Santa Catarina")
    assert marca is not None and marca.alvo == alvo.PRINCIPAL


def test_o_orgao_sozinho_continua_exigindo_prova_de_sc():
    """O que relaxou foi o CARGO, e so ele. A sigla "SAP" e o nome de uma
    secretaria de Sao Paulo tambem, e "SAP SP abre estagio" esta no feed: sem
    prova de estado, nome de orgao nao marca nada."""
    assert alvo.marcar("SAP divulga calendario de 2027") is None
    assert alvo.marcar("SAP SP abre estagio com bolsa mensal", uf="SP") is None


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


def test_o_alvo_secundario_nao_tem_sinonimo():
    """Nos blocos secundarios os termos nomeiam a CARREIRA, nao um cargo: a
    Policia Civil lista delegado, escrivao, investigador e agente, que sao
    quatro cargos com quatro provas diferentes. Trata-los como o mesmo cargo
    seria a equivalencia falsa que a prova substituta evita."""
    assert alvo.sinonimos_do_cargo("Agente de Policia") == []
    assert alvo.sinonimos_do_cargo("Guarda Municipal") == []


def test_o_que_o_yaml_exclui_nao_ganha_sinonimo():
    """"Policia Penal Federal" contem "policia penal" e e outro concurso -
    tem bloco proprio nos secundarios. Sem esta trava, procurar prova dele
    devolvia os cadernos de Agente Penitenciario de SC como se fossem o
    mesmo cargo."""
    assert alvo.sinonimos_do_cargo("Policia Penal Federal") == []
    assert alvo.sinonimos_do_cargo("Policial Penal Federal") == []


def test_cargo_fora_do_yaml_nao_tem_sinonimo():
    """Sem invencao: o que nao esta anotado nao ganha parente."""
    assert alvo.sinonimos_do_cargo("Merendeira") == []
    assert alvo.sinonimos_do_cargo("") == []


# --- o plural, que a comparacao por palavra inteira nao da de graca ---------
#
# Titulos reais da coleta: noticia sobre concurso quase sempre fala no plural
# ("600 policiais penais"), e era justamente a noticia que eu nao podia
# perder - ela chega antes de existir edital.

@pytest.mark.parametrize("titulo", [
    "Concurso PP SC: governo autoriza contratacao de 600 policiais penais",
    "Concurso para agentes penitenciarios em Santa Catarina",
    "Santa Catarina abre concurso para agente prisional",
    "SC vai convocar agentes prisionais aprovados",
])
def test_o_cargo_no_plural_bate_no_alvo_principal(titulo):
    marca = alvo.marcar(titulo, uf="SC")

    assert marca is not None
    assert marca.alvo == alvo.PRINCIPAL


def test_o_plural_tambem_vale_para_a_tela_de_foco():
    """`nomeia_cargo_do_principal` decide o que a home pode AFIRMAR: e ela que
    separa "edital aberto do meu cargo" de "edital aberto na mesma casa"."""
    assert alvo.nomeia_cargo_do_principal("policiais penais tomam posse")
    assert alvo.nomeia_cargo_do_principal("agentes penitenciarios convocados")


def test_o_plural_do_federal_continua_excluido():
    """"Policia Penal Federal" e outro concurso, e no plural tambem: sem
    "penais federais" na exclusao, o titulo federal virava o meu alvo."""
    titulo = "Concurso reune policiais penais federais em Santa Catarina"
    marca = alvo.marcar(titulo, uf="SC")

    assert marca.alvo == alvo.SECUNDARIO
    assert marca.nome == "Policia Penal Federal"


def test_o_plural_tambem_cai_na_marca_de_fora_do_estado():
    """O plural e justamente como a noticia escreve ("600 policiais penais"),
    e a noticia de outro estado e a que chega primeiro de todas."""
    for titulo, uf in [
        ("Governo do PR contrata policiais penais", "PR"),
        ("Parana contrata policiais penais", None),
    ]:
        marca = alvo.marcar(titulo, uf=uf)
        assert marca.alvo == alvo.PRINCIPAL_FORA, titulo


# --- a mesma trava de estado, para quem ja tem o item no banco --------------

def test_a_uf_decide_quando_existe():
    """Com UF na mao ela manda, e o texto nao tem voto."""
    assert alvo.e_do_estado_do_principal("SC", "Concurso qualquer")
    assert alvo.e_do_estado_do_principal("sc", "Concurso qualquer")
    assert not alvo.e_do_estado_do_principal(
        "PR", "Policia Penal de Santa Catarina"
    )


def test_sem_uf_quem_decide_e_a_palavra_que_so_existe_aqui():
    """A FEPESE e a IESES nao informam a UF. Ai vale a mesma lista de sempre,
    `prova_de_sc`, nunca a sigla solta."""
    assert alvo.e_do_estado_do_principal(None, "Policia Penal de Santa Catarina")
    assert alvo.e_do_estado_do_principal(None, "SEJURI abre concurso")
    assert not alvo.e_do_estado_do_principal(None, "Policia Penal do Parana")


def test_sem_uf_e_sem_palavra_a_resposta_e_nao():
    """Nunca chutar: a duvida nao vira sim, nem para o acervo de provas."""
    assert not alvo.e_do_estado_do_principal(None, "")
    assert not alvo.e_do_estado_do_principal(None, "Concurso Policia Penal")


# --- de olho: a cidade que muda o aviso sem mudar o alvo (etapa 14) --------
#
# Guarda Municipal continua sendo alvo secundario em qualquer lugar. Em duas
# cidades - as unicas em que eu prestaria - ela passa a furar o teto de
# mensagens do dia, e ganha um cartao no Meu foco. Quem escolhe as cidades e
# o `de_olho` do config/alvo.yml, nunca o codigo.

def test_a_cidade_de_olho_liga_a_prioridade():
    for titulo in (
        "Concurso Guarda Municipal de Florianopolis abre 40 vagas",
        "Prefeitura de Balneario Camboriu abre concurso para Guarda Municipal",
    ):
        marca = alvo.marcar(titulo)
        assert marca.alvo == alvo.SECUNDARIO, titulo
        assert marca.prioritario is True, titulo
        assert "De olho" in marca.motivo


def test_de_olho_nao_promove_o_cargo_a_alvo_principal():
    """Guarda Municipal em Florianopolis continua sendo Guarda Municipal. O
    que muda e o teto do aviso, e nada mais: ela nao entra no estudo, que e
    do cargo que eu vou prestar."""
    marca = alvo.marcar("Guarda Municipal de Florianopolis: edital publicado")
    assert marca.nome == "Guarda Municipal"
    assert marca.alvo not in alvo.PRINCIPAIS


def test_guarda_de_outra_cidade_segue_como_sempre():
    marca = alvo.marcar(
        "Concurso Prefeitura de Guarulhos (SP) abre 200 vagas para Guarda "
        "Municipal"
    )
    assert marca.alvo == alvo.SECUNDARIO
    assert marca.prioritario is False


def test_a_cidade_vale_mesmo_quando_so_o_campo_municipio_a_traz():
    """O titulo da FEPESE costuma ser "2026 - Prefeitura Municipal de X". A
    cidade chega no campo `municipio`, que o classificador ja extraiu, e sem
    ele o cartao de Florianopolis ficaria vazio com o concurso na tela."""
    marca = alvo.marcar(
        "2026 - Prefeitura Municipal: Guarda Municipal",
        municipio="Florianópolis",
    )
    assert marca.prioritario is True


def test_a_cidade_sozinha_nao_liga_nada():
    """Sem o cargo, a cidade nao diz nada: Florianopolis abre concurso de
    professor toda semana."""
    assert alvo.marcar(
        "Concurso Prefeitura de Florianopolis abre vagas para Professor"
    ) is None


def test_o_par_de_olho_diz_qual_cartao_o_concurso_preenche():
    """E o que o Meu foco usa para nao trocar uma cidade pela outra."""
    assert alvo.par_de_olho(
        "Guarda Municipal de Balneario Camboriu tem edital"
    ) == ("Guarda Municipal", "Balneario Camboriu")
    assert alvo.par_de_olho("Guarda Municipal de Guarulhos") is None


def test_a_lista_de_olho_sai_do_yaml():
    pedidas = alvo.de_olho()
    assert {p["cidade"] for p in pedidas} == {
        "Balneario Camboriu", "Florianopolis"
    }
    assert {p["cargo"] for p in pedidas} == {"Guarda Municipal"}


def test_sem_de_olho_no_yaml_ninguem_e_prioritario(tmp_path, monkeypatch):
    """A regra mora no arquivo: tirando a lista de la, a prioridade some."""
    (tmp_path / "alvo.yml").write_text(
        "secundarios:\n"
        "  - nome: Guarda Municipal\n"
        "    termos: [guarda municipal]\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("RADAR_CONFIG_DIR", str(tmp_path))
    alvo.recarregar()

    assert alvo.de_olho() == []
    marca = alvo.marcar("Guarda Municipal de Florianopolis abre vagas")
    assert marca.alvo == alvo.SECUNDARIO and marca.prioritario is False


def test_a_prioridade_chega_ao_banco(banco_temporario):
    """A marca so vale se for gravada: e a coluna que o aviso consulta."""
    from radar import servico

    _semear(
        url="https://exemplo.test/gm-fpolis",
        titulo="Concurso Guarda Municipal de Florianopolis abre 40 vagas",
    )
    servico.reclassificar()

    concurso = _do_banco()
    assert concurso.alvo == alvo.SECUNDARIO
    assert concurso.alvo_prioritario is True


def test_o_cargo_fora_do_estado_chega_ao_banco(banco_temporario):
    from radar import servico

    _semear(
        url="https://exemplo.test/pp-pr",
        titulo="Governo do Parana autoriza concurso da Policia Penal",
        uf="PR",
    )
    servico.reclassificar()

    concurso = _do_banco()
    assert concurso.alvo == alvo.PRINCIPAL_FORA
    assert concurso.alvo_prioritario is False


# --- a prova de reforco (25/09/2026) ----------------------------------------

@pytest.mark.parametrize("cargo, ano, esperado", [
    ("Agente de Segurança Socioeducativo (AS)", 2016, True),
    # O mesmo cargo em 2013 e outra decisao, e nao entra por semelhanca.
    ("Agente de Segurança Socioeducativo", 2013, False),
    # A minha prova nao e reforco: ela e a prova.
    ("Agente Penitenciário - Feminino (AP)", 2019, False),
    (None, 2016, False),
])
def test_reforco_e_cargo_e_ano(cargo, ano, esperado):
    assert alvo.e_reforco(cargo, ano) is esperado
