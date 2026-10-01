# Progresso — evolução do sistema de estudos

Andamento das etapas do [roteiro](roteiro.md). Cada etapa só é marcada como
concluída quando o critério de conclusão dela foi conferido de verdade.

Legenda: ✅ concluída · 🟡 feita, falta conferir algo · ⬜ não começada.

| # | Etapa | Situação |
|---|---|---|
| 1 | 1A — GitHub Actions verde | 🟡 falta o verde no GitHub |
| 2 | 1B — Texto de máquina e Previsão | ⬜ |
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
