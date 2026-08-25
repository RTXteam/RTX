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

# The facts that describe the box rather than measure it: what it runs and
# where. Each is best effort and prints nothing when it cannot be read, so a
# fact that is missing is simply left off the page rather than shown blank.
# The cloud and the instance type are constants because there is one host.
PREVIEW_HOST_CLOUD="AWS EC2"
PREVIEW_HOST_INSTANCE="m5a.large"

# The docker version as a bare number, "24.0.7" out of "Docker version 24.0.7,
# build ...". DOCKER is "sudo docker", two words, so it must split.
host_docker_version() {
    local out
    # shellcheck disable=SC2086
    out="$(${DOCKER} --version 2>/dev/null || true)"
    out="$(printf '%s' "${out}" | sed -n 's/^Docker version \([^, ]*\).*/\1/p')"
    [ -n "${out}" ] && printf '%s\n' "${out}"
    return 0
}

# The distribution name, "Ubuntu 20.04.6 LTS". /etc/os-release first, then
# lsb_release, so a host without one still has the other.
host_os_pretty() {
    local pretty=""
    if [ -r /etc/os-release ]; then
        # os-release is a runtime host file of KEY=VALUE lines, not in this repo.
        # shellcheck disable=SC1091
        pretty="$(. /etc/os-release 2>/dev/null; printf '%s' "${PRETTY_NAME:-}")"
    fi
    if [ -z "${pretty}" ] && command -v lsb_release >/dev/null 2>&1; then
        pretty="$(lsb_release -ds 2>/dev/null | sed 's/^"//; s/"$//')"
    fi
    [ -n "${pretty}" ] && printf '%s\n' "${pretty}"
    return 0
}

# The running kernel release, "5.15.0-1084-aws".
host_kernel() {
    local kernel
    kernel="$(uname -r 2>/dev/null || true)"
    [ -n "${kernel}" ] && printf '%s\n' "${kernel}"
    return 0
}

# Uptime as a phrase, "up 3 days, 4 hours". uptime -p is procps only, so a
# host without it simply has no uptime fact.
host_uptime() {
    local up
    up="$(uptime -p 2>/dev/null | sed 's/^up //')"
    [ -n "${up}" ] && printf '%s\n' "${up}"
    return 0
}

# The EC2 region, best effort and cheap. PREVIEW_HOST_REGION pins it without a
# network call, which is what a test uses. Otherwise IMDSv2: a one second token
# fetch then a one second lookup, and any failure, including not being on EC2,
# prints nothing rather than hanging.
host_region() {
    if [ -n "${PREVIEW_HOST_REGION:-}" ]; then
        printf '%s\n' "${PREVIEW_HOST_REGION}"
        return 0
    fi
    command -v curl >/dev/null 2>&1 || return 0
    local token region
    token="$(curl -sS -m 1 -X PUT \
        -H 'X-aws-ec2-metadata-token-ttl-seconds: 60' \
        http://169.254.169.254/latest/api/token 2>/dev/null || true)"
    [ -n "${token}" ] || return 0
    region="$(curl -sS -m 1 \
        -H "X-aws-ec2-metadata-token: ${token}" \
        http://169.254.169.254/latest/meta-data/placement/region 2>/dev/null || true)"
    case "${region}" in
        ''|*[!a-z0-9-]*) return 0 ;;
    esac
    printf '%s\n' "${region}"
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

    HOST_CLOUD="${PREVIEW_HOST_CLOUD}"
    HOST_INSTANCE="${PREVIEW_HOST_INSTANCE}"
    HOST_REGION="$(host_region)"
    HOST_OS_PRETTY="$(host_os_pretty)"
    HOST_DOCKER_VERSION="$(host_docker_version)"
    HOST_KERNEL="$(host_kernel)"
    HOST_UPTIME="$(host_uptime)"

    export HOST_MEM_AVAIL_MB HOST_MEM_TOTAL_MB HOST_DISK_AVAIL_GB HOST_DISK_SIZE_GB \
        HOST_LOAD_1 HOST_LOAD_5 HOST_LOAD_15 HOST_SLOTS_USED HOST_SLOTS_MAX \
        HOST_CONTAINER_STATS \
        HOST_CLOUD HOST_INSTANCE HOST_REGION HOST_OS_PRETTY HOST_DOCKER_VERSION \
        HOST_KERNEL HOST_UPTIME
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

# Host port for a preview is this base plus the pull request number, bound to
# loopback. The card prints it in dim so a human on the box can curl it.
try:
    port_base = int(os.environ.get("PREVIEW_PORT_BASE", "10000").strip())
except (TypeError, ValueError):
    port_base = 10000

# The host is one box, so what it is stays a constant rather than being read
# off the machine on every render. The live facts below come from the
# collectors.
HOST_NAME = "cicd.rtx.ai"

# vCPU count of the box, used only to scale the load meter. m5a.large is 2.
NVCPU = 2

# A runaway file must not turn the page into a multi megabyte download. The
# file on disk is always complete, this only caps what is embedded.
MAX_EMBED_BYTES = 200000

# stage key, label on the row, report file the done state is summarised from
STAGES = [
    ("deploy", "deploy", None),
    ("smoke", "smoke", "smoke.md"),
    ("pytest", "pytest", "pytest.md"),
    ("queries", "live queries", "queries.md"),
]


def esc(value):
    return html_module.escape(str(value), quote=True)


def env_int(name):
    try:
        return int(os.environ.get(name, "").strip())
    except (TypeError, ValueError):
        return None


def env_float(name):
    try:
        return float(os.environ.get(name, "").strip())
    except (TypeError, ValueError):
        return None


def env_text(name):
    return os.environ.get(name, "").strip()


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


# ---------------------------------------------------------------------------
# Markdown table parsing. Every report a script writes is a GitHub flavoured
# markdown table, and the page turns it back into a real HTML table so a
# reader sees a grid rather than a wall of pipes. Anything that will not parse
# drops its rows rather than breaking the page.
# ---------------------------------------------------------------------------
def parse_md_table(text):
    headers = None
    rows = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        # The row of dashes under the header.
        if cells and all(cell and set(cell) <= set("-: ") for cell in cells):
            continue
        if headers is None:
            headers = cells
            continue
        rows.append(cells)
    return headers, rows


def fit(cells, width):
    cells = list(cells)
    while len(cells) < width:
        cells.append("")
    return cells[:width]


# ---------------------------------------------------------------------------
# Host facts and live metrics.
# ---------------------------------------------------------------------------
def host_facts():
    """(key, value) rows for the left column. A fact that could not be read is
    left out rather than shown blank."""
    ordered = [
        ("cloud", env_text("HOST_CLOUD")),
        ("instance", env_text("HOST_INSTANCE")),
        ("region", env_text("HOST_REGION")),
        ("os", env_text("HOST_OS_PRETTY")),
        ("docker", env_text("HOST_DOCKER_VERSION")),
        ("kernel", env_text("HOST_KERNEL")),
        ("uptime", env_text("HOST_UPTIME")),
    ]
    return [(key, value) for key, value in ordered if value]


def clamp_pct(fraction):
    if fraction is None:
        return None
    pct = int(round(fraction * 100))
    if pct < 0:
        return 0
    if pct > 100:
        return 100
    return pct


def host_metrics():
    """(id, label, value, pct, state) for the four live numbers, computed the
    same way the browser recomputes them from host.json so the two never
    disagree. pct is the meter fill, state is one of "", "warn", "bad"."""
    metrics = []

    mem_avail = env_int("HOST_MEM_AVAIL_MB")
    mem_total = env_int("HOST_MEM_TOTAL_MB")
    ram_floor = env_int("PREVIEW_MIN_FREE_RAM_MB")
    if mem_avail is not None and mem_total:
        state = "bad" if (ram_floor is not None and mem_avail < ram_floor) else ""
        pct = clamp_pct((mem_total - mem_avail) / float(mem_total))
        value = "%.1f GB free / %.1f GB" % (mem_avail / 1024.0, mem_total / 1024.0)
        metrics.append(("metric-mem", "memory", value, pct, state))
    else:
        metrics.append(("metric-mem", "memory", "no data", None, ""))

    disk_avail = env_int("HOST_DISK_AVAIL_GB")
    disk_size = env_int("HOST_DISK_SIZE_GB")
    disk_floor = None
    floor = env_int("PREVIEW_MIN_FREE_DISK_GB") or 0
    pct_floor = env_int("PREVIEW_MIN_FREE_DISK_PCT") or 0
    if disk_size:
        by_pct = disk_size * pct_floor // 100
        disk_floor = by_pct if by_pct > floor else floor
    if disk_avail is not None and disk_size:
        state = "bad" if (disk_floor is not None and disk_avail < disk_floor) else ""
        pct = clamp_pct((disk_size - disk_avail) / float(disk_size))
        value = "%d GB free / %d GB" % (disk_avail, disk_size)
        metrics.append(("metric-disk", "disk", value, pct, state))
    else:
        metrics.append(("metric-disk", "disk", "no data", None, ""))

    load1 = env_float("HOST_LOAD_1")
    load5 = env_float("HOST_LOAD_5")
    load15 = env_float("HOST_LOAD_15")
    if load1 is not None:
        state = ""
        if load1 > 2 * NVCPU:
            state = "bad"
        elif load1 > NVCPU:
            state = "warn"
        pct = clamp_pct(load1 / float(NVCPU))
        parts = ["%.2f" % load1]
        if load5 is not None:
            parts.append("%.2f" % load5)
        if load15 is not None:
            parts.append("%.2f" % load15)
        metrics.append(("metric-load", "load", "  ".join(parts), pct, state))
    else:
        metrics.append(("metric-load", "load", "no data", None, ""))

    slots_used = env_int("HOST_SLOTS_USED")
    slots_max = env_int("HOST_SLOTS_MAX")
    if slots_used is not None and slots_max:
        state = "bad" if slots_used >= slots_max else ""
        pct = clamp_pct(slots_used / float(slots_max))
        metrics.append(("metric-slots", "slots", "%d / %d" % (slots_used, slots_max), pct, state))
    else:
        metrics.append(("metric-slots", "slots", "no data", None, ""))

    return metrics


def container_stats():
    """(name, memory, cpu) for every rtx_ container docker stats reported. The
    memory field already carries "usage / limit" from docker."""
    raw = os.environ.get("HOST_CONTAINER_STATS", "")
    rows = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        fields = line.split("\t")
        if len(fields) < 3:
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
sample_hms = time.strftime("%H:%M:%S UTC", time.gmtime())
sampled_epoch = int(time.time())

# ---------------------------------------------------------------------------
# Palette. Light is the base on :root, dark is the same names with the neovim
# values, applied both when the system asks for dark and when the reader picked
# dark by hand, so neither theme can drift from the other.
# ---------------------------------------------------------------------------
LIGHT_TOKENS = """  color-scheme: light dark;
  --bg: #fbfbfa;
  --panel: #ffffff;
  --border: #d9dce1;
  --fg: #1b1f24;
  --dim: #6b7280;
  --accent: #0b6fc2;
  --ok: #1a7f37;
  --warn: #9a6700;
  --bad: #cf222e;
  --track: #eceef1;
"""

DARK_TOKENS = """  --bg: #0e1013;
  --panel: #14171b;
  --border: #262b31;
  --fg: #d6d9dd;
  --dim: #8b929c;
  --accent: #6cb6ff;
  --ok: #6bd968;
  --warn: #e2b53d;
  --bad: #ff6b6b;
  --track: #1c2127;
"""

MONO = ('"JetBrains Mono", "SFMono-Regular", "SF Mono", Menlo, Consolas, '
        '"DejaVu Sans Mono", monospace')

RULES = """* { box-sizing: border-box; }
html { color-scheme: light dark; }
body { margin: 0; background: var(--bg); color: var(--fg);
       font-family: MONOFONT; font-size: 13px; line-height: 1.55;
       font-variant-numeric: tabular-nums;
       -webkit-font-smoothing: antialiased; }
.num { font-variant-numeric: tabular-nums; }
.wrap { max-width: 1100px; margin: 0 auto; padding: 24px 20px 56px; }
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }

/* Header */
.top { display: flex; align-items: baseline; justify-content: space-between;
       gap: 16px; flex-wrap: wrap; margin-bottom: 8px; }
.brand { display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; }
.brand .name { color: var(--accent); font-weight: 700; font-size: 16px; }
.brand .sub { color: var(--dim); font-size: 12px; }

/* Theme switch: [ sys ][ light ][ dark ] */
.themes { display: none; }
:root[data-js="on"] .themes { display: inline-flex; }
.themes button { appearance: none; -webkit-appearance: none; border: 1px solid var(--border);
                 background: var(--panel); color: var(--dim); cursor: pointer;
                 font-family: inherit; font-size: 12px; line-height: 1;
                 padding: 5px 9px; margin: 0; }
.themes button + button { border-left: 0; }
.themes button:hover { color: var(--fg); }
.themes button[aria-pressed="true"] { color: var(--accent); background: var(--bg); }

/* Section rule: a short lead line, the label, then a rule to the edge */
.rule { display: flex; align-items: center; gap: 10px; margin: 26px 0 12px;
        color: var(--dim); font-size: 12px; }
.rule .k { white-space: nowrap; color: var(--accent); letter-spacing: 0.04em; }
.rule .lead { flex: 0 0 22px; border-top: 1px solid var(--border); }
.rule .fill { flex: 1 1 auto; border-top: 1px solid var(--border); }
.rule.sub { margin: 18px 0 8px; }
.rule.sub .k { color: var(--dim); }

/* Panels */
.panel { background: var(--panel); border: 1px solid var(--border); padding: 14px 16px; }
.host { display: grid; grid-template-columns: minmax(260px, 0.9fr) minmax(280px, 1.1fr);
        gap: 22px 32px; }
@media (max-width: 720px) { .host { grid-template-columns: 1fr; gap: 18px; } }

/* Key / value fact rows */
.kv { display: grid; grid-template-columns: 74px minmax(0, 1fr); gap: 3px 14px; }
.kv dt { color: var(--dim); }
.kv dd { margin: 0; overflow-wrap: anywhere; }

/* Live metrics */
.metrics { display: grid; gap: 8px; align-content: start; }
.metrics.stale { opacity: 0.5; }
.metric { display: grid; grid-template-columns: 60px minmax(0, 1fr) 120px;
          align-items: center; gap: 12px; }
.metric .mk { color: var(--dim); }
.metric .mv { color: var(--fg); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.meter { position: relative; height: 8px; background: var(--track);
         border: 1px solid var(--border); }
.meter .fill { position: absolute; left: 0; top: 0; bottom: 0; width: 0;
               background: var(--accent); }
.metric[data-state="warn"] .fill { background: var(--warn); }
.metric[data-state="bad"] .fill { background: var(--bad); }

/* Live pulse line */
.pulse { display: flex; align-items: center; gap: 8px; margin-top: 14px;
         font-size: 12px; color: var(--dim); }
.pulse .dot { width: 8px; height: 8px; background: var(--ok); flex: none;
              animation: arax-blink 1.4s ease-in-out infinite; }
.pulse.stale .dot { background: var(--bad); animation: none; }
.pulse.stale { color: var(--bad); }
@keyframes arax-blink { 0%, 100% { opacity: 1; } 50% { opacity: 0.2; } }
@media (prefers-reduced-motion: reduce) { .pulse .dot { animation: none; } }

/* Tables */
.scroll { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 12.5px; }
th { text-align: left; font-weight: 700; color: var(--dim); padding: 6px 12px;
     border-bottom: 1px solid var(--border); white-space: nowrap; }
td { padding: 5px 12px; border-top: 1px solid var(--border); vertical-align: top; }
tbody tr:first-child td { border-top: none; }
td.num { white-space: nowrap; font-variant-numeric: tabular-nums; }
.rpt { border: 1px solid var(--border); background: var(--panel); }
.cell-ok { color: var(--ok); white-space: nowrap; }
.cell-bad { color: var(--bad); white-space: nowrap; }
tr.bad-row td { color: var(--bad); }

/* Preview cards */
.pv { border: 1px solid var(--border); background: var(--panel);
      padding: 14px 16px; margin-bottom: 14px; }
.pv-head { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.pv-head .pr { font-weight: 700; }
.pv-head .pr a { color: var(--fg); }
.pv-head .repo, .pv-head .branch, .pv-head .sha { color: var(--dim); }
.pv-head .sha a { color: var(--dim); }
.pv-head .health { margin-left: auto; display: inline-flex; align-items: center; gap: 6px;
                   color: var(--dim); }
.dot { width: 8px; height: 8px; background: var(--dim); display: inline-block; flex: none; }
.dot.ok { background: var(--ok); }
.dot.bad { background: var(--bad); }
.pv .kv { margin-top: 12px; }
.loop { color: var(--dim); }

/* Stage rows */
.stages { display: grid; gap: 3px; }
.check { display: flex; align-items: center; gap: 9px; }
.check .g { flex: none; width: 15px; text-align: center; font-weight: 700; }
.check .g.ok { color: var(--ok); }
.check .g.bad { color: var(--bad); }
.check .g.pending { color: var(--dim); }
.check .t { overflow-wrap: anywhere; }
.check .t .d { color: var(--dim); }
.spinner { flex: none; width: 11px; height: 11px; border: 2px solid var(--track);
           border-top-color: var(--accent); border-radius: 50%;
           animation: arax-spin 0.9s linear infinite; }
@keyframes arax-spin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) { .spinner { animation-duration: 2.4s; } }

/* Expanders */
details { margin-top: 8px; }
summary { cursor: pointer; color: var(--dim); font-size: 12px; }
summary:hover { color: var(--fg); }
pre { overflow-x: auto; background: var(--bg); border: 1px solid var(--border);
      padding: 10px 12px; margin: 6px 0 2px; font-size: 12px; line-height: 1.5;
      font-family: MONOFONT; white-space: pre; }
.detail-grid { display: grid; gap: 8px; margin-top: 8px; }

.empty { color: var(--dim); border: 1px dashed var(--border); background: var(--panel);
         padding: 18px; }
footer { color: var(--dim); font-size: 12px; border-top: 1px solid var(--border);
         margin-top: 34px; padding-top: 14px; }
footer p { margin: 0 0 6px; }
footer p:last-child { margin: 0; }
"""
RULES = RULES.replace("MONOFONT", MONO)

CSS = (
    ":root {\n" + LIGHT_TOKENS + "}\n"
    + "@media (prefers-color-scheme: dark) {\n  :root:not([data-theme=\"light\"]) {\n"
    + "".join("  " + line + "\n" for line in DARK_TOKENS.strip("\n").split("\n"))
    + "  }\n}\n"
    + ":root[data-theme=\"dark\"] {\n" + DARK_TOKENS + "}\n"
    + RULES
)

# Runs before any of the page is painted: says JavaScript is available, which
# reveals the theme control, and applies a stored theme choice so a reload does
# not flash the other theme. localStorage throws rather than returning nothing
# where site data is blocked, so it is guarded.
BOOT_SCRIPT = """(function () {
  var root = document.documentElement;
  root.setAttribute("data-js", "on");
  try {
    var stored = localStorage.getItem("arax-preview-theme");
    if (stored === "light" || stored === "dark") {
      root.setAttribute("data-theme", stored);
    }
  } catch (error) {
    // Storage is blocked. The system preference decides, which is the default.
  }
})();"""


def rule(label, sub=False):
    cls = "rule sub" if sub else "rule"
    out.append(
        "<div class=\"" + cls + "\"><span class=\"lead\"></span>"
        "<span class=\"k\">" + esc(label) + "</span><span class=\"fill\"></span></div>"
    )


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
out.append("<script>")
out.append(BOOT_SCRIPT)
out.append("</script>")
out.append("<div class=\"wrap\">")

# Header
out.append("<div class=\"top\">")
out.append("<div class=\"brand\">")
out.append("<span class=\"name\">arax-preview</span>")
out.append("<span class=\"sub\">" + esc(HOST_NAME) + "</span>")
out.append("</div>")
out.append("<div class=\"themes\" id=\"theme-switch\" role=\"group\" aria-label=\"Colour theme\">")
for choice, label in (("system", "sys"), ("light", "light"), ("dark", "dark")):
    out.append(
        "<button type=\"button\" data-theme-choice=\"" + choice + "\" aria-pressed=\"false\">"
        + esc(label) + "</button>"
    )
out.append("</div>")
out.append("</div>")

# Host
rule("host")
out.append("<div class=\"panel host\">")
out.append("<dl class=\"kv\">")
for key, value in host_facts():
    out.append("<dt>" + esc(key) + "</dt><dd>" + esc(value) + "</dd>")
out.append("</dl>")
out.append("<div class=\"metrics\" id=\"host-metrics\">")
for mid, label, value, pct, state in host_metrics():
    width = "" if pct is None else "width:" + str(pct) + "%"
    out.append(
        "<div class=\"metric\" id=\"" + esc(mid) + "\" data-state=\"" + esc(state) + "\">"
        "<span class=\"mk\">" + esc(label) + "</span>"
        "<span class=\"mv num\">" + esc(value) + "</span>"
        "<span class=\"meter\"><span class=\"fill\" style=\"" + esc(width) + "\"></span></span>"
        "</div>"
    )
out.append("</div>")
out.append("</div>")

out.append(
    "<div class=\"pulse\" id=\"host-pulse\"><span class=\"dot\"></span>"
    "<span>live</span><span class=\"num\" id=\"host-sample\" data-epoch=\"" + esc(sampled_epoch)
    + "\" data-at=\"" + esc(sample_hms) + "\">last sample " + esc(sample_hms) + " (0 s ago)</span></div>"
)

rule("containers", sub=True)
out.append("<div class=\"scroll\"><table class=\"rpt\" id=\"host-containers\">")
out.append("<thead><tr><th>container</th><th>mem</th><th>cpu</th></tr></thead>")
out.append("<tbody>")
stats = container_stats()
if stats:
    for name, mem, cpu in stats:
        out.append(
            "<tr><td>" + esc(name) + "</td><td class=\"num\">" + esc(mem)
            + "</td><td class=\"num\">" + esc(cpu) + "</td></tr>"
        )
else:
    out.append("<tr><td colspan=\"3\">no preview containers running</td></tr>")
out.append("</tbody></table></div>")

# Previews
rule("previews")
if not previews:
    out.append("<div class=\"empty\">no previews deployed right now</div>")

for item in previews:
    pr = item["pr"]
    path = "/" + prefix + pr
    url = base_url + path + "/"
    status_path = path + "/api/arax/v1.4/status"
    loop = "127.0.0.1:" + str(port_base + int(pr))
    sha = item["sha"]

    out.append("<div class=\"pv\">")
    out.append("<div class=\"pv-head\">")
    out.append(
        "<span class=\"pr\"><a href=\"https://github.com/" + esc(repo) + "/pull/" + esc(pr)
        + "\">PR #" + esc(pr) + "</a></span>"
    )
    out.append("<span class=\"repo\">" + esc(repo) + "#" + esc(pr) + "</span>")
    out.append("<span class=\"branch\">" + esc(item["branch"]) + "</span>")
    if sha and sha != "unknown":
        out.append(
            "<span class=\"sha\"><a href=\"https://github.com/" + esc(repo) + "/commit/" + esc(sha)
            + "\">" + esc(sha[:7]) + "</a></span>"
        )
    else:
        out.append("<span class=\"sha\">unknown</span>")
    if item["state"]:
        out.append(
            "<span class=\"health\"><span class=\"dot\" data-status=\"" + esc(status_path)
            + "\" title=\"health unknown\"></span>health</span>"
        )
    out.append("</div>")

    out.append("<dl class=\"kv\">")
    if item["state"]:
        out.append(
            "<dt>url</dt><dd><a href=\"" + esc(url) + "\">" + esc(url) + "</a> "
            "<span class=\"loop\">" + esc(loop) + "</span></dd>"
        )
        state_color = "var(--ok)" if item["state"] == "running" else "var(--warn)"
        out.append(
            "<dt>container</dt><dd style=\"color:" + state_color + "\">" + esc(item["state"]) + "</dd>"
        )
    else:
        out.append(
            "<dt>url</dt><dd>" + esc(url) + " <span class=\"loop\">once the container is up</span></dd>"
        )
        out.append("<dt>container</dt><dd style=\"color:var(--warn)\">not created yet</dd>")
    if item["command"]:
        out.append("<dt>command</dt><dd>/" + esc(item["command"]) + "</dd>")
    if item["created"]:
        out.append("<dt>created</dt><dd>" + esc(item["created"]) + "</dd>")
    out.append("</dl>")

    # Stage rows
    if item["has_state"]:
        rule("stages", sub=True)
        out.append("<div class=\"stages\">")
        for key, label, filename in STAGES:
            entry = item["stages"].get(key)
            if not isinstance(entry, dict):
                entry = {}
            status = entry.get("status") or "pending"
            detail = str(entry.get("detail") or "")
            since = clock(entry.get("started_at"))
            if status == "running":
                glyph = "<span class=\"spinner\"></span>"
                text = label + " running"
                if since:
                    text = text + " since " + since
                dim = ""
            elif status == "failed":
                glyph = "<span class=\"g bad\">&#10007;</span>"
                text = label + " failed"
                dim = detail
            elif status == "done":
                glyph = "<span class=\"g ok\">&#10003;</span>"
                text = label + " done"
                dim = detail
            else:
                glyph = "<span class=\"g pending\">&#183;</span>"
                text = label + " pending"
                dim = ""
            row = "<div class=\"check\">" + glyph + "<span class=\"t\">" + esc(text)
            if dim:
                row += " <span class=\"d\">" + esc(dim) + "</span>"
            row += "</span></div>"
            out.append(row)
        out.append("</div>")

    # smoke: a real table plus the raw file
    smoke_text = read_data_file(pr, "smoke.md")
    if smoke_text is not None:
        headers, srows = parse_md_table(smoke_text)
        if srows:
            rule("smoke", sub=True)
            out.append("<div class=\"scroll\"><table class=\"rpt\">")
            out.append("<thead><tr><th>check</th><th>result</th><th>detail</th></tr></thead><tbody>")
            for cells in srows:
                check, result, det = fit(cells, 3)
                low = result.strip().lower()
                if low == "pass":
                    rcell = "<td class=\"cell-ok\">&#10003; pass</td>"
                elif low in ("fail", "failed"):
                    rcell = "<td class=\"cell-bad\">&#10007; FAIL</td>"
                else:
                    rcell = "<td>" + esc(result) + "</td>"
                out.append(
                    "<tr><td>" + esc(check) + "</td>" + rcell + "<td>" + esc(det) + "</td></tr>"
                )
            out.append("</tbody></table></div>")
            out.append("<details><summary>smoke.md raw</summary><pre>"
                       + esc(smoke_text.rstrip()) + "</pre></details>")

    # pytest: the summary as a status row, then the full captured output
    pytest_text = read_data_file(pr, "pytest.md")
    pytest_full = read_data_file(pr, "pytest-full.txt")
    if pytest_text is not None or pytest_full is not None:
        rule("pytest", sub=True)
        summary = ""
        passed = None
        if pytest_text is not None:
            for line in pytest_text.splitlines():
                stripped = line.strip()
                if stripped.startswith("**pytest:**"):
                    summary = stripped[len("**pytest:**"):].strip()
                    passed = (" 0 failed" in summary) or ("failed" not in summary)
                    break
        if summary:
            if passed:
                glyph = "<span class=\"g ok\">&#10003;</span>"
            else:
                glyph = "<span class=\"g bad\">&#10007;</span>"
            out.append(
                "<div class=\"stages\"><div class=\"check\">" + glyph
                + "<span class=\"t\">" + esc(summary) + "</span></div></div>"
            )
        if pytest_full is not None:
            out.append("<details><summary>pytest output</summary><pre>"
                       + esc(pytest_full.rstrip()) + "</pre></details>")
        elif pytest_text is not None:
            out.append("<details><summary>pytest.md raw</summary><pre>"
                       + esc(pytest_text.rstrip()) + "</pre></details>")

    # live queries: a real table plus per query detail
    queries_text = read_data_file(pr, "queries.md")
    if queries_text is not None:
        headers, qrows = parse_md_table(queries_text)
        if qrows:
            rule("live queries", sub=True)
            out.append("<div class=\"scroll\"><table class=\"rpt\">")
            out.append(
                "<thead><tr><th>#</th><th>query</th><th>HTTP</th><th>s</th><th>results</th>"
                "<th>KG nodes/edges</th><th>status</th></tr></thead><tbody>"
            )
            for cells in qrows:
                num, query, code, secs, results, kg, status = fit(cells, 7)
                degraded = num.startswith("⚠")
                num = num.lstrip("⚠").strip()
                row_cls = " class=\"bad-row\"" if degraded else ""
                mark = "<span class=\"cell-bad\">! </span>" if degraded else ""
                out.append(
                    "<tr" + row_cls + "><td>" + mark + esc(num) + "</td><td>" + esc(query)
                    + "</td><td class=\"num\">" + esc(code) + "</td><td class=\"num\">" + esc(secs)
                    + "</td><td class=\"num\">" + esc(results) + "</td><td class=\"num\">" + esc(kg)
                    + "</td><td>" + esc(status) + "</td></tr>"
                )
            out.append("</tbody></table></div>")

        # Per query detail files, query-1.txt .. query-4.txt
        detail_items = []
        for index in range(1, 9):
            detail = read_data_file(pr, "query-%d.txt" % index)
            if detail is None:
                continue
            label = "query %d" % index
            first = detail.strip().splitlines()[0] if detail.strip() else ""
            if first.startswith("query"):
                name = first[len("query"):].strip()
                if name:
                    label = name + " detail"
            detail_items.append((label, detail))
        if detail_items:
            out.append("<div class=\"detail-grid\">")
            for label, detail in detail_items:
                out.append("<details><summary>" + esc(label) + "</summary><pre>"
                           + esc(detail.rstrip()) + "</pre></details>")
            out.append("</div>")

    # deploy log and build log, kept distinct
    logs = [("deploy-log.txt", "deploy log"), ("build-log.txt", "build log")]
    log_bodies = [(label, read_data_file(pr, name)) for name, label in logs]
    if any(body is not None for _, body in log_bodies):
        rule("logs", sub=True)
        for label, body in log_bodies:
            if body is None:
                continue
            out.append("<details><summary>" + esc(label) + "</summary><pre>"
                       + esc(body.rstrip()) + "</pre></details>")

    out.append("</div>")

out.append("<footer>")
out.append("<p>page generated " + esc(generated) + "</p>")
out.append(
    "<p>rewritten on every deploy event and every 5 minutes from cron. the host metrics refresh "
    "on their own every 15 seconds from host.json, and the health dot on each preview is checked "
    "by your browser. with JavaScript off the page still renders as it was at generation time.</p>"
)
out.append("</footer>")
out.append("</div>")

# ---------------------------------------------------------------------------
# The only script on the page. It handles the theme switch, refreshes the host
# metrics from host.json every 15 seconds and asks each preview whether it is
# alive. Everything it touches is already on the page, so JavaScript off loses
# the live updates and nothing else.
# ---------------------------------------------------------------------------
SCRIPT = """(function () {
  var THEME_KEY = "arax-preview-theme";
  var themeSwitch = document.getElementById("theme-switch");

  function storedChoice() {
    try {
      var value = localStorage.getItem(THEME_KEY);
      return (value === "light" || value === "dark") ? value : "system";
    } catch (error) {
      return "system";
    }
  }

  function paintChoice(choice) {
    if (!themeSwitch) { return; }
    var buttons = themeSwitch.querySelectorAll("button[data-theme-choice]");
    Array.prototype.forEach.call(buttons, function (button) {
      var mine = button.getAttribute("data-theme-choice") === choice;
      button.setAttribute("aria-pressed", mine ? "true" : "false");
    });
  }

  function applyChoice(choice) {
    var root = document.documentElement;
    if (choice === "light" || choice === "dark") {
      root.setAttribute("data-theme", choice);
    } else {
      root.removeAttribute("data-theme");
    }
    try {
      if (choice === "light" || choice === "dark") {
        localStorage.setItem(THEME_KEY, choice);
      } else {
        localStorage.removeItem(THEME_KEY);
      }
    } catch (error) {
      // The choice still applies to this page, it just cannot be remembered.
    }
    paintChoice(choice);
  }

  if (themeSwitch) {
    paintChoice(storedChoice());
    themeSwitch.addEventListener("click", function (event) {
      var node = event.target;
      while (node && node !== themeSwitch) {
        if (node.getAttribute && node.getAttribute("data-theme-choice")) {
          applyChoice(node.getAttribute("data-theme-choice"));
          return;
        }
        node = node.parentNode;
      }
    });
  }

  if (typeof fetch !== "function") { return; }
  var STALE_AFTER = 60;
  var NVCPU = 2;
  var sample = document.getElementById("host-sample");
  var pulse = document.getElementById("host-pulse");
  var metrics = document.getElementById("host-metrics");
  var table = document.getElementById("host-containers");
  var sampledEpoch = 0;
  var sampledText = "";
  var baseAge = 0;
  var stampMs = Date.now();

  if (sample) {
    sampledEpoch = Number(sample.getAttribute("data-epoch")) || 0;
    sampledText = sample.getAttribute("data-at") || "";
  }

  function isNumber(value) {
    return typeof value === "number" && isFinite(value);
  }

  function clampPct(fraction) {
    var pct = Math.round(fraction * 100);
    if (pct < 0) { return 0; }
    if (pct > 100) { return 100; }
    return pct;
  }

  function setMetric(id, value, pct, state) {
    var node = document.getElementById(id);
    if (!node) { return; }
    var mv = node.querySelector(".mv");
    var fill = node.querySelector(".fill");
    if (mv) { mv.textContent = value; }
    if (fill) { fill.style.width = (pct === null ? 0 : pct) + "%"; }
    node.setAttribute("data-state", state || "");
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
      var only = cell("no preview containers running");
      only.setAttribute("colspan", "3");
      empty.appendChild(only);
      body.appendChild(empty);
      return;
    }
    rows.forEach(function (row) {
      var line = document.createElement("tr");
      line.appendChild(cell(row.name || ""));
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
      var memState = "";
      if (isNumber(limits.ram_min_mb) && data.mem_available_mb < limits.ram_min_mb) {
        memState = "bad";
      }
      setMetric("metric-mem",
        (data.mem_available_mb / 1024).toFixed(1) + " GB free / " +
        (data.mem_total_mb / 1024).toFixed(1) + " GB",
        clampPct((data.mem_total_mb - data.mem_available_mb) / data.mem_total_mb), memState);
    } else {
      setMetric("metric-mem", "no data", null, "");
    }

    if (isNumber(data.disk_avail_gb) && isNumber(data.disk_size_gb) && data.disk_size_gb) {
      var diskState = "";
      if (isNumber(limits.disk_floor_gb) && data.disk_avail_gb < limits.disk_floor_gb) {
        diskState = "bad";
      }
      setMetric("metric-disk",
        data.disk_avail_gb + " GB free / " + data.disk_size_gb + " GB",
        clampPct((data.disk_size_gb - data.disk_avail_gb) / data.disk_size_gb), diskState);
    } else {
      setMetric("metric-disk", "no data", null, "");
    }

    if (isNumber(data.load1)) {
      var loadState = "";
      if (data.load1 > 2 * NVCPU) { loadState = "bad"; }
      else if (data.load1 > NVCPU) { loadState = "warn"; }
      var loadText = data.load1.toFixed(2);
      if (isNumber(data.load5)) { loadText += "  " + data.load5.toFixed(2); }
      if (isNumber(data.load15)) { loadText += "  " + data.load15.toFixed(2); }
      setMetric("metric-load", loadText, clampPct(data.load1 / NVCPU), loadState);
    } else {
      setMetric("metric-load", "no data", null, "");
    }

    if (isNumber(data.slots_used) && isNumber(data.slots_max) && data.slots_max) {
      setMetric("metric-slots", data.slots_used + " / " + data.slots_max,
        clampPct(data.slots_used / data.slots_max),
        data.slots_used >= data.slots_max ? "bad" : "");
    } else {
      setMetric("metric-slots", "no data", null, "");
    }

    applyContainers(Array.isArray(data.containers) ? data.containers : []);

    if (isNumber(data.sampled_epoch) && data.sampled_epoch !== sampledEpoch) {
      sampledEpoch = data.sampled_epoch;
      var at = String(data.sampled_at || "");
      var t = at.indexOf("T");
      var z = at.indexOf("Z");
      if (t >= 0 && z > t) {
        sampledText = at.substring(t + 1, z) + " UTC";
      } else {
        sampledText = at;
      }
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
    if (pulse) { pulse.className = stale ? "pulse stale" : "pulse"; }
    if (metrics) { metrics.className = stale ? "metrics stale" : "metrics"; }
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
