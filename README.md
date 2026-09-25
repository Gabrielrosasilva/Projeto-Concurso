# Radar de Concursos

Sistema pessoal para acompanhar concursos publicos que valem a pena para mim:
coleta os que abrem, guarda num banco, le o edital, baixa as provas antigas e
deixa treinar em cima delas.

O alvo principal e **Policia Penal SC**, e depois dele as outras carreiras de
seguranca publica. Para o resto, o filtro que importa e **onde a prova e
aplicada** — Grande Florianopolis e arredores.

**Estado: fases 1 a 6, 8 e 9 prontas**, fase 7 parcial. Tres fontes coletando,
elegibilidade lida do edital, 5.928 questoes catalogadas, simulado, previsao de
abertura, a aba Macetes, a home "Meu foco" e a aba Acompanhando.

Os outros documentos do projeto:

- **[CLAUDE.md](CLAUDE.md)** — contexto permanente, para trabalhar no codigo;
- **[docs/decisoes.md](docs/decisoes.md)** — as decisoes ja tomadas, com o motivo;
- **[docs/historico.md](docs/historico.md)** — como cada fase foi feita, com os
  numeros medidos;
- **COMO_LIGAR_A_IA.txt** — o passo a passo da unica parte que custa dinheiro.

## Instalando

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

Dai em diante os comandos sao iguais nos tres. Para conferir que ficou de pe:

```bash
radar atualizar
radar web          # http://localhost:8000
pytest -q
```

O `pip install -e` instala o projeto em modo editavel: o comando `radar` passa
a existir no PATH do venv e o Python acha o pacote sozinho. Por isso nao existe
`PYTHONPATH=src` espalhado pelos comandos.

### Depois de cada atualizacao

Sempre os mesmos tres comandos, nesta ordem:

```bash
git pull
pip install -e ".[dev]"     # rapido quando nada mudou; nao custa rodar sempre
radar reclassificar         # so se o classificador, o regioes.yml ou o
                            # alvo.yml mudaram
```

**Voce nunca precisa apagar `data/radar.db`.** Quando o modelo ganha uma
coluna, o proprio programa cria essa coluna no banco ao iniciar, preenchendo o
valor padrao nas linhas que ja existiam. O que ele nao faz e renomear, trocar
tipo ou remover coluna — se um dia precisarmos disso, eu aviso antes.

### Quando alguma coisa nao sobe

**`'radar' nao e reconhecido como um comando...`** — o comando so existe no
PATH com o ambiente virtual **ativado**. Repare no inicio do prompt: com o venv
ligado aparece `(.venv)` na frente.

```
(.venv) C:\Projeto concurso claude\Projeto-Concurso>   <- funciona
        C:\Projeto concurso claude\Projeto-Concurso>   <- nao funciona
```

Duas saidas, as duas validas: ativar o venv (`.venv\Scripts\activate`) ou
chamar pelo atalho `radar.bat`, que fica na raiz e repassa tudo para o
executavel do venv, com ou sem venv ligado.

**`A porta 8000 ja esta em uso.`** — e quase sempre um `radar web` esquecido em
outra janela. Feche com Ctrl+C, ou suba noutra porta: `radar web --porta 8001`.
O proprio comando sugere uma porta livre.

**Um link que esta na tela responde erro 404.** E o servidor rodando codigo
antigo: pare o `radar web` com Ctrl+C e suba de novo. A pagina de erro detecta
esse caso sozinha e diz isso. O porque esta no
[historico](docs/historico.md#dois-sintomas-confusos-que-vale-saber-de-cor).

## O dia a dia

```bash
radar atualizar
```

Um comando so, que roda a rotina inteira na ordem em que ela faz sentido —
coletar, ler a pagina dos novos, baixar edital, ler o que o edital exige e
conferir retificacao. **Ele nao manda mensagem**: quem avisa e o robo do
GitHub, uma vez por dia, e ele e o unico (`--avisar` manda daqui assim mesmo):

```
1/5 Coletando das fontes
   concursosnobrasil: 2 novo(s) | fepese: 0 novo(s) | ieses: 0 novo(s)
2/5 Lendo a pagina dos concursos novos
   15 pagina(s) lida(s): 1 com prazo de inscricao, 0 com banca
3/5 Baixando edital de concurso aberto
   5 concurso(s) lido(s): 18 edital(is)
4/5 Lendo o que o edital exige
   5 concurso(s), 5 com exigencias lidas
5/5 Conferindo retificacao de edital
   10 edital(is) conferido(s), nenhum mudou

Tudo em dia.
19 concurso(s) com inscricao aberta agora.
```

A ordem **nao e opcional**: cada etapa depende da anterior. Etapa que falha e
registrada e a rotina segue. Duas opcoes: `--avisar` manda no Telegram daqui
(por padrao nao manda), e `--completo` tambem baixa provas novas e le as
questoes delas (fica de fora do dia a dia porque demora).

### Trocando com o GitHub

```bash
radar sincronizar
```

O robo sabe o que apareceu na coleta e o que ele ja avisou; voce sabe quais
concursos marcou com a estrela e o que anotou neles. Este comando junta os
dois: `git pull` → `radar importar` → `radar exportar` → commit → push.

A ordem importa. Importar **antes** de exportar e o que traz as marcas de
aviso do robo para o seu banco antes de voce escrever o JSON de volta — na
ordem inversa, ele mandaria tudo de novo no dia seguinte. Ele so encosta nos
JSON do radar em `data/`; o resto da pasta fica como esta, e conflito de
rebase ele nao tenta resolver: para e mostra o erro.

Um deles e **`data/simulados.json`**: cada simulado e cada resposta que voce
deu. E o unico dado que nao se reconstroi de lugar nenhum, e ate 25/09/2026
ele vivia so no `radar.db`. A questao vai nomeada pelo caderno e pelo numero
(a gerada, pela impressao), porque o id muda quando o banco e refeito. O
arquivo so cresce: simulado cujas questoes ainda nao foram extraidas neste
banco fica de fora do importar, e contado, mas nao sai do arquivo.

Rode depois de marcar favorito ou anotar alguma coisa. E assim que o robo
passa a conhecer a sua estrela — sem isso, ele nunca avisa mudanca de
favorito.

Depois disso, o lugar de olhar e a web:

```bash
radar web                       # so nesta maquina
radar web --porta 9000          # outra porta
radar web --host 0.0.0.0        # abre tambem no celular, na mesma wi-fi
```

### A pagina web, aba por aba

| aba | para que serve |
|---|---|
| **Perto de mim** | o padrao: `nucleo` e `proximo`, com os filtros |
| **Inscricoes abertas** | ordenada pelo prazo; 7 dias ou menos aparece em vermelho |
| **Meus favoritos** | o que eu marquei, ordenado por quem fecha primeiro |
| **Noticias e andamento** | procura em **tudo**, e ordena por fase, nao por data |
| **Simulado** | responder questoes das provas do acervo |
| **Macetes** | o costume da banca, por contagem |
| **Previsao de abertura** | onde vale ficar de olho agora, municipio por municipio |
| **Calendario** | explica e entrega o `.ics` dos prazos |

Os favoritos tem aba propria, **[Acompanhando](#como-a-tela-e-organizada)**.
Ela substituiu o mural lateral, que mostrava os mesmos concursos num cartao
apertado em toda pagina.

**Favorito e escolha sua:** a coleta nunca mexe nele, e **nenhum filtro o
esconde** — nem distancia, nem salario, nem prazo vencido. Isso vale para os
recortes que voce nao pediu (o anel padrao da tela, a faixa de remuneracao);
uma busca por palavra ou um anel escolhido a dedo continuam sendo perguntas, e
a resposta nao vem com um favorito de outro lugar no meio.

A aba **Noticias e andamento** faz o contrario das outras: nao filtra nada.
Quem procura "PM" quer saber de qualquer policia militar, onde estiver e na
fase em que estiver. Concurso que ja passou e justamente o que diz se aquele
orgao costuma abrir.

### Filtrando

Todo filtro combina com a aba em que voce esta e com os demais.

- **Remuneracao**: um campo de minimo (quem digita um valor quer dizer "a
  partir de X") e uma caixinha com quatro faixas prontas. O filtro **exclui
  quem nao tem valor conhecido**, e a tela avisa quantos ficaram de fora — o
  salario e lido do titulo, e 1.115 dos 2.185 concursos nao trazem valor ali;
- **Banca**: aceita nome curto e por extenso — "FCC" e "Fundacao Carlos Chagas"
  trazem os mesmos concursos;
- **Palavra-chave**: ignora acento e maiuscula, e procura tambem no municipio —
  "palhoca" acha "Palhoça" com cedilha.

Campo vazio ou com texto que nao e numero nao quebra a pagina: o valor invalido
e ignorado. E com filtro ligado e zero resultado, a tela diz que foi **o
filtro** que nao achou nada.

### Como a tela e organizada

No topo, quatro destinos e um menu:

| item | o que tem la |
|---|---|
| **Meu foco** | a home: a situacao do alvo principal |
| **Concursos** | a lista, com busca, atalhos e filtros |
| **Acompanhando** | um bloco por favorito: o que mudou e o que fazer agora |
| **Estudar** | Macetes e Simulado, nesta ordem |
| **Mais** | Previsao e Calendario |

**Meu foco** e a pagina inicial, e responde "o que esta acontecendo com o
concurso que eu espero?". Ela mostra se ha edital aberto, qual foi o ultimo
concurso, a banca e a validade; os sinais recentes (eventos e noticias do
alvo); as materias do edital com o peso de cada uma, ao lado do que caiu de
verdade nas provas **e do meu acerto em cada uma**; e um botao para treinar 20
questoes do proprio cargo.

Na tabela de materias, as que estao **acima da media da prova** ficam em
negrito — no edital de 2019 sao sete, e valem 80 das 100 questoes. A pior
delas ganha o rotulo **"comece por aqui"**: errar numa materia de 5 questoes
custa 5 questoes, errar numa de 15 decide a prova. Materia que voce nunca
treinou aparece como "nao treinei" e nao concorre ao destaque — zero por cento
diria que voce errou tudo.

Logo abaixo vem **Onde estudar primeiro**, que desce um andar: dentro da
materia, **qual assunto**. "Estudar Direitos Humanos" nao e uma tarefa de
tarde; "estudar as Regras de Mandela" e. A conta e esta, e nao ha nada alem
dela:

    questoes esperadas = o peso da materia no edital
                         x a fatia que aquele assunto ocupa nas provas
    pontos a ganhar    = questoes esperadas x (1 - seu acerto no simulado)

Sao duas colunas porque nenhuma decide sozinha: um assunto de 10 questoes em
que voce acerta 90% vale 1 ponto a recuperar, e um de 4 questoes em que voce
acerta 25% vale 3. O grafico e de barras deitadas, CSS puro, do maior para o
menor, e uma frase curta em cima dele repete em portugues o que a primeira
barra diz em pixel.

Cada linha mostra **em quantas questoes ela se apoia**, e separa o que e seu do
que nao e: "13 do meu cargo · 57 de reforco". Sao so duas provas do cargo no
acervo, e duas provas nao sustentam uma fatia - o **reforco** e a mesma banca
nas mesmas materias, em outros concursos. Os dois numeros nunca aparecem
somados.

Assunto que voce nunca treinou fica com barra **amarela** e entra na ordem so
pelas questoes esperadas, dizendo isso na tela: sem acerto medido nao ha pontos
a ganhar para calcular, e zero por cento seria mentira. Cada assunto de Direito
ganha um link **"ler a lei"**, que vai para o Planalto (lei federal e
Constituicao) ou para a ALESC (lei estadual de SC) e sai de `config/leis.yml`.
E so link: o radar nao baixa nem guarda o texto de lei nenhuma.

O botao de treino monta a rodada nesta ordem: primeiro as questoes das
**provas do proprio cargo**; quando elas acabam, as da **mesma banca nas
mesmas materias** em outros concursos; e so entao repete o que voce ja
respondeu, dizendo que repetiu. Materia que nao caiu na sua prova nao entra.

Quem e o alvo sai de `config/alvo.yml`. **Onde o dado nao existe, a tela diz
"nao sei ainda"** - ela nunca preenche por conta propria. A banca aparece como
`hipotese: FEPESE, que fez 2013 e 2019` enquanto nao houver edital novo
dizendo quem e.

Um cartao pequeno, **De olho**, fecha a parte de cima: uma linha por cidade da
lista `de_olho` do `config/alvo.yml` - hoje a Guarda Municipal de Florianopolis
e a de Balneario Camboriu - com a situacao de cada uma. A cidade que ainda nao
tem nada no radar continua na lista, dizendo "nada no radar ainda": sumir com
ela responderia "nao ha concurso", que e outra coisa de nao saber.

**Acompanhando** e a aba dos favoritos, um bloco por concurso marcado. Cada
bloco traz:

- a **contagem de dias** — "inscricao fecha em 5 dia(s)", em vermelho quando
  falta uma semana ou menos, e "nao sei ainda" quando nao ha prazo conhecido;
- a **proxima acao** — inscrever-se, ler o edital, estudar o padrao da banca,
  so acompanhar. Ela sai da situacao gravada e do prazo lido, nunca de
  palpite: sem dado, ela diz que nao sabe;
- a **linha do tempo** inteira, do mais novo para o mais velho, com data e com
  o link do que mudou (o PDF retificado, por exemplo).

O **Telegram avisa sozinho** quando um favorito muda de verdade: edital
publicado, edital retificado, inscricao abrindo, inscricao fechando e prova
marcada. Os outros acontecimentos ("apareceu", "de prevista para autorizado")
ficam na linha do tempo sem tocar o celular. Esse aviso nao passa por filtro de
distancia nem disputa o teto com o aviso de concurso novo — ele sai primeiro.

A regra de quem fica na barra e quem fica no "Mais": o que eu abro todo dia
fica a vista, o que eu abro de vez em quando fica no menu.

Em **Concursos**, a busca vem primeiro - e o que resolve o caso que atalho
nenhum resolve. Depois vem quatro atalhos: **Perto**, **Estadual SC**,
**Abertos** e **Todos**. Longe, A confirmar e a busca em tudo ficam em **mais
filtros**, que nasce fechado e abre sozinho quando ha filtro ligado.

Cada cartao mostra o titulo e uma linha so: **onde &middot; salario &middot;
prazo**. Sao as tres perguntas que se faz antes de decidir abrir o concurso.
Banca, tipo, exigencias do edital, motivo da classificacao e a anotacao ficam
em **detalhes**, fechado - mas o conteudo continua no HTML, entao o Ctrl+F do
navegador continua achando.

A lista mostra **30 cartoes por vez**, com "ver mais" de 30 em 30.

### O filtro por distancia

Todo concurso coletado e classificado em um anel:

| anel | o que e |
|---|---|
| `nucleo` | Grande Florianopolis (na tela aparece como "Perto") |
| `proximo` | Itajai, Blumenau, Tubarao, Lages e vizinhos |
| `estadual` | orgao estadual de SC, sem municipio (na tela, "Estadual SC") |
| `remoto` | outro lugar, inclusive o resto de SC |
| `indefinida` | nao da para saber sem ler o edital |

`estadual` e o unico que nao sai de `config/regioes.yml`: e a Secretaria de
Estado, a Policia Civil, Militar, Penal e Cientifica, o Corpo de Bombeiros — o
orgao que serve o estado inteiro e nao tem municipio no titulo. Os polos de
prova so saem no edital, entao ele **nunca vira `nucleo` por palpite**; mas
tambem nao pode ficar enterrado em `indefinida`, porque e onde mora a Policia
Penal SC.

A lista padrao mostra so `nucleo` e `proximo`. **Nada e apagado**: o resto
continua no banco e sai com `--todos` ou pelos atalhos da pagina web. Todo
registro guarda *por que* foi classificado assim, em `motivo_relevancia`, e o
motivo aparece na tela.

Os aneis sao configurados em `config/regioes.yml`. Incluiu um municipio novo la?
Rode `radar reclassificar` e os registros antigos se corrigem na hora, sem ir a
internet.

### O que eu anoto: notas, favorito e salario

Tres campos sao **meus**, e a coleta nunca os sobrescreve:

- a **estrela**, que leva o concurso para a aba Acompanhando e liga o aviso no
  Telegram quando algo importante mudar nele;
- o **"+ anotar"**, uma caixa de texto para o que nenhuma fonte sabe
  ("conversei com quem fez em 2022", "prova cai no mesmo dia da outra");
- a **remuneracao digitada**. Mais da metade dos concursos nao informa salario
  no titulo: o cartao mostra `R$ ??` e um lapis. Aceita do jeito que se digita
  (`5200`, `R$ 5.200`, `5.200,50`), e entra no filtro como qualquer outro.

## Os comandos

```bash
radar atualizar             # a rotina do dia a dia (faz quase tudo)
```

**Coletar e classificar**

```bash
radar coletar               # so a coleta das tres fontes
radar detalhar              # le a pagina do post: prazo, banca, lotacao
radar reclassificar         # reaplica a regra do anel no banco inteiro
radar situacoes             # recalcula a fase (o tempo passa sozinho)
radar carga-inicial --dias 90   # historico, uma vez so; --sim nao pergunta
```

**Ver**

```bash
radar listar                    # so o que esta perto
radar listar --abertas          # so o que da para se inscrever hoje
radar listar --todos            # tudo, inclusive o que e longe
radar listar --favoritos
radar listar --noticias         # o que o filtro achou que nao era concurso
radar listar --relevancia remoto
radar listar --salario-min 5000
radar previsao                  # onde vale ficar de olho agora
```

**Marcar**

```bash
radar favoritar 324             # o id aparece na primeira coluna do listar
radar favoritar 324 --remover
radar salario 324 5200          # grava; sem o valor, limpa
radar eventos 324               # a linha do tempo daquele concurso
```

A **linha do tempo** responde o que o resto do radar nao responde: o resto
mostra como o concurso esta hoje, e `radar eventos` mostra o caminho ate aqui.
Fica gravado quando ele apareceu, cada passo do ciclo de vida, quando a
inscricao abriu e fechou, e cada vez que o edital foi retificado.

Ela vale da primeira coleta em diante. Os concursos que ja estavam no banco
antes da tabela existir aparecem sem evento nenhum - nao ha como saber quando
eles apareceram, e inventar a data seria pior que nao ter.

**Edital e provas**

```bash
radar provas --limite 20    # le os hotsites e baixa edital, prova e gabarito
                            # comeca pelo alvo principal, onde quer que ele esteja
radar provas --abertos      # o edital de quem ainda esta em andamento
radar baixar-provas         # reconstroi o acervo a partir do manifesto
radar elegibilidade         # le o edital: escolaridade, idade, CNH, teste fisico
radar retificacoes          # acusa edital que mudou (--avisar manda no Telegram)
```

**Questoes e estudo**

```bash
radar questoes              # separa os cadernos do acervo em questoes
radar questoes --refazer    # passa o parser novo por cima do acervo inteiro
radar padrao                # o que a banca mais cobra, por materia
radar padrao --cargo Guarda
radar repetidas             # as questoes que a banca mais reaproveita
radar parecidas "Guarda Municipal" --banca FEPESE
radar parecidas "Policial Penal"   # acha o cargo pelo nome antigo tambem
radar assuntos              # SIMULA o assunto fino; --valendo gasta de verdade
radar assuntos --so-alvo    # so as minhas provas, escolhendo na lista do edital
radar cobertura             # quantas questoes ja tem assunto, por materia
```

**Avisos e calendario**

```bash
radar avisar                # favoritos que mudaram, e depois concursos novos
radar avisar --sem-favoritos   # so os concursos novos
radar testar-telegram       # uma mensagem de teste, nao mexe no banco
radar calendario            # grava radar.ics
radar sincronizar           # troca com o GitHub: pull, importar, exportar, push
radar auditar               # confere banco x PDFs e escreve docs/auditoria.md
```

`radar avisar` e o **unico** lugar que manda mensagem, e quem o chama todo dia
e o robo do GitHub. Ele avisa nesta ordem: primeiro o que mudou nos concursos
que voce segue, depois os que apareceram — se o teto do dia cortar alguma
coisa, que corte a descoberta.

`radar questoes`, `radar padrao`, `radar repetidas` e `radar parecidas` nao vao
a internet: trabalham nos PDFs que `radar provas` ja baixou.

## Configurando

### Os aneis, em `config/regioes.yml`

Os tres aneis de distancia, e a grafia canonica de cada municipio. O municipio
e sempre gravado na grafia deste arquivo — cada fonte escreve de um jeito, e
sem isso qualquer conta por municipio sai errada.

### Os cargos que eu quero, em `config/alvo.yml`

Tres marcas, e elas nao valem a mesma coisa:

- **`principal`** e a Policia Penal SC. Para ela o cargo manda, entao a marca
  **fura o filtro de distancia e o teto de 10 avisos**, e vale ate para
  `noticia` - que normalmente nunca vira mensagem. No Telegram o aviso abre
  com 🚨. Sao os tres nomes que a secretaria ja teve (SJC em 2013, SAP em
  2019, SEJURI hoje), os termos do cargo ("policia penal", "policial penal",
  "agente penitenciario") e a banca historica, a FEPESE.
- **`principal_fora`** e o mesmo cargo em outro estado, ou sem prova de qual.
  **Avisa igual** - sirene, sem distancia, sem teto - porque outra banca
  abrindo Policia Penal e noticia que eu quero na hora. E **so avisa**: o
  estudo (Meu foco, incidencia, treino, acervo) le `principal` sozinho,
  porque fora de SC e outra banca, outro conteudo e outra lei estadual.
- **`secundario`** e o resto da lista: Guarda Municipal, Policia Civil,
  Oficial de Bombeiros, Policia Penal Federal, Bombeiro Militar e Policia
  Cientifica, nessa ordem. Ganha a marca e mais nada: as regras de aviso
  continuam as de sempre.

Um bloco secundario pode ainda trazer uma lista **`de_olho`** de cidades. Hoje
so a Guarda Municipal tem, com Florianopolis e Balneario Camboriu: nessas duas
o aviso **fura o teto** (abre com 👀) e a cidade ganha um cartao "De olho" no
Meu foco, com a situacao de cada uma. O cargo continua secundario - isso nao
entra no estudo, que e do cargo que eu vou prestar.

Tres cuidados que o arquivo toma, e que valem a leitura antes de mexer nele:

- a comparacao e por **palavra inteira**. Sem isso a sigla "SAP" casa dentro
  de Sapezal, Sapiranga, Massape e SAPE/SC, que estao todos na coleta;
- os **`orgaos`** exigem **prova de que o item e de SC**. Sem UF, so uma
  palavra exclusiva serve ("santa catarina", "sejuri", "sap/sc") - Sao Paulo
  tambem tem uma secretaria SAP. Quem relaxou essa trava foram so os
  `termos`, e o que eles ganham e a marca `principal_fora`, nao a `principal`;
- a **banca nunca marca sozinha**. A FEPESE faz dezenas de concursos de
  prefeitura por ano; ela so entra no motivo da marca.

Mexeu no arquivo? `radar reclassificar` recalcula o banco inteiro e lista o
que bateu, sem ir a internet.

### O link para a lei, em `config/leis.yml`

Liga cada materia e assunto de Direito do edital ao **texto oficial**, e e de
onde sai o "ler a lei" do Onde estudar primeiro.

```yaml
materias:
  - materia: Direito Penal              # como o quadro do edital escreve
    lei: Codigo Penal (Decreto-Lei 2.848/1940)
    url: https://www.planalto.gov.br/ccivil_03/decreto-lei/del2848compilado.htm

  - materia: Legislacao Estadual        # sem url: nao ha um texto que cubra
    assuntos:
      - quando: "6.745"                 # marca procurada no nome do assunto
        lei: Lei 6.745/1985 - Estatuto do Servidor Publico do Estado de SC
        url: https://leis.alesc.sc.gov.br/ato-normativo/7963
```

Quatro regras:

1. **duas fontes, e so elas.** Planalto para lei federal e Constituicao, ALESC
   para lei estadual de SC. Ha teste guardando isso: um link para site de
   resumo de lei entraria sem ninguem perceber, e resumo de lei nao e lei;
2. **`quando` e procurado DENTRO do nome do assunto**, e nao comparado com ele.
   O assunto do edital e comprido - um deles tem 126 caracteres - e a proxima
   edicao reescreve a frase;
3. **assunto sem marca cai no link da materia.** "Crimes contra a Administracao
   Publica" nao e uma lei: e um titulo do Codigo Penal;
4. **o que nao tem lei fica sem link.** As Regras de Mandela sao documento da
   ONU, nao lei brasileira; teoria geral dos direitos humanos e doutrina. Link
   errado e pior que link nenhum.

Um campo `nota` opcional aparece na tela junto do link, para o que eu preciso
saber antes de abrir - a Lei 4.898/1965 que o edital de 2019 cobra, por
exemplo, foi revogada pela Lei 13.869/2019.

**O radar nao baixa nem guarda o texto de lei nenhuma.** Lei muda, e o unico
lugar em que a versao vigente esta certa e a fonte.

### O perfil, em `config/perfil.yml`

```yaml
ano_de_nascimento:
escolaridade: superior
formacao: Sistemas de Informacao
cnh: []
```

Com ele o radar deixa de so mostrar o que o edital pede e passa a responder
**se eu sirvo para a vaga**, com o motivo junto:

```
Vagas de nivel superior, medio, fundamental; exige CNH categoria A;
tem teste fisico | tenho superior, que atende as vagas de superior,
medio, fundamental
```

Tres regras:

1. **campo em branco quer dizer "nao sei", e nao "nao tenho".** Sem o ano de
   nascimento, um edital com idade maxima nao vira inelegivel: vira elegivel
   com aviso;
2. **escolaridade e piso, e nao teto.** Quem tem superior atende vaga de medio
   e de fundamental;
3. **CNH avisa, mas nunca barra.** O edital pede CNH em algumas vagas e nao em
   outras, e o radar guarda um registro por concurso.

So dois fatos tornam um concurso `inelegivel`: idade acima do teto declarado,
ou nenhuma vaga no nivel que eu tenho.

### Avisos no Telegram

O radar manda uma mensagem por concurso novo que interessa, **com o link da
fonte junto**. Configurar, uma vez:

1. No Telegram, fale com o **@BotFather**, mande `/newbot` e escolha um nome.
   Ele responde com um **token**;
2. fale com o **@userinfobot**. Ele responde com o seu **chat_id** numerico;
3. coloque os dois no `.env`:

   ```
   RADAR_TELEGRAM_TOKEN=...
   RADAR_TELEGRAM_CHAT_ID=...
   ```

4. mande `/start` para o **seu** bot. O Telegram nao deixa um bot puxar
   conversa: enquanto voce nao falar com ele, ele nao pode te responder;
5. confira com `radar testar-telegram`.

**No GitHub Actions**, os mesmos dois valores vao em *Settings > Secrets and
variables > Actions*, com os mesmos nomes. O `.env` esta no `.gitignore` e
nunca sobe para o repositorio.

**Quem vira mensagem:** `nucleo`, `proximo`, `estadual` e `indefinida`. Os indefinidos
entram de proposito — sao os federais e os sem UF, que ainda podem aplicar
prova em Florianopolis. Melhor dois avisos a toa do que perder o unico que
interessava. `remoto` e `noticia` nunca viram mensagem.

Cada concurso e avisado **uma vez so**, e o **teto e de 10 mensagens por
coleta**. O teto nao e economia, e protecao: se uma regra de classificacao
quebrar, o estrago fica em 10 mensagens mais um alerta, em vez de 200
notificacoes as 6h da manha.

### A chave da Anthropic

`radar assuntos` e a **unica parte do radar que custa dinheiro**, e **simula por
padrao**: sem `--valendo` nao gasta nada. A chave vai em `RADAR_ANTHROPIC_KEY`,
no `.env`, como o token do Telegram — nunca no codigo. O passo a passo esta em
**COMO_LIGAR_A_IA.txt**.

> **Correcao de 25/09/2026.** Ate esta data o README, os commits e os docs
> falavam de 93 assuntos "pagos" em `data/assuntos.json`. **Eles nunca foram
> pagos, e nunca houve chamada a API** - a chave nao existe no `.env` nem no
> ambiente. Os rotulos tinham sido escritos durante uma sessao de trabalho e
> exportados como se fossem saida do modelo. O arquivo foi **zerado** e a
> coluna `assunto` das 98 linhas do banco foi limpa. O motivo esta em
> [docs/decisoes.md](docs/decisoes.md). Hoje **nenhuma** questao de Direito
> tem assunto, e nada aqui foi cobrado ate agora.

Com `--so-alvo` sao duas mudancas, e as duas importam:

- entram so as questoes das provas do **meu cargo no meu estado** — 99 em vez
  de 2.802, estimados US$ 0,03 em vez de US$ 0,40. Assunto fino de prova de
  Merendeira e da mesma banca e nao me serve de nada;
- a IA **escolhe** o assunto dentro do **conteudo programatico do edital** (85
  assuntos em 11 materias, lidos do ANEXO 1 de 2019) em vez de inventar um
  nome. O que vier fora da lista e descartado, e nao gravado como assunto novo.

Portugues e Raciocinio Logico **nao entram na conta paga**: eles continuam
saindo do catalogo de palavras-chave, de graca, e ja cobrem 83% e 44% das
minhas questoes.

O que for pago vai para **`data/assuntos.json`**, que e versionado e entra no
`exportar`, no `importar` e no `sincronizar` como os outros dois. A chave e a
impressao do enunciado: refazer o banco, ou trocar de computador, nao faz eu
pagar de novo pela mesma questao.

**Cada linha desse arquivo diz de onde veio**: `modelo` e `classificado_em`.
Linha sem os dois e **recusada** na importacao, e o `radar importar` conta
quantas recusou em voz alta. O `gravar_assuntos` tambem exige o modelo e
levanta erro sem ele. As duas portas existem por causa de 24/09: a primeira
versao nao tinha campo nenhum de procedencia, e por isso rotulo escrito a mao
e rotulo pago eram indistinguiveis depois.

`radar cobertura` mostra quanto de cada materia ja tem assunto, com a coluna
dizendo de onde ele veio — catalogo (de graca), edital (custa), ou "fora do
programa de hoje", que e a materia que a edicao de 2013 cobrava e a de 2019
nao cobra mais.

### Questoes geradas: treinar com o que a IA escreve

`radar gerar` e a **segunda parte que custa dinheiro**, e como a outra **simula
por padrao**: sem `--valendo` nao gasta nada.

```bash
radar gerar --quantas 5                      # simula: mostra o custo e o pedido
radar gerar --quantas 5 --materia "Direito Penal"
radar gerar --quantas 5 --valendo            # so aqui gasta
```

**A regra que vale para tudo nesta parte: questao gerada serve para TREINAR,
nunca para MEDIR o que a banca cobra.** Ela nao entra na incidencia, no peso
das materias, na aba Macetes nem nas questoes esperadas do "Onde estudar
primeiro". Quem garante isso nao e um filtro que alguem precise lembrar: e a
tabela `questoes_geradas`, separada da `questoes`. O meu acerto aparece sempre
em **dois numeros**, o das reais e o das geradas, e nunca somado.

**Dois modos, e o padrao nao e criar do zero:**

- **variacao** (padrao) parte de uma questao **real** da FEPESE com o gabarito
  definitivo conferido e pede 3 variacoes — muda cenario e numeros, mantem a
  regra juridica. O estilo e o da banca de verdade e a resposta esta ancorada
  num gabarito que a propria banca publicou;
- **do zero** so entra quando nao existe questao real na materia. Ai as
  questoes reais entram so como exemplo de **estilo**, sem gabarito junto.

A base e so a prova do **meu cargo, no meu estado**, e questao anulada fica de
fora. Cada questao gerada guarda o modo, a questao real de origem, a materia, o
assunto, **o artigo da lei** em que se apoia e qual modelo a escreveu — e o
artigo aparece na tela com o link do `config/leis.yml`, para eu conferir em 10
segundos.

**O modelo e `claude-sonnet-5`**, e nao o mais barato: no `radar assuntos` o
erro do modelo fraco e um rotulo torto, aqui seria um gabarito errado que eu
estudaria como certo. US$ 2,00 por milhao de tokens de entrada e US$ 10,00 de
saida. Medido na simulacao: **5 questoes custam US$ 0,06** (~R$ 0,31). O teto
padrao e **US$ 0,90** (uns R$ 5), conferido antes de cada chamada contra o
gasto real que a API informou — e por execucao, nao por mes.

O que foi gerado vai para **`data/questoes_geradas.json`**, versionado e
chaveado pela impressao do enunciado, como o `assuntos.json`: refazer o banco
nao faz eu pagar de novo pela mesma questao. O `rejeitada` vai junto porque ele
e meu, e nao da IA.

**A simulacao mostra o pedido, e nao questao inventada.** O texto da questao so
existe depois da chamada — entao o que `--simular` imprime e a instrucao e o
pedido exatos que iriam para a API. Mostrar "exemplos" de questao gerada sem
ter chamado nada seria apresentar texto inventado como saida do modelo.

**O texto da lei nao vai junto no pedido, e ha um motivo.** A ideia era baixar
o artigo do Planalto para reduzir o risco de gabarito errado. O
`planalto.gov.br/robots.txt` responde 404 — ou seja, o robots nao proibe nada.
O impedimento e outro: o servidor **derruba a conexao para qualquer User-Agent
que nao seja de navegador** (testado alternando: o UA honesto do projeto e
`curl/8.4.0` sao recusados; um UA de Chrome responde 200). Baixar exigiria o
radar se disfarcar, e o CLAUDE.md manda identificar-se no User-Agent. Entao nao
se baixa — e o radar continua so apontando o link da lei.

#### Na tela

Em **Estudar** há uma terceira aba, ao lado de Macetes e Simulado: **Gerar
questões**. Escolho a matéria e quantas quero, e ela responde em dois passos —
**"Ver o custo disto"** recarrega a página com o preço daquela escolha, e só
então aparece o botão que gasta, com o valor escrito nele. São dois passos de
propósito: não existe botão de gastar com preço de uma escolha anterior.

Ao gerar, caio direto no **mesmo simulado de sempre** — não há uma segunda tela
de responder questão. A rodada leva só o que acabou de nascer.

Cada questão gerada chega com **selo, acima do enunciado**: que foi criada por
IA, de qual questão real ela é variação (com banca, ano e cargo, e dizendo que
*aquela* tem gabarito oficial e esta não), e em que **artigo** ela diz se
apoiar — com o link "ler a lei" do `config/leis.yml` ao lado. Quando a IA não
soube dizer o artigo, a tela diz isso, em vez de calar.

No selo fica também **"Essa questão está errada"**. Um clique e ela sai do
sorteio para sempre; as respostas dela saem junto da conta do meu acerto, e a
rodada em andamento anda para a próxima. A questão em si não é apagada: o erro
guardado é o que me diz depois se um assunto dá errado toda vez — e aí o
problema não é a questão, é o pedido.

**O acerto aparece em dois números, nunca somado.** Na tela do Simulado são
duas tabelas separadas, "Como você vai até agora" (reais) e "Nas questões
geradas"; na aba Gerar questões, uma tabela com as duas colunas lado a lado. Na
revisão do fim da rodada, cada questão gerada leva a marca "criada por IA" e o
artigo que ela alega.

### O gabarito que vale e o definitivo

O caderno de prova da FEPESE marca a alternativa certa dentro do proprio PDF, e
e de la que o acervo tira o gabarito. Mas esse arquivo e publicado no dia
seguinte a prova, **antes dos recursos**: ele carrega o gabarito **provisorio**.

No concurso de 2019 da Policia Penal SC o definitivo **anulou 5 questoes**
(11, 22, 33, 63 e 100) e **trocou a letra de outras 4** (66, 68, 82 e 87).
Treinar pelo caderno era marcar como erro quatro respostas certas e perseguir
cinco questoes que nao tem resposta.

O definitivo nao esta na pagina de provas do hotsite — ele e anunciado na lista
de avisos da **capa**, e por isso `radar provas` le tres paginas por concurso
em vez de duas. Como ele sai depois do caderno, existe o **`--revisitar`**:

```bash
radar provas --revisitar    # le de novo hotsite que ja esta no acervo
radar questoes --refazer    # aplica o gabarito definitivo por cima
```

A questao anulada fica **marcada e fora de tudo**: nao entra no treino (ficou
sem resposta certa), nem na incidencia, nem na cobertura, nem na fila da
classificacao paga.

### O calendario no celular

`radar calendario` grava o `radar.ics`; na web, o link **Calendario** abre a
pagina que explica e entrega o arquivo, com o passo a passo de como importar no
celular, no Google Agenda e no Outlook.

Entra o que e favorito e o que esta perto de casa, com prazo conhecido e ainda
em pe. Quando ha data de prova, ela vira um segundo compromisso. O lembrete
toca **dois dias antes** — um dia antes ja e tarde para juntar documento e
pagar boleto.

## Automacao

`.github/workflows/coleta.yml` roda a coleta todo dia as 6h de Florianopolis,
no GitHub Actions, e commita o resultado. Tambem da para disparar na mao pela
aba Actions.

Actions e gratuito em repositorio privado ate 2.000 minutos por mes; a coleta
gasta uns 3 minutos por dia. Sua maquina nao roda nada: ela so e usada quando
voce abre a web ou pede para baixar prova.

## Como o projeto esta organizado

```
src/radar/
├── config.py       le ambiente (.env). Nenhum efeito colateral no import.
├── models.py       tabelas concursos, eventos, questoes, questoes_geradas,
│                   simulados e respostas
├── db.py           engine preguicoso + context manager de sessao
├── servico/        as regras, um arquivo por assunto:
│   ├── __init__.py   consulta, favoritos, detalhe, elegibilidade,
│   │                 retificacao e calendario - e a fachada dos demais
│   ├── coleta.py     roda as fontes, grava com upsert, classifica
│   ├── avisos.py     quem vira mensagem no Telegram, e quando
│   ├── provas.py     acervo, leitura dos cadernos, padrao da banca
│   ├── simulado.py   monta a rodada, responde, mede o acerto
│   ├── geradas.py    as questoes que a IA escreveu: plano, guarda, sorteio
│   ├── previsao.py   quando o municipio costuma abrir de novo
│   └── comum.py      o pouco que mais de um assunto usa
├── regioes.py      le config/regioes.yml: anel e grafia canonica do municipio
├── alvo.py         le config/alvo.yml: e o cargo que eu quero?
├── gabarito.py     o gabarito definitivo, e as questoes anuladas
├── eventos.py      a linha do tempo: o que mudou em cada concurso, e quando
├── foco.py         a situacao do alvo principal, para a pagina inicial
├── onde_estudar.py por qual assunto comecar: quanto ele vale, quanto eu erro
├── leis.py         le config/leis.yml: onde ler o texto oficial da lei
├── acompanhando.py os favoritos: linha do tempo, proxima acao, fila de aviso
├── edital_materias.py  o quadro de distribuicao de questoes do edital
├── edital_programa.py  o conteudo programatico: o que cai em cada materia
├── classificador.py  tipo, municipio, salario, relevancia e alvo, pelo titulo
├── avisos.py       monta e manda a mensagem no Telegram
├── detalhes.py     le a pagina do post: prazo, banca e municipio de lotacao
├── elegibilidade.py  le o edital: escolaridade, idade, CNH e teste fisico
├── perfil.py       le config/perfil.yml e cruza com o que o edital exige
├── provas.py       acervo: acha, baixa e cataloga edital, prova e gabarito
├── provas_ieses.py como achar os documentos no hotsite da IESES
├── questoes.py     separa o caderno da FEPESE em questoes
├── questoes_ieses.py  o mesmo para a IESES: 4 alternativas, gabarito a parte
├── edital_ieses.py de que materia e cada questao, pelos anexos II e IV
├── assuntos.py     assunto fino pela API da Claude (a primeira parte paga)
├── gerador.py      escreve questao nova pela API, para treinar (a segunda)
├── substituta.py   qual prova do acervo mais se parece com o cargo que quero
├── macetes.py      o costume da banca: forma de perguntar, questao repetida,
│                   palavra frequente, letra do gabarito
├── calendario.py   monta o .ics dos prazos (iCalendar, sem dependencia)
├── acervo.py       exporta e importa o banco em JSON (inclusive os simulados)
├── auditoria.py    confere o banco contra edital e gabarito definitivo
├── util.py         fuso e formatacao de data
├── cli.py          comandos typer. `atualizar` roda a rotina inteira
├── collectors/
│   ├── base.py                  Coletor + ItemColetado; robots.txt,
│   │                            User-Agent e atraso entre requisicoes
│   ├── concursos_no_brasil.py   fonte 1: feed RSS, com paginacao
│   ├── fepese.py                fonte 2: API REST do WordPress da FEPESE
│   └── ieses.py                 fonte 3: API JSON da listagem de projetos
└── web/          FastAPI + Jinja2
    ├── app.py                    rotas e o contexto de cada tela
    └── templates/_topo.html      a barra de navegacao, igual em toda pagina

config/
├── regioes.yml     os tres aneis de distancia
├── alvo.yml        os cargos que eu quero, em ordem
├── leis.yml        onde ler a lei de cada materia e assunto de Direito
└── perfil.yml      meus dados, para a elegibilidade
```

A ideia central: **cada fonte e um arquivo isolado em `collectors/`**. O resto
do sistema nao sabe de onde veio o dado.

Banco: SQLite em `data/radar.db`, Postgres opcional via `RADAR_DATABASE_URL`.
Um concurso e identificado pela **url**: se a mesma url aparecer de novo numa
coleta seguinte, o registro e **atualizado**, nao duplicado. O ciclo de vida
fica em `situacao`:

```
prevista → autorizado → banca_definida → edital_publicado
→ inscricoes_abertas → encerrado
```

### Adicionando uma fonte nova

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

Depois inclua em `COLETORES`, dentro de `servico/coleta.py`.

O `self.get()` herdado ja cuida de tres coisas: checa o `robots.txt` do site,
manda o `User-Agent` do projeto e espera o intervalo configurado entre uma
requisicao e outra ao mesmo host.

### Quem entra no acervo

Nesta ordem:

1. **o alvo principal de `config/alvo.yml`**, esteja ele onde estiver. Ele
   nao passa pelo filtro de distancia: e concurso estadual, e eu presto onde
   a prova for. Foi o que trouxe para o acervo as duas unicas provas de Agente
   Penitenciario que SC ja teve - 2013 (70 questoes) e 2019 (100);
2. concurso **encerrado** perto de casa (`nucleo` e `proximo`), que e o padrao
   da banca na minha regiao;
3. o que ainda depende de ler o edital (`indefinida`).

A ordem importa porque o limite de requisicoes e curto: se so couber um
concurso na rodada, tem que ser o que eu vou prestar. Use `--abertos` para
pegar tambem o edital de quem ainda esta em andamento.

### Os PDFs nao ficam no git

Os PDFs vao para `data/provas/`, que esta no `.gitignore`. O que e versionado e
o **manifesto** (`data/provas.json`): link de origem, banca, orgao, municipio,
cargo, ano, tipo e o `sha256` de cada arquivo. Com ele, `radar baixar-provas`
reconstroi o acervo inteiro em qualquer maquina.

### Testes

```bash
pytest -q
```

Os testes usam arquivos de exemplo em `tests/fixtures/` e um SQLite temporario.
**Nenhum deles vai a internet**, entao passam offline e rodam em menos de 1s.

## Sobre as fontes

Nao existe API oficial unica de concursos no Brasil. As tres que o radar usa:

| fonte | o que traz | como |
|---|---|---|
| Concursos no Brasil | concurso de todo o pais, inclusive municipal de SC | feed RSS |
| FEPESE | os concursos da banca que mais atua em SC | API REST do WordPress |
| IESES | a outra banca catarinense, de 2021 para ca | API JSON |

Regras da casa para as proximas:

- respeitar o `robots.txt` **sem excecao** — e por isso que o DOM/SC, o DOU e o
  Querido Diario estao de fora;
- nao raspar site cujos termos proibem (Qconcursos, por exemplo) nem conteudo
  atras de login ou paywall;
- manter o intervalo entre requisicoes (`RADAR_REQUEST_DELAY`);
- identificar-se no `User-Agent`;
- guardar sempre o link original — o sistema e um indice, nao um substituto.

O que ja foi avaliado e ficou de fora, com o motivo de cada um, esta no
[historico](docs/historico.md#fase-17-fontes-federais-e-diarios-o-que-foi-avaliado-e-ficou-de-fora).

## Nota sobre dependencias

As versoes estao presas no `pyproject.toml`, inclusive o `click` — ele e
dependencia indireta do `typer` e uma versao nova dele ja quebrou a CLI aqui.
Se a coleta diaria comecar a falhar por instalacao, o proximo passo e gerar um
lock com `pip freeze`.
