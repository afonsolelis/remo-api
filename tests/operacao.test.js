// TC-operacao: RF-operacao (docs/especificacao/calculos.md#operação)
const test = require("node:test");
const assert = require("node:assert/strict");
const { calculos } = require("./apoio.js");

const AGORA = Date.parse("2026-11-06T12:00:00Z");
const exec = (conclusion, updated_at, status = "completed") => ({ status, conclusion, updated_at });

test("última execução com falha: estado falha e conta as falhas seguidas", () => {
  const { situacaoWorkflow } = calculos();
  const s = situacaoWorkflow([
    exec("failure", "2026-11-06T07:11:00Z"),
    exec("failure", "2026-11-05T23:46:00Z"),
    exec("success", "2026-11-04T18:11:00Z"),
  ], AGORA, 12);
  assert.equal(s.estado, "falha");
  assert.equal(s.falhasSeguidas, 2);
  assert.equal(s.ultimoSucesso.updated_at, "2026-11-04T18:11:00Z");
});

test("sucesso recente é ok; sucesso antigo demais é atrasado", () => {
  const { situacaoWorkflow } = calculos();
  assert.equal(situacaoWorkflow([exec("success", "2026-11-06T09:00:00Z")], AGORA, 12).estado, "ok");
  assert.equal(situacaoWorkflow([exec("success", "2026-11-05T20:00:00Z")], AGORA, 12).estado, "atrasado");
});

test("canceladas não contam e execução em andamento é sinalizada", () => {
  const { situacaoWorkflow } = calculos();
  const s = situacaoWorkflow([
    exec(null, "2026-11-06T11:59:00Z", "in_progress"),
    exec("cancelled", "2026-11-06T11:00:00Z"),
    exec("success", "2026-11-06T10:00:00Z"),
  ], AGORA, 12);
  assert.equal(s.estado, "ok");
  assert.equal(s.rodando, true);
  assert.equal(s.falhasSeguidas, 0);
});

test("sem execuções: sem-dados; só falhas: todas contam", () => {
  const { situacaoWorkflow } = calculos();
  assert.equal(situacaoWorkflow([], AGORA, 12).estado, "sem-dados");
  const s = situacaoWorkflow([exec("failure", "2026-11-06T07:00:00Z"), exec("timed_out", "2026-11-06T05:00:00Z")], AGORA, 12);
  assert.equal(s.falhasSeguidas, 2);
  assert.equal(s.ultimoSucesso, null);
});
