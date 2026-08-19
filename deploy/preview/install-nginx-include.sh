#!/usr/bin/env bash
#
# One time host setup for the ARAX preview environments on cicd.rtx.ai.
# A human runs this once, as root or with sudo. Everything the deploy workflow
# does afterwards stays inside PREVIEW_NGINX_DIR and never edits the certbot
# managed site file again.
#
# Usage: sudo bash deploy/preview/install-nginx-include.sh
#
# Issue #2846.

set -o nounset -o pipefail -o errexit

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
. "${SCRIPT_DIR}/lib.sh"

# The certbot managed site file on cicd.rtx.ai, set up by
# tests/setup-ci-report-append-logfile-webroot.sh.
PREVIEW_NGINX_SITE="${PREVIEW_NGINX_SITE:-/etc/nginx/sites-enabled/default}"
INCLUDE_LINE="    include ${PREVIEW_NGINX_DIR}/*.conf;"
INCLUDE_MARKER="include ${PREVIEW_NGINX_DIR}/*.conf;"

log "installing the ARAX preview include into ${PREVIEW_NGINX_SITE}"

[ -f "${PREVIEW_NGINX_SITE}" ] || die "${PREVIEW_NGINX_SITE} does not exist. Set PREVIEW_NGINX_SITE to the certbot managed site file for cicd.rtx.ai."

# ---------------------------------------------------------------------------
# The snippet directory
# ---------------------------------------------------------------------------

${SUDO} mkdir -p "${PREVIEW_NGINX_DIR}"
${SUDO} chmod 755 "${PREVIEW_NGINX_DIR}"
log "${PREVIEW_NGINX_DIR} is ready"

# ---------------------------------------------------------------------------
# The include line
# ---------------------------------------------------------------------------

if ${SUDO} grep -qF "${INCLUDE_MARKER}" "${PREVIEW_NGINX_SITE}"; then
    printf 'already installed: %s already contains "%s"\n' "${PREVIEW_NGINX_SITE}" "${INCLUDE_MARKER}"
    exit 0
fi

TIMESTAMP="$(date -u '+%Y%m%d%H%M%S')"
BACKUP="${PREVIEW_NGINX_SITE}.bak.${TIMESTAMP}"
${SUDO} cp -p "${PREVIEW_NGINX_SITE}" "${BACKUP}"
log "backed up ${PREVIEW_NGINX_SITE} to ${BACKUP}"

# Brace counting beats a sed regex here, because we have to be sure we land in
# the TLS server block and not in the plain port 80 redirect block.
INSERTER="$(mktemp)"
cat > "${INSERTER}" <<'PYTHON_EOF'
import sys

path = sys.argv[1]
include_line = sys.argv[2]
server_name_needle = sys.argv[3]

with open(path, "r") as handle:
    lines = handle.readlines()

# Walk the file and record every top level "server { ... }" block as a
# (start_index, end_index_exclusive) pair.
blocks = []
depth = 0
start = None
for index, line in enumerate(lines):
    stripped = line.strip()
    if depth == 0 and stripped.startswith("server") and "{" in stripped:
        start = index
    depth += line.count("{") - line.count("}")
    if start is not None and depth <= 0:
        blocks.append((start, index + 1))
        start = None
        depth = 0

for begin, end in blocks:
    body = lines[begin:end]
    has_tls = any("listen" in item and "443" in item for item in body)
    if not has_tls:
        continue
    for offset, item in enumerate(body):
        if item.strip() == server_name_needle:
            insert_at = begin + offset + 1
            lines.insert(insert_at, include_line + "\n")
            with open(path, "w") as handle:
                handle.writelines(lines)
            sys.stdout.write(str(insert_at + 1))
            sys.exit(0)

sys.exit(3)
PYTHON_EOF

set +o errexit
INSERTED_AT="$(${SUDO} python3 "${INSERTER}" "${PREVIEW_NGINX_SITE}" "${INCLUDE_LINE}" 'server_name cicd.rtx.ai;')"
INSERT_RC=$?
set -o errexit
rm -f "${INSERTER}"

if [ "${INSERT_RC}" -ne 0 ]; then
    ${SUDO} rm -f "${BACKUP}"
    cat >&2 <<MANUAL_EOF

Could not find a server block in ${PREVIEW_NGINX_SITE} that has both a
"listen ... 443" line and a "server_name cicd.rtx.ai;" line. Nothing was
changed.

Add the include by hand instead. Open ${PREVIEW_NGINX_SITE}, find the TLS
server block that certbot manages for cicd.rtx.ai, and add this single line
just after its server_name line, inside the braces of that server block:

${INCLUDE_LINE}

Then run:

    sudo nginx -t && sudo systemctl reload nginx

MANUAL_EOF
    exit 1
fi

log "inserted the include at line ${INSERTED_AT} of ${PREVIEW_NGINX_SITE}"

# ---------------------------------------------------------------------------
# Validate, and undo the edit if nginx does not like it
# ---------------------------------------------------------------------------

if ! ${SUDO} nginx -t; then
    ${SUDO} cp -p "${BACKUP}" "${PREVIEW_NGINX_SITE}"
    log "nginx -t failed, restored ${PREVIEW_NGINX_SITE} from ${BACKUP}"
    die "nginx rejected the edited configuration, nothing was changed"
fi

${SUDO} systemctl reload nginx
log "nginx reloaded"

cat <<NOTE_EOF

Installed.

  site file      ${PREVIEW_NGINX_SITE}
  backup         ${BACKUP}
  snippet dir    ${PREVIEW_NGINX_DIR}
  include line   ${INCLUDE_LINE}

The GitHub Actions runner user also needs passwordless sudo for docker, nginx,
systemctl reload nginx, tee, rm and mkdir. That is already the case on
cicd.rtx.ai, because .github/workflows/pytest.yml calls "sudo docker" with no
terminal attached. Check it as the runner user with:

    sudo -n true && echo "passwordless sudo works"

Deploy a preview with:

    bash deploy/preview/deploy.sh <PR> <BRANCH>

NOTE_EOF
