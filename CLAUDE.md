# CLAUDE.md

Guia para o Claude Code neste repositório.

## Visão geral

**Remo nos Campeonatos** é um site estático no GitHub Pages (raiz da branch `main`) que acompanha os campeonatos do
Remo (Séries A e B, Parazão, Copa Verde; Remo como time padrão). Os dados vêm da API de tabelas do ge
(`https://api.globoesporte.globo.com/tabela`) e ficam num Postgres próprio na Hostinger (banco `remo`, tabelas
`remo_ligas`, `remo_clubes`, `remo_partidas`, `remo_noticias`), lido pelo site via PostgREST em
`https://remo-api.afonsolelis.tech`. A infraestrutura (compose do Coolify) fica no repositório `hostinger`; guia em
`docs/implantacao/hostinger.md`. Os nomes `supabase/` e `sync_supabase.py` ficaram da época do Supabase.

- `index.html`, `style.css`, `app.js` — página única com abas por campeonato e filtro de time. HTML/CSS simples e
  ApexCharts (CDN, versão fixa). Lê o banco pela API REST (PostgREST, sem chave). Ligas `pontos` rodam a simulação
  Monte Carlo (Poisson) no navegador, só quando a liga é aberta, com zonas vindas de `remo_ligas.zonas` (faixas do ge);
  ligas `copa` mostram campanha, grupos e chaves a partir de `remo_ligas.fases`. A aba Notícias lê `remo_noticias`.
  A aba Próximos jogos mostra o calendário de todas as ligas até 31/12 (fuso de Belém), por dia, com
  horário, estádio, link do ge e filtro de clube.
  A aba Resultados passados mostra os jogos encerrados do ano, do mais recente ao mais antigo, com filtro de
  período (de/até) e de clube (com o retrospecto do clube).
  A aba Operação lê as execuções dos workflows direto da API pública do GitHub (funciona sem o banco) e marca ⚠️
  quando alguma atualização falhou ou atrasou.
  Troque o `?v=` no `index.html` a cada mudança de JS/CSS.
- `calculos.js` — funções puras (classificação, simulação, copas, time padrão), sem DOM nem rede. Script comum
  carregado antes de `app.js`; também exporta para o Node, onde os testes o usam. Contrato em
  `docs/especificacao/calculos.md`.
- `scripts/sync_supabase.py` — baixa todas as fases de cada campeonato de `LIGAS` (pontos corridos, grupos, mata-mata)
  e regrava cada liga no Postgres, uma transação por liga: se uma falhar, as outras seguem e o dado anterior fica. O
  UUID de cada tabela do ge muda a cada temporada e é lido da página do campeonato a cada execução. Executa
  `supabase/schema.sql` (idempotente) antes de gravar. Termina com erro se alguma liga falhou ou se usou o UUID
  reserva, para o GitHub avisar o mantenedor por e-mail. Também grava as últimas matérias do ge de cada clube
  (`noticias` como argumento faz só isso). Contrato em `docs/especificacao/sync.md`.
- `tests/` — contratos de teste sem dependências: `node:test` para `calculos.js` e `unittest` para o sync.
- `docs/arquitetura/`, `docs/especificacao/` e `.daia/` — documentação no método DAIA-E (ver abaixo).
- `.github/workflows/dados.yml` — sync diário às 03:00 UTC (00:00 em Belém), usa o secret `DATABASE_URL`
  e se reativa a cada execução (o GitHub desliga agendamentos após 60 dias sem atividade). `noticias.yml` atualiza
  só as notícias a cada 2 horas.

## Comandos

```bash
pip install -r requirements.txt
DATABASE_URL=postgresql://... python scripts/sync_supabase.py
python -m http.server 8000
node --test tests/*.test.js
python -m unittest tests.test_sync
```

## Processo (DAIA-E)

O projeto segue o DAIA-E (`npm install -g github:afonsolelis/daia-e-core`). O modelo fica em `.daia/model/`, as
evidências em `.daia/evidence/` e as baselines assinadas em `.daia/baselines/` (não edite à mão). Comece por
`daia next` e `daia status`. Mudanças em artefatos de baseline assinada pedem nova aprovação do mantenedor; só ele
assina (`daia baseline sign`). Os testes rodam com `daia verify`.

## Regras

- Mantenha tudo simples: sem framework, sem build, sem bundler.
- Texto para o usuário em português.
- Só crie/altere tabelas `remo_*`.
- Nunca commite senha ou string de conexão; a API é pública por design, e o papel `anon` só tem `select`.
- Trate a API do ge como não confiável; o site sempre mostra o último dado gravado no banco.
- Testes sem dependências (`node:test` e `unittest`): rode os dois antes de commitar, e também o sync e a página
  localmente quando mexer neles.
- Commits com assunto curto, imperativo, em português (ex.: `Adiciona gráfico de pontos`).
- Projeto pessoal: ao terminar cada pedido que mude arquivos, commite e envie direto para a `main`, sem perguntar.
  Siga a skill `subir-na-main` (testes antes, workflow depois quando houver dado novo).
