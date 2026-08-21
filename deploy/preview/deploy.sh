#!/usr/bin/env bash
#
# Deploy one ARAX preview environment for a pull request on cicd.rtx.ai.
# Idempotent: running it again replaces the container, the image and the
# nginx snippet for that PR.
#
# Usage: deploy.sh <PR> <BRANCH> [SHA]
#
# Issue #2846.

set -o nounset -o pipefail -o errexit

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
. "${SCRIPT_DIR}/lib.sh"

usage() {
    cat >&2 <<'USAGE_EOF'
Usage: deploy.sh <PR> <BRANCH> [SHA]

  PR      pull request number, for example 2853
  BRANCH  branch name on RTXteam/RTX, for example issue-2846
  SHA     optional commit sha, recorded as a container label only
USAGE_EOF
    exit 2
}

# ---------------------------------------------------------------------------
# 1. Validate arguments and the host setup
# ---------------------------------------------------------------------------

[ "$#" -ge 2 ] || usage

PR="$1"
BRANCH="$2"
SHA="${3:-unknown}"

require_int "${PR}" "PR number"
[ -n "${BRANCH}" ] || die "branch name must not be empty"

PORT="$(preview_port "${PR}")"
CONTAINER="$(preview_container "${PR}")"
IMAGE="$(preview_image "${PR}")"
PUBLIC_PATH="$(preview_path "${PR}")"
PUBLIC_URL="$(preview_url "${PR}")"
NGINX_CONF="$(preview_nginx_conf "${PR}")"

log "step 1/8 validating host setup"
log "PR ${PR}, branch ${BRANCH}, sha ${SHA}"
log "container ${CONTAINER}, image ${IMAGE}, port 127.0.0.1:${PORT}"
log "public url ${PUBLIC_URL}"

if ! ${SUDO} test -d "${PREVIEW_NGINX_DIR}"; then
    die "${PREVIEW_NGINX_DIR} does not exist. Run deploy/preview/install-nginx-include.sh once on this host as a human with sudo."
fi
if ! ${SUDO} test -w "${PREVIEW_NGINX_DIR}"; then
    die "${PREVIEW_NGINX_DIR} is not writable through sudo. Run deploy/preview/install-nginx-include.sh once on this host as a human with sudo."
fi
[ -f "${PREVIEW_DOCKERFILE}" ] || die "Dockerfile ${PREVIEW_DOCKERFILE} not found. Set PREVIEW_BUILD_CONTEXT to a checkout's DockerBuild directory."
log "build context ${PREVIEW_BUILD_CONTEXT}, dockerfile ${PREVIEW_DOCKERFILE}"

# ---------------------------------------------------------------------------
# 2. Remove anything left over from a previous deploy of this PR
# ---------------------------------------------------------------------------

log "step 2/8 removing any previous container and image for PR ${PR}"
${DOCKER} rm -f "${CONTAINER}" >/dev/null 2>&1 || log "no previous container ${CONTAINER}"
${DOCKER} rmi -f "${IMAGE}" >/dev/null 2>&1 || log "no previous image ${IMAGE}"

# ---------------------------------------------------------------------------
# 3. Build the image
# ---------------------------------------------------------------------------

# CICD-Dockerfile git clones RTXteam/RTX inside the image and checks out
# BUILD_BRANCH, so the branch has to exist on the upstream repository. Fork
# pull requests cannot work with this build and are refused by the workflow.
log "step 3/8 building ${IMAGE} from branch ${BRANCH} (this takes a while)"
${DOCKER} build \
    --no-cache=true \
    --rm \
    --build-arg "BUILD_BRANCH=${BRANCH}" \
    -t "${IMAGE}" \
    -f "${PREVIEW_DOCKERFILE}" \
    "${PREVIEW_BUILD_CONTEXT}/"

# ---------------------------------------------------------------------------
# 4. Run the container and start the services inside it
# ---------------------------------------------------------------------------

CREATED="$(date -u '+%s')"

# The image has no CMD and no ENTRYPOINT, so it needs -d -i -t to stay up,
# exactly like the pytest workflow does.
log "step 4/8 starting ${CONTAINER} on 127.0.0.1:${PORT}"
${DOCKER} run -d -i -t \
    --name "${CONTAINER}" \
    -p "127.0.0.1:${PORT}:80" \
    -v "${PREVIEW_DB_DIR}:/mnt/data/orangeboard/databases" \
    -v "${PREVIEW_CONFIG_SECRETS}:/mnt/data/orangeboard/production/RTX/code/config_secrets.json" \
    --label "arax.preview=true" \
    --label "arax.preview.pr=${PR}" \
    --label "arax.preview.branch=${BRANCH}" \
    --label "arax.preview.sha=${SHA}" \
    --label "arax.preview.created=${CREATED}" \
    "${IMAGE}"

log "creating database symlinks"
${DOCKER} exec "${CONTAINER}" bash -c "sudo -u rt bash -c 'cd /mnt/data/orangeboard/production/RTX && python3 code/ARAX/ARAXQuery/ARAX_database_manager.py'"

log "building the KP info cache"
${DOCKER} exec "${CONTAINER}" bash -c "cd /mnt/data/orangeboard/production/RTX/code/ARAX/ARAXQuery/Expand && python3 kp_info_cacher.py"

log "starting apache2, RTX_OpenAPI_production and RTX_Complete"
${DOCKER} exec "${CONTAINER}" service apache2 start
${DOCKER} exec "${CONTAINER}" service RTX_OpenAPI_production start
${DOCKER} exec "${CONTAINER}" service RTX_Complete start

# ---------------------------------------------------------------------------
# 5. Publish the preview through nginx
# ---------------------------------------------------------------------------

log "step 5/8 writing ${NGINX_CONF}"

# Keep a copy of the shared autocomplete snippet so a failed nginx -t can be
# rolled back to exactly what was there before.
RTXCOMPLETE_BACKUP=""
if ${SUDO} test -f "${PREVIEW_RTXCOMPLETE_CONF}"; then
    RTXCOMPLETE_BACKUP="$(mktemp)"
    ${SUDO} cat "${PREVIEW_RTXCOMPLETE_CONF}" > "${RTXCOMPLETE_BACKUP}"
fi

rollback_nginx() {
    ${SUDO} rm -f "${NGINX_CONF}"
    if [ -n "${RTXCOMPLETE_BACKUP}" ]; then
        ${SUDO} tee "${PREVIEW_RTXCOMPLETE_CONF}" >/dev/null < "${RTXCOMPLETE_BACKUP}"
    else
        ${SUDO} rm -f "${PREVIEW_RTXCOMPLETE_CONF}"
    fi
    rm -f "${RTXCOMPLETE_BACKUP}"
    # Best effort: put nginx back on the configuration it had before.
    nginx_reload || log "nginx did not reload after rollback, inspect the host by hand"
}

# The trailing slash on proxy_pass is what strips the /<PR>/ prefix before the
# request reaches apache in the container.
${SUDO} tee "${NGINX_CONF}" >/dev/null <<NGINX_EOF
# managed by deploy/preview/deploy.sh, PR ${PR}, branch ${BRANCH}, sha ${SHA}, created $(date -u '+%Y-%m-%dT%H:%M:%SZ')
location = ${PUBLIC_PATH} { return 301 ${PUBLIC_PATH}/; }
location ${PUBLIC_PATH}/ {
    proxy_pass http://127.0.0.1:${PORT}/;
    proxy_read_timeout 3000s;
    proxy_buffering off;
    proxy_set_header Host \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
    proxy_set_header X-Forwarded-Prefix ${PUBLIC_PATH};
}
NGINX_EOF

write_rtxcomplete_conf "${PORT}" "${PR}"

if ! nginx_reload; then
    rollback_nginx
    die "nginx rejected the preview configuration for PR ${PR}, rolled back"
fi
rm -f "${RTXCOMPLETE_BACKUP}"

# ---------------------------------------------------------------------------
# 6. Wait for the ARAX API to come up
# ---------------------------------------------------------------------------

HEALTH_URL="http://127.0.0.1:${PORT}/api/arax/v1.4/status"
log "step 6/8 polling ${HEALTH_URL} for up to ${PREVIEW_HEALTH_TIMEOUT}s"

DEADLINE=$(( $(date -u '+%s') + PREVIEW_HEALTH_TIMEOUT ))
HEALTHY="no"
while [ "$(date -u '+%s')" -lt "${DEADLINE}" ]; do
    if curl -fsS -o /dev/null -m 15 "${HEALTH_URL}"; then
        HEALTHY="yes"
        break
    fi
    sleep 10
done

if [ "${HEALTHY}" != "yes" ]; then
    log "the preview never answered ${HEALTH_URL}, last 200 lines of container output follow"
    ${DOCKER} logs --tail 200 "${CONTAINER}" >&2 || true
    die "PR ${PR} preview failed its health check after ${PREVIEW_HEALTH_TIMEOUT}s"
fi
log "health check passed"

# ---------------------------------------------------------------------------
# 7. Check the public URL, without failing the deploy on it
# ---------------------------------------------------------------------------

log "step 7/8 checking the public URL"
if curl -fsS -o /dev/null -m 20 "${PUBLIC_URL}api/arax/v1.4/status"; then
    log "public url ok: ${PUBLIC_URL}"
else
    log "WARNING: ${PUBLIC_URL}api/arax/v1.4/status did not answer. The container is healthy, so this points at nginx or DNS on the host."
fi

# ---------------------------------------------------------------------------
# 8. Summary
# ---------------------------------------------------------------------------

log "step 8/8 done"
cat <<SUMMARY_EOF
=====================================================
ARAX preview deployed
  pr        ${PR}
  branch    ${BRANCH}
  sha       ${SHA}
  url       ${PUBLIC_URL}
  port      127.0.0.1:${PORT}
  container ${CONTAINER}
  image     ${IMAGE}
  nginx     ${NGINX_CONF}
=====================================================
SUMMARY_EOF

if [ -n "${GITHUB_OUTPUT:-}" ]; then
    {
        printf 'url=%s\n' "${PUBLIC_URL}"
        printf 'port=%s\n' "${PORT}"
        printf 'container=%s\n' "${CONTAINER}"
        printf 'image=%s\n' "${IMAGE}"
        printf 'path=%s\n' "${PUBLIC_PATH}"
    } >> "${GITHUB_OUTPUT}"
fi
