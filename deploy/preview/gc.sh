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

if [ -z "${PRS}" ]; then
    printf 'No ARAX previews found on this host.\n'
    exit 0
fi

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

if [ "${DRY_RUN}" = "yes" ]; then
    printf 'dry run: would run docker image prune -f\n'
else
    # Dangling layers only. Tagged images belonging to live previews and to the
    # pytest workflow are never touched by this.
    log "pruning dangling images"
    ${DOCKER} image prune -f
fi
