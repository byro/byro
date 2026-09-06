#!/usr/bin/env bats
# byroctl plugin list|add|remove|update|rebuild against the docker/curl shims,
# on top of an installation created from the local deploy/ directory. The
# catalog is a test catalog; GitHub and PyPI answer from $SHIM_HTTP.

load helpers/common

constants() {
    SHA_A=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
    SHA_B=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
    SHA_C=cccccccccccccccccccccccccccccccccccccccc
}

# pypi_release PACKAGE VERSION / github_release OWNER/REPO TAG SHA: fixtures
pypi_release() {
    mkdir -p "$SHIM_HTTP/pypi.org/pypi/$1"
    printf '{"info": {"name": "%s", "summary": "x", "version": "%s"}, "releases": {"%s": []}, "urls": []}\n' "$1" "$2" "$2" \
        >"$SHIM_HTTP/pypi.org/pypi/$1/json"
}
github_release() {
    mkdir -p "$SHIM_HTTP/api.github.com/repos/$1/releases" "$SHIM_HTTP/api.github.com/repos/$1/commits"
    printf '{\n  "url": "https://api.github.com/repos/%s/releases/1",\n  "tag_name": "%s",\n  "name": "Release %s",\n  "prerelease": false\n}\n' "$1" "$2" "$2" \
        >"$SHIM_HTTP/api.github.com/repos/$1/releases/latest"
    printf '%s' "$3" >"$SHIM_HTTP/api.github.com/repos/$1/commits/$2"
}

test_catalog() {
    cat >"$BYRO_ROOT/plugin-catalog.conf" <<'EOF'
[testplug]
name=Test plugin
description=A PyPI test plugin.
package=byro-testplug
source=pypi
repo=https://pypi.org/project/byro-testplug/

[gitplug]
name=Git plugin
description=A GitHub test plugin.
package=byro-gitplug
source=github
repo=https://github.com/byro/gitplug

[norelease]
name=No release yet
description=A GitHub repository without releases.
package=byro-norelease
source=github
repo=https://github.com/byro/norelease

[branchplug]
name=Branch as release
description=A release named after a branch.
package=byro-branchplug
source=github
repo=https://github.com/byro/branchplug
EOF
}

setup() {
    constants
    load_byroctl
    make_root
    use_shims
    export BYROCTL_SOURCE_DIR="$DEPLOY_DIR"
    export SHIM_TAGS="ghcr.io/byro/byro:v2026.3.0 ghcr.io/byro/byro@sha256:1111111111111111111111111111111111111111111111111111111111111111"
    export SHIM_LOCAL_IMAGES="ghcr.io/byro/byro:v2026.3.0"
    export SHIM_DIGESTS="ghcr.io/byro/byro:v2026.3.0 ghcr.io/byro/byro@sha256:1111111111111111111111111111111111111111111111111111111111111111"
    export BYROCTL_ADMIN_PASSWORD="Admin-Passw0rd"
    export BYROCTL_WEB_HEALTH_TIMEOUT=2
    run byroctl --root "$BYRO_ROOT" install --non-interactive --version v2026.3.0 \
        --admin-user admin --admin-email admin@example.org \
        --set BYRO_SITE_URL=https://byro.example.org --set BYROCTL_PROXY=none --set BYRO_DEPLOY_PORT=18995
    [ "$status" -eq 0 ]
    printf 'the-secret-key\n' >"$BYRO_ROOT/data/.secret"
    test_catalog
    pypi_release byro-testplug 1.0.0
    github_release byro/gitplug v1.2.0 "$SHA_A"
    github_release byro/branchplug main "$SHA_A"
    : >"$SHIM_LOG"
}

plugin() { run byroctl --root "$BYRO_ROOT" plugin "$@"; }
docker_seq() { grep -oE "$1" "$SHIM_LOG" | tr '\n' '|'; }
PHASES='docker (buildx version|compose build( --no-cache)? web|compose run --rm -T manage check|compose exec -T db pg_dump|compose run --rm -T manage migrate --noinput|compose up -d$)'
GITPLUG_LINE() { printf 'byro-gitplug @ git+https://github.com/byro/gitplug.git@%s  # byroctl:catalog=gitplug version=%s' "$1" "$2"; }

@test "add resolves a PyPI catalog entry, pins it, enables the add-on and runs both phases" {
    before_conf="$(cat "$CONF_FILE")"
    plugin add testplug
    [ "$status" -eq 0 ]
    grep -qxF 'byro-testplug==1.0.0  # byroctl:catalog=testplug version=1.0.0' "$PLUGINS_FILE"
    [ "$(conf_get COMPOSE_FILE)" = "docker-compose.yml:compose/postgres.yml:compose/plugins.yml" ]
    [ "$(docker_seq "$PHASES")" = "docker buildx version|docker compose build web|docker compose run --rm -T manage check|docker compose exec -T db pg_dump|docker compose run --rm -T manage migrate --noinput|docker compose up -d|" ]
    grep -q "curl .*https://pypi.org/pypi/byro-testplug/json" "$SHIM_LOG"
    [[ "$output" == *"plugins now: testplug 1.0.0"* ]]
    # the safeguard carries the state from before the change
    dir="$(ls -d "$BYRO_ROOT"/backups/pre-plugin-v2026.3.0-*)"
    [ "$(cat "$dir/db.dump")" = "PGDMP-shim" ]
    [ "$(cat "$dir/.secret")" = "the-secret-key" ]
    [ "$(cat "$dir/byro.conf")" = "$before_conf" ]
    refute grep -q "byro-testplug" "$dir/plugins.txt"
    grep -qx 'BYROCTL_KIND=pre-plugin' "$dir/META"
    grep -qx 'BYROCTL_PREVIOUS_PLUGINS=plugins.txt' "$dir/META"
    [ -z "$(ls -d "$BYRO_ROOT"/.byroctl/plugin-snapshot.* 2>/dev/null)" ]
    [ ! -d "$BYRO_ROOT/.byroctl/lock" ]
}

@test "add resolves a GitHub catalog entry to the commit of the current release" {
    plugin add gitplug
    [ "$status" -eq 0 ]
    grep -qxF "$(GITPLUG_LINE "$SHA_A" v1.2.0)" "$PLUGINS_FILE"
    grep -q "curl .*-H Accept: application/vnd.github+json .*repos/byro/gitplug/releases/latest" "$SHIM_LOG"
    grep -q "curl .*-H Accept: application/vnd.github.sha .*repos/byro/gitplug/commits/v1.2.0" "$SHIM_LOG"
    [[ "$output" == *"plugins now: gitplug v1.2.0"* ]]
}

@test "GitHub entries without a release, with a branch as release or with a bad commit are refused before any change" {
    before="$(cat "$PLUGINS_FILE")"
    plugin add norelease
    [ "$status" -eq 1 ]
    [[ "$output" == *"has no GitHub release yet"* ]]
    [[ "$output" == *"git+https://github.com/byro/norelease.git@<ref>"* ]]
    plugin add branchplug
    [ "$status" -eq 1 ]
    [[ "$output" == *"a branch name, not a release tag"* ]]
    printf 'not-a-sha' >"$SHIM_HTTP/api.github.com/repos/byro/gitplug/commits/v1.2.0"
    plugin add gitplug
    [ "$status" -eq 1 ]
    [[ "$output" == *"unexpected commit id"* ]]
    [ "$(cat "$PLUGINS_FILE")" = "$before" ]
    refute grep -q "compose build" "$SHIM_LOG"
    [ "$(conf_get COMPOSE_FILE)" = "docker-compose.yml:compose/postgres.yml" ]
}

@test "explicit requirements are accepted, unpinned ones with a warning, bare names outside the catalog not at all" {
    plugin add 'byro-foo>=1'
    [ "$status" -eq 0 ]
    [[ "$output" == *"not pinned"* ]]
    grep -qxF 'byro-foo>=1' "$PLUGINS_FILE"
    : >"$SHIM_LOG"
    plugin add 'byro-bar==1.0' './local-plugin'
    [ "$status" -eq 0 ]
    [[ "$output" != *"not pinned"* ]]
    grep -qxF 'byro-bar==1.0' "$PLUGINS_FILE"
    grep -qxF './local-plugin' "$PLUGINS_FILE"
    plugin add byro-baz
    [ "$status" -eq 64 ]
    [[ "$output" == *"not in the plugin catalog"* ]]
    [[ "$output" == *"byro-baz==1.2.3"* ]]
}

@test "requirements with pip options, comments, variables or nothing at all are rejected" {
    before="$(cat "$PLUGINS_FILE")"
    local bad
    for bad in 'byro-x --hash=sha256:00' 'a#b' 'a $B' 'a;b' ''; do
        plugin add "$bad"
        [ "$status" -eq 64 ]
        [[ "$output" == *"invalid plugin requirement"* ]]
    done
    # a pip option in option position is refused by the argument parser
    plugin add '--index-url=https://evil.example'
    [ "$status" -eq 64 ]
    [[ "$output" == *"never a pip option"* ]]
    [ "$(cat "$PLUGINS_FILE")" = "$before" ]
    refute grep -q "compose build" "$SHIM_LOG"
}

@test "an entry that is already listed is a no-op; the same project with another requirement is refused" {
    plugin add testplug
    [ "$status" -eq 0 ]
    : >"$SHIM_LOG"
    plugin add testplug
    [ "$status" -eq 0 ]
    [[ "$output" == *"already listed: testplug 1.0.0"* ]]
    refute grep -q "compose build" "$SHIM_LOG"
    plugin add 'byro-testplug==2.0.0'
    [ "$status" -eq 64 ]
    [[ "$output" == *"already listed with a different requirement"* ]]
    plugin add 'Byro_Testplug==2.0.0'
    [ "$status" -eq 64 ]
    [ "$(grep -c byro-testplug "$PLUGINS_FILE")" -eq 1 ]
}

@test "a failed build or check in phase 1 reverts everything and leaves the stack alone" {
    before="$(cat "$PLUGINS_FILE")"; before_conf="$(cat "$CONF_FILE")"
    export SHIM_FAIL="compose build"
    plugin add testplug
    [ "$status" -eq 1 ]
    [[ "$output" == *"nothing was changed"* ]]
    [ "$(cat "$PLUGINS_FILE")" = "$before" ]
    [ "$(cat "$CONF_FILE")" = "$before_conf" ]
    refute grep -qE "manage migrate|compose up|pg_dump" "$SHIM_LOG"
    [ -z "$(ls -A "$BYRO_ROOT/backups")" ]
    [ -z "$(ls -d "$BYRO_ROOT"/.byroctl/plugin-snapshot.* 2>/dev/null)" ]
    # with a plugin already installed, a failed check re-tags the previous image from the cache
    unset SHIM_FAIL
    plugin add testplug
    [ "$status" -eq 0 ]
    before="$(cat "$PLUGINS_FILE")"; before_conf="$(cat "$CONF_FILE")"
    : >"$SHIM_LOG"
    export SHIM_FAIL="manage check"
    plugin add 'byro-x==1.0'
    [ "$status" -eq 1 ]
    [ "$(cat "$PLUGINS_FILE")" = "$before" ]
    [ "$(cat "$CONF_FILE")" = "$before_conf" ]
    [ "$(grep -c "compose build web" "$SHIM_LOG")" -eq 2 ]
    refute grep -qE "manage migrate|compose up" "$SHIM_LOG"
    [[ "$output" == *"restoring the previous plugin image"* ]]
}

@test "a failed migration in phase 2 keeps the attempted state and prints the generic way back" {
    export SHIM_FAIL="manage migrate"
    plugin add testplug
    [ "$status" -eq 2 ]
    grep -q "byro-testplug==1.0.0" "$PLUGINS_FILE"
    [ "$(conf_get COMPOSE_FILE)" = "docker-compose.yml:compose/postgres.yml:compose/plugins.yml" ]
    [ "$(grep -c "compose build web" "$SHIM_LOG")" -eq 1 ]
    refute grep -q "compose up -d$" "$SHIM_LOG"
    [[ "$output" == *"Do not switch back"* ]]
    [[ "$output" == *"restore $BYRO_ROOT/backups/pre-plugin-v2026.3.0-"* ]]
    [[ "$output" == *"plugins/plugins.txt from there"* ]]
    [[ "$output" == *"2. byroctl plugin rebuild"* ]]
    [[ "$output" == *"3. byroctl start"* ]]
    [[ "$output" != *"plugin remove"* ]]
    dir="$(ls -d "$BYRO_ROOT"/backups/pre-plugin-v2026.3.0-*)"
    [ -f "$dir/plugins.txt" ]
    refute grep -q byro-testplug "$dir/plugins.txt"
    [ ! -d "$BYRO_ROOT/.byroctl/lock" ]
}

@test "an unhealthy web after the migration is reported without switching back" {
    export SHIM_HEALTH=unhealthy
    plugin add testplug --skip-safeguard
    [ "$status" -eq 3 ]
    [[ "$output" == *"the migration has run"* ]]
    [[ "$output" == *"Do not switch back"* ]]
    grep -q "byro-testplug==1.0.0" "$PLUGINS_FILE"
    grep -q "compose up -d$" "$SHIM_LOG"
}

@test "remove drops an entry, the last one disables the add-on; unknown entries are a usage error" {
    plugin add testplug 'byro-x==1.0'
    [ "$status" -eq 0 ]
    : >"$SHIM_LOG"
    plugin remove byro-x
    [ "$status" -eq 0 ]
    refute grep -q "byro-x" "$PLUGINS_FILE"
    grep -q "byro-testplug" "$PLUGINS_FILE"
    grep -q "compose build web" "$SHIM_LOG"
    : >"$SHIM_LOG"
    plugin remove testplug
    [ "$status" -eq 0 ]
    refute grep -q "byro-testplug" "$PLUGINS_FILE"
    [ "$(conf_get COMPOSE_FILE)" = "docker-compose.yml:compose/postgres.yml" ]
    refute grep -q "compose build" "$SHIM_LOG"
    grep -q "manage migrate" "$SHIM_LOG"
    grep -q "compose up -d$" "$SHIM_LOG"
    [[ "$output" == *"Database tables of removed plugins are kept"* ]]
    before="$(cat "$PLUGINS_FILE")"
    plugin remove nothere
    [ "$status" -eq 64 ]
    [[ "$output" == *"not listed"* ]]
    [ "$(cat "$PLUGINS_FILE")" = "$before" ]
}

@test "update moves catalog entries to their current release, --check only reports" {
    plugin add testplug gitplug 'byro-x==1.0'
    [ "$status" -eq 0 ]
    : >"$SHIM_LOG"
    plugin update --check
    [ "$status" -eq 3 ]
    [[ "$output" == *"at their current release"* ]]
    pypi_release byro-testplug 2.0.0
    github_release byro/gitplug v1.3.0 "$SHA_B"
    before="$(cat "$PLUGINS_FILE")"
    plugin update --check
    [ "$status" -eq 0 ]
    [[ "$output" == *"testplug: 1.0.0 -> 2.0.0"* ]]
    [[ "$output" == *"gitplug: v1.2.0 -> v1.3.0"* ]]
    [ "$(cat "$PLUGINS_FILE")" = "$before" ]
    refute grep -q "compose build" "$SHIM_LOG"
    plugin update
    [ "$status" -eq 0 ]
    grep -qxF 'byro-testplug==2.0.0  # byroctl:catalog=testplug version=2.0.0' "$PLUGINS_FILE"
    grep -qxF "$(GITPLUG_LINE "$SHA_B" v1.3.0)" "$PLUGINS_FILE"
    grep -qxF 'byro-x==1.0' "$PLUGINS_FILE"
    grep -q "compose build web" "$SHIM_LOG"
    dir="$(ls -dt "$BYRO_ROOT"/backups/pre-plugin-v2026.3.0-* | head -n1)"
    grep -q "byro-testplug==1.0.0" "$dir/plugins.txt"
    grep -qF "$SHA_A" "$dir/plugins.txt"
    # only the named entry
    pypi_release byro-testplug 3.0.0
    github_release byro/gitplug v1.4.0 "$SHA_C"
    plugin update testplug
    [ "$status" -eq 0 ]
    grep -q "byro-testplug==3.0.0" "$PLUGINS_FILE"
    grep -qF "$(GITPLUG_LINE "$SHA_B" v1.3.0)" "$PLUGINS_FILE"
}

@test "a release tag that moved to another commit stops the update fail-closed" {
    plugin add testplug gitplug
    [ "$status" -eq 0 ]
    before="$(cat "$PLUGINS_FILE")"
    : >"$SHIM_LOG"
    github_release byro/gitplug v1.2.0 "$SHA_C"
    plugin update
    [ "$status" -eq 1 ]
    [[ "$output" == *"release v1.2.0 now points to commit $SHA_C, the installed pin is $SHA_A"* ]]
    [[ "$output" == *"treated as immutable"* ]]
    [[ "$output" == *"publish a new release"* ]]
    [[ "$output" == *"nothing was changed"* ]]
    [ "$(cat "$PLUGINS_FILE")" = "$before" ]
    refute grep -qE "compose build|pg_dump|manage migrate|compose up" "$SHIM_LOG"
    # a sibling with a new release is not updated either
    pypi_release byro-testplug 2.0.0
    plugin update
    [ "$status" -eq 1 ]
    [ "$(cat "$PLUGINS_FILE")" = "$before" ]
    refute grep -q "compose build" "$SHIM_LOG"
    plugin update --check
    [ "$status" -eq 1 ]
    [ "$(cat "$PLUGINS_FILE")" = "$before" ]
}

@test "rebuild applies a hand-edited list; a phase 1 failure keeps the list and restores COMPOSE_FILE" {
    printf 'byro-hand==1.0\n' >>"$PLUGINS_FILE"
    edited="$(cat "$PLUGINS_FILE")"
    export SHIM_FAIL="compose build"
    plugin rebuild
    [ "$status" -eq 1 ]
    [[ "$output" == *"was kept as you edited it"* ]]
    [ "$(cat "$PLUGINS_FILE")" = "$edited" ]
    [ "$(conf_get COMPOSE_FILE)" = "docker-compose.yml:compose/postgres.yml" ]
    refute grep -qE "manage migrate|compose up|pg_dump" "$SHIM_LOG"
    unset SHIM_FAIL
    : >"$SHIM_LOG"
    plugin rebuild --no-cache
    [ "$status" -eq 0 ]
    [ "$(conf_get COMPOSE_FILE)" = "docker-compose.yml:compose/postgres.yml:compose/plugins.yml" ]
    grep -q "compose build --no-cache web" "$SHIM_LOG"
    # no plugin container or image existed before: the safeguard says so
    dir="$(ls -d "$BYRO_ROOT"/backups/pre-plugin-v2026.3.0-*)"
    [ ! -e "$dir/plugins.txt" ]
    grep -q "^BYROCTL_PREVIOUS_PLUGINS='none" "$dir/META"
    [[ "$output" == *"no previously applied plugin state"* ]]
    # with the add-on active a failed rebuild keeps COMPOSE_FILE and re-tags the old image
    : >"$SHIM_LOG"
    export SHIM_FAIL="manage check"
    plugin rebuild
    [ "$status" -eq 1 ]
    [ "$(conf_get COMPOSE_FILE)" = "docker-compose.yml:compose/postgres.yml:compose/plugins.yml" ]
    [ "$(cat "$PLUGINS_FILE")" = "$edited" ]
    [ "$(grep -c "compose build web" "$SHIM_LOG")" -eq 2 ]
}

@test "rebuild puts the previously applied list from the running image into the safeguard" {
    plugin add testplug
    [ "$status" -eq 0 ]
    rm -rf "$BYRO_ROOT"/backups/pre-plugin-*
    export SHIM_APPLIED_PLUGINS="byro-testplug==1.0.0  # byroctl:catalog=testplug version=1.0.0"
    printf 'byro-hand==2.0\n' >>"$PLUGINS_FILE"
    plugin rebuild
    [ "$status" -eq 0 ]
    dir="$(ls -d "$BYRO_ROOT"/backups/pre-plugin-v2026.3.0-*)"
    [ "$(cat "$dir/plugins.txt")" = "$SHIM_APPLIED_PLUGINS" ]
    refute grep -q "byro-hand" "$dir/plugins.txt"
    grep -q "byro-hand==2.0" "$PLUGINS_FILE"
    grep -qx 'BYROCTL_PREVIOUS_PLUGINS=plugins.txt' "$dir/META"
    grep -q "compose exec -T web cat /byro/plugins.txt" "$SHIM_LOG"
}

@test "list shows the catalog with installed versions, extra entries and the image; it needs no docker" {
    plugin add testplug 'byro-x==1.0'
    [ "$status" -eq 0 ]
    PATH="/usr/bin:/bin" run "$DEPLOY_DIR/byroctl" --root "$BYRO_ROOT" plugin list
    [ "$status" -eq 0 ]
    [[ "${lines[0]}" == NAME*PACKAGE*SOURCE*INSTALLED*DESCRIPTION* ]]
    [[ "$output" == *"testplug"*"byro-testplug"*"pypi"*"1.0.0"*"A PyPI test plugin."* ]]
    [[ "$output" == *"gitplug"*"byro-gitplug"*"github"*"-"* ]]
    [[ "$output" == *"Additional entries in plugins/plugins.txt:"* ]]
    [[ "$output" == *"byro-x==1.0"* ]]
    [[ "$output" == *"plugin image: byro-plugins:v2026.3.0"* ]]
}

@test "with a stopped stack add builds, checks and migrates but does not start anything" {
    export SHIM_RUNNING=0
    plugin add testplug
    [ "$status" -eq 0 ]
    grep -q "manage migrate" "$SHIM_LOG"
    refute grep -q "compose up -d$" "$SHIM_LOG"
    [[ "$output" == *"start it with: byroctl start"* ]]
}

@test "config check reports invalid lines and a list that disagrees with COMPOSE_FILE" {
    printf -- '--index-url=https://evil.example\n' >>"$PLUGINS_FILE"
    run byroctl --root "$BYRO_ROOT" config check
    [ "$status" -eq 1 ]
    [[ "$output" == *"invalid line: --index-url"* ]]
    [[ "$output" == *"has invalid entries"* ]]
    printf 'byro-x==1.0\n' >"$PLUGINS_FILE"
    run byroctl --root "$BYRO_ROOT" config check
    [ "$status" -eq 1 ]
    [[ "$output" == *"COMPOSE_FILE does not include compose/plugins.yml"* ]]
    : >"$PLUGINS_FILE"
    conf_set COMPOSE_FILE "docker-compose.yml:compose/postgres.yml:compose/plugins.yml"
    run byroctl --root "$BYRO_ROOT" config check
    [ "$status" -eq 1 ]
    [[ "$output" == *"names no plugin"* ]]
}

@test "version lists the configured and the loaded plugins" {
    plugin add testplug
    [ "$status" -eq 0 ]
    run byroctl --root "$BYRO_ROOT" version
    [ "$status" -eq 0 ]
    [[ "$output" == *"plugins:        testplug 1.0.0"* ]]
    [[ "$output" == *"loaded plugins: byro_testplugin"* ]]
}

@test "plugin without a subcommand or with an unknown one is a usage error" {
    plugin
    [ "$status" -eq 64 ]
    plugin frobnicate
    [ "$status" -eq 64 ]
    plugin --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"Exit codes"* ]]
}
