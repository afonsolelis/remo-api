// Cálculos puros, sem DOM nem rede (docs/especificacao/calculos.md, AD-modulo-calculos).
// No navegador é um <script> comum carregado antes de app.js; no Node, os testes o importam.

const REMO = 364;

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

// Desempate: pontos, vitórias, saldo, gols pró e, por fim, sorteio.
function ordenar(t, aleatorio = Math.random) {
  const sorteio = {};
  for (const id of Object.keys(t)) sorteio[id] = aleatorio();
  return Object.values(t).sort((a, b) =>
    b.PTS - a.PTS || b.V - a.V || (b.GP - b.GC) - (a.GP - a.GC) || b.GP - a.GP || sorteio[a.id] - sorteio[b.id]);
}

function classificacao(clubes, partidas, aleatorio = Math.random) {
  const t = tabelaVazia(clubes);
  for (const p of partidas) if (p.encerrada) somarJogo(t, p.casa_id, p.fora_id, p.gols_casa, p.gols_fora);
  return ordenar(t, aleatorio);
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

// Sorteio de Poisson (Knuth) a partir de e^(-λ) já calculado.
function poisson(expMenosL, aleatorio) {
  let k = 0, p = 1;
  do { k++; p *= aleatorio(); } while (p > expMenosL);
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
// Cada simulação trabalha sobre vetores numéricos reaproveitados (AD-simulacao-sob-demanda).

function simular(d, { simulacoes = 10000, aleatorio = Math.random } = {}) {
  const jogados = d.partidas.filter(p => p.encerrada);
  const futuros = d.partidas.filter(p => !p.encerrada);
  const modelo = forcas(d.clubes, jogados);
  const base = tabelaVazia(d.clubes);
  for (const p of jogados) somarJogo(base, p.casa_id, p.fora_id, p.gols_casa, p.gols_fora);

  const ids = Object.keys(d.clubes).map(Number);
  const n = ids.length;
  const idx = new Map(ids.map((id, i) => [id, i]));
  const basePTS = Int32Array.from(ids, id => base[id].PTS);
  const baseV = Int32Array.from(ids, id => base[id].V);
  const baseSG = Int32Array.from(ids, id => base[id].GP - base[id].GC);
  const baseGP = Int32Array.from(ids, id => base[id].GP);

  const casa = Int32Array.from(futuros, p => idx.get(p.casa_id));
  const fora = Int32Array.from(futuros, p => idx.get(p.fora_id));
  const expC = new Float64Array(futuros.length), expF = new Float64Array(futuros.length);
  futuros.forEach((p, i) => {
    const [lc, lf] = lambdas(modelo, p.casa_id, p.fora_id);
    expC[i] = Math.exp(-lc);
    expF[i] = Math.exp(-lf);
  });

  const PTS = new Int32Array(n), V = new Int32Array(n), SG = new Int32Array(n), GP = new Int32Array(n);
  const sorteio = new Float64Array(n);
  const ordem = Array.from({ length: n }, (_, i) => i);
  const somaPontos = new Float64Array(n);
  const contagem = Array.from({ length: n }, () => new Float64Array(n));
  const comparar = (a, b) =>
    PTS[b] - PTS[a] || V[b] - V[a] || SG[b] - SG[a] || GP[b] - GP[a] || sorteio[a] - sorteio[b];

  for (let s = 0; s < simulacoes; s++) {
    PTS.set(basePTS); V.set(baseV); SG.set(baseSG); GP.set(baseGP);
    for (let i = 0; i < futuros.length; i++) {
      const c = casa[i], f = fora[i];
      const gc = poisson(expC[i], aleatorio), gf = poisson(expF[i], aleatorio);
      GP[c] += gc; GP[f] += gf; SG[c] += gc - gf; SG[f] += gf - gc;
      if (gc > gf) { PTS[c] += 3; V[c]++; }
      else if (gc < gf) { PTS[f] += 3; V[f]++; }
      else { PTS[c]++; PTS[f]++; }
    }
    for (let i = 0; i < n; i++) sorteio[i] = aleatorio();
    ordem.sort(comparar);
    for (let pos = 0; pos < n; pos++) {
      const t = ordem[pos];
      somaPontos[t] += PTS[t];
      contagem[t][pos]++;
    }
  }

  const res = {};
  ids.forEach((id, i) => {
    const posicoes = Array.from(contagem[i], x => x / simulacoes);
    res[id] = {
      pontos: somaPontos[i] / simulacoes,
      posicoes,
      zonas: d.info.zonas.map(z => z.posicoes.reduce((a, p) => a + (posicoes[p - 1] || 0), 0)),
    };
  });
  return { res, modelo, futuros, base, tabela: ordenar(structuredClone(base), aleatorio) };
}

// ---------- copas e estaduais ----------

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

// ---------- time padrão ----------

// O Remo se ele participa; senão o líder; senão o primeiro clube.
function timePadrao(clubes, tabela) {
  if (clubes[REMO]) return REMO;
  if (tabela && tabela.length) return tabela[0].id;
  return Number(Object.keys(clubes)[0]);
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    REMO, tabelaVazia, somarJogo, ordenar, classificacao, forcas, lambdas, prob1x2, simular,
    vencedor, chavesDaFase, campanha, campeao, timePadrao,
  };
}
