FROM python:3.8-alpine as base

COPY requirements.txt /

RUN apk update \
    && apk add --no-cache --virtual \
        .build-deps \
        gcc \
        musl-dev \
        curl \
        linux-headers

RUN pip install -r requirements.txt

################################################################################

FROM python:3.8-alpine

RUN mkdir -p /app/cache
WORKDIR /app
COPY --from=base /usr/local/lib/python3.8/site-packages /usr/local/lib/python3.8/site-packages
COPY ./*.py /app/

VOLUME /app/cache
VOLUME /var/run/strava.sock
EXPOSE 8080

CMD ["python3", "web.py"]
