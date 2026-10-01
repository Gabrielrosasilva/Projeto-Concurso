# Progresso — evolução do sistema de estudos

Andamento das etapas do [roteiro](roteiro.md). Cada etapa só é marcada como
concluída quando o critério de conclusão dela foi conferido de verdade.

Legenda: ✅ concluída · 🟡 feita, falta conferir algo · ⬜ não começada.

| # | Etapa | Situação |
|---|---|---|
| 1 | 1A — GitHub Actions verde | 🟡 falta o verde no GitHub |
| 2 | 1B — Texto de máquina e Previsão | ✅ |
| 3 | 1C — Fonte única das métricas | ⬜ |
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
