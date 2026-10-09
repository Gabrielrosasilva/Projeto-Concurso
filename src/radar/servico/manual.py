"""Usar a IA sem pagar a API: o pedido vai para um arquivo, a resposta volta.

O `radar gerar --valendo` chama a API e custa dinheiro. Este e o outro
caminho: o radar escreve TODOS os pedidos em `data/pedido_ia.json`, com a
instrucao e o formato da resposta dentro, eu respondo pelo Claude Code do VS
Code (na minha assinatura), e o radar le a resposta de volta.

Duas regras seguram tudo, e sao as mesmas da API:

  * **procedencia honesta.** O que entra por aqui e gravado como "Claude
    Code, importado manualmente, em <data>" - NUNCA com o nome do modelo da
    API. O radar nao sabe qual modelo o Claude Code usou, e dizer que sabe
    seria inventar procedencia;
  * **resposta torta e recusada, e contada.** Questao sem as cinco
    alternativas, sem gabarito ou sem o artigo da lei nao entra; macete sem
    fonte, ou citando questao que nao foi enviada, tambem nao.

Serve para os dois: questao gerada (`tipo: questoes`) e macete (`tipo:
macetes`). A questao gerada entra na tabela `questoes_geradas`, com a mesma
separacao de sempre - treina, nunca mede. O macete ainda nao tem tela: ele
vai para `data/macetes.json`, versionado, e a Central de Macetes (fase 5 da
especificacao) le de la.
"""
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

from radar import config, gerador, leis
from radar.db import criar_tabelas, sessao
from radar.models import agora
from radar.origem import FRASE_SEM_EVIDENCIA, IA
from radar.questoes import chave_da_questao
from radar.regioes import normalizar
from radar.servico import geradas
from radar.util import fuso_local

TIPOS = ("questoes", "macetes", "explicacoes", "classificacao", "fichas", "associados",
         "resumos", "novidades")

# Quantos macetes por materia. Tres cabe numa resposta so e obriga a IA a
# escolher o que mais cai, em vez de listar tudo.
MACETES_POR_MATERIA = 3


def caminho_do_pedido() -> Path:
    return config.diretorio_dados() / "pedido_ia.json"


def caminho_dos_macetes() -> Path:
    return config.diretorio_dados() / "macetes.json"


def caminho_das_explicacoes() -> Path:
    return config.diretorio_dados() / "explicacoes.json"


#: O nome de modelo que a resposta pode declarar: letras, numeros, ponto,
#: hifen e sublinhado ("claude-opus-5-5"). Outra coisa nao entra no texto.
MODELO_DECLARADO = re.compile(r"^[A-Za-z0-9._-]{3,60}$")


def procedencia(quando: datetime | None = None, modelo_ia: str | None = None) -> str:
    """O que vai no campo `modelo`: o caminho e, quando a resposta diz, o
    modelo que escreveu (decisao 116, revisa a 47). O importador nao sabe
    quem respondeu; quem escreve sabe, e declara no `modelo` da resposta.

    A data e a do relogio de Florianopolis: o `agora()` e UTC, e uma
    importacao depois das 21h saia com o dia seguinte (as 61 fichas de
    02/10/2026, importadas as 22h, sairam "em 03/10/2026")."""
    momento = quando or agora()
    if momento.tzinfo is not None:
        momento = momento.astimezone(fuso_local())
    quem = "Claude Code"
    if modelo_ia and MODELO_DECLARADO.match(modelo_ia.strip()):
        quem = f"Claude Code ({modelo_ia.strip()})"
    return f"{quem}, importado manualmente, em {momento:%d/%m/%Y}"


# --- as instrucoes ----------------------------------------------------------

INSTRUCAO_MACETE = """Voce recebe questoes reais de concurso publico brasileiro, da banca FEPESE, com o gabarito oficial ja conferido, todas da mesma materia.

Escreva macetes para estudar esta materia para a proxima prova da mesma banca.

Regras:
- cada macete e uma regra pratica curta, que ajuda a resolver questoes como
  estas - nao um resumo da materia;
- diga a FONTE de cada macete: o artigo da lei, assim: "art. 112 da Lei
  7.210/1984"; fora de Direito, a regra gramatical ou logica. Sem fonte
  segura, nao escreva o macete;
- a lei pode ter mudado depois da prova: cite o texto VIGENTE, e se a questao
  antiga ficou desatualizada, diga isso na regra;
- se houver uma pegadinha recorrente (a alternativa errada que a banca usa
  para enganar), descreva-a em "pegadinha"; se nao houver, responda "";
- em "questoes", cite os CODIGOS (ex.: "2019-q66") das questoes reais em que o
  macete se apoia. So codigos que estao neste pedido;
- no maximo %d macetes, os que mais ajudam.

Responda SOMENTE um JSON, no formato:
{"macetes": [{"assunto": "...", "regra": "...", "fonte": "art. 112 da Lei 7.210/1984", "pegadinha": "...", "questoes": ["2019-q66"]}]}""" % MACETES_POR_MATERIA


INSTRUCAO_EXPLICACAO = """Voce recebe UMA questao real de concurso publico brasileiro, da banca FEPESE, com o gabarito oficial ja conferido. Eu errei esta questao.

Explique por que a alternativa do gabarito oficial e a correta.

Regras:
- o gabarito oficial manda: explique a alternativa dele, e repita a letra dele
  no campo "correta". Se voce discordar do gabarito, NAO responda este pedido;
- diga a FONTE: o artigo da lei, assim: "art. 112 da Lei 7.210/1984"; fora de
  Direito, a regra gramatical ou logica. Sem fonte segura, nao responda;
- a lei pode ter mudado depois da prova: se o texto vigente mudou o gabarito,
  diga isso na explicacao;
- diga tambem por que a alternativa errada mais tentadora esta errada;
- curto: no maximo 5 frases.

Responda SOMENTE um JSON, no formato:
{"correta": "c", "explicacao": "...", "fonte": "art. 112 da Lei 7.210/1984"}"""


# A explicacao da questao real que e EXEMPLO de um tema do cronograma (R2): o
# "onde estava a pegadinha" do exemplo da ficha. Eu nao errei estas.
INSTRUCAO_EXPLICACAO_DO_TEMA = """Voce recebe UMA questao real da prova do meu cargo (Policia Penal / Agente Penitenciario de SC, banca FEPESE), com o gabarito oficial ja conferido. Ela e exemplo de um tema do meu cronograma.

Explique onde estava a pegadinha: por que a alternativa do gabarito oficial e a correta, e por que a errada mais tentadora esta errada.

Regras:
- o gabarito oficial manda: explique a alternativa dele, e repita a letra dele
  no campo "correta". Se voce discordar do gabarito, NAO responda este pedido;
- diga a FONTE: o artigo da lei, assim: "art. 112 da Lei 7.210/1984"; nas
  Regras de Mandela, "Regras de Mandela, regra 12.1"; fora de Direito, a regra
  gramatical ou logica. Sem fonte segura, nao responda;
- a lei pode ter mudado depois da prova: se o texto vigente mudou o gabarito,
  diga isso na explicacao;
- curto: no maximo 5 frases.

Responda SOMENTE um JSON, no formato:
{"correta": "c", "explicacao": "...", "fonte": "art. 112 da Lei 7.210/1984"}"""


INSTRUCAO_EXPLICACAO_DO_COMPLEMENTAR = INSTRUCAO_EXPLICACAO_DO_TEMA.replace(
    "UMA questao real da prova do meu cargo (Policia Penal / Agente Penitenciario "
    "de SC, banca FEPESE)",
    "UMA questao real de OUTRA prova da FEPESE (o acervo complementar: outro "
    "cargo, a mesma banca)",
).replace("Ela e exemplo de um tema do meu cronograma.",
          "O resumo de um tema do meu cronograma a cita como exemplo de como a "
          "banca cobra.")


INSTRUCAO_CLASSIFICACAO = """Voce recebe questoes reais da prova do meu cargo (Policia Penal / Agente Penitenciario de SC, banca FEPESE), com o gabarito oficial, todas da mesma materia, e a arvore de conteudos dessa materia.

Classifique cada questao na arvore: materia > assunto > subassunto > elemento.

Regras:
- o ASSUNTO e escolhido DENTRO da lista `assuntos_do_edital` do pedido, com o
  nome escrito exatamente como esta la. Assunto fora da lista sera RECUSADO;
- proponha o SUBASSUNTO (o tema dentro do assunto, ex.: "Lei penal no tempo")
  e, quando se aplicar, o ELEMENTO especifico cobrado (ex.: "CP, art. 2º"),
  com o `tipo_elemento` tirado da lista `elementos` do pedido e a `referencia`
  onde ler. Elemento sem subassunto sera recusado. Os dois sao opcionais:
  nao invente um para preencher;
- diga o `tipo_de_questao`, escolhido na lista `tipos_de_questao`;
- descreva a `pegadinha`: o que torna a alternativa errada atraente. Se nao
  houver, responda "";
- justifique: `trecho` (o pedaco do enunciado ou da alternativa que decide o
  assunto), `item_do_edital` (o item do edital, literal) e `dispositivo` (o
  artigo da lei; fora de Direito, a regra);
- SEM SEGURANCA, responda `"status": "pendente"` com o `motivo`. Pendente e
  uma resposta valida e honesta; uma classificacao forcada nao e;
- na materia FORA do edital atual (`fora_do_edital: true`), so use um assunto
  de outra materia do edital (campo `materia`, e o assunto da lista
  `outras_materias_do_edital`) se o item do edital justificar; senao,
  proponha o assunto debaixo da propria materia.

Responda SOMENTE um JSON, no formato:
{"classificacoes": [{"questao": "2019-q51", "status": "classificada", "assunto": "...", "subassunto": "...", "elemento": "...", "tipo_elemento": "artigo", "referencia": "CP, art. 2º", "tipo_de_questao": "literalidade da lei", "pegadinha": "...", "trecho": "...", "item_do_edital": "...", "dispositivo": "art. 2º do Código Penal"}]}"""


# Os conceitos ASSOCIADOS (§14, item 7 do novo.md): a questao ja tem o no
# principal, conferido; aqui se pede o que ELA TAMBEM cobra. Nunca entram na
# incidencia - la so conta a principal (decisao 86).
INSTRUCAO_ASSOCIADOS = """Voce recebe questoes reais da prova do meu cargo (Policia Penal / Agente Penitenciario de SC, banca FEPESE), cada uma com o no PRINCIPAL da arvore de conteudos em que ela ja foi classificada e conferida, e a arvore inteira (`arvore`).

Diga, para cada questao, os OUTROS conceitos que ela tambem cobra: os nos da arvore que aparecem no enunciado ou nas alternativas, alem do principal. E o que responde "quais conceitos aparecem associados".

Regras:
- use so nos da lista `arvore`, com o caminho escrito exatamente como esta la. No fora da lista sera RECUSADO;
- o associado e de assunto para baixo: a materia inteira nao e conceito;
- nunca o principal, nem um no acima ou abaixo dele: isso e o mesmo conceito;
- justifique cada um com o `trecho` da questao (do enunciado ou da alternativa) em que ele aparece;
- alternativa errada tambem conta: se ela fala de outro conceito, a questao o poe ao lado do principal;
- nao force: a questao que so cobra o principal responde "nos": []. Na duvida, deixe de fora.

Responda SOMENTE um JSON, no formato:
{"associados": [{"questao": "2019-q83", "nos": [{"no": "<caminho da arvore>", "trecho": "..."}]}]}"""



# A mesma tarefa, noutro acervo. O que muda e de QUEM e a prova, e para onde
# vai o numero: o complementar mostra o estilo da banca e NUNCA entra na
# incidencia da Policia Penal.
INSTRUCAO_CLASSIFICACAO_COMPLEMENTAR = INSTRUCAO_CLASSIFICACAO.replace(
    "Voce recebe questoes reais da prova do meu cargo (Policia Penal / Agente "
    "Penitenciario de SC, banca FEPESE), com o gabarito oficial, todas da mesma "
    "materia, e a arvore de conteudos dessa materia.",
    "Voce recebe questoes reais de OUTRO concurso da FEPESE (o acervo "
    "complementar: nao e a prova do meu cargo), com o gabarito, todas da mesma "
    "materia, e a arvore de conteudos dessa materia - a do MEU edital, que e "
    "onde elas serao penduradas. "
    "Isto serve para estudar o estilo da banca. O numero daqui vive numa linha "
    "separada e NUNCA e somado a incidencia da Policia Penal SC. Se o conteudo "
    "cobrado nao couber em nenhum assunto do meu edital, responda "
    '"status": "pendente" com o motivo - nao force.')


# No bloco generico a MATERIA tambem e pergunta: o caderno so diz
# "Conhecimentos Especificos", e a questao pode nem ser de materia minha.
INSTRUCAO_CLASSIFICACAO_GENERICA = """Voce recebe questoes reais de OUTRO concurso da FEPESE (o acervo complementar: nao e a prova do meu cargo), com o gabarito. O caderno NAO diz a materia delas: o bloco se chama "Conhecimentos Especificos" ou parecido. O nome do lote e so a suspeita que um termo levantou, e pode estar errado.

Para cada questao, diga em que materia DO MEU EDITAL ela cai, e classifique nela.

Regras:
- a MATERIA vai no campo `materia`, escrita exatamente como aparece em
  `outras_materias_do_edital`. O ASSUNTO e escolhido dentro da lista daquela
  materia, com o nome exatamente como esta la;
- **a questao que nao for de nenhuma materia do meu edital** (conteudo do
  cargo daquele concurso: pedagogia, enfermagem, contabilidade, informatica,
  atualidades...) recebe `"status": "pendente"` com o motivo. Isso e o
  esperado para a maioria: o termo so levantou suspeita. Nao force;
- no resto, valem as mesmas regras da classificacao normal: subassunto e
  elemento opcionais (elemento sem subassunto e recusado), `tipo_elemento` da
  lista `elementos`, `tipo_de_questao` da lista, `pegadinha`, e a
  justificativa com `trecho`, `item_do_edital` e `dispositivo`.

O numero daqui vive numa linha separada e NUNCA e somado a incidencia da Policia Penal SC.

Responda SOMENTE um JSON, no formato:
{"classificacoes": [{"questao": "2024-q31", "status": "classificada", "materia": "Direito Penal", "assunto": "...", "subassunto": "...", "tipo_de_questao": "conceito", "pegadinha": "...", "trecho": "...", "item_do_edital": "...", "dispositivo": "..."}]}"""


# A ficha de estudo (Etapa 6B, secao 11): o texto que o cronograma nao tem -
# o que ler, como pesquisar, o que entender e memorizar - e os nos da arvore
# que o tema cobre. O resto da ficha (incidencia, padroes, questoes reais,
# desempenho, prioridade) o radar calcula: a IA nao escreve numero do acervo.
INSTRUCAO_FICHA = """Voce recebe UM tema do meu cronograma de estudo para a Policia Penal SC (banca FEPESE): as faixas em que ele aparece, com o detalhe que o plano escreveu, os artigos-chave do dia quando houver, e a arvore de conteudos da materia, com quantas questoes reais o acervo tem em cada no (alvo = as provas do meu cargo; complementar = outras provas da FEPESE).

Escreva a FICHA DE ESTUDO do tema: o que eu preciso fazer para estudar exatamente isto, com comeco, meio e fim.

Regras:
- `nos`: os caminhos da arvore que este tema cobre, copiados EXATAMENTE da lista `arvore` do pedido. Escolha os nos do tema, e nao um no amplo que contenha outros temas (a materia inteira e recusada; um no dentro do outro tambem). Sem no que sirva, responda "nos": [] e diga por que - nao force. Justifique em `por_que_estes_nos`;
- `assunto` e `subassunto`: os nomes do edital, copiados da arvore (opcionais; subassunto exige assunto);
- `elemento`: a parte exata ("CF, art. 5º, caput e incisos I a XVI"; em Portugues, a regra; em Raciocinio, o tipo de problema), e `tipo_elemento` da lista `elementos`;
- `ler_exatamente`: o que ler, com os dispositivos e onde (o texto oficial, quando houver lei);
- `como_pesquisar`: 3 buscas para YouTube ou Google, do jeito que se digita;
- `entender`: os conceitos que eu preciso entender, curtos e objetivos;
- `memorizar`: o que decorar - prazos, fracoes, listas, excecoes -, com o dispositivo de cada um;
- `pegadinhas`: as confusoes comuns NESTE conteudo (o que costuma ser trocado ou invertido). NAO afirme o que a FEPESE faz: o padrao da banca sai do acervo, com o numero, e quem mostra e o sistema;
- `fonte_sugerida`: so quando NAO houver lei (Portugues, Raciocinio, doutrina): uma fonte de estudo, uma so;
- a lei pode ter mudado depois das provas de 2013 e 2019: escreva pelo texto VIGENTE e diga quando a mudanca importa;
- nada de previsao ("vai cair", "certamente", "a FEPESE sempre..."): sera RECUSADO;
- sem seguranca sobre um artigo ou um numero, nao escreva: um prazo errado ensina errado.

Responda SOMENTE um JSON, no formato:
{"ficha": {"tema": "...", "assunto": "...", "subassunto": "", "elemento": "...", "tipo_elemento": "...", "nos": ["..."], "por_que_estes_nos": "...", "ler_exatamente": "...", "como_pesquisar": ["..."], "entender": ["..."], "memorizar": ["..."], "pegadinhas": ["..."], "fonte_sugerida": ""}}"""


# O resumo do tema (R2, revisao final do estudo): o texto de uma tela para o
# caderno. A parte 1 (caiu ou nao caiu) o radar calcula na hora; a IA escreve
# as outras, e cada frase diz o que a sustenta.
INSTRUCAO_RESUMO = """Voce recebe UM tema do meu cronograma de estudo para a Policia Penal SC (banca FEPESE), com a ficha de estudo dele, o que as provas do meu cargo (2013 e 2019) mostram desse tema, as questoes reais do tema (com as alternativas e o gabarito oficial) e as de outras provas da FEPESE, separadas.

Escreva o RESUMO do tema: um texto curto, que caiba numa tela, para eu passar para o caderno antes da videoaula. Partes, nesta ordem:
- `dominar`: o que eu preciso dominar (3 a 6 frases curtas);
- `artigos`: os artigos ou regras-chave (2 a 6), cada um com o que ele diz;
- `como_cobra`: como a banca cobrou ESTE tema, so a partir das questoes reais do pedido, cada frase citando o codigo da questao ("2019-q51" nas provas do meu cargo; "FEPESE-2024-q8" nas outras provas da FEPESE, sempre com o prefixo, e dizendo que sao de outro concurso). Sem questao real no pedido, a parte e EXATAMENTE uma frase com o texto "{frase_sem_evidencia}" (com os acentos, igual) e a fonte "acervo";
- `pegadinhas`: as pegadinhas, cada uma com o codigo da questao real em que aparece; a confusao comum que nao vem de questao real leva a fonte "sem questão real";
- `basico`: SO quando o pedido diz que o tema NAO caiu: o basico do tema (2 a 4 frases). Quando caiu, nao escreva esta parte.

Regras:
- CADA frase tem `texto` e `fontes`: a lista do que a sustenta - o dispositivo ("CP, art. 13, § 2º"; "Regras de Mandela, regra 12.1"), a regra gramatical com a obra ("regra de concordancia - Pestana"), ou o codigo da questao real ("2013-q7"). Frase sem fonte sera RECUSADA;
- so cite questao que esta no pedido; ao citar o gabarito, escreva "2013-q7 (gabarito B)" e use a letra do gabarito oficial do pedido;
- escreva pelo texto VIGENTE da lei; se ela mudou depois da prova, diga isso na frase;
- nada de previsao ("vai cair", "certamente", "a FEPESE sempre..."): sera RECUSADO. O que a banca fez e o que as questoes do pedido mostram, e so;
- sem seguranca sobre um artigo, uma regra ou um numero, nao escreva a frase.

Responda SOMENTE um JSON, no formato:
{"resumo": {"dominar": [{"texto": "...", "fontes": ["..."]}], "artigos": [...], "como_cobra": [...], "pegadinhas": [...], "basico": [...]}}"""
# A frase do acervo mora so no origem.py (o teste dela vigia): entra aqui.
INSTRUCAO_RESUMO = INSTRUCAO_RESUMO.replace("{frase_sem_evidencia}", FRASE_SEM_EVIDENCIA)


def _como_responder(tipo: str) -> str:
    """O recado para quem responde. Vai dentro do arquivo, no topo."""
    if tipo == "resumos":
        return (
            "Este arquivo foi gerado por `radar fichas --pedido --resumos`. Para "
            "cada item de `pedidos`, siga a `instrucao` usando o texto de `pedido` "
            "e as listas do proprio item. Responda TODOS num unico arquivo JSON, "
            "no formato de `formato_da_resposta`: o mesmo `lote`, o `modelo` que "
            "escreveu (ex.: \"claude-opus-5-5\") e o `id` de cada pedido com o "
            "objeto `resumo` dele. Salve como data/resposta_ia.json e rode "
            "`radar fichas --importar data/resposta_ia.json`. Frase sem fonte, "
            "questao que nao esta no pedido, gabarito diferente do oficial, "
            "'como a banca cobra' sem questao real ou texto de previsao sera "
            "RECUSADO."
        )
    if tipo == "fichas":
        return (
            "Este arquivo foi gerado por `radar fichas --pedido`. Para cada item "
            "de `pedidos`, siga a `instrucao` usando o texto de `pedido` e as "
            "listas do proprio item. Responda TODOS num unico arquivo JSON, no "
            "formato de `formato_da_resposta`: o mesmo `lote`, e o `id` de cada "
            "pedido com o objeto `ficha` dele. Salve como data/resposta_ia.json e "
            "rode `radar fichas --importar data/resposta_ia.json`. Ficha com no "
            "fora da arvore, sem o que ler, sem como pesquisar, sem o que "
            "entender ou memorizar, ou com texto de previsao sera RECUSADA."
        )
    if tipo == "classificacao":
        return (
            "Este arquivo foi gerado por `radar classificar --pedido`. Para cada "
            "item de `pedidos`, siga a `instrucao` usando o texto de `pedido` e as "
            "listas do proprio item. Responda TODOS num unico arquivo JSON, no "
            "formato de `formato_da_resposta`: o mesmo `lote`, e o `id` de cada "
            "pedido com a lista `classificacoes` dele. Salve como "
            "data/resposta_ia.json e rode `radar classificar --importar "
            "data/resposta_ia.json`. Classificacao com assunto fora do edital, "
            "tipo fora da lista, sem justificativa, ou de questao que nao estava "
            "no pedido sera RECUSADA."
        )
    if tipo == "associados":
        return (
            "Este arquivo foi gerado por `radar classificar --pedido --associados`. "
            "Para cada item de `pedidos`, siga a `instrucao` usando o texto de "
            "`pedido` e a `arvore` do item. Responda TODOS num unico arquivo JSON, "
            "no formato de `formato_da_resposta`: o mesmo `lote`, e o `id` de cada "
            "pedido com a lista `associados` dele. Salve como data/resposta_ia.json "
            "e rode `radar classificar --importar data/resposta_ia.json`. No fora "
            "da arvore, a materia inteira, o ramo da principal, conceito sem "
            "`trecho` ou questao que nao estava no pedido serao RECUSADOS."
        )
    if tipo == "explicacoes":
        return (
            "Este arquivo foi gerado por `radar gerar --pedido --explicacoes`. "
            "Para cada item de `pedidos`, siga a `instrucao` usando o texto de "
            "`pedido`. Responda TODOS num unico arquivo JSON, no formato de "
            "`formato_da_resposta`: o mesmo `lote` deste arquivo, e o `id` de "
            "cada pedido com o objeto `explicacao` dele. Salve como "
            "data/resposta_ia.json e rode `radar gerar --importar "
            "data/resposta_ia.json`. Explicacao cuja `correta` nao for a letra "
            "do gabarito oficial, ou sem `fonte`, sera RECUSADA."
        )
    campo = "questoes" if tipo == "questoes" else "macetes"
    texto = (
        "Este arquivo foi gerado por `radar gerar --pedido`. Para cada item de "
        "`pedidos`, siga a `instrucao` usando o texto de `pedido`. Responda "
        "TODOS os pedidos num unico arquivo JSON, no formato de "
        "`formato_da_resposta`: o mesmo `lote` deste arquivo, e o `id` de cada "
        f"pedido com a lista `{campo}` dele. Salve como data/resposta_ia.json e "
        "rode `radar gerar --importar data/resposta_ia.json`. "
    )
    if tipo == "questoes":
        texto += (
            "Questao sem o artigo da lei no campo `artigo` sera RECUSADA - nas "
            "Regras de Mandela, que nao tem artigo, cite a regra pelo numero "
            "(\"Regras de Mandela, regra 12.1\"); fora "
            "de Direito (Portugues, Raciocinio Logico), ponha ali a regra em "
            "que a resposta se apoia. Se nao tiver certeza do artigo, nao "
            "escreva a questao: a instrucao diz para deixar vazio, mas aqui "
            "vazio e recusado. Escreva no maximo `quantas` questoes por pedido."
        )
    else:
        texto += (
            "Macete sem `fonte`, ou citando em `questoes` um codigo que nao "
            "esta no pedido, sera RECUSADO."
        )
    return texto


def _formato(tipo: str) -> dict:
    """O exemplo de resposta do lote, sempre com o `modelo`: e por ele que a
    procedencia diz quem escreveu (decisao 116). So o de resumos o tinha, e as
    82 geradas e 10 explicacoes de 06/10/2026 entraram sem o modelo."""
    formato = _formato_das_respostas(tipo)
    return {"lote": formato["lote"], "modelo": "<o modelo que escreveu>",
            **{chave: valor for chave, valor in formato.items() if chave != "lote"}}


def _formato_das_respostas(tipo: str) -> dict:
    if tipo == "resumos":
        frase = {"texto": "...", "fontes": ["CP, art. 13, § 2º", "2019-q51 (gabarito C)"]}
        item = {"dominar": [frase], "artigos": [frase], "como_cobra": [frase],
                "pegadinhas": [frase], "basico": []}
        return {"lote": "<o lote deste arquivo>", "modelo": "<o modelo que escreveu>",
                "respostas": [{"id": "r1", "resumo": item}]}
    if tipo == "fichas":
        item = {"tema": "<o tema do pedido>", "assunto": "...", "subassunto": "",
                "elemento": "...", "tipo_elemento": "...", "nos": ["..."],
                "por_que_estes_nos": "...", "ler_exatamente": "...",
                "como_pesquisar": ["..."], "entender": ["..."], "memorizar": ["..."],
                "pegadinhas": ["..."], "fonte_sugerida": ""}
        return {"lote": "<o lote deste arquivo>",
                "respostas": [{"id": "f1", "ficha": item}]}
    if tipo == "classificacao":
        item = {"questao": "2019-q51", "status": "classificada", "assunto": "...",
                "subassunto": "...", "elemento": "...", "tipo_elemento": "artigo",
                "referencia": "CP, art. 2º", "tipo_de_questao": "literalidade da lei",
                "pegadinha": "...", "trecho": "...", "item_do_edital": "...",
                "dispositivo": "art. 2º do Código Penal"}
        pendente = {"questao": "2019-q52", "status": "pendente", "motivo": "..."}
        return {"lote": "<o lote deste arquivo>",
                "respostas": [{"id": "c1", "classificacoes": [item, pendente]}]}
    if tipo == "associados":
        item = {"questao": "2019-q83",
                "nos": [{"no": "<caminho da arvore>", "trecho": "..."}]}
        return {"lote": "<o lote deste arquivo>",
                "respostas": [{"id": "a1", "associados": [item]}]}
    if tipo == "explicacoes":
        item = {"correta": "c", "explicacao": "...",
                "fonte": "art. 112 da Lei 7.210/1984"}
        return {"lote": "<o lote deste arquivo>",
                "respostas": [{"id": "e1", "explicacao": item}]}
    if tipo == "questoes":
        # `conteudo` so e exigido no pedido com escopo (Etapa 5), e esta no
        # formato sempre: mostrar o campo e o que faz a resposta vir com ele.
        item = {"enunciado": "...", "alternativas": {
            "a": "...", "b": "...", "c": "...", "d": "...", "e": "..."},
            "resposta": "c", "artigo": "art. 41, XV, da Lei 7.210/1984",
            "conteudo": "<copie o CONTEUDO do pedido, quando houver>"}
        return {"lote": "<o lote deste arquivo>",
                "respostas": [{"id": "p1", "questoes": [item]}]}
    item = {"assunto": "...", "regra": "...", "fonte": "art. 112 da Lei 7.210/1984",
            "pegadinha": "...", "questoes": ["2019-q66"]}
    return {"lote": "<o lote deste arquivo>",
            "respostas": [{"id": "m1", "macetes": [item]}]}


def _novo_lote(tipo: str, pedidos: list[dict]) -> dict:
    agora_ = agora()
    return {
        "lote": f"{tipo}-{agora_:%Y%m%d-%H%M%S}",
        "tipo": tipo,
        "criado_em": agora_.isoformat(),
        "como_responder": _como_responder(tipo),
        "formato_da_resposta": _formato(tipo),
        "pedidos": pedidos,
    }


# --- montar o pedido --------------------------------------------------------

#: O que entra no pedido quando ele tem ESCOPO (Etapa 5, secoes 7 a 9). A
#: ordem de nao sair do escopo e a parte que importa, e ela vem com a exigencia
#: de cada questao DECLARAR o no e o dispositivo: e declarando que a importacao
#: pode recusar o que saiu, e e isso que faz a garantia ser verificavel em vez
#: de confianca.
INSTRUCAO_DO_ESCOPO = """
ESCOPO FECHADO - a regra mais importante deste pedido:

- toda questao tem de estar DENTRO do conteudo indicado em CONTEUDO, abaixo.
  Nao escreva questao de outro assunto da mesma materia, nem de um assunto
  vizinho, nem de um tema mais amplo que contenha este;
- se o escopo listar DISPOSITIVOS, cada questao tem de cobrar um deles;
- em cada questao, responda tambem:
    "conteudo": o caminho do conteudo, copiado igual ao que esta em CONTEUDO
                (se CONTEUDO listar mais de um caminho, copie o da questao);
    "artigo":   o dispositivo em que ela se apoia ("LEP, art. 112"), ou "" se
                voce nao tiver certeza - artigo inventado e pior que nenhum;
- se voce nao conseguir escrever a quantidade pedida SEM sair do escopo,
  escreva menos questoes. Faltar questao e um problema pequeno; questao de
  outro assunto estraga o treino, porque eu vou estudar achando que e isto.
"""


def _instrucao_com_escopo(instrucao: str, escopo, lei=None) -> str:
    """A instrucao original mais o escopo, o dispositivo e o link oficial."""
    if escopo.elementos:
        from radar import conteudos as arvore

        # Com elemento pedido, o conteudo de cada questao e um dos elementos,
        # e nao o no de cima: a importacao recusa o subassunto e o irmao.
        linhas = [instrucao, INSTRUCAO_DO_ESCOPO,
                  "CONTEUDO (um destes caminhos):",
                  *[f"  {e}" for e in escopo.elementos]]
        nomes = [arvore.partes(e)[-1] for e in escopo.elementos]
        linhas.append(f"DISPOSITIVOS: {'; '.join(nomes)}")
    else:
        linhas = [instrucao, INSTRUCAO_DO_ESCOPO, f"CONTEUDO: {escopo.no}"]
    if lei is not None:
        linhas.append(f"FONTE OFICIAL: {lei.titulo}")
        if lei.url:
            linhas.append(f"TEXTO DA LEI: {lei.url}")
        if lei.nota:
            # A ressalva do config/leis.yml (lei revogada, data divergente): se
            # ela existe, a IA tem de saber antes de escrever a questao.
            linhas.append(f"ATENCAO: {lei.nota}")
    return "\n".join(linhas)


def pedido_de_questoes(materia: str | None = None, quantas: int = 5,
                       semente: int | None = None, escopo=None,
                       modo: str | None = None) -> dict:
    """Os mesmos pedidos que o `--valendo` mandaria a API, todos num lote.

    Sai do mesmo `geradas.preparar`: a escolha da questao de base, o modo do
    zero e a divisao em chamadas sao os de sempre. O que muda e so quem
    responde.
    """
    plano = geradas.preparar(materia, quantas, semente, escopo=escopo, modo=modo)
    pedidos = []
    for numero, pedido in enumerate(plano["pedidos"], start=1):
        se_escopo = pedido.get("escopo")
        if pedido["modo"] == "do_zero":
            instrucao = gerador.INSTRUCAO_DO_ZERO
            corpo = gerador._montar_pedido_do_zero(
                pedido["materia"], pedido.get("assunto"),
                pedido.get("exemplos") or [], pedido["quantas"],
            )
            base = {"materia": pedido["materia"], "assunto": pedido.get("assunto"),
                    "origem_impressao": None, "origem_chave": None}
        else:
            questao = pedido["questao"]
            instrucao = gerador.INSTRUCAO_VARIACAO
            corpo = gerador._montar_pedido_variacao(questao, pedido["quantas"])
            # Com escopo, a materia e o assunto vem do pedido (os do escopo);
            # no pedido amplo, sem escopo, continuam os da questao de base.
            base = {"materia": pedido.get("materia") or questao.materia,
                    "assunto": pedido.get("assunto") or getattr(questao, "assunto", None),
                    "origem_impressao": questao.impressao,
                    # A chave diz QUAL questao foi: o enunciado sozinho se
                    # repete em questoes diferentes da mesma prova.
                    "origem_chave": chave_da_questao(questao.enunciado,
                                                     questao.alternativas)}
        if se_escopo is not None:
            instrucao = _instrucao_com_escopo(instrucao, se_escopo,
                                              pedido.get("lei"))
        pedidos.append({
            "id": f"p{numero}", "modo": pedido["modo"],
            "quantas": pedido["quantas"], **base,
            # O escopo viaja NO PEDIDO, pelo caminho de nomes: e contra ele que
            # a importacao recusa questao de fora, e o arquivo do pedido e o
            # que fica para eu auditar depois.
            "modo_do_pedido": plano["modo_do_pedido"],
            "conteudo": pedido.get("conteudo"),
            "escopo": se_escopo.no if se_escopo is not None else None,
            "escopo_dispositivos": list(se_escopo.elementos) if se_escopo is not None else [],
            "base": pedido.get("base"),
            "evidencia_da_base": pedido.get("evidencia_da_base"),
            "instrucao": instrucao, "pedido": corpo,
        })
    return _novo_lote("questoes", pedidos)


def _codigo(questao) -> str:
    return f"{questao.ano}-q{questao.numero}"


def pedido_de_macetes(materia: str | None = None) -> dict:
    """Um pedido por materia, com as questoes reais do MEU cargo nela.

    So as provas do alvo (2013 e 2019), e nao o reforco: macete e sobre o que
    a banca cobra de mim. Anulada fica de fora - a banca disse que ela nao tem
    resposta certa, e um macete apoiado nela ensinaria o erro.
    """
    criar_tabelas()
    with sessao() as s:
        reais = geradas._reais_do_alvo(s, materia)

    por_materia: dict[str, list] = {}
    for q in sorted(reais, key=lambda q: (q.ano or 0, q.numero)):
        por_materia.setdefault(q.materia or "sem materia", []).append(q)

    pedidos = []
    for numero, (nome, questoes) in enumerate(sorted(por_materia.items()), start=1):
        citaveis, blocos = {}, []
        for q in questoes:
            codigo = _codigo(q)
            citaveis[codigo] = {"prova_url": q.prova_url, "numero": q.numero,
                                "impressao": q.impressao, "ano": q.ano}
            blocos.append(f"[{codigo}]\n{gerador._questao_por_extenso(q)}")
        corpo = (f"MATERIA: {nome}\n\nQUESTOES REAIS\n\n" + "\n\n".join(blocos)
                 + f"\n\nEscreva ate {MACETES_POR_MATERIA} macetes.")
        pedidos.append({
            "id": f"m{numero}", "materia": nome,
            "instrucao": INSTRUCAO_MACETE, "pedido": corpo,
            "citaveis": citaveis,
        })
    return _novo_lote("macetes", pedidos)


def pedido_de_explicacoes() -> dict:
    """Um pedido por questao real que eu errei na ultima vez que respondi.

    A lista e a mesma do [Revisar agora] - uma regra so para "errei" - e a
    questao que ja tem explicacao fica de fora: pedir duas vezes a mesma
    explicacao nao ensina nada novo.
    """
    from radar.models import QuestaoDeProva
    from radar.servico import simulado as treino

    ja_explicadas = set(carregar_explicacoes())
    criar_tabelas()
    with sessao() as s:
        questoes = [
            q for q in (s.get(QuestaoDeProva, qid) for qid in treino.questoes_erradas())
            if q is not None and q.resposta and q.impressao not in ja_explicadas
        ]
        pedidos = []
        vistos = set()
        for q in sorted(questoes, key=lambda q: (q.ano or 0, q.numero)):
            if q.impressao in vistos:
                continue
            vistos.add(q.impressao)
            pedidos.append({
                "id": f"e{len(pedidos) + 1}", "materia": q.materia,
                "impressao": q.impressao, "gabarito": q.resposta,
                "instrucao": INSTRUCAO_EXPLICACAO,
                "pedido": (f"MATERIA: {q.materia or 'nao informada'}\n\n"
                           f"QUESTAO ({q.banca or 'FEPESE'} {q.ano or ''})\n\n"
                           f"{gerador._questao_por_extenso(q, inteira=True)}"),
            })
    return _novo_lote("explicacoes", pedidos)


def pedido_de_explicacoes_dos_temas(desde=None) -> dict:
    """Um pedido por questao real do ALVO que e exemplo de um tema do
    cronograma (as que a ficha conta e as pendentes do tema), de `desde`
    (padrao: o comeco do plano) em diante, e que ainda nao tem explicacao
    (R2). E o mesmo lote "explicacoes", com a mesma importacao: o gabarito
    oficial manda e a fonte e obrigatoria."""
    from sqlalchemy import select

    from radar import fichas
    from radar.models import QuestaoDeProva
    from radar.servico import fichas as servico_fichas

    ctx = servico_fichas.contexto()
    ja_explicadas = set(carregar_explicacoes())
    temas_por_questao: dict[tuple, list[str]] = {}
    materia_da_ficha: dict[tuple, str] = {}
    for tema in fichas.temas_do_plano(ctx.plano, desde or ctx.plano.inicio):
        escrita = next((e for e in ctx.escritas if e.chave == fichas.chave_do_tema(tema.tema)
                        and e.materia == tema.materia), None)
        if escrita is None:
            continue
        for q in fichas.montar(escrita, ctx).exemplos:
            temas_por_questao.setdefault((q.prova, q.numero), []).append(escrita.tema)
            materia_da_ficha.setdefault((q.prova, q.numero), escrita.materia)
    criar_tabelas()
    pedidos = []
    with sessao() as s:
        for (prova, numero), temas in sorted(temas_por_questao.items(),
                                             key=lambda x: (x[0][0], x[0][1] or 0)):
            q = s.scalar(select(QuestaoDeProva).where(QuestaoDeProva.prova_url == prova)
                         .where(QuestaoDeProva.numero == numero))
            if q is None or not q.resposta or q.anulada or q.impressao in ja_explicadas:
                continue
            ja_explicadas.add(q.impressao)
            materia = materia_da_ficha.get((prova, numero)) or q.materia
            pedidos.append({
                "id": f"e{len(pedidos) + 1}", "materia": materia,
                "impressao": q.impressao, "gabarito": q.resposta,
                "codigo": f"{q.ano}-q{q.numero}", "temas": temas,
                "instrucao": INSTRUCAO_EXPLICACAO_DO_TEMA,
                "pedido": (f"TEMA: {'; '.join(temas)}\nMATERIA: {_materia_no_pedido(materia, q)}"
                           f"\n\nQUESTAO {q.ano}-q{q.numero} ({q.banca or 'FEPESE'} {q.ano or ''})"
                           f"\n\n{gerador._questao_por_extenso(q, inteira=True)}"),
            })
    return _novo_lote("explicacoes", pedidos)


def _materia_no_pedido(materia: str | None, q) -> str:
    """A materia da ficha, e a da prova quando o caderno escreve outra.

    A regra da fonte (`fonte_serve`) olha a materia do pedido, e o caderno do
    complementar chama Portugues de "Conhecimentos Especificos" (decisao 133):
    pela prova, a explicacao de crase exigiria artigo de lei. A ficha sabe a
    materia pela arvore; a da prova vai junto so para quem le o pedido.
    """
    if q.materia and q.materia != materia:
        return f"{materia or 'nao informada'} (na prova: {q.materia})"
    return materia or "nao informada"


def pedido_de_explicacoes_dos_resumos() -> dict:
    """Um pedido por questao do COMPLEMENTAR que algum resumo cita ("FEPESE-
    2024-q3") e que ainda nao tem explicacao (item 5, 06/10/2026). O resumo
    manda ler aquela questao como exemplo do padrao da banca; sem explicacao,
    ela e so um gabarito. O mesmo lote "explicacoes", com a mesma importacao."""
    from sqlalchemy import select

    from radar import fichas
    from radar.models import QuestaoDeProva
    from radar.servico import fichas as servico_fichas

    ctx = servico_fichas.contexto()
    ja_explicadas = set(carregar_explicacoes())
    temas_por_questao: dict[tuple, list[str]] = {}
    codigo_da_questao: dict[tuple, str] = {}
    materia_da_ficha: dict[tuple, str] = {}
    for escrita in ctx.escritas:
        if not escrita.resumo:
            continue
        citados = {codigo for frases in escrita.resumo.get("partes", {}).values()
                   for frase in frases for fonte in [frase.get("texto", "")] + frase.get("fontes", [])
                   for codigo in fichas.CODIGO_DA_QUESTAO.findall(fonte)
                   if codigo.startswith(fichas.PREFIXO_DO_COMPLEMENTAR)}
        if not citados:
            continue
        for q in fichas.montar(escrita, ctx).questoes_reais:
            codigo = fichas.codigo_citavel(q)
            if codigo in citados:
                temas_por_questao.setdefault((q.prova, q.numero), []).append(escrita.tema)
                codigo_da_questao[(q.prova, q.numero)] = codigo
                materia_da_ficha.setdefault((q.prova, q.numero), escrita.materia)
    criar_tabelas()
    pedidos = []
    with sessao() as s:
        for (prova, numero), temas in sorted(temas_por_questao.items(),
                                             key=lambda x: (x[0][0], x[0][1] or 0)):
            q = s.scalar(select(QuestaoDeProva).where(QuestaoDeProva.prova_url == prova)
                         .where(QuestaoDeProva.numero == numero))
            if q is None or not q.resposta or q.anulada or q.impressao in ja_explicadas:
                continue
            ja_explicadas.add(q.impressao)
            codigo = codigo_da_questao[(prova, numero)]
            materia = materia_da_ficha.get((prova, numero)) or q.materia
            pedidos.append({
                "id": f"e{len(pedidos) + 1}", "materia": materia,
                "impressao": q.impressao, "gabarito": q.resposta,
                "codigo": codigo, "temas": temas,
                "instrucao": INSTRUCAO_EXPLICACAO_DO_COMPLEMENTAR,
                "pedido": (f"TEMA: {'; '.join(temas)}\nMATERIA: {_materia_no_pedido(materia, q)}"
                           f"\n\nQUESTAO {codigo} ({q.banca or 'FEPESE'} {q.ano or ''}, "
                           f"{q.cargo or 'outro cargo'})"
                           f"\n\n{gerador._questao_por_extenso(q, inteira=True)}"),
            })
    return _novo_lote("explicacoes", pedidos)


def _materia_sugerida_por_termo():
    """Devolve f(questao) -> materia do edital que os termos sugerem, ou None.

    E so uma SUSPEITA, para agrupar o pedido em lotes do tamanho de uma
    leitura: o termo pode estar de passagem, e quem decide a materia e a
    classificacao. A lista mora no `config/complementar.yml`.
    """
    from radar import complementar as regra
    from radar.servico import complementar as acervo

    termos = {m: [regra.procurar(x) for x in ts if x]
              for m, ts in acervo.carregar_termos().items()}

    def sugerir(q):
        texto = regra.normalizar(
            (q.enunciado or "") + " "
            + " ".join(str(v) for v in (q.alternativas or {}).values()))
        for m, lista in termos.items():
            if any(b.search(texto) for b in lista):
                return m
        return None

    return sugerir


def pedido_de_classificacao(materia: str | list[str] | None = None,
                            de_evidencia: str | None = None,
                            genericos: bool = False) -> dict:
    """Um pedido por materia, com as questoes e a arvore dela.

    `de_evidencia` diz de onde vem a questao: `alvo` (o padrao: as 170 de
    2013 e 2019) ou `complementar` (as provas FEPESE aceitas no
    `data/acervo_complementar.json`; prova nao aceita nao e classificada).
    As duas nunca se misturam num lote, e o que a classificacao do
    complementar produz nunca entra na conta do alvo.

    Vao todas, anuladas inclusive (marcadas). Fica de fora so a que eu ja
    conferi - a conferencia e minha e nao se refaz por cima. A materia do
    caderno encontra o no pela regra dos textos antigos (igual, ou pelo
    sinonimo do config/taxonomia.yml).

    `genericos` inverte a seleção no complementar: em vez das questoes cujo
    caderno declara uma materia minha, pede as de BLOCO GENERICO - o caderno
    so diz "Conhecimentos Especificos" -, agrupadas pela materia que os termos
    do `config/complementar.yml` sugerem. Nelas, a materia tambem e pergunta:
    o pedido vai marcado `bloco_generico` e leva a arvore inteira, e a
    resposta diz em que materia a questao cai (ou que nao cai em nenhuma).
    """
    from sqlalchemy import select

    from radar import conteudos as arvore
    from radar.models import Classificacao, Conteudo, QuestaoDeProva
    from radar.servico import complementar as acervo
    from radar.servico import evidencia

    de_evidencia = de_evidencia or evidencia.ALVO
    if de_evidencia not in (evidencia.ALVO, evidencia.COMPLEMENTAR):
        raise ValueError(f"evidência {de_evidencia!r}: use alvo ou complementar")
    so_estas = ([materia] if isinstance(materia, str) else list(materia or [])) or None

    taxonomia = arvore.carregar_taxonomia()
    criar_tabelas()
    with sessao() as s:
        nos = list(s.scalars(select(Conteudo)))
        conferidas = set(s.scalars(
            select(Classificacao.chave)
            .where(Classificacao.principal.is_(True))
            .where(Classificacao.conferida_em.is_not(None))))
        consulta = (select(QuestaoDeProva)
                    .where(QuestaoDeProva.evidencia == de_evidencia)
                    .order_by(QuestaoDeProva.ano, QuestaoDeProva.numero))
        if de_evidencia == evidencia.COMPLEMENTAR:
            # Prova fora do acervo nao e classificada: seria dar a ela um
            # lugar na estatistica que a validacao negou.
            consulta = consulta.where(
                QuestaoDeProva.prova_url.in_(acervo.provas_aceitas()))
        questoes = list(s.scalars(consulta))

    if genericos and de_evidencia != evidencia.COMPLEMENTAR:
        raise ValueError("bloco genérico só existe no acervo complementar")

    caminhos = [n.caminho for n in nos]
    fora = {n.caminho for n in nos if n.nivel == "materia" and n.fora_do_edital}
    do_edital = {n.caminho: [x.nome for x in nos
                             if x.pai == n.caminho and x.origem == "edital"]
                 for n in nos if n.nivel == "materia" and not n.fora_do_edital}

    from radar.servico.classificacoes import chave_de

    por_materia: dict[str, list] = {}
    sugerida = _materia_sugerida_por_termo() if genericos else {}
    for q in questoes:
        if chave_de(q) in conferidas:
            continue
        no = (arvore.achar(caminhos, q.materia)
              or arvore.achar(caminhos, taxonomia.materia_do_texto(q.materia)))
        if genericos:
            # Aqui interessa justamente a questao SEM materia minha no
            # caderno; o termo so diz em que lote ela entra, e nao onde ela
            # sera pendurada - isso quem decide e a classificacao.
            if no is not None:
                continue
            no = sugerida(q)
            if no is None:
                continue
        elif no is None:
            continue
        if so_estas and no not in so_estas:
            continue
        por_materia.setdefault(no, []).append(q)

    pedidos = []
    for numero, (no, lista) in enumerate(por_materia.items(), start=1):
        blocos, codigos, ja_no_lote = [], {}, set()
        for q in lista:
            chave = chave_de(q)
            # A MESMA questao em dois cadernos (a FEPESE reaproveita) e uma
            # questao so para a classificacao, que trabalha por chave:
            # mandar as duas seria pedir o mesmo trabalho duas vezes.
            if chave in ja_no_lote:
                continue
            ja_no_lote.add(chave)
            codigo = _codigo(q)
            # Duas provas do mesmo ano no mesmo lote (acontece no
            # complementar) dariam o mesmo codigo, e a resposta ficaria
            # ambigua: um sufixo da prova desempata.
            if codigo in codigos:
                codigo = f"{codigo}-{sum(map(ord, q.prova_url)) % 1000:03d}"
            codigos[codigo] = chave
            marca = " (ANULADA pela banca: classifique assim mesmo)" if q.anulada else ""
            blocos.append(f"[{codigo}]{marca}\n{gerador._questao_por_extenso(q)}")
        dela = [c for c in caminhos if c == no or c.startswith(no + arvore.SEPARADOR)]
        item = {
            "id": f"c{numero}", "materia": no, "fora_do_edital": no in fora,
            "questoes": codigos,
            "assuntos_do_edital": do_edital.get(no, []),
            "arvore": dela,
            "elementos": taxonomia.elementos_da_materia(no),
            "tipos_de_questao": taxonomia.tipos_de_questao,
            "evidencia": de_evidencia,
            "bloco_generico": genericos,
            "instrucao": (INSTRUCAO_CLASSIFICACAO_GENERICA if genericos else
                          INSTRUCAO_CLASSIFICACAO
                          if de_evidencia == evidencia.ALVO
                          else INSTRUCAO_CLASSIFICACAO_COMPLEMENTAR),
            "pedido": f"MATERIA: {no}\n\nQUESTOES\n\n" + "\n\n".join(blocos),
        }
        if no in fora or genericos:
            item["outras_materias_do_edital"] = do_edital
        if genericos:
            # O caderno nao diz a materia: o nome do lote e so a SUSPEITA que
            # o termo levantou, e o pedido avisa isso.
            item["materia_sugerida_pelo_termo"] = no
            item["pedido"] = ("BLOCO GENÉRICO (o caderno não diz a matéria). "
                              f"Termo sugeriu: {no}\n\nQUESTOES\n\n"
                              + "\n\n".join(blocos))
        pedidos.append(item)
    return _novo_lote("classificacao", pedidos)


def pedido_de_fichas(materia: str | None = None, desde=None,
                     refazer: bool = False) -> dict:
    """Um pedido por tema do cronograma que ainda nao tem ficha (Etapa 6B).

    O pedido leva o que o Claude Code precisa para escrever SEM inventar: as
    faixas do tema com o detalhe do plano, os artigos-chave do dia, a arvore da
    materia com quantas questoes reais o acervo tem em cada no (alvo e
    complementar separados, nunca somados), os tipos de elemento e o link da
    lei. `refazer` inclui o tema cuja ficha eu ainda nao conferi; a conferida
    nunca volta.
    """
    from radar import conteudos as arvore
    from radar import cronograma as plano_de_estudo
    from radar import fichas
    from radar import incidencia
    from radar.servico import conteudos as servico_conteudos
    from radar.servico import cronograma as diario
    from radar.servico import fichas as servico_fichas
    from radar.servico import incidencia as servico_incidencia

    plano = plano_de_estudo.carregar()
    desde = desde or diario.hoje_local()
    escritas = servico_fichas.carregar()
    if refazer:
        conferidas = {(e.chave, e.materia) for e in escritas if e.conferida_em}
        temas = [t for t in fichas.temas_do_plano(plano, desde)
                 if (fichas.chave_do_tema(t.tema), t.materia) not in conferidas]
    else:
        temas = servico_fichas.sem_ficha(plano, desde, escritas)
    if materia:
        temas = [t for t in temas if t.materia == materia]

    nos = servico_conteudos.nos()
    mapa = {linha.caminho: len(linha.questoes)
            for m in incidencia.montar(nos, servico_incidencia.ocorrencias())
            for linha in m.linhas}
    complementar = incidencia.complementar_por_no(
        nos, servico_incidencia.ocorrencias_complementares())
    taxonomia = arvore.carregar_taxonomia()

    pedidos = []
    for numero, tema in enumerate(temas, start=1):
        faixas = [{"data": f.data.isoformat(), "bloco": f.bloco, "tipo": f.faixa.tipo,
                   "titulo": f.faixa.titulo, "questoes": f.faixa.questoes,
                   "detalhe": f.faixa.detalhe, "filtro": f.faixa.filtro,
                   "link": f.faixa.link}
                  for f in tema.faixas]
        artigos = []
        estudo = tema.estudo()
        if estudo is not None and estudo.faixa.tipo == "teoria":
            dia = plano.dia(estudo.data)
            if dia is not None and dia.essencial is not None:
                artigos = [{"artigos": a.artigos, "porque": a.porque}
                           for a in dia.essencial.chave + dia.essencial.apoio]
        da_materia = [n for n in nos if n.caminho == tema.materia
                      or n.caminho.startswith(tema.materia + arvore.SEPARADOR)]
        arvore_do_pedido = [
            {"caminho": n.caminho, "nivel": n.nivel,
             "alvo": mapa.get(n.caminho, 0),
             "complementar": complementar[n.caminho].questoes
             if n.caminho in complementar else 0}
            for n in da_materia]
        lei = leis.da_materia(tema.materia)
        corpo = [f"TEMA: {tema.tema}", f"MATERIA: {tema.materia}", "", "FAIXAS"]
        for f in faixas:
            corpo.append(f"- {f['data']} ({f['tipo']}): {f['titulo']}"
                         + (f" | {f['questoes']} questoes" if f["questoes"] else "")
                         + (f"\n  {f['detalhe']}" if f["detalhe"] else ""))
        if artigos:
            corpo += ["", "ARTIGOS-CHAVE DO DIA (selecao do plano, nao incidencia)"]
            corpo += [f"- {a['artigos']}: {a['porque']}" for a in artigos]
        corpo += ["", "ARVORE (alvo / complementar)"]
        corpo += [f"- {n['caminho']} [{n['nivel']}] ({n['alvo']} / {n['complementar']})"
                  for n in arvore_do_pedido]
        pedidos.append({
            "id": f"f{numero}", "tema": tema.tema, "materia": tema.materia,
            "faixas": faixas, "artigos_chave": artigos,
            "arvore": arvore_do_pedido,
            "elementos": taxonomia.elementos_da_materia(tema.materia),
            "lei": {"titulo": lei.titulo, "url": lei.url} if lei else None,
            "instrucao": INSTRUCAO_FICHA,
            "pedido": "\n".join(corpo),
        })
    return _novo_lote("fichas", pedidos)


#: Quantas questoes do complementar vao no pedido do resumo: bastam para
#: mostrar o jeito da banca, e o pedido continua lendo-se de uma vez.
COMPLEMENTARES_NO_RESUMO = 8


def pedido_de_resumos(ids: list[str] | None = None, desde=None,
                      refazer: bool = False) -> dict:
    """Um pedido de RESUMO por tema (R2). Sem `ids`, os temas do cronograma
    de `desde` (padrao: o comeco do plano) em diante que ainda nao tem
    resumo; `refazer` inclui o que tem resumo que eu ainda nao conferi.

    O pedido leva o que o resumo precisa para nao inventar: a ficha, o que as
    provas do alvo mostram do tema (a frase e prova a prova), as questoes
    reais do tema inteiras, com o gabarito oficial, e as do complementar,
    separadas; os artigos-chave do dia; e a lista dos codigos que o resumo
    pode citar - que a importacao confere.
    """
    from radar import fichas
    from radar.servico import fichas as servico_fichas

    ctx = servico_fichas.contexto()
    plano = ctx.plano
    if ids:
        escolhidas = [e for e in (servico_fichas.achar(i, ctx.escritas) for i in ids) if e]
    else:
        desde = desde or plano.inicio
        temas = fichas.temas_do_plano(plano, desde)
        por_chave = {(e.chave, e.materia): e for e in ctx.escritas}
        escolhidas = [por_chave[(fichas.chave_do_tema(t.tema), t.materia)] for t in temas
                      if (fichas.chave_do_tema(t.tema), t.materia) in por_chave]
    if not refazer:
        escolhidas = [e for e in escolhidas if not e.resumo]
    else:
        escolhidas = [e for e in escolhidas
                      if not (e.resumo and e.resumo.get("conferido_em"))]

    def questao(q) -> str:
        alternativas = "\n".join(f"   ({letra}) {texto}" for letra, texto in q.alternativas)
        extra = ""
        if q.como == "pendente":
            extra = " [classificação pendente: o artigo gravado é do tema]"
        elif q.como == "artigo":
            extra = " [contada pelo artigo gravado na classificação]"
        partes = [f"- {fichas.codigo_citavel(q)}{extra} · gabarito oficial: "
                  f"{(q.resposta or '?').upper()}",
                  f"   {q.enunciado}", alternativas]
        if q.pegadinha:
            partes.append(f"   pegadinha (classificação): {q.pegadinha}")
        for mud in q.mudancas:
            partes.append(f"   a lei mudou depois desta prova: {mud.tema} ({mud.lei})")
        return "\n".join(p for p in partes if p)

    pedidos = []
    for numero, escrita in enumerate(escolhidas, start=1):
        ficha = fichas.montar(escrita, ctx)
        exige = servico_fichas.exigencias_do_resumo(ficha)
        compl = [q for q in ficha.questoes_reais if q.evidencia == "complementar"
                 and fichas.codigo_citavel(q) in exige["codigos"]][:COMPLEMENTARES_NO_RESUMO]
        citaveis = {fichas.codigo_citavel(q): exige["codigos"][fichas.codigo_citavel(q)]
                    for q in list(ficha.exemplos) + compl
                    if fichas.codigo_citavel(q) in exige["codigos"]}
        caiu = ficha.caiu
        corpo = [f"TEMA: {escrita.tema}", f"MATERIA: {escrita.materia}",
                 "CAMINHO: " + " > ".join(ficha.caminho_exibido), "",
                 "AS PROVAS DO MEU CARGO (Polícia Penal SC, 2013 e 2019)",
                 f"- {caiu.frase}"]
        if not caiu.sem_contagem:
            corpo.append(f"- prova a prova: {caiu.por_prova}")
        corpo += [f"- {n}" for n in caiu.notas]
        corpo.append("- O TEMA " + ("CAIU: não escreva 'basico'." if exige["caiu"] else
                                    ("NÃO CAIU nas provas que bastam: escreva 'basico'."
                                     if exige["basico_obrigatorio"] else
                                     "não tem base para dizer que caiu ou não: "
                                     "'basico' é opcional.")))
        corpo += ["", "A FICHA (texto de IA, por conferir)",
                  f"- ler exatamente: {escrita.ler_exatamente}"]
        corpo += [f"- entender: {t}" for t in escrita.entender]
        corpo += [f"- memorizar: {t}" for t in escrita.memorizar]
        corpo += [f"- confusão comum: {t}" for t in escrita.pegadinhas]
        if ficha.artigos_chave:
            corpo += ["", "ARTIGOS-CHAVE DO DIA (seleção do plano)"]
            corpo += [f"- {a.artigos}: {a.porque}" for a in ficha.artigos_chave]
        corpo += ["", "QUESTÕES REAIS DO TEMA — Polícia Penal SC"]
        corpo += [questao(q) for q in ficha.exemplos] or ["- nenhuma"]
        corpo += ["", "QUESTÕES DE OUTRAS PROVAS DA FEPESE (complementar aceito; "
                  "nunca somadas às do meu cargo)"]
        corpo += [questao(q) for q in compl] or ["- nenhuma"]
        corpo += ["", "CÓDIGOS QUE O RESUMO PODE CITAR: "
                  + (", ".join(citaveis) or "nenhum (o tema não tem questão real: "
                     "'como_cobra' é a frase de evidência insuficiente)")]
        pedidos.append({
            "id": f"r{numero}", "tema": escrita.tema, "materia": escrita.materia,
            "ficha": escrita.id, "codigos": citaveis, "caiu": exige["caiu"],
            "basico_obrigatorio": exige["basico_obrigatorio"],
            "exige_artigo": exige["exige_artigo"],
            "instrucao": INSTRUCAO_RESUMO, "pedido": "\n".join(corpo),
        })
    return _novo_lote("resumos", pedidos)


def _importar_fichas(lote: dict, respostas: list[dict], modelo: str) -> dict:
    from radar.servico import fichas as servico_fichas

    return servico_fichas.importar_respostas(lote["pedidos"], respostas, modelo)


def pedido_de_associados(materia: str | list[str] | None = None) -> dict:
    """O pedido dos conceitos ASSOCIADOS (§14, item 7): para cada questao do
    alvo que ja tem a classificacao principal (e nao pendente), os outros nos
    que ela tambem cobra. Um pedido por materia da principal, com a arvore
    inteira - o associado pode morar noutra materia.

    A conferida entra: o associado nao mexe na principal, que e o que a
    conferencia protege.
    """
    from sqlalchemy import select

    from radar import conteudos as arvore
    from radar.models import Classificacao, Conteudo, QuestaoDeProva
    from radar.servico import evidencia
    from radar.servico.classificacoes import PENDENTE, chave_de

    so_estas = ([materia] if isinstance(materia, str) else list(materia or [])) or None
    criar_tabelas()
    with sessao() as s:
        caminhos = sorted(s.scalars(select(Conteudo.caminho)))
        principais = {c.chave: c.conteudo for c in s.scalars(
            select(Classificacao).where(Classificacao.principal.is_(True))
            .where(Classificacao.status != PENDENTE))}
        questoes = list(s.scalars(
            select(QuestaoDeProva).where(QuestaoDeProva.evidencia == evidencia.ALVO)
            .order_by(QuestaoDeProva.ano, QuestaoDeProva.numero)))

    por_materia: dict[str, list] = {}
    for q in questoes:
        principal = principais.get(chave_de(q))
        if principal is None:
            continue
        da_materia = arvore.partes(principal)[0]
        if so_estas and da_materia not in so_estas:
            continue
        por_materia.setdefault(da_materia, []).append((q, principal))

    pedidos = []
    for numero, (da_materia, lista) in enumerate(sorted(por_materia.items()), start=1):
        blocos, codigos, principal_de, ja = [], {}, {}, set()
        for q, principal in lista:
            chave = chave_de(q)
            if chave in ja:
                continue          # a mesma questao em dois cadernos e uma so
            ja.add(chave)
            codigo = _codigo(q)
            if codigo in codigos:
                codigo = f"{codigo}-{sum(map(ord, q.prova_url)) % 1000:03d}"
            codigos[codigo] = chave
            principal_de[codigo] = principal
            blocos.append(f"[{codigo}] PRINCIPAL: {principal}\n"
                          f"{gerador._questao_por_extenso(q)}")
        pedidos.append({
            "id": f"a{numero}", "materia": da_materia,
            "questoes": codigos, "principais": principal_de,
            "arvore": caminhos,
            "instrucao": INSTRUCAO_ASSOCIADOS,
            "pedido": f"MATERIA: {da_materia}\n\nQUESTOES\n\n" + "\n\n".join(blocos),
        })
    return _novo_lote("associados", pedidos)


def _importar_associados(lote: dict, respostas: list[dict], modelo: str) -> dict:
    from radar.servico import classificacoes

    por_id = {p["id"]: p for p in lote["pedidos"]}
    gravadas, recusas, vistas = 0, [], set()
    for resposta in respostas:
        pedido = por_id.get(resposta.get("id"))
        if pedido is None:
            recusas.append(f"{resposta.get('id')}: nao existe esse pedido no lote")
            continue
        for item in resposta.get("associados") or []:
            if not isinstance(item, dict):
                continue
            codigo = item.get("questao")
            if (pedido["id"], codigo) in vistas:
                recusas.append(f"{pedido['id']}/{codigo}: respondida duas vezes")
                continue
            vistas.add((pedido["id"], codigo))
            try:
                gravadas += classificacoes.aplicar_associados(item, pedido, modelo)
            except classificacoes.PropostaRecusada as erro:
                recusas.append(str(erro))
    if gravadas:
        classificacoes.exportar()
    return {"gravadas": gravadas, "repetidas": 0, "recusas": recusas}


def _importar_classificacao(lote: dict, respostas: list[dict], modelo: str) -> dict:
    from radar.servico import classificacoes

    por_id = {p["id"]: p for p in lote["pedidos"]}
    gravadas, recusas, vistas = 0, [], set()
    sem_materia = []
    for resposta in respostas:
        pedido = por_id.get(resposta.get("id"))
        if pedido is None:
            recusas.append(f"{resposta.get('id')}: nao existe esse pedido no lote")
            continue
        for item in resposta.get("classificacoes") or []:
            if not isinstance(item, dict):
                continue
            # O codigo ("2024-q29") so e unico DENTRO de um pedido: dois
            # lotes podem ter questoes diferentes com o mesmo ano e numero,
            # vindas de provas diferentes. A repeticao se conta por pedido.
            codigo = item.get("questao")
            if (pedido["id"], codigo) in vistas:
                recusas.append(f"{pedido['id']}/{codigo}: classificada duas vezes na resposta")
                continue
            vistas.add((pedido["id"], codigo))
            try:
                classificacoes.aplicar_proposta(item, pedido, modelo)
                gravadas += 1
            except classificacoes.PendenteSemMateria as fora:
                sem_materia.append(str(fora))
            except classificacoes.PropostaRecusada as erro:
                recusas.append(str(erro))
    if gravadas:
        classificacoes.exportar()
    return {"gravadas": gravadas, "repetidas": 0, "recusas": recusas,
            "fora_do_edital": sem_materia}


def salvar_pedido(lote: dict, caminho: Path | None = None) -> Path:
    destino = caminho or caminho_do_pedido()
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps(lote, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return destino


# --- ler a resposta de volta ------------------------------------------------

# "art. 41", "arts. 5º e 6º", "artigo 112", "Súmula Vinculante 56" - e "regra
# 12.1": as Regras de Mandela, que o edital cobra em Direitos Humanos, nao tem
# artigo, e se citam pela regra (decisao 76). Sem o numero, nao serve: "conforme
# as Regras de Mandela" continua recusado, como "conforme a doutrina".
# "§ 5" sozinho tambem cita: a Declaracao de Viena (1993) e numerada por
# paragrafo, e nao por artigo - chamar o § 5 de "art. 5º" para passar aqui
# seria citar errado (R2, a mesma ideia da "regra 12" de Mandela, decisao 76).
CITA_ARTIGO = re.compile(r"(?i)\bart(?:igo)?s?\.?\s*\d|\bs[uú]mula\b|\bregras?\s+\d|§\s*\d")


def fonte_serve(fonte: str | None, materia: str | None) -> bool:
    fonte = " ".join((fonte or "").split())
    if not fonte:
        return False
    return bool(CITA_ARTIGO.search(fonte)) if leis.exige_artigo(materia) else True


def _ler_json(texto: str) -> dict:
    """O JSON da resposta, mesmo cercado de crase tripla ou de uma frase."""
    achado = re.search(r"\{.*\}", texto or "", re.DOTALL)
    if not achado:
        raise ValueError("a resposta nao tem JSON nenhum")
    try:
        return json.loads(achado.group(0))
    except json.JSONDecodeError as erro:
        raise ValueError(f"a resposta nao e um JSON valido ({erro})") from erro


def _fora_do_escopo(pedido: dict, item: dict, conferida: dict,
                    caminhos: set[str] | None = None) -> str | None:
    """Por que esta questao nao entra. None quando ela esta dentro.

    As recusas do roteiro da Etapa 5, e as duas da auditoria de 04/10:

      * **o no declarado nao esta dentro do escopo pedido.** E a recusa
        principal: ela e o que faz a §8 ("nenhuma questao fora do escopo") ser
        verificavel, e nao uma promessa. **Com elemento pedido, o escopo sao
        os elementos**, e nao o subassunto de cima: pedi o art. 26 e a
        questao declara o art. 24, irmao dele, esta fora - mesmo citando o
        numero 26. Para elemento que nao e artigo (regra, tratado), e so isto
        que separa o pedido do vizinho;
      * **o no declarado tem de existir na arvore** (`caminhos`). Um caminho
        que comeca certo e termina num no inventado gravaria um vinculo que
        nao existe (regra inviolavel 9);
      * **com dispositivo pedido, o artigo citado tem de bater.** Pedi o art.
        119 e a questao cita o 112: nao serve, ainda que o assunto seja o mesmo;
      * **`origem_impressao` so se a questao real estava no pedido** - a §9
        proibe inventar vinculo com questao real;
      * **`do_zero` so com a marca "sem questao real de referencia"**, que aqui
        e `evidencia_da_base: nenhuma`.

    Pedido sem escopo (o simulado amplo de sempre) nao passa por nada disto: ele
    nao fechou escopo nenhum, e inventar um agora mudaria o que eu pedi.
    """
    from radar import conteudos as arvore

    escopo = pedido.get("escopo")

    # As duas recusas que valem com escopo ou sem ele: elas sao sobre a BASE.
    if pedido["modo"] == "variacao" and not pedido.get("origem_impressao"):
        return "variacao sem a questao real de base no pedido"
    if pedido["modo"] == "do_zero":
        if pedido.get("origem_impressao"):
            return "do_zero com vinculo a questao real, que o pedido nao tinha"
        if escopo and pedido.get("evidencia_da_base") != "nenhuma":
            return ("do_zero sem a marca \"sem questao real de referencia\" "
                    "(evidencia_da_base)")

    if not escopo:
        return None

    declarado = " ".join((item.get("conteudo") or "").split())
    if not declarado:
        return "a questao nao declarou o conteudo dela"
    dispositivos = pedido.get("escopo_dispositivos") or []
    # A mesma regra do `Escopo.dentro`: com elemento pedido valem os
    # elementos (e o que houver abaixo deles); sem elemento, o no e tudo abaixo.
    alvos = dispositivos or [escopo]
    dentro = any(declarado == alvo or declarado.startswith(alvo + arvore.SEPARADOR)
                 for alvo in alvos)
    if not dentro:
        if dispositivos:
            nomes = "; ".join(arvore.partes(d)[-1] for d in dispositivos)
            return (f"o conteudo declarado {declarado!r} nao e nenhum dos "
                    f"elementos pedidos: {nomes}")
        return f"o conteudo declarado {declarado!r} esta fora de {escopo!r}"
    if caminhos is not None and declarado not in caminhos:
        return f"o conteudo declarado {declarado!r} nao existe na arvore"

    if dispositivos:
        citado = normalizar(conferida.get("artigo") or "")
        nomes = [arvore.partes(d)[-1] for d in dispositivos]
        # Bate quando o numero do dispositivo aparece no artigo citado: a IA
        # escreve "LEP, art. 119" ou "art. 119 da Lei 7.210/1984", e as duas
        # formas sao a mesma coisa. O que nao vale e citar outro artigo.
        if not any(_mesmo_dispositivo(nome, citado) for nome in nomes):
            return (f"o artigo citado ({conferida.get('artigo') or 'nenhum'}) "
                    f"nao e nenhum dos pedidos: {'; '.join(nomes)}")
    return None


#: "LEP, art. 119" -> "119"; "CP, art. 2º" -> "2". E o numero que identifica o
#: dispositivo: o resto e como cada um escreve o nome da lei.
_NUMERO_DO_ARTIGO = re.compile(r"art\.?\s*([0-9]+)\s*(?:-\s*([a-z]))?", re.I)


def _mesmo_dispositivo(pedido: str, citado: str) -> bool:
    """O artigo citado e o pedido? Compara pelo NUMERO, nao pelo texto."""
    do_pedido = _NUMERO_DO_ARTIGO.search(normalizar(pedido))
    if not do_pedido:
        # Elemento que nao e artigo (regra gramatical, tipo de problema): a
        # conferencia pelo numero nao se aplica, e o no declarado ja garantiu
        # o escopo.
        return True
    numero = do_pedido.group(1)
    letra = do_pedido.group(2)
    for achado in _NUMERO_DO_ARTIGO.finditer(citado):
        if achado.group(1) == numero and (achado.group(2) or None) == (letra or None):
            return True
    return False


def _importar_questoes(lote: dict, respostas: list[dict], modelo: str) -> dict:
    por_id = {p["id"]: p for p in lote["pedidos"]}
    aceitas, recusas = [], []
    from radar.servico import conteudos as servico_conteudos

    # A arvore, lida uma vez: so e preciso quando algum pedido fechou escopo.
    caminhos = (set(servico_conteudos.caminhos())
                if any(p.get("escopo") for p in lote["pedidos"]) else None)

    for resposta in respostas:
        pedido = por_id.get(resposta.get("id"))
        if pedido is None:
            recusas.append(f"{resposta.get('id')}: nao existe esse pedido no lote")
            continue
        itens = [i for i in resposta.get("questoes") or [] if isinstance(i, dict)]
        for posicao, item in enumerate(itens, start=1):
            onde = f"{pedido['id']}, questao {posicao}"
            if posicao > pedido["quantas"]:
                recusas.append(f"{onde}: o pedido era de {pedido['quantas']}")
                continue
            conferida = gerador._conferir(item)
            if conferida is None:
                recusas.append(f"{onde}: sem as 5 alternativas ou sem gabarito valido")
                continue
            if not fonte_serve(conferida["artigo"], pedido.get("materia")):
                recusas.append(f"{onde}: sem o artigo da lei em que se apoia")
                continue

            # As recusas de ESCOPO (Etapa 5). A garantia da §8 e esta: a IA
            # DECLARA o no e o dispositivo, e aqui se confere o que ela
            # declarou. Nada e corrigido para caber - o que saiu do escopo e
            # recusado e contado na saida.
            fora = _fora_do_escopo(pedido, item, conferida, caminhos)
            if fora:
                recusas.append(f"{onde}: {fora}")
                continue

            aceitas.append(gerador.QuestaoNova(
                modo=pedido["modo"], materia=pedido.get("materia"),
                assunto=pedido.get("assunto"),
                origem_impressao=pedido.get("origem_impressao"),
                origem_chave=pedido.get("origem_chave"),
                modelo=modelo,
                modo_do_pedido=pedido.get("modo_do_pedido"),
                conteudo=item.get("conteudo") or pedido.get("conteudo"),
                escopo=pedido.get("escopo"),
                base=pedido.get("base"),
                evidencia_da_base=pedido.get("evidencia_da_base"),
                **conferida,
            ))

    # Repetida dentro da resposta, ou ja gerada antes: nao entra duas vezes.
    gravadas = geradas.gravar(aceitas)
    repetidas = len(aceitas) - gravadas
    if gravadas:
        from radar import acervo

        acervo.exportar_geradas()
    return {"gravadas": gravadas, "repetidas": repetidas, "recusas": recusas}


def _impressao_do_macete(materia: str, regra: str) -> str:
    return hashlib.md5(
        f"{normalizar(materia)}|{normalizar(regra)}".encode("utf-8")
    ).hexdigest()


def carregar_macetes(caminho: Path | None = None) -> list[dict]:
    origem = caminho or caminho_dos_macetes()
    if not origem.exists():
        return []
    return json.loads(origem.read_text(encoding="utf-8")) or []


def gravar_macetes(novos: list[dict], caminho: Path | None = None) -> int:
    """Junta os macetes novos ao arquivo. Devolve quantos entraram.

    A mesma trava da questao gerada: macete sem `modelo` e `criado_em` nao
    entra, e o lote inteiro para.
    """
    if any(not m.get("modelo") or not m.get("criado_em") for m in novos):
        raise ValueError("macete sem procedencia nao e gravado: diga de onde veio")

    destino = caminho or caminho_dos_macetes()
    existentes = carregar_macetes(destino)
    vistos = {m.get("impressao") for m in existentes}
    entraram = 0
    for macete in novos:
        if macete["impressao"] in vistos:
            continue
        vistos.add(macete["impressao"])
        existentes.append(macete)
        entraram += 1

    existentes.sort(key=lambda m: (m.get("materia") or "", m.get("criado_em") or ""))
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps(existentes, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return entraram


def _importar_macetes(lote: dict, respostas: list[dict], modelo: str) -> dict:
    por_id = {p["id"]: p for p in lote["pedidos"]}
    aceitos, recusas = [], []
    quando = agora().isoformat()

    for resposta in respostas:
        pedido = por_id.get(resposta.get("id"))
        if pedido is None:
            recusas.append(f"{resposta.get('id')}: nao existe esse pedido no lote")
            continue
        itens = [i for i in resposta.get("macetes") or [] if isinstance(i, dict)]
        for posicao, item in enumerate(itens, start=1):
            onde = f"{pedido['id']} ({pedido['materia']}), macete {posicao}"
            if posicao > MACETES_POR_MATERIA:
                recusas.append(f"{onde}: o pedido era de ate {MACETES_POR_MATERIA}")
                continue
            regra = " ".join(str(item.get("regra") or "").split())
            fonte = " ".join(str(item.get("fonte") or "").split())
            codigos = [str(c) for c in item.get("questoes") or []]
            if len(regra) < 20:
                recusas.append(f"{onde}: sem regra")
                continue
            if not fonte_serve(fonte, pedido["materia"]):
                recusas.append(f"{onde}: sem a fonte (o artigo da lei)")
                continue
            # A pegadinha vira link para as questoes reais. Codigo que nao
            # foi enviado seria um link para uma questao que nao existe.
            citaveis = pedido.get("citaveis") or {}
            if not codigos or any(c not in citaveis for c in codigos):
                recusas.append(f"{onde}: cita questao que nao estava no pedido")
                continue
            aceitos.append({
                "materia": pedido["materia"],
                "assunto": " ".join(str(item.get("assunto") or "").split()) or None,
                "regra": regra,
                "fonte": fonte,
                "pegadinha": " ".join(str(item.get("pegadinha") or "").split()) or None,
                "questoes": [{"codigo": c, **citaveis[c]} for c in codigos],
                "modelo": modelo,
                "criado_em": quando,
                "impressao": _impressao_do_macete(pedido["materia"], regra),
            })

    gravados = gravar_macetes(aceitos) if aceitos else 0
    return {"gravadas": gravados, "repetidas": len(aceitos) - gravados,
            "recusas": recusas}


def carregar_explicacoes(caminho: Path | None = None) -> dict[str, dict]:
    """{impressao: explicacao} - so as que dizem a fonte e de onde vieram.

    O arquivo e editavel a mao, e a tela nao confia nele: explicacao sem
    `fonte` ou sem procedencia nao aparece, como o macete.
    """
    origem = caminho or caminho_das_explicacoes()
    if not origem.exists():
        return {}
    linhas = json.loads(origem.read_text(encoding="utf-8")) or []
    return {
        # A origem do selo (Etapa 7A): explicacao e texto de IA.
        e["impressao"]: {**e, "origem": IA} for e in linhas
        if e.get("impressao") and (e.get("fonte") or "").strip()
        and (e.get("modelo") or "").strip() and e.get("criado_em")
    }


def _importar_explicacoes(lote: dict, respostas: list[dict], modelo: str) -> dict:
    por_id = {p["id"]: p for p in lote["pedidos"]}
    destino = caminho_das_explicacoes()
    existentes = (json.loads(destino.read_text(encoding="utf-8")) or []
                  if destino.exists() else [])
    ja = {e.get("impressao") for e in existentes}
    quando = agora().isoformat()
    gravadas = repetidas = 0
    recusas = []

    for resposta in respostas:
        pedido = por_id.get(resposta.get("id"))
        if pedido is None:
            recusas.append(f"{resposta.get('id')}: nao existe esse pedido no lote")
            continue
        item = resposta.get("explicacao") or {}
        onde = f"{pedido['id']} ({pedido.get('materia')})"
        texto = " ".join(str(item.get("explicacao") or "").split())
        fonte = " ".join(str(item.get("fonte") or "").split())
        correta = str(item.get("correta") or "").strip().lower()[:1]
        # O gabarito oficial manda. Explicacao que defende outra letra
        # ensinaria o erro com cara de certeza.
        if correta != (pedido.get("gabarito") or "").lower():
            recusas.append(f"{onde}: explica a letra {correta or '?'}, e o "
                           f"gabarito oficial e {pedido.get('gabarito')}")
            continue
        if len(texto) < 40:
            recusas.append(f"{onde}: sem explicacao")
            continue
        if not fonte_serve(fonte, pedido.get("materia")):
            recusas.append(f"{onde}: sem a fonte (o artigo da lei)")
            continue
        if pedido["impressao"] in ja:
            repetidas += 1
            continue
        ja.add(pedido["impressao"])
        existentes.append({
            "impressao": pedido["impressao"], "materia": pedido.get("materia"),
            "correta": correta, "explicacao": texto, "fonte": fonte,
            "modelo": modelo, "criado_em": quando,
        })
        gravadas += 1

    if gravadas:
        existentes.sort(key=lambda e: e["impressao"])
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(
            json.dumps(existentes, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return {"gravadas": gravadas, "repetidas": repetidas, "recusas": recusas}


def importar(resposta: Path, pedido: Path | None = None,
             quando: datetime | None = None) -> dict:
    """Le a resposta, confere contra o lote do pedido, e grava o que presta.

    Devolve {"tipo", "gravadas", "repetidas", "recusas"}. Levanta ValueError
    quando nada pode ser lido: sem pedido, JSON quebrado, ou resposta de
    OUTRO lote - aplicar a resposta de um pedido velho sobre o pedido novo
    poria a variacao de uma questao em cima de outra.
    """
    origem_do_pedido = pedido or caminho_do_pedido()
    if not origem_do_pedido.exists():
        raise ValueError(f"nao achei o pedido em {origem_do_pedido}")
    lote = json.loads(origem_do_pedido.read_text(encoding="utf-8"))
    corpo = _ler_json(resposta.read_text(encoding="utf-8"))

    if corpo.get("lote") != lote.get("lote"):
        raise ValueError(
            f"a resposta e do lote {corpo.get('lote')!r} e o pedido e do lote "
            f"{lote.get('lote')!r}"
        )
    respostas = [r for r in corpo.get("respostas") or [] if isinstance(r, dict)]
    modelo = procedencia(quando, corpo.get("modelo") if isinstance(corpo.get("modelo"), str)
                         else None)

    if lote.get("tipo") == "novidades":
        # A pesquisa das carreiras da aba Acompanhando (decisao 141): vai para
        # data/acompanhamentos.json, e nunca para o banco.
        from radar.servico import acompanhamentos

        resultado = acompanhamentos.importar_novidades(lote, respostas, modelo)
    elif lote.get("tipo") == "resumos":
        from radar.servico import fichas as servico_fichas

        resultado = servico_fichas.importar_resumos(lote["pedidos"], respostas, modelo)
    elif lote.get("tipo") == "classificacao":
        resultado = _importar_classificacao(lote, respostas, modelo)
    elif lote.get("tipo") == "associados":
        resultado = _importar_associados(lote, respostas, modelo)
    elif lote.get("tipo") == "fichas":
        resultado = _importar_fichas(lote, respostas, modelo)
    elif lote.get("tipo") == "macetes":
        resultado = _importar_macetes(lote, respostas, modelo)
    elif lote.get("tipo") == "explicacoes":
        resultado = _importar_explicacoes(lote, respostas, modelo)
    else:
        resultado = _importar_questoes(lote, respostas, modelo)
    return {"tipo": lote.get("tipo"), "modelo": modelo, **resultado}
