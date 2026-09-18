# Radar de Concursos

Sistema pessoal para acompanhar concursos publicos que valem a pena para mim:
coleta os que abrem, guarda num banco, e deixa filtrar por estado, banca e
palavra-chave. O filtro que importa e **onde a prova e aplicada** — Grande
Florianopolis e arredores.

Estado: **fase 1** — esqueleto e a primeira fonte (feed RSS) funcionando.
O roadmap completo esta no `CLAUDE.md`.

## Rodando pela primeira vez

No Linux ou no Mac:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

No Windows (prompt de comando), onde o executavel se chama `python` e nao
`python3`, e nao se usa `source`:

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
copy .env.example .env
```

Dai em diante os comandos sao iguais nos tres:

```bash
radar coletar
radar listar                       # so o que esta perto de voce
radar listar --abertas             # so o que da para se inscrever hoje
radar listar --todos               # tudo, inclusive o que e longe
radar web                          # http://localhost:8000
```

### Depois de cada atualizacao

Sempre os mesmos tres comandos, nesta ordem:

```bash
git pull
pip install -e ".[dev]"     # rapido quando nada mudou; nao custa rodar sempre
radar reclassificar         # so se o classificador ou o regioes.yml mudaram
```

**Voce nunca precisa apagar `data/radar.db`.** Quando o modelo ganha uma
coluna, o proprio programa cria essa coluna no banco ao iniciar, preenchendo
o valor padrao nas linhas que ja existiam. O que ele nao faz e renomear,
trocar tipo ou remover coluna - se um dia precisarmos disso, eu aviso antes.

### Filtro por distancia

Todo concurso coletado e classificado em um anel:

| anel | o que e |
|---|---|
| `nucleo` | Grande Florianopolis |
| `proximo` | Itajai, Blumenau, Tubarao, Lages e vizinhos |
| `remoto` | outro lugar, inclusive o resto de SC |
| `indefinida` | nao da para saber sem ler o edital |

A lista padrao mostra so `nucleo` e `proximo`. **Nada e apagado**: o resto
continua no banco e sai com `--todos` ou pelos atalhos da pagina web.

Todo registro guarda *por que* foi classificado assim, em `motivo_relevancia`,
e o motivo aparece na tela. Se a decisao estiver errada, da para ver onde.

```bash
radar listar --relevancia remoto    # so o que ficou de fora
radar listar --noticias             # o que o filtro achou que nao era concurso
radar reclassificar                 # depois de editar config/regioes.yml
```

`radar reclassificar` roda a regra de novo no banco inteiro, sem ir a
internet. Incluiu um municipio novo no YAML? Rode isso e os registros antigos
se corrigem na hora.

### Trazendo o historico (carga inicial)

O RSS e um **fluxo, nao um arquivo**. Ele entrega so os 15 itens mais
recentes, entao quem liga o radar hoje ve os concursos de hoje e nada do que
foi publicado antes. Foi a primeira duvida depois que o Telegram ficou pronto:
"por que so aparecem 14 concursos?".

A resposta e este comando, que anda para tras no feed:

```bash
radar carga-inicial --dias 90      # tres meses de historico
radar carga-inicial --dias 7       # so a ultima semana
radar carga-inicial --dias 90 --sim   # sem perguntar antes
```

Ele usa `?paged=N` do proprio feed, que devolve as paginas mais antigas com a
mesma estrutura da primeira. Por isso a carga inicial usa o mesmo parser e traz
os mesmos campos - titulo completo, data e categoria -, em vez de raspar HTML.

Roda **uma vez so**, na mao. Nao entra na coleta diaria. Duas protecoes:
pausa de 1,5s entre paginas, e parada automatica assim que uma pagina inteira
fica mais antiga que o periodo pedido.

Medido no site em 17/09/2026: cerca de 1,5 pagina por dia de historico, 15
itens por pagina. Noventa dias saem em uns 3 minutos.

### O que esta com inscricao ABERTA

Data de publicacao nao e prazo. Um edital publicado ha um mes pode estar com
inscricao aberta ate semana que vem, e um de ontem pode ja ter fechado. Para
saber o que da para fazer HOJE, o radar le a pagina de cada post:

```bash
radar detalhar                  # le ate 150 paginas
radar listar --abertas          # so o que da para se inscrever agora
```

`radar detalhar` traz tres coisas que o RSS nao da:

| o que | para que serve |
|---|---|
| prazo de inscricao | responder "o que esta aberto agora" |
| banca | saber que padrao de prova estudar |
| municipio de lotacao | resolver o concurso estadual (ver abaixo) |

Ele **nao le a pagina de todos**. Seriam 2.200 requisicoes por quase uma hora,
e 1.400 delas de outro estado. A ordem e: primeiro o que ja esta perto, depois
os concursos de SC que ficaram `indefinida`, depois os federais.

**O caso que motivou isto:** "Concurso SEFAZ (SC)" nao tem "Prefeitura de X"
no titulo, entao o classificador nao acha municipio nenhum e marca
`indefinida` - o concurso existe, esta no banco, mas nao aparece em "Perto de
mim". A pagina do post diz "lotacao em Florianopolis", e com isso ele vai para
o nucleo, onde deveria estar.

Quando a pagina cita varios municipios - comum em edital de secretaria
estadual, que lista vagas pelo estado inteiro - o radar **nao escolhe nenhum**
e o registro segue `indefinida`. Chutar seria pior.

Na pagina web ha a aba **Inscricoes abertas**, ordenada pelo prazo, e cada
cartao mostra quantos dias faltam. Sete dias ou menos aparece em vermelho.

### Avisos no Telegram

O radar manda uma mensagem por concurso novo que interessa, com o link da
fonte junto - a ideia e nao precisar abrir o computador para saber do que se
trata.

**Configurar, uma vez:**

1. No Telegram, fale com o **@BotFather**, mande `/newbot` e escolha um nome.
   Ele responde com um **token**.
2. Fale com o **@userinfobot**. Ele responde com o seu **chat_id** numerico.
3. Coloque os dois no arquivo `.env`:

   ```
   RADAR_TELEGRAM_TOKEN=...
   RADAR_TELEGRAM_CHAT_ID=...
   ```

4. Mande `/start` para o **seu** bot. O Telegram nao deixa um bot puxar
   conversa: enquanto voce nao falar com ele, ele nao pode te responder.
5. Confira:

   ```bash
   radar testar-telegram
   ```

**No GitHub Actions**, os mesmos dois valores vao em
*Settings > Secrets and variables > Actions*, com os mesmos nomes. O `.env`
esta no `.gitignore` e nunca sobe para o repositorio.

**Quem vira mensagem:** `nucleo`, `proximo` e `indefinida`. Os indefinidos
entram de proposito - sao os federais e os sem UF, que ainda podem aplicar
prova em Florianopolis. Melhor dois avisos a toa do que perder o unico que
interessava. `remoto` e `noticia` nunca viram mensagem.

Cada concurso e avisado **uma vez so**: a data fica em `avisado_em` e a coleta
de amanha nao repete a de hoje.

**Teto de 10 mensagens por coleta.** Nao e economia, e protecao: se uma regra
de classificacao quebrar, o estrago fica em 10 mensagens mais um alerta, em
vez de 200 notificacoes as 6h da manha. O que sobrar continua pendente e sai
na proxima rodada.

```bash
radar avisar                # manda o que esta pendente
radar avisar --limite 3     # teto menor nesta rodada
radar testar-telegram       # so uma mensagem de teste, nao mexe no banco
```

### A interface web

```bash
radar web                       # so nesta maquina
radar web --porta 9000          # outra porta
radar web --host 0.0.0.0        # abre tambem no celular, na mesma wi-fi
radar web --recarregar          # reinicia ao salvar arquivo (para desenvolver)
```

O modo `--recarregar` vem **desligado**. Ligado, o uvicorn sobe um segundo
processo que reimporta o projeto, e isso quebra no Windows quando o caminho
da pasta tem espaco no nome. Desligado, o servidor e um processo so.

O `pip install -e` instala o projeto em modo editavel: o comando `radar` passa
a existir no PATH do venv e o Python acha o pacote sozinho. E por isso que nao
existe mais `PYTHONPATH=src` espalhado pelos comandos.

Rodar os testes:

```bash
pytest -q
```

Os testes usam arquivos de exemplo em `tests/fixtures/` e um SQLite temporario.
Nenhum deles vai a internet, entao passam offline e rodam em menos de 1s.

## Como o projeto esta organizado

```
src/radar/
├── config.py       le ambiente (.env). Nenhum efeito colateral no import.
├── models.py       tabela `concursos`
├── db.py           conexao criada sob demanda, nao no import
├── servico.py      roda coletores, grava com upsert, consulta
├── util.py         fuso horario e formatacao de data
├── cli.py          comandos de terminal
├── collectors/
│   ├── base.py                  contrato: toda fonte herda de Coletor
│   └── concursos_no_brasil.py   fonte 1 (feed RSS)
└── web/app.py      interface web

config/
├── regioes.yml     os tres aneis de distancia   (lido a partir da fase 1.5)
└── perfil.yml      seus dados para elegibilidade (lido a partir da fase 2.5)
```

A ideia central: **cada fonte e um arquivo isolado em `collectors/`**. O resto
do sistema nao sabe de onde veio o dado. Somar o diario oficial de SC depois e
criar um arquivo e registra-lo em `servico.COLETORES` — nada mais muda.

## Adicionando uma fonte nova

```python
# src/radar/collectors/minha_fonte.py
from radar.collectors.base import Coletor, ItemColetado

class MinhaFonte(Coletor):
    nome = "minha_fonte"

    def coletar(self) -> list[ItemColetado]:
        html = self.get("https://exemplo.com/concursos").text
        # ... extrair os dados ...
        return [ItemColetado(titulo="...", url="...", uf="SC")]
```

Depois inclua em `COLETORES`, dentro de `servico.py`.

O `self.get()` herdado ja cuida de tres coisas por voce: checa o `robots.txt`
do site, manda o `User-Agent` do projeto e espera o intervalo configurado
entre uma requisicao e outra ao mesmo host.

## O que o radar guarda

Um concurso e identificado pela **url**. Se a mesma url aparecer de novo numa
coleta seguinte, o registro e **atualizado**, nao duplicado — e por isso que
uma mudanca de `inscricoes_abertas` para `encerrado` chega no banco.

Duas colunas sao suas e a coleta nunca encosta nelas: `interesse` e `notas`.

O ciclo de vida fica em `situacao`:

```
prevista → autorizado → banca_definida → edital_publicado
→ inscricoes_abertas → encerrado
```

## Automacao

`.github/workflows/coleta.yml` roda a coleta todo dia as 6h de Florianopolis,
no GitHub Actions, e commita o resultado. Tambem da para disparar na mao pela
aba Actions.

Actions e gratuito em repositorio privado ate 2.000 minutos por mes; a coleta
gasta uns 3 minutos por dia. Sua maquina nao roda nada: ela so e usada quando
voce abre a web ou pede para baixar prova.

## Sobre as fontes

Nao existe API oficial unica de concursos no Brasil. A fase 1 usa o **feed
RSS** do Concursos no Brasil de proposito: RSS e publico, estavel e feito para
ser lido por programa, e nao quebra quando o site muda o layout.

Vale saber da limitacao: **RSS e um fluxo, nao um arquivo.** Ele entrega o que
e recente, entao "todos os concursos do ano" nao sai dele — isso e a fase 1.6,
com uma carga inicial pelas paginas de arquivo do site.

Regras da casa para as proximas fontes:
- respeitar o `robots.txt`;
- manter o intervalo entre requisicoes (`RADAR_REQUEST_DELAY`);
- identificar-se no `User-Agent`;
- guardar sempre o link original — o sistema e um indice, nao um substituto.

## Por que os PDFs nao ficam no git

A partir da fase 3 o radar baixa provas e editais. Eles vao para `data/provas/`
e `data/editais/`, que estao no `.gitignore`.

O que vai para o git e o **manifesto** (`data/provas.json`): link original,
banca, orgao, cargo, ano e o `sha256` de cada arquivo. Com ele, `radar
baixar-provas` reconstroi o acervo inteiro em qualquer maquina, e o hash prova
que o arquivo e o mesmo.

Motivo: git guarda uma copia inteira de cada arquivo binario a cada commit.
Algumas centenas de PDFs deixariam o repositorio grande e lento. Versionar a
receita em vez do artefato e a mesma logica de Dockerfile e imagem.

## Nota sobre dependencias

As versoes estao presas no `pyproject.toml`, inclusive o `click` — ele e
dependencia indireta do `typer` e uma versao nova dele ja quebrou a CLI aqui.
Se a coleta diaria comecar a falhar por instalacao, o proximo passo e gerar um
lock com `pip freeze`.
