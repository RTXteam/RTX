#!/usr/bin/env bash
#
# Smoke test one ARAX preview container. Everything is checked against the
# loopback port on the host, not through nginx, so a failure here always means
# the container itself is unhealthy.
#
# Usage: smoke.sh <PR> [--pytest "<pytest args>"]
#
# Prints a Markdown table on stdout, which the workflow pastes into the PR
# comment. Exits non-zero when any check failed.
#
# Issue #2846.

set -o nounset -o pipefail -o errexit

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
. "${SCRIPT_DIR}/lib.sh"

usage() {
    cat >&2 <<'USAGE_EOF'
Usage: smoke.sh <PR> [--pytest "<pytest args>"]

  PR        pull request number, for example 2853
  --pytest  also run the ARAX test suite inside the container. The argument
            may be an empty string, which runs the whole suite.
USAGE_EOF
    exit 2
}

[ "$#" -ge 1 ] || usage

PR="$1"
shift
require_int "${PR}" "PR number"

RUN_PYTEST="no"
PYTEST_ARGS=""
while [ "$#" -gt 0 ]; do
    case "$1" in
        --pytest)
            RUN_PYTEST="yes"
            PYTEST_ARGS="${2:-}"
            shift 2 || shift
            ;;
        *)
            die "unknown argument '$1'"
            ;;
    esac
done

PORT="$(preview_port "${PR}")"
CONTAINER="$(preview_container "${PR}")"
BASE="http://127.0.0.1:${PORT}"

ROWS=()
FAILURES=0
PYTEST_TAIL=""

record() {
    local name="$1"
    local ok="$2"
    local detail="$3"
    if [ "${ok}" = "yes" ]; then
        ROWS+=("| ${name} | pass | ${detail} |")
    else
        ROWS+=("| ${name} | FAIL | ${detail} |")
        FAILURES=$(( FAILURES + 1 ))
    fi
}

# Prints the HTTP status code, or 000 when the request never completed.
http_code() {
    local url="$1"
    local timeout="$2"
    curl -s -o /dev/null -w '%{http_code}' -m "${timeout}" "${url}" 2>/dev/null || printf '000'
}

log "smoke testing PR ${PR} at ${BASE}"

# The container must exist at all before any HTTP check is meaningful.
if ! ${DOCKER} inspect "${CONTAINER}" >/dev/null 2>&1; then
    record "container ${CONTAINER} exists" "no" "not found"
else
    RUNNING="$(${DOCKER} inspect --format '{{.State.Running}}' "${CONTAINER}" 2>/dev/null || printf 'false')"
    if [ "${RUNNING}" = "true" ]; then
        record "container ${CONTAINER} running" "yes" "up"
    else
        record "container ${CONTAINER} running" "no" "state ${RUNNING}"
    fi
fi

# 1. the ARAX status endpoint
CODE="$(http_code "${BASE}/api/arax/v1.4/status" 30)"
if [ "${CODE}" = "200" ]; then
    record "GET /api/arax/v1.4/status" "yes" "HTTP ${CODE}"
else
    record "GET /api/arax/v1.4/status" "no" "HTTP ${CODE}"
fi

# 2. the UI index page, which apache serves from the checked out repository
BODY_FILE="$(mktemp)"
CODE="$(curl -s -o "${BODY_FILE}" -w '%{http_code}' -m 30 "${BASE}/" 2>/dev/null || printf '000')"
if [ "${CODE}" = "200" ] && grep -q 'ARAX' "${BODY_FILE}"; then
    record "GET / serves the ARAX UI" "yes" "HTTP ${CODE}, body contains ARAX"
elif [ "${CODE}" = "200" ]; then
    record "GET / serves the ARAX UI" "no" "HTTP ${CODE}, body does not contain ARAX"
else
    record "GET / serves the ARAX UI" "no" "HTTP ${CODE}"
fi
rm -f "${BODY_FILE}"

# 3. the swagger UI. Connexion answers with a redirect on some versions, so
# any 2xx or 3xx counts as a pass.
CODE="$(http_code "${BASE}/api/arax/v1.4/ui/" 30)"
case "${CODE}" in
    200|30[0-9])
        record "GET /api/arax/v1.4/ui/" "yes" "HTTP ${CODE}"
        ;;
    *)
        record "GET /api/arax/v1.4/ui/" "no" "HTTP ${CODE}"
        ;;
esac

# 4. the meta knowledge graph, which is the first endpoint that touches the
# knowledge provider caches and is therefore slow on a cold container.
CODE="$(http_code "${BASE}/api/arax/v1.4/meta_knowledge_graph" 180)"
if [ "${CODE}" = "200" ]; then
    record "GET /api/arax/v1.4/meta_knowledge_graph" "yes" "HTTP ${CODE}"
else
    record "GET /api/arax/v1.4/meta_knowledge_graph" "no" "HTTP ${CODE}"
fi

# 5. optional full test suite inside the container
if [ "${RUN_PYTEST}" = "yes" ]; then
    log "running pytest inside ${CONTAINER} with args '${PYTEST_ARGS}'"
    PYTEST_LOG="$(mktemp)"
    set +o errexit
    ${DOCKER} exec "${CONTAINER}" bash -c "cd /mnt/data/orangeboard/production/RTX/code/ARAX/test && pytest -v --disable-pytest-warnings ${PYTEST_ARGS}" \
        > "${PYTEST_LOG}" 2>&1
    PYTEST_RC=$?
    set -o errexit
    cat "${PYTEST_LOG}" >&2
    PYTEST_TAIL="$(tail -n 60 "${PYTEST_LOG}")"
    rm -f "${PYTEST_LOG}"
    if [ "${PYTEST_RC}" -eq 0 ]; then
        record "pytest ${PYTEST_ARGS}" "yes" "exit 0"
    else
        record "pytest ${PYTEST_ARGS}" "no" "exit ${PYTEST_RC}"
    fi
fi

# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

render_report() {
    printf '| check | result | detail |\n'
    printf '| --- | --- | --- |\n'
    local row
    for row in "${ROWS[@]}"; do
        printf '%s\n' "${row}"
    done
    if [ -n "${PYTEST_TAIL}" ]; then
        printf '\n<details><summary>pytest output, last 60 lines</summary>\n\n'
        # the backticks are a literal markdown fence, not a substitution
        # shellcheck disable=SC2016
        printf '```\n%s\n```\n\n' "${PYTEST_TAIL}"
        printf '</details>\n'
    fi
}

render_report

if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
    render_report >> "${GITHUB_STEP_SUMMARY}"
fi

if [ "${FAILURES}" -gt 0 ]; then
    log "${FAILURES} smoke check(s) failed for PR ${PR}"
    exit 1
fi
log "all smoke checks passed for PR ${PR}"
