# VERIQ, CPU only. Build:  docker build -t veriq .          (voice extras: --build-arg VOICE=1)
# Run:   docker compose up   (see docker-compose.yml and DEPLOY.md). NOT built or run by Claude (no Docker in its sandbox).
# Base pinned by version tag (python 3.11.9, Debian bookworm). For a pilot, also pin by digest: docker pull, then
# replace the tag with python:3.11.9-slim-bookworm@sha256:<digest shown by `docker images --digests`>.
FROM python:3.11.9-slim-bookworm

ARG VOICE=0
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    VERIQ_DATA_DIR=/data VERIQ_OFFLINE=1 VERIQ_AASIST_REPO=/app/external/aasist

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt requirements-voice.txt ./
RUN pip install -r requirements.txt \
    && if [ "$VOICE" = "1" ]; then pip install --index-url https://download.pytorch.org/whl/cpu torch torchaudio \
       && pip install soundfile scikit-learn; fi

COPY . .
RUN useradd --create-home --uid 10001 veriq && mkdir -p /data && chown -R veriq:veriq /data /app
USER veriq

EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=4).read().strip()==b'ok' else 1)"

CMD ["python", "-m", "streamlit", "run", "app/streamlit_app.py", "--server.headless", "true", \
     "--server.address", "0.0.0.0", "--server.port", "8501", "--browser.gatherUsageStats", "false", \
     "--client.toolbarMode", "minimal"]
