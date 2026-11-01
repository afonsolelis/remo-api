// TC-legibilidade: QS-legibilidade (docs/especificacao/interface-celular.md#legibilidade)
const test = require("node:test");
const assert = require("node:assert/strict");
const { css, appJs, MEDIA, separar, px } = require("./celular.js");

test("existe o @media do celular", () => {
  assert.ok(css.includes(MEDIA), `falta ${MEDIA} no style.css`);
});

test("no celular o texto corrido tem 16 px", () => {
  const { celular } = separar();
  const body = celular.find(r => r.seletores.includes("body"));
  assert.ok(body, "falta regra para body no @media");
  assert.equal(px(body.decl["font-size"]), 16);
});

test("no celular nenhuma fonte fica abaixo de 14 px", () => {
  const { fora, celular } = separar();
  const noCelular = {};
  for (const r of celular) for (const s of r.seletores) if (r.decl["font-size"]) noCelular[s] = r.decl["font-size"];
  for (const r of celular) {
    if (!r.decl["font-size"]) continue;
    assert.ok(px(r.decl["font-size"]) >= 14, `${r.seletores} usa ${r.decl["font-size"]} no celular`);
  }
  for (const r of fora) {
    const t = px(r.decl["font-size"]);
    if (t === null || t >= 14) continue;
    for (const s of r.seletores) {
      assert.ok(noCelular[s] && px(noCelular[s]) >= 14, `${s} fica com ${r.decl["font-size"]} no celular`);
    }
  }
});

test("no celular os gráficos usam fonte de 14 px", () => {
  assert.match(appJs, /matchMedia\("\(max-width: 600px\)"\)/);
  assert.match(appJs, /fontSize:[^,\n]*"14px"/);
});
