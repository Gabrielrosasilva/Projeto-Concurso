# CLAUDE.md
Contexto permanente deste projeto, lido pelo Claude Code em toda sessao aberta
nesta pasta. Curto de proposito. O que nao cabe aqui:

- **[docs/novo.md](docs/novo.md)** — é o pedido: o que você quer que o sistema faça e as regras que não podem ser quebradas;
- **[docs/roteiro.md](docs/roteiro.md)** — plano e os critérios de cada etapa;
- **[docs/progresso.md](docs/progresso.md)** — como cada etapa andou: situação,
  arquivos, testes e o critério de conclusão marcado;
- **[docs/decisoes.md](docs/decisoes.md)** — decisoes ja tomadas, com o motivo;
  nao se rediscutem. **Decisao que mudar, atualize la.**
- **[docs/pendencias.md](docs/pendencias.md)** — o que falta, o que esta
  quebrado e o que ficou combinado. **Leia antes de propor etapa.**
- **[docs/especificacao.md](docs/especificacao.md)** — o redesign; leia antes de
  mexer em tela ou em dado de estudo. **[docs/historico.md](docs/historico.md)**
  — como cada fase foi feita. **[README.md](README.md)** — instalar e usar.

## O que e

Sistema **pessoal** (um unico usuario) para acompanhar concursos publicos que
valem a pena para mim. Nao e produto, nao tem login, nao vai para producao
(a nuvem com login e dois perfis esta so planejada: decisao 126).
Prioridade: funcionar e ser facil de manter sozinho.

## Quem mantem

Analista de infraestrutura/SRE. Domino Linux, Docker, Kubernetes, Terraform,
GitLab CI, GitHub Actions, AWS e OCI, shell script, SQL e Java. **Nao tenho
pratica em Python** — e a linguagem escolhida aqui justamente para aprender.
Por causa disso:
- prefira o jeito simples e legivel ao esperto, e a biblioteca padrao quando a
  diferenca for pequena;
- nao introduza abstracao sem necessidade concreta; comentario explica **por
  que**, nao o que a linha faz.

Comentarios, commits, texto de interface e nomes de variaveis, funcoes e
arquivos: em **portugues** — o codigo ja segue isso.

## O que eu procuro num concurso

**O alvo principal e Policia Penal SC.** Para ele o cargo manda e a distancia
nao importa: e concurso estadual, e eu presto onde for. **A de outro estado
tambem avisa, e so avisa** (marca `principal_fora`): o **estudo** — Meu foco,
incidencia, treino, acervo — le so as provas de SC, porque fora daqui e outra
banca e outra lei estadual. **A excecao e o meu acerto** (decisao 166): a
questao de outra banca treina no radar e mede o meu desempenho no no, com a
origem ao lado, e nunca entra no que a FEPESE cobra.

Depois dele, nesta ordem: Guarda Municipal · Policia Civil · Oficial de
Bombeiros · e as demais carreiras de seguranca publica (Policia Penal Federal,
Bombeiro Militar, Policia Cientifica). **A lista ordena, nao descarta** —
nenhum concurso sai do radar por nao estar nela. Ela mora em
`config/alvo.yml`, nunca no codigo; bater no alvo principal fura o filtro de
distancia e o teto de avisos, e vale ate para noticia. A lista `de_olho` do
mesmo arquivo fura o teto e ganha cartao na tela Analises > Edital para a
**Guarda Municipal de Florianopolis e de Balneario Camboriu**, sem virar alvo
nem entrar no estudo.

Para todo o resto continuam valendo os criterios de sempre, nesta ordem:

1. **Onde a prova e aplicada.** Grande Florianopolis ou perto. Fora do alvo,
   este e o filtro principal; o cargo e secundario.
2. **Se eu posso prestar.** Superior em Sistemas de Informacao. Muitos cargos
   pedem "superior em qualquer area" — esses servem.
3. **Salario.** Acima de R$ 5.000 e o alvo. Nao e corte: abaixo disso continua
   aparecendo, so mais embaixo no ranking.

Consequencia pratica disso, e e importante: as materias que interessam sao as
de **carreira policial e seguranca publica** — Direito Constitucional, Penal,
Processo Penal, Administrativo, Legislacao Especial, Direitos Humanos,
Portugues, Raciocinio Logico, Atualidades. **Nao** e TI.

E as bancas que importam nao sao as nacionais de sempre. Em SC o peso esta em
**FEPESE**, ACAFE, IESES, FURB, Instituto o Barriga Verde, e nas de seguranca
publica (IBFC, Instituto AOCP, FUNDATEC, Consulplan, e o Cebraspe nas
federais). Qual banca fez qual concurso e coisa para **confirmar lendo o
edital**, nunca para afirmar de memoria.

## Regra de relevancia geografica

Tres aneis, configurados em `config/regioes.yml` (nunca fixos no codigo):

1. **nucleo** — Regiao Metropolitana da Grande Florianopolis.
2. **proximo** — Itajai, Balneario Camboriu, Brusque, Tubarao, Laguna,
   Imbituba, Blumenau, Lages e vizinhos. Blumenau (~2h) e Lages (~3h) estao
   aqui por escolha minha, nao por tempo de estrada.
3. **remoto** — qualquer outro lugar. So interessa se o edital disser que ha
   prova em Florianopolis.

Como decidir o anel, em ordem de confianca:

- **concurso de SC**: pelo municipio do orgao, extraido do titulo/resumo;
- **federal ou de outro estado**: so pelo texto do edital em PDF, procurando as
  cidades de aplicacao. Sem edital lido, fica `indefinida` — **nunca chute**;
- guarde sempre *por que* foi classificado assim, em `motivo_relevancia`:
  eu preciso poder auditar a decisao.

Concurso irrelevante **nao e apagado**: fica marcado, para eu corrigir a regra.

## Ciclo de vida do concurso

O radar acompanha desde antes do edital. Campo `situacao`: `prevista` →
`autorizado` → `banca_definida` → `edital_publicado` → `inscricoes_abertas` →
`encerrado`. `banca_definida` e o sinal mais valioso: a contratacao da banca
sai **2 a 4 meses antes do edital**, e da tempo de estudar o padrao dela.

## Estado atual (18/10/2026; detalhe no [historico](docs/historico.md))

**Pronto:** o radar (fases 1-15), a especificacao e o **Ciclo 1 de estudo,
rodando desde 28/09** (`config/cronograma.yml`: tela Hoje - o cronometro e a
dobra dos blocos sao os dois unicos JS, so nesta tela e dispensaveis -,
caderno de erros, Semanas, Minhas materias; automacao no Windows). E o
**pedido de evolucao** ([roteiro](docs/roteiro.md),
[progresso](docs/progresso.md)), etapas 1A a 8: a fonte unica das metricas, a
arvore de conteudos (materia > assunto > subassunto > elemento) com alvo,
complementar e fora separados, a incidencia e os padroes, o desempenho por
conteudo com a amostra, a geracao com escopo fechado, a ficha de estudo de
cada tema (65 em `data/fichas.json`), os selos do novo.md (🟢 oficial, 🔵
acervo, 🟡 automatico, 🟣 IA) gravados no dado, e o site inteiro no design
system. A **auditoria final** ([auditoria_final](docs/auditoria_final.md))
confere a §23 do novo.md: **19 de 19 itens atendem com o dado real** (o 18,
a media "por prova" dos Macetes, foi corrigido no lote de 04/10).
**Correcoes depois da auditoria (03/10, decisoes 63 a 66):** o "Onde estudar
primeiro" nao soma mais o alvo e o complementar; o backup das 23h30, que
falhava desde 27/09, roda com a pasta suja; a lista de leis alteradas depois
das provas existe (15 itens, 17 questoes, por conferir:
[leis_alteradas](docs/leis_alteradas.md)); e os docs foram revistos. **O ciclo
especifico (pedido de 03/10):** feitas a 2A - o diagnostico e o simulado de
07/11 mostram de quais assuntos e subassuntos sao as questoes e criam a rodada
com essa composicao (decisao 67) - e a 2B - o simulado do Qconcursos sem
numero escrito a mao, a revisao semanal, o R+7 dos diagnosticos e a
comparacao de 07/11 (decisoes 69 e 70) - e a 2C - cada faixa diz o assunto, o
subassunto e o elemento (decisao 71). A **secao F** (o Pedido 1) esta inteira,
F1 a F15 (decisoes 74 a 86): o "Onde estudar primeiro" e a revisao espacada
pela arvore, so o complementar aceito no costume e no treino, a base da gerada
pela chave, os padroes do complementar, a ultima revisao e a evolucao no Meu
desempenho, o painel mais leve, a faixa sem `conteudo` no que cobre, a
revisao feita passando o 1-7-30, os termos empatados em ordem, as variacoes
religadas, os ultimos minimos no `config/amostra.yml`, as leis de fronteira
na ficha, os conceitos associados e o 1-7-30 da primeira resposta.
**O lote de 04/10 (decisoes 87 a 90):** as 61 fichas e as 15 leis lidas contra
a fonte (15 fichas corrigidas: [conferencia_das_fichas](docs/conferencia_das_fichas.md));
a tela de conferencia do complementar, com a amostra do catalogo - que
reprovou o lote, refeito pelo Claude Code; o `?cor=` no lugar do `?tema=` da
cor; as geradas antigas com materia e no (7 erradas fora do sorteio); a base
da media nos Macetes; e o leitor do caderno consertado (o lixo no fim da
alternativa, a palavra partida, a numeracao, a ordem das secoes) com o acervo
relido e as 21 provas que o download nunca tinha baixado.
**Depois do lote (04/10, decisoes 91 a 95):** o /geradas treina pelo no
(materia, assunto ou subassunto), e a ficha manda direto para os do tema; 40
macetes e 6 explicacoes escritos contra o texto vigente; acento no terminal,
no Telegram, na auditoria e no motivo de elegibilidade (a descricao dos
comandos, os valores digitados e as chaves ficam sem); a conferencia dos
conceitos associados na Analises > Conferencia; e o leitor entende o
texto-base compartilhado ("Caso 3") e a marca "square" minuscula - os 3
cadernos que sobravam fecharam, e o acervo foi relido.
Acervo: 8.462 questoes (as 170 do alvo classificadas e conferidas; 172
provas complementares aceitas); 1.709 geradas (10 rejeitadas), as aceitas
todas com nivel; 214 explicacoes; arvore com 438 nos; banco na versao 8 (9 desde 18/10, decisao 174).
**A auditoria independente de 04/10** ([auditoria_independente](docs/auditoria_independente.md)):
186 requisitos e 8 defeitos, todos consertados nas Rodadas 1 a 4 (decisoes 96
a 103); sobra a 2013-q53, so com voce (pendencia G). **O pedido de 05/10**
(decisoes 104 a 107): a reanalise as cegas do complementar, os diagnosticos
passados para 10/10 (R+7 de todos os erros em 17/10; a comparacao de 07/11
contra 10/10), Portugues e Raciocinio classificados, e a faixa de Portugues
que comeca pelas questoes do radar.
**A revisao final do estudo (05/10, decisoes 108 a 126):** o "caiu ou nao
caiu" de cada tema, prova a prova, com as pendentes e o artigo gravado; a
questao real inteira, a explicacao e os macetes na ficha; a aba Fichas por
dia; a faixa de questoes que diz o no, manda ao Qconcursos e da os 3 passos
para gerar (pelo `.venv\Scripts\radar.exe`); 14 trechos de 7 fichas
corrigidos (Mandela pela letra do CNJ); o RESUMO dos 65 temas no botao de toda
faixa (janela so com CSS) e 64 explicacoes das questoes reais do alvo; o
Ciclo 1 redistribuido pela classe de cada tema em 7 dias (minutos iguais); o
saldo do estoque de geradas (sob demanda); e os docs com o
[indice](docs/indice.md). A procedencia de texto de IA novo diz o modelo.
**Os itens 8, 2, 3, 4 e 5 (06/10, decisoes 128 a 133):** uma fila de revisao
so (a home mostra as pontas da do Meu desempenho, e o prazo acaba na de 30
dias); as 15 fichas sem no ligadas (9 nos novos, aprovados por voce; o art.
75 no lugar dele); a falta de geradas de 06 a 12/10 escrita (90); o
texto-base das questoes de interpretacao do alvo no banco (`texto_base`, lido
por colunas; na tela, na ficha e no pedido, sem corte); e 125 explicacoes das
questoes do complementar que os resumos citam (+10 do alvo). Rodados so os
testes tocados, a seu pedido. A decisao 127 (o treino de IA no "Fiz hoje")
e a 130 (a faixa avisa o que ja foi respondido no radar) vieram de outra
conversa.
**A auditoria de uso de 06/10** ([proposta_de_melhorias](docs/proposta_de_melhorias.md),
so leitura): 57 problemas de precisao (8 criticos), 64 melhorias e 9 ideias,
com codigos P, U e I. Voce aprovou a ordem: **ate 07/11 so entra o que
corrige numero ou prepara os sabados que medem** (I3). Feito o **lote 1**
(decisoes 134 a 137): os diagnosticos abrem o 10/10, o dia que mede nao tem
Plano B, o Resumo saiu das faixas que medem, a Conferencia nao apaga mais o
artigo; e o 29/09 corrigido (37 para 27 questoes) e 5 fichas conferidas.
Fora dos lotes, a seu pedido, cada faixa ganhou o **"Treinar geral no
radar"** (decisao 139): as geradas de todos os nos dela, divididas por igual e
embaralhadas, com a quantidade sua; e o **"Abrir no Qconcursos"** (decisao
140): a faixa abre o filtro pronto, com os assuntos do proprio site
(`config/qconcursos.yml`, tirado das listas que voce copiou; o radar nao
consulta o site), e avisa quando o site e mais largo que o tema. E o **lote 2** (decisao 138): o "Fiz
hoje" virou tres linhas - as questoes reais (Qconcursos e provas), o treino
de IA e o total -, o "fiz no Qconcursos" da faixa vem sempre vazio, a faixa
feita no radar fecha com o ✓ vazio guardando so o tempo, e a faixa e a ficha
mostram o "Treino de IA neste tema". O 06/10 foi corrigido (as 12 geradas
estavam anotadas de novo na Fixacao).
**Falta, de voce:** conferir as outras 60 fichas, os 65 resumos e as 30
traducoes dos artigos (pendencia M) (a ficha conferida
tambem liga as faixas do tema ao Meu desempenho, decisao 81); as
classificacoes abertas e pendentes do complementar (lista unica em
[conferir_classificacoes](docs/conferir_classificacoes.md)), os 109 conceitos
associados e os itens da lista de leis; os pontos da pendencia H (gabaritos a
olhar, os 9 nos novos ao conferir as fichas); e o **Ciclo 2**, depois do simulado de 07/11 e antes de
09/11, ja com as fichas, os resumos e as explicacoes dos temas novos
(decisao 123).
**A aba Acompanhando por carreira (06/10, decisao 141):** um cartao por
carreira do `config/acompanhamentos.yml` (Policia Penal SC, Guardas de
Florianopolis e BC, Policia Civil, PM e Bombeiros de SC; a PM entrou no
`alvo.yml`), com situacao, marcos, 🔔 so de fato, "visto", o botao
"Verificar atualizacoes" (a coleta agora, em thread) e a pesquisa do Claude
Code (`radar acompanhar --pedido/--importar`, 🟣 por conferir, em
`data/acompanhamentos.json`, nunca no banco); o Telegram so no critico. O que
falta: pendencia J.
**Os tres pedidos de 07/10 (decisao 142):** no treino a questao volta
corrigida depois da letra, com a explicacao, o "Proxima" e as bolinhas (a
rodada que mede continua so no fim); o "vou no chute" antes da letra, ao lado
do acerto e nunca dentro; as geradas nunca feitas saem primeiro, e a faixa
avisa com metade e com todas feitas, ja com os 3 passos; e o "📝 Como foi" de
cada faixa (chutes fora do radar, entendi, nota), relido na ficha e no Meu
desempenho para o Ciclo 2.
**O lote 3 da proposta (09/10, decisoes 143 e 144):** o R+7 e o R+30 com
"+ 3 de Portugues" viraram duas faixas no plano (31, de 08/10 em diante; o
07/10, ja anotado, ficou como era), e o erro anotado chega ligado ao no -
cada erro do relatorio da rodada com o no da questao, a faixa com o no que
voce deu (`conteudo`, `nos`, ficha conferida) -, com a faixa mista
(Diagnosticos) sem materia.
**O lote 4 da proposta (09/10, decisoes 145 a 150):** a rodada que mede nao
repete a questao de outra do ciclo (o fechamento de 07/11 repetiria 19 das
40 de 10/10); o que decide o Ciclo 2 e o acumulado do ciclo, com o
fechamento ao lado; o anotado sem `conteudo` conta no no da MATERIA (uma
regra so em toda tela; "sem acerto medido"); a letra do gabarito, a
explicacao e a pegadinha da questao so aparecem depois de responder no
radar; o "caiu" diz a base pequena e as notas na faixa, e a prioridade baixa
foi para o "Por que agora"; a seta do acerto nas Semanas so com 20 respostas
de cada lado. **A proposta de melhorias esta feita ate 07/11.**
**O nivel das geradas (09/10, decisao 151, a seu pedido e fora dos lotes):**
toda gerada tem um nivel - facil, media ou dificil -, o que a IA declara, com
o porque e a procedencia (`nivel`, `por_que_o_nivel`, `nivel_procedencia`,
`suspeita`; banco na versao 8). Os criterios moram no `radar/niveis.py`. O
`radar gerar --pedido` leva o `--nivel misturada|facil|media|dificil`
(misturada: partes iguais, a sobra na media, 10 = 3/4/3), e a importacao
recusa a questao sem nivel ou sem o porque e conta a mistura ("pedi 3/4/3,
veio 5/3/2") sem completar; a `comando_de_gerar` escreve o `--nivel` em todo
lugar, e o topo da tela Gerar questoes da os 3 passos sem API. No treino, um
nivel so traz as daquele nivel e nunca completa com outro ("so havia 2
dificeis neste assunto", com os 3 passos daquele nivel); a misturada traz
todas. A questao diz "🟣 Gerada por IA · Dificil" (o porque so depois de
responder), e o resultado da rodada tem o acerto por nivel, a parte. As 911
antigas foram classificadas pelo `radar gerar --pedido --classificar-nivel`
(478 faceis, 364 medias, 69 dificeis), com 8 suspeitas so listadas, por
conferir (pendencia K).
**O numero do treino de IA honesto (10/10, decisao 152; cabe na I3: corrige
um numero):** o NIVEL do treino de IA (a faixa, a ficha, Minhas materias, o
Simulado, a tela de gerar e o "Por nivel" da rodada) conta so a 1a resposta
de cada gerada, e refazer vira REVISAO, ao lado; o VOLUME (o "Fiz hoje", as
Semanas, a Conferencia) continua contando toda resposta. O chute fica ao lado
no "firme", a variacao e o do zero saem separados, e abaixo do minimo da
secao nova `treino_ia` do `config/amostra.yml` (10/15/10/30) o numero diz
"Amostra insuficiente". Uma conta so, `metricas.treino_ia_dos_nos` e
`treino_ia_por_materia`; nada disto entra no acerto das reais.
**As fontes oficiais novas (11/10, decisoes 153 e 154; os 7 sites
investigados de uma vez):** o robo roda as 05:17 e a reserva as 08:47, parte
da ponta do branch (sem repetir aviso) e commita o manifesto `provas.json`
(a retificacao nao e mais avisada todo dia); e o Diario Oficial do Estado e a
fonte 4 (`collectors/doe_sc.py`, pela busca POST da tela): o contrato ou a
dispensa da banca, a autorizacao, a comissao e o edital das carreiras do
`config/alvo.yml`. A carga de um ano (`radar carga-inicial --fonte doe_sc`)
trouxe 17 atos, entre eles o contrato da PM SC com o Instituto AOCP (o cartao
da PM diz "Banca: Instituto AOCP 🟢"). Depois, no mesmo dia (decisoes 155 a
159): o Instituto AOCP (`aocp`, os abertos e em andamento, ligado pela
`carga-inicial --fonte aocp` para nao avisar o que ja havia), as noticias da
Prefeitura de BC (`prefeitura_bc`, o anuncio do concurso da Guarda no cartao
de BC), os editais da SEJURI (`sejuri`) e o IDIB (`idib`, o CFO e o CFP do
CBMSC no cartao dos Bombeiros, pelo `cbmsc` do `prova_de_sc`). O Idecan e a
Prefeitura de Florianopolis ficaram fora, so registrados. O radar tem 8
fontes. E, aprovada por voce, a decisao 160 (muda a 141): a situacao e os
marcos do cartao olham a edicao inteira - cada marco do item mais novo que o
sabe -, e os Bombeiros passaram a "edital publicado" com Banca IDIB. Em
12/10, aprovadas por voce: o edital de ABERTURA do DOE entra como "edital
publicado" e a carga inicial marca tambem os eventos da fonte (decisao 162;
a PC SC mostra o edital de 12/12/2025); o 🔔 so acende para item da edicao de
agora (163; a Policia Penal perdeu os sinos dos editais de 2006 a 2022); e o
termo do cartao aceita "todas as partes" - `cbmsc + formacao de oficiais`
poe o CFO do CBMSC no cartao do Oficial de Bombeiros (164).
**O resumo enxuto e o "🗣 Traduz pra mim" (12/10, decisao 161, a seu pedido e
fora dos lotes; nao mexe em numero):** na janela e na ficha, os artigos
abertos, um bloco por artigo (as frases que citam so ele, pela fonte), o
basico, as 3 pegadinhas que mais derrubam e o resto dobrado; o link da Noite
cai em "Como a banca cobra" aberta. Nas fichas de lei, cada bloco tem a
traducao (na real, exemplo, na prova; 🟣), o tema tem o "⚖️ Nao confunda" e a
1a vez de cada palavra do `data/glossario.json` fica sublinhada, com o
significado no `:hover`/`:focus`, sem JS (so nas materias de lei). O jeito de
escrever mora no `config/linguagem.yml`; a traducao, na ficha (`traducao`),
com procedencia e "✓ Conferi a traducao" proprios: `radar fichas --pedido
--traducoes [--tema] [--materia] [--refazer]`. Traduzidas as 30 fichas de lei:
200 artigos, 130 linhas de "nao confunda", 215 termos (pendencia M); o artigo
com bloco proprio no resumo conta como do tema (`servico.fichas.artigos_do_tema`).
**A crase do jeito da banca (13/10, decisao 165, a seu pedido e fora dos
lotes; nao mexe em numero):** o texto-base das questoes de lacuna mostra o
`____` - lido por colunas, o tracinho virava espaco duplo, ou espaco no
comeco da linha -, so no texto com 2 espacos duplos ou mais (85 questoes
relidas pelo `radar questoes --textos-base`); a tela da questao e a ficha
avisam, com o link do caderno, quando a leitura nao mostra todas as lacunas
que a alternativa pede (6 de 287, pendencia N); a Crase 2 aponta para o
assunto "Emprego da crase" (24 reais e 83 geradas, antes 1 e 29); e 20
geradas novas nos dois formatos que voce mostrou - 10 de texto com "a • à •
há", 10 de crase e regencia verbal, sempre pela preposicao "a".
**Outras bancas no treino e na medida (17/10, decisao 166, a seu pedido; fura
a I3):** o Qconcursos e o TEC Concursos ficam fora (os termos dos dois
proibem robo, mesmo acionado por voce), e as provas de outras bancas entram
pelo site oficial de cada uma. Elas medem o seu acerto por no, com a origem
ao lado, e nunca o que a FEPESE cobra; Certo/Errado so treina; o fechamento
de 07/11 continua so FEPESE. O levantamento de 9 bancas
([levantamento_de_bancas](docs/levantamento_de_bancas.md)) deu Cebraspe, ACAFE
e IDIB com ressalva. **Feita a etapa A** (o mecanismo): `radar classificar
--pedido --evidencia fora`, o leitor da IESES consertado (a alternativa d
levava a questao seguinte) e relido so nela (`radar questoes --refazer
--banca IESES`), o "Treinar com outras bancas no radar" na faixa e "(N FEPESE,
M de outras bancas)" no Meu desempenho - e, desde 18/10, no acumulado do
Minhas materias e da tabela de 07/11, o numero que decide (a conta nao muda;
o anotado fica do lado da FEPESE); a mesma questao em outro caderno e
uma so (`outras_bancas.mesma_questao`). No dado de hoje, 41 questoes de
Portugues da IESES (38 classificadas).
**Os tres botoes e as bancas novas (17/10, decisoes 167 e 168):** cada faixa
de treino tem "Gerar questao real" (as reais da FEPESE do no, em toda
materia; `servico/fepese_no_radar.py`), "Gerar questoes outras bancas" (com
"ainda nao ha") e "Gerar treino" (as geradas). O treino com questao real da
FEPESE nunca usa o que uma rodada que mede ainda vai usar
(`composicao.reserva_das_que_medem`: o fechamento de 07/11 guarda 50). A
FEPESE entra tambem pelo cargo (`radar provas --por-conteudo`; o firewall
dela bloqueou os hotsites na primeira leitura, e o radar para depois de 5
sem resposta: ir devagar). Outras bancas entram por lista conferida
(`config/provas_de_outras_bancas.yml`, `radar provas --outras-bancas`), com
leitor por banca: NC-UFPR (PC-PR 2020) e Selecon (SEJUSP/MG 2021, Policial
Penal). Classificado so o Direito; a arvore foi a 561 nos.
**O Cebraspe (17/10, decisao 169):** 14 cadernos de multipla escolha de
2019 a 2026 (`radar/questoes_cebraspe.py`; o download confere o `%%EOF`),
422 questoes de lei, 220 no edital pelo pedido generico (um por caderno, a
materia e resposta da classificacao); a PC PB 2022 fica sem gabarito (o
definitivo nao confere com o caderno publicado). A arvore foi a 682 nos. No
treino, de outras bancas: Constitucional 73, Penal 44, Legislacao Especial
39, Processo Penal 29, Direitos Humanos 26, LEP 15. Faltam a ACAFE, o IDIB,
o IBADE (liberado por voce) e as Guardas da Selecon: pendencia O.
**Os sabados leves e o Raciocinio na sexta (pedido de 18/10, decisao 170, a
seu pedido e fora dos lotes; nao mexe na medicao):** de 23/10 a 07/11 o
sabado tem umas 2 horas, num bloco so - as revisoes do dia (ate 5 questoes
cada), a "Revisao rapida" (so as erradas da semana), o Simulado da semana de
25 e a correcao das erradas: 24/10 com 2h15, 31/10 com 2h35. O Simulado da
semana e a regra da 69 em duas partes (20 dos temas de segunda a sexta, 5 dos
de antes, com o Raciocinio Logico), cada tema primeiro do radar - a FEPESE
fora da reserva de 07/11, depois outras bancas, as nunca feitas primeiro -, e
so o que falta no Qconcursos; treina e nunca mede (`treino: true`, recusado
pelo `composicao.mede`; a rodada `simulado_da_semana` corrige no fim). O 07/11
ficou so com o fechamento e a correcao, na mesma posicao da noite (a semente
das 50 nao mudou). Nas sextas a aula de Raciocinio do sabado entra no lugar da
lei seca e do Portugues (10 de RL a noite), e o Portugues da sexta foi para a
segunda seguinte; Termos integrantes 2, Redacao oficial 2, a Revisao ativa 3 e
cinco revisoes foram para o Ciclo 2 (pendencia D). O Ciclo 1 foi de 2133 para
2050 questoes.
**A conferencia das provas novas (pedido de 18/10, Parte 2, decisao 171; so o
Claude Code ate 01/11, voce depois de 07/11):** as 640 classificacoes de 17/10
foram lidas de novo as cegas (11 leituras, so com a arvore): 435 no mesmo no
(conferidas pelo Claude Code), 97 no mesmo assunto (foram para o no em comum,
regra nova, tambem conferidas), 79 pendentes nas duas e 29 que discordam -
estas viraram pendentes, lado a lado na lista unica, para conferir depois de
07/11. Pendente nao treina nem entra no fechamento. O passo 2 (a data da
prova) conferiu as 449 de Direito contra o que mudou depois de cada prova -
lei, emenda e decisao do STF com efeito geral: 8 sairam do treino (2 pela lei,
6 pelo gabarito discutivel) e 34 ganharam o aviso "A lei mudou depois desta
prova" (27 itens 🟣 no config/leis.yml, com a chave nova `provas`, que prende
o item aos cadernos conferidos); o aviso aparece tambem na tela da questao,
depois da resposta. O passo 3 apagou 31 dos 40 nos novos que ficaram vazios
(`conteudos.apagar_vazio`; a arvore foi a 707); os outros 9 sao leitura de
questao pendente e saem depois da sua conferencia.
**Os PDFs baixados a mao e a versao do caderno (18/10, decisao 172, a seu
pedido):** a lista de outras bancas aceita o PDF que voce salva em
`data\provas\manual\` (`arquivo`, com o link original no `caderno`), e o
caderno que vem em mais de uma versao (Tipo 1 a 4, Prova A e B) so e lido
na `versao` da lista: as paginas dela (`radar/questoes_por_rodada.py`, um
leitor para a FGV, a Access, a Idecan e a Selecon nova) e o bloco dela no
gabarito (`radar/gabarito_por_versao.py`), ou nada entra - o "PROVA A" da PM
de Sergipe trazia a Prova B junto. A anulada fica de fora de toda conta e
treino, como sempre; o gabarito preliminar nao entra. Entraram 11 provas
(SEAP-BA, SENAPPEN, PM SE Soldado e Oficial, Guardas de Niteroi, Ribeirao
Preto e Cariacica; e, no adendo, a PC SC 2026 da Idecan, Escrivao e Agente,
a PC SC 2023 Delegado e a PC RN 2021, da FGV), 417 questoes, 194 no edital,
relidas as cegas pela regra da 171 (159 no mesmo no, 24 no no em comum, 11
pendentes). O `caderno` e o link de onde veio (ate espelho, como o
Qconcursos), e o `radar baixar-provas` nunca busca o que veio a mao.
Dos gabaritos discutiveis, 6 sairam do treino (3 depois, tambem aprovados
por voce em 18/10: Escrivao q25, Delegado q46 e Cariacica q45) e a de Ribeirao
Preto ganhou o aviso do STF. Outras bancas no treino: 424 de lei. Falta o Delegado
da PC RN, se voce quiser (pendencia O).
**A tela da amostra das provas novas (18/10, decisao 173, a seu pedido):** a
conferencia ganhou dois recortes, nunca juntos com o alvo e o complementar -
"outras bancas" (com a banca, o ano e o cargo) e "provas novas de 17/10". O
lote e a lista de chaves do `data/lotes_de_classificacao.json` (a procedencia
nao bastava), e a amostra de cada grupo (FEPESE, NC-UFPR e Selecon, Cebraspe,
IESES) sai do que a segunda leitura decidiu sozinha - o mesmo no, o no em
comum e a pendente nas duas -, pelo hash da chave, uma por questao: nas 10
primeiras, nenhum erro passa, 2 voltam, 1 abre as 10 seguintes (os tamanhos
no `config/amostra.yml`); descer no mesmo ramo e ajuste, e nao erro. As 37
pendentes (regra c e fora do treino) ficam na mesma tela. Em todo recorte a
questao nao respondida no radar vem sem a letra, o dispositivo, a pegadinha
e o trecho, e o "Responder no radar" abre so ela, como treino; a guardada para
uma rodada que mede (38 do alvo e 12 do complementar) nao aparece. A sua
conferencia entra no Ciclo 2, uns 20 minutos por semana (pendencia D).
**O motivo de cada erro, num clique (18/10, decisao 174, a seu pedido; nao
mexe em numero):** toda resposta errada no radar tem cinco botoes - Nao
sabia, Confundi, Li errado, Pegadinha, Chutei - e o clique grava o motivo na
propria resposta (`respostas_de_simulado.motivo`, banco na versao 9; vale o
ultimo). No treino, na correcao; na rodada que corrige no fim, so no
relatorio. O "vou no chute" ja marca o Chutei (`erros.motivo_do_erro`, sem
gravar nada), o caderno aberto pelo radar leva o motivo de volta para a
resposta, e o "📝 Como foi" da faixa ganha os erros de fora do radar por
motivo, com a soma presa aos erros do "fiz". A conta do Historico (parte 1)
esta pronta, sem tela: `metricas.motivos_dos_erros`, por origem, nunca
somadas, cada erro uma vez, com o erro bobo (`erros.ERRO_BOBO`).
**Sem lei seca de 19/10 em diante (18/10, decisao 175, a seu pedido):** as 12
faixas de lei seca que restavam no Ciclo 1 sairam do `config/cronograma.yml`,
com a pausa logo depois, sem nada no lugar: a manha acaba as 12h00. As
sextas da 170, os sabados, o 07/11 e os dias passados ficam iguais; o Plano
B e o "Resumo" continuam com os artigos-chave. O Ciclo 2 decide se tera lei
seca (pendencia D).
**Os pronomes e o Portugues das provas novas (19/10, decisao 177, a seu
pedido; cabe na I3: corrige um numero):** as 9 questoes de emprego de pronome
que estavam no no de colocacao foram para o no da ficha Pronomes 1 (a faixa
de 19/10 dizia "0 do radar"), e as 163 de Portugues da FEPESE das provas novas
de 17/10, sem classificacao ate ali, foram classificadas e lidas de novo as
cegas pela regra da 171 (121 no mesmo no, 10 no no em comum, 12 na lista unica
e 20 pendentes nas duas; o lote "2026-10-19"). A reserva de 07/11 manteve a
composicao, com 21 das 50 trocadas. Ampliar o Portugues da FEPESE fica para
depois de 07/11 (pendencia O).
**O sublinhado e o negrito do caderno (19/10, decisao 178, a seu pedido; nao
mexe em numero):** "o termo sublinhado" agora aparece sublinhado - na questao
do treino e da rodada, no relatorio, na ficha, na conferencia e nos macetes.
O `radar/destaques.py` le a posicao das letras e os tracos do caderno pelo
`pdfminer.six` (dependencia nova), acha o trecho no campo da questao pelo
texto em volta e grava na coluna `questoes.destaques` (banco na versao 10),
sem mudar o texto nem a chave; `radar questoes --destaques` preenche o
acervo, e cada caderno lido depois ja vem com as marcas.
**O circulo em toda faixa (20/10, decisao 179, a seu pedido):** a faixa de
questoes ganhou o circulo - sem numero, conta na meta e no tempo
(`sem_numero`), e o 0 digitado continua recusado -, a feita dobra numa linha
com o resultado, e a faixa que o radar cobriu fecha sozinha
(`cronograma.fechar_pelo_radar`, depois de cada resposta). O 19/10 ficou Ideal,
9 de 9. As outras melhorias da aba Hoje estao propostas na pendencia O.
**A faixa enxuta (22/10, decisao 180, a seu pedido):** a faixa da Hoje tem a
linha (com o "caiu" curto, `CaiuNoAlvo.etiqueta`), o que fazer agora (com
"Treinar no radar: FEPESE · Outras bancas · IA", um clique cada) e um "mais"
fechado com o resto; as regras que se repetiam viraram um "ⓘ" so. Nada saiu
da tela.
**A barra do dia e a proxima faixa (22/10, decisao 181, a seu pedido):** o
topo da Hoje tem "4 de 9 faixas · 29 de 49 questoes · 1h45 de 3h40" com a
barra (`cronograma.progresso_do_dia`, a mesma regra de faixa da sugestao) e a
proxima faixa por fazer, na ordem do dia; o bloco completo nasce fechado.
**Proximo:** os sabados que medem (17/10 e 07/11) e o Ciclo 2;
depois de 07/11, o redesenho das telas e a nuvem
([roteiro_nuvem](docs/roteiro_nuvem.md), decisao 126).
**Conferido:** o Actions de 04/10 foi verde (`coleta: 2026-10-04`); as duas
coletas de 18/10 morreram no commit (o status de 20 classificacoes fora de
sincronia), consertado em 19/10 (decisao 176). O backup das 23h30 voltou em
03/10.
**Em aberto:** a falta do estoque de geradas de 13/10 em diante (sob demanda),
as 2 explicacoes do complementar e as 2 do alvo que ficaram de fora, a
alternativa da 2019-q6 com o Texto 2 colado, a Redacao oficial sem link do Qconcursos, o texto local das leis (o
verificador ainda nao confere se o artigo citado existe) e o resto dos
achados da varredura de 03/10 (pendencia F). Ordem e detalhe em
[docs/pendencias.md](docs/pendencias.md); arvore no [README](README.md);
banco em `data/radar.db`.

**Arquitetura a preservar:** cada fonte e um arquivo isolado em `collectors/`,
herda de `Coletor`, devolve `list[ItemColetado]` e esta em `COLETORES`
(`servico/coleta.py`) - nada fora de `collectors/` sabe de onde vem o dado. O
`servico` e um pacote, um arquivo por assunto; escreva `servico.funcao(...)`.
**Toda contagem de questao, acerto e erro passa pelo `servico/metricas.py`**:
tela nenhuma refaz a conta, e template nenhum soma. **Todo minimo de amostra sai do
`config/amostra.yml`**, pelo `radar/amostra.py`: nenhuma tela tem regua propria.
A unica excecao e o 3 do `servico/erros.py` (fatia de motivo de erro, nao
acerto); a evolucao da home, a tendencia de letra no gabarito e o "base
pequena" vieram para o arquivo em 04/10 (decisao 83). **Se um tema caiu nas provas do
alvo sai do `incidencia.caiu_no_alvo`** (decisao 108), por `fichas.caiu_do_tema`:
ficha, faixa, aba e redistribuicao nao refazem a conta. **O resumo do tema
mora na ficha** (`resumo`), cada frase com a fonte, conferido pelo
`fichas.conferir_resumo` na importacao e no `--verificar-resumos`; a parte
"caiu ou nao caiu" e calculada na hora, nunca gravada. **A tela o mostra
enxuto** (`fichas.resumo_enxuto`, decisao 161): o artigo de cada frase sai do
`radar/artigos.py`, a traducao de cada artigo mora na ficha (`traducao`) e e
conferida pelo `radar/traducao.py`, e o glossario corta o texto no servico
(`radar/glossario.py`); o template so desenha. **A prioridade de um
tema sai do `config/prioridade.yml`**,
pelo `radar/prioridade.py`, e a ficha de estudo do `radar/fichas.py`: o tema e
reconhecido pelo titulo da faixa, sem o prefixo, e o texto escrito mora em
`data/fichas.json`, 🟣 com a procedencia. **O desempenho por conteudo e do
`servico/desempenho_por_conteudo.py`**, e os dois recortes - medido no radar e
anotado - **nunca sao somados na tela**, so no estado da amostra. **O assunto
do "Onde estudar primeiro" e da revisao espacada e o no da arvore** em que a
questao foi classificada (decisao 74), e nao o catalogo nem a coluna
`assunto`. **A fila de revisao e uma so, a do `servico/estudo.py`**
(decisao 128): o Meu desempenho a mostra inteira, a home e a rodada de
revisao so as pontas (`estudo.pontas`). **O texto-base da questao mora so no
banco** (`texto_base`, decisao 132): e de terceiros, e nunca vai para arquivo
versionado. **A ultima revisao de um no sai do `Lancamento.revisao`** do
`metricas` (decisao 79) - faixa de revisao, extra de revisao, rodada que
revisa; pratica nao e revisao -, e a evolucao semanal conta toda resposta.
**Os selos moram no `radar/origem.py`**, e quem escolhe a cor e o dado: o
servico grava a origem (`origem`, ou `origens` quando junta partes) e o
template so desenha; `--selo-*` so no `design.css`, e a meta do dia tem as
cores dela. **A composicao das rodadas que medem** (diagnostico e simulado no radar) **sai
do `servico/composicao.py`** (decisao 67): so questao real da FEPESE, do alvo e
do complementar aceito, e gravada na rodada; a do simulado do Qconcursos
tambem, por tema estudado (decisao 69). **O sabado** - a revisao semanal, o
R+7 dos diagnosticos e a comparacao de 07/11 - **sai do `servico/sabado.py`**
(decisao 70). **A faixa de Portugues que comeca no radar** sai do
`servico/faixa_no_radar.py` (decisao 107). **O treino com outras bancas** sai
do `servico/outras_bancas.py` (decisao 166): so evidencia `fora`, e nunca
entra na incidencia nem nas rodadas que medem. **O Simulado da semana** sai
do `servico/simulado_da_semana.py` (decisao 170): faixa com `treino`, que o
`composicao.mede` recusa - treina, nunca mede nem reserva questao. **A amostra
do lote** sai do `servico/conferencia_do_lote.py` (decisao 173): o lote e a
lista de chaves do `data/lotes_de_classificacao.json`, e a conferencia nunca
mostra a letra da questao que eu nao respondi no radar nem a guardada para uma
rodada que mede. **O sublinhado e o negrito da questao** saem do `radar/destaques.py`
(decisao 178), gravados em `questoes.destaques` fora da chave; a tela so
desenha pelo filtro `destacado`. **O motivo do erro** sai do `erros.motivo_do_erro` (decisao
174), e a conta dos motivos do `metricas.motivos_dos_erros`: o caderno com
fonte "radar" nunca conta (o erro conta pela resposta), e nada disso entra em
acerto, erro ou volume. **Onde a faixa esta na arvore** sai do `fichas.onde_na_arvore`
(decisao 71): a ficha, ou a chave `nos` do plano; nenhum no e criado. Para o
estudado e as datas, a faixa sem `conteudo` conta nos `nos` do plano e na
ficha CONFERIDA, nunca no acerto (decisao 81). **Alvo,
complementar e
fora saem do `servico/evidencia.py`** (uma regra, nunca somados; e prova
complementar so entra em estatistica se estiver aceita no
`data/acervo_complementar.json`), e tudo que
aponta para um conteudo usa o caminho do no (`data/conteudos.json`); a
classificacao reconhece a questao pela CHAVE (enunciado + alternativas), nunca
so pela impressao do enunciado - e a gerada aponta a sua base tambem pela chave
(decisao 77).
Reler o caderno (`radar questoes --refazer`) leva a classificacao e a base
das geradas para a chave nova, so quando o texto e o da mesma questao
(decisao 90). Mudanca de estrutura do banco vira passo novo em `migracoes.py`, e o
`criar_tabelas` confere o esquema uma vez por conexao (decisao 80): banco
trocado por baixo de um processo pede `db.resetar_engine()`.

## Fontes de dados

Nao existe API oficial unica de concursos no Brasil.

- prefira **RSS e dados abertos** a raspagem de HTML, sempre;
- **nao** raspe site cujos termos proibem (Qconcursos, por exemplo) nem
  conteudo atras de login ou paywall;
- respeite `robots.txt` **sem excecao**, mantenha o atraso e identifique-se no
  User-Agent - a classe `Coletor` faz os tres. O DOM/SC, o DOU e o Querido
  Diario estao fora por isso; o Planalto tambem, que so responde a navegador;
- guarde sempre o link original: isto e um indice pessoal, nao uma copia do
  conteudo de ninguem.

## Como trabalhar aqui

- **trabalhe sempre na branch `main`.** Nao abra branch nem PR;
- **commit e push ao fim de cada etapa**, nunca deixando trabalho so no disco;
- **se uma decisao mudar, atualize `docs/decisoes.md`** na mesma etapa;
- **uma coisa por vez.** Uma mudanca, testada, e so entao a proxima. Nao
  refatore o que nao faz parte do pedido. **Uma conversa por etapa:** ao fim,
  atualize os docs e o "Estado atual";
- **teste nunca depende do Windows nem da data de hoje** (o Actions e Linux);
- **questao gerada por IA TREINA, nunca MEDE**: vive em `questoes_geradas`,
  fora de tudo que conta o que a banca cobra, e o acerto nela e um segundo
  numero - nunca somado ao das reais;
- **dado vindo de IA so entra com procedencia** (modelo e data), e **nunca
  apresente como saida dela um texto que ela nao escreveu**: simulacao mostra
  o PEDIDO, nao um exemplo de resposta;
- todo coletor e todo classificador precisa de **teste com dado fixo**
  (fixture em arquivo), nunca teste que va a internet;
- antes de dizer que terminou: `pytest -q` passando **e** o comando afetado
  rodado de verdade no terminal;
- nao adicione dependencia sem justificar em uma linha;
- **me diga quando nao souber** em vez de inventar seletor de HTML, URL ou nome
  de campo. Se precisar da estrutura real de uma pagina, peca para eu baixar e
  colar — o Claude Code na web **nao tem internet aberta**.
