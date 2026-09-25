"""O historico de treino sai do radar.db e volta, sem perder nada.

Ate 25/09/2026 `simulados` e `respostas_de_simulado` eram as duas tabelas
sem copia: refazer o banco era perder cada resposta que eu ja tinha dado. O
teste que importa e o de ponta a ponta - exportar, jogar o banco fora,
reconstruir com as questoes em OUTRA numeracao e importar - porque o id da
questao muda quando o banco e refeito, e e ai que um backup ingenuo quebraria.
"""
import json
from datetime import datetime, timezone

from sqlalchemy import select

from radar import acervo, db
from radar.db import sessao
from radar.models import (
    QuestaoDeProva,
    QuestaoGerada,
    RespostaDeSimulado,
    Simulado,
)

CADERNO = "https://sap.exemplo.test/AP.pdf"
CRIADO = datetime(2026, 9, 20, 13, 0, tzinfo=timezone.utc)


def _questoes(deslocar: int = 0):
    """As mesmas duas questoes reais e uma gerada, com ids diferentes.

    `deslocar` poe questoes-lixo antes, para a numeracao do banco novo nao
    coincidir com a do velho por acaso.
    """
    with sessao() as s:
        for i in range(deslocar):
            s.add(QuestaoDeProva(
                prova_url="https://outro.test/x.pdf", numero=i + 1,
                enunciado=f"lixo {i}", impressao=f"lixo{i}",
            ))
            s.add(QuestaoGerada(
                modo="do_zero", enunciado=f"lixo {i}", impressao=f"glixo{i}",
            ))
        s.flush()
        for numero in (7, 8):
            s.add(QuestaoDeProva(
                prova_url=CADERNO, numero=numero, materia="Direito Penal",
                enunciado=f"questao {numero}", resposta="a",
                impressao=f"imp{numero}",
            ))
        s.add(QuestaoGerada(
            modo="variacao", enunciado="gerada", resposta="b",
            impressao="gerada1", modelo="claude-teste",
        ))


def _ids():
    with sessao() as s:
        reais = {
            q.numero: q.id for q in s.scalars(
                select(QuestaoDeProva).where(QuestaoDeProva.prova_url == CADERNO)
            )
        }
        gerada = s.scalar(
            select(QuestaoGerada.id).where(QuestaoGerada.impressao == "gerada1")
        )
    return reais, gerada


def _rodada():
    """Duas rodadas, como o radar as cria: uma de prova (uma certa, uma
    errada) e uma de geradas, ainda em branco - as duas nunca se misturam."""
    reais, gerada = _ids()
    with sessao() as s:
        sim = Simulado(criado_em=CRIADO, filtros={"materias": ["Direito Penal"]})
        das_geradas = Simulado(
            criado_em=CRIADO.replace(hour=14), filtros={"geradas": True}
        )
        s.add_all([sim, das_geradas])
        s.flush()
        s.add_all([
            RespostaDeSimulado(
                simulado_id=sim.id, questao_id=reais[7], ordem=1,
                escolhida="a", acertou=True,
                respondida_em=datetime(2026, 9, 20, 13, 5, tzinfo=timezone.utc),
            ),
            RespostaDeSimulado(
                simulado_id=sim.id, questao_id=reais[8], ordem=2,
                escolhida="c", acertou=False,
                respondida_em=datetime(2026, 9, 20, 13, 6, tzinfo=timezone.utc),
            ),
            RespostaDeSimulado(
                simulado_id=das_geradas.id, questao_id=gerada, ordem=1,
                gerada=True,
            ),
        ])


def _o_que_eu_respondi():
    """As rodadas descritas sem id nenhum: e isto que tem que sobreviver."""
    reais, _ = _ids()
    numero_do_id = {v: k for k, v in reais.items()}
    with sessao() as s:
        rodadas = []
        for sim in s.scalars(select(Simulado).order_by(Simulado.criado_em)):
            respostas = s.scalars(
                select(RespostaDeSimulado)
                .where(RespostaDeSimulado.simulado_id == sim.id)
                .order_by(RespostaDeSimulado.ordem)
            )
            rodadas.append((sim.criado_em, sim.finalizado_em, sim.filtros, [
                (
                    r.ordem,
                    "gerada" if r.gerada else numero_do_id[r.questao_id],
                    r.escolhida, r.acertou, r.respondida_em,
                )
                for r in respostas
            ]))
        return rodadas


def _banco_novo(tmp_path, monkeypatch, nome):
    monkeypatch.setenv("RADAR_DATABASE_URL", f"sqlite:///{tmp_path / nome}")
    db.resetar_engine()
    db.criar_tabelas()


def test_exportar_e_importar_preserva_a_rodada(banco_temporario, tmp_path,
                                              monkeypatch):
    _questoes()
    _rodada()
    antes = _o_que_eu_respondi()

    assert acervo.exportar_simulados() == 2

    # O radar.db foi perdido; as questoes voltam da extracao, com outros ids.
    _banco_novo(tmp_path, monkeypatch, "refeito.db")
    _questoes(deslocar=5)

    assert acervo.importar_simulados() == (2, 0)
    assert _o_que_eu_respondi() == antes


def test_importar_duas_vezes_nao_duplica(banco_temporario):
    _questoes()
    _rodada()
    acervo.exportar_simulados()

    assert acervo.importar_simulados() == (0, 0)
    with sessao() as s:
        assert len(list(s.scalars(select(Simulado)))) == 2
        assert len(list(s.scalars(select(RespostaDeSimulado)))) == 3


def test_sem_as_questoes_fica_de_fora_e_o_arquivo_nao_perde(
    banco_temporario, tmp_path, monkeypatch
):
    """Computador novo, antes do `radar questoes`: a rodada de prova nao
    entra pela metade, e o exportar seguinte nao a apaga do arquivo. A das
    geradas entra: a questao dela chegou pelo questoes_geradas.json."""
    _questoes()
    _rodada()
    acervo.exportar_simulados()
    arquivo_antes = json.loads(acervo.caminho_dos_simulados().read_text("utf-8"))

    _banco_novo(tmp_path, monkeypatch, "vazio.db")
    with sessao() as s:
        s.add(QuestaoGerada(modo="variacao", enunciado="gerada",
                            impressao="gerada1"))
    assert acervo.importar_simulados() == (1, 1)

    acervo.exportar_simulados()
    arquivo_depois = json.loads(acervo.caminho_dos_simulados().read_text("utf-8"))
    assert arquivo_depois == arquivo_antes


def test_importar_completa_sem_apagar(banco_temporario):
    """Simulado que ja existe aqui ganha a resposta que so o arquivo tem, e
    nao perde a que so o banco tem."""
    _questoes()
    _rodada()
    acervo.exportar_simulados()

    linhas = json.loads(acervo.caminho_dos_simulados().read_text("utf-8"))
    gerada = linhas[1]["respostas"][0]
    gerada.update(escolhida="b", acertou=True)
    acervo.caminho_dos_simulados().write_text(json.dumps(linhas), "utf-8")

    acervo.importar_simulados()

    escolhas = [
        resposta[:3] for rodada in _o_que_eu_respondi() for resposta in rodada[3]
    ]
    assert escolhas == [(1, 7, "a"), (2, 8, "c"), (1, "gerada", "b")]
