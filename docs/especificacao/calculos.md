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

## Tabela final prevista (**novo**)

`tabelaPrevista(res)` recebe o `res` de `simular` e devolve
`[{ id, pontos, posicaoMedia }]`, um por clube, em ordem de pontos esperados
(`res[id].pontos`, decrescente). Empate: menor posição média
(`Σ (k + 1) · posicoes[k]`) e, por fim, menor `id`.

Invariantes verificáveis:

1. Todo clube de `res` aparece uma vez.
2. Os pontos não crescem ao longo da lista.
3. Sem jogos restantes, a ordem é a da `tabela` atual (salvo empate total).

## Projeção de pontos rodada a rodada (`RF-timelapse`) — **novo**

`projecaoPontos(partidas, id, modelo, { faixa = [0.1, 0.9] })` percorre os jogos do clube na
ordem de `partidas` e devolve `{ jogos, final }`:

- Jogo encerrado: `{ rodada, encerrada: true, pontos, media, min, max }`, todos iguais aos pontos reais acumulados.
- Jogo por disputar: `{ rodada, encerrada: false, media, min, max, vitoria, empate, derrota }`. Cada jogo soma
  3, 1 ou 0 com as chances de `prob1x2` (modelo de `simular`), e a distribuição dos pontos acumulados é
  calculada **exatamente**, combinando jogo a jogo (sem sorteio). `media` é a média; `min` e `max` são os
  quantis `faixa` (80% dos cenários no padrão).
- `final`: `[{ pontos, chance }]` ao fim dos jogos do clube.

Invariantes verificáveis: `min ≤ media ≤ max`; a média não cai ao longo dos jogos; as chances de
`final` somam 1; a média final fica perto de `res[id].pontos` de `simular` (que sorteia a mesma coisa).

Na página, o gráfico "Pontos por rodada" mostra os pontos reais, a linha tracejada dos pontos esperados
e a faixa de 80%. O botão "Gerar timelapse" redesenha o gráfico jogo a jogo, do primeiro ao último, com
os eixos fixos, e mostra embaixo os pontos (ou a média e a faixa) do jogo da vez. Clicar de novo para.

## Copas (`RF-campanha-copa`)

- `vencedor(jogos)`: `null` se não há jogos ou algum não terminou. Senão, quem
  fez mais gols na soma. Empate na soma: pênaltis do último jogo; sem pênaltis, `null`.
- `campanha(liga, id)`: texto da situação do clube. "Não participou", "Disputando: <fase>",
  "Classificado na <fase>", "Eliminado: <fase>", "Encerrou na <fase>",
  "Campeão 🏆" ou "Vice-campeão".
- `campeao(liga)`: vencedor da chave única da última fase, se ela for de mata-mata; senão `null`.

## Próximos jogos (`RF-jogos-hoje`) — **novo**

- `diaEmBelem(instante)`: `"AAAA-MM-DD"` do instante no fuso `America/Belem` (`FUSO`),
  seja qual for o fuso do aparelho.
- `calendario(dados, de, ate, clube = 0)`: recebe `{ [liga]: { partidas } }` e devolve
  `[{ dia, jogos }]` com as partidas de todas as ligas cujo dia de Belém está entre
  `de` e `ate` (inclusive). Cada partida ganha os campos `liga` e `dia`. Dias e jogos
  em ordem de horário (empate: `partida_id`). Partidas sem `data` ficam de fora. Com
  `clube` diferente de 0, só as partidas dele.

A aba Próximos jogos mostra o calendário de hoje até 31/12, com filtro de clube
(começa em "Todos os clubes").

## Resultados passados (`RF-resultados`) — **novo**

- `resultados(dados, de, ate, clube = 0)`: o mesmo recorte de `calendario`, só com as
  partidas encerradas; dias sem jogo encerrado ficam de fora. Dias e jogos do mais
  recente ao mais antigo.
- `retrospecto(jogos, clube)`: `{ J, V, E, D, GP, GC }` do clube nas partidas encerradas
  da lista em que ele jogou.

A aba Resultados passados abre com o período de 1º/01 até hoje (Belém) e "Todos os
clubes". Os filtros "De"/"Até" mudam o período (se "De" passar de "Até", os dois viram o
mesmo dia). Com um clube escolhido, os cards mostram jogos, V · E · D, gols e
aproveitamento no período.

## Time padrão (`RF-escolher-time`, `QS-facilidade`)

`timePadrao(clubes, tabela)`: o Remo (364) se ele participa; senão o líder da
`tabela`; senão o primeiro clube.

## Ambiguidades declaradas

- O sorteio no desempate não segue o regulamento (confronto direto, cartões).
  Isso é aceito como está: o efeito nas probabilidades é pequeno.
