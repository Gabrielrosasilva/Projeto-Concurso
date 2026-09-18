"""Diario oficial pela API do Querido Diario.

O valor prometido era o sinal "contratou a banca", que sai 2 a 4 meses antes do
edital. Os testes aqui guardam as duas armadilhas que a API real pregou: busca
sem territorio vira busca NACIONAL, e o nome do municipio nao casa sem acento.
"""
from datetime import date

import pytest

from radar import diario


class _RespostaFalsa:
    status_code = 200

    def __init__(self, dados):
        self._dados = dados

    def json(self):
        return self._dados

    def raise_for_status(self):
        return None


class _SessaoFalsa:
    """Uma sessao que devolve o que o teste mandar, e anota o que foi pedido."""

    def __init__(self, por_caminho):
        self.por_caminho = por_caminho
        self.pedidos = []

    def get(self, url, params=None, timeout=None):
        self.pedidos.append((url, params or {}))
        for pedaco, dados in self.por_caminho.items():
            if pedaco in url:
                return _RespostaFalsa(dados)
        return _RespostaFalsa({})


CIDADES = {
    "cities": [
        {"territory_name": "Florianópolis", "state_code": "SC",
         "territory_id": "4205407", "availability_date": "2020-10-30"},
        {"territory_name": "Palhoça", "state_code": "SC",
         "territory_id": "4211900", "availability_date": None},
        {"territory_name": "Floriano", "state_code": "PI",
         "territory_id": "2203909", "availability_date": "2021-01-01"},
    ]
}

EDICOES = {
    "gazettes": [
        {"date": "2026-08-20", "territory_name": "Florianópolis",
         "url": "https://data.test/a.pdf", "edition": "4088",
         "excerpts": ["...  abertura   de concurso publico  ..."]},
        {"date": "2026-05-13", "territory_name": "Florianópolis",
         "url": "https://data.test/b.pdf", "excerpts": []},
    ]
}


# --- quais municipios tem diario --------------------------------------------

def test_so_entra_municipio_com_diario_coletado():
    """Conhecer o municipio nao e ter diario dele: a API lista os 5.570 do
    pais, e so alguns tem edicao coletada."""
    sessao = _SessaoFalsa({"/cities": CIDADES})

    achadas = diario.com_diario(["Florianopolis", "Palhoca"], sessao=sessao)

    assert [c.nome for c in achadas] == ["Florianópolis"]


def test_o_nome_casa_mesmo_sem_acento():
    """config/regioes.yml guarda "Florianopolis" e o cadastro de la tem acento.
    A busca da API NAO ignora acento - procurar pelo nome cru devolvia lista
    vazia justamente para a capital."""
    sessao = _SessaoFalsa({"/cities": CIDADES})

    assert diario.com_diario(["Florianopolis"], sessao=sessao)


def test_municipio_de_outra_uf_com_nome_parecido_fica_de_fora():
    """"Floriano" no Piaui nao e "Florianopolis"."""
    sessao = _SessaoFalsa({"/cities": CIDADES})

    achadas = diario.com_diario(["Floriano"], uf="SC", sessao=sessao)

    assert achadas == []


def test_api_fora_do_ar_nao_quebra():
    class _Explode:
        def get(self, *a, **k):
            raise OSError("sem rede")

    assert diario.cidades(sessao=_Explode()) == []


# --- a busca ----------------------------------------------------------------

def test_busca_sem_territorio_e_recusada():
    """A API sem territorio busca no Brasil inteiro. Na primeira versao isso
    aconteceu calado e trouxe diario de Sergipe como se fosse daqui."""
    sessao = _SessaoFalsa({"/gazettes": EDICOES})

    assert diario.buscar("", "Florianopolis", sessao=sessao) == []
    assert sessao.pedidos == [], "nem chegou a pedir"


def test_a_busca_leva_o_territorio_pedido():
    sessao = _SessaoFalsa({"/gazettes": EDICOES})

    diario.buscar("4205407", "Florianopolis", termos=("abertura",), sessao=sessao)

    assert sessao.pedidos[0][1]["territory_ids"] == "4205407"


def test_uma_busca_por_termo():
    """Assim da para dizer QUAL termo trouxe cada achado - e o termo e o que
    diz se aquilo e abertura, homologacao ou contratacao de banca."""
    sessao = _SessaoFalsa({"/gazettes": EDICOES})

    diario.buscar("4205407", "Floripa", termos=("um", "dois", "tres"), sessao=sessao)

    assert len(sessao.pedidos) == 3


def test_a_mesma_edicao_nao_entra_duas_vezes():
    """Dois termos podem casar na mesma edicao."""
    sessao = _SessaoFalsa({"/gazettes": EDICOES})

    achados = diario.buscar("4205407", "Floripa", termos=("um", "dois"), sessao=sessao)

    assert len({a.url for a in achados}) == len(achados) == 2


def test_o_achado_guarda_o_termo_que_o_trouxe():
    sessao = _SessaoFalsa({"/gazettes": EDICOES})

    achados = diario.buscar("4205407", "Floripa", termos=("abertura",), sessao=sessao)

    assert achados[0].termo == "abertura"


def test_o_trecho_vem_limpo():
    """O excerpt da API vem com espaco sobrando do PDF."""
    sessao = _SessaoFalsa({"/gazettes": EDICOES})

    achados = diario.buscar("4205407", "Floripa", termos=("abertura",), sessao=sessao)
    trecho = next(a.trecho for a in achados if a.url.endswith("a.pdf"))

    assert "  " not in trecho


def test_edicao_sem_trecho_nao_quebra():
    sessao = _SessaoFalsa({"/gazettes": EDICOES})

    achados = diario.buscar("4205407", "Floripa", termos=("abertura",), sessao=sessao)

    assert any(a.trecho == "" for a in achados)


def test_o_mais_recente_vem_primeiro():
    sessao = _SessaoFalsa({"/gazettes": EDICOES})

    achados = diario.buscar("4205407", "Floripa", termos=("abertura",), sessao=sessao)

    assert achados[0].data == "2026-08-20"


def test_busca_respeita_a_data_de_corte():
    sessao = _SessaoFalsa({"/gazettes": EDICOES})

    diario.buscar("4205407", "Floripa", desde=date(2026, 1, 1),
                  termos=("abertura",), sessao=sessao)

    assert sessao.pedidos[0][1]["published_since"] == "2026-01-01"


def test_termo_que_falha_nao_derruba_os_outros():
    class _MeioQuebrada(_SessaoFalsa):
        def get(self, url, params=None, timeout=None):
            if params and params.get("querystring") == '"quebra"':
                raise OSError("timeout")
            return super().get(url, params, timeout)

    sessao = _MeioQuebrada({"/gazettes": EDICOES})

    achados = diario.buscar("4205407", "Floripa",
                            termos=("quebra", "abertura"), sessao=sessao)

    assert achados
