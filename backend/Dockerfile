FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential gosu libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system gradebook \
    && useradd --system --gid gradebook --home-dir /app --shell /usr/sbin/nologin gradebook \
    && mkdir -p /data/storage /data/backups \
    && chown -R gradebook:gradebook /data

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN sed -i 's/\r$//' /docker-entrypoint.sh \
    && chmod +x /docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/docker-entrypoint.sh"]
