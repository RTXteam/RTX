# ARAX preview environments

Every open pull request can get its own live ARAX instance on `cicd.rtx.ai`, built from that
branch and reachable over HTTPS at a URL derived from the pull request number. The whole thing
is a push button flow: comment `/deploy` on a pull request, wait for the build, and click the
link that the bot posts back. This implements
[issue #2846](https://github.com/RTXteam/RTX/issues/2846).

`DockerBuild/test-instance-scripts/` is the older manual way of standing up a test instance on a
fresh EC2 box and stays available for the cases this workflow does not cover.

## URL and port scheme

| thing | value for PR 2853 | how it is derived |
| --- | --- | --- |
| public URL | `https://cicd.rtx.ai/2853/` | `PREVIEW_PUBLIC_BASE_URL` + `/` + `PREVIEW_PATH_PREFIX` + PR + `/` |
| host port | `127.0.0.1:12853` | `PREVIEW_PORT_BASE` + PR |
| container | `rtx_pr_2853` | `rtx_pr_` + PR |
| image | `rtx:pr-2853` | `rtx:pr-` + PR |
| nginx snippet | `/etc/nginx/arax-preview.d/2853.conf` | `PREVIEW_NGINX_DIR` + `/` + `PREVIEW_PATH_PREFIX` + PR + `.conf` |

The host port is bound to loopback only, so nothing is reachable from outside the box except
through nginx on 443. `https://cicd.rtx.ai/2853` without the trailing slash redirects to
`https://cicd.rtx.ai/2853/`.

Setting `PREVIEW_PATH_PREFIX=pr-` moves the same preview to `https://cicd.rtx.ai/pr-2853/` and
renames the snippet to `pr-2853.conf`. The port and the container name do not change.

## How to deploy

Three commands, all comments on the pull request itself. Only comments from an OWNER, MEMBER or
COLLABORATOR are acted on, and the command has to be the first thing on the first line.

| command | what it does | how long |
| --- | --- | --- |
| `/deploy` | fresh rebuild. Builds the image from the current head of the branch and replaces the container, whatever was there before | about 6 minutes |
| `/redeploy` | restart with the latest code. Moves the container that is already running onto the new commit and restarts the services. Refuses with a reason when that cannot work | about a minute |
| `/undeploy` | removes the container, the image and the nginx snippet | seconds |

Add `--no-tests` to `/deploy` or `/redeploy` to skip the pytest suite, which otherwise runs after
every deploy. Nothing else is read off the line, and a leftover `--force` is accepted and ignored.

Previews are cleaned up on their own. Closing or merging the pull request tears the preview down,
and the nightly garbage collection removes previews older than `PREVIEW_TTL_DAYS`, so an
`/undeploy` is only needed to free a slot early.

The same thing is available from the Actions tab: pick **Preview Deploy**, **Run workflow**, fill
in `pr_number` and pick a `mode`, either **full rebuild** which is `/deploy` or **fast restart**
which is `/redeploy`. `run_tests` is ticked by default and `pytest_args` narrows the suite down.

On the host directly, `deploy.sh` also has an automatic mode that neither command uses:
`bash deploy/preview/deploy.sh 2853 my-branch <sha>` picks the restart itself when it can and
rebuilds when it cannot. `--force` rules the restart out and `--fast-only` rules the rebuild out,
which is exactly what `/deploy` and `/redeploy` pass. The two flags cannot be combined.

### The comments

A run posts a start notification as soon as it picks the command up, and then up to three
comments as it goes.

| comment | marker | what is in it | can it fail the job |
| --- | --- | --- | --- |
| **started** | `arax-preview-status` | which command is running, the branch and short commit, a link to the run and how long it should take | no |
| **ARAX preview** | `arax-preview-status` | deployed or restarted, the URL, the branch and short commit, which path ran with the reason, and the smoke test table | yes, through the deploy and smoke steps |
| **Preview pytest** | `arax-preview-pytest` | the container it ran in, one summary line of passed, failed and skipped counts, and an expander with the failing test names and the last 80 lines when something failed | no |
| **Preview live queries** | `arax-preview-queries` | the endpoint it posted to, then a table of the four example queries of the UI numbered Example 1 to Example 3 and Pathfinder, each with HTTP code, the seconds curl measured to two decimals, result count and knowledge graph size | no |

Every event posts a new comment so the thread reads in order, and the previous comment with the
same marker is collapsed as outdated so the thread does not fill up. The start notification
carries the status marker, so the finished status comment folds it away on its way in. The pytest
and live query comments are informational: they report what happened and never turn the job red,
because a preview that is up and answering is still useful when one test is broken.

A command that cannot be carried out gets a comment saying which limit was hit rather than a
generic failure. The reasons are a fork pull request, a closed pull request, no free preview slot,
not enough free disk, not enough free memory, the port already taken, and for `/redeploy` the
cases in **What /redeploy does** below: no preview running, the commit not pushed yet, or a change
to one of the files a restart cannot pick up.

The scripts always run from the workflow's own branch on master, never from the pull
request. The pull request head is checked out
into `pr-head/` and used only as the docker build context, so a pull request that changes
`DockerBuild/CICD-Dockerfile` is built with its own Dockerfile, exactly as `pytest.yml` does.
This also means a pull request opened before this tooling existed can be previewed.

GitHub only registers a workflow, and only fires `workflow_dispatch`, `issue_comment` and
`schedule`, from the default branch copy of the file. Until this workflow is merged to master
no GitHub trigger works at all, not even **Run workflow**, because the workflow does not appear
in the Actions tab. Test on the host with `deploy/preview/deploy.sh` until then, and verify the
triggers immediately after the merge.

## How it works

The flow below is the full rebuild that `/deploy` runs. `/redeploy` takes the shorter path
described in **What /redeploy does** below.

```
  PR comment "/deploy" or "/redeploy"  or  Actions "Run workflow"
              |
              v
  +------------------------------------+
  | GitHub Actions: Preview Deploy     |
  |  resolve PR -> branch, sha         |
  |  refuse fork PRs and closed PRs    |
  +------------------------------------+
              |  runs on the self-hosted runner
              v
  +------------------------------------------------------------+
  | cicd.rtx.ai                                                 |
  |                                                             |
  |  deploy.sh                                                  |
  |    preflight: previews on the box, disk, memory, port       |
  |    docker build -f DockerBuild/CICD-Dockerfile              |
  |      (the image git clones RTXteam/RTX and checks out       |
  |       BUILD_BRANCH, so the branch must live upstream)       |
  |         |                                                   |
  |         v                                                   |
  |    docker run -d -i -t --name rtx_pr_2853                   |
  |      --memory 2g --cpus 1.5                                 |
  |      -p 127.0.0.1:12853:80                                  |
  |      -v databases  -v config_secrets.json                   |
  |         |                                                   |
  |         +-> ARAX_database_manager.py   (db symlinks)        |
  |         +-> kp_info_cacher.py          (KP info cache)      |
  |         +-> service apache2 start                           |
  |         +-> service RTX_OpenAPI_production start            |
  |         +-> service RTX_Complete start                      |
  |         |                                                   |
  |         v                                                   |
  |    write /etc/nginx/arax-preview.d/2853.conf                |
  |    write /etc/nginx/arax-preview.d/_rtxcomplete.conf        |
  |    nginx -t && systemctl reload nginx                       |
  |         |                                                   |
  |         v                                                   |
  |    poll http://127.0.0.1:12853/api/arax/v1.4/status         |
  |    write /var/www/arax-preview/data/2853/state.json         |
  |      (written before the build too, so the card shows up    |
  |       on /previews/ while the image is still building)      |
  |    write /var/www/arax-preview/index.html                   |
  |                                                             |
  |  nginx :443  server_name cicd.rtx.ai                        |
  |    include /etc/nginx/arax-preview.d/*.conf;                |
  |      location /2853/ -> proxy_pass 127.0.0.1:12853/         |
  |                          (the trailing slash strips /2853)  |
  +------------------------------------------------------------+
              |
              v
     https://cicd.rtx.ai/2853/
```

Inside the container, apache serves the ARAX UI from the checked out repository and proxies
`/api/arax/v1.4` to the Flask service on port 5000. The UI asks for its API with a relative
path, so it does not care that nginx stripped a prefix in front of it.

## What `/redeploy` does

Rebuilding the image takes about six minutes, and most pushes to a pull request change nothing
that the image bakes in. `/redeploy` moves the container that is already running onto the new
commit instead, which takes roughly 15 to 30 seconds.

It needs all of this to hold, and says which one failed when it refuses:

- the container `rtx_pr_<PR>` for that pull request exists and is running. Otherwise there is
  nothing to restart and the answer is to comment `/deploy`
- a commit sha was passed, which the workflow always does
- that commit is on `origin` once the container has fetched. A commit that was never pushed
  cannot be checked out inside the container
- `git diff` between the commit checked out in the container and the target commit is empty for
  `requirements.txt`, `DockerBuild/` and `code/config_dbs.json`

Those three paths are the gate because a change to them cannot be picked up by a checkout inside
a container that is already running. The first two are baked into the image, and `config_dbs.json`
decides which database files the container was set up with. When the diff is not empty the
refusal names the files that changed, and the answer is `/deploy`.

A fast redeploy checks the repository clone inside the container out on the target commit as user
`rt` with a detached HEAD, reruns `ARAX_database_manager.py` and `kp_info_cacher.py`, and restarts
`RTX_OpenAPI_production` and `RTX_Complete`. Apache is left alone, because it serves the UI
straight from that working tree and picks up UI changes with no restart. The nginx snippet is
rewritten so its header names the new commit, and nginx is only reloaded when the routing itself
changed.

The commit a preview is running is read with `git rev-parse HEAD` inside the container, never from
the `arax.preview.sha` label. Docker labels cannot be changed on a running container, so that
label keeps naming the commit the image was built from.

A restart that fails its health check stops there rather than rebuilding behind your back, and
says to run `/deploy` instead. Run by hand with no flag, `deploy.sh` falls back to a full rebuild
in every one of these cases instead of refusing, and prints the reason it chose to.

## Resource guards

The box is an `m5a.large` with 2 vCPUs, 7.5 GB of memory and no swap, and it also runs the pytest
workflow. Every full deploy therefore has to get past a preflight before the image build starts,
and every container is capped once it runs.

| guard | default | why this number |
| --- | --- | --- |
| `PREVIEW_MEMORY_LIMIT` | `2g` | a preview idles at about 400 MB and was measured at 1889 MiB peak while answering queries. Never set this lower than `2g`, the kernel would kill the container in the middle of a query |
| `PREVIEW_CPU_LIMIT` | `1.5` | a pathfinder query saturates both vCPUs for about 90 seconds. Half a core stays for nginx and the runner |
| `PREVIEW_MAX_ACTIVE` | `3` | three previews at 2 GB each still leave room for the pytest workflow on a 7.5 GB box |
| `PREVIEW_MIN_FREE_DISK_GB` | `10` | absolute part of the disk floor, one preview image is about 3.94 GB |
| `PREVIEW_MIN_FREE_DISK_PCT` | `10` | percentage part of the disk floor, the larger of the two wins, about 48 GB on the 485 GB root of cicd.rtx.ai |
| `PREVIEW_MIN_FREE_RAM_MB` | `2048` | enough for the container that is about to start |

The preflight runs on the full rebuild path only, after the previous container and image for this
pull request are removed. A fast redeploy reuses a container that is already running and asks the
host for nothing new, so none of it applies there. The checks are, in order:

1. **How many other previews are on the box.** A redeploy of a pull request that already has a
   container is not a new preview and never counts against the cap.
2. **Free space** on the docker root, `/var/lib/docker`, falling back to `/`.
3. **Available memory**, the available column of `free -m` rather than the free one, because page
   cache is reclaimable.
4. **The port**, which must be free now that this pull request's old container is gone. Anything
   still listening belongs to something else, and `docker run` would only discover that several
   minutes later, after the build.

A refusal names the limit that was hit and what to do about it, and the pull request comment says
`❌ refused` with that reason instead of the generic failure text. Comment `/undeploy` on a
preview somebody is done with, or run `bash deploy/preview/gc.sh` on the host.

## Status page

`https://cicd.rtx.ai/previews/` is the front door of the whole thing. The bare root of
`cicd.rtx.ai` redirects there, which replaces the stock **Welcome to nginx** page. `/cicd.txt`
and `/.well-known/` are unaffected, because the redirect is an exact match on `/` only.

Everything the page needs is a static file under the document root. Nothing on this host answers
a request with code, and nothing should: the page is regenerated by the scripts, and the browser
reads the files that are already there.

The page reads top to bottom as an introduction followed by the live state of the box:

| section | what it is |
| --- | --- |
| title | the name, the host it runs on and the host spec |
| About | three sentences on what the service is, who it is for and what it promises |
| How it works | five lines on containers, databases, URLs, limits and lifetime |
| Commands | `/deploy`, `/redeploy` and `/undeploy`, with what each one costs |
| Flow | an inline SVG of the deploy, the redeploy and the teardown paths |
| Host | memory, disk, load and preview slots, the live sample line and the container table |
| Previews | one card per pull request |

### The Host section, and the 15 second sampler

The four tiles are memory available, free disk, one minute load average and how many of the
`PREVIEW_MAX_ACTIVE` preview slots are taken. The memory, disk and slot tiles turn red on exactly
the thresholds the preflight check refuses a deploy on, so a red tile means the next `/deploy`
gets turned away. Under the tiles is a row per `rtx_` container with what `docker stats` says it
is using. A number that cannot be read shows as **no data** rather than disappearing, so the
layout never moves.

Those numbers are refreshed without regenerating the page. `host-stats.sh` runs as a systemd
service, samples the host every 15 seconds and writes `${PREVIEW_WEB_ROOT}/host.json`, writing to
a temporary file in the same directory and renaming it into place so a browser can never read
half a sample. The page fetches that file every 15 seconds with a 10 second timeout, updates the
tiles and the container table from it, and keeps a line under the tiles that says how old the
sample is and ticks every second:

```
last sample 2026-08-25 01:08:42 UTC (7 s ago)
```

Past 60 seconds that line turns red and gains the word `stale`, and the tiles are dimmed, so a
sampler that died is visible on the page instead of silently showing yesterday's numbers. The
tile colours come from the thresholds carried in `host.json`, which are the same numbers the
preflight check uses. With JavaScript turned off the tiles still show the values they had when
the page was generated.

`host.json` has one sample in it:

```json
{
  "sampled_at": "2026-08-25T01:08:42Z",
  "sampled_epoch": 1787620122,
  "mem_total_mb": 7676,
  "mem_available_mb": 4795,
  "disk_size_gb": 485,
  "disk_avail_gb": 301,
  "load1": 0.42, "load5": 0.55, "load15": 0.61,
  "slots_used": 1,
  "slots_max": 3,
  "containers": [
    {"name": "rtx_pr_2853", "mem_usage": "512.4MiB", "mem_limit": "2GiB", "cpu_pct": "3.21%"}
  ],
  "thresholds": {"ram_min_mb": 2048, "disk_floor_gb": 48}
}
```

Every collector is best effort and a number that could not be read is written as `null`. The
sampler and the page generator call the same collectors in `lib.sh`, so the live tiles and the
generated page can never disagree about what free means. `host-stats.sh --once` writes a single
sample and exits, which is what the installer runs and what a test can call.

The service is `arax-preview-stats.service`, installed by `install-nginx-include.sh`:

```
[Unit]
Description=ARAX preview host sampler for the /previews/ status page
After=docker.service

[Service]
Type=simple
User=<the user who ran the installer>
ExecStart=/bin/bash <checkout>/deploy/preview/host-stats.sh
Restart=always
RestartSec=5
```

The loop shells out to `sudo docker` like every other script here, so the user it runs as needs
passwordless sudo, which the runner user on `cicd.rtx.ai` already has. Check it with
`systemctl status arax-preview-stats` and read its log with `journalctl -u arax-preview-stats`.

### The cards, and what a run looks like while it is running

A card is drawn for every preview container on the box and for every pull request that has a run
state file, which is what a deploy looks like in the minutes between the comment and the first
container. A card carries the pull request number linked to GitHub, the branch and short commit
linked to the commit, which comment started the run, when the container was created, whether it
is running, and a link to the preview. The dot next to the pull request number is live: the page
asks each preview for its `/api/arax/v1.4/status` when it loads and turns green or red.

Under that is one row per stage. The stages are the deploy itself, the smoke test, pytest and the
live queries, in the order they run:

| state | how it looks | when |
| --- | --- | --- |
| pending | grey dot | the stage has not started |
| running | a spinning ring and `pytest running since 01:12 UTC` | the script is in the middle of it |
| done | green check | it finished, with the numbers from its report under it |
| failed | red cross and the reason | it finished badly, or the run was abandoned |

The results parsed out of the report files sit under the stage they belong to, so a card answers
both "what is happening right now" and "did it work" without opening anything. The spinner is a
CSS animation with no image behind it.

Each script writes its own stage: `deploy.sh` marks the deploy running before the image build
starts, which is what puts the card on the page while there is still nothing to link to, and
marks it done or failed on the way out, naming the reason a refusal or a failed health check
gave. `smoke.sh`, `pytest_report.sh` and `query_smoke.sh` do the same around their own work. The
state lives in `${PREVIEW_WEB_ROOT}/data/<PR>/state.json` and is removed with the preview.

A run that is killed between running and its result would otherwise spin forever. Whenever the
page is generated, any stage still marked running after `PREVIEW_STATE_STALE_SECONDS`, two hours
by default, is written down as failed with the detail `abandoned`.

### The report files

Under the stages are expanders with whatever reports exist for that pull request, embedded at
generation time rather than fetched by the browser:

| file | written by | what it holds |
| --- | --- | --- |
| `state.json` | every script | the stage states the card is drawn from, not shown as an expander |
| `deploy-log.txt` | `deploy.sh` | the last 200 lines of the deploy, with every line that mentions a password, token, secret or authorization dropped |
| `build-log.txt` | `deploy.sh` | the last 400 lines of the docker build, same secrets filter. Only a full rebuild writes it, and a fast redeploy deletes the one the previous deploy left |
| `smoke.md` | `smoke.sh` | the smoke test table |
| `pytest.md` | `pytest_report.sh` | the pytest summary |
| `queries.md` | `query_smoke.sh` | the live query table |

Those files live in `${PREVIEW_WEB_ROOT}/data/<PR>/`, which is `/var/www/arax-preview/data/<PR>/`
by default, and they are removed with the preview. The full deploy logs live in
`${PREVIEW_LOG_DIR}`, `/var/log/arax-preview` by default, one file per deploy run named
`pr<PR>-<timestamp>.log`. Those outlive the preview on purpose, so a preview that is already gone
can still be looked at, and garbage collection deletes them after 30 days.

### How often it is rewritten

The page itself is rewritten at the start and the end of every deploy, at the start and the end
of every smoke test, pytest run and query run, on every teardown, by the nightly garbage
collection, and every 5 minutes by cron. The host numbers on it refresh every 15 seconds on their
own from `host.json`. The cron entry runs `status-refresh.sh`, which does nothing but rewrite the
page:

```
*/5 * * * * /bin/bash /path/to/RTX/deploy/preview/status-refresh.sh >/dev/null 2>&1
```

`install-nginx-include.sh` installs that entry in the crontab of the user who invoked it, and is
idempotent about it: a crontab that already mentions `status-refresh.sh` is left untouched, so
running the installer again never doubles the entry up. Writing the page is best effort
throughout and can never fail a deploy, a teardown or a cron run. The installer also creates the
document root, the log directory and the nginx snippet, writes the first `host.json` and the
empty state page, and installs the sampler service, so `/previews/` answers before the first
preview is ever deployed.

**Rerun the installer once after this lands.** It is the only thing that creates
`arax-preview-stats.service`, and it is idempotent: the nginx include, the snippet and the cron
entry are left exactly as they are, and the unit file is rewritten only when its content actually
changed.

```
sudo bash deploy/preview/install-nginx-include.sh
```

## One-time host setup

Run this once on `cicd.rtx.ai`, as a human with sudo:

```
sudo bash deploy/preview/install-nginx-include.sh
```

It creates `/etc/nginx/arax-preview.d/`, backs up `/etc/nginx/sites-enabled/default` into
`/var/backups/arax-preview/` (a backup inside `sites-enabled/` would itself be parsed as
configuration, Ubuntu's nginx.conf includes that directory with a bare glob), and adds
one line inside the certbot managed TLS server block for `cicd.rtx.ai`:

```
    include /etc/nginx/arax-preview.d/*.conf;
```

It also creates `/var/www/arax-preview/` and `/var/log/arax-preview/`, and writes
`/etc/nginx/arax-preview.d/_previews.conf`, which serves the status page and redirects the bare
root to it:

```
location = / { return 302 /previews/; }
location /previews/ {
    alias /var/www/arax-preview/;
    index index.html;
    default_type text/html;
}
```

Then it runs `nginx -t` and reloads. If the check fails the backup is restored and a snippet this
run wrote is removed again. If no matching server block is found nothing is written and the script
prints the manual instructions. Running it a second time detects the existing include line and
exits, after making sure the status page pieces are in place, and it only reloads nginx when it
had to write the snippet.

It also installs the host sampler behind the live tiles on the status page. It writes one sample
by hand so `host.json` exists right away, writes
`/etc/systemd/system/arax-preview-stats.service` if its content is not already exactly what it
should be, reloads systemd when it wrote it, and runs `systemctl enable --now
arax-preview-stats.service`. The service runs as the user who invoked the installer, which is why
it has to be run with `sudo` by that user rather than from a root shell. On a host with no
systemd the installer says so and leaves the sampler to be started some other way.

The runner user needs passwordless sudo for `docker`, `nginx`, `systemctl reload nginx`, `tee`,
`rm` and `mkdir`. This is already true on `cicd.rtx.ai`, because `.github/workflows/pytest.yml`
calls `sudo docker` with no terminal attached. Confirm it as the runner user with `sudo -n true`.

### Environment variables

Everything below is read by `deploy/preview/lib.sh` and can be overridden in the environment.

| variable | default | meaning |
| --- | --- | --- |
| `PREVIEW_PATH_PREFIX` | empty | text placed in front of the PR number in the URL and the snippet name |
| `PREVIEW_PORT_BASE` | `10000` | host port is this plus the PR number |
| `PREVIEW_NGINX_DIR` | `/etc/nginx/arax-preview.d` | where the per-PR nginx snippets live |
| `PREVIEW_PUBLIC_BASE_URL` | `https://cicd.rtx.ai` | scheme and host used to build the public URL |
| `PREVIEW_DB_DIR` | `/mnt/data/orangeboard/databases` | host database directory mounted into every preview |
| `PREVIEW_CONFIG_SECRETS` | `/mnt/config/config_secrets.json` | host secrets file mounted into every preview |
| `PREVIEW_TTL_DAYS` | `7` | age after which garbage collection removes a preview |
| `PREVIEW_HEALTH_TIMEOUT` | `900` | seconds to wait for the ARAX status endpoint after start |
| `PREVIEW_FAST_HEALTH_TIMEOUT` | `180` | same wait after a fast redeploy, where only the Flask services restart |
| `PREVIEW_REPO` | `RTXteam/RTX` | repository the pull request state is checked against |
| `PREVIEW_BUILD_CONTEXT` | `<repo>/DockerBuild` | docker build context, the workflow points it at `pr-head/DockerBuild` |
| `PREVIEW_DOCKERFILE` | `$PREVIEW_BUILD_CONTEXT/CICD-Dockerfile` | Dockerfile used for the image |
| `PREVIEW_NGINX_SITE` | `/etc/nginx/sites-enabled/default` | site file edited by `install-nginx-include.sh` |
| `PREVIEW_MEMORY_LIMIT` | `2g` | `docker run --memory` for a preview container. Never lower than `2g` |
| `PREVIEW_CPU_LIMIT` | `1.5` | `docker run --cpus` for a preview container |
| `PREVIEW_MAX_ACTIVE` | `3` | how many previews may live on the host at once |
| `PREVIEW_MIN_FREE_DISK_GB` | `10` | absolute disk floor for a full rebuild, combined with the percentage below |
| `PREVIEW_MIN_FREE_DISK_PCT` | `10` | percentage of the docker root volume, the larger of the two floors applies |
| `PREVIEW_MIN_FREE_RAM_MB` | `2048` | refuse a full rebuild below this much available memory |
| `PREVIEW_WEB_ROOT` | `/var/www/arax-preview` | document root of the status page, per-PR reports go in `data/<PR>/` |
| `PREVIEW_HOST_STATS_INTERVAL` | `15` | seconds between host samples written to `host.json` |
| `PREVIEW_STATE_STALE_SECONDS` | `7200` | a stage still marked running after this is written down as abandoned |
| `PREVIEW_ORPHAN_TTL_HOURS` | `24` | how long `gc.sh` keeps status page data that has no container behind it |
| `PREVIEW_STATS_SERVICE` | `/etc/systemd/system/arax-preview-stats.service` | unit file the installer writes for the sampler |
| `PREVIEW_LOG_DIR` | `/var/log/arax-preview` | full deploy logs, pruned after 30 days by `gc.sh` |
| `PREVIEW_UI_RTXJS` | `<repo>/code/UI/interactive/rtx.js` | UI source `query_smoke.sh` reads the example payloads from |
| `PREVIEW_QUERY_BASE` | the public preview URL | base URL `query_smoke.sh` posts to |
| `DOCKER` | `sudo docker` | docker command used by every script |
| `SUDO` | `sudo` | privilege escalation command used by every script |

## The shared `/rtxcomplete/` caveat

`code/UI/interactive/index.html` and `rtxcompletenode.js` load the autocomplete service with a
root absolute path, `/rtxcomplete/...`, not a relative one. That path has no PR number in it, so
it cannot be routed per preview. All previews on the box therefore share a single
`/rtxcomplete/` route, and `deploy.sh` points it at the preview that was deployed most recently.

What this means in practice: autocomplete suggestions in an older preview come from the newest
preview's container. Everything else, including the whole ARAX API, is properly isolated per
pull request. Tearing down the newest preview repoints `/rtxcomplete/` at whichever preview is
next newest, and removes the route entirely when no previews are left.

## Lifecycle

- **Redeploy** takes whichever path the command asks for, and the URL stays the same either way.
  `/deploy` removes the existing container and image for that pull request and builds again from
  scratch. `/redeploy` moves the container to the new commit and restarts the Flask services. See
  **What /redeploy does** above.
- **Teardown on close.** Closing or merging a pull request triggers the teardown job, which
  removes the container, the image and the nginx snippet.
- **Daily garbage collection.** A scheduled run of `gc.sh` removes previews older than
  `PREVIEW_TTL_DAYS` and previews whose pull request is no longer open. Merged pull requests
  count as closed. Without a GitHub token the age rule is the only one that applies. The same
  run also sweeps the status page data of pull requests that have no container, removing a
  directory whose pull request is closed and one left by a failed or abandoned run that finished
  more than `PREVIEW_ORPHAN_TTL_HOURS` ago, 24 by default, so a deploy that died before it ever
  created a container stops drawing a card the next day.
- **Status page refresh.** A cron entry runs `status-refresh.sh` every 5 minutes, which rewrites
  the status page with current host numbers and container states. It touches nothing else.
- **Host sampling.** `arax-preview-stats.service` runs `host-stats.sh` for as long as the host is
  up, writing one `host.json` sample every 15 seconds. systemd restarts it 5 seconds after a
  crash and starts it again after a reboot.

## Manual operations

```
# deploy a preview, letting the script pick the path
bash deploy/preview/deploy.sh 2853 my-branch

# same, with a commit, which is what makes the restart path possible at all
bash deploy/preview/deploy.sh 2853 my-branch 0123456789abcdef0123456789abcdef01234567

# always rebuild the image, what /deploy runs
bash deploy/preview/deploy.sh --force 2853 my-branch

# only restart, refuse rather than rebuild, what /redeploy runs
bash deploy/preview/deploy.sh --fast-only 2853 my-branch 0123456789abcdef0123456789abcdef01234567

# remove one preview
bash deploy/preview/teardown.sh 2853

# see what garbage collection would do, without doing it
bash deploy/preview/gc.sh --dry-run

# smoke test a running preview, optionally with the test suite
bash deploy/preview/smoke.sh 2853
bash deploy/preview/smoke.sh 2853 --pytest "-k test_ARAX_query"

# run the test suite and print the Markdown report the bot posts
bash deploy/preview/pytest_report.sh 2853
bash deploy/preview/pytest_report.sh 2853 "-k test_ARAX_query"

# post the four example queries of the UI at a preview, through its public URL
bash deploy/preview/query_smoke.sh 2853

# the same, against a preview reached some other way
PREVIEW_QUERY_BASE=http://127.0.0.1:12853 bash deploy/preview/query_smoke.sh 2853

# rewrite the status page by hand, the same thing cron runs every 5 minutes
bash deploy/preview/status-refresh.sh

# write one host.json sample and exit, the same thing the installer runs
bash deploy/preview/host-stats.sh --once

# the sampler behind the live tiles: is it up, and what has it been saying
systemctl status arax-preview-stats
journalctl -u arax-preview-stats -n 50

# what a preview left on the host
ls /var/www/arax-preview/data/2853/     # the reports the status page embeds
ls /var/log/arax-preview/               # full deploy logs, pruned after 30 days

# list every preview on the box
sudo docker ps --filter label=arax.preview=true

# one time host setup
sudo bash deploy/preview/install-nginx-include.sh
```

## Limitations

- **Same repository branches only.** `DockerBuild/CICD-Dockerfile` clones `RTXteam/RTX` inside
  the image and checks out `BUILD_BRANCH`, so a branch that only exists on a fork cannot be
  built. The workflow refuses fork pull requests with a clear message rather than failing
  halfway through a build.
- **One box, shared resources.** Previews run on the same EC2 instance as the pytest workflow
  and as every other preview. Several previews at once compete for memory and disk. The preflight
  and the per-container caps described under **Resource guards** keep that from taking the host
  down, at the price of refusing the fourth preview outright.
- **Plain HTTP inside the box.** TLS terminates at nginx. The container speaks HTTP on a
  loopback port and is not reachable from outside the host on its own.
- **Shared `/rtxcomplete/`.** See the section above.
- **Startup is slow.** A cold preview takes several minutes to answer, because the image is
  built with `--no-cache` and the container has to build the knowledge provider info cache
  before the API responds.
- **A host reboot needs a redeploy.** The container has no init system, apache and the Flask
  services are started with `docker exec` after `docker run`. If `cicd.rtx.ai` reboots the
  containers may come back but the services inside them do not. Comment `/deploy` again.
- **`pytest.yml` must stay scoped.** The pytest workflow used to stop and delete every container
  and image on the host. It now only touches `rtx_test` and `rtx:test`. Reverting that change
  would kill every preview on each CI run.

## Security note

Previews run on a self-hosted runner that mounts real database files and a real
`config_secrets.json` into the container. Anyone who can make that runner execute arbitrary code
gets those secrets. Two guards follow from that:

- `/deploy`, `/redeploy` and `/undeploy` are only honoured when the comment author association is
  `OWNER`, `MEMBER` or `COLLABORATOR`. A drive-by comment from an outside contributor does
  nothing.
- Fork pull requests are refused outright.

Preview URLs are unauthenticated and anybody who knows the pull request number can reach one.
Treat a preview as public and do not put anything sensitive into a preview query.
