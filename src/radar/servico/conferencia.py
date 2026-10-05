"""A conferencia dos dias ja gravados (Etapa 1D): o que esta no banco bate
com a regra do `servico.metricas`?

A 1C mudou a conta, e nao mexeu em dado nenhum. Ficou a pergunta do pedido
(secao 17): o que foi gravado antes dela precisa de correcao? Esta conferencia
responde dia a dia, e SO LE. Quem corrige e o `aplicar`, e so depois de eu
aprovar o que a conferencia mostrou - com copia de seguranca antes.

O que ela procura, em cada dia do ciclo:

- o registro do dia (a copia "31 questoes, 13 acertos" de antes da 1C)
  contra a conta da regra;
- faixa de questoes marcada com 0 questoes - a unica coisa que o `aplicar`
  corrige sozinho: a faixa sai de "feita" (regra decidida na 1D);
- faixa ou estudo extra com mais acertos do que questoes;
- treino de IA no dia, so para ficar dito que ele esta no volume;
- resposta a questao que a banca anulou;
- check orfao: o titulo nao bate mais com o config/cronograma.yml, e por isso
  ele nao conta em lugar nenhum;
- dia que esta no banco e nao esta no JSON (ou esta diferente). O JSON e a
  unica copia do diario fora do radar.db; o `aplicar` termina exportando.

O que nao e correcao automatica fica so no relatorio, com a proposta escrita:
numero digitado errado quem corrige sou eu, na tela.
"""
import shutil
import sqlite3
from contextlib import closing
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy import select

from radar import acervo, config
from radar import cronograma as plano_de_estudo
from radar.db import criar_tabelas, sessao
from radar.models import EstadoDoDia, QuestaoDeProva, RespostaDeSimulado, agora
from radar.servico import cronograma as diario
from radar.servico import extra as estudo_extra
from radar.servico import metricas

REGISTRO = "registro do dia"
ZERO = "faixa feita com 0 questões"
ACERTO_MAIOR = "acertos maiores que as questões"
TREINO_IA = "treino de IA"
ANULADA = "resposta a questão anulada"
ORFAO = "check órfão"
JSON = "JSON do diário"


@dataclass
class Achado:
    """Uma linha do relatorio: o que esta gravado, o que a regra diz, e o que
    fazer."""
    tipo: str
    gravado: str
    regra: str
    proposta: str
    #: True so no que o `aplicar` corrige sozinho. O resto pede a minha mao.
    corrige: bool = False
    #: O check que sai, quando o achado e uma faixa feita com 0 questoes.
    check: dict | None = None


@dataclass
class DiaConferido:
    data: date
    achados: list[Achado] = field(default_factory=list)
    #: A linha "N questoes = ..." da regra, ou o motivo de ela nao fechar.
    conta: str = ""
    minutos: int = 0
    #: Havia alguma coisa gravada neste dia?
    gravado: bool = False

    @property
    def a_corrigir(self) -> list[Achado]:
        return [a for a in self.achados if a.corrige]


def _faixa_do_check(montado, check: dict):
    """A faixa do dia montado na posicao do check, ou None se ela nao existe."""
    bloco, indice = check.get("bloco"), check.get("indice")
    if montado is None or bloco not in plano_de_estudo.TODOS_OS_BLOCOS:
        return None
    faixas = getattr(montado, bloco)
    if not isinstance(indice, int) or not 0 <= indice < len(faixas):
        return None
    return faixas[indice]


def _achados_das_faixas(plano, data: date, estado: EstadoDoDia) -> list[Achado]:
    montado = (metricas.dia_para_contar(plano, data, estado)
               if plano.dia(data) is not None else None)
    valores = diario.valores_das_faixas(montado, estado)
    achados = []
    for check in estado.faixas_feitas or []:
        titulo = check.get("titulo") or "(sem título)"
        faixa = _faixa_do_check(montado, check)
        feita = valores.get((check.get("bloco"), check.get("indice")))
        if faixa is None or feita is None or feita.titulo != check.get("titulo"):
            achados.append(Achado(
                ORFAO,
                gravado=f"{titulo!r} em {check.get('bloco')} {check.get('indice')}",
                regra="não bate com o cronograma de hoje: não conta em nada",
                proposta="nada: fica guardado como história do dia",
            ))
            continue
        if plano_de_estudo.tem_acerto(faixa) and not feita.questoes:
            achados.append(Achado(
                ZERO,
                gravado=f"{titulo}: feita, 0 questões, {feita.minutos} min",
                regra="faixa de questões sem questão não é feita",
                proposta=f"desmarcar a faixa: saem {feita.minutos} min do dia",
                corrige=True, check=check,
            ))
        if feita.acertos is not None and feita.acertos > (feita.questoes or 0):
            achados.append(Achado(
                ACERTO_MAIOR,
                gravado=f"{titulo}: {feita.acertos} acertos em {feita.questoes or 0}",
                regra="acerto nunca passa das questões",
                proposta="corrigir os números da faixa na tela Hoje",
            ))
    return achados


def _achados_dos_extras(data: date) -> list[Achado]:
    return [
        Achado(
            ACERTO_MAIOR,
            gravado=f"estudo extra #{e.id}: {e.acertos} acertos em {e.questoes or 0}",
            regra="acerto nunca passa das questões",
            proposta="corrigir o estudo extra na tela Hoje",
        )
        for e in estudo_extra.entre(data, data)
        if e.acertos is not None and e.acertos > (e.questoes or 0)
    ]


def _achados_das_anuladas(data: date) -> list[Achado]:
    """Resposta dada a uma questao que hoje esta anulada.

    A questao anulada nao sai mais no sorteio, mas a resposta antiga ficou, e
    conta como acerto ou erro. Nao ha correcao automatica: decidir se ela sai
    do acerto e uma regra nova, e regra nova eu decido antes.
    """
    comeco, termino = metricas.janela_do_dia(data)
    with sessao() as s:
        linhas = s.execute(
            select(RespostaDeSimulado, QuestaoDeProva)
            .join(QuestaoDeProva, QuestaoDeProva.id == RespostaDeSimulado.questao_id)
            .where(RespostaDeSimulado.gerada.is_(False))
            .where(RespostaDeSimulado.respondida_em >= comeco)
            .where(RespostaDeSimulado.respondida_em < termino)
            .where(QuestaoDeProva.anulada.is_(True))
        ).all()
    return [
        Achado(
            ANULADA,
            gravado=(f"simulado #{r.simulado_id}: questão {q.numero} de {q.ano}, "
                     f"{'certa' if r.acertou else 'errada'}"),
            regra="a banca anulou a questão; a resposta conta no acerto",
            proposta="nada automático: decidir se a resposta sai do acerto",
        )
        for r, q in linhas
    ]


def _achado_do_registro(registro, conta: metricas.Conta | None) -> Achado:
    if registro.questoes_feitas is None and registro.acertos is None:
        gravado, proposta = f"meta {registro.meta}, sem número", "nada"
    else:
        gravado = (f"meta {registro.meta}, {registro.questoes_feitas} questões, "
                   f"{registro.acertos} acertos")
        bate = conta is not None and (
            registro.questoes_feitas == conta.total.questoes
            and registro.acertos == conta.total.acertos)
        proposta = ("nada: a cópia bate com a regra" if bate else
                    "nada no dado: a cópia fica guardada e não aparece; vale a regra")
    regra = (metricas.frase_da_conta(conta.total) if conta is not None
             else "a conta do dia não fecha (veja abaixo)")
    return Achado(REGISTRO, gravado=gravado, regra=regra, proposta=proposta)


def _achados_do_json(data: date, registro, estado, no_arquivo: dict,
                     estados_no_arquivo: dict) -> list[Achado]:
    """O dia do banco contra o do JSON. So o que o banco tem e o JSON nao."""
    chave = data.isoformat()
    faltam = []
    if registro is not None:
        linha = no_arquivo.get(chave)
        if linha is None:
            faltam.append("o registro não está no JSON")
        elif (linha.get("meta"), linha.get("questoes_feitas"), linha.get("acertos"),
              linha.get("anotacao")) != (registro.meta, registro.questoes_feitas,
                                         registro.acertos, registro.anotacao):
            faltam.append("o registro está diferente no JSON")
    if estado is not None:
        linha = estados_no_arquivo.get(chave)
        if linha is None:
            faltam.append("os checks não estão no JSON")
        elif ((linha.get("faixas_feitas") or [], linha.get("plano_b"))
              != (list(estado.faixas_feitas or []), estado.plano_b)):
            faltam.append("os checks estão diferentes no JSON")
    if not faltam:
        return []
    return [Achado(
        JSON,
        gravado="; ".join(faltam),
        regra="o JSON é a única cópia do diário fora do radar.db",
        proposta="exportar o diário para o JSON",
        corrige=True,
    )]


def conferir(inicio: date | None = None, fim: date | None = None, *,
             plano=None, hoje: date | None = None) -> list[DiaConferido]:
    """Um `DiaConferido` por dia, de `inicio` a `fim` (padrao: o ciclo ate
    hoje). So le: nada muda no banco nem nos arquivos."""
    plano = plano or plano_de_estudo.carregar()
    hoje = hoje or diario.hoje_local()
    inicio = inicio or plano.inicio
    fim = fim or min(hoje, plano.fim)

    criar_tabelas()
    registros = diario.registros(inicio, fim)
    with sessao() as s:
        estados = {e.data: e for e in s.scalars(
            select(EstadoDoDia).where(EstadoDoDia.data >= inicio,
                                      EstadoDoDia.data <= fim))}
    registros_no_arquivo = acervo.registros_no_arquivo()
    estados_no_arquivo = acervo.estados_no_arquivo()

    dias = []
    data = inicio
    while data <= fim:
        dia = DiaConferido(data)
        registro, estado = registros.get(data), estados.get(data)
        linhas = metricas.lancamentos(data, data, plano)
        dia.gravado = bool(registro or estado or linhas)

        conta = None
        try:
            conta = metricas.contar(linhas)
            dia.conta = metricas.frase_da_conta(conta.total)
            dia.minutos = conta.minutos
        except metricas.ContaInconsistente as erro:
            # A conferencia existe para achar isto: ela mostra, e nao para.
            dia.conta = f"a conta não fecha: {erro}"

        if registro is not None:
            dia.achados.append(_achado_do_registro(registro, conta))
        if estado is not None:
            dia.achados += _achados_das_faixas(plano, data, estado)
        dia.achados += _achados_dos_extras(data)

        de_ia = [linha for linha in linhas if linha.gerada]
        if de_ia:
            # A conta e a do `metricas` (o treino de IA dele), e nao uma
            # recontagem aqui: resposta do radar nunca tem conta inconsistente.
            certas = metricas.contar(de_ia).treino_ia.ia_acertos
            dia.achados.append(Achado(
                TREINO_IA,
                gravado=f"{len(de_ia)} respostas a questão de IA ({certas} certas)",
                regra="conta no volume, nunca no acerto",
                proposta="nada",
            ))
        dia.achados += _achados_das_anuladas(data)
        dia.achados += _achados_do_json(data, registro, estado,
                                        registros_no_arquivo, estados_no_arquivo)
        dias.append(dia)
        data += timedelta(days=1)
    return dias


# --- aplicar: so depois do "pode" ------------------------------------------------

def caminho_das_copias() -> Path:
    return config.diretorio_dados() / "copias"


def copia_de_seguranca() -> Path:
    """Copia o radar.db e os dois JSON do diario para uma pasta com a hora.

    O banco vai pela API de backup do SQLite, e nao por copia de arquivo: com
    o `radar web` aberto, copiar o arquivo no meio de uma gravacao daria uma
    copia quebrada.
    """
    url = config.url_do_banco()
    if not url.startswith("sqlite:///"):
        raise RuntimeError("A cópia de segurança só sabe copiar banco SQLite.")
    banco = Path(url.removeprefix("sqlite:///"))

    pasta = caminho_das_copias() / f"conferencia-{diario.agora_local():%Y-%m-%d-%H%M%S}"
    pasta.mkdir(parents=True, exist_ok=False)
    with closing(sqlite3.connect(banco)) as origem, \
         closing(sqlite3.connect(pasta / banco.name)) as destino:
        origem.backup(destino)
    for arquivo in (acervo.caminho_dos_registros(), acervo.caminho_dos_estados()):
        if arquivo.exists():
            shutil.copy2(arquivo, pasta / arquivo.name)
    return pasta


def aplicar(dias: list[DiaConferido]) -> Path | None:
    """Corrige o que a conferencia marcou com `corrige`, e so isso.

    Devolve a pasta da copia de seguranca, ou None quando nao havia o que
    corrigir (e entao nada e copiado nem gravado).
    """
    a_corrigir = [(dia, achado) for dia in dias for achado in dia.a_corrigir]
    if not a_corrigir:
        return None

    pasta = copia_de_seguranca()
    with sessao() as s:
        for dia, achado in a_corrigir:
            if achado.tipo != ZERO:
                continue
            estado = s.scalar(select(EstadoDoDia).where(EstadoDoDia.data == dia.data))
            # Lista nova, e nao remove na velha: o SQLAlchemy so percebe que a
            # coluna JSON mudou quando o valor e trocado.
            estado.faixas_feitas = [c for c in estado.faixas_feitas or []
                                    if c != achado.check]
            estado.atualizado_em = agora()
    # Sempre por ultimo: o JSON fica igual ao banco ja corrigido.
    acervo.exportar_registros()
    acervo.exportar_estados()
    return pasta
