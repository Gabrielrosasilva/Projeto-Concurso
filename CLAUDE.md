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

**Fases 1, 1.5, 1.6, 2 e parte da 2.5 prontas:** feed RSS coletando,
classificador de relevancia, carga inicial do historico, avisos no Telegram, e
leitura da pagina do post para prazo de inscricao, banca e lotacao.

```
src/radar/
├── config.py       le ambiente. Nenhum efeito colateral no import.
├── models.py       tabelas `concursos`, `questoes`, `simulados` e
│                `respostas_de_simulado` (SQLAlchemy 2.0, estilo Mapped)
├── db.py           engine preguicoso + context manager de sessao
├── servico.py      roda coletores, grava com upsert, classifica, consulta
├── regioes.py      le config/regioes.yml: em que anel um municipio esta,
│                e qual e a grafia canonica dele
├── classificador.py  tipo, municipio, salario e relevancia, a partir do titulo
├── avisos.py       monta e manda a mensagem no Telegram
├── detalhes.py     le a pagina do post: prazo, banca e municipio de lotacao
├── provas.py       acervo: acha, baixa e cataloga edital, prova e gabarito
├── questoes.py     separa o caderno em questoes, com materia e gabarito
├── macetes.py      conta o costume da banca: forma de perguntar, questao
│                repetida, palavra frequente, letra do gabarito
├── util.py         fuso e formatacao de data
├── cli.py          comandos typer: coletar, listar, favoritar, avisar, web
├── collectors/
│   ├── base.py                  Coletor + ItemColetado; cuida de robots.txt,
│   │                            User-Agent e atraso entre requisicoes
│   ├── concursos_no_brasil.py   fonte 1: feed RSS, com paginacao (?paged=N)
│   │                             para a carga inicial do historico
│   └── fepese.py                fonte 2: API REST do WordPress da FEPESE
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
- PDF nao vai para o git. Vai o manifesto `data/provas.json`, com sha256, e
  `radar baixar-provas` reconstroi a pasta. Medido: 29 documentos deram
  37 MB em disco contra 18 KB de manifesto;
- caminho no manifesto usa barra normal mesmo no Windows, senao a outra
  maquina nao acha o arquivo;
- o acervo comeca pelo concurso ENCERRADO e perto de casa: encerrado e o
  que tem prova publicada, e perto e o padrao de banca que me serve;
- a materia de cada questao vem do cabecalho de secao do proprio caderno,
  e o gabarito vem marcado no texto (Check-square). Nada disso e adivinhado;
- a leitura do caderno parte das ALTERNATIVAS, nunca dos numeros: a ordem
  do texto e embaralhada pelas duas colunas, e o enunciado pode ter lista
  numerada dentro;
- linha que se repete em toda pagina e mobilia e sai do texto. Foi assim
  que a sujeira na ultima alternativa caiu de 5,1% para 1,1%;
- concurso municipal de outro estado e `remoto`, nao `indefinida`: prova de
  municipio de SP e aplicada em SP. `indefinida` fica para quem pode mesmo
  aplicar em Florianopolis (federal, nacional, ou sem UF);
- a lista padrao esconde `remoto`, `indefinida` e `noticia`. Nada e apagado:
  a pagina e a CLI mostram tudo com --todos;
- avisos sao por **Telegram**. WhatsApp foi avaliado e descartado: o oficial
  exige conta Meta Business, numero separado e template aprovado para mensagem
  proativa; o nao oficial arrisca banir meu numero pessoal;
- o aviso leva SEMPRE o link da fonte junto;
- viram mensagem: `nucleo`, `proximo` e `indefinida`. O indefinido entra de
  proposito - federal sem UF pode aplicar prova em Floripa, e perder um
  concurso bom e pior que receber dois avisos a toa;
- cada concurso e avisado uma vez so (coluna `avisado_em`), e o teto e de 10
  mensagens por coleta. O teto e protecao contra regra quebrada virar 200
  notificacoes de madrugada;
- token e chat_id SO em variavel de ambiente: `.env` na maquina, Secrets no
  Actions. O log nunca imprime a URL da API, porque ela carrega o token;
- a carga inicial anda para tras pelo `?paged=N` do proprio feed, e nao por
  raspagem de HTML nem pelo sitemap. Conferido no site real: o sitemap existe
  mas para em junho/2026, e nao traz titulo - so URL. O feed paginado traz
  tudo e usa o mesmo parser;
- favorito e escolha minha: a coleta nao mexe, e NENHUM filtro o esconde -
  nem distancia, nem salario, nem prazo vencido. Os favoritos ficam num mural
  fixo a esquerda, visivel em qualquer aba;
- na tela, TODA informacao vem com rotulo ("Banca: FEPESE", nao "FEPESE"), e
  `nucleo` aparece como "Perto";
- dois campos tem dono e o classificador nao encosta neles: o salario que eu
  digitei (`salario_manual`) e o municipio que veio da pagina do edital
  (`municipio_confirmado`). Sem a segunda trava, um `reclassificar` desfazia o
  trabalho do `detalhar` e a SEFAZ SC voltava de `nucleo` para `indefinida`;
- os campos numericos da rota web chegam como TEXTO e sao convertidos por
  `util.converter_valor`. Formulario HTML manda todo campo, inclusive o vazio:
  declarar `salario_min` como numero fazia `salario_min=` virar erro 422 e
  derrubar a pagina inteira, nao so aquele filtro;
- o filtro de banca aceita nome curto e nome por extenso (FCC = Fundacao
  Carlos Chagas), pela mesma tabela de apelidos de `detalhes.BANCAS`;
- a busca por palavra ignora acento, via funcao `sem_acento` registrada no
  SQLite, e procura tambem no municipio;
- com filtro ligado e zero resultado, a tela diz que foi o FILTRO que nao
  achou nada - dizer "nenhum concurso perto de voce" levaria a conclusao
  errada;
- o filtro de salario exclui quem nao tem valor conhecido, e a tela avisa
  quantos ficaram de fora. A primeira versao incluia os nulos para nao
  esconder concurso bom, e o resultado foi um filtro que nao filtrava: 1.115
  dos 2.185 nao trazem salario no titulo;
- `situacao` vem das datas de inscricao quando ha prazo conhecido, e do
  TITULO quando nao ha: "tem concurso autorizado" vira `autorizado`, "define
  banca" vira `banca_definida`, "deve sair" vira `prevista`. Data e fato,
  titulo e interpretacao - por isso a data manda;
- a aba de noticias NAO filtra nada: nem anel, nem fase, nem tipo. Quem
  procura "PM" quer saber de qualquer policia militar, onde estiver e na fase
  em que estiver. Ela ordena por ANDAMENTO, e nao por data;
- valor neutro da fonte nao rebaixa o que ja se sabe: "desconhecida" na
  situacao e tratado como nulo em `VALORES_SEM_INFORMACAO`;
- `reclassificar` passa o municipio e o tipo ja conhecidos para o
  classificador. Sem isso ele reextraia do titulo e os 107 concursos da FEPESE
  perdiam o municipio - o titulo dela nao tem "(SC)". Reclassificar existe
  para reaplicar a regra do ANEL, nao para reextrair o que a fonte ja deu;
- o formulario da web usa autocomplete="off": o navegador restaurava o valor
  digitado antes e o campo aparecia preenchido sozinho;
- o DOM/SC esta FORA de raspagem: robots.txt com "Disallow: /" para todos.
  Nao insista; o caminho legitimo e o alerta por e-mail do proprio site;
- fonte que sabe o que publica declara `tipo` no ItemColetado, e o
  classificador respeita. A FEPESE publica num tipo de post `concurso`, entao
  nao ha o que adivinhar pelo titulo - sem isso, "2026 - Prefeitura Municipal
  de Sao Jose" virava `noticia`, porque nao tem a palavra concurso no titulo;
- municipio conhecido decide o anel mesmo sem UF declarada: config/regioes.yml
  so tem municipio catarinense. So nao vale se a fonte afirmar outro estado;
- aviso e sobre NOVIDADE: nao avisa o que ja encerrou nem o publicado ha mais
  de 30 dias, a menos que a inscricao esteja aberta. Sem isso, ligar uma fonte
  nova despejava o historico dela no celular;
- prazo de inscricao, banca e lotacao vem da PAGINA DO POST, nao do PDF do
  edital. Sai mais barato e cobre a maioria dos casos;
- `radar detalhar` nao le a pagina de todos: segue a prioridade nucleo/proximo,
  depois SC indefinida, depois federal. Outro estado nunca;
- pagina que cita varios municipios nao define municipio nenhum. Edital de
  secretaria estadual lista o estado inteiro, e escolher um seria chute;
- a lacuna do "complete as frases" nao esta escrita no caderno: a FEPESE
  desenha o tracinho como grafico e sobra so espaco em branco. `marcar_lacunas`
  troca corrida de 3+ espacos por ____, e roda ANTES de juntar as linhas -
  lacuna no comeco e no fim da linha some se juntar primeiro. 258 enunciados
  (5,1%) ganharam lacuna, e em 188 de 193 o numero de lacunas bate com o numero
  de itens da resposta;
- `radar questoes --refazer` atualiza a questao no lugar, pela chave (prova,
  numero). Nao apaga para regravar: o simulado guarda o id da questao;
- municipio e gravado SEMPRE na grafia de config/regioes.yml. Cada fonte
  escreve de um jeito ("Palhoca" e "Palhoca" com cedilha, Florianopolis em 4
  grafias), e qualquer conta por municipio saia errada. Municipio de fora de SC
  volta como veio: o YAML so tem catarinense;
- a previsao de abertura usa o ritmo do proprio municipio, mas LIMITADO pela
  validade legal (2 a 4 anos), e por MEDIANA. Sem isso, buraco de cobertura
  virava absurdo: Tubarao, com 2011 e 2026 conhecidos, dava "proximo em 2041";
- a previsao carrega sempre o motivo e os anos que a embasam, e a tela avisa o
  que o historico NAO cobre (outra banca entre 2021 e 2025);
- a aba Macetes nao calcula nada antes de a banca ser escolhida, e o menu de
  bancas vem das PROVAS baixadas, nao dos concursos. As citadas sem acervo
  aparecem numa nota explicando que falta um coletor por banca;
- o assunto dentro da materia sai de um catalogo de palavras-chave escrito a
  mao em `macetes.CATALOGO_DE_ASSUNTOS`. Cobertura em enunciados distintos:
  portugues 76%, informatica 61%, gerais 59%, raciocinio 53%. O que sobra e
  contado como "sem assunto detectado" - nunca empurrado para um assunto;
- a materia dominante do recorte so e afirmada com 60% ou mais das questoes.
  "Crase" da 56 de 59 em Portugues; recorte que mistura nao tem materia;
- questoes por caderno divide pelos cadernos em que AQUELA materia apareceu.
  Temas de Educacao so cai em prova de professor: dividir pelo total faria
  parecer que cai pouco quando cai muito onde cai;
- na aba Macetes, gabarito e palavras contam UMA VEZ POR ENUNCIADO, e
  materia e forma de perguntar contam todas. Buscando "crase" saem 59 questoes
  e so 7 enunciados: a mesma aparece em 38 cadernos e a resposta e "d", o que
  dava "letra d em 64%" e levaria a chutar d;
- abaixo de 50 enunciados diferentes a pagina NAO afirma nada sobre a letra do
  gabarito. Com 7 questoes o que parece tendencia e sorteio;
- no acervo inteiro as cinco letras ficam entre 19,5% e 20,5%: o "chute na C"
  nao existe na FEPESE, e a tela diz isso;
- a aba Macetes nao inventa: pegadinha especifica e macete de memorizacao nao
  saem de contagem, e ficam de fora ate a leitura por IA entrar;
- a pagina de erro 404 detecta sozinha o caso "servidor rodando codigo
  antigo", comparando a data dos .py com a hora em que subiu. E o sintoma mais
  confuso que aparece aqui: o link esta na tela (template e lido do disco a
  cada visita) e a rota nao existe (codigo e lido so na partida);
- o simulado guarda o estado no BANCO, nao na sessao do navegador: da para
  fechar a pagina no meio e voltar depois, e o F5 nao responde de novo;
- o sorteio do simulado e por ENUNCIADO, nao por linha: dos 5.021 registros so
  1.815 sao perguntas diferentes, e uma aparece em 44 cadernos;
- simulado sem materia escolhida usa as materias que caem em qualquer concurso
  (Portugues, Raciocinio, Informatica, Conhecimentos Gerais). O acervo nao tem
  prova de Guarda Municipal nem de Policia Penal, e essas quatro treinam
  mesmo assim;
- nao somar coluna booleana no SQL: o SQLAlchemy devolve a soma com o tipo da
  coluna, entao 2 acertos voltam como True e viram 1. Use `case(...)`;
- o tipo `noticia` e decidido primeiro pelo CAMINHO da URL: /concursos/ e
  concurso, /beneficios-sociais/ e noticia. Isso pega o que a palavra no
  titulo nao pega ("INSS paga hoje com vagas para todos").

## Roadmap

```
1.55 FALTA: perfil/elegibilidade (idade, CNH, escolaridade) e campo de
     notas. Favoritos e filtro de remuneracao ja estao prontos
1.7  PARCIAL: a FEPESE entrou como fonte 2. O DOM/SC ficou de fora porque
     o robots.txt dele proibe robo; ver README. Falta: DOU (federal), o
     Querido Diario quando a API voltar, e o sinal "contrataram a banca"
2.2  export .ics para o calendario
2.5  FALTA: ler o PDF do edital para escolaridade, idade maxima, CNH e TAF
     + deteccao de retificacao por hash. Prazo, banca e lotacao ja saem da
     pagina do post, sem abrir PDF nenhum
3    PARCIAL: acervo da FEPESE funcionando, com manifesto versionado.
     Falta: prova substituta (quando nao ha prova do orgao, trazer a mais
     parecida - mesma banca e mesmo cargo em outro lugar)
4    PARCIAL: 5.021 questoes extraidas, com materia, gabarito e lacuna
     marcada, e incidencia por materia funcionando. Falta: o ASSUNTO
     fino dentro de Conhecimentos Especificos (Direito Penal, Primeiros
     Socorros...), que e onde entra a API da Claude
5    PRONTA: modo simulado na web, com acerto por MATERIA. Por assunto
     fino depende da fase 4 terminar
6    PRONTA: previsao de abertura por municipio, na web e na CLI
7    PARCIAL: aba Macetes com o costume da banca por contagem. Falta a
     parte que so a IA faz: pegadinha especifica e macete de memorizacao
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
