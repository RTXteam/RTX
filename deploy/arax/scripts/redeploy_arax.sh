#!/usr/bin/env bash
# redeploy_arax.sh
# - Author: Adilbek Bazarkulov <bazarkua@oregonstate.edu>
#
# Safe redeploy helper for ARAX endpoints running inside a docker container.
# - Supports redeploying a specific endpoint (e.g. -test) or all endpoints (-all)
# - For each endpoint:
#   - git stash (preserve local changes)
#   - git pull --ff-only (safe, no merge commits)
#   - git stash pop (re-apply local changes)
#   - restart the corresponding service
#   - sleep and run basic status/HTTP checks
#
# This script is intended to be run on the HOST, not inside the container.
#
# Design goals:
# - No irreversible operations (no deletes, no forced resets)
# - Clear, quantitative output (timestamps, exit codes, http codes)
# - Explicit confirmation before doing anything

set -Eeuo pipefail

SCRIPT_NAME="$(basename "$0")"
DEFAULT_CONTAINER="rtx2"
DEFAULT_SLEEP_SECONDS="3"
DEFAULT_BRANCH="master"
DEFAULT_LOCK_FILE="/tmp/redeploy_arax.lock"
DEFAULT_HTTP_RETRIES="5"
DEFAULT_HTTP_RETRY_SLEEP_SECONDS="2"
DEFAULT_HTTP_CONNECT_TIMEOUT="2"
DEFAULT_HTTP_MAX_TIME="10"

CONTAINER_NAME="$DEFAULT_CONTAINER"
SLEEP_SECONDS="$DEFAULT_SLEEP_SECONDS"
TARGET_BRANCH="$DEFAULT_BRANCH"
LOCK_FILE="$DEFAULT_LOCK_FILE"
HTTP_RETRIES="$DEFAULT_HTTP_RETRIES"
HTTP_RETRY_SLEEP_SECONDS="$DEFAULT_HTTP_RETRY_SLEEP_SECONDS"
HTTP_CONNECT_TIMEOUT="$DEFAULT_HTTP_CONNECT_TIMEOUT"
HTTP_MAX_TIME="$DEFAULT_HTTP_MAX_TIME"
DO_DRY_RUN="0"
ASSUME_YES="0"

declare -a SELECTED_ENDPOINTS=()

print_help() {
  cat <<'HELP'
Usage:
  redeploy_arax.sh [options] (-all | one-or-more endpoint flags)

Endpoint flags:
  -production    Redeploy production (/), service RTX_OpenAPI_production
  -test          Redeploy /test, service RTX_OpenAPI_test
  -beta          Redeploy /beta, service RTX_OpenAPI_beta
  -devED         Redeploy /devED, service RTX_OpenAPI_devED
  -devLM         Redeploy /devLM, service RTX_OpenAPI_devLM
  -shepherd      Redeploy /shepherd, service RTX_OpenAPI_shepherd
  -complete      Redeploy RTX_Complete (/rtxcomplete/), service RTX_Complete
  -all           Redeploy all of the above, in a safe order

Options:
  -container NAME    Docker container name (default: rtx2)
  -sleep SECONDS     Sleep time after restarting each endpoint (default: 3)
  -branch NAME       Git branch to checkout before pull (default: master)
  -lock-file PATH    Lock file used for concurrency control (default: /tmp/redeploy_arax.lock)
  -http-retries N    HTTP check retries after restart (default: 5)
  -http-retry-sleep  Seconds to sleep between HTTP retries (default: 2)
  -http-timeout      curl max-time seconds for HTTP checks (default: 10)
  -http-connect-timeout curl connect-timeout seconds for HTTP checks (default: 2)
  -dry-run           Print what would happen, do not change anything
  -yes               Skip confirmation prompt (use with caution)
  -help              Show this help

What it does for each endpoint:
  1) Adds git safe.directory for the repo path (avoids "dubious ownership" errors)
  2) In the endpoint repo directory:
     - git stash push -u (only if there are local changes)
     - git checkout <branch> (default: master)
     - git pull --ff-only
     - git stash pop (only if a stash was created)
  3) Restarts the service for that endpoint
  4) Sleeps for the configured duration
  5) Checks "service status" inside the container
  6) Checks HTTP status from the host via http://localhost (nginx -> apache -> service)

Safety rules:
  - Uses git pull --ff-only (won't create merge commits)
  - Does not run git reset/clean
  - If git stash pop reports conflicts, the script stops for that endpoint and exits non-zero
  - Uses a lock file (flock) so two redeploys cannot run at the same time

Examples:
  ./redeploy_arax.sh -test
  ./redeploy_arax.sh -beta -sleep 5
  ./redeploy_arax.sh -all -branch master
  ./redeploy_arax.sh -all -branch issue2521
  ./redeploy_arax.sh -all -container rtx2
  ./redeploy_arax.sh -production -dry-run
HELP
}

ts() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

die() {
  echo "ERROR: $*" 1>&2
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Missing required command: $1"
}

docker_exec_root() {
  local cmd="$1"
  docker exec "$CONTAINER_NAME" bash -lc "$cmd"
}

docker_exec_git() {
  # Run git operations as the repository owner user ("rt") to avoid permission weirdness.
  # If rt doesn't exist, docker will fail; then we fallback to root.
  local cmd="$1"
  if docker exec -u rt "$CONTAINER_NAME" bash -lc "true" >/dev/null 2>&1; then
    docker exec -u rt "$CONTAINER_NAME" bash -lc "$cmd"
  else
    docker exec "$CONTAINER_NAME" bash -lc "$cmd"
  fi
}

container_is_running() {
  docker ps --filter "name=^${CONTAINER_NAME}$" --format '{{.Names}}' | grep -qx "$CONTAINER_NAME"
}

add_endpoint() {
  SELECTED_ENDPOINTS+=("$1")
}

parse_args() {
  if [[ $# -eq 0 ]]; then
    print_help
    exit 1
  fi

  while [[ $# -gt 0 ]]; do
    case "$1" in
      -help|--help|-h)
        print_help
        exit 0
        ;;
      -container)
        shift
        [[ $# -gt 0 ]] || die "-container requires a value"
        CONTAINER_NAME="$1"
        shift
        ;;
      -sleep)
        shift
        [[ $# -gt 0 ]] || die "-sleep requires a value"
        SLEEP_SECONDS="$1"
        shift
        ;;
      -branch)
        shift
        [[ $# -gt 0 ]] || die "-branch requires a value"
        TARGET_BRANCH="$1"
        shift
        ;;
      -lock-file)
        shift
        [[ $# -gt 0 ]] || die "-lock-file requires a value"
        LOCK_FILE="$1"
        shift
        ;;
      -http-retries)
        shift
        [[ $# -gt 0 ]] || die "-http-retries requires a value"
        HTTP_RETRIES="$1"
        shift
        ;;
      -http-retry-sleep)
        shift
        [[ $# -gt 0 ]] || die "-http-retry-sleep requires a value"
        HTTP_RETRY_SLEEP_SECONDS="$1"
        shift
        ;;
      -http-timeout)
        shift
        [[ $# -gt 0 ]] || die "-http-timeout requires a value"
        HTTP_MAX_TIME="$1"
        shift
        ;;
      -http-connect-timeout)
        shift
        [[ $# -gt 0 ]] || die "-http-connect-timeout requires a value"
        HTTP_CONNECT_TIMEOUT="$1"
        shift
        ;;
      -dry-run)
        DO_DRY_RUN="1"
        shift
        ;;
      -yes)
        ASSUME_YES="1"
        shift
        ;;
      -all)
        add_endpoint "production"
        add_endpoint "test"
        add_endpoint "beta"
        add_endpoint "devED"
        add_endpoint "devLM"
        add_endpoint "shepherd"
        add_endpoint "complete"
        shift
        ;;
      -production) add_endpoint "production"; shift ;;
      -test)       add_endpoint "test"; shift ;;
      -beta)       add_endpoint "beta"; shift ;;
      -devED)      add_endpoint "devED"; shift ;;
      -devLM)      add_endpoint "devLM"; shift ;;
      -shepherd)   add_endpoint "shepherd"; shift ;;
      -complete)   add_endpoint "complete"; shift ;;
      *)
        die "Unknown argument: $1 (use -help)"
        ;;
    esac
  done

  if [[ ${#SELECTED_ENDPOINTS[@]} -eq 0 ]]; then
    die "No endpoints selected. Use -all or one-or-more endpoint flags. Use -help."
  fi

  # Dedupe endpoints (deterministic order: keep first occurrence)
  if [[ ${#SELECTED_ENDPOINTS[@]} -gt 1 ]]; then
    declare -A seen=()
    declare -a deduped=()
    for ep in "${SELECTED_ENDPOINTS[@]}"; do
      if [[ -z "${seen[$ep]+x}" ]]; then
        seen["$ep"]=1
        deduped+=("$ep")
      fi
    done
    SELECTED_ENDPOINTS=("${deduped[@]}")
  fi

  # Basic validation of sleep
  if ! [[ "$SLEEP_SECONDS" =~ ^[0-9]+$ ]]; then
    die "-sleep must be an integer number of seconds (got: $SLEEP_SECONDS)"
  fi
  if ! [[ "$HTTP_RETRIES" =~ ^[0-9]+$ ]]; then
    die "-http-retries must be an integer (got: $HTTP_RETRIES)"
  fi
  if ! [[ "$HTTP_RETRY_SLEEP_SECONDS" =~ ^[0-9]+$ ]]; then
    die "-http-retry-sleep must be an integer (got: $HTTP_RETRY_SLEEP_SECONDS)"
  fi
  if ! [[ "$HTTP_CONNECT_TIMEOUT" =~ ^[0-9]+$ ]]; then
    die "-http-connect-timeout must be an integer (got: $HTTP_CONNECT_TIMEOUT)"
  fi
  if ! [[ "$HTTP_MAX_TIME" =~ ^[0-9]+$ ]]; then
    die "-http-timeout must be an integer (got: $HTTP_MAX_TIME)"
  fi
}

endpoint_repo_dir() {
  local ep="$1"
  case "$ep" in
    production) echo "/mnt/data/orangeboard/production/RTX" ;;
    test)       echo "/mnt/data/orangeboard/test/RTX" ;;
    beta)       echo "/mnt/data/orangeboard/beta/RTX" ;;
    devED)      echo "/mnt/data/orangeboard/devED/RTX" ;;
    devLM)      echo "/mnt/data/orangeboard/devLM/RTX" ;;
    shepherd)   echo "/mnt/data/orangeboard/shepherd/RTX" ;;
    complete)   echo "/mnt/data/orangeboard/production/RTX" ;; # RTX_Complete lives under production repo
    *) die "Unknown endpoint for repo_dir: $ep" ;;
  esac
}

endpoint_service_name() {
  local ep="$1"
  case "$ep" in
    production) echo "RTX_OpenAPI_production" ;;
    test)       echo "RTX_OpenAPI_test" ;;
    beta)       echo "RTX_OpenAPI_beta" ;;
    devED)      echo "RTX_OpenAPI_devED" ;;
    devLM)      echo "RTX_OpenAPI_devLM" ;;
    shepherd)   echo "RTX_OpenAPI_shepherd" ;;
    complete)   echo "RTX_Complete" ;;
    *) die "Unknown endpoint for service_name: $ep" ;;
  esac
}

endpoint_http_check_path() {
  local ep="$1"
  case "$ep" in
    production) echo "/api/arax/v1.4/ui/" ;;
    test)       echo "/test/api/arax/v1.4/ui/" ;;
    beta)       echo "/beta/api/arax/v1.4/ui/" ;;
    devED)      echo "/devED/api/arax/v1.4/ui/" ;;
    devLM)      echo "/devLM/api/arax/v1.4/ui/" ;;
    shepherd)   echo "/shepherd/api/arax/v1.4/ui/" ;;
    complete)   echo "/rtxcomplete/" ;;
    *) die "Unknown endpoint for http_check_path: $ep" ;;
  esac
}

endpoint_http_secondary_check_path() {
  # A lightweight API endpoint that should exist if the service is really up.
  # Using /entity is a simple GET and has been used by uptime monitors.
  local ep="$1"
  case "$ep" in
    production) echo "/api/arax/v1.4/entity?q=ALCAM" ;;
    test)       echo "/test/api/arax/v1.4/entity?q=ALCAM" ;;
    beta)       echo "/beta/api/arax/v1.4/entity?q=ALCAM" ;;
    devED)      echo "/devED/api/arax/v1.4/entity?q=ALCAM" ;;
    devLM)      echo "/devLM/api/arax/v1.4/entity?q=ALCAM" ;;
    shepherd)   echo "/shepherd/api/arax/v1.4/entity?q=ALCAM" ;;
    complete)   echo "/rtxcomplete/" ;;
    *) die "Unknown endpoint for secondary http path: $ep" ;;
  esac
}

curl_code_and_time() {
  # Outputs: "<http_code> <time_total>"
  # - http_code is 000 on network/connect errors
  # - time_total is 0 on errors
  #
  # We intentionally do NOT use curl --fail here because we want the real HTTP code
  # even for 4xx/5xx. We decide success based on the code.
  local url="$1"
  local out rc
  set +e
  out="$(curl -sS --connect-timeout "$HTTP_CONNECT_TIMEOUT" --max-time "$HTTP_MAX_TIME" -o /dev/null -w '%{http_code} %{time_total}' "$url" 2>/dev/null)"
  rc="$?"
  set -e
  if [[ "$rc" -ne 0 || -z "$out" ]]; then
    echo "000 0"
    return 0
  fi
  echo "$out"
}

confirm_plan() {
  echo "Plan summary (no changes yet):"
  echo "  time_utc: $(ts)"
  echo "  container: $CONTAINER_NAME"
  echo "  sleep_seconds: $SLEEP_SECONDS"
  echo "  git_branch: $TARGET_BRANCH"
  echo "  lock_file: $LOCK_FILE"
  echo "  http_retries: $HTTP_RETRIES"
  echo "  http_retry_sleep_seconds: $HTTP_RETRY_SLEEP_SECONDS"
  echo "  http_connect_timeout_seconds: $HTTP_CONNECT_TIMEOUT"
  echo "  http_timeout_seconds: $HTTP_MAX_TIME"
  echo "  endpoints:"
  for ep in "${SELECTED_ENDPOINTS[@]}"; do
    echo "    - endpoint: $ep"
    echo "      repo_dir: $(endpoint_repo_dir "$ep")"
    echo "      service:  $(endpoint_service_name "$ep")"
    echo "      http_check: http://localhost$(endpoint_http_check_path "$ep")"
    echo "      http_check_2: http://localhost$(endpoint_http_secondary_check_path "$ep")"
  done
  echo
  echo "For each endpoint the script will:"
  echo "  - configure git safe.directory for the repo (per-command, not global)"
  echo "  - git stash push -u (only if there are local changes)"
  echo "  - git checkout $TARGET_BRANCH"
  echo "  - git pull --ff-only"
  echo "  - git stash pop (only if a stash was created)"
  echo "  - restart the service"
  echo "  - sleep, then run service status and an HTTP status check"
  echo

  if [[ "$DO_DRY_RUN" == "1" ]]; then
    echo "Dry-run selected: no changes will be made."
    return 0
  fi

  if [[ "$ASSUME_YES" == "1" ]]; then
    echo "Auto-confirm selected (-yes). Proceeding without prompt."
    return 0
  fi

  echo "Type 'yes' to proceed, anything else to cancel:"
  read -r answer
  if [[ "$answer" != "yes" ]]; then
    die "Cancelled by user."
  fi
}

git_safe_directory() {
  local repo="$1"
  # Intentionally no-op: we avoid mutating global git config.
  # We pass -c safe.directory=<repo> on each git command.
  :
}

git_has_local_changes() {
  local repo="$1"
  docker_exec_git "cd '$repo' && test -n \"\$(git -c safe.directory='$repo' status --porcelain)\""
}

git_branch_and_commit() {
  local repo="$1"
  docker_exec_git "cd '$repo' && printf '%s %s\n' \"\$(git -c safe.directory='$repo' rev-parse --abbrev-ref HEAD)\" \"\$(git -c safe.directory='$repo' rev-parse --short HEAD)\""
}

git_checkout_branch() {
  local repo="$1"
  local branch="$2"
  # Ensure branch exists locally or as a remote tracking branch
  # This does not create merges; it just ensures the branch is present.
  docker_exec_git "cd '$repo' && git -c safe.directory='$repo' show-ref --verify --quiet refs/heads/'$branch' || git -c safe.directory='$repo' show-ref --verify --quiet refs/remotes/origin/'$branch' || exit 10"
  docker_exec_git "cd '$repo' && git -c safe.directory='$repo' checkout '$branch'"
}

redeploy_endpoint() {
  local ep="$1"
  local repo
  local service
  local http_path
  local start_ts end_ts dur_s
  local before after
  local stashed="0"
  local pull_rc="0"
  local pop_rc="0"
  local checkout_rc="0"

  repo="$(endpoint_repo_dir "$ep")"
  service="$(endpoint_service_name "$ep")"
  http_path="$(endpoint_http_check_path "$ep")"
  local http_path_2
  http_path_2="$(endpoint_http_secondary_check_path "$ep")"

  echo "--------------------------------------------------------------------------------"
  echo "endpoint=$ep time_utc=$(ts)"
  echo "repo_dir=$repo service=$service"

  # Verify repo exists
  if ! docker_exec_root "test -d '$repo/.git'"; then
    die "Repo missing or not a git repo: $repo"
  fi

  git_safe_directory "$repo"

  before="$(git_branch_and_commit "$repo" || true)"
  echo "git_before=$before"

  if [[ "$DO_DRY_RUN" == "1" ]]; then
    echo "dry_run=1 action=skip"
    return 0
  fi

  start_ts="$(date +%s)"

  if git_has_local_changes "$repo"; then
    echo "git_local_changes=1 action=git_stash_push include_untracked=1"
    docker_exec_git "cd '$repo' && git -c safe.directory='$repo' stash push -u -m '$SCRIPT_NAME $(ts) endpoint=$ep' >/dev/null"
    stashed="1"
  else
    echo "git_local_changes=0"
  fi

  echo "action=git_checkout branch=$TARGET_BRANCH"
  set +e
  git_checkout_branch "$repo" "$TARGET_BRANCH"
  checkout_rc="$?"
  set -e
  if [[ "$checkout_rc" -ne 0 ]]; then
    echo "git_checkout_rc=$checkout_rc"
    if [[ "$checkout_rc" -eq 10 ]]; then
      echo "ERROR: branch '$TARGET_BRANCH' not found in $repo (neither local nor origin/$TARGET_BRANCH)"
    fi
    if [[ "$stashed" == "1" ]]; then
      echo "action=git_stash_pop_after_checkout_failure"
      docker_exec_git "cd '$repo' && git -c safe.directory='$repo' stash pop" || true
    fi
    die "git checkout failed for endpoint=$ep. No pull/restart performed."
  fi

  echo "action=git_pull_ff_only"
  set +e
  docker_exec_git "cd '$repo' && git -c safe.directory='$repo' pull --ff-only"
  pull_rc="$?"
  set -e
  if [[ "$pull_rc" -ne 0 ]]; then
    echo "git_pull_rc=$pull_rc"
    if [[ "$stashed" == "1" ]]; then
      echo "action=git_stash_pop_after_pull_failure"
      docker_exec_git "cd '$repo' && git -c safe.directory='$repo' stash pop" || true
    fi
    die "git pull failed for endpoint=$ep (rc=$pull_rc). No service restart performed."
  fi

  if [[ "$stashed" == "1" ]]; then
    echo "action=git_stash_pop"
    set +e
    docker_exec_git "cd '$repo' && git -c safe.directory='$repo' stash pop"
    pop_rc="$?"
    set -e
    if [[ "$pop_rc" -ne 0 ]]; then
      echo "git_stash_pop_rc=$pop_rc"
      echo "WARNING: git stash pop had conflicts or failed. The stash may still exist."
      echo "WARNING: Resolve conflicts in $repo inside container, then restart service manually."
      die "Stopping to avoid a bad deploy. endpoint=$ep"
    fi
  fi

  after="$(git_branch_and_commit "$repo" || true)"
  echo "git_after=$after"

  echo "action=service_restart service=$service"
  docker_exec_root "service '$service' restart"

  echo "sleep_seconds=$SLEEP_SECONDS"
  sleep "$SLEEP_SECONDS"

  echo "action=service_status service=$service"
  docker_exec_root "service '$service' status" 2>&1 | tail -15

  # HTTP checks (host-side) through nginx/apache, time-bounded, retries.
  # We use two checks: UI page + a simple API call. Both should succeed.
  echo "action=http_check_start retries=$HTTP_RETRIES connect_timeout=$HTTP_CONNECT_TIMEOUT timeout=$HTTP_MAX_TIME"
  local attempt=1
  local ok1="0" ok2="0"
  local code1="000" t1="0"
  local code2="000" t2="0"
  while [[ "$attempt" -le "$HTTP_RETRIES" ]]; do
    ok1="0"
    ok2="0"
    read -r code1 t1 <<<"$(curl_code_and_time "http://localhost${http_path}")"
    read -r code2 t2 <<<"$(curl_code_and_time "http://localhost${http_path_2}")"
    if [[ "$code1" =~ ^2[0-9][0-9]$ ]]; then ok1="1"; fi
    if [[ "$code2" =~ ^2[0-9][0-9]$ ]]; then ok2="1"; fi
    echo "http_attempt=$attempt ui_code=$code1 ui_time_total_seconds=$t1 api_code=$code2 api_time_total_seconds=$t2"
    if [[ "$ok1" == "1" && "$ok2" == "1" ]]; then
      break
    fi
    attempt="$((attempt + 1))"
    sleep "$HTTP_RETRY_SLEEP_SECONDS"
  done
  if [[ "$ok1" != "1" || "$ok2" != "1" ]]; then
    die "HTTP health checks failed for endpoint=$ep (ui_code=$code1 api_code=$code2). Service was restarted but may not be healthy."
  fi

  end_ts="$(date +%s)"
  dur_s="$((end_ts - start_ts))"
  echo "endpoint=$ep done=1 duration_seconds=$dur_s time_utc=$(ts)"
}

main() {
  parse_args "$@"

  require_cmd docker
  require_cmd curl
  require_cmd flock

  if ! container_is_running; then
    die "Container '$CONTAINER_NAME' is not running. Start it first: docker start $CONTAINER_NAME"
  fi

  # Confirm apache is up (it is required for routing)
  if ! docker_exec_root "service apache2 status >/dev/null 2>&1"; then
    echo "WARNING: apache2 not running inside container. Some endpoints may not route until apache2 is started."
  fi

  # Concurrency lock (host-side)
  exec 9>"$LOCK_FILE"
  if ! flock -n 9; then
    die "Another redeploy is already running (lock file: $LOCK_FILE)."
  fi

  confirm_plan

  for ep in "${SELECTED_ENDPOINTS[@]}"; do
    redeploy_endpoint "$ep"
  done

  echo "--------------------------------------------------------------------------------"
  echo "Redeploy complete time_utc=$(ts)"
}

main "$@"


