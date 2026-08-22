# shellcheck shell=bash
#
# Shared helpers for the per-PR ARAX preview environments on cicd.rtx.ai.
# Issue #2846.
#
# This file is sourced, never executed. Callers own the shell options
# (set -o nounset -o pipefail -o errexit) so that sourcing this file cannot
# change the behaviour of an interactive shell.

# Absolute location of this library, so the scripts work no matter where they
# are invoked from. We never rely on $PWD.
PREVIEW_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# deploy/preview -> repository root is two levels up
REPO_ROOT="$(cd "${PREVIEW_LIB_DIR}/../.." && pwd)"
export PREVIEW_LIB_DIR REPO_ROOT

# ---------------------------------------------------------------------------
# Defaults. Every one of these can be overridden from the environment.
# ---------------------------------------------------------------------------

# Public path prefix in front of the PR number. Empty means PR 2853 is served
# at /2853/. Setting it to "pr-" yields /pr-2853/.
PREVIEW_PATH_PREFIX="${PREVIEW_PATH_PREFIX:-}"
# Host port for a preview is PREVIEW_PORT_BASE + PR number, bound to loopback.
PREVIEW_PORT_BASE="${PREVIEW_PORT_BASE:-10000}"
# Directory of per-PR nginx snippets, included from the 443 server block.
PREVIEW_NGINX_DIR="${PREVIEW_NGINX_DIR:-/etc/nginx/arax-preview.d}"
# Scheme and host the previews are reachable at from the outside.
PREVIEW_PUBLIC_BASE_URL="${PREVIEW_PUBLIC_BASE_URL:-https://cicd.rtx.ai}"
# Host paths bind-mounted into every preview container, same as pytest.yml.
PREVIEW_DB_DIR="${PREVIEW_DB_DIR:-/mnt/data/orangeboard/databases}"
PREVIEW_CONFIG_SECRETS="${PREVIEW_CONFIG_SECRETS:-/mnt/config/config_secrets.json}"
# Garbage collection age limit in days.
PREVIEW_TTL_DAYS="${PREVIEW_TTL_DAYS:-7}"
# Seconds to wait for the ARAX Flask service to answer /status after start.
PREVIEW_HEALTH_TIMEOUT="${PREVIEW_HEALTH_TIMEOUT:-900}"
# Same wait for a fast redeploy. The image, the databases and the KP info cache
# are already in place there, so only the Flask services have to come back.
PREVIEW_FAST_HEALTH_TIMEOUT="${PREVIEW_FAST_HEALTH_TIMEOUT:-180}"
# Repository the previews are built from. CICD-Dockerfile clones this by name.
PREVIEW_REPO="${PREVIEW_REPO:-RTXteam/RTX}"
# Docker build context and Dockerfile. The workflow points these at a checkout
# of the PR head so that a PR can change the Dockerfile itself, while the
# scripts run from the trusted default branch copy.
PREVIEW_BUILD_CONTEXT="${PREVIEW_BUILD_CONTEXT:-${REPO_ROOT}/DockerBuild}"
PREVIEW_DOCKERFILE="${PREVIEW_DOCKERFILE:-${PREVIEW_BUILD_CONTEXT}/CICD-Dockerfile}"

# The runner user on cicd.rtx.ai has passwordless sudo and the existing
# pytest.yml workflow already shells out to "sudo docker", so we do the same.
DOCKER="${DOCKER:-sudo docker}"
# Note the ${SUDO-sudo} form rather than ${SUDO:-sudo}: setting SUDO to an
# empty string is a supported way to say "this shell is already root".
SUDO="${SUDO-sudo}"

export PREVIEW_PATH_PREFIX PREVIEW_PORT_BASE PREVIEW_NGINX_DIR \
    PREVIEW_PUBLIC_BASE_URL PREVIEW_DB_DIR PREVIEW_CONFIG_SECRETS \
    PREVIEW_TTL_DAYS PREVIEW_HEALTH_TIMEOUT PREVIEW_FAST_HEALTH_TIMEOUT PREVIEW_REPO \
    PREVIEW_BUILD_CONTEXT PREVIEW_DOCKERFILE DOCKER SUDO

# Name of the shared autocomplete snippet. Leading underscore keeps it sorted
# ahead of the numeric per-PR files, which is only cosmetic.
PREVIEW_RTXCOMPLETE_CONF="${PREVIEW_NGINX_DIR}/_rtxcomplete.conf"
export PREVIEW_RTXCOMPLETE_CONF

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

# Logs go to stderr so that stdout stays clean for tables and summaries that
# get pasted into PR comments.
log() {
    printf '[%s] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*" >&2
}

die() {
    printf '[%s] ERROR: %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*" >&2
    exit 1
}

# ---------------------------------------------------------------------------
# Naming helpers
# ---------------------------------------------------------------------------

# require_int <value> <name>
# Fails unless the value is a positive integer with no leading sign or zero.
require_int() {
    local value="${1:-}"
    local name="${2:-value}"
    case "${value}" in
        ''|*[!0-9]*) die "${name} must be a positive integer, got '${value}'" ;;
    esac
    if [ "${value}" -le 0 ] 2>/dev/null; then
        die "${name} must be a positive integer, got '${value}'"
    fi
}

preview_port() {
    local pr="${1:-}"
    require_int "${pr}" "PR number"
    printf '%s\n' "$(( PREVIEW_PORT_BASE + pr ))"
}

preview_container() {
    local pr="${1:-}"
    require_int "${pr}" "PR number"
    printf 'rtx_pr_%s\n' "${pr}"
}

preview_image() {
    local pr="${1:-}"
    require_int "${pr}" "PR number"
    printf 'rtx:pr-%s\n' "${pr}"
}

# Public path without a trailing slash, for example /2853 or /pr-2853.
preview_path() {
    local pr="${1:-}"
    require_int "${pr}" "PR number"
    printf '/%s%s\n' "${PREVIEW_PATH_PREFIX}" "${pr}"
}

# Public URL with a trailing slash, which is what a browser needs.
preview_url() {
    local pr="${1:-}"
    require_int "${pr}" "PR number"
    printf '%s/%s%s/\n' "${PREVIEW_PUBLIC_BASE_URL%/}" "${PREVIEW_PATH_PREFIX}" "${pr}"
}

preview_nginx_conf() {
    local pr="${1:-}"
    require_int "${pr}" "PR number"
    printf '%s/%s%s.conf\n' "${PREVIEW_NGINX_DIR}" "${PREVIEW_PATH_PREFIX}" "${pr}"
}

# ---------------------------------------------------------------------------
# nginx helpers
# ---------------------------------------------------------------------------

# Validates the whole nginx configuration before reloading, so a broken
# preview snippet can never take down the site. Returns non-zero on failure
# instead of exiting, so callers can roll back first.
nginx_reload() {
    if ! ${SUDO} nginx -t; then
        log "nginx -t failed, not reloading"
        return 1
    fi
    if ! ${SUDO} systemctl reload nginx; then
        log "systemctl reload nginx failed"
        return 1
    fi
    log "nginx reloaded"
    return 0
}

# write_rtxcomplete_conf <port|"">
# The ARAX UI loads /rtxcomplete/ with a root absolute path, so every preview
# on the box has to share one autocomplete backend. We point it at whichever
# preview was deployed most recently. An empty port removes the snippet.
write_rtxcomplete_conf() {
    local port="${1:-}"
    if [ -z "${port}" ]; then
        ${SUDO} rm -f "${PREVIEW_RTXCOMPLETE_CONF}"
        log "removed shared ${PREVIEW_RTXCOMPLETE_CONF}"
        return 0
    fi
    require_int "${port}" "port"
    local pr_note="${2:-}"
    ${SUDO} tee "${PREVIEW_RTXCOMPLETE_CONF}" >/dev/null <<RTXCOMPLETE_EOF
# managed by deploy/preview/*.sh. The ARAX UI references /rtxcomplete/ root-absolute,
# so all previews share the autocomplete service of the most recently deployed preview (PR ${pr_note}).
location /rtxcomplete/ {
    proxy_pass http://127.0.0.1:${port}/rtxcomplete/;
    proxy_read_timeout 300s;
    proxy_buffering off;
    proxy_set_header Host \$host;
}
RTXCOMPLETE_EOF
    log "wrote shared ${PREVIEW_RTXCOMPLETE_CONF} pointing at port ${port}"
}

# Reads the upstream port currently configured in the shared snippet, or
# nothing if the snippet is absent.
rtxcomplete_conf_port() {
    # The trailing "|| true" matters: callers run with errexit and pipefail, and
    # a missing snippet has to read as "no port", not as a fatal error.
    ${SUDO} cat "${PREVIEW_RTXCOMPLETE_CONF}" 2>/dev/null \
        | sed -n 's|^ *proxy_pass http://127\.0\.0\.1:\([0-9][0-9]*\)/rtxcomplete/;.*|\1|p' \
        | head -n 1 || true
}

# ---------------------------------------------------------------------------
# Container inventory
# ---------------------------------------------------------------------------

# All PR numbers that have a preview container, running or not.
list_preview_prs() {
    ${DOCKER} ps -a --filter 'label=arax.preview=true' \
        --format '{{.Label "arax.preview.pr"}}' 2>/dev/null \
        | grep -E '^[0-9]+$' || true
}

# Reads one label off a preview container. Prints nothing if absent.
preview_label() {
    local pr="${1:-}"
    local key="${2:-}"
    local container
    container="$(preview_container "${pr}")"
    ${DOCKER} inspect --format "{{index .Config.Labels \"${key}\"}}" "${container}" 2>/dev/null || true
}

# container_running <name>
# True when the container exists and is running. Anything else, including a
# missing container, is false rather than an error, so callers under errexit
# can branch on it with a plain if.
container_running() {
    local name="${1:-}"
    [ -n "${name}" ] || return 1
    local state
    state="$(${DOCKER} inspect --format '{{.State.Running}}' "${name}" 2>/dev/null || true)"
    [ "${state}" = "true" ]
}

# PR number of the running preview with the largest creation timestamp, or
# nothing when no preview is running.
newest_preview_pr() {
    # As above: grep exits 1 when no preview is running, and with pipefail that
    # would abort the caller instead of simply printing nothing.
    ${DOCKER} ps --filter 'label=arax.preview=true' \
        --format '{{.Label "arax.preview.created"}} {{.Label "arax.preview.pr"}}' 2>/dev/null \
        | grep -E '^[0-9]+ [0-9]+$' \
        | sort -k1,1n \
        | tail -n 1 \
        | awk '{print $2}' || true
}
