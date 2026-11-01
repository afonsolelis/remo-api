// TC-tabela-celular: QS-tabela-celular (docs/especificacao/interface-celular.md#tabela-de-classificação)
const test = require("node:test");
const assert = require("node:assert/strict");
const { appJs, separar } = require("./celular.js");

const decl = (regras, seletor) => regras.find(r => r.seletores.includes(seletor))?.decl ?? {};

test("no celular as colunas secundárias e o nome longo somem, e a sigla aparece", () => {
  const { fora, celular } = separar();
  assert.equal(decl(celular, ".sec").display, "none");
  assert.equal(decl(celular, ".nome-longo").display, "none");
  assert.equal(decl(fora, ".nome-curto").display, "none", "no computador a sigla fica escondida");
  assert.ok(decl(celular, ".nome-curto").display && decl(celular, ".nome-curto").display !== "none");
});

test("J, V, SG, Pts esp. e Título são colunas secundárias", () => {
  for (const col of ["J", "V", "SG", "Pts esp.", "Título"]) {
    assert.ok(appJs.includes(`<th class="sec">${col}</th>`), `coluna ${col} sem class="sec"`);
  }
});

test("o time aparece pelo nome e pela sigla", () => {
  assert.match(appJs, /class="nome-longo"/);
  assert.match(appJs, /class="nome-curto"/);
  assert.match(appJs, /abreviacao/);
});
