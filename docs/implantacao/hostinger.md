# Banco na Hostinger (Postgres + PostgREST)

Guia para tirar o banco do Supabase e usar um Postgres próprio numa VPS da Hostinger. O site continua estático
no GitHub Pages; só muda de onde ele lê e para onde o sync grava.

```
ge ──(Actions, psycopg)──► Postgres :5432 ──► PostgREST :3000 ──(HTTPS, Caddy)──► site (GitHub Pages)
```

## O que o código já aceita

- **Sync** (`scripts/sync_supabase.py`): conecta pela `DATABASE_URL`, qualquer Postgres serve. Na primeira
  execução o `supabase/schema.sql` cria as tabelas `remo_*` e os papéis `anon` e `authenticated` (sem login).
  Para isso o usuário da `DATABASE_URL` precisa ser dono do schema `public` e ter `CREATEROLE` na primeira vez
  (ou rode o `schema.sql` uma vez como administrador).
- **Site** (`app.js`): a URL da API e a chave ficam em `API_URL` e `API_CHAVE`, no topo do arquivo.

## Passos na VPS

1. Postgres 16+ com acesso externo à porta 5432 liberado só com senha forte e SSL (o GitHub Actions precisa
   alcançar o banco; os IPs do Actions variam, então não dá para fechar por IP).
2. Usuário de escrita para o sync, dono das tabelas:
   ```sql
   create role remo_sync login password '<senha>' createrole;
   create database remo owner remo_sync;
   ```
3. Papel que o PostgREST usa para conectar (troca para `anon` a cada requisição):
   ```sql
   create role authenticator login noinherit password '<outra senha>';
   grant anon to authenticator;   -- depois que o schema.sql criar o anon
   ```
4. PostgREST (`postgrest.conf`):
   ```
   db-uri = "postgres://authenticator:<outra senha>@localhost:5432/remo"
   db-schemas = "public"
   db-anon-role = "anon"
   server-port = 3000
   ```
   O PostgREST libera CORS para qualquer origem por padrão, o que basta (só há leitura).
5. HTTPS na frente do PostgREST (o GitHub Pages é HTTPS e o navegador bloqueia chamada HTTP). Com Caddy:
   ```
   api.seudominio.com.br {
     reverse_proxy localhost:3000
   }
   ```

## Troca

1. Secret `DATABASE_URL` no GitHub: `postgresql://remo_sync:<senha>@<host>:5432/remo?sslmode=require`.
2. Rodar `gh workflow run dados.yml` e conferir o log; depois `gh workflow run noticias.yml`.
3. Testar a API: `curl https://api.seudominio.com.br/remo_ligas?select=id` deve devolver as ligas, e um
   `POST` deve dar 401/403.
4. No `app.js`: `API_URL = "https://api.seudominio.com.br"` e `API_CHAVE = null`; trocar o `?v=` no `index.html`.
5. Religar o `schedule` em `.github/workflows/dados.yml` e `noticias.yml`.
6. Atualizar README, `docs/arquitetura/technology.md` e a decisão `AD-tec-banco` no `.daia` (pede nova
   assinatura do mantenedor).
