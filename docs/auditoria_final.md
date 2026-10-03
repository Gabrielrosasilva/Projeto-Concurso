# Auditoria final integrada (Etapa 8)

Conferência do sistema de ponta a ponta contra a **seção 23 do novo.md**, em
03/10/2026, sobre o código do commit `2052a6b` (fim da 7B) e o banco real
(`data/radar.db`, versão 4). Cada item tem duas evidências:

- **o teste de aceite**, em `tests/test_aceite.py`, com banco de fixture (dado
  fixo, não depende de hoje nem do Windows);
- **o uso real**, com o banco e a configuração de verdade - comando, tela ou
  conta, como está descrito em cada item.

O que não atende está dito, com o motivo, e virou pendência
([pendencias.md](pendencias.md)). A etapa não é dada como concluída "porque
existe código".

## Resumo

| # | Item da §23 | Situação | Evidência |
|---|---|---|---|
| 1 | Exatamente o que ler | ✅ atende | teste `a_ficha_responde[exatamente o que ler]`; ficha real do Art. 5º |
| 2 | Onde ler | ✅ atende | teste `[onde ler]`; ficha real: a CF no Planalto, 🟢 |
| 3 | Como procurar | ✅ atende | teste `[como procurar]`; ficha real: 3 buscas |
| 4 | O que entender | ✅ atende | teste `[o que preciso entender]`; ficha real: 8 itens |
| 5 | O que memorizar | ✅ atende | teste `[o que preciso memorizar]`; ficha real: 5 itens |
| 6 | Quais pegadinhas | ✅ atende | teste `[quais pegadinhas observar]`; ficha real: 3 do acervo, 4 escritas |
| 7 | Como a FEPESE cobrou | ✅ atende | teste `[como a FEPESE cobrou]`; ficha real: alvo e complementar em linhas separadas |
| 8 | Quais questões reais | ✅ atende | teste `[quais questões reais...]`; ficha real: 2013-q31, 2024-q24, 2024-q26 |
| 9 | Quantas questões fazer | ✅ atende | teste `[quantas questões devo fazer]`; ficha real: as 3 faixas do plano |
| 10 | Quais geradas fazer | ✅ atende | teste `[quais questões geradas...]`; ficha real: 0 geradas e o `radar gerar` de cada nó |
| 11 | Quais erros revisar | ✅ atende | teste `[quais erros devo revisar depois]`; ficha real: 0 no radar, 0 no caderno, nunca somados |
| 12 | Por que priorizado hoje | ✅ atende | teste `[por que esse conteúdo...]`; ficha real: o R+7 de 06/10 e cada fator |
| 13 | Selecionar matéria → assunto → subassunto → elemento e gerar sem sair do escopo | ⚠️ atende o mecanismo, **não os dois exemplos com a árvore real** | testes dos dois pedidos na árvore de fixture; no real, os dois caminhos não existem (abaixo) |
| 14 | Números iguais em todas as telas | ✅ atende | teste `os_numeros_sao_iguais_em_todas_as_telas`; real: 28/09 e 29/09, semana 1 e Minhas matérias |
| 15 | Incidência do alvo não muda por prova complementar | ✅ atende | teste `a_incidencia_do_alvo_nao_muda...`; real (numa cópia): 426 linhas iguais com 0 ou 122 provas complementares |
| 16 | Nenhum dado antigo perdido | ✅ atende | teste `nenhum_dado_antigo_e_perdido_na_migracao`; real: contagens contra a cópia de antes da Etapa 2 |
| 17 | ANKI desativado, mas reativável | ✅ atende | teste `o_anki_esta_desativado_e_religa...`; real: `radar hoje` com a config e com uma cópia religada |
| 18 | Nenhuma estatística sem amostra | ⚠️ atende, **com 1 lugar sem a amostra completa** | teste `nenhuma_estatistica_aparece_sem_amostra`; real: 31 aberturas de tela, 114 porcentagens (abaixo) |
| 19 | Nenhuma questão gerada como oficial | ✅ atende | teste `nenhuma_questao_gerada_aparece_como_oficial`; real: as 2 rodadas de IA |

E o roteiro da etapa, além da §23:

| Conferência | Situação |
|---|---|
| Actions verde | ✅ até 02/10 (o `coleta: 2026-10-02` do radar-bot); a primeira execução com o código da 7A, 7B e 8 é a de hoje, e fica para conferir |
| Uso real do backup das 23h30 | ❌ **falhou em todas as execuções registradas** (abaixo) |
| Uso real do caderno de erros | ✅ |
| Uso real da tela Semanas | ✅ |

## 1. A ficha do Art. 5º, incisos I a XVI (itens 1 a 12)

`radar fichas --tema "Art. 5º, caput e incisos I a XVI" --data 2026-10-06`, com
o banco real (a ficha escrita na 6B, ainda **não conferida por você**):

- **por que agora** 📌 "O cronograma de 06/10 traz este tema: R+7 (a volta do
  estudo de 29/09)", e cada fator com número e selo: 🟢 peso no edital (5 de
  100), 🔵 incidência no alvo (1 de 15 da matéria), 🔵 complementar (2 de 34,
  peso 0,25), 🟡 desempenho, tempo e fila, 🟡 prioridade 0,41 (49º de 61);
- **onde ler** 🟢 a Constituição Federal, no Planalto (o link);
- **o que ler** 🟣 "CF, art. 5º: o caput e os incisos I a XVI, no texto
  oficial", e 📌 os 6 artigos-chave do dia;
- **como procurar** 🟣 3 buscas; **entender** 🟣 8 itens; **memorizar** 🟣 5;
- **pegadinhas** 🔵 3 do acervo, cada uma de uma questão real (2013-q31 do
  alvo, conferida; 2024-q24 e 2024-q26 do complementar), e 🟣 4 escritas;
- **como a FEPESE cobrou** 🔵 "Polícia Penal SC: 1 questão · 1 prova" com a
  frase "Não há evidência suficiente no acervo para afirmar isso." para o
  padrão, e "Acervo complementar FEPESE: 2 questões · 2 provas (linha separada,
  nunca somada à do alvo)";
- **questões reais** 🔵 as 3, com o gabarito e o nó;
- **quantas fazer** 📌 Aprendizagem de 15 (29/09, com consulta), R+7 de 10 e
  R+30 de 10 (sem consulta), e "comece pelas 3 reais";
- **geradas** 🟣 0 no conteúdo, e o `radar gerar --pedido` de cada nó;
- **erros** 🟡 0 no radar e 0 no caderno, em duas contas que nunca se somam.

## 2. Gerar com escopo fechado (item 13)

**Os dois exemplos da §23 não existem na árvore real**, e o `radar gerar` faz
o que deve - recusa e sugere, sem alargar:

```
radar gerar --materia "Direito Penal" --assunto "Aplicação da lei penal" --subassunto "Lei penal no tempo" --quantas 20
O assunto 'Aplicação da lei penal' não existe em 'Direito Penal'. Você quis dizer: Imputabilidade penal?
Nada foi gerado: eu nao alargo o escopo sozinho.

radar gerar --materia "Lei de Execução Penal" --assunto "Progressão de regime" --elemento "Art. 112" --quantas 20
O assunto 'Progressão de regime' não existe em 'Lei de Execução Penal'. Os que existem: Lei de Execução Penal (Lei nº 7.210 de 11 de julho de 1984).
Nada foi gerado: eu nao alargo o escopo sozinho.
```

Por quê: a árvore nasce do programa do edital de 2019 e da classificação das
questões reais (decisão 9 e regra inviolável 9: nó não se inventa). O programa
de Direito Penal de 2019 não lista "aplicação da lei penal"; a LEP é um
assunto só ("Lei nº 7.210..."), e as questões do alvo classificadas nela não
deram nó de progressão nem de art. 112 (há "Regimes de cumprimento da pena >
LEP, art. 119").

**O mecanismo funciona**, provado de dois jeitos:

- `tests/test_aceite.py`, numa árvore de fixture com os dois caminhos e um
  vizinho com questão real ao lado de cada um: os 20 pedidos ficam no nó
  pedido, a base real é a do nó, a instrução diz "ESCOPO FECHADO", e a
  resposta da IA com questão do vizinho é recusada na importação;
- no banco real, com os nós mais próximos que existem (o serviço, sem gastar
  nada):

| Escopo pedido (20 questões) | Pedidos | Base real | Todos no escopo |
|---|---|---|---|
| Direito Penal > Tipicidade, ilicitude, culpabilidade, punibilidade > Abolitio criminis (a lei penal no tempo, CP art. 2º) | 7 chamadas | 1 (do complementar) + do zero na fonte oficial do mesmo nó | sim |
| Lei de Execução Penal > Lei nº 7.210 > Regimes de cumprimento da pena | 7 chamadas | 1 (do alvo) + do zero na fonte oficial do mesmo nó | sim |

**Pendência:** criar (ou não) os nós dos dois exemplos é escolha sua - ver
pendências.

## 3. Os seis itens finais (14 a 19)

### Números iguais em todas as telas (14)

Com o banco real, a linha da conta de cada dia, na tela Hoje e no `radar hoje`:

| Dia | Tela Hoje | `radar hoje` |
|---|---|---|
| 28/09 | 31 questões = 13 acertos + 8 erros + 10 de treino de IA | igual |
| 29/09 | 37 questões = 4 acertos + 18 erros + 15 sem acerto anotado | igual |
| 30/09 a 02/10 | nada anotado | nada anotado |

E a semana 1 (28/09 a 03/10): **68 questões = 17 acertos + 26 erros + 15 sem
acerto anotado + 10 de treino de IA** - a mesma linha na tela Semanas, na soma
dos cinco dias e na soma dos cartões de Minhas matérias.

### A incidência do alvo não muda por causa do complementar (15)

Numa cópia do `data/` (o real não foi tocado): o mapa do alvo calculado com
**nenhuma** prova complementar aceita e depois com as **122** aceitas hoje.
As 426 linhas do mapa - questões, denominador, provas, anuladas e pendentes de
cada matéria - ficaram iguais; a linha complementar foi de 0 para 782 questões,
ao lado.

### Nenhum dado antigo perdido (16)

As tabelas do banco real contra a cópia feita pela migração da Etapa 2
(`data/copias/migracao-v0-para-v1-2026-10-01-163540/radar.db`, 01/10, 16h35):

| Tabela | Antes da Etapa 2 | Hoje |
|---|---|---|
| concursos | 2.848 | 2.848 |
| questoes | 8.433 | 8.433 |
| questoes_geradas | 50 | 50 |
| eventos | 58 | 58 |
| simulados | 4 | 4 |
| respostas_de_simulado | 80 | 80 |
| registros_de_estudo | 2 | 2 |
| estados_do_dia | 2 | 2 |
| erros_anotados | 2 | 2 |
| conteudos, classificacoes, versao_do_banco | não existiam | 426, 402, 1 |

Nenhuma linha a menos. (As outras pastas `migracao-v0-*` de `data/copias/`
são cópias de bancos de teste, decisão 50.)

### ANKI desativado, mas reativável (17)

`radar hoje --data 2026-10-05` com a `config/` real escreve **"ANKI
temporariamente desativado"**; com uma cópia da `config/` em que a chave diz
`anki: ativado` (pelo `RADAR_CONFIG_DIR`), a faixa volta: **"22:00-22:15 Anki ·
Anki [1] Direito Penal"**. A `config/` real não foi alterada.

### Nenhuma estatística sem amostra (18)

A regra da varredura da 7A aplicada às telas com o banco real: 31 aberturas
(as 18 telas da varredura, Hoje de 28 e 29/09, Auditoria, as 4 rodadas e 5
fichas; Macetes da FEPESE e Mais entraram duas vezes) e 114 porcentagens. Sem
a amostra perto, 8 diferentes:

- **6 no gráfico "Quantas questões caem numa prova" dos Macetes**: a fatia
  tem a sua base no centro do gráfico ("N questões da banca"), mas a média
  "8.5/prova" não diz **em quantas provas** - falta metade da amostra.
  **Não atende**, e virou pendência;
- 2 não são estatística: "Apenas 1% dos eleitores" é o texto de uma questão
  (rodada 4), e "no mínimo 50% acima da normal" é o texto da CF (ficha dos
  direitos sociais).

### Nenhuma questão gerada como oficial (19)

As 4 rodadas do banco real: as duas de IA (1 e 2) mostram o 🟣 e "Gerada por
IA: não é questão oficial da FEPESE."; nenhuma escreve "Gabarito definitivo" -
a resposta certa da gerada é "Resposta da IA". As duas reais não têm a frase.

## 4. Além da §23

- **Actions:** o último `coleta:` do radar-bot é de 02/10 (15h13 UTC), e o
  workflow roda o `pytest -q` antes de coletar - ele só commita com a suíte
  verde, no Linux. A primeira execução com o código desta auditoria é a de
  hoje; fica para conferir o `coleta: 2026-10-03`. (O `gh` não está instalado
  no PC: a evidência é o commit do robô.)
- **Backup das 23h30: não funciona.** Os logs de `data/logs/` registram 6
  execuções - 27/09, 29/09, 30/09 (duas), 01/10 e 02/10 - e **todas** falharam
  no primeiro passo, com "cannot pull with rebase: You have unstaged changes":
  o `radar sincronizar` tenta o pull com mudança local no disco e para. A tela
  Mais e o `radar status` avisam a falha, como devem. Virou pendência (A),
  com etapa própria, combinada antes desta auditoria.
- **Caderno de erros, com dado real:** 2 erros anotados, "2 para rever hoje",
  e o "O que mais te derruba" contado nos 2.
- **Semanas, com dado real:** a semana 1 com 68 questões, 17 acertos, 26
  erros, 40% de acerto (sem consulta: 40%), 6h50, 2 erros no caderno e a
  linha da conta igual à das outras telas.
