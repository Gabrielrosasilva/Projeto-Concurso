"""A releitura do caderno com o leitor consertado (B.7).

O leitor da FEPESE deixava lixo no fim da ultima alternativa - o titulo da
secao seguinte, a grade de respostas, o rodape da fundacao - e apagava como
cabecalho a metade de baixo de uma palavra quebrada ("e cor-" / "reto
afirmar:"). E quando o `radar questoes --refazer` muda o texto de uma
questao, muda a chave dela: a classificacao e a base das geradas vao junto.
"""
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from radar import config, edital_programa, questoes
from radar.db import sessao
from radar.models import Classificacao, QuestaoDeProva, QuestaoGerada
from radar.servico import classificacoes, conteudos, geradas

PROGRAMA = edital_programa.ler_programa(
    (Path(__file__).parent / "fixtures" / "provas" / "edital_sap_2019_programa.txt")
    .read_text(encoding="utf-8"))
IMPUTABILIDADE = "Direito Penal > Imputabilidade penal"
CRIMES = "Direito Penal > Crimes contra a Administração Pública"
AGORA = datetime(2026, 10, 4, 12, tzinfo=timezone.utc)


def _questao(numero, enunciado, fim_da_e="Quinta."):
    return (f"{numero}. {enunciado}\n"
            "a. SQUARE Primeira.\n"
            "b. Check-square Segunda.\n"
            "c. SQUARE Terceira.\n"
            "d. SQUARE Quarta.\n"
            f"e. SQUARE {fim_da_e}\n")


def _ler(*partes) -> dict[int, questoes.Questao]:
    return {q.numero: q for q in questoes.dividir_em_questoes("".join(partes))}


# --- o leitor -------------------------------------------------------------------------

def test_a_metade_de_baixo_da_palavra_quebrada_nao_e_cabecalho():
    """"reto afirmar:" se repete em toda questao que comeca igual, e era
    apagada como cabecalho: o enunciado acabava em "e cor-"."""
    comeco = "De acordo com o Código Penal Brasileiro, é cor-\nreto afirmar:"
    lidas = _ler("Direito Penal 3 questões\n",
                 _questao(1, comeco), _questao(2, comeco), _questao(3, comeco))
    assert {q.enunciado for q in lidas.values()} == {
        "De acordo com o Código Penal Brasileiro, é correto afirmar:"}


def test_o_titulo_da_secao_seguinte_nao_gruda_na_ultima_alternativa():
    lidas = _ler("Direito Penal 1 questões\n", _questao(1, "Qual é a pena?"),
                 "Direitos Humanos 1 questões\n",
                 "Texto de apoio das questões de baixo.\n",
                 _questao(2, "O que diz o texto?"))
    assert lidas[1].alternativas["e"] == "Quinta."
    assert lidas[2].materia == "Direitos Humanos"


def test_o_titulo_quebrado_em_duas_linhas_tambem_sai():
    lidas = _ler("Direito Penal 1 questões\n", _questao(1, "Qual é a pena?"),
                 "Conhecimentos\nGerais sobre Educação 1 questões\n",
                 _questao(2, "O que diz a lei?"))
    assert lidas[1].alternativas["e"] == "Quinta."
    assert lidas[2].materia == "Conhecimentos Gerais sobre Educação"


def test_a_questao_cem_nao_leva_o_numero_no_enunciado():
    lidas = _ler("Sociologia Aplicada 1 questões\n", _questao(100, "Analise as afirmativas."))
    assert lidas[100].enunciado == "Analise as afirmativas."


def test_a_ordem_das_secoes_sai_do_caderno_e_nao_do_texto():
    """No Socioeducativo, o titulo de Direito Processual Penal (49 e 50) saia
    depois do de Legislacao Estadual (51 a 60), e a conta pela ordem do texto
    trocava as materias (B.10)."""
    lidas = _ler("Direito Penal 2 questões\n", _questao(1, "Um?"), _questao(2, "Dois?"),
                 "Legislação Estadual 2 questões\n", _questao(5, "Cinco?"), _questao(6, "Seis?"),
                 "Direito Processual Penal 2 questões\n", _questao(3, "Tres?"),
                 _questao(4, "Quatro?"))
    assert {n: q.materia for n, q in lidas.items()} == {
        1: "Direito Penal", 2: "Direito Penal",
        3: "Direito Processual Penal", 4: "Direito Processual Penal",
        5: "Legislação Estadual", 6: "Legislação Estadual"}


def test_pista_fora_da_faixa_fica_a_ordem_do_texto():
    """Se a primeira questao depois de um titulo nao cabe na faixa que a
    secao ganharia, a pista nao serve, e vale a ordem de sempre."""
    texto = ("Direito Penal 2 questões\n" + _questao(9, "Fora?")
             + "Direitos Humanos 2 questões\n" + _questao(3, "Tres?"))
    secoes = questoes.achar_secoes(texto)
    assert questoes.materias_por_numero(secoes, texto) == {
        1: "Direito Penal", 2: "Direito Penal", 3: "Direitos Humanos", 4: "Direitos Humanos"}


def test_o_fim_do_caderno_sai_da_alternativa():
    """A grade de respostas, o rodape da fundacao e a coluna em branco."""
    cortar = questoes.cortar_mobilia
    assert cortar("F • V • V • F • V . Utilize a grade ao lado para anotar as "
                  "suas respostas. Não destaque esta folha.") == "F • V • V • F • V"
    assert cortar("Mais de 7500 1 2 3 4 5 6 7 8 9 10 11 12 . GRADE DE RESPOSTAS "
                  "Utilize a grade") == "Mais de 7500"
    assert cortar("para a servidora efetiva. FEPESE • Fundação de Estudos e "
                  "Pesquisas Sócio-Econômicos Campus Universitário • UFSC") == (
        "para a servidora efetiva.")
    assert cortar("Rio do Sul. Coluna em Branco. Texto 8a “ … é preciso") == "Rio do Sul."
    assert cortar("porém afiançável. Conhecimentos Específicos (40 questões)") == (
        "porém afiançável.")


def test_o_corte_nao_pega_texto_de_questao():
    cortar = questoes.cortar_mobilia
    assert cortar("O texto tem 5 (cinco) linhas.") == "O texto tem 5 (cinco) linhas."
    assert cortar("São corretas as afirmativas 1, 2, 3, 4 e 5.") == (
        "São corretas as afirmativas 1, 2, 3, 4 e 5.")


# --- a chave acompanha o texto --------------------------------------------------------

def _linhas(chave):
    with sessao() as s:
        return {c.conteudo: c for c in s.scalars(
            select(Classificacao).where(Classificacao.chave == chave))}


def test_a_classificacao_vai_para_a_chave_nova(banco_temporario):
    conteudos.semear(programa=PROGRAMA)
    classificacoes.classificar("velha", IMPUTABILIDADE, "Claude Code", conferida_em=AGORA)

    resumo = classificacoes.rechavear({"velha": {"nova"}}, em_uso={"nova"})

    assert resumo["levadas"] == 1
    assert _linhas("velha") == {}
    nova = _linhas("nova")[IMPUTABILIDADE]
    assert (nova.principal, nova.procedencia) == (True, "Claude Code")
    assert nova.conferida_em is not None


def test_a_chave_antiga_que_ainda_existe_e_copiada(banco_temporario):
    """A mesma questao em outro caderno, que a releitura nao mudou."""
    conteudos.semear(programa=PROGRAMA)
    classificacoes.classificar("velha", IMPUTABILIDADE, "Claude Code")

    classificacoes.rechavear({"velha": {"nova"}}, em_uso={"velha", "nova"})

    assert set(_linhas("velha")) == {IMPUTABILIDADE}
    assert set(_linhas("nova")) == {IMPUTABILIDADE}


def test_juntando_duas_fica_a_conferida_e_uma_principal(banco_temporario):
    conteudos.semear(programa=PROGRAMA)
    classificacoes.classificar("nova", CRIMES, "Claude Code")
    classificacoes.classificar("velha", IMPUTABILIDADE, "Claude Code", conferida_em=AGORA)

    resumo = classificacoes.rechavear({"velha": {"nova"}}, em_uso={"nova"})

    linhas = _linhas("nova")
    assert linhas[IMPUTABILIDADE].principal and linhas[IMPUTABILIDADE].conferida_em
    assert not linhas[CRIMES].principal          # a outra vira associada
    assert resumo["principais_desfeitas"] == 1


def test_no_mesmo_no_a_conferida_prevalece(banco_temporario):
    conteudos.semear(programa=PROGRAMA)
    classificacoes.classificar("nova", IMPUTABILIDADE, "Claude Code", trecho="sem conferir")
    classificacoes.classificar("velha", IMPUTABILIDADE, "manual", trecho="conferida",
                               conferida_em=AGORA)

    classificacoes.rechavear({"velha": {"nova"}}, em_uso={"nova"})

    (linha,) = _linhas("nova").values()
    assert (linha.trecho, linha.procedencia) == ("conferida", "manual")


def _gerada(impressao, origem_chave, origem_impressao):
    return QuestaoGerada(impressao=impressao, enunciado=f"Gerada {impressao}?",
                         alternativas={"a": "x", "b": "y"}, resposta="a", modo="variacao",
                         modelo="claude-x", criada_em=AGORA, origem_chave=origem_chave,
                         origem_impressao=origem_impressao)


def test_a_base_da_gerada_acompanha_a_chave_nova(banco_temporario):
    with sessao() as s:
        s.add(_gerada("g1", "velha", "imp-velha"))
        s.add(_gerada("g2", "dupla", "imp-dupla"))

    mudaram = geradas.rechavear({"velha": {"nova"}, "dupla": {"n1", "n2"}},
                                {"imp-velha": {"imp-nova"}})

    with sessao() as s:
        por_impressao = {g.impressao: g for g in s.scalars(select(QuestaoGerada))}
    assert (por_impressao["g1"].origem_chave, por_impressao["g1"].origem_impressao) == (
        "nova", "imp-nova")
    # Duas chaves novas para a mesma antiga: nao ha como saber qual.
    assert por_impressao["g2"].origem_chave == "dupla"
    assert mudaram == 2


def test_releer_o_caderno_leva_a_classificacao_junto(banco_temporario, tmp_path, monkeypatch):
    """De ponta a ponta: o banco tem o texto do leitor antigo, com o titulo da
    secao seguinte grudado na "e"; o `refazer` le o caderno de novo, o texto
    muda, e a classificacao conferida continua la, na chave nova."""
    from radar import provas, servico

    conteudos.semear(programa=PROGRAMA)
    (config.diretorio_dados() / "p.pdf").write_bytes(b"%PDF-1.4 fingindo")
    provas.gravar_manifesto(provas.carregar_manifesto() + [{
        "tipo": "prova", "url": "https://x.test/p.pdf", "arquivo": "p.pdf",
        "caminho": "p.pdf", "banca": "FEPESE", "ano": 2024, "municipio": "Palhoca",
        "cargo": "Guarda Patrimonial", "concurso_url": "https://x.test/c"}])
    alternativas = {"a": "Primeira.", "b": "Segunda.", "c": "Terceira.", "d": "Quarta.",
                    "e": "Quinta. Direitos Humanos 1 questões"}
    with sessao() as s:
        s.add(QuestaoDeProva(
            prova_url="https://x.test/p.pdf", numero=1, banca="FEPESE", ano=2024,
            materia="Direito Penal", enunciado="Qual é a pena?", alternativas=alternativas,
            resposta="b", impressao=questoes.impressao_de("Qual é a pena?")))
    velha = questoes.chave_da_questao("Qual é a pena?", alternativas)
    classificacoes.classificar(velha, IMPUTABILIDADE, "Claude Code", conferida_em=AGORA)
    monkeypatch.setattr(questoes, "extrair_texto", lambda caminho: (
        "Direito Penal 1 questões\n" + _questao(1, "Qual é a pena?")
        + "Direitos Humanos 1 questões\n" + _questao(2, "O que diz o texto?")))

    resultado = servico.extrair_questoes(limite=5, refazer=True)

    nova = questoes.chave_da_questao("Qual é a pena?", {**alternativas, "e": "Quinta."})
    assert (resultado.texto_mudou, resultado.classificacoes_levadas) == (1, 1)
    assert _linhas(velha) == {}
    assert _linhas(nova)[IMPUTABILIDADE].conferida_em is not None
    assert "com o texto mudado" in str(resultado)


# --- o download: arquivo de mesmo nome em dois hotsites (B.9) -------------------------

def _documento(url):
    from radar import provas
    return provas.Documento(tipo="prova", url=url, arquivo="S07.pdf", banca="FEPESE",
                            ano=2024, municipio="Palhoca")


def test_dois_hotsites_com_o_mesmo_nome_de_arquivo_nao_dividem_o_caminho(banco_temporario):
    """A FEPESE chama de S07.pdf provas de cargos diferentes em concursos
    diferentes de Palhoca. O segundo nunca era baixado: o caminho ja existia,
    e a prova dele apontava para o PDF do outro concurso."""
    from radar import provas

    primeiro = _documento("https://2024emergencialpalhoca.fepese.org.br/?arquivo=S07.pdf")
    segundo = _documento("https://2024pseducapalhoca.fepese.org.br/?arquivo=S07.pdf")
    padrao = provas.destino(primeiro)
    ocupados = {provas._caminho_relativo(padrao): primeiro.url}

    assert provas.destino(primeiro, ocupados) == padrao          # o dono continua
    outro = provas.destino(segundo, ocupados)
    assert outro != padrao and outro.name == "2024pseducapalhoca-s07.pdf"
    assert provas.destino(segundo) == padrao                     # sem o manifesto, o de sempre


def test_a_reconstrucao_usa_o_caminho_que_o_manifesto_gravou(banco_temporario, monkeypatch):
    from radar import provas, servico

    segundo = _documento("https://2024pseducapalhoca.fepese.org.br/?arquivo=S07.pdf")
    proprio = "provas/fepese/2024/palhoca/2024pseducapalhoca-s07.pdf"
    provas.gravar_manifesto([{**provas.para_registro(segundo), "caminho": proprio}])
    gravados = []
    monkeypatch.setattr(provas, "baixar", lambda documento, buscador, forcar=False,
                        caminho=None, ocupados=None: gravados.append(caminho) or documento)
    monkeypatch.setattr(servico.provas, "Buscador", lambda: None)

    servico.provas.baixar_do_manifesto()

    assert [c.as_posix().endswith(proprio) for c in gravados] == [True]


# --- o numero da questao depois de alternativa com lista numerada (B.9) ---------------

def test_a_lista_numerada_da_alternativa_nao_vira_o_numero_da_seguinte():
    """Na Florianopolis 2023, a "e" da 19 tinha "1. silepse • 2. comparacao" e
    "3. eufemismo" comecando linha: a 20 virava a "3", batia com a 3 de
    verdade e sumia em 26 cadernos; e a "e" da 19 acabava cortada."""
    lista = ("1. silepse • 2. comparação •\n"
             "3. eufemismo • 4. catacrese")
    lidas = _ler("Língua Portuguesa 3 questões\n", _questao(1, "Um?"), _questao(2, "Dois?", lista),
                 _questao(3, "Tres?"))
    assert sorted(lidas) == [1, 2, 3]
    assert lidas[2].alternativas["e"] == "1. silepse • 2. comparação • 3. eufemismo • 4. catacrese"
    assert lidas[3].enunciado == "Tres?"


def test_a_lista_de_dentro_do_enunciado_continua_no_enunciado():
    lidas = _ler("Língua Portuguesa 2 questões\n", _questao(1, "Um?"),
                 _questao(2, "Analise:\n1. primeira.\n2. segunda.\nQuais estão certas?"))
    assert lidas[2].enunciado == "Analise: 1. primeira. 2. segunda. Quais estão certas?"


def test_a_releitura_reconhece_a_mesma_questao_limpa_ou_completada():
    from radar.servico import provas as servico_provas

    mesma = servico_provas._mesma_questao
    texto = servico_provas._texto_inteiro
    sujo = texto("Qual é a pena?", {"a": "Um.", "e": "Cinco. Direitos Humanos 10 questões"})
    limpo = texto("Qual é a pena?", {"a": "Um.", "e": "Cinco."})
    assert mesma(sujo, limpo)
    assert mesma(texto("De acordo com o CP, é cor-", {"a": "Um."}),
                 texto("De acordo com o CP, é correto afirmar:", {"a": "Um."}))
    assert not mesma(texto("Qual é a capital de Santa Catarina?", {"a": "Florianópolis."}),
                     texto("Assinale a alternativa sobre o Excel.", {"a": "A planilha."}))


def test_numero_que_passou_a_ser_de_outra_questao_nao_leva_a_classificacao(
        banco_temporario, monkeypatch):
    """A releitura que poe OUTRA questao no mesmo numero nao e limpeza: a
    classificacao fica na chave antiga, e nao classifica a questao errada."""
    from radar import provas, servico

    conteudos.semear(programa=PROGRAMA)
    (config.diretorio_dados() / "p.pdf").write_bytes(b"%PDF-1.4 fingindo")
    provas.gravar_manifesto([{
        "tipo": "prova", "url": "https://x.test/p.pdf", "arquivo": "p.pdf",
        "caminho": "p.pdf", "banca": "FEPESE", "ano": 2024, "municipio": "Palhoca",
        "cargo": "Guarda Patrimonial", "concurso_url": "https://x.test/c"}])
    alternativas = {"a": "Florianópolis.", "b": "Joinville.", "c": "Blumenau.",
                    "d": "Lages.", "e": "Chapecó."}
    enunciado = "Qual é a capital de Santa Catarina?"
    with sessao() as s:
        s.add(QuestaoDeProva(prova_url="https://x.test/p.pdf", numero=1, banca="FEPESE",
                             ano=2024, materia="Direito Penal", enunciado=enunciado,
                             alternativas=alternativas, resposta="a",
                             impressao=questoes.impressao_de(enunciado)))
    velha = questoes.chave_da_questao(enunciado, alternativas)
    classificacoes.classificar(velha, IMPUTABILIDADE, "Claude Code", conferida_em=AGORA)
    monkeypatch.setattr(questoes, "extrair_texto", lambda caminho: (
        "Direito Penal 1 questões\n" + _questao(1, "Assinale a alternativa sobre o Excel.")))

    resultado = servico.extrair_questoes(limite=5, refazer=True)

    assert (resultado.conteudo_trocado, resultado.classificacoes_levadas) == (1, 0)
    assert set(_linhas(velha)) == {IMPUTABILIDADE}
