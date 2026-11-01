# Inventário do software existente (recuperação)

Levantado com IA em 2026-10-31, a partir do repositório na branch `main`
(commit `6681f78`). Precisa de revisão humana.

## Código

| Arquivo | Linhas | O que faz |
|---|---|---|
| `index.html` | 66 | Página única com abas por campeonato e filtro de time. Carrega ApexCharts por CDN com versão fixa. |
| `app.js` | 429 | Lê `remo_ligas`, `remo_clubes` e `remo_partidas` pela API REST do Supabase com a chave publishable. Nas ligas `pontos`, monta a tabela e roda 10.000 simulações Monte Carlo (Poisson, com forças de ataque e defesa por time e médias de gols de mandante e visitante) no navegador e mostra as chances por posição e por zona. Nas ligas `copa`, mostra campanha, grupos, chaves e campeão. Time padrão: Remo (id 364). |
| `style.css` | 111 | Estilos da página. |
| `scripts/sync_supabase.py` | 199 | Lê o UUID da edição atual na página de cada campeonato no ge (com UUID de reserva), baixa todas as fases e regrava cada liga numa transação própria. Se uma liga falhar ou vier sem jogos, mantém o dado anterior e segue com as outras. Nas ligas `pontos`, guarda só os jogos da primeira fase. |
| `supabase/schema.sql` | 60 | Cria as tabelas `remo_*` e o RLS só de leitura. É idempotente e roda antes de cada sync. |
| `.github/workflows/dados.yml` | 30 | Sync diário às 03:00 UTC (00:00 em Belém) e manual, com o secret `DATABASE_URL`. Reativa o próprio agendamento a cada execução. |

## Integrações

- **API de tabelas do ge** (`api.globoesporte.globo.com/tabela`) e as páginas dos campeonatos no ge. Não é oficial nem documentada, por isso é tratada como não confiável.
- **Supabase Postgres**, compartilhado com o projeto `aulas_mackenzie`. Este projeto só usa as tabelas `remo_*`.
- **GitHub Pages** (raiz da `main`) e **GitHub Actions**.
- **ApexCharts** por CDN.

## Testes

Não há suíte de testes. Hoje a validação é manual: rodar o sync e abrir a
página localmente (`CLAUDE.md`).

## Documentos

`CLAUDE.md` (guia e regras do projeto), `AGENTS.md` (aponta para o
`CLAUDE.md`), `README.md` e o histórico do git.

## Resultados

- As views da SP1 foram redigidas a partir das respostas do mantenedor e deste inventário.
- A fronteira atual (A2, A3 e A4 automatizadas, A1 externa, A5 manual) é a que o código implementa.

## Limitações

- O inventário foi feito por leitura do código. Nada foi executado: nem o sync, nem a página.
- `AGENTS.md` cita só as Séries A e B. Está desatualizado em relação ao Parazão e à Copa Verde.
- Quando uma liga falha no sync, o script registra a falha no log e sai com sucesso. O GitHub não avisa o mantenedor, então só uma falha geral (por exemplo, de conexão com o banco) fica visível sem abrir o log.
- A simulação cobre só a primeira fase das ligas `pontos`. Não há estimativa de chances para fases eliminatórias nem para as copas.
- A pasta `data/` (fora do git, no `.gitignore`) guarda JSONs de uma versão anterior do projeto. Não é usada pelo código atual.
- A precisão do modelo de Poisson nunca foi medida contra resultados reais.
