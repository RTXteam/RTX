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

Three ways, all of which end up running the same scripts on the runner.

- Comment `/deploy` on the pull request. Comment `/undeploy` to remove it again. Only comments
  from an OWNER, MEMBER or COLLABORATOR are acted on.
- Actions tab, pick **Preview Deploy**, **Run workflow**, fill in `pr_number`. Tick `run_tests`
  to also run the ARAX test suite inside the container, and put anything extra in `pytest_args`.
- On the host directly: `bash deploy/preview/deploy.sh 2853 my-branch`.

The workflow posts one sticky comment on the pull request with the URL, the branch and short
commit, and the smoke test table. Redeploying updates that same comment instead of adding a
new one. A refused `/deploy` (fork pull request, closed pull request) gets a short reply saying
why.

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

```
  PR comment "/deploy"  or  Actions "Run workflow"
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
  |    docker build -f DockerBuild/CICD-Dockerfile              |
  |      (the image git clones RTXteam/RTX and checks out       |
  |       BUILD_BRANCH, so the branch must live upstream)       |
  |         |                                                   |
  |         v                                                   |
  |    docker run -d -i -t --name rtx_pr_2853                   |
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

Then it runs `nginx -t` and reloads. If the check fails the backup is restored. If no matching
server block is found nothing is written and the script prints the manual instructions. Running
it a second time detects the existing line and exits without touching anything.

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
| `PREVIEW_REPO` | `RTXteam/RTX` | repository the pull request state is checked against |
| `PREVIEW_BUILD_CONTEXT` | `<repo>/DockerBuild` | docker build context, the workflow points it at `pr-head/DockerBuild` |
| `PREVIEW_DOCKERFILE` | `$PREVIEW_BUILD_CONTEXT/CICD-Dockerfile` | Dockerfile used for the image |
| `PREVIEW_NGINX_SITE` | `/etc/nginx/sites-enabled/default` | site file edited by `install-nginx-include.sh` |
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

- **Redeploy** replaces. `deploy.sh` removes the existing container and image for that PR before
  it builds, so the URL stays the same and always serves the latest push you deployed.
- **Teardown on close.** Closing or merging a pull request triggers the teardown job, which
  removes the container, the image and the nginx snippet.
- **Daily garbage collection.** A scheduled run of `gc.sh` removes previews older than
  `PREVIEW_TTL_DAYS` and previews whose pull request is no longer open. Merged pull requests
  count as closed. Without a GitHub token the age rule is the only one that applies.

## Manual operations

```
# deploy or redeploy a preview
bash deploy/preview/deploy.sh 2853 my-branch

# remove one preview
bash deploy/preview/teardown.sh 2853

# see what garbage collection would do, without doing it
bash deploy/preview/gc.sh --dry-run

# smoke test a running preview, optionally with the test suite
bash deploy/preview/smoke.sh 2853
bash deploy/preview/smoke.sh 2853 --pytest "-k test_ARAX_query"

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
  and as every other preview. Several previews at once compete for memory and disk. Keep the
  number of live previews small and let garbage collection do its job.
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

- `/deploy` and `/undeploy` are only honoured when the comment author association is `OWNER`,
  `MEMBER` or `COLLABORATOR`. A drive-by comment from an outside contributor does nothing.
- Fork pull requests are refused outright.

Preview URLs are unauthenticated and anybody who knows the pull request number can reach one.
Treat a preview as public and do not put anything sensitive into a preview query.
