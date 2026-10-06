"""A origem de cada dado que a tela mostra, e o selo dela (Etapa 7A).

A secao 20 do novo.md pede quatro origens, cada uma com uma cor:

  * **oficial** (🟢) - o que a banca ou o legislador publicou: edital,
    gabarito, caderno de prova, texto de lei;
  * **acervo** (🔵) - o que o sistema CONTOU nas provas do acervo:
    incidencia, padroes, quantas questoes ha de cada coisa;
  * **automatico** (🟡) - o que o sistema CALCULOU ou DEDUZIU: o meu
    desempenho, a prioridade, a classificacao por palavra-chave, a tendencia;
  * **ia** (🟣) - o que uma IA escreveu: questao gerada, macete, ficha.

Mais o **plano** (📌), que a ficha da 6B ja usava: o que eu mesmo planejei no
config/cronograma.yml.

O servico grava a origem no dado (um campo `origem`) e o template desenha o
selo a partir dela: quem decide a cor e o dado, e nao a tela. Este modulo e o
lugar UNICO dos selos e das duas frases que nao podem variar - a tela web
(`_componentes.html`), a ficha e o terminal leem daqui.
"""
from typing import NamedTuple

# As origens. O valor e o que o servico grava no campo `origem`.
OFICIAL, ACERVO, AUTOMATICO, IA, PLANO = "oficial", "acervo", "automatico", "ia", "plano"

# Tres selos sao a mesma origem com uma palavra a mais, porque a tela precisa
# dizer QUAL parte da origem e: a questao tirada do caderno e oficial como o
# edital, e a classificacao por palavra-chave e automatica como o desempenho.
PROVA, CLASSIFICACAO, TENDENCIA = "prova", "classificacao", "tendencia"

# O item que a coleta leu num site de NOTICIAS de concurso (decisao 141): e
# automatico como a classificacao - o sistema leu e deduziu -, e a palavra a
# mais diz de onde veio, porque e ela que manda conferir na fonte oficial.
NOTICIA = "noticia"


class Selo(NamedTuple):
    """Um selo: a origem (que da a cor), o emoji, o texto e o porque."""

    origem: str
    emoji: str
    texto: str
    explicacao: str


SELOS = {
    OFICIAL: Selo(OFICIAL, "🟢", "Fonte oficial",
                  "Edital, gabarito, prova ou lei - publicado pela banca ou pelo legislador"),
    PROVA: Selo(OFICIAL, "🟢", "Extraída da prova",
                "Questão real, tirada do caderno oficial"),
    ACERVO: Selo(ACERVO, "🔵", "Estatística do acervo",
                 "Contagem nas provas do acervo, com a amostra ao lado"),
    AUTOMATICO: Selo(AUTOMATICO, "🟡", "Análise automática",
                     "Calculado pelo sistema a partir dos meus registros - confira a amostra"),
    CLASSIFICACAO: Selo(AUTOMATICO, "🟡", "Análise automática (classificação)",
                        "Atribuído por palavra-chave, pelo classificador"),
    TENDENCIA: Selo(AUTOMATICO, "🟡", "Análise automática (tendência)",
                    "Leitura dos números - base pequena, confira"),
    NOTICIA: Selo(AUTOMATICO, "🟡", "Site de notícias",
                  "Lido automaticamente de um site de notícias de concurso - confira na fonte oficial"),
    IA: Selo(IA, "🟣", "Gerado por IA",
             "Texto de IA: material auxiliar, confira na fonte"),
    PLANO: Selo(PLANO, "📌", "Seleção do plano (cronograma)",
                "O que eu planejei no config/cronograma.yml"),
}

#: A frase da regra inviolavel 4 do novo.md, com o texto exato. Vale para o
#: que o ACERVO nao sustenta (incidencia, padrao, pegadinha); para o meu
#: desempenho com pouca resposta, o estado e "Amostra insuficiente"
#: (amostra.INSUFICIENTE), e para fato que ainda nao se sabe (prazo, banca),
#: "não sei ainda".
FRASE_SEM_EVIDENCIA = "Não há evidência suficiente no acervo para afirmar isso."

#: O que toda tela que mostra questao de IA escreve junto do 🟣 (regra 5).
FRASE_DA_QUESTAO_DE_IA = "Gerada por IA: não é questão oficial da FEPESE."
