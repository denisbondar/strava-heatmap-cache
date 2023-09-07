FROM python:3.11-slim-bullseye as staging-build

WORKDIR /app

RUN set -eux; \
    apt-get update; \
    apt-get full-upgrade -y; \
    pip install --no-cache-dir --upgrade pip wheel; \
    rm -rf /var/lib/apt/lists/*; \
    python -m venv /app/venv

ENV PATH="/app/venv/bin:$PATH"

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt



FROM python:3.11-slim-bullseye as staging-deploy

ENV PYTHONUNBUFFERED True
ENV PATH="/app/venv/bin:$PATH"
ENV CACHE_DIR="/app/cache"

RUN mkdir -p /app/cache

COPY ./docker/rootfs /
COPY --from=staging-build /app/venv /app/venv
COPY heatmap /app/heatmap

RUN chmod +x /usr/bin/docker-entrypoint.sh

WORKDIR /app
VOLUME /app/cache
VOLUME /var/run/strava.sock

EXPOSE 8080

ENTRYPOINT ["/usr/bin/docker-entrypoint.sh"]

CMD ["python", "-m", "heatmap"]
