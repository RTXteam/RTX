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

die() {
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
# Status page
# ---------------------------------------------------------------------------

# collect_host_stats
# Reads the host numbers the status page shows into HOST_* variables and
# exports them, because the python that renders the page must not shell out.
# Every collector is best effort: one that cannot read its number leaves the
# variable empty and the page leaves that tile or that table out.
collect_host_stats() {
    HOST_MEM_AVAIL_MB=""
    HOST_MEM_TOTAL_MB=""
    HOST_DISK_AVAIL_GB=""
    HOST_DISK_SIZE_GB=""
    HOST_LOAD_1=""
    HOST_LOAD_5=""
    HOST_LOAD_15=""
    HOST_SLOTS_USED=""
    HOST_SLOTS_MAX="${PREVIEW_MAX_ACTIVE}"
    HOST_CONTAINER_STATS=""

    # Memory. The available column rather than the free one, same as the
    # preflight check, because page cache is reclaimable.
    local mem_line avail_mb total_mb
    mem_line="$(free -m 2>/dev/null | awk '/^Mem:/{print $7, $2}' || true)"
    avail_mb="$(printf '%s' "${mem_line}" | awk '{print $1}' | tr -dc '0-9')"
    total_mb="$(printf '%s' "${mem_line}" | awk '{print $2}' | tr -dc '0-9')"
    if [ -n "${avail_mb}" ] && [ -n "${total_mb}" ]; then
        HOST_MEM_AVAIL_MB="${avail_mb}"
        HOST_MEM_TOTAL_MB="${total_mb}"
    fi

    # Disk, the same call the preflight check makes, so the page and the
    # refusal message can never disagree about how much room is left.
    local df_line size_gb avail_gb
    df_line="$(df -BG --output=size,avail /var/lib/docker 2>/dev/null \
        || df -BG --output=size,avail / 2>/dev/null || true)"
    df_line="$(printf '%s' "${df_line}" | tail -n 1)"
    size_gb="$(printf '%s' "${df_line}" | awk '{print $1}' | tr -dc '0-9')"
    avail_gb="$(printf '%s' "${df_line}" | awk '{print $2}' | tr -dc '0-9')"
    if [ -n "${size_gb}" ] && [ -n "${avail_gb}" ]; then
        HOST_DISK_SIZE_GB="${size_gb}"
        HOST_DISK_AVAIL_GB="${avail_gb}"
    fi

    # Load. There is no /proc on a mac, so a missing file is expected and
    # simply drops the tile.
    local one five fifteen rest
    if [ -r /proc/loadavg ]; then
        read -r one five fifteen rest < /proc/loadavg || true
        case "${one}:${five}:${fifteen}" in
            *[!0-9.:]*|*::*) : ;;
            *)
                HOST_LOAD_1="${one}"
                HOST_LOAD_5="${five}"
                HOST_LOAD_15="${fifteen}"
                ;;
        esac
    fi

    # Preview slots. Every preview on the box counts, running or not, which
    # is the same set the garbage collector and the preflight count walk.
    local used
    used="$(list_preview_prs | sort -n -u | wc -l | tr -dc '0-9' || true)"
    if [ -n "${used}" ]; then
        HOST_SLOTS_USED="${used}"
    fi

    # Per container memory and cpu. docker stats can hang for a long time on
    # a wedged daemon and this runs on the path of every deploy, so it gets a
    # hard time limit and the table is dropped rather than waited for.
    local stats_raw
    if command -v timeout >/dev/null 2>&1; then
        # DOCKER is "sudo docker", two words on purpose, so it has to split.
        # shellcheck disable=SC2086
        stats_raw="$(timeout 20 ${DOCKER} stats --no-stream \
            --format '{{.Name}}\t{{.MemUsage}}\t{{.CPUPerc}}' 2>/dev/null || true)"
    else
        stats_raw="$(${DOCKER} stats --no-stream \
            --format '{{.Name}}\t{{.MemUsage}}\t{{.CPUPerc}}' 2>/dev/null || true)"
    fi
    HOST_CONTAINER_STATS="$(printf '%s\n' "${stats_raw}" | grep '^rtx_' || true)"

    export HOST_MEM_AVAIL_MB HOST_MEM_TOTAL_MB HOST_DISK_AVAIL_GB HOST_DISK_SIZE_GB \
        HOST_LOAD_1 HOST_LOAD_5 HOST_LOAD_15 HOST_SLOTS_USED HOST_SLOTS_MAX \
        HOST_CONTAINER_STATS
}

# write_status_page
# Regenerates ${PREVIEW_WEB_ROOT}/index.html from the docker labels of every
# preview container on the box, the host numbers collected just above, and
# whatever per-PR report files exist at generation time. Called by deploy.sh,
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

    collect_host_stats

    local rows html
    # One tab separated line per preview: pr, branch, sha, created, state.
    rows="$(${DOCKER} ps -a --filter 'label=arax.preview=true' \
        --format '{{.Label "arax.preview.pr"}}\t{{.Label "arax.preview.branch"}}\t{{.Label "arax.preview.sha"}}\t{{.Label "arax.preview.created"}}\t{{.State}}' \
        2>/dev/null || true)"

    if ! html="$(printf '%s\n' "${rows}" | python3 -c '
import html as html_module
import os
import sys
import time

web_root = os.environ.get("PREVIEW_WEB_ROOT", "/var/www/arax-preview")
prefix = os.environ.get("PREVIEW_PATH_PREFIX", "")
base_url = os.environ.get("PREVIEW_PUBLIC_BASE_URL", "https://cicd.rtx.ai").rstrip("/")
repo = os.environ.get("PREVIEW_REPO", "RTXteam/RTX")
ttl = os.environ.get("PREVIEW_TTL_DAYS", "7")

# What the host is, for the subtitle under the name. One host, so it is
# written down here rather than read off the machine on every deploy.
HOST_NAME = "cicd.rtx.ai"
HOST_SPEC = "m5a.large, 2 vCPU, 7.5 GB, no swap"

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


# The compact one line per check summary above the expanders. Each builder
# returns a list of (text, state) pairs, where the state is True for a pass,
# False for a failure and None for something that did not run. Anything that
# cannot be parsed drops its rows rather than breaking the page.
def pytest_rows(pr):
    text = read_data_file(pr, "pytest.md")
    if text is None:
        return [("pytest: not run", None)]
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
        return [("live queries: not run", None)]
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


def status_rows(pr):
    rows = []
    for builder in (pytest_rows, query_rows, smoke_rows):
        try:
            rows.extend(builder(pr))
        except Exception:
            continue
    return rows


# The host tiles. Each one is (value, label, state, title), where the state is
# ok or bad or the empty string for a number with no threshold behind it. The
# thresholds are the ones the preflight check refuses on, read from the same
# environment variables, so the page turns red exactly when a deploy would be
# turned away.
def host_tiles():
    tiles = []

    mem_avail = env_int("HOST_MEM_AVAIL_MB")
    mem_total = env_int("HOST_MEM_TOTAL_MB")
    if mem_avail is not None and mem_total:
        floor_mb = env_int("PREVIEW_MIN_FREE_RAM_MB")
        state = "ok"
        if floor_mb is not None and mem_avail < floor_mb:
            state = "bad"
        tiles.append(
            (
                "%.1f GB" % (mem_avail / 1024.0),
                "memory available of %.1f GB" % (mem_total / 1024.0),
                state,
                "%d MB available, floor %s MB" % (mem_avail, floor_mb),
            )
        )

    disk_avail = env_int("HOST_DISK_AVAIL_GB")
    disk_size = env_int("HOST_DISK_SIZE_GB")
    if disk_avail is not None and disk_size:
        floor_gb = env_int("PREVIEW_MIN_FREE_DISK_GB") or 0
        pct = env_int("PREVIEW_MIN_FREE_DISK_PCT") or 0
        pct_floor = disk_size * pct // 100
        if pct_floor > floor_gb:
            floor_gb = pct_floor
        state = "bad" if disk_avail < floor_gb else "ok"
        tiles.append(
            (
                "%d GB" % disk_avail,
                "disk free of %d GB" % disk_size,
                state,
                "floor %d GB, the larger of the absolute and the percentage guard" % floor_gb,
            )
        )

    load_1 = env_float("HOST_LOAD_1")
    if load_1 is not None:
        detail = " ".join(
            [
                os.environ.get("HOST_LOAD_1", ""),
                os.environ.get("HOST_LOAD_5", ""),
                os.environ.get("HOST_LOAD_15", ""),
            ]
        ).strip()
        tiles.append(("%.2f" % load_1, "load 1m", "", "1m 5m 15m: " + detail))

    slots_used = env_int("HOST_SLOTS_USED")
    slots_max = env_int("HOST_SLOTS_MAX")
    if slots_used is not None and slots_max:
        state = "bad" if slots_used >= slots_max else "ok"
        tiles.append(
            (
                "%d/%d" % (slots_used, slots_max),
                "preview slots",
                state,
                "PREVIEW_MAX_ACTIVE is %d" % slots_max,
            )
        )

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


previews = []
for line in sys.stdin.read().splitlines():
    if not line.strip():
        continue
    fields = line.split("\t")
    if len(fields) < 5:
        # Older docker builds hand the format string through without turning
        # the escape into a real tab.
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
    previews.append(
        {
            "pr": pr,
            "branch": branch or "unknown",
            "sha": sha,
            "created": created_text,
            "state": state or "unknown",
        }
    )
previews.sort(key=lambda item: int(item["pr"]))

generated = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())

out = []
out.append("<!DOCTYPE html>")
out.append("<html lang=\"en\">")
out.append("<head>")
out.append("<meta charset=\"utf-8\">")
out.append("<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">")
out.append("<title>ARAX preview host</title>")
out.append("<style>")
out.append(""":root { color-scheme: light; }
* { box-sizing: border-box; }
body { margin: 0; background: #f7f7f8; color: #1f2937;
       font: 15px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, sans-serif; }
.wrap { max-width: 1100px; margin: 0 auto; padding: 32px 20px 64px; }
a { color: #2563eb; text-decoration: none; }
a:hover { text-decoration: underline; }
code { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 13px; }
.top { display: flex; align-items: flex-start; justify-content: space-between;
       gap: 16px; flex-wrap: wrap; }
h1 { font-size: 22px; font-weight: 600; margin: 0; }
.spec { color: #6b7280; font-size: 13px; margin: 4px 0 0; }
.asof { color: #6b7280; font-size: 13px; white-space: nowrap; }
p.lede { color: #6b7280; margin: 16px 0 0; max-width: 78ch; }
h2 { font-size: 13px; font-weight: 600; color: #6b7280; margin: 32px 0 12px; }
.tiles { display: flex; flex-wrap: wrap; gap: 12px; margin: 0 0 12px; }
.tile { flex: 1 1 200px; background: #ffffff; border: 1px solid #e5e7eb;
        border-radius: 8px; padding: 16px 18px; }
.tile .value { font-size: 24px; font-weight: 600; line-height: 1.25; }
.tile.ok .value { color: #059669; }
.tile.bad .value { color: #dc2626; }
.tile .label { font-size: 13px; color: #6b7280; margin-top: 4px; }
.scroll { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; background: #ffffff;
        border: 1px solid #e5e7eb; border-radius: 8px; font-size: 13px; }
th { text-align: left; font-weight: 600; color: #6b7280; padding: 10px 16px;
     border-bottom: 1px solid #e5e7eb; white-space: nowrap; }
td { padding: 10px 16px; border-top: 1px solid #f3f4f6; white-space: nowrap; }
tr:first-child td { border-top: none; }
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
.checks { border-top: 1px solid #f3f4f6; margin-top: 16px; padding-top: 12px; }
.check { display: flex; align-items: center; gap: 9px; font-size: 14px; padding: 2px 0; }
.chip { flex: none; display: inline-flex; align-items: center; justify-content: center;
        width: 18px; height: 18px; border-radius: 5px; font-size: 11px; font-weight: 700;
        color: #6b7280; background: #f3f4f6; }
.chip.ok { color: #059669; background: #ecfdf5; }
.chip.bad { color: #dc2626; background: #fef2f2; }
details { margin-top: 10px; }
summary { cursor: pointer; color: #6b7280; font-size: 13px; }
pre { overflow-x: auto; background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 6px;
      padding: 12px 14px; margin: 8px 0 4px; font-size: 12px; line-height: 1.5;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      white-space: pre-wrap; overflow-wrap: anywhere; }
.empty { color: #6b7280; background: #ffffff; border: 1px dashed #e5e7eb;
         border-radius: 8px; padding: 24px; text-align: center; }
footer { color: #6b7280; font-size: 13px; border-top: 1px solid #e5e7eb;
         margin-top: 36px; padding-top: 16px; }""")
out.append("</style>")
out.append("</head>")
out.append("<body>")
out.append("<div class=\"wrap\">")
out.append("<div class=\"top\">")
out.append("<div><h1>" + esc(HOST_NAME) + "</h1><p class=\"spec\">" + esc(HOST_SPEC) + "</p></div>")
out.append("<div class=\"asof\">as of " + esc(generated) + "</div>")
out.append("</div>")
out.append(
    "<p class=\"lede\">Every card below is a per-PR preview deployment of "
    "<a href=\"https://github.com/" + esc(repo) + "\">" + esc(repo) + "</a>, built from that pull "
    "request and served from its own container. See <code>deploy/preview/README.md</code> in the "
    "repository for how they are made and torn down. Previews are public, unauthenticated and "
    "temporary: they are removed " + esc(ttl) + " days after they are deployed, or as soon as "
    "their pull request closes.</p>"
)

tiles = host_tiles()
stats = container_stats()
if tiles or stats:
    out.append("<h2>Host</h2>")
if tiles:
    out.append("<div class=\"tiles\">")
    for value, label, state, title in tiles:
        classes = "tile " + state if state else "tile"
        out.append(
            "<div class=\"" + esc(classes) + "\" title=\"" + esc(title) + "\">"
            "<div class=\"value\">" + esc(value) + "</div>"
            "<div class=\"label\">" + esc(label) + "</div></div>"
        )
    out.append("</div>")
if stats:
    out.append("<div class=\"scroll\"><table>")
    out.append("<tr><th>container</th><th>memory</th><th>cpu</th></tr>")
    for name, mem, cpu in stats:
        out.append(
            "<tr><td><code>" + esc(name) + "</code></td><td>" + esc(mem) + "</td><td>"
            + esc(cpu) + "</td></tr>"
        )
    out.append("</table></div>")

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
            "<code>" + esc(item["branch"]) + "</code> @ <a href=\"https://github.com/"
            + esc(repo) + "/commit/" + esc(sha) + "\"><code>" + esc(sha[:7]) + "</code></a>"
        )
    else:
        meta = "<code>" + esc(item["branch"]) + "</code> @ <code>unknown</code>"
    out.append("<div class=\"meta\">" + meta + "</div>")
    out.append("</div>")
    out.append(
        "<span class=\"dot\" data-status=\"" + esc(status_path) + "\" title=\"health unknown\">"
        "</span>"
    )
    out.append("</div>")
    out.append("<dl>")
    out.append("<dt>created</dt><dd>" + esc(item["created"]) + "</dd>")
    state_class = "running" if item["state"] == "running" else "stopped"
    out.append("<dt>state</dt><dd class=\"" + state_class + "\">" + esc(item["state"]) + "</dd>")
    out.append("<dt>preview</dt><dd><a href=\"" + esc(url) + "\">" + esc(url) + "</a></dd>")
    out.append("</dl>")
    checks = status_rows(pr)
    if checks:
        out.append("<div class=\"checks\">")
        for text, state in checks:
            if state is True:
                chip = "<span class=\"chip ok\">&#10003;</span>"
            elif state is False:
                chip = "<span class=\"chip bad\">&#10007;</span>"
            else:
                chip = "<span class=\"chip\">&#183;</span>"
            out.append("<div class=\"check\">" + chip + "<span>" + esc(text) + "</span></div>")
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
    "<footer>Generated " + esc(generated) + ". This page is rewritten on every deploy event and "
    "again every 5 minutes from cron, so the host numbers are never much older than that. The "
    "dots are live and are checked by your browser when the page loads.</footer>"
)
out.append("</div>")
out.append("<script>")
out.append("""(function () {
  if (typeof fetch !== "function") { return; }
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
})();""")
out.append("</script>")
out.append("</body>")
out.append("</html>")

sys.stdout.write("\n".join(out) + "\n")
')"; then
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
