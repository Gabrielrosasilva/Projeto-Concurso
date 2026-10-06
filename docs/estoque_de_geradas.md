# O estoque de questões geradas (até 07/11/2026)

Questões de treino escritas pelo Claude Code, com os seus créditos, para os
conteúdos que as faixas de treino usam até o simulado de 07/11 - **sem chave da
API e sem gastar nada**. O caminho é sempre o mesmo: `radar gerar --pedido` →
o Claude Code escreve a resposta → `radar gerar --importar`. Nunca use
`--valendo`.

As regras que não mudam (o porquê está no `decisoes.md`, 35, 36, 40, 72 e 73):

- **questão gerada treina e nunca mede.** Ela serve ao treino rápido (/geradas)
  e à lista de geradas da ficha do tema; nunca entra em diagnóstico, simulado,
  incidência ou acerto das reais;
- **a base segue a prioridade da §9:** questão real do mesmo nó (alvo antes do
  complementar aceito) → fonte oficial → item do edital. Com questão real, o
  radar pede variação (até 3 por questão); o que faltar sai do zero DENTRO do
  nó, marcado "sem questão real de referência". O radar faz essa divisão
  sozinho, e nunca inventa vínculo com questão real;
- **matéria, assunto e subassunto:** cada lote é UM nó de subassunto, e a
  gerada grava a matéria, o assunto e o caminho inteiro do nó (`conteudo`);
- **procedência:** a importação grava "Claude Code, importado manualmente, em
  DD/MM/AAAA" em cada questão. Em Direito, cada questão cita o dispositivo; em
  Português e Raciocínio Lógico, a regra;
- **o registro é o `data/questoes_geradas.json`**, versionado. A importação o
  exporta do banco real; antes de cada commit, confira que ele não ficou vazio
  (decisão 40).

## Antes de começar

Tudo no **terminal do VS Code, em PowerShell**, na pasta do projeto:

```powershell
cd "C:\Projeto concurso claude\Projeto-Concurso"
```

O `.\radar.bat` chama o radar do ambiente virtual sem precisar ativá-lo. No Git
Bash ele falha por causa do espaço no caminho da pasta; use o PowerShell (ou
`.\.venv\Scripts\radar.exe`, que funciona nos dois).

## Um lote, passo a passo

Um lote é um nó. Faça um de cada vez: **importe e faça o commit antes do próximo
`--pedido`**, porque o pedido novo substitui o anterior e a resposta de um lote
velho é recusada.

**1. Gerar o pedido** - o comando do lote, da lista abaixo. Exemplo (o lote 1):

```powershell
.\radar.bat gerar --pedido --modo treino --materia "Direito Penal" --assunto "Tipicidade, ilicitude, culpabilidade, punibilidade" --subassunto "Abolitio criminis" --quantas 19
```

Os parâmetros (`.\radar.bat gerar --help`): `--modo` (treino | revisao |
simulado), `--materia`, `--assunto`, `--subassunto`, `--elemento` (repetível: um
dispositivo, regra ou tipo de problema do nó) e `--quantas` (padrão 5). Nome que
a árvore não tem para o comando, com sugestões; `.\radar.bat conteudos` lista a
árvore. A saída diz quantos pedidos foram para `data\pedido_ia.json`, o escopo
fechado, de onde sai cada questão ("3 questão(ões) de questao_real
(complementar)", "16 questão(ões) de fonte_oficial, sem questão real de
referência") e o número do lote.

**2. Os dois arquivos.** `data\pedido_ia.json` é escrito pelo passo 1;
`data\resposta_ia.json`, pelo Claude Code. Os dois ficam fora do git (estão no
`.gitignore`).

**3. No Claude Code do VS Code, cole:**

> Responda o pedido do radar. Leia data\pedido_ia.json e siga o campo como_responder: para cada item de pedidos, siga a instrucao usando o texto de pedido e escreva no máximo `quantas` questões. Cada questão com enunciado, as 5 alternativas (a até e), resposta, artigo (em Direito, o dispositivo exato, como "CP, art. 2º, parágrafo único"; em Português e Raciocínio Lógico, a regra) e conteudo copiado igual ao CONTEUDO do pedido (se o CONTEUDO listar mais de um caminho, o da questão). Na variação, mantenha a regra da questão real e troque o cenário e os números; no do_zero, escreva só dentro do CONTEUDO, a partir da FONTE OFICIAL, sem vínculo com questão real. Se não tiver certeza do dispositivo, não escreva a questão. Salve tudo num único JSON, no formato de formato_da_resposta e com o mesmo lote, em data\resposta_ia.json. Não rode comandos do radar e não altere nenhum outro arquivo.

**4. Importar:**

```powershell
.\radar.bat gerar --importar data\resposta_ia.json
```

Como ler a saída:

- **"N questão(ões) gravado(s)"** - as que entraram;
- **"Procedencia: Claude Code, importado manualmente, em DD/MM/AAAA"** - o que
  ficou gravado em cada uma;
- **"X repetida(s), ignorada(s)"** - já existiam;
- **"Y recusada(s):"**, uma linha por questão, com o motivo: sem as 5
  alternativas ou sem gabarito válido; sem o artigo em que se apoia; não
  declarou o conteúdo, ou o conteúdo está fora do escopo; o artigo citado não é
  nenhum dos pedidos (quando há `--elemento`); variação sem a questão real de
  base; do zero com vínculo a questão real ou sem a marca; questão a mais que o
  pedido;
- **"Nada importado: a resposta é do lote X e o pedido é do lote Y"** - a
  resposta é de outro pedido; nada entra.

**5. Ver o estoque:**

- o total: `(Get-Content data\questoes_geradas.json -Raw | ConvertFrom-Json).Count`;
- por tema: `.\radar.bat fichas --tema "Aplicação da lei penal (arts. 1º a 12)"` -
  a linha "Geradas por IA neste conteúdo: N" - ou na web, Hoje > Fichas > a
  ficha do tema;
- para treinar: na web, o /geradas (ele sorteia pela matéria).

**6. Conferir, commit e push:**

```powershell
(Get-Content data\questoes_geradas.json -Raw | ConvertFrom-Json).Count   # o de antes + N, nunca 0
git status --short                                                        # só data/questoes_geradas.json
git add data\questoes_geradas.json
git commit -m "Gera N questoes de treino sobre <no> (<dispositivo ou regra>)" -m "Respondidas pelo Claude Code (radar gerar --pedido / --importar), sem chave da Anthropic. Procedencia: Claude Code, importado manualmente, em DD/MM/AAAA."
git pull --rebase
git push
```

O `git pull --rebase` é porque o robô da coleta faz push todo dia.

## Os 57 lotes, por data de uso

A conta de cada lote (decisão 73): o déficit do tema - as questões das faixas de
treino de 04/10 a 07/11 menos as reais ainda não respondidas nos nós dele -
dividido entre os nós de subassunto do tema, no máximo 20 por nó (5 no nó que é
um artigo só). Os lotes 2 a 56 foram feitos todos em 03/10 (escolha sua); como
o /geradas sorteia pela matéria, o treino rápido já mistura temas que ainda não
estudei (está nas pendências). Os lotes 50 e 57 entraram depois da decisão 76
- ver "Os lotes 2 a 56", abaixo.

### 05 a 10/10

1. **05/10 · Penal · Aplicação da lei penal (arts. 1º a 12)** - Abolitio criminis: 19 (3 variação + 16 do zero) - **feito em 03/10 (19 questões)**
   ```powershell
   .\radar.bat gerar --pedido --modo treino --materia "Direito Penal" --assunto "Tipicidade, ilicitude, culpabilidade, punibilidade" --subassunto "Abolitio criminis" --quantas 19
   ```
2. **06/10 · Const. · Art. 5º, incisos XVII a XLIX** - Liberdade de associação: 11 (3 variação + 8 do zero)
   ```powershell
   .\radar.bat gerar --pedido --modo treino --materia "Direito Constitucional" --assunto "Direitos e garantias fundamentais: direitos e garantias individuais e coletivos" --subassunto "Liberdade de associação" --quantas 11
   ```
3. **06/10 · Const. · Art. 5º, incisos XVII a XLIX** - Tribunal do júri: 11 (3 variação + 8 do zero)
   ```powershell
   .\radar.bat gerar --pedido --modo treino --materia "Direito Constitucional" --assunto "Direitos e garantias fundamentais: direitos e garantias individuais e coletivos" --subassunto "Tribunal do júri" --quantas 11
   ```
4. **06/10 · Const. · Art. 5º, incisos XVII a XLIX** - Princípios constitucionais penais: 11 (9 variação + 2 do zero)
   ```powershell
   .\radar.bat gerar --pedido --modo treino --materia "Direito Constitucional" --assunto "Direitos e garantias fundamentais: direitos e garantias individuais e coletivos" --subassunto "Princípios constitucionais penais" --quantas 11
   ```
5. **06/10 · Const. · Art. 5º, incisos XVII a XLIX** - Crimes inafiançáveis e imprescritíveis: 11 (3 variação + 8 do zero)
   ```powershell
   .\radar.bat gerar --pedido --modo treino --materia "Direito Constitucional" --assunto "Direitos e garantias fundamentais: direitos e garantias individuais e coletivos" --subassunto "Crimes inafiançáveis e imprescritíveis" --quantas 11
   ```
6. **06/10 · Port. · Concordância verbal 1: regra geral** - Concordância verbal: 15 (3 variação + 12 do zero)
   ```powershell
   .\radar.bat gerar --pedido --modo treino --materia "Língua Portuguesa" --assunto "Concordância nominal e verbal" --subassunto "Concordância verbal" --quantas 15
   ```
7. **06/10 · Const. · Art. 5º, caput e incisos I a XVI** - Liberdade de consciência, crença e assistência religiosa: 6 (3 variação + 3 do zero)
   ```powershell
   .\radar.bat gerar --pedido --modo treino --materia "Direito Constitucional" --assunto "Direitos e garantias fundamentais: direitos e garantias individuais e coletivos" --subassunto "Liberdade de consciência, crença e assistência religiosa" --quantas 6
   ```
8. **06/10 · Const. · Art. 5º, caput e incisos I a XVI** - Intimidade, vida privada, honra e imagem: 6 (3 variação + 3 do zero)
   ```powershell
   .\radar.bat gerar --pedido --modo treino --materia "Direito Constitucional" --assunto "Direitos e garantias fundamentais: direitos e garantias individuais e coletivos" --subassunto "Intimidade, vida privada, honra e imagem" --quantas 6
   ```
9. **06/10 · Const. · Art. 5º, caput e incisos I a XVI** - Inviolabilidade do domicílio: 6 (3 variação + 3 do zero)
   ```powershell
   .\radar.bat gerar --pedido --modo treino --materia "Direito Constitucional" --assunto "Direitos e garantias fundamentais: direitos e garantias individuais e coletivos" --subassunto "Inviolabilidade do domicílio" --quantas 6
   ```
10. **07/10 · Port. · Concordância verbal 2: casos especiais** - Concordância do verbo haver impessoal: 15 (3 variação + 12 do zero)
   ```powershell
   .\radar.bat gerar --pedido --modo treino --materia "Língua Portuguesa" --assunto "Concordância nominal e verbal" --subassunto "Concordância do verbo haver impessoal" --quantas 15
   ```
11. **08/10 · DH · Afirmação histórica e dimensões (gerações)** - Gerações (dimensões) de direitos: 18 (6 variação + 12 do zero)
   ```powershell
   .\radar.bat gerar --pedido --modo treino --materia "Direitos Humanos" --assunto "Teoria geral dos direitos humanos" --subassunto "Gerações (dimensões) de direitos" --quantas 18
   ```
12. **08/10 · DH · Afirmação histórica e dimensões (gerações)** - Gerações (dimensões) dos direitos humanos: 18 (3 variação + 15 do zero)
   ```powershell
   .\radar.bat gerar --pedido --modo treino --materia "Direitos Humanos" --assunto "Teoria geral dos direitos humanos" --subassunto "Gerações (dimensões) dos direitos humanos" --quantas 18
   ```
13. **08/10 · Port. · Interpretação 2: tipos de texto** - Tipologia e gênero textual: 5 (3 variação + 2 do zero)
   ```powershell
   .\radar.bat gerar --pedido --modo treino --materia "Língua Portuguesa" --assunto "Compreensão e interpretação de texto (s)" --subassunto "Tipologia e gênero textual" --quantas 5
   ```
14. **08/10 · DH · Teoria geral** - Características dos direitos humanos: 6 (6 variação + 0 do zero)
   ```powershell
   .\radar.bat gerar --pedido --modo treino --materia "Direitos Humanos" --assunto "Teoria geral dos direitos humanos" --subassunto "Características dos direitos humanos" --quantas 6
   ```
15. **08/10 · DH · Teoria geral** - Eficácia horizontal: 6 (3 variação + 3 do zero)
   ```powershell
   .\radar.bat gerar --pedido --modo treino --materia "Direitos Humanos" --assunto "Teoria geral dos direitos humanos" --subassunto "Eficácia horizontal" --quantas 6
   ```
16. **09/10 · LEP · Deveres e direitos do preso (arts. 38 a 43)** - Deveres do condenado: 18 (3 variação + 15 do zero)
   ```powershell
   .\radar.bat gerar --pedido --modo treino --materia "Lei de Execução Penal" --assunto "Lei de Execução Penal (Lei nº 7.210 de 11 de julho de 1984)" --subassunto "Deveres do condenado" --quantas 18
   ```
17. **09/10 · LEP · Deveres e direitos do preso (arts. 38 a 43)** - Direitos do preso: 18 (3 variação + 15 do zero)
   ```powershell
   .\radar.bat gerar --pedido --modo treino --materia "Lei de Execução Penal" --assunto "Lei de Execução Penal (Lei nº 7.210 de 11 de julho de 1984)" --subassunto "Direitos do preso" --quantas 18
   ```
18. **09/10 · LEP · Assistência ao preso e ao egresso (arts. 10 a 27)** - Assistência ao preso e ao egresso: 17 (9 variação + 8 do zero)
   ```powershell
   .\radar.bat gerar --pedido --modo treino --materia "Lei de Execução Penal" --assunto "Lei de Execução Penal (Lei nº 7.210 de 11 de julho de 1984)" --subassunto "Assistência ao preso e ao egresso" --quantas 17
   ```
19. **10/10 · RL · Princípios de contagem** - Princípio multiplicativo: 4 (3 variação + 1 do zero)
   ```powershell
   .\radar.bat gerar --pedido --modo treino --materia "Raciocínio Lógico" --assunto "Princípios de contagem e probabilidade" --subassunto "Princípio multiplicativo" --quantas 4
   ```
20. **10/10 · RL · Princípios de contagem** - Permutações e ordenação: 4 (3 variação + 1 do zero)
   ```powershell
   .\radar.bat gerar --pedido --modo treino --materia "Raciocínio Lógico" --assunto "Princípios de contagem e probabilidade" --subassunto "Permutações e ordenação" --quantas 4
   ```
21. **10/10 · RL · Princípios de contagem** - Combinações: 4 (3 variação + 1 do zero)
   ```powershell
   .\radar.bat gerar --pedido --modo treino --materia "Raciocínio Lógico" --assunto "Princípios de contagem e probabilidade" --subassunto "Combinações" --quantas 4
   ```

### 12 a 17/10

22. **12/10 · Penal · Tentativa, dolo, culpa e erro (arts. 14 a 21)** - Dolo e culpa: 18 (6 variação + 12 do zero)
   ```powershell
   .\radar.bat gerar --pedido --modo treino --materia "Direito Penal" --assunto "Tipicidade, ilicitude, culpabilidade, punibilidade" --subassunto "Dolo e culpa" --quantas 18
   ```
23. **12/10 · Penal · Tentativa, dolo, culpa e erro (arts. 14 a 21)** - Tentativa e crime impossível: 18 (3 variação + 15 do zero)
   ```powershell
   .\radar.bat gerar --pedido --modo treino --materia "Direito Penal" --assunto "Tipicidade, ilicitude, culpabilidade, punibilidade" --subassunto "Tentativa e crime impossível" --quantas 18
   ```
24. **13/10 · Const. · Art. 5º, incisos L a LXXVIII e § 1º a 4º (remédios)** - Direitos do preso: 9 (3 variação + 6 do zero)
   ```powershell
   .\radar.bat gerar --pedido --modo treino --materia "Direito Constitucional" --assunto "Direitos e garantias fundamentais: direitos e garantias individuais e coletivos" --subassunto "Direitos do preso" --quantas 9
   ```
25. **13/10 · Const. · Art. 5º, incisos L a LXXVIII e § 1º a 4º (remédios)** - Devido processo legal: 9 (3 variação + 6 do zero)
   ```powershell
   .\radar.bat gerar --pedido --modo treino --materia "Direito Constitucional" --assunto "Direitos e garantias fundamentais: direitos e garantias individuais e coletivos" --subassunto "Devido processo legal" --quantas 9
   ```
26. **13/10 · Const. · Art. 5º, incisos L a LXXVIII e § 1º a 4º (remédios)** - Remédios constitucionais: 9 (6 variação + 3 do zero)
   ```powershell
   .\radar.bat gerar --pedido --modo treino --materia "Direito Constitucional" --assunto "Direitos e garantias fundamentais: direitos e garantias individuais e coletivos" --subassunto "Remédios constitucionais" --quantas 9
   ```
27. **13/10 · Const. · Art. 5º, incisos L a LXXVIII e § 1º a 4º (remédios)** - Gratuidades constitucionais aos reconhecidamente pobres: 9 (3 variação + 6 do zero)
   ```powershell
   .\radar.bat gerar --pedido --modo treino --materia "Direito Constitucional" --assunto "Direitos e garantias fundamentais: direitos e garantias individuais e coletivos" --subassunto "Gratuidades constitucionais aos reconhecidamente pobres" --quantas 9
   ```
28. **13/10 · Port. · Crase 2: proibida, facultativa e casos especiais** - Crase diante de substantivo feminino sem artigo: 20 (3 variação + 17 do zero)
   ```powershell
   .\radar.bat gerar --pedido --modo treino --materia "Língua Portuguesa" --assunto "Emprego da crase" --subassunto "Crase diante de substantivo feminino sem artigo" --quantas 20
   ```
29. **14/10 · Port. · Pontuação 1: vírgula entre termos** - Emprego da vírgula: 20 (3 variação + 17 do zero)
   ```powershell
   .\radar.bat gerar --pedido --modo treino --materia "Língua Portuguesa" --assunto "Pontuação" --subassunto "Emprego da vírgula" --quantas 20
   ```
30. **15/10 · DH · Sistemas de proteção e responsabilidade do Estado** - Sistema interamericano de proteção: 6 (3 variação + 3 do zero)
   ```powershell
   .\radar.bat gerar --pedido --modo treino --materia "Direitos Humanos" --assunto "Teoria geral dos direitos humanos" --subassunto "Sistema interamericano de proteção" --quantas 6
   ```
31. **15/10 · DH · Sistemas de proteção e responsabilidade do Estado** - Corte Interamericana de Direitos Humanos: 6 (6 variação + 0 do zero)
   ```powershell
   .\radar.bat gerar --pedido --modo treino --materia "Direitos Humanos" --assunto "Teoria geral dos direitos humanos" --subassunto "Corte Interamericana de Direitos Humanos" --quantas 6
   ```
32. **15/10 · DH · Sistemas de proteção e responsabilidade do Estado** - Sistema global e sistemas regionais de proteção: 6 (3 variação + 3 do zero)
   ```powershell
   .\radar.bat gerar --pedido --modo treino --materia "Direitos Humanos" --assunto "Teoria geral dos direitos humanos" --subassunto "Sistema global e sistemas regionais de proteção" --quantas 6
   ```
33. **15/10 · DH · Sistemas de proteção e responsabilidade do Estado** - Convenção Americana sobre Direitos Humanos (Pacto de San José): 6 (3 variação + 3 do zero)
   ```powershell
   .\radar.bat gerar --pedido --modo treino --materia "Direitos Humanos" --assunto "Teoria geral dos direitos humanos" --subassunto "Convenção Americana sobre Direitos Humanos (Pacto de San José)" --quantas 6
   ```
34. **15/10 · DH · Sistemas de proteção e responsabilidade do Estado** - Sistema interamericano de proteção: 6 (6 variação + 0 do zero)
   ```powershell
   .\radar.bat gerar --pedido --modo treino --materia "Direitos Humanos" --assunto "A Constituição brasileira e os tratados internacionais de direitos humanos" --subassunto "Sistema interamericano de proteção" --quantas 6
   ```
35. **15/10 · Port. · Interpretação 3: coesão e referência** - Relações de sentido e conectivos: 5 (3 variação + 2 do zero)
   ```powershell
   .\radar.bat gerar --pedido --modo treino --materia "Língua Portuguesa" --assunto "Compreensão e interpretação de texto (s)" --subassunto "Relações de sentido e conectivos" --quantas 5
   ```
36. **17/10 · RL · Probabilidade** - Probabilidade: 13 (6 variação + 7 do zero)
   ```powershell
   .\radar.bat gerar --pedido --modo treino --materia "Raciocínio Lógico" --assunto "Princípios de contagem e probabilidade" --subassunto "Probabilidade" --quantas 13
   ```

### 19 a 24/10

37. **19/10 · Penal · Coação, obediência e excludentes de ilicitude (arts. 22 a 25)** - Excludentes de ilicitude: 20 (9 variação + 11 do zero)
   ```powershell
   .\radar.bat gerar --pedido --modo treino --materia "Direito Penal" --assunto "Tipicidade, ilicitude, culpabilidade, punibilidade" --subassunto "Excludentes de ilicitude" --quantas 20
   ```
38. **20/10 · Port. · Pronomes 2: colocação pronominal** - Colocação e emprego dos pronomes: 20 (3 variação + 17 do zero)
   ```powershell
   .\radar.bat gerar --pedido --modo treino --materia "Língua Portuguesa" --assunto "Pronomes: emprego, forma de tratamento e colocação" --subassunto "Colocação e emprego dos pronomes" --quantas 20
   ```
39. **21/10 · LEP · Órgãos da execução penal (arts. 61 a 81-B)** - Órgãos da execução penal: 20 (3 variação + 17 do zero)
   ```powershell
   .\radar.bat gerar --pedido --modo treino --materia "Lei de Execução Penal" --assunto "Lei de Execução Penal (Lei nº 7.210 de 11 de julho de 1984)" --subassunto "Órgãos da execução penal" --quantas 20
   ```
40. **21/10 · LEP · Órgãos da execução penal (arts. 61 a 81-B)** - LEP, art. 75: 5 (3 variação + 2 do zero)
   ```powershell
   .\radar.bat gerar --pedido --modo treino --materia "Lei de Execução Penal" --assunto "Lei de Execução Penal (Lei nº 7.210 de 11 de julho de 1984)" --subassunto "Estabelecimentos penais" --elemento "LEP, art. 75" --quantas 5
   ```
41. **21/10 · Port. · Pronomes 3: formas de tratamento** - Uniformidade de tratamento: 20 (3 variação + 17 do zero)
   ```powershell
   .\radar.bat gerar --pedido --modo treino --materia "Língua Portuguesa" --assunto "Pronomes: emprego, forma de tratamento e colocação" --subassunto "Uniformidade de tratamento" --quantas 20
   ```
42. **22/10 · DH · Na Constituição e o status dos tratados** - Incorporação e hierarquia dos tratados: 9 (6 variação + 3 do zero)
   ```powershell
   .\radar.bat gerar --pedido --modo treino --materia "Direitos Humanos" --assunto "A Constituição brasileira e os tratados internacionais de direitos humanos" --subassunto "Incorporação e hierarquia dos tratados" --quantas 9
   ```
43. **22/10 · DH · Na Constituição e o status dos tratados** - Hierarquia da norma internacional incorporada: 9 (3 variação + 6 do zero)
   ```powershell
   .\radar.bat gerar --pedido --modo treino --materia "Direitos Humanos" --assunto "A Constituição brasileira e os tratados internacionais de direitos humanos" --subassunto "Hierarquia da norma internacional incorporada" --quantas 9
   ```
44. **22/10 · DH · Na Constituição e o status dos tratados** - Tratados equivalentes a emenda constitucional (EC 45/2004): 9 (3 variação + 6 do zero)
   ```powershell
   .\radar.bat gerar --pedido --modo treino --materia "Direitos Humanos" --assunto "A Constituição brasileira e os tratados internacionais de direitos humanos" --subassunto "Tratados equivalentes a emenda constitucional (EC 45/2004)" --quantas 9
   ```
45. **22/10 · DH · Na Constituição e o status dos tratados** - Audiência de custódia: 9 (3 variação + 6 do zero)
   ```powershell
   .\radar.bat gerar --pedido --modo treino --materia "Direitos Humanos" --assunto "A Constituição brasileira e os tratados internacionais de direitos humanos" --subassunto "Audiência de custódia" --quantas 9
   ```
46. **23/10 · Port. · Termos integrantes 1: objeto direto e indireto** - Objeto direto e indireto: 20 (3 variação + 17 do zero)
   ```powershell
   .\radar.bat gerar --pedido --modo treino --materia "Língua Portuguesa" --assunto "Termos integrantes da oração: objeto direto e indireto, agente da passiva e complemento nominal" --subassunto "Objeto direto e indireto" --quantas 20
   ```

### 26 a 31/10

47. **27/10 · Const. · Nacionalidade e direitos políticos (arts. 12 a 17)** - Alistamento eleitoral e voto: 19 (6 variação + 13 do zero)
   ```powershell
   .\radar.bat gerar --pedido --modo treino --materia "Direito Constitucional" --assunto "cidadania e direitos políticos" --subassunto "Alistamento eleitoral e voto" --quantas 19
   ```
48. **27/10 · Const. · Nacionalidade e direitos políticos (arts. 12 a 17)** - Voto facultativo e obrigatório: 19 (3 variação + 16 do zero)
   ```powershell
   .\radar.bat gerar --pedido --modo treino --materia "Direito Constitucional" --assunto "cidadania e direitos políticos" --subassunto "Voto facultativo e obrigatório" --quantas 19
   ```
49. **28/10 · LEP · Execução da pena, regimes e progressão (arts. 105 a 119)** - Regimes de cumprimento da pena: 20 (3 variação + 17 do zero)
   ```powershell
   .\radar.bat gerar --pedido --modo treino --materia "Lei de Execução Penal" --assunto "Lei de Execução Penal (Lei nº 7.210 de 11 de julho de 1984)" --subassunto "Regimes de cumprimento da pena" --quantas 20
   ```
50. **29/10 · DH · Regras de Mandela - parte 1 (regras 1 a 35)** - Regras de aplicação geral: 20 (3 variação + 17 do zero)
   ```powershell
   .\radar.bat gerar --pedido --modo treino --materia "Direitos Humanos" --assunto "Regras mínimas da ONU para o tratamento de pessoas presas" --subassunto "Regras de aplicação geral" --quantas 20
   ```
51. **29/10 · Port. · Interpretação 5: tipos de discurso** - Discurso direto e indireto: 5 (3 variação + 2 do zero)
   ```powershell
   .\radar.bat gerar --pedido --modo treino --materia "Língua Portuguesa" --assunto "Redação Oficial: formas de tratamento, tipos de discursos, correspondência oficial" --subassunto "Discurso direto e indireto" --quantas 5
   ```
52. **30/10 · LEP · Permissão de saída, saída temporária e remição (arts. 120 a 130)** - Remição: 20 (3 variação + 17 do zero)
   ```powershell
   .\radar.bat gerar --pedido --modo treino --materia "Lei de Execução Penal" --assunto "Lei de Execução Penal (Lei nº 7.210 de 11 de julho de 1984)" --subassunto "Remição" --quantas 20
   ```
53. **30/10 · Port. · Redação oficial 1: atributos e tratamento** - Vocativos e formas de tratamento: 20 (3 variação + 17 do zero)
   ```powershell
   .\radar.bat gerar --pedido --modo treino --materia "Língua Portuguesa" --assunto "Redação Oficial: formas de tratamento, tipos de discursos, correspondência oficial" --subassunto "Vocativos e formas de tratamento" --quantas 20
   ```

### 02 a 07/11

54. **02/11 · Penal · Crimes do funcionário público contra a Administração (arts. 312 a 327)** - Crimes praticados por funcionário público contra a administração em geral: 16 (3 variação + 13 do zero)
   ```powershell
   .\radar.bat gerar --pedido --modo treino --materia "Direito Penal" --assunto "Crimes contra a Administração Pública" --subassunto "Crimes praticados por funcionário público contra a administração em geral" --quantas 16
   ```
55. **02/11 · Penal · Crimes do funcionário público contra a Administração (arts. 312 a 327)** - Peculato: 16 (3 variação + 13 do zero)
   ```powershell
   .\radar.bat gerar --pedido --modo treino --materia "Direito Penal" --assunto "Crimes contra a Administração Pública" --subassunto "Peculato" --quantas 16
   ```
56. **04/11 · LEP · Livramento condicional, monitoração e penas alternativas (arts. 131 a 170)** - Monitoração eletrônica: 20 (3 variação + 17 do zero)
   ```powershell
   .\radar.bat gerar --pedido --modo treino --materia "Lei de Execução Penal" --assunto "Lei de Execução Penal (Lei nº 7.210 de 11 de julho de 1984)" --subassunto "Monitoração eletrônica" --quantas 20
   ```
57. **05/11 · DH · Regras de Mandela - parte 2 (regras 36 em diante)** - Pessoal do estabelecimento prisional: 20 (3 variação + 17 do zero)
   ```powershell
   .\radar.bat gerar --pedido --modo treino --materia "Direitos Humanos" --assunto "Regras mínimas da ONU para o tratamento de pessoas presas" --subassunto "Pessoal do estabelecimento prisional" --quantas 20
   ```

## Os 28 temas que ficam sem estoque gerado

Eles não têm nó de subassunto na árvore: ou a árvore só tem o assunto, ou a
ficha do tema não aponta nó. Gerar com "matéria, assunto e subassunto" pediria
criar nó, e a escolha 5B foi não criar (decisão 73). As faixas deles continuam no
Qconcursos, como o plano manda.

- 05/10 · Penal · Fato típico e nexo causal (art. 13) (a árvore só tem o assunto)
- 05/10 · Port. · Vozes do verbo (a árvore só tem o assunto)
- 05/10 · RL · Bônus: lógica proposicional (a árvore só tem o assunto)
- 07/10 · LEP · Trabalho do preso (arts. 28 a 37) (a ficha não aponta nó)
- 07/10 · LEP · Objeto, classificação e exame criminológico (arts. 1º a 9º-A) (a ficha não aponta nó)
- 08/10 · Port. · Interpretação de texto (cronometrada) (a árvore só tem o assunto)
- 09/10 · Port. · Concordância nominal (a ficha não aponta nó)
- 12/10 · Port. · Crase 1: regra geral e casos obrigatórios (a ficha não aponta nó)
- 14/10 · LEP · Disciplina, faltas graves e RDD (arts. 44 a 52) (a ficha não aponta nó)
- 16/10 · LEP · Sanções, recompensas e procedimento disciplinar (arts. 53 a 60) (a ficha não aponta nó)
- 16/10 · Port. · Pontuação 2: vírgula entre orações e outros sinais (a ficha não aponta nó)
- 19/10 · Port. · Pronomes 1: emprego (a ficha não aponta nó)
- 20/10 · Const. · Direitos sociais (arts. 6º a 11) (a árvore só tem o assunto)
- 22/10 · Port. · Interpretação 4: inferência e sentido das palavras (a ficha não aponta nó)
- 23/10 · LEP · Estabelecimentos penais (arts. 82 a 104) (a ficha não aponta nó)
- 24/10 · RL · Conjuntos e diagramas lógicos (a árvore só tem o assunto)
- 26/10 · Penal · Imputabilidade e concurso de pessoas (arts. 26 a 31) (a árvore só tem o assunto)
- 26/10 · Port. · Termos integrantes 2: complemento nominal e agente da passiva (a ficha não aponta nó)
- 27/10 · Port. · Ortografia oficial (a árvore só tem o assunto)
- 28/10 · Port. · Acentuação gráfica (a árvore só tem o assunto)
- 31/10 · RL · Argumentação e quantificadores (a árvore só tem o assunto)
- 02/11 · Port. · Redação oficial 2: o padrão ofício (a ficha não aponta nó)
- 03/11 · Const. · Defesa do Estado e segurança pública (arts. 136 a 144) (a árvore só tem o assunto)
- 03/11 · Port. · Revisão ativa 1: concordância, crase e pontuação (a árvore só tem o assunto)
- 04/11 · Port. · Revisão ativa 2: pronomes, verbos e termos integrantes (a árvore só tem o assunto)
- 05/11 · Port. · Interpretação 6: bateria cronometrada (a árvore só tem o assunto)
- 06/11 · LEP · Medida de segurança, incidentes e disposições finais (arts. 171 a 204) (a ficha não aponta nó)
- 06/11 · Port. · Revisão ativa 3: ortografia, acentuação e redação oficial (a árvore só tem o assunto)

## O lote 1, feito em 03/10/2026

- **O nó:** Direito Penal > Tipicidade, ilicitude, culpabilidade, punibilidade >
  Abolitio criminis (o R+7 de 05/10 de "Aplicação da lei penal").
- **O que entrou:** 19 de 19, nenhuma recusada nem repetida. 3 por variação da
  questão real do complementar e 16 do zero, pela fonte oficial (CP), marcadas
  sem questão real de referência. Todas com matéria "Direito Penal", assunto
  "Abolitio criminis" e o caminho do nó; os dispositivos citados são o CP, art.
  2º e art. 107, III, o CF, art. 5º, XL, a Súmula 611 do STF e a LEP, art. 66, I.
- **Antes e depois:** no banco, 50 → 69; no JSON, 50 → 69; no nó, 0 → 19.
- **O conserto que veio junto (decisão 72):** a primeira versão do pedido dava
  às 3 variações a matéria "Conhecimentos Específicos", copiada do bloco
  genérico da prova complementar. Agora a variação com escopo grava a matéria e
  o assunto do escopo.

## Os lotes 2 a 56, feitos em 03/10/2026

- **O que entrou:** 666 questões em 54 lotes (todos, menos o 50), um commit por
  semana de uso: 05-10/10, 210 (`989f9e4`); 12-17/10, 160 (`53da083`);
  19-24/10, 141 (`9b4d649`); 26-31/10, 103 (`43ce39f`); 02-07/11, 52. Com o lote
  1, o estoque tem 685: Português 165, LEP 138, Constitucional 136, Direitos
  Humanos 114, Penal 107, Raciocínio Lógico 25. No banco e no JSON, 69 → 735.
- **Recusas:** nenhuma. **Repetidas:** 5, no lote 6 - o mesmo comando
  ("Assinale a alternativa correta quanto à concordância verbal.") em seis
  questões de alternativas diferentes; a importação guardou uma (ver
  "Cuidados"). As 5 foram reescritas com enunciados próprios e repostas com um
  pedido de 5 no mesmo nó.
- **O texto de lei:** conferido na compilação da Câmara (LEP, CF, CP e CPP),
  como manda a lista de leis. Entraram as mudanças de 2024 a 2026: LEP, art. 41,
  § 1º (quem suspende visita é o juiz da execução) e § 2º, e art. 41-A; art. 112
  (o caput e os percentuais do hediondo, de 70% a 85%) e o exame criminológico
  do § 1º; art. 126, § 9º; art. 146-B, VI a VIII, e art. 146-E; CPP, art. 310 (a
  audiência de custódia por videoconferência). Os incisos I a IV do art. 112,
  reescritos em 2026, ficaram de fora: a redação compilada repete percentuais e
  é fácil de errar.
- **Os lotes 50 e 57 (Regras de Mandela, 40 questões):** pararam porque, em
  Direitos Humanos, a importação só aceitava "art." ou "súmula" na fonte, e a
  regra de Mandela se cita como "regra 12.1". Com a sua escolha, a importação
  passou a aceitar "regra" seguida de número (decisão 76), e os dois entraram:
  40 de 40, escritos sobre o texto oficial da ONU (o PDF do UNODC, em inglês) -
  as regras 1 a 35 no lote 50 e as 74 a 82, do pessoal, no lote 57. O estoque
  fechou nos 57 lotes: 725 questões, e o JSON em 775.

## Cuidados

- **Enunciado repetido não entra.** A gerada é única pelo enunciado (a
  `impressao`): dois comandos genéricos iguais, com alternativas diferentes,
  viram uma questão só, e o resto sai como "repetida(s), ignorada(s)". Escreva
  cada enunciado com o que ele cobra.

- **Leia as questões ao treinar.** Elas são material auxiliar (🟣); a que estiver
  errada, marque no treino com "essa questão está errada" - ela sai do sorteio.
- ~~As 20 geradas de 28/09 com a matéria "Aplicação da lei penal"~~: resolvido
  em 04/10 (decisão 89) - viraram "Direito Penal", e as 50 antigas ganharam o
  nó.
- **A ajuda do `radar gerar`** já foi corrigida na docstring (o do zero completa
  dentro do nó, decisão 35); sobra só a mensagem do console no `cli.py`.

## O saldo de 05/10, com o plano redistribuído (R5)

Calculado pela mesma conta que a faixa de questões mostra
(`servico.geradas.das_faixas`, decisões 112 e 113), nas faixas de treino de
06/10 a 07/11 já redistribuídas (decisão 124), com os números do arquivo (sem
a rampa do nível). **Nada foi gerado nem apagado:** o estoque é por nó, e
fica. Pela sua escolha na Fase 1, a falta se gera **sob demanda**, pelos 3
passos da própria faixa (`radar gerar --pedido` / `--importar`, com os seus
créditos, nunca `--valendo`).

- 171 faixas de treino; 86 nós; **24 nós com zero gerada**;
- **falta 231** questões contra a maior cota que uma faixa pede de cada nó
  (259 com o pedido mínimo de 5); **sobra 410** - fica guardada para revisão
  e para os próximos ciclos;
- 13 temas (30 faixas) **sem nó na árvore**: a faixa não dá comando de gerar
  (pendência H).

"Maior cota" é o que a faixa que mais pede deste nó pede dele (as questões da
faixa divididas entre os nós dela). "Falta" e "sobra" são contra ela.

| Nó | Temas | Geradas válidas | Maior cota de uma faixa | Faixas | Falta | Sobra |
|---|---|---|---|---|---|---|
| Imputabilidade penal | Imputabilidade e concurso de pessoas (arts. 26 a 31) | 0 | 25 | 3 | 25 | — |
| Acentuação gráfica | Acentuação gráfica; Revisão ativa 3: ortografia, acentuação e redação oficial | 0 | 15 | 4 | 15 | — |
| Ortografia oficial | Ortografia oficial; Revisão ativa 3: ortografia, acentuação e redação oficial | 0 | 15 | 4 | 15 | — |
| direitos sociais | Direitos sociais (arts. 6º a 11) | 0 | 14 | 3 | 14 | — |
| Defesa do Estado e das instituições democráticas: segurança pública | Defesa do Estado e segurança pública (arts. 136 a 144) | 0 | 13 | 2 | 13 | — |
| organização da segurança pública | Defesa do Estado e segurança pública (arts. 136 a 144) | 0 | 12 | 2 | 12 | — |
| Afirmação histórica dos direitos humanos | Afirmação histórica e dimensões (gerações) | 0 | 10 | 4 | 10 | — |
| nacionalidade | Nacionalidade e direitos políticos (arts. 12 a 17) | 0 | 9 | 3 | 9 | — |
| Vozes do verbo | Revisão ativa 2: pronomes, verbos e termos integrantes; Vozes do verbo | 0 | 9 | 3 | 9 | — |
| Direitos humanos na Constituição Federal | Na Constituição e o status dos tratados | 0 | 7 | 3 | 7 | — |
| Lei de Execução Penal (Lei nº 7.210 de 11 de julho de 1984) > Estabelecimentos penais > LEP, art. 75 | Órgãos da execução penal (arts. 61 a 81-B) | 5 | 12 | 3 | 7 | — |
| Classes gramaticais variáveis: substantivo, adjetivo, artigo, numeral, pronome, verbo > Classificação morfológica | Artigo, numeral e pronome (classificação) | 0 | 7 | 2 | 7 | — |
| Infração penal: elementos, espécies | Fato típico e nexo causal (art. 13) | 0 | 6 | 2 | 6 | — |
| Tipicidade, ilicitude, culpabilidade, punibilidade > Excludentes de ilicitude | Coação, obediência e excludentes de ilicitude (arts. 22 a 25) | 20 | 25 | 3 | 5 | — |
| Regras mínimas da ONU para o tratamento de pessoas presas > Pessoal do estabelecimento prisional | Regras de Mandela - parte 2 (regras 36 em diante) | 20 | 25 | 2 | 5 | — |
| Regras mínimas da ONU para o tratamento de pessoas presas > Regras de aplicação geral | Regras de Mandela - parte 1 (regras 1 a 35) | 20 | 25 | 3 | 5 | — |
| Lei de Execução Penal (Lei nº 7.210 de 11 de julho de 1984) > Monitoração eletrônica | Livramento condicional, monitoração e penas alternativas (arts. 131 a 170) | 20 | 25 | 2 | 5 | — |
| Lei de Execução Penal (Lei nº 7.210 de 11 de julho de 1984) > Regimes de cumprimento da pena | Execução da pena, regimes e progressão (arts. 105 a 119) | 20 | 25 | 3 | 5 | — |
| Compreensão e interpretação de texto (s) | Interpretação 6: bateria cronometrada; Interpretação de texto (cronometrada) | 10 | 15 | 6 | 5 | — |
| Diagramas lógicos | Conjuntos e diagramas lógicos | 0 | 5 | 2 | 5 | — |
| Lógica de argumentação: analogias, inferências, deduções e conclusões | Argumentação e quantificadores | 0 | 5 | 2 | 5 | — |
| Lógica de primeira ordem | Argumentação e quantificadores | 0 | 5 | 2 | 5 | — |
| Operações com conjuntos | Conjuntos e diagramas lógicos | 0 | 5 | 2 | 5 | — |
| Direitos humanos e responsabilidade do Estado | Sistemas de proteção e responsabilidade do Estado | 0 | 4 | 3 | 4 | — |
| Emprego de tempos e modos verbais | Revisão ativa 2: pronomes, verbos e termos integrantes; Verbo 2: emprego dos tempos e modos | 0 | 4 | 3 | 4 | — |
| Lógica proposicional (ou sentencial) | Bônus: lógica proposicional | 0 | 4 | 24 | 4 | — |
| direito à vida, à liberdade, à igualdade, à segurança e à propriedade | Art. 5º, caput e incisos I a XVI | 0 | 3 | 4 | 3 | — |
| Conceito, terminologia, estrutura normativa, fundamentação | Teoria geral | 0 | 3 | 2 | 3 | — |
| Lei de Execução Penal (Lei nº 7.210 de 11 de julho de 1984) > Remição | Permissão de saída, saída temporária e remição (arts. 120 a 130) | 22 | 25 | 3 | 3 | — |
| Equivalências | Bônus: lógica proposicional | 0 | 3 | 24 | 3 | — |
| Tabelas-verdade | Bônus: lógica proposicional | 0 | 3 | 24 | 3 | — |
| Flexão nominal e verbal > Plural dos substantivos terminados em -ão | Substantivo e adjetivo (flexão nominal) | 0 | 2 | 1 | 2 | — |
| Compreensão e interpretação de texto (s) > Relações de sentido e conectivos | Interpretação 3: coesão e referência | 5 | 6 | 1 | 1 | — |
| Compreensão e interpretação de texto (s) > Tipologia e gênero textual | Interpretação 2: tipos de texto | 5 | 6 | 1 | 1 | — |
| Redação Oficial: formas de tratamento, tipos de discursos, correspondência oficial > Discurso direto e indireto | Interpretação 5: tipos de discurso | 5 | 6 | 1 | 1 | — |
| Direitos e garantias fundamentais: direitos e garantias individuais e coletivos > Crimes inafiançáveis e imprescritíveis | Art. 5º, incisos XVII a XLIX | 11 | 5 | 5 | — | 6 |
| Direitos e garantias fundamentais: direitos e garantias individuais e coletivos > Devido processo legal | Art. 5º, incisos L a LXXVIII e § 1º a 4º (remédios) | 9 | 5 | 3 | — | 4 |
| Direitos e garantias fundamentais: direitos e garantias individuais e coletivos > Direitos do preso | Art. 5º, incisos L a LXXVIII e § 1º a 4º (remédios) | 9 | 5 | 3 | — | 4 |
| Direitos e garantias fundamentais: direitos e garantias individuais e coletivos > Gratuidades constitucionais aos reconhecidamente pobres | Art. 5º, incisos L a LXXVIII e § 1º a 4º (remédios) | 9 | 5 | 3 | — | 4 |
| Direitos e garantias fundamentais: direitos e garantias individuais e coletivos > Intimidade, vida privada, honra e imagem | Art. 5º, caput e incisos I a XVI | 6 | 3 | 4 | — | 3 |
| Direitos e garantias fundamentais: direitos e garantias individuais e coletivos > Inviolabilidade do domicílio | Art. 5º, caput e incisos I a XVI | 6 | 3 | 4 | — | 3 |
| Direitos e garantias fundamentais: direitos e garantias individuais e coletivos > Liberdade de associação | Art. 5º, incisos XVII a XLIX | 11 | 5 | 5 | — | 6 |
| Direitos e garantias fundamentais: direitos e garantias individuais e coletivos > Liberdade de consciência, crença e assistência religiosa | Art. 5º, caput e incisos I a XVI | 6 | 3 | 4 | — | 3 |
| Direitos e garantias fundamentais: direitos e garantias individuais e coletivos > Princípios constitucionais penais | Art. 5º, incisos XVII a XLIX | 11 | 5 | 5 | — | 6 |
| Direitos e garantias fundamentais: direitos e garantias individuais e coletivos > Remédios constitucionais | Art. 5º, incisos L a LXXVIII e § 1º a 4º (remédios) | 9 | 5 | 3 | — | 4 |
| Direitos e garantias fundamentais: direitos e garantias individuais e coletivos > Tribunal do júri | Art. 5º, incisos XVII a XLIX | 11 | 5 | 5 | — | 6 |
| cidadania e direitos políticos > Alistamento eleitoral e voto | Nacionalidade e direitos políticos (arts. 12 a 17) | 19 | 8 | 3 | — | 11 |
| cidadania e direitos políticos > Voto facultativo e obrigatório | Nacionalidade e direitos políticos (arts. 12 a 17) | 19 | 8 | 3 | — | 11 |
| Crimes contra a Administração Pública > Crimes praticados por funcionário público contra a administração em geral | Crimes do funcionário público contra a Administração (arts. 312 a 327) | 16 | 13 | 2 | — | 3 |
| Crimes contra a Administração Pública > Peculato | Crimes do funcionário público contra a Administração (arts. 312 a 327) | 16 | 12 | 2 | — | 4 |
| Tipicidade, ilicitude, culpabilidade, punibilidade > Abolitio criminis | Aplicação da lei penal (arts. 1º a 12) | 21 | 10 | 2 | — | 11 |
| Tipicidade, ilicitude, culpabilidade, punibilidade > Dolo e culpa | Tentativa, dolo, culpa e erro (arts. 14 a 21) | 17 | 10 | 4 | — | 7 |
| Tipicidade, ilicitude, culpabilidade, punibilidade > Tentativa e crime impossível | Tentativa, dolo, culpa e erro (arts. 14 a 21) | 18 | 10 | 4 | — | 8 |
| A Constituição brasileira e os tratados internacionais de direitos humanos > Audiência de custódia | Na Constituição e o status dos tratados | 9 | 6 | 3 | — | 3 |
| A Constituição brasileira e os tratados internacionais de direitos humanos > Hierarquia da norma internacional incorporada | Na Constituição e o status dos tratados | 9 | 6 | 3 | — | 3 |
| A Constituição brasileira e os tratados internacionais de direitos humanos > Incorporação e hierarquia dos tratados | Na Constituição e o status dos tratados | 18 | 6 | 3 | — | 12 |
| A Constituição brasileira e os tratados internacionais de direitos humanos > Sistema interamericano de proteção | Sistemas de proteção e responsabilidade do Estado | 12 | 4 | 3 | — | 8 |
| Teoria geral dos direitos humanos > Características dos direitos humanos | Teoria geral | 6 | 4 | 2 | — | 2 |
| Teoria geral dos direitos humanos > Convenção Americana sobre Direitos Humanos (Pacto de San José) | Sistemas de proteção e responsabilidade do Estado | 6 | 4 | 3 | — | 2 |
| Teoria geral dos direitos humanos > Corte Interamericana de Direitos Humanos | Sistemas de proteção e responsabilidade do Estado | 6 | 4 | 3 | — | 2 |
| Teoria geral dos direitos humanos > Eficácia horizontal | Teoria geral | 6 | 3 | 2 | — | 3 |
| Teoria geral dos direitos humanos > Gerações (dimensões) de direitos | Afirmação histórica e dimensões (gerações) | 36 | 10 | 4 | — | 26 |
| Teoria geral dos direitos humanos > Sistema global e sistemas regionais de proteção | Sistemas de proteção e responsabilidade do Estado | 6 | 4 | 3 | — | 2 |
| Lei de Execução Penal (Lei nº 7.210 de 11 de julho de 1984) > Assistência ao preso e ao egresso | Assistência ao preso e ao egresso (arts. 10 a 27) | 20 | 10 | 2 | — | 10 |
| Lei de Execução Penal (Lei nº 7.210 de 11 de julho de 1984) > Deveres do condenado | Deveres e direitos do preso (arts. 38 a 43) | 19 | 10 | 3 | — | 9 |
| Lei de Execução Penal (Lei nº 7.210 de 11 de julho de 1984) > Direitos do preso | Deveres e direitos do preso (arts. 38 a 43) | 21 | 10 | 3 | — | 11 |
| Lei de Execução Penal (Lei nº 7.210 de 11 de julho de 1984) > Órgãos da execução penal | Órgãos da execução penal (arts. 61 a 81-B) | 23 | 13 | 3 | — | 10 |
| Classes gramaticais variáveis: substantivo, adjetivo, artigo, numeral, pronome, verbo > Substantivo e adjetivo | Substantivo e adjetivo (flexão nominal) | 8 | 2 | 1 | — | 6 |
| Concordância nominal e verbal | Revisão ativa 1: concordância, crase e pontuação | 31 | 5 | 2 | — | 26 |
| Concordância nominal e verbal > Concordância do verbo haver impessoal | Concordância verbal 2: casos especiais | 15 | 8 | 2 | — | 7 |
| Concordância nominal e verbal > Concordância verbal | Concordância verbal 1: regra geral | 15 | 10 | 3 | — | 5 |
| Emprego da crase | Revisão ativa 1: concordância, crase e pontuação | 20 | 5 | 2 | — | 15 |
| Emprego da crase > Crase diante de substantivo feminino sem artigo | Crase 2: proibida, facultativa e casos especiais | 20 | 6 | 2 | — | 14 |
| Pontuação | Revisão ativa 1: concordância, crase e pontuação | 20 | 5 | 2 | — | 15 |
| Pontuação > Emprego da vírgula | Pontuação 1: vírgula entre termos | 20 | 15 | 2 | — | 5 |
| Pronomes: emprego, forma de tratamento e colocação | Revisão ativa 2: pronomes, verbos e termos integrantes | 40 | 4 | 2 | — | 36 |
| Pronomes: emprego, forma de tratamento e colocação > Colocação e emprego dos pronomes | Pronomes 2: colocação pronominal | 20 | 15 | 2 | — | 5 |
| Pronomes: emprego, forma de tratamento e colocação > Uniformidade de tratamento | Pronomes 3: formas de tratamento | 20 | 8 | 2 | — | 12 |
| Redação Oficial: formas de tratamento, tipos de discursos, correspondência oficial | Revisão ativa 3: ortografia, acentuação e redação oficial | 25 | 5 | 2 | — | 20 |
| Redação Oficial: formas de tratamento, tipos de discursos, correspondência oficial > Vocativos e formas de tratamento | Redação oficial 1: atributos e tratamento | 20 | 15 | 2 | — | 5 |
| Termos integrantes da oração: objeto direto e indireto, agente da passiva e complemento nominal | Revisão ativa 2: pronomes, verbos e termos integrantes | 20 | 3 | 2 | — | 17 |
| Termos integrantes da oração: objeto direto e indireto, agente da passiva e complemento nominal > Objeto direto e indireto | Termos integrantes 1: objeto direto e indireto | 20 | 15 | 2 | — | 5 |
| Princípios de contagem e probabilidade > Combinações | Princípios de contagem | 4 | 1 | 1 | — | 3 |
| Princípios de contagem e probabilidade > Permutações e ordenação | Princípios de contagem | 4 | 2 | 1 | — | 2 |
| Princípios de contagem e probabilidade > Princípio multiplicativo | Princípios de contagem | 4 | 2 | 1 | — | 2 |
| Princípios de contagem e probabilidade > Probabilidade | Probabilidade | 13 | 10 | 2 | — | 3 |

## 06/10: a semana de 06 a 12/10 completada

A falta das faixas de 06 a 12/10 foi escrita de uma vez (decisao 131): 90
questoes em 15 nos, inclusive os 4 nos novos da decisao 129 que essa semana
usa, lidas uma a uma contra a fonte antes da importacao. A conta da faixa
(`fichas.geradas_por_no`) da falta zero nessa semana; de 13/10 em diante
continua sob demanda.
