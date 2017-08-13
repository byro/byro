#!/bin/bash
set -e

echo "Running $1"

if [ "$1" == "tests" ]; then
    psql -c 'create database byro;' -U postgres
    cd src
    python manage.py check
    pytest --cov=byro tests
fi

if [ "$1" == "docs" ]; then
    cd docs
    make html
    make linkcheck
    npm install -g write-good
    write-good **/*.rst
fi
