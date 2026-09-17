# Radar de Concursos

Sistema pessoal para acompanhar concursos publicos que valem a pena para mim:
coleta os que abrem, guarda num banco, e deixa filtrar por estado, banca e
palavra-chave. O filtro que importa e **onde a prova e aplicada** — Grande
Florianopolis e arredores.

Estado: **fase 1** — esqueleto e a primeira fonte (feed RSS) funcionando.
O roadmap completo esta no `CLAUDE.md`.

## Rodando pela primeira vez

No Linux ou no Mac:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

No Windows (prompt de comando), onde o executavel se chama `python` e nao
`python3`, e nao se usa `source`:

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
copy .env.example .env
```

Dai em diante os comandos sao iguais nos tres:

```bash
radar coletar
radar listar --uf SC
radar web                          # http://localhost:8000
```

O `pip install -e` instala o projeto em modo editavel: o comando `radar` passa
a existir no PATH do venv e o Python acha o pacote sozinho. E por isso que nao
existe mais `PYTHONPATH=src` espalhado pelos comandos.

Rodar os testes:

```bash
pytest -q
```

Os testes usam arquivos de exemplo em `tests/fixtures/` e um SQLite temporario.
Nenhum deles vai a internet, entao passam offline e rodam em menos de 1s.

## Como o projeto esta organizado

```
src/radar/
├── config.py       le ambiente (.env). Nenhum efeito colateral no import.
├── models.py       tabela `concursos`
├── db.py           conexao criada sob demanda, nao no import
├── servico.py      roda coletores, grava com upsert, consulta
├── util.py         fuso horario e formatacao de data
├── cli.py          comandos de terminal
├── collectors/
│   ├── base.py                  contrato: toda fonte herda de Coletor
│   └── concursos_no_brasil.py   fonte 1 (feed RSS)
└── web/app.py      interface web

config/
├── regioes.yml     os tres aneis de distancia   (lido a partir da fase 1.5)
└── perfil.yml      seus dados para elegibilidade (lido a partir da fase 2.5)
```

A ideia central: **cada fonte e um arquivo isolado em `collectors/`**. O resto
do sistema nao sabe de onde veio o dado. Somar o diario oficial de SC depois e
criar um arquivo e registra-lo em `servico.COLETORES` — nada mais muda.

## Adicionando uma fonte nova

```python
# src/radar/collectors/minha_fonte.py
from radar.collectors.base import Coletor, ItemColetado

class MinhaFonte(Coletor):
    nome = "minha_fonte"

    def coletar(self) -> list[ItemColetado]:
        html = self.get("https://exemplo.com/concursos").text
        # ... extrair os dados ...
        return [ItemColetado(titulo="...", url="...", uf="SC")]
```

Depois inclua em `COLETORES`, dentro de `servico.py`.

O `self.get()` herdado ja cuida de tres coisas por voce: checa o `robots.txt`
do site, manda o `User-Agent` do projeto e espera o intervalo configurado
entre uma requisicao e outra ao mesmo host.

## O que o radar guarda

Um concurso e identificado pela **url**. Se a mesma url aparecer de novo numa
coleta seguinte, o registro e **atualizado**, nao duplicado — e por isso que
uma mudanca de `inscricoes_abertas` para `encerrado` chega no banco.

Duas colunas sao suas e a coleta nunca encosta nelas: `interesse` e `notas`.

O ciclo de vida fica em `situacao`:

```
prevista → autorizado → banca_definida → edital_publicado
→ inscricoes_abertas → encerrado
```

## Automacao

`.github/workflows/coleta.yml` roda a coleta todo dia as 6h de Florianopolis,
no GitHub Actions, e commita o resultado. Tambem da para disparar na mao pela
aba Actions.

Actions e gratuito em repositorio privado ate 2.000 minutos por mes; a coleta
gasta uns 3 minutos por dia. Sua maquina nao roda nada: ela so e usada quando
voce abre a web ou pede para baixar prova.

## Sobre as fontes

Nao existe API oficial unica de concursos no Brasil. A fase 1 usa o **feed
RSS** do Concursos no Brasil de proposito: RSS e publico, estavel e feito para
ser lido por programa, e nao quebra quando o site muda o layout.

Vale saber da limitacao: **RSS e um fluxo, nao um arquivo.** Ele entrega o que
e recente, entao "todos os concursos do ano" nao sai dele — isso e a fase 1.6,
com uma carga inicial pelas paginas de arquivo do site.

Regras da casa para as proximas fontes:
- respeitar o `robots.txt`;
- manter o intervalo entre requisicoes (`RADAR_REQUEST_DELAY`);
- identificar-se no `User-Agent`;
- guardar sempre o link original — o sistema e um indice, nao um substituto.

## Por que os PDFs nao ficam no git

A partir da fase 3 o radar baixa provas e editais. Eles vao para `data/provas/`
e `data/editais/`, que estao no `.gitignore`.

O que vai para o git e o **manifesto** (`data/provas.json`): link original,
banca, orgao, cargo, ano e o `sha256` de cada arquivo. Com ele, `radar
baixar-provas` reconstroi o acervo inteiro em qualquer maquina, e o hash prova
que o arquivo e o mesmo.

Motivo: git guarda uma copia inteira de cada arquivo binario a cada commit.
Algumas centenas de PDFs deixariam o repositorio grande e lento. Versionar a
receita em vez do artefato e a mesma logica de Dockerfile e imagem.

## Nota sobre dependencias

As versoes estao presas no `pyproject.toml`, inclusive o `click` — ele e
dependencia indireta do `typer` e uma versao nova dele ja quebrou a CLI aqui.
Se a coleta diaria comecar a falhar por instalacao, o proximo passo e gerar um
lock com `pip freeze`.
