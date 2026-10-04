"""A ficha de estudo de cada tema do cronograma (Etapa 6B, secoes 10 a 12 e 14).

O que estes testes seguram:

  * a ficha e UMA estrutura, com todos os campos da secao 11;
  * o tema e reconhecido pelo titulo EXATO sem o prefixo, em toda faixa dele
    (teoria, fixacao, aprendizagem, R+7, R+30, Plano B) - e so nelas;
  * alvo e complementar ficam separados, cada um com a amostra, e uma prova
    complementar nova nao muda nada do alvo (regra inviolavel 1);
  * campo do acervo sem dado diz a frase exata da regra 4; campo escrito sem
    texto diz que falta texto - e nada e inventado;
  * texto de IA leva o 🟣 e a procedencia (decisao 9);
  * a importacao recusa no fora da arvore, materia inteira, no dentro de no,
    ficha sem o que ler, e texto com cara de previsao; nao sobrescreve a
    ficha que eu conferi;
  * a tela e o terminal mostram a ficha, e a tela Hoje leva ate ela.

Nada aqui vai a internet nem chama a API.
"""
import json
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from radar import amostra, conteudos as arvore, cronograma, fichas, incidencia, leis, origem, prioridade
from radar.cli import app as cli
from radar.servico import estudo
from radar.servico import fichas as servico_fichas
from radar.servico import manual
from radar.web.app import app

FIXTURE = Path(__file__).parent / "fixtures" / "cronograma_fichas.yml"
PREVISAO = re.compile(r"(?i)vai cair|certamente|sempre cobra|cairá")

DC = "Direito Constitucional"
DIREITOS = f"{DC} > Direitos e garantias fundamentais: direitos e garantias individuais e coletivos"
CASA = f"{DIREITOS} > Inviolabilidade do domicílio"
CASA_XI = f"{CASA} > CF, art. 5º, XI"
INTIMIDADE = f"{DIREITOS} > Intimidade, vida privada, honra e imagem"
REMEDIOS = f"{DIREITOS} > Remédios constitucionais"
VIDA = f"{DC} > direito à vida, à liberdade, à igualdade, à segurança e à propriedade"
LP = "Língua Portuguesa"
VOZES = f"{LP} > Vozes do verbo"
RL = "Raciocínio Lógico"
CONTAGEM = f"{RL} > Princípios de contagem"

NIVEIS = {DC: "materia", DIREITOS: "assunto", CASA: "subassunto", CASA_XI: "elemento",
          INTIMIDADE: "subassunto", REMEDIOS: "subassunto", VIDA: "assunto",
          LP: "materia", VOZES: "assunto", RL: "materia", CONTAGEM: "assunto"}

TEMA = "Art. 5º, caput e incisos I a XVI"


def _plano():
    return cronograma.carregar(FIXTURE)


def _escrita(**mudar) -> fichas.FichaEscrita:
    base = dict(
        tema=TEMA, materia=DC,
        assunto="Direitos e garantias fundamentais: direitos e garantias individuais e coletivos",
        elemento="CF, art. 5º, caput e incisos I a XVI", tipo_elemento="inciso",
        nos=[VIDA, CASA, INTIMIDADE],
        por_que_estes_nos="o caput é outro assunto do edital; X e XI têm nó",
        ler_exatamente="CF, art. 5º: o caput e os incisos I a XVI, no texto oficial.",
        como_pesquisar=["artigo 5 constituição incisos I a XVI"],
        entender=["a casa é asilo inviolável do indivíduo"],
        memorizar=["de dia, só por ordem judicial (XI)"],
        pegadinhas=["trocar 'dia' por 'noite' na ordem judicial"],
        modelo="Claude Code, importado manualmente, em 02/10/2026",
        criado_em="2026-10-02T12:00:00+00:00",
    )
    base.update(mudar)
    return fichas.FichaEscrita(**base)


def _oc(prova, ano, numero, conteudo, *, status="completa", anulada=False,
        impressao=None, pegadinha=None, conferida=True, materia=DC):
    return incidencia.Ocorrencia(
        prova=prova, ano=ano, materia=materia, conteudo=conteudo, status=status,
        anulada=anulada, pegadinha=pegadinha, enunciado=f"Enunciado {prova}-{numero}",
        resposta="c", impressao=impressao or f"{prova}-{numero}", numero=numero,
        conferida=conferida, tipo_de_questao="literalidade da lei")


ALVO = [
    _oc("ap2013", 2013, 15, CASA_XI, pegadinha="ordem judicial só de dia"),
    _oc("ap2019", 2019, 40, REMEDIOS),
    _oc("ap2019", 2019, 41, DC, status="pendente"),
    _oc("ap2013", 2013, 20, CASA_XI, anulada=True),
]
COMPLEMENTAR = [
    _oc("am2024", 2024, 3, INTIMIDADE, impressao="mesma", conferida=False,
        pegadinha="anonimato assegurado"),
    _oc("gm2024", 2024, 7, INTIMIDADE, impressao="mesma", conferida=False),
    _oc("as2016", 2016, 12, REMEDIOS, conferida=False),
]


@dataclass
class _NaFila:
    caminho: str
    motivos: list = field(default_factory=lambda: ["erro recente"])

    @property
    def porque(self) -> str:
        return " · ".join(self.motivos)


def _contexto(**mudar) -> fichas.Contexto:
    plano = mudar.pop("plano", None) or _plano()
    base = dict(
        hoje=date(2026, 10, 2), plano=plano,
        caminhos=list(NIVEIS), niveis=dict(NIVEIS),
        ocorrencias_alvo=list(ALVO), ocorrencias_complementares=list(COMPLEMENTAR),
        entradas=[], metas={DC: 80}, fila=[], situacoes={}, geradas=[],
        lei=lambda materia, assunto: (leis.Lei("Constituição Federal de 1988",
                                               "https://www.planalto.gov.br/cf")
                                      if materia == DC else None),
        minimos_amostra=amostra.PADRAO, minimos_acervo=incidencia.Minimos(),
        regra=prioridade.Regra(),
        dia_montado=lambda d: cronograma.montar_dia(plano, d, 1),
        refazer=lambda dentro: estudo.Refazer(),
        escritas=[_escrita()],
    )
    base.update(mudar)
    return fichas.Contexto(**base)


def _montar(escrita=None, data=None, **mudar) -> fichas.FichaDeEstudo:
    ctx = _contexto(**mudar)
    return fichas.montar(escrita or ctx.escritas[0], ctx, data)


# --- a estrutura unica (secao 11) ---------------------------------------------------

def test_a_ficha_tem_todos_os_campos_da_secao_11():
    ficha = _montar()
    assert len(fichas.CAMPOS_DA_SECAO_11) == 16
    for ingles, portugues in fichas.CAMPOS_DA_SECAO_11.items():
        assert hasattr(ficha, portugues), f"{ingles} -> {portugues}"
    assert ficha.caminho_exibido == [
        DC, "Direitos e garantias fundamentais: direitos e garantias individuais e coletivos",
        "CF, art. 5º, caput e incisos I a XVI"]


def test_todo_campo_tem_origem_registrada():
    for campo in fichas.CAMPOS_DA_SECAO_11.values():
        if campo == "fonte":
            continue        # a fonte carrega a dela: oficial ou ia
        assert campo in fichas.ORIGEM_DO_CAMPO, campo
    assert set(fichas.ORIGEM_DO_CAMPO.values()) <= set(origem.SELOS)
    ficha = _montar()
    assert ficha.fonte.origem == fichas.OFICIAL
    assert ficha.ler_exatamente.origem == fichas.IA


def test_texto_de_ia_leva_o_selo_roxo_e_a_procedencia():
    ficha = _montar()
    assert origem.SELOS[fichas.IA].emoji == "🟣"
    assert fichas.ORIGEM_DO_CAMPO["entender"] == fichas.IA
    assert fichas.ORIGEM_DO_CAMPO["memorizar"] == fichas.IA
    assert ficha.procedencia == "Claude Code, importado manualmente, em 02/10/2026"
    assert not ficha.conferida


# --- o tema pelo titulo -------------------------------------------------------------

def test_o_tema_sai_do_titulo_sem_o_prefixo():
    assert fichas.tema_da_faixa("R+7: " + TEMA) == TEMA
    assert fichas.tema_da_faixa("R+30: " + TEMA) == TEMA
    assert fichas.tema_da_faixa("Fixação: " + TEMA) == TEMA
    assert fichas.tema_da_faixa("Aprendizagem: " + TEMA) == TEMA
    assert fichas.tema_da_faixa("Artigos-chave: " + TEMA) == TEMA
    assert fichas.tema_da_faixa("Questões de prova: " + TEMA) == TEMA
    assert fichas.tema_da_faixa("Raciocínio Lógico: princípios de contagem",
                                RL) == "princípios de contagem"
    assert fichas.id_do_tema(TEMA) == "art-5o-caput-e-incisos-i-a-xvi"


def test_toda_faixa_do_tema_mostra_a_ficha_e_so_elas():
    plano = _plano()
    escritas = [_escrita()]
    dia = plano.dia(date(2026, 9, 29))
    com_ficha = [f.titulo for f in dia.manha + dia.noite if fichas.da_faixa(f, escritas)]
    assert com_ficha == [TEMA, "Fixação: " + TEMA, "Aprendizagem: " + TEMA]
    revisao = plano.dia(date(2026, 10, 6)).noite[0]
    assert fichas.da_faixa(revisao, escritas).id == "art-5o-caput-e-incisos-i-a-xvi"
    # Outro inciso do mesmo artigo e outro tema: nada e aproximado.
    outro = plano.dia(date(2026, 10, 6)).manha[0]
    assert fichas.da_faixa(outro, escritas) is None


def test_mesmo_titulo_em_outra_materia_nao_e_o_mesmo_tema():
    faixa = cronograma.Faixa(bloco="manha", tipo="teoria", titulo=TEMA, materia=LP)
    assert fichas.da_faixa(faixa, [_escrita()]) is None
    sem_materia = cronograma.Faixa(bloco="manha", tipo="pausa", titulo=TEMA)
    assert fichas.da_faixa(sem_materia, [_escrita()]) is None


def test_o_plano_b_tambem_leva_a_ficha():
    plano = _plano()
    plano.plano_b = cronograma.PlanoB(
        opcoes={30: cronograma.OpcaoDoPlanoB(30, 10, 8, 0, False)},
        sabado="Refaça", sabado_questoes=20)
    dia = cronograma.montar_plano_b(plano, date(2026, 9, 29), 30, 1)
    titulos = [f.titulo for f in dia.plano_b if fichas.da_faixa(f, [_escrita()])]
    assert titulos == ["Artigos-chave: " + TEMA, "Questões de prova: " + TEMA]


def test_os_temas_do_plano_incluem_o_estudado_antes_que_ainda_volta():
    temas = fichas.temas_do_plano(_plano(), date(2026, 10, 2))
    nomes = [t.tema for t in temas]
    # O Art. 5º foi estudado em 29/09 e volta em 06/10 e 29/10.
    assert TEMA in nomes
    # Vozes do verbo so teve 29/09: nao entra de 02/10 em diante.
    assert "Vozes do verbo" not in nomes
    assert "Princípios de contagem" in nomes
    art5 = next(t for t in temas if t.tema == TEMA)
    assert [f.data.isoformat() for f in art5.faixas] == [
        "2026-09-29", "2026-09-29", "2026-09-29", "2026-10-06", "2026-10-29"]


# --- alvo e complementar, separados e com a amostra ---------------------------------

def test_alvo_e_complementar_separados_cada_um_com_a_amostra():
    ficha = _montar()
    # Alvo: so a 2013-q15 (XI). A de Remedios esta fora do escopo, a
    # pendente e a anulada nao contam.
    assert ficha.linha_do_alvo.amostra == "1 questão · 1 prova"
    assert ficha.linha_do_alvo.rotulo == "apareceu em 1 de 2 provas"
    # Complementar: a mesma questao em dois cadernos e UMA questao.
    assert ficha.linha_complementar.questoes == 1
    assert ficha.linha_complementar.ocorrencias == 2
    assert ficha.linha_complementar.frase.startswith("Acervo complementar FEPESE: 1 questão")


def test_abaixo_do_minimo_o_padrao_diz_a_frase_exata():
    ficha = _montar()
    assert not ficha.padroes_do_alvo.suficiente
    assert ficha.padroes_do_alvo.frase == "Não há evidência suficiente no acervo para afirmar isso."


def test_com_amostra_o_padrao_aparece_e_diz_que_e_do_acervo():
    alvo = [_oc("ap2013", 2013, n, CASA_XI) for n in (1, 2)] + [
        _oc("ap2019", 2019, n, CASA_XI) for n in (3, 4)]
    ficha = _montar(ocorrencias_alvo=alvo)
    assert ficha.padroes_do_alvo.suficiente
    assert "padrão identificado no acervo analisado" in ficha.padroes_do_alvo.amostra


def test_prova_complementar_nova_nao_muda_nada_do_alvo():
    antes = _montar()
    nova = COMPLEMENTAR + [_oc(f"pref{n}", 2025, n, CASA_XI, conferida=False) for n in range(9)]
    depois = _montar(ocorrencias_complementares=nova)
    assert depois.linha_do_alvo.amostra == antes.linha_do_alvo.amostra
    assert depois.linha_do_alvo.rotulo == antes.linha_do_alvo.rotulo
    assert depois.padroes_do_alvo == antes.padroes_do_alvo
    assert depois.prioridade.alvo == antes.prioridade.alvo
    assert depois.linha_complementar.questoes > antes.linha_complementar.questoes


def test_os_padroes_do_complementar_so_com_gabarito_definitivo_e_a_parte():
    """F4 (decisao 78): os mesmos padroes do alvo, contados no complementar,
    so das provas com gabarito definitivo - e nunca somados aos do alvo."""
    nova = COMPLEMENTAR + [_oc(f"pref{n}", 2025, n, INTIMIDADE, conferida=False)
                           for n in range(3)]

    sem = _montar(ocorrencias_complementares=nova)
    assert not sem.padroes_complementares.suficiente
    assert sem.padroes_complementares.frase == fichas.FRASE_SEM_EVIDENCIA

    com = _montar(ocorrencias_complementares=nova,
                  provas_dos_padroes={"am2024", "pref0", "pref1", "pref2"})
    p = com.padroes_complementares
    assert p.suficiente
    assert "4 questões · 4 provas · acervo complementar FEPESE" in p.amostra
    # Classificacao sem conferir: nem tipo nem pegadinha viram padrao.
    assert (p.tipos, p.pegadinhas) == ([], [])
    assert com.padroes_do_alvo == sem.padroes_do_alvo


def test_as_questoes_reais_alvo_primeiro_sem_anulada_nem_pendente():
    ficha = _montar()
    codigos = [(q.codigo, q.evidencia) for q in ficha.questoes_reais]
    assert codigos == [("2013-q15", "alvo"), ("2024-q3", "complementar")]
    assert ficha.questoes_reais[1].onde == "acervo complementar FEPESE"
    # A pegadinha do acervo cita a questao, e diz se a classificacao foi conferida.
    pegadinhas = [(q.codigo, q.conferida) for q in ficha.pegadinhas_do_acervo]
    assert pegadinhas == [("2013-q15", True), ("2024-q3", False)]


# --- campo sem dado: nada inventado -------------------------------------------------

def test_tema_sem_no_nao_conta_nada_do_acervo_e_diz_a_frase():
    ficha = _montar(_escrita(nos=[], por_que_estes_nos="o programa de 2019 não lista o tema"))
    assert ficha.sem_no
    assert ficha.questoes_reais == []
    assert ficha.linha_do_alvo.amostra == "0 questões · 0 provas" or not ficha.linha_do_alvo.questoes
    assert ficha.vazio("questoes_reais") == fichas.FRASE_SEM_EVIDENCIA
    assert ficha.vazio("padroes_do_alvo") == fichas.FRASE_SEM_EVIDENCIA
    assert ficha.vazio("pegadinhas_do_acervo") == fichas.FRASE_SEM_EVIDENCIA
    # O "por que agora" tambem nao afirma nada das provas sobre ele.
    assert "não tem nó na árvore" in ficha.prioridade.alvo.texto
    assert not any("não apareceu" in item.texto for item in ficha.por_que_agora)


def test_campo_escrito_vazio_diz_que_falta_texto_e_nao_fala_do_acervo():
    ficha = _montar()
    assert ficha.vazio("entender") == fichas.FRASE_SEM_TEXTO
    assert ficha.vazio("como_pesquisar") == fichas.FRASE_SEM_TEXTO
    assert "acervo" not in fichas.FRASE_SEM_TEXTO
    with pytest.raises(KeyError):
        ficha.vazio("meta_de_questoes")     # do plano: a tela tem frase propria


# --- o plano: o que ler, quantas questoes, quando revisar ---------------------------

def test_os_artigos_chave_sao_os_do_dia_da_teoria_e_so_do_tema_dela():
    ficha = _montar()
    assert [a.artigos for a in ficha.artigos_chave] == ["CF art. 5º, XI", "CF art. 5º, XII"]
    vozes = _escrita(tema="Vozes do verbo", materia=LP, assunto="Vozes do verbo",
                     elemento="voz passiva", tipo_elemento="regra gramatical",
                     nos=[VOZES], fonte_sugerida="uma gramática")
    ficha_de_vozes = _montar(vozes)
    # O essencial de 29/09 e do Direito do dia, nao do Portugues.
    assert ficha_de_vozes.artigos_chave == []
    assert ficha_de_vozes.fonte.origem == fichas.IA


def test_a_meta_de_questoes_sai_do_plano_com_a_consulta():
    ficha = _montar()
    linhas = [(p.data.isoformat(), p.rotulo, p.questoes, p.consulta)
              for p in ficha.meta_de_questoes]
    assert linhas == [
        ("2026-09-29", "Fixação", 8, True),
        ("2026-09-29", "Aprendizagem", 15, True),     # a rampa de Direito: pode consultar
        ("2026-10-06", "R+7", 10, False),
        ("2026-10-29", "R+30", 10, False),
    ]


def test_quando_revisar_tem_o_plano_e_a_fila_como_sugestao():
    ficha = _montar()
    assert ficha.revisoes_do_plano == [(date(2026, 10, 6), "R+7"), (date(2026, 10, 29), "R+30")]
    assert "R+7 em 06/10 · R+30 em 29/10" in ficha.quando_revisar[0].texto
    assert any("Fora da fila" in m.texto for m in ficha.quando_revisar)

    na_fila = _montar(fila=[_NaFila(CASA), _NaFila(REMEDIOS, ["prazo de revisão vencido"])])
    textos = [m.texto for m in na_fila.quando_revisar]
    assert any("Inviolabilidade do domicílio — erro recente" in t for t in textos)
    # Remedios nao e deste tema: a fila dele nao entra aqui.
    assert not any("Remédios" in t for t in textos)
    assert na_fila.prioridade.revisao.valor == 1.5


def test_por_que_agora_diz_o_dia_do_cronograma_e_os_fatores():
    ficha = _montar(data=date(2026, 10, 29))
    assert ficha.por_que_agora[0].texto == (
        "O cronograma de 29/10 traz este tema: R+30 (a volta do estudo de 29/09).")
    assert ficha.por_que_agora[0].origem == fichas.PLANO
    origens = [m.origem for m in ficha.por_que_agora]
    assert fichas.OFICIAL in origens and fichas.ACERVO in origens and fichas.AUTOMATICO in origens
    sem_faixa = _montar(data=date(2026, 10, 20), hoje=date(2026, 10, 20))
    assert sem_faixa.por_que_agora[0].texto == "Próxima vez no cronograma: 29/10 (R+30)."
    assert sem_faixa.por_que_agora[1].texto == "Última vez no cronograma: 06/10 (R+7)."


def test_as_geradas_do_escopo_aparecem_e_as_de_fora_nao():
    dentro = SimpleNamespace(conteudo=CASA_XI, enunciado="gerada sobre a casa")
    fora = SimpleNamespace(conteudo=REMEDIOS, enunciado="gerada sobre habeas corpus")
    ficha = _montar(geradas=[dentro, fora])
    assert ficha.geradas == [dentro]
    assert fichas.ORIGEM_DO_CAMPO["geradas"] == fichas.IA


def test_o_comando_de_gerar_e_um_por_no_e_em_modo_treino():
    assert fichas.comando_de_gerar(CASA_XI) == (
        'radar gerar --pedido --modo treino --materia "Direito Constitucional" '
        '--assunto "Direitos e garantias fundamentais: direitos e garantias individuais '
        'e coletivos" --subassunto "Inviolabilidade do domicílio" --elemento "CF, art. 5º, '
        'XI" --quantas 10')


def test_desempenho_do_escopo_conta_cada_resposta_uma_vez():
    from radar.servico import desempenho_por_conteudo as por_conteudo

    entradas = [por_conteudo.Entrada(CASA_XI, por_conteudo.NO_RADAR, date(2026, 10, 1),
                                     respostas=1, acertos=1),
                por_conteudo.Entrada(INTIMIDADE, por_conteudo.ANOTADO, date(2026, 10, 1),
                                     respostas=10, acertos=6),
                por_conteudo.Entrada(REMEDIOS, por_conteudo.ANOTADO, date(2026, 10, 1),
                                     respostas=5, acertos=5)]
    ficha = _montar(entradas=entradas)
    assert ficha.desempenho.radar.respostas == 1
    assert ficha.desempenho.anotado.respostas == 10     # Remedios fica fora
    assert ficha.desempenho.divisao() == "radar 100% em 1 · anotado 60% em 10"
    # Um assunto inteiro no escopo pede o minimo do assunto (10): 11 respostas medem.
    assert ficha.estado.minimo == amostra.PADRAO.do_nivel("assunto")
    assert ficha.prioridade.desempenho.valor == pytest.approx(1 - 7 / 11, abs=0.01)


# --- a importacao da parte escrita --------------------------------------------------

TAXONOMIA = arvore.Taxonomia(familias={"direito": ([DC], ["artigo", "inciso"]),
                                       "portugues": ([LP], ["regra gramatical"])},
                             elementos_comuns=["conceito"], tipos_de_questao=[],
                             materias_fora_do_edital=[], sinonimos_de_materia={})

BRUTA = {
    "tema": TEMA, "assunto": "Direitos e garantias fundamentais: direitos e garantias individuais e coletivos",
    "subassunto": "", "elemento": "CF, art. 5º, caput e incisos I a XVI",
    "tipo_elemento": "inciso", "nos": [VIDA, CASA, INTIMIDADE],
    "por_que_estes_nos": "o caput é outro assunto do edital",
    "ler_exatamente": "CF, art. 5º, caput e incisos I a XVI.",
    "como_pesquisar": ["artigo 5 incisos I a XVI"], "entender": ["igualdade"],
    "memorizar": ["XI: de dia, por ordem judicial"], "pegadinhas": [],
    "fonte_sugerida": "",
}


def _conferir(**mudar):
    bruta = {**BRUTA, **mudar}
    return fichas.conferir_escrita(bruta, tema=TEMA, materia=DC, caminhos=list(NIVEIS),
                                   niveis=NIVEIS, taxonomia=TAXONOMIA)


def test_a_ficha_certa_passa_e_sai_sem_procedencia_ate_importar():
    escrita = _conferir()
    assert escrita.nos == [VIDA, CASA, INTIMIDADE]
    assert escrita.modelo == ""          # quem escreve a procedencia e a importacao


@pytest.mark.parametrize("mudar, motivo", [
    ({"tema": "Art. 5º, incisos XVII a XLIX"}, "outro tema"),
    ({"assunto": "Direitos fundamentais"}, "não existe"),
    ({"assunto": "", "subassunto": "Inviolabilidade do domicílio"}, "subassunto sem assunto"),
    ({"tipo_elemento": "regra gramatical"}, "taxonomia"),
    ({"nos": [f"{DIREITOS} > Liberdade de reunião"]}, "não está na árvore"),
    ({"nos": [VOZES]}, "outra matéria"),
    ({"nos": [DC]}, "matéria inteira"),
    ({"nos": [CASA, CASA]}, "duas vezes"),
    ({"nos": [CASA, CASA_XI]}, "dentro de"),
    ({"por_que_estes_nos": ""}, "porquê"),
    ({"ler_exatamente": "art 5"}, "ler exatamente"),
    ({"como_pesquisar": []}, "como pesquisar"),
    ({"entender": ["", " "]}, "entender"),
    ({"memorizar": []}, "memorizar"),
    ({"pegadinhas": ["este inciso vai cair na prova"]}, "previsão"),
    ({"entender": ["a FEPESE sempre cobra o inciso XI"]}, "previsão"),
    ({"memorizar": ["a fepese costuma trocar dia por noite"]}, "previsão"),
])
def test_a_importacao_recusa(mudar, motivo):
    with pytest.raises(fichas.FichaRecusada, match=motivo):
        _conferir(**mudar)


def test_sem_no_que_sirva_e_resposta_valida_com_o_porque():
    escrita = _conferir(nos=[], por_que_estes_nos="o programa de 2019 não lista o tema")
    assert escrita.nos == []


# --- o arquivo e a importacao no banco de teste ------------------------------------

@pytest.fixture
def arvore_no_banco(banco_temporario):
    from radar.db import sessao
    from radar.models import Conteudo

    with sessao() as s:
        for caminho, nivel in NIVEIS.items():
            nomes = arvore.partes(caminho)
            s.add(Conteudo(caminho=caminho, pai=arvore.SEPARADOR.join(nomes[:-1]) or None,
                           nivel=nivel, nome=nomes[-1], origem="edital", procedencia="teste"))


PEDIDO = [{"id": "f1", "tema": TEMA, "materia": DC}]


def test_importar_grava_com_a_procedencia(arvore_no_banco):
    resultado = servico_fichas.importar_respostas(
        PEDIDO, [{"id": "f1", "ficha": BRUTA}], "Claude Code, importado manualmente, em 02/10/2026")
    assert resultado["gravadas"] == 1 and not resultado["recusas"]
    (gravada,) = servico_fichas.carregar()
    assert gravada.modelo.startswith("Claude Code")
    assert gravada.criado_em
    assert gravada.conferida_em is None


def test_importar_recusa_pedido_que_nao_existe_e_resposta_repetida(arvore_no_banco):
    resultado = servico_fichas.importar_respostas(
        PEDIDO, [{"id": "f9", "ficha": BRUTA}, {"id": "f1", "ficha": BRUTA},
                 {"id": "f1", "ficha": BRUTA}, ], "modelo")
    assert resultado["gravadas"] == 1
    assert any("f9" in r for r in resultado["recusas"])
    assert any("duas vezes" in r for r in resultado["recusas"])


def test_a_ficha_conferida_nao_e_sobrescrita_e_a_nao_conferida_e(arvore_no_banco):
    servico_fichas.importar_respostas(PEDIDO, [{"id": "f1", "ficha": BRUTA}], "primeira")
    segunda = {**BRUTA, "entender": ["outra coisa"]}
    r = servico_fichas.importar_respostas(PEDIDO, [{"id": "f1", "ficha": segunda}], "segunda")
    assert r["substituidas"] == 1
    assert servico_fichas.carregar()[0].entender == ["outra coisa"]

    conferida = servico_fichas.conferir(TEMA, date(2026, 10, 2))
    assert conferida.conferida_em == "2026-10-02"
    assert conferida.modelo == "segunda"           # conferir nao reescreve quem escreveu
    r = servico_fichas.importar_respostas(PEDIDO, [{"id": "f1", "ficha": BRUTA}], "terceira")
    assert r["gravadas"] == 0
    assert "já conferiu" in r["recusas"][0]


def test_ficha_sem_procedencia_no_arquivo_nao_e_lida(banco_temporario):
    servico_fichas.caminho_do_arquivo().write_text(json.dumps([
        {**BRUTA, "materia": DC, "modelo": "", "criado_em": "2026-10-02"},
        {**BRUTA, "tema": "Outro", "materia": DC, "modelo": "manual", "criado_em": "2026-10-02"},
    ], ensure_ascii=False), encoding="utf-8")
    assert [e.tema for e in servico_fichas.carregar()] == ["Outro"]


def test_o_pedido_leva_os_temas_sem_ficha_com_a_arvore(arvore_no_banco, monkeypatch):
    plano = _plano()
    monkeypatch.setattr(cronograma, "carregar", lambda caminho=None: plano)
    lote = manual.pedido_de_fichas(desde=date(2026, 10, 2))
    assert lote["tipo"] == "fichas"
    temas = [p["tema"] for p in lote["pedidos"]]
    # Na ordem do calendario: o sabado de 03/10, e os dois de 06/10.
    assert temas == ["Princípios de contagem", TEMA, "Art. 5º, incisos XVII a XLIX"]
    art5 = next(p for p in lote["pedidos"] if p["tema"] == TEMA)
    assert {n["caminho"] for n in art5["arvore"]} == {c for c in NIVEIS if c.startswith(DC)}
    assert [a["artigos"] for a in art5["artigos_chave"]] == ["CF art. 5º, XI", "CF art. 5º, XII"]
    assert "NAO afirme o que a FEPESE faz" in art5["instrucao"]
    # Com a ficha gravada, o tema sai do pedido.
    servico_fichas.importar_respostas(PEDIDO, [{"id": "f1", "ficha": BRUTA}], "modelo")
    temas_depois = [p["tema"] for p in manual.pedido_de_fichas(desde=date(2026, 10, 2))["pedidos"]]
    assert TEMA not in temas_depois


def test_o_importar_do_manual_reconhece_o_lote_de_fichas(arvore_no_banco, tmp_path, monkeypatch):
    plano = _plano()
    monkeypatch.setattr(cronograma, "carregar", lambda caminho=None: plano)
    lote = manual.pedido_de_fichas(desde=date(2026, 10, 2))
    pedido = manual.salvar_pedido(lote, tmp_path / "pedido.json")
    ident = next(p["id"] for p in lote["pedidos"] if p["tema"] == TEMA)
    resposta = tmp_path / "resposta.json"
    resposta.write_text(json.dumps({"lote": lote["lote"], "respostas": [
        {"id": ident, "ficha": BRUTA}]}, ensure_ascii=False), encoding="utf-8")
    resultado = manual.importar(resposta, pedido)
    assert resultado["tipo"] == "fichas"
    assert resultado["gravadas"] == 1
    assert resultado["modelo"].startswith("Claude Code, importado manualmente")


# --- a tela e o terminal ----------------------------------------------------------

@pytest.fixture
def com_ficha_real(arvore_no_banco):
    """A ficha do Art. 5º gravada no arquivo do banco de teste. O cronograma e o
    REAL (config/cronograma.yml): o tema existe nele em 29/09, 06/10 e 29/10."""
    servico_fichas.importar_respostas(PEDIDO, [{"id": "f1", "ficha": BRUTA}],
                                      "Claude Code, importado manualmente, em 02/10/2026")


def test_a_pagina_da_ficha_mostra_tudo_com_o_selo_e_sem_previsao(com_ficha_real):
    cliente = TestClient(app)
    pagina = cliente.get("/fichas/art-5o-caput-e-incisos-i-a-xvi?data=2026-10-29")
    assert pagina.status_code == 200
    html = pagina.text
    assert "🟣" in html and "Claude Code, importado manualmente, em 02/10/2026" in html
    assert "O cronograma de 29/10 traz este tema: R+30" in html
    assert "Não há evidência suficiente no acervo para afirmar isso." in html
    assert "Polícia Penal SC:" in html and "Acervo complementar FEPESE" in html
    assert "Gerada por IA: não é questão oficial da FEPESE." in html
    assert "Conferi esta ficha" in html
    assert not PREVISAO.search(html)
    assert "<script" not in html


def test_o_selo_de_cada_parte_sai_da_origem_do_campo(com_ficha_real, monkeypatch):
    """A tela nao escolhe a cor (Etapa 7A): trocada a origem de um campo no
    dado, o selo daquela parte troca junto."""
    monkeypatch.setattr(fichas, "ORIGEM_DO_CAMPO",
                        {**fichas.ORIGEM_DO_CAMPO, "geradas": origem.OFICIAL})

    html = TestClient(app).get("/fichas/art-5o-caput-e-incisos-i-a-xvi?data=2026-10-29").text

    assert re.search(r'ds-selo--oficial ds-selo--curto"[^>]*>🟢</span> Questões geradas por IA', html)


def test_ficha_que_nao_existe_e_404(com_ficha_real):
    assert TestClient(app).get("/fichas/nao-existe").status_code == 404


def test_conferir_pela_tela_marca_e_volta(com_ficha_real):
    cliente = TestClient(app)
    resposta = cliente.post("/fichas/art-5o-caput-e-incisos-i-a-xvi/conferir",
                            data={"data": "2026-10-29"}, follow_redirects=False)
    assert resposta.status_code == 303
    assert resposta.headers["location"] == "/fichas/art-5o-caput-e-incisos-i-a-xvi?data=2026-10-29"
    assert servico_fichas.carregar()[0].conferida_em
    assert "Conferida por você" in cliente.get(resposta.headers["location"]).text


def test_a_lista_das_fichas_mostra_quem_tem_e_quem_falta(com_ficha_real, monkeypatch):
    from radar.servico import cronograma as diario

    monkeypatch.setattr(diario, "hoje_local", lambda: date(2026, 10, 2))
    html = TestClient(app).get("/fichas").text
    assert TEMA in html
    assert "sem ficha" in html            # os outros temas do cronograma real
    assert "Polícia Penal SC:" in html


def test_a_tela_hoje_leva_a_ficha_nas_faixas_do_tema(com_ficha_real):
    html = TestClient(app).get("/hoje?data=2026-10-06").text
    # O R+7 de 06/10 e do Art. 5º, I a XVI: o link aparece uma vez, nele.
    assert html.count("/fichas/art-5o-caput-e-incisos-i-a-xvi?data=2026-10-06") == 1
    assert "Ficha de estudo" in html


def test_o_terminal_mostra_a_ficha_e_o_radar_hoje_aponta_para_ela(com_ficha_real):
    runner = CliRunner()
    saida = runner.invoke(cli, ["fichas", "--tema", "art-5o-caput-e-incisos-i-a-xvi",
                                "--data", "2026-10-29"])
    assert saida.exit_code == 0, saida.output
    texto = saida.output
    for secao in ("Por que agora", "Fonte principal", "O que ler exatamente",
                  "Como pesquisar", "Você precisa entender", "Você precisa memorizar",
                  "Pegadinhas", "Como a FEPESE cobrou", "Questões reais relacionadas",
                  "Quantas questões fazer", "Erros para revisar", "Quando revisar",
                  "Meu desempenho"):
        assert secao in texto, secao
    assert "🟣" in texto
    assert "Não há evidência suficiente no acervo para afirmar isso." in texto
    assert not PREVISAO.search(texto)

    hoje = runner.invoke(cli, ["hoje", "--data", "2026-10-06"])
    assert "📋" in hoje.output
    assert "radar fichas --tema art-5o-caput-e-incisos-i-a-xvi" in hoje.output


def test_conferir_pelo_terminal(com_ficha_real):
    saida = CliRunner().invoke(cli, ["fichas", "--conferir", TEMA])
    assert saida.exit_code == 0
    assert servico_fichas.carregar()[0].conferida_em
    assert CliRunner().invoke(cli, ["fichas", "--conferir", "nada"]).exit_code == 1


# --- os arquivos reais --------------------------------------------------------------

RAIZ = Path(__file__).resolve().parents[1]


def _reais():
    arquivo = RAIZ / "data" / "fichas.json"
    return servico_fichas.carregar(arquivo)


def test_as_fichas_reais_passam_na_conferencia_contra_a_arvore_real():
    """O data/fichas.json versionado: toda ficha tem procedencia, e passaria de
    novo pela importacao contra a arvore real (data/conteudos.json)."""
    linhas = json.loads((RAIZ / "data" / "conteudos.json").read_text(encoding="utf-8"))
    niveis = {l["caminho"]: l["nivel"] for l in linhas}
    taxonomia = arvore.carregar_taxonomia()
    reais = _reais()
    assert reais, "o data/fichas.json real está vazio"
    for escrita in reais:
        assert escrita.modelo and escrita.criado_em
        fichas.conferir_escrita(escrita.para_dict(), tema=escrita.tema,
                                materia=escrita.materia, caminhos=list(niveis),
                                niveis=niveis, taxonomia=taxonomia)


def test_todo_tema_do_resto_do_ciclo_1_tem_ficha():
    """O que a Etapa 6B entregou: de 02/10 a 07/11, nenhum tema de estudo do
    cronograma real ficou sem ficha."""
    plano = cronograma.carregar()
    temas = fichas.temas_do_plano(plano, date(2026, 10, 2))
    com_ficha = {(e.chave, e.materia) for e in _reais()}
    faltam = [t.tema for t in temas if (fichas.chave_do_tema(t.tema), t.materia) not in com_ficha]
    assert not faltam, faltam
