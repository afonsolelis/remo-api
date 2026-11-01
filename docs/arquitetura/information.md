# View information

Quais dados existem, como se relacionam e como mudam. Atende `CON-situacao`,
`CON-chances` e `CON-confiabilidade`. Recuperada do código (`supabase/schema.sql`,
`scripts/sync_supabase.py`, `app.js`) em 2026-10-31.

## Modelo estático

```mermaid
erDiagram
  LIGA ||--o{ CLUBE : "tem"
  LIGA ||--o{ PARTIDA : "tem"
  CLUBE ||--o{ PARTIDA : "mandante"
  CLUBE ||--o{ PARTIDA : "visitante"
  LIGA {
    text liga PK "serie_a, serie_b, parazao, copa_verde"
    text nome
    text tipo "pontos | copa"
    jsonb zonas "faixas do regulamento: nome, cor, posicoes"
    jsonb fases "fases, grupos e tabela oficial de cada grupo"
    int rodada_atual
    timestamptz atualizado_em "momento da última coleta bem-sucedida"
  }
  CLUBE {
    text liga PK
    int id PK "id do clube no ge; Remo = 364"
    text nome
    text abreviacao
    text escudo
  }
  PARTIDA {
    text liga PK
    bigint partida_id PK
    int rodada
    timestamptz data
    int casa_id
    int fora_id
    int gols_casa "nulo antes do jogo"
    int gols_fora
    bool encerrada
    text fase
    int fase_ordem
    text chave "grupo ou chave do mata-mata"
    int pen_casa
    int pen_fora
  }
```

Dados derivados, calculados no navegador e nunca gravados:

| Dado | Origem | Requisito |
|---|---|---|
| Classificação (PTS, J, V, E, D, GP, GC) | partidas encerradas | `RF-classificacao` |
| Probabilidade de cada posição final por clube | simulação dos jogos restantes | `RF-simular` |
| Probabilidade por zona | soma das posições de cada zona | `RF-chances-zona` |
| Vencedor da chave, campanha, campeão | partidas do mata-mata | `RF-campanha-copa` |

Invariantes:

- As partidas, os clubes e a liga são sempre regravados juntos (uma transação por liga).
- Nas ligas `pontos`, só as partidas da primeira fase entram na simulação.
- As probabilidades de posição de um clube somam 1, e cada posição soma 1 entre os clubes.

## Modelo dinâmico (ciclo de vida dos dados de uma liga)

```mermaid
stateDiagram-v2
  [*] --> Ausente
  Ausente --> Gravada: coleta com jogos
  Gravada --> Gravada: coleta com jogos (substitui tudo, atualizado_em = agora)
  Gravada --> Gravada: coleta falha ou sem jogos (mantém o dado anterior)
  Gravada --> NovaEdicao: ge publica nova temporada
  NovaEdicao --> Gravada: coleta lê o novo UUID e substitui a edição anterior
```
