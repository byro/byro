# Shared bats helpers for the byroctl test suite.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
DEPLOY_DIR="$REPO_ROOT/deploy"
SHIM_BIN="$DEPLOY_DIR/tests/helpers/bin"

# Source byroctl so that single functions can be tested. main() is guarded and
# not executed on source; set -e is only enabled inside main().
load_byroctl() {
    # shellcheck disable=SC1091
    source "$DEPLOY_DIR/byroctl"
}

# A fresh installation root for a test.
make_root() {
    BYRO_ROOT="$(mktemp -d "$BATS_TEST_TMPDIR/root.XXXXXX")"
    CONF_FILE="$BYRO_ROOT/byro.conf"
    export BYRO_ROOT CONF_FILE
}

# Put the docker/curl shims first in PATH and reset their state.
use_shims() {
    export PATH="$SHIM_BIN:$PATH"
    export SHIM_LOG="$BATS_TEST_TMPDIR/shim.log"
    : >"$SHIM_LOG"
    export SHIM_TAGS="${SHIM_TAGS:-}"          # space separated refs that "exist" in the registry
    export SHIM_LOCAL_IMAGES="${SHIM_LOCAL_IMAGES:-}"   # refs that exist locally
    export SHIM_DIGESTS="${SHIM_DIGESTS:-}"    # lines "ref repo@sha256:..." for image inspect
    export SHIM_HEALTH="${SHIM_HEALTH:-healthy}"
    export SHIM_SUPERUSER_EXISTS="${SHIM_SUPERUSER_EXISTS:-0}"   # 1 = superuser exists
    export SHIM_SERVICES="${SHIM_SERVICES:-web periodic db}"
}

# run byroctl as a program (fresh process), with the shims.
byroctl() {
    "$DEPLOY_DIR/byroctl" "$@"
}

have_real_docker() {
    command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1
}
