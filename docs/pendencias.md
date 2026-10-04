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

O backup das 23h30 (decisao 64) tambem voltou: a noite de 03/10 terminou em
`RESULTADO: ok` (`data/logs/sincronizar-2026-10-03.log`) e subiu o commit
`sincronizar: 2026-10-04`, com os 3 simulados de 28 e 29/09 (o quarto estava
vazio, e a limpeza o apagou). Nada quebrado agora.

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

### B.8 🟡 Classificacao do acervo complementar (Etapa 3B, passo 4)

As 169 provas aceitas no `data/acervo_complementar.json` estao no acervo
(eram 122 ate 04/10: o leitor consertado e as 21 provas baixadas fizeram
entrar 47, decisao 90).
**Feito (02/10):** as 80 do Socioeducativo 2013 e 2016 (lote 1), com 62
classificadas e 18 pendentes com motivo; a incidencia ja mostra o complementar
por no nessas materias. **Falta o resto**, e a linha diz quantas ("993 sem
classificacao ainda" em Portugues):

1. ✅ **os 80 do Socioeducativo 2013 e 2016** - feitos em 02/10;
2. ✅ **os blocos genericos** - feitos em 02/10: das 125 com indicio,
   44 classificadas e 81 sem linha (conteudo do cargo daquele concurso);
3. ✅ **Portugues e Raciocinio Logico pelo catalogo** - feitos em 02/10: 92 + 16
   propostas automaticas 🟡. **Reprovadas na amostra de 04/10** (o catalogo
   errou o assunto em 9 de 20 e em 9 de 16) e refeitas pelo Claude Code, uma a
   uma: o lote 4 (decisao 87).

**O que sobra na B.8:**
- **a sua conferencia**, uma a uma, das 232 classificadas do complementar
  aceito: as 124 do Claude Code de 02/10 (lotes 1 e 2) e as 108 refeitas em
  04/10 (lote 4). A tela existe desde 04/10 (decisao 87): Analises >
  Conferencia, filtro "complementar aceito". O Claude Code releu as 44 do lote
  2 no mesmo dia: todas no no certo; um dispositivo que nao existe (CPP, art.
  282, § 7º) virou o art. 282, § 5º, e o art. 316, paragrafo unico. Proposta
  nova do catalogo, se ele rodar de novo, se confere pela amostra da tela;
- **a sua conferencia dos 109 conceitos associados** do alvo (decisoes 86 e
  94): Analises > Conferencia, evidencia "alvo", caixa "so com associado por
  conferir" - 72 questoes, cada associado com Confirmar ou Tirar;
- **as questoes sem linha**: 81 do lote 2 (conteudo de outro cargo, de
  proposito) e, em Portugues e Raciocinio Logico, as que o catalogo nao cobre
  (47 sem palavra, 23 ambiguas, 22 sem par no edital em Portugues; 21 e 8 em
  Raciocinio). Ampliar o catalogo ou o mapa do `config/complementar.yml`
  resolve parte;
- **os 1.738 "Conhecimentos Especificos" distintos sem indicio nenhum**: sao
  conteudo do cargo daquele concurso (enfermagem, pedagogia, contabilidade).
  Nao ha por que classifica-los.

### B.9 🟡 Defeitos do acervo complementar achados na 3B

Resolvidos em 04/10 (decisao 90): o "mesmo sha256 em dois enderecos" era o
download gravando dois S07.pdf no mesmo lugar - as 21 provas que faltavam
foram baixadas -, e a numeracao furada de 28 cadernos era o leitor tomando o
"N." da lista da alternativa anterior pelo numero da questao. Sobram:

- ~~3 cadernos com a numeracao furada~~: resolvidos em 04/10 (decisao 95) -
  o texto-base "Caso 3" antes da questao e a marca "square" minuscula; as 3
  provas entraram no complementar aceito (169 -> 172), ainda sem
  classificacao, como as outras que entraram pela validacao;
- **os tres de Florianopolis 2025 (COMCAP) em http e https** sao de fato a
  mesma prova em dois enderecos: a segunda fica recusada, como deve;
- **a 2013-q20 do alvo sem a imagem** do icone do Excel: o PDF traz a figura,
  e o texto nao. E Nocoes de Informatica, fora do edital de 2019.

## D. Combinado para depois

- 🟡 **Marcar a lista de leis alteradas como conferida** (`config/leis.yml`;
  decisoes 65 e 84). Os 15 itens de `mudancas` foram reconferidos pelo Claude
  Code em 04/10, artigo por artigo, no texto oficial de hoje (Camara e ALESC):
  **nenhum esta errado**, e as ressalvas - o que nao se le daqui (a data de
  2027 da EC 132, as ADIs que a compilacao cita, a EC estadual 80/2020) - estao
  na tabela de [leis_alteradas.md](leis_alteradas.md). Os 9 de `fronteira`
  tambem foram conferidos (decisao 84). Falta so o seu `conferida: true` em
  cada um - e o que tira o 🟣 -, comecando pelas 5 em que o gabarito oficial
  ficou errado: 2013 q64 e q66, 2019 q46, q71 e q75;
- 🔴 **Conferir as 61 fichas da 6B** (Hoje > Fichas, botao "Conferi esta
  ficha", ou `radar fichas --conferir <tema>`), comecando pelas da semana. Na
  conferencia, vale olhar os nos de cada uma: 13 ficaram sem no (decisao 43).
  O Claude Code leu as 61 contra a fonte em 04/10 - LEP, CF, CP e CPP no texto
  compilado de 03/10, Mandela no texto da ONU: 15 corrigidas (um erro de
  verdade, a regra 40 de Mandela) e 7 com ponto que ele nao conseguiu
  conferir, entre eles a guarda municipal no STF e o Manual de Redacao.
  Tudo em [conferencia_das_fichas.md](conferencia_das_fichas.md); a
  conferencia continua sua;
- 🔴 **Reclassificacoes que as fichas mostraram**: 2 questoes de regencia
  estao em "Emprego de tempos e modos verbais" (no complementar, a regencia
  foi para Termos integrantes > Objeto direto e indireto, o lugar da ficha -
  decisao 87; as 2 do alvo sao conferidas suas, e mudar e com voce); as de
  pronome do complementar
  estavam em "Classes gramaticais variaveis", junto com substantivo e adjetivo
  (refeitas no lote 4 de 04/10: foram para Pronomes, decisao 87);
  as de concordancia, crase, pontuacao e complemento nominal estao so no nivel
  do assunto, e por isso as fichas de tema nao as contam; "Regras de aplicacao
  geral" (Regras de Mandela) nomeia a Parte I inteira (regras 1 a 85);
- ⚪ **Quatro explicacoes nao escritas** (04/10, decisao 92): das 10 questoes
  reais que voce errou, 4 dependem do texto da prova ou do termo sublinhado,
  que o radar nao guarda (2013 q2, 2016 q3, 2019 q6 e a de 2024 do
  Catupiry). Ficaram sem explicacao em vez de explicacao chutada; o
  proximo `radar gerar --pedido --explicacoes` pede de novo so elas e as
  que voce errar daqui para frente;
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
- ⚪ **Conferir o Actions de 04/10**: o primeiro `coleta:` do radar-bot com o
  codigo da 2A, da 2B e da 2C. O de 03/10 foi verde (o commit `coleta: 2026-10-03`
  e a prova: o job roda o `pytest -q` antes de coletar). No fim do lote de
  04/10 o GitHub ainda nao tinha o `coleta: 2026-10-04` (o `gh` nao esta
  instalado aqui; vi pelo `git fetch`), e o proximo ja roda com o lote;
- ⚪ **O que ficou sem acento de proposito** (decisao 93): a descricao de
  cada comando no `radar --help` (e a docstring da funcao, e o codigo segue
  sem acento), os valores que eu digito (`--anel proximo`, `--modo revisao`,
  `--marcar minima`), os prompts de IA e os nomes de assunto do
  `macetes.py`, que sao chave de casamento;
- ⚪ **Token do Telegram**: foi revogado depois de colado numa conversa.
  Confirmar que o novo esta so em variavel de ambiente / Secrets do GitHub.

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
- ⚪ **Duas geradas antigas para voce olhar** (decisao 89): a de genero do
  substantivo de 28/09 da "conjuge" como comum de dois generos, e a gramatica
  tradicional o da como sobrecomum ("o conjuge"); e a do diretor de
  estabelecimento de 27/09 cita o "art. 76" da LEP, e o requisito e do art.
  75. As duas ficaram no sorteio: o botao "essa questao esta errada" do
  /geradas tira, se voce concordar;

## E. Cancelado

- **C1b, sirene para a Guarda Municipal de Florianopolis e de Balneario
  Camboriu**: nao e para fazer. O `de_olho` ja avisa com 👀 quando sair algo,
  que e tudo o que eu quero (ver decisoes.md).

## F. Achados da varredura de 03/10 (depois da Etapa 8)

A varredura dos docs contra o codigo e o banco achou estes pontos, que nenhuma
etapa tinha registrado. Os cinco que ela mandou corrigir na hora ja sairam
(decisoes 63 a 66 e a limpeza dos docs); estes ficam:

- ⚪ **3 variacoes geradas de 27/09 sem a questao real de base** (decisao
  77): o enunciado da base delas se repete no acervo com alternativas
  diferentes, e nao ha registro do pedido. O selo diz que o acervo nao
  consegue identificar. As 30 do estoque de 03/10 foram religadas em 04/10
  pelo historico da conversa (F10);
