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
  --resumos`, `--pedido --explicacoes` e, nas fichas de lei, `--pedido
  --traducoes` (decisao 161), cada um com o `--importar`, e o
  `radar fichas --verificar-resumos` no fim. A redistribuicao pela classe
  de cada tema (decisao 108) vale tambem para ele. Prazo: antes de 09/11.
  **O que os sabados leves (decisao 170) mandaram para o Ciclo 2**, e que
  ele precisa encaixar:
  - os temas de Portugues **Termos integrantes 2** (complemento nominal e
    agente da passiva), **Redacao oficial 2** (o padrao oficio) e **Revisao
    ativa 3** (ortografia, acentuacao e redacao oficial) - as fichas dos tres
    continuam no `data/fichas.json`, e a "Revisao ativa 2" de 04/11 so cobriu
    a parte 1 dos termos integrantes;
  - em **09/11**: a R+7 de Redacao oficial 1 (estudada em 02/11), a R+7 de
    Argumentacao e quantificadores (30/10), a R+30 de Afirmacao historica e
    dimensoes (08/10) e a R+30 de Interpretacao 2 (08/10) - as tres ultimas
    sairam de 07/11, que ficou so com o fechamento;
  - em **13/11**: a R+7 de Problemas aritmeticos e geometricos (06/11);
  - e decidir se o sabado de 2 horas e o Raciocinio na sexta continuam no
    Ciclo 2 (a decisao 170 vale ate 07/11);
  **A minha conferencia das provas novas** (decisao 173) entra no Ciclo 2
  como **faixa de uns 20 minutos por semana, ate acabar**: a amostra dos
  quatro grupos (FEPESE, NC-UFPR e Selecon, Cebraspe, IESES; 10 por grupo,
  mais 10 no grupo com 1 erro) e as pendentes da regra c com as 8 fora do
  treino (37), na Analises > Conferencia, evidencia "provas novas de 17/10";
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
126; `progresso.md`, linha 25), e depois os itens 8, 2, 3, 4 e 5 do pedido
de 05/10 (decisões 128 a 133; linha 26). O que sobra, numa lista só, na ordem
de prioridade, separado entre o que depende de você e o que a IA pode fazer.

### Depende de você

2. 🟡 **Conferir as fichas e os resumos dos temas da semana** (Hoje > Fichas,
   "Ficha completa": "Conferi esta ficha" e "Conferi este resumo"; ou
   `radar fichas --conferir` / `--conferir-resumo`). Em 06/10 você conferiu
   as 5 fichas dos temas já estudados (as que ligavam 9 faixas feitas: a fila
   de revisão passou a ter Penal e Constitucional); faltam 60 fichas e os 65
   resumos. A ficha conferida liga as faixas do tema ao Meu desempenho
   (decisão 81). Tamanho: grande, aos poucos - a do tema do dia, com a lei
   aberta.
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
     seção D). Explicada em 09/10, a seu pedido, com a letra oficial e a conta
     que dá 50% (decisão 133);
   - FEPESE-2023-q14 (colocação pronominal): o gabarito (A) põe "a cuja
     enteada atribuem-se", e o relativo "cuja" pede a próclise ("se
     atribuem"); a A é a menos errada, não a certa. Explicada em 09/10,
     dizendo isso;
   - FEPESE-2023-q30 ("desdenhar"): o gabarito (A) trata "desdenha do
     executivo" como a única regência certa, e o verbo também aceita objeto
     direto. Explicada em 09/10, dizendo isso: a afirmativa 2 traz o trecho.
4. 🔴 **O Ciclo 2** (seção D): a proposta depois do simulado de 07/11, com a
   classe de cada tema (decisão 124) e as fichas, os resumos e as explicações
   dos temas novos antes de 09/11 (decisão 123). Tamanho: grande.
5. ✅ ~~As faixas sem nó na árvore~~: resolvido em 06/10 (decisão 129), com
   a lista aprovada por você. Só a Interpretação 1 (o método) ficou sem nó,
   de propósito. Na conferência das fichas, olhe os 9 nós novos e o porquê
   de cada um ("por que estes nós").
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
2. ⚪ **A falta do estoque de geradas** (R5, decisão 125): as faixas de 06 a
   12/10 foram completadas em 06/10 (90 questões, decisão 131); de 13/10 em
   diante continua sob demanda, pelos 3 passos de cada faixa, ou uma semana
   por vez, como esta. Médio.
3. ⚪ **2 questões do alvo sem explicação** (2019-q28 e q38, Direitos
   Humanos): a fonte delas é só doutrina, e a regra pede dispositivo
   (procurado de novo em 09/10: o § 5 de Viena e o art. 26 da Convenção
   Americana cobrem outras alternativas, não o ponto da resposta). As
   outras 10 saíram com o texto-base (decisão 132). Pequeno, se um dia
   houver dispositivo.
4. ⚪ **2 questões do complementar citadas nos resumos sem explicação**
   (decisão 133): a FEPESE-2016-q1 (o caderno não diz "texto 1", e o leitor
   não liga o texto à questão) e a FEPESE-2023-q1 do Monitor Escolar (de
   lacunas: uma das seis sumiu na leitura do PDF). As outras 9 saíram em
   09/10, com o texto-base também no complementar aceito.
5. ⚪ **A alternativa E da 2019-q6 leva um pedaço do Texto 2 colado no fim**
   ("BBC News Brasil – Muitos no Brasil acham..." até "[Adaptado]"): é a
   leitura normal do caderno, a mesma ordem trocada que a leitura por colunas
   do texto-base contornou (decisão 132). Consertar é cortar a alternativa no
   começo de um texto de apoio e reler o caderno de 2019 (`--refazer`, que
   leva a classificação junto). Pequeno.

## I. A proposta de melhorias de 06/10 (o que ainda não foi feito)

A auditoria de uso está em [proposta_de_melhorias.md](proposta_de_melhorias.md),
com os códigos P (precisão), U (tela) e I (ideia). **Feito em 06/10** (decisões
134 a 137): o lote 1 - I1, P14 (o Plano B e a Reduzida dos sábados que medem),
U02, P06 e os textos do I4 e do I6 -, a correção do 29/09 (P02) e as 5 fichas
do I5. A regra de trabalho até 07/11 (I3, aprovada): só entra o que corrige
número ou prepara 10/10, 17/10 e 07/11.

### Próximos lotes, já aprovados (um por conversa)

1. ✅ **Lote 2, o "fiz" (P03 · U03)** - feito em 06/10 (decisão 138): as
   reais e o treino de IA em linhas próprias, o "fiz no Qconcursos" sempre
   vazio, a faixa feita no radar com o ✓ vazio e o "Treino de IA neste tema".
   O 06/10 foi corrigido como o 29/09. Para valer, o servidor precisa ser
   reiniciado (`radar parar` e `radar subir`): o que estava no ar era de antes
   da decisão 130.
2. 🔴 **Lote 3, até 16/10**: ✅ P04 em 09/10 (decisão 143: as 31 faixas de
   08/10 em diante viraram duas linhas, Direito e Português; o 07/10, já
   anotado, ficou como era) e ✅ U21 · P36 em 09/10 (decisão 144: cada erro
   do relatório da rodada vai ao caderno com a matéria e o nó da questão; a
   faixa leva o nó que você deu - `conteudo`, `nos` ou a ficha conferida -; a
   faixa mista abre sem matéria). **Lote 3 feito.** Para valer na tela, o
   servidor precisa ser reiniciado (`radar parar` e `radar subir`).
3. 🔴 **Lote 4, até 06/11**: P07 (as rodadas que medem não repetem questão:
   o fechamento de 07/11 repetiria as 8 de RL de 10/10; muda a decisão 67),
   P01 + P09 (o anotado sem conteúdo conta no nó da matéria, escolha sua;
   muda a decisão 81), P05 (a ficha esconde o gabarito da questão ainda não
   respondida; muda as decisões 109 e 118), P10, P11 · U18 e P30.
   **As escolhas, feitas por você em 09/10:** P01 + P09 = o anotado sem
   conteúdo conta no nó da MATÉRIA (não no assunto), e as telas dizem "sem
   acerto medido" no lugar de "não treinei"; P05 = a letra fica escondida até
   eu responder a questão no radar (sem botão "ver gabarito"); P30 = decide o
   acumulado do ciclo, com o fechamento ao lado, e a tela diz que os
   simulados do Qconcursos ficam fora. P07, P10 e P11 · U18 como a proposta.
   **Feito:** ✅ P07 em 09/10 (decisão 145: o estoque da rodada que mede não
   tem a questão de outra rodada que mede do ciclo; o fechamento de 07/11
   repetiria 19 das 40 de 10/10); ✅ P30 em 09/10 (decisão 146: o plano e a
   tela dizem que decide o acumulado do ciclo, com o fechamento ao lado, e
   que os simulados do Qconcursos ficam fora); ✅ P01 + P09 em 09/10 (decisão
   147: o anotado sem conteúdo conta no nó da matéria, em toda tela; "sem
   acerto medido" no lugar de "não treinei"; o erro do caderno só com a
   matéria entra na fila); ✅ P05 em 09/10 (decisão 148: a letra, a explicação
   e a pegadinha da questão só aparecem depois de você responder no radar, na
   ficha e no resumo; o dado continua com a letra); ✅ P10 em 09/10 (decisão
   149: o "não apareceu" diz a base pequena, a prioridade baixa foi para o
   "Por que agora", e a faixa mostra as notas do "caiu"); ✅ P11 + U18 em
   09/10 (decisão 150: a seta do acerto só com 20 respostas de cada lado, e
   nenhuma na semana em andamento; o n de cada ponto). **Lote 4 feito.**
   Para valer na tela, o servidor precisa ser reiniciado (`radar parar` e
   `radar subir`).

### Depende de você

- ⚪ **28/09 (P08):** você não soube dizer se as 10 de Português foram do
  Qconcursos ou as 10 geradas da rodada 2; ficou como está (decisão 3 da
  Etapa 0). Se lembrar, a correção é a mesma do 29/09.
- ⚪ **A chave `ae5ac356...` (2013 q2 do complementar)** perdeu o artigo e o
  item do edital na conferência de 05/10 (decisão 137); o valor antigo está
  no commit `1bc222e`. Restaurar ou deixar.
- 🟡 **O link do Qconcursos (decisão 140).** (1) Abrir um link com vários
  assuntos (o da faixa do Art. 5º, XVII a XLIX) e ver se os 3 aparecem no
  filtro do site: nenhum teste confere isso, só o de um assunto. (2) A lista da
  disciplina **Redação Oficial**, para as 2 faixas que ficaram sem link. (3)
  Para o Ciclo 2: achar onde o site põe a **Maria da Penha** (Lei 11.340, 2
  questões em 2019) - no Direito Penal não está; a lista dele acaba mesmo no
  "40.13 Lei de Tóxicos". Já achado em `C:\qconcursos`, para o Ciclo 2: a LC
  529/2011 (7 questões em 2019) é o assunto 23303 da disciplina Regimento
  Interno (92); o Estatuto do Servidor de SC (Lei 6.745) é o 9371 da
  Legislação Estadual (61, a lista filtrada por SC de propósito); as LCs 472 e
  675 não apareceram. A legislação de Florianópolis (disciplina 600) é da
  Guarda Municipal (`de_olho`), não do alvo.

### Depois de 07/11 (I3)

O redesenho do Hoje, do Meu foco e das Semanas (seção 8 da proposta),
começando pelo I8 (o teste que segura a limpeza); depois as telas de análise
e de consulta; por fim a coerência de nomes, botões e componentes (U52 a U54,
U59, U60, U64), a coluna BAIXA da tabela 6 e a nuvem (decisão 126). A
legenda da Reduzida no "Como foi o dia" (U04, parte) também ficou para lá.

## J. A aba Acompanhando por carreira (decisao 141, 06/10)

Feito nesta sessao: o cartao por carreira, o 🔔 de fato, o "visto", o botao
"Verificar atualizacoes", a pesquisa do Claude Code (`radar acompanhar
--pedido/--importar`), a conferencia e o Telegram so no critico. O que falta:

### Depende de voce

- 🔴 **Ver a aba no seu Windows, com o banco real**: `radar sincronizar`
  (traz o YAML e a PM no alvo.yml), `radar reclassificar` (para a marca de
  PM valer nos itens que ja estao no banco), `radar web` e um clique no
  botao. Aqui ela foi conferida com o banco remontado dos JSON: os 7 cartoes
  dizem "aguardando", porque nenhum concurso dessas carreiras saiu no radar
  nos ultimos 12 meses;
- 🟡 **A primeira pesquisa**: `radar acompanhar --pedido`, responder no
  Claude Code do VS Code e `--importar`; depois conferir cada 🟣 na tela;
- 🟡 **Os termos**: o `termos_extras` de cada carreira saiu do que a coleta
  ja mostrou ("PC SC", "PMBC", "PMF") e do nome das siglas. Se um item da
  carreira ficar fora do cartao, ou um de fora entrar, o ajuste e no
  `config/acompanhamentos.yml`, sem codigo.

- ⚪ **Rodar a pesquisa de novo** (desde 09/10 ela pede o proximo concurso
  e o ultimo): `radar acompanhar --pedido` e os 3 passos. Ela completa o
  "Ultimo concurso" das Guardas e da PM, que ainda dizem "nao sei ainda".

### A IA pode fazer (quando voce pedir)

- 🟡 **Fontes oficiais novas** (pedido de 11/10: os 7 sites investigados de
  uma vez, a ordem aprovada por voce). Uma por vez, cada uma um arquivo em
  `collectors/`, com o robots.txt conferido e teste com fixture:
  - ✅ **Diario Oficial do Estado** (`doe_sc`, decisao 154): o contrato da
    banca, a autorizacao, a comissao e o edital das carreiras do
    `config/alvo.yml`. A carga de um ano trouxe 17 atos;
  - ✅ **Instituto AOCP** (`aocp`, decisao 155): os abertos e em andamento,
    com a data do edital pelo detalhe. Ligada pela carga inicial, sem aviso
    do que ja havia (34 concursos, nenhum de carreira catarinense hoje);
  - ✅ **Prefeitura de Balneario Camboriu** (`prefeitura_bc`, decisao 156):
    a noticia de concurso publico; o cartao da Guarda de BC ja mostra o
    anuncio de 04/08/2026 pela propria prefeitura (🟢). Daqui, o host
    `sim.bc.sc.gov.br` falhou no DNS em 2 das 4 coletas de 11/10 (a fonte
    falha sozinha e as outras gravam): ver se o Actions tambem falha;
  - ✅ **SEJURI** (`sejuri`, decisao 157): os editais de concurso publico
    (2006 a 2022) e os processos seletivos; o `alvo.yml` separa;
  - ✅ **IDIB** (`idib`, decisao 158): os abertos e em andamento; o CFO e o
    CFP do CBMSC ja estao no cartao dos Bombeiros (pelo `cbmsc` do
    `prova_de_sc`);
  - ✅ **Idecan** e **Prefeitura de Florianopolis**: registrados, sem codigo
    (decisao 159). Reavaliar o Idecan se ele ganhar concurso municipal da
    Grande Florianopolis; a de Florianopolis, se voce salvar a pagina da
    lista de noticias da Secretaria de Seguranca e Ordem Publica;
  - ⚪ **O leitor de robots do radar nao entende curinga** (`*` e `$`, da
    RFC 9309): o `urllib.robotparser` le `/*bet*` ao pe da letra e nao
    proibe nada. Nenhuma fonte de hoje usa curinga no que o radar pede (so a
    Prefeitura de Florianopolis, que ficou fora); se uma fonte nova usar, o
    `Coletor._robots_permite` precisa entender antes de ela entrar.
  - ✅ **Os marcos olham a edicao inteira** (feito em 11/10, decisao 160):
    cada marco do item mais novo que o sabe, e a situacao do mais novo que a
    sabe. Os Bombeiros dizem "edital publicado" com Banca IDIB; a PC SC,
    "banca contratada" com a banca do contrato;
  - ✅ **O edital de abertura do DOE entra como "edital publicado"** (feito
    em 12/10, decisao 162): a errata, a retificacao e a comissao continuam
    sem fase, e refazer a carga nao avisa o passado;
  - ✅ **O 🔔 so acende para item da edicao de agora** (feito em 12/10,
    decisao 163): os editais de 2006 a 2022 da SEJURI sairam do sino da
    Policia Penal; o ato de 2025 que e da edicao de agora continua acendendo;
  - ✅ **O CFO do CBMSC cai no cartao do Oficial de Bombeiros** (feito em
    12/10, decisao 164): o termo `cbmsc + formacao de oficiais`, que pede as
    duas partes; o CFO da PM fica so no cartao da PM;
  - ⚪ **Conferir a banca por extenso**: o DOE escreve "INSTITUTO DE
    DESENVOLVIMENTO EDUCACIONAL, CULTURAL, E ASSISTENCIAL NACIONAL" (o
    Idecan) e "INSTITUTO DE DESENVOLVIMENTO INSTITUCIONAL BRASILEIRO" (o
    IDIB). O coletor guarda como o ato escreve; virar sigla e uma tabela no
    config, se um dia valer.
- ✅ **A situacao do site de noticias e fraca** (feito em 08/10): o marco
  que vem so do Concursos no Brasil diz "segundo site de notícias" por
  extenso, no cartao e no `radar acompanhar` (decisao 141). Esperar a pagina
  detalhada continua possivel, se um dia valer;
- ✅ **"Oficial" que nao era** (feito em 08/10): a pesquisa de 07/10 trouxe
  2 novidades "oficial" com link no CDN de um curso. O tipo agora sai do
  dominio do link (governo ou `dominios_oficiais` do YAML), o importar conta
  as rebaixadas, e as 2 foram regravadas como noticia (decisao 141). Banca
  nova que entrar no radar: somar o dominio dela no `dominios_oficiais`;
- ✅ **A pesquisa por carreira** (feito em 08/10): `radar acompanhar
  --pedido --carreira "<nome>"` (decisao 141). O botao continua um so, no
  topo: a coleta e uma para todas as fontes;
- ✅ **Ligar a banca definida ao estudo** (feito em 08/10): com banca, o
  cartao da Policia Penal aponta para Analises > Edital e o padrao dela; sem
  prova da banca no acervo, diz isso (decisao 141). Incluir a banca no
  acervo e outra conversa: um coletor de provas por banca.

## K. O nivel das geradas (decisao 151, 09/10)

Feito: o campo (banco na versao 8), o `--nivel` no pedido e em todo comando,
o treino por nivel com o "so havia N", o acerto por nivel no resultado da
rodada e a classificacao das 911 antigas (478 faceis, 364 medias, 69
dificeis). O que falta:

### Depende de voce

- 🔴 **As 8 suspeitas da classificacao** (so listadas: nenhuma saiu do
  sorteio; o botao "Essa questao esta errada" tira, se for o caso). Cada uma
  com o motivo gravado em `questoes_geradas.suspeita`:
  - `d795a622` (Penal, peculato): a afirmativa 3 condiciona o bem particular
    a posse, mas o peculato-furto (CP, art. 312, § 1º) alcanca bem particular
    sem posse - o gabarito "e" e discutivel;
  - `0c75cfe7` (Const., voto facultativo): a alternativa A omite os maiores
    de 70 anos (CF, art. 14, § 1º, II, b) - e a melhor, mas incompleta;
  - `0d586eff`, `4e2ced15` e `ca99b241` (LEP, direitos do preso): o gabarito
    da como direito do art. 41 itens que nao sao a letra dele ("programa de
    reabilitacao", correspondencia "sem censura previa", "tratamento
    especializado");
  - `5a3ee22e` (LEP, orgaos da execucao): o art. 64 nao fala em "assessorar o
    Ministerio da Justica", e a alternativa A fica defensavel;
  - `cc44aaaa` (Port., plural de compostos): a alternativa A tambem esta
    certa (guarda-roupas) - duas certas;
  - `9192cbe3` (Port., concordancia do adjetivo posposto): B, D e E tambem
    sao aceitas pela norma culta (concordancia com o mais proximo).
- 🟡 **A regua do nivel variou entre as materias**: Penal saiu com 2
  dificeis em 132 e Direitos Humanos com 98 faceis em 167, contra 14
  dificeis em 35 no Raciocinio Logico. E o que a IA declarou, por lote; se,
  treinando, o "dificil" de uma materia parecer o "media" de outra, a
  conferencia e por amostra (o porque de cada uma esta gravado). Dois casos
  que contrariam a propria regra ja apareceram nos exemplos: `37bc3ced`
  (Penal, "junta os arts. 25 e 23", deu media) e `9586cfb7` (Penal, "as
  erradas sao claramente erradas", deu media). Reclassificar uma questao e
  apagar o nivel dela no banco e rodar o `--classificar-nivel` de novo (nao
  ha botao).
- ⚪ **Reinicie o servidor** depois do `git pull`: `radar parar` e `radar
  subir` (o banco migra sozinho para a versao 8 no primeiro comando).

## L. O treino de IA honesto (decisao 152, 10/10)

Feito: o nivel do treino de IA pela 1a vez em cada gerada, a revisao ao
lado, o firme, a variacao e o do zero separados e o minimo do `treino_ia`.
O que falta:

- ⚪ **Os minimos (10/15/10/30) sao a primeira regua.** Se, treinando, o
  "Amostra insuficiente" ficar tempo demais na tela - ou sumir cedo demais -,
  o ajuste e so no `config/amostra.yml`, secao `treino_ia`, sem codigo.
- ⚪ **Direitos Humanos ainda nao tem resposta a gerada**: o numero dele
  aparece quando houver treino.

## M. O resumo enxuto e a traducao dos artigos (decisao 161, 12/10)

Feito: o resumo enxuto nas 65 fichas (os artigos abertos, o resto dobrado),
o `config/linguagem.yml`, o `radar fichas --pedido --traducoes`, a tela da
traducao com o glossario e as 30 fichas de lei traduzidas (200 artigos, 130
linhas de "nao confunda", 215 termos). Os tres blocos de Direitos Humanos que
tinham ficado de fora (Viena, § 5; CF, art. 1º; Protocolo de San Salvador,
art. 11) entraram em 12/10, com a regra nova: o artigo com bloco proprio no
resumo e do tema (decisao 161). O que falta:

### Depende de voce

- 🔴 **Conferir as 30 traducoes** (Hoje > Fichas > "Ficha completa", no
  "🗣 Traduz pra mim" de cada artigo, e o botao **"✓ Conferi a traducao"**).
  A conferida nao e mais sobrescrita pela importacao. Aos poucos, a do tema
  do dia. Achou algo errado numa nao conferida: `radar fichas --pedido
  --traducoes --tema "<o tema>" --refazer`, os passos 2 e 3 de sempre, e
  `radar fichas --importar data/resposta_ia.json`;
- ⚪ **Olhar o glossario** (`data/glossario.json`, 215 termos, 🟣): nao ha
  botao de conferencia por termo. O termo errado se corrige a mao no arquivo
  (o primeiro escrito vale: a importacao nao sobrescreve). Alguns significados
  vem de doutrina, e a fonte diz isso ("doutrina (...)");
- ⚪ **Reinicie o servidor** depois do `git pull`: `radar parar` e `radar
  subir` (os templates e o CSS mudaram).

### A IA pode fazer (quando voce pedir)

- ⚪ **O texto oficial de Viena** nao se le daqui (o site do Alto
  Comissariado da ONU responde 403, e o sistema de documentos da ONU so
  entrega o visualizador): o § 5 foi conferido na copia da Human Rights
  Library da Universidade de Minnesota. Conferir no oficial quando der;
- ⚪ **A traducao dos temas do Ciclo 2**: montar o ciclo (decisao 123) passa a
  incluir o `--pedido --traducoes` das fichas de lei novas, depois do resumo.

## N. A crase do jeito da banca (decisao 165, 13/10)

Feito: o texto-base das questoes de lacuna mostra o `____` (85 questoes
relidas), e a tela avisa, com o link do caderno, a questao em que a leitura
perdeu alguma lacuna; a Crase 2 aponta para o assunto "Emprego da crase"
(24 reais, 83 geradas); e 20 geradas novas nos formatos da banca (10 de
lacunas com a, à e há; 10 de crase e regencia). O que falta:

### Depende de voce

- ⚪ **Reinicie o servidor** depois do `git pull`: `radar parar` e `radar
  subir` (a tela da questao e a ficha ganharam o aviso de lacuna).

### A IA pode fazer (quando voce pedir)

- ⚪ **Lacunas com outra preposicao** ("com • a • à • aos", a sua 2a imagem
  de 13/10): sao de regencia, e o lugar delas e o no "Regencia verbal e
  nominal": `radar gerar --pedido --modo treino --materia "Língua
  Portuguesa" --assunto "Termos integrantes da oração: objeto direto e
  indireto, agente da passiva e complemento nominal" --subassunto "Regência
  verbal e nominal" --quantas 10 --nivel misturada`, os passos de sempre e o
  `--importar`. Nao entrou porque a Crase 2 nao cobre esse no.

- ⚪ **As 6 questoes de lacuna que a tela avisa.** Quatro ficam sem texto:
  dizem "lacunas do texto" sem o numero, e o caderno numera os textos (2024:
  P09 e P13, q1 - 5 lacunas cada; S1, q1), ou o texto nao foi lido (2016, AS,
  q1, a de "a – à" nas alternativas). Duas mostram uma lacuna a menos (2024,
  os dois M1, q1): a leitura nao achou sinal nenhum dela. O conserto das
  quatro seria ligar a questao ao unico texto antes dela; ate la, o aviso
  manda ao caderno.

## O. Outras bancas no treino e na medida (decisao 166, 17/10)

Feito:
- o levantamento das 9 bancas, so leitura
  ([levantamento_de_bancas](levantamento_de_bancas.md));
- **a etapa A** (17/10): a classificacao das outras bancas (`--evidencia
  fora`), o leitor da IESES consertado e relido so nela (`--banca`), o
  "Treinar com outras bancas no radar" nas faixas e a origem ao lado no Meu
  desempenho. No dado de hoje: 41 questoes de Portugues da IESES, 38
  classificadas, em 13 nos; o botao aparece em 13 dias ate 07/11.

O que falta vai nesta ordem, uma etapa por conversa.

### Depende de voce (da etapa A)

- ⚪ **Reinicie o servidor** depois do `git pull`: `radar parar` e `radar
  subir` (a tela Hoje, a questao e o Meu desempenho mudaram);
- ⚪ **Conferir a classificacao da IESES** na Analises > Conferencia (a
  conferencia e sua; a do Claude Code nao vale como conferida). Dois pontos
  que a leitura levantou:
  - a 2024-q6 (2 versoes): o gabarito deu "tufao e furacao sao substantivos
    concretos" e nao aceitou "civilizacao e substantivo abstrato", que pela
    gramatica tradicional tambem parece certa; a ressalva esta na pegadinha;
  - a 2024-q7 (17 versoes, o nucleo do sujeito "Eu") foi para Classes
    gramaticais > Classificacao morfologica, e nao para pendente.

### A IA pode fazer (quando voce pedir)

- ⚪ **O resto da IESES**: Raciocinio (84 chaves, no caderno "Matematica e
  Raciocinio Logico"), Informatica (53) e Etica no Servico Publico (74) nao
  casam com materia da arvore, e nao foram pedidos. O de Raciocinio pede o
  sinonimo no `config/taxonomia.yml` antes; a matematica pura fica pendente;
- ⚪ **A palavra partida da IESES** ("senti do", "par a") continua no texto:
  o treino ja trata as versoes como uma questao so, mas a tela mostra a
  palavra partida (a das baixadas a mao vai junto, na secao de baixo). Nos
  cadernos de educacao de Biguacu 2024, 8 questoes tem a letra certa fora
  das alternativas (a leitura cortou alternativa) e 4 tem "Pagina 4" colado
  no texto - nenhuma classificada, e o treino ja recusa as primeiras;
- ⚪ **As 18 pendentes da IESES**: 17 sao a mesma questao mista (acentuacao,
  pontuacao e sinonimo nos itens I a III), e 1 cobra o sujeito, que e termo
  essencial e nao esta no edital.

### Feito depois da etapa A (17/10, decisoes 167 e 168)

- os tres botoes da faixa ("Gerar questao real", "Gerar questoes outras
  bancas", "Gerar treino"), a reserva do fechamento de 07/11 e o "ainda nao
  ha" das outras bancas;
- a FEPESE pelo conteudo (`radar provas --por-conteudo`), o `--so-novas` do
  classificar e o `--banca` do `radar questoes`;
- a lista de provas de outras bancas (`config/provas_de_outras_bancas.yml`)
  e os leitores do NC-UFPR (Policia Civil PR 2020, tres Guardas do PR) e da
  Selecon (SEJUSP/MG 2021, Policial Penal).

### Depende de voce (decisoes 167 e 168)

- ⚪ **Reinicie o servidor** depois do `git pull` (a tela Hoje mudou de novo);
- ⚪ **Conferir a classificacao das provas novas** (Analises > Conferencia,
  evidencia "provas novas de 17/10", decisao 173), **no Ciclo 2**, uns 20
  minutos por semana (pendencia D). A tela mostra a amostra de cada grupo e
  a conta (conferidas, ajustes, erros e se o grupo passa ou volta), e as
  pendentes na Parte "as pendentes"; a letra do gabarito, o dispositivo e a
  pegadinha so aparecem depois do "Responder no radar", e a questao guardada
  para o fechamento de 07/11 fica de fora. Grupo que volta: peca ao Claude
  Code que classifique de novo o grupo inteiro, com as suas correcoes como
  exemplo, e confira a mesma amostra outra vez. Das 640 de 17/10, a
  segunda leitura as cegas de 18/10 (decisao 171) conferiu 532 - 435 no
  mesmo no e 97 no no em comum das duas leituras. Ficam 108 pendentes, que
  nao treinam nem medem: as 29 em que as leituras discordam estao na lista
  unica ([conferir_classificacoes](conferir_classificacoes.md)), com as
  duas lado a lado; as outras 79 ficaram pendentes nas duas. Os nos que
  elas criaram (a arvore foi de 438 para 682) sao o passo 3 da Parte 2.
  **O passo 2 (a data da prova, 18/10)** tirou do treino 8 (2 pela lei e 6
  pelo gabarito; uma ja era pendente, e as pendentes das 640 foram a 115) e
  deu o aviso "A lei mudou depois desta prova" a 34
  (27 itens 🟣 no config/leis.yml, por conferir, com a lista no
  [leis_alteradas](leis_alteradas.md)). Dos nove gabaritos discutiveis de
  17/10, seis sairam do treino (Selecon q43, PC RJ q39 e q40, Colombo q26,
  Sao Cristovao q34 e q82, e a DEINFRA q22, que depende de olhar o caderno:
  "vinculado" ou "discricionario"); ficaram a FEPESE 2017 q40, a PC-PR
  Delegado q4 e a PM TO q44, e a PC-PR Investigador q13 ganhou o aviso do RE
  635.659. **A revisar quando o STF publicar o acordao das ADIs 7.156 e
  7.236** (prescricao da improbidade, julgadas em 01/07/2026): os dois
  avisos sairam da noticia, e um deles (PC RJ q42) depende de o teto de 20
  anos alcancar o ressarcimento ao erario. **O passo 3** apagou 31 dos 244
  nos novos, que ficaram vazios (a arvore foi a 707); **depois da sua
  conferencia, apague os 9 que continuarem vazios** - cada um e uma leitura
  de questao pendente, e por isso ficou (`conteudos.apagar_vazio` recusa o
  que ainda servir). Gabaritos discutiveis que ainda esperam:
  - das baixadas a mao de 18/10 (decisao 172): PM SE 2024 Oficial
    (Selecon), q39 - o gabarito a) (adicional noturno pago a inativo como
    ofensa a moralidade) nao tem base clara, e a d) chega perto do art. 37,
    § 1º; Guarda de Niteroi 2024, q12 - a d) (prova emprestada) tambem e
    dispensavel (Sumula 591 do STJ); Guardas de Ribeirao Preto 2023, q24, e
    Cariacica 2024, q45 - o gabarito segue a letra do art. 144, e o STF (ADPF
    995, 2023) poe as guardas na seguranca publica; SEAP-BA 2024 (FGV), q30
    - so e certa pela Lei 14.857/2024 (art. 17-A da Maria da Penha), e a q77
    cobra doutrina ("o direito a vida e o nucleo essencial");
- ⚪ **A clausula 5 do IBADE**: "nao podendo ser copiado, reproduzido,
  distribuido ou utilizado sem autorizacao expressa do IBADE". O IBADE tem o
  Agente Socioeducativo AC 2021 e o Inspetor Penitenciario ES 2023, e o robo
  pode ler. Entra ou nao e escolha sua;
- ✅ **A tela da amostra das provas novas** (decisao 173, 18/10): os recortes
  "outras bancas" e "provas novas de 17/10" na conferencia, a amostra por
  grupo com a regra (10, e mais 10 com 1 erro; os tamanhos no
  `config/amostra.yml`), as pendentes no mesmo lugar, a letra escondida ate o
  "Responder no radar" e a guardada para uma rodada que mede fora da lista.
  As 5 pendentes do lote de 18/10 ficam no recorte "outras bancas", com "so
  as nao conferidas";
- ✅ **Os PDFs que so dao a mao**: voce os baixou em 17/10 (decisao 172).
  Os termos da FGV proibem robo e "reproduzir, duplicar, copiar": o PDF fica
  so na sua maquina (`data\provas\manual\`, fora do git), e os testes usam
  texto inventado.

### As proximas etapas

- 🔴 **O resto da FEPESE pelo conteudo, devagar**: o firewall dela bloqueou
  os hotsites em 17/10 (decisao 167). Esperar alguns dias e rodar `radar
  provas --por-conteudo --limite 20` por dia; o que nao respondeu volta
  sozinho. A Policia Cientifica 2022 e o IGP 2021 estao entre eles; a PC SC
  2017 saiu do ar;
- 🔴 **As Guardas da Selecon** (Niterói 2019, Boa Vista 2019, Campo Grande
  2020, Sao Goncalo 2020, Sao Luis 2022): os links estao conferidos; falta
  baixar, ler a faixa de materias da capa de cada uma e por na lista;
- ✅ **B. O Cebraspe de multipla escolha** (decisao 169): 14 cadernos, 422
  questoes de lei, classificadas pelo bloco generico (220 no edital, 202
  fora). A PC PB 2022 ficou sem gabarito: o definitivo nao confere com o
  caderno publicado. Sobra:
  - ⚪ **a PC PB 2022 com a versao certa**: se o Cebraspe tiver o caderno
    do mesmo codigo com justificativas, ou o gabarito da versao publicada,
    as 36 voltam (18 ja classificadas). Hoje a pagina do concurso so
    mostra este par;
  - o **Certo/Errado** (13 provas, entre elas o DEPEN 2020 e a SERIS/AL):
    so treina, e precisa do acerto a parte antes de entrar;
  - a **Guarda de Barra dos Coqueiros 2020**, de outro formato (10 questoes);
- 🔴 **O IBADE** (voce liberou em 17/10): o Agente Socioeducativo AC 2021, o
  Inspetor Penitenciario ES 2023, a PC/ES 2025 e os peritos BA. O leitor e a
  lista; a fixture de teste com texto inventado (a clausula 5 proibe
  reproduzir, e o repositorio e publico);
- ✅ **Os PDFs baixados a mao** (decisao 172, 18/10): a entrada local na
  lista (`arquivo`, `arquivo_do_gabarito`, `versao`, `cargo_no_pdf`) e um
  leitor so para a FGV, a Access, a Idecan e a Selecon nova, que le so a
  versao do caderno da lista e o bloco dela no gabarito. Entraram 7 provas,
  231 questoes de lei, 107 classificadas no edital; a segunda leitura as
  cegas conferiu 102 e deixou 5 pendentes, na lista unica. Os dois pares de
  nos gemeos que o lote criou ("Direito de reuniao" / "Liberdade de
  reuniao"; "Manifestacao do pensamento..." / "Liberdade de manifestacao do
  pensamento...") vao para o passo 3 da Parte 2. Sobra:
  - ✅ **o segundo lote (18/10, adendo da 172)**: a PC SC 2026 (Idecan,
    Escrivao e Agente, Tipo A), a PC SC 2023 (Delegado, FGV, Tipo 1) e a PC
    RN 2021 (Agente e Escrivao, FGV, Tipo 1, com o `cargo_no_gabarito`),
    com os gabaritos definitivos: 186 questoes de lei, 87 no edital, e a
    segunda leitura as cegas conferiu 81 e deixou 6 pendentes. No treino de
    outras bancas: 430 questoes de lei;
  - ⚪ **o Delegado da PC RN 2021 (FGV)**: o link que voce mandou e o deste
    caderno (`pcrn-delegado-de-policia-civil-substituto-deleg-01-tipo-1.pdf`),
    que nao veio para a pasta; o gabarito definitivo que voce baixou ja tem
    o bloco do Delegado. Se quiser (e quase todo de Direito): baixar e
    salvar em `data\provas\manual\`;
  - ⚪ **os gabaritos discutiveis das baixadas a mao** (lista na Parte do
    passo 2, acima, e mais): Delegado PC SC 2024, q71 (Protocolo de Palermo
    exige a finalidade de exploracao tambem com a crianca) e q46
    (reconhecimento fotografico como "prova irritual"); Escrivao PC SC 2026,
    q25 (a certa traz "ou dele se beneficia...", trecho que a Lei
    14.230/2021 tirou do art. 3º da Lei 8.429). Decidir se saem do treino,
    como as seis de 17/10 no passo 2 da 171;
  - ⚪ **a palavra partida nas baixadas a mao**, como na IESES: "p ara", "c
    om", "L ei", "policia l", e a ligadura "ﬁ m" da Selecon - FGV 55 de 160
    questoes, Selecon 12, Access 10, Idecan 3. Nao muda o gabarito; a
    correcao muda a chave (releitura com o `--refazer`, que leva a
    classificacao) e precisa de regra que nao junte o que e letra de
    verdade (incisos I, V, X; "A, B, C e D"). Uma etapa so, com a da IESES;
  - ⚪ **o no vazio e os gemeos do lote de 18/10**: "Liberdade de reuniao"
    ficou sem questao (a sua subiu para o no em comum); "Manifestacao do
    pensamento e acesso a informacao" (4) e "Liberdade de manifestacao do
    pensamento e de expressao" (1) cobrem o mesmo. Vao com o passo 3;
  - ⚪ **a Idecan da PC-CE e da PEFOCE 2021**, que estavam na lista e nao
    vieram;
- ⚪ **O Cebraspe (registro antigo do plano)**:
  - a entrada delas no `config/provas_de_outras_bancas.yml` (o download ja
    existe), conferindo o tamanho do PDF (um veio cortado com 200);
  - o leitor do caderno de multipla escolha e o do Certo/Errado (que so
    treina), comecando pelos de seguranca publica. O C/E precisa de um
    acerto a parte: hoje o treino de outras bancas so aceita questao com
    quatro alternativas ou mais, e por isso o C/E ainda nao entra em nada;
  - antes de tudo, contar quantos dos ~50 de seguranca sao de multipla
    escolha;
- 🔴 **C. A ACAFE**:
  - a lista fixa dos cadernos da PC SC 2010 e do Delegado 2014;
  - o leitor com a limpeza: o glifo, o espaco no meio da palavra, o hifen;
  - o Agente 2014 fica fora, porque e escaneado;
  - as questoes de antes de 2019 conferidas contra a lei de hoje, como na
    [lista de leis alteradas](leis_alteradas.md);
- 🔴 **D. O IDIB**:
  - guardar o caderno durante a janela do recurso, na coleta do IDIB que o
    radar ja faz;
  - o leitor com os tipos A, B e C no mesmo PDF.

### Depende de voce

- ⚪ **O Referer do IDIB** (antes da etapa D): o download pede o cabecalho da
  pagina oficial ("Download disponivel apenas atraves do site oficial"). E
  trava contra link direto, nao login, e mandar ou nao e escolha sua;
- ✅ **O simulado da semana** passou para o radar primeiro em 24/10 e 31/10
  (decisao 170), e o que falta vai para o Qconcursos.
