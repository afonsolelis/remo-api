// TC-classificacao: RF-classificacao (docs/especificacao/calculos.md#classificação)
const test = require("node:test");
const assert = require("node:assert/strict");
const { calculos } = require("./apoio.js");

const clubes = { 1: { id: 1 }, 2: { id: 2 }, 3: { id: 3 }, 4: { id: 4 } };
const jogo = (casa_id, fora_id, gols_casa, gols_fora, encerrada = true) =>
  ({ casa_id, fora_id, gols_casa, gols_fora, encerrada });

test("vitória vale 3, empate 1 e só jogos encerrados contam", () => {
  const { classificacao } = calculos();
  const t = classificacao(clubes, [jogo(1, 2, 2, 0), jogo(3, 4, 1, 1), jogo(1, 3, null, null, false)]);
  const por = Object.fromEntries(t.map(l => [l.id, l]));
  assert.equal(por[1].PTS, 3);
  assert.equal(por[2].PTS, 0);
  assert.equal(por[3].PTS, 1);
  assert.equal(por[4].PTS, 1);
  assert.equal(por[1].J, 1);
  assert.deepEqual([por[1].GP, por[1].GC], [2, 0]);
});

test("todo clube aparece, mesmo sem jogos", () => {
  const { classificacao } = calculos();
  assert.equal(classificacao(clubes, []).length, 4);
});

test("desempate: pontos, vitórias, saldo e gols pró", () => {
  const { classificacao } = calculos();
  // 1 e 2 com 3 pontos: 1 tem saldo +3, 2 tem saldo +1 → 1 na frente.
  // 3 e 4 com 0 pontos e saldos −3 e −1 → 4 na frente de 3.
  const t = classificacao(clubes, [jogo(1, 3, 3, 0), jogo(2, 4, 1, 0)]);
  assert.deepEqual(t.map(l => l.id), [1, 2, 4, 3]);

  // Mesmo saldo (+1), mais gols pró na frente: 2 (3×2) antes de 1 (1×0).
  const u = classificacao(clubes, [jogo(1, 3, 1, 0), jogo(2, 4, 3, 2)]);
  assert.deepEqual(u.map(l => l.id).slice(0, 2), [2, 1]);

  // Três pontos de uma vitória vencem três empates.
  const v = classificacao(clubes, [jogo(1, 4, 1, 0), jogo(2, 3, 0, 0), jogo(2, 4, 0, 0), jogo(3, 2, 0, 0)]);
  assert.equal(v[0].id, 1);
});
