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
const OPERACAO = "operacao";
// Workflows do GitHub que alimentam o banco: arquivo, nome, agenda e horas máximas entre dois sucessos
// (o GitHub costuma atrasar os agendamentos em várias horas).
const REPO = "afonsolelis/remo-api";
const WORKFLOWS = [
  ["dados.yml", "Tabelas e jogos", "todo dia às 00:00 (Belém)", 36],
  ["noticias.yml", "Notícias", "a cada 2 horas", 12],
];
let operacao = null;          // workflow -> { situacao, execucoes } ou { erro }
let pedidoOperacao = null;    // leitura do GitHub em andamento (uma por visita)
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
  if (liga === OPERACAO) return;
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
  pararTimelapse();
  const vista = liga === OPERACAO ? "operacao" : liga === NOTICIAS ? "noticias" : liga === PROXIMOS ? "calendario" : liga === RESULTADOS ? "resultados" :
    dados[liga].info.tipo === "copa" ? "copa" : "pontos";
  for (const v of ["pontos", "copa", "noticias", "calendario", "resultados", "operacao"]) $(`vista-${v}`).hidden = v !== vista;
  $("filtro").hidden = vista === "operacao";
  $("cards").hidden = vista === "noticias" || vista === "operacao" || vista === "calendario" || (vista === "resultados" && !escolhido[RESULTADOS]);
  ({ pontos: desenharPontos, copa: desenharCopa, noticias: desenharNoticias, calendario: desenharCalendario,
    resultados: desenharResultados, operacao: desenharOperacao })[vista]();
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

// ---------- operação ----------

// Lê as execuções direto do GitHub (repositório público, sem chave), para a aba funcionar mesmo com o banco fora.
function carregarOperacao() {
  return pedidoOperacao ??= lerOperacao();
}

async function lerOperacao() {
  const agora = Date.now();
  operacao = Object.fromEntries(await Promise.all(WORKFLOWS.map(async ([arq, , , limite]) => {
    try {
      const r = await fetch(`https://api.github.com/repos/${REPO}/actions/workflows/${arq}/runs?per_page=20`);
      if (!r.ok) throw new Error(`GitHub: ${r.status}`);
      const execucoes = (await r.json()).workflow_runs;
      return [arq, { execucoes, situacao: situacaoWorkflow(execucoes, agora, limite) }];
    } catch (e) {
      console.error(e);
      return [arq, { erro: true }];
    }
  })));
  const problema = Object.values(operacao).some(o => o.erro || ["falha", "atrasado"].includes(o.situacao.estado));
  const botao = document.querySelector(`#abas button[data-liga="${OPERACAO}"]`);
  if (botao) botao.textContent = problema ? "Operação ⚠️" : "Operação";
}

const quando = t => t ? new Date(t).toLocaleString("pt-BR", { timeZone: FUSO, day: "2-digit", month: "2-digit",
  hour: "2-digit", minute: "2-digit" }) : "—";
const ESTADOS = {
  ok: ["ok", "Funcionando"], falha: ["falha", "Falhando"], atrasado: ["atrasado", "Atrasado"],
  "sem-dados": ["atrasado", "Sem execuções"],
};
const RESULTADO = { success: "ok", failure: "falha", timed_out: "tempo esgotado", cancelled: "cancelada",
  skipped: "pulada", startup_failure: "falha ao iniciar" };

function desenharOperacao() {
  $("atualizado").textContent = "Situação das atualizações automáticas do site";
  const ligas = LIGAS.filter(([l]) => dados[l]).map(([l, nome]) =>
    `<tr><td>${nome}</td><td>${quando(dados[l].info.atualizado_em)}</td></tr>`).join("");
  $("dados-banco").innerHTML = ligas ? `<tr><th>Campeonato</th><th>Gravado no banco em</th></tr>${ligas}` :
    `<tr><td>Não foi possível ler o banco.</td></tr>`;

  $("workflows").innerHTML = WORKFLOWS.map(([arq, nome, agenda, limite]) => {
    const o = operacao?.[arq];
    const link = `https://github.com/${REPO}/actions/workflows/${arq}`;
    if (!o) return `<section><h2>${nome}</h2><p class="nota">Carregando…</p></section>`;
    if (o.erro) return `<section><h2>${nome}</h2><p class="nota">Não foi possível ler o GitHub agora.
      <a href="${link}" target="_blank" rel="noopener">Ver no GitHub</a></p></section>`;
    const s = o.situacao;
    const [classe, rotulo] = ESTADOS[s.estado];
    const aviso = s.estado === "falha" ? `${s.falhasSeguidas === 1 ? "A última execução falhou" :
        `As últimas ${s.falhasSeguidas} execuções falharam`}; o site mostra o último dado gravado.`
      : s.estado === "atrasado" ? `Nenhuma execução certa nas últimas ${limite} horas.` : "";
    const linhas = o.execucoes.slice(0, 10).map(e => {
      const res = e.status === "completed" ? RESULTADO[e.conclusion] ?? e.conclusion : "rodando";
      const cls = e.conclusion === "success" ? "ok" : e.status !== "completed" || ["cancelled", "skipped"].includes(e.conclusion) ? "" : "falha";
      return `<tr><td>${quando(e.run_started_at ?? e.created_at)}</td>
        <td>${e.event === "schedule" ? "agendada" : "manual"}</td>
        <td><a class="estado ${cls}" href="${esc(e.html_url)}" target="_blank" rel="noopener">${esc(res)}</a></td></tr>`;
    }).join("");
    return `<section>
      <div class="titulo-secao"><h2>${nome}</h2><span class="estado ${classe}">${rotulo}${s.rodando ? " · rodando" : ""}</span></div>
      <p class="nota">Agenda: ${agenda}. Último sucesso: ${quando(s.ultimoSucesso?.updated_at)}.
        <a href="${link}" target="_blank" rel="noopener">Ver no GitHub</a></p>
      ${aviso ? `<p class="alerta">${aviso}</p>` : ""}
      <div class="rolagem"><table><tr><th>Início (Belém)</th><th>Tipo</th><th>Resultado</th></tr>${linhas}</table></div>
    </section>`;
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

  desenharGraficoPosicoes(time.posicoes, `Posição final — ${nome(id)}`);

  $("titulo-pontos").textContent = `Pontos por rodada — ${nome(id)}`;
  desenharGraficoPontos();
  desenharDispersao();

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

// Chance (0 a 1) de cada posição; `fixo` prende o eixo em 0–100% durante o timelapse.
function desenharGraficoPosicoes(posicoes, titulo, fixo = false) {
  const zonas = dados[liga].info.zonas;
  const opcoes = {
    chart: { type: "bar", height: 280, toolbar: { show: false }, animations: { enabled: false } },
    series: [{ name: "Chance", data: posicoes.map(x => +(x * 100).toFixed(1)) }],
    xaxis: { categories: posicoes.map((_, i) => `${i + 1}º`), labels: { style: fonte() },
      title: { text: titulo, style: fonte() } },
    yaxis: { min: 0, max: fixo ? 100 : undefined, tickAmount: fixo ? 4 : undefined,
      labels: { formatter: v => v.toFixed(0) + "%", style: fonte() } },
    dataLabels: { enabled: false },
    colors: [({ dataPointIndex: i }) => cor(zonaDaPosicao(zonas, i + 1)?.cor) || "#94a3b8"],
    tooltip: { style: fonte(), y: { formatter: v => v + "%" } },
  };
  if (graficoPosicoes) graficoPosicoes.updateOptions(opcoes);
  else (graficoPosicoes = new ApexCharts($("grafico-posicoes"), opcoes)).render();
}

// Pontos reais e projeção (média e faixa de 80%) jogo a jogo, com todas as combinações de resultado.
// `ate` corta o gráfico no jogo `ate` para o timelapse; os eixos ficam fixos para não pular.
let timelapse = null;

function desenharGraficoPontos(ate = Infinity) {
  const d = dados[liga];
  const id = escolhido[liga];
  const { jogos } = projecaoPontos(d.partidas, id, d.sim.modelo);
  const n = jogos.length;
  const ultimoReal = jogos.findLastIndex(j => j.encerrada);
  const visivel = i => i + 1 <= ate;
  const real = jogos.map((j, i) => ({ x: i + 1, y: j.pontos })).filter((p, i) => jogos[i].encerrada && visivel(i));
  // A projeção começa no último jogo real para a linha emendar.
  let proj = jogos.map((j, i) => ({ j, i })).filter(({ i }) => i >= Math.max(ultimoReal, 0) && visivel(i));
  if (ultimoReal >= 0 && proj.length < 2) proj = [];  // só o ponto de emenda: nada a projetar ainda
  const semReal = ultimoReal < 0;
  const esperado = (semReal ? [{ x: 0, y: 0 }] : []).concat(proj.map(({ j, i }) => ({ x: i + 1, y: +j.media.toFixed(1) })));
  const faixa = (semReal ? [{ x: 0, y: [0, 0] }] : []).concat(proj.map(({ j, i }) => ({ x: i + 1, y: [j.min, j.max] })));
  const rodada = v => jogos[Math.round(v) - 1]?.rodada;
  const opcoes = {
    chart: { type: "rangeArea", height: 280, toolbar: { show: false }, animations: { enabled: false } },
    series: [
      { type: "rangeArea", name: "Faixa provável (80%)", data: faixa },
      { type: "line", name: "Pontos", data: real },
      { type: "line", name: "Esperado", data: esperado },
    ],
    colors: ["#93c5fd", "#0b2a5b", "#2563eb"],
    fill: { opacity: [0.35, 1, 1] },
    stroke: { width: [0, 3, 2], dashArray: [0, 0, 5], curve: "straight" },
    markers: { size: [0, 3, 0] },
    xaxis: { type: "numeric", min: semReal ? 0 : 1, max: Math.max(n, 1), tickAmount: Math.min(n, CELULAR.matches ? 6 : 12),
      labels: { style: fonte(), formatter: v => rodada(v) ? `R${rodada(v)}` : "" } },
    dataLabels: { enabled: false },
    yaxis: { min: 0, max: Math.ceil(Math.max(3, ...jogos.map(j => j.max)) / 10) * 10, tickAmount: 5, labels: { style: fonte(), formatter: v => v.toFixed(0) } },
    legend: { labels: { colors: "#475569" }, fontSize: fonte().fontSize },
    tooltip: { shared: true, style: fonte(), x: { formatter: v => rodada(v) ? `Rodada ${rodada(v)}` : "Início" },
      y: { formatter: v => v == null ? "" : (+v).toFixed(1).replace(".", ",") } },
  };
  if (graficoPontos) graficoPontos.updateOptions(opcoes, false, false);
  else (graficoPontos = new ApexCharts($("grafico-pontos"), opcoes)).render();

  const j = jogos[Math.min(ate, n) - 1];
  const fmt = x => x.toFixed(1).replace(".", ",");
  $("nota-pontos").textContent = !j ? "" : j.encerrada
    ? `Jogo ${Math.min(ate, n)} de ${n} (rodada ${j.rodada}): ${j.pontos} pontos.`
    : `Jogo ${Math.min(ate, n)} de ${n} (rodada ${j.rodada}): ${fmt(j.media)} pontos esperados, ` +
      `entre ${j.min} e ${j.max} em 80% dos cenários.`;
}

const botoesTimelapse = () => document.querySelectorAll(".botao-timelapse");
const SIMULACOES_TIMELAPSE = 3000;
let graficoDispersao = null;

// Rodadas do timelapse: antes do campeonato (0) até a última com jogo encerrado.
const rodadasJogadas = d =>
  [0, ...new Set(d.partidas.filter(p => p.encerrada && p.rodada != null).map(p => p.rodada).sort((a, b) => a - b))];
const nomeRodada = r => r === 0 ? "Início" : `R${r}`;

function textoResumo(posicoes, r) {
  const { moda, chance, de, ate } = resumoPosicoes(posicoes);
  const quando = r === 0 ? "Antes da 1ª rodada" : `Após a rodada ${r}`;
  return `${quando}: posição final mais provável ${moda}º (${pct(chance)}); ` +
    (de === ate ? `${de}º em 80% dos cenários.` : `entre ${de}º e ${ate}º em 80% dos cenários (${ate - de + 1} posições).`);
}

// Mapa de calor rodada × posição final do clube; células ainda não simuladas ficam vazias.
function desenharDispersao() {
  const d = dados[liga], id = escolhido[liga];
  const hist = d.historico || {};
  const rodadas = rodadasJogadas(d);
  if (!rodadas.some(r => hist[r])) { $("dispersao").hidden = true; return; }
  $("dispersao").hidden = false;
  const n = Object.keys(d.clubes).length;
  const series = [];
  for (let pos = n; pos >= 1; pos--) series.push({
    name: `${pos}º`,
    data: rodadas.map(r => ({ x: nomeRodada(r), y: hist[r] ? +(hist[r][id].posicoes[pos - 1] * 100).toFixed(1) : -1 })),
  });
  const faixas = [[0, 1, "#f1f5f9"], [1, 5, "#dbeafe"], [5, 15, "#93c5fd"], [15, 30, "#3b82f6"], [30, 60, "#1d4ed8"], [60, 101, "#0b2a5b"]];
  const opcoes = {
    chart: { type: "heatmap", height: Math.max(260, n * 16 + 60), toolbar: { show: false }, animations: { enabled: false } },
    series,
    dataLabels: { enabled: false },
    legend: { show: true, fontSize: fonte().fontSize },
    plotOptions: { heatmap: { radius: 0, enableShades: false, colorScale: { ranges: [
      ...(rodadas.every(r => hist[r]) ? [] : [{ from: -1, to: -0.5, color: "#ffffff", name: "ainda não simulado" }]),
      ...faixas.map(([de, ate, c]) => ({ from: de, to: ate - 0.001, color: c, name: de === 0 ? "<1%" : `${de}–${Math.min(ate, 100)}%` })),
    ] } } },
    stroke: { width: 0.5, colors: ["#ffffff"] },
    xaxis: { type: "category", labels: { style: fonte(), rotate: -45, hideOverlappingLabels: true },
      tickAmount: CELULAR.matches ? 6 : 12 },
    yaxis: { labels: { style: fonte() } },
    tooltip: { style: fonte(), y: { formatter: v => v < 0 ? "—" : v + "%" } },
  };
  if (graficoDispersao) graficoDispersao.updateOptions(opcoes, false, false);
  else (graficoDispersao = new ApexCharts($("grafico-dispersao"), opcoes)).render();
}

function pararTimelapse() {
  clearTimeout(timelapse);
  timelapse = null;
  botoesTimelapse().forEach(b => b.textContent = "Gerar timelapse");
}

// Volta ao início do campeonato e anda rodada a rodada: a cada passo, a previsão da posição final feita com o
// que se sabia ali (gráfico da Simulação e mapa de calor) e os pontos reais até aquela rodada.
function gerarTimelapse() {
  if (timelapse) { pararTimelapse(); desenhar(); return; }
  const d = dados[liga], id = escolhido[liga];
  const nome = d.clubes[id]?.nome ?? id;
  const jogos = projecaoPontos(d.partidas, id, d.sim.modelo).jogos;
  const rodadas = rodadasJogadas(d);
  const hist = d.historico ??= {};
  botoesTimelapse().forEach(b => b.textContent = "Parar");
  let k = 0;
  const passo = () => {
    const r = rodadas[k];
    // Cada rodada é simulada uma vez e guardada: rever o timelapse ou trocar de time sai na hora.
    hist[r] ??= previsaoNaRodada(d, r, { simulacoes: SIMULACOES_TIMELAPSE }).res;
    const posicoes = hist[r][id].posicoes;
    desenharGraficoPosicoes(posicoes, `Posição final prevista ${r === 0 ? "antes da 1ª rodada" : `após a rodada ${r}`} — ${nome}`, true);
    $("nota-sim").textContent = textoResumo(posicoes, r);
    desenharGraficoPontos(r === rodadas.at(-1) ? Infinity : jogos.filter(j => j.encerrada && j.rodada <= r).length);
    desenharDispersao();
    if (++k >= rodadas.length) return pararTimelapse();
    timelapse = setTimeout(passo, 250);
  };
  timelapse = setTimeout(passo, 20);
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
  if (liga === OPERACAO && !operacao) carregarOperacao().then(() => { if (liga === OPERACAO) desenhar(); });
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
      `<button data-liga="${NOTICIAS}">Notícias</button><button data-liga="${OPERACAO}">Operação</button>`;
    carregarOperacao();  // marca a aba com ⚠️ se alguma atualização falhou
    // Abre na série (pontos corridos) em que o Remo está neste ano.
    const doRemo = LIGAS.map(([l]) => l).find(l => dados[l]?.info.tipo === "pontos" && dados[l].clubes[REMO]);
    trocarLiga(doRemo ?? Object.keys(dados)[0]);
  } catch (e) {
    console.error(e);
    // Sem banco, sobra a aba Operação para mostrar o que está acontecendo.
    $("abas").innerHTML = `<button data-liga="${OPERACAO}">Operação</button>`;
    trocarLiga(OPERACAO);
    $("atualizado").textContent = "Não foi possível carregar os dados.";
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

botoesTimelapse().forEach(b => b.addEventListener("click", gerarTimelapse));

iniciar();
