# Laboratório da Aula 2 de ES08 (Inteli)

Regras para o agente durante a aula "As decisões arquiteturais resolvem os defeitos?". Valem junto com o
`AGENTS.md` e o `CLAUDE.md` da raiz; em caso de conflito, prevalecem as regras deste arquivo enquanto durar a aula.

## Contexto

O site lê o Postgres do Supabase pela API REST (PostgREST) com a chave publishable. Cada visitante que abre a
página dispara 12 leituras em paralelo (`iniciar()` e `carregar()` em `app.js`: `remo_ligas`, `remo_clubes` e
`remo_partidas` para as quatro ligas). No laboratório, o Supabase é emulado localmente por Postgres e PostgREST em
docker compose, com os dados de `laboratorio/seed.sql`, e o teste de carga mede essa API.

## Uma etapa por vez

- Leia o prompt inteiro, mostre o plano em poucas linhas e espere o ok do professor antes de criar ou editar arquivos.
- Faça só o que a etapa pede e pare ao fim dela. A etapa seguinte vem em outro prompt.
- Ao fim de cada etapa, acrescente em `docs/prompts.md` uma seção com o número e o nome da etapa, a data, o prompt
  recebido copiado literalmente (sem corrigir digitação) e a lista de arquivos criados ou alterados.

## Onde escrever

- Arquivos de infraestrutura e de carga ficam em `laboratorio/` (`docker-compose.yml`, `init/`, `carga/`,
  `resultados/`, `nginx.conf`).
- Documentos de arquitetura ficam em `docs/atam/`.
- Não altere `app.js`, `calculos.js`, `index.html`, `supabase/schema.sql`, `scripts/` nem `.daia/`.

## Docker e carga

- Imagens com versão fixa: `postgres:16-alpine`, `postgrest/postgrest:v12.2.3`, `grafana/k6:0.54.0` e
  `nginx:1.27-alpine`. Elas já foram baixadas no computador da aula; não troque de versão.
- O k6 roda como serviço do compose, na mesma rede dos outros contêineres, para que o caminho de rede entre
  o host e os contêineres não contamine a medida.
- Senhas são só locais e ficam em `laboratorio/.env.example`; nunca use a `DATABASE_URL` de produção.
- Não rode o sync (`scripts/sync_supabase.py`) contra o banco local nem contra o de produção.

## Git

Durante a aula, não commite nem envie nada. O professor decide ao final o que entra na `main`.
