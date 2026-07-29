FROM docker.io/library/python:3.12-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

# libgomp1: exigido pelo XGBoost; tzdata: fuso America/Belem via TZ
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ src/
COPY scripts/ scripts/
COPY app.py .
COPY .streamlit/ .streamlit/

EXPOSE 8501
CMD ["sh", "scripts/start.sh"]
