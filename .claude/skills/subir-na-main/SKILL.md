---
name: subir-na-main
description: Commita e envia para a main toda mudança pedida pelo mantenedor, sem perguntar antes. Use ao terminar qualquer alteração de código, página, dados ou documentação neste repositório.
---

# Subir na main

Projeto pessoal: o mantenedor autorizou commit e push direto na `main` ao fim de cada pedido, sem confirmação.

## Quando

Ao terminar qualquer pedido que mude arquivos versionados. Não use quando o pedido for só uma pergunta, ou quando
o mantenedor disser para não subir.

## Passos

1. Se mudou `app.js`, `calculos.js` ou `style.css`, confira se o `?v=` no `index.html` foi trocado.
2. Rode os testes: `node --test tests/*.test.js` e `python -m unittest tests.test_sync`. Se algum falhar, corrija.
   Se não der para corrigir, **não suba** e explique o motivo.
3. Confira `git status` e adicione só os arquivos da mudança. Nunca commite senha, string de conexão, `.env` nem
   arquivos de teste temporários.
4. Commit com assunto curto, imperativo, em português (ex.: `Adiciona aba de notícias`), terminando com a linha de
   coautoria pedida pelo Claude Code.
5. `git push origin main`.
6. Se a mudança precisa de dado novo no banco (tabela ou coluna nova em `supabase/schema.sql`, coleta nova no sync),
   dispare o workflow certo depois do push: `gh workflow run dados.yml` (tudo) ou `gh workflow run noticias.yml`
   (só notícias).
7. No resumo final, diga o hash do commit e o que foi enviado. Lembre se o `daia status` pede reassinatura de baseline
   (só o mantenedor assina).

Nunca use `--force`, `--no-verify` nem reescreva o histórico.
