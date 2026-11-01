# Remo no Brasileirão

Site estático (GitHub Pages) que acompanha as **Séries A e B** do Brasileirão
(com o **Clube do Remo** como time padrão): classificação, pontos por rodada,
próximos jogos e uma simulação Monte Carlo do resto do campeonato, rodada no
navegador. Dá para escolher qualquer time no filtro ou clicando na tabela.

Site: https://afonsolelis.github.io/remo-api/

## Como funciona

```
API de tabelas do ge ──(GitHub Actions, 00:00 Belém)──► Postgres (Supabase) ──(REST, chave pública)──► site
```

- `index.html`, `style.css`, `app.js` — a página, com abas Série A / Série B
  e filtro de time. Usa ApexCharts para os gráficos. Lê as tabelas `remo_*`
  pela API REST do Supabase e simula 10 mil campeonatos com um modelo Poisson
  simples (ataque/defesa por time) ao abrir a página ou no botão "Simular de
  novo". As zonas (Libertadores, acesso, rebaixamento…) vêm das faixas que o
  próprio ge publica.
- `scripts/sync_supabase.py` — baixa todas as rodadas das duas séries do ge e
  grava no Postgres. Cria as tabelas de `supabase/schema.sql` se faltarem.
  Os UUIDs das tabelas do ge mudam a cada temporada (ver comentário em
  `LIGAS`).
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
