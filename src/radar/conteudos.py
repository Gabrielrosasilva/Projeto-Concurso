"""A arvore de conteudos e as regras dela. Puro: nao fala com banco nem rede.

    materia > assunto > subassunto > elemento

Os dois niveis de baixo sao opcionais: "Lingua Portuguesa > Emprego da
crase" ja e um no completo, e o Direito desce ate "CP, art. 2º" quando a
questao chega la. O que e "elemento" depende da materia, e a lista mora no
config/taxonomia.yml - ampliar a lista nao muda o banco.

Todo no e reconhecido pelo CAMINHO de nomes ("Direito Penal > Imputabilidade
penal"): e assim que a questao, a faixa do cronograma, o erro anotado e a
questao gerada apontam para ele. O id do banco muda quando o banco e refeito;
o caminho, nao.

A semente e o edital: as materias e os assuntos com o texto LITERAL do anexo
de programas, inclusive os defeitos dele (o `edital_programa` explica por
que). Nada aqui inventa no para caber uma classificacao: o que nao casa fica
pendente (regra inviolavel 9).
"""
from dataclasses import dataclass
from pathlib import Path

import yaml

from radar import config
from radar.regioes import normalizar

NIVEIS = ("materia", "assunto", "subassunto", "elemento")
SEPARADOR = " > "

ORIGENS = ("edital", "classificacao", "manual")

# De onde veio a semente. Um texto so, para a procedencia de todos os nos do
# edital dizer a mesma coisa.
PROCEDENCIA_DO_EDITAL = "edital de 2019 (anexo de programas)"


class ConteudoInvalido(ValueError):
    """Um no que nao cabe na arvore. A mensagem diz por que."""


@dataclass
class No:
    """Um no antes de ir para o banco (ou depois de sair dele, no JSON)."""
    caminho: str
    pai: str | None
    nivel: str
    nome: str
    ordem: int = 0
    origem: str = "edital"
    texto_do_edital: str | None = None
    fora_do_edital: bool = False
    procedencia: str | None = None
    tipo_elemento: str | None = None
    referencia: str | None = None


def caminho(pai: str | None, nome: str) -> str:
    """O caminho do filho `nome` debaixo de `pai`."""
    nome = " ".join((nome or "").split())
    if not nome:
        raise ConteudoInvalido("O nó precisa de nome.")
    if SEPARADOR.strip() in nome:
        # O ">" e o separador do caminho: dentro do nome ele partiria o no
        # em dois na volta do JSON.
        raise ConteudoInvalido(f"O nome não pode ter {SEPARADOR.strip()!r}: {nome!r}")
    return f"{pai}{SEPARADOR}{nome}" if pai else nome


def partes(caminho_do_no: str) -> list[str]:
    return caminho_do_no.split(SEPARADOR)


def nivel_do_filho(nivel_do_pai: str | None) -> str:
    """O nivel de quem nasce debaixo de um no desse nivel."""
    if nivel_do_pai is None:
        return NIVEIS[0]
    posicao = NIVEIS.index(nivel_do_pai)
    if posicao == len(NIVEIS) - 1:
        raise ConteudoInvalido("O elemento é o último nível: não tem filho.")
    return NIVEIS[posicao + 1]


# --- a taxonomia ----------------------------------------------------------------

@dataclass
class Taxonomia:
    #: {familia: (materias, elementos)}
    familias: dict[str, tuple[list[str], list[str]]]
    elementos_comuns: list[str]
    tipos_de_questao: list[str]
    #: [{"nome": ..., "procedencia": ...}]
    materias_fora_do_edital: list[dict]
    #: {nome antigo: nome do edital}
    sinonimos_de_materia: dict[str, str]

    def elementos_da_materia(self, materia: str) -> list[str]:
        """Os tipos de elemento que esta materia aceita."""
        alvo = normalizar(materia)
        for materias, elementos in self.familias.values():
            if any(normalizar(m) == alvo for m in materias):
                return list(self.elementos_comuns) + list(elementos)
        return list(self.elementos_comuns)

    def materia_do_texto(self, texto: str | None) -> str | None:
        """O nome do edital para um nome de materia escrito numa prova antiga,
        quando ha sinonimo declarado. None quando nao ha."""
        alvo = normalizar(texto or "")
        for antigo, novo in self.sinonimos_de_materia.items():
            if normalizar(antigo) == alvo:
                return novo
        return None


def carregar_taxonomia(caminho_do_arquivo: Path | None = None) -> Taxonomia:
    arquivo = caminho_do_arquivo or (config.diretorio_config() / "taxonomia.yml")
    dados = yaml.safe_load(Path(arquivo).read_text(encoding="utf-8")) or {}
    familias = {}
    for nome, bruta in (dados.get("familias") or {}).items():
        bruta = bruta or {}
        familias[nome] = ([str(m) for m in bruta.get("materias") or []],
                          [str(e) for e in bruta.get("elementos") or []])
    return Taxonomia(
        familias=familias,
        elementos_comuns=[str(e) for e in dados.get("elementos_comuns") or []],
        tipos_de_questao=[str(t) for t in dados.get("tipos_de_questao") or []],
        materias_fora_do_edital=list(dados.get("materias_fora_do_edital") or []),
        sinonimos_de_materia={str(k): str(v) for k, v
                              in (dados.get("sinonimos_de_materia") or {}).items()},
    )


def conferir_elemento(taxonomia: Taxonomia, materia: str, tipo: str | None) -> None:
    """Recusa o tipo de elemento que a familia da materia nao aceita."""
    if tipo is None:
        raise ConteudoInvalido("O elemento precisa de tipo (artigo, regra gramatical...).")
    aceitos = taxonomia.elementos_da_materia(materia)
    if tipo not in aceitos:
        raise ConteudoInvalido(
            f"{tipo!r} não é tipo de elemento de {materia} no config/taxonomia.yml "
            f"(aceitos: {', '.join(aceitos)})."
        )


# --- a semente ------------------------------------------------------------------

def semente(programa: dict[str, list[str]], taxonomia: Taxonomia) -> list[No]:
    """Os nos que o edital da: cada materia e os assuntos dela, literais.

    Mais as materias que cairam numa prova do alvo e nao estao no edital de
    agora (`materias_fora_do_edital`), marcadas assim - sem assunto, porque
    nao ha programa delas para copiar.
    """
    nos: list[No] = []
    for ordem, (materia, assuntos) in enumerate(programa.items()):
        nos.append(No(caminho=caminho(None, materia), pai=None, nivel="materia",
                      nome=materia, ordem=ordem, texto_do_edital=materia,
                      procedencia=PROCEDENCIA_DO_EDITAL))
        vistos = set()
        for posicao, assunto in enumerate(assuntos):
            filho = caminho(materia, assunto.replace(SEPARADOR.strip(), "-"))
            if filho in vistos:
                continue
            vistos.add(filho)
            nos.append(No(caminho=filho, pai=materia, nivel="assunto",
                          nome=partes(filho)[-1], ordem=posicao,
                          texto_do_edital=assunto, procedencia=PROCEDENCIA_DO_EDITAL))

    ja_tem = {normalizar(n.nome) for n in nos if n.nivel == "materia"}
    for posicao, fora in enumerate(taxonomia.materias_fora_do_edital):
        nome = str(fora.get("nome") or "").strip()
        if not nome or normalizar(nome) in ja_tem:
            continue
        nos.append(No(caminho=caminho(None, nome), pai=None, nivel="materia",
                      nome=nome, ordem=len(programa) + posicao, origem="manual",
                      fora_do_edital=True,
                      procedencia=str(fora.get("procedencia") or "") or None))
    return nos


def achar(caminhos: list[str], texto: str | None, pai: str | None = None) -> str | None:
    """O caminho cujo ultimo nome e IGUAL a `texto` (sem diferenca de
    maiuscula nem de acento), debaixo de `pai` (ou entre as materias, sem
    pai). None quando nao ha - e ai o texto fica pendente, nunca aproximado."""
    alvo = normalizar(texto or "")
    if not alvo:
        return None
    for candidato in caminhos:
        nomes = partes(candidato)
        mesmo_pai = (SEPARADOR.join(nomes[:-1]) or None) == pai
        if mesmo_pai and normalizar(nomes[-1]) == alvo:
            return candidato
    return None
