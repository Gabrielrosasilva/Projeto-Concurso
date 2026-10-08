"""As carreiras que eu acompanho, lidas de config/acompanhamentos.yml.

Este arquivo so responde uma pergunta: **este item da coleta e de qual
carreira que eu acompanho?** Quem monta o cartao, conta novidade e guarda o
"visto" e o `servico/acompanhamentos.py`.

A regra e a do alvo.yml, e por isso ela mora la: os termos de cada carreira
sao os do bloco secundario de mesmo nome, e a Policia Penal e o alvo
principal que o classificador ja marcou. Aqui entram so as duas coisas que o
alvo.yml nao sabe - a CIDADE (as Guardas de Florianopolis e de BC) e o
ESTADO (Policia Civil, PM e Bombeiros de SC, e nao de qualquer lugar).

Nunca chutar vale aqui como vale no anel de distancia: item sem prova de que
e de SC fica fora do cartao que pede SC.
"""
from dataclasses import dataclass, field
from datetime import date
from functools import cache

import yaml

from radar import alvo as alvos
from radar import config, regioes
from radar.regioes import normalizar

#: O `cargo` que aponta o alvo principal, em vez de um bloco secundario.
PRINCIPAL = "principal"

#: Os aneis que so tem municipio de SC (config/regioes.yml). O `remoto` fica
#: fora: ele tambem e o anel do municipio de outro estado.
ANEIS_DE_SC = ("nucleo", "proximo", "estadual")


@dataclass(frozen=True)
class Acompanhamento:
    """Uma carreira que eu acompanho, como esta no YAML."""

    nome: str
    cargo: str
    termos: tuple[str, ...] = ()
    local: tuple[str, ...] = ()
    uf: str | None = None


@dataclass(frozen=True)
class Regras:
    """O arquivo inteiro: a lista e os numeros que valem para todos."""

    acompanhamentos: tuple[Acompanhamento, ...] = ()
    intervalo_minimo_minutos: int = 30
    janela_da_edicao_em_dias: int = 365
    novidades_desde: date | None = None
    telegram_desde: date | None = None
    fontes_oficiais: tuple[str, ...] = ()
    dominios_oficiais: tuple[str, ...] = ()
    fontes_de_sc: tuple[str, ...] = ()
    prova_de_sc: tuple[str, ...] = field(default=("santa catarina",))


class ErroNosAcompanhamentos(ValueError):
    """O YAML aponta para algo que nao existe. A mensagem diz o que."""


def _data(valor, chave: str) -> date | None:
    if valor in (None, ""):
        return None
    if isinstance(valor, date):
        return valor
    try:
        return date.fromisoformat(str(valor))
    except ValueError as erro:
        raise ErroNosAcompanhamentos(
            f"`{chave}` tem que ser uma data AAAA-MM-DD (veio {valor!r})"
        ) from erro


def _lista(valor) -> tuple[str, ...]:
    return tuple(str(v) for v in (valor or []) if str(v).strip())


@cache
def regras() -> Regras:
    """Le o YAML uma vez. Sem arquivo, nenhuma carreira - e nao erro."""
    arquivo = config.diretorio_config() / "acompanhamentos.yml"
    if not arquivo.exists():
        return Regras()
    dados = yaml.safe_load(arquivo.read_text(encoding="utf-8")) or {}

    lista = []
    nomes = set()
    for bruto in dados.get("acompanhamentos") or []:
        nome = str(bruto.get("nome") or "").strip()
        cargo = str(bruto.get("cargo") or "").strip()
        if not nome or not cargo:
            raise ErroNosAcompanhamentos(
                f"todo acompanhamento precisa de `nome` e `cargo` (veio {bruto!r})"
            )
        if nome in nomes:
            raise ErroNosAcompanhamentos(f"o acompanhamento {nome!r} aparece duas vezes")
        nomes.add(nome)
        termos = ()
        if cargo != PRINCIPAL:
            termos = tuple(alvos.termos_do_bloco(cargo)) + _lista(bruto.get("termos_extras"))
            if not alvos.termos_do_bloco(cargo):
                # Um nome errado aqui deixaria o cartao vazio para sempre, sem
                # ninguem perceber. Melhor parar e dizer onde.
                raise ErroNosAcompanhamentos(
                    f"{nome}: o cargo {cargo!r} nao e um bloco de `secundarios` "
                    f"do config/alvo.yml"
                )
        lista.append(Acompanhamento(
            nome=nome,
            cargo=cargo,
            termos=termos,
            local=_lista(bruto.get("local")),
            uf=(str(bruto["uf"]).upper() if bruto.get("uf") else None),
        ))

    return Regras(
        acompanhamentos=tuple(lista),
        intervalo_minimo_minutos=int(dados.get("intervalo_minimo_minutos") or 30),
        janela_da_edicao_em_dias=int(dados.get("janela_da_edicao_em_dias") or 365),
        novidades_desde=_data(dados.get("novidades_desde"), "novidades_desde"),
        telegram_desde=_data(dados.get("telegram_desde"), "telegram_desde"),
        fontes_oficiais=tuple(f.lower() for f in _lista(dados.get("fontes_oficiais"))),
        dominios_oficiais=tuple(d.lower().strip(".") for d in
                                _lista(dados.get("dominios_oficiais"))),
        fontes_de_sc=tuple(f.lower() for f in _lista(dados.get("fontes_de_sc"))),
        prova_de_sc=_lista(dados.get("prova_de_sc")) or ("santa catarina",),
    )


def recarregar() -> None:
    """Esquece o que foi lido. Usado pelos testes e se voce editar o YAML."""
    regras.cache_clear()
    alvos.recarregar()


def todos() -> tuple[Acompanhamento, ...]:
    return regras().acompanhamentos


def por_nome(nome: str) -> Acompanhamento | None:
    return next((a for a in todos() if a.nome == nome), None)


def e_de_sc(concurso) -> bool:
    """O item e de SC? A UF manda; sem UF, o anel, a fonte ou uma palavra.

    UF de outro estado tira o item sempre: "Sao Jose" e nome de municipio em
    varios lugares, e a fonte que disse o estado sabe mais que o nome.
    """
    uf = (getattr(concurso, "uf", None) or "").upper()
    if uf:
        return uf == "SC"
    if getattr(concurso, "relevancia", None) in ANEIS_DE_SC:
        return True
    if (getattr(concurso, "fonte", None) or "").lower() in regras().fontes_de_sc:
        return True
    return bool(alvos.primeiro_termo(regras().prova_de_sc, concurso.titulo,
                                     getattr(concurso, "resumo", None)))


def _no_local(acompanhamento: Acompanhamento, concurso) -> bool:
    """O item e da cidade do cartao: pelo municipio gravado, ou pelo texto."""
    municipio = getattr(concurso, "municipio", None)
    if municipio:
        nome = normalizar(regioes.nome_canonico(municipio) or municipio)
        if any(normalizar(lugar) == nome for lugar in acompanhamento.local):
            return True
    return bool(alvos.primeiro_termo(acompanhamento.local, concurso.titulo,
                                     getattr(concurso, "resumo", None)))


def casa(acompanhamento: Acompanhamento, concurso) -> bool:
    """Este item da coleta e desta carreira?"""
    if acompanhamento.cargo == PRINCIPAL:
        # A regra do alvo principal (o cargo, o orgao, a prova de SC) ja
        # rodou no classificador. Refazer aqui seria um segundo criterio que
        # podia discordar do primeiro.
        if getattr(concurso, "alvo", None) != alvos.PRINCIPAL:
            return False
    elif not alvos.primeiro_termo(acompanhamento.termos, concurso.titulo,
                                  getattr(concurso, "resumo", None)):
        return False

    if acompanhamento.local and not _no_local(acompanhamento, concurso):
        return False
    if acompanhamento.uf == "SC" and not e_de_sc(concurso):
        return False
    return True


def de_quais(concurso) -> list[Acompanhamento]:
    """As carreiras deste item. Pode ser mais de uma: um edital de Policia
    Militar e Bombeiros juntos e dos dois cartoes."""
    return [a for a in todos() if casa(a, concurso)]
