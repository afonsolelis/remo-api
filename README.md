# Remo nos Campeonatos

Site estático (GitHub Pages) que acompanha os campeonatos do **Clube do Remo**
(time padrão; dá para escolher qualquer outro no filtro ou clicando na tabela):

- **Série A e Série B** — classificação, pontos por rodada, próximos jogos e
  uma simulação Monte Carlo do resto do campeonato, rodada no navegador.
- **Parazão e Copa Verde** — campanha do time, jogos com placar e pênaltis,
  tabelas dos grupos, chaves do mata-mata e campeão.

Site: https://afonsolelis.github.io/remo-api/

## Como funciona

```
API de tabelas do ge ──(GitHub Actions, 00:00 Belém)──► Postgres (Supabase) ──(REST, chave pública)──► site
```

- `index.html`, `style.css`, `app.js` — a página, com uma aba por campeonato
  e filtro de time. Ao mudar `app.js` ou `style.css`, troque o `?v=` no
  `index.html` para furar o cache do navegador. Usa ApexCharts para os gráficos. Lê as tabelas `remo_*`
  pela API REST do Supabase e simula 10 mil campeonatos com um modelo Poisson
  simples (ataque/defesa por time) ao abrir a página ou no botão "Simular de
  novo". As zonas (Libertadores, acesso, rebaixamento…) vêm das faixas que o
  próprio ge publica.
- `scripts/sync_supabase.py` — baixa todas as fases de cada campeonato do ge
  (pontos corridos, grupos e mata-mata) e grava no Postgres. Para incluir um
  campeonato, adicione-o em `LIGAS` no script e no topo do `app.js`. Cria as tabelas de `supabase/schema.sql` se faltarem.
  O identificador de cada tabela no ge muda a cada temporada; o script o lê
  da página do campeonato a cada execução, então a virada de ano é automática.
- `.github/workflows/dados.yml` — roda o sync todo dia à meia-noite de Belém
  (e manualmente em *Actions → Atualizar dados → Run workflow*). Ele se
  reativa a cada execução, porque o GitHub desliga agendamentos após 60 dias
  sem atividade no repositório.

## Configuração

- Secret do repositório `DATABASE_URL`: string de conexão do Postgres
  (pooler do Supabase).
- A URL da API REST (`API_URL`) e a chave *publishable* (`API_CHAVE`) ficam no
  topo de `app.js`. Essa chave é pública; o RLS só permite leitura. Para trocar
  o Supabase por um Postgres + PostgREST próprio, veja
  `docs/implantacao/hostinger.md`.
- O GitHub Pages publica a raiz da branch `main`.

## Rodando localmente

```bash
pip install -r requirements.txt
DATABASE_URL=postgresql://... python scripts/sync_supabase.py   # carrega o banco
python -m http.server 8000                                       # abre http://localhost:8000
```
