"""O Simulado da semana dos sabados leves: treina, nao mede (decisao 170).

De 24/10 em diante o sabado tem umas 2 horas, num bloco so, e o simulado de
35 a 40 questoes no Qconcursos virou um de 25, feito primeiro AQUI:

- **a composicao e a da decisao 69, em duas partes**: `questoes - anteriores`
  entre os temas da semana (de segunda a sexta: a semana do plano) e
  `anteriores` entre os temas de semanas anteriores. Cada parte e o
  `composicao.compor_por_tema` de sempre - com a janela da semana, ou antes
  dela;
- **cada tema sai primeiro do radar, so questao real**: as da FEPESE fora da
  reserva das rodadas que medem (decisao 167), depois as de outras bancas
  (decisao 166), as nunca feitas primeiro em todas. Questao gerada nao entra.
  So o que faltar vai para o Qconcursos, pelo link do tema;
- **e TREINO, e nao rodada que mede**: a faixa tem `treino`, o
  `composicao.mede` a recusa, e a rodada daqui (`simulado_da_semana`) nao
  esta nas `RODADAS_QUE_MEDEM`. Ela nao reserva questao, nao tira questao do
  fechamento de 07/11 e nao entra na comparacao. A resposta conta no acumulado
  do ciclo como qualquer questao real respondida no radar, com a origem ao
  lado; a parte feita no Qconcursos continua fora (decisao 146);
- **corrige no fim**, como simulado (`simulado.corrige_na_hora`).

A escolha e deterministica (a semente e a faixa: data, bloco e posicao), e a
rodada criada guarda o que escolheu: criada, ela nao e recriada.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, timedelta

from radar import conteudos as arvore
from radar.db import criar_tabelas, sessao
from radar.models import RespostaDeSimulado, Simulado
from radar.origem import AUTOMATICO
from radar.servico import composicao, evidencia, fepese_no_radar, outras_bancas

#: O nome da rodada em `Simulado.filtros`.
RODADA = "simulado_da_semana"

#: As duas partes da composicao.
SEMANA, ANTERIORES = "semana", "anteriores"

#: De onde veio a questao escolhida.
FEPESE, OUTRA_BANCA = "fepese", "outra_banca"

REGRA = ("decisão 170: a regra da 69 em duas partes (os temas da semana e os de "
         "antes), cada tema primeiro do radar, só questão real")


def aceita(faixa) -> bool:
    """O Simulado da semana: simulado com `treino` e as materias escritas."""
    return (faixa is not None and faixa.tipo == "simulado"
            and bool(getattr(faixa, "treino", False)) and bool(faixa.questoes)
            and bool(getattr(faixa, "materias_da_rodada", ())))


@dataclass
class TemaDoSimulado:
    """Um tema da composicao: quantas o plano pede e de onde elas saem."""

    parte: str                    # SEMANA ou ANTERIORES
    materia: str
    tema: str
    estudado_em: date | None
    pedidas: int
    fepese: int = 0               # reais da FEPESE do radar
    outras: int = 0               # reais de outras bancas do radar
    filtro: str | None = None     # o filtro escrito no plano, sem link do site
    sem_no: bool = False          # sem no, o radar nao acha questao do tema

    @property
    def do_radar(self) -> int:
        return self.fepese + self.outras

    @property
    def no_qconcursos(self) -> int:
        return max(self.pedidas - self.do_radar, 0)


@dataclass
class Escolhida:
    questao_id: int
    origem: str                   # FEPESE ou OUTRA_BANCA
    evidencia: str                # alvo | complementar | fora
    banca: str | None = None


@dataclass
class SimuladoDaSemana:
    """O que a tela Hoje e o `radar hoje` mostram no Simulado da semana."""

    tipo = "simulado_da_semana"
    origem = AUTOMATICO

    inicio_da_semana: date
    total: int
    anteriores: int
    temas: list[TemaDoSimulado]
    escolhidas: list[Escolhida] = field(default_factory=list)
    rodada_id: int | None = None
    regra: str = REGRA

    @property
    def da_parte_da_semana(self) -> int:
        """Quantas o plano pede dos temas da semana: o total menos as de antes."""
        return self.total - self.anteriores

    @property
    def da_semana(self) -> list[TemaDoSimulado]:
        return [t for t in self.temas if t.parte == SEMANA]

    @property
    def de_antes(self) -> list[TemaDoSimulado]:
        return [t for t in self.temas if t.parte == ANTERIORES]

    @property
    def do_radar(self) -> int:
        return sum(t.do_radar for t in self.temas)

    @property
    def no_qconcursos(self) -> int:
        return sum(t.no_qconcursos for t in self.temas)

    @property
    def fim_da_semana(self) -> date:
        """A sexta da semana: os temas da semana vao de segunda ate ela."""
        return self.inicio_da_semana + timedelta(days=4)

    def como_dicionario(self) -> dict:
        """O que a rodada grava: a regra e, por tema, quanto e de onde."""
        return {
            "regra": self.regra,
            "inicio_da_semana": self.inicio_da_semana.isoformat(),
            "total": self.total,
            "anteriores": self.anteriores,
            "temas": [{
                "parte": t.parte, "materia": t.materia, "tema": t.tema,
                "estudado_em": t.estudado_em.isoformat() if t.estudado_em else None,
                "pedidas": t.pedidas, "fepese": t.fepese, "outras": t.outras,
                "filtro": t.filtro, "sem_no": t.sem_no,
            } for t in self.temas],
        }


# --- a composicao ----------------------------------------------------------------

def inicio_da_semana(data: date, plano) -> date:
    """O primeiro dia da semana do plano de `data` - a segunda. E a semana do
    plano, e nao a do calendario, como na revisao do sabado (decisao 70)."""
    dia = plano.dia(data)
    if dia is not None:
        da_semana = [d.data for d in plano.dias if d.semana == dia.semana]
        if da_semana:
            return min(da_semana)
    return data - timedelta(days=data.weekday())


def _partes(data: date, faixa, plano, contexto) -> tuple[date, list]:
    """[(parte, Composicao)]: a da semana e a de antes, pela regra da 69."""
    inicio = inicio_da_semana(data, plano)
    anteriores = faixa.anteriores or 0
    materias = list(faixa.materias_da_rodada)
    partes = [(SEMANA, composicao.compor_por_tema(
        data, materias, faixa.questoes - anteriores, plano, contexto=contexto, desde=inicio))]
    if anteriores:
        partes.append((ANTERIORES, composicao.compor_por_tema(
            inicio, materias, anteriores, plano, contexto=contexto)))
    return inicio, partes


def _dentro(conteudo: str, nos: list[str]) -> bool:
    return any(conteudo == no or conteudo.startswith(no + arvore.SEPARADOR) for no in nos)


def escolher(partes: list, reserva: composicao.Reserva, estoque_fepese: dict,
             outras: list, feitas_reais: set[str], feitas_outras: set[str],
             semente: str) -> tuple[list[TemaDoSimulado], list[Escolhida]]:
    """Os temas com o que sai do radar, e as questoes escolhidas, em ordem.

    Em cada tema: as da FEPESE nunca feitas, as de outras bancas nunca feitas,
    e so entao as ja feitas (FEPESE antes) - refazer mede memoria. A FEPESE
    reservada para a rodada que mede nao entra. Uma questao uma vez so no
    simulado inteiro: dois temas podem ter o mesmo no."""
    sorteio = random.Random(semente)
    usadas_chave: set[str] = set()
    usadas_enunciado: set[str] = set()
    usadas_mesma: set[str] = set()
    temas: list[TemaDoSimulado] = []
    escolhidas: list[Escolhida] = []
    for parte, comp in partes:
        for materia in comp.materias:
            for a in materia.assuntos:
                if not a.pedidas:
                    continue
                tema = TemaDoSimulado(parte=parte, materia=materia.materia, tema=a.nome,
                                      estudado_em=a.estudado_em, pedidas=a.pedidas,
                                      filtro=a.filtro, sem_no=not a.nos)
                temas.append(tema)
                if not a.nos:
                    continue
                fep = [c for c in fepese_no_radar.do_tema(a.nos, estoque_fepese)
                       if c.chave not in reserva.chaves]
                ob = [c for c in outras if _dentro(c.conteudo, a.nos)]
                grupos = (
                    [(FEPESE, c) for c in fep if c.impressao not in feitas_reais],
                    [(OUTRA_BANCA, c) for c in ob if c.mesma not in feitas_outras],
                    [(FEPESE, c) for c in fep if c.impressao in feitas_reais],
                    [(OUTRA_BANCA, c) for c in ob if c.mesma in feitas_outras],
                )
                for grupo in grupos:
                    sorteio.shuffle(grupo)
                for origem, c in (par for grupo in grupos for par in grupo):
                    if tema.do_radar >= a.pedidas:
                        break
                    if c.chave in usadas_chave:
                        continue
                    if origem == FEPESE:
                        if c.impressao in usadas_enunciado:
                            continue
                        usadas_enunciado.add(c.impressao)
                        tema.fepese += 1
                        escolhidas.append(Escolhida(c.id, FEPESE, c.evidencia))
                    else:
                        if c.mesma in usadas_mesma:
                            continue
                        usadas_mesma.add(c.mesma)
                        tema.outras += 1
                        escolhidas.append(Escolhida(c.id, OUTRA_BANCA, evidencia.FORA, c.banca))
                    usadas_chave.add(c.chave)
    return temas, escolhidas


def _semente(data: date, bloco: str, indice: int) -> str:
    return f"{data.isoformat()}|{bloco}|{indice}|{RODADA}"


def planejar(data: date, bloco: str, indice: int, faixa, plano,
             contexto: composicao.Contexto | None = None) -> SimuladoDaSemana:
    """A composicao e as questoes do radar. NAO cria nada.

    Com a rodada ja criada, mostra o que foi GRAVADO nela: a de hoje pode ter
    mudado com uma classificacao nova, e a rodada continua sendo a que foi."""
    existente = composicao.rodada_da_faixa(data, bloco, indice, faixa)
    if existente is not None:
        return _da_rodada(existente)
    contexto = contexto or composicao.Contexto.ler(com_estoque=False)
    inicio, partes = _partes(data, faixa, plano, contexto)
    nos = sorted({no for _parte, comp in partes for m in comp.materias
                  for a in m.assuntos if a.pedidas for no in a.nos})
    temas, escolhidas = escolher(
        partes, composicao.reserva_das_que_medem(data, plano), composicao.estoque_real(),
        outras_bancas.estoque(nos), composicao.ja_respondidas(), outras_bancas.respondidas(),
        _semente(data, bloco, indice))
    return SimuladoDaSemana(inicio_da_semana=inicio, total=faixa.questoes,
                            anteriores=faixa.anteriores or 0, temas=temas,
                            escolhidas=escolhidas)


def _da_rodada(simulado: Simulado) -> SimuladoDaSemana:
    """O que a rodada gravou, de volta aos objetos da tela."""
    gravado = (simulado.filtros or {}).get(RODADA) or {}
    temas = [TemaDoSimulado(
        parte=t["parte"], materia=t["materia"], tema=t["tema"],
        estudado_em=date.fromisoformat(t["estudado_em"]) if t.get("estudado_em") else None,
        pedidas=t["pedidas"], fepese=t.get("fepese", 0), outras=t.get("outras", 0),
        filtro=t.get("filtro"), sem_no=bool(t.get("sem_no")))
        for t in gravado.get("temas") or []]
    return SimuladoDaSemana(
        inicio_da_semana=date.fromisoformat(gravado["inicio_da_semana"]),
        total=gravado.get("total", 0), anteriores=gravado.get("anteriores", 0),
        temas=temas, rodada_id=simulado.id, regra=gravado.get("regra", REGRA))


def criar_rodada(data: date, bloco: str, indice: int, faixa, plano) -> Simulado | None:
    """A rodada com as questoes do radar, ou a que ja existe. None quando o
    radar nao tem questao nenhuma: o simulado fica todo no Qconcursos."""
    if not aceita(faixa):
        return None
    existente = composicao.rodada_da_faixa(data, bloco, indice, faixa)
    if existente is not None:
        return existente
    planejado = planejar(data, bloco, indice, faixa, plano)
    if not planejado.escolhidas:
        return None
    escolhidas = planejado.escolhidas
    criar_tabelas()
    with sessao() as s:
        simulado = Simulado(filtros={
            "quantidade": len(escolhidas),
            "rodada": RODADA,
            # A mesma identidade das rodadas da faixa: e por ela que a faixa
            # acha a rodada, e que o "Fiz hoje" conta o que eu respondi.
            "faixa": composicao.identidade_da_faixa(data, bloco, indice, faixa),
            RODADA: planejado.como_dicionario(),
            "proprias": sum(1 for e in escolhidas if e.evidencia == evidencia.ALVO),
            "da_banca": sum(1 for e in escolhidas if e.evidencia == evidencia.COMPLEMENTAR),
            "outras": sum(1 for e in escolhidas if e.origem == OUTRA_BANCA),
            "bancas": sorted({e.banca for e in escolhidas if e.banca}),
        })
        s.add(simulado)
        s.flush()
        for ordem, escolhida in enumerate(escolhidas, start=1):
            # So questao real: `gerada` fica no padrao, falso.
            s.add(RespostaDeSimulado(simulado_id=simulado.id,
                                     questao_id=escolhida.questao_id, ordem=ordem))
    return simulado


def das_faixas(blocos, data: date, plano) -> dict:
    """{(bloco, indice): SimuladoDaSemana} do dia. Dia sem ele nao conta nada."""
    if plano is None:
        return {}
    achadas = [(bloco.chave, indice, faixa) for bloco in blocos
               for indice, faixa in enumerate(bloco.faixas) if aceita(faixa)]
    if not achadas:
        return {}
    contexto = composicao.Contexto.ler(com_estoque=False)
    return {(chave, indice): planejar(data, chave, indice, faixa, plano, contexto)
            for chave, indice, faixa in achadas}
