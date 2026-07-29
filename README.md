# 🦁 Remo no Brasileirão — simulador com IA

Dashboard local (Streamlit) que acompanha o **Clube do Remo** no Brasileirão
Série A usando a API pública do Cartola FC (`https://api.cartola.globo.com`),
com **simulações Monte Carlo** do restante da temporada e previsão de jogos por
**LSTM (PyTorch)**.

## O que tem

- **🦁 Remo** — posição, pontos, forma recente, próximo jogo e probabilidades
  de título / Libertadores (G4) / rebaixamento (Z4) nas simulações.
- **📊 Classificação** — tabela completa calculada dos resultados oficiais,
  com escudos e forma recente.
- **📋 Partidas & elenco** — pontuação e scout do Cartola de cada jogador em
  cada partida (gols, assistências, desarmes, defesas, cartões…) e o plantel
  de qualquer clube com estatísticas da temporada (preço, média, status).
  Guardado no banco: coleções `atletas`, `atletas_daily` e `pontuados`.
- **🔮 Simulações** — milhares de temporadas simuladas: distribuição de posição
  final de cada clube (heatmap), probabilidades e pontos esperados.
- **📅 Próximos jogos** — probabilidades 1X2 do modelo para cada rodada futura.
- **🧠 Modelo** — **backtest comparativo** entre os modelos (LSTM, GRU,
  XGBoost, Poisson, Poisson temporal e Ensemble — acurácia, log loss e RPS
  nas últimas rodadas), métricas e curva de perda das redes, retreino em
  1 clique e **histórico de treinamentos** (erro e acurácia a cada dia).

## Rodando com Docker (recomendado)

```bash
docker compose up -d --build   # ou: podman compose up -d --build
```

Sobe três serviços:

| Serviço   | Papel |
|-----------|-------|
| `mongo`   | MongoDB local (volume `mongo_data`): snapshot atual em `season` e um snapshot por dia em `season_daily` |
| `app`     | o dashboard em `http://localhost:8501` |
| `updater` | baixa da API do Cartola e retreina as redes **2× ao dia (08h e 22h**, fuso `America/Belem`) |

Horários e fuso são configuráveis no `docker-compose.yml` (`UPDATE_TIMES`,
`TZ`). Os checkpoints dos modelos e o cache do histórico 2012+ ficam nos bind
mounts `./models` e `./data` (compartilhados entre `app` e `updater`).

Comandos úteis:

```bash
docker compose logs -f updater      # acompanhar as atualizações agendadas
docker compose exec mongo mongosh remo --eval \
  'db.season_daily.find({}, {fetched_at: 1}).sort({_id: -1})'   # snapshots no banco
docker compose down                 # parar (dados persistem no volume)
```

## Deploy no Railway

O serviço roda em contêiner único e em **modo leve, sem PyTorch**
(`Dockerfile.railway`): o app detecta a ausência do torch e usa XGBoost,
Poisson, Poisson temporal e o Ensemble — treino de segundos, imagem ~3×
menor. As redes LSTM/GRU ficam para o modo local completo. O agendador roda
junto do dashboard (`ENABLE_UPDATER=1`) e atualiza os dados 2× ao dia.

Variáveis do serviço:

```
MONGO_URL=${{MongoDB.MONGO_URL}}   # referência ao serviço MongoDB do projeto
TZ=America/Belem
ENABLE_UPDATER=1
RAILWAY_DOCKERFILE_PATH=Dockerfile.railway
```

Um volume montado em `/app/models` persiste artefatos entre deploys. O deploy
é automático a cada push na `main` (repo conectado); `railway up` também
funciona para testes sem commit.

## Rodando sem Docker

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt \
  --index-url https://download.pytorch.org/whl/cpu \
  --extra-index-url https://pypi.org/simple
.venv/bin/streamlit run app.py
```

Sem a variável `MONGO_URL`, o armazenamento cai para JSON local
(`data/season.json` + `data/daily/`) e o app refaz o download sozinho quando
os dados têm mais de 24 h. Para atualizar/treinar manualmente ou via cron:

```bash
.venv/bin/python scripts/update_data.py --train
```

Também há o botão **“🔄 Atualizar dados agora”** na barra lateral (nos dois
modos). Artefatos de cada treino:

```
models/lstm.pt / gru.pt                  # modelos atuais
models/daily/{lstm,gru}-AAAA-MM-DD.pt    # "pickle do dia" — um checkpoint por data
models/history.jsonl                     # métricas de cada treino (alimenta o dashboard)
```

## Como funciona a previsão

1. **Dados de treino** — além da temporada atual (API do Cartola), as redes e o
   XGBoost treinam com o histórico do Brasileirão **2012+** (~5.300 jogos, de
   football-data.co.uk, cache em `data/historical/`), com peso decrescente por
   ano de distância.
2. **Features** — sequência dos últimos 6 jogos de cada equipe (gols pró/contra,
   pontos, mando, força do adversário e **rating Elo**, atualizado jogo a jogo);
   para o XGBoost, indicadores tabulares de forma + Elo.
3. **Modelos** — LSTM, GRU, XGBoost (todos regressão de Poisson: preveem taxas
   de gols λ), Poisson por médias, Poisson temporal (recentes pesam mais) e
   Ensemble (média de todos).
4. **Monte Carlo** — cada jogo restante é sorteado de `Poisson(λ)` milhares de
   vezes; a tabela final é recalculada por cenário (desempate: pontos,
   vitórias, saldo, gols pró) → probabilidades de título, G4, G6 e Z4.
5. **Backtest** (aba Modelo) — replay das últimas rodadas com treino só no
   passado, medindo acurácia, log loss e RPS de cada modelo.

## Estrutura

```
app.py                  # dashboard Streamlit
Dockerfile              # imagem do app/updater (python 3.12 + torch CPU)
docker-compose.yml      # mongo + app + updater (2x/dia)
scripts/scheduler.py    # agendador do updater (08h e 22h)
scripts/update_data.py  # atualização manual/cron + retreino
src/cartola.py          # cliente da API do Cartola
src/store.py            # persistência: MongoDB (Docker) ou JSON local
src/history.py          # histórico 2012+ (football-data.co.uk)
src/standings.py        # classificação e forma
src/features.py         # sequências, tabulares e rating Elo
src/model.py            # LSTM/GRU, XGBoost, Poisson, ensemble
src/evaluate.py         # backtest walk-forward (RPS, log loss)
src/simulate.py         # Monte Carlo vetorizado (numpy)
src/viz.py              # paleta e estilo dos gráficos
```

> ⚠️ Projeto recreativo: com uma temporada só de dados, as previsões são
> estimativas grosseiras — não use para apostas.
