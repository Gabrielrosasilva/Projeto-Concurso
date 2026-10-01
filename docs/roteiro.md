# Roteiro — evolução do sistema de estudos

Plano das **Etapas 1 a 8** da seção 22 do pedido de evolução (`docs/novo.md`),
montado na Etapa 0 (análise da arquitetura, 01/10/2026). O andamento de cada
etapa é registrado em [docs/progresso.md](progresso.md).

Nomes de campos, tabelas e comandos daqui são **propostas**: seguem as
convenções do projeto (português, um arquivo por assunto no `servico/`) e podem
mudar na execução, desde que o comportamento pedido seja respeitado.

---

## Como usar este roteiro

- **O pedido é o `docs/novo.md`**: requisitos e regras invioláveis. Este roteiro
  diz **em que ordem** e **como** atendê-lo. Onde os dois divergirem, vale o que
  estiver registrado em `docs/decisoes.md` (é lá que fica a resolução de cada
  conflito).
- **Uma conversa por etapa (ou subetapa).** Toda conversa começa lendo, nesta
  ordem: `CLAUDE.md`, `docs/roteiro.md`, `docs/progresso.md`, `docs/novo.md`,
  `docs/decisoes.md`, `docs/pendencias.md`. Antes de mexer em qualquer coisa,
  confere se esses arquivos se contradizem e avisa.
- **Onde roda:** no Claude Code do VS Code, no PC. É lá que estão o banco real
  (`data/radar.db`) e o venv (`.venv\Scripts\python`, ou `radar.bat`). Teste
  usa sempre fixture em arquivo, nunca o banco real nem a internet.
- **Pontos de parada** (novo.md, "Como quero que você trabalhe"):
  1. ao fim de cada etapa, **PARAR** e mostrar: arquivos alterados, testes
     executados, resultado dos testes e se o critério de conclusão foi atendido;
  2. o que estiver marcado aqui como **"aprovar antes de aplicar"** (correção de
     dado gravado, rotina nova, lista de provas, migração) é mostrado e só é
     aplicado depois do "pode";
  3. se no meio de uma etapa aparecer algo que muda o plano (problema maior,
     dependência imprevista, estrutura existente que já resolve parte), **parar
     e avisar** antes de seguir;
  4. commits só da etapa em andamento, na `main`, com push. Nunca misturar
     etapas num commit.
- **Antes de mudar estrutura do banco ou dado gravado:** cópia de segurança,
  mostrar o que muda, e no fim a conferência "antes × depois".
- **Ao fechar a etapa:** atualizar `docs/historico.md` (o que foi feito),
  `docs/decisoes.md` (o que foi decidido e por quê), `docs/pendencias.md` (o
  que sobrou), o "Estado atual" do `CLAUDE.md` e o `docs/progresso.md`.
- **Etapa só é concluída quando atende ao objetivo**, conferido de verdade, e
  não porque existe código relacionado a ela (novo.md, seção 22).

---

## Decisões tomadas na Etapa 0 (01/10/2026)

Estas decisões ainda não estão no `docs/decisoes.md` (na Etapa 0 só este
arquivo e o `docs/progresso.md` podiam ser criados). **O primeiro commit da
Etapa 1 as registra lá.** (Registradas no `decisoes.md` na 1A, em 01/10/2026.)

1. **Branch:** sempre `main`, sem branch nem PR (CLAUDE.md). A
   `claude/busy-davinci-fgt1br` foi apagada: não tinha nada fora da `main`.
2. **Uma conversa por etapa**, com o estado no repositório (este roteiro, o
   `docs/progresso.md` e os docs).
3. **O dia 28/09 foi investigado** com os dados reais:

   | Origem | Questões | Acertos | Erros |
   |---|---|---|---|
   | Faixa anotada (Qconcursos): Direito Penal | 11 | 6 | 5 |
   | Faixa anotada (Qconcursos): Português | 10 | 7 | 3 |
   | Respondidas no radar: questões de IA | 10 | — | — |
   | **"Fiz hoje" mostrou** | **31** | **13** | **8** |

   Não houve contagem dupla, problema de fuso nem dado perdido. A linha não
   fecha porque as 10 de IA entram no volume e, pela regra, nunca em acerto, e
   a linha não diz isso. O registro do dia guardou "31 questões, 13 acertos",
   que se lê como 18 erros. E a faixa Bônus foi marcada como feita com
   0 questões: os 25 min dela estão dentro das 3h50.
4. **Números iguais:** uma fonte única de contagem, com **recortes de nome
   fixo**: *medido no radar*, *anotado* (faixas e estudo extra, que vêm do
   Qconcursos), *treino de IA* e *total*. Mesmo recorte e mesmo período dão o
   mesmo número em qualquer tela, e cada tela escreve o recorte que mostra.
5. **Selos:** passam a 🟢 fonte oficial · 🔵 estatística do acervo ·
   🟡 análise automática · 🟣 gerado por IA. Substitui a decisão dos seis selos
   em quatro cores (🟦🟩🟨🟥).
6. **Limites de amostra num lugar só**, valendo para todo o sistema:

   | Nível | Mínimo de respostas sem consulta |
   |---|---|
   | Matéria | 20 |
   | Assunto | 10 |
   | Subassunto ou elemento | 6 |

   | Estado | Regra |
   |---|---|
   | Amostra insuficiente | abaixo do mínimo; não entra em ordenação nem em projeção |
   | Precisa revisar | abaixo de 60% |
   | Em aprendizado | de 60% até abaixo da meta da matéria |
   | Desempenho consistente | na meta ou acima |
   | Bom desempenho com amostra suficiente | na meta ou acima, com pelo menos o dobro do mínimo, respondido em dois dias diferentes ou mais |

   A meta da matéria é a do `config/cronograma.yml` (ex.: 12 de 15 = 80%);
   matéria sem meta própria usa a da prova (79 de 100). Motivo dos mínimos:
   com 10 questões a margem de uma porcentagem ainda é de ~30 pontos; com 20,
   de ~22. Substitui os mínimos de hoje (5 e 3 no Onde estudar, 20 em Minhas
   matérias).
7. **Desempenho por conteúdo** usa o radar e o Qconcursos: no Qconcursos eu
   anoto "fiz N, acertei M" por matéria e subassunto. Sempre com a divisão
   "radar X% em N · anotado Y% em M". Questão de IA nunca entra. A partir da
   Etapa 4, o Meu foco e o Onde estudar passam a usar esse desempenho (revisa a
   decisão E2, que os deixava só no radar); até lá, ficam no recorte *medido no
   radar*, escrito na tela.
8. **As 162 questões válidas do alvo** são classificadas pelo Claude Code, no
   fluxo pedido/importar, com procedência, e conferidas por mim.
9. **Fichas de tarefa (§11):** o texto escrito por IA é aceito, marcado 🟣,
   com procedência, e conferível.
10. **2019:** o caderno masculino é igual ao feminino (AP), que é o auditado.
11. **Provas:** o concurso-alvo tem só as provas de 2013 e 2019, já no banco.
    Não há prova nova para importar. O acervo complementar é o que já está no
    banco (Socioeducativo 2016 e as provas FEPESE de prefeituras), e o
    levantamento da §5 vira consulta a esse acervo.
12. **ANKI:** desligado por uma chave no `config/cronograma.yml`, sem apagar
    nada. Vale já no Ciclo 1.
13. **Rotina com questões também de manhã:** vale já no Ciclo 1, o quanto
    antes, com a proposta aprovada antes de mexer no cronograma.
14. **Pendências** do `docs/pendencias.md`: ver a tabela "Pendências × etapas".

Correção de documentação que entra no mesmo primeiro commit: o "Estado atual"
do CLAUDE.md diz "40 geradas, todas `do_zero`", mas o arquivo tem **50**:
20 `variacao` de LEP (com questão de origem), 20 `do_zero` de Direito Penal com
a `materia` gravada como "Aplicação da lei penal (arts. 1º a 12)" (um título de
faixa) e sem assunto, e 10 `do_zero` de Português. O conserto do dado é da
Etapa 2.

---

## Ordem de execução

| # | Etapa | Entrega | Depende de |
|---|---|---|---|
| 1 | 1A | GitHub Actions verde (pendência A1) | — |
| 2 | 1B | Texto de máquina e Previsão (pendências A2 e A3) | — |
| 3 | 1C | Fonte única das métricas; "Fiz hoje" fecha a conta | 1A |
| 4 | 1D | Conferência dos dados já gravados | 1C |
| 5 | 6A | Rotina nova do Ciclo 1 e ANKI desativado | 1C (recomendado) |
| 6 | 2 | Estrutura de conteúdos e migração | 1 |
| 7 | 3A | Auditoria, classificação do alvo, incidência e padrões | 2 |
| 8 | 3B | Acervo complementar FEPESE | 3A |
| 9 | 4 | Amostra, desempenho e controle de estudo | 1C, 2, 3A |
| 10 | 5 | Geração de questões com filtro e três modos | 2, 3A, 4 |
| 11 | 6B | Cronograma operacional: fichas e prioridade | 3, 4, 5, 6A |
| 12 | 7A | Selos, frase padrão e marcação de IA | 1 a 6 |
| 13 | 7B | As 6 telas no design system (pendência C) | 7A |
| 14 | 8 | Auditoria final integrada | todas |

**Por que difere da ordem do novo.md:**

- **Actions primeiro (1A):** sem ele os testes de cada etapa não rodam no
  GitHub e a coleta diária segue parada desde 26/09.
- **6A antecipada:** a rotina com questões de manhã e o ANKI desligado foram
  pedidos para o Ciclo 1, que termina em 07/11. Nenhum dos dois depende da
  taxonomia. A 6A também não depende da 1C/1D: se quiser a rotina nova antes,
  ela pode vir logo depois da 1A.
- **Etapa 3 dividida:** as 162 questões do alvo destravam as Etapas 4, 5 e 6;
  o complementar é maior e pode vir depois sem travar nada.
- **Pendências encaixadas** onde mexem nos mesmos arquivos (A2 e A3 antes das
  telas; o bloco C junto da troca de selos, para não editar cada tela duas
  vezes). A 1B é independente e pode trocar de lugar com qualquer outra.

**Prazo externo:** o Ciclo 2 começa em **09/11**. Se a 6B não estiver pronta
até lá, o Ciclo 2 nasce no formato atual, com a rotina da 6A, e a 6B o converte
depois. Avisar quando faltar uma semana.

---

## Pendências × etapas

| Pendência (`docs/pendencias.md`) | Onde entra |
|---|---|
| A1 — Actions vermelho | 1A |
| A2 — texto de máquina na tela | 1B |
| A3 — Previsão com ano passado | 1B |
| B.1 — assunto e artigo nas questões FEPESE de Direito | 3A |
| B.2 — mapa de incidência por tema | 3A (o mapa) e 6B (na faixa); os rótulos "cai sempre"/"nunca caiu" são reescritos sem previsão |
| B.3 — lei seca vira "artigo cobrado" | 6A (provisório: os artigos-chave do `essencial`) e 6B (os artigos que a FEPESE cobrou) |
| B.4 — questões distribuídas pela incidência | 5 e 6B |
| B.5 — teoria com teto | 6A e 6B |
| B, pergunta 1 — quais provas FEPESE têm Direito Penal | 3B |
| B, perguntas 2 e 4 — quem classifica; Anki | respondidas na Etapa 0 (decisões 8 e 12) |
| B, pergunta 3 — versão enxuta do cronograma agora | 6A |
| B — quantas questões dos arts. 1º a 12 do CP caíram em 2019 | 3A |
| C — 6 telas no CSS antigo | 7B |
| D — `config/leis.yml` (leis que mudaram depois das provas) | 3A, se você trouxer a lista de mudanças; sem ela, segue pendente |
| D — importar macete e explicação | 6B (viram parte das fichas) |
| D — assunto no Direito | 3A |
| D — cronograma por IA | fora deste roteiro (fase futura); a 6B prepara a base |
| D — Ciclo 2 | 6B (ou formato atual com a rotina da 6A; ver o prazo) |
| D — conferir D1 e E1 a E4 em uso real | 8 |
| D — notificação do Windows; token do Telegram | ação sua, fora do roteiro |
| E — C1b cancelada | — |

---

## Etapa 1 — Correções críticas

Seção 17 do novo.md, mais as pendências A1, A2 e A3. Quatro subetapas, cada
uma com seus commits; cada uma pode ser uma conversa.

### 1A — GitHub Actions verde (pendência A1)

**Objetivo.** A suíte passar no Linux e em qualquer data, para o Actions voltar
a rodar a coleta diária e validar as próximas etapas.

**Arquivos envolvidos.**
- `tests/test_automacao.py`, `tests/test_cronometro.py`, `tests/test_avisos.py`;
- `docs/decisoes.md` e `CLAUDE.md` (o commit de registro da Etapa 0, ver acima).
- Nada em `src/` nem em `.github/workflows/coleta.yml`.

**Comportamento atual.** O `coleta.yml` (09:00 UTC) para no `pytest -q` desde o
commit `9ca6c04` (26/09): não coleta, não avisa e não exporta. Último verde: run
36245200577; vermelhos: 36325681266 e 36455934061. No Windows a suíte passa.

**Problema.** Três testes dependem do Windows ou da data de hoje:
`test_a_tarefa_da_web_chama_o_python_sem_janela_neste_modulo` (compara com
`pythonw.exe`, que não existe no Linux), `test_sem_javascript_nada_do_cronometro_aparece`
(assume 28/09 no futuro) e a função `_concurso` do `test_avisos.py` (data fixa
de 17/09, que sai da janela de 30 dias e quebra 18 testes por volta de 17/10).

**Solução proposta.** As três trocas descritas na pendência A1:
- comparar com `automacao.python_sem_janela()` em vez do nome do executável;
- parar o relógio (`servico.cronograma.agora_local`) na véspera, como já faz
  `test_as_faixas_do_plano_b_tambem_tem_play`;
- `publicado_em = agora() - timedelta(days=1)` no `_concurso`.

**Dependências.** Nenhuma.

**Implementação.**
1. Commit de documentação: as decisões da Etapa 0 no `decisoes.md` e a correção
   do "Estado atual" (geradas) no `CLAUDE.md`.
2. Commit com as três trocas nos testes.

**Testes necessários.** Os três passam; a suíte inteira passa; repetir a
conferência com o relógio simulado em 20/10/2026, 10/11/2026 e 15/03/2027, fora
do repositório (sem dependência nova), como foi feito na auditoria da pendência.

**Resultado dos testes.** Preenchido no `docs/progresso.md` ao fim da etapa.

**Critério de conclusão.**
- `pytest -q` verde no PC;
- workflow verde no GitHub: você dispara o "Run workflow" (o `workflow_dispatch`
  existe) ou espera o das 09:00 UTC;
- a pendência A1 sai do `pendencias.md`.

### 1B — Texto de máquina e Previsão (pendências A2 e A3)

**Objetivo.** Tirar da tela o texto cru das mudanças de situação e as frases
erradas da Previsão.

**Arquivos envolvidos.**
- `src/radar/eventos.py` (a descrição "Situacao: {de} -> {depois}");
- os templates que mostram eventos (`acompanhando.html`, `calendario.html`, e o
  que a home e as Análises usam — conferir antes);
- `src/radar/servico/previsao.py` e `templates/previsao.html`;
- `tests/test_eventos.py`, `tests/test_previsao.py`, `tests/test_home.py`.

**Comportamento atual.**
- A tela mostra "Situação: inscricoes_abertas -> encerrado".
- A Previsão mostra "Tijucas - Previsto para 2025", com o ano já passado, e
  "O último foi há 0 ano(s), so em 2030".
- Há texto exibido sem acento (lista da pendência A2).

**Problema.** Texto de máquina na tela; previsão vencida apresentada como se
estivesse para acontecer; frase errada.

**Solução proposta.**
- Uma frase por transição ("As inscrições encerraram", "O edital foi
  publicado", "A banca foi definida"…), só na exibição: banco e `eventos.json`
  não mudam.
- "Atrasado: era esperado em 2025", e esses ficam no topo de "Na janela de
  agora".
- "O último foi este ano" / "há 1 ano" / "há N anos", com acento.
- A conta da previsão não muda, só como aparece.
- Acentos no texto exibido, conferindo antes o que ainda está sem acento.

**Dependências.** Nenhuma.

**Implementação.** Um commit para A2, um para A3.

**Testes necessários.** A frase de cada transição; os acentos; a Previsão com
data fingida: ano passado vira "atrasado"; 0, 1 e 3 anos.

**Resultado dos testes.** Preenchido no `docs/progresso.md` ao fim da etapa.

**Critério de conclusão.** `pytest -q` verde; `radar web` mostrando as frases
novas na home, nas Análises e na Previsão; A2 e A3 saem do `pendencias.md`.

### 1C — Fonte única das métricas (seção 17)

**Objetivo.** Uma regra de contagem, num lugar só, lida por todas as telas e
relatórios; o "Fiz hoje" fechando a conta.

**Arquivos envolvidos.**
- `src/radar/servico/cronograma.py` (`Numeros`, `TotaisDoDia`,
  `totais_do_dia`, `numeros_do_radar`, `registrar_o_dia`), evoluídos para
  `src/radar/servico/metricas.py` (novo);
- quem hoje refaz a conta por conta própria: `servico/semanas.py`,
  `servico/materias.py`, `servico/simulado.py` (`desempenho`, `evolucao`,
  `resumo_do_simulado`, `_desempenho_pela_ultima_resposta`), `foco.py`
  (`_acerto_por_materia`, `_acerto_por_assunto`), `onde_estudar.py`,
  `servico/inicio.py`, `servico/espacada.py`;
- `src/radar/cli.py` (`hoje`, `_totais_legiveis`, `_registro_legivel`);
- `src/radar/web/app.py` e os templates `hoje.html`, `semanas.html`,
  `materias.html`, `foco.html`, `home.html`, `relatorio.html`;
- `tests/test_metricas.py` (novo), mais ajustes em `test_acertos_do_dia.py`,
  `test_semanas.py`, `test_materias_na_tela.py`, `test_tela_hoje.py`,
  `test_registro_estudo.py`, `test_ultima_resposta.py`.

**Comportamento atual.**
- `totais_do_dia` soma três origens: as faixas marcadas (questões e acertos
  digitados), o estudo extra (digitado) e as respostas dadas no radar (medidas).
  `Numeros` separa `questoes` (volume) de `medidas` (com acerto anotado e que
  não são de IA) e calcula `erros = max(medidas − acertos, 0)`.
- A linha "Fiz hoje" mostra o volume (31) ao lado de acertos e erros das
  medidas (13 + 8 = 21). As 10 de IA aparecem numa linha menor, separada.
- `registrar_o_dia` grava no registro do dia uma cópia do total (31) e dos
  acertos (13). A tela Hoje mostra também "Gravado neste dia: 31 questões,
  13 acertos", e o `radar hoje` mostra a mesma cópia em "Como foi". O
  `radar hoje --feitas/--acertos` ainda grava número digitado no registro.
- Semanas usa `totais_do_dia`. Minhas matérias refaz a conta sozinha (IA à
  parte; resposta de matéria que não casa fica fora). Meu foco, Onde estudar e
  home usam só o radar, pela última resposta de cada questão.

**Problema.**
- "Total ≠ acertos + erros", sem dizer qual é o terceiro estado.
- Dois números para o mesmo dia: o calculado e a cópia gravada.
- Telas que refazem a conta podem divergir entre si.
- O `max(…, 0)` esconde inconsistência em vez de acusá-la.

**Estados encontrados no código** (a regra tem que cobrir todos):

| Estado | De onde vem | Entra em |
|---|---|---|
| Acerto | resposta certa a questão real no radar; acertos anotados na faixa ou no extra | volume e acerto |
| Erro | resposta errada a questão real; questões − acertos anotados | volume e acerto |
| Sem resultado anotado | faixa ou extra com questões e sem acertos (inclui o check antigo `do_plano`) | só volume |
| Treino de IA | resposta a questão gerada | só volume; o acerto dela é um segundo número |
| Com consulta | atributo da faixa ou do extra (o radar é sempre sem consulta) | separa o que vale para a meta |
| Não respondida | questão de simulado sem `respondida_em` (rodada não terminada) | nada |
| Anulada | fica sem gabarito e não entra no sorteio | nada (a 1D confere respostas antigas) |
| Faixa feita com 0 questões | o Bônus de 28/09 | minutos sim, questões não (regra decidida na 1D) |

- **Duplicidade.** A mesma rodada recusa uma segunda resposta. A mesma questão
  respondida em duas rodadas conta 2 vezes no volume do dia (são duas
  respostas) e 1 vez no acumulado por questão (a última resposta, decisão de
  26/09). As duas contagens existem e passam a ter nome diferente.
- **Fuso.** O dia é o local: `_janela_do_dia` converte para UTC. Já está certo
  e ganha teste no módulo novo.

**Solução proposta.**
- `servico/metricas.py` passa a ser o único lugar de contagem. É a evolução de
  `Numeros`/`TotaisDoDia`, e não um módulo paralelo.
  - Duas contagens com nome: **respostas** (volume do dia e da semana) e
    **questões** (o acumulado, pela última resposta).
  - Os quatro recortes da decisão 4.
  - A regra: `total = acertos + erros + sem resultado anotado + treino de IA`,
    verificada em teste.
- Toda tela e o CLI pedem o número a ele; nenhum template soma nada.
- "Fiz hoje: 31 questões = 13 acertos + 8 erros + 10 de treino de IA", com
  "sem resultado anotado" quando houver, e o acerto da IA como segundo número.
- O registro do dia passa a guardar só a meta e a anotação. Os números já
  gravados ficam no banco e no JSON (nada é apagado), mas deixam de aparecer
  como o número do dia. O `radar hoje --feitas/--acertos` passa a gravar um
  estudo extra, que entra na conta como anotado.
- Meu foco, Onde estudar e home continuam no recorte *medido no radar*, escrito
  na tela, até a Etapa 4. Os mínimos de amostra também ficam para a Etapa 4.

**Dependências.** 1A.

**Implementação.**
1. O módulo novo, com os testes do caso 28/09.
2. Hoje e `radar hoje`.
3. Semanas e Minhas matérias.
4. Meu foco, Onde estudar, home e relatório do simulado.

Um commit por passo.

**Testes necessários.**
- A regra do total em todos os recortes.
- 28/09 reproduzido: Penal 11/6, Português 10/7, Bônus com 0 questões e 10 de
  IA dão "31 = 13 + 8 + 10".
- Mesmo período, mesmo número: Hoje, `radar hoje`, Semanas e Minhas matérias no
  mesmo recorte; Meu foco, Onde estudar e home iguais entre si no recorte radar.
- IA nunca em acerto; rodada não terminada não conta.
- Resposta às 22h de Florianópolis cai no dia certo.
- A mesma questão em duas rodadas: 2 respostas, 1 questão.

**Resultado dos testes.** Preenchido no `docs/progresso.md` ao fim da etapa.

**Critério de conclusão.**
- `pytest -q` verde;
- `radar hoje --data 2026-09-28` e a tela Hoje de 28/09 mostram a conta fechada;
- busca no código: nenhum serviço ou template fora de `metricas.py` soma acerto;
- decisão registrada no `decisoes.md`, dizendo o que muda na decisão E2.

### 1D — Conferência dos dados já gravados (seção 17, último parágrafo)

**Objetivo.** Saber se algum dado gravado desde 28/09 precisa de correção,
mostrar antes e corrigir só o que for aprovado.

**Arquivos envolvidos.**
- `src/radar/cli.py`: um comando de conferência, que só lê; ele grava só com
  `--aplicar`, depois da aprovação;
- `src/radar/servico/metricas.py`;
- `src/radar/acervo.py` (`data/registro_estudo.json`, `data/estado_do_dia.json`);
- `tests/test_conferencia_dos_dias.py` (novo).

**Comportamento atual.** Nenhum relatório compara o que está gravado com o que a
regra calcula.

**Problema.** O caso de 28/09 é conhecido (registro 31/13; Bônus feito com 0
questões e 25 min contados). Os outros dias não foram olhados.

**Solução proposta.**
- Um relatório por dia do ciclo, com estas colunas:
  - registro gravado × fonte única;
  - faixas feitas com 0 questões;
  - faixas com acertos maiores que as questões;
  - treino de IA no dia;
  - respostas a questões hoje anuladas;
  - checks órfãos (título que não bate mais com o cronograma).
- Saída em tabela: "dia · o que está gravado · o que a regra diz · proposta".
- **Aprovar antes de aplicar.** Com o "pode": cópia de segurança do banco e dos
  JSON, a alteração, e uma nova conferência mostrando que bate.
- Pergunta que já fica para você: **você fez o Bônus de 28/09?** Se não fez, a
  faixa sai de "feita" e as 3h50 viram 3h25. A regra para "faixa de questões
  marcada com 0 questões" é decidida aqui.

**Dependências.** 1C.

**Implementação.** Comando só de leitura → você aprova → `--aplicar` → o
`historico.md` registra o que mudou e por quê.

**Testes necessários.**
- Com banco de teste: cada anomalia é detectada.
- Nada muda sem `--aplicar`.
- Com `--aplicar`: cópia de segurança antes, e só o aprovado muda.

**Resultado dos testes.** Preenchido no `docs/progresso.md` ao fim da etapa.

**Critério de conclusão.**
- Relatório rodado no banco real e mostrado.
- As correções aprovadas aplicadas, ou registrado que nenhuma era necessária.
- Totais antes × depois conferidos.

---

## Etapa 2 — Estrutura de conteúdos

Seções 6, 14 (taxonomia), 2 (status de classificação), 4 (origem alvo ou
complementar) e 21 (migração). Regras invioláveis 1, 8 e 9.

**Objetivo.** A hierarquia matéria → assunto → subassunto → elemento
específico, com os níveis de baixo opcionais e taxonomia flexível por
disciplina. Junto, o status de classificação, a origem alvo ou complementar
gravada, e a migração do que já existe, sem perder nada.

**Arquivos envolvidos.**
- `src/radar/models.py`, `src/radar/db.py`;
- `src/radar/migracoes.py` (novo) e `src/radar/conteudos.py` (novo, puro: a
  árvore e as regras dela);
- `src/radar/edital_programa.py` e `src/radar/edital_materias.py` (a semente);
- a regra de evidência: `src/radar/alvo.py`, `src/radar/foco.py`
  (`_provas_do_alvo`), `src/radar/servico/simulado.py`
  (`_questoes_para_o_alvo`), `servico/geradas.py`, `servico/cartoes.py`,
  `auditoria.py`;
- `src/radar/acervo.py` e `src/radar/cli.py` (`importar`, `exportar`,
  `sincronizar`, e os comandos novos `radar migrar` e `radar conteudos`);
- `config/taxonomia.yml` (novo); `config/cronograma.yml` (chave `conteudo`
  nas faixas) e `src/radar/cronograma.py` (conferir a chave);
- `servico/erros.py`, `servico/extra.py`, `QuestaoGerada` (ligação opcional);
- `data/conteudos.json` e `data/classificacoes.json` (novos);
- `.gitignore` (`data/backup/`);
- testes novos: `test_conteudos.py`, `test_migracoes.py`, `test_evidencia.py`.

**Comportamento atual.**
- O assunto é um texto solto em cada lugar:
  - `questoes.assunto`, com modelo e data: 0 questões de Direito desde a
    etapa 15-0;
  - Português e Raciocínio Lógico: calculados na hora pelo catálogo de
    palavras-chave do `macetes.py`, sem nada gravado;
  - `questoes_geradas.materia/assunto/artigo`;
  - título da faixa no `cronograma.yml`: o mesmo tema teve dois nomes em
    28/09, "Aplicação da lei penal (arts. 1º a 12)" e "Aprendizagem: Aplicação
    da lei penal…";
  - caderno de erros e estudo extra: matéria e assunto digitados.
- O edital de 2019 dá 11 matérias e o programa de assuntos, lido literalmente
  pelo `edital_programa.py`. Não há subassunto nem elemento em lugar nenhum.
- "O que é alvo" é calculado, não gravado, e por **duas regras diferentes**:
  - `foco._provas_do_alvo` (cargo + estado), usada por Meu foco, geração,
    cartões e auditoria;
  - `simulado._questoes_para_o_alvo` (só o cargo).
  O Socioeducativo 2016 é "reforço" pelo `alvo.e_reforco`, que só a auditoria
  usa. O Meu foco também chama de "reforço" a mesma banca nas mesmas matérias.
- 20 questões geradas têm a matéria gravada como um título de faixa.
- A única migração que existe é `db._adicionar_colunas_novas` (ADD COLUMN
  automático). Não há versão do banco nem cópia antes de mudar. O
  `radar backup` exporta os JSON e faz push, mas não copia o `.db`.

**Problema.** Sem hierarquia não há incidência por subassunto ou elemento, nem
desempenho por conteúdo, nem filtro de geração, nem tarefa precisa. Os textos
soltos divergem. A origem alvo ou complementar não está gravada e tem duas
regras.

**Solução proposta.**
- **Tabela `conteudos`** (o nó):
  - pai, nível (matéria | assunto | subassunto | elemento) e nome, único
    dentro do mesmo pai;
  - tipo do elemento e referência (ex.: "CP, art. 2º");
  - origem (edital | classificação | manual), texto literal do edital quando
    vier dele, e procedência.
- **`config/taxonomia.yml`**: os tipos de elemento por família de matéria
  (artigo, inciso, súmula, prazo, regra gramatical, tipo de problema, comando,
  tratado, autor…) e os tipos de questão. Ampliar a lista não muda o banco.
- **Tabela `classificacoes`** (questão ↔ nó), pela impressão do enunciado, a
  chave que já sobrevive à reconstrução do banco:
  - o nó mais fundo alcançado;
  - status **completa** (chegou ao nível mais fundo que se aplica),
    **parcial** (parou no assunto) ou **pendente** (sem classificação segura);
  - justificativa: o trecho do enunciado, o item do edital e o dispositivo;
  - procedência (modelo e data, ou "manual") e "conferida por mim" com data;
  - **uma classificação principal por questão**, que é a que conta na
    incidência, e nós **associados** opcionais, mostrados e nunca somados.
- **Coluna `evidencia` em `questoes`**:
  - **alvo**: Agente Penitenciário / Polícia Penal SC, FEPESE, 2013 e 2019;
  - **complementar**: FEPESE, outra prova; o Socioeducativo 2016 vira
    complementar;
  - **fora**: outra banca; não entra em estatística da FEPESE.
  Preenchida por uma única função, que substitui as duas regras de hoje, e
  recalculada a cada reconstrução e a cada `importar`.
- **Semente:**
  - as matérias e assuntos do edital de 2019, com o texto literal;
  - as matérias de 2013 que não estão no edital atual (Noções de Informática,
    Direito Administrativo), marcadas como "fora do edital atual".
- **Ligações opcionais ao nó** na faixa do `cronograma.yml` (chave `conteudo`,
  conferida no carregamento como a `materia` já é), no check da faixa, no
  caderno de erros, no estudo extra e na questão gerada. O texto antigo fica
  onde está. Nos arquivos versionados o nó é gravado **pelo caminho de nomes**
  ("Direito Penal > Aplicação da lei penal > …"), e não pelo id, porque o banco
  é reconstruível.
- **Migração versionada (`migracoes.py`)**, o mínimo:
  - uma lista numerada de passos e a versão gravada no banco;
  - cópia do `.db` em `data/backup/` antes;
  - relatório "antes × depois" por tabela;
  - desfazer = restaurar a cópia (`radar migrar --desfazer`).
- **Textos antigos:** o que casa exatamente com um nó é ligado; o resto fica
  **pendente**, nunca forçado. As 20 geradas de Penal ganham a proposta
  "Direito Penal > [assunto do edital]", **mostrada antes de gravar**.
- **`data/assuntos.json`** (hoje vazio) é absorvido por
  `data/classificacoes.json`. O `importar` continua aceitando o formato antigo,
  com procedência obrigatória.

**Dependências.** Etapa 1 (números confiáveis antes de mexer no banco).

**Implementação.**
1. Migrações, cópia de segurança e desfazer.
2. `conteudos`, `taxonomia.yml` e a semente do edital.
3. `classificacoes`, com exportar e importar em JSON.
4. A regra única de evidência.
5. Ligações opcionais e migração dos textos antigos (aprovar antes de aplicar).
6. Docs.

**Testes necessários.**
- Migração:
  - banco no formato antigo migrado com as mesmas contagens por tabela;
  - migrar duas vezes não duplica;
  - a cópia é feita antes;
  - desfazer devolve o banco como era;
  - nenhuma linha apagada.
- Semente: a fixture `edital_sap_2019_programa.txt` dá as 11 matérias e os
  assuntos com o texto literal.
- Taxonomia: um tipo de elemento novo no YAML funciona sem migração.
- Classificação: sem procedência é recusada; texto que não casa fica pendente.
- Evidência: 2013 e 2019 = alvo, 2016 = complementar, IESES = fora; as duas
  regras antigas dão o mesmo que a nova.
- **Adicionar uma prova complementar não muda nenhum número do alvo** (§4).

**Resultado dos testes.** Preenchido no `docs/progresso.md` ao fim da etapa.

**Critério de conclusão.**
- Migração rodada no banco real, com o "antes × depois" batendo.
- `radar conteudos` mostra a árvore: 11 matérias e o mesmo número de assuntos
  que o `edital_programa.py` lê.
- Evidência conferida: 170 questões do alvo, as 70 de 2016 como complementar.
- Pendentes listados.
- Docs atualizados.

---

## Etapa 3 — Banco e análise FEPESE

Seções 2, 3, 4, 5 e 13. Regras invioláveis 1, 2, 3, 4 e 9.

### 3A — Auditoria e classificação do alvo, mapa de incidência, padrões

**Objetivo.**
- Auditar a extração das provas de 2013 e 2019.
- Classificar as 170 questões delas (162 válidas) na hierarquia.
- Montar o mapa de incidência do concurso-alvo e os padrões de cobrança.
- Tudo sempre com a amostra e separado de qualquer outra evidência.

**Arquivos envolvidos.**
- `src/radar/auditoria.py` e `docs/auditoria.md` (gerado pelo `radar auditar`);
- `src/radar/servico/manual.py`: novo tipo de pedido, "classificação", ao lado
  de questões, macetes e explicações;
- `src/radar/cli.py`: `radar classificar --pedido / --importar`;
- `src/radar/incidencia.py` (novo, puro, como o `onde_estudar.py`) e o serviço
  dele;
- `src/radar/macetes.py`: comandos, distribuição do gabarito, termos
  frequentes, por nó;
- `src/radar/foco.py` e `src/radar/onde_estudar.py`, que passam a contar por
  nó;
- `config/amostra.yml` (novo; nasce aqui com a seção do acervo e ganha a do
  desempenho na Etapa 4);
- `config/leis.yml` (`mudancas`, se a lista vier);
- web: uma tela de conferência da classificação e uma página
  "Análises → Incidência";
- testes novos: `test_classificacao.py`, `test_incidencia.py`, mais acréscimos
  em `test_auditoria.py`.

**Comportamento atual.**
- `radar auditar` confere, para 2013 (70 questões, 3 anuladas), 2019 (100, 5)
  e 2016 (70, 2):
  - a contagem por matéria contra o quadro do edital;
  - o gabarito definitivo, letra por letra;
  - as anuladas.
  Tudo bate. O próprio relatório avisa que **não confere enunciado e
  alternativa questão a questão**.
- O Meu foco mostra a incidência por matéria e ano.
- Por assunto, só Português e Raciocínio Lógico, pelo catálogo.
- Direito não tem nenhum assunto.

**Problema.**
- Não se sabe se o enunciado e as alternativas foram extraídos inteiros.
- Não há incidência por assunto, subassunto ou artigo.
- A pendência B.2 sugeriu rótulos com cara de previsão ("cai sempre").
- 2013 e 2019 têm editais diferentes:
  - 2013: 70 questões, com Informática e Direito Administrativo; sem LEP, sem
    Sociologia e sem Raciocínio Lógico;
  - 2019: 100 questões.
  "Apareceu em 1 de 2 provas" engana quando a matéria nem estava no edital
  daquele ano.

**Solução proposta.**
- **Auditoria ampliada:**
  - verificações automáticas de extração: enunciado vazio ou curto demais,
    alternativas diferentes de a–e, alternativa vazia, cabeçalho ou rodapé
    dentro do texto, sinal de tabela ou imagem perdida;
  - as suspeitas listadas para conferência;
  - no relatório, a contagem de classificação completa, parcial e pendente.
- **Classificação pelo Claude Code** (decisão 8), por lotes de matéria.
  - O pedido leva:
    - as questões, com gabarito;
    - a árvore atual;
    - os tipos do `taxonomia.yml`;
    - as regras: escolher o assunto **dentro do programa do edital**, propor
      subassunto e elemento, dizer o tipo de questão e a pegadinha (o que
      torna a alternativa errada atraente), justificar com trecho, item do
      edital e dispositivo, e responder **"pendente" quando não houver
      segurança**.
  - A importação recusa:
    - assunto fora do edital da matéria;
    - tipo fora da lista;
    - resposta sem justificativa;
    - classificação de questão que não estava no pedido.
  - Questão de 2013 em matéria que não está no edital atual só vai para um
    assunto de 2019 se o item do edital justificar. Senão fica em
    "fora do edital atual".
- **Conferência:** uma tela simples, com enunciado, alternativas, gabarito e a
  proposta lado a lado, e os botões confirmar / corrigir / pendente. São 162
  questões; a 3A só fecha com todas conferidas.
- **Mapa de incidência do alvo** (`radar incidencia` e a página
  "Análises → Incidência"):
  - por matéria, assunto, subassunto e elemento: quantidade de questões,
    provas, anos e tipo de questão;
  - recorrentes (nas 2 provas), as que apareceram uma vez só, e os itens do
    edital que não apareceram.
  - Sempre com a amostra: "8 questões · 2 provas".
  - O denominador é o número de **provas cujo edital tinha aquela matéria**
    ("LEP: 10 questões · 1 prova — só o edital de 2019 cobrava LEP").
  - **Anuladas** ficam fora da contagem e aparecem à parte, com o número.
  - **Pendentes** ficam fora da contagem e aparecem à parte, com o número.
  - Os rótulos da pendência B.2 viram "apareceu nas 2 provas · apareceu em 1 ·
    não apareceu nas provas analisadas".
- **Padrões de cobrança (§13):**
  - Contagens do `macetes.py` por nó: comando (correta/incorreta),
    distribuição do gabarito, termos frequentes.
  - Atributos da classificação: tipo de questão, literalidade, pegadinha.
  - Sempre como "padrão identificado no acervo analisado: N questões ·
    M provas · alvo".
  - Abaixo do mínimo do `config/amostra.yml` (proposta: 3 questões em
    2 provas), a frase fica exatamente "Não há evidência suficiente no acervo
    para afirmar isso."
- **Respostas que saem daqui:** quantas questões dos arts. 1º a 12 do CP caíram
  em 2019 (pendência B), por consulta.

**Dependências.** Etapa 2.

**Implementação.**
1. Auditoria ampliada.
2. O tipo de pedido "classificação" e a importação.
3. A tela de conferência.
4. Lotes por matéria: pedido → resposta → importar → conferir.
5. `incidencia.py` e a página.
6. Padrões.
7. Docs e `docs/auditoria.md` regerado.

**Testes necessários.**
- Importação:
  - recusa sem procedência, sem justificativa, com assunto fora do edital e com
    questão fora do pedido;
  - resposta "pendente" fica pendente, sem nó forçado.
- Incidência:
  - anuladas e pendentes fora da conta, mas mostradas;
  - o denominador segue o edital de cada ano;
  - toda linha leva a amostra;
  - abaixo do mínimo, a frase padrão exata;
  - nenhum texto com "vai cair", "certamente" ou "sempre cobra".
- Auditoria: cada verificação de extração pega o defeito numa fixture feita
  para isso.

**Resultado dos testes.** Preenchido no `docs/progresso.md` ao fim da etapa.

**Critério de conclusão.**
- `docs/auditoria.md` regerado: extraídas × prova, completa/parcial/pendente,
  sem gabarito ou inconsistente, anuladas, erros de extração.
- As 170 questões do alvo classificadas (completa, parcial ou pendente com
  motivo) e as 162 válidas conferidas por você.
- `radar incidencia` e a página mostram o mapa com a amostra.
- A pergunta dos arts. 1º a 12 respondida com o número.

### 3B — Acervo complementar FEPESE

**Objetivo.**
- Usar as provas FEPESE de outros concursos que já estão no banco para
  entender o estilo da banca, sem nunca misturá-las com o alvo.
- Ter pronto o processo de validação para qualquer prova que entrar depois.

**Arquivos envolvidos.**
- `src/radar/auditoria.py`: a validação generalizada para qualquer prova
  FEPESE com edital;
- um arquivo versionado de validação em `data/`, pela sha256 do caderno, com o
  status do parsing, do gabarito e a data de inclusão;
- `src/radar/incidencia.py` (a linha complementar);
- `src/radar/cli.py`: `radar complementar`, uma consulta que gera
  `docs/complementar.md`;
- `servico/manual.py` (classificação, como na 3A);
- `tests/test_complementar.py` (novo).

**Comportamento atual.**
- O manifesto `data/provas.json` já guarda url, concurso, ano e **sha256** de
  cada arquivo, de 25 concursos: 24 FEPESE (Estado 2013, 2016 e 2019, mais
  prefeituras de 2023 a 2026) e 1 IESES.
- A validação (contagem × quadro, gabarito definitivo, anuladas) só existe para
  o alvo e o 2016.
- O Meu foco já mostra o "reforço" (mesma banca, mesmas matérias) separado das
  provas do cargo, por assunto do catálogo.

**Problema.**
- Não se sabe quais provas FEPESE do acervo têm matérias semelhantes, nem
  quantas questões.
- Prova complementar não tem status de validação gravado.
- As perguntas da §5 (LEP, Sociologia e legislação prisional de SC fora da
  Polícia Penal) não têm resposta documentada.

**Solução proposta.**
- **Levantamento por consulta** (decisão 11): por matéria do edital, as provas
  FEPESE do acervo que a cobram, com cargo, ano, quantidade de questões e
  fonte. O resultado vai para `docs/complementar.md` e responde às 6 perguntas
  da §5 com o que o acervo tem, sem afirmar o que não está lá.
- **Aprovar antes de aplicar:** você escolhe quais provas entram como
  evidência complementar.
- **Validação mínima** de cada prova escolhida:
  - parsing: a contagem bate com o quadro do edital dela;
  - gabarito: definitivo, cobrindo todas as questões;
  - hash único: a mesma prova não entra duas vezes, mesmo com outro nome.
  - Prova sem validação não entra em estatística, e o sistema diz por quê.
- **Classificação** das provas escolhidas, por matéria, na ordem que você
  aprovar.
  - O catálogo de Português e Raciocínio Lógico serve de primeira proposta
    (🟡).
  - A conferência é **por amostra**: 20 por matéria, com a taxa de erro
    mostrada. Se a taxa for alta, o lote volta. Isso fica escrito na tela:
    "classificação automática conferida por amostra".
- **Incidência complementar sempre em linha própria**: "Polícia Penal SC:
  2 ocorrências em 2 provas · Acervo complementar FEPESE: 30 ocorrências em
  X provas".

**Dependências.** 3A (mesmo fluxo de classificação e incidência); a sua
aprovação da lista.

**Implementação.**
1. `radar complementar` e `docs/complementar.md`.
2. Você aprova a lista.
3. Validação e o arquivo de status.
4. Classificação por matéria.
5. A linha complementar na incidência.

**Testes necessários.**
- **Os números do alvo não mudam quando uma prova complementar é adicionada**
  (§4), comparando as contagens antes e depois com fixture.
- Hash repetido com outro nome é recusado.
- Prova sem validação fica fora da estatística, com o motivo.
- A consulta da §5 responde a partir da fixture.

**Resultado dos testes.** Preenchido no `docs/progresso.md` ao fim da etapa.

**Critério de conclusão.**
- `docs/complementar.md` gerado e mostrado.
- Lista aprovada.
- Provas escolhidas validadas e classificadas.
- A incidência mostra alvo e complementar separados, cada um com a amostra.

---

## Etapa 4 — Estatísticas, desempenho e controle de estudo

Seções 16 e 19 (e a parte de desempenho das seções 14 e 15). Regras
invioláveis 1, 3 e 4. A desativação do ANKI, que o novo.md põe aqui, foi
antecipada para a 6A.

**Objetivo.**
- Os estados de amostra com os limites da decisão 6, num lugar só.
- O desempenho por conteúdo (radar + Qconcursos).
- O controle do que já estudei, do que não estudei, do que revisar e do que
  refazer, sem ANKI.

**Arquivos envolvidos.**
- `config/amostra.yml` (a seção do desempenho);
- `src/radar/servico/metricas.py`;
- `src/radar/servico/desempenho.py` (novo: desempenho e estado por nó);
- `src/radar/servico/estudo.py` (novo: estudado, revisar, refazer), que reusa
  `servico/espacada.py` e `servico/erros.py` em vez de criar fila paralela;
- `onde_estudar.py`, `foco.py`, `servico/materias.py`, `servico/inicio.py`;
- templates `hoje.html` (seletor de conteúdo na faixa e no extra),
  `erro_novo.html`, `materias.html`, `foco.html`, `home.html`, e uma página
  "Análises → Meu desempenho";
- testes novos: `test_amostra.py`, `test_desempenho.py`, `test_estudo.py`.

**Comportamento atual.**
- Os mínimos são diferentes por tela:
  - `onde_estudar.py`: 5 na matéria e 3 no assunto;
  - `servico/materias.py`: 20;
  - `servico/erros.py`: 3, que mede outra coisa, a fatia dos motivos de erro.
- O acerto vem só do radar no Meu foco e no Onde estudar, e do radar mais o
  anotado em Minhas matérias.
- A anotação do Qconcursos é por faixa: matéria e o título da faixa, sem
  subassunto.
- A revisão 1-7-30 existe para assunto errado no radar (`espacada.py`) e para
  o caderno de erros.
- "Aulas vistas" conta as faixas de teoria marcadas, por matéria.

**Problema.**
- Três réguas diferentes para a mesma pergunta ("já dá para acreditar nesse
  número?").
- O desempenho do Qconcursos não chega ao subassunto.
- Não há definição de "conteúdo estudado", que o modo Revisão da Etapa 5 exige.
- A revisão não está ligada aos conteúdos.

**Solução proposta.**
- **`config/amostra.yml`** com os mínimos e os estados da decisão 6, lidos por
  todas as telas. O 5/3 e o 20 saem, registrados como revogados no
  `decisoes.md`. O 3 do caderno de erros é avaliado na etapa e documentado: ele
  mede fatia de motivo, não acerto.
- **Desempenho por nó:**
  - recortes: medido no radar (cada questão classificada, pela última
    resposta) + anotado (Qconcursos e extra, no nó escolhido ao anotar);
  - só o que foi respondido sem consulta conta para o estado;
  - treino de IA à parte;
  - sempre com a divisão "radar X% em N · anotado Y% em M".
  - Recorte de tempo padrão: o ciclo em andamento (decisão E4), com a opção
    "desde o início".
- **Anotar por subassunto:** o formulário da faixa e o do estudo extra ganham o
  seletor matéria → assunto → subassunto. O padrão vem da `conteudo` da faixa.
- **Conteúdo "estudado"** (resposta à §8): um nó está **estudado** quando uma
  faixa de estudo ligada a ele ou a um nó abaixo dele foi marcada como feita
  (teoria, lei seca, português, raciocínio), ou quando há estudo extra de teoria
  ou lei nele. Está **praticado** quando tem respostas. **Não estudado** é
  nenhum dos dois. Para cada nó: data do primeiro e do último estudo, última
  revisão, taxa de acerto e evolução semana a semana (as mesmas contas da tela
  Semanas).
- **Revisão (§19):**
  - um nó volta para revisão por erro recente, por estado "precisa revisar" ou
    pelo prazo 1-7-30 vencido;
  - "questões a refazer" = as erradas no radar + o caderno de erros;
  - tudo calculado do histórico, sem estado gravado à parte (a mesma escolha
    do `espacada.py`).
- O Meu foco e o Onde estudar passam a usar esse desempenho (decisão 7).

**Dependências.** 1C (fonte única), 2 (nós), 3A (questões reais classificadas).

**Implementação.**
1. `amostra.yml` e a troca dos mínimos.
2. `desempenho.py`.
3. O seletor de conteúdo nos formulários.
4. `estudo.py` e a revisão por nó.
5. A página "Meu desempenho" e os ajustes no Meu foco, Onde estudar e home.

**Testes necessários.**
- Mudar um valor no YAML de teste muda o comportamento.
- Bordas: 19/20 respostas, 59%/60%, exatamente na meta, dobro do mínimo com 1 e
  com 2 dias.
- Só o sem consulta conta para o estado; IA nunca conta.
- O anotado entra no nó escolhido.
- Estudado, praticado e não estudado.
- Os três gatilhos de revisão.
- A lista de refazer.
- A evolução semanal igual à da tela Semanas no mesmo período.

**Resultado dos testes.** Preenchido no `docs/progresso.md` ao fim da etapa.

**Critério de conclusão.**
- Nenhum mínimo de amostra fora do `config/amostra.yml` (conferido por busca).
- A página "Meu desempenho" mostra estado e amostra por nó, com dados reais.
- A definição de "estudado" registrada no `decisoes.md`.

---

## Etapa 5 — Geração de questões

Seções 7, 8 e 9. Regras invioláveis 5 e 9.

**Objetivo.**
- Um filtro hierárquico preciso para gerar questões.
- Três modos que não se confundem: treino específico, revisão e simulado.
- Cada questão gerada com a base dela registrada.

**Arquivos envolvidos.**
- `src/radar/cli.py` (`gerar`), `src/radar/servico/manual.py`,
  `src/radar/servico/geradas.py`, `src/radar/gerador.py` (o caminho com API,
  para ficar igual);
- `src/radar/models.py` (`QuestaoGerada`) e `src/radar/acervo.py` (os campos
  novos no `questoes_geradas.json`);
- `src/radar/web/app.py` e `geradas.html`: o mesmo filtro na tela;
- `tests/test_geracao_por_conteudo.py` (novo).

**Comportamento atual.**
- `radar gerar --pedido` aceita só `--materia` e `--quantas`.
- O modo `variacao` guarda `origem_impressao` (a questão real de base); o
  `do_zero` entra quando a matéria não tem questão real e grava a matéria
  recebida, sem assunto.
- Existe uma coluna `artigo` em texto livre.
- A importação confere a procedência e o artigo citado (`leis.exige_artigo`).

**Problema.**
- Pedir "Lei de Execução Penal" traz qualquer parte da lei.
- Não há treino só do que já estudei.
- A questão gerada não diz o escopo dela nem se a base é do alvo ou do
  complementar.

**Solução proposta.**
- **Comandos (nomes em português; `--elemento` vale também para regra, comando,
  tipo de problema):**
  - `radar gerar --pedido --modo treino --materia "Direito Penal"
    --assunto "Aplicação da lei penal" [--subassunto "Lei penal no tempo"]
    [--elemento "art. 2º"] --quantas 20`
  - `radar gerar --pedido --modo revisao --materia "Direito Constitucional"
    --quantas 20` — só os nós **estudados** (Etapa 4).
  - `radar gerar --pedido --modo simulado --materia …` — o comportamento amplo
    de hoje, pelo edital e pelo peso, com o modo escrito na saída.
  - Sem `--modo`: com assunto é treino; só com matéria é simulado, e a saída diz
    isso.
- **Nome que não existe:** o comando para e sugere até 5 nomes parecidos
  (`difflib`, da biblioteca padrão). Ele nunca alarga o escopo sozinho.
- **O pedido leva:**
  - o caminho do nó;
  - as questões reais dele (alvo primeiro, depois complementar, cada uma
    marcada);
  - o dispositivo e o link oficial (`leis.yml`);
  - a ordem de não sair do escopo, com cada questão declarando o nó e o
    dispositivo.
- **A importação aceita só:**
  - questão cujo nó declarado está dentro do escopo pedido;
  - com elemento pedido, o dispositivo citado tem que bater;
  - `origem_impressao` só se a questão real estava no pedido;
  - `do_zero` só com a marca "sem questão real de referência".
  O resto é recusado e contado na saída. **A garantia é a validação do que a IA
  declara**; a leitura do texto continua sendo sua, no treino, com o botão de
  marcar como errada que já existe.
- **Campos novos na questão gerada:**
  - o nó;
  - o modo do pedido;
  - a base (variação de questão real | fonte oficial | item do edital);
  - a evidência da base (alvo | complementar | nenhuma);
  - o dispositivo.
  As 50 de hoje ganham isso na migração da Etapa 2.
- **Prioridade da base (§9):** questão real do mesmo nó (alvo, depois
  complementar) → fonte oficial → item do edital.

**Dependências.** 2, 3A (bases classificadas) e 4 ("estudado").

**Implementação.**
1. Filtro e validação dos nomes.
2. Os três modos.
3. O pedido com escopo.
4. A importação com as recusas.
5. Os campos novos e a tela.

**Testes necessários.**
- **Nenhuma questão fora do escopo informado entra** (§8): uma fixture de
  resposta com itens dentro e fora; só os de dentro são gravados.
- Nome inexistente: erro com sugestões, sem gerar.
- O modo revisão só pega nós estudados.
- Vínculo com questão real que não estava no pedido é recusado.
- `do_zero` sem a marca é recusado.
- A evidência da base vem gravada.
- As 50 antigas continuam listadas.

**Resultado dos testes.** Preenchido no `docs/progresso.md` ao fim da etapa.

**Critério de conclusão.** Os dois exemplos da §23 rodados de verdade no PC,
com a conferência de que nenhuma questão saiu do escopo:
- "20 · Direito Penal · Aplicação da Lei Penal · Lei penal no tempo";
- "20 · LEP · Progressão de regime · Art. 112".

---

## Etapa 6 — Cronograma e rotina

Seções 10, 11, 12, 14, 15 e 18. Regras invioláveis 6 e 7. Dividida em duas: a
**6A** vai já para o Ciclo 1 (decisão 13); a **6B** depende das Etapas 3 a 5.

### 6A — Rotina do Ciclo 1 com questões de manhã e ANKI desativado (antecipada)

**Objetivo.** Redistribuir o dia útil entre teoria, lei seca, questões,
correção e revisão, com questões também de manhã, sem aumentar o dia; e
desligar o ANKI sem apagar nada, fácil de religar.

**Arquivos envolvidos.**
- `config/cronograma.yml`: só os dias a partir da data de aplicação, e a
  chave `anki`;
- `src/radar/cronograma.py`:
  - ler a chave `anki`;
  - esconder a faixa `anki` e o chip do `baralho` quando desligado;
  - a chave `consulta` por faixa (hoje a regra está fixa no código para a
    rampa de Direito);
- `src/radar/servico/cronograma.py` (a sugestão de meta ignora a faixa
  desligada);
- `src/radar/web/templates/hoje.html` e `src/radar/cli.py` (`radar hoje`);
- `README.md` (como religar);
- `tests/fixtures/cronograma_mini.yml`, `test_cronograma.py`,
  `test_tela_hoje.py`, `test_faixas_do_dia.py`, `test_plano_b.py`.

**Comportamento atual.** No dia útil, nível 1:

| Bloco | Hoje |
|---|---|
| Manhã (10:15) | teoria 50 · pausa 10 · lei seca 40 · pausa 10 · Português (ou Raciocínio) 30 = 2h20, **0 questões** |
| Noite (18:00) | questões de Direito (rampa: 15 no nível 1, até 25) · pausa 10 · questões de Português (10 a 15) · correção 20 ≈ 1h35 |
| Depois das 22h | **ANKI 30** · bônus opcional (10 questões) |
| **Total** | **≈ 4h25 e 25 questões** |

- No arquivo há 36 faixas `tipo: anki` e o campo `baralho` nas teorias.
- O detalhe das 30 faixas de lei seca manda "transformar em cartões do Anki à
  noite".

**Problema.**
- A manhã inteira é leitura passiva.
- A lei seca de 40 minutos é igual em 30 dias (decisão de 28/09: vai mudar).
- O ANKI é etapa obrigatória do dia, e eu não quero usar agora.

**Solução proposta.** O ponto de partida abaixo. **Aprovar antes de
aplicar**, com os números finais (§18).

| Bloco | Proposta |
|---|---|
| Manhã (10:15) | teoria dirigida 40 (uma fonte só; passou do tempo, segue) · **questões de fixação do tema 20 (8 questões)** · pausa 10 · lei seca dirigida 20 (só os artigos-chave do `essencial` do dia) · pausa 10 · Português (ou Raciocínio): teoria 20 + **6 questões 15** = 2h15, **14 questões** |
| Noite (18:00) | igual |
| Depois das 22h | linha minimizada "ANKI temporariamente desativado" · bônus opcional |
| **Total** | **≈ 3h50 e 39 questões no nível 1** (35 min a menos, 14 questões a mais) |

- A fixação segue a regra da faixa de aprendizagem de Direito: a caixa "com
  consulta" vem marcada, e ela fica fora da comparação com a meta. Acabou de
  ler o tema; o número infla.
- A lei seca dirigida é seleção do plano, a partir do texto da lei. Ela vira
  "os artigos que a FEPESE cobrou" na 6B.
- **Dias que já passaram não mudam:** os checks são reconhecidos por bloco,
  posição e título, e mudar um dia passado apagaria o que foi feito.
- **ANKI:** a chave `anki: desativado` no topo do `cronograma.yml`. As
  36 faixas e o `baralho` continuam no arquivo; com a chave desligada, a faixa
  some do dia, do total e da sugestão de meta. **Para religar: trocar para
  `anki: ativado`** (escrito no README e no `decisoes.md`).

**Dependências.** 1C, recomendado. Pode vir logo depois da 1A, se você quiser a
rotina antes.

**Implementação.**
1. Apresentar a proposta final e esperar o "pode".
2. A chave `anki`, com testes.
3. A chave `consulta` por faixa.
4. Reescrever os dias a partir da data de aplicação com um script de uma vez
   só, fora do repositório, mostrando o resumo dia a dia (o que sai, o que
   entra).
5. Commit do YAML.
6. Docs.

**Testes necessários.**
- ANKI desligado: a faixa some do dia, do total e da sugestão, e a linha
  minimizada aparece. Religado: volta igual a antes.
- Nenhum dia anterior à data de aplicação mudou (comparado com o YAML antigo).
- Minutos do dia útil depois da mudança ≤ antes.
- Toda manhã de dia útil depois da mudança tem faixa de questões.
- O YAML carrega (as conferências que já existem).
- O Plano B continua montando.

**Resultado dos testes.** Preenchido no `docs/progresso.md` ao fim da etapa.

**Critério de conclusão.**
- A proposta foi aprovada e aplicada.
- A tela Hoje e o `radar hoje` de um dia depois da mudança mostram a manhã com
  questões e o ANKI minimizado.
- Religar foi testado (troca a chave, confere, destroca).
- Como religar está escrito no README.

### 6B — Cronograma operacional: fichas e prioridade

**Objetivo.** Cada tarefa do cronograma vira um instrumento de estudo
executável, com começo, meio e fim. A prioridade passa a ser explicada.

**Arquivos envolvidos.**
- `src/radar/servico/fichas.py` (novo): a estrutura única da tarefa;
- `data/fichas.json` (novo, versionado): o conteúdo escrito;
- `config/prioridade.yml` (novo): os pesos;
- `src/radar/onde_estudar.py`: a fórmula de prioridade evolui daqui;
- `config/cronograma.yml` (a chave `conteudo` nas faixas, e o Ciclo 2) e
  `src/radar/cronograma.py`;
- `servico/manual.py`: pedido de ficha, como os de macete e explicação, que
  esta etapa absorve;
- `config/leis.yml` (a fonte oficial);
- `hoje.html` e `cli.py` (`radar hoje`);
- `tests/test_fichas.py` e `tests/test_prioridade.py` (novos).

**Comportamento atual.**
- A faixa tem título, detalhe (um parágrafo como "Art. 5º, caput e incisos
  I a XVI" com a lista de temas), link oficial e o filtro do Qconcursos.
- O dia útil tem o `essencial`: artigos-chave com o porquê, escolhidos pelo
  plano.
- A prioridade existe só no Onde estudar: questões esperadas × (1 − acerto) ×
  fator de tempo. Ela não aparece na tarefa.

**Problema.** A tarefa diz o nome do assunto, não o que fazer agora (§10): o
que ler exatamente, como achar o conteúdo, o que dominar, quais pegadinhas,
quantas questões e de quê, por que hoje.

**Solução proposta.**
- **Estrutura única `FichaDeEstudo`**, com os campos da §11 em português:

  | Campo da §11 | Campo na ficha | De onde vem |
  |---|---|---|
  | subject, topic, subtopic | `materia`, `assunto`, `subassunto` | a árvore (Etapa 2) |
  | specific_element, element_type | `elemento`, `tipo_elemento` | a árvore |
  | why_now | `por_que_agora` | calculado: cada fator, com número e origem |
  | source_material | `fonte` | `leis.yml` (🟢) ou a fonte escolhida, com o selo |
  | read_exactly | `ler_exatamente` | escrito (🟣 ou à mão) |
  | search_queries | `como_pesquisar` | escrito (🟣) |
  | must_understand, must_memorize | `entender`, `memorizar` | escrito (🟣) |
  | fepese_traps | `pegadinhas` | das classificações (🔵, com número da questão) ou escrito (🟣) |
  | fepese_pattern | `padrao_fepese` | calculado (3A/3B): alvo e complementar separados, com a amostra |
  | related_real_questions | `questoes_reais` | calculado (as classificadas no nó) |
  | practice_target | `meta_de_questoes` | calculado: N do elemento + M do assunto, e de onde vêm |
  | review_trigger | `quando_revisar` | calculado (Etapa 4) |

  - Uma estrutura só, usada pela tela Hoje (a faixa de estudo abre a ficha),
    pelo `radar hoje`, pelo Plano B (o essencial sai da ficha) e pela geração
    (o escopo).
  - Campo sem dado mostra a frase padrão, e nunca é inventado.
- **Conteúdo escrito** pelo Claude Code no fluxo pedido/importar (decisão 9),
  com procedência e 🟣, ou à mão. A fonte oficial vem do `leis.yml`.
- **Prioridade documentada** em `config/prioridade.yml`:
  - parte da fórmula do Onde estudar: peso da matéria no edital × fatia do nó
    na incidência **do alvo** × (1 − acerto quando medido; "não estudado"
    conta como 1) × fator de tempo (1 a 2) × gatilho de revisão;
  - o complementar entra só em linha separada, com peso menor declarado no
    YAML (§15);
  - "Você está estudando isto agora porque…" lista cada fator com o número e
    a origem.
- **No cronograma:**
  - as faixas do resto do Ciclo 1 ganham `conteudo` e mostram a ficha;
  - o **Ciclo 2** (09/11 a 19/12) é montado pela prioridade e pela rotina da
    6A, **aprovado antes de gravar**;
  - as faixas R+7/R+30 continuam fixas no calendário, mas o conteúdo delas é
    escolhido pela fila de revisão (Etapa 4) na hora de mostrar.

**Dependências.** 3 (incidência e padrões), 4 (desempenho e revisão), 5
(questões geradas por nó) e 6A.

**Implementação.**
1. `FichaDeEstudo` e a montagem dos campos calculados.
2. O pedido e a importação das partes escritas.
3. `prioridade.yml` e o "por que agora".
4. A ficha na tela Hoje e no CLI.
5. O Ciclo 2: proposta → aprovação → YAML.
6. Docs.

**Testes necessários.**
- A ficha tem todos os campos; campo vazio mostra a frase padrão.
- A prioridade é reproduzível com a fixture e muda quando o peso do YAML muda.
- Alvo e complementar separados na explicação; com peso 0 do complementar, a
  ordem não muda.
- Texto de IA na ficha leva 🟣 e procedência.
- O YAML do Ciclo 2 carrega, e os dias passados ficam intactos.

**Resultado dos testes.** Preenchido no `docs/progresso.md` ao fim da etapa.

**Critério de conclusão.** O cenário da §23 respondido pela ficha, com dados
reais: "Direito Constitucional → Direitos Fundamentais → Art. 5º → incisos
I a XVI". Ela tem que dizer:
- o que ler, onde ler e como procurar;
- o que entender e o que memorizar;
- as pegadinhas e como a FEPESE cobrou;
- as questões reais relacionadas;
- quantas questões fazer e quais geradas fazer;
- os erros a revisar;
- por que hoje.

---

## Etapa 7 — UX e confiabilidade visual

Seção 20 e as regras invioláveis 2, 3, 4 e 5 vistas na tela; mais a
pendência C.

### 7A — Selos, frase padrão e marcação de IA

**Objetivo.**
- As quatro origens com as cores do novo.md, registradas nos dados e não só
  pintadas.
- A frase de evidência insuficiente idêntica em todo lugar.
- Alvo, complementar e desempenho sempre separados.
- Questão de IA nunca parecendo oficial.

**Arquivos envolvidos.**
- `src/radar/web/templates/_componentes.html` (`SELOS`, `selo`,
  `legenda_dos_selos`);
- `src/radar/web/static/design.css`: os tokens `--selo-*`, claro e escuro;
- as cores das metas, que hoje reusam os tokens dos selos: `design.css`,
  `app.py` (`OPCOES_DE_META`), `hoje.html`;
- os serviços que entregam número ou texto à tela (o campo de origem);
- `docs/especificacao.md` (a tabela dos selos) e `docs/decisoes.md`;
- `tests/test_design.py` e um teste novo de varredura das telas.

**Comportamento atual.** Seis selos em quatro cores:
- 🟦 fonte oficial e 🟦 extraída da prova;
- 🟩 calculado (contagem no acervo);
- 🟨 classificação automática e 🟨 tendência;
- 🟥 gerado por IA.

As metas Ideal, Reduzida e Mínima reusam essas cores. A frase "não sei ainda"
e o rótulo "amostra pequena" variam por tela.

**Problema.** As cores pedidas trocam o significado do verde (hoje é calculado,
passa a ser oficial). O selo é escolhido no template, e não vem do dado. A
frase padrão da regra 4 não existe.

**Solução proposta.**

| Hoje | Passa a |
|---|---|
| 🟦 Fonte oficial | 🟢 Fonte oficial |
| 🟦 Extraída da prova | 🟢 Extraída da prova |
| 🟩 Calculado pelo sistema (contagem no acervo) | 🔵 Estatística do acervo |
| 🟨 Classificação automática | 🟡 Análise automática (classificação) |
| 🟨 Tendência | 🟡 Análise automática (tendência) |
| — (desempenho, prioridade) | 🟡 Análise automática |
| 🟥 Gerado por IA | 🟣 Gerado por IA |

- **A origem gravada no dado:** todo número ou texto que um serviço entrega
  leva a origem (`oficial` | `acervo` | `automatico` | `ia`), e o template
  desenha o selo a partir dela.
- **As metas ganham tokens próprios**, para a troca dos selos não mudar a cor
  delas sem querer.
- **Frase padrão:** "Não há evidência suficiente no acervo para afirmar isso."
  numa constante só, usada para acervo e padrão. Para desempenho pessoal vale o
  estado "Amostra insuficiente" (decisão 6).
- **Exibição separada:** alvo, complementar e desempenho em linhas próprias,
  cada uma com a amostra.
- **🟣 em toda tela que mostra questão de IA**, com "não é questão oficial da
  FEPESE".

**Dependências.** Etapas 1 a 6: as telas finais já existem.

**Implementação.**
1. Os tokens e o `SELOS`.
2. A origem nos serviços.
3. A frase padrão.
4. As telas, uma por commit.
5. `especificacao.md` e `decisoes.md`.

**Testes necessários.**
- O `test_design.py` com as cores novas.
- Todo serviço de número devolve a origem.
- A frase padrão com o texto exato.
- Varredura das telas: nenhum "vai cair", "certamente" ou "sempre cobra";
  nenhuma questão de IA sem 🟣; nenhuma estatística sem a amostra.

**Resultado dos testes.** Preenchido no `docs/progresso.md` ao fim da etapa.

**Critério de conclusão.**
- `pytest -q` verde.
- As telas conferidas no navegador, nos dois temas.
- `especificacao.md` e `decisoes.md` dizem as cores novas.

### 7B — As 6 telas no design system (pendência C)

**Objetivo.** Migrar as seis telas que ainda usam o CSS antigo, sem mudar
função nem dado.

**Arquivos envolvidos.** `foco.html` (Análises), `index.html` (Concursos),
`previsao.html`, `acompanhando.html`, `calendario.html`, `404.html`; o CSS
antigo de cada uma; a seção do `README.md` que descreve as telas; os testes de
cada tela.

**Comportamento atual.** As seis não têm `body class="ds"`. Simulado e Gerar
questões já migraram (B1).

**Problema.** Duas aparências no mesmo site; os selos novos da 7A não chegam
inteiros nessas telas.

**Solução proposta.** Uma tela por commit:
- só `ds-pagina`, `ds-cartao`, `ds-campo`, `ds-botao`, `ds-tabela` e os tokens
  que já existem;
- nos dois temas;
- o CSS antigo da tela sai.

**Dependências.** 7A (e a 1B, que mexe nos mesmos templates).

**Implementação.** Seis commits; o último ajusta o README.

**Testes necessários.** Cada tela abre (status 200) com `class="ds"` e sem o
CSS antigo; os testes de função de cada tela continuam passando.

**Resultado dos testes.** Preenchido no `docs/progresso.md` ao fim da etapa.

**Critério de conclusão.** As seis conferidas no navegador, nos dois temas; o
bloco C sai do `pendencias.md`.

---

## Etapa 8 — Auditoria final integrada

Seção 23 inteira.

**Objetivo.** Verificar o sistema de ponta a ponta contra os critérios de
aceite, com dados reais, e registrar o resultado.

**Arquivos envolvidos.**
- `tests/test_aceite.py` (novo, com banco de fixture);
- `docs/auditoria_final.md` (gerado);
- `docs/historico.md`, `decisoes.md`, `pendencias.md`, o "Estado atual" do
  `CLAUDE.md` e o `docs/progresso.md`.

**Comportamento atual.** Cada etapa foi testada sozinha; ninguém conferiu o
conjunto.

**Problema.** Uma etapa pode ter quebrado a promessa de outra, por exemplo um
número que voltou a divergir, ou um selo que sumiu numa tela nova.

**Solução proposta.**
1. **Testes de aceite automáticos**, na fixture, para cada item da §23.
2. **Roteiro manual no PC**, com o banco real:
   - o cenário do Art. 5º, incisos I a XVI, pela ficha;
   - os dois pedidos de geração da §23, conferindo que nada saiu do escopo;
   - o mesmo período na Hoje, Semanas, Minhas matérias e `radar hoje`;
   - a incidência do alvo antes e depois de pôr uma prova complementar;
   - as contagens por tabela contra a cópia de antes da Etapa 2;
   - desligar e religar o ANKI;
   - nenhuma estatística sem amostra e nenhuma questão de IA sem 🟣;
   - o Actions verde.
3. **Uso real** do backup das 23h30, do caderno de erros e da tela Semanas
   (pendência D: conferir D1 e E1 a E4).

**Dependências.** Todas as etapas.

**Implementação.** Os testes de aceite; o roteiro manual com o resultado de
cada item em `docs/auditoria_final.md`; o que não atender vira pendência, com o
motivo.

**Testes necessários.** `tests/test_aceite.py` cobrindo:
- os 12 itens que a ficha tem que responder (§23);
- a seleção matéria → assunto → subassunto → elemento para gerar;
- os 6 itens finais da §23.

**Resultado dos testes.** Preenchido no `docs/progresso.md` ao fim da etapa.

**Critério de conclusão.**
- Cada item da §23 marcado "atende", com a evidência (teste, comando ou tela).
- O que não atende está registrado como pendência; a etapa não é marcada
  concluída "porque existe código".
- O "Estado atual" do `CLAUDE.md` reescrito.

---

## Checklist de fim de etapa

- [ ] `pytest -q` verde, sem teste que dependa do Windows ou da data de hoje
- [ ] o comando afetado rodado de verdade no PC, com o banco real
- [ ] as regras invioláveis do novo.md conferidas para o que a etapa tocou
- [ ] nada apagado; se mexeu em banco ou dado gravado: cópia antes e "antes × depois"
- [ ] commits só desta etapa, na `main`, com push
- [ ] `historico.md`, `decisoes.md`, `pendencias.md`, "Estado atual" do `CLAUDE.md` e `docs/progresso.md` atualizados
- [ ] PAROU e mostrou: arquivos alterados, testes executados, resultado e critério atendido

## Como registrar no docs/progresso.md

Uma seção por etapa (ou subetapa), acrescentada quando ela começa e completada
quando termina:

```
## Etapa 1C — Fonte única das métricas
- Situação: em andamento | aguardando aprovação | concluída
- Datas: início dd/mm · fim dd/mm
- Commits: <hash> <título>, ...
- Arquivos alterados: ...
- Testes: `pytest -q` → N passed (novos: ...)
- Comando real rodado: ...
- Critério de conclusão: atendido / não atendido — por quê
- Decisões e pendências geradas: ...
- Aprovada por mim em: dd/mm
```
