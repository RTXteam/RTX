#!/usr/bin/env bash
#
# Garbage collect ARAX preview environments on cicd.rtx.ai. A preview goes
# away when it is older than the time to live, or when its pull request is no
# longer open. Merged pull requests are closed pull requests, so the state
# check covers them.
#
# Usage: gc.sh [--ttl-days N] [--dry-run]
#
# Set GITHUB_TOKEN or GH_TOKEN to enable the pull request state check. Without
# a token only the age rule applies.
#
# Issue #2846.

set -o nounset -o pipefail -o errexit

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
. "${SCRIPT_DIR}/lib.sh"
preview_validate_env

DRY_RUN="no"
while [ "$#" -gt 0 ]; do
    case "$1" in
        --ttl-days)
            PREVIEW_TTL_DAYS="${2:-}"
            require_int "${PREVIEW_TTL_DAYS}" "--ttl-days"
            shift 2
            ;;
        --dry-run)
            DRY_RUN="yes"
            shift
            ;;
        -h|--help)
            printf 'Usage: gc.sh [--ttl-days N] [--dry-run]\n' >&2
            exit 0
            ;;
        *)
            die "unknown argument '$1'"
            ;;
    esac
done

TOKEN="${GITHUB_TOKEN:-${GH_TOKEN:-}}"
TTL_SECONDS=$(( PREVIEW_TTL_DAYS * 86400 ))
NOW="$(date -u '+%s')"

log "garbage collecting previews, ttl ${PREVIEW_TTL_DAYS} days, dry run ${DRY_RUN}"
if [ -z "${TOKEN}" ]; then
    log "no GITHUB_TOKEN or GH_TOKEN in the environment, checking age only"
fi

# Asks the GitHub API whether a pull request is still open. Prints one of
# open, closed or unknown. Kept deliberately tolerant: a rate limited or
# unreachable API must never delete somebody's preview.
pr_state() {
    local pr="$1"
    local body
    body="$(curl -fsS -m 30 \
        -H "Authorization: Bearer ${TOKEN}" \
        -H "Accept: application/vnd.github+json" \
        "https://api.github.com/repos/${PREVIEW_REPO}/pulls/${pr}" 2>/dev/null || true)"
    if [ -z "${body}" ]; then
        printf 'unknown'
        return 0
    fi
    # python3.8 on the host, so no walrus and no match statement here
    printf '%s' "${body}" | python3 -c '
import json
import sys

try:
    data = json.load(sys.stdin)
except Exception:
    sys.stdout.write("unknown")
    sys.exit(0)

state = data.get("state")
merged = data.get("merged")
if state == "closed" or merged is True:
    sys.stdout.write("closed")
elif state == "open":
    sys.stdout.write("open")
else:
    sys.stdout.write("unknown")
'
}

human_age() {
    local seconds="$1"
    local days=$(( seconds / 86400 ))
    local hours=$(( (seconds % 86400) / 3600 ))
    printf '%sd%sh' "${days}" "${hours}"
}

PRS="$(list_preview_prs | sort -n -u)"

# The container sweep. An empty box is not a reason to stop: the status page
# data sweep below, the image prune and the log prune all still have work to
# do, and a pull request whose deploy died before it ever made a container
# leaves nothing here but a data directory.
if [ -z "${PRS}" ]; then
    printf 'No ARAX preview containers on this host.\n\n'
else
    ROWS=()
    TO_REMOVE=()

    for pr in ${PRS}; do
        created="$(preview_label "${pr}" 'arax.preview.created')"
        branch="$(preview_label "${pr}" 'arax.preview.branch')"
        [ -n "${branch}" ] || branch="unknown"

        case "${created}" in
            ''|*[!0-9]*)
                # A preview without a usable timestamp is treated as too old to
                # keep, because nothing else can tell us when it was made.
                age_seconds="${TTL_SECONDS}"
                age_text="unknown"
                expired="yes"
                ;;
            *)
                age_seconds=$(( NOW - created ))
                age_text="$(human_age "${age_seconds}")"
                if [ "${age_seconds}" -gt "${TTL_SECONDS}" ]; then
                    expired="yes"
                else
                    expired="no"
                fi
                ;;
        esac

        state="skipped"
        if [ -n "${TOKEN}" ]; then
            state="$(pr_state "${pr}")"
        fi

        decision="keep"
        if [ "${expired}" = "yes" ]; then
            decision="remove, older than ${PREVIEW_TTL_DAYS} days"
        fi
        if [ "${state}" = "closed" ]; then
            decision="remove, pull request is closed"
        fi

        ROWS+=("| ${pr} | ${age_text} | ${branch} | ${state} | ${decision} |")
        case "${decision}" in
            remove*) TO_REMOVE+=("${pr}") ;;
        esac
    done

    printf '| pr | age | branch | pr state | decision |\n'
    printf '| --- | --- | --- | --- | --- |\n'
    for row in "${ROWS[@]}"; do
        printf '%s\n' "${row}"
    done
    printf '\n'

    if [ "${#TO_REMOVE[@]}" -eq 0 ]; then
        printf 'Nothing to remove.\n'
    else
        for pr in "${TO_REMOVE[@]}"; do
            if [ "${DRY_RUN}" = "yes" ]; then
                printf 'dry run: would tear down PR %s\n' "${pr}"
            else
                log "tearing down PR ${pr}"
                "${SCRIPT_DIR}/teardown.sh" "${pr}" || log "WARNING: teardown of PR ${pr} failed"
            fi
        done
    fi
    printf '\n'
fi

# ---------------------------------------------------------------------------
# Status page data with no container behind it
#
# A deploy that failed before it ever created a container still leaves
# ${PREVIEW_WEB_ROOT}/data/<PR>/ behind, and the status page draws a card from
# it. Teardown removes that directory, so the only ones that reach this sweep
# belong to a pull request that never had a container to tear down. They are
# kept for a day, long enough to read the failure on the page, and then go.
# ---------------------------------------------------------------------------

# Hours a data directory with no container is kept after the run that wrote it
# finished, or after it was last touched when there is no run state at all.
PREVIEW_ORPHAN_TTL_HOURS="${PREVIEW_ORPHAN_TTL_HOURS:-24}"
require_int "${PREVIEW_ORPHAN_TTL_HOURS}" "PREVIEW_ORPHAN_TTL_HOURS"
ORPHAN_TTL_SECONDS=$(( PREVIEW_ORPHAN_TTL_HOURS * 3600 ))

# Recomputed here rather than reusing PRS, because the teardowns above have
# just changed the answer, and their data directories are already gone.
CONTAINER_PRS="$(list_preview_prs | sort -n -u)"

ORPHAN_ROWS=()
ORPHAN_TO_REMOVE=()
ORPHAN_COUNT=0
ORPHAN_REMOVE_COUNT=0

# orphan_state <data dir>
# Prints "<deploy status>\t<newest timestamp>" for one data directory. The
# status is the state of the deploy stage, the word abandoned when the page
# generator closed the run out, or none when there is no state file at all.
# The timestamp is the newest moment the run recorded, and the modification
# time of the directory when it recorded nothing.
orphan_state() {
    python3 -c '
import json
import os
import sys

path = sys.argv[1]
status = "none"
newest = 0

try:
    with open(os.path.join(path, "state.json"), "r", errors="replace") as handle:
        doc = json.load(handle)
except Exception:
    doc = None

if isinstance(doc, dict):
    status = "unknown"
    stages = doc.get("stages")
    if not isinstance(stages, dict):
        stages = {}
    deploy = stages.get("deploy")
    if isinstance(deploy, dict):
        status = str(deploy.get("status") or "unknown")
        if str(deploy.get("detail") or "").strip() == "abandoned":
            status = "abandoned"
    for entry in list(stages.values()) + [{"finished_at": doc.get("updated_at")}]:
        if not isinstance(entry, dict):
            continue
        for key in ("finished_at", "started_at"):
            try:
                value = int(entry.get(key) or 0)
            except (TypeError, ValueError):
                value = 0
            if value > newest:
                newest = value

if not newest:
    try:
        newest = int(os.path.getmtime(path))
    except Exception:
        newest = 0

sys.stdout.write("%s\t%d\n" % (status, newest))
' "${1}"
}

if ${SUDO} test -d "${PREVIEW_WEB_ROOT}/data"; then
    for data_dir in "${PREVIEW_WEB_ROOT}/data"/*; do
        [ -d "${data_dir}" ] || continue
        pr="$(basename "${data_dir}")"
        case "${pr}" in
            ''|*[!0-9]*) continue ;;
        esac
        # A preview that still has a container is the container sweep's
        # business, and its data directory goes when the preview goes.
        if printf '%s\n' "${CONTAINER_PRS}" | grep -qx "${pr}"; then
            continue
        fi

        verdict="$(orphan_state "${data_dir}" || true)"
        run_status="$(printf '%s' "${verdict}" | awk -F'\t' '{print $1}')"
        newest="$(printf '%s' "${verdict}" | awk -F'\t' '{print $2}' | tr -dc '0-9')"
        [ -n "${run_status}" ] || run_status="unknown"
        if [ -n "${newest}" ] && [ "${newest}" -gt 0 ]; then
            age_seconds=$(( NOW - newest ))
            [ "${age_seconds}" -ge 0 ] || age_seconds=0
            age_text="$(human_age "${age_seconds}")"
        else
            # Nothing readable to date it by, so it is treated as old enough.
            age_seconds="${ORPHAN_TTL_SECONDS}"
            age_text="unknown"
        fi

        state="skipped"
        if [ -n "${TOKEN}" ]; then
            state="$(pr_state "${pr}")"
        fi

        decision="keep"
        case "${run_status}" in
            failed|abandoned)
                if [ "${age_seconds}" -gt "${ORPHAN_TTL_SECONDS}" ]; then
                    decision="remove, ${run_status} run older than ${PREVIEW_ORPHAN_TTL_HOURS}h"
                fi
                ;;
            none)
                if [ "${age_seconds}" -gt "${ORPHAN_TTL_SECONDS}" ]; then
                    decision="remove, no run state and untouched for ${PREVIEW_ORPHAN_TTL_HOURS}h"
                fi
                ;;
        esac
        if [ "${state}" = "closed" ]; then
            decision="remove, pull request is closed"
        fi

        ORPHAN_ROWS+=("| ${pr} | ${age_text} | ${run_status} | ${state} | ${decision} |")
        ORPHAN_COUNT=$(( ORPHAN_COUNT + 1 ))
        case "${decision}" in
            remove*)
                ORPHAN_TO_REMOVE+=("${data_dir}")
                ORPHAN_REMOVE_COUNT=$(( ORPHAN_REMOVE_COUNT + 1 ))
                ;;
        esac
    done
fi

if [ "${ORPHAN_COUNT}" -eq 0 ]; then
    printf 'No status page data without a container.\n\n'
else
    printf '| pr | age | last run | pr state | decision |\n'
    printf '| --- | --- | --- | --- | --- |\n'
    for row in "${ORPHAN_ROWS[@]}"; do
        printf '%s\n' "${row}"
    done
    printf '\n'

    if [ "${ORPHAN_REMOVE_COUNT}" -eq 0 ]; then
        printf 'No status page data to remove.\n'
    else
        for data_dir in "${ORPHAN_TO_REMOVE[@]}"; do
            if [ "${DRY_RUN}" = "yes" ]; then
                printf 'dry run: would remove %s\n' "${data_dir}"
            else
                log "removing ${data_dir}, which has no container behind it"
                if ${SUDO} rm -rf "${data_dir}"; then
                    printf 'removed %s\n' "${data_dir}"
                else
                    log "WARNING: could not remove ${data_dir}"
                fi
            fi
        done
    fi
    printf '\n'
fi

if [ "${DRY_RUN}" = "yes" ]; then
    printf 'dry run: would run docker image prune -f\n'
else
    # Dangling layers only. Tagged images belonging to live previews and to the
    # pytest workflow are never touched by this.
    log "pruning dangling images"
    ${DOCKER} image prune -f
fi

# Deploy logs outlive the previews they belong to on purpose, so a preview that
# is already gone can still be looked at. A month is long enough for that.
if ${SUDO} test -d "${PREVIEW_LOG_DIR}"; then
    if [ "${DRY_RUN}" = "yes" ]; then
        printf 'dry run: would delete files under %s older than 30 days\n' "${PREVIEW_LOG_DIR}"
    else
        log "deleting deploy logs under ${PREVIEW_LOG_DIR} older than 30 days"
        ${SUDO} find "${PREVIEW_LOG_DIR}" -type f -mtime +30 -delete \
            || log "WARNING: could not prune ${PREVIEW_LOG_DIR}"
    fi
else
    log "no ${PREVIEW_LOG_DIR} on this host, no deploy logs to prune"
fi

# Last, so the page reflects the sweep that just happened. Generating the page
# also closes out any run that was killed between "running" and its result:
# a stage still marked running after PREVIEW_STATE_STALE_SECONDS is written
# down as failed with the detail "abandoned", so no card spins forever.
if [ "${DRY_RUN}" = "yes" ]; then
    printf 'dry run: would rewrite the status page and close out abandoned runs\n'
else
    write_status_page
fi
