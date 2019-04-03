#!/bin/bash
set -e

echo "Running $1"

if [ "$1" == "tests" ]; then
    psql -c 'create database byro;' -U postgres
    python -m byro check
    pytest --cov=byro tests
    codecov
fi

if [ "$1" == "style" ]; then
    pylama .
    isort --check-only --recursive --diff .
fi

if [ "$1" == "docs" ]; then
    pip install -r src/requirements/documentation.txt
    cd ../docs
    make html
    make linkcheck
    npm install -g write-good
    write-good **/*.rst --no-passive --no-adverb || true
fi
