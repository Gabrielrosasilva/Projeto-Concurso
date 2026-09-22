"""Exportar e importar o banco como JSON.

Por que isto existe: a coleta diaria roda no GitHub Actions e precisa guardar
o resultado em algum lugar. Commitar o arquivo .db do SQLite funcionaria, mas
git guarda uma copia inteira de cada arquivo binario a cada commit — em um ano
seriam 365 copias do banco dentro do repositorio.

O JSON resolve os dois lados: e texto, entao o git guarda so a diferenca, e o
diff do commit diario fica legivel — da para abrir e ver exatamente quais
concursos entraram naquele dia.

Fluxo no Actions:  importar -> coletar -> exportar -> commit do JSON
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select

from radar import config
from radar.db import criar_tabelas, sessao
from radar.models import Concurso, DataHoraUTC

# Colunas exportadas, em ordem fixa. Ordem fixa e chave ordenada deixam o
# arquivo estavel: mudou o diff, mudou o dado de verdade.
COLUNAS = [c.name for c in Concurso.__table__.columns if c.name != "id"]

# Quais delas sao data, perguntado ao PROPRIO modelo.
#
# Isto ja foi uma lista escrita a mao, e ela envelheceu calada: `avisado_em`
# entrou na fase 2 e `detalhado_em` na 2.5, nenhuma das duas foi acrescentada
# ali, e o `radar importar` passou a quebrar com "'str' object has no attribute
# 'tzinfo'" - a data voltava do JSON como texto. Na minha maquina isso nao
# aparecia, porque o banco ja existia; no GitHub Actions, que comeca sem banco
# todo dia, a coleta diaria falhava.
COLUNAS_DE_DATA = frozenset(
    c.name for c in Concurso.__table__.columns if isinstance(c.type, DataHoraUTC)
)


def caminho_padrao() -> Path:
    return config.diretorio_dados() / "concursos.json"


def _serializar(valor: Any) -> Any:
    return valor.isoformat() if isinstance(valor, datetime) else valor


def _desserializar(coluna: str, valor: Any) -> Any:
    if valor is None:
        return None
    if coluna in COLUNAS_DE_DATA:
        return datetime.fromisoformat(valor)
    return valor


def exportar(caminho: Path | None = None) -> int:
    """Escreve o banco inteiro no JSON. Devolve quantos registros gravou."""
    criar_tabelas()
    destino = caminho or caminho_padrao()

    with sessao() as s:
        # ordenado pela url para o diff nao embaralhar a cada execucao
        concursos = list(s.scalars(select(Concurso).order_by(Concurso.url)))
        linhas = [
            {coluna: _serializar(getattr(c, coluna)) for coluna in COLUNAS}
            for c in concursos
        ]

    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps(linhas, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return len(linhas)


def importar(caminho: Path | None = None) -> int:
    """Recria o banco a partir do JSON. Devolve quantos registros leu.

    Nao apaga o que ja existe: casa pela url e atualiza. Rodar duas vezes da
    no mesmo resultado.
    """
    origem = caminho or caminho_padrao()
    if not origem.exists():
        return 0

    criar_tabelas()
    linhas = json.loads(origem.read_text(encoding="utf-8"))

    with sessao() as s:
        for linha in linhas:
            concurso = s.scalar(select(Concurso).where(Concurso.url == linha["url"]))
            if concurso is None:
                concurso = Concurso(url=linha["url"])
                s.add(concurso)
            for coluna in COLUNAS:
                if coluna == "url" or coluna not in linha:
                    continue
                setattr(concurso, coluna, _desserializar(coluna, linha[coluna]))

    return len(linhas)
