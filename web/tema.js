// tema.js — Tema claro / escuro da interface (parte visual do [ITEM 4]).
//
// Como funciona:
//  1. Ao abrir, usa o tema salvo neste navegador; se não houver, segue o tema do Windows.
//  2. O botão no topo troca o tema e grava a escolha (localStorage).
//  3. O CSS tem as cores em variáveis; o atributo data-tema="escuro" no <html> troca todas de uma vez.
// Nada aqui interfere na varredura: é só aparência.

(function () {
  var CHAVE = "netprobe-tema";

  function lerSalvo() {
    try { return localStorage.getItem(CHAVE); } catch (e) { return null; }
  }
  function salvar(tema) {
    try { localStorage.setItem(CHAVE, tema); } catch (e) { /* navegador sem armazenamento: só não lembra */ }
  }
  function aplicar(tema) {
    document.documentElement.setAttribute("data-tema", tema);
    var botao = document.getElementById("btn-tema");
    if (botao) botao.textContent = tema === "escuro" ? "☀️ Claro" : "🌙 Escuro";
  }

  var sistemaEscuro = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  var tema = lerSalvo() || (sistemaEscuro ? "escuro" : "claro");
  aplicar(tema); // roda antes da página aparecer

  document.addEventListener("DOMContentLoaded", function () {
    aplicar(tema); // atualiza o texto do botão, que agora existe
    document.getElementById("btn-tema").addEventListener("click", function () {
      tema = tema === "escuro" ? "claro" : "escuro";
      aplicar(tema);
      salvar(tema);
    });
  });
})();
