# CLAUDE.md

Guia para o Claude Code neste repositório.

## Visão geral

**Remo no Brasileirão** é um site estático no GitHub Pages (raiz da branch `main`) que acompanha o Clube do Remo na
Série A. Os dados vêm da API pública do Cartola FC (`https://api.cartola.globo.com`) e ficam num Postgres do Supabase
(o mesmo projeto do `aulas_mackenzie`, tabelas com prefixo `remo_`).

- `index.html`, `style.css`, `app.js` — página única. HTML/CSS simples e ApexCharts (CDN, versão fixa). Lê o banco pela
  API REST com a chave *publishable* e roda a simulação Monte Carlo (Poisson) no navegador.
- `scripts/sync_supabase.py` — baixa o Cartola e faz upsert no Postgres. Executa `supabase/schema.sql` (idempotente)
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
- Trate a API do Cartola como não confiável; o site sempre mostra o último dado gravado no banco.
- Sem suíte de testes: valide rodando o sync e abrindo a página localmente.
- Commits com assunto curto, imperativo, em português (ex.: `Adiciona gráfico de pontos`).
