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
o que sobra esta nos itens 🟡 e nas B.8 e B.9.

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
   dele tem tela desde 04/10, decisao 87: ver B.8);
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
Claude Code, pelo `radar classificar --pedido/--importar`, e voce confere -
no complementar, a segunda leitura as cegas que cai no mesmo no conta como
conferida pelo Claude Code (decisao 104).

As perguntas 3 (versao enxuta agora) e 4 (o Anki continua?) foram respondidas
e feitas na Etapa 6A: rotina nova a partir de 02/10 e `anki: desativado`.

**Quantas questoes dos arts. 1o a 12 do CP cairam em 2019?** Respondida na
3A, por consulta a classificacao: **1** (2019-q51, a correta e o art. 8o; as
alternativas passam pelos arts. 2o, 3o e 4o). Em 2013 foram 3 (q50, art. 8o;
q51, art. 7o; q53, art. 2o). As quatro estao pendentes: o programa de 2019
nao lista "aplicacao da lei penal".

### B.8 🟡 Classificacao do acervo complementar (Etapa 3B, passo 4)

As 172 provas aceitas no `data/acervo_complementar.json` estao no acervo
(eram 122 ate 04/10: o leitor consertado e as 21 provas baixadas fizeram
entrar 47, decisao 90).
**Feito (02/10):** as 80 do Socioeducativo 2013 e 2016 (lote 1), com 62
classificadas e 18 pendentes com motivo; a incidencia ja mostra o complementar
por no nessas materias. O resto foi feito depois, e desde 05/10 (decisao
106) o complementar aceito das materias do edital nao tem questao sem
classificacao:

1. ✅ **os 80 do Socioeducativo 2013 e 2016** - feitos em 02/10;
2. ✅ **os blocos genericos** - feitos em 02/10: das 125 com indicio,
   44 classificadas e 81 sem linha (conteudo do cargo daquele concurso);
3. ✅ **Portugues e Raciocinio Logico pelo catalogo** - feitos em 02/10: 92 + 16
   propostas automaticas 🟡. **Reprovadas na amostra de 04/10** (o catalogo
   errou o assunto em 9 de 20 e em 9 de 16) e refeitas pelo Claude Code, uma a
   uma: o lote 4 (decisao 87).

**O que sobra na B.8:**
- **a sua conferencia das 46 classificacoes abertas e das 29 pendentes** da
  lista unica (a recontagem no banco de 05/10 deu 47 e 30: recontar ao
  conferir)
  (decisoes 104 e 106): o que as duas leituras as cegas nao fecharam, na
  reanalise e na classificacao de Portugues e Raciocinio. Lista unica, com a
  segunda leitura ao lado: [conferir_classificacoes.md](conferir_classificacoes.md).
  Tela: Analises > Conferencia, filtro "complementar aceito" e "so as nao
  conferidas";
- **a sua conferencia dos 109 conceitos associados** do alvo (decisoes 86 e
  94): Analises > Conferencia, evidencia "alvo", caixa "so com associado por
  conferir" - 72 questoes, cada associado com Confirmar ou Tirar;
- **as questoes sem linha**: as 81 do lote 2 (conteudo de outro cargo, de
  proposito). As de Portugues e Raciocinio Logico que o catalogo nao cobria
  foram classificadas a mao em 05/10 (decisao 106);
- **os 1.738 "Conhecimentos Especificos" distintos sem indicio nenhum**: sao
  conteudo do cargo daquele concurso (enfermagem, pedagogia, contabilidade).
  Nao ha por que classifica-los.

### B.9 🟡 Defeitos do acervo complementar achados na 3B

Resolvidos em 04/10 (decisao 90): o "mesmo sha256 em dois enderecos" era o
download gravando dois S07.pdf no mesmo lugar - as 21 provas que faltavam
foram baixadas -, e a numeracao furada de 28 cadernos era o leitor tomando o
"N." da lista da alternativa anterior pelo numero da questao. Sobram:

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
- 🔴 **Conferir as 65 fichas** (Hoje > Fichas, botao "Conferi esta
  ficha", ou `radar fichas --conferir <tema>`), comecando pelas da semana.
  As 4 de Portugues de 28/09 a 01/10 (substantivo e adjetivo; artigo,
  numeral e pronome; Verbo 1; Interpretacao 1) foram escritas pelo Claude
  Code em 05/10 e sao gramatica, sem lei para ler contra. Na
  conferencia, vale olhar os nos de cada uma: 15 ficaram sem no (decisao 43;
  as 13 de 02/10 e as 2 de 05/10, Interpretacao 1 e Verbo 1).
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
  por materia com o diagnostico de 10/10 (decisao 105); e esse numero que
  decide o Ciclo 2.
  Depois dele: a proposta pela prioridade (`config/prioridade.yml`) e pela
  rotina da 6A, a minha aprovacao e so entao o `config/cronograma.yml` (as
  faixas gravadas no diario continuam contando; o check guarda materia e
  assunto). **Montar o ciclo inclui escrever, antes do primeiro dia, as
  fichas e os resumos dos temas novos e a explicacao das questoes reais
  deles** (decisao 123): `radar fichas --pedido`, depois `--pedido
  --resumos` e `--pedido --explicacoes`, cada um com o `--importar`, e o
  `radar fichas --verificar-resumos` no fim. A redistribuicao pela classe
  de cada tema (decisao 108) vale tambem para ele. Prazo: antes de 09/11;
- 🟡 **Notificacao do Windows**: funciona (teste de 10 s e configuracoes do
  Windows conferidas), mas falta liberar a permissao no navegador;
- ⚪ **O que ficou sem acento de proposito** (decisao 93): a descricao de
  cada comando no `radar --help` (e a docstring da funcao, e o codigo segue
  sem acento), os valores que eu digito (`--anel proximo`, `--modo revisao`,
  `--marcar minima`), os prompts de IA e os nomes de assunto do
  `macetes.py`, que sao chave de casamento;
- ⚪ **Token do Telegram**: foi revogado depois de colado numa conversa.
  Confirmar que o novo esta so em variavel de ambiente / Secrets do GitHub.

- 🔴 **Dois gabaritos de Raciocinio para conferir**: a 2024-q21 (a conta da
  50%, o gabarito diz 24% a 26%) e a 2023-q10-533 (enunciado cortado). As 24
  classificacoes abertas de Portugues e Raciocinio (24 de Portugues e 2 de
  Raciocinio) estao na lista unica da B.8;
- ⚪ **Portugues no radar: so o comeco da faixa** (decisao 107): o acervo
  nao tem questao para trocar o Qconcursos inteiro (varios temas tem 1 a 3),
  entao a faixa comeca pelas do radar e termina la. Para ter mais, so mais
  provas da FEPESE no acervo (o `radar baixar-provas` e a validacao do
  complementar); estender a outras materias e trocar o `MATERIAS`;
- ⚪ **A gerada e unica pelo enunciado** (`QuestaoGerada.impressao`): dois
  comandos genericos iguais com alternativas diferentes viram uma so, e a
  importacao conta a segunda como repetida. Por desenho; no estoque, cada
  enunciado foi escrito com o que cobra;
- 🔴 **Levar o radar para a nuvem, com login e dois perfis** (pedido de
  05/10): o plano, as opcoes, os custos e as perguntas que voce precisa
  responder antes estao em [roteiro_nuvem.md](roteiro_nuvem.md);

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

## G. Achados da auditoria independente de 04/10

Detalhe, reprodução e plano em [auditoria_independente.md](auditoria_independente.md)
(R7 e R14). Os 8 defeitos (BUG-1 a BUG-8) e os menores saíram nas Rodadas 1
a 4 e no lote de 05/10 (decisões 96 a 103; o resumo está no
[historico](historico.md)). Ficam, de propósito:

- 🔴 **A 2013-q53 (abolitio criminis) continua pendente:** a classificação é
  conferida por você, e só você muda o nó dela;
- ⚪ **Mais nós repetidos, achados na reanálise de 05/10** (os 3 pares da
  decisão 99 já foram juntados): em Direitos Humanos, "Declaração Universal de
  1948", "Declaração Universal dos Direitos Humanos (1948)" e "Conteúdo da
  Declaração Universal dos Direitos Humanos"; "Conferência de Viena (1993)" e
  "Declaração e Programa de Ação de Viena (1993)"; no Estatuto do Servidor de
  SC, "Posse e exercício", "Provimento: nomeação e posse" e "Jornada, serviço
  extraordinário e posse"; e o nó de abuso de autoridade tem o nome da Lei
  4.898/1965, revogada pela 13.869/2019, que é a que as questões cobram.
  Juntar ou renomear é com você (`radar conteudos --juntar`);
- ⚪ **O `compilado.mesma_materia` (comparação difusa, 0,85)** continua: casa
  o nome do quadro do edital com o do caderno (decisão 97);
- ⚪ **CL-2 da auditoria:** o `provas.py` e o `provas_ieses.py` sabem ler os
  hotsites das bancas, fora de `collectors/`; é anterior à evolução e não foi
  mexido.

## H. Revisão final do estudo (pedido de 05/10)

Feita inteira: a Fase 1 (a análise) e as subetapas R1 a R7 (decisões 108 a
126; `progresso.md`, linha 25). O que sobra, numa lista só, na ordem de
prioridade, separado entre o que depende de você e o que a IA pode fazer.

### Depende de você

1. 🔴 **Commit e push de toda a série**, no fim da R7, com a sua autorização.
2. 🔴 **Conferir as fichas e os resumos dos temas da semana** (Hoje > Fichas,
   "Ficha completa": "Conferi esta ficha" e "Conferi este resumo"; ou
   `radar fichas --conferir` / `--conferir-resumo`). São 65 de cada; a ficha
   conferida liga as faixas do tema ao Meu desempenho (decisão 81). Tamanho:
   grande, aos poucos.
3. 🔴 **Os gabaritos que a escrita dos resumos levantou** (pequeno):
   - 2019-q87: o gabarito oficial (E) dá como certo "atribuição de trabalho,
     remuneração e horário de lazer"; o art. 41, II, da LEP não fala em
     lazer (descanso e recreação estão no inciso V). O resumo registra isso
     sem mudar o gabarito;
   - 2013-q28 (o meu cargo, "norma infraconstitucional") e FEPESE-2013-q24
     (outro concurso, "norma constitucional"): gabaritos opostos para
     perguntas parecidas sobre a hierarquia dos tratados. Registrado como
     pegadinha, sem dizer qual está errado;
   - FEPESE-2024-q21 (probabilidade): a conta direta dá 50%, e o gabarito
     oficial (D) diz outra faixa (já na lista dos 2 gabaritos de Raciocínio,
     seção D).
4. 🔴 **O Ciclo 2** (seção D): a proposta depois do simulado de 07/11, com a
   classe de cada tema (decisão 124) e as fichas, os resumos e as explicações
   dos temas novos antes de 09/11 (decisão 123). Tamanho: grande.
5. ⚪ **As faixas sem nó na árvore** (até 07/11): na LEP, Objeto e
   classificação, Trabalho do preso, Disciplina e RDD, Sanções e recompensas,
   Estabelecimentos penais, Medida de segurança; em Português, Concordância
   nominal, Crase 1, Pontuação 2, Pronomes 1, Interpretação 4, Termos
   integrantes 2 e Redação oficial 2. A faixa diz "sem nó na árvore" e não
   dá comando de gerar; nas da LEP, o "caiu" sai pelo artigo (decisão 108).
   Resolver é escolher o nó na conferência da ficha (nenhum nó é criado sem
   você). Médio.
6. ⚪ **O pedido do art. 13 em `data/pedido_ia.json`** (8 questões, "Infração
   penal: elementos, espécies"), esperando os passos 2 e 3, se você quiser.
   O escopo é o assunto inteiro: a árvore não tem nó do art. 13.
7. ⚪ **Pontos escritos de memória, para olhar quando conferir** (pequeno):
   Redação oficial 1 e 2 citam o Manual de Redação da Presidência (3ª ed.)
   pela seção, sem o número do subitem, com três pontos de memória (a data
   sem a UF, a numeração das páginas, o signatário em maiúsculas); e três
   explicações têm fonte mais fraca: as gerações de direitos (a classificação
   é doutrina; a fonte ancora no art. 225 ou no art. 5º, XIV, da CF), a
   eficácia horizontal (art. 5º, § 1º, e o RE 201.819) e a 2013-q51, cujo
   gabarito embaralha a redação do art. 7º, I, c, do CP (a explicação avisa).

### A IA pode fazer (quando você pedir)

1. 🔴 **O texto local das leis**, para o verificador conferir se o artigo
   citado numa ficha ou num resumo existe (o item 4a da Fase 1). Não foi
   feito nesta série: precisa de uma decisão sua antes - onde mora o
   download (é uma fonte nova: a regra do CLAUDE.md diz que só `collectors/`
   sabe de onde vem o dado), se o texto fica fora do git (`data/copias/`),
   e o `robots.txt` do normas.leg.br conferido (a Câmara recusou a conexão
   em 05/10). Médio.
2. ⚪ **A falta do estoque de geradas** (R5, decisão 125): 231 questões em 24
   nós sem gerada e alguns com pouca, no quadro do `estoque_de_geradas.md`.
   Sob demanda, pelos 3 passos de cada faixa; ou um lote por semana, se você
   preferir. Médio.
3. ⚪ **12 questões reais do alvo sem explicação**, deixadas de fora por falta
   de fonte segura: dependem do texto-base da prova, que o radar não guarda
   inteiro (2013-q2; 2019-q1, q2, q4, q9, q13, q14), do sublinhado perdido
   (2013-q4; 2019-q6, q7) ou são só doutrina (2019-q28, q38). Só com o texto
   da prova à mão. Pequeno.
4. ⚪ **Sugestão (melhoria):** a explicação das questões do complementar que
   são exemplo de tema (hoje só as do alvo têm), pelo mesmo fluxo. Médio.
