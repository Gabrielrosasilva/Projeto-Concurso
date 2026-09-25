# Especificação — Painel Pessoal de Preparação para Concursos

> Coloque este arquivo em `docs/especificacao.md` e adicione ao CLAUDE.md a linha:
> "**docs/especificacao.md** — o redesign em andamento; leia antes de mexer em tela ou em dado de estudo."

## Proposta central

Transformar provas anteriores, edital e o meu desempenho em uma orientação de estudo
prática e imediata. Ao abrir o site eu preciso saber **o que estudar, por que estudar
aquilo, e começar a treinar em um clique**.

Princípio de interface: mais limpa → menos informação ao mesmo tempo → mais visual →
mais didática → compreensão rápida → ação imediata.

## Regras que valem para tudo

1. **Não reescrever o que já funciona.** O sistema já tem: tabela `questoes` (provas
   oficiais) separada de `questoes_geradas`, campo `anulada`, `simulados` e
   `respostas_de_simulado`, `gabarito.py` (anuladas e trocadas), `macetes.py` (só
   contagem). Reaproveitar tudo isso; mudar só o que for preciso.
2. **Seguir o CLAUDE.md**: Python simples, sem framework JS pesado, texto em português.
3. **Nenhum número sem fonte.** Todo número exibido mostra de onde veio
   (ex.: "12 de 60 questões — provas 2013 e 2019"). Nada fixo no código: por exemplo,
   o total de anuladas de 2019 vem do banco, não de um texto escrito à mão.
4. **Amostra pequena é dita na tela.** Só existem 2 provas de Agente Penitenciário
   (2013 e 2019). Tendência tirada de 2 provas aparece com o aviso "base pequena".
5. **Os testes existentes (pytest) continuam passando** e cada fase ganha testes novos.

## Selos de confiança (aparecem em todo conteúdo)

| Selo | O que é | Origem | Exemplo |
|---|---|---|---|
| 🟦 Fonte oficial | Edital, gabarito definitivo/retificado | PDF oficial FEPESE | "O edital 2019 cobrou 10 questões de Português" |
| 🟦 Extraída da prova | Questão real | Caderno oficial | Questão 14, SAP/SC 2019 |
| 🟩 Calculado pelo sistema | Contagem no acervo | Banco de questões | "Português = 20% das questões" |
| 🟨 Classificação automática | Assunto atribuído por palavra-chave | Classificador | Q14 → "Inquérito policial" |
| 🟨 Tendência | Leitura dos números | Estatística (base pequena!) | "A FEPESE costuma cobrar interpretação" |
| 🟥 Gerado por IA | Macete, explicação, questão criada | LLM — material auxiliar | Mnemônico, questão gerada |

Regras dos selos:
- Conteúdo 🟥 **nunca** aparece misturado com conteúdo oficial sem o selo.
- Questão ou explicação 🟥 precisa **citar o artigo de lei** que fundamenta a resposta.
- Questão de prova antiga cujo tema mudou por lei posterior ganha o aviso
  **"⚠ A lei mudou depois desta prova"** (EC 104/2019, Lei 13.964/2019 — Pacote
  Anticrime —, alterações na LEP, CP, CPP etc.). A lista de temas afetados mora em
  `config/leis.yml`, não no código.

## Navegação (sitemap)

- 🎯 **Meu foco**: Polícia Penal SC · Minha evolução · Prioridades · Próximo treino
- 📚 **Estudar**: Treino rápido · Simulados · Meus erros
- 🧠 **Revisão**: Macetes · Padrões da banca · Pegadinhas · Assuntos
- 📊 **Análises**: Incidência FEPESE · Matérias/Assuntos · Meu desempenho
- 🏛 **Concursos**: Acompanhando · Inscrições abertas · Próximos/Outros · Calendário · Previsão
- ⚙ **Mais**: Fontes e evidências · Configurações · Sistema

Onde cada tela atual vai parar:

| Tela atual | Destino |
|---|---|
| `index.html` (radar de concursos) | Concursos → Inscrições abertas / Outros |
| `foco.html` | Meu foco (home) + Análises |
| `simulado.html` | Estudar → Simulados |
| `geradas.html` | Estudar → Treino rápido (com selo 🟥) |
| `macetes.html` | Revisão |
| `acompanhando.html`, `calendario.html`, `previsao.html` | Concursos |

## Home — só 5 blocos, nada além disso

1. **🎯 Polícia Penal SC**: status do concurso (edital aberto? previsão?).
2. **📚 O que estudar agora**: as 3 matérias prioritárias + botão **[Começar treino]**.
3. **📊 Sua evolução**: % geral de acerto e a variação nos últimos 30 dias.
4. **🧠 Revisar**: nº de questões erradas, assuntos fracos, revisões pendentes + **[Revisar agora]**.
5. **📋 Concurso**: últimas alterações e notícias.

## "O que estudar primeiro" (prioridade do dia)

Cálculo **sem IA**, explicável na tela:
`prioridade = incidência do assunto na FEPESE × (1 − minha taxa de acerto) × fator de tempo desde a última revisão`

- Com menos de 5 respostas no assunto, a taxa de acerto é tratada como "desconhecida"
  e o assunto entra como "ainda não treinado".
- O cartão mostra o porquê: "Alta incidência + 32% de acerto em 25 questões".

## Simulados

- **Só meus erros**: caderno só com questões que errei (sem as anuladas).
- **Simulado compilado (40 / 50 / 100 questões)**: escolho as matérias; a distribuição
  segue os pesos do **quadro de provas do último edital** (edital SAP 2019), lidos do
  edital, não digitados no código.
- Provas oficiais e questões geradas **nunca** se misturam no mesmo simulado sem aviso.

### Relatório pós-simulado

- Resultado geral (acertos / total, %).
- Desempenho por matéria, com destaque para as que ficaram abaixo da média.
- Para cada erro: a alternativa que marquei, a correta, a explicação e o macete
  relacionado, cada um com o seu selo.
- **Não mostrar "nota de corte estimada"** enquanto não houver fonte oficial para ela
  (resultado/classificação publicados). Se um dia houver, mostrar com o selo 🟦 e a fonte.

## Central de macetes (formato do card)

- Assunto + base ("83 questões analisadas") + selo.
- 🟩 **Padrão da banca**: o que a contagem mostra.
- 🟥 **Macete (IA)**: regra prática, com a fonte legal/gramatical.
- ⚠ **Pegadinha recorrente**: com link **[Ver questões reais relacionadas]**.

## Cronograma via IA — FASE FUTURA

Informo meus horários livres e o sistema monta "o que estudar hoje" cruzando o edital
com revisão espaçada. **Fica para depois das outras fases.** A primeira versão é sem IA:
revisão espaçada simples (revisar o assunto errado em 1, 7 e 30 dias). IA só entra se a
versão simples não bastar, com o teto de gasto que já existe no `gerador.py`.

## Ordem de execução (uma fase por vez, cada uma com commit próprio)

0. **Auditoria de dados** → `docs/auditoria.md`: contagem por matéria de 2013 e 2019
   comparada com os PDFs; gabarito definitivo/retificado aplicado; anuladas marcadas;
   20 questões por prova conferidas à mão; lista das questões com lei desatualizada;
   decidir se a prova de 2016 (Agente Socioeducativo) entra na análise.
1. **Design system**: variáveis CSS (cores, espaçamento, tipografia), cards, selos,
   modo escuro. Primeiro um protótipo HTML estático das telas para eu aprovar.
2. **Navegação nova + home de 5 blocos.**
3. **Tela de questão** focada e relatório pós-simulado.
4. **Meus erros + simulado compilado com os pesos do edital.**
5. **Central de macetes no formato de card.**
6. **Revisão espaçada** e, depois, o cronograma.

Uso principal: **computador** (mas precisa funcionar no celular).

## Critérios de aceite

- A home cabe em uma tela de notebook sem rolar.
- Chego do "abrir o site" ao "responder a primeira questão" em até 2 cliques.
- Todo conteúdo tem selo; todo número tem fonte.
- Nenhuma anulada entra em cálculo nem em simulado.
- `pytest -q` passa.
