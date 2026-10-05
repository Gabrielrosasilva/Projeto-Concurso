# Roteiro: levar o radar para a nuvem

Pedido de 05/10/2026: abrir o site pelo celular, na rua ou em outra cidade,
com **usuário e senha**, e com **dois perfis**: o *admin*, que faz tudo, e o
*usuário*, que só faz simulados e treino e não edita nada. Ainda não começou:
este arquivo é o plano e a lista do que eu preciso responder antes.

## O ponto de partida (o que muda ao sair do PC)

- O site é o `radar web` (FastAPI + Jinja), hoje só em `localhost`. Ele **não
  tem login**: quem abre a página pode tudo. Por isso ele **nunca** vai para a
  internet antes da etapa N2 (login).
- O banco é um arquivo SQLite (`data/radar.db`). Os dados que importam também
  estão nos JSON versionados (`data/*.json`), que o backup das 23h30
  (`radar sincronizar`) sobe para o GitHub.
- A automação mora no **Agendador do Windows**: o backup das 23h30, o
  lembrete e a notificação do Windows. A coleta diária roda no **GitHub
  Actions** e não muda.
- O site tem 30 páginas (GET) e 26 ações que gravam (POST): responder
  simulado, marcar a faixa do dia, conferir, anotar erro, gerar e rejeitar
  questão, favoritar, coletar...

## A pergunta do Tailscale

**Funciona fora de casa, sim:** no 4G/5G, em outra cidade, em qualquer rede. O
app do Tailscale no celular liga o aparelho a uma rede privada sua, e o
celular enxerga o PC como se estivesse em casa. Dois limites:

1. o **PC precisa estar ligado** (e o `radar web` de pé) para o site abrir;
2. o Tailscale escolhe **quais aparelhos** entram, e não quem é admin: o
   usuário e a senha, com os dois perfis, continuam sendo trabalho do site
   (etapa N2).

Serve bem como passo zero (hoje, de graça, sem mexer no código) ou como cerca
extra em volta do servidor. Sozinho, não cumpre o pedido.

## As opções

| | A. Tailscale + o PC de casa | B. Cloudflare Tunnel + o PC | C. Servidor na nuvem (OCI) |
|---|---|---|---|
| Custo | grátis | grátis + domínio (~R$ 40/ano) | grátis (OCI Always Free) + domínio opcional |
| Precisa do PC ligado | sim | sim | **não** |
| Abre no navegador de qualquer aparelho | só nos que têm o app | sim | sim |
| Login com perfis | é do site (N2) | o do Cloudflare + o do site | é do site (N2) |
| Trabalho | ~15 min | ~1 h + N2 | etapas N1 a N6 |

**Recomendação: C**, com a A no meio do caminho se eu quiser usar antes. A
OCI Always Free dá uma VM ARM (até 4 OCPU e 24 GB) sem custo, eu já domino
OCI, Linux e Terraform, e o site passa a existir sem o PC.

## Etapas (uma conversa cada, como o roteiro principal)

**N0 — Já, sem código (opcional):** Tailscale no PC e no celular; `radar web`
ouvindo só no endereço do Tailscale. *Pronto quando:* o site abre no celular
fora do Wi-Fi de casa.

**N1 — O servidor:** VM na OCI (Terraform, que já é o meu terreno): Ubuntu,
firewall só com 22 (por chave) e 443, usuário sem root, Python 3.13, o
projeto clonado e o `radar web` como serviço do systemd, ouvindo só em
127.0.0.1. *Pronto quando:* `systemctl status radar-web` verde e nada
exposto além do 22.

**N2 — Login e perfis:** tabela de usuários (nome, hash da senha e perfil:
`admin` ou `usuario`); senha com `hashlib.scrypt`, da biblioteca padrão;
sessão por cookie assinado (o `SessionMiddleware` do Starlette, que pede a
dependência `itsdangerous`, a justificar); tela de entrada; limite de
tentativas; comando `radar usuario --novo` no terminal (nenhuma tela cria
admin). Toda página exige login; toda ação que grava diz qual perfil pode.
*Pronto quando:* testes provando que sem login nada abre, que o `usuario`
recebe 403 em cada ação de admin e que a senha não fica em texto no banco.

**N3 — HTTPS e o endereço:** Caddy na frente do site (certificado automático)
e um endereço: domínio próprio ou um gratuito (DuckDNS). Cookie só por
HTTPS. *Pronto quando:* o cadeado aparece no celular e o http redireciona.

**N4 — O banco e o backup:** o servidor passa a ser **a** cópia que vale (o
PC deixa de gravar, ou os dois brigam pelo mesmo dado). O `radar
sincronizar` vira um timer do systemd às 23h30, com chave de deploy do
GitHub; cópia diária do `radar.db` para um bucket da OCI (Always Free tem 20
GB). *Pronto quando:* um backup de verdade subiu e eu restaurei de um.

**N5 — A automação:** o que hoje é do Agendador do Windows vira timer do
systemd; a notificação do Windows vira Telegram (que já existe), porque o
servidor não tem área de trabalho. Token só em variável de ambiente.
*Pronto quando:* um dia inteiro rodou sem o PC.

**N6 — Endurecer e documentar:** fail2ban no SSH, atualização automática de
segurança, o README com "como subir do zero", e um teste do restore.

## O que eu preciso responder antes da N1

1. **Quem é o "usuário"?** Outra pessoa (amigo, parente) ou eu mesmo num
   aparelho emprestado? **É a pergunta que mais muda o trabalho:** o radar
   tem UM desempenho. Se outra pessoa responde simulados, as respostas dela
   entram no MEU acerto, no Meu desempenho, na revisão e no 1-7-30. Para
   outra pessoa, cada resposta precisa saber de quem é (desempenho por
   usuário): é uma etapa a mais, e grande.
2. O usuário vê o meu desempenho, o caderno de erros e as anotações, ou só
   faz simulado e treino?
3. Quais ações ele pode fazer? Sugestão: responder simulado e treino, e mais
   nada (nem marcar a faixa do dia, nem anotar erro, nem gerar questão).
4. Domínio próprio (~R$ 40/ano) ou endereço gratuito?
5. Região da OCI: São Paulo ou Vinhedo? Tenho conta lá, ou é uma nova?
6. O PC continua sendo usado para estudar (pelo navegador, no servidor), ou
   continua rodando o radar localmente? A recomendação é **um só banco**, o
   do servidor.
7. Quero o passo N0 (Tailscale) agora, enquanto o resto não sai?

## Custos

- OCI Always Free: R$ 0 (VM ARM, 200 GB de disco, 20 GB de bucket). O risco
  é a OCI recuperar VM ociosa da conta gratuita: o uso diário do site e o
  timer das 23h30 bastam para não ficar ociosa.
- Domínio: ~R$ 40/ano (opcional).
- Tailscale: R$ 0 no plano pessoal.

## Riscos

- **Nada vai para a internet sem a N2 e a N3 prontas.** O site de hoje, sem
  login, aberto na internet, entrega o banco a qualquer um.
- Dois bancos (PC e servidor) gravando ao mesmo tempo perdem dado: a N4
  decide qual vale antes de ligar o segundo.
- Senha e token nunca no repositório: só em variável de ambiente ou num
  arquivo fora do git.
