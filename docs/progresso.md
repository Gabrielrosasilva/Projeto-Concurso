# Progresso — evolução do sistema de estudos

Andamento das etapas do [roteiro](roteiro.md). Cada etapa só é marcada como
concluída quando o critério de conclusão dela foi conferido de verdade.

Legenda: ✅ concluída · 🟡 feita, falta conferir algo · ⬜ não começada.

| # | Etapa | Situação |
|---|---|---|
| 1 | 1A — GitHub Actions verde | 🟡 falta o verde no GitHub |
| 2 | 1B — Texto de máquina e Previsão | ✅ |
| 3 | 1C — Fonte única das métricas | ✅ |
| 4 | 1D — Conferência dos dados gravados | ⬜ |
| 5 | 6A — Rotina nova do Ciclo 1 e ANKI desativado | ⬜ |
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

