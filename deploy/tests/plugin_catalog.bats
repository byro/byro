#!/usr/bin/env bats
# .github/scripts/check-plugin-catalog.sh against throwaway catalog files, and
# the contract between the lint and byroctl's catalog parser.

load helpers/common

# catalog LINES...: write a catalog file with one argument per line
catalog() {
    CATALOG="$BATS_TEST_TMPDIR/plugin-catalog.conf"
    printf '%s\n' "$@" >"$CATALOG"
}

# valid_entry [SECTION]: the lines of a complete, valid section
valid_entry() {
    local s="${1:-camt}"
    printf '%s\n' "[$s]" "name=CAMT import" "description=Imports CAMT.053 statements." \
        "package=byro-$s" "source=github" "repo=https://github.com/byro/byro-$s"
}

setup() {
    SCRIPT="$REPO_ROOT/.github/scripts/check-plugin-catalog.sh"
}

lint() { run "$SCRIPT" "$CATALOG"; }

@test "a valid catalog passes" {
    catalog "# comment" "" "$(valid_entry camt)" "" "$(valid_entry mailman | sed 's/source=github/source=pypi/; s#repo=.*#repo=https://pypi.org/project/byro-mailman/#')"
    lint
    [ "$status" -eq 0 ]
    [[ "$output" == *"well-formed (2 plugin(s))"* ]]
}

@test "the shipped catalog passes" {
    run "$SCRIPT" "$DEPLOY_DIR/plugin-catalog.conf"
    [ "$status" -eq 0 ]
}

@test "every required key must be present exactly once" {
    local key
    for key in name description package source repo; do
        catalog "$(valid_entry | grep -v "^$key=")"
        lint
        [ "$status" -eq 1 ]
        [[ "$output" == *"exactly one $key= line (found 0)"* ]]
    done
    catalog "$(valid_entry)" "package=byro-other"
    lint
    [ "$status" -eq 1 ]
    [[ "$output" == *"exactly one package= line (found 2)"* ]]
}

@test "empty values are rejected" {
    catalog "$(valid_entry | sed 's/^description=.*/description=/')"
    lint
    [ "$status" -eq 1 ]
    [[ "$output" == *"has an empty description"* ]]
}

@test "duplicate sections are rejected" {
    catalog "$(valid_entry camt)" "$(valid_entry camt)"
    lint
    [ "$status" -eq 1 ]
    [[ "$output" == *"duplicate sections: camt"* ]]
}

@test "section names are lower-case letters, digits and hyphens" {
    local bad
    for bad in Camt my_plugin -camt; do
        catalog "$(valid_entry | sed "1s/.*/[$bad]/")"
        lint
        [ "$status" -eq 1 ]
        [[ "$output" == *"invalid section name [$bad]"* ]]
    done
}

@test "source must be github or pypi" {
    catalog "$(valid_entry | sed 's/source=github/source=gitlab/')"
    lint
    [ "$status" -eq 1 ]
    [[ "$output" == *"source must be github or pypi"* ]]
}

@test "github repos are https://github.com/owner/repo without .git" {
    catalog "$(valid_entry | sed 's#repo=.*#repo=http://github.com/byro/byro-camt#')"
    lint
    [ "$status" -eq 1 ]
    [[ "$output" == *"repo must be https://github.com/<owner>/<repo>"* ]]
    catalog "$(valid_entry | sed 's#repo=.*#repo=https://github.com/byro/byro-camt.git#')"
    lint
    [ "$status" -eq 1 ]
    catalog "$(valid_entry | sed 's#repo=.*#repo=https://gitlab.com/byro/byro-camt#')"
    lint
    [ "$status" -eq 1 ]
}

@test "pypi entries need an https homepage" {
    catalog "$(valid_entry | sed 's/source=github/source=pypi/; s#repo=.*#repo=http://example.org#')"
    lint
    [ "$status" -eq 1 ]
    [[ "$output" == *"repo must be an https:// URL"* ]]
}

@test "package must be a Python project name" {
    local bad
    for bad in "-e byro-camt" "byro camt" "byro-camt==1.0" "byro-camt-"; do
        catalog "$(valid_entry | sed "s/^package=.*/package=$bad/")"
        lint
        [ "$status" -eq 1 ]
        [[ "$output" == *"not a valid Python project name"* ]]
    done
}

@test "a key before the first section and unknown keys are rejected" {
    catalog "name=orphan" "$(valid_entry)"
    lint
    [ "$status" -eq 1 ]
    [[ "$output" == *"name= before the first [section]"* ]]
    catalog "$(valid_entry)" "version=1.0.0"
    lint
    [ "$status" -eq 1 ]
    [[ "$output" == *"unknown key version"* ]]
}

@test "lines that are neither section, key nor comment are rejected" {
    catalog "$(valid_entry)" "just words"
    lint
    [ "$status" -eq 1 ]
    [[ "$output" == *"neither a [section], a key=value line nor a comment"* ]]
}

@test "tabs, CRLF and trailing whitespace are rejected" {
    catalog "$(valid_entry)" $'name2=x\t'
    lint
    [ "$status" -eq 1 ]
    [[ "$output" == *"contains tabs"* ]]
    catalog "$(valid_entry | sed 's/$/\r/')"
    lint
    [ "$status" -eq 1 ]
    [[ "$output" == *"carriage returns"* ]]
    catalog "$(valid_entry | sed 's/^name=.*/& /')"
    lint
    [ "$status" -eq 1 ]
    [[ "$output" == *"trailing whitespace"* ]]
}

@test "overlong name and description are rejected" {
    catalog "$(valid_entry | sed "s/^name=.*/name=$(printf 'x%.0s' {1..61})/")"
    lint
    [ "$status" -eq 1 ]
    [[ "$output" == *"name is longer than 60"* ]]
    catalog "$(valid_entry | sed "s/^description=.*/description=$(printf 'x%.0s' {1..121})/")"
    lint
    [ "$status" -eq 1 ]
    [[ "$output" == *"description is longer than 120"* ]]
}

@test "a missing file is an error" {
    run "$SCRIPT" "$BATS_TEST_TMPDIR/does-not-exist.conf"
    [ "$status" -eq 1 ]
    [[ "$output" == *"is missing"* ]]
}

@test "what the lint accepts is what byroctl reads" {
    load_byroctl
    catalog "$(valid_entry camt)" "" "$(valid_entry mailman | sed 's/source=github/source=pypi/; s#repo=.*#repo=https://pypi.org/project/byro-mailman/#')"
    lint
    [ "$status" -eq 0 ]
    [ "$(catalog_names "$CATALOG" | tr '\n' ' ')" = "camt mailman " ]
    catalog_has camt "$CATALOG"
    refute catalog_has other "$CATALOG"
    [ "$(catalog_field camt package "$CATALOG")" = "byro-camt" ]
    [ "$(catalog_field camt source "$CATALOG")" = "github" ]
    [ "$(catalog_field camt repo "$CATALOG")" = "https://github.com/byro/byro-camt" ]
    [ "$(catalog_field mailman source "$CATALOG")" = "pypi" ]
    [ "$(catalog_field mailman repo "$CATALOG")" = "https://pypi.org/project/byro-mailman/" ]
    [ -z "$(catalog_field camt version "$CATALOG")" ]
    # the shipped catalog through the same functions
    [ "$(catalog_field finance-import-bank-files package "$DEPLOY_DIR/plugin-catalog.conf")" = "byro-finance-import-bank-files" ]
}
