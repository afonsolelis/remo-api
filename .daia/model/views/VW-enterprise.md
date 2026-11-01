# View enterprise — Remo nos Campeonatos

Rascunho redigido com IA a partir das respostas do mantenedor (2026-10-31) e do
código existente. Revisado e aprovado pelo mantenedor em 2026-10-31.

## Propósito

Dar a torcedores fanáticos por futebol uma forma fácil de saber como o seu time
está nos campeonatos e quais as probabilidades de como ele termina cada um. O
Remo é o time padrão, mas qualquer time dos campeonatos acompanhados pode ser
escolhido.

## Partes interessadas e preocupações

| Parte interessada | Preocupações |
|---|---|
| Torcedor fanático (`STK-torcedor`) | situação do time (`CON-situacao`), chances ao fim do campeonato (`CON-chances`), facilidade de entender (`CON-facilidade`), dado atualizado e disponível (`CON-confiabilidade`) |
| Mantenedor (`STK-mantenedor`) | dado atualizado e disponível (`CON-confiabilidade`), manutenção com pouco esforço e sem custo (`CON-manutencao`) |

## Direcionadores

- `BD-situacao-facil`: saber de forma fácil como o time está (com hipótese).
- `BD-probabilidades`: saber as probabilidades de como o time termina (com hipótese).
- `BD-manutencao-baixa`: dados atualizados todo dia, de temporada a temporada, sem trabalho manual nem custo.

Não há metas numéricas: o mantenedor definiu o projeto como genérico, sem metas
de audiência ou de desempenho.

## Fronteira (IDEF0 A0)

| Atividade | Fronteira |
|---|---|
| A1 Publicar tabelas e resultados oficiais | externa (ge) |
| A2 Coletar e guardar os dados dos campeonatos | sistema |
| A3 Apresentar a situação do time escolhido | sistema |
| A4 Estimar as chances de classificação final | sistema |
| A5 Interpretar a situação e as chances do time | manual (torcedor) |

Campeonatos dentro do escopo hoje: Série A, Série B, Parazão e Copa Verde.

Fora do escopo (confirmado pelo mantenedor na assinatura da SP1): jogos ao vivo,
notícias, escalações e estatísticas de jogadores, contas de usuário,
notificações e chances para fases eliminatórias das copas.
