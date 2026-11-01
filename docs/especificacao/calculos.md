# Especificação: `calculos.js`

Módulo de funções puras, sem DOM nem rede (`AD-modulo-calculos`). No navegador
é carregado por `<script>` antes de `app.js` e expõe as funções como globais.
No Node, exporta as mesmas funções por `module.exports`. Comportamento recuperado
de `app.js`; as mudanças estão marcadas como **novo**.

## Tipos

- `clubes`: objeto `{ [id]: { id, nome, ... } }`.
- `partida`: `{ casa_id, fora_id, gols_casa, gols_fora, encerrada, fase, chave, pen_casa, pen_fora }`.
- `liga`: `{ info: { tipo, zonas: [{ nome, cor, posicoes: [int] }], fases }, clubes, partidas }`.
- `aleatorio`: função sem argumentos que devolve um número em [0, 1). O padrão é
  `Math.random`. **Novo**: é injetável para testes determinísticos (`testability/limit-nondeterminism`).

## Classificação (`RF-classificacao`)

`classificacao(clubes, partidas, aleatorio?)` devolve a lista de linhas
`{ id, PTS, J, V, E, D, GP, GC }`, em ordem.

- Só partidas com `encerrada = true` contam.
- Vitória vale 3 pontos, empate 1, derrota 0.
- Desempate, nesta ordem: pontos, vitórias, saldo (GP − GC), gols pró e, por
  fim, sorteio com `aleatorio`.
- Todo clube de `clubes` aparece, mesmo sem jogos.

## Simulação (`RF-simular`, `RF-chances-zona`, `QS-desempenho`)

`simular(liga, { simulacoes = 10000, aleatorio = Math.random })` devolve
`{ res, tabela, futuros, modelo }`:

- `res[id].posicoes[k]` é a probabilidade de o clube terminar na posição `k + 1`.
- `res[id].pontos` é a média de pontos finais.
- `res[id].zonas[z]` é a soma de `posicoes` nas posições da zona `info.zonas[z]`.
- `tabela` é a classificação atual (`classificacao`).
- Modelo: Poisson com forças de ataque e defesa por clube, puxadas para a média
  com K = 5 jogos fictícios, e médias de gols de mandante e visitante (padrão
  1,4 e 1,1 quando não há jogos).

Invariantes verificáveis:

1. Para cada clube, a soma de `posicoes` é 1 (tolerância 1e-9).
2. Para cada posição, a soma entre os clubes é 1.
3. Sem jogos restantes, a probabilidade da posição atual de cada clube é 1.
4. `zonas[z]` é igual à soma de `posicoes` nas posições da zona.

Desempenho (**novo**, `AD-simulacao-sob-demanda`): sem `structuredClone` por
rodada simulada; a tabela de cada simulação reaproveita vetores numéricos.
Contrato de teste: liga de 20 clubes com os 380 jogos por disputar e 10.000
simulações em até 1.000 ms no Node. Isso é um **proxy**: supõe-se que um
celular comum seja até 3 vezes mais lento que o computador do mantenedor. A
medida real em celular fica para a SP5.

## Copas (`RF-campanha-copa`)

- `vencedor(jogos)`: `null` se não há jogos ou algum não terminou. Senão, quem
  fez mais gols na soma. Empate na soma: pênaltis do último jogo; sem pênaltis, `null`.
- `campanha(liga, id)`: texto da situação do clube. "Não participou", "Disputando: <fase>",
  "Classificado na <fase>", "Eliminado: <fase>", "Encerrou na <fase>",
  "Campeão 🏆" ou "Vice-campeão".
- `campeao(liga)`: vencedor da chave única da última fase, se ela for de mata-mata; senão `null`.

## Time padrão (`RF-escolher-time`, `QS-facilidade`)

`timePadrao(clubes, tabela)`: o Remo (364) se ele participa; senão o líder da
`tabela`; senão o primeiro clube.

## Ambiguidades declaradas

- O sorteio no desempate não segue o regulamento (confronto direto, cartões).
  Isso é aceito como está: o efeito nas probabilidades é pequeno.
