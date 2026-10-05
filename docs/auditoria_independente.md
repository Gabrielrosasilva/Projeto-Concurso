# Auditoria independente e completa do projeto (somente leitura)

Auditor: Claude Code (Opus 5.5), sessão de 04/10/2026. Não sou o autor das
etapas; trato cada afirmação dos documentos como hipótese.

**Situação deste arquivo:** CONCLUÍDO em 04/10/2026. Fase 1 (seções 1 a 6,
aprovada com os P3 também a fundo e a árvore de trabalho como alvo), registro
da execução das Fases 2 e 3 (seção 7) e o relatório final (R1 a R15). Resposta:
**PARCIALMENTE** — ver R2 e R15.

**Depois da auditoria (04/10):** a Rodada 1 do plano (R14, grupos 1, 4 e a
parte do traceback do 5) consertou o BUG-8, o BUG-1, o BUG-2 e o BUG-6
(decisão 96); a Rodada 2, o BUG-4 e o `radar padrao` por evidência (decisões
97 e 98); e as Rodadas 3 e 4, em 05/10, o BUG-5, o BUG-3, o BUG-7, os simulados
pela chave, os menores e as 4 fichas que faltavam (decisões 99 a 103). **Os 8
defeitos estão consertados**; o que ficou de propósito está na pendência G do
`pendencias.md`. O texto abaixo continua como a auditoria encontrou o sistema.

---

## 1. Ambiente e linha de base

| Item | Valor |
|---|---|
| Data/hora do início | 04/10/2026 18:18 (Florianópolis) |
| Commit (HEAD) | `b811a156b8a8296c7f3ae23e1befc9f3bcd68c52` — "Lote de 04/10: F8 a F15, as conferencias e os abertos (decisoes 82 a 90)" |
| `origin/main` local | igual ao HEAD (não fiz `fetch`: usa rede) |
| Árvore de trabalho | **44 arquivos modificados e 5 novos não commitados** (o trabalho das decisões 91 a 95). A auditoria cobre a árvore de trabalho, não só o HEAD |
| Python / SO | 3.13.15 · Windows 10 (10.0.19045) |
| Bibliotecas | pytest 8.3.4 · FastAPI 0.115.6 · SQLAlchemy 2.0.36 · Typer 0.27.2 |
| Cópia de trabalho | `C:\auditoria_copia` (359 MB; sem `.git`, `.venv`, `.env`, `__pycache__`, `.pytest_cache`, `*.egg-info` e sem `data/copias/`, que são backups) |
| Banco da cópia | `C:\auditoria_copia\data\radar.db`, snapshot pela API de backup do SQLite com o original aberto em `mode=ro` |
| Importação conferida | `python -c "import radar; print(radar.__file__)"` → `C:\auditoria_copia\src\radar\__init__.py` |
| Cópia para mutação | `C:\auditoria_mutacao` — **ainda não criada** (Fase 3) |

Variáveis usadas em toda execução na cópia: `PYTHONPATH=C:\auditoria_copia\src`,
`RADAR_DATA_DIR=C:\auditoria_copia\data`,
`RADAR_DATABASE_URL=sqlite:///C:/auditoria_copia/data/radar.db`,
`PYTHONIOENCODING=utf-8`. Python: `.venv\Scripts\python.exe` do projeto.

**Linha de base gravada** (fora do repositório, no scratchpad da sessão):
`git rev-parse HEAD`, `git status --short --ignored` (66 linhas), SHA-256 dos
20 `data/*.json`, SHA-256 dos 434 arquivos ignorados (`.env`, `data/radar.db`,
`data/provas/`, `data/copias/`, `data/logs/`, `data/pedido_ia.json`,
`data/resposta_ia.json`, `data/edital_do_alvo.json`, `RELATORIO_DO_PROJETO.pdf`)
e SHA-256 dos 49 arquivos modificados/novos da árvore de trabalho.

**Atenção para a comparação final:** o banco real está **em uso** durante a
auditoria. O `data/radar.db` foi modificado às 18:15, 3 minutos antes do início,
e tem um simulado (id 5) criado hoje às 18:15 pelo uso normal. Se o hash do
banco mudar no fim, vou separar o que é uso seu do que seria efeito meu
(nenhum comando meu abre o banco real em modo de escrita).

---

## 2. Mapa da arquitetura (conferido contra o código)

### 2.1 Diretórios

| Pasta | Conteúdo |
|---|---|
| `src/radar/` | 43 módulos na raiz (`cli.py` com 3.408 linhas é o maior) |
| `src/radar/servico/` | pacote com 30 arquivos, um por assunto; fachada em `__init__.py` (1.090 linhas) |
| `src/radar/collectors/` | `base.py` (classe `Coletor`), `concursos_no_brasil.py`, `fepese.py`, `ieses.py` |
| `src/radar/web/` | `app.py` (FastAPI), 28 templates, `static/` com `design.css`, `cronometro.js` e `dobra.js` |
| `config/` | 9 YAML |
| `data/` | 20 JSON versionados (+ `radar.db`, `provas/`, `copias/`, `logs/`, ignorados) |
| `tests/` | 104 arquivos `test_*.py` (mais `conftest.py`), **2.553 testes coletados** (`pytest --collect-only -q`, 6,3 s) |
| `.github/workflows/coleta.yml` | 09:00 UTC: `pip install -e .[dev]` → `pytest -q` → `importar` → `coletar` → `avisar` → `retificacoes --avisar` → `exportar` → commit/push de `concursos.json` e `eventos.json`. Python 3.13 |

### 2.2 Módulos da raiz (uma linha cada; primeira linha da docstring)

| Módulo | O que é |
|---|---|
| `acervo.py` | exportar e importar o banco como JSON |
| `acompanhando.py` | concursos seguidos, o que aconteceu e o que fazer |
| `alvo.py` | cargos do `config/alvo.yml`; `e_reforco` (só a auditoria usa) |
| `amostra.py` | **os mínimos de amostra num lugar só** (lê `config/amostra.yml`) e os 5 estados |
| `assuntos.py` | classificação do assunto fino com a API (caminho pago, nunca usado) |
| `auditoria.py` | auditoria automática das provas do alvo contra os PDFs |
| `automacao.py` | subir sem janela, parar, Agendador do Windows |
| `avisos.py` | Telegram |
| `calendario.py` | `.ics` dos prazos |
| `classificador.py` | decide pelo título se o concurso interessa |
| `cli.py` | os 46 comandos |
| `complementar.py` | puro: validação das provas complementares e respostas da §5 |
| `config.py` | caminhos e variáveis (`RADAR_DATA_DIR`, `RADAR_CONFIG_DIR`, `RADAR_DATABASE_URL`, tokens) |
| `conteudos.py` | puro: árvore, `resolver_escopo`, sugestões por `difflib` |
| `cronograma.py` | lê `config/cronograma.yml`: dias, faixas, chave `anki`, `consulta`, `nos`, `conteudo` |
| `db.py` | conexão; `criar_tabelas` confere esquema uma vez por conexão |
| `detalhes.py` | lê a página do post do concurso |
| `edital_ieses.py`, `edital_materias.py`, `edital_programa.py` | quadro de matérias e programa do edital |
| `elegibilidade.py`, `perfil.py` | requisitos do edital × `config/perfil.yml` |
| `eventos.py` | linha do tempo; `para_tela` (frases) |
| `fichas.py` | a ficha de estudo (`FichaDeEstudo`), `ORIGEM_DO_CAMPO`, `onde_na_arvore` |
| `foco.py` | painel do alvo (Análises), "Onde estudar primeiro" |
| `gabarito.py` | gabarito definitivo e anuladas |
| `gerador.py` | geração pela API (pago; `--valendo`) |
| `incidencia.py` | puro: mapa de incidência por nó, linha complementar, padrões |
| `leis.py` | `config/leis.yml`: links oficiais, `mudancas`, `fronteira` |
| `macetes.py` | costume da banca (comando, gabarito, termos), catálogo de palavras-chave |
| `migracoes.py` | passos numerados 1 a 5 (`VERSAO_ATUAL = 5`), cópia antes, desfazer |
| `models.py` | 14 tabelas |
| `onde_estudar.py` | puro: a conta do "por qual assunto começar" |
| `origem.py` | origens, `SELOS`, `FRASE_SEM_EVIDENCIA`, frase da questão de IA |
| `prioridade.py` | prioridade de um tema (`config/prioridade.yml`) |
| `provas.py`, `provas_ieses.py`, `questoes.py`, `questoes_ieses.py` | acervo de provas e o leitor dos cadernos |
| `regioes.py` | os três anéis (`config/regioes.yml`) |
| `substituta.py` | prova mais parecida quando não há a do cargo |
| `util.py` | ajudantes |

### 2.3 `servico/` (30 arquivos)

`avisos`, `cartoes` (Central de Macetes), `classificacoes` (questão ↔ nó,
conferência, `rechavear`), `coleta` (`COLETORES`), `compilado`, `complementar`,
`composicao` (rodadas que medem), `comum`, `conferencia` (1D), `conteudos`,
`cronograma` (diário do dia), `desempenho_por_conteudo`, `erros` (caderno),
`espacada` (1-7-30), `estudo` (estudado, revisar, refazer), `evidencia`
(**a regra única** alvo/complementar/fora), `extra`, `fichas`, `geradas`,
`incidencia`, `inicio` (home), `manual` (pedido/importar sem API), `materias`,
`metricas` (**a fonte única** de contagem), `previsao`, `provas`, `sabado`,
`semanas`, `simulado`.

### 2.4 Tabelas (`models.py`) e contagens na cópia do banco real

| Tabela | Linhas | Auditoria final (03/10) | Observação preliminar |
|---|---|---|---|
| concursos | 2.893 | 2.848 | coleta nova (a verificar na Fase 2) |
| eventos | 105 | 58 | idem (o sincronizar de 03/10 trouxe 32) |
| questoes | 8.462 | 8.433 | decisões 90 e 95: 8.433 → 8.421 → 8.462 |
| simulados | 4 | 4 | ids 2, 3, 4 e **5 (criado hoje)**; o **id 1 sumiu** (ver P-2) |
| respostas_de_simulado | 65 | 80 | 22 respondidas antes e depois; ver P-2 |
| questoes_geradas | 775 | 50 | estoque de 03/10 |
| registros_de_estudo | 2 | 2 | |
| estados_do_dia | 2 | 2 | |
| erros_anotados | 2 | 2 | |
| estudos_extras | 0 | — | |
| notas_da_semana | 0 | — | |
| conteudos | 426 | 426 | |
| classificacoes | 511 | 402 | 402 principais (170 conferidas) + 109 associadas |
| versao_do_banco | 1 linha: versão **5** | versão 4 | |

Evidência gravada na cópia: alvo 170 · complementar 7.385 · fora 907.

### 2.5 Comandos da CLI (46)

`agendar`, `assuntos`, `atualizar`, `auditar`, `avisar`, `backup`,
`baixar-provas`, `calendario`, `carga-inicial`, `classificar`, `cobertura`,
`coletar`, `complementar`, `conferir-dias`, `conteudos`, `descartar`,
`desempenho`, `detalhar`, `elegibilidade`, `eventos`, `exportar`, `favoritar`,
`fichas`, `gerar`, `hoje`, `importar`, `incidencia`, `listar`, `migrar`,
`padrao`, `parar`, `parecidas`, `previsao`, `provas`, `questoes`,
`reclassificar`, `repetidas`, `retificacoes`, `salario`, `simulados`,
`sincronizar`, `situacoes`, `status`, `subir`, `testar-telegram`, `web`.

### 2.6 Rotas web (`app.py`): 37 GET e 26 POST

GET: `/`, `/concursos`, `/tema`, `/favicon.svg`, `/favicon.ico`, `/simulado`,
`/simulado/{id}`, `/geradas`, `/hoje`, `/semanas`, `/analises`,
`/analises/materias`, `/fichas`, `/fichas/{ident}`, `/analises/desempenho`,
`/analises/incidencia`, `/analises/conferencia`, `/foco`, `/acompanhando`,
`/estudar`, `/revisao`, `/erros`, `/erros/novo`, `/mais`, `/auditoria`,
`/previsao`, `/macetes`, `/macetes/{impressao}/questoes`, `/calendario`,
`/calendario.ics` (+ `/static` montado e o handler de 404).

POST: `/favoritar`, `/salario`, `/notas`, `/coletar`,
`/simulado/{id}/descartar`, `/simulado/compilado`, `/simulado/novo`,
`/simulado/{id}/responder`, `/geradas/gerar`, `/geradas/treinar`,
`/geradas/{id}/errada`, `/hoje/rodada`, `/hoje/registrar`, `/hoje/faixa`,
`/hoje/faixa/questoes`, `/hoje/extra`, `/hoje/extra/{ident}`,
`/semanas/nota`, `/hoje/plano-b`, `/revisao/hoje`, `/revisar`,
`/fichas/{ident}/conferir`, `/analises/conferencia`, `/foco/treinar`,
`/erros/novo`, `/erros/{ident}/revisar`.

### 2.7 `config/` (9 arquivos)

| Arquivo | Controla |
|---|---|
| `alvo.yml` | alvo principal, secundários, `de_olho` |
| `amostra.yml` | seções `acervo` e `desempenho`: mínimos e estados |
| `complementar.yml` | termos de busca por matéria e o mapa catálogo → edital |
| `cronograma.yml` (4.099 linhas) | Ciclo 1 (28/09 a 07/11), `anki: desativado`, blocos, rampa, gatilho, Plano B, semanas, dias |
| `leis.yml` | links oficiais, `mudancas` (15) e `fronteira` (9) |
| `perfil.yml` | idade, escolaridade, formação, CNH |
| `prioridade.yml` | pesos: `incidencia` (complementar 0,25), `tempo`, `revisao` |
| `regioes.yml` | anéis núcleo e próximo |
| `taxonomia.yml` | tipos de elemento por família, tipos de questão, matérias fora do edital, sinônimos |

### 2.8 `data/*.json` versionados (20)

`acervo_complementar` (183 registros, 172 aceitos), `assuntos` (vazio),
`caderno_erros`, `classificacoes` (511), `concursos`, `conteudos` (426),
`edital_do_alvo` (ignorado pelo git), `estado_do_dia`, `estudo_extra` (vazio),
`eventos`, `explicacoes` (6, **não commitado**), `fichas` (61, 0 conferidas),
`macetes` (40, **não commitado**), `notas_semana` (vazio), `pedido_ia` e
`resposta_ia` (ignorados), `provas` (manifesto), `questoes_geradas` (775; 7
rejeitadas; 236 com `origem_chave`), `registro_estudo`, `simulados` (3
simulados, 60 respostas).

### 2.9 Onde a realidade diverge da documentação (para a Fase 3)

1. **JavaScript:** o pedido desta auditoria diz "o único JS é o cronômetro"; o
   código tem dois (`cronometro.js` e `dobra.js`), como mandam a decisão 30, o
   CLAUDE.md e o README. 🔁 substituído por decisão registrada.
2. **`config/regioes.yml`**: o cabeçalho diz "AINDA NÃO É LIDO POR CÓDIGO
   NENHUM"; o `regioes.py` o lê. Comentário que contradiz o código.
3. **`config/amostra.yml`**: o cabeçalho diz "Lido por src/radar/incidencia.py";
   quem lê é o `src/radar/amostra.py`.
4. **Item 18 da §23:** CLAUDE.md, `auditoria_final.md` e a tabela do topo do
   `progresso.md` dizem "18 de 19" com o item 18 pendente; a seção 18 do
   próprio `progresso.md` (linha 2637) diz que a base da média dos Macetes foi
   corrigida ("18.3/prova em 120 provas"), e o `pendencias.md` não lista mais o
   item. Um dos dois está errado.
5. Nomes do roteiro que mudaram (todos com decisão): `servico/desempenho.py` →
   `servico/desempenho_por_conteudo.py` (dec. 25); `data/backup/` →
   `data/copias/` (dec. 2.7); a validação da 3B foi para `complementar.py`, e
   não para `auditoria.py`; a ficha virou `radar/fichas.py` +
   `servico/fichas.py`; nasceram `amostra.py`, `origem.py`,
   `servico/conferencia.py`, `servico/composicao.py`, `servico/sabado.py`.
6. O workflow usa Python 3.13; o pedido da auditoria fala em "3.11+". Não é
   conflito, só registro.

---

## 3. Conferência de entregáveis por etapa

Método: para cada etapa, os arquivos do campo "Arquivos envolvidos" do roteiro
(com os nomes reais), conferidos com `os.path.exists` e com
`git diff-tree --name-only -r <commit>` dos commits da etapa (script
`entregaveis.py` no scratchpad). "Não tocado" não é falha por si: o roteiro
diz que os nomes eram propostas — cada um tem a explicação ao lado.

| Etapa | Commits | Prometidos | Existem | Não tocados pelos commits da etapa | Explicação / a verificar na Fase 2 |
|---|---|---|---|---|---|
| 1A | `afd9cc6`, `a49e3b8` | 5 | 5 | — | |
| 1B | `e3dcf84`, `f2c931d` | 8 | 8 | `tests/test_home.py` | o teste da home ficou no `test_eventos.py`/`test_foco.py` (conferir) |
| 1C | `f411b5f` `c97a890` `dbb154f` `ca11491` `2e7e3ca` | 24 | 24 | `servico/espacada.py`, `test_ultima_resposta.py` | o roteiro listava o `espacada` entre "quem refaz a conta"; conferir se ainda refaz (Fase 2, área A) |
| 1D | `9c4c1e8`, `633dd02` | 5 | 5 | `servico/metricas.py` | a conferência usa o `metricas` sem mudá-lo (coerente) |
| 6A | `594362c`, `2a70830` | 12 | 12 | `cronograma_mini.yml`, `test_faixas_do_dia.py`, `test_plano_b.py` | o progresso diz que o mini não precisou mudar; Plano B testado no `test_rotina_sem_anki.py` |
| 2 | `4db393d` `904f1b7` `fc8da2e` | 26 | 26 | `edital_programa.py`, `edital_materias.py`, `alvo.py`, `servico/geradas.py`, `servico/cartoes.py`, `auditoria.py`, `servico/erros.py`, `servico/extra.py` | o roteiro pedia que geradas, cartões e auditoria passassem pela regra única: **verificar se usam `evidencia.py`** (área B); erros/extra ganharam o `conteudo` na Etapa 4 |
| 3A | `f2ffba5` `709b23f` `344f311` `ca1c8ac` | 16 | 16 | `macetes.py`, `foco.py`, `onde_estudar.py`, `config/leis.yml` | decisão 9 da 3A adiou foco/onde_estudar para a 4; `leis.yml` só depois (dec. 65) |
| 3B | `ad14e79` `509365d` `9dfca94` `7b57e69` | 10 | 10 | `auditoria.py` | validação em `complementar.py` (dec. 3B-2) |
| 4 | `b8a56d3`, `4afb6cd` | 20 | 20 | `servico/espacada.py` | o `estudo.py` lê o mesmo histórico (progresso 4, ajuste 3) |
| 5 | `2ffbc57` | 11 | 11 | `acervo.py` | **verificar se o JSON das geradas leva os campos novos** (área F) |
| 6B | `37f9641` `d47176e` `1805637` | 14 | 14 | `cronograma.py`, `config/leis.yml` | dec. 42: o tema é a chave, o YAML não precisou mudar |
| 7A | 18 commits (`19a1e34` … `4b86613`) | 10 | 10 | — | |
| 7B | 7 commits (`d135971` … `2052a6b`) | 8 | 8 | — | |
| 8 | `43e2e59` | 7 | 7 | — | |
| Pós-8 | `792118f`, `6c327bb`, `57ef4e1`, `8c641c9`, F1–F7, lote `b811a15` | — | — | — | **decisões 91–95 só no disco, sem commit** |

Números do `progresso.md` conferidos já nesta fase (leitura direta da cópia):

| Afirmação | Documento | Na cópia | Bate? |
|---|---|---|---|
| 61 fichas, todas por conferir | progresso, CLAUDE.md | `data/fichas.json`: 61, 0 com `conferida_em` | sim |
| 511 classificações: 402 principais, 170 conferidas, 109 associadas | dec. 95 | banco e JSON: 232 + 170 principais, 109 não principais | sim |
| 232 do complementar por conferir | pendências B.8 | 232 principais sem `conferida_em` | sim (falta separar alvo × complementar: Fase 2) |
| 775 geradas, 7 rejeitadas, 236 com base | CLAUDE.md, dec. 89 e F10 | 775 · 7 · 236 | sim |
| 172 provas complementares aceitas | CLAUDE.md, dec. 95 | `acervo_complementar.json`: 172 aceitas de 183 | sim |
| 40 macetes, 6 explicações | dec. 92 | 40 · 6 | sim |
| 426 nós | auditoria final | 426 (banco e JSON) | sim |
| 8.462 questões | CLAUDE.md | 8.462 | sim |
| 170 do alvo | várias | 170 | sim |
| 2.553 testes | progresso (última suíte) | 2.553 coletados | sim (a rodar na Fase 2) |
| 18 de 19 itens da §23 | CLAUDE.md, auditoria final | contraditório no próprio progresso (ver 2.9, item 4) | **a verificar** |

---

## 4. Achados preliminares (a confirmar na Fase 2)

- **P-1 — trabalho sem commit.** As decisões 91 a 95 (o /geradas pelo nó, os
  40 macetes e 6 explicações, o acento fora da web, a conferência dos
  associados, o leitor do texto-base) estão só no disco: 44 arquivos
  modificados e 5 novos. O CLAUDE.md manda "commit e push ao fim de cada
  etapa"; a sua memória registra "git só quando ele pedir". Não é defeito de
  código, mas é risco de perda (o `data/macetes.json` e o
  `data/explicacoes.json` não existem no git).
- **P-2 — o simulado 1 sumiu do banco.** Estava em todas as cópias de
  `data/copias/` até a de 03/10 20:59 (4 simulados, 80 respostas, 22
  respondidas) e não está na de 04/10 15:03 (3 simulados, 60 respostas, 22
  respondidas). Era uma rodada de 20 questões **sem nenhuma resposta dada**,
  apagada pela regra "limpar os simulados vazios" (decisão A8 de 26/09; o
  `pendencias.md` diz "o quarto estava vazio, e a limpeza o apagou"). As
  respostas dadas foram preservadas. Classificação prevista: não é perda de
  histórico de desempenho; vou conferir na Fase 2 se a regra 8 do novo.md
  ("nenhum dado existente pode ser perdido") foi ponderada contra a decisão
  A8 em algum lugar.
- **P-3 — documentos se contradizem sobre o item 18 da §23** (seção 2.9,
  item 4).
- **P-4 — comentários de config que contradizem o código** (2.9, itens 2 e 3).
- **P-5 — o Actions de 04/10 não pode ser conferido daqui:** o último
  `coleta:` no histórico local é `5420a2a` (03/10 14:10). Sem `gh` e sem
  `fetch` (rede), fica 🔍; na Fase 2 eu digo exatamente o que você precisa
  colar.

---

## 5. Lista de requisitos

Legenda do status previsto (o que o `progresso.md` afirma hoje): ✅ feito ·
🟡 feito, falta conferência · 🧑 depende da sua conferência · ⏭️ não começado ·
🔁 mudado por decisão. Prioridade: **P1** (integridade, contagem, separação de
evidências, IA) · **P2** · **P3**.

### 5.1 Bloco A — regras invioláveis do novo.md (RI)

| ID | Requisito | Prev. | Prio |
|---|---|---|---|
| RI-1 | Alvo, complementar e desempenho nunca somados nem apresentados como um número | ✅ | P1 |
| RI-2 | Histórico nunca vira previsão ("vai cair", "certamente", "sempre cobra") em tela, terminal, relatório ou texto de IA importado | ✅ | P1 |
| RI-3 | Toda estatística mostra a amostra ("N questões · M provas") | ✅ (⚠️ item 18) | P1 |
| RI-4 | Sem dados suficientes: exatamente "Não há evidência suficiente no acervo para afirmar isso." | ✅ | P1 |
| RI-5 | Questão gerada nunca é oficial, e isso está sempre visível | ✅ | P1 |
| RI-6 | ANKI desativado e não removido (código, dados, config) | ✅ | P2 |
| RI-7 | Manhã também tem questões | ✅ | P2 |
| RI-8 | Nenhum dado existente perdido; mudança de estrutura preserva e migra | ✅ | P1 |
| RI-9 | Não inventar vínculo nem classificação; o que não é seguro fica pendente/sem base | ✅ | P1 |
| RI-10 | Números iguais em todas as telas, lidos da mesma fonte | ✅ | P1 |

### 5.2 Bloco A — seção 23 (numeração do `auditoria_final.md`)

| ID | Requisito | Prev. | Prio |
|---|---|---|---|
| C23-1 | A ficha diz exatamente o que ler | ✅ 🧑 | P2 |
| C23-2 | Onde ler (fonte oficial com link correto) | ✅ 🧑 | P2 |
| C23-3 | Como procurar (buscas) | ✅ 🧑 | P2 |
| C23-4 | O que entender | ✅ 🧑 | P2 |
| C23-5 | O que memorizar | ✅ 🧑 | P2 |
| C23-6 | Quais pegadinhas (do acervo, com a questão) | ✅ 🧑 | P2 |
| C23-7 | Como a FEPESE cobrou (alvo e complementar separados, com amostra) | ✅ | P1 |
| C23-8 | Quais questões reais estão relacionadas | ✅ | P2 |
| C23-9 | Quantas questões fazer (escopo exato) | ✅ | P2 |
| C23-10 | Quais geradas posso fazer | ✅ | P2 |
| C23-11 | Quais erros revisar (radar e caderno, nunca somados) | ✅ | P2 |
| C23-12 | Por que priorizado hoje (cada fator com número e origem) | ✅ | P2 |
| C23-13 | Selecionar matéria → assunto → subassunto → elemento e gerar sem sair do escopo | ✅ 🔁 (dec. 66) | P1 |
| C23-14 | Questões, acertos e erros iguais em todas as telas | ✅ | P1 |
| C23-15 | Incidência do alvo não muda com prova complementar (e nada do alvo: Onde estudar, prioridade, composição) | ✅ | P1 |
| C23-16 | Nenhum dado antigo perdido | ✅ | P1 |
| C23-17 | ANKI desativado e reativável | ✅ | P2 |
| C23-18 | Nenhuma estatística sem amostra | ⚠️ (contraditório: ver P-3) | P1 |
| C23-19 | Nenhuma questão gerada aparece como oficial | ✅ | P1 |

### 5.3 Bloco A — critério de conclusão de cada etapa (R)

| ID | Requisito | Prev. | Prio |
|---|---|---|---|
| R-1A-1 | `pytest -q` verde no PC | ✅ | P1 |
| R-1A-2 | Workflow verde no GitHub (último run) | ✅ (04/10 ⚪) | P2 |
| R-1A-3 | Pendência A1 fora do `pendencias.md` | ✅ | P3 |
| R-1A-4 | Nenhum teste depende do Windows ou da data de hoje (relógio congelado ou data relativa) | ✅ | P1 |
| R-1B-1 | Eventos em frases (sem `inscricoes_abertas`, `->`, `_`) na home, Análises, Acompanhando, Calendário | ✅ | P2 |
| R-1B-2 | Previsão: "Atrasado: era esperado em AAAA" e "este ano / há 1 ano / há N anos" | ✅ | P2 |
| R-1B-3 | A2 e A3 fora do `pendencias.md` | ✅ | P3 |
| R-1C-1 | `radar hoje --data 2026-09-28` e a tela Hoje de 28/09 com a conta fechada (31 = 13 + 8 + 10) | ✅ | P1 |
| R-1C-2 | Nenhum serviço ou template fora do `metricas.py` soma acerto/erro/questão (busca) | ✅ | P1 |
| R-1C-3 | Decisão registrada, com o que muda na E2 | ✅ | P3 |
| R-1C-4 | `total = acertos + erros + sem resultado anotado + treino de IA` em todo recorte, com teste | ✅ | P1 |
| R-1D-1 | `radar conferir-dias` só lê; o relatório roda no banco | ✅ | P1 |
| R-1D-2 | Correções aplicadas com cópia antes; totais antes × depois | ✅ | P2 |
| R-6A-1 | Dia útil depois de 02/10 com questões de manhã, sem aumentar os minutos do dia | ✅ | P2 |
| R-6A-2 | Hoje e `radar hoje` de dia posterior: manhã com questões e "ANKI temporariamente desativado" | ✅ | P2 |
| R-6A-3 | Religar (`anki: ativado`) volta tudo igual; nada do ANKI apagado (36 faixas, 30 `baralho`) | ✅ | P2 |
| R-6A-4 | README explica como religar | ✅ | P3 |
| R-6A-5 | Dias anteriores a 02/10 idênticos ao YAML de antes | ✅ | P2 |
| R-2-1 | Migração com versão, passos, cópia, antes × depois e `--desfazer` | ✅ | P1 |
| R-2-2 | `radar conteudos`: 11 matérias e o mesmo nº de assuntos (85) do `edital_programa.py` | ✅ | P2 |
| R-2-3 | Evidência: 170 alvo; 2016 complementar; IESES fora | ✅ | P1 |
| R-2-4 | Pendentes listados | ✅ | P2 |
| R-3A-1 | `docs/auditoria.md`: extraídas × prova, completa/parcial/pendente, sem gabarito, anuladas, erros de extração | ✅ | P2 |
| R-3A-2 | 170 do alvo classificadas (pendente com motivo) e 162 válidas conferidas | ✅ | P1 |
| R-3A-3 | `radar incidencia` e a página com o mapa e a amostra | ✅ | P1 |
| R-3A-4 | Pergunta dos arts. 1º a 12 do CP respondida com número | ✅ | P3 |
| R-3B-1 | `docs/complementar.md` gerado e coerente com o banco | ✅ | P2 |
| R-3B-2 | Validação mínima por prova (parsing, gabarito, hash único); sem validação fica fora e diz por quê | ✅ | P1 |
| R-3B-3 | Classificação do complementar conferida por amostra, com a taxa de erro e o aviso na tela | 🟡 🧑 | P2 |
| R-3B-4 | Incidência com alvo e complementar em linhas separadas, cada um com amostra | ✅ | P1 |
| R-4-1 | Nenhum mínimo de amostra fora do `config/amostra.yml` (exceção declarada: o 3 do `erros.py`) | ✅ | P1 |
| R-4-2 | Página "Meu desempenho" com estado e amostra por nó | ✅ | P2 |
| R-4-3 | Definição de "estudado" no `decisoes.md` igual à do código | ✅ | P2 |
| R-5-1 | Os dois exemplos da §23: literais recusados com sugestão; equivalentes reais rodam | ✅ 🔁 | P1 |
| R-5-2 | Nenhuma questão fora do escopo entra (pedido e importação) | ✅ | P1 |
| R-6B-1 | Cenário do Art. 5º, I a XVI, respondido pela ficha com dados reais (os 12 pontos) | ✅ | P2 |
| R-6B-2 | Conferência das 61 fichas | 🧑 | — |
| R-6B-3 | Ciclo 2 (passo 5) | ⏭️ | — |
| R-7A-1 | Selos novos nos dois temas; especificacao e decisoes com as cores novas | ✅ | P2 |
| R-7B-1 | As 6 telas com `body class="ds"`, sem o CSS antigo, nos dois temas | ✅ | P3 |
| R-8-1 | Cada item da §23 com evidência; o que não atende virou pendência; "Estado atual" reescrito | 🟡 | P2 |

### 5.4 Bloco A — decisões que viraram regra de sistema (D)

| ID | Decisão | Requisito verificável | Prev. | Prio |
|---|---|---|---|---|
| D-SELOS | 53–55 | 🟢🔵🟡🟣 + 📌 em `origem.py`; macro e tokens claro/escuro; `--selo-*` só no `design.css`; metas com tokens próprios; sem resíduo dos selos antigos | ✅ | P2 |
| D-ORIGEM-NO-DADO | 54 | o serviço grava a origem; o template só desenha | ✅ | P2 |
| D-FRASE | 56 | a frase padrão numa constante só; "Amostra insuficiente" para desempenho; "não sei ainda" só para fato | ✅ | P1 |
| D-IA-TELA | 57 | 🟣 + "Gerada por IA: não é questão oficial da FEPESE." em toda tela que mostra gerada; "Resposta da IA", nunca "Gabarito definitivo" | ✅ | P1 |
| D-AMOSTRA | 6, 19, 83 | mínimos 20/10/6, corte 60%, meta da matéria ou 79/100; evolução 20; tendência 50; provas 3 | ✅ | P1 |
| D-ESTADOS | 6 | os 5 estados e as bordas (19/20, 59/60%, meta, dobro com 1 e 2 dias); insuficiente fora de ordenação e projeção | ✅ | P1 |
| D-RECORTES | 1C-4, 1C-5 | recortes de nome fixo (radar, anotado, IA, total) escritos na tela; "respostas" × "questões" | ✅ | P1 |
| D-REGISTRO | 1C-7 | o registro do dia não compete com o número calculado | ✅ | P1 |
| D-INCONSISTENTE | 1C-3 | acerto > questões é acusado (`ContaInconsistente`), sem `max(…,0)` | ✅ | P1 |
| D-FAIXA-0 | 1D-1 | faixa de questões com 0 é recusada | ✅ | P2 |
| D-FUSO | 1C, 51 | o dia é o de Florianópolis (resposta às 01:30 UTC cai no dia anterior); procedência com data local | ✅ | P1 |
| D-EVIDENCIA | 2-1, 75 | uma regra em `servico/evidencia.py`; regras paralelas antigas só delegam | ✅ | P1 |
| D-COMPL-ACEITO | 3B-5, 75 | só prova aceita no `acervo_complementar.json` entra em estatística, treino, compilado, composição | ✅ | P1 |
| D-COMPL-DISTINTA | 3B-14 | complementar conta questão distinta, com ocorrências ao lado | ✅ | P2 |
| D-CAMINHO | 2-2 | todo vínculo a conteúdo é o caminho de nomes (faixa, caderno, extra, gerada, ficha) e resolve para nó existente | ✅ | P1 |
| D-TAXONOMIA | 2-3 | tipo novo no YAML funciona sem migração | ✅ | P2 |
| D-CHAVE | 3A-1, 77, 90 | classificação e base da gerada pela chave; reler o caderno leva a classificação só quando é a mesma questão | ✅ | P1 |
| D-IMPORT-CLASSIF | 3A-2 | importação recusa: fora do pedido, sem justificativa, assunto fora do edital, tipo fora da lista, elemento sem subassunto, matéria trocada, já conferida | ✅ | P1 |
| D-INCID | 3A-7 | só o alvo; nó e os de cima; anulada e pendente fora e mostradas; denominador = provas com a matéria | ✅ | P1 |
| D-PADROES | 3A-8, 78 | padrões com amostra e origem; complementar só com gabarito definitivo; tipo e pegadinha só de classificação conferida | ✅ | P1 |
| D-ESTUDADO | 20, F14 | estudado = faixa de estudo ou extra de teoria/lei seca; praticado = resposta; filho não herda | ✅ | P2 |
| D-DIVISAO | 7, 21 | "radar X% em N · anotado Y% em M", nunca somado na tela; IA nunca; só sem consulta no estado | ✅ | P1 |
| D-REVISAO | 23, 79, 82, 85 | 3 gatilhos; âncora 1-7-30; revisão fora do radar passa de etapa; primeiro contato = primeira resposta | ✅ | P2 |
| D-REFAZER | 24 | erradas no radar e caderno em listas separadas | ✅ | P2 |
| D-ESCOPO | 31–37 | escopo fechado; nome inexistente para com até 5 sugestões; nada alargado; revisão sem estudado para; artigo pelo número | ✅ | P1 |
| D-GERADA-CAMPOS | 35, 38, 39, 77, 89 | `modo_do_pedido`, base, evidência da base, artigo, `conteudo`, `origem_chave`; antigas legíveis; "sem questão real de referência" | ✅ | P1 |
| D-FICHA | 41–43, 47 | uma estrutura; tema pela chave do título; nós justificados; importação recusa previsão; conferida não é sobrescrita | ✅ | P2 |
| D-PRIORIDADE | 44, 63 | fórmula no YAML; complementar só na ordem com peso 0,25; peso 0 = ordem do alvo; "regra, não previsão" | ✅ | P1 |
| D-MIGRACAO | 2-7, 80 | passo nunca editado; passo que perde linha é desfeito; `--desfazer`; esquema conferido uma vez por conexão | ✅ | P1 |
| D-COMPOSICAO | 67, 69 | rodada que mede: só real da FEPESE (alvo + complementar aceito), sem anulada, sem gerada, gravada e não recriada | ✅ | P1 |
| D-SABADO | 70 | revisão semanal, R+7 dos diagnósticos e comparação de 07/11 em `servico/sabado.py`, contas no `metricas` | ✅ | P2 |
| D-ONDE-ARVORE | 71, 74, 81 | faixa diz onde está na árvore; Onde estudar e espaçada pela árvore; faixa sem `conteudo` conta só situação e datas | ✅ | P2 |
| D-ASSOCIADOS | 86, 94 | associados nunca entram na contagem; conferíveis | ✅ 🧑 | P2 |
| D-JS | 30 | só `cronometro.js` e `dobra.js`, só na Hoje; a tela funciona sem eles; nada inline | ✅ 🔁 | P3 |
| D-COR | 88 | `?cor=` pinta; `?tema=` só filtra Macetes | ✅ | P3 |
| D-LEIS | 65, 84 | `mudancas` e `fronteira` com procedência; não conferido sai 🟣 | ✅ 🧑 | P2 |

### 5.5 Bloco A — regras permanentes do CLAUDE.md (CL)

| ID | Requisito | Prev. | Prio |
|---|---|---|---|
| CL-1 | Cada fonte é um arquivo em `collectors/`, herda de `Coletor`, devolve `list[ItemColetado]`, está em `COLETORES` | ✅ | P2 |
| CL-2 | Nada fora de `collectors/` sabe de onde vem o dado | ✅ | P3 |
| CL-3 | `robots.txt`, atraso e User-Agent na classe base, sem exceção | ✅ | P1 |
| CL-4 | Nada raspa Qconcursos, login ou paywall; DOM/SC, DOU, Querido Diário e Planalto fora | ✅ | P1 |
| CL-5 | Link original sempre guardado | ✅ | P3 |
| CL-6 | Coletor e classificador com teste de fixture; nenhum teste vai à internet | ✅ | P1 |
| CL-7 | Teste não depende do Windows nem da data de hoje (= R-1A-4) | ✅ | P1 |
| CL-8 | Questão de IA treina e nunca mede (fora de incidência, padrão, macete, acerto, desempenho do alvo; acerto dela é 2º número) | ✅ | P1 |
| CL-9 | Dado de IA só com procedência (modelo e data); simulação mostra o pedido, não resposta inventada | ✅ | P1 |
| CL-10 | Dependência nova justificada (`pyproject.toml` desde 25/09) | ✅ | P3 |
| CL-11 | `servico` é pacote, um arquivo por assunto; sem lógica duplicada entre eles | ✅ | P3 |
| CL-12 | Mudança de estrutura do banco = passo novo em `migracoes.py` (sem `ALTER` solto fora dele) | ✅ | P1 |
| CL-13 | Concurso irrelevante não é apagado; `motivo_relevancia` gravado; anéis em `config/regioes.yml`; `indefinida` sem edital | ✅ | P3 |
| CL-14 | Alvo e `de_olho` em `config/alvo.yml`, nunca no código | ✅ | P3 |
| CL-15 | Segredos: nada de token/chave no código, config, data, docs nem no histórico do git; `.env` no `.gitignore`; `.env.example` sem valor real | ✅ | **P1 (repositório público)** |
| CL-16 | GET nunca grava; mutação só por POST; `radar web --rede` sem autenticação documentado | ✅ | P2 |
| CL-17 | Commit e push ao fim de cada etapa; decisão que muda vai ao `decisoes.md` | ⚠️ (P-1) | P3 |

### 5.6 Bloco B — demais seções do novo.md (amostragem, ≥ 3 por seção)

Onde a seção já está coberta a fundo pelo bloco A, o item B aponta o ID de A e
acrescenta só o que A não pega.

| ID | Seção | Requisito | Prev. |
|---|---|---|---|
| N1-1 | §1 | A cadeia edital → … → revisão está ligada: classificação alimenta incidência, que alimenta prioridade, ficha, geração e composição | ✅ |
| N1-2 | §1 | A ficha usa incidência, desempenho, geradas e fila de revisão reais (não cópias) | ✅ |
| N1-3 | §1 | Não há estrutura paralela para o mesmo conceito (ex.: duas filas de revisão) | ✅ |
| N2-1 | §2 | Cada questão do alvo tem enunciado, 5 alternativas, matéria, gabarito, prova, ano, cargo e número; anuladas marcadas | ✅ |
| N2-2 | §2 | O relatório diz extraídas × prova por prova e sem gabarito/inconsistente | ✅ |
| N2-3 | §2 | Pendentes separadas nas estatísticas, nunca num assunto qualquer | ✅ |
| N3-1 | §3 | Incidência por matéria, assunto, subassunto e elemento, com questões, provas e anos | ✅ |
| N3-2 | §3 | Recorrentes, uma vez só e do edital que não apareceram; tipo de questão | ✅ |
| N3-3 | §3 | Anuladas e pendentes: se entram ou não está documentado e visível | ✅ |
| N4-1 | §4 | Toda prova e toda questão têm a evidência gravada | ✅ |
| N4-2 | §4 | Exibição "Polícia Penal SC: … · Acervo complementar FEPESE: …" | ✅ |
| N4-3 | §4 | Teste automatizado de que o alvo não muda com prova complementar | ✅ |
| N5-1 | §5 | Por prova: PDF, gabarito, banca, concurso, cargo, ano, fonte, URL, data de inclusão, evidência, status de validação, anuladas | ✅ |
| N5-2 | §5 | Hash duplicado com outro nome recusado | ✅ |
| N5-3 | §5 | As 6 perguntas respondidas por consulta, sem pesquisa manual | ✅ |
| N6-1 | §6 | 4 níveis, os 2 de baixo opcionais; nada obriga artigo | ✅ |
| N6-2 | §6 | A mesma hierarquia em estudo, geração, análise e cronograma | ✅ |
| N6-3 | §6 | Integridade da árvore: nome único no pai, sem órfão, nível coerente | ✅ |
| N7-1 | §7 | A consulta só por matéria continua e se diz "simulado" | ✅ |
| N7-2 | §7 | Filtro funciona para elemento não jurídico (regra, tipo de problema) | ✅ |
| N7-3 | §7 | Mesmo filtro na tela `/geradas` | ✅ |
| N8-1 | §8 | Três modos; sem modo: com assunto = treino, só matéria = simulado | ✅ |
| N8-2 | §8 | Revisão só com nós estudados; sem nada estudado, para | ✅ |
| N8-3 | §8 | Simulado respeita o peso do edital (dec. 68) | ✅ |
| N9-1 | §9 | A relação gerada → real → prova → ano → gabarito → fonte é navegável | ✅ |
| N9-2 | §9 | Sem real: "sem questão real de referência"; nenhum vínculo inventado | ✅ |
| N9-3 | §9 | A base registra alvo ou complementar | ✅ |
| N11-1 | §11 | Uma estrutura de tarefa com os 16 campos (sem duplicata) | ✅ |
| N11-2 | §11 | Aplicado a todos os conteúdos do cronograma (quantas faixas de estudo têm ficha) | 🟡 |
| N11-3 | §11 | Campo sem dado usa a frase padrão, não é inventado | ✅ |
| N12-1 | §12 | Tarefa com começo, meio e fim, também nas matérias não jurídicas | ✅ |
| N12-2 | §12 | Nenhuma ficha genérica ("estude LEP") | ✅ 🧑 |
| N12-3 | §12 | 8 fichas no teste de executabilidade (Art. 5º I–XVI; Penal; LEP; Proc. Penal; Português; Rac. Lógico; Sociologia; Leg. Estadual) | ✅ 🧑 |
| N13-1 | §13 | Padrões: assuntos, artigos, alternativas, termos, literalidade/interpretação | ✅ |
| N13-2 | §13 | "Padrão identificado no acervo analisado", nunca "a FEPESE sempre" | ✅ |
| N13-3 | §13 | Cada padrão com N questões, M provas e origem | ✅ |
| N14-1 | §14 | Taxonomia por família, ampliável sem mudar o banco | ✅ |
| N14-2 | §14 | Os 10 objetivos (incl. conceitos associados e "sem amostra suficiente") | ✅ |
| N14-3 | §14 | Alvo, complementar e desempenho separados por elemento | ✅ |
| N15-1 | §15 | Fatores (peso, incidência, provas, questões, desempenho, respondidas, erros, não estudados, baixo desempenho, revisão) | ✅ |
| N15-2 | §15 | "Você está estudando isto porque…" com cada fator | ✅ |
| N15-3 | §15 | Regra documentada e ajustável | ✅ |
| N16-1 | §16 | Nenhum "você é fraco em X" com 1–2 respostas | ✅ |
| N16-2 | §16 | Limites documentados com o motivo | ✅ |
| N16-3 | §16 | Insuficiente fora de ordenação e projeção | ✅ |
| N17-1 | §17 | As 8 telas da §17 (Hoje, histórico, gráficos, estatísticas, desempenho, relatórios, matérias, assuntos) com o mesmo número no mesmo período | ✅ |
| N17-2 | §17 | Gráficos e resumo diário na mesma fonte; semana sem questão não vira zero | ✅ |
| N17-3 | §17 | Estados identificados e regra única documentada | ✅ |
| N18-1 | §18 | ANKI não obrigatório no cronograma | ✅ |
| N18-2 | §18 | Distribuição proposta antes de aplicar; dia sustentável | ✅ |
| N18-3 | §18 | Como reativar dito exatamente | ✅ |
| N19-1 | §19 | Estudados, não estudados, erros, revisar, refazer, última revisão | ✅ |
| N19-2 | §19 | Taxa por assunto/subassunto e evolução por assunto (igual à Semanas no período) | ✅ |
| N19-3 | §19 | Alimenta o modo revisão e o `quando_revisar` da ficha | ✅ |
| N20-1 | §20 | Informação jurídica prioriza fonte oficial | ✅ |
| N20-2 | §20 | Conclusão de padrão dita "análise do acervo" | ✅ |
| N20-3 | §20 | Nenhum conteúdo de IA (questão, macete, explicação, ficha, lei alterada) sem 🟣 e procedência | ✅ |
| N21-1 | §21 | Cópia antes de mexer na estrutura | ✅ |
| N21-2 | §21 | Histórico não recalculado em silêncio; dado antigo que não coube fica pendente | ✅ |
| N21-3 | §21 | Conferência antes × depois e desfazer | ✅ |
| N22-1 | §22 | Cada etapa com testes próprios, executados nela | ✅ |
| N22-2 | §22 | Commits não misturam etapas | ✅ |
| N22-3 | §22 | Progresso registra objetivo, arquivos, testes, resultado e critério por etapa | ✅ |

**Totais da lista:** 10 RI · 19 C23 · 43 R · 36 D · 17 CL (bloco A = 125) e
63 N (bloco B). Total: **188 requisitos**.

---

## 6. Como as Fases 2 a 4 vão rodar (para você aprovar junto)

- **Fase 2:** a suíte inteira **uma vez**, na cópia, com `--durations=10`
  (≈ 14 a 25 min), e o hash do `C:\auditoria_copia\data` antes e depois — para
  pegar teste que ainda escreve em `data/` (o defeito da decisão 50). Depois,
  cada requisito do bloco A pelas áreas A a N da seção 7 do pedido, com
  contra-exemplo (fuso, duplicidade, prova complementar nova, tipo novo na
  taxonomia, importações fabricadas, peso da prioridade, ANKI religado,
  migração desfeita) — tudo na cópia, com GET pelo `TestClient`.
- **Fase 3:** bloco B, a tabela conceito × módulo, os testes de mutação em
  `C:\auditoria_mutacao` (8 regras), regressões, saúde do código, segurança
  (inclusive `git log --all -p -S` por padrões de token) e documentação.
- **Fase 4:** relatório final, riscos e plano de correção.

**O que não vou executar em fase nenhuma** (usa rede, git, Telegram ou mexe no
Windows): `coletar`, `atualizar`, `carga-inicial`, `provas`, `baixar-provas`,
`detalhar`, `elegibilidade`, `retificacoes`, `assuntos`, `avisar`,
`testar-telegram`, `gerar --valendo`, `sincronizar`, `backup`, `agendar`,
`subir`, `parar`.

**Pontos em que preciso da sua decisão agora:**
1. aprovar, cortar ou repriorizar a lista acima (188 itens; os P3 podem cair
   para amostragem se você quiser encurtar);
2. o Actions (R-1A-2, P-5): se puder, cole a saída dos últimos 5 runs do
   `coleta.yml` (página Actions do GitHub: data, status e o commit);
3. confirmar que a auditoria deve cobrir a **árvore de trabalho** (com as
   decisões 91–95 sem commit), e não só o HEAD `b811a15` — foi o que assumi.

---

## 7. FASE 2 — progresso parcial (salvo durante a execução)

Cópias usadas: `C:\auditoria_copia` (suíte inteira, sem outra escrita) e
`C:\auditoria_mutacao` (snapshot novo do banco às 18:52; experimentos que
gravam dado, e depois as mutações de código). Ferramenta fora do projeto:
`time-machine` em `C:\auditoria_ferramentas` (pip `--target`, sem tocar no
`.venv`).

### 7.1 Confirmado por execução (E)

- **Contagem (área A):** `metricas.do_dia`, tela `/hoje?data=`, `radar hoje
  --data`, `/semanas` e `/analises/materias` dão o mesmo número: 28/09 =
  "31 questões = 13 acertos + 8 erros + 10 de treino de IA" (IA 7 de 10, fora
  do acerto); 29/09 = "37 = 4 + 18 + 15 sem acerto anotado"; Semana 1 = "68 =
  17 + 26 + 15 + 10" (Semanas) = soma dos 3 cartões de Minhas matérias (42 +
  15 + 11; acertos 11 + 0 + 6; erros 21 + 0 + 5). Os números de referência do
  `auditoria_final.md` continuam iguais.
- **Incidência recalculada à mão (área D):** script próprio por SQL
  (`incid_manual.py`), 11 linhas — Língua Portuguesa (22 · 2 provas; 2
  anuladas, 1 pendente), Compreensão e interpretação (9 · 2), LEP (10 · 1,
  2019), Direito Administrativo (2 · 1, 2013), Noções de Informática (10 · 1,
  2013), Raciocínio Lógico (9 · 1; 1 anulada), Sociologia (9 · 1; 1 anulada),
  CF art. 5º XI (1 · 1, 2013), Emprego da crase (0 · 0), Direito Penal (9 · 2;
  4 pendentes), Legislação Estadual (16 · 2; 1 anulada, 3 pendentes): **todas
  iguais** à saída do `radar incidencia`. Direito Processual Penal junta o
  "Direito Processo Penal" de 2013 (6 + 1 anulada + 4 pendentes = 11; 2 provas).
- **Integridade da árvore e das classificações (área C):** 426 nós, 0 órfãos,
  0 nível incoerente, 0 nome repetido no mesmo pai, 0 elemento sem tipo; 85
  assuntos do edital com texto literal; 511 classificações, 0 com mais de uma
  principal, 0 em nó inexistente, 0 sem procedência, 0 principal sem
  justificativa, 0 pendente sem motivo, 0 chave órfã, 0 status incoerente com
  a árvore; alvo = 170 questões, 162 válidas, todas com principal e
  conferidas (146 completas, 9 parciais, 15 pendentes); nenhuma chave em duas
  evidências; gerada, caderno e extra apontam só para nós que existem.
- **Importação de classificação fabricada (área C):** 1 gravada e 7 recusas
  corretas — sem justificativa, assunto fora do edital ("Regência verbal"),
  questão fora do pedido, tipo de elemento fora da família, pendente sem
  motivo, elemento sem subassunto, tipo de questão inexistente.
- **Tipo novo na taxonomia sem migração (D-TAXONOMIA):** "tipo novo da
  auditoria" acrescentado ao `config/taxonomia.yml` da cópia; a importação
  aceitou e criou o nó com o tipo; o banco ficou na versão 5.
- **Importação de geradas fabricada (área F):** as 5 recusas esperadas
  funcionam — fora do escopo, sem artigo, artigo de outro dispositivo, do zero
  com vínculo a questão real (pedido adulterado), do zero sem a marca
  "sem questão real de referência" (pedido adulterado).
- **Varredura de telas por GET (área K):** 61 aberturas; nenhuma com status
  500, "Traceback", `None`, `nan`, `undefined` ou Jinja cru; **o conteúdo do
  banco é idêntico antes e depois de todos os GET** (hash do dump). Só a Hoje
  tem `<script>` (os dois arquivos da decisão 30).
- **Rotina (área H):** `radar hoje --data 2026-10-05`: manhã com Fixação de
  8 + 6 questões e "ANKI temporariamente desativado".

### 7.2 Defeitos confirmados até aqui

- **BUG-1 (geração, RI-9/D-CAMINHO):** a importação de gerada aceita um
  `conteudo` que **não existe na árvore**, desde que comece pelo caminho do
  escopo. Reprodução na cópia: pedido com escopo fechado em "LEP > … >
  Assistência ao preso e ao egresso" e `--elemento "LEP, art. 26"`; resposta
  com `"conteudo": "… > LEP, art. 26 > No inventado pela IA"` → gravada
  (id 777). Causa: `servico/manual.py:977` confere só o prefixo.
- **BUG-2 (geração, §8/C23-13):** com `--elemento` pedido, a importação aceita
  questão declarada num **elemento irmão que não foi pedido**: pedido só do
  art. 26 → aceita `"conteudo": "… > LEP, art. 24"` com o artigo "art. 26"
  (id 778); pedido só do "Protocolo de San Salvador" → aceita questão no
  "Pacto de San José da Costa Rica", porque para elemento que não é artigo
  `_mesmo_dispositivo` devolve sempre verdadeiro (`manual.py:1004-1007`) e o
  escopo conferido é o do subassunto (`manual.py:977`, `escopo` = `escopo.no`,
  e não `Escopo.dentro`).
- **BUG-3 (árvore, §4/§14):** a classificação do complementar (02/10) criou
  **nós paralelos** a conceitos que o alvo já tinha (01/10), em vez de usar o
  mesmo nó: "Características dos direitos humanos" (alvo 2 num assunto,
  complementar 2 em outro), "Sistema interamericano de proteção" (3 × 1, em
  assuntos diferentes), "Gerações (dimensões) de direitos" × "… dos direitos
  humanos" (2 × 1), Maria da Penha com três nós de "formas de violência",
  CPP art. 306 em "Comunicação da prisão" × "… e audiência de custódia",
  segurança pública com três nós de "órgãos/atribuições", tortura com dois de
  "penas". Efeito: no nó do alvo a linha complementar sai "—" para um
  conteúdo que o complementar tem, e a ficha/prioridade subestimam o
  complementar. Causa: a importação cria nó novo sem procurar nome parecido.

### 7.3 Achados menores já vistos

- Texto de tela sem acento: "sem materia (30)" em `/simulado`; o nível cru
  "· materia" e "conteudo" em `/analises/desempenho`.
- Duas regras de sinônimo de matéria: `config/taxonomia.yml`
  (`sinonimos_de_materia`) e `servico/compilado.mesma_materia` (fuzzy 0,85);
  filtros pela coluna crua `QuestaoDeProva.materia ==` em
  `servico/simulado.py:98`, `servico/geradas.py:55`, `servico/espacada.py:168`
  e `servico/complementar.py:427` (a testar: 2013 "Direito Processo Penal").
- 4 temas de 28/09 a 01/10 sem ficha (Substantivo e adjetivo; Artigo,
  numeral e pronome; Verbo 1; Interpretação 1) — o pedido de fichas só olha
  de hoje em diante.
- Anulada respondida: o `metricas` a conta no acerto do dia (decisão 1D-5),
  o `desempenho_por_conteudo` a tira (`_questoes_respondidas`). Divergência
  sem caso real hoje.
- `servico/conferencia.py:259` conta os acertos de IA por conta própria (a
  mesma conta do `metricas`, refeita).

**Mais confirmações por execução (E), na `C:\auditoria_mutacao`:**

- **Fuso e duplicidade (D-FUSO, R-1C):** resposta gravada às 01:30 UTC de
  06/10 conta em 05/10 (o dia de Florianópolis) e não em 06/10; a mesma
  rodada recusa a segunda resposta (`responder` devolve `None`); a mesma
  questão em duas rodadas dá 2 respostas no dia ("2 questões = 1 acertos + 1
  erros") e +1 no acumulado de questões (12 → 13).
- **Prova complementar nova (C23-15, N4-3):** uma prova FEPESE inventada,
  aceita no `acervo_complementar.json`, com 3 questões classificadas no nó do
  alvo "CF, art. 5º, XI": o `radar incidencia` muda em 8 linhas, **todas** na
  coluna/linha do complementar (o nó passa de "—" a "3 questões · 1 prova");
  nenhuma coluna do alvo muda. O fator do alvo na prioridade das 61 fichas
  fica idêntico; só o fator complementar muda.
- **Prioridade (D-PRIORIDADE):** reproduzida à mão — Art. 5º I–XVI: 5 ×
  (1/15 + 0,25 × 2/34) = 0,407 (o sistema: 0,4069); Vozes do verbo: 15 ×
  0,0455 = 0,682 (0,6818). Peso do complementar 0 → 24 fichas mudam de lugar,
  o complementar zera nas 61 e o total vira peso × alvo × desempenho × tempo
  × revisão; peso 1,0 → 22 mudam. A ficha escreve "acervo complementar com
  peso 0 … não entra".
- **ANKI (RI-6, R-6A-3):** 36 faixas `tipo: anki` e 30 `baralho` no YAML;
  `anki: ativado` na cópia → "22:00-22:15 Anki · Anki [3] LEP" e o Bônus vai
  para 22:15; de volta a `desativado` → saída idêntica à de antes; o bloco
  `pos22` nasce sem `open` e com a frase.
- **Rotina (RI-7, R-6A-1, R-6A-5):** contra o YAML de antes da 6A
  (`594362c^`): os 26 dias úteis de 02/10 a 07/11 têm questões de manhã (14) e
  ficaram 20 min mais curtos (ex.: 05/10, 280 → 260 min sem o bônus; 28/10,
  310 → 290); nenhum dia útil de antes de 02/10 mudou (dia montado igual).
- **Migração (R-2-1, D-MIGRACAO):** o banco da cópia de antes da Etapa 2
  (`data/copias/migracao-v0-para-v1-…/radar.db`, versão 0) migrado numa pasta
  isolada: 0 → 5, cópia antes, antes × depois sem nenhuma linha perdida;
  2ª vez "Nada a migrar"; `--desfazer` devolve um banco com o **dump
  idêntico** ao original e guarda o de antes de desfazer.

**Mais defeitos confirmados:**

- **BUG-4 (sinônimo de matéria, §7/N7-1):** o sinônimo "Direito Processo
  Penal" (2013) = "Direito Processual Penal" vale na incidência, mas não nos
  filtros pela coluna crua. `geradas._reais_do_alvo(s, "Direito Processual
  Penal")` devolve só 3 questões de 2019; as 5 válidas de 2013 só aparecem
  pedindo "Direito Processo Penal". `radar gerar --materia "Direito
  Processual Penal"` (modo simulado) monta 3 pedidos, todos com base de 2019;
  o simulado por matéria idem. Lugares: `servico/geradas.py:55`,
  `servico/simulado.py:98`, `servico/espacada.py:168`,
  `servico/complementar.py:427`. Há duas regras de sinônimo
  (`taxonomia.yml` e `compilado.mesma_materia`, fuzzy 0,85).
- **BUG-5 (RI-8, migração):** os passos 1, 4 e 5 exportam os JSON versionados
  a partir do banco que está sendo migrado (`migracoes.py:58-60, 113, 129`).
  Migrar um banco antigo sobrescreve o registro mais novo: na pasta isolada, o
  `questoes_geradas.json` de 779 questões virou o de 50, e o
  `caderno_erros.json` foi regravado. O caminho real: depois de `radar migrar
  --desfazer`, a mensagem diz que "o próximo comando do radar novo migra de
  novo" — e essa migração exporta o banco velho por cima do JSON. O dado
  sobrevive no git e na cópia "antes-de-desfazer", mas a perda no arquivo é
  silenciosa (o mesmo mecanismo da decisão 50, agora fora dos testes).
- **Menor:** as colunas novas entram também pelo `ADD COLUMN` automático do
  `db.py` (6 colunas criadas antes dos passos numerados, com o recado "Rode
  `radar reclassificar`", que não tem relação), e não só por passo do
  `migracoes.py` (CL-12). A frase da conta não flexiona: "1 acertos + 1 erros".

**Suíte completa (rodada uma vez, em `C:\auditoria_copia`, 04/10 18:43 →
19:06):** `pytest -q -p no:cacheprovider --durations=10 -rs` → **2553 passed,
0 failed, 0 skipped, 38 warnings, 1381,86 s (23 min 01 s)**. O hash de
`data/` e `config/` da cópia é o mesmo antes e depois (nenhum teste grava nos
dados de verdade; o defeito da decisão 50 não voltou). Os 10 mais lentos são
`setup` de banco: 3 da varredura das telas (3,65 / 3,40 / 3,22 s), 2 do aceite
(2,82 / 2,36 s) e 5 do `test_sincronizar.py` com git de verdade (2,40 a
2,06 s). O único `pytest.skip` do projeto (`test_sincronizar.py:375`, "sem git
nesta máquina") não disparou.

- **BUG-6 (CLI, N8-2):** `radar gerar --modo revisao --materia "Direito
  Penal"` sem `--pedido` (a simulação, o modo padrão) termina em
  **Traceback** (`cli.py:915` → `geradas.preparar` → `escopo_da_revisao`
  levanta `EscopoInvalido` e ninguém trata). Com `--pedido` a mesma situação
  dá a mensagem certa ("Eu ainda não estudei nenhum conteúdo…"). O mesmo para
  Direito Constitucional.
- **BUG-7 (decisões 20 e 34, R-4-3):** o modo revisão da geração aceita como
  "estudado" o nó só **praticado**: `servico/geradas.py:141`
  (`if not (situacao.estudado or situacao.praticado)`), enquanto a decisão 20
  separa estudado de praticado, a 34 manda usar "o estudado da Etapa 4" e a
  docstring da própria função diz "os nós que eu JÁ ESTUDEI". No banco real,
  os 11 nós de Português do escopo da revisão vêm todos das respostas no radar
  de 28 e 29/09 (praticados), não de estudo.

### 7.4 Mais verificações executadas (E)

- **Regra única de evidência (RI-1, D-EVIDENCIA):** `evidencia.por_prova`
  comparado com a coluna `questoes.evidencia` nas 8.462 questões: **0
  divergências**; alvo = 2013 (70) + 2019 (100); `alvo.e_reforco` (que só a
  auditoria ainda usa, decisão 2-1) marca as 70 de 2016, todas
  `complementar`; `fora` = 907, todas IESES.
- **JSON versionado × banco:** exportado o banco da cópia para uma pasta
  isolada e comparado com `data/*.json`: idênticos `eventos`, `questoes_geradas`
  (775), `registro_estudo`, `estado_do_dia`, `caderno_erros`, `estudo_extra`,
  `notas_semana`, `classificacoes` (511), `conteudos` (426) e `assuntos`.
  Diferem: `simulados.json` (3 no JSON, 4 no banco: a rodada 5, criada hoje
  às 18:15, ainda não exportada — o backup das 23h30 exporta) e
  `concursos.json` (mesmas 2.893 URLs; 37 com `motivo_elegibilidade` e
  `atualizado_em` novos, da releitura de hoje, decisão 93, ainda não
  exportada; **8 deles com `escolaridade` mudada**, ex. "Fundamental" →
  "superior, fundamental", o que a decisão 93 não registra — ela diz só que
  "nenhum veredito mudou").
- **Nada do histórico perdido (RI-8, C23-16, N21):** todo registro dos JSON
  versionados no commit anterior à Etapa 2 (`2a70830`) existe hoje
  (concursos 2.863 → 2.893, eventos 75 → 105, geradas 50 → 775, provas 408,
  registro e estado 2 = 2). Banco: o simulado 1 (20 questões, nenhuma
  respondida) foi apagado pela limpeza de rodada vazia (decisão A8); as 22
  respostas dadas continuam.
- **Estados de amostra (D-ESTADOS):** `amostra.estado` com o config real:
  19/20 → insuficiente; 20/20 → consistente; 9/10 → insuficiente; 59% →
  precisa revisar; 60% → em aprendizado; 5/6 → insuficiente; 6/6 →
  consistente; exatamente na meta → consistente; dobro do mínimo na meta em
  1 dia → consistente, em 2 dias → bom com amostra; sem meta, 79/100 → bom,
  78/100 → em aprendizado; 0 respostas → insuficiente com porcentagem `None`.
- **Questão de IA nas telas (RI-5, D-IA-TELA):** rodadas de IA 2 e 5,
  `/geradas`, `/simulado`, a ficha e a questão aberta: 🟣 e a frase "Gerada
  por IA: não é questão oficial da FEPESE."; nenhuma rodada de IA escreve
  "Gabarito definitivo" (a 2 escreve "Resposta da IA").
- **Testes sem internet (CL-6):** 17 arquivos (coleta, FEPESE, IESES, provas,
  detalhes, avisos, elegibilidade, retificação, gerador, assuntos,
  sincronizar, web --rede, releitura, questões…) rodados com um plugin que
  derruba qualquer conexão fora de localhost: **402 passed, 0 tentativas de
  rede**.
- **Saúde do código (seção 11):** 79 módulos importados sem erro
  (`pkgutil.walk_packages`), `compileall` sem erro; nenhum `|safe`, `print`
  solto, TODO/FIXME ou SQL montado com entrada do usuário (o único `text()` é
  o DDL fixo do passo 3); todo `except Exception` registra no log e conta a
  falha.
- **7B (R-7B-1):** as 6 telas têm `class="ds"` e nenhuma variável do CSS
  antigo; os tokens `--selo-*` apontam para cores redefinidas no tema escuro.
- **Item 18 da §23:** **corrigido no código** — a média dos Macetes escreve
  "18.8/prova em 170 provas", "8.6/prova em 172 provas"… A varredura não achou
  porcentagem real sem a base por perto. Os documentos (CLAUDE.md,
  `auditoria_final.md`, tabela do `progresso.md`) continuam dizendo "18 de 19".
- **Regressões (seção 10):** `radar listar`, `previsao`, `simulados`,
  `padrao`, `repetidas`, `cobertura`, `status`, `conteudos`, `desempenho`,
  `conferir-dias` rodam sem traceback; `/calendario.ics` responde 200.

### 7.5 Testes de mutação (seção 9.3), em `C:\auditoria_mutacao`

Base sem mutação: 319 passed nos 12 arquivos usados. Cada mutação foi
aplicada, testada só com os arquivos da regra e desfeita (conferido por
`diff` contra o repositório).

| # | Regra quebrada | Detectada? | Teste que pegou |
|---|---|---|---|
| a | acerto de IA soma no acerto | **sim** | `test_metricas::test_o_28_09_fecha_a_conta` |
| b | prova complementar vira alvo | **sim** | `test_evidencia::test_a_regra_de_cada_prova` |
| c | importação aceita assunto fora do edital | **sim** | `test_classificacao::test_o_que_a_importacao_recusa[…assunto fora do edital]` |
| d | geração aceita questão fora do escopo (nó de fora) | **sim** | `test_geracao_por_conteudo::test_so_as_questoes_de_dentro_do_escopo_sao_gravadas` |
| e | mínimo da matéria 20 → 15 no config | **sim** | `test_amostra::test_os_minimos_vem_do_arquivo_real` |
| f | selo da IA 🟣 → 🟡 | **sim** | `test_origem::test_as_quatro_origens_tem_o_emoji_do_novo_md` |
| g | frase padrão alterada | **sim** | `test_origem::test_a_frase_padrao_com_o_texto_exato` |
| h | migração apaga uma linha | **sim** | `test_migracoes::test_migrar_mantem_as_contagens_e_cria_o_que_falta` |
| extra | anulada entra na conta do alvo | **sim** | `test_incidencia::test_anuladas_e_pendentes_fora_da_conta_mas_mostradas` (+3) |
| extra | pendente entra na conta do alvo | **sim** | o mesmo, e `test_com_a_amostra_o_padrao_aparece` |
| extra | anulada entra na linha complementar | **sim** (só com `test_complementar.py`) | `test_a_questao_anulada_fica_fora_da_linha_complementar` |
| extra | o dia passa a ser o de UTC | **sim** | `test_metricas::test_o_dia_e_o_mesmo_dentro_de_um_periodo_maior` |

**Cobertura aparente achada pelos bugs, e não pelas mutações:** os testes de
escopo da importação de geradas não cobrem nó inexistente dentro do escopo
(BUG-1) nem elemento irmão não pedido (BUG-2); nenhum teste cobre o caminho
de simulação do modo revisão sem nada estudado (BUG-6), o sinônimo de matéria
nos filtros da geração e do simulado (BUG-4), o efeito da migração sobre os
JSON versionados (BUG-5) nem contas feitas dentro de template.

### 7.6 Mais achados (para a Fase 3)

- **`radar padrao` mistura evidências (RI-1):** o comando antigo "O que a
  banca mais cobra: incidência por matéria" soma alvo, complementar (aceito e
  recusado) e IESES num número só ("Incidência por matéria (8.455
  questões)"), com "Peso" em %; "Direito Processo Penal" e "Direito
  Processual Penal" em linhas separadas; "sem materia" sem acento. Nada no
  `decisoes.md` o trata.
- **`radar previsao` no terminal** ainda escreve "Tijucas -> 2025" (e
  "JANELA"), sem o "Atrasado: era esperado em 2025" que a tela ganhou na 1B.
- **Contas em template (R-1C-2):** `desempenho.html:106` soma `com_consulta +
  sem_resultado`; `macetes.html:342` usa `| sum(attribute='total')`;
  `questao.html:71` faz `pedidas - entregues`; `ficha.html:186` conta por
  `| length`. Nenhum teste vigia isso.
- **README sem o `radar conferir-dias`** (0 menções).
- **§5, pergunta 4 (complementar.md):** responde "Sociologia Aplicada: 34
  indícios por termo em 30 provas", sem dizer que a classificação do
  complementar não achou nenhuma questão de Sociologia; a pergunta 1 conta
  ocorrências (1.506) e não questões distintas, ao contrário da incidência
  (decisão 3B-14).

### 7.7 Testes com o relógio simulado (R-1A-4, CL-7)

Os 63 arquivos de teste que usam data (`date.today`, `agora()`, `hoje`,
`date(20..)`, `timedelta`, cronograma) rodados na cópia com o `time-machine`
(plugin próprio fora do projeto, `tick=True`):

- **20/11/2026 15:00 (Florianópolis): 1 failed, 1.870 passed (26 min).**
- **BUG-8 (teste-bomba, Actions):** `tests/test_eventos.py:429`
  (`test_prazo_e_retificacao_saem_com_acento`) usa `FECHA = 31/10/2026`
  (linha 27) e espera "Prazo de inscrição: até 31/10/2026"; de **01/11/2026**
  em diante o sistema escreve, corretamente, "Prazo de inscrição, já
  encerrado: até 31/10/2026", e o teste falha (rodado em 30/10 → passa; 01/11
  e 20/11 → falha). Como o `coleta.yml` roda `pytest -q` antes de coletar, **a
  coleta diária e os avisos param em 01/11/2026** — a mesma falha da pendência
  A1, agora noutro teste (criado na 1B, 01/10).
- **Simulados x JSON:** as 50 respostas reais do `simulados.json` apontam,
  pelo par (prova_url, número), para a mesma questão que o banco liga pelo id
  (0 divergências). O vínculo, porém, é por número, e não pela chave da
  questão: depois de uma releitura que troca o número (a decisão 95 registra
  26 casos), refazer o banco a partir do JSON ligaria a resposta à questão
  errada. Hoje nenhuma resposta caiu nesses 26.
- **Composição das rodadas que medem (D-COMPOSICAO):** criadas na cópia as
  rodadas dos diagnósticos de 03/10 e do simulado de 07/11: 20, 20 e 50
  questões, todas FEPESE, só alvo e complementar aceito (0 de prova não
  aceita), 0 anuladas, 0 sem gabarito, 0 geradas, 0 enunciados repetidos; o
  segundo `criar_rodada` devolve a mesma rodada.

---

# RELATÓRIO FINAL (Fase 4)

## R1. Ambiente e linha de base

Ver a seção 1. Cópias: `C:\auditoria_copia` (suíte, relógio simulado,
leitura), `C:\auditoria_mutacao` (experimentos que gravam e mutações; o
código e a `config/` foram devolvidos iguais ao repositório depois das
mutações), `C:\auditoria_mutacao\migr` (banco antigo para a migração),
`C:\auditoria_mutacao\exp` (exportação para comparar com os JSON),
`C:\auditoria_ferramentas` (`time-machine` e os plugins `relogio_plugin.py` e
`sem_rede_plugin.py`, fora do projeto). A comparação final do repositório
contra a linha de base está na seção R15.

## R2. Resumo executivo

- **186 requisitos analisados** (bloco A: 123; bloco B: 63). A Fase 1 dizia
  188 por erro de soma meu (os critérios de etapa são 41, não 43); nenhum
  item da lista ficou de fora da matriz (conferido por script).
- **Por status:** ✅ 151 · ⚠️ 18 · 🐛 12 · ❌ 0 · 🔍 0 · ⏭️ 2 · 🔁 3. Bloco A:
  ✅ 99 · 🐛 10 · ⚠️ 10 · 🔁 3 · ⏭️ 1. Bloco B: ✅ 52 · ⚠️ 8 · 🐛 2 ·
  ⏭️ 1. Em 13 linhas há 🧑 (pronto, mas falta a sua conferência).
- **Por nível de evidência:** executei (E ou E+T) 176 · só teste (T) 8 · só
  leitura (L) 2. Nenhum ✅ ficou só com L.
- **Suíte:** 2.553 passed, 0 failed, 0 skipped, 23 min 01 s (Windows).
- **Defeitos confirmados por execução: 8** (BUG-1 a BUG-8), além de 12
  achados menores.
- **Principais riscos:** a coleta diária para em 01/11/2026 por um teste
  preso à data (BUG-8); a importação de geradas aceita questão fora do escopo
  pedido e nó inexistente (BUG-1 e BUG-2), quebrando a promessa central da §8;
  migrar um banco antigo sobrescreve os JSON versionados (BUG-5); nós
  duplicados na árvore separam o alvo do complementar do mesmo conceito
  (BUG-3); o sinônimo de matéria não vale nos filtros da geração e do
  simulado (BUG-4).

## R3. Matriz de requisitos

Evidência: E = executei; T = teste que passou nesta execução; L = só li.
"🧑" na observação = pronto, mas depende da sua conferência.

| ID | Fonte | Requisito | Status | Evidência | Nível | Problema | Observação |
|---|---|---|---|---|---|---|---|
| RI-1 | novo §RI | Alvo, complementar e desempenho nunca somados | 🐛 | incidência, ficha, prioridade e Onde estudar separam (7.1, 7.4) | E | `radar padrao` mostra "Incidência por matéria (8.455 questões)" somando alvo, complementar, recusadas e IESES (7.6) | o núcleo novo está certo; o comando antigo não foi revisto |
| RI-2 | novo §RI | Histórico nunca vira previsão | ✅ | varredura de 61 telas sem "vai cair/certamente/sempre cobra"; `test_varredura_das_telas` | E,T | — | — |
| RI-3 | novo §RI | Toda estatística com amostra | ✅ | varredura; Macetes "18.8/prova em 170 provas"; incidência "N questões · M provas" | E | — | — |
| RI-4 | novo §RI | Frase exata sem evidência | ✅ | `origem.FRASE_SEM_EVIDENCIA`, única cópia; ficha e §5 usam; mutação g detectada | E,T | — | — |
| RI-5 | novo §RI | Gerada nunca parece oficial | ✅ | rodadas 2 e 5, /geradas, ficha, questão aberta com 🟣 e a frase; mutação f detectada | E,T | — | — |
| RI-6 | novo §RI | ANKI desativado, não removido | ✅ | 36 faixas e 30 `baralho`; liga e desliga na cópia | E | — | — |
| RI-7 | novo §RI | Manhã com questões | ✅ | 26 dias úteis com 14 questões de manhã | E | — | — |
| RI-8 | novo §RI | Nenhum dado perdido; migrar preserva | 🐛 | contagens e JSON antigos preservados (7.4); migração v0→v5 sem perda | E | BUG-5: migrar banco antigo sobrescreve os JSON versionados | o dado ainda está no git e na cópia "antes-de-desfazer" |
| RI-9 | novo §RI | Não inventar vínculo nem classificação | 🐛 | importação de classificação recusa os 7 casos (7.1) | E | BUG-1: gerada gravada num nó que não existe | — |
| RI-10 | novo §RI | Mesmos números em todas as telas | ✅ | 28/09, 29/09 e semana 1 iguais em metricas, Hoje, `radar hoje`, Semanas e Matérias | E | — | — |
| C23-1 | §23 | O que ler | ✅ | ficha real do Art. 5º; `test_aceite` | E,T | — | 🧑 61 fichas por conferir |
| C23-2 | §23 | Onde ler | ✅ | fonte 🟢 CF com link | E,T | — | 🧑 |
| C23-3 | §23 | Como procurar | ✅ | 3 buscas | E,T | — | 🧑 |
| C23-4 | §23 | O que entender | ✅ | 8 itens | E,T | — | 🧑 |
| C23-5 | §23 | O que memorizar | ✅ | 5 itens | E,T | — | 🧑 |
| C23-6 | §23 | Pegadinhas | ✅ | 3 do acervo com a questão e 4 escritas 🟣 | E,T | — | 🧑 |
| C23-7 | §23 | Como a FEPESE cobrou | ✅ | alvo "1 questão · 1 prova" e complementar "2 · 2" em linhas separadas | E,T | o BUG-3 reduz o complementar de alguns temas | — |
| C23-8 | §23 | Questões reais relacionadas | ✅ | 2013-q31, 2024-q24, 2024-q26 com nó e gabarito | E,T | — | — |
| C23-9 | §23 | Quantas fazer | ✅ | 3 faixas do plano e "comece pelas 3 reais" | E,T | — | — |
| C23-10 | §23 | Quais geradas | ✅ | 18 geradas e um `radar gerar` por nó | E,T | — | — |
| C23-11 | §23 | Erros a revisar | ✅ | "0 no radar · 0 no caderno (nunca somadas)" | E,T | — | — |
| C23-12 | §23 | Por que hoje | ✅ | 7 fatores com número e origem; conta refeita à mão (0,407) | E,T | — | — |
| C23-13 | §23 | Gerar sem sair do escopo | 🐛 | literais recusados com sugestão; equivalentes reais rodam | E | BUG-1 e BUG-2: a importação aceita nó inexistente e elemento irmão não pedido | — |
| C23-14 | §23 | Números iguais nas telas | ✅ | ver RI-10 | E | — | — |
| C23-15 | §23 | Alvo não muda com prova complementar | ✅ | prova nova aceita: 8 linhas mudam, todas do complementar; fator do alvo igual nas 61 fichas | E | — | — |
| C23-16 | §23 | Nenhum dado antigo perdido | ✅ | JSON de antes da Etapa 2 contidos nos de hoje; contagens | E | risco do BUG-5 (RI-8) | — |
| C23-17 | §23 | ANKI desativado e reativável | ✅ | ver RI-6 | E | — | — |
| C23-18 | §23 | Nenhuma estatística sem amostra | ✅ | Macetes corrigido ("/prova em N provas"); varredura | E | os docs ainda dizem que falta (7.4) | — |
| C23-19 | §23 | Nenhuma gerada como oficial | ✅ | ver RI-5 | E,T | — | — |
| R-1A-1 | roteiro 1A | `pytest -q` verde | ✅ | 2553 passed | E | — | — |
| R-1A-2 | roteiro 1A | Actions verde | ✅ | no push do fim da auditoria, o `git fetch` trouxe `ea86683 coleta: 2026-10-04` (radar-bot, 04/10): o job só commita depois do `pytest -q` verde no Linux, com o código do `b811a15` | E | — | o BUG-8 o deixa vermelho a partir de 01/11; as decisões 91-95 só sobem agora |
| R-1A-3 | roteiro 1A | A1 fora das pendências | ✅ | `pendencias.md`, seção A | E | — | — |
| R-1A-4 | roteiro 1A / CLAUDE | Testes sem depender da data | 🐛 | relógio simulado em 20/11/2026: 1 falha | E | BUG-8 (`test_eventos.py:429`) | ver 7.7 |
| R-1B-1 | roteiro 1B | Eventos em frases | ✅ | varredura sem "inscricoes_abertas" nem "->" nas telas; `test_eventos` | E,T | — | — |
| R-1B-2 | roteiro 1B | Previsão "Atrasado…" e "há N anos" | ⚠️ | tela certa (`test_previsao`) | T,E | `radar previsao` no terminal: "Tijucas -> 2025", sem "Atrasado" | — |
| R-1B-3 | roteiro 1B | A2 e A3 fora das pendências | ✅ | `pendencias.md` | E | — | — |
| R-1C-1 | roteiro 1C | 28/09 fecha a conta | ✅ | tela e `radar hoje`: 31 = 13 + 8 + 10 | E | — | — |
| R-1C-2 | roteiro 1C | Ninguém fora do `metricas` soma | ⚠️ | serviços só agregam lançamentos do `metricas` | E | 4 contas em template; `conferencia.py:259` reconta os acertos de IA | — |
| R-1C-3 | roteiro 1C | Decisão registrada | ✅ | decisões 1C, 1 a 10 | E | — | — |
| R-1C-4 | roteiro 1C | Total = acertos + erros + sem resultado + IA | ✅ | `Numeros.questoes` é a soma; mutação a detectada | E,T | — | "1 acertos + 1 erros", sem plural |
| R-1D-1 | roteiro 1D | `conferir-dias` só lê | ✅ | rodado na cópia | E | — | — |
| R-1D-2 | roteiro 1D | Correções aplicadas, antes × depois | ✅ | 28/09 e 29/09 com 3h25 (Bônus de 0 fora) | E | — | — |
| R-6A-1 | roteiro 6A | Questões de manhã sem aumentar o dia | ✅ | 26 dias úteis: −20 min e +14 questões de manhã | E | — | — |
| R-6A-2 | roteiro 6A | Hoje e `radar hoje` com a manhã e o ANKI minimizado | ✅ | 05/10 e 07/10 | E | — | — |
| R-6A-3 | roteiro 6A | Religar volta igual | ✅ | saída idêntica depois de destrocar | E | — | — |
| R-6A-4 | roteiro 6A | README explica religar | ✅ | seção "Religar o Anki" | E | — | — |
| R-6A-5 | roteiro 6A | Dias antes de 02/10 iguais | ✅ | montados contra o YAML de `594362c^` | E | — | — |
| R-2-1 | roteiro 2 | Migração versionada com cópia e desfazer | ✅ | v0→v5; 2ª vez "nada"; desfazer com dump idêntico | E | ver BUG-5 | — |
| R-2-2 | roteiro 2 | 11 matérias e 85 assuntos do edital | ✅ | 13 matérias (11 + 2 fora) e 85 assuntos de origem edital | E | — | — |
| R-2-3 | roteiro 2 | 170 alvo, 2016 complementar, IESES fora | ✅ | 0 divergências entre a coluna e a regra | E | — | — |
| R-2-4 | roteiro 2 | Pendentes listados | ✅ | `radar conteudos`; "fora da conta: N pendentes" | E | — | — |
| R-3A-1 | roteiro 3A | `docs/auditoria.md` completo | ✅ | seções de contagem, gabarito, anuladas, suspeitas e classificação | E | — | — |
| R-3A-2 | roteiro 3A | 170 classificadas, 162 conferidas | ✅ | SQL: 146/9/15; 162 válidas conferidas | E | — | — |
| R-3A-3 | roteiro 3A | Mapa com amostra | ✅ | 11 linhas recalculadas à mão, iguais | E | — | — |
| R-3A-4 | roteiro 3A | Arts. 1º a 12 do CP | ✅ | 2019: q51 (art. 8º); 2013: q50, q51, q53, todas pendentes | E | 2013-q53 (art. 2º) pendente, embora o nó "Abolitio criminis" exista | — |
| R-3B-1 | roteiro 3B | `docs/complementar.md` coerente | ⚠️ | regerado na cópia | E | pergunta 4 ignora a classificação (34 "indícios" de Sociologia, 0 classificadas); pergunta 1 conta ocorrências | — |
| R-3B-2 | roteiro 3B | Validação mínima e hash único | ✅ | 3 COMCAP recusadas por PDF repetido, com o motivo | E,T | — | — |
| R-3B-3 | roteiro 3B | Complementar conferido por amostra | 🔁 | tela com filtro e amostra (200); lote do catálogo refeito (dec. 87) | E | — | 🧑 232 por conferir |
| R-3B-4 | roteiro 3B | Linhas separadas com amostra | ✅ | `radar incidencia` | E | — | — |
| R-4-1 | roteiro 4 | Nenhum mínimo fora do `amostra.yml` | ✅ | grep; mutação e detectada; exceção declarada (o 3 do caderno) | E,T | — | — |
| R-4-2 | roteiro 4 | Meu desempenho com estado e amostra | ✅ | `/analises/desempenho` 200 | E | o nível cru "· materia" aparece na tela | — |
| R-4-3 | roteiro 4 | "Estudado" do código = decisão 20 | 🐛 | `estudo.py` segue a decisão (T) | E,T | BUG-7: o modo revisão da geração usa estudado OU praticado | — |
| R-5-1 | roteiro 5 | Exemplos da §23 | ✅ | literais recusados, equivalentes rodam | E | — | decisão 66 |
| R-5-2 | roteiro 5 | Nenhuma questão fora do escopo entra | 🐛 | as 5 recusas esperadas funcionam | E | BUG-1 e BUG-2 | — |
| R-6B-1 | roteiro 6B | Cenário do Art. 5º pela ficha | ✅ | ver C23-1 a 12 | E | — | 🧑 |
| R-6B-2 | roteiro 6B | Conferência das 61 fichas | 🔁 | 0 de 61 conferidas | E | — | 🧑 sua (dec. 47) |
| R-6B-3 | roteiro 6B | Ciclo 2 | ⏭️ | decisão 52 | L | — | depois de 07/11 |
| R-7A-1 | roteiro 7A | Selos novos nos dois temas; docs | ✅ | tokens `--selo-*` → cores redefinidas no escuro; `test_design`; especificação sem selo antigo | E,T | — | não abri navegador |
| R-7B-1 | roteiro 7B | 6 telas no design system | ✅ | `class="ds"` e 0 variável antiga; `test_telas_no_design_system` | E,T | — | — |
| R-8-1 | roteiro 8 | §23 com evidência; pendências; Estado atual | ⚠️ | `auditoria_final.md` existe | E | item 18 corrigido e docs não atualizados | — |
| D-SELOS | dec. 53-55 | 4 selos + 📌, um lugar, tokens, metas próprias | ✅ | `origem.py`; 🟦 e 🟨 só nas metas | E,T | — | — |
| D-ORIGEM-NO-DADO | dec. 54 | Serviço grava a origem | ✅ | `test_origem` | T | — | — |
| D-FRASE | dec. 56 | Frase única; "Amostra insuficiente" | ✅ | grep; mutação g | E,T | — | — |
| D-IA-TELA | dec. 57 | 🟣 + frase; "Resposta da IA" | ✅ | ver RI-5 | E | — | — |
| D-AMOSTRA | dec. 6, 19, 83 | 20/10/6, 60%, 79, 20, 50, 3 | ✅ | `config/amostra.yml`; `amostra.estado` | E | — | — |
| D-ESTADOS | dec. 6 | Os 5 estados e as bordas | ✅ | 15 casos de borda (7.4) | E | — | — |
| D-RECORTES | dec. 1C-4/5 | Recortes de nome fixo; respostas × questões | ✅ | 2 respostas e 1 questão (7.4) | E | — | — |
| D-REGISTRO | dec. 1C-7 | Registro não compete com o calculado | ✅ | `radar hoje`: "Como foi: Reduzida", sem número | E | — | — |
| D-INCONSISTENTE | dec. 1C-3 | Acerto > questões é acusado | ✅ | `test_metricas`, `test_conferencia_dos_dias` | T | — | — |
| D-FAIXA-0 | dec. 1D-1 | Faixa com 0 recusada | ✅ | `test_conferencia_dos_dias` | T | — | — |
| D-FUSO | dec. 1C, 51 | Dia de Florianópolis | ✅ | 01:30 UTC → dia anterior; mutação j | E,T | — | — |
| D-EVIDENCIA | dec. 2-1, 75 | Uma regra; as antigas delegam | ✅ | 0 divergências; `foco._provas_do_alvo` delega | E | — | `alvo.e_reforco` só na auditoria (decidido) |
| D-COMPL-ACEITO | dec. 3B-5, 75 | Só o aceito em estatística e treino | ✅ | composição sem prova não aceita; incidência pelo arquivo | E | — | — |
| D-COMPL-DISTINTA | dec. 3B-14 | Complementar em questão distinta | ✅ | "254 questões · 172 provas (1487 ocorrências)" | E | `complementar.md`, pergunta 1, em ocorrências | — |
| D-CAMINHO | dec. 2-2 | Vínculo pelo caminho, a nó existente | 🐛 | 775 geradas, 2 erros e as fichas: 0 nó inexistente | E | BUG-1 deixa entrar nó inexistente | — |
| D-TAXONOMIA | dec. 2-3 | Tipo novo sem migração | ✅ | 7.1 | E | — | — |
| D-CHAVE | dec. 3A-1, 77, 90 | Tudo pela chave | ⚠️ | classificação e base da gerada pela chave; 0 órfãs | E | `simulados.json` liga a resposta por (prova_url, número) | sem dano hoje (0 de 50) |
| D-IMPORT-CLASSIF | dec. 3A-2 | Recusas da importação | ✅ | 7 recusas reais | E | — | — |
| D-INCID | dec. 3A-7 | Só alvo; anuladas e pendentes à parte; denominador | ✅ | recálculo à mão; mutações i2 e i3 | E,T | — | — |
| D-PADROES | dec. 3A-8, 78 | Padrões com amostra e origem | ✅ | ficha: "padrão identificado no acervo analisado… só das provas com gabarito definitivo" | E,T | — | — |
| D-ESTUDADO | dec. 20, F14 | Estudado × praticado | ✅ | `test_estudo` | T | ver R-4-3 | — |
| D-DIVISAO | dec. 7, 21 | "radar X% em N · anotado Y% em M" | ✅ | Meu desempenho; `test_desempenho` | E,T | — | — |
| D-REVISAO | dec. 23, 79, 82, 85 | Gatilhos e 1-7-30 | ✅ | `test_estudo` | T | duas filas na tela (N1-3) | — |
| D-REFAZER | dec. 24 | Duas listas nunca somadas | ✅ | ficha "nunca somadas" | E | — | — |
| D-ESCOPO | dec. 31-37 | Escopo fechado, sugestões, não alarga | 🐛 | sugestões e recusa (7.1) | E | BUG-2; BUG-6 (traceback na simulação) | — |
| D-GERADA-CAMPOS | dec. 35-39, 77, 89 | Campos da gerada | ✅ | id 776 com nó, artigo, modo, base, evidência e modelo; 236 com chave; 7 rejeitadas | E | — | — |
| D-FICHA | dec. 41-43, 47 | Uma estrutura; tema; nós; importação | ✅ | `FichaDeEstudo`, 16 campos; 61 de 65 temas | E,T | — | — |
| D-PRIORIDADE | dec. 44, 63 | Fórmula no YAML; peso 0 | ✅ | 7.4 | E | — | — |
| D-MIGRACAO | dec. 2-7, 80 | Passos, desfazer, uma vez por conexão | ⚠️ | v0→v5 e desfazer certos | E | BUG-5; ADD COLUMN fora dos passos | — |
| D-COMPOSICAO | dec. 67, 69 | Rodada que mede | ✅ | 7.7 | E | — | — |
| D-SABADO | dec. 70 | Sábado no `sabado.py` | ✅ | `test_sabado` | T | — | — |
| D-ONDE-ARVORE | dec. 71, 74, 81 | Faixa diz onde está; pela árvore | ✅ | `test_onde_na_arvore`; telas | T,E | — | — |
| D-ASSOCIADOS | dec. 86, 94 | Associado nunca conta | ✅ | recálculo à mão só com a principal bate | E | — | 🧑 109 por conferir |
| D-JS | dec. 30 | Só 2 JS, só na Hoje | 🔁 | varredura: scripts só na Hoje | E | — | substitui "único JS = cronômetro" |
| D-COR | dec. 88 | `?cor=` | ✅ | `/macetes?cor=claro` e `/hoje?cor=escuro` 200 | E | — | — |
| D-LEIS | dec. 65, 84 | Leis alteradas por conferir, com 🟣 | ✅ | `test_leis` | T | — | 🧑 24 itens |
| CL-1 | CLAUDE | Coletores isolados, `COLETORES` | ✅ | 3 classes `Coletor`; lista em `servico/coleta.py:31` | E | — | — |
| CL-2 | CLAUDE | Só `collectors/` sabe a fonte | ⚠️ | `provas.py` e `provas_ieses.py` sabem ler os hotsites | L | — | anterior à evolução |
| CL-3 | CLAUDE | robots, atraso e UA na base | ✅ | `collectors/base.py:110-180`; `Buscador` herda; testes | E,T | — | — |
| CL-4 | CLAUDE | Sem Qconcursos, login, paywall ou fonte proibida | ✅ | grep sem domínio proibido | E | — | — |
| CL-5 | CLAUDE | Link original guardado | ✅ | `concursos.url`, manifesto `url` | E | — | — |
| CL-6 | CLAUDE | Testes sem internet | ✅ | 402 testes com a rede bloqueada, 0 tentativas | E | — | — |
| CL-7 | CLAUDE | Teste sem data nem Windows | 🐛 | ver R-1A-4 | E | BUG-8 | — |
| CL-8 | CLAUDE | IA treina, não mede | ✅ | consumidores de `QuestaoGerada` revistos; mutação a | E,T | — | — |
| CL-9 | CLAUDE | IA com procedência | ✅ | 511 classificações, 775 geradas, 61 fichas, 40 macetes e 6 explicações com procedência | E | — | "Claude Code" no lugar do modelo (dec. 47) |
| CL-10 | CLAUDE | Dependência justificada | ✅ | `pyproject.toml` sem mudança desde 25/09 | E | — | — |
| CL-11 | CLAUDE | Um arquivo por assunto, sem duplicação | ⚠️ | — | E | duas regras de sinônimo; duas filas de revisão; recontagem da IA | — |
| CL-12 | CLAUDE | Estrutura só por passo de migração | ⚠️ | 5 passos | E | `db._adicionar_colunas_novas` ainda cria coluna sozinho | — |
| CL-13 | CLAUDE | Irrelevante não apagado; motivo gravado | ✅ | 2.893 com `motivo_relevancia`; 1.553 remotos no banco | E | — | — |
| CL-14 | CLAUDE | Alvo e `de_olho` no YAML | ✅ | `config/alvo.yml`; `evidencia.da_prova` lê dele | E | — | — |
| CL-15 | CLAUDE | Sem segredo no repositório nem no histórico | ✅ | `.env` ignorado; `.env.example` sem valor; `git log --all -G` sem token (só o exemplo "sk-ant-cole-a…") | E | — | — |
| CL-16 | CLAUDE | GET não grava; `--rede` documentado | ✅ | dump do banco igual antes e depois de 61 GET; README | E | — | `--rede` sem senha na rede local (documentado) |
| CL-17 | CLAUDE | Commit e push por etapa | ⚠️ | — | E | decisões 91 a 95 sem commit | você pediu o commit no fim |
| N1-1 | §1 | Cadeia ligada | ✅ | a ficha usa incidência, prioridade, desempenho, geradas e fila | E | — | — |
| N1-2 | §1 | Ficha com dados reais | ✅ | ficha do Art. 5º | E | — | — |
| N1-3 | §1 | Sem estrutura paralela | ⚠️ | — | E | fila da home (6) × fila do Meu desempenho (12), regras diferentes | — |
| N2-1 | §2 | Campos extraídos do alvo | ✅ | 170: 5 alternativas, gabarito, matéria, número contínuo | E | — | — |
| N2-2 | §2 | Relatório de extração | ✅ | `docs/auditoria.md` | E | — | — |
| N2-3 | §2 | Pendentes à parte | ✅ | "fora da conta: N pendentes" | E | — | — |
| N3-1 | §3 | Por nível: questões, provas e anos | ✅ | `radar incidencia` | E | — | — |
| N3-2 | §3 | Recorrentes, uma vez, não apareceu; tipo | ✅ | rótulos e coluna Tipo | E | — | — |
| N3-3 | §3 | Anuladas e pendentes documentadas | ✅ | linha "fora da conta" | E | — | — |
| N4-1 | §4 | Evidência gravada em tudo | ✅ | coluna nas 8.462 | E | — | — |
| N4-2 | §4 | Exibição separada | ✅ | linha dupla | E | — | — |
| N4-3 | §4 | Teste do alvo intacto | ✅ | `test_complementar`, `test_aceite` e o experimento | E,T | — | — |
| N5-1 | §5 | Metadados por prova | ✅ | manifesto + `acervo_complementar.json` + questões, pela URL | E | — | espalhados em 3 lugares |
| N5-2 | §5 | Hash duplicado recusado | ✅ | 3 COMCAP | E,T | — | — |
| N5-3 | §5 | 6 perguntas por consulta | ⚠️ | relatório regerado | E | a pergunta 4 ignora a classificação | — |
| N6-1 | §6 | 4 níveis, os de baixo opcionais | ✅ | árvore | E | — | — |
| N6-2 | §6 | Mesma hierarquia em tudo | ⚠️ | — | E | BUG-4 (matéria pelo nome cru) | — |
| N6-3 | §6 | Integridade da árvore | ⚠️ | 0 órfão, 0 nível errado | E | BUG-3: conceitos duplicados | — |
| N7-1 | §7 | Consulta por matéria continua e diz "simulado" | ✅ | `radar gerar --materia` | E | — | — |
| N7-2 | §7 | Elemento não jurídico | 🐛 | `--elemento` aceito | E | BUG-2 (irmão aceito) | — |
| N7-3 | §7 | Filtro na tela | ✅ | `/geradas` 200; `test_geracao_por_conteudo` | E,T | — | — |
| N8-1 | §8 | Três modos | ✅ | treino, revisão e simulado | E | — | — |
| N8-2 | §8 | Revisão só do estudado; para sem nada | 🐛 | com `--pedido` para certo | E | BUG-6 (traceback) e BUG-7 (praticado) | — |
| N8-3 | §8 | Simulado pelo peso do edital | ⚠️ | decisão 68 | E | BUG-4 (2013 fora) | — |
| N9-1 | §9 | Gerada → real → prova → ano → gabarito → fonte | ✅ | 236 com `origem_chave`; `test_gerador` | E,T | — | 3 antigas sem base, marcadas |
| N9-2 | §9 | Sem real: marcado | ✅ | `evidencia_da_base: nenhuma`; recusa sem a marca | E | — | — |
| N9-3 | §9 | Base alvo ou complementar | ✅ | campo gravado | E | — | — |
| N11-1 | §11 | Estrutura única, 16 campos | ✅ | `fichas.FichaDeEstudo` | E | — | — |
| N11-2 | §11 | Todos os conteúdos do cronograma | ⚠️ | 61 de 65 temas | E | 4 temas de 28/09 a 01/10 sem ficha | — |
| N11-3 | §11 | Campo sem dado com a frase | ✅ | ficha | E | — | — |
| N12-1 | §12 | Começo, meio e fim | ✅ | 5 fichas lidas (Penal, DH, LEP, Português, RL) | E | — | 🧑 |
| N12-2 | §12 | Nenhuma ficha genérica | ✅ | nenhuma "estude X" | E | — | 🧑 |
| N12-3 | §12 | 8 fichas executáveis | ⏭️ | — | E | Proc. Penal, Sociologia e Leg. Estadual não têm ficha porque não estão no Ciclo 1 | Ciclo 2 |
| N13-1 | §13 | Tipos de padrão | ✅ | comando, gabarito, termos, tipo, pegadinha | E,T | — | — |
| N13-2 | §13 | "Padrão identificado no acervo analisado" | ✅ | ficha e incidência | E | — | — |
| N13-3 | §13 | N questões · M provas · origem | ✅ | idem | E | — | — |
| N14-1 | §14 | Taxonomia flexível | ✅ | ver D-TAXONOMIA | E | — | — |
| N14-2 | §14 | Os 10 objetivos | ✅ | associados, sem amostra, desempenho | E,T | — | — |
| N14-3 | §14 | Separados por elemento | ✅ | incidência por elemento | E | — | — |
| N15-1 | §15 | Fatores | ✅ | 7 fatores na ficha | E | — | — |
| N15-2 | §15 | "Por que agora" | ✅ | ficha | E | — | — |
| N15-3 | §15 | Documentada e ajustável | ✅ | peso mudado na cópia muda a ordem | E | — | — |
| N16-1 | §16 | Sem "fraco" com 1 ou 2 respostas | ✅ | estados | E | — | — |
| N16-2 | §16 | Limites com o motivo | ✅ | docstring do `amostra.py` e config | E | — | — |
| N16-3 | §16 | Insuficiente fora de ordem e projeção | ✅ | `onde_estudar.py:277`, `foco.py:789` | E,T | — | — |
| N17-1 | §17 | Mesmo número nas telas | ✅ | ver RI-10 | E | — | — |
| N17-2 | §17 | Gráficos na mesma fonte | ✅ | Semanas e Matérias somam a mesma lista; `test_metricas` | E,T | — | — |
| N17-3 | §17 | Estados e regra documentados | ✅ | decisões 1C | E | — | — |
| N18-1 | §18 | ANKI não obrigatório | ✅ | faixa desligada fora do total | E | — | — |
| N18-2 | §18 | Distribuição aprovada; dia sustentável | ✅ | −20 min por dia útil | E | — | — |
| N18-3 | §18 | Como reativar | ✅ | README | E | — | — |
| N19-1 | §19 | Estudado, revisar, refazer, última revisão | ✅ | Meu desempenho | E | — | — |
| N19-2 | §19 | Taxa e evolução por assunto | ✅ | `test_estudo` (evolução = Semanas) | T | — | — |
| N19-3 | §19 | Alimenta revisão e `quando_revisar` | ⚠️ | ficha certa | E | BUG-7 no modo revisão | — |
| N20-1 | §20 | Fonte oficial priorizada | ✅ | ficha | E | — | — |
| N20-2 | §20 | Padrão = análise do acervo | ✅ | ficha e incidência | E | — | — |
| N20-3 | §20 | Conteúdo de IA com 🟣 e procedência | ✅ | ver CL-9 e RI-5 | E | — | — |
| N21-1 | §21 | Cópia antes | ✅ | migração e `conferir-dias` | E | — | — |
| N21-2 | §21 | Nada recalculado em silêncio | ⚠️ | — | E | o BUG-5 regrava JSON | — |
| N21-3 | §21 | Antes × depois e desfazer | ✅ | 7.4 | E | — | — |
| N22-1 | §22 | Testes por etapa | ✅ | `progresso.md` e git log | E | — | — |
| N22-2 | §22 | Commits sem misturar etapas | ✅ | commits "Etapa X (n/m)" | E | — | — |
| N22-3 | §22 | Registro por etapa | ✅ | `progresso.md` | E | — | — |

## R4. Conferência de entregáveis por etapa (atualizada)

A tabela da seção 3 continua válida: todo arquivo prometido existe, e cada
"não tocado" tem decisão registrada. As duas dúvidas abertas na Fase 1 foram
fechadas: (1) geradas, cartões e auditoria passam pela regra única (cartões e
geradas por `foco._provas_do_alvo`, que delega a `evidencia.provas`; a
auditoria usa `alvo.e_reforco` para o 2016, como a decisão 2-1 manda); (2) o
JSON das geradas leva os campos novos (exportado do banco = versionado,
idêntico, 775). Os números do `progresso.md` conferem com o banco; a única
afirmação desatualizada é "18 de 19" (o item 18 foi corrigido no código).

## R5. Problemas críticos

1. **BUG-5 — perda silenciosa no registro versionado (integridade).**
   Migrar um banco antigo exporta-o por cima dos JSON (`migracoes.py:58-60,
   113, 129`). Na pasta isolada, `questoes_geradas.json` passou de 779 para 50
   questões. O caminho real existe: `radar migrar --desfazer` + qualquer
   comando depois.
2. **BUG-1 e BUG-2 — a trava da §8 deixa passar o que devia recusar
   (geração).** A importação aceita questão num nó que não existe e num
   elemento irmão não pedido. A promessa "nenhuma questão fora do escopo
   informado" (§8, C23-13) não vale para o elemento.
3. **BUG-8 — a coleta diária para em 01/11/2026 (confiabilidade).** Um teste
   preso a 31/10/2026 falha a partir de 01/11, e o Actions roda os testes
   antes de coletar.
4. **BUG-3 — o mesmo conceito em nós diferentes (estatística).** No nó do
   alvo, a linha complementar sai "—" para conteúdos que o complementar tem, e
   a ficha e a prioridade subestimam o complementar desses temas.
5. **`radar padrao` soma todas as evidências (RI-1).** Comando antigo, sem
   aviso de que mistura alvo, complementar, provas recusadas e outra banca.

## R6. Requisitos não implementados ou parcialmente implementados

Nenhum requisito ficou ❌. Os ⚠️ (o que existe / o que falta):

- **R-1B-2** — tela da Previsão certa / o terminal ainda escreve "-> 2025".
- **R-1C-2** — serviços leem do `metricas` / 4 contas em template e uma
  recontagem em `conferencia.py:259`.
- **R-3B-1, N5-3** — relatório gerado e as 6 respostas / pergunta 4 sem o
  resultado da classificação; pergunta 1 em ocorrências.
- **R-8-1** — auditoria final escrita / não registra que o item 18 foi
  corrigido.
- **D-CHAVE** — chave na classificação e na base da gerada / `simulados.json`
  ainda liga resposta por (prova_url, número).
- **D-MIGRACAO, CL-12, N21-2** — passos, cópia e desfazer / BUG-5 e o ADD
  COLUMN automático do `db.py`.
- **CL-2** — coletores isolados / `provas.py` e `provas_ieses.py` sabem ler os
  hotsites (anterior à evolução).
- **CL-11, N1-3** — um arquivo por assunto / duas regras de sinônimo, duas
  filas de revisão com números diferentes na tela (6 na home, 12 no Meu
  desempenho).
- **CL-17** — etapas commitadas / decisões 91 a 95 sem commit (o commit vem
  no fim desta auditoria, como você pediu).
- **N6-2, N8-3** — a hierarquia é usada / a matéria pelo nome cru deixa 2013
  de fora (BUG-4).
- **N6-3** — árvore sem órfão nem nível errado / conceitos duplicados (BUG-3).
- **N11-2** — 61 de 65 temas com ficha / 4 temas de 28/09 a 01/10 sem ficha.
- **N19-3** — ficha usa a fila de revisão / o modo revisão da geração usa
  "praticado" (BUG-7).

## R7. Bugs encontrados (como achei e como reproduzir)

Todos reproduzidos na `C:\auditoria_mutacao`, com o código do repositório.

| Bug | Onde | Como achei | Como reproduzir | Requisito |
|---|---|---|---|---|
| BUG-1 | `servico/manual.py:977` (`_fora_do_escopo` confere só o prefixo) | leitura, depois importação fabricada | `radar gerar --pedido --materia "Lei de Execução Penal" --assunto "Lei de Execução Penal (Lei nº 7.210 de 11 de julho de 1984)" --subassunto "Assistência ao preso e ao egresso" --elemento "LEP, art. 26" --quantas 10`; responder com `"conteudo": "<escopo> > LEP, art. 26 > No inventado pela IA"` e `"artigo": "LEP, art. 26"`; `radar gerar --importar` → "gravado" (id 777) | RI-9, C23-13, D-CAMINHO |
| BUG-2 | `servico/manual.py:977` e `:1004-1007` | idem | mesmo pedido, `"conteudo": "<escopo> > LEP, art. 24"` com artigo "LEP, art. 26" → gravado (id 778); pedido do DH com `--elemento "Protocolo de San Salvador"` e resposta no "Pacto de San José da Costa Rica" → gravado | C23-13, R-5-2, N7-2 |
| BUG-3 | dados (`data/conteudos.json`, `data/classificacoes.json`) e a importação (`servico/classificacoes.py`, cria nó sem procurar parecido) | script de nomes parecidos (difflib ≥ 0,8) e contagem por nó | ver 7.2: p. ex. "Direitos Humanos > Teoria geral… > Características dos direitos humanos" (alvo 2) × "… > Conceito, terminologia… > Características dos direitos humanos" (complementar 2) | N6-3, C23-7, §4 |
| BUG-4 | `servico/geradas.py:55`, `servico/simulado.py:98`, `servico/espacada.py:168`, `servico/complementar.py:427` | grep de filtro pela coluna crua + execução | `geradas._reais_do_alvo(s, "Direito Processual Penal")` → só 2019 (3); `radar gerar --materia "Direito Processual Penal"` → 3 pedidos, todos com base de 2019 | N6-2, N8-3 |
| BUG-5 | `migracoes.py:58-60, 113, 129` | migração de um banco v0 numa pasta com os JSON de hoje | copiar `data/copias/migracao-v0-para-v1-…/radar.db` para uma pasta com os JSON atuais e rodar `radar migrar` → `questoes_geradas.json` 779 → 50; `caderno_erros.json` regravado | RI-8, N21-2 |
| BUG-6 | `cli.py:915` (simulação sem tratar `EscopoInvalido`) | execução do modo revisão | `radar gerar --modo revisao --materia "Direito Penal" --quantas 5` → Traceback | N8-2, D-ESCOPO |
| BUG-7 | `servico/geradas.py:141` | leitura + execução | `geradas.preparar("Língua Portuguesa", 5, modo="revisao")` → escopo com 11 nós que só têm resposta no radar (praticados) | R-4-3, N8-2, N19-3 |
| BUG-8 | `tests/test_eventos.py:27` e `:429` | relógio simulado | `RELOGIO=2026-11-01T12:00:00-03:00 pytest -p relogio_plugin tests/test_eventos.py::test_prazo_e_retificacao_saem_com_acento` → falha | R-1A-4, CL-7 |

Achados menores (não são defeito de regra, mas estão errados): "sem materia
(30)" no `/simulado` e o nível cru "· materia" no Meu desempenho; "1 acertos
+ 1 erros" sem plural; `radar previsao` com "->"; 2013-q53 (art. 2º, abolitio
criminis) pendente embora o nó exista; anulada respondida conta no acerto do
dia (decisão 1D-5) e não no desempenho por conteúdo; os cabeçalhos do
`config/regioes.yml` ("ainda não é lido por código nenhum") e do
`config/amostra.yml` ("lido por incidencia.py") contradizem o código; 8
concursos com `escolaridade` mudada na releitura de hoje, sem registro na
decisão 93.

## R8. Testes ausentes, insuficientes ou cobertura aparente

- **Mutações (7.5):** as 8 regras críticas pedidas foram **detectadas**, e
  também 4 extras (anulada e pendente no alvo, anulada no complementar, fuso).
  A mutação "anulada na linha complementar" só é pega pelo
  `test_complementar.py`, não pelo `test_incidencia.py` (cobertura em um
  arquivo só).
- **Cobertura aparente achada pelos bugs:** o escopo da importação de geradas
  (só testa nó de fora do prefixo, não nó inexistente nem elemento irmão);
  o modo revisão na simulação; o sinônimo de matéria nos filtros; a migração
  sobre os JSON versionados; contas dentro de template; um teste que depende
  da data (BUG-8).
- **Lacunas por área pedida:** parser de caderno, alternativas, gabarito,
  anuladas e duplicidade têm testes (`test_questoes`, `test_releitura`,
  `test_texto_base`, `test_marca_minuscula`, `test_gabarito`,
  `test_complementar` para o hash); estatística, classificação, filtros,
  geração, separação real × gerada, incidência, cronograma, desempenho e
  migração têm testes, com as lacunas acima; **falta teste de integridade dos
  dados reais da árvore** (nomes duplicados/parecidos no mesmo ramo ou em
  ramos da mesma matéria) e **teste de ponta a ponta de "refazer o banco a
  partir dos JSON"** com as respostas ligadas pela chave.
- **Testes enfraquecidos (9.2):** desde 25/09 foram removidos 22 testes em 12
  commits; todos ligados a uma decisão registrada (o "único JS", os seis selos
  antigos, o registro que guardava número, o `?tema=`), e o dos títulos dos
  sábados foi renomeado e ampliado. Não achei assert afrouxado sem decisão.
- **Total e tempo:** 2.553 testes, 23 min 01 s; os 10 mais lentos estão na
  seção 7 (Suíte completa). Nenhum `skip`/`xfail` disparou (o único
  `pytest.skip` exige máquina sem git).

## R9. Inconsistências de arquitetura (conceito × módulo)

| Conceito | Como cada parte identifica | Divergência |
|---|---|---|
| Matéria | 1º nome do caminho do nó (incidência, desempenho, ficha, prioridade, composição); coluna crua `QuestaoDeProva.materia` (simulado, geradas, espaçada, complementar, `metricas.acumulado_por`); `normalizar` sem acento (`--materia` do `desempenho` e da `incidencia`); `compilado.mesma_materia` difusa 0,85 (compilado, composição, sábado, Minhas matérias); `taxonomia.sinonimos_de_materia` (ligar texto antigo) | quatro regras para o mesmo nome; "Direito Processo Penal" só é unificado em parte (BUG-4) |
| Assunto | nó de nível assunto (incidência, Onde estudar, espaçada, composição); `QuestaoGerada.assunto` = último nome do escopo (pode ser o elemento, "LEP, art. 26"); `Lancamento.assunto` = título da faixa; `ErroAnotado.assunto` digitado; `questoes.assunto` (catálogo antigo, vazio no Direito); ficha: texto da IA conferido contra a árvore | texto solto em 4 lugares (inventário pedido em 7.2.C) |
| Subassunto/elemento | caminho do nó; `QuestaoGerada.artigo` e `ficha.elemento` em texto livre | o elemento da gerada e da ficha não é nó |
| Prova | `prova_url` (evidência, acervo complementar, `simulados.json`); sha256 (manifesto, validação); código "ano-qN" (pedidos, único só no lote) | — |
| Evidência | coluna `questoes.evidencia` (fotografia) e `evidencia.por_prova` (na hora) | iguais hoje; a coluna só se refaz em migrar/importar/ler caderno |
| Questão real | id (respostas no banco; muda ao refazer), chave (classificação, base da gerada), impressão (geradas, macetes, `/macetes/{impressao}`), (prova_url, número) (`simulados.json`) | o JSON das respostas não usa a chave (D-CHAVE) |
| Nó | caminho de nomes em todo lugar | estável; mas o mesmo conceito tem caminhos diferentes (BUG-3) |
| Revisão | `servico/espacada.py` (home: assunto errado, 1-7-30) e `servico/estudo.py` (Meu desempenho: nó, 3 gatilhos) | duas filas, números diferentes na tela |

Módulos que existem e quase não alimentam nada: `assuntos.py` (classificador
pago, nunca usado desde 25/09), a coluna `questoes.assunto` e o
`data/assuntos.json` vazio (aceito só por compatibilidade).

## R10. Regressões

Nenhuma regressão de funcionamento: `radar listar`, `previsao`, `simulados`,
`padrao`, `repetidas`, `cobertura`, `status`, Plano B (`radar hoje
--plano-b 30`), calendário e `.ics`, favoritos, avisos (pelos testes, sem
enviar), simulado e relatório, macetes, auditoria, caderno de erros, Semanas,
Minhas matérias e cronômetro respondem (CLI sem traceback; telas 200) e a
suíte inteira passa. Mudaram por decisão registrada: o "único JS" (dec. 30),
o `?tema=` → `?cor=` (dec. 88), o registro do dia sem número (1C-7), o
"reforço" que somava no Onde estudar (dec. 63). Ficaram para trás na
evolução, sem decisão: o `radar padrao` (RI-1) e o `radar previsao` do
terminal (R-1B-2). Backup e automação: só li o código (`sincronizar` com
fetch + merge `--ff-only`, decisão 64); o log de 03/10 diz "RESULTADO: ok";
não executei.

## R11. Segurança e documentação

- **Segredos (CL-15):** nenhum token, chave ou senha em código, config, data,
  docs ou no histórico (`git log --all -G` para Telegram, `sk-ant-` e
  `api_key/token/senha/password`): só o exemplo "sk-ant-cole-a-sua-chave-aqui"
  do `COMO_LIGAR_A_IA.txt`. `.env` no `.gitignore`; `.env.example` só com
  `RADAR_USER_AGENT`, `RADAR_REQUEST_DELAY` e `RADAR_REQUEST_TIMEOUT`. O
  token do Telegram revogado (pendência D) não aparece no repositório.
- **Web:** nenhum GET grava (dump do banco igual antes e depois de 61 GET);
  `radar web --rede` expõe as telas e os POST na rede local sem senha —
  documentado no README; risco BAIXO para uso em casa, MÉDIO em rede de
  terceiros.
- **Documentação desatualizada:** "18 de 19" no CLAUDE.md, no
  `auditoria_final.md` e na tabela do `progresso.md` (o item 18 está
  corrigido); README sem o `radar conferir-dias`; `pendencias.md:27` cita
  "B.7 a B.10", já resolvidas e apagadas; cabeçalhos do `regioes.yml` e do
  `amostra.yml`; decisão 93 sem a mudança de `escolaridade`; o CLAUDE.md se
  diz "curto de propósito", mas o "Estado atual" tem 764 palavras num bloco
  só (não há teto escrito). Nenhum link quebrado entre os documentos; o
  `historico.md` tem seção para cada etapa e subetapa; a `especificacao.md`
  não tem mais os selos antigos.

## R12. Riscos

| Risco | Classe | Por quê |
|---|---|---|
| BUG-5 (migração sobrescreve JSON) | **CRÍTICO** | perda de dado no registro de onde o banco se refaz, sem aviso; regra inviolável 8 |
| BUG-1 (nó inexistente aceito) | **CRÍTICO** | vínculo inventado gravado, regra inviolável 9; o treino apontaria para um conteúdo que não existe |
| `radar padrao` somando evidências | **CRÍTICO** pela definição (regra 1 quebrada); impacto prático pequeno | é um comando de terminal antigo, mas mostra "incidência" como um número só |
| BUG-8 (teste-bomba de 01/11) | ALTO | para a coleta diária, os avisos e a exportação no GitHub — a funcionalidade central do radar |
| BUG-2 (elemento irmão aceito) | ALTO | o treino específico recebe questão de outro dispositivo, que é o que a §8 proíbe |
| BUG-3 (nós duplicados) | ALTO | engana o estudo: o complementar de um tema aparece zerado no nó do alvo |
| BUG-4 (sinônimo nos filtros) | ALTO | a geração e o simulado de Processual Penal ignoram a prova de 2013 inteira |
| BUG-7 (revisão com "praticado") | MÉDIO | modo revisão mais amplo que a decisão; não sai da matéria |
| BUG-6 (traceback) | MÉDIO | só na simulação; o `--pedido` trata |
| D-CHAVE (`simulados.json` por número) | MÉDIO | sem dano hoje; refazer o banco depois de uma releitura pode ligar resposta à questão errada |
| Duas filas de revisão | MÉDIO | números diferentes na tela para a mesma pergunta |
| Contas em template, recontagem da IA | MÉDIO | fragilidade da fonte única (hoje dão o mesmo número) |
| ADD COLUMN fora dos passos | MÉDIO | mudança de estrutura sem versão nem cópia |
| Docs desatualizados, acentos, plural, `previsao` no terminal | BAIXO | texto; não muda número |

## R13. O que NÃO consegui verificar, e o que depende de você

- **Actions (R-1A-2):** resolvido no push final — o `coleta: 2026-10-04` do
  radar-bot existe no GitHub (verde em 04/10). Falta ver o primeiro run com
  as decisões 91-95 (o de 05/10) e, principalmente, corrigir o BUG-8 antes
  de 01/11.
- **Telas no navegador, nos dois temas:** conferi tokens e HTML, não a
  aparência.
- **Se o texto escrito pela IA está certo** (fichas, macetes, explicações,
  leis alteradas, classificações do complementar): isso é a sua conferência
  (🧑: 61 fichas, 232 classificações, 109 associados, 24 itens de lei).
- **Backup das 23h30, Agendador e Telegram:** proibidos de rodar; li o código
  e o log.
- **Relógio simulado em 15/03/2027:** rodado; ver R15.

## R14. Plano de correção (não implementei nada)

Ordem: integridade → erros que afetam várias partes → crítico não feito →
bugs → arquitetura → testes → UX → secundário. Uma conversa por grupo.

| # | Grupo / conversa | IDs | Mudança (1-2 linhas) | Arquivos | Teste que prova | Tam. | Depende | Onde cabe | Tipo |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **Antes de 01/11** | R-1A-4, CL-7 | `FECHA` relativa a `agora()` (ou relógio congelado) no `test_eventos.py` | `tests/test_eventos.py` | rodar o arquivo com o relógio em 01/11/2026 e 15/03/2027 | P | — | pendência A nova | mecânico |
| 2 | Integridade da migração | RI-8, N21-2, D-MIGRACAO | o passo de migração não exporta por cima de JSON com mais linhas (ou só exporta no `sincronizar`), e avisa | `migracoes.py`, `acervo.py` | migrar um banco v0 numa pasta com o JSON de 775 geradas: o JSON continua com 775 | M | decisão sua (exportar ou não na migração) | etapa nova "integridade" | decisão |
| 3 | Integridade do registro | D-CHAVE | `simulados.json` passa a guardar a chave da questão (com o par atual como reserva) | `acervo.py`, `migracoes.py` (passo 6) | refazer o banco de um JSON depois de trocar números de questão: as respostas ficam nas mesmas questões | M | 2 | idem | decisão |
| 4 | Escopo da geração | RI-9, C23-13, R-5-2, D-ESCOPO, N7-2 | `_fora_do_escopo` usa `Escopo.dentro` com os elementos pedidos e exige nó que exista na árvore | `servico/manual.py` | respostas fabricadas: nó inexistente e elemento irmão recusados; artigo e não artigo | P | — | correção da Etapa 5 | mecânico |
| 5 | Modo revisão | N8-2, R-4-3, BUG-6, BUG-7 | tratar `EscopoInvalido` na simulação; decidir "estudado" × "praticado" e alinhar código, docstring e decisão 34 | `cli.py`, `servico/geradas.py`, `docs/decisoes.md` | simulação sem nada estudado mostra a frase; teste do conjunto de nós da revisão | P | decisão sua | correção da Etapa 5 | decisão |
| 6 | Árvore sem duplicados | N6-3, C23-7, BUG-3 | unificar os ~10 pares de nós (com a sua escolha do nome), levando as classificações; a importação procura nome parecido no mesmo ramo antes de criar | `servico/classificacoes.py`, dados, `migracoes.py` | teste de integridade: nenhum par de irmãos (ou mesma matéria) com similaridade ≥ 0,85; incidência do nó do alvo passa a mostrar o complementar | G | decisão sua, conferência | etapa nova "árvore" | decisão |
| 7 | Uma regra de matéria | N6-2, N8-3, CL-11, BUG-4 | um `nome_canonico(materia)` (taxonomia) usado em todo filtro por matéria; aposentar `mesma_materia` difusa onde a taxonomia resolve | `servico/geradas.py`, `simulado.py`, `espacada.py`, `complementar.py`, `compilado.py` | geração e simulado de Processual Penal trazem 2013 e 2019 | M | — | etapa nova "nomes" | mecânico |
| 8 | Comandos antigos | RI-1, R-1B-2 | `radar padrao` separa alvo/complementar/fora (ou diz "acervo inteiro, todas as bancas"); `radar previsao` usa as frases da tela | `cli.py`, `servico/__init__.py` | saída sem número misto; "Atrasado: era esperado em" no terminal | P | decisão sua sobre o `padrao` | correção | decisão |
| 9 | Fonte única de verdade | R-1C-2, CL-11, N1-3 | as 4 contas de template e a recontagem da IA para o serviço; decidir se a home mostra a fila do `estudo.py` | templates, `servico/conferencia.py`, `servico/inicio.py` | teste que proíbe `+`/`sum`/`length` de contagem nos templates | M | — | correção da 1C | mecânico + decisão (filas) |
| 10 | Estrutura do banco | CL-12 | o ADD COLUMN automático vira passo de migração (ou só avisa) | `db.py`, `migracoes.py` | coluna nova sem passo é recusada em teste | M | 2 | etapa "integridade" | decisão |
| 11 | Testes que faltam | R8 | integridade da árvore real; refazer o banco a partir dos JSON; relógio simulado no CI (ou uma data fixa futura) | `tests/` | os próprios | M | 1, 6 | junto dos grupos | mecânico |
| 12 | Texto e UX | K | "sem materia", "· materia", plural da conta, `complementar.md` perguntas 1 e 4, cabeçalhos de config | templates, `metricas.py`, `servico/complementar.py`, `config/` | varredura de acentos nas telas | P | — | correção | mecânico |
| 13 | Documentação | R-8-1, docs | item 18 "atende" (19 de 19, se você concordar), README com `conferir-dias`, `pendencias.md:27`, decisão 93 (escolaridade), "Estado atual" mais curto | docs | — | P | — | fim de etapa | mecânico |
| 14 | Fichas que faltam | N11-2 | as 4 de 28/09 a 01/10, se você quiser revisá-las | `data/fichas.json` | `servico.fichas.sem_ficha(desde=plano.inicio)` vazio | P | — | 6B | decisão |

## R15. Prova de que nada foi alterado, resposta final e checklist

**Comparação com a linha de base (04/10, 19:45, antes do commit):** HEAD
igual (`b811a15`); `git status --short --ignored` igual, com uma única linha a
mais: `?? docs/auditoria_independente.md`; os SHA-256 dos 20 `data/*.json`,
dos 49 arquivos modificados/novos de antes e dos 434 arquivos ignorados
(`.env`, `data/radar.db`, `data/provas/`, `data/copias/`, `data/logs/`…)
**iguais**. O banco real não mudou durante a auditoria. Depois disso, a seu
pedido, vieram o commit e o push (ver o fim desta seção).

**Relógio simulado em 15/03/2027:** 1 failed (o mesmo BUG-8), 1.870 passed,
19 min 07 s. Nenhum outro teste depende da data.

**Pergunta final — "Tudo o que foi solicitado foi implementado, está
estruturado como solicitado, integrado e funciona corretamente?"**

**PARCIALMENTE.** De 186 requisitos, 151 estão implementados e comprovados
(✅, 176 com execução), 18 parcialmente (⚠️), 12 com problema (🐛), 0 sem
implementação; 2 ainda não são desta etapa (Ciclo 2) e 3 mudaram por decisão
registrada (🔁). O núcleo funciona com o dado real: contagem igual em todas as
telas, incidência do alvo recalculada à mão igual, alvo intacto com prova
complementar nova, ANKI religável, 2.553 testes verdes, 8 de 8 mutações
críticas detectadas. Mas 8 defeitos confirmados quebram regras do pedido: a
trava de escopo da geração (§8, regra 9), a migração que sobrescreve o
registro (regra 8), a coleta que para em 01/11, nós duplicados na árvore e o
sinônimo de matéria fora dos filtros.

**Os 10 problemas mais graves, em ordem de risco:**

1. BUG-5 — migrar um banco antigo sobrescreve os JSON versionados (779 → 50
   geradas na cópia). CRÍTICO.
2. BUG-1 — a importação de gerada aceita nó que não existe na árvore. CRÍTICO.
3. `radar padrao` soma alvo, complementar, recusadas e IESES como
   "incidência". CRÍTICO pela regra 1, impacto pequeno.
4. BUG-8 — teste preso a 31/10/2026: a coleta diária para em 01/11/2026. ALTO.
5. BUG-2 — a importação aceita questão de elemento irmão não pedido (art. 24
   no pedido do art. 26; Pacto de San José no do Protocolo de San Salvador).
   ALTO.
6. BUG-3 — conceitos duplicados na árvore separam o alvo do complementar do
   mesmo conteúdo. ALTO.
7. BUG-4 — "Direito Processo Penal" (2013) fora da geração e do simulado de
   Processual Penal. ALTO.
8. BUG-7 — o modo revisão trata como "estudado" o que só foi praticado.
   MÉDIO.
9. `simulados.json` liga a resposta por (prova_url, número), e não pela
   chave. MÉDIO.
10. BUG-6 — traceback no `radar gerar --modo revisao` (simulação) sem nada
    estudado. MÉDIO.

**Checklist de encerramento:**

- [x] `git status --short --ignored` e hashes iguais aos do início (única
      diferença: este arquivo), conferido antes do commit;
- [x] nenhuma alteração fora deste arquivo durante a auditoria; commit e push
      só no fim, a seu pedido;
- [x] suíte completa rodada uma vez (2.553 passed, 23 min 01 s);
- [x] todo ✅ tem evidência E ou T;
- [x] o que não deu para verificar está dito, com o motivo (R13); o único 🔍
      (Actions) foi resolvido pelo `git fetch` do push final;
- [x] caminhos das cópias informados (R1);
- [x] resumo e resposta PARCIALMENTE entregues;
- [x] não corrigi nada no projeto.

**Commit e push (pedido seu, no fim):** `584b0bb` (as decisões 91 a 95, que
estavam só no disco — os mesmos 49 arquivos da linha de base) e `ad64f71`
(este relatório), postos em cima de `ea86683 coleta: 2026-10-04` do
radar-bot por `git rebase origin/main` (o robô só mexe em
`data/concursos.json` e `data/eventos.json`; nenhum conflito) e enviados
para `origin/main`. Este último ajuste (R-1A-2) vai num commit à parte.
