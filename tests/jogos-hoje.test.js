// TC-jogos-hoje: RF-jogos-hoje (docs/especificacao/calculos.md#próximos-jogos)
const test = require("node:test");
const assert = require("node:assert/strict");
const { calculos } = require("./apoio.js");

const j = (partida_id, data, casa_id = 1, fora_id = 2) => ({ partida_id, data, casa_id, fora_id });

const dados = {
  serie_b: { partidas: [j(1, "2026-11-01T21:30:00-03:00"), j(2, "2026-11-01T16:00:00-03:00", 364, 3), j(3, null)] },
  parazao: { partidas: [j(4, "2026-11-01T18:00:00-03:00"), j(5, "2026-11-04T19:00:00-03:00", 5, 364)] },
  copa_verde: { partidas: [j(6, "2026-10-31T20:00:00-03:00"), j(7, "2027-01-10T20:00:00-03:00")] },
};

test("o dia é o de Belém, não o do UTC", () => {
  const { diaEmBelem } = calculos();
  // 01:30 UTC do dia 2 ainda é 22:30 do dia 1 em Belém.
  assert.equal(diaEmBelem("2026-11-02T01:30:00Z"), "2026-11-01");
  assert.equal(diaEmBelem("2026-11-02T03:00:00Z"), "2026-11-02");
});

test("calendário de todas as ligas, por dia e em ordem de horário, só dentro do período", () => {
  const { calendario } = calculos();
  const dias = calendario(dados, "2026-11-01", "2026-12-31");
  assert.deepEqual(dias.map(d => d.dia), ["2026-11-01", "2026-11-04"]);
  assert.deepEqual(dias[0].jogos.map(p => p.partida_id), [2, 4, 1]);
  assert.deepEqual(dias[0].jogos.map(p => p.liga), ["serie_b", "parazao", "serie_b"]);
  assert.deepEqual(calendario(dados, "2026-11-05", "2026-12-31"), []);
});

test("com clube, só os jogos dele", () => {
  const { calendario } = calculos();
  const dias = calendario(dados, "2026-11-01", "2026-12-31", 364);
  assert.deepEqual(dias.flatMap(d => d.jogos.map(p => p.partida_id)), [2, 5]);
});
