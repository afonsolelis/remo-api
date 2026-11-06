# Registro de prompts

## 2026-11-04 — Árvore de utilidade (passo 5 do ATAM)

**Saída**: `docs/atam/arvore-utilidade.md`

**Observação**: os arquivos citados no prompt (`app.js`, `supabase/schema.sql`, `scripts/sync_supabase.py`, `.daia/model/scenarios/`, `.daia/evidence/atam-sp3.md`, `laboratorio/AGENTS.md`) não existem neste repositório. Por decisão do responsável ("pode escrever, crie a árvore de utilidades"), a árvore foi feita sobre o sistema que está em produção: Streamlit com JSON em volume no Railway. Por isso o risco R4 não foi consultado.

**Prompt**:

```text
[C] Personagem
Você é arquiteto de software e conduz o passo 5 do ATAM no projeto Remo nos Campeonatos, um site estático que lê o Postgres do Supabase pela API REST (PostgREST).

[R] Pedido
Monte a árvore de utilidade do sistema em produção com cenários de desempenho, disponibilidade e segurança do lado do servidor. Leia app.js, supabase/schema.sql, scripts/sync_supabase.py, os cenários de .daia/model/scenarios/ e o ATAM de .daia/evidence/atam-sp3.md, em especial o risco R4.

[E] Exemplos
Folha de desempenho em seis partes. Fonte: 200 torcedores. Estímulo: abrem o site ao mesmo tempo depois de um gol, e cada abertura dispara 12 GETs em paralelo (4 ligas × 3 tabelas). Artefato: PostgREST e Postgres. Ambiente: pico de acesso. Resposta: todas as leituras são atendidas. Medida: p95 ≤ 500 ms e falhas < 1%.

[A] Ajustes
No mínimo dois cenários por atributo, cada um com medida numérica e par de prioridade (importância, dificuldade) em H, M ou L. Não repita os cenários de interface que já existem (legibilidade, celular, facilidade). Para cada folha (H,H) ou (H,M), aponte a decisão arquitetural envolvida e classifique o achado como ponto de sensibilidade, ponto de trade-off, risco ou não risco.

[T] Tipo de saída
docs/atam/arvore-utilidade.md com a árvore em lista aninhada, uma tabela com as seis partes de cada folha e uma seção com os achados da análise.

[E] Extras
Leia AGENTS.md e laboratorio/AGENTS.md. Mostre o plano, espere meu ok, escreva, registre o prompt em docs/prompts.md e pare.
```

## 2026-11-04 — Teste de carga com 200 acessos simultâneos

**Saída**: `docs/atam/teste-carga-200.md`, `scripts/loadtest.py` e uma nota no achado D1 de `docs/atam/arvore-utilidade.md`.

**Observação**: a mensagem trazia colado o prompt de um laboratório Postgres e PostgREST em docker compose. Esse laboratório depende de `app.js`, `supabase/schema.sql` e `laboratorio/seed.sql`, que não existem neste repositório, e não foi feito. O pedido do responsável foi o teste de carga. Ele foi executado contra o dashboard Streamlit, que é o sistema em produção, no cenário D1.

**Prompt**:

```text
vamos fazer o teste de carga e gere o relatório para 200 acessos simultaneos
```
