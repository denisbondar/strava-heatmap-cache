#!/usr/bin/env bash

if [ -z "$1" ]; then
  echo "Use: $0 <version_number> [push]"
  exit
fi

docker build --pull --file=Dockerfile --tag denisbondar/strava-heatmap-cache:"$1" --tag denisbondar/strava-heatmap-cache:latest . \
  && if [ "$2" == 'push' ]; then
    echo "Push to Docker HUB"
    docker login \
      && docker push denisbondar/strava-heatmap-cache:"$1" \
      && docker push denisbondar/strava-heatmap-cache:latest;
    fi
