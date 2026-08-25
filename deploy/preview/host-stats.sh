#!/usr/bin/env bash
#
# Sample the host numbers the /previews/ status page shows and write them to
# ${PREVIEW_WEB_ROOT}/host.json every 15 seconds, so the page can refresh its
# tiles without the page itself being regenerated. The page is static and
# nothing on this host answers requests dynamically, so the file on disk is
# the whole interface: the browser fetches it, and this loop rewrites it.
#
# Usage: host-stats.sh [--once]
#
#   --once  write one sample and exit. Used by the installer, so that
#           host.json exists before the service has ticked, and by tests.
#
# Installed as the systemd unit arax-preview-stats.service by
# install-nginx-include.sh. Issue #2846.

set -o nounset -o pipefail -o errexit

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
. "${SCRIPT_DIR}/lib.sh"
preview_validate_env

# Seconds between samples. The page fetches host.json on the same period.
PREVIEW_HOST_STATS_INTERVAL="${PREVIEW_HOST_STATS_INTERVAL:-15}"

usage() {
    cat >&2 <<'USAGE_EOF'
Usage: host-stats.sh [--once]

Writes ${PREVIEW_WEB_ROOT}/host.json every PREVIEW_HOST_STATS_INTERVAL
seconds, 15 by default. With --once it writes a single sample and exits.
USAGE_EOF
    exit 2
}

ONCE="no"
while [ "$#" -gt 0 ]; do
    case "$1" in
        --once) ONCE="yes"; shift ;;
        -h|--help) usage ;;
        *) die "unknown argument '$1'" ;;
    esac
done

require_int "${PREVIEW_HOST_STATS_INTERVAL}" "PREVIEW_HOST_STATS_INTERVAL"
[ -n "${PREVIEW_WEB_ROOT}" ] || die "PREVIEW_WEB_ROOT must not be empty"

HOST_JSON_FILE="${PREVIEW_WEB_ROOT}/host.json"
# Written next to the real file, on the same filesystem, so the rename that
# publishes it is atomic and a browser can never read half a sample.
HOST_JSON_TMP="${PREVIEW_WEB_ROOT}/.host.json.${$}"

# write_host_json
# One sample. Every collector is best effort and a number that cannot be read
# is written as null rather than left out, so the page can tell "no data"
# from "zero". Returns non-zero only so the caller can log it once.
write_host_json() {
    local mem disk load slots stats json

    mem="$(host_mem_mb)"
    disk="$(host_disk_gb)"
    load="$(host_load)"
    slots="$(host_slots_used)"
    stats="$(host_container_stats)"

    if ! json="$(HOST_JSON_MEM="${mem}" \
        HOST_JSON_DISK="${disk}" \
        HOST_JSON_LOAD="${load}" \
        HOST_JSON_SLOTS="${slots}" \
        HOST_JSON_CONTAINERS="${stats}" \
        python3 - <<'PYTHON_EOF'
import json
import os
import sys
import time


def numbers(name, count):
    """The first <count> whitespace separated integers of an environment
    variable, with None wherever the collector printed nothing."""
    parts = os.environ.get(name, "").split()
    out = []
    for index in range(count):
        try:
            out.append(int(parts[index]))
        except (IndexError, ValueError):
            out.append(None)
    return out


def decimals(name, count):
    parts = os.environ.get(name, "").split()
    out = []
    for index in range(count):
        try:
            out.append(float(parts[index]))
        except (IndexError, ValueError):
            out.append(None)
    return out


def setting(name, fallback=None):
    try:
        return int(os.environ.get(name, "").strip())
    except (TypeError, ValueError):
        return fallback


mem_available, mem_total = numbers("HOST_JSON_MEM", 2)
disk_size, disk_avail = numbers("HOST_JSON_DISK", 2)
load1, load5, load15 = decimals("HOST_JSON_LOAD", 3)
slots_used = numbers("HOST_JSON_SLOTS", 1)[0]

containers = []
for line in os.environ.get("HOST_JSON_CONTAINERS", "").splitlines():
    if not line.strip():
        continue
    fields = line.split("\t")
    if len(fields) < 3:
        # Older docker builds hand the format string through without turning
        # the escape into a real tab.
        fields = line.split("\\t")
    if len(fields) < 3:
        continue
    name, usage, cpu = [item.strip() for item in fields[:3]]
    limit = ""
    if "/" in usage:
        usage, limit = [part.strip() for part in usage.split("/", 1)]
    containers.append(
        {"name": name, "mem_usage": usage, "mem_limit": limit, "cpu_pct": cpu}
    )
containers.sort(key=lambda item: item["name"])

# The disk floor the preflight check refuses a deploy under: the larger of the
# absolute guard and the percentage of the volume. The page colours its tile
# on the same number, so it turns red exactly when the next deploy would be
# turned away.
floor_gb = setting("PREVIEW_MIN_FREE_DISK_GB", 0) or 0
percent = setting("PREVIEW_MIN_FREE_DISK_PCT", 0) or 0
if disk_size:
    percent_floor = disk_size * percent // 100
    if percent_floor > floor_gb:
        floor_gb = percent_floor

now = int(time.time())
document = {
    "sampled_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
    "sampled_epoch": now,
    "mem_total_mb": mem_total,
    "mem_available_mb": mem_available,
    "disk_size_gb": disk_size,
    "disk_avail_gb": disk_avail,
    "load1": load1,
    "load5": load5,
    "load15": load15,
    "slots_used": slots_used,
    "slots_max": setting("PREVIEW_MAX_ACTIVE"),
    "containers": containers,
    "thresholds": {
        "ram_min_mb": setting("PREVIEW_MIN_FREE_RAM_MB"),
        "disk_floor_gb": floor_gb,
    },
}
sys.stdout.write(json.dumps(document, indent=2, sort_keys=True) + "\n")
PYTHON_EOF
)"; then
        return 1
    fi

    if ! ${SUDO} mkdir -p "${PREVIEW_WEB_ROOT}" 2>/dev/null; then
        return 1
    fi
    if ! printf '%s\n' "${json}" | ${SUDO} tee "${HOST_JSON_TMP}" >/dev/null; then
        ${SUDO} rm -f "${HOST_JSON_TMP}" 2>/dev/null || true
        return 1
    fi
    ${SUDO} chmod 644 "${HOST_JSON_TMP}" 2>/dev/null || true
    if ! ${SUDO} mv -f "${HOST_JSON_TMP}" "${HOST_JSON_FILE}" 2>/dev/null; then
        ${SUDO} rm -f "${HOST_JSON_TMP}" 2>/dev/null || true
        return 1
    fi
    return 0
}

cleanup() {
    ${SUDO} rm -f "${HOST_JSON_TMP}" 2>/dev/null || true
}
trap cleanup EXIT

if [ "${ONCE}" = "yes" ]; then
    write_host_json || die "could not write ${HOST_JSON_FILE}"
    log "wrote ${HOST_JSON_FILE}"
    exit 0
fi

log "sampling the host into ${HOST_JSON_FILE} every ${PREVIEW_HOST_STATS_INTERVAL}s"

# One line in the journal when the sampler starts failing and one when it
# recovers, rather than one every 15 seconds forever.
HEALTHY="unknown"
while true; do
    if write_host_json; then
        if [ "${HEALTHY}" != "yes" ]; then
            log "wrote ${HOST_JSON_FILE}"
            HEALTHY="yes"
        fi
    else
        if [ "${HEALTHY}" != "no" ]; then
            log "WARNING: could not write ${HOST_JSON_FILE}, will keep trying"
            HEALTHY="no"
        fi
    fi
    sleep "${PREVIEW_HOST_STATS_INTERVAL}"
done
