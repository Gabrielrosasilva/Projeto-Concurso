"""O link do Qconcursos de cada tema (decisao 140).

A faixa dizia "No Qconcursos: Direito Constitucional > direitos e deveres
individuais e coletivos" - um caminho escrito de cabeca no plano, que nao
existe no site, e o que existe trazia o art. 5º inteiro. Agora o tema aponta os
assuntos do proprio site, e a faixa abre o filtro pronto: a FEPESE, sem anulada
nem desatualizada, so os assuntos do tema.

O radar nao consulta o Qconcursos (os termos proibem raspagem): os numeros
moram no config/qconcursos.yml, tirados das listas que eu copiei do site, e
aqui so se monta o endereco. Puro: le o arquivo e devolve o link.
"""
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlencode

import yaml

from radar import config
from radar.fichas import chave_do_tema, tema_da_faixa

ENDERECO = "https://www.qconcursos.com/questoes-de-concursos/questoes"


@dataclass(frozen=True)
class LinkDoTema:
    """Um tema do arquivo: a disciplina e os assuntos do site, e o aviso
    quando o assunto do site e mais largo que o tema."""

    tema: str
    banca: int
    disciplina: int
    assuntos: tuple = ()          # ((numero, nome no site), ...)
    aviso: str | None = None

    @property
    def url(self) -> str:
        """O endereco do filtro, no formato que o proprio site gera."""
        parametros = [
            ("discipline_ids[]", self.disciplina),
            ("examining_board_ids[]", self.banca),
            ("exclude_nullified", "true"),
            ("exclude_outdated", "true"),
            ("per_page", 20),
        ] + [("subject_ids[]", numero) for numero, _ in self.assuntos]
        return f"{ENDERECO}?{urlencode(parametros)}"

    @property
    def nomes(self) -> list[str]:
        return [nome for _, nome in self.assuntos]


def carregar(caminho: Path | None = None) -> dict[str, LinkDoTema]:
    """{chave do tema: LinkDoTema}. Sem o arquivo, nenhum tema tem link e a
    faixa continua com o filtro escrito do plano."""
    arquivo = Path(caminho or (config.diretorio_config() / "qconcursos.yml"))
    if not arquivo.exists():
        return {}
    dados = yaml.safe_load(arquivo.read_text(encoding="utf-8")) or {}
    banca = int(dados["banca"])
    links = {}
    for item in dados.get("temas") or []:
        link = LinkDoTema(
            tema=item["tema"], banca=banca, disciplina=int(item["disciplina"]),
            assuntos=tuple((int(numero), str(nome))
                           for numero, nome in (item.get("assuntos") or {}).items()),
            aviso=item.get("aviso"))
        links[chave_do_tema(link.tema)] = link
    return links


def do_tema(tema: str | None, links: dict[str, LinkDoTema] | None = None) -> LinkDoTema | None:
    """O link do tema, reconhecido como a ficha: sem acento, sem caixa."""
    links = carregar() if links is None else links
    return links.get(chave_do_tema(tema))


def da_faixa(faixa, links: dict[str, LinkDoTema] | None = None) -> LinkDoTema | None:
    """O link da faixa que manda ao Qconcursos, pelo tema do titulo (sem o
    prefixo, como a ficha: "R+7: Vozes do verbo" e o tema "Vozes do verbo").
    A faixa de teoria do mesmo tema nao ganha link: ela nao e no Qconcursos."""
    if faixa is None or getattr(faixa, "onde", None) != "qconcursos":
        return None
    return do_tema(tema_da_faixa(faixa.titulo, getattr(faixa, "materia", None)), links)
