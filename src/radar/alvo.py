"""Os cargos que eu quero, lidos de config/alvo.yml.

O radar ja sabia ONDE a prova e aplicada e se eu sirvo para a vaga. Faltava a
pergunta mais simples de todas: **e o cargo que eu quero?**

Duas marcas, e elas nao valem a mesma coisa:

- `principal` e a Policia Penal SC. Para ela o cargo manda e a distancia nao
  importa, entao a marca passa por cima do filtro de anel e do teto de
  mensagens do Telegram. Vale ate para noticia, que normalmente nunca vira
  aviso: "governo autoriza concurso da Policia Penal" e exatamente o que eu
  nao posso perder.
- `secundario` e o resto da minha lista. Marca so para eu reconhecer o cargo;
  as regras de aviso continuam as mesmas.

A regra de ouro do projeto continua valendo aqui: **nunca chutar**. O alvo
principal e de Santa Catarina, entao sem prova de que o item e de SC a marca
nao sai - "SAP SP abre estagio" e "Policia Penal do Parana" estao no feed de
verdade, e nenhum dos dois e o meu concurso.
"""
import re
from dataclasses import dataclass
from functools import cache

import yaml

from radar import config
from radar.regioes import normalizar

PRINCIPAL, SECUNDARIO = "principal", "secundario"


@dataclass(frozen=True)
class Marca:
    """O que o texto bateu, e por que. O motivo vai para o banco e para o
    aviso: eu preciso poder auditar a marca, como faco com o anel."""

    alvo: str
    nome: str
    motivo: str


@cache
def _carregar() -> dict:
    """Le config/alvo.yml. Arquivo ausente vira lista vazia, e nao erro."""
    arquivo = config.diretorio_config() / "alvo.yml"
    if not arquivo.exists():
        return {}
    return yaml.safe_load(arquivo.read_text(encoding="utf-8")) or {}


def recarregar() -> None:
    """Esquece o que foi lido. Usado pelos testes e se voce editar o YAML."""
    _carregar.cache_clear()
    _padrao.cache_clear()


@cache
def _padrao(termo: str) -> re.Pattern:
    """O termo casado por PALAVRA INTEIRA.

    Sem a borda, a sigla "SAP" casa dentro de Sapezal, Sapiranga, Massape e
    SAPE/SC - os quatro ja apareceram na coleta, e nenhum tem a ver com o
    concurso que eu espero.
    """
    return re.compile(rf"\b{re.escape(normalizar(termo))}\b")


# O titulo da FEPESE gruda a lista de cargos no fim do nome do orgao:
# "Secretaria de Estado da Justica e CidadaniaAgente Penitenciario
# (masculino)Agente Penitenciario (feminino)...". Sem separar isso, nem o
# orgao nem o cargo casam, porque a palavra que a busca procura comeca colada
# na anterior. Vale so para minuscula seguida de MAIUSCULA: sigla grudada em
# sigla ("SAPE/SC") fica como esta.
MINUSCULA = "a-z" + chr(0xE0) + "-" + chr(0xFF)
MAIUSCULA = "A-Z" + chr(0xC0) + "-" + chr(0xDE)
GRUDADAS = re.compile(f"([{MINUSCULA}])([{MAIUSCULA}])")


def _primeiro(termos, texto: str) -> str | None:
    """O primeiro termo da lista que aparece no texto. None se nenhum aparece.

    Devolve o termo, e nao so True, porque e ele que vai escrito no motivo.
    """
    for termo in termos or []:
        if _padrao(str(termo)).search(texto):
            return str(termo)
    return None


def _e_do_estado(principal: dict, texto: str, uf: str | None) -> bool:
    """O item e mesmo do estado do alvo principal?

    Com UF na mao, ela decide e ponto. Sem UF - a FEPESE e a IESES nao mandam
    - quem decide e uma palavra que so existe aqui, nunca a sigla solta.
    """
    esperada = (principal.get("uf") or "").upper()
    if not esperada:
        return True
    if uf:
        return uf.upper() == esperada
    return bool(_primeiro(principal.get("prova_de_sc"), texto))


def _marcar_principal(
    principal: dict, texto: str, uf: str | None, banca: str | None
) -> Marca | None:
    if not principal:
        return None

    # A exclusao vem antes de tudo: "Policia Penal Federal" casa com
    # "policia penal" e e outro concurso, que tem bloco proprio nos
    # secundarios.
    if _primeiro(principal.get("exclui"), texto):
        return None

    achado = _primeiro(principal.get("termos"), texto) or _primeiro(
        principal.get("orgaos"), texto
    )
    if not achado or not _e_do_estado(principal, texto, uf):
        return None

    nome = principal.get("nome") or PRINCIPAL
    motivo = f'Alvo principal ({nome}): o texto fala em "{achado}".'

    # A banca nunca marca alvo sozinha - a FEPESE faz dezenas de concursos de
    # prefeitura por ano. Aqui ela so entra para o aviso lembrar que o padrao
    # de prova dessa banca eu ja conheco.
    if banca and _primeiro(principal.get("bancas"), normalizar(banca)):
        motivo += f" Banca {banca}, a mesma das edições anteriores."

    return Marca(PRINCIPAL, nome, motivo)


def principal() -> dict:
    """O bloco inteiro do alvo principal, como esta no YAML.

    Devolve {} quando nao ha alvo configurado - e ai quem chama diz que a tela
    depende de `config/alvo.yml` estar preenchido, em vez de mostrar vazio sem
    explicar por que.
    """
    return _carregar().get("principal") or {}


def termos_do_principal() -> list[str]:
    """Como o cargo do alvo aparece escrito ("policial penal", e afins).

    Serve para achar as provas dele no acervo: o cargo gravado na questao vem
    do rotulo do hotsite, e cada ano escreveu de um jeito.
    """
    return [str(x) for x in principal().get("termos") or []]


def sinonimos_do_cargo(cargo: str) -> list[str]:
    """Os outros nomes do mesmo cargo, segundo `config/alvo.yml`.

    O caso que obrigou isto: as duas provas do meu concurso estao catalogadas
    como "Agente Penitenciario", o nome que o cargo tinha em 2013 e 2019, e
    hoje ele se chama "Policial Penal". Os dois nomes nao dividem uma palavra
    sequer - procurar pelo nome de hoje nao achava prova nenhuma. Quem sabe
    que sao a mesma coisa sou eu, e ja estava escrito no YAML: e a lista de
    `termos`, que existe para reconhecer o cargo no texto do feed.

    Vale SO para o alvo principal, e isso e uma limitacao consciente. Nos
    blocos secundarios os `termos` nomeiam a CARREIRA, e nao um cargo: a
    Policia Civil lista delegado, escrivao, investigador e agente, que sao
    quatro cargos diferentes com quatro provas diferentes. Dizer que a prova
    de Delegado e "o mesmo cargo com outro nome" que a de Agente seria
    exatamente a equivalencia falsa que a prova substituta existe para nao
    fingir. No bloco principal eu escrevi os tres nomes do MEU cargo, e por
    isso ali eles sao sinonimos de verdade.

    A lista `exclui` vale aqui como vale no resto do arquivo: "Policia Penal
    Federal" contem "policia penal" e e outro concurso, com bloco proprio nos
    secundarios.

    Cargo fora disso devolve lista vazia, e a busca fica como sempre foi - por
    palavra em comum.
    """
    texto = normalizar(cargo or "")
    if not texto:
        return []

    bloco = principal()
    if _primeiro(bloco.get("exclui"), texto):
        return []

    termos = [str(t) for t in bloco.get("termos") or []]
    # Por palavra inteira, como todo o resto deste arquivo. Cobre os dois
    # jeitos de escrever: o nome curto que eu digito ("policial penal") e o
    # rotulo como o hotsite publica ("Agente Penitenciario - Feminino (AP)"),
    # que CONTEM o termo.
    if any(_padrao(termo).search(texto) for termo in termos):
        return termos
    return []


def bancas_do_principal() -> list[str]:
    """As bancas que ja fizeram o concurso do alvo, na ordem do YAML.

    Isto e HISTORIA, e nao previsao. Quem chama tem que tratar como hipotese
    enquanto nao houver edital novo dizendo quem e.
    """
    return [str(x) for x in principal().get("bancas") or []]


def orgaos_do_principal() -> list[str]:
    """Os nomes e siglas do orgao do alvo principal, como o YAML os escreve.

    Existe para o classificador de anel nao ter que repetir a mesma lista: a
    secretaria do sistema prisional de SC e orgao estadual por natureza, nos
    tres nomes que ela ja teve, e quem sabe escrever esses nomes e este
    arquivo.
    """
    return [str(o) for o in principal().get("orgaos") or []]


def nomeia_cargo_do_principal(titulo: str, resumo: str | None = None) -> bool:
    """O texto fala do CARGO do alvo, e nao so da casa que o abre?

    A diferenca decide o que a tela de foco pode afirmar. "SEJURI SC divulga
    novo edital com vaga para Medico" bate no alvo pelo nome do orgao - e e
    certo que bata, porque e a secretaria que eu acompanho. Mas nao e o meu
    concurso, e tratar os dois como a mesma coisa faria a tela anunciar
    "edital aberto" quando o que abriu foi vaga de medico.
    """
    texto = normalizar(
        GRUDADAS.sub(r"\1 \2", f"{titulo or ''} {resumo or ''}")
    )
    return bool(_primeiro(termos_do_principal(), texto))


def nomeia_orgao_do_principal(titulo: str, resumo: str | None = None) -> bool:
    """O texto nomeia o orgao do alvo principal?

    Por PALAVRA INTEIRA, como todo o resto deste arquivo - sem isso a sigla
    "SAP" casaria dentro de "SAPE/SC", que e a Secretaria da Agricultura.
    """
    texto = normalizar(
        GRUDADAS.sub(r"\1 \2", f"{titulo or ''} {resumo or ''}")
    )
    return bool(_primeiro(orgaos_do_principal(), texto))


def marcar(
    titulo: str,
    resumo: str | None = None,
    uf: str | None = None,
    banca: str | None = None,
) -> Marca | None:
    """A marca de alvo deste texto, ou None se ele nao for cargo meu."""
    bruto = GRUDADAS.sub(r"\1 \2", f"{titulo or ''} {resumo or ''}")
    texto = normalizar(bruto)

    marca = _marcar_principal(_carregar().get("principal") or {}, texto, uf, banca)
    if marca:
        return marca

    # A ordem do YAML e a ordem do CLAUDE.md: o primeiro que casar e o que
    # fica. Por isso "Oficial de Bombeiros" vem antes de "Bombeiro Militar".
    for cargo in _carregar().get("secundarios") or []:
        achado = _primeiro(cargo.get("termos"), texto)
        if achado:
            nome = cargo.get("nome") or SECUNDARIO
            return Marca(
                SECUNDARIO,
                nome,
                f'Alvo secundário ({nome}): o texto fala em "{achado}".',
            )
    return None
