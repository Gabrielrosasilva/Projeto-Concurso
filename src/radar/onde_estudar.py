"""Por qual ASSUNTO comecar hoje, e quanto ele vale em ponto de prova.

A tabela de materias do Meu foco ja responde "que materia pesa mais" e "onde
eu vou pior". Falta a pergunta que decide a tarde de estudo: **dentro da
materia, qual assunto?** Direitos Humanos vale 15 questoes, mas estudar
"Direitos Humanos" nao e um plano - estudar as Regras de Mandela e.

A conta e esta, e ela cabe em duas linhas:

    questoes esperadas = quantas questoes o edital reserva para a materia
                         x a fatia que aquele assunto ocupa nas provas
    pontos a ganhar    = questoes esperadas x (1 - meu acerto no simulado)

"Pontos a ganhar" e o que eu deixo na mesa hoje. Um assunto de 10 questoes em
que eu acerto 90% vale 1 ponto a recuperar; um de 4 questoes em que eu acerto
25% vale 3. O segundo e onde a tarde rende mais, e nenhum dos dois numeros
sozinho diria isso.

Este arquivo nao fala com banco nem com rede: recebe contagem e devolve
numero, como o `macetes`. Quem varre o acervo e o `foco`.

REGRA DE SEMPRE: nunca inventar. Assunto sem simulado fica com `acerto=None` e
`pontos=None` - e NAO com zero por cento, que diria que eu errei tudo quando o
que houve foi eu nao ter treinado. A tela diz isso com todas as letras.
"""
from dataclasses import dataclass

from radar.leis import Lei, do_assunto
from radar.regioes import normalizar

# Quantas linhas cabem na tela. O programa do edital de 2019 tem 70 assuntos, e
# setenta barras nao sao um grafico - sao uma lista telefonica. O que sobra vira
# uma linha de rodape dizendo quantos ficaram de fora.
NA_TELA = 12

# De onde saiu o nome do assunto. Nao e detalhe de implementacao: uma origem
# custou dinheiro e a outra nao, e a tela mostra qual e qual.
CATALOGO, EDITAL = "catalogo", "edital"


@dataclass(frozen=True)
class LinhaDeEstudo:
    """Um assunto do programa, e quanto ele vale em ponto de prova."""

    materia: str
    assunto: str

    #: Quantas questoes o edital reserva para a materia inteira.
    questoes_no_edital: int

    #: Em quantas questoes a fatia se apoia, separadas por procedencia. As
    #: proprias sao as provas do meu cargo no meu estado - so duas existem. O
    #: reforco vem da mesma banca nas mesmas materias, em outros concursos.
    proprias: int
    reforco: int
    #: O denominador da fatia: todas as marcas de assunto daquela materia.
    base_da_materia: int

    #: O produto das duas coisas acima. Fracionado de proposito: dizer "3,8
    #: questoes" e mais honesto que arredondar para 4 e parecer contagem.
    esperadas: float

    #: Meu acerto naquele assunto, em porcento. None = nunca treinei.
    acerto: float | None
    respondidas: int

    #: esperadas x (1 - acerto). None quando nao ha acerto medido.
    pontos: float | None

    origem: str
    lei: Lei | None = None

    @property
    def apoio(self) -> int:
        """Em quantas questoes do acervo esta linha inteira se apoia."""
        return self.proprias + self.reforco

    @property
    def repete_a_materia(self) -> bool:
        """O assunto do programa ja diz o nome da materia?

        Tem materia do edital que e uma lei so, e ai o assunto do programa
        repete o nome dela: "Lei de Execução Penal (Lei nº 7.210 ...)" dentro
        da materia "Lei de Execução Penal". Mostrar as duas daria uma linha que
        se gagueja, e por isso a tela e a frase de conclusao perguntam isto.
        """
        return normalizar(self.materia) in normalizar(self.assunto)

    @property
    def ordem(self) -> float:
        """Por onde a lista e ordenada, do maior para o menor.

        Com acerto medido, sao os pontos a ganhar. Sem acerto, e o proprio
        tamanho esperado do assunto - que e o teto dos pontos a ganhar, ja que
        `pontos <= esperadas` sempre. Um assunto que eu nunca treinei entra,
        entao, pelo maximo que ele PODERIA valer: e o unico palpite que nao
        precisa de dado que eu nao tenho.
        """
        return self.esperadas if self.pontos is None else self.pontos


def _fatia(marcas: int, base: int) -> float:
    return marcas / base if base else 0.0


def montar(
    materias_do_edital: list,
    contagens: dict[tuple[str, str], tuple[int, int]],
    acertos: dict[tuple[str, str], tuple[int, int]],
    origens: dict[str, str],
) -> list[LinhaDeEstudo]:
    """As linhas ordenadas por quanto ha para ganhar em cada assunto.

    - `materias_do_edital`: o quadro lido do PDF, que da o peso de cada materia;
    - `contagens`: {(materia, assunto): (proprias, reforco)}, em enunciados
      distintos;
    - `acertos`: {(materia, assunto): (respondidas, acertos)}, do simulado;
    - `origens`: {materia: "catalogo" ou "edital"}.

    Materia que nao esta no quadro do edital fica de fora: sem o peso dela nao
    ha "questoes esperadas" nenhuma, e inventar um peso e justamente o que
    faria eu estudar a materia errada por meses.
    """
    peso_da_materia = {m.nome: m.questoes for m in materias_do_edital}

    # A base e a soma das marcas da PROPRIA materia, e nao o total do acervo:
    # a fatia responde "quanto desta materia e este assunto", e so as questoes
    # dela entram na conta.
    base: dict[str, int] = {}
    for (materia, _assunto), (proprias, reforco) in contagens.items():
        base[materia] = base.get(materia, 0) + proprias + reforco

    linhas = []
    for (materia, assunto), (proprias, reforco) in contagens.items():
        if materia not in peso_da_materia:
            continue

        no_edital = peso_da_materia[materia]
        esperadas = no_edital * _fatia(proprias + reforco, base.get(materia, 0))
        if not esperadas:
            continue

        respondidas, certas = acertos.get((materia, assunto), (0, 0))
        acerto = (certas / respondidas * 100) if respondidas else None
        pontos = None if acerto is None else esperadas * (1 - acerto / 100)

        linhas.append(LinhaDeEstudo(
            materia=materia,
            assunto=assunto,
            questoes_no_edital=no_edital,
            proprias=proprias,
            reforco=reforco,
            base_da_materia=base.get(materia, 0),
            esperadas=esperadas,
            acerto=acerto,
            respondidas=respondidas,
            pontos=pontos,
            origem=origens.get(materia, EDITAL),
            lei=do_assunto(materia, assunto),
        ))

    # Empate desempata pelo assunto mais medido, e depois pelo nome: duas
    # aberturas seguidas da tela tem que mostrar a mesma ordem.
    linhas.sort(key=lambda l: (-l.ordem, -l.apoio, l.assunto))
    return linhas


def numero(valor: float, casas: int = 1) -> str:
    """O numero como se escreve em portugues: virgula, e sem zero a toa."""
    texto = f"{valor:.{casas}f}".replace(".", ",")
    return texto[:-2] if texto.endswith(",0") else texto


def _como_chamar(linha: LinhaDeEstudo) -> str:
    """O assunto, com a materia entre parenteses so quando ela acrescenta algo."""
    if linha.repete_a_materia:
        return linha.assunto
    return f"{linha.assunto} ({linha.materia})"


def conclusao(linhas: list[LinhaDeEstudo]) -> str | None:
    """Uma frase montada dos numeros da primeira linha. Nunca inventada.

    Ela nao acrescenta nada ao grafico: diz em portugues o que a primeira
    barra ja diz em pixel. Existe porque o grafico responde "qual e o maior" e
    a frase responde "e dai?" - e e a segunda que faz eu abrir a apostila.

    None quando nao ha linha nenhuma: sem numero nao ha conclusao, e escrever
    uma mesmo assim seria inventar.
    """
    if not linhas:
        return None

    primeira = linhas[0]
    onde = _como_chamar(primeira)

    if primeira.acerto is None:
        return (
            f"{onde} é o maior bloco esperado da prova: "
            f"{numero(primeira.esperadas)} questões. "
            f"Eu ainda não respondi nenhuma questão dele no simulado, então "
            f"não dá para dizer quanto há a ganhar - vale medir antes de "
            f"escolher por onde começar."
        )

    return (
        f"{onde} deve valer {numero(primeira.esperadas)} questões e eu acerto "
        f"{numero(primeira.acerto, 0)}% delas: são "
        f"{numero(primeira.pontos)} pontos a ganhar, "
        f"mais do que em qualquer outro assunto."
    )
