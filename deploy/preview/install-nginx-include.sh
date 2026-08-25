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
# The status page: its document root, the deploy log directory and the nginx
# snippet that serves both it and the redirect from the bare root.
# ---------------------------------------------------------------------------

STATUS_CONF_CREATED="no"

# install_status_cron
# The status page is rewritten on every deploy, teardown and garbage
# collection run, and cron keeps it honest in between. Idempotent: a crontab
# that already mentions the refresh script is left exactly as it is, so
# running this installer again never doubles the entry up.
install_status_cron() {
    local script entry owner current tmp
    script="${SCRIPT_DIR}/status-refresh.sh"
    entry="*/5 * * * * /bin/bash ${script} >/dev/null 2>&1"
    # This installer is run with sudo, so the crontab that matters belongs to
    # the human who invoked it rather than to root.
    owner="${SUDO_USER:-root}"

    if [ ! -f "${script}" ]; then
        log "WARNING: ${script} is missing, not installing the cron entry"
        return 0
    fi
    if ! command -v crontab >/dev/null 2>&1; then
        printf 'no crontab command on this host, add this line by hand: %s\n' "${entry}"
        return 0
    fi

    current="$(${SUDO} crontab -u "${owner}" -l 2>/dev/null || true)"
    if printf '%s\n' "${current}" | grep -qF "status-refresh.sh"; then
        printf 'already installed: the crontab of %s already refreshes the status page\n' "${owner}"
        return 0
    fi

    # Written through a file rather than a pipe so an existing crontab keeps
    # its own comments and blank lines exactly as the owner wrote them.
    tmp="$(mktemp)"
    if [ -n "${current}" ]; then
        printf '%s\n' "${current}" > "${tmp}"
    fi
    printf '%s\n' "${entry}" >> "${tmp}"
    if ${SUDO} crontab -u "${owner}" "${tmp}"; then
        printf 'installed in the crontab of %s: %s\n' "${owner}" "${entry}"
    else
        printf 'could not write the crontab of %s, add this line by hand: %s\n' "${owner}" "${entry}"
    fi
    rm -f "${tmp}"
}

# The sampler that keeps the host numbers on the page live. systemd owns it,
# because it has to survive a logout, come back after a reboot and be
# restarted when it dies, none of which cron can do for a loop.
PREVIEW_STATS_SERVICE="${PREVIEW_STATS_SERVICE:-/etc/systemd/system/arax-preview-stats.service}"
PREVIEW_STATS_SERVICE_NAME="$(basename "${PREVIEW_STATS_SERVICE}")"

install_stats_service() {
    local script owner unit current changed active
    script="${SCRIPT_DIR}/host-stats.sh"
    # This installer is run with sudo, so the unit runs as the human who
    # invoked it rather than as root. The loop shells out to "sudo docker"
    # like every other script here, which that user can already do without a
    # password, because the pytest workflow depends on it.
    owner="${SUDO_USER:-root}"

    if [ ! -f "${script}" ]; then
        log "WARNING: ${script} is missing, not installing the sampler service"
        return 0
    fi

    # One sample right now, so host.json exists before the first browser asks
    # for it and before systemd has had a chance to tick.
    if ! /bin/bash "${script}" --once; then
        log "WARNING: ${script} --once failed, the host tiles will say no data until it works"
    fi

    if ! command -v systemctl >/dev/null 2>&1; then
        printf 'no systemctl on this host. Run the sampler some other way: /bin/bash %s\n' "${script}"
        return 0
    fi

    unit="$(cat <<UNIT_EOF
[Unit]
Description=ARAX preview host sampler for the /previews/ status page
After=docker.service

[Service]
Type=simple
User=${owner}
ExecStart=/bin/bash ${script}
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT_EOF
)"

    # Idempotent: the unit is only rewritten when its content actually
    # changed, so running this installer again does not restart a sampler
    # that is doing its job.
    current="$(${SUDO} cat "${PREVIEW_STATS_SERVICE}" 2>/dev/null || true)"
    changed="no"
    if [ "${current}" = "${unit}" ]; then
        log "${PREVIEW_STATS_SERVICE} is already up to date"
    else
        printf '%s\n' "${unit}" | ${SUDO} tee "${PREVIEW_STATS_SERVICE}" >/dev/null
        ${SUDO} chmod 644 "${PREVIEW_STATS_SERVICE}" 2>/dev/null || true
        changed="yes"
        log "wrote ${PREVIEW_STATS_SERVICE}"
        ${SUDO} systemctl daemon-reload || log "WARNING: systemctl daemon-reload failed"
    fi

    if ! ${SUDO} systemctl enable --now "${PREVIEW_STATS_SERVICE_NAME}"; then
        printf 'could not enable %s, start it by hand with: sudo systemctl enable --now %s\n' \
            "${PREVIEW_STATS_SERVICE_NAME}" "${PREVIEW_STATS_SERVICE_NAME}"
        return 0
    fi
    if [ "${changed}" = "yes" ]; then
        ${SUDO} systemctl restart "${PREVIEW_STATS_SERVICE_NAME}" \
            || log "WARNING: could not restart ${PREVIEW_STATS_SERVICE_NAME}"
    fi

    active="$(${SUDO} systemctl is-active "${PREVIEW_STATS_SERVICE_NAME}" 2>/dev/null || printf 'unknown')"
    printf '%s is %s, sampling the host into %s every 15 seconds\n' \
        "${PREVIEW_STATS_SERVICE_NAME}" "${active}" "${PREVIEW_WEB_ROOT}/host.json"
}

ensure_status_assets() {
    ${SUDO} mkdir -p "${PREVIEW_WEB_ROOT}/data"
    ${SUDO} chmod 755 "${PREVIEW_WEB_ROOT}" "${PREVIEW_WEB_ROOT}/data"
    ${SUDO} mkdir -p "${PREVIEW_LOG_DIR}"
    ${SUDO} chmod 755 "${PREVIEW_LOG_DIR}"
    log "${PREVIEW_WEB_ROOT} and ${PREVIEW_LOG_DIR} are ready"

    if ${SUDO} test -f "${PREVIEW_STATUS_CONF}"; then
        log "${PREVIEW_STATUS_CONF} is already there, leaving it alone"
    else
        # The exact match on / only catches the bare root, so /cicd.txt and
        # /.well-known/ keep being served by the site file as before. The
        # trailing slash on the alias is required by nginx.
        ${SUDO} tee "${PREVIEW_STATUS_CONF}" >/dev/null <<STATUS_EOF
# managed by deploy/preview/install-nginx-include.sh
location = / { return 302 /previews/; }
location /previews/ {
    alias ${PREVIEW_WEB_ROOT}/;
    index index.html;
    default_type text/html;
}
STATUS_EOF
        STATUS_CONF_CREATED="yes"
        log "wrote ${PREVIEW_STATUS_CONF}"
    fi

    # So that /previews/ answers with the empty state right away, before any
    # preview has ever been deployed on this host.
    write_status_page

    install_status_cron
    install_stats_service
}

ensure_status_assets

# ---------------------------------------------------------------------------
# The include line
# ---------------------------------------------------------------------------

if ${SUDO} grep -qF "${INCLUDE_MARKER}" "${PREVIEW_NGINX_SITE}"; then
    printf 'already installed: %s already contains "%s"\n' "${PREVIEW_NGINX_SITE}" "${INCLUDE_MARKER}"
    # Nothing else changed, so nginx only has to hear about a snippet that was
    # written just now.
    if [ "${STATUS_CONF_CREATED}" = "yes" ]; then
        if ! nginx_reload; then
            ${SUDO} rm -f "${PREVIEW_STATUS_CONF}"
            die "nginx rejected ${PREVIEW_STATUS_CONF}, removed it again and did not reload"
        fi
        printf 'added the status page at %s/previews/\n' "${PREVIEW_PUBLIC_BASE_URL%/}"
    fi
    exit 0
fi

TIMESTAMP="$(date -u '+%Y%m%d%H%M%S')"

BACKUP_DIR="${PREVIEW_NGINX_DIR_BACKUP_DIR:-/var/backups/arax-preview}"
${SUDO} mkdir -p "${BACKUP_DIR}"
BACKUP="${BACKUP_DIR}/$(basename "${PREVIEW_NGINX_SITE}").bak.${TIMESTAMP}"
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
    if [ "${STATUS_CONF_CREATED}" = "yes" ]; then
        ${SUDO} rm -f "${PREVIEW_STATUS_CONF}"
        log "also removed ${PREVIEW_STATUS_CONF}, which this run had just written"
    fi
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
  status page    ${PREVIEW_PUBLIC_BASE_URL%/}/previews/
  page root      ${PREVIEW_WEB_ROOT}
  deploy logs    ${PREVIEW_LOG_DIR}
  host sampler   ${PREVIEW_STATS_SERVICE}

The GitHub Actions runner user also needs passwordless sudo for docker, nginx,
systemctl reload nginx, tee, rm and mkdir. That is already the case on
cicd.rtx.ai, because .github/workflows/pytest.yml calls "sudo docker" with no
terminal attached. Check it as the runner user with:

    sudo -n true && echo "passwordless sudo works"

Deploy a preview with:

    bash deploy/preview/deploy.sh <PR> <BRANCH>

NOTE_EOF
