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
- **seis selos, quatro cores** (*revista em 01/10/2026, Etapa 0, decisao 5:
  passam a 🟢🔵🟡🟣 quando a Etapa 7A trocar*): a cor diz a ORIGEM - azul para o que a banca
  publicou (fonte oficial, extraida da prova), verde para o que o sistema
  contou, amarelo para o que o sistema adivinhou (classificacao automatica,
  tendencia), vermelho para o que a IA escreveu. O aviso de lei alterada e
  laranja: nao e origem, e validade;
- **o conteudo de um selo fica dentro do bloco da cor dele** (`ds-bloco--ia`,
  `ds-bloco--calculado`). O "conselho" de cada forma de perguntar, escrito a
  mao no `macetes.py`, ganhou a ressalva "dica fixa do radar, nao e
  contagem" - sob o selo verde sem ela, seria texto passando por contagem;
- ~~modo escuro pelo sistema operacional~~ - substituido em 26/09/2026:
  escuro e o padrao e claro e escolha, guardada em cookie (veja "Escuro e o
  padrao", mais abaixo). O `?tema=` na URL continua forcando um dos dois;
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

> **Revista em 01/10/2026 (Etapa 0, decisao 6):** os minimos passam a 20 na
> materia, 10 no assunto e 6 no subassunto/elemento, para o sistema inteiro.
> O 5/3 abaixo vale ate a Etapa 4 aplicar.

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

- o cronograma e DADO, e nao codigo: o Ciclo 2 entra trocando o arquivo, sem
  mexer em Python, e corrigir um dia e editar texto, nao abrir codigo;
- os horarios NAO sao gravados: saem da soma das duracoes a partir do inicio
  do bloco. Faixa de questoes dura questoes x minutos por questao (2,5, ou o
  `min_por_questao` da faixa - o simulado usa 3), arredondado PARA CIMA de 5
  em 5. O motivo e a rampa: ela troca o numero de questoes da noite conforme
  o nivel, e com horario gravado cada troca deixaria a agenda errada dali em
  diante. Calculado, o horario acompanha sozinho;
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
  nem Onde estudar, nem home, nem minimo. O acerto do radar e medido questao
  por questao, com materia, assunto e anulada conhecidos; um total digitado
  de memoria, de questoes de outras bancas, nao tem nada disso, e somado ali
  poria lembranca no lugar de medida. Ha teste garantindo;
- a copia vai em `data/registro_estudo.json`, pelo mesmo caminho do
  `simulados.json` (exportar, importar, sincronizar). A chave e a data; com
  a mesma data dos dois lados, vale o `anotado_em` mais recente. O arquivo
  so cresce, e por isso `servico.cronograma.apagar` tira do banco E do
  arquivo.

### O gatilho: o nivel sobe, fica ou desce sozinho (etapa 3, 26/09/2026)

`cronograma.niveis(plano, metas, hoje)` da o nivel de cada semana; o `radar
hoje` passa o efetivo para o `montar_dia` e mostra o motivo no topo. Os tres
numeros da regra moram em `gatilho` no YAML, e faltar um e erro de carga -
sao eles que eu vou querer ajustar, e ajustar nao pode pedir codigo.

As regras, com os numeros do Ciclo 1:

- a semana 1 comeca no nivel 1; o PLANEJADO da semana N e N (ate o maior
  nivel da `rampa`, 6);
- semana BOA: 5 dias ou mais na Ideal (`sobe_com_dias_na_ideal`) e nenhum
  `nao_fiz`. A seguinte sobe 1;
- semana RUIM: 3 dias ou mais abaixo da Ideal (`semana_ruim_com_dias_abaixo`).
  Repete o nivel; a 2a ruim SEGUIDA (`desce_apos_semanas_ruins`) desce 1,
  nunca abaixo de 1, e a contagem recomeca;
- qualquer outra e NEUTRA e repete. O motivo de repetir em vez de descer
  logo: uma semana ruim isolada e acidente (trabalho, doenca); duas seguidas
  dizem que a carga passou do que eu aguento.

Os detalhes:

- so semana com TODOS os dias no passado e avaliada. Semana cuja anterior
  ainda nao fechou e "futura" e fica na carga do PLANO - o gatilho nao chuta,
  e o que nao aconteceu nao entra na conta das outras;
- dia passado sem marcacao conta como abaixo, mas NAO como zerado: so o
  `nao_fiz` trava a subida. Feriado conta como na Ideal se marcado minima ou
  melhor: a planilha pede pelo menos a minima no feriado, e cumprir o que o
  plano pede nao pode derrubar a semana. Sem marcacao, continua abaixo;
- "ruins seguidas" quer dizer uma logo depois da outra: uma semana neutra ou
  boa no meio recomeca a contagem;
- efetivo = min(planejado, calculado). Como o calculado sobe no maximo 1 por
  semana, quem vai bem segue o plano, e quem tropeca fica atras dele ate
  firmar;
- o "hoje" do gatilho e min(dia visto, hoje de verdade), numa funcao so
  (`servico.cronograma.hoje_do_gatilho`), usada pela tela e pelo `radar
  hoje`. Dia passado mostra a carga que valia naquele dia; dia futuro mostra
  o plano. A primeira versao usava o dia visto nos dois casos, e olhar
  28/10 em setembro contava as semanas do meio como fechadas sem marcacao:
  duas ruins seguidas, nivel 1, 45 questoes em vez de 60;
- a semana e futura quando a ANTERIOR nao fechou, e nao quando ela propria
  ainda nao comecou. A diferenca e o domingo: com a semana 1 fechada no
  sabado, a segunda-feira seguinte ja tem nivel decidido pelo gatilho, e
  mostrar a carga do plano ali seria esconder o resultado;
- consequencia esperada: sem marcacao nenhuma, a semana 1 fecha com 6 dias
  abaixo e a semana 2 repete o nivel 1.

### A tela Hoje (etapa 4, 26/09/2026)

- `/hoje` e o PRIMEIRO item da barra: a navegacao passou a ter 7 destinos, os
  seis do sitemap e o cronograma na frente. Primeiro porque e a tela que eu
  abro todo dia: a especificacao pede saber o que estudar em um clique, e o
  cronograma responde isso com hora marcada. A home ganhou no topo o cartao
  "Hoje no cronograma", pelo mesmo motivo. Antes do ciclo ele diz quando
  comeca e leva ao primeiro dia (sumir ali escondia justamente o que eu
  preciso saber na vespera); depois do fim, some;
- toda conta sai pronta de `servico.cronograma.tela_do_dia`; o template so
  desenha. O relogio mora em `servico.cronograma.agora_local`, um lugar so,
  para o teste poder parar o tempo;
- as cores por tipo de faixa sao tokens `--faixa-*` no design.css, apontando
  para as cores que ja existiam. Tres hues novos (roxo, ciano, rosa) entraram
  porque os selos ja gastam azul, verde, amarelo e vermelho com significado.
  O registro do dia usa as cores dos selos: Ideal verde, Reduzida azul,
  Minima amarela, Nao fiz vermelha;
- recusa do formulario volta a tela com a mensagem e status 400, nunca 500.
  Os campos numericos chegam como texto, pelo mesmo motivo do converter_valor.

## Escuro e o padrao; claro e escolha, guardada em cookie (26/09/2026)

- **escuro e o padrao** em todas as paginas, e o tema do Windows
  (`prefers-color-scheme`) deixou de mandar: a previa aprovada da tela Hoje e
  escura, e eu estudo a noite;
- **claro e escolha minha**, pelo botao ☀️/🌙 na barra do topo. A escolha
  fica no cookie `tema` (claro|escuro, validade de dez anos). O botao e um
  link simples, sem JavaScript: `GET /tema?valor=claro&volta=/hoje` grava o
  cookie e volta para a pagina onde eu estava. So caminho interno serve de
  `volta`: o que nao comeca com "/" (ou comeca com "//") volta para "/";
- **o `?tema=` da URL continua valendo e vence o cookie** - serve para
  comparar os dois sem trocar a escolha. O botao tira o `tema` da volta, senao
  a URL venceria o cookie recem-gravado e o clique pareceria nao fazer nada;
- **um lugar so decide**: `tema_da_pagina(request)`, no `web/app.py`,
  exposta ao Jinja; todo `<html>` escreve `data-tema` com ela. Nenhuma rota
  repete a conta. No design.css o escuro vale em `:root:not([data-tema="claro"])`;
  as telas ainda nao migradas trocaram o `@media (prefers-color-scheme)` pelo
  mesmo seletor, para o botao funcionar nelas tambem;
- **barra do topo**: "Radar" a esquerda, as abas centralizadas, o botao a
  direita. Abaixo de 640px a marca e o botao dividem a primeira linha e as
  abas quebram em linhas embaixo, sem rolagem lateral.

### O visual novo da tela Hoje (etapa A2, 26/09/2026)

- **faixa azul no topo, de ponta a ponta**: a data, "Ciclo · Semana N de 6",
  os selos ⚡ Nivel, 🔥 dias seguidos e 🎯 Meta, e a navegacao entre dias.
  O 🔥 mostrou "–" ate a A6 criar a conta da sequencia: lugar reservado,
  nunca numero inventado;
- **duas colunas a partir de 1100px**: a linha do tempo a esquerda e uma
  coluna lateral de 300px, fixa ao rolar, com Agora, Esta semana (as
  pilulas, que sairam do topo) e Objetivo. O Cronometro (A5) ocupa o topo
  da coluna. No HTML a lateral vem ANTES da
  linha do tempo: abaixo de 1100px e ali que ela aparece, logo depois da
  faixa azul, sem CSS de reordenacao;
- **"Fim do Ciclo em N dias" conta de HOJE**, nao do dia que esta na tela:
  e quanto falta de verdade. Passou do fim, "Ciclo 1 encerrado";
- **o nome do alvo no Objetivo sai do `config/alvo.yml`** (`principal.nome`),
  como na home - nenhum nome de cargo escrito no template;
- **o bloco das 22h e sobreaviso**: azul-noite, texto claro e a etiqueta
  "🌙 sobreaviso · pode interromper". Tudo la dentro troca de cor (titulo,
  chips, "ver detalhe", filtro): o "suave" do sobreaviso e um lilas claro, e
  nao o cinza, que some no azul. O das 18h ganha so um azul leve;
- **o link da lei virou botao e diz onde abre** - "Ler no Planalto", "Ler na
  ALESC" ou "Ler a lei" - pelo dominio do proprio link (`rotulo_da_lei`, no
  app.py), sem campo novo no YAML. Dominio que so termina parecido
  ("falsoplanalto.gov.br") nao conta;
- **cor nova e token novo**, com a versao clara e a escura no design.css:
  `--heroi-*`, `--pontinho`, `--fundo-noite`, `--fundo-sobreaviso` e
  `--sobreaviso-*`. O pontilhado do fundo vale so na tela Hoje;
- no "Como foi o dia", a legenda da Minima passou a ser "Plano B".

### O check de cada faixa, e o formulario que sugere (etapa A3, 26/09/2026)

- **tabela nova `estados_do_dia`** (EstadoDoDia), separada do registro: o
  registro e a meta que EU declaro; o estado e o rascunho de durante o dia
  (as faixas riscadas e, na A4, o Plano B escolhido). Tambem e diario: nao
  entra em acerto medido nenhum;
- **a faixa e reconhecida por bloco + indice + TITULO**. So a posicao nao
  basta: se o cronograma.yml mudar, a faixa 2 da noite pode virar outra, e o
  check marcaria como feita uma faixa que eu nao fiz. Check cujo titulo nao
  bate e ignorado, sem erro; marcar com titulo velho e recusado ("recarregue");
- **o circulo e um formulario (POST /hoje/faixa), sem JavaScript**, e volta
  para `#faixa-bloco-indice`. So em hoje ou dia passado; pausa nao tem;
- **o formulario SUGERE, nunca marca**: a opcao sugerida fica tracejada, e
  "questoes feitas" chega com a soma das faixas marcadas (numero do nivel
  efetivo) so enquanto nao ha registro salvo. A regra, em ordem: todas as
  faixas que contam = Ideal; manha inteira + Direito da noite = Reduzida;
  alguma faixa de questoes = Minima; o resto, sem sugestao. "Contam" exclui
  pausa e bonus (opcional) - o mesmo "fora do total" de sempre. Na SOMA das
  questoes o bonus entra: se eu marquei, eu fiz;
- **backup em `data/estado_do_dia.json`**, no mesmo caminho do
  registro_estudo.json (exportar, importar, sincronizar), mescla pelo
  `atualizado_em`. O `apagar` do dia leva registro e checks, do banco e dos
  dois arquivos.

### O botao Plano B (etapa A4, 26/09/2026)

- **o cronograma.yml ganhou `essencial` (nos 30 dias uteis) e `plano_b`**, e
  entrou sozinho no commit `66b893f`. So ganhou: fora o texto novo da
  `minima`, nenhuma linha antiga mudou. Com `plano_b` no arquivo, todo dia
  util sem `essencial` para o carregamento com o dia na mensagem; sem
  `plano_b` (o YAML de teste), o `essencial` e opcional;
- **o essencial e SELECAO DO PLANO, nao "o que a banca mais cobra"**. Os
  artigos-chave foram escolhidos lendo o texto da lei, e nao contados nas
  provas: o Direito ainda nao tem assunto gravado no acervo, entao nao ha
  incidencia medida para sustentar "o mais cobrado". Dizer isso seria numero
  sem fonte. O cabecalho do cronograma.yml e o codigo repetem a ressalva;
- **nao ha resumo escrito por IA no Plano B**. O dia corrido e justamente o
  dia em que eu nao confiro nada: um resumo de lei feito por modelo, que troca
  prazo, percentual ou numero de artigo, seria estudado sem desconfianca. O
  Plano B manda ler os artigos NO TEXTO OFICIAL (o link da teoria do dia) e
  fazer questoes de prova - duas fontes que nao inventam;
- **`montar_plano_b` e funcao pura** (cronograma.py): o tema, o filtro e a
  materia saem das faixas do proprio dia (`rampa: direito` e `rampa:
  portugues`); os numeros (8/15 de Direito, 0/4 de Portugues, 10/15 min de
  essencial) saem do `plano_b` do arquivo, e nao da rampa - o Plano B nao
  sobe com o nivel. Sem horario: a tela mostra 1º, 2º, 3º;
- **o Plano B escolhido fica no EstadoDoDia (`plano_b` = 30 ou 60)**, com o
  mesmo backup dos checks. Os checks valem no bloco `plano_b` (o titulo das
  faixas nao muda entre 30 e 60, entao trocar o tempo nao perde o que ja
  risquei). Voltar ao plano completo so apaga o `plano_b`: os checks do dia
  normal continuam la;
- **com Plano B ativo a Minima vem marcada no formulario**, mas nada e salvo
  sozinho: o registro so existe quando eu clico em Salvar. Dia futuro nao
  tem o botao (e o POST e recusado); domingo tambem nao;
- o `radar hoje --plano-b 30` so MOSTRA o Plano B no terminal: nao ativa.

### O cronometro: a UNICA excecao ao "sem JavaScript" (etapa A5, 26/09/2026)

- **o cronometro e o unico JavaScript do radar**, e mora num arquivo so,
  `src/radar/web/static/cronometro.js`. Nenhum `<script>` inline, em tela
  nenhuma. A excecao existe porque avisar "acabou, vai para a pausa" com som
  e notificacao do Windows e coisa que so o navegador faz;
- **a tela funciona igual sem ele**: o servidor escreve o cartao do
  cronometro, o aviso em tela cheia e os botoes ▶ com `hidden`, e so o
  script tira. Sem JavaScript, nada do cronometro aparece, e o resto (checks,
  Plano B, "Como foi o dia") continua sendo formulario;
- **o servidor diz o que a faixa e, o script so conta**: cada faixa que nao
  e pausa leva `data-duracao`, `data-titulo` e o que vem depois
  (`data-proxima-titulo`, `-pausa`, `-duracao`, `data-depois-titulo`),
  calculado em `TelaDoDia.proxima_de` - atravessa os blocos. As faixas de
  questoes do Plano B ganharam duracao (questoes x minutos_por_questao) para
  terem o que contar;
- **conta a DURACAO CHEIA a partir do clique**, e nao ate o horario do plano:
  50 min de teoria sao 50 min mesmo comecando atrasado;
- **o fim fica no localStorage** (a hora de termino, nao "quanto falta"):
  recarregar ou trocar de aba nao perde nada. O alarme e UM setTimeout ate o
  termino, refeito quando a aba volta a ficar visivel; o relogio mm:ss da
  tela atualiza a cada segundo, mas o alarme nao depende dele;
- **o aviso e um trio**: tela cheia (veu `--cor-veu`, borda laranja), som
  que repete ate o OK (Web Audio, sem arquivo de som) e notificacao do
  Windows (Notification API, `requireInteraction`, uma tag so para nao
  duplicar entre abas). "OK, pausa!" comeca a pausa sozinho;
- **o som so comeca depois de um clique meu** (regra dos navegadores): o
  contexto de audio nasce no ▶ ou no Testar; depois de recarregar a pagina
  com o cronometro rodando, o primeiro clique nela religa;
- **notificacao do Windows so em contexto seguro** (localhost). Aberto pelo
  IP na rede, o Testar avisa que ali so ha a tela e o som; com a permissao
  negada, ensina a liberar (cadeado -> Notificacoes -> Permitir) e lembra do
  "Nao perturbe"/Assistente de Foco;
- o comportamento do JS e testado na mao; o pytest segura o contrato (o
  script, os data-*, pausa sem ▶, tudo `hidden` sem JS).

### A sequencia 🔥 e a frase da semana (etapa A6, 26/09/2026)

- **a sequencia conta dias do PLANO seguidos sem zerar**: ideal, reduzida ou
  minima mantem; dia sem marcacao ou "nao fiz" quebra. Domingo nao esta no
  plano, entao nao quebra. Conta de ontem para tras; HOJE entra so se ja
  estiver marcado (o dia ainda nao acabou, e nao marcar ate agora nao e
  zerar - mas marcado como "nao fiz", zera). E contada a partir do hoje de
  verdade, e nao do dia aberto na tela, como o "fim do ciclo em N dias";
- **a frase usa a MESMA regra do gatilho** e os numeros do YAML: sobe com
  `sobe_com_dias_na_ideal` dias completos e nenhum "nao fiz"; feriado feito
  como Minima ou melhor conta como completo. "Dia completo" e o nome na tela
  do que o codigo chama de "ideal";
- **dia que ja passou sem marcacao conta como perdido** na frase: "restam"
  so os dias sem marcacao de hoje em diante. Da para marcar um dia passado
  depois, e ai a frase muda - mas prometer com um dia que eu nao marquei
  seria contar com o que nao aconteceu;
- **a frase some** em semana futura, fora do ciclo, e na ULTIMA semana do
  ciclo abaixo do teto: la nao existe "semana que vem" para subir. No teto
  (nivel 6), a frase e a da carga maxima;
- "o que sobe" diz so a materia que muda de um nivel para o outro ("20
  questoes de Direito"), lida da rampa, nunca escrita a mao;
- na segunda sem nada marcado, a frase e "Faca 5 dias completos...", e nao
  "0 dias completos!";
- tudo em `servico.cronograma` (`sequencia` e `frase_da_semana`), contas
  puras com teste de data fingida; o template so escreve.

### Abrir no celular: `radar web --rede` (etapa A7, 26/09/2026)

- **e opt-in**: sem `--rede`, o servidor continua escutando so em
  127.0.0.1, como sempre. Abrir para a rede e uma decisao de cada vez que eu
  subo o radar, e nao um padrao - o notebook tambem entra em Wi-Fi que nao e
  o de casa (cafe, rodoviaria), e ali o radar nao pode estar aberto por
  descuido. O `--host` continua existindo; o `--rede` e o atalho com nome
  claro, e e ele que mostra o endereco para o celular;
- **nao ha login**, de proposito: o radar tem um usuario so, eu, e o que ele
  guarda (concursos publicos, o meu diario de estudo) nao e segredo. Login
  exigiria senha guardada, sessao e tela de entrada - manutencao que nao
  compra nada numa rede de casa. O custo aceito, e escrito no README e na
  propria saida do comando: qualquer pessoa no meu Wi-Fi consegue abrir. Se
  um dia o radar sair de casa (internet, rede do trabalho), ai sim login
  entra na conversa;
- **o IP e descoberto sem ir a internet**: um socket UDP "conectado" a um
  endereco privado so pergunta ao Windows por qual placa sairia o pacote -
  nada e enviado. Sem rota, tenta o nome da maquina; sem nada, a saida manda
  rodar `ipconfig`, em vez de chutar um endereco;
- a regra de firewall do README e so do perfil **Privado**: em rede publica
  a porta continua fechada mesmo com o `--rede`.

## Limpar os simulados vazios (etapa A8, 26/09/2026)

- **cada clique em "Treinar" cria uma rodada**, com as questoes sorteadas e
  nenhuma resposta ainda. A que eu abandono fica para sempre no banco e no
  data/simulados.json: em 26/09 eram 7, todas com 20 questoes e 0 respostas;
- **`radar descartar --vazios` apaga so o simulado SEM NENHUMA resposta e
  criado ha MAIS DE 1 DIA**, do banco e do arquivo (pelo mesmo
  `esquecer_simulados` do descartar - so do banco, o proximo importar o
  traria de volta). O de hoje fica: pode ser a rodada que eu abri e ainda vou
  fazer. Mostra quais (data e hora de criacao) e pergunta; `--sim` pula;
- **uma resposta que seja e historico, e nunca sai** por esta limpeza. A
  conferencia se repete dentro da transacao que apaga, para uma resposta dada
  entre a listagem e o apagar tirar o simulado da limpeza;
- **o `radar sincronizar` limpa sozinho, sem perguntar**, entre o
  reclassificar e o exportar, e diz quantos sairam. Sem pergunta porque nao
  ha o que perder: por definicao, nada ali foi respondido. Antes do exportar,
  para o arquivo que vai ao GitHub ja sair limpo.

## Parte B: as outras telas no design system (a partir de 26/09/2026)

- **uma tela por etapa**, sem mudar funcionalidade nem dado: a tela passa a
  usar so o design.css (`body class="ds"`, `ds-pagina`, `ds-cabeca`,
  `ds-cartao`, `ds-campo`, `ds-botao`), fica com a cara da tela Hoje nos dois
  temas, e o CSS antigo dela (as cores coladas no `<style>`) sai;
- **o design system ganhou o que as telas antigas usavam e ele nao tinha**,
  so com os tokens que ja existiam: a tabela (`ds-tabela`, numero em `ds-n`,
  e `ds-rolagem` para a tabela larga rolar dentro do cartao no celular) e
  tres variantes de botao - `ds-botao--secundario` (contorno, a acao que nao
  gasta nem apaga), `ds-botao--perigo` (apaga de verdade) e `ds-botao--ia`
  (gasta dinheiro com a API), os dois ultimos no vermelho da familia IA;
- **B1, Estudar**: simulado.html e geradas.html. A simulado.html so desenha a
  escolha da rodada (a rodada e a questao.html, ja migrada): o CSS de
  questao, resultado e revisao que ela ainda carregava estava sem uso e
  saiu. O aviso "isto treina, nao mede" virou bloco da familia IA
  (`ds-bloco--ia`), no vermelho do selo de IA - antes era roxo, cor que o
  design system nao tem.

## O orgao sozinho nao marca o alvo principal (etapa C1, 26/09/2026)

- **o defeito**: `principal.orgaos` aceitava o nome da secretaria sozinho. A
  SEJURI tambem faz selecao de outros cargos, e dois itens viraram alvo
  principal - sirene no Telegram e linha na home - sem ser o meu concurso:
  "SEJURI (SC) publica edital de selecao com salario de R$ 8,7 mil" (vaga no
  CASE) e "SEJURI SC divulga novo edital com vaga para Medico". O orgao diz
  QUEM publicou, nao O QUE: a mesma secretaria contrata medico, socioeducativo
  e policial penal;
- **agora, sem o cargo no texto, o orgao precisa de confirmacao**: uma palavra
  de `orgao_exige_um_de` ("concurso publico") ou a banca ser uma das `bancas`
  das edicoes anteriores (FEPESE) - e nenhuma palavra de `orgao_exclui`
  ("processo seletivo", "selecao", "socioeducativo", "case"). As listas moram
  em config/alvo.yml, nunca no codigo. Com o cargo no texto nada disso vale:
  o titulo de 2013 lista o Agente Penitenciario e o Socioeducativo juntos;
- **a banca entrou como confirmacao por causa de um item real**: a pagina da
  FEPESE de 2019 cujo titulo e so "2019 – Secretaria de Estado da
  Administracao Prisional e Socioeducativa", sem cargo e sem "concurso
  publico". Pela regra so de palavras ela perderia a marca, e ela e o meu
  concurso. A banca continua sem marcar nada sozinha: ela so confirma um
  orgao que ja casou;
- "socioeducativo" e por palavra inteira: nao casa com "Socioeducativa", o
  nome da secretaria em 2019;
- o motivo diz o que confirmou ("fala em SAP e em concurso publico", "e a
  banca e FEPESE"): continuo podendo auditar a marca. O `radar reclassificar`
  de 26/09 tirou a marca dos dois seletivos e manteve os quatro concursos de
  2013, 2016 e 2019.

## Tarefa no logon, e nao servico do Windows (etapa D1, 27/09/2026)

O radar precisa estar no ar quando eu abrir o navegador, e o backup precisa
rodar todo dia sem eu lembrar. Servico do Windows seria o caminho "profissional"
e e o errado aqui:

- **servico pede administrador** para instalar (`sc create`, ou um empacotador
  tipo NSSM). Tarefa do proprio usuario qualquer um cria - sem UAC, sem senha
  de admin, e eu posso recriar tudo depois de formatar sem pensar duas vezes;
- **servico roda sem usuario logado**, e isso e desvantagem: o radar so serve
  quando eu estou na frente do PC. Servico rodando sozinho as 3h da manha e
  processo consumindo memoria para ninguem;
- **servico nao tem "roda quando eu ligar o PC se perdeu o horario"**. A tarefa
  tem (`StartWhenAvailable`), e e o que faz o backup das 23h30 acontecer mesmo
  nas noites em que eu desliguei o PC as 22h;
- **servico e dificil de parar**: `services.msc`, ou `net stop` no prompt de
  administrador. Aqui e um .bat na Area de Trabalho, ou `radar parar`;
- **servico esconde o erro.** O que nao sobe vira uma linha no Visualizador de
  Eventos. A tarefa deixa o erro em `data/logs/`, e a tela Mais o mostra.

Os detalhes que vieram com a escolha:

- **XML, e nao a linha de comando do schtasks.** `schtasks /Create /SC DAILY
  /ST 23:30` nao tem opcao para o `StartWhenAvailable`, que e justamente o que
  eu quero. Por arquivo XML da, e o arquivo sai em **UTF-16**: com UTF-8 o
  schtasks recusa dizendo "o XML da tarefa contem um valor formatado
  incorretamente", mensagem que nao aponta para a codificacao;
- **as duas tarefas chamam o `pythonw.exe -m radar.automacao`**, e nao o
  `radar.bat`. O .bat abriria uma janela preta em todo logon e as 23h30. Pelo
  mesmo motivo o `__main__` daquele modulo nao imprime nada: o pythonw nao tem
  console, e o rich da CLI estouraria escrevendo num stdout que nao existe;
- **a tarefa da web nao tem limite de execucao** (`PT0S`). O Agendador conta a
  tarefa como rodando enquanto o servidor filho viver, e qualquer limite
  mataria o radar no meio do dia. A do backup tem uma hora: sincronizar
  pendurado numa credencial nao pode ficar assim ate amanha;
- **o backup e `radar backup`, um embrulho de tres linhas em volta do
  `radar sincronizar`.** A tarefa nao podia chamar o sincronizar direto porque
  o log precisa de nome com a data (`%date%` do cmd muda de formato com o
  idioma do Windows) e porque alguem tem que escrever a linha final dizendo se
  deu certo. Essa linha (`RESULTADO: ok` / `RESULTADO: falhou - <motivo>`) e o
  contrato com a tela Mais - procurar a palavra "erro" no meio da saida seria
  adivinhar, e adivinhar erra calado;
- **`radar parar` confere se o processo ainda e um Python** antes de matar.
  Numero de processo se reaproveita: com o PC desligado na tomada, o
  `data/radar_web.pid` sobra apontando para um numero que amanha pode ser o
  Bloco de Notas;
- **os atalhos vao para a Area de Trabalho que o registro do Windows informa**,
  e nao para `%USERPROFILE%\Desktop`. Com o OneDrive ligado a pasta real e
  `OneDrive\Desktop`, e atalho escrito no caminho antigo simplesmente nao
  aparece na tela;
- `data/radar_web.pid` e `data/logs/` ficam **fora do git**: sao rastro de
  execucao desta maquina, e o robo do GitHub nao tem nada a ver com eles.
## O caderno de erros tem tabela, e a regra certa e obrigatoria (etapa E1, 27/09/2026)

Tres decisoes, e a primeira e a que mais vai me poupar discussao comigo mesmo:

- **duas revisoes 1-7-30, de proposito.** Ja existia uma
  (`servico/espacada.py`), calculada do historico de respostas e sem tabela
  nenhuma. O caderno tem tabela (`erros_anotados`) porque a ORIGEM e outra: a
  do espacada sai do que eu respondi DENTRO do radar, e pode ser recalculada
  a qualquer momento; a do caderno sai do meu julgamento - "ja sei" nao esta
  escrito em lugar nenhum a nao ser ali. Sem tabela, apertar "ja sei" nao
  guardaria nada. Os INTERVALOS vem do `espacada`, para nao existirem dois
  numeros para a mesma ideia;
- **a `regra` e obrigatoria.** Anotar "errei a questao 42" nao ensina nada;
  "o prazo de progressao conta da data da prisao, nao da condenacao" ensina. E
  a regra que volta em 1, 7 e 30 dias - sem ela, o caderno seria uma lista de
  derrotas. A recusa e em voz alta, na propria tela, e nao um campo vazio no
  banco;
- **o caderno NAO mede nada**, pela mesma razao do "Como foi o dia": o que
  esta nele eu digitei a mao, e quase tudo vem do Qconcursos. Ele nao entra em
  Meu foco, Onde estudar, home nem compilado - la so conta questao respondida
  dentro do radar, uma por uma. Ha teste segurando isso.

O resto veio junto:

- a chave do backup (`data/caderno_erros.json`) e o `criado_em`, e nao a data:
  num dia eu anoto cinco erros. Microssegundo separa dois erros; dois erros
  criados no mesmo microssegundo nao existem;
- **"para rever hoje" inclui o atrasado.** Erro que venceu anteontem e nao foi
  revisado nao pode desaparecer da fila - desaparecer e o que ele faria se a
  comparacao fosse por igualdade de data;
- a porcentagem do "O que mais te derruba" so aparece com 3 erros ou mais na
  materia. De dois erros, um e 50%, e 50% de dois nao e padrao nenhum;
- **"Ainda erro" desarquiva.** Se eu apertei aquilo num erro que estava no
  arquivo, ele nao estava aprendido;
- o botao "Anotar erro" so aparece nas faixas em que eu respondo questao
  (questoes, revisao, simulado, diagnostico): na teoria da manha nao ha o que
  errar. A Revisao semanal do sabado nao tem materia, e por isso ganha, no
  lugar, o link para os erros da semana;
- a aba **Revisao** passou a abrir no caderno, e nao nos Macetes: o que eu
  errei ontem manda mais que o costume da banca.
## O que conta no volume, no acerto e na meta (etapa E2, 27/09/2026)

> **Revista em 01/10/2026 (Etapa 0, decisoes 4 e 7):** a contagem vai para uma
> fonte unica com recortes de nome fixo (Etapa 1C), e o Meu foco e o Onde
> estudar passam a usar radar + anotado a partir da Etapa 4.
>
> **Revista de novo em 01/10/2026 (Etapa 1C):** feita a fonte unica
> (`servico/metricas.py`). O que mudou aqui: o registro do dia deixou de
> guardar a copia do total (o item "salvar a meta grava o total" abaixo nao
> vale mais), e o `radar hoje --feitas` grava estudo extra. Ver "A fonte unica
> das metricas", no fim do arquivo.

Tres origens medem o meu estudo, e elas nao se misturam do mesmo jeito:

- **VOLUME** (questoes feitas, horas) **soma tudo**: as faixas do plano que eu
  marquei, o estudo extra e as questoes que eu respondi dentro do radar. Volume
  e tempo gasto, e tempo gasto nao tem asterisco;
- **o ACERTO principal tambem soma as tres**, e embaixo dele a tela mostra de
  onde ele vem: "radar: X% em N · anotado: Y% em M". O primeiro foi medido
  questao por questao contra o gabarito; o segundo fui eu que digitei. Sao
  numeros de confianca diferente, e por isso aparecem separados - mas somar
  apenas o radar seria fingir que as 40 questoes que eu faco no Qconcursos nao
  existem;
- **a comparacao com a META usa so questao SEM CONSULTA.** A meta e de prova, e
  na prova nao ha lei aberta. A faixa de aprendizagem de Direito - a
  `rampa: direito`, cujo proprio detalhe diz "PODE consultar a lei" - ja vem com
  a caixa "com consulta" MARCADA: ela treina, e treinar com a lei aberta e o
  jeito certo de aprender o artigo. O que ela nao pode e me dar a impressao de
  que eu bati a meta;
- **questao escrita por IA fica fora de todo acerto.** Ela conta no volume,
  porque o tempo foi gasto, e nunca no acerto - e a mesma decisao da fase das
  questoes geradas: elas treinam, nao medem o que a banca cobra;
- **o Meu foco e o "Onde estudar primeiro" continuam usando SO o que o radar
  mede, questao por questao.** Eles respondem "o que a banca cobra de mim e
  quanto eu erro nisso", e a resposta nao pode depender de numero digitado a
  mao. O diario (faixas, extra, caderno de erros) fica na tela Hoje, onde eu
  sei o que estou lendo.

O resto veio junto:

- **os campos "questoes feitas" e "acertos" sairam do "Como foi o dia".** Eram
  eles que faziam o diario nao bater com o que eu tinha feito: eu somava de
  cabeca e esquecia os extras. Agora o numero e calculado, e salvar a meta grava
  o total. Registro antigo, com numero digitado, continua valendo como esta - e
  aparece na tela dizendo que foi gravado naquele dia;
- **a META do dia continua sendo escolha minha.** O estudo extra nao muda a
  meta nem a sugestao: fazer mais do que o plano pedia nao transforma um dia
  reduzido em ideal;
- **cada faixa de questoes guarda os numeros no proprio check** - minutos,
  questoes, acertos, consulta, materia e assunto -, e nao so a posicao dela no
  arquivo. E o Ciclo 2 que exige isso: quando o cronograma.yml mudar, a faixa 2
  da noite de 20/10 sera outra coisa, e o historico tem que continuar contando o
  que eu fiz naquele dia. Check antigo, sem os campos, e preenchido pelo plano
  enquanto a faixa existir nele;
- **"fiz" pode ser diferente do que o plano pedia** (25 no lugar de 15): mesmo
  tema, mais questoes. Os minutos continuam sendo os da faixa - quanto tempo eu
  gastei de verdade eu nao sei, e inventar seria pior;
- **"acertei" vazio conta no volume e em acerto nenhum.** Foi o que aconteceu:
  eu fiz e nao anotei quantas acertei. Contar como zero acerto seria mentira;
- **o extra com `onde = radar` nao guarda questao nem acerto**, so o tempo: o
  radar ja contou cada questao dele uma por uma, e somar aqui contaria o mesmo
  acerto duas vezes;
- **o bloco `materias`** (as 11 materias do edital de 2019, com as questoes de
  cada uma e a minha meta) mora no config/cronograma.yml, e o carregamento
  confere nome repetido, meta maior que as questoes da materia e materia escrita
  numa faixa que nao existe na lista. A ultima e a que pega erro de digitacao:
  "Direito Penall" nunca mais somaria em lugar nenhum;
- **`materias_mistas`** e a saida para a faixa que tem rotulo de materia mas
  cobre mais de uma - hoje so o R+7 que refaz os erros dos diagnosticos, que
  sao de Raciocinio Logico e de Portugues juntos. Ela conta no volume e no
  acerto geral, e em nenhuma materia, como o simulado misto de sabado.
## A tela de Semanas usa as mesmas contas do dia (etapa E3, 27/09/2026)

Nenhum numero desta tela e calculado de novo, e isso e a decisao:

- **"dias completos" e o `balanco_da_semana` do cronograma**, a MESMA funcao que
  o gatilho usa para decidir o nivel - incluindo o feriado cumprido na minima. A
  tela nao pode dizer "4 dias completos" enquanto o gatilho conta 3 e mostra um
  nivel que nao bate com a contagem ao lado;
- **volume e acerto somam dia por dia, pelo `totais_do_dia`**, o mesmo que a
  tela Hoje usa. Escrever uma soma semanal separada era mais rapido e garantia
  que, no dia em que uma das duas mudasse, elas divergiriam em silencio;
- **o `hoje` vai direto para o gatilho.** Passar pelo `hoje_do_gatilho` (que
  olha o relogio de verdade) deixava todas as semanas como "futura" quando o
  teste para o tempo - e um teste que nao consegue simular dezembro nao testa
  nada do Ciclo 1.

O resto do que decidi aqui:

- **semana futura nao aparece**: ela nao tem o que contar. A semana corrente
  aparece marcada "em andamento", porque os numeros dela sao parciais e mostrar
  isso e mais honesto do que exibi-los como se ela tivesse fechado;
- **a semana em andamento nao concorre ao 🏆**: comparar meia semana com uma
  semana fechada e competicao torta;
- **a seta do acerto compara PONTO a ponto** (72% para 68% = -4), que e como eu
  leio "caiu 4 pontos", e nao a razao entre os dois. Semana sem acerto medido
  nao compara acerto nenhum - comparar com o nada daria uma flecha inventada;
- **em erros, menos e melhor**: a cor da seta sai de `melhor`, e nao do sinal da
  diferenca;
- **a chave da reflexao e a SEGUNDA-FEIRA**, e nao o numero da semana: numero e
  do ciclo e reinicia no Ciclo 2; a data nao reinicia nunca;
- **texto vazio na reflexao apaga o campo.** E assim que eu desfaco uma frase
  escrita errado, sem um botao a mais na tela;
- **o grafico e CSS puro** (altura por regra de tres com a maior semana), como a
  pizza dos Macetes: o unico JavaScript do radar continua sendo o cronometro.
## Minhas materias: o recorte, a amostra e o nome (etapa E4, 27/09/2026)

- **o recorte e o CICLO que esta no cronograma.yml**, e nao a vida inteira.
  Misturar o meu acerto de hoje com o da primeira semana responde outra
  pergunta - e e a pergunta errada para decidir o que estudar amanha. A tela
  diz "neste ciclo" em voz alta, e o grafico semana a semana ja deixava isso
  implicito;
- **20 questoes sem consulta e o minimo para eu acreditar numa porcentagem.**
  (*Mantido na materia pela decisao 6 da Etapa 0, 01/10/2026, que estende a
  regra ao sistema inteiro.*)
  Abaixo disso a materia entra como "sem dado" e a barra ganha o aviso "amostra
  pequena": 100% em cinco questoes nao e 100% de nada;
- **materia sem amostra fica FORA da projecao** - nao entra como zero nem como
  a media das outras. As duas coisas seriam invencao; a tela prefere dizer
  quantas materias ficaram de fora e projetar so com o que tem base. Por isso o
  selo e o de tendencia, e nao o de calculado;
- **o nome casa pela regra que o radar ja usa** (`compilado.mesma_materia`), e
  nao por texto exato: o caderno de 2013 escreve "Direito Processo Penal" e o
  edital de 2019 "Direito Processual Penal". A mesma regra vale para o caderno
  de erros e para o estudo extra;
- **o "entra no Ciclo N" sai primeiro do PLANO**, e so depois do texto do mapa:
  se a materia tem faixa nos dias gravados, o ciclo daqueles dias e fato. Para o
  resto, a mencao do mapa ("Processo Penal") so decide quando casa com UMA
  materia - "Penal" sozinho casa com tres, e ai a tela nao diz nada em vez de
  dizer o ciclo errado. A comparacao ali e por palavra (prefixo comum de seis
  letras: "processo" e "processual" sao a mesma), e nao pela distancia de texto
  do `mesma_materia`, que apelido nao passa;
- **"aulas vistas" conta as faixas de estudo da manha** (teoria, portugues e
  raciocinio), uma por materia por dia. A `lei_seca` fica de fora: ela le a lei
  do MESMO tema da teoria daquele dia, e contar as duas faria o programa de
  Direito andar em dobro;
- **o treino de IA conta para "eu ja encostei nesta materia"**, e so para isso.
  Ele nao entra em acerto nenhum, mas dizer "ainda nao estudei" depois de 20
  questoes geradas seria falso;
- **o grafico e SVG desenhado no servidor.** Semana sem questao sem consulta nao
  vira ponto: a linha pula, em vez de fingir um zero que eu nao tirei. Com menos
  de dois pontos nao ha grafico - dois pontos e o minimo de uma linha.

## De 28/09 a 01/10/2026: o primeiro dia de estudo, o Actions e o jeito de trabalhar

- **Guarda Municipal de Florianopolis e de Balneario Camboriu continuam com o
  👀, sem sirene (cancela a "C1b").** Eu so quero ficar sabendo quando sair
  edital, e o `de_olho` ja faz isso: fura o teto de avisos e ganha cartao na
  home. A sirene e o nivel do alvo principal (o concurso que eu espero ha anos)
  e dar a ela um segundo uso apagaria a diferenca que ela existe para marcar;
- **teste nao depende do sistema operacional nem da data de hoje.** O GitHub
  Actions e o unico lugar que roda em Linux e com a data de verdade, e la
  quebraram tres testes que passavam no meu Windows: um comparava o executavel
  com `pythonw.exe` (no Linux nao existe), um assumia 28/09 como futuro e um
  tinha a data fixa de 17/09, que sai da janela de 30 dias de novidade e falha
  em torno de 17/10. A regra: o teste compara com a funcao do proprio modulo
  (`python_sem_janela()`), fixa o relogio (`agora_local`) ou usa data relativa a
  `agora()`. Conferido rodando a suite inteira com o relogio simulado em
  20/10/2026, 10/11/2026 e 15/03/2027. A lib de relogio simulado so foi usada
  fora do repositorio, para auditar; nao virou dependencia;
- **a profundidade de estudo de cada tema tem que seguir o que a FEPESE cobra
  de verdade, e nao so o edital de 2019.** Foi o que eu decidi no primeiro dia
  do Ciclo 1, ao ver a faixa de teoria de 50 minutos para "Aplicacao da lei
  penal (arts. 1o a 12)", sem nenhuma indicacao de quanto a banca cobra cada
  artigo. O cronograma atual foi montado pelo conteudo e pelo peso das materias
  no edital; a incidencia por tema nunca foi medida, porque as questoes do
  acervo nao tem assunto gravado (0 questoes de Direito com assunto, desde a
  etapa 15-0). Tema que a banca nunca cobriu deve ser leitura por cima, e a
  tela deve dizer isso com o numero. **Direcao decidida, desenho em aberto**
  (pendencias.md, bloco B);
- **a lei seca de 40 minutos por dia, como esta, vai mudar.** Sao 30 faixas
  (cerca de 20 horas) de ler o artigo inteiro grifando "salvo", "somente",
  "vedado", sem saber quais artigos caem. A leitura certa e a dos artigos que a
  banca cobrou, do jeito que cobrou. O formato novo nao foi decidido;
- **questao gerada so e boa quando parte de questao real.** O modo `variacao`
  (muda o cenario, mantem a regra e o gabarito oficial da questao de origem) e
  o seguro; o `do_zero` e excecao, para assunto sem nenhuma questao real. Sem
  assunto gravado no Direito, as 40 questoes geradas ate hoje sao todas
  `do_zero`: imitam o estilo da banca, mas nenhuma esta ancorada num gabarito
  oficial. Continuam treinando e nunca medindo (regra que ja valia). Gravar o
  assunto e o que destrava o `variacao`;
- **uma conversa por etapa, e o estado mora no repositorio.** Cada mensagem
  reenvia a conversa inteira; o cache de prompt barateia a parte repetida mas
  expira se eu paro um tempo e nao sobrevive a troca de modelo; e conversa
  muito longa e resumida sozinha, perdendo detalhe. Por isso: termina a etapa,
  commit, `/clear`, e o chat novo comeca lendo o `CLAUDE.md` e os docs. Toda
  etapa fecha atualizando `historico.md` (o que foi feito), `decisoes.md` (o
  que foi decidido e por que), `pendencias.md` (o que sobrou) e o "Estado
  atual" do `CLAUDE.md`. Resumo colado no chat novo e a pior opcao: custa token
  de novo, envelhece e depende de eu lembrar de colar;
- **modelo: o mais forte para analisar e decidir, o mais barato para etapa
  mecanica, escolhido no inicio da conversa e sem trocar no meio** (a troca
  perde o cache).

## Etapa 0 do pedido de evolucao: o plano e o que ele decidiu (01/10/2026)

O pedido e o [docs/novo.md](novo.md); o plano das Etapas 1 a 8, com a ordem e
o detalhe de cada uma, e o [docs/roteiro.md](roteiro.md); o andamento fica no
[docs/progresso.md](progresso.md). Na Etapa 0 so esses dois arquivos podiam ser
criados, entao as decisoes dela entram aqui no primeiro commit da Etapa 1:

1. **branch sempre `main`**, sem branch nem PR. A `claude/busy-davinci-fgt1br`
   foi apagada: nao tinha nada fora da `main`;
2. **uma conversa por etapa (ou subetapa)**, com o estado no repositorio: o
   roteiro, o progresso e os docs;
3. **o dia 28/09 foi investigado com os dados reais.** Penal 11 questoes / 6
   acertos e Portugues 10 / 7 (anotados, do Qconcursos), mais 10 de IA
   respondidas no radar: o "Fiz hoje" mostrou 31 questoes, 13 acertos e 8 erros.
   Nao houve contagem dupla, fuso errado nem dado perdido: a linha nao fecha
   porque as 10 de IA entram no volume e, pela regra, nunca no acerto, e a
   linha nao dizia isso. O registro do dia guardou "31 questoes, 13 acertos",
   que se le como 18 erros. E o Bonus foi marcado como feito com 0 questoes
   (os 25 min dele estao dentro das 3h50). O conserto e da 1C e da 1D;
4. **numeros iguais em toda tela:** uma fonte unica de contagem, com recortes
   de nome fixo - *medido no radar*, *anotado* (faixas e estudo extra, que vem
   do Qconcursos), *treino de IA* e *total*. Mesmo recorte e mesmo periodo dao
   o mesmo numero, e cada tela escreve o recorte que mostra (Etapa 1C);
5. **os selos passam a quatro: 🟢 fonte oficial · 🔵 estatistica do acervo ·
   🟡 analise automatica · 🟣 gerado por IA.** Substitui os "seis selos, quatro
   cores" (🟦🟩🟨🟥) da fase 1 da especificacao. Vale quando a Etapa 7A trocar;
   ate la as telas seguem com os antigos;
6. **limites de amostra num lugar so, para o sistema inteiro**, em respostas
   sem consulta: materia 20, assunto 10, subassunto ou elemento 6. Estados:
   *amostra insuficiente* (abaixo do minimo: fora de ordenacao e de projecao),
   *precisa revisar* (abaixo de 60%), *em aprendizado* (de 60% ate abaixo da
   meta), *desempenho consistente* (na meta ou acima) e *bom desempenho com
   amostra suficiente* (na meta, com o dobro do minimo, em dois dias ou mais).
   A meta e a da materia no `config/cronograma.yml`; sem ela, a da prova (79
   de 100). Motivo: com 10 questoes a margem de uma porcentagem ainda e de ~30
   pontos; com 20, de ~22. Substitui os minimos 5/3 do Onde estudar e o 20 de
   Minhas materias quando a Etapa 4 aplicar;
7. **desempenho por conteudo usa o radar e o Qconcursos**, sempre com a divisao
   "radar X% em N · anotado Y% em M", e questao de IA nunca entra. A partir da
   Etapa 4 o Meu foco e o Onde estudar passam a usar esse desempenho - isso
   revisa a decisao E2, que os deixava so no radar. Ate la ficam no recorte
   *medido no radar*, escrito na tela;
8. **as 162 questoes validas do alvo sao classificadas pelo Claude Code**, no
   fluxo pedido/importar, com procedencia, e conferidas por mim (Etapa 3A);
9. **fichas de tarefa (§11 do novo.md):** o texto escrito por IA e aceito,
   marcado 🟣, com procedencia e conferivel;
10. **2019: o caderno masculino e igual ao feminino (AP)**, que e o auditado;
11. **o concurso-alvo tem so as provas de 2013 e 2019**, ja no banco; nao ha
    prova nova para importar. O acervo complementar e o que ja esta no banco
    (Socioeducativo 2016 e as provas FEPESE de prefeituras), e o levantamento
    da §5 vira consulta a esse acervo (Etapa 3B);
12. **o ANKI e desligado por uma chave no `config/cronograma.yml`**, sem apagar
    nada, ja no Ciclo 1 (Etapa 6A);
13. **rotina com questoes tambem de manha**, ja no Ciclo 1, com a proposta
    aprovada antes de mexer no cronograma (Etapa 6A);
14. **as pendencias do `docs/pendencias.md` foram encaixadas nas etapas** (a
    tabela "Pendencias × etapas" do roteiro). A ordem difere da do novo.md em
    tres pontos, explicados no roteiro: o Actions primeiro (1A), a rotina do
    Ciclo 1 antecipada (6A) e a Etapa 3 dividida em alvo (3A) e complementar
    (3B).

## Texto de evento e previsao na tela (Etapa 1B, 01/10/2026)

1. **A descricao do evento e traduzida so na exibicao** (`eventos.para_tela`,
   filtro `evento` no Jinja). O banco e o `eventos.json` continuam com
   "Situacao: a -> b": a descricao e parte da chave de deduplicacao do acervo
   (`CHAVE_DO_EVENTO`), e reescrever o texto gravado duplicaria eventos na
   proxima importacao. So frases que o proprio `eventos.py` monta sao
   reconhecidas, e inteiras; qualquer outro texto (titulo de noticia) passa
   como veio;
2. **a frase diz para onde o concurso foi** ("As inscricoes encerraram"). Se a
   situacao **anda para tras** no ciclo (o banco real tem
   "inscricoes_abertas -> edital_publicado"), a frase diz "A situacao voltou
   de ... para ...", e nao "O edital foi publicado": evento e fato observado;
3. **o nome legivel da situacao mora em `eventos.NOME_DA_SITUACAO`**, e o
   `SITUACAO_LEGIVEL` da web aponta para ele: um lugar so para "banca
   contratada", "inscricoes abertas"...;
4. **Previsao: ano previsto que ja passou e "Atrasado: era esperado em
   AAAA"**, mesmo dentro da folga de 1 ano (grupo "Na janela de agora"), e
   esses vem no topo da janela. A conta e os grupos nao mudaram;
5. **acento so no texto que chega a tela web** nesta etapa. O terminal (CLI),
   o Telegram, os prompts de IA, o relatorio de auditoria e os nomes de
   assunto do `macetes.py` (que sao chave de casamento) ficaram como estavam;
   ver `pendencias.md`.

## A fonte unica das metricas (Etapa 1C, 01/10/2026)

1. **Toda contagem de questao, acerto e erro mora no `servico/metricas.py`.**
   Tela Hoje, `radar hoje`, Semanas, Minhas materias, Meu foco, Onde estudar,
   home e relatorio do simulado pedem o numero a ele; nenhum template soma.
   Ele e a evolucao do `Numeros`/`TotaisDoDia` que estavam no
   `servico/cronograma.py` (que sairam de la), e nao um modulo paralelo;
2. **a regra:** `questoes = acertos + erros + sem acerto anotado + treino de
   IA`. O `Numeros` guarda os quatro estados e o total e a soma deles, entao a
   linha nao tem como nao fechar. "Fiz hoje: 31 questoes = 13 acertos + 8
   erros + 10 de treino de IA", com o acerto da IA como segundo numero ("7 de
   10, fora do acerto"). Estado que nao existe nao aparece na frase;
3. **linha anotada com mais acertos que questoes e acusada**
   (`ContaInconsistente`, com a data e a faixa), e nao arredondada: o
   `max(medidas - acertos, 0)` antigo escondia o erro;
4. **os recortes tem nome fixo** - *medido no radar*, *anotado*, *treino de
   IA* e *total* - e a tela escreve qual mostra. Meu foco, Onde estudar e home
   continuam no *medido no radar* ate a Etapa 4 (decisao 7 da Etapa 0), agora
   dito na tela;
5. **duas contagens com nome diferente:** *respostas* (volume do dia, da
   semana, e a evolucao da home) e *questoes* (o acumulado, pela ultima
   resposta de cada questao). A mesma questao em duas rodadas sao 2 respostas
   e 1 questao. A home dizia "N questoes reais" para o que eram respostas;
   passou a dizer "respostas";
6. **todas as telas somam a mesma lista de lancamentos** (faixas marcadas,
   estudo extra, respostas no radar). Mesmo periodo, mesmo numero: o dia, a
   semana e a soma dos cartoes de materia dao os mesmos `Numeros`. Isso
   consertou duas divergencias que existiam: o dia de **Plano B** (a tela Hoje
   contava as faixas dele; Semanas e Minhas materias montavam o dia normal e
   nao achavam check nenhum) e o **treino de IA** (entrava no volume da semana
   e nao no da materia; agora entra no total das duas, fora do acerto);
7. **o registro do dia guarda so a meta e o recado.** As copias de total ja
   gravadas (28/09: 31/13; 29/09: 37/4, iguais ao calculado) ficam no banco e
   no `registro_estudo.json`, mas saem da tela e do `radar hoje`; a 1D as
   confere. Salvar a meta nao apaga a copia antiga;
8. **`radar hoje --feitas N [--acertos M] --minutos X [--materia ...]` grava
   um estudo extra** (Qconcursos, sem consulta), que entra no "Fiz hoje" como
   anotado. Sem `--minutos`, recusa: o extra exige tempo ("estudo sem tempo
   nao e estudo"), e essa regra nao foi afrouxada (escolha sua, 01/10);
9. **o grafico semanal de Minhas materias passa a incluir as respostas no
   radar** no acerto sem consulta da semana: antes so faixas e extras
   entravam nele, e o cartao (que ja contava o radar) dizia outra coisa;
10. **o "acertei X de Y" do Onde estudar vem da conta**, e nao mais de volta
    da porcentagem (que arredondava).

## A conferencia dos dias gravados (Etapa 1D, 01/10/2026)

1. **Faixa de questoes marcada com 0 questoes nao e "feita".** O
   `anotar_faixa` recusa 0 e vazio ("se nao fez nenhuma, desmarque a faixa").
   Aceitar o 0 contava os minutos da faixa no dia: foi o Bonus de 28 e 29/09,
   25 min cada, de um estudo que nao aconteceu (escolha sua, 01/10). Faixa de
   teoria, lei seca e correcao continua so com o circulo;
2. **`radar conferir-dias` so le.** Um relatorio por dia do ciclo: o registro
   gravado contra a conta do `servico.metricas`, faixa feita com 0 questoes,
   acertos maiores que as questoes (faixa ou extra), treino de IA no dia,
   resposta a questao hoje anulada, check orfao, e dia do banco que nao esta
   no JSON. A conferencia nao tem conta propria: a linha do dia e a do
   `metricas`;
3. **o `--aplicar` corrige so duas coisas, e so depois de aprovado:** tira o
   check da faixa com 0 questoes e exporta o diario para os JSON. O resto
   (acerto maior que questoes, orfao, anulada, copia que nao bate) e mostrado
   com a proposta e fica para eu corrigir na tela ou decidir antes. Antes de
   gravar, copia o `radar.db` (pela API de backup do SQLite, segura com o
   `radar web` aberto) e os dois JSON para `data/copias/conferencia-<hora>/`,
   fora do git;
4. **as copias de total do registro (28/09: 31/13; 29/09: 37/4) ficam como
   estao**: batem com a regra e nao aparecem mais (decisao 7 da 1C);
5. **resposta a questao anulada depois continua no acerto** ate haver regra
   para isso; a conferencia a acusa. No banco real nao ha nenhuma.

## A rotina nova do Ciclo 1 e o Anki desativado (Etapa 6A, 01/10/2026)

Aprovado por voce em 01/10, com os numeros do arquivo real (o roteiro
estimava o Anki em 30 min; ele tinha 15 nos dias uteis e 10 no sabado):

1. **a manha do dia util, de 02/10 em diante:** teoria dirigida 40 (teto, uma
   fonte so) · **fixacao do tema, 8 questoes (20 min), com consulta** · pausa
   10 · lei seca dirigida 20 (so os artigos `chave` do `essencial` do dia) ·
   pausa 10 · Portugues, teoria 20 + **6 questoes (15 min)**. Sao 2h15 e 14
   questoes (era 2h20 e nenhuma). A noite nao mudou;
2. **o dia util ficou 20 min mais curto e com 14 questoes a mais** (semana 1:
   3h50 e 39; com R+7: 4h20-4h25 e 49; com R+30: 4h50 e 59). O sabado perde os
   10 min do Anki;
3. **a fixacao vem com a caixa "com consulta" marcada**, como a aprendizagem
   de Direito: acabou de ler o tema, o numero inflaria a meta. A chave
   `consulta: true|false` passou a existir por faixa; sem ela, vale a regra de
   antes (so a `rampa: direito`). A fixacao de Portugues e sem consulta;
4. **dias antes de 02/10 nao mudaram** (teste com a impressao deles): os
   checks sao reconhecidos por bloco, posicao e titulo. O 01/10 ficou no
   formato antigo, porque a manha dele ja tinha passado;
5. **`anki: desativado` no topo do `cronograma.yml`.** As 36 faixas e os 30
   `baralho` continuam no arquivo. Desativada, a faixa fica NA MESMA POSICAO
   (tira-la mudaria a posicao do Bonus, e os checks contam posicao), sem
   duracao, fora do total, da sugestao de meta e de "a proxima faixa", e nao
   se marca; a tela e o `radar hoje` mostram "ANKI temporariamente
   desativado", e o chip do baralho some. **Para religar: `anki: ativado`.**
   Sem a chave, vale ativado (o arquivo antigo carrega igual);
6. **textos reescritos de 02/10 em diante:** a lei seca nao manda mais
   "transformar em cartoes do Anki"; o item (3) da revisao semanal de sabado
   virou "releia os artigos-chave da semana (os da lei seca dirigida)"
   (escolha sua); o bloco "Depois das 22h — Anki" virou "Depois das 22h".
   Religar o Anki nao desfaz esses textos.

## A estrutura de conteudos, a evidencia e a migracao (Etapa 2, 01/10/2026)

1. **Uma regra de evidencia, em `servico/evidencia.py`.** `alvo` = a prova do
   cargo do alvo principal E do estado dele (config/alvo.yml); `complementar`
   = outra prova de uma banca do alvo (FEPESE); `fora` = o resto (IESES). Ela
   substitui as duas de antes: o `foco._provas_do_alvo` (cargo e estado)
   passou a delegar a ela, e o simulado, que olhava so o cargo, tambem. A
   coluna `questoes.evidencia` e a fotografia dela, refeita na migracao, ao
   ler os cadernos, no `importar` e no `sincronizar`. No acervo real: 170 alvo
   (2013 e 2019), 7.356 complementar (o Socioeducativo 2016 entre elas, que
   deixou de ser "reforco" na contagem) e 907 fora. A auditoria continua
   auditando o 2016 como antes (`alvo.e_reforco`);
2. **a arvore** (`conteudos`): materia > assunto > subassunto > elemento, os
   dois de baixo opcionais. O no se reconhece pelo **caminho de nomes**
   ("Direito Penal > Imputabilidade penal"), no banco e nos JSON - nao pelo
   id, que muda quando o banco e refeito. A semente e o anexo de programas de
   2019 com o texto literal (11 materias, 85 assuntos) mais Nocoes de
   Informatica e Direito Administrativo, que cairam em 2013, marcadas "fora do
   edital atual". O arquivo versionado e o `data/conteudos.json`;
3. **a taxonomia** mora no `config/taxonomia.yml`: os tipos de elemento por
   familia de materia, os tipos de questao, as materias fora do edital e os
   sinonimos de materia de prova antiga ("Direito Processo Penal" de 2013 =
   "Direito Processual Penal"). Ampliar a lista nao muda o banco;
4. **a classificacao** (`classificacoes`): pela impressao do enunciado; uma
   principal por questao (a nova rebaixa a antiga a associada); status
   **completa** (no sem filho), **parcial** (no com filho) ou **pendente** (so
   a materia, ou dado assim por quem classificou); procedencia obrigatoria,
   sem ela a linha e recusada. Questao sem classificacao tambem e pendente,
   sem precisar de linha: hoje sao todas. Arquivo: `data/classificacoes.json`.
   O formato antigo (`data/assuntos.json`) continua entrando, e vira
   classificacao quando casa com um no; o resto fica pendente na materia, com
   o texto antigo no trecho;
5. **textos antigos**: ligados so quando casam EXATAMENTE (sem diferenca de
   maiuscula nem acento) com um no; o texto fica onde esta. As 20 geradas de
   Penal ("Aplicacao da lei penal (arts. 1o a 12)", tema que o programa de
   2019 nao lista) ficam em "Direito Penal" com o assunto pendente (escolha
   sua, 01/10): nenhum no novo fora do edital. A regra que as liga e geral -
   texto que e titulo de uma faixa vale a materia da faixa. As 20 de LEP em
   "Lei de Execucao Penal"; as 10 de Portugues e os 2 erros anotados so na
   materia (o assunto nao casa);
6. **chave `conteudo` nas faixas do cronograma.yml**, conferida no
   carregamento contra o `data/conteudos.json` (sem o arquivo, nao confere).
   So 6 faixas casam exatamente hoje (Portugues: Vozes do verbo, Ortografia
   oficial, Acentuacao grafica; manha e noite). A "Fixacao: X" nao entra:
   o texto nao e igual. O check da faixa guarda o `conteudo` quando ela tem;
7. **migracao versionada** (`migracoes.py`): a versao fica na tabela
   `versao_do_banco`; cada passo e numerado e nunca editado depois; antes de
   qualquer passo, o radar.db e copiado para
   `data/copias/migracao-v<de>-para-v<para>-<hora>/` (a pasta da 1D, fora do
   git - escolha sua, no lugar do `data/backup/` do roteiro); passo que
   termine com menos linhas e desfeito pela copia e a migracao para;
   `radar migrar --desfazer` restaura a ultima copia (e guarda o banco de
   antes de desfazer). Qualquer comando migra sozinho na primeira vez, como as
   colunas novas ja faziam; banco novo nasce na versao atual, sem copia.

## A classificacao do alvo, a incidencia e os padroes (Etapa 3A, 01/10/2026)

1. **A classificacao e pela CHAVE da questao inteira** (enunciado +
   alternativas, `questoes.chave_da_questao`), e nao pela impressao do
   enunciado, como a Etapa 2 decidiu. Motivo, achado na classificacao: a
   FEPESE repete enunciados genericos - "De acordo com o Codigo Penal
   Brasileiro, e correto" em quatro questoes de 2019 -, e 16 questoes do alvo
   colidiam. A chave continua achando a mesma questao reaproveitada em outro
   caderno (escolha sua). Migracao v3: a tabela foi refeita; linha antiga de
   enunciado repetido virou pendente em cada questao (nao da para saber de
   qual era). Vale para o `data/classificacoes.json`, que ainda aceita linha
   antiga com `impressao`. As 9 pendentes desse tipo que a conversao criou em
   provas do complementar (artefato da importacao errada do mesmo dia) foram
   apagadas;
2. **classificacao pelo Claude Code**, pelo `radar classificar --pedido` e
   `--importar` (decisao 8 da Etapa 0), com a procedencia "Claude Code,
   importado manualmente, em <data>". A importacao recusa: questao fora do
   pedido, sem justificativa (trecho e item do edital), assunto fora do edital
   da materia, tipo fora do `config/taxonomia.yml`, elemento sem subassunto,
   materia trocada numa materia do edital, e a questao que voce ja conferiu.
   "Pendente" exige motivo e guarda o dispositivo;
3. **materia fora do edital atual** (Informatica e Direito Administrativo de
   2013): vai para um assunto de 2019 so quando o item do edital justifica
   (4 de Direito Administrativo foram para Administracao Publica); senao ganha
   assunto proposto debaixo dela, com origem "classificacao" (escolha sua);
4. **tema fora do programa de 2019 fica pendente**, com o motivo: aplicacao da
   lei penal (CP, arts. 1o a 12), inquerito policial, e a LC 472/2009 de 2013
   (o edital de 2019 cobra a LC 675). Nenhum no novo foi criado para eles;
5. **pendente substituida nao vira associada**: quando uma classificacao real
   toma o lugar de uma pendente, a pendente sai (ela so dizia "ainda sem
   classificacao"). Uma real substituida continua como associada;
6. **conferencia em Analises > Conferencia**: confirmar (marca a data),
   corrigir (outro no da materia; a procedencia vira "manual") ou pendente
   (com o meu motivo). A 3A so fecha com as 162 validas conferidas;
7. **o mapa de incidencia** (`incidencia.py`, puro): so o alvo; a questao conta
   no no da classificacao principal e nos de cima; anulada e pendente ficam
   fora e aparecem com o numero; o denominador e o numero de provas em que a
   materia teve questao (LEP: 1, "apareceu na unica prova que cobrava a
   materia"). Os rotulos: "apareceu nas 2 provas", "apareceu em 1 de 2
   provas", "nao apareceu nas provas analisadas". Nenhum "vai cair";
8. **padroes de cobranca** por no: forma de perguntar, gabarito e termos (do
   `macetes.py`, uma por questao pela chave), tipo de questao e pegadinhas da
   classificacao, sempre como "padrao identificado no acervo analisado: N
   questoes · M provas · alvo". Abaixo do minimo do `config/amostra.yml`
   (3 questoes em 2 provas), a frase exata "Nao ha evidencia suficiente no
   acervo para afirmar isso.";
9. **Meu foco e Onde estudar continuam como estavam** ate a Etapa 4 (escolha
   sua): contar por no antes da sua conferencia poria classificacao nao
   conferida na tela como numero;
10. **auditoria ampliada**: verificacoes de extracao (enunciado curto, letras
    fora de a-e, alternativa vazia, cabecalho/rodape no texto, numero da
    questao no enunciado, figura citada, palavra cortada no fim), calibradas
    nas 170 sem disparar em texto legitimo; sem gabarito; e a classificacao
    por prova. O texto das questoes nao foi corrigido (pendencia B.7).


## O acervo complementar FEPESE (Etapa 3B, 01/10/2026)

O plano da 3B nao sobreviveu ao contato com o acervo, e os tres primeiros
pontos foram decididos por voce antes de qualquer linha de codigo:

1. **gabarito provisorio e um status proprio.** Das 183 provas complementares,
   161 so tem o gabarito provisorio no acervo (o que vem embutido no caderno);
   definitivo so existe para 22. A regra estrita do roteiro - prova sem
   validacao fica fora da estatistica - esvaziaria a etapa. Entao: a prova com
   provisorio **classifica** (para saber de que assunto a banca gosta, ele
   basta) e fica **fora dos padroes de cobranca** (forma de perguntar,
   distribuicao do gabarito, qual alternativa engana), que se medem sobre a
   letra CERTA, e essa muda depois dos recursos;
2. **a validacao confere o proprio caderno**, sem reler o PDF: numeracao de 1
   a N sem buraco nem repeticao, cinco alternativas em toda questao, gabarito
   em toda questao (ou anulada) e sha256 do PDF contra o acervo. O quadro de
   distribuicao do edital fica registrado como **"nao lido"**, nunca como "bate":
   o leitor de quadro (`auditoria.py`) foi feito para os editais do Estado e
   nao acha o quadro em edital de prefeitura. Conferir o quadro fica para a
   validacao da prova escolhida, que le o PDF;
3. **duas colunas que nunca se somam** no levantamento: *pelo nome da materia*
   (o caderno diz "Direito Penal": e certo) e *por termo no texto* (🟡 indicio:
   o caderno so diz "Conhecimentos Especificos" e um termo do
   `config/complementar.yml` apareceu). Indicio nao e evidencia, e so a questao
   que o nome NAO contou entra nele - a mesma questao nunca conta duas vezes.
   Motivo: fora o Socioeducativo, as prefeituras jogam tudo em "Conhecimentos
   Especificos" (3.405 questoes), e contar so pelo nome perderia isso;
4. **quem entra no acervo** (decisao sua, 01/10, com autonomia): a prova que
   tem **ao menos uma materia do edital de 2019** pelo nome no caderno e passa
   na validacao minima. Materia fora do edital de agora (Nocoes de Informatica,
   Direito Administrativo, Temas de Educacao) **nao serve de motivo** para a
   prova entrar. No acervo real: 122 das 183. Consequencia medida e registrada:
   **173 das 175 provas que se qualificam entram so por Portugues e Raciocinio
   Logico** - so o Socioeducativo 2013 e 2016 trazem Direito, Direitos Humanos
   e Legislacao Estadual;
5. **a decisao fica num arquivo versionado**, `data/acervo_complementar.json`,
   gravado por `radar complementar --aplicar`: fonte, concurso, cargo, ano,
   arquivo, sha256, questoes, materias do edital, tipo de gabarito, quadro do
   edital, aceita/recusada com o motivo, e a **data de inclusao**, que e
   preservada quando o comando roda de novo. Sem o arquivo, **nenhuma** prova
   complementar entra em estatistica: levantar nao e aprovar;
6. **a linha complementar da incidencia** anda ao lado da do alvo e nunca e
   somada a ela (regra inviolavel 1): "Policia Penal SC: 9 questoes · 2 provas ·
   Acervo complementar FEPESE: 4 questoes · 2 provas". No nivel da **materia** a
   questao sem classificacao conta, porque o proprio caderno declara a materia
   dela, e isso e evidencia; **abaixo da materia so conta a classificada**, e
   quantas faltam vai escrito na linha ("993 sem classificacao ainda").
   Adivinhar o assunto pelo nome do caderno seria o que a regra 9 proibe.
