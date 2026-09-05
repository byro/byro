#!/usr/bin/env bash
# Generate or verify deploy/SHA256SUMS, the checksum list that install.sh and
# byroctl use to verify the deployment artefacts of a release tag.
#
#   .github/scripts/deploy-checksums.sh --write   regenerate after changing deploy/
#   .github/scripts/deploy-checksums.sh --check   fail if the list is out of date (CI)
#
# The list is an explicit allowlist of the files that install.sh and byroctl
# download from a release tag. Files that only go into the image (Dockerfile,
# entrypoint.sh, healthcheck.py) are deliberately not listed: nobody verifies
# them at runtime, and Dependabot's base image bumps must not invalidate the
# list. Tests, caches and the list itself are not part of it either.
set -euo pipefail

FILES=(
    byroctl
    install.sh
    docker-compose.yml
    compose/postgres.yml
    compose/caddy.yml
    Caddyfile
    byro.conf.example
    release.env
)

cd "$(dirname "${BASH_SOURCE[0]}")/../../deploy"

checksums() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "${FILES[@]}"
    else
        shasum -a 256 "${FILES[@]}"
    fi
}

case "${1:-}" in
    --write)
        checksums >SHA256SUMS
        echo "wrote deploy/SHA256SUMS (${#FILES[@]} files)" ;;
    --check)
        [[ -f SHA256SUMS ]] || { echo "deploy/SHA256SUMS is missing; run $0 --write" >&2; exit 1; }
        if diff -u SHA256SUMS <(checksums) >&2; then
            echo "deploy/SHA256SUMS is current"
        else
            echo "deploy/SHA256SUMS is out of date; run $0 --write" >&2
            exit 1
        fi ;;
    *)
        echo "usage: $0 --write | --check" >&2
        exit 64 ;;
esac
