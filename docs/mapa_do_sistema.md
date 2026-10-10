# Mapa do sistema (09/10/2026)

Pedido de 09/10: entender o radar como ele é, sem mudar nada. **Nada foi
alterado no código, na configuração nem no dado**; este é o único arquivo
novo. Como foi verificado, e tudo o que rodou, está no
[anexo](#anexo-o-que-rodou-e-como-foi-verificado). As linhas citadas
(`hoje.html:1088`) são as do commit `9b37859`.

Legenda dos estados (seção 7): ✅ implementada e verificada (abri a tela ou
rodei o comando com o banco real, e há teste passando) · 🟢 verificação
parcial (só uma das duas) · 🟡 parcialmente implementada · 📄 documentada ou
planejada, não implementada · 🔴 com problema identificado · ❔ não deu para
saber.

---

## 0. Para ler primeiro

**O que o radar é.** Um programa pessoal, em Python, que roda no seu
notebook (a web na porta 8000, um banco SQLite) e no GitHub (um robô diário).
Ele faz duas coisas: **acompanha concursos** (coleta três fontes, decide se
cada um é perto, se é a sua carreira, e avisa no Telegram) e **organiza o
estudo para a Polícia Penal SC** (o plano do dia, as fichas, as questões
reais da FEPESE, o treino com questões de IA e as contas de quanto você
acerta). A IA não é paga: todo texto de IA entra pelo Claude Code, em três
passos que você roda à mão.

**As 5 coisas que você mais precisa saber para usá-lo bem**

1. **Amanhã (10/10) a medição nasce no botão da própria faixa.** "Criar a
   rodada com esta composição" só aparece no dia. Até lá, **não clique** em
   "Começar treino" (Meu foco e Edital), nem no "Começar" do Simulado, nem no
   "Criar a rodada" que ainda aparece no **03/10**: os três gastam questões
   reais que o diagnóstico usaria (a respondida vai para o fim da fila da
   composição; a da rodada criada no 03/10 sai do estoque de vez). É o P12
   da proposta, ainda aberto - o CLAUDE.md diz "a proposta está feita até
   07/11", e este item não está.
2. **O que você marca vai só para o banco do notebook.** O GitHub (e o
   robô) só recebe no backup das 23:30, que roda com o PC ligado e você
   logado; se perder a hora, roda quando você logar (08/10 não rodou; rodou
   09/10 às 12:05). **Depois de qualquer mudança no código** (outra
   conversa do Claude Code, `git pull`): `.venv\Scripts\radar.exe parar` e
   `.venv\Scripts\radar.exe subir` - o servidor não recarrega sozinho, e o
   README não diz isso.
3. **Como ler os números.** "radar" é questão real respondida no radar;
   "anotado" é o que você digita do Qconcursos; o acerto que vale é o **sem
   consulta**, e o treino de IA é sempre um número à parte (conferido no
   código: nunca soma). A mesma matéria pode aparecer com dois números porque
   as telas contam recortes diferentes: Língua Portuguesa é **46% em 57** no
   Meu foco, no Edital e em Minhas matérias e **45% em 58** no Meu
   desempenho. O que decide o Ciclo 2 é o **acumulado do ciclo**, na faixa
   de 07/11.
4. **IA: um pedido por vez.** `--pedido` grava `data/pedido_ia.json`, o
   Claude Code responde em `data/resposta_ia.json`, `--importar` confere e
   grava. Um `--pedido` novo **apaga** o que estava esperando, sem cópia: o
   pedido do art. 13 que a pendência H.6 ainda cita já foi substituído em
   09/10.
5. **Telegram.** O robô "das 06:00" sai, na prática, entre 11h e 13h. Ele
   avisa concurso novo perto ou da sua carreira e os marcos críticos das 7
   carreiras da aba Acompanhando. **Favorito não avisa nada porque você tem
   0 favoritos** - quem acompanha a Polícia Penal SC é a aba Acompanhando.

**Os problemas encontrados** (detalhe na seção 9; o que fazer, na 8)

- **Antes de 10/10:** o "Começar treino" e o "Criar a rodada" do 03/10
  (acima). É o único risco para a medição de amanhã.
- **Números que divergem entre telas:** LP 46%/57 × 45%/58 (o P20 da
  proposta aconteceu); LEP "anotado 50% em 22" em Minhas matérias × "31% em
  13" no Edital e no Meu desempenho (Minhas matérias soma o feito com
  consulta); a home põe as "Matérias fracas" (radar + anotado) sob a legenda
  "medido no radar: das 26 questões".
- **Radar de concursos:** 3 dos 10 "banca definida" são falsos (o sinal que
  o CLAUDE.md chama de mais valioso); o mesmo fato vira dois eventos (robô ×
  notebook, 8 pares no `eventos.json`); uma retificação de edital seria
  avisada todo dia (o robô não commita o `provas.json`); o `robots.txt` fora
  do ar libera a coleta, contra o "sem exceção" do CLAUDE.md.
- **IA:** o `--pedido` sobrescreve sem aviso; a importação aceita resposta
  sem o modelo (o CLAUDE.md pede modelo e data); uma gerada rejeitada voltou
  a contar no treino de IA; o gerador pago gera sem o escopo que mostrou
  (latente: não há chave).
- **Documentação:** o README está atrás do código em ~30 pontos (Hoje,
  Telegram, sincronizar, "depois de atualizar"); o CLAUDE.md diz 901 geradas
  (são 921), 65 resumos por conferir (são 64), três anéis (o código tem
  cinco) e não cita a Polícia Militar, que está no `alvo.yml`.

---

## 1. Visão geral

Confirmado: é o que o CLAUDE.md descreve - um sistema de um usuário só, sem
login, para (1) achar concursos que valem a pena, com a Polícia Penal SC como
alvo e Guarda Municipal, Polícia Civil e as demais carreiras de segurança
pública na ordem do `config/alvo.yml`, e (2) estudar para o alvo pelo
edital de 2019 e pelas provas FEPESE de 2013 e 2019. O que mudou desde o
texto de origem: o estudo virou a maior parte do código (o `servico/` tem 33
arquivos, quase todos de estudo), e há um Ciclo 1 em andamento (28/09 a
07/11) com três sábados que medem (10/10, 17/10, 07/11).

O tamanho em 09/10: 2.962 concursos e 188 eventos; 8.462 questões de 216
provas (170 do alvo, 7.385 do complementar FEPESE, 907 de outras bancas);
árvore de 438 nós; 708 classificações; 921 questões geradas; 65 fichas; 17
rodadas e 140 linhas de resposta (26 respostas a questões reais, 72 a
geradas); 2 erros no caderno. São 117 arquivos de teste; a última suíte
inteira registrada deu 2.853 passed (`docs/progresso.md`, linha 38).

---

## 2. Como funciona

### O caminho do dado

```
 FONTES (sites)                 NOTEBOOK (radar.db + web :8000)             GITHUB
 Concursos no Brasil (RSS) ┐
 FEPESE (API WordPress)    ├─► collectors/ ─► coleta + classificador ─► concursos, eventos ─► Concursos, Acompanhando
 IESES (API JSON)          ┘     (robots, atraso, User-Agent)              │                    Calendário, Previsão
                                                                           └─► avisos ─► Telegram (de rotina, só o robô)
 Hotsites (PDF) ─► provas ─► questões ─► evidência (alvo / complementar / fora)
                                   └─► classificação na árvore ─► incidência ─► fichas, composição das rodadas
 config/cronograma.yml ─► Hoje (faixas) ─► o que você marca + rodadas ─► metricas ─► Semanas, Minhas matérias,
                                                                                    Meu desempenho, fila de revisão
 Claude Code ◄─ pedido_ia.json ◄─ --pedido      resposta_ia.json ─► --importar ─► geradas, fichas, resumos,
                                                                                  explicações, classificações
 sincronizar (23:30): puxa o JSON do robô, reaplica as regras, exporta o banco para data/*.json, commit e push
 robô (cron 06:00): pytest, importar JSON, coletar, avisar, exportar, commit "coleta:"
```

O banco (`data/radar.db`) não vai para o git: o que vai são os JSON de
`data/`, e o banco se refaz deles (`radar importar`), menos as questões e o
texto-base, que se refazem dos PDFs.

### (a) Um edital que sai na FEPESE, até o cartão e o Telegram

1. O robô do GitHub (`.github/workflows/coleta.yml`, cron 09:00 UTC, na
   prática entre 11h e 13h) roda o `pytest -q` (se falhar, para), refaz o
   banco dos JSON (`radar importar`) e roda `radar coletar`.
2. O coletor da FEPESE (`collectors/fepese.py`) lê a API WordPress do site,
   com o `robots.txt`, 1,5 s entre requisições e o User-Agent da classe
   `Coletor` (`collectors/base.py`). Devolve o item com banca FEPESE,
   situação e hotsite.
3. `servico/coleta.py` grava pela URL e chama `classificador.classificar`:
   o município sai do **título**, vira anel pelo `config/regioes.yml`
   (núcleo, próximo, estadual, remoto ou indefinida, com o
   `motivo_relevancia`), o salário sai do título, a fase do texto, e o
   `alvo.marcar` diz se é a sua carreira (`config/alvo.yml`). Nasce o
   evento "apareceu"; as datas atualizam a situação.
4. `radar avisar` manda, nesta ordem: (1) o que mudou nos favoritos (hoje,
   nada: 0 favoritos); (2) os marcos críticos das carreiras do
   `config/acompanhamentos.yml` (edital, inscrições, prova, retificação,
   banca definida), desde 06/10; (3) concurso novo perto, estadual ou
   indefinido, ou do alvo. Polícia Penal SC (🚨) e os `de_olho` (👀) furam
   o teto de 10 por etapa (`servico/avisos.py`).
5. `radar retificacoes --avisar` confere se edital baixado mudou;
   `radar exportar` grava `concursos.json` e `eventos.json`; o commit
   `coleta: AAAA-MM-DD` só sai se algo mudou.
6. No notebook, o cartão aparece em **Concursos › Todos** depois do backup
   das 23:30 (que puxa o JSON e reaplica as regras de hoje) ou na hora, pelo
   botão **"Verificar atualizações"** da aba Acompanhando (a mesma coleta,
   mais a leitura da página de 15 concursos, dentro do servidor). Prazo,
   banca e município da página (`radar detalhar`) e a elegibilidade pelo PDF
   (`radar elegibilidade`) **só rodam no notebook** (`radar atualizar`),
   nunca no robô. Se o concurso é de uma das 7 carreiras, o cartão da aba
   Acompanhando ganha 🔔. A prova e o gabarito, depois, entram no acervo por
   `radar provas`.

### (b) Uma faixa da noite, do Hoje até o Meu desempenho

Exemplo real: 09/10, 18:30, "Aprendizagem: Deveres e direitos do preso (arts.
38 a 43)", 15 questões.

1. `GET /hoje` (`servico/cronograma.py:920`, `tela_do_dia`) monta o dia do
   `config/cronograma.yml` no nível da semana (nível 1: Direito 15). A faixa
   diz onde está na árvore (`fichas.onde_na_arvore`), se o tema caiu nas
   provas do alvo (`incidencia.caiu_no_alvo`), traz o botão **"Abrir no
   Qconcursos"** (o filtro FEPESE montado pelo `config/qconcursos.yml`; para a
   LEP, "o link traz a lei inteira: faça só as dos arts. 38 a 43"), a **ficha**,
   o **Resumo** (janela só com CSS) e as geradas do tema com **"Treinar no
   radar"**.
2. Você faz as questões no Qconcursos e anota **"fiz / acertei"** na faixa
   (`POST /hoje/faixa/questoes` → `estados_do_dia.faixas_feitas`, com matéria,
   consulta e os nós). O campo vem vazio de propósito (decisão 138). Se fizer
   no radar, a rodada já conta sozinha e a faixa fecha com o ✓ vazio.
3. **"📝 Como foi"** (`POST /hoje/faixa/nota`) guarda chutes, "entendi?" e a
   nota - diário, fora de toda conta. **"Anotar erro"** abre o caderno com o
   nó da faixa (decisão 144).
4. `servico/metricas.py` (`lancamentos`) junta faixas, extras e respostas do
   radar: daí saem o **"Fiz hoje"** em três linhas (reais · treino de IA ·
   total), as Semanas e Minhas matérias.
5. O **Meu desempenho** (`servico/desempenho_por_conteudo.py`) põe o
   anotado no nó da faixa (o `conteudo`, os `nos` do plano ou a ficha
   **conferida**; sem nada disso, no nó da matéria - decisão 147), só o sem
   consulta, e decide o estado pela amostra do `config/amostra.yml` (20 na
   matéria, 10 no assunto, 6 abaixo).
6. O nó entra na **fila de revisão** (`servico/estudo.py`, `para_revisar`)
   por erro recente, acerto abaixo do corte ou prazo 1-7-30 vencido; a home
   mostra as pontas e o "Fazer as revisões de hoje".
7. Às 23:30 o `sincronizar` exporta para `data/estado_do_dia.json` e
   `registro_estudo.json` e sobe para o GitHub.

### (c) Um pedido de questões geradas, até o treino

Exemplo real: a faixa de 09/10, 18:20, "R+7: Verbo 2", diz "Não há questão
gerada" e dá os três passos.

1. `.venv\Scripts\radar.exe gerar --pedido --modo treino --materia "Língua
   Portuguesa" --assunto "Emprego de tempos e modos verbais" --quantas 5`
   grava `data/pedido_ia.json` (`servico/manual.py`, `salvar_pedido`), com o
   lote, o escopo, as regras e o "como responder". **Substitui o pedido que
   estiver lá.**
2. No Claude Code do VS Code: "Leia data/pedido_ia.json e siga o
   como_responder; escreva data/resposta_ia.json" (com o `modelo`).
3. `.venv\Scripts\radar.exe gerar --importar data/resposta_ia.json`: o
   `manual.importar` confere o lote, as 5 alternativas, o gabarito, o
   artigo ou a regra, o escopo e o nó; descarta as repetidas; grava em
   `questoes_geradas` e `data/questoes_geradas.json` com a procedência
   "Claude Code (modelo), importado manualmente, em dd/mm/aaaa".
4. Na faixa, **"Treinar no radar"** (`POST /geradas/treinar`) abre uma
   rodada com as nunca feitas primeiro (`geradas._na_ordem_de_treino`); a
   questão volta corrigida na hora, com o selo 🟣.
5. O acerto vai para o **Treino de IA** (`metricas`, `Conta.treino_ia`) e
   nunca para o acerto real, o estado, a fila ou a prioridade.

---

## 3. Mapa das abas

A barra tem 7 seções; a sub-aba vem depois do ›. "Abriu" = aberta
no meu servidor da porta 8001, com o banco real, em 09/10 (todas deram 200,
sem erro). A melhoria entra só como referência.

| Tela | Para que serve | O que eu faço nela | De onde vem o dado | Com o que se liga | Estado |
|---|---|---|---|---|---|
| 📅 Hoje › Hoje (`/hoje`) | O dia do cronograma, faixa a faixa, com o "Agora" | Sigo a faixa, abro Qconcursos, ficha e Resumo, treino no radar, anoto "fiz", "Como foi", erro e o "Como foi o dia" | `cronograma.yml` + `servico/cronograma.py` + fichas, incidência, geradas, `metricas` | Ficha, Simulado (rodada), Caderno, Semanas, Meu desempenho | ✅ (P16, U05 a U07) |
| Hoje nos sábados que medem (`/hoje?data=2026-10-10`, `-10-17`, `-11-07`) | Diagnóstico, R+7 dos erros e fechamento | No dia, "Criar a rodada com esta composição" | `servico/composicao.py`, `servico/sabado.py` | Simulado, comparação de 07/11 | 🟢 (tela certa; a criação nunca rodou) · 03/10 🔴 (P12) |
| 📅 Hoje › Semanas (`/semanas`) | Uma semana por cartão, com setas | Leio; escrevo a reflexão (segunda) | `servico/semanas.py` ← `metricas.lancamentos` | Gatilho do nível, caderno | ✅ (P38) |
| 📅 Hoje › Fichas (`/fichas`, `?ver=todas`, `/fichas/{tema}`) | O que ler, como pesquisar, como a FEPESE cobrou, o Resumo | Leio; "Conferi esta ficha" e "Conferi este resumo" | `data/fichas.json` + `radar/fichas.py` + incidência | Faixas do Hoje; a ficha conferida liga a faixa ao Meu desempenho | ✅ (U12, U13, U22) |
| 📅 Hoje › Caderno de erros (`/erros`) | Os erros com a regra e o 1-7-30 | "Já sei" / "Ainda erro" | `erros_anotados` ← `servico/erros.py` | Fila de revisão, Semanas | ✅ (2 erros, vencidos desde 30/09: I4) |
| Anotar erro (`/erros/novo`) | O formulário do caderno | Regra, motivo, fonte, nó | árvore + link da faixa ou da questão | Caderno | ✅ (U14) |
| 🎯 Meu foco (`/`) | O que estudar hoje e o que revisar | "Abrir o dia", "Começar treino", "Revisar agora", "Fazer as revisões de hoje" | `servico/inicio.py` ← `foco`, `estudo.pontas`, `metricas.evolucao` | Hoje, Edital, Meu desempenho, Simulado | 🔴 (legenda das "Matérias fracas"; U01·P12) |
| 📚 Estudar › Simulado (`/simulado`, `/simulado/{id}`) | Rodadas com questão real: erros, compilado, "Começar" | Crio, respondo, leio o relatório | `servico/simulado.py`, `compilado.py` | Métricas, caderno, fila | 🔴 ("Começar" sem trava de banca: P13) |
| 📚 Estudar › Gerar questões (`/geradas`) | Gerar pela API (sem chave) e treinar com as que existem | "Treinar com as que já tenho" | `servico/geradas.py`, `gerador.py` | Faixas, ficha, Treino de IA | 🔴 (gerar pela tela ignora o escopo; latente) |
| 🧠 Revisão › Macetes (`/macetes`, `/macetes/{id}/questoes`) | Central por matéria e exploração por banca/cargo | Leio; abro as questões do macete | `data/macetes.json`, `servico/cartoes.py` | Ficha, relatório | 🔴 (Processo Penal em 2 cartões: P28; U19, U46) |
| 📊 Análises › Edital (`/analises`) | Edital × provas × meu acerto, "Onde estudar primeiro" | Leio; "Treinar 20" | `foco.py`, `onde_estudar.py`, incidência | Meu foco, Simulado | 🔴 (Processo Penal 2013 "--": P24) |
| 📊 Análises › Minhas matérias (`/analises/materias`) | Um cartão por matéria do ciclo, projeção | Leio | `servico/materias.py` ← `metricas` | Semanas, Edital | 🔴 (LEP "anotado 50% em 22" com consulta; P17, P31) |
| 📊 Análises › Meu desempenho (`/analises/desempenho`) | Cada nó: estado, amostra, revisões, fila inteira | Leio; refaço as erradas | `servico/desempenho_por_conteudo.py`, `estudo.py` | Fila, home, Ciclo 2 (notas) | 🔴 (45% em 58 × 46% em 57: P20) |
| 📊 Análises › Incidência (`/analises/incidencia`) | O que caiu por nó, alvo × complementar | Leio | `servico/incidencia.py` (coluna `evidencia`) | Fichas, composição, Onde estudar | 🔴 ("67 questões · 168 provas": P29; U32) |
| 📊 Análises › Conferência (`/analises/conferencia`) | Conferir classificações e associados | Confirmar, corrigir, pendente | `servico/classificacoes.py` | Incidência, fichas | ✅ (abre com 2,5 MB: U34) |
| 🏛 Concursos › Todos (`/concursos`) | A lista com onde, quanto e até quando | Filtro, ★, salário, nota | `servico.listar` | Calendário, Telegram | ✅ (não mostra alvo nem elegibilidade; P55, P56) |
| 🏛 Concursos › Acompanhando (`/acompanhando`) | Um cartão por carreira, com 🔔 e a pesquisa 🟣 | "Visto", "Verificar atualizações", conferir pesquisa | `servico/acompanhamentos.py`, `data/acompanhamentos.json` | Telegram (crítico), Edital | ✅ |
| 🏛 Concursos › Calendário (`/calendario`, `.ics`) | Prazos para a agenda | Baixo o `.ics` | `servico.eventos_do_calendario` | — | 🟡 (data de prova nunca preenchida) |
| 🏛 Concursos › Previsão (`/previsao`) | Município parado há tempo demais | Leio | `servico/previsao.py` | — | ✅ (P57) |
| ⚙ Mais (`/mais`) e Auditoria (`/auditoria`) | Selos, cobertura, leis, backup; o `docs/auditoria.md` | Leio | `previsao`, `automacao`, `docs/auditoria.md` | — | ✅ |
| Endereços que só redirecionam | `/foco` → `/`, `/estudar` → `/simulado`, `/revisao` → `/erros`, `/tema` (cookie claro/escuro) | — | — | — | ✅ |
| `POST /coletar` | Coleta sem tela | — (nenhum botão chama) | `coleta.coletar_tudo` | — | 🟢 (sem teste nem uso) |

---

## 4. Mapa dos comandos

No Windows, sempre `.venv\Scripts\radar.exe <comando>` (ou `.\radar.bat`).
L = só lê · G = grava · R = internet · T = Telegram · A = apaga.

| Comando | Para que | Quando rodar | Efeito |
|---|---|---|---|
| **Dia a dia** | | | |
| `hoje` | O dia no terminal (`--data`, `--marcar`, `--plano-b`) | Quando quiser | L; `--marcar` e `--feitas/--acertos/--minutos` G |
| `status` | Web no ar? Último backup? | Quando a tela não abrir | L (apaga o PID órfão) |
| `subir` / `parar` | Web sem janela / desligar | Depois de mudar o código: `parar` e `subir` | G PID e `web.log` / A PID |
| `web` | Web numa janela (`--porta`, `--rede`) | Para outra porta ou o celular | L (a tela grava o que você marcar) |
| `sincronizar` | Troca com o GitHub e reaplica as regras | Sozinho às 23:30; à mão para trazer o robô | G banco, 10 JSON, commit, push · R · A rodadas vazias com mais de 1 dia |
| `backup` | O `sincronizar` com log | É o que a tarefa das 23:30 roda | Como o `sincronizar` |
| `agendar` | Cria as 2 tarefas e os 2 atalhos | Uma vez (`--status` para conferir) | G Agendador; `--status` L |
| **Estudo** | | | |
| `fichas` | Ficha do tema; conferir; pedido e importação | Ao conferir e ao montar o Ciclo 2 | Sem opção L; `--conferir*` e `--importar` G `fichas.json` |
| `desempenho` | Meu desempenho no terminal | Quando quiser | L |
| `incidencia` / `padrao` / `repetidas` | O que caiu, por nó / por matéria / repetidas | Quando quiser | L |
| `simulados` / `descartar` | Listar / apagar rodada | Raramente | L / **A sem perguntar** pelo id |
| `conferir-dias` | Confere os dias gravados | Depois de corrigir um dia | L; `--aplicar` G |
| **IA (sem API)** | | | |
| `gerar` | Questões geradas, macetes, explicações | Quando a faixa diz "não há gerada" | `--pedido` G (substitui o pedido); `--importar` G; sem opção só simula; `--valendo` R e gasta (sem chave hoje) |
| `classificar` | Classificação na árvore | Acervo novo | `--pedido`/`--importar` G |
| `acompanhar` | Cartões das carreiras; a pesquisa | Sem opção, quando quiser; `--pedido` para pesquisar | Sem opção L; `--verificar` R G; `--pedido`/`--importar`/`--visto` G |
| `conteudos` | A árvore (`--pendentes`, `--juntar`) | Ao juntar nós repetidos (pendência G) | Sem opção L; `--juntar` G em 6 JSON |
| **Acervo** | | | |
| `provas` / `baixar-provas` | Baixar edital, prova e gabarito / refazer os PDFs | Banca nova; PC novo | G PDFs e `provas.json` · R |
| `questoes` | Cadernos → questões (`--refazer`, `--textos-base`) | Depois de baixar provas | G; **`--refazer` relê só 30 sem `--limite`** |
| `complementar` | Levanta o acervo complementar | Raramente | G `docs/complementar.md`; `--aplicar` G o JSON |
| `auditar` | Banco × PDFs | Depois de mexer no leitor | G `docs/auditoria.md` |
| `parecidas` / `cobertura` / `assuntos` | Prova parecida / assunto fino (coluna antiga) | Praticamente aposentados | L; `assuntos --valendo` gasta |
| **Concursos** | | | |
| `coletar` / `atualizar` | Coleta / a rotina inteira (detalhar, elegibilidade, retificações) | `atualizar` à mão, quando quiser prazos e banca completos | G · R; `atualizar --avisar` T |
| `listar` / `eventos` / `previsao` | Lista, linha do tempo, previsão | Quando quiser | L |
| `favoritar` / `salario` | Marcar concurso | Quando quiser | G |
| `detalhar` / `situacoes` / `elegibilidade` / `retificacoes` / `reclassificar` | Partes do `atualizar`; reaplicar as regras | Depois de mudar `alvo.yml`/`regioes.yml` (o backup já reclassifica) | G; `detalhar`/`retificacoes` R; `retificacoes --avisar` T |
| `avisar` / `testar-telegram` | Telegram | Só o robô roda o `avisar` | T |
| `carga-inicial` | Histórico que a coleta não pegou | Uma vez | G · R (pergunta antes) |
| `calendario` | Exporta o `.ics` | Prefira o botão da tela | G `radar.ics` na pasta atual |
| **Manutenção** | | | |
| `exportar` / `importar` | Banco → JSON / JSON → banco | O `sincronizar` faz os dois | G |
| `migrar` | Leva o banco à versão atual (com cópia) | Sozinho, no primeiro comando depois de um passo novo | G; `--desfazer` restaura |

Os comandos "só para ver" do pedido (`hoje`, `acompanhar`, `listar`,
`desempenho`, `incidencia`, `padrao`, `previsao`, `repetidas`, `status`,
`agendar --status`) de fato só leem hoje. A ressalva: todo comando que abre o
banco chama `criar_tabelas` (`db.py:83`), que **migra e grava** quando o
código traz um passo novo em `migracoes.py` - o primeiro comando depois de um
`git pull` desses grava, com cópia antes.

---

## 5. Mapa da rotina

| O quê | Quando | Como | Se esquecer, ou se falhar |
|---|---|---|---|
| Robô do GitHub: testes, coleta, Telegram, `coleta:` | Sozinho, cron 06:00 (sai entre 11h e 13h) | `.github/workflows/coleta.yml` | Sem aviso naquele dia. Sem commit = sem novidade **ou** falha: pelo git não dá para saber (não há `coleta:` em 05 e 06/10) |
| Web na porta 8000 | Sozinha, no logon | Tarefa "Radar - web" | Se cair: `.venv\Scripts\radar.exe subir --abrir` (ou o atalho Radar.bat) |
| Backup das 23:30 (`sincronizar`) | Sozinho, com o PC ligado e você logado; se perdeu, ao logar | Tarefa "Radar - backup" → `data/logs/sincronizar-<dia>.log` | O que você marcou fica só no `radar.db`; o robô não vê. Ver `radar status` ou a tela Mais. Com a pasta suja e o GitHub à frente, falha toda noite até resolver à mão |
| Depois de mudar o código (outra conversa, `git pull`) | Toda vez | `.venv\Scripts\radar.exe parar` e `.venv\Scripts\radar.exe subir` | Tela antiga: o Python e os YAML com cache (`regioes`, `alvo`, `perfil`, `leis`, `acompanhamentos`) ficam os de antes. O `cronograma.yml` é relido a cada vez |
| Depois de mudar `alvo.yml` ou `regioes.yml` | Na hora, se quiser ver | `.venv\Scripts\radar.exe reclassificar` + `parar`/`subir` | O backup das 23:30 reclassifica; a web só vê depois de reiniciar |
| Trazer o que o robô coletou hoje | Quando quiser | Botão "Verificar atualizações" (Acompanhando) ou `.venv\Scripts\radar.exe sincronizar` | Espera as 23:30 |
| Prazos, banca, elegibilidade | Quando quiser | `.venv\Scripts\radar.exe atualizar` | O robô não faz: o concurso novo fica sem prazo da página e sem elegibilidade |
| Faixa com "Não há questão gerada" | Na hora da faixa | Os 3 passos que a faixa mostra | Treina só no Qconcursos. Um pedido por vez |
| Sábados que medem (10/10, 17/10, 07/11) | No dia | "Criar a rodada com esta composição" na faixa | Antes do dia o botão não aparece; em dia passado aparece (P12) |
| Conferir fichas, resumos, classificações, leis | Aos poucos (a do tema do dia) | Hoje › Fichas; Análises › Conferência; `config/leis.yml` | A ficha não conferida não liga a faixa sem `conteudo` ao Meu desempenho (decisão 81) |
| Ciclo 2 | Antes de 09/11 | Fichas, resumos e explicações dos temas novos (`radar fichas --pedido`, `--resumos`, `--explicacoes`) e o `cronograma.yml` | Sem plano a partir de 09/11 |

---

## 6. Componentes

**Entrada e telas**
- `src/radar/cli.py` - os 47 comandos (typer); `radar.bat` chama o `.venv`.
- `src/radar/web/app.py` - as 61 rotas (FastAPI); `templates/` (30) e `static/` (`cronometro.js`, `dobra.js`, `design.css`).
- `src/radar/automacao.py` - `subir`, `parar`, `status`, `backup` e as tarefas do Agendador.

**Radar de concursos**
- `collectors/base.py` (`Coletor`: robots, atraso, User-Agent), `concursos_no_brasil.py`, `fepese.py`, `ieses.py`.
- `servico/coleta.py` - `COLETORES`, gravação, situação pelas datas.
- `classificador.py` (tipo, município, salário, fase), `regioes.py`, `alvo.py`, `perfil.py`, `elegibilidade.py`, `detalhes.py`, `eventos.py`.
- `servico/avisos.py` + `avisos.py` - Telegram; `servico/acompanhamentos.py` + `acompanhamentos.py` - as carreiras; `acompanhando.py` - os favoritos.
- `servico/previsao.py`, `calendario.py`.

**Estudo**
- `cronograma.py` (ler e montar o dia) + `servico/cronograma.py` (a tela e o que se marca).
- `servico/metricas.py` - **a fonte única das contas**; `amostra.py` + `config/amostra.yml` - os mínimos.
- `servico/desempenho_por_conteudo.py`, `servico/estudo.py` (a fila única), `servico/espacada.py`, `servico/erros.py`, `servico/semanas.py`, `servico/materias.py`, `servico/inicio.py` (home), `foco.py` + `onde_estudar.py` (Edital).
- `servico/simulado.py`, `servico/compilado.py`, `servico/composicao.py` (rodadas que medem), `servico/sabado.py`, `servico/faixa_no_radar.py`, `servico/extra.py`, `servico/notas_da_faixa.py`.
- `fichas.py` + `servico/fichas.py`; `incidencia.py` + `servico/incidencia.py`; `prioridade.py` + `config/prioridade.yml`; `macetes.py` + `servico/cartoes.py`; `qconcursos.py` + `config/qconcursos.yml`; `origem.py` (os selos).

**Acervo e IA**
- `provas.py`, `provas_ieses.py`, `acervo.py` (JSON ↔ banco), `questoes.py`, `questoes_ieses.py`, `gabarito.py`, `substituta.py`, `servico/provas.py`.
- `complementar.py` + `servico/complementar.py` + `config/complementar.yml`; `servico/evidencia.py` (alvo, complementar, fora).
- `conteudos.py` + `servico/conteudos.py` (a árvore); `servico/classificacoes.py`; `config/taxonomia.yml`.
- `servico/manual.py` - o caminho `--pedido`/`--importar`; `gerador.py` + `servico/geradas.py` (API paga, sem chave); `leis.py` + `config/leis.yml`.
- `db.py`, `models.py` (14 tabelas), `migracoes.py` (versão 7).

**Configuração (você edita)**: `cronograma.yml`, `alvo.yml`, `regioes.yml`,
`acompanhamentos.yml`, `amostra.yml`, `prioridade.yml`, `qconcursos.yml`,
`leis.yml`, `perfil.yml`, `taxonomia.yml`, `complementar.yml`.

**Dados**: `data/radar.db` (fora do git); os JSON de `data/` (o registro
versionado); `data/provas/` (os PDFs, refeitos pelo manifesto
`provas.json`); `data/copias/` (cópias antes de cada mudança); `data/logs/`.

**Integrações**: GitHub (repositório e Actions), Telegram (bot, segredos no
GitHub), Agendador do Windows, Claude Code no VS Code (manual), Qconcursos
(só link), API da Anthropic (código pronto, sem chave).

---

## 7. Estado atual

Os testes citados passam: a suíte inteira deu 2.853 passed no fim do lote 4
(`progresso.md`, linha 38) e o robô de 09/10 rodou o `pytest -q` antes do
commit `coleta: 2026-10-09`; depois disso só mudou `data/acompanhamentos.json`,
cujos testes rodei (127 passed).

**Radar de concursos**

| Funcionalidade | Estado | Evidência |
|---|---|---|
| Coleta das 3 fontes | 🟢 | `coleta: 2026-10-09` do robô; itens de 09/10 17:21 UTC no banco; `test_fepese`, `test_ieses`, `test_coletor_concursos_no_brasil` (não rodei: proibido) |
| Anel pelo município (SC) | ✅ | `radar listar` (Perto/Proximo com motivo); `test_classificador`, `test_regioes` |
| Anel pelas cidades de prova no PDF (federal, outro estado) | 📄 | CLAUDE.md:90; nenhum código lê a cidade de aplicação; outra UF com município vira `remoto` direto (`classificador.py:342-348`) |
| Alvo, `principal_fora`, `de_olho` | ✅ | `radar acompanhar`; Edital "De olho"; `test_alvo` |
| Fase `banca_definida` | 🔴 | 3 dos 10 são falsos: ids 1851, 195 e 1422 (`classificador.py:87-92`) |
| Elegibilidade | 🟡 | Grava pelo PDF (`test_elegibilidade`), mas a lista não filtra nem mostra o veredito |
| Salário no ranking | 🟡 | CLAUDE.md:62 diz "mais embaixo"; a lista só usa salário como filtro (`servico/__init__.py:299-342`) |
| Situação e linha do tempo | 🔴 | O mesmo fato vira dois eventos (8 pares no `eventos.json`; `acervo.py:74`); `test_eventos` passa |
| Concursos › Todos | ✅ | Abriu; `test_web`, `test_filtros` |
| Acompanhando e a pesquisa 🟣 | ✅ | Abriu; `radar acompanhar`; 127 passed (rodados por mim) |
| "Verificar atualizações" | 🟢 | `web.log` de 09/10 mostra a verificação das 17:21; não cliquei (POST) |
| Calendário e `.ics` | 🟡 | Abriu; a data de prova nunca é preenchida (0 no banco), e o README:1821 promete |
| Previsão | ✅ | Abriu; `radar previsao`; `test_previsao` |
| Telegram (`avisar`) | 🟢 | `test_avisos` (44); o envio real não dá para ver daqui; 0 favoritos |
| Retificação de edital | 🔴 | Latente: seria avisada todo dia (o robô não commita `provas.json`); 0 casos até hoje |

**Estudo**

| Funcionalidade | Estado | Evidência |
|---|---|---|
| Cronograma e `radar hoje` | ✅ | Rodou; `test_cronograma` |
| Hoje: faixas, "Agora", onde na árvore, caiu | ✅ | Abriu ("Agora · 20:52"); `test_tela_hoje`, `test_onde_na_arvore` |
| Resumo (janela CSS) | ✅ | 12 no dia; nenhum nas faixas de diagnóstico; `test_resumo` |
| "Fiz no Qconcursos" e o ✓ da faixa feita no radar | ✅ | Checks reais em 5 dias; `test_fiz_no_radar` |
| "Fiz hoje" em três linhas | ✅ | 07/10: "reais 57 · Treino de IA 27 · total 84"; `test_acertos_do_dia` |
| "Treinar no radar" | ✅ | 12 rodadas de geradas no banco; `test_treinar_pelo_no` |
| "Treinar geral no radar" | 🟢 | Botão em 3 faixas de hoje; `test_treinar_geral`; sem uso que eu possa separar |
| "Abrir no Qconcursos" | 🟢 | URL na faixa; `test_qconcursos`; o link de vários assuntos nunca foi conferido no site (pendência I) |
| "📝 Como foi" | ✅ | Usado agora há pouco (`POST /hoje/faixa/nota` no `web.log`); `test_notas_da_faixa` |
| Plano B e Reduzida | 🟢 | Na tela, e recusado no dia que mede; `test_plano_b`; nunca usado |
| Sábado 10/10 | 🟢 | Tela certa (diagnósticos abrem, sem Plano B e sem Resumo); a rodada só nasce amanhã |
| Sábados 17/10 e 07/11 | 🟢 | Tela e `test_sabado`; dependem de 10/10 |
| Rodada que mede não repete questão (decisão 145) | 🟢 | `test_composicao`; nenhuma rodada `composta` existe ainda |
| "Criar a rodada" em dia passado (03/10) | 🔴 | 2 botões na tela de 03/10 (`hoje.html:1088`): P12 |
| Semanas | ✅ | Abriu; `test_semanas` |
| Fichas e resumos | ✅ | 65 fichas, 5 conferidas, 1 resumo conferido; `test_fichas`, `test_gabarito_escondido` |
| Caderno de erros | ✅ | Abriu; `test_caderno_erros`; os 2 erros vencidos há 9 dias |
| Fila de revisão e "Revisar agora" | ✅ | Home: 20 conteúdos, 15 erradas; `test_estudo`, `test_home` |
| Rodada de revisão espaçada | 🟢 | `test_espacada`; nenhuma criada até hoje |
| Simulado (lista, rodada, relatório, compilado) | ✅ | Abriu as rodadas 16 e 23; `test_simulado`, `test_relatorio` |
| "Começar" do Simulado | 🔴 | Sorteia de qualquer prova, inclusive IESES (`servico/simulado.py:84-122`): P13 |
| Gerada treina, nunca mede | ✅ | `metricas.py:160-170`, `:410-433`; `test_metricas`, `test_desempenho` |
| Gerada rejeitada | 🔴 | A resposta 121 (gerada 43, rejeitada) continua e conta no Treino de IA |
| Macetes | 🔴 | 40 macetes; 14 cartões, com Processo Penal partido em dois (P28) |
| Notificação do Windows (cronômetro) | 🟡 | Pendência D: falta a permissão no navegador |

**Análises**

| Funcionalidade | Estado | Evidência |
|---|---|---|
| Meu foco | 🔴 | "Matérias fracas: LP 46% em 57" sob "medido no radar: das 26 questões" (`home.html:221-225`) |
| Edital | 🔴 | Abriu; "Direito Processo Penal" de 2013 fica fora (P24) |
| Minhas matérias | 🔴 | LEP "57% de acerto" e "anotado 50% em 22" × 48% e "31% em 13" no Edital e no Meu desempenho |
| Meu desempenho | 🔴 | LP 45% em 58 × 46% em 57 nas outras (P20); abriu; `radar desempenho` |
| "Nunca somados na tela" (decisão 21) | 🔴 | O cabeçalho diz isso (`desempenho.html:49`), e a coluna Acerto mostra a soma (`:102`) |
| Incidência | 🔴 | Abriu; `radar incidencia`; "67 questões · 168 provas" conta caderno (P29) |
| Conferência | ✅ | Abriu (2,5 MB); `test_classificacao` |
| Mais e Auditoria | ✅ | Abriram; `test_auditoria_na_tela` |

**Acervo e IA**

| Funcionalidade | Estado | Evidência |
|---|---|---|
| Provas e manifesto | 🟢 | 216 provas e 408 documentos com sha256; `test_provas` (não rodei `provas`) |
| Leitor de questões e texto-base | ✅ | Questões reais na ficha e nos macetes; `test_questoes`, `test_texto_base` |
| `questoes --refazer` | 🟡 | Relê 30 provas sem `--limite`; o README:1034 diz "o acervo inteiro" |
| Complementar aceito | ✅ | `radar padrao`: 172 provas; `test_complementar` |
| Árvore e classificações | ✅ | 438 nós, 708 classificações; Incidência e Conferência; `test_conteudos` |
| Caminho `--pedido` → `--importar` | ✅ | O lote de 09/10 foi importado (4 explicações); `test_ia_manual` |
| Procedência de IA com modelo e data | 🟡 | Novo só com modelo se a resposta declarar (`manual.py:75-78`); sem modelo: 775 geradas, 40 macetes, 706 classificações |
| Gerador pago (API) | 🔴 | Sem chave; quando houver, gera sem o escopo mostrado (`cli.py:1007`, `app.py:1032`) |
| `cobertura` e `assuntos` | 🟡 | Leem a coluna antiga `questoes.assunto`, toda vazia |
| Leis alteradas (`config/leis.yml`) | 🟡 | 15 + 9 itens, todos `conferida: false` |
| Texto local das leis (verificar o artigo citado) | 📄 | Pendência H, "A IA pode fazer" 1 |
| Cronograma por IA | 📄 | Pendência D |

**Rotinas**

| Funcionalidade | Estado | Evidência |
|---|---|---|
| Robô do GitHub | ✅ | `coleta:` em 07, 08 e 09/10, 5 a 7 h depois do cron |
| Backup das 23:30 | ✅ | Logs `RESULTADO: ok`; `radar status`; `test_sincronizar`; 08/10 perdido e feito 09/10 12:05 |
| Web no logon | ✅ | `radar status` (no ar desde 14:20); `radar agendar --status` (Pronto); `test_automacao` |
| Nuvem com login | 📄 | `docs/roteiro_nuvem.md` (decisão 126) |

---

## 8. Melhorias

### 8.1 O que já está na proposta de 06/10

Sem repetir a proposta: só a situação de cada código, conferida no código.

- **Feitos:** P01, P03·U03, P04·U09, P05, P06, P07, P09, P10, P11·U18, P14,
  P30, U02, U21·P36, I1, I3 (a regra), I6 (o texto).
- **Feitos em parte:** P02 (falta o `conferir-dias` cruzar faixa e rodada
  da mesma matéria no mesmo dia); U04 (falta uma definição só de Reduzida);
  I4 (faltam os vencidos do caderno dentro da Correção); I5 (falta a faixa
  avisar a ficha não conferida); U62 (a decisão 139 somou o "Treinar geral"
  aos botões por nó, em vez de um só).
- **Parado por decisão sua:** P08.
- **Faltam e cabem antes de 07/11 pela regra I3** (corrigem número ou
  preparam os sábados), nesta ordem:
  1. **U01 · P12 · P15** - o mais urgente, porque o diagnóstico é amanhã:
     tirar o "Começar treino" da home, travar o sorteio do alvo
     (`servico/simulado.py:239-310`) e esconder o "Criar a rodada" em dia
     passado (`hoje.html:1088`). Tirar a lista "O que estudar agora" também
     resolve um defeito que a proposta não viu: o fator de tempo dela só
     olha a resposta no radar (`servico/inicio.py:116-137`), e
     Constitucional, com 32 anotadas, fica sem data.
  2. **P20**, que agora aparece de verdade (LP 46% em 57 × 45% em 58) - ver
     N1 abaixo, que entra junto.
  3. **I2** (com o **P50**): a faixa que revisa diz se o dia de origem foi
     marcado - vale para os R+7 de 30/09 a 03/10, que não têm registro.
  4. **I4**, a parte que falta, antes de 17/10.
  5. **P13**, só a trava do sorteio (o mesmo vale para a rodada de revisão
     espaçada, `servico/espacada.py:71-76`, que também não filtra a banca).
  6. **P02**, a segunda metade: o `conferir-dias` pegaria o 07/10 (seção 9).
- **Faltam, para depois de 07/11:** todo o resto - U05, U06, U07, U08·P33,
  U10, U11·P19, U12, U13, U14, U15·P18, U17·P21, U19·P26, U20, U22 (ALTA) e
  todos os de prioridade MÉDIA e BAIXA.

### 8.2 Novas - problemas comprovados

| # | Onde | Problema | Mudança sugerida | Benefício | Prior. | Quando |
|---|---|---|---|---|---|---|
| N1 | Meu foco (`home.html:221-225`), Minhas matérias (`servico/materias.py:279-281`) | A legenda "medido no radar: das 26 questões" fica sob "LP 46% em 57" (radar + anotado); em Minhas matérias, "anotado" inclui o com consulta (LEP 50% em 22) e nas outras telas não (31% em 13) | Junto com o P20: cada rótulo diz o seu recorte ("radar + anotado, sem consulta"; "anotado, com e sem consulta") | Um nome, um número, em toda tela | Média | Antes de 07/11, no mesmo lote do P20 |
| N2 | Meu desempenho, Edital, home | A decisão 21, o README:1106 e o cabeçalho do `desempenho.html:49` dizem "nunca somadas num número só"; a coluna Acerto e o "Meu acerto" mostram a soma | Escrever o que a tela faz: "o número é o do estado (radar + anotado, sem consulta); a divisão ao lado". **Muda a decisão 21**, que hoje proíbe a soma na tela, e cumpre o que o P01 já pediu | A regra escrita volta a valer | Média | Depois de 07/11 |
| N3 | `classificador.py:87-92`, `:135-143` | 3 dos 10 "banca definida" são falsos (frase negativa, concurso já aberto); o estágio de Barra Velha virou "Estadual SC" | Exigir a afirmação ("a banca será", "contratou") e recusar negação; órgão estadual não vale em título de estágio ou prefeitura | O sinal de 2 a 4 meses antes do edital volta a ser confiável; nada de 🔔 falso de carreira | Alta | Depois de 07/11 |
| N4 | `acervo.py:74`, `eventos.py:73-80` | O mesmo fato vira dois eventos quando o robô e o notebook o registram em horas diferentes: 8 pares no `eventos.json`, inclusive "apareceu" duas vezes | Chave do evento sem a hora (concurso + tipo + dia, ou + descrição) | Linha do tempo limpa; sem risco de aviso de carreira em dobro | Média | Depois de 07/11 |
| N5 | `coleta.yml:82`, `ARQUIVOS_DO_RADAR` (`cli.py:2419`) | O robô atualiza `data/provas.json` ao achar retificação e não o commita: a mesma retificação seria avisada e gravada todo dia | Pôr `data/provas.json` no commit do robô e no `sincronizar` | Um aviso por retificação | Média | Depois de 07/11 (latente: 0 casos) |
| N6 | `servico/manual.py:1219` | Um `--pedido` apaga o que estava esperando, sem cópia (o do art. 13 se perdeu; a pendência H.6 ainda o cita) | Guardar o pedido anterior em `data/copias/`, ou recusar se o lote anterior não foi importado | Nenhum pedido some | Média | Depois de 07/11 |
| N7 | `servico/manual.py:64-78` | A importação aceita resposta sem `modelo`; o CLAUDE.md pede modelo e data | Recusar a resposta sem `modelo`. **Muda a decisão 116** ("quando a resposta diz") | A procedência completa em todo texto novo | Média | Depois de 07/11 |
| N8 | `collectors/base.py:159-167` | `robots.txt` com erro 5xx ou sem rede libera a coleta; a RFC 9309, que o próprio código cita, manda supor proibição | 4xx libera (como hoje); 5xx e erro de rede pulam aquele site naquela coleta | Cumpre o "sem exceção" do CLAUDE.md | Baixa | Depois de 07/11 |
| N9 | `servico/geradas.py:743-769`, `acervo.py:622-719` | Rejeitar uma gerada apaga a resposta só no banco; o `sincronizar` a traz de volta do `simulados.json` (resposta 121) | Rejeitar também exporta, e o `importar` ignora resposta de gerada rejeitada | O Treino de IA sem resto | Baixa | Depois de 07/11 |
| N10 | README, CLAUDE.md, `pendencias.md` | O README está atrás do código (seção 9); o CLAUDE.md tem números velhos, "três anéis", a PM ausente e "a proposta está feita até 07/11"; a H.6 cita um pedido que não existe mais | Uma passada nos docs; primeiro o CLAUDE.md:239 e o README:70-79 (mandar `parar`/`subir`) | Os docs dizem o que o radar faz hoje | Média | Os dois primeiros já (não mudam o radar); o resto depois |
| N11 | `cli.py:142-150`, `:184-188`; `app.py:584,600,612,1096`; `avisos.py:194-206` | Pequenos: `atualizar` diz "Tudo em dia" com fonte que falhou e, com `--avisar`, pula as carreiras; `voltar=//outro.site` passa em 4 rotas; a retificação vai ao Telegram sem escapar o HTML | Um lote só de consertos pequenos | Menos surpresa no terminal e no Telegram | Baixa | Depois de 07/11 |

O gerador pago, que ignora o escopo (`cli.py:1007`, `app.py:1032`), não
vira item próprio: o U51·P53 da proposta já tira o cartão da API da tela, e
sem chave nada roda.

### 8.3 Novas - ideias a avaliar

| # | Onde | Ideia | Por quê | Prior. | Quando |
|---|---|---|---|---|---|
| A1 | Telegram, aba Acompanhando | Juntar: ou favoritar o que importa, ou tirar o passo "favoritos" do `avisar` e deixar o Acompanhando como o único caminho | Há 0 favoritos; o passo existe e nunca manda nada | Baixa | Depois de 07/11 |
| A2 | Concursos › Todos | Decidir sobre três critérios do CLAUDE.md que a lista não aplica: salário no ranking, elegibilidade no cartão e a cidade de prova pelo PDF. Ou implementar, ou tirar do CLAUDE.md | Hoje o texto promete o que a tela não faz | Baixa | Depois de 07/11 |

---

## 9. Pontos de atenção

**Dados que só você pode confirmar**
- **07/10:** a faixa "Fixação: Trabalho do preso" está anotada 9/7 com
  consulta, e a anotação do dia diz que não havia questão no Qconcursos e que
  você fez "mais questões dentro do radar". No mesmo dia há a rodada 16 (8
  reais de LEP) e a 18 (8 geradas). Se as 9 forem as do radar, é o caso do
  29/09 (P02) - contaria duas vezes no volume e no "anotado com consulta" de
  Minhas matérias (não no acerto sem consulta).
- **08/10:** meta "mínima" sem nenhuma faixa, extra ou resposta.
- **Sem registro:** 30/09, 01, 02 e 03/10 (os R+7 que olham para esses dias
  são revisão ou primeiro contato? É o I2).

**Inconsistências entre documentação e código** (o código manda; os docs
ficam para o N10)
- CLAUDE.md: "três anéis" (são cinco: `estadual` e `indefinida`,
  `regioes.py:13-29`); município por "título/resumo" (só título,
  `classificador.py:264`); Polícia Militar fora da lista (está no
  `alvo.yml:188`); "nada fora de `collectors/` sabe de onde vem o dado"
  (`detalhes.py`, `servico/provas.py`, `servico/acompanhamentos.py` sabem; a
  CL-2 da pendência G cita só parte); 901 geradas (921); 65 resumos (64 por
  conferir); "a proposta está feita até 07/11" (faltam U01·P12 e I2, que a
  própria I3 punha nessa lista).
- README: Hoje (o "Como foi o dia" com números, 498-506; o "fiz" preenchido,
  771; o "Fiz hoje" de uma linha, 805; Resumo em toda faixa, 1085; setas sem
  mínimo, 852; Plano B sem o dia que mede, 615); "não treinei" (307, hoje
  "sem acerto medido"); "não há mínimo escrito no código" (1364; há em
  `home.html:260`, `relatorio.html:85`, `inicio.py:51`); o exemplo `radar
  hoje --marcar ideal --feitas 25 --acertos 18` (597) falha sem `--minutos`;
  "depois de cada atualização" (70-79) não manda reiniciar a web; o
  `sincronizar` (150, 1240) não cita reclassificar e apagar rodadas vazias;
  o `avisar` como "único" que manda mensagem (1262; o robô também roda
  `retificacoes --avisar`) e o teto de "10 por coleta" (1469; é 10 por
  etapa); `--refazer` no "acervo inteiro" (1034); "169 de 183" (1199; são
  172); o macete "sem tela" (1757); a procedência "não é um modelo" (1751;
  hoje é, quando declarado); a hora do robô "6h" (1828).
- Pendências: a H.6 (o pedido do art. 13) não existe mais; a B.8 diz 46 + 29
  abertas, e o banco tem 77 (40 completas, 7 parciais, 30 pendentes).
- Código: comentários que ainda comparam com 03/10 (`cronograma.py:185`,
  `composicao.py:4`, `sabado.py:206`, `metricas.py:662`; o YAML diz
  `compara_com: '2026-10-10'`); `radar extrair`, que não existe
  (`cli.py:3497`, `servico/evidencia.py:86`); o texto das semanas 1 e 2 no
  `cronograma.yml:145-146` ("Sábado = diagnóstico" na semana 1, "40 por
  noite" na 2, que tem 35).

**Números que não são erro, mas confundem**
- `radar padrao` × `radar incidencia` (Penal 13 × 9, Processo Penal 10 × 6):
  o primeiro conta pela matéria do caderno, o segundo pelo nó, sem as 12
  pendentes. A Incidência diz "fora da conta" em cada matéria.
- A coleta conta como "atualizado" o município que só trocou de grafia (os
  "101 atualizados" da FEPESE em 09/10, `coleta.py:177-203`).

**Limitações**
- O alvo tem 2 provas (162 questões válidas); Raciocínio Lógico,
  Sociologia, LEP e Legislação Especial caíram numa só. Toda conta do alvo
  é "base pequena", e a tela diz.
- Português e RL têm poucas questões reais por tema no acervo; a faixa de
  Português começa no radar e termina no Qconcursos (decisão 107).
- 845 das 911 geradas ativas nunca foram feitas; o estoque de 13/10 em
  diante é sob demanda.
- 60 fichas e 64 resumos sem a sua conferência; 109 associados e 77
  classificações do complementar abertas.

**Dependências**
- GitHub Actions atrasa o cron (5 a 7 h nos commits de outubro); o
  Telegram depende dos segredos do repositório (o token antigo foi revogado:
  pendência D).
- O backup depende do Agendador com você logado; a web, do logon.
- Qconcursos é só link: se o site mudar a numeração dos assuntos, o
  `config/qconcursos.yml` fica velho sem aviso.
- Os sites das fontes: se a FEPESE mudar a API, o coletor quebra (a coleta
  segue com as outras e sai com código 0).

**Riscos**
- O que você marca durante o dia só existe no `radar.db` até as 23:30.
- O `sincronizar` apaga sem perguntar as rodadas sem nenhuma resposta
  criadas há mais de 1 dia (é a regra; a rodada de sábado criada e não
  começada some no dia seguinte).
- `radar descartar <id>` apaga sem confirmação.
- Com a pasta suja e o GitHub à frente, o backup falha toda noite até
  resolver à mão; o `radar status` e a tela Mais mostram.
- Servidor sem reiniciar depois de mudar código: Python e YAML antigos (e,
  provável, templates novos com Python velho - não verifiquei).
- Duas conversas do Claude Code no mesmo repositório (a proposta de 06/10 registra um caso)
  podem commitar o trabalho uma da outra.

---

## 10. Glossário

| Termo | O que é |
|---|---|
| Faixa | Um horário do plano do dia (teoria, lei seca, questões, revisão, pausa), com o que fazer. |
| Bloco | Manhã, noite ou depois das 22h; agrupa as faixas. |
| Nó | Um ponto da árvore de conteúdos: matéria › assunto › subassunto › elemento. |
| Alvo | As provas do seu cargo (Polícia Penal SC, FEPESE 2013 e 2019): 170 questões. |
| Complementar | Provas de outros cargos da FEPESE, aceitas por ter matéria do edital: 172 provas; só ordenam, nunca somam com o alvo. |
| Fora | Questões de outra banca (IESES): ficam fora de toda estatística. |
| Gerada | Questão escrita pela IA: treina, nunca mede. |
| Selo | O ícone que diz de onde vem o dado: 🟢 oficial, 🔵 acervo, 🟡 automático, 🟣 IA, 📌 plano. |
| Radar × anotado | Questão respondida no radar × o que você digitou do Qconcursos; o acerto que vale é o sem consulta. |
| Rodada que mede | Diagnóstico, simulado no radar e R+7 dos erros: só questão real, sem correção na hora, sem repetir questão de outra do ciclo. |
| R+7, R+30, 1-7-30 | Revisão 7 e 30 dias depois do estudo; o 1-7-30 é o prazo da fila e do caderno. |
| Ficha e Resumo | O roteiro do tema (o que ler, como a banca cobrou) e a síntese com a fonte de cada frase; você confere. |
| Plano B, Reduzida, Mínima | O dia apertado: o bloco único de 30 ou 60 min; a manhã + parte da noite; o mínimo do dia. Dia que mede não tem Plano B. |
| Pedido / importar | O caminho da IA sem API: `--pedido` → Claude Code → `--importar`. |
| Sincronizar | O backup das 23:30: troca os JSON com o GitHub e reaplica as regras. |

---

## 11. Conclusão

**Como funciona hoje.** O radar está de pé e sendo usado: as 31 telas
abrem, os comandos de leitura respondem, o robô roda todo dia, o backup
fecha em `ok`, e as regras mais importantes do `novo.md` estão no código -
uma fonte só para as contas, a gerada que nunca mede, alvo e complementar
nunca somados, a amostra mínima de um arquivo só, a rodada que mede sem
repetir questão. O ponto fraco não é o cálculo: é **o nome do número** (o
mesmo rótulo para recortes diferentes) e **o que ficou de fora do robô**
(detalhar, elegibilidade, `provas.json`).

**Pontos fortes.** A separação por evidência; a procedência do texto de IA;
o caminho sem API, que funciona de ponta a ponta; o plano do dia que diz a
tarefa concreta; e o volume de testes (117 arquivos, 2.853 testes).

**As melhorias de maior impacto, em ordem.**
1. Antes de amanhã: U01 · P12 · P15 (seção 8.1) - ou, sem código, não
   clicar nos três botões (seção 0).
2. Antes de 07/11: P20 + N1 (um rótulo por recorte), I2, o resto do I4 e a
   trava do P13.
3. Depois de 07/11: N3 (banca definida), N4 e N5 (eventos e retificação), N6
   e N7 (o pedido e a procedência), e a passada nos docs (N10) - com o
   CLAUDE.md:239 e o README:70-79 já.

---

## Anexo: o que rodou e como foi verificado

**Leitura:** CLAUDE.md, `docs/indice.md`, `docs/pendencias.md`,
`docs/proposta_de_melhorias.md`, partes de `docs/decisoes.md`, README e
código. Sete subagentes (Explore), só leitura, um por área: radar de
concursos; Hoje e cronograma; Simulado, geradas, caderno e macetes; análises;
acervo e IA; rotinas e comandos; e a situação da proposta. Os achados que
entraram aqui foram conferidos por mim no código, no banco ou na tela; os que
não deu para conferir estão como suspeita ou ficaram de fora.

**Comandos rodados** (todos só leitura):
- `git status`, `git log`, `git show --stat`, `git diff --stat`,
  `git ls-files`, `git check-ignore`;
- `radar --help`; `radar status`; `radar agendar --status`; `radar hoje`;
  `radar acompanhar`; `radar listar`; `radar desempenho`; `radar
  incidencia`; `radar padrao`; `radar previsao`; `radar repetidas` - todos
  sem opção, todos com código 0;
- `radar web --porta 8001`, fechado no fim; 45 GET nele (as 31 telas, os
  sábados, 03/10 e 07/10, uma ficha, um macete, filtros) e nenhum POST
  (conferido no log dele); 1 GET em `/mais` na sua 8000, para ver se
  continuava no ar;
- `pytest -q tests/test_acompanhamentos.py tests/test_acompanhando.py`: 127
  passed (o único arquivo mudado depois do último registro da suíte é
  `data/acompanhamentos.json`, commit `9b37859`);
- consultas ao `data/radar.db` só com `mode=ro` (SELECT e PRAGMA); leitura
  dos JSON de `data/` e dos logs;
- `sha1sum` de `data/*.json` e do `radar.db` antes e depois de abrir as
  telas.

**O que mudou no dado enquanto eu trabalhava:** os JSON ficaram iguais; o
`radar.db` mudou às 21:03 - foi você, na 8000 (o `web.log` mostra `POST
/hoje/faixa/nota` e `POST /geradas/treinar`, que criou a rodada 25). Os
números deste mapa são de antes disso: 17 rodadas e 140 linhas de resposta
(depois, 18 e 150).

**O que não vi:** o Telegram de verdade, o resultado dos POST (criar rodada,
responder, conferir), a API da Anthropic (sem chave), o Qconcursos, os logs
do Actions (pedem rede) e o servidor depois de uma mudança de template sem
reiniciar. As contagens de palavras deste trabalho incluem o texto dentro de
`<details>` fechado, e por isso não se comparam com as da proposta de 06/10.
