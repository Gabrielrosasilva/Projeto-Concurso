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

1. gravar assunto e artigo nas questoes FEPESE de Direito, comecando pelas
   provas de Policia Penal e Agente Penitenciario SC;
2. um mapa de incidencia por tema (🔥 cai sempre · ⚠ as vezes · 💤 nunca caiu),
   mostrado em cada faixa; o 💤 vira "leitura por cima, 10 min";
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

1. Quais provas FEPESE com Direito Penal estao no acervo? So a de 2019 da
   Policia Penal, ou tambem 2013 e 2016?
2. Quem classifica os assuntos: o Claude Code no VS Code, sem pagar, no mesmo
   esquema do `gerar --pedido`, ou a mao?

As perguntas 3 (versao enxuta agora) e 4 (o Anki continua?) foram respondidas
e feitas na Etapa 6A: rotina nova a partir de 02/10 e `anki: desativado`.

Sem resposta tambem: **quantas questoes dos arts. 1o a 12 do CP cairam em
2019?** O banco com as 8.433 questoes mora no meu PC; a copia que a sessao web
tem esta vazia. Rodar a contagem la, nao chutar.

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
