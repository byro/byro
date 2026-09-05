#!/usr/bin/env bats
# .github/scripts/update-stable-branch.sh against a local bare repository as
# "origin" and the docker shim as the registry. No network involved.

load helpers/common

# Constants are set in setup(): top-level assignments are not reliably visible
# inside bats test functions.
constants() {
    SCRIPT="$REPO_ROOT/.github/scripts/update-stable-branch.sh"
    IMAGE="ghcr.io/byro/byro"
}

# make_tag TAG [MARKER]: a release commit with deploy/install.sh (the real file,
# plus a visible marker) and a matching deploy/SHA256SUMS, tagged and pushed.
make_tag() {
    local tag="$1" marker="${2:-}"
    mkdir -p "$CLONE/deploy"
    cp "$DEPLOY_DIR/install.sh" "$CLONE/deploy/install.sh"
    if [[ -n "$marker" ]]; then
        printf '\n# %s\n' "$marker" >>"$CLONE/deploy/install.sh"
    fi
    ( cd "$CLONE/deploy" && sha256sum install.sh >SHA256SUMS )
    git -C "$CLONE" add -A
    git -C "$CLONE" commit -q -m "release $tag"
    git -C "$CLONE" tag "$tag"
    git -C "$CLONE" push -q origin main "refs/tags/$tag"
}

stable_file() { git -C "$ORIGIN" show "stable:$1"; }
stable_count() { git -C "$ORIGIN" rev-list --count stable; }
stable_exists() { git -C "$ORIGIN" rev-parse --verify -q refs/heads/stable >/dev/null; }

setup() {
    constants
    use_shims
    export HOME="$BATS_TEST_TMPDIR/home"
    mkdir -p "$HOME"
    export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null
    export GIT_AUTHOR_NAME=test GIT_AUTHOR_EMAIL=test@example.org
    export GIT_COMMITTER_NAME=test GIT_COMMITTER_EMAIL=test@example.org
    export SHIM_TAGS="$IMAGE:v2026.3.0 $IMAGE:v2026.4.0 $IMAGE:v2026.9.9 $IMAGE:v2026.10.0"
    ORIGIN="$BATS_TEST_TMPDIR/origin.git"
    CLONE="$BATS_TEST_TMPDIR/clone"
    git init -q --bare "$ORIGIN"
    git -c init.defaultBranch=main init -q "$CLONE"
    git -C "$CLONE" remote add origin "$ORIGIN"
    make_tag v2026.3.0
    make_tag v2026.4.0 "changed in v2026.4.0"
    cd "$CLONE"
}

@test "creates the stable branch with install.sh, stable.env and README" {
    run "$SCRIPT" v2026.3.0
    [ "$status" -eq 0 ]
    [[ "$output" == *"stable now points to v2026.3.0 (was none)"* ]]
    stable_exists
    [ "$(stable_count)" -eq 1 ]
    stable_file stable.env | grep -qx 'BYRO_RELEASE_VERSION=v2026.3.0'
    [ "$(stable_file stable.env | grep -cE '^BYRO_RELEASE_VERSION=')" -eq 1 ]
    diff <(git show v2026.3.0:deploy/install.sh) <(stable_file install.sh)
    [[ "$(git -C "$ORIGIN" ls-tree stable install.sh)" == 100755* ]]
    stable_file README.md | grep -q 'Stable pointer'
    git -C "$ORIGIN" log -1 --format=%s stable | grep -qx 'stable: point to v2026.3.0'
    grep -q "docker manifest inspect $IMAGE:v2026.3.0" "$SHIM_LOG"
    # the checkout itself is untouched
    [ -z "$(git status --porcelain)" ]
}

@test "running again for the same release changes nothing" {
    "$SCRIPT" v2026.3.0
    run "$SCRIPT" v2026.3.0
    [ "$status" -eq 0 ]
    [[ "$output" == *"already points to v2026.3.0"* ]]
    [ "$(stable_count)" -eq 1 ]
}

@test "a newer release appends a commit and replaces the content" {
    "$SCRIPT" v2026.3.0
    run "$SCRIPT" v2026.4.0
    [ "$status" -eq 0 ]
    [[ "$output" == *"stable now points to v2026.4.0 (was v2026.3.0)"* ]]
    [ "$(stable_count)" -eq 2 ]
    stable_file stable.env | grep -qx 'BYRO_RELEASE_VERSION=v2026.4.0'
    diff <(git show v2026.4.0:deploy/install.sh) <(stable_file install.sh)
    stable_file install.sh | grep -q 'changed in v2026.4.0'
    # the history is kept, the first pointer is the parent
    git -C "$ORIGIN" log --format=%s stable | tail -n1 | grep -qx 'stable: point to v2026.3.0'
}

@test "an older release leaves stable alone and exits 0 with a clear notice" {
    "$SCRIPT" v2026.4.0
    run "$SCRIPT" v2026.3.0
    [ "$status" -eq 0 ]
    [[ "$output" == *"stable stays at v2026.4.0: v2026.3.0 is an older release"* ]]
    [ "$(stable_count)" -eq 1 ]
    stable_file stable.env | grep -qx 'BYRO_RELEASE_VERSION=v2026.4.0'
}

@test "--force moves stable back to an older release, still as a new commit" {
    "$SCRIPT" v2026.4.0
    run "$SCRIPT" v2026.3.0 --force
    [ "$status" -eq 0 ]
    [[ "$output" == *"stable now points to v2026.3.0 (was v2026.4.0)"* ]]
    [ "$(stable_count)" -eq 2 ]
    stable_file stable.env | grep -qx 'BYRO_RELEASE_VERSION=v2026.3.0'
    diff <(git show v2026.3.0:deploy/install.sh) <(stable_file install.sh)
}

@test "versions are compared numerically, never lexicographically" {
    # shellcheck disable=SC1090
    source "$SCRIPT"
    [ "$(calver_cmp v2026.10.0 v2026.9.9)" = 1 ]
    [ "$(calver_cmp v2026.9.9 v2026.10.0)" = -1 ]
    [ "$(calver_cmp v2027.1.0 v2026.99.99)" = 1 ]
    [ "$(calver_cmp v2026.99.99 v2027.1.0)" = -1 ]
    [ "$(calver_cmp v2026.3.10 v2026.3.9)" = 1 ]
    [ "$(calver_cmp v2026.3.9 v2026.3.10)" = -1 ]
    [ "$(calver_cmp v2026.3.0 v2026.3.0)" = 0 ]
    [ "$(calver_cmp v2026.03.0 v2026.3.0)" = 0 ]
}

@test "the pointer moves from v2026.9.9 to v2026.10.0 but not back" {
    make_tag v2026.9.9 "v2026.9.9"
    make_tag v2026.10.0 "v2026.10.0"
    "$SCRIPT" v2026.9.9
    run "$SCRIPT" v2026.10.0
    [ "$status" -eq 0 ]
    [[ "$output" == *"stable now points to v2026.10.0 (was v2026.9.9)"* ]]
    stable_file stable.env | grep -qx 'BYRO_RELEASE_VERSION=v2026.10.0'
    run "$SCRIPT" v2026.9.9
    [ "$status" -eq 0 ]
    [[ "$output" == *"stable stays at v2026.10.0: v2026.9.9 is an older release"* ]]
    stable_file stable.env | grep -qx 'BYRO_RELEASE_VERSION=v2026.10.0'
    [ "$(stable_count)" -eq 2 ]
}

@test "a tag without deploy/install.sh is refused and nothing is pushed" {
    # a release from before byroctl: no deploy/ directory at all
    git rm -q -r deploy
    git commit -q -m "release without deploy/"
    git tag v2026.5.0
    git push -q origin main refs/tags/v2026.5.0
    export SHIM_TAGS="$SHIM_TAGS $IMAGE:v2026.5.0"
    run "$SCRIPT" v2026.5.0
    [ "$status" -ne 0 ]
    [[ "$output" == *"has no deploy/install.sh"* ]]
    ! stable_exists
}

@test "pre-release tags and other names are refused before anything happens" {
    run "$SCRIPT" v2026.3.0-rc1
    [ "$status" -ne 0 ]
    [[ "$output" == *"not a release tag"* ]]
    run "$SCRIPT" latest
    [ "$status" -ne 0 ]
    run "$SCRIPT" 2026.3.0
    [ "$status" -ne 0 ]
    ! stable_exists
    [ ! -s "$SHIM_LOG" ]
}

@test "a missing image blocks the update" {
    export SHIM_TAGS=""
    run "$SCRIPT" v2026.3.0
    [ "$status" -ne 0 ]
    [[ "$output" == *"is not available in the registry"* ]]
    ! stable_exists
    grep -q "docker manifest inspect $IMAGE:v2026.3.0" "$SHIM_LOG"
}

@test "--image-repo selects the repository for the registry check" {
    export SHIM_TAGS="example.org/mirror/byro:v2026.3.0"
    run "$SCRIPT" v2026.3.0 --image-repo example.org/mirror/byro
    [ "$status" -eq 0 ]
    grep -q "docker manifest inspect example.org/mirror/byro:v2026.3.0" "$SHIM_LOG"
    git -C "$ORIGIN" log -1 --format=%b stable | grep -q 'Image: example.org/mirror/byro:v2026.3.0'
}

@test "--no-image-check skips the registry" {
    export SHIM_TAGS=""
    run "$SCRIPT" v2026.3.0 --no-image-check
    [ "$status" -eq 0 ]
    ! grep -q "manifest" "$SHIM_LOG"
    stable_exists
}

@test "install.sh that does not match the tag's SHA256SUMS is refused" {
    printf '%s  install.sh\n' "$(printf '0%.0s' {1..64})" >deploy/SHA256SUMS
    git commit -q -am "stale checksums"
    git tag v2026.6.0
    git push -q origin main refs/tags/v2026.6.0
    export SHIM_TAGS="$SHIM_TAGS $IMAGE:v2026.6.0"
    run "$SCRIPT" v2026.6.0
    [ "$status" -ne 0 ]
    [[ "$output" == *"does not match its SHA256SUMS"* ]]
    ! stable_exists
}

@test "--dry-run shows the commit and pushes nothing" {
    run "$SCRIPT" v2026.3.0 --dry-run
    [ "$status" -eq 0 ]
    [[ "$output" == *"dry run: would push"* ]]
    [[ "$output" == *"install.sh"* ]]
    ! stable_exists
}

@test "a tag that is missing locally is fetched from the remote" {
    git tag -d v2026.4.0 >/dev/null
    run "$SCRIPT" v2026.4.0
    [ "$status" -eq 0 ]
    [[ "$output" == *"fetching tag v2026.4.0"* ]]
    stable_file stable.env | grep -qx 'BYRO_RELEASE_VERSION=v2026.4.0'
}

@test "a stable branch written from another checkout is continued, not rewritten" {
    "$SCRIPT" v2026.3.0
    git clone -q "$ORIGIN" "$BATS_TEST_TMPDIR/clone2"
    cd "$BATS_TEST_TMPDIR/clone2"
    run "$SCRIPT" v2026.4.0
    [ "$status" -eq 0 ]
    [ "$(stable_count)" -eq 2 ]
    git -C "$ORIGIN" log --format=%s stable | tail -n1 | grep -qx 'stable: point to v2026.3.0'
}

@test "the generated stable.env is accepted by install.sh" {
    "$SCRIPT" v2026.3.0
    stable_file stable.env >"$BATS_TEST_TMPDIR/stable.env"
    export BYROCTL_RAW_BASE="https://example.test"
    BYROCTL_STABLE_FILE="$BATS_TEST_TMPDIR/stable.env" run "$DEPLOY_DIR/install.sh" --root "$BATS_TEST_TMPDIR/byro" --dry-run
    [ "$status" -eq 0 ]
    [[ "$output" == *"current stable byro release: v2026.3.0"* ]]
}
