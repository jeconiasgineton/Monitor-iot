"""Página do painel web. HTML e JavaScript puros, servidos por /painel. Sem build.

Monta a tela com textContent (nunca innerHTML com dados vindos da API).
"""

HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Monitoramento de bombas - painel</title>
<style>
  :root { --bg:#f5f6f8; --card:#fff; --txt:#1f2430; --sub:#6b7280; --ok:#16a34a; --alerta:#dc2626; --azul:#2563eb; }
  * { box-sizing: border-box; }
  body { margin:0; font-family: system-ui, sans-serif; background:var(--bg); color:var(--txt); }
  header { background:#111827; color:#fff; padding:12px 16px; display:flex; justify-content:space-between; align-items:center; }
  header h1 { font-size:16px; margin:0; font-weight:600; }
  main { max-width:960px; margin:0 auto; padding:16px; }
  .card { background:var(--card); border-radius:10px; padding:16px; margin-bottom:16px; box-shadow:0 1px 2px rgba(0,0,0,.06); }
  h2 { font-size:15px; margin:0 0 12px; }
  label { display:block; font-size:13px; color:var(--sub); margin:8px 0 4px; }
  input { width:100%; padding:10px; border:1px solid #d1d5db; border-radius:6px; font-size:15px; }
  button { padding:10px 14px; border:0; border-radius:6px; background:var(--azul); color:#fff; font-size:15px; cursor:pointer; margin-top:12px; }
  button.secundario { background:#e5e7eb; color:var(--txt); }
  button.sair { background:transparent; border:1px solid #4b5563; padding:6px 10px; font-size:13px; margin:0; }
  .msg { font-size:14px; margin-top:10px; min-height:18px; }
  .erro { color:var(--alerta); } .ok { color:var(--ok); }
  .grade { display:grid; grid-template-columns:repeat(auto-fill,minmax(220px,1fr)); gap:12px; }
  .disp { border:1px solid #e5e7eb; border-radius:8px; padding:12px; cursor:pointer; background:#fff; text-align:left; }
  .disp:hover, .disp.ativo { border-color:var(--azul); }
  .disp strong { display:block; font-size:14px; margin-bottom:4px; }
  .disp span { font-size:12px; color:var(--sub); }
  .alerta-item { padding:8px 10px; border-left:4px solid var(--alerta); background:#fef2f2; border-radius:4px; margin-bottom:8px; font-size:14px; }
  .alerta-item.informativa { border-color:#9ca3af; background:#f9fafb; }
  .vazio { color:var(--sub); font-size:14px; }
  .oculto { display:none; }
  svg { width:100%; height:220px; background:#fafafa; border-radius:6px; }
  .legenda { font-size:12px; color:var(--sub); margin-top:6px; }
  details summary { cursor:pointer; font-size:14px; color:var(--azul); }
  .linha { display:flex; gap:8px; justify-content:space-between; align-items:center; }
</style>
</head>
<body>
<header>
  <h1>Monitoramento de bombas</h1>
  <button id="btn-sair" class="sair oculto" type="button">Sair</button>
</header>

<main>
  <section id="tela-login" class="card">
    <h2>Entrar</h2>
    <form id="form-login">
      <label for="email">E-mail</label>
      <input id="email" type="email" autocomplete="username" required>
      <label for="senha">Senha</label>
      <input id="senha" type="password" autocomplete="current-password" required>
      <button type="submit">Entrar</button>
      <div id="msg-login" class="msg erro"></div>
    </form>
  </section>

  <section id="tela-app" class="oculto">
    <div class="card">
      <div class="linha">
        <h2>Dispositivos</h2>
        <button id="btn-atualizar" class="secundario" type="button">Atualizar</button>
      </div>
      <div id="lista-dispositivos" class="grade"></div>
      <div id="msg-lista" class="msg erro"></div>
    </div>

    <div id="detalhe" class="card oculto">
      <div class="linha">
        <h2 id="titulo-detalhe"></h2>
        <span id="estado-detalhe" class="legenda"></span>
      </div>

      <h2 style="margin-top:12px">Alertas abertos</h2>
      <div id="lista-alertas"></div>

      <h2 style="margin-top:16px">Corrente RMS (últimas 50 leituras)</h2>
      <div id="grafico"></div>
      <div class="legenda" id="legenda-grafico"></div>
      <div id="msg-detalhe" class="msg erro"></div>
    </div>

    <details class="card">
      <summary>Trocar minha senha</summary>
      <form id="form-senha">
        <label for="senha-atual">Senha atual</label>
        <input id="senha-atual" type="password" autocomplete="current-password" required>
        <label for="senha-nova">Nova senha (mínimo 10 caracteres)</label>
        <input id="senha-nova" type="password" autocomplete="new-password" minlength="10" required>
        <button type="submit">Trocar senha</button>
        <div id="msg-senha" class="msg"></div>
      </form>
    </details>
  </section>
</main>

<script>
(function () {
  const API = "";
  const CHAVE = "monitor_token";
  let dispositivoAtual = null;
  let timer = null;

  const $ = (id) => document.getElementById(id);

  function token() { return sessionStorage.getItem(CHAVE); }

  function mostrarTela(logado) {
    $("tela-login").classList.toggle("oculto", logado);
    $("tela-app").classList.toggle("oculto", !logado);
    $("btn-sair").classList.toggle("oculto", !logado);
  }

  function sair() {
    sessionStorage.removeItem(CHAVE);
    if (timer) { clearInterval(timer); timer = null; }
    dispositivoAtual = null;
    $("detalhe").classList.add("oculto");
    mostrarTela(false);
  }

  async function api(caminho, opcoes = {}) {
    const cabecalhos = Object.assign({}, opcoes.headers || {});
    if (token()) cabecalhos["Authorization"] = "Bearer " + token();
    if (opcoes.body) cabecalhos["Content-Type"] = "application/json";
    const r = await fetch(API + caminho, Object.assign({}, opcoes, { headers: cabecalhos }));
    let dados = null;
    try { dados = await r.json(); } catch (e) { dados = null; }
    if (r.status === 401 && caminho !== "/v1/auth/login" && caminho !== "/v1/auth/senha") {
      sair();
      throw new Error("Sessão expirada. Entre de novo.");
    }
    if (!r.ok) {
      const detalhe = dados && dados.detail ? dados.detail : "Erro " + r.status;
      throw new Error(typeof detalhe === "string" ? detalhe : "Erro " + r.status);
    }
    return dados;
  }

  $("form-login").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    $("msg-login").textContent = "";
    try {
      const dados = await api("/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ email: $("email").value.trim(), senha: $("senha").value })
      });
      sessionStorage.setItem(CHAVE, dados.token);
      $("senha").value = "";
      mostrarTela(true);
      await carregarDispositivos();
    } catch (e) {
      $("msg-login").textContent = e.message;
    }
  });

  $("btn-sair").addEventListener("click", sair);
  $("btn-atualizar").addEventListener("click", carregarDispositivos);

  async function carregarDispositivos() {
    $("msg-lista").textContent = "";
    const lista = $("lista-dispositivos");
    lista.textContent = "";
    try {
      const dados = await api("/v1/dispositivos");
      if (!dados.dispositivos.length) {
        const p = document.createElement("p");
        p.className = "vazio";
        p.textContent = "Nenhum dispositivo disponível para este usuário.";
        lista.appendChild(p);
        return;
      }
      dados.dispositivos.forEach((d) => {
        const b = document.createElement("button");
        b.type = "button";
        b.className = "disp";
        const nome = document.createElement("strong");
        nome.textContent = d.id;
        const info = document.createElement("span");
        info.textContent = "Condomínio: " + d.condominio_id + " · Bomba: " + d.bomba_id;
        b.appendChild(nome);
        b.appendChild(info);
        b.addEventListener("click", () => abrirDispositivo(d.id, b));
        lista.appendChild(b);
      });
    } catch (e) {
      $("msg-lista").textContent = e.message;
    }
  }

  function abrirDispositivo(id, botao) {
    document.querySelectorAll(".disp").forEach((x) => x.classList.remove("ativo"));
    if (botao) botao.classList.add("ativo");
    dispositivoAtual = id;
    $("detalhe").classList.remove("oculto");
    $("titulo-detalhe").textContent = id;
    atualizarDetalhe();
    if (timer) clearInterval(timer);
    timer = setInterval(atualizarDetalhe, 60000);
  }

  async function atualizarDetalhe() {
    if (!dispositivoAtual) return;
    const id = dispositivoAtual;
    $("msg-detalhe").textContent = "";
    try {
      const [alertas, telemetria] = await Promise.all([
        api("/v1/dispositivos/" + encodeURIComponent(id) + "/alertas?somente_abertos=true"),
        api("/v1/dispositivos/" + encodeURIComponent(id) + "/telemetria?limite=50")
      ]);
      if (id !== dispositivoAtual) return;
      renderAlertas(alertas.alertas);
      renderGrafico(telemetria.leituras);
    } catch (e) {
      if (id === dispositivoAtual) $("msg-detalhe").textContent = e.message;
    }
  }

  function renderAlertas(lista) {
    const caixa = $("lista-alertas");
    caixa.textContent = "";
    if (!lista.length) {
      const p = document.createElement("p");
      p.className = "vazio";
      p.textContent = "Nenhum alerta aberto.";
      caixa.appendChild(p);
      $("estado-detalhe").textContent = "Sem alertas";
      return;
    }
    $("estado-detalhe").textContent = lista.length + " alerta(s) aberto(s)";
    lista.forEach((a) => {
      const div = document.createElement("div");
      div.className = "alerta-item" + (a.severidade === "informativa" ? " informativa" : "");
      div.textContent = a.mensagem + " (" + a.severidade + ")";
      caixa.appendChild(div);
    });
  }

  function renderGrafico(leituras) {
    const caixa = $("grafico");
    caixa.textContent = "";
    if (!leituras.length) {
      const p = document.createElement("p");
      p.className = "vazio";
      p.textContent = "Ainda não há leituras para este dispositivo.";
      caixa.appendChild(p);
      $("legenda-grafico").textContent = "";
      return;
    }
    const ordem = leituras.slice().reverse();
    const valores = ordem.map((l) => Number(l.corrente_rms_a));
    const max = Math.max(...valores, 1);
    const W = 900, H = 220, P = 24;
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 " + W + " " + H);
    svg.setAttribute("preserveAspectRatio", "none");
    const pontos = valores.map((v, i) => {
      const x = P + (i * (W - 2 * P)) / Math.max(valores.length - 1, 1);
      const y = H - P - (v / max) * (H - 2 * P);
      return x.toFixed(1) + "," + y.toFixed(1);
    }).join(" ");
    const linha = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
    linha.setAttribute("points", pontos);
    linha.setAttribute("fill", "none");
    linha.setAttribute("stroke", "#2563eb");
    linha.setAttribute("stroke-width", "2");
    svg.appendChild(linha);
    caixa.appendChild(svg);
    const ultima = valores[valores.length - 1];
    $("legenda-grafico").textContent =
      "Última leitura: " + ultima.toFixed(2) + " A · Máximo no período: " + max.toFixed(2) + " A";
  }

  $("form-senha").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const msg = $("msg-senha");
    msg.className = "msg";
    msg.textContent = "";
    try {
      await api("/v1/auth/senha", {
        method: "POST",
        body: JSON.stringify({ senha_atual: $("senha-atual").value, senha_nova: $("senha-nova").value })
      });
      msg.className = "msg ok";
      msg.textContent = "Senha alterada. Entre de novo com a senha nova.";
      $("form-senha").reset();
      setTimeout(sair, 1500);
    } catch (e) {
      msg.className = "msg erro";
      msg.textContent = e.message;
    }
  });

  if (token()) {
    mostrarTela(true);
    carregarDispositivos();
  } else {
    mostrarTela(false);
  }
})();
</script>
</body>
</html>
"""
