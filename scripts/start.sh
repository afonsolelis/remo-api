#!/bin/sh
# Entrypoint do contêiner.
# Em deploys de serviço único (ex.: Railway), ENABLE_UPDATER=1 sobe o
# agendador de atualizações junto com o dashboard. No docker-compose local
# o updater é um serviço separado e essa variável fica desligada.

# Migração única do MongoDB para JSON (só age com MONGO_MIGRATION_URL).
python scripts/migrate_mongo.py

if [ "$ENABLE_UPDATER" = "1" ]; then
    python scripts/scheduler.py &
fi
exec streamlit run app.py --server.headless true --server.address 0.0.0.0 \
    --server.port "${PORT:-8501}"
