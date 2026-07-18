# QA Sentinel — Streamlit (use on Render / Railway / any Docker host)
# Vercel cannot run Streamlit (needs long-lived WebSocket server).

FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN bash scripts/setup_harness.sh || true

EXPOSE 8501
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

CMD streamlit run app.py --server.port=${PORT:-8501} --server.address=0.0.0.0
