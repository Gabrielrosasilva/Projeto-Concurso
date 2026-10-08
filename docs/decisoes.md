# Decisoes que ja foram tomadas

Decisoes ja fechadas do radar, com o motivo de cada uma. Nao precisam ser
rediscutidas: se uma delas mudar, **este arquivo e atualizado junto**.

O `CLAUDE.md` aponta para ca e fica so com o contexto permanente do projeto.
O porque detalhado de cada fase, com os numeros medidos, esta em
[docs/historico.md](historico.md).

**Como ler a numeracao** (nota de 03/10/2026). Ate a primeira secao da Etapa
3B, cada secao do pedido de evolucao numera as suas decisoes de 1 em diante -
a Etapa 0 vai de 1 a 14, a 3A de 1 a 10 -, e por isso "decisao 9" sozinho e
ambiguo ali: cite com a etapa ("decisao 9 da 3A"). Da 3B em diante a
numeracao e continua (7 a 66, ate aqui), e o numero sozinho basta.

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
  nao encosta em arquivo que nao seja os dois JSON (o "pull" deixou de ser
  `pull --rebase` em 03/10/2026: decisao 64);
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
- ~~**o reforco soma na fatia e nunca aparece somado na tela.**~~ **Substituida
  pela decisao 63 (03/10/2026):** somar na fatia era somar alvo e complementar
  num numero so, o que a regra inviolavel 1 do novo.md proibe. Hoje as
  questoes esperadas sao so das provas do cargo, e o complementar (so as
  provas aceitas) pesa so na ordem. O texto de antes: sao duas provas do
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
  104 (dezembro de 2019) contra a prova de 2019. ~~**A lista ainda nao foi
  gravada**: ela espera a minha conferencia (parte 1).~~ **Mudou em 03/10/2026
  (decisao 65):** a lista foi gravada pelo Claude Code, com procedencia, e
  fica POR CONFERIR - o aviso sai com o 🟣 ate eu marcar `conferida: true`.
  Sem lista nenhuma, a tela continua dizendo que ela falta, em vez de sugerir
  que nenhuma lei mudou;
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

### O cronometro: a primeira excecao ao "sem JavaScript" (etapa A5, 26/09/2026)

> **Revisado em 02/10/2026 (B.11):** ele deixou de ser o UNICO. A dobra dos
> blocos da tela Hoje (`static/dobra.js`) e a segunda excecao, pelo mesmo
> critério: guardar estado no navegador e coisa que so o navegador faz, e a
> tela funciona igual sem o arquivo. Ver a decisao 30. As duas excecoes valem
> **so na tela Hoje**; o resto do radar continua sem JavaScript.

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

## A classificacao do acervo complementar (Etapa 3B, passo 4, 02/10/2026)

7. **o mesmo fluxo da 3A, com a evidencia escolhida**: `radar classificar
   --pedido --evidencia complementar` pede as provas ACEITAS no acervo
   (prova recusada na validacao nao e classificada - seria dar a ela um lugar
   na estatistica que a validacao negou), e `--materia` passou a aceitar mais
   de uma. A instrucao do complementar diz que a prova NAO e a do meu cargo e
   que o numero dela nunca entra na incidencia da Policia Penal. O lote nunca
   mistura as duas evidencias;
8. **as 80 do Socioeducativo 2013 e 2016 classificadas** (Direito Penal,
   Processual Penal, Constitucional, Direitos Humanos, Legislacao Estadual e
   Direito Administrativo): 62 classificadas e 18 pendentes com motivo. As
   pendentes, por motivo: 8 por **bloco trocado no caderno** (ver abaixo), 4
   da LC 472/2009 (o edital de 2019 cobra a LC 675), 3 de instrumentos de
   infancia e juventude (Regras de Riad, de Beijing e a Convencao de 1989:
   tema do concurso socioeducativo, fora do meu programa de Direitos
   Humanos), 2 da Constituicao do Estado de SC (o programa lista so a Lei
   6.745, a LC 675 e a LC 529) e 1 de tortura (Lei 9.455/1997, que no meu
   edital e Legislacao Especial, nao Direito Penal);
9. **erro de separacao por materia nos cadernos do Socioeducativo**, achado
   pela classificacao: 8 questoes estao no bloco errado. As 2013-q49, 2013-q50,
   2016-q49 e 2016-q50 sao de Processo Penal e estao no bloco "Legislacao
   Estadual"; as 2013-q59, 2013-q60, 2016-q59 e 2016-q60 sao de Legislacao
   Estadual e estao no bloco "Direito Processual Penal". **Nada foi
   corrigido**: a importacao recusa trocar de materia quando ela esta no
   edital (e bom que recuse), e consertar isso e mexer no leitor do caderno.
   As oito ficaram pendentes com o motivo escrito, e a pendencia esta no
   `pendencias.md`;
10. **a classificacao do complementar nao mexe em numero nenhum do alvo**, e
    isso tem teste: os 170 continuam 146 completas, 9 parciais e 15
    pendentes, e nenhuma linha do alvo foi escrita na importacao. No acervo
    real nao ha uma chave sequer repetida entre alvo e complementar (foi
    conferido); se houvesse, seria a MESMA questao reaproveitada, e classificar
    uma classificaria a outra - que e o comportamento decidido na 3A.

## A classificacao do complementar: blocos genericos e catalogo (Etapa 3B, 02/10/2026)

11. **bloco generico e um tipo de pedido proprio.** Nas prefeituras o caderno
    nao diz a materia: joga tudo em "Conhecimentos Especificos". Nesses lotes
    a MATERIA tambem e pergunta - o pedido vai marcado `bloco_generico`, leva
    a arvore inteira, e a resposta diz em que materia do meu edital a questao
    cai. A importacao recusa materia fora do edital de agora e assunto fora
    dela. **Pendente em bloco generico nao vira linha**: sem materia no
    caderno nao ha onde pendura-la, e questao sem linha ja e pendente desde a
    Etapa 2;
12. **o lote so agrupa pela suspeita do termo**, e o pedido escreve isso. O
    termo passou a casar **palavra inteira**: "dolo" casava dentro de
    "dolorosa" e levava questao de enfermagem para Direito Penal. So isso
    derrubou o lote de Direito Penal de 45 para 2 questoes - o resto era
    lixo. Termo em pedaco de palavra ("sociologic") nao casa mais nada, e o
    `config/complementar.yml` avisa;
13. **a mesma questao em dois cadernos e UMA questao**, e o pedido nao a manda
    duas vezes. O codigo da questao ("2024-q29") so e unico dentro de um
    lote: dois lotes podem ter questoes diferentes com o mesmo ano e numero,
    e a conferencia de repeticao passou a ser por lote;
14. **a incidencia complementar conta questao DISTINTA**, com as ocorrencias
    ao lado: "187 questoes · 122 provas (998 ocorrencias em cadernos
    diferentes)". Motivo: a FEPESE repete o mesmo caderno de Portugues em
    dezenas de cargos do mesmo concurso, e dizer 998 faria o acervo parecer
    cinco vezes maior do que e. A contagem do ALVO nao muda: la cada caderno
    e um concurso diferente;
15. **Portugues e Raciocinio Logico pelo catalogo** (`radar classificar
    --catalogo`): o catalogo de palavras-chave do `macetes.py` propoe o
    assunto, e o mapa dele para o texto literal do edital mora no
    `config/complementar.yml`. A proposta sai com a procedencia "catalogo
    automatico (macetes.py), conferir por amostra" e a tela de conferencia
    mostra o aviso 🟡. **Nada e forcado**: enunciado que nao casa palavra
    nenhuma, que casa DOIS assuntos (crase e regencia andam juntas) ou cujo
    nome nao tem par no edital fica sem linha; questao ja classificada nao e
    sobrescrita.

## A conferencia do alvo e as anuladas (02/10/2026)

16. **as 162 validas foram conferidas por voce em 02/10**, e com isso a 3A
    fechou. Confirmar marca a data da conferencia e **nao** reescreve a
    procedencia: a linha continua dizendo "Claude Code, importado
    manualmente", e e isso que deixa auditavel que a proposta foi de IA e a
    conferencia foi sua;
17. **a questao anulada sai da lista da conferencia** (escolha sua): a banca
    desfez a pergunta, ela nao entra em conta nenhuma - nem na incidencia -, e
    conferi-la nao muda numero algum. Os dois totais continuam a vista ("162
    de 162 validas · 170 de 170 contando as anuladas") e a caixa "mostrar as
    anuladas" traz de volta. Nada foi apagado.

## A conferencia do complementar fica para depois (02/10/2026)

18. **o acervo complementar segue NAO conferido, por ora** (escolha sua, 02/10).
    As 44 do bloco generico e as 108 do catalogo nao tem tela: a aba
    Conferencia lista so o alvo. Em vez de construir o filtro de evidencia
    agora, elas ficam como estao - e isso nao esconde nada: cada linha ja
    carrega a procedencia ("Claude Code, importado manualmente" ou "catalogo
    automatico (macetes.py), conferir por amostra"), e a linha complementar da
    incidencia escreve quantas faltam classificar.

    **Por que nao atrapalha agora:** o desempenho da Etapa 4 sai das MINHAS
    respostas, nao da classificacao do complementar; e a incidencia do alvo
    nunca se mistura com ele. **Quando volta a importar:** na Etapa 5, quando
    a classificacao passar a escolher questao para treino - ai a tela ganha o
    filtro de evidencia e a conferencia por amostra acontece (20 por materia;
    taxa de erro alta, o lote volta). Isso esta na pendencia B.8.

## Etapa 4 — amostra, desempenho por conteudo e controle de estudo (02/10/2026)

19. **os minimos de amostra vivem num lugar so**, o `config/amostra.yml`,
    secao `desempenho`, lida pelo `src/radar/amostra.py`. Os valores sao os da
    decisao 6 da Etapa 0: **20** respostas sem consulta na materia, **10** no
    assunto, **6** no subassunto e no elemento. **Revogados** o 5 na materia e
    o 3 no assunto do `onde_estudar.py` e o 20 do `servico/materias.py`: eram
    tres reguas para a mesma duvida, e tres leituras do mesmo dia.

    **O 3 do caderno de erros FICA onde esta** (`servico/erros.py`),
    avaliado nesta etapa: ele mede a FATIA de cada motivo de erro ("3 dos meus
    10 erros foram por pressa"), e nao o meu acerto num conteudo. Sao duas
    perguntas com riscos diferentes, e juntar as duas na mesma regua tornaria
    as duas erradas. O motivo esta escrito nos dois arquivos;

20. **"estudado" tem definicao** (a resposta a §8 do novo.md): um no esta
    **estudado** quando uma faixa de ESTUDO (`teoria`, `lei_seca`,
    `portugues`, `raciocinio`) ligada a ele ou a um no abaixo dele foi marcada
    como feita, ou quando ha estudo extra de teoria ou de lei seca nele. Esta
    **praticado** quando tem resposta, minha no radar ou anotada. **Nao
    estudado** e nenhum dos dois, e um no pode ser os dois primeiros ao mesmo
    tempo.

    **Faixa de questoes nao deixa um conteudo "estudado"**: fazer questao e
    praticar, e eu posso praticar o que nunca li. **O filho nao herda do pai**:
    ter lido o assunto nao e ter estudado cada parte dele;

21. **o desempenho por conteudo soma o radar e o anotado para o ESTADO, e
    nunca os soma na tela** (aplica a decisao 7, que revisa a E2). A tela
    escreve sempre a divisao "radar X% em N · anotado Y% em M", com travessao
    na metade vazia. Motivo: as duas origens medem de maneiras diferentes - uma
    e questao a questao aqui dentro, a outra e a minha anotacao do Qconcursos -
    e um numero unico esconderia isso; mas ignorar metade do meu treino no
    estado seria pior. **Só o respondido sem consulta** entra no estado; o que
    teve consulta e o que eu fiz sem anotar o acerto ficam no volume, a parte.
    Questao escrita por IA nunca entra em nada disto;

22. **o anotado chega ao conteudo por um seletor nos formularios** (faixa,
    estudo extra, caderno de erros). Um `<select>` so, com o caminho inteiro no
    valor e o nome recuado no rotulo, em vez de tres caixas encadeadas:
    encadear precisaria de JavaScript, e o cronometro continua sendo o unico JS
    do projeto. **Na faixa o seletor nao sai do ramo dela**: anotar Portugues
    dentro da faixa de LEP nao e detalhar, e trocar de materia - e para isso
    existe o estudo extra. No que nao existe na arvore e recusado em voz alta;

23. **a revisao por no nao mora em tabela nenhuma**, pela mesma escolha do
    `espacada.py`: sai do historico, e descartar um simulado de teste apaga
    sozinho o que ele agendava. **Tres gatilhos**, e a linha diz qual disparou:
    erro recente (no radar ou no caderno), estado "precisa revisar", e o prazo
    1-7-30 vencido. **A ancora do 1-7-30 e o ultimo estudo** ou, sem estudo
    nenhum, o PRIMEIRO contato pratico: ancorar na ultima resposta reiniciaria
    a conta a cada questao, e a etapa nunca andaria;

24. **"questoes a refazer" sao duas listas separadas**, nunca somadas: as
    erradas no radar (eu refaco respondendo) e as do caderno de erros (eu
    refaco relendo a regra que eu escrevi). Somar as duas daria um numero que
    nao corresponde a nenhuma acao;

25. **o modulo novo se chama `servico/desempenho_por_conteudo.py`**, e nao
    `servico/desempenho.py` como o roteiro propunha: `servico.desempenho()` ja
    existe na fachada e e o desempenho por MATERIA. Duas coisas com o mesmo
    nome no mesmo lugar e exatamente o que esta etapa veio consertar em outro
    canto;

26. **o recorte de tempo padrao e o ciclo em andamento** (decisao E4), com a
    opcao "desde o inicio" na tela e no `--desde-o-inicio` do comando. A
    pergunta "eu ja estudei isto?", porem, olha **sempre desde o inicio**: ter
    lido a LEP no Ciclo 1 nao desaprende quando o Ciclo 2 comeca.

## Os blocos da aba Hoje dobram (B.11, 02/10/2026)

27. **cada bloco do dia e um `<details>` com o cabecalho de `<summary>`**: a
    dobra em si nao usa JavaScript nenhum, como o Mapa do ano da lateral ja
    fazia, e um sinal (▾ / ▴) no canto direito mostra o estado.

    **So o SINAL do canto dobra**, e nao o cabecalho inteiro (escolha sua, na
    segunda passada): um clique no titulo ou nos horarios nao pode recolher o
    bloco sem eu querer. Como se faz: `pointer-events: none` no `<summary>`,
    para o clique atravessar, e `auto` so no sinal. O **teclado nao passa por
    ali**, entao Tab ate o cabecalho e Enter continuam dobrando, e o foco
    continua visivel. O sinal ganhou area de clique de verdade (1,75rem) e um
    `title` dizendo o que ele faz, porque o alvo ficou pequeno;

28. **"Depois das 22h" nasce FECHADO**, e os outros blocos abertos. Motivo: o
    bloco e sobreaviso ("pode interromper") e, com `anki: desativado`, nao ha
    nada ali para fazer fora do Bonus - abrir e acao minha, que foi o pedido.
    Fechado, ele mostra no proprio cabecalho a frase "ANKI temporariamente
    desativado"; aberto, a frase do cabecalho sai e fica a da faixa
    minimizada, que a 6A criou - a mesma frase duas vezes no mesmo bloco seria
    ruido. A frase segue a faixa DESLIGADA, e nao o nome do bloco: religando o
    Anki ela desaparece sozinha, e o bloco continua nascendo fechado;

29. ~~a dobra NAO e lembrada entre recarregamentos~~ — **revogada no mesmo dia,
    por voce**: ela passou a ser lembrada. Ver a decisao 30.

30. **a dobra e LEMBRADA entre recarregamentos**, e isso cria o **segundo
    JavaScript do radar**: `src/radar/web/static/dobra.js`. Eu avisei que
    guardar o estado precisa de `localStorage`, e que isso muda a regra do
    "cronometro e o unico JS"; voce pediu mesmo assim, e a regra mudou -
    passam a ser **duas excecoes, as duas so na tela Hoje**.

    O limite e o mesmo do cronometro, e e ele que faz a excecao aceitavel: **a
    tela funciona igual sem o arquivo.** O padrao (`<details open>` em quem
    nasce aberto) e escrito pelo SERVIDOR, e a dobra responde ao clique com ou
    sem JavaScript; o script so restaura o que eu deixei e salva o que eu mudo.
    Todo acesso ao `localStorage` esta em `try/catch`: janela privada ou dado
    do site limpo nao podem quebrar a tela.

    **A chave e o BLOCO** (`data-bloco`: manha, noite, pos22, plano_b), e nao o
    dia: "eu prefiro o bloco das 22h fechado" e uma preferencia minha, nao uma
    coisa de 02/10. **Excecao:** quando o endereco traz uma ancora
    (`#faixa-pos22-1`, que e onde a tela volta depois de eu anotar uma faixa), o
    bloco daquela faixa fica aberto e nao e recolhido - recolher justo o que eu
    acabei de anotar esconderia a resposta do meu proprio clique.

## Etapa 5 — o filtro hierarquico, os tres modos e a base da gerada (02/10/2026)

31. **o escopo e um caminho fechado da arvore**, e mora no modulo puro
    (`radar/conteudos.resolver_escopo`): materia > assunto > subassunto >
    elemento. Dois nomes em portugues, `--assunto`, `--subassunto` e
    `--elemento` (repetivel), no lugar do `--artigos "1,2,3"` que a §7
    sugeria - a propria §7 abre essa porta ("nao precisa usar exatamente esses
    nomes"), e `--elemento` serve tambem para regra gramatical e tipo de
    problema, que a §14 pede. **O nivel de baixo exige o de cima**: subassunto
    sem assunto nao fecha escopo, porque duas materias podem ter subassunto de
    nome igual;

32. **nome que a arvore nao tem PARA o comando**, com ate 5 sugestoes
    (`difflib`, biblioteca padrao) e um corte de semelhanca de 0,5: abaixo
    disso ele lista os que existem em vez de sugerir qualquer coisa. **Nada e
    aproximado e nada e alargado**: nome errado nunca vira o nome mais
    parecido. E a §7 ao pe da letra ("avisar e sugerir, em vez de gerar
    questoes de outra coisa");

33. **o simulado continua amplo, inclusive com a materia escolhida.** So
    materia nao e escopo especifico: o pedido vai pela coluna `materia` como
    sempre, e nao pela classificacao. Motivo: restringir o simulado as questoes
    ja classificadas o deixaria menor do que ele e, e a §7 manda preservar a
    consulta ampla. Sem `--modo`, **com assunto e treino, so com materia e
    simulado**, e a saida escreve qual foi;

34. **o modo revisao usa o "estudado" da Etapa 4**, e nao uma conta nova (a
    definicao esta na decisao 20). Ele monta um escopo da materia restrito aos
    nos estudados. **Sem nada estudado, ele PARA** em vez de gerar a materia
    inteira: alargar o escopo "para nao ficar vazio" e exatamente o que a §8
    proibe;

35. **a prioridade da base da §9 vale tambem para completar o pedido.** Pedi 20
    e o no tem 1 questao real: 3 variacoes dela, e as 17 restantes do zero
    DENTRO do mesmo no, pela fonte oficial do `config/leis.yml` ou pelo item do
    edital. O que nao se faz e sair do escopo para achar base. As do zero saem
    marcadas `evidencia_da_base: nenhuma`, que e o registro explicito que a §9
    pede - **o sistema nunca inventa vinculo com questao real**;

36. **a garantia da §8 e a validacao do que a IA DECLARA**, e nao a confianca
    nela. O pedido exige que cada questao escreva o `conteudo` dela, e a
    importacao recusa (contando na saida): conteudo fora do escopo, artigo que
    nao e nenhum dos dispositivos pedidos, vinculo com questao real que nao
    estava no pedido, e `do_zero` sem a marca. A leitura do TEXTO continua
    minha, no treino, com o botao "essa questao esta errada";

37. **o artigo bate pelo NUMERO, nao pelo texto**: "LEP, art. 112" e "art. 112
    da Lei 7.210/1984" sao o mesmo dispositivo. Elemento que nao e artigo
    (regra gramatical, tipo de problema) nao passa por essa conferencia - o no
    declarado ja garantiu o escopo;

38. **`modo_do_pedido` e coluna nova, e `modo` fica como esta.** O `modo` da
    questao gerada ja quer dizer "variacao ou do zero" - como ela foi ESCRITA.
    O modo do pedido e outro eixo: para que ela foi pedida. Juntar os dois num
    campo seria o duplo sentido que a Etapa 4 veio consertar em outro canto. O
    **dispositivo** reusa a coluna `artigo`, que ja existia e e exatamente
    isso;

39. **os campos novos ficam NULOS nas 50 geradas antigas** (migracao v4, com
    copia antes). Elas nasceram de um pedido que nao tinha escopo nenhum, e
    preencher agora diria que foram pedidas de um jeito que nao foram.

## Achado da Etapa 5: o JSON das geradas estava vazio (02/10/2026)

40. **o `data/questoes_geradas.json` versionado estava `[]`** desde o commit da
    Etapa 2 (`904f1b7`), enquanto o banco tinha as 50. O export daquela etapa
    rodou contra um banco temporario e sobrescreveu o arquivo - o mesmo
    tropeco que eu repeti nesta etapa e peguei na hora.

    **Por que importa:** o arquivo e o registro, e o banco e reconstruivel A
    PARTIR dele. Com o arquivo vazio, refazer o banco perderia as 50 - e o §23
    e explicito: nenhum dado antigo pode ter sido perdido. Nada foi perdido de
    fato (o banco as tinha), mas o registro versionado estava.

    **Consertado nesta etapa**, exportando do banco real: as 50 estao no
    arquivo (30 `do_zero`, 20 `variacao`), e um teste novo
    (`test_o_json_real_das_geradas_nao_esta_vazio`) nao deixa isso voltar a
    acontecer calado.

    **Revisto na Etapa 6B (02/10/2026):** o conserto nao chegou ao commit da
    Etapa 5 - o arquivo continuava `[]` no git. A causa era um teste, e esta na
    decisao 50.

## Etapa 6B — a ficha de estudo e a prioridade (02/10/2026)

41. **a ficha ja nasce com os selos do novo.md** - 🟢 fonte oficial, 🔵
    estatistica do acervo, 🟡 analise automatica, 🟣 gerado por IA -, mais o 📌
    do que o plano escolheu (o cronograma.yml). Cada campo tem UMA origem,
    escrita no `ORIGEM_DO_CAMPO` do `src/radar/fichas.py`. O resto do site
    troca os selos na Etapa 7A; a ficha nao espera por ela.

42. **o tema e a chave, e nao uma chave `conteudo` em cada faixa.** O roteiro
    previa gravar o `conteudo` em toda faixa do resto do Ciclo 1. A ficha e
    reconhecida pelo TITULO exato da faixa, sem o prefixo ("Fixação: ",
    "Aprendizagem: ", "R+7: ", "R+30: ", "Artigos-chave: ", "Questões de
    prova: "), e pela materia. **Por que:** o cronograma.yml nao muda por
    causa da ficha, e a mesma ficha aparece em toda faixa do tema - teoria,
    fixacao, aprendizagem, revisoes e Plano B. Nada e aproximado: titulo
    diferente e outro tema. A lista de prefixos e fechada; um prefixo novo no
    YAML tem de entrar no `PREFIXOS_DO_TEMA`.

43. **o escopo da ficha e a lista de nos (`nos`), escolhida com o porque.**
    Dela saem as questoes reais, a incidencia, os padroes e o meu desempenho.
    A escolha e julgamento, e por isso vem justificada (`por_que_estes_nos`) e
    espera a minha conferencia. As regras:
    - sem no que sirva, a lista fica VAZIA e diz por que - nenhum no e criado
      (regra 9). Em 02/10 sao 13 assim: 6 da LEP (os trechos sem questao
      classificada) e 7 de Portugues (questoes classificadas so no nivel do
      assunto, junto com as de outro tema). A ficha sem no vale o piso de meia
      questao na prioridade, mas o "por que agora" diz que o tema nao tem no e
      que o acervo nao foi contado - e nao "nao apareceu nas provas", que
      ninguem verificou (regra inviolavel 4);
    - a materia inteira nunca e escopo, e um no dentro de outro na mesma ficha
      e recusado (a mesma resposta contaria duas vezes);
    - **fichas irmas nao repetem no.** Quando um no cobre dois temas (o
      subassunto "Concordancia verbal" serve a regra geral e aos casos
      especiais), ele fica numa so, e a outra diz onde ele esta;
    - **as revisoes ativas e a bateria de interpretacao cobrem os assuntos
      inteiros de proposito:** sao revisao do que as fichas de tema cobrem, e
      as questoes classificadas so no nivel do assunto, que nenhuma ficha de
      tema pode contar, entram nelas.

44. **a prioridade mora no `config/prioridade.yml`, e e regra, nao
    previsao.** A conta e a do Onde estudar, evoluida: peso da materia no
    edital x (fatia do ALVO + 0,25 x fatia do complementar) x (1 - acerto, so
    com amostra suficiente) x tempo (1 a 2, dobra em 30 dias) x 1,5 quando o
    conteudo esta na fila de revisao. Tema do edital que nao apareceu nas
    provas conta **meia questao** (piso), para nao zerar e ficar sempre abaixo
    de quem apareceu uma vez. O complementar entra em fator proprio, com o peso
    escrito no YAML (§15); com peso 0 a ordem e so a do alvo. A ficha mostra
    cada fator com o numero e a origem, e a frase "e regra de priorizacao, nao
    previsao de prova".

45. **a fila de revisao SUGERE, e nao troca o tema da faixa R+7/R+30.** O
    roteiro dizia que o conteudo dessas faixas seria escolhido pela fila na
    hora de mostrar. A faixa continua com o tema do calendario - e ele que o
    check, o registro do dia e o caderno gravam -, e a fila aparece na ficha,
    em "Quando revisar", com o motivo, e pesa x1,5 na prioridade. Trocar o
    tema na hora de mostrar faria a faixa dizer uma coisa e o registro outra.

46. **os artigos-chave da ficha saem do `essencial` do dia da teoria**, e nao
    o contrario. O roteiro dizia que o Plano B tiraria o essencial da ficha. O
    `essencial` e selecao do plano (📌), ja alimenta o Plano B e a lei seca
    dirigida, e o texto da ficha e de IA (🟣) e espera conferencia: o Plano B
    nao passa a depender dele. So a ficha do tema da TEORIA do dia mostra os
    artigos-chave - o essencial e do Direito do dia, e nao do Portugues.

47. **o texto da ficha vem do Claude Code, pelo pedido e importar, e a
    conferencia e minha.** `radar fichas --pedido` escreve o pedido com os
    temas sem ficha; a importacao recusa tema fora do pedido, no fora da
    arvore, campo obrigatorio vazio e texto com cara de previsao ("vai cair",
    "a FEPESE sempre..."). A procedencia e "Claude Code, importado
    manualmente, em <data>" - nunca o nome de um modelo. Conferir
    (`--conferir` ou o botao) grava a data e NAO apaga a procedencia; a ficha
    conferida nao e sobrescrita por importacao nova, e `--pedido --refazer`
    pede de novo so as nao conferidas. As 61 de 02/10 estao todas por
    conferir. *Revista em 05/10/2026 pelas decisoes 116 e 121: o texto de IA
    novo diz o modelo ("Claude Code (claude-opus-5-5), ..."), quando a
    resposta o declara; o que ja estava gravado nao mudou.*

48. **texto de lei na ficha e o texto VIGENTE, conferido na compilacao da
    Camara.** O Planalto recusa a conexao do Claude Code; a norma atualizada
    da Camara (Centro de Documentacao e Informacao) traz cada dispositivo com a
    lei que deu a redacao. As fichas da LEP dizem ate que lei o texto foi
    conferido ("ate a Lei 15.410, de 20/05/2026") e quando a mudanca e
    posterior as provas de 2013 e 2019. A LEP mudou muito em 2024-2026 (art.
    9º-A, art. 41, § 1º, art. 52, art. 112, saida temporaria, art. 124
    revogado), e o detalhe do cronograma de 09/10, 28/10 e 30/10 foi corrigido
    pelo mesmo texto. As fichas de Direito Penal e Constitucional, escritas
    antes, nao passaram por essa conferencia (ver pendencias).

49. **fonte sugerida: uma so por ficha, quando nao ha lei.** Portugues: "A
    Gramatica para Concursos Publicos" (Fernando Pestana); interpretacao:
    "Para Entender o Texto" (Fiorin e Platao); tipos de discurso: a "Nova
    Gramatica do Portugues Contemporaneo" (Cunha e Cintra); redacao oficial: o
    Manual de Redacao da Presidencia, 3ª edicao (2018); Raciocinio Logico:
    "Raciocinio Logico Simplificado", vols. 1 e 2 (Sergio Carvalho e Weber
    Campos); doutrina de Direitos Humanos: o "Curso de Direitos Humanos" (Andre
    de Carvalho Ramos); Regras de Mandela: a traducao oficial do CNJ (2016). As
    revisoes ativas apontam para o caderno de erros, e a bateria de
    interpretacao para as minhas notas da aula de 01/10.

50. **teste nenhum aponta o banco para o tmp sem apontar os dados.** O
    `test_tabela_nova_entra_em_banco_antigo` criava um banco sem versao no
    `tmp_path` e mudava so o `RADAR_DATABASE_URL`. O banco sem versao migra
    sozinho, e os passos 1 e 4 da migracao exportam os JSON versionados e
    copiam o banco para `<dados>/copias`. Resultado: a cada `pytest`, o
    `data/questoes_geradas.json` virava o `[]` do banco vazio, o caderno de
    erros e os extras eram regravados, e uma pasta `migracao-v0-para-v*` com
    `antigo.db` caia em `data/copias/`. Foi assim que as 50 geradas sumiram do
    arquivo na Etapa 2 e de novo depois do conserto da Etapa 5 (a suite
    inteira, rodada no fim, sobrescreveu o arquivo antes do commit).
    **Consertado:** o teste aponta tambem o `RADAR_DATA_DIR` para o
    `tmp_path`, e as 50 foram exportadas de novo do banco real (0 -> 50: 30
    `do_zero`, 20 `variacao`). Depois da suite inteira, o arquivo continua com
    as 50 - conferido antes do commit.

51. **a data da procedencia e a de Florianopolis.** O `procedencia()` formatava
    o `agora()`, que e UTC: as fichas importadas as 22h de 02/10 sairam "em
    03/10/2026". Passou a converter para o fuso local, com teste de hora fixa,
    e as 61 foram reimportadas com a data certa (nenhuma estava conferida).

52. **o Ciclo 2 fica para depois do simulado de 07/11.** O passo 5 da 6B
    (proposta -> aprovacao -> YAML) nao foi feito: a faixa de correcao de
    07/11 manda comparar o acerto por materia com o diagnostico de 03/10, e "e
    esse numero que decide o Ciclo 2". A proposta sai depois dele, pela
    prioridade e pela rotina da 6A, e so vira YAML com a minha aprovacao,
    antes de 09/11.

## Etapa 7A — os selos do novo.md, a frase padrao e a questao de IA (02-03/10/2026)

53. **as cores do novo.md em todo o site, e o "calculado" deixou de existir.**
    🟢 fonte oficial (edital, gabarito, lei e a questao tirada da prova), 🔵
    estatistica do acervo, 🟡 analise automatica (com as variacoes
    "classificacao" e "tendencia") e 🟣 gerado por IA, mais o 📌 do plano.
    Moram num lugar so, o `src/radar/origem.py`: a tela (o `selo` do
    `_componentes.html`), a ficha e o terminal leem de la. O antigo 🟩
    "calculado pelo sistema" foi dividido pela natureza do dado: contagem
    nas provas virou 🔵 acervo; o que o sistema calcula de mim e do radar
    (meu acerto, medido no radar, total do dia, nivel, erros do caderno,
    concursos coletados) virou 🟡 automatico. **Por que dividir, e nao
    trocar a cor:** o verde passou a querer dizer oficial, e "meu acerto"
    nao e estatistica do acervo (regra inviolavel 1).

54. **a origem mora no dado, e a tela so desenha.** Tres formas, a mais
    simples que serve:
    - tipo de origem fixa: atributo de classe `origem` (Numeros, Evolucao,
      Nivel, Revisar, Contagem, Desempenho, FatiaDoCaderno, Cartao,
      MaceteDoCartao, Previsao, Cobertura, Projecao, Lei, QuestaoDeProva e
      QuestaoGerada). Nas duas questoes **nao e coluna**: a tabela ja diz de
      onde a linha veio, e nao ha migracao;
    - tipo que junta partes de origens diferentes: `origens`, parte ->
      origem (a Conta do dia - o treino de IA leva o selo da IA -, o Painel
      do Meu foco, a Analise dos Macetes, o Plano do compilado e a ficha,
      pelo `ORIGEM_DO_CAMPO`);
    - origem que depende do dado: propriedade ou campo (a questao da revisao
      e a rodada: prova ou IA; a resposta certa: gabarito definitivo ou
      resposta da IA; o acerto por materia: IA nas geradas; o salario: lido
      do anuncio, ou sem selo quando fui eu que digitei).
    Selo de LEGENDA ou de NOTA DE METODO (frase fixa da tela que explica uma
    regra: a legenda da Mais, "so questoes reais", "os minimos vem do
    config/amostra.yml") continua escrito no template. Tres campos antigos
    se chamam `origem` com outro sentido e ficaram como estao, por estarem
    fora do pedido: `Conteudo.origem` (edital/classificacao/manual),
    `Lancamento.origem` (faixa/extra/radar) e `servico.geradas.origem_de` (a
    questao real em que a gerada se baseia).

55. **a meta do dia tem cor propria, e nada pinta com a cor de selo.** O
    `design.css` ganhou cores com nome (`--cor-verde`, `--cor-azul`,
    `--cor-ambar`, `--cor-vermelho`, `--cor-roxo-fundo`); o `--selo-*` aponta
    para elas; a meta usa `--meta-ideal`, `--meta-reduzida`, `--meta-minima` e
    `--meta-nao-fiz` (verde, azul, amarelo e vermelho - as de antes); bom e
    ruim (acerto na meta, alternativa certa, seta da semana) e as faixas do
    cronograma usam as cores com nome direto. **Por que:** trocar o selo
    pintaria a Reduzida de verde e a Mínima de outra cor sem ninguem pedir.
    Um teste proibe `--selo-*` fora do `design.css`. Os emojis da meta (✅ 🟦
    🟨 ❌) ficam: sao meta, nao selo. Duas mudancas de cor de proposito: o
    botao que gasta a API fica roxo, a cor da IA (o de apagar continua
    vermelho), e o roxo da IA e o mesmo da faixa de raciocinio.

56. **tres frases, cada uma para uma falta diferente.**
    - o ACERVO nao sustenta (incidencia, padrao, por qual assunto comecar):
      "Não há evidência suficiente no acervo para afirmar isso.", exata, numa
      constante so (`origem.FRASE_SEM_EVIDENCIA`, antes copiada em tres
      arquivos), com teste de que nenhum outro arquivo a escreve;
    - o meu DESEMPENHO tem pouca resposta: "Amostra insuficiente"
      (`amostra.INSUFICIENTE`, decisao 6), no Meu foco, na home, em Minhas
      materias e no "Onde estudar primeiro" - "amostra pequena" saiu;
    - FATO que ainda nao se sabe (prazo, banca, validade, edital nao lido, o
      que houve antes da primeira coleta): "nao sei ainda", como antes - nao
      e falta de evidencia no acervo.
    O aviso "base pequena" (so duas provas do cargo) continua: ele acompanha
    um numero que tem amostra, e nao toma o lugar dele.

57. **questao de IA: o 🟣 e "Gerada por IA: não é questão oficial da
    FEPESE." onde ela aparecer** - a questao aberta (antes do enunciado), o
    relatorio da rodada de IA, o acerto nas geradas do Simulado, a tela Gerar
    questoes e as geradas da ficha. No relatorio, a resposta certa da gerada
    leva "Resposta da IA", em roxo, e nunca "Gabarito definitivo".

58. **a varredura das telas e um teste** (`tests/test_varredura_das_telas.py`):
    21 telas abertas com uma base de data fixa, conferindo a regra 2 (nada de
    "vai cair", "devem cair", "certamente", "sempre cobra"...), a 5 (onde a
    questao de IA aparece, o 🟣 e a frase aparecem junto) e a 3 (toda
    porcentagem com a amostra perto: "em N", "de N", "(N)", "N questões", ou
    o numero da celula ao lado, na tabela e no grafico). Ela achou "Já caíram
    várias vezes e devem cair de novo" no cartao "Questões que ela repete" dos
    Macetes - previsao -, trocado por "é o que já aconteceu, e não uma
    previsão".

## Etapa 7B — as 6 telas no design system (03/10/2026)

59. **o roxo das telas antigas virou azul e neutro.** Concursos e Analises
    pintavam de roxo "Estadual SC", "A confirmar", a fase "autorizado" e o
    aviso de outra inscricao na secretaria. Desde a 7A o roxo e a cor da IA
    (decisao 53), e o roteiro manda usar so os tokens que ja existem. Ficou:
    **Estadual SC e o aviso da secretaria em azul** (`--cor-azul`), e **"a
    confirmar" e "autorizado" em cinza com borda tracejada** - e o "ainda nao
    sei" da tela. A cor do anel continua dizendo a distancia: perto verde,
    proximo amarelo, longe cinza. As outras cores das telas antigas foram para
    o token mais proximo (o vermelho de prazo, que era rosa, ficou o
    `--cor-vermelho`; o amarelo de "nao sei ainda", o `--cor-ambar`).

60. **a ponte dos nomes antigos saiu, e a barra do topo le os tokens.** O
    `design.css` mantinha `--fundo`, `--cartao`, `--azul`... apontando para os
    tokens novos, porque a barra do topo (`_topo_estilo.html`, dentro de toda
    pagina) e as telas antigas usavam esses nomes. Com a ultima tela migrada,
    a barra passou para os tokens e a ponte saiu - sem mudar a cara de nada,
    porque a ponte ja apontava para os mesmos valores. Um teste proibe os
    nomes velhos em qualquer template e no `design.css`, e outro exige
    `body class="ds"` em todo template de pagina. Na migracao, as classes que
    testes e links usam (`li class="nucleo"`, `atalhos`, `mais-filtros`,
    `detalhes`, `menu-faixa`) ficaram como estavam; mudou o estilo, nao a
    marcacao que outra parte le. A 404 continua sem a barra do topo, como
    sempre foi.

## Etapa 8 — a auditoria final integrada (03/10/2026)

61. **o aceite da §23 tem duas provas, e a etapa nao se da por concluida
    "porque existe codigo".** Cada item tem um teste em `tests/test_aceite.py`,
    com banco de fixture montado pelos mesmos construtores das etapas (a ficha
    do Art. 5º, a arvore, o acervo complementar, o banco antigo, a
    varredura), e o uso real com o banco e a config de verdade, registrado no
    `docs/auditoria_final.md`. O que mexeria em dado real foi feito numa copia
    (o `data/` pelo `RADAR_DATA_DIR`, a `config/` pelo `RADAR_CONFIG_DIR`). O
    item que nao atende vira pendencia com o motivo, e a etapa fica 🟡.

62. **os dois exemplos de geracao da §23 nao viram no a forca.** "Direito
    Penal > Aplicacao da lei penal > Lei penal no tempo" e "LEP > Progressao de
    regime > Art. 112" nao existem na arvore real (ela nasce do edital de 2019
    e da classificacao das questoes reais). O aceite prova o escopo fechado
    numa arvore de fixture com os dois caminhos, e o uso real roda com os nos
    mais proximos que existem; criar os dois caminhos como nos manuais fica
    para decisao sua (regra inviolavel 9). E o backup das 23h30, que a
    auditoria achou quebrado desde 27/09, e consertado numa etapa propria, e
    nao dentro da auditoria. **Corrigida em 03/10/2026:** nao havia o que
    decidir sobre os nos - a escolha tinha sido feita na Etapa 5 e so nao
    estava registrada aqui (decisao 66). E o backup foi consertado no mesmo
    dia (decisao 64).

## Correcoes depois da auditoria (03/10/2026)

A varredura dos docs, depois da Etapa 8, achou cinco pontos; eles foram
corrigidos nesta ordem, um de cada vez.

63. **o "Onde estudar primeiro" nao soma mais o alvo e o complementar.** Desde
    a fase do grafico (decisao "o reforco soma na fatia", acima), as questoes
    esperadas eram `peso x (do cargo + reforco) / (base do cargo + base do
    reforco)` - um numero so, feito das duas evidencias, o que a regra
    inviolavel 1 do novo.md proibe. E o "reforco" era qualquer caderno da
    FEPESE, aceito ou nao no levantamento da Etapa 3B. Agora:
    - as **questoes esperadas** e os **pontos a ganhar** sao so das provas do
      cargo: `peso da materia x fatia do assunto nas provas do cargo`;
    - o complementar e so o das provas **aceitas** no
      `data/acervo_complementar.json`, com a evidencia gravada - a mesma regra
      da incidencia;
    - ele pesa so na **ordem**, com o peso do `config/prioridade.yml` (0,25),
      a mesma conta da prioridade das fichas (decisao 44): `peso da materia x
      (fatia do cargo + 0,25 x fatia do complementar)`, vezes o que eu erro e o
      tempo, quando ha acerto medido. Com peso 0 a ordem e so a do cargo;
    - a tela mostra as duas fatias, cada uma sobre a sua base ("13 de 38 nas
      provas do cargo · 54 de 169 no acervo complementar, com peso 0,25 so na
      ordem"); assunto que so caiu no complementar aparece como "so no acervo
      complementar", sem questao esperada nenhuma;
    - a conclusao deixou de dizer que o assunto "deve valer" tantas questoes:
      e regra de priorizacao, e nao previsao. Ela diz "vem primeiro na ordem"
      e da as questoes esperadas pelas provas do cargo.
    Com o banco real, Interpretacao de texto continua em primeiro (4,8 → 5,1
    questoes esperadas, agora so do cargo), e "Conjuntos" (0 do cargo, 4 de
    outras provas) deixou de aparecer com 1 questao esperada.

64. **o backup roda com a pasta suja, e nunca mexe no que nao e dele.** O
    `radar sincronizar` fazia `git pull --rebase`, e o rebase recusa rodar com
    QUALQUER arquivo versionado mudado - o codigo de uma etapa pela metade
    bastava. Os logs mostram as 6 execucoes de 27/09 a 02/10 paradas nisso: o
    ultimo sincronizar que funcionou foi o de 25/09, o banco local ficou sem 32
    eventos da coleta do robo, e os 4 simulados de 28 e 29/09 so existem no
    `radar.db`. Atras dele havia um segundo defeito: o `git add` recebia os 15
    caminhos de `ARQUIVOS_DO_RADAR`, e `data/macetes.json`,
    `data/explicacoes.json` e `data/notas_semana.json` nao existem - com um
    caminho inexistente o `git add` para sem adicionar NENHUM, e o backup ia
    dizer "nada mudou" sem ter guardado nada. Agora:
    - o pull e `git fetch` + `git merge --ff-only origin/main`: o git avanca
      com a pasta suja, desde que o que chega nao caia num arquivo mudado aqui
      (se cair, ele recusa sem tocar em nada, e o comando para dizendo qual);
    - quando ha commit local que nao subiu e o robo subiu outro, so o rebase
      junta - e ele so roda com a pasta limpa; com conflito, `rebase --abort`
      e a pasta fica como estava. Nunca `--autostash`: com conflito na volta,
      ele deixaria marcas de conflito no meu codigo pela metade;
    - o `git add` leva so os arquivos que existem, e o commit leva os caminhos
      no fim (`git commit -- arquivos`): so os do radar, mesmo com outra coisa
      no stage. `git add` que falha para o comando, e nao vira "nada mudou";
    - o teste usa o **git de verdade**, em repositorios no `tmp_path` (a
      "origem" e uma pasta, sem internet): foi o git falso dos testes que
      deixou os dois defeitos passarem.

65. **a lista de leis alteradas e gravada pelo Claude Code, com procedencia, e
    fica por conferir.** A decisao antiga era esperar a minha conferencia antes
    de gravar - e a lista nunca nasceu. Agora:
    - cada questao de Direito das duas provas (115 das 170) foi conferida
      contra o texto **compilado e atualizado** (a Camara para lei federal,
      codigos e Constituicao - o Planalto recusa a conexao daqui -, e a ALESC
      para lei de SC), com a data de cada prova tirada dos documentos do
      acervo: 10/11/2013 e 01/12/2019. Entra so a mudanca com a anotacao da
      compilacao na mao, e que toca no que a questao cobra; jurisprudencia nao
      conta;
    - deu 17 questoes, em 15 itens (`config/leis.yml`, `mudancas`), e as
      `marcas` foram afinadas contra as 170 questoes reais com a mesma funcao
      que a tela usa: pegam as 17, nenhuma a mais;
    - cada item leva `procedencia` (modelo e data), `fonte` (o texto que foi
      lido - nao e link de "ler a lei") e `conferida: false`. Item com
      procedencia e sem `conferida: true` e dado de IA: o aviso sai com o 🟣
      "Escrito por IA, por conferir", e as telas Macetes e Mais dizem quantos
      faltam. Item sem procedencia e meu, e vale como conferido;
    - a evidencia de cada item (a anotacao copiada, o efeito em cada questao,
      os casos de fronteira que ficaram de fora e os limites da conferencia)
      esta em `docs/leis_alteradas.md`.
    Em 5 questoes o gabarito oficial ficou errado pela lei de hoje: 2013 q64 e
    q66, 2019 q46, q71 e q75.

66. **(registro atrasado, decisao de 02/10/2026, na Etapa 5) os dois exemplos
    de geracao da §23 rodam pelos equivalentes reais, e os literais mostram a
    recusa.** "Direito Penal > Aplicacao da Lei Penal > Lei penal no tempo" e
    "LEP > Progressao de regime > Art. 112" nao existem na arvore - a Etapa 2
    ja tinha visto que "Aplicacao da lei penal" e titulo de faixa do
    cronograma, e nao item do programa de 2019. Antes de comecar a Etapa 5 eu
    escolhi rodar os equivalentes reais (CP, art. 2º, e LEP, art. 119, 20
    questoes cada, no escopo) e mostrar que o filtro recusa e sugere os nomes
    literais, em vez de criar nos que o edital nao lista (regra inviolavel 9).
    A escolha ficou so no `progresso.md`; a auditoria da Etapa 8 nao a achou,
    reabriu a questao como "decisao sua" (decisao 62 e uma pendencia) e marcou
    o item 13 da §23 com ⚠️. Corrigido: o item 13 atende, a §23 fica com 18
    de 19 itens, e a pendencia saiu.

## As faixas que medem e o ciclo especifico (pedido de 03/10/2026)

O pedido de 03/10 (o sabado generico e o "item 4" das pendencias) foi
respondido em duas partes - as perguntas, com evidencia, e o plano - e
aprovado "com as recomendadas". As escolhas, de uma vez: o Pedido 1 e a secao
F inteira, em subetapas depois do Pedido 2, com o item 4 dela ja na 2A (1B);
a regra abaixo (2A); a comparacao de 07/11 mostra a rodada de 07/11 e o
acumulado do ciclo, separados (3A+C, na 2B); os simulados semanais ficam no
Qconcursos, com a composicao calculada (4A, na 2B); nenhum no de subassunto e
criado - a faixa mostra o assunto, o subassunto quando existe e o elemento
(5B, na 2C); o diagnostico de hoje espera a 2A (6B); so o complementar ACEITO
mede (7A); commit e push por subetapa (8A).

67. **a composicao das rodadas que medem e uma regra so, em
    `servico/composicao.py`, a mesma no diagnostico de 03/10 e no simulado de
    07/11.** O diagnostico mandava "Radar > Simulado > materia X", que sorteia
    de qualquer banca com aquele nome de materia - em Portugues, 254
    enunciados, 39 da IESES e 68 de provas que a 3B recusou -, sem dizer de
    que assunto. Agora:
    - o total e o do plano; com varias materias, ele se divide pelo quadro do
      edital com o `compilado.distribuir` (o do simulado compilado);
    - dentro da materia, o assunto com amostra no ALVO (`config/amostra.yml`:
      3 questoes em 2 provas) pesa "fatia do alvo + 0,25 x fatia do
      complementar" (a conta da prioridade, decisao 44); os sem amostra
      dividem o resto por igual, com a frase padrao, porque o edital nao da
      peso entre os assuntos de uma materia. A parte de cada grupo e a fatia
      das questoes do alvo que cai nele;
    - so questao real da FEPESE classificada no assunto (a arvore, e nao a
      coluna `assunto`): alvo primeiro, depois o complementar ACEITO; uma por
      chave e uma por enunciado, sem anulada, com gabarito, nunca gerada;
    - o que falta num assunto vai para os outros da materia, pelo mesmo peso,
      primeiro no mesmo grupo; faltou na materia inteira, falta mesmo;
    - o desempate entre assuntos de mesmo peso e a ordem do edital;
    - a escolha e deterministica (a semente e a faixa: data, bloco e posicao),
      a nunca respondida antes da respondida, e a rodada grava a composicao
      (`filtros["composicao"]`, com a regra) e a faixa de onde veio. Criada,
      ela nao e recriada.
    Com o banco de 03/10: Portugues sai com 8 de Interpretacao (9 questoes ·
    2 provas) e 1 de cada um dos outros 12 assuntos; Raciocinio Logico, que so
    caiu em 2019, sai todo pelo edital - 7 dos 12 assuntos nao tem questao real
    classificada, e a rodada usa 20 das 25 que existem. No 07/11, as 50 dao 13
    de Portugues, 8 de Raciocinio Logico, 13 de Direitos Humanos, 4 de
    Constitucional, 4 de Penal e 8 da LEP. A faixa so mede quando e diagnostico
    ou simulado FEITO NO RADAR; o simulado do Qconcursos fica para a 2B.

68. **o modo simulado da geracao divide as questoes pelo peso do edital**
    (item 4 da secao F das pendencias). A §8 pede que o modo 3 respeite "o
    edital, o peso das materias"; sem materia escolhida, a geracao sorteava as
    bases sem olhar o peso. Agora `geradas.preparar` divide o pedido pelo
    quadro do edital (o `compilado.distribuir`), so entre as materias com
    questao real do alvo para servir de base, e o `radar gerar` diz a divisao.
    Com a materia escolhida, nada muda: nao ha o que dividir.

69. **o simulado da semana fica no Qconcursos, e a composicao dele e a regra
    da 67 entre os temas ja estudados** (escolha 4A, subetapa 2B). O detalhe
    dos cinco simulados de sabado (03/10 a 31/10) trazia os numeros escritos a
    mao ("3 Penal (arts. 1º a 13) · 3 Constitucional..."). Agora a faixa tem so
    as materias (`materias_da_rodada`, sem numero), e a tela Hoje calcula
    (`composicao.compor_por_tema`):
    - o total e o do plano, dividido entre as materias pelo quadro do edital
      (o `compilado.distribuir`);
    - dentro da materia, a unidade e o TEMA estudado antes do dia (a faixa de
      estudo do cronograma), e nao o assunto do edital: e o tema que diz o que
      ja foi visto, e e ele que tem o filtro do Qconcursos;
    - o tema com amostra no alvo (pelos nos da ficha) entra pela incidencia,
      com o complementar a 0,25; os sem amostra dividem o resto por igual, com
      a frase padrao. No empate, o mais recente vai primeiro: e o simulado DA
      SEMANA, e o tema antigo volta no R+30 e no fechamento;
    - a parte dos temas sem amostra e o RESTO da incidencia da materia (as
      questoes do alvo fora dos temas com amostra), e nao a soma do que se
      contou neles - a unica diferenca de conta para a 67. Tema sem ficha ou
      sem no nao tem incidencia contada, e contar zero para ele zeraria o
      grupo; a tela diz "o tema não tem nó na árvore: o acervo não foi
      contado", e nao "nao apareceu";
    - materia sem tema estudado antes do dia fica fora da divisao;
    - nao ha rodada: a questao e do Qconcursos. A composicao nao e gravada, e
      muda quando mudam o acervo e as fichas.
    Com o banco de 03/10: o mini-simulado de hoje sai com 3 de Constitucional
    (art. 5º, I a XVI), 2 de Penal (aplicacao da lei penal) e 5 da LEP (3 de
    assistencia ao preso, 2 de objeto e classificacao) - o plano escrevia
    "3 Penal (arts. 1º a 13)", mas o art. 13 so e estudado em 05/10. O de
    10/10 sai com 9 de Portugues, 9 de Direitos Humanos, 3 de Constitucional,
    3 de Penal e 6 da LEP. As faixas de Portugues nao tem `filtro` no plano, e
    a tela manda procurar pelo nome do tema - filtro do Qconcursos nao se
    inventa.

70. **o sabado diz o que revisar com o que ja esta gravado**
    (`servico/sabado.py`, subetapa 2B):
    - a **Revisao semanal** mostra os temas da semana do plano (com os nos da
      ficha e o link para ela), os erros anotados no caderno de segunda a
      sabado - o mesmo filtro do link "abrir os erros da semana" -, por tema,
      os temas com mais erro e os motivos, e os artigos-chave do `essencial`
      de cada dia. O detalhe da faixa nao mudou;
    - o **R+7 dos diagnosticos** (10/10) lista os erros das rodadas de 03/10
      por assunto e cria, pelo botao "Criar a rodada com os erros", uma rodada
      so com eles: questao real, nunca recriada. O plano pede 5: com mais
      erros, ele refaz 5, divididos entre os assuntos pelo numero de erros (o
      `compilado.distribuir`); com menos, refaz todos. Quem reconhece a faixa
      e o dado: revisao NO RADAR com dia de origem;
    - a **correcao de 07/11** ganhou a chave `compara_com: '2026-10-03'`
      (conferida no carregamento) e mostra, por materia, o diagnostico de
      03/10, o fechamento de 07/11 e o acumulado do ciclo sem consulta (o
      numero de Minhas materias): tres colunas, nunca somadas, com "Amostra
      insuficiente" abaixo de 20 respostas (o minimo da materia no
      `config/amostra.yml`). Com 20 questoes por materia no diagnostico e de 4
      a 13 no fechamento, o fechamento sozinho nunca tem amostra - e por isso
      o acumulado do ciclo fica do lado, como a escolha 3A+C combinou.
    As duas contas novas - o acerto de varias rodadas juntas e os erros delas -
    moram no `servico/metricas.py`.

71. **a faixa diz onde esta na arvore** (escolha 5B, subetapa 2C). O assunto
    e o subassunto so apareciam dentro da ficha. Agora cada faixa com ficha,
    ou com no do plano, mostra nela mesma o assunto, o subassunto - ou "nao ha
    subassunto na arvore para este tema" - e o elemento exato
    (`fichas.onde_na_arvore`):
    - pela ficha (🟣, escrita pela IA e por conferir): os nos dela, agrupados
      por assunto; sem no, o assunto e o subassunto que ela escreveu (a
      importacao conferiu os dois contra a arvore), com o aviso de que a
      ficha nao aponta no;
    - sem ficha, pelos nos do plano (📌): a chave nova `nos` da faixa no
      `cronograma.yml` - uma lista, como a da ficha, conferida no carregamento
      contra a arvore e contra a materia da faixa -, ou o `conteudo`. O
      `conteudo` continua sendo o no em que o acerto e anotado; `nos` so diz o
      que a faixa cobre;
    - "o assunto inteiro" so quando o no escolhido e o proprio assunto e a
      arvore tem subassunto nele. A LEP tem subassunto na arvore (Remicao,
      Assistencia...), mas nao para o trabalho do preso: ali a frase e "nao ha
      subassunto na arvore para este tema";
    - nenhum no foi criado. O bonus ganhou `nos` com Logica proposicional (ou
      sentencial), Tabelas-verdade e Equivalencias - o titulo diz logica
      proposicional e o detalhe, tabelas-verdade e equivalencias, e os tres
      sao assuntos do edital -, e a interpretacao cronometrada com
      Compreensao e interpretacao de texto, de 05/10 em diante. Os dias
      passados ficaram como estavam.
    Com o plano real, as 176 faixas de questoes de 03/10 a 07/11 dizem o
    assunto: 167 nesta linha (137 pela ficha, 30 pelo plano) e 9 na composicao
    do sabado (decisoes 67 e 69). Junto, o `ler_programa` passou a juntar a
    palavra partida no hifen, o que antes so a leitura do PDF fazia: o texto
    do edital usado nos testes dava "Tabelas- verdade", e a arvore real tem
    "Tabelas-verdade".

## O estoque de geradas ate 07/11 (pedido de 03/10/2026)

72. **a variacao com escopo grava a materia e o assunto do ESCOPO**, e nao os
    da questao real que serviu de base. Achado no lote 1: a base do
    complementar pode vir de um bloco generico de outra prova ("Conhecimentos
    Especificos", "Legislacao e Educacao"), e a variacao herdava esse nome - 3
    das 19 do abolitio criminis, e cerca de 27 nos 57 lotes do plano, ficariam
    fora do treino de Direito Penal no /geradas, que sorteia pela materia. O
    `geradas._preparar_no_escopo` poe a materia e o ultimo nome do escopo no
    pedido de variacao, como ja fazia no do zero, e o `manual` usa os dois. O
    pedido amplo, sem escopo, nao muda. O caminho da API (`--valendo`) nao tem
    o defeito: ele nao usa escopo e so varia questao do alvo.

73. **o estoque de geradas ate 07/11 e so dos nos de subassunto**, um no por
    lote (o `--pedido` fecha um escopo so), aprovado com as recomendadas:
    - quanto: o deficit do tema - as questoes das faixas de treino de 04/10 a
      07/11 (fixacao, aprendizagem, Portugues, R+7, R+30, bonus e
      interpretacao; diagnostico e simulados ficam fora, porque medem) menos as
      reais ainda nao respondidas nos nos dele - dividido entre os nos de
      subassunto do tema, no maximo 20 por no, e 5 no no que e um artigo so.
      Da 57 lotes e 725 questoes (216 por variacao, 509 do zero);
    - os 28 temas sem subassunto na arvore (15 so com o assunto, 13 com ficha
      sem no) ficam sem estoque: gerar com materia, assunto e subassunto
      pediria criar no, e a escolha 5B foi nao criar;
    - a ordem e a da data de uso, uma semana por vez: o /geradas sorteia pela
      materia, e o estoque de um tema ainda nao estudado entraria no treino;
    - o lote 1 (abolitio criminis, 19) foi feito junto, em 03/10; os outros 56
      sao feitos por mim, pelo `docs/estoque_de_geradas.md`.

## A secao F das pendencias (Pedido 1 de 03/10/2026)

74. **o "Onde estudar primeiro" e a revisao espacada leem a arvore de
    conteudos** (F1). O assunto vinha do catalogo de palavras-chave
    (Portugues e Raciocinio Logico) e da coluna `assunto` (o resto, zerada em
    25/09): a tela dizia que as nove materias de Direito nao tinham "nenhuma
    questao classificada", com as 170 do cargo classificadas e conferidas
    desde 02/10 - e o catalogo dava outros numeros que a Incidencia (13 de 38
    em Interpretacao, contra 9 de 22). A decisao 9 da 3A tinha deixado isso
    para depois da conferencia; ela foi feita, e agora:
    - o assunto e o no de nivel assunto da arvore (o item do edital) em que a
      questao foi classificada. As fatias sao as da incidencia: as questoes do
      cargo (evidencia alvo) e as do complementar aceito, cada uma sobre a sua
      base, e o complementar so na ordem, como na decisao 63;
    - o meu acerto em cada assunto e o do desempenho por conteudo (decisao 7):
      a tela mostra a divisao "radar X% em N · anotado Y% em M", e a soma dos
      dois so faz a conta - a amostra e os pontos a ganhar. Antes ela
      mostrava "eu acerto X%", somado;
    - "sem assunto" e a questao do cargo pendente ou classificada so na
      materia (eram 108; sao 12), e a materia sem nenhuma linha continua na
      lista das que caem na prova (eram 9; e nenhuma);
    - a revisao espacada agenda pelo mesmo assunto (a classificacao da
      questao); sem assunto, a materia, como antes;
    - o selo do assunto no painel passou de 🟡 "classificacao por
      palavra-chave" para 🔵 acervo: e a contagem por no da incidencia.
    Com o banco de 03/10: 66 assuntos em todas as materias; a LEP vem
    primeiro, com 10 questoes esperadas, porque o edital tem um item so para a
    lei inteira. O painel ficou ~1 s mais lento (as ocorrencias do
    complementar e o desempenho por no): a tela Analises abre em ~3 s e a home
    em ~4 s.

75. **so o complementar ACEITO entra no costume da banca, no treino do alvo e
    no compilado** (F2). Dois lugares ainda usavam qualquer prova da FEPESE:
    - o **"costume de qualquer banca"** dos Macetes contava "sobre o acervo
      inteiro": na FEPESE, as 170 do cargo, as 5.015 do complementar aceito e
      as 2.341 de provas que a 3B recusou num numero so - estatistica, contra a
      regra inviolavel 1. Agora ele conta so a evidencia que vale: da banca do
      alvo, o complementar aceito (as provas do cargo tem a Central de
      macetes); de outra banca, a prova dela (fora). O que ficou de fora vai
      contado na tela ("Ficaram fora desta conta 170 das provas do meu cargo e
      2.341 de provas que a Etapa 3B recusou"), e nunca somado;
    - o **"Treinar"** do alvo, e o **compilado**, que sai da mesma lista e mede,
      completavam com qualquer prova de evidencia complementar. Agora so com
      as aceitas: 1.593 questoes da banca nas materias do cargo, contra 2.190
      (saem 597 de provas recusadas). Escolha de 03/10: e treino, mas a prova
      recusada pode ter o gabarito ou a materia errados, e a regra fica uma
      so com a da rodada que mede (escolha 7A).
    A evidencia de cada prova sai do `evidencia.por_prova`, a regra unica.

76. **nas Regras de Mandela, a fonte e a regra, pelo numero** (03/10). O
    `radar gerar --importar` exige, nas materias de lei, que a fonte cite
    "art." ou "sumula" (`manual.CITA_ARTIGO`). As Regras Minimas da ONU para o
    Tratamento de Presos, que o edital cobra em Direitos Humanos, nao tem
    artigo: citam-se pela regra ("Regras de Mandela, regra 12.1"), e essa
    citacao correta era recusada - os lotes 50 e 57 do estoque pararam nela.
    Agora "regra" seguida de numero tambem serve, na questao, no macete e na
    explicacao, e o pedido diz isso a quem responde. Sem o numero continua
    recusado ("conforme as Regras de Mandela"), como "conforme a doutrina".
    Escolha de 03/10, entre aceitar a regra e citar ao lado o artigo da LEP ou
    da CF que dissesse o mesmo: a questao cita a fonte verdadeira.

77. **a questao gerada guarda a CHAVE da questao real de base, e o selo so
    aponta questao real por ela** (F3). O `geradas.origem_de` achava a base
    pela impressao do enunciado, com `limit(1)`; e a FEPESE repete o comando
    ("De acordo com a Lei de Execucao Penal, e correto") em questoes de
    alternativas diferentes - o selo podia apontar a errada. Agora:
    - a variacao grava a `origem_chave` (enunciado e alternativas,
      `questoes.chave_da_questao`), pela API e pelo `radar gerar --importar`;
    - o selo acha a base pela chave; sem chave, so quando a impressao aponta
      uma questao so (ou a mesma questao em mais de um caderno);
    - a variacao antiga cuja impressao aponta questoes diferentes fica SEM
      base: o passo 5 da migracao nao escolhe uma, e a tela diz "o acervo
      daqui nao consegue identificar" em vez de "escrita do zero", que ela
      nao foi.
    No banco de 03/10: 206 das 239 variacoes ganharam a chave; 33 ficaram sem
    (30 do estoque de 03/10, 3 de 27/09).

78. **os padroes de cobranca tambem do acervo complementar, a parte e so com
    gabarito definitivo** (F4). A secao 13 pede que todo padrao diga em
    quantas questoes e em quantas provas foi observado, e se veio do alvo ou do
    complementar; ate aqui os padroes so eram calculados para o alvo, e o
    `entra_nos_padroes` da 3B so aparecia nos relatorios. Agora:
    - os mesmos padroes (forma de perguntar, gabarito, termos) sao contados no
      complementar, so das provas aceitas com gabarito DEFINITIVO - o
      provisorio muda depois dos recursos, e o padrao se mede sobre a letra
      certa - e em questao distinta, pela chave;
    - dentro de um no, as regras da linha complementar: na materia conta a
      questao que o caderno poe nela; abaixo, so a classificada;
    - tipo de questao e pegadinha saem so da classificacao CONFERIDA. A do
      complementar e automatica e ninguem a conferiu ainda (B.8), entao hoje
      nao aparecem, e a tela diz por que;
    - aparecem na Incidencia (o bloco da materia), na ficha e no terminal,
      ao lado dos do alvo, com a amostra "· acervo complementar FEPESE", e
      nunca somados.
    No banco de 03/10: 22 das 122 provas aceitas tem gabarito definitivo (940
    questoes); em Portugues, 45 questoes em 22 provas.

79. **a ultima revisao de um conteudo e so o que e revisao, e a evolucao
    conta toda resposta** (F5, secao 19 do novo.md). O Meu desempenho ganhou
    a secao "Quando eu estudei e revisei cada conteudo": cada no em que eu ja
    encostei, com a ultima vez, a ultima revisao e, no assunto, o acerto
    semana a semana. As regras:
    - **revisao** e a faixa de revisao do plano (`revisao`, `revisao_semanal`)
      ou o estudo extra de revisao anotados no no, ou questao dele respondida
      numa rodada que revisa - a revisao espacada (`revisao` nos filtros) e
      as rodadas so de erradas (`erros`: o "Refazer as erradas" e a do
      sabado). Questao de faixa de questoes ou de rodada comum e pratica, e
      nao muda a data. Quem marca e o `Lancamento.revisao` do `metricas`, e
      o `ultima_revisao`, que existia desde a Etapa 4 e nunca era preenchido,
      passou a ser;
    - **a evolucao conta TODA resposta**, cada uma na semana em que foi dada,
      pela conta do `metricas` (o acerto sem consulta, em questao real): as
      mesmas contas da tela Semanas, como a Etapa 4 ja prometia. Antes a
      parte do radar contava so a ultima resposta de cada questao - errar em
      28/09 e acertar em 29/09 dava "100% em 1", e o erro sumia. A resposta
      do radar chega ao no pela chave da questao (`Lancamento.chave`);
    - **a semana abaixo do minimo do no** (`config/amostra.yml`: 10 no
      assunto) aparece em cinza, com o numero: e pouco para dizer se eu
      melhorei. Nenhuma tendencia e calculada;
    - a fila, os nao estudados e a secao nova saem das mesmas situacoes,
      montadas uma vez por tela.
    Com o banco de 03/10, 10 nos de Portugues praticados no radar, todos com
    "nunca" na revisao: nenhuma rodada de revisao foi feita, e nenhuma faixa
    do plano chega a conteudo (pendencias, secao F).

80. **o painel deixou de refazer a mesma conta varias vezes por pagina**
    (F6). A home levava ~4 s e Analises ~3 s, e o perfil mostrou de onde:
    - o `config/cronograma.yml` (180 mil caracteres) era interpretado 6 vezes
      por abertura da home. Passou a ser lido pelo leitor em C do PyYAML (a
      libyaml), que da o mesmo resultado ~8 vezes mais rapido; sem ela
      instalada, fica o leitor em Python;
    - a chave de cada uma das ~5 mil questoes do complementar era refeita a
      cada pagina. A impressao (`questoes.impressao_de`) e funcao pura - o
      mesmo texto da sempre o mesmo resultado - e agora fica guardada em
      memoria (`functools.cache`);
    - o `criar_tabelas` olhava as colunas de todas as tabelas a cada chamada,
      ~40 por pagina. Agora confere uma vez por conexao, como ja fazia com a
      versao do banco. **Consequencia:** um banco trocado por baixo de um
      processo que ja esta rodando so e conferido numa conexao nova
      (`db.resetar_engine()`, ou o radar aberto de novo) - e assim que o banco
      antigo chega depois de um `git pull`, e o `_restaurar` da migracao ja
      solta a conexao antes;
    - a linha complementar de cada no perguntava, para cada no da arvore, se
      cada questao estava debaixo dele (770 mil comparacoes). Agora cada
      questao entra direto no no dela e nos de cima, na mesma ordem.
    Com o banco de 03/10: a home de ~4,2 s para ~1,4 s (a primeira abertura
    depois de ligar o servidor, ~2 s, porque faz a conta das chaves uma vez),
    Analises de ~3 s para ~1 s, o Meu desempenho de 1,6 s para 0,4 s, a
    Incidencia de 1,3 s para 0,4 s e a Hoje de 3 s para 1,1 s. As 25 paginas
    conferidas sairam iguais byte a byte antes e depois (com o
    `PYTHONHASHSEED` fixo), tirando o relogio da Hoje e a estimativa de custo
    da /geradas, que sorteia as questoes de base a cada abertura.

81. **a faixa sem `conteudo` conta no que ela cobre, so para a situacao e as
    datas** (F7, a opcao (b) que voce escolheu em 03/10). So 6 faixas do plano
    tem a chave `conteudo`, e nenhum R+7: sem ela, a teoria, a lei seca e o
    R+7 contavam no dia e em no nenhum, e o Meu desempenho nao via o que eu
    estudava nas faixas. Agora:
    - **o que a faixa cobre** sao os `nos` que o plano da a ela (📌, meu dado)
      e, depois que eu confiro a ficha do tema, os nos da ficha - ou, na ficha
      sem no, o assunto e o subassunto que ela escreve. **A ficha por
      conferir nao entra**: ate la, o vinculo e so da IA;
    - nesses nos (e nos de cima) a faixa marca **estudado ou praticado e as
      datas** - o estudo, a pratica e a revisao -, e alimenta a fila de
      revisao e o "o que eu ainda nao estudei";
    - **o acerto nao vai a no nenhum**: nao se sabe de qual dos nos cobertos
      ele e. O desempenho, o estado e a evolucao continuam so com o radar e o
      anotado no `conteudo` (decisao 71). Nem os minutos sao espalhados;
    - a faixa COM `conteudo` continua como era: so o no escolhido.
    Com o banco de 04/10 nada muda ainda: nenhuma das 61 fichas esta
    conferida, e nenhuma faixa com `nos` foi feita (as primeiras sao de
    05/10). Com as duas fichas das faixas ja marcadas (28 e 29/09) conferidas,
    9 nos de Penal e Constitucional passariam a "estudado e praticado", e a
    fila de revisao iria de 10 para 19.

82. **a revisao feita fora do radar passa o 1-7-30 de etapa** (F8, a opcao
    (b) que voce aprovou em 04/10). O prazo so andava com acerto no RADAR na
    data do vencimento ou depois: o R+7 feito no Qconcursos marcava a data da
    revisao (decisao 79), mas o conteudo continuava "prazo de revisao vencido".
    Agora:
    - a faixa de revisao marcada (o R+7) e o estudo extra de revisao, no
      vencimento ou depois, passam o conteudo para a etapa seguinte, como o
      acerto no radar ja fazia. Antes do vencimento e treino, e nao conta - a
      mesma regra do `espacada.py`;
    - a rodada de revisao do radar continua andando pelo acerto: errar nela
      marca a data da revisao, mas nao passa de etapa;
    - a revisao sem questao (o extra de revisao so de leitura) deixou de
      contar como estudo. Contar reiniciaria o prazo na etapa 1 em vez de
      passar de etapa - e a decisao 20 ja dizia que "estudado" vem de faixa de
      estudo e de extra de teoria ou de lei seca.
    Com o banco de 04/10 a fila continua com 10: nenhum R+7 nem extra de
    revisao foi feito ainda.

## O lote de 04/10/2026 (o resto da secao F, as conferencias e os abertos)

83. **os ultimos minimos fixos foram para o `config/amostra.yml`** (F11).
    Eram excecoes declaradas desde a varredura de 03/10, e o pedido do lote
    foi resolver a secao F com o que eu recomendo. Agora:
    - `desempenho.evolucao` (20): respostas em cada metade da comparacao dos
      ultimos 30 dias, na evolucao da home - era o `MINIMO_PARA_EVOLUCAO`;
    - `acervo.tendencia_de_gabarito` (50): questoes com gabarito para falar
      de tendencia de letra nos Macetes - era o `MINIMO_PARA_TENDENCIA`;
    - `acervo.provas_para_tendencia` (3): abaixo disto de provas, o que sai
      delas leva o aviso "base pequena" - era o `PROVAS_PARA_TENDENCIA` dos
      cartoes e o `length < 3` do Meu foco, da home e da previsao.
    Os valores nao mudaram. Os dois do acervo ficam na secao `acervo` porque
    falam da banca, e o da evolucao na `desempenho`, porque fala de mim - as
    duas secoes nunca se somam. O teste que procura minimo escrito em codigo
    passou a vigiar os tres nomes e os templates. Fica de fora so o 3 do
    `servico/erros.py`, que mede a fatia de um motivo de erro, e nao acerto.

84. **o que mudou na lei num ponto que nenhuma questao cobra vai para a ficha
    do tema** (F12). Os 9 "casos de fronteira" do `docs/leis_alteradas.md`
    tinham ficado fora do aviso da questao, para ele nao virar ruido - e
    tambem fora de qualquer tela. Agora:
    - moram na lista `fronteira:` do `config/leis.yml`, com o que mudou, a
      lei, a fonte onde conferir, a procedencia e `conferida: false`;
    - chegam a ficha de estudo do tema - e so a ela -, por dois caminhos
      escritos no item: um no dele no mesmo ramo de um no do tema, ou uma
      marca dele no titulo do tema, na mesma materia (a saida temporaria nao
      tem no na arvore, e nenhum no foi criado). A ficha sem no vale pelo
      subassunto que escreve; so o assunto - na LEP, a lei inteira - poria
      cada caso em todas as fichas da materia;
    - a contagem de leis por conferir passou a somar as duas listas (15 + 9).
    Conferidos no texto da Camara de 03/10: a EC 104/2019 (art. 144, VI e §
    5º-A), a LEP arts. 41, 122 e 126, § 9º, o CP art. 25, paragrafo unico, e a
    CF arts. 201 e 206, IX. Na conferencia apareceram os arts. 41-A e 41-B da
    LEP (Lei 15.358/2026), que entraram no item do art. 41. Os tres de lei
    especial (Maria da Penha, tortura, desarmamento) ficam com a conferencia
    de 03/10 e o link do Planalto. Hoje cinco fichas mostram o aviso; os de
    lei especial, seguridade e educacao esperam as fichas do Ciclo 2.

85. **o primeiro contato com um conteudo e a primeira resposta, de todas**
    (F15). A ancora do 1-7-30 de quem so praticou (sem estudo) e a primeira
    pratica, mas ela era tirada da ULTIMA resposta de cada questao: refazer
    uma questao empurrava o "primeiro contato" para o dia da refeita, e o
    prazo andava para frente sem eu ter revisado nada. Agora a primeira e a
    ultima pratica saem de toda resposta (`metricas.respostas_reais`). O
    acerto que passa de etapa continua o da ultima resposta de cada questao;
    a anulada continua fora. Junto (F14), o "estudado" passou a usar as
    constantes da decisao 20, que estavam declaradas e sem uso: so a faixa de
    estudo (teoria, lei seca, portugues, raciocinio) e o extra de teoria ou de
    lei seca - a correcao marcada, mesmo apontando o no, nao e estudo.

86. **os conceitos associados respondem a §14, item 7, e nunca entram na
    contagem** (F13). A pergunta "quais conceitos aparecem associados" nao
    tinha resposta: as 402 classificacoes eram todas principais. Agora:
    - `radar classificar --pedido --associados` pede, para cada questao do
      alvo com a principal, os OUTROS nos que ela tambem cobra, no enunciado
      ou nas alternativas, com o trecho; a importacao recusa no fora da arvore,
      a materia inteira, o ramo da principal (o no, os de cima e os de baixo)
      e conceito sem trecho, sem gravar a questao pela metade, e nao
      sobrescreve associado que eu ja tenha conferido;
    - o associado e a classificacao NAO principal que o modelo ja previa; a
      principal conferida nao muda;
    - a Incidencia mostra, em cada materia, "Conceitos que aparecem juntos
      nas questoes": o par (principal + associado), as questoes e o selo 🟣
      "Classificacao do Claude Code, por conferir"; o `radar incidencia
      --padroes` tambem. A contagem da tabela continua so com a principal.
    O Claude Code respondeu as 155 questoes do alvo (04/10): 74 com
    associado, 109 associacoes, 81 so com o principal ("na duvida, deixe de
    fora"). As 402 classificacoes de antes ficaram identicas, e as celulas de
    amostra da Incidencia sairam iguais.

87. **a conferencia do complementar tem tela, e o lote do catalogo voltou**
    (B.8). A tela Analises > Conferencia so listava o alvo; agora tem o filtro
    "Evidencia" (alvo ou complementar aceito, nunca os dois juntos). No
    complementar ela lista uma linha por questao CLASSIFICADA (a mesma questao
    aparece em varios cadernos do concurso, um por cargo, e a classificacao e
    uma so, pela chave), e a proposta automatica do catalogo se confere por
    amostra: as 20 primeiras de cada materia pelo hash da chave - sempre as
    mesmas -, com a conta "conferidas" e "corrigidas ou pendentes". O tamanho
    da amostra mora no `config/amostra.yml` (`acervo.amostra_do_catalogo`).
    Corrigir uma proposta do catalogo guarda no trecho que ela era do
    catalogo, para a amostra nao perder justamente o erro.
    O Claude Code conferiu a amostra em 04/10: o catalogo errou o assunto em
    9 das 20 de Portugues e em 9 das 16 de Raciocinio Logico. Ele casa
    palavra no enunciado: "lacunas do texto" virava Interpretacao, "conjunto
    {2, 3, 4}" virava Conjuntos, pronome ia para Classes gramaticais. Pela
    regra da 3B, o lote voltou: as 108 foram classificadas de novo, uma a uma,
    pelo `radar classificar --importar` (lote 4: 104 com no e 4 pendentes -
    3 sem item no edital, conjuncoes, silabas e sujeito, e a de MS Word que o
    caderno grudou no Raciocinio). Nenhum no foi criado. A regencia, que o
    edital de 2019 nao tem, foi para Termos integrantes > Objeto direto e
    indireto, o mesmo lugar da ficha. E a proposta do catalogo que perde o
    posto de principal SAI, em vez de virar associada como as outras:
    palavra-chave casada nao e conceito que a questao cobra (as 73 que ja
    tinham virado associadas na importacao foram apagadas).

88. **a cor forcada pela URL e o `?cor=`, e o `tema` e so o filtro dos
    Macetes** (04/10; achado da 7A, em 03/10). O mesmo nome fazia as duas coisas:
    `/macetes?tema=claro` pintava a tela de claro E procurava o tema "claro",
    e o botao ☀️/🌙, que tira o parametro da cor da volta, tirava junto o
    filtro. Ficou o `tema` do filtro, que e o que aparece em link salvo (as
    fichas apontam para os Macetes por ele); a cor passou a `?cor=claro` /
    `?cor=escuro`. O cookie continua `tema`: e interno, e renomear apagaria a
    escolha gravada no navegador. De quebra, a tela Semanas passou a levar a
    cor forcada no "salvar nota" - ela lia uma variavel que nunca existia.

89. **as geradas antigas ganharam materia e no, e as erradas sairam do
    sorteio** (04/10). As 50 de antes do escopo fechado so tinham a materia no
    `conteudo`, e as 20 de 28/09 ainda tinham a materia "Aplicacao da lei
    penal (arts. 1º a 12)" - fora do treino de Direito Penal no /geradas. O
    Claude Code leu as 50 contra a lei: as 20 viraram "Direito Penal" (as do
    art. 2º no no do art. 2º; o resto fica na materia, porque o edital de 2019
    nao tem "aplicacao da lei penal"); 13 de LEP e as 10 de Portugues ganharam
    o no do artigo ou do assunto. E 7 variacoes de LEP de 27/09 tinham gabarito
    errado ou nenhuma alternativa certa - diretor sem o nivel superior do art.
    75, egresso fora do art. 26, o trabalho que o art. 39, V, faz dever, a
    remicao pelo trabalho no regime aberto que o art. 126 nao da: foram
    rejeitadas pelo mesmo `rejeitar` do botao "essa questao esta errada".
    Nenhuma tinha resposta, entao nada foi apagado; o texto delas continua no
    arquivo, marcado. Duas duvidosas ficaram para mim (pendencia D).

90. **o leitor do caderno conserta o que grudava, o que sumia e o que trocava
    de materia; e reler o caderno leva a classificacao junto, so quando e a
    mesma questao** (04/10; B.7, B.9 e B.10). No `questoes.py`:
    - a ultima alternativa e cortada no titulo da secao seguinte ("Direitos
      Humanos 10 questoes", tambem o de duas linhas e o entre parenteses de
      2013) e no fim do caderno da FEPESE (a grade de respostas, o rodape da
      fundacao, a "Coluna em Branco");
    - a linha que continua uma palavra quebrada nao e mais apagada como
      cabecalho repetido: as quatro questoes de 2019 que acabavam em "e cor-"
      voltaram a "e correto afirmar:";
    - o "100." saiu do enunciado da questao 100 (o corte so aceitava dois
      digitos), e a questao voltou inteira;
    - a ORDEM das secoes sai da primeira questao depois de cada titulo, quando
      essa pista fecha as faixas: o extrator de duas colunas punha o titulo de
      Direito Processual Penal depois do de Legislacao Estadual no
      Socioeducativo, e 162 questoes de 13 cadernos estavam na materia
      vizinha (as 8 da B.10, reclassificadas: 6 com no e 2 pendentes, porque a
      Constituicao do Estado nao esta no edital de 2019);
    - o numero da questao nao e o "N." da lista numerada da alternativa
      anterior ("1. silepse • 2. comparacao" / "3. eufemismo"): 29 questoes
      que sumiam voltaram, 26 delas a questao 20 de cadernos de Florianopolis.
    No download, dois hotsites com arquivo de mesmo nome (a FEPESE chama de
    S07.pdf provas diferentes de Palhoca) dividiam o caminho, e o segundo
    nunca era baixado: a prova dele apontava para o PDF do outro, e 16 dessas
    copias estavam ACEITAS no complementar com o rotulo errado. Agora o caminho
    de outra url ganha o nome do hotsite na frente, e a reconstrucao pelo
    manifesto usa o caminho gravado. As 21 provas que faltavam foram baixadas
    (o dono de cada PDF e o hotsite impresso na capa), as 5 respostas de
    simulado que caiam nas copias foram para a questao identica da prova dona,
    e as 840 copias sairam.
    O `radar questoes --refazer` agora leva a classificacao e a base das
    geradas para a chave nova quando o texto muda (`classificacoes.rechavear`,
    `geradas.rechavear`) - a antiga que ainda existe em outro caderno e
    copiada, a que sumiu e levada, fica uma principal por questao, a
    conferida -, mas so quando o texto novo e o da MESMA questao (um contido
    no outro, ou 80% igual). Quando o numero passa a ser de outra questao, a
    classificacao fica onde estava. As duas releituras de verdade (cada uma
    ensaiada antes numa copia do banco): 637 questoes com o texto limpo, 64
    classificacoes e 45 geradas levadas para a chave nova, 799 questoes das
    provas baixadas, 29 recuperadas, 1 numero corrigido sem levar nada; o
    banco foi de 8.433 a 8.421 questoes, as 511 classificacoes sairam iguais
    tirando a chave (402 principais, 170 conferidas, nenhuma orfa), e as 236
    geradas com base continuam com ela. A auditoria do alvo passou a "nenhuma
    suspeita", e o complementar aceito foi de 122 para 169 provas (das 14
    fora, so 3 ainda pela numeracao). A pendente trocada tambem passou a sair
    sempre, e nao so quando a nova nao e pendente.

## Depois do lote de 04/10/2026

91. **as geradas se treinam pelo no: materia, assunto ou subassunto** (04/10;
    pedido do dia). O "Treinar com as que ja tenho" do /geradas trocou o
    seletor de materia por um seletor da arvore - a materia e, recuados
    dentro dela, os assuntos e os subassuntos que tem gerada, cada um com
    quantas valem (`geradas.conteudos_para_treinar`). Escolher um no sorteia
    dele e de tudo abaixo (`criar_simulado(conteudo=...)`): o assunto pega os
    subassuntos, o subassunto pega os elementos, e a materia pega tambem a
    gerada que ficou sem no, pela coluna `materia`. O filtro e pelo
    separador " > ", e nao pelo comeco do texto, para "Teoria do crime" nao
    pegar um irmao que comece igual. O elemento nao vira opcao - poucas
    geradas por elemento, e a lista viraria um paredao. O no vai gravado nos
    `filtros` da rodada, e o `materia` do POST continua valendo. A ficha do
    tema manda um link por no dela, com o no ja escolhido
    (`/geradas?treinar=<no>`), em vez de mandar para a materia inteira - que
    misturava os temas ainda nao estudados. No que nao tem gerada volta com
    recado, sem criar rodada vazia.

92. **os macetes e as explicacoes existem, escritos contra o texto vigente**
    (04/10; o `radar gerar --pedido --macetes` / `--explicacoes` e o
    `--importar`). O Claude Code respondeu os dois lotes a mao, com a
    procedencia "Claude Code, importado manualmente, em 04/10/2026":
    - **40 macetes** em `data/macetes.json`, ate 3 por materia nas 14 do alvo,
      cada um citando as questoes reais em que se apoia (as 40 abrem as
      questoes certas). Todo artigo citado foi lido no texto compilado (CF,
      CP, CPP, LEP, Leis 11.340, 9.455, 10.826 e 8.429, DL 200; LC 529, LC
      774 da ALESC) e no `docs/leis_alteradas.md`; quando a lei mudou depois
      da prova, o macete diz isso (improbidade, carreira estadual, piso do
      trabalho do preso, remicao no domiciliar). Os 3 macetes de Sociologia
      Aplicada sem lei citam a obra ou o proprio gabarito oficial;
    - **6 explicacoes** em `data/explicacoes.json`, das 10 questoes reais que
      eu errei. As outras 4 dependem do texto da prova ou do termo
      sublinhado, que o radar nao guarda - e a regra e "sem fonte segura, nao
      responda". Ficaram sem explicacao em vez de explicacao chutada.

93. **o texto de gente fora da tela web tambem tem acento** (o resto da A2;
    decisao 5 da Etapa 1B). Ganhou acento: a saida do terminal (`cli.py`, 240
    textos), a mensagem do Telegram (o anel pelo nome, "Inscrições abertas",
    "Inscrição até" e o evento pela frase da tela, `eventos.para_tela`, e
    nao pela chave "Situacao: a -> b"), a linha do tempo do `radar eventos`,
    o `__str__` dos resultados do servico, o `docs/auditoria.md`
    (regenerado: so o texto mudou, os numeros sao os mesmos) e o motivo de
    elegibilidade (o nivel pelo nome, "médio"; os 37 concursos relidos, nenhum
    veredito mudou). A troca no `cli.py` foi feita por uma ferramenta que so
    mexe em literal de texto (fora docstring, log, regex, chave e comparacao)
    e so em palavra sem ambiguidade; e/é, esta/está, da/dá e tem/têm foram
    decididos um a um. **Fica sem acento de proposito:** a descricao de cada
    comando no `radar --help` (e a docstring, e o codigo segue sem acento),
    os valores que eu digito (`--anel proximo`, `--modo revisao`, `--marcar
    minima`), as chaves gravadas, os prompts de IA e os nomes de assunto do
    `macetes.py`.

    *Nota da auditoria independente (04/10):* a releitura dos 37 editais
    mudou tambem o campo `escolaridade` de 8 concursos (ex.: "Fundamental"
    vira "superior, fundamental", quando o edital tem vagas dos dois
    niveis); o veredito de elegibilidade de nenhum mudou. O `concursos.json`
    com os valores novos subiu no backup das 23h30 de 04/10.

94. **os conceitos associados se conferem na Analises > Conferencia**
    (decisao 86). Cada questao do alvo mostra os associados dela, com o
    trecho, o selo 🟣 "por conferir" ou ✓ e dois botoes: Confirmar (grava a
    data; continua fora da contagem) e Tirar (apaga o associado; a principal
    nao muda). O topo conta "N de M conceitos associados conferidos", e o
    filtro "só com associado por conferir" deixa so as que faltam. A
    importacao nova passou a tirar o associado que saiu da resposta - menos o
    conferido, que e meu.

95. **o leitor do caderno entende o texto-base compartilhado e a marca
    minuscula** (os 3 cadernos que sobraram da decisao 90):
    - uma lista que comeca em "1." e segue em sequencia ANTES do numero da
      questao e o texto-base de um grupo ("Caso 3: 1. Lancamento... 8.
      Arrecadacao...", e so entao "49."): a questao e o primeiro marcador que
      quebra a sequencia; e a ultima alternativa da questao de cima para no
      "Caso N" / "Texto N" ou no "Para responder as questoes...". O S7 de Sao
      Jose 2024 foi de 59 para 60 questoes (e a "questao 1" dele deixou de
      ser o lixo do Caso 3);
    - a caixa da alternativa errada tambem sai como "square", em minusculas
      (Palhoca emergencial 2024, Brusque educa 2023): o leitor so achava a
      certa e lia 14 de 39;
    - o `migracoes.ultima_copia()` escolhe pela HORA do fim do nome e so pasta
      com o banco: a ordem alfabetica comecava pela versao. As 15 pastas de
      teste (`antigo.db` de 8 KB) sairam de `data/copias/`.
    Comparado o leitor de antes com o de agora nos 216 cadernos, 12 mudaram:
    os 3 de fora e 9 em que so a alternativa "e" perdeu o texto-base grudado
    nela (inclusive as questoes 6 e 8 da prova de 2019 do alvo). A releitura
    (ensaiada antes numa copia): 41 questoes novas (8.421 -> 8.462), 29 com o
    texto mudado (4 classificacoes e 9 geradas levadas para a chave nova), 26
    em que o numero passou a ser de outra questao (a classificacao ficou na
    chave antiga); as 511 classificacoes iguais (402 principais, 170
    conferidas, nenhuma orfa) e as 236 geradas com base continuam com ela. A
    auditoria do alvo segue sem suspeita, e o complementar aceito foi de 169
    para 172 provas - das 11 fora, nenhuma mais pela numeracao.

## A auditoria independente de 04/10/2026 e a Rodada 1 das correcoes

A auditoria (`docs/auditoria_independente.md`) conferiu 186 requisitos e achou
8 defeitos (BUG-1 a BUG-8); o plano de correcao esta na secao R14 dela, em
rodadas. A Rodada 1 (sem decisao sua pendente) consertou quatro:

96. **com elemento pedido, o escopo da importacao sao os ELEMENTOS, e o no
    declarado tem de existir na arvore** (BUG-1 e BUG-2). A importacao de
    geradas conferia so o prefixo do subassunto: aceitava um caminho que
    comecava certo e terminava num no inventado, e aceitava a questao do
    elemento irmao (pedi o art. 26, entrava o art. 24 citando o numero 26;
    pedi o Protocolo de San Salvador, entrava o Pacto de San Jose - para
    elemento que nao e artigo, nada separava os dois). Agora
    `manual._fora_do_escopo` usa a regra do `Escopo.dentro` (com elemento,
    so os elementos e o que houver abaixo deles) e recusa no que nao esta na
    arvore. Junto, a instrucao do pedido com elemento passa a listar o
    CAMINHO de cada elemento em "CONTEUDO (um destes caminhos)", e nao o do
    subassunto - copiar o subassunto, como a instrucao antiga mandava, seria
    recusado. As 775 geradas do registro nao caem em nenhuma das recusas
    novas (conferido no banco real).

Os outros dois consertos da rodada nao mudam regra: o
`test_prazo_e_retificacao_saem_com_acento` deixou de depender de
31/10/2026 (quebraria o Actions em 01/11, BUG-8), e o `radar gerar --modo
revisao` sem nada estudado, sem `--pedido`, da a mesma frase do `--pedido`
em vez de traceback (BUG-6).

## A Rodada 2 das correcoes da auditoria (04/10/2026)

97. **a materia de uma prova antiga vale pelo nome do edital em todo filtro
    e em todo acerto por materia** (BUG-4). O `config/taxonomia.yml` ja
    dizia que "Direito Processo Penal" (2013) e "Direito Processual Penal";
    a incidencia usava isso, mas a geracao, o simulado por materia, a
    revisao espacada e o catalogo do complementar filtravam pela coluna crua
    e so achavam 2019. Agora a taxonomia responde as duas perguntas -
    `grafias(materia)` (todas as grafias que valem como ela) e
    `nome_do_edital(grafia)` - e os quatro filtros usam `grafias`; o acerto
    por materia do `metricas` agrupa por `nome_do_edital`, e a questao sem
    materia se chama "sem matéria". O dado gravado nao muda. A comparacao
    difusa do `compilado.mesma_materia` (0,85) continua onde estava: ela
    casa o nome do quadro do edital com o do caderno, e trocá-la e outra
    conversa.

98. **o `radar padrao` mostra um bloco por evidencia** (regra inviolavel 1).
    O comando antigo somava as provas do cargo, o complementar - aceito e
    recusado - e a IESES num numero so, chamado "Incidencia por materia".
    Agora `servico.incidencia_por_evidencia` devolve tres blocos (Policia
    Penal SC, acervo complementar FEPESE aceito, outras bancas), cada um com
    "N questoes · M provas", contando questao DISTINTA (pela chave) e as
    ocorrencias ao lado quando a banca repete caderno (decisao 14 da 3B); a
    prova complementar recusada na validacao fica de fora e e contada no
    rodape. O `incidencia_por_materia`, que so este comando usava, saiu.

## As Rodadas 3 e 4 e o resto da auditoria (05/10/2026)

99. **o mesmo conceito em dois nos vira um so, e a classificacao recusa o
    subassunto novo parecido com um que ja existe** (BUG-3). A classificacao
    do complementar criou, ao lado dos nos do alvo, 12 subassuntos que eram
    o mesmo conceito com outro nome (Sistema interamericano, Geracoes dos
    direitos humanos, Caracteristicas dos direitos humanos, tratados com
    forca de emenda, direitos dos trabalhadores, orgaos e atribuicoes da
    seguranca publica, direito a educacao, CPP art. 306, a pena da tortura,
    as formas de violencia da Maria da Penha): a incidencia e o desempenho
    contavam o mesmo assunto em dois lugares. O `radar conteudos --juntar
    <duplicado> --em <mantido>` (com copia antes) leva os nos de baixo, as
    classificacoes (a principal fica uma so), as geradas (conteudo e
    escopo), o caderno de erros, o estudo extra e os `nos` das fichas para
    o no mantido - sempre o do alvo -, e apaga o duplicado. Os 12 foram
    juntados em 05/10 (arvore 426 → 408 nos). Para nao voltar:
    `conteudos.no_parecido` (o mesmo nome sem acento, um nome inteiro dentro
    do outro por palavra, ou 90% de semelhanca) faz a classificacao recusar
    o subassunto novo e dizer qual usar. Tres pares parecidos NAO foram
    juntados, porque nao sao o mesmo conceito com certeza (pendencia G).

100. **o `db.py` so cria a coluna nova; dado levado do antigo e passo do
     `migracoes.py`**. O recado do ADD COLUMN automatico mandava rodar
     `radar reclassificar`, que so serve as colunas da coleta. Agora diz que
     a coluna nasce vazia nas linhas antigas e que o que precisa de dado vem
     dos passos de `radar migrar` (que rodam em seguida, decisao 80).

101. **o modo revisao da geracao aceita o no so praticado, e diz quantos sao**
     (BUG-7, contra a letra da decisao 20). O `nos_estudados` juntava o no
     com estudo registrado e o no que so tem resposta; o certo pela decisao
     20 seria so o primeiro, mas o no respondido tambem ja foi visto, e
     revisar o que se errou praticando e o objetivo da revisao. Fica aceito
     de proposito: `servico.geradas.nos_da_revisao` devolve os dois grupos
     separados, e o `radar gerar --modo revisao` mostra "N estudado(s) · M so
     praticado(s)".

102. **migrar um banco antigo nao sobrescreve o JSON versionado que tem mais
     linhas** (BUG-5). Os passos 1, 4 e 5 da migracao exportavam o banco que
     estava sendo migrado: migrar uma copia velha trocava as 779 geradas do
     `questoes_geradas.json` por 50. Agora `migracoes._exportar_sem_perder`
     compara: com menos linhas no banco que no arquivo, o arquivo fica e o
     log diz por que. O `radar exportar` continua sobrescrevendo, porque e
     pedido de proposito.

103. **a resposta do simulado volta para a questao pela CHAVE** (a mesma
     regra da classificacao, decisao 77). O `simulados.json` apontava a
     questao so por (prova, numero): reler o caderno com a numeracao
     consertada trocaria a questao respondida. A linha exportada ganha a
     `chave`, e a importacao procura por ela no mesmo caderno antes do par
     prova + numero, que continua valendo para o arquivo antigo.

## O pedido de 05/10/2026 (depois das Rodadas 3 e 4)

104. **a classificacao do complementar que uma segunda leitura as cegas pos
     no MESMO no conta como conferida - pelo Claude Code, e a tela diz
     isso.** Muda a regra de que conferir e so seu (decisao 16), a seu
     pedido: as 232 classificacoes do complementar tomariam um tempo de
     estudo. As 215 questoes distintas sem conferencia foram classificadas
     de novo por 5 leituras independentes, que nao viram a classificacao de
     antes. No igual, com confianca alta ou media: 176, marcadas com
     `conferida_por = "Claude Code, reanálise às cegas"` (coluna nova; nula
     com `conferida_em` = conferida por voce). As outras 39 - no igual com
     confianca baixa (4), o mesmo assunto num nivel acima ou abaixo (21) e
     outro subassunto (14) - ficam para voce, com as duas leituras lado a
     lado em `docs/reanalise_do_complementar.md`. A conferida por voce nunca
     e tocada, e a sua conferencia de uma marcada pelo Claude Code apaga a
     marca dele. Os 109 conceitos associados do alvo e as fichas continuam
     so seus.

105. **os diagnosticos passam de 03/10 para 10/10, e o R+7 deles refaz
     TODOS os erros em 17/10.** Os diagnosticos de 03/10 nao foram feitos
     (nenhuma rodada no banco), e voce quer comecar a medir nesta semana.
     Em 10/10: o de Raciocinio Logico de manha, no lugar do R+7, e o de
     Portugues a noite, no lugar das 10 questoes de contagem. Em 17/10: o
     R+7 "refazer os erros dos diagnosticos" com `questoes: 40` - o maximo
     dos dois somados, para a faixa refazer todos (a regra de dividir pelo
     assunto continua no codigo, para faixa que pedir menos que os erros) -,
     com o motivo de cada erro no caderno. A comparacao de 07/11, que decide
     o Ciclo 2, passa a ser com 10/10. O dia 03/10 fica como estava: passado
     nao se reescreve.

Junto, sem decisao nova: os 3 pares parecidos foram juntados (decisao 99:
Accountability, Brasileiros natos, Progressao funcional - os tres no nome
mais curto, que cobre a questao do outro) e as 2 geradas antigas da decisao
89 foram rejeitadas (a do "conjuge" e a do "art. 76" da LEP; a 10 e a 12, do
mesmo lote, ja estavam).

106. **Portugues e Raciocinio Logico do complementar classificados em duas
     leituras independentes; a arvore ganha, DEBAIXO dos assuntos do edital,
     o que a FEPESE cobra e o edital nao nomeia.** Antes de classificar, tres
     subassuntos criados a mao: "Regencia verbal e nominal" (em Termos
     integrantes - a regencia e a relacao do verbo e do nome com o
     complemento), "Fonologia: fonema, silaba, encontros vocalicos e
     digrafos" (em Acentuacao grafica, que depende dela) e "Lacunas com a, a
     e ha" (em Emprego da crase). Figura de linguagem e parte da
     interpretacao de texto (a lista de tipos de elemento ja a previa): vira
     subassunto de Compreensao e interpretacao. O que o edital de 2019 nao
     lista em lugar nenhum - formacao de palavras, tipos de sujeito (termo
     essencial; o edital so traz os integrantes), variacao linguistica,
     funcoes da linguagem - fica pendente, com o motivo: o assunto continua
     sendo so do edital. As 204 questoes sem classificacao (173 + 31): a
     primeira leitura no formato do `radar classificar --importar`, com os
     nomes de subassunto novo unificados antes de importar (cinco agentes
     deram nomes diferentes ao mesmo conceito); a segunda as cegas, so com o
     caminho. No igual com confianca alta ou media: 161 conferidas pelo
     Claude Code (a regra da decisao 104). Ficam para voce 24, mais as 19
     pendentes (18 em que as duas leituras concordaram), em
     `docs/classificacao_pt_rl.md`. Com isso, o complementar aceito de
     Portugues (251 questoes distintas) e de Raciocinio (45) nao tem mais
     questao sem classificacao.

107. **a faixa de questoes de Portugues comeca pelas do radar e termina no
     Qconcursos** (pedido de 05/10, a opcao recomendada). O complementar
     aceito tem 251 questoes distintas de Portugues da FEPESE, e o dia pede
     21 de um tema so (6 de manha, 15 a noite): varios temas tem 1 a 3. Por
     isso a faixa NAO foi trocada para o radar: ela continua no Qconcursos,
     e ganha na tela Hoje o botao "Comecar pelas N do radar" - as questoes
     reais do tema (os nos da ficha, ou o que ela escreveu, ou os do plano;
     o mesmo caminho do `fichas.onde_na_arvore`), do alvo primeiro e depois
     do complementar aceito, uma por chave, sem anulada, que eu ainda nao
     respondi e que nao estao noutra faixa (a manha e a noite do mesmo tema
     nao repetem). O resto, a tela diz quantas, no Qconcursos. As do radar
     contam sozinhas no desempenho por tema e no 1-7-30; o "fiz X, acertei
     Y" da faixa fica so para as do Qconcursos. A rodada nao mede: nao entra
     na comparacao do fechamento. Mora no `servico/faixa_no_radar.py`; so
     Portugues por enquanto (`MATERIAS`), a materia que o complementar
     cobre inteira.

## A revisao final do estudo, subetapa R1 (05/10/2026)

A Fase 1 do pedido de 05/10 ("revisao final do estudo") foi aprovada com as
16 respostas recomendadas; cada uma vira decisao na subetapa em que e
aplicada. Na R1:

108. **"Caiu ou nao caiu" e uma conta so, prova a prova**
     (`incidencia.caiu_no_alvo`), usada pela ficha, pela faixa da tela Hoje,
     pela aba Fichas e, na R4, pela redistribuicao. Tres fontes, nunca
     aproximadas:
     - a questao classificada num no do tema (a regra do mapa);
     - **sem no na ficha**, a questao classificada na mesma materia cujo
       ARTIGO gravado (`dispositivo`) cai na faixa de artigos do tema ("LEP,
       arts. 28 a 37"), e so da mesma lei (`LEI_DO_DISPOSITIVO`: CP, CPP, CF,
       LEP). A questao de Sociologia que cita a LEP nao conta na LEP;
     - a questao **PENDENTE** da materia com o artigo do tema: caiu, e vai a
       parte, com o aviso. Motivo: a "Aplicacao da lei penal" dizia "0
       questoes · 0 provas", e cairam 4 (2013 q50, q51, q53; 2019 q51),
       pendentes porque o tema nao esta no programa de 2019. A incidencia do
       NO continua sem elas.
     O "—" de cada ano sai do CADERNO daquele ano (a materia que ele
     declara), e nao da classificacao: as 4 de Direito Administrativo de
     2013 que foram para Administracao Publica nao fazem a materia "existir"
     em 2013. A classe do tema (para a R4): **cheio** quando caiu nas provas
     que bastam (o `minimo_provas` do `config/amostra.yml`, 2); **normal**
     quando caiu numa; **basico** quando nao caiu, com a materia nas 2
     provas e o tema contado. Tema sem contagem (sem no e sem faixa de
     artigos) ou de materia de uma prova so (LEP, Raciocinio, Legislacao
     Especial, Sociologia) **nao e rebaixado**, e a tela diz "Base de uma
     prova so, e o tema nao e rebaixado: Nao ha evidencia suficiente no
     acervo para afirmar isso.";
109. **o exemplo real e a questao inteira**: enunciado, alternativas e o
     gabarito oficial (🟢, a questao tirada da prova), recolhidos num
     `<details>`; a pegadinha da classificacao (🔵), a explicacao escrita
     quando existe (🟣, `data/explicacoes.json`, pela impressao do
     enunciado) e o aviso da lei que mudou depois da prova. Os **macetes**
     entram na ficha pela questao real que citam (prova e numero), e nunca
     pelo nome do assunto: macete sem questao do tema nao aparece. O titulo
     "Questoes reais relacionadas" fica (§11 e o aceite);
110. **a lei seca dirigida e do tema da teoria do mesmo dia e da mesma
     materia** (`fichas.da_faixa_no_dia`), so para a tela: o botao da
     ficha (e o do resumo, na R2) e o "onde na arvore". O "estudado" da
     Etapa 4 nao muda: so conta a faixa com ficha propria;
111. **a aba Fichas abre no DIA, por bloco** (Manha, Noite, Depois das
     22h), um cartao por tema em cada bloco em que ele aparece, com o
     caminho na arvore, as faixas do bloco, "Policia Penal SC (2013 e
     2019)" prova a prova e "Outras provas FEPESE (complementar aceito)" em
     linha separada. Faixa com materia sem ficha (o bonus) aparece como
     "Ficha ainda nao escrita para este tema". A lista do ciclo inteiro
     continua em `/fichas?ver=todas`, agora com o mesmo "caiu".
     **O defeito relatado (o art. 13 sumido na aba) nao se reproduziu** com
     o codigo e o dado de 05/10, nem no servidor que estava no ar: a lista
     antiga o tinha na 2a linha. A causa provavel era a lista do ciclo
     inteiro sem manha e noite; o dia por bloco resolve de qualquer jeito.

## A revisao final do estudo, subetapa R6 (05/10/2026)

112. **a faixa de questoes diz onde fazer, nesta ordem** (as decisoes suas da
     Fase 1, item 10): "Voce estudou: <tema>; na arvore: <no>"; **1º no
     Qconcursos**, que mede (o filtro da faixa, ou "procure pelo nome do
     tema"); **2º, se quiser mais, as geradas do radar**, que so treinam e
     cujo acerto e um segundo numero. Com gerada no no: "N questoes geradas
     deste assunto" e o botao "Treinar no radar" (form POST para
     `/geradas/treinar`, sem JavaScript). Sem gerada: "Nao ha questao gerada
     deste assunto ainda." e os 3 passos. O check da faixa continua guardando
     so o que eu fiz no Qconcursos. Vale para as faixas `questoes`, `revisao`
     e `bonus` com materia; diagnostico e simulado medem e ficam de fora;
113. **o N do pedido**: as questoes da faixa divididas entre os nos dela por
     igual (o resto para os primeiros), menos as geradas validas que cada no
     ja tem (nele e abaixo, `servico.geradas.contagem_por_no`), **no minimo
     5** (`fichas.PEDIDO_MINIMO_DE_GERADAS`). No com o bastante nao pede.
     A ficha SEM no fica "sem no na arvore", sem comando: o assunto que ela
     escreve pode ser a lei inteira (na LEP, 150 geradas), e contar as
     geradas dele seria aproximar. Sem ficha, valem os `nos` do plano ou o
     `conteudo`;
114. **o comando e `.venv\Scripts\radar.exe`**, e sai de uma funcao so
     (`fichas.comando_de_gerar`, com `RADAR_NO_WINDOWS`), como os passos 2 e
     3 (`PASSO_NO_CLAUDE_CODE`, `COMANDO_DE_IMPORTAR`, `AVISO_DO_PEDIDO`):
     a faixa, a ficha, a tela de gerar e o `radar hoje` mostram o mesmo
     texto. `python -m radar` nao funciona (o pacote nao tem `__main__.py`).
     O `--elemento` so vai quando o proprio no e um elemento da arvore.
     Nenhum comando mostrado tem `--valendo`, e o botao da API nao aparece;
115. **a tela Gerar questoes lista os nos do cronograma**, das faixas de
     treino do comeco do plano ate 7 dias depois de hoje, os com zero
     tambem ("sem questao gerada"), cada um com os 3 passos num `<details>`
     e o N pela maior cota que uma faixa pede dele (`servico.geradas.
     nos_do_cronograma`). O "Treinar com as que ja tenho" nao mudou.

## A revisao final do estudo, subetapa R3 (05/10/2026)

116. **a procedencia do texto de IA passa a dizer o modelo** (revisa a
     decisao 47, a seu pedido na Fase 1): "Claude Code (claude-opus-5-5),
     <o que fez>, em <data>". A 47 tirava o modelo porque o importador nao
     sabe quem respondeu; quem escreve sabe, e o CLAUDE.md e a decisao 65 ja
     pediam "modelo e data". **O que ja esta gravado nao muda** - nenhuma
     procedencia antiga e reescrita. Na R3, a correcao a mao das 7 fichas
     acrescentou "; corrigida pelo Claude Code (claude-opus-5-5) em
     05/10/2026 (R3)" ao campo `modelo`. A importacao (`manual.procedencia`)
     passa a usar o modelo na R2, quando a resposta disser qual foi;
117. **nas Regras de Mandela, a ficha da a letra da traducao do CNJ (2016),
     com a nota do original em ingles quando os dois diferem** (sua escolha
     na Fase 1). A ficha manda ler o CNJ, e a prova tende a copiar a
     traducao oficial. Nas regras 12 (o ingles condiciona ao alojamento em
     celas individuais) e 40 (o ingles diz "in any disciplinary capacity"; o
     CNJ, "em cumprimento a qualquer medida disciplinar"), a correcao de
     04/10, que seguia o ingles, foi revista; e a pegadinha que contradizia
     a letra do CNJ saiu.

## A revisao final do estudo, subetapa R2 (05/10/2026)

118. **o resumo do tema mora na ficha** (`resumo` no `data/fichas.json`, sem
     estrutura paralela; a ficha sem resumo fica no arquivo como era). A
     **parte 1 ("caiu ou nao caiu") e calculada na hora** (🔵, o
     `incidencia.caiu_no_alvo`), e nao texto gravado: o numero acompanha
     qualquer reclassificacao. As partes 2 a 6 (dominar, artigos, como a
     banca cobra, pegadinhas, o basico) sao texto de IA (🟣), e **cada frase
     tem as fontes**. A importacao (e o `radar fichas --verificar-resumos`,
     que confere de novo contra o acervo do dia - o item 4e) recusa: frase
     sem fonte; questao fora do tema ou com o gabarito trocado; "como a
     banca cobra" sem questao real (sem nenhuma, so a frase exata de
     evidencia insuficiente); pegadinha sem questao e sem a marca "sem
     questão real"; artigo sem dispositivo nas materias de lei; o basico
     quando o tema caiu, ou faltando quando e da classe basica; e previsao.
     O resumo conferido por mim nao e sobrescrito;
119. **a questao de outra prova se cita com o prefixo `FEPESE-`**
     ("FEPESE-2024-q8"): o mesmo ano e numero pode ser de outra prova, e
     "2013-q6" do complementar se confundia com a prova de 2013 do cargo;
120. **o botao "Resumo" fica em toda faixa ligada a materia, menos a pausa,
     e na aba Fichas**; abre uma janela por cima da pagina SO com CSS
     (`.ds-janela`, `:target`/`:has(:target)`, no `design.css`), com
     "Fechar"; na Noite, ja em "como a banca cobra". A lei seca abre o da
     teoria do dia (decisao 110). Faixa de varios temas abre a lista: a
     correcao, os temas do dia; a revisao semanal, os estudados de segunda
     ate o dia; o simulado e o diagnostico, os das materias deles estudados
     ate o dia; o R+7 dos diagnosticos, os das materias dos diagnosticos do
     dia de origem. Faixa com materia e sem ficha: "Resumo ainda nao escrito
     para este tema". Nenhum JavaScript novo;
121. **a procedencia com o modelo vale na importacao** (aplica a 116): a
     resposta declara o `modelo` ("claude-opus-5-5"), e a procedencia fica
     "Claude Code (claude-opus-5-5), importado manualmente, em <data>"; sem a
     declaracao (ou com texto que nao e nome de modelo), o texto de antes;
122. **a explicacao das questoes reais do alvo que sao exemplo de tema**
     (`radar fichas --pedido --explicacoes`): o mesmo lote "explicacoes" e a
     mesma importacao do `--explicacoes` (o gabarito oficial manda, a fonte
     e obrigatoria), com a instrucao propria ("onde estava a pegadinha", e
     nao "eu errei"). A fonte por paragrafo ("§ 5 da Declaracao de Viena")
     passou a servir, como a "regra 12" de Mandela (decisao 76): chamar o §
     de "art." para passar na trava seria citar errado;
123. **montar um ciclo novo inclui escrever as fichas e os resumos dos temas
     dele**, pelo mesmo fluxo (`radar fichas --pedido`, depois `--pedido
     --resumos` e `--pedido --explicacoes`), antes do primeiro dia do ciclo.
     Esta registrado na pendencia do Ciclo 2.

## A revisao final do estudo, subetapa R4 (05/10/2026)

124. **o Ciclo 1 foi redistribuido pela classe de cada tema** (decisao 108),
     de 06/10 a 07/11, aprovado por voce com o ensaio dia a dia:
     - tema **basico** (nao caiu nas 2 provas, com no ou faixa de artigos,
       sem pendente do tema): Direito - teoria 40→30, fixacao 8→4, lei seca
       20→10, aprendizagem com `teto` 10 (14 quando o complementar tem
       amostra); Portugues - teoria 20→15, fixacao 6→4, noite com `teto` 6
       (8 com complementar); R+7/R+30 de tema basico - 10→6;
     - o tempo que sai vira a faixa **"Extra: <tema>"** (`tipo: revisao`,
       `rotulo: Extra`, sem consulta), no mesmo dia, de um tema que CAIU, da
       MESMA materia, ja estudado, o de contato mais antigo no plano (empate:
       mais questoes no alvo). A da noite usa `sobra_da_rampa`: a rampa do
       nivel menos o teto, e o total do dia fica igual em todo nivel. O
       prefixo "Extra: " entrou no `PREFIXOS_DO_TEMA`: a faixa tem ficha,
       resumo e geradas do tema dela;
     - **o teto com complementar e 14, e nao os 15 da Fase 1**: o
       arredondamento de 5 em 5 min so fecha com teto par (com 15, o dia do
       nivel 2 ficaria 5 min mais longo);
     - **os minutos de cada dia ficaram iguais nos niveis 1 a 6; as questoes
       subiram** onde a teoria e a lei seca viraram questao: +2 em 07, 13 e
       21/10 e +8 em 20/10 (2119 → 2133 no plano). Na Fase 1 eu tinha
       escrito que as questoes tambem ficavam iguais, e estava errado;
     - mudaram 7 dias: 07/10 (Concordancia verbal 2), 12/10 (R+7 do art. 13),
       13/10 (Crase 2), 20/10 (Direitos sociais), 21/10 (Pronomes 3), 27/10
       (R+7 de Direitos sociais) e 04/11 (R+30 do art. 13). A LEP e o
       Raciocinio (uma prova so) e os temas sem contagem nao rebaixaram, e o
       R+30 da Aplicacao da lei penal (28/10) tambem nao: as 4 pendentes dele
       cairam nas 2 provas. Os dias ate 05/10, os titulos e as datas dos temas
       nao mudaram; a fotografia de antes esta em
       `tests/fixtures/cronograma_antes_da_r4.json`.
     A mesma regra vale para montar o Ciclo 2 (decisao 123).

## A revisao final do estudo, subetapa R5 (05/10/2026)

125. **o estoque de geradas se completa sob demanda** (sua escolha na Fase
     1): com o Qconcursos primeiro e as geradas so como treino a mais
     (decisao 112), nao se gera a falta inteira de uma vez. O saldo por no
     (falta 231, sobra 410, 24 nos com zero) esta no
     `docs/estoque_de_geradas.md`; cada faixa diz quanto falta no no dela e
     da os 3 passos, e o estoque - por no, e nao por dia - nunca e refeito
     nem apagado.

## A revisao final do estudo, subetapa R7 (05/10/2026)

126. **(registro atrasado, pedido de 05/10) o radar vai para a nuvem com
     login e dois perfis - planejado, e nao comecado.** O CLAUDE.md dizia
     "nao tem login, nao vai para producao", e a decisao de 26/09 (o `radar
     web --rede`) tambem; o pedido de 05/10 abriu o roteiro
     ([roteiro_nuvem.md](roteiro_nuvem.md), etapas N0 a N6), com as perguntas
     que voce responde antes da N1. Ate la, vale o sistema local de sempre.
     Achado na conferencia dos docs da Fase 1, que viu o roteiro sem a
     decisao.

Junto, sem decisao nova: a decisao 47 ("nunca o nome de um modelo" na
procedencia) foi revista pela 116 e pela 121 - o texto de IA novo diz o
modelo, e o antigo continua como esta; a 10ª gerada rejeitada, que so estava
no banco, foi exportada para o `questoes_geradas.json` (775 linhas, 10
rejeitadas); e os 2 macetes de "Direito Processo Penal" (o nome do caderno de
2013) passaram ao nome do edital, "Direito Processual Penal".

## O treino de IA no "Fiz hoje" (05/10/2026)

127. **o segundo numero do dia diz os acertos e os erros do treino de IA, no
     tamanho do "Fiz hoje".** Era "Treino de IA: 10 de 23 (43%), fora do
     acerto", miudo e cinza embaixo do total: os erros ficavam para quem le
     calcular, e a linha passava despercebida. Agora e "Treino de IA: 23
     questoes = 10 acertos + 13 erros (43%), fora do acerto real; conta no
     volume", no mesmo molde e no mesmo tamanho do "Fiz hoje". A frase e uma
     so (`metricas.frase_da_ia`): a Hoje, as Minhas materias, as Semanas e o
     `radar hoje` mudaram juntas. Continua um numero a parte, nunca somado ao
     acerto das reais (a regra de sempre).

Junto, sem decisao nova: o dia 05/10 foi corrigido a seu pedido. As 3 faixas
de questoes (Fixacao: Fato tipico, Fixacao: Vozes do verbo e o R+7 da
Aplicacao da lei penal) estavam anotadas com os mesmos numeros das respostas
dadas no radar - 26 questoes contadas duas vezes, e 23 delas, de IA, entrando
como acerto real. Pela regra da 1D (faixa de questoes com 0 nao conta como
feita), elas foram desmarcadas, e o tempo delas (20 + 15 + 25 min) virou
estudo extra "Onde: Radar", que guarda so o tempo. O "Fiz hoje" passou de 53
questoes (14 + 16 + 23 de IA) para 26 (2 + 1 + 23 de IA), com as mesmas 2h.
Fica em aberto impedir que a faixa repita o que foi respondido no radar:
avisar ou bloquear, a sua escolha.

## Uma fila de revisao so, e as ultimas contas fora dos templates (06/10/2026)

128. **a home mostra a fila de revisao do Meu desempenho, e nao mais a
     agenda do `espacada.py`.** Eram duas filas com dois numeros (a
     auditoria de 04/10, CL-11 e N1-3): a da home, por materia e assunto,
     so do erro no radar; a do Meu desempenho (`servico/estudo.py`), pelo no
     da arvore, com o erro recente, o acerto abaixo do corte e o prazo 1-7-30.
     Ficou a segunda. A home mostra so as **pontas** dela (`estudo.pontas`:
     o no sem descendente na fila) - o erro num subassunto poe na fila ele, o
     assunto e a materia, e contar os tres seria contar a mesma revisao tres
     vezes -, com o motivo de cada uma e a proxima revisao quando a fila esta
     vazia (`estudo.proxima_revisao`). O botao "Fazer as revisoes de hoje"
     monta a rodada pelas mesmas pontas (`espacada.criar_simulado_de_revisao`):
     primeiro as erradas do no, depois questao real do no ou de um no abaixo
     dele que eu nunca respondi, 3 por no; no sem questao nenhuma nao vira
     rodada vazia. A rodada grava `revisao: [{no, etapa, motivos}]`, e o
     `metricas` continua a conta-la como revisao (decisao 79). A agenda antiga
     (`espacada.agenda`/`pendentes`) saiu; o `espacada.py` guarda os
     intervalos e a rodada. Junto, um defeito da fila do `estudo`: feita a
     revisao de 30 dias, o prazo nunca acabava e o no voltava por prazo para
     sempre; agora acaba, como acabava na agenda antiga. E as duas contas que
     sobravam em template foram para o Python - o "faltarao" do simulado
     (`LinhaDoCompilado.faltarao`) e o numero de questoes reais da ficha
     (`FichaDeEstudo.reais`) -, a conferencia dos dias pede ao `metricas`
     tambem o numero de respostas de IA, e o teste que vigia os templates
     passou a olhar a conta dentro de `{{ }}`, que ele deixava passar.

## A faixa avisa o que ja foi respondido no radar (06/10/2026)

130. **a faixa de questoes avisa quantas dela ja foram respondidas no radar,
     e o "fiz" deixa de vir com o numero do plano - so avisa, nao bloqueia**
     (sua escolha, fechando o que a decisao 127 deixou em aberto). O
     `metricas.no_radar_por_faixa` conta, por faixa (bloco, indice e
     titulo), o que foi respondido nas rodadas que ela abriu: a das reais
     (`faixa`, decisoes 67 e 107) e a de geradas aberta pelo botao "Treinar
     no radar", que passou a guardar a faixa em `da_faixa` - chave propria,
     porque o `composicao.rodada_da_faixa` pega a primeira rodada com
     `faixa`, e a de geradas tomaria o lugar da que mede. Com resposta no
     radar, a faixa diz "Voce ja respondeu N desta faixa no radar (X reais e
     Y de IA): elas ja contam sozinhas no Fiz hoje", e o "fiz" vem vazio: no
     05/10 um clique em "Fiz" gravava o numero do plano por cima do que ja
     estava contado. As rodadas de geradas de antes desta decisao nao
     guardam a faixa, e nao entram no aviso.

## As fichas sem no, a falta de geradas e o texto-base (06/10/2026)

129. **as 15 fichas sem no ganharam no, com a sua aprovacao da lista.** Nove
     nos novos (origem `manual`, procedencia com o modelo e a aprovacao): cinco
     subassuntos da LEP pelos titulos e capitulos da Lei 7.210 (Objeto e
     classificacao do condenado; Trabalho do preso; Disciplina, faltas
     disciplinares e RDD; Sancoes, recompensas e procedimento disciplinar;
     Medida de seguranca, incidentes e procedimento judicial) e quatro de
     Portugues (Inferencia, pressupostos e subentendidos; Demais sinais de
     pontuacao; Emprego dos pronomes pessoais, demonstrativos e relativos;
     Complemento nominal e agente da passiva). As outras fichas foram para nos
     que a classificacao da decisao 106 ja tinha criado (Concordancia nominal,
     os dois de crase, Significacao das palavras, Especies de documentos
     oficiais, Conjugacao de verbos irregulares), e a Redacao oficial 1 ganhou
     "Conceito e atributos da redacao oficial", que nao tinha ficha. O
     elemento "LEP, art. 75" saiu de "Estabelecimentos penais" (Titulo IV) para
     "Orgaos da execucao penal", onde o artigo esta na lei (Titulo III, Cap.
     VI), pelo `radar conteudos --juntar`; "Estabelecimentos penais" ficou com
     a ficha dos arts. 82 a 104. A Interpretacao 1 (o metodo) ficou sem no de
     proposito: o assunto inteiro e o no da Interpretacao 6. A arvore foi de
     429 para 438 nos. Ligar a ficha mudou a classe de 5 temas de "nao contado"
     para "nao caiu nas 2 provas", e o no trouxe questoes do complementar a 6
     resumos: eles ganharam "o basico e isto" e o "como a banca cobra" com as
     questoes citadas (os 65 passam no `--verificar-resumos`).

131. **a falta de geradas das faixas de 06 a 12/10 foi escrita: 90 questoes em
     15 nos.** Pelo caminho de sempre (`pedido_de_questoes` e a importacao que
     confere), com os pedidos no scratchpad para o `data/pedido_ia.json` do
     art. 13 ficar intacto. Cada questao foi lida contra a fonte antes de
     entrar (a LEP pelo texto vigente da Camara, inclusive o art. 9º-A da Lei
     15.295/2025). Fato historico sem artigo nao passa na regra da fonte: as 8
     de "Afirmacao historica" foram reescritas sobre dispositivos (Declaracao
     de 1789, DUDH, Carta da ONU, Pactos, Viena). Junto, dois consertos: o
     formato de resposta de todo lote passou a pedir o `modelo` (so o de
     resumos pedia; 82 geradas e 10 explicacoes entraram sem ele e foram
     corrigidas para "Claude Code (claude-opus-5-5)"), e o enunciado igual
     conta como a mesma questao na importacao - "Um exemplo de tautologia e:"
     tres vezes virou uma.

132. **o texto-base da questao de interpretacao mora no banco, nas provas do
     alvo.** Coluna nova `questoes_de_prova.texto_base`, preenchida pelo passo
     6 da migracao (versao 6, com copia antes) e pelo `radar questoes
     --textos-base`: o caderno e lido de novo POR COLUNAS (a ordem do PDF pos
     o fim do Texto 2 de 2019 antes do cabecalho dele), o texto vai do
     "Texto N" ate a primeira questao (ou, na prova de texto unico de 2013, do
     titulo de Portugues ate a questao 1), e a questao de Portugues recebe o
     texto que cita ("texto 1", "textos 2 e 3"). So no banco, nunca num
     arquivo versionado: o texto e de terceiros (BBC, artigo academico). So
     a coluna muda: enunciado, chave e classificacao ficam. 15 questoes
     ganharam texto. Ele aparece na tela da questao, na questao inteira da
     ficha e no pedido da IA - e a questao que a IA tem de resolver (a
     explicada e a base da variacao) vai agora SEM o corte de 600 caracteres
     do exemplo de estilo, que levava metade das afirmativas de V/F. Com isso
     sairam 10 das 12 explicacoes que faltavam no alvo; as 2 de Direitos
     Humanos (2019-q28 e q38) continuam fora: a fonte delas e so doutrina, e a
     regra pede dispositivo.

133. **as questoes do complementar que os resumos citam ganharam explicacao:
     125 de 136.** O pedido e o `manual.pedido_de_explicacoes_dos_resumos`
     (`radar fichas --pedido --explicacoes --dos-resumos`): so a questao
     `FEPESE-` que algum resumo cita, inteira, com uma instrucao propria (a
     questao e de OUTRA prova da FEPESE, e nao do meu cargo); a importacao e
     a de sempre (a letra do gabarito oficial, a fonte com dispositivo em
     Direito). Ficaram 11 de fora, todas registradas na pendencia H: 6 citam
     o texto de uma prova do complementar, que o radar nao guarda (o texto-base
     da decisao 132 e so do alvo); 3 sao de Portugues numa materia que a regra
     da fonte trata como Direito ("Conhecimentos Especificos"); e 2 tem o
     gabarito discutivel (FEPESE-2023-q14, a colocacao depois de "cuja"; e a
     FEPESE-2024-q21, a probabilidade que ja estava na lista). As explicacoes
     foram de 80 para 205.

Junto, sem decisao nova: o `servico.fichas.levar_no` (o que o `--juntar` usa
para as fichas) deixava a ficha com um no e outro dentro dele quando o no
levado caia sob um no que ela ja tinha - foi o caso do art. 75, que a ficha
dos Orgaos passou a ter duas vezes. Agora fica so o de cima, como a conferencia
da ficha exige; o dado foi corrigido.

## O lote 1 da proposta de melhorias: o sabado que mede (06/10/2026)

A auditoria de uso de 06/10 (`docs/proposta_de_melhorias.md`) propos; voce
aprovou o lote 1, o que tem de estar pronto antes dos diagnosticos de 10/10.

134. **em 10/10 os diagnosticos abrem a manha e a noite** (I1). Manha:
     Diagnostico de Raciocinio Logico, Pausa, Principios de contagem, Revisao
     semanal; noite: Diagnostico de Portugues, Pausa, Simulado da semana,
     Correcao. O diagnostico de RL vinha depois de 50 min de teoria de
     contagem e de 60 de revisao semanal, e o de Portugues depois de 90 min
     de simulado: a linha de base que e comparada com 07/11 media o assunto
     recem-estudado e o cansaco. Revisa a decisao 105 so na posicao; o dia,
     o R+7 de 17/10 e a comparacao de 07/11 ficam. As rodadas ainda nao
     existiam, entao a composicao (a semente e a posicao da faixa) mudou sem
     perda nenhuma.

135. **dia que mede nao tem Plano B, e a Reduzida guarda a medicao** (P14).
     `servico.cronograma.faixas_que_medem`: o diagnostico e o simulado no
     radar (`composicao.mede`) e o R+7 que refaz os erros deles
     (`sabado.refaz_rodadas`). Com elas, o `ativar_plano_b` recusa e diz
     quais medem, e a tela troca o botao por "Hoje mede (...): sem Plano B.
     Se o dia apertar, faca so estas." Vale para 10/10, 17/10 e 07/11. O
     Plano B de sabado trocava o dia inteiro por "refazer as erradas" no
     Qconcursos e apagava a linha de base; ele nao podia so manter as faixas
     que medem, porque a rodada e reconhecida pela posicao no bloco do dia, e
     o Plano B e outro bloco. A Reduzida de 10/10 passou a "Faca so os dois
     diagnosticos no radar; o simulado da semana fica de fora", a de 17/10 a
     "Faca so o R+7 dos diagnosticos no radar...", e a Minima, a "ao menos um
     dos diagnosticos" e "ao menos o R+7 dos diagnosticos".

136. **as faixas que medem sem consulta nao tem botao de Resumo** (U02;
     revisa a decisao 120). O diagnostico e o simulado (tipos `diagnostico` e
     `simulado`, no radar ou no Qconcursos) sao cronometrados e sem consulta,
     e o resumo cita a questao real com a letra do gabarito: o botao a um
     clique desfazia o "sem consulta". O resumo continua na Correcao, no R+7
     (o dos diagnosticos tambem) e na ficha. De quebra, o 07/11 deixa de
     carregar os 65 resumos escondidos.

137. **a conferencia nao apaga mais o artigo nem o item do edital** (P06). O
     seletor "Corrigir para" vem no no atual, e o `classificacoes.conferir`
     chamava o `classificar` sem `dispositivo` e `item_do_edital`, que eram
     gravados vazios - no mesmo no, por cima da propria linha. Agora corrigir
     para o mesmo no e confirmar, e corrigir para outro no ou deixar pendente
     levam o artigo, o item do edital, o tipo e a pegadinha da classificacao
     antiga: sao da questao, e e o artigo que leva a pendente ao tema
     (decisao 108). Ja tinha acontecido em 05/10 com a chave `ae5ac356...`
     (2013 q2 do complementar): o valor antigo esta no commit `1bc222e`. Nao
     foi restaurado: fica com voce (pendencias, H).

Junto, sem decisao nova:
- **os textos do plano (I4 e I6).** A Correcao de 07/10 em diante (23 dias)
  diz "Antes de ler o comentario de cada erro, diga para si por que a certa e
  certa. No caderno de erros, UMA regra por tema que voce errou hoje", no
  lugar de copiar TODO erro; a de 10/10 manda ler a explicacao de cada erro
  dos diagnosticos e pedir as que faltam ate 16/10; o R+7 de 17/10 refaz cada
  erro antes de reler a explicacao e pede uma regra por assunto, e nao o
  motivo de cada um dos 40.
- **o 29/09 foi corrigido a seu pedido (P02).** Voce confirmou que as 10 de
  Portugues anotadas na faixa "Artigo, numeral e pronome" (10/2) eram as
  mesmas 10 da rodada 4 do radar. A faixa foi desmarcada e os 25 min viraram
  estudo extra "Onde: Radar", como no 05/10 (decisao 127). O 29/09 passou de
  37 para 27 questoes (2 acertos + 10 erros + 15 sem acerto anotado), a
  semana 1 de 68 para 58 (sem consulta 15 de 33, 45%), Portugues sem
  consulta de 13 de 35 para 11 de 25, e a projecao de ~6 para ~7. O registro
  do dia (37/4) e a copia guardada da 1D e nao aparece. Copia antes em
  `data/copias/correcao-2026-09-29-101355/`.
- **o 28/09 (P08) fica como esta.** Voce nao sabe dizer se as 10 foram do
  Qconcursos ou as geradas da rodada 2, e a decisao 3 da Etapa 0 registrou
  Qconcursos: sem evidencia, o dado nao se reescreve (regra inviolavel 9).
- **as 5 fichas dos temas ja estudados foram conferidas por voce** (I5):
  Aplicacao da lei penal; Art. 5o, caput e incisos I a XVI; Fato tipico e
  nexo causal; Substantivo e adjetivo; Artigo, numeral e pronome. Pela
  decisao 81, as faixas desses temas passam a contar para o "estudado" e as
  datas de revisao (nunca para o acerto): os nos estudados ou praticados
  foram de 16 (todos de Portugues) para 31, e a fila de revisao da home de 8
  para 17 pontas, ja com Penal e Constitucional (era o P09).

## O lote 2 da proposta: o "fiz" e o "Fiz hoje" (06/10/2026)

O caso: em 06/10 a tela mostrou "Fiz hoje: 5 questões" antes de eu fazer
questao real, e "24" depois de 12 geradas. O 5 era o meio do treino de IA
(entre a 5a e a 6a resposta, 10:43 a 10:45), somado na mesma linha das
reais; o 24 eram as 12 geradas contadas duas vezes, porque o "fiz" da faixa
Fixacao veio com numero e eu anotei nele o treino (12/11). O servidor estava
no ar desde 00:21, antes da decisao 130, e nao mostrou o aviso. Corrigido o
dia como o 29/09: a faixa desmarcada, e os 16 min do treino (10:38 a 10:54)
viraram estudo extra "Onde: Radar". Copia antes em
`data/copias/correcao-2026-10-06-111005/`.

138. **as reais e o treino de IA em linhas proprias, e o "fiz" so do que eu
     fiz fora do radar** (P03, U03; muda o texto da decisao 127 e a regra 1
     da 1D, estende a 130). Quatro partes, aprovadas por voce:
     - o "Fiz hoje" virou tres linhas, na tela e no `radar hoje`:
       "Questões reais (Qconcursos e provas): N" (`metricas.frase_das_reais`
       sobre o `Conta.reais`, o anotado mais o respondido no radar), "Treino
       de IA no radar: N = a + e (x%), não entra no acerto" e "Total do dia: N
       questões · tempo". O treino continua no volume do total (decisao 127);
       so nao divide mais a linha com as reais;
     - o campo da faixa se chama "fiz no Qconcursos" (ou "fiz fora do
       radar", na faixa que nao e do Qconcursos) e vem SEMPRE vazio; o numero
       do plano fica so de dica, no placeholder. Era ele que virava "fiz" com
       um clique;
     - a faixa feita no radar fecha com o "fiz" vazio: o check guarda 0
       questoes, o tempo da faixa e `no_radar`, e a faixa mostra "feita no
       radar". So vale com resposta numa rodada aberta pelo botao da faixa
       (`metricas.no_radar_por_faixa`); sem ela, o vazio continua recusado.
       A conferencia nao chama essa faixa de "feita com 0 questoes". O aviso
       da faixa diz "Você treinou N de IA nesta faixa (a de N): já contam no
       Treino de IA" e "se fez só no radar, deixe vazio e marque ✓";
     - o sinal de treino do tema: "Treino de IA neste tema: a de N (x%) · não
       entra no acerto", na faixa de treino e na ficha. E toda resposta a
       gerada dos nos do tema, de qualquer dia (`metricas.treino_ia_dos_nos`),
       nunca somada ao acerto do tema.

## O "Treinar geral no radar" da faixa (06/10/2026)

139. **cada faixa de questoes ganhou um "Treinar geral no radar", ao lado
     dos botoes de cada no** (pedido seu; os de cada no ficam como estao). O
     geral junta TODOS os nos da faixa numa rodada so de geradas, embaralhada,
     para eu nao saber de qual assunto vem a proxima, e a quantidade e minha
     (o campo vem com as questoes do plano, sem passar das geradas dos nos
     nem de 30). O sorteio (`geradas._sortear_misturado`) divide por igual
     entre os nos, um de cada ate completar, e so depois embaralha: o
     sorteio puro numa lista so traria quase tudo do no com mais geradas. O
     no que acaba passa a vez aos outros, e um no dentro do outro nao repete
     questao. A rodada guarda os nos (`conteudos`) e a faixa (`da_faixa`, como
     a do botao do no, decisao 130): conta sozinha no aviso da faixa e no
     treino de IA, nunca no acerto. O botao so aparece com 2 nos ou mais COM
     gerada (`GeradasDaFaixa.geral`): com um so, seria o mesmo botao do no.
     Aparece em todo dia do plano, como os outros. No 06/10, a faixa do Art.
     5º, incisos XVII a XLIX, ainda nao o mostra: 3 dos 4 nos dela estao sem
     gerada.

## O link do Qconcursos de cada tema (06/10/2026)

140. **a faixa que manda ao Qconcursos abre o filtro pronto, com os assuntos
     do proprio site** (pedido seu). O filtro escrito no plano ("Direito
     Constitucional > direitos e deveres individuais e coletivos") nao existe
     no site, e o mais proximo trazia o art. 5º inteiro, com o que eu nao tinha
     estudado. O radar NAO consulta o Qconcursos (os termos proibem raspagem):
     voce copiou do site, uma vez, a lista de assuntos de cada disciplina (F12
     > Elements > `<ul class="q-options">`, cada assunto com o numero), e os
     temas foram casados aos assuntos a partir dela - o casamento aprovado por
     voce. Ele mora no `config/qconcursos.yml` (62 temas: o tema, a
     disciplina, os numeros com o nome do site e, quando o assunto do site e
     mais largo que o tema, o `aviso` do que pular); o `radar/qconcursos.py`
     so le e monta o endereco no formato que o site gera (a banca 61, a
     FEPESE; sem anuladas nem desatualizadas; um `subject_ids[]` por
     assunto). O tema e reconhecido pelo titulo da faixa sem o prefixo, como a
     ficha, entao o R+7 ganha o link do tema; so a faixa com `onde:
     qconcursos`. A faixa troca o "Filtro:" pelo botao "Abrir no Qconcursos",
     com os assuntos e o aviso, e o simulado do Qconcursos ganha o link de cada
     tema; sem link, fica o filtro escrito, como era. Fica largo, e a faixa
     avisa: a LEP (um assunto so no site, o 40.3, dentro do Direito Penal), as
     Regras de Mandela (um so, o 5.8), a concordancia verbal e nominal (um
     so) e a crase. Sem assunto: as 2 faixas de Redacao oficial (falta a lista
     dessa disciplina). As listas de Administracao Publica, Processo Penal,
     Sociologia e Legislacao Estadual ficam para o Ciclo 2.

## A aba Acompanhando por carreira (06/10/2026)

141. **a aba Concursos > Acompanhando ganhou um cartao por CARREIRA, acima
     dos favoritos** (pedido seu, feito nesta sessao). O favorito e UM item
     da coleta; a carreira existe antes de qualquer noticia e junta sozinha o
     que a coleta trouxer dela. A lista mora no `config/acompanhamentos.yml`
     (Policia Penal SC, Guarda Municipal de Florianopolis e de Balneario
     Camboriu, Policia Civil SC, PM SC - soldado e oficial -, Oficial do
     Corpo de Bombeiros SC e Bombeiro Militar SC), e cada uma aponta um bloco
     do `config/alvo.yml` pelo nome: os termos sao os de la, mais os
     `termos_extras` ("PC SC", "CBMSC"), a cidade (`local`, com a sigla da
     FEPESE: "PMBC", "PMF") e o estado (`uf: SC`; sem UF, vale o anel, a
     FEPESE ou "santa catarina" no texto; UF de outro estado tira o item). A
     Policia Penal usa a marca `principal` que o classificador ja da. A **PM
     entrou no alvo.yml** como bloco secundario, no fim (os Bombeiros casam
     antes; "PM" sozinha nao, porque e Prefeitura Municipal na FEPESE). As
     regras de precisao:
     - **a situacao e os marcos** (banca, edital, inscricoes, prova) saem do
       item mais recente que e concurso, dentro de 12 meses e sem ano velho
       no titulo ("2019 – ..." republicado em 2024 nao conta). Sem ele, o
       cartao diz "nenhum concurso desta carreira no radar nos ultimos 12
       meses" e os marcos ficam "aguardando" - hoje, com o dado real, os 7;
     - **o 🔔 e so FATO**: o evento da linha do tempo (apareceu, mudou de
       situacao, edital, inscricao, prova, retificacao) de item que nao e
       noticia, um por link, depois da data `novidades_desde` e do meu
       "Marcar como visto"; ou a pesquisa do Claude Code confirmada.
       Noticia vai para o historico (num `<details>`, fechado);
     - **o selo diz de onde veio**: 🟢 a propria banca (FEPESE, IESES), 🟡 o
       site de noticias (selo novo `noticia`, da familia automatica, no
       `radar/origem.py`), 🟣 a pesquisa;
     - **o botao "Verificar atualizacoes"** roda a mesma coleta do `radar
       atualizar` (as fontes permitidas e a leitura das paginas novas), numa
       thread, sem Telegram; a pagina se recarrega com `<meta refresh>`
       (HTML, nao JS) enquanto roda, e o botao espera 30 minutos entre um
       clique e outro (`intervalo_minimo_minutos`). Busca aberta na internet
       ficou fora: raspar buscador fere o robots e os termos (CLAUDE.md) e
       traz justamente o rumor e a noticia velha;
     - **a pesquisa do Claude Code** e o caminho do que o robo nao ve
       (comissao, autorizacao, jornal): `radar acompanhar --pedido` ->
       Claude Code do VS Code -> `radar acompanhar --importar`, pelo mesmo
       `manual.importar` (tipo `novidades`). Recusa sem link, sem data, data
       futura, fato de mais de 12 meses, marco fora da lista, e ignora o que
       o radar ja sabe; texto de previsao vira "nao confirmado" (nao acende o
       🔔, nao se confere, nao preenche marco). O que entra fica 🟣 "por
       conferir" em `data/acompanhamentos.json` (versionado, no sincronizar)
       e so preenche marco depois do meu "Confere". **Nunca muda a situacao
       de um concurso no banco**;
     - **o Telegram so avisa o critico** das carreiras: banca contratada,
       edital publicado, inscricoes abertas, prova marcada e retificacao, de
       item que nao e noticia, a partir de `telegram_desde` e dos ultimos 30
       dias, pelo mesmo `avisado_em` do favorito (sai uma vez so). Roda no
       `radar avisar` do Actions, depois do favorito e antes do concurso novo.

## A correcao na hora, as geradas nunca feitas e a nota da faixa (07/10/2026)

142. **tres pedidos seus de 07/10, fora dos lotes da proposta de melhorias**
     (a regra "ate 07/11 so o que corrige numero ou prepara o sabado" ficou
     de lado a seu pedido, para estes tres). Banco na versao 7: o passo 7
     cria `respostas_de_simulado.chutou` e `estados_do_dia.notas_das_faixas`,
     as duas nulas nas linhas antigas.
     - **a correcao na hora, no treino.** Depois da letra, a tela da questao
       volta com ela corrigida (`/simulado/{id}?ver={questao}`): a marcada
       em vermelho, a certa em verde, a explicacao e os macetes que o
       relatorio do fim ja mostrava, o "Proxima ->" (ou "Ver o resultado")
       e, no erro, "Anotar no caderno de erros" com materia, assunto, fonte
       (radar), referencia e o motivo "chutei" ja preenchidos. Em cima, uma
       bolinha por questao (verde, vermelha, vazia), os acertos e "🔥 N
       seguidas" a partir de 3. A letra nao muda depois (o servico ja recusava
       a segunda). Sem JavaScript: um formulario so, com a letra no botao.
       **A rodada que mede nao corrige na hora** (`simulado.RODADAS_QUE_MEDEM`:
       "composta" - diagnostico e simulado no radar - e "erros_das_rodadas",
       o R+7): la o `ver` e ignorado e a bolinha da respondida fica cinza; o
       certo e o errado so no relatorio, como na prova.
     - **o "vou no chute"**, marcado ANTES da letra (marcar depois de ver o
       resultado seria marcar so quando erro), em toda rodada, inclusive a
       que mede. Fica em `chutou`, ao lado do acerto e nunca dentro: o
       resumo da rodada ganha `chutes` e `acertos_no_chute`, o relatorio diz
       "🎲 N no chute", a faixa diz os chutes do que respondi no radar por
       ela (`Numeros.chutes`, que nao entra em `questoes` nem no acerto). A
       resposta antiga fica nula ("nao se sabe", e nao "nao"); o backup so
       leva a chave quando ha valor.
     - **as geradas nunca feitas primeiro.** O sorteio (`geradas._sortear`,
       e por ele o "Treinar geral") poe na frente as que eu nunca respondi;
       acabadas, repete a errada da ultima vez antes da acertada, e a mais
       antiga antes da mais nova (`metricas.ultimas_das_geradas`). A faixa
       diz "voce ja fez X" (geradas DIFERENTES, `metricas.geradas_feitas_por_no`)
       e, com metade feita, "Voce ja tem metade das questoes feitas: vamos
       fazer mais algumas"; com todas, "Voce ja fez todas as questoes deste
       tema: esta na hora de criar mais" - **e nos dois casos os 3 passos de
       gerar vem junto** (o no que tinha o bastante passa a pedir a cota, no
       minimo 5). O relatorio da rodada de geradas mostra o mesmo, por no.
       A tela de gerar (`nos_do_cronograma`) continua contando so o estoque.
     - **a nota da faixa ("📝 Como foi")**, em toda faixa da tela Hoje que
       nao e pausa nem do futuro: quantas chutei fora do radar (so na faixa de
       questoes, como o "fiz"), "entendi o assunto?" (sim, mais ou menos,
       nao) e a nota livre (2000 caracteres). Mora em
       `estados_do_dia.notas_das_faixas`, FORA do `faixas_feitas`: escrevo
       antes ou depois de marcar, e desmarcar nao apaga; tudo vazio tira.
       Reconhecida por bloco + indice + titulo, como o check. E diario, como
       o caderno de erros: nao entra em acerto nenhum. O servico e o
       `servico/notas_da_faixa.py`; a ficha do tema ("Como eu disse que fui")
       e o Meu desempenho ("Como eu disse que fui (para o Ciclo 2)") releem,
       por tema, com o que eu ainda nao entendi (ou entendi mais ou menos) na
       frente, marcado "fica no Ciclo 2". Vai no `data/estado_do_dia.json`
       so nos dias que tem nota.
