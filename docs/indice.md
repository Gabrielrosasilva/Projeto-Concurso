# Índice dos documentos

Para que serve cada arquivo, e qual ler primeiro. Nenhum documento é apagado:
os que viraram história ficam, marcados como tal.

## Ler primeiro, nesta ordem

1. **[CLAUDE.md](../CLAUDE.md)** — o contexto permanente: o que é o sistema, o
   que eu procuro num concurso, a arquitetura a preservar, as regras de
   trabalho e o **"Estado atual"**.
2. **[pendencias.md](pendencias.md)** — o que falta, o que está quebrado e o
   que ficou combinado. **Leia antes de propor etapa.** A seção H é a lista da
   revisão final do estudo (05/10).
3. **[decisoes.md](decisoes.md)** — as decisões tomadas, com o motivo. **A
   mais recente manda**, e não se rediscutem. Em conflito, a precedência é
   `decisoes.md` > `roteiro.md` > `novo.md`. A numeração é contínua da
   decisão 7 (Etapa 3B, 02/10) em diante; antes dela, cada seção numera a
   sua (1 a 14 da Etapa 0, 1 a 5 da 1B…), e as seções anteriores a 01/10 não
   têm número.

## O pedido e o plano

| Arquivo | Para que serve |
|---|---|
| [novo.md](novo.md) | O pedido de evolução: o objetivo, as **regras invioláveis** e os critérios de aceite (§23). |
| [roteiro.md](roteiro.md) | O plano das Etapas 1 a 8, com a ordem, as dependências e o critério de cada uma. Os pedidos de 03/10 e 05/10 não estão nele: ficam no progresso e nas decisões. |
| [progresso.md](progresso.md) | Como cada etapa andou: arquivos, testes, resultado e critério atendido (linhas 1 a 25). |
| [historico.md](historico.md) | A narrativa de como cada fase foi feita, curta, com o que mudou. |
| [especificacao.md](especificacao.md) | O redesign das telas (selos, home, fases 0 a 6). Ler antes de mexer em tela ou em dado de estudo. |
| [roteiro_nuvem.md](roteiro_nuvem.md) | O plano para levar o radar à nuvem com login e dois perfis (decisão 126). Ainda não começou. |

## Auditorias (história: o que valia no dia)

| Arquivo | Para que serve |
|---|---|
| [auditoria.md](auditoria.md) | **Gerado** por `radar auditar`: o banco contra os PDFs, o gabarito e as anuladas. Não editar à mão. |
| [auditoria_final.md](auditoria_final.md) | A Etapa 8 (03/10): os 19 itens da §23, com teste e uso real. |
| [auditoria_independente.md](auditoria_independente.md) | A auditoria de 04/10: 186 requisitos, 8 defeitos e o plano das rodadas de correção (todas feitas). |

## Registros de trabalho com dado

| Arquivo | Para que serve |
|---|---|
| [conferencia_das_fichas.md](conferencia_das_fichas.md) | A leitura das fichas contra a fonte (04/10 e 05/10) e o antes × depois das correções. A conferência de verdade é sua. |
| [leis_alteradas.md](leis_alteradas.md) | A evidência dos itens de `config/leis.yml`: as leis que mudaram depois das provas de 2013 e 2019. |
| [complementar.md](complementar.md) | **Gerado** por `radar complementar`: o levantamento do acervo complementar FEPESE. |
| [estoque_de_geradas.md](estoque_de_geradas.md) | O estoque de questões geradas por nó: o manual de 03/10 e o saldo de 05/10 (R5). |
| [reanalise_do_complementar.md](reanalise_do_complementar.md) | A reanálise às cegas do complementar (decisão 104). Registro do dia; a lista do que falta conferir está na lista única. |
| [classificacao_pt_rl.md](classificacao_pt_rl.md) | As duas leituras de Português e Raciocínio Lógico (decisão 106). Registro do dia, como o de cima. |
| [conferir_classificacoes.md](conferir_classificacoes.md) | **A lista única** do que você ainda confere na classificação do complementar. |

## Fora de docs/

- **[README.md](../README.md)** — instalar e usar: os comandos, as telas e a
  árvore do código. No Windows, o comando é `.venv\Scripts\radar.exe` (ou
  `.\radar.bat` no PowerShell); `python -m radar` não funciona.
- **config/** — os dados que eu edito à mão (cronograma, alvo, regiões,
  amostra, prioridade, leis, taxonomia, complementar).
- **data/** — o registro versionado (os JSON); o `radar.db` se refaz a partir
  deles. `data/copias/` guarda as cópias de antes de cada mudança, fora do
  git.
