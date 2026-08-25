#!/usr/bin/env bash
#
# Deploy one ARAX preview environment for a pull request on cicd.rtx.ai.
# Idempotent: running it again either fast redeploys the container that is
# already up, or replaces the container, the image and the nginx snippet.
#
# Usage: deploy.sh [--force|--fast-only] <PR> <BRANCH> [SHA]
#
# With no flag the script picks the path itself, which is what a human on the
# host wants. The workflow always says which one it means: /deploy runs it
# with --force and /redeploy with --fast-only.
#
# Issue #2846.

set -o nounset -o pipefail -o errexit

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
. "${SCRIPT_DIR}/lib.sh"
preview_validate_env

usage() {
    cat >&2 <<'USAGE_EOF'
Usage: deploy.sh [--force|--fast-only] <PR> <BRANCH> [SHA]

  PR           pull request number, for example 2853
  BRANCH       branch name on RTXteam/RTX, for example issue-2846
  SHA          optional commit sha. With a sha the script can fast redeploy an
               already running preview instead of rebuilding its image.
  --force      always rebuild the image, even when a fast redeploy is possible.
  --fast-only  never rebuild. Restart the running preview on the new commit,
               and refuse with a reason when that cannot be done.
  Both flags may appear before or after the positional arguments, and they
  cannot be given together.
USAGE_EOF
    exit 2
}

# ---------------------------------------------------------------------------
# 1. Validate arguments and the host setup
# ---------------------------------------------------------------------------

FORCE="no"
FAST_ONLY="no"
PR=""
BRANCH=""
SHA=""
POSITIONAL_COUNT=0

# Hand rolled parsing rather than getopts, because the flags have to be
# accepted on either side of the positional arguments.
for arg in "$@"; do
    case "${arg}" in
        --force)
            FORCE="yes"
            ;;
        --fast-only)
            FAST_ONLY="yes"
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

# One flag says never restart and the other says never rebuild, so asking for
# both is a mistake in the caller rather than a situation to resolve.
if [ "${FORCE}" = "yes" ] && [ "${FAST_ONLY}" = "yes" ]; then
    printf 'ERROR: --force and --fast-only cannot be given together\n\n' >&2
    usage
fi

[ "${POSITIONAL_COUNT}" -ge 2 ] || usage
[ -n "${SHA}" ] || SHA="unknown"

require_int "${PR}" "PR number"
[ -n "${BRANCH}" ] || die "branch name must not be empty"

# ---------------------------------------------------------------------------
# Log capture and the end of run bookkeeping
# ---------------------------------------------------------------------------

# Everything printed from here on is copied into a host log file as well, and
# the tail of that file is what the status page shows under this pull request.
# The workflow still tees the same output into the job log and the artifact.
DEPLOY_LOG_FILE=""
DEPLOY_LOG_TEE_PID=""

setup_log_capture() {
    [ -n "${PREVIEW_LOG_DIR}" ] || return 0
    if ! ${SUDO} mkdir -p "${PREVIEW_LOG_DIR}" 2>/dev/null; then
        log "WARNING: could not create ${PREVIEW_LOG_DIR}, this deploy is not logged to disk"
        return 0
    fi
    ${SUDO} chmod 755 "${PREVIEW_LOG_DIR}" 2>/dev/null || true
    DEPLOY_LOG_FILE="${PREVIEW_LOG_DIR}/pr${PR}-$(date -u '+%Y%m%dT%H%M%SZ').log"
    # tee runs through sudo because the directory belongs to root and the
    # runner user is not root.
    exec > >(${SUDO} tee -a "${DEPLOY_LOG_FILE}") 2>&1
    DEPLOY_LOG_TEE_PID="$!"
    ${SUDO} chmod 644 "${DEPLOY_LOG_FILE}" 2>/dev/null || true
}

# Copies the tail of this run's log where the status page can show it, then
# rewrites the status page. Every step is best effort.
publish_deploy_artifacts() {
    local tail_text build_text
    if [ -n "${DEPLOY_LOG_FILE}" ] && ${SUDO} test -f "${DEPLOY_LOG_FILE}"; then
        # The secrets guard is crude on purpose. The page is public, so a line
        # that so much as mentions a credential is dropped rather than shown.
        # The docker build section is stripped out here, from the step 4 line up
        # to but not including the step 5 line, so the deploy log is orchestration
        # only and the build lines live once, in build-log.txt below. A fast
        # redeploy has no such section, so nothing is removed on that path.
        tail_text="$(${SUDO} cat "${DEPLOY_LOG_FILE}" 2>/dev/null \
            | awk '/step 4\/10 building/ { skip = 1 }
                   /step 5\/10 starting/ { skip = 0 }
                   !skip { print }' \
            | tail -n 200 \
            | grep -viE 'password|token|secret|authorization' || true)"
        printf '%s\n' "${tail_text}" | write_preview_data "${PR}" "deploy-log.txt"

        # The docker build on its own, because the build is the part that is
        # worth reading when an image comes out wrong and the tail above is
        # all container start and health polling by then. The section runs
        # from the step 4 line to the step 5 line of the full path, so a fast
        # redeploy, which has no build, matches nothing.
        build_text="$(${SUDO} cat "${DEPLOY_LOG_FILE}" 2>/dev/null \
            | awk '/step 5\/10 starting/ { if (inside) { exit } }
                   /step 4\/10 building/ { inside = 1 }
                   inside { print }' \
            | tail -n 400 \
            | grep -viE 'password|token|secret|authorization' || true)"
        if [ -n "${build_text}" ]; then
            printf '%s\n' "${build_text}" | write_preview_data "${PR}" "build-log.txt"
        else
            # A fast redeploy must not leave the previous build on the page
            # looking like it belongs to this commit.
            ${SUDO} rm -f "$(preview_data_dir "${PR}")/build-log.txt" 2>/dev/null || true
        fi
    fi
    write_status_page
}

# Runs on every exit, including the ones die() takes. The original exit status
# is preserved so nothing here can turn a failed deploy into a green one.
finalize() {
    local rc=$?
    trap - EXIT
    set +o errexit
    # The card on the status page stops spinning here, whichever way this run
    # went. die() leaves its reason in PREVIEW_LAST_ERROR, so a refusal or a
    # failed health check is named on the card instead of a bare exit status.
    if [ "${rc}" -eq 0 ]; then
        if [ "${MODE:-full}" = "fast" ]; then
            write_preview_state "${PR}" "deploy" "done" "fast redeploy, no image rebuild"
        else
            write_preview_state "${PR}" "deploy" "done" "full rebuild"
        fi
    else
        write_preview_state "${PR}" "deploy" "failed" \
            "${PREVIEW_LAST_ERROR:-the deploy failed, see the deploy log below}"
    fi
    publish_deploy_artifacts
    # Let the tee child see end of file and finish writing before this process
    # goes away, so neither the host log nor the workflow log loses its tail.
    if [ -n "${DEPLOY_LOG_TEE_PID}" ]; then
        exec 1>&- 2>&-
        wait "${DEPLOY_LOG_TEE_PID}" 2>/dev/null || true
    fi
    exit "${rc}"
}

setup_log_capture
trap finalize EXIT

# Which pull request comment started this run. The workflow always says what
# it means: /redeploy runs with --fast-only and /deploy with --force.
if [ "${FAST_ONLY}" = "yes" ]; then
    DEPLOY_COMMAND="redeploy"
else
    DEPLOY_COMMAND="deploy"
fi

# The card has to be on the status page while the image is still building,
# which is minutes before any container exists, so the run state is written
# and the page is regenerated before any of the work starts. The reset is
# deliberate: the previous run's test results belong to the previous commit
# and must not sit next to a build that has only just begun.
export PREVIEW_STATE_RESET=1
export PREVIEW_STATE_BRANCH="${BRANCH}"
export PREVIEW_STATE_SHA="${SHA}"
export PREVIEW_STATE_COMMAND="${DEPLOY_COMMAND}"
write_preview_state "${PR}" "deploy" "running" "started by /${DEPLOY_COMMAND}"
unset PREVIEW_STATE_RESET PREVIEW_STATE_BRANCH PREVIEW_STATE_SHA PREVIEW_STATE_COMMAND
write_status_page

# refuse <one line reason>
# A preflight refusal. The reason is handed to the workflow so the pull
# request comment can say what the host ran out of, rather than the generic
# "the deploy failed".
refuse() {
    local reason="$*"
    if [ -n "${GITHUB_OUTPUT:-}" ]; then
        printf 'refused=%s\n' "${reason}" >> "${GITHUB_OUTPUT}"
    fi
    die "${reason}"
}

PORT="$(preview_port "${PR}")"
CONTAINER="$(preview_container "${PR}")"
IMAGE="$(preview_image "${PR}")"
PUBLIC_PATH="$(preview_path "${PR}")"
PUBLIC_URL="$(preview_url "${PR}")"
NGINX_CONF="$(preview_nginx_conf "${PR}")"
HEALTH_URL="http://127.0.0.1:${PORT}/api/arax/v1.4/status"

# Where CICD-Dockerfile puts the clone it makes inside the image.
CONTAINER_REPO="/mnt/data/orangeboard/production/RTX"
# The only paths a fast redeploy cannot apply. requirements.txt and DockerBuild/
# are baked into the image at build time and pip install never runs on the fast
# path, so a change to either needs a full rebuild. code/config_dbs.json is not
# gated: the fast path re-runs ARAX_database_manager.py, so a change to the
# database config is applied on every redeploy.
FAST_GATE_PATHS="requirements.txt DockerBuild/"

log "step 1/10 validating host setup"
log "PR ${PR}, branch ${BRANCH}, sha ${SHA}, force ${FORCE}, fast-only ${FAST_ONLY}"
log "container ${CONTAINER}, image ${IMAGE}, port 127.0.0.1:${PORT}"
log "public url ${PUBLIC_URL}"

if ! ${SUDO} test -d "${PREVIEW_NGINX_DIR}"; then
    die "${PREVIEW_NGINX_DIR} does not exist. Run deploy/preview/install-nginx-include.sh once on this host as a human with sudo."
fi
if ! ${SUDO} test -w "${PREVIEW_NGINX_DIR}"; then
    die "${PREVIEW_NGINX_DIR} is not writable through sudo. Run deploy/preview/install-nginx-include.sh once on this host as a human with sudo."
fi
[ -f "${PREVIEW_DOCKERFILE}" ] || die "Dockerfile ${PREVIEW_DOCKERFILE} not found. Set PREVIEW_BUILD_CONTEXT to a checkout's DockerBuild directory."

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

# preflight
# Resource guards for the full path only. The fast path reuses a container
# that is already running and asks the host for nothing new, so none of this
# applies to it. Runs after the previous container and image for this pull
# request are gone, so the space they held counts as free and the port they
# held reads as free.
preflight() {
    local others count avail_gb free_mb

    # 1. how many other previews are on the box. A redeploy of a pull request
    #    that already has a container is not a new preview, so this PR is
    #    excluded from the count.
    others="$(list_preview_prs | sort -n -u | grep -v "^${PR}$" | tr '\n' ' ' | sed 's/  */ /g; s/ $//' || true)"
    count=0
    if [ -n "${others}" ]; then
        # shellcheck disable=SC2086
        set -- ${others}
        count="$#"
    fi
    if [ "${count}" -ge "${PREVIEW_MAX_ACTIVE}" ]; then
        refuse "the host already has ${count} other preview(s) deployed, for PR(s) ${others}, and PREVIEW_MAX_ACTIVE is ${PREVIEW_MAX_ACTIVE}. Comment /undeploy on one of them, then deploy this one again."
    fi
    log "preflight: ${count} other preview(s) on the host, limit ${PREVIEW_MAX_ACTIVE}"

    # 2. free space where the image is going to land
    # Both forms can fail on a host that lays its filesystems out differently,
    # and an unreadable df is a reason to skip the check, not to refuse. The
    # floor is the larger of PREVIEW_MIN_FREE_DISK_GB and
    # PREVIEW_MIN_FREE_DISK_PCT percent of the volume, so the same default is
    # sane on a small host and on the 485 GB root of cicd.rtx.ai.
    local df_line size_gb avail_gb pct_floor_gb floor_gb
    df_line="$(df -BG --output=size,avail /var/lib/docker 2>/dev/null \
        || df -BG --output=size,avail / 2>/dev/null || true)"
    df_line="$(printf '%s' "${df_line}" | tail -n 1)"
    size_gb="$(printf '%s' "${df_line}" | awk '{print $1}' | tr -dc '0-9')"
    avail_gb="$(printf '%s' "${df_line}" | awk '{print $2}' | tr -dc '0-9')"
    case "${avail_gb}:${size_gb}" in
        *[!0-9:]*|:*|*:)
            log "WARNING: could not read the free disk space, skipping that check"
            ;;
        *)
            pct_floor_gb=$(( size_gb * PREVIEW_MIN_FREE_DISK_PCT / 100 ))
            floor_gb="${PREVIEW_MIN_FREE_DISK_GB}"
            [ "${pct_floor_gb}" -gt "${floor_gb}" ] && floor_gb="${pct_floor_gb}"
            if [ "${avail_gb}" -lt "${floor_gb}" ]; then
                refuse "the preview host has ${avail_gb} GB free of ${size_gb} GB where docker stores its images and the floor is ${floor_gb} GB (the larger of PREVIEW_MIN_FREE_DISK_GB=${PREVIEW_MIN_FREE_DISK_GB} and PREVIEW_MIN_FREE_DISK_PCT=${PREVIEW_MIN_FREE_DISK_PCT}% of the volume). One preview image is about 4 GB. Tear down an old preview or run deploy/preview/gc.sh on cicd.rtx.ai."
            fi
            log "preflight: ${avail_gb} GB free of ${size_gb} GB on the docker root, floor ${floor_gb} GB"
            ;;
    esac

    # 3. available memory. The available column, not the free one: page cache
    #    is reclaimable and would otherwise read as used.
    free_mb="$(free -m 2>/dev/null | awk '/^Mem:/{print $7}' || true)"
    case "${free_mb}" in
        ''|*[!0-9]*)
            log "WARNING: could not read the available memory, skipping that check"
            ;;
        *)
            if [ "${free_mb}" -lt "${PREVIEW_MIN_FREE_RAM_MB}" ]; then
                refuse "the preview host has ${free_mb} MB of memory available and PREVIEW_MIN_FREE_RAM_MB is ${PREVIEW_MIN_FREE_RAM_MB}. A preview peaks at about 1900 MB. Tear down an old preview or wait for the running queries to finish."
            fi
            log "preflight: ${free_mb} MB memory available, minimum ${PREVIEW_MIN_FREE_RAM_MB} MB"
            ;;
    esac

    # 4. the port. The container for this pull request is gone by now, so
    #    anything still listening belongs to something else and docker run
    #    would fail several minutes from now, after the image build.
    # The connect attempt runs in a subshell for two reasons: a failed exec
    # redirection can take a non-interactive shell down with it, and a refused
    # connection is the expected case here. The close is chained with && and
    # not with a semicolon, because a semicolon would hand the successful
    # close's exit status to the if and every port would read as taken.
    if (exec 3<>"/dev/tcp/127.0.0.1/${PORT}" && exec 3<&-) 2>/dev/null; then
        refuse "something is already listening on 127.0.0.1:${PORT}, which is the port PR ${PR} needs. Find it with 'sudo ss -lptn sport = :${PORT}' on cicd.rtx.ai."
    fi
    log "preflight: 127.0.0.1:${PORT} is free"
}

# ---------------------------------------------------------------------------
# 2. Decide between a fast redeploy and a full rebuild
# ---------------------------------------------------------------------------

MODE="full"
REASON=""
BUILD_SHA=""

# fall_back <reason> <refusal>
# In auto mode every reason to fall back is a plain reason to rebuild, never a
# failure, because a full rebuild is always a correct answer. Under
# --fast-only there is nothing to fall back to, so the same condition is a
# refusal and refuse() takes the script down with the reason attached, which
# is what puts it in the pull request comment.
fall_back() {
    REASON="${1}"
    if [ "${FAST_ONLY}" = "yes" ]; then
        refuse "${2}"
    fi
    return 0
}

# Sets MODE and REASON.
decide_mode() {
    local changed=""

    if [ "${FORCE}" = "yes" ]; then
        REASON="--force was given"
        return 0
    fi
    if ! is_sha "${SHA}"; then
        fall_back "no commit sha was passed" \
            "no commit sha was passed, a restart has nothing to check out"
        return 0
    fi
    if ! container_running "${CONTAINER}"; then
        fall_back "no running container ${CONTAINER}" \
            "no preview is running for this PR, comment /deploy first"
        return 0
    fi

    # The gate compares against the commit the image was built from, not the
    # commit currently checked out. pip install runs at image build time only,
    # so the installed packages are frozen at the sha the image was built from,
    # and a prior fast redeploy has already moved the working tree off it. That
    # sha is recorded in the arax.preview.sha label at docker run, and because a
    # label cannot change on a running container it still names the build commit
    # after any number of fast redeploys.
    BUILD_SHA="$(preview_label "${PR}" "arax.preview.sha" | tr -d '[:space:]')" || BUILD_SHA=""
    if ! is_sha "${BUILD_SHA}"; then
        fall_back "could not read the image build sha for ${CONTAINER}" \
            "could not tell what the running image was built from, comment /deploy for a full rebuild"
        return 0
    fi
    log "${CONTAINER} image was built from ${BUILD_SHA}"

    if ! container_git git fetch origin; then
        fall_back "git fetch origin failed inside ${CONTAINER}" \
            "git fetch origin failed inside ${CONTAINER}, comment /deploy for a full rebuild"
        return 0
    fi
    # Both the target and the build commit have to resolve in the container
    # clone: the target because the fast path checks it out, and the build sha
    # because the gate diffs from it. A branch force pushed away can take either
    # one off origin.
    if ! container_git "git cat-file -e ${SHA}^{commit}"; then
        fall_back "target sha not on origin" \
            "commit ${SHA} is not on origin yet, push the branch and comment /redeploy again"
        return 0
    fi
    if ! container_git "git cat-file -e ${BUILD_SHA}^{commit}"; then
        fall_back "the commit the image was built from is no longer on origin" \
            "the image build commit is gone from origin, comment /deploy for a full rebuild"
        return 0
    fi

    if ! changed="$(container_git "git diff --name-only ${BUILD_SHA} ${SHA} -- ${FAST_GATE_PATHS}" | tr '\n' ' ')"; then
        fall_back "git diff failed inside ${CONTAINER}" \
            "git diff failed inside ${CONTAINER}, comment /deploy for a full rebuild"
        return 0
    fi
    # Collapse the file list onto one line so it can be a GITHUB_OUTPUT value.
    changed="$(printf '%s' "${changed}" | sed 's/  */ /g; s/ $//')"
    if [ -n "${changed}" ]; then
        fall_back "image inputs changed: ${changed}" \
            "the image was built with a different ${changed}, its installed packages and Dockerfile are frozen at build time and a restart cannot change them, comment /deploy for a full rebuild"
        return 0
    fi

    MODE="fast"
    REASON="the image already has the build inputs of ${SHA}"
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

    # 3. Remove anything left over from a previous deploy of this PR, then
    #    check that the host can afford what comes next. Removal comes first
    #    so the roughly 4 GB the old image held counts as free space.
    log "step 3/10 clearing the previous deploy of PR ${PR} and checking the host"
    ${DOCKER} rm -f "${CONTAINER}" >/dev/null 2>&1 || log "no previous container ${CONTAINER}"
    ${DOCKER} rmi -f "${IMAGE}" >/dev/null 2>&1 || log "no previous image ${IMAGE}"
    preflight

    # 4. Build the image
    #    CICD-Dockerfile git clones RTXteam/RTX inside the image and checks out
    #    BUILD_BRANCH, so the branch has to exist on the upstream repository.
    #    Fork pull requests cannot work with this build and are refused by the
    #    workflow.
    log "step 4/10 building ${IMAGE} from branch ${BRANCH} (this takes a while)"
    # Logged here, on the full path only, right before the build. On a restart
    # there is no build, so the deploy log never mentions a build context.
    log "build context ${PREVIEW_BUILD_CONTEXT}, dockerfile ${PREVIEW_DOCKERFILE}"
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
    log "step 5/10 starting ${CONTAINER} on 127.0.0.1:${PORT}, capped at ${PREVIEW_MEMORY_LIMIT} memory and ${PREVIEW_CPU_LIMIT} cpus"
    ${DOCKER} run -d -i -t \
        --name "${CONTAINER}" \
        --memory "${PREVIEW_MEMORY_LIMIT}" \
        --cpus "${PREVIEW_CPU_LIMIT}" \
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
