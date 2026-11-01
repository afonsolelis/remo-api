// Apoio: lê o style.css e separa as regras de fora e de dentro do @media do celular.
const fs = require("node:fs");
const path = require("node:path");

const raiz = path.join(__dirname, "..");
const css = fs.readFileSync(path.join(raiz, "style.css"), "utf8").replace(/\/\*[\s\S]*?\*\//g, "");
const appJs = fs.readFileSync(path.join(raiz, "app.js"), "utf8");
const MEDIA = "@media (max-width: 600px)";

// Devolve [{ seletores: [...], decl: { prop: valor } }] de um trecho de CSS sem blocos aninhados.
function regras(texto) {
  const out = [];
  for (const m of texto.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
    const decl = {};
    for (const d of m[2].split(";")) {
      const i = d.indexOf(":");
      if (i > 0) decl[d.slice(0, i).trim()] = d.slice(i + 1).trim();
    }
    out.push({ seletores: m[1].split(",").map(s => s.trim()).filter(Boolean), decl });
  }
  return out;
}

// Separa o bloco do @media do celular do resto do CSS.
function separar() {
  const ini = css.indexOf(MEDIA);
  if (ini < 0) return { fora: regras(css), celular: [] };
  const abre = css.indexOf("{", ini);
  let nivel = 0, fim = abre;
  for (; fim < css.length; fim++) {
    if (css[fim] === "{") nivel++;
    if (css[fim] === "}" && --nivel === 0) break;
  }
  return { fora: regras(css.slice(0, ini) + css.slice(fim + 1)), celular: regras(css.slice(abre + 1, fim)) };
}

// Tamanho em px (16 px por rem/em); null se não for rem, em ou px.
function px(valor) {
  const m = /^([\d.]+)(rem|em|px)$/.exec(valor || "");
  if (!m) return null;
  return m[2] === "px" ? +m[1] : +m[1] * 16;
}

module.exports = { css, appJs, MEDIA, separar, px };
