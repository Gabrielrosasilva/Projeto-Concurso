# CLAUDE.md
Contexto permanente deste projeto, lido pelo Claude Code em toda sessao aberta
nesta pasta. Curto de proposito. O que nao cabe aqui:

- **[docs/novo.md](docs/novo.md)** — é o pedido: o que você quer que o sistema faça e as regras que não podem ser quebradas;
- **[docs/roteiro.md](docs/roteiro.md)** — plano e os critérios de cada etapa;
- **[docs/progresso.md](docs/progresso.md)** — como cada etapa andou: situação,
  arquivos, testes e o critério de conclusão marcado;
- **[docs/decisoes.md](docs/decisoes.md)** — decisoes ja tomadas, com o motivo;
  nao se rediscutem. **Decisao que mudar, atualize la.**
- **[docs/pendencias.md](docs/pendencias.md)** — o que falta, o que esta
  quebrado e o que ficou combinado. **Leia antes de propor etapa.**
- **[docs/especificacao.md](docs/especificacao.md)** — o redesign; leia antes de
  mexer em tela ou em dado de estudo. **[docs/historico.md](docs/historico.md)**
  — como cada fase foi feita. **[README.md](README.md)** — instalar e usar.

## O que e

Sistema **pessoal** (um unico usuario) para acompanhar concursos publicos que
valem a pena para mim. Nao e produto, nao tem login, nao vai para producao.
Prioridade: funcionar e ser facil de manter sozinho.

## Quem mantem

Analista de infraestrutura/SRE. Domino Linux, Docker, Kubernetes, Terraform,
GitLab CI, GitHub Actions, AWS e OCI, shell script, SQL e Java. **Nao tenho
pratica em Python** — e a linguagem escolhida aqui justamente para aprender.
Por causa disso:
- prefira o jeito simples e legivel ao esperto, e a biblioteca padrao quando a
  diferenca for pequena;
- nao introduza abstracao sem necessidade concreta; comentario explica **por
  que**, nao o que a linha faz.

Comentarios, commits, texto de interface e nomes de variaveis, funcoes e
arquivos: em **portugues** — o codigo ja segue isso.

## O que eu procuro num concurso

**O alvo principal e Policia Penal SC.** Para ele o cargo manda e a distancia
nao importa: e concurso estadual, e eu presto onde for. **A de outro estado
tambem avisa, e so avisa** (marca `principal_fora`): o **estudo** — Meu foco,
incidencia, treino, acervo — le so as provas de SC, porque fora daqui e outra
banca e outra lei estadual.

Depois dele, nesta ordem: Guarda Municipal · Policia Civil · Oficial de
Bombeiros · e as demais carreiras de seguranca publica (Policia Penal Federal,
Bombeiro Militar, Policia Cientifica). **A lista ordena, nao descarta** —
nenhum concurso sai do radar por nao estar nela. Ela mora em
`config/alvo.yml`, nunca no codigo; bater no alvo principal fura o filtro de
distancia e o teto de avisos, e vale ate para noticia. A lista `de_olho` do
mesmo arquivo fura o teto e ganha cartao na tela Analises > Edital para a
**Guarda Municipal de Florianopolis e de Balneario Camboriu**, sem virar alvo
nem entrar no estudo.

Para todo o resto continuam valendo os criterios de sempre, nesta ordem:

1. **Onde a prova e aplicada.** Grande Florianopolis ou perto. Fora do alvo,
   este e o filtro principal; o cargo e secundario.
2. **Se eu posso prestar.** Superior em Sistemas de Informacao. Muitos cargos
   pedem "superior em qualquer area" — esses servem.
3. **Salario.** Acima de R$ 5.000 e o alvo. Nao e corte: abaixo disso continua
   aparecendo, so mais embaixo no ranking.

Consequencia pratica disso, e e importante: as materias que interessam sao as
de **carreira policial e seguranca publica** — Direito Constitucional, Penal,
Processo Penal, Administrativo, Legislacao Especial, Direitos Humanos,
Portugues, Raciocinio Logico, Atualidades. **Nao** e TI.

E as bancas que importam nao sao as nacionais de sempre. Em SC o peso esta em
**FEPESE**, ACAFE, IESES, FURB, Instituto o Barriga Verde, e nas de seguranca
publica (IBFC, Instituto AOCP, FUNDATEC, Consulplan, e o Cebraspe nas
federais). Qual banca fez qual concurso e coisa para **confirmar lendo o
edital**, nunca para afirmar de memoria.

## Regra de relevancia geografica

Tres aneis, configurados em `config/regioes.yml` (nunca fixos no codigo):

1. **nucleo** — Regiao Metropolitana da Grande Florianopolis.
2. **proximo** — Itajai, Balneario Camboriu, Brusque, Tubarao, Laguna,
   Imbituba, Blumenau, Lages e vizinhos. Blumenau (~2h) e Lages (~3h) estao
   aqui por escolha minha, nao por tempo de estrada.
3. **remoto** — qualquer outro lugar. So interessa se o edital disser que ha
   prova em Florianopolis.

Como decidir o anel, em ordem de confianca:

- **concurso de SC**: pelo municipio do orgao, extraido do titulo/resumo;
- **federal ou de outro estado**: so pelo texto do edital em PDF, procurando as
  cidades de aplicacao. Sem edital lido, fica `indefinida` — **nunca chute**;
- guarde sempre *por que* foi classificado assim, em `motivo_relevancia`:
  eu preciso poder auditar a decisao.

Concurso irrelevante **nao e apagado**: fica marcado, para eu corrigir a regra.

## Ciclo de vida do concurso

O radar acompanha desde antes do edital. Campo `situacao`: `prevista` →
`autorizado` → `banca_definida` → `edital_publicado` → `inscricoes_abertas` →
`encerrado`. `banca_definida` e o sinal mais valioso: a contratacao da banca
sai **2 a 4 meses antes do edital**, e da tempo de estudar o padrao dela.

## Estado atual (03/10/2026; detalhe no [historico](docs/historico.md))

**Pronto:** o radar (fases 1-15), a especificacao e o **Ciclo 1 de estudo,
rodando desde 28/09** (`config/cronograma.yml`: tela Hoje - o cronometro e a
dobra dos blocos sao os dois unicos JS, so nesta tela e dispensaveis -,
caderno de erros, Semanas, Minhas materias; automacao no Windows). E o
**pedido de evolucao** ([roteiro](docs/roteiro.md),
[progresso](docs/progresso.md)), etapas 1A a 8: a fonte unica das metricas, a
arvore de conteudos (materia > assunto > subassunto > elemento) com alvo,
complementar e fora separados, a incidencia e os padroes, o desempenho por
conteudo com a amostra, a geracao com escopo fechado, a ficha de estudo de
cada tema (61 em `data/fichas.json`), os selos do novo.md (🟢 oficial, 🔵
acervo, 🟡 automatico, 🟣 IA) gravados no dado, e o site inteiro no design
system. A **auditoria final** ([auditoria_final](docs/auditoria_final.md))
confere a §23 do novo.md: **18 de 19 itens atendem com o dado real**.
**Correcoes depois da auditoria (03/10, decisoes 63 a 66):** o "Onde estudar
primeiro" nao soma mais o alvo e o complementar; o backup das 23h30, que
falhava desde 27/09, roda com a pasta suja; a lista de leis alteradas depois
das provas existe (15 itens, 17 questoes, por conferir:
[leis_alteradas](docs/leis_alteradas.md)); e os docs foram revistos. **O ciclo
especifico (pedido de 03/10):** feitas a 2A - o diagnostico e o simulado de
07/11 mostram de quais assuntos e subassuntos sao as questoes e criam a rodada
com essa composicao (decisao 67) - e a 2B - o simulado do Qconcursos sem
numero escrito a mao, a revisao semanal, o R+7 dos diagnosticos e a
comparacao de 07/11 (decisoes 69 e 70); faltam a 2C e a secao F.
Acervo: 8.433 questoes (as 170 do alvo classificadas e conferidas; 122 provas
complementares aceitas); 50 geradas; banco na versao 4.
**Falta, de voce:** conferir as 61 fichas, o complementar (as automaticas,
por amostra - B.8) e os 15 itens da lista de leis; o **Ciclo 2**, depois do
simulado de 07/11 e antes de 09/11.
**Conferir:** a primeira noite do backup consertado (`data/logs/` ou a tela
Mais) e o Actions de 04/10, o primeiro com a 2A e a 2B (pendencias A e D); o de
03/10 foi verde.
**Em aberto:** a media "por prova" dos Macetes sem o numero de provas, o
`?tema=` dos Macetes, o numero de questoes das faixas (ainda o do plano; o R+7
dos diagnosticos refaz 5 erros), os temas sem no e o Portugues sem filtro do
Qconcursos, e os
achados da varredura de 03/10 - entre eles, o "Onde estudar" que ainda nao le
a arvore de conteudos (pendencia F). Ordem e detalhe em
[docs/pendencias.md](docs/pendencias.md); arvore no [README](README.md);
banco em `data/radar.db`.

**Arquitetura a preservar:** cada fonte e um arquivo isolado em `collectors/`,
herda de `Coletor`, devolve `list[ItemColetado]` e esta em `COLETORES`
(`servico/coleta.py`) - nada fora de `collectors/` sabe de onde vem o dado. O
`servico` e um pacote, um arquivo por assunto; escreva `servico.funcao(...)`.
**Toda contagem de questao, acerto e erro passa pelo `servico/metricas.py`**:
tela nenhuma refaz a conta, e template nenhum soma. **Todo minimo de amostra sai do
`config/amostra.yml`**, pelo `radar/amostra.py`: nenhuma tela tem regua propria.
As excecoes declaradas (pendencia F): o 3 do `servico/erros.py` (fatia de
motivo de erro, nao acerto), o `MINIMO_PARA_EVOLUCAO` (20, `servico/metricas.py`),
o `MINIMO_PARA_TENDENCIA` (50, `macetes.py`) e o "base pequena" de menos de 3
provas (`PROVAS_PARA_TENDENCIA` no `servico/cartoes.py`, e o `length < 3` de
tres templates). **A prioridade de um tema sai do `config/prioridade.yml`**,
pelo `radar/prioridade.py`, e a ficha de estudo do `radar/fichas.py`: o tema e
reconhecido pelo titulo da faixa, sem o prefixo, e o texto escrito mora em
`data/fichas.json`, 🟣 com a procedencia. **O desempenho por conteudo e do
`servico/desempenho_por_conteudo.py`**, e os dois recortes - medido no radar e
anotado - **nunca sao somados na tela**, so no estado da amostra.
**Os selos moram no `radar/origem.py`**, e quem escolhe a cor e o dado: o
servico grava a origem (`origem`, ou `origens` quando junta partes) e o
template so desenha; `--selo-*` so no `design.css`, e a meta do dia tem as
cores dela. **A composicao das rodadas que medem** (diagnostico e simulado no radar) **sai
do `servico/composicao.py`** (decisao 67): so questao real da FEPESE, do alvo e
do complementar aceito, e gravada na rodada; a do simulado do Qconcursos
tambem, por tema estudado (decisao 69). **O sabado** - a revisao semanal, o
R+7 dos diagnosticos e a comparacao de 07/11 - **sai do `servico/sabado.py`**
(decisao 70). **Alvo, complementar e
fora saem do `servico/evidencia.py`** (uma regra, nunca somados; e prova
complementar so entra em estatistica se estiver aceita no
`data/acervo_complementar.json`), e tudo que
aponta para um conteudo usa o caminho do no (`data/conteudos.json`); a
classificacao reconhece a questao pela CHAVE (enunciado + alternativas), nunca
so pela impressao do enunciado.
Mudanca de estrutura do banco vira passo novo em `migracoes.py`.

## Fontes de dados

Nao existe API oficial unica de concursos no Brasil.

- prefira **RSS e dados abertos** a raspagem de HTML, sempre;
- **nao** raspe site cujos termos proibem (Qconcursos, por exemplo) nem
  conteudo atras de login ou paywall;
- respeite `robots.txt` **sem excecao**, mantenha o atraso e identifique-se no
  User-Agent - a classe `Coletor` faz os tres. O DOM/SC, o DOU e o Querido
  Diario estao fora por isso; o Planalto tambem, que so responde a navegador;
- guarde sempre o link original: isto e um indice pessoal, nao uma copia do
  conteudo de ninguem.

## Como trabalhar aqui

- **trabalhe sempre na branch `main`.** Nao abra branch nem PR;
- **commit e push ao fim de cada etapa**, nunca deixando trabalho so no disco;
- **se uma decisao mudar, atualize `docs/decisoes.md`** na mesma etapa;
- **uma coisa por vez.** Uma mudanca, testada, e so entao a proxima. Nao
  refatore o que nao faz parte do pedido. **Uma conversa por etapa:** ao fim,
  atualize os docs e o "Estado atual";
- **teste nunca depende do Windows nem da data de hoje** (o Actions e Linux);
- **questao gerada por IA TREINA, nunca MEDE**: vive em `questoes_geradas`,
  fora de tudo que conta o que a banca cobra, e o acerto nela e um segundo
  numero - nunca somado ao das reais;
- **dado vindo de IA so entra com procedencia** (modelo e data), e **nunca
  apresente como saida dela um texto que ela nao escreveu**: simulacao mostra
  o PEDIDO, nao um exemplo de resposta;
- todo coletor e todo classificador precisa de **teste com dado fixo**
  (fixture em arquivo), nunca teste que va a internet;
- antes de dizer que terminou: `pytest -q` passando **e** o comando afetado
  rodado de verdade no terminal;
- nao adicione dependencia sem justificar em uma linha;
- **me diga quando nao souber** em vez de inventar seletor de HTML, URL ou nome
  de campo. Se precisar da estrutura real de uma pagina, peca para eu baixar e
  colar — o Claude Code na web **nao tem internet aberta**.
