# 🦁 Remo no Brasileirão — simulador com IA

Dashboard local (Streamlit) que acompanha o **Clube do Remo** no Brasileirão
Série A usando a API pública do Cartola FC (`https://api.cartola.globo.com`),
com **simulações Monte Carlo** do restante da temporada e previsão de jogos por
modelos leves (XGBoost com Elo, Poisson, Poisson temporal e Ensemble — todos
treinam em segundos).

## O que tem

- **🦁 Remo** — posição, pontos, forma recente, próximo jogo e probabilidades
  de título / Libertadores (G4) / rebaixamento (Z4) nas simulações.
- **📊 Classificação** — tabela completa calculada dos resultados oficiais,
  com escudos e forma recente.
- **🏆 Copa do Brasil** — chaveamento completo via API de tabela do ge
  (mesmos IDs de clube do Cartola), campanha do Remo e **simulação Monte
  Carlo do mata-mata**: ida/volta por Poisson, pênaltis, probabilidade de
  cada clube avançar fase a fase até o título. Guardado no banco (`copa`).
- **📋 Partidas & elenco** — pontuação e scout do Cartola de cada jogador em
  cada partida (gols, assistências, desarmes, defesas, cartões…) e o plantel
  de qualquer clube com estatísticas da temporada (preço, média, status).
  Guardado no banco: coleções `atletas`, `atletas_daily` e `pontuados`.
- **🔮 Simulações** — milhares de temporadas simuladas: distribuição de posição
  final de cada clube (heatmap), probabilidades e pontos esperados.
- **📅 Próximos jogos** — probabilidades 1X2 do modelo para cada rodada futura.
- **🧠 Modelo** — **backtest comparativo** entre os modelos (XGBoost,
  Poisson, Poisson temporal e Ensemble): acurácia, log loss e RPS nas
  últimas rodadas.

## Rodando com Docker (recomendado)

```bash
docker compose up -d --build   # ou: podman compose up -d --build
```

Sobe três serviços:

| Serviço   | Papel |
|-----------|-------|
| `mongo`   | MongoDB local (volume `mongo_data`): snapshot atual em `season` e um snapshot por dia em `season_daily` |
| `app`     | o dashboard em `http://localhost:8501` |
| `updater` | atualiza as APIs e publica 20.000 simulações **2× ao dia (08h e 22h**, fuso `America/Belem`) |

Horários e fuso são configuráveis no `docker-compose.yml` (`UPDATE_TIMES`,
`TZ`). O cache do histórico 2012+ fica no bind mount `./data`
(compartilhado entre `app` e `updater`).

Comandos úteis:

```bash
docker compose logs -f updater      # acompanhar as atualizações agendadas
docker compose exec mongo mongosh remo --eval \
  'db.season_daily.find({}, {fetched_at: 1}).sort({_id: -1})'   # snapshots no banco
docker compose down                 # parar (dados persistem no volume)
```

## Deploy no Railway

O serviço roda em contêiner único (mesmo Dockerfile do local): o agendador
sobe junto do dashboard via `ENABLE_UPDATER=1` e atualiza os dados 2× ao dia.
Variáveis do serviço:

```
MONGO_URL=${{MongoDB.MONGO_URL}}   # referência ao serviço MongoDB do projeto
TZ=America/Belem
ENABLE_UPDATER=1
SIMULATION_MODEL=ensemble
SIMULATION_COUNT=20000
BACKTEST_ROUNDS=6
```

O deploy é automático a cada push na `main` (repo conectado); `railway up`
também funciona para testes sem commit.

## Rodando sem Docker

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run app.py
```

Sem a variável `MONGO_URL`, o armazenamento cai para JSON local
(`data/season.json` + `data/daily/`) e o app refaz o download sozinho quando
os dados têm mais de 24 h. Para atualizar manualmente ou via cron:

```bash
.venv/bin/python scripts/update_data.py
```

O dashboard público é somente leitura. Dados, modelos, backtest e simulações
são atualizados pelo agendador às 08h e 22h; visitas ao site não chamam APIs
externas nem executam modelos. O último snapshot válido permanece disponível
se uma atualização falhar.

## Como funciona a previsão

1. **Dados de treino** — além da temporada atual (API do Cartola), o XGBoost
   treina com o histórico do Brasileirão **2012+** (~5.300 jogos, de
   football-data.co.uk, cache em `data/historical/`), com peso decrescente por
   ano de distância.
2. **Features** — indicadores de forma das duas equipes antes de cada jogo
   (pontos por jogo, média de gols nos últimos 5, desempenho por mando) e o
   **rating Elo**, atualizado jogo a jogo.
3. **Modelos** — XGBoost, Poisson por médias, Poisson temporal (recentes pesam
   mais) e Ensemble (média de todos) — todos regressão de Poisson: preveem
   taxas de gols λ e treinam em segundos.
4. **Monte Carlo** — cada jogo restante é sorteado de `Poisson(λ)` milhares de
   vezes; a tabela final é recalculada por cenário (desempate: pontos,
   vitórias, saldo, gols pró) → probabilidades de título, G4, G6 e Z4.
5. **Backtest** (página Modelo) — replay das últimas rodadas com treino só no
   passado, medindo acurácia, log loss e RPS de cada modelo.

## Estrutura

```
app.py                  # dashboard Streamlit
pages/                  # páginas e rotas da navegação superior
Dockerfile              # imagem única do app/updater (python 3.12, leve)
docker-compose.yml      # mongo + app + updater (2x/dia)
scripts/scheduler.py    # agendador do updater (08h e 22h)
scripts/update_data.py  # atualização manual/cron dos dados
src/cartola.py          # cliente da API do Cartola
src/copa.py             # Copa do Brasil (API do ge) + simulação do mata-mata
src/store.py            # persistência: MongoDB (Docker) ou JSON local
src/history.py          # histórico 2012+ (football-data.co.uk)
src/standings.py        # classificação e forma
src/features.py         # features tabulares de forma + rating Elo
src/model.py            # XGBoost, Poisson, Poisson temporal, ensemble
src/evaluate.py         # backtest walk-forward (RPS, log loss)
src/simulate.py         # Monte Carlo vetorizado (numpy)
src/projections.py      # geração offline do snapshot público
src/viz.py              # paleta e estilo dos gráficos
src/dashboard.py        # renderização compartilhada das páginas
src/page_runner.py      # executor comum usado pelas rotas
```

> ⚠️ Projeto recreativo: com uma temporada só de dados, as previsões são
> estimativas grosseiras — não use para apostas.
