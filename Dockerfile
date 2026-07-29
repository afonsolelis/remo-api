FROM docker.io/library/python:3.12-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

# libgomp1: exigido pelo XGBoost; tzdata: fuso America/Belem via TZ
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
# índice CPU do PyTorch primeiro (evita baixar a build CUDA de ~2 GB)
RUN pip install -r requirements.txt \
    --index-url https://download.pytorch.org/whl/cpu \
    --extra-index-url https://pypi.org/simple

COPY src/ src/
COPY scripts/ scripts/
COPY app.py .
COPY .streamlit/ .streamlit/

EXPOSE 8501
CMD ["sh", "scripts/start.sh"]
