#!/usr/bin/env bash
# Lint deploy/plugin-catalog.conf, the plugin catalog that "byroctl plugin add
# <shortname>" reads.
#
#   .github/scripts/check-plugin-catalog.sh [FILE]
#
# The catalog carries metadata only (no versions, no pins): one [shortname]
# section per plugin with the keys name, description, package, source and repo,
# each exactly once. byroctl parses it with grep/awk, so the format is strict:
# values run to the end of the line, no quotes, no inline comments, no tabs, no
# trailing whitespace. Anything the lint accepts must be what byroctl reads;
# deploy/tests/plugin_catalog.bats checks that contract. Process:
# docs/developer/releasing.rst, section "Plugin catalog".

FILE="deploy/plugin-catalog.conf"
KEYS="name description package source repo"
NAME_MAX=60
DESCRIPTION_MAX=120

# Output: progress on stderr; results as GitHub Actions annotations on stdout
# (harmless prefixes outside Actions).
log() { printf '%s\n' "$*" >&2; }
die() { printf '::error::%s\n' "$*"; exit 1; }
ERRORS=0
error() { printf '::error::%s\n' "$*"; ERRORS=$((ERRORS + 1)); }

# section_value SECTION KEY: the raw value, empty if absent
section_value() {
    awk -v s="[$1]" -v k="$2" '
        $0 == s { f = 1; next }
        /^\[/  { f = 0 }
        f && index($0, k "=") == 1 { print substr($0, length(k) + 2); exit }
    ' "$FILE"
}

lint_file() {
    local line n=0 section="" key
    if grep -q $'\r' "$FILE"; then error "$FILE contains carriage returns (CRLF line endings)"; fi
    if grep -q $'\t' "$FILE"; then error "$FILE contains tabs"; fi
    if grep -qE '[[:space:]]$' "$FILE"; then error "$FILE contains trailing whitespace"; fi
    while IFS= read -r line || [[ -n "$line" ]]; do
        n=$((n + 1))
        [[ -n "$line" && "$line" != \#* ]] || continue
        if [[ "$line" =~ ^\[([^]]*)\]$ ]]; then
            section="${BASH_REMATCH[1]}"
            [[ "$section" =~ ^[a-z0-9][a-z0-9-]{0,31}$ ]] \
                || error "$FILE:$n: invalid section name [$section] (lower-case letters, digits, hyphens, at most 32 characters)"
            continue
        fi
        if [[ "$line" =~ ^([a-z_]+)= ]]; then
            key="${BASH_REMATCH[1]}"
            [[ -n "$section" ]] || error "$FILE:$n: $key= before the first [section]"
            [[ " $KEYS " == *" $key "* ]] || error "$FILE:$n: unknown key $key (allowed: $KEYS)"
            continue
        fi
        error "$FILE:$n: neither a [section], a key=value line nor a comment: $line"
    done <"$FILE"
}

lint_sections() {
    local sections duplicate section key count value
    sections="$(grep -oE '^\[[^]]*\]$' "$FILE" | tr -d '[]' || true)"
    duplicate="$(sort <<<"$sections" | uniq -d | tr '\n' ' ')"
    [[ -z "${duplicate// /}" ]] || error "$FILE: duplicate sections: $duplicate"
    while IFS= read -r section; do
        [[ -n "$section" ]] || continue
        for key in $KEYS; do
            count="$(awk -v s="[$section]" -v k="$key" '
                $0 == s { f = 1; next }
                /^\[/  { f = 0 }
                f && index($0, k "=") == 1 { c++ }
                END { print c + 0 }' "$FILE")"
            [[ "$count" == 1 ]] || error "$FILE: [$section] must have exactly one $key= line (found $count)"
            value="$(section_value "$section" "$key")"
            [[ -n "$value" ]] || error "$FILE: [$section] has an empty $key"
        done
        lint_values "$section"
    done <<<"$sections"
}

lint_values() {
    local section="$1" value source
    value="$(section_value "$section" name)"
    (( ${#value} <= NAME_MAX )) || error "$FILE: [$section] name is longer than $NAME_MAX characters"
    value="$(section_value "$section" description)"
    (( ${#value} <= DESCRIPTION_MAX )) || error "$FILE: [$section] description is longer than $DESCRIPTION_MAX characters"
    value="$(section_value "$section" package)"
    [[ "$value" =~ ^[A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?$ ]] \
        || error "$FILE: [$section] package is not a valid Python project name: $value"
    source="$(section_value "$section" source)"
    [[ "$source" =~ ^(github|pypi)$ ]] || error "$FILE: [$section] source must be github or pypi (got: $source)"
    value="$(section_value "$section" repo)"
    case "$source" in
        github)
            [[ "$value" =~ ^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ && "$value" != *.git ]] \
                || error "$FILE: [$section] repo must be https://github.com/<owner>/<repo> without .git for source=github (got: $value)" ;;
        *)
            [[ "$value" =~ ^https://[^[:space:]]+$ ]] || error "$FILE: [$section] repo must be an https:// URL (got: $value)" ;;
    esac
}

main() {
    set -euo pipefail
    case "${1:-}" in
        "") ;;
        -h|--help) log "usage: $0 [FILE]"; exit 0 ;;
        *) FILE="$1" ;;
    esac
    [[ -f "$FILE" ]] || die "$FILE is missing"
    lint_file
    lint_sections
    if (( ERRORS > 0 )); then
        log "plugin catalog: $ERRORS error(s) in $FILE"
        exit 1
    fi
    log "plugin catalog: $FILE is well-formed ($(grep -cE '^\[' "$FILE" || true) plugin(s))"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    main "$@"
fi
