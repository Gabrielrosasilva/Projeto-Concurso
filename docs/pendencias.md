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
     seção D); a explicação dela ficou de fora pelo mesmo motivo;
   - FEPESE-2023-q14 (colocação pronominal): o gabarito (A) põe "a cuja
     enteada atribuem-se", e o relativo "cuja" pede a próclise ("se
     atribuem"); a A é a menos errada, não a certa. Sem explicação;
   - FEPESE-2023-q30 ("desdenhar"): o gabarito (A) trata "desdenha do
     executivo" como a única regência certa, e o verbo também aceita objeto
     direto. Sem explicação (o trecho também não veio no pedido).
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
   Humanos): a fonte delas é só doutrina, e a regra pede dispositivo. As
   outras 10 saíram com o texto-base (decisão 132). Pequeno, se um dia
   houver dispositivo.
4. ⚪ **11 questões do complementar citadas nos resumos sem explicação**
   (decisão 133): 6 citam o texto de uma prova do complementar (o texto-base
   é só do alvo; guardá-lo também no complementar é a mesma decisão 132
   estendida, se você quiser), 3 são de Português na matéria "Conhecimentos
   Específicos", que a regra da fonte trata como Direito (pôr a matéria no
   `sem_lei` do `config/leis.yml` resolveria), e 2 têm gabarito discutível
   (acima, item 3 de "Depende de você"). Pequeno.
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
2. 🔴 **Lote 3, até 16/10**: P04 (o R+7/R+30 com "+ 3 de Português" vira duas
   linhas no plano, nas 32 faixas de 07/10 em diante; até lá, anotar no "fiz"
   só as de Direito) e U21 · P36 (o erro anotado chega ligado ao nó; o R+7 de
   17/10 não preenche a matéria "Diagnósticos").
3. 🔴 **Lote 4, até 06/11**: P07 (as rodadas que medem não repetem questão:
   o fechamento de 07/11 repetiria as 8 de RL de 10/10; muda a decisão 67),
   P01 + P09 (o anotado sem conteúdo conta no nó da matéria, escolha sua;
   muda a decisão 81), P05 (a ficha esconde o gabarito da questão ainda não
   respondida; muda as decisões 109 e 118), P10, P11 · U18 e P30.

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

### A IA pode fazer (quando voce pedir)

- 🟡 **Fontes oficiais novas** (SEJURI/DPP, PCSC, PMSC, CBMSC, prefeituras de
  Florianopolis e BC): uma por conversa, cada uma um arquivo em
  `collectors/`, com o robots.txt conferido e teste com fixture. Precisa de
  voce colar a pagina real - a sessao web nao tem internet;
- ✅ **A situacao do site de noticias e fraca** (feito em 08/10): o marco
  que vem so do Concursos no Brasil diz "segundo site de notícias" por
  extenso, no cartao e no `radar acompanhar` (decisao 141). Esperar a pagina
  detalhada continua possivel, se um dia valer;
- ✅ **A pesquisa por carreira** (feito em 08/10): `radar acompanhar
  --pedido --carreira "<nome>"` (decisao 141). O botao continua um so, no
  topo: a coleta e uma para todas as fontes;
- ⚪ **Ligar a banca definida ao estudo**: quando o cartao da Policia Penal
  ganhar banca, apontar para Analises > Edital e o padrao dela.
