# Especificação: interface no celular

Contrato da página em telas de até 600 px (`AD-responsivo`, `RNF-legibilidade`,
`RNF-tabela-celular`). É a mesma página do computador; só o CSS e alguns
detalhes de exibição mudam.

## Ponto de quebra

- Celular: `@media (max-width: 600px)` no `style.css` e
  `matchMedia("(max-width: 600px)")` no `app.js`, com o mesmo valor.

## Legibilidade (`QS-legibilidade`)

- Texto corrido: `font-size: 1rem` (16 px) no `body`.
- Nenhum texto abaixo de `.875rem` (14 px). Toda regra que no computador usa
  menos que `.875rem` (rótulos dos cards, notas, tabelas, chaves, cabeçalho,
  rodapé) é sobrescrita dentro do `@media`.
- Gráficos: no celular, rótulos dos eixos, títulos dos eixos, legendas e
  tooltips usam `fontSize: "14px"`.

## Tabela de classificação (`QS-tabela-celular`)

- Colunas secundárias levam a classe `sec` no `<th>` e no `<td>`: J, V, SG,
  Pts esp. e Título. No celular, `.sec { display: none }`.
- O time aparece duas vezes na célula: `<span class="nome-longo">` com o nome
  e `<span class="nome-curto">` com a sigla (`remo_clubes.abreviacao`; se faltar,
  as 3 primeiras letras do nome). No celular só a sigla aparece; no computador,
  só o nome.
- Cabeçalho de zona no celular: as 3 primeiras letras do nome da zona e ponto
  (ex.: "Reb."), com a cor da zona na borda de cima. O nome completo fica no
  `title` do `<th>` e na legenda abaixo da tabela.
- O mesmo vale para a tabela de próximos jogos: siglas no celular.

## Fora do escopo

- Layout de copas: a classe `nome-curto` não é obrigatória lá; só a legibilidade vale.
- Modo escuro, gestos e instalação como aplicativo.
