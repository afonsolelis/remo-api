// TC-simulacao: RF-simular e RF-chances-zona (docs/especificacao/calculos.md#simulação)
const test = require("node:test");
const assert = require("node:assert/strict");
const { calculos, semente, ligaPontos } = require("./apoio.js");

const perto = (a, b) => Math.abs(a - b) < 1e-9;

test("probabilidades de cada clube e de cada posição somam 1", () => {
  const { simular } = calculos();
  const liga = ligaPontos(6, 15);
  const { res } = simular(liga, { simulacoes: 2000, aleatorio: semente(1) });
  const ids = Object.keys(liga.clubes);
  for (const id of ids) assert.ok(perto(res[id].posicoes.reduce((a, b) => a + b, 0), 1), `clube ${id}`);
  for (let k = 0; k < ids.length; k++) {
    assert.ok(perto(ids.reduce((a, id) => a + res[id].posicoes[k], 0), 1), `posição ${k + 1}`);
  }
});

test("sem jogos restantes, a posição atual tem probabilidade 1", () => {
  const { simular } = calculos();
  const jogo = (casa_id, fora_id, gols_casa, gols_fora) => ({ casa_id, fora_id, gols_casa, gols_fora, encerrada: true });
  // Pontos finais sem empate: 1 = 6, 2 = 3, 3 = 0.
  const liga = { info: { tipo: "pontos", zonas: [], fases: [] }, clubes: { 1: {}, 2: {}, 3: {} },
    partidas: [jogo(1, 2, 2, 0), jogo(1, 3, 1, 0), jogo(2, 3, 3, 1)] };
  const { res, tabela } = simular(liga, { simulacoes: 500, aleatorio: semente(2) });
  assert.deepEqual(tabela.map(l => l.id), [1, 2, 3]);
  tabela.forEach((linha, k) => assert.equal(res[linha.id].posicoes[k], 1));
});

test("chance por zona é a soma das posições da zona", () => {
  const { simular } = calculos();
  const zonas = [{ nome: "Acesso", cor: "#0000ff", posicoes: [1, 2] }, { nome: "Rebaixamento", cor: "#ff0000", posicoes: [5, 6] }];
  const liga = ligaPontos(6, 12, zonas);
  const { res } = simular(liga, { simulacoes: 2000, aleatorio: semente(3) });
  for (const id of Object.keys(liga.clubes)) {
    const r = res[id];
    assert.ok(perto(r.zonas[0], r.posicoes[0] + r.posicoes[1]));
    assert.ok(perto(r.zonas[1], r.posicoes[4] + r.posicoes[5]));
  }
});

test("mesma semente, mesmo resultado", () => {
  const { simular } = calculos();
  const liga = ligaPontos(6, 10);
  const a = simular(liga, { simulacoes: 1000, aleatorio: semente(7) });
  const b = simular(liga, { simulacoes: 1000, aleatorio: semente(7) });
  assert.deepEqual(a.res, b.res);
});

test("tabela final prevista: todos os clubes, pontos em ordem decrescente", () => {
  const { simular, tabelaPrevista } = calculos();
  const liga = ligaPontos(6, 12);
  const { res } = simular(liga, { simulacoes: 1000, aleatorio: semente(4) });
  const prevista = tabelaPrevista(res);
  assert.deepEqual(prevista.map(t => t.id).sort(), Object.keys(liga.clubes).map(Number).sort());
  for (let i = 1; i < prevista.length; i++) assert.ok(prevista[i - 1].pontos >= prevista[i].pontos);
});

test("tabela final prevista sem jogos restantes é a classificação atual", () => {
  const { simular, tabelaPrevista } = calculos();
  const jogo = (casa_id, fora_id, gols_casa, gols_fora) => ({ casa_id, fora_id, gols_casa, gols_fora, encerrada: true });
  const liga = { info: { tipo: "pontos", zonas: [], fases: [] }, clubes: { 1: {}, 2: {}, 3: {} },
    partidas: [jogo(2, 1, 2, 0), jogo(3, 1, 1, 0), jogo(2, 3, 3, 1)] };
  const { res, tabela } = simular(liga, { simulacoes: 200, aleatorio: semente(5) });
  assert.deepEqual(tabelaPrevista(res).map(t => t.id), tabela.map(t => t.id));
});
