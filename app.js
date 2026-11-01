// Chave publishable: feita para ficar no navegador; o RLS só libera leitura.
const SUPABASE_URL = "https://lwamaovuxcevsjfvtqhf.supabase.co";
const SUPABASE_KEY = "sb_publishable_j0O_u0t7-lDCtBbmqaIz3A_8vAIGcyJ";
const REMO = 364;
const SIMULACOES = 10000;

let clubes = {};
let partidas = [];
let graficoPosicoes = null;

async function ler(tabela, query = "select=*") {
  const r = await fetch(`${SUPABASE_URL}/rest/v1/${tabela}?${query}`, {
    headers: { apikey: SUPABASE_KEY },
  });
  if (!r.ok) throw new Error(`${tabela}: ${r.status}`);
  return r.json();
}

// ---------- classificação ----------

function tabelaVazia() {
  const t = {};
  for (const id of Object.keys(clubes)) t[id] = { id: +id, PTS: 0, J: 0, V: 0, E: 0, D: 0, GP: 0, GC: 0 };
  return t;
}

function somarJogo(t, casa, fora, gc, gf) {
  const c = t[casa], f = t[fora];
  c.J++; f.J++;
  c.GP += gc; c.GC += gf; f.GP += gf; f.GC += gc;
  if (gc > gf) { c.V++; c.PTS += 3; f.D++; }
  else if (gc < gf) { f.V++; f.PTS += 3; c.D++; }
  else { c.E++; f.E++; c.PTS++; f.PTS++; }
}

function ordenar(t) {
  return Object.values(t).sort((a, b) =>
    b.PTS - a.PTS || b.V - a.V || (b.GP - b.GC) - (a.GP - a.GC) || b.GP - a.GP || Math.random() - .5);
}

// ---------- modelo Poisson simples ----------
// Força de ataque/defesa de cada time = gols por jogo / média da liga,
// puxada para a média com K jogos "fantasmas" para não exagerar no início.

const K = 5;

function forcas(jogados) {
  let golsCasa = 0, golsFora = 0;
  for (const p of jogados) { golsCasa += p.gols_casa; golsFora += p.gols_fora; }
  const n = Math.max(jogados.length, 1);
  const mediaCasa = golsCasa / n || 1.4, mediaFora = golsFora / n || 1.1;
  const media = (mediaCasa + mediaFora) / 2;

  const t = tabelaVazia();
  for (const p of jogados) somarJogo(t, p.casa_id, p.fora_id, p.gols_casa, p.gols_fora);
  const f = {};
  for (const s of Object.values(t)) {
    f[s.id] = {
      ataque: (s.GP + K * media) / (s.J + K) / media,
      defesa: (s.GC + K * media) / (s.J + K) / media,
    };
  }
  return { f, mediaCasa, mediaFora };
}

function lambdas(m, casa, fora) {
  return [
    m.mediaCasa * m.f[casa].ataque * m.f[fora].defesa,
    m.mediaFora * m.f[fora].ataque * m.f[casa].defesa,
  ];
}

function poisson(l) {
  const L = Math.exp(-l);
  let k = 0, p = 1;
  do { k++; p *= Math.random(); } while (p > L);
  return k - 1;
}

function prob1x2(lc, lf) {
  const pmf = (l, k) => Math.exp(-l) * l ** k / [1, 1, 2, 6, 24, 120, 720, 5040, 40320, 362880, 3628800][k];
  let v = 0, e = 0, d = 0;
  for (let i = 0; i <= 10; i++) for (let j = 0; j <= 10; j++) {
    const p = pmf(lc, i) * pmf(lf, j);
    if (i > j) v += p; else if (i === j) e += p; else d += p;
  }
  const s = v + e + d;
  return [v / s, e / s, d / s];
}

// ---------- Monte Carlo ----------

function simular() {
  const jogados = partidas.filter(p => p.encerrada);
  const futuros = partidas.filter(p => !p.encerrada);
  const modelo = forcas(jogados);
  const base = tabelaVazia();
  for (const p of jogados) somarJogo(base, p.casa_id, p.fora_id, p.gols_casa, p.gols_fora);

  const ids = Object.keys(clubes).map(Number);
  const n = ids.length;
  const res = {};
  for (const id of ids) res[id] = { pontos: 0, posicoes: new Array(n).fill(0) };
  const lam = futuros.map(p => lambdas(modelo, p.casa_id, p.fora_id));

  for (let s = 0; s < SIMULACOES; s++) {
    const t = structuredClone(base);
    futuros.forEach((p, i) => somarJogo(t, p.casa_id, p.fora_id, poisson(lam[i][0]), poisson(lam[i][1])));
    ordenar(t).forEach((time, pos) => {
      res[time.id].pontos += time.PTS;
      res[time.id].posicoes[pos]++;
    });
  }

  for (const id of ids) {
    const r = res[id];
    r.pontos /= SIMULACOES;
    r.posicoes = r.posicoes.map(x => x / SIMULACOES);
    r.titulo = r.posicoes[0];
    r.g6 = r.posicoes.slice(0, 6).reduce((a, b) => a + b, 0);
    r.z4 = r.posicoes.slice(n - 4).reduce((a, b) => a + b, 0);
  }
  return { res, modelo, futuros, base };
}

// ---------- tela ----------

const pct = x => x > 0 && x < 0.005 ? "<1%" : x < 1 && x > 0.995 ? ">99%" : Math.round(x * 100) + "%";
const nome = id => clubes[id]?.nome ?? id;
const escudo = id => clubes[id]?.escudo ? `<img src="${clubes[id].escudo}" alt="">` : "";

function desenhar() {
  const { res, modelo, futuros, base } = simular();
  const tabela = ordenar(structuredClone(base));
  const posRemo = tabela.findIndex(t => t.id === REMO) + 1;
  const remo = res[REMO];
  const n = tabela.length;

  document.getElementById("cards").innerHTML = [
    ["Posição atual", `${posRemo}º`],
    ["Pontos", base[REMO].PTS],
    ["Pontos esperados", remo.pontos.toFixed(1)],
    ["Chance de G6", pct(remo.g6)],
    ["Chance de Z4", pct(remo.z4)],
    ["Chance de título", pct(remo.titulo)],
  ].map(([k, v]) => `<div class="card"><span>${k}</span><strong>${v}</strong></div>`).join("");

  document.getElementById("nota-sim").textContent =
    `${SIMULACOES.toLocaleString("pt-BR")} campeonatos simulados com os ${futuros.length} jogos restantes.`;

  const opcoesPos = {
    chart: { type: "bar", height: 280, toolbar: { show: false }, animations: { enabled: false } },
    series: [{ name: "Chance", data: remo.posicoes.map(x => +(x * 100).toFixed(1)) }],
    xaxis: { categories: remo.posicoes.map((_, i) => `${i + 1}º`), title: { text: "Posição final do Remo" } },
    yaxis: { labels: { formatter: v => v.toFixed(0) + "%" } },
    dataLabels: { enabled: false },
    colors: [({ dataPointIndex: i }) => (i < 6 ? "#1a7f37" : i >= n - 4 ? "#c0362c" : "#0b2a5b")],
    tooltip: { y: { formatter: v => v + "%" } },
  };
  if (graficoPosicoes) graficoPosicoes.updateOptions(opcoesPos);
  else (graficoPosicoes = new ApexCharts(document.getElementById("grafico-posicoes"), opcoesPos)).render();

  document.getElementById("proximos").innerHTML =
    "<tr><th>Rodada</th><th>Jogo</th><th>Vitória Remo</th><th>Empate</th><th>Derrota</th></tr>" +
    futuros.filter(p => p.casa_id === REMO || p.fora_id === REMO).map(p => {
      const [v, e, d] = prob1x2(...lambdas(modelo, p.casa_id, p.fora_id));
      const [vr, dr] = p.casa_id === REMO ? [v, d] : [d, v];
      return `<tr><td>${p.rodada}</td><td>${nome(p.casa_id)} × ${nome(p.fora_id)}</td>
        <td>${pct(vr)}</td><td>${pct(e)}</td><td>${pct(dr)}</td></tr>`;
    }).join("");

  document.getElementById("tabela").innerHTML =
    "<tr><th>#</th><th>Time</th><th>P</th><th>J</th><th>V</th><th>SG</th><th>Pts esp.</th><th>G6</th><th>Z4</th><th>Título</th></tr>" +
    tabela.map((t, i) => {
      const r = res[t.id];
      const cls = [t.id === REMO ? "remo" : "", i < 6 ? "g6" : i >= n - 4 ? "z4" : ""].join(" ");
      return `<tr class="${cls}"><td>${i + 1}</td><td>${escudo(t.id)}${nome(t.id)}</td>
        <td>${t.PTS}</td><td>${t.J}</td><td>${t.V}</td><td>${t.GP - t.GC}</td>
        <td>${r.pontos.toFixed(1)}</td><td>${pct(r.g6)}</td><td>${pct(r.z4)}</td><td>${pct(r.titulo)}</td></tr>`;
    }).join("");
}

function desenharPontos() {
  let total = 0;
  const pontos = partidas
    .filter(p => p.encerrada && (p.casa_id === REMO || p.fora_id === REMO))
    .sort((a, b) => new Date(a.data) - new Date(b.data))
    .map(p => {
      const [meus, deles] = p.casa_id === REMO ? [p.gols_casa, p.gols_fora] : [p.gols_fora, p.gols_casa];
      total += meus > deles ? 3 : meus === deles ? 1 : 0;
      return { x: `R${p.rodada}`, y: total };
    });
  new ApexCharts(document.getElementById("grafico-pontos"), {
    chart: { type: "line", height: 260, toolbar: { show: false } },
    series: [{ name: "Pontos", data: pontos }],
    stroke: { width: 3 },
    markers: { size: 3 },
    colors: ["#0b2a5b"],
  }).render();
}

async function iniciar() {
  try {
    const [cs, ps, at] = await Promise.all([
      ler("remo_clubes"),
      ler("remo_partidas", "select=*&order=data.asc"),
      ler("remo_atualizacao"),
    ]);
    clubes = Object.fromEntries(cs.map(c => [c.id, c]));
    partidas = ps;
    const quando = at[0] ? new Date(at[0].executado_em).toLocaleString("pt-BR") : "—";
    document.getElementById("atualizado").textContent = `Dados atualizados em ${quando}`;
    desenharPontos();
    desenhar();
  } catch (e) {
    document.getElementById("atualizado").textContent = "Não foi possível carregar os dados.";
    console.error(e);
  }
}

document.getElementById("simular").addEventListener("click", e => {
  e.target.disabled = true;
  setTimeout(() => { desenhar(); e.target.disabled = false; }, 20);
});

iniciar();
