"""Gerar questoes dentro de um escopo fechado (Etapa 5, secoes 7, 8 e 9).

O que estes testes seguram, e e o coracao da etapa:

  * **nenhuma questao fora do escopo informado entra** (§8). A IA declara o no
    de cada questao, e a importacao recusa a que declarou outro - a garantia e
    a validacao do que ela declara, nao a confianca nela;
  * nome que a arvore nao tem PARA o pedido, com sugestoes, e nao gera nada
    (§7): o sistema nunca alarga o escopo sozinho;
  * o modo revisao so pega nos que eu ja estudei (§8, modo 2);
  * a base de cada questao fica registrada, com a evidencia (alvo ou
    complementar), e `do_zero` so com a marca "sem questao real de
    referencia" (§9);
  * as 50 geradas antes desta etapa continuam listadas, com os campos novos
    nulos.

Nada aqui vai a internet nem chama a API: o caminho testado e o do
pedido/importacao em arquivo.
"""
import json
from datetime import date

import pytest

from radar import conteudos as arvore
from radar.db import sessao
from radar.models import (
    Classificacao,
    Conteudo,
    QuestaoDeProva,
    QuestaoGerada,
)
from radar.servico import classificacoes
from radar.servico import conteudos as servico_conteudos
from radar.servico import geradas, manual

CARGO = "Agente Penitenciário"
CONCURSO = "https://fepese.test/concurso-2019"
CADERNO_DO_ALVO = "https://fepese.test/ap2019.pdf"
CADERNO_COMPLEMENTAR = "https://fepese.test/gm2024.pdf"
CONCURSO_COMPLEMENTAR = "https://fepese.test/concurso-gm-2024"

LEP = "Lei de Execução Penal"
REGIMES = "Lei de Execução Penal > Regimes de cumprimento da pena"
ART_112 = "Lei de Execução Penal > Regimes de cumprimento da pena > LEP, art. 112"
ART_119 = "Lei de Execução Penal > Regimes de cumprimento da pena > LEP, art. 119"
REMICAO = "Lei de Execução Penal > Remição"
PENAL = "Direito Penal"


@pytest.fixture
def arvore_de_teste(banco_temporario):
    """Duas materias, com subassunto e dois elementos num deles."""
    with sessao() as s:
        for caminho, pai, nivel in [
            (LEP, None, "materia"),
            (REGIMES, LEP, "assunto"),
            (ART_112, REGIMES, "subassunto"),
            (ART_119, REGIMES, "subassunto"),
            (REMICAO, LEP, "assunto"),
            (PENAL, None, "materia"),
        ]:
            s.add(Conteudo(caminho=caminho, pai=pai, nivel=nivel,
                           nome=arvore.partes(caminho)[-1], origem="edital",
                           procedencia="teste"))


def _concurso():
    """O concurso-alvo, com os campos que o `foco._provas_do_alvo` exige."""
    from datetime import timedelta

    from radar.models import Concurso, agora

    return Concurso(
        url=CONCURSO, fonte="fepese",
        titulo="2019 - Secretaria de Estado da Administracao Prisional",
        uf="SC", tipo="concurso", situacao="encerrado", relevancia="estadual",
        alvo="principal", motivo_alvo="Alvo principal (Policia Penal SC).",
        publicado_em=agora() - timedelta(days=100),
    )


def _questao(numero: int, caderno: str = CADERNO_DO_ALVO, materia: str = LEP,
             texto: str | None = None) -> QuestaoDeProva:
    # O caderno complementar e de OUTRO concurso: pendurado no concurso-alvo
    # ele seria alvo tambem, e o teste da prioridade nao provaria nada.
    concurso = (CONCURSO_COMPLEMENTAR if caderno == CADERNO_COMPLEMENTAR
                else CONCURSO)
    return QuestaoDeProva(
        prova_url=caderno, banca="FEPESE", concurso_url=concurso, ano=2019,
        cargo=CARGO, numero=numero, materia=materia,
        enunciado=texto or f"questão real número {numero} sobre a LEP?",
        alternativas={"a": f"a{numero}", "b": f"b{numero}", "c": f"c{numero}",
                      "d": f"d{numero}", "e": f"e{numero}"},
        resposta="a", impressao=f"imp{numero}",
    )


def _gravar(questao: QuestaoDeProva, no: str | None) -> str:
    """Grava a questao e, se houver no, a classificacao dela. Devolve a chave."""
    from sqlalchemy import select

    from radar.models import Concurso

    with sessao() as s:
        existe = s.scalar(select(Concurso).where(Concurso.url == CONCURSO))
        if existe is None:
            s.add(_concurso())
    with sessao() as s:
        s.add(questao)
        s.flush()
        chave = classificacoes.chave_de(questao)
    if no:
        classificacoes.classificar(chave, no, "teste")
    return chave


def _resolver(materia=None, assunto=None, subassunto=None, elementos=None):
    return arvore.resolver_escopo(
        servico_conteudos.caminhos(), materia, assunto, subassunto, elementos)


# --- o filtro hierarquico (§7) --------------------------------------------------

def test_o_escopo_desce_os_quatro_niveis(arvore_de_teste):
    escopo = _resolver(LEP, "Regimes de cumprimento da pena", "LEP, art. 112")

    assert escopo.no == ART_112
    assert escopo.nivel == "subassunto"
    assert escopo.especifico


def test_sem_nada_nao_ha_escopo(arvore_de_teste):
    """A consulta ampla por matéria não foi removida (§7)."""
    assert _resolver() is None
    assert _resolver(LEP).nivel == "materia"
    assert not _resolver(LEP).especifico


def test_assunto_que_nao_existe_para_o_pedido_e_sugere(arvore_de_teste):
    with pytest.raises(arvore.EscopoInvalido) as erro:
        _resolver(LEP, "Regime de cumprimento")      # sem o "s", e sem "da pena"

    assert "não existe" in str(erro.value)
    assert "Regimes de cumprimento da pena" in str(erro.value)
    assert erro.value.sugestoes == [REGIMES]


def test_materia_que_nao_existe_lista_as_que_existem(arvore_de_teste):
    with pytest.raises(arvore.EscopoInvalido) as erro:
        _resolver("LEP")              # o apelido nao e o nome do edital

    assert LEP in str(erro.value)


def test_nome_sem_nenhuma_semelhanca_lista_em_vez_de_sugerir(arvore_de_teste):
    with pytest.raises(arvore.EscopoInvalido) as erro:
        _resolver(LEP, "xilofone")

    assert erro.value.sugestoes == []
    assert "Os que existem" in str(erro.value)


def test_subassunto_sem_assunto_nao_fecha_escopo(arvore_de_teste):
    with pytest.raises(arvore.EscopoInvalido, match="não fecha um escopo"):
        _resolver(LEP, None, "LEP, art. 112")


def test_assunto_sem_materia_nao_fecha_escopo(arvore_de_teste):
    with pytest.raises(arvore.EscopoInvalido, match="Sem a matéria"):
        _resolver(None, "Regimes de cumprimento da pena")


def test_elemento_repetivel_restringe_o_escopo(arvore_de_teste):
    escopo = _resolver(LEP, "Regimes de cumprimento da pena",
                       elementos=["LEP, art. 112", "LEP, art. 119"])

    assert escopo.nivel == "elemento"
    assert escopo.caminhos == (ART_112, ART_119)
    assert escopo.dentro(ART_112) and escopo.dentro(ART_119)
    # O irmao que eu NAO pedi fica fora, mesmo sendo do mesmo assunto.
    assert not escopo.dentro(REGIMES)


def test_o_escopo_sem_elemento_cobre_tudo_abaixo(arvore_de_teste):
    escopo = _resolver(LEP, "Regimes de cumprimento da pena")

    assert escopo.dentro(REGIMES) and escopo.dentro(ART_112)
    assert not escopo.dentro(REMICAO)


def test_o_escopo_nao_pega_no_de_nome_parecido_de_outro_ramo(arvore_de_teste):
    """"Lei de Execução Penal > Remição" não está em "> Regimes...", e um
    `startswith` ingênuo poderia achar que sim."""
    assert not _resolver(LEP, "Regimes de cumprimento da pena").dentro(REMICAO)


# --- as questoes reais do escopo, alvo antes do complementar (§9) ---------------

def test_as_reais_do_escopo_saem_da_classificacao(arvore_de_teste):
    dentro = _gravar(_questao(1), ART_112)
    _gravar(_questao(2), REMICAO)                 # mesma materia, outro assunto
    _gravar(_questao(3), None)                    # sem classificacao

    achadas = geradas.reais_do_escopo(
        _resolver(LEP, "Regimes de cumprimento da pena"))

    assert [classificacoes.chave_de(q) for q, _e in achadas] == [dentro]


def test_o_alvo_vem_antes_do_complementar(arvore_de_teste, monkeypatch):
    _gravar(_questao(1, CADERNO_COMPLEMENTAR), ART_112)
    _gravar(_questao(2, CADERNO_DO_ALVO), ART_112)
    monkeypatch.setattr(
        "radar.servico.complementar.provas_aceitas",
        lambda *a, **k: {CADERNO_COMPLEMENTAR},
    )

    achadas = geradas.reais_do_escopo(
        _resolver(LEP, "Regimes de cumprimento da pena"))

    assert [e for _q, e in achadas] == ["alvo", "complementar"]


def test_prova_complementar_nao_aceita_fica_de_fora(arvore_de_teste, monkeypatch):
    """A mesma regra de toda estatistica: prova sem validacao nao entra."""
    _gravar(_questao(1, CADERNO_COMPLEMENTAR), ART_112)
    monkeypatch.setattr("radar.servico.complementar.provas_aceitas",
                        lambda *a, **k: set())

    assert geradas.reais_do_escopo(
        _resolver(LEP, "Regimes de cumprimento da pena")) == []


def test_anulada_nao_serve_de_base(arvore_de_teste):
    questao = _questao(1)
    questao.anulada = True
    _gravar(questao, ART_112)

    assert geradas.reais_do_escopo(
        _resolver(LEP, "Regimes de cumprimento da pena")) == []


# --- os tres modos (§8) ---------------------------------------------------------

def test_sem_modo_com_assunto_e_treino(arvore_de_teste):
    escopo = _resolver(LEP, "Regimes de cumprimento da pena")

    assert geradas.modo_do_pedido(escopo) == "treino"


def test_sem_modo_so_com_materia_e_simulado(arvore_de_teste):
    """A seleção ampla não pode ser confundida com treino específico (§8)."""
    assert geradas.modo_do_pedido(_resolver(LEP)) == "simulado"
    assert geradas.modo_do_pedido(None) == "simulado"


def test_modo_que_nao_existe_e_recusado(arvore_de_teste):
    with pytest.raises(ValueError, match="nao existe"):
        geradas.modo_do_pedido(None, "chute")


def test_o_modo_revisao_so_pega_no_estudado(arvore_de_teste, monkeypatch):
    """O registro de "estudado" é o da Etapa 4, e não uma conta nova."""
    monkeypatch.setattr(geradas, "nos_estudados",
                        lambda materia=None: [REGIMES, ART_112])

    escopo = geradas.escopo_da_revisao(LEP)

    assert escopo.dentro(REGIMES) and escopo.dentro(ART_112)
    assert not escopo.dentro(REMICAO)         # existe, e eu nunca estudei


def test_revisao_sem_nada_estudado_para_em_vez_de_alargar(arvore_de_teste,
                                                          monkeypatch):
    monkeypatch.setattr(geradas, "nos_estudados", lambda materia=None: [])

    with pytest.raises(arvore.EscopoInvalido, match="não há"):
        geradas.escopo_da_revisao(LEP)


def test_o_plano_leva_o_modo_e_o_escopo(arvore_de_teste):
    _gravar(_questao(1), ART_112)

    plano = geradas.preparar(quantas=3, escopo=_resolver(
        LEP, "Regimes de cumprimento da pena"), semente=1)

    assert plano["modo_do_pedido"] == "treino"
    assert plano["escopo"].no == REGIMES
    assert plano["do_alvo"] == 1 and plano["do_complementar"] == 0


# --- a prioridade da base (§9) --------------------------------------------------

def test_a_real_vem_primeiro_e_o_resto_sai_da_fonte_oficial(arvore_de_teste):
    """Uma real e vinte pedidas: 3 variacoes dela, e o resto do zero DENTRO do
    mesmo no - nunca de um no vizinho para "achar base"."""
    _gravar(_questao(1), ART_112)

    plano = geradas.preparar(quantas=20, escopo=_resolver(
        LEP, "Regimes de cumprimento da pena"), semente=1)

    assert plano["quantas"] == 20
    primeiro = plano["pedidos"][0]
    assert primeiro["modo"] == "variacao" and primeiro["base"] == "questao_real"
    assert primeiro["evidencia_da_base"] == "alvo"
    resto = plano["pedidos"][1:]
    assert resto and all(p["modo"] == "do_zero" for p in resto)
    assert all(p["evidencia_da_base"] == "nenhuma" for p in resto)
    assert all(p["conteudo"] == REGIMES for p in plano["pedidos"])


def test_sem_real_nenhuma_a_base_e_a_fonte_ou_o_edital(arvore_de_teste):
    plano = geradas.preparar(quantas=3, escopo=_resolver(
        LEP, "Regimes de cumprimento da pena"), semente=1)

    assert plano["sem_base"] and plano["base_disponivel"] == 0
    (pedido,) = plano["pedidos"]
    assert pedido["base"] in ("fonte_oficial", "item_do_edital")
    assert pedido["evidencia_da_base"] == "nenhuma"


# --- o pedido com escopo --------------------------------------------------------

def test_o_pedido_manda_nao_sair_do_escopo_e_declarar_o_no(arvore_de_teste):
    _gravar(_questao(1), ART_112)

    lote = manual.pedido_de_questoes(quantas=3, escopo=_resolver(
        LEP, "Regimes de cumprimento da pena"))

    (pedido,) = lote["pedidos"]
    assert "ESCOPO FECHADO" in pedido["instrucao"]
    assert f"CONTEUDO: {REGIMES}" in pedido["instrucao"]
    assert '"conteudo"' in pedido["instrucao"]
    assert pedido["escopo"] == REGIMES
    assert pedido["modo_do_pedido"] == "treino"


def test_o_pedido_com_dispositivo_escreve_quais_sao(arvore_de_teste):
    lote = manual.pedido_de_questoes(quantas=3, escopo=_resolver(
        LEP, "Regimes de cumprimento da pena", elementos=["LEP, art. 112"]))

    pedido = lote["pedidos"][0]
    assert "DISPOSITIVOS: LEP, art. 112" in pedido["instrucao"]
    assert pedido["escopo_dispositivos"] == [ART_112]


def test_o_pedido_amplo_nao_ganha_escopo(arvore_de_teste):
    """Sem escopo o pedido é o de sempre: a §7 manda preservá-lo."""
    _gravar(_questao(1, materia=LEP), None)

    lote = manual.pedido_de_questoes(materia=LEP, quantas=3)

    pedido = lote["pedidos"][0]
    assert pedido["escopo"] is None
    assert pedido["modo_do_pedido"] == "simulado"
    assert "ESCOPO FECHADO" not in pedido["instrucao"]


# --- a importacao: NENHUMA questao fora do escopo entra (§8) --------------------

def _resposta(lote: dict, itens: list[dict]) -> dict:
    return {"lote": lote["lote"],
            "respostas": [{"id": lote["pedidos"][0]["id"], "questoes": itens}]}


def _item(conteudo: str | None = REGIMES, artigo: str = "LEP, art. 112",
          enunciado: str = "Sobre o regime de cumprimento da pena, assinale.") -> dict:
    item = {
        "enunciado": enunciado,
        "alternativas": {"a": "primeira", "b": "segunda", "c": "terceira",
                         "d": "quarta", "e": "quinta"},
        "resposta": "a", "artigo": artigo,
    }
    if conteudo is not None:
        item["conteudo"] = conteudo
    return item


def _importar(tmp_path, lote: dict, itens: list[dict]) -> dict:
    pedido = tmp_path / "pedido.json"
    resposta = tmp_path / "resposta.json"
    manual.salvar_pedido(lote, pedido)
    resposta.write_text(json.dumps(_resposta(lote, itens), ensure_ascii=False),
                        encoding="utf-8")
    return manual.importar(resposta, pedido)


def test_so_as_questoes_de_dentro_do_escopo_sao_gravadas(arvore_de_teste, tmp_path):
    """O teste que a §8 pede: a mesma resposta com itens dentro e fora, e só os
    de dentro entram."""
    _gravar(_questao(1), ART_112)
    lote = manual.pedido_de_questoes(quantas=3, escopo=_resolver(
        LEP, "Regimes de cumprimento da pena"))

    resultado = _importar(tmp_path, lote, [
        _item(enunciado="Dentro do escopo: o regime fechado começa em qual?"),
        _item(conteudo=REMICAO, enunciado="Fora: a remição conta como o quê?"),
        _item(conteudo=PENAL, enunciado="Fora: o dolo eventual exige o quê?"),
    ])

    assert resultado["gravadas"] == 1
    assert len(resultado["recusas"]) == 2
    assert all("fora de" in r for r in resultado["recusas"])
    with sessao() as s:
        gravadas = list(s.scalars(select_geradas()))
    assert len(gravadas) == 1
    assert "Dentro do escopo" in gravadas[0].enunciado


def select_geradas():
    from sqlalchemy import select

    return select(QuestaoGerada)


def test_questao_que_nao_declara_o_conteudo_e_recusada(arvore_de_teste, tmp_path):
    _gravar(_questao(1), ART_112)
    lote = manual.pedido_de_questoes(quantas=3, escopo=_resolver(
        LEP, "Regimes de cumprimento da pena"))

    resultado = _importar(tmp_path, lote, [_item(conteudo=None)])

    assert resultado["gravadas"] == 0
    assert "não declarou o conteudo" in resultado["recusas"][0].replace("nao", "não")


def test_com_dispositivo_pedido_o_artigo_citado_tem_de_bater(arvore_de_teste,
                                                             tmp_path):
    lote = manual.pedido_de_questoes(quantas=3, escopo=_resolver(
        LEP, "Regimes de cumprimento da pena", elementos=["LEP, art. 112"]))

    resultado = _importar(tmp_path, lote, [
        _item(conteudo=ART_112, artigo="LEP, art. 112",
              enunciado="Dentro: o art. 112 trata da progressão como?"),
        _item(conteudo=ART_112, artigo="LEP, art. 119",
              enunciado="Fora: o art. 119 fala de que coisa afinal?"),
    ])

    assert resultado["gravadas"] == 1
    assert "nao e nenhum dos pedidos" in resultado["recusas"][0]


def test_o_artigo_bate_escrito_de_outra_forma(arvore_de_teste, tmp_path):
    """"art. 112 da Lei 7.210/1984" e "LEP, art. 112" sao o mesmo artigo."""
    lote = manual.pedido_de_questoes(quantas=3, escopo=_resolver(
        LEP, "Regimes de cumprimento da pena", elementos=["LEP, art. 112"]))

    resultado = _importar(tmp_path, lote, [
        _item(conteudo=ART_112, artigo="art. 112 da Lei 7.210/1984",
              enunciado="Dentro: a progressão de regime exige o quê mesmo?"),
    ])

    assert resultado["gravadas"] == 1, resultado["recusas"]


def test_a_base_e_a_evidencia_ficam_gravadas(arvore_de_teste, tmp_path):
    _gravar(_questao(1), ART_112)
    lote = manual.pedido_de_questoes(quantas=3, escopo=_resolver(
        LEP, "Regimes de cumprimento da pena"))

    _importar(tmp_path, lote, [
        _item(enunciado="Dentro do escopo: o regime semiaberto admite o quê?")])

    with sessao() as s:
        (gravada,) = list(s.scalars(select_geradas()))
    assert gravada.modo_do_pedido == "treino"
    assert gravada.escopo == REGIMES
    assert gravada.conteudo == REGIMES
    assert gravada.base == "questao_real"
    assert gravada.evidencia_da_base == "alvo"


def test_a_variacao_leva_a_materia_e_o_assunto_do_escopo(arvore_de_teste, tmp_path,
                                                         monkeypatch):
    """A base do complementar pode vir de um bloco generico de outra prova
    ("Conhecimentos Especificos"): a gerada fica com a materia e o assunto do
    ESCOPO, e nao com os gravados na questao de base - senao ela some do treino
    da materia no /geradas, que sorteia pela materia."""
    _gravar(_questao(1, CADERNO_COMPLEMENTAR, materia="Conhecimentos Específicos"),
            ART_112)
    monkeypatch.setattr("radar.servico.complementar.provas_aceitas",
                        lambda *a, **k: {CADERNO_COMPLEMENTAR})
    lote = manual.pedido_de_questoes(quantas=3, escopo=_resolver(
        LEP, "Regimes de cumprimento da pena"))

    (pedido,) = lote["pedidos"]
    assert pedido["modo"] == "variacao"
    assert (pedido["materia"], pedido["assunto"]) == (LEP, "Regimes de cumprimento da pena")

    _importar(tmp_path, lote, [
        _item(enunciado="Dentro do escopo: o regime aberto se baseia em quê?")])
    with sessao() as s:
        (gravada,) = list(s.scalars(select_geradas()))
    assert gravada.materia == LEP
    assert gravada.assunto == "Regimes de cumprimento da pena"
    assert gravada.evidencia_da_base == "complementar"


def test_do_zero_fica_marcado_sem_questao_real_de_referencia(arvore_de_teste,
                                                             tmp_path):
    """A §9: quando nao houver questao real, tem de ficar registrado que ela
    NAO tem questao real de referencia."""
    lote = manual.pedido_de_questoes(quantas=3, escopo=_resolver(
        LEP, "Regimes de cumprimento da pena"))

    _importar(tmp_path, lote, [
        _item(enunciado="Sem real embaixo: o regime aberto se cumpre onde?")])

    with sessao() as s:
        (gravada,) = list(s.scalars(select_geradas()))
    assert gravada.modo == "do_zero"
    assert gravada.origem_impressao is None
    assert gravada.evidencia_da_base == "nenhuma"
    assert gravada.base in ("fonte_oficial", "item_do_edital")


def test_vinculo_com_real_que_nao_estava_no_pedido_e_recusado(arvore_de_teste,
                                                              tmp_path):
    """A §9 proibe inventar vinculo com questao real so para preencher o campo.
    O pedido do zero nao tem real nenhuma, e a importacao nao deixa aparecer
    uma."""
    lote = manual.pedido_de_questoes(quantas=3, escopo=_resolver(
        LEP, "Regimes de cumprimento da pena"))
    lote["pedidos"][0]["origem_impressao"] = "imp999"      # nao estava no pedido

    resultado = _importar(tmp_path, lote, [_item()])

    assert resultado["gravadas"] == 0
    assert "vinculo a questao real" in resultado["recusas"][0]


def test_variacao_sem_a_real_de_base_e_recusada(arvore_de_teste, tmp_path):
    _gravar(_questao(1), ART_112)
    lote = manual.pedido_de_questoes(quantas=3, escopo=_resolver(
        LEP, "Regimes de cumprimento da pena"))
    lote["pedidos"][0]["origem_impressao"] = None          # a base desapareceu

    resultado = _importar(tmp_path, lote, [_item()])

    assert resultado["gravadas"] == 0
    assert "sem a questao real de base" in resultado["recusas"][0]


def test_o_pedido_amplo_nao_exige_conteudo_declarado(arvore_de_teste, tmp_path):
    """Pedido sem escopo não fechou escopo nenhum: exigir o nó agora mudaria o
    que eu pedi."""
    _gravar(_questao(1, materia=LEP), None)
    lote = manual.pedido_de_questoes(materia=LEP, quantas=3)

    resultado = _importar(tmp_path, lote, [
        _item(conteudo=None, enunciado="Ampla: qual destas é a regra da LEP?")])

    assert resultado["gravadas"] == 1, resultado["recusas"]


# --- o que ja existia continua -------------------------------------------------

def test_as_geradas_antigas_continuam_listadas_com_os_campos_nulos(
    arvore_de_teste
):
    """As 50 de antes desta etapa nasceram sem escopo, e os campos ficam NULOS:
    preencher diria que elas foram pedidas de um jeito que nao foram."""
    with sessao() as s:
        s.add(QuestaoGerada(
            modo="do_zero", materia=LEP, enunciado="antiga?",
            alternativas={"a": "x", "b": "y"}, resposta="a",
            impressao="antiga", modelo="modelo antigo",
        ))

    with sessao() as s:
        (antiga,) = list(s.scalars(select_geradas()))
    assert antiga.modo_do_pedido is None and antiga.escopo is None
    assert antiga.base is None and antiga.evidencia_da_base is None


def test_o_json_das_geradas_leva_os_campos_novos(arvore_de_teste, tmp_path):
    from radar import acervo

    with sessao() as s:
        s.add(QuestaoGerada(
            modo="variacao", materia=LEP, enunciado="nova?",
            alternativas={"a": "x", "b": "y"}, resposta="a", impressao="nova",
            modelo="teste", modo_do_pedido="treino", escopo=REGIMES,
            conteudo=REGIMES, base="questao_real", evidencia_da_base="alvo",
        ))

    destino = tmp_path / "geradas.json"
    acervo.exportar_geradas(destino)
    (linha,) = json.loads(destino.read_text(encoding="utf-8"))

    assert linha["modo_do_pedido"] == "treino"
    assert linha["escopo"] == REGIMES
    assert linha["base"] == "questao_real"
    assert linha["evidencia_da_base"] == "alvo"


def test_o_simulado_continua_amplo_mesmo_com_a_materia_escolhida(arvore_de_teste):
    """A §7 manda preservar a consulta ampla, e a §8 chama isso de simulado:
    com so a materia, o plano vai pela coluna `materia` e nao pela
    classificacao - restringir aos ja classificados o deixaria menor do que e.
    """
    _gravar(_questao(1, materia=LEP), None)        # real SEM classificacao

    plano = geradas.preparar(materia=LEP, quantas=3, semente=1)

    assert plano["modo_do_pedido"] == "simulado"
    assert plano["escopo"] is None
    assert plano["base_disponivel"] == 1           # a nao classificada entrou


def test_o_modo_simulado_explicito_ignora_o_escopo_da_materia(arvore_de_teste):
    _gravar(_questao(1, materia=LEP), None)

    plano = geradas.preparar(quantas=3, escopo=_resolver(LEP),
                             modo="simulado", semente=1)

    assert plano["escopo"] is None and plano["base_disponivel"] == 1


# --- a tela usa o mesmo filtro --------------------------------------------------

def test_a_tela_oferece_o_assunto_da_materia_escolhida(arvore_de_teste):
    from fastapi.testclient import TestClient

    from radar.web.app import app

    # A tela so mostra o formulario quando ha questao real para variar: e o
    # comportamento de antes desta etapa.
    _gravar(_questao(1), ART_112)
    texto = TestClient(app).get(f"/geradas?materia={LEP}").text

    assert 'name="assunto"' in texto
    assert "Regimes de cumprimento da pena" in texto
    # Sem assunto, a tela diz que e amplo - e nao treino especifico.
    assert "abrangência ampla" in texto


def test_a_tela_com_assunto_escreve_o_escopo_e_o_modo(arvore_de_teste):
    from fastapi.testclient import TestClient

    from radar.web.app import app

    _gravar(_questao(1), ART_112)
    texto = TestClient(app).get(
        f"/geradas?materia={LEP}&assunto=Regimes de cumprimento da pena").text

    assert "Modo <b>treino</b>" in texto
    assert "escopo fechado em" in texto
    assert "concurso-alvo" in texto


def test_a_tela_recusa_nome_que_nao_existe_sem_gerar(arvore_de_teste):
    from fastapi.testclient import TestClient

    from radar.web.app import app

    _gravar(_questao(1), ART_112)
    texto = TestClient(app).get(f"/geradas?materia={LEP}&assunto=xilofone").text

    assert "Não gerei nada" in texto
    assert "não alargo o escopo sozinho" in texto


# --- o arquivo versionado das geradas -------------------------------------------

def test_o_json_real_das_geradas_nao_esta_vazio():
    """O registro VERSIONADO das 50 geradas tem de existir.

    Este teste nasceu de um defeito achado na Etapa 5: o commit da Etapa 2
    gravou `data/questoes_geradas.json` como `[]` enquanto o banco tinha as 50
    (o export rodou contra um banco temporario). O banco e reconstruivel A
    PARTIR do arquivo, entao um arquivo vazio significa perder as 50 na
    proxima reconstrucao - e o §23 e explicito: nenhum dado antigo pode ter
    sido perdido.

    Ele le o arquivo do repositorio de proposito, e nao um tmp_path: o que ele
    guarda e o conteudo versionado, nao o comportamento da funcao.
    """
    from pathlib import Path

    arquivo = (Path(__file__).resolve().parent.parent / "data"
               / "questoes_geradas.json")
    linhas = json.loads(arquivo.read_text(encoding="utf-8"))

    assert linhas, "o registro versionado das questoes geradas esta vazio"
    assert all(linha.get("impressao") for linha in linhas)
    # Toda gerada tem procedencia: e a trava que existe desde o `gravar`.
    assert all(linha.get("modelo") for linha in linhas)


def test_toda_variacao_do_registro_tem_a_base_pela_chave_menos_as_3_de_27_09():
    """As 30 variacoes do estoque de 03/10 que tinham ficado sem a questao de
    base (decisao 77) foram religadas pelo historico da conversa, que imprimiu
    a base de cada pedido. So as 3 de 27/09 seguem sem: delas nao ha registro."""
    from pathlib import Path

    arquivo = (Path(__file__).resolve().parent.parent / "data"
               / "questoes_geradas.json")
    linhas = json.loads(arquivo.read_text(encoding="utf-8"))
    sem_base = [linha for linha in linhas
                if linha.get("modo") == "variacao" and not linha.get("origem_chave")]

    assert len(sem_base) == 3
    assert all("27/09/2026" in (linha.get("modelo") or "") for linha in sem_base)
