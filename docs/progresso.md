# Progresso — evolução do sistema de estudos

Andamento das etapas do [roteiro](roteiro.md). Cada etapa só é marcada como
concluída quando o critério de conclusão dela foi conferido de verdade.

Legenda: ✅ concluída · 🟡 feita, falta conferir algo · ⬜ não começada.

| # | Etapa | Situação |
|---|---|---|
| 1 | 1A — GitHub Actions verde | ✅ |
| 2 | 1B — Texto de máquina e Previsão | ✅ |
| 3 | 1C — Fonte única das métricas | ✅ |
| 4 | 1D — Conferência dos dados gravados | ✅ |
| 5 | 6A — Rotina nova do Ciclo 1 e ANKI desativado | ✅ |
| 6 | 2 — Estrutura de conteúdos | ✅ |
| 7 | 3A — Classificação do alvo e incidência | ✅ |
| 8 | 3B — Acervo complementar FEPESE | 🟡 acervo e 3 lotes classificados; falta a sua conferência |
| 9 | 4 — Amostra, desempenho e controle de estudo | ✅ |
| 10 | 5 — Geração de questões | ✅ |
| 11 | 6B — Cronograma operacional | 🟡 fichas e prioridade prontas; falta a sua conferência das 61 fichas e o Ciclo 2, depois do simulado de 07/11 |
| 12 | 7A — Selos e marcação de IA | ✅ |
| 13 | 7B — As 6 telas no design system | ✅ |
| 14 | 8 — Auditoria final integrada | 🟡 18 de 19 itens da §23 atendem com o dado real (eram 17: o item 13 foi corrigido em 03/10); 1 virou pendência |
| 15 | Correções depois da auditoria (5 itens) | ✅ os cinco feitos; falta a sua conferência da lista de leis e conferir a primeira noite do backup |
| 16 | O ciclo 1 específico (pedido de 03/10): 2A, 2B, 2C e a seção F | 🔄 2A, 2B e 2C feitas (as faixas que medem, o simulado do Qconcursos, o sábado e o assunto na faixa); falta a seção F |
| 17 | O estoque de geradas até 07/11 (pedido de 03/10) | 🔄 lote 1 de 57 feito (19 questões, banco e JSON 50 → 69); os outros 56 pelo `docs/estoque_de_geradas.md` |

---

## 1A — GitHub Actions verde (01/10/2026)

**Plano conferido contra o código antes de começar:** válido sem mudança. Os
três testes estavam como a pendência A1 descreve, e o arquivo de geradas tem
mesmo 50 questões (30 `do_zero`, 20 `variacao`).

**Commits.**
1. Documentação: as 14 decisões da Etapa 0 no `docs/decisoes.md` (com nota de
   revisão nas decisões que elas substituem: selos, mínimos de amostra, E2 e
   E4) e o "Estado atual" do `CLAUDE.md` com as 50 geradas.
2. Testes: as três trocas, mais `docs/pendencias.md`, `docs/historico.md`, o
   "Estado atual" e este arquivo.

**Arquivos alterados.**
- `tests/test_automacao.py` — compara com `automacao.python_sem_janela()`;
- `tests/test_cronometro.py` — relógio parado em 27/09/2026 no
  `test_sem_javascript_nada_do_cronometro_aparece`;
- `tests/test_avisos.py` — `_concurso` publica em `agora() - timedelta(days=1)`;
- `docs/decisoes.md`, `CLAUDE.md`, `docs/roteiro.md` (nota de que as decisões
  foram registradas), `docs/pendencias.md`, `docs/historico.md`, este arquivo.
- Nada em `src/` nem no `.github/workflows/coleta.yml`.

**Resultado dos testes.**

| Rodada | Resultado |
|---|---|
| Antes da correção, PC (01/10) | falha em `test_sem_javascript_nada_do_cronometro_aparece` |
| Os três arquivos corrigidos | 109 passed |
| Suíte inteira, PC, data real | 1840 passed |
| Relógio simulado em 20/10/2026 | 1840 passed |
| Relógio simulado em 10/11/2026 | 1840 passed |
| Relógio simulado em 15/03/2027 | 1840 passed |
| `test_avisos.py` **antigo** com o relógio em 20/10/2026 | 18 failed (a quebra prevista) |

O relógio simulado usou `time-machine` instalado fora do repositório, num
plugin do pytest de uso único; não virou dependência. Um teste à parte
confirmou que o plugin muda `date.today()` e `agora()`.

**Critério de conclusão.**
- [x] `pytest -q` verde no PC;
- [x] **workflow verde no GitHub (02/10/2026)** — a coleta diária rodou
  sozinha e commitou `adafb03 coleta: 2026-10-02` às 15:13 UTC. O
  `coleta.yml` roda `pytest -q` antes de coletar, e passo que falha aborta o
  job: o commit é a prova de que a suíte passou no Linux;
- [x] pendência A1 fora do `pendencias.md`.

---

## 1B — Texto de máquina e Previsão (01/10/2026)

- Situação: ✅ concluída
- Datas: início 01/10 · fim 01/10

**Plano conferido contra o código antes de começar:** válido. Três ajustes de
execução, sem mudar o objetivo:
1. além de "Situacao: a -> b", a tela mostrava o tipo cru ("inscricoes
   encerradas") e o evento `apareceu` com a situação crua ("como
   edital_publicado"): entraram na A2;
2. o banco real tem 2 transições para trás (inscricoes_abertas →
   edital_publicado). A frase do destino diria "O edital foi publicado", que
   é falso; virou "A situação voltou de inscrições abertas para edital
   publicado";
3. acentos: só o texto que chega à tela web. Terminal, Telegram, prompts de
   IA, relatório de auditoria e nomes de assunto do `macetes.py` ficaram fora
   e estão anotados no `pendencias.md` (D).

**Arquivos alterados.**
- `src/radar/eventos.py` — `para_tela` (descrição → frase), `rotulo_do_tipo`,
  `NOME_DA_SITUACAO`, `FRASE_DA_SITUACAO`. O que é gravado não mudou;
- `src/radar/web/app.py` — filtros `evento` e `tipo_do_evento`;
  `SITUACAO_LEGIVEL` aponta para `eventos.NOME_DA_SITUACAO`; recados de Gerar
  questões com acento;
- templates `home.html`, `foco.html` (Análises), `acompanhando.html` — usam os
  filtros; `previsao.html` — mostra `p.quando`; `calendario.html`,
  `simulado.html`, `questao.html` — acentos;
- `src/radar/servico/previsao.py` — `_este_ano()` (o teste finge a data),
  campos `vencido` e `quando`, frases com plural e acento, vencidos no topo da
  janela. A conta não mudou;
- acentos no texto exibido: `servico/__init__.py` (Calendário),
  `servico/cronograma.py` (erros do diário), `macetes.py` (conselhos),
  `onde_estudar.py`, `substituta.py`;
- testes: `test_eventos.py`, `test_previsao.py`, `test_acompanhando.py`,
  `test_foco.py` (novos); `test_calendario.py`, `test_registro_estudo.py`,
  `test_tela_hoje.py`, `test_plano_b.py`, `test_faixas_do_dia.py`,
  `test_acertos_do_dia.py`, `test_treino_do_alvo.py` (texto esperado agora
  com acento);
- docs: `decisoes.md`, `historico.md`, `pendencias.md` (A2 e A3 saíram),
  `CLAUDE.md` ("Estado atual"), este arquivo.

**Testes novos (29).**
- frase de cada transição (7), transição para trás, ponta a ponta coleta →
  banco cru → frase, `apareceu`, prazo e retificação com acento, texto que não
  é da coleta passa intacto (3), nenhuma combinação de situações deixa `_` ou
  `->`, rótulo do tipo com acento (4);
- telas: home e Análises mostram "O concurso foi autorizado"; Acompanhando
  mostra "As inscrições encerraram" e não "inscricoes_abertas";
- Previsão com o ano fingido em 2026: ano passado vira "Atrasado: era
  esperado em 2025" (a situação continua "esperado"); vencido no topo da
  janela; "este ano" / "há 1 ano" / "há 3 anos"; "o próximo só em 2030";
  "passaram 5 anos do previsto"; a tela `/previsao` sem "ano(s)".

**Resultado dos testes.**

| Rodada | Resultado |
|---|---|
| Arquivos tocados, antes de corrigir `questao.html` | 428 passed, 1 failed (`test_treino_do_alvo`: a mesma frase também estava no `questao.html`) |
| Suíte inteira, PC, depois da correção | **1869 passed** (1840 de antes + 29 novos) |

**Comando real rodado.** `radar web --porta 8765` com o banco real: a
Previsão mostra "Tijucas — Atrasado: era esperado em 2025" no topo de "Na
janela de agora", "um a cada 4 anos. O último foi há 5 anos, é a janela de
agora"; o Calendário mostra "Último dia de inscrição", "Salário" e "O botão".
O banco real não tem evento em concurso-alvo nem favorito, então home,
Análises e Acompanhando mostram "Nada novo". Para vê-las, `radar web --porta
8766` numa **cópia** do banco com um evento "Situacao: inscricoes_abertas ->
encerrado" no alvo, marcado como favorito: as três telas mostram
"inscrições encerradas · As inscrições encerraram" e nenhum valor cru. A
cópia foi apagada; o banco real não foi alterado.

**Critério de conclusão.**
- [x] `pytest -q` verde;
- [x] `radar web` mostrando as frases novas na home, nas Análises e na
  Previsão (home e Análises na cópia do banco, pelo motivo acima);
- [x] A2 e A3 saíram do `pendencias.md` (o resto dos acentos, fora da web,
  ficou no bloco D).

---

## 1C — Fonte única das métricas (01/10/2026)

- Situação: ✅ concluída
- Datas: início 01/10 · fim 01/10

**Plano conferido contra o código antes de começar:** válido; os estados, o
caso de 28/09 e quem refazia a conta batiam com o roteiro. Uma mudança, que
você decidiu antes da implementação: o estudo extra exige minutos, então
`radar hoje --feitas` passou a pedir `--minutos`.

Encontrado no caminho, e consertado pela própria fonte única:
- **Plano B**: a tela Hoje contava as faixas dele, mas Semanas e Minhas
  matérias montavam o dia normal e perdiam essas questões;
- **treino de IA**: entrava no volume da semana e não no da matéria;
- **home**: chamava de "questões" o que eram respostas (evolução);
- **relatório do simulado**: calculava porcentagem e contava erros no
  template.

**Commits.**
1. `f411b5f` — o módulo `servico/metricas.py` e os testes do 28/09;
2. `c97a890` — Hoje e `radar hoje`; o registro do dia guarda só meta e recado;
   `--feitas` vira estudo extra;
3. `dbb154f` — Semanas e Minhas matérias somam a mesma lista; sai a conta
   antiga do `servico/cronograma.py`;
4. Meu foco, Onde estudar, home e relatório (o acumulado, as rodadas e a
   evolução saem do `simulado.py` para o `metricas.py`);
5. docs.

**Arquivos alterados.**
- novos: `src/radar/servico/metricas.py`, `tests/test_metricas.py`;
- serviço: `servico/cronograma.py`, `servico/semanas.py`,
  `servico/materias.py`, `servico/simulado.py`, `servico/inicio.py`,
  `servico/__init__.py`, `foco.py`, `onde_estudar.py`, `cli.py`,
  `web/app.py`;
- telas: `hoje.html`, `semanas.html`, `materias.html`, `foco.html`,
  `home.html`, `relatorio.html`;
- testes ajustados: `test_acertos_do_dia.py`, `test_registro_estudo.py`,
  `test_faixas_do_dia.py`, `test_tela_hoje.py`, `test_semanas.py`,
  `test_materias_na_tela.py`;
- docs: `decisoes.md` (nova seção + nota na E2), `historico.md`, `CLAUDE.md`,
  este arquivo. `pendencias.md` não tinha item desta etapa.

**Testes novos (18, em `test_metricas.py`).** 28/09 reproduzido
("31 = 13 + 8 + 10 de treino de IA", IA 7 de 10 como segundo número); Bônus
com 0 questões; a regra fechando em todos os recortes; total = soma dos
recortes; IA nunca no acerto; rodada não terminada não conta; linha com mais
acertos que questões é acusada; 22h30 e 0h05 no dia certo; mesma questão em
duas rodadas = 2 respostas e 1 questão; o dia igual dentro de um período
maior; tela Hoje e `radar hoje` com a mesma linha; Hoje = Semanas = soma de
Minhas matérias (Numeros idênticos); o mesmo num dia de Plano B; Meu foco e
home lendo o mesmo acumulado do `metricas`.

**Resultado dos testes.**

| Rodada | Resultado |
|---|---|
| `test_metricas.py` (passo 1) | 12 passed |
| Arquivos do passo 2 | 179 passed |
| Arquivos do passo 3 | 186 passed, 3 failed (testes que liam o campo antigo `geradas`; ajustados) → 67 passed |
| Arquivos do passo 4 | 191 passed |
| Suíte inteira, PC | **1885 passed** |
| `test_materias_na_tela.py` + `test_metricas.py`, depois do último ajuste de tela | 49 passed |

**Comando real rodado (banco real, só leitura).**
- `radar hoje --data 2026-09-28` → "Fiz hoje: 31 questões = 13 acertos + 8
  erros + 10 de treino de IA · 3h50 de estudo" e "Treino de IA: 7 de 10
  (70%), fora do acerto"; o "Como foi" mostra só a meta e o recado;
- `radar hoje --data 2026-09-29` → "37 questões = 4 acertos + 18 erros + 15
  sem acerto anotado";
- `radar web` (porta 8767): a tela Hoje de 28/09 e 29/09 com as mesmas
  linhas; Semanas, "Total: 68 questões = 17 acertos + 26 erros + 15 sem acerto
  anotado + 10 de treino de IA" (= 31 + 37); Minhas matérias, home e Análises
  com o recorte "medido no radar" escrito. Nessa conferência apareceu um
  cartão de matéria com "0 questões = 0 acertos + 0 erros" (só minutos); a
  frase passou a aparecer só com questão.

**Critério de conclusão.**
- [x] `pytest -q` verde (1885);
- [x] `radar hoje --data 2026-09-28` e a tela Hoje de 28/09 mostram a conta
  fechada;
- [x] busca no código: fora do `metricas.py`, nenhum serviço ou template soma
  acerto. O que sobra são razões calculadas sobre números que já vêm contados
  (prioridade do Onde estudar e da home, porcentagem de uma faixa ou de uma
  rodada);
- [x] decisão no `decisoes.md`, com a nota do que muda na E2.

**Para a 1D.** As cópias gravadas no registro (28/09: 31/13; 29/09: 37/4)
são iguais ao calculado. O Bônus de 28/09 e o de 29/09 estão marcados com 0
questões e 25 min cada; a pergunta "você fez o Bônus?" continua de pé.

---

## 1D — Conferência dos dados gravados (01/10/2026)

- Situação: ✅ concluída
- Datas: início 01/10 · fim 01/10

**Plano conferido contra o código antes de começar:** válido. O banco real
mostrou três pontos, que você decidiu antes da implementação:
1. **os JSON do diário estavam vazios** (`[]`): 28/09 e 29/09 só existiam no
   `radar.db`, porque o `sincronizar` não rodou desde 28/09. A conferência
   ganhou a coluna "dia fora do JSON", e o `--aplicar` termina exportando;
2. **o Bônus com 0 questões estava em 28/09 e também em 29/09** (o roteiro
   citava só 28/09). Você não fez nenhum dos dois: os dois saem;
3. **regra do 0:** faixa de questões marcada com 0 questões (ou vazio) passa
   a ser recusada pela tela, em vez de aceita com os minutos.

**Arquivos alterados.**
- novos: `src/radar/servico/conferencia.py` (a conferência e o `aplicar`),
  `tests/test_conferencia_dos_dias.py`;
- `src/radar/cli.py` — comando `radar conferir-dias [--de] [--ate] [--aplicar]`;
- `src/radar/acervo.py` — `registros_no_arquivo` e `estados_no_arquivo`;
- `src/radar/servico/cronograma.py` — `anotar_faixa` recusa 0 questões;
- `src/radar/servico/__init__.py` — expõe `servico.conferencia`;
- `tests/test_metricas.py` — o Bônus com 0 do 28/09 entra direto no banco
  (a tela não aceita mais);
- `.gitignore` — `data/copias/` (as cópias de segurança, com o banco);
- dados: `data/registro_estudo.json` e `data/estado_do_dia.json` (o diário
  exportado depois da correção);
- docs: `decisoes.md`, `historico.md`, `CLAUDE.md` ("Estado atual"), este
  arquivo. `pendencias.md` não tinha item desta etapa.

**Testes novos (15, em `test_conferencia_dos_dias.py`).** Dia sem nada
gravado; o 28/09 com o Bônus de 0 como única correção do dado; cópia do
registro que bate e que não bate; treino de IA no dia; acertos maiores que
as questões na faixa e no extra (a conta "não fecha" e a conferência não
para); resposta a questão anulada; check órfão; dia fora do JSON, que some
depois de exportar; a tela recusa 0, "0" e vazio; conferir não muda banco
nem arquivo nem cria cópia; `aplicar` copia antes, tira só o Bônus (órfão e
registro ficam) e a nova conferência bate, com 25 min a menos; `aplicar` sem
nada a corrigir não grava nada; o comando só lê e, com `--aplicar`, corrige
e mostra antes × depois; a linha do dia é a mesma do `metricas`.

**Resultado dos testes.**

| Rodada | Resultado |
|---|---|
| `test_conferencia_dos_dias.py` + `test_metricas.py` + `test_acertos_do_dia.py`, 1ª rodada | 59 passed, 2 failed (um valor de minutos chutado no teste e o JSON lido como texto; os dois testes foram corrigidos) |
| `test_conferencia_dos_dias.py` | 15 passed |
| Suíte inteira, PC | **1900 passed** (1885 de antes + 15 novos), 15 min |

**Comando real rodado (banco real).**
- `radar conferir-dias` (só leitura): 28/09 e 29/09 com o registro batendo
  (31/13 e 37/4), o Bônus "feita, 0 questões, 25 min" e "o registro e os
  checks não estão no JSON"; 28/09 com 10 respostas de IA (7 certas);
  nenhum órfão, anulada ou acerto maior; 30/09 e 01/10 "nada gravado".
  "4 correções propostas. Nada mudou";
- `radar conferir-dias --aplicar`: cópia em
  `data/copias/conferencia-2026-10-01-143927` (radar.db e os dois JSON), e a
  nova conferência sem proposta nenhuma;
- `radar hoje --data 2026-09-28`: "Fiz hoje: 31 questões = 13 acertos + 8
  erros + 10 de treino de IA · 3h25 de estudo".

**Totais antes × depois.**

| Dia | Antes | Depois |
|---|---|---|
| 28/09 | 31 questões = 13 + 8 + 10 de treino de IA · 3h50 | 31 questões = 13 + 8 + 10 de treino de IA · 3h25 |
| 29/09 | 37 questões = 4 + 18 + 15 sem acerto anotado · 3h50 | 37 questões = 4 + 18 + 15 sem acerto anotado · 3h25 |

**Critério de conclusão.**
- [x] relatório rodado no banco real e mostrado;
- [x] correções aprovadas aplicadas (Bônus de 28 e 29/09; diário exportado
  para os JSON), com cópia de segurança antes;
- [x] totais antes × depois conferidos: questões iguais, 25 min a menos em
  cada dia.

---

## 6A — Rotina nova do Ciclo 1 e ANKI desativado (01/10/2026)

- Situação: ✅ concluída
- Datas: início 01/10 · fim 01/10

**Plano conferido contra o código antes de começar:** válido na estrutura,
com os números corrigidos pelo arquivo real e mostrados antes de aplicar:
1. o Anki tinha 15 min nos dias úteis e 10 no sábado (só 28/09 tinha 30), e
   o dia útil ia de 4h10 a 5h10, não 4h25. A economia é de **20 min por dia
   útil**, não 35;
2. outros textos citavam o Anki: as 30 lei secas ("cartões do Anki à
   noite"), o item (3) da revisão semanal e o nome do bloco "Depois das 22h —
   Anki". Reescritos de 02/10 em diante;
3. a faixa do Anki desligada fica na mesma posição, sem duração (tirá-la
   mudaria a posição do Bônus e os checks contam posição).

**Aprovado por você:** a distribuição como proposta; aplicação a partir de
**02/10**; o item (3) do sábado vira "releia os artigos-chave da semana".

**Arquivos alterados.**
- `config/cronograma.yml` — `anki: desativado` no topo, as chaves novas no
  cabeçalho, o bloco "Depois das 22h", e os 32 dias de 02/10 a 07/11 (26
  úteis com a manhã nova, 6 sábados com o item trocado). Script de uso único
  fora do repositório; o trecho antes de 02/10 ficou com o texto idêntico;
- `src/radar/cronograma.py` — chave `anki` (`ativado`/`desativado`, sem a
  chave = ativado), `Faixa.desligada`, `Faixa.consulta` e
  `consulta_por_padrao` lendo a chave, `montar_dia` sem tempo para a
  desligada, `Dia.faixas()` só com as que valem;
- `src/radar/servico/cronograma.py` — a sugestão de meta ignora a desligada;
  ela não se marca; o horário do bloco sai das faixas que valem;
- `src/radar/web/templates/hoje.html` e `src/radar/web/app.py` — a linha
  minimizada "ANKI temporariamente desativado";
- `src/radar/cli.py` — a mesma linha no `radar hoje`;
- `README.md` — "Religar o Anki" e a caixa "com consulta" na fixação;
- testes: `tests/test_rotina_sem_anki.py` (novo); `test_cronograma.py`
  (total do ciclo 1690 → 2054 = + 26 × 14), `test_tela_hoje.py` (28/10:
  60 → 74), `test_caderno_erros.py` (o botão "Anotar erro" aparece na
  fixação da manhã e continua fora da teoria). O `cronograma_mini.yml` não
  mudou: sem a chave, ele carrega como antes;
- docs: `decisoes.md`, `historico.md`, `pendencias.md` (B.3 e B.5 provisórios;
  perguntas 3 e 4 respondidas), `CLAUDE.md` ("Estado atual"), este arquivo.

**Testes novos (16, em `test_rotina_sem_anki.py`).** Sem a chave, ativado;
desativado: a faixa fica no lugar, sem tempo, o Bônus começa às 22h, fora de
`faixas()` e sem baralho; o total não muda e a sugestão dá Ideal sem o Anki;
o Anki desligado não se marca; religar volta igual a antes; valor errado na
chave é erro; `consulta: true` marca a caixa e `consulta: false` desmarca até
a rampa de Direito; tela Hoje e `radar hoje` com a linha minimizada e a
fixação; no arquivo real: Anki desativado sem apagar faixa nem baralho
(36 e 30), **nenhum dia antes de 02/10 mudou** (impressão dos dias), toda
manhã de dia útil com 14 questões (8 com consulta + 6 sem), manhã de 2h15 e
nada do Anki no total, lei seca de 20 min com os artigos-chave do dia, Anki
fora dos textos novos, Plano B montando em todos os dias úteis (30 e 60).

**Resultado dos testes.**

| Rodada | Resultado |
|---|---|
| Arquivos do cronograma, depois das chaves `anki` e `consulta` | 203 passed |
| `test_rotina_sem_anki.py`, 1ª rodada | 15 passed, 1 failed (a contagem de "tipo: anki" pegava os comentários novos; passou a contar "- tipo: anki") |
| Arquivos do cronograma, depois da reescrita do YAML | 173 passed, 2 failed (`test_cronograma` e `test_tela_hoje` fixavam o total antigo; atualizados) → 108 passed |
| Os outros arquivos que leem o cronograma real | 347 passed, 1 failed (`test_caderno_erros`: a manhã agora tem questões; ajustado) → 52 passed |
| Suíte inteira, PC (uma vez, no fim) | **1916 passed** (1900 de antes + 16 novos), 14 min |

**Comando real rodado.**
- `radar hoje --data 2026-10-02`: manhã 10:15–12:30 com "Fixação: Assistência
  ao preso e ao egresso" (8 questões) e "Fixação: Verbo 2" (6), "Lei seca
  dirigida: LEP art. 10; LEP art. 11; LEP art. 26" (11:25–11:45), "ANKI
  temporariamente desativado" e o Bônus às 22:00–22:25; "Total do dia: 39
  questões";
- `radar web` (porta 8771), `/hoje?data=2026-10-02`: as mesmas faixas, a
  linha minimizada, nenhum chip 🃏, o bloco "Depois das 22h"; com o relógio
  em 02/10, a caixa "com consulta" marcada na fixação de Direito e
  desmarcada na de Português;
- **religar testado:** `anki: ativado` → `radar hoje` mostra "22:00-22:15 Anki
  [3] LEP" e o Bônus às 22:15, a tela volta a ter o chip "🃏 [3] LEP";
  `anki: desativado` de novo → a linha minimizada volta, e o arquivo ficou
  idêntico ao de antes da troca.

**Critério de conclusão.**
- [x] a proposta foi aprovada e aplicada;
- [x] a tela Hoje e o `radar hoje` de 02/10 mostram a manhã com questões e o
  ANKI minimizado;
- [x] religar testado (troca a chave, confere, destroca);
- [x] como religar está no README ("Religar o Anki").

---

## 2 — Estrutura de conteúdos (01/10/2026)

- Situação: ✅ concluída
- Datas: início 01/10 · fim 01/10

**Plano conferido contra o código antes de começar:** válido. Os números do
roteiro bateram (170 do alvo, 70 de 2016, 907 da IESES; 11 matérias e 85
assuntos no programa; `assuntos.json` vazio). Três pontos, mostrados antes:
1. **as 20 geradas de Penal** são de "Aplicação da lei penal (arts. 1º a
   12)", que o programa de 2019 **não lista** (Penal tem 5 itens): não havia
   "[assunto do edital]" onde ligá-las. Você escolheu: só "Direito Penal",
   assunto pendente, nenhum nó novo;
2. **cópia da migração** em `data/copias/` (a pasta da 1D), no lugar do
   `data/backup/`: escolha sua;
3. desenho: todo vínculo a um nó é o **caminho de nomes**, também no banco;
   questão sem classificação é pendente sem precisar de linha.

**Arquivos alterados.**
- novos: `src/radar/migracoes.py`, `src/radar/conteudos.py`,
  `src/radar/servico/evidencia.py`, `src/radar/servico/conteudos.py`,
  `src/radar/servico/classificacoes.py`, `config/taxonomia.yml`;
- `models.py` (tabelas `conteudos`, `classificacoes`, `versao_do_banco`;
  `questoes.evidencia`; `conteudo` nas geradas, no caderno de erros e no
  estudo extra), `db.py` (a versão conferida no `criar_tabelas`);
- a regra única: `foco.py` (`_provas_do_alvo` delega; sai o `_e_do_cargo`),
  `servico/simulado.py` (`_questoes_para_o_alvo`), `servico/provas.py`
  (evidência refeita depois de ler os cadernos);
- `acervo.py` (`conteudo` no caderno, no extra e nas geradas; o assunto
  antigo vira classificação), `cli.py` (`radar migrar`, `radar conteudos`;
  `importar`, `exportar` e `sincronizar` com os JSON novos e a evidência);
- `cronograma.py` e `servico/cronograma.py` (a chave `conteudo` da faixa,
  conferida contra a árvore, e no check); `config/cronograma.yml` (6 faixas
  de Português com `conteudo`, todas de 05/10 em diante, e o cabeçalho);
- dados: `data/conteudos.json`, `data/classificacoes.json` (vazio),
  `data/caderno_erros.json` e `data/estudo_extra.json` (não existiam no
  disco), `data/questoes_geradas.json` (só o campo `conteudo`);
- testes: `test_migracoes.py`, `test_conteudos.py`, `test_evidencia.py`
  (novos); `test_foco.py`, `test_treino_do_alvo.py` (questões do alvo agora
  com o concurso de SC: sem estado provado não é alvo), `test_sincronizar.py`
  (os dois JSON novos no commit);
- `.gitignore` (comentário: `data/copias/` também guarda a migração);
  `README.md`; docs: `decisoes.md`, `historico.md`, `pendencias.md`,
  `CLAUDE.md`, este arquivo.

**Testes novos (32).**
- migração: o banco antigo está mesmo no formato antigo; migrar mantém as
  contagens e cria o que falta (98 nós, evidência, ligações); a cópia é feita
  antes e é o banco de antes; migrar duas vezes não duplica nem copia de
  novo; qualquer comando migra sozinho; desfazer devolve o banco como era (e
  guarda o de antes de desfazer); passo que apaga linha é desfeito pela
  cópia; banco novo nasce na versão atual sem cópia; o comando mostra o
  "antes × depois", "nada a migrar" e desfaz;
- árvore: a semente dá as 11 matérias e os 85 assuntos literais (a "Regras
  mínimas da ONU…", e o "espécies" sozinho, defeito do edital); as 2 de 2013
  fora do edital; semear não duplica e o JSON reconstrói; níveis opcionais e
  o elemento com tipo; o tipo segue a família; **tipo novo no YAML funciona
  sem migração**;
- classificação: **sem procedência é recusada**; o status sai da árvore; uma
  principal por questão; **texto antigo que não casa fica pendente**; o JSON
  vai e volta; o JSON recusa linha sem procedência ou com nó inexistente; o
  `assuntos.json` antigo vira classificação;
- textos antigos e cronograma: a prévia não grava; título de faixa vale a
  matéria da faixa; sinônimo de 2013; a chave `conteudo` conferida contra a
  árvore e gravada no check; sem árvore não confere; pendente é a questão sem
  principal (anulada fora); o comando `radar conteudos --pendentes`;
- evidência: a regra de cada prova; `atualizar` grava a coluna; **as duas
  regras antigas dão o mesmo que a nova**; **adicionar prova complementar não
  muda nenhum número do alvo** (incidência, questões do treino, pendentes).

**Resultado dos testes.**

| Rodada | Resultado |
|---|---|
| `test_evidencia.py` | 4 passed |
| `test_migracoes.py`, 1ª rodada | 1 passed, 7 errors (campo `explicacao` inexistente na gerada do teste; corrigido) → 8 passed |
| `test_conteudos.py`, 1ª rodada | falhas por autoflush (o status consultado depois do `add`; corrigido no `classificar`) → 18 passed |
| Arquivos das áreas afetadas (19 arquivos) | 425 passed, 18 failed (16 do `test_treino_do_alvo` e 2 do `test_foco` sem concurso de SC; 1 do `test_sincronizar` com a lista de arquivos; ajustados) → 102 passed |
| Novos com os testes de comando | 28 passed |
| Cronograma real com a chave `conteudo` | 125 passed |
| Suíte inteira, PC (uma vez, no fim) | **1948 passed** (1916 de antes + 32 novos), 17 min |

**Comando real rodado (banco real).**
- ensaio antes, numa cópia do banco e dos JSON no scratchpad: o mesmo
  resultado abaixo;
- `radar migrar`: versão 0 → 1, cópia em
  `data/copias/migracao-v0-para-v1-2026-10-01-163540`. Antes × depois:
  concursos 2848 = 2848, questoes 8433 = 8433, questoes_geradas 50 = 50,
  respostas_de_simulado 80 = 80, simulados 4 = 4, eventos 58 = 58,
  erros_anotados 2 = 2, registros_de_estudo 2 = 2, estados_do_dia 2 = 2;
  novas: conteudos 98, classificacoes 0, versao_do_banco 1. "Nenhuma linha
  perdida". De novo: "Banco já está na versão 1. Nada a migrar";
- evidência no banco: **170 alvo** (2013: 70, 2019: 100), **7.356
  complementar** (o 2016 com as 70), **907 fora**;
- `radar conteudos`: "11 matéria(s) do edital · 2 fora do edital atual · 85
  assunto(s)" — o mesmo que o `edital_programa` lê (11 e 85);
- `radar conteudos --pendentes`: 162 alvo (2019: 95, 2013: 67; as 8
  anuladas fora) · 7.354 complementar em 162 provas · 907 fora.

**Critério de conclusão.**
- [x] migração rodada no banco real, com o "antes × depois" batendo;
- [x] `radar conteudos` mostra a árvore: 11 matérias e os 85 assuntos que o
  `edital_programa.py` lê (mais as 2 fora do edital, marcadas);
- [x] evidência conferida: 170 questões do alvo, as 70 de 2016 como
  complementar;
- [x] pendentes listados (`radar conteudos --pendentes`);
- [x] docs atualizados.

---

## 3A — Classificação do alvo, incidência e padrões (01/10/2026)

- Situação: ✅ concluída. A sua conferência das 162 válidas entrou em
  **02/10/2026** (a tela marca 162 de 162; com as 8 anuladas, 170 de 170).
- Datas: início 01/10 · fim 01/10 (a minha parte)

**Plano conferido contra o código antes de começar:** válido. Três pontos
decididos por você antes:
1. o critério pede as 162 conferidas por você, o que não cabe numa conversa:
   eu classifico as 170 agora e você confere depois (🟡 até lá);
2. Meu foco e Onde estudar por nó ficam para a Etapa 4: contar por nó antes
   da conferência poria classificação não conferida na tela;
3. as 16 questões de 2013 fora do edital atual ganham assunto proposto (4 de
   Direito Administrativo foram para Administração Pública, pelo item do
   edital).

**Mudou no meio, com você:** a primeira importação deu 160 classificações
principais para 170 questões. A impressão é só do enunciado, e a FEPESE
repete enunciado genérico ("De acordo com o Código Penal Brasileiro, é cor-"
em 4 questões de 2019): 16 questões colidiam. A classificação passou a ser
pela **chave da questão inteira** (enunciado + alternativas), com a migração
v3, e a resposta foi importada de novo.

**Arquivos alterados.**
- novos: `src/radar/incidencia.py`, `src/radar/servico/incidencia.py`,
  `config/amostra.yml`, `src/radar/web/templates/conferencia.html`,
  `src/radar/web/templates/incidencia.html`;
- `auditoria.py` — verificações de extração, sem gabarito, classificação por
  prova; `docs/auditoria.md` regerado;
- `servico/manual.py` — o tipo de pedido "classificação";
  `servico/classificacoes.py` — a proposta com as recusas, a conferência, a
  tela, a chave e o JSON antigo pela impressão; `servico/conteudos.py`
  (`garantir`, pendentes pela chave); `questoes.py` (`chave_da_questao`);
- `models.py` (`chave`, `tipo_de_questao`, `pegadinha`), `migracoes.py`
  (passos 2 e 3); `acervo.py` (o assunto antigo pela chave);
- `cli.py` — `radar classificar --pedido/--importar`, `radar incidencia
  [--materia] [--padroes]`; `web/app.py` e `_topo.html` — as abas Incidência
  e Conferência;
- dados: `data/classificacoes.json` (170) e `data/conteudos.json` (a árvore
  com 7 assuntos, 121 subassuntos e 57 elementos novos, todos com origem
  "classificação" e procedência);
- testes: `test_classificacao.py`, `test_incidencia.py` (novos), a fixture
  `tests/fixtures/auditoria/extracao_com_defeitos.json`; acréscimos em
  `test_auditoria.py`, `test_migracoes.py`, `test_conteudos.py`;
- `README.md`; docs: `decisoes.md`, `historico.md`, `pendencias.md` (B.1 e
  B.2 🟡; perguntas respondidas; novas B.6 conferência e B.7 erros de
  extração), `CLAUDE.md`, este arquivo.

**Testes novos (41).**
- auditoria: cada verificação pega o defeito feito para ela (8 defeitos, mais
  uma questão inteira com "Secretaria de Estado" e "Estado de Santa Catarina"
  que não pode disparar nada); o relatório lista suspeitas, sem gabarito e
  classificação;
- importação: recusa sem procedência, sem justificativa (trecho ou item do
  edital), com assunto fora do edital, com tipo fora da lista, elemento sem
  subassunto, tipo de elemento de outra família, matéria trocada e questão
  fora do pedido; pendente fica pendente na matéria, sem nó forçado, e exige
  motivo; a mesma questão duas vezes; lote errado; fora do edital vai para o
  edital só justificado ou ganha assunto próprio; a já conferida não é
  sobrescrita; o pedido sai por matéria só com o alvo (sinônimo de 2013,
  anuladas marcadas);
- conferência: confirmar, corrigir e pendente, e a tela gravando e voltando
  ao mesmo lugar;
- incidência: anuladas e pendentes fora da conta mas mostradas; a questão
  conta no nó e nos de cima; o denominador segue as provas da matéria; toda
  linha leva a amostra; abaixo do mínimo, a frase exata; com a amostra, o
  padrão aparece; o mapa do banco só conta o alvo (uma prova complementar
  não muda nada); página e terminal sem "vai cair", "certamente" ou "sempre
  cobra";
- chave: o JSON antigo pela impressão vira chave (enunciado repetido vira
  pendente em cada questão); a migração v3 faz o mesmo no banco.

**Resultado dos testes.**

| Rodada | Resultado |
|---|---|
| `test_auditoria.py` + `test_auditoria_na_tela.py` | 24 passed |
| `test_classificacao.py`, 1ª rodada | 18 passed, 1 failed (erro do teste: parâmetro com o nome do campo) → 19 passed; com a tela, 1 failed (o `>` escapado como `&gt;`) → 20 passed |
| `test_migracoes.py` + `test_conteudos.py` com o passo 2 | 28 passed |
| Depois da troca para a chave | 68 passed (classificação, conteúdos, migrações, auditoria); migração v3, 10 passed |
| `test_incidencia.py`, 1ª rodada | 7 passed, 2 failed (o teste usou um comando que o `macetes.py` não conhece; e a página dizia "e não o que vai cair" — reescrita) → 9 passed |
| Suíte inteira, PC (uma vez, no fim) | **1989 passed** (1948 de antes + 41 novos), 18 min |

**Comando real rodado (banco real).**
- `radar migrar`: v1 → v2 e v2 → v3, cada uma com cópia em `data/copias/` e
  "Nenhuma linha perdida" (na v3, classificações 169 → 179 pela conversão;
  depois a reimportação e a limpeza dos 9 artefatos deixaram 170);
- `radar classificar --pedido`: 13 pedidos, 170 questões; resposta escrita
  pelo Claude Code; `--importar`: **170 gravadas, 0 recusadas**;
- classificação do alvo: **146 completas, 9 parciais, 15 pendentes** (todas
  com motivo: aplicação da lei penal fora do programa de 2019, inquérito
  policial, LC 472/2009 de 2013, questões que misturam assuntos, uma
  anulada com o texto truncado). Conferidas: 0 de 162;
- `radar auditar`: contagem, gabarito e anuladas batem nas 3 provas; 25
  suspeitas de extração no alvo; a tabela de classificação (2013: 56 / 2 /
  12; 2019: 90 / 7 / 3);
- `radar incidencia --materia "Direito Penal" --padroes`: "9 questões · 2
  provas · apareceu nas 2 provas"; "Tipicidade, ilicitude, culpabilidade,
  punibilidade: 5 questões · 2 provas"; "Infração penal: elementos,
  espécies: não apareceu nas provas analisadas"; fora da conta: 4
  pendentes;
- `radar web`: Análises > Incidência com as 13 matérias (LEP: "9 questões · 1
  prova · apareceu na única prova que cobrava a matéria"); Análises >
  Conferência com "0 de 162" e as 170 questões;
- **a pergunta dos arts. 1º a 12 do CP:** em 2019, **1 questão** (q51, art.
  8º; as alternativas passam pelos arts. 2º, 3º e 4º); em 2013, 3 (q50, q51
  e q53). As quatro pendentes: o tema não está no programa de 2019.

**Critério de conclusão.**
- [x] `docs/auditoria.md` regerado: extraídas × prova, completa/parcial/
  pendente, sem gabarito ou inconsistente, anuladas, erros de extração;
- [x] as 170 questões do alvo classificadas (completa, parcial ou pendente
  com motivo);
- [x] **as 162 válidas conferidas por você** — feito em 02/10/2026;
- [x] `radar incidencia` e a página mostram o mapa com a amostra;
- [x] a pergunta dos arts. 1º a 12 respondida com o número (1 em 2019).


---

## 3B — Acervo complementar FEPESE (01/10/2026)

- Situação: 🟡 **os 5 passos feitos**; falta a sua conferência. O passo 2
  (sua aprovação da lista) virou uma regra, com a autonomia que você deu:
  entra a prova que tem matéria do edital de 2019 e passa na validação. O
  passo 4, a classificação, foi feito em três lotes em 02/10 (abaixo); falta a
  sua conferência das classificações automáticas, por amostra (pendência
  B.8).
- Datas: início 01/10 · fim dos passos 1, 3 e 5 em 01/10

**Plano conferido contra o código antes de começar: NÃO valia como estava.**
Três pontos foram levantados antes de escrever qualquer linha, e você decidiu
os três:

1. **só 2 das 183 provas complementares passariam.** Rodei as verificações da
   auditoria nas 183 (script fora do repositório, só leitura): **161 provas só
   têm gabarito provisório** no acervo, e **o leitor de quadro do edital não
   acha o quadro em nenhuma prova de prefeitura** — ele foi feito para os
   editais do Estado. Passavam só o Socioeducativo 2013 e 2016. O roteiro
   manda deixar fora da estatística a prova sem validação, e isso esvaziaria
   a etapa. **Decidido (A):** o gabarito provisório vira status próprio — a
   prova classifica, mas fica fora dos padrões de cobrança, que se medem
   sobre a letra certa. **Decidido (B):** a validação confere o próprio
   caderno (numeração, alternativas, gabarito, sha256) e registra o quadro do
   edital como "não lido", em vez de dizer que bate;
2. **Direito quase não aparece com o nome da matéria no complementar.** Fora o
   Socioeducativo, as prefeituras jogam tudo em "Conhecimentos Específicos"
   (3.405 questões). **Decidido (C):** o levantamento tem duas colunas, que
   nunca se somam — *pelo nome da matéria* (certo) e *por termo no texto*
   (🟡 indício, a confirmar na classificação);
3. **número do roteiro desatualizado:** ele fala em 25 concursos no manifesto;
   são 38 (37 FEPESE e 1 IESES), com 183 provas complementares no banco.

**Arquivos alterados.**
- novos: `src/radar/complementar.py` (puro: a validação, as duas colunas e as
  respostas da §5), `src/radar/servico/complementar.py` (o levantamento a
  partir do banco e o relatório), `config/complementar.yml` (os termos de
  busca por matéria), `tests/test_complementar.py`, `docs/complementar.md`
  (gerado);
- `src/radar/cli.py` — comando `radar complementar [--caminho]`;
- `src/radar/servico/__init__.py` — expõe `servico.complementar`;
- docs: este arquivo. Nada em `models.py`, nenhuma migração: a 3B até aqui
  **só lê**.

**Testes novos (23, em `test_complementar.py`).** Validação: prova inteira com
definitivo passa; provisório e ausente classificam e ficam fora dos padrões;
numeração com buraco e número repetido; alternativa faltando; questão sem
gabarito (e a anulada, que não é defeito); caderno vazio; **hash repetido com
outro nome é recusado** e sha256 diferente não é repetição. Duas colunas: o
nome conta e o termo é indício à parte; questão que já tem matéria própria não
vira indício de outra; matéria sem nada diz isso sem afirmar o que não sabe.
Do banco: o levantamento só lê o complementar; o tipo do gabarito vem do
manifesto; **os números do alvo não mudam quando prova complementar entra**;
as 6 perguntas da §5 respondidas pela fixture; o relatório mostra o motivo de
cada prova fora, diz que as evidências nunca se somam e não tem texto com cara
de previsão; o comando escreve o relatório e **não muda o banco**; sem prova
complementar ele avisa; os termos vêm do config; o manifesto real tem sha256.

**Resultado dos testes.**

| Rodada | Resultado |
|---|---|
| `test_complementar.py`, 1ª rodada | 22 passed, 1 failed — a fixture dava o mesmo enunciado às duas questões do alvo, e a chave da classificação é enunciado + alternativas: classificar uma classificava as duas (o defeito era do teste, e é o mesmo que a 3A achou nas 16 questões reais) |
| `test_complementar.py`, depois da correção | 23 passed |
| Suíte inteira, PC | **2012 passed** (1989 de antes + 23 novos) |

**Comando real rodado (banco real, só leitura).** `radar complementar`:

- **183 provas complementares, 7.356 questões.** 22 validadas (extração
  inteira e gabarito definitivo), 106 só para classificar (gabarito provisório
  ou ausente), 55 recusadas — 31 por extração e 24 por PDF repetido;
- por matéria, pelo nome: Língua Portuguesa 1.478 em 175 provas · Noções de
  Informática 334 em 63 · Raciocínio Lógico 300 em 60 · Direitos Humanos,
  Direito Constitucional e Legislação Estadual 20 em 2 cada · Direito
  Administrativo 12 em 2 · Direito Penal e Direito Processual Penal 4 em 2;
- **Lei de Execução Penal: zero**, nem pelo nome nem por termo. O relatório
  escreve a frase padrão de evidência insuficiente e diz que isso é sobre o
  ACERVO, não sobre o que a FEPESE já cobrou;
- por termo (🟡 indício): Direito Penal 139 em 76 provas · Direito
  Constitucional 57 em 40 · Administração Pública 56 em 25 · Direitos Humanos
  37 em 25 · Sociologia Aplicada 35 em 30;
- a incidência do alvo conferida antes e depois: **igual**.

**Dois achados para a sua decisão, no relatório.**
1. **24 provas com o PDF repetido:** o mesmo sha256 em dois endereços. Parte é
   o mesmo caderno em http e https (os três de Florianópolis 2025); parte são
   dois hotsites de Palhoça (2024 emergencial e 2024 PS educa) com o mesmo
   arquivo `S07.pdf` e cargos diferentes — e no banco as duas provas têm só 24
   das 40 questões em comum. Ou a mesma prova entrou duas vezes, ou o hash do
   manifesto está errado para elas. Nenhuma das duas coisas foi mexida;
2. **31 provas com a numeração furada:** 26 delas são cadernos de 39 questões
   de 2023 e um caso é um caderno de 40 em que falta a questão 20. É o mesmo
   tipo de defeito da pendência B.7, agora no complementar.

**Critério de conclusão.**
- [x] `docs/complementar.md` gerado e mostrado;
- [ ] **lista aprovada por você** — é o próximo passo, e a etapa está parada
  aqui;
- [ ] provas escolhidas validadas e classificadas;
- [ ] a incidência mostra alvo e complementar separados, cada um com a
  amostra.

### 3B, segunda parte: quem entra no acervo e a linha complementar (01/10)

**O que você decidiu nesta parte.** Autonomia para eu escolher as provas, com
o critério: entra a prova que tem matéria do **edital de 2019** (Sociologia
Aplicada, LEP, Legislação Estadual, Direito Processual Penal, Legislação
Especial, Direito Penal, Administração Pública, Direito Constitucional,
Direitos Humanos, Raciocínio Lógico, Língua Portuguesa).

**O que medi antes de aplicar, e que vale você saber:** das 175 provas que se
qualificam, **173 entram só por Português e Raciocínio Lógico**. Só o
Socioeducativo 2013 e 2016 trazem Direito, Direitos Humanos e Legislação
Estadual. Matéria fora do edital de agora (Noções de Informática, Direito
Administrativo, Temas de Educação) não serviu de motivo para entrar.

**Arquivos alterados (segunda parte).**
- `src/radar/complementar.py` — `Registro`, `decidir` (a regra do edital) e
  `LinhaComplementar` (a linha da §4);
- `src/radar/incidencia.py` — `complementar_por_no`, separada da conta do alvo;
- `src/radar/servico/complementar.py` — o arquivo de status
  (`data/acervo_complementar.json`): gravar, carregar, preservar a data de
  inclusão, e `provas_aceitas()`;
- `src/radar/servico/incidencia.py` — `ocorrencias_complementares()` e
  `linhas_complementares()`, só das provas aceitas;
- `src/radar/cli.py` — `radar complementar --aplicar`; a coluna "Complementar
  FEPESE" e a linha dupla no `radar incidencia`;
- `src/radar/web/app.py` e `incidencia.html` — a coluna e a linha dupla na
  tela, com "as duas nunca se somam";
- dados: `data/acervo_complementar.json` (novo, versionado);
- docs: `decisoes.md`, `historico.md`, `pendencias.md` (a pergunta 1 do bloco B
  respondida; novas B.8 e B.9), `CLAUDE.md`, este arquivo.

**Testes novos (13, total de 36 no arquivo).** Prova sem matéria do edital não
entra; com matéria e extração inteira entra; com matéria e extração furada não
entra; com provisório entra com o aviso. O `--aplicar` grava o arquivo com
hash, matérias e data; a data de inclusão **não muda** quando o comando roda de
novo; **sem o arquivo, nenhuma prova entra na estatística**; depois de aplicar
a linha aparece, e nada conta abaixo da matéria sem classificação; a prova
recusada fica fora; **a linha do alvo não muda**; a tela e o terminal mostram
as duas linhas com "as duas nunca se somam"; anulada fica fora; o comando sem
`--aplicar` não grava.

**Resultado dos testes.**

| Rodada | Resultado |
|---|---|
| `test_complementar.py` | 36 passed |
| `test_incidencia.py` + `test_complementar.py` | 32 passed (antes dos 13 novos) |
| Suíte inteira, PC | **2025 passed** |

**Comando real rodado (banco real).**
- `radar complementar --aplicar` (11 s): **122 provas no acervo**, 22 também
  nos padrões de cobrança, 61 fora com o motivo. `data/acervo_complementar.json`
  com 183 registros (122 com `incluida_em: 2026-10-01`, 61 com `null`);
- `radar incidencia --materia "Direito Penal"`: "Polícia Penal SC: 9 questões ·
  2 provas · Acervo complementar FEPESE: 4 questões · 2 provas (4 sem
  classificação ainda) (as duas nunca se somam)";
- Língua Portuguesa: "22 questões · 2 provas" do alvo contra "993 questões ·
  122 provas (993 sem classificação ainda)" do complementar;
- `radar web` (porta 8790), Análises > Incidência: as duas linhas lado a lado
  nas 13 matérias e a coluna "Complementar FEPESE" na tabela.

**Critério de conclusão (atualizado).**
- [x] `docs/complementar.md` gerado e mostrado;
- [x] lista definida — pela regra do edital de 2019, com a consequência medida
  e registrada;
- [~] provas escolhidas **validadas** (122 de 183, cada recusa com o motivo);
  **não classificadas** — é a pendência B.8;
- [x] a incidência mostra alvo e complementar separados, cada um com a
  amostra.

### 3B, passo 4 (lote 1): as 80 do Socioeducativo classificadas (02/10)

**O que foi feito.** O fluxo de pedido/importação da 3A passou a servir ao
complementar, e o primeiro lote — o que eu sugeri e você aprovou — foi
classificado: as 80 questões de Direito, Direitos Humanos e Legislação
Estadual do Socioeducativo 2013 e 2016.

**Arquivos alterados.**
- `src/radar/servico/manual.py` — `pedido_de_classificacao` com
  `de_evidencia` (alvo ou complementar; complementar só traz prova aceita no
  acervo) e `materia` aceitando uma lista; `INSTRUCAO_CLASSIFICACAO_COMPLEMENTAR`;
  código da questão com sufixo quando duas provas do mesmo ano caem no lote;
- `src/radar/cli.py` — `radar classificar --evidencia` e `--materia` repetível;
- dados: `data/classificacoes.json` (80 novas) e `data/conteudos.json` (os nós
  de subassunto e elemento que a classificação criou);
- docs: `decisoes.md`, `historico.md`, `pendencias.md` (B.8 passa a 🟡; nova
  B.10), este arquivo.

**Testes novos (5, total de 41 no arquivo).** O pedido do complementar só traz
prova aceita (sem o arquivo de status, não traz nada); a instrução do
complementar avisa que não é a prova do meu cargo e que o número não entra na
incidência do alvo; o pedido do alvo continua só com o alvo; evidência
inexistente é recusada; **classificar o complementar inteiro não muda nenhum
número do alvo**, e o complementar passa a contar abaixo da matéria.

**Resultado dos testes.**

| Rodada | Resultado |
|---|---|
| `test_complementar.py`, 1ª rodada | 40 passed, 1 failed — a fixture dava o mesmo enunciado às três questões do Socioeducativo, e a chave as unia numa só (o mesmo defeito que a 3A achou nas 16 reais). Fixture corrigida |
| `test_complementar.py` | 41 passed |
| `test_classificacao.py` + `test_ia_manual.py` | 40 passed |
| Suíte inteira, PC | **2030 passed** |

**Comando real rodado (banco real).**
- `radar classificar --pedido --evidencia complementar --materia ...` (6
  matérias): 6 pedidos, 80 questões;
- `radar classificar --importar data/resposta_ia.json`: 1ª rodada 79 gravadas
  e **1 recusada** (tipo de elemento "parágrafo" não existe na família de
  Direitos Humanos no `config/taxonomia.yml` — a recusa estava certa);
  corrigido para "artigo", 2ª rodada **80 gravadas, 0 recusadas**;
- resultado: **62 classificadas, 18 pendentes com motivo**;
- `radar incidencia --materia "Direitos Humanos"`: "Polícia Penal SC: 24
  questões · 2 provas · Acervo complementar FEPESE: 18 questões · 2 provas",
  e agora com linha por nó (Corte Interamericana: 3 no complementar, 0 no
  alvo);
- **o alvo conferido depois da importação:** os 170 continuam 146 completas,
  9 parciais e 15 pendentes, e nenhuma classificação do alvo foi escrita na
  data de hoje. Também conferi que **não há uma única chave repetida entre
  alvo e complementar** no acervo real.

**As 18 pendentes, por motivo.** 8 por bloco de matéria trocado no caderno
(pendência B.10, achada aqui); 4 da LC 472/2009 (o edital de 2019 cobra a LC
675); 3 de instrumentos de infância e juventude (Regras de Riad, de Beijing e
a Convenção de 1989: tema do concurso socioeducativo, fora do meu programa de
Direitos Humanos); 2 da Constituição do Estado de SC (o programa lista só a
Lei 6.745, a LC 675 e a LC 529); 1 de tortura (Lei 9.455/1997, que no meu
edital é Legislação Especial, e o bloco do caderno dizia Direito Penal).

**O que falta na 3B.** Os lotes 2 e 3 da pendência B.8: os blocos
"Conhecimentos Específicos" das provas de segurança e fiscalização, e depois
Português e Raciocínio Lógico. E a conferência por amostra destas 80 é sua.

### 3B, passo 4 (lotes 2 e 3): blocos genéricos e catálogo (02/10)

**Lote 2 — blocos genéricos.** Nas prefeituras o caderno não diz a matéria
("Conhecimentos Específicos"), então a matéria virou pergunta: o pedido vai
marcado `bloco_generico`, leva a árvore inteira, e a resposta diz em que
matéria do edital a questão cai. Pendente aqui **não vira linha** — sem
matéria no caderno não há onde pendurá-la.

**Corrigido no caminho, defeito meu:** a busca por termo casava pedaço de
palavra — "dolo" dentro de "dolorosa" levava questão de enfermagem para
Direito Penal. Passou a casar **palavra inteira**, e só isso derrubou o lote
de Direito Penal de 45 para 2 questões. Também passei a mandar cada questão
**uma vez só** (a mesma questão em dois cadernos é uma questão), e a conferir
repetição de código **por lote** (o código "2024-q29" existe em vários lotes,
em provas diferentes).

**Lote 3 — Portugués e Raciocínio Lógico pelo catálogo.** `radar classificar
--catalogo` usa o catálogo de palavras-chave do `macetes.py`, com o mapa para
o texto literal do edital no `config/complementar.yml`. A proposta é
automática 🟡 e a tela de conferência escreve "classificação automática,
conferida por amostra".

**Achado que mudou a conta.** As 993 ocorrências de Português no complementar
são **184 questões distintas**: a FEPESE repete o mesmo caderno em dezenas de
cargos do mesmo concurso. A linha complementar passou a contar **questões
distintas**, com as ocorrências entre parênteses — dizer 993 faria o acervo
parecer cinco vezes maior do que é. A contagem do alvo não muda: lá cada
caderno é um concurso diferente.

**Arquivos alterados.**
- `src/radar/complementar.py` — `procurar()` (palavra inteira) e
  `LinhaComplementar` com `ocorrencias`;
- `src/radar/incidencia.py` — a linha complementar conta por chave;
- `src/radar/servico/manual.py` — `genericos=True`,
  `INSTRUCAO_CLASSIFICACAO_GENERICA`, `_materia_sugerida_por_termo`, uma
  questão por chave no pedido, repetição por lote, `fora_do_edital` no
  resultado da importação;
- `src/radar/servico/classificacoes.py` — matéria escolhida no bloco
  genérico, `PendenteSemMateria`, `propor_pelo_catalogo`;
- `src/radar/servico/complementar.py` — `carregar_mapa_do_catalogo`,
  `classificar_pelo_catalogo`;
- `src/radar/cli.py` — `--genericos` e `--catalogo`; `conferencia.html` — o
  aviso 🟡;
- `config/complementar.yml` — o mapa catálogo → edital e a nota da palavra
  inteira; dados: `data/classificacoes.json`, `data/conteudos.json`,
  `docs/complementar.md`;
- docs: `decisoes.md`, `historico.md`, `pendencias.md`, este arquivo.

**Testes novos (9, total de 50 no arquivo).** O pedido genérico só pega bloco
sem matéria minha; o termo casa palavra inteira e não pedaço; a matéria vem na
resposta e sem ela é recusada; matéria fora do edital é recusada; pendente em
bloco genérico fica sem linha; o catálogo propõe e marca a procedência; o
catálogo não chuta com dois assuntos nem com nenhum; não sobrescreve
classificação existente; a mesma questão em vários cadernos conta uma vez.

**Resultado dos testes.**

| Rodada | Resultado |
|---|---|
| `test_complementar.py`, 1ª rodada dos novos | 48 passed, 2 failed — eu é que errei as expectativas: "concordância verbal" casa dois assuntos do catálogo (e o certo é ficar sem linha), e a numeração do caderno de teste tinha de fechar |
| `test_complementar.py` | 50 passed |
| `test_complementar.py` + `test_incidencia.py` + `test_classificacao.py` | 70 passed |
| Suíte inteira, PC | **2039 passed** |

**Comando real rodado (banco real).**
- `radar classificar --pedido --evidencia complementar --genericos`: 11 lotes,
  125 questões; importação: **44 gravadas, 81 sem linha**, 0 recusadas;
- `radar classificar --catalogo --evidencia complementar --materia "Língua
  Portuguesa" --materia "Raciocínio Lógico"`: **92 + 16 propostas**; sem linha
  em Português 47 sem palavra do catálogo, 23 ambíguas, 22 sem par no edital;
- o complementar hoje, por matéria (distintas · classificadas): Português
  187 · 95 · Raciocínio Lógico 45 · 16 · Constitucional 34 · 34 · Direitos
  Humanos 21 · 19 · Administração Pública 21 · 21 · Legislação Estadual
  20 · 10 · Processual Penal 6 · 2 · Penal 5 · 4 · Legislação Especial 5 · 5;
  **LEP e Sociologia seguem em zero**;
- o alvo conferido de novo: as 13 matérias com os mesmos números e as mesmas
  pendentes de antes dos três lotes.

**O que falta na 3B:** a sua conferência (as 44 do lote 2 uma a uma, as 108 do
catálogo por amostra) e, se você quiser, ampliar o catálogo para cobrir o que
ficou sem linha. Detalhe na pendência B.8.


### Fechamento da 3A e as anuladas fora da conferência (02/10)

Você conferiu as 170 do alvo (162 válidas + as 8 anuladas), e com isso a 3A
fecha. A procedência de cada linha continua "Claude Code, importado
manualmente": confirmar marca a data da conferência, não reescreve quem
classificou — é isso que deixa auditável que a proposta foi de IA e a
conferência foi sua.

**Mudança pedida por você:** a tela Conferência não lista mais as **anuladas**.
A banca desfez a pergunta, elas não entram em conta nenhuma (nem na
incidência), e conferi-las não muda número algum. Os dois totais continuam à
vista ("162 de 162 válidas · 170 de 170 contando as anuladas") e a caixa
"mostrar as anuladas" traz de volta quando você quiser.

**Arquivos alterados.** `src/radar/servico/classificacoes.py` (`com_anuladas`),
`src/radar/web/app.py`, `conferencia.html`, `tests/test_classificacao.py`
(2 testes novos), e os docs. **Testes:** `test_classificacao.py` 22 passed.

**Antes da Etapa 4, uma coisa que falta e que não dá para fazer na tela:** a
conferência do **complementar** (as 44 do bloco genérico e as 108 do catálogo)
não existe ali — a tela de Conferência lista só o alvo. Ou a tela ganha o
filtro de evidência, ou o complementar segue não conferido, marcado como está.
Isso **não** bloqueia a Etapa 4, que depende do alvo.

---

## 4 — Amostra, desempenho por conteúdo e controle de estudo (02/10/2026)

- Situação: ✅ concluída
- Datas: início 02/10 · fim 02/10

**Plano conferido contra o código antes de começar: válido.** Item por item: o
`config/amostra.yml` tinha só a seção `acervo`; os três mínimos estavam onde o
roteiro descreve (`onde_estudar.py` com 5 e 3, `servico/materias.py` com 20,
`servico/erros.py` com 3); `servico/desempenho.py` e `servico/estudo.py` não
existiam; as metas por matéria estavam no `config/cronograma.yml` e a da prova
é 79/100; `ErroAnotado.conteudo` e `EstudoExtra.conteudo` já existiam como
coluna (Etapa 2) e **ninguém escrevia neles**.

**Quatro ajustes de execução, mostrados antes de implementar:**
1. **`metricas.Lancamento` e `cronograma.FaixaFeita` não levavam `conteudo`** —
   o check do dia gravava e a leitura descartava. Sem isso o recorte *anotado*
   não chegaria ao nó. O campo entrou na fonte única, não num módulo paralelo;
2. o recorte *medido no radar* por nó sai da tabela `classificacoes` **pela
   chave** (enunciado + alternativas, da 3A), e não de `questoes.assunto`, que
   em Direito é vazio;
3. `espacada.py` continua agendando a rodada pelo assunto do catálogo; a revisão
   por nó nasceu no `estudo.py` lendo o mesmo histórico, sem fila paralela;
4. **consequência medida e avisada:** o banco real tem **12 respostas reais**.
   Com os mínimos da decisão 6, quase toda linha do *medido no radar* vira
   "Amostra insuficiente" — é o comportamento pedido na §16, e a tela fica
   visivelmente mais vazia de porcentagem do que estava.

**Mudou no meio:** o módulo não pôde se chamar `servico/desempenho.py`, como o
roteiro propunha — `servico.desempenho()` já é função na fachada, e é o
desempenho por **matéria**. Virou `servico/desempenho_por_conteudo.py`
(decisão 25).

**Arquivos alterados.**
- novos: `src/radar/amostra.py` (puro: os mínimos e os cinco estados),
  `src/radar/servico/desempenho_por_conteudo.py`,
  `src/radar/servico/estudo.py`, `src/radar/web/templates/desempenho.html`,
  `tests/test_amostra.py`, `tests/test_desempenho.py`, `tests/test_estudo.py`;
- `config/amostra.yml` — a seção `desempenho` (mínimos por nível, corte dos
  60%, meta padrão, o que faz "bom desempenho");
- os mínimos trocados: `onde_estudar.py` (`montar(..., minimos=)`, e o mínimo
  viaja **na linha**), `foco.py`, `servico/inicio.py`, `servico/materias.py`,
  `web/app.py` (os globais do Jinja saem do config);
- `servico/erros.py` — o porquê de o 3 dele ficar, escrito no arquivo;
- o `conteudo` na fonte única: `servico/metricas.py` (`Lancamento.conteudo`),
  `servico/cronograma.py` (`FaixaFeita.conteudo`, `_conferir_o_no`,
  `anotar_faixa(..., conteudo=)`);
- o seletor: `servico/extra.py` e `servico/erros.py` (`conteudo` conferido
  contra a árvore), `web/app.py` (`opcoes_de_conteudo`, os três POST),
  templates `hoje.html` (faixa e extra) e `erro_novo.html`;
- a decisão 7: `foco.py` (`_acerto_por_materia` soma o anotado;
  `divisao_por_materia`; `_acerto_por_assunto` soma o anotado),
  `servico/inicio.py` (a home lê o mesmo desempenho), `foco.html` e `home.html`;
- a tela e o comando: `_topo.html` (a sub-aba), `web/app.py`
  (`/analises/desempenho`), `cli.py` (`radar desempenho`);
- testes ajustados pelos mínimos novos: `test_minimo.py` (lê o config em vez de
  importar constante), `test_onde_estudar.py`, `test_foco.py`, `test_home.py`,
  `test_espacada.py`;
- docs: `decisoes.md` (decisões 19 a 26), `historico.md`, `pendencias.md` (a
  **B.11** nova: os blocos minimizáveis da aba Hoje, pedidos por você no meio
  desta etapa e deixados para conversa própria), `CLAUDE.md`, este arquivo.

**Testes novos (72).**
- `test_amostra.py` (17): os mínimos vêm do arquivo real; **mudar um valor no
  YAML muda o comportamento** (mínimo 4 mede com 4; corte em 90 põe 85% em
  "precisa revisar"); arquivo sem a seção e arquivo inexistente usam os valores
  da decisão; nível desconhecido usa o da matéria; as bordas: 19/20, no mínimo
  exato, 55%/60%, exatamente na meta, o dobro do mínimo com 1 e com 2 dias, o
  dobro abaixo da meta, matéria sem meta usa a da prova, o subassunto com 6;
  sem resposta a porcentagem é desconhecida e não zero; a frase da amostra
  pequena diz o mínimo do nível; **nenhum mínimo de amostra fora do config**
  (conferido por busca no `src/`);
- `test_desempenho.py` (31): a resposta conta no nó e nos de cima; o anotado
  entra no nó escolhido e sobe; a divisão mostra as duas metades e nunca a
  soma, com travessão na vazia; com consulta fica no volume e fora do estado;
  IA nunca conta; questão sem classificação e anotação sem conteúdo contam em
  nó nenhum; "fiz e não anotei quantas acertei" é volume sem acerto;
  classificação para nó apagado não faz o nó renascer; o estado sai do nível do
  nó; dois dias contam para o estado mais alto; o recorte padrão é o ciclo; a
  tela em ordem de árvore com recuo, filtrada por matéria, com a frase da
  amostra pequena; nó sem resposta não entra; o anotado por matéria e por
  assunto, e o nó que para na matéria não vira assunto; a faixa recusa nó de
  fora do ramo dela e nó que não existe; sem escolher nada vale o nó da faixa;
  a página mostra estado, divisão e amostra, convida quando não há dado, não
  tem texto com cara de previsão e **não usa JavaScript**;
- `test_estudo.py` (24): sem nada tudo é não estudado; faixa de teoria deixa
  estudado (e o filho **não** herda); faixa de questões deixa praticado e não
  estudado; extra de teoria deixa estudado; os dois rótulos juntos; os não
  estudados listam a matéria e não os filhos dela, e descem quando o pai foi
  estudado; a evolução semanal igual à da tela Semanas no mesmo período, e o
  que teve consulta fica fora dela; os três gatilhos de revisão (prazo, erro no
  radar, erro no caderno, desempenho abaixo do corte) e os motivos acumulados
  na mesma linha; o que eu nunca estudei não entra na fila; acertar na data do
  vencimento empurra o prazo e tira o nó da fila; o mais atrasado primeiro; o
  refazer separa radar e caderno e nunca soma, por nó e no total; sem erro a
  lista está vazia; gerada errada não entra.

**Resultado dos testes.**

| Rodada | Resultado |
|---|---|
| `test_amostra.py` + `test_minimo.py`, depois da troca dos mínimos | 28 passed |
| Áreas tocadas pelos mínimos (`test_onde_estudar`, `test_foco`, `test_home`, `test_materias_na_tela`) | 121 passed, 4 failed — os quatro contavam com os mínimos antigos (5 na matéria, 8 no assunto); atualizados → 94 passed |
| `test_metricas` + `test_faixas_do_dia` + `test_registro_estudo` + `test_caderno_erros`, depois do `conteudo` na fonte única | 111 passed |
| `test_desempenho.py`, 1ª rodada | 20 passed, 7 failed — a troca do corpo do `_check_da_faixa` não tinha sido aplicada (o comentário no arquivo era outro) e o `conteudo` escolhido não chegava ao check; corrigido → 27 passed |
| `test_estudo.py`, 1ª rodada | 18 passed, 4 failed — três erros meus no teste (a API do `semanas.montar`, um motivo de erro que não existe, um erro anotado que ainda não estava vencido) e **um defeito real**: a âncora do 1-7-30 era a última prática, e não o primeiro contato, então a etapa nunca andava. Corrigido no `estudo.py` → 22 passed |
| `test_desempenho.py` + `test_estudo.py` + `test_amostra.py` | 72 passed |
| Arquivos das áreas tocadas (13 arquivos) | 368 passed |
| Suíte inteira, PC, 1ª rodada | 2112 passed, **1 failed** — `test_espacada.py::test_com_treino_o_tempo_sem_revisar_entra_na_conta`: ele treinava 5 questões, que era o mínimo antigo da matéria. Com 20, a matéria conta como não treinada e o fator de tempo fica neutro — que é exatamente o que o mínimo existe para fazer. O teste passou a treinar `amostra.carregar().do_nivel("materia")` questões → 14 passed |
| Suíte inteira, PC, depois da correção | **2113 passed** (2039 de antes + 72 novos + 2 da tela e do comando), 19 min |

**Comando real rodado (banco real, só leitura).**
- `radar desempenho`: as 10 linhas que existem — Língua Portuguesa
  "radar 25% em 8 · anotado —", e abaixo dela os assuntos e subassuntos, todos
  "Amostra insuficiente" com a amostra ao lado ("2 de 8 respostas sem
  consulta"). O rodapé escreve os mínimos do config e as duas listas de
  refazer, separadas;
- `radar desempenho --revisar`: 10 nós na fila, cada um com o motivo
  ("erro recente · prazo de revisão vencido (1 dia(s))") e o atraso de 2 dias;
- `radar web`, `/analises/desempenho`: as quatro seções (o que respondi, o que
  voltou para revisão, o que ainda não estudei — 24 matérias —, e as questões a
  refazer: 10 erradas no radar e 2 no caderno). O filtro de matéria e de
  período funciona pelo botão "Ver", sem JavaScript;
- o anotado está vazio no banco real porque as faixas com `conteudo` começam em
  **05/10** (Etapa 2): o seletor passa a ter efeito a partir dali. Nenhum dado
  foi alterado nesta etapa.

**Critério de conclusão.**
- [x] **nenhum mínimo de amostra fora do `config/amostra.yml`** — conferido por
  busca, e o teste `test_nenhum_minimo_de_amostra_fora_do_config` guarda isso.
  O 3 do caderno de erros fica, documentado nos dois arquivos: ele mede fatia
  de motivo, não acerto;
- [x] a página "Meu desempenho" mostra estado e amostra por nó, com dados
  reais;
- [x] a definição de "estudado" registrada no `decisoes.md` (decisão 20).

---

## B.11 — Os blocos da aba Hoje dobram (02/10/2026)

- Situação: ✅ concluída
- Não é etapa do roteiro: é a pendência que você pediu no meio da Etapa 4 e
  mandou deixar para conversa própria.

**O que você pediu.** Minimizar e maximizar cada bloco da aba Hoje ("Manhã —
estudo", "Noite — estudo", "Depois das 22h") pelo clique na parte de cima,
canto direito, perto dos horários — os dois sentidos. E o ANKI sempre
minimizado, mostrando a mensagem de que está temporariamente desativado, com
abrir sendo ação sua.

**Como foi feito.** `<details>/<summary>` puro, **sem JavaScript** — o
cronômetro continua sendo o único JS do projeto, e o Mapa do ano da lateral já
usava o mesmo recurso. O `<summary>` é o próprio `.ds-cartao__cabeca`, então o
**cabeçalho inteiro** é o botão: o canto que você pediu está dentro dele, com
um sinal ▾ / ▴ à direita dos horários mostrando o estado. Alvo de clique maior
do que só o canto, e o canto funciona.

**Duas decisões de execução, que valem você saber:**
1. **"Depois das 22h" nasce fechado**, e não só a faixa do Anki. A faixa
   desligada já é uma linha só, sem nada para abrir; o que faz sentido
   recolher é o bloco. Fechado, o cabeçalho dele carrega a frase "ANKI
   temporariamente desativado"; aberto, essa frase sai e fica a da faixa
   minimizada da 6A — a mesma frase duas vezes no mesmo bloco seria ruído. A
   frase segue a **faixa desligada**, e não o nome do bloco: religando o Anki
   ela desaparece sozinha;
2. **a dobra não é lembrada entre recarregamentos.** Guardar o estado precisa
   de `localStorage`, que é JavaScript, e não foi pedido. Cada abertura da tela
   começa no padrão. Consequência prática: depois de anotar uma faixa do Bônus,
   a volta recolhe o bloco das 22h de novo (os navegadores atuais abrem o
   `<details>` quando a âncora cai dentro dele, mas o padrão volta na próxima
   abertura).

**Arquivos alterados.**
- `src/radar/web/templates/hoje.html` — o `<details class="bloco-dobra">` em
  volta do cabeçalho e da `<ol class="linha-tempo">`, o `<summary>`, o sinal da
  dobra, a frase do ANKI no cabeçalho, e o CSS dos cinco seletores novos;
- novo: `tests/test_blocos_dobraveis.py`;
- docs: `decisoes.md` (27 a 29), `historico.md`, `pendencias.md` (**a B.11
  saiu**), `CLAUDE.md`, este arquivo.

**Testes novos (11).** Cada bloco é um `<details>` com o cabeçalho de
`<summary>`; os horários e o sinal ficam **dentro** da área que recolhe (era o
ponto do pedido); o sinal vira quando abre, só com CSS; a `<ol>` das faixas
fica dentro do `<details>` (fora dele, fechar não esconderia nada); Manhã e
Noite nascem abertos e o das 22h fechado; fechado o bloco das 22h mostra que o
ANKI está desativado, e aberto a frase do cabeçalho sai e a da faixa fica;
**com o Anki religado o cabeçalho não fala de desativado** (o teste religa num
arquivo copiado, porque a chave `anki` é aplicada na leitura do arquivo, não ao
montar o dia — o config real não é tocado); nenhum `onclick`/`onchange`; e **o
único `<script>` da tela continua sendo o cronômetro**.

**Resultado dos testes.**

| Rodada | Resultado |
|---|---|
| `test_blocos_dobraveis.py`, 1ª rodada | 10 passed, 1 failed — o meu teste do Anki religado remontava o `Plano` em memória, e a chave `anki` é aplicada na **leitura** do arquivo (`_sem_anki`): a faixa já vinha desligada. Passou a religar num arquivo copiado, como a 6A fez |
| `test_blocos_dobraveis.py` | 11 passed |
| As telas que leem a aba Hoje (`test_tela_hoje`, `test_rotina_sem_anki`, `test_cronometro`, `test_plano_b`, `test_faixas_do_dia`) | 125 passed |
| Suíte inteira, PC | **2124 passed** (2113 de antes + 11 novos), 19 min |

**Comando real rodado.** `radar web` nos dias 02/10, 03/10 e 05/10: nos três,
Manhã e Noite abertos e "Depois das 22h" fechado, com a frase do ANKI no
cabeçalho e **um único `<script>`** na página. Num dia com o **Plano B ativo**
(numa cópia do banco, apagada depois): o bloco `plano_b` também dobra e nasce
aberto. O banco real não foi alterado.

**Critério de conclusão.**
- [x] os três blocos minimizam e maximizam pelo cabeçalho, nos dois sentidos;
- [x] o bloco do ANKI nasce minimizado e, minimizado, mostra a mensagem de
  desativado;
- [x] nenhum JavaScript novo — o cronômetro segue sendo o único;
- [x] a pendência B.11 saiu do `pendencias.md`.

### B.11, segunda passada: so o canto dobra, e a dobra e lembrada (02/10)

Você pediu as duas coisas que eu havia deixado em aberto no fim da primeira
passada. As duas foram aplicadas.

**1. Só o sinal do canto dobra.** Um clique no título ou nos horários não
recolhe mais o bloco. Como: `pointer-events: none` no `<summary>`, para o
clique atravessar, e `auto` só no sinal. O **teclado não passa por `pointer-
events`**, então Tab até o cabeçalho e Enter continuam dobrando, com o foco
visível. O sinal ganhou área de clique de verdade (1,75rem, com borda no hover)
e um `title` dizendo o que faz — o alvo ficou pequeno, e um glifo de dez pixels
não é botão.

**2. A dobra é lembrada — e isto cria o segundo JavaScript do radar.** Eu avisei
antes de mexer: guardar o estado precisa de `localStorage`, e o `CLAUDE.md`
registrava que o cronômetro era o único JS. Você pediu mesmo assim, então a
regra mudou e está registrada (decisão 30): **duas exceções, as duas só na tela
Hoje, as duas dispensáveis.**

O limite é o mesmo do cronômetro, e é ele que faz a exceção aceitável: o padrão
(`<details open>`) é escrito pelo **servidor**, a dobra responde ao clique com
ou sem JavaScript, e o `dobra.js` só restaura e salva. Todo acesso ao
`localStorage` está em `try/catch` — janela privada ou dado do site limpo não
quebram a tela. A chave é o **bloco** (`data-bloco`), não o dia: "prefiro o das
22h fechado" é preferência, não coisa de 02/10. E o bloco da **âncora** (onde a
tela volta depois de anotar uma faixa) nunca é recolhido, senão o sistema
esconderia a resposta do seu próprio clique.

**Arquivos alterados.**
- novo: `src/radar/web/static/dobra.js`;
- `src/radar/web/templates/hoje.html` — `data-bloco` e `title` no cabeçalho, o
  CSS do `pointer-events` e da área do sinal, o segundo `<script>`;
- `tests/test_blocos_dobraveis.py` — reescrito (19 testes);
- `tests/test_tela_hoje.py` — `test_o_unico_javascript_e_o_do_cronometro` virou
  `test_o_javascript_da_tela_sao_dois_arquivos_e_nada_inline`;
- docs: `decisoes.md` (a 27 reescrita, a **29 revogada** e a **30** nova; a
  seção do cronômetro da etapa A5 ganhou a nota de revisão), `historico.md`,
  `README.md` (a seção "Dobrar os blocos do dia"), `CLAUDE.md`, este arquivo.

**Testes (19, oito deles novos nesta passada).** Só o sinal recebe o clique; o
cabeçalho continua focável pelo teclado; o sinal tem área de clique de verdade;
o `title` explica o canto; a tela tem **os dois scripts e só eles**, nenhum
inline e nenhum `onclick`; a dobra funciona sem o JavaScript (o padrão está no
HTML); cada bloco leva a chave que o script guarda; o `dobra.js` é servido e
protege **todo** acesso ao armazenamento; ele não recolhe o bloco da âncora; e
sai de fininho onde não há bloco nenhum.

**Resultado dos testes.**

| Rodada | Resultado |
|---|---|
| `test_blocos_dobraveis.py` reescrito | 19 passed |
| As telas que leem a aba Hoje + `test_design` | 121 passed, 1 failed — `test_tela_hoje::test_o_unico_javascript_e_o_do_cronometro`, que afirmava um `<script>` só. Era a afirmação que esta mudança revoga: o teste foi reescrito para exigir os dois arquivos e nada inline |
| `test_tela_hoje.py` + `test_blocos_dobraveis.py` | 58 passed |
| Suíte inteira, PC | **2132 passed** (2124 de antes + 8 novos), 20 min |

---

## 5 — Geração de questões com escopo fechado (02/10/2026)

- Situação: ✅ concluída
- Datas: início 02/10 · fim 02/10

**Plano conferido contra o código antes de começar: válido na estrutura, com um
problema no critério de conclusão que você decidiu antes de eu escrever código.**

**O problema, e a sua decisão.** Os dois exemplos da §23 que o critério manda
rodar **não existem na árvore real**:

```
no critério                             em data/conteudos.json
──────────────────────────────────────────────────────────────
Direito Penal > Aplicação da Lei Penal      NÃO EXISTE
  > Lei penal no tempo                      NÃO EXISTE
LEP > Progressão de regime > Art. 112       NÃO EXISTE
```

Não é defeito novo: a Etapa 2 já tinha achado que "Aplicação da lei penal" é
**título de faixa do cronograma**, e não item do programa de 2019 — foi por isso
que as 20 geradas de Penal ficaram com assunto pendente. A árvore tem só os nós
do edital mais os que as 170 do alvo tocaram.

Você escolheu: **rodar os equivalentes reais e mostrar a recusa dos literais**,
em vez de criar nós que o edital não lista (que violaria a regra inviolável 9).

**Três ajustes de execução, avisados antes:**
1. **precisou de migração v4.** O roteiro diz que os campos novos da gerada vêm
   "na migração da Etapa 2", mas a Etapa 2 só acrescentou `conteudo`;
2. **colisão de nome:** `QuestaoGerada.modo` já quer dizer "variacao | do_zero"
   (como a questão foi escrita). O modo do pedido é outro eixo, então virou
   `modo_do_pedido`; o **dispositivo** reusa a coluna `artigo`, que já era isso;
3. **`geradas.preparar` filtrava por `questoes.materia`** (o texto do caderno) e
   só olhava o alvo. Com escopo, passou a escolher pela **classificação**, e a
   buscar alvo **e** complementar, cada um marcado (§9).

**Mudou no meio, e é a decisão 33:** o **simulado continua amplo mesmo com a
matéria escolhida**. Só matéria não é escopo específico; restringir o simulado às
questões já classificadas o deixaria menor do que ele é, e a §7 manda preservar a
consulta ampla.

**Arquivos alterados.**
- `src/radar/conteudos.py` — `Escopo`, `EscopoInvalido`, `resolver_escopo` e as
  sugestões por `difflib` (tudo puro, sem banco);
- `src/radar/models.py` — `MODOS_DE_PEDIDO`, `BASES_DA_GERADA`,
  `EVIDENCIAS_DA_BASE`, e as 4 colunas novas em `QuestaoGerada`;
- `src/radar/migracoes.py` — o passo 4 (versão 4), com cópia antes;
- `src/radar/servico/geradas.py` — `reais_do_escopo` (pela classificação, alvo
  antes do complementar), `nos_estudados`, `escopo_da_revisao`,
  `modo_do_pedido`, `_preparar_no_escopo`, e o `preparar` com `escopo=` e
  `modo=`;
- `src/radar/servico/manual.py` — `INSTRUCAO_DO_ESCOPO`,
  `_instrucao_com_escopo` (o dispositivo e o link oficial do `config/leis.yml`),
  o escopo viajando no pedido, e as quatro recusas em `_fora_do_escopo` /
  `_mesmo_dispositivo`;
- `src/radar/gerador.py` — os campos novos em `QuestaoNova`;
- `src/radar/cli.py` — `--assunto`, `--subassunto`, `--elemento` (repetível) e
  `--modo` no `radar gerar`; `_escopo_do_pedido` e `_mostrar_o_escopo`;
- `src/radar/web/app.py` e `geradas.html` — o mesmo filtro na tela, com os
  seletores em cascata (um nível por vez, sem JavaScript), o modo e o escopo
  escritos, e o recado de nome inexistente;
- dados: `data/questoes_geradas.json` (ver o achado abaixo);
- novo: `tests/test_geracao_por_conteudo.py`;
- docs: `decisoes.md` (31 a 40), `historico.md`, `README.md` (a seção do filtro
  e dos três modos), `CLAUDE.md`, este arquivo.

**Achado que não era da etapa, e consertado.** O `data/questoes_geradas.json`
versionado estava **`[]`** desde o commit da Etapa 2 (`904f1b7`), enquanto o
banco tinha as 50. O export daquela etapa rodou contra um banco temporário e
sobrescreveu o arquivo — o mesmo tropeço que eu repeti aqui e peguei na hora.
**Por que importa:** o arquivo é o registro, e o banco se reconstrói a partir
dele; com o arquivo vazio, refazer o banco perderia as 50, e o §23 é explícito
("nenhum dado antigo pode ter sido perdido"). Nada se perdeu de fato — o banco
as tinha. Exportado do banco real: **as 50 voltaram** (30 `do_zero`, 20
`variacao`), e um teste novo não deixa isso acontecer calado de novo.

**Testes novos (42).**
- o filtro: desce os quatro níveis; sem nada não há escopo e a consulta ampla
  continua; assunto errado **sugere o parecido**; matéria errada lista as que
  existem; nome sem semelhança lista em vez de sugerir; subassunto sem assunto e
  assunto sem matéria não fecham escopo; `--elemento` repetível restringe, e o
  irmão não pedido fica fora; sem elemento cobre tudo abaixo; nó de nome
  parecido de outro ramo não entra (o `startswith` ingênuo erraria);
- as reais do escopo: saem da classificação; **alvo antes do complementar**;
  prova complementar não aceita fica fora; anulada não serve de base;
- os modos: com assunto é treino, só com matéria é simulado, modo inexistente é
  recusado; revisão só pega nó estudado e **para** sem nada estudado; o
  **simulado continua amplo** mesmo com a matéria escolhida (e com `--modo
  simulado` explícito);
- a base: a real vem primeiro e o resto sai da fonte oficial **dentro do mesmo
  nó**; sem real nenhuma a base é a fonte ou o edital;
- o pedido: manda não sair do escopo e declarar o nó; escreve os dispositivos; o
  pedido amplo não ganha escopo;
- **a importação (o teste que a §8 pede):** uma resposta com itens dentro e fora,
  e **só os de dentro são gravados** — as duas recusas dizem o conteúdo e o
  escopo; questão que não declara o conteúdo é recusada; com dispositivo pedido o
  artigo tem de bater, e bate escrito de outra forma ("art. 112 da Lei
  7.210/1984"); a base e a evidência ficam gravadas; `do_zero` fica marcado "sem
  questão real de referência"; vínculo com real fora do pedido é recusado;
  variação sem a real de base é recusada; o pedido amplo não exige o nó;
- o que já existia: as geradas antigas continuam listadas com os campos nulos; o
  JSON leva os campos novos; **o JSON real não está vazio**;
- a tela: oferece o assunto da matéria escolhida, escreve o escopo e o modo, e
  recusa nome que não existe sem gerar.

**Resultado dos testes.**

| Rodada | Resultado |
|---|---|
| `test_geracao_por_conteudo.py`, 1ª rodada | 6 erros meus no teste (o `Concurso` de teste sem os campos que o `_provas_do_alvo` exige, o concurso inserido duas vezes, o caderno complementar pendurado no concurso-alvo, e a assinatura do `manual.importar`) → corrigidos |
| `test_geracao_por_conteudo.py` | 42 passed |
| `test_gerador` + `test_ia_manual` + `test_migracoes` + `test_conteudos` | 90 passed |
| Suíte inteira, PC (uma vez, no fim) | **2174 passed** (2132 de antes + 42 novos), 23 min |

**Comando real rodado (banco real; a importação, numa cópia).**

1. **os dois nomes literais da §23 — recusados, como devem ser:**
   - `--materia "Direito Penal" --assunto "Aplicação da Lei Penal"` → "O assunto
     'Aplicação da Lei Penal' não existe em 'Direito Penal'. Você quis dizer:
     Imputabilidade penal?" + "Nada foi gerado: eu não alargo o escopo sozinho";
   - `--materia "LEP"` → "A matéria 'LEP' não existe. Os que existem: …" (com as
     13 matérias);
2. **o equivalente real de "Direito Penal · lei penal no tempo", 20 questões:**
   `--assunto "Tipicidade, ilicitude, culpabilidade, punibilidade" --subassunto
   "Abolitio criminis" --elemento "CP, art. 2º"` → 7 pedidos, modo **treino**,
   escopo fechado, "Só estes dispositivos: CP, art. 2º", 3 de questão real
   (complementar) + 17 da fonte oficial sem questão real de referência;
3. **o equivalente real de "LEP · Progressão de regime · Art. 112", 20
   questões:** `--subassunto "Regimes de cumprimento da pena" --elemento "LEP,
   art. 119"` → 7 pedidos, modo **treino**, 3 de questão real (**alvo**) + 17 da
   fonte oficial;
4. **a conferência de que nada saiu do escopo:** no `data/pedido_ia.json`, **um
   único escopo** nos 7 pedidos, um único modo (`treino`), um único dispositivo,
   20 questões no total, e **toda** instrução com "ESCOPO FECHADO" e o
   `CONTEUDO:` certo;
5. **o modo revisão:** `--modo revisao --materia "Língua Portuguesa"` → escopo
   da matéria restrito aos 9 conteúdos que eu estudei; `--materia "Direito
   Penal"` → "Eu ainda não estudei nenhum conteúdo de 'Direito Penal', então não
   há o que revisar";
6. **a importação com item fora do escopo** (numa cópia do banco, apagada
   depois): 1 gravada e **2 recusadas**, cada recusa dizendo o conteúdo
   declarado e o escopo. A gravada ficou com `modo_do_pedido: treino`, o escopo,
   o conteúdo, `base: questao_real`, `evidencia_da_base: alvo` e o artigo. As
   **50 antigas seguem com escopo nulo**. O banco real não foi alterado.

**Critério de conclusão.**
- [x] os dois exemplos da §23 **rodados de verdade no PC** — os literais, para
  mostrar que o filtro os **recusa e sugere**, e os equivalentes reais, com 20
  questões cada;
- [x] a conferência de que **nenhuma questão saiu do escopo**: no pedido (um só
  escopo nos 7 pedidos de cada exemplo) e na importação (2 de 3 recusadas, com o
  motivo);
- [x] por que os nomes literais não rodam está registrado aqui e na decisão 31
  — eles não existem na árvore, e criá-los violaria a regra inviolável 9.

---

## 6B — Cronograma operacional: fichas e prioridade (02/10/2026)

- Situação: 🟡 feita; falta a sua conferência das 61 fichas e o Ciclo 2
  (passo 5), que depende do simulado de 07/11
- Datas: início 02/10 · fim 02/10

**Como foi feita.** Em três sessões, no mesmo dia:
1. o código — a `FichaDeEstudo`, a prioridade, o pedido e a importação, as
   telas e o terminal —, com 56 testes novos;
2. o texto das 61 fichas, escrito pelo Claude Code em partes de duas por
   arquivo e conferido uma a uma pelo `conferir_escrita` antes de juntar;
3. a importação, os consertos achados no caminho e os docs.

**O que mudou em relação ao roteiro, e por quê** (decisões 41 a 52):
- o tema é a chave (o título da faixa sem o prefixo), e não uma chave
  `conteudo` gravada em cada faixa: o `cronograma.yml` não muda por causa da
  ficha (decisão 42);
- a fila de revisão **sugere** e não troca o tema das faixas R+7/R+30: o
  check e o registro do dia gravam o tema do calendário (decisão 45);
- os artigos-chave da ficha saem do `essencial`, e não o contrário: o Plano B
  não passa a depender de texto de IA ainda não conferido (decisão 46);
- o Ciclo 2 fica para depois do simulado de 07/11, que é o que o decide
  (decisão 52).

**Arquivos alterados.**
- novos: `src/radar/fichas.py`, `src/radar/prioridade.py`,
  `src/radar/servico/fichas.py`, `config/prioridade.yml`,
  `src/radar/web/templates/ficha.html` e `fichas.html`,
  `tests/test_fichas.py`, `tests/test_prioridade.py`,
  `tests/fixtures/cronograma_fichas.yml`;
- `src/radar/cli.py` — `radar fichas` e o 📋 no `radar hoje`;
- `src/radar/web/app.py`, `_topo.html` e `hoje.html` — a sub-aba Fichas, a
  página da ficha e o botão nas faixas;
- `src/radar/incidencia.py` e `servico/incidencia.py` — a linha de um escopo
  de vários nós e o complementar do escopo;
- `servico/desempenho_por_conteudo.py` — o desempenho de um escopo de vários
  nós, cada resposta uma vez; `servico/estudo.py` — o "refazer" do escopo;
- `src/radar/onde_estudar.py` — o fator de tempo com os números vindos de fora;
- `servico/manual.py` — o pedido e a importação de fichas, e a data da
  procedência no fuso de Florianópolis (decisão 51);
- `config/cronograma.yml` — o detalhe da teoria e o Plano B de 09/10, 28/10 e
  30/10 pelo texto vigente da LEP (decisão 48);
- testes que já existiam: `test_sincronizar.py` (o `data/fichas.json` no
  sincronizar), `test_registro_estudo.py` (o teste que sobrescrevia o `data/`
  real, decisão 50) e `test_ia_manual.py` (a data da procedência);
- dados: `data/fichas.json` (novo) e `data/questoes_geradas.json` (as 50 de
  volta);
- docs: `decisoes.md` (41 a 52), `historico.md`, `pendencias.md`,
  `README.md`, `CLAUDE.md`, este arquivo.

**Antes × depois dos dados** (o banco não mudou).

| Arquivo | Antes | Depois |
|---|---|---|
| `data/fichas.json` | não existia | 61 fichas: Português 26, LEP 12, Penal 6, Constitucional 6, Direitos Humanos 6, Raciocínio Lógico 5 — todas por conferir |
| `data/questoes_geradas.json` | `[]` no git desde a Etapa 2 | 50 (30 `do_zero`, 20 `variacao`), exportadas do banco real |

**Testes.**

| Rodada | Resultado |
|---|---|
| Suíte inteira antes da importação (02/10, 21h) | 2243 passed, 3 failed: os 2 da 6B que pedem o `data/fichas.json` e o do JSON das geradas vazio |
| `test_fichas`, `test_prioridade`, `test_geracao_por_conteudo`, `test_registro_estudo` e `test_sincronizar`, depois da importação e do conserto | 144 passed |
| `test_ia_manual` e `test_central_de_macetes` (a data da procedência) | 31 passed |
| `test_prioridade` e `test_fichas`, depois do texto da ficha sem nó (decisão 43) | 73 passed |
| Suíte inteira, final (PC, 02/10) | **2248 passed**, 0 failed, 21 min 44 s — e depois dela o `data/questoes_geradas.json` continua com as 50, o caderno e os extras intactos e nenhuma cópia nova em `data/copias/` |

**Comando real rodado (banco real).**
1. `radar fichas --importar data/resposta_ia.json` → "61 ficha(s) gravado(s)",
   procedência "Claude Code, importado manualmente, em 02/10/2026";
2. `radar fichas --tema "Art. 5º, caput e incisos I a XVI" --data 2026-10-06`
   → a ficha do cenário da §23 (abaixo);
3. `radar hoje --data` 2026-10-09, 2026-10-28 e 2026-10-30 → a lei seca e o
   Plano B com o texto novo da LEP;
4. as telas `/fichas`, `/fichas/<id>` e `/hoje` → 200, com o selo 🟣, o "por
   que agora" e as questões reais.

**Critério de conclusão** — o cenário da §23 com dados reais: "Direito
Constitucional → Direitos Fundamentais → Art. 5º → incisos I a XVI". A ficha
de 06/10 (R+7) diz:
- [x] o que ler, onde e como procurar: "CF, art. 5º: o caput e os incisos I a
  XVI, no texto oficial (Planalto)", a fonte 🟢 (a Constituição, com o link),
  os 6 artigos-chave do dia e 3 buscas;
- [x] o que entender (8 itens) e o que memorizar (5);
- [x] as pegadinhas e como a FEPESE cobrou: 3 do acervo (2013-q31 do alvo,
  conferida; 2024-q24 e 2024-q26 do complementar) e 4 escritas; "Polícia Penal
  SC: 1 questão · 1 prova" e "Acervo complementar FEPESE: 2 questões · 2
  provas" em linhas separadas, e a frase "Não há evidência suficiente no
  acervo para afirmar isso." no padrão do alvo, abaixo da amostra;
- [x] as questões reais: 2013-q31 (alvo), 2024-q24 e 2024-q26 (complementar);
- [x] quantas fazer e quais geradas: as faixas do plano (aprendizagem de 15,
  com consulta; R+7 e R+30 de 10, sem consulta), "comece pelas 3 reais" e um
  `radar gerar` por nó (nenhuma gerada no escopo ainda);
- [x] os erros a revisar: 0 no radar e 0 no caderno neste escopo, nunca
  somados;
- [x] por que hoje: "O cronograma de 06/10 traz este tema: R+7 (a volta do
  estudo de 29/09)" e cada fator da prioridade, com o número e a origem
  (0,41; 49º de 61 temas).

Fica em aberto:
- [ ] a sua conferência das 61 fichas (na conferência, olhar os nós: 13 ficaram
  sem nó, decisão 43);
- [ ] o Ciclo 2 (passo 5 do roteiro): a proposta depois do simulado de 07/11 e a
  sua aprovação antes de 09/11.

## 7A — Selos, frase padrão e marcação de IA (02-03/10/2026)

- Situação: ✅
- Datas: início 02/10 · fim 03/10

**Como foi feita.** Os cinco passos do roteiro, cada um com os testes dele e
um commit, e as telas uma por commit (17 commits, de `19a1e34` a `ec19488`,
mais o dos docs).

**O que mudou em relação ao roteiro, e por quê** (os cinco ajustes aprovados
antes de começar; decisões 53 a 58):
- o antigo 🟩 "calculado" foi **dividido** pela natureza do dado, e não só
  trocado de cor: contagem nas provas virou 🔵 acervo; o que o sistema calcula
  de mim e do radar virou 🟡 automático (decisão 53);
- a frase da regra 4 já existia em dois arquivos (e uma terceira cópia na
  ficha): virou **uma constante só**, no `origem.py`; "não sei ainda" ficou
  para fato que não se sabe (decisão 56);
- a ficha da 6B, que já tinha os quatro selos com um dicionário próprio,
  passou a usar o **mesmo componente** de selo, na forma curta;
- não só as metas reusavam a cor dos selos: a faixa do cronograma, o "agora",
  o círculo de feito, o cronômetro e o bom/ruim de várias telas também. Todos
  ganharam cor pelo nome, e um teste proíbe `--selo-*` fora do `design.css`
  (decisão 55);
- a origem foi gravada **nos dados que a tela mostra com selo** (17 telas), e
  não em todo número de todo serviço (decisão 54).

**Arquivos alterados.**
- novo: `src/radar/origem.py` (as origens, o `SELOS`, a frase da regra 4 e a
  da questão de IA);
- `src/radar/web/static/design.css` — cores com nome, `--selo-*` nas cores do
  novo.md, `--meta-*`, as classes `ds-selo--acervo`, `--plano` e `--curto`;
- `src/radar/web/templates/_componentes.html` — o `selo` lê o `SELOS`, com a
  forma curta;
- os serviços que entregam dado com selo: `servico/metricas.py`,
  `cronograma.py`, `foco.py`, `servico/inicio.py`, `servico/erros.py`,
  `servico/desempenho_por_conteudo.py`, `macetes.py`, `servico/cartoes.py`,
  `servico/previsao.py`, `servico/materias.py`, `servico/simulado.py`,
  `servico/compilado.py`, `leis.py`, `models.py` (a origem da questão e do
  salário, sem coluna nova), `servico/geradas.py`, `servico/manual.py`,
  `fichas.py` e `prioridade.py`;
- a frase padrão: `incidencia.py`, `complementar.py`, `onde_estudar.py`;
- `src/radar/web/app.py` e `src/radar/cli.py` — o `SELOS` e as frases como
  globais do Jinja, e o terminal lendo o mesmo `SELOS`;
- 17 templates: `foco`, `home`, `hoje`, `semanas`, `erros`, `macetes`,
  `macete_questoes`, `questao`, `relatorio`, `simulado`, `geradas`, `index`,
  `materias`, `previsao`, `mais`, `ficha` e `desempenho`;
- testes novos: `tests/test_origem.py` e `tests/test_varredura_das_telas.py`;
  ajustados ou ampliados: `test_design`, `test_fichas`, `test_foco`,
  `test_central_de_macetes`, `test_macetes`, `test_home`, `test_metricas`,
  `test_semanas`, `test_caderno_erros`, `test_gerador`, `test_relatorio`,
  `test_web`, `test_previsao`, `test_materias_na_tela` e `test_minimo`;
- docs: `especificacao.md` (a tabela dos selos), `decisoes.md` (53 a 58),
  `historico.md`, `pendencias.md`, `README.md`, `CLAUDE.md`, este arquivo.

Nenhum dado mudou, e o banco não mudou de versão: a origem da questão real e
da gerada é da tabela, e não uma coluna.

**Testes.**

| Rodada | Resultado |
|---|---|
| Passo 1 (selos, tokens e cores das telas), 21 arquivos, 1ª rodada | 27 passed, 1 failed (o próprio teste novo: o ajudante procurava "marca {", e a marca é o título da seção) |
| Passo 1, depois do conserto do teste | 686 passed |
| Passo 2 (a origem nos serviços): `test_origem.py`, depois 22 arquivos | 35 passed; 607 passed |
| Passo 3 (a frase padrão), 6 arquivos | 170 passed |
| Meu foco · home · Semanas · Caderno de erros | 70 · 9 · 37 · 53 passed |
| Hoje (`test_metricas`, `test_tela_hoje`, `test_acertos_do_dia`) | 85 passed, 1 failed (o teste novo: a linha "medido no radar" só aparece com resposta real no dia; o teste ganhou uma) → 3 passed |
| Macetes (`test_macetes`, `test_central_de_macetes`) | 67 passed, 2 failed (a questão do macete lia a origem do modelo, e não da `QuestaoRelacionada`, que passou a delegar; o teste das repetidas usava impressões diferentes) → 105 passed, com o `test_origem` |
| Rodada (questão e relatório), Simulado, Gerar questões | 99 · 146 · 181 passed |
| Concursos, Minhas matérias, Previsão e Mais | 200 passed; o teste novo da Mais, 1 failed (a legenda do topo já tem todos os selos: o teste passou a olhar só a cabeça do cartão) → 29 passed |
| Ficha (`test_fichas`, `test_prioridade`) | 74 passed |
| Varredura das telas, 1ª rodada | 2 passed, 1 failed: "15 \| 15%" e "60% \| 21", a base na célula ao lado; e a base de teste dependia da data de hoje → reescrita com data fixa e o vizinho aceito: 3 passed |
| Suíte inteira, PC (uma vez, no fim) | **2316 passed** (2248 de antes + 68 novos), 0 failed, 23 min — e depois dela o `data/` intacto (`git status` sem nada em `data/`) |

**Comando real rodado (banco real).**
1. `radar web --porta 8765` e as telas Hoje, Semanas, home, Meu foco, Minhas
   matérias, Simulado, relatório de uma rodada, Gerar questões, Macetes,
   Mais, uma ficha e Previsão, capturadas pelo Edge sem janela com
   `?tema=claro` e `?tema=escuro` (24 capturas);
2. `radar fichas --tema "Aplicação da lei penal (arts. 1º a 12)" --data
   2026-10-05` → cada linha com o selo do `origem.py` (📌 🟢 🔵 🟡 🟣).

**Critério de conclusão.**
- [x] `pytest -q` verde (acima);
- [x] as telas conferidas no navegador, nos dois temas: os selos com as cores
  do novo.md (🟢 verde, 🔵 azul, 🟡 amarelo, 🟣 roxo), as metas do dia com as
  cores de antes (a Reduzida azul e a Mínima amarela no "Se o dia apertar" e
  nas pílulas da semana), o bom e o ruim em verde e vermelho;
- [x] `especificacao.md` (a tabela dos selos) e `decisoes.md` (53 a 58) dizem
  as cores novas.

Achado e anotado em pendências (A): o `?tema=` da URL colide com o filtro
"Matéria ou tema" dos Macetes - fora da 7A.

## 7B — As 6 telas no design system (03/10/2026)

- Situação: ✅
- Datas: início 03/10 · fim 03/10

**Como foi feita.** Uma tela por commit, da menor para a maior (`d135971` a
`405d4af`): 404, Calendário, Previsão, Acompanhando, Análises (`foco.html`) e
Concursos (`index.html`). Em cada uma: `body class="ds"`, `ds-pagina`,
`ds-cabeca`, `ds-cartao`, `ds-tabela` (dentro de `ds-rolagem`), `ds-botao`, e o
`<style>` da tela reescrito nos tokens, sem a paleta própria. O último commit
leva a barra do topo para os tokens, tira a ponte do `design.css` e ajusta o
README.

**O que mudou em relação ao roteiro, e por quê** (aprovado antes de começar;
decisões 59 e 60):
- o roxo das telas antigas (Estadual SC, "a confirmar", a fase "autorizado",
  o aviso da secretaria) virou **azul e cinza tracejado**: desde a 7A o roxo é
  a cor da IA, e o roteiro manda usar só os tokens que já existem;
- **a barra do topo e a ponte** entraram na etapa: o `_topo_estilo.html` (dentro
  de toda página) ainda lia `--cartao`, `--azul`... pela ponte do `design.css`,
  que o próprio arquivo dizia que sairia com a última tela;
- as classes que testes e links leem (`li class="nucleo"`, `atalhos`,
  `mais-filtros`, `detalhes`, `menu-faixa`) ficaram: mudou o estilo, não a
  marcação. A 404 segue sem a barra do topo, como sempre foi.

**Arquivos alterados.**
- `src/radar/web/templates/404.html`, `calendario.html`, `previsao.html`,
  `acompanhando.html`, `foco.html` e `index.html` — as seis telas;
- `src/radar/web/templates/_topo_estilo.html` — a barra do topo nos tokens;
- `src/radar/web/static/design.css` — a ponte dos nomes antigos saiu;
- teste novo: `tests/test_telas_no_design_system.py`;
- docs: `README.md` (o parágrafo das telas no design system), `decisoes.md`
  (59 e 60), `pendencias.md` (o bloco C saiu), `historico.md`, `CLAUDE.md` e
  este arquivo.

Nenhum dado mudou, e nenhum texto de tela mudou.

**Testes.**

| Rodada | Resultado |
|---|---|
| 404 (`test_404`, `test_telas_no_design_system`) | 7 passed |
| Calendário (`test_calendario`) | 29 passed |
| Previsão (`test_previsao`) | 32 passed |
| Acompanhando (`test_acompanhando`, `test_favoritos`) | 105 passed |
| Análises (`test_foco`, `test_minimo`, `test_onde_estudar`, `test_treino_do_alvo`, `test_design`) | 172 passed |
| Concursos (`test_web`, `test_filtros`, `test_favoritos`, `test_elegibilidade`, `test_detalhes`, `test_abertas`, `test_retificacao`, `test_perfil`) | 280 passed |
| Barra do topo e ponte (`test_telas_no_design_system`, `test_design`, `test_web`) | 106 passed |
| Suíte inteira, PC (uma vez, no fim) | **2324 passed** (2316 de antes + 8 novos), 0 failed, 23 min; o `data/` intacto |

**Comando real rodado (banco real).** `radar web --porta 8765`, e cada tela
capturada pelo Edge sem janela com `?tema=claro` e `?tema=escuro`: 404,
Calendário, Previsão, Acompanhando, Análises, Concursos (a lista inteira, o
filtro Estadual SC e a aba de notícias) e a barra do topo na tela Mais. A
captura da aba de notícias mostrou os botões "Limpar" e "Voltar" esticados ao
lado do campo de busca; o alinhamento foi acertado antes do commit.

**Critério de conclusão.**
- [x] as seis conferidas no navegador, nos dois temas (acima);
- [x] o bloco C saiu do `pendencias.md`.

## 8 — Auditoria final integrada (03/10/2026)

- Situação: 🟡 feita; 18 dos 19 itens da §23 atendem com o dado real, e o
  que não atende por inteiro é pendência (abaixo). Eram 17: o item 13 estava
  ⚠️ por um erro meu, corrigido em 03/10 (veja "Correções depois da
  auditoria", item 4)
- Datas: início 03/10 · fim 03/10

**Como foi feita.** Antes de começar, a checagem do plano achou dois pontos,
decididos por você (decisões 61 e 62): os dois exemplos de geração da §23 não
existem na árvore real - o aceite prova o escopo numa árvore de fixture, e a
falta dos nós vira pendência -, e o backup das 23h30, quebrado desde 27/09,
vira etapa própria. Depois:
1. `tests/test_aceite.py`, com banco de fixture: as 12 perguntas da ficha, os
   dois pedidos de geração e os 6 itens finais;
2. o uso real, item por item, com o banco e a config de verdade - e o que
   mexeria em dado, numa cópia (`RADAR_DATA_DIR`, `RADAR_CONFIG_DIR`);
3. o resultado de cada item em `docs/auditoria_final.md`.

**Arquivos alterados.**
- novos: `tests/test_aceite.py` e `docs/auditoria_final.md`;
- docs: `decisoes.md` (61 e 62), `pendencias.md` (o backup em A; os nós da
  §23, a média "por prova" dos Macetes e o Actions de 03/10 em D; o item de
  "uso real" de D1 e E1 a E4 saiu, conferido), `historico.md`, o "Estado
  atual" do `CLAUDE.md` reescrito, e este arquivo.

Nenhum código de produção mudou, e nenhum dado real foi alterado.

**Os itens da §23** (o detalhe e a evidência de cada um estão no
`docs/auditoria_final.md`):

| Item | Situação |
|---|---|
| 1 a 12 — a ficha do Art. 5º responde o que ler, onde, como procurar, entender, memorizar, pegadinhas, como a FEPESE cobrou, questões reais, quantas fazer, geradas, erros e por que hoje | ✅ teste e ficha real |
| 13 — selecionar matéria → assunto → subassunto → elemento e gerar sem sair do escopo | ✅ o mecanismo atende (teste e nós reais mais próximos), e os dois exemplos rodam pelos equivalentes reais, como decidido na Etapa 5 (decisão 66) - estava ⚠️ por engano |
| 14 — números iguais em todas as telas | ✅ 28/09, 29/09 e a semana 1 iguais na Hoje, no `radar hoje`, na Semanas e em Minhas matérias |
| 15 — a incidência do alvo não muda por prova complementar | ✅ 426 linhas iguais com 0 e com 122 provas complementares (numa cópia) |
| 16 — nenhum dado antigo perdido | ✅ cada tabela igual à cópia de antes da Etapa 2 |
| 17 — ANKI desativado, mas reativável | ✅ `radar hoje` com a config real e com uma cópia religada |
| 18 — nenhuma estatística sem amostra | ⚠️ 114 porcentagens em 31 aberturas de tela; a média "por prova" do gráfico dos Macetes não diz em quantas provas → pendência |
| 19 — nenhuma questão gerada como oficial | ✅ as 2 rodadas de IA com 🟣 e a frase, sem "Gabarito definitivo" |

Fora da §23: o Actions estava verde até 02/10 (conferir o de 03/10); o backup
das 23h30 falhou em todas as execuções registradas (pendência A, próxima
etapa); o caderno de erros e a Semanas funcionam com o dado real.

**Testes.**

| Rodada | Resultado |
|---|---|
| `test_aceite.py`, 1ª rodada | 22 passed, 2 failed, 2 errors: a regex da linha da conta não aceitava o "IA" maiúsculo; a chave `anki: desativado` aparece também num comentário do YAML; e faltava importar a fixture do quadro do edital que a varredura usa - os três no próprio teste |
| `test_aceite.py`, depois | 26 passed |
| Suíte inteira, PC (uma vez, no fim) | **2350 passed** (2324 de antes + 26 do aceite), 0 failed, 24 min; o `data/` e a `config/` intactos |

**Comandos reais rodados (banco real).** `radar fichas --tema "Art. 5º, caput
e incisos I a XVI" --data 2026-10-06`; os dois `radar gerar` da §23 (recusados,
sem gastar); `radar hoje --data` de 28/09 a 02/10 e 05/10 (com a config real e
com a cópia religada); e as telas pelo `TestClient`, com o banco real.

**Critério de conclusão.**
- [x] cada item da §23 marcado, com a evidência (teste, comando ou tela);
- [x] o que não atende está registrado como pendência, com o motivo - e por
  isso a etapa fica 🟡, e não ✅;
- [x] o "Estado atual" do `CLAUDE.md` reescrito.

## Correções depois da auditoria (03/10/2026)

- Situação: ✅ os cinco itens feitos; falta a sua conferência dos 15 itens da
  lista de leis e conferir a primeira noite do backup consertado
- Datas: início 03/10 · fim 03/10

**O pedido:** a varredura dos docs depois da Etapa 8 achou cinco pontos, e você
pediu os cinco, nesta ordem, um só depois do outro pronto: (1) o "Onde estudar
primeiro" somando alvo e complementar; (2) o backup das 23h30; (3) a lista de
leis alteradas do `config/leis.yml`; (4) o meu erro da Etapa 8 nos docs; (5) a
limpeza geral dos docs. Commit e push uma vez só, no fim do item 5.

### Item 1 — o "Onde estudar primeiro" e a regra inviolável 1 ✅

**O que estava errado.** As questões esperadas eram `peso × (do cargo +
reforço) / (base do cargo + base do reforço)`: um número só, feito do alvo e
do complementar - o que a regra inviolável 1 proíbe. E o "reforço" era
qualquer caderno da FEPESE, aceito ou não no levantamento da 3B. A Etapa 8 não
pegou isso.

**O que mudou** (decisão 63):
- `src/radar/onde_estudar.py`: as questões esperadas e os pontos são só das
  provas do cargo; o complementar entra só na ordem, com o peso do
  `config/prioridade.yml` (0,25, a mesma conta da prioridade das fichas); a
  linha guarda as duas fatias separadas; a conclusão diz "vem primeiro na
  ordem", e não mais "deve valer";
- `src/radar/foco.py`: o complementar é só o das provas aceitas no
  `data/acervo_complementar.json`, a mesma regra da incidência;
- `foco.html`: as duas fatias na linha ("13 de 38 nas provas do cargo · 54 de
  169 no acervo complementar, com peso 0,25 só na ordem") e as legendas;
- `README.md` (a seção do Onde estudar) e `docs/decisoes.md` (63, e a decisão
  antiga "o reforço soma na fatia" marcada como substituída).

**Com o banco real** (numa cópia): Interpretação de texto continua em
primeiro, com 5,1 questões esperadas só do cargo (eram 4,8 com o reforço
somado); "Conjuntos", que nunca caiu nas provas do cargo, aparecia com 1
questão esperada e agora aparece como "só no acervo complementar", fora das 12
da tela.

**Testes.**

| Rodada | Resultado |
|---|---|
| `test_onde_estudar.py`, 1ª rodada | 20 passed, 1 failed (a frase do assunto só do complementar dizia "questões classificadas", e o que ela conta são marcas de assunto; corrigida a frase) |
| `test_onde_estudar.py` + `test_foco.py` | 92 passed, 1 failed (o teste da prova não aceita procurava um trecho que também está na legenda; afinado) → os 12 do recorte passed |
| `test_minimo.py`, `test_espacada.py`, `test_prioridade.py` | 40 passed |

### Item 2 — o backup das 23h30 ✅

**O que estava errado.** Dois defeitos, um atrás do outro:
1. o `radar sincronizar` fazia `git pull --rebase`, e o rebase recusa rodar
   com qualquer arquivo versionado mudado na pasta - o código de uma etapa pela
   metade bastava. As 6 execuções de 27/09 a 02/10 pararam aí;
2. escondido atrás dele: o `git add` recebia os 15 caminhos do radar, e 3 não
   existem (`data/macetes.json`, `data/explicacoes.json`,
   `data/notas_semana.json`). Com um caminho inexistente o `git add` para sem
   adicionar nenhum, e o backup diria "nada mudou" sem ter guardado nada.

Resultado: o último sincronizar que funcionou foi o de 25/09; o banco local
está sem 32 eventos da coleta do robô, e os 4 simulados de 28 e 29/09 só
existem no `radar.db`.

**O que mudou** (decisão 64), em `src/radar/cli.py`:
- o pull virou `git fetch` + `git merge --ff-only origin/main`, que avança com
  a pasta suja desde que o que chega não caia num arquivo mudado aqui;
- commit local que não subiu + commit do robô: rebase só com a pasta limpa, e
  `rebase --abort` se der conflito (antes, um conflito deixava o rebase pela
  metade);
- o `git add` leva só os arquivos que existem, o commit leva os caminhos no
  fim (só os do radar, mesmo com outra coisa no stage), e `git add` que falha
  para o comando;
- `README.md` (Trocando com o GitHub; a tarefa do backup), `docs/decisoes.md`
  (64), `docs/pendencias.md` (o backup saiu de A; ficou a conferência da
  primeira noite) e o "Estado atual" do `CLAUDE.md`.

**Testes.** `tests/test_sincronizar.py` ganhou 7 testes, 5 deles com o **git de
verdade** em repositórios no `tmp_path` (a "origem" é uma pasta, sem internet):
pasta suja + coleta do robô; nada novo no GitHub; histórias separadas com a
pasta suja (para sem tocar em nada: mesmo HEAD, sem stash, sem rebase pela
metade, sem exportar); histórias separadas com a pasta limpa (rebase); e a
coleta que cai num arquivo mudado aqui (recusa, o arquivo continua o meu).

| Rodada | Resultado |
|---|---|
| `test_sincronizar.py` | 21 passed (14 de antes, 3 ajustados ao fetch/merge, + 7 novos) |

**Comando real.** Numa cópia do repositório (`git clone` para uma origem
falsa, local), com o banco real copiado, a pasta suja com as mudanças dos itens
1 e 2, e uma coleta do robô simulada na origem: `python -m radar.cli
sincronizar` trouxe a coleta, importou (2878 concursos, 32 eventos novos),
exportou e commitou só `data/concursos.json`, `data/eventos.json`,
`data/notas_semana.json` e `data/simulados.json`, empurrou para a origem, e
deixou os 11 arquivos em andamento como estavam. Depois, `radar backup` no
mesmo lugar: `Nada mudou` e `RESULTADO: ok` no log.

### Item 3 — a lista de leis alteradas depois das provas ✅

**O que faltava.** A lista `mudancas` do `config/leis.yml` nunca tinha sido
gravada (a decisão antiga mandava esperar a sua conferência), e por isso
nenhuma questão antiga ganhava o aviso **⚠ A lei mudou depois desta prova**.

**Como foi feita** (decisão 65):
1. as datas das provas, nos documentos oficiais do acervo: 2013 em 10/11/2013
   (edital, item 11.1.4) e 2019 em 01/12/2019 (termos aditivos 3 e 4 e o
   gabarito);
2. as 115 questões de Direito, em cinco frentes paralelas (Constituição;
   CP e CPP; LEP, leis especiais e administração; leis de SC; Direitos
   Humanos), cada dispositivo conferido no texto compilado da Câmara ou da
   ALESC, com a anotação copiada como evidência;
3. o resultado: 17 questões tocam regra que mudou (1 na CF, 3 no CPP, 2 na
   LEP e na improbidade, 10 nas leis de SC, 1 em Direitos Humanos), em 15
   itens; as `marcas` foram afinadas contra as 170 questões reais com a mesma
   função da tela: 17 pegas, nenhuma a mais, nenhuma faltando;
4. o código: `Mudanca` ganhou `procedencia` e `conferida`; item escrito por IA
   e não conferido sai com o 🟣 "Escrito por IA, por conferir", e as telas
   Macetes e Mais dizem quantos faltam (`leis.mudancas_por_conferir()`);
5. a evidência de cada item, para a sua conferência, em
   `docs/leis_alteradas.md`.

**Arquivos.** `config/leis.yml` (a lista, no fim), `src/radar/leis.py`,
`src/radar/web/app.py`, `_componentes.html`, `macetes.html`,
`macete_questoes.html`, `mais.html`; testes em `test_leis.py` (3 novos, sobre
a lista real) e `test_central_de_macetes.py` (4 novos; o `config_propria`
passou a tirar a lista real, para cada teste dizer qual lista quer); docs:
`leis_alteradas.md` (novo), `decisoes.md` (65, e a antiga marcada como
substituída), `pendencias.md`, `README.md`, `especificacao.md`, o "Estado
atual" do `CLAUDE.md`.

**Testes.**

| Rodada | Resultado |
|---|---|
| `test_central_de_macetes.py` + `test_leis.py`, com o código novo | 30 passed |
| Os 18 arquivos que leem leis, Macetes ou Mais | 650 passed |
| `test_leis.py` + `test_central_de_macetes.py`, com a lista real | 33 passed |

**Uso real (banco real, numa cópia).** A Central de Macetes mostra o aviso em
6 cartões - Legislação Estadual 9, Direito Processo Penal 2 e 1 em cada um de
Direito Constitucional, LEP, Administração Pública e Direito Processual Penal
(as 17 menos as 2 anuladas, que o cartão não conta) -, cada um com o 🟣
"Escrito por IA, por conferir"; a nota da Central e a tela Mais dizem "15
item(ns) ... por conferir".

### Item 4 — o meu erro da Etapa 8 nos docs ✅

**O erro.** Na Etapa 5 você decidiu, antes de eu escrever código, rodar os
equivalentes reais dos dois exemplos de geração da §23 e mostrar a recusa dos
literais, em vez de criar nós que o edital não lista. A escolha ficou só neste
arquivo (seção da Etapa 5), e não no `decisoes.md`. Na Etapa 8 eu não a achei:
reabri a questão como "decisão sua" (decisão 62 e uma pendência em D) e marquei
o item 13 da §23 com ⚠️ - e a auditoria ficou com 17 de 19.

**A correção.**
- `docs/decisoes.md`: a decisão 66 registra a escolha da Etapa 5, com a data
  dela (02/10); a 62 ganhou a nota de que estava errada nesse ponto;
- `docs/auditoria_final.md`: o item 13 passou a ✅; o item 15 ganhou a nota de
  que a auditoria só conferiu a incidência (o "Onde estudar" somava o
  complementar - item 1); a linha do backup diz que ele foi consertado; e uma
  seção nova, "Correções depois da auditoria";
- `docs/pendencias.md`: a pendência dos nós saiu;
- este arquivo (a linha da Etapa 8 e a seção dela) e o "Estado atual" do
  `CLAUDE.md`: **18 de 19 itens**.

Nenhum código mudou neste item.

### Item 5 — a limpeza geral dos docs ✅

**Os relatórios gerados, regerados de verdade:**
- `docs/complementar.md` (`radar complementar`): dizia "Nada entrou em
  estatística nenhuma" com 122 provas já na incidência. O texto agora depende
  de o acervo ter sido aplicado (`servico/complementar.py`, com 2 testes
  novos): antes do `--aplicar`, é o levantamento; depois, "Onde isto está";
- `docs/auditoria.md` (`radar auditar`): era de 01/10, com 0 classificações
  conferidas; agora mostra as 170 do alvo conferidas.

**Os textos velhos corrigidos:**
- `README.md`: o estado do topo (dizia "fases 1 a 6, 8 e 9", "5.928
  questões"), a lista dos documentos, as três descrições da navegação de antes
  do redesign (a tabela "aba por aba", "Como a tela é organizada" e a barra do
  design system), o mínimo da home (dizia 5; é o do `config/amostra.yml`,
  hoje 20), o cartão "De olho" (fica em Análises > Edital, não na home) e o
  tempo dos testes (dizia "menos de 1s"; são ~2.400 e uns 25 minutos);
- `docs/especificacao.md`: como a navegação ficou (sete destinos) e o mínimo
  de amostra de hoje;
- `CLAUDE.md`: o cartão "De olho", as exceções de mínimo fixo declaradas, a
  descrição do `progresso.md` (era igual à do roteiro) e o "Estado atual"
  reescrito;
- este arquivo: as cinco etapas que diziam "aguardando sua aprovação" e a
  situação da 3B (dizia que faltava o passo 4, feito em 02/10);
- `docs/pendencias.md`: o cabeçalho da B (dizia "nada disso virou código"), a
  nota da decisão 18 (a Etapa 5 não fez o filtro de evidência da Conferência)
  e a seção **F** nova, com os 10 achados da varredura que nenhuma etapa tinha
  registrado;
- `docs/decisoes.md`: como ler a numeração (até a 3B ela recomeça por seção);
- `docs/historico.md`: a contradição da dobra dos blocos (dizia que lembrar a
  dobra "ficou de fora", e a mesma seção diz que foi feito).

### Testes e comandos de todos os itens

| Rodada | Resultado |
|---|---|
| `test_complementar.py`, com o relatório novo | 52 passed |
| Suíte inteira, PC (uma vez, no fim dos cinco itens) | **2372 passed** (2350 de antes + 22 novos: 4 do Onde estudar, 2 da tela, 7 do sincronizar - 5 com git de verdade -, 4 dos Macetes, 3 da lista de leis e 2 do relatório do complementar), 0 failed, 23 min |

**Comandos reais rodados:** a tela Análises (o "Onde estudar") e as telas
Macetes e Mais com o banco real (numa cópia); `python -m radar.cli
sincronizar` e `radar backup` numa cópia do repositório, com origem local;
`radar complementar` e `radar auditar` no projeto. Commit e push uma vez só,
no fim do item 5, como você pediu.

## 16 — O ciclo 1 específico (pedido de 03/10/2026)

- Situação: 🔄 em andamento; a subetapa 2A está feita
- Datas: início 03/10

**O pedido.** Dois, ligados: (1) implementar o "item 4" das pendências; (2) o
sábado de 03/10 está genérico - o diagnóstico manda "Radar > Simulado > matéria
X > 20 questões" sem dizer de que assunto - e o ciclo 1 inteiro talvez também.
Primeiro as respostas com evidência e o plano, sem mexer em nada; depois o
"pode", com as alternativas recomendadas.

**As respostas do Passo 1** (só leitura):
1. a ficha não depende da data, e sim do tema: ela é reconhecida pelo título
   (decisão 42) em qualquer dia; a chave `conteudo` existe em só 6 faixas de
   Português; o sábado de 03/10 é o único só de medida - do 10/10 em diante o
   sábado tem estudo de Raciocínio Lógico com ficha -, e as faixas que medem
   (diagnóstico, simulado, revisão semanal, R+7 dos diagnósticos) nunca têm
   ficha. Mesmo com ficha, a faixa não mostrava o assunto: ele ficava dentro
   da ficha;
2. de 03/10 a 07/11, 121 das 182 faixas de questões não dizem o assunto e o
   subassunto exatos: 45 sem ficha nem nó (diagnósticos, simulados, revisões
   semanais, o R+7 dos diagnósticos, 25 bônus, 5 interpretações
   cronometradas), 30 com ficha sem nó (LEP e Português), 29 só no assunto e
   17 com nós mistos;
3. os dias seguintes já se veem: "← dia anterior · Hoje · próximo dia →" e
   `/hoje?data=AAAA-MM-DD`;
4. o diagnóstico foi feito por matéria, e o caminho dele sorteava de qualquer
   banca (em Português, 39 da IESES e 68 de provas recusadas na 3B entre 254);
5. a pendência F do "Onde estudar" continua aberta: a composição usa a
   incidência por nó da árvore, e não o "Onde estudar".

As decisões: 1B, 2A, 3A+C, 4A, 5B, 6B, 7A e 8A (registradas no `decisoes.md`,
antes da decisão 67).

### 2A — as faixas que medem ✅

**O que mudou** (decisões 67 e 68):
- `src/radar/servico/composicao.py` (novo): a regra de composição, a rodada
  que mede (só questão real da FEPESE do alvo e do complementar aceito, uma
  por enunciado, sem anulada, com gabarito, nunca gerada), a composição
  gravada na rodada e a rodada que não é recriada;
- a tela Hoje: a faixa que mede diz "Só questões: não há o que estudar nesta
  faixa.", mostra a composição - assunto, quantas, a amostra das provas do
  cargo, o complementar separado com o peso, os subassuntos das questões
  escolhidas e a frase padrão onde falta amostra - e o botão "Criar a rodada
  com esta composição" (`POST /hoje/rodada`); criada, mostra a composição
  gravada e o link para a rodada;
- `config/cronograma.yml`: só o `detalhe` das três faixas que medem (03/10
  manhã e noite, 07/11 noite) e a chave nova `materias_da_rodada` no 07/11;
  nenhum título mudou. `src/radar/cronograma.py` lê a chave e confere cada
  nome contra o bloco `materias`;
- o item 4 da seção F: o modo simulado da geração, sem matéria, divide pelo
  peso do edital (`servico/geradas.py`), e o `radar gerar` diz a divisão;
- docs: `decisoes.md` (as escolhas, 67 e 68), `pendencias.md` (o item 4 da F
  saiu; o que falta do pedido entrou em D), `README.md`, `historico.md` e o
  "Estado atual" do `CLAUDE.md`.

**Com o banco real** (numa cópia): o diagnóstico de Raciocínio Lógico sai com
20 de 20 pelo edital (nenhum assunto tem amostra; 7 dos 12 sem questão real
classificada); o de Português com 8 de Interpretação e 1 de cada um dos
outros 12 assuntos; o 07/11 com 50 de 50. A rodada criada pelo botão teve 20
questões, todas da FEPESE, 17 das provas do cargo e 3 do complementar aceito,
nenhuma gerada, nenhuma anulada, 20 enunciados distintos; o segundo clique
reabriu a mesma rodada. A tela de 03/10 abre em ~3 s (as outras não mudam:
~0,4 s). `radar gerar --quantas 20 --modo simulado` (simulação, nada gasto)
dividiu as 20 entre as 11 matérias pelo edital.

**Testes.**

| Rodada | Resultado |
|---|---|
| `test_composicao.py` (novo), 1ª rodada | 11 passed, 1 failed (o ajudante do teste passava `onde` duas vezes; corrigido no teste) |
| `test_composicao.py` | 18 passed |
| `test_gerador.py`, os 2 novos do modo simulado | 2 passed |
| Os 12 arquivos das áreas tocadas (cronograma, tela Hoje, Plano B, geração, compilado, varredura, design system, aceite) | 328 passed |
| Suíte inteira, PC (uma vez, no fim da 2A) | **2392 passed** (2372 de antes + 20 novos: 18 da composição e 2 do modo simulado da geração), 0 failed, 25 min |

### 2B — o sábado ✅

**O que mudou** (decisões 69 e 70):
- `src/radar/servico/composicao.py`: a composição do simulado do Qconcursos
  (`compor_por_tema`), por tema estudado antes do dia, com o filtro do tema;
  a tela lê o acervo uma vez só para ela e para a do radar;
- `src/radar/servico/sabado.py` (novo): a revisão semanal (os temas, os
  erros anotados por tema, os motivos e os artigos-chave da semana), o R+7
  dos diagnósticos (os erros das rodadas de 03/10 e a rodada deles) e a
  comparação de 07/11 (diagnóstico, fechamento e ciclo, separados);
- `src/radar/servico/metricas.py`: o acerto de várias rodadas juntas e os
  erros delas - as contas novas, no lugar das contas;
- a tela Hoje: o simulado do Qconcursos mostra a composição sem botão; a
  revisão semanal, o R+7 (com o botão "Criar a rodada com os erros", no
  mesmo `POST /hoje/rodada`) e a tabela de 07/11. Sem JavaScript novo;
- `config/cronograma.yml`: o `detalhe` dos cinco simulados de sábado sem
  número e com `materias_da_rodada`; o detalhe do R+7 de 10/10; e a chave
  nova `compara_com` na correção de 07/11, lida e conferida pelo
  `src/radar/cronograma.py`. Nenhum título mudou, e os dias antes de 03/10
  continuam com a mesma impressão;
- docs: `decisoes.md` (69 e 70), `pendencias.md` (o Actions de 03/10 saiu -
  foi verde -; entraram o R+7 de 5 erros e os temas sem nó), `README.md`,
  `historico.md` e o "Estado atual" do `CLAUDE.md`.

**Com o banco real** (numa cópia): o mini-simulado de hoje sai com 3 de
Constitucional, 2 de Penal e 5 da LEP, um filtro por tema; o de 10/10 com 9 de
Português, 9 de Direitos Humanos, 3 de Constitucional, 3 de Penal e 6 da LEP;
o de 31/10 com 12, 12, 4, 4 e 8. A revisão semanal de hoje mostra a semana de
28/09 a 02/10: 10 temas, 2 erros anotados (1 no art. 5º, 1 em artigo, numeral
e pronome) e 17 artigos-chave. Com os diagnósticos respondidos numa cópia (11
erros), o R+7 de 10/10 refez 5 - 2 de Interpretação, 1 de Lógica
proposicional, 1 de Contagem e 1 de Equivalências -, só questão real, e o
segundo clique reabriu a mesma rodada. A tela de 03/10 abre em ~3 s; a de
10/10 em ~2 s; a de 07/11 em ~3 s.

**Testes.**

| Rodada | Resultado |
|---|---|
| `test_sabado.py` (novo) e `test_composicao.py` (8 novos do Qconcursos; os títulos dos cinco sábados) | 37 passed |
| Suíte inteira, PC (uma vez, no fim da 2B) | **2411 passed** (2392 de antes + 19 novos: 11 do sábado e 8 do Qconcursos), 0 failed, 25 min |
| `test_sabado.py` e `test_composicao.py` de novo, depois da última linha do template (o "Só questões" no R+7) | 37 passed |

### 2C — o assunto na própria faixa ✅

**O que mudou** (decisão 71):
- `src/radar/fichas.py`: `onde_na_arvore` - o assunto, o subassunto (ou que
  a árvore não tem) e o elemento de uma faixa, pela ficha ou pelos nós do
  plano; `servico/fichas.py`: `arvore_das_faixas`, para a tela;
- `src/radar/cronograma.py`: a chave nova `nos` da faixa, conferida contra a
  árvore e contra a matéria;
- a tela Hoje: a linha embaixo do título de cada faixa, com o selo da origem
  (🟣 a ficha, 📌 o plano). Sem JavaScript novo;
- `config/cronograma.yml`: `nos` nos 25 bônus (de 05/10 a 06/11) e nas 5
  interpretações cronometradas (de 08/10 a 05/11). Nenhum título mudou, e os
  dias passados não ganharam nada;
- `src/radar/edital_programa.py`: a palavra partida no hífen volta inteira
  em qualquer texto, e não só no PDF ("Tabelas-verdade");
- docs: `decisoes.md` (71), `pendencias.md`, `README.md`, `historico.md` e o
  "Estado atual" do `CLAUDE.md`.

**Com o plano e as fichas reais**: das 176 faixas de questões de 03/10 a
07/11, 167 dizem o assunto nesta linha (137 pela ficha, 30 pelo plano) e 9 na
composição do sábado. Das linhas de assunto, 84 mostram o subassunto
escolhido, 86 dizem "o assunto inteiro" e 87 "não há subassunto na árvore
para este tema". A tela de 05/10 mostra, no bônus, "📌 Lógica proposicional
(ou sentencial) · Tabelas-verdade · Equivalências"; a de 07/10, no trabalho do
preso, "🟣 Lei de Execução Penal (...) · não há subassunto na árvore para este
tema · Elemento: LEP, arts. 28 a 37".

**Testes.**

| Rodada | Resultado |
|---|---|
| `test_onde_na_arvore.py` (novo), 1ª rodada | 9 passed, 1 failed (a tela: o texto do edital dos testes dava "Tabelas- verdade", e o plano não carregava; consertado no `ler_programa`) |
| `test_onde_na_arvore.py` e `test_edital_programa.py` (1 novo: o hífen) | 22 passed |
| Suíte inteira, PC (uma vez, no fim da 2C) | **2422 passed** (2411 de antes + 11 novos: 10 do assunto na faixa e 1 do hífen), 0 failed, 25 min |

## 17 — O estoque de geradas até 07/11 (pedido de 03/10/2026)

**O pedido:** um estoque de questões de treino geradas para os conteúdos das
faixas até 07/11, sem chave da API (o Claude Code responde o `--pedido`), com
matéria, assunto e subassunto; o Passo 1 (passo a passo e plano, somente
leitura), o Passo 2 (o lote 1, junto) e o passo a passo salvo para repetir.

**O plano aprovado (decisão 73):** 57 lotes, um nó de subassunto cada, 725
questões (216 por variação, 509 do zero), por semana de uso: 05–10/10, 21 lotes
(229); 12–17/10, 15 (160); 19–24/10, 10 (141); 26–31/10, 7 (123); 02–07/11, 4
(72). Os 28 temas sem subassunto na árvore ficam sem estoque.

**O lote 1** (Direito Penal > Tipicidade, ilicitude, culpabilidade,
punibilidade > Abolitio criminis): 19 gravadas de 19, nenhuma recusada nem
repetida - 3 por variação da questão real do complementar e 16 do zero, pela
fonte oficial, marcadas sem questão real de referência. Banco 50 → 69; JSON
50 → 69; no nó, 0 → 19; a ficha do tema mostra as 19.

**O bug achado e consertado (decisão 72):** a variação herdava a matéria da
questão de base ("Conhecimentos Específicos"); agora grava a do escopo.
Arquivos: `src/radar/servico/geradas.py`, `src/radar/servico/manual.py` e um
teste novo em `tests/test_geracao_por_conteudo.py`.

**Testes** (só os de geração e importação, a pedido; a mudança de código é a
do conserto):

| Rodada | Resultado |
|---|---|
| `test_geracao_por_conteudo.py` (1 novo), `test_ia_manual.py`, `test_gerador.py` | 108 passed |
| `test_aceite.py`, `test_central_de_macetes.py`, `test_classificacao.py`, `test_fichas.py`, `test_origem.py`, `test_relatorio.py` (os outros que passam pela geração ou pela importação) | 167 passed |
| O `data/questoes_geradas.json` depois das duas rodadas | 69 (não foi sobrescrito) |
