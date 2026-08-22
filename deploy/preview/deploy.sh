#!/usr/bin/env bash
#
# Deploy one ARAX preview environment for a pull request on cicd.rtx.ai.
# Idempotent: running it again either fast redeploys the container that is
# already up, or replaces the container, the image and the nginx snippet.
#
# Usage: deploy.sh [--force] <PR> <BRANCH> [SHA]
#
# Issue #2846.

set -o nounset -o pipefail -o errexit

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
. "${SCRIPT_DIR}/lib.sh"

usage() {
    cat >&2 <<'USAGE_EOF'
Usage: deploy.sh [--force] <PR> <BRANCH> [SHA]

  PR       pull request number, for example 2853
  BRANCH   branch name on RTXteam/RTX, for example issue-2846
  SHA      optional commit sha. With a sha the script can fast redeploy an
           already running preview instead of rebuilding its image.
  --force  always rebuild the image, even when a fast redeploy is possible.
           May appear before or after the positional arguments.
USAGE_EOF
    exit 2
}

# ---------------------------------------------------------------------------
# 1. Validate arguments and the host setup
# ---------------------------------------------------------------------------

FORCE="no"
PR=""
BRANCH=""
SHA=""
POSITIONAL_COUNT=0

# Hand rolled parsing rather than getopts, because --force has to be accepted
# on either side of the positional arguments.
for arg in "$@"; do
    case "${arg}" in
        --force)
            FORCE="yes"
            ;;
        -h|--help)
            usage
            ;;
        -*)
            die "unknown option '${arg}'"
            ;;
        *)
            POSITIONAL_COUNT=$(( POSITIONAL_COUNT + 1 ))
            case "${POSITIONAL_COUNT}" in
                1) PR="${arg}" ;;
                2) BRANCH="${arg}" ;;
                3) SHA="${arg}" ;;
                *) die "too many arguments, expected at most PR, BRANCH and SHA" ;;
            esac
            ;;
    esac
done

[ "${POSITIONAL_COUNT}" -ge 2 ] || usage
[ -n "${SHA}" ] || SHA="unknown"

require_int "${PR}" "PR number"
[ -n "${BRANCH}" ] || die "branch name must not be empty"

PORT="$(preview_port "${PR}")"
CONTAINER="$(preview_container "${PR}")"
IMAGE="$(preview_image "${PR}")"
PUBLIC_PATH="$(preview_path "${PR}")"
PUBLIC_URL="$(preview_url "${PR}")"
NGINX_CONF="$(preview_nginx_conf "${PR}")"
HEALTH_URL="http://127.0.0.1:${PORT}/api/arax/v1.4/status"

# Where CICD-Dockerfile puts the clone it makes inside the image.
CONTAINER_REPO="/mnt/data/orangeboard/production/RTX"
# A change to any of these cannot be picked up by a git checkout inside the
# running container: requirements.txt and DockerBuild/ are baked into the
# image at build time, and config_dbs.json decides which database files the
# container was set up with.
FAST_GATE_PATHS="requirements.txt DockerBuild/ code/config_dbs.json"

log "step 1/10 validating host setup"
log "PR ${PR}, branch ${BRANCH}, sha ${SHA}, force ${FORCE}"
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
# Helpers shared by both paths
# ---------------------------------------------------------------------------

# container_git <git command words>
# The clone inside the container belongs to user rt and apache serves it, so
# every git command has to run as rt. Running it as root would leave root
# owned objects in .git and trip git's dubious ownership check afterwards.
container_git() {
    local cmd="$*"
    ${DOCKER} exec "${CONTAINER}" bash -c "sudo -u rt bash -c 'cd ${CONTAINER_REPO} && ${cmd}'"
}

# True for something that looks like a git object name. This also keeps the
# value safe to interpolate into the nested shell command above.
is_sha() {
    local value="${1:-}"
    case "${value}" in
        ''|*[!0-9a-fA-F]*) return 1 ;;
    esac
    [ "${#value}" -ge 7 ]
}

# wait_healthy <seconds>
# Polls the container's own status endpoint. Returns non-zero on timeout so
# the caller can decide what to log and how to fail.
wait_healthy() {
    local timeout="${1}"
    local deadline
    deadline=$(( $(date -u '+%s') + timeout ))
    while [ "$(date -u '+%s')" -lt "${deadline}" ]; do
        if curl -fsS -o /dev/null -m 15 "${HEALTH_URL}"; then
            return 0
        fi
        sleep 10
    done
    return 1
}

# Only the lines nginx acts on. The header comment carries a timestamp that
# changes on every run, so comparing whole files would always report a change.
nginx_conf_body() {
    ${SUDO} cat "${1}" 2>/dev/null | grep -v '^#' || true
}

NGINX_CONF_BACKUP=""
RTXCOMPLETE_BACKUP=""

# Puts the two snippets back exactly as they were, then reloads. Restoring
# beats deleting: on a fast redeploy the previous snippet was serving a
# working preview.
rollback_nginx() {
    if [ -n "${NGINX_CONF_BACKUP}" ]; then
        ${SUDO} tee "${NGINX_CONF}" >/dev/null < "${NGINX_CONF_BACKUP}"
    else
        ${SUDO} rm -f "${NGINX_CONF}"
    fi
    if [ -n "${RTXCOMPLETE_BACKUP}" ]; then
        ${SUDO} tee "${PREVIEW_RTXCOMPLETE_CONF}" >/dev/null < "${RTXCOMPLETE_BACKUP}"
    else
        ${SUDO} rm -f "${PREVIEW_RTXCOMPLETE_CONF}"
    fi
    clean_nginx_backups
    # Best effort: put nginx back on the configuration it had before.
    nginx_reload || log "nginx did not reload after rollback, inspect the host by hand"
}

clean_nginx_backups() {
    if [ -n "${NGINX_CONF_BACKUP}" ]; then
        rm -f "${NGINX_CONF_BACKUP}"
        NGINX_CONF_BACKUP=""
    fi
    if [ -n "${RTXCOMPLETE_BACKUP}" ]; then
        rm -f "${RTXCOMPLETE_BACKUP}"
        RTXCOMPLETE_BACKUP=""
    fi
}

# publish_nginx <always|if-changed>
# Writes both snippets and reloads nginx. With if-changed the reload is
# skipped when the effective configuration is byte for byte what it already
# was, which is the normal case for a fast redeploy.
publish_nginx() {
    local reload_mode="${1}"
    local before_conf before_shared after_conf after_shared

    before_conf="$(nginx_conf_body "${NGINX_CONF}")"
    before_shared="$(nginx_conf_body "${PREVIEW_RTXCOMPLETE_CONF}")"

    # Keep copies so a failed nginx -t can be rolled back to exactly what was
    # there before.
    if ${SUDO} test -f "${NGINX_CONF}"; then
        NGINX_CONF_BACKUP="$(mktemp)"
        ${SUDO} cat "${NGINX_CONF}" > "${NGINX_CONF_BACKUP}"
    fi
    if ${SUDO} test -f "${PREVIEW_RTXCOMPLETE_CONF}"; then
        RTXCOMPLETE_BACKUP="$(mktemp)"
        ${SUDO} cat "${PREVIEW_RTXCOMPLETE_CONF}" > "${RTXCOMPLETE_BACKUP}"
    fi

    # The trailing slash on proxy_pass is what strips the /<PR>/ prefix before
    # the request reaches apache in the container.
    ${SUDO} tee "${NGINX_CONF}" >/dev/null <<NGINX_EOF
# managed by deploy/preview/deploy.sh, PR ${PR}, branch ${BRANCH}, sha ${SHA}, written $(date -u '+%Y-%m-%dT%H:%M:%SZ')
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

    after_conf="$(nginx_conf_body "${NGINX_CONF}")"
    after_shared="$(nginx_conf_body "${PREVIEW_RTXCOMPLETE_CONF}")"

    if [ "${reload_mode}" = "if-changed" ] \
        && [ "${before_conf}" = "${after_conf}" ] \
        && [ "${before_shared}" = "${after_shared}" ]; then
        log "nginx routing is unchanged, skipping the reload"
        clean_nginx_backups
        return 0
    fi

    if ! nginx_reload; then
        rollback_nginx
        die "nginx rejected the preview configuration for PR ${PR}, rolled back"
    fi
    clean_nginx_backups
}

# ---------------------------------------------------------------------------
# 2. Decide between a fast redeploy and a full rebuild
# ---------------------------------------------------------------------------

MODE="full"
REASON=""
RUNNING_SHA=""

# Sets MODE and REASON. Every reason to fall back is a plain return, never a
# failure, because a full rebuild is always a correct answer.
decide_mode() {
    local changed=""

    if [ "${FORCE}" = "yes" ]; then
        REASON="--force was given"
        return 0
    fi
    if ! is_sha "${SHA}"; then
        REASON="no commit sha was passed"
        return 0
    fi
    if ! container_running "${CONTAINER}"; then
        REASON="no running container ${CONTAINER}"
        return 0
    fi

    # The arax.preview.sha label is deliberately not used here. Labels cannot
    # be changed on a running container, so the label still names the commit
    # the image was built from after any fast redeploy.
    RUNNING_SHA="$(container_git git rev-parse HEAD | tr -d '[:space:]')" || RUNNING_SHA=""
    if ! is_sha "${RUNNING_SHA}"; then
        REASON="could not read the sha checked out in ${CONTAINER}"
        return 0
    fi
    log "${CONTAINER} currently has ${RUNNING_SHA} checked out"

    if ! container_git git fetch origin; then
        REASON="git fetch origin failed inside ${CONTAINER}"
        return 0
    fi
    if ! container_git "git cat-file -e ${SHA}^{commit}"; then
        REASON="target sha not on origin"
        return 0
    fi

    if ! changed="$(container_git "git diff --name-only ${RUNNING_SHA} ${SHA} -- ${FAST_GATE_PATHS}" | tr '\n' ' ')"; then
        REASON="git diff failed inside ${CONTAINER}"
        return 0
    fi
    # Collapse the file list onto one line so it can be a GITHUB_OUTPUT value.
    changed="$(printf '%s' "${changed}" | sed 's/  */ /g; s/ $//')"
    if [ -n "${changed}" ]; then
        REASON="image inputs changed: ${changed}"
        return 0
    fi

    MODE="fast"
    REASON="no image inputs changed between ${RUNNING_SHA} and ${SHA}"
}

log "step 2/10 deciding how to deploy"
decide_mode
if [ "${MODE}" = "fast" ]; then
    log "mode: fast (${REASON})"
else
    log "mode: full rebuild (${REASON})"
fi

if [ "${MODE}" = "fast" ]; then

    # -----------------------------------------------------------------------
    # Fast path: move the clone inside the running container to the new commit
    # and restart the two Flask services. No image build, no new container.
    # -----------------------------------------------------------------------

    # 3. Move the working tree onto the new commit
    log "step 3/10 checking out ${SHA} inside ${CONTAINER}"
    # Detached on purpose. The preview only ever has to match one commit, and
    # a detached HEAD cannot drift with a force pushed branch.
    if ! container_git "git checkout --detach ${SHA}"; then
        die "git checkout ${SHA} failed inside ${CONTAINER}. Rerun deploy.sh with --force to rebuild this preview from scratch."
    fi

    # 4. Database symlinks, in case the new commit changed config_dbs.json
    #    in a way that only adds or renames a symlink.
    log "step 4/10 refreshing database symlinks"
    ${DOCKER} exec "${CONTAINER}" bash -c "sudo -u rt bash -c 'cd /mnt/data/orangeboard/production/RTX && python3 code/ARAX/ARAXQuery/ARAX_database_manager.py'"

    # 5. KP info cache
    log "step 5/10 rebuilding the KP info cache"
    ${DOCKER} exec "${CONTAINER}" bash -c "cd /mnt/data/orangeboard/production/RTX/code/ARAX/ARAXQuery/Expand && python3 kp_info_cacher.py"

    # 6. Restart the Flask services only. Apache serves the UI straight from
    #    the working tree, so UI changes are already live without a restart.
    log "step 6/10 restarting RTX_OpenAPI_production and RTX_Complete"
    ${DOCKER} exec "${CONTAINER}" service RTX_OpenAPI_production restart
    ${DOCKER} exec "${CONTAINER}" service RTX_Complete restart

    # 7. nginx. The routing is almost certainly identical, the rewrite is here
    #    to keep the sha in the header honest.
    log "step 7/10 refreshing ${NGINX_CONF}"
    publish_nginx "if-changed"

    # 8. Health
    log "step 8/10 polling ${HEALTH_URL} for up to ${PREVIEW_FAST_HEALTH_TIMEOUT}s"
    if ! wait_healthy "${PREVIEW_FAST_HEALTH_TIMEOUT}"; then
        log "the preview never answered ${HEALTH_URL}, last 200 lines of container output follow"
        ${DOCKER} logs --tail 200 "${CONTAINER}" >&2 || true
        # No automatic rebuild here. A fast redeploy that fails is worth
        # looking at, and a silent six minute rebuild would hide it.
        die "PR ${PR} fast redeploy failed its health check after ${PREVIEW_FAST_HEALTH_TIMEOUT}s. Rerun deploy.sh with --force to rebuild this preview from scratch."
    fi
    log "health check passed"

else

    # -----------------------------------------------------------------------
    # Full path: rebuild the image and replace the container.
    # -----------------------------------------------------------------------

    # 3. Remove anything left over from a previous deploy of this PR
    log "step 3/10 removing any previous container and image for PR ${PR}"
    ${DOCKER} rm -f "${CONTAINER}" >/dev/null 2>&1 || log "no previous container ${CONTAINER}"
    ${DOCKER} rmi -f "${IMAGE}" >/dev/null 2>&1 || log "no previous image ${IMAGE}"

    # 4. Build the image
    #    CICD-Dockerfile git clones RTXteam/RTX inside the image and checks out
    #    BUILD_BRANCH, so the branch has to exist on the upstream repository.
    #    Fork pull requests cannot work with this build and are refused by the
    #    workflow.
    log "step 4/10 building ${IMAGE} from branch ${BRANCH} (this takes a while)"
    ${DOCKER} build \
        --no-cache=true \
        --rm \
        --build-arg "BUILD_BRANCH=${BRANCH}" \
        -t "${IMAGE}" \
        -f "${PREVIEW_DOCKERFILE}" \
        "${PREVIEW_BUILD_CONTEXT}/"

    # 5. Run the container
    CREATED="$(date -u '+%s')"

    # The image has no CMD and no ENTRYPOINT, so it needs -d -i -t to stay up,
    # exactly like the pytest workflow does.
    log "step 5/10 starting ${CONTAINER} on 127.0.0.1:${PORT}"
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

    # 6. Start the services inside it
    log "step 6/10 setting up databases and starting the services"
    log "creating database symlinks"
    ${DOCKER} exec "${CONTAINER}" bash -c "sudo -u rt bash -c 'cd /mnt/data/orangeboard/production/RTX && python3 code/ARAX/ARAXQuery/ARAX_database_manager.py'"

    log "building the KP info cache"
    ${DOCKER} exec "${CONTAINER}" bash -c "cd /mnt/data/orangeboard/production/RTX/code/ARAX/ARAXQuery/Expand && python3 kp_info_cacher.py"

    log "starting apache2, RTX_OpenAPI_production and RTX_Complete"
    ${DOCKER} exec "${CONTAINER}" service apache2 start
    ${DOCKER} exec "${CONTAINER}" service RTX_OpenAPI_production start
    ${DOCKER} exec "${CONTAINER}" service RTX_Complete start

    # 7. Publish the preview through nginx
    log "step 7/10 writing ${NGINX_CONF}"
    publish_nginx "always"

    # 8. Wait for the ARAX API to come up
    log "step 8/10 polling ${HEALTH_URL} for up to ${PREVIEW_HEALTH_TIMEOUT}s"
    if ! wait_healthy "${PREVIEW_HEALTH_TIMEOUT}"; then
        log "the preview never answered ${HEALTH_URL}, last 200 lines of container output follow"
        ${DOCKER} logs --tail 200 "${CONTAINER}" >&2 || true
        die "PR ${PR} preview failed its health check after ${PREVIEW_HEALTH_TIMEOUT}s"
    fi
    log "health check passed"

fi

# ---------------------------------------------------------------------------
# 9. Check the public URL, without failing the deploy on it
# ---------------------------------------------------------------------------

log "step 9/10 checking the public URL"
if curl -fsS -o /dev/null -m 20 "${PUBLIC_URL}api/arax/v1.4/status"; then
    log "public url ok: ${PUBLIC_URL}"
else
    log "WARNING: ${PUBLIC_URL}api/arax/v1.4/status did not answer. The container is healthy, so this points at nginx or DNS on the host."
fi

# ---------------------------------------------------------------------------
# 10. Summary
# ---------------------------------------------------------------------------

log "step 10/10 done"
cat <<SUMMARY_EOF
=====================================================
ARAX preview deployed
  pr        ${PR}
  branch    ${BRANCH}
  sha       ${SHA}
  mode      ${MODE}
  reason    ${REASON}
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
        printf 'mode=%s\n' "${MODE}"
        printf 'reason=%s\n' "${REASON}"
    } >> "${GITHUB_OUTPUT}"
fi
