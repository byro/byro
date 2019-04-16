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
    isort --check-only --recursive --diff .
    black -S --check --exclude "/(\.eggs|\.git|\.mypy_cache|\.nox|\.tox|\.venv|_build|build|static|static.dist|dist|migrations)/|urls.py" .
fi

if [ "$1" == "docs" ]; then
    cd ../docs
    pip install -r requirements.txt
    make html
    make linkcheck
    npm install -g write-good
    write-good **/*.rst --no-passive --no-adverb || true
fi
