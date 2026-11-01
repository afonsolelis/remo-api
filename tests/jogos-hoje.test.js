// TC-jogos-hoje: RF-jogos-hoje (docs/especificacao/calculos.md#jogos-de-hoje)
const test = require("node:test");
const assert = require("node:assert/strict");
const { calculos } = require("./apoio.js");

const j = (partida_id, data) => ({ partida_id, data, casa_id: 1, fora_id: 2 });

const dados = {
  serie_b: { partidas: [j(1, "2026-11-01T21:30:00-03:00"), j(2, "2026-11-01T16:00:00-03:00"), j(3, null)] },
  parazao: { partidas: [j(4, "2026-11-01T18:00:00-03:00"), j(5, "2026-11-04T19:00:00-03:00")] },
  copa_verde: { partidas: [j(6, "2026-11-03T20:00:00-03:00")] },
};

test("o dia é o de Belém, não o do UTC", () => {
  const { diaEmBelem } = calculos();
  // 01:30 UTC do dia 2 ainda é 22:30 do dia 1 em Belém.
  assert.equal(diaEmBelem("2026-11-02T01:30:00Z"), "2026-11-01");
  assert.equal(diaEmBelem("2026-11-02T03:00:00Z"), "2026-11-02");
});

test("junta os jogos do dia de todas as ligas, em ordem de horário", () => {
  const { jogosDoDia } = calculos();
  const jogos = jogosDoDia(dados, "2026-11-01");
  assert.deepEqual(jogos.map(p => p.partida_id), [2, 4, 1]);
  assert.deepEqual(jogos.map(p => p.liga), ["serie_b", "parazao", "serie_b"]);
  assert.deepEqual(jogosDoDia(dados, "2026-11-02"), []);
});

test("próximo dia com jogos, ignorando jogos sem data", () => {
  const { proximoDiaComJogos } = calculos();
  assert.equal(proximoDiaComJogos(dados, "2026-11-01"), "2026-11-03");
  assert.equal(proximoDiaComJogos(dados, "2026-11-03"), "2026-11-04");
  assert.equal(proximoDiaComJogos(dados, "2026-11-04"), null);
});
