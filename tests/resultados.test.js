// TC-resultados: RF-resultados (docs/especificacao/calculos.md#resultados-passados)
const test = require("node:test");
const assert = require("node:assert/strict");
const { calculos } = require("./apoio.js");

const j = (partida_id, data, casa_id, fora_id, gols_casa, gols_fora) =>
  ({ partida_id, data, casa_id, fora_id, gols_casa, gols_fora, encerrada: gols_casa != null });

const dados = {
  serie_b: { partidas: [
    j(1, "2026-10-20T16:00:00-03:00", 364, 2, 2, 0),
    j(2, "2026-10-20T21:00:00-03:00", 3, 4, 1, 1),
    j(3, "2026-11-05T16:00:00-03:00", 364, 3, null, null),
  ] },
  parazao: { partidas: [
    j(4, "2026-02-01T16:00:00-03:00", 5, 364, 3, 1),
    j(5, "2025-12-01T16:00:00-03:00", 364, 5, 0, 0),
    j(6, null, 364, 5, null, null),
  ] },
};

test("só jogos encerrados no período, do mais recente ao mais antigo", () => {
  const { resultados } = calculos();
  const dias = resultados(dados, "2026-01-01", "2026-11-01");
  assert.deepEqual(dias.map(d => d.dia), ["2026-10-20", "2026-02-01"]);
  assert.deepEqual(dias[0].jogos.map(p => p.partida_id), [2, 1]);
  assert.equal(dias[1].jogos[0].liga, "parazao");
  assert.deepEqual(resultados(dados, "2026-03-01", "2026-10-19"), []);
});

test("com clube, só os jogos dele", () => {
  const { resultados } = calculos();
  const dias = resultados(dados, "2026-01-01", "2026-12-31", 364);
  assert.deepEqual(dias.flatMap(d => d.jogos.map(p => p.partida_id)), [1, 4]);
});

test("retrospecto conta vitórias, empates, derrotas e gols do clube", () => {
  const { resultados, retrospecto } = calculos();
  const jogos = resultados(dados, "2025-01-01", "2026-12-31").flatMap(d => d.jogos);
  assert.deepEqual(retrospecto(jogos, 364), { J: 3, V: 1, E: 1, D: 1, GP: 3, GC: 3 });
  assert.deepEqual(retrospecto(jogos, 99), { J: 0, V: 0, E: 0, D: 0, GP: 0, GC: 0 });
});
