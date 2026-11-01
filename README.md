# Remo no Brasileirão

Site estático (GitHub Pages) que acompanha o **Clube do Remo** na Série A:
classificação, pontos por rodada, próximos jogos e uma simulação Monte Carlo
do resto do campeonato, rodada no navegador.

Site: https://afonsolelis.github.io/remo-api/

## Como funciona

```
API do Cartola ──(GitHub Actions, 00:00 Belém)──► Postgres (Supabase) ──(REST, chave pública)──► site
```

- `index.html`, `style.css`, `app.js` — a página. Usa ApexCharts para os
  gráficos. Lê as tabelas `remo_*` pela API REST do Supabase e simula 10 mil
  campeonatos com um modelo Poisson simples (ataque/defesa por time) ao abrir
  a página ou no botão "Simular de novo".
- `scripts/sync_supabase.py` — baixa todas as rodadas do Cartola e grava no
  Postgres. Cria as tabelas de `supabase/schema.sql` se faltarem.
- `.github/workflows/dados.yml` — roda o sync todo dia à meia-noite de Belém
  (e manualmente em *Actions → Atualizar dados → Run workflow*).

## Configuração

- Secret do repositório `DATABASE_URL`: string de conexão do Postgres
  (pooler do Supabase).
- A URL do projeto e a chave *publishable* ficam no topo de `app.js`. Essa
  chave é pública; o RLS só permite leitura.
- O GitHub Pages publica a raiz da branch `main`.

## Rodando localmente

```bash
pip install -r requirements.txt
DATABASE_URL=postgresql://... python scripts/sync_supabase.py   # carrega o banco
python -m http.server 8000                                       # abre http://localhost:8000
```
