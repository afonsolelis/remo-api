# Preparação do computador da aula

Checklist para a Aula 2 de ES08 (quarta, 04/11/2026). A aula constrói ao vivo, por prompts, um Supabase local
(Postgres e PostgREST em docker compose), um teste de carga em k6 e um proxy com cache. Tudo roda offline depois
que as imagens estiverem baixadas, exceto o agente de IA, que precisa de internet.

## Na véspera

- [ ] Instalar ou atualizar o **Docker Desktop** e confirmar que ele está rodando:
      `docker version` e `docker compose version` (Compose v2).
- [ ] Reservar memória para o Docker (Settings → Resources): pelo menos 4 GB e 4 CPUs.
- [ ] Baixar as quatro imagens com antecedência, porque a rede da sala pode estar lenta:

      docker pull postgres:16-alpine
      docker pull postgrest/postgrest:v12.2.3
      docker pull grafana/k6:0.54.0
      docker pull nginx:1.27-alpine

- [ ] Clonar o projeto (ou atualizar, se já existir):
      `git clone https://github.com/afonsolelis/remo-api.git` e `cd remo-api && git pull`.
- [ ] Conferir que `laboratorio/seed.sql`, `laboratorio/AGENTS.md` e este arquivo estão lá.
- [ ] Instalar o **Claude Code** e fazer login (`claude`, depois `/login`). Abrir uma vez na pasta `remo-api` e
      aceitar a confiança na pasta, para não aparecer o diálogo durante a aula.
- [ ] Deixar livres as portas 3000 (PostgREST), 5432 (Postgres) e 8080 (proxy). No Windows:
      `netstat -ano | findstr ":3000 :5432 :8080"` não deve listar nada em LISTENING.

## Ensaio no computador da aula (recomendado, 15 min)

Faça o ensaio numa branch descartável para chegar à aula com a `main` limpa:

    git switch -c ensaio
    # rode os prompts das Etapas 01 a 04 (estão no material e nos slides da aula)
    docker compose -f laboratorio/docker-compose.yml down -v
    git switch main
    git branch -D ensaio
    git clean -n          # confira o que será apagado
    git clean -fd docs/atam docs/prompts.md laboratorio/init laboratorio/carga laboratorio/resultados

No ensaio, confira os números de referência obtidos no computador de preparação, com 200 usuários virtuais
e o k6 dentro da rede do compose:

| Medida | PostgREST direto | Proxy com cache |
|---|---|---|
| p95 | cerca de 1,1 s | cerca de 36 ms |
| Falhas | 0% | 0% |

Os valores mudam com a máquina. O que importa é o direto passar dos 500 ms do cenário e o proxy ficar abaixo.
Se o direto ficar abaixo de 500 ms, aumente o pico da rampa no prompt da Etapa 03 de 200 para 400 usuários.

## Antes de entrar na sala

- [ ] Docker Desktop aberto e com o motor verde.
- [ ] `git status` limpo na `main` do remo-api e nenhum contêiner do laboratório rodando (`docker ps`).
- [ ] Terminal aberto na pasta `remo-api`, com fonte grande para projeção (pelo menos 18 pt).
- [ ] Claude Code aberto na pasta `remo-api`, em modo que pede confirmação antes de editar.
- [ ] Deck da aula aberto no navegador:
      `https://afonsolelis.github.io/aulas/pages/module-8-eng-software/slides/slide-lesson-2.html`.
- [ ] Material aberto em outra aba, como reserva para copiar os prompts.

## Se algo falhar durante a aula

- **O agente demora ou trava:** os prompts estão completos no material. Siga a teoria e volte ao artefato depois.
  Em último caso, mostre os números de referência da tabela acima.
- **`docker compose up` falha por porta ocupada:** troque a porta publicada no `docker-compose.yml` (por exemplo
  3001) e ajuste os curls.
- **O PostgREST sobe antes do Postgres terminar o seed:** `docker compose -f laboratorio/docker-compose.yml restart rest`.
- **Para recomeçar uma etapa do zero:** `docker compose -f laboratorio/docker-compose.yml down -v` apaga o banco e o
  próximo `up` recarrega o schema e o seed.
- **Sem internet na sala:** o laboratório local continua funcionando, mas o agente não. Use o material e os números
  de referência.

## Depois da aula

- [ ] `docker compose -f laboratorio/docker-compose.yml down -v`.
- [ ] Decidir se os artefatos gerados (`docs/atam/`, `docs/prompts.md`, `laboratorio/`) entram na `main` do remo-api.
