#!/usr/bin/env bats
# Library-level tests for byroctl: configuration file handling, quoting,
# validation, password generation. No docker needed except for the round-trip
# test, which is skipped when docker compose is unavailable.

load helpers/common

setup() {
    load_byroctl
    make_root
}

@test "conf_set creates the file with mode 600 and conf_get reads it back" {
    conf_set BYRO_SITE_URL https://byro.example.org
    [ "$(stat -c %a "$CONF_FILE" 2>/dev/null || stat -f %Lp "$CONF_FILE")" = "600" ]
    [ "$(conf_get BYRO_SITE_URL)" = "https://byro.example.org" ]
}

@test "conf_set replaces an existing definition in place and keeps comments" {
    printf '# head\nA=1\n# mid\nB=2\n' >"$CONF_FILE"
    conf_set A 9
    [ "$(cat "$CONF_FILE")" = "$(printf '# head\nA=9\n# mid\nB=2')" ]
}

@test "conf_set activates a commented template line" {
    printf '#BYRO_UID=1000\nX=1\n' >"$CONF_FILE"
    conf_set BYRO_UID 1234
    [ "$(cat "$CONF_FILE")" = "$(printf 'BYRO_UID=1234\nX=1')" ]
}

@test "conf_set appends a missing key" {
    printf 'A=1\n' >"$CONF_FILE"
    conf_set B two
    [ "$(cat "$CONF_FILE")" = "$(printf 'A=1\nB=two')" ]
}

@test "conf_set is idempotent and drops duplicate active lines" {
    printf 'A=1\nA=2\n' >"$CONF_FILE"
    conf_set A 3
    conf_set A 3
    [ "$(cat "$CONF_FILE")" = "A=3" ]
}

@test "conf_get returns 1 for missing keys and ignores commented lines" {
    printf '#A=1\nB=2\n' >"$CONF_FILE"
    run conf_get A
    [ "$status" -eq 1 ]
    [ "$(conf_get B)" = "2" ]
}

@test "conf_get honours the last definition and strips inline comments of unquoted values" {
    printf 'A=1\nA=abc #comment\nC=x#y\n' >"$CONF_FILE"
    [ "$(conf_get A)" = "abc" ]
    [ "$(conf_get C)" = "x#y" ]
}

@test "conf_encode leaves safe values unquoted and quotes everything else with single quotes" {
    [ "$(conf_encode plain-value_1.2:3/4@x)" = "plain-value_1.2:3/4@x" ]
    [ "$(conf_encode 'has space')" = "'has space'" ]
    [ "$(conf_encode 'p$a${b}')" = "'p\$a\${b}'" ]
    [ "$(conf_encode 'p#a')" = "'p#a'" ]
    [ "$(conf_encode 'say "hi"')" = "'say \"hi\"'" ]
    [ "$(conf_encode "it's")" = "'it\\'s'" ]
    [ "$(conf_encode 'a\b')" = "'a\\b'" ]
    [ "$(conf_encode '')" = "" ]
}

@test "conf_encode rejects newlines and a trailing backslash" {
    run conf_encode $'two\nlines'
    [ "$status" -eq 1 ]
    run conf_encode 'ends\'
    [ "$status" -eq 1 ]
    run conf_set BAD $'two\nlines'
    [ "$status" -ne 0 ]
    [ ! -f "$CONF_FILE" ]
}

@test "conf_set/conf_get round trip preserves special characters" {
    local v
    for v in 'p$a${b}s' 'p#a #b' 'has space' "it's" 'a\b\\c' 'say "hi"' 'x$1 #c '"'"'q'"'"' "d" \z' 'a\'"'"'b' '/&sed/'; do
        conf_set SECRET_VALUE "$v"
        [ "$(conf_get SECRET_VALUE)" = "$v" ]
    done
}

@test "values written by conf_set survive docker compose .env interpolation and env_file" {
    have_real_docker || skip "docker compose not available"
    local proj v
    proj="$(mktemp -d "$BATS_TEST_TMPDIR/proj.XXXXXX")"
    CONF_FILE="$proj/byro.conf"
    ln -s byro.conf "$proj/.env"
    cat >"$proj/docker-compose.yml" <<'YML'
services:
  t:
    image: alpine
    env_file: byro.conf
    environment:
      INTERPOLATED: ${PW}
YML
    for v in 'p$a${b}s' 'p#a #b' 'has space' "it's" 'a\b' 'say "hi"' 'mix$1 #c '"'"'q'"'"' "d" \z'; do
        conf_set PW "$v"
        run docker compose --project-directory "$proj" --project-name byroctl-quoting config --format json
        [ "$status" -eq 0 ]
        # both the interpolated and the env_file value must equal the input
        printf '%s' "$output" >"$proj/config.json"
        python3 - "$v" "$proj/config.json" <<'PY'
import json, sys
value = sys.argv[1]
with open(sys.argv[2], encoding="utf-8") as f:
    cfg = json.load(f)
env = cfg["services"]["t"]["environment"]
assert env["INTERPOLATED"] == value, (env["INTERPOLATED"], value)
assert env["PW"] == value, (env["PW"], value)
PY
    done
}

@test "gen_password yields 32 alphanumeric characters under pipefail" {
    set -o pipefail
    local pw
    pw="$(gen_password)"
    [ "${#pw}" -eq 32 ]
    [[ "$pw" =~ ^[A-Za-z0-9]+$ ]]
    [ "$(gen_password)" != "$pw" ]
}

@test "validators accept and reject as intended" {
    valid_url https://byro.example.org
    valid_url http://localhost:8345
    ! valid_url https://byro.example.org/path
    ! valid_url byro.example.org
    valid_email admin@example.org
    ! valid_email a@b
    valid_username admin.user+1
    ! valid_username 'bad user'
    valid_version v2026.3.0
    ! valid_version 2026.3.0
    ! valid_version latest
    valid_digest sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
    ! valid_digest sha256:short
    is_secret_key BYRO_DB_PASS
    is_secret_key BYRO_OIDC_CLIENT_SECRET
    ! is_secret_key BYRO_SITE_URL
}

@test "version_ge compares dotted versions" {
    version_ge 24.0.7 24.0.0
    version_ge 2.31.0 2.20.0
    ! version_ge 2.19.9 2.20.0
    version_ge 27.1 24.0.0
}

@test "conf_mask hides secrets only" {
    [ "$(conf_mask BYRO_DB_PASS geheim)" = "********" ]
    [ "$(conf_mask BYRO_DB_PASS '')" = "" ]
    [ "$(conf_mask BYRO_SITE_URL https://x)" = "https://x" ]
}

@test "compose_files splits COMPOSE_FILE and defaults to the base file" {
    printf 'COMPOSE_FILE=docker-compose.yml:compose/postgres.yml\n' >"$CONF_FILE"
    [ "$(compose_files | tr '\n' ' ')" = "docker-compose.yml compose/postgres.yml " ]
    compose_file_active compose/postgres.yml
    ! compose_file_active compose/caddy.yml
    : >"$CONF_FILE"
    [ "$(compose_files)" = "docker-compose.yml" ]
}
