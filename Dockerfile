FROM python:3.11-slim-bullseye as base

COPY requirements.txt /

RUN pip install -r requirements.txt



FROM python:3.11-slim-bullseye

RUN mkdir -p /app/cache

WORKDIR /app

COPY ./docker/rootfs /
COPY --from=base /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY web.py main.py ./

RUN chmod +x /usr/bin/docker-entrypoint.sh

VOLUME /app/cache

VOLUME /var/run/strava.sock

EXPOSE 8080

ENTRYPOINT ["/usr/bin/docker-entrypoint.sh"]

CMD ["python3", "web.py"]
