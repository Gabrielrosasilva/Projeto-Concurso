"""Os minimos de amostra num lugar so, e os cinco estados da secao 16.

O que estes testes guardam:

  * mudar um valor no YAML muda o comportamento - o minimo nao esta escrito em
    codigo nenhum;
  * as bordas exatas de cada estado (19/20, 59%/60%, em cima da meta, o dobro
    do minimo com 1 e com 2 dias);
  * abaixo do minimo o numero aparece e nao ordena nada;
  * nenhum minimo de amostra sobrou fora do config/amostra.yml.
"""
from pathlib import Path

import pytest

from radar import amostra


def _config(tmp_path: Path, texto: str) -> Path:
    arquivo = tmp_path / "amostra.yml"
    arquivo.write_text(texto, encoding="utf-8")
    return arquivo


# --- o arquivo manda ------------------------------------------------------------

def test_os_minimos_vem_do_arquivo_real():
    minimos = amostra.carregar()
    assert minimos.do_nivel("materia") == 20
    assert minimos.do_nivel("assunto") == 10
    assert minimos.do_nivel("subassunto") == 6
    assert minimos.do_nivel("elemento") == 6
    assert minimos.precisa_revisar_abaixo_de == 60
    assert minimos.meta_padrao == amostra.META_DA_PROVA == 79


def test_mudar_o_yaml_muda_o_comportamento(tmp_path):
    """A prova de que o numero nao esta no codigo: com minimo 4, quatro
    respostas ja medem; com o arquivo real, nao medem."""
    arquivo = _config(tmp_path, """
desempenho:
  minimos:
    assunto: 4
  precisa_revisar_abaixo_de: 90
""")
    frouxo = amostra.carregar(arquivo)
    assert frouxo.do_nivel("assunto") == 4

    quatro = amostra.estado(4, 4, nivel="assunto", meta=80, minimos=frouxo)
    assert quatro.suficiente and quatro.nome == amostra.CONSISTENTE
    assert amostra.estado(4, 4, nivel="assunto", meta=80).nome == amostra.INSUFICIENTE

    # O corte do "precisa revisar" tambem vem do arquivo: 85% com corte em 90
    # ainda precisa revisar.
    muitas = amostra.estado(20, 17, nivel="assunto", meta=95, minimos=frouxo)
    assert muitas.porcentagem == 85 and muitas.nome == amostra.PRECISA_REVISAR


def test_arquivo_sem_a_secao_usa_os_valores_da_decisao(tmp_path):
    arquivo = _config(tmp_path, "acervo:\n  minimo_questoes: 3\n")
    assert amostra.carregar(arquivo) == amostra.PADRAO


def test_arquivo_que_nao_existe_usa_os_valores_da_decisao(tmp_path):
    assert amostra.carregar(tmp_path / "nao_existe.yml") == amostra.PADRAO


def test_nivel_desconhecido_usa_o_minimo_da_materia():
    """Na duvida, medir menos - e nao medir errado."""
    assert amostra.carregar().do_nivel("coisa_nova") == 20


# --- as bordas de cada estado ---------------------------------------------------

def test_dezenove_de_vinte_e_amostra_insuficiente():
    quase = amostra.estado(19, 19, nivel="materia", meta=80)
    assert quase.nome == amostra.INSUFICIENTE
    assert quase.falta_para_o_minimo == 1
    # O numero continua na linha, para a tela mostrar o que eu fiz.
    assert quase.porcentagem == 100
    assert not quase.entra_na_ordenacao


def test_no_minimo_exato_ja_mede():
    assert amostra.estado(20, 16, nivel="materia", meta=80).nome == amostra.CONSISTENTE


@pytest.mark.parametrize("acertos, esperado", [
    (11, amostra.PRECISA_REVISAR),     # 55%
    (12, amostra.EM_APRENDIZADO),      # 60%, o corte exato
])
def test_a_borda_dos_sessenta_por_cento(acertos, esperado):
    assert amostra.estado(20, acertos, nivel="materia", meta=80).nome == esperado


def test_exatamente_na_meta_e_consistente():
    """80% com meta 80 esta NA meta: consistente, nao "em aprendizado"."""
    assert amostra.estado(20, 16, nivel="materia", meta=80).nome == amostra.CONSISTENTE
    assert amostra.estado(20, 15, nivel="materia", meta=80).nome == amostra.EM_APRENDIZADO


def test_o_dobro_do_minimo_em_um_dia_nao_e_bom_desempenho():
    """Uma tarde boa num assunto fresco na cabeca nao e dominio."""
    um_dia = amostra.estado(40, 36, nivel="materia", meta=80, dias=1)
    assert um_dia.nome == amostra.CONSISTENTE


def test_o_dobro_do_minimo_em_dois_dias_e_bom_desempenho():
    dois = amostra.estado(40, 36, nivel="materia", meta=80, dias=2)
    assert dois.nome == amostra.BOM_COM_AMOSTRA


def test_o_dobro_do_minimo_abaixo_da_meta_nao_sobe_de_estado():
    assert amostra.estado(40, 28, nivel="materia", meta=80,
                          dias=5).nome == amostra.EM_APRENDIZADO


def test_materia_sem_meta_propria_usa_a_meta_da_prova():
    """79 de 100 e a meta da prova inteira."""
    na_meta = amostra.estado(20, 16, nivel="materia")          # 80%
    abaixo = amostra.estado(20, 15, nivel="materia")           # 75%
    assert na_meta.meta == 79 and na_meta.nome == amostra.CONSISTENTE
    assert abaixo.nome == amostra.EM_APRENDIZADO


def test_o_subassunto_mede_com_seis():
    assert amostra.estado(6, 5, nivel="subassunto", meta=80).suficiente
    assert not amostra.estado(5, 5, nivel="subassunto", meta=80).suficiente


# --- sem resposta nenhuma -------------------------------------------------------

def test_sem_resposta_a_porcentagem_e_desconhecida_e_nao_zero():
    vazio = amostra.estado(0, 0, nivel="assunto")
    assert vazio.porcentagem is None
    assert vazio.nome == amostra.INSUFICIENTE
    assert "não respondi nenhuma" in amostra.frase_da_amostra_pequena(vazio)


def test_a_frase_da_amostra_pequena_diz_o_minimo_do_nivel():
    frase = amostra.frase_da_amostra_pequena(
        amostra.estado(3, 2, nivel="subassunto"))
    assert "3 respostas sem consulta" in frase and "das 6" in frase


def test_a_amostra_e_escrita_com_as_duas_contagens():
    assert amostra.estado(10, 7, nivel="assunto").amostra == (
        "7 de 10 respostas sem consulta")
    assert amostra.estado(1, 1, nivel="assunto").amostra == (
        "1 de 1 resposta sem consulta")


# --- nenhum minimo fora do config -----------------------------------------------

def test_nenhum_minimo_de_amostra_fora_do_config():
    """O critério de conclusão da Etapa 4, conferido por busca.

    Os numeros 5, 3 e 20 do "Onde estudar", de "Minhas materias" e da home
    sairam do codigo. O 3 do caderno de erros FICA: ele mede a fatia de cada
    motivo de erro, nao acerto - outra pergunta, outra regua, e esta anotado
    la e no radar/amostra.py.
    """
    raiz = Path(__file__).resolve().parent.parent / "src" / "radar"
    proibidos = ("MINIMO_NA_MATERIA =", "MINIMO_NO_ASSUNTO =",
                 "MINIMO_DA_AMOSTRA =")
    achados = []
    for arquivo in raiz.rglob("*.py"):
        texto = arquivo.read_text(encoding="utf-8")
        for proibido in proibidos:
            if proibido in texto:
                achados.append(f"{arquivo.name}: {proibido}")
    assert not achados, f"minimo escrito em codigo: {achados}"
