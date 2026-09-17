# CLAUDE.md

Contexto permanente deste projeto. O Claude Code le este arquivo em toda
sessao aberta nesta pasta.

## O que e

Sistema **pessoal** (um unico usuario) para acompanhar concursos publicos que
valem a pena para mim. Nao e produto, nao tem login, nao vai para producao.
Prioridade: funcionar e ser facil de manter sozinho.

## Quem mantem

Analista de infraestrutura/SRE. Domino Linux, Docker, Kubernetes, Terraform,
GitLab CI, GitHub Actions, AWS e OCI, shell script, SQL e Java. **Nao tenho
pratica em Python** — e a linguagem escolhida aqui justamente para aprender.

Por causa disso:
- prefira o jeito simples e legivel ao jeito esperto;
- prefira biblioteca padrao quando a diferenca for pequena;
- nao introduza abstracao nova sem necessidade concreta;
- comentario explica **por que**, nao o que a linha faz.

Escreva comentarios, mensagens de commit e texto de interface em **portugues**.
Nomes de variaveis, funcoes e arquivos tambem em portugues — o codigo ja segue
isso, mantenha a consistencia.

## O que eu procuro num concurso

Nao tenho area unica. Meus criterios reais, em ordem:

1. **Onde a prova e aplicada.** Grande Florianopolis ou perto. Este e o filtro
   principal; o cargo e secundario.
2. **Se eu posso prestar.** Superior em Sistemas de Informacao. Muitos cargos
   pedem "superior em qualquer area" — esses servem.
3. **Salario.** Acima de R$ 5.000 e o alvo. Nao e corte: abaixo disso continua
   aparecendo, so mais embaixo no ranking.

Cargos que eu mais quero, em ordem de preferencia:

Policia Penal · Guarda Municipal · Policia Civil · Policia Penal Federal ·
Bombeiro Militar · Oficial de Bombeiros · Policia Cientifica

**Nenhum concurso e descartado por nao estar nessa lista.** Ela ordena, nao
filtra. Concurso federal entra, principalmente se aplicar prova em Floripa.

Consequencia pratica disso, e e importante: as materias que interessam sao as
de **carreira policial e seguranca publica** — Direito Constitucional, Penal,
Processo Penal, Administrativo, Legislacao Especial, Direitos Humanos,
Portugues, Raciocinio Logico, Atualidades. **Nao** e TI.

E as bancas que importam nao sao as nacionais de sempre. Em SC o peso esta em
**FEPESE**, ACAFE, IESES, FURB, Instituto o Barriga Verde, e nas que costumam
fazer seguranca publica (IBFC, Instituto AOCP, FUNDATEC, Consulplan, e o
Cebraspe nas federais). Qual banca fez qual concurso e coisa para **confirmar
lendo o edital**, nunca para afirmar de memoria.

## Regra de relevancia geografica

Tres aneis, configurados em `config/regioes.yml` (nunca fixos no codigo):

1. **nucleo** — Regiao Metropolitana da Grande Florianopolis.
2. **proximo** — Itajai, Balneario Camboriu, Brusque, Tubarao, Laguna,
   Imbituba, Blumenau, Lages e vizinhos. Blumenau (~2h) e Lages (~3h) estao
   aqui por escolha minha, nao por tempo de estrada.
3. **remoto** — qualquer outro lugar. So interessa se o edital disser que ha
   aplicacao de prova em Florianopolis.

Como decidir o anel, em ordem de confianca:

- **concurso de SC**: pelo municipio do orgao, extraido do titulo/resumo;
- **federal ou de outro estado**: so pelo texto do edital em PDF, procurando as
  cidades de aplicacao. Sem edital lido, fica `indefinida` — **nunca chute**;
- guarde sempre *por que* foi classificado assim, em `motivo_relevancia`.
  Eu preciso poder auditar a decisao.

Concurso irrelevante **nao e apagado**: fica marcado, para eu revisar e
corrigir a regra.

## Ciclo de vida do concurso

O radar acompanha o concurso desde antes do edital. Campo `situacao`:

```
prevista → autorizado → banca_definida → edital_publicado
→ inscricoes_abertas → encerrado
```

`banca_definida` e o sinal mais valioso: quando a prefeitura contrata a banca,
sai licitacao ou dispensa no diario oficial, tipicamente **2 a 4 meses antes
do edital**. Da tempo de comecar a estudar o padrao da banca.

## Estado atual

**Fase 1 pronta:** esqueleto + feed RSS do Concursos no Brasil funcionando.

```
src/radar/
├── config.py       le ambiente. Nenhum efeito colateral no import.
├── models.py       tabela `concursos` (SQLAlchemy 2.0, estilo Mapped)
├── db.py           engine preguicoso + context manager de sessao
├── servico.py      roda coletores, grava com upsert, consulta
├── util.py         fuso e formatacao de data
├── cli.py          comandos typer: coletar, listar, web
├── collectors/
│   ├── base.py                  Coletor + ItemColetado; cuida de robots.txt,
│   │                            User-Agent e atraso entre requisicoes
│   └── concursos_no_brasil.py   fonte 1: feed RSS
└── web/app.py      FastAPI + Jinja2, uma pagina com filtros
```

Banco: SQLite em `data/radar.db`, Postgres opcional via `RADAR_DATABASE_URL`.
Testes em `tests/`, todos com dado fixo, nenhum vai a internet.

**Arquitetura a preservar:** cada fonte e um arquivo isolado em `collectors/`,
herda de `Coletor`, devolve `list[ItemColetado]` e esta registrada em
`servico.COLETORES`. Nada fora de `collectors/` sabe de onde vem o dado.

**Decisoes que ja foram tomadas e nao precisam ser rediscutidas:**
- datas: sempre UTC com fuso, convertidas para horario local so na exibicao;
- a coleta faz upsert e **nunca** sobrescreve `interesse` e `notas`;
- fonte que falha e registrada e a coleta segue com as outras;
- o schema ja tem colunas de fases futuras, vazias. E de proposito: sem
  Alembic, coluna nova depois significa recriar o banco;
- PDF nao vai para o git. Vai o manifesto; o comando rebaixa tudo;
- avisos sao por **Telegram**. WhatsApp foi avaliado e descartado: o oficial
  exige conta Meta Business, numero separado e template aprovado para mensagem
  proativa; o nao oficial arrisca banir meu numero pessoal.

## Roadmap

```
1.5  relevancia geografica (3 aneis) + perfil/elegibilidade
     + interesse/notas na CLI e na web
1.6  carga inicial: varrer as paginas de arquivo e trazer o ano inteiro
     (o RSS so entrega o que e recente)
1.7  Diario Oficial dos Municipios de SC + DOE-SC + DOU
     inclui o sinal "contrataram a banca"
2    avisos no Telegram + export .ics para o calendario
2.5  leitura do edital em PDF: local de prova, prazos, salario, escolaridade,
     idade maxima, CNH, TAF + deteccao de retificacao por hash
3    acervo de provas (FEPESE primeiro) + manifesto no git + prova substituta
4    padrao da banca: questao a questao, incidencia por assunto
5    modo simulado com acerto por assunto
6    concurso atrasado + validade vencendo (previsao de abertura)
```

## Fontes de dados

Nao existe API oficial unica de concursos no Brasil.

- prefira **RSS e dados abertos** a raspagem de HTML, sempre;
- fonte primaria para municipio de SC e o **Diario Oficial dos Municipios de
  SC** (CIGA) — e onde o ato oficial sai, e cobre exatamente meu recorte;
- **nao** raspe site cujos termos proibem (Qconcursos, por exemplo) nem
  conteudo atras de login ou paywall;
- respeite `robots.txt`, mantenha o atraso entre requisicoes e identifique-se
  no User-Agent. A classe `Coletor` ja faz os tres;
- guarde sempre o link original: isto e um indice pessoal, nao uma copia do
  conteudo de ninguem.

## Como trabalhar aqui

- **uma coisa por vez.** Uma mudanca, testada, e so entao a proxima. Nao
  refatore o que nao faz parte do pedido;
- todo coletor e todo classificador precisa de **teste com dado fixo**
  (fixture em arquivo), nunca teste que va a internet;
- antes de dizer que terminou: `pytest -q` passando **e** o comando afetado
  rodado de verdade no terminal;
- nao adicione dependencia sem justificar em uma linha;
- **me diga quando nao souber** em vez de inventar seletor de HTML, URL ou
  nome de campo. Se precisar da estrutura real de uma pagina, peca para eu
  baixar e colar — o ambiente do Claude Code na web **nao tem internet aberta**
  e nao consegue conferir pagina de terceiro sozinho.
