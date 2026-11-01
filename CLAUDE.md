# CLAUDE.md

Guia para o Claude Code neste repositório.

## Visão geral

**Remo nos Campeonatos** é um site estático no GitHub Pages (raiz da branch `main`) que acompanha as Séries A e B do
Brasileirão (Remo como time padrão). Os dados vêm da API de tabelas do ge (`https://api.globoesporte.globo.com/tabela`)
e ficam num Postgres do Supabase (o mesmo projeto do `aulas_mackenzie`, tabelas `remo_ligas`, `remo_clubes`,
`remo_partidas`).

- `index.html`, `style.css`, `app.js` — página única com abas por liga e filtro de time. HTML/CSS simples e ApexCharts
  (CDN, versão fixa). Lê o banco pela API REST com a chave *publishable* e roda a simulação Monte Carlo (Poisson) no
  navegador. As zonas da tabela vêm de `remo_ligas.zonas` (faixas do ge), nada fixo no código.
- `scripts/sync_supabase.py` — baixa as duas séries do ge e regrava cada liga no Postgres (uma transação por liga; se
  uma falhar, a outra segue e o dado anterior fica). Os UUIDs do ge mudam a cada temporada. Executa `supabase/schema.sql` (idempotente)
  antes de gravar.
- `.github/workflows/dados.yml` — sync diário às 03:00 UTC (00:00 em Belém), usa o secret `DATABASE_URL`.

## Comandos

```bash
pip install -r requirements.txt
DATABASE_URL=postgresql://... python scripts/sync_supabase.py
python -m http.server 8000
```

## Regras

- Mantenha tudo simples: sem framework, sem build, sem bundler.
- Texto para o usuário em português.
- O banco é compartilhado com outro projeto: só crie/altere tabelas `remo_*`.
- Nunca commite senha ou string de conexão; a chave *publishable* em `app.js` é pública por design, e o RLS só libera
  `select`.
- Trate a API do ge como não confiável; o site sempre mostra o último dado gravado no banco.
- Sem suíte de testes: valide rodando o sync e abrindo a página localmente.
- Commits com assunto curto, imperativo, em português (ex.: `Adiciona gráfico de pontos`).
