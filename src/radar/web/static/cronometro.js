/* ==========================================================================
   O cronometro da tela Hoje - o UNICO JavaScript do radar.

   Por que existe (docs/decisoes.md): avisar a hora da pausa e a hora de
   voltar, com som e notificacao do Windows, e coisa que so o navegador faz.
   Todo o resto do radar continua sem JavaScript, e a tela Hoje funciona igual
   sem este arquivo: o servidor escreve o cartao, o aviso e os botoes ▶ com
   `hidden`, e e so aqui que eles aparecem.

   O que o servidor escreve em cada faixa (data-*): a duracao em minutos, o
   titulo, e o que vem depois - o titulo da proxima, se ela e pausa, quanto a
   pausa dura e o que vem depois da pausa.

   Tres regras que mandam no desenho:
   - a contagem e da DURACAO CHEIA a partir do clique: 50 min de teoria sao
     50 min, mesmo comecando atrasado;
   - o fim fica gravado no localStorage (a hora de termino, e nao "quanto
     falta"): recarregar a pagina ou trocar de aba nao perde nada;
   - o alarme e UM setTimeout ate o termino, e a conta e refeita quando a aba
     volta a ficar visivel. O relogio da tela (mm:ss) atualiza a cada segundo,
     mas o alarme nao depende dele: aba escondida atrasa intervalo, e o
     setTimeout unico mais a conferencia na volta cobrem isso.
   ========================================================================== */
(function () {
  "use strict";

  var CHAVE = "radar.cronometro";
  var raiz = document.getElementById("cronometro");
  var aviso = document.getElementById("aviso-cheio");
  if (!raiz || !aviso) {
    return;
  }

  function parte(nome) {
    return raiz.querySelector('[data-crono="' + nome + '"]');
  }
  function doAviso(nome) {
    return aviso.querySelector('[data-aviso="' + nome + '"]');
  }

  var cartao = raiz.querySelector(".cronometro");
  var tituloDaPagina = document.title;
  var estado = null;          // o cronometro rodando (ou null)
  var audio = null;           // o contexto de som, criado num clique meu
  var somRepetindo = null;
  var alarme = null;          // o setTimeout unico ate o termino
  var notificacao = null;
  var emTeste = false;        // o aviso aberto e o do "Testar aviso"

  // --- guardar: localStorage, com a memoria como reserva ------------------
  // Em janela anonima ou com o armazenamento bloqueado, o localStorage pode
  // falhar. O cronometro continua funcionando; so nao sobrevive a recarga.

  function ler() {
    try {
      var bruto = window.localStorage.getItem(CHAVE);
      return bruto ? JSON.parse(bruto) : null;
    } catch (e) {
      return estado;
    }
  }

  function gravar() {
    try {
      if (estado) {
        window.localStorage.setItem(CHAVE, JSON.stringify(estado));
      } else {
        window.localStorage.removeItem(CHAVE);
      }
    } catch (e) {
      // sem localStorage: fica so na memoria desta aba
    }
  }

  // --- o som (Web Audio, sem arquivo) -------------------------------------
  // O navegador so deixa tocar som depois de um clique meu. O ▶ e o Testar
  // criam o contexto; depois de recarregar a pagina, o primeiro clique em
  // qualquer lugar dela religa.

  function garantirAudio() {
    var Contexto = window.AudioContext || window.webkitAudioContext;
    if (!audio && Contexto) {
      audio = new Contexto();
    }
    if (audio && audio.state === "suspended") {
      audio.resume();
    }
  }

  function bipe() {
    if (!audio) {
      return;
    }
    var inicio = audio.currentTime;
    [0, 0.25, 0.5].forEach(function (atraso) {
      var oscilador = audio.createOscillator();
      var volume = audio.createGain();
      oscilador.type = "square";
      oscilador.frequency.value = 880;
      volume.gain.setValueAtTime(0.0001, inicio + atraso);
      volume.gain.exponentialRampToValueAtTime(0.2, inicio + atraso + 0.02);
      volume.gain.exponentialRampToValueAtTime(0.0001, inicio + atraso + 0.18);
      oscilador.connect(volume);
      volume.connect(audio.destination);
      oscilador.start(inicio + atraso);
      oscilador.stop(inicio + atraso + 0.2);
    });
  }

  function tocarSom() {
    pararSom();
    garantirAudio();
    bipe();
    // Repete ate eu clicar OK: alarme que toca uma vez so passa batido.
    somRepetindo = window.setInterval(bipe, 1500);
  }

  function pararSom() {
    if (somRepetindo) {
      window.clearInterval(somRepetindo);
      somRepetindo = null;
    }
  }

  // --- a notificacao do Windows -------------------------------------------

  function podeNotificar() {
    return "Notification" in window && window.isSecureContext &&
      Notification.permission === "granted";
  }

  function notificar(msg) {
    if (!podeNotificar()) {
      return;
    }
    try {
      notificacao = new Notification(msg.titulo, {
        body: [msg.texto, msg.depois].filter(Boolean).join("\n"),
        tag: "radar-cronometro",
        renotify: true,
        // Fica na tela ate eu fechar: e aviso de pausa, nao recado.
        requireInteraction: true
      });
      notificacao.onclick = function () {
        window.focus();
        notificacao.close();
      };
    } catch (e) {
      // Navegador que so notifica por service worker: fica o aviso e o som.
    }
  }

  function fecharNotificacao() {
    if (notificacao) {
      notificacao.close();
      notificacao = null;
    }
  }

  // --- o aviso em tela cheia ----------------------------------------------

  function mostrarAviso(msg) {
    doAviso("titulo").textContent = msg.titulo;
    doAviso("texto").textContent = msg.texto;
    doAviso("depois").textContent = msg.depois || "";
    doAviso("ok").textContent = msg.botao;
    aviso.hidden = false;
    doAviso("ok").focus();
  }

  function fecharAviso() {
    aviso.hidden = true;
    pararSom();
    fecharNotificacao();
  }

  // O texto do fim de uma faixa: os tres casos da especificacao.
  function mensagemDoFim(e) {
    var proxima = e.proxima || {};
    if (e.etapa === "pausa") {
      return {
        titulo: "▶ VOLTE: " + (proxima.titulo || "o estudo"),
        texto: "A pausa acabou.",
        depois: "",
        botao: "OK, voltei!"
      };
    }
    if (proxima.pausa) {
      return {
        titulo: "⏸ INTERVALO — " + proxima.duracao + " min",
        texto: "Terminou: " + e.nome,
        depois: proxima.depois ? "Depois da pausa: " + proxima.depois : "",
        botao: "OK, pausa!"
      };
    }
    return {
      titulo: "✅ Terminou: " + e.nome,
      texto: proxima.titulo ? "Próximo: " + proxima.titulo : "Era a última faixa do dia.",
      depois: "",
      botao: "OK"
    };
  }

  // --- o cronometro ---------------------------------------------------------

  function restante() {
    if (!estado) {
      return 0;
    }
    if (estado.restante !== null && estado.restante !== undefined) {
      return estado.restante;
    }
    return Math.max(0, estado.fim - Date.now());
  }

  function formatar(ms) {
    var segundos = Math.ceil(ms / 1000);
    var minutos = Math.floor(segundos / 60);
    var resto = segundos % 60;
    return (minutos < 10 ? "0" : "") + minutos + ":" + (resto < 10 ? "0" : "") + resto;
  }

  function desenhar() {
    var pausado = estado && estado.restante !== null && estado.restante !== undefined;
    if (!estado) {
      parte("nome").textContent = "Clique no ▶ de uma faixa para começar.";
      parte("tempo").textContent = "--:--";
      document.title = tituloDaPagina;
    } else {
      parte("nome").textContent = (estado.etapa === "pausa" ? "⏸ " : "▶ ") + estado.nome +
        (pausado ? " (pausado)" : "");
      parte("tempo").textContent = formatar(restante());
      document.title = "⏱ " + formatar(restante()) + " · " + tituloDaPagina;
    }
    parte("pausar").hidden = !estado || estado.tocando;
    parte("parar").hidden = !estado;
    parte("pausar").textContent = pausado ? "Retomar" : "Pausar";
    cartao.classList.toggle("rodando", !!estado && !pausado);
  }

  function agendar() {
    window.clearTimeout(alarme);
    alarme = null;
    if (!estado || estado.tocando || (estado.restante !== null && estado.restante !== undefined)) {
      return;
    }
    var falta = estado.fim - Date.now();
    if (falta <= 0) {
      disparar();
      return;
    }
    // UM setTimeout ate o fim. O teto e o do navegador (~24 dias).
    alarme = window.setTimeout(conferir, Math.min(falta, 2147483000));
  }

  function conferir() {
    if (estado && !estado.tocando && Date.now() >= estado.fim &&
        (estado.restante === null || estado.restante === undefined)) {
      disparar();
    } else {
      agendar();
    }
  }

  function disparar() {
    estado.tocando = true;
    var msg = mensagemDoFim(estado);
    var jaNotificado = estado.notificado;
    estado.notificado = true;
    gravar();
    emTeste = false;
    mostrarAviso(msg);
    tocarSom();
    // Outra aba ja notificou? A tag tambem evita a duplicata, mas assim nem
    // tenta de novo depois de recarregar.
    if (!jaNotificado) {
      notificar(msg);
    }
    desenhar();
  }

  function comecar(nome, minutos, etapa, proxima) {
    estado = {
      nome: nome,
      etapa: etapa,                  // "estudo" | "pausa"
      fim: Date.now() + minutos * 60000,
      restante: null,                // ms que faltavam, quando pausado
      proxima: proxima,
      tocando: false,
      notificado: false
    };
    gravar();
    agendar();
    desenhar();
  }

  function aoClicarNoPlay(evento) {
    var faixa = evento.currentTarget.closest("li");
    garantirAudio();
    parte("msg").textContent = "";
    comecar(faixa.dataset.titulo, Number(faixa.dataset.duracao), "estudo", {
      titulo: faixa.dataset.proximaTitulo,
      pausa: faixa.dataset.proximaPausa === "sim",
      duracao: Number(faixa.dataset.proximaDuracao),
      depois: faixa.dataset.depoisTitulo
    });
  }

  function aoClicarOk() {
    fecharAviso();
    if (emTeste) {
      emTeste = false;
      return;
    }
    var anterior = estado;
    if (anterior && anterior.etapa === "estudo" && anterior.proxima && anterior.proxima.pausa) {
      // "OK, pausa!": o cronometro da pausa comeca sozinho.
      comecar("Pausa", anterior.proxima.duracao, "pausa", {
        titulo: anterior.proxima.depois, pausa: false
      });
      return;
    }
    estado = null;
    gravar();
    agendar();
    desenhar();
  }

  function aoPausar() {
    garantirAudio();
    if (!estado) {
      return;
    }
    if (estado.restante === null || estado.restante === undefined) {
      estado.restante = Math.max(0, estado.fim - Date.now());
    } else {
      estado.fim = Date.now() + estado.restante;
      estado.restante = null;
    }
    gravar();
    agendar();
    desenhar();
  }

  function aoParar() {
    estado = null;
    gravar();
    agendar();
    fecharAviso();
    desenhar();
  }

  // --- o teste do aviso -------------------------------------------------------

  var TESTE = {
    titulo: "🔔 Teste do radar",
    texto: "Teste do radar: se você está vendo isto, o aviso funciona",
    depois: "",
    botao: "OK"
  };
  var COMO_LIBERAR = "As notificações estão bloqueadas para o radar. Para liberar: " +
    "clique no cadeado na barra de endereço → Notificações → Permitir, e " +
    "recarregue a página. Confira também se o \"Não perturbe\" (Assistente de " +
    "Foco) do Windows está desligado.";

  function dispararTeste(comNotificacao, recado) {
    emTeste = true;
    parte("msg").textContent = recado;
    mostrarAviso(TESTE);
    tocarSom();
    if (comNotificacao) {
      notificar(TESTE);
    }
  }

  function aoTestar() {
    garantirAudio();
    if (!window.isSecureContext) {
      dispararTeste(false, "Notificação do Windows só funciona no PC do radar " +
        "(localhost). Aqui, só o aviso na tela e o som.");
      return;
    }
    if (!("Notification" in window)) {
      dispararTeste(false, "Este navegador não tem notificação. Aqui, só o aviso na tela e o som.");
      return;
    }
    function depoisDaPermissao(permissao) {
      if (permissao === "granted") {
        dispararTeste(true, "Notificação liberada. Se ela não aparecer, confira o " +
          "\"Não perturbe\" (Assistente de Foco) do Windows.");
      } else if (permissao === "denied") {
        dispararTeste(false, COMO_LIBERAR);
      } else {
        dispararTeste(false, "Sem resposta do pedido de permissão. Clique em " +
          "Testar de novo e escolha Permitir.");
      }
    }
    if (Notification.permission === "default") {
      // Na primeira vez: pede a permissao, e so entao dispara. Navegador
      // novo responde pela promessa, antigo pelo callback - e alguns pelos
      // dois, dai o "so uma vez".
      var respondido = false;
      var umaVez = function (permissao) {
        if (!respondido) {
          respondido = true;
          depoisDaPermissao(permissao);
        }
      };
      var pedido = Notification.requestPermission(umaVez);
      if (pedido && pedido.then) {
        pedido.then(umaVez);
      }
    } else {
      depoisDaPermissao(Notification.permission);
    }
  }

  // --- ligar tudo -------------------------------------------------------------

  raiz.hidden = false;
  Array.prototype.forEach.call(document.querySelectorAll(".play-faixa"), function (botao) {
    botao.hidden = false;
    botao.addEventListener("click", aoClicarNoPlay);
  });
  parte("pausar").addEventListener("click", aoPausar);
  parte("parar").addEventListener("click", aoParar);
  parte("testar").addEventListener("click", aoTestar);
  doAviso("ok").addEventListener("click", aoClicarOk);
  // Recarreguei com o cronometro rodando: o primeiro clique na pagina religa
  // o som (o navegador nao deixa sem clique).
  document.addEventListener("pointerdown", function () {
    if (audio || estado) {
      garantirAudio();
    }
  });

  // Voltei para a aba: refaz a conta (o setTimeout pode ter atrasado).
  document.addEventListener("visibilitychange", function () {
    if (!document.hidden) {
      estado = ler();
      conferir();
      desenhar();
    }
  });
  // Outra aba mexeu no cronometro: acompanha, e fecha o aviso se ela deu OK.
  window.addEventListener("storage", function (evento) {
    if (evento.key !== CHAVE) {
      return;
    }
    estado = ler();
    if (!emTeste && (!estado || !estado.tocando)) {
      aviso.hidden = true;
      pararSom();
      fecharNotificacao();
    }
    agendar();
    desenhar();
  });

  estado = ler();
  if (estado && estado.tocando) {
    // Recarreguei com o aviso aberto: ele volta (o som, so depois de um clique).
    mostrarAviso(mensagemDoFim(estado));
    tocarSom();
  } else {
    agendar();
  }
  desenhar();
  // So o relogio da tela. O alarme e o setTimeout de cima.
  window.setInterval(desenhar, 1000);
})();
