# View technology

As tecnologias que realizam cada nó da view engineering. Cada escolha é uma
decisão registrada com a alternativa preterida (`AD-tec-*`). Atende
`CON-manutencao`.

## Modelo

| Nó (engineering) | Tecnologia | Decisão |
|---|---|---|
| Runner | GitHub Actions, `ubuntu-latest`, Python 3.12, `requests`, `psycopg[binary]` | `AD-tec-coleta` |
| Hospedagem estática | GitHub Pages, sem Jekyll (`.nojekyll`) | `AD-estatico-sem-servidor` |
| Banco e API de leitura | Supabase (Postgres + PostgREST), projeto compartilhado | `AD-tec-banco` |
| Página | HTML, CSS e JavaScript sem framework; ApexCharts 3.54.1 por CDN | `AD-tec-pagina` |
| Testes | `node:test` (JavaScript) e `unittest` (Python), sem dependências | `AD-tec-testes` |

## Restrições aplicadas

- `RNF-sem-custo`: todos os serviços estão no plano gratuito.
- `RNF-simplicidade`: nenhuma etapa de build. `calculos.js` é um script comum,
  carregado antes de `app.js`, que também exporta as funções para o Node.
- `RNF-banco-compartilhado`: só objetos com prefixo `remo_`.
