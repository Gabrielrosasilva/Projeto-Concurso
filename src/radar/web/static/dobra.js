/* ==========================================================================
   Lembrar a dobra dos blocos da tela Hoje.

   Por que existe (docs/decisoes.md, B.11): os blocos do dia dobram num
   <details>/<summary>, e isso funciona sem JavaScript. O que o HTML sozinho
   NAO faz e lembrar: toda abertura da tela voltava ao padrao (Manha e Noite
   abertos, "Depois das 22h" fechado), e no uso real o vai e volta incomoda.
   Guardar o estado e coisa de navegador, como o cronometro.

   **A tela funciona igual sem este arquivo.** O servidor escreve o padrao no
   HTML (`<details open>` em quem nasce aberto), e a dobra responde ao clique
   com ou sem JavaScript. Este arquivo so RESTAURA o que eu deixei e SALVA o
   que eu mudo. Se o localStorage estiver bloqueado (janela privada, dado do
   site limpo), tudo continua funcionando no padrao - por isso cada acesso ao
   armazenamento esta num try/catch.

   A chave e o bloco (`data-bloco`: manha, noite, pos22, plano_b), e nao o dia:
   "eu prefiro o bloco das 22h fechado" e uma preferencia minha, nao uma coisa
   de 02/10.

   Uma excecao que importa: quando o endereco traz uma ancora (#faixa-pos22-1,
   que e onde a tela volta depois de eu anotar uma faixa), o bloco daquela
   faixa e ABERTO e nao e recolhido - recolher justo o que eu acabei de anotar
   seria esconder a resposta do meu proprio clique.
   ========================================================================== */
(function () {
  "use strict";

  var CHAVE = "radar.dobra";
  var blocos = document.querySelectorAll("details.bloco-dobra[data-bloco]");
  if (!blocos.length) {
    return;
  }

  function lido() {
    try {
      return JSON.parse(window.localStorage.getItem(CHAVE)) || {};
    } catch (erro) {
      // Dado corrompido ou armazenamento bloqueado: vale o padrao do HTML.
      return {};
    }
  }

  function gravar(estado) {
    try {
      window.localStorage.setItem(CHAVE, JSON.stringify(estado));
    } catch (erro) {
      // Nao ha o que fazer, e nao e erro meu: a dobra continua funcionando,
      // so nao sera lembrada na proxima abertura.
    }
  }

  // O bloco que a ancora aponta: ele fica como o servidor mandou.
  function blocoDaAncora() {
    var alvo;
    try {
      alvo = window.location.hash
        ? document.querySelector(window.location.hash)
        : null;
    } catch (erro) {
      return null;              // hash que nao e seletor valido
    }
    if (!alvo) {
      return null;
    }
    var dentro = alvo.closest("details.bloco-dobra[data-bloco]");
    return dentro ? dentro.getAttribute("data-bloco") : null;
  }

  var estado = lido();
  var daAncora = blocoDaAncora();

  Array.prototype.forEach.call(blocos, function (bloco) {
    var nome = bloco.getAttribute("data-bloco");

    if (nome === daAncora) {
      // A faixa que eu acabei de anotar esta aqui dentro: deixa aberto e
      // guarda isso, para a proxima abertura concordar com o que eu vejo.
      bloco.open = true;
      estado[nome] = true;
      gravar(estado);
    } else if (Object.prototype.hasOwnProperty.call(estado, nome)) {
      bloco.open = estado[nome] === true;
    }

    bloco.addEventListener("toggle", function () {
      var agora = lido();
      agora[nome] = bloco.open;
      gravar(agora);
    });
  });
})();
