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
  nem distancia, nem salario, nem prazo vencido. Os favoritos tinham um mural
  fixo a esquerda; na etapa 8 eles ganharam a aba Acompanhando, e a promessa
  passou para a consulta (veja o fim deste arquivo);
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
- a tabela `eventos` guarda a linha do tempo, porque o resto do banco guarda so
  o AGORA: quando a situacao muda, o valor antigo e sobrescrito e ninguem
  lembra que ele existiu. Sem isso nao da para responder "quando foi que essa
  inscricao abriu?" nem "esse edital ja tinha sido retificado antes?" - e o
  caminho e o que ensina, mais que o estado de hoje;
- o evento aponta o concurso pela URL, e nao pelo id: a url e a chave natural
  do projeto, e o id muda quando o banco e reconstruido a partir de
  `data/concursos.json`. Evento amarrado a id nao sobreviveria a um
  `radar importar`;
- quem grava o evento sao os pontos do servico onde o campo MUDA de valor, e
  nao um gatilho generico. Em `_gravar` a situacao anterior e guardada antes de
  qualquer escrita e comparada no fim: ela pode mudar por dois caminhos - o
  valor que a fonte manda e a fase que o classificador le no titulo - e
  comparar no fim pega os dois sem espalhar registro pelo meio da funcao;
- abrir e fechar inscricao tem tipo proprio (`inscricoes_abertas` e
  `inscricoes_encerradas`) em vez do generico `mudou_situacao`: sao os dois
  momentos que eu de fato preciso achar depois, e o resto do ciclo e tramite;
- o evento de "apareceu" diz tambem em que situacao o concurso chegou.
  Concurso raramente entra no radar no comeco da vida: quando o radar ligou,
  muita coisa ja estava com inscricao aberta, e a linha do tempo comecaria
  dizendo so "apareceu", sem dizer em que pe;
- `registrar()` recebe a sessao de quem chama, em vez de abrir a propria: o
  evento tem que entrar no mesmo commit da mudanca que o gerou. Se a coleta
  falhar no meio, nao pode sobrar evento de uma mudanca que nao foi gravada;
- a linha do tempo NAO foi preenchida retroativamente para os 2.790 concursos
  que ja estavam no banco. Nenhum deles tem data de quando apareceu, e inventar
  uma seria o mesmo chute que a regra do anel existe para impedir. A tabela
  comeca a valer da primeira coleta em diante;
- o evento `prova_marcada` esta pronto e ligado no upsert, mas nao dispara
  hoje: nenhuma fonte do projeto preenche `data_prova`. A coluna existe e o
  calendario a le, mas so seria preenchida por uma fonte que ainda nao temos.
- a navegacao tem quatro destinos fixos no topo - Meu foco, Concursos,
  Acompanhando, Estudar - e um menu "Mais" com Previsao e Calendario. A regra
  para decidir onde cada coisa fica: o que eu abro todo dia fica na barra, o
  que eu abro de vez em quando fica no "Mais". Antes eram onze links na mesma
  linha, misturando filtro de anel com pagina inteira, e nada tinha hierarquia;
- a barra e a mesma em TODA pagina. Antes cada uma tinha so um "voltar ao
  radar": ir de Macetes para o Calendario custava dois cliques e uma parada na
  home. O estilo dela vive em `_topo_estilo.html` e o markup em `_topo.html`,
  separados porque um vai no <head> e o outro no <body>;
- Macetes e Simulado viraram as duas faces de **Estudar**, e `/estudar` abre
  em Macetes: ver o que a banca cobra e o passo que decide o que treinar
  depois. As duas paginas continuam existindo nas mesmas URLs;
- Meu foco e Acompanhando entram em construcao, com pagina propria. Elas ja
  ocupam lugar no menu porque a posicao delas na navegacao esta decidida -
  mudar navegacao depois custa mais do que deixar a porta aberta agora;
- em Concursos a busca vem ANTES dos atalhos: e o que resolve o caso que
  atalho nenhum resolve. Os atalhos sao quatro - Perto, Estadual SC, Abertos,
  Todos. Longe, A confirmar, o mural e a busca em tudo desceram para "mais
  filtros": continuam a um clique, mas nao competem por espaco com o que eu
  abro todo dia;
- "mais filtros" nasce fechado, e abre sozinho quando ha filtro ligado. Filtro
  escondido E ligado seria a pior combinacao: a lista viria curta e a tela nao
  diria por que. Quando abre sozinho, mostra a marca "ligado";
- o cartao mostra titulo e uma linha so: **onde, salario, prazo**. Sao as tres
  perguntas que eu faco antes de decidir se abro o concurso. Banca, tipo,
  exigencias do edital, motivo da classificacao e a minha anotacao ficam em
  "detalhes", fechado. A versao anterior usava um selo por informacao, e o
  cartao virava um paragrafo de selos onde nada se destacava;
- "detalhes" fechado continua com o conteudo no HTML, entao o Ctrl+F do
  navegador continua achando banca e motivo. Isso e proposital: esconder da
  vista nao pode virar esconder da busca;
- a cidade e o unico item da linha sem rotulo. Ela abre a linha, e ali e o
  unico item que pode ser nome de lugar - rotular seria repetir o obvio numa
  linha que precisa caber inteira;
- a lista mostra 30 cartoes por vez, com "ver mais" de 30 em 30. A consulta
  pede um a mais do que vai para a tela: e assim que se sabe se ha proxima
  pagina sem fazer uma segunda consulta so para contar. `mostrar` menor que 30
  e ignorado, senao URL editada a mao deixaria a pagina com um cartao so;
- o mural lateral fica como esta por enquanto. Ele e o embriao de
  "Acompanhando", e move-lo antes de a secao existir seria refazer duas vezes.
- **Meu foco e a home.** A lista de concursos foi para `/concursos`. A lista
  responde "o que existe?"; o foco responde "o que esta acontecendo com o
  concurso que eu espero?", e essa e a pergunta que eu faco todo dia. O
  endereco antigo `/foco` continua levando para la;
- a tela de foco nunca afirma o que nao sabe. Toda funcao de `foco.py` devolve
  None, lista vazia ou campo nulo quando o dado nao existe, e a tela escreve
  "nao sei ainda" com cara propria - marca amarela, para nunca parecer um
  dado. Dado errado sobre o meu proprio concurso e pior que tela vazia: eu
  estudaria a materia errada, ou deixaria de estudar achando que ha tempo;
- a banca e **hipotese** enquanto nao ha edital aberto DO CARGO. A frase sai
  pronta de `Banca.como_hipotese` - "hipotese: FEPESE, que fez 2013 e 2019" -
  e os anos vem do acervo, nao do YAML: e prova de que aquela banca fez aquele
  ano, e nao anotacao minha que pode ter envelhecido;
- **bater no alvo pelo nome do ORGAO nao e o mesmo que bater pelo CARGO.**
  "SEJURI SC divulga novo edital com vaga para Medico" bate no alvo, e e certo
  que bata - e a secretaria que eu acompanho. Mas anunciar "edital aberto" por
  causa disso seria dizer o que nao e. A tela separa os dois: edital aberto do
  cargo, e um aviso a parte para o que e da casa mas de outro cargo. Pelo
  mesmo motivo, so edital do cargo confirma banca;
- o quadro de materias sai do PDF do edital, e nao das provas. Sao coisas
  diferentes e a tela mostra as duas lado a lado: o edital diz o que PROMETE
  cobrar, a prova diz o que CAIU. Onde batem, o peso e regra; onde discordam,
  e sinal de que a prova mudou de uma edicao para a outra;
- o quadro so vale se fechar a conta. `edital_materias.ler_quadro` confere a
  soma das materias contra o total declarado pelo proprio edital e devolve
  lista vazia se nao bater - ler metade do quadro e pior que nao ler, porque
  eu estudaria com pesos errados sem nunca desconfiar;
- as materias que cairam na prova mas nao estao no quadro do edital aparecem
  numa linha a parte, e nao somem. Sumir seria esconder que a prova mudou: em
  2013 caiu Nocoes de Informatica e Direito Administrativo, que o edital de
  2019 nao lista;
- o filtro de CARGO passou a ignorar acento, como o de titulo ja fazia. O
  cargo vem acentuado do rotulo do hotsite ("Agente Penitenciario") e o termo
  com que eu procuro vem sem: com ilike puro, `--cargo "agente penitenciario"`
  devolvia ZERO das 170 questoes que existem. Isso valia para o sorteio do
  simulado e para `radar padrao`, nao so para a tela nova;
- o botao "treinar 20 questoes" sorteia pelo primeiro termo do alvo que de
  fato acha prova no acervo - hoje "agente penitenciario", o nome ANTIGO do
  cargo. "policia penal" nao casa caderno nenhum, porque as duas provas que
  existem sao anteriores a mudanca de nome;
- a validade aparece como o edital escreve, e nao resumida: "2 anos a contar
  da homologacao do resultado, prorrogaveis por mais 2". Saber o PRAZO nao e
  saber ate quando - a homologacao sai no Diario Oficial do Estado, que este
  projeto nao le por causa do robots.txt. Por isso a tela diz, junto, "quando
  comeca a contar: nao sei ainda".

## Etapa 8: a aba Acompanhando

- **o mural lateral saiu.** Ele resolvia "nao me deixe perder isso de vista",
  mas nao resolvia "e agora, o que eu faco?": cabia em qualquer aba e nao
  cabia nada dentro dele. Os favoritos foram para a aba Acompanhando, onde
  cada um tem espaco para a linha do tempo inteira e para a proxima acao;
- **a promessa "nenhum filtro esconde favorito" virou consulta, nao tela.**
  Era o mural que a cumpria; sem isso, ela passaria a valer so dentro de
  Acompanhando. Agora `listar()` deixa o favorito escapar dos recortes que eu
  NAO pedi - o anel padrao da tela e a faixa de remuneracao;
- **o escape nao cobre pergunta explicita.** Quem digita "Palhoca", escolhe um
  anel a dedo ou abre "Abertos" esta perguntando, e a resposta nao pode vir
  com um favorito de Itajai no meio - senao o filtro deixa de responder. A
  linha que separa os dois e simples: recorte padrao escapa, filtro digitado
  nao;
- **a proxima acao e derivada, nunca adivinhada.** E o unico campo
  interpretado da tela, e sai sempre de dois fatos gravados: a situacao e o
  prazo. Prazo correndo vence qualquer outra coisa, porque e o unico que tem
  hora para acabar. Situacao que nao diz nada vira "nao sei ainda", pela mesma
  regra de `foco.py`: dado errado sobre o meu proprio concurso e pior que tela
  vazia;
- **quando a situacao e a data se contradizem, manda a data.** "Inscricoes
  abertas" com prazo vencido nao vira "faltam -3 dias": vira "conferir na
  fonte: o prazo que eu tenho ja venceu, mas o registro ainda diz aberto". Eu
  prefiro saber que o registro esta velho;
- **so cinco tipos de evento tocam o celular**, e so de favorito:
  `edital_publicado`, `edital_retificado`, `inscricoes_abertas`,
  `inscricoes_encerradas` e `prova_marcada`. O corte e por consequencia, nao
  por raridade - estes cinco mudam o que eu tenho que FAZER. "Apareceu" e "de
  prevista para autorizado" ficam na linha do tempo, para eu ler quando
  quiser. Por causa disso, `edital_publicado` deixou de cair no generico
  `mudou_situacao` e ganhou tipo proprio;
- **o aviso de favorito e outro aviso**, em funcao separada
  (`servico.avisar_favoritos`). O `avisar()` responde "apareceu algo que pode
  me interessar?" e por isso filtra por distancia; este responde "mudou algo
  no que eu JA seguo?", e para essa pergunta filtro nenhum faz sentido. Ele
  roda ANTES do outro no `radar atualizar`: se o teto do dia cortar alguma
  coisa, que corte a descoberta, e nao a mudanca no meu favorito;
- a fila de aviso e por EVENTO, nao por concurso: a coluna `eventos.avisado_em`
  existe pelo mesmo motivo que `concursos.avisado_em` - a coleta de amanha nao
  pode repetir o aviso de hoje. E so marca o que realmente saiu, para Telegram
  fora do ar deixar a fila em pe em vez de sumir com a mudanca.

## Etapa 9: estudar pelo alvo

- **os `termos` do `config/alvo.yml` sao sinonimos do cargo**, e nao so
  padroes para reconhecer o feed. Eles resolvem um caso que nenhuma regra de
  semelhanca de texto resolveria: as duas provas que eu tenho estao
  catalogadas como "Agente Penitenciario", o nome de 2013 e 2019, e o cargo
  hoje se chama "Policial Penal" - os dois nomes nao dividem uma palavra
  sequer. Vale para o alvo principal e para os secundarios;
- **o sinonimo tem que caber INTEIRO no cargo do acervo.** "Agente
  Penitenciario - Feminino (AP)" tem as duas palavras de "agente
  penitenciario" e e a mesma profissao; "Agente Administrativo" tem so
  "agente" e nao e. Sem a exigencia do sinonimo completo, todo "Agente" do
  acervo entraria na lista de provas parecidas;
- **o treino do alvo tem ordem de preferencia, e ela e o conteudo da etapa:**
  primeiro as questoes das provas do proprio cargo, que sao a prova de
  verdade; quando elas acabam, as da mesma banca NAS MESMAS MATERIAS, em
  outros concursos; so entao repete o que eu ja respondi, avisando que
  repetiu. Sao 160 enunciados distintos do cargo contra 356 da banca: oito
  rodadas de 20 acabam com os primeiros;
- **"acabar" e por enunciado ja respondido**, em qualquer simulado, e nao por
  id de questao. A mesma pergunta aparece em varios cadernos, e reve-la com
  outro numero nao seria questao nova;
- **a materia e o que limita a segunda fonte.** Das 7.046 questoes da FEPESE
  em outros cargos, entram as 2.129 das materias que cairam na minha prova.
  "Conhecimentos Especificos" de Merendeira e da mesma banca e nao me serve de
  nada;
- as materias da segunda fonte saem das PROVAS do cargo, e nao do quadro do
  edital. E de proposito: o quadro depende do PDF estar no acervo e legivel, e
  o sorteio nao pode depender disso. A consequencia conhecida e que Nocoes de
  Informatica entra - ela caiu em 2013 e saiu do edital de 2019 - e a propria
  tela mostra esse desencontro, na linha "caiu na prova mas nao esta no
  edital";
- **a rodada registra de onde cada questao veio** (`Simulado.filtros`), e a
  tela diz. Acertar 70% nas questoes da minha prova nao e a mesma coisa que
  acertar 70% em prova de outro cargo da mesma banca;
- **materia de maior peso e a que esta acima da media da propria prova**
  (total de questoes dividido pelo numero de materias). O corte nao e um
  numero que eu escolhi: ele se ajusta sozinho quando o edital muda. No de
  2019 sao sete materias, que valem 80 das 100 questoes;
- **o destaque aponta a pior entre essas**, e nao a pior de todas: errar numa
  materia de 5 questoes custa 5 questoes; errar numa de 15 decide a prova.
  Empate de porcentagem desempata pela materia mais feita - entre 50% em duas
  questoes e 50% em trinta, a segunda e a que eu sei que e verdade;
- **materia nunca treinada nao vale zero por cento.** Ela aparece como "nao
  treinei" e NAO concorre ao destaque: zero diria que eu errei tudo, quando o
  que houve foi eu nao ter feito. E a mesma regra de nunca inventar que vale
  para o resto da tela de foco.

## Etapa 10: o servico virou pacote

- **`servico` e um pacote, e a fachada continua sendo o `servico`.** Cada
  assunto tem arquivo proprio - `coleta`, `avisos`, `provas`, `simulado`,
  `previsao` - e o `__init__` reexporta todos. Quem chama escreve
  `servico.coletar_tudo(...)` como sempre escreveu: a CLI, a web e os testes
  nao mudaram uma linha por causa da divisao;
- **o `comum.py` so recebe o que JA era compartilhado** por mais de um
  assunto. Ele nao e o quarto de despejo do que nao tem casa - a unica coisa
  pior que um arquivo de 2.700 linhas sao dois arquivos com a mesma funcao
  copiada dentro;
- **modulo do radar que tem o mesmo nome de um submodulo entra apelidado.**
  Dentro de `servico/provas.py`, `provas.baixar(...)` nao se le - virou
  `arquivos_de_prova.baixar(...)`. O mesmo no `__init__`, e ali nao e so
  estetica: com `servico/provas.py` existindo, o atributo `servico.provas`
  passa a ser o submodulo e apaga o `from radar import provas`;
- **teste que troca um global tem que trocar onde ele e LIDO.**
  `servico.COLETORES` e `servico.Buscador` viraram copias reexportadas;
  quem le e `servico.coleta` e `servico.provas`. Trocar a copia deixaria o
  teste verde sem testar nada. Trocar atributo de CLASSE (como
  `servico.Buscador.get`) continua valendo de qualquer lado.

## Consertos achados na revisao das etapas 8 a 10

- **a situacao que a FONTE manda nao desmente o prazo.** A regra ja existia
  para a fase lida do titulo ("data de inscricao e fato, titulo e
  interpretacao") e agora vale tambem para o campo que o coletor envia. Sem
  ela o radar entrava em looping: o Concursos no Brasil marca
  "edital_publicado" em todo item, a coleta gravava isso por cima de um
  concurso encerrado e o `atualizar_situacoes` da mesma rodada desfazia - dois
  eventos por coleta, todo dia, e desde a etapa 8 duas mensagens no Telegram.
- **sinonimo de cargo vale so para o alvo PRINCIPAL.** Nos blocos secundarios
  os `termos` nomeiam a carreira, e nao um cargo: a Policia Civil lista
  delegado, escrivao, investigador e agente, que sao quatro provas
  diferentes. Chamar a prova de Delegado de "o mesmo cargo com outro nome" que
  a de Agente seria a equivalencia falsa que a prova substituta existe para
  nao fingir. E a lista `exclui` vale aqui como vale no resto: "Policia Penal
  Federal" contem "policia penal" e e outro concurso.
- **o evento de prazo tem o tipo que a DATA manda.** `registrar_prazo` sempre
  gravou `inscricoes_abertas`, mesmo lendo um edital cujo prazo ja tinha
  vencido - a propria docstring dizia que isso acontece. Virava um
  "inscricoes abertas" verde no Telegram para concurso fechado, que e o tipo
  de aviso que faz eu parar de confiar nos avisos;
- **aviso de evento tambem tem janela de novidade** (30 dias, a mesma do
  aviso de concurso). Marcar a estrela hoje num concurso cujo edital saiu ha
  tres semanas nao pode despejar a historia dele no celular;
- **`enviar_varios` devolve uma resposta por mensagem, e nao a contagem.**
  Com a contagem, quem chamava marcava como avisadas as N primeiras: falhando
  a do meio, ela ficava marcada como enviada - sumia para sempre - e a que
  saiu voltava no dia seguinte.
- **plural de cargo entra escrito no `alvo.yml`**, e nao por regra de
  linguagem. A comparacao e por palavra inteira - de proposito, porque e ela
  que impede "SAP" de casar dentro de "Sapezal" - e por isso "policial penal"
  nao acha "policiais penais". Noticia sobre concurso quase sempre fala no
  plural ("600 policiais penais"), e noticia e justamente o que chega antes do
  edital. O plural de "penal federal" entrou junto na exclusao, senao o
  concurso federal no plural viraria o meu alvo.

## Etapa 11: um lugar so manda mensagem

- **quem avisa e o robo do GitHub, e ele e o unico.** `radar atualizar` roda
  calado por padrao (`--avisar` manda daqui assim mesmo). Com os dois
  avisando, o mesmo concurso chegava duas vezes no celular: cada ponta
  guardava a sua propria lista do que ja tinha avisado, e elas so se
  encontravam quando eu lembrava de exportar e importar na mao;
- **a linha do tempo viaja em arquivo proprio**, `data/eventos.json`, ao lado
  do `concursos.json`. Sao coisas diferentes - um e o AGORA de cada concurso,
  o outro e o caminho que ele percorreu - e juntos, cada evento novo
  reescreveria a linha inteira do concurso no diff;
- **a identidade do evento sao quatro campos**: concurso, tipo, data e
  descricao. O `id` nao serve, porque e autoincremental e cada maquina numera
  do seu jeito - o meu evento 7 e o do robo sao coisas diferentes. Sem isso,
  cada importacao dobraria a linha do tempo;
- **`radar sincronizar` faz pull, importar, RECLASSIFICAR, exportar, commit e
  push, nesta ordem**, e a ordem e o conteudo da decisao. Importar antes de
  exportar e o que traz o `avisado_em` do robo para o meu banco antes de eu
  escrever o JSON de volta; na ordem inversa eu apagaria as marcas dele, e ele
  mandaria tudo de novo no dia seguinte. Ele nao resolve conflito de rebase e
  nao encosta em arquivo que nao seja os dois JSON;
- a CLI passou a chamar `git` por subprocess, o que ate aqui so acontecia no
  workflow em bash. E o preco de ter um comando so, e fica contido numa funcao
  de quatro linhas.

## Quem e dono do favorito e da nota

- **`interesse` e `notas` tem dono, e o dono e a minha maquina.** So eu mexo
  neles, pela web ou pela CLI; o robo do GitHub nunca escreve um favorito nem
  uma nota - ele so carrega os meus de um lado para o outro. Por isso o
  `radar importar` nao atualiza esses dois campos em concurso que ja existe
  aqui: o banco local e a verdade, e o JSON e uma copia possivelmente velha;
- a regra anterior era mais fraca - "valor vazio nao apaga" - e tornava
  **impossivel desmarcar**. O `radar sincronizar` faz pull, importar,
  exportar: eu tirava a estrela, o importar encontrava o JSON que ainda a
  tinha, e ela voltava. Toda sincronizacao ressuscitava o que eu tinha acabado
  de desmarcar;
- **eles sao escritos numa situacao so: quando o concurso nao existe no banco
  local.** E o computador novo, ou a reinstalacao - ali o JSON e tudo que
  existe, e e dele que os meus favoritos voltam. E tambem o caso do robo, que
  comeca sem banco todo dia: e assim que ele fica sabendo quais sao os meus
  favoritos para poder avisar sobre eles;
- `salario_manual` e `municipio_confirmado` continuam na regra mais fraca:
  eles acompanham campos que a coleta escreve (o salario e o municipio), e
  para eles "valor vazio nao apaga" basta.

## PDF que nem abre

- **arquivo corrompido nao derruba a rodada.** Download interrompido deixa no
  disco meio PDF, e o leitor estoura `PdfStreamError` na primeira pagina.
  Antes, o primeiro arquivo cortado matava o `radar elegibilidade` inteiro, e
  os outros 36 concursos da fila ficavam sem ser lidos por causa de um. Agora
  a leitura de cada edital e isolada: o que falhar e contado e a rodada segue;
- **o arquivo quebrado e registrado pelo NOME**, no log e no resumo, e nao so
  contado. O numero sozinho nao diz qual apagar para baixar de novo;
- "corrompido" e "so em imagem" ficam em contagens separadas, porque pedem
  coisas diferentes: o primeiro se resolve apagando o arquivo e rodando
  `radar provas` de novo, e o segundo nao se resolve - edital publicado como
  imagem nao vira texto.

## O sincronizar reclassifica

- **o `reclassificar` roda DENTRO do `radar sincronizar`**, entre o importar e
  o exportar. Sem isso, mudar `config/regioes.yml` ou `config/alvo.yml` nao
  adiantava nada: eu reclassificava, sincronizava, e o importar trazia de
  volta o JSON com a classificacao velha - desfazendo na hora o que eu tinha
  acabado de corrigir. Nao era so o caso do acento: vale para municipio novo
  num anel, cargo novo no alvo, qualquer regra;
- **a posicao e a unica que funciona.** Antes do importar, o JSON velho
  passaria por cima do que acabou de ser calculado; depois do exportar, o
  arquivo ja teria saido com a regra antiga. Tem teste so para a posicao, alem
  do que reproduz o caso inteiro: grafia velha no JSON, sincronizar, grafia
  nova sobrevive - no banco e no arquivo que vai para o robo;
- reclassificar nao vai a internet e so reescreve campo derivado (relevancia,
  motivo, municipio canonico, marca de alvo). Os campos meus e o que a coleta
  trouxe nao sao tocados, entao rodar sempre sai barato e nao tem risco.

## A trava do municipio confirmado protege o municipio, e so ele

- **`municipio_confirmado` trava o MUNICIPIO; o anel e o motivo sao conta.**
  A pagina do edital sabe mais que o titulo sobre ONDE o concurso e - essa e
  a razao da trava, e ela continua. Mas em qual anel aquele municipio cai, e
  por que, e conta feita em cima do `config/regioes.yml`, e conta se refaz;
- protege-los junto era demais, e o caso que mostrou isso: tirando Blumenau
  do anel `proximo`, os concursos cuja lotacao a pagina tinha confirmado
  continuavam `proximo` - para sempre, porque nada os revisita. Ficavam 34
  concursos presos na regra do dia em que a pagina foi lida;
- **o motivo continua dizendo de onde veio o municipio** ("aparece como
  lotação na página do edital"), porque e essa informacao que me deixa
  auditar a classificacao depois. O que mudou e que ele passa a ser reescrito
  com a regra de hoje, em vez de congelado;
- a frase mora numa funcao so (`_anel_da_lotacao`), usada pelo `detalhar` e
  pelo `reclassificar`. Duas copias da mesma frase divergem: foi assim que 34
  registros ficaram sem acento enquanto 2.768 tinham sido corrigidos.

## Uma grafia so para cada cidade, inclusive fora dos aneis

- **para quem esta nos aneis manda o `config/regioes.yml`; para o resto,
  manda o proprio banco.** Cada fonte digita de um jeito, e o banco tinha
  "Caçador" e "Cacador", "GASPAR" e "Gaspar", "Araranguá" e "Ararangua" - dez
  cidades escritas de dois jeitos, todas fora dos aneis, onde nao ha lista
  para consultar;
- a escolha e por nota, nesta ordem: **acento vence tudo**, porque ele e
  informacao ("Caçador" sem cedilha e a mesma cidade escrita pior); depois
  **caixa normal**, que descarta o "GASPAR" que a fonte manda em maiuscula;
  depois a mais frequente; e por fim a ordem alfabetica, para duas execucoes
  darem o mesmo resultado. O acento vence mesmo sendo minoria - "Chapeco"
  aparecia 15 vezes e "Chapecó" uma so;
- isto e **cosmetico**. Duas grafias do mesmo lugar nunca confundiram a
  classificacao, porque toda comparacao passa por `normalizar`. O que elas
  estragavam era a leitura: a mesma cidade aparecia duas vezes na tela.

## Meu foco guarda o que leu do edital, em vez de reler o PDF

- **o edital e lido uma vez e o resultado fica em `data/edital_do_alvo.json`.**
  A aba relia o PDF de 2019 inteiro a cada abertura, e duas vezes: uma para o
  quadro de materias, outra para a validade. Sao dois segundos por leitura, e
  a aba abria em 4,4 segundos. Depois, 0,06;
- **quem decide se vale reler e o sha256 que o manifesto ja guardava**, e nao
  a data nem o nome do arquivo. Edital publicado nao se reescreve: mesmo
  arquivo, mesma resposta. Se uma retificacao trocar o PDF, o hash muda e a
  leitura acontece de novo - que e exatamente o caso em que reler importa;
- o arquivo e **cache, e por isso nao vai para o git**: apagar nao perde nada,
  o radar le o PDF outra vez. O que e versionado continua sendo o manifesto,
  que e a receita. Arquivo corrompido tambem nao quebra a tela - vale como
  "nao tenho";
- **o total de questoes e somado na hora, e nao guardado.** Um total que
  discordasse das materias seria numero orfao, e o quadro so vale quando
  fecha a conta;
- as tres contas do cargo tambem pararam de varrer o acervo. Elas carregavam
  as 8 mil questoes para filtrar em Python as 170 minhas, tres vezes por
  abertura. Agora **"que provas sao minhas?" e perguntado uma vez**, sobre as
  ~200 provas distintas, e o resto consulta o banco so por elas.

## Prova so conta como minha se for o meu cargo E o meu estado

- **`exclui` e `uf` do `config/alvo.yml` passaram a valer tambem no acervo.**
  A tela de foco comparava so os `termos`, e por isso uma prova de "Policial
  Penal Federal" - que contem "policial penal" - entrava nas contas como se
  fosse minha, e uma prova de Policia Penal do Parana tambem. Sao o mesmo
  cargo e outro concurso: outra banca, outro programa, outra prova. Estudar
  pelo peso delas e estudar a materia errada;
- **quem sabe a UF da prova e o concurso que a originou**, e e por isso que a
  consulta alcanca a tabela de concursos. A regra de estado e a mesma da
  coleta, e mora em `alvo.e_do_estado_do_principal`: com UF ela manda; sem
  UF - a FEPESE e a IESES nao informam - decide uma palavra da lista
  `prova_de_sc`, nunca a sigla solta;
- **prova que nao chega a um concurso conhecido fica de fora.** Sem ele nao ha
  como provar o estado, e contar assim mesmo seria chutar - a mesma regra do
  anel de distancia;
- quem responde "e o meu cargo?" passou a ser `alvo.sinonimos_do_cargo`, que
  ja tratava os `termos` como nomes do mesmo cargo e ja aplicava o `exclui`.
  Uma regra, um dono: o arquivo que le o `alvo.yml`;
- **o sorteio do treino ainda nao aplica as duas regras.**
  `servico/simulado.py` usa `nomeia_cargo_do_principal`, que so olha os
  `termos`. No acervo de hoje da no mesmo - as duas unicas provas do cargo
  sao de SC - mas a falha existe e esta anotada aqui para nao se perder.

## Policia Penal de qualquer estado avisa; so a de SC entra no estudo

- **as duas perguntas que eu faco sobre esse cargo tem respostas diferentes, e
  por isso agora sao duas marcas.** "Quero saber?" e sim em qualquer estado:
  outra banca abrindo Policia Penal e noticia que eu quero na hora. "Quero
  estudar por essa prova?" e nao fora de SC: e outra banca, outro conteudo
  programatico e outra lei estadual - estudar por ela e estudar a materia
  errada;
- a marca nova e **`principal_fora`**. Ela avisa igual ao `principal`: sirene,
  sem filtro de distancia, sem teto, valendo ate para noticia. E ela nao
  aparece em nada que seja estudo - Meu foco, incidencia, treino e acervo
  continuam lendo `principal` sozinho, que e o que ja significava "o meu
  concurso";
- **o que relaxou foi so o cargo, e so ele.** Os `orgaos` do YAML continuam
  exigindo prova de SC, porque sigla nao prova estado: "SAP" tambem e o nome
  de uma secretaria de Sao Paulo, e "SAP SP abre estagio" esta no feed de
  verdade. Sem essa trava, cada post da SAP paulista viraria sirene;
- **sem prova de estado tambem cai em `principal_fora`**, e nao em nada. Antes
  a duvida apagava a marca inteira; hoje ela apaga so a metade que exige
  prova. Nao saber de onde e nunca foi motivo para perder a noticia - e
  continua nao sendo motivo para chamar a prova de minha;
- Policia Penal Federal segue no lugar dela, como alvo secundario: `exclui`
  roda antes de tudo, e ela tem bloco proprio. Policia Civil segue como
  estava, no radar e sem destaque.

## "De olho": duas Guardas que furam o teto sem virar alvo

- **Guarda Municipal de Florianopolis e de Balneario Camboriu sao as unicas
  que eu prestaria de fato**, e elas estavam se perdendo no meio das dezenas
  de Guardas que aparecem por ano. Agora o bloco secundario aceita uma lista
  `de_olho` com cidades, e quem bate nela **fura o teto de mensagens do dia** e
  ganha um cartao na home;
- **isso nao promove o cargo a alvo principal, de proposito.** Guarda Municipal
  em Florianopolis continua sendo Guarda Municipal: nao entra no estudo, que e
  do cargo que eu vou prestar. O que muda e o teto, e mais nada - nem o filtro
  de distancia precisou mudar, porque as duas cidades ja estao nos aneis;
- o aviso leva 👀 no lugar da sirene. **Sao dois niveis porque sao duas
  coisas**: o concurso que eu espero ha anos, e um cargo secundario numa cidade
  que me serve. Um emoji so acabaria com a diferenca que a sirene existe para
  marcar;
- **a cidade vale tambem quando so o campo `municipio` a traz.** O titulo da
  FEPESE e "2026 - Prefeitura Municipal de Florianopolis", e o cargo vem colado
  depois; quem extraiu a cidade foi o classificador, uma linha antes. Por isso
  o `marcar` passou a receber o municipio - e e o unico lugar em que a cidade
  decide alguma coisa na marca de alvo;
- **o cartao mostra as duas cidades sempre**, inclusive a que nao tem nada no
  radar. Sumir com a linha vazia responderia "nao ha concurso" a uma pergunta
  que ninguem fez: o que eu sei e que nada apareceu. Entre dois concursos da
  mesma cidade, ganha o que nao esta encerrado - uma noticia de ontem sobre a
  edicao velha nao pode esconder a inscricao que esta aberta.

## O caderno da FEPESE traz o gabarito PROVISORIO

- **o caderno de prova marca a alternativa certa dentro do proprio PDF**, e
  era de la que o acervo tirava o gabarito. So que esse arquivo e publicado no
  dia seguinte a prova, **antes dos recursos**. No concurso de 2019 o
  definitivo **anulou 5 questoes e trocou a letra de outras 4**, em 100 -
  treinar pelo caderno era marcar como erro 4 respostas certas minhas e
  perseguir 5 questoes que nao tem resposta;
- **o definitivo nao esta em `?go=provas`**, que e a pagina que o acervo lia.
  Ele e anunciado na lista de avisos da **capa** do hotsite, e por isso a capa
  virou a terceira pagina lida por concurso. O que entra dali e so o link cujo
  rotulo diz "gabarito definitivo", fora os de outra fase (curso de formacao,
  recuperacao, capacidade fisica), que sao outra prova;
- **a data do aviso vem da celula ao lado do link, e ela decide qual vale**: em
  2019 saiu o definitivo em 13/12 e, em 23/01 do ano seguinte, a retificacao
  que anulou a questao 33. Aplicando na ordem da data, o ultimo e o que fica -
  e a retificacao tambem DESmarca anulacao, para uma questao que voltasse nao
  ficar anulada para sempre;
- **um PDF traz varios cargos.** O de 2013 tem "AP - Agente Penitenciario" e
  "AS - Agente de Seguranca Socioeducativo", cada um numerado de 1 a 70: lidos
  juntos viravam uma grade de 73 questoes que nao era de cargo nenhum. O que
  separa as duas e a numeracao voltar ao 1;
- **grade que nao passa nas tres conferencias e ignorada em silencio**: mesmo
  numero de questoes, e a sigla batendo com o nome do caderno (AP -> AP.pdf)
  ou o cargo aparecendo no cargo do caderno. Aplicar a grade do cargo errado
  trocaria as 100 respostas de uma vez, e ficar com o provisorio e menos pior;
- **a correcao e aplicada na LEITURA do caderno, e nao no banco.** Assim ela
  vale tambem quando eu refaco a extracao do zero, em vez de ser um conserto
  que se perde na proxima vez;
- **questao anulada nao conta em lugar nenhum**: nem no treino (ela ficou sem
  resposta), nem na incidencia, nem na cobertura, nem na fila da classificacao
  paga. A banca desfez a pergunta;
- **`radar provas --revisitar`** existe por causa disto. A regra antiga era
  "concurso que ja esta no acervo nao e lido de novo", e ela parte de que o
  hotsite nao muda depois da prova - o que e falso: o gabarito definitivo saiu
  dias depois do caderno, e a retificacao um mes depois disso.

## O assunto do meu cargo sai do conteudo programatico do edital

- **a IA escolhe dentro de uma lista, em vez de inventar um nome.** A lista sai
  do ANEXO 1 do edital de 2019 - 85 assuntos em 11 materias - e o que vem fora
  dela e descartado no proprio codigo, e nao so pedido na instrucao. Rotulo
  inventado no meio dos do edital seria pior do que a questao ficar sem
  assunto: eu nao distinguiria os dois na tela;
- **o texto e o do edital, defeitos inclusive.** Ele escreveu "Acao penal;
  especies", e por isso "especies" aparece sozinho na lista; escreveu "Decreto
  º 7.037/2009" sem o "n", e assim fica. Consertar na mao seria eu decidindo o
  que a banca quis dizer - e o nome so serve se for o mesmo que o edital usa;
- **o anexo exige o outro modo de extracao do pypdf.** No modo normal o texto
  justificado volta com espaco no meio das palavras ("cidad ania", "envol
  vendo", "desp orto"), e assunto com palavra partida nao serve para nada. Por
  isso `extrair_texto` ganhou `layout=True`, usado so aqui;
- **onde um assunto acaba**: no ponto-e-virgula sempre, e no ponto so quando o
  proximo comeca com maiuscula ou numero. As duas excecoes sao do proprio
  edital - "Lei n.º 7.210" tem tres pontos dentro e e um assunto so, e
  "Processos. dos crimes de responsabilidade" tem um ponto que e engano dele;
- **`--so-alvo` classifica so as questoes das minhas provas**: 99 em vez de
  2.802, estimados US$ 0,03 em vez de US$ 0,40 (estimativa - este comando
  nunca chegou a rodar valendo). Nao e economia pela economia - assunto
  fino de prova de Merendeira e da mesma banca e nao me serve de nada. Materia
  que saiu do programa entre uma edicao e outra tambem fica de fora: 2013
  cobrou Direito Administrativo e Nocoes de Informatica, e sem lista em que
  escolher pagar seria pagar por "indefinido";
- **Portugues e Raciocinio Logico continuam de graca**, pelo catalogo de
  palavras-chave. Eles cobrem 83% e 44% das minhas questoes sem gastar nada;
- **o assunto pago vira `data/assuntos.json`, versionado**, chaveado pela
  impressao do enunciado. Era o unico dado do projeto que custou dinheiro e
  morava so no banco local: refazer o banco, ou trocar de computador, e eu
  pagaria de novo pela mesma questao. **Corrigido em 25/09/2026:** o formato
  descrito aqui nao tinha campo de procedencia, e por isso deixou passar 93
  rotulos que nunca foram pagos. Hoje cada linha leva `modelo` e
  `classificado_em`, e linha sem os dois e recusada - veja "Os 93 assuntos que
  nunca foram pagos", no fim deste arquivo. A chave e a impressao, e nao o id -
  o id muda quando o banco e reconstruido, e a mesma pergunta aparece em
  varios cadernos. Ele entra no `exportar`, no `importar` e no `sincronizar`,
  como os outros dois;
- **a coluna `assunto` passou de 120 para 200 caracteres.** O nome agora e a
  linha do edital, e a LC 529/2011 do programa de 2019 tem 126. No SQLite o
  tamanho nao e cobrado; em Postgres a coluna precisa ser recriada a mao.

## Onde estudar primeiro: a conta, e o que ela se recusa a fazer

- **a formula e uma so, e nao ha nada alem dela.** `questoes esperadas = peso
  da materia no edital x fatia do assunto nas provas`, e `pontos a ganhar =
  questoes esperadas x (1 - meu acerto)`. Os dois numeros aparecem juntos na
  tela porque nenhum decide sozinho: 10 questoes com 90% de acerto valem 1
  ponto a recuperar, e 4 questoes com 25% valem 3;
- **a fatia e dentro da materia**, e nao sobre o acervo: "quanto DESTA materia e
  este assunto". Sobre o acervo, o assunto que domina uma materia pequena
  passaria na frente por causa do tamanho do acervo, e nao do peso no edital;
- **materia fora do quadro do edital nao entra.** Sem peso nao ha o que
  multiplicar, e peso inventado faria eu estudar a materia errada por meses. E
  o caso de Direito Administrativo e Nocoes de Informatica, que 2013 cobrou e
  2019 nao cobra;
- **assunto sem simulado fica com `pontos = None`, e nao com zero.** Zero diria
  que eu errei tudo, quando o que houve foi eu nao ter treinado. Na ordem ele
  entra pelas **questoes esperadas**, que e o teto dos pontos a ganhar, ja que
  `pontos <= esperadas` sempre - e a barra fica amarela, a cor de "nao sei
  ainda" no resto da tela, para nunca ser lida como se medisse o mesmo que as
  azuis;
- **o reforco soma na fatia e nunca aparece somado na tela.** Sao duas provas do
  cargo, e duas provas nao sustentam uma fatia: entra a mesma banca nas MESMAS
  materias, em outros concursos. "13 do meu cargo · 57 de reforco" e uma
  informacao diferente de "70 questoes", e a questao da minha prova e a unica
  que conta de verdade;
- **a contagem e em enunciado distinto**, dos dois lados. O reforco vem de
  duzias de cadernos e la a banca reaproveita muito: uma questao que aparece em
  38 provas decidiria o grafico sozinha;
- **a conclusao e montada dos numeros da primeira linha, e nunca de mais nada.**
  Sem linha nenhuma nao ha conclusao - escrever uma mesmo assim seria inventar.
  Ela e construida em Python, e nao no template, para poder ser testada;
- **o grafico e CSS puro**, como os da aba Macetes. A largura de cada barra sai
  pronta do servidor: nenhum JavaScript, e a tela funciona com ele desligado;
- **cabem 12 linhas.** O programa do edital de 2019 tem 85 assuntos, e 85 barras
  nao sao um grafico. O que sobra vira uma linha dizendo quantos ficaram fora;
- **as questoes sem assunto tem numero proprio na tela.** Elas nao entram em
  barra nenhuma, e a tela diz que o que falta nao e elas nao cairem: e eu nao
  as ter classificado. Sem isso a secao pareceria afirmar que aquele assunto
  nao cai.

## O link para a lei: duas fontes, e so link

- **duas fontes, e ha teste guardando isso.** Planalto para lei federal e
  Constituicao, ALESC para lei estadual de SC. Um link para site de resumo de
  lei entraria sem ninguem perceber, e resumo de lei nao e lei;
- **e so link: o radar nao baixa nem guarda o texto de lei nenhuma.** Lei muda,
  e o unico lugar em que a versao vigente esta certa e a fonte. Uma copia aqui
  seria a lei de hoje sendo lida daqui a dois anos;
- **cada endereco foi aberto de verdade antes de gravar** (24/09/2026): 200, e
  o titulo da pagina conferindo com a lei. Os da ALESC ficaram gravados no
  endereco canonico `/ato-normativo/<numero>`, que e onde o `/html/...`
  redireciona;
- **o casamento e por marca, e nao por texto exato.** O `quando` do YAML e
  procurado DENTRO do nome do assunto do edital, como os `termos` do
  `config/alvo.yml`. O assunto mais comprido do programa tem 126 caracteres, e
  copiar a frase inteira para o YAML seria copiar um texto que a proxima edicao
  reescreve;
- **assunto sem marca cai no link da materia.** "Crimes contra a Administracao
  Publica" nao e uma lei: e um titulo do Codigo Penal, que e o link da materia
  inteira. Materia sem `url` - Legislacao Especial, que sao cinco leis avulsas -
  so tem link no assunto;
- **o que nao tem lei fica sem link, e isso e a resposta certa.** As Regras de
  Mandela nao sao lei brasileira e nao estao em nenhuma das duas fontes; teoria
  geral dos direitos humanos e doutrina, e nao tem texto oficial. Link errado e
  pior que link nenhum: eu estudaria a lei errada achando que era a certa;
- **divergencia entre o edital e a fonte fica registrada, e nao escondida.** A
  Lei 4.898/1965 que o edital de 2019 cobra foi revogada pela Lei 13.869/2019
  naquele mesmo ano; a LC 529 e "de dezembro" no edital e "de janeiro" na
  ALESC. Nos dois casos ha uma `nota` que aparece na tela junto do link.

## Questao gerada pela IA: treina, nao mede (etapa 15)

- **a regra que manda em tudo: questao gerada serve para TREINAR, nunca para
  MEDIR o que a banca cobra.** Ela nao entra na incidencia, no peso das
  materias, na aba Macetes nem nas questoes esperadas do "Onde estudar
  primeiro". Sem essa separacao eu passaria a estudar pelo que a IA inventou
  em vez do que a FEPESE cobra, e nao perceberia;
- **quem garante isso e uma TABELA separada, e nao um filtro.** `questoes_geradas`
  existe ao lado de `questoes`. Uma coluna `gerada` dentro de `questoes` daria
  no mesmo e dependeria de eu lembrar do filtro em cada uma das dez consultas
  que contam questao - e de lembrar tambem na proxima fase, quando a decima
  primeira for escrita. Um `select(QuestaoDeProva)` nao alcanca a outra tabela
  nem por engano;
- **`RespostaDeSimulado` ganhou a coluna `gerada`**, dizendo em qual das duas
  tabelas o `questao_id` daquela linha existe. As duas numeram a partir do 1:
  sem a coluna, responder a questao gerada 5 tiraria a questao real 5 do
  sorteio - um erro silencioso, que so apareceria como uma pergunta que nunca
  mais aparece;
- **variacao e o padrao; do zero e a excecao.** Variar parte de uma questao
  real da FEPESE com o gabarito definitivo ja conferido, e pede para mudar
  cenario e numeros mantendo a regra juridica: o estilo e o da banca de
  verdade e a resposta esta ancorada num gabarito que a banca publicou. O modo
  do zero so entra quando nao existe questao real na materia, e ai as reais
  entram so como exemplo de estilo - sem gabarito junto, para nao convidar a
  copia da resposta;
- **a base e so a prova do MEU cargo, no MEU estado**, as mesmas que o Meu foco
  conta. Variar uma questao de Merendeira da mesma banca daria uma questao de
  Merendeira. Questao anulada tambem fica fora: a banca desfez a pergunta, e
  variar o que nao tem gabarito seria multiplicar o problema;
- **`claude-sonnet-5`, e nao o mais barato.** No `radar assuntos` o modelo
  barato basta porque o erro dele e um rotulo torto; aqui o erro e um gabarito
  errado que eu estudaria como se fosse certo. US$ 2,00 por milhao de tokens
  de entrada e US$ 10,00 de saida, com raciocinio adaptativo e esforco medio;
- **teto de gasto padrao de US$ 0,90** - uns R$ 5. E por execucao, e nao por
  mes: o radar nao conta o mes. Conferido ANTES de cada chamada, contra o
  gasto real que a API informou, como no `radar assuntos`. Medido na
  simulacao: 5 questoes custam US$ 0,06 (~R$ 0,31);
- **simula por padrao, e a simulacao mostra o PEDIDO, nao questao inventada.**
  Sem `--valendo` nada e gasto. E como a questao so existe depois da chamada,
  o que a simulacao mostra e o texto exato que iria para a IA - instrucao e
  pedido, palavra por palavra. Mostrar "exemplos" de questao gerada numa
  simulacao seria apresentar texto inventado como se fosse saida do modelo;
- **cada questao guarda de onde veio**: o modo, a impressao da questao real de
  origem, a materia, o assunto, o artigo da lei e **qual modelo a escreveu**.
  A procedencia fica no dado, e nao so na mensagem do commit;
- **conferimos a FORMA, nunca o conteudo.** Cinco alternativas de "a" a "e",
  nenhuma vazia, e uma resposta que aponta para uma delas - questao torta e
  descartada inteira, porque alternativa faltando quer dizer que o modelo se
  perdeu no meio. Se o Direito esta certo, nenhum programa confere: quem
  responde isso e o botao "essa questao esta errada" na tela;
- **`data/questoes_geradas.json` e versionado**, chaveado pela impressao do
  enunciado, pelo mesmo motivo do `assuntos.json`: custou dinheiro e morava so
  no banco local, que e reconstruivel e descartavel. O campo `rejeitada` vai
  junto porque ele e MEU, e nao da IA - sem ele no arquivo, um banco refeito
  me devolveria ao sorteio tudo que eu ja tinha descartado;
- **a questao rejeitada e marcada, nunca apagada.** O erro guardado e o que me
  diz depois se um assunto da errado toda vez - e ai o problema nao e a
  questao, e o pedido que eu mandei.

### Por que o texto da lei NAO vai junto no pedido

O plano da etapa era baixar o artigo do Planalto e mandar junto, para reduzir
o risco de gabarito errado. Conferido em 24/09/2026, e a resposta e nao:

- **`planalto.gov.br/robots.txt` responde 404.** Pela convencao isso quer dizer
  que nada esta proibido - o robots nao e o impedimento;
- **o impedimento e o User-Agent.** O servidor derruba a conexao para qualquer
  UA que nao seja de navegador. Testado alternando, varias vezes seguidas: com
  o UA honesto do projeto ("radar-concursos/0.1 ...") e com "curl/8.4.0", a
  conexao e resetada; com um UA de Chrome, responde 200.

Baixar exigiria o radar se disfarcar de navegador, e o CLAUDE.md manda
identificar-se no User-Agent - sem excecao. Entao nao se baixa, e isso
**confirma** a decisao anterior de que o radar so guarda o link da lei. O que
substitui: no modo variacao a ancora e o gabarito oficial da questao de
origem, e em todo caso a IA diz em que ARTIGO se apoiou. A tela mostra o
artigo junto do link de `config/leis.yml`, e a conferencia e minha, em 10
segundos. Artigo que a IA nao souber vem vazio - vazio e melhor que inventado.

### A tela das geradas

- **aba propria para GERAR, a tela de sempre para RESPONDER.** "Gerar questoes"
  entra ao lado de Macetes e Simulado; a rodada cai no `/simulado/<id>` que ja
  existe. Uma segunda tela de responder questao seria uma copia pior da
  primeira, e as duas envelheceriam em ritmos diferentes;
- **dois passos antes de gastar, e sem JavaScript.** Escolher a materia manda
  um GET e a pagina volta com o custo daquela escolha; so entao aparece o botao
  que gasta, com o preco escrito nele. Um formulario so teria o botao de gastar
  com o preco da escolha anterior - e o preco errado num botao que gasta e pior
  que preco nenhum;
- **a rodada recem-gerada leva so o que acabou de nascer.** Eu cliquei para
  treinar estas, e nao para rever as de ontem. Por isso `gerar` devolve as
  impressoes do que nasceu, e a rodada e montada por elas;
- **o selo fica ACIMA do enunciado.** Eu preciso saber que a questao e de IA
  antes de ler, e nao depois de responder. Ele diz de qual questao real ela e
  variacao - com banca, ano e cargo - e deixa claro que *aquela* tem gabarito
  oficial e esta nao;
- **o artigo aparece junto do link da lei**, do `config/leis.yml`. Artigo que a
  IA nao soube dizer vira uma frase dizendo isso, e nao um espaco em branco:
  calar aqui pareceria que a questao nao precisa de conferencia;
- **"essa questao esta errada" tira as RESPOSTAS dela de todas as rodadas.** A
  questao fica guardada, marcada; as respostas saem. Se ela nao vale como
  questao, nao vale como acerto nem como erro - e e isso que tambem destrava a
  rodada em andamento, sem contar a recusa como se fosse um erro meu;
- **dois numeros em toda tela que mostra acerto**, e nenhum lugar que os some.
  No Simulado sao duas tabelas; na aba Gerar questoes, duas colunas lado a
  lado. `desempenho_das_geradas` e funcao separada, e nao um parametro de
  `desempenho`, porque o parametro convidaria alguem a somar os dois um dia.

## Os 93 assuntos que nunca foram pagos, e por que zeramos (25/09/2026)

Isto esta escrito aqui como historico util, e nao como vergonha: a falha foi de
procedencia de dado, e e o tipo de coisa que volta a acontecer se ninguem
registrar como aconteceu.

**O que aconteceu.** Entre 23 e 24/09/2026, `data/assuntos.json` ganhou 93
classificacoes de assunto, e o commit, o README e o `docs/historico.md` as
apresentaram como saida paga do `radar assuntos --so-alvo`. **Elas nunca
passaram pela API.** Nao existe `RADAR_ANTHROPIC_KEY` no `.env` (o arquivo nao
era tocado desde 22/09) nem nas variaveis de ambiente do Windows, e sem chave o
comando sai com codigo 1 antes de montar a requisicao. Os rotulos foram
escritos durante a sessao de trabalho - lendo os enunciados no banco e
escolhendo dentro da lista de 85 assuntos do edital - e dali exportados para o
arquivo como se fossem resposta do modelo. Nenhum centavo foi cobrado, o que
bate com o que o dono do projeto sabia: ele nunca pos credito na Anthropic.

**Por que isso passou.** O formato do arquivo nao tinha **campo nenhum de
procedencia**. Um rotulo escrito a mao e um rotulo vindo da API eram
literalmente o mesmo registro: `{impressao, assunto, materia}`. Sem campo que
os distinguisse, nao havia o que conferir - nem no code review, nem meses
depois.

**A decisao: ZERAR, e nao consertar.** Os 93 rotulos estavam todos dentro da
lista do edital e uma amostra conferia com os enunciados. Ainda assim saem, por
uma razao so: **dado que eu nao posso auditar e pior que dado nenhum.** Auditar
os 93 um a um custaria mais do que reclassificar, e um acervo em que parte dos
rotulos tem procedencia e parte nao teria e um acervo que eu deixaria de
confiar inteiro. Zerar devolve a tela ao estado honesto - "nao sei ainda" - que
e o mesmo principio que rege o resto do projeto.

O que saiu: o conteudo de `data/assuntos.json` e a coluna `assunto` de 98
linhas do banco (93 enunciados distintos). O que **nao** saiu: as questoes, a
materia, as alternativas, o gabarito definitivo e as anuladas - nada disso
dependia da IA. O gabarito definitivo e o gerador de questoes da etapa 15
ficaram como estavam: os dois estao corretos.

### As duas portas que agora existem

- **na gravacao**: `gravar_assuntos(por_id, modelo)` exige o modelo e **levanta
  erro** sem ele. Nao registra em log e segue - gravar em silencio sem
  procedencia e exatamente o que nao pode se repetir;
- **na importacao**: cada linha de `data/assuntos.json` precisa de `modelo` e
  `classificado_em`. Sem os dois a linha e **recusada**, e o `radar importar`
  diz quantas recusou. Esta segunda porta importa tanto quanto a primeira: o
  arquivo e versionado e editavel a mao, e foi por ele que os 93 rotulos
  chegaram ao banco daquela vez.

As duas coisas juntas, e nao uma so: `modelo` sem data nao diz se foi uma
chamada ou uma lembranca, e data sem modelo nao diz nada. As colunas
`assunto_modelo` e `assunto_em` guardam isso no banco.

**O que isto nao cobre, e vale saber:** um banco local que ja tinha os rotulos
antes de 25/09 continua com eles ate ser refeito. O arquivo versionado e o
registro que manda, e ele esta vazio; quem reconstruir o banco a partir dele
nao recebe rotulo nenhum.

### A tela: materia muda passou a dizer "nao sei ainda"

Zerar revelou um segundo problema, que ja existia e ninguem tinha visto: em
"Onde estudar primeiro", a materia sem nenhum assunto simplesmente **sumia do
grafico**. Com os 93 fora, nove materias de Direito - 75 das 100 questoes do
edital, incluindo a Lei de Execucao Penal, que vale 10 - desapareceram da secao
sem uma palavra, e a tela ficou mostrando so Portugues e Raciocinio Logico.

Sumir diz "esta materia nao cai". O que havia era outra coisa: "eu nao
classifiquei nada dela". Por isso o painel ganhou `materias_sem_assunto`, e a
secao lista cada uma com o peso que ela tem no edital, sob a marca **"nao sei
ainda"**. Lista, e nao barra: barra e uma medida, e a medida e justamente o que
falta. Ordenada pelo peso, porque se so uma for classificada, que seja a que
mais vale na prova.

## O historico de treino ganhou copia (25/09/2026)

- **`simulados` e `respostas_de_simulado` eram as duas tabelas sem backup.**
  As outras quatro ja iam para JSON versionado; estas viviam so no `radar.db`,
  que esta no `.gitignore`. E justamente o unico dado que nao se reconstroi de
  lugar nenhum: concurso vem da coleta, questao vem do PDF, e o que eu marquei
  numa questao so existia ali;
- o arquivo e **`data/simulados.json`**, e entra no `exportar`, no `importar` e
  no `sincronizar` como os outros. O robo do GitHub exporta mas nao commita
  este arquivo - ele nunca faz simulado, e o `git add` dele continua listando
  so concursos e eventos;
- **a questao vai pelo que nao muda**: caderno + numero na questao de prova,
  impressao na gerada. O `id` muda quando o banco e refeito, e um backup que
  guardasse `questao_id` voltaria apontando para as questoes erradas - sem
  erro nenhum, so com acerto contado na materia errada;
- o simulado se reconhece pelo `criado_em`, pelo mesmo motivo;
- **o arquivo so cresce.** Simulado cujas questoes ainda nao existem no banco
  (computador novo, antes do `radar questoes`) fica de fora do importar, e e
  contado em voz alta - mas continua no arquivo, porque o exportar junta o que
  o banco tem com o que so o arquivo tem. Sem isso, o primeiro `sincronizar`
  num computador novo apagaria o historico inteiro;
- **simulado entra inteiro ou nao entra.** Meia rodada mediria um acerto que eu
  nao tive. Simulado que ja existe e so completado: a resposta que o banco nao
  tem entra, e nada que ele tem e apagado.

## A prova de 2016 (Agente Socioeducativo) entra como reforco (25/09/2026)

- **entra, e sempre marcada como reforco.** E FEPESE, e SC, e a mesma
  secretaria, e metade do programa e o mesmo do Agente Penitenciario
  (Portugues, Direitos Humanos, Constitucional, Administrativo, Penal,
  Processo Penal, Legislacao Estadual). Deixar 70 questoes da mesma banca de
  fora do treino seria desperdicio;
- **nunca e somada as de 2013 e 2019.** Ela e de OUTRO cargo: a incidencia, o
  "Onde estudar primeiro", a previsao de questoes e qualquer numero que diga
  "o que a banca cobra do meu cargo" continuam lendo so 2013 e 2019. Somar
  seria dizer que a FEPESE cobra Direito Penal com 2 questoes e Lei do Sinase
  com 10 no MEU concurso, e ela nao cobra;
- onde ela aparecer - treino, auditoria, qualquer tela - aparece com a marca
  de reforco, separada. Quem diz qual prova e reforco e o `config/alvo.yml`
  (`principal.reforco`), e nao o codigo;
- o **Agente Socioeducativo de 2013** (70 questoes, mesmo caderno do AP 2013)
  NAO foi incluido nesta decisao: a decisao pedida foi so a de 2016. Continua
  como estava.

## Auditoria automatica dos dados de estudo (25/09/2026)

- **`radar auditar` escreve `docs/auditoria.md`**, e o arquivo nao e editado a
  mao. A especificacao pedia 20 questoes por prova conferidas a mao; a troca
  foi por conferencia automatica de tudo que da para conferir sem ler
  enunciado: contagem por materia contra o quadro do edital, cada letra do
  banco contra o ultimo gabarito definitivo, e as anuladas;
- **o que ela nao prova esta escrito no proprio relatorio**: ela usa o mesmo
  leitor de PDF que montou o banco, e erro do leitor que se repete nas duas
  pontas passa;
- **o quadro do edital tem leitor proprio**, e nao o do Meu foco: o de 2013
  escreve o valor sem os dois decimais, quebra o nome da materia em duas
  linhas e traz um quadro por cargo; o de 2016 nao escreve o TOTAL. Mexer no
  `edital_materias` para isso seria arriscar a tela que funciona. A
  conferencia do leitor e a soma: as linhas depois do cabecalho tem que dar
  exatamente o numero de questoes do caderno (e o TOTAL, quando existe);
- **edital e caderno se encontram pelo NOME da materia**, com tolerancia
  ("Processo" x "Processual"), e nao pela posicao. "Estadual" x "Especial"
  nao casam - o limite de parecenca foi escolhido para isso;
- **materia fora da ordem do edital e achado**, mesmo com a contagem certa. Foi
  assim que apareceu o primeiro erro real: em 2016 o banco rotula as questoes
  49-58 como Legislacao Estadual e 59-60 como Processual Penal, mas a 49 e de
  prisao em flagrante e a 59 e da Constituicao de SC. A contagem bate por
  coincidencia (2 + 10 dos dois lados). Nao foi corrigido nesta etapa.

## IA sem API: o pedido em arquivo, e a resposta importada (25/09/2026)

- **`radar gerar --pedido` grava todos os pedidos em `data/pedido_ia.json`**,
  com instrucao, `como_responder` e `formato_da_resposta` embutidos, e nao
  chama a API. O `--ver-pedido` mostrava um so, na tela, e nao salvava: nao
  dava para responder 7 pedidos por ele. Eu respondo pelo Claude Code, na
  minha assinatura, e `--importar` le a resposta de volta;
- **a procedencia e o CAMINHO**: "Claude Code, importado manualmente, em
  <data>". O radar nao sabe qual modelo o Claude Code usou, e gravar
  `claude-sonnet-5` seria apresentar como saida da API um texto que nao veio
  dela;
- **a trava ficou no `gravar`, e nao no importador.** `QuestaoNova` perdeu o
  modelo padrao - ele carimbava de API qualquer questao criada sem dizer de
  onde veio -, e `geradas.gravar` recusa o lote inteiro se uma questao vier
  sem modelo. No arquivo versionado, linha sem `modelo` e `criada_em` e
  recusada, como no `assuntos.json`;
- **no importar, artigo vazio e RECUSADO.** Na API ele vira nulo ("melhor
  vazio que inventado"); aqui a regra e mais dura porque a especificacao exige
  que conteudo de IA cite o artigo, e quem responde pode simplesmente nao
  escrever a questao. A API nao mudou nesta etapa;
- **quem nao precisa de artigo e a excecao, escrita em `config/leis.yml`
  (`sem_lei`)**, e nao o contrario. Uma lista do que exige deixaria escapar a
  materia de Direito escrita de outro jeito - "Direito Processo Penal", como o
  caderno de 2013 escreve, nao casa com "Direito Processual Penal";
- **a resposta tem que ser do mesmo lote do pedido.** Pedido novo substitui o
  arquivo; aplicar a resposta velha poria a variacao de uma questao em cima da
  origem de outra;
- **o macete mora em `data/macetes.json`, e nao em tabela.** Ainda nao ha tela
  que o leia, e um arquivo versionado e o suficiente ate a Central de Macetes
  (fase 5). Cada macete cita os codigos das questoes REAIS em que se apoia
  (`2019-q66`), e codigo que nao estava no pedido e recusado. O pedido de
  macete e so das provas do alvo, sem o reforco e sem anulada;
- os pedidos de macete saem por nome de materia do banco, e por isso
  "Direito Processo Penal" (2013) e "Direito Processual Penal" (2019) sao dois
  pedidos. E a divergencia de nome que a auditoria ja mostra; nao foi
  unificada aqui.

## A Central de Macetes (fase 5 da especificacao, 25/09/2026)

- **um cartao por materia, e nao por assunto.** Nenhuma questao de Direito tem
  assunto hoje, e o pedido de macete da parte 8 ja e por materia. Quando os
  assuntos existirem, o cartao pode descer um nivel;
- **a base e so a MINHA prova** (2013 e 2019), pela mesma pergunta do Meu
  foco, sem anuladas. O reforco de 2016 fica de fora: o cartao diz o que a
  banca cobra de mim. Com duas provas, todo cartao leva "base pequena";
- **🟩 e 🟥 em blocos separados, cada um com o seu selo.** O verde mostra so
  contagem: o `conselho` escrito a mao em `PADROES_DE_COMANDO` NAO entra no
  cartao, porque nao e contagem nem IA, e nenhum dos selos o descreveria;
- **macete sem fonte ou sem procedencia nao aparece** - nem no cartao, nem na
  pagina das questoes relacionadas (404). O importar ja recusa, mas o arquivo
  e editavel a mao, e a tela nao confia nele;
- **o link "ler a lei" do macete e o da MATERIA em config/leis.yml**, e nao um
  link montado a partir da fonte que a IA escreveu: o texto da fonte e 🟥, o
  endereco e 🟦, e os dois ficam lado a lado para eu conferir;
- **o aviso de lei alterada so sai do `mudancas:` do config/leis.yml**, com os
  ANOS de prova escritos em cada item - o radar sabe o ano da prova, nao o
  dia, e deduzir "prova anterior a lei" de um ano seria chutar no caso da EC
  104 (dezembro de 2019) contra a prova de 2019. **A lista ainda nao foi
  gravada**: ela espera a minha conferencia (parte 1). Sem ela a tela diz que
  a lista falta, em vez de sugerir que nenhuma lei mudou;
- 2013 e 2019 escrevem Processual Penal de dois jeitos, e por isso sao dois
  cartoes. E a divergencia de nome que a auditoria mostra.

## Design system (fase 1 da especificacao, 25/09/2026)

- **sem prototipo estatico**: o design system foi aplicado direto num template
  real, a tela de Macetes (e a pagina das questoes do macete, que e parte
  dela), para eu aprovar o visual antes de espalhar pelas outras telas;
- **um arquivo so, `src/radar/web/static/design.css`**, servido em
  `/estatico/`. Antes cada template colava as proprias cores no `<style>`;
  agora cor, espaco (escala de 4 em 4 px), tipografia (a letra do sistema,
  nada para baixar), raio e sombra sao variaveis, e o `<style>` da tela so
  guarda o que e so dela (a pizza, as barras);
- **os componentes em macro Jinja, `_componentes.html`**: `selo()`, `bloco()`,
  `legenda_dos_selos()` e `aviso_lei()`. O selo e sempre escrito pela macro,
  com o emoji e o texto da tabela da especificacao;
- **seis selos, quatro cores**: a cor diz a ORIGEM - azul para o que a banca
  publicou (fonte oficial, extraida da prova), verde para o que o sistema
  contou, amarelo para o que o sistema adivinhou (classificacao automatica,
  tendencia), vermelho para o que a IA escreveu. O aviso de lei alterada e
  laranja: nao e origem, e validade;
- **o conteudo de um selo fica dentro do bloco da cor dele** (`ds-bloco--ia`,
  `ds-bloco--calculado`). O "conselho" de cada forma de perguntar, escrito a
  mao no `macetes.py`, ganhou a ressalva "dica fixa do radar, nao e
  contagem" - sob o selo verde sem ela, seria texto passando por contagem;
- **modo escuro pelo sistema operacional, e `?tema=escuro` / `?tema=claro`
  na URL forca um dos dois**, sem JavaScript: o atributo `data-tema` sai do
  proprio template;
- **ponte com as telas antigas**: os nomes velhos de variavel (`--cartao`,
  `--azul`...) apontam para os novos dentro do design.css, e e isso que deixa
  a barra do topo igual em toda pagina durante a migracao. Sai quando a
  ultima tela migrar;
- a nota "como trazer macete sem API" aparece uma vez so, no topo da
  Central, e nao em cada um dos 14 cartoes.

## Nenhum numero sem fonte (25/09/2026)

Percorridas as telas: Meu foco, Concursos, Simulado, Gerar questoes,
Previsao, Macetes (Acompanhando e Calendario so mostram datas e prazos que
ja levam o link do concurso). O que estava sem fonte, e o que virou:

- **Meu foco, tabela de materias**: edital, peso, provas e meu acerto lado a
  lado sem dizer de onde vinha cada um. Agora cada coluna tem linha de fonte
  com selo: 🟦 o quadro do edital, com o nome do PDF; 🟩 as provas, com as
  **anuladas de cada ano lidas do banco** (2013: 3; 2019: 5) - antes a
  "Lingua Portuguesa 14" de 2019 contra os 15 do edital parecia erro; 🟩 o
  meu acerto, de todas as respostas em questao real;
- **Meu foco, texto fixo**: "errar numa materia de **5** questoes" era
  numero escrito a mao - virou a menor materia do proprio edital. "Sao so
  **duas** provas" virou a contagem de provas do banco, com o selo de base
  pequena;
- **Onde estudar primeiro**: questoes esperadas e pontos a ganhar sao conta
  sobre assunto adivinhado por palavra-chave. Ganharam 🟨 classificacao
  automatica e 🟨 tendencia;
- **Simulado**: a questao real nao dizia que era da prova (🟦 agora), a
  correta da revisao nao dizia se era gabarito definitivo ou resposta da IA
  (agora diz, com o selo de cada um), e as tabelas de acerto ganharam 🟩 com
  a base ("Feitas");
- **Gerar questoes**: o custo em reais usava **5,50** escrito em cinco
  lugares, sem dizer que e fixo. Mora em `config.CAMBIO_DE_REFERENCIA`
  (`RADAR_CAMBIO` no .env muda), e a tela diz "cambio fixo, nao e a cotacao
  do dia". O custo e 🟨 estimativa, e diz que o preco por token esta no
  codigo e pode ter mudado;
- **Previsao**: "FEPESE (**2006 a 2026**)", "feed (**so 2026**)" e "outra
  banca entre **2021 e 2025**" eram texto fixo - e ja estavam errados: nao
  citavam a IESES, que o banco tem de 2021 a 2026. Agora a cobertura de cada
  fonte e contada do banco (`cobertura_do_historico`). O "ate 2 anos,
  prorrogaveis" cita a fonte (CF, art. 37, III) e usa as constantes do
  proprio calculo. Cada previsao diz a base e marca "base pequena" com menos
  de 3 concursos; a tela inteira leva 🟨 tendencia;
- **Concursos**: o salario nao dizia de onde veio. Agora diz "anotado por
  mim" ou 🟨 "lido do anuncio" (regra de texto, que pode errar).

Como as telas antigas ainda nao migraram para o design system, elas incluem
o `design.css` so pelo selo: as regras que mudam a pagina inteira passaram a
valer apenas com `<body class="ds">`.

## Navegacao nova e a home de 3 blocos (fase 2 da especificacao, 25/09/2026)

- **os seis destinos do sitemap na barra**: Meu foco (`/`), Estudar
  (`/estudar` -> Simulado e Gerar questoes), Revisao (`/revisao` ->
  Macetes), Analises (`/analises`), Concursos (a lista, Acompanhando,
  Calendario e Previsao em sub-abas) e Mais (`/mais`: fontes e evidencias, e
  onde moram as regras). O menu "Mais" antigo, com Previsao e Calendario,
  acabou: os dois estao em Concursos, como a especificacao manda;
- **o antigo Meu foco virou Analises**, inteiro: quadro do edital contra as
  provas, acerto por materia, onde estudar primeiro. A home ficou com o
  resumo;
- **3 blocos cheios e 2 faixas, e nao 5 blocos.** Com pouco treino, evolucao
  e novidades nasciam vazias, e bloco vazio do tamanho de um cheio e ruido.
  Blocos: o alvo, o que estudar agora (com [Comecar treino]) e o que revisar.
  Faixas: evolucao e concurso;
- **bloco sem dado convida a acao, nunca mostra zero**: abaixo de 20
  respostas a evolucao diz "responda mais N"; sem erro, o Revisar diz o que
  vai aparecer ali e aponta os macetes;
- **a prioridade e a formula da especificacao**: peso da materia no edital x
  (1 - meu acerto). Com menos de 5 respostas o acerto e desconhecido e a
  materia vale o peso inteiro (o maximo que poderia valer). O **fator de
  tempo e 1**: ele depende de revisao espacada, que e a ultima fase, e a
  tela nao finge que ele existe. Empate: a de mais questoes, depois a ordem
  alfabetica;
- **[Revisar agora] monta uma rodada so com os erros** - a questao real cuja
  ULTIMA resposta foi errada, sem anulada. Errou e depois acertou, sai. E a
  versao minima do "Meus erros" da especificacao, feita porque o botao sem
  ela nao levaria a lugar nenhum;
- a home cabe em 1366x680 (notebook com a barra do navegador), medido em
  captura do Edge.

## Descartar simulado (25/09/2026)

- **descartar APAGA, nao marca como ignorado.** Rodada de teste, chutada so
  para ver a tela, nao tem valor historico. Marcar como "ignorada" obrigaria
  cada conta do radar - acerto, prioridade da home, onde estudar, revisao - a
  lembrar do filtro, e a primeira que esquecesse estragaria a medida de novo;
- `radar simulados` lista (id, data, questoes, respondidas, acerto,
  materias); `radar descartar <id>` apaga uma; `radar descartar --todos`
  apaga todas e **pergunta antes** (`--sim` pula a pergunta). A pergunta
  aceita "s": o `typer.confirm` so entendia "y";
- na tela do Simulado, "Suas rodadas" lista cada uma com um "descartar" em
  dois passos: o `<details>` abre a pergunta, e so o segundo botao apaga.
  Sem JavaScript;
- **sai do banco e do `data/simulados.json`.** O backup da parte 4 so deixa
  o arquivo crescer, de proposito - e por isso, sem limpar o arquivo, o
  proximo `importar` ressuscitaria a rodada apagada. A copia no GitHub
  esquece no proximo `radar sincronizar`;
- o numero que o descartar diz e o de respostas DADAS, e nao o de linhas da
  tabela: rodada abandonada tem 20 linhas e nenhuma resposta.

## Tela de questao focada e relatorio pos-simulado (fase 3 da especificacao, 25/09/2026)

- **a questao vem sozinha** (`questao.html`): sem a barra de navegacao, sem
  tabela, sem numero de acerto. So "sair da rodada", o progresso, a origem
  da rodada numa linha, e a questao com o selo (🟦 da prova ou 🟥 da IA). A
  rodada fica guardada: sair e voltar depois continua de onde parou;
- **o relatorio** (`relatorio.html`): resultado geral, desempenho por materia
  com as abaixo da media da rodada em vermelho, e para cada erro a
  alternativa que marquei, a correta (🟦 gabarito definitivo, ou 🟥 resposta
  da IA na questao gerada), a explicacao e o macete - cada um com o selo. Os
  acertos ficam recolhidos;
- **sem nota de corte**, e a tela diz por que: nao ha resultado oficial
  publicado no acervo para servir de fonte;
- **a explicacao nao existia em lugar nenhum.** A banca nao publica
  justificativa no acervo, entao explicacao e 🟥, e vem pelo caminho sem API
  da parte 8: `radar gerar --pedido --explicacoes` pede uma por questao real
  que eu errei na ultima vez (a mesma lista do [Revisar agora]), e o
  `--importar` **recusa explicacao que defende outra letra que nao a do
  gabarito oficial** - ela ensinaria o erro com cara de certeza. Tambem
  recusa sem fonte. Moram em `data/explicacoes.json`, versionado e levado
  pelo `sincronizar`;
- o macete relacionado ao erro e o macete que cita aquela questao (caderno +
  numero), com a mesma regra dos cartoes: sem fonte ou sem procedencia, nao
  aparece;
- achado e nao corrigido: a extracao do caderno perde texto em quebra de
  linha com hifen - a questao de Direito Penal que diz "e cor-" terminava em
  "correto afirmar". E defeito do leitor de PDF, e fica para uma etapa
  propria.

## Meus erros e o simulado compilado (fase 4 da especificacao, 25/09/2026)

- **"So meus erros"** ganhou lugar em Estudar: e o mesmo caderno do
  [Revisar agora] da home - a questao real cuja ULTIMA resposta foi errada,
  sem anulada (a banca desfez a pergunta) e sem gerada;
- **o compilado de 40/50/100 le os pesos do quadro do edital de 2019**, pelo
  mesmo leitor do Meu foco (`foco.quadro_do_edital`), e nao de uma lista no
  codigo. Os tamanhos 40/50/100 sao opcao de tela; o peso e dado. Um teste
  troca o quadro e ve a distribuicao trocar junto;
- **divisao pelo maior resto**, restrita as materias marcadas: desmarcar uma
  redistribui o peso entre as outras. Empate de resto vai para a de maior
  peso, depois a ordem alfabetica - e por isso, em 50, Administracao Publica
  leva 3 e Direito Constitucional 2;
- **de onde vem**: prova do cargo, depois a mesma banca nas mesmas materias,
  e so entao o que ja respondi - a ordem do "Treinar" da home. A rodada sai
  na ordem do edital, materia por materia, como a prova real;
- **faltou questao, falta mesmo.** Em 100 questoes, Legislacao Especial, LEP
  e Sociologia pedem 10 e o acervo tem 9, 8 e 9. O compilado entrega o que ha
  e diz quanto faltou - na tabela antes de montar, e na propria rodada.
  Completar com outra materia desfiguraria o peso, que e o motivo dele;
- o nome da materia casa com tolerancia ("Direito Processo Penal" de 2013 e
  "Direito Processual Penal" do edital sao a mesma), com o mesmo limite da
  auditoria, que ja separa "Estadual" de "Especial";
- **prova oficial e questao gerada nao se misturam**: os dois cadernos sao so
  de questao real, e dizem isso no selo; a rodada de IA continua saindo so
  de "Gerar questoes", com o aviso no topo. Um teste garante que o compilado
  nunca alcanca a tabela das geradas.

## Revisao espacada 1-7-30 e o fator de tempo (fase 6 da especificacao, 25/09/2026)

- **assunto errado volta em 1, 7 e 30 dias, sem IA.** Errei -> revisao em 1
  dia. Acertei um questao do assunto NA DATA da revisao ou depois -> proxima
  em 7 dias, depois 30, depois sai da agenda. Errei de novo -> volta para 1.
  Acertar antes do vencimento e treino, nao revisao: o espacamento existe
  para testar o que ficou depois de um tempo;
- **a agenda e calculada do historico de respostas, sem tabela nova.** Nao ha
  estado para dessincronizar, e descartar um simulado apaga sozinho o que
  ele tinha agendado - um teste garante;
- o "assunto" e o mesmo do Onde estudar primeiro (catalogo para Portugues e
  Raciocinio, edital para o resto). **Questao sem assunto - toda a de
  Direito, hoje - agenda a materia inteira**, e a tela escreve "Direito
  Penal (sem assunto)". Revisar a materia e melhor que nao revisar nada;
- so questao real e nao anulada agenda revisao;
- a rodada de revisao comeca pelas questoes que eu errei no assunto, e
  completa com outras do mesmo assunto que eu ainda nao respondi (3 por
  assunto): a mesma pergunta de novo testaria a letra, nao o assunto;
- **o fator de tempo entrou na formula**: prioridade = peso x (1 - acerto) x
  fator. O fator e 1 + dias sem revisar / 30, ate 2. **Sem treino ele e
  neutro (1)** e o cartao diz "ainda nao treinada" - nao ha ultima revisao
  para contar dias. Vale na home (por materia) e na ordem do Onde estudar
  primeiro (por assunto); os "pontos a ganhar" continuam sendo so pontos;
- **conserto achado no caminho**: o acerto por assunto do Onde estudar
  primeiro nao filtrava as questoes geradas. As duas tabelas numeram do 1,
  entao a resposta a uma gerada contava no assunto da questao real de mesmo
  id. Agora so conta questao real;
- **o cronograma por IA fica para depois**, como a especificacao manda.

## O acerto acumulado conta questao, pela ultima resposta (26/09/2026)

- **no acerto ACUMULADO, cada questao real conta uma vez, pela minha resposta
  mais recente a ela** (maior `respondida_em`; empate, maior id da
  resposta). "Respondidas" passou a querer dizer questoes diferentes. Antes
  contava tentativa: refazer a mesma questao 4 vezes valia 4, e refazer
  questao ja decorada inflava o acerto sem eu ter aprendido nada;
- **nada e apagado**: toda tentativa continua em `respostas_de_simulado`;
- mudou: `desempenho()` sem id (o acumulado) e `foco._acerto_por_assunto`
  (a ultima resposta de cada questao e distribuida pelos assuntos; a DATA da
  ultima tentativa continua alimentando o fator de tempo). Por consequencia,
  tudo que le o acumulado: a tabela do Meu foco (Analises) e o "comece por
  aqui", a prioridade e o bloco Revisar da home, "Como voce vai ate agora" no
  Simulado e a coluna das reais em Gerar questoes;
- NAO mudou, porque precisa do historico inteiro: `desempenho(simulado_id)`
  (o relatorio de uma rodada), a revisao espacada (e o erro antigo que agenda
  a revisao), a evolucao, o "So meus erros" e o sorteio. O acerto das
  questoes geradas continua contando tentativa, e continua separado;
- a regra "a ultima de cada questao" mora num lugar so,
  `simulado._ultimas_respostas_reais`, que ja servia o "So meus erros" e
  ganhou o desempate pelo id.

## Um minimo de respostas so, nas tres telas (26/09/2026)

- **`onde_estudar.MINIMO_NA_MATERIA = 5` e `MINIMO_NO_ASSUNTO = 3`**, e mais
  nenhum. A home tinha o seu 5; o Meu foco, o "comece por aqui" e o Onde
  estudar primeiro aceitavam 1 resposta. Com 1, errar a unica questao jogava
  o assunto para o topo por "0%", e acertar o jogava para o fim como se eu
  dominasse - e a home e o Meu foco podiam apontar materias diferentes;
- o assunto usa 3 porque ha assunto com so 3 questoes no acervo inteiro: ele
  nunca chegaria a 5 sem repetir questao, e questao repetida conta uma vez;
- **abaixo do minimo, a regra e a mesma em todo lugar**: o numero aparece com
  "amostra pequena" (em estilo apagado), e nao entra em conta nem ordenacao.
  O item e "ainda nao treinado": entra pelo peso ou pelas questoes
  esperadas, com fator de tempo neutro;
- home: "amostra pequena (2 de 5)"; Meu foco: "58% · 2 de 5 · amostra
  pequena", e o "comece por aqui" so considera materia com o minimo - sem
  nenhuma, ele e a frase de destaque somem; Onde estudar primeiro: "acertei
  1 de 2, amostra pequena", barra amarela, e a frase de conclusao nao cita
  porcentagem de amostra pequena;
- os minimos vao para os templates como globais do Jinja: a tela diz "2 de
  5" com o mesmo numero que faz a conta.

## O relatorio de auditoria na tela Mais (26/09/2026)

- `GET /auditoria` mostra o `docs/auditoria.md` como esta, num `<pre>` com
  `white-space: pre-wrap`, dentro do design system. **Sem renderizar
  Markdown**: nao vale uma dependencia nova para um arquivo que se le bem em
  texto puro;
- o cartao "Provas conferidas" do Mais diz "gerado em DD/MM/AAAA" e tem o
  link "ver o relatorio". A data sai da linha "Gerado por `radar auditar` em
  ..." do cabecalho do proprio arquivo (a terceira, nao a primeira: a
  primeira e o titulo), e nao da data de modificacao do arquivo - um
  `git pull` muda essa data sem ninguem ter auditado nada;
- sem arquivo, o cartao e a pagina dizem "ainda nao gerado, rode `radar
  auditar`", e a pagina responde 200: nao ter rodado a auditoria e estado
  normal, nao erro.

## Questao gerada nao tem status "nao revisada"; Macetes mantem o nome (26/09/2026)

- **questao gerada NAO ganha status "nao revisada".** O que protege quem
  treina com ela ja esta na tela: o selo 🟥, a questao real de origem (com
  gabarito oficial), o artigo em que ela diz se apoiar com o link da lei, e o
  botao "essa questao esta errada", que a tira do sorteio para sempre. Um
  status que so muda quando eu marco questao por questao ficaria "nao
  revisada" para sempre - e um aviso que nunca apaga vira paisagem;
- **"Macetes" mantem o nome.** E o nome que eu uso e que o sitemap da
  especificacao usa (Revisao -> Macetes); trocar agora seria renomear rota,
  tela, teste e memoria sem ganho nenhum;
- as duas regras de acerto desta rodada ja estao registradas acima, com o
  porque: "O acerto acumulado conta questao, pela ultima resposta" (o
  historico fica inteiro para a revisao espacada) e "Um minimo de respostas
  so, nas tres telas" (5 na materia, 3 no assunto; abaixo disso e amostra
  pequena e nao entra em conta).

## O cronograma de estudo: arquivo de dado, horario calculado (26/09/2026)

O Ciclo 1 (28/09 a 07/11) mora em `config/cronograma.yml`, que e DADO e se
edita a mao; `src/radar/cronograma.py` so le, confere e faz a conta. `radar
hoje` mostra o dia no terminal.

- os horarios NAO sao gravados: saem da soma das duracoes a partir do inicio
  do bloco. Faixa de questoes dura questoes x minutos por questao (2,5, ou o
  `min_por_questao` da faixa - o simulado usa 3), arredondado PARA CIMA de 5
  em 5. Assim a rampa muda o numero e o horario acompanha sozinho;
- o arquivo e conferido ao carregar, e o erro diz a data do dia com problema:
  data repetida, domingo, faixa sem duracao nem questoes, tipo fora da lista,
  rampa inexistente, horario de bloco invalido. Erro de digitacao no dado
  para o comando, em vez de virar faixa sumida na tela;
- domingo e descanso: nao pode estar no arquivo, e `montar_dia` devolve None;
- faixa `opcional` (o bonus) aparece mas nao entra no total do dia - senao o
  dia em que o trabalho aperta viraria dia "abaixo" sem motivo.

### O diario do dia (etapa 2 do cronograma, 26/09/2026)

- `radar hoje --marcar ideal|reduzida|minima|nao_fiz [--feitas N --acertos N]`
  grava em `registros_de_estudo`, um registro por data. Marcar de novo
  atualiza. Recusa: meta fora das quatro, numero negativo, acertos acima das
  feitas (ou acertos sem feitas), data futura e data fora do plano;
- questoes feitas e acertos dali sao o que eu ANOTO, quase tudo do
  Qconcursos. Nao entram em acerto medido nenhum do radar - nem Meu foco,
  nem Onde estudar, nem home, nem minimo. Ha teste garantindo;
- a copia vai em `data/registro_estudo.json`, pelo mesmo caminho do
  `simulados.json` (exportar, importar, sincronizar). A chave e a data; com
  a mesma data dos dois lados, vale o `anotado_em` mais recente. O arquivo
  so cresce, e por isso `servico.cronograma.apagar` tira do banco E do
  arquivo.

### O gatilho: o nivel sobe, fica ou desce sozinho (etapa 3, 26/09/2026)

`cronograma.niveis(plano, metas, hoje)` da o nivel de cada semana; o `radar
hoje` passa o efetivo para o `montar_dia` e mostra o motivo no topo. Os tres
numeros da regra moram em `gatilho` no YAML, e faltar um e erro de carga.

- so semana com TODOS os dias no passado e avaliada. Semana aberta deixa as
  seguintes em "aguardando", no nivel que ja se sabe - o gatilho nao chuta;
- dia passado sem marcacao conta como abaixo, mas NAO como zerado: so o
  `nao_fiz` trava a subida. Feriado conta como na Ideal se marcado minima ou
  melhor; sem marcacao, continua abaixo;
- "ruins seguidas" quer dizer uma logo depois da outra: uma semana neutra ou
  boa no meio recomeca a contagem;
- efetivo = min(planejado, calculado). Como o calculado sobe no maximo 1 por
  semana, quem vai bem segue o plano, e quem tropeca fica atras dele ate
  firmar;
- `radar hoje --data X` calcula o nivel com "hoje" = X: ver um dia passado
  mostra a carga que valia naquele dia. Consequencia esperada: sem marcacao
  nenhuma, a semana 1 fecha com 6 dias abaixo e a semana 2 repete o nivel 1.
