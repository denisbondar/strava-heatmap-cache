#!/usr/bin/env bash
set -Eeo pipefail

_is_sourced() {
  # https://unix.stackexchange.com/a/215279
  [ "${#FUNCNAME[@]}" -ge 2 ] &&
    [ "${FUNCNAME[0]}" = '_is_sourced' ] &&
    [ "${FUNCNAME[1]}" = 'source' ]
}

_main() {
  if [ "$1" = 'build' ] || [ "$1" = 'warmup' ]; then
    exec python /app/heatmap/warmup.py
  fi

  exec "$@"
}

if ! _is_sourced; then
  _main "$@"
fi
