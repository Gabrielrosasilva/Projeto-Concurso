"""O estudo extra: o que eu estudei fora das faixas do plano.

O plano manda no dia, mas o dia nao cabe nele. Uma hora de lei seca no almoco,
20 questoes na fila do banco, uma videoaula a noite: sem isto esse tempo nao
existia em lugar nenhum, e eu terminava a semana achando que tinha feito menos
do que fiz.

Duas regras que sao do assunto, e nao da tela:

  * `onde = radar` nao guarda questao nem acerto. O radar ja contou cada
    questao que eu respondi nele, uma por uma - somar aqui seria contar duas
    vezes o mesmo acerto. Do extra do radar vale o TEMPO;
  * o extra NAO muda a meta do dia nem a sugestao dela. A meta e a do plano, e
    fazer mais do que o plano pedia nao transforma um dia reduzido em ideal.

Como o resto do diario, nada daqui entra em acerto medido do radar.
"""
from datetime import date

from sqlalchemy import select

from radar import cronograma as plano_de_estudo
from radar.db import criar_tabelas, sessao
from radar.models import EstudoExtra, agora
from radar.servico.comum import RegistroInvalido

# O que eu fiz. Os mesmos nomes dos tipos de faixa do cronograma, de proposito:
# "lei seca extra" e a mesma coisa que a faixa de lei seca, feita fora da hora.
O_QUE = {
    "teoria": "Teoria",
    "lei_seca": "Lei seca",
    "questoes": "Questões",
    "revisao": "Revisão",
}

# Onde eu fiz. O radar e separado porque ele ja conta questao por questao.
ONDE = {
    "qconcursos": "Qconcursos",
    "radar": "Radar",
    "outro": "Outro",
}

#: Em `onde = radar`, questao e acerto sao do radar, e nao meus de digitar.
ONDE_SEM_QUESTOES = "radar"

# Estudo EXTRA de mais de 10 horas num dia e erro de digitacao - 720 no lugar
# de 72. Melhor recusar e eu corrigir do que gravar uma semana com 40 horas
# falsas, que e o tipo de numero que eu nunca mais desconfiaria.
MAXIMO_DE_MINUTOS = 10 * 60


def hoje_local() -> date:
    """O dia de hoje, perguntado ao diario do cronograma.

    O import e dentro da funcao de proposito: o cronograma importa este arquivo
    (ele soma os extras no total do dia), e importar de volta la em cima
    fecharia o circulo. Perguntar na hora do uso tambem garante UM relogio so -
    o teste para o tempo num lugar, e para para os dois.
    """
    from radar.servico import cronograma as diario

    return diario.hoje_local()


def _inteiro(valor, campo: str, minimo: int = 0) -> int | None:
    """Campo numerico do formulario: vazio vira None, lixo vira recusa."""
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        return None
    try:
        numero = int(str(valor).strip())
    except ValueError:
        raise RegistroInvalido(f"{campo} precisa ser um número inteiro (veio {valor!r})")
    if numero < minimo:
        raise RegistroInvalido(f"{campo} não pode ser menor que {minimo} (veio {numero})")
    return numero


def _conferir(
    data: date,
    o_que: str,
    onde: str,
    minutos: int | None,
    questoes: int | None,
    acertos: int | None,
    plano,
    hoje: date,
) -> tuple[int, int | None, int | None]:
    """Tudo o que precisa valer antes de gravar. Devolve os numeros limpos."""
    if o_que not in O_QUE:
        raise RegistroInvalido(
            f"Não conheço {o_que!r}. Escolha um destes: {', '.join(O_QUE)}."
        )
    if onde not in ONDE:
        raise RegistroInvalido(
            f"Não conheço o lugar {onde!r}. Escolha um destes: {', '.join(ONDE)}."
        )
    if data > hoje:
        raise RegistroInvalido(
            f"{data:%d/%m/%Y} ainda não chegou: só se anota hoje ou um dia passado."
        )
    if plano.dia(data) is None:
        raise RegistroInvalido(f"{data:%d/%m/%Y} não está no cronograma.")

    if not minutos:
        raise RegistroInvalido("Diga quantos minutos: estudo sem tempo não é estudo.")
    if minutos > MAXIMO_DE_MINUTOS:
        raise RegistroInvalido(
            f"{minutos} minutos é mais que {MAXIMO_DE_MINUTOS // 60} horas num dia - "
            f"confira se não sobrou um zero."
        )

    if onde == ONDE_SEM_QUESTOES:
        # Nao e recusa: e o radar mandando. As questoes dele ja estao contadas
        # uma por uma, e o extra guarda o tempo.
        return minutos, None, None

    if acertos is not None:
        if questoes is None:
            raise RegistroInvalido("Acertos sem questões: diga quantas você fez.")
        if acertos > questoes:
            raise RegistroInvalido(
                f"Acertos ({acertos}) maior que as questões feitas ({questoes})."
            )
    return minutos, questoes, acertos


def _conferir_o_no(caminho: str | None) -> str | None:
    """O caminho do no, se ele existe na arvore. None quando nao veio nada."""
    caminho = (caminho or "").strip()
    if not caminho:
        return None
    from radar import servico

    if caminho not in servico.conteudos.caminhos():
        raise RegistroInvalido(
            f"O conteúdo {caminho!r} não está na árvore (data/conteudos.json). "
            f"Confira com `radar conteudos`."
        )
    return caminho


def anotar(
    data: date | None = None,
    o_que: str = "questoes",
    materia: str | None = None,
    assunto: str | None = None,
    minutos=None,
    questoes=None,
    acertos=None,
    consulta: bool = False,
    onde: str = "outro",
    anotacao: str | None = None,
    conteudo: str | None = None,
    *,
    plano=None,
    hoje: date | None = None,
) -> EstudoExtra:
    """Grava um estudo extra no dia. Varios por dia, de proposito."""
    hoje = hoje or hoje_local()
    data = data or hoje
    plano = plano or plano_de_estudo.carregar()
    minutos, questoes, acertos = _conferir(
        data, o_que, onde,
        _inteiro(minutos, "Os minutos", minimo=0),
        _inteiro(questoes, "As questões", minimo=0),
        _inteiro(acertos, "Os acertos", minimo=0),
        plano, hoje,
    )

    criar_tabelas()
    extra = EstudoExtra(
        data=data,
        o_que=o_que,
        materia=_materia(materia, plano),
        assunto=(assunto or "").strip()[:200] or None,
        minutos=minutos,
        questoes=questoes,
        acertos=acertos,
        consulta=bool(consulta) and onde != ONDE_SEM_QUESTOES,
        onde=onde,
        anotacao=(anotacao or "").strip() or None,
        # O no da arvore, escolhido no formulario (Etapa 4). E por aqui que o
        # anotado do Qconcursos chega ao subassunto: antes ele parava na
        # materia e no titulo da faixa.
        conteudo=_conferir_o_no(conteudo),
    )
    with sessao() as s:
        s.add(extra)
    return extra


def _materia(nome: str | None, plano) -> str | None:
    """A materia, conferida contra o bloco `materias` do cronograma.

    Nome fora da lista e recusado em voz alta: aceitar calado faria o extra
    somar numa materia que nao existe, e o numero sumiria da tela sem aviso.
    """
    nome = (nome or "").strip()
    if not nome:
        return None
    if plano.materias and plano.materia(nome) is None:
        raise RegistroInvalido(
            f"{nome!r} não é uma das matérias do edital (config/cronograma.yml)."
        )
    return nome


def editar(ident: int, *, plano=None, hoje: date | None = None, **campos) -> EstudoExtra:
    """Muda um extra que eu ja tinha anotado. Confere o mesmo que o anotar."""
    hoje = hoje or hoje_local()
    plano = plano or plano_de_estudo.carregar()
    criar_tabelas()
    with sessao() as s:
        extra = s.get(EstudoExtra, ident)
        if extra is None:
            raise RegistroInvalido(f"Não achei o estudo extra #{ident}.")

        data = campos.get("data") or extra.data
        o_que = campos.get("o_que") or extra.o_que
        onde = campos.get("onde") or extra.onde
        minutos, questoes, acertos = _conferir(
            data, o_que, onde,
            _inteiro(campos.get("minutos", extra.minutos), "Os minutos", minimo=0),
            _inteiro(campos.get("questoes", extra.questoes), "As questões", minimo=0),
            _inteiro(campos.get("acertos", extra.acertos), "Os acertos", minimo=0),
            plano, hoje,
        )

        extra.data = data
        extra.o_que = o_que
        extra.onde = onde
        extra.minutos = minutos
        extra.questoes = questoes
        extra.acertos = acertos
        if "materia" in campos:
            extra.materia = _materia(campos["materia"], plano)
        if "assunto" in campos:
            extra.assunto = (campos["assunto"] or "").strip()[:200] or None
        if "anotacao" in campos:
            extra.anotacao = (campos["anotacao"] or "").strip() or None
        if "consulta" in campos:
            extra.consulta = bool(campos["consulta"]) and onde != ONDE_SEM_QUESTOES
        if "conteudo" in campos:
            extra.conteudo = _conferir_o_no(campos["conteudo"])
        extra.atualizado_em = agora()
        s.add(extra)
    return extra


def apagar(ident: int) -> bool:
    """Apaga um extra. False quando ele nao existia (F5 na pagina, por exemplo)."""
    criar_tabelas()
    with sessao() as s:
        extra = s.get(EstudoExtra, ident)
        if extra is None:
            return False
        s.delete(extra)
    return True


def do_dia(data: date) -> list[EstudoExtra]:
    """Os extras daquele dia, na ordem em que eu anotei."""
    criar_tabelas()
    with sessao() as s:
        return list(s.scalars(
            select(EstudoExtra)
            .where(EstudoExtra.data == data)
            .order_by(EstudoExtra.criado_em, EstudoExtra.id)
        ))


def entre(inicio: date, fim: date) -> list[EstudoExtra]:
    """Os extras das duas datas, inclusive. E o que a tela de Semanas soma."""
    criar_tabelas()
    with sessao() as s:
        return list(s.scalars(
            select(EstudoExtra)
            .where(EstudoExtra.data >= inicio, EstudoExtra.data <= fim)
            .order_by(EstudoExtra.data, EstudoExtra.criado_em)
        ))
