#!/usr/bin/env bash
#
# Run the four example queries the ARAX UI ships with against one preview and
# print a Markdown table on stdout, which the workflow posts as its own pull
# request comment.
#
# The payloads are read out of code/UI/interactive/rtx.js, so this always
# tests exactly what the Try an example buttons in the UI put in the box. The
# requests go through the public URL, which means nginx on the host and apache
# in the container are on the path and get tested too.
#
# Usage: query_smoke.sh <PR>
#
# The report is informational and the script exits 0 even when queries fail.
# Only a usage error exits non-zero.
#
# Issue #2846.

set -o nounset -o pipefail -o errexit

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
. "${SCRIPT_DIR}/lib.sh"
preview_validate_env

usage() {
    cat >&2 <<'USAGE_EOF'
Usage: query_smoke.sh <PR>

  PR  pull request number, for example 2853

Environment:
  PREVIEW_UI_RTXJS    rtx.js the example payloads are read from. Defaults to
                      the copy in this checkout. The workflow points it at the
                      pull request head, so a pull request that changes the
                      examples is tested with its own.
  PREVIEW_QUERY_BASE  base URL the queries are sent to. Defaults to the public
                      preview URL for this pull request.
USAGE_EOF
    exit 2
}

[ "$#" -ge 1 ] || usage
case "${1}" in
    -h|--help) usage ;;
esac

PR="$1"
require_int "${PR}" "PR number"

PREVIEW_UI_RTXJS="${PREVIEW_UI_RTXJS:-${REPO_ROOT}/code/UI/interactive/rtx.js}"
PREVIEW_QUERY_BASE="${PREVIEW_QUERY_BASE:-$(preview_url "${PR}")}"
# Trailing slash off, because the path below brings its own.
QUERY_URL="${PREVIEW_QUERY_BASE%/}/api/arax/v1.4/query"

export PREVIEW_UI_RTXJS PREVIEW_QUERY_BASE

WORK_DIR="$(mktemp -d)"
trap 'rm -rf "${WORK_DIR}"' EXIT

# kind, short name for the first column, label for the table, timeout in
# seconds. The short names are the ones on the Try an example buttons in the
# UI, so a row can be matched to a button without reading the query graph.
# The pathfinder query was measured at 90 seconds on this host, the other
# three at 3 to 5 seconds.
QUERIES=(
    "JSON1|Example 1|interacts_with (CHEBI:46195)|240"
    "JSON2|Example 2|treats inferred (MONDO:0015564)|240"
    "JSON3|Example 3|affects qualified (NCBIGene:1576)|240"
    "PATH1|Pathfinder|pathfinder (MONDO:0005011 to MONDO:0005180)|400"
)

log "reading the example query graphs from ${PREVIEW_UI_RTXJS}"

# The extractor writes one ready to post request body per example into the
# work directory and prints "<kind> ok <node count>" or "<kind> fail <reason>"
# for each. A payload it cannot read is reported and skipped, never fatal.
EXTRACTION="$(QUERY_WORK_DIR="${WORK_DIR}" python3 - <<'PYTHON_EOF'
import json
import os
import re
import sys

path = os.environ.get("PREVIEW_UI_RTXJS", "")
work = os.environ.get("QUERY_WORK_DIR", "")
kinds = ["JSON1", "JSON2", "JSON3", "PATH1"]

ESCAPES = {
    "n": "\n",
    "t": "\t",
    "r": "\r",
    "b": "\b",
    "f": "\f",
    "0": "\0",
    "'": "'",
    "\"": "\"",
    "\\": "\\",
    "/": "/",
}
ASSIGNMENT = re.compile(r"\.value\s*=\s*'")


def report(kind, state, detail):
    sys.stdout.write(kind + "\t" + state + "\t" + detail + "\n")


try:
    with open(path, "r", errors="replace") as handle:
        source = handle.read()
except Exception as error:
    for kind in kinds:
        report(kind, "fail", "cannot read the UI source: %s" % error)
    sys.exit(0)


def js_string_after(marker_index):
    """The single quoted JavaScript string assigned to .value after an index."""
    found = ASSIGNMENT.search(source, marker_index)
    if found is None:
        return None, "no .value assignment follows the case"
    index = found.end()
    out = []
    while index < len(source):
        char = source[index]
        if char == "\\":
            nxt = source[index + 1:index + 2]
            out.append(ESCAPES.get(nxt, nxt))
            index += 2
            continue
        if char == "'":
            return "".join(out), ""
        if char == "\n":
            return None, "the string is not terminated on one line"
        out.append(char)
        index += 1
    return None, "the string is not terminated"


for kind in kinds:
    marker = 'type == "' + kind + '"'
    at = source.find(marker)
    if at < 0:
        report(kind, "fail", "no branch for " + kind + " in pasteExample")
        continue
    text, problem = js_string_after(at)
    if text is None:
        report(kind, "fail", problem)
        continue
    try:
        graph = json.loads(text)
    except Exception as error:
        report(kind, "fail", "the payload is not valid JSON: %s" % error)
        continue
    if not isinstance(graph, dict):
        report(kind, "fail", "the payload is not a query graph object")
        continue
    # The envelope the UI builds around the box contents before it posts.
    body = {"message": {"query_graph": graph}}
    try:
        with open(os.path.join(work, kind + ".body.json"), "w") as handle:
            json.dump(body, handle)
    except Exception as error:
        report(kind, "fail", "could not write the request body: %s" % error)
        continue
    report(kind, "ok", str(len(graph.get("nodes") or {})))
PYTHON_EOF
)"

printf '%s\n' "${EXTRACTION}" >&2

ROWS=()
DEGRADED=0

# Everything the queries are asked about, in one place, so the row builder
# below stays readable.
for entry in "${QUERIES[@]}"; do
    KIND="${entry%%|*}"
    REST="${entry#*|}"
    SHORT="${REST%%|*}"
    REST="${REST#*|}"
    LABEL="${REST%%|*}"
    TIMEOUT="${REST##*|}"

    STATE="$(printf '%s\n' "${EXTRACTION}" | awk -F'\t' -v k="${KIND}" '$1 == k {print $2; exit}')"
    DETAIL="$(printf '%s\n' "${EXTRACTION}" | awk -F'\t' -v k="${KIND}" '$1 == k {print $3; exit}')"

    if [ "${STATE}" != "ok" ]; then
        log "${KIND}: payload extraction failed, ${DETAIL}"
        ROWS+=("| ⚠ ${SHORT} | ${LABEL} | - | - | - | - | payload extraction failed |")
        DEGRADED=$(( DEGRADED + 1 ))
        continue
    fi

    log "${KIND}: posting to ${QUERY_URL} with a ${TIMEOUT}s timeout"
    BODY_FILE="${WORK_DIR}/${KIND}.body.json"
    RESPONSE_FILE="${WORK_DIR}/${KIND}.response.json"
    # curl writes "<http code> <seconds>", for example "200 2.923400". Its own
    # timing is what goes in the table, because whole seconds off the clock
    # cannot tell a 3 second query from a 3.9 second one. LC_ALL=C keeps the
    # decimal separator a dot on a host with a comma locale.
    CURL_OUT="$(LC_ALL=C curl -sS -m "${TIMEOUT}" \
        -o "${RESPONSE_FILE}" \
        -w '%{http_code} %{time_total}' \
        -H 'Content-Type: application/json' \
        --data-binary "@${BODY_FILE}" \
        "${QUERY_URL}" 2>>"${WORK_DIR}/curl.err" || true)"
    CODE="${CURL_OUT%% *}"
    RAW_SECONDS="${CURL_OUT##* }"
    case "${CODE}" in
        [1-5][0-9][0-9]) : ;;
        *) CODE="000" ;;
    esac
    # A curl that died before it wrote anything leaves both fields empty, so
    # anything that is not a plain number becomes a dash rather than a crash.
    SECONDS_TEXT="$(printf '%s\n' "${RAW_SECONDS}" \
        | LC_ALL=C awk '{ if ($1 ~ /^[0-9]+(\.[0-9]+)?$/) printf "%.2f", $1; else printf "-" }')"

    PARSED="$(python3 - "${RESPONSE_FILE}" <<'PYTHON_EOF'
import json
import sys

try:
    with open(sys.argv[1], "r", errors="replace") as handle:
        data = json.load(handle)
except Exception:
    sys.stdout.write("-\t-\t-\tno parsable response body\n")
    sys.exit(0)

if not isinstance(data, dict):
    sys.stdout.write("-\t-\t-\tthe response is not a TRAPI object\n")
    sys.exit(0)

message = data.get("message") or {}
if not isinstance(message, dict):
    message = {}
graph = message.get("knowledge_graph") or {}
if not isinstance(graph, dict):
    graph = {}
results = message.get("results") or []
nodes = graph.get("nodes") or {}
edges = graph.get("edges") or {}
status = data.get("status")
if not isinstance(status, str):
    status = ""
# The table has to survive whatever the server put in there.
status = status.replace("|", "/").replace("\n", " ").replace("\r", " ").strip()
sys.stdout.write(
    "%d\t%d\t%d\t%s\n" % (len(results), len(nodes), len(edges), status[:60] or "-")
)
PYTHON_EOF
)"

    RESULTS="$(printf '%s\n' "${PARSED}" | awk -F'\t' 'NR == 1 {print $1}')"
    NODES="$(printf '%s\n' "${PARSED}" | awk -F'\t' 'NR == 1 {print $2}')"
    EDGES="$(printf '%s\n' "${PARSED}" | awk -F'\t' 'NR == 1 {print $3}')"
    STATUS="$(printf '%s\n' "${PARSED}" | awk -F'\t' 'NR == 1 {print $4}')"

    MARK=""
    # No results is a failure of the preview even when the HTTP call worked,
    # which is the whole reason this report exists next to the smoke test.
    if [ "${CODE}" != "200" ] || [ "${RESULTS}" = "0" ] || [ "${RESULTS}" = "-" ]; then
        MARK="⚠ "
        DEGRADED=$(( DEGRADED + 1 ))
    fi
    log "${KIND}: HTTP ${CODE} in ${SECONDS_TEXT}s, ${RESULTS} result(s), status ${STATUS}"
    ROWS+=("| ${MARK}${SHORT} | ${LABEL} | ${CODE} | ${SECONDS_TEXT} | ${RESULTS} | ${NODES}/${EDGES} | ${STATUS} |")
done

render_report() {
    # The endpoint comes first because the workflow slices the pull request
    # comment from this line, so it has to be the top of the report.
    # the backticks are markdown around the URL, not a substitution
    # shellcheck disable=SC2016
    printf '**Endpoint:** `%s`\n\n' "${QUERY_URL}"
    printf '| # | query | HTTP | s | results | KG nodes/edges | status |\n'
    printf '| --- | --- | --- | --- | --- | --- | --- |\n'
    local row
    for row in "${ROWS[@]}"; do
        printf '%s\n' "${row}"
    done
}

# The count goes out before the report, not after it. The workflow slices the
# pull request comment from the endpoint line to the end of the log, so a log
# line printed after the table would land under the table in the comment.
if [ "${DEGRADED}" -gt 0 ]; then
    log "${DEGRADED} of ${#QUERIES[@]} example queries came back degraded for PR ${PR}"
else
    log "all ${#QUERIES[@]} example queries answered for PR ${PR}"
fi

render_report
render_report | write_preview_data "${PR}" "queries.md"

if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
    render_report >> "${GITHUB_STEP_SUMMARY}"
fi

# Informational by design: a slow or empty answer is worth reading, not worth
# turning the deploy red.
exit 0
