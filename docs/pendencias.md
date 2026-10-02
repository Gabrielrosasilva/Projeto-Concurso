# Pendencias

Tudo o que ficou por fazer, incompleto, quebrado ou combinado para depois.
Foi montado em 01/10/2026, a partir do git (ate `c8609b5`) e de uma varredura
do codigo. **Quando uma pendencia for resolvida, apague-a daqui e registre no
[historico](historico.md); se ela virou decisao, em [decisoes.md](decisoes.md).**

Legenda: 🔴 nao feita · 🟡 feita pela metade · ⚪ nao verificada.

## A. Quebrado agora

### A1. 🟡 GitHub Actions: corrigido no PC, falta ver o verde la

Os tres testes que dependiam do Windows ou da data de hoje foram corrigidos na
Etapa 1A (01/10/2026; detalhe no [historico](historico.md)). A suite passa no
PC (1.840) e com o relogio simulado em 20/10/2026, 10/11/2026 e 15/03/2027.
**Falta:** disparar o "Run workflow" na aba Actions (ou esperar o das 09:00
UTC) e conferir o verde. Verde la, esta pendencia sai daqui.

## B. O desenho do estudo (decisao tomada, desenho aberto)

Veio do primeiro dia do Ciclo 1 (28/09) e esta registrado em
[decisoes.md](decisoes.md) como **direcao**. Nada disso virou codigo.

O que foi observado:

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

Sugestoes feitas e **ainda nao aprovadas** (em ordem de impacto):

1. 🟡 gravar assunto e artigo nas questoes FEPESE de Direito, comecando pelas
   provas de Policia Penal e Agente Penitenciario SC. **Feito na 3A para as
   170 do alvo** (todas as materias, nao so Direito), pelo Claude Code;
   **falta a sua conferencia** das 162 validas em Analises > Conferencia. O
   complementar e da 3B;
2. 🟡 um mapa de incidencia por tema. **Feito na 3A** (`radar incidencia` e
   Analises > Incidencia), com os rotulos sem previsao: "apareceu nas 2
   provas", "apareceu em 1 de 2", "nao apareceu nas provas analisadas". Falta
   mostra-lo em cada faixa: e da 6B;
3. 🟡 trocar a lei seca por "artigo cobrado": 10-15 min lendo so os artigos
   que cairam, mais a lista das pegadinhas, cada uma com o numero da questao
   real; o tempo que sobra vai para questoes. **Provisorio feito na 6A
   (02/10):** a lei seca virou "dirigida", 20 min, so os artigos-chave do
   `essencial` do dia (selecao do plano, nao incidencia). Os artigos que a
   FEPESE cobrou entram na 6B;
4. questoes distribuidas pela incidencia, nao uma por artigo (FEPESE real
   primeiro; as da IA so no modo `variacao`);
5. 🟡 teoria com teto: uma fonte por tema, nunca video por artigo.
   **Provisorio feito na 6A:** teoria de 40 min com "uma fonte so: passou do
   tempo, siga para a fixacao" no detalhe. A ficha da tarefa e da 6B.

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

### B.6 🟡 Conferencia da classificacao do alvo (Etapa 3A)

As 170 questoes do alvo estao classificadas pelo Claude Code (146 completas,
9 parciais, 15 pendentes com motivo). **A 3A so fecha com as 162 validas
conferidas por voce** em Analises > Conferencia (confirmar, corrigir ou
pendente). Hoje: 0 de 162.

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

1. ✅ **os 80 de Direito, Direitos Humanos e Legislacao Estadual do
   Socioeducativo 2013 e 2016** - feitos em 02/10;
2. **os blocos "Conhecimentos Especificos" das provas de seguranca e fiscalizacao**
   (Guarda Municipal 2024, Procurador, Agente de Fiscalizacao, Agente Social,
   Educador Social): e onde moram os 139 indicios de Direito Penal, 57 de
   Constitucional, 56 de Administracao Publica, 37 de Direitos Humanos e 35 de
   Sociologia. Nenhuma dessas provas tem gabarito definitivo: classificam, mas
   nao entram nos padroes de cobranca;
3. **Portugues e Raciocinio Logico** (993 + 290 questoes): o catalogo do
   `macetes.py` serve de primeira proposta (🟡), com conferencia por amostra de
   20 por materia, como o roteiro pede.

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

## C. Telas ainda no CSS antigo (B2 a B7) 🔴

B1 migrou Simulado e Gerar questoes para o `design.css`. Faltam seis telas que
ainda nao tem `body class="ds"` (conferido nos templates): **`foco.html`
(Analises), `index.html` (Concursos), `previsao.html`, `acompanhando.html`,
`calendario.html` e `404.html`**. Uma por etapa, sem mudar funcionalidade nem
dado: so `ds-pagina`, `ds-cartao`, `ds-campo`, `ds-botao`, `ds-tabela` e os
tokens que ja existem, nos dois temas, e o CSS antigo da tela sai. A ultima
(B7) tambem ajusta a secao do README que descreve as telas. O enunciado
original de cada etapa nao foi guardado; este paragrafo e o que sobrou dele.
O A2 e o A3, que mexiam nos mesmos templates, foram feitos na Etapa 1B.

## D. Combinado para depois

- 🔴 **`config/leis.yml`**: conferir a lista `mudancas` (leis alteradas depois
  das provas). Esta vazia; a tela de Macetes diz "ainda nao gravada" em vez de
  inventar;
- 🔴 **Importar macete e explicacao**: `radar gerar --pedido --macetes` e
  `--explicacoes`, e o `--importar` de cada um. `data/macetes.json` e
  `data/explicacoes.json` ainda nao existem;
- 🔴 **Assunto no Direito** (o item 1 do bloco B). Hoje: 0 questoes de Direito
  com assunto; "Onde estudar primeiro" so tem Portugues e Raciocinio Logico;
- 🔴 **Cronograma por IA**: fase futura da especificacao; so entra se a revisao
  espacada simples nao bastar, com o teto de gasto do `gerador.py`;
- ⚪ **Ciclo 2** (09/11 a 19/12, "o resto do programa"): a faixa de 07/11, no fim do
  Ciclo 1, manda comparar o acerto por materia com o diagnostico de 03/10; e
  esse numero que decide o Ciclo 2. Depois, editar o `config/cronograma.yml`
  (as faixas gravadas no diario continuam contando; o check guarda materia e
  assunto);
- 🟡 **Notificacao do Windows**: funciona (teste de 10 s e configuracoes do
  Windows conferidas), mas falta liberar a permissao no navegador;
- ⚪ **D1 e E1 a E4** foram commitados e testados, mas nao conferi uma a uma
  contra o roteiro que os pediu; vale uma passada de uso real (o backup das
  23h30 rodar no PC, o caderno de erros e a tela Semanas com dados de verdade);
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

## E. Cancelado

- **C1b, sirene para a Guarda Municipal de Florianopolis e de Balneario
  Camboriu**: nao e para fazer. O `de_olho` ja avisa com 👀 quando sair algo,
  que e tudo o que eu quero (ver decisoes.md).
