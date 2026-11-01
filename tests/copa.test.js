// TC-copa: RF-campanha-copa (docs/especificacao/calculos.md#copas)
const test = require("node:test");
const assert = require("node:assert/strict");
const { calculos } = require("./apoio.js");

const j = (casa_id, fora_id, gols_casa, gols_fora, extra = {}) =>
  ({ casa_id, fora_id, gols_casa, gols_fora, encerrada: gols_casa != null, pen_casa: null, pen_fora: null, ...extra });

test("vencedor pela soma dos gols, pelos pênaltis ou ainda indefinido", () => {
  const { vencedor } = calculos();
  assert.equal(vencedor([j(1, 2, 2, 0), j(2, 1, 1, 0)]), 1);
  assert.equal(vencedor([j(1, 2, 1, 0), j(2, 1, 1, 0, { pen_casa: 4, pen_fora: 3 })]), 2);
  assert.equal(vencedor([j(1, 2, 1, 0), j(2, 1, null, null)]), null);
  assert.equal(vencedor([]), null);
});

const copa = {
  info: {
    tipo: "copa",
    fases: [
      { nome: "Semifinal", tipo: "mata", grupos: [] },
      { nome: "Final", tipo: "mata", grupos: [] },
    ],
  },
  clubes: { 1: {}, 2: {}, 3: {}, 4: {}, 5: {} },
  partidas: [
    { ...j(1, 2, 2, 0), fase: "Semifinal", chave: "A" },
    { ...j(3, 4, 0, 1), fase: "Semifinal", chave: "B" },
    { ...j(1, 4, 1, 0), fase: "Final", chave: "F" },
  ],
};

test("campanha e campeão de uma copa encerrada", () => {
  const { campanha, campeao } = calculos();
  assert.equal(campeao(copa), 1);
  assert.equal(campanha(copa, 1), "Campeão 🏆");
  assert.equal(campanha(copa, 4), "Vice-campeão");
  assert.equal(campanha(copa, 2), "Eliminado: Semifinal");
  assert.equal(campanha(copa, 5), "Não participou");
});

test("final em aberto", () => {
  const { campanha, campeao } = calculos();
  const aberta = { ...copa, partidas: [...copa.partidas.slice(0, 2), { ...j(1, 4, null, null), fase: "Final", chave: "F" }] };
  assert.equal(campeao(aberta), null);
  assert.equal(campanha(aberta, 1), "Disputando: Final");
});
