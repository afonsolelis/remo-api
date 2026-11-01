// Apoio aos testes: carrega calculos.js e monta ligas de exemplo.
const path = require("node:path");

const calculos = () => require(path.join(__dirname, "..", "calculos.js"));

// Gerador determinístico (mulberry32) para testes reproduzíveis.
function semente(s) {
  return () => {
    s |= 0; s = (s + 0x6d2b79f5) | 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// Liga de pontos corridos em turno e returno; os `jogados` primeiros jogos já terminaram.
function ligaPontos(n, jogados, zonas = [{ nome: "Acesso", cor: "#0000ff", posicoes: [1, 2] }]) {
  const clubes = {};
  for (let i = 1; i <= n; i++) clubes[i] = { id: i, nome: `Clube ${i}` };
  const partidas = [];
  let k = 0;
  for (let a = 1; a <= n; a++) for (let b = 1; b <= n; b++) if (a !== b) {
    const fim = k++ < jogados;
    partidas.push({ casa_id: a, fora_id: b, encerrada: fim,
      gols_casa: fim ? (a * 7 + b) % 4 : null, gols_fora: fim ? (a + b * 3) % 3 : null });
  }
  return { info: { tipo: "pontos", zonas, fases: [] }, clubes, partidas };
}

module.exports = { calculos, semente, ligaPontos };
