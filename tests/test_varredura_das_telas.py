"""A varredura das telas (Etapa 7A): as regras do novo.md, em toda tela.

Uma base pequena com o que as telas mostram - a minha prova, questao real
respondida certa e errada, rodada de questao gerada, questao gerada aberta,
faixa anotada no dia - e cada tela aberta com ela. Em todas:

  * nenhuma previsao (regra 2): "vai cair", "certamente", "sempre cobra"...;
  * questao de IA nunca sem o 🟣 e sem "nao e questao oficial da FEPESE"
    (regra 5);
  * nenhuma porcentagem sem a amostra ao lado (regra 3).

O relogio e a data de cada resposta sao fixos: o teste nao depende de hoje.
"""
import re
from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient

from radar import cronograma, origem
from radar.db import sessao
from radar.models import QuestaoDeProva, QuestaoGerada, RespostaDeSimulado, Simulado
from radar.servico import cronograma as diario
from radar.util import fuso_local
from radar.web.app import app
from tests.test_foco import CONCURSO_DE_2019, _concurso, com_quadro_do_edital  # noqa: F401

DIA = date(2026, 10, 20)
QUANDO = datetime(2026, 10, 19, 21, 0, tzinfo=fuso_local())

PREVISAO = re.compile(
    r"(?i)vai cair|v[ãa]o cair|devem? cair|cair[áa]\b|certamente|sempre cobra|com certeza"
)

#: As telas que leem o banco. Cada uma abre com a base de baixo.
TELAS = [
    "/", f"/hoje?data={DIA.isoformat()}", "/semanas", "/analises",
    "/analises/materias", "/analises/desempenho", "/analises/incidencia",
    "/simulado", "/geradas", "/macetes", "/macetes?banca=FEPESE", "/previsao",
    "/mais", "/concursos", "/erros?situacao=todos", "/fichas", "/revisao",
    "/acompanhando",
]

#: O texto da questao que a IA escreveu, para reconhecer onde ela aparece.
ENUNCIADO_DE_IA = "Enunciado escrito pela IA sobre a pena de detencao, para treinar?"


def _rodada(respostas, gerada=False) -> int:
    """Uma rodada com as respostas [(questao_id, letra ou None, acertou)]."""
    with sessao() as s:
        rodada = Simulado(filtros={"geradas": True} if gerada else {}, criado_em=QUANDO)
        s.add(rodada)
        s.flush()
        for ordem, (questao_id, letra, acertou) in enumerate(respostas, start=1):
            s.add(RespostaDeSimulado(
                simulado_id=rodada.id, questao_id=questao_id, gerada=gerada,
                ordem=ordem, escolhida=letra, acertou=acertou if letra else None,
                respondida_em=QUANDO if letra else None,
            ))
        return rodada.id


@pytest.fixture
def telas(banco_temporario, com_quadro_do_edital, monkeypatch):  # noqa: F811
    """{endereco: html} de todas as telas, e das tres paginas de rodada."""
    monkeypatch.setattr(diario, "agora_local", lambda: datetime(2026, 10, 20, 20, 0,
                                                                tzinfo=fuso_local()))
    with sessao() as s:
        s.add(_concurso())
        reais = [QuestaoDeProva(
            prova_url="https://fepese.test/ap2019.pdf", banca="FEPESE",
            concurso_url=CONCURSO_DE_2019, ano=2019, cargo="Agente Penitenciário",
            numero=n + 1, materia="Direito Penal", enunciado=f"Questao real {n}?",
            alternativas={"a": "x", "b": "y"}, resposta="a", impressao=f"real-{n}",
        ) for n in range(20)]
        geradas = [QuestaoGerada(
            modo="variacao", materia="Direito Penal", enunciado=ENUNCIADO_DE_IA,
            alternativas={letra: f"alternativa {letra}" for letra in "abcde"},
            resposta="c", impressao=f"ia-{n}", modelo="teste", rejeitada=False,
        ) for n in range(2)]
        s.add_all(reais + geradas)
        s.flush()
        ids_reais = [q.id for q in reais]
        ids_geradas = [q.id for q in geradas]

    # 12 certas e 8 erradas; uma de IA respondida errada; outra de IA aberta.
    real = _rodada([(q, "a" if n < 12 else "b", n < 12) for n, q in enumerate(ids_reais)])
    respondida = _rodada([(ids_geradas[0], "a", False)], gerada=True)
    aberta = _rodada([(ids_geradas[1], None, None)], gerada=True)

    plano = cronograma.carregar()
    montado = cronograma.montar_dia(plano, DIA, diario.nivel_do_dia(plano, DIA).efetivo)
    diario.anotar_faixa(DIA, "noite", 0, montado.noite[0].titulo, questoes=10,
                        acertos=7, plano=plano, hoje=DIA)

    cliente = TestClient(app)
    paginas = {}
    for endereco in TELAS + [f"/simulado/{real}", f"/simulado/{respondida}",
                             f"/simulado/{aberta}"]:
        resposta = cliente.get(endereco)
        assert resposta.status_code == 200, endereco
        paginas[endereco] = resposta.text
    return paginas


def _visivel(html: str) -> str:
    """O texto que a tela mostra: sem estilo, sem script, sem atributo."""
    html = re.sub(r"(?is)<(style|script)\b.*?</\1>", " ", html)
    html = re.sub(r"(?s)<!--.*?-->", " ", html)
    texto = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", texto)


def test_nenhuma_tela_fala_em_previsao(telas):
    for endereco, html in telas.items():
        achado = PREVISAO.search(_visivel(html))
        assert not achado, (endereco, achado and achado.group(0))


def test_questao_de_ia_nunca_aparece_sem_o_selo_e_a_frase(telas):
    """Onde o enunciado escrito pela IA aparece, o 🟣 e a frase da regra 5
    aparecem junto. A rodada de IA aberta e o relatorio dela, pelo menos."""
    com_questao_de_ia = [e for e, html in telas.items() if ENUNCIADO_DE_IA in html]
    assert len(com_questao_de_ia) >= 2, com_questao_de_ia
    for endereco in com_questao_de_ia:
        html = telas[endereco]
        assert "🟣" in html, endereco
        assert origem.FRASE_DA_QUESTAO_DE_IA in html, endereco


#: O que conta como amostra perto de uma porcentagem: "em 20", "de 20",
#: "(20)", "20 questões", "20 respostas", "2 provas"...
AMOSTRA = re.compile(
    r"\b(em|de|das|dos) \d+\b|\(\d+\)|\b\d+ (questões|questão|respostas|resposta"
    r"|provas|prova|erros|erro|vezes|cadernos|feitas|enunciados)\b"
)


def _tem_amostra(texto: str, inicio: int, fim: int) -> bool:
    em_volta = texto[max(0, inicio - 90):fim + 90]
    if AMOSTRA.search(em_volta):
        return True
    # Na tabela e no grafico, a base mora na celula ao lado: "15 | 15%"
    # (questoes do edital e o peso), "60% | 21" (o acerto e as questoes).
    return bool(re.search(r"\b\d+\s*$", texto[max(0, inicio - 12):inicio])
                or re.match(r"\s*\d+\b", texto[fim:fim + 12]))


def test_nenhuma_porcentagem_sem_a_amostra(telas):
    """Regra 3: toda estatistica mostra a amostra. Cada "N%" da tela tem, no
    trecho em volta, de quantas ele saiu."""
    sem_amostra, vistas = [], 0
    for endereco, html in telas.items():
        texto = _visivel(html)
        for achado in re.finditer(r"\d+(?:,\d+)?\s?%", texto):
            vistas += 1
            if not _tem_amostra(texto, achado.start(), achado.end()):
                sem_amostra.append((endereco, texto[max(0, achado.start() - 90):achado.end() + 90]))
    assert not sem_amostra, sem_amostra
    # A base de cima tem acerto medido: a varredura viu porcentagem de verdade.
    assert vistas >= 20, vistas
