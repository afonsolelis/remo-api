# View engineering

Como as funções da view computational são distribuídas em nós, canais e
políticas. Atende `CON-confiabilidade` e `CON-manutencao`.

## Modelo de implantação

```mermaid
flowchart TB
  subgraph Runner["Nó: runner efêmero do GitHub Actions (ubuntu)"]
    COL[Coletor + Agendador]
  end
  subgraph Pages["Nó: GitHub Pages (raiz da main)"]
    EST[index.html, style.css, app.js, calculos.js]
  end
  subgraph Supabase["Nó: Supabase (projeto compartilhado)"]
    PG[(Postgres: tabelas remo_*)]
    API[PostgREST]
    PG --- API
  end
  subgraph Navegador["Nó: navegador do torcedor (celular ou computador)"]
    PAG[Apresentação + Cálculos]
  end
  CDN[jsDelivr: ApexCharts 3.54.1]
  GE[ge.globo.com / api.globoesporte.globo.com]

  COL -- "HTTPS, timeout 20 s" --> GE
  COL -- "Postgres sobre TLS, DATABASE_URL (secret)" --> PG
  PAG -- "HTTPS, estático" --> EST
  PAG -- "HTTPS, credencial pública, só select" --> API
  PAG -- "HTTPS" --> CDN
```

## Canais e políticas

| Canal | Política | Origem |
|---|---|---|
| Runner → ge | requisição com timeout de 20 s; falha de uma liga não interrompe as outras | `AD-isolamento-por-liga` |
| Runner → Postgres | uma transação por liga; credencial só no secret `DATABASE_URL` | `AD-isolamento-por-liga`, `RNF-sem-segredos` |
| Navegador → PostgREST | credencial publishable; RLS libera só `select` | `AD-rls-somente-leitura` |
| Navegador → Pages | arquivos estáticos; `?v=` no `index.html` invalida o cache | `AD-estatico-sem-servidor` |
| Agendador → mantenedor | execução com falha gera o e-mail padrão do GitHub Actions | `AD-aviso-por-falha` |

## Alocação de carga

- A simulação roda no nó mais fraco (o celular do torcedor). Por isso é feita só
  para a liga aberta e com estruturas leves (`AD-simulacao-sob-demanda`).
- O ge só é acessado pelo runner, uma vez por dia. O torcedor nunca depende do ge
  em tempo real (`AD-coleta-agendada`).
