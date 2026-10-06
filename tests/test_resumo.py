"""O resumo de cada tema (R2, 05/10/2026).

O que estes testes seguram: cada frase do resumo tem fonte; questao citada e
do tema e com o gabarito oficial; "como a banca cobra" so com questao real (ou
a frase exata); o basico so quando o tema nao caiu; nada de previsao; a
procedencia diz o modelo; o resumo conferido nao e sobrescrito; e o botao
"Resumo" abre uma janela so com HTML e CSS, na Noite ja em "como a banca
cobra", e a lista nas faixas de varios temas.
"""
import json
import re
from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from radar import fichas
from radar.origem import FRASE_SEM_EVIDENCIA
from radar.servico import cronograma as diario
from radar.servico import fichas as servico_fichas
from radar.servico import manual
from radar.web.app import app

PENAL = "Direito Penal"
TEMA = "Fato típico e nexo causal (art. 13)"
INFRACAO = f"{PENAL} > Infração penal: elementos, espécies"


def _f(texto, *fontes):
    return {"texto": texto, "fontes": list(fontes)}


CODIGOS = {"2019-q53": "c", "FEPESE-2024-q8": "d"}
BOM = {
    "dominar": [_f("A relação de causalidade pela equivalência dos antecedentes.", "CP, art. 13, caput")],
    "artigos": [_f("Art. 13, § 2º: quem devia e podia agir responde pelo resultado.", "CP, art. 13, § 2º")],
    "como_cobra": [_f("Cobrou a letra da lei, com a alternativa certa copiada.", "2019-q53 (gabarito C)"),
                   _f("Em outro concurso da FEPESE, a mesma letra.", "FEPESE-2024-q8")],
    "pegadinhas": [_f("Trocar 'devia e podia' por 'devia ou podia'.", "2019-q53"),
                   _f("Confundir omissivo próprio e impróprio.", fichas.SEM_QUESTAO_REAL)],
}


def _conferir(partes=None, **mudar):
    regras = dict(codigos=CODIGOS, caiu=True, exige_artigo=True)
    regras.update(mudar)
    return fichas.conferir_resumo({"partes": partes if partes is not None else BOM}, **regras)


def test_o_resumo_certo_passa_com_cada_frase_e_a_fonte():
    partes = _conferir()
    assert list(partes) == ["dominar", "artigos", "como_cobra", "pegadinhas"]
    assert partes["como_cobra"][0]["fontes"] == ["2019-q53 (gabarito C)"]


@pytest.mark.parametrize("mudar, motivo", [
    ({"dominar": [_f("Uma frase sem a fonte dela.")]}, "sem fonte"),
    ({"pegadinhas": [_f("Pegadinha de questão de outro tema.", "2013-q99")]}, "não é deste tema"),
    ({"como_cobra": [_f("Cobrou a letra, com o gabarito errado.", "2019-q53 (gabarito A)")]},
     "gabarito oficial"),
    ({"como_cobra": [_f("A banca cobra muito a letra da lei.", "CP, art. 13")]},
     "sem a questão real"),
    ({"pegadinhas": [_f("Uma confusão sem questão e sem a marca.", "CP, art. 13")]},
     "cite a questão real"),
    ({"artigos": [_f("O dever de agir do garantidor.", "doutrina")]}, "sem o dispositivo"),
    ({"dominar": [_f("Isto certamente vai cair na prova.", "CP, art. 13")]}, "previsão"),
    ({"basico": [_f("O básico do tema que caiu.", "CP, art. 13")]}, "só para o que não caiu"),
    ({"extra": [_f("Uma parte que não existe.", "x")]}, "parte que o resumo não tem"),
])
def test_o_resumo_e_recusado(mudar, motivo):
    with pytest.raises(fichas.FichaRecusada, match=motivo):
        _conferir({**BOM, **mudar})


def test_sem_questao_real_como_cobra_e_a_frase_exata_e_o_basico_e_obrigatorio():
    sem = {**BOM, "como_cobra": [_f(FRASE_SEM_EVIDENCIA, "acervo")],
           "pegadinhas": [_f("Confundir omissivo próprio e impróprio.", fichas.SEM_QUESTAO_REAL)]}
    with pytest.raises(fichas.FichaRecusada, match="o básico é isto"):
        _conferir(sem, codigos={}, caiu=False, basico_obrigatorio=True)
    partes = _conferir({**sem, "basico": [_f("Leia o art. 13 e o § 2º.", "CP, art. 13")]},
                       codigos={}, caiu=False, basico_obrigatorio=True)
    assert partes["como_cobra"][0]["texto"] == FRASE_SEM_EVIDENCIA
    with pytest.raises(fichas.FichaRecusada, match="frase de evidência insuficiente"):
        _conferir({**sem, "como_cobra": [_f("A banca gosta da letra da lei.", "acervo")]},
                  codigos={}, caiu=False, basico_obrigatorio=False)
    # Sem base para afirmar (uma prova so, ou sem contagem), o basico e opcional.
    assert "basico" not in _conferir(sem, codigos={}, caiu=False, basico_obrigatorio=False)


def test_o_paragrafo_sozinho_e_regra_de_mandela_contam_como_dispositivo():
    for fonte in ("Declaração de Viena (1993), § 5", "Regras de Mandela, regra 12.1",
                  "Súmula Vinculante 11"):
        partes = _conferir({**BOM, "artigos": [_f("Um dispositivo citado pela fonte.", fonte)]})
        assert partes["artigos"][0]["fontes"] == [fonte]


def test_portugues_nao_exige_artigo_mas_exige_a_fonte():
    partes = _conferir({**BOM, "artigos": [_f("VTD + SE com sujeito no plural vai ao plural.",
                                              "regra de concordância - Pestana")]},
                       exige_artigo=False)
    assert partes["artigos"][0]["fontes"] == ["regra de concordância - Pestana"]


def test_a_procedencia_diz_o_modelo_que_a_resposta_declara():
    quando = datetime(2026, 10, 5, 15, 0, tzinfo=timezone.utc)
    assert manual.procedencia(quando) == "Claude Code, importado manualmente, em 05/10/2026"
    assert manual.procedencia(quando, "claude-opus-5-5") == (
        "Claude Code (claude-opus-5-5), importado manualmente, em 05/10/2026")
    # Texto que nao e nome de modelo nao entra.
    assert manual.procedencia(quando, "<script>") == (
        "Claude Code, importado manualmente, em 05/10/2026")


# --- a importacao, no banco de teste ---------------------------------------------

def _ficha_gravada(resumo=None):
    escrita = fichas.FichaEscrita(tema=TEMA, materia=PENAL, nos=[INFRACAO],
                                  modelo="Claude Code, de teste",
                                  criado_em="2026-10-02T12:00:00+00:00", resumo=resumo)
    servico_fichas.gravar([escrita])
    return escrita


PEDIDO = [{"id": "r1", "tema": TEMA, "materia": PENAL, "ficha": fichas.id_do_tema(TEMA),
           "codigos": CODIGOS, "caiu": True, "basico_obrigatorio": False,
           "exige_artigo": True}]


def test_importar_grava_o_resumo_dentro_da_ficha(banco_temporario):
    _ficha_gravada()
    resultado = servico_fichas.importar_resumos(
        PEDIDO, [{"id": "r1", "resumo": BOM}],
        "Claude Code (claude-opus-5-5), importado manualmente, em 05/10/2026")
    assert resultado["gravadas"] == 1 and not resultado["recusas"]
    (gravada,) = servico_fichas.carregar()
    assert gravada.resumo["modelo"].startswith("Claude Code (claude-opus-5-5)")
    assert gravada.resumo["conferido_em"] is None
    assert gravada.resumo["partes"]["artigos"][0]["fontes"] == ["CP, art. 13, § 2º"]


def test_o_resumo_conferido_nao_e_sobrescrito_e_a_ficha_sem_resumo_nao_ganha_a_chave(
        banco_temporario, tmp_path):
    _ficha_gravada()
    bruto = json.loads((tmp_path / "fichas.json").read_text(encoding="utf-8"))
    assert "resumo" not in bruto[0]
    servico_fichas.importar_resumos(PEDIDO, [{"id": "r1", "resumo": BOM}], "m")
    servico_fichas.conferir_resumo(TEMA, date(2026, 10, 6))
    de_novo = servico_fichas.importar_resumos(PEDIDO, [{"id": "r1", "resumo": BOM}], "m")
    assert de_novo["gravadas"] == 0 and "já conferiu este resumo" in de_novo["recusas"][0]


def test_o_importar_do_manual_reconhece_o_lote_de_resumos(banco_temporario, tmp_path):
    _ficha_gravada()
    lote = manual._novo_lote("resumos", PEDIDO)
    pedido = tmp_path / "pedido_ia.json"
    pedido.write_text(json.dumps(lote, ensure_ascii=False), encoding="utf-8")
    resposta = tmp_path / "resposta_ia.json"
    resposta.write_text(json.dumps({"lote": lote["lote"], "modelo": "claude-opus-5-5",
                                    "respostas": [{"id": "r1", "resumo": BOM}]},
                                   ensure_ascii=False), encoding="utf-8")
    resultado = manual.importar(resposta, pedido)
    assert resultado["tipo"] == "resumos" and resultado["gravadas"] == 1
    assert "(claude-opus-5-5)" in resultado["modelo"]


# --- o que cada faixa abre ------------------------------------------------------

def _faixa(tipo, titulo="", materia=None, **mais):
    base = dict(tipo=tipo, titulo=titulo, materia=materia, desligada=False, origem=None,
                materias_da_rodada=())
    base.update(mais)
    return SimpleNamespace(**base)


def test_cada_faixa_abre_o_seu_tema_ou_a_lista(banco_temporario):
    from radar import cronograma

    plano = cronograma.carregar()   # o real: o tema do art. 13 e de 05/10
    escrita = _ficha_gravada()
    teoria = _faixa("teoria", TEMA, PENAL)
    lei_seca = _faixa("lei_seca", "Lei seca dirigida: CP art. 13", PENAL)
    pausa = _faixa("pausa", "Pausa")
    bonus = _faixa("bonus", "Bônus: lógica proposicional", "Raciocínio Lógico")
    correcao = _faixa("correcao", "Correção")
    blocos = [SimpleNamespace(chave="manha", faixas=[teoria, pausa, lei_seca]),
              SimpleNamespace(chave="noite", faixas=[correcao]),
              SimpleNamespace(chave="pos22", faixas=[bonus])]
    r = servico_fichas.resumos_do_dia(blocos, date(2026, 10, 5), plano, [escrita], [], [])
    tema = "resumo-" + escrita.id
    assert r.por_faixa[("manha", 0)] == [tema]
    assert r.por_faixa[("manha", 2)] == [tema]            # a lei seca leva o da teoria
    assert ("manha", 1) not in r.por_faixa               # a pausa nao tem botao
    assert r.por_faixa[("noite", 0)] == [tema]            # a correcao: os temas do dia
    (sem,) = r.da_faixa("pos22", 0)
    assert not sem.tem_ficha and not sem.escrito


def test_a_revisao_semanal_abre_a_lista_dos_temas_da_semana(banco_temporario):
    from radar import cronograma

    plano = cronograma.carregar()
    escritas = [fichas.FichaEscrita(tema=t, materia=m, modelo="m", criado_em="x")
                for t, m in ((TEMA, PENAL), ("Vozes do verbo", "Língua Portuguesa"),
                             ("Aplicação da lei penal (arts. 1º a 12)", PENAL))]
    semanal = _faixa("revisao_semanal", "Revisão semanal")
    r = servico_fichas.resumos_do_dia([SimpleNamespace(chave="manha", faixas=[semanal])],
                                      date(2026, 10, 10), plano, escritas, [], [])
    temas = [x.tema for x in r.da_faixa("manha", 0)]
    # A semana de 05/10 a 10/10: o art. 13 e Vozes do verbo, e nao o de 28/09.
    assert TEMA in temas and "Vozes do verbo" in temas
    assert "Aplicação da lei penal (arts. 1º a 12)" not in temas


# --- a tela ---------------------------------------------------------------------

@pytest.fixture
def com_resumo(banco_temporario, monkeypatch):
    monkeypatch.setattr(diario, "hoje_local", lambda: date(2026, 10, 5))
    _ficha_gravada({"partes": {**BOM}, "modelo": "Claude Code (claude-opus-5-5), em teste",
                    "criado_em": "2026-10-05T12:00:00+00:00", "conferido_em": None})


def test_o_botao_abre_a_janela_so_com_css_e_na_noite_em_como_cobra(com_resumo):
    html = TestClient(app).get("/hoje?data=2026-10-05").text
    ident = "resumo-" + fichas.id_do_tema(TEMA)
    assert f'href="#{ident}"' in html                 # de manha
    assert f'href="#{ident}-cobra"' in html           # a noite, em como a banca cobra
    assert f'<div class="ds-janela" id="{ident}"' in html
    assert f'<section id="{ident}-cobra">' in html
    assert "Claude Code (claude-opus-5-5), em teste" in html
    assert "Fonte: CP, art. 13, § 2º" in html
    # O bonus (sem ficha) diz que o resumo nao foi escrito.
    assert "Resumo ainda não escrito para este tema." in html
    # Nenhum JavaScript novo: so os dois de sempre, o cronometro e a dobra.
    assert sorted(re.findall(r'<script[^>]*src="([^"]+)"', html)) == [
        "/estatico/cronometro.js", "/estatico/dobra.js"]


def test_a_ficha_mostra_o_resumo_e_confere(com_resumo):
    cliente = TestClient(app)
    ident = fichas.id_do_tema(TEMA)
    html = cliente.get(f"/fichas/{ident}?data=2026-10-05").text
    assert "Conferi este resumo" in html and "Como a banca cobra" in html
    volta = cliente.post(f"/fichas/{ident}/resumo/conferir", data={"data": "2026-10-05"},
                         follow_redirects=False)
    assert volta.status_code == 303
    assert servico_fichas.carregar()[0].resumo["conferido_em"]


# --- o pedido: o resumo e a explicacao dos exemplos reais ------------------------

@pytest.fixture
def vozes_no_banco(banco_temporario):
    """Uma questao do alvo (2013-q7) classificada no no de Vozes do verbo, o
    no na arvore e a ficha do tema - que o cronograma real tem em 05/10."""
    from radar.db import sessao
    from radar.models import Classificacao, Conteudo, QuestaoDeProva
    from radar.questoes import chave_da_questao

    lp, vozes = "Língua Portuguesa", "Língua Portuguesa > Vozes do verbo"
    alternativas = {l: f"alternativa {l} da questão de vozes" for l in "abcde"}
    enunciado = "Assinale a frase que transpõe a passiva analítica para a sintética."
    with sessao() as s:
        s.add(Conteudo(caminho=lp, pai=None, nivel="materia", nome=lp, origem="edital",
                       procedencia="teste"))
        s.add(Conteudo(caminho=vozes, pai=lp, nivel="assunto", nome="Vozes do verbo",
                       origem="edital", procedencia="teste"))
        s.add(QuestaoDeProva(prova_url="ap2013", ano=2013, numero=7, materia=lp,
                             enunciado=enunciado, alternativas=alternativas, resposta="c",
                             impressao="imp-q7", evidencia="alvo"))
        s.add(Classificacao(chave=chave_da_questao(enunciado, alternativas), conteudo=vozes,
                            principal=True, status="completa", procedencia="teste",
                            pegadinha="'Soltou-se os presos' erra a concordância"))
    servico_fichas.gravar([fichas.FichaEscrita(
        tema="Vozes do verbo", materia=lp, nos=[vozes], modelo="m", criado_em="x",
        ler_exatamente="O capítulo de vozes verbais.")])


def test_o_pedido_de_resumo_leva_a_questao_inteira_e_os_codigos(vozes_no_banco):
    lote = manual.pedido_de_resumos(["vozes-do-verbo"])
    (p,) = lote["pedidos"]
    assert lote["tipo"] == "resumos" and p["ficha"] == "vozes-do-verbo"
    assert p["codigos"] == {"2013-q7": "c"} and p["caiu"] is True
    assert p["exige_artigo"] is False
    assert "2013-q7 · gabarito oficial: C" in p["pedido"]
    assert "(a) alternativa a da questão de vozes" in p["pedido"]
    assert "O TEMA CAIU" in p["pedido"]
    # Pedido de novo: o tema que ja tem resumo nao volta, sem --refazer.
    servico_fichas.importar_resumos(lote["pedidos"], [{"id": p["id"], "resumo": {
        "dominar": [_f("Passiva sintética: VTD + se.", "regra - Pestana")],
        "artigos": [_f("VTD + se + sujeito plural = plural.", "regra - Pestana")],
        "como_cobra": [_f("Pediu a transposição para a sintética.", "2013-q7 (gabarito C)")],
        "pegadinhas": [_f("'Soltou-se os presos' está errado.", "2013-q7")]}}], "m")
    assert manual.pedido_de_resumos(["vozes-do-verbo"])["pedidos"] == []
    assert len(manual.pedido_de_resumos(["vozes-do-verbo"], refazer=True)["pedidos"]) == 1


def test_o_pedido_de_explicacao_vai_pelas_questoes_reais_dos_temas(vozes_no_banco):
    lote = manual.pedido_de_explicacoes_dos_temas()
    (p,) = lote["pedidos"]
    assert lote["tipo"] == "explicacoes"
    assert (p["codigo"], p["gabarito"], p["impressao"]) == ("2013-q7", "c", "imp-q7")
    assert p["temas"] == ["Vozes do verbo"]
    assert "Eu errei" not in p["instrucao"] and "onde estava a pegadinha" in p["instrucao"]


def test_a_fonte_por_paragrafo_serve_e_o_texto_solto_nao():
    """A Declaracao de Viena e numerada por paragrafo: "§ 5" cita (chamar de
    "art. 5º" seria citar errado). Doutrina solta continua recusada."""
    dh = "Direitos Humanos"
    assert manual.fonte_serve("§ 5 da Declaração e Programa de Ação de Viena (1993)", dh)
    assert manual.fonte_serve("Regras de Mandela, regra 12.1", dh)
    assert not manual.fonte_serve("doutrina (gerações de direitos)", dh)


def test_o_pedido_de_explicacao_do_complementar_vai_pelas_citadas_nos_resumos(vozes_no_banco):
    """Item 5 (06/10/2026): a questao de outra prova da FEPESE que o resumo
    cita ganha pedido de explicacao; a do mesmo no que ele nao cita, nao."""
    from radar.db import sessao
    from radar.models import Classificacao, QuestaoDeProva
    from radar.questoes import chave_da_questao

    from tests.test_treino_do_alvo import _aceitar

    vozes = "Língua Portuguesa > Vozes do verbo"
    questoes = []
    with sessao() as s:
        for numero, resposta in ((3, "b"), (4, "d")):
            alternativas = {l: f"alternativa {l} da questão {numero}" for l in "abcde"}
            enunciado = f"Questão {numero} de vozes de outra prova da FEPESE."
            q = QuestaoDeProva(prova_url="outra2024", ano=2024, numero=numero, banca="FEPESE",
                               materia="Língua Portuguesa", enunciado=enunciado,
                               alternativas=alternativas, resposta=resposta,
                               impressao=f"imp-c{numero}", evidencia="complementar")
            s.add(q)
            s.add(Classificacao(chave=chave_da_questao(enunciado, alternativas), conteudo=vozes,
                                principal=True, status="completa", procedencia="teste"))
            questoes.append(q)
    _aceitar(questoes)
    escritas = servico_fichas.carregar()
    escritas[0].resumo = {"partes": {"como_cobra": [_f(
        "Outra prova pediu a passiva sintética.", "FEPESE-2024-q3 (gabarito B)")]},
        "modelo": "m", "criado_em": "x", "conferido_em": None}
    servico_fichas.gravar(escritas)

    lote = manual.pedido_de_explicacoes_dos_resumos()

    (p,) = lote["pedidos"]
    assert (p["codigo"], p["gabarito"], p["impressao"]) == ("FEPESE-2024-q3", "b", "imp-c3")
    assert p["instrucao"] == manual.INSTRUCAO_EXPLICACAO_DO_COMPLEMENTAR
    assert "OUTRA prova da FEPESE" in p["instrucao"] and "meu cargo" not in p["instrucao"]
    assert "alternativa e da questão 3" in p["pedido"]          # inteira, sem corte
