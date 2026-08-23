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
# Refuse to build below this much free space on the docker root. One preview
# image is about 3.94 GB.
PREVIEW_MIN_FREE_DISK_GB="${PREVIEW_MIN_FREE_DISK_GB:-10}"
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
    PREVIEW_MIN_FREE_DISK_GB PREVIEW_MIN_FREE_RAM_MB \
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

# write_status_page
# Regenerates ${PREVIEW_WEB_ROOT}/index.html from the docker labels of every
# preview container on the box, plus whatever per-PR report files exist at
# generation time. Called by deploy.sh, teardown.sh, gc.sh and the installer.
# Best effort throughout: the page is a convenience and must never be able to
# fail a deploy or a teardown.
write_status_page() {
    if [ -z "${PREVIEW_WEB_ROOT}" ]; then
        return 0
    fi
    if ! ${SUDO} mkdir -p "${PREVIEW_WEB_ROOT}/data" 2>/dev/null; then
        log "WARNING: could not create ${PREVIEW_WEB_ROOT}, skipping the status page"
        return 0
    fi
    ${SUDO} chmod 755 "${PREVIEW_WEB_ROOT}" "${PREVIEW_WEB_ROOT}/data" 2>/dev/null || true

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

# name on disk, label in the expander
DATA_FILES = [
    ("deploy-log.txt", "deploy log"),
    ("smoke.md", "smoke test"),
    ("pytest.md", "pytest"),
    ("queries.md", "live queries"),
]
# A runaway file must not turn the page into a 40 MB download.
MAX_EMBED_BYTES = 200000


def esc(value):
    return html_module.escape(str(value), quote=True)


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

out = []
out.append("<!DOCTYPE html>")
out.append("<html lang=\"en\">")
out.append("<head>")
out.append("<meta charset=\"utf-8\">")
out.append("<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">")
out.append("<title>ARAX preview host</title>")
out.append("<style>")
out.append(""":root { color-scheme: dark; }
* { box-sizing: border-box; }
body { margin: 0; background: #15171a; color: #d7dae0;
       font: 15px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
.wrap { max-width: 920px; margin: 0 auto; padding: 34px 20px 64px; }
h1 { font-size: 22px; margin: 0 0 10px; font-weight: 600; }
p.lede { color: #98a0ab; margin: 0 0 26px; max-width: 70ch; }
a { color: #7bb2f0; }
a:hover { color: #a9cdf7; }
.card { border: 1px solid #2b3037; border-radius: 8px; background: #1b1e23;
        padding: 16px 18px; margin: 0 0 16px; }
.card h2 { font-size: 17px; font-weight: 600; margin: 0 0 12px;
           display: flex; align-items: center; gap: 9px; }
.dot { width: 10px; height: 10px; border-radius: 50%; background: #59616c;
       display: inline-block; flex: none; }
.dot.ok { background: #46a758; }
.dot.bad { background: #d1444a; }
dl { display: grid; grid-template-columns: 108px minmax(0, 1fr); gap: 3px 14px; margin: 0; }
dt { color: #98a0ab; }
dd { margin: 0; overflow-wrap: anywhere; }
code { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 13px; }
.running { color: #46a758; }
.stopped { color: #d68b3c; }
details { border-top: 1px solid #2b3037; margin-top: 10px; padding-top: 9px; }
details + details { margin-top: 0; }
summary { cursor: pointer; color: #98a0ab; font-size: 14px; }
pre { overflow-x: auto; background: #101216; border: 1px solid #2b3037; border-radius: 6px;
      padding: 10px 12px; font-size: 12px; line-height: 1.45; margin: 10px 0 4px;
      white-space: pre-wrap; overflow-wrap: anywhere; }
.empty { color: #98a0ab; border: 1px dashed #2b3037; border-radius: 8px; padding: 22px; text-align: center; }
footer { color: #6d7681; font-size: 13px; border-top: 1px solid #2b3037;
         margin-top: 30px; padding-top: 14px; }""")
out.append("</style>")
out.append("</head>")
out.append("<body>")
out.append("<div class=\"wrap\">")
out.append("<h1>ARAX preview host</h1>")
out.append(
    "<p class=\"lede\">This is cicd.rtx.ai. Every card below is a per-PR preview deployment of "
    "<a href=\"https://github.com/" + esc(repo) + "\">" + esc(repo) + "</a>, built from that pull "
    "request and served from its own container. See <code>deploy/preview/README.md</code> in the "
    "repository for how they are made and torn down. Previews are public, unauthenticated and "
    "temporary: they are removed " + esc(ttl) + " days after they are deployed, or as soon as "
    "their pull request closes.</p>"
)

if not previews:
    out.append("<p class=\"empty\">No previews are deployed right now.</p>")

for item in previews:
    pr = item["pr"]
    path = "/" + prefix + pr
    url = base_url + path + "/"
    status_path = path + "/api/arax/v1.4/status"
    sha = item["sha"]
    out.append("<div class=\"card\">")
    out.append(
        "<h2><span class=\"dot\" data-status=\"" + esc(status_path) + "\" title=\"health unknown\">"
        "</span><a href=\"https://github.com/" + esc(repo) + "/pull/" + esc(pr) + "\">PR #"
        + esc(pr) + "</a></h2>"
    )
    out.append("<dl>")
    out.append("<dt>branch</dt><dd><code>" + esc(item["branch"]) + "</code></dd>")
    if sha and sha != "unknown":
        out.append(
            "<dt>commit</dt><dd><a href=\"https://github.com/" + esc(repo) + "/commit/" + esc(sha)
            + "\"><code>" + esc(sha[:7]) + "</code></a></dd>"
        )
    else:
        out.append("<dt>commit</dt><dd><code>unknown</code></dd>")
    out.append("<dt>created</dt><dd>" + esc(item["created"]) + "</dd>")
    state_class = "running" if item["state"] == "running" else "stopped"
    out.append("<dt>state</dt><dd class=\"" + state_class + "\">" + esc(item["state"]) + "</dd>")
    out.append("<dt>preview</dt><dd><a href=\"" + esc(url) + "\">" + esc(url) + "</a></dd>")
    out.append("</dl>")
    for name, label in DATA_FILES:
        body = read_data_file(pr, name)
        if body is None:
            continue
        out.append("<details><summary>" + esc(label) + "</summary>")
        out.append("<pre>" + esc(body.rstrip()) + "</pre>")
        out.append("</details>")
    out.append("</div>")

out.append(
    "<footer>Generated " + time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    + ". This page is rewritten on every deploy, on every teardown and by the nightly garbage "
    "collection, so it can be up to a day behind a container that died on its own. The dots are "
    "live and are checked by your browser when the page loads.</footer>"
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
