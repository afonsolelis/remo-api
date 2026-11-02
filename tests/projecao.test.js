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
