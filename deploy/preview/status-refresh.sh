#!/usr/bin/env bash
#
# Rewrite the preview status page at ${PREVIEW_WEB_ROOT}/index.html.
#
# The page is regenerated on every deploy, teardown and garbage collection
# run, but the host numbers on it go stale between those, and a container that
# died on its own would keep showing as running. Cron runs this every 5
# minutes so the page is never far behind the box it describes.
#
# Usage: status-refresh.sh
#
# Installed into cron by install-nginx-include.sh. Issue #2846.

set -o nounset -o pipefail -o errexit

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
. "${SCRIPT_DIR}/lib.sh"
preview_validate_env

usage() {
    cat >&2 <<'USAGE_EOF'
Usage: status-refresh.sh

Rewrites the preview status page. Takes no arguments. Meant for cron, and
safe to run by hand at any time.
USAGE_EOF
    exit 2
}

if [ "$#" -gt 0 ]; then
    case "${1}" in
        -h|--help) usage ;;
        *) usage ;;
    esac
fi

write_status_page
log "status page refreshed"
