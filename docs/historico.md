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

Na primeira versao, lembrar a dobra entre recarregamentos tinha ficado de
fora (precisaria de `localStorage`, e nao tinha sido pedido); a segunda
mudanca acima a trouxe, no `static/dobra.js`.

## Etapa 5 — geracao de questoes com escopo fechado (02/10)

**O filtro.** `radar/conteudos.resolver_escopo` (puro) fecha o caminho
materia > assunto > subassunto > elemento, conferindo cada nivel DENTRO do de
cima. Nome que a arvore nao tem para o comando, com ate 5 sugestoes do
`difflib`, e nao gera nada. O `Escopo.dentro()` e o que a importacao usa depois.

**Os tres modos.** `treino` (escopo fechado), `revisao` (so os nos estudados,
pela definicao da Etapa 4) e `simulado` (amplo, pelo edital e pelo peso). Sem
`--modo`: com assunto e treino, so com materia e simulado, e a saida escreve
qual foi.

**As questoes de base passaram a sair da CLASSIFICACAO**, e nao da coluna
`materia`: `geradas.reais_do_escopo` pega as reais cujo no esta dentro do
escopo, **alvo antes do complementar** (§9), e prova complementar so entra se
estiver aceita no acervo. Faltou real para o tanto pedido? O resto sai da fonte
oficial do `config/leis.yml` ou do item do edital, DENTRO do mesmo no, marcado
"sem questao real de referencia".

**A importacao recusa quatro coisas**, contando na saida: conteudo declarado
fora do escopo, artigo que nao e nenhum dos dispositivos pedidos, vinculo com
questao real que nao estava no pedido, e `do_zero` sem a marca. A garantia e a
validacao do que a IA declara - a leitura do texto continua minha.

**Quatro colunas novas** em `questoes_geradas` (`modo_do_pedido`, `escopo`,
`base`, `evidencia_da_base`), na migracao v4 com copia antes; o dispositivo
reusa o `artigo`, que ja era isso. Nas 50 antigas os campos ficam nulos.

**Achado no caminho, e consertado:** o `data/questoes_geradas.json` estava `[]`
desde o commit da Etapa 2, enquanto o banco tinha as 50. O arquivo e o
registro, e o banco se reconstroi dele: refazer o banco teria perdido as 50.
Exportado do banco real (50 de volta) e com teste para nao repetir.

## Etapa 6B — a ficha de estudo e a prioridade (02/10)

**A estrutura.** `radar/fichas.py` (puro) monta a `FichaDeEstudo` com os
campos da §11, cada um com a origem (📌 plano, 🟢 oficial, 🔵 acervo, 🟡
automatico, 🟣 IA). `radar/prioridade.py` (puro) faz a conta do
`config/prioridade.yml`. `servico/fichas.py` junta o que o banco ja conta - a
incidencia do alvo e do complementar, o desempenho por conteudo, a fila de
revisao, as geradas, o cronograma - e le e grava o `data/fichas.json`. O tema
e reconhecido pelo titulo da faixa sem o prefixo, e a mesma ficha aparece na
teoria, na fixacao, na aprendizagem, no R+7, no R+30 e no Plano B.

**Onde aparece.** O botao 📋 Ficha de estudo nas faixas da tela Hoje, a
sub-aba Hoje > Fichas (os temas de hoje em diante, na ordem do calendario, com
a prioridade de cada um na linha), a
pagina de cada ficha com o botao "Conferi esta ficha", e o terminal: `radar
fichas` (lista, `--tema`, `--pedido`, `--importar`, `--conferir`) e o `radar
hoje`, que marca a faixa com 📋 e lista as fichas do dia.

**O texto das 61 fichas** foi escrito pelo Claude Code em tres sessoes, em
partes de duas fichas por arquivo (`fichas_*.json`, conferidas uma a uma
pelo `conferir_escrita` antes de juntar), e importado em 02/10 pelo
`radar fichas --importar`. Para a LEP, as Regras de Mandela e a redacao
oficial, o texto foi conferido no documento oficial: a LEP compilada pela
Camara (ate a Lei 15.410, de 20/05/2026), a traducao do CNJ das Regras de
Mandela e o Manual de Redacao da Presidencia (3ª edicao). A LEP tinha mudado
muito desde as provas - o juiz, e nao mais o diretor, suspende os direitos do
art. 41; o art. 112 voltou a regra geral de 1/6 e levou os hediondos a 70% a
85%; a saida temporaria ficou so para estudo e o art. 124 foi revogado; o
art. 9º-A passou a valer para toda reclusao em regime inicial fechado. O
detalhe do cronograma de 09/10, 28/10 e 30/10 foi corrigido junto, e a ficha
dos arts. 1º a 9º-A, escrita antes, tambem.

**Achado no caminho, e consertado de vez:** o JSON das geradas tinha voltado a
`[]` depois do conserto da Etapa 5. A causa era o
`test_tabela_nova_entra_em_banco_antigo`: ele apontava o banco para o tmp, mas
nao os dados, e a migracao automatica do banco sem versao exportava o banco
vazio por cima do `data/questoes_geradas.json` (e copiava o banco de teste
para `data/copias/`). Teste consertado, as 50 exportadas de novo do banco
real. E a data da procedencia passou a ser a de Florianopolis: a importacao
das 22h tinha saido "em 03/10/2026". Por ultimo, a ficha sem no deixou de
dizer "nao apareceu nas provas analisadas" no "por que agora": sem no, o
acervo nem foi contado para ela.

**O que ficou:** a minha conferencia das 61 fichas e o Ciclo 2, que depende do
simulado de fechamento de 07/11 e da minha aprovacao antes de 09/11.

## Etapa 7A — os selos do novo.md, a frase padrao e a questao de IA (02-03/10)

**O pedido:** as quatro origens da secao 20 do novo.md com as cores dele, a
origem registrada no dado e nao so pintada, a frase da regra 4 identica em
todo lugar, e questao de IA nunca parecendo oficial. Antes de comecar, cinco
ajustes ao roteiro foram aprovados: dividir o antigo "calculado" pela natureza
do dado (acervo ou automatico), unificar a frase que ja existia duas vezes,
a ficha da 6B usar o mesmo componente, dar cor propria a tudo que reusava a
cor de selo (e nao so as metas) e gravar a origem nos dados que a tela mostra
com selo, e nao em todo numero de todo servico.

**Como foi feito**, em passos pequenos, cada um com os testes dele e um
commit:
1. o `src/radar/origem.py` (as origens, o `SELOS` e as duas frases), os
   tokens do `design.css` (cores com nome, `--selo-*`, `--meta-*`) e o
   `_componentes.html` lendo o `SELOS`; as cores que nao eram selo (meta do
   dia, bom e ruim, o que esta rodando) passaram a usar a cor pelo nome;
2. a origem nos tipos que os servicos entregam a tela (atributo `origem`,
   `origens` quando o objeto junta partes, ou propriedade quando depende do
   dado), com o `tests/test_origem.py`;
3. a frase padrao: a constante unica, o "Amostra insuficiente" no lugar do
   "amostra pequena" e a frase do acervo onde a falta era de evidencia;
4. as telas, uma por commit: Meu foco, home, Hoje, Semanas, Caderno de erros,
   Macetes, a rodada (questao e relatorio), Simulado, Gerar questoes,
   Concursos, Minhas materias, Previsao e Mais, e a Ficha - cada uma com um
   teste que troca a origem NO DADO e confere que o selo troca junto;
5. a varredura das telas (`tests/test_varredura_das_telas.py`), e os docs.

**A conferencia no navegador** foi por captura do Edge sem janela, nos dois
temas, com o banco real: Hoje, Semanas, home, Meu foco, Minhas materias,
Simulado, relatorio, Gerar questoes, Macetes, Mais, ficha e Previsao. As metas
do dia ficaram com as cores de antes; os selos, com as do novo.md.

**Achados no caminho.** A varredura achou uma previsao que ninguem tinha
visto: "Já caíram várias vezes e devem cair de novo", no cartao das questoes
repetidas dos Macetes - trocada. A captura achou que o `?tema=` da URL (o que
forca claro ou escuro) colide com o filtro "Materia ou tema" dos Macetes -
anotado em pendencias, porque o conserto e renomear um parametro que pode
estar em link salvo. E a tela Mais mostrava o backup de 02/10 falho: as 23h30
o `radar sincronizar` nao conseguiu o pull porque havia mudanca nao commitada
no disco (era o trabalho desta etapa em andamento).

## Etapa 7B — as 6 telas no design system (03/10)

**O pedido:** acabar com as duas caras do site. Seis telas ainda tinham a
propria paleta (`:root` com `--fundo`, `--cartao`, `--azul`...) e o `body` sem
a classe do design system: a 404, o Calendario, a Previsao, o Acompanhando, o
Analises (`foco.html`) e o Concursos (`index.html`).

**Antes de comecar, duas decisoes minhas** (59 e 60): o roxo das telas antigas
(Estadual SC, "a confirmar", a fase "autorizado", o aviso da secretaria) nao
podia ficar, porque desde a 7A o roxo e a cor da IA - virou azul e cinza
tracejado; e a barra do topo, que ainda lia os nomes antigos pela "ponte" do
`design.css`, entrou no ultimo commit, junto com a saida da ponte.

**Como foi feito:** uma tela por commit, da menor para a maior - 404,
Calendario, Previsao, Acompanhando, Analises e Concursos. Em cada uma: `body
class="ds"`, `ds-pagina`, `ds-cabeca`, `ds-cartao`, `ds-tabela`, `ds-botao`,
e o `<style>` da tela reescrito nos tokens, sem a paleta propria. As classes
que testes e links leem ficaram. Cada tela foi aberta com o banco real e
capturada pelo Edge sem janela nos dois temas antes do commit; na de noticias
do Concursos, a captura mostrou os botoes esticados ao lado do campo de busca,
e o alinhamento foi acertado. Por ultimo, a barra do topo passou para os
tokens, a ponte saiu do `design.css` e o README ganhou o paragrafo das telas.

`tests/test_telas_no_design_system.py` nasceu com a primeira tela e cresceu a
cada uma: cada tela abre com o design system e sem a paleta antiga, todo
template de pagina marca `class="ds"`, e ninguem usa os nomes velhos.

## Etapa 8 — a auditoria final integrada (03/10)

**O pedido:** conferir o sistema de ponta a ponta contra a §23 do novo.md -
cada etapa tinha sido testada sozinha, e ninguem tinha conferido o conjunto.

**Antes de comecar**, a checagem do plano achou dois pontos e eles viraram
decisao (61 e 62): os dois exemplos de geracao da §23 nao existem na arvore
real, e o backup das 23h30 falhou em todas as execucoes registradas. Ficou
combinado provar o escopo fechado numa arvore de fixture e registrar a falta
dos nos como pendencia, e consertar o backup numa etapa propria.

**Como foi feito.** Primeiro o `tests/test_aceite.py`: as 12 perguntas da
ficha, os dois pedidos de geracao (com o vizinho de cada no recusado) e os 6
itens finais, montados com os construtores que as etapas ja usavam. Depois o
uso real, item por item, com o banco de verdade: a ficha do Art. 5º no
terminal, os dois pedidos (recusados) e os nos mais proximos (escopo fechado),
os numeros de 28 e 29/09 e da semana 1 em quatro lugares, a incidencia do alvo
com 0 e com 122 provas complementares numa copia do `data/`, as tabelas contra
a copia de antes da Etapa 2, o ANKI religado numa copia da `config/`, a
varredura da 7A nas telas reais e as rodadas de IA. Tudo foi para o
`docs/auditoria_final.md`.

**O que a auditoria achou:** 17 dos 19 itens da §23 atendem com o dado real.
Os dois que nao atendem por inteiro viraram pendencia - os nos dos exemplos de
geracao e a media "por prova" do grafico de pizza dos Macetes, sem o numero de
provas. Fora da §23: o backup nunca funcionou nos logs (desde 27/09), o
caderno de erros e a Semanas funcionam com o dado real, e o Actions estava
verde ate 02/10 - o de hoje, o primeiro com o codigo novo, fica para conferir.

## Correcoes depois da auditoria (03/10)

**O pedido:** os cinco pontos que a varredura dos docs achou depois da Etapa
8, nesta ordem e um de cada vez, com um commit so no fim.

**1. O "Onde estudar primeiro" somava o alvo e o complementar.** A conta das
questoes esperadas usava as marcas do cargo e as do "reforco" no mesmo
numerador e no mesmo denominador - a regra inviolavel 1 do novo.md nao deixa.
E o reforco era qualquer caderno da FEPESE, sem olhar o levantamento da 3B.
Agora as questoes esperadas e os pontos sao so das provas do cargo; o
complementar, so das provas aceitas, pesa so na ordem, com o 0,25 do
`config/prioridade.yml` - a mesma conta da prioridade das fichas -, e a tela
mostra as duas fatias, cada uma sobre a sua base (decisao 63).

**2. O backup das 23h30.** Falhava todas as noites desde 27/09 com "cannot
pull with rebase: You have unstaged changes": o rebase recusa a pasta suja, e
quase sempre havia uma etapa pela metade nela. Atras dele, o `git add` recebia
tres arquivos que nao existem e, com isso, nao adicionava nenhum. O pull virou
`fetch` + `merge --ff-only` (o rebase so com a pasta limpa, e desfeito se der
conflito), e o `git add` e o commit levam so os arquivos do radar que existem
(decisao 64). Os testes novos usam o git de verdade, em repositorios no
`tmp_path`; e o comando rodou numa copia do repositorio, com o banco real.

**3. A lista de leis alteradas.** Nunca tinha sido gravada: a decisao antiga
esperava a conferencia do usuario antes. Foi feita questao a questao - as 115
de Direito das duas provas, em cinco frentes paralelas, cada dispositivo no
texto compilado da Camara ou da ALESC, com as datas das provas tiradas do
acervo (10/11/2013 e 01/12/2019) - e deu 17 questoes em 15 itens. As leis de
SC foram as que mais mudaram: a carreira cobrada nas duas provas (LC
472/2009 e LC 675/2016) foi revogada, e o cargo virou Policial Penal (EC
estadual 80/2020, LC 774/2021). A lista entrou com procedencia e por
conferir, e o aviso sai com o 🟣 ate a conferencia (decisao 65); a evidencia
esta em `docs/leis_alteradas.md`.

**4. O erro da Etapa 8 nos docs.** A escolha da Etapa 5 sobre os dois exemplos
de geracao da §23 (rodar os equivalentes reais e mostrar a recusa dos literais)
nunca tinha ido para o `decisoes.md`; a auditoria da Etapa 8 nao a achou e a
reabriu como pendencia, com o item 13 da §23 em ⚠️. O registro que faltava e
a decisao 66; o item 13 passou a ✅ e a §23 ficou com 18 de 19 itens.

**5. A limpeza geral dos docs.** Os dois relatorios gerados foram regerados (o
do complementar dizia "nada entrou em estatistica" com 122 provas na
incidencia, e o texto passou a depender de o acervo ter sido aplicado); o
README, a especificacao e o CLAUDE.md perderam o que tinha ficado velho - a
navegacao de antes do redesign, o estado de 5.928 questoes, o minimo de 5
respostas, o tempo dos testes, o cartao "De olho" na home -; e as pendencias
ganharam a secao F, com os 10 achados da varredura que nenhuma etapa tinha
registrado. Commit e push uma vez so, no fim dos cinco itens, a pedido.

## O sabado generico e o ciclo especifico, subetapa 2A (03/10)

**O pedido:** o sabado de 03/10 mostrava "Diagnostico de Raciocinio Logico" e
"Diagnostico de Portugues" com o detalhe "Radar > Simulado > materia X > 20
questoes", sem dizer de que assunto; e o ciclo inteiro, estava assim tambem?
Junto, o "item 4" das pendencias.

**O que a leitura achou:** 121 das 182 faixas de questoes de 03/10 a 07/11 nao
dizem o assunto e o subassunto exatos; o sabado de 03/10 e o unico so de
medida; o caminho do diagnostico sorteava de qualquer banca (a IESES e provas
recusadas na 3B entravam); e a arvore so tem amostra no alvo, em Portugues,
para Interpretacao - Raciocinio Logico so caiu em 2019.

**A 2A:** uma regra de composicao (decisao 67) num servico novo, o
`servico/composicao.py`, que usa o que ja existia - a incidencia por no da
arvore, o `compilado.distribuir`, o minimo do `config/amostra.yml` e o peso do
complementar do `config/prioridade.yml`. A tela Hoje mostra a composicao nas
faixas que medem e cria a rodada com ela; a rodada grava a composicao e nao e
recriada. O `cronograma.yml` mudou so no `detalhe` das tres faixas que medem e
na lista de materias do 07/11 (chave nova, `materias_da_rodada`); nenhum titulo
mudou, e os dias antes de 03/10 tem teste. E o modo simulado da geracao passou
a dividir pelo peso do edital (decisao 68).

## O sabado, subetapa 2B (03/10)

**O que estava generico:** os simulados de sabado no Qconcursos tinham os
numeros escritos a mao no YAML; a revisao semanal mandava "refazer TODAS as
questoes que voce errou" e "reler os artigos-chave da semana" sem dizer
quais; o R+7 de 10/10 mandava ao "So meus erros" (todos os erros de todas as
rodadas); e a correcao de 07/11 pedia para comparar com o diagnostico sem
mostrar numero.

**A 2B:** o simulado do Qconcursos saiu pela regra da 67, entre os temas ja
estudados (decisao 69); o sabado ganhou um servico proprio, o
`servico/sabado.py` (decisao 70), que diz a semana com o que ja esta gravado -
o plano, o caderno de erros e as rodadas. O R+7 cria a rodada so com os erros
dos diagnosticos, no numero do plano; a correcao de 07/11 compara o
diagnostico, o fechamento e o acumulado do ciclo, sem somar. O YAML mudou so
em detalhe e em chave nova (`materias_da_rodada` nos sabados, `compara_com`
no 07/11); nenhum titulo mudou.

O Actions de 03/10 passou: o commit `coleta: 2026-10-03` e a prova (o job roda
a suite antes de coletar).

## O assunto na faixa, subetapa 2C (03/10)

**O que estava generico:** a faixa dizia o tema e so; o assunto e o
subassunto ficavam dentro da ficha, e o bonus e a interpretacao cronometrada
nao tinham nem ficha nem no.

**A 2C:** cada faixa diz, nela mesma, o assunto, o subassunto - ou que a
arvore nao tem subassunto para o tema - e o elemento (decisao 71). A fonte e a
ficha (🟣) ou, sem ficha, os nos que o plano da para a faixa (📌, a chave nova
`nos`). Nenhum no foi criado, pela escolha 5B. O bonus e a interpretacao
cronometrada ganharam `nos` de 05/10 em diante. Para o plano carregar nos
testes, o leitor do programa do edital passou a juntar "Tabelas-" e "verdade"
em qualquer texto, como ja fazia no PDF.

## O estoque de geradas, lote 1 (03/10)

**O pedido:** deixar no sistema, antes de precisar, questoes de treino geradas
para os conteudos das faixas ate 07/11, sem chave da API - o Claude Code
responde o `radar gerar --pedido` e o `radar gerar --importar` grava -, com
materia, assunto e subassunto.

**O plano** (somente leitura, numa copia do banco): 61 temas de treino, 1.925
questoes nas faixas, 211 reais livres nos 86 nos deles. So 33 temas tem no de
subassunto; o estoque ficou em 57 lotes e 725 questoes (decisao 73). As 50
geradas antigas tem so a materia no `conteudo` e nao contam para no nenhum.

**O lote 1:** o pedido mostrou um bug - a variacao herdava a materia
"Conhecimentos Especificos" da questao do complementar. Parei, e com a sua
escolha o conserto entrou antes (decisao 72, com teste). Depois: 19 de 19
gravadas (3 por variacao, 16 do zero pela fonte oficial), procedencia "Claude
Code, importado manualmente, em 03/10/2026"; banco e JSON de 50 para 69. O
passo a passo para os outros lotes esta em `docs/estoque_de_geradas.md`.

## O "Onde estudar" pela arvore, F1 (03/10)

**O que estava errado:** o "Onde estudar primeiro" tirava o assunto do
catalogo de palavras-chave e da coluna `assunto`, zerada em 25/09. As nove
materias de Direito apareciam sem nenhuma questao classificada, e os numeros
de Portugues nao batiam com a Incidencia.

**O F1:** o assunto e o no da arvore em que a questao foi classificada, com as
fatias da incidencia (cargo e complementar aceito, separados) e o acerto do
desempenho por conteudo, mostrado nos dois recortes (decisao 74). A revisao
espacada passou a usar o mesmo assunto. Resultado: 66 assuntos em todas as
materias, 12 questoes sem assunto (eram 108).

## O complementar que vale, F2 (03/10)

**O que estava errado:** o "costume de qualquer banca" dos Macetes contava a
FEPESE inteira num numero so - as provas do cargo, o complementar aceito e as
provas que a 3B recusou -, e o "Treinar" (com o compilado) completava com
qualquer prova da banca.

**O F2:** os dois passaram a usar so o complementar aceito (decisao 75). O
costume diz o que ficou de fora (170 do cargo, 2.341 de provas recusadas); o
treino completa com 1.593 questoes da banca, e nao mais 2.190.

## O estoque de geradas, lotes 2 a 56 (03/10)

**O pedido:** os 56 lotes que faltavam, agora, na ordem de uso, com um commit
por semana.

**Como foi:** cada lote pelo mesmo caminho do lote 1 (`radar gerar --pedido`,
a resposta escrita pelo Claude Code, `radar gerar --importar`), e o texto de lei
conferido na compilacao da Camara antes de escrever - a LEP, a CF, o CP e o CPP
mudaram em 2024-2026 (art. 41, art. 112 e art. 146-E da LEP; art. 310 do CPP).
666 questoes em 54 lotes, nenhuma recusada; 5 do lote 6 sairam como repetidas
(o mesmo comando em varias questoes) e foram repostas. O JSON foi de 69 para
735.

**O que ficou:** os lotes 50 e 57, das Regras de Mandela. A importacao exige
"art." ou "sumula" na fonte de Direitos Humanos, e a regra de Mandela se cita
como "regra N". Parei nesses dois e segui com os outros.

## As Regras de Mandela no estoque, decisao 76 (03/10)

**O que travava:** a importacao so aceitava, em Direitos Humanos, fonte com
"art." ou "sumula", e a regra de Mandela se cita como "regra 12.1". Os lotes 50
e 57 do estoque pararam ai, e a escolha foi sua.

**O conserto:** "regra" seguida de numero passou a valer como fonte (decisao
76), com teste; sem o numero, continua recusada. Depois, os dois lotes - 40
questoes escritas sobre o texto oficial da ONU, baixado do UNODC. O estoque
fechou nos 57 lotes e 725 questoes; o JSON, em 775.

## A base da gerada pela chave, e a materia sem acento, F3 (03/10)

**O que estava errado:** o selo da questao gerada achava a questao real de
base pela impressao do enunciado, e a FEPESE repete o comando em questoes de
alternativas diferentes - o selo podia apontar a errada; e o `--materia` do
`radar desempenho` e do `radar incidencia` nao achava a materia digitada sem
acento.

**O F3:** a variacao passou a guardar a chave da base (decisao 77), com o
passo 5 da migracao preenchendo as antigas onde nao ha duvida - 206 de 239; as
33 ambiguas ficaram sem base, e a tela diz isso em vez de "escrita do zero". O
filtro de materia passou a ignorar acento e caixa.

## Os padroes de cobranca do complementar, F4 (03/10)

**O que faltava:** a secao 13 pede padroes de cobranca com a amostra e a
origem; so o alvo tinha os seus, e o complementar aparecia so como contagem.

**O F4:** os mesmos padroes passaram a ser contados no complementar, so das
provas com gabarito definitivo e em questao distinta, ao lado dos do alvo e
nunca somados (decisao 78). Tipo de questao e pegadinha esperam a conferencia
da classificacao do complementar. Em Portugues, 45 questoes em 22 provas.

## A ultima revisao e a evolucao no Meu desempenho, F5 (03/10)

**O que faltava:** a secao 19 pede a data da ultima revisao de cada conteudo
e a evolucao por assunto. O servico tinha o campo da revisao desde a Etapa 4,
mas nunca o preenchia; e a evolucao semanal contava so a ultima resposta de
cada questao do radar, nao todas, como a tela Semanas.

**O F5:** revisao passou a ser so o que e revisao - faixa de revisao, extra de
revisao, rodada que revisa no radar -, e a evolucao conta toda resposta pela
conta do `metricas`, com a semana abaixo do minimo em cinza (decisao 79). A
tela ganhou a secao "Quando eu estudei e revisei cada conteudo". O achado do
caminho: quase nenhuma faixa do plano chega a arvore - nenhum R+7 tem a chave
`conteudo` -, e o que fazer com isso ficou nas pendencias, para voce decidir.

## O painel mais leve, F6 (04/10)

**O que estava lento:** a home levava ~4 s e Analises ~3 s. O perfil mostrou
a mesma conta feita varias vezes por pagina: o cronograma interpretado 6 vezes,
a chave das ~5 mil questoes do complementar refeita a cada abertura, as colunas
do banco conferidas ~40 vezes, e cada questao comparada com cada no da arvore.

**O F6:** o leitor em C do YAML, a impressao guardada em memoria, o esquema
conferido uma vez por conexao e a linha complementar montada direto (decisao
80). A home caiu para ~1,4 s e Analises para ~1 s, com as paginas iguais byte a
byte. No caminho, um achado antigo: os termos frequentes empatados trocam de
ordem a cada vez que o radar sobe - ficou nas pendencias.

## A faixa sem `conteudo` no que ela cobre, F7 (04/10)

**O que faltava:** so 6 faixas do plano tem a chave `conteudo`, e nenhum R+7.
A teoria, a lei seca e o R+7 contavam no dia e em conteudo nenhum, e o Meu
desempenho nao via o que eu estudava nas faixas.

**A F7 (a opcao (b), sua escolha):** a faixa sem `conteudo` conta no que cobre
- os `nos` do plano e a ficha depois de conferida - so para estudado,
praticado e as datas; o acerto fica fora (decisao 81). Hoje nada muda, porque
nenhuma ficha esta conferida; com as duas de 28 e 29/09, 9 nos de Penal e
Constitucional acenderiam. O achado: o R+7 feito nao tira o conteudo da fila,
porque o 1-7-30 so anda com acerto no radar - ficou para voce decidir.

## A revisao feita passa o 1-7-30 de etapa, F8 (04/10)

**O que estava errado:** o prazo da revisao so andava com acerto no radar.
O R+7 feito no Qconcursos marcava a data da revisao, mas o conteudo continuava
"prazo vencido" - e, com as fichas conferidas (F7), a fila so ia encher.

**A F8 (a opcao (b), aprovada por voce):** a faixa de revisao e o extra de
revisao, no vencimento ou depois, passam de etapa como o acerto no radar; a
revisao sem questao deixou de contar como estudo, que reiniciava o prazo
(decisao 82). Subiu no commit do lote de 04/10.

## Os termos empatados em ordem alfabetica, F9 (04/10)

O achado do F6: os termos frequentes empatados mudavam de ordem a cada vez que
o radar subia, porque entram na conta por um conjunto, e o Python sorteia a
ordem dele por processo. Agora o empate e alfabetico, sem olhar acento, e a
pagina sai igual em qualquer processo. Subiu no commit do lote de 04/10.

## O lote de 04/10: o resto da secao F, as conferencias e os abertos

Pedido: fechar a F8 e a F9, fazer o resto da secao F, depois as conferencias
e os abertos que listei, tudo com o que eu recomendo, e so no fim a suite, o
commit e o push.

**F10, as variacoes religadas:** as 30 do estoque de 03/10 sem a questao de
base acharam a base no historico da conversa, onde cada pedido tinha sido
impresso com as alternativas. Sobraram as 3 de 27/09, sem registro.

**F11, os minimos:** os tres que tinham ficado escritos no codigo - a evolucao
da home, a tendencia de letra no gabarito e o "base pequena" - foram para o
`config/amostra.yml`, com os mesmos valores (decisao 83).

**F12, as leis de fronteira:** os 9 casos em que a lei mudou depois da prova
num ponto que a questao nao cobra sairam do documento e foram para a ficha do
tema, onde vale saber deles (decisao 84). Na conferencia apareceram os arts.
41-A e 41-B da LEP, de 2026.

**F14 e F15:** o "estudado" passou a seguir a decisao 20 pelas constantes que
estavam sem uso, e a ancora do 1-7-30 de quem so praticou passou a ser a
primeira resposta de verdade, e nao a ultima de cada questao (decisao 85).

**F13, os conceitos associados:** a §14 pergunta "quais conceitos aparecem
associados", e nenhuma questao tinha associado. Um pedido novo, respondido
pelo Claude Code para as 155 questoes do alvo, deu 109 associacoes - a
Incidencia mostra os pares, e a contagem nao muda (decisao 86).

**As conferencias:** as 61 fichas foram lidas contra a fonte - a lei no texto
compilado da Camara, Mandela no texto da ONU, Portugues e Raciocinio pela
regra -, e 15 foram corrigidas; so uma tinha erro de conteudo (a regra 40 de
Mandela proibe dar ao preso FUNCAO disciplinar, e a ficha falava de castigo).
As 15 leis da lista foram reconferidas: nenhuma errada. A marca de conferida,
nas duas, continua sua.

**B.8, o complementar:** a tela de Conferencia ganhou o filtro do complementar
aceito e a amostra fixa do catalogo. A amostra reprovou o catalogo - ele casa
palavra no enunciado, e "lacunas do texto" virava Interpretacao -, e as 108
propostas foram classificadas de novo; a proposta do catalogo trocada deixou
de virar "conceito associado" (decisao 87).

**Os abertos:** o `?tema=` dos Macetes virou `?cor=` para a cor (decisao 88);
as geradas antigas ganharam materia e no, e 7 de LEP com gabarito errado
sairam do sorteio (decisao 89); a media "por prova" dos Macetes diz em
quantas provas.

**B.7, B.9 e B.10, o leitor do caderno:** o lixo que grudava no fim da ultima
alternativa (o titulo da secao seguinte, a grade de respostas, o rodape), a
metade de palavra apagada como cabecalho ("e cor-"), o "100." no enunciado, a
lista numerada da alternativa tomada pelo numero da questao seguinte e a
ordem das secoes trocada pelas duas colunas foram consertados no leitor; e o
download que gravava dois S07.pdf no mesmo lugar deixou 21 provas sem baixar,
com as do outro concurso no lugar. As 21 foram baixadas, as copias sairam (as
5 respostas que caiam nelas foram para a questao identica), e o acervo
inteiro foi relido duas vezes - com a classificacao indo junto para a chave
nova, so quando o texto e o da mesma questao. A auditoria do alvo ficou sem
suspeita, e o complementar aceito foi de 122 para 169 provas (decisao 90).

## Depois do lote de 04/10: treinar pelo no, macetes, acento e o leitor

**O /geradas pelo no:** treinar as geradas misturava os temas da materia,
inclusive os que eu ainda nao tinha estudado. O seletor virou a arvore -
materia, assunto, subassunto, com a contagem -, e a ficha manda para la com o
no do tema ja escolhido (decisao 91).

**Macetes e explicacoes:** os dois arquivos nunca tinham existido. O Claude
Code respondeu os pedidos a mao, artigo por artigo contra o texto vigente
baixado da Camara e da ALESC: 40 macetes, e 6 das 10 explicacoes - as outras
4 dependem do texto da prova, que o radar nao guarda, e ficaram sem resposta
em vez de resposta chutada (decisao 92).

**O acento fora da web:** terminal, Telegram, auditoria e motivo de
elegibilidade. Uma ferramenta pos acento so em texto de saida e so em palavra
sem ambiguidade; o resto foi decidido um a um, e os valores que eu digito
ficaram como sao (decisao 93).

**Os conceitos associados** ganharam a conferencia que faltava: Confirmar ou
Tirar em cada questao, e a importacao nova deixou de acumular o que saiu da
resposta (decisao 94).

**O leitor**, de novo: o "Caso 3" do S7 de Sao Jose traz uma lista "1." a
"8." antes da questao 49, e o leitor tomava o "1." pelo numero; e dois
cadernos escrevem a caixa da alternativa como "square", em minusculas. Com os
dois consertos, e com a ultima alternativa parando no texto-base, os 3
cadernos fecharam e 9 outros perderam o texto-base grudado na "e" - inclusive
duas questoes da prova de 2019 do alvo. O acervo foi relido (ensaiado antes
numa copia), sem perder classificacao nenhuma (decisao 95).

## A auditoria independente e a Rodada 1 das correcoes (04/10)

**A auditoria** conferiu, em copias fora do repositorio e sem mudar nada, os
186 requisitos do pedido de evolucao, das regras invioláveis as regras do
CLAUDE.md: a contagem igual em todas as telas, a incidencia recalculada a mao,
o alvo intacto com uma prova complementar nova, o ANKI religavel, a migracao
desfeita, a suite com a rede bloqueada e com o relogio em 2026 e 2027, e 12
mutacoes do codigo. Resposta: PARCIALMENTE, com 8 defeitos e o plano em
rodadas (`docs/auditoria_independente.md`).

**A Rodada 1** consertou os quatro que nao pediam decisao: o teste que
quebraria o Actions em 01/11 (a data de fechamento fixa em 31/10/2026); a
importacao de geradas, que aceitava no inventado e o elemento vizinho do
pedido (decisao 96); e o traceback do modo revisao na simulacao. O resto esta
na pendencia G.

O Actions de 04/10, que a pendencia D mandava conferir, foi verde: o
`coleta: 2026-10-04` do radar-bot chegou ao GitHub (visto no push do fim da
auditoria), e o job so commita depois do `pytest -q` passar no Linux.

## A Rodada 2 das correcoes da auditoria (04/10)

O "Direito Processo Penal" de 2013 voltou para a geracao, o simulado por
materia e a revisao espacada: os filtros passaram a pedir todas as grafias
da materia ao `config/taxonomia.yml`, e o acerto por materia junta as duas
numa linha (decisao 97). E o `radar padrao`, o comando mais antigo das
provas, deixou de somar o alvo, o complementar e a IESES: sao tres blocos,
cada um com a sua amostra, e a prova recusada fica de fora com a conta dela
(decisao 98).

## As Rodadas 3 e 4 e o resto da auditoria (05/10)

Os oito defeitos da auditoria sairam. Migrar uma copia velha do banco nao
apaga mais as geradas do JSON (decisao 102), e a resposta do simulado volta
para a questao pela chave (103). Os 12 conceitos que a classificacao do
complementar tinha criado em dobro foram juntados no no do alvo, com tudo o
que apontava para eles, e a classificacao passa a recusar o nome parecido
(99). O modo revisao continua aceitando o no so praticado, agora de
proposito e dizendo quantos sao (101). Junto, os menores da auditoria e as 4
fichas de Portugues da primeira semana, que nunca tinham sido escritas.

## O pedido de 05/10: a reanalise, os diagnosticos e a nuvem

Para nao gastar tempo de estudo conferindo 232 classificacoes, a conferencia
do complementar passou a aceitar uma segunda leitura as cegas: 5 leituras
independentes classificaram de novo as 215 questoes, e onde caiu no mesmo no
a classificacao ficou conferida pelo Claude Code, com a marca na tela
(decisao 104). Sobraram 39. Os diagnosticos de 03/10, que nao tinham sido
feitos, passaram para 10/10, e o R+7 deles refaz todos os erros (decisao
105). Os 3 pares parecidos foram juntados e as 2 geradas erradas saíram.
Ficou levantado o que falta classificar (so Portugues e Raciocinio Logico, no
edital) e escrito o roteiro para levar o radar a nuvem com login.

## Portugues e Raciocinio Logico classificados (05/10)

A arvore de Portugues ganhou, debaixo dos assuntos do edital, o que a FEPESE
cobra e o edital nao nomeia (regencia, fonologia, o "ha" das lacunas, figuras
de linguagem). As 204 questoes do complementar sem classificacao passaram
por duas leituras independentes; onde caiu no mesmo no, ficou conferida pelo
Claude Code (161). Sobraram 24 para conferir e 19 pendentes, quase todas de
tema que o edital nao lista (decisao 106).

## A faixa de Portugues comeca no radar (05/10)

Com Portugues classificado, a ideia era fazer as faixas de Portugues no radar
em vez do Qconcursos. A conta mostrou que nao da: o acervo tem 251 questoes
distintas, e varios temas tem uma so. A faixa ficou mista: comeca pelas
questoes reais do tema que o radar tem e eu nao respondi, e termina no
Qconcursos (decisao 107).

## A revisao final do estudo: a Fase 1 e a R1 (05/10)

O pedido "revisao final do estudo" comecou por uma analise so de leitura: a
matriz edital 2019 x provas x Ciclo 1, o inventario do que a ficha e a faixa
mostram, a conferencia de 10 fichas contra o texto vigente (12 imprecisoes,
nenhum erro de fundo, e a regra 40 de Mandela a rever contra a traducao do
CNJ), a coerencia dos documentos (30 achados) e o saldo do estoque de
geradas. Duas descobertas mudaram o desenho: a "Aplicacao da lei penal"
aparecia como "nao caiu" com 4 questoes que cairam (pendentes), e
`python -m radar` nao funciona neste projeto (o comando e `radar.exe`). As 16
perguntas de decisao foram respondidas com as recomendadas.

Na R1, o "caiu ou nao caiu" virou uma conta so, prova a prova, com as
pendentes e o artigo gravado (decisao 108); a ficha passou a mostrar a
questao real inteira e os macetes ligados pela questao (decisao 109); a lei
seca ficou com o tema da teoria (decisao 110); e a aba Fichas abre no dia,
por bloco (decisao 111).

## R6: as questoes da faixa (05/10)

A faixa do art. 13 mandava fazer 8 questoes no Qconcursos e nao dizia nada do
radar, e o assunto sem gerada sumia da tela de gerar. Agora cada faixa de
questoes diz o tema e o no, manda primeiro ao Qconcursos e, se eu quiser
mais, as geradas: o botao quando ha, os 3 passos com o comando exato quando
nao ha (decisoes 112 a 115). O comando e o `radar.exe` do venv, que funciona
no Windows; o passo 1, copiado da tela, gerou o pedido do no certo.

## R3: as correcoes das fichas (05/10)

A segunda leitura de 10 fichas, agora com a traducao do CNJ das Regras de
Mandela e a compilacao da Camara pelo normas.leg.br, achou 12 imprecisoes e
nenhum erro de fundo. As 12 foram corrigidas, e a regra 40 de Mandela voltou
a letra do CNJ (decisao 117): 14 trechos em 7 fichas, com copia antes, o antes
x depois em `docs/conferencia_das_fichas.md` e a procedencia com o modelo
(decisao 116). As fichas continuam por conferir.

## R2: o resumo de cada tema e as explicacoes (05/10)

Cada tema do Ciclo 1 ganhou o resumo de uma tela para o caderno, dentro da
ficha: a parte "caiu ou nao caiu" sai na hora, e as outras sao texto de IA em
que cada frase diz a fonte (decisoes 118 e 119). O botao "Resumo" abre uma
janela por cima da pagina, so com CSS, em toda faixa com materia, e a de
varios temas abre a lista (decisao 120). O lote 1 (5 temas) foi aprovado; os
outros 60 vieram em 6 lotes escritos em paralelo e passaram pela mesma
conferencia. Depois, 64 das 76 questoes reais do alvo dos temas ganharam a
explicacao de onde estava a pegadinha; 12 ficaram de fora, sem fonte segura
(o texto-base da prova que o radar nao guarda, o sublinhado perdido, ou so
doutrina). A procedencia passou a dizer o modelo (decisoes 121 e 122).

## R4: o Ciclo 1 pela classe de cada tema (05/10)

O tempo de um tema que nao caiu nas duas provas virou revisao de um tema que
caiu, no mesmo dia e da mesma materia. Duas chaves novas no cronograma
fazem isso sem alongar o dia em nivel nenhum: o `teto` na faixa de rampa e a
`sobra_da_rampa` na faixa "Extra". Mudaram 7 dias de 06/10 a 07/11; os
minutos ficaram iguais e as questoes subiram um pouco onde a teoria virou
questao (decisao 124). O ensaio, feito numa copia carregada pelo proprio
radar, mostrou dois ajustes a proposta da Fase 1 (o teto par e as questoes),
que voce aprovou antes da gravacao.

## R5: o saldo do estoque de geradas (05/10)

Com o plano redistribuido, o saldo foi calculado pela mesma conta da faixa:
24 nos sem gerada, falta de 231 questoes contra a maior cota de uma faixa,
sobra de 410. Nada foi gerado: a falta se completa sob demanda, pelos 3 passos
de cada faixa (decisao 125).

## R7: os documentos (05/10)

O `docs/indice.md` diz para que serve cada documento e qual ler primeiro. As
incoerencias que a Fase 1 achou foram corrigidas: o diagnostico de 03/10 que
virou 10/10 no README e nas pendencias, os numeros velhos (8.433 questoes, 169
provas, 13 fichas sem no, 7 geradas rejeitadas), o "18 de 19" da auditoria
final, os itens resolvidos que continuavam abertos, a decisao 47 revista pela
116, e a nuvem com login, que virou a decisao 126. O "Estado atual" do
CLAUDE.md ficou mais curto. A secao H das pendencias e a lista unica do que
sobra, separada entre o que depende de voce e o que a IA pode fazer. Junto, a
10ª gerada rejeitada foi exportada para o JSON e os macetes de "Direito
Processo Penal" passaram ao nome do edital.

## Os itens 8, 2, 3, 4 e 5 do pedido de 05/10 (06/10)

Cinco melhorias pedidas de uma vez, na ordem que voce escolheu, com uma parada
para aprovar a lista de nos. **A fila de revisao virou uma so** (decisao 128):
a home deixou a agenda por assunto do `espacada.py` e mostra as pontas da fila
do Meu desempenho, e o botao revisa por elas; de passagem, o prazo 1-7-30
passou a acabar na revisao de 30 dias, e as duas ultimas contas em template
foram para o Python. **As 15 fichas sem no ganharam no** (129): 9 nos novos
pela lei e pelo edital, o art. 75 no lugar dele, e 6 resumos completados.
**A falta de geradas de 06 a 12/10 foi escrita** (131): 90 questoes lidas
contra a fonte antes de entrar; o formato de resposta passou a pedir o
modelo. **O texto-base das questoes de interpretacao do alvo** (132) mora no
banco, lido do caderno por colunas, e vai na tela, na ficha e no pedido - o
que destravou 10 das 12 explicacoes que faltavam. **As questoes do
complementar que os resumos citam** (133) ganharam 125 explicacoes. A suite
inteira nao foi rodada, a seu pedido: so os testes de cada item.

A auditoria de uso de 06/10 (so leitura, `docs/proposta_de_melhorias.md`):
31 telas medidas com uma regua unica numa copia do banco, 57 problemas de
precisao conferidos por verificador independente (8 criticos), 64 melhorias,
9 ideias e o rascunho do Hoje e do Meu foco. Voce aprovou a ordem: ate 07/11
so entra o que corrige numero ou prepara os sabados que medem. **O lote 1**
(decisoes 134 a 137) saiu no mesmo dia: os diagnosticos de 10/10 abrem a
manha e a noite; o dia que mede nao tem Plano B, e a Reduzida guarda a
medicao; o Resumo saiu das faixas que medem sem consulta; a Conferencia nao
apaga mais o artigo da questao; e os textos da Correcao pedem uma regra por
tema. Junto, o 29/09 foi corrigido (as 10 de Portugues anotadas eram as do
radar: o dia foi de 37 para 27 questoes, a semana 1 de 68 para 58) e voce
conferiu as 5 fichas dos temas ja estudados, o que pos Penal e
Constitucional na fila de revisao (de 8 para 17 pontas).

## O "Treinar geral no radar" (06/10)

Pedido seu, fora dos lotes da proposta: cada faixa de questoes ganhou, abaixo
dos botoes de cada no, um campo de quantidade e o "Treinar geral no radar"
(decisao 139) - as geradas de todos os nos da faixa, divididas por igual e
embaralhadas. A rodada guarda a faixa como a do botao do no, entao o aviso e o
treino de IA a contam sem mudanca nenhuma. So os testes do item foram rodados
(20, com o `tests/test_treinar_geral.py` novo); a suite inteira espera a sua
ordem.

## O link do Qconcursos de cada tema (06/10)

Tambem a seu pedido: o filtro escrito no plano nao existia no Qconcursos, e o
mais proximo trazia o art. 5º inteiro. Como o radar nao pode consultar o site,
voce copiou pelo F12 a lista de assuntos de 9 disciplinas (cada assunto com o
numero, em `C:\qconcursos`, fora do repositorio); a primeira tentativa veio
com 14 assuntos, porque a lista so carrega ao rolar ate o fim. Os 64 temas do
Ciclo 1 que vao ao Qconcursos foram casados aos assuntos do site, voce aprovou,
e 62 viraram o `config/qconcursos.yml` (as 2 de Redacao oficial ficam sem: a
disciplina nao foi baixada). A faixa ganhou o "Abrir no Qconcursos" com o
filtro pronto e o aviso quando o site e mais largo que o tema (decisao 140).
De passagem: a Legislacao Especial caiu em 2019 (10 questoes: Desarmamento,
Drogas, Maria da Penha e Tortura) e, no site, fica no Direito Penal (40). So os
testes tocados foram rodados (85); a suite inteira espera a sua ordem.

## O lote 2: o "fiz" e o "Fiz hoje" (06/10)

Voce viu "Fiz hoje: 5 questões" sem ter feito questao real, e "24" depois de
12 geradas. O 5 era o meio do treino de IA, somado na linha das reais; o 24,
as 12 geradas contadas de novo na faixa Fixacao, cujo "fiz" vinha com numero.
O servidor estava no ar desde antes da decisao 130, e por isso nao avisou.
Corrigido o dia como o 29/09, e feito o lote 2 (decisao 138): o "Fiz hoje"
virou "Questões reais (Qconcursos e provas)", "Treino de IA no radar" e
"Total do dia"; o "fiz no Qconcursos" vem vazio; a faixa feita no radar fecha
com o ✓ vazio e guarda so o tempo; e a faixa e a ficha mostram o treino de IA
do tema, fora do acerto. Rodados so os testes tocados (174); a suite inteira ficou para depois, a seu pedido.

## A correcao na hora, as geradas nunca feitas e a nota da faixa (07/10)

Tres pedidos seus, de uma vez (decisao 142). No treino, a questao volta
corrigida depois da letra: a certa em verde, a marcada em vermelho, a
explicacao e os macetes, as bolinhas da rodada, o "🔥 N seguidas" e o
"Proxima ->"; no erro, o caderno de erros abre preenchido. O diagnostico, o
simulado no radar e o R+7 continuam so no fim. A caixa "vou no chute",
marcada antes da letra, grava o chute ao lado do acerto. O sorteio das
geradas poe as nunca feitas primeiro (depois as erradas, depois as mais
antigas), e a faixa avisa com metade e com todas feitas, ja com os 3 passos
de gerar - no dado real, o no de Substantivo e adjetivo ja estava todo feito.
E cada faixa da tela Hoje ganhou o "📝 Como foi" (chutes fora do radar,
entendi, nota), separado do check, relido na ficha do tema e no Meu
desempenho, com o que eu nao entendi na frente: a lista do Ciclo 2. O banco
foi para a versao 7 (copia em `data/copias/migracao-v6-para-v7-...`).
