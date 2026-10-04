# Pendencias

Tudo o que ficou por fazer, incompleto, quebrado ou combinado para depois.
Foi montado em 01/10/2026, a partir do git (ate `c8609b5`) e de uma varredura
do codigo. **Quando uma pendencia for resolvida, apague-a daqui e registre no
[historico](historico.md); se ela virou decisao, em [decisoes.md](decisoes.md).**

Legenda: 🔴 nao feita · 🟡 feita pela metade · ⚪ nao verificada.

## A. Quebrado agora

A A1 (Actions vermelho desde 26/09) saiu em **02/10/2026**: a coleta diaria
voltou a rodar e commitou `coleta: 2026-10-02`. O `coleta.yml` roda
`pytest -q` ANTES de coletar, e passo que falha aborta o job - o commit e a
prova de que a suite passou no Linux.

- ⚪ **Conferir a primeira noite do backup consertado** (03/10, decisao 64).
  O `radar sincronizar` deixou de exigir a pasta limpa e o `git add` deixou de
  receber arquivo que nao existe; o comando foi rodado de verdade numa copia
  do repositorio, com o banco real e a pasta suja. Falta a primeira execucao
  da tarefa das 23h30 no repositorio de verdade: o log de
  `data/logs/sincronizar-2026-10-03.log` (ou a tela Mais) tem que terminar em
  `RESULTADO: ok`, e o GitHub ganhar um commit `sincronizar: 2026-10-03` -
  e com ele os 4 simulados de 28 e 29/09, que ate hoje so existem no
  `radar.db`;
- 🔴 **`?tema=` na tela Macetes** (achado na conferencia da 7A, 03/10): o
  parametro que forca o tema claro/escuro pela URL e o mesmo nome do filtro
  "Materia ou tema" do recorte por banca. `/macetes?tema=claro` pinta a tela
  de claro E procura o tema "claro". O botao da barra nao sofre disso (ele
  grava o cookie e tira o `tema` da URL na volta); so quem digita o
  parametro. O conserto e renomear um dos dois - e o do filtro aparece em
  link salvo, entao a escolha e sua.

## B. O desenho do estudo (decisao tomada, desenho aberto)

Veio do primeiro dia do Ciclo 1 (28/09) e foi registrado em
[decisoes.md](decisoes.md) como **direcao**. As etapas 2 a 6B transformaram a
maior parte em codigo - o que foi feito de cada sugestao esta marcado abaixo;
o que sobra esta nos itens 🟡 e nas B.7 a B.10.

O que foi observado em 28/09:

- o conteudo e o peso de cada faixa vieram do **edital de 2019**; a frequencia
  com que a FEPESE cobra cada tema nunca foi medida, porque as questoes nao
  tem assunto gravado;
- a faixa de teoria da manha de 28/09 (50 min para os arts. 1o a 12 do CP) nao
  diz o quanto aprofundar; video por artigo (~15 min cada) estoura o tempo;
- a lei seca de 40 min e igual em 30 faixas (~20 h): ler o artigo inteiro,
  grifando "salvo", "somente", "vedado". Eu a considero inutil assim;
- as questoes da tarde sao genericas ("15 questoes sobre Aplicacao da lei
  penal"): nao ha distribuicao por artigo;
- as 40 questoes geradas sao todas `do_zero` (nenhuma ancorada em questao real).

Sugestoes de 28/09, em ordem de impacto, e o que foi feito de cada uma:

1. 🟡 gravar assunto e artigo nas questoes FEPESE de Direito, comecando pelas
   provas de Policia Penal e Agente Penitenciario SC. **Feito na 3A para as
   170 do alvo** (todas as materias, nao so Direito), pelo Claude Code;
   e **conferido por voce em 02/10**. O complementar e da 3B (a conferencia
   dele ainda nao tem tela: ver B.8);
2. ✅ um mapa de incidencia por tema. **Feito na 3A** (`radar incidencia` e
   Analises > Incidencia), com os rotulos sem previsao: "apareceu nas 2
   provas", "apareceu em 1 de 2", "nao apareceu nas provas analisadas". **Na
   faixa, feito na 6B (02/10):** a ficha de cada tema traz "Como a FEPESE
   cobrou", com o alvo e o complementar em linhas separadas e a amostra;
3. 🟡 trocar a lei seca por "artigo cobrado": 10-15 min lendo so os artigos
   que cairam, mais a lista das pegadinhas, cada uma com o numero da questao
   real; o tempo que sobra vai para questoes. **Provisorio feito na 6A
   (02/10):** a lei seca virou "dirigida", 20 min, so os artigos-chave do
   `essencial` do dia (selecao do plano, nao incidencia). **Na 6B (02/10)**, a
   ficha de cada tema lista as questoes reais com o artigo de cada uma e as
   pegadinhas com o numero da questao; a faixa de lei seca continua com os
   artigos do `essencial`;
4. 🟡 questoes distribuidas pela incidencia, nao uma por artigo (FEPESE real
   primeiro; as da IA so no modo `variacao`). **Na 6B (02/10)**, a ficha manda
   comecar pelas reais do escopo e traz um `radar gerar` por no; o numero de
   questoes de cada faixa continua o do plano;
5. ✅ teoria com teto: uma fonte por tema, nunca video por artigo.
   **Provisorio feito na 6A:** teoria de 40 min com "uma fonte so: passou do
   tempo, siga para a fixacao" no detalhe. **A ficha da tarefa, feita na 6B
   (02/10):** cada tema diz o que ler exatamente e uma fonte so.

**Perguntas que ficaram sem resposta** (preciso delas antes de qualquer
roteiro):

1. Quais provas FEPESE com Direito Penal estao no acervo? **Respondida na 3B**
   (`docs/complementar.md`): pelo nome da materia, so o Socioeducativo 2013 e
   2016, com 2 questoes cada. Nas prefeituras, Direito Penal so aparece dentro
   de "Conhecimentos Especificos" - 139 indicios por termo em 76 provas, que
   so a classificacao confirma.

A pergunta 2 (quem classifica) foi respondida na Etapa 0 e feita na 3A: o
Claude Code, pelo `radar classificar --pedido/--importar`, e voce confere.

As perguntas 3 (versao enxuta agora) e 4 (o Anki continua?) foram respondidas
e feitas na Etapa 6A: rotina nova a partir de 02/10 e `anki: desativado`.

**Quantas questoes dos arts. 1o a 12 do CP cairam em 2019?** Respondida na
3A, por consulta a classificacao: **1** (2019-q51, a correta e o art. 8o; as
alternativas passam pelos arts. 2o, 3o e 4o). Em 2013 foram 3 (q50, art. 8o;
q51, art. 7o; q53, art. 2o). As quatro estao pendentes: o programa de 2019
nao lista "aplicacao da lei penal".

### B.7 🔴 Erros de extracao nas provas do alvo

O `radar auditar` (Etapa 3A) acusa 25 questoes do alvo com suspeita, listadas
em `docs/auditoria.md`: o titulo da materia seguinte ou o rodape da FEPESE
grudado na alternativa "e" (20), a grade de respostas na 2019-q99, o numero
dentro do enunciado na 2019-q100 e "e cor-" cortado em 2019-q51 a 55. Mais um
que a verificacao nao pega: a 2013-q20 perdeu a imagem do icone do Excel. O
texto nao foi corrigido; o conserto e no leitor do caderno (`questoes.py`).

### B.8 🟡 Classificacao do acervo complementar (Etapa 3B, passo 4)

As 122 provas aceitas no `data/acervo_complementar.json` estao no acervo.
**Feito (02/10):** as 80 do Socioeducativo 2013 e 2016 (lote 1), com 62
classificadas e 18 pendentes com motivo; a incidencia ja mostra o complementar
por no nessas materias. **Falta o resto**, e a linha diz quantas ("993 sem
classificacao ainda" em Portugues):

1. ✅ **os 80 do Socioeducativo 2013 e 2016** - feitos em 02/10;
2. ✅ **os blocos genericos** - feitos em 02/10: das 125 com indicio,
   44 classificadas e 81 sem linha (conteudo do cargo daquele concurso);
3. ✅ **Portugues e Raciocinio Logico pelo catalogo** - feitos em 02/10: 92 + 16
   propostas automaticas 🟡.

**O que sobra na B.8:**
- **a sua conferencia**: 44 do lote 2 e 108 do catalogo esperam conferencia -
  as do catalogo por AMOSTRA (20 por materia; taxa de erro alta, o lote volta).
  **A tela de Conferencia lista so o alvo**: para conferir o complementar ela
  precisa de um filtro de evidencia, que ainda nao existe. **Decidido em 02/10
  (decisao 18): fica para a Etapa 5**, quando a classificacao passar a
  escolher questao para treino - **e a Etapa 5 nao o fez** (ela passou a
  escolher pela classificacao, mas a tela continua so com o alvo; achado da
  varredura de 03/10). Ate la o complementar vale como esta, com a
  procedencia a vista;
- **as questoes sem linha**: 81 do lote 2 (conteudo de outro cargo, de
  proposito) e, em Portugues e Raciocinio Logico, as que o catalogo nao cobre
  (47 sem palavra, 23 ambiguas, 22 sem par no edital em Portugues; 21 e 8 em
  Raciocinio). Ampliar o catalogo ou o mapa do `config/complementar.yml`
  resolve parte;
- **os 1.738 "Conhecimentos Especificos" distintos sem indicio nenhum**: sao
  conteudo do cargo daquele concurso (enfermagem, pedagogia, contabilidade).
  Nao ha por que classifica-los.

### B.10 🔴 Blocos de materia trocados no Socioeducativo 2013 e 2016

A classificacao do lote 1 (02/10) achou 8 questoes no bloco errado, nos dois
cadernos do Socioeducativo:

- **2013-q49, 2013-q50, 2016-q49 e 2016-q50**: sao de Direito Processual Penal
  (inquerito na acao publica condicionada, crimes de responsabilidade de
  funcionario publico, nota de culpa) e estao no bloco "Legislacao Estadual";
- **2013-q59, 2013-q60, 2016-q59 e 2016-q60**: sao de Legislacao Estadual
  (Estatuto do Servidor de SC, Constituicao Estadual) e estao no bloco
  "Direito Processual Penal".

Isso vem da separacao do caderno por materia (`questoes.py`), que erra a
fronteira entre blocos quando o titulo da materia seguinte gruda no texto - o
mesmo defeito da B.7, agora mudando a MATERIA da questao. Consequencia hoje:
as oito estao pendentes (a importacao, com razao, nao deixa trocar de materia
quando ela esta no edital), e a contagem "pelo nome da materia" do
complementar erra por 4 em cada uma das duas materias. **Nada foi corrigido.**
Duas saidas, nenhuma escolhida: consertar a fronteira no leitor e reextrair,
ou corrigir a materia dessas 8 no banco com copia antes e "antes x depois".

### B.9 🔴 Defeitos do acervo complementar achados na 3B

- **24 provas com o mesmo sha256 em dois enderecos.** Parte e o mesmo caderno
  em http e https (os tres de Florianopolis 2025); parte sao dois hotsites de
  Palhoca (2024 emergencial e 2024 PS educa) com o mesmo `S07.pdf` e cargos
  diferentes - e no banco as duas provas tem so 24 das 40 questoes em comum.
  Ou a mesma prova entrou duas vezes, ou o hash do manifesto esta errado para
  elas. A validacao recusa a segunda; nada foi apagado;
- **31 provas com a numeracao furada**, 26 delas cadernos de 39 questoes de
  2023, e um caderno de 40 em que falta a questao 20. Mesmo tipo de defeito da
  B.7, agora no complementar. O conserto e no leitor do caderno
  (`questoes.py`).

## D. Combinado para depois

- 🟡 **Conferir a lista de leis alteradas** (`config/leis.yml`, `mudancas`;
  decisao 65). Ela existe desde 03/10: 15 itens, escritos pelo Claude Code a
  partir do texto compilado (Camara e ALESC), que pegam 17 questoes de 2013 e
  2019 - todos `conferida: false`, e por isso o aviso sai com o 🟣. Para cada
  item, leia a evidencia em [leis_alteradas.md](leis_alteradas.md) e troque
  para `conferida: true` (ou apague o item). Comece pelas 5 em que o gabarito
  oficial ficou errado: 2013 q64 e q66, 2019 q46, q71 e q75;
- 🔴 **Conferir as 61 fichas da 6B** (Hoje > Fichas, botao "Conferi esta
  ficha", ou `radar fichas --conferir <tema>`), comecando pelas da semana. Na
  conferencia, vale olhar os nos de cada uma: 13 ficaram sem no (decisao 43);
- 🔴 **Fichas de Direito Penal e Constitucional sem o texto vigente**: as 12
  foram escritas antes de a 6B adotar a conferencia pelo texto compilado
  (decisao 48). O CP e a CF tambem mudaram depois de 2019; refazer a
  conferencia artigo por artigo antes de estudar cada tema;
- 🔴 **Reclassificacoes que as fichas mostraram**: 2 questoes de regencia
  estao em "Emprego de tempos e modos verbais"; as de pronome do complementar
  estao em "Classes gramaticais variaveis", junto com substantivo e adjetivo;
  as de concordancia, crase, pontuacao e complemento nominal estao so no nivel
  do assunto, e por isso as fichas de tema nao as contam; "Regras de aplicacao
  geral" (Regras de Mandela) nomeia a Parte I inteira (regras 1 a 85);
- ⚪ **Pastas de teste em `data/copias/`**: 15 pastas `migracao-v0-para-v*`
  com `antigo.db` sao copias do banco de um teste, e nao do banco real (a
  causa saiu na 6B, decisao 50). Podem ser apagadas a mao. E o
  `migracoes.ultima_copia()` ordena pelo NOME, que comeca pela versao, e nao
  pela hora como diz a docstring: hoje acerta por acaso (v3 > v0);
- 🔴 **Importar macete e explicacao**: `radar gerar --pedido --macetes` e
  `--explicacoes`, e o `--importar` de cada um. `data/macetes.json` e
  `data/explicacoes.json` ainda nao existem;
- 🔴 **Assunto no Direito** (o item 1 do bloco B). Hoje: 0 questoes de Direito
  com assunto; "Onde estudar primeiro" so tem Portugues e Raciocinio Logico;
- 🔴 **Cronograma por IA**: fase futura da especificacao; so entra se a revisao
  espacada simples nao bastar, com o teto de gasto do `gerador.py`;
- 🔴 **Ciclo 2** (09/11 a 19/12, "o resto do programa") - **o passo 5 da 6B**
  (decisao 52): a faixa de 07/11, no fim do Ciclo 1, manda comparar o acerto
  por materia com o diagnostico de 03/10; e esse numero que decide o Ciclo 2.
  Depois dele: a proposta pela prioridade (`config/prioridade.yml`) e pela
  rotina da 6A, a minha aprovacao e so entao o `config/cronograma.yml` (as
  faixas gravadas no diario continuam contando; o check guarda materia e
  assunto). Prazo: antes de 09/11;
- 🟡 **Notificacao do Windows**: funciona (teste de 10 s e configuracoes do
  Windows conferidas), mas falta liberar a permissao no navegador;
- 🔴 **Macetes, "Quantas questoes caem numa prova"** (auditoria da Etapa 8):
  a fatia tem a base no centro do grafico, mas a media "8.5/prova" nao diz em
  quantas provas - a amostra fica pela metade (regra inviolavel 3);
- ⚪ **Conferir o Actions de 04/10**: o primeiro `coleta:` do radar-bot com o
  codigo da 2A, da 2B e da 2C. O de 03/10 foi verde (o commit `coleta: 2026-10-03`
  e a prova: o job roda o `pytest -q` antes de coletar);
- 🔴 **Acento fora da tela web** (o que sobrou da A2, feita na Etapa 1B so
  para a web): a saida do terminal (`cli.py`, ~100 textos, inclusive a
  linha do tempo de `radar eventos`, que ainda mostra "Situacao: a -> b"), a
  mensagem do Telegram (`avisos.py`: "Inscricoes abertas", "Inscricao ate" e
  a descricao crua do evento), o relatorio `docs/auditoria.md`
  (`auditoria.py`) e o `motivo_elegibilidade` gravado (`perfil.py`). Os nomes
  de assunto do `macetes.py` ("Concordancia", "Pontuacao"...) sao chave de
  casamento: a arvore de conteudos existe desde a Etapa 2, mas ligar esse
  catalogo aos nos dela e da 3A, com a classificacao. Prompts de IA ficam sem
  acento de proposito;
- ⚪ **Token do Telegram**: foi revogado depois de colado numa conversa.
  Confirmar que o novo esta so em variavel de ambiente / Secrets do GitHub.

- 🟡 **O ciclo 1 especifico (pedido de 03/10)**: a 2A, a 2B e a 2C estao
  feitas (as faixas que medem, o simulado do Qconcursos, o sabado e o assunto
  na propria faixa: decisoes 67, 69, 70 e 71). Da **secao F** (o Pedido 1),
  feitas a F1 a F6 (decisoes 74, 75, 77, 78, 79 e 80); falta o resto dela, em
  subetapas;
- ⚪ **O R+7 dos diagnosticos refaz 5 erros** (decisao 70): e o numero do
  plano. Com mais erros, os outros ficam para a rodada "So meus erros" da
  home. Se quiser refazer todos, e trocar o `questoes: 5` da faixa de 10/10 -
  decisao sua;
- ⚪ **Temas sem no e Portugues sem filtro** (achados da 2B): as fichas de LEP e de
  Portugues sem no (30 faixas de 03/10 a 07/11) deixam o tema, no simulado do
  Qconcursos, sem incidencia contada - e a faixa diz "a ficha nao aponta no da
  arvore" (2C); e as faixas de Portugues nao tem `filtro` do
  Qconcursos. Dar no a uma ficha e mexer no texto da IA (precisa da sua
  conferencia); o filtro, so com o caminho exato do Qconcursos, que eu nao
  sei - me passe se quiser;

- ⚪ **A gerada e unica pelo enunciado** (`QuestaoGerada.impressao`): dois
  comandos genericos iguais com alternativas diferentes viram uma so, e a
  importacao conta a segunda como repetida. Por desenho; no estoque, cada
  enunciado foi escrito com o que cobra;
- 🔴 **As 20 geradas de 28/09 estao com a materia "Aplicacao da lei penal
  (arts. 1º a 12)"**, e nao "Direito Penal": ficam fora do treino de Direito
  Penal no /geradas. E as 50 antigas tem so a materia no `conteudo`, entao
  nenhuma ficha as mostra. Corrigir e mexer em dado antigo - decisao sua;
- 🟡 **O /geradas treina pela materia, e nao pelo no**: a ficha lista as
  geradas do tema, mas manda treinar no /geradas, que mistura os temas da
  materia - inclusive os ainda nao estudados;
- 🟡 **A ajuda do `radar gerar`** ainda diz que o do zero "so entra quando nao
  existe questao real na materia"; desde a decisao 35 ele completa dentro do no;

## E. Cancelado

- **C1b, sirene para a Guarda Municipal de Florianopolis e de Balneario
  Camboriu**: nao e para fazer. O `de_olho` ja avisa com 👀 quando sair algo,
  que e tudo o que eu quero (ver decisoes.md).

## F. Achados da varredura de 03/10 (depois da Etapa 8)

A varredura dos docs contra o codigo e o banco achou estes pontos, que nenhuma
etapa tinha registrado. Os cinco que ela mandou corrigir na hora ja sairam
(decisoes 63 a 66 e a limpeza dos docs); estes ficam:

- ⚪ **Os termos frequentes empatados mudam de ordem a cada vez que o radar
  sobe** (achado do F6): na Incidencia e nos Macetes, as palavras com a mesma
  contagem saem numa ordem que o Python sorteia por processo, e no corte
  (as 8 primeiras) ate a palavra mostrada pode trocar. Desempatar em ordem
  alfabetica resolve;
- 🟡 **33 variacoes geradas sem a questao real de base identificada** (F3,
  decisao 77): 30 do estoque de 03/10 e 3 de 27/09. A base delas tem um
  enunciado que se repete no acervo com alternativas diferentes, e elas foram
  gravadas antes de a chave ser guardada; o selo diz que o acervo nao
  consegue identificar. As 30 do estoque podem ser religadas pelos pedidos
  que ficaram no historico da conversa de 03/10 (o texto de cada questao de
  base foi impresso la); as 3 de 27/09 nao tem registro. Decisao sua;
- 🟡 **As faixas do plano quase nao chegam a arvore** (achado do F5, decisao
  79): a faixa so conta num no pela chave `conteudo` do
  `config/cronograma.yml`, e so 6 faixas a tem. Ate 07/11, das 45 faixas de
  revisao nenhuma tem (38 so tem no pela ficha, que e da IA e esta por
  conferir); das 95 de estudo, 3. Sem ela, a tela Hoje nem mostra o seletor
  de conteudo, e o R+7, a teoria e a lei seca contam no dia e em no nenhum:
  o Meu desempenho nao ve o que eu estudei nas faixas, e a ultima revisao
  so vem das rodadas de revisao do radar e do estudo extra. Decisao sua:
  (a) deixar assim; (b) a faixa sem `conteudo` conta no no que ela cobre
  (`fichas.onde_na_arvore`) para o "estudado" e para as datas, nunca para o
  acerto - pelos `nos` do plano ja, e pela ficha so depois de voce
  conferi-la; (c) eu proponho a chave `conteudo` de cada faixa a partir das
  fichas, e voce confere antes de entrar no plano;
- ⚪ **O "estudado" do codigo e mais largo que a decisao 20**: qualquer faixa
  ou extra SEM questao deixa o no estudado (as constantes `TIPOS_DE_ESTUDO` e
  `EXTRA_DE_ESTUDO` de `servico/estudo.py` estao declaradas e sem uso). Hoje
  so o extra de revisao sem questao cai nisso; com a (b) ou a (c) acima, a
  faixa de correcao marcada tambem cairia;
- ⚪ **O 1-7-30 sem estudo conta da ULTIMA resposta de cada questao**
  (`estudo.situacoes`, `primeira_pratica`): questao refeita empurra o
  "primeiro contato" para a data da refeita. A evolucao ja conta toda
  resposta (decisao 79); a ancora da revisao ficou como estava;
- 🟡 **§14, item 7 do novo.md ("quais conceitos aparecem associados")**: as
  402 classificacoes sao todas principais; nenhuma questao tem conteudo
  associado, e a pergunta nao tem resposta;
- 🟡 **Minimos fixos fora do `config/amostra.yml`**: `MINIMO_PARA_EVOLUCAO`
  (20, `servico/metricas.py`), `MINIMO_PARA_TENDENCIA` (50, `macetes.py`),
  `PROVAS_PARA_TENDENCIA` (3, `servico/cartoes.py`) e o `length < 3` de tres
  templates (`foco.html`, `home.html`, `previsao.html`). Estao declarados no
  `CLAUDE.md` como excecao; leva-los ao `config/amostra.yml` e decisao sua;
- ⚪ **A lista de leis alteradas so tem o que as provas de 2013 e 2019
  cobraram.** Mudanca que nenhuma questao cobra (a saida temporaria so para
  estudo, as policias penais da EC 104/2019) fica de fora do aviso - esta em
  `docs/leis_alteradas.md`, "Casos de fronteira".
