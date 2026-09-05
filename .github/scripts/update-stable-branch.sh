#!/usr/bin/env bash
# Point the CI-managed branch "stable" at a byro release tag.
#
#   .github/scripts/update-stable-branch.sh TAG [--force] [--dry-run]
#                                               [--image-repo REPO] [--no-image-check]
#
# The branch carries install.sh (a byte-identical copy of deploy/install.sh from
# the release tag) and stable.env (BYRO_RELEASE_VERSION=vYYYY.M.P); the byro
# bootstrap and "byroctl update --check" read them. The release pipeline runs
# this script as its last step, the workflow "Stable pointer" runs it by hand.
# The pointer only moves forward on its own (numeric CalVer comparison), --force
# allows an older release; a re-created tag with changed content refreshes the
# branch. Every change is a new commit on top of the branch history, built with
# git plumbing (no checkout, no index) and pushed as a fast-forward. Process and
# rationale: docs/developer/releasing.rst.
#
# Options:
#   --force             allow pointing stable at an older release
#   --dry-run           show what would be committed, push nothing
#   --image-repo REPO   image repository for the registry check (default ghcr.io/byro/byro)
#   --no-image-check    skip the registry check (tests and development only)
#
# Run it inside any checkout of the repository, whatever its depth: the tag and
# the branch are fetched from origin when they are missing locally. Needs git
# and, unless --no-image-check, the docker CLI. The committer identity comes
# from the git configuration.

TAG=""
FORCE=0
DRY_RUN=0
REMOTE="origin"
BRANCH="stable"
IMAGE_REPO="ghcr.io/byro/byro"
IMAGE_CHECK=1

# Output: progress on stderr; results as GitHub Actions annotations on stdout
# (harmless prefixes outside Actions). notice also feeds the step summary.
log() { printf '%s\n' "$*" >&2; }
die() { printf '::error::%s\n' "$*"; exit 1; }
notice() {
    printf '::notice::%s\n' "$*"
    if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
        printf '%s\n\n' "$*" >>"$GITHUB_STEP_SUMMARY"
    fi
}

usage() {
    sed -n '2,/^$/p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

# valid_version TAG: a release tag vYYYY.M.P. Stricter than the consumers' rule
# in byroctl (no leading zeros in a field), so that one release has one spelling.
valid_version() { [[ "$1" =~ ^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$ ]]; }

# calver_cmp A B: compare two release tags vYYYY.M.P field by field as integers
# and print -1 (A older), 0 (same) or 1 (A newer). Spelled out on purpose so
# that the ordering rule stands on its own, independent of sort implementations.
calver_cmp() {
    local a="${1#v}" b="${2#v}" i x y
    local -a fa fb
    IFS=. read -r -a fa <<<"$a"
    IFS=. read -r -a fb <<<"$b"
    for i in 0 1 2; do
        x=$((10#${fa[$i]}))
        y=$((10#${fb[$i]}))
        if (( x < y )); then printf -- '-1'; return 0; fi
        if (( x > y )); then printf '1'; return 0; fi
    done
    printf '0'
}

# sha256_of: the SHA-256 of stdin, with the same fallback the production scripts use
sha256_of() {
    { if command -v sha256sum >/dev/null 2>&1; then sha256sum; else shasum -a 256; fi; } | awk '{print $1}'
}

# stable_version: reads a stable.env on stdin and prints the release it names,
# or nothing. Only a line that exactly matches the expected form counts; this is
# the consumers' rule from install.sh and byroctl, kept identical on purpose.
stable_version() {
    grep -E '^BYRO_RELEASE_VERSION=v[0-9]+\.[0-9]+\.[0-9]+$' | head -n1 | cut -d= -f2 || true
}

stable_env() {
    cat <<EOF
# byro: the current stable release. Written by CI (.github/workflows/stable.yml)
# after the release's image and package were published. Do not edit by hand.
# install.sh and byroctl read exactly one line of this file:
BYRO_RELEASE_VERSION=$1
EOF
}

readme() {
    cat <<'EOF'
# byro stable pointer

This branch is written by CI and points at the current stable byro release.
It is not a source branch. It only carries

* `install.sh`, the bootstrap script: a byte-identical copy of `deploy/install.sh`
  from the release tag named in `stable.env`, and
* `stable.env`, one line `BYRO_RELEASE_VERSION=vYYYY.M.P`.

Everything else (byroctl, the Compose files, the container image) comes from the
immutable release tag. Install byro with

    bash -c "$(curl -fsSL https://raw.githubusercontent.com/byro/byro/stable/install.sh)"

Documentation: https://byro.readthedocs.io/en/latest/administrator/installation-byroctl.html

Do not edit this branch or push to it by hand. The pointer moves automatically
after every release; to move it deliberately, run the "Stable pointer" workflow
(see docs/developer/releasing.rst in the main branch).
EOF
}

parse_args() {
    while (( $# )); do
        case "$1" in
            --force) FORCE=1 ;;
            --dry-run) DRY_RUN=1 ;;
            --image-repo) [[ $# -ge 2 ]] || die "--image-repo needs a value"; IMAGE_REPO="$2"; shift ;;
            --no-image-check) IMAGE_CHECK=0 ;;
            -h|--help) usage; exit 0 ;;
            -*) die "unknown option: $1 (see --help)" ;;
            *) [[ -z "$TAG" ]] || die "unexpected argument: $1"; TAG="$1" ;;
        esac
        shift
    done
    [[ -n "$TAG" ]] || die "missing release tag (see --help)"
}

main() {
    set -euo pipefail
    parse_args "$@"
    valid_version "$TAG" \
        || die "not a release tag: $TAG (expected vYYYY.M.P without leading zeros; pre-release tags never move stable)"
    git rev-parse --git-dir >/dev/null 2>&1 || die "run this inside a checkout of the byro repository"

    # 1. the release tag; its install.sh blob is reused as it is
    if ! git rev-parse -q --verify "refs/tags/$TAG^{commit}" >/dev/null; then
        log "fetching tag $TAG from $REMOTE"
        git fetch --quiet --no-tags "$REMOTE" "refs/tags/$TAG:refs/tags/$TAG" 2>/dev/null \
            || die "tag $TAG not found on $REMOTE"
    fi
    local blob_install expected actual
    blob_install="$(git rev-parse -q --verify "$TAG:deploy/install.sh" 2>/dev/null)" \
        || die "$TAG has no deploy/install.sh (a release from before byroctl); stable cannot point at it"
    expected="$(git show "$TAG:deploy/SHA256SUMS" 2>/dev/null | awk '$2 == "install.sh" {print $1}' | head -n1 || true)"
    [[ -n "$expected" ]] || die "$TAG has no deploy/SHA256SUMS entry for install.sh"
    actual="$(git cat-file blob "$blob_install" | sha256_of)"
    [[ "$actual" == "$expected" ]] \
        || die "deploy/install.sh of $TAG does not match its SHA256SUMS ($actual, expected $expected)"

    # 2. the current pointer: a missing branch is fine, a failing remote is not
    local rc=0 base="" current=""
    git ls-remote --exit-code --heads "$REMOTE" "$BRANCH" >/dev/null 2>&1 || rc=$?
    case "$rc" in
        0)
            git fetch --quiet --no-tags "$REMOTE" "refs/heads/$BRANCH" || die "cannot fetch $BRANCH from $REMOTE"
            base="$(git rev-parse FETCH_HEAD)"
            current="$(git show "FETCH_HEAD:stable.env" 2>/dev/null | stable_version || true)" ;;
        2)
            log "branch $BRANCH does not exist yet on $REMOTE; creating it" ;;
        *)
            die "cannot query $REMOTE for branch $BRANCH (git ls-remote failed with exit $rc); stable is not moved" ;;
    esac

    # 3. the new tree, built from blobs without touching the working copy
    local blob_env blob_readme tree
    blob_env="$(stable_env "$TAG" | git hash-object -w --stdin)"
    blob_readme="$(readme | git hash-object -w --stdin)"
    tree="$(printf '100644 blob %s\tREADME.md\n100755 blob %s\tinstall.sh\n100644 blob %s\tstable.env\n' \
        "$blob_readme" "$blob_install" "$blob_env" | git mktree)"
    if [[ -n "$base" && "$(git rev-parse "$base^{tree}")" == "$tree" ]]; then
        notice "stable already points to $TAG with this content; nothing to do"
        exit 0
    fi

    # 4. stable only moves forward; the same release with changed content is refreshed
    if [[ -n "$current" ]]; then
        case "$(calver_cmp "$current" "$TAG")" in
            0)
                log "refreshing stable at $TAG: the content of the tag changed" ;;
            1)
                if (( ! FORCE )); then
                    notice "stable stays at $current: $TAG is an older release. To move it back on purpose, run the workflow 'Stable pointer' with force."
                    exit 0
                fi
                log "moving stable back from $current to $TAG (--force)" ;;
            *)
                log "moving stable from $current to $TAG" ;;
        esac
    elif [[ -n "$base" ]]; then
        log "branch $BRANCH exists but has no valid stable.env; replacing its content"
    fi

    # 5. the image gate, the same check install.sh performs
    if (( IMAGE_CHECK )); then
        docker manifest inspect "$IMAGE_REPO:$TAG" >/dev/null 2>&1 \
            || die "the image $IMAGE_REPO:$TAG is not available in the registry; stable is not moved"
    else
        log "skipping the image check (--no-image-check)"
    fi

    # 6. the commit on top of the branch history, and the fast-forward push
    local commit
    # ${base:+-p "$base"} adds the parent only when the branch exists (word splitting intended)
    # shellcheck disable=SC2086
    commit="$(git commit-tree "$tree" ${base:+-p "$base"} -m "stable: point to $TAG" \
        -m "$(printf 'Previous: %s\nImage: %s:%s\ninstall.sh: deploy/install.sh from tag %s (sha256 %s)' \
            "${current:-none}" "$IMAGE_REPO" "$TAG" "$TAG" "$actual")")"
    if (( DRY_RUN )); then
        log "dry run: would push commit $commit to $REMOTE $BRANCH"
        git show --stat --format='%s' "$commit" >&2
        exit 0
    fi
    git push --quiet "$REMOTE" "$commit:refs/heads/$BRANCH" \
        || die "push to $REMOTE $BRANCH failed (a concurrent update? run again)"
    notice "stable now points to $TAG (was ${current:-none})"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    main "$@"
fi
