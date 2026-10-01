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

### A2. 🟡 Texto de maquina na tela (C2)

- 🔴 `src/radar/eventos.py:98` escreve `Situacao: {de} -> {depois}`, e a home e
  a Analises mostram isso literalmente (ex.: "inscricoes_abertas -> encerrado").
  Mostrar uma frase por transicao ("As inscricoes encerraram", "O edital foi
  publicado", "A banca foi definida"...). O dado cru fica como esta (banco e
  `eventos.json` nao mudam); a traducao e so na exibicao;
- ⚪ acentos em todo texto que chega a tela vindo do Python ou dos templates
  (ex.: Calendario "Ultimo dia de inscricao", "Salario", "O botao"; diario
  "maior que questoes feitas"). So texto exibido: comentario, variavel e chave
  de dado ficam como estao. Os exemplos vieram do roteiro original; uma busca por
  "Ultimo dia" em `src/` e nos templates nao achou nada, entao confira o que
  ainda esta sem acento antes de editar;
- testes: a frase de cada transicao; calendario e erro do diario acentuados.

### A3. 🔴 Previsao com ano no passado e frases estranhas (C3)

`src/radar/servico/previsao.py:71-85`, na tela Previsao:

1. "Tijucas - Previsto para 2025", com o ano ja passado: mostrar "Atrasado: era
   esperado em 2025", e esses ficam no topo de "Na janela de agora";
2. "O ultimo foi ha 0 ano(s), so em 2030": usar "O ultimo foi este ano", "ha 1
   ano", "ha 3 anos", e "so" com acento (o texto atual e `ano(s)` e `so em`);
3. a conta da previsao nao muda, so como aparece. Testes com data fingida.

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
3. trocar a lei seca por "artigo cobrado": 10-15 min lendo so os artigos que
   cairam, mais a lista das pegadinhas, cada uma com o numero da questao real;
   o tempo que sobra vai para questoes;
4. questoes distribuidas pela incidencia, nao uma por artigo (FEPESE real
   primeiro; as da IA so no modo `variacao`);
5. teoria com teto: uma fonte por tema, nunca video por artigo.

**Perguntas que ficaram sem resposta** (preciso delas antes de qualquer
roteiro):

1. Quais provas FEPESE com Direito Penal estao no acervo? So a de 2019 da
   Policia Penal, ou tambem 2013 e 2016?
2. Quem classifica os assuntos: o Claude Code no VS Code, sem pagar, no mesmo
   esquema do `gerar --pedido`, ou a mao?
3. Ate o mapa ficar pronto, quero uma versao enxuta do cronograma agora (lei
   seca para 15 min e o resto em questoes)?
4. O Anki continua? A faixa de 28/09 pede 30 min para montar os baralhos.

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
Fazer depois do A2 e do A3, que mexem nos mesmos templates.

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
- ⚪ **Token do Telegram**: foi revogado depois de colado numa conversa.
  Confirmar que o novo esta so em variavel de ambiente / Secrets do GitHub.

## E. Cancelado

- **C1b, sirene para a Guarda Municipal de Florianopolis e de Balneario
  Camboriu**: nao e para fazer. O `de_olho` ja avisa com 👀 quando sair algo,
  que e tudo o que eu quero (ver decisoes.md).
