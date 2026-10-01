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
| 6 | 2 — Estrutura de conteúdos | ⬜ |
| 7 | 3A — Classificação do alvo e incidência | ⬜ |
| 8 | 3B — Acervo complementar FEPESE | ⬜ |
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
