"""A Central de Macetes: um cartao por materia da minha prova.

O formato e o da especificacao, e cada parte do cartao carrega o selo de
onde veio - e nunca se mistura com a parte de outro selo:

  * a BASE: quantas questoes reais da materia, e de quais provas. So existem
    duas provas do cargo (2013 e 2019), e isso aparece como "base pequena";
  * 🟩 o PADRAO DA BANCA: contagem do `macetes.py` sobre essas questoes -
    como ela pergunta, que palavra mais aparece. Nada escrito por IA;
  * 🟥 o MACETE e a PEGADINHA: texto de IA, importado pelo caminho da parte 8
    (`radar gerar --pedido --macetes` / `--importar`), com a fonte legal ou
    gramatical e a procedencia. Macete sem fonte ou sem procedencia NAO
    aparece: a especificacao exige que todo conteudo 🟥 cite a fonte, e o
    arquivo e editavel a mao.

A questao real citada pelo macete abre numa pagina propria, com o selo de
questao extraida da prova e, quando `config/leis.yml` disser, o aviso de que
a lei mudou depois dela.
"""
from dataclasses import dataclass, field

from sqlalchemy import select

from radar import leis, macetes
from radar.db import criar_tabelas, sessao
from radar.models import QuestaoDeProva
from radar.regioes import normalizar
from radar.servico import manual

# Com menos provas que isto, a tendencia tirada delas leva o aviso "base
# pequena" (regra 4 da especificacao). Hoje sao duas.
PROVAS_PARA_TENDENCIA = 3


@dataclass
class MaceteDoCartao:
    regra: str
    fonte: str
    pegadinha: str | None
    assunto: str | None
    procedencia: str
    impressao: str
    questoes: int
    #: As leis posteriores que atingem alguma das questoes em que o macete
    #: se apoia. O macete foi escrito sobre elas, e herda o aviso.
    mudancas: list = field(default_factory=list)


@dataclass
class Cartao:
    materia: str
    questoes: int
    anos: list[int]
    comandos: list = field(default_factory=list)
    termos: list = field(default_factory=list)
    lei: "leis.Lei | None" = None
    macetes: list[MaceteDoCartao] = field(default_factory=list)
    com_lei_mudada: int = 0

    @property
    def base_pequena(self) -> bool:
        return len(self.anos) < PROVAS_PARA_TENDENCIA

    @property
    def de_onde(self) -> str:
        """"provas 2013 e 2019", para a frase da base."""
        if not self.anos:
            return "nenhuma prova"
        nomes = [str(a) for a in self.anos]
        juntos = nomes[0] if len(nomes) == 1 else (
            ", ".join(nomes[:-1]) + " e " + nomes[-1]
        )
        return ("prova " if len(nomes) == 1 else "provas ") + juntos


def _texto(questao) -> str:
    alternativas = " ".join(str(v) for v in (questao.alternativas or {}).values())
    return f"{questao.enunciado} {alternativas}"


def mudancas_da(questao) -> list:
    return leis.mudancas_da_questao(questao.ano, questao.materia, _texto(questao))


def _questoes_do_alvo() -> list[QuestaoDeProva]:
    """As questoes validas da MINHA prova: cargo e estado, sem as anuladas.

    A pergunta "e a minha prova?" e a do Meu foco, e nao uma copia dela. O
    reforco (2016) fica de fora: ele e outro cargo, e o cartao diz o que a
    banca cobra de MIM.
    """
    from radar.foco import _provas_do_alvo

    criar_tabelas()
    with sessao() as s:
        return list(s.scalars(
            select(QuestaoDeProva)
            .where(QuestaoDeProva.prova_url.in_(_provas_do_alvo(s)))
            .where(QuestaoDeProva.anulada.is_not(True))
            .order_by(QuestaoDeProva.ano, QuestaoDeProva.numero)
        ))


def _chave_da_questao(prova_url: str, numero: int) -> tuple:
    return (prova_url, int(numero))


def _macete_aparece(macete: dict) -> bool:
    """So entra na tela o macete com fonte e com procedencia."""
    return bool((macete.get("fonte") or "").strip()) and bool(
        (macete.get("modelo") or "").strip()
    ) and bool(macete.get("criado_em"))


def cartoes() -> list[Cartao]:
    """Um cartao por materia da minha prova, da que tem mais questao a menos."""
    questoes = _questoes_do_alvo()
    por_materia: dict[str, list] = {}
    for q in questoes:
        por_materia.setdefault(q.materia or "sem materia", []).append(q)
    por_chave = {_chave_da_questao(q.prova_url, q.numero): q for q in questoes}

    importados = [m for m in manual.carregar_macetes() if _macete_aparece(m)]

    resultado = []
    for materia, lista in por_materia.items():
        cartao = Cartao(
            materia=materia,
            questoes=len(lista),
            anos=sorted({q.ano for q in lista if q.ano}),
            comandos=macetes.contar_comandos(lista)[:3],
            termos=macetes.termos_frequentes(lista, 6),
            lei=leis.da_materia(materia),
            com_lei_mudada=sum(1 for q in lista if mudancas_da(q)),
        )
        for m in importados:
            if normalizar(m.get("materia") or "") != normalizar(materia):
                continue
            citadas = [
                por_chave[chave] for chave in (
                    _chave_da_questao(c["prova_url"], c["numero"])
                    for c in m.get("questoes") or []
                ) if chave in por_chave
            ]
            vistas, mudancas = set(), []
            for q in citadas:
                for mudanca in mudancas_da(q):
                    if mudanca not in vistas:
                        vistas.add(mudanca)
                        mudancas.append(mudanca)
            cartao.macetes.append(MaceteDoCartao(
                regra=m["regra"], fonte=m["fonte"],
                pegadinha=m.get("pegadinha") or None,
                assunto=m.get("assunto") or None,
                procedencia=m["modelo"], impressao=m["impressao"],
                questoes=len(citadas), mudancas=mudancas,
            ))
        resultado.append(cartao)

    return sorted(resultado, key=lambda c: (-c.questoes, c.materia))


@dataclass
class QuestaoRelacionada:
    questao: QuestaoDeProva
    mudancas: list


def questoes_do_macete(impressao: str) -> tuple[dict, list] | None:
    """O macete e as questoes REAIS em que ele se apoia, ou None.

    E o destino do link [Ver questoes reais relacionadas]: ali o 🟥 encontra o
    🟦, e eu confiro o macete contra a prova de verdade.
    """
    macete = next(
        (m for m in manual.carregar_macetes()
         if m.get("impressao") == impressao and _macete_aparece(m)),
        None,
    )
    if macete is None:
        return None

    criar_tabelas()
    relacionadas = []
    with sessao() as s:
        for citada in macete.get("questoes") or []:
            questao = s.scalar(
                select(QuestaoDeProva)
                .where(QuestaoDeProva.prova_url == citada.get("prova_url"))
                .where(QuestaoDeProva.numero == citada.get("numero"))
            )
            if questao is not None:
                relacionadas.append(QuestaoRelacionada(questao, mudancas_da(questao)))
    return macete, relacionadas
