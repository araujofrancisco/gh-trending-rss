FROM python:3.12-slim

RUN apt-get update \
  && apt-get install -y --no-install-recommends ca-certificates \
  && rm -rf /var/lib/apt/lists/*

RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
  && rm -rf /root/.cache

COPY generate_rss.py .
RUN chown -R appuser:appuser /app

USER appuser

ENTRYPOINT ["python", "/app/generate_rss.py"]
