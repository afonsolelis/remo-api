// TC-desempenho: QS-desempenho (proxy em Node; ver docs/especificacao/calculos.md#simulação)
const test = require("node:test");
const assert = require("node:assert/strict");
const { calculos, ligaPontos } = require("./apoio.js");

const LIMITE_MS = 1000;  // 3 s no celular ÷ fator 3 suposto entre celular comum e computador

test("pior caso (20 clubes, 380 jogos por disputar, 10.000 simulações) em até 1 s", () => {
  const { simular } = calculos();
  const liga = ligaPontos(20, 0);
  simular(liga, { simulacoes: 200 });  // aquece o JIT
  const t = performance.now();
  simular(liga, { simulacoes: 10000 });
  const ms = performance.now() - t;
  console.log(`simulação: ${Math.round(ms)} ms`);
  assert.ok(ms <= LIMITE_MS, `${Math.round(ms)} ms > ${LIMITE_MS} ms`);
});
