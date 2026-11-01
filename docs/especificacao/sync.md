# Especificação: coletor (`scripts/sync_supabase.py`)

Contrato de integração com o ge e com o banco. Comportamento recuperado do
código; as mudanças estão marcadas como **novo**.

## Entradas

- `DATABASE_URL` (ambiente). Sem ela, o script termina com código diferente de zero.
- `LIGAS`: `liga -> (nome, tipo, página no ge, UUID reserva)`.

## Edição atual (`RF-edicao-atual`, `QS-virada-temporada`)

`uuid_atual(pagina, reserva)`:

- Lê `https://ge.globo.com/<pagina>/` e devolve o primeiro `data-bs-resource-id`
  com formato de UUID.
- Se a página falha (erro de rede ou HTTP) ou não tem o atributo, devolve `reserva`.

## Por liga (`RF-coletar`, `RF-preservar`, `QS-tolerancia-fonte`)

1. Busca todas as fases da edição (`fetch_liga`).
2. Se a busca levanta exceção: registra "falhou" e **não** toca no banco dessa liga.
3. Se não há partidas: registra "sem jogos" e **não** toca no banco dessa liga.
4. Senão, numa única transação: faz upsert de `remo_ligas` com `atualizado_em = now()`,
   apaga e regrava `remo_clubes` e `remo_partidas` da liga.
5. Segue para a próxima liga em qualquer caso.

## Saída (`RF-avisar-falha`) — **novo**

- Termina com código 0 se todas as ligas foram gravadas.
- Termina com código 1 se a busca de alguma liga levantou exceção, ou se a
  edição atual de alguma liga não foi achada na página e o UUID reserva foi
  usado (risco R1 do ATAM). Isso acontece depois de processar todas as outras.
  A mensagem final lista as ligas afetadas e o motivo.
- "Sem jogos" não conta como falha: acontece no começo de uma edição nova,
  antes de os confrontos terem os dois clubes definidos.
- O GitHub Actions marca a execução como falha e envia o e-mail padrão ao
  mantenedor (`AD-aviso-por-falha`).

## Esquema (`QS-somente-leitura`, `RNF-banco-compartilhado`)

`supabase/schema.sql` é idempotente, só cria objetos com prefixo `remo_`, liga o
RLS em todas as tabelas e cria só políticas `for select`.
