// Tela e leitura do banco. Classificação, simulação e regras de copa vêm de calculos.js.

// Chave publishable: feita para ficar no navegador; o RLS só libera leitura.
const SUPABASE_URL = "https://lwamaovuxcevsjfvtqhf.supabase.co";
const SUPABASE_KEY = "sb_publishable_j0O_u0t7-lDCtBbmqaIz3A_8vAIGcyJ";
const SIMULACOES = 10000;
const LIGAS = [
  ["serie_a", "Série A"],
  ["serie_b", "Série B"],
  ["parazao", "Parazão"],
  ["copa_verde", "Copa Verde"],
];

// Cores das faixas do ge, trocadas por tons mais legíveis.
const CORES = { "#0000ff": "#2563eb", "#00ffff": "#06b6d4", "#008040": "#16a34a", "#ff0000": "#dc2626" };
const cor = c => CORES[c] || c;

const dados = {};       // liga -> { info, clubes, partidas, sim }
const escolhido = {};   // liga -> id do time escolhido
let liga = "serie_a";
let graficoPosicoes = null;
let graficoPontos = null;

async function ler(tabela, query) {
  const r = await fetch(`${SUPABASE_URL}/rest/v1/${tabela}?${query}`, {
    headers: { apikey: SUPABASE_KEY },
  });
  if (!r.ok) throw new Error(`${tabela}: ${r.status}`);
  return r.json();
}

// ---------- tela ----------

const pct = x => x > 0 && x < 0.005 ? "<1%" : x < 1 && x > 0.995 ? ">99%" : Math.round(x * 100) + "%";
const $ = id => document.getElementById(id);

function zonaDaPosicao(zonas, pos) {
  return zonas.find(z => z.posicoes.includes(pos));
}

function preencherTimes() {
  const d = dados[liga];
  const ids = Object.keys(d.clubes).map(Number);
  if (!escolhido[liga]) escolhido[liga] = timePadrao(d.clubes, d.sim?.tabela);
  $("time").innerHTML = ids
    .sort((a, b) => d.clubes[a].nome.localeCompare(d.clubes[b].nome, "pt-BR"))
    .map(id => `<option value="${id}" ${id === escolhido[liga] ? "selected" : ""}>${d.clubes[id].nome}</option>`)
    .join("");
}

function desenhar() {
  const copa = dados[liga].info.tipo === "copa";
  $("vista-pontos").hidden = copa;
  $("vista-copa").hidden = !copa;
  if (copa) desenharCopa(); else desenharPontos();
}

// ---------- copas e estaduais ----------

const placar = p => {
  if (p.gols_casa == null) return "×";
  const pen = p.pen_casa != null ? ` <small>(pên ${p.pen_casa}×${p.pen_fora})</small>` : "";
  return `${p.gols_casa} × ${p.gols_fora}${pen}`;
};

function desenharCopa() {
  const d = dados[liga];
  const id = escolhido[liga];
  const nome = x => d.clubes[x]?.nome ?? x;
  const escudo = x => d.clubes[x]?.escudo ? `<img src="${d.clubes[x].escudo}" alt="">` : "";
  const meus = d.partidas.filter(p => p.casa_id === id || p.fora_id === id);
  let v = 0, e = 0, dr = 0, gp = 0, gc = 0;
  for (const p of meus.filter(p => p.encerrada)) {
    const [a, b] = p.casa_id === id ? [p.gols_casa, p.gols_fora] : [p.gols_fora, p.gols_casa];
    gp += a; gc += b;
    if (a > b) v++; else if (a === b) e++; else dr++;
  }
  const c = campeao(d);

  $("atualizado").textContent =
    `${d.info.nome} · dados de ${new Date(d.info.atualizado_em).toLocaleString("pt-BR")}`;

  $("cards").innerHTML = [
    ["Campanha", campanha(d, id)],
    ["Campeão", c ? nome(c) : "A definir"],
    ["Jogos", meus.length],
    ["V · E · D", `${v} · ${e} · ${dr}`],
    ["Gols pró · contra", `${gp} · ${gc}`],
  ].map(([k, val]) => `<div class="card"><span>${k}</span><strong>${val}</strong></div>`).join("");

  $("titulo-jogos").textContent = `Jogos — ${nome(id)}`;
  $("jogos-copa").innerHTML = meus.length === 0 ? "<tr><td>Nenhum jogo.</td></tr>" :
    "<tr><th>Fase</th><th>Data</th><th>Jogo</th></tr>" + meus.map(p => {
      const dia = p.data ? new Date(p.data).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" }) : "";
      return `<tr><td>${p.fase}${p.chave && !p.chave.startsWith(p.fase) ? ` · ${p.chave}` : ""}</td><td>${dia}</td>
        <td class="jogo">${nome(p.casa_id)} ${placar(p)} ${nome(p.fora_id)}</td></tr>`;
    }).join("");

  $("fases").innerHTML = [...d.info.fases].reverse().map(f => {
    let corpo;
    if (f.tipo === "pontos") {
      corpo = f.grupos.map(g => `
        ${f.grupos.length > 1 ? `<h3>${g.nome}</h3>` : ""}
        <div class="rolagem"><table>
          <tr><th>#</th><th>Time</th><th>P</th><th>J</th><th>V</th><th>E</th><th>D</th><th>SG</th></tr>
          ${g.times.map((t, i) => {
            const z = zonaDaPosicao(g.zonas, i + 1);
            return `<tr class="${t.id === id ? "escolhido" : ""}" data-id="${t.id}">
              <td style="border-left:4px solid ${z ? cor(z.cor) : "transparent"}">${i + 1}</td>
              <td>${escudo(t.id)}${nome(t.id)}</td><td>${t.pontos}</td><td>${t.jogos}</td>
              <td>${t.vitorias}</td><td>${t.empates}</td><td>${t.derrotas}</td><td>${t.saldo}</td></tr>`;
          }).join("")}
        </table></div>`).join("");
    } else {
      const chaves = chavesDaFase(d.partidas, f.nome);
      corpo = Object.keys(chaves).length === 0 ? `<p class="nota">Confrontos a definir.</p>` :
        `<div class="chaves">${Object.values(chaves).map(js => {
          const w = vencedor(js);
          return `<div class="chave">${js.map(p => `<div class="${[p.casa_id, p.fora_id].includes(id) ? "escolhido" : ""}">
            <span class="${w === p.casa_id ? "vence" : ""}">${nome(p.casa_id)}</span> ${placar(p)}
            <span class="${w === p.fora_id ? "vence" : ""}">${nome(p.fora_id)}</span></div>`).join("")}</div>`;
        }).join("")}</div>`;
    }
    return `<section><h2>${f.nome}</h2>${corpo}</section>`;
  }).join("");
}

// ---------- pontos corridos ----------

function desenharPontos() {
  const d = dados[liga];
  const { res, modelo, futuros, base, tabela } = d.sim;
  const zonas = d.info.zonas;
  const id = escolhido[liga];
  const nome = x => d.clubes[x]?.nome ?? x;
  const escudo = x => d.clubes[x]?.escudo ? `<img src="${d.clubes[x].escudo}" alt="">` : "";
  const time = res[id];
  const n = tabela.length;

  $("atualizado").textContent =
    `${d.info.nome} · rodada ${d.info.rodada_atual} · dados de ${new Date(d.info.atualizado_em).toLocaleString("pt-BR")}`;

  $("cards").innerHTML = [
    ["Posição atual", `${tabela.findIndex(t => t.id === id) + 1}º`],
    ["Pontos", base[id].PTS],
    ["Pontos esperados", time.pontos.toFixed(1)],
    ["Título", pct(time.posicoes[0])],
    ...zonas.map((z, i) => [z.nome, pct(time.zonas[i]), cor(z.cor)]),
  ].map(([k, v, c]) =>
    `<div class="card" ${c ? `style="border-top:4px solid ${c}"` : ""}><span>${k}</span><strong>${v}</strong></div>`).join("");

  $("nota-sim").textContent =
    `${SIMULACOES.toLocaleString("pt-BR")} campeonatos simulados com os ${futuros.length} jogos restantes.`;

  const opcoesPos = {
    chart: { type: "bar", height: 280, toolbar: { show: false }, animations: { enabled: false } },
    series: [{ name: "Chance", data: time.posicoes.map(x => +(x * 100).toFixed(1)) }],
    xaxis: { categories: time.posicoes.map((_, i) => `${i + 1}º`), title: { text: `Posição final — ${nome(id)}` } },
    yaxis: { labels: { formatter: v => v.toFixed(0) + "%" } },
    dataLabels: { enabled: false },
    colors: [({ dataPointIndex: i }) => cor(zonaDaPosicao(zonas, i + 1)?.cor) || "#94a3b8"],
    tooltip: { y: { formatter: v => v + "%" } },
  };
  if (graficoPosicoes) graficoPosicoes.updateOptions(opcoesPos);
  else (graficoPosicoes = new ApexCharts($("grafico-posicoes"), opcoesPos)).render();

  let total = 0;
  const pontos = d.partidas
    .filter(p => p.encerrada && (p.casa_id === id || p.fora_id === id))
    .map(p => {
      const [meus, deles] = p.casa_id === id ? [p.gols_casa, p.gols_fora] : [p.gols_fora, p.gols_casa];
      total += meus > deles ? 3 : meus === deles ? 1 : 0;
      return { x: `R${p.rodada}`, y: total };
    });
  $("titulo-pontos").textContent = `Pontos por rodada — ${nome(id)}`;
  const opcoesPontos = {
    chart: { type: "line", height: 260, toolbar: { show: false } },
    series: [{ name: "Pontos", data: pontos }],
    stroke: { width: 3 },
    markers: { size: 3 },
    colors: ["#0b2a5b"],
  };
  if (graficoPontos) graficoPontos.updateOptions(opcoesPontos);
  else (graficoPontos = new ApexCharts($("grafico-pontos"), opcoesPontos)).render();

  const meus = futuros.filter(p => p.casa_id === id || p.fora_id === id);
  $("proximos").innerHTML = meus.length === 0 ? "<tr><td>Sem jogos restantes.</td></tr>" :
    `<tr><th>Rodada</th><th>Jogo</th><th>Vitória</th><th>Empate</th><th>Derrota</th></tr>` +
    meus.map(p => {
      const [v, e, dr] = prob1x2(...lambdas(modelo, p.casa_id, p.fora_id));
      const [vt, dt] = p.casa_id === id ? [v, dr] : [dr, v];
      const dia = p.data ? new Date(p.data).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" }) : "";
      return `<tr><td>${p.rodada}<br><small>${dia}</small></td><td>${nome(p.casa_id)} × ${nome(p.fora_id)}</td>
        <td>${pct(vt)}</td><td>${pct(e)}</td><td>${pct(dt)}</td></tr>`;
    }).join("");

  $("tabela").innerHTML =
    `<tr><th>#</th><th>Time</th><th>P</th><th>J</th><th>V</th><th>SG</th><th>Pts esp.</th><th>Título</th>` +
    zonas.map(z => `<th>${z.nome}</th>`).join("") + "</tr>" +
    tabela.map((t, i) => {
      const r = res[t.id];
      const z = zonaDaPosicao(zonas, i + 1);
      return `<tr class="${t.id === id ? "escolhido" : ""}" data-id="${t.id}">
        <td style="border-left:4px solid ${z ? cor(z.cor) : "transparent"}">${i + 1}</td>
        <td>${escudo(t.id)}${nome(t.id)}</td>
        <td>${t.PTS}</td><td>${t.J}</td><td>${t.V}</td><td>${t.GP - t.GC}</td>
        <td>${r.pontos.toFixed(1)}</td><td>${pct(r.posicoes[0])}</td>` +
        r.zonas.map(p => `<td>${pct(p)}</td>`).join("") + "</tr>";
    }).join("");

  $("legenda").innerHTML = zonas.map(z =>
    `<span class="legenda" style="background:${cor(z.cor)}"></span>${z.nome} (${z.posicoes.length > 1 ? `${z.posicoes[0]}º–${z.posicoes.at(-1)}º` : `${z.posicoes[0]}º`})`)
    .join(" &nbsp; ") + " · Clique numa linha para escolher o time.";
}

// Simula a liga só na primeira vez que ela é aberta (AD-simulacao-sob-demanda).
function garantirSimulacao(l) {
  const d = dados[l];
  if (d.info.tipo !== "copa" && !d.sim) d.sim = simular(d, { simulacoes: SIMULACOES });
}

function trocarLiga(nova) {
  liga = nova;
  garantirSimulacao(liga);
  document.querySelectorAll("#abas button").forEach(b => b.classList.toggle("ativa", b.dataset.liga === liga));
  preencherTimes();
  desenhar();
}

async function carregar(l) {
  const [info, clubes, partidas] = await Promise.all([
    ler("remo_ligas", `liga=eq.${l}`),
    ler("remo_clubes", `liga=eq.${l}`),
    ler("remo_partidas", `liga=eq.${l}&order=fase_ordem.asc,data.asc,partida_id.asc`),
  ]);
  if (!info[0]) return;  // liga ainda não carregada no banco
  const d = { info: info[0], clubes: Object.fromEntries(clubes.map(c => [c.id, c])), partidas };
  dados[l] = d;
}

async function iniciar() {
  try {
    await Promise.all(LIGAS.map(([l]) => carregar(l)));
    $("abas").innerHTML = LIGAS.filter(([l]) => dados[l])
      .map(([l, nome]) => `<button data-liga="${l}">${nome}</button>`).join("");
    // Abre na série (pontos corridos) em que o Remo está neste ano.
    const doRemo = LIGAS.map(([l]) => l).find(l => dados[l]?.info.tipo === "pontos" && dados[l].clubes[REMO]);
    trocarLiga(doRemo ?? Object.keys(dados)[0]);
  } catch (e) {
    $("atualizado").textContent = "Não foi possível carregar os dados.";
    console.error(e);
  }
}

$("abas").addEventListener("click", e => {
  const b = e.target.closest("button[data-liga]");
  if (b) trocarLiga(b.dataset.liga);
});

$("time").addEventListener("change", e => { escolhido[liga] = +e.target.value; desenhar(); });

// Clique numa linha de qualquer tabela escolhe o time.
document.querySelector("main").addEventListener("click", e => {
  const tr = e.target.closest("tr[data-id]");
  if (!tr) return;
  escolhido[liga] = +tr.dataset.id;
  preencherTimes();
  desenhar();
  window.scrollTo({ top: 0, behavior: "smooth" });
});

$("simular").addEventListener("click", e => {
  e.target.disabled = true;
  setTimeout(() => {
    dados[liga].sim = simular(dados[liga], { simulacoes: SIMULACOES });
    desenhar();
    e.target.disabled = false;
  }, 20);
});

iniciar();
