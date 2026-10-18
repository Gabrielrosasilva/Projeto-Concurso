"""A tela da amostra das provas novas (decisao 173).

O que estes testes seguram:

  * a regra de cada grupo: as 10 primeiras sem erro passam, 2 erros voltam, 1
    erro pede as 10 seguintes; o ajuste no mesmo ramo nao conta como erro;
  * a amostra e sempre a mesma (o hash da chave), uma por questao, e pula a
    questao guardada para uma rodada que mede, dizendo quantas;
  * os tamanhos moram no config/amostra.yml;
  * na tela, a letra so aparece na questao que eu ja respondi no radar, e o
    "Responder no radar" abre so aquela questao - menos a guardada;
  * as outras bancas sao um recorte proprio, com a banca, o ano e o cargo.
"""
import json
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from radar import amostra as regua
from radar import edital_programa
from radar.db import sessao
from radar.models import QuestaoDeProva, RespostaDeSimulado, Simulado
from radar.servico import classificacoes, conferencia_do_lote, conteudos
from radar.servico.conferencia_do_lote import (AJUSTE, CONFIRA_MAIS, CONFIRMADA, EM_ANDAMENTO,
                                               ERRO, PASSA, VOLTA, ItemDoLote, Lote)

FIXTURES = Path(__file__).parent / "fixtures"
PROGRAMA = edital_programa.ler_programa(
    (FIXTURES / "provas" / "edital_sap_2019_programa.txt").read_text(encoding="utf-8"))

ASSUNTO = "Direito Penal > Imputabilidade penal"
SUBASSUNTO = ASSUNTO + " > Menoridade"
ARTIGO = SUBASSUNTO + " > CP, art. 27"
OUTRO_ASSUNTO = "Direito Penal > Crimes contra a Administração Pública"
QUANDO = datetime(2026, 10, 17, 12, 0)


# --- a regra, sem banco ------------------------------------------------------------

def _minha(conteudo, status="completa"):
    """Uma principal que eu conferi."""
    return SimpleNamespace(conteudo=conteudo, status=status, conferida_em=QUANDO,
                           conferida_por=None)


@pytest.mark.parametrize("no_conferido, principal, esperado", [
    (SUBASSUNTO, None, None),
    # A marca da segunda leitura nao e conferencia minha.
    (SUBASSUNTO, SimpleNamespace(conteudo=SUBASSUNTO, status="parcial", conferida_em=QUANDO,
                                 conferida_por=classificacoes.REANALISE), None),
    (SUBASSUNTO, _minha(SUBASSUNTO), CONFIRMADA),
    # Descer no mesmo ramo e ajuste: do subassunto para o artigo, do assunto
    # para o subassunto.
    (SUBASSUNTO, _minha(ARTIGO), AJUSTE),
    (ASSUNTO, _minha(SUBASSUNTO), AJUSTE),
    # Subir sem sair do subassunto tambem; subir para o assunto muda a faixa.
    (ARTIGO, _minha(SUBASSUNTO), AJUSTE),
    (SUBASSUNTO, _minha(ASSUNTO), ERRO),
    (SUBASSUNTO, _minha(OUTRO_ASSUNTO), ERRO),
    # A classificada que eu deixo pendente, e o contrario.
    (SUBASSUNTO, _minha("Direito Penal", status="pendente"), ERRO),
    (None, _minha(SUBASSUNTO), ERRO),
    (None, _minha("Direito Penal", status="pendente"), CONFIRMADA),
])
def test_o_tipo_de_cada_conferencia(no_conferido, principal, esperado):
    assert conferencia_do_lote.tipo_da_conferencia(no_conferido, principal) == esperado


def test_a_regra_do_grupo():
    ok, x = CONFIRMADA, ERRO
    regra = conferencia_do_lote.resultado_do_grupo
    assert regra([ok] * 10, 10, 10).estado == PASSA
    assert regra([ok] * 9 + [None], 10, 10).estado == EM_ANDAMENTO
    # Dois erros ja decidem, mesmo antes de conferir as 10.
    assert regra([x, x] + [None] * 8, 10, 10).estado == VOLTA
    # Um erro: as 10 seguintes decidem.
    assert regra([x] + [ok] * 9 + [None] * 10, 10, 10).estado == CONFIRA_MAIS
    assert regra([x] + [ok] * 9 + [ok] * 10, 10, 10).estado == PASSA
    assert regra([x] + [ok] * 9 + [ok] * 3 + [x] + [None] * 6, 10, 10).estado == VOLTA
    # O ajuste nao conta como erro.
    assert regra([AJUSTE] * 2 + [ok] * 8, 10, 10).estado == PASSA


def _lote(*itens):
    return Lote(id="t", nome="Lote de teste", grupos=["G"], itens=list(itens))


def test_a_amostra_e_sempre_a_mesma_uma_por_questao_e_pula_a_guardada():
    itens = [ItemDoLote(chave=f"k{n}", grupo="G", categoria="a", no_conferido=SUBASSUNTO)
             for n in range(8)]
    itens.append(ItemDoLote(chave="pendente", grupo="G", categoria="pendente nas duas"))
    # A regra c espera a minha conferencia uma a uma: nao entra na amostra.
    itens.append(ItemDoLote(chave="discordam", grupo="G", categoria="c"))
    ordem = sorted([i.chave for i in itens if i.categoria != "c"],
                   key=conferencia_do_lote.por_hash)
    guardada, repetida = ordem[1], ordem[3]
    mesma_de = {repetida: ordem[2]}         # a mesma questao em outro caderno

    (grupo,) = conferencia_do_lote.amostra(_lote(*itens), {}, {guardada}, mesma_de,
                                           primeiras=3, mais=2)

    esperadas = [k for k in ordem if k not in (guardada, repetida)]
    assert grupo.chaves == esperadas[:3]
    assert (grupo.fora_por_reserva, grupo.conferidas_pelo_claude_code) == (1, 9)
    assert grupo.resultado.estado == EM_ANDAMENTO
    # De novo, a mesma amostra.
    (outra_vez,) = conferencia_do_lote.amostra(_lote(*reversed(itens)), {}, {guardada},
                                               mesma_de, primeiras=3, mais=2)
    assert outra_vez.chaves == grupo.chaves


def test_um_erro_abre_as_seguintes():
    itens = [ItemDoLote(chave=f"k{n}", grupo="G", categoria="a", no_conferido=SUBASSUNTO)
             for n in range(8)]
    ordem = sorted((i.chave for i in itens), key=conferencia_do_lote.por_hash)
    principais = {k: _minha(SUBASSUNTO) for k in ordem[:3]}
    principais[ordem[0]] = _minha(OUTRO_ASSUNTO)

    (grupo,) = conferencia_do_lote.amostra(_lote(*itens), principais, set(),
                                           primeiras=3, mais=2)

    assert grupo.resultado.estado == CONFIRA_MAIS
    assert grupo.chaves == ordem[:5]
    assert (grupo.conferidas, grupo.erros, grupo.ajustes) == (3, 1, 0)


def test_os_tamanhos_moram_no_config(tmp_path):
    reais = regua.carregar()
    assert (reais.amostra_do_lote, reais.amostra_do_lote_extra) == (10, 10)
    arquivo = tmp_path / "amostra.yml"
    arquivo.write_text("acervo:\n  amostra_do_lote: 5\n  amostra_do_lote_extra: 3\n",
                       encoding="utf-8")
    minimos = regua.carregar(arquivo)
    assert (minimos.amostra_do_lote, minimos.amostra_do_lote_extra) == (5, 3)


# --- a tela, com banco ---------------------------------------------------------------

def _questao(numero, banca, evidencia, ano=2022, cargo="Policial Penal"):
    return QuestaoDeProva(
        prova_url=f"https://{banca.lower()}.test/{ano}.pdf", banca=banca, ano=ano,
        numero=numero, materia="Direito Penal", cargo=cargo,
        enunciado=f"Questão {numero} da {banca} sobre a menoridade?",
        alternativas={l: f"{l}{numero}" for l in "abcd"}, resposta="c",
        impressao=f"{banca}-{numero}", evidencia=evidencia)


def _k(banca, numero):
    with sessao() as s:
        q = s.scalar(select(QuestaoDeProva).where(QuestaoDeProva.impressao == f"{banca}-{numero}"))
    return classificacoes.chave_de(q)


@pytest.fixture
def provas_novas(banco_temporario, tmp_path, monkeypatch):
    """Tres questoes de outra banca no lote - duas conferidas pela segunda
    leitura, uma pendente da regra c - e uma do alvo, fora dele."""
    conteudos.semear(programa=PROGRAMA)
    conteudos.garantir(ASSUNTO, "Menoridade")
    with sessao() as s:
        for numero in (1, 2, 3):
            s.add(_questao(numero, "Cebraspe", "fora"))
        s.add(_questao(9, "FEPESE", "alvo", ano=2019, cargo="Agente Penitenciário"))
    for numero in (1, 2):
        classificacoes.classificar(_k("Cebraspe", numero), SUBASSUNTO, "Claude Code (teste)",
                                   conferida_em=QUANDO, conferida_por=classificacoes.REANALISE,
                                   pegadinha="a idade da pegadinha")
    classificacoes.classificar(_k("Cebraspe", 3), "Direito Penal", "Claude Code (teste)",
                               status="pendente")
    classificacoes.classificar(_k("FEPESE", 9), SUBASSUNTO, "Claude Code (teste)")
    itens = [{"chave": _k("Cebraspe", n), "grupo": "Cebraspe", "categoria": "a",
              "no_conferido": SUBASSUNTO} for n in (1, 2)]
    itens.append({"chave": _k("Cebraspe", 3), "grupo": "Cebraspe", "categoria": "c",
                  "primeira": SUBASSUNTO, "segunda": OUTRO_ASSUNTO, "confianca": "media"})
    (tmp_path / "lotes_de_classificacao.json").write_text(json.dumps({"lotes": [{
        "id": conferencia_do_lote.LOTE_DE_17_10, "nome": "As provas novas de 17/10",
        "grupos": ["FEPESE", "Cebraspe"], "itens": itens}]}), encoding="utf-8")
    guardadas = set()
    monkeypatch.setattr(conferencia_do_lote, "reservadas", lambda hoje=None: guardadas)
    return guardadas


def test_o_lote_mostra_a_amostra_e_as_pendentes(provas_novas):
    tela = classificacoes.conferencia(evidencia_escolhida="lote")
    assert tela.lote == "As provas novas de 17/10"
    assert sorted(i.chave for i in tela.itens) == sorted(_k("Cebraspe", n) for n in (1, 2))
    fepese, cebraspe = tela.grupos
    assert (fepese.conferidas_pelo_claude_code, cebraspe.conferidas_pelo_claude_code) == (0, 2)
    # A marca da segunda leitura nao conta como conferida por mim.
    assert tela.conferidas == 0 and not any(i.conferida for i in tela.itens)

    pendentes = classificacoes.conferencia(evidencia_escolhida="lote", parte="pendentes")
    (item,) = pendentes.itens
    assert item.do_lote.segunda == OUTRO_ASSUNTO
    # Corrigir pode ir para a materia das duas leituras.
    assert OUTRO_ASSUNTO in item.opcoes

    classificacoes.conferir(_k("Cebraspe", 3), corrigir_para=OUTRO_ASSUNTO)
    assert classificacoes.conferencia(evidencia_escolhida="lote", parte="pendentes",
                                      so_abertas=True).itens == []


def test_corrigir_na_amostra_conta_o_erro_e_o_ajuste(provas_novas):
    um, dois = _k("Cebraspe", 1), _k("Cebraspe", 2)
    classificacoes.conferir(um, corrigir_para=OUTRO_ASSUNTO)
    conteudos.garantir(SUBASSUNTO, "CP, art. 27", tipo_elemento="artigo")
    classificacoes.conferir(dois, corrigir_para=ARTIGO)

    tela = classificacoes.conferencia(evidencia_escolhida="lote")
    (cebraspe,) = [g for g in tela.grupos if g.grupo == "Cebraspe"]
    assert (cebraspe.conferidas, cebraspe.erros, cebraspe.ajustes) == (2, 1, 1)
    assert {i.chave: i.tipo for i in tela.itens} == {um: ERRO, dois: AJUSTE}


def test_a_guardada_nao_aparece_e_a_tela_diz_quantas(provas_novas):
    provas_novas.add(_k("Cebraspe", 1))
    tela = classificacoes.conferencia(evidencia_escolhida="lote")
    assert [i.chave for i in tela.itens] == [_k("Cebraspe", 2)]
    assert tela.fora_por_reserva == 1
    fora = classificacoes.conferencia(evidencia_escolhida="fora")
    assert _k("Cebraspe", 1) not in [i.chave for i in fora.itens]
    assert fora.fora_por_reserva == 1


def test_a_letra_so_aparece_depois_de_responder_no_radar(provas_novas):
    cliente = TestClient(app_web())
    chave = _k("Cebraspe", 1)
    texto = cliente.get("/analises/conferencia?evidencia=lote").text
    assert "← gabarito" not in texto and "a idade da pegadinha" not in texto
    assert "Responder no radar" in texto

    ida = cliente.post("/analises/conferencia/responder",
                       data={"chave": chave, "evidencia": "lote"}, follow_redirects=False)
    assert ida.status_code == 303 and ida.headers["location"].startswith("/simulado/")
    simulado_id = int(ida.headers["location"].rsplit("/", 1)[1])
    with sessao() as s:
        simulado = s.get(Simulado, simulado_id)
        assert simulado.filtros["rodada"] == conferencia_do_lote.RODADA
        questao_id = s.scalar(select(RespostaDeSimulado.questao_id)
                              .where(RespostaDeSimulado.simulado_id == simulado_id))
    assert "conferência da classificação" in cliente.get(ida.headers["location"]).text
    cliente.post(f"/simulado/{simulado_id}/responder", data={"questao_id": questao_id,
                                                             "letra": "a"})

    depois = cliente.get("/analises/conferencia?evidencia=lote").text
    assert depois.count("← gabarito") == 1 and "a idade da pegadinha" in depois


def test_a_guardada_nao_abre_no_responder(provas_novas):
    chave = _k("Cebraspe", 1)
    provas_novas.add(chave)
    cliente = TestClient(app_web())
    resposta = cliente.post("/analises/conferencia/responder",
                            data={"chave": chave, "evidencia": "lote"}, follow_redirects=False)
    assert resposta.status_code == 303
    assert "aviso=" in resposta.headers["location"]
    with sessao() as s:
        assert s.scalars(select(Simulado)).first() is None


def test_outras_bancas_e_um_recorte_proprio(provas_novas):
    fora = classificacoes.conferencia(evidencia_escolhida="fora")
    assert {i.codigo for i in fora.itens} == {f"Cebraspe 2022 · Policial Penal · q{n}"
                                              for n in (1, 2, 3)}
    assert "FEPESE" not in {i.codigo.split()[0] for i in fora.itens}
    alvo = classificacoes.conferencia()
    assert [i.codigo for i in alvo.itens] == ["2019-q9"]


def app_web():
    from radar.web.app import app
    return app
