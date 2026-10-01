"""As mudancas de estrutura do banco, numeradas, com copia antes e desfazer.

Ate a Etapa 2 o banco so ganhava coluna nova (`db._adicionar_colunas_novas`)
e ninguem guardava a versao. Isso bastou enquanto a mudanca era coluna vazia.
A Etapa 2 traz tabela nova E dado novo derivado do antigo (a evidencia de
cada questao, a arvore de conteudos, as ligacoes dos textos antigos), e o
pedido (secao 21) e claro: copia antes, nenhuma linha perdida, conferencia
"antes x depois" e um jeito de desfazer.

O minimo para isso, sem Alembic:

- **a versao** fica na tabela `versao_do_banco` (sem ela, versao 0);
- **cada passo** e uma funcao numerada em `PASSOS`, que leva o dado antigo
  para o formato novo. A estrutura (tabela e coluna) continua vindo do
  modelo, pelo `create_all` e pelo `_adicionar_colunas_novas`;
- **antes de qualquer passo**, o radar.db e copiado para
  `data/copias/migracao-v<de>-para-v<para>-<hora>/`, fora do git;
- **desfazer** e restaurar essa copia (`radar migrar --desfazer`).

Banco novo (sem tabela nenhuma) nao migra: nasce na versao atual. E o caso de
todo teste e do robo do GitHub, que monta o banco do zero a cada execucao.
"""
import logging
import sqlite3
from contextlib import closing
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from sqlalchemy import Engine, func, inspect, select, text

from radar import config
from radar.models import Base, VersaoDoBanco, agora
from radar.util import fuso_local

log = logging.getLogger(__name__)

PREFIXO_DA_COPIA = "migracao"


def _passo_1() -> None:
    """Etapa 2: a evidencia de cada questao, a arvore e as ligacoes antigas.

    Importado aqui dentro de proposito: o `servico` usa o `db`, e o `db` chama
    esta migracao - importar no topo faria um ciclo.
    """
    from radar import acervo
    from radar.servico import conteudos, evidencia

    conteudos.semear()
    evidencia.atualizar()
    conteudos.ligar_textos_antigos()
    # A ligacao nova vai para os arquivos versionados ja: o `sincronizar` nao
    # exporta as geradas, e o banco e reconstruivel.
    acervo.exportar_geradas()
    acervo.exportar_erros()
    acervo.exportar_extras()


#: versao -> (o que muda, a funcao). A ordem e a dos numeros; passo aplicado
#: nao se edita nunca mais: mudanca nova e passo novo.
PASSOS = {
    1: ("A árvore de conteúdos, as classificações e a evidência de cada questão",
        _passo_1),
}
VERSAO_ATUAL = max(PASSOS)


@dataclass
class Relatorio:
    de: int
    para: int
    #: {tabela: linhas}. Tabela que nao existia antes nao aparece em `antes`.
    antes: dict[str, int] = field(default_factory=dict)
    depois: dict[str, int] = field(default_factory=dict)
    copia: Path | None = None

    @property
    def mudou(self) -> bool:
        return self.para != self.de

    @property
    def perdidas(self) -> dict[str, int]:
        """{tabela: quantas linhas sumiram}. Tem que ser vazio, sempre."""
        return {tabela: n - self.depois.get(tabela, 0)
                for tabela, n in self.antes.items()
                if self.depois.get(tabela, 0) < n}


class MigracaoFalhou(RuntimeError):
    """Um passo terminou com menos linhas do que comecou. O banco e
    devolvido a copia antes de esta excecao subir."""


def _tabelas(engine: Engine) -> set[str]:
    return set(inspect(engine).get_table_names())


def versao(engine: Engine) -> int:
    if VersaoDoBanco.__tablename__ not in _tabelas(engine):
        return 0
    with engine.connect() as conexao:
        lida = conexao.execute(select(func.max(VersaoDoBanco.versao))).scalar()
    return lida or 0


def _gravar_versao(engine: Engine, numero: int) -> None:
    VersaoDoBanco.__table__.create(engine, checkfirst=True)
    with engine.begin() as conexao:
        conexao.execute(VersaoDoBanco.__table__.delete())
        conexao.execute(VersaoDoBanco.__table__.insert().values(
            id=1, versao=numero, migrado_em=agora()))


def contar_linhas(engine: Engine) -> dict[str, int]:
    """{tabela: linhas}, de toda tabela que existe no banco agora."""
    contagem = {}
    with engine.connect() as conexao:
        for tabela in sorted(_tabelas(engine)):
            contagem[tabela] = conexao.execute(
                text(f'SELECT COUNT(*) FROM "{tabela}"')).scalar()
    return contagem


# --- a copia ---------------------------------------------------------------------

def caminho_das_copias() -> Path:
    return config.diretorio_dados() / "copias"


def _arquivo_do_banco() -> Path | None:
    url = config.url_do_banco()
    if not url.startswith("sqlite:///"):
        return None
    return Path(url.removeprefix("sqlite:///"))


def copiar_banco(nome: str) -> Path:
    """Copia o radar.db para `data/copias/<nome>-<hora>/` e devolve a pasta.

    Pela API de backup do SQLite, e nao por copia de arquivo: com o `radar
    web` aberto, copiar o arquivo no meio de uma gravacao daria uma copia
    quebrada.
    """
    banco = _arquivo_do_banco()
    if banco is None:
        raise RuntimeError("A cópia de segurança só sabe copiar banco SQLite.")
    pasta = caminho_das_copias() / f"{nome}-{datetime.now(fuso_local()):%Y-%m-%d-%H%M%S}"
    pasta.mkdir(parents=True, exist_ok=False)
    with closing(sqlite3.connect(banco)) as origem, \
         closing(sqlite3.connect(pasta / banco.name)) as destino:
        origem.backup(destino)
    return pasta


def _restaurar(pasta: Path) -> None:
    from radar import db

    banco = _arquivo_do_banco()
    copia = pasta / banco.name
    if not copia.exists():
        raise FileNotFoundError(f"A cópia {copia} não existe.")
    # Solta a conexao antes: o SQLite nao deixa sobrescrever um banco que o
    # proprio processo esta segurando.
    db.resetar_engine()
    with closing(sqlite3.connect(copia)) as origem, \
         closing(sqlite3.connect(banco)) as destino:
        origem.backup(destino)


# --- migrar e desfazer -------------------------------------------------------------

def _criar_estrutura(engine: Engine) -> None:
    from radar.db import _adicionar_colunas_novas

    Base.metadata.create_all(engine)
    _adicionar_colunas_novas(engine)


def preparar(engine: Engine) -> Relatorio | None:
    """O que o `db.criar_tabelas` chama: banco novo nasce na versao atual, e
    banco velho e migrado. Devolve o relatorio quando migrou."""
    if not _tabelas(engine):
        _criar_estrutura(engine)
        _gravar_versao(engine, VERSAO_ATUAL)
        return None
    if versao(engine) >= VERSAO_ATUAL:
        return None
    relatorio = migrar(engine)
    log.warning("Banco migrado da versão %d para a %d. Cópia de antes em %s",
                relatorio.de, relatorio.para, relatorio.copia)
    return relatorio


def migrar(engine: Engine | None = None) -> Relatorio:
    """Leva o banco a `VERSAO_ATUAL`, passo a passo, com copia antes.

    Rodar de novo num banco ja migrado nao faz nada: a versao gravada diz que
    os passos ja foram aplicados, e nenhum deles roda duas vezes.
    """
    from radar import db

    engine = engine or db.get_engine()
    # Os passos chamam `criar_tabelas`, que migraria de novo se nao soubesse
    # que a versao ja esta sendo cuidada aqui.
    db._versao_conferida = True
    if not _tabelas(engine):
        # Banco vazio nao tem o que copiar nem o que levar: nasce na atual.
        preparar(engine)
        return Relatorio(de=VERSAO_ATUAL, para=VERSAO_ATUAL)
    de = versao(engine)
    relatorio = Relatorio(de=de, para=de)
    if de >= VERSAO_ATUAL:
        relatorio.antes = relatorio.depois = contar_linhas(engine)
        return relatorio

    relatorio.antes = contar_linhas(engine)
    if _arquivo_do_banco() is not None:
        relatorio.copia = copiar_banco(f"{PREFIXO_DA_COPIA}-v{de}-para-v{VERSAO_ATUAL}")

    _criar_estrutura(engine)
    for numero in range(de + 1, VERSAO_ATUAL + 1):
        _, passo = PASSOS[numero]
        log.info("migração %d: %s", numero, PASSOS[numero][0])
        passo()
    relatorio.depois = contar_linhas(engine)

    if relatorio.perdidas:
        # Nenhum passo apaga linha. Se sumiu, e defeito: o banco volta a copia
        # e a migracao para, em vez de seguir com o dado a menos.
        if relatorio.copia is not None:
            _restaurar(relatorio.copia)
        raise MigracaoFalhou(f"Linhas perdidas: {relatorio.perdidas}. O banco "
                             f"voltou à cópia de {relatorio.copia}.")
    _gravar_versao(engine, VERSAO_ATUAL)
    relatorio.para = VERSAO_ATUAL
    # De novo, agora com a versao gravada: e o banco como ele ficou.
    relatorio.depois = contar_linhas(engine)
    return relatorio


def ultima_copia() -> Path | None:
    """A copia da migracao mais recente. O nome tem a hora, entao a ordem
    alfabetica e a ordem do tempo."""
    pasta = caminho_das_copias()
    if not pasta.exists():
        return None
    copias = sorted(p for p in pasta.iterdir()
                    if p.is_dir() and p.name.startswith(PREFIXO_DA_COPIA + "-"))
    return copias[-1] if copias else None


def desfazer() -> Path:
    """Devolve o banco a copia da ultima migracao. Devolve a pasta usada.

    Antes de sobrescrever, o banco de agora tambem e copiado: desfazer por
    engano tem que ter volta. Para ficar na versao antiga, o codigo tambem
    tem que voltar (git): o proximo comando do radar novo migraria de novo.
    """
    copia = ultima_copia()
    if copia is None:
        raise FileNotFoundError("Não há cópia de migração em data/copias/.")
    copiar_banco("antes-de-desfazer")
    _restaurar(copia)
    return copia

