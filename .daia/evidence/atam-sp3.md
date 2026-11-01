# ATAM — primeira volta (SP3)

Redigido com IA (`@atam`) em 2026-10-31, a partir da árvore de utilidade da SP2.

## Cenários e decisões

| Cenário (imp., dif.) | Decisões | Táticas | Situação |
|---|---|---|---|
| `QS-tolerancia-fonte` (H,H) | `AD-coleta-agendada`, `AD-isolamento-por-liga`, `AD-aviso-por-falha` | transactions, exception-detection, exception-handling, sanity-checking, passive-redundancy, degradation, monitor | atendido hoje (`TC-tolerancia-fonte` verde); aviso de falha em vermelho |
| `QS-atualidade` (H,M) | `AD-coleta-agendada` | maintain-multiple-copies-data | verde, mas verificado de forma estática |
| `QS-facilidade` (H,L) | `AD-modulo-calculos`, `AD-tec-pagina` | — | vermelho até existir `calculos.js` |
| `QS-virada-temporada` (M,H) | `AD-uuid-dinamico` | defer-binding, degradation | verde |
| `QS-desempenho` (M,M) | `AD-simulacao-sob-demanda`, `AD-estatico-sem-servidor` | increase-resource-efficiency, schedule-resources, manage-sampling-rate, reduce-overhead | vermelho; medido ~330 ms com 100 jogos restantes, estimado acima de 1 s com 380 |
| `QS-somente-leitura` (M,L) | `AD-rls-somente-leitura` | authorize-actors, limit-access, limit-exposure, separate-entities | verde |

## Pontos de tradeoff

1. **Disponibilidade × atualidade** (`AD-coleta-agendada`): o site sobrevive à
   queda do ge, mas o dado pode ter até um dia.
2. **Preservar o dado × mostrar dado velho** (`AD-isolamento-por-liga`): mitigado
   pela data da atualização visível (`RF-data-atualizacao`).
3. **Custo zero × desempenho no celular** (`AD-estatico-sem-servidor`,
   `AD-simulacao-sob-demanda`): o processamento fica no dispositivo do torcedor.
4. **Zero manutenção × acoplamento ao HTML do ge** (`AD-uuid-dinamico`).

## Riscos

- **R1:** se o ge mudar o HTML, o coletor usa em silêncio o UUID reserva da
  temporada passada. Sem falha, sem aviso. Isso afeta `QS-virada-temporada` e
  `QS-atualidade`. **Mitigado por decisão do mantenedor (2026-10-31):** usar o
  UUID reserva conta como falha em `AD-aviso-por-falha` (teste
  `test_usar_o_uuid_reserva_e_falha`, vermelho).
- **R2:** o proxy de desempenho pode aprovar um tempo que um celular de entrada reprova.
- **R3:** dados do ge com jogos mas errados passam pela verificação de sanidade.
- **R4:** o Supabase compartilhado é ponto único de falha e de cota. Risco aceito
  pelo mantenedor, sem cenário próprio.

## Não riscos

- A escrita por visitantes é impossível sem o secret (`TC-somente-leitura` verde).
- A falha de uma liga não contamina as outras (`TC-tolerancia-fonte` verde).
