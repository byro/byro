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
    # BSD sed needs a suffix for -i, GNU doesn't care
    sed -i.bak "s/MAIL_HOST/$IP/" "$CONFIG"
    rm -f "$CONFIG.bak"
}

manage() {
    "${COMPOSE[@]}" run manage "$@"
}

start_db() {
    echo "Starting database in background..."
    "${COMPOSE[@]}" up -d db
}

start_migrate() {
    echo "Performing migrations..."
    manage migrate
    touch "$COMPLETE_MIGRATE"
}

start_rebuild() {
    echo "Running rebuild..."
    manage compress
    manage collectstatic --noinput
    touch "$COMPLETE_REBUILD"
}

start_superuser () {
    cat <<EOF
Creating superuser...
===
You will be prompted for an email address, and a password.
Please choose your password to be secure and do not forget it.
===
EOF
    manage createsuperuser --username admin
    
    touch "$COMPLETE_SUPERUSER"
    start
}

start() {
    "${COMPOSE[@]}" up -d db gunicorn nginx
    
    cat <<EOF
All done!
Your software should now be running at this URL:
http://127.0.0.1:8345/

If you want to expose that to the world, make sure to disable "Debug" in the config and put a TLS certificate on it!

If you want to do other tasks like install plugins, run '$0 help' for more info
EOF
}

plugin() {
    repo="$1"
    name="$(basename "$repo" .git)"
    path="../src/local/${name}"
    if [[ ! -d "$path" ]]; then
        git clone "$repo" "../src/local/${name}"
    else
        pushd "$path" >/dev/null
        git pull
        popd >/dev/null
    fi
    "${COMPOSE[@]}" build
    
    start_migrate
    start_rebuild
    
    "${COMPOSE[@]}" run --user root manage makemessages -l de -i build -i dist -i "*egg*"
    "${COMPOSE[@]}" up -d gunicorn
}

arg="${1:-}"
case "$arg" in
stop)
    stop
    ;;
logs)
    "${COMPOSE[@]}" logs --tail=20 -f
    ;;
plugin)
    repo="$2"
    plugin "$repo"
    ;;
fints)
    plugin https://github.com/henryk/byro-fints
    ;;
manage)
    shift
    manage "$@"
    ;;
db)
    docker exec -it byro_db_1 psql -U byro
    ;;
help|--help|-h|h)
    cat <<EOF
Usage:
  General:
    $0          Run setup
    $0 stop     Stop running services
    $0 logs     Tail the logs

  Plugins:
    $0 plugin <git-url>
                install a plugin from a git url
    $0 fints    install the byron-fints plugin

  Plumbing:
    $0 manage [args]
                directly run "python -m byro [args]"
    $0 db       get a psql shell to the database
EOF
    ;;
"")
    if [[ ! -f "$CONFIG" ]]; then
        create_config
    elif [[ ! -f "$COMPLETE_MIGRATE" ]]; then
        start_db

        start_migrate
        start_rebuild
        start_superuser

    elif [[ ! -f "$COMPLETE_REBUILD" ]]; then
        start_db
        
        start_rebuild
        start_superuser

    elif [[ ! -f "$COMPLETE_SUPERUSER" ]]; then
        start_db
        
        start_superuser

    else
        start
    fi
    ;;
esac
