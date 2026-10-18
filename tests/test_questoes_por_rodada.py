"""O caderno de outra banca lido pela rodada de alternativas (decisao 172):
FGV, Access, Idecan e a Selecon nova.

O texto dos testes e INVENTADO, no formato de cada banca: os termos da FGV
proibem reproduzir o material, e o repositorio e publico.
"""
from pathlib import Path

import pytest

from radar import questoes_por_rodada as qp


def _pagina(cabecalho: list[str], corpo: str, rodape: list[str] = ()) -> str:
    return "\n".join([*cabecalho, corpo, *rodape])


def test_fgv_o_numero_sozinho_e_a_marca_e_o_titulo_nao_gruda():
    cab = ["SECRETARIA DE ADMINISTRAÇÃO FGV CONHECIMENTO", "AGENTE – TARDE TIPO BRANCA – PÁGINA {}"]
    paginas = [
        _pagina([c.format(2) for c in cab],
                "Leia o texto.\n5\nlinha do texto\n10\noutra linha\n"
                "31\nSobre a pena, assinale a correta.\n(A) um\n(B) dois\n(C) três\n(D) quatro\n"
                "(E) cinco.\nDireitos Humanos"),
        _pagina([c.format(3) for c in cab],
                "32\nSobre a Declaração, assinale a correta.\n(A) a\n(B) b\n(C) c\n(D) d\n(E) e."),
        _pagina([c.format(4) for c in cab], "33\nOutra?\n(A) a\n(B) b\n(C) c\n(D) d\n(E) e."),
    ]
    texto = qp.sem_cabecalho(paginas, tirar_numeros=False)
    assert "FGV CONHECIMENTO" not in texto and "PÁGINA" not in texto
    lidas = qp.dividir_em_questoes(texto, {31: "e", 32: "b", 33: None}, marca="numero")
    assert [(q.numero, q.resposta, q.anulada) for q in lidas] == [
        (31, "e", False), (32, "b", False), (33, None, True)]
    # O titulo "Direitos Humanos" ficou fora da alternativa E da 31.
    assert lidas[0].alternativas["e"] == "cinco."


def test_access_a_alternativa_repetida_em_toda_pagina_nao_e_cabecalho():
    alternativas = ("(A) se apenas as afirmativas I e II estiverem corretas.\n"
                    "(B) se apenas a I estiver correta.\n(C) se apenas a II estiver correta.\n"
                    "(D) se nenhuma estiver correta.\n(E) se todas estiverem corretas.")
    paginas = [
        _pagina(["Guarda Civil - Edital nº 01/2023", f"Caderno de prova tipo 1 - branco | Página - {n}"],
                f"Questão {n}\nAnalise as afirmativas da questão {n}.\n{alternativas}")
        for n in range(21, 25)]
    lidas = qp.dividir_em_questoes(qp.sem_cabecalho(paginas), {}, marca="questao")
    assert [q.numero for q in lidas] == [21, 22, 23, 24]
    assert all(len(q.alternativas) == 5 for q in lidas)
    assert all("Caderno de prova" not in q.alternativas["e"] for q in lidas)


def test_idecan_a_linha_repetida_dentro_da_pagina_fica_e_o_numero_da_pagina_sai():
    cab = ["ESTADO DE SANTA CATARINA", "POLÍCIA CIVIL", "02100 – ESCRIVÃO DE POLÍCIA CIVIL – TIPO A"]
    corpo = ("13. Qual o prazo?\n"
             "(A) 5 dias, prorrogável, em caso de extrema e\ncomprovada necessidade.\n"
             "(B) 10 dias, em caso de extrema e\ncomprovada necessidade.\n"
             "(C) 15 dias, em caso de extrema e\ncomprovada necessidade.\n"
             "(D) 20 dias, em caso de extrema e\ncomprovada necessidade.\n"
             "(E) 30 dias, em caso de extrema e\ncomprovada necessidade.\n"
             "Tecnologia da Informação, Segurança Cibernética e Crimes Digitais")
    paginas = [_pagina(["4", *cab], corpo)] + [
        _pagina([str(n), *cab], f"{n + 10}. Outra?\n(A) a\n(B) b\n(C) c\n(D) d\n(E) e.")
        for n in range(5, 8)]
    lidas = qp.dividir_em_questoes(qp.sem_cabecalho(paginas), {13: "b"}, marca="ponto")
    treze = lidas[0]
    assert treze.numero == 13 and treze.resposta == "b"
    assert treze.alternativas["e"] == "30 dias, em caso de extrema e comprovada necessidade."
    assert all(alt.endswith("comprovada necessidade.") for alt in treze.alternativas.values())


def test_selecon_a_ordem_embaralhada_e_a_marca_de_canto():
    pagina = ("A\nPROVA\n24. Vinte e quatro?\nA) a\nB) b\nC) c\nD) d\n"
              "26. Vinte e seis?\nA) a\nB) b\nC) c\nD) d fim da 26\nAPROVA\n"
              "23. Vinte e tres?\nA) a\nB) b\nC) c\nD) d\n25. Vinte e cinco?\nA) a\nB) b\nC) c\nD) d")
    lidas = qp.dividir_em_questoes(qp.sem_cabecalho([pagina]), {}, marca="ponto",
                                   alternativa="fecha", letras="ABCD")
    assert [q.numero for q in lidas] == [23, 24, 25, 26]
    assert lidas[1].enunciado == "Vinte e quatro?"
    assert lidas[3].alternativas["d"] == "d fim da 26"


def test_so_as_paginas_da_versao_e_do_cargo():
    """O "PROVA A" da PM de Sergipe traz a Prova A e depois a B; o da
    SENAPPEN junta os cargos. A pagina sem marca e da versao da anterior."""
    paginas = ["A\nPROVA\nANALISTA EM DIREITO\n1. a1", "ANALISTA EM DIREITO\n2. a2 (sem marca)",
               "B\nPROVA\nANALISTA EM DIREITO\n1. b1", "B\nPROVA\nANALISTA EM DIREITO\n2. b2",
               "A\nPROVA\nANALISTA EM ECONOMIA\n1. outro cargo"]
    da_a = qp.paginas_da_versao(paginas, "PROVA A", "ANALISTA EM DIREITO")
    assert [p.splitlines()[-1] for p in da_a] == ["1. a1", "2. a2 (sem marca)"]
    assert qp.paginas_da_versao(paginas, "PROVA C") == []


def test_ler_limita_as_questoes():
    texto = "\n".join(f"{n}. Q{n}?\n(A) a\n(B) b\n(C) c\n(D) d\n(E) e" for n in range(1, 7))
    lidas = qp.dividir_em_questoes(texto, {}, marca="ponto", ler=["2-3", "6"])
    assert [q.numero for q in lidas] == [2, 3, 6]


def test_o_caderno_sem_pagina_da_versao_e_recusado(monkeypatch):
    monkeypatch.setattr(qp, "paginas_do_caderno", lambda caminho: ["A\nPROVA\n1. x"])
    with pytest.raises(ValueError):
        qp.ler_prova(Path("caderno.pdf"), {}, versao="PROVA B", marca="ponto")


def test_o_servico_nao_le_sem_versao_nem_com_a_versao_errada(monkeypatch):
    from radar import gabarito_por_versao, servico

    monkeypatch.setattr(qp, "paginas_do_caderno", lambda caminho: [
        "A\nPROVA\n1. Uma?\nA) a\nB) b\nC) c\nD) d"])
    monkeypatch.setattr(gabarito_por_versao, "da_versao", lambda caminho, versao, cargo=None: {1: "b"})
    ler = servico.provas._ler_selecon
    certa = ler(Path("c.pdf"), {"versao": "PROVA A", "alternativas": 4}, Path("g.pdf"))
    assert [(q.numero, q.resposta) for q in certa] == [(1, "b")]
    assert ler(Path("c.pdf"), {"versao": "PROVA B", "alternativas": 4}, Path("g.pdf")) == []
    assert servico.provas._ler_fgv(Path("c.pdf"), {"versao": "TIPO 1"}, None) == []
