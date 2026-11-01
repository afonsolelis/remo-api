# CLAUDE.md

Guia para o Claude Code neste repositório.

## Visão geral

**Remo nos Campeonatos** é um site estático no GitHub Pages (raiz da branch `main`) que acompanha os campeonatos do
Remo (Séries A e B, Parazão, Copa Verde; Remo como time padrão). Os dados vêm da API de tabelas do ge
(`https://api.globoesporte.globo.com/tabela`) e ficam num Postgres do Supabase (o mesmo projeto do `aulas_mackenzie`,
tabelas `remo_ligas`, `remo_clubes`, `remo_partidas`).

- `index.html`, `style.css`, `app.js` — página única com abas por campeonato e filtro de time. HTML/CSS simples e
  ApexCharts (CDN, versão fixa). Lê o banco pela API REST com a chave *publishable*. Ligas `pontos` rodam a simulação
  Monte Carlo (Poisson) no navegador, com zonas vindas de `remo_ligas.zonas` (faixas do ge); ligas `copa` mostram
  campanha, grupos e chaves a partir de `remo_ligas.fases`. Troque o `?v=` no `index.html` a cada mudança de JS/CSS.
- `scripts/sync_supabase.py` — baixa todas as fases de cada campeonato de `LIGAS` (pontos corridos, grupos, mata-mata)
  e regrava cada liga no Postgres, uma transação por liga: se uma falhar, as outras seguem e o dado anterior fica. O
  UUID de cada tabela do ge muda a cada temporada e é lido da página do campeonato a cada execução. Executa `supabase/schema.sql` (idempotente) antes de gravar.
- `.github/workflows/dados.yml` — sync diário às 03:00 UTC (00:00 em Belém), usa o secret `DATABASE_URL`
  e se reativa a cada execução (o GitHub desliga agendamentos após 60 dias sem atividade).

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
