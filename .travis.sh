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
    if [  $(python -c "import sys; print(sys.version_info[1])") -gt 5 ]; then
        pip install ".[dev]"
        isort --check-only --recursive --diff .
        black --check .
        flake8 .
        check-manifest .
    fi
fi

if [ "$1" == "docs" ]; then
    cd ..
    pip install -r docs/requirements.txt  # We need to go the roundabout way to mirror rtd
    cd docs/
    make html
    make linkcheck
    npm install -g write-good
    write-good **/*.rst --no-passive --no-adverb || true
fi
