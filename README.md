# Radar de Concursos

Sistema pessoal para acompanhar concursos publicos que valem a pena para mim:
coleta os que abrem, guarda num banco, le o edital, baixa as provas antigas e
deixa treinar em cima delas.

O alvo principal e **Policia Penal SC**, e depois dele as outras carreiras de
seguranca publica. Para o resto, o filtro que importa e **onde a prova e
aplicada** — Grande Florianopolis e arredores.

**Estado (05/10/2026):** o radar (fases 1 a 15), a especificacao e o pedido de
evolucao (etapas 1A a 8) prontos, e o Ciclo 1 de estudo rodando desde 28/09.
Tres fontes coletando, 8.462 questoes no acervo (as 170 do alvo classificadas
e conferidas), simulado, geracao de questoes com escopo fechado, ficha e
resumo de cada tema (com "caiu ou nao caiu" prova a prova), a tela Hoje e as
analises. O que falta esta no "Estado
atual" do [CLAUDE.md](CLAUDE.md) e em [docs/pendencias.md](docs/pendencias.md).

Os outros documentos do projeto - a lista completa, e qual ler primeiro, esta
no **[docs/indice.md](docs/indice.md)**:

- **[CLAUDE.md](CLAUDE.md)** — contexto permanente, para trabalhar no codigo;
- **[docs/novo.md](docs/novo.md)** — o pedido de evolucao e as regras que nao
  podem ser quebradas; **[docs/roteiro.md](docs/roteiro.md)** — o plano dele,
  etapa por etapa; **[docs/progresso.md](docs/progresso.md)** — como cada etapa
  andou: situacao, testes e criterio de conclusao;
- **[docs/decisoes.md](docs/decisoes.md)** — as decisoes ja tomadas, com o motivo;
- **[docs/pendencias.md](docs/pendencias.md)** — o que falta, o que esta
  quebrado e o que ficou combinado;
- **[docs/historico.md](docs/historico.md)** — como cada fase foi feita, com os
  numeros medidos;
- **[docs/auditoria_final.md](docs/auditoria_final.md)** e
  **[docs/leis_alteradas.md](docs/leis_alteradas.md)** — a conferencia contra a
  §23 do pedido, e a das leis que mudaram depois das provas;
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
JSON do radar em `data/`; o resto da pasta fica como esta.

**A pasta nao precisa estar limpa** (desde 03/10/2026). O "pull" e um `git
fetch` seguido de um `git merge --ff-only`: o GitHub entra avancando so para a
frente, e o codigo de uma etapa pela metade fica onde esta - a coleta do robo
mexe so em `data/concursos.json` e `data/eventos.json`. O commit leva so os
JSON do radar que existem, mesmo com outra coisa no stage. Ele para, e diz
por que, em dois casos: quando o que chega do GitHub cai num arquivo que esta
mudado aqui sem commit, e quando ha commit seu que ainda nao subiu ao mesmo
tempo que um do robo - ai so o rebase junta as duas historias, e ele so roda
com a pasta limpa (se der conflito, ele desfaz e a pasta fica como estava).

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
radar web --rede                # abre tambem no celular, na mesma wi-fi
```

### Abrir no celular

O radar roda no PC; o celular so abre a pagina, pelo Wi-Fi de casa. Uma vez,
no Windows:

1. **Rede privada.** Configuracoes → Rede e Internet → Wi-Fi → a sua rede →
   *Tipo de perfil de rede*: **Privada**. Em rede "Publica" o Windows fecha a
   porta para o celular.
2. **Subir com `--rede`:**

   ```bash
   radar web --rede
   ```

   Na primeira vez o Windows pergunta se o Python pode usar a rede: marque
   **Redes privadas** e clique em **Permitir**. O radar mostra o endereco:

   ```
   Abra no celular (mesmo Wi-Fi): http://192.168.0.15:8000/hoje
   ```

   Se ele disser que nao achou o IP, rode `ipconfig` e use o "Endereco IPv4"
   do adaptador Wi-Fi.
3. **No celular**, conectado ao mesmo Wi-Fi, abra esse endereco. Vale salvar
   na tela inicial.
4. *(opcional)* **Fixar o IP do PC** no roteador (reserva de DHCP, "DHCP
   reservation"), para o endereco nao mudar depois de reiniciar. O caminho
   muda de roteador para roteador; costuma ficar em LAN → DHCP.
5. **Se nao abrir**, crie a regra de firewall para a porta, so no perfil
   Privado. No PowerShell **como administrador** (troque 8000 se usar outra
   porta):

   ```powershell
   New-NetFirewallRule -DisplayName "Radar de Concursos (porta 8000)" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow -Profile Private
   ```

   Para desfazer: `Remove-NetFirewallRule -DisplayName "Radar de Concursos (porta 8000)"`.

Os limites:

- o PC precisa estar **ligado, com o `radar web --rede` rodando**;
- so funciona **no Wi-Fi de casa** - fora dela, o celular nao enxerga o PC;
- no celular **nao ha notificacao do cronometro**: o navegador so libera
  notificacao em https (ou no proprio PC, pelo localhost). Fica o aviso na
  tela e o som, com a pagina aberta;
- o radar **nao tem senha**: qualquer pessoa conectada ao seu Wi-Fi consegue
  abrir a pagina (e marcar coisas nela). Sem o `--rede`, ele so escuta no
  proprio PC.

### Tema claro e escuro

O radar abre no **escuro**. O botao **☀️/🌙** no canto direito da barra troca
para o claro (e de volta), e a escolha fica guardada no navegador (um cookie),
valendo para todas as paginas ate eu trocar de novo. O tema do Windows nao
manda. Para comparar sem mudar a escolha, `?cor=claro` ou `?cor=escuro` no
fim do endereco vale so para aquela pagina.

### A pagina web, aba por aba

Sete destinos na barra do topo, cada um com as suas paginas (desde a Etapa
7B, 03/10/2026):

| aba | o que tem la |
|---|---|
| **📅 Hoje** | o cronograma do dia, e onde marco como foi ([Cronograma](#cronograma)); dentro dela, **Semanas**, **Fichas** e o **Caderno de erros** |
| **🎯 Meu foco** | a home: o alvo, o que estudar agora e o que revisar |
| **📚 Estudar** | **Simulado** (questoes das provas do acervo) e **Gerar questoes** (🟣, so treino) |
| **🧠 Revisao** | o **Caderno de erros** (a regra certa e a revisao 1-7-30) e os **Macetes** (o costume da banca, por contagem) |
| **📊 Analises** | **Edital** (o edital contra as provas e onde estudar primeiro), **Minhas materias** (o progresso, a meta e a projecao), **Meu desempenho**, **Incidencia** e **Conferencia** |
| **🏛 Concursos** | **Todos** (a lista, com busca, atalhos e filtros), **Acompanhando** (um bloco por favorito), **Calendario** (o `.ics` dos prazos) e **Previsao** (onde vale ficar de olho agora) |
| **⚙ Mais** | fontes e evidencias, a auditoria e o ultimo backup |

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

As abas estao na tabela de cima. Esta parte descreve as telas que mais pedem
explicacao: **Analises > Edital**, **Acompanhando** e **Concursos**.

**Analises > Edital** (`/analises`) foi a pagina inicial ate a Etapa 7B, com o
nome de "Meu foco" - o nome passou para a home nova. Ela responde "o que esta
acontecendo com o concurso que eu espero?". Ela mostra se ha edital aberto, qual foi o ultimo
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
                         x a fatia que aquele assunto ocupa nas provas do cargo
    pontos a ganhar    = questoes esperadas x (1 - seu acerto no assunto)

O assunto e o no da **arvore de conteudos** em que cada questao foi
classificada (decisao 74): os mesmos numeros de Analises > Incidencia. O seu
acerto aparece nos dois recortes, cada um com o seu numero - o medido no radar
e o anotado das faixas e dos extras, sem consulta -; os dois juntos so decidem
se a amostra basta e a conta dos pontos.

Sao duas colunas porque nenhuma decide sozinha: um assunto de 10 questoes em
que voce acerta 90% vale 1 ponto a recuperar, e um de 4 questoes em que voce
acerta 25% vale 3. O grafico e de barras deitadas, CSS puro, do maior para o
menor, e uma frase curta em cima dele repete em portugues o que a primeira
barra diz em pixel.

Cada linha mostra **em quantas questoes ela se apoia**, uma fatia por
evidencia e nunca somadas: "9 de 22 nas provas do cargo · 52 de 95 no acervo
complementar, com peso 0,25 so na ordem". Sao so duas provas do cargo no
acervo, e duas provas sustentam pouco uma fatia - por isso entra o **acervo
complementar**: as provas da FEPESE **aceitas** no
`data/acervo_complementar.json` (Etapa 3B). Ele nunca entra nas questoes
esperadas nem nos pontos a ganhar (regra inviolavel 1 do novo.md): pesa so na
**ordem**, com o peso do `config/prioridade.yml` - a mesma regra da prioridade
das fichas -, e o assunto que so caiu no complementar aparece como "so no
acervo complementar", sem questao esperada.

Assunto que voce nunca treinou fica com barra **amarela** e entra na ordem so
pelo tamanho (as questoes esperadas, mais o complementar com o seu peso),
dizendo isso na tela: sem acerto medido nao ha pontos a ganhar para calcular,
e zero por cento seria mentira. Cada assunto de Direito
ganha um link **"ler a lei"**, que vai para o Planalto (lei federal e
Constituicao) ou para a ALESC (lei estadual de SC) e sai de `config/leis.yml`.
E so link: o radar nao baixa nem guarda o texto de lei nenhuma.

O botao de treino monta a rodada nesta ordem: primeiro as questoes das
**provas do proprio cargo**; quando elas acabam, as da **mesma banca nas
mesmas materias** em outros concursos - so das provas **aceitas** no
levantamento da Etapa 3B (decisao 75); e so entao repete o que voce ja
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

## Cronograma

O plano de estudo do dia a dia, com horario, materia, assunto e numero de
questoes. O Ciclo 1 vai de 28/09 a 07/11/2026, de segunda a sabado; domingo e
descanso.

### A tela Hoje

`radar web` e abra **Hoje**, o primeiro item da barra.

**A faixa azul do topo** traz a data, "Ciclo 1 — a base · Semana N de 6", e
tres selos: **⚡ Nivel** da semana, **🔥 dias seguidos** sem zerar e **🎯 Meta**
de acertos da prova. A direita, os botoes para o dia anterior, hoje e o
proximo.

**A coluna do lado** (a direita em tela larga, fixa ao rolar; no celular,
logo abaixo da faixa azul):

- **⏱ Cronometro** - veja [O cronometro](#o-cronometro);
- **Agora** - so no dia de hoje: a faixa EM ANDAMENTO, com horario, e o que
  vem depois. Nos outros dias, a que horas o dia comeca;
- **Esta semana** - os 6 dias em pilulas, na cor do que eu marquei (Ideal
  verde, Reduzida azul, Minima amarela, Nao fiz vermelha, sem marcacao
  cinza); a sequencia ("🔥 12 · dias seguidos sem zerar"); a frase da semana
  (quanto falta para subir de nivel, semana garantida, ou "nao sobe mais,
  mas cada dia feito mantem a sequencia"); e o motivo do nivel;
- **Objetivo** - o alvo, a meta da prova e quantos dias faltam para o fim do
  ciclo.

**No meio**, de cima para baixo:

- tres numeros (horas de estudo, questoes do dia, a que horas a noite acaba)
  e o botao **🆘 Ativar Plano B** - veja [O Plano B](#o-plano-b-para-o-dia-que-apertou);
- os tres blocos: **manha**; **noite**, num azul leve; e **depois das 22h**,
  em azul-noite com a etiqueta "🌙 sobreaviso · pode interromper". Uma faixa
  por linha, na cor do tipo, com o detalhe do que estudar, o filtro do
  Qconcursos e o botao **⚖️ Ler no Planalto** (ou **na ALESC**) para a lei.
  A faixa em andamento ganha borda verde e a etiqueta AGORA;
- **Se o dia apertar**: a meta Reduzida e a Minima daquele dia;
- **Como foi o dia**: o formulario onde eu marco a meta, as questoes feitas e
  os acertos. So hoje ou dia passado.

**O circulo de cada faixa.** A direita de cada faixa (menos as pausas) ha um
circulo: clicar marca como feita (circulo verde com ✓, faixa apagada e
riscada) e clicar de novo desmarca. So hoje ou dia passado. Os checks
**sugerem**, nunca marcam: o "Como foi o dia" ganha a linha "Sugestao: Ideal
(11 de 11 faixas)" com a opcao sugerida destacada, e "questoes feitas" vem
com a soma das faixas marcadas enquanto eu nao salvei. A regra: todas as
faixas (fora pausa e bonus) = Ideal; a manha inteira + a faixa de Direito da
noite = Reduzida; alguma faixa de questoes = Minima. Quem salva sou eu.

**A sequencia 🔥** conta os dias do plano seguidos com Ideal, Reduzida ou
Minima, de ontem para tras (hoje entra se ja estiver marcado). Domingo nao
esta no plano e nao quebra; dia sem marcacao ou "Nao fiz" quebra. Com zero, a
tela diz "Comece hoje a sua sequencia".

A home (Meu foco) tem um cartao no topo com o que esta acontecendo agora e o
botao **Abrir o dia**. Antes do ciclo ele diz quando comeca e leva ao
primeiro dia; depois do fim, some.

### A ficha de estudo de cada tema

Toda faixa de um tema que tem ficha - a teoria, a fixacao, a aprendizagem, o
R+7, o R+30 e o Plano B - ganha o botao **📋 Ficha de estudo**. A ficha e a
mesma em todas: o tema e reconhecido pelo titulo da faixa, sem o prefixo
("Fixação: ", "R+7: "...). A aba **Hoje > Fichas** lista os temas de hoje em
diante, com e sem ficha, na ordem do calendario e com a prioridade de cada um
na linha.

A ficha diz, com o selo da origem de cada parte: **por que agora** (o dia do
cronograma e cada fator da prioridade, com o numero), a **fonte** (🟢 a lei do
`config/leis.yml`, ou a fonte sugerida), **o que ler exatamente** e os
artigos-chave do dia, **como pesquisar**, **o que entender** e **o que
memorizar**, as **pegadinhas** (🔵 as das questoes reais, com o numero, e 🟣 as
escritas), **como a FEPESE cobrou** (alvo e complementar em linhas separadas,
com a amostra), as **questoes reais** do escopo, **quantas questoes fazer** (as
faixas do plano e um `radar gerar` por no), os **erros a refazer** e **quando
revisar**. Campo sem dado diz a frase padrao, e nao inventa.

O texto (o que ler, como pesquisar, entender, memorizar e as pegadinhas
escritas) e do Claude Code, marcado 🟣 com a procedencia, e fica em
`data/fichas.json` (versionado). Ele so vale como conferido depois que eu leio:
o botao **Conferi esta ficha** (ou `radar fichas --conferir`) marca a data e nao
apaga a procedencia.

Embaixo do titulo, a propria faixa diz **onde esta na arvore**: o assunto, o
subassunto - ou "não há subassunto na árvore para este tema" - e o elemento
exato (decisao 71). Vem da ficha (🟣) ou, na faixa sem ficha, dos nos que o
plano da para ela (📌): a chave `nos` do `cronograma.yml`, uma lista de
caminhos da arvore conferida no carregamento. O bonus de logica proposicional
e a interpretacao cronometrada usam essa chave.

### As faixas que medem: o diagnostico e o simulado no radar

Os diagnosticos (10/10; eram de 03/10, decisao 105) e o simulado de fechamento (07/11) **medem**, e por isso
nao tem ficha: a faixa diz **"Só questões: não há o que estudar nesta faixa."**
e mostra a **composicao** - de quais assuntos e subassuntos sao as questoes, e
de onde saiu cada numero -, com o botao **Criar a rodada com esta composição**.
A regra e uma so (decisao 67, `src/radar/servico/composicao.py`):

- o total e o do plano; com varias materias (o 07/11), ele se divide pelo
  quadro do edital, com a mesma conta do simulado compilado;
- dentro da materia, o assunto com amostra nas provas do cargo (3 questoes em
  2 provas, do `config/amostra.yml`) entra pela incidencia - com o complementar
  valendo 0,25, como na prioridade -; os sem amostra dividem o resto por igual,
  com a frase "Não há evidência suficiente no acervo para afirmar isso.";
- so questao real da FEPESE, classificada no assunto: das provas do cargo
  primeiro, depois do complementar ACEITO; uma por enunciado, sem anulada, com
  gabarito. Questao de IA nunca entra: ela treina, nao mede;
- assunto sem questao bastante passa o que falta para os outros da materia; se
  a materia inteira nao tiver, falta mesmo, e a faixa diz quanto.

A composicao e deterministica (a mesma faixa da as mesmas questoes) e fica
gravada na rodada. Criada, a rodada nao e recriada: a faixa passa a mostrar a
composicao gravada e o link **Abrir a rodada desta faixa**.

### O sabado: o simulado da semana, a revisao, o R+7 e a comparacao

- **o simulado da semana** continua no Qconcursos, mas sem numero escrito a
  mao: a faixa diz so as materias, e a tela Hoje mostra quantas questoes de
  cada tema ja estudado, com o filtro do tema (decisao 69). A conta e a do
  diagnostico, com o tema no lugar do assunto do edital; no empate, o tema
  mais recente primeiro;
- **a revisao semanal** mostra os temas da semana, os erros anotados no
  caderno por tema, onde mais errou e os artigos-chave dos dias (decisao 70);
- **o R+7 dos diagnosticos** (17/10) lista os erros das rodadas de 10/10 e
  cria uma rodada so com eles - o plano pede 40, para refazer todos (decisao
  105); faixa que pedir menos que os erros divide pelos assuntos com mais
  erro - pelo botao **Criar a rodada com os erros**;
- **a correcao de 07/11** mostra, por materia, o diagnostico de 10/10, o
  fechamento de 07/11 e o acumulado do ciclo sem consulta, lado a lado e sem
  somar, com "Amostra insuficiente" abaixo do minimo da materia.

### No terminal

```bash
radar hoje                              # o dia de hoje
radar hoje --data 2026-10-28            # outro dia
radar hoje --marcar ideal --feitas 25 --acertos 18
radar hoje --marcar minima --data 2026-10-12 --anotacao "feriado"
radar hoje --plano-b 30                 # so mostra o Plano B do dia (30 ou 60)
radar conferir-dias                     # confere os dias gravados contra a regra
                                        # de contagem; so le (Etapa 1D)
radar conferir-dias --aplicar           # corrige o aprovado, com copia antes
```

`--marcar` aceita `ideal`, `reduzida`, `minima` ou `nao_fiz`. Marcar de novo o
mesmo dia corrige, nao duplica. Dia futuro e dia fora do plano sao recusados.
A faixa com ficha ganha o 📋, e o fim da saida lista as fichas do dia com o
`radar fichas --tema ... --data ...` de cada uma.

**O que eu anoto aqui e diario, nao medida.** As questoes feitas e os acertos
sao digitados a mao (quase tudo do Qconcursos) e nao entram em nenhum acerto
do radar: Meu foco, Onde estudar e a home contam so o que eu respondi dentro
dele, questao por questao.

### O Plano B, para o dia que apertou

Na tela Hoje, ao lado dos tres numeros, o botao **🆘 Ativar Plano B** pergunta
quanto tempo eu tenho (30 min ou 1 hora) e troca o dia inteiro por um bloco
so, sem horario: os artigos-chave do tema do dia (o campo `essencial` do
cronograma.yml) e questoes de prova do mesmo tema, com o filtro da faixa de
Direito do dia. Na de 1 hora entram os artigos de apoio e, se sobrar tempo,
um pouco de Portugues. No sabado e refazer as questoes erradas da semana.
Sem Anki, sem pausa. O dia conta como Minima; **↩ Voltar ao plano completo**
desfaz. So vale para hoje ou dia passado.

### O cronometro

Cada faixa (menos a pausa, e tambem as do Plano B) tem um ▶ ao lado do
horario. Ele conta a duracao
cheia da faixa a partir do clique, no cartao **⏱ Cronometro** da coluna do
lado, e quando acaba avisa em tela cheia, com som e notificacao do Windows:
pausa, volta da pausa, ou a proxima faixa. Recarregar a pagina nao perde a
contagem. **🔔 Testar aviso** pede a permissao de notificacao na primeira vez
e dispara um aviso de teste. A notificacao do Windows so funciona abrindo o
radar no proprio PC (`http://localhost:8000`); pelo IP, na rede, ficam a
tela e o som. Se ela nao aparecer, confira a permissao (cadeado na barra de
endereco → Notificacoes → Permitir) e o "Nao perturbe"/Assistente de Foco do
Windows. O som so toca depois de um clique na pagina (regra dos navegadores):
o ▶ e o Testar ja contam como clique.

E um dos dois JavaScript do radar - o outro e o `dobra.js`, que lembra quais
blocos do dia eu deixei recolhidos. Os dois sao so da tela Hoje e os dois sao
dispensaveis: sem eles a tela funciona igual, so sem o cronometro e sem lembrar
a dobra.

### Dobrar os blocos do dia

Cada bloco da aba Hoje - Manha, Noite, "Depois das 22h" e o do Plano B - recolhe
e volta pelo **sinal ▾ / ▴ no canto direito do cabecalho**, do lado dos
horarios. So o sinal dobra: um clique no titulo ou nos horarios nao mexe em
nada. Pelo teclado, Tab ate o cabecalho e Enter.

"Depois das 22h" **nasce fechado**, e fechado ele mostra ali mesmo que o ANKI
esta temporariamente desativado - abrir e acao sua. O que voce deixar recolhido
fica lembrado para a proxima abertura (por bloco, nao por dia).

### O nivel sobe e desce sozinho

A noite tem uma **rampa**: o numero de questoes de Direito e de Portugues
cresce com o nivel, de 1 a 6. O plano e a semana N no nivel N, mas o nivel
que vale sai do que eu marquei na semana anterior, depois que ela fecha:

- **semana boa** (5 dias ou mais na Ideal, nenhum "nao fiz"): sobe 1;
- **semana ruim** (3 dias ou mais abaixo da Ideal): repete. A segunda ruim
  seguida desce 1, nunca abaixo do 1;
- qualquer outra: repete;
- dia sem marcacao conta como abaixo; feriado marcado como minima ou melhor
  conta como Ideal.

O nivel nunca passa do planejado: quem vai bem segue o plano, quem tropeca
repete a carga ate firmar. Os numeros moram em `gatilho` no YAML.

### Editando o `config/cronograma.yml`

E dado, nao codigo: pode editar a mao. O cabecalho do arquivo explica cada
chave. O que importa saber:

- **os horarios nao estao gravados.** Cada faixa tem `duracao` em minutos ou
  `questoes`, e o horario sai da soma a partir do inicio do bloco (`blocos`:
  manha 10:15, noite 18:00, pos22 22:00). Faixa de questoes dura questoes x
  2,5 min (ou o `min_por_questao` dela), arredondado para cima de 5 em 5. Por
  isso mudar um numero de questoes empurra sozinho tudo o que vem depois;
- a faixa com `rampa: direito` ou `rampa: portugues` usa o numero do nivel,
  e nao o `questoes` gravado;
- na meta `reduzida`, escreva `{direito}` no lugar do numero de questoes de
  Direito: a tela preenche com o numero do nivel da semana, o mesmo da faixa
  `rampa: direito` daquele dia;
- `opcional: true` e bonus: aparece, mas nao conta no total do dia;
- domingo nao pode estar no arquivo. Data repetida, tipo desconhecido, rampa
  que nao existe ou faixa sem duracao nem questoes param o comando com a data
  do dia errado na mensagem.

Confira com `radar hoje --data AAAA-MM-DD` depois de editar. O Ciclo 2 entra
trocando este arquivo.

#### Religar o Anki

O Anki esta **desativado** desde 02/10/2026: no topo do
`config/cronograma.yml` esta `anki: desativado`. As 36 faixas `tipo: anki` e os
30 `baralho` continuam no arquivo; desativado, a faixa vira a linha
"ANKI temporariamente desativado" (sem horario, sem circulo, fora do total e da
sugestao de meta) e o chip do baralho some.

Para religar: troque a linha para `anki: ativado` e rode `radar hoje` para
conferir. Nada mais - a faixa volta com o horario dela, o Bonus volta a comecar
depois dela, e os baralhos reaparecem. Dois textos foram reescritos de 02/10 em
diante e nao voltam sozinhos: a lei seca dirigida nao manda mais "transformar
em cartoes do Anki", e o item (3) da revisao semanal virou "releia os
artigos-chave da semana".

#### As materias do edital, e a minha meta

O bloco `materias` e a prova: quantas questoes cada materia tem (numeros do
edital de 2019, o ultimo) e quantas eu quero acertar. A soma das metas e a meta
da prova inteira - hoje **79 de 100**.

```yaml
materias:
- {nome: Língua Portuguesa, questoes: 15, meta: 12}
- {nome: Lei de Execução Penal, questoes: 10, meta: 8}
# ... as outras nove
```

E daqui que sai a comparacao "estou na meta desta materia?", e por isso o
carregamento confere tres coisas: **nome repetido**, **meta maior que as
questoes** da materia, e **materia escrita numa faixa que nao existe nesta
lista** - essa ultima e a que pega erro de digitacao, porque "Direito Penall"
nunca mais somaria em lugar nenhum.

Faixa **sem** materia (pausa, correcao, simulado misto de sabado) nao e
conferida: ela conta no total do dia e em nenhuma materia. Quando a faixa tem
rotulo de materia mas cobre mais de uma - o R+7 que refaz os erros dos
diagnosticos, que sao de Raciocinio Logico e de Portugues -, o nome dela entra
em `materias_mistas` e vale como faixa sem materia.

#### O mapa do ano

O bloco `mapa` e o ano inteiro em seis linhas, e serve para uma coisa so: o
cartao **🗺️ Mapa do ano**, na lateral da tela Hoje, mostrar onde eu estou. O
ciclo de hoje sai destacado com "voce esta aqui", e os que ja acabaram levam
um ✓. No celular, um toque no titulo recolhe a lista.

Ele **nao manda em nada do dia a dia**: quem manda no que acontece hoje
continua sendo `dias`, e o ciclo que esta rodando e o `ciclo`/`inicio`/`fim` do
topo do arquivo.

```yaml
mapa:
- nome: Ciclo 2
  inicio: '2026-11-09'
  fim: '2026-12-19'
  foco: 'O resto do programa: Processo Penal, Legislacao Especial, ...'
- nome: Ciclo 4+
  inicio: '2027-03-01'        # sem `fim`: etapa em aberto ("a partir de")
  foco: Reforco pelos pontos fracos e simulados
- nome: Pos-edital
  quando: quando sair         # sem data: nunca e a etapa de agora
  foco: Ciclo ajustado ao edital novo
```

Tres regras conferidas no carregamento, para eu nao me enganar editando: datas
em ordem, sem sobreposicao (uma etapa comeca **depois** do fim da anterior), e
etapa sem data so no fim da lista. Vao entre duas etapas e permitido - entre o
Ciclo 1 e o 2 ha um domingo, que nao e de nenhum dos dois.

### Acertos na propria faixa, e o estudo extra

Cada faixa de questoes da tela Hoje tem, no lugar do circulo, um formulario
curto: **fiz [15] · acertei [__]** e a caixa **com consulta**.

- **"fiz"** ja vem com as questoes daquela faixa no nivel do dia, e pode ser
  mudado: fiz 25 no lugar de 15 e o mesmo tema, so mais questoes;
- **"acertei" e opcional.** Vazio conta no volume e em acerto nenhum - foi o
  que aconteceu: eu fiz e nao anotei quantas acertei. Contar como zero seria
  mentira;
- **"com consulta"** ja vem MARCADA na faixa de aprendizagem de Direito (o
  detalhe dela diz "PODE consultar a lei") e na fixacao da manha (8 questoes
  logo depois da teoria), e desmarcada nas outras. Quem manda e a chave
  `consulta: true` da faixa no `config/cronograma.yml`; sem ela, so a `rampa:
  direito` vem marcada. Questao com a lei aberta treina, e **fica fora da
  comparacao com a meta**: na prova nao ha lei aberta;
- **0 questoes nao e faixa feita**: se nao fez nenhuma, desmarque;
- faixa feita mostra **"11 de 15 · 73%"** ao lado do titulo, e o formulario
  recolhe num "corrigir os numeros", com um **desmarcar** ao lado.

Os numeros ficam gravados na propria faixa (minutos, questoes, acertos,
consulta, materia e assunto), e nao so a posicao dela no arquivo: quando o
cronograma.yml mudar no Ciclo 2, o historico continua contando o que eu fiz.

O **➕ Estudo extra**, no fim do dia, e para o que eu estudei fora das faixas:
uma hora de lei seca no almoco, 20 questoes na fila do banco. Cada um tem o
que foi (teoria, lei seca, questoes, revisao), a materia, o assunto, os
minutos, as questoes, os acertos e onde foi. **No Radar as questoes ficam
vazias**: cada uma delas ja foi contada uma por uma, e somar aqui contaria o
mesmo acerto duas vezes.

O extra **nao muda a meta** do dia nem a sugestao dela: fazer mais do que o
plano pedia nao transforma um dia reduzido em ideal.

### O total do dia

O "Como foi o dia" **nao tem mais campo de numero**. Ele mostra a soma, feita
sozinha:

```
Fiz hoje: 35 questões · 27 acertos · 8 erros · 3h10 de estudo (2h40 do plano + 30 min extra)
          radar: 80% em 10 · anotado: 76% em 25
```

O que eu escolho continua sendo a **meta** (Ideal, Reduzida, Minima, Nao fiz), e
salvar grava os totais no registro do dia. As tres regras, com o porque em
[docs/decisoes.md](docs/decisoes.md):

| | soma o que |
|---|---|
| **volume** (questoes, horas) | faixas do plano + estudo extra + respostas no radar |
| **acerto** | as tres, com a divisao "radar / anotado" embaixo |
| **meta** | so questao **sem consulta** |

Questao escrita por IA conta no volume e **em acerto nenhum** — ela treina, nao
mede. Com erros no dia, aparece o atalho **📓 anotar os erros**, que abre o
[caderno](#o-caderno-de-erros) ja no dia certo.

A tabela de materias do **Meu foco** continua usando so o que o radar mede,
questao por questao. O **"Onde estudar primeiro"** usa o desempenho por
conteudo, com o medido no radar e o anotado lado a lado (decisao 74).

### Semanas: como fui em cada uma

A aba **Semanas** (`/semanas`, ao lado de Hoje e do Caderno de erros) mostra
uma semana por cartao, agrupadas pelos **ciclos do mapa do ano**. O ciclo de
agora fica aberto; ciclo que terminou fecha num `<details>` com uma linha de
resumo:

```
Ciclo 1: 29 dias completos · 1.420 questões · 72% de acerto ▸
```

Semana que ainda nao comecou nao aparece; a semana corrente aparece marcada
**em andamento** — os numeros dela sao parciais, e dizer isso e mais honesto
que mostra-los como se ela tivesse fechado.

Cada cartao tem as **6 pilulas** dos dias (nas cores do diario, clicaveis) e:

- **dias completos** — a MESMA conta do gatilho, incluindo o feriado cumprido
  na minima. A tela nao pode dizer "4 completos" enquanto o gatilho conta 3;
- **questoes, acertos, erros e % de acerto** (faixas + extras + radar) e,
  embaixo, **"sem consulta: X%"** — o numero que se compara com a meta;
- **horas estudadas** (faixas + extras, sem pausa: o radar nao cronometra
  simulado), **sequencia** no fim da semana, **nivel** com o motivo, **vezes no
  Plano B** e **erros anotados** no caderno;
- **setas de comparacao com a semana anterior** (↑ +35 questoes, ↓ −4% de
  acerto), verdes quando melhora e vermelhas quando piora. Acerto compara ponto
  a ponto, e semana sem acerto medido nao compara acerto nenhum;
- **🏆 na melhor semana do ciclo**: mais dias completos, e no empate mais
  questoes. A semana em andamento nao concorre — ela nao acabou.

No topo do ciclo aberto, um **grafico de barras em CSS puro** (sem JavaScript):
questoes por semana, com o % de acerto em cima de cada barra.

E, em cada semana, a **reflexao**: duas caixas, *O que funcionou* e *O que
ajustar*. Elas existem porque numero nao responde "por que" — a semana em que
eu fiz 300 questoes e acertei 60% tem uma explicacao, e daqui a um mes eu nao
vou lembrar dela. Ficam em `data/notas_semana.json`, com a **segunda-feira**
como chave (numero de semana reinicia no Ciclo 2; data nao reinicia).

A conta inteira mora em `servico/semanas.py`; a tela so mostra.

### Minhas materias: o progresso em cada uma

Em **📊 Analises > Minhas materias** (`/analises/materias`), um cartao por
materia do edital, na ordem do peso na prova. O recorte e o **ciclo de agora**:
misturar o meu acerto de hoje com o da primeira semana responderia outra
pergunta.

No topo, a **projecao**:

```
Se a prova fosse hoje: ~46 acertos de 100 · meta 79
```

Ela soma, materia por materia, o meu acerto **sem consulta** vezes as questoes
que aquela materia tem na prova. Materia com menos de **20 questoes sem
consulta** fica de fora - nao entra como zero nem como a media das outras, que
seriam as duas invencoes possiveis -, e a frase diz quantas ficaram. O selo e o
de **tendencia**: e leitura, nao fato.

Cada cartao tem:

- **questoes feitas** (faixas + extras + radar) e, a parte, **"treino IA: N
  (nao conta)"**;
- **acerto geral** e, embaixo, **"radar: X% em N · anotado: Y% em M"**;
- a **barra "voce x meta"**: o acerto sem consulta contra a meta da materia
  (LEP: 8 de 10 = 80%), verde quando atinge, com o aviso **amostra pequena**
  enquanto nao houver 20 questoes sem consulta;
- um **grafico do acerto sem consulta semana a semana** — SVG desenhado no
  servidor, sem JavaScript. Semana sem questao nao vira ponto: a linha pula
  ela, em vez de fingir um zero que eu nao tirei;
- **horas estudadas** e **"ultima vez: ha N dias"**;
- o **programa andando**: "8 de 12 aulas vistas" (as faixas de estudo da manha
  daquela materia, marcadas / as do plano);
- os **assuntos**, do pior para o melhor acerto, com a quantidade de cada;
- os **erros no caderno** da materia e o motivo mais comum, com link.

Materia que eu ainda nao encostei fica **cinza**: "ainda nao estudei — entra no
Ciclo 2", pelo mapa do ano.

Os nomes casam pela regra que o radar ja usa (`compilado.mesma_materia`): o
caderno de 2013 escreve "Direito Processo Penal" e o edital de 2019 "Direito
Processual Penal", e os dois sao a mesma materia. Os filtros por materia (a
geracao, o simulado, a revisao espacada) e o acerto por materia do
`servico/metricas.py` juntam as duas grafias pelo `sinonimos_de_materia` do
`config/taxonomia.yml` (decisao 97). A conta inteira mora em
`servico/materias.py`; a tela so mostra.

### Backup

O que eu marco no "Como foi o dia" vai para `data/registro_estudo.json` no
`radar exportar` e no `radar sincronizar`, pelo mesmo caminho dos simulados: e a copia que o
`radar.db` nao tem. Na volta (`radar importar`), a chave e a data, e se os
dois lados tem o mesmo dia, vale a anotacao mais recente.

Os checks de cada faixa (o circulo da tela Hoje) e o Plano B escolhido vao,
do mesmo jeito, para `data/estado_do_dia.json`, e na volta vale o
`atualizado_em` mais recente. O cronometro nao vai: ele vive no navegador
(localStorage) e so importa enquanto a faixa esta rodando.

O caderno de erros vai para `data/caderno_erros.json`, o estudo extra para
`data/estudo_extra.json` e a reflexao das semanas para `data/notas_semana.json`,
pelo mesmo caminho. A chave nos dois e o `criado_em`
(e nao a data, porque num dia eu anoto varios), e na volta vale o mais recente.

## O caderno de erros

O que eu errei, com a **regra certa escrita por mim** — e ela e obrigatoria,
porque anotar "errei a 42" nao ensina nada e "o prazo conta da data da prisao,
nao da condenacao" ensina. Fica em **🧠 Revisao > Caderno de erros**, que e
onde a aba abre.

Cada erro guarda o dia do estudo, a materia, o assunto, **por que** eu errei
(nao sabia, confundi, li errado, pegadinha, chutei), de onde veio a questao e,
se eu tiver, o link dela.

**A revisao e a mesma 1-7-30 do resto do radar:**

- anotei um erro, ele volta **amanha**;
- **"Ja sei"** passa para a proxima etapa: 7 dias, depois 30. Acertei a de 30,
  o erro esta aprendido e vai para o arquivo;
- **"Ainda erro"** volta para a etapa 1, e volta amanha. Errar depois de 30
  dias e errar do zero.

A diferenca em relacao a revisao espacada do simulado e a origem: aquela e
calculada das respostas gravadas no radar, e esta sai do meu julgamento - "ja
sei" nao esta escrito em lugar nenhum a nao ser aqui.

No topo da tela, **"O que mais te derruba"**: a contagem por materia e por
motivo, com a frase que eu quero ler ("LEP: 60% dos erros sao pegadinha"). A
porcentagem so aparece com pelo menos 3 erros na materia - de dois erros, um e
50%, e 50% de dois nao e padrao.

**De onde se anota:** na tela Hoje, cada faixa de questoes, revisao, simulado e
diagnostico tem um **📓 Anotar erro** que abre o formulario com a data, a
materia e o assunto daquela faixa ja preenchidos, e volta para a mesma faixa. No
sabado, a faixa "Revisao semanal" leva direto aos **erros da semana**. Na coluna
lateral, um cartao mostra quantos erros vencem hoje (e some quando nao ha nenhum).

**O caderno nao mede nada.** Como o "Como foi o dia", ele e diario: o que esta
nele **nao entra em acerto medido nenhum** do radar (Meu foco, Onde estudar,
home, compilado). La so conta o que eu respondi dentro do radar, questao por
questao.

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
radar questoes --refazer    # passa o parser novo por cima do acervo inteiro;
                            # o texto que muda leva a classificacao junto
radar questoes --textos-base  # so o texto de apoio das questoes de Portugues
                            # do alvo ("considerando o texto 1"), lido por
                            # colunas; mora so no banco (decisao 132)
radar padrao                # o que a banca mais cobra, por materia: um bloco
                            # por evidencia (provas do cargo, complementar
                            # aceito, outras bancas), nunca somados
radar padrao --cargo Guarda
radar repetidas             # as questoes que a banca mais reaproveita
radar parecidas "Guarda Municipal" --banca FEPESE
radar parecidas "Policial Penal"   # acha o cargo pelo nome antigo tambem
radar assuntos              # SIMULA o assunto fino; --valendo gasta de verdade
radar assuntos --so-alvo    # so as minhas provas, escolhendo na lista do edital
radar cobertura             # quantas questoes ja tem assunto, por materia
radar conteudos             # a arvore: materia > assunto > subassunto > elemento
radar conteudos --pendentes # as questoes sem classificacao, alvo prova a prova
radar conteudos --semear    # poe na arvore o que o edital tem e ela nao
radar classificar --pedido  # pede ao Claude Code a classificacao do alvo
radar classificar --pedido --evidencia complementar --materia "Direito Penal"
radar classificar --importar data/resposta_ia.json   # grava o que presta
radar incidencia            # o mapa do alvo por no, com a amostra
radar incidencia --materia "Direito Penal" --padroes
radar complementar          # o que o acervo complementar FEPESE tem, por materia
radar complementar --aplicar  # grava quais provas entram no acervo complementar
radar desempenho            # o MEU acerto por no, com o estado e a amostra
radar desempenho --materia "Lingua Portuguesa" --desde-o-inicio
radar desempenho --revisar  # o que voltou para revisao hoje, e por que
radar fichas                # os temas de hoje em diante: com ficha ou sem, e a prioridade
radar fichas --tema "Art. 5º, caput e incisos I a XVI" --data 2026-10-06
radar fichas --pedido       # pede ao Claude Code as fichas dos temas sem ficha
radar fichas --importar data/resposta_ia.json   # grava as que passam na conferencia
radar fichas --conferir art-5o-caput-e-incisos-i-a-xvi   # marca como lida por mim
radar fichas --pedido --resumos [--id vozes-do-verbo]   # pede os RESUMOS dos temas
radar fichas --pedido --explicacoes   # explicacao das questoes reais do alvo de cada tema
radar fichas --pedido --explicacoes --dos-resumos   # e das do complementar que os resumos citam
radar fichas --conferir-resumo vozes-do-verbo   # marca o resumo como lido por mim
radar fichas --verificar-resumos      # confere cada resumo de novo contra o acervo de hoje
```

**No Windows, o comando inteiro e `.venv\Scripts\radar.exe ...`** (ou
`.\radar.bat ...` no PowerShell): `python -m radar` NAO funciona, porque o
pacote nao tem `__main__.py`. E esta a forma que a faixa, a ficha e a tela de
gerar escrevem nos 3 passos para gerar questao (decisao 114).

**O resumo de cada tema e a aba Fichas (revisao final do estudo, 05/10).** A
aba **Hoje > Fichas** abre no dia, por bloco (Manha, Noite, Depois das 22h),
um cartao por tema, com **"caiu ou nao caiu"** prova a prova (2013 e 2019,
"—" quando a materia nao estava no edital daquele ano; as pendentes e as
questoes pelo artigo gravado, a parte) e a linha das outras provas da FEPESE,
nunca somada; a lista do ciclo inteiro continua em `/fichas?ver=todas`. O
botao **📝 Resumo** - em toda faixa com materia e no cartao - abre o resumo
numa janela por cima da pagina (so CSS): a parte 1 sai na hora, e as outras
(dominar, artigos, como a banca cobra, pegadinhas, o basico quando nao caiu)
sao texto de IA em que cada frase diz a fonte. Na Noite, ele abre ja em "como
a banca cobra". A faixa de questoes diz o no e manda primeiro ao Qconcursos;
as geradas vem depois, com o botao "Treinar no radar" ou os 3 passos para
gerar. Decisoes 108 a 125.

**A ficha de estudo e a prioridade (Etapa 6B).** `radar fichas --tema` mostra
a mesma ficha da tela (ver [A ficha de estudo de cada tema](#a-ficha-de-estudo-de-cada-tema)).
O texto vem pelo caminho sem API: `--pedido` escreve `data/pedido_ia.json` com
os temas do cronograma que ainda nao tem ficha (com as faixas, os
artigos-chave e a arvore da materia), e `--importar` recusa ficha de outro
tema, no que a arvore nao tem, no dentro de outro, campo obrigatorio vazio e
texto com cara de previsao. A ficha que eu ja conferi nao e sobrescrita;
`--pedido --refazer` pede de novo as que eu ainda nao conferi. A prioridade
de cada tema segue o `config/prioridade.yml` (ver
[A prioridade das fichas](#a-prioridade-das-fichas-em-configprioridadeyml)).

**O meu desempenho por conteudo (Etapa 4).** `radar desempenho` e
**Analises > Meu desempenho** respondem como eu vou em cada no da arvore, e nao
so por materia. Duas origens, **nunca somadas num numero so**: *radar* e questao
real respondida aqui dentro, pela ultima resposta de cada, ligada ao no pela
classificacao; *anotado* e o que eu digitei nas faixas e nos extras, no conteudo
que eu escolhi ao anotar - e para isso que os formularios da faixa, do estudo
extra e do caderno de erros tem o seletor de conteudo (o da faixa so aparece
quando o plano da a ela a chave `conteudo`). So o respondido **sem
consulta** conta para o estado; questao escrita por IA nunca entra.

Os cinco estados (Amostra insuficiente, Precisa revisar, Em aprendizado,
Desempenho consistente, Bom desempenho com amostra suficiente) e os minimos de
cada nivel ficam no **`config/amostra.yml`**, secao `desempenho` - mude o numero
la e toda tela muda com ele. Abaixo do minimo o numero aparece e **nao entra em
ordenacao nem em projecao**.

A mesma tela faz o que o ANKI fazia: **quando eu estudei e revisei cada
conteudo** (a ultima vez, a ultima revisao - so faixa de revisao, extra de
revisao ou rodada que revisa no radar; pratica nao conta - e, no assunto, o
acerto semana a semana, com toda resposta e a semana abaixo do minimo em
cinza - a faixa sem a chave `conteudo` conta no que cobre, os `nos` do plano e
a ficha que eu ja conferi, so para a situacao e as datas, nunca para o
acerto), **o que eu ainda nao estudei**, **o que voltou para revisao** (por erro
recente, por desempenho abaixo do corte, ou pelo prazo 1-7-30 vencido - a linha
diz qual; o prazo passa de etapa com o acerto no radar e com a revisao feita,
o R+7 ou o extra de revisao, no vencimento ou depois) e **as questoes a
refazer** (as erradas no radar e as do caderno de erros, em duas listas que
nunca se somam). Nada disso e gravado em tabela: sai
do historico.

**Classificacao e incidencia do alvo (Etapa 3A).** As 170 questoes de 2013 e
2019 sao classificadas pelo Claude Code: `radar classificar --pedido` escreve
`data/pedido_ia.json` (um pedido por materia, com a arvore e as regras), a
resposta volta com `--importar`, e a importacao recusa assunto fora do edital,
tipo fora do `config/taxonomia.yml`, falta de justificativa e questao que nao
estava no pedido. A proposta so vale depois de **conferida** em **Analises >
Conferencia** (confirmar, corrigir ou pendente). A questao e reconhecida pela
chave da questao inteira (enunciado + alternativas): a impressao, so do
enunciado, juntava questoes de enunciado igual.

O **mapa de incidencia** (`radar incidencia` e **Analises > Incidencia**) conta
so o alvo, no por no, com a amostra em toda linha ("8 questoes · 2 provas") e
o que aconteceu ("apareceu nas 2 provas", "apareceu em 1 de 2", "nao apareceu
nas provas analisadas"). Anuladas e pendentes ficam fora da conta e aparecem a
parte. Os padroes de cobranca (forma de perguntar, gabarito, termos, tipo de
questao, pegadinhas) so aparecem com a amostra minima do `config/amostra.yml`;
abaixo dela, a tela diz "Nao ha evidencia suficiente no acervo para afirmar
isso." Os mesmos padroes aparecem, num bloco a parte e nunca somados, para o
acervo complementar FEPESE: so das provas com gabarito definitivo, em questao
distinta, e com o tipo de questao e as pegadinhas so da classificacao ja
conferida (decisao 78).

Cada materia ainda mostra os **conceitos que aparecem juntos nas questoes**
(§14, item 7): o no principal e os outros que a questao tambem cobra, no
enunciado ou nas alternativas, com as questoes de cada par. Vem de
`radar classificar --pedido --associados` (respondido pelo Claude Code,
com o 🟣 "por conferir") e nunca entra na contagem, que e so da principal
(decisao 86). Confere-se na Analises > Conferencia, em cada questao, com
Confirmar ou Tirar, e a caixa "so com associado por conferir" (decisao 94).

**O acervo complementar FEPESE (Etapa 3B).** `radar complementar` consulta o
que ja esta no banco e escreve `docs/complementar.md`: por materia do meu
edital, quantas questoes cada prova complementar tem **pelo nome da materia**
(certo) e **por termo no texto** (🟡 indicio, do `config/complementar.yml`) -
duas colunas que nunca se somam. Cada prova leva a validacao minima: numeracao
de 1 a N sem buraco, cinco alternativas, gabarito em toda questao e sha256 do
PDF (a mesma prova com outro nome e recusada); o quadro do edital fica "nao
lido", porque o leitor de quadro so da conta dos editais do Estado. Gabarito
**provisorio** classifica mas nao entra nos padroes de cobranca, que se medem
sobre a letra certa.

As questoes das provas aceitas sao classificadas pelo mesmo fluxo do alvo,
com `--evidencia complementar` (prova recusada na validacao nao e
classificada). O lote nunca mistura as duas evidencias, e o que sai dai nunca
entra na incidencia da Policia Penal. Quando o caderno nao diz a materia
("Conhecimentos Especificos"), `--genericos` monta o pedido em que a MATERIA
tambem e resposta, agrupado pela materia que um termo do
`config/complementar.yml` sugere - e so uma suspeita. Para Portugues e
Raciocinio Logico, `--catalogo` propoe o assunto pelo catalogo de
palavras-chave do `macetes.py`: proposta automatica 🟡, que vale depois da
conferencia POR AMOSTRA. Nada e forcado: sem palavra, com dois assuntos ou sem
par no edital, a questao fica sem linha. A conferencia e na tela Analises >
Conferencia, filtro "complementar aceito" (uma linha por questao, mesmo que
ela se repita em varios cadernos); "so a amostra do catalogo" mostra as 20 de
cada materia - sempre as mesmas - e quantas delas foram corrigidas. A amostra
de 04/10 reprovou o lote (o catalogo errou o assunto em quase metade), e as
108 foram classificadas de novo pelo Claude Code (decisao 87).

Na linha complementar a conta e em questao **distinta**, com as ocorrencias ao
lado ("187 questoes · 122 provas (998 ocorrencias em cadernos diferentes)"): a
FEPESE repete o mesmo caderno de Portugues em dezenas de cargos do mesmo
concurso.

`radar complementar --aplicar` grava em `data/acervo_complementar.json` quais
provas entram: as que tem **materia do edital de 2019** e passam na validacao
(hoje, 169 de 183), cada uma com hash, status e data de inclusao. Sem esse
arquivo, nenhuma prova complementar entra em estatistica. Na incidencia, o
complementar e uma **coluna propria**, ao lado do alvo e nunca somada a ele:
"Policia Penal SC: 9 questoes · 2 provas · Acervo complementar FEPESE: 4
questoes · 2 provas". No nivel da materia conta a questao sem classificacao
(o caderno diz a materia); abaixo dela, so a classificada.

**A arvore de conteudos e a evidencia (Etapa 2).** Toda questao do acervo tem
uma **evidencia**: `alvo` (a prova do meu cargo e do meu estado: 2013 e 2019,
170 questoes), `complementar` (outra prova da FEPESE, inclusive o
Socioeducativo 2016) ou `fora` (outra banca). E uma regra so, no
`servico/evidencia.py`, e os tres nunca se somam. A **arvore** nasce do anexo
de programas do edital de 2019, com o texto literal (11 materias, 85 assuntos),
mais Nocoes de Informatica e Direito Administrativo, que cairam em 2013 e nao
estao no edital de agora. Ela mora em `data/conteudos.json`; a classificacao
de cada questao (completa, parcial ou pendente, sempre com procedencia) mora em
`data/classificacoes.json`. Os dois voltam no `importar` e vao no
`sincronizar`.

**Migracao do banco.** Mudanca de estrutura agora tem versao e copia antes.
Qualquer comando migra sozinho na primeira vez; `radar migrar` faz o mesmo e
mostra a tabela "antes x depois". A copia fica em
`data/copias/migracao-v<de>-para-v<para>-<hora>/`, e `radar migrar
--desfazer` devolve o banco a ela (para ficar na versao antiga, volte tambem o
codigo pelo git: o proximo comando do radar novo migraria de novo).

```bash
radar migrar                # leva o banco a versao atual, com copia antes
radar migrar --desfazer     # devolve o banco a copia da ultima migracao
radar conteudos --juntar "<no duplicado>" --em "<no que fica>"
                            # o mesmo conceito em dois nos vira um so, com copia
                            # antes (decisao 99)
```

**Avisos e calendario**

```bash
radar avisar                # favoritos que mudaram, e depois concursos novos
radar avisar --sem-favoritos   # so os concursos novos
radar testar-telegram       # uma mensagem de teste, nao mexe no banco
radar calendario            # grava radar.ics
radar sincronizar           # troca com o GitHub: pull, importar, exportar, push
radar auditar               # confere banco x PDFs e escreve docs/auditoria.md
radar hoje                  # o cronograma do dia; --marcar grava como foi
radar simulados             # lista as rodadas: id, data, acerto, materias
radar descartar 3           # apaga a rodada 3 e as respostas dela (sem volta)
radar descartar --todos     # apaga todas, perguntando antes
radar descartar --vazios    # apaga as sem nenhuma resposta, com mais de 1 dia
```

**A web e a automacao**

```bash
radar web                   # sobe e segura o terminal; Ctrl+C para
radar web --rede            # abre tambem no celular, na mesma rede Wi-Fi
radar subir --abrir         # sobe em segundo plano, sem janela, e abre no navegador
radar parar                 # desliga o que o `radar subir` subiu
radar status                # no ar ou nao, e como foi o ultimo backup
radar agendar               # web no logon e backup as 23:30, no Agendador
radar agendar --status      # --remover apaga tarefas e atalhos
radar backup                # o sincronizar das 23:30, agora e com log
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
o aviso **fura o teto** (abre com 👀) e a cidade ganha um cartao "De olho" na
tela Analises > Edital, com a situacao de cada uma. O cargo continua secundario - isso nao
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

### A amostra minima, em `config/amostra.yml`

Abaixo de quantas questoes e provas o radar nao tira conclusao. Duas secoes,
que nunca se somam: `acervo` fala da banca (os padroes de cobranca: 3
questoes em 2 provas; a tendencia de letra no gabarito: 50 questoes; o "base
pequena": menos de 3 provas) e `desempenho` fala de mim (o minimo de cada
nivel da arvore, os cortes dos estados e a evolucao da home: 20 respostas
em cada metade). Mude o numero la e toda tela muda com ele - nao ha minimo
escrito no codigo, fora o 3 do caderno de erros, que mede outra coisa.

### O link do Qconcursos, em `config/qconcursos.yml`

A faixa que manda ao Qconcursos tem o botao "Abrir no Qconcursos", com o
filtro pronto: FEPESE, sem anuladas nem desatualizadas, so os assuntos do tema
(decisao 140). O radar nao consulta o site (os termos proibem raspagem): os
numeros dos assuntos foram copiados por mim do proprio site, uma vez. Para
corrigir um tema, troque os numeros no arquivo. Para achar o numero de um
assunto: no Qconcursos, escolha so a disciplina, abra a lista de Assunto e
role ate o fim; F12 > Elements, botao direito num assunto > Inspecionar, suba
ate o `<ul class="q-options">` e veja o `value` de cada assunto. Quando o
assunto do site e mais largo que o tema (a LEP e um assunto so), o `aviso` do
tema diz na faixa o que pular. Tema fora do arquivo continua com o filtro
escrito do plano.

### A prioridade das fichas, em `config/prioridade.yml`

A regra que ordena os temas e explica "por que agora" na ficha. E regra de
priorizacao, e nao previsao de prova:

```
prioridade = peso da materia no edital (questoes da prova)
           x (fatia do ALVO + peso_do_complementar x fatia do complementar)
           x (1 - meu acerto, so com amostra suficiente; sem ela, 1)
           x tempo (1 a fator_maximo, pelos dias desde a ultima pratica)
           x multiplicador, quando o conteudo esta na fila de revisao
```

Os numeros ajustaveis: `piso_em_questoes` (o tema que nao apareceu nas provas
conta meia questao, para nao zerar), `peso_do_complementar` (0,25; com 0 a
ordem e so a do alvo), `dias_para_dobrar` e `fator_maximo` do tempo, e o
`multiplicador` da revisao (1,5). Mude la e a ficha mostra a conta nova.

### A taxonomia, em `config/taxonomia.yml`

Os tipos de "elemento" que cada familia de materia aceita na arvore de
conteudos: artigo, inciso e sumula no Direito; regra gramatical e crase no
Portugues; tipo de problema e tabela-verdade no Raciocinio; e assim por
diante. Ampliar uma lista e editar o arquivo: o banco nao muda e nao ha
migracao. Tipo fora da lista da familia e recusado, para um erro de digitacao
nao virar tipo novo. O arquivo tambem guarda os tipos de questao, as materias
que cairam no alvo e nao estao no edital atual, e os sinonimos de materia de
provas antigas (como "Direito Processo Penal" de 2013).

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

> Desde a decisao 74 (03/10/2026), o "Onde estudar primeiro" e a revisao
> espacada nao leem mais esta coluna nem o catalogo: o assunto e o da
> classificacao na arvore de conteudos (`radar classificar`).

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
- **do zero** entra quando nao ha questao real no escopo, e tambem completa
  o pedido quando a base nao basta - sempre dentro do mesmo no, pela fonte
  oficial ou pelo item do edital, marcada sem questao real de referencia
  (decisao 35).

**Treinar com as que ja tenho** (`/geradas`) escolhe pelo no da arvore:
a materia, um assunto ou um subassunto, cada um com quantas geradas tem, e o
no pega tudo que esta abaixo dele. A ficha do tema manda para la com o no ja
escolhido (decisao 91).

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

#### A navegacao e a home

A barra tem os seis destinos da especificacao e mais um, o **Hoje** (o
cronograma do dia, que o Ciclo 1 trouxe): **Hoje**, **Meu foco** (a home),
**Estudar**, **Revisão**, **Análises**, **Concursos** e **Mais** - as paginas
de cada um estao na tabela "A pagina web, aba por aba".

A home tem três blocos — o alvo, **o que estudar agora** com [Começar
treino], e **o que revisar** com [Revisar agora] — e duas faixas finas,
evolução e concurso. Bloco sem dado convida: abaixo de 20 respostas, a
evolução diz quantas faltam. A prioridade é peso no edital × (1 − meu
acerto), e matéria com menos respostas que o mínimo da matéria no
`config/amostra.yml` (hoje 20) conta como não treinada.

#### O design system

As cores, o espaco e a letra moram em **`src/radar/web/static/design.css`**, e
os componentes (selo, bloco, aviso de lei) em **`templates/_componentes.html`**.
O escuro e o padrao; o botao da barra troca e guarda a escolha em cookie, e
`?cor=escuro` ou `?cor=claro` na URL forca um dos dois para comparar.

**Toda tela esta no design system** desde a Etapa 7B: cada uma marca
`<body class="ds">`, usa a coluna `ds-pagina`, o cartao, a tabela e o botao
do `design.css`, e o `<style>` dela so guarda o que e so dela, nos tokens de
la. Nenhuma tela define a propria paleta, e a barra do topo tambem le os
tokens. Na lista de Concursos, a cor do anel diz a distancia: perto verde,
proximo amarelo, estadual azul, longe cinza e "a confirmar" cinza tracejado.

Os **selos** sao as quatro origens da secao 20 do novo.md (Etapa 7A): 🟢 fonte
oficial (edital, gabarito, lei, a questao da prova), 🔵 estatistica do acervo,
🟡 analise automatica (o meu desempenho, a prioridade, a classificacao, a
tendencia) e 🟣 gerado por IA - mais o 📌 do plano, na ficha. Eles moram em
**`src/radar/origem.py`**, e quem escolhe a cor e o dado: cada servico grava a
origem (`origem`, ou `origens` quando junta partes) e a tela so desenha. A meta
do dia (Ideal, Reduzida, Minima, Nao fiz) nao e selo e tem as cores dela.

#### A Central de Macetes

Abaixo da Central, **o costume de qualquer banca** e a exploracao por banca,
cargo e tema. Ele conta so a evidencia que vale (decisao 75): da FEPESE, o
acervo complementar **aceito** - as provas do cargo tem a Central, e prova
recusada no levantamento da Etapa 3B nao entra -; de outra banca, as provas
dela. O que ficou de fora vai contado na tela, e nunca somado.

O topo de `/macetes` e um **cartao por materia** das minhas provas (2013 e
2019, sem as anuladas), no formato da especificacao. Cada parte leva o selo
de onde veio, e as partes nao se misturam:

- **base**: "24 questoes analisadas — provas 2013 e 2019", com o aviso
  **base pequena** — sao so duas provas do cargo;
- **🔵 Padrao da banca**: a contagem do `macetes.py` sobre essas questoes —
  como ela pergunta ("3 de 24 pedem a INCORRETA") e as palavras que mais
  aparecem;
- **🟣 Macete (IA)**: a regra, a **fonte citada** (com o link oficial da lei
  da materia) e a **pegadinha recorrente**, com a procedencia embaixo. Vem de
  `data/macetes.json`, pelo caminho sem API (`--pedido --macetes` /
  `--importar`). Macete sem fonte ou sem procedencia **nao aparece**, mesmo
  que alguem o escreva a mao no arquivo;
- **[Ver questoes reais relacionadas]** abre as questoes em que o macete se
  apoia, com o selo 🟢, o gabarito definitivo e o link do caderno — e ali que
  eu confiro o 🟣 contra a prova.

O aviso **⚠ A lei mudou depois desta prova** sai da lista `mudancas:` do
`config/leis.yml`: tema, lei, quais anos de prova ficaram velhos e as palavras
que reconhecem a questao. Sem a lista, nenhuma questao ganha o aviso, e a tela
diz isso em vez de ficar calada.

A lista existe desde 03/10/2026: 15 itens, que pegam 17 questoes das provas de
2013 e 2019, conferidos questao a questao no texto compilado da lei (a
evidencia esta em [docs/leis_alteradas.md](docs/leis_alteradas.md)). Eles foram
escritos pelo Claude Code e estao **por conferir**: o aviso sai com o 🟣
"Escrito por IA, por conferir" ate voce trocar `conferida: false` por
`conferida: true` no item - ou apagar o item, se estiver errado.

A lista `fronteira:` do mesmo arquivo guarda o que mudou depois das provas
num ponto que nenhuma questao cobra (a EC 104/2019 das policias penais, a
saida temporaria da Lei 14.843/2024...). Ali nao ha aviso na questao - ela
continua certa -, e sim na **ficha do tema**, onde vale saber: o item entra
quando um no dele esta no mesmo ramo de um no da ficha, ou quando uma marca
dele esta no titulo do tema. Tambem por conferir, com o 🟣.

#### Sem pagar: o pedido em arquivo, respondido pelo Claude Code

```bash
radar gerar --pedido --quantas 20            # TODOS os pedidos em data/pedido_ia.json
radar gerar --pedido --macetes               # um pedido de macete por materia
radar gerar --pedido --explicacoes           # explicacao de cada questao que errei
radar gerar --importar data/resposta_ia.json # le a resposta, confere e grava
```

#### O filtro hierarquico e os tres modos (Etapa 5)

Pedir so a materia e amplo demais: "Lei de Execucao Penal" tem dezenas de
assuntos, e eu podia receber questao de conteudo que ainda nem estudei. O
escopo fecha ate onde eu quiser, e **nada de fora dele entra**:

```bash
radar gerar --pedido --quantas 20   --materia "Direito Penal"   --assunto "Tipicidade, ilicitude, culpabilidade, punibilidade"   --subassunto "Abolitio criminis" --elemento "CP, art. 2º"

radar gerar --pedido --modo revisao --materia "Lingua Portuguesa" --quantas 20
radar gerar --pedido --modo simulado --materia "Direito Penal" --quantas 20
```

**Os tres modos** (`--modo`), e o que cada um faz:

| Modo | O que entra |
|---|---|
| `treino` | so o escopo fechado: materia > assunto [> subassunto [> elemento]] |
| `revisao` | so os conteudos que eu JA ESTUDEI (`radar desempenho`) |
| `simulado` | a abrangencia ampla de sempre; sem materia escolhida, as questoes se dividem pelo peso do edital |

Sem `--modo`: **com assunto e treino, so com materia e simulado**, e a saida
escreve qual foi - amplo e especifico nao podem se confundir.

**Nome que a arvore nao tem para o comando**, com ate cinco sugestoes, e nao
gera nada:

```
$ radar gerar --pedido --materia "Direito Penal" --assunto "Aplicacao da Lei Penal"
O assunto 'Aplicacao da Lei Penal' nao existe em 'Direito Penal'.
Voce quis dizer: Imputabilidade penal?
Nada foi gerado: eu nao alargo o escopo sozinho.
```

**A base de cada questao fica gravada** (a regra de ouro da secao 9), nesta
ordem de prioridade: questao real do mesmo no - **alvo antes do complementar** -,
depois a fonte oficial do `config/leis.yml`, e por fim o item do edital. Quando
nao ha questao real, a questao fica marcada com **"sem questao real de
referencia"**: o sistema nunca inventa um vinculo para preencher o campo.

**A garantia e a validacao do que a IA declara.** Cada questao da resposta tem
de dizer o `conteudo` dela, e a importacao recusa, contando na saida:

- conteudo declarado fora do escopo pedido;
- com dispositivo pedido, artigo citado que nao e nenhum deles;
- vinculo com questao real que nao estava no pedido;
- `do_zero` sem a marca de "sem questao real de referencia".

A leitura do TEXTO continua sendo minha, no treino, com o botao "essa questao
esta errada" que ja existe. O mesmo filtro esta na tela, em **Estudar > Gerar
questoes**.

O `--pedido` nao chama a API. Ele escreve os mesmos pedidos que o `--valendo`
mandaria, com a instrucao, o campo `como_responder` e o `formato_da_resposta`
dentro do arquivo. Eu abro o Claude Code no VS Code, peco para ele ler
`data/pedido_ia.json` e seguir o `como_responder`, e ele escreve
`data/resposta_ia.json`. Os dois arquivos ficam fora do git: sao de passagem.

O `--importar` confere antes de gravar, e **conta em voz alta o que recusou**:

- a resposta tem que ser do **mesmo lote** do pedido. Pedido novo substitui o
  velho, e resposta de lote velho e recusada inteira;
- questao: as cinco alternativas, um gabarito que aponta para uma delas, e **o
  artigo da lei** — aqui artigo vazio e recusado. Nas Regras de Mandela, que
  nao tem artigo, vale a regra pelo numero ("regra 12.1", decisao 76). Fora de
  Direito (as materias em `sem_lei` do `config/leis.yml`), vale a regra
  gramatical ou logica;
- macete: regra, fonte (com artigo, nas materias de lei) e os codigos das
  **questoes reais** em que ele se apoia — codigo que nao estava no pedido e
  recusado, porque viraria link para questao que nao existe.

**A procedencia e o caminho, e nao um modelo:** o que entra por aqui e gravado
como `Claude Code, importado manualmente, em 25/09/2026`. O radar nao sabe qual
modelo o Claude Code usou, e dizer `claude-sonnet-5` seria inventar. Questao
sem modelo nao e gravada por nenhum caminho, e linha do
`questoes_geradas.json` sem `modelo` e `criada_em` e recusada no importar.

A questao importada vai para a mesma tabela e o mesmo arquivo das geradas: o
selo e a separacao das reais sao os de sempre. O macete ainda nao tem tela: ele
vai para **`data/macetes.json`**, versionado e levado pelo `sincronizar`, e a
Central de Macetes le de la quando existir.

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
gasta uns 3 minutos por dia.

### Deixar tudo automatico

Um comando, uma vez so, e voce nao precisa mais lembrar de nada:

```bash
radar agendar
```

Ele cria **duas tarefas no Agendador do Windows**, no seu proprio usuario (nao
pede administrador, nao pede senha):

| Tarefa | Quando | O que faz |
|---|---|---|
| `Radar - web` | ao fazer logon | sobe a web em segundo plano, sem janela |
| `Radar - backup` | todo dia as 23:30 | roda o `radar sincronizar` e guarda a saida em `data/logs/` |

Se o PC estava desligado as 23:30, o backup roda assim que voce ligar - e por
isso que as tarefas nascem de um XML e nao da linha de comando do `schtasks`,
que nao tem essa opcao. Os logs com mais de 30 dias somem sozinhos.

Ele roda com uma etapa pela metade na pasta: o `radar sincronizar` nao precisa
da pasta limpa (acima, em "Trocando com o GitHub"). De 27/09 a 03/10/2026
precisava, e o backup falhou em todas as noites.

E cria **dois atalhos na Area de Trabalho**:

- **Radar.bat** - sobe o radar e abre a tela Hoje no navegador;
- **Parar o Radar.bat** - desliga.

**Nao e servico do Windows**, de proposito: servico pede administrador, roda
sem voce estar logado (para nada), e esconde o erro no Visualizador de Eventos.
O porque completo esta em [docs/decisoes.md](docs/decisoes.md).

#### O Git precisa lembrar o login do GitHub

O backup das 23:30 faz `git push`. Se o git pedir usuario e senha naquela hora,
ninguem vai estar la para digitar, e o backup falha todo dia.

Quem resolve isso ja esta instalado: o **Git Credential Manager**, que vem com
o Git para Windows. Ele guarda o login no Gerenciador de Credenciais do Windows
na **primeira vez** que voce empurra algo:

```bash
git push
```

Na primeira vez abre uma janela do navegador para entrar no GitHub; da proxima
em diante ele nao pergunta mais nada. Para conferir que ficou guardado, rode
`radar backup`: se ele terminar sem pedir nada, o login esta no lugar.

Se o backup falhar por causa disso, o motivo aparece no log e na tela **Mais**
como `fatal: Authentication failed`.

#### Subir, parar e conferir

```bash
radar subir              # sobe em segundo plano, sem janela, e devolve o prompt
radar subir --abrir      # e ja abre a tela Hoje no navegador
radar parar              # desliga
radar status             # no ar ou nao, o endereco, e como foi o ultimo backup
radar agendar --status   # o que o Agendador diz das duas tarefas
radar agendar --remover  # apaga as tarefas e os atalhos
radar backup             # faz um backup agora, sem esperar as 23:30
```

O `radar subir` e diferente do `radar web`: o `web` segura o terminal aberto e
para com Ctrl+C; o `subir` deixa o servidor solto, sem janela nenhuma, e anota
o numero do processo em `data/radar_web.pid` - que e como o `parar` sabe quem
desligar. Ele confere se o servidor respondeu de verdade antes de dizer que
subiu, e quando nao sobe mostra o fim de `data/logs/web.log`.

```
$ radar status
Web: no ar em http://127.0.0.1:8000 (processo 24680)
     desde 27/09/2026 às 08:12
Backup: deu certo em 27/09/2026
```

**Backup que falhou aparece na tela Mais** ("O ultimo backup falhou em 26/09:
fatal: Could not resolve host: github.com") e fica la ate o proximo dar certo.
Falha em silencio seria o mesmo que nao ter backup.

## Como o projeto esta organizado

```
src/radar/
├── config.py       le ambiente (.env). Nenhum efeito colateral no import.
├── models.py       tabelas concursos, eventos, questoes, questoes_geradas,
│                   simulados, respostas, registros_de_estudo, erros_anotados,
│                   estudos_extras, notas_da_semana, conteudos,
│                   classificacoes e versao_do_banco
├── db.py           engine preguicoso + context manager de sessao
├── migracoes.py    a versao do banco: passos numerados, copia antes, desfazer
├── conteudos.py    a arvore de conteudos e a taxonomia (puro, sem banco)
├── incidencia.py   o mapa de incidencia do alvo e os padroes (puro)
├── origem.py       as quatro origens e os selos (🟢 🔵 🟡 🟣 e o 📌), e as
│                   duas frases que nao variam: a do acervo e a da IA
├── servico/        as regras, um arquivo por assunto:
│   ├── __init__.py   consulta, favoritos, detalhe, elegibilidade,
│   │                 retificacao e calendario - e a fachada dos demais
│   ├── coleta.py     roda as fontes, grava com upsert, classifica
│   ├── avisos.py     quem vira mensagem no Telegram, e quando
│   ├── provas.py     acervo, leitura dos cadernos, padrao da banca
│   ├── simulado.py   monta a rodada, responde, mede o acerto
│   ├── geradas.py    as questoes que a IA escreveu: plano, guarda, sorteio
│   ├── manual.py     IA sem API: pedido em arquivo, resposta importada
│   ├── cartoes.py    a Central de Macetes: um cartao por materia
│   ├── previsao.py   quando o municipio costuma abrir de novo
│   ├── cronograma.py o diario do dia e o que a tela Hoje mostra
│   ├── erros.py      o caderno de erros: anotar, e a revisao 1-7-30 dele
│   ├── extra.py      o estudo extra, fora das faixas do plano
│   ├── semanas.py    como fui em cada semana, agrupado pelos ciclos do mapa
│   ├── materias.py   o progresso em cada materia do edital, e a projecao
│   ├── metricas.py   a fonte unica da contagem: questao, acerto e erro
│   ├── conferencia.py o gravado no diario contra a regra, dia a dia
│   ├── evidencia.py  alvo, complementar ou fora: a regra unica da prova
│   ├── conteudos.py  a arvore no banco: semear, JSON, textos antigos, pendentes
│   ├── classificacoes.py a questao ligada a um no, com status e procedencia
│   ├── incidencia.py o mapa do alvo a partir do banco
│   ├── complementar.py o acervo complementar FEPESE: levantar, validar, aceitar
│   ├── desempenho_por_conteudo.py o meu acerto por no (radar e anotado, a parte)
│   ├── estudo.py     estudado, praticado, a fila de revisao (a unica: o Meu
│   │                 desempenho inteira, a home so as pontas) e o que refazer
│   ├── espacada.py   o 1-7-30 e a rodada "Fazer as revisoes de hoje" (decisao 128)
│   ├── fichas.py     as fichas e os resumos: arquivo, contexto, aba por dia,
│   │                 o que o botao Resumo de cada faixa abre
│   ├── composicao.py a composicao das rodadas que medem (decisao 67)
│   ├── sabado.py     a revisao semanal, o R+7 dos diagnosticos e a comparacao
│   ├── faixa_no_radar.py a faixa de Portugues que comeca pelas do radar
│   ├── compilado.py  o simulado compilado e a divisao pelo quadro do edital
│   ├── inicio.py     a pagina inicial
│   └── comum.py      o pouco que mais de um assunto usa
├── amostra.py      le config/amostra.yml: os minimos de amostra, num lugar so
├── prioridade.py   le config/prioridade.yml: a prioridade de cada tema
├── qconcursos.py   le config/qconcursos.yml: o link do Qconcursos de cada tema
├── fichas.py       a ficha de estudo, o resumo, o "caiu" de cada tema e as
│                   geradas da faixa (puro)
├── complementar.py a linha complementar e a validacao do caderno (puro)
├── regioes.py      le config/regioes.yml: anel e grafia canonica do municipio
├── alvo.py         le config/alvo.yml: e o cargo que eu quero?
├── gabarito.py     o gabarito definitivo, e as questoes anuladas
├── eventos.py      a linha do tempo: o que mudou em cada concurso, e quando
├── foco.py         a situacao do alvo principal, para a pagina inicial
├── onde_estudar.py por qual assunto comecar: quanto ele vale, quanto eu erro
├── cronograma.py   le config/cronograma.yml: horarios, rampa e o nivel
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
├── automacao.py    a web em segundo plano, as tarefas do Agendador e o backup
├── cli.py          comandos typer. `atualizar` roda a rotina inteira
├── collectors/
│   ├── base.py                  Coletor + ItemColetado; robots.txt,
│   │                            User-Agent e atraso entre requisicoes
│   ├── concursos_no_brasil.py   fonte 1: feed RSS, com paginacao
│   ├── fepese.py                fonte 2: API REST do WordPress da FEPESE
│   └── ieses.py                 fonte 3: API JSON da listagem de projetos
└── web/          FastAPI + Jinja2
    ├── app.py                    rotas e o contexto de cada tela
    ├── templates/_topo.html      a barra de navegacao, igual em toda pagina
    └── templates/hoje.html       a tela Hoje, o cronograma do dia

config/
├── regioes.yml     os tres aneis de distancia
├── alvo.yml        os cargos que eu quero, em ordem
├── leis.yml        onde ler a lei de cada materia e assunto de Direito
├── perfil.yml      meus dados, para a elegibilidade
├── taxonomia.yml   os tipos de elemento por familia de materia
├── amostra.yml     os minimos de amostra (padroes de cobranca)
├── qconcursos.yml  os assuntos do Qconcursos de cada tema (o link da faixa)
└── cronograma.yml  o plano de estudo, dia a dia (dado, editavel a mao)
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
cargo, ano, tipo, o `sha256` e o caminho de cada arquivo. Com ele, `radar
baixar-provas` reconstroi o acervo inteiro em qualquer maquina - no caminho
gravado, porque a FEPESE da o mesmo nome de arquivo (S07.pdf) a provas de
concursos diferentes do mesmo municipio, e o segundo leva o nome do hotsite na
frente (decisao 90).

### Testes

```bash
pytest -q
```

Os testes usam arquivos de exemplo em `tests/fixtures/` e um SQLite temporario.
**Nenhum deles vai a internet**, entao passam offline. Sao ~2.400, e a suite
inteira leva uns 25 minutos neste PC: durante o
trabalho, rode so o arquivo do que mudou, e a suite inteira uma vez no fim -
o `coleta.yml` roda a suite antes de coletar.

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
