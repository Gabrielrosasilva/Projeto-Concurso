"""Quem eu sou, para cruzar com o que o edital exige.

O radar ja sabia ONDE a prova e aplicada e o que o edital pede. Aqui ele junta
as duas pontas e responde a pergunta que interessa: **eu sirvo para esta
vaga?**

A regra que vale para o arquivo inteiro: **campo em branco quer dizer "nao
sei", e nao "nao tenho"**. Sem a minha idade, um edital com idade maxima nao
vira "inelegivel" - vira "a confirmar". Concluir a partir de campo vazio seria
o mesmo erro de chutar o anel de um concurso sem saber a cidade.

O arquivo e `config/perfil.yml`, como `regioes.yml`: nada de dado meu escrito
no codigo.
"""
from dataclasses import dataclass, field
from datetime import date
from functools import cache

import yaml

from radar import config
from radar.elegibilidade import Exigencias

ELEGIVEL, INELEGIVEL, A_CONFIRMAR = "elegivel", "inelegivel", "a_confirmar"


@dataclass
class Perfil:
    ano_de_nascimento: int | None = None
    escolaridade: str | None = None
    formacao: str | None = None
    cnh: list[str] = field(default_factory=list)

    @property
    def idade(self) -> int | None:
        if not self.ano_de_nascimento:
            return None
        return date.today().year - self.ano_de_nascimento


@cache
def carregar() -> Perfil:
    """Le config/perfil.yml. Arquivo ausente vira perfil vazio, e nao erro."""
    arquivo = config.diretorio_config() / "perfil.yml"
    if not arquivo.exists():
        return Perfil()

    dados = yaml.safe_load(arquivo.read_text(encoding="utf-8")) or {}
    cnh = dados.get("cnh") or []
    return Perfil(
        ano_de_nascimento=dados.get("ano_de_nascimento"),
        escolaridade=(dados.get("escolaridade") or "").strip().lower() or None,
        formacao=(dados.get("formacao") or "").strip() or None,
        cnh=[str(c).strip().upper() for c in cnh if str(c).strip()],
    )


def recarregar() -> None:
    """Esquece o que foi lido. Usado pelos testes e se voce editar o YAML."""
    carregar.cache_clear()


@dataclass
class Veredito:
    """Se eu sirvo para o concurso, e por que."""

    situacao: str = A_CONFIRMAR
    motivos: list[str] = field(default_factory=list)

    @property
    def motivo(self) -> str:
        return "; ".join(self.motivos)


# A ordem importa: quem tem superior tambem atende vaga de medio e de
# fundamental. O contrario nao vale.
ORDEM_DE_ESCOLARIDADE = ("fundamental", "medio", "superior")


def _atende_escolaridade(minha: str | None, exigidos: list[str]) -> bool | None:
    """Tenho escolaridade para alguma das vagas? None quando nao da para dizer."""
    if not minha or minha not in ORDEM_DE_ESCOLARIDADE or not exigidos:
        return None
    meu_nivel = ORDEM_DE_ESCOLARIDADE.index(minha)
    return any(
        exigido in ORDEM_DE_ESCOLARIDADE
        and ORDEM_DE_ESCOLARIDADE.index(exigido) <= meu_nivel
        for exigido in exigidos
    )


def avaliar(exigencias: Exigencias, quem: Perfil | None = None) -> Veredito:
    """Cruza o que o edital pede com quem eu sou.

    So diz `inelegivel` quando ha um fato que me barra - idade acima do teto do
    edital, ou nenhuma vaga no nivel que eu tenho. Falta de informacao nunca
    vira barreira: vira "a confirmar".
    """
    quem = quem or carregar()
    veredito = Veredito()

    if not exigencias.legivel:
        veredito.motivos.append("edital nao pode ser lido")
        return veredito

    # --- idade --------------------------------------------------------------
    if exigencias.idade_maxima and quem.idade:
        if quem.idade > exigencias.idade_maxima:
            veredito.situacao = INELEGIVEL
            veredito.motivos.append(
                f"idade {quem.idade} acima do teto de {exigencias.idade_maxima}"
            )
            return veredito
        veredito.motivos.append(f"idade {quem.idade} dentro do teto")
    elif exigencias.idade_maxima:
        veredito.motivos.append(
            f"edital poe teto de {exigencias.idade_maxima} anos e eu nao informei "
            "meu ano de nascimento"
        )

    # --- escolaridade -------------------------------------------------------
    atende = _atende_escolaridade(quem.escolaridade, exigencias.niveis)
    if atende is False:
        veredito.situacao = INELEGIVEL
        veredito.motivos.append("nenhuma vaga no nivel que eu tenho")
        return veredito
    if atende:
        veredito.situacao = ELEGIVEL
        atendidos = [
            nivel for nivel in exigencias.niveis
            if nivel in ORDEM_DE_ESCOLARIDADE
            and ORDEM_DE_ESCOLARIDADE.index(nivel)
            <= ORDEM_DE_ESCOLARIDADE.index(quem.escolaridade)
        ]
        veredito.motivos.append(
            f"tenho {quem.escolaridade}, que atende as vagas de "
            + ", ".join(atendidos)
        )
    else:
        veredito.motivos.append("escolaridade a confirmar")

    # --- CNH ----------------------------------------------------------------
    # Nunca barra: um edital pede CNH em algumas vagas e nao em outras, e o
    # radar guarda um registro por concurso.
    if exigencias.cnh and exigencias.cnh != "sim":
        categorias = {c.strip() for c in exigencias.cnh.split() if c.strip().isalpha()}
        if quem.cnh and not (categorias & set(quem.cnh)):
            veredito.motivos.append(
                f"alguma vaga pede CNH {exigencias.cnh}, que eu nao tenho"
            )

    return veredito
