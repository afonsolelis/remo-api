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
const NOTICIAS = "noticias";  // abas que não são campeonato
const PROXIMOS = "proximos-jogos";
const RESULTADOS = "resultados";
const periodo = { de: null, ate: null };  // filtro de datas da aba Resultados passados ("AAAA-MM-DD")
let noticias = null;          // linhas de remo_noticias, lidas na primeira vez que a aba abre
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

// Mesmo ponto de quebra do style.css (docs/especificacao/interface-celular.md).
const CELULAR = matchMedia("(max-width: 600px)");
const fonte = () => ({ fontSize: CELULAR.matches ? "14px" : "12px" });

const pct = x => x > 0 && x < 0.005 ? "<1%" : x < 1 && x > 0.995 ? ">99%" : Math.round(x * 100) + "%";
const $ = id => document.getElementById(id);

// Texto vindo do ge entra na página sempre escapado.
const esc = t => String(t ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

// Todos os clubes de todos os campeonatos (o mesmo id pode estar em vários).
function todosOsClubes() {
  const clubes = {};
  for (const d of Object.values(dados)) Object.assign(clubes, d.clubes);
  return clubes;
}

function zonaDaPosicao(zonas, pos) {
  return zonas.find(z => z.posicoes.includes(pos));
}

function preencherTimes() {
  if (liga === PROXIMOS || liga === RESULTADOS) return preencherClubesCalendario();
  if (liga === NOTICIAS) return preencherClubesNoticias();
  const d = dados[liga];
  const ids = Object.keys(d.clubes).map(Number);
  if (!escolhido[liga]) escolhido[liga] = timePadrao(d.clubes, d.sim?.tabela);
  $("time").innerHTML = ids
    .sort((a, b) => d.clubes[a].nome.localeCompare(d.clubes[b].nome, "pt-BR"))
    .map(id => `<option value="${id}" ${id === escolhido[liga] ? "selected" : ""}>${d.clubes[id].nome}</option>`)
    .join("");
}

function desenhar() {
  const vista = liga === NOTICIAS ? "noticias" : liga === PROXIMOS ? "calendario" : liga === RESULTADOS ? "resultados" :
    dados[liga].info.tipo === "copa" ? "copa" : "pontos";
  for (const v of ["pontos", "copa", "noticias", "calendario", "resultados"]) $(`vista-${v}`).hidden = v !== vista;
  $("cards").hidden = vista === "noticias" || vista === "calendario" || (vista === "resultados" && !escolhido[RESULTADOS]);
  ({ pontos: desenharPontos, copa: desenharCopa, noticias: desenharNoticias, calendario: desenharCalendario,
    resultados: desenharResultados })[vista]();
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

// ---------- próximos jogos ----------

function preencherClubesCalendario() {
  const clubes = todosOsClubes();
  if (escolhido[liga] === undefined) escolhido[liga] = 0;  // abre com todos os clubes
  $("time").innerHTML = `<option value="0">Todos os clubes</option>` + Object.keys(clubes).map(Number)
    .sort((a, b) => clubes[a].nome.localeCompare(clubes[b].nome, "pt-BR"))
    .map(id => `<option value="${id}" ${id === escolhido[liga] ? "selected" : ""}>${esc(clubes[id].nome)}</option>`)
    .join("");
}

function atualizadoTodos() {
  const recente = Object.values(dados).map(d => d.info.atualizado_em).sort().at(-1);
  $("atualizado").textContent = recente ? `Jogos de todos os campeonatos · dados de ${new Date(recente).toLocaleString("pt-BR")}` : "";
}

function desenharCalendario() {
  const hoje = diaEmBelem(Date.now());
  const fimDoAno = `${hoje.slice(0, 4)}-12-31`;
  const id = escolhido[PROXIMOS];
  const dias = calendario(dados, hoje, fimDoAno, id);
  atualizadoTodos();
  const total = dias.reduce((n, d) => n + d.jogos.length, 0);
  $("titulo-calendario").textContent = `Próximos jogos${id ? ` — ${todosOsClubes()[id]?.nome ?? ""}` : ""} · ` +
    (total ? `${total} até 31/12` : "nenhum até 31/12");
  $("jogos-calendario").innerHTML = listaPorDia(dias, hoje);
}

// ---------- resultados passados ----------

function desenharResultados() {
  const hoje = diaEmBelem(Date.now());
  if (!periodo.de) {  // abre com o ano todo até hoje
    periodo.de = `${hoje.slice(0, 4)}-01-01`;
    periodo.ate = hoje;
    $("data-de").value = periodo.de;
    $("data-ate").value = periodo.ate;
  }
  $("data-de").max = $("data-ate").max = hoje;
  const id = escolhido[RESULTADOS];
  const dias = resultados(dados, periodo.de, periodo.ate, id);
  const jogos = dias.flatMap(d => d.jogos);
  atualizadoTodos();
  $("titulo-resultados").textContent = `Resultados passados${id ? ` — ${todosOsClubes()[id]?.nome ?? ""}` : ""} · ` +
    (jogos.length ? `${jogos.length} jogo${jogos.length > 1 ? "s" : ""}` : "nenhum jogo");

  if (id) {
    const r = retrospecto(jogos, id);
    $("cards").innerHTML = [
      ["Jogos", r.J],
      ["V · E · D", `${r.V} · ${r.E} · ${r.D}`],
      ["Gols pró · contra", `${r.GP} · ${r.GC}`],
      ["Aproveitamento", r.J ? Math.round((r.V * 3 + r.E) / (r.J * 3) * 100) + "%" : "–"],
    ].map(([k, v]) => `<div class="card"><span>${k}</span><strong>${v}</strong></div>`).join("");
  }
  $("jogos-resultados").innerHTML = dias.length ? listaPorDia(dias, hoje) :
    `<section><p class="nota">Nenhum jogo encerrado neste período.</p></section>`;
}

// Jogos agrupados por dia, no formato de calendario() e resultados().
function listaPorDia(dias, hoje) {
  const nomeDia = x => x === hoje ? "Hoje" : new Date(`${x}T12:00:00-03:00`).toLocaleDateString("pt-BR",
    { timeZone: FUSO, weekday: "long", day: "2-digit", month: "2-digit" });
  const nomeLiga = Object.fromEntries(LIGAS);
  return dias.map(({ dia, jogos }) => `<section><h2>${nomeDia(dia)}</h2>${jogos.map(p => {
    const clubes = dados[p.liga].clubes;
    const ganhou = p.encerrada ? vencedor([p]) : null;
    const lado = (x, escudoAntes) => {
      const c = clubes[x] || {};
      const img = c.escudo ? `<img src="${esc(c.escudo)}" alt="">` : "";
      return `<span class="${x === ganhou ? "vence" : ""}">${escudoAntes ? img : ""}${esc(c.nome ?? x)}${escudoAntes ? "" : " " + img}</span>`;
    };
    const hora = p.hora_definida === false ? `<div class="hora indefinida">Horário a definir</div>` :
      `<div class="hora">${new Date(p.data).toLocaleTimeString("pt-BR", { timeZone: FUSO, hour: "2-digit", minute: "2-digit" })}</div>`;
    const etapa = dados[p.liga].info.tipo === "pontos" ? `${p.rodada}ª rodada` :
      `${esc(p.fase)}${p.chave && !p.chave.startsWith(p.fase) ? ` · ${esc(p.chave)}` : ""}`;
    const detalhes = [p.estadio ? `📍 ${esc(p.estadio)}` : "Local a definir", `${nomeLiga[p.liga]}, ${etapa}`,
      p.link ? `<a href="${esc(p.link)}" target="_blank" rel="noopener">ver no ge</a>` : ""].filter(Boolean).join(" · ");
    return `<div class="jogo-dia ${[p.casa_id, p.fora_id].includes(REMO) ? "escolhido" : ""}">${hora}
      <div class="confronto"><div class="times">${lado(p.casa_id, true)} ${placar(p)} ${lado(p.fora_id, false)}</div>
      <small>${detalhes}</small></div></div>`;
  }).join("")}</section>`).join("");
}

// ---------- notícias ----------

function preencherClubesNoticias() {
  const clubes = todosOsClubes();
  const comNoticia = [...new Set(noticias.map(n => n.clube_id))].filter(id => clubes[id]);
  if (escolhido[NOTICIAS] === undefined) escolhido[NOTICIAS] = comNoticia.includes(REMO) ? REMO : 0;
  $("time").innerHTML = `<option value="0">Todos os clubes</option>` + comNoticia
    .sort((a, b) => clubes[a].nome.localeCompare(clubes[b].nome, "pt-BR"))
    .map(id => `<option value="${id}" ${id === escolhido[NOTICIAS] ? "selected" : ""}>${esc(clubes[id].nome)}</option>`)
    .join("");
}

function desenharNoticias() {
  const clubes = todosOsClubes();
  const id = escolhido[NOTICIAS];
  $("atualizado").textContent = "Notícias do ge, atualizadas a cada 2 horas";
  $("titulo-noticias").textContent = id ? `Notícias — ${clubes[id]?.nome ?? ""}` : "Notícias de todos os clubes";

  // "Todos": a mesma matéria pode ser de dois clubes (um clássico, por exemplo); aparece uma vez.
  const vistas = new Set();
  const lista = noticias
    .filter(n => id ? n.clube_id === id : !vistas.has(n.noticia_id) && vistas.add(n.noticia_id))
    .slice(0, 40);

  $("noticias").innerHTML = lista.length === 0 ? `<p class="nota">Sem notícias deste clube.</p>` :
    lista.map(n => {
      const quando = new Date(n.publicado_em).toLocaleString("pt-BR",
        { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
      const c = clubes[n.clube_id];
      const clube = !id && c ? `${c.escudo ? `<img src="${esc(c.escudo)}" alt="">` : ""}${esc(c.nome)} · ` : "";
      return `<a class="noticia" href="${esc(n.url)}" target="_blank" rel="noopener">
        ${n.imagem ? `<img class="foto" src="${esc(n.imagem)}" alt="" loading="lazy">` : ""}
        <div><strong>${esc(n.titulo)}</strong>
          ${n.resumo ? `<p>${esc(n.resumo)}</p>` : ""}
          <small>${clube}${quando}</small></div></a>`;
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
  const sigla = x => d.clubes[x]?.abreviacao || String(nome(x)).slice(0, 3).toUpperCase();
  // Nome no computador, sigla no celular.
  const rotulo = x => `<span class="nome-longo">${nome(x)}</span><span class="nome-curto">${sigla(x)}</span>`;
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
    xaxis: { categories: time.posicoes.map((_, i) => `${i + 1}º`), labels: { style: fonte() },
      title: { text: `Posição final — ${nome(id)}`, style: fonte() } },
    yaxis: { labels: { formatter: v => v.toFixed(0) + "%", style: fonte() } },
    dataLabels: { enabled: false },
    colors: [({ dataPointIndex: i }) => cor(zonaDaPosicao(zonas, i + 1)?.cor) || "#94a3b8"],
    tooltip: { style: fonte(), y: { formatter: v => v + "%" } },
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
    xaxis: { labels: { style: fonte() } },
    yaxis: { labels: { style: fonte() } },
    tooltip: { style: fonte() },
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
      return `<tr><td>${p.rodada}<br><small>${dia}</small></td><td>${rotulo(p.casa_id)} × ${rotulo(p.fora_id)}</td>
        <td>${pct(vt)}</td><td>${pct(e)}</td><td>${pct(dt)}</td></tr>`;
    }).join("");

  $("tabela").innerHTML =
    `<tr><th>#</th><th>Time</th><th>P</th><th class="sec">J</th><th class="sec">V</th><th class="sec">SG</th>` +
    `<th class="sec">Pts esp.</th><th class="sec">Título</th>` +
    zonas.map(z => `<th title="${z.nome}" style="border-top:3px solid ${cor(z.cor)}">` +
      `<span class="nome-longo">${z.nome}</span><span class="nome-curto">${z.nome.slice(0, 3)}.</span></th>`).join("") + "</tr>" +
    tabela.map((t, i) => {
      const r = res[t.id];
      const z = zonaDaPosicao(zonas, i + 1);
      return `<tr class="${t.id === id ? "escolhido" : ""}" data-id="${t.id}">
        <td style="border-left:4px solid ${z ? cor(z.cor) : "transparent"}">${i + 1}</td>
        <td>${escudo(t.id)}${rotulo(t.id)}</td>
        <td>${t.PTS}</td><td class="sec">${t.J}</td><td class="sec">${t.V}</td><td class="sec">${t.GP - t.GC}</td>
        <td class="sec">${r.pontos.toFixed(1)}</td><td class="sec">${pct(r.posicoes[0])}</td>` +
        r.zonas.map(p => `<td>${pct(p)}</td>`).join("") + "</tr>";
    }).join("");

  // Variação entre a posição atual e a prevista.
  const atual = new Map(tabela.map((t, i) => [t.id, i + 1]));
  const seta = d => d > 0 ? `<span class="sobe">▲${d}</span>` : d < 0 ? `<span class="desce">▼${-d}</span>` : "–";
  $("tabela-prevista").innerHTML =
    `<tr><th>#</th><th>Time</th><th>Pts esp.</th><th>Agora</th><th class="sec">Chance no lugar</th></tr>` +
    tabelaPrevista(res).map((t, i) => {
      const z = zonaDaPosicao(zonas, i + 1);
      return `<tr class="${t.id === id ? "escolhido" : ""}" data-id="${t.id}">
        <td style="border-left:4px solid ${z ? cor(z.cor) : "transparent"}">${i + 1}</td>
        <td>${escudo(t.id)}${rotulo(t.id)}</td>
        <td>${t.pontos.toFixed(1)}</td>
        <td>${atual.get(t.id)}º ${seta(atual.get(t.id) - (i + 1))}</td>
        <td class="sec">${pct(res[t.id].posicoes[i])}</td></tr>`;
    }).join("");

  $("legenda").innerHTML = zonas.map(z =>
    `<span class="legenda" style="background:${cor(z.cor)}"></span>${z.nome} (${z.posicoes.length > 1 ? `${z.posicoes[0]}º–${z.posicoes.at(-1)}º` : `${z.posicoes[0]}º`})`)
    .join(" &nbsp; ") + " · Clique numa linha para escolher o time.";
}

// Simula a liga só na primeira vez que ela é aberta (AD-simulacao-sob-demanda).
function garantirSimulacao(l) {
  const d = dados[l];
  if (!d) return;
  if (d.info.tipo !== "copa" && !d.sim) d.sim = simular(d, { simulacoes: SIMULACOES });
}

async function trocarLiga(nova) {
  if (nova === NOTICIAS && !noticias) {
    try {
      noticias = await ler("remo_noticias", "order=publicado_em.desc");
    } catch (e) {
      $("atualizado").textContent = "Não foi possível carregar as notícias.";
      console.error(e);
      return;
    }
  }
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
      .map(([l, nome]) => `<button data-liga="${l}">${nome}</button>`).join("") +
      `<button data-liga="${PROXIMOS}">Próximos jogos</button><button data-liga="${RESULTADOS}">Resultados passados</button>` +
      `<button data-liga="${NOTICIAS}">Notícias</button>`;
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

// Ao girar o celular ou redimensionar a janela, redesenha os gráficos com a fonte certa.
CELULAR.addEventListener("change", () => { if (dados[liga] || liga === PROXIMOS || liga === RESULTADOS) desenhar(); });

$("time").addEventListener("change", e => { escolhido[liga] = +e.target.value; desenhar(); });

// Filtro de datas dos resultados; se "de" passar de "até", os dois viram o mesmo dia.
for (const campo of ["de", "ate"]) $(`data-${campo}`).addEventListener("change", e => {
  if (!e.target.value) { e.target.value = periodo[campo]; return; }
  periodo[campo] = e.target.value;
  if (periodo.de > periodo.ate) {
    const outro = campo === "de" ? "ate" : "de";
    periodo[outro] = periodo[campo];
    $(`data-${outro}`).value = periodo[campo];
  }
  desenhar();
});

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
