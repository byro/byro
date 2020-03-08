#!/bin/bash
set -euo pipefail

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

mkdirs() {
    mkdir -p "$DATA/data"
    mkdir -p "$DATA/static.dist"
}

DATA="$DIR/../../byro-data"
mkdirs
DATA="$(cd "$DATA" && pwd)"

CONFIG="$DATA/byro.cfg"

COMPLETE_MIGRATE="$DATA/.completed_migrate"
COMPLETE_REBUILD="$DATA/.completed_rebuild"
COMPLETE_SUPERUSER="$DATA/.completed_superuser"
COMPOSE=(docker-compose -p byro)

stop() {
    "${COMPOSE[@]}" down -v
}

create_config() {
    stop

    cat <<EOF
=== Welcome ===
This will setup a byro production deployment using docker.

Your data will end up in $DATA.
Make sure to setup backups for everything in that folder.

Firstly, we will create a configuration.
An example config will be created at $CONFIG.

Please, edit that config file to your likings and re-run this script to continue.
If you want to start over, simply delete the data folder, and re-run this script.
EOF
    cp "$DIR/byro.example.cfg" "$CONFIG"
    
    start_db
    IP="$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.Gateway}}{{end}}' byro_db_1)"
    sed -i "s/MAIL_HOST/$IP/" "$CONFIG"
}

start_db() {
    echo "Starting database in background..."
    "${COMPOSE[@]}" up -d db
}

start_migrate() {
    echo "Performing migrations..."
    "${COMPOSE[@]}" run manage migrate
    touch "$COMPLETE_MIGRATE"

    start_rebuild
}

start_rebuild() {
     echo "Running rebuild..."
    "${COMPOSE[@]}" run manage collectstatic
    touch "$COMPLETE_REBUILD"
    
    start_superuser
}

start_superuser () {
    cat <<EOF
Creating superuser...
===
You will be prompted for an email address, and a password.
Please choose your password to be secure and do not forget it.
===
EOF
    "${COMPOSE[@]}" run manage createsuperuser --username admin
    
    touch "$COMPLETE_SUPERUSER"
    start
}

start() {
    "${COMPOSE[@]}" up -d db gunicorn nginx
    
    cat <<EOF
All done!
Your software should now be running at this URL:
http://127.0.0.1:8345/

If you want to expose that to the world, make sure to disable "Debug" in the config and put an SSL certificate on it!
EOF
}


case "$*" in

stop)
    stop
    ;;
help|--help|-h|h)
    cat <<EOF
Usage:
    ./setup.sh          Run setup
    ./setup.sh stop     Stop running services
EOF
    ;;
"")
    if [[ ! -f "$CONFIG" ]]; then
        create_config
    elif [[ ! -f "$COMPLETE_MIGRATE" ]]; then
        start_db
        start_migrate
    elif [[ ! -f "$COMPLETE_REBUILD" ]]; then
        start_db
        start_rebuild
    elif [[ ! -f "$COMPLETE_SUPERUSER" ]]; then
        start_db
        start_superuser
    else
        start
    fi
    ;;
esac
