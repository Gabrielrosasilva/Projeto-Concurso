# Decisoes que ja foram tomadas

Decisoes ja fechadas do radar, com o motivo de cada uma. Nao precisam ser
rediscutidas: se uma delas mudar, **este arquivo e atualizado junto**.

O `CLAUDE.md` aponta para ca e fica so com o contexto permanente do projeto.
O porque detalhado de cada fase, com os numeros medidos, esta em
[docs/historico.md](historico.md).

- datas: sempre UTC com fuso, convertidas para horario local so na exibicao;
- a coleta faz upsert e **nunca** sobrescreve `interesse` e `notas`;
- fonte que falha e registrada e a coleta segue com as outras;
- o schema ja tem colunas de fases futuras, vazias. E de proposito: sem
  Alembic, coluna nova depois significa recriar o banco;
- PDF nao vai para o git. Vai o manifesto `data/provas.json`, com sha256, e
  `radar baixar-provas` reconstroi a pasta. Medido: 29 documentos deram
  37 MB em disco contra 18 KB de manifesto;
- caminho no manifesto usa barra normal mesmo no Windows, senao a outra
  maquina nao acha o arquivo;
- o acervo comeca pelo concurso ENCERRADO e perto de casa: encerrado e o
  que tem prova publicada, e perto e o padrao de banca que me serve. O alvo
  principal passou na frente disso - veja a decisao sobre `config/alvo.yml`
  mais abaixo;
- a materia de cada questao vem do cabecalho de secao do proprio caderno,
  e o gabarito vem marcado no texto (Check-square). Nada disso e adivinhado;
- a leitura do caderno parte das ALTERNATIVAS, nunca dos numeros: a ordem
  do texto e embaralhada pelas duas colunas, e o enunciado pode ter lista
  numerada dentro;
- linha que se repete em toda pagina e mobilia e sai do texto. Foi assim
  que a sujeira na ultima alternativa caiu de 5,1% para 1,1%;
- concurso municipal de outro estado e `remoto`, nao `indefinida`: prova de
  municipio de SP e aplicada em SP. `indefinida` fica para quem pode mesmo
  aplicar em Florianopolis (federal, nacional, ou sem UF);
- a lista padrao esconde `remoto`, `indefinida` e `noticia`. Nada e apagado:
  a pagina e a CLI mostram tudo com --todos;
- avisos sao por **Telegram**. WhatsApp foi avaliado e descartado: o oficial
  exige conta Meta Business, numero separado e template aprovado para mensagem
  proativa; o nao oficial arrisca banir meu numero pessoal;
- o aviso leva SEMPRE o link da fonte junto;
- viram mensagem: `nucleo`, `proximo` e `indefinida`. O indefinido entra de
  proposito - federal sem UF pode aplicar prova em Floripa, e perder um
  concurso bom e pior que receber dois avisos a toa;
- cada concurso e avisado uma vez so (coluna `avisado_em`), e o teto e de 10
  mensagens por coleta. O teto e protecao contra regra quebrada virar 200
  notificacoes de madrugada;
- token e chat_id SO em variavel de ambiente: `.env` na maquina, Secrets no
  Actions. O log nunca imprime a URL da API, porque ela carrega o token;
- a carga inicial anda para tras pelo `?paged=N` do proprio feed, e nao por
  raspagem de HTML nem pelo sitemap. Conferido no site real: o sitemap existe
  mas para em junho/2026, e nao traz titulo - so URL. O feed paginado traz
  tudo e usa o mesmo parser;
- favorito e escolha minha: a coleta nao mexe, e NENHUM filtro o esconde -
  nem distancia, nem salario, nem prazo vencido. Os favoritos ficam num mural
  fixo a esquerda, visivel em qualquer aba;
- na tela, TODA informacao vem com rotulo ("Banca: FEPESE", nao "FEPESE"), e
  `nucleo` aparece como "Perto";
- dois campos tem dono e o classificador nao encosta neles: o salario que eu
  digitei (`salario_manual`) e o municipio que veio da pagina do edital
  (`municipio_confirmado`). Sem a segunda trava, um `reclassificar` desfazia o
  trabalho do `detalhar` e a SEFAZ SC voltava de `nucleo` para `indefinida`;
- os campos numericos da rota web chegam como TEXTO e sao convertidos por
  `util.converter_valor`. Formulario HTML manda todo campo, inclusive o vazio:
  declarar `salario_min` como numero fazia `salario_min=` virar erro 422 e
  derrubar a pagina inteira, nao so aquele filtro;
- o filtro de banca aceita nome curto e nome por extenso (FCC = Fundacao
  Carlos Chagas), pela mesma tabela de apelidos de `detalhes.BANCAS`;
- a busca por palavra ignora acento, via funcao `sem_acento` registrada no
  SQLite, e procura tambem no municipio;
- com filtro ligado e zero resultado, a tela diz que foi o FILTRO que nao
  achou nada - dizer "nenhum concurso perto de voce" levaria a conclusao
  errada;
- o filtro de salario exclui quem nao tem valor conhecido, e a tela avisa
  quantos ficaram de fora. A primeira versao incluia os nulos para nao
  esconder concurso bom, e o resultado foi um filtro que nao filtrava: 1.115
  dos 2.185 nao trazem salario no titulo;
- `situacao` vem das datas de inscricao quando ha prazo conhecido, e do
  TITULO quando nao ha: "tem concurso autorizado" vira `autorizado`, "define
  banca" vira `banca_definida`, "deve sair" vira `prevista`. Data e fato,
  titulo e interpretacao - por isso a data manda;
- a aba de noticias NAO filtra nada: nem anel, nem fase, nem tipo. Quem
  procura "PM" quer saber de qualquer policia militar, onde estiver e na fase
  em que estiver. Ela ordena por ANDAMENTO, e nao por data;
- valor neutro da fonte nao rebaixa o que ja se sabe: "desconhecida" na
  situacao e tratado como nulo em `VALORES_SEM_INFORMACAO`;
- `reclassificar` passa o municipio e o tipo ja conhecidos para o
  classificador. Sem isso ele reextraia do titulo e os 107 concursos da FEPESE
  perdiam o municipio - o titulo dela nao tem "(SC)". Reclassificar existe
  para reaplicar a regra do ANEL, nao para reextrair o que a fonte ja deu;
- o formulario da web usa autocomplete="off": o navegador restaurava o valor
  digitado antes e o campo aparecia preenchido sozinho;
- o DOU (in.gov.br) tambem esta FORA: robots.txt com Disallow: / para todos,
  igual ao DOM/SC. O Sigepe Oportunidades foi testado e nao serve - sao vagas
  de movimentacao para quem JA e servidor federal, e nao concurso aberto;
- o Querido Diario SAIU do radar. O robots.txt dele traz Disallow: /api, e a
  regra passou a ser respeitar robots.txt sem excecao - nem para API publica
  de projeto de dados abertos. O que ele devolvia eu ja pego das bancas, e
  mais cedo: cobria 1 dos meus 35 municipios e nao tinha o ato de contratacao
  de banca. Nao reintroduzir;
- o DOM/SC esta FORA de raspagem: robots.txt com "Disallow: /" para todos.
  Nao insista; o caminho legitimo e o alerta por e-mail do proprio site;
- fonte que sabe o que publica declara `tipo` no ItemColetado, e o
  classificador respeita. A FEPESE publica num tipo de post `concurso`, entao
  nao ha o que adivinhar pelo titulo - sem isso, "2026 - Prefeitura Municipal
  de Sao Jose" virava `noticia`, porque nao tem a palavra concurso no titulo;
- municipio conhecido decide o anel mesmo sem UF declarada: config/regioes.yml
  so tem municipio catarinense. So nao vale se a fonte afirmar outro estado;
- aviso e sobre NOVIDADE: nao avisa o que ja encerrou nem o publicado ha mais
  de 30 dias, a menos que a inscricao esteja aberta. Sem isso, ligar uma fonte
  nova despejava o historico dela no celular;
- prazo de inscricao, banca e lotacao vem da PAGINA DO POST, nao do PDF do
  edital. Sai mais barato e cobre a maioria dos casos;
- `radar detalhar` nao le a pagina de todos: segue a prioridade nucleo/proximo,
  depois SC indefinida, depois federal. Outro estado nunca;
- pagina que cita varios municipios nao define municipio nenhum. Edital de
  secretaria estadual lista o estado inteiro, e escolher um seria chute;
- a lacuna do "complete as frases" nao esta escrita no caderno: a FEPESE
  desenha o tracinho como grafico e sobra so espaco em branco. `marcar_lacunas`
  troca corrida de 3+ espacos por ____, e roda ANTES de juntar as linhas -
  lacuna no comeco e no fim da linha some se juntar primeiro. 258 enunciados
  (5,1%) ganharam lacuna, e em 188 de 193 o numero de lacunas bate com o numero
  de itens da resposta;
- `radar questoes --refazer` atualiza a questao no lugar, pela chave (prova,
  numero). Nao apaga para regravar: o simulado guarda o id da questao;
- municipio e gravado SEMPRE na grafia de config/regioes.yml. Cada fonte
  escreve de um jeito ("Palhoca" e "Palhoca" com cedilha, Florianopolis em 4
  grafias), e qualquer conta por municipio saia errada. Municipio de fora de SC
  volta como veio: o YAML so tem catarinense;
- a previsao de abertura usa o ritmo do proprio municipio, mas LIMITADO pela
  validade legal (2 a 4 anos), e por MEDIANA. Sem isso, buraco de cobertura
  virava absurdo: Tubarao, com 2011 e 2026 conhecidos, dava "proximo em 2041";
- a previsao carrega sempre o motivo e os anos que a embasam, e a tela avisa o
  que o historico NAO cobre (outra banca entre 2021 e 2025);
- a aba Macetes nao calcula nada antes de a banca ser escolhida, e o menu de
  bancas vem das PROVAS baixadas, nao dos concursos. As citadas sem acervo
  aparecem numa nota explicando que falta um coletor por banca;
- o assunto dentro da materia sai de um catalogo de palavras-chave escrito a
  mao em `macetes.CATALOGO_DE_ASSUNTOS`. Cobertura em enunciados distintos:
  portugues 76%, informatica 61%, gerais 59%, raciocinio 53%. O que sobra e
  contado como "sem assunto detectado" - nunca empurrado para um assunto;
- a materia dominante do recorte so e afirmada com 60% ou mais das questoes.
  "Crase" da 56 de 59 em Portugues; recorte que mistura nao tem materia;
- questoes por caderno divide pelos cadernos em que AQUELA materia apareceu.
  Temas de Educacao so cai em prova de professor: dividir pelo total faria
  parecer que cai pouco quando cai muito onde cai;
- os graficos da aba Macetes sao pizza, feitos com conic-gradient no CSS: sem
  JavaScript, como o resto da tela. Acima de 8 categorias o resto vira uma
  fatia "outros";
- na pizza, a fatia e a participacao no TOTAL de questoes, nunca a media por
  prova: somar media de materias que caem em provas diferentes daria 81 numa
  prova de 40. O numero por prova fica na legenda;
- na aba Macetes, gabarito e palavras contam UMA VEZ POR ENUNCIADO, e
  materia e forma de perguntar contam todas. Buscando "crase" saem 59 questoes
  e so 7 enunciados: a mesma aparece em 38 cadernos e a resposta e "d", o que
  dava "letra d em 64%" e levaria a chutar d;
- abaixo de 50 enunciados diferentes a pagina NAO afirma nada sobre a letra do
  gabarito. Com 7 questoes o que parece tendencia e sorteio;
- no acervo inteiro as cinco letras ficam entre 19,5% e 20,5%: o "chute na C"
  nao existe na FEPESE, e a tela diz isso;
- a aba Macetes nao inventa: pegadinha especifica e macete de memorizacao nao
  saem de contagem, e ficam de fora ate a leitura por IA entrar;
- a pagina de erro 404 detecta sozinha o caso "servidor rodando codigo
  antigo", comparando a data dos .py com a hora em que subiu. E o sintoma mais
  confuso que aparece aqui: o link esta na tela (template e lido do disco a
  cada visita) e a rota nao existe (codigo e lido so na partida);
- a IESES entrou como fonte 3, pela API que a propria listagem usa
  (/projetos/api), achada lendo o JS da pagina. Ela NAO afirma uf=SC: a banca e
  catarinense mas faz concurso no Amazonas e no Mato Grosso do Sul;
- resposta 4xx ao pedir robots.txt significa que NAO HA robots.txt, e o site
  pode ser acessado (RFC 9309). O leitor do Python trata 403 como "proibido
  tudo", e isso bloqueou o acervo inteiro da IESES: o CDN dela responde 403 a
  qualquer caminho inexistente, inclusive /robots.txt. So o que se consegue
  LER vira restricao - o DOM/SC, que responde 200 com Disallow: /, segue fora;
- na IESES o gabarito e um PDF separado do caderno, e casa com a prova pelo
  codigo do cargo no nome do arquivo. Prova e gabarito se chamam igual na
  origem, entao o tipo entra no nome em disco;
- a materia da questao da IESES vem do EDITAL, nao do caderno: o Anexo II liga
  cargo a nivel, e o Anexo IV diz de que o nivel e feito, na ordem da prova. O
  caderno dela nao tem cabecalho de secao nenhum;
- os Conhecimentos Especificos da IESES sao "o resto" depois das materias
  listadas. O mesmo edital escreve o numero deles de tres jeitos, e a ordem
  (gerais primeiro) e a unica coisa que nunca muda;
- o que conta como materia UNIVERSAL sai do catalogo de apelidos de
  `macetes`, e nao de uma lista fixa de nomes: cada banca escreve a mesma
  materia de um jeito ("Nocoes de Informatica" e "Informatica");
- elegibilidade e por CONCURSO, nao por cargo: o edital traz dezenas de cargos
  e o radar guarda um registro por concurso. "elegivel" quer dizer que HA vaga
  de nivel superior, e nao que eu sirvo para todas as vagas;
- cada exigencia lida do edital guarda o TRECHO que a embasa. "Idade maxima 75"
  e aposentadoria compulsoria (LC 152/2015), e so o trecho mostra isso;
- "aptidao fisica e mental por junta medica" NAO e TAF: e exame admissional.
  So conta "Teste de Aptidao Fisica de carater eliminatorio";
- edital que nao rende texto e apontado como digitalizado em imagem, nunca
  tratado como "nao exige nada". Sao 3 dos 32 editais do acervo;
- o hotsite da banca e extraido da PAGINA DO AGREGADOR: e a ponte que leva
  concurso vindo do feed ate o acervo. Cada banca identifica o concurso num
  lugar do endereco - a FEPESE no subdominio, a FCC no caminho -, e entre
  varias telas do mesmo hotsite vale a de caminho mais curto;
- no perfil, campo em branco quer dizer "NAO SEI", e nunca "nao tenho". Sem o
  ano de nascimento, edital com idade maxima nao vira inelegivel: vira
  elegivel com aviso. So barram dois fatos - idade acima do teto declarado e
  nenhuma vaga no nivel que eu tenho;
- escolaridade e piso, nao teto: quem tem superior atende vaga de medio e de
  fundamental;
- CNH avisa mas nunca barra: o edital pede CNH em algumas vagas e nao em
  outras, e o radar guarda um registro por concurso;
- notas sao minhas, como o favorito: a coleta nunca sobrescreve;
- o .ics e montado a mao: o formato e texto puro e nao justifica dependencia.
  Tres detalhes decidem se o arquivo e aceito - CRLF em toda linha, dobra em
  75 BYTES com continuacao comecando por espaco, e evento de dia inteiro
  terminando no dia seguinte;
- o UID do evento vem do endereco do concurso, sempre igual: e assim que o
  calendario atualiza o compromisso em vez de duplicar quando o prazo muda;
- na prova substituta, so entra quem divide ao menos uma PALAVRA com o cargo
  pedido. Banca e municipio sao desempate, nunca motivo de entrada: sem isso,
  "Policia Penal" devolvia Merendeira por ser da mesma banca;
- a lista de parecidas carrega sempre o motivo ("1 palavra em comum no cargo"),
  e nunca afirma equivalencia: Guarda Patrimonial nao e Guarda Municipal;
- retificacao de edital e detectada pelo sha256 que o manifesto ja guardava.
  Depois de acusar, o manifesto E o arquivo em disco passam a valer a versao
  nova - senao toda conferencia repetiria o alarme, e o acervo ficaria com o
  edital velho;
- `radar assuntos` e a UNICA parte paga do radar, e SIMULA por padrao: sem
  --valendo nao gasta nada. O teto e conferido antes de cada lote com o custo
  real que a API informou, e nao com a estimativa;
- a chave da Anthropic so em RADAR_ANTHROPIC_KEY, no .env, como o token do
  Telegram. Nunca no codigo;
- o assunto pago se espalha para as copias do mesmo enunciado: 1.813
  classificacoes atualizam 2.673 linhas;
- `radar atualizar` e o comando do dia a dia: roda coletar, detalhar, baixar
  edital, elegibilidade, retificacao e aviso, nessa ordem - que nao e opcional,
  cada etapa depende da anterior. Etapa que falha nao para a rotina;
- o simulado guarda o estado no BANCO, nao na sessao do navegador: da para
  fechar a pagina no meio e voltar depois, e o F5 nao responde de novo;
- o sorteio do simulado e por ENUNCIADO, nao por linha: dos 5.021 registros so
  1.815 sao perguntas diferentes, e uma aparece em 44 cadernos;
- simulado sem materia escolhida usa as materias que caem em qualquer concurso
  (Portugues, Raciocinio, Informatica, Conhecimentos Gerais). Elas treinam
  mesmo quando nao ha prova do cargo. **Isso mudou para a Policia Penal**: o
  acervo passou a ter os dois cadernos de Agente Penitenciario de SC, o de
  2013 (70 questoes) e o de 2019 (100), mais o de Agente de Seguranca
  Socioeducativo de 2013 e 2016. Guarda Municipal continua sem prova nenhuma;
- nao somar coluna booleana no SQL: o SQLAlchemy devolve a soma com o tipo da
  coluna, entao 2 acertos voltam como True e viram 1. Use `case(...)`;
- orgao estadual de SC tem relevancia propria, `estadual`, e nunca vira
  `nucleo`: a sede e em Florianopolis, mas os polos de prova so saem no
  edital. Ele existe porque `indefinida` enterrava justamente a Policia Penal
  SC, que e o alvo principal. A lista de orgaos e curta e literal (Secretaria
  de Estado, Governo do Estado, Policia Civil/Militar/Penal/Cientifica, Corpo
  de Bombeiros): autarquia e estatal (Celesc, Casan, TJSC) continuam
  `indefinida`, porque incluir por semelhanca seria o chute que a regra existe
  para impedir;
- quem diz que o orgao estadual e de SC e a FONTE, nao o titulo: a FEPESE so
  organiza concurso estadual em SC, entao o coletor dela preenche `uf=SC`
  nesses casos. Conferido nos 520 concursos do historico dela - os 16 de orgao
  estadual sao todos de SC, e o unico fora do estado e municipal. Como a UF
  nasce no coletor, `radar reclassificar` sozinho nao conserta registro
  antigo: precisa de uma coleta antes;
- o tipo `noticia` e decidido primeiro pelo CAMINHO da URL: /concursos/ e
  concurso, /beneficios-sociais/ e noticia. Isso pega o que a palavra no
  titulo nao pega ("INSS paga hoje com vagas para todos").
- o cargo que eu quero fica em `config/alvo.yml`, com a mesma regra de
  `regioes.yml`: nome de cargo nenhum e escrito no codigo. Duas marcas, e elas
  NAO valem a mesma coisa. `principal` e a Policia Penal SC, e ela fura duas
  regras de aviso - o filtro de distancia e o teto de 10 mensagens - e vale
  ate para `noticia`, que normalmente nunca vira aviso: "governo autoriza
  concurso da Policia Penal" e o que eu quero saber antes de todo mundo.
  `secundario` e o resto da lista do CLAUDE.md e so ganha a marca, seguindo as
  regras normais. Nada e descartado por nao ter marca;
- o alvo principal exige PROVA de que o item e de SC, pelo mesmo motivo que o
  anel nao se chuta. Sem a UF na mao, so uma palavra exclusiva vale ("santa
  catarina", "sejuri", "sap/sc"). A sigla solta nao serve: Sao Paulo tem uma
  secretaria SAP, e ela esta no feed;
- a comparacao de termo do alvo e por PALAVRA INTEIRA. Sem isso a sigla "SAP"
  casa dentro de Sapezal, Sapiranga, Massape e SAPE/SC - os quatro estao na
  coleta de verdade, e nenhum tem a ver com o concurso que eu espero;
- a banca do alvo (FEPESE, que fez as duas edicoes: edital 01/2013-SJC/SC e
  001/SAP/2019) NUNCA marca alvo sozinha. Ela faz dezenas de concursos de
  prefeitura por ano; se marcasse, metade de SC viraria alvo principal. Ela so
  entra no motivo, para o aviso lembrar que o padrao de prova ja e conhecido;
- o alvo principal fura o teto de avisos, mas NAO fura a janela de novidade:
  furar as duas faria a primeira coleta despejar o concurso de 2013 no
  celular;
- os tres nomes da secretaria entram juntos no YAML porque o orgao e o mesmo e
  so o nome mudou: SJC em 2013, SAP em 2019 e SEJURI (Secretaria de Estado de
  Justica e Reintegracao Social) hoje - conferido no site oficial em
  22/09/2026, e o dominio antigo sap.sc.gov.br ja serve o conteudo da SEJURI.
  O concurso antigo continua indexado pelo nome da epoca;
- "Policia Penal Federal" e excluida do alvo principal a mao: ela casa com
  "policia penal" e e outro concurso, que tem bloco proprio nos secundarios.
- o acervo deixou de ser so geografico: concurso que bate no alvo principal de
  `config/alvo.yml` entra esteja onde estiver, e entra PRIMEIRO na fila de
  requisicoes. A regra antiga so aceitava `nucleo`, `proximo` e `indefinida`,
  e com isso as duas unicas provas de Agente Penitenciario de SC ficavam de
  fora por serem `estadual`. O acervo existe para mostrar o padrao da banca no
  cargo que eu vou prestar; deixar justamente esse cargo de fora era o acervo
  contrariando o proprio motivo de existir;
- na pagina `?go=provas`, o que nao e gabarito **e** prova. Era o contrario: o
  caderno precisava provar que era caderno, por palavra no rotulo ("caderno",
  "prova") ou por nome de arquivo com nivel e numero ("M1.pdf", "S12.pdf").
  Em 2013 e 2019 o link do caderno se chama so "AP.pdf" e o rotulo e o nome do
  cargo, sem palavra-chave nenhuma - as duas provas eram descartadas na
  leitura da pagina. Quem precisa se identificar agora e a excecao, numa lista
  curta (edital, termo aditivo, cronograma, convocacao...) que nao inclui
  "recurso", porque "Analista de Recursos Humanos" e nome de cargo;
- cada pedaco do caminho do acervo tem teto de 60 caracteres. O titulo do
  concurso de 2013 na FEPESE gruda os quatro cargos num campo so, o que dava
  160 caracteres de nome de pasta e derrubava o download com FileNotFoundError
  no meio da rodada. O Windows para em 260 caracteres no caminho inteiro;
- o caderno da FEPESE tem DOIS desenhos de alternativa, e os dois precisam ser
  lidos: ate 2016 a caixa vinha escrita, "( X )" na certa e "( )" nas outras;
  de 2019 em diante virou simbolo de fonte, que o extrator devolve como
  "Check-square" e "SQUARE". As duas provas de Agente Penitenciario estao uma
  em cada formato;
- quem decide se uma linha repetida e mobilia de pagina e o proprio
  PADRAO_ALTERNATIVA, e nao o nome do simbolo. A protecao antiga procurava
  "SQUARE" e "Check-square", que so existem no caderno novo: no de 2013, a
  alternativa "a. ( ) Sao corretas apenas as afirmativas 1 e 3." se repete
  entre questoes e era apagada como se fosse rodape - a questao chegava ao
  banco com tres alternativas e sem gabarito;
- o numero da questao aceita tres digitos. A prova de 2019 tem 100 questoes, e
  com o teto em dois a de numero 100 era jogada fora;
- o hotsite de 2016 da FEPESE declara `charset=iso-8859-1` e serve os dois
  encodings no mesmo arquivo: "PROVISORIO" em latin-1 e "Seguranca" em UTF-8.
  Nao existe decodificacao unica certa para essa pagina, entao o texto fica
  como o site entrega e o cargo dela aparece com acento quebrado no manifesto.
  Adivinhar byte a byte seria o mesmo chute que a regra do anel existe para
  impedir. Os dois cadernos que importam, 2013 e 2019, vem corretos.
- pagina que declara latin-1 e lida POR BYTE: o que forma UTF-8 valido e
  UTF-8, o byte que sobra e latin-1. Isso corrige o hotsite de 2016 da FEPESE,
  que mistura os dois no mesmo arquivo, sem tocar nos de 2013 e 2019, que sao
  latin-1 honestos e saem identicos. Vale so quando o cabecalho declarou
  latin-1 ou parente - que e onde ha ambiguidade, porque latin-1 aceita
  qualquer byte e nunca reclama nem quando esta errado. Quem declara UTF-8
  fica como esta. **Isto substitui a decisao anterior** de deixar o acento
  quebrado: la a conclusao foi que nao havia UMA codificacao certa para o
  arquivo, o que continua verdade - o que existe e uma leitura certa por byte;
- orgao estadual e reconhecido por duas listas, porque cada fonte titula de um
  jeito. A do codigo pega o nome por extenso ("Secretaria de Estado da..."),
  que e como a FEPESE escreve. A de `config/alvo.yml` pega a SIGLA, que e como
  o agregador escreve ("SEJURI SC divulga novo edital") - e sigla nenhuma casa
  com "secretaria de estado", entao os dois concursos da SEJURI ficavam em
  `indefinida` mesmo com uf=SC. A comparacao por sigla e por palavra inteira,
  senao "SAP" casaria dentro de "SAPE/SC", que e a Secretaria da Agricultura.
