// app.js — [ITEM 4] Lógica da tela: envia os parâmetros, recebe eventos em TEMPO REAL
// (Server-Sent Events) e desenha a tabela de dispositivos online/offline.

const $ = (id) => document.getElementById(id);
const hosts = new Map();      // ip -> dados do host
let filtro = "online";
let rodando = false;

// ---------- Utilidades ----------
function ipParaNumero(ip) {
  return ip.split(".").reduce((acc, parte) => acc * 256 + Number(parte), 0);
}
function mostrarMensagem(texto) { $("mensagem").textContent = texto || ""; }
function escapar(texto) {
  return String(texto).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// ---------- Desenho da tabela ----------
function seloStatus(h) {
  if (h.status !== "online") return '<span class="selo offline">OFFLINE</span>';
  if (h.metodo === "ARP") return '<span class="selo arp">ONLINE · ICMP bloqueado</span>';
  return '<span class="selo online">ONLINE</span>';
}

function passaNoFiltro(h) {
  if (filtro === "todos") return true;
  if (filtro === "online") return h.status === "online";
  if (filtro === "offline") return h.status !== "online";
  if (filtro === "arp") return h.metodo === "ARP";
  return true;
}

function desenharTabela(destacarIp) {
  const linhas = [...hosts.values()]
    .filter(passaNoFiltro)
    .sort((a, b) => ipParaNumero(a.ip) - ipParaNumero(b.ip))
    .map((h) => {
      const portas = (h.portas || []).map((p) => `<span class="porta">${p.porta}/${escapar(p.servico)}</span>`).join("")
        || (h.status === "online" ? "—" : "");
      const latencia = h.latencia_ms === null || h.latencia_ms === undefined ? "—"
        : h.latencia_ms < 1 ? "< 1 ms" : `${h.latencia_ms} ms`;
      const metodo = h.metodo === "ICMP" ? "Ping (ICMP)" : h.metodo === "ARP" ? "ARP Probe" : "—";
      return `<tr class="${h.ip === destacarIp ? "novo" : ""}">
        <td class="mono">${escapar(h.ip)}</td>
        <td>${seloStatus(h)}</td>
        <td class="mono">${escapar(h.mac || "—")}</td>
        <td>${metodo}</td>
        <td>${latencia}</td>
        <td>${portas}</td></tr>`;
    });
  $("tabela").innerHTML = linhas.join("");
  $("vazio").style.display = linhas.length ? "none" : "block";
  desenharResumo();
}

function desenharResumo() {
  const lista = [...hosts.values()];
  const online = lista.filter((h) => h.status === "online");
  $("r-online").textContent = online.length;
  $("r-icmp").textContent = online.filter((h) => h.metodo === "ICMP").length;
  $("r-arp").textContent = online.filter((h) => h.metodo === "ARP").length;
  $("r-offline").textContent = lista.length - online.length;
}

function definirRodando(sim) {
  rodando = sim;
  $("btn-iniciar").disabled = sim;
  $("btn-cancelar").disabled = !sim;
}

// ---------- Tempo real (SSE) ----------
function conectarEventos() {
  const fonte = new EventSource("/api/eventos");
  fonte.onmessage = (msg) => {
    const evento = JSON.parse(msg.data);
    const d = evento.dados;
    switch (evento.tipo) {
      case "inicio":
        hosts.clear();
        desenharTabela();
        definirRodando(true);
        $("barra-preenchida").style.width = "0";
        break;
      case "etapa":
        $("etapa").textContent = d.texto;
        $("barra-preenchida").style.width = "0";
        break;
      case "progresso":
        $("barra-preenchida").style.width = `${Math.round((100 * d.feitos) / Math.max(1, d.total))}%`;
        break;
      case "host":
        hosts.set(d.ip, d);
        desenharTabela(d.ip);
        break;
      case "fim":
        $("etapa").textContent = d.cancelado
          ? "Varredura cancelada."
          : `Concluída em ${d.duracao_s} s — ${d.online} online (${d.via_icmp} por ICMP, ${d.via_arp} por ARP), ${d.offline} offline.`;
        $("barra-preenchida").style.width = "100%";
        definirRodando(false);
        break;
      case "salvo":
        carregarHistorico();
        break;
      case "erro":
        mostrarMensagem(d.mensagem);
        definirRodando(false);
        break;
    }
  };
  // Se a conexão cair, o navegador reconecta sozinho (comportamento padrão do EventSource).
}

// ---------- Ações ----------
async function iniciarVarredura(evento) {
  evento.preventDefault();
  if (rodando) return;  // trava contra clique duplo
  mostrarMensagem("");
  const parametros = {
    rede: $("rede").value.trim(),
    timeout_ms: $("timeout").value,
    porta_inicial: $("porta-inicial").value,
    porta_final: $("porta-final").value,
  };
  $("btn-iniciar").disabled = true;
  try {
    const resposta = await fetch("/api/varrer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(parametros),
    });
    const corpo = await resposta.json();
    if (!resposta.ok) {
      mostrarMensagem(corpo.erro || "Não foi possível iniciar.");
      $("btn-iniciar").disabled = rodando;
    }
  } catch (e) {
    mostrarMensagem("Sem comunicação com o servidor. Ele está rodando?");
    $("btn-iniciar").disabled = rodando;
  }
}

async function cancelarVarredura() {
  try { await fetch("/api/cancelar", { method: "POST" }); } catch (e) { /* ignora */ }
}

async function carregarHistorico() {
  try {
    const lista = await (await fetch("/api/historico")).json();
    $("lista-historico").innerHTML = lista.map((v) =>
      `<li data-id="${v.id}"><b>#${v.id}</b> · ${escapar(v.data_hora)} · rede ${escapar(v.rede)} · portas ${escapar(v.portas)}
       · <b>${v.resumo.online}</b> online (${v.resumo.via_arp} via ARP) · ${v.resumo.duracao_s} s</li>`).join("")
      || "<li>Nenhuma varredura salva ainda.</li>";
  } catch (e) { /* histórico é opcional; não quebra a tela */ }
}

async function abrirDoHistorico(id) {
  if (rodando || !id) return;
  try {
    const v = await (await fetch(`/api/historico/${id}`)).json();
    if (!v.hosts) return;
    hosts.clear();
    v.hosts.forEach((h) => hosts.set(h.ip, h));
    desenharTabela();
    $("etapa").textContent = `Exibindo varredura salva #${v.id} (${v.data_hora}, rede ${v.rede}).`;
  } catch (e) { /* ignora */ }
}

// ---------- Inicialização ----------
async function iniciar() {
  try {
    const info = await (await fetch("/api/info")).json();
    $("meu-ip").textContent = `Esta máquina: ${info.ip} · ${info.sistema} · ${info.arp}`;
    $("rede").value = info.rede_sugerida;
  } catch (e) { /* segue com o campo vazio */ }

  $("formulario").addEventListener("submit", iniciarVarredura);
  $("btn-cancelar").addEventListener("click", cancelarVarredura);
  document.querySelectorAll("#filtros button").forEach((b) =>
    b.addEventListener("click", () => {
      filtro = b.dataset.filtro;
      document.querySelectorAll("#filtros button").forEach((x) => x.classList.toggle("ativo", x === b));
      desenharTabela();
    }));
  $("lista-historico").addEventListener("click", (e) => {
    const li = e.target.closest("li");
    if (li) abrirDoHistorico(li.dataset.id);
  });

  conectarEventos();
  carregarHistorico();
  desenharTabela();
}

iniciar();
