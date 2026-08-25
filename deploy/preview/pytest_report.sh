#!/usr/bin/env bash
#
# Run the ARAX test suite inside one preview container and print a short
# Markdown report on stdout, which the workflow posts as its own pull request
# comment. The raw pytest output goes to stderr, so the workflow log and the
# uploaded artifact keep all of it.
#
# Usage: pytest_report.sh <PR> [PYTEST_ARGS]
#
# Exits with the exit code of pytest itself.
#
# Issue #2846.

set -o nounset -o pipefail -o errexit

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
. "${SCRIPT_DIR}/lib.sh"
preview_validate_env

usage() {
    cat >&2 <<'USAGE_EOF'
Usage: pytest_report.sh <PR> [PYTEST_ARGS]

  PR           pull request number, for example 2853
  PYTEST_ARGS  extra arguments for pytest as one string, for example
               "-k test_ARAX_query". May be empty or left out, which runs the
               whole suite.
USAGE_EOF
    exit 2
}

[ "$#" -ge 1 ] || usage
case "${1}" in
    -h|--help) usage ;;
esac

PR="$1"
require_int "${PR}" "PR number"
PYTEST_ARGS="${2:-}"

CONTAINER="$(preview_container "${PR}")"
TEST_DIR="/mnt/data/orangeboard/production/RTX/code/ARAX/test"

# The report opens with the container it ran in, so the pull request comment
# and the status page both say which preview was tested. The workflow slices
# the comment body from this line, so it has to be the top of the report.
# the backticks are markdown around the container name, not a substitution
# shellcheck disable=SC2016
ENV_BLOCK="$(printf '**Container:** `%s`' "${CONTAINER}")"

if ! container_running "${CONTAINER}"; then
    # the backticks are markdown around the container name, not a substitution
    # shellcheck disable=SC2016
    printf '%s\n\n**pytest:** not run, the container `%s` is not running\n' \
        "${ENV_BLOCK}" "${CONTAINER}"
    exit 1
fi

PYTEST_LOG="$(mktemp)"
trap 'rm -f "${PYTEST_LOG}"' EXIT

log "running pytest inside ${CONTAINER} with args '${PYTEST_ARGS}'"

# No -v. The suite is long and the summary line is what the report is built
# from, so per test lines only make the artifact bigger.
set +o errexit
${DOCKER} exec "${CONTAINER}" bash -c "cd ${TEST_DIR} && pytest --disable-pytest-warnings ${PYTEST_ARGS}" \
    > "${PYTEST_LOG}" 2>&1
PYTEST_RC=$?
set -o errexit

# Everything pytest said, for the job log and the artifact.
cat "${PYTEST_LOG}" >&2

REPORT="$(PYTEST_RC="${PYTEST_RC}" python3 - "${PYTEST_LOG}" <<'PYTHON_EOF'
import os
import re
import sys

path = sys.argv[1]
try:
    rc = int(os.environ.get("PYTEST_RC", "1"))
except ValueError:
    rc = 1

with open(path, "r", errors="replace") as handle:
    lines = handle.read().splitlines()

# The summary line pytest ends with looks like
#   ===== 3 failed, 128 passed, 5 skipped, 2 warnings in 154.32s (0:02:34) =====
# Read it from the bottom, because a test that prints something similar must
# not win over the real one.
COUNT_RE = re.compile(r"(\d+) (passed|failed|skipped|errors?|xfailed|xpassed)\b")
DURATION_RE = re.compile(r"\bin ([0-9.]+s(?: \([^)]*\))?)")

counts = {}
duration = ""
for line in reversed(lines):
    stripped = line.strip().strip("=").strip()
    found = COUNT_RE.findall(stripped)
    when = DURATION_RE.search(stripped)
    if found and when:
        for number, word in found:
            key = "error" if word.startswith("error") else word
            counts[key] = counts.get(key, 0) + int(number)
        duration = when.group(1)
        break

report = []
if counts and duration:
    parts = [
        "%d passed" % counts.get("passed", 0),
        "%d failed" % counts.get("failed", 0),
        "%d skipped" % counts.get("skipped", 0),
    ]
    if counts.get("error", 0):
        parts.append("%d errors" % counts["error"])
    report.append("**pytest:** " + ", ".join(parts) + " in " + duration)
else:
    # A crashed collection, a killed container or an unknown pytest version.
    report.append("**pytest:** exit %d" % rc)

if rc != 0:
    failed = [line.rstrip() for line in lines
              if line.startswith("FAILED ") or line.startswith("ERROR ")]
    body = failed + ["", "--- last 80 lines of output ---", ""] + [line.rstrip() for line in lines[-80:]]
    # chr(96) keeps a literal backtick out of this file. bash cannot parse a
    # backtick inside a heredoc that sits inside a command substitution.
    fence = chr(96) * 3
    report.append("")
    report.append("<details><summary>failed tests and last 80 lines</summary>")
    report.append("")
    report.append(fence)
    # A fence inside the output would end the block early.
    report.extend([line.replace(fence, "'''") for line in body])
    report.append(fence)
    report.append("")
    report.append("</details>")

sys.stdout.write("\n".join(report) + "\n")
PYTHON_EOF
)"

render_report() {
    printf '%s\n\n' "${ENV_BLOCK}"
    printf '%s\n' "${REPORT}"
}

render_report
render_report | write_preview_data "${PR}" "pytest.md"
# The page must show the result the moment it exists, not on the next cron tick.
write_status_page

if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
    render_report >> "${GITHUB_STEP_SUMMARY}"
fi

exit "${PYTEST_RC}"
