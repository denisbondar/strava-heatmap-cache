#!/usr/bin/env bash

set -e

autoflake --in-place --remove-all-unused-imports --recursive heatmap tests
isort .
black .
