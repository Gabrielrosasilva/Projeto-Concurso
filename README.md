# Radar de Concursos

Sistema pessoal para acompanhar concursos publicos que valem a pena para mim:
coleta os que abrem, guarda num banco, e deixa filtrar por estado, banca e
palavra-chave. O filtro que importa e **onde a prova e aplicada** — Grande
Florianopolis e arredores.

Estado: **fase 1** — esqueleto e a primeira fonte (feed RSS) funcionando.
O roadmap completo esta no `CLAUDE.md`.

## Rodando pela primeira vez

No Linux ou no Mac:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

No Windows (prompt de comando), onde o executavel se chama `python` e nao
`python3`, e nao se usa `source`:

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
copy .env.example .env
```

Dai em diante os comandos sao iguais nos tres:

```bash
radar coletar
radar listar                       # so o que esta perto de voce
radar listar --abertas             # so o que da para se inscrever hoje
radar listar --todos               # tudo, inclusive o que e longe
radar web                          # http://localhost:8000
```

### Se a porta ja estiver em uso

```
A porta 8000 ja esta em uso.
Costuma ser um radar web aberto em outra janela - procure a janela e feche
com Ctrl+C.
```

E quase sempre um servidor que ficou aberto numa janela esquecida. Duas
saidas: feche a outra janela com Ctrl+C, ou suba noutra porta.

```bat
radar web --porta 8001
```

O proprio comando sugere uma porta livre quando isso acontece.

### Se o comando `radar` nao for reconhecido

```
'radar' nao e reconhecido como um comando interno ou externo...
```

O comando so existe no PATH quando o ambiente virtual esta **ativado**. Repare
no inicio do prompt: com o venv ligado aparece `(.venv)` na frente.

```
(.venv) C:\Projeto concurso claude\Projeto-Concurso>   <- funciona
        C:\Projeto concurso claude\Projeto-Concurso>   <- nao funciona
```

Duas saidas, as duas validas:

```bat
.venv\Scriptsctivate      :: liga o venv nesta janela
.
adar.bat web             :: ou chame pelo atalho, sem ativar nada
```

O `radar.bat` fica na raiz do projeto e repassa tudo para o executavel do
venv, entao `.
adar.bat listar --abertas` e qualquer outro comando funcionam
de dentro da pasta do projeto, com ou sem o venv ligado.

### Depois de cada atualizacao

Sempre os mesmos tres comandos, nesta ordem:

```bash
git pull
pip install -e ".[dev]"     # rapido quando nada mudou; nao custa rodar sempre
radar reclassificar         # so se o classificador ou o regioes.yml mudaram
```

**Voce nunca precisa apagar `data/radar.db`.** Quando o modelo ganha uma
coluna, o proprio programa cria essa coluna no banco ao iniciar, preenchendo
o valor padrao nas linhas que ja existiam. O que ele nao faz e renomear,
trocar tipo ou remover coluna - se um dia precisarmos disso, eu aviso antes.

### Filtro por distancia

Todo concurso coletado e classificado em um anel:

| anel | o que e |
|---|---|
| `nucleo` | Grande Florianopolis |
| `proximo` | Itajai, Blumenau, Tubarao, Lages e vizinhos |
| `remoto` | outro lugar, inclusive o resto de SC |
| `indefinida` | nao da para saber sem ler o edital |

A lista padrao mostra so `nucleo` e `proximo`. **Nada e apagado**: o resto
continua no banco e sai com `--todos` ou pelos atalhos da pagina web.

Todo registro guarda *por que* foi classificado assim, em `motivo_relevancia`,
e o motivo aparece na tela. Se a decisao estiver errada, da para ver onde.

```bash
radar listar --relevancia remoto    # so o que ficou de fora
radar listar --noticias             # o que o filtro achou que nao era concurso
radar reclassificar                 # depois de editar config/regioes.yml
```

`radar reclassificar` roda a regra de novo no banco inteiro, sem ir a
internet. Incluiu um municipio novo no YAML? Rode isso e os registros antigos
se corrigem na hora.

### As fontes

| fonte | o que traz | como |
|---|---|---|
| Concursos no Brasil | concurso de todo o pais, inclusive municipal de SC | feed RSS |
| FEPESE | os concursos da banca que mais atua em SC | API REST do WordPress |

A FEPESE entrega coisa que o agregador nao tem: a **banca ja vem preenchida**
(e o site dela), o **status vem da propria banca** numa lista fechada
("Inscricoes abertas", "Em andamento", "Encerrados") em vez de ser deduzido de
data escrita em texto corrido, e a **escolaridade exigida** vem junto. Cada
concurso ainda traz o endereco do hotsite, onde ficam edital, prova e gabarito
- e de la que a fase 3 vai montar o acervo.

#### Por que nao o Diario Oficial

O plano desta fase era o **Diario Oficial dos Municipios de SC**, que seria a
fonte primaria. Nao da: o `robots.txt` dele proibe robo.

```
User-agent: *
Disallow: /
Crawl-delay: 10
```

So o Bingbot tem permissao. Como a regra da casa e respeitar `robots.txt`, o
DOM/SC esta fora de raspagem. O caminho legitimo que o proprio site oferece e
o **alerta por e-mail** dele; ler essa caixa por IMAP fica como ideia futura.

Duas outras portas foram testadas no mesmo dia:

- **Querido Diario** (projeto de dados abertos que padroniza diarios
  municipais) seria o ideal, mas a API respondeu `503 no available server`.
  Vale tentar de novo mais para frente;
- **DOE-SC** (diario do estado) e uma aplicacao que so monta a pagina com
  JavaScript, sem HTML para ler. Precisaria de outra abordagem.

### Trazendo o historico (carga inicial)

O RSS e um **fluxo, nao um arquivo**. Ele entrega so os 15 itens mais
recentes, entao quem liga o radar hoje ve os concursos de hoje e nada do que
foi publicado antes. Foi a primeira duvida depois que o Telegram ficou pronto:
"por que so aparecem 14 concursos?".

A resposta e este comando, que anda para tras no feed:

```bash
radar carga-inicial --dias 90      # tres meses de historico
radar carga-inicial --dias 7       # so a ultima semana
radar carga-inicial --dias 90 --sim   # sem perguntar antes
```

Ele usa `?paged=N` do proprio feed, que devolve as paginas mais antigas com a
mesma estrutura da primeira. Por isso a carga inicial usa o mesmo parser e traz
os mesmos campos - titulo completo, data e categoria -, em vez de raspar HTML.

Roda **uma vez so**, na mao. Nao entra na coleta diaria. Duas protecoes:
pausa de 1,5s entre paginas, e parada automatica assim que uma pagina inteira
fica mais antiga que o periodo pedido.

Medido no site em 17/09/2026: cerca de 1,5 pagina por dia de historico, 15
itens por pagina. Noventa dias saem em uns 3 minutos.

### O que esta com inscricao ABERTA

Data de publicacao nao e prazo. Um edital publicado ha um mes pode estar com
inscricao aberta ate semana que vem, e um de ontem pode ja ter fechado. Para
saber o que da para fazer HOJE, o radar le a pagina de cada post:

```bash
radar detalhar                  # le ate 150 paginas
radar listar --abertas          # so o que da para se inscrever agora
```

`radar detalhar` traz tres coisas que o RSS nao da:

| o que | para que serve |
|---|---|
| prazo de inscricao | responder "o que esta aberto agora" |
| banca | saber que padrao de prova estudar |
| municipio de lotacao | resolver o concurso estadual (ver abaixo) |

Ele **nao le a pagina de todos**. Seriam 2.200 requisicoes por quase uma hora,
e 1.400 delas de outro estado. A ordem e: primeiro o que ja esta perto, depois
os concursos de SC que ficaram `indefinida`, depois os federais.

**O caso que motivou isto:** "Concurso SEFAZ (SC)" nao tem "Prefeitura de X"
no titulo, entao o classificador nao acha municipio nenhum e marca
`indefinida` - o concurso existe, esta no banco, mas nao aparece em "Perto de
mim". A pagina do post diz "lotacao em Florianopolis", e com isso ele vai para
o nucleo, onde deveria estar.

Quando a pagina cita varios municipios - comum em edital de secretaria
estadual, que lista vagas pelo estado inteiro - o radar **nao escolhe nenhum**
e o registro segue `indefinida`. Chutar seria pior.

Na pagina web ha a aba **Inscricoes abertas**, ordenada pelo prazo, e cada
cartao mostra quantos dias faltam. Sete dias ou menos aparece em vermelho.

### O mural

A estrela de cada concurso o fixa no **mural**, a coluna da esquerda que
aparece em qualquer aba. No celular ele vai para o topo.

Cada cartao do mural tem cor do anel, cidade, remuneracao, banca e o prazo em
vermelho com os dias que faltam.

### Meus favoritos

Clique na estrela de qualquer concurso para guardar na aba **Meus favoritos**.

Favorito e escolha sua, e por isso:

- **a coleta nunca mexe nele.** O titulo pode ser corrigido pela fonte, mas a
  estrela fica;
- **nenhum filtro esconde um favorito.** Nem distancia, nem salario, nem
  prazo vencido. Se voce marcou, voce ve;
- os favoritos aparecem ordenados por **quem fecha primeiro**, e o que nao tem
  prazo conhecido vai para o fim da lista em vez de sumir.

Em "Ver com o status completo", cada favorito mostra o **caminho completo** do
concurso, com a etapa atual em destaque:

```
previsto -> autorizado -> banca contratada -> edital publicado
-> inscricoes abertas -> encerrado
```

A etapa sai das datas, nao de palpite: com o prazo em maos da para afirmar se
esta aberto, se ainda vai abrir ou se ja encerrou. Sem prazo conhecido, o
status nao e inventado - a tela diz para rodar `radar detalhar`.

Pelo terminal:

```bash
radar listar                    # o id aparece na primeira coluna
radar favoritar 324             # guarda
radar favoritar 324 --remover   # tira
radar listar --favoritos
radar situacoes                 # recalcula os status (o tempo passa sozinho)
```

### Aba de noticias e andamento

```
Noticias e andamento  ->  procure "PM", "policia cientifica", "bombeiro"...
```

As outras abas filtram para nao afogar o que importa. Esta faz o contrario:
procura em **tudo** - qualquer regiao, qualquer fase, inclusive o que ja
encerrou. Concurso que ja passou e justamente o que diz se aquele orgao
costuma abrir.

O resultado nao vem por data, e sim por **andamento**: primeiro o que esta com
inscricao aberta, depois o que ja tem banca contratada, depois o autorizado, e
o encerrado por ultimo. No topo, um resumo de quantos ha em cada fase.

#### As fases antes do edital

O ciclo de vida do concurso comeca bem antes do edital, e isso sai no titulo
da noticia:

| fase | como aparece no titulo |
|---|---|
| `previsto` | "edital previsto", "deve sair", "expectativa de" |
| `autorizado` | "tem concurso autorizado", "recebe autorizacao" |
| `banca contratada` | "define FCC como banca", "vai contratar banca" |

`banca contratada` e o sinal mais valioso: costuma vir 2 a 4 meses antes do
edital, que e tempo de comecar a estudar o padrao daquela banca.

Se o concurso ja tem prazo de inscricao conhecido, o prazo manda - data e
fato, titulo e interpretacao.

### Filtrando

Todo filtro da pagina combina com a aba em que voce esta e com os demais.

**Remuneracao** tem o campo de minimo e, ao lado dele, uma caixinha que abre
com quatro faixas prontas: ate R$ 2.000, R$ 2.100 a R$ 5.000, R$ 5.000 a
R$ 10.000, e acima de R$ 10.000. Escolhida uma, o proprio botao passa a
mostrar qual esta valendo.

Nao ha campo de maximo: quem digita um valor quer dizer "a partir de X". As
faixas fechadas existem pela caixinha, que e mais rapida que digitar dois
numeros.

**Banca** aceita o nome curto e o por extenso: "FCC" e "Fundacao Carlos
Chagas" trazem os mesmos concursos. A tabela de apelidos e a mesma que o radar
usa para reconhecer a banca na pagina do edital.

**Palavra-chave** ignora acento e maiuscula, e procura tambem no municipio:
"palhoca" acha "Palhoca" com cedilha.

Nada disso quebra a pagina quando o campo fica vazio ou recebe texto que nao e
numero - o valor invalido e simplesmente ignorado.

### A remuneracao que o titulo nao traz

Mais da metade dos concursos nao informa salario no titulo. Nesses, o cartao
mostra **R$ ??** e um lapis: clicar abre um campo, e o valor que voce digitar
fica gravado.

Valor digitado **nao e sobrescrito** pela coleta nem pelo `reclassificar` - o
que voce leu no edital vale mais que o que da para adivinhar pelo titulo. E
ele entra no filtro de remuneracao como qualquer outro.

Aceita do jeito que se digita: `5200`, `R$ 5.200`, `5.200,50`, `5200.50`.

```bash
radar salario 324 5200     # grava
radar salario 324          # limpa
```

### Filtro de remuneracao

```bash
radar listar --salario-min 5000
```

Na web ha o campo **Salario min**, que combina com a aba em que voce esta.

Uma limitacao que a tela avisa: o salario e lido do **titulo** do post, e
1.115 dos 2.185 concursos nao trazem valor nenhum ali. Esses ficam de fora do
filtro. A pagina mostra quantos sao e oferece o link para ver sem o filtro -
entre eles esta, por exemplo, o concurso de 300 vagas de Sao Jose.

## O padrao da banca

```bash
radar questoes              # separa os cadernos do acervo em questoes
radar padrao                # o que a banca mais cobra, por materia
radar padrao --cargo Guarda # so nos cargos que me interessam
radar repetidas             # questoes que a banca reaproveitou
```

`radar questoes` nao vai a internet: trabalha nos PDFs que `radar provas` ja
baixou.

O caderno da FEPESE tem estrutura regular, e dois detalhes dela pouparam muito
trabalho:

1. **a materia vem da propria banca**, em cabecalho de secao ("Lingua
   Portuguesa 10 questoes"). Nao precisa adivinhar o assunto de cada questao;
2. **a alternativa correta esta marcada no texto**. O caderno usa um simbolo
   de caixa marcada que o extrator le como `Check-square`, contra `SQUARE` nas
   demais. Prova e gabarito no mesmo arquivo.

### O que saiu do acervo

125 cadernos renderam **5.021 questoes**, todas com materia e gabarito:

| materia | questoes | peso |
|---|---|---|
| Conhecimentos Especificos | 2.396 | 47,7% |
| Lingua Portuguesa | 1.048 | 20,9% |
| Conhecimentos Gerais | 754 | 15,0% |
| Nocoes de Informatica | 309 | 6,2% |
| Raciocinio Logico | 200 | 4,0% |
| Temas de Educacao | 180 | 3,6% |

E o achado que mais vale: dos 5.021, so **1.815 enunciados sao diferentes**.
A FEPESE reaproveita questao entre provas, e muito - uma delas aparece em **44
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
Social"). Em vez de adivinhar padrao por padrao, o que se repete em toda
pagina e tratado como mobilia. A sujeira caiu de 5,1% para 1,1% das questoes.

## Treinar: modo simulado

A ponta que fecha o ciclo. O radar acha o concurso, o acervo baixa as provas,
`radar questoes` separa as questoes - e aqui eu respondo elas.

Abre em `radar web`, no link **Simulado**. Nao tem comando de terminal: e uma
coisa de clicar, uma questao por tela.

Como funciona:

- **sem escolher materia**, o simulado usa as que caem em QUALQUER concurso -
  Lingua Portuguesa, Raciocinio Logico, Nocoes de Informatica e Conhecimentos
  Gerais. Isso importa aqui: o acervo nao tem prova de Guarda Municipal nem de
  Policia Penal, e essas quatro materias treinam mesmo assim;
- **a mesma questao nao aparece duas vezes na mesma rodada.** O sorteio e por
  enunciado, nao por linha: dos 5.021 registros so 1.815 sao perguntas
  diferentes, e sortear sem cuidado repetiria a mesma pergunta;
- **da para fechar a pagina no meio e voltar depois.** O lugar onde parei fica
  no banco, nao na sessao do navegador;
- **F5 nao responde de novo.** A questao ja respondida e ignorada, e o POST
  responde com redirecionamento;
- no fim vem a **revisao**, com o que eu marquei e qual era a correta, erros
  primeiro. Errar sem ver a correta nao ensina nada;
- a tela de comecar mostra o **acumulado de todas as rodadas**, com a materia
  de menor acerto em cima: e onde vale gastar tempo de estudo.

Uma armadilha que custou tempo: somar a coluna booleana `acertou` direto no
SQL **nao funciona**. O SQLAlchemy devolve a soma com o tipo da coluna, entao
2 acertos voltam como `True` e viram 1 - todo mundo ficava com 50%. A conta
passa por `case(...)` para virar inteiro antes de somar.

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

O vestigio existe - e a corrida de espacos - e a normalizacao de espaco em
branco o apagava. Agora `marcar_lacunas` roda ANTES de juntar as linhas,
porque a lacuna aparece em tres posicoes e duas delas some ao juntar: no meio
(`chegava    hora`), no comeco da linha (`   medida`) e no fim (`contar    `
com a frase seguindo abaixo).

Medido em 8 cadernos antes de mexer: 68 corridas de 3 espacos ou mais, e a
unica que nao era lacuna foi `CADERNO   `, que a limpeza de mobilia ja tira.

Resultado no acervo: **258 enunciados** (5,1%) ganharam lacuna. A conferencia
que vale: nas 193 questoes cuja resposta vem em itens (`a • a • as`), o numero
de lacunas bate com o numero de itens em **188** delas. Os 5 restantes sao
alternativas que ja vem numeradas na origem.

Junto saiu outra sujeira: 178 caracteres que nenhuma fonte sabe desenhar - o
caderno usa simbolos de fonte propria - e que viravam quadradinho no meio do
enunciado. Viram espaco, e nao nada, senao a palavra de antes cola na de
depois. E o simbolo mais o espaco ao redor viram UM espaco, senao " simbolo "
daria tres espacos e seria lido como lacuna que nao existe.

```bash
radar questoes --refazer   # passa o parser novo por cima do acervo inteiro
```

`--refazer` atualiza a questao no lugar, pela chave (prova, numero). Nao apaga
e grava de novo porque o simulado guarda o id da questao: o historico ficaria
apontando para o nada.

## Previsao de abertura

```bash
radar previsao
```

Tambem na web, no link **Previsao de abertura**. Responde a pergunta "onde
vale ficar de olho agora", municipio por municipio, perto de casa.

A conta tem chao e teto vindos da lei: o concurso vale por ate 2 anos,
prorrogaveis por mais 2. Antes de 2 anos o orgao ainda tem aprovado na fila;
passados 4, quem precisa de gente tem de abrir outro. **Dentro dessa faixa**,
quem manda e o ritmo do proprio municipio.

Duas escolhas que os dados reais forcaram:

1. **mediana, e nao media.** De Tubarao eu so conheco 2011 e 2026, e a media
   dizia "um a cada 15 anos, proximo em 2041". O buraco e o que eu nao
   coletei, nao concurso que deixou de existir;
2. **teto de 4 anos.** Biguacu tem 2021 e 2022 no historico - dois editais do
   mesmo momento, nao um concurso por ano.

Toda previsao vem com o motivo e com os anos que a embasam, porque eu preciso
poder conferir a conta:

```
ATRASADO Biguacu -> 2024
         2 concursos conhecidos (2021 a 2022), um a cada 2 ano(s).
         O ultimo foi ha 4 ano(s), passou 2 ano(s) do previsto.
```

**O que isto nao sabe, e a tela avisa:** o historico vem da FEPESE (2006 a
2026) e do feed de noticias (so 2026). Municipio que contratou outra banca
entre 2021 e 2025 tem concurso que nao esta aqui, e aparece mais atrasado do
que e.

### Uma grafia so para cada municipio

Isto quebrava a previsao antes de ela existir: o mesmo municipio estava no
banco em ate quatro grafias. A FEPESE grava `Palhoca` e o feed grava `Palhoça`;
`Florianopolis`, `Florianópolis` e `FLORIANOPOLIS` eram tres cidades para
qualquer conta por municipio.

Agora o municipio e gravado sempre na grafia de `config/regioes.yml`, que ja
era a fonte de verdade dos aneis. `radar reclassificar` conserta o que ja esta
gravado - inclusive o municipio confirmado pela pagina do edital, porque
trocar a grafia nao e reclassificar. Municipio de fora de SC volta como veio:
o YAML so tem municipio catarinense, e inventar grafia seria pior.

## Macetes: o costume da banca

Na web, no link **Macetes**. Voce escolhe a banca, escreve o cargo e o tema, e
a pagina varre as provas do acervo.

O tema e **texto livre** de proposito: escreva `crase` ou `primeiros socorros`,
e nao o nome exato da materia. A busca olha a materia E o enunciado, e ignora
acento, porque o nome que a banca usa ("Lingua Portuguesa") raramente e a
palavra que voce pensa ("crase").

**Nada e calculado antes de voce escolher a banca.** O retrato do acervo
inteiro misturava bancas e nao respondia pergunta nenhuma.

Quando o tema aponta para uma materia so - "crase" e Lingua Portuguesa em 56
das 59 questoes -, a pagina responde a pergunta seguinte com dois graficos:

1. **quantas questoes caem numa prova**, materia por materia. Na FEPESE:
   Conhecimentos Especificos 19,2 por caderno, Lingua Portuguesa 9,0,
   Conhecimentos Gerais 6,4, Informatica 5,2, Raciocinio Logico 5,0. A divisao
   usa os cadernos em que AQUELA materia apareceu, e nao o total: Temas de
   Educacao so cai em prova de professor, e dividir por tudo faria parecer que
   cai pouco quando cai muito onde cai;
2. **o que mais cai dentro daquela materia**, assunto por assunto, com o
   assunto procurado destacado. Em Lingua Portuguesa: interpretacao de texto
   289 questoes, verbos 141, classes de palavras 104, concordancia 98, crase 56.

O assunto sai de um **catalogo de palavras-chave escrito a mao**, e nao de
adivinhacao: da para conferir cada padrao abrindo as provas. Cobertura medida
em enunciados distintos - portugues 76%, informatica 61%, conhecimentos gerais
59%, raciocinio 53% - e o que sobra a tela conta como "sem assunto detectado",
em vez de empurrar para um assunto qualquer.

O que a pagina mostra, alem disso, tudo por contagem:

- **o que mais cai** no recorte, materia por materia;
- **como a banca pergunta**, com o conselho pratico de cada forma. Pedir a
  INCORRETA (4,0% das questoes) e o jeito classico de fazer quem le rapido
  marcar a alternativa verdadeira e errar;
- **as questoes que ela repete**, com em quantos cadernos cada uma apareceu.
  Sao as que mais valem estudar;
- **as palavras que mais aparecem**, que e o mais perto de "assunto" que da
  para chegar so contando;
- **sobre o chute**: a distribuicao da letra correta.

### Duas coisas que os dados corrigiram

**O "chute na C" nao existe nesta banca.** No acervo inteiro as cinco letras
ficam entre 19,5% e 20,5%. Nao ha letra mais provavel.

**A repeticao mentia nas contas.** Buscando "crase" saem 59 questoes, mas so
**7 enunciados diferentes** - a mesma questao aparece em 38 cadernos, e a
resposta dela e "d". Contando todas, o gabarito dizia "letra d em 64%", e a
conclusao seria chutar d. Agora gabarito e palavras contam **uma vez por
enunciado**; materia e forma de perguntar contam todas, porque questao
repetida pesa mesmo mais na prova que voce vai fazer.

Junto veio um minimo de amostra: **abaixo de 50 enunciados diferentes a pagina
nao afirma nada** sobre a letra. Com 7 questoes, o que parece tendencia e
sorteio.

### Por que so aparece a FEPESE

O menu de bancas vem das **provas baixadas**, e nao dos concursos coletados.
AMEOSC, Cebraspe, FURB, FCC, FGV e IESES ja aparecem nos concursos, mas sem
prova no acervo - e a tela diz isso, em vez de parecer que o radar so conhece
uma banca.

Cada banca publica as provas de um jeito diferente, entao incluir uma delas
quer dizer escrever um coletor para o site dela. Da para fazer, uma de cada
vez. A FEPESE veio primeiro por ser a que mais aplica prova perto de casa.

### O que ainda nao esta la

Pegadinha especifica e macete de memorizacao **nao saem de contagem**: alguem
precisa ler as questoes e perceber o padrao. Isso fica para quando a leitura
por IA entrar. Ate la a pagina nao inventa: tudo o que ela mostra da para
conferir abrindo as provas do acervo.

### Quando o link aparece mas da erro

Sintoma confuso, e vale saber de cor: voce clica numa aba que esta ali na tela
e recebe erro de pagina inexistente.

O motivo e que **a tela e o codigo sao lidos em momentos diferentes**. O
template e lido do disco a cada visita, entao o link novo aparece assim que
voce atualiza o repositorio. O codigo Python e lido uma vez so, na partida,
entao a rota nova nao existe no servidor que ja estava rodando.

A solucao e parar o `radar web` com `Ctrl+C` e subir de novo. A pagina de erro
agora detecta esse caso sozinha - ela compara a data dos arquivos `.py` com a
hora em que o servidor subiu - e diz isso, em vez do
`{"detail":"Not Found"}` cru do FastAPI.

Existe `radar web --recarregar`, que reinicia sozinho ao salvar arquivo, mas
ele fica **desligado por padrao**: sobe um segundo processo que reimporta
tudo, e isso quebra no Windows quando o caminho da pasta tem espaco no nome -
que e o caso aqui (`C:\Projeto concurso claude\...`).

## Fonte 3: IESES

Segunda banca catarinense do radar. Ela fica em Florianopolis e faz concurso de
prefeitura da regiao - Biguacu e Gaspar estao na lista dela.

Como foi achada: `ieses.org/projetos` e uma tela que carrega a lista por
JavaScript, com botao "carregar mais". O arquivo `/projetos-static/projetos.js`
mostra de onde vem o dado, `/projetos/api?offset=&limit=`, e essa API devolve
JSON limpo. Melhor que raspar a tela - nao quebra quando mudam o CSS.

Nao ha `robots.txt` no dominio (404), entao nada esta declarado como proibido.
O coletor continua se identificando no User-Agent e respeitando o atraso.

Dois limites, medidos:

1. **sao 26 projetos**, de 2021 a 2026. A API nao devolve o historico inteiro
   da banca, so o que esta publicado no site;
2. **10 dos 26 hotsites ja sairam do ar** - erro de SSL ou de Cloudflare, quase
   todos de 2023 para tras. O que sobra ainda traz Biguacu 2024 e Gaspar 2024.

Uma coisa que o coletor **nao** faz: afirmar `uf=SC`. A IESES e catarinense mas
faz concurso fora (tribunal do Amazonas, gas do Mato Grosso do Sul), e afirmar
SC mandaria esses para o anel errado.

### Avisos no Telegram

O radar manda uma mensagem por concurso novo que interessa, com o link da
fonte junto - a ideia e nao precisar abrir o computador para saber do que se
trata.

**Configurar, uma vez:**

1. No Telegram, fale com o **@BotFather**, mande `/newbot` e escolha um nome.
   Ele responde com um **token**.
2. Fale com o **@userinfobot**. Ele responde com o seu **chat_id** numerico.
3. Coloque os dois no arquivo `.env`:

   ```
   RADAR_TELEGRAM_TOKEN=...
   RADAR_TELEGRAM_CHAT_ID=...
   ```

4. Mande `/start` para o **seu** bot. O Telegram nao deixa um bot puxar
   conversa: enquanto voce nao falar com ele, ele nao pode te responder.
5. Confira:

   ```bash
   radar testar-telegram
   ```

**No GitHub Actions**, os mesmos dois valores vao em
*Settings > Secrets and variables > Actions*, com os mesmos nomes. O `.env`
esta no `.gitignore` e nunca sobe para o repositorio.

**Quem vira mensagem:** `nucleo`, `proximo` e `indefinida`. Os indefinidos
entram de proposito - sao os federais e os sem UF, que ainda podem aplicar
prova em Florianopolis. Melhor dois avisos a toa do que perder o unico que
interessava. `remoto` e `noticia` nunca viram mensagem.

Cada concurso e avisado **uma vez so**: a data fica em `avisado_em` e a coleta
de amanha nao repete a de hoje.

**Teto de 10 mensagens por coleta.** Nao e economia, e protecao: se uma regra
de classificacao quebrar, o estrago fica em 10 mensagens mais um alerta, em
vez de 200 notificacoes as 6h da manha. O que sobrar continua pendente e sai
na proxima rodada.

```bash
radar avisar                # manda o que esta pendente
radar avisar --limite 3     # teto menor nesta rodada
radar testar-telegram       # so uma mensagem de teste, nao mexe no banco
```

### A interface web

```bash
radar web                       # so nesta maquina
radar web --porta 9000          # outra porta
radar web --host 0.0.0.0        # abre tambem no celular, na mesma wi-fi
radar web --recarregar          # reinicia ao salvar arquivo (para desenvolver)
```

O modo `--recarregar` vem **desligado**. Ligado, o uvicorn sobe um segundo
processo que reimporta o projeto, e isso quebra no Windows quando o caminho
da pasta tem espaco no nome. Desligado, o servidor e um processo so.

O `pip install -e` instala o projeto em modo editavel: o comando `radar` passa
a existir no PATH do venv e o Python acha o pacote sozinho. E por isso que nao
existe mais `PYTHONPATH=src` espalhado pelos comandos.

Rodar os testes:

```bash
pytest -q
```

Os testes usam arquivos de exemplo em `tests/fixtures/` e um SQLite temporario.
Nenhum deles vai a internet, entao passam offline e rodam em menos de 1s.

## Como o projeto esta organizado

```
src/radar/
├── config.py       le ambiente (.env). Nenhum efeito colateral no import.
├── models.py       tabela `concursos`
├── db.py           conexao criada sob demanda, nao no import
├── servico.py      roda coletores, grava com upsert, consulta
├── util.py         fuso horario e formatacao de data
├── cli.py          comandos de terminal
├── collectors/
│   ├── base.py                  contrato: toda fonte herda de Coletor
│   └── concursos_no_brasil.py   fonte 1 (feed RSS)
└── web/app.py      interface web

config/
├── regioes.yml     os tres aneis de distancia   (lido a partir da fase 1.5)
└── perfil.yml      seus dados para elegibilidade (lido a partir da fase 2.5)
```

A ideia central: **cada fonte e um arquivo isolado em `collectors/`**. O resto
do sistema nao sabe de onde veio o dado. Somar o diario oficial de SC depois e
criar um arquivo e registra-lo em `servico.COLETORES` — nada mais muda.

## Adicionando uma fonte nova

```python
# src/radar/collectors/minha_fonte.py
from radar.collectors.base import Coletor, ItemColetado

class MinhaFonte(Coletor):
    nome = "minha_fonte"

    def coletar(self) -> list[ItemColetado]:
        html = self.get("https://exemplo.com/concursos").text
        # ... extrair os dados ...
        return [ItemColetado(titulo="...", url="...", uf="SC")]
```

Depois inclua em `COLETORES`, dentro de `servico.py`.

O `self.get()` herdado ja cuida de tres coisas por voce: checa o `robots.txt`
do site, manda o `User-Agent` do projeto e espera o intervalo configurado
entre uma requisicao e outra ao mesmo host.

## O que o radar guarda

Um concurso e identificado pela **url**. Se a mesma url aparecer de novo numa
coleta seguinte, o registro e **atualizado**, nao duplicado — e por isso que
uma mudanca de `inscricoes_abertas` para `encerrado` chega no banco.

Duas colunas sao suas e a coleta nunca encosta nelas: `interesse` e `notas`.

O ciclo de vida fica em `situacao`:

```
prevista → autorizado → banca_definida → edital_publicado
→ inscricoes_abertas → encerrado
```

## Automacao

`.github/workflows/coleta.yml` roda a coleta todo dia as 6h de Florianopolis,
no GitHub Actions, e commita o resultado. Tambem da para disparar na mao pela
aba Actions.

Actions e gratuito em repositorio privado ate 2.000 minutos por mes; a coleta
gasta uns 3 minutos por dia. Sua maquina nao roda nada: ela so e usada quando
voce abre a web ou pede para baixar prova.

## Sobre as fontes

Nao existe API oficial unica de concursos no Brasil. A fase 1 usa o **feed
RSS** do Concursos no Brasil de proposito: RSS e publico, estavel e feito para
ser lido por programa, e nao quebra quando o site muda o layout.

Vale saber da limitacao: **RSS e um fluxo, nao um arquivo.** Ele entrega o que
e recente, entao "todos os concursos do ano" nao sai dele — isso e a fase 1.6,
com uma carga inicial pelas paginas de arquivo do site.

Regras da casa para as proximas fontes:
- respeitar o `robots.txt`;
- manter o intervalo entre requisicoes (`RADAR_REQUEST_DELAY`);
- identificar-se no `User-Agent`;
- guardar sempre o link original — o sistema e um indice, nao um substituto.

## O acervo de provas

```bash
radar provas --limite 20     # le os hotsites e baixa o que achar
radar baixar-provas          # reconstroi o acervo a partir do manifesto
```

Cada concurso da FEPESE tem um hotsite proprio, e e nele que ficam os PDFs:

| pagina do hotsite | o que tem |
|---|---|
| `?go=edital` | o edital de abertura |
| `?go=provas` | o caderno de prova de cada cargo, e os gabaritos |

O caderno vem com o **cargo no rotulo do link** ("Monitor de Transporte
Escolar", "Supervisor Escolar"). E isso que importa: o que vale estudar e o
padrao da banca no *seu* cargo, nao a media de todos.

`radar provas` nao le os 520 hotsites de uma vez - seriam horas de requisicao
e a maior parte nao interessa. A ordem e: concurso **ja encerrado** (que e o
que tem prova publicada) e **perto de casa** primeiro, depois os indefinidos.

### Por que os PDFs nao ficam no git

Os PDFs vao para `data/provas/`, que esta no `.gitignore`.

O que e versionado e o **manifesto** (`data/provas.json`): link de origem,
banca, orgao, municipio, cargo, ano, tipo e o `sha256` de cada arquivo. Com
ele, `radar baixar-provas` reconstroi o acervo inteiro em qualquer maquina, e
o hash prova que o arquivo e o mesmo.

A conta que motiva isso: os primeiros 29 documentos deram **37 MB em disco** e
**18 KB de manifesto**. Git guarda uma copia inteira de cada arquivo binario a
cada commit, entao o acervo no repositorio o deixaria grande e lento em pouco
tempo. Versionar a receita em vez do artefato e a mesma logica de Dockerfile e
imagem.

Os caminhos no manifesto usam barra normal mesmo no Windows, senao a outra
maquina nao acharia os arquivos.

## Nota sobre dependencias

As versoes estao presas no `pyproject.toml`, inclusive o `click` — ele e
dependencia indireta do `typer` e uma versao nova dele ja quebrou a CLI aqui.
Se a coleta diaria comecar a falhar por instalacao, o proximo passo e gerar um
lock com `pip freeze`.
