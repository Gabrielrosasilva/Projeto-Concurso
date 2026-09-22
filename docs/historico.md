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
