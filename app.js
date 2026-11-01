// Chave publishable: feita para ficar no navegador; o RLS só libera leitura.
const SUPABASE_URL = "https://lwamaovuxcevsjfvtqhf.supabase.co";
const SUPABASE_KEY = "sb_publishable_j0O_u0t7-lDCtBbmqaIz3A_8vAIGcyJ";
const REMO = 364;
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

// ---------- classificação ----------

function tabelaVazia(clubes) {
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

function forcas(clubes, jogados) {
  let golsCasa = 0, golsFora = 0;
  for (const p of jogados) { golsCasa += p.gols_casa; golsFora += p.gols_fora; }
  const n = Math.max(jogados.length, 1);
  const mediaCasa = golsCasa / n || 1.4, mediaFora = golsFora / n || 1.1;
  const media = (mediaCasa + mediaFora) / 2;

  const t = tabelaVazia(clubes);
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
  const fat = [1, 1, 2, 6, 24, 120, 720, 5040, 40320, 362880, 3628800];
  const pmf = (l, k) => Math.exp(-l) * l ** k / fat[k];
  let v = 0, e = 0, d = 0;
  for (let i = 0; i <= 10; i++) for (let j = 0; j <= 10; j++) {
    const p = pmf(lc, i) * pmf(lf, j);
    if (i > j) v += p; else if (i === j) e += p; else d += p;
  }
  const s = v + e + d;
  return [v / s, e / s, d / s];
}

// ---------- Monte Carlo ----------

function simular(d) {
  const jogados = d.partidas.filter(p => p.encerrada);
  const futuros = d.partidas.filter(p => !p.encerrada);
  const modelo = forcas(d.clubes, jogados);
  const base = tabelaVazia(d.clubes);
  for (const p of jogados) somarJogo(base, p.casa_id, p.fora_id, p.gols_casa, p.gols_fora);

  const ids = Object.keys(d.clubes).map(Number);
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
    r.zonas = d.info.zonas.map(z => z.posicoes.reduce((a, p) => a + (r.posicoes[p - 1] || 0), 0));
  }
  return { res, modelo, futuros, base, tabela: ordenar(structuredClone(base)) };
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
  if (!escolhido[liga]) escolhido[liga] = d.clubes[REMO] ? REMO : (d.sim ? d.sim.tabela[0].id : ids[0]);
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

// Quem passou no confronto: soma dos gols e, se empatar, pênaltis do último jogo.
function vencedor(jogos) {
  if (!jogos.length || jogos.some(p => !p.encerrada)) return null;
  const gols = {};
  for (const p of jogos) {
    gols[p.casa_id] = (gols[p.casa_id] || 0) + p.gols_casa;
    gols[p.fora_id] = (gols[p.fora_id] || 0) + p.gols_fora;
  }
  const [a, b] = Object.keys(gols).map(Number);
  if (gols[a] !== gols[b]) return gols[a] > gols[b] ? a : b;
  const u = jogos.at(-1);
  if (u.pen_casa == null) return null;
  return u.pen_casa > u.pen_fora ? u.casa_id : u.fora_id;
}

function chavesDaFase(partidas, fase) {
  const chaves = {};
  for (const p of partidas.filter(p => p.fase === fase)) (chaves[p.chave] ??= []).push(p);
  return chaves;
}

function campanha(d, id) {
  const fases = d.info.fases;
  const joga = f => d.partidas.some(p => p.fase === f.nome && (p.casa_id === id || p.fora_id === id)) ||
    f.grupos.some(g => g.times.some(t => t.id === id));
  const i = fases.map(joga).lastIndexOf(true);
  if (i < 0) return "Não participou";
  const fase = fases[i];
  const temDepois = fases.slice(i + 1).some(f => d.partidas.some(p => p.fase === f.nome));
  if (fase.tipo === "mata") {
    const minha = Object.values(chavesDaFase(d.partidas, fase.nome))
      .find(js => js.some(p => p.casa_id === id || p.fora_id === id));
    const v = vencedor(minha || []);
    if (v === null) return `Disputando: ${fase.nome}`;
    if (i === fases.length - 1) return v === id ? "Campeão 🏆" : "Vice-campeão";
    return v === id ? `Classificado na ${fase.nome}` : `Eliminado: ${fase.nome}`;
  }
  const encerrada = d.partidas.filter(p => p.fase === fase.nome).every(p => p.encerrada);
  if (!encerrada) return `Disputando: ${fase.nome}`;
  return temDepois ? `Eliminado: ${fase.nome}` : `Encerrou na ${fase.nome}`;
}

function campeao(d) {
  const final = d.info.fases.at(-1);
  if (!final || final.tipo !== "mata") return null;
  const chaves = Object.values(chavesDaFase(d.partidas, final.nome));
  return chaves.length === 1 ? vencedor(chaves[0]) : null;
}

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

function trocarLiga(nova) {
  liga = nova;
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
  if (d.info.tipo !== "copa") d.sim = simular(d);
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
    dados[liga].sim = simular(dados[liga]);
    desenhar();
    e.target.disabled = false;
  }, 20);
});

iniciar();
