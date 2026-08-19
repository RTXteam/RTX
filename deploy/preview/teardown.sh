#!/usr/bin/env bash
#
# Remove one ARAX preview environment. Safe to run repeatedly and safe to run
# for a PR that was never deployed.
#
# Usage: teardown.sh <PR>
#
# Issue #2846.

set -o nounset -o pipefail -o errexit

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
. "${SCRIPT_DIR}/lib.sh"

[ "$#" -ge 1 ] || { printf 'Usage: teardown.sh <PR>\n' >&2; exit 2; }

PR="$1"
require_int "${PR}" "PR number"

PORT="$(preview_port "${PR}")"
CONTAINER="$(preview_container "${PR}")"
IMAGE="$(preview_image "${PR}")"
NGINX_CONF="$(preview_nginx_conf "${PR}")"

REMOVED=()

log "tearing down the preview for PR ${PR}"

if ${DOCKER} rm -f "${CONTAINER}" >/dev/null 2>&1; then
    REMOVED+=("container ${CONTAINER}")
else
    log "no container ${CONTAINER}"
fi

if ${DOCKER} rmi -f "${IMAGE}" >/dev/null 2>&1; then
    REMOVED+=("image ${IMAGE}")
else
    log "no image ${IMAGE}"
fi

NGINX_TOUCHED="no"
if ${SUDO} test -d "${PREVIEW_NGINX_DIR}"; then
    if ${SUDO} test -f "${NGINX_CONF}"; then
        ${SUDO} rm -f "${NGINX_CONF}"
        REMOVED+=("nginx snippet ${NGINX_CONF}")
        NGINX_TOUCHED="yes"
    else
        log "no nginx snippet ${NGINX_CONF}"
    fi

    # The shared autocomplete snippet may still point at the preview we just
    # deleted. The container is already gone, so newest_preview_pr cannot pick
    # this PR again.
    CURRENT_RTXCOMPLETE_PORT="$(rtxcomplete_conf_port)"
    if [ "${CURRENT_RTXCOMPLETE_PORT}" = "${PORT}" ]; then
        NEWEST="$(newest_preview_pr)"
        if [ -n "${NEWEST}" ]; then
            write_rtxcomplete_conf "$(preview_port "${NEWEST}")" "${NEWEST}"
            REMOVED+=("repointed /rtxcomplete/ at PR ${NEWEST}")
        else
            write_rtxcomplete_conf ""
            REMOVED+=("removed the shared /rtxcomplete/ snippet, no previews left")
        fi
        NGINX_TOUCHED="yes"
    fi

    if [ "${NGINX_TOUCHED}" = "yes" ]; then
        nginx_reload || log "WARNING: nginx did not reload cleanly, inspect the host by hand"
    fi
else
    log "WARNING: ${PREVIEW_NGINX_DIR} does not exist, skipping the nginx cleanup"
fi

if [ "${#REMOVED[@]}" -eq 0 ]; then
    printf 'Nothing to remove for PR %s.\n' "${PR}"
else
    printf 'Removed for PR %s:\n' "${PR}"
    for item in "${REMOVED[@]}"; do
        printf '  - %s\n' "${item}"
    done
fi
