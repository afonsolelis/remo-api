// TC-facilidade: QS-facilidade e RF-escolher-time.
// Até 2 ações: (1) aba do campeonato e (2) seletor de time, ambos fora de menus;
// e o Remo já vem escolhido quando participa (0 ações para o torcedor do Remo).
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { calculos } = require("./apoio.js");

const html = fs.readFileSync(path.join(__dirname, "..", "index.html"), "utf8");

test("o time padrão é o Remo quando ele participa", () => {
  const { timePadrao } = calculos();
  const tabela = [{ id: 7 }, { id: 364 }];
  assert.equal(timePadrao({ 7: {}, 364: {} }, tabela), 364);
});

test("sem o Remo, o time padrão é o líder; sem tabela, o primeiro clube", () => {
  const { timePadrao } = calculos();
  assert.equal(timePadrao({ 7: {}, 9: {} }, [{ id: 9 }, { id: 7 }]), 9);
  assert.equal(timePadrao({ 7: {}, 9: {} }, null), 7);
});

test("abas e seletor de time ficam visíveis no topo da página", () => {
  assert.match(html, /<nav[^>]*id="abas"/);
  assert.match(html, /<select id="time"/);
  const abas = html.indexOf('id="abas"'), seletor = html.indexOf('id="time"');
  const conteudo = html.indexOf('id="cards"');
  assert.ok(abas < conteudo && seletor < conteudo, "abas e seletor antes do conteúdo");
  assert.doesNotMatch(html.slice(0, conteudo), /<details|class="menu/, "nada escondido em menu");
});
