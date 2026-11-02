# Preparação do computador da aula (Linux Mint)

Checklist para a Aula 2 de ES08 (quarta, 04/11/2026, 11:00 às 13:00). A aula constrói ao vivo, por prompts, um
Supabase local (Postgres e PostgREST em docker compose), um teste de carga em k6 e um proxy com cache. Tudo roda
offline depois que as imagens estiverem baixadas, exceto o agente de IA, que precisa de internet.

Os comandos abaixo valem para o Linux Mint 21 ou 22, que usam a base do Ubuntu 22.04 ou 24.04.

## Na véspera

- [ ] Instalar o Docker Engine e o plugin do Compose pelo repositório oficial da Docker. O pacote `docker.io` do
      repositório do Mint traz um Compose antigo ou nenhum; use o da Docker:

      sudo apt-get update
      sudo apt-get install -y ca-certificates curl git
      sudo install -m 0755 -d /etc/apt/keyrings
      sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
      sudo chmod a+r /etc/apt/keyrings/docker.asc
      echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$UBUNTU_CODENAME") stable" \
        | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
      sudo apt-get update
      sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

      O `$UBUNTU_CODENAME` é o que faz funcionar no Mint: ele devolve `noble` ou `jammy`, e não o nome da versão
      do Mint, que o repositório da Docker não conhece.

- [ ] Usar o Docker sem `sudo`, para não digitar senha na frente da turma:

      sudo usermod -aG docker $USER
      # encerrar a sessão e entrar de novo (ou reiniciar)
      docker run --rm hello-world
      docker compose version          # precisa ser v2

- [ ] Garantir que o Docker sobe junto com o sistema: `sudo systemctl enable --now docker`.
- [ ] Baixar as quatro imagens com antecedência, porque a rede da sala pode estar lenta:

      docker pull postgres:16-alpine
      docker pull postgrest/postgrest:v12.2.3
      docker pull grafana/k6:0.54.0
      docker pull nginx:1.27-alpine

- [ ] Clonar o projeto (ou atualizar, se já existir):

      git clone https://github.com/afonsolelis/remo-api.git ~/remo-api
      cd ~/remo-api && git pull

- [ ] Conferir que `laboratorio/seed.sql`, `laboratorio/AGENTS.md` e este arquivo estão lá.
- [ ] Instalar o **Claude Code** e fazer login. O instalador nativo não precisa de Node:

      curl -fsSL https://claude.ai/install.sh | bash
      # abrir um terminal novo para o PATH ser recarregado
      cd ~/remo-api && claude          # fazer o login e aceitar a confiança na pasta

- [ ] Deixar livres as portas 3000 (PostgREST) e 8080 (proxy). O comando abaixo não deve imprimir nada:

      ss -ltn | grep -E ':(3000|8080)\b'

      Se houver um serviço local ocupando alguma delas, pare-o (`sudo systemctl stop <serviço>`) ou troque a porta
      publicada no prompt.

## Ensaio no computador da aula (recomendado, 15 min)

Faça o ensaio numa branch descartável para chegar à aula com a `main` limpa:

    cd ~/remo-api
    git switch -c ensaio
    # rode os prompts das Etapas 01 a 04 (estão no material e nos slides da aula)
    docker compose -f laboratorio/docker-compose.yml down -v
    git switch main
    git branch -D ensaio
    git clean -n          # confira o que será apagado
    git clean -fd docs/atam docs/prompts.md laboratorio/init laboratorio/carga laboratorio/resultados

No ensaio, confira os números de referência obtidos no computador de preparação, com 200 usuários virtuais e o
k6 dentro da rede do compose:

| Medida | PostgREST direto | Proxy com cache |
|---|---|---|
| p95 | cerca de 1,1 s | cerca de 36 ms |
| Falhas | 0% | 0% |

Os valores mudam com a máquina. O que importa é o direto passar dos 500 ms do cenário e o proxy ficar abaixo.
No Linux, sem a máquina virtual que o Docker Desktop usa no Windows, o PostgREST direto tende a ser mais rápido.
Se ele ficar abaixo de 500 ms, aumente o pico da rampa no prompt da Etapa 03 de 200 para 400 usuários.

## Antes de entrar na sala

- [ ] `systemctl is-active docker` responde `active`.
- [ ] `git status` limpo na `main` do remo-api e nenhum contêiner do laboratório rodando (`docker ps`).
- [ ] Terminal aberto em `~/remo-api`, com fonte grande para projeção (no Terminal do Mint, `Ctrl+Shift++` aumenta
      a fonte; pelo menos 18 pt).
- [ ] Claude Code aberto em `~/remo-api`, em modo que pede confirmação antes de editar.
- [ ] Deck da aula aberto no navegador:
      `https://afonsolelis.github.io/aulas/pages/module-8-eng-software/slides/slide-lesson-2.html`.
- [ ] Material aberto em outra aba, como reserva para copiar os prompts.
- [ ] Gerenciamento de energia sem suspender a tela durante a aula (Menu → Gerenciamento de energia).

## Se algo falhar durante a aula

- **O agente demora ou trava:** os prompts estão completos no material. Siga a teoria e volte ao artefato depois.
  Em último caso, mostre os números de referência da tabela acima.
- **`permission denied` ao falar com o Docker:** a sessão ainda não recarregou o grupo `docker`. Rode `newgrp docker`
  no terminal da aula ou use `sudo` só naquele comando.
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
