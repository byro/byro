#!/usr/bin/env bash
# Point the CI-managed branch "stable" at a byro release tag.
#
#   .github/scripts/update-stable-branch.sh TAG [options]
#
# The branch "stable" carries only what the byro bootstrap needs before it knows
# a release: install.sh, a byte-identical copy of deploy/install.sh from the
# release tag, and stable.env, which names the release
# (BYRO_RELEASE_VERSION=vYYYY.M.P). install.sh and byroctl download everything
# else from the immutable release tag. The release pipeline runs this script as
# its last step, after the image and the PyPI package were published; the
# workflow "Stable pointer" runs it by hand (workflow_dispatch).
#
# Rules:
#   * TAG must be a release tag vYYYY.M.P; anything else (pre-release tags,
#     "latest") is rejected.
#   * The tag must contain deploy/install.sh, and the copy must match the tag's
#     deploy/SHA256SUMS.
#   * The image IMAGE_REPO:TAG must exist in the registry, the same check that
#     install.sh performs later (--no-image-check: tests and development only).
#   * stable only moves forward. Versions are compared numerically field by
#     field (v2026.10.0 is newer than v2026.9.9). An older release leaves the
#     pointer alone and exits 0 with a notice; --force allows moving back.
#   * Every change is a new commit on top of the existing branch history,
#     pushed as a fast-forward. The branch is never force-pushed or rewritten.
#
# Options:
#   --force             allow pointing stable at an older release
#   --dry-run           show what would be committed, push nothing
#   --remote NAME       git remote (default origin)
#   --branch NAME       branch name (default stable)
#   --image-repo REPO   image repository (default ghcr.io/byro/byro)
#   --no-image-check    skip the registry check (tests and development only)
#
# Run it inside any checkout of the repository, whatever its depth: the tag and
# the branch are fetched from the remote when they are missing locally. The
# commit is built with git plumbing (hash-object, mktree, commit-tree), so the
# working copy and the index stay untouched. Requires git and, unless
# --no-image-check, the docker CLI.

TAG=""
FORCE=0
DRY_RUN=0
REMOTE="origin"
BRANCH="stable"
IMAGE_REPO="ghcr.io/byro/byro"
IMAGE_CHECK=1
WORK=""   # temporary directory, removed by the EXIT trap (global: the trap runs after main returns)

log() { printf '%s\n' "$*" >&2; }
die() { log "error: $*"; exit 1; }

# notice MESSAGE: visible in the GitHub Actions log as an annotation and on stderr.
notice() {
    if [[ -n "${GITHUB_ACTIONS:-}" ]]; then
        printf '::notice::%s\n' "$*"
    fi
    log "$*"
}

# summary MESSAGE: one line in the GitHub Actions step summary, if available.
summary() {
    if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
        printf '%s\n\n' "$*" >>"$GITHUB_STEP_SUMMARY"
    fi
    return 0
}

usage() {
    sed -n '2,/^$/p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

valid_tag() { [[ "$1" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; }

# calver_cmp A B: compare two release tags vYYYY.M.P numerically, field by
# field, and print -1 (A older), 0 (same) or 1 (A newer). Never lexicographic:
# v2026.10.0 is newer than v2026.9.9, v2027.1.0 is newer than v2026.99.99.
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

sha256_of() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | cut -d' ' -f1
    else
        shasum -a 256 "$1" | cut -d' ' -f1
    fi
}

# stable_version: reads a stable.env on stdin and prints the release it names,
# or nothing. Only a line that exactly matches the expected form counts; this is
# the same rule install.sh and byroctl apply.
stable_version() {
    grep -E '^BYRO_RELEASE_VERSION=v[0-9]+\.[0-9]+\.[0-9]+$' | head -n1 | cut -d= -f2 || true
}

# ensure_identity: git commit-tree needs an author; CI sets it via git config,
# otherwise fall back to the GitHub Actions bot.
ensure_identity() {
    if [[ -z "${GIT_COMMITTER_NAME:-}" && -z "$(git config user.name 2>/dev/null || true)" ]]; then
        export GIT_AUTHOR_NAME="github-actions[bot]" GIT_COMMITTER_NAME="github-actions[bot]"
    fi
    if [[ -z "${GIT_COMMITTER_EMAIL:-}" && -z "$(git config user.email 2>/dev/null || true)" ]]; then
        export GIT_AUTHOR_EMAIL="41898282+github-actions[bot]@users.noreply.github.com"
        export GIT_COMMITTER_EMAIL="41898282+github-actions[bot]@users.noreply.github.com"
    fi
}

write_stable_env() {
    cat >"$1" <<EOF
# byro: the current stable release. Written by CI (.github/workflows/stable.yml)
# after the release's image and package were published. Do not edit by hand.
# install.sh and byroctl read exactly one line of this file:
BYRO_RELEASE_VERSION=$2
EOF
}

write_readme() {
    cat >"$1" <<'EOF'
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
            --remote) [[ $# -ge 2 ]] || die "--remote needs a value"; REMOTE="$2"; shift ;;
            --branch) [[ $# -ge 2 ]] || die "--branch needs a value"; BRANCH="$2"; shift ;;
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
    valid_tag "$TAG" || die "not a release tag: $TAG (expected vYYYY.M.P; pre-release tags never move stable)"
    git rev-parse --git-dir >/dev/null 2>&1 || die "run this inside a checkout of the byro repository"

    WORK="$(mktemp -d)"
    trap 'rm -rf "$WORK"' EXIT

    # 1. the release tag and its install.sh
    if ! git rev-parse -q --verify "refs/tags/$TAG^{commit}" >/dev/null; then
        log "fetching tag $TAG from $REMOTE"
        git fetch --quiet --no-tags "$REMOTE" "refs/tags/$TAG:refs/tags/$TAG" 2>/dev/null \
            || die "tag $TAG not found on $REMOTE"
    fi
    git show "$TAG:deploy/install.sh" >"$WORK/install.sh" 2>/dev/null \
        || die "$TAG has no deploy/install.sh (a release from before byroctl); stable cannot point at it"
    git show "$TAG:deploy/SHA256SUMS" >"$WORK/SHA256SUMS" 2>/dev/null \
        || die "$TAG has no deploy/SHA256SUMS"
    local expected actual
    expected="$(grep -E '^[0-9a-f]{64}  install\.sh$' "$WORK/SHA256SUMS" | head -n1 | cut -d' ' -f1 || true)"
    [[ -n "$expected" ]] || die "deploy/SHA256SUMS of $TAG has no entry for install.sh"
    actual="$(sha256_of "$WORK/install.sh")"
    [[ "$actual" == "$expected" ]] \
        || die "deploy/install.sh of $TAG does not match its SHA256SUMS ($actual, expected $expected)"

    # 2. the image gate, the same check install.sh performs
    if (( IMAGE_CHECK )); then
        docker manifest inspect "$IMAGE_REPO:$TAG" >/dev/null 2>&1 \
            || die "the image $IMAGE_REPO:$TAG is not available in the registry; stable is not moved"
    else
        log "skipping the image check (--no-image-check)"
    fi

    # 3. the current pointer
    local base="" current=""
    if git fetch --quiet --no-tags "$REMOTE" "refs/heads/$BRANCH" 2>/dev/null; then
        base="$(git rev-parse FETCH_HEAD)"
        current="$(git show "FETCH_HEAD:stable.env" 2>/dev/null | stable_version)"
    fi
    if [[ -n "$current" ]]; then
        case "$(calver_cmp "$current" "$TAG")" in
            0)
                notice "stable already points to $TAG; nothing to do"
                summary "stable already points to \`$TAG\`; nothing to do."
                exit 0 ;;
            1)
                if (( ! FORCE )); then
                    notice "stable stays at $current: $TAG is an older release. To move it back on purpose, run the workflow 'Stable pointer' with force."
                    summary "stable stays at \`$current\`: \`$TAG\` is an older release (not moved)."
                    exit 0
                fi
                log "moving stable back from $current to $TAG (--force)" ;;
            *)
                log "moving stable from $current to $TAG" ;;
        esac
    elif [[ -n "$base" ]]; then
        log "branch $BRANCH exists but has no valid stable.env; replacing its content"
    else
        log "branch $BRANCH does not exist yet on $REMOTE; creating it"
    fi

    # 4. the new content as a git tree, built without touching the working copy
    write_stable_env "$WORK/stable.env" "$TAG"
    write_readme "$WORK/README.md"
    local blob_install blob_env blob_readme tree
    blob_install="$(git hash-object -w "$WORK/install.sh")"
    blob_env="$(git hash-object -w "$WORK/stable.env")"
    blob_readme="$(git hash-object -w "$WORK/README.md")"
    tree="$(printf '100644 blob %s\tREADME.md\n100755 blob %s\tinstall.sh\n100644 blob %s\tstable.env\n' \
        "$blob_readme" "$blob_install" "$blob_env" | git mktree)"
    if [[ -n "$base" && "$(git rev-parse "$base^{tree}")" == "$tree" ]]; then
        notice "stable already has this content; nothing to do"
        exit 0
    fi

    # 5. the commit on top of the existing history, and the fast-forward push
    ensure_identity
    local subject body commit
    subject="stable: point to $TAG"
    body="$(printf 'Previous: %s\nImage: %s:%s\ninstall.sh: deploy/install.sh from tag %s (sha256 %s)' \
        "${current:-none}" "$IMAGE_REPO" "$TAG" "$TAG" "$actual")"
    if [[ -n "$base" ]]; then
        commit="$(git commit-tree "$tree" -p "$base" -m "$subject" -m "$body")"
    else
        commit="$(git commit-tree "$tree" -m "$subject" -m "$body")"
    fi
    if (( DRY_RUN )); then
        log "dry run: would push commit $commit to $REMOTE $BRANCH ($subject)"
        if [[ -n "$base" ]]; then
            git diff-tree --stat "$base" "$tree" >&2
        else
            git ls-tree "$tree" >&2
        fi
        exit 0
    fi
    git push --quiet "$REMOTE" "$commit:refs/heads/$BRANCH" \
        || die "push to $REMOTE $BRANCH failed (a concurrent update? run again)"
    notice "stable now points to $TAG (was ${current:-none})"
    summary "stable now points to \`$TAG\` (was \`${current:-none}\`)."
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    main "$@"
fi
