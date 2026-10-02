# Progresso — evolução do sistema de estudos

Andamento das etapas do [roteiro](roteiro.md). Cada etapa só é marcada como
concluída quando o critério de conclusão dela foi conferido de verdade.

Legenda: ✅ concluída · 🟡 feita, falta conferir algo · ⬜ não começada.

| # | Etapa | Situação |
|---|---|---|
| 1 | 1A — GitHub Actions verde | 🟡 falta o verde no GitHub |
| 2 | 1B — Texto de máquina e Previsão | ✅ |
| 3 | 1C — Fonte única das métricas | ✅ |
| 4 | 1D — Conferência dos dados gravados | ✅ |
| 5 | 6A — Rotina nova do Ciclo 1 e ANKI desativado | ✅ |
| 6 | 2 — Estrutura de conteúdos | ✅ |
| 7 | 3A — Classificação do alvo e incidência | 🟡 falta a sua conferência das 162 |
| 8 | 3B — Acervo complementar FEPESE | 🟡 acervo definido; lote 1 (80) classificado; faltam os lotes 2 e 3 |
| 9 | 4 — Amostra, desempenho e controle de estudo | ⬜ |
| 10 | 5 — Geração de questões | ⬜ |
| 11 | 6B — Cronograma operacional | ⬜ |
| 12 | 7A — Selos e marcação de IA | ⬜ |
| 13 | 7B — As 6 telas no design system | ⬜ |
| 14 | 8 — Auditoria final integrada | ⬜ |

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
- [ ] workflow verde no GitHub — o `coleta.yml` só roda pelo agendamento
  (09:00 UTC) ou pelo "Run workflow"; falta disparar e conferir;
- [~] pendência A1: rebaixada a 🟡 "falta ver o verde lá". Sai do
  `pendencias.md` quando o Actions passar.

---

## 1B — Texto de máquina e Previsão (01/10/2026)

- Situação: concluída (aguardando sua aprovação para seguir à 1C)
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

- Situação: concluída (aguardando sua aprovação para seguir à 1D)
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

- Situação: concluída (aguardando sua aprovação para seguir à 6A)
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

- Situação: concluída (aguardando sua aprovação para seguir à Etapa 2)
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

- Situação: concluída (aguardando sua aprovação para seguir à 3A)
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

- Situação: 🟡 feita, falta a **sua conferência** das 162 válidas
  (Análises > Conferência). Fecha quando ela terminar.
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
- [ ] **as 162 válidas conferidas por você** — falta (Análises >
  Conferência);
- [x] `radar incidencia` e a página mostram o mapa com a amostra;
- [x] a pergunta dos arts. 1º a 12 respondida com o número (1 em 2019).


---

## 3B — Acervo complementar FEPESE (01/10/2026)

- Situação: 🟡 **passos 1, 3 e 5 de 5 feitos**. O passo 2 (sua aprovação da
  lista) virou uma regra, com a autonomia que você deu: entra a prova que tem
  matéria do edital de 2019 e passa na validação. **Falta o passo 4**, a
  classificação das questões do complementar (pendência B.8).
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
