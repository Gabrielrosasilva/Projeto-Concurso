# SOLICITAÇÃO DE EVOLUÇÃO DO SISTEMA DE ESTUDOS — POLÍCIA PENAL SC (FEPESE)

Quero que você analise o meu projeto como um sistema completo de estudos para concursos e, a partir das informações abaixo, ajuste a arquitetura, as regras e as funcionalidades necessárias.

IMPORTANTE:

Não quero que você trate tudo abaixo como uma lista de sugestões independentes.

Quero que você entenda o objetivo geral do sistema e transforme essas necessidades em uma implementação coerente, confiável e integrada.

Antes de começar a alterar o projeto, analise como o sistema funciona atualmente, quais funcionalidades já existem, quais dados estão disponíveis e como elas se relacionam.

Não crie uma solução paralela se já existir uma estrutura adequada no projeto. Aproveite e evolua o que já existe.

Também não quero que você simplesmente concorde com minhas ideias. Quando alguma ideia minha puder gerar erro, distorção estatística, experiência ruim de estudo ou problema de arquitetura, explique e proponha uma solução melhor.

Os nomes de campos, parâmetros e comandos que aparecem neste documento são exemplos para deixar clara a minha intenção. Se o projeto já tiver convenções próprias de nomes, estrutura de pastas ou tecnologia, siga as convenções do projeto, desde que o comportamento que estou pedindo seja respeitado.

---

## COMO QUERO QUE VOCÊ TRABALHE (PONTOS DE PARADA)

Esta solicitação é grande. Para evitar que muita coisa seja alterada de uma vez sem a minha validação, quero que você trabalhe assim:

1. Primeiro, faça a análise completa da arquitetura atual e monte o plano de etapas (seção 22).
2. Depois de apresentar a análise e o plano, **PARE e aguarde a minha aprovação**. Não altere nenhum arquivo nessa fase.
3. Após a minha aprovação, implemente **uma etapa por vez**.
4. Ao final de cada etapa, **PARE novamente**, mostre o que foi feito (arquivos alterados, testes executados, resultado dos testes, critério de conclusão atendido) e aguarde a minha aprovação antes de começar a próxima.
5. Se durante uma etapa você descobrir algo que muda o plano (um problema maior, uma dependência que não estava prevista, uma estrutura existente que resolve parte do problema), pare e me avise antes de seguir.

Não faça commits que misturem etapas diferentes. Cada etapa deve poder ser revisada separadamente.

---

## REGRAS INVIOLÁVEIS

Estas regras valem para o projeto inteiro. Se algum trecho deste documento parecer contradizer alguma delas, estas regras prevalecem e você deve me avisar da contradição.

1. **Nunca misturar evidências.** A incidência da Polícia Penal SC (concurso-alvo), a incidência do acervo complementar FEPESE e o meu desempenho pessoal são três coisas separadas. Nunca devem ser somadas ou apresentadas como se fossem um único número.
2. **Nunca transformar histórico em previsão.** O sistema mostra o que aconteceu no acervo ("apareceu X vezes em Y provas analisadas"), nunca o que "vai cair".
3. **Toda estatística mostra a amostra.** Exemplo: "8 questões · 2 provas".
4. **Quando não houver dados suficientes**, o sistema deve dizer exatamente: "Não há evidência suficiente no acervo para afirmar isso."
5. **Questão gerada por IA nunca é questão oficial da FEPESE**, e isso deve estar sempre visível.
6. **ANKI fica desativado, mas não é removido.** Nada relacionado ao ANKI deve ser apagado (veja a seção 18).
7. **O período da manhã também deve ter questões.** Não quero manhã só de teoria (veja a seção 18).
8. **Nenhum dado existente pode ser perdido.** Toda mudança de estrutura precisa preservar e migrar o que já existe (veja a seção 21).
9. **Não inventar vínculos ou classificações para cumprir uma regra.** Se não for possível classificar com segurança ou vincular uma questão a uma base real, o sistema deve registrar isso como pendente/sem base, e não forçar uma resposta.
10. **Números iguais em todas as telas.** Todas as telas e relatórios devem ler as métricas da mesma fonte (veja a seção 17).

---

## 1. OBJETIVO CENTRAL DO SISTEMA

Meu sistema está sendo desenvolvido principalmente para me ajudar a estudar para a Polícia Penal de Santa Catarina, tendo como referência a banca FEPESE.

Eu quero que o sistema consiga transformar os dados reais das provas e do edital em um ambiente de estudo realmente útil.

A lógica deve ser:

```
EDITAL
↓
MATÉRIAS
↓
ASSUNTOS
↓
SUBASSUNTOS
↓
ELEMENTO ESPECÍFICO (artigo/dispositivo nas matérias jurídicas; regra, conceito, comando etc. nas demais — veja a seção 14), QUANDO APLICÁVEL
↓
QUESTÕES REAIS DA FEPESE
↓
INCIDÊNCIA E PADRÕES DE COBRANÇA
↓
MEU DESEMPENHO
↓
PRIORIDADE DE ESTUDO
↓
CRONOGRAMA
↓
QUESTÕES DE TREINO
↓
REVISÃO
```

Quero que essas partes conversem entre si.

---

## 2. BASE PRINCIPAL: POLÍCIA PENAL SC

Quero que você verifique especificamente as provas da Polícia Penal/Agente Penitenciário de Santa Catarina aplicadas pela FEPESE em 2013 e 2019.

Quero saber se o sistema está realmente conseguindo extrair corretamente dessas provas:

- questões;
- enunciado e alternativas;
- matéria;
- assunto;
- subassunto, quando possível;
- artigo/dispositivo ou elemento específico, quando aplicável;
- gabarito;
- prova de origem;
- ano;
- cargo;
- número da questão;
- eventuais questões anuladas;
- demais metadados relevantes.

Quero que você faça uma auditoria dessa extração.

Não quero que uma classificação seja considerada correta apenas porque a IA "acha" que ela pertence àquele assunto.

Sempre que possível, a classificação deve estar relacionada ao conteúdo efetivamente cobrado na questão e/ou ao conteúdo programático correspondente do edital.

Quando não for possível classificar uma questão com segurança, ela não deve receber uma classificação forçada. Nesse caso, quero que ela fique marcada com um status como "classificação pendente" ou "precisa de revisão manual", para que eu possa conferir depois. Questões pendentes devem aparecer separadas nas estatísticas, e não entrar silenciosamente em um assunto qualquer.

No resultado da auditoria, quero saber:

- quantas questões foram extraídas de cada prova, comparado com quantas a prova realmente tem;
- quantas estão com classificação completa, parcial ou pendente;
- quantas estão sem gabarito ou com gabarito inconsistente;
- quais questões anuladas foram identificadas;
- quais erros de extração foram encontrados.

---

## 3. MAPA DE INCIDÊNCIA DA POLÍCIA PENAL

Quero que o sistema consiga montar um mapa de incidência específico das provas de 2013 e 2019.

Preciso conseguir visualizar pelo menos:

- incidência por matéria;
- incidência por assunto;
- incidência por subassunto;
- incidência por artigo/dispositivo ou elemento específico, quando aplicável;
- quantidade de questões;
- quantidade de provas em que o assunto apareceu;
- distribuição por ano;
- assuntos recorrentes;
- assuntos que apareceram apenas uma vez;
- assuntos do edital que não apareceram;
- padrão de cobrança;
- tipo de questão;
- eventuais pegadinhas/padrões de formulação identificáveis.

IMPORTANTE:

Não transforme isso em uma previsão absoluta.

Exemplo:

ERRADO:
"A FEPESE vai cobrar o artigo X."

CORRETO:
"O artigo X apareceu X vezes nas provas analisadas."

Também quero que o sistema mostre claramente o tamanho da amostra:

Exemplo:
"8 questões · 2 provas"

ou

"8 ocorrências em 2 provas"

Não quero estatísticas sem contexto.

Questões anuladas e questões com classificação pendente devem ser tratadas de forma explícita: quero saber se elas entram ou não na contagem, e isso deve estar documentado e visível.

---

## 4. SEPARAÇÃO ENTRE CONCURSO-ALVO E BANCO GERAL FEPESE

Quero ampliar o acervo com outras provas da FEPESE para entender melhor o estilo da banca.

Exemplos de matérias que podem possuir bastante material em outros concursos:

- Direito Penal;
- Direito Constitucional;
- Direito Processual Penal;
- Direitos Humanos;
- Administração Pública;
- outras matérias semelhantes.

Mas quero que isso seja feito com uma separação muito clara.

Devem existir pelo menos dois tipos de evidência:

A) EVIDÊNCIA DO CONCURSO-ALVO
Provas específicas da Polícia Penal/Agente Penitenciário de SC.

B) EVIDÊNCIA COMPLEMENTAR DA BANCA
Outras provas da FEPESE que possuem matérias/assuntos semelhantes.

Toda prova e toda questão do acervo devem ter essa origem registrada (alvo ou complementar), de forma que qualquer consulta ou estatística consiga separar as duas.

A evidência complementar pode ser usada para:

- entender padrões de cobrança da FEPESE;
- identificar formas recorrentes de elaboração de questões;
- estudar como determinado assunto costuma ser abordado pela banca;
- aumentar o repertório para geração de questões;
- identificar pegadinhas e formas de formulação.

Porém:

A evidência complementar NÃO deve ser misturada automaticamente com a incidência histórica específica da Polícia Penal.

Por exemplo:

Se um assunto apareceu 2 vezes na Polícia Penal e 30 vezes em outros concursos FEPESE, o sistema não pode apresentar "32 ocorrências na Polícia Penal".

Deve ficar algo semelhante a:

```
Polícia Penal SC:
2 ocorrências em 2 provas.

Acervo complementar FEPESE:
30 ocorrências em X provas.
```

Isso é muito importante para não distorcer o meu mapa de incidência.

Quero testes automatizados que garantam que os números do concurso-alvo não mudam quando uma prova complementar é adicionada.

---

## 5. PESQUISA E IMPORTAÇÃO DE OUTRAS PROVAS FEPESE

Quero que você verifique se é possível ampliar o banco com provas da FEPESE de outros concursos que possuam matérias relevantes.

Nesta solicitação, isso acontece em duas fases:

1. **Levantamento:** primeiro você pesquisa e me apresenta uma lista das provas encontradas, com fonte, matérias, ano e cargo. Nada é importado nessa fase.
2. **Importação:** somente depois que eu aprovar a lista, as provas escolhidas passam pelo processo de importação e validação.

Para cada prova adicionada, preciso manter:

- PDF da prova;
- gabarito;
- banca;
- concurso;
- cargo;
- ano;
- fonte;
- URL ou referência da fonte original;
- data de inclusão;
- tipo de evidência (alvo ou complementar);
- status de validação;
- eventuais questões anuladas.

Não quero simplesmente baixar provas aleatoriamente.

Quero definir critérios para inclusão.

A prova só deve entrar no acervo depois de passar por uma validação mínima. Essa validação deve registrar pelo menos:

- **status da extração (parsing):** se o texto das questões foi extraído corretamente e se a quantidade de questões bate com a prova;
- **integridade do gabarito:** se o gabarito existe, se é o definitivo e se corresponde a todas as questões;
- **identificação do arquivo de origem (hash):** para evitar que a mesma prova seja importada duas vezes, mesmo com nomes de arquivo diferentes.

Se uma prova ou gabarito não puder ser validado, o sistema deve informar isso.

Além disso, quero que você investigue e responda:

1. Quais matérias da Polícia Penal realmente possuem boa quantidade de provas FEPESE complementares?
2. Quais possuem pouco ou nenhum material complementar?
3. Existem provas FEPESE anteriores com LEP?
4. Existem provas FEPESE com Sociologia Aplicada?
5. Existem provas FEPESE com legislação estadual específica relacionada ao sistema prisional de SC?
6. Quais outras matérias possuem acervo suficiente para servir como reforço?

Não presuma que uma matéria é exclusiva da Polícia Penal apenas porque ela aparece pouco em outros concursos.

Verifique isso com base documental.

Depois que as provas estiverem no banco, quero que o sistema consiga responder essas mesmas perguntas por consulta, sem depender de uma nova pesquisa manual.

---

## 6. CLASSIFICAÇÃO HIERÁRQUICA DOS CONTEÚDOS

Quero melhorar o cadastro e a classificação dos conteúdos.

A estrutura deve permitir:

```
MATÉRIA
→ ASSUNTO
→ SUBASSUNTO
→ ARTIGO/DISPOSITIVO OU ELEMENTO ESPECÍFICO, QUANDO APLICÁVEL
```

Exemplo:

```
Direito Penal
→ Aplicação da Lei Penal
→ Lei penal no tempo
→ Art. 2º do Código Penal
```

Outro exemplo:

```
Lei de Execução Penal
→ Execução da pena
→ Progressão de regime
→ Art. 112
```

Outro:

```
Língua Portuguesa
→ Sintaxe
→ Concordância verbal
→ Casos específicos
```

Nem toda matéria terá artigos.

Portanto, o sistema não deve obrigar a existência de artigo. Os níveis abaixo de assunto podem ficar vazios quando não se aplicarem.

Essa hierarquia deve ser desenhada junto com a taxonomia flexível da seção 14, e não separadamente. Não quero uma estrutura feita só para artigos que depois precise ser refeita para as outras matérias.

Quero que essa hierarquia seja usada tanto para estudo quanto para geração de questões, análise e cronograma.

---

## 7. NOVO FILTRO PARA GERAÇÃO DE QUESTÕES

Esse é um requisito MUITO importante.

Hoje eu consigo fazer algo parecido com:

```
radar gerar --pedido --materia "Lei de Execução Penal" --quantas 20
```

O problema é que isso é amplo demais.

Se eu pedir "Lei de Execução Penal", existem inúmeros assuntos e artigos possíveis.

Posso acabar recebendo questões de conteúdos que ainda nem estudei.

Quero criar filtros mais específicos.

Por exemplo:

```
radar gerar --pedido --materia "Lei de Execução Penal" --assunto "Progressão de regime" --quantas 20
```

Ou:

```
radar gerar --pedido --materia "Direito Penal" --assunto "Aplicação da Lei Penal" --subassunto "Lei penal no tempo" --quantas 20
```

Ou, quando aplicável:

```
radar gerar --pedido --materia "Direito Penal" --assunto "Aplicação da Lei Penal" --artigos "1,2,3" --quantas 20
```

Quero que você projete a melhor estrutura para isso.

Não precisa necessariamente usar exatamente esses nomes de parâmetros.

Pode propor uma estrutura melhor.

O importante é existir um filtro hierárquico e preciso.

Atenção:

- A consulta ampla só por matéria **não deve ser removida**. Ela continua sendo útil, por exemplo, para simulados. O que muda é que ela não pode ser confundida com um treino específico (veja a seção 8).
- Se eu informar um filtro que não existe no banco (um assunto com nome errado, por exemplo), o sistema deve me avisar e, se possível, sugerir os nomes existentes, em vez de gerar questões de outra coisa.
- O filtro deve funcionar também para os elementos específicos das matérias não jurídicas (seção 14), e não apenas para artigos.

---

## 8. REGRA PARA GERAÇÃO DE QUESTÕES

Quero três modos diferentes:

MODO 1 — TREINO ESPECÍFICO

O usuário informa:

- matéria;
- assunto;
- opcionalmente subassunto;
- opcionalmente artigo/dispositivo ou elemento específico;
- quantidade.

Nesse modo, a IA deve gerar questões SOMENTE dentro daquele escopo.

MODO 2 — REVISÃO

O sistema seleciona apenas conteúdos que eu já estudei anteriormente.

Exemplo:

"Gerar 20 questões de Direito Constitucional somente dos assuntos que já estudei."

Para isso, o sistema precisa ter um registro confiável de quais conteúdos eu já estudei (seção 19). Se esse registro ainda não existir no projeto, ele deve ser criado antes deste modo. Quero que você me diga como o sistema define que um conteúdo foi "estudado".

MODO 3 — SIMULADO

Pode utilizar uma abrangência muito maior de conteúdos, respeitando o edital, o peso das matérias e as regras do simulado.

Isso impede que uma seleção ampla de matéria seja confundida com um treino específico.

Quero testes que confirmem que, no modo Treino Específico, nenhuma questão fora do escopo informado é gerada.

---

## 9. REGRA DE OURO PARA QUESTÕES GERADAS

Toda questão gerada deve, sempre que possível, informar sua base.

A geração deve considerar prioritariamente:

1. questões reais da FEPESE;
2. assuntos realmente cobrados pela FEPESE;
3. legislação/fonte oficial correspondente;
4. padrão de formulação da banca.

Não quero que a IA simplesmente invente perguntas genéricas sobre o assunto.

Quando houver questões reais relacionadas, quero que o sistema consiga armazenar a relação:

```
QUESTÃO GERADA
↓
QUESTÃO REAL DE REFERÊNCIA
↓
PROVA
↓
ANO
↓
GABARITO
↓
FONTE/LEGISLAÇÃO
```

Quando não houver questão real relacionada (o que pode acontecer, por exemplo, em algumas partes de Português, Raciocínio Lógico ou Informática), a questão pode ser gerada a partir da fonte oficial ou do conteúdo do edital, mas deve ficar registrado claramente que ela **não tem questão real de referência**. O sistema nunca deve inventar um vínculo com uma questão real só para preencher esse campo.

Também deve ficar registrado se a base usada foi do concurso-alvo ou do acervo complementar.

A questão gerada nunca deve ser tratada como questão oficial da FEPESE, e isso deve aparecer visualmente em todas as telas onde ela for exibida (🟣, seção 20).

---

## 10. CRONOGRAMA — PRINCIPAL PROBLEMA ATUAL

Essa é atualmente uma das minhas maiores dores.

Hoje o sistema pode mostrar algo como:

"Art. 5º, caput e incisos I a XVI"

E depois apresentar uma explicação enorme sobre:

- igualdade;
- legalidade;
- tortura;
- manifestação do pensamento;
- liberdade de crença;
- intimidade;
- casa;
- comunicações;
- profissão;
- informação;
- locomoção;
- reunião etc.

O problema é que isso ainda não me diz claramente:

"O que exatamente eu devo fazer agora?"

Se eu pegar apenas:

"Art. 5º, caput e incisos I a XVI"

e jogar isso no YouTube, posso encontrar conteúdo demais ou não encontrar uma aula exatamente com esse título.

Quero que o cronograma deixe de ser apenas uma lista de assuntos e se torne um INSTRUMENTO OPERACIONAL DE ESTUDO.

---

## 11. FORMATO IDEAL DE CADA TAREFA DO CRONOGRAMA

Para cada bloco de estudo, quero que o sistema informe claramente:

1. O QUE ESTUDAR
2. QUAL PARTE EXATA ESTUDAR
3. ONDE ESTUDAR
4. COMO ENCONTRAR O CONTEÚDO
5. QUAIS PALAVRAS PESQUISAR
6. QUAIS ARTIGOS/DISPOSITIVOS LER
7. QUAIS PONTOS PRECISO DOMINAR
8. QUAIS PEGADINHAS OBSERVAR
9. COMO A FEPESE costuma abordar aquele conteúdo no acervo analisado
10. QUANTAS QUESTÕES FAZER DEPOIS
11. DE QUAIS ASSUNTOS
12. COMO REVISAR OS ERROS

Exemplo de saída desejada:

```
DIREITO CONSTITUCIONAL

Tema:
Direitos e Garantias Fundamentais

Estudar hoje:
Art. 5º, caput e incisos I a XVI.

Por que agora:
[fatores de prioridade utilizados — seção 15]

Fonte principal:
Constituição Federal — fonte oficial.

Como pesquisar:
"Artigo 5 Constituição Federal direitos e garantias fundamentais"
"Artigo 5 incisos I a XVI explicado"
"Direitos fundamentais artigo 5 FEPESE"

Leitura obrigatória:
Caput + incisos I a XVI.

Você precisa saber:
[lista objetiva]

Atenção:
[pegadinhas identificadas]

Padrão FEPESE:
[com base nas questões reais analisadas, sempre com a amostra]

Questões reais relacionadas:
[lista das questões do acervo]

Questões após o estudo:
10 questões sobre exatamente esse conteúdo.

Revisão:
[quando e em que condições esse conteúdo volta para revisão]
```

Isso deve ser aplicado a todos os conteúdos do cronograma.

### Estrutura única de dados da tarefa

Para que todas as telas e funções usem o mesmo formato, quero que cada tarefa do cronograma siga **uma única estrutura de dados**. Não quero duas versões diferentes desse formato no sistema. Os nomes abaixo são uma proposta e podem ser adaptados às convenções do projeto, mas o conteúdo de cada campo deve ser este:

| Campo | O que representa |
|---|---|
| `subject` | Matéria do edital. |
| `topic` | Assunto do edital. |
| `subtopic` | Subassunto, quando houver. |
| `specific_element` | Elemento específico a estudar (ex.: "Art. 5º, caput e incisos I a XVI"; em Português, uma regra; em Informática, um recurso etc. — seção 14). |
| `element_type` | Tipo do elemento (artigo, súmula, regra gramatical, tipo de problema, comando, tratado etc.). |
| `why_now` | Fatores que levaram essa tarefa a ser priorizada (seção 15). |
| `source_material` | Fonte principal de estudo, com a sua classificação de confiabilidade (🟢🔵🟡🟣). |
| `read_exactly` | O que ler exatamente (dispositivos, trechos, páginas). |
| `search_queries` | Termos exatos para pesquisar no YouTube/Google. |
| `must_understand` | Conceitos que preciso entender. |
| `must_memorize` | O que preciso memorizar (prazos, exceções, listas etc.). |
| `fepese_traps` | Pegadinhas identificadas no acervo. |
| `fepese_pattern` | Como a FEPESE cobrou esse conteúdo, separando alvo e complementar e mostrando a amostra. Se não houver dados, usar a frase padrão de evidência insuficiente. |
| `related_real_questions` | Questões reais do acervo relacionadas ao conteúdo. |
| `practice_target` | Quantas questões fazer e de qual escopo exato (quantas do elemento específico e quantas do assunto em geral). |
| `review_trigger` | Condições que colocam esse conteúdo de volta em revisão (ex.: erro, baixa taxa de acerto, tempo desde a última revisão). |

---

## 12. O SISTEMA NÃO DEVE ME DEIXAR "PERDIDO" SOBRE O QUE ESTUDAR

Quero que a IA transforme um conteúdo jurídico amplo em uma tarefa executável.

Exemplo:

NÃO:

"Estude Lei de Execução Penal."

NÃO:

"Estude Execução da Pena."

SIM:

"Leia os arts. X a Y."
"Entenda estes tópicos."
"Pesquise usando estes termos."
"Observe estas diferenças."
"Depois faça 15 questões sobre estes subassuntos."

Quero que cada tarefa tenha um começo, meio e fim.

O mesmo vale para as matérias que não são jurídicas.

---

## 13. PADRÕES DE COBRANÇA DA FEPESE

Quero que o sistema utilize o acervo para identificar padrões como:

- assuntos mais cobrados;
- artigos recorrentes;
- forma de elaboração das alternativas;
- pegadinhas recorrentes;
- confusões conceituais;
- palavras ou expressões frequentemente utilizadas;
- nível de literalidade;
- necessidade de interpretação;
- comparação entre conceitos;
- cobrança direta de legislação;
- outras características identificáveis.

Mas essas conclusões precisam ser apresentadas como:

"Padrão identificado no acervo analisado."

E não como:

"A FEPESE sempre faz isso."

Nem:

"A FEPESE certamente fará isso na próxima prova."

Todo padrão deve indicar em quantas questões e em quantas provas ele foi observado, e se veio do concurso-alvo ou do acervo complementar.

---

## 14. MAPEAMENTO DOS CONTEÚDOS MAIS RELEVANTES DO EDITAL (TAXONOMIA FLEXÍVEL)

Não quero limitar essa análise aos artigos de matérias jurídicas.

Minha necessidade é identificar os conteúdos mais relevantes de TODAS as matérias do edital da Polícia Penal.

O sistema deve fazer uma análise granular:

```
MATÉRIA
→ ASSUNTO
→ SUBASSUNTO
→ ELEMENTO ESPECÍFICO COBRADO
→ QUESTÕES RELACIONADAS
→ INCIDÊNCIA
→ PADRÃO DE COBRANÇA
→ MEU DESEMPENHO
```

O "elemento específico" deve variar de acordo com a natureza da matéria.

Exemplos:

**DIREITO E LEGISLAÇÃO:**
pode ser artigo, inciso, parágrafo, súmula, doutrina, conceito jurídico, instituto, exceção, prazo, competência, procedimento ou diferença entre conceitos.

**LÍNGUA PORTUGUESA:**
pode ser regra gramatical, classificação, estrutura sintática, tipo/padrão de interpretação, figura de linguagem, concordância, regência, crase etc.

**RACIOCÍNIO LÓGICO E MATEMÁTICA:**
pode ser tipo de problema, conceito lógico, proposição, tabela-verdade, equivalência, negação, propriedade, forma de resolução, porcentagem, análise combinatória etc.

**INFORMÁTICA:**
pode ser conceito, ferramenta, comando, atalho, recurso, protocolo, função, configuração ou tecnologia específica.

**DIREITOS HUMANOS:**
pode ser tratado, convenção, princípio, conceito, artigo/dispositivo, classificação, contexto histórico ou entendimento específico.

**SOCIOLOGIA APLICADA:**
pode ser autor, teoria sociológica, conceito, princípio ou contexto histórico.

PORTANTO:

Não quero que o sistema tente aplicar a mesma estrutura de classificação para todas as matérias.

Quero uma taxonomia flexível, capaz de representar o que realmente está sendo cobrado em cada disciplina.

Essa taxonomia faz parte da estrutura de conteúdos e deve ser implementada na mesma etapa da hierarquia (seção 22, Etapa 2). Os tipos de elemento listados acima são exemplos iniciais: a lista deve poder ser ampliada sem alterar a estrutura do banco.

### OBJETIVO

Para cada matéria e assunto do edital, quero descobrir:

1. Quais conteúdos específicos aparecem nas provas analisadas;
2. Quantas questões abordaram cada conteúdo;
3. Em quantas provas esse conteúdo apareceu;
4. Em quais anos apareceu;
5. Como a FEPESE cobrou esse conteúdo;
6. Quais variações de cobrança foram encontradas;
7. Quais conceitos aparecem associados;
8. Quais conteúdos parecem possuir maior recorrência no acervo;
9. Quais conteúdos ainda não possuem amostra suficiente;
10. Meu desempenho naquele conteúdo.

### IMPORTANTE SOBRE INCIDÊNCIA

Não quero que o sistema transforme ocorrência histórica em previsão.

Exemplo:

ERRADO:
"Esse conteúdo certamente cairá."

CORRETO:
"Esse conteúdo apareceu X vezes em Y provas analisadas."

Também quero distinguir, para cada elemento específico:

- **incidência no concurso-alvo** (Polícia Penal SC 2013 e 2019): ocorrências e provas de origem;
- **incidência no acervo complementar FEPESE**: ocorrências em outros concursos da banca;
- **meu desempenho pessoal**: total respondido, taxa de acerto e estado da amostra (seção 16).

Esses dados não devem ser misturados.

### RELAÇÃO COM O CRONOGRAMA

Esse mapeamento deve alimentar diretamente o cronograma.

O sistema deve conseguir transformar:

```
EDITAL
→ MATÉRIA
→ ASSUNTO
→ CONTEÚDO ESPECÍFICO
→ PRIORIDADE
→ TAREFA DE ESTUDO
→ QUESTÕES
→ REVISÃO
```

Exemplo:

```
Direito Constitucional
→ Direitos e Garantias Fundamentais
→ Art. 5º
→ Incisos I a XVI
```

A tarefa não deve simplesmente dizer:

"Estude Art. 5º."

Ela deve identificar exatamente:

- quais partes estudar;
- quais conceitos dominar;
- quais conteúdos possuem incidência;
- quais pontos apresentam maior relevância dentro do acervo;
- quais questões reais estão relacionadas;
- quais questões devo fazer depois;
- quais pegadinhas/padrões de cobrança devem ser observados.

O mesmo princípio deve existir para TODAS as matérias, usando a estrutura única de tarefa da seção 11.

### REGRA FUNDAMENTAL

Quero que o sistema seja capaz de responder:

"Dentro deste assunto do edital, exatamente o que eu preciso estudar?"

E não apenas:

"Qual é o nome do assunto?"

Essa granularidade é essencial para que o cronograma seja realmente executável.

---

## 15. CRONOGRAMA + DESEMPENHO

O cronograma não deve ser estático.

Quero que ele consiga considerar:

- peso da matéria no edital;
- incidência histórica;
- quantidade de provas;
- quantidade de questões;
- desempenho pessoal;
- quantidade de questões que já respondi;
- quantidade de erros;
- assuntos ainda não estudados;
- assuntos estudados mas com baixo desempenho;
- necessidade de revisão.

Mas tudo isso deve ser tratado como uma regra de priorização, não como previsão de prova.

Quero que o sistema consiga explicar:

"Você está estudando este assunto agora porque..."

e apresente os fatores utilizados.

A incidência usada na priorização deve ser a do concurso-alvo. Se o acervo complementar também for usado, isso deve aparecer separado na explicação, com um peso menor e declarado.

Quero que a regra de priorização seja documentada (quais fatores, qual peso de cada um), para que eu possa entender e ajustar.

---

## 16. AMOSTRA E CONFIABILIDADE

Toda estatística precisa considerar o tamanho da amostra.

Não quero que o sistema diga:

"Você é muito fraco em X"

porque respondeu apenas 1 ou 2 questões.

Quero estados como:

- Amostra insuficiente;
- Em aprendizado;
- Desempenho consistente;
- Precisa revisar;
- Bom desempenho com amostra suficiente.

Os limites precisam ser definidos tecnicamente.

Antes de aplicar esses limites, quero que você me proponha os valores (por exemplo, quantas questões mínimas e qual taxa de acerto definem cada estado), explique o motivo de cada um e deixe esses valores documentados e fáceis de ajustar em um único lugar.

---

## 17. ERRO DE CONTAGEM — 28/09

Existe atualmente um problema importante.

No registro do dia 28/09 aparece algo semelhante a:

"Fiz hoje: 31 questões · 13 acertos · 8 erros · 3h50 de estudo"

Porém:

13 acertos + 8 erros = 21 questões.

Isso indica uma inconsistência de dados.

Quero que você investigue a origem desse problema.

Não quero apenas corrigir a tela.

Quero descobrir:

- de onde vem o número total de questões;
- de onde vêm acertos;
- de onde vêm erros;
- se existem outros status;
- se existem questões anuladas;
- se existem questões não respondidas ou em branco;
- se existem sessões não finalizadas;
- se uma mesma sessão ou questão está sendo contabilizada duas vezes;
- se os gráficos usam uma fonte diferente;
- se o resumo diário usa uma fonte diferente;
- se existe algum problema de agregação;
- se existe algum problema de data/fuso horário que faça registros caírem no dia errado.

Depois, crie uma regra única e confiável para a contabilização.

Essa regra deve existir em **um único lugar do sistema (uma única fonte de verdade)**, e todas as telas e relatórios devem ler dela, em vez de cada um fazer a sua própria conta.

O sistema nunca deve apresentar números conflitantes entre:

- tela "Hoje";
- histórico;
- gráficos;
- estatísticas;
- desempenho;
- relatórios;
- análise de matérias;
- análise de assuntos.

Quero testes automatizados para impedir que esse problema volte a acontecer. Esses testes devem garantir, no mínimo, que:

```
Total = Acertos + Erros + (outros estados válidos que você identificar)
```

e que o mesmo período mostra o mesmo número em todas as telas listadas acima.

IMPORTANTE:

Não assuma que "questões = acertos + erros" se o sistema possuir outros estados válidos.

Primeiro descubra todos os estados existentes e depois defina a regra correta.

Também quero saber se os dados já gravados (incluindo o dia 28/09) precisam ser corrigidos. Se sim, me mostre o que será corrigido antes de alterar qualquer registro.

---

## 18. ROTINA DE ESTUDO

Eu não quero usar ANKI neste momento.

Deixe o ANKI no sistema, mas com essa parte da experiência desativada por enquanto, sem destruir a possibilidade de ativá-la futuramente. Pode deixar minimizado e só com o texto "ANKI temporariamente desativado".

Isso significa:

- não apagar código, dados, configurações ou integrações do ANKI;
- apenas desativar e esconder, de forma que reativar seja simples;
- me dizer exatamente como reativar no futuro.

Não quero que ANKI seja considerado uma etapa obrigatória do cronograma.

Também quero avaliar uma mudança na distribuição dos estudos.

Minha preferência atual é que o período da manhã também tenha questões, em vez de concentrar quase tudo em leitura de teoria.

Quero que você analise a estrutura atual e proponha uma distribuição mais eficiente entre:

- teoria;
- leitura de legislação;
- questões;
- correção;
- revisão.

Não quero simplesmente adicionar mais conteúdo ao meu dia.

Quero uma estrutura que seja sustentável e que priorize retenção e prática.

Me apresente a proposta de distribuição antes de alterá-la no sistema.

---

## 19. ESTUDO SEM ANKI

Como não vou utilizar ANKI neste momento, quero que o próprio sistema consiga controlar:

- conteúdos estudados;
- conteúdos ainda não estudados;
- erros;
- assuntos que precisam de revisão;
- artigos/elementos que precisam ser revisitados;
- questões que devo refazer;
- data da última revisão de cada conteúdo;
- taxa de acerto por assunto/subassunto;
- evolução por assunto.

Esse controle deve ser baseado no meu desempenho real nas sessões e deve alimentar o modo Revisão (seção 8) e o gatilho de revisão do cronograma (`review_trigger`, seção 11).

Posteriormente poderemos adicionar ANKI novamente.

---

## 20. FONTES E CONFIABILIDADE

Toda informação importante deve possuir uma origem identificável.

Quero diferenciar:

- 🟢 Fonte oficial (legislação, edital)
- 🔵 Estatística do acervo (base de questões reais)
- 🟡 Análise automática (métricas calculadas pelo sistema)
- 🟣 Conteúdo gerado por IA (questões, resumos, explicações sintéticas)

Não quero que conteúdo gerado pela IA seja apresentado como se fosse uma informação oficial da FEPESE.

Quando for uma informação jurídica, quero priorizar fonte oficial.

Quando for uma estatística, quero mostrar a amostra.

Quando for uma conclusão baseada em padrão, quero informar que é uma análise do acervo.

Quando não houver dados suficientes para uma estatística, padrão ou conclusão, o sistema deve exibir exatamente:

"Não há evidência suficiente no acervo para afirmar isso."

Essa classificação não deve ser apenas visual: ela deve estar registrada nos dados, para que qualquer tela consiga exibi-la corretamente.

---

## 21. PRESERVAÇÃO DOS DADOS EXISTENTES E MIGRAÇÃO

O sistema já está funcionando e já possui dados meus: questões, sessões, histórico, desempenho e cronograma.

Por isso:

- antes de qualquer alteração na estrutura do banco, faça uma cópia de segurança dos dados;
- toda mudança de estrutura deve vir com uma migração que leve os dados atuais para o novo formato;
- nenhum histórico de desempenho pode ser perdido ou recalculado de forma silenciosa;
- se algum dado antigo não puder ser encaixado na nova hierarquia, ele deve ficar marcado como pendente, e não ser descartado;
- depois da migração, quero uma conferência mostrando que os totais antes e depois batem (ou explicando exatamente por que mudaram, como no caso da correção do erro de 28/09);
- se possível, a migração deve poder ser desfeita.

---

## 22. O QUE EU QUERO QUE VOCÊ FAÇA AGORA

Antes de modificar o projeto, faça uma análise completa da arquitetura atual.

Depois, organize as alterações nas etapas abaixo. A ordem foi pensada para respeitar as dependências: cada etapa usa o que foi construído nas anteriores.

**ETAPA 0 — Análise e plano (sem alterar nada)**
Análise da arquitetura atual, das funcionalidades existentes e dos dados disponíveis. Apresentação do plano detalhado das etapas seguintes. Além do novo.md, considere o CLAUDE.md, docs/historico.md, docs/decisoes.md e docs/pendencias.md. Aponte qualquer conflito entre o novo.md e as decisões já registradas, e indique quais pendências se sobrepõem às etapas do novo.md. Aqui você PARA e aguarda a minha aprovação.

**ETAPA 1 — Correções críticas**
Investigação e correção do erro de contagem de 28/09 (seção 17) e criação da fonte única de verdade para as métricas. Vem primeiro porque todas as estatísticas, o desempenho e o cronograma dependem de números confiáveis.

**ETAPA 2 — Estrutura de conteúdos**
Hierarquia matéria → assunto → subassunto → elemento específico (seção 6), taxonomia flexível por disciplina (seção 14), status de classificação pendente (seção 2), registro de alvo/complementar (seção 4) e migração dos dados existentes (seção 21).

**ETAPA 3 — Banco e análise FEPESE**
Auditoria da extração das provas de 2013 e 2019 (seção 2), mapa de incidência do concurso-alvo (seção 3), separação entre alvo e complementar (seção 4), levantamento e processo de importação e validação de outras provas FEPESE (seção 5) e padrões de cobrança (seção 13).

**ETAPA 4 — Estatísticas, desempenho e controle de estudo**
Estados de amostra e seus limites (seção 16), desempenho por conteúdo, controle de estudo e revisão sem ANKI (seção 19) e desativação do ANKI sem remoção (seção 18). Vem antes da geração de questões e do cronograma porque os dois dependem de saber o que eu já estudei e como estou indo.

**ETAPA 5 — Geração de questões**
Filtro hierárquico (seção 7), os três modos (seção 8) e a rastreabilidade das questões geradas (seção 9).

**ETAPA 6 — Cronograma e rotina**
Cronograma operacional com a estrutura única de tarefa (seções 10, 11, 12 e 14), priorização explicada (seção 15) e nova distribuição da rotina de estudo (seção 18).

**ETAPA 7 — UX e confiabilidade visual**
Indicadores 🟢🔵🟡🟣, frase padrão de evidência insuficiente (seção 20), exibição separada de alvo/complementar/desempenho e marcação de questões geradas por IA.

**ETAPA 8 — Auditoria final integrada**
Verificação de ponta a ponta de todo o sistema contra os critérios de aceite da seção 23.

Os testes **não ficam para o final**: cada etapa deve ter seus próprios testes, criados e executados dentro dela. A Etapa 8 serve para verificar se tudo funciona em conjunto.

Para cada etapa informe:

- objetivo;
- arquivos envolvidos;
- comportamento atual;
- problema;
- solução proposta;
- dependências;
- implementação;
- testes necessários;
- resultado dos testes;
- critério para considerar a etapa concluída.

Não marque uma etapa como concluída apenas porque existe código relacionado a ela.

Verifique se ela realmente atende ao objetivo.

Se, ao analisar o projeto, você concluir que outra ordem de etapas é melhor, explique o motivo antes de mudar.

---

## 23. CRITÉRIOS DE ACEITE

Ao final, quero conseguir fazer algo semelhante a:

"Hoje preciso estudar Direito Constitucional → Direitos Fundamentais → Art. 5º → incisos I a XVI."

O sistema deve me dizer:

- exatamente o que ler;
- onde ler;
- como procurar;
- o que preciso entender;
- o que preciso memorizar;
- quais pegadinhas observar;
- como a FEPESE cobrou esse conteúdo;
- quais questões reais estão relacionadas;
- quantas questões devo fazer;
- quais questões geradas posso fazer;
- quais erros devo revisar depois;
- por que esse conteúdo foi priorizado hoje.

E eu quero conseguir selecionar:

```
Matéria
→ Assunto
→ Subassunto
→ Artigo/elemento específico, quando aplicável
```

para gerar questões específicas.

Exemplo:

```
20 questões
Direito Penal
Aplicação da Lei Penal
Lei penal no tempo
```

ou:

```
20 questões
LEP
Progressão de regime
Art. 112
```

sem receber questões aleatórias de outras partes da matéria.

Além disso:

- os números de questões, acertos e erros devem ser iguais em todas as telas;
- a incidência do concurso-alvo nunca deve mudar por causa de provas complementares;
- nenhum dado antigo pode ter sido perdido;
- o ANKI deve estar desativado, mas reativável;
- nenhuma estatística pode aparecer sem amostra;
- nenhuma questão gerada pode aparecer como oficial.

---

## 24. MUITO IMPORTANTE SOBRE NOVAS SUGESTÕES

Não implemente automaticamente uma ideia nova apenas porque parece interessante.

Primeiro diferencie:

A) requisito que estou solicitando;
B) correção necessária;
C) melhoria técnica necessária;
D) sugestão nova sua.

Para qualquer sugestão nova de arquitetura ou funcionalidade, explique:

- problema resolvido;
- benefício;
- impacto;
- complexidade;
- se é realmente necessária agora;
- se pode ficar para uma fase posterior.

Minha prioridade é:

1. confiabilidade dos dados;
2. precisão do conteúdo;
3. rastreabilidade das informações;
4. qualidade do cronograma;
5. qualidade da geração de questões;
6. desempenho e estatísticas;
7. experiência de uso;
8. funcionalidades extras.

Não quero aumentar a complexidade do sistema sem necessidade.

---

## 25. REGRA FINAL

Meu objetivo não é ter um sistema bonito que apenas mostra informações.

Quero um sistema que realmente funcione como um assistente de preparação para o concurso.

O sistema deve conseguir responder:

"O que eu devo estudar hoje?"

"Exatamente o que devo estudar?"

"De onde devo estudar?"

"Como devo procurar esse conteúdo?"

"Por que estou estudando isso?"

"Como a FEPESE já cobrou isso?"

"Quais são as pegadinhas?"

"Quantas questões devo fazer?"

"Quais questões devo fazer?"

"Quais erros preciso revisar?"

"Por que esse assunto tem prioridade?"

"E de onde veio essa informação?"

O sistema pode sugerir.

O sistema pode analisar.

O sistema pode calcular.

O sistema pode gerar questões.

Mas ele nunca deve apresentar como certeza algo que o acervo não consegue sustentar.

Quando os dados forem insuficientes, o sistema deve dizer claramente:

"Não há evidência suficiente no acervo para afirmar isso."

Essa regra é mais importante do que tentar parecer inteligente.
