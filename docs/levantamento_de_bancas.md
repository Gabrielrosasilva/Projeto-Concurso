# Levantamento das bancas: onde estão as provas de outras bancas

Registro do levantamento de 17/10/2026, que deu origem à decisão 166 e à pendência O. Feito pelo Claude Code (claude-opus-5-5), **só leitura**: nada do repositório mudou, e os PDFs de amostra ficaram fora dele. Vale o que valia no dia: site de banca muda, e cada etapa confere de novo antes de escrever o coletor.

## Por que

O simulado da semana manda fazer questões que você não acha no Qconcursos, e várias matérias (a aplicação da lei penal, por exemplo) não têm mais questão da FEPESE. O pedido: "sobre esse assunto, responda esta questão", dentro do radar e contado.

**O Qconcursos e o TEC Concursos ficam fora**, e não é só a regra do CLAUDE.md:

- **TEC Concursos** ([termos de uso](https://www.tecconcursos.com.br/termos-de-uso), lidos em 17/10): a cláusula 18, item 8.1, proíbe "robôs, scripts, crawlers, spiders, scrapers, agentes autônomos"; o 8.2 diz que vale "inclusive quando a ferramenta for acionada diretamente pelo próprio usuário"; a 18.7 proíbe compartilhar a conta; a 20 proíbe reproduzir o conteúdo. O [robots.txt](https://www.tecconcursos.com.br/robots.txt) bloqueia questões e cadernos para qualquer robô;
- **Qconcursos**: os termos proíbem raspagem (decisão 140).

As questões desses sites são as provas das bancas. O caminho é o site oficial de cada banca.

## Como foi feito

Nove bancas, as do CLAUDE.md: as de segurança pública (Instituto AOCP, IDIB, IBFC, FUNDATEC, Instituto Consulplan, Cebraspe) e as de SC (ACAFE, FURB, Instituto o Barriga Verde). Em cada uma:

- o robots.txt lido antes de tudo, pela RFC 9309 (4xx = sem regras);
- curl com o User-Agent do radar e 2 s entre pedidos;
- sem login, sem agregador;
- o termo de uso procurado;
- um caderno de segurança pública baixado e lido com o `pypdf`, a mesma biblioteca do radar.

**Dois deslizes**, ambos registrados aqui:

- **AOCP**: um PDF (um comunicado da Polícia Penal DF 2022) foi baixado no mesmo comando que leu o robots.txt do host `arquivos-site.institutoaocp.org.br`, que é `Disallow: /`. Foi apagado sem ser aberto, e o host não foi mais acessado.
- **FURB**: o redirecionamento para `concursos.furb.br/` foi seguido antes de ler o robots.txt dele. A raiz é liberada.

## Resultado

| Banca | Onde estão as provas | robots.txt | Termos | Caderno em texto? | Alternativas | Segurança pública | Recomendação |
|---|---|---|---|---|---|---|---|
| **Cebraspe** | API JSON da própria tela (`apis.cebraspe.org.br/cebraspe/eventos/...`) e PDF em `cdn.cebraspe.org.br` | liberado | sem termos; o caderno diz **"É permitida a reprodução deste material apenas para fins didáticos, desde que citada a fonte"** | sim, bom | maioria **Certo/Errado**; A a E no PC PE 2023 e na PM SC 2023 Oficial | ~50 encerrados (5 penitenciários) + 19 em andamento | **entra com ressalva** |
| **ACAFE** | hotsite de cada concurso, PDF estático em `storage.acafe.org.br` | 404 (liberado) | sem termos | sim, menos o Agente 2014 (escaneado) | A a D (2010), A a E (2014) | PC SC 2010 (Agente, Escrivão) e 2014 (Agente, Delegado) | **entra com ressalva** |
| **IDIB** | `concurso.idib.org.br/Concurso.aspx?ID=n`, **só na janela do recurso** | liberado | sem termos; o download pede o cabeçalho Referer da página oficial | sim, excelente (100 de 100) | A a E | ~10; **1 caderno no ar** (PMES CHS 2026) | **entra com ressalva**, daqui para frente |
| Instituto AOCP | os PDFs ficam em `arquivos-site.institutoaocp.org.br` | **`Disallow: /`** nesse host | sem termos | não testado | — | ~50 (5 penitenciários) | **não entra** (a API da lista, que o coletor usa, continua liberada) |
| IBFC | `ibfc.selecao.net.br/informacoes/<id>/` | listas liberadas | sem termos | não testado | A a E | ~27 | **não entra**: o caderno sai do ar ou pede login (Polícia Penal GO 2024) |
| FURB | `concursos.furb.br/informacoes/<id>/`, PDF em `anexos.cdn.selecao.net.br` | **`Disallow: /`** no CDN do acervo | o edital cita "direitos autorais adquiridos" | sim (2026, em .7z) | A a E | 1 Guarda Municipal (Itapema 2022, no CDN proibido) | **não entra** |
| Instituto Consulplan | `institutoconsulplan.org.br/Concursos` | liberado | sem termos | sim | A a E | ~6 a 10, só gabarito | **não entra**: o caderno da objetiva quase nunca é publicado |
| FUNDATEC | — | não lido: o site inteiro responde o desafio de robô do AWS WAF | não acessível | — | — | — | **não entra** (passar pelo desafio seria contornar a proteção) |
| Instituto o Barriga Verde | — | — | — | — | — | — | **não entra**: hoje não há site oficial com provas (`iobv.org.br` é um modelo vazio) |

## O que entra, com as ressalvas

### Cebraspe: o maior volume

- **Lista:** `GET https://apis.cebraspe.org.br/cebraspe/eventos/tipo/concursos/fase/encerrado`, com 426 encerrados em 17/10.
- **Detalhe:** `GET https://apis.cebraspe.org.br/cebraspe/eventos/<eventoURL>`, que traz `arquivosGabarito[]` com "PROVA OBJETIVA - CARGO N" e "GABARITO DEFINITIVO".
- **Endereço do PDF:** `https://cdn.cebraspe.org.br/concursos/<eventoURL>/arquivos/<nomeArquivo>`, ou `https://cdn.cebraspe.org.br/<nomeArquivo>` quando `isGuid`.
- **Penitenciários:**
  - DEPEN 2020: Certo/Errado, com Penal, Processo Penal, LEP e Direitos Humanos;
  - SERES PE 2017 e 2021;
  - SERIS AL 2021.
- **Múltipla escolha verificada:** PC PE 2023 e PM SC 2023 Oficial. O caderno "com justificativas" marca cada alternativa CORRETA ou INCORRETA, com o item do edital.
- **Ressalvas:**
  - **Certo/Errado só treina** (decisão 166). Quantos dos ~50 de segurança são de múltipla escolha ainda não foi contado;
  - **o CDN dá 404 de vez em quando**: a prova da PC PE deu 404 e, minutos depois, 200. O coletor repete, e um 404 sozinho não prova que o arquivo não existe;
  - **o caderno não diz o nome da matéria**: ela sai do comando ("Com relação a direito penal, julgue...") ou do item do edital nas justificativas;
  - a API não é documentada; é a da própria tela, como a da AOCP.

### ACAFE: pouco, mas de SC e com Penal

- **Os cadernos, numa lista fixa de URLs** (cada hotsite tem um desenho, então não há raspador genérico):
  - PC SC 2010, Agente e Escrivão (`storage.acafe.org.br/concurso/policia_civil/2010/`): Constitucional, Administrativo, Penal e Processo Penal, Direitos Humanos;
  - PC SC 2014, Delegado (`.../2014/delegado/`): inclui aplicação da lei penal;
  - Celesc 2024, Advogado: Constitucional e Administrativo.
- **Gabarito:** PDF à parte, com o oficial pós-recurso e as anuladas.
- **Ressalvas:**
  - **o caderno de Agente 2014 é imagem** e fica fora sem OCR;
  - a leitura pede limpeza: o glifo "⇒" nas alternativas de 2010, o espaço no meio da palavra ("naci o-nal") e o hífen de fim de linha. Isso mexe na chave da questão (enunciado + alternativas);
  - **as provas são anteriores ao Pacote Anticrime (2019) e à nova Lei de Abuso de Autoridade**: o gabarito pode estar desatualizado, como na [lista de leis alteradas](leis_alteradas.md).

### IDIB: só daqui para frente

- **Quando o caderno fica no ar:** o edital do CBMSC CFO 2026 diz que "as provas objetivas serão disponibilizadas no site www.idib.org.br, no período de recurso". Depois disso, a página fica só com os gabaritos: das 11 olhadas, só a da PMES CHS 2026 ainda tinha a prova.
- **Como captar:** na janela do recurso. O radar já consulta o IDIB todo dia.
- **O Referer:** o download devolve "Download disponível apenas através do site oficial." sem o cabeçalho Referer da página do concurso. É trava contra link direto, não login, mas mandar o Referer é decisão sua (pendência O).
- **Ressalvas:**
  - os tipos A, B e C vêm no mesmo PDF;
  - o nome da matéria sai no fim do texto da página, e não antes da 1ª questão dela;
  - a plataforma nova (`idib.selecao.net.br`) guarda os anexos num CDN proibido.

## O que não entra, e o que daria

Quatro bancas, uma por uma:

- **AOCP, FURB:** o robots.txt proíbe o servidor dos PDFs. **IBFC, Consulplan:** o caderno não é publicado, ou sai do ar.
- **FUNDATEC:** não deu nem para ler o robots.txt. Daria só baixando à mão no navegador e importando de uma pasta local, mas os termos dela não foram lidos, e isso não está planejado.
- **AOCP:** é a banca da PM SC. Se o caderno da PM SC sair numa página pública, vale olhar de novo.

## Segundo levantamento: as bancas de concurso policial de 2019 a 2026 (17/10)

Pedido seu, depois da etapa A: todas as bancas que fazem ou fizeram concurso policial de 2019 a 2026, com as matérias de lei do edital da Polícia Penal (Português e Raciocínio ficam de fora: a FEPESE já tem bastante). Doze bancas, com as mesmas regras do primeiro. Em cada uma, o pesquisador também anotou o que o robô não pode e uma pessoa pode baixar à mão no navegador, como você se ofereceu para fazer.

| Banca | O que tem de policial, 2019–2026 | Robô | Termos | Recomendação |
|---|---|---|---|---|
| **NC-UFPR** | **Polícia Civil PR 2020**: Delegado (~100 de Direito) e Investigador/Papiloscopista (25); Guardas de Colombo 2022, Alm. Tamandaré 2023 e Campo Magro 2024. A–E, com a resposta certa marcada (►) no próprio caderno | pode | sem termos; caderno sem cláusula | **entra pelo robô** |
| **Selecon** (site principal) | **SEJUSP/MG 2021, Policial Penal** (40 de 60 de Direito, com LEP); Guardas de Niterói 2019, Boa Vista 2019, Campo Grande 2020, São Gonçalo 2020 e São Luís 2022. A–D | pode | sem termos | **entra pelo robô** |
| **IBADE** | **Agente Socioeducativo AC 2021** (~55 de 60 de Direito), **Inspetor Penitenciário ES 2023** (25 de 60), PC/ES 2025, peritos BA 2022, GCM SP 2022 e outras. A–E | pode | **a cláusula 5 proíbe**: o conteúdo "não pode ser copiado, reproduzido, distribuído ou utilizado sem autorização expressa do IBADE" | **decisão sua** |
| **FGV** | **SEAP-BA 2024, Agente Penitenciário** (50 de 80 de Direito, A–E); a lista traz ainda a **Polícia Civil SC 2023**, PCs de MG, PI, PR, RJ, RN e AM, Guardas e PMs | o robots.txt deixa, **os termos não**: "Não utilizar ferramentas automatizadas" | proíbem robô e "reproduzir, duplicar, copiar" | **só à mão**, e com a mesma decisão sobre reprodução |
| **Idecan** | Polícia Civil CE 2021, Perícia Forense CE 2021, Bombeiros RR | o site inteiro atrás de um desafio anti-robô | não achados | **só à mão** |
| **FUMARC** | PC MG 2022 (Analista e Técnico Assistente), ALMG Policial Legislativo, TRT3 Polícia Judicial; os cadernos da PC MG 2021 nunca foram publicados | pode | sem termos | pelo robô, **prioridade baixa** (pouco Direito, muita lei mineira) |
| **Access** | Guardas de Ribeirão Preto 2023, Cariacica 2023, Apiaí 2024; Bombeiros PB internos 2025 | o servidor dos PDFs proíbe | não achados | **só à mão**, prioridade baixa |
| **Vunesp** | não deu para saber | bloqueia o robô já no robots.txt | não lidos | conferir no navegador |
| **FCC** | PMs e Bombeiros de BA, AP e PI; nenhuma Polícia Penal | o robots.txt barra as páginas de concurso e os PDFs | não achados | **só à mão**, prioridade baixa |
| **IADES** | Agente de Segurança Prisional GO 2019, PM-PA 2020, Polícia Técnico-Científica GO 2023 | pode | não achados | **não entra**: os cadernos vêm trancados pela banca (copiar e imprimir proibidos), e abrir o texto seria furar a trava |
| **Instituto Mais** | só Guardas, com o caderno na área do candidato inscrito | — | — | **não entra** |
| **Quadrix** | nenhum concurso policial | — | — | **não entra** |

**O que só dá à mão** (páginas públicas, sem login, no navegador):
- **FGV**: `https://conhecimento.fgv.br/concursos/seapba24` (SEAP-BA 2024; basta o Tipo 1 e o "Gabarito Oficial Definitivo"), `/concursos/pcsc23` (PC SC 2023) e as outras Polícias Civis da lista;
- **Idecan**: `https://concurso.idecan.org.br/`, nos concursos realizados: PC-CE 2021 e PEFOCE 2021;
- **Selecon** (plataforma nova): `https://selecon.selecao.net.br/informacoes/45/` e `/46/` (PM SE 2024), `/48/` (SENAPPEN 2024), `/52/` (GCM Niterói 2024);
- **FCC**: `https://www.concursosfcc.com.br/concursos/govba222/index.html` (PM e Bombeiros BA 2022) e as do AP e PI;
- **Access**: `https://concursos.access.org.br/informacoes/69/`, `/86/`, `/135/`.

Baixado à mão, o PDF ainda precisa de um leitor do caderno daquela banca e de uma entrada no radar para PDF que não veio pelo robô (pendência O).
