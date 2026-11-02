// TC-projecao: RF-timelapse (docs/especificacao/calculos.md#projeção-de-pontos-rodada-a-rodada)
const test = require("node:test");
const assert = require("node:assert/strict");
const { calculos, semente, ligaPontos } = require("./apoio.js");

test("jogos encerrados seguem os pontos reais, sem faixa", () => {
  const { projecaoPontos, forcas, classificacao } = calculos();
  const liga = ligaPontos(6, 30);
  const m = forcas(liga.clubes, liga.partidas.filter(p => p.encerrada));
  const { jogos } = projecaoPontos(liga.partidas, 1, m);
  const pts = classificacao(liga.clubes, liga.partidas).find(l => l.id === 1).PTS;
  const ult = jogos.filter(j => j.encerrada).at(-1);
  assert.equal(ult.pontos, pts);
  for (const j of jogos.filter(j => j.encerrada)) assert.ok(j.min === j.media && j.max === j.media);
});

test("a projeção cresce jogo a jogo e a faixa contém a média", () => {
  const { projecaoPontos, forcas } = calculos();
  const liga = ligaPontos(6, 12);
  const m = forcas(liga.clubes, liga.partidas.filter(p => p.encerrada));
  const { jogos, final } = projecaoPontos(liga.partidas, 2, m);
  assert.equal(jogos.length, 10);
  for (let i = 1; i < jogos.length; i++) assert.ok(jogos[i].media >= jogos[i - 1].media);
  for (const j of jogos) assert.ok(j.min <= j.media && j.media <= j.max);
  assert.ok(Math.abs(final.reduce((a, x) => a + x.chance, 0) - 1) < 1e-9);
  assert.ok(Math.abs(final.reduce((a, x) => a + x.chance * x.pontos, 0) - jogos.at(-1).media) < 1e-9);
});

test("a média final bate com a média da simulação Monte Carlo", () => {
  const { projecaoPontos, simular } = calculos();
  const liga = ligaPontos(6, 10);
  const sim = simular(liga, { simulacoes: 20000, aleatorio: semente(7) });
  for (const id of [1, 4]) {
    const { jogos } = projecaoPontos(liga.partidas, id, sim.modelo);
    assert.ok(Math.abs(jogos.at(-1).media - sim.res[id].pontos) < 0.2, `clube ${id}`);
  }
});

// ligaPontos não tem rodada; numera cada jogo como uma rodada para o teste.
const comRodadas = liga => ({ ...liga, partidas: liga.partidas.map((p, i) => ({ ...p, rodada: i + 1 })) });

test("posições por rodada: jogadas são certas, e cada rodada soma 1", () => {
  const { posicoesPorRodada } = calculos();
  const liga = comRodadas(ligaPontos(6, 12));
  const pr = posicoesPorRodada(liga, 3, { simulacoes: 2000, aleatorio: semente(3) });
  assert.equal(Object.keys(pr).length, 30);
  for (let r = 1; r <= 12; r++) assert.equal(pr[r].filter(x => x === 1).length, 1, `rodada ${r}`);
  for (const p of Object.values(pr)) assert.ok(Math.abs(p.reduce((a, b) => a + b, 0) - 1) < 1e-9);
});

test("posições na última rodada batem com a simulação", () => {
  const { posicoesPorRodada, simular } = calculos();
  const liga = comRodadas(ligaPontos(6, 10));
  const pr = posicoesPorRodada(liga, 2, { simulacoes: 20000, aleatorio: semente(4) });
  const { res } = simular(liga, { simulacoes: 20000, aleatorio: semente(5) });
  pr[30].forEach((x, k) => assert.ok(Math.abs(x - res[2].posicoes[k]) < 0.03, `posição ${k + 1}`));
});
