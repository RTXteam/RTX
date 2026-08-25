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

# Resource guards. One preview must never be able to take the whole box down.
# The memory ceiling for a preview container: an ARAX container idles at about
# 400 MB and was measured at 1889 MiB peak while answering queries, so 2g is
# the floor here. Anything lower gets the container killed by the kernel in
# the middle of a query.
PREVIEW_MEMORY_LIMIT="${PREVIEW_MEMORY_LIMIT:-2g}"
# CPU ceiling for a preview container. The host has 2 vCPUs and a pathfinder
# query saturates both, so 1.5 leaves half a core for nginx and the runner.
PREVIEW_CPU_LIMIT="${PREVIEW_CPU_LIMIT:-1.5}"
# How many previews may live on the host at once. A redeploy of a pull request
# that already has a container never counts against this.
PREVIEW_MAX_ACTIVE="${PREVIEW_MAX_ACTIVE:-3}"
# Refuse to build below this much free space on the docker root. The floor is
# the larger of the absolute value and the percentage of the volume size, so
# it scales with the host: one preview image is about 3.94 GB, and on the
# 485 GB root of cicd.rtx.ai the percentage wins at about 48 GB.
PREVIEW_MIN_FREE_DISK_GB="${PREVIEW_MIN_FREE_DISK_GB:-10}"
PREVIEW_MIN_FREE_DISK_PCT="${PREVIEW_MIN_FREE_DISK_PCT:-10}"
# Refuse to start a container below this much available memory on the host.
PREVIEW_MIN_FREE_RAM_MB="${PREVIEW_MIN_FREE_RAM_MB:-2048}"

# Document root of the status page served at /previews/. The per-PR files the
# page embeds live under ${PREVIEW_WEB_ROOT}/data/<PR>/.
PREVIEW_WEB_ROOT="${PREVIEW_WEB_ROOT:-/var/www/arax-preview}"
# Full deploy logs, one file per deploy run, pruned by gc.sh after 30 days.
PREVIEW_LOG_DIR="${PREVIEW_LOG_DIR:-/var/log/arax-preview}"

# The runner user on cicd.rtx.ai has passwordless sudo and the existing
# pytest.yml workflow already shells out to "sudo docker", so we do the same.
DOCKER="${DOCKER:-sudo docker}"
# Note the ${SUDO-sudo} form rather than ${SUDO:-sudo}: setting SUDO to an
# empty string is a supported way to say "this shell is already root".
SUDO="${SUDO-sudo}"

export PREVIEW_PATH_PREFIX PREVIEW_PORT_BASE PREVIEW_NGINX_DIR \
    PREVIEW_PUBLIC_BASE_URL PREVIEW_DB_DIR PREVIEW_CONFIG_SECRETS \
    PREVIEW_TTL_DAYS PREVIEW_HEALTH_TIMEOUT PREVIEW_FAST_HEALTH_TIMEOUT PREVIEW_REPO \
    PREVIEW_BUILD_CONTEXT PREVIEW_DOCKERFILE DOCKER SUDO \
    PREVIEW_MEMORY_LIMIT PREVIEW_CPU_LIMIT PREVIEW_MAX_ACTIVE \
    PREVIEW_MIN_FREE_DISK_GB PREVIEW_MIN_FREE_DISK_PCT PREVIEW_MIN_FREE_RAM_MB \
    PREVIEW_WEB_ROOT PREVIEW_LOG_DIR

# Name of the shared autocomplete snippet. Leading underscore keeps it sorted
# ahead of the numeric per-PR files, which is only cosmetic.
PREVIEW_RTXCOMPLETE_CONF="${PREVIEW_NGINX_DIR}/_rtxcomplete.conf"
# The snippet that serves the status page at /previews/ and redirects the bare
# root to it. Also sorted ahead of the per-PR files by its leading underscore.
PREVIEW_STATUS_CONF="${PREVIEW_NGINX_DIR}/_previews.conf"
export PREVIEW_RTXCOMPLETE_CONF PREVIEW_STATUS_CONF

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

# Logs go to stderr so that stdout stays clean for tables and summaries that
# get pasted into PR comments.
log() {
    printf '[%s] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*" >&2
}

# The reason the most recent die() gave. An EXIT trap can read it and put the
# reason where a human sees it, rather than reporting a bare exit status. Only
# a die() reached in this shell sets it, so a caller must have a fallback for
# the case where the failure happened inside a subshell.
PREVIEW_LAST_ERROR=""

die() {
    # Read by the EXIT trap in deploy.sh, which shellcheck cannot see from here.
    # shellcheck disable=SC2034
    PREVIEW_LAST_ERROR="$*"
    printf '[%s] ERROR: %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*" >&2
    exit 1
}

# ---------------------------------------------------------------------------
# Naming helpers
# ---------------------------------------------------------------------------

# preview_validate_env
# Every numeric knob can be overridden from the environment, and a typo there
# must fail here, before any work happens, with the variable named. Without
# this a bad value would abort six minutes into a build with a bash
# arithmetic error that names nothing.
preview_validate_env() {
    local pair name value
    for pair in \
        "PREVIEW_PORT_BASE=${PREVIEW_PORT_BASE}" \
        "PREVIEW_TTL_DAYS=${PREVIEW_TTL_DAYS}" \
        "PREVIEW_HEALTH_TIMEOUT=${PREVIEW_HEALTH_TIMEOUT}" \
        "PREVIEW_FAST_HEALTH_TIMEOUT=${PREVIEW_FAST_HEALTH_TIMEOUT}" \
        "PREVIEW_MAX_ACTIVE=${PREVIEW_MAX_ACTIVE}" \
        "PREVIEW_MIN_FREE_DISK_GB=${PREVIEW_MIN_FREE_DISK_GB}" \
        "PREVIEW_MIN_FREE_DISK_PCT=${PREVIEW_MIN_FREE_DISK_PCT}" \
        "PREVIEW_MIN_FREE_RAM_MB=${PREVIEW_MIN_FREE_RAM_MB}"; do
        name="${pair%%=*}"
        value="${pair#*=}"
        case "${value}" in
            ''|*[!0-9]*) die "${name} must be a positive integer, got '${value}'" ;;
        esac
    done
}

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

# ---------------------------------------------------------------------------
# Status page data files
# ---------------------------------------------------------------------------

# Directory the status page reads the per-PR reports from.
preview_data_dir() {
    local pr="${1:-}"
    require_int "${pr}" "PR number"
    printf '%s/data/%s\n' "${PREVIEW_WEB_ROOT}" "${pr}"
}

# write_preview_data <PR> <filename>
# Copies stdin into the per-PR data directory the status page embeds. Best
# effort on purpose: these files are a convenience, so a failure is logged as
# a warning and never propagated to the caller. Stdin is always drained, even
# when nothing is written, so the producer never sees a broken pipe.
write_preview_data() {
    local pr="${1:-}"
    local name="${2:-}"
    local dir
    case "${pr}" in
        ''|*[!0-9]*)
            cat >/dev/null
            return 0
            ;;
    esac
    if [ -z "${name}" ] || [ -z "${PREVIEW_WEB_ROOT}" ]; then
        cat >/dev/null
        return 0
    fi
    dir="${PREVIEW_WEB_ROOT}/data/${pr}"
    if ! ${SUDO} mkdir -p "${dir}" 2>/dev/null; then
        cat >/dev/null
        log "WARNING: could not create ${dir}, not saving ${name}"
        return 0
    fi
    # World readable, because the page generator and nginx both read these as
    # somebody other than root.
    ${SUDO} chmod 755 "${PREVIEW_WEB_ROOT}" "${PREVIEW_WEB_ROOT}/data" "${dir}" 2>/dev/null || true
    if ! ${SUDO} tee "${dir}/${name}" >/dev/null; then
        log "WARNING: could not write ${dir}/${name}"
        return 0
    fi
    ${SUDO} chmod 644 "${dir}/${name}" 2>/dev/null || true
    return 0
}

# ---------------------------------------------------------------------------
# Per-PR run state
# ---------------------------------------------------------------------------

# The four stages of a preview run, in the order the status page shows them.
PREVIEW_STAGES="deploy smoke pytest queries"
# A run that is still marked running after this long was killed without ever
# getting to write its own result, so the page stops spinning for it.
PREVIEW_STATE_STALE_SECONDS="${PREVIEW_STATE_STALE_SECONDS:-7200}"
export PREVIEW_STAGES PREVIEW_STATE_STALE_SECONDS

# write_preview_state <PR> <stage> <status> [detail]
# Merges one stage transition into ${PREVIEW_WEB_ROOT}/data/<PR>/state.json,
# the file the status page reads to draw a card for a preview whose container
# does not exist yet. The stage is one of PREVIEW_STAGES and the status is one
# of pending, running, done, failed.
#
# The top level fields are carried in the environment rather than in more
# positional arguments, so that the common call stays three words long:
#   PREVIEW_STATE_RESET     1 starts a fresh document, which is what a new
#                           deploy wants so the previous run's results do not
#                           linger next to a build that has just started
#   PREVIEW_STATE_BRANCH    branch the preview is built from
#   PREVIEW_STATE_SHA       commit the preview is built from
#   PREVIEW_STATE_COMMAND   deploy or redeploy, the comment that started it
#
# Best effort throughout, exactly like write_preview_data: the page is a
# convenience and must never be able to fail a deploy or a test run.
write_preview_state() {
    local pr="${1:-}"
    local stage="${2:-}"
    local status="${3:-}"
    local detail="${4:-}"
    local current merged
    case "${pr}" in
        ''|*[!0-9]*) return 0 ;;
    esac
    if [ -z "${PREVIEW_WEB_ROOT}" ] || [ -z "${stage}" ] || [ -z "${status}" ]; then
        return 0
    fi

    current="$(${SUDO} cat "${PREVIEW_WEB_ROOT}/data/${pr}/state.json" 2>/dev/null || true)"

    if ! merged="$(printf '%s' "${current}" \
        | PREVIEW_STATE_PR="${pr}" \
          PREVIEW_STATE_NAME="${stage}" \
          PREVIEW_STATE_STATUS="${status}" \
          PREVIEW_STATE_DETAIL="${detail}" \
          PREVIEW_STAGES="${PREVIEW_STAGES}" \
          python3 -c '
import json
import os
import sys
import time

STATES = ("pending", "running", "done", "failed")
stages_wanted = os.environ.get("PREVIEW_STAGES", "").split()

raw = sys.stdin.read()
doc = {}
if raw.strip() and os.environ.get("PREVIEW_STATE_RESET") != "1":
    try:
        doc = json.loads(raw)
    except Exception:
        doc = {}
if not isinstance(doc, dict):
    doc = {}

stages = doc.get("stages")
if not isinstance(stages, dict):
    stages = {}
for name in stages_wanted:
    entry = stages.get(name)
    if not isinstance(entry, dict):
        stages[name] = {
            "status": "pending",
            "started_at": None,
            "finished_at": None,
            "detail": "",
        }

# The identity of the run. Written once by deploy.sh and left alone by every
# later caller, so a smoke test cannot blank out the branch name.
for key, variable in (
    ("pr", "PREVIEW_STATE_PR"),
    ("branch", "PREVIEW_STATE_BRANCH"),
    ("sha", "PREVIEW_STATE_SHA"),
    ("command", "PREVIEW_STATE_COMMAND"),
):
    value = os.environ.get(variable, "").strip()
    if value:
        doc[key] = value

now = int(time.time())
name = os.environ.get("PREVIEW_STATE_NAME", "").strip()
status = os.environ.get("PREVIEW_STATE_STATUS", "").strip()
detail = os.environ.get("PREVIEW_STATE_DETAIL", "").strip()
if name in stages and status in STATES:
    entry = stages[name]
    entry["status"] = status
    entry["detail"] = detail
    if status == "running":
        entry["started_at"] = now
        entry["finished_at"] = None
    elif status == "pending":
        entry["started_at"] = None
        entry["finished_at"] = None
    else:
        if not entry.get("started_at"):
            entry["started_at"] = now
        entry["finished_at"] = now

doc["stages"] = stages
doc["updated_at"] = now
sys.stdout.write(json.dumps(doc, indent=2, sort_keys=True) + "\n")
')"; then
        log "WARNING: could not update the run state of PR ${pr}"
        return 0
    fi

    printf '%s\n' "${merged}" | write_preview_data "${pr}" "state.json"
    return 0
}

# expire_stale_preview_states
# A deploy that was killed between "running" and its result would spin on the
# page forever. Every time the page is generated, any stage still marked
# running after PREVIEW_STATE_STALE_SECONDS is written down as failed with the
# detail "abandoned", so the card tells the truth without a human touching the
# host. Best effort, and silent when there is nothing to do.
expire_stale_preview_states() {
    local data_dir file pr updated
    data_dir="${PREVIEW_WEB_ROOT}/data"
    [ -n "${PREVIEW_WEB_ROOT}" ] || return 0
    [ -d "${data_dir}" ] || return 0
    for file in "${data_dir}"/*/state.json; do
        [ -f "${file}" ] || continue
        pr="$(basename "$(dirname "${file}")")"
        case "${pr}" in
            ''|*[!0-9]*) continue ;;
        esac
        updated="$(${SUDO} cat "${file}" 2>/dev/null \
            | PREVIEW_STATE_STALE_SECONDS="${PREVIEW_STATE_STALE_SECONDS}" python3 -c '
import json
import os
import sys
import time

try:
    limit = int(os.environ.get("PREVIEW_STATE_STALE_SECONDS", "7200"))
except ValueError:
    limit = 7200

try:
    doc = json.load(sys.stdin)
except Exception:
    sys.exit(0)
if not isinstance(doc, dict):
    sys.exit(0)

stages = doc.get("stages")
if not isinstance(stages, dict):
    sys.exit(0)

now = int(time.time())
changed = False
for name in sorted(stages):
    entry = stages[name]
    if not isinstance(entry, dict) or entry.get("status") != "running":
        continue
    started = entry.get("started_at") or doc.get("updated_at") or 0
    try:
        started = int(started)
    except (TypeError, ValueError):
        started = 0
    if started and now - started <= limit:
        continue
    entry["status"] = "failed"
    entry["detail"] = "abandoned"
    entry["finished_at"] = now
    changed = True

if changed:
    doc["updated_at"] = now
    sys.stdout.write(json.dumps(doc, indent=2, sort_keys=True) + "\n")
' || true)"
        [ -n "${updated}" ] || continue
        log "PR ${pr} had a stage still running after ${PREVIEW_STATE_STALE_SECONDS}s, marking it abandoned"
        printf '%s\n' "${updated}" | write_preview_data "${pr}" "state.json"
    done
    return 0
}

# ---------------------------------------------------------------------------
# Host measurements
#
# One collector per number, each printing its value on stdout and printing
# nothing at all when it cannot read it. Both readers of the host numbers use
# these: write_status_page for the page it renders, and host-stats.sh for the
# host.json it rewrites every 15 seconds. Neither parses anything itself, so
# the page and the live tiles can never disagree about what free means.
# ---------------------------------------------------------------------------

# Prints "<available> <total>" in MB. The available column rather than the free
# one, same as the preflight check, because page cache is reclaimable.
host_mem_mb() {
    local line avail total
    line="$(free -m 2>/dev/null | awk '/^Mem:/{print $7, $2}' || true)"
    avail="$(printf '%s' "${line}" | awk '{print $1}' | tr -dc '0-9')"
    total="$(printf '%s' "${line}" | awk '{print $2}' | tr -dc '0-9')"
    if [ -n "${avail}" ] && [ -n "${total}" ]; then
        printf '%s %s\n' "${avail}" "${total}"
    fi
    return 0
}

# Prints "<size> <available>" in GB for the volume docker stores its images
# on, which is the same call the preflight check makes.
host_disk_gb() {
    local line size avail
    line="$(df -BG --output=size,avail /var/lib/docker 2>/dev/null \
        || df -BG --output=size,avail / 2>/dev/null || true)"
    line="$(printf '%s' "${line}" | tail -n 1)"
    size="$(printf '%s' "${line}" | awk '{print $1}' | tr -dc '0-9')"
    avail="$(printf '%s' "${line}" | awk '{print $2}' | tr -dc '0-9')"
    if [ -n "${size}" ] && [ -n "${avail}" ]; then
        printf '%s %s\n' "${size}" "${avail}"
    fi
    return 0
}

# Prints "<1m> <5m> <15m>". /proc/loadavg on the host, and uptime as a fallback
# so the collector still has something to say on a developer machine.
host_load() {
    local one five fifteen rest line
    if [ -r /proc/loadavg ]; then
        read -r one five fifteen rest < /proc/loadavg || true
        case "${one}:${five}:${fifteen}" in
            *[!0-9.:]*|*::*) : ;;
            *)
                printf '%s %s %s\n' "${one}" "${five}" "${fifteen}"
                return 0
                ;;
        esac
    fi
    # LC_ALL=C so a host with a comma decimal separator cannot turn one number
    # into two, and tr so that both the Linux form, "1.20, 1.30, 1.40", and the
    # BSD form, "1.20 1.30 1.40", come out as three fields.
    line="$(LC_ALL=C uptime 2>/dev/null | sed -n 's/.*load average[s]*: *//p' | tr ',' ' ' || true)"
    one="$(printf '%s' "${line}" | awk '{print $1}')"
    five="$(printf '%s' "${line}" | awk '{print $2}')"
    fifteen="$(printf '%s' "${line}" | awk '{print $3}')"
    case "${one}:${five}:${fifteen}" in
        *[!0-9.:]*|*::*|:*|*:) return 0 ;;
    esac
    printf '%s %s %s\n' "${one}" "${five}" "${fifteen}"
    return 0
}

# How many previews are on the box, running or not. The same set the garbage
# collector and the preflight count walk.
host_slots_used() {
    local used
    used="$(list_preview_prs | sort -n -u | wc -l | tr -dc '0-9' || true)"
    if [ -n "${used}" ]; then
        printf '%s\n' "${used}"
    fi
    return 0
}

# One tab separated "<name> <memory usage> <cpu percent>" line per preview
# container. docker stats can hang for a long time on a wedged daemon and this
# runs on the path of every deploy, so it gets a hard time limit and the table
# is dropped rather than waited for.
host_container_stats() {
    local raw
    if command -v timeout >/dev/null 2>&1; then
        # DOCKER is "sudo docker", two words on purpose, so it has to split.
        # shellcheck disable=SC2086
        raw="$(timeout 20 ${DOCKER} stats --no-stream \
            --format '{{.Name}}\t{{.MemUsage}}\t{{.CPUPerc}}' 2>/dev/null || true)"
    else
        raw="$(${DOCKER} stats --no-stream \
            --format '{{.Name}}\t{{.MemUsage}}\t{{.CPUPerc}}' 2>/dev/null || true)"
    fi
    printf '%s\n' "${raw}" | grep '^rtx_' || true
    return 0
}

# collect_host_stats
# Reads the host numbers the status page shows into HOST_* variables and
# exports them, because the python that renders the page must not shell out.
# Every collector is best effort: one that cannot read its number leaves the
# variable empty and the page shows that tile as having no data.
collect_host_stats() {
    local mem disk load

    mem="$(host_mem_mb)"
    HOST_MEM_AVAIL_MB="$(printf '%s' "${mem}" | awk '{print $1}')"
    HOST_MEM_TOTAL_MB="$(printf '%s' "${mem}" | awk '{print $2}')"

    disk="$(host_disk_gb)"
    HOST_DISK_SIZE_GB="$(printf '%s' "${disk}" | awk '{print $1}')"
    HOST_DISK_AVAIL_GB="$(printf '%s' "${disk}" | awk '{print $2}')"

    load="$(host_load)"
    HOST_LOAD_1="$(printf '%s' "${load}" | awk '{print $1}')"
    HOST_LOAD_5="$(printf '%s' "${load}" | awk '{print $2}')"
    HOST_LOAD_15="$(printf '%s' "${load}" | awk '{print $3}')"

    HOST_SLOTS_USED="$(host_slots_used)"
    HOST_SLOTS_MAX="${PREVIEW_MAX_ACTIVE}"
    HOST_CONTAINER_STATS="$(host_container_stats)"

    export HOST_MEM_AVAIL_MB HOST_MEM_TOTAL_MB HOST_DISK_AVAIL_GB HOST_DISK_SIZE_GB \
        HOST_LOAD_1 HOST_LOAD_5 HOST_LOAD_15 HOST_SLOTS_USED HOST_SLOTS_MAX \
        HOST_CONTAINER_STATS
}

# ---------------------------------------------------------------------------
# Status page
# ---------------------------------------------------------------------------

# write_status_page
# Regenerates ${PREVIEW_WEB_ROOT}/index.html from the docker labels of every
# preview container on the box, the host numbers collected just above, the
# per-PR run state files and whatever per-PR report files exist at generation
# time. Called by deploy.sh, smoke.sh, pytest_report.sh, query_smoke.sh,
# teardown.sh, gc.sh, status-refresh.sh and the installer. Best effort
# throughout: the page is a convenience and must never be able to fail a
# deploy or a teardown.
write_status_page() {
    if [ -z "${PREVIEW_WEB_ROOT}" ]; then
        return 0
    fi
    if ! ${SUDO} mkdir -p "${PREVIEW_WEB_ROOT}/data" 2>/dev/null; then
        log "WARNING: could not create ${PREVIEW_WEB_ROOT}, skipping the status page"
        return 0
    fi
    ${SUDO} chmod 755 "${PREVIEW_WEB_ROOT}" "${PREVIEW_WEB_ROOT}/data" 2>/dev/null || true

    expire_stale_preview_states
    collect_host_stats

    local rows html
    # One tab separated line per preview: pr, branch, sha, created, state.
    rows="$(${DOCKER} ps -a --filter 'label=arax.preview=true' \
        --format '{{.Label "arax.preview.pr"}}\t{{.Label "arax.preview.branch"}}\t{{.Label "arax.preview.sha"}}\t{{.Label "arax.preview.created"}}\t{{.State}}' \
        2>/dev/null || true)"

    if ! html="$(PREVIEW_CONTAINER_ROWS="${rows}" python3 - <<'PYTHON_EOF'
import html as html_module
import json
import os
import sys
import time

web_root = os.environ.get("PREVIEW_WEB_ROOT", "/var/www/arax-preview")
prefix = os.environ.get("PREVIEW_PATH_PREFIX", "")
base_url = os.environ.get("PREVIEW_PUBLIC_BASE_URL", "https://cicd.rtx.ai").rstrip("/")
repo = os.environ.get("PREVIEW_REPO", "RTXteam/RTX")
ttl = os.environ.get("PREVIEW_TTL_DAYS", "7")
max_active = os.environ.get("PREVIEW_MAX_ACTIVE", "3")
memory_limit = os.environ.get("PREVIEW_MEMORY_LIMIT", "2g")

# What the host is, for the line under the subtitle. One host, so it is
# written down here rather than read off the machine on every deploy.
HOST_NAME = "cicd.rtx.ai"
HOST_SPEC = "m5a.large, 2 vCPU, 7.5 GB, no swap, Ubuntu 20.04"

# name on disk, label in the expander
DATA_FILES = [
    ("deploy-log.txt", "deploy log"),
    ("build-log.txt", "docker build log"),
    ("smoke.md", "smoke test"),
    ("pytest.md", "pytest"),
    ("queries.md", "live queries"),
]
# A runaway file must not turn the page into a 40 MB download.
MAX_EMBED_BYTES = 200000

# stage key, label on the card, report file the done state is summarised from
STAGES = [
    ("deploy", "deploy", None),
    ("smoke", "smoke test", "smoke.md"),
    ("pytest", "pytest", "pytest.md"),
    ("queries", "live queries", "queries.md"),
]


def esc(value):
    return html_module.escape(str(value), quote=True)


def env_int(name):
    """The environment value as an int, or None when it is missing or junk."""
    try:
        return int(os.environ.get(name, "").strip())
    except (TypeError, ValueError):
        return None


def env_float(name):
    try:
        return float(os.environ.get(name, "").strip())
    except (TypeError, ValueError):
        return None


def human_memory(value):
    """2g as it is written for docker, said the way a person reads it."""
    text = str(value).strip()
    if text[-1:] in ("g", "G"):
        return text[:-1] + " GB"
    if text[-1:] in ("m", "M"):
        return text[:-1] + " MB"
    return text


def read_data_file(pr, name):
    path = os.path.join(web_root, "data", str(pr), name)
    try:
        with open(path, "r", errors="replace") as handle:
            text = handle.read()
    except Exception:
        return None
    if len(text) > MAX_EMBED_BYTES:
        text = "[truncated]\n" + text[-MAX_EMBED_BYTES:]
    return text


def read_state(pr):
    text = read_data_file(pr, "state.json")
    if text is None:
        return None
    try:
        doc = json.loads(text)
    except Exception:
        return None
    if not isinstance(doc, dict):
        return None
    return doc


def clock(value):
    """An epoch second as HH:MM UTC, or the empty string."""
    try:
        return time.strftime("%H:%M UTC", time.gmtime(int(value)))
    except (TypeError, ValueError):
        return ""


# The compact one line per check summary. Each builder returns a list of
# (text, state) pairs, where the state is True for a pass, False for a failure
# and None for something that did not run. Anything that cannot be parsed
# drops its rows rather than breaking the page.
def pytest_rows(pr):
    text = read_data_file(pr, "pytest.md")
    if text is None:
        return []
    marker = "**pytest:**"
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(marker):
            rest = stripped[len(marker):].strip()
            if not rest:
                return []
            passed = " 0 failed" in rest or "failed" not in rest
            return [("pytest: " + rest, passed)]
    return []


def query_rows(pr):
    text = read_data_file(pr, "queries.md")
    if text is None:
        return []
    rows = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 4:
            continue
        name = cells[0]
        # The header row and the row of dashes under it.
        if not name or name == "#" or set(name) <= set("-: "):
            continue
        failed = name.startswith("⚠")
        short = name.lstrip("⚠").strip() or "query"
        if failed:
            rows.append((short + ": failed", False))
        else:
            rows.append((short + ": ok (" + cells[3] + " s)", True))
    return rows


def smoke_rows(pr):
    text = read_data_file(pr, "smoke.md")
    if text is None:
        return []
    passed = 0
    failed = 0
    for line in text.splitlines():
        if "| pass |" in line:
            passed += 1
        elif "| FAIL |" in line:
            failed += 1
    total = passed + failed
    if not total:
        return []
    return [("smoke: %d/%d passed" % (passed, total), failed == 0)]


REPORT_ROWS = {
    "smoke": smoke_rows,
    "pytest": pytest_rows,
    "queries": query_rows,
}


def report_rows(pr, key):
    builder = REPORT_ROWS.get(key)
    if builder is None:
        return []
    try:
        return builder(pr)
    except Exception:
        return []


def legacy_rows(pr):
    """What a card showed before run state files existed, for a preview that
    was deployed by an older copy of these scripts and has no state.json."""
    rows = []
    for key, label, filename in STAGES:
        if filename is None:
            continue
        found = report_rows(pr, key)
        if found:
            rows.extend(found)
        elif read_data_file(pr, filename) is None:
            rows.append((label + ": not run", None))
    return rows


# ---------------------------------------------------------------------------
# Host tiles. Each one is (key, value, label, state), where the state is ok or
# bad or the empty string for a number with no threshold behind it. The
# thresholds are the ones the preflight check refuses on, read from the same
# environment variables, so the page turns red exactly when a deploy would be
# turned away. Every tile is always rendered, with the word "no data" when the
# collector could not read it, so the live refresh never moves the page.
# ---------------------------------------------------------------------------
NO_DATA = "no data"


def disk_floor_gb(disk_size):
    floor = env_int("PREVIEW_MIN_FREE_DISK_GB") or 0
    pct = env_int("PREVIEW_MIN_FREE_DISK_PCT") or 0
    if disk_size:
        pct_floor = disk_size * pct // 100
        if pct_floor > floor:
            floor = pct_floor
    return floor


def host_tiles():
    tiles = []

    mem_avail = env_int("HOST_MEM_AVAIL_MB")
    mem_total = env_int("HOST_MEM_TOTAL_MB")
    ram_floor = env_int("PREVIEW_MIN_FREE_RAM_MB")
    if mem_avail is not None and mem_total:
        state = "ok"
        if ram_floor is not None and mem_avail < ram_floor:
            state = "bad"
        tiles.append(
            (
                "mem",
                "%.1f GB" % (mem_avail / 1024.0),
                "memory available of %.1f GB" % (mem_total / 1024.0),
                state,
            )
        )
    else:
        tiles.append(("mem", NO_DATA, "memory available", ""))

    disk_avail = env_int("HOST_DISK_AVAIL_GB")
    disk_size = env_int("HOST_DISK_SIZE_GB")
    if disk_avail is not None and disk_size:
        floor = disk_floor_gb(disk_size)
        state = "bad" if disk_avail < floor else "ok"
        tiles.append(("disk", "%d GB" % disk_avail, "disk free of %d GB" % disk_size, state))
    else:
        tiles.append(("disk", NO_DATA, "disk free", ""))

    load_1 = env_float("HOST_LOAD_1")
    if load_1 is not None:
        tiles.append(("load", "%.2f" % load_1, "load average, 1 minute", ""))
    else:
        tiles.append(("load", NO_DATA, "load average, 1 minute", ""))

    slots_used = env_int("HOST_SLOTS_USED")
    slots_max = env_int("HOST_SLOTS_MAX")
    if slots_used is not None and slots_max:
        state = "bad" if slots_used >= slots_max else "ok"
        tiles.append(("slots", "%d/%d" % (slots_used, slots_max), "preview slots in use", state))
    else:
        tiles.append(("slots", NO_DATA, "preview slots in use", ""))

    return tiles


def container_stats():
    """(name, memory, cpu) for every rtx_ container docker stats reported."""
    raw = os.environ.get("HOST_CONTAINER_STATS", "")
    rows = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        fields = line.split("\t")
        if len(fields) < 3:
            # Older docker builds hand the format string through without
            # turning the escape into a real tab.
            fields = line.split("\\t")
        if len(fields) < 3:
            continue
        name, mem, cpu = [item.strip() for item in fields[:3]]
        if not name.startswith("rtx_"):
            continue
        rows.append((name, mem, cpu))
    rows.sort(key=lambda item: item[0])
    return rows


# ---------------------------------------------------------------------------
# The previews: every running container, plus every pull request that has a
# run state file but no container yet, which is what a deploy looks like while
# its image is still building.
# ---------------------------------------------------------------------------
containers = {}
for line in os.environ.get("PREVIEW_CONTAINER_ROWS", "").splitlines():
    if not line.strip():
        continue
    fields = line.split("\t")
    if len(fields) < 5:
        fields = line.split("\\t")
    while len(fields) < 5:
        fields.append("")
    pr, branch, sha, created, state = [item.strip() for item in fields[:5]]
    if not pr.isdigit():
        continue
    if created.isdigit():
        created_text = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(int(created)))
    else:
        created_text = "unknown"
    containers[pr] = {
        "branch": branch,
        "sha": sha,
        "created": created_text,
        "state": state or "unknown",
    }

state_prs = []
try:
    for name in os.listdir(os.path.join(web_root, "data")):
        if name.isdigit() and os.path.isfile(os.path.join(web_root, "data", name, "state.json")):
            state_prs.append(name)
except Exception:
    state_prs = []

previews = []
for pr in sorted(set(list(containers.keys()) + state_prs), key=int):
    box = containers.get(pr)
    state = read_state(pr)
    stages = {}
    if state and isinstance(state.get("stages"), dict):
        stages = state["stages"]
    previews.append(
        {
            "pr": pr,
            "branch": (box or {}).get("branch") or (state or {}).get("branch") or "unknown",
            "sha": (box or {}).get("sha") or (state or {}).get("sha") or "",
            "created": (box or {}).get("created") or "",
            "state": (box or {}).get("state") or "",
            "command": (state or {}).get("command") or "",
            "stages": stages,
            "has_state": state is not None,
        }
    )

generated = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
sampled_epoch = int(time.time())

CSS = """:root { color-scheme: light; }
* { box-sizing: border-box; }
body { margin: 0; background: #f7f7f8; color: #1f2937;
       font: 15px/1.6 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, sans-serif;
       -webkit-font-smoothing: antialiased; }
.wrap { max-width: 1100px; margin: 0 auto; padding: 40px 24px 64px; }
a { color: #2563eb; text-decoration: none; }
a:hover { text-decoration: underline; }
code, .num { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
       font-size: 13px; font-variant-numeric: tabular-nums; }
h1 { font-size: 26px; font-weight: 600; margin: 0; letter-spacing: -0.01em; }
.subtitle { font-size: 15px; color: #4b5563; margin: 6px 0 0; }
.spec { color: #6b7280; font-size: 13px; margin: 6px 0 0; }
h2 { font-size: 13px; font-weight: 600; color: #6b7280; margin: 36px 0 12px; }
p { margin: 0 0 10px; }
p:last-child { margin-bottom: 0; }
.prose { max-width: 76ch; }
ul { margin: 0; padding-left: 20px; }
li { margin-bottom: 6px; }
li:last-child { margin-bottom: 0; }
.scroll { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; background: #ffffff;
        border: 1px solid #e5e7eb; border-radius: 8px; font-size: 14px; }
th { text-align: left; font-weight: 600; color: #6b7280; font-size: 13px;
     padding: 10px 16px; border-bottom: 1px solid #e5e7eb; white-space: nowrap; }
td { padding: 10px 16px; border-top: 1px solid #f3f4f6; vertical-align: top; }
tbody tr:first-child td { border-top: none; }
td.cmd { white-space: nowrap; width: 1%; }
td.num { white-space: nowrap; }
.note { color: #6b7280; font-size: 13px; margin: 10px 0 0; }
.flow { background: #ffffff; border: 1px solid #e5e7eb; border-radius: 8px;
        padding: 18px 16px; overflow-x: auto; }
.flow svg { display: block; width: 100%; min-width: 720px; height: auto; }
.tiles { display: flex; flex-wrap: wrap; gap: 12px; margin: 0 0 10px; }
.tiles.stale .tile { opacity: 0.55; }
.tile { flex: 1 1 200px; background: #ffffff; border: 1px solid #e5e7eb;
        border-radius: 8px; padding: 16px 18px; }
.tile .value { font-size: 24px; font-weight: 600; line-height: 1.25;
        font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
        font-variant-numeric: tabular-nums; }
.tile.ok .value { color: #059669; }
.tile.bad .value { color: #dc2626; }
.tile .label { font-size: 13px; color: #6b7280; margin-top: 4px; }
.sample { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
          font-variant-numeric: tabular-nums; font-size: 12px; color: #6b7280;
          margin: 0 0 14px; min-height: 18px; line-height: 18px; }
.sample.stale { color: #dc2626; }
.card { background: #ffffff; border: 1px solid #e5e7eb; border-radius: 8px;
        padding: 18px 20px; margin: 0 0 12px; }
.card-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.card h3 { font-size: 16px; font-weight: 600; margin: 0; }
.card h3 a { color: #1f2937; }
.meta { color: #6b7280; font-size: 13px; margin-top: 3px; }
.dot { width: 9px; height: 9px; border-radius: 50%; background: #9ca3af;
       display: inline-block; flex: none; margin-top: 7px; }
.dot.ok { background: #059669; }
.dot.bad { background: #dc2626; }
dl { display: grid; grid-template-columns: 96px minmax(0, 1fr); gap: 4px 16px;
     margin: 14px 0 0; font-size: 14px; }
dt { color: #6b7280; }
dd { margin: 0; overflow-wrap: anywhere; }
.running { color: #059669; }
.stopped { color: #b45309; }
.stages { border-top: 1px solid #f3f4f6; margin-top: 16px; padding-top: 12px; }
.check { display: flex; align-items: center; gap: 9px; font-size: 14px; padding: 2px 0; }
.check.sub { padding-left: 27px; color: #4b5563; }
.check span { overflow-wrap: anywhere; }
.chip { flex: none; display: inline-flex; align-items: center; justify-content: center;
        width: 18px; height: 18px; border-radius: 5px; font-size: 11px; font-weight: 700;
        color: #6b7280; background: #f3f4f6; }
.chip.ok { color: #059669; background: #ecfdf5; }
.chip.bad { color: #dc2626; background: #fef2f2; }
.spinner { flex: none; width: 18px; height: 18px; border-radius: 50%;
           border: 2px solid #e5e7eb; border-top-color: #2563eb;
           animation: arax-spin 0.9s linear infinite; }
@keyframes arax-spin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) { .spinner { animation-duration: 2.4s; } }
details { margin-top: 10px; }
summary { cursor: pointer; color: #6b7280; font-size: 13px; }
pre { overflow-x: auto; background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 6px;
      padding: 12px 14px; margin: 8px 0 4px; font-size: 12px; line-height: 1.5;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      white-space: pre-wrap; overflow-wrap: anywhere; }
.empty { color: #6b7280; background: #ffffff; border: 1px dashed #e5e7eb;
         border-radius: 8px; padding: 24px; text-align: center; }
footer { color: #6b7280; font-size: 13px; border-top: 1px solid #e5e7eb;
         margin-top: 40px; padding-top: 16px; }
@media (max-width: 640px) {
  .wrap { padding: 28px 20px 48px; }
  h1 { font-size: 22px; }
  dl { grid-template-columns: 1fr; gap: 0 0; }
  dt { margin-top: 8px; }
}"""

# ---------------------------------------------------------------------------
# The flow diagram. Hand written SVG on a fixed viewBox that scales to the
# width of the page, so there is nothing to load and nothing to lay out.
# ---------------------------------------------------------------------------
FLOW_W = 158
FLOW_PITCH = 178
FLOW_H = 64
FLOW_LEFT = 26

FLOW_SKINS = {
    "": ("#ffffff", "#d1d5db", "#1f2937", "#6b7280"),
    "start": ("#eff6ff", "#bfdbfe", "#1d4ed8", "#2563eb"),
    "target": ("#ecfdf5", "#a7f3d0", "#047857", "#059669"),
    "gone": ("#fef2f2", "#fecaca", "#b91c1c", "#dc2626"),
}


def flow_col(index):
    return FLOW_LEFT + index * FLOW_PITCH


def flow_box(x, y, width, first, second, skin=""):
    fill, stroke, ink, sub = FLOW_SKINS[skin]
    middle = x + width / 2.0
    parts = [
        '<rect x="%g" y="%g" width="%g" height="%d" rx="8" fill="%s" stroke="%s"/>'
        % (x, y, width, FLOW_H, fill, stroke)
    ]
    parts.append(
        '<text x="%g" y="%g" text-anchor="middle" font-size="13" fill="%s">%s</text>'
        % (middle, y + 26, ink, esc(first))
    )
    if second:
        parts.append(
            '<text x="%g" y="%g" text-anchor="middle" font-size="13" fill="%s">%s</text>'
            % (middle, y + 44, sub, esc(second))
        )
    return "".join(parts)


def flow_arrow(x_from, x_to, y):
    return (
        '<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="#9ca3af" stroke-width="1.5" '
        'marker-end="url(#arax-arrow)"/>' % (x_from, y + FLOW_H / 2.0, x_to, y + FLOW_H / 2.0)
    )


def flow_svg():
    row1 = 34
    row2 = 150
    row3 = 266
    parts = [
        '<svg viewBox="0 0 1100 348" xmlns="http://www.w3.org/2000/svg" role="img" '
        'aria-label="How a preview is deployed, redeployed and removed">',
        '<defs><marker id="arax-arrow" viewBox="0 0 10 10" refX="9" refY="5" '
        'markerWidth="7" markerHeight="7" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" '
        'fill="#9ca3af"/></marker></defs>',
    ]

    first_row = [
        ("PR comment", "/deploy", "start"),
        ("GitHub Actions", "Preview Deploy", ""),
        ("self-hosted runner", HOST_NAME, ""),
        ("docker build", "container rtx_pr_N", ""),
        ("nginx route", "/N/", ""),
        (base_url, "/N/", "target"),
    ]
    for index, item in enumerate(first_row):
        x = flow_col(index)
        parts.append(flow_box(x, row1, FLOW_W, item[0], item[1], item[2]))
        if index:
            parts.append(flow_arrow(flow_col(index - 1) + FLOW_W + 4, x - 5, row1))

    parts.append(flow_box(flow_col(0), row2, FLOW_W, "PR comment", "/redeploy", "start"))
    parts.append(flow_arrow(flow_col(0) + FLOW_W + 4, flow_col(1) - 5, row2))
    parts.append(
        flow_box(flow_col(1), row2, FLOW_W * 2 + 20, "git checkout and service restart",
                 "inside the running container", "")
    )
    parts.append(flow_arrow(flow_col(1) + FLOW_W * 2 + 24, flow_col(5) - 5, row2))
    parts.append(flow_box(flow_col(5), row2, FLOW_W, "same URL", "no image rebuild", "target"))

    parts.append(flow_box(flow_col(0), row3, FLOW_W, "PR closed", "or /undeploy", "start"))
    parts.append(flow_arrow(flow_col(0) + FLOW_W + 4, flow_col(1) - 5, row3))
    parts.append(
        flow_box(flow_col(1), row3, FLOW_W * 3 + 40, "teardown removes the container, the image,",
                 "the nginx route and the reports on this page", "gone")
    )
    parts.append("</svg>")
    return "".join(parts)


out = []
out.append("<!DOCTYPE html>")
out.append("<html lang=\"en\">")
out.append("<head>")
out.append("<meta charset=\"utf-8\">")
out.append("<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">")
out.append("<title>ARAX preview environments</title>")
out.append("<style>")
out.append(CSS)
out.append("</style>")
out.append("</head>")
out.append("<body>")
out.append("<div class=\"wrap\">")

out.append("<h1>ARAX preview environments</h1>")
out.append(
    "<p class=\"subtitle\">" + esc(HOST_NAME) + ", per pull request deployments for "
    "<a href=\"https://github.com/" + esc(repo) + "\">" + esc(repo) + "</a></p>"
)
out.append("<p class=\"spec\">" + esc(HOST_SPEC) + "</p>")

out.append("<h2>About</h2>")
out.append("<div class=\"prose\">")
out.append(
    "<p>This host runs disposable copies of ARAX, one per open pull request, so a change can be "
    "used before it is merged. It is meant for the developers and reviewers of "
    "<a href=\"https://github.com/" + esc(repo) + "\">" + esc(repo) + "</a>, who need to try a "
    "pull request live rather than read a diff and guess. Every pull request can get its own "
    "running ARAX with the real databases, reachable at a public URL, and it is removed when the "
    "pull request closes.</p>"
)
out.append("</div>")

out.append("<h2>How it works</h2>")
out.append("<ul class=\"prose\">")
out.append("<li>One container per pull request, built from that branch.</li>")
out.append("<li>The databases are shared from the host and mounted into every preview rather than copied.</li>")
out.append(
    "<li>Each preview has its own URL, <code>" + esc(base_url) + "/&lt;PR&gt;/</code>.</li>"
)
out.append(
    "<li>At most " + esc(max_active) + " previews at a time, with " + esc(human_memory(memory_limit))
    + " of memory each.</li>"
)
out.append(
    "<li>Previews are public and unauthenticated, and they are removed " + esc(ttl)
    + " days after they are deployed or as soon as the pull request closes.</li>"
)
out.append("</ul>")

out.append("<h2>Commands</h2>")
out.append("<div class=\"scroll\"><table>")
out.append("<thead><tr><th>comment</th><th>what it does</th></tr></thead><tbody>")
out.append(
    "<tr><td class=\"cmd\"><code>/deploy</code></td><td>Full rebuild from the pull request head. "
    "About 6 minutes. Use it for the first deploy, and after a change to the requirements or the "
    "Dockerfile.</td></tr>"
)
out.append(
    "<tr><td class=\"cmd\"><code>/redeploy</code></td><td>Restart the running preview on the "
    "latest commit. About a minute. Refuses with a reason when a rebuild is needed.</td></tr>"
)
out.append(
    "<tr><td class=\"cmd\"><code>/undeploy</code></td><td>Remove the preview now.</td></tr>"
)
out.append("</tbody></table></div>")
out.append(
    "<p class=\"note\">A command has to be the whole first line of a pull request comment, only "
    "members of the repository can trigger one, and the results are posted back on the pull "
    "request.</p>"
)

out.append("<h2>Flow</h2>")
out.append("<div class=\"flow\">" + flow_svg() + "</div>")

out.append("<h2>Host</h2>")
out.append("<div class=\"tiles\" id=\"host-tiles\">")
for key, value, label, state in host_tiles():
    classes = "tile " + state if state else "tile"
    out.append(
        "<div class=\"" + esc(classes) + "\" id=\"tile-" + esc(key) + "\">"
        "<div class=\"value\">" + esc(value) + "</div>"
        "<div class=\"label\">" + esc(label) + "</div></div>"
    )
out.append("</div>")
out.append(
    "<p class=\"sample\" id=\"host-sample\" data-epoch=\"" + esc(sampled_epoch) + "\" "
    "data-at=\"" + esc(generated) + "\">last sample " + esc(generated) + " (0 s ago)</p>"
)
out.append("<div class=\"scroll\"><table id=\"host-containers\">")
out.append("<thead><tr><th>container</th><th>memory</th><th>cpu</th></tr></thead>")
out.append("<tbody>")
stats = container_stats()
if stats:
    for name, mem, cpu in stats:
        out.append(
            "<tr><td><code>" + esc(name) + "</code></td><td class=\"num\">" + esc(mem)
            + "</td><td class=\"num\">" + esc(cpu) + "</td></tr>"
        )
else:
    out.append("<tr><td colspan=\"3\">No preview containers are running.</td></tr>")
out.append("</tbody></table></div>")

out.append("<h2>Previews</h2>")

if not previews:
    out.append("<p class=\"empty\">No previews are deployed right now.</p>")

for item in previews:
    pr = item["pr"]
    path = "/" + prefix + pr
    url = base_url + path + "/"
    status_path = path + "/api/arax/v1.4/status"
    sha = item["sha"]
    out.append("<div class=\"card\">")
    out.append("<div class=\"card-head\">")
    out.append("<div>")
    out.append(
        "<h3><a href=\"https://github.com/" + esc(repo) + "/pull/" + esc(pr) + "\">PR #"
        + esc(pr) + "</a></h3>"
    )
    if sha and sha != "unknown":
        meta = (
            "<code>" + esc(item["branch"]) + "</code> at <a href=\"https://github.com/"
            + esc(repo) + "/commit/" + esc(sha) + "\"><code>" + esc(sha[:7]) + "</code></a>"
        )
    else:
        meta = "<code>" + esc(item["branch"]) + "</code> at <code>unknown</code>"
    out.append("<div class=\"meta\">" + meta + "</div>")
    out.append("</div>")
    if item["state"]:
        out.append(
            "<span class=\"dot\" data-status=\"" + esc(status_path) + "\" title=\"health unknown\">"
            "</span>"
        )
    out.append("</div>")

    out.append("<dl>")
    if item["command"]:
        out.append("<dt>command</dt><dd><code>/" + esc(item["command"]) + "</code></dd>")
    if item["created"]:
        out.append("<dt>created</dt><dd>" + esc(item["created"]) + "</dd>")
    if item["state"]:
        state_class = "running" if item["state"] == "running" else "stopped"
        out.append(
            "<dt>container</dt><dd class=\"" + state_class + "\">" + esc(item["state"]) + "</dd>"
        )
        out.append("<dt>preview</dt><dd><a href=\"" + esc(url) + "\">" + esc(url) + "</a></dd>")
    else:
        out.append("<dt>container</dt><dd class=\"stopped\">not created yet</dd>")
        out.append("<dt>preview</dt><dd>" + esc(url) + " once the container is up</dd>")
    out.append("</dl>")

    rows = []
    if item["has_state"]:
        for key, label, filename in STAGES:
            entry = item["stages"].get(key)
            if not isinstance(entry, dict):
                entry = {}
            status = entry.get("status") or "pending"
            detail = str(entry.get("detail") or "")
            since = clock(entry.get("started_at"))
            if status == "running":
                text = label + " running"
                if since:
                    text = text + " since " + since
                rows.append(("spin", text))
            elif status == "failed":
                text = label + " failed"
                if detail:
                    text = text + ": " + detail
                rows.append(("bad", text))
            elif status == "done":
                text = label + " done"
                if detail:
                    text = text + ", " + detail
                rows.append(("ok", text))
            else:
                rows.append(("pending", label + " pending"))
            # Whatever the report file says, under the stage it belongs to.
            if status in ("done", "failed"):
                for found, passed in report_rows(pr, key):
                    if passed is True:
                        rows.append(("sub-ok", found))
                    elif passed is False:
                        rows.append(("sub-bad", found))
                    else:
                        rows.append(("sub-pending", found))
    else:
        # A preview from before the run state files existed.
        for found, passed in legacy_rows(pr):
            if passed is True:
                rows.append(("ok", found))
            elif passed is False:
                rows.append(("bad", found))
            else:
                rows.append(("pending", found))

    if rows:
        out.append("<div class=\"stages\">")
        for kind, text in rows:
            sub = kind.startswith("sub-")
            base = kind[4:] if sub else kind
            if base == "spin":
                mark = "<span class=\"spinner\"></span>"
            elif base == "ok":
                mark = "<span class=\"chip ok\">&#10003;</span>"
            elif base == "bad":
                mark = "<span class=\"chip bad\">&#10007;</span>"
            else:
                mark = "<span class=\"chip\">&#183;</span>"
            row_class = "check sub" if sub else "check"
            out.append(
                "<div class=\"" + row_class + "\">" + mark + "<span>" + esc(text) + "</span></div>"
            )
        out.append("</div>")

    for name, label in DATA_FILES:
        body = read_data_file(pr, name)
        if body is None:
            continue
        out.append("<details><summary>" + esc(label) + "</summary>")
        out.append("<pre>" + esc(body.rstrip()) + "</pre>")
        out.append("</details>")
    out.append("</div>")

out.append(
    "<footer>Page generated " + esc(generated) + ". It is rewritten on every deploy event and "
    "again every 5 minutes from cron. The host numbers above that refresh on their own come from "
    "a sampler that writes them every 15 seconds, and the dot next to a pull request number is "
    "checked by your browser. With JavaScript turned off everything on this page still renders, "
    "as it was at generation time.</footer>"
)
out.append("</div>")

# ---------------------------------------------------------------------------
# The only script on the page. It refreshes the host numbers from host.json,
# which the sampler service rewrites every 15 seconds, and asks each preview
# whether it is alive. Everything it touches is already on the page, so a
# browser with JavaScript turned off loses the live updates and nothing else.
# ---------------------------------------------------------------------------
SCRIPT = """(function () {
  if (typeof fetch !== "function") { return; }
  var STALE_AFTER = 60;
  var sample = document.getElementById("host-sample");
  var tiles = document.getElementById("host-tiles");
  var table = document.getElementById("host-containers");
  var sampledEpoch = 0;
  var sampledText = "";
  var baseAge = 0;
  var stampMs = Date.now();

  if (sample) {
    sampledEpoch = Number(sample.getAttribute("data-epoch")) || 0;
    sampledText = sample.getAttribute("data-at") || "";
  }

  function setTile(id, value, label, state) {
    var tile = document.getElementById(id);
    if (!tile) { return; }
    var valueNode = tile.querySelector(".value");
    var labelNode = tile.querySelector(".label");
    if (valueNode) { valueNode.textContent = value; }
    if (labelNode && label) { labelNode.textContent = label; }
    tile.className = state ? "tile " + state : "tile";
  }

  function isNumber(value) {
    return typeof value === "number" && isFinite(value);
  }

  function cell(text, className) {
    var node = document.createElement("td");
    node.textContent = text;
    if (className) { node.className = className; }
    return node;
  }

  function applyContainers(rows) {
    if (!table) { return; }
    var body = table.querySelector("tbody");
    if (!body) { return; }
    while (body.firstChild) { body.removeChild(body.firstChild); }
    if (!rows.length) {
      var empty = document.createElement("tr");
      var only = cell("No preview containers are running.");
      only.setAttribute("colspan", "3");
      empty.appendChild(only);
      body.appendChild(empty);
      return;
    }
    rows.forEach(function (row) {
      var line = document.createElement("tr");
      var nameCell = document.createElement("td");
      var name = document.createElement("code");
      name.textContent = row.name || "";
      nameCell.appendChild(name);
      line.appendChild(nameCell);
      var usage = row.mem_usage || "";
      if (row.mem_limit) { usage = usage + " / " + row.mem_limit; }
      line.appendChild(cell(usage, "num"));
      line.appendChild(cell(row.cpu_pct || "", "num"));
      body.appendChild(line);
    });
  }

  function apply(data) {
    var limits = data.thresholds || {};

    if (isNumber(data.mem_available_mb) && isNumber(data.mem_total_mb) && data.mem_total_mb) {
      var memState = "ok";
      if (isNumber(limits.ram_min_mb) && data.mem_available_mb < limits.ram_min_mb) {
        memState = "bad";
      }
      setTile("tile-mem", (data.mem_available_mb / 1024).toFixed(1) + " GB",
              "memory available of " + (data.mem_total_mb / 1024).toFixed(1) + " GB", memState);
    } else {
      setTile("tile-mem", "no data", "memory available", "");
    }

    if (isNumber(data.disk_avail_gb) && isNumber(data.disk_size_gb) && data.disk_size_gb) {
      var diskState = "ok";
      if (isNumber(limits.disk_floor_gb) && data.disk_avail_gb < limits.disk_floor_gb) {
        diskState = "bad";
      }
      setTile("tile-disk", data.disk_avail_gb + " GB",
              "disk free of " + data.disk_size_gb + " GB", diskState);
    } else {
      setTile("tile-disk", "no data", "disk free", "");
    }

    if (isNumber(data.load1)) {
      setTile("tile-load", data.load1.toFixed(2), "load average, 1 minute", "");
    } else {
      setTile("tile-load", "no data", "load average, 1 minute", "");
    }

    if (isNumber(data.slots_used) && isNumber(data.slots_max) && data.slots_max) {
      setTile("tile-slots", data.slots_used + "/" + data.slots_max, "preview slots in use",
              data.slots_used >= data.slots_max ? "bad" : "ok");
    } else {
      setTile("tile-slots", "no data", "preview slots in use", "");
    }

    applyContainers(Array.isArray(data.containers) ? data.containers : []);

    if (isNumber(data.sampled_epoch) && data.sampled_epoch !== sampledEpoch) {
      sampledEpoch = data.sampled_epoch;
      sampledText = String(data.sampled_at || "").replace("T", " ").replace("Z", " UTC");
      // How old the sample already was when it arrived, from the clock of
      // whoever is reading the page. A browser clock that runs behind the
      // host would make this negative, so it is floored at zero, and from
      // here on the age is counted locally rather than against either clock.
      var seen = Math.floor(Date.now() / 1000) - sampledEpoch;
      baseAge = seen > 0 ? seen : 0;
      stampMs = Date.now();
    }
    tick();
  }

  function tick() {
    if (!sample || !sampledText) { return; }
    var age = Math.round(baseAge + (Date.now() - stampMs) / 1000);
    if (age < 0) { age = 0; }
    var stale = age > STALE_AFTER;
    sample.textContent = "last sample " + sampledText + " (" + age + " s ago)" +
      (stale ? " stale" : "");
    sample.className = stale ? "sample stale" : "sample";
    if (tiles) { tiles.className = stale ? "tiles stale" : "tiles"; }
  }

  function poll() {
    var options = { cache: "no-store" };
    try { options.signal = AbortSignal.timeout(10000); } catch (error) { options = { cache: "no-store" }; }
    fetch("host.json", options).then(function (response) {
      return response.ok ? response.json() : null;
    }).then(function (data) {
      if (data && typeof data === "object") { apply(data); }
    }).catch(function () {
      // A sampler that stopped writing, or a request that timed out. The age
      // keeps counting up on its own and the line says stale on its own.
    });
  }

  setInterval(tick, 1000);
  setInterval(poll, 15000);
  poll();

  var dots = document.querySelectorAll(".dot[data-status]");
  Array.prototype.forEach.call(dots, function (dot) {
    var options = {};
    try { options.signal = AbortSignal.timeout(8000); } catch (error) { options = {}; }
    fetch(dot.getAttribute("data-status"), options).then(function (response) {
      dot.className = response.ok ? "dot ok" : "dot bad";
      dot.title = "HTTP " + response.status;
    }).catch(function (error) {
      dot.className = "dot bad";
      dot.title = "unreachable: " + error;
    });
  });
})();"""

out.append("<script>")
out.append(SCRIPT)
out.append("</script>")
out.append("</body>")
out.append("</html>")

sys.stdout.write("\n".join(out) + "\n")
PYTHON_EOF
)"; then
        log "WARNING: could not render the status page"
        return 0
    fi

    if ! printf '%s\n' "${html}" | ${SUDO} tee "${PREVIEW_WEB_ROOT}/index.html" >/dev/null; then
        log "WARNING: could not write ${PREVIEW_WEB_ROOT}/index.html"
        return 0
    fi
    ${SUDO} chmod 644 "${PREVIEW_WEB_ROOT}/index.html" 2>/dev/null || true
    log "wrote the status page ${PREVIEW_WEB_ROOT}/index.html"
    return 0
}
