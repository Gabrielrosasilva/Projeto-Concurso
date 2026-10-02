# Historico de implementacao

Como cada fase foi feita, com os numeros que foram medidos de verdade e os
becos sem saida que nao valem ser tentados de novo.

Isto e memoria de projeto, nao manual: para instalar e usar, veja o
[README](../README.md). Para as decisoes fechadas em forma de lista, veja
[decisoes.md](decisoes.md).

## Fase 1: a primeira fonte, e por que nao foi o diario oficial

O plano original era o **Diario Oficial dos Municipios de SC** (CIGA), que
seria a fonte primaria: e onde o ato oficial sai e cobre exatamente o recorte
da Grande Florianopolis. Nao deu. O `robots.txt` dele proibe robo:

```
User-agent: *
Disallow: /
Crawl-delay: 10
```

So o Bingbot tem permissao. Como a regra da casa e respeitar `robots.txt`, o
DOM/SC esta fora de raspagem. O caminho legitimo que o proprio site oferece e
o **alerta por e-mail** dele; ler essa caixa por IMAP fica como ideia futura.

Duas outras portas foram testadas no mesmo dia:

- **DOE-SC** (diario do estado) e uma aplicacao que so monta a pagina com
  JavaScript, sem HTML para ler. Precisaria de outra abordagem;
- **Querido Diario**, na primeira tentativa, respondeu `503 no available
  server`.

A fonte 1 acabou sendo o **feed RSS** do Concursos no Brasil, de proposito:
RSS e publico, estavel, feito para ser lido por programa, e nao quebra quando
o site muda o layout.

## Fase 1.6: o RSS e um fluxo, nao um arquivo

O feed entrega so os 15 itens mais recentes. Quem ligou o radar naquele dia viu
os concursos daquele dia e nada do que foi publicado antes — a primeira duvida
depois que o Telegram ficou pronto foi exatamente "por que so aparecem 14
concursos?".

A resposta foi `radar carga-inicial`, que anda para tras usando o `?paged=N`
do proprio feed. As paginas antigas vem com a mesma estrutura da primeira, e
por isso a carga inicial usa o **mesmo parser** e traz os mesmos campos —
titulo completo, data e categoria — em vez de raspar HTML.

O sitemap foi conferido no site real e nao serve: para em junho/2026 e nao traz
titulo, so URL.

Roda uma vez so, na mao, e nao entra na coleta diaria. Duas protecoes: pausa
de 1,5s entre paginas, e parada automatica assim que uma pagina inteira fica
mais antiga que o periodo pedido.

Medido no site em 17/09/2026: cerca de 1,5 pagina por dia de historico, 15
itens por pagina. Noventa dias saem em uns 3 minutos.

## Fase 2: a pagina do post, e o caso SEFAZ

Data de publicacao nao e prazo. Um edital publicado ha um mes pode estar com
inscricao aberta ate semana que vem, e um de ontem pode ja ter fechado. Por
isso `radar detalhar` le a pagina de cada post e traz tres coisas que o RSS
nao da: **prazo de inscricao, banca e municipio de lotacao**.

**O caso que motivou isto:** "Concurso SEFAZ (SC)" nao tem "Prefeitura de X" no
titulo, entao o classificador nao acha municipio nenhum e marca `indefinida` —
o concurso existe, esta no banco, mas nao aparece em "Perto de mim". A pagina
do post diz "lotacao em Florianopolis", e com isso ele vai para o nucleo.

Ele **nao le a pagina de todos**. Seriam 2.200 requisicoes por quase uma hora,
e 1.400 delas de outro estado. A ordem e: primeiro o que ja esta perto, depois
os concursos de SC que ficaram `indefinida`, depois os federais.

Quando a pagina cita varios municipios — comum em edital de secretaria
estadual, que lista vagas pelo estado inteiro — o radar **nao escolhe nenhum**
e o registro segue `indefinida`. Chutar seria pior.

## Fonte 2: FEPESE

A FEPESE e a banca que mais faz concurso em Santa Catarina, e o site dela expoe
os concursos como JSON em `/wp-json/wp/v2/concurso`. Entrega coisa que o
agregador nao tem:

- a **banca ja vem preenchida** (e o site dela);
- o **status vem da propria banca**, numa lista fechada ("Inscricoes abertas",
  "Em andamento", "Encerrados"), em vez de ser deduzido de data escrita em
  texto corrido;
- a **escolaridade exigida** vem junto;
- cada concurso traz o endereco do **hotsite**, onde ficam edital, prova e
  gabarito. E dali que o acervo da fase 3 foi montado.

Um efeito colateral util: como a FEPESE publica num tipo de post `concurso`,
nao ha o que adivinhar pelo titulo. Sem isso, "2026 - Prefeitura Municipal de
Sao Jose" virava `noticia`, porque nao tem a palavra concurso no titulo.

## Fase 1.7: fontes federais e diarios, o que foi avaliado e ficou de fora

As candidatas foram testadas de verdade. O motivo de cada uma fica registrado
para nao serem testadas de novo daqui a seis meses:

**Diario Oficial da Uniao (in.gov.br)** — `robots.txt` com `User-agent: *` e
`Disallow: /`. Proibe robo no site inteiro, exatamente como o DOM/SC. Fora.

**Portal de Editais de Oportunidades (Sigepe)** — tem 2.953 editais federais
numa pagina so, sem robots.txt restringindo. Mas os editais **nao sao concurso
publico**: sao movimentacao interna de quem ja e servidor federal — "Funcao
Comissionada Executiva", "Chefe de Divisao", "selecionando 1 pessoa para
atuar". Nao serve para quem esta de fora.

**Querido Diario** — entrou por um tempo, e depois **saiu**. Vale o registro
completo, porque foi a promessa mais alta da fase.

A promessa era o sinal "contratou a banca": quando a prefeitura contrata quem
vai fazer a prova, sai licitacao ou dispensa no diario, 2 a 4 meses antes de o
edital existir. O coletor foi escrito e testado, e ai os numeros apareceram:

| o que se esperava | o que tinha |
|---|---|
| os 35 municipios de `config/regioes.yml` | **1**: so Florianopolis tem diario coletado |
| ato de contratacao de banca | **0** achados para "inexigibilidade", "dispensa de licitacao banca", "contratacao de instituicao" |
| sinal antes do edital | 5 edicoes em 180 dias, e os trechos eram de editais **ja publicados** |

Duas armadilhas descobertas no caminho, que nao custa saber: buscar sem
`territory_id` virava **busca nacional, e calada** — a primeira versao trouxe
diario de Sergipe —, e a busca por nome de municipio **nao** ignora acento.

O `robots.txt` do Querido Diario traz `Disallow: /api`. Por um tempo o projeto
usou mesmo assim, com justificativa explicita (API publica e documentada de um
projeto de dados abertos, uso de leitura, so aquele host). Depois a regra
passou a ser **respeitar `robots.txt` sem excecao**, e com isso `diario.py`, o
comando `radar diario` e os testes dele foram removidos. O que a fonte
devolvia ja vinha das bancas, e mais cedo.

## Fonte 3: IESES

Segunda banca catarinense do radar. Ela fica em Florianopolis e faz concurso de
prefeitura da regiao — Biguacu e Gaspar estao na lista dela.

Como foi achada: `ieses.org/projetos` e uma tela que carrega a lista por
JavaScript, com botao "carregar mais". O arquivo `/projetos-static/projetos.js`
mostra de onde vem o dado, `/projetos/api?offset=&limit=`, e essa API devolve
JSON limpo. Melhor que raspar a tela — nao quebra quando mudam o CSS.

Dois limites, medidos:

1. **sao 26 projetos**, de 2021 a 2026. A API nao devolve o historico inteiro
   da banca, so o que esta publicado no site;
2. **10 dos 26 hotsites ja sairam do ar** — erro de SSL ou de Cloudflare, quase
   todos de 2023 para tras. O que sobra ainda traz Biguacu 2024 e Gaspar 2024.

Uma coisa que o coletor **nao** faz: afirmar `uf=SC`. A IESES e catarinense mas
faz concurso fora (tribunal do Amazonas, gas do Mato Grosso do Sul), e afirmar
SC mandaria esses para o anel errado.

### O acervo da IESES, e um robots.txt que nao existia

O hotsite poe tudo numa pagina so, com os PDFs num CDN e o endereco num formato
regular:

```
.../{ano}/{pasta}/edital.pdf
.../{ano}/{pasta}/provas/{codigo}.pdf
.../{ano}/{pasta}/gabaritos/{codigo}.pdf
```

O codigo e o do cargo e e o mesmo nas duas pastas: e por ele que a prova casa
com o gabarito. O nome do cargo nao esta no endereco, e sim no texto ao lado do
link ("- 1016 - Assistente Social"). Como os dois arquivos se chamam
`1016.pdf`, o tipo entra no nome em disco, senao um sobrescreve o outro.

Na primeira tentativa, **nada baixou**: 65 falhas seguidas com
`ColetorBloqueadoPeloRobots`. O CDN da IESES e um balde de arquivos que
responde **403** a qualquer caminho que nao exista, inclusive `/robots.txt`. E
o leitor de robots.txt do Python trata 403 como **"proibido tudo"**. Ou seja: o
acervo inteiro estava bloqueado por um arquivo que nunca existiu.

A regra do padrao atual (RFC 9309) e a que passou a valer aqui: **resposta 4xx
quer dizer que nao ha robots.txt**, e o site pode ser acessado. So o conteudo
que o coletor conseguiu LER de fato vira restricao. Site que proibe de verdade
continua proibido — o DOM/SC, que responde 200 com `Disallow: /`, segue fora.

### A materia que estava no edital, e nao no caderno

O caderno da IESES tem tres diferencas em relacao ao da FEPESE:

1. **quatro alternativas**, de a) a d), e nao cinco;
2. **o gabarito e um PDF a parte** ("1 A", "2B", "3C"...), e nao uma marca
   dentro do proprio caderno;
3. **a materia nao aparece no caderno**. Sao 30 questoes numeradas de 1 a 30,
   sem cabecalho de secao nenhum.

O terceiro item podia inviabilizar tudo: sem materia, a questao nao entra no
simulado nem nos macetes. Mas a informacao existe — esta no **edital**:

* o **Anexo II** liga o codigo do cargo ao nivel (1016 Assistente Social esta
  sob "NIVEL SUPERIOR");
* o **Anexo IV** diz de que o nivel e feito, **na ordem em que cai na prova**:
  Lingua Portuguesa 8, Matematica e Raciocinio Logico 4, Informatica 3,
  Atualidades 2, Etica no Servico Publico 3, e o resto de Especificos.

Com os dois, a questao 13 e de Informatica porque o edital diz isso — e nao
porque alguem leu o enunciado e achou. Conferido no caderno real: 1 a 8 sao o
poema e a gramatica, 9 a 12 sao juros e sequencia, 13 a 15 sao Word e Excel, 16
e 17 sao economia verde e inteligencia artificial, 18 a 20 sao etica do
servidor, e 21 a 30 sao servico social.

**Os especificos sao "o resto", de proposito.** O mesmo edital escreve o numero
deles de tres jeitos: `ESPECIFICOS - COM 10 (DEZ) QUESTOES`, "contera 10 (dez)
questoes especificas" e "tera 10 (dez questoes)" — com a palavra *dentro* do
parentese. Perseguir a redacao era briga perdida; a ordem, essa sim, nunca
muda: gerais primeiro.

Resultado: **907 questoes**, todas com gabarito e 877 com materia. As 30 que
faltam sao de um cargo que o edital nao declara no Anexo II nem na retificacao
— fica sem materia mesmo, que e melhor que chutar.

### Uma lista fixa de materias nao serve para duas bancas

O simulado sem materia escolhida usa as que caem em qualquer concurso. Isso era
uma lista de quatro nomes exatos, e com a IESES no acervo ela passou a mentir:
a FEPESE escreve "Raciocinio Logico" e "Nocoes de Informatica", a IESES escreve
"Matematica e Raciocinio Logico" e "Informatica". O simulado so trazia
Portugues das provas da IESES.

Agora quem decide e o **catalogo de apelidos** dos macetes, que ja sabia que as
duas coisas sao a mesma materia. De quebra, ele aprendeu a recusar materia de
uma area so: "Conhecimentos Gerais sobre Educacao" comeca igual a
"Conhecimentos Gerais", mas so cai em prova de professor.

## Fase 3: o acervo de provas

Cada concurso da FEPESE tem um hotsite proprio, e e nele que ficam os PDFs:
`?go=edital` tem o edital de abertura, `?go=provas` tem o caderno de cada cargo
e os gabaritos. O caderno vem com o **cargo no rotulo do link** ("Monitor de
Transporte Escolar", "Supervisor Escolar") — e isso que importa, porque o que
vale estudar e o padrao da banca no *meu* cargo, nao a media de todos.

`radar provas` nao le os 520 hotsites de uma vez: seriam horas de requisicao e
a maior parte nao interessa. A ordem e concurso **ja encerrado** (que e o que
tem prova publicada) e **perto de casa** primeiro, depois os indefinidos.

### Por que os PDFs nao ficam no git

A conta que motivou: os primeiros 29 documentos deram **37 MB em disco** e
**18 KB de manifesto**. Git guarda uma copia inteira de cada arquivo binario a
cada commit, entao o acervo no repositorio o deixaria grande e lento em pouco
tempo. Versionar a receita em vez do artefato e a mesma logica de Dockerfile e
imagem.

O que e versionado e o manifesto `data/provas.json`: link de origem, banca,
orgao, municipio, cargo, ano, tipo e o `sha256` de cada arquivo. Com ele,
`radar baixar-provas` reconstroi o acervo inteiro em qualquer maquina, e o hash
prova que o arquivo e o mesmo. Os caminhos usam barra normal mesmo no Windows,
senao a outra maquina nao acha o arquivo.

### A ponte ate o concurso ABERTO

O acervo comeca pelo concurso encerrado, que e quem tem prova publicada. Mas a
elegibilidade interessa justamente no que esta aberto — e ai faltava uma ponte.

A ponte estava na pagina do agregador: ela **linka o hotsite da banca**. Dali
sai o edital. `radar detalhar` passou a guardar esse endereco, e
`radar provas --abertos` baixa o edital de quem ainda esta em andamento.

Cada banca identifica o concurso num lugar diferente do endereco, e os dois
casos sao reais:

* no **subdominio**, como a FEPESE faz —
  `https://2026cpeducaeesj.fepese.org.br/?go=edital` vira
  `https://2026cpeducaeesj.fepese.org.br`;
* no **caminho**, como a FCC faz —
  `https://www.concursosfcc.com.br/concursos/sefsc126/index.html` vira
  `https://www.concursosfcc.com.br/concursos/sefsc126`.

Devolver so o dominio no segundo caso perderia justamente o pedaco que diz de
que concurso se trata. E quando a mesma pagina linka varias telas do mesmo
hotsite — edital, inscricao, provas —, vale a mais curta: de Sao Jose 2026 saiu
`.../inscricao` na primeira versao, so porque foi o primeiro link do HTML.

## Fase 4: do PDF para a questao

O caderno da FEPESE tem estrutura regular, e dois detalhes dela pouparam muito
trabalho:

1. **a materia vem da propria banca**, em cabecalho de secao ("Lingua
   Portuguesa 10 questoes"). Nao precisa adivinhar o assunto de cada questao;
2. **a alternativa correta esta marcada no texto**. O caderno usa um simbolo de
   caixa marcada que o extrator le como `Check-square`, contra `SQUARE` nas
   demais. Prova e gabarito no mesmo arquivo.

125 cadernos renderam **5.021 questoes**, todas com materia e gabarito:

| materia | questoes | peso |
|---|---|---|
| Conhecimentos Especificos | 2.396 | 47,7% |
| Lingua Portuguesa | 1.048 | 20,9% |
| Conhecimentos Gerais | 754 | 15,0% |
| Nocoes de Informatica | 309 | 6,2% |
| Raciocinio Logico | 200 | 4,0% |
| Temas de Educacao | 180 | 3,6% |

E o achado que mais vale: dos 5.021, so **1.815 enunciados sao diferentes**. A
FEPESE reaproveita questao entre provas, e muito — uma delas aparece em **44
cadernos**. `radar repetidas` lista as campeas, que sao as que mais valem
estudar.

### Tres coisas que o PDF real ensinou

**A ordem do texto nao e a ordem das questoes.** O caderno e impresso em duas
colunas, e o extrator leu 1 a 15, depois 21 e 22, e so entao 16 a 20. A
primeira versao exigia ordem e parava na questao 20.

**O enunciado pode ter lista numerada dentro** ("1. ... 2. ... 3."). Partir dos
numeros quebrava a questao no meio e perdia as alternativas dela. A leitura
agora parte das ALTERNATIVAS: cada rodada de a ate e fecha uma questao.

**Cabecalho e rodape grudavam na ultima alternativa.** Alem dos padroes obvios
("Pagina 7"), o caderno repete um codigo em toda pagina ("AM2 Educador
Social"). Em vez de adivinhar padrao por padrao, o que se repete em toda pagina
e tratado como mobilia. A sujeira caiu de 5,1% para 1,1% das questoes.

### A lacuna que nao estava escrita

Respondendo as questoes no simulado, apareceu isto:

> Analise o periodo abaixo: medida que chegava hora de contar verdade...

Faltavam as lacunas, e sem elas a questao nao quer dizer nada. Dos 5.021
enunciados, **so 1 tinha underscore**.

Abrindo o PDF, o motivo: **a lacuna nunca esteve no texto**. A FEPESE desenha o
tracinho como grafico, e o extrator devolve so espaco em branco:

```
   medida que chegava    hora de contar
verdade, ficava ainda mais nervoso.
```

O vestigio existe — e a corrida de espacos — e a normalizacao de espaco em
branco o apagava. Agora `marcar_lacunas` roda ANTES de juntar as linhas, porque
a lacuna aparece em tres posicoes e duas delas somem ao juntar: no meio
(`chegava    hora`), no comeco da linha (`   medida`) e no fim (`contar    `
com a frase seguindo abaixo).

Medido em 8 cadernos antes de mexer: 68 corridas de 3 espacos ou mais, e a
unica que nao era lacuna foi `CADERNO   `, que a limpeza de mobilia ja tira.

Resultado no acervo: **258 enunciados** (5,1%) ganharam lacuna. A conferencia
que vale: nas 193 questoes cuja resposta vem em itens, o numero de lacunas bate
com o numero de itens em **188** delas. Os 5 restantes sao alternativas que ja
vem numeradas na origem.

Junto saiu outra sujeira: 178 caracteres que nenhuma fonte sabe desenhar — o
caderno usa simbolos de fonte propria — e que viravam quadradinho no meio do
enunciado. Viram espaco, e nao nada, senao a palavra de antes cola na de
depois. E o simbolo mais o espaco ao redor viram UM espaco, senao " simbolo "
daria tres espacos e seria lido como lacuna que nao existe.

`radar questoes --refazer` passa o parser novo por cima do acervo inteiro. Ele
atualiza a questao no lugar, pela chave (prova, numero), e nao apaga para
gravar de novo: o simulado guarda o id da questao, e o historico ficaria
apontando para o nada.

### O assunto fino, a unica parte que custa dinheiro

As materias universais foram resolvidas de graca, com um catalogo de
palavras-chave escrito a mao — ele cobre 76% dos enunciados de Portugues. Isso
funciona porque Portugues e sempre Portugues. Ja "Conhecimentos Especificos"
muda com o cargo, e o acervo tem 134 cargos: Servico Social, Psicologia,
Contabilidade, Enfermagem, cada area de professor. Um catalogo teria que cobrir
todas, e ai nao e mais catalogo, e adivinhacao.

**Custo medido no acervo: 1.813 questoes, US$ 0,26 (~R$ 1,43), uma vez so.**
Quatro coisas mantem esse numero baixo:

1. **uma questao por enunciado** — das 2.673 de Conhecimentos Especificos, so
   1.813 tem enunciado diferente. E o assunto pago se espalha para as copias:
   1.813 classificacoes atualizam 2.673 linhas;
2. **em lote**, com a instrucao enviada uma vez em vez de uma por questao;
3. **so o enunciado, cortado em 400 caracteres**, sem as alternativas — elas
   sao a maior parte do texto e nao dizem o assunto;
4. **Haiku**, que e o modelo barato. Dizer o assunto e rotulagem, nao
   raciocinio.

Tres travas contra susto na conta: **simular e o padrao** (sem `--valendo` o
comando so mostra o custo), **teto de gasto** conferido antes de cada lote com
o custo REAL que a API informou — e nao com a estimativa —, e **a chave so em
variavel de ambiente** (`RADAR_ANTHROPIC_KEY` no `.env`). Nao entrou biblioteca
nova: a API e REST e `requests` ja era dependencia.

**Uma ressalva honesta sobre o valor disto:** as questoes de Conhecimentos
Especificos do acervo sao de Psicologo, Assistente Social, Professor e Contador.
**Nenhuma e de Guarda Municipal ou Policia Penal.** Classificar esses assuntos
organiza provas de areas que nao sao a minha. Isso passa a valer no dia em que
entrar no acervo uma prova de cargo da minha area.

## Fase 5: o simulado

A ponta que fecha o ciclo: o radar acha o concurso, o acervo baixa as provas,
`radar questoes` separa as questoes, e aqui eu respondo elas.

Decisoes que vieram de usar:

- **o sorteio e por enunciado, nao por linha.** Dos 5.021 registros so 1.815
  sao perguntas diferentes, e sortear sem cuidado repetiria a mesma pergunta;
- **o estado fica no banco, nao na sessao do navegador.** Da para fechar a
  pagina no meio e voltar depois, e o F5 nao responde de novo;
- **a revisao vem no fim, com os erros primeiro.** Errar sem ver a correta nao
  ensina nada;
- **sem materia escolhida**, usa as que caem em qualquer concurso. O acervo nao
  tem prova de Guarda Municipal nem de Policia Penal, e essas quatro treinam
  mesmo assim.

Uma armadilha que custou tempo: somar a coluna booleana `acertou` direto no SQL
**nao funciona**. O SQLAlchemy devolve a soma com o tipo da coluna, entao 2
acertos voltam como `True` e viram 1 — todo mundo ficava com 50%. A conta passa
por `case(...)` para virar inteiro antes de somar.

## Fase 6: previsao de abertura

A conta tem chao e teto vindos da lei: o concurso vale por ate 2 anos,
prorrogaveis por mais 2. Antes de 2 anos o orgao ainda tem aprovado na fila;
passados 4, quem precisa de gente tem de abrir outro. **Dentro dessa faixa**,
quem manda e o ritmo do proprio municipio.

Duas escolhas que os dados reais forcaram:

1. **mediana, e nao media.** De Tubarao so se conhece 2011 e 2026, e a media
   dizia "um a cada 15 anos, proximo em 2041". O buraco e o que nao foi
   coletado, nao concurso que deixou de existir;
2. **teto de 4 anos.** Biguacu tem 2021 e 2022 no historico — dois editais do
   mesmo momento, nao um concurso por ano.

Toda previsao vem com o motivo e com os anos que a embasam. E a tela avisa o
que o historico **nao** cobre: ele vem da FEPESE (2006 a 2026) e do feed de
noticias (so 2026), entao municipio que contratou outra banca entre 2021 e 2025
aparece mais atrasado do que e.

### Uma grafia so para cada municipio

Isto quebrava a previsao antes de ela existir: o mesmo municipio estava no
banco em ate quatro grafias. A FEPESE grava `Palhoca` e o feed grava `Palhoça`;
`Florianopolis`, `Florianópolis` e `FLORIANOPOLIS` eram tres cidades para
qualquer conta por municipio.

Agora o municipio e gravado sempre na grafia de `config/regioes.yml`, que ja
era a fonte de verdade dos aneis. `radar reclassificar` conserta o que ja esta
gravado — inclusive o municipio confirmado pela pagina do edital, porque trocar
a grafia nao e reclassificar. Municipio de fora de SC volta como veio: o YAML so
tem municipio catarinense, e inventar grafia seria pior.

## Fase 7: macetes, e o que os dados corrigiram

**O "chute na C" nao existe nesta banca.** No acervo inteiro as cinco letras
ficam entre 19,5% e 20,5%. Nao ha letra mais provavel.

**A repeticao mentia nas contas.** Buscando "crase" saem 59 questoes, mas so
**7 enunciados diferentes** — a mesma questao aparece em 38 cadernos, e a
resposta dela e "d". Contando todas, o gabarito dizia "letra d em 64%", e a
conclusao seria chutar d. Agora gabarito e palavras contam **uma vez por
enunciado**; materia e forma de perguntar contam todas, porque questao repetida
pesa mesmo mais na prova que eu vou fazer.

Junto veio um minimo de amostra: **abaixo de 50 enunciados diferentes a pagina
nao afirma nada** sobre a letra. Com 7 questoes, o que parece tendencia e
sorteio.

Outros cuidados da aba:

- **nada e calculado antes de a banca ser escolhida.** O retrato do acervo
  inteiro misturava bancas e nao respondia pergunta nenhuma;
- a fatia da pizza e a **participacao no total de questoes**, e nao a media por
  prova: somar "questoes por caderno" de materias que caem em provas diferentes
  daria 81 numa prova de 40. O numero por prova fica na legenda;
- **questoes por caderno divide pelos cadernos em que AQUELA materia
  apareceu.** Temas de Educacao so cai em prova de professor; dividir pelo
  total faria parecer que cai pouco quando cai muito onde cai;
- os graficos sao pizza feita com `conic-gradient` no CSS, **sem JavaScript**,
  como o resto da tela. Acima de 8 categorias o resto vira uma fatia "outros";
- o assunto sai de um **catalogo de palavras-chave escrito a mao**. Cobertura
  medida em enunciados distintos: portugues 76%, informatica 61%, gerais 59%,
  raciocinio 53%. O que sobra e contado como "sem assunto detectado";
- a materia dominante do recorte so e afirmada com 60% ou mais das questoes:
  "crase" da 56 de 59 em Portugues, e recorte que mistura nao tem materia.

### Por que so aparece a FEPESE

O menu de bancas vem das **provas baixadas**, e nao dos concursos coletados.
AMEOSC, Cebraspe, FURB, FCC, FGV e IESES ja aparecem nos concursos, mas sem
prova no acervo — e a tela diz isso, em vez de parecer que o radar so conhece
uma banca. Incluir uma banca quer dizer escrever um coletor para o site dela.

### O que ainda nao esta la

Pegadinha especifica e macete de memorizacao **nao saem de contagem**: alguem
precisa ler as questoes e perceber o padrao. Isso fica para quando a leitura
por IA entrar. Ate la a pagina nao inventa.

## Fase 2.5: o que o edital exige de mim

`radar elegibilidade` le os editais que `radar provas` ja baixou e grava, em
cada concurso, o que ele pede: **escolaridade, idade, CNH e teste fisico**.

Tres decisoes:

**E por CONCURSO, e nao por cargo.** Um edital de prefeitura traz dezenas de
cargos com requisitos diferentes, e o radar guarda um registro por concurso.
Entao "elegivel" quer dizer uma coisa so: **este concurso tem vaga de nivel
superior**. Nao e promessa de que eu sirvo para todas as vagas dele.

**Cada achado guarda o trecho que o embasa.** O veredito sozinho nao da para
conferir, e as vezes ele engana: num edital de Florianopolis aparece "idade
maxima de 75 anos", que e a aposentadoria compulsoria da Lei Complementar
152/2015, e nao uma barreira de carreira. O trecho mostra isso.

**Edital digitalizado como imagem e apontado, e nao tratado como "nao exige
nada".** Medido no acervo: 3 dos 32 editais nao rendem texto algum — um deles
tem 2,5 MB e 34 caracteres.

Uma distincao que custou um teste: quase todo edital diz "aptidao fisica e
mental, verificada por junta medica oficial" — isso e exame admissional. O TAF,
que e o que elimina em concurso policial, aparece como "Teste de Aptidao Fisica
de carater eliminatorio". So o segundo conta.

Numeros da primeira rodada: 23 editais com vaga de superior, 15 exigindo CNH,
13 com idade minima declarada, 2 com idade maxima, 3 com teste fisico. E um
achado que interessa direto: **Brusque 2026 tem prova de aptidao fisica e exige
CNH categoria A** — perfil de guarda municipal.

### Edital retificado

Retificacao muda prazo, vaga e requisito — e descobrir tarde e o tipo de erro
que nao da para corrigir depois. O manifesto ja guardava o **sha256** de cada
arquivo desde a fase 3, para reconstruir o acervo noutra maquina; serve tambem
para isto: se o mesmo endereco passa a devolver bytes diferentes, o edital foi
retificado.

Tres cuidados, e os tres tem teste:

1. **so confere edital em pe.** Concurso encerrado nao vai mais ser retificado,
   e cada conferencia custa uma requisicao e um download;
2. **o manifesto passa a valer o arquivo novo**, senao toda conferencia seguinte
   repetiria o mesmo alarme. E o PDF em disco tambem e trocado: nao adianta
   avisar e deixar o acervo com a versao velha;
3. **pagina de erro nao vira retificacao.** Erro devolvido com HTTP 200 e comum;
   sem a checagem de que o arquivo e PDF, o acervo trocaria o edital por HTML e
   ainda acusaria mudanca.

A mensagem nao diz *o que* mudou, porque o sha256 nao sabe — ela diz que mudou,
qual arquivo, e manda o link para reler.

## Fase 2.2: o calendario

O prazo de inscricao e a unica coisa do radar que nao pode ser vista tarde
demais. O aviso do Telegram chega uma vez; o calendario lembra de novo **dois
dias antes** — um dia antes ja e tarde para juntar documento e pagar boleto.

A primeira versao baixava o `.ics` direto do menu, e um arquivo que aparece do
nada nao diz o que e nem o que fazer com ele. Agora ha uma pagina que explica
antes de oferecer o arquivo.

O formato iCalendar e texto puro, entao **nao entrou biblioteca nova**. Da
especificacao (RFC 5545), tres detalhes decidem se o arquivo e aceito:

1. **toda linha termina em CRLF.** Com LF sozinho o Outlook recusa;
2. **linha acima de 75 bytes e dobrada**, e a continuacao comeca com um espaco.
   Titulo longo de concurso e a regra aqui, nao a excecao — sem dobrar, o Google
   Agenda recusa o arquivo inteiro. A dobra conta BYTES, senao uma letra
   acentuada seria partida no meio;
3. **evento de dia inteiro termina no dia seguinte.** Com o mesmo dia nos dois
   campos, o compromisso some da agenda.

E um quarto detalhe, que nao e do formato mas do uso: o identificador do evento
vem do endereco do concurso, sempre igual. E assim que o calendario **atualiza**
o compromisso quando o prazo e retificado, em vez de criar um duplicado.

## Prova substituta: quando nao ha prova do meu cargo

O problema e concreto e nao tem jeito bonito: **Guarda Municipal e Policia
Penal, que sao os cargos que eu mais quero, nao tem uma prova sequer no
acervo**. Sao 134 cargos catalogados e nenhum deles e esse. Esperar a prova
aparecer nao e plano.

O que o radar faz e ordenar o que existe pela semelhanca, e dizer **em cima de
que** a semelhanca foi medida:

```
~ Guarda Patrimonial   FEPESE / Palhoca / 2024 / 40 questoes
    1 palavra(s) em comum no cargo: guarda; mesma banca (FEPESE); prova recente
```

O que ele nao faz e fingir equivalencia. Guarda Patrimonial divide uma palavra
com Guarda Municipal e e outra profissao — por isso o motivo diz "1 palavra em
comum", e nao "cargo equivalente".

**So entra quem divide ao menos uma palavra com o cargo.** Banca e municipio sao
desempate, e nunca motivo de entrada: sem essa regra, procurar "Policia Penal"
devolvia Merendeira e Professor de Ensino Religioso, so por serem da mesma
banca. Oito linhas de ruido sao piores que uma tela que admite nao ter nada.

E quando nao ha nada, a tela diz a coisa mais util — que e a que menos parece
resposta: que o que serve para esse cargo sao as materias que caem em qualquer
concurso, com as provas da mesma banca. Isso nao e consolo: essas materias
valem **20 das 30 questoes** de uma prova da IESES.

## O concurso estadual que parecia federal

"2019 – Secretaria de Estado da Administracao Prisional e Socioeducativa" — o
concurso da Policia Penal SC, o alvo principal — aparecia com o motivo "Sem UF:
pode ser federal com prova em Florianopolis". Dois buracos se somavam: a API da
FEPESE nao manda UF nenhuma, e o titulo de orgao estadual nao tem municipio
para o classificador achar. Sem UF e sem municipio, so restava `indefinida`.

O conserto tem duas metades, uma em cada camada:

- **a UF vem da fonte.** A FEPESE e a fundacao da UFSC e so organiza concurso
  estadual em SC, entao o coletor dela preenche `uf=SC` quando o titulo nomeia
  um orgao do estado. Antes de escrever a regra, os 520 concursos do historico
  dela foram conferidos: os 16 de orgao estadual sao todos de SC, e o unico
  concurso fora do estado e municipal (Paraiso do Tocantins, 2023);
- **o anel vem do classificador.** Com `uf=SC` e sem municipio, um orgao
  estadual cai numa relevancia propria, `estadual`, com o motivo "Orgao
  estadual de SC; polos de prova a confirmar no edital". Ela nunca vira
  `nucleo`: a sede e em Florianopolis, mas onde a prova e aplicada quem diz e
  o edital.

Na tela ela aparece como "Estadual SC", em aba propria — concurso do estado
nao e "perto" nem "longe". Entra nos avisos do Telegram, e na fila do
`radar detalhar` vem logo depois de `nucleo` e `proximo`.

Uma consequencia que vale saber: como a UF nasce no coletor, `radar
reclassificar` sozinho nao conserta registro antigo da FEPESE — ele so reaplica
a regra sobre o que ja esta no banco. Foi preciso um `radar coletar` antes. Na
primeira vez, 17 registros sairam de `indefinida` para `estadual`.

## Dois sintomas confusos que vale saber de cor

**O link aparece na tela mas da erro 404.** A tela e o codigo sao lidos em
momentos diferentes: o template e lido do disco a cada visita, entao o link novo
aparece assim que o repositorio e atualizado; o codigo Python e lido uma vez so,
na partida, entao a rota nova nao existe no servidor que ja estava rodando. A
solucao e parar o `radar web` com Ctrl+C e subir de novo. A pagina de erro
detecta esse caso sozinha, comparando a data dos `.py` com a hora em que o
servidor subiu.

**O `--recarregar` quebra no Windows.** Ele sobe um segundo processo que
reimporta o projeto, e isso falha quando o caminho da pasta tem espaco no nome —
que e o caso aqui. Por isso vem desligado por padrao.

## Etapa 8: Acompanhando, e o que o mural nao resolvia

O mural lateral mostrava os favoritos em qualquer aba, e resolvia bem o
problema para o qual nasceu: "nao me deixe perder isso de vista". Ele nao
resolvia o seguinte, que e o que eu de fato pergunto ao abrir a tela — "e
agora, o que eu faco?". Num cartao de seis linhas cabiam titulo, cidade,
salario e prazo, e nao cabia mais nada: nem o historico do concurso, nem o
proximo passo.

A aba Acompanhando desfaz esse aperto. Um bloco por favorito, com espaco para
as tres coisas que o mural nao tinha como mostrar:

- a **contagem de dias**, que responde "da tempo?";
- a **proxima acao**, que responde "o que eu faco?";
- a **linha do tempo inteira**, com data e link, que responde "como chegamos
  aqui?".

### A proxima acao e derivada, nunca adivinhada

E o unico campo interpretado da tela, e por isso o de maior risco. Ela sai de
dois fatos gravados — a `situacao` e o prazo lido do edital — e de mais nada.
A ordem das perguntas e a ordem em que elas mandam: prazo correndo vence
qualquer outra coisa, porque e a unica que tem hora para acabar.

Dois casos mereceram tratamento proprio:

- **situacao aberta, prazo desconhecido.** Isso e urgente e ao mesmo tempo
  impossivel de quantificar. A tela diz as duas coisas: "inscrever-se; o prazo
  esta aberto, mas a data-limite eu nao sei — confira na pagina do concurso";
- **situacao aberta, prazo vencido.** Aqui os dois registros se contradizem, e
  quem manda e a data: "conferir na fonte: o prazo que eu tenho ja venceu, mas
  o registro ainda diz aberto". A alternativa seria a tela escrever "faltam -3
  dias", que e pior do que nao dizer nada.

Situacao que nao diz nada vira "nao sei ainda", com a mesma marca amarela de
`foco.py`. Dado errado sobre o meu proprio concurso e pior que tela vazia.

### O corte do que toca o celular

A tabela `eventos` grava seis acontecimentos, e avisar os seis no Telegram
seria transformar em notificacao coisa que e so tramite. O corte ficou em
cinco, e por consequencia, nao por raridade: **edital publicado, edital
retificado, inscricao abrindo, inscricao fechando e prova marcada** — os cinco
que mudam o que eu tenho que FAZER. "Apareceu" e "mudou de prevista para
autorizado" ficam na linha do tempo, para eu ler quando quiser.

Isso obrigou uma mudanca em `eventos.py`: `edital_publicado` caia no generico
`mudou_situacao` junto com o resto do ciclo, e nao dava para avisar so ele sem
avisar tudo. Ganhou tipo proprio.

O aviso de favorito e outro aviso, e nao um caso do que ja existia. O
`avisar()` responde "apareceu algo que pode me interessar?", e por isso filtra
por distancia; `avisar_favoritos()` responde "mudou algo no que eu JA escolhi
seguir?", e para essa pergunta filtro nenhum faz sentido — um favorito de
Capinzal avisa igual. No `radar atualizar` ele roda primeiro: se o teto do dia
cortar alguma coisa, que corte a descoberta, e nao a mudanca no meu favorito.

A fila e por evento, com a coluna nova `eventos.avisado_em`, e so marca o que
realmente saiu. Telegram fora do ar deixa a fila em pe para a proxima coleta,
como ja acontecia com o aviso de concurso novo.

### A promessa que o mural cumpria sozinho

"NENHUM filtro esconde um favorito" era uma decisao da fase 2, e quem a
cumpria era o mural: ele aparecia em toda aba, entao o favorito de Itajai
nunca sumia. Tirar o mural sem mais nada teria reduzido a promessa a "nenhum
filtro esconde um favorito **dentro da aba Acompanhando**", que nao e a mesma
coisa.

Ela desceu para a consulta. Em `servico.listar`, o favorito escapa dos
recortes que eu **nao** pedi — o anel padrao da tela e a faixa de remuneracao.
Nao escapa do que eu digitei: busca por palavra, anel escolhido a dedo e a aba
"Abertos" continuam sendo perguntas, e resposta com favorito de outro lugar no
meio e filtro que deixou de responder.

## Etapa 9: estudar pelo alvo

Tres coisas que pareciam separadas e sao a mesma: o radar sabia o que eu quero
prestar, sabia que provas existem e sabia como eu vou no simulado — e nao
cruzava nada disso. O botao de treino sorteava sempre do mesmo balde de 160
questoes, a busca por prova parecida nao achava as provas do meu proprio
cargo, e o quadro de materias do edital nao sabia que eu vou mal em Direitos
Humanos.

### O cargo que mudou de nome

`radar parecidas "policial penal"` devolvia nada, com duas provas do cargo
catalogadas no acervo. O motivo e que elas estao gravadas com o nome da epoca,
"Agente Penitenciario", e o cargo hoje se chama Policial Penal.

Isto nao e problema de busca: os dois nomes **nao dividem uma palavra sequer**.
Nenhum ajuste de semelhanca de texto ia resolver — quem sabe que sao o mesmo
cargo sou eu, e ja estava escrito em `config/alvo.yml`, na lista de `termos`
que o radar usa para reconhecer o cargo no feed. Ela passou a valer tambem
como lista de sinonimos.

A parte que exigiu cuidado foi a regra de entrada. Aceitar "uma palavra em
comum com algum sinonimo" encheria a lista: "agente penitenciario" arrastaria
Agente Administrativo, Agente de Servicos e Agente Comunitario. Por isso o
sinonimo tem que caber **inteiro** no cargo do acervo — "Agente Penitenciario
- Feminino (AP)" tem as duas palavras e entra; "Agente Administrativo" tem uma
e fica fora.

### O balde que acabava

O botao "Treinar 20 questoes" passava um filtro de cargo para o sorteio comum,
e `criar_simulado` aceita um filtro so. Por isso existia `cargo_para_treinar`,
que escolhia na mao **um** termo do YAML — o primeiro que achasse prova. Com
160 enunciados distintos no acervo do cargo, oito rodadas de 20 acabam com
eles, e dali em diante o botao so repetia.

A regra nova tem tres degraus, nesta ordem:

1. as questoes das provas do proprio cargo (2013 e 2019). Sao a prova de
   verdade, e nenhuma outra chega perto;
2. as da mesma banca **nas mesmas materias**, em outros concursos. Sao 356
   enunciados distintos, e e a segunda melhor coisa: a FEPESE cobra Portugues
   do mesmo jeito em qualquer caderno que faca;
3. so entao repete o que eu ja respondi — e a rodada registra que repetiu.

"Acabar" e por **enunciado ja respondido**, em qualquer simulado, e nao por id
de questao: a mesma pergunta aparece em varios cadernos, e reve-la com outro
numero nao seria questao nova.

O filtro de materia e o que impede o degrau 2 de virar "qualquer coisa". Das
7.046 questoes que a FEPESE deixou em outros cargos, entram 2.129:

    Lingua Portuguesa      1.425      Direito Constitucional    20
    Nocoes de Informatica    329      Legislacao Estadual       20
    Raciocinio Logico        295      Direito Administrativo    12
    Direitos Humanos          20      Direito Penal              4

As 3.265 de "Conhecimentos Especificos" ficam de fora inteiras, que e o ponto:
Conhecimentos Especificos de Merendeira e da mesma banca e nao me serve de
nada.

### Por onde comecar hoje

O quadro do edital dizia o que vale mais e o simulado dizia como eu vou, cada
um na sua tela. Juntos eles respondem a pergunta que nenhum dos dois responde
sozinho: **por onde eu comeco a estudar hoje**.

A tabela de materias ganhou a coluna "Meu acerto", e duas marcas:

- as materias **acima da media da propria prova** ficam em negrito. O corte
  nao e um numero escolhido a mao — e o total de questoes dividido pelo numero
  de materias, e se ajusta sozinho quando o edital muda. No de 2019 sao sete,
  e elas valem 80 das 100 questoes;
- a **pior entre essas sete** ganha cor e o rotulo "comece por aqui". A pior
  entre as pesadas, e nao a pior de todas: errar numa materia de 5 questoes
  custa 5 questoes; errar numa de 15 decide a prova.

Materia que eu nunca treinei aparece como "nao treinei" e nao concorre ao
destaque. Zero por cento diria que eu errei tudo, quando o que houve foi eu
nao ter feito — a mesma regra de nunca inventar que vale para o resto da tela.

## Etapa 10: dividir o servico sem mudar nada

`servico.py` tinha 2.704 linhas e cinco assuntos dentro. O objetivo era um so:
separar por assunto **sem mudar comportamento nenhum**. Por isso o arquivo
virou pacote em vez de virar cinco modulos soltos - `servico/__init__.py`
reexporta tudo, e nenhum chamador precisou mudar.

A divisao saiu em seis commits, um arquivo por commit, com `pytest -q` passando
em cada um:

    comum.py      54 linhas   o que mais de um assunto usa
    coleta.py    348 linhas   rodar as fontes, gravar, classificar
    avisos.py    192 linhas   quem vira mensagem, e quando
    simulado.py  490 linhas   montar a rodada, responder, medir
    provas.py    757 linhas   acervo, cadernos, padrao da banca, substituta
    previsao.py  125 linhas   quando o municipio costuma abrir de novo
    __init__.py  969 linhas   consulta, favoritos, detalhe, elegibilidade,
                              retificacao, calendario - e a fachada

### Tres coisas que so aparecem quando se divide

**Uma funcao que nunca rodava.** Havia DUAS `_ano_do_concurso` no arquivo, uma
na secao do acervo e outra na da previsao, e a segunda apagava a primeira em
silencio - nos dois lugares rodava a segunda. Dividir sem notar isso teria
devolvido a primeira ao acervo e mudado comportamento sem ninguem ver: a morta
aceitava quatro digitos quaisquer no inicio do titulo, a viva exige "2020 -" e
ainda le "Edital 003/2018". A morta foi apagada.

**Um nome que some sozinho.** Com `servico/provas.py` existindo, o atributo
`servico.provas` passa a ser o submodulo - e isso apaga o `from radar import
provas` que o `__init__` fazia. A retificacao foi chamar `carregar_manifesto`
no lugar errado e quebrou na hora. O apelido `arquivos_de_prova` resolve dos
dois lados, e o teste vermelho foi o que avisou.

**Dois testes que testavam a copia.** `servico.COLETORES` e `servico.Buscador`
viraram nomes reexportados; quem os LE sao `servico.coleta` e `servico.provas`.
Trocar a copia deixaria os dois testes verdes sem testar coisa alguma, e foi
exatamente o que aconteceu ate eles serem apontados para o modulo certo.
Trocar atributo de CLASSE - como os testes de retificacao fazem com
`servico.Buscador.get` - continua funcionando de qualquer lado, porque a classe
e a mesma.

### A ordem importou uma vez

`recado_sobre_o_cargo`, do assunto provas, chama `materias_universais`, do
simulado. Movendo o simulado primeiro, a dependencia aponta numa direcao so e
nao ha import circular para contornar.

## Etapa 14-D: onde estudar primeiro

A tabela de materias respondia "que materia pesa mais" e "onde eu vou pior".
Nenhuma das duas e um plano de tarde: **Direitos Humanos vale 15 questoes, mas
"estudar Direitos Humanos" nao e uma tarefa** - estudar as Regras de Mandela e.
A secao nova desce esse andar.

A conta cabe em duas linhas, e nao ha nada alem dela:

    questoes esperadas = quantas questoes o edital reserva para a materia
                         x a fatia que aquele assunto ocupa nas provas
    pontos a ganhar    = questoes esperadas x (1 - meu acerto no simulado)

"Pontos a ganhar" e o numero que decide, e ele nao esta em nenhum dos dois
lados sozinho: um assunto de 10 questoes em que eu acerto 90% vale 1 ponto a
recuperar, e um de 4 questoes em que eu acerto 25% vale 3. O segundo e onde a
tarde rende mais.

### Duas origens de assunto, e a tela diz qual e qual

O projeto ja tinha duas: Portugues e Raciocinio Logico saem do catalogo de
palavras-chave do `macetes`, de graca; as outras nove materias saem da coluna
`assunto`, que a IA escolhe dentro do conteudo programatico do edital e que
custou dinheiro uma vez. A secao usa as duas com a mesma formula - a fatia e
sempre "marcas deste assunto sobre marcas de todos os assuntos daquela
materia" - e mostra a procedencia em cada linha.

### O assunto que eu nunca treinei nao vale zero

Ele fica com `acerto=None` e `pontos=None`, barra amarela, e entra na ordem
pelas **questoes esperadas** - que e o teto dos pontos a ganhar, ja que
`pontos <= esperadas` sempre. Zero por cento diria que eu errei tudo, quando o
que houve foi eu nao ter feito: a mesma regra do resto da tela.

### Duas provas nao sustentam uma fatia

Existem duas provas do cargo, 170 questoes. Dividir 8 marcas por 8 e dizer
"100% da materia" e uma conta que uma prova a mais desmonta. Por isso entra o
**reforco**: a mesma banca, nas MESMAS materias, em outros concursos - a FEPESE
cobra crase do mesmo jeito em qualquer caderno que faca. Os dois numeros somam
na fatia e **nunca aparecem somados na tela**: "13 do meu cargo · 57 de
reforco" e uma informacao diferente de "70 questoes".

A contagem e em **enunciado distinto** dos dois lados. No reforco a banca
reaproveita muito, e uma questao que aparece em 38 cadernos decidiria o grafico
sozinha - o mesmo motivo que fez o `macetes.uma_por_enunciado` existir.

### O que a secao custou em tempo de tela

Meu foco abria em 0,06s. A primeira versao da secao levou para 0,94s, e duas
coisas explicavam quase tudo:

- `macetes.assuntos_de` tirava o acento do enunciado **uma vez por padrao**, e
  sao ate 18 padroes por materia. Normalizar uma vez por questao levou a
  abertura para 0,27s, e deixou a aba Macetes mais rapida de brinde;
- a contagem de "quantos ficaram sem assunto" rodava o catalogo inteiro de
  novo. Ela passou a sair junto da contagem principal.

Ficou em 0,16s. A secao varre ~2.000 questoes a cada abertura, entao os 0,1s
de diferenca sao o preco dela, e nao desperdicio.

### As 93 escolhas, e as 6 que ficaram indefinidas

> **Desfeito em 25/09/2026.** Estas 93 classificacoes **nunca passaram pela
> API**: foram escritas durante a sessao de trabalho e exportadas como se
> fossem saida do modelo. O arquivo foi zerado e a coluna `assunto` limpa. O
> que segue abaixo fica como registro do que foi feito - nao como descricao do
> estado atual. O relato completo esta em "Os 93 assuntos que nunca foram
> pagos", em [decisoes.md](decisoes.md), e na Etapa 15-0 no fim deste arquivo.

As 99 questoes do cargo foram classificadas escolhendo DENTRO do programa do
edital, e o nome gravado e copiado do programa letra por letra. Seis ficaram
sem assunto de proposito:

- tres de Direito Penal falam de **lei penal no espaco** (crime cometido no
  estrangeiro, cumprimento de pena fora do pais), que o programa de 2019 nao
  lista. Rotular seria inventar um assunto que a prova de hoje nao cobra;
- duas tem o **enunciado cortado no PDF** ("De acordo com o Codigo de Processo
  Penal, e") - nao ha o que classificar;
- uma e generica demais ("Assinale a alternativa correta em materia de
  Direitos Humanos").

O caderno de 2013 cita a LC 472/2009, que a LC 675/2016 substituiu. O ASSUNTO
e o mesmo - plano de carreira e vencimentos - e e ele que o programa de hoje
lista, entao a questao de 2013 conta para a LC 675. E o que faz o acervo antigo
servir para a prova nova.

## Etapa 14-F: config/leis.yml

Cada materia e assunto de Direito ganhou o endereco do texto oficial, e a secao
mostra um link "ler a lei". **E so link.** O radar nao baixa e nao guarda o
texto de lei nenhuma: lei muda, e o unico lugar em que a versao vigente esta
certa e a fonte.

Duas fontes, e ha teste guardando que nao entre uma terceira: **Planalto** para
lei federal e Constituicao, **ALESC** para lei estadual de SC. Um link para
site de resumo de lei entraria sem ninguem perceber, e resumo de lei nao e lei.

Os 15 enderecos foram abertos de verdade antes de gravar - todos responderam
200 e o titulo da pagina confere com a lei. Os da ALESC redirecionam para o
endereco canonico `/ato-normativo/<numero>`, e e ele que esta gravado.

O casamento nao e por texto exato: o `quando` do YAML e uma marca procurada
DENTRO do nome do assunto, como os `termos` do `config/alvo.yml`. O assunto do
edital tem 126 caracteres em um dos casos, e copiar a frase inteira seria
copiar um texto que a proxima edicao reescreve.

### Tres coisas que ficaram sem link, e por que

- **Regras minimas da ONU para o tratamento de pessoas presas** (Regras de
  Mandela). Nao e lei brasileira: nao esta no Planalto nem na ALESC. Tem
  traducao oficial publicada pelo CNJ, que nao e nenhuma das duas fontes - e
  apontar para outro lugar seria inventar a fonte.
- **Assunto de doutrina** (Teoria geral dos direitos humanos, Afirmacao
  historica, Modelos de gestao) nao tem texto oficial para abrir.
- **Lingua Portuguesa, Raciocinio Logico e Sociologia Aplicada** nao sao
  Direito.

### Duas divergencias que o YAML registra em vez de esconder

- A **Lei 4.898/1965** (abuso de autoridade), que o edital de 2019 cobra, foi
  revogada pela Lei 13.869/2019 em setembro daquele ano. O link e o que o
  edital pede, e uma `nota` aparece na tela junto dele: eu nao posso estudar
  uma lei revogada sem saber que ela esta revogada.
- O edital escreve a **LC 529** como de "17 de dezembro de 2011"; a ALESC
  publica a mesma LC 529 como de 17 de janeiro. O numero, o ano e o texto do
  Regimento Interno conferem - um dos dois errou o mes, e a nota diz isso.

## Etapa 15: questao gerada pela IA, para treinar

O acervo tem 8.433 questoes reais, e as do meu cargo sao 152 com gabarito
conferido. Uma prova tem 100. Treinar duas vezes nas mesmas 152 e reconhecer a
pergunta de cor em vez de saber a regra - e foi dai que veio o pedido de gerar
questao nova.

A etapa inteira gira em volta de uma frase: **questao gerada serve para
TREINAR, nunca para MEDIR o que a banca cobra.** O risco nao e a IA escrever
uma questao ruim; e a questao gerada entrar na incidencia e eu passar a estudar
pelo que ela inventou achando que e o que a FEPESE cobra.

### A separacao nao e um filtro, e uma tabela

A escolha estrutural da etapa foi `questoes_geradas` ao lado de `questoes`, e
nao uma coluna `gerada` dentro das reais. As duas dariam no mesmo hoje. A
diferenca aparece depois:

- com a coluna, dez consultas precisam do filtro - incidencia, peso das
  materias, macetes, "Onde estudar primeiro", cobertura, sorteio do simulado,
  contagem do acervo, e mais. Todas passam a depender de alguem lembrar;
- com a tabela separada, `select(QuestaoDeProva)` simplesmente nao alcanca a
  outra. A decima primeira consulta, que ainda nao foi escrita, ja nasce certa.

O preco disso foi uma coluna nova em `respostas_de_simulado`: `gerada`, dizendo
em qual tabela o `questao_id` daquela linha existe. Ela nao e enfeite - as duas
tabelas numeram a partir do 1, e sem ela responder a questao gerada 5 marcaria
a questao real 5 como ja respondida. Seria um erro mudo: uma pergunta real que
nunca mais aparece no sorteio, e ninguem descobre por que.

Ha um teste chamado `test_questao_gerada_nao_entra_em_nada_que_meca`. E o mais
importante do arquivo, e existe para estourar no dia em que alguem juntar as
duas coisas.

### O Planalto disse nao, e nao pelo motivo esperado

O plano era baixar o texto do artigo e mandar junto no pedido, para reduzir o
risco de gabarito errado. Conferido em 24/09/2026:

- **`planalto.gov.br/robots.txt` responde 404.** Pela convencao, isso quer dizer
  que nada esta proibido. O robots nao era o problema;
- **o problema e o User-Agent.** Alternando as requisicoes varias vezes: com o
  UA honesto do projeto ("radar-concursos/0.1 ...") a conexao e derrubada; com
  "curl/8.4.0", derrubada; com um UA de Chrome, HTTP 200 e 307 KB de HTML.

Ou seja: para baixar a lei o radar teria que se disfarcar de navegador. O
CLAUDE.md manda identificar-se no User-Agent, sem excecao, entao a resposta e
nao - e a decisao antiga de que o radar so aponta o link da lei sai
confirmada, e nao contrariada.

O que ficou no lugar e mais honesto do que parece. No modo variacao a ancora e
o gabarito oficial da questao de origem, que a banca publicou; e em todo caso
a IA declara em que ARTIGO se apoiou, e a tela mostra o artigo junto do link do
`config/leis.yml`. A conferencia e minha, e leva 10 segundos - o que e bem
diferente de confiar que o modelo acertou.

### Variacao e o padrao; do zero e a excecao

Variar parte de uma questao real com gabarito definitivo conferido e pede para
mudar cenario e numeros mantendo a regra juridica. O estilo ja e o da banca de
verdade, e a resposta esta presa a uma pergunta cujo gabarito existe.

O modo do zero so entra quando nao ha questao real na materia. Ali as reais
viram exemplo de ESTILO - e vao **sem gabarito**, de proposito: mandar a
resposta junto convidaria o modelo a copiar o conteudo em vez do formato.

A base e so a prova do meu cargo no meu estado, a mesma regra do Meu foco.
Questao anulada fica fora: a banca desfez a pergunta depois dos recursos, e
variar o que nao tem gabarito seria multiplicar o problema.

### O gasto

`claude-sonnet-5`, e nao o modelo barato do `radar assuntos`. La o erro do
modelo fraco e um rotulo torto que eu vejo na tabela; aqui seria um gabarito
errado que eu estudaria como certo. US$ 2,00 por milhao de tokens de entrada e
US$ 10,00 de saida, com raciocinio adaptativo em esforco medio.

Medido na simulacao, no acervo de verdade: **5 questoes custam US$ 0,06**
(~R$ 0,31), em 2 chamadas. O teto padrao e US$ 0,90 - uns R$ 5 - conferido
antes de cada chamada contra o gasto real que a API informou, como no
`radar assuntos`. E por execucao, e nao por mes: o radar nao conta o mes, e
fingir que conta seria pior que nao ter teto.

### A simulacao mostra o pedido, e nao questao inventada

`radar gerar` simula por padrao, e a simulacao imprime a **instrucao e o pedido
exatos** que iriam para a API - nao um exemplo de questao gerada. A questao so
existe depois da chamada; mostrar um "exemplo" seria apresentar texto inventado
como se fosse saida do modelo. Foi a mesma linha que a apuracao da parte 0
desta etapa cobrou, e ela vale para o codigo tambem.

### A tela

Terceira aba em Estudar, ao lado de Macetes e Simulado. Escolher a materia
recarrega a pagina com o custo daquela escolha; so entao aparece o botao que
gasta, com o preco escrito nele. Dois passos, sem JavaScript, porque um
formulario so deixaria o botao de gastar com o preco de uma escolha anterior.

Ao gerar, cai no `/simulado/<id>` de sempre - nao ha segunda tela de responder
questao. O selo fica acima do enunciado, e nao no rodape: eu preciso saber que
a questao e de IA antes de ler, e nao depois de responder.

"Essa questao esta errada" marca a questao e apaga as **respostas** dela em
todas as rodadas. A questao fica guardada de proposito - o erro acumulado e o
que me diz depois se um assunto da errado toda vez, e ai o problema nao e a
questao, e o pedido que eu mandei. As respostas saem porque uma questao que eu
declarei errada nao pode continuar pesando no meu acerto, para nenhum lado.

E o acerto aparece em dois numeros em toda tela que o mostra, sem nenhum lugar
que os some. `desempenho_das_geradas` e funcao separada, e nao um parametro de
`desempenho`: o parametro convidaria alguem a somar os dois um dia.

## Etapa 15-0: zerar os 93 assuntos sem procedencia

A etapa 15 comecou com uma apuracao, e nao com codigo: "o `data/assuntos.json`
tem 93 questoes classificadas, mas eu nunca pus credito na Anthropic".

Estava certo. Nao existe `RADAR_ANTHROPIC_KEY` no `.env` - arquivo nao tocado
desde 22/09, dois dias antes de o JSON ser escrito - nem nas variaveis de
ambiente do Windows (User, Machine, processo). Sem chave, `radar assuntos
--valendo` sai com codigo 1 antes de montar a requisicao, e `classificar_assuntos`
devolve `{"erro": "sem chave"}`. Nao havia como aquelas linhas terem vindo da
API.

Havia dois caminhos no codigo que escrevem `assunto` no banco: `gravar_assuntos`
(resultado da API) e `importar_assuntos` (a partir do proprio arquivo). O
arquivo nasceu vazio (`[]`) num commit e ganhou as 93 entradas quatro horas
depois, ja identico byte a byte ao que `exportar_assuntos()` produz - ou seja, o
banco foi preenchido primeiro e depois exportado.

A prova mais direta estava no proprio historico: a secao "As 93 escolhas"
explicava **por que** seis ficaram indefinidas ("enunciado cortado no PDF",
"generica demais"). O caminho da API nao produz isso - `classificar_lote`
descarta "indefinido" e resposta fora da lista em silencio, so com `log.info`.
Aquele texto so sai de alguem que leu os 99 enunciados.

### Por que zerar, tendo os rotulos conferido

Uma amostra batia com os enunciados, e os 93 estavam todos dentro da lista de 85
assuntos do edital. Mesmo assim saem, e a razao e a regra do projeto inteiro:
**dado que eu nao posso auditar e pior que dado nenhum.** Auditar 93 um a um
custaria mais do que reclassificar, e um acervo em que parte dos rotulos tem
procedencia e parte nao teria e um acervo inteiro em que eu deixaria de
confiar.

Saiu o conteudo de `data/assuntos.json` e a coluna `assunto` de 98 linhas do
banco - 93 enunciados distintos. Ficaram as 8.433 questoes, com materia,
alternativas, gabarito definitivo e anuladas: nada disso passou pela IA. O
gabarito definitivo e o gerador da etapa 15 nao foram tocados.

### As duas portas, e por que sao duas

O formato antigo nao tinha campo de procedencia nenhum: `{impressao, assunto,
materia}`. Rotulo escrito a mao e rotulo pago eram o mesmo registro, e por isso
nao havia o que conferir.

Agora o banco tem `assunto_modelo` e `assunto_em`, e o arquivo carrega `modelo`
e `classificado_em` por linha. `gravar_assuntos` **exige** o modelo e levanta
erro sem ele - nao registra em log e segue, porque gravar em silencio sem
procedencia e exatamente o que nao pode se repetir. E `importar_assuntos`
**recusa** linha sem os dois campos, com o `radar importar` dizendo quantas
recusou.

A segunda porta e tao necessaria quanto a primeira: o arquivo e versionado e
editavel a mao, e foi por ele que os 93 rotulos chegaram ao banco daquela vez.

### O que zerar revelou na tela

Com os 93 fora, nove materias de Direito - 75 das 100 questoes do edital,
incluindo a Lei de Execucao Penal, que vale 10 - **sumiram** de "Onde estudar
primeiro", e a secao passou a mostrar so Portugues e Raciocinio Logico, que
saem do catalogo de palavras-chave e nao custam nada.

Sumir e a tela dizendo "esta materia nao cai", quando o que houve foi "eu nao
classifiquei nada dela". O bug ja existia; zerar foi o que o tornou visivel. O
painel ganhou `materias_sem_assunto` e a secao passou a listar cada uma com o
peso dela no edital, sob a marca "nao sei ainda" - em lista, e nao em barra,
porque barra e uma medida e a medida e justamente o que falta.

Numeros depois de zerar: 0 questoes com assunto de Direito, 108 questoes das
minhas provas sem assunto (eram 15), e 12 barras no grafico, todas de Portugues
e Raciocinio Logico.

---

# De 25/09 a 01/10/2026: a especificacao, o cronograma e o primeiro dia de estudo

Ate aqui o historico parou na etapa 15-0. O que veio depois estava so no git e
no `decisoes.md`. Cada bloco abaixo diz o que foi feito e em qual commit; o
**porque** de cada escolha esta em [decisoes.md](decisoes.md), e o que ficou
aberto esta em [pendencias.md](pendencias.md).

## A especificacao do redesign (25/09, fases 0 a 6)

`afd4ae3` gravou `docs/especificacao.md` e o CLAUDE.md passou a apontar para
ela. Uma fase por vez, cada uma com commit:

- fase 0, auditoria (`0a5cf79`): `radar auditar` escreve `docs/auditoria.md`,
  com a contagem por materia contra o quadro do edital, o gabarito definitivo e
  as anuladas. Tudo bate nas tres provas; a ordem das materias de 2016 denuncia
  um rotulo trocado (questoes 49-60). Na mesma rodada: backup dos simulados em
  `data/simulados.json` e a prova de 2016 como reforco (nunca somada a 2013 e
  2019). A tela `/auditoria` veio depois (`34cd6cf`);
- IA sem pagar (`1360929`): `radar gerar --pedido` grava os pedidos em
  `data/pedido_ia.json`, o Claude Code responde em `data/resposta_ia.json` e
  `radar gerar --importar` confere e grava, com procedencia "Claude Code,
  importado manualmente, em <data>";
- fase 5, Central de Macetes (`78ea3ee`): um cartao por materia, com o selo
  verde (padrao da banca, por contagem) separado do vermelho (macete de IA, com
  fonte e procedencia). A lista de leis alteradas nao foi gravada;
- fase 1, design system (`1ff4b41`, `1b5d40c`): `design.css` com tokens, os seis
  selos como macro e o modo escuro; depois "nenhum numero sem fonte" em todas as
  telas;
- fase 2, navegacao e home (`35bfc34`): seis destinos e a home de tres blocos
  (alvo, o que estudar agora, o que revisar), que cabe em 1366x680;
- descartar simulado (`153db8b`), tela de questao e relatorio (`835efd3`),
  "so meus erros" e o compilado de 40/50/100 pelos pesos do edital (`5ee1633`),
  revisao espacada 1-7-30 com fator de tempo na prioridade (`214e94c`);
- duas rodadas de acerto: o acumulado pela ultima resposta de cada questao
  (`17207ad`) e um minimo de respostas so, 5 na materia e 3 no assunto
  (`691c3a0`). `89d633a` reescreveu o "Estado atual" do CLAUDE.md.

Acervo conferido no banco nessa data: 8.433 questoes, 3.372 enunciados, 10
anuladas.

## O cronograma do Ciclo 1 (26/09)

Nasceu de uma conversa de estrategia fora do repositorio (perfil de estudo,
FEPESE, edital de 2019) e de uma planilha. Primeira versao recusada pelo
usuario, que pediu estudo especifico em tudo: duas horas de teoria de manha e
questoes a tarde e a noite. O que entrou como dado em `config/cronograma.yml`:
Ciclo 1 de 28/09 a 07/11/2026, 36 dias de estudo e 1.690 questoes.

- `a507654`, `815f9fb`: o YAML como veio da planilha e `cronograma.py` (puro),
  que confere o arquivo e calcula o horario de cada faixa a partir do inicio do
  bloco, com a rampa por nivel de 1 a 6 em Direito e Portugues;
- `f5eb720`: o diario (`radar hoje --marcar`, tabela `registros_de_estudo`,
  copia em `data/registro_estudo.json`);
- `dcbf107`: o gatilho que sobe, mantem ou desce o nivel da semana sozinho;
- `2de0f0e`, `412a73f`: a tela Hoje na web, o cartao na home e a documentacao;
- dois bugs do gatilho, os dois pegos na auditoria, olhando a tela: `fdde951` (o dia
  visto em setembro usava 28/10 como "hoje" e dava nivel 1 com 45 questoes; o
  "hoje" do gatilho passou a ser o menor entre o dia visto e o dia real) e
  `d42c842` (a reduzida trazia o numero de Direito gravado, e nao o do nivel).
  A primeira correcao foi pulada por engano uma vez; so a segunda rodada
  fechou.

## A Parte A: a tela Hoje como ela e (26/09)

Escuro como padrao com botao na barra (`3d769da`); faixa azul no topo, coluna
lateral e bloco das 22h em sobreaviso (`0cf0fcd`); circulo de "feita" em cada
faixa e formulario que sugere a meta (`99b657f`); botao Plano B de 30 min ou 1
hora, com o essencial do tema (`52a38aa`); cronometro com aviso em tela cheia,
som e notificacao do Windows, o unico JavaScript do radar (`be49a77`); sequencia
de dias sem zerar e a frase da semana (`e3f315a`); `radar web --rede` para o
celular (`0285a85`); `radar descartar --vazios` (`4c3b6cf`); documentacao
(`1404b09`).

A notificacao do Windows nao apareceu de primeira. O que resolveu foi o botao
"Testar em 10 s" e a linha de diagnostico no cartao (`95d5bad`), mais conferir
as configuracoes de notificacao do Windows. Depois disso o balao aparece; falta
so ativar a permissao no navegador (ver pendencias).

## B1, C1, D1 e D2 (26 e 27/09)

- `953e1ba` (B1): Simulado e Gerar questoes migrados para o `design.css`. So
  estas duas foram feitas; seis telas ainda usam o CSS antigo (ver pendencias);
- `3b0b249` (C1): o nome da SEJURI sozinho marcava alvo principal e dois
  seletivos (CASE e medico) viraram aviso de alarme no Telegram. Agora, sem o
  cargo no texto, o orgao exige "concurso publico" ou a banca das edicoes
  anteriores, e nenhuma palavra de selecao. Os dois seletivos sairam; 2013, 2016
  e 2019 continuam;
- `303cac5` (D1): tudo automatico no Windows. `radar subir`, `parar`, `status`,
  `agendar` e `backup`; duas tarefas no Agendador, "Radar - web" no logon e
  "Radar - backup" as 23:30, no usuario e sem administrador, criadas por XML
  para ligar o "executar assim que possivel". Nao e servico do Windows;
- `9ca6c04` (D2): o mapa do ano (seis etapas) como bloco do `cronograma.yml` e
  cartao na lateral da tela Hoje.

## Fase E: o diario passa a medir (27/09)

- `40add6a` (E1): o caderno de erros, com a regra certa obrigatoria e revisao
  1-7-30 propria (`data/caderno_erros.json`);
- `9a3dad0` (E2): acertos na propria faixa, o estudo extra e o total do dia
  (`data/estudo_extra.json`); a meta usa so questao sem consulta; bloco
  `materias` no YAML com as 11 materias do edital e a meta de 79 de 100;
- `3efe4c2` (E3): a aba Semanas, agrupada pelos ciclos do mapa, com reflexao
  da semana (`data/notas_semana.json`) e as mesmas contas do dia;
- `3e225fb` (E4): a aba Minhas materias, com a projecao "se a prova fosse hoje".

A suite chegou a 1.838 testes verdes no Linux dessa data, fora os dois abaixo.

## O primeiro dia de estudo e o que ele mostrou (28/09 a 01/10)

- `b206a31` (dados) e `c8609b5`: 20 questoes de treino sobre a aplicacao da lei
  penal (CP, arts. 1 a 12), respondidas pelo Claude Code sem chave da API, pelo
  fluxo `gerar --pedido` / `--importar`. O arquivo tem 40 questoes geradas, todas
  em modo `do_zero`;
- o fluxo de tres passos (pedido, resposta, importar) confundiu uma vez: o
  usuario rodou o `--importar` sem a resposta escrita ("Nao achei
  data\resposta_ia.json"). Sao 7 pedidos para 20 questoes, porque cada pedido
  gera 3 variacoes de uma questao real;
- **o GitHub Actions esta vermelho desde `9ca6c04`.** A coleta diaria so rodou
  ate 26/09 (ultimo verde: run 36245200577, em `52a38aa`). Causa, medida
  rodando a suite no Linux e depois com o relogio simulado em outras datas:
  tres testes dependem do Windows ou da data de hoje. Dois ja falham (o do
  `pythonw.exe` e o do cronometro, que assumia 28/09 como futuro); o terceiro, o
  de `test_avisos.py`, tem data fixa de 17/09 e quebra por volta de 17/10, ao
  sair da janela de 30 dias de novidade. Com as tres correcoes a suite passou
  inteira (1.840) com o relogio em 20/10/2026, 10/11/2026 e 15/03/2027. A
  correcao **nao foi aplicada**; esta em pendencias;
- o primeiro dia mostrou que o conteudo da faixa de Direito nao reflete o que a
  FEPESE cobra: foi montado pelo edital de 2019. Detalhe e os numeros em
  pendencias e em decisoes.

## Etapa 1A do pedido de evolucao: os testes que quebravam o Actions (01/10)

- primeiro commit da Etapa 1: as 14 decisoes da Etapa 0 (o plano, no
  [roteiro](roteiro.md)) entraram no `decisoes.md`, com nota de revisao nas
  decisoes que elas substituem (selos, minimos de amostra, E2 e E4); o "Estado
  atual" do `CLAUDE.md` passou de "40 geradas, todas `do_zero`" para as 50 que
  o arquivo tem (30 `do_zero`, 20 `variacao`);
- as tres correcoes da pendencia A1, so nos testes: o da tarefa da web compara
  com `automacao.python_sem_janela()`; o do cronometro para o relogio em 27/09;
  o `_concurso` do `test_avisos.py` publica em `agora() - 1 dia`;
- antes da correcao a suite ja falhava tambem no Windows (o teste do
  cronometro: 28/09 deixou de ser futuro). Depois: 1.840 passando no PC e com
  o relogio simulado em 20/10/2026, 10/11/2026 e 15/03/2027 (`time-machine`
  instalado fora do repositorio, num plugin do pytest de uso unico). O
  `test_avisos.py` antigo, com o relogio em 20/10, da as 18 falhas previstas;
- o workflow so roda pelo agendamento ou pelo "Run workflow"; o verde no
  GitHub fica para conferir (pendencia A1).

## Etapa 1B do pedido de evolucao: texto de maquina e Previsao (01/10)

- **A2:** a linha do tempo (home, Analises, Acompanhando) mostrava
  "Situacao: inscricoes_abertas -> encerrado" e o tipo cru ("inscricoes
  encerradas"). Agora `eventos.para_tela` traduz na exibicao: uma frase por
  transicao, "voltou de ... para ..." quando a situacao anda para tras, o
  "Entrou no radar ... (situacao: edital publicado)", e prazo e retificacao
  com acento. O banco e o `eventos.json` nao mudaram;
- acentos no texto que chega a tela web: Calendario ("Ultimo dia de
  inscricao", "Salario", "O botao"), os erros do diario, os recados de
  Gerar questoes, a origem da rodada no simulado e na questao, os conselhos
  do Macetes, "Respondi so" do Onde estudar e o recado de cargo sem prova
  parecida. A busca por "Ultimo dia" da pendencia nao tinha achado nada porque
  o texto estava no `servico/__init__.py`, com o resto da frase numa f-string;
- **A3:** a Previsao mostrava "Previsto para 2025" em 2026 e "ha 0 ano(s), so
  em 2030". Agora: "Atrasado: era esperado em 2025" no topo da janela, "O
  ultimo foi este ano / ha 1 ano / ha N anos", "o proximo so em", "um a cada
  N anos". A conta nao mudou. O ano de hoje passou a sair de `_este_ano()`,
  que o teste troca para fingir a data;
- conferido com o `radar web` de verdade: Previsao e Calendario com o banco
  real; home, Analises e Acompanhando numa copia do banco com um evento a
  mais, porque o banco real nao tem evento em concurso-alvo nem favorito (a
  copia foi apagada depois).

## Etapa 1C do pedido de evolucao: a fonte unica das metricas (01/10)

- `servico/metricas.py` passou a ser o unico lugar que conta questao, acerto e
  erro: o `Numeros` com os quatro estados (acerto, erro, sem acerto anotado,
  treino de IA), a lista de lancamentos de um periodo e a soma por recorte;
  mais o acumulado pela ultima resposta, as rodadas e a evolucao, que sairam
  do `simulado.py` (os nomes continuam la, reexportados);
- quatro commits, como o roteiro pedia: o modulo e os testes do 28/09; Hoje e
  `radar hoje`; Semanas e Minhas materias; Meu foco, Onde estudar, home e
  relatorio;
- com o banco real: 28/09 fecha em "31 = 13 + 8 + 10 de treino de IA"; 29/09
  em "37 = 4 + 18 + 15 sem acerto anotado" (a faixa de aprendizagem com
  consulta e sem acerto); a semana 1, em 68 = 31 + 37;
- duas divergencias apareceram e foram consertadas pela lista unica: o dia de
  Plano B sumia de Semanas e de Minhas materias, e o treino de IA contava no
  volume da semana e nao no da materia;
- o registro do dia deixou de gravar copia do total; o `radar hoje --feitas`
  virou estudo extra, com `--minutos` obrigatorio (decidido com voce antes de
  implementar: o roteiro nao previa que o extra exige minutos).

## Etapa 1D do pedido de evolucao: a conferencia dos dias gravados (01/10)

- `radar conferir-dias` (`servico/conferencia.py`) compara, dia a dia do
  ciclo, o que esta gravado com a regra do `metricas`, e so le; com
  `--aplicar`, faz copia de seguranca e corrige o aprovado;
- no banco real: as copias do registro batiam (31/13 e 37/4); nenhum check
  orfao, nenhuma resposta a questao anulada, nenhum acerto maior que as
  questoes; 30/09 e 01/10 sem nada gravado. O que nao batia: o **Bonus
  marcado com 0 questoes em 28/09 e em 29/09** (voce nao fez), e os **JSON
  do diario vazios** - os dois dias so existiam no `radar.db`, porque o
  `sincronizar` nao rodou desde 28/09;
- aplicado com o seu "pode": os dois checks do Bonus sairam e o diario foi
  exportado. 28/09 e 29/09 passaram de 3h50 para 3h25; as questoes nao
  mudaram (31 e 37). Copia de antes em `data/copias/conferencia-2026-10-01-143927`;
- a tela passou a recusar faixa de questoes com 0 questoes.

## Etapa 6A do pedido de evolucao: questoes de manha e o Anki desativado (01/10)

- a proposta foi apresentada com os numeros do arquivo real e aprovada antes
  de mexer: o "Comportamento atual" do roteiro tinha o Anki em 30 min e o dia
  em 4h25, e o arquivo tinha 15 min e dias de 4h10 a 5h10;
- `config/cronograma.yml` reescrito de 02/10 em diante por um script de uma
  vez so, fora do repositorio, com o resumo dia a dia (26 dias uteis com a
  manha nova, 6 sabados com o item do Anki trocado). O trecho do arquivo
  antes de 02/10 ficou com o texto identico;
- a chave `anki` e a `consulta` por faixa no `cronograma.py`; a faixa do Anki
  desligada fica na lista, sem duracao, e `Dia.faixas()` passou a devolver so
  as que valem;
- religar foi testado no arquivo real: com `anki: ativado` o Anki volta as
  22:00-22:15, o Bonus a 22:15 e o chip do baralho reaparece;
- tres testes que fixavam numeros do arquivo real mudaram junto: o total do
  ciclo (1690 -> 2054 = + 26 x 14), o dia 28/10 (60 -> 74) e o botao "Anotar
  erro", que agora aparece na fixacao da manha (e continua fora da teoria).

## Etapa 2 do pedido de evolucao: arvore de conteudos, evidencia e migracao (01/10)

- plano conferido contra o codigo: valido. Duas decisoes suas antes de
  implementar: as 20 geradas de Penal (tema fora do programa de 2019) ficam
  so em "Direito Penal"; a copia da migracao vai para `data/copias/`;
- novos: `migracoes.py`, `conteudos.py`, `servico/evidencia.py`,
  `servico/conteudos.py`, `servico/classificacoes.py`,
  `config/taxonomia.yml`; tabelas `conteudos`, `classificacoes` e
  `versao_do_banco`; colunas `questoes.evidencia` e `conteudo` nas geradas, no
  caderno de erros e no estudo extra; comandos `radar migrar` e `radar
  conteudos`;
- ensaio numa copia do banco e dos JSON no scratchpad, e so depois o banco
  real: versao 0 -> 1, nenhuma linha perdida (8.433 questoes, 2.848
  concursos, 80 respostas...), 98 nos, evidencia 170 / 7.356 / 907;
- o caderno de erros e o estudo extra ganharam o JSON no disco agora: os 2
  erros so existiam no radar.db (o `sincronizar` nao rodou desde 28/09);
- tres arquivos de teste mudaram com a regra unica: o `test_treino_do_alvo` e
  dois do `test_foco` montavam questao do alvo sem concurso (sem estado
  provado, a prova nao e do alvo), e o `test_sincronizar` ganhou os dois JSON
  novos.

## Etapa 3A do pedido de evolucao: classificacao do alvo, incidencia e padroes (01/10)

- antes de implementar, tres decisoes suas: classificar as 170 agora e voce
  conferir depois (a 3A fica 🟡); Meu foco e Onde estudar por no so na Etapa
  4; materia fora do edital ganha assunto proposto;
- auditoria ampliada e `docs/auditoria.md` regerado: 25 questoes do alvo com
  suspeita de extracao (o titulo da materia seguinte grudado na alternativa
  "e", a grade de respostas na 2019-q99...), nenhuma sem gabarito, e a
  classificacao por prova;
- o tipo de pedido "classificacao" no `manual.py`, o `radar classificar`, a
  importacao que recusa, a tela de conferencia; migracoes v2 (tipo de questao
  e pegadinha) e v3 (a chave);
- as 170 classificadas pelo Claude Code lendo enunciado, alternativas e
  gabarito: 146 completas, 9 parciais, 15 pendentes com motivo; 7 assuntos,
  121 subassuntos e 57 elementos novos na arvore, com procedencia;
- no meio, a primeira importacao mostrou 160 principais para 170 questoes:
  a impressao (so do enunciado) juntava questoes diferentes. A chave passou a
  ser a questao inteira (decidido com voce), a migracao v3 refez a tabela e a
  resposta foi importada de novo;
- `incidencia.py`, `radar incidencia` e Analises > Incidencia; os padroes por
  no com o minimo do `config/amostra.yml`;
- a pergunta dos arts. 1o a 12 do CP: 1 questao em 2019, 3 em 2013.

## Armadilhas desta rodada

- teste que usa data fixa ou o nome do executavel do Windows funciona no PC e
  quebra no Actions; o Actions e o unico lugar que roda em Linux e com a data
  de verdade, e um teste vermelho la quase sempre e isso;
- ao testar com relogio simulado, `test_404.py` falhou numa rodada em 28/09 e
  passa com o relogio real: foi artefato do simulador, nao bug do radar;
- copiei um arquivo de trabalho (`listagem_stats.json`) para a raiz do
  repositorio por engano e o removi antes do commit: arquivo de apoio fica fora
  da pasta do projeto;
- um token do Telegram foi colado numa conversa no inicio; foi revogado.
  Token, chat id e chave da API vivem so em variavel de ambiente ou em Secrets,
  nunca em arquivo versionado nem em conversa.

## Etapa 3B do pedido de evolucao: o acervo complementar FEPESE (01/10)

Passos 1, 3 e 5 dos 5 da 3B. O 2 (a sua aprovacao da lista) virou a regra do
edital de 2019, com autonomia dada por voce; o 4 (classificacao fina das
provas aceitas) nao foi feito e esta no `pendencias.md`.

O plano do roteiro nao valia: rodando as verificacoes da auditoria nas 183
provas complementares, so 2 passariam (161 so tem gabarito provisorio, e o
leitor de quadro do edital nao le edital de prefeitura). As decisoes que
destravaram estao no `decisoes.md`.

Entrou: `radar complementar [--aplicar]`, o modulo puro `complementar.py` (a
validacao minima, as duas colunas e as respostas da secao 5), o servico que
le o banco e o manifesto, `config/complementar.yml` (os termos de busca),
`docs/complementar.md` (gerado), o arquivo de status
`data/acervo_complementar.json` (122 provas aceitas de 183) e a coluna
"Complementar FEPESE" na incidencia, no terminal e na tela, sempre separada
da do alvo.

Achados do acervo real, nenhum deles corrigido aqui: **LEP, Sociologia
Aplicada, Legislacao Especial e Administracao Publica tem zero questao pelo
nome da materia** no complementar; 24 provas tem o mesmo sha256 em dois
enderecos; 31 tem a numeracao furada.

## Etapa 3B, passo 4: as 80 do Socioeducativo classificadas (02/10)

`radar classificar` ganhou `--evidencia complementar` e `--materia` repetivel.
As 80 questoes de Direito, Direitos Humanos e Legislacao Estadual do
Socioeducativo 2013 e 2016 - as unicas do complementar nas materias que mais
importam, e as unicas com gabarito definitivo - foram classificadas pelo
Claude Code: 62 classificadas, 18 pendentes com motivo.

A classificacao achou um defeito que a auditoria nao pegava: **8 questoes
estao no bloco de materia errado** nos cadernos do Socioeducativo (Processo
Penal dentro de "Legislacao Estadual" e vice-versa). Nada foi corrigido; as
oito ficaram pendentes com o motivo, e a pendencia foi registrada.

A incidencia agora mostra o complementar por NO, e nao so por materia: em
Direitos Humanos, "Policia Penal SC: 24 questoes · 2 provas · Acervo
complementar FEPESE: 18 questoes · 2 provas". Os numeros do alvo nao mudaram.

## Etapa 3B, lotes 2 e 3 do complementar (02/10)

**Lote 2, blocos genericos.** Entrou o pedido `--genericos`, em que a materia
tambem e resposta. Dos 3.420 em bloco generico nas provas aceitas, 125 tinham
indicio de materia minha depois de corrigir a busca por termo (palavra
inteira, nao pedaco: "dolo" casava em "dolorosa"). Das 125, **44
classificadas** e 81 sem linha - conteudo do cargo daquele concurso
(pedagogia, saude, licitacao, legislacao municipal), que era o esperado.
Direito Constitucional foi de 20 para 34 questoes distintas no complementar, e
Administracao Publica, de 0 para 21.

**Lote 3, Portugues e Raciocinio Logico pelo catalogo.** `radar classificar
--catalogo` propoe o assunto pelo catalogo de palavras-chave do `macetes.py`,
com o mapa para o edital no `config/complementar.yml`: **92 propostas em
Portugues e 16 em Raciocinio Logico**, todas marcadas como automaticas e para
conferir por amostra. O que nao casa, casa dois assuntos ou nao tem par no
edital fica sem linha.

**Achado que mudou a conta:** as 993 ocorrencias de Portugues no complementar
sao **184 questoes distintas** - a FEPESE repete o mesmo caderno em dezenas de
cargos. A linha complementar passou a contar distintas, com as ocorrencias
entre parenteses. O alvo nao mudou.

## O Actions voltou ao verde (02/10)

A coleta diaria rodou sozinha e commitou `coleta: 2026-10-02` (as 15:13 UTC,
pelo `radar-bot`), a primeira desde 26/09. O `coleta.yml` roda `pytest -q`
antes de coletar, e um passo que falha aborta o job: o commit e a prova de que
a suite passou no Linux. A pendencia A1 saiu do `pendencias.md`, e com ela o
bloco "Quebrado agora" ficou vazio.

## Etapa 4 — amostra, desempenho por conteudo e controle de estudo (02/10)

As tres reguas para a mesma duvida ("ja da para acreditar neste numero?")
viraram uma, e o desempenho desceu da materia para o conteudo.

**Os minimos.** O 5 e o 3 do `onde_estudar.py` e o 20 do `servico/materias.py`
sairam do codigo: agora vem do `config/amostra.yml`, secao `desempenho`, com os
valores da decisao 6 (20 na materia, 10 no assunto, 6 no subassunto e no
elemento) e os cinco estados da §16 do novo.md. O modulo novo
`src/radar/amostra.py` e puro: le o YAML e devolve o estado de um no. O 3 do
caderno de erros ficou onde estava, de proposito: ele mede a fatia de cada
motivo de erro, nao acerto.

**Consequencia medida, e mostrada antes:** com 12 respostas reais no banco,
quase toda linha do recorte "medido no radar" passou a dizer "Amostra
insuficiente". E o comportamento pedido - o numero aparece e nao ordena nem
projeta nada -, e quatro testes que contavam com os minimos antigos (5 na
materia, 3 ou 8 no assunto) foram atualizados para os novos.

**O desempenho por no.** `servico/desempenho_por_conteudo.py` junta as duas
origens do meu treino: o radar (cada questao real, pela ultima resposta, ligada
ao no pela classificacao da 3A, reconhecida pela CHAVE) e o anotado (as faixas e
os extras ligados a um no). As duas nunca sao somadas na tela - a linha escreve
"radar X% em N · anotado Y% em M" -, e sao somadas para o estado, que e o meu
desempenho naquele conteudo. A questao conta no no dela e em todos os de cima.
So o sem consulta conta para o estado; IA nunca conta.

**O seletor.** O `conteudo` passou a viajar na fonte unica (`metricas.Lancamento`
e `cronograma.FaixaFeita` ganharam o campo; o check do dia ja gravava e a
leitura descartava). Os tres formularios - faixa, estudo extra, caderno de erros
- ganharam um `<select>` com o caminho do no, recuado por nivel, sem JavaScript.
Na faixa ele nao sai do ramo dela.

**O controle de estudo.** `servico/estudo.py` responde o que o ANKI fazia:
estudado, praticado, nao estudado (com a definicao da decisao 20), a data do
primeiro e do ultimo estudo, a evolucao semana a semana com as contas da tela
Semanas, os tres gatilhos de revisao e as duas listas de refazer. Nada gravado
em tabela: tudo sai do historico.

**As telas.** Nasceu "Analises → Meu desempenho" e o comando
`radar desempenho [--revisar] [--desde-o-inicio] [--materia]`. O Meu foco, a
home e o Onde estudar passaram a somar o anotado ao radar (decisao 7, que revisa
a E2), e as frases das telas trocaram "medido no radar" pela divisao.

## Os blocos da aba Hoje dobram (B.11, 02/10)

Pedido durante a Etapa 4 e feito em conversa propria, depois dela.

Cada bloco do dia - "Manha", "Noite", "Depois das 22h" e o do Plano B - virou
um `<details>` cujo `<summary>` e o proprio cabecalho do cartao, com um sinal
▾ / ▴ no canto direito. A dobra em si nao usa JavaScript, como o Mapa do ano da
lateral ja fazia.

**Duas mudancas suas, no mesmo dia, depois da primeira versao:**

1. **so o sinal do canto dobra**, e nao o cabecalho inteiro: um clique no titulo
   ou nos horarios nao pode recolher o bloco sem querer. Feito com
   `pointer-events: none` no `<summary>` e `auto` so no sinal - o teclado nao
   passa por ali, entao Tab + Enter continuam dobrando. O sinal ganhou area de
   clique de 1,75rem e um `title`, porque o alvo ficou pequeno;
2. **a dobra passou a ser lembrada** entre recarregamentos, e isso criou o
   **segundo JavaScript do radar**: `static/dobra.js`. Eu avisei que isso muda a
   regra do "cronometro e o unico JS"; voce pediu mesmo assim. O limite e o
   mesmo do cronometro: o padrao vem do servidor, a dobra funciona sem o
   arquivo, e todo acesso ao `localStorage` esta em try/catch. A chave e o
   BLOCO, nao o dia, e o bloco da ancora (onde a tela volta depois de eu anotar
   uma faixa) nunca e recolhido.

"Depois das 22h" nasce **fechado**, e fechado mostra no cabecalho que o ANKI
esta temporariamente desativado; aberto, essa frase sai e fica a da faixa
minimizada da 6A. A frase segue a faixa desligada, e nao o nome do bloco: o
teste religa o Anki num arquivo copiado e confere que ela desaparece.

Lembrar a dobra entre recarregamentos ficou de fora: precisaria de
`localStorage`, e nao foi pedido.
