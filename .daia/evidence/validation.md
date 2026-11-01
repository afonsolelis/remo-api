# Validação (SP5)

Redigido com IA (`@val`) em 2026-10-31. Confronta as hipóteses da SP1 com a
evidência da SP4 e da demonstração abaixo. Uma instanciação não sustenta
afirmações sobre outros sites ou outros torcedores.

## Roteiro de demonstração

1. Abrir o site sem escolher nada: deve abrir na série de pontos corridos em que
   o Remo está, com o Remo escolhido (`RF-escolher-time`).
2. Ler no topo a posição, os pontos e a data da última atualização
   (`RF-classificacao`, `RF-data-atualizacao`).
3. Ler os cards de chance por zona e o gráfico de posição final (`RF-chances-zona`, `RF-simular`).
4. Trocar para a Série B e escolher outro time: 2 ações (`QS-facilidade`).
5. Abrir a Copa Verde: campanha, campeão, grupos e chaves (`RF-campanha-copa`).
6. Repetir os passos 1 a 3 com 390 px de largura (celular).

## Evidências coletadas

| Evidência | Resultado |
|---|---|
| Roteiro no Chrome, com dados reais (2026-10-31) | passos 1 a 5 ok, sem erros no console. Série A, rodada 33: Remo em 19º, 29 pontos, 99% de rebaixamento |
| Largura de 390 px (iframe no Chrome do computador) | sem rolagem lateral; abas, seletor, posição e chances visíveis sem rolar |
| Tempo até as chances aparecerem a 390 px | 713 ms, com rede e banco reais, na CPU do computador |
| Simulação só da liga aberta | ao carregar, só a Série A estava simulada; a Série B foi simulada ao abrir a aba |
| UUID das edições no ge real | as 4 ligas acharam o UUID na página; nenhum aviso falso |
| Contratos | 10 de 10 verdes (`daia verify SP4`) |

### Precisão do modelo (teste retroativo)

Previsão de vitória, empate e derrota dos jogos já disputados depois de cada
rodada de corte, treinando só com as rodadas anteriores. Comparação com um
palpite ingênuo: as frequências de vitória do mandante, empate e vitória do
visitante no treino. Brier score: quanto menor, melhor.

| Liga | Corte | Jogos previstos | Brier do modelo | Brier ingênuo | Acerto do favorito |
|---|---|---|---|---|---|
| Série A | rodada 10 | 229 | 0,627 | 0,637 | 49% |
| Série A | rodada 19 | 139 | 0,611 | 0,636 | 49% |
| Série A | rodada 26 | 70 | 0,556 | 0,608 | 59% |
| Série B | rodada 10 | 254 | 0,619 | 0,654 | 44% |
| Série B | rodada 19 | 164 | 0,601 | 0,643 | 47% |
| Série B | rodada 26 | 94 | 0,598 | 0,638 | 49% |

O modelo ficou melhor que o palpite ingênuo nos 6 cortes, mas com vantagem
pequena (0,01 a 0,05). Os cortes compartilham jogos, então não são amostras
independentes. Essa é a precisão por jogo; a das probabilidades de posição
final ainda não foi medida, porque a temporada não terminou.

## Hipóteses

### `BD-situacao-facil`: **inconclusiva**

> Um torcedor sem conhecimento de estatística encontra sozinho, numa única
> página, a posição e a campanha do seu time em cada campeonato.

A evidência técnica sustenta as condições: a posição e a campanha aparecem no
topo, com no máximo 2 ações, também no celular. Mas nenhum torcedor além do
mantenedor usou o site sob observação. A hipótese fala do torcedor, não da página.

### `BD-probabilidades`: **inconclusiva**

> O torcedor entende as probabilidades apresentadas por zona do regulamento e
> consegue responder, com elas, como o seu time deve terminar o campeonato.

As probabilidades existem por zona e o modelo prevê melhor que um palpite
ingênuo, por pouco. Ninguém verificou se o torcedor entende os números. Isso
vale, por exemplo, para "99% Rebaixados" ao lado de "Pontos esperados 34.4".

### `BD-manutencao-baixa` (sem hipótese declarada)

Tem evidência a favor: virada de temporada sem alteração, testes verdes e aviso
de falha. Será confirmado de verdade só depois de semanas de execução real.

## Como tornar as hipóteses conclusivas

- Pedir a 3 a 5 torcedores (de preferência não programadores) que abram o site
  no próprio celular e respondam, sem ajuda: "em que posição seu time está?" e
  "qual a chance de ele cair ou subir?". Registrar acertos e dúvidas aqui.
- Depois da última rodada de 2026, comparar as probabilidades de zona com o
  resultado final (calibração).

## Limitações

- **Sem usuários reais.** Nenhum torcedor foi observado; as duas hipóteses
  continuam inconclusivas.
- **Celular emulado.** A largura de 390 px foi testada num iframe no computador,
  com a CPU do computador. O limiar de 3 s em celular comum não foi medido.
- **Sync real não executado.** O coletor alterado ainda não rodou contra o banco
  real. Isso acontece na primeira execução do GitHub Actions depois do push.
- **Precisão limitada.** O teste retroativo cobre só os jogos de 2026 das Séries A e
  B, com cortes que se sobrepõem. O Parazão e a Copa Verde não têm simulação.
- **Dívida da SP4.** Os 3 itens aceitos na assinatura da SP4 continuam abertos.
