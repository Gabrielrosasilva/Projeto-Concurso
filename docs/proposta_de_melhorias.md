# Proposta de melhorias — auditoria de uso (06/10/2026)

Pedido de 06/10: auditar o uso do radar com o banco real, sem mudar nada, e propor melhorias. **Nenhum código, template, configuração ou dado foi alterado**; este é o único arquivo novo. Auditado: o commit `f58faa1` com uma foto da pasta `data/` de 06/10, 00:37. Cada item escolhido vira uma subetapa própria.

> **Andamento (06/10):** aprovada a ordem da seção "Apêndice B" e a regra do I3. Feitos o lote 1 (I1, P14, U02, P06 e os textos do I4 e do I6; decisões 134 a 137), a correção do 29/09 (P02) e as 5 fichas do I5. O P08 ficou como está (sem evidência). Os próximos lotes estão na pendência I do [pendencias.md](pendencias.md).

## Para ler primeiro

**Em três linhas.** Os números estão quase todos certos: a fonte única funciona e as regras do novo.md estão de pé (seção 1). Mas há **8 problemas críticos de precisão** que me fazem estudar ou medir errado, ou apagam dado, vários ligados ao sábado 10/10 e à comparação de 07/11, que decide o Ciclo 2 (seção 3). E as telas do dia têm muito mais texto do que precisam: o Hoje tem 2.104 palavras visíveis e 52 botões; o desenho da seção 8, medido num protótipo com a mesma régua, cai para 441 palavras e 8 botões (~450 com os enxertos, estimativa à mão), sem tirar nenhuma regra.

**Só você pode dizer** (seção 3.1): se as 10 questões de Português anotadas em 29/09 são as mesmas 10 respondidas no radar naquela noite (P02); se as 10 de 28/09 foram do Qconcursos ou das geradas (P08); e qual regra vale para o "anotado" sem conteúdo (P01).

**Com prazo:**

| Até | O quê | Itens |
|---|---|---|
| hoje, 18:00 | No R+7, anotar no "fiz" só as 7 de Direito Constitucional; as 3 de Português ficam fora dele | P04 |
| amanhã, 07/10 | O R+7 da LEP diz "o que você estudou em 30/09", e 30/09 não tem registro: decidir se é revisão ou primeiro contato | I2 |
| 09/10 | A ordem dos diagnósticos de 10/10; a Reduzida e o Plano B de sábado, que hoje pulam a medição; o "fiz" que vem com 20; o Resumo dentro das faixas que medem sem consulta | I1, P14, P03, U02 |
| 17/10 | O R+7 dos diagnósticos sem 40 formulários e sem a matéria "Diagnósticos" | I4, P36 |
| 07/11 | O fechamento não pode repetir as questões do diagnóstico; o plano e a tela precisam dizer o mesmo sobre o que decide o Ciclo 2 | P07, P30 |

**O que mais muda a tela** (seção 8 e tabela da seção 6):
1. **Hoje:** a faixa da hora num painel no topo, as outras faixas em uma linha cada, o treino de IA dobrado (2.104 → 441 palavras no protótipo, ~450 com os enxertos; 52 → 8 botões).
2. **Meu foco:** sai a lista "O que estudar agora", que contradiz o plano, e o "Começar treino", que gasta as questões que medem; entra a "Revisão de hoje", a mesma do Hoje; a home volta a caber em 1366×680.
3. **A volta:** a rodada e a ficha voltam para a faixa; a ficha abre na seção certa e esconde o gabarito das questões que eu ainda vou responder.
4. **Telas de consulta:** Incidência (9.129 palavras), Conferência (117.897 palavras, 2,56 MB) e Macetes (5.953) passam a abrir dobradas, pelo que falta.
5. **Um nome por conceito e um rótulo por ação:** "treino" só para IA, "simulado" só para questão real; na caixa "Revisão de hoje", cada fila com o seu nome (fila 1-7-30, erros do caderno, R+7), nunca somadas.

## Como foi medido (e o que eu não vi)

**O que foi auditado.** O código do commit `f58faa1` (06/10, 00:34) e uma foto da pasta `data/` de 06/10 às 00:37, os dois copiados para fora do repositório. A cópia rodou num servidor próprio (porta 8765); o seu servidor (porta 8000) e o seu `data/radar.db` não foram usados. Só houve GET: nenhum formulário foi enviado, nenhuma rodada foi criada. As linhas citadas (`hoje.html:1264`) são as do commit `f58faa1`.

**Outra sessão estava trabalhando ao mesmo tempo** no texto-base das questões e na decisão 129 (nós novos da LEP, com `models.py`, `questoes.py`, `migracoes.py`, `ficha.html`, `questao.html` e os JSON de `data/` modificados, e o banco migrado para a versão 6 às 00:36). O código dessa sessão não entrou na auditoria (o código auditado é o do `f58faa1`), mas **parte do dado entrou**: a foto de `data/` das 00:37 é posterior às gravações dela. O banco da cópia está na versão 6; o `conteudos.json` tem 438 nós (429 no commit, 9 novos da decisão 129); o `fichas.json` (16 fichas ganharam nós), o `classificacoes.json` e o `questoes_geradas.json` também diferem do commit. Por isso o seletor de conteúdo tem 439 opções. Onde um achado toca nesse trabalho (a questão de Português sem o "texto 2", as faixas da LEP sem nó), ele está marcado.

**A régua.** Todas as telas foram medidas pelo mesmo script, com as mesmas definições:
- *palavras visíveis*: o texto que o navegador mostra ao abrir, sem o que está dentro de `<details>` fechado, nas janelas de resumo (`.ds-janela`) e em `hidden`;
- *cartões*: elementos `ds-cartao`; *botões*: `<button>`, `<input type=submit>` e links com classe de botão; *dobras*: `<summary>` visíveis;
- *frases em prosa*: frases de 5 palavras ou mais em parágrafos, notas e legendas;
- *frases explicativas* (as que explicam como o sistema conta, e não o que fazer): a régua não as separa. A coluna "Frases em prosa" é uma aproximação por cima; a separação foi feita à mão só no Meu foco (5 de 16), no Edital (~23 de 35) e no Meu desempenho (465 palavras);
- *"está no topo?"*: quantas palavras visíveis vêm antes do título da seção que importa. No Hoje, a régua conta na ordem do HTML, que é a ordem do celular; no notebook (≥ 1100 px) a lateral vai para a direita, e por isso os números do Hoje são dados também só para a coluna principal.

A hora do Hoje foi simulada (07:00 e 19:30, e outras) trocando só o relógio do cronograma. Os sábados (10/10, 17/10, 07/11) foram vistos como dia futuro e, para os botões, renderizados no próprio dia.

**Como os achados foram feitos.** Sete agentes leram e mediram as telas (um grupo cada), três conferiram precisão, regras e coerência, e um contou os cliques. Cada suspeita de precisão (104 ao todo) passou por um verificador independente, que tentou derrubá-la refazendo a medida no banco da cópia e lendo o código: 98 confirmadas, 5 refutadas, 1 incerta. Depois, as 98 confirmadas e a incerta (P08), mais o "Começar treino" (P12), que não passou por verificador, foram juntadas em 57 problemas (seção 3), e uma conferência de fidelidade comparou cada um com a fonte; as melhorias viraram uma lista única (seção 4); três desenhos independentes do Hoje e do Meu foco passaram por um juiz (seção 8); e as ideias novas, por um crítico da §24 (seção 5). As suspeitas refutadas estão em 3.6.

**O que eu não vi** (e por isso não afirmo):
- a tela no navegador de verdade (cor, altura, quebra no celular): a régua conta palavras, não pixels. As únicas medidas em pixels das telas reais são capturas sem cabeça do Edge na cópia: a home (o conteúdo termina em ~770 px) e o Edital (a tabela rola na horizontal em 1366 px); as do protótipo estão na seção 8;
- o efeito do JavaScript (cronômetro e `dobra.js`): quem deixou blocos dobrados vê menos palavras do que as contadas;
- o Qconcursos (externo, com login; o CLAUDE.md proíbe raspar): os cliques foram contados até o link sair do radar e na volta para anotar;
- qualquer coisa que exija POST (criar rodada, responder, conferir): o que acontece depois foi lido no código, não visto;
- o dia de hoje (06/10) com dado: a foto não tem nada marcado hoje;
- o estado de amostra, a ordem e a projeção com várias matérias: só Português, Penal e Constitucional têm resposta no banco;
- a exatidão jurídica ou gramatical dos textos de IA (fichas, resumos, macetes): foi conferido o selo, a procedência e a frase, não o conteúdo;
- as 65 fichas uma a uma (foram abertas 2, a aba do dia e a lista do ciclo);
- qual entrada você usa todo dia (o `Radar.bat` abre `/hoje`; `localhost:8000` abre `/`): os cliques foram contados pelas duas;
- as frases explicativas das outras telas, uma a uma (a tabela 2.0 dá as frases em prosa);
- o tempo de resposta do Hoje com a "Revisão de hoje" proposta (o `estudo.pontas` a cada abertura).

## 1. O que está bom e deve ficar

A base é sólida. O que a limpeza precisa preservar, primeiro nas regras e depois nas telas:

**As regras do novo.md estão de pé** (o detalhe conferido está em 3.5):
- **Uma fonte só para as contas.** Hoje, Semanas e Minhas matérias somam igual, o "Fiz hoje" bate com o `metricas` nos três dias com dado, e os templates das telas de acerto só desenham número pronto.
- **A gerada treina e não mede.** O treino de IA é sempre um número à parte ("fora do acerto real; conta no volume") e nunca entra no acerto, no estado, na prioridade nem no nível; toda questão gerada traz "Gerada por IA: não é questão oficial da FEPESE."
- **Alvo, complementar e meu desempenho nunca se somam.** Ficam em colunas e linhas próprias, e o peso 0,25 do complementar só ordena — e a tela diz isso.
- **Sem previsão.** Nenhuma palavra proibida ("vai cair", "sempre cobra"…) em texto do sistema; a Incidência fala só do que aconteceu ("apareceu em 1 de 2 provas"); a Previsão de concursos se declara previsão.
- **Amostra e frase padrão.** "N questões · M provas" em toda linha da Incidência e no "caiu ou não caiu"; "Amostra insuficiente (15 de 20)" e "Responda mais 5" na home; a frase "Não há evidência suficiente no acervo para afirmar isso." sai sempre exata, da constante única.
- **Procedência.** O texto de IA novo diz o modelo e a data ("Claude Code (claude-opus-5-5), importado manualmente, em 05/10/2026"), e o Resumo dá a fonte de cada frase.

**No dia (Hoje e sábados):**
- O cartão **Agora** muda com o relógio, e a faixa em curso ganha contorno e a etiqueta AGORA.
- A **faixa diz a tarefa concreta**: os incisos a ler com "Teto de 40 min, uma fonte só", o filtro do Qconcursos, o número de questões — é o §12 do novo.md funcionando.
- O **"fiz X, acertei Y" fica na própria faixa** e volta para ela; o **Resumo abre numa janela só com CSS**, sem sair da página; o aviso da decisão 130 aparece na faixa certa.
- **Nos sábados que medem**, a faixa diz onde, quantas e se é cronometrada; a rodada não pode ser criada antes do dia e é gravada uma vez (em dia passado o botão ainda aparece: P12); a composição mostra a amostra e o alvo separado do complementar; o R+7 de 17/10 é honesto quando não há dado; a comparação de 07/11 tem três colunas que nunca se somam.
- **A rodada:** um clique por questão, sem acerto à vista, e ela continua de onde parou.

**Nas outras telas:**
- **Meu foco** é leve (295 palavras), não afirma o que não sabe ("banca: hipótese FEPESE", "base pequena") e já usa a fila única de revisão (decisão 128).
- **Caderno de erros:** o cartão do erro já é a revisão (atraso, "revisão 1 de 3", os dois botões); o erro atrasado não some; anotar exige a regra certa e diz quando o erro volta.
- **Ficha:** "Ler exatamente", "Artigos-chave do dia" e "Como pesquisar" formam a tarefa com começo, meio e fim; a questão real inteira fica num `<details>`; "Por que agora" diz "regra de priorização, não previsão".
- **Análises:** o Edital diz a fonte de cada coluna (edital 🟢, provas 🔵 com as anuladas por ano, meu acerto 🟡); Minhas matérias diz "Ainda não estudei — entra no Ciclo N" em vez de mostrar zero; o Meu desempenho separa "radar" e "anotado" em toda linha e pinta de cinza a semana sem base; a Incidência tem filtro por matéria; a Conferência põe a questão ao lado da proposta e diz quem conferiu.
- **Macetes:** cada parte do cartão traz o selo da sua origem, e macete sem fonte ou sem procedência não aparece.
- **Concursos e Mais:** a lista responde onde, quanto e até quando; o salário diz a origem; o "não sei ainda" aparece onde não se sabe; a legenda dos selos mora num lugar só (o que permite tirar as legendas repetidas das outras telas); o backup tem alerta quando falha.

## 2. Os problemas, tela por tela

Cada tela tem quatro linhas: **para que eu venho**, **isso está no topo?**, **medidas** (régua única, ver "Como foi medido") e os **problemas**, com a evidência. Gravidade entre colchetes: é a da tela, dada por quem a leu; a prioridade de cada P segue a régua da seção 3 e pode ser outra (o P43, por exemplo, é [alta] no relatório e BAIXA na seção 3). Os problemas de precisão estão resumidos aqui e detalhados na seção 3 (P01…P57); as melhorias, na seção 4 e na tabela da seção 6 (U01…U64).

### 2.0 As medidas de todas as telas

Palavras visíveis ao abrir (o que o navegador mostra sem clicar); entre parênteses, as do HTML inteiro, contando o que está em `<details>` fechado e nas janelas de resumo.

| Tela | Palavras visíveis (HTML) | Cartões | Botões | Dobras | Formulários | Frases em prosa | Peso |
|---|---:|---:|---:|---:|---:|---:|---:|
| Meu foco (`/`) | 295 (295) | 6 | 5 | 0 | 3 | 16 | 13 KB |
| Hoje, 06/10 às 07:00 | 2.104 (6.530) | 14 | 52 | 12 | 25 | 70 | 246 KB |
| Hoje, 06/10 às 19:30 | 2.107 (6.533) | 14 | 52 | 12 | 25 | 70 | 246 KB |
| Hoje, 05/10 (dia anotado) | 1.796 (11.687) | 14 | 42 | 15 | 13 | 82 | 496 KB |
| Hoje, sáb. 10/10 (diagnósticos), visto de 06/10, sem os botões do dia | 2.146 (15.572) | 14 | 15 | 10 | 1 | 81 | 273 KB |
| Hoje, sáb. 17/10 (R+7 dos diagnósticos) | 2.087 (23.105) | 14 | 23 | 11 | 5 | 77 | 378 KB |
| Hoje, sáb. 07/11 (fechamento) | 2.339 (45.749) | 14 | 18 | 10 | 2 | 76 | 671 KB |
| Semanas | 289 (307) | 3 | 0 | 2 | 0 | 15 | 18 KB |
| Fichas (aba do dia) | 469 (2.521) | 6 | 13 | 0 | 0 | 24 | 43 KB |
| Fichas, todos os temas | 2.862 (2.862) | 1 | 1 | 0 | 0 | 266 | 70 KB |
| Ficha: Art. 5º, XVII a XLIX | 3.134 (3.787) | 12 | 8 | 6 | 2 | 190 | 51 KB |
| Ficha: Concordância verbal 1 | 2.533 (4.362) | 12 | 5 | 14 | 2 | 147 | 58 KB |
| Simulado (lista) | 579 (651) | 6 | 3 | 8 | 3 | 16 | 31 KB |
| Rodada: questão real / gerada | 177 / 180 | 1 | 5 / 6 | 0 | 0 | 8 | 6 KB |
| Relatório de rodada de IA (`/simulado/10`) | 377 (515) | 7 | 1 | 1 | 0 | 15 | 16 KB |
| Gerar questões | 1.909 (3.063) | 4 | 30 | 17 | 3 | 84 | 67 KB |
| Caderno de erros | 235 (235) | 5 | 6 | 0 | 5 | 10 | 14 KB |
| Anotar erro | 1.979 (1.979) | 1 | 2 | 0 | 1 | 84 | 93 KB |
| Macetes | 5.953 (5.953) | 17 | 41 | 0 | 1 | 413 | 91 KB |
| Análises › Edital | 1.557 (1.557) | 6 | 1 | 0 | 1 | 35 | 42 KB |
| Análises › Minhas matérias | 520 (520) | 12 | 2 | 0 | 0 | 37 | 20 KB |
| Análises › Meu desempenho | 2.278 (2.278) | 6 | 2 | 0 | 2 | 138 | 41 KB |
| Análises › Incidência | 9.129 (14.716) | 14 | 1 | 26 | 1 | 573 | 276 KB |
| Análises › Conferência | 117.897 (117.897) | 163 | 701 | 0 | 594 | 2.030 | 2,56 MB |
| Concursos › Todos | 769 (1.426) | 0 | 31 | 31 | 31 | 32 | 85 KB |
| Concursos › Acompanhando | 130 | 1 | 1 | 0 | 1 | 5 | 10 KB |
| Concursos › Calendário | 276 | 3 | 1 | 0 | 0 | 16 | 9 KB |
| Concursos › Previsão | 915 | 23 | 0 | 0 | 0 | 73 | 19 KB |
| Mais | 273 | 4 | 1 | 0 | 0 | 17 | 10 KB |
| Mais › Auditoria | 1.221 | 1 | 0 | 0 | 0 | 1 | 14 KB |

Duas leituras dessa tabela. (1) As telas do dia (Hoje, ficha) passam de 2.000 palavras; a home, que tem a pergunta mais simples, é a mais enxuta (295). (2) O peso escondido cresce com o dia: o Hoje de 07/11 tem 45.749 palavras no HTML porque o botão "📝 Resumos (65)" põe os 65 resumos na página.

### 2.1 Hoje — dia comum (`/hoje`, `hoje.html`)

- **Para que eu venho:** saber o que fazer agora, abrir a ficha ou o resumo, fazer as questões da faixa e anotar; à noite, marcar como foi o dia.
- **Está no topo?** De manhã, sim: no notebook (duas colunas a partir de 1100 px) a primeira faixa vem 12 palavras abaixo do topo da coluna principal. À noite, não: **a ordem não muda com a hora**. "Noite — questões" está depois de 858 palavras da coluna principal às 07:00 e às 19:30; a faixa em andamento às 19:30, depois de ~1.579; "Como foi o dia", depois de ~1.771. O cartão **Agora** acerta a faixa da hora ("EM ANDAMENTO · 19:15–19:40 Concordância verbal 1"), mas não é link. No celular, a lateral (Agora, Esta semana, Objetivo, Caderno, Mapa do ano: ~209 palavras) vem antes da primeira faixa.
- **Medidas:** 2.104 palavras visíveis (6.530 no HTML) · 14 cartões · 52 botões · 12 dobras · 25 formulários · 70 frases · 246 KB por abertura (33 KB se a resposta fosse comprimida).
- **Problemas:**
  - [alta] **O treino de IA ocupa mais espaço que a tarefa que mede.** O bloco das geradas ("2º Se quiser mais, no radar", 13 botões "Treinar no radar", os 3 passos com comandos de terminal) tem 774 das 2.104 palavras (37%) — na Fixação das 10:55, 190 das 274 palavras da faixa (`hoje.html:1100-1141`).
  - [alta] **A mesma posição na árvore duas vezes em cada faixa, e o mesmo tema em quatro faixas.** A linha Assunto/Subassunto/Elemento (`hoje.html:934-943`, decisão 71) e o "Você estudou: …; na árvore: …" (`hoje.html:1103-1104`, decisão 112) somam 511 palavras (24%). O art. 5º, XVII a XLIX aparece em 4 faixas com a mesma linha, o mesmo "🔵 Caiu em 2013: 1 questão · 1 prova" e os mesmos botões: 8 "📋 Ficha de estudo" e 8 "📝 Resumo" para 3 temas.
  - [alta] **Instruções que se contradizem na mesma faixa.** Português (12:15 e 19:15): "🔵 Comece pelas 6 questões reais da FEPESE… [Começar pelas 6 do radar]" e logo abaixo "1º No Qconcursos (são as que medem)" (`hoje.html:1074-1080` × `1105-1106`). Na Fixação com consulta, "1º No Qconcursos (são as que medem)", enquanto o detalhe da mesma faixa diz "com a lei aberta: fixam, não medem" (`config/cronograma.yml:873-874`).
  - [alta] **O R+7 esconde as 3 questões de Português.** À vista, "10 questões" e o filtro de Constitucional; o "+ 3 de Português: artigo, numeral e pronome" só aparece em "ver detalhe" (`cronograma.yml:913-914`). São 34 faixas R+7/R+30 assim no Ciclo 1. E o "fiz" grava as 10 em Direito Constitucional (P04).
  - [alta] **Faixa feita toda no radar não pode ser marcada** ("Faixa de questões com 0 questões não conta como feita", `servico/cronograma.py:362-369`). A Fixação de Concordância de hoje (6 reais, 0 no Qconcursos) nunca fica "feita", e a sugestão do dia nunca chega a Ideal. Em 05/10 o contorno foi desmarcar e lançar extra (P03).
  - [média] **Coisa de outra hora antes do dia (no celular).** O Mapa do ano nasce aberto (102 palavras, `hoje.html:697`), o Objetivo e o motivo do nível ("🟡 A semana 1 fechou com 6 dias abaixo da Ideal…") vêm antes da primeira faixa.
  - [média] **O mesmo dado duas vezes:** a sequência (herói "🔥 1 dia seguido" e "Esta semana"), a meta (herói e Objetivo), "49 questões" e "termina às 20:05" (que repetem os cabeçalhos dos blocos).
  - [média] **"1h55 de estudo" é só a manhã** (`radar/cronograma.py:268-269`); o dia planejado tem 3h50 (P16).
  - [média] **A lei seca manda ver o porquê "no Plano B do dia"** (`cronograma.yml:886-888`, 26 faixas), mas o porquê só aparece com o Plano B ativo — que rebaixa o dia para Mínima.
  - [baixa] **246 KB por abertura, sem compressão.** O `<select>` de 439 conteúdos do Estudo extra é 32% da página; em 05/10, com 4 cópias dele (a do extra novo e 3 dos "editar"), a página vai a 496 KB.
  - [baixa] **Com JavaScript, o primeiro cartão da lateral é um painel de teste** ("🔔 Testar aviso", "⏳ Testar em 10 s" e a linha de diagnóstico da notificação, `hoje.html:597-613`).
  - [baixa] **A Correção não tem "📓 Anotar erro"** e esconde a instrução "copie no caderno de erros" no "ver detalhe".
  - [baixa] **Frases que explicam o sistema:** "O que eu anoto aqui é o diário do cronograma: não entra em nenhum acerto medido do radar." (`hoje.html:1364`), o texto do Estudo extra (`1433-1437`) e outras.

### 2.2 Hoje — dia passado (`/hoje?data=2026-10-05`)

- **Para que eu venho:** conferir e corrigir o que fiz ontem.
- **Está no topo?** Não: o topo é o de hoje ("Agora · Este dia: começa às 10:15"); o resumo do dia ("Fiz hoje: 26 questões…") só aparece depois de 1.549 palavras.
- **Problemas:** [alta] as faixas feitas no radar ficam abertas e convidam a "✓ Fiz" com o número do plano (Fixação 8, R+7 10; as rodadas de IA 7 e 10 não guardam a faixa) — P03; [média] o tempo do plano aparece como "Estudo extra" ("2h de estudo (1h do plano + 1h extra)"), por causa do contorno de 05/10; [média] o rótulo "Fiz hoje" é fixo num dia que já passou; [baixa] 496 KB, 63% em 4 cópias do `<select>` de 439 conteúdos.

### 2.3 Hoje — os sábados que medem (`/hoje?data=2026-10-10`, `-17`, `2026-11-07`, `2026-10-03`)

- **Para que eu venho:** medir (10/10: diagnósticos de RL e Português no radar e o simulado da semana no Qconcursos), refazer os erros (17/10), fechar o ciclo (07/11).
- **Está no topo?** Não. Nada diz que é o sábado que mede. Em 10/10 a primeira faixa que mede está na palavra 505 da coluna principal, o botão "Criar a rodada" do RL na 750 e o do Português na 1.808. Em 07/11 (página inteira), o botão do fechamento está na palavra ~2.090 (2.088 e 2.099 em dois renders) e a tabela da comparação na 2.154 (1.969 na coluna principal).
- **Medidas (renderizado no próprio dia, 10/10 às 08:00; a tabela 2.0 traz a tela vista de 06/10):** 2.153 palavras visíveis (17.565 no HTML), 23 botões, 369 KB; 1.564 das 1.906 palavras da coluna principal (82%) são listas de composição: simulado da semana 704, revisão semanal 336, diagnóstico de Português 291 e diagnóstico de RL 233. Em 07/11: 671 KB, e 94% das palavras do HTML são as 68 janelas de resumo.
- **Problemas:**
  - [alta] **A Reduzida e o Plano B de sábado pulam o que mede:** "reduzida: Faça só o simulado da noite." (`cronograma.yml:1328` e `2015`), e o Plano B troca o dia por "refazer as erradas" no Qconcursos (`radar/cronograma.py:912-921`). O dia apertado perde justamente o diagnóstico (P14).
  - [alta] **"fiz = 20 / 40 / 50" já preenchido nas faixas que são 100% no radar** (`hoje.html:1264`): um clique em "✓ Fiz" grava questões que não foram feitas; depois de responder, o 0 é recusado (P03).
  - [alta] **A comparação de 07/11, "que decide o Ciclo 2", não tem como decidir:** a composição do fechamento dá 13 de LP, 8 de RL, 13 de DH, 4 de DC, 4 de DP e 8 de LEP — todas abaixo de 20, o mínimo da matéria, então toda célula sai "Amostra insuficiente"; e só RL e Português têm diagnóstico em 10/10 (`sabado.py:318-324`) — P30.
  - [alta] **O fechamento de RL repete as questões do diagnóstico** (simulação só de leitura com o banco de 06/10: as 8 de RL do fechamento são as 8 já usadas em 10/10) — P07.
  - [média] **O botão da medição vem depois de toda a composição:** no diagnóstico de RL, 245 palavras de lista e de regra entre o título e o botão; no fechamento, 898 (`hoje.html:1019-1061`).
  - [média] **"📝 Resumos (20 / 30 / 65)" dentro das faixas que medem**, que são sem consulta e cronometradas (decisão 120).
  - [média] **A Correção não mostra o resultado** das rodadas do dia (14 palavras; o detalhe manda "anote a nota e os erros por matéria").
  - [média] **"estudado em 01/10"** é a data do plano, não do estudo (`composicao.py:572`) — P50.
  - [média] **O simulado de sábado do Qconcursos não entra por matéria** (a faixa não tem `materia`; `metricas.py:309-311`): Minhas matérias não o vê (P30).
  - [média] **03/10 (passado): os diagnósticos que passaram para 10/10 ainda mostram o botão de criar a rodada** (`hoje.html:1051`), embora a tela diga que ele "aparece no dia da faixa" (P12).
  - [média] **Três "refazer erros" com fontes diferentes** no sábado: a revisão semanal mostra só o caderno ("Os erros anotados na semana: 2"), enquanto o radar gravou 10 erradas em questão real na semana 1.

### 2.4 Semanas (`/semanas`)

- **Para que eu venho:** ver se estou evoluindo semana a semana e no ciclo.
- **Está no topo?** Em parte: o gráfico responde "quanto fiz" (68 e 26), mas o "67%" da semana 2 vem de 3 respostas, a barra de 26 tem 23 questões de IA, e a semana atual vem por último.
- **Medidas:** 289 palavras · 3 cartões · 0 botões · 15 frases · 5 selos 🟡 e nenhum 🟣.
- **Problemas:** [alta] **setas sem amostra e na semana em andamento** — "67% ↑ +27%" com 3 respostas e "1 ↓ −25 erros" em verde, comparando 2 dias com uma semana inteira (`servico/semanas.py:196-219`, sem mínimo) — P11; [média] "2h ↓ −290 estudadas": a seta em minutos, sem unidade (P38); [média] a linha do treino de IA sem 🟣, que no Hoje ela tem (P46); [média] a barra soma IA sem mostrar; [média] **não há linha do ciclo atual** — o resumo do ciclo é calculado (`semanas.py:358-362`) mas só aparece com o ciclo encerrado; [baixa] o cabeçalho explica o sistema e fala de meta, que a tela não mostra.

### 2.5 Meu foco (`/`, `home.html`)

- **Para que eu venho:** abrir o dia: o que estudar agora e por quê, o que revisar, se estou evoluindo; chegar à primeira questão em até 2 cliques.
- **Está no topo?** Em parte. "📅 Hoje no cronograma" dá o quê nas primeiras 28 palavras, sem o porquê. Na palavra 70, **"📚 O que estudar agora" dá outra resposta** (1. Direitos Humanos 2. Língua Portuguesa 3. Legislação Especial) e não diz que está fora do plano. A evolução fica abaixo da dobra em 1366×680.
- **Medidas:** 295 palavras · 6 cartões · 5 botões · 3 formulários · 16 frases (5 de regra do sistema) · selos 🟢 1, 🟡 2.
- **Problemas:**
  - [alta] **Duas respostas para "o que estudar" na mesma tela** (`home.html:85-106` × `156-178`). A lista sai de `servico/inicio.py:140-178` (peso do edital × (1 − acerto) × tempo), que não lê o cronograma; Legislação Especial é do Ciclo 2 (Minhas matérias diz "entra no Ciclo 2") e o 3º lugar sai de um empate de 5 desfeito pela ordem alfabética (P15).
  - [alta] **"Começar treino · 20 questões" sorteia do alvo de qualquer matéria** (`app.py:1657-1671` → `servico/simulado.py:238-280`) e gasta as questões que o diagnóstico de 10/10 e o fechamento de 07/11 preferem nunca respondidas (P12).
  - [média] **Revisar com dois números e dois botões que se sobrepõem:** "8 conteúdo(s) [Fazer as revisões de hoje]" e "11 questão(ões) que errei [Revisar agora]"; 10 das 11 erradas são as primeiras questões da rodada de revisão; e a home chama de "a mesma fila" 8 dos 16 itens do Meu desempenho (P19).
  - [média] **O Revisar só tem Português**, e não diz que Penal e Constitucional ficam de fora (decisão 81, P09) nem mostra o caderno (2 erros vencidos desde 30/09).
  - [média] **"prazo de revisão vencido (1 dia(s)) · atrasada 6 dia(s)"**: o 1 é a etapa R+1, o 6 é o atraso (`estudo.py:460`).
  - [média] **A home não cabe mais em 1366×680** (termina em ~770 px na captura), critério da especificação e da decisão "Navegação nova e a home de 3 blocos".
  - [baixa] O cartão do alvo ocupa 1/3 da linha com dado parado e repete a faixa "Concurso"; frases de sistema, uma desatualizada ("A linha do tempo passa a registrar a partir da próxima coleta"); "162 questões" sem dizer "sem as 8 anuladas", contra "147 de 152" no Edital (P23).

### 2.6 Estudar › Simulado (`/simulado`, a rodada e o relatório)

- **Para que eu venho:** refazer as reais que errei (d) e, às vezes, montar um simulado de reais (e).
- **Está no topo?** Para refazer, sim ("Só meus erros" na palavra 20). Para o simulado do sábado, não: as rodadas que medem nascem no Hoje, e esta tela não diz isso.
- **Medidas:** lista 579 palavras · 6 cartões · 3 botões · 8 dobras. Questão real: 25 palavras antes do enunciado; **questão gerada: 75**. Relatório de IA: o primeiro erro aos 137 palavras.
- **Problemas:**
  - [alta] **"Refazer os 11 erro(s)" monta uma rodada de 10** (`app.py:1393` sem quantidade; `servico/simulado.py:535`, padrão 10) — P32.
  - [alta] **"Como você vai até agora" conclui com 15 questões**, sem o estado de amostra, com a linha vermelha por um 60 escrito no template (`simulado.html:205`) e a frase fixa "é onde vale gastar tempo de estudo" (P18).
  - [alta] **O formulário "Começar" sorteia de qualquer banca e de provas recusadas** (`servico/simulado.py:83-150`): em Língua Portuguesa, 1.482 questões do complementar aceito, 252 da IESES e 24 de provas recusadas (P13).
  - [alta] **Na questão gerada, o artigo vem ANTES do enunciado e às vezes entrega a resposta** (`questao.html:100-101`; ex.: geradas 778 e 779) — P21.
  - [alta] **No relatório da rodada de IA, a legenda diz "a correta do gabarito"** (`relatorio.html:110`, sem condição) e a questão de IA aparece sem procedência (0 ocorrências de modelo ou data no relatório) — P43 e P44.
  - [média] "Essa questão está errada" fica antes do enunciado, vale com 1 clique e não tem volta (`servico/geradas.py:742-775` apaga as respostas dela em todas as rodadas).
  - [média] O relatório manda ver "o acumulado na home", que não o mostra; "Por matéria" repete o resultado geral (todas as 8 rodadas têm uma matéria só); os botões levam para fora do dia ("Gerar mais" cai no cartão da API; "Voltar ao meu foco"); a rodada aberta pela faixa não volta para a faixa.
  - [média] "Suas rodadas" não diz que rodada é cada linha (nem o nó da IA) e só cresce.
  - [baixa] "8.462 questões no acervo" soma alvo, complementar, recusadas e outras bancas (P52); "sem materia" sem acento (já na auditoria independente de 04/10, R14 item 12, e continua); Processual Penal em duas opções (P24; resto do R14 item 7 / BUG-4); o artigo da gerada cortado em 200 caracteres, em 57 geradas (P22).

### 2.7 Estudar › Gerar questões (`/geradas`)

- **Para que eu venho:** treinar com as geradas de um assunto e ver o que falta gerar.
- **Está no topo?** Não. O primeiro cartão gera pela API ("Ver o custo disto", "Gerar e treinar — gasta US$ 0.14"), que sem chave termina em "Falta a chave da Anthropic". O botão "Treinar", que é o que eu uso, só vem depois de 241 palavras.
- **Medidas:** 1.909 palavras (1.390 sem as opções dos selects) · 4 cartões · 30 botões · 17 dobras · 84 frases.
- **Problemas:** [alta] **o cartão da API contradiz o texto da decisão 114** ("o botão da API não aparece") e empurra o treino para baixo; [média] o botão pago ignora o assunto escolhido (`app.py:916` só lê matéria e quantidade) — P53; [média] "Qualquer matéria" é o padrão do treino (sorteia entre 801 geradas, inclusive temas que eu não estudei); [média] "Os assuntos do cronograma" tem 43 itens, ~1.060 palavras, sem a data da faixa e com o caminho repetido 10 vezes; [média] "Como você vai, nos dois" mostra "27% (15)" sem o estado de amostra; [baixa] nomes crus das matérias (Processual Penal duas vezes, Informática fora do edital: o R14 item 7 da auditoria independente, ainda aberto).

### 2.8 Revisão › Caderno de erros (`/erros`) e Anotar erro (`/erros/novo`)

- **Para que eu venho:** rever os erros que vencem hoje (✅ Já sei / ↻ Ainda erro); anotar a regra certa depois das questões.
- **Está no topo?** Em parte: "2 para rever hoje" aparece cedo, mas os 2 erros vêm depois de "O que mais te derruba" e do filtro de 4 campos. No Anotar erro, **"A regra certa" — o campo que importa — é o 7º**, depois de um `<select>` de 439 opções.
- **Medidas:** caderno 235 palavras, 6 botões; Anotar erro 1.979 palavras, das quais 1.898 são as opções do `<select>` (71.634 bytes, 77% da página).
- **Problemas:**
  - [alta] **A revisão do caderno não está acontecendo:** as 2 entradas são de 29/09, estão atrasadas há 6 dias, nunca foram revisadas e foram escritas como relato de sessão, não como regra.
  - [alta] **O nó que a faixa mostra não chega ao formulário:** o link "📓 Anotar erro" leva só data, matéria e assunto (`app.py:246-257`); o GET nem aceita `conteudo` (`app.py:1776-1799`). Sem o nó, o erro não vira gatilho de revisão daquele conteúdo (P09).
  - [alta] **17/10: até 40 erros, um formulário de 8 campos para cada,** com a matéria "Diagnósticos" (rótulo de faixa mista) e sem referência (P36).
  - [média] O caderno está em dois menus (sub-aba do Hoje e de Revisão) e o clique pelo Hoje troca de seção; Macetes não tem as sub-abas de Revisão.
  - [média] Não há como corrigir nem arquivar uma entrada errada (só `/erros/novo` e `/erros/{id}/revisar`).
  - [média] O caderno não aparece na home (o "🧠 Revisar" não o menciona).
  - [baixa] "O que mais te derruba" repete a lista de 2 erros; "Onde" vem sempre "Qconcursos", até para erro do radar; o assunto chega com o prefixo da faixa ("Aprendizagem: …").

### 2.9 Revisão › Macetes (`/macetes`)

- **Para que eu venho:** reler o macete e a pegadinha da matéria do dia antes das questões ou da revisão.
- **Está no topo?** Não. Não há índice; Direito Constitucional (a matéria desta semana) começa na palavra 1.699; a seção de outras bancas, na 5.774.
- **Medidas:** 5.953 palavras · 17 cartões · 41 botões · 413 frases · 🟣 60, 🔵 29, 🟢 1 · 16 avisos de lei.
- **Problemas:** [alta] **o cartão conta diferente da Incidência para a mesma matéria do alvo** (LP 23 × 22; Direito Penal 13 × 9: o cartão agrupa pela matéria do caderno e inclui pendentes) — P28; [alta] **"Padrão da banca" em matéria de uma prova só, sem a frase padrão** (P26); [alta] **Processual Penal partido em dois cartões**, e o de 2013 diz "Macete (IA) nenhum ainda" enquanto o de 2019 cita q55 a q59 de 2013 (P24); [média] "Pegadinha recorrente" em 12 macetes que se apoiam em 1 questão (P27); [baixa] na seção FEPESE, "170 das provas do meu cargo" contra 162 na Central (P54); [média] página-catálogo sem índice (as âncoras `#materia-N` existem, mas nada aponta para elas); [média] o formulário de banca parece filtrar a Central, mas só serve à seção de baixo, e recarrega no topo; [baixa] nota de manutenção do `config/leis.yml` no topo; "confira na fonte antes de confiar" 40 vezes; "Palavras que mais aparecem" ("agosto (5), mediante (4)") sem valor de estudo.

### 2.10 Fichas (aba do dia, todos os temas e a ficha completa)

- **Para que eu venho:** de manhã, o que ler, onde e o que memorizar antes da teoria; à noite, como a FEPESE cobrou, as pegadinhas, quantas questões e onde.
- **Está no topo?** Não. Na ficha do Art. 5º, XVII a XLIX, "O que estudar" começa na palavra 874; as pegadinhas, na 1.367; "Quantas questões fazer", na 1.942; "Meu desempenho", na 3.097. Antes vêm a legenda de 5 selos, o Resumo inteiro (614 palavras) e o "Por que agora". O botão "📋 Ficha de estudo" do Hoje abre a ficha no topo, sem âncora, e a volta ("← voltar ao dia") só existe no fim.
- **Medidas:** ficha 3.134 palavras · 12 cartões · 190 frases; aba do dia 469 palavras; todos os temas 2.862 palavras e 266 frases.
- **Problemas:**
  - [alta] **O gabarito fica à vista das questões que eu vou responder no radar** (`ficha.html:223`, `237` e `208`; o Resumo cita "2013-q1 (gabarito B)") — P05.
  - [alta] **44 enunciados de geradas e 4 comandos ocupam um terço da ficha** ("Quantas questões fazer" = 1.063 das 3.134 palavras; 754 só da lista das geradas, `ficha.html:273-275`).
  - [média] O mesmo conteúdo em quatro seções ("imprescrit" aparece 17 vezes: Resumo 7, O que estudar 5, Pegadinhas 3, Macetes 2) e o mesmo número em vários cartões.
  - [média] A ficha pede "--quantas 10" para nós que a faixa diz que não faltam (decisão 113, P34); "No radar há 6 questões reais… comece por elas" contradiz a faixa de Direito ("1º no Qconcursos").
  - [média] Código de questão ambíguo ("2024-q8" três vezes, com gabaritos B, C e B, de provas diferentes); "X de Y respostas" com dois sentidos na mesma ficha (P35); as erradas no radar contadas, mas sem lista.
  - [média] A pegadinha tirada de classificação não conferida aparece sob 🔵 (P25); "prioridade baixa, estude o básico" sob o selo azul em 12 temas, com 2 provas (P10); "13 questões · 65 provas" no complementar são 65 cadernos de 6 concursos (P29).
  - [média] Aba do dia: repete o Hoje (o único dado novo é a linha do complementar) e põe o mesmo tema em dois cartões (5 cartões para 3 temas, decisão 111); não diz se a ficha ou o resumo foram conferidos. "Todos os temas": mostra só a conferência da ficha, não a do resumo.

### 2.11 Análises › Edital (`/analises`, `foco.html`)

- **Para que eu venho:** planejar (o Ciclo 2, ou quando sair edital): o peso das matérias contra o que caiu e os assuntos que pesam mais. Não é tela do dia.
- **Está no topo?** Não: as primeiras 134 palavras (a primeira tela inteira em 1366×680) são Situação, De olho e Sinais. A tabela começa na palavra 171, o "Onde estudar primeiro" na 476 e o "Treinar" na 1.486.
- **Medidas:** 1.557 palavras · 6 cartões · 1 botão · 35 frases (~23 de método ou de sistema) · a tabela rola na horizontal em 1366 px.
- **Problemas:** [alta] **"não treinei" em Direito Penal e Constitucional**, que eu treinei (P01); [legibilidade, não é defeito] no "Onde estudar primeiro", a ordem vem de alvo + 0,25 × complementar (decisão 63), e não do número que aparece: a conta está certa (caiu na verificação, 3.6), e sobra a frase que explica, longe da barra (U45); [média] o 1º lugar é "a LEP inteira", um item só no edital (decisão 74) e sem nó nas faixas (pendência H.5); [média] Direito Processual Penal aparece como "--" em 2013 (5 questões gravadas como "Direito Processo Penal", sinônimo que a taxonomia já conhece) — P24; [baixa] "10 de 10 nas provas do cargo" esconde que é 1 prova (P42); [baixa] "Treinar: 147 de 152" contra os "162" da home (P23).

### 2.12 Análises › Minhas matérias (`/analises/materias`)

- **Para que eu venho:** por matéria, quanto fiz neste ciclo, o acerto sem consulta contra a meta e se estou melhorando (uso de sábado).
- **Está no topo?** Não. O topo é "Se a prova fosse hoje ~6 acertos de 100 · meta 79", feito com 1 das 11 matérias; das 3 matérias estudadas, LP está na palavra 155, Constitucional na 347 e Penal na 420, entre 8 cartões cinza "Ainda não estudei".
- **Medidas:** 520 palavras · 12 cartões (8 "Ainda não estudei") · 2 botões · 37 frases · 1 selo.
- **Problemas:** [alta] **o gráfico semana a semana sobe de 34% para 67% com 3 respostas**, sem o número nem a base de cada ponto (`materias.html:69-80`) — P11; [alta] **o maior número da tela é uma projeção de 1 matéria** comparada com a prova inteira (P17); [média] o % grande aparece abaixo do mínimo (Penal "55% de acerto" com 11 sem consulta; o aviso vem 4 linhas abaixo) — P31; [média] **contradiz a home e o Edital em LP** (35 respostas aqui, 15 lá — P01); [média] "medido no radar" conta respostas aqui e a última resposta nas outras telas (P20); [baixa] "quase sempre chutei" com 1 erro no caderno (P41); o treino de IA sem 🟣 (P46); [baixa] sem selo nas matérias; a lista "assuntos" mostra títulos de faixa ("Aprendizagem: Art. 5º…").

### 2.13 Análises › Meu desempenho (`/analises/desempenho`)

- **Para que eu venho:** a fila de revisão de hoje (a fila única desde a decisão 128) e a evolução por conteúdo.
- **Está no topo?** Não. As primeiras ~150 palavras são navegação, 80 palavras de regra e o filtro. A fila começa na palavra 1.167 (3º cartão) e **não tem o botão "Fazer as revisões de hoje"**, que só existe na home.
- **Medidas:** 2.278 palavras · 6 cartões · 2 botões · 138 frases · 465 palavras explicam como o sistema conta.
- **Problemas:** [alta] **"O que eu ainda não estudei" lista Direito Penal e Constitucional** sob a frase "nunca marquei faixa de estudo… e nunca respondi questão" — falso (P09); [alta] **os mesmos 16 conteúdos aparecem três vezes** ("O que eu já respondi", "Quando eu estudei e revisei", "O que voltou para revisão": 1.626 das 2.278 palavras, 71%); [alta] o anotado fica de fora sem aviso: 46 questões anotadas sem conteúdo, "anotado —" nas 16 linhas (P01); [média] a fila mostra 16 itens para 8 revisões (as pontas da decisão 128 misturadas com os nós de cima) — P19; [média] a amostra dita 3 vezes em cada linha; [média] "6 dia(s) de atraso … prazo de revisão vencido (1 dia(s))" na mesma linha; [baixa] a lista do não estudado inclui matérias fora do edital e 19 nós de Português um a um.

### 2.14 Análises › Incidência (`/analises/incidencia`)

- **Para que eu venho:** consultar o que caiu nas provas do alvo, conteúdo por conteúdo, ao lado do complementar — para priorizar o Ciclo 2 e entender o tema.
- **Está no topo?** Em parte: o primeiro dado vem na palavra 143. Mas a página abre as 13 matérias e 425 linhas (Direito Penal na palavra 5.572, LEP na 7.866). Com `?materia=` ela cai para 725 palavras — o filtro existe, o padrão é mostrar tudo.
- **Medidas:** 9.129 palavras visíveis (14.716 no HTML) · 26 dobras · 573 frases · 191 das 425 linhas (45%) com "0 questões · 0 provas" no alvo · nenhum selo 🔵.
- **Problemas:** [alta] abre tudo; [média] **a linha do nó diz "não apareceu" sem avisar a pendente do mesmo artigo** (Abolitio criminis/CP art. 2º: "0 questões · 0 provas", e a 2013-q53, pendência G, é desse artigo): pela decisão 108 a conta está certa, falta o aviso (U33); [média] **"N provas" do complementar conta cadernos**: "Conjugação de verbos irregulares: 1 questão · 26 provas" é 1 questão repetida em 26 cadernos do mesmo concurso (P29); [média] a mesma amostra duas vezes por cartão e "as duas nunca se somam" 13 vezes; [média] três colunas para um fato (alvo, "O que aconteceu", "Anos") em 191 linhas; [média] os padrões do complementar trazem pegadinhas escritas e conferidas pelo Claude Code sem 🟣 (P25); [média] "padrão identificado no acervo analisado" seguido de "Não há evidência suficiente…" na mesma linha, 10 vezes (P26); [baixa] nenhum selo azul na tela que é a estatística do acervo (P45); "20 sem classificação ainda" são 20 pendentes com motivo (P51); [baixa] a cabeça mantém "A classificação é do Claude Code e vale depois de conferida" com 162 de 162 conferidas; "questãoões".

### 2.15 Análises › Conferência (`/analises/conferencia`)

- **Para que eu venho:** manutenção (pendências B.8 e G): conferir as 75 classificações abertas do complementar e os 107 conceitos associados; mudar o nó da 2013-q53.
- **Está no topo?** Não: sem parâmetro, ela lista as 162 do alvo **já conferidas**; o primeiro item por conferir aparece na palavra 849.
- **Medidas:** 2,56 MB · 117.897 palavras (82.958 delas dentro das `<option>` dos 162 seletores "Corrigir para") · 701 botões · 594 formulários · 3.558 campos escondidos.
- **Problemas:** [alta] abre no que já está feito; [alta] **"Corrigir" e "Pendente" podem apagar o artigo da questão** (o serviço chama `classificar()` sem o dispositivo e o item do edital, que viram `None`; 157 das 170 classificações do alvo têm dispositivo; já aconteceu em 05/10 com uma do complementar — P06); [média] o peso está nos seletores; [baixa] o contador "0 de 109" conta 2 associados de anuladas que a lista não mostra, 107 (P51); a caixa "só a amostra do catálogo" não tem uso (lote refeito, decisão 87); "Confirmar" para duas ações no mesmo cartão; a proposta do Claude Code sem 🟣 (P25).

### 2.16 Concursos (Todos, Acompanhando, Calendário, Previsão)

- **Para que eu venho:** consulta, não tarefa do dia — se abriu algo que vale a pena e o prazo.
- **Está no topo?** Em parte: o primeiro concurso aparece na palavra ~40 e é o certo (São José, FEPESE, faltam 10 dias), mas o alvo e o "de olho" não aparecem na lista padrão.
- **Problemas:** [média] **"30 de 2878 concurso(s) no banco"** com o atalho "Perto 187" aceso: o denominador é o banco inteiro, a lista tem 188 (P55); [média] **nenhum dos 34 itens com marca de alvo está na lista padrão** (as Guardas de Florianópolis 2015 e BC 2014/2010, da FEPESE, ficam em "A confirmar" porque o órgão vem como "PMF"/"PMBC", e o "De olho" do Edital diz "nada no radar ainda" — P37); [média] concurso encerrado aparece como "prazo não confirmado" (13 de 19 em Estadual SC) — P56; [média] **Previsão conta seletivo e chamada pública como concurso** (10 dos 20 municípios "Em dia" não têm concurso no último ano, só seletivo ou item "desconhecido") — P57; [baixa] Previsão: 23 cartões, 12 deles iguais ("um único concurso conhecido (2026)"); [baixa] Calendário: instrução de uso antes dos 2 compromissos, e o salário sem a origem (P48); Acompanhando: metade do texto explica o sistema, e a mesma marca tem cinco nomes (Acompanhando, Meu mural, Fixar no mural, estrela, favorito).

### 2.17 Mais (`/mais`) e Auditoria (`/auditoria`)

- **Para que eu venho:** consulta: o que é cada selo, de onde vem o dado, se o backup rodou.
- **Está no topo?** Sim (a legenda dos 8 selos entre as palavras 20 e 59).
- **Problemas:** [baixa] texto de funcionamento do backup e da configuração à vista; "Concursos coletados" conta seletivos (1.707 seletivos, 1.045 concursos e 126 "desconhecido" no banco); "24 itens" de leis por conferir aqui, "15 itens" no CLAUDE.md e na especificação (são 15 mudanças + 9 de fronteira); a Auditoria é Markdown cru num `<pre>`, e a última seção dela diz o contrário da Mais sobre o aviso de lei.

### 2.18 Coerência entre as telas

- **Nomes.** "Revisar" serve a quatro coisas diferentes: a fila 1-7-30 por conteúdo ("8 conteúdo(s) para revisar hoje", `home.html:198`), o caderno ("2 erros para rever hoje", `hoje.html:687`), o R+7/R+30 do plano e as questões erradas, que têm quatro rótulos ("Revisar agora", "Refazer os 11 erro(s)", "Refazer as erradas", "Revisar meus erros": `home.html:228`, `simulado.html:100`, `desempenho.html:253`, `relatorio.html:192`). "Treino" é questão real na home e no Edital ("Começar treino", "Treinar") e é IA no resto ("Treino de IA"). "Radar" quer dizer questão real em "Começar pelas 6 do radar" (`hoje.html:1080`) e IA em "Treinar no radar" (`hoje.html:1125`), na mesma faixa. Numa faixa do Hoje, o mesmo nó é chamado de tema, de assunto e de nó; "bloco" tem três sentidos (Manhã/Noite, a próxima faixa, alvo × complementar). O alvo aparece como "Policia Penal SC" (lido do `alvo.yml`) e como "Polícia Penal SC" escrito à mão em 13 linhas de template. (U53)
- **Componentes.** Os 25 templates de página têm `<style>` próprio — 1.438 linhas, contra 499 do `design.css` —, e o `hoje.html` sozinho tem 132 classes próprias; há 62 `style=` inline (35 de margem fixa). A barra de progresso tem 10 definições com 5 nomes, e a pílula, umas 18. A frase "Não há evidência suficiente no acervo para afirmar isso." sai com 5 desenhos; no Hoje, com uma classe (`.nao-sei`) cujo CSS a página não tem. O selo de origem vira etiqueta de estado: na Conferência, 162 "✓ conferida" e 107 "🟣 por conferir" em `ds-selo` sem origem (`conferencia.html:129-131`, `209-210`); na lista do ciclo das Fichas, 253 emojis de selo soltos e nenhum `ds-selo`. O selo curto (só o emoji) aparece 23 vezes no Hoje sem a legenda que o justifica. (U54, U64)
- **Botões.** A mesma ação tem rótulos e estilos diferentes: "Começar treino · 20 questões" (home) × "Treinar 20 questões" (Edital); "📓 Anotar erro" × "📓 anotar os erros"; três rótulos para criar a rodada da faixa e dois para abrir a que já existe; "📋 Ficha de estudo" × "Ficha completa"; quatro formas de "ler a lei"; sete formas de "voltar", quase todas no rodapé. (U52)
- **Navegação.** O Caderno de erros está em dois menus, e o clique pelo Hoje troca de seção (a aba acesa vira "Revisão"); os Macetes não têm as sub-abas de Revisão; "Estudar", "Revisão" e "/foco" passam por redirecionamento; a marca "Radar" e a aba "Meu foco" levam ao mesmo lugar; o link "os macetes da banca →" da home cai no Caderno de erros. (U59)

## 3. Precisão (vem primeiro na prioridade)

São **57 problemas**, cada um conferido por um verificador independente na cópia do banco (o P12 é a exceção, dita no item). A prioridade segue uma régua só: **CRÍTICA** = eu estudo a coisa errada, ou o dado se perde ou se contamina; **ALTA** = número errado ou enganoso numa tela do dia; **MÉDIA** = enganoso em tela de consulta, ou latente; **BAIXA** = forma. Onde a prioridade daqui ficou acima da gravidade que o verificador deu, isso está escrito no item ("verificador: média"); a escala do verificador ia só até "alta", e os críticos que ele deu como alta (P01, P02, P04, P05) não levam nota.

### 3.1 O que só você pode confirmar

Três números dependem de um fato que o banco não guarda:

1. **29/09 (P02):** a faixa "Artigo, numeral e pronome" foi anotada 10/2, e a rodada 4 do radar, no mesmo dia, teve 10 questões reais de Português com 2 acertos (18:22–18:29); o erro do caderno criado às 18:34 tem fonte "radar". **Você fez outras 10 no Qconcursos nesse dia?** Se não, o 29/09 está contado duas vezes.
2. **28/09 (P08):** a faixa "Substantivo e adjetivo" foi anotada 10/7, e a rodada 2 do mesmo dia teve 10 **geradas** sobre o mesmo tema, com 7 acertos (19:16–19:21). A decisão 3 da Etapa 0 diz que foram do Qconcursos. **As 10 de 28/09 foram do Qconcursos ou são as geradas?** Se forem as geradas, 7 acertos de IA estão contando como acerto real.
3. **Qual regra vale para o "anotado" sem conteúdo (P01):** contar pela matéria (como Minhas matérias) ou ficar fora (como a home e o Meu desempenho).

Até a correção, quatro cuidados de uso evitam gravar número errado:
- **Na faixa R+7 de hoje (18:00):** anote no "fiz" só as 7 de Direito Constitucional; as 3 de Português vão como estudo extra de LP (P04).
- **Nas faixas "Comece pelas N do radar" e nas rodadas de sábado:** apague o número que vem no "fiz" e anote só o que fez no Qconcursos (P03).
- **Na Conferência:** use "Confirmar"; não use "Corrigir" sem trocar o nó, nem "Pendente" (P06).
- **Até 07/11:** evite "Começar treino · 20 questões" e "Treinar 20 questões" (P12).

### 3.2 Críticos

**P01 · O "anotado" tem duas regras, e Português e Penal mudam de tela para tela** — CRÍTICA · M
- *Evidência:* as faixas de 28 e 29/09 não têm `conteudo` (LP 10/7 e 10/2, Penal 11/6, Constitucional 15 com consulta). A home, o Edital e o Meu desempenho descartam essas linhas (`desempenho_por_conteudo.py:307` e `485`); Minhas matérias e a comparação de 07/11 somam pela matéria da linha (`materias.py:260-280`, `sabado.py:378-385`). Resultado: LP é "Amostra insuficiente (15 de 20)" na home, no Edital e no Meu desempenho, e "sem consulta: 37% em 35", sem aviso e na projeção, em Minhas matérias; o Edital diz "não treinei" para Penal (11 anotadas, 6 acertos) e Constitucional (15 questões, 2h10).
- *Impacto:* a home ordena "O que estudar agora" com LP como não treinada, e eu não sei se LP já tem base: o estado da amostra é o oposto em telas vizinhas.
- *Correção:* uma regra só. A linha sem `conteudo` conta no nó da **matéria** (a faixa sabe a matéria) para acerto e amostra; assunto e subassunto ficam como estão; "não treinei" vira "sem acerto medido". **Muda a decisão 81** (só no nível da matéria). Alternativa sem mudar decisão: Minhas matérias e a comparação deixam de contar essas linhas e mostram "N anotadas sem conteúdo, fora do acerto". Fazer junto com o U01/P15: com LP corrigida, duas matérias do Ciclo 2 subiriam para o top 3 da home.

**P02 · 29/09: a faixa de Português e a rodada do radar contaram as mesmas 10 questões, e nada acusa** — CRÍTICA · P
- *Evidência:* ver 3.1. Hoje: "Fiz hoje: 37 questões = 4 acertos + 18 erros + 15 sem acerto anotado"; Semana 1: 68 questões, 40%; LP: 37% em 35. Sem a faixa (recalculado pelo `metricas`): 29/09 = 27; Semana 1 = 58 e 45%; LP sem consulta 11 de 25 (44%); a base de LP da comparação de 07/11 passaria a "11 de 25 · 44%". O aviso da decisão 130 não pega (a rodada 4 não guarda a faixa) e o `conferir-dias` não cruza faixa com rodada do mesmo dia. As duas auditorias anteriores deram o 37 como certo.
- *Impacto:* o acerto de LP, a semana 1, a projeção e a base de 07/11 — que decide o Ciclo 2 — partem de um número inflado. É o mesmo defeito que a decisão 127 corrigiu no 05/10.
- *Correção:* com a sua confirmação, corrigir o 29/09 como o 05/10 (desmarcar a faixa; o tempo vira estudo extra "Onde: Radar"). No código, o `conferir-dias` passa a acusar faixa de questões e rodada do radar da mesma matéria, no mesmo dia, com os mesmos números (só lê, como manda a 1D).

**P03 · O "fiz" da faixa feita no radar vem com o número do plano e, depois de responder, recusa 0** — CRÍTICA · M (verificador: alta)
- *Evidência:* o campo vem com o total do plano até haver resposta no radar ligada à faixa (`hoje.html:1263-1264`): hoje, 6 na Fixação das 12:15 (as 6 são do radar; o certo seria 0) e 10 na faixa das 19:15 (7 do radar + 3 do Qconcursos); nos sábados, 20 em cada diagnóstico, 40 no R+7 de 17/10 e 50 no fechamento. Depois de responder, o campo vem vazio e o 0 é recusado ("Faixa de questões com 0 questões não conta como feita", `servico/cronograma.py:362-369`); a faixa feita toda no radar não fecha, e a sugestão do dia nunca chega a Ideal. *Atenuante:* a faixa já diz "As do radar contam sozinhas…: anote só as do Qconcursos"; as 3 faixas de 05/10 estão desmarcadas e só voltam a contar em dobro com um novo clique em "Fiz".
- *Impacto:* um clique em "Fiz" antes de responder grava o plano por cima das respostas (o 05/10 e o 29/09 foram isso). Sem o clique, a faixa feita some do dia, e no sábado as faixas que medem nunca ficam feitas.
- *Correção:* faixa com rodada do radar abre com o "fiz" vazio e o rótulo "fiz no Qconcursos"; com a rodada respondida, a faixa conta como feita (grava só os minutos). Estende a decisão 130 e **muda a regra 1 da Etapa 1D** só para faixa com rodada respondida. Precisa de teste que garanta 0 questões gravadas.

**P04 · O R+7 e o R+30 com "+ 3 de Português" gravam as 10 questões na matéria de Direito** — CRÍTICA · M
- *Evidência:* R+7 de hoje (18:00): matéria Direito Constitucional, 10 questões; "7 questões NOVAS de Direito Constitucional … + 3 de Português" só no "ver detalhe" fechado (`config/cronograma.yml:907-916`; `app.py:222`). O "fiz" grava `materia: faixa.materia`. São 34 faixas assim no Ciclo 1 (R+7 25, R+30 9), 33 delas de hoje em diante.
- *Impacto:* a partir de hoje à noite, cada R+7/R+30 põe 3 questões de Português no acerto de Direito e tira de LP; a comparação de 07/11 fica misturada.
- *Correção:* as 3 de Português viram linha própria do plano nessas faixas, de 07/10 em diante (dias passados intactos, com a sua aprovação), e a divisão aparece à vista (U09). Não usar `materias_mistas`: tiraria as 7 de Direito de toda matéria.

**P05 · A ficha e o resumo mostram o gabarito das questões que a faixa manda responder no radar, sem consulta** — CRÍTICA · M
- *Evidência:* as 13 questões que o radar planeja para a Concordância verbal hoje (6 de manhã, 7 à noite) estão entre as 14 questões reais da ficha do tema, com "· gabarito X" na linha visível e a certa em negrito com ✓ (`ficha.html:208`, `223`, `237`); o Resumo cita 2013-q1 (B), FEPESE-2024-q5 (A), q6 (A), q10 (C) e 2016-q7 (B), todas da faixa, e a janela do resumo está no próprio HTML do Hoje.
- *Impacto:* de manhã eu leio a ficha com os gabaritos e depois respondo as mesmas 13 "sem consulta": o acerto que entra no desempenho por tema e no 1-7-30 mede a memória do gabarito.
- *Correção:* questão real ainda não respondida no radar aparece sem o gabarito na ficha e no resumo (a letra fica no dado e aparece depois de responder). **Muda as decisões 109 e 118** (o resumo cita "gabarito X", que o `fichas.conferir_resumo` confere na importação; sem a letra no texto, a conferência passa a ler o gabarito pela questão citada). Até lá: responder as do radar antes de abrir a ficha do tema.

**P06 · Conferência: "Corrigir" sem trocar o nó e "Pendente" apagam o artigo e o item do edital da classificação** — CRÍTICA · P (verificador: média)
- *Evidência:* o seletor "Corrigir para" já vem marcado no nó atual (`conferencia.html:183`); `conferir()` chama `classificar()` sem `dispositivo` nem `item_do_edital`, e `classificar()` grava os dois como vazios — no mesmo nó, sobrescreve a própria linha (`servico/classificacoes.py:523-533` e `123-132`; conferido também por mim no código). **Já aconteceu em 05/10** no complementar: a chave `ae5ac356…` (2013 q2) tinha dispositivo e item do edital no commit `1bc222e` e ficou sem os dois no `45b023c`. No alvo, 157 das 170 classificações principais têm dispositivo, e é o dispositivo que leva a pendente ao tema no "caiu ou não caiu" (decisão 108). O valor antigo continua no histórico do git do `data/classificacoes.json`.
- *Impacto:* a conferência é trabalho que está comigo agora (pendência B.8). Cada clique desses apaga o artigo; nas pendentes do alvo, o tema deixa de "cair" na ficha e na faixa.
- *Correção:* "Corrigir" para o mesmo nó vira confirmar; "Corrigir" para outro nó e "Pendente" copiam o dispositivo e o item do edital; um teste que confere e relê o dispositivo. Decidir se a chave `ae5ac356…` volta ao valor do `1bc222e`.

**P07 · O fechamento de 07/11 repete as 8 questões de Raciocínio Lógico do diagnóstico de 10/10** — CRÍTICA · M (verificador: média)
- *Evidência:* simulação só de leitura da composição (com os 40 do diagnóstico como respondidos): o fechamento pede 8 de RL em 6 assuntos de estoque mínimo, que o diagnóstico já esgota, e repete as 8 (e 1 de LP); Contagem (30 questões) e Conjuntos (11) ficam com 0. O R+7 de 17/10 refaz os erros dessas mesmas questões (`servico/composicao.py:414-454`).
- *Impacto:* a linha de RL da comparação que decide o Ciclo 2 mede memória; uma melhora de RL pode ser falsa. (Atenuante: a linha já sai "Amostra insuficiente", 8 < 20.)
- *Correção:* nas rodadas que medem, contar como estoque só a questão que nenhuma rodada que mede do ciclo usou; a cota que faltar vai para os assuntos com estoque. **Muda a decisão 67** no que conta como falta de estoque. Precisa estar pronto antes de 07/11.

**P08 · 28/09: as 10 anotadas de Português podem ser as 10 geradas da rodada 2** — CRÍTICA · P · **INCERTO** (verificador: média)
- *Evidência e decisão:* ver 3.1. Se forem as geradas, sem as duas faixas de LP (28 e 29/09) LP fica com 15 respostas sem consulta (27%), em "Amostra insuficiente", e sai da projeção — o que a home já mostra.
- *Correção:* se forem as geradas, corrigir como o 05/10, com a sua aprovação (**muda a decisão 3 da Etapa 0**). O cruzamento do P02 no `conferir-dias` também pegaria este caso.

### 3.3 Altos

**P09 · Penal e Constitucional fora da árvore: "nunca estudei", fila de revisão só de Português, e o erro de Constitucional vencido some** — ALTA · M (verificador: média na parte da revisão; alta na parte do "não estudei")
- *Evidência:* das 14 faixas feitas no ciclo, 13 não têm `conteudo` nem `nos`, e nenhuma das 65 fichas foi conferida; só 16 nós estão "estudados ou praticados", todos de Português. O Meu desempenho lista Direito Penal e Constitucional sob "Nó em que eu nunca marquei faixa de estudo nem anotei teoria ou lei seca, e em que nunca respondi questão" (`desempenho.html:226-227`) — falso: houve teoria, lei seca e questões das duas. A fila tem 8 pontas, todas de LP; o R+7 de "Aplicação da lei penal" de 05/10 não conta como revisão; o erro de Constitucional do caderno, vencido desde 30/09, fica fora da fila (`estudo.py:439-440`).
- *Impacto:* o 1-7-30 de Penal e Constitucional não anda, e a tela afirma como fato que eu nunca estudei o que estudei.
- *Correção:* sem mudar decisão — a frase passa a "… ou cuja faixa ainda não tem nó conferido", a home avisa "Penal e Constitucional entram depois de conferir as fichas", e o erro do caderno ligado à matéria entra na fila. Conferir as 5 fichas dos temas já estudados liga 9 faixas feitas (ideia I5). Para a faixa contar sem ficha conferida: o mesmo ajuste do P01 (**muda a decisão 81** no nível da matéria).

**P10 · O "caiu ou não caiu" afirma mais do que a base** — ALTA · P (verificador: média)
- *Evidência:* (1) a faixa do Hoje mostra só a frase, sem as notas que a ficha mostra: "R+7: Aplicação da lei penal" (05/10) diz "Caiu em 2013 e 2019: 4 questões · 2 provas", e as 4 são pendentes; "Trabalho do preso" (07/10) diz "Não apareceu na prova de 2019, a única que cobrava a matéria." sem "Base de uma prova só… Não há evidência suficiente no acervo para afirmar isso." (que só está na janela escondida) — `hoje.html:947`. (2) Tema que não caiu em 2013 nem em 2019 ganha, sob o selo azul, "prioridade baixa, estude o básico." — 12 temas, inclusive crase, que o complementar mostra em 9 questões · 62 provas (`incidencia.py:642-646`); é conclusão de 2 provas sem "base pequena" (`amostra.yml`: 3 provas para tendência).
- *Impacto:* eu posso estudar raso o que cai.
- *Correção:* a faixa mostra as notas do "caiu" num chip; a linha azul fica só com o histórico ("Não apareceu nas provas de 2013 e 2019 · base pequena: 2 provas") e a prioridade fica no "Por que agora" (amarelo). **Muda a decisão 108** só no texto da frase.

**P11 · "Estou evoluindo?" respondido com 3 respostas** — ALTA · P
- *Evidência:* Semanas, semana 2 (em andamento, só 05/10): "67% ↑ +27% de acerto" e "1 ↓ −25 erros", as duas em verde, com 2 acertos e 1 erro; `_comparar` não tem mínimo nem olha "em andamento" (`servico/semanas.py:196-219`). Minhas matérias: a linha de LP sobe de 34% (em 32) para 67% (em 3), sem nenhum n na tela (`materias.html:69-81`). Para a mesma pergunta, a home diz "Responda mais 5 para eu medir sua evolução" (mínimo 20) e o Meu desempenho pinta de cinza "semana 2: 67% em 3".
- *Impacto:* duas telas dizem "melhorou +27" com 3 questões; eu posso tirar tempo de LP.
- *Correção:* seta só entre semanas fechadas com o mínimo `desempenho.evolucao` (20) de cada lado; abaixo, "67% em 3" sem seta; no gráfico, o n de cada ponto e o ponto abaixo do mínimo em cinza (só CSS). Não contradiz decisão (a das Semanas não define mínimo).

**P12 · "Começar treino" da home gasta as questões que as rodadas que medem vão usar** — ALTA · M · *medido, sem verificador independente*
- *Evidência:* o botão sorteia 20 entre as 162 do alvo, de todas as matérias, inéditas primeiro (`app.py:1657-1671` → `servico/simulado.py:238-280`); o diagnóstico e o fechamento também preferem a inédita do alvo. Na simulação só de leitura (300 sorteios, feita na consolidação, sem verificador independente): com 1 rodada de treino antes de 10/10, o diagnóstico de LP cai de 17 para 15,0 questões do alvo e o de RL de 8 para 7,5, e o fechamento passa de 1 para ~2,6 questões já vistas em média (máx. 7); com 3 rodadas, ~5,9 (máx. 10). Confirmado por verificador só o pedaço de 03/10 (gravidade baixa): os botões "Criar a rodada" dos diagnósticos que passaram para 10/10 seguem ativos em 03/10, e a rodada criada ali ficaria fora do R+7 e da comparação.
- *Impacto:* o caminho de 2 cliques da home tira questões inéditas da comparação 10/10 × 07/11.
- *Correção:* o botão sai da home (U01; já existe no Edital), e o "Treinar 20 questões" do Edital deixa de sortear as questões que as rodadas que medem vão usar (a composição é determinística pela semente), ou sorteia só do complementar aceito; em dia passado, a faixa que mede não oferece "Criar a rodada".

**P13 · "Começar" do Simulado sorteia da IESES e de provas recusadas** — ALTA · P (verificador: média)
- *Evidência:* `_sortear_questoes` filtra matéria, cargo e banca, sem filtro de evidência (`servico/simulado.py:83-150`): no sorteio padrão, 600 de 3.711 candidatas (16%) são de outra banca e 54 de provas recusadas; em LP, 1.482 do complementar aceito, 252 da IESES e 24 de provas recusadas. A resposta entraria no acerto por matéria que ordena a home e o Edital. Hoje as 15 respostas reais são do alvo (5) e do complementar aceito (10): é risco, não número errado hoje.
- *Correção:* o "Começar" sai (U16) ou sorteia como o compilado (alvo + complementar aceito). Cumpre a decisão 75 e a regra do CLAUDE.md.

**P14 · A Reduzida e o Plano B de sábado tiram do dia as faixas que medem, sem avisar** — ALTA · P (verificador: média)
- *Evidência:* "reduzida: Faça só o simulado da noite." (`cronograma.yml:1328`, `2015`, `4142`): em 10/10 saem os dois diagnósticos; em 17/10, o R+7 deles. O Plano B de sábado troca o dia por "Refazer as questões erradas da semana" no Qconcursos (`radar/cronograma.py:912-921`). E a mesma tela tem três definições de Reduzida.
- *Impacto:* num sábado apertado (10/10 tem 70 questões), a Reduzida apaga a linha de base de 07/11.
- *Correção:* em sábado que mede, Reduzida e Plano B mantêm as faixas que medem ("Reduzida: os dois diagnósticos no radar; o simulado da semana fica de fora"); uma definição só de Reduzida. Antes de 10/10.

**P15 · O 3º lugar de "O que estudar agora" sai de um empate de 5, desempatado pelo nome, e é matéria do Ciclo 2** — ALTA · P (verificador: média)
- *Evidência:* DH 15,0 e LP 15,0; Legislação Especial, Legislação Estadual, LEP, Raciocínio Lógico e Sociologia empatam em 10,0, e o desempate pelo nome põe Legislação Especial (Ciclo 2) em 3º (`servico/inicio.py:159-177`).
- *Correção:* o bloco sai da home (U01). Se ficar, só matéria do ciclo atual e o empate escrito.

### 3.4 Médios e baixos

| # | Problema | Telas | Evidência | Correção | Esf. | Prior. |
|---|---|---|---|---|---|---|
| P16 | "1h55 de estudo" é só a manhã | Hoje | O dia tem 3h50 (115 + 115 min); as 49 questões são do dia inteiro (`radar/cronograma.py:268-269`) | "3h50 de estudo", ou "de manhã" | P | MÉDIA |
| P17 | "Se a prova fosse hoje ~6 acertos de 100 · meta 79" projeta só Português | Minhas matérias | 37% × 15 = 5,55; o 100 e a meta 79 são da prova inteira; a amostra (35 respostas, 1 matéria) não aparece (`servico/materias.py:387-405`; `materias.html:104-121`) | "~6 de 15 (só LP, 35 respostas) · meta 12", ou "Amostra insuficiente em 10 de 11 matérias" | P | MÉDIA |
| P18 | Simulado e relatório julgam o acerto sem o mínimo | Simulado, Gerar questões, relatório | LP "27% · 15" em vermelho por um 60 escrito no template e "é onde vale gastar tempo"; relatório verde com 3 questões (`simulado.html:204-214`, `relatorio.html:75`) | Estado de amostra ao lado; cor e recomendação só com amostra; o 60 lido do `amostra.yml` | P | MÉDIA |
| P19 | A home chama de "a mesma fila" 8 de 16 itens | Meu foco, Meu desempenho | 8 pontas espalhadas entre 16 linhas, sem contagem; a errada 8057, ligada só à matéria, nunca entra na rodada das pontas (`servico/estudo.py:479-489`; `home.html:195-199`) | O Meu desempenho abre pelas 8 pontas (U11); a errada ligada só à matéria entra na rodada | P | MÉDIA |
| P20 | "Medido no radar" soma respostas em Minhas matérias e conta a última resposta no resto | Minhas matérias × Meu desempenho, Simulado, Edital, home | Hoje coincide (15 questões, 15 respostas); refazendo as 11 erradas e acertando 6: 67% numa tela e 38% na outra, com o mesmo rótulo | O rótulo diz o recorte ("em 15 respostas" × "em 15 questões, pela última resposta"), como pede a decisão 1C.5 | P | MÉDIA |
| P21 | O artigo da questão gerada, mostrado antes do enunciado, entrega a resposta | Rodada (gerada) | Ex.: gerada 778 "(Serão contratados novos agentes → Contratar-s" (correta e); 62 das 801 com indício pela busca; hoje o "Nas geradas" de LP não está inflado (sem elas, 73%) | O artigo só depois de responder (U17) | P | MÉDIA |
| P22 | O artigo da gerada é cortado em 200 caracteres na gravação | Relatório, questão gerada | 57 das 811 geradas com 200 caracteres exatos (56 de LP) (`gerador.py:329`; `models.py:458`) | Tirar o corte; campo `Text` (passo novo no `migracoes.py`); reimportar se os lotes guardarem o texto | P | MÉDIA |
| P23 | Estoque do alvo: "162 questões" na home e "147 de 152" no Treinar | Meu foco, Edital | 162 válidas, 152 enunciados distintos: 16 questões com o mesmo comando e alternativas diferentes contam como 6, e 10 nunca saem como novas (`foco.py:800-811`; `servico/simulado.py:186-202`; `home.html:140-141`; `foco.html:619-623`) | Sortear e contar pela chave ("157 de 162"); a home diz "162 válidas (sem as 8 anuladas)" | M | MÉDIA |
| P24 | "Direito Processo Penal" × "Direito Processual Penal" | Edital, Simulado, Gerar questões, Macetes | Edital: Processual Penal "--" em 2013 (caíram 5); Gerar oferece uma opção que não gera nada; o cartão de 2013 dos Macetes diz "nenhum macete" | Agrupar pelo nome do edital (cumpre a decisão 97) no Edital, no Simulado e em Gerar; nos Macetes, juntar os dois cartões **muda a decisão da Central de Macetes** (25/09) | P | MÉDIA |
| P25 | Pegadinha e tipo escritos pelo Claude Code sob o selo azul, ou sem o roxo | Ficha, Incidência, Conferência | Ficha: 2 pegadinhas de "classificação não conferida" sob 🔵; Incidência: padrões do complementar de 40 conferidas, 39 delas pelo próprio Claude Code, sem dizer | Não conferida sai da lista ou leva 🟣; "conferido pelo Claude Code" escrito (decisão 104); proposta da Conferência com 🟣. **Muda a decisão 109** para as não conferidas | P | MÉDIA |
| P26 | Padrão de cobrança abaixo do mínimo | Macetes, Incidência | Macetes: "Padrão da banca 4 de 9" em matéria de uma prova só, sem a frase padrão; Incidência: "padrão identificado…" seguido de "Não há evidência suficiente…" (10 vezes) | Os Macetes deixam de mostrar o padrão e apontam para a Incidência (U19); na Incidência, abaixo do mínimo, o rótulo vira "amostra: …" (`incidencia.py:351-353`) | P | MÉDIA |
| P27 | "Pegadinha recorrente" em macete que se apoia em 1 questão | Macetes | 12 dos 40 macetes com "(1)" questão relacionada (`macetes.html:166`; `servico/cartoes.py:163`) | Rótulo "Pegadinha" e "(N questões · M provas)"; muda o formato do cartão da especificação | M | MÉDIA |
| P28 | Os Macetes contam "quanto cai" por outra base que a Incidência | Macetes × Incidência | Crase: 11 perguntas diferentes em 43 cadernos (catálogo) × 24 questões · 98 provas (árvore); LP 23 × 22, Penal 13 × 9 (`macetes.py:396-435`; `servico/cartoes.py:91-107`; `incidencia.py:161-191`) | Ler a árvore com as contas da Incidência (U50); até lá, dizer a base | M | MÉDIA |
| P29 | "M provas" do complementar conta cadernos | Incidência, Fichas, ficha, resumo | "1 questão · 26 provas" = 1 questão em 26 cadernos do mesmo concurso; Concordância 1: "65 provas" de 6 concursos; o mínimo dos padrões passa com 1 concurso (`incidencia.py:295`; `servico/complementar.py:391`) | Contar por concurso (ano e município) e usar no mínimo. **Muda a decisão 14 da 3B** | M | MÉDIA |
| P30 | A comparação de 07/11 "decide o Ciclo 2" sem amostra no fechamento e sem os simulados do Qconcursos | Hoje 07/11 | Fechamento: todas as matérias abaixo de 20; diagnóstico só em RL e LP; o "Acumulado do ciclo" deixa fora até 145 questões dos simulados de sábado (faixas sem matéria) | Plano e tela dizem o mesmo: decide o acumulado do ciclo, com o fechamento ao lado; dizer que os simulados ficam fora (repartir por matéria **muda a E2**) | P | MÉDIA |
| P31 | Minhas matérias destaca "55% de acerto" de Penal com 11 respostas | Minhas matérias | O % grande sai igual ao de LP; o aviso vem 4 linhas abaixo; a divisão radar/anotado não aparece, contra a decisão 7 da Etapa 0 (`materias.html:150-153`) | "Amostra insuficiente (11 de 20)" no lugar do % grande; divisão sempre | P | MÉDIA |
| P32 | "Refazer os 11 erro(s)" monta uma rodada de 10 | Simulado, home, relatório, Meu desempenho | `criar_simulado_de_erros()` sem quantidade; padrão 10 (`servico/simulado.py:68`, `535`) | Passar a quantidade, ou "refazer 10 dos 11" | P | MÉDIA |
| P33 | Faixa com consulta diz "1º No Qconcursos (são as que medem)" | Hoje | Fixação e Aprendizagem com consulta; o detalhe diz "fixam, não medem" (`hoje.html:1105`; `cronograma.yml:873-875`) | "(com a lei aberta)" nas com consulta (U08) | P | MÉDIA |
| P34 | A ficha manda gerar 10 por nó; a faixa, para os mesmos nós, não pede nenhuma | Ficha × Hoje | 4 comandos "--quantas 10" no Art. 5º, que já tem 11 geradas por nó; a faixa pede 0 (decisão 113) | A ficha usa o N da faixa e não mostra comando para nó com o bastante (U43) | P | MÉDIA |
| P35 | "X de Y respostas sem consulta" com dois sentidos na mesma ficha | Ficha | "1 de 6" (respostas sobre o mínimo) × "0 de 1" (acertos sobre respostas) (`prioridade.py:207-210`; `amostra.py:171-174`) | "1 resposta sem consulta; o mínimo é 6" | P | MÉDIA |
| P36 | O R+7 dos diagnósticos (17/10) manda anotar até 40 erros na "matéria" Diagnósticos | Hoje 17/10 → Anotar erro | O link preenche `materia=Diagnósticos`, sem nó; o caderno e Minhas matérias não a acham (`app.py:246-257`; `servico/erros.py:300-303`) | Faixa mista não preenche a matéria; a rodada dá matéria e nó de cada erro (U21) | P | MÉDIA |
| P37 | "De olho" diz "nada no radar" para as Guardas de Florianópolis e de Balneário Camboriú | Edital, Concursos | Há 3 edições FEPESE no banco (2015 "PMF", 2014 e 2010 "PMBC"), sem município (`foco.py:296-339`; `alvo.py:387-402`) | Traduzir as siglas das prefeituras por configuração (`config/regioes.yml`), nunca no código | P | MÉDIA |
| P38 | Semanas: "−290" sem unidade ao lado de horas, e "+27%" onde são pontos | Semanas | 6h50 − 2h = 290 min (`servico/semanas.py:197-217`; `semanas.html:93-98`) | "−4h50" e "+27 pontos" | P | BAIXA |
| P39 | Réguas, contas e frases escritas à mão nos templates | home, relatório, Macetes | "20 respostas" e "60%" fixos na home; "< 20" no relatório; "25% das provas" calculado em `macetes.html:319`; o teste só procura + e − (resto do R-1C-2 da auditoria independente, que a decisão 128 fechou só em parte) | Ler do `amostra.yml`; a porcentagem vem pronta do Python; o teste olha também / e * | P | BAIXA |
| P40 | A meta 79 sai de dois campos | Hoje × Minhas matérias | `meta_da_prova.acertos` × soma das metas por matéria, hoje iguais (`hoje.html:556`; `radar/cronograma.py:377-380`; `servico/materias.py:394`) | O Hoje usa a soma | P | BAIXA |
| P41 | "quase sempre `<motivo>`" com 1 erro no caderno | Minhas matérias | O caderno tem 2 erros; o próprio caderno só mostra motivo com 3 ou mais, decisão E1 (`servico/materias.py:340-349`; `servico/erros.py:69-78`) | Usar a conta do `servico/erros.py` | P | BAIXA |
| P42 | Edital: "10 de 10 nas provas do cargo" esconde que é 1 prova | Edital | LEP e Estatuto do Desarmamento só caíram em 2019 (`foco.html:426-429`, `451`, `465`) | "10 de 10 em 1 prova (2019)" | P | BAIXA |
| P43 | Rodada só de geradas diz que "a correta" sai "do gabarito" | Relatório de IA | Frase fixa em `relatorio.html:108-111` | A frase só em rodada com questão real (U36) | P | BAIXA |
| P44 | Texto de IA sem o modelo e a data que estão gravados | Macetes, fichas, relatório de IA | Aviso de lei: só "Escrito por IA, por conferir" (24 itens com procedência no `leis.yml`); relatório de IA: 0 menções de modelo | A procedência no `title` do selo roxo; o modelo no relatório | P | BAIXA |
| P45 | A Incidência não tem nenhum selo azul | Incidência, home | 13 selos na tela, todos roxos; a amostra está em toda linha (`incidencia.html:66-93`; `home.html:138-144`) | Selo azul no cabeçalho de cada matéria, pela origem gravada no dado | P | BAIXA |
| P46 | Treino de IA sem o selo roxo e sem "conta no volume" | Minhas matérias, Semanas | No Hoje a frase tem 🟣 e "; conta no volume" (decisão 127); `frase_da_ia` não tem | Pôr o sufixo na função e o selo nos dois templates | P | BAIXA |
| P47 | Os artigos-chave da semana sob o selo amarelo; na ficha, "seleção do plano" | Hoje (sábados) × ficha | `RevisaoDaSemana.origem = AUTOMATICO` (`servico/sabado.py:59`; `hoje.html:1149`) | Selo do plano no item (3) | P | BAIXA |
| P48 | Calendário: o salário sem a origem | Calendário × Concursos | "Salário: R$ 4.000." (lido do anúncio) e "R$ 4.500." (anotado por mim) iguais; vai também para o `.ics` (`servico/__init__.py:930-931`; `calendario.html:67-71`) | "(lido do anúncio)" / "(anotado por mim)" no serviço | P | BAIXA |
| P49 | O aviso "já contam no Fiz hoje" soma respostas de outro dia | Hoje | Caso de borda montado no teste; não aconteceu no dado | O aviso conta as do dia da faixa e diz as outras com a data | P | BAIXA |
| P50 | "estudado em DD/MM" na composição do simulado é a data do plano | Hoje 10/10 e 17/10 | Há datas futuras ("09/10") e temas que Minhas matérias diz "Ainda não estudei" (`composicao.py:572`) | "no plano em DD/MM · não marcado" (ver ideia I2) | P | BAIXA |
| P51 | Contadores do que falta conferir não batem com a lista | Incidência, Conferência | "20 sem classificação" são 20 pendentes com motivo; "0 de 109 associados" com 107 na lista, 2 de anuladas (`incidencia.py:296`; `servico/classificacoes.py:757-766`) | "20 pendentes (com motivo)"; o contador conta o que a lista mostra | P | BAIXA |
| P52 | "São 8.462 questões no acervo … com o gabarito que a banca publicou", sob o selo azul | Simulado | 8.462 = alvo + aceito + recusado (360) + outra banca (907); 3.776 enunciados | Contar só alvo + complementar aceito, por enunciado (U16) | P | BAIXA |
| P53 | "Gerar e treinar" geraria a matéria inteira mesmo com assunto escolhido | Gerar questões | O POST só lê matéria e quantidade (`app.py:915-926`); latente (não há chave) | O cartão da API sai (U51; decisão 114) | P | BAIXA |
| P54 | Macetes da FEPESE: "Ficaram fora desta conta 170 das provas do meu cargo", mas a Central mostra 162 | Macetes | 170 são questões, não provas; 8 anuladas (`macetes.html:284`; `servico/provas.py:782-791`) | "170 questões (162 na Central; 8 anuladas)" | P | BAIXA |
| P55 | "30 de 2878 concurso(s) no banco" com o filtro Perto aceso | Concursos | A lista filtrada tem 188 (`index.html:561`; `app.py:469`) | "30 de 188 (Perto + 1 favorito)" | P | BAIXA |
| P56 | Concursos encerrados aparecem como "prazo não confirmado" | Concursos (Estadual SC) | 13 de 19, de 2006 a 2022, acima dos encerrados recentes (`index.html:330-332`; `servico/__init__.py:290-297`) | Sem prazo, usar a situação da fonte | P | BAIXA |
| P57 | A Previsão conta seletivo e chamada pública como concurso | Previsão | Paulo Lopes "Em dia" só com 3 seletivos e 2 itens "desconhecido"; 10 dos 20 "Em dia" sem concurso no último ano (`servico/previsao.py:144-149`) | Contar só tipo "concurso" | P | BAIXA |

### 3.5 Conferido e certo

Isto bateu, e é a base para confiar no resto:
- **O "Fiz hoje" bate com o `metricas`** em 28/09, 29/09 e 05/10 (o de 05/10 com a correção da decisão 127 e o aviso da 130 na faixa certa); o que o P02 e o P08 questionam é o dado, não a conta.
- **Hoje, Semanas e Minhas matérias somam igual:** Semana 1 = 68 = 17 + 26 + 15 sem acerto + 10 de IA; LP 51 + DC 15 + DP 28 = 94 = 68 + 26; os minutos fecham (6h50 + 2h).
- **O treino de IA é sempre um número à parte** (LP 16, DP 17, total 33) e **nunca entra no acerto real**, no estado, na prioridade nem no nível.
- **O acumulado no radar é o mesmo em cinco telas** (15 questões, 27%); as 11 erradas, os 2 erros do caderno, as 49 questões do dia, a meta 79, os 32 dias até o fim do ciclo e o nível batem em todas.
- **Alvo e complementar nunca são somados** num número de incidência; o peso 0,25 do complementar só entra na ordem e a tela diz isso (decisões 63 e 67).
- **Nenhuma palavra de previsão proibida** em texto do sistema (vai cair, certamente, sempre cobra, tende a…); "tendência" só no rótulo do selo amarelo.
- **A frase "Não há evidência suficiente no acervo para afirmar isso." sai sempre exata**, com acentos, da constante única; a frase "Gerada por IA: não é questão oficial da FEPESE." aparece em toda questão gerada.
- **A procedência do texto de IA novo diz o modelo** (resumos e explicações de 05/10); a antiga, sem modelo, é a aceita pela decisão 116.
- **Hoje, Semanas, Minhas matérias, Meu desempenho e home só desenham números prontos** do `metricas`: conta em template só em largura de barra (a exceção é a dos Macetes, P39).

### 3.6 O que caiu na verificação

Cinco suspeitas não se sustentaram e ficaram fora:
- a barra do "Onde estudar primeiro" (alvo + 0,25 × complementar) não ser o número visível — é a decisão 63, e a tela diz "com peso 0,25 só na ordem";
- o % da semana somar faixas com consulta — é a decisão E2, e a tela diz;
- "não apareceu" em Abolitio criminis com a 2013-q53 pendente — é a regra da decisão 108 (a pendente vai à parte, com aviso); sobra a clareza (U33);
- a Previsão dar ano para município com um concurso só — é a regra da validade, com "base pequena" e "Toda data desta tela é previsão, e não fato" (só a docstring de `servico/previsao.py` está desatualizada);
- os Macetes afirmarem "costume" da banca — as dicas vêm com "Dica fixa do radar, não é contagem", como decidiu o design system (25/09).

## 4. Melhorias das telas que existem

A preferência foi sempre **remover > juntar > mover > mudar > criar**. Cada item tem um código (U01…U64); o benefício, o risco, o esforço e a prioridade de cada um estão na tabela única da seção 6. Aqui, o mapa por tela.

### 4.1 Por tela

**Hoje (dia comum)**
- U05 · o "Agora" vira atalho: o título da faixa da hora é link para ela, "Marque como foi" é link para "Como foi o dia", e o dia passado mostra "Fiz em DD/MM".
- U07 · o treino de IA de cada faixa num `<details>` com 🟣 e "treina, não mede" no resumo; sai "Você estudou: …; na árvore: …".
- U08 · uma linha e uma ordem para "onde fazer" ("Qconcursos: X"; em Português, 1º as reais do radar, 2º o Qconcursos).
- U09 · o R+7/R+30 mostra a divisão "7 de Direito Constitucional + 3 de Português" à vista.
- U10 · lei seca com o porquê de cada artigo na própria faixa (não no Plano B), com o selo do plano.
- U23 · o tema uma vez por dia: árvore e "caiu" só na primeira faixa do tema.
- U24 · topo e lateral só com o que é de agora (sai o "1h55", saem as repetições, o Mapa do ano fecha, "Se o dia apertar" entra no Plano B).
- U20 · uma caixa "Revisão de hoje": fila 1-7-30 com o botão, caderno e R+7, nunca somados.
- U26 · a Correção diz o que corrigir e tem "Anotar erro".
- U62 · um "Treinar no radar" por faixa; U63 · resposta comprimida (246 KB → 33 KB) e um formulário de editar só.

**Hoje (sábados que medem)**
- U02 · sem "Resumo(s)" nas faixas que medem sem consulta.
- U03 · "fiz no Qconcursos" vazio nas faixas com rodada; a faixa feita no radar fecha com a rodada.
- U04 · Reduzida e Plano B mantêm as faixas que medem.
- U25 · o botão da rodada antes da composição (que vai para um `<details>` com a amostra no resumo); o simulado da semana em tabela.
- U27 · revisão semanal: (1) e (2) numa lista, mais "N erradas no radar → Refazer"; artigos-chave num `<details>`.

**Meu foco (home)**
- U01 · saem "O que estudar agora" e "Começar treino" (ficam em Análises › Edital).
- U20 · "Revisão de hoje" no lugar do Revisar, com um número e um botão por fila; "Revisar agora" vai para Estudar › Simulado.
- U28 · o alvo e "Concurso" numa linha no fim; "Sua evolução" vira link — e a home volta a caber em 1366×680.
- U29 · o motivo da revisão com uma data e um número ("R+1 vencida em 30/09, há 6 dias").

**Estudar › Simulado, rodada e relatório**
- U15 · saem "Como você vai até agora" e "Nas questões geradas" (o acerto, com amostra, fica em Minhas matérias e no Meu desempenho).
- U16 · sai o "Começar" (e o "8.462"); o simulado curto de questão real passa a ser o compilado de 10 e 20, com a mesma trava do P12 (não sorteia as questões que as rodadas que medem vão usar). **Muda a decisão "Meus erros e o simulado compilado" (fase 4) e a especificação**, que fixam 40, 50 e 100.
- U35 · pesos do compilado e "Suas rodadas" em `<details>`; "o diagnóstico de 10/10 e o simulado de 07/11 começam no Hoje →".
- U17 · na questão gerada, o artigo só depois de responder, e "Essa questão está errada" embaixo, em 2 passos.
- U06 · a rodada volta para a faixa; U36 · no relatório, só o resultado antes dos erros.

**Estudar › Gerar questões**
- U37 · "Treinar com as que já tenho" em primeiro, com o seletor nos nós de hoje.
- U51 · o cartão da API vira os 3 passos com o comando exato (decisão 114).
- U38 · "Os assuntos do cronograma" só com os nós sem gerada, com a data da faixa.

**Revisão › Caderno de erros e Anotar erro**
- U39 · os erros logo depois do título; U40 · botão "Arquivar (não é regra)".
- U14 · no Anotar erro, "A regra certa" e "Por que eu errei" no topo, o resto num `<details>`, o seletor só no ramo da matéria.
- U21 · o erro chega ligado ao nó da faixa; "Anotar erro" em cada erro do relatório.

**Revisão › Macetes**
- U19 · sai o "Padrão da banca" (vai para a Incidência, com o mínimo); U46 · atalhos por matéria e os macetes em `<details>`.
- U50 · um cartão por matéria da árvore, com a base da Incidência; U47 · "O costume de qualquer banca" em página própria.
- U61 · na página de questões de um macete, título e volta certos.

**Fichas e ficha completa**
- U22 · "O que estudar" logo abaixo do "caiu"; o texto completo e o "Por que agora" em `<details>`.
- U12 · âncoras na ficha (`#o-que-estudar`, `#questoes`) pelo tipo da faixa; U13 · sai a lista dos 44 enunciados de geradas; U43 · os comandos de gerar num `<details>` "Gerar mais", com o N da faixa e só nos nós com falta (a receita do relatório vai para Mais; o aviso "12 sem assunto" do Edital, para a Conferência).
- U49 · "caiu" e "como a FEPESE cobrou" num cartão; "Revisão e desempenho" noutro.
- U41 · um cartão por tema na aba do dia; U42 · o estado da conferência (ficha e resumo) no cartão e na lista.

**Semanas** — U18 · sem setas na semana em andamento; U44 · a linha do ciclo atual, com link para a comparação de 07/11.

**Análises** — U30 · Edital com Matérias e "Onde estudar primeiro" no topo; U31 · Minhas matérias com as matérias com dado no topo; U11 · Meu desempenho abre pela fila; U48 · uma tabela por nó; U32 · Incidência com cada matéria num `<details>`; U33 · pendentes e anuladas listadas; U34 · Conferência abre no que falta; U45 · o método das telas de análise num `<details>` "Como esta tela conta".

**Concursos e Mais** — U56 · dado e botão no topo, instrução dobrada; U57 · Previsão com os 12 municípios de um ano só numa linha; U58 · banca e tipo na linha do concurso e atalho "Segurança pública".

**Em todas as telas** — U52 · um rótulo por ação; U53 · um nome por conceito; U54 · selo só para origem e a frase padrão com uma cara só; U55 · menos frases de sistema; U59 · um caminho por tela (o Caderno sai das sub-abas do Hoje, a Conferência vai para Mais); U60 · textos menores; U64 · o que se repete sobe para o `design.css`.

### 4.2 O que cortar ou mover

Nada aqui apaga amostra, selo, procedência, a frase padrão, a separação das evidências ou o "treina, não mede": o que é dessas regras só muda de lugar (chip, `<details>`, página de detalhe).

| Tela | O que | Ação | Para onde | Por quê |
|---|---|---|---|---|
| Hoje | 'Você estudou: `<tema>`; na árvore: `<caminhos>`' | cortar | — (o nó fica na linha Assunto/Subassunto/Elemento) | repete a árvore: 254 palavras |
| Hoje | '2º Se quiser mais, no radar', formulários 'Treinar no radar' e 3 passos de gerar | mover | `<details>` por faixa, com selo roxo e 'só treina, não mede (N geradas)' no resumo | 774 de 2.104 palavras (37%) de treino acima do que mede |
| Hoje | 'Filtro: X' + '1º No Qconcursos (são as que medem): X' | juntar | 'Qconcursos: X' (sem 'são as que medem' com consulta) | mesmo filtro 2x; faixa com consulta não mede |
| Hoje | Regra 'As do radar contam sozinhas…' + aviso da 130; '(só treinam; … nunca somado ao da faixa)' 5x | juntar | uma linha; 'só treina, não mede' no resumo das geradas | a mesma instrução repetida |
| Hoje | Linha da árvore e 'Caiu em…' nas faixas repetidas do tema | mover | 'ver detalhe' (inteiros na 1ª faixa do tema) | Art. 5º XVII-XLIX repete 34 palavras em 4 faixas |
| Hoje | Cartões '1h55 de estudo · 49 questões · termina às 20:05' | cortar | — ('Ativar Plano B' fica) | 1h55 é só a manhã; o resto repete os blocos |
| Hoje | Sequência de 'Esta semana' e cartão Objetivo | juntar | herói ('Meta 79 de 100', selo do plano) | sequência e meta 2x |
| Hoje | Mapa do ano aberto (102 palavras) e motivo do nível (23) | mover | `<details>` fechado; motivo só na Semanas, com o selo amarelo | outra hora antes da 1ª faixa no celular |
| Hoje | Cartão 'Se o dia apertar' | juntar | `<details>` do 'Ativar Plano B' | Reduzida com 3 definições na tela |
| Hoje (lei seca) | 'O porquê de cada um está no Plano B' e 'Seleção do plano… não é o que a banca mais cobra' | mover | lista do essencial (artigo — porquê) e selo do plano com a ressalva no title | porquê só com o Plano B ativo |
| Hoje | 'O que eu anoto aqui é o diário do cronograma…' | cortar | — | explica o sistema e erra quando o acerto é do radar |
| Hoje | 'Testar aviso', 'Testar em 10 s' e diagnóstico | mover | `<details>` no cartão do cronômetro | com JS, o 1º cartão é painel de teste |
| Hoje | 'anotar os erros' do 'Fiz hoje' | mover | faixa Correção | fica onde o plano manda anotar |
| Hoje | 'ver todas as semanas →', 'Hoje' do herói no próprio dia, sub-aba 'Caderno de erros' | cortar | — (sub-aba Semanas, aba Hoje e Revisão bastam) | destinos repetidos; o caderno troca de seção |
| Hoje (lateral) | Cartão do caderno | juntar | cartão 'Revisão de hoje' (fila 1-7-30 + caderno, nunca somados) | a fila da 128 não aparece no Hoje |
| Hoje (dia passado) | Cartão 'Agora · Este dia: começa às 10:15' em dia passado | cortar | linha 'Fiz em DD/MM' (do metricas) | 'Fiz hoje' depois de 1.549 palavras |
| Hoje (dia passado) | Formulário 'editar' de cada extra (select de 439) | mover | um formulário só ou página de edição | 4 cópias do select de 439 = ~310 KB (63%) |
| Hoje (sábados) | 'Resumo(s)' nas faixas que medem | cortar | — (fica na Correção, no R+7 e na ficha) | medição sem consulta; 65 resumos em 07/11 |
| Hoje (sábados) | 'fiz / acertei / com consulta / ✓ Fiz' nas faixas 100% no radar | cortar | ✓ que grava só o tempo; número vem da rodada | fiz 20/40/50 conta em dobro |
| Hoje (10/10, 07/11) | Composição das faixas que medem (233, 291, 885 palavras) com regra e frase padrão | mover | `<details>` com a amostra no resumo; botão abaixo do título | botão depois de toda a composição |
| Hoje (sábados) | Lista do Simulado da semana em prosa e 'Sem questão neste simulado…' | mover | tabela Qtd / Tema / Filtro / provas do cargo; o resto num `<details>` | 918 palavras em prosa |
| Hoje (sábados) | 'Só questões…' (3x), 'É o diagnóstico de 03/10… (decisão 105)', '(o mínimo… no config/amostra.yml)' | cortar | — (amostra e 'Amostra insuficiente' ficam) | regra repetida, nº de decisão e arquivo na tela |
| Hoje (sábados) | Artigos-chave da semana (264 a 337 palavras) | mover | `<details>` '(3) Os artigos-chave da semana' | como 'Os temas da semana' |
| Hoje (sábados) | '(2) Onde mais errou' | juntar | lista do (1): 'tema · erros · motivo' | repete os temas |
| Hoje (03/10) | 'Criar a rodada' em dia passado | cortar | — (só no dia da faixa) | rodada órfã gasta o estoque de RL |
| Hoje (07/11) | Linhas DH/DC/DP/LEP 'sem diagnóstico' | juntar | uma linha com acumulado e amostra | só RL e Português comparam |
| Semanas | Setas da semana em andamento | cortar | — | comparam 1 dia com semana inteira |
| Semanas; Minhas matérias | Parágrafo do cabeçalho | mover | chip 'soma plano, extra e radar · meta só sem consulta' + `<details>` | mesmo parágrafo nas duas telas; a E2 segue declarada |
| Semanas | Tiles 'acertos' e 'erros' | juntar | linha Total | mesmo número 2x |
| Semanas | Foco do ciclo ('A base: Português, RL…') | mover | linha do ciclo atual (ResumoDoCiclo) com link para 07/11 | repete o Mapa do ano |
| Meu foco (home) | Bloco 'O que estudar agora' e botão 'Começar treino' | mover | Análises > Edital (tabela de matérias e 'Treinar', que já existem) | contradiz o plano e gasta questões do alvo |
| Meu foco (home) | '11 questão(ões) que errei' + 'Revisar agora' | mover | Estudar > Simulado ('Só meus erros'), com link no cartão | 10 das 11 já abrem a rodada de revisão |
| Meu foco (home) | Bloco do alvo + faixa 'Concurso' | juntar | uma linha no fim ('hipótese' e 'base pequena' ficam) | home não cabe em 1366x680 |
| Meu foco (home) | Fórmula, regra do Revisar, nota da última resposta | mover | `<details>` 'Como conto' (selo e amostra num chip) | regra entre ele e o que fazer |
| Meu foco (home) | 'A linha do tempo passa a registrar… radar atualizar' | cortar | — | instrução de manutenção |
| Análises > Edital | Cartões Situação, De olho e Sinais | mover | fim, uma linha cada sem novidade | ocupam a 1ª tela |
| Análises > Edital | Legendas de método | mover | `<details>` 'Como esta tela conta' (frase da barra fica junto da barra) | ~23 frases de método |
| Análises > Edital | '12 questões … sem assunto … radar conteudos --pendentes' | mover | Conferência | manutenção no estudo |
| Análises > Edital | 'Sai de de_olho, no config/alvo.yml' e frase similar | cortar | — | cita arquivo de config |
| Análises > Minhas matérias | 8 cartões 'Ainda não estudei' | juntar | uma linha por ciclo, no fim | matérias em estudo entre cartões cinza |
| Análises > Minhas matérias | 'Se a prova fosse hoje' no topo | mover | abaixo dos cartões | maior número feito com 1 de 11 matérias |
| Meu desempenho | Coluna 'Fora do estado' vazia e frase longa de amostra por linha | mover | chip quando houver valor; frase na legenda do `<details>` ('faltam N' e 'radar X% em N' ficam) | '—' em 16 linhas; amostra 3x por linha |
| Meu desempenho | Cartão 'Quando eu estudei e revisei' | juntar | colunas da tabela 'O que eu já respondi' | os mesmos 16 nós |
| Meu desempenho | Assunto e matéria da fila (8 de 16); 'Questões a refazer' | mover | `<details>` abaixo das 8 pontas; caixa da fila no topo | mesma revisão 2-3x; ação no fim |
| Meu desempenho | Cabeça (80) e 6 parágrafos (385) | mover | `<details>` no fim; chip com selo, 'nunca somados', 'só sem consulta', 'treina, não mede' | 465 palavras de regra |
| Meu desempenho | 'O que eu ainda não estudei' | mover | `<details>` com o total; fora do edital no fim | 455 palavras (a frase errada é o P09) |
| Incidência | Tabelas das 13 matérias abertas e 191 linhas zeradas | mover | `<details>` por matéria (amostra no resumo); zerados em `<details>` próprio | 9.129 palavras ao abrir |
| Incidência | 2ª linha-resumo, 26 'nunca se somam', colunas 'O que aconteceu' e 'Anos' | juntar | 1ª linha; uma vez na cabeça; célula única do alvo | mesma amostra 2x; 3 colunas para 1 fato |
| Incidência | 'A classificação é do Claude Code e vale depois de conferida' | mover | `<details>` 'Como ler' | 162 de 162 conferidas; procedência não some |
| Conferência | Lista das 162 já conferidas como padrão | mover | atrás de 'ver todas' | 2,56 MB no que está feito |
| Conferência | Seletor 'Corrigir para' e motivo 'Pendente' | mover | `<details>` por questão | menos clique errado |
| Conferência | Texto amarelo e caixa do catálogo | cortar | — (voltam com amostra) | caixa devolve 'Nenhuma questão' |
| Conferência | 'A proposta é do Claude Code e só vale depois de conferida' (alvo) | mover | só com proposta por conferir | 162 de 162 conferidas |
| Análises | Aba Conferência | mover | Mais, ao lado da Auditoria | manutenção, não análise |
| Estudar > Simulado | Tabelas 'Como você vai até agora' e 'Nas questões geradas' | mover | Minhas matérias e Meu desempenho (já estão, com amostra) | LP 27% em 15 em vermelho, sem amostra |
| Estudar > Simulado | Formulário 'Começar' e frase '8.462 questões no acervo' | cortar | — (compilado com 10 e 20) | sorteia IESES e recusadas; 8.462 soma evidências |
| Estudar > Simulado | Pesos do compilado, 3 frases e 'Suas rodadas' | mover | `<details>`; 'Continuar' fora | botão na palavra 209 |
| Rodada (questão gerada) | 'Diz se apoiar em … — ler a lei' e 'Essa questão está errada' | mover | relatório; abaixo das alternativas em 2 passos | entrega a resposta; 1 clique apaga respostas |
| Rodada (questão gerada) | Selo roxo da cabeça + 'Treino com questões escritas por IA — não medem…' | juntar | uma linha com o selo: 'Gerada por IA… — treina, não mede' | 4 avisos de IA; 'treina, não mede' fica |
| Relatório da rodada | Legenda 'Cada parte com o seu selo…' e 'Por matéria' com 1 matéria | cortar | — (selo por linha fica; tabela volta com 2+) | chama a resposta da IA de gabarito; repete o geral |
| Relatório da rodada | 'Sem nota de corte…' e 'o acumulado está na home' | mover | title do número; chip 'N questões · amostra pequena' com link | aponta onde o acumulado não está |
| Relatório da rodada | Receita 'radar gerar --pedido --explicacoes' | mover | Mais (comando da 114) | manutenção antes dos erros |
| Relatório da rodada (IA) | Botão 'Gerar mais' | cortar | 'Treinar mais deste assunto' | leva à API sem chave |
| Gerar questões | Custo US$, câmbio, 'Gerar e treinar — gasta', 'rode radar gerar --quantas 5' | cortar | terminal (--valendo), se houver chave | sem chave; decisão 114 |
| Gerar questões | Cartão 'Treinar com as que já tenho' | mover | 1º cartão | botão aos 241 palavras |
| Gerar questões | 27 nós com gerada em 'Os assuntos do cronograma' | juntar | seletor do treino | ~650 palavras |
| Gerar questões | 'Como você vai, nos dois' | mover | Minhas matérias (já separados) | acerto num lugar, com amostra |
| Gerar questões | 2 frases de sistema do aviso roxo | mover | `<details>` 'por quê' (selo, frase e 'Isto treina, não mede.' à vista) | regra antes do conteúdo |
| Caderno de erros | 'O que mais te derruba' e filtro de 4 campos | mover | `<details>` (abertos com 3+ erros / filtro ativo) | vêm antes de 2 erros |
| Caderno de erros | Subtítulo de 2 frases e 'Contado nos N erros… contam a história' | juntar | chip de uma linha; o N no resumo do `<details>` | base fica, justificativa sai |
| Anotar erro | Select de 438 nós e campos já preenchidos | mover | `<details>` 'Detalhes'; seletor no ramo | 77% da página; regra é o 7º campo |
| Anotar erro | 'Diagnósticos' na sugestão de matéria | cortar | — | não é matéria |
| Macetes | Bloco azul 'Padrão da banca' + 'Palavras que mais aparecem' | mover | Incidência da matéria (link) | padrão sem mínimo, diverge da Incidência |
| Macetes | Corpo dos 40 macetes | mover | `<details>` por cartão, selo roxo e títulos no resumo | 4.914 palavras abertas |
| Macetes | Cartões 'Direito Processo Penal' e 'Direito Processual Penal' | juntar | um cartão | o de 2013 diz que não há macete |
| Macetes | 'O costume de qualquer banca' e 'Por que só aparece FEPESE, IESES' | mover | página própria; Mais (Fontes) | começa na palavra 5.774 |
| Macetes; Questões de um macete | Nota do config/leis.yml | cortar | — (só com aviso de lei) | 36 de 40 páginas sem aviso |
| Macetes | 'confira na fonte' 40x, 'ler `<lei>`' repetido, título em 4 partes | juntar | 1x no topo; 1x por cartão; um título (procedência em cada macete) | ~240 palavras repetidas |
| Fichas (aba do dia) | Parágrafo de abertura da aba do dia | mover | estado de conferência em cada cartão | frase fixa |
| Fichas (aba do dia) | Cartão repetido Manhã/Noite e as 2 linhas do tema sem ficha | juntar | um cartão por tema; uma linha 'Sem ficha nem resumo' | 5 cartões para 3 temas |
| Fichas | Janelas de resumo sem botão e abertura da lista do ciclo | cortar | — | peso invisível; explicação do sistema |
| Ficha completa | Lista dos 44 enunciados das geradas | cortar | — (contagem, selo roxo e frase oficial ficam) | 754 palavras (24%) |
| Ficha completa | Comandos de gerar | mover | `<details>` 'Gerar mais', com N da faixa, só nós com falta | '--quantas 10' onde a faixa pede 0 |
| Ficha completa | 'Entender', 'Memorizar', 'Confusões comuns' e 'Por que agora' | mover | `<details>` com procedência / prioridade e 'regra, não previsão' no resumo | ~505 palavras antes do que ler |
| Ficha completa | 'Como a FEPESE cobrou'; 'Erros', 'Quando revisar', 'Meu desempenho' | juntar | cartão 'Caiu ou não caiu'; cartão 'Revisão e desempenho' | mesma contagem em 4 cartões |
| Ficha completa | Legenda dos 5 selos e 'Conferi esta ficha' | mover | fim (no topo, só o estado) | topo com o tema |
| Concursos — Todos | Banca e tipo em 'detalhes' | mover | linha principal | seletivo e FEPESE num olhar |
| Concursos — Todos | 'Meu mural (1)' | juntar | sub-aba Acompanhando | 5 nomes para a marca |
| Acompanhando | 2 frases de sistema | cortar | — ('Sem eventos ainda') | ~50 de 130 palavras |
| Calendário; Previsão; Mais | Instruções de uso (Calendário), conta (Previsão), backup e configs (Mais) | mover | `<details>`; à vista botão, frase de previsão e 'Último backup' | instrução antes do dado |
| Previsão | 12 cartões 'um único concurso conhecido (2026)' | juntar | uma linha com 'base pequena' | 12 cartões iguais |

## 5. Ideias novas

Dois agentes levantaram ideias (uma linha de método de estudo, outra de produto e UX) e um terceiro as filtrou pela §24 do novo.md: descartou o que contradiz regra, traz o Anki de volta, pede JS ou dependência nova, inventa dado, repete uma melhoria da seção 4 ou não tem benefício concreto para o meu estudo. Ficaram 9. A classe é a da §24: **B** correção necessária, **C** melhoria técnica necessária, **D** sugestão nova.

**I1 · Em 10/10, os dois diagnósticos abrem o bloco** — D · ALTA · P · *decidir até 09/10*
- *Problema:* a linha de base que será comparada com 07/11 está marcada em condição pior. De manhã, o diagnóstico de RL vem depois de 50 min de teoria de "Princípios de contagem" e 60 min de revisão semanal; à noite, o de Português vem depois do simulado de 30 questões (`cronograma.yml:1326-1384`). Em 03/10 os dois abriam o bloco (`:660-712`); a decisão 105 os mudou de lugar junto com a data. (Um agente mediu que 4 das 20 questões de RL são de contagem; não foi conferido de forma independente.)
- *Benefício:* o diagnóstico mede o que eu sei antes de estudar o assunto e sem 90 min de prova nas costas; a teoria de contagem, feita depois, aproveita as questões que acabei de ver. O dia não muda de tamanho.
- *Como:* só a ordem de 10/10 no `cronograma.yml` (e a lista de 10/10 em `tests/test_composicao.py:248-251`).
- *Agora?* Sim, até 09/10: a rodada é reconhecida pela posição da faixa, e mudar a ordem depois de criá-la desliga o R+7 de 17/10 e a comparação. *Risco:* melhora a medida; a semente muda e com ela as 20 questões, sem perda (as rodadas ainda não existem). **Muda a decisão 105** só na posição; é mudança de cronograma, com a sua aprovação (§18).

**I2 · A faixa que revisa diz se o dia de origem foi marcado, e o "Agora" avisa o dia que ficou aberto** — B · ALTA · P · *a partir de amanhã*
- *Problema:* o R+7 de amanhã (07/10) diz "7 questões NOVAS de Lei de Execução Penal sobre o que você estudou em 30/09" (`cronograma.yml:1041-1042`), mas **de 30/09 a 04/10 não há nada gravado** — só 28/09, 29/09 e 05/10 têm registro (conferido por mim na cópia). São 7 faixas de revisão desta semana e das próximas que voltam a esses dias (64 questões); Minhas matérias diz "Ainda não estudei" para LEP e Direitos Humanos.
- *Benefício:* amanhã eu sei, antes do Qconcursos, se o R+7 da LEP é revisão ou primeiro contato; se estudei e não marquei, marco 30/09 com um clique; se não estudei, leio a ficha antes das 10 questões.
- *Como:* a linha "volta do dia 30/09" (`hoje.html:950`) passa a dizer "volta do estudo de 30/09 ✓", "30/09 sem marca · marcar 30/09 → · ler a ficha antes →" ou "em 30/09 marquei Não fiz", e o "Agora" ganha "05/10 ficou aberto → fechar" quando for o caso. É uma função de leitura ao lado da `arvore_das_faixas`; nada é gravado.
- *Risco:* nenhum número muda; a tela diz "sem marca", nunca "não estudou". Decisão: nenhuma (é a mesma ideia do P50, "no plano em DD/MM · não marcado").

**I3 · Até 07/11, o radar só muda para corrigir número ou preparar 10/10 e 17/10** — D · ALTA · P · *regra de trabalho*
- *Problema:* os dados mostram o radar disputando o tempo do estudo. Em 29/09 o "Como foi o dia" diz "Dia horrivel preciso configurar todo o site mas estou esperando o token…"; de 30/09 a 04/10 não há marca de estudo, e as Etapas 0 a 8 do `decisoes.md` são desses dias; as decisões 127 a 130 são de 05 e 06/10. Se tudo desta auditoria entrar agora, a régua muda no meio do ciclo que vai medir 10/10 e 07/11.
- *Benefício:* as noites voltam para as questões, entra menos número novo (e errado) na tela, e 10/10 e 07/11 são medidos com a mesma régua.
- *Como:* escrito no `docs/pendencias.md` e no "Próximo" do CLAUDE.md: até 07/11 só entra (a) o que corrige número ou o risco de gravar número errado (P01 a P08 com a sua aprovação, o "fiz" pré-preenchido, o "Começar treino") e (b) o que prepara 10/10 e 17/10 (I1, I2, I4 e I6). O resto e a nuvem, depois de 07/11.
- *Risco:* nenhum (é menos mudança). Adia a decisão 126 (a nuvem); a data exata fica com você.

**I4 · Caderno de erros: uma regra por tema, e os vencidos revistos dentro da Correção** — D · ALTA · P
- *Problema:* o caderno não está funcionando como 1-7-30: as 2 entradas são de 29/09, são relato de sessão e não regra, estão vencidas desde 30/09 e nunca foram revistas. E o plano pede mais do que cabe: a Correção de 25 min manda copiar "TODO erro" no caderno; o 10/10 manda cada erro "com o motivo"; o 17/10, o motivo de até 40 erros — um formulário de 8 campos para cada.
- *Benefício:* uma regra por tema cabe nos 25 min e é o que o caderno existe para guardar; a revisão acontece numa faixa que eu já faço toda noite, tentando lembrar a regra antes de vê-la — é o único 1-7-30 de memória que sobrou sem o Anki; o 17/10 passa a caber no tempo.
- *Como:* (1) texto da Correção: "Antes de ler o comentário, diga por que a certa é certa. Escreva no caderno UMA regra por tema que você errou hoje"; (2) na faixa Correção, até 3 erros vencidos, cada um num `<details>` "📓 matéria · assunto — qual é a regra?", com os dois botões que já existem; (3) em 10/10 e 17/10, "uma regra por assunto errado", não o motivo de cada um dos 40. O erro feito no radar continua no radar (decisões 24 e 128).
- *Agora?* O texto de 10/10 antes de 10/10, o de 17/10 antes de 17/10; os cartões na Correção, até 17/10. *Risco:* nenhum (o caderno não mede, E1). **Muda a decisão 105** no ponto "com o motivo de cada erro" e o texto da Correção.

**I5 · Conferir primeiro as 5 fichas dos temas já estudados** — D · ALTA · P
- *Problema:* nenhuma das 65 fichas foi conferida, e pela decisão 81 a faixa sem `conteudo` só chega à árvore pela ficha conferida — por isso Penal e Constitucional estão fora da revisão (P09). "65 fichas" é grande demais para começar, e nenhuma tela diz por onde.
- *Benefício:* Direito entra na revisão 1-7-30 conferindo 5 fichas, não 65; depois, uma por dia — a do tema que acabei de estudar, com a lei ainda aberta, que é quando dá para conferir de verdade.
- *Como:* agora, sem código, esta lista (medida por um agente): **Aplicação da lei penal; Art. 5º, caput e incisos I a XVI; Substantivo e adjetivo; Artigo, numeral e pronome; Fato típico e nexo causal** — elas ligam 9 faixas já feitas. Depois: a faixa de teoria e a de lei seca ganham "🟣 ficha não conferida — conferir liga esta faixa à revisão →", e Fichas › todos põe primeiro os temas já estudados e não conferidos.
- *Risco:* a conferência liga só o "estudado" e as datas, nunca o acerto (decisão 81, que fica). O risco é conferir sem ler; por isso a linha diz o que o clique muda.
- *Pendência:* dá a ordem da D ("Conferir as 65 fichas") e da H.2, sem resolvê-las: as outras 60 continuam.

**I6 · Ler a explicação dos erros de 10/10 antes do R+7 de 17/10** — D · MÉDIA · P
- *Problema:* o R+7 de 17/10 refaz no radar todos os erros dos diagnósticos, mas (segundo um agente, não conferido) só 16 das 40 questões que a composição escolhe hoje têm explicação; a Correção de 10/10 não diz de onde vem o porquê de cada erro.
- *Benefício:* fecha o ciclo errar → entender → refazer; o 17/10 passa a testar se a explicação ficou.
- *Como:* só o texto do plano: na Correção de 10/10, "leia a explicação de cada erro no relatório; para os sem explicação, faça o pedido (os 3 passos de Gerar questões) até 16/10"; no R+7, "refaça cada erro antes de reler a explicação".
- *Risco:* a explicação é texto de IA (🟣, fonte, modelo e data) — vale o gabarito oficial (decisão 122). Decisão: nenhuma.
- *Pendência:* o pedido das que faltam é o mesmo da D ("Quatro explicações não escritas"), que fica de pé para as que dependem do texto da prova.

**I7 · O Hoje abre na faixa de agora** — D · MÉDIA · P · *depois de 07/11*
- *Problema:* às 19:30 a faixa em curso vem depois de ~1.579 palavras na coluna principal; o U05 transforma o "Agora" em link, mas isso ainda custa 1 clique a cada abertura.
- *Como:* o servidor põe `id="agora"` na faixa em curso (ou na próxima que conta, nunca no Bônus opcional; depois da última, no "Como foi o dia"); o `Radar.bat`, a aba Hoje e a marca "Radar" passam a apontar para `/hoje#agora`. A `dobra.js` já abre o bloco da âncora: não há JS novo.
- *Benefício:* abro o radar e já estou na faixa de agora, sem clique e sem rolar. *Risco:* nenhum para o dado.

**I8 · Um teste que segura a limpeza** — C · MÉDIA · P · *primeiro passo da limpeza*
- *Problema:* a limpeza mexe em dezenas de lugares onde moram a amostra, os selos, a procedência, a frase exata e o "treina, não mede"; nada impede que um corte apague o que é inviolável, nem que a próxima etapa encha a tela de novo (o Hoje cresceu decisão a decisão: 71, 112, 120, 125, 130).
- *Como:* um teste com dado fixo e relógio parado renderiza o Hoje de um dia útil, o de um sábado e uma ficha, e confere primeiro que estão presentes, onde a regra exige, "N questões · M provas", os selos, a procedência, a frase exata e "treina, não mede"; depois, um teto de palavras visíveis por tela, com folga. O `beautifulsoup4` já é dependência.
- *Benefício:* a tela limpa continua limpa e honesta; se um corte tirar a amostra, o `pytest` acusa antes do commit.

**I9 · Fixação e Aprendizagem: responder de cabeça e abrir a lei só para conferir** — D · BAIXA · P · *Ciclo 2, ou antes se você aprovar*
- *Problema:* a consulta virou licença para chutar: em 29/09, numa faixa com consulta, a nota do caderno diz "Em 12 questoes acho que umas 3 eu tinha certeza o resto foi tudo chute".
- *Como:* só texto no plano: "Marque de cabeça; só então abra o artigo para conferir". Opcional: "antes de ler, faça 2 das 8 da Fixação, sem consultar" (pré-teste), sem faixa nova.
- *Benefício:* cada dúvida vira recuperação, não chute. *Risco:* nenhum número muda (a faixa com consulta continua fora da meta, E2). Muda o texto da 6A, item 1, com a sua aprovação.

**Descartadas pelo crítico** (com o motivo):
- *marcar "chutei" em cada questão do radar* — mexe na camada que mede, 4 dias antes da linha de base;
- *pré-teste como faixa nova* — o mesmo efeito cabe no texto (I9);
- *simulado de sábado só com tema de estudo marcado* — muda a decisão 69 sem necessidade (o I2 já mostra o fato);
- *fechar o dia numa caixa só* — criaria um segundo lugar para anotar o mesmo número;
- *ligar no relatório a rodada solta a uma faixa* — é o P02;
- *folha para anotar todos os erros de uma vez* — sem necessidade com o I4;
- *o caderno como cartão na lateral* — foi para a Correção (I4);
- *redirecionar "/" para o Hoje e tirar a home* — conflita com o desenho da home (seção 8); fica como alternativa depois de 07/11;
- *guardar o link do filtro do Qconcursos* — o favorito do navegador ou o filtro salvo no próprio Qconcursos resolvem sem código; e o radar nunca inventa URL;
- *log de uso por dia* — com um usuário só, basta perguntar quais telas ele usa.

## 6. A tabela única

Todas as sugestões, numa tabela só, da mais à menos importante (e, dentro da mesma prioridade, a de menor esforço primeiro). **P** = correção de precisão (seção 3), **U** = melhoria de tela (seção 4), **I** = ideia nova (seção 5); quando duas são a mesma ação, estão na mesma linha, e a prioridade e o esforço são os da ação inteira (vale a maior prioridade entre elas). A seção 3 dá a de cada P sozinho, e por isso os dois podem diferir: o P52 é BAIXA sozinho e ALTA junto com o P13 e o U16. Esforço: **P** pequeno (um arquivo, uma tarde), **M** médio (serviço + template + teste), **G** grande (várias telas).

| # | Sugestão | Tela | Benefício para o meu estudo | Risco para a precisão | Esf. | Prioridade |
|---|---|---|---|---|---|---|
| P02 | Confirmar e corrigir o 29/09; o `conferir-dias` acusa faixa × rodada da mesma matéria no mesmo dia | Hoje, Semanas, Minhas matérias, 07/11 | O acerto de LP e a base de 07/11 sem 10 questões contadas duas vezes | Mexe em dado gravado: só com a sua confirmação, com cópia antes | P | CRÍTICA |
| P06 | Na Conferência, "Corrigir" no mesmo nó vira confirmar; "Corrigir" e "Pendente" copiam artigo e item do edital | Conferência | Para de apagar o artigo que leva a pendente ao tema | Nenhum; precisa de teste que relê o dispositivo | P | CRÍTICA |
| P08 | Confirmar se o 28/09 foi do Qconcursos ou das geradas; se geradas, corrigir | Hoje 28/09, Minhas matérias | Nenhum acerto de IA contando como real | Só com a sua resposta; muda a decisão 3 da Etapa 0 | P | CRÍTICA |
| U02 | Tirar "Resumo(s)" das faixas que medem sem consulta | Hoje (sábados) | Diagnóstico e fechamento sem consulta de verdade; 07/11 sem 65 janelas escondidas | Nenhum (o Resumo fica na Correção e na ficha); muda a decisão 120 | P | CRÍTICA |
| U01 · P12 · P15 | Tirar da home "O que estudar agora" e "Começar treino" (ficam no Edital); o "Treinar 20 questões" do Edital não sorteia as questões que medem | Meu foco, Edital | Uma resposta só para "o que estudar" (a do plano) e a linha de base 10/10 × 07/11 protegida | Reduz; muda a decisão "home de 3 blocos" | M | CRÍTICA |
| P01 | Uma regra só para o "anotado" sem conteúdo (conta na matéria) | Meu foco, Edital, Meu desempenho, Minhas matérias, 07/11 | LP e Penal com o mesmo número e o mesmo estado de amostra em toda tela | É a própria correção; muda a decisão 81 (só no nível da matéria) | M | CRÍTICA |
| P03 · U03 | "fiz no Qconcursos" vazio nas faixas com rodada; a faixa feita no radar fecha com a rodada (grava só o tempo) | Hoje (dia, dia passado, sábados) | Nenhum clique grava o plano por cima das respostas; o dia volta a poder ser Ideal | Precisa de teste que garanta 0 questões gravadas; muda a 1D (regra 1) e estende a 130 | M | CRÍTICA |
| P04 · U09 | R+7/R+30 com "+ 3 de Português": divisão à vista e linha própria no plano, de 07/10 em diante | Hoje, Minhas matérias | As 3 de Português vão para LP; eu não pulo a revisão de Português | Mexe em 32 faixas do cronograma (de 07/10 em diante; a de hoje fica com o cuidado de uso da 3.1), com a sua aprovação | M | CRÍTICA |
| P05 | Esconder o gabarito das questões reais ainda não respondidas no radar (ficha e resumo) | Ficha, Resumo, Hoje | O acerto das 13 de Concordância mede domínio, não memória | A letra fica no dado; muda as decisões 109 e 118 | M | CRÍTICA |
| P07 | As rodadas que medem não repetem questão já usada por outra rodada que mede | Hoje 10/10, 17/10, 07/11 | A comparação que decide o Ciclo 2 mede RL, não memória | Muda a decisão 67; precisa estar pronto antes de 07/11 | M | CRÍTICA |
| U04 · P14 | Reduzida e Plano B de sábado mantêm as faixas que medem; uma definição só de Reduzida | Hoje (sábados) | Um sábado apertado não apaga a linha de base de 10/10 | O Plano B é código: precisa de teste | M | CRÍTICA |
| I1 | Em 10/10, os diagnósticos abrem o bloco | `cronograma.yml` (10/10) | A base de 10/10 sem o estudo do mesmo assunto antes e sem cansaço | Melhora a medida; muda a decisão 105 só na posição; **até 09/10** | P | ALTA |
| I2 | A faixa que revisa diz se o dia de origem foi marcado; o "Agora" avisa o dia aberto | Hoje | Amanhã sei se o R+7 da LEP é revisão ou primeiro contato (30/09 não tem registro) | Nenhum número muda | P | ALTA |
| I3 | Até 07/11, o radar só muda para corrigir número ou preparar 10/10 e 17/10 | (forma de trabalhar) | As noites voltam para as questões; 10/10 e 07/11 com a mesma régua | Nenhum; adia a nuvem (decisão 126) | P | ALTA |
| I4 | Caderno: uma regra por tema; os vencidos revistos dentro da Correção | `cronograma.yml`, Hoje (Correção) | O 1-7-30 do caderno volta a acontecer; o 17/10 sem 40 formulários | Nenhum (o caderno não mede); muda a 105 no 17/10 | P | ALTA |
| I5 | Conferir primeiro as 5 fichas dos temas já estudados; a faixa avisa a ficha não conferida | Fichas, Hoje | Penal e Constitucional entram na revisão conferindo 5 fichas, não 65 | Nenhum (liga só o "estudado", nunca o acerto) | P | ALTA |
| P10 | O "caiu" da faixa com as notas; "prioridade baixa, estude o básico" sai do selo azul | Hoje, Fichas, ficha | Não estudar raso o que cai | É a correção; muda a 108 só no texto | P | ALTA |
| P11 · U18 | Seta da semana só com o mínimo (20) entre semanas fechadas; o n em cada ponto do gráfico | Semanas, Minhas matérias | "Estou melhorando?" respondido só com base | Nenhum | P | ALTA |
| P13 · U16 · P52 | Tirar o "Começar" do Simulado e o "8.462"; o simulado curto vira o compilado de 10 e 20 | Simulado | Nenhuma questão de outra banca ou de prova recusada no acerto | O compilado também começa pelas inéditas do alvo (`servico/compilado.py:168-179`), como o P12: só com a mesma trava; muda os tamanhos 40/50/100 (fase 4 e especificação) | P | ALTA |
| U05 | O "Agora" vira atalho para a faixa e para "Como foi o dia"; "Fiz em DD/MM" no dia passado | Hoje, Meu foco | Às 19:30 a faixa em 1 clique, sem rolar ~1.579 palavras da coluna (1.790 no celular) | Nenhum | P | ALTA |
| U06 | A rodada, o relatório e a ficha voltam para a faixa | Rodada, relatório, ficha | Um clique e estou no "Fiz" e no "Anotar erro" | Nenhum | P | ALTA |
| U07 | O treino de IA da faixa num `<details>` com 🟣 e "treina, não mede"; sai "Você estudou…" | Hoje | −~770 palavras e −13 botões; o que mede fica à vista | Nenhum (selo e frase no resumo); muda a 112 | P | ALTA |
| U08 · P33 | Uma linha e uma ordem para "onde fazer"; sem "são as que medem" nas faixas com consulta | Hoje, ficha | Sei por onde começar; a fixação com consulta deixa de "medir" | Melhora; muda a 112 (texto) | P | ALTA |
| U10 | Lei seca com o porquê de cada artigo na faixa e o selo do plano | Hoje | Ler os incisos sabendo por quê, sem rebaixar o dia | Nenhum | P | ALTA |
| U11 · P19 | O Meu desempenho abre pela fila: 8 pontas, o botão "Fazer as revisões de hoje" e as erradas | Meu desempenho | A revisão do dia sem rolar; 8 lá = 8 cá | Nenhum; muda a 128 no Meu desempenho | P | ALTA |
| U12 | Âncoras na ficha (o que estudar / questões) pelo tipo da faixa | Ficha, Hoje | A ficha abre no que preciso naquela hora | Nenhum | P | ALTA |
| U13 | Tirar da ficha a lista dos 44 enunciados de geradas | Ficha | −754 palavras (24% da ficha) | Nenhum (fica a contagem com 🟣 e a frase oficial) | P | ALTA |
| U14 | Anotar erro: regra e motivo no topo, o resto num `<details>`, o seletor só no ramo da matéria | Anotar erro | Anotar vira 2 campos e o botão | Nenhum | P | ALTA |
| U15 · P18 | Tirar do Simulado "Como você vai até agora" e "Nas questões geradas" | Simulado | Some o acerto sem amostra pintado de vermelho | Reduz; muda "A tela das geradas" | P | ALTA |
| U17 · P21 | Na gerada, o artigo só depois de responder; "Essa questão está errada" embaixo, em 2 passos | Rodada | O treino não entrega a resposta; um clique perdido não apaga histórico | Nenhum para o acerto; muda a decisão "Questão gerada não tem status não revisada" (26/09), cujo motivo é o artigo à vista: ele vai para o relatório, com o link da lei | P | ALTA |
| U19 · P26 | Tirar dos Macetes o "Padrão da banca" e as "Palavras que mais aparecem"; link para a Incidência | Macetes | Some um "padrão" sem amostra | Nenhum; muda o formato do cartão (especificação) | P | ALTA |
| P09 | A frase do "não estudei" verdadeira, o aviso na home e o erro do caderno ligado à matéria na fila | Meu desempenho, Meu foco, Caderno | O 1-7-30 de Penal e Constitucional anda; a tela para de afirmar o falso | Nenhum sem mudar decisão (ou o ajuste do P01) | M | ALTA |
| U20 | "Revisão de hoje" igual no Hoje e na home: fila com o botão, caderno e R+7, nunca somados | Hoje, Meu foco, Caderno | A revisão do dia inteira onde passo o dia (~44 → ~31 cliques, 1 tela) | Nenhum (contagens lado a lado); muda a "home de 3 blocos" | M | ALTA |
| U21 · P36 | O erro chega ao caderno ligado ao nó; "Anotar erro" em cada erro do relatório | Hoje, relatório, Anotar erro | O erro volta na revisão do assunto; o 17/10 sem a matéria "Diagnósticos" | Nenhum | M | ALTA |
| U22 | Ficha: "O que estudar" logo abaixo do "caiu"; texto completo e "Por que agora" em `<details>` | Ficha | O que ler sai da palavra 874 para o topo | Nenhum (procedência no resumo) | M | ALTA |
| P16 · U24 | Topo e lateral do Hoje só com o que é de agora (sai o "1h55" e as repetições; Mapa do ano fechado) | Hoje | No celular o dia começa logo; some um número enganoso | Nenhum | P | MÉDIA |
| P17 | A projeção como "~6 de 15 (só LP)" ou "Amostra insuficiente em 10 de 11" | Minhas matérias | O número grande informa em vez de desanimar | Nenhum (dentro da E4) | P | MÉDIA |
| P20 | O rótulo de "medido no radar" diz o recorte (respostas × questões) | Minhas matérias | 67% × 38% não aparece sem explicação na primeira revisão | Nenhum | P | MÉDIA |
| P22 | Guardar o artigo inteiro da gerada | (gravação) | A regra da questão não chega cortada | Passo novo no `migracoes.py` | P | MÉDIA |
| P24 | Agrupar pelo nome do edital (Processual Penal) no Edital, no Simulado e em Gerar | Edital, Simulado, Gerar | O Edital para de dizer que não caiu Processo Penal em 2013 | Nenhum (cumpre a 97) | P | MÉDIA |
| P25 | Pegadinha e tipo de IA com 🟣 ou fora da lista; "conferido pelo Claude Code" escrito | Ficha, Incidência, Conferência | Texto de IA não passa por estatística das provas | Muda a 109 para as não conferidas | P | MÉDIA |
| P30 | Plano e tela dizem o mesmo sobre o que decide o Ciclo 2 e o que fica fora do acumulado | Hoje 07/11, `cronograma.yml` | A decisão do Ciclo 2 com a base certa | Repartir os simulados por matéria mudaria a E2 | P | MÉDIA |
| P31 | "Amostra insuficiente (11 de 20)" no lugar do % grande; a divisão radar/anotado sempre | Minhas matérias | 55% de 11 deixa de parecer medida firme | Nenhum | P | MÉDIA |
| P32 | "Refazer os 11" monta 11 (ou diz "10 dos 11") | Simulado, home, relatório, Meu desempenho | O botão faz o que diz | Nenhum | P | MÉDIA |
| P34 · U43 | Comando de terminal fora da vista no estudo; a ficha usa o N da faixa | Ficha, relatório, Edital, Fichas | A manutenção sai do caminho; nada de 40 geradas a mais | Nenhum | P | MÉDIA |
| P35 | "1 resposta sem consulta; o mínimo é 6" | Ficha | Sem ler "1 de 6" como acerto | Nenhum | P | MÉDIA |
| P37 | Siglas PMF/PMBC traduzidas pela configuração (`regioes.yml`) | Edital, Concursos | O "De olho" avisa a próxima Guarda | Regra no config, nunca no código | P | MÉDIA |
| U23 | O tema uma vez por dia (árvore e "caiu" só na 1ª faixa do tema) | Hoje | −142 palavras; aparece o que muda entre as faixas | Nenhum; muda a decisão 71 | P | MÉDIA |
| U25 | Sábado: o botão da rodada antes da composição (em `<details>` com a amostra no resumo) | Hoje (sábados) | ~8.700 palavras de rolagem a menos no sábado | Nenhum (amostra e frase a 1 clique) | P | MÉDIA |
| U26 | A Correção mostra os resultados das rodadas do dia e tem "Anotar erro" | Hoje | Corrijo onde o plano manda | Nenhum | P | MÉDIA |
| U27 | Revisão semanal: (1) e (2) numa lista, "N erradas no radar → Refazer", artigos-chave dobrados | Hoje (sábados) | O passo (1) do plano vira ação | Nenhum | P | MÉDIA |
| U28 | O alvo e "Concurso" numa linha no fim da home; "Sua evolução" vira link | Meu foco | A home volta a caber em 1366×680 | Nenhum; muda a "home de 3 blocos" | P | MÉDIA |
| U29 | O motivo da revisão com uma data e um número | Meu foco, Meu desempenho | Sem "(1 dia(s)) · atrasada 6 dia(s)" | Nenhum | P | MÉDIA |
| U30 | Edital com Matérias e "Onde estudar primeiro" no topo | Edital | O que planejo na primeira tela | Põe à vista o "não treinei" (P01): corrigir antes | P | MÉDIA |
| U31 | Minhas matérias: matérias com dado no topo; "Ainda não estudei" numa linha por ciclo | Minhas matérias | A evolução por matéria na primeira tela | Nenhum | P | MÉDIA |
| U32 | Incidência: cada matéria num `<details>` com a linha-resumo | Incidência | Abre com 13 linhas (~400 palavras, não 9.129) | Nenhum (amostra no resumo) | P | MÉDIA |
| U33 | Incidência: pendentes e anuladas listadas com código e artigo | Incidência | Não descarto tema por "não apareceu" com pendente | Nenhum (cumpre a 108) | P | MÉDIA |
| U34 | A Conferência abre no que falta (contadores como links) | Conferência | A pendência B.8 a 1 clique, numa página de ~200 palavras | Nenhum (o P06 antes) | P | MÉDIA |
| U35 | Simulado: pesos e "Suas rodadas" dobrados; "10/10 e 07/11 começam no Hoje" | Simulado | Não monto a rodada errada no sábado | Nenhum | P | MÉDIA |
| U36 · P43 | Relatório: só o resultado antes dos erros; sai a legenda "a correta do gabarito" | Relatório | O primeiro erro sobe; a resposta da IA não vira gabarito | Muda em parte a decisão da fase 3 | P | MÉDIA |
| U37 | Gerar questões: "Treinar com as que já tenho" em 1º, nos nós de hoje | Gerar questões | Treino sem passar pelo cartão da API | Nenhum; muda "A tela das geradas" | P | MÉDIA |
| U38 | "Os assuntos do cronograma" só com os nós sem gerada, com a data | Gerar questões | −~650 palavras; o que gerar para amanhã primeiro | Nenhum; muda a 115 | P | MÉDIA |
| U39 | Caderno: os erros logo depois do título | Caderno | Os botões de revisar sobem | Nenhum | P | MÉDIA |
| U40 | Botão "Arquivar (não é regra)" no erro | Caderno | Relato de sessão sai da fila | Nenhum (o histórico guarda) | P | MÉDIA |
| U41 | Fichas do dia: um cartão por tema | Fichas | −2 de 5 cartões | Nenhum; muda a 111 | P | MÉDIA |
| U42 | O estado da conferência (ficha e resumo) no cartão e na lista | Fichas | Sei o que falta conferir dos temas da semana | Nenhum | P | MÉDIA |
| U44 | Semanas: a linha do ciclo atual, com link para a comparação de 07/11 | Semanas | "Evoluo no ciclo?" numa linha | Nenhum | P | MÉDIA |
| U45 | O método das telas de análise num `<details>` "Como esta tela conta", com um chip à vista | Meu desempenho, Edital, Incidência, Minhas matérias, Semanas | −465 palavras só no Meu desempenho | Nenhum (o chip leva selo e regra) | P | MÉDIA |
| U46 | Macetes: atalhos por matéria e os macetes em `<details>` | Macetes | A matéria do dia a 1 clique (~1.000 palavras, não 5.953) | Nenhum | P | MÉDIA |
| U47 | "O costume de qualquer banca" em página própria | Macetes, Mais | Macetes só com a minha prova | Nenhum | P | MÉDIA |
| I6 | Ler a explicação dos erros de 10/10 antes do R+7 de 17/10 | `cronograma.yml` | O R+7 vira reteste de verdade | Texto de IA com 🟣; vale o gabarito oficial | P | MÉDIA |
| I7 | O Hoje abre na faixa de agora (`/hoje#agora`, posto pelo servidor) | Hoje | Zero clique e zero rolagem ao abrir | Nenhum | P | MÉDIA |
| I8 | Teste que segura a limpeza (as regras presentes + teto de palavras) | `tests/` | A tela limpa continua honesta | Nenhum | P | MÉDIA |
| P23 | Sortear e contar o alvo pela chave; "162 válidas (sem as 8 anuladas)" | Meu foco, Edital | 10 questões do cargo deixam de ficar presas | Nenhum | M | MÉDIA |
| P27 | "Pegadinha" sem "recorrente", com "(N questões · M provas)" | Macetes | Sem padrão sem base | Muda o formato do cartão de macete | M | MÉDIA |
| P28 · U50 | Um cartão por matéria da árvore nos Macetes, com a base da Incidência | Macetes | Um número por matéria no site; nenhum macete escondido | Muda a decisão da Central de Macetes (25/09) | M | MÉDIA |
| P29 | Contar as "provas" do complementar por concurso | Incidência, Fichas, ficha | "26 provas" deixa de ser 1 concurso; o mínimo dos padrões fica honesto | Muda a decisão 14 da 3B | M | MÉDIA |
| U48 | Meu desempenho: uma tabela por nó | Meu desempenho | −~400 palavras | Nenhum; muda a forma da 79 | M | MÉDIA |
| U49 | Ficha: "caiu" e "como cobrou" num cartão; "Revisão e desempenho" noutro | Ficha | A errada no radar vira ação | Nenhum | M | MÉDIA |
| U51 · P53 | Gerar: o cartão da API vira os 3 passos com o comando exato | Gerar questões | A porta que funciona no lugar da fechada | Reduz; cumpre a 114 | M | MÉDIA |
| U52 | Um rótulo por ação (refazer, treinar, começar, voltar…) | Todas | Questão real e gerada com nomes diferentes | Nenhum | M | MÉDIA |
| U53 | Um nome por conceito (matéria > assunto > subassunto; as quatro revisões; simulado × treino) | Todas | Não confundo revisão, treino e medida | Nenhum | M | MÉDIA |
| U54 | Selo só para origem; a frase padrão com uma cara só; legenda dos selos curtos | Várias | O selo volta a dizer só de onde vem o dado | Nenhum | M | MÉDIA |
| P38 | Semanas: "−4h50" e "+27 pontos" | Semanas | Leio a semana sem conta | Nenhum | P | BAIXA |
| P39 | Réguas e contas fora dos templates; o teste olha também / e * | Meu foco, relatório, Macetes | Mudar o `amostra.yml` não separa as telas | Nenhum | P | BAIXA |
| P40 | A meta do Hoje sai da soma das metas | Hoje | Um lugar para mudar a meta | Nenhum | P | BAIXA |
| P41 | "quase sempre" só com 3 erros ou mais | Minhas matérias | Sem padrão de 1 erro | Nenhum | P | BAIXA |
| P42 | "10 de 10 em 1 prova (2019)" | Edital | Vejo que a fatia é de uma prova | Nenhum | P | BAIXA |
| P44 | A procedência no `title` do selo roxo (aviso de lei) e o modelo no relatório | Macetes, fichas, relatório | Sei quem escreveu o aviso e a questão | Nenhum | P | BAIXA |
| P45 | Selo azul na Incidência, pela origem gravada | Incidência, Meu foco | O selo diz de onde vem a contagem | Nenhum | P | BAIXA |
| P46 | Treino de IA com 🟣 e "conta no volume" em Minhas matérias e Semanas | Minhas matérias, Semanas | A mesma frase nas quatro telas (decisão 127) | Nenhum | P | BAIXA |
| P47 | Selo do plano nos artigos-chave da semana | Hoje (sábados) | Um selo para o mesmo dado | Nenhum | P | BAIXA |
| P48 | Salário do Calendário com a origem | Calendário | Lido do anúncio ≠ anotado por mim | Nenhum | P | BAIXA |
| P49 | O aviso da faixa separa as respostas de outro dia | Hoje | Caso de borda sem texto enganoso | Nenhum | P | BAIXA |
| P50 | "no plano em DD/MM · não marcado" no lugar de "estudado em" | Hoje (sábados) | A composição não afirma estudo que não houve | Nenhum (a 69 fica) | P | BAIXA |
| P51 | Contadores do que falta conferir iguais à lista | Incidência, Conferência | Sei quanto falta de verdade | Nenhum | P | BAIXA |
| P54 | "170 questões (162 na Central; 8 anuladas)" | Macetes | O número fecha com a tela de cima | Nenhum | P | BAIXA |
| P55 | "30 de 188" no lugar de "30 de 2878" | Concursos | O denominador é o do filtro | Nenhum | P | BAIXA |
| P56 | Encerrado sem prazo aparece como encerrado | Concursos | Concurso de 2006 não parece aberto | Nenhum | P | BAIXA |
| P57 | A Previsão conta só concurso (não seletivo) | Previsão | A data prevista vale para concurso | Nenhum | P | BAIXA |
| U55 | Menos frases que explicam o sistema | Hoje, Meu foco, Fichas, Gerar, ficha | Menos regra a ler a cada abertura | Nenhum (selos e amostras ficam) | P | BAIXA |
| U56 | Consultas com dado e botão no topo, instrução dobrada | Calendário, Previsão, Acompanhando, Mais | Cada consulta responde em uma linha | Nenhum | P | BAIXA |
| U57 | Previsão: os 12 municípios de um ano só numa linha | Previsão | 23 cartões viram ~11 | Nenhum | P | BAIXA |
| U58 | Banca e tipo na linha do concurso; atalho "Segurança pública" | Concursos | Separo seletivo e acho o alvo num olhar | Nenhum | P | BAIXA |
| U59 | Um caminho por tela (Caderno fora das sub-abas do Hoje, Macetes com sub-abas, Conferência em Mais) | Barra e sub-abas | O clique não troca de seção sem aviso | Nenhum; muda a decisão 6 da 3A e o sitemap da 7B | P | BAIXA |
| U60 | Textos menores (um nome para a marca de favorito, "não sei ainda", acentos, plural) | Várias | Cada nome diz o que é | Nenhum | P | BAIXA |
| U61 | Questões de um macete: título e volta certos | Macetes | Volto ao cartão de onde saí | Nenhum | P | BAIXA |
| I9 | Fixação e Aprendizagem: responder de cabeça e abrir a lei só para conferir | `cronograma.yml` | Cada dúvida vira recuperação, não chute | Nenhum; muda o texto da 6A, com a sua aprovação | P | BAIXA |
| U62 | Um "Treinar no radar" por faixa, com todos os nós | Hoje | Um clique e uma rodada para o treino da faixa | Nenhum; muda a 112 | M | BAIXA |
| U63 | Resposta comprimida (gzip) e um formulário de editar só | Hoje | 246 → 33 KB por abertura (496 → 59 KB em 05/10) | Nenhum; sem dependência nova | M | BAIXA |
| U64 | Subir ao `design.css` o que se repete; tirar as classes mortas | Todas | Menos CSS para manter sozinho | Nenhum | G | BAIXA |

## 7. O fluxo ideal do meu dia

**Como fica o dia com o desenho da seção 8:**
1. **Abrir** (pelo `Radar.bat`, em `/hoje`, ou por `localhost:8000`, em `/`): o primeiro cartão é a faixa da hora, inteira, com o tema, a linha "📌 no plano de hoje · 🔵 alvo: caiu em 2013 — 1 questão · 1 prova" e os botões da faixa. A home mostra a mesma faixa ("Agora no plano") e a "Revisão de hoje" — nunca uma lista que contradiga o plano.
2. **Manhã:** teoria (📋 Ficha abre em "o que estudar"), fixação, lei seca com o porquê de cada artigo, Português; a fixação feita no radar começa no próprio painel ("▶ Começar as 6 reais do radar"), e a rodada volta para a faixa, que fecha com "✓ Feita no radar".
3. **Ficha ou resumo do tema:** a 1 clique do painel; a ficha abre na seção certa e tem "← voltar à faixa" no topo.
4. **Noite:** às 18:00 o painel é o R+7 (com "7 de Direito Constitucional + 3 de Português" à vista); às 19:15, "1º ▶ Começar as 7 reais do radar → 2º Qconcursos, as outras 3 → fiz no Qconcursos [3]"; às 19:40, a Correção com "📓 Anotar erro" e os vencidos do caderno para lembrar.
5. **Revisão do dia:** a caixa "🧠 Revisão de hoje" (fila 1-7-30 com o botão, caderno e R+7, cada um com o seu número, nunca somados).
6. **Fechar o dia:** depois da última faixa, "Como foi o dia" sobe para o lugar do painel, com o "Fiz hoje" e o que ficou "○ sem marca" em links.

**Cliques e rolagem, hoje e no desenho proposto.** "Rolagem" é quantas palavras visíveis eu passo até achar o que preciso. Os números de hoje vêm da contagem na cópia; os propostos, do protótipo medido com a mesma régua (marcados com ~ quando são estimativa).

| Passo | Hoje | Proposto | O que muda |
|---|---|---|---|
| a) Abrir e saber o que estudar e por quê | 0 clique para o quê; 1 a 2 para o porquê, que está na palavra 732 da ficha (~1.200 palavras de rolagem). Pela home, uma lista concorrente logo abaixo. | 0 clique; o quê e o porquê curto na primeira tela, pelas duas entradas; 1 clique para os fatores completos ("por que hoje →") | O porquê sobe da ficha para a faixa; some a lista que manda estudar outra matéria |
| Manhã inteira (teoria → fixação → lei seca → Português → fixação no radar) | ~12 cliques + 1 campo; o botão da rodada de 6 na palavra 1.008; a fixação feita no radar não fecha | ~13 cliques (um a mais: o "✓ Feita no radar", que hoje não existe) + 1 campo; ~0 de rolagem na hora de cada faixa | As 5 faixas ficam marcadas e o dia pode chegar a Ideal |
| b) Abrir a ficha ou o resumo | 1 clique (+1 para fechar ou voltar, caindo no topo do dia); 442 palavras até o link | 1 clique, na primeira tela; a volta cai na faixa | Ficha na seção certa; volta para onde eu estava |
| c) Noite: as questões da faixa e anotar | Faixa de Português: 10 cliques + 2 campos; noite inteira: 15 cliques + 4 campos e ~3.900 palavras de rolagem | Faixa de Português: 10 cliques + 1 campo; noite inteira: 15 cliques + 3 campos e ~0 de rolagem na hora certa | A faixa da hora no topo; a rodada volta para ela; o "fiz" só pede o Qconcursos |
| d) Revisão do dia (R+7, R+30, erros) | ~44 cliques (35 são respostas) em 3 telas, com 4 números para "revisar hoje" (2, 8, 11, R+7 de 10) | ~31 cliques + 1 campo numa tela, com 3 números com nome, nunca somados | Some a rodada que refazia as mesmas 10 erradas; a fila da decisão 128 aparece no Hoje |
| Fechar o dia | 2 cliques; "Como foi o dia" a ~1.771 palavras na coluna | 2 cliques; no topo depois da última faixa | Sem rolagem para fechar |
| e) Sábado 10/10 (revisão semanal, diagnósticos e simulado) | ~52 cliques (40 respostas) + 1 campo, dos quais 3 são da revisão semanal (abrir os erros da semana, voltar, ✓); ~9.700 palavras de rolagem no dia; o "fiz" vem com 20 | ~54 cliques (+2 "✓ Feita no radar"); ~0 de rolagem por faixa feita na hora (estimativa: o sábado não foi prototipado) | O botão antes da composição; Reduzida e Plano B não apagam a medição |
| e) Sábado 17/10 (R+7 dos diagnósticos) | Não contei: a cópia não tem rodada de 10/10, e o botão "Criar a rodada com os erros" só aparece com ela (`hoje.html:1172-1199`). O que se vê: o "fiz" vem com 40, e um clique grava 40 questões não feitas | 1 + N respostas + 2 cliques (N = erros de 10/10, não medido), sem "fiz" pré-preenchido | Sem número falso |
| e) Sábado 07/11 (fechamento) | ~61 cliques no dia (52 no simulado); o botão na palavra ~2.090, depois de ~900 palavras de composição | ~53 cliques no simulado (+1, o "✓ Feita no radar"); ~0 de rolagem (estimativa) | O fechamento sem questão repetida do diagnóstico (P07) |
| f) Ver se estou evoluindo | 1 a 2 cliques por matéria e por semana; a comparação de 07/11 sem link (32 cliques em "próximo dia") | 1 clique para cada (matéria, semana, ciclo e a comparação de 07/11) | A seta só com amostra; a comparação a 1 clique |

**Em resumo:** os cliques quase não mudam — a maior parte deles é responder questão, um clique cada. O que cai é a **rolagem** (à noite, de ~3.900 palavras para ~0 na hora certa; no sábado, de ~9.700 para ~1.000, estimativa: o sábado não foi prototipado, e ~1.000 é o que a proposta B mediu num render derivado) e, mais importante, o **risco de anotar errado** (o "fiz" com o número do plano, a Reduzida que apaga a medição).

## 8. Rascunho do Hoje e do Meu foco

**Como este desenho foi escolhido.** Três propostas independentes, por três ângulos: *a ação de agora primeiro* (menos cliques e rolagem), *uma resposta por pergunta, com a fonte à vista* (precisão primeiro) e *o ciclo do estudo* (aprender → praticar → corrigir → revisar → medir). Um juiz deu nota de 0 a 10 em precisão, ruído, cliques, viabilidade e estudo:

| Proposta | Precisão | Menos ruído | Cliques | Viabilidade | Estudo |
|---|---:|---:|---:|---:|---:|
| A — a ação de agora primeiro | 9 | 9 | 9 | 6 | 7 |
| B — uma resposta por pergunta | 8 | 7 | 7 | 5 | 7 |
| C — o ciclo do estudo | 8 | 6 | 8 | 4 | 9 |

A base é a **A**: é a que mais corta, a única cuja home não destaca número de acerto enquanto P01, P02 e P08 estão em aberto, e a que põe a faixa da hora e o botão que começa na primeira tela do notebook às 07:00 e às 19:30. Das outras duas vieram os enxertos de precisão e de método: o R+7 dividido (P04), a composição que não repete o diagnóstico (P07), a Reduzida de sábado que mantém a medição (P14), o "fiz no Qconcursos" e o "✓ Feita no radar" (P03), as notas no "caiu" (P10), a seta só com amostra (P11), a linha do R+7 na "Revisão de hoje", o "Hoje mede: …" no sábado e o Mapa do ano na tela Semanas.

**A ideia central do Hoje:** um **painel com a faixa da hora**, inteira, no topo da coluna; as outras faixas viram **uma linha cada** ("▸", que abre a faixa no mesmo molde do painel); e o servidor escolhe o que vai no painel pela hora — nenhum JavaScript novo. A proposta A foi prototipada em HTML estático, com o texto real de 06/10 e o CSS do projeto, e medida com a mesma régua:

| Tela | Palavras visíveis | Cartões | Botões | Dobras | Frases |
|---|---:|---:|---:|---:|---:|
| Hoje 07:00 — hoje | 2.104 | 14 | 52 | 12 | 70 |
| Hoje 07:00 — proposto (protótipo; ~450 com os enxertos) | 441 | 7 | 8 | 14 | 25 |
| Hoje 19:30 — hoje | 2.107 | 14 | 52 | 12 | 70 |
| Hoje 19:30 — proposto (protótipo; ~425 com os enxertos) | 415 | 7 | 9 | 15 | 23 |
| Meu foco — hoje | 295 | 6 | 5 | 0 | 16 |
| Meu foco — proposto (protótipo; ~212 com a linha 🩺) | 190 | 4 | 5 | 0 | 13 |

Às 19:30, o botão "▶ Começar as 7 reais do radar" fica na palavra 26 da coluna (hoje, ~1.579); o "Como foi o dia", na 285 (hoje, ~1.771); a home termina em ~630 px e cabe em 1366×680 (hoje, ~770 px). É protótipo, não template: as linhas fechadas ainda carregam a faixa inteira no HTML (o peso cai com a compressão, U63), e o sábado não foi prototipado.

**Legenda:** `[ ]` botão · `( )` chip ou selo · `▸` `<details>` fechado (o resumo fica sempre visível) · `▶` cronômetro da faixa (só com JS, já existe) · `(✓)` círculo de marcar · `○` faixa sem marca · `↓ / →` âncora ou link · `↑ agora` a linha da faixa que está no painel · `~~~` fim da primeira tela em 1366×680 · 🟢 oficial · 🔵 acervo · 🟡 automático · 🟣 IA · 📌 seleção do plano · DC = Direito Constitucional · N = número que só existe depois do dado gravado.

### 8.1 Hoje às 07:00 (notebook)

```
NOTEBOOK ≥ 1100 px · terça 06/10 · 07:00 · nada marcado na cópia
┌─ barra ─ Radar  📅 Hoje · 🎯 Meu foco · 📚 Estudar · 🧠 Revisão · 📊 Análises · 🏛 Concursos · ⚙ Mais  ☀️
├─ herói compacto (faixa azul)
│ Terça, 6 de outubro                                  [← dia anterior] [Hoje] [próximo dia →]
│ Ciclo 1 — a base · Semana 2 de 6 · termina em 32 dias
│ (⚡ Nível 1) (🔥 1 dia seguido) (🎯 Meta 79 de 100 📌)
└─ (Hoje) (Semanas) (Fichas)                 ← sai a sub-aba "Caderno de erros"

COLUNA PRINCIPAL                                                   LATERAL (300 px, fixa)
┌─ #agora (fora de dobra; mantém #faixa-manha-0 e os data-*) ──┐   ┌─ ⏱ Cronômetro (só com JS)
│ PRÓXIMA ÀS 10:15            depois: 10:55 Fixação · 8         │   │   ▸ testar o aviso
│ 10:15–10:55 ▶ 📖 Teoria (Direito Constitucional) (Videoaula) (✓)│   ├─ 🧠 REVISÃO DE HOJE · fora das faixas
│ Art. 5º, incisos XVII a XLIX                                  │   │ 🟡 8 conteúdos vencidos na fila 1-7-30
│ Teto de 40 min, uma fonte só: passou do tempo, siga para a    │   │    (até 24 questões reais)
│ fixação. Associação (XVII a XXI); propriedade e função social │   │    [Fazer as revisões de hoje]
│ (XXII a XXVI); … integridade física e moral do PRESO (XLIX).  │   │ 📓 2 erros do caderno, vencidos desde
│ [⚖️ Ler no Planalto]  📋 Ficha · 📝 Resumo · por que hoje →    │   │    30/09  [abrir →]
│ 📌 no plano de hoje · 🔵 alvo: caiu em 2013 — 1 questão ·     │   │ 📌 R+7 às 18:00 · Art. 5º, caput e
│    1 prova (2013: 1 · 2019: 0)                                │   │    I a XVI ↓
│ ▸ 🟣 Onde na árvore: 1 assunto · 4 subassuntos                │   │ (Penal e Constitucional fora da fila até
└───────────────────────────────────────────────────────────────┘   │  conferir as fichas — só se vier de conta)
~~~~~~~~~~~~~~~~~~~~~~ fim da 1ª tela em 1366×680 (captura de A) ~~~~~~~~~~~├─ ESTA SEMANA
┌─ #o-dia  O dia · 49 questões · termina às 20:05   ▸ 🆘 Plano B ─┐   │ Seg 5 [Ter 6] Qua 7 Qui 8 Sex 9 Sáb 10 🩺
│ Manhã · 10:15 – 12:30 · 14 questões                           │   │ 🔥 Faça 5 dias completos e a semana que
│    10:15 📖 Teoria · Art. 5º, XVII a XLIX · Videoaula  ↑ agora │   │   vem sobe para 20 questões de Direito.
│  ▸ 10:55 🎯 Fixação · Art. 5º, XVII a XLIX · 8 · Qconcursos ·  │   │ [minhas matérias →]
│          com consulta                                     ○   │   └──
│          11:15 ☕ pausa 10 min                                 │
│  ▸ 11:25 ⚖️ Lei seca · CF art. 5º, XLIII; XLVII; XLVIII e XLIX ○│
│          11:45 ☕ pausa 10 min                                 │
│  ▸ 11:55 ✍️ Português · Concordância verbal 1: regra geral ·   │
│          Videoaula                                        ○   │
│  ▸ 12:15 🎯 Fixação · Concordância verbal 1 · 6 no radar   ○   │
│ Noite · 18:00 – 20:05 · 35 questões                           │
│  ▸ 18:00 🔁 R+7 · Art. 5º, caput e I a XVI · 7 de DC + 3 de    │
│          Português · Qconcursos                           ○   │
│  ▸ 18:25 🎯 Aprendizagem · Art. 5º, XVII a XLIX · 15 ·         │
│          Qconcursos · com consulta                        ○   │
│          19:05 ☕ pausa 10 min                                 │
│  ▸ 19:15 🎯 Questões · Concordância verbal 1 · 7 no radar +    │
│          3 no Qconcursos                                  ○   │
│  ▸ 19:40 📝 Correção · 25 min                              ○   │
│  ▸ Depois das 22h · 🌙 sobreaviso · ANKI temporariamente       │
│    desativado            (fechado; o Bônus fica dentro)       │
└───────────────────────────────────────────────────────────────┘
┌─ #como-foi  Como foi o dia
│ ( ) ✅ Ideal ( ) 🟦 Reduzida ( ) 🟨 Mínima ( ) ❌ Não fiz  [Salvar]  ▸ anotação
└──
▸ ➕ Estudo extra · fora das faixas do plano; não muda a meta
```
Dentro dos ▸ (nada apagado, tudo a 1 clique):
- Linha de faixa aberta = a faixa inteira no molde do painel. Ex. 10:55: 'Qconcursos: Direito Constitucional > direitos e deveres individuais e coletivos' (com consulta · fora da meta) · fiz no Qconcursos [8] acertei [ ] ☑ com consulta [✓ Fiz] · 📓 Anotar erro · 📋 Ficha · 📝 Resumo · ▸ '🟣 Treinar mais no radar · 44 geradas · gerada por IA: treina, não mede' com um botão só [🟣 Treinar 8 geradas]; nó sem gerada: 'Sem gerada em `<nó>`: Gerar questões →'.
- 12:15 (toda no radar): [▶ Começar as 6 reais do radar] · 🔵 '6 reais da FEPESE deste tema que você ainda não respondeu' · sem fiz; com a rodada completa, [✓ Feita no radar] (grava só os minutos).
- 11:25 lei seca: 📌 XLIII — tortura, tráfico, terrorismo e hediondos: inafiançáveis e insuscetíveis de graça ou anistia; XLVII — as penas proibidas; XLVIII e XLIX — estabelecimento distinto; integridade do preso. O title do 📌 diz 'seleção do plano, feita do texto da lei: não é o que a banca mais cobra'. Sai 'O porquê de cada um está no Plano B do dia'.
- ▸ Onde na árvore: Assunto: Direitos e garantias fundamentais: direitos e garantias individuais e coletivos · Subassunto: Liberdade de associação; Tribunal do júri; Princípios constitucionais penais; Crimes inafiançáveis e imprescritíveis · Elemento: CF, art. 5º, incisos XVII a XLIX (inciso). Procedência da ficha no title.
- ▸ 🆘 Plano B: 'Quanto tempo você tem? [30 min] [1 hora]' + '🟦 Reduzida: A manhã inteira + só as 15 questões de Direito Constitucional à noite.' + '🟨 Mínima: Plano B: os artigos-chave + questões de prova de: Art. 5º, incisos XVII a XLIX.' (o cartão 'Se o dia apertar' deixa de existir).
- 'por que hoje →' abre /fichas/art-5o-incisos-xvii-a-xlix?data=2026-10-06#por-que-agora (o h2 ganha o id).
Medido no protótipo A (antes dos enxertos): 441 palavras visíveis, 7 cartões, 8 botões, 14 dobras, 25 frases; título da faixa na palavra 21 da coluna. Com os enxertos (linha do R+7 na revisão, Mapa do ano fora): ~450, estimativa à mão.

### 8.2 Hoje às 19:30 (notebook)

```
NOTEBOOK ≥ 1100 px · 06/10 · 19:30 · herói, sub-abas e lateral iguais às 07:00
┌─ #agora ── (#faixa-noite-3, data-* do cronômetro) ───────────────────────┐
│ AGORA 19:30 · EM ANDAMENTO                       depois: 19:40 Correção  │
│ 19:15–19:40 ▶ 🎯 Questões (Língua Portuguesa) (sem consulta) 10 questões │
│ Concordância verbal 1: regra geral                                       │
│ 1º [▶ Começar as 7 reais do radar]                                       │
│    🔵 7 reais da FEPESE deste tema que você ainda não respondeu           │
│ 2º Qconcursos, as outras 3: procure pelo nome do tema                    │
│    "Concordância verbal 1: regra geral"                                  │
│ fiz no Qconcursos [3] acertei [  ] ☐ com consulta  [✓ Fiz]               │
│ 📓 Anotar erro · 📋 Ficha · 📝 Resumo                                     │
│ 📌 no plano de hoje · 🔵 alvo: caiu em 2013 — 1 questão · 1 prova        │
│    (2013: 1 · 2019: 0) · por que hoje →                                  │
│ ▸ 🟣 Treinar mais no radar · 15 geradas · gerada por IA: treina, não mede │
│ ▸ 🟣 Onde na árvore: Concordância nominal e verbal › Concordância verbal │
~~~~~~~~~~~~~~~~ fim da 1ª tela em 1366×680 (captura de A) ~~~~~~~~~~~~~~~~
│ ○ sem marca: 18:00 R+7 ↓ · 18:25 Aprendizagem ↓ · e 5 da manhã ↓          │
└──────────────────────────────────────────────────────────────────────────┘
┌─ O dia · 49 questões · termina às 20:05                     ▸ 🆘 Plano B
│ Manhã · 10:15 – 12:30 · 14 questões   (5 linhas, cada uma '○ sem marca')
│ Noite · 18:00 – 20:05 · 35 questões
│  ▸ 18:00 🔁 R+7 · Art. 5º, caput e I a XVI · 7 de DC + 3 de Português ○ sem marca
│  ▸ 18:25 🎯 Aprendizagem · Art. 5º, XVII a XLIX · 15 · Qconcursos ·
│          com consulta                                         ○ sem marca
│          19:05 ☕ pausa 10 min
│    19:15 🎯 Questões · Concordância verbal 1 · 7 no radar + 3 Qconcursos ↑ agora
│  ▸ 19:40 📝 Correção · 25 min                                  ○
│  ▸ Depois das 22h · 🌙 sobreaviso · ANKI temporariamente desativado
└──
Como foi o dia · ▸ ➕ Estudo extra   (iguais às 07:00)
```
Estados do painel (o servidor escolhe; nenhum JS novo):
- Depois de responder as 7: o 1º vira '✓ 7 respondidas no radar (reais): já contam no Fiz hoje · [▶ Abrir a rodada]'; o fiz continua 'fiz no Qconcursos [3]'.
- 18:00: o painel é o R+7, com o detalhe aberto: '7 questões NOVAS de Direito Constitucional … + 3 de Português: artigo, numeral e pronome (classificação)'. De 07/10 em diante (enxerto, com sua aprovação) são duas faixas, cada uma com seu fiz.
- 19:40: Correção com o detalhe aberto ('Leia o comentário de TODO erro e copie no caderno de erros: a questão, por que errou e a regra certa.') e [📓 Anotar erro] na faixa.
- 20:05 em diante: o painel é 'Como foi o dia' (Fiz hoje com 'medido no radar: X% em N · anotado: Y% em M' e '🟣 Treino de IA: … fora do acerto real; conta no volume', as 4 metas, [Salvar], '○ sem marca' em links). Nunca aponta o Bônus opcional das 22h.
- A rodada aberta pela faixa volta por '← Voltar à faixa' (/hoje?data=2026-10-06&abrir=noite-3#faixa-noite-3) na questão e no relatório; o ✓/fiz volta com o mesmo ?abrir.
Medido no protótipo A: 415 palavras, 7 cartões, 9 botões, 15 dobras, 23 frases; '▶ Começar as 7 reais do radar' na palavra 26 da coluna (hoje ~1.579), '✓ Fiz' na 62, 'Como foi o dia' na 285 (hoje ~1.771). Com os enxertos: ~425, estimativa à mão.

### 8.3 Hoje no celular

```
CELULAR < 1100 px · uma coluna · a ordem do HTML é a ordem da tela
┌ barra (abas em 2 linhas)
├ herói compacto: Terça, 6 de outubro · Ciclo 1, Semana 2 de 6 · termina em 32 dias
│ (⚡ Nível 1) (🔥 1 dia seguido) (🎯 Meta 79 de 100 📌)   ← →
├ (Hoje) (Semanas) (Fichas)
├ #agora — a faixa da hora inteira (às 19:30: [▶ Começar as 7 reais do radar]
│          a ~555 px no protótipo de A em 412×915: 1ª tela)
├ O dia — uma linha por faixa (▸), '↑ agora' na da hora, ▸ 🆘 Plano B
├ Como foi o dia (sobe para o lugar do painel depois da última faixa)
├ ▸ ➕ Estudo extra
└ lateral, no fim: ⏱ Cronômetro (só com JS) · 🧠 Revisão de hoje
  (8 · 2 · R+7 ↓) · Esta semana
```
A lateral passa para depois do dia no HTML; no notebook o grid explícito (hoje.html:57-59) já a põe à direita. Muda a A2. Hoje, no celular, a lateral (~209 palavras: Mapa do ano 102, Objetivo, motivo do nível) vem antes da 1ª faixa, que começa depois de ~269 palavras da página, e ~1.790 até a faixa das 19:30. Custo: a Revisão de hoje fica perto do fim (palavra ~369 da página às 19:30, medido em A) e o cronômetro também. O Mapa do ano sai do Hoje (vai para Semanas). Não medi a altura no template real; o protótipo de A transbordava ~20 px para a direita (artefato do protótipo, a conferir).

### 8.4 Meu foco (a home)

```
NOTEBOOK 1366×680 · 06/10 · 07:00 · cabe sem rolar (protótipo de A termina em ~630 px; hoje ~770)
┌─ barra (igual)
│ Meu foco
│ Terça, 6 de outubro · Ciclo 1, semana 2 · Nível 1
├─ 📅 AGORA NO PLANO · 07:00 · PRÓXIMA ÀS 10:15 ────(2/3)─┐ ┌─ 🧠 Revisão de hoje · fora das faixas ─(1/3)─┐
│ 📖 Teoria · Direito Constitucional · Videoaula ·          │ │ 🟡 8 conteúdos vencidos na fila 1-7-30      │
│ 10:15 – 10:55                                            │ │ • Regras de acentuação · etapa de 1 dia     │
│ Art. 5º, incisos XVII a XLIX                             │ │   vencida há 6 dias                         │
│ 🔵 alvo: caiu em 2013 — 1 questão · 1 prova               │ │ • Concordância verbal · erro recente ·      │
│    (2013: 1 · 2019: 0)                                   │ │   etapa de 1 dia vencida há 6 dias          │
│ 📌 hoje: 49 questões, das 10:15 às 20:05                 │ │ • Parônimos e grafia · erro recente ·       │
│ [Abrir a faixa →]  📋 Ficha · 📝 Resumo                   │ │   etapa de 1 dia vencida há 6 dias          │
└──────────────────────────────────────────────────────────┘ │ [Fazer as revisões de hoje]                 │
                                                              │ 📓 2 erros do caderno · R+7 às 18:00 →      │
                                                              └─────────────────────────────────────────────┘
│ 🩺 Próxima medição: sáb 10/10 · diagnósticos de RL e de Português, 20 + 20 no radar · simulado da semana, 30 no Qconcursos
│ 📊 Evolução · 🟡 medido no radar: 15 respostas a questões reais; faltam 5 para medir a evolução · Minhas matérias → · Semanas →
│ 🎯 Polícia Penal SC · sem edital aberto · banca: hipótese FEPESE, que fez 2013 e 2019 · 🔵 provas 2013 e 2019 · 162 questões · base pequena · nada novo · Edital contra as provas →
```
O cartão 'Agora no plano' sai da MESMA TelaDoDia do Hoje:
- 19:30: '📅 AGORA NO PLANO · EM ANDAMENTO ATÉ 19:40 / 🎯 Questões · Língua Portuguesa · 10: 7 reais no radar + 3 no Qconcursos / Concordância verbal 1: regra geral / 🔵 alvo: caiu em 2013 — 1 questão · 1 prova / ○ sem marca: 7 · depois: 19:40 Correção / [▶ Começar as 7 reais do radar] [Abrir a faixa →]' — 1 clique até a 1ª questão, e é do plano (mesmo POST /hoje/rodada).
- 12:40: 'PRÓXIMA ÀS 18:00: 🔁 R+7 · Art. 5º, caput e incisos I a XVI · 7 de DC + 3 de Português · Qconcursos' [Abrir a faixa →].
- 23:00: 'DIA ENCERRADO · ○ sem marca: N' [Marcar como foi o dia →] (/hoje#como-foi).
- Sábado 10/10, 12:15: '🩺 Diagnóstico de Raciocínio Lógico · 20 reais · Radar' [▶ Começar a rodada (20 reais)]. Domingo: 'Hoje é descanso.'
- A linha 🩺 muda com o dado gravado (sabado.py): depois de 10/10, 'linha de base: RL N de 20 · Português N de 20 (radar, sem consulta)'; depois de 17/10, o R+7; em 07/11, link para a comparação.
Saem: '📚 O que estudar agora' e a fórmula (para Análises › Edital); [Começar treino · 20 questões] (fica só em Edital › Treinar 20 questões); '11 questão(ões) que errei' + [Revisar agora] (Estudar › Simulado, 'Refazer os 11 erro(s)'); o bloco do alvo e a faixa Concurso viram uma linha; 'A linha do tempo passa a registrar… radar atualizar' sai; a regra do Revisar vai para o title do 🟡.
Medido no protótipo A: 190 palavras às 07:00 e 201 às 19:30 (hoje 295), 4 cartões (6), 5 botões (5), 13 frases (16). Com a linha 🩺: ~212 e ~223, estimativa à mão; 4 cartões (a linha não é cartão).

### 8.5 Onde fica cada regra que não pode sumir

- **Amostra:** no painel e na home ("🔵 alvo: caiu em 2013 — 1 questão · 1 prova (2013: 1 · 2019: 0)"), da mesma conta de hoje (`incidencia.caiu_no_alvo`), agora com as notas da ficha; no sábado, no resumo do `<details>` da composição; no "Fiz hoje", "medido no radar: X% em N · anotado: Y% em M".
- **Selos:** nenhum some; o 📌, que hoje não aparece em tela nenhuma do dia, passa a marcar o que é do plano (a meta, "no plano de hoje", o essencial da lei seca). Selo curto guarda o nome no `title`.
- **Procedência:** a janela do Resumo continua a 1 clique do painel, com o modelo e a data; o "Onde na árvore" (que vem da ficha 🟣) leva a procedência no `title`.
- **A frase "Não há evidência suficiente no acervo para afirmar isso.":** continua na ficha, no resumo, na Incidência e na composição de sábado, e passa a aparecer à vista na faixa quando a base é de uma prova só (hoje só existe na janela escondida).
- **Alvo × complementar × meu desempenho:** o painel e a home mostram só o alvo ("alvo:"); o complementar fica no Resumo, na ficha e na composição; o meu desempenho, na "Revisão de hoje", no "Fiz hoje" e na linha de evolução — sem soma.
- **"Treina, não mede":** o resumo "🟣 Treinar mais no radar · N geradas · gerada por IA: treina, não mede" fica visível sem abrir; as faixas com consulta passam a dizer "com consulta · fora da meta", e o "não mede" fica só para a gerada.

### 8.6 Riscos do desenho

- **A ordem importa:** primeiro as correções de precisão (P03 com teste que garanta 0 questões gravadas, P04, P07, P10, P14 e I1, antes de 10/10 quando der); depois o Hoje, a home e as Semanas. Mudar a tela antes só deixa o erro mais rápido de cometer.
- **O painel vale para a hora em que a página carregou** (sem JS novo ele não anda sozinho): se eu atrasar, o painel já mostra a faixa seguinte; o "○ sem marca" com âncoras e o recarregamento a cada ✓ atenuam isso. Os testes têm de parar o relógio (`agora_local`).
- **Uma faixa, uma macro:** o painel, as linhas e a home têm de sair das mesmas funções (`TelaDoDia`, `incidencia.caiu_no_alvo`, `faixa_no_radar`, `estudo.pontas`, `erros.quantos_para_rever`) e da mesma macro de faixa, com um teste que compare Hoje e home; uma segunda versão da faixa seria a divergência que a regra 10 proíbe.
- **O "fiz" pré-preenchido:** o desenho mostra "fiz no Qconcursos [3]" (19:15) e "[8]" (10:55), mas o P03 · U03 propõe o "fiz" vazio nas faixas com rodada. Pré-preencher ainda deixa um clique gravar o que não foi feito (não em dobro, mas grava); o vazio é mais preciso, ao custo de um campo por faixa. Escolha sua; se for o vazio, os desenhos 8.1 e 8.2 passam a "[  ]".
- **Os 2 cliques da especificação:** sem "Começar treino" na home, numa faixa só do Qconcursos e com a fila de revisão vazia, a primeira questão do radar fica a mais de 2 cliques. O critério muda de sentido: passa a valer pela faixa da hora (quando ela tem rodada no radar) ou pela fila de revisão (apêndice A).
- **Peso e tempo:** as linhas fechadas ainda carregam as faixas no HTML (o peso cai com a compressão, U63), e a "Revisão de hoje" passa a chamar `estudo.pontas` a cada abertura do Hoje — custo não medido.
- **Hábito:** cada faixa fora da hora custa 1 clique para abrir; se a linha não disser o bastante (tipo, tema, quantas, onde, estado), deixo de abrir.
- **Celular:** com a lateral depois do dia, o cronômetro e a "Revisão de hoje" vão para o fim da página.
- **Esforço:** médio a alto (o `hoje.html` tem ~1.500 linhas), e o desenho toca ~16 decisões (apêndice A) — todas registradas no `decisoes.md` na mesma etapa.

## Apêndice A — As decisões que as propostas mudam

Nenhuma decisão muda sem você escolher o item. Quando escolher, a decisão vai para o `decisoes.md` na mesma subetapa.

| Decisão | O que muda | Itens |
|---|---|---|
| 81 (a faixa sem conteúdo só chega a nó pela ficha conferida; o acerto não vai a nó nenhum) | O anotado conta no nó da **matéria** (assunto e subassunto ficam como estão) | P01, P09 (opcional) |
| 3 da Etapa 0 (28/09 sem contagem dupla) | Só se as 10 de 28/09 forem as geradas | P08 |
| Etapa 1D, regra 1 (faixa de questões com 0 não conta como feita) | A faixa com rodada respondida no radar conta como feita | P03 · U03 |
| 130 (a faixa avisa o que já foi respondido) | O "fiz" vem vazio também antes da primeira resposta | P03 · U03 |
| 109 (o gabarito oficial na ficha; a pegadinha da classificação com 🔵) | O gabarito só depois de responder; a pegadinha não conferida leva 🟣 ou sai | P05, P25 |
| 118 (o resumo cita a questão com o gabarito, e a importação confere) | A letra sai do texto da questão ainda não respondida; a conferência lê a letra no dado | P05 |
| 67 (a composição volta à questão já respondida quando o assunto esgota) | As rodadas que medem não repetem questão de outra rodada que mede | P07 |
| 105 (os diagnósticos de 10/10; "com o motivo de cada erro" no 17/10) | Os diagnósticos abrem o bloco; uma regra por assunto errado | I1, I4 |
| 108 (o "caiu ou não caiu") — só o texto | "prioridade baixa, estude o básico" sai do selo azul | P10 |
| 112 (a faixa diz "Você estudou…", "1º no Qconcursos, que mede", as geradas abertas, um botão por nó) | Sai "Você estudou…"; "são as que medem" sai das faixas com consulta; o treino dobrado; um botão por faixa | U07, U08, U62 |
| 71 (toda faixa mostra assunto, subassunto e elemento abertos) | Só na primeira faixa do tema (ou num `<details>`, seção 8) | U23, seção 8 |
| 113 e 125 (geradas por nó; a faixa dá os 3 passos de gerar) | Um botão por faixa; os comandos ficam em Gerar questões (no desenho da seção 8) | U62, seção 8 |
| 120 (Resumo em toda faixa, inclusive no diagnóstico e no simulado) | Sai das faixas que medem sem consulta | U02 |
| 128 (a home mostra as pontas; o Meu desempenho, a fila inteira) | O Meu desempenho abre pelas pontas, com a fila inteira dobrada | U11 |
| 111 (um cartão por tema em cada bloco, na aba Fichas) | Um cartão por tema no dia | U41 |
| 115 (Gerar lista os nós do cronograma, com e sem gerada) | Só os sem gerada, com a data | U38 |
| 79 (a seção de revisão do Meu desempenho) — só a forma | As seções viram colunas de uma tabela | U48 |
| 14 da Etapa 3B ("provas" do complementar = cadernos) | "Provas" por concurso | P29 |
| 6 da Etapa 3A e o sitemap da 7B (Conferência em Análises) | A Conferência vai para Mais | U59 |
| E2 (o simulado misto não tem matéria) | Só se os simulados de sábado forem repartidos por matéria | P30 (opcional) |
| E3 (as setas das Semanas) | A seta passa a exigir o mínimo de amostra (completa a decisão, que não define mínimo) | P11 · U18 |
| 27, 28 e 30 (a dobra dos blocos, lembrada por bloco) e A2 (o visual do Hoje) | O painel da faixa da hora; as faixas em linhas; a lateral depois do dia no HTML | Seção 8 |
| "Navegação nova e a home de 3 blocos" (25/09), os blocos 2 e 4 da especificação e o critério de aceite "até 2 cliques até a 1ª questão" | Saem "O que estudar agora", "Começar treino" e "Revisar agora"; o alvo vira uma linha; os 2 cliques passam a valer pela faixa da hora (quando ela tem rodada no radar) ou pela fila de revisão | U01, U20, U28, seção 8 |
| "A tela das geradas" (25/09) | Saem as tabelas de acerto do Simulado e de Gerar; o artigo só depois de responder; o cartão da API vira os 3 passos | U15, U17, U37, U51 |
| "Questão gerada não tem status não revisada" (26/09) | O motivo dela é o artigo à vista: o artigo e o link da lei saem da questão e vão para o relatório | U17 |
| "Meus erros e o simulado compilado" (fase 4) e a especificação ("Simulado compilado (40 / 50 / 100 questões)") | O compilado ganha 10 e 20, com a trava do P12 | U16 |
| "A Central de Macetes" (25/09) e o formato do cartão de macete (especificação) | Um cartão por matéria da árvore; sai o "Padrão da banca"; "Pegadinha" sem "recorrente" | P24, P28 · U50, U19, P27 |
| Relatório pós-simulado (fase 3, 25/09) | "Sem nota de corte" vira `title`; a legenda sai | U36 |
| 6A, item 1 (a fixação com a lei aberta) | "Marque de cabeça; só então abra o artigo" | I9 |
| 126 (a nuvem como "Próximo") | Fica para depois de 07/11 | I3 |

## Apêndice B — Uma ordem possível (a escolha é sua)

1. **Sem código, já:** os quatro cuidados de uso da seção 3.1; responder P02 e P08; conferir as 5 fichas do I5 (liga 9 faixas feitas à revisão).
2. **Até 09/10** (antes do diagnóstico): I1, P14 · U04, P03 · U03 (ao menos nas faixas de sábado), U02, os textos do I4 e do I6 para 10/10, e o I2 (o R+7 de amanhã já volta a um dia sem registro). O P06 (Conferência que apaga o artigo) é pequeno e vale fazer antes de voltar a conferir.
3. **Até 17/10:** o texto do I4 para 17/10, o U21 · P36 (o erro ligado ao nó, sem "Diagnósticos").
4. **Até 07/11:** P07 (composição) e P30 (o que decide o Ciclo 2) obrigatoriamente; P04 (R+7 dividido, quanto antes), P01 · P09 (a regra do anotado), P05 (o gabarito na ficha), P10, P11 · U18.
5. **Depois de 07/11** (se você aceitar o I3): o redesenho do Hoje, do Meu foco e das Semanas (seção 8), começando pelo I8 (o teste que segura a limpeza); depois as telas de análise e de consulta; por fim a coerência (U52 a U54, U59, U60, U64).
