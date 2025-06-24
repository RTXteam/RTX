_NOTE: To create a new issue based on this template, simply go to: https://github.com/RTXteam/RTX/issues/new?template=kg2rollout.md_

**THE BRANCH FOR THIS ROLLOUT IS: `________`**
**THE ARAX-DATABASES.RTX.AI DIRECTORY FOR THIS ROLLOUT IS: `/home/rtxconfig/KG2_____`**  
**Sprint changelog link: ([Changelog](https://github.com/RTXteam/RTX/issues/ ________))**

#### Prerequisites
##### ssh access
To complete this workflow, you will need `ssh` access to:
- [ ] `arax-databases.rtx.ai`
- [ ] the self-hosted ARAX/KG2 instance, `arax.ncats.io` (see example configuration information below)
- [ ] the self-hosted PloverDB instances, `kg2cploverN.rtx.ai`
- [ ] the self-hosted Neo4j instances for KG2c, `kg2canoncalizedN.rtx.ai`
- [ ] the self-hosted CI/CD instance, `cicd.rtx.ai`
- [ ] the webserver for downloading of the KG2c "lite" JSON file, `kg2webhost.rtx.ai`

##### GitHub access
- [ ] write access to the `RTXteam/PloverDB` project area
- [ ] write access to the `RTXteam/RTX` project area
- [ ] write access to the `ncats/translator-lfs-artifacts` project area (not critical, but needed for some final archiving steps; Amy Glen and Sundar Pullela have access)

##### AWS access
You will need:
- [ ] access to the AWS Console (you'll need an IAM username; ask Stephen Ramsey about getting one)
- [ ] IAM permission to start and stop instances in EC2 via the AWS Console
- [ ] access to the S3 bucket `s3://rtx-kg2/` (ask Stephen Ramsey for access)

##### Slack workspaces
You will also need access to the following Slack workspaces:
- [ ] ARAXTeam (subscribe to `#deployment`)
- [ ] NCATSTranslator (subscribe to `#devops-teamexpanderagent`)

#### Example ssh config for setting up login into `arax.ncats.io`:
```
Host arax.ncats.io
    User stephenr
    ProxyCommand ssh -i ~/.ssh/id_rsa_long -W %h:%p stephenr@35.87.194.254
    IdentityFile ~/.ssh/id_rsa_long
    Hostname 172.31.53.16
```

#### 1. Build and load KG2c:

- [ ] merge `master` into the branch being used for this KG2 version (which would typically be named like `KG2.X.Yc`).  Record this issue number in the merge message.
- [ ] update the four hardcoded biolink and KG2c version numbers in the branch (as needed):
  - [ ] in `code/UI/OpenAPI/python-flask-server/openapi_server/openapi/openapi.yaml` ([github](https://github.com/RTXteam/RTX/tree/master/code/UI/OpenAPI/python-flask-server/openapi_server/openapi/openapi.yaml#L18); [local](../code/UI/OpenAPI/python-flask-server/openapi_server/openapi/openapi.yaml))
  - [ ] in `code/UI/OpenAPI/python-flask-server/KG2/openapi_server/openapi/openapi.yaml` ([github](https://github.com/RTXteam/RTX/tree/master/code/UI/OpenAPI/python-flask-server/KG2/openapi_server/openapi/openapi.yaml#L18); [local](../code/UI/OpenAPI/python-flask-server/KG2/openapi_server/openapi/openapi.yaml))
  - [ ] in `code/UI/OpenAPI/specifications/export/ARAX/1.5.0/openapi.yaml`([github](https://github.com/RTXteam/RTX/blob/master/code/UI/OpenAPI/specifications/export/ARAX/1.5.0/openapi.yaml#L18))
  - [ ] in `code/UI/OpenAPI/specifications/export/KG2/1.5.0/openapi.yaml` ([github](https://github.com/RTXteam/RTX/blob/master/code/UI/OpenAPI/specifications/export/KG2/1.5.0/openapi.yaml#L18))
- [ ] build a new KG2c on `buildkg2c.rtx.ai` from the branch (how-to is [here](https://github.com/RTXteam/RTX/tree/master/code/kg2c#build-kg2canonicalized))
  - [ ] before starting the build:
    - [ ] make sure there is enough disk space available on `arax-databases.rtx.ai` (need at least 100G, ideally >120G). delete old KG2 database directories as needed (warn the team on Slack in advance).

  **NOTE:** For detailed deployment instructions, follow the instructions [here](https://github.com/RTXteam/RTX/tree/master/code/kg2c#building-kg2c)
    - [ ] to do a standard build of a new synonymizer (expected runtime: 7-10 hours), run:
      - [ ] `cd RTX/code/kg2c/synonymizer_build`
      - [ ] `python build_synonymizer.py 2.X.Y v1.0 --downloadkg2pre --uploadartifacts`
      - [ ] after the build, run the Synonymizer pytest regression test suite:
        - [ ] `pytest -vs test_synonymizer.py --synonymizername node_synonymizer_v1.0_KG2.X.Y.sqlite`
      - [ ] make sure that `node_synonymizer_v1.0_KG2.X.Y.sqlite` is about 15-20 GB and its last modified date is today
      - [ ] copy `node_synonymizer_v1.0_KG2.X.Y.sqlite` to the public S3 bucket for RTX-KG2: `aws s3 cp node_synonymizer_v1.0_KG2.X.Y.sqlite s3://rtx-kg2-public/`
    - [ ] to do a standard full build of a new KG2c (expected runtime: 8-10 hours), run:
      - [ ] `cd RTX/code/kg2c`
      - [ ] `python build_kg2c.py 2.X.Y v1.0 4.2.1 --uploadartifacts`
        - **NOTE:** 4.2.1 is the Biolink version, please use the latest biolink version based on the KG2pre build's biolink version. Add a `--test` flag to the KG2c build execution to do a test build.
      - [ ] after the build is done, make sure `kg2c_lite.json.gz`'s last modified date is today (or whatever day the build was run)
    - [ ] the synonymizer and KG2c artifacts should have been auto-uploaded into the proper directory on `arax-databases.rtx.ai` (`/home/rtxconfig/KG2.X.Y`) and to `kg2webhost.rtx.ai` (if `--uploadartifacts` flag during the KG2c build is set). If not, manually upload the files using `scp` (and _make sure to set the ownership of the database files to user `rtxconfig`)_.
    - [ ] Upload the JSON-lines files (`kg2c-2.X.Y-v1.0-nodes.jsonl.gz` and `kg2c-2.X.y-v1.0-edges.jsonl.gz`) to the public S3 bucket, `s3://rtx-kg2-public`
- [ ] load the new KG2c into neo4j at http://kg2-X-Yc.rtx.ai:7474/browser/ (how to is [here](https://github.com/RTXteam/RTX/tree/master/code/kg2c#host-kg2canonicalized-in-neo4j))
  - [ ] verify the correct KG2 version was uploaded by running this query: `match (n {id:"RTX:KG2c"}) return n`
- [ ] update `RTX/code/config_dbs.json` in the branch:
  - [ ] update the synonymizer version number/path
  - [ ] update the fda_approved_drugs version number/path
  - [ ] update the autocomplete version number/path
  - [ ] update the meta_kg version number/path
  - [ ] update the kg2c sqlite version number/path
  - [ ] update the KG2pre and KG2c Neo4j endpoints
- [ ] load the new KG2c into Plover (how-to is [here](https://github.com/RTXteam/PloverDB/wiki/Deployment-notes#to-build-plover-from-a-new-kg2-version))
  - [ ] update `config_kg2c.json` in the `kg2.X.Yc` branch of the Plover repo to point to the new KG2.X.Yc json lines nodes and edges files on `kg2webhost.rtx.ai` (push this change)
  - [ ] `ssh ubuntu@kg2cploverN.rtx.ai`
  - [ ] `cd PloverDB && git pull origin kg2.X.Yc`
  - [ ] if you have **not** yet built the 2.X.Y docker image/container on this instance, run:
    - [ ] `bash -x run.sh -b kg2.X.Yc` (takes about an hour)
  - [ ] otherwise, simply run:
    - [ ] `sudo docker start plovercontainer` (takes about ten minutes)
- [ ] verify that Plover's regression tests pass, and fix any broken tests; from any instance/computer, run:
  - [ ] `cd PloverDB/test`
  - [ ] `pytest -v --endpoint https://kg2cploverN.rtx.ai:9990`
- [ ] update `config_dbs.json` in the branch for this KG2 version in the RTX repo to point to the new Plover in the `plover_url_override` slot

#### 2. Rebuild downstream databases:

The following databases should be rebuilt and copies of them should be put in `/home/rtxconfig/KG2.X.Y` on `arax-databases.rtx.ai`. Please use this kind of naming format: `mydatabase_v1.0_KG2.X.Y.sqlite`.

- [ ] NGD database (how-to is [here](https://github.com/RTXteam/RTX/blob/master/code/ARAX/ARAXQuery/Overlay/ngd/README.md))
    - [ ] Upload the file `curie_to_pmids_v1.0_KG2.X.Y.sqlite` to the public S3 bucket `s3://rtx-kg2-public`.
- [ ] Update the test data indexes for PathFinder @mohsenht
- [ ] Build CURIE NGD database @mohsenht
- [ ] refreshed XDTD database @chunyuma 
- [ ] XDTD database @chunyuma _(may be skipped - depends on the changes in this KG2 version)_
- [ ] refreshed XCRG database @chunyuma
- [ ] XCRG database @chunyuma _(may be skipped - depends on the changes in this KG2 version)_

**NOTE**: As databases are rebuilt, `RTX/code/config_dbs.json` will need to be updated to point to their new paths! Push these changes to the branch for this KG2 version, unless the rollout of this KG2 version has already occurred, in which case you should push to `master` (but first follow the steps described [here](https://github.com/RTXteam/RTX/wiki/Config,-databases,-and-SFTP#config_dbsjson)). 

#### 3. Update the ARAX codebase:

All code changes should **go in the branch for this KG2 version**!

- [ ] update Expand code as needed
- [ ] update any other modules as needed
- [ ] test everything together:
  - [ ] check out the branch and pull to get the latest changes
  - [ ] then run the entire ARAX pytest suite (i.e., `pytest -v`)
  - [ ] address any failing tests
- [ ] update the KG2 and ARAX version numbers in the appropriate places (in the branch for this KG2 version)
  - [ ] Bump version on line 12 in `RTX/code/UI/OpenAPI/python-flask-server/openapi_server/openapi/openapi.yaml` ([github](https://github.com/RTXteam/RTX/blob/master/code/UI/OpenAPI/python-flask-server/openapi_server/openapi/openapi.yaml#L12); [local](../code/UI/OpenAPI/python-flask-server/openapi_server/openapi/openapi.yaml)); the major and minor release numbers are kept synchronous with the TRAPI version; just bump the patch release version (least significant digit)
  - [ ] Bump version on line 12 in `RTX/code/UI/OpenAPI/python-flask-server/KG2/openapi_server/openapi/openapi.yaml` ([github](https://github.com/RTXteam/RTX/blob/master/code/UI/OpenAPI/python-flask-server/KG2/openapi_server/openapi/openapi.yaml#L12); [local](../code/UI/OpenAPI/python-flask-server/KG2/openapi_server/openapi/openapi.yaml)); the first three digits are kept synchronous with the KG2 release version
  - [ ] Bump version on line 4 in `RTX/code/UI/OpenAPI/python-flask-server/RTX_OA3_TRAPI1.4_ARAX.yaml` ([github](https://github.com/RTXteam/RTX/blob/master/code/UI/OpenAPI/python-flask-server/RTX_OA3_TRAPI1.4_ARAX.yaml#L4); [local](../code/UI/OpenAPI/python-flask-server/RTX_OA3_TRAPI1.4_ARAX.yaml)); same as for the ARAX `openapi.yaml` file
  - [ ] Bump version on line 4 in `RTX/code/UI/OpenAPI/python-flask-server/RTX_OA3_TRAPI1.4_KG2.yaml` ([github](https://github.com/RTXteam/RTX/blob/master/code/UI/OpenAPI/python-flask-server/RTX_OA3_TRAPI1.4_KG2.yaml#L4); [local](../code/UI/OpenAPI/python-flask-server/RTX_OA3_TRAPI1.4_KG2.yaml)); same as for the KG2 `openapi.yaml` file

#### 4. Pre-upload databases:

Before rolling out, we need to pre-upload the new databases (referenced in `config_dbs.json`) to `arax.ncats.io` and the ITRB SFTP server. These steps can be done well in advance of the rollout; it doesn't hurt anything to do them early.

- [ ] make sure `arax.ncats.io` has at least 100G of disk space free; delete old KG2 databases to free up space as needed (before doing this, warn the team on the `#deployment` Slack channel on the `ARAXTeam` workspace)
- [ ] copy the new databases from `arax-databases.rtx.ai` to `arax.ncats.io:/translator/data/orangeboard/databases/KG2.X.Y`; example for KG2.8.0:
  - [ ] `ssh myuser@arax.ncats.io`
  - [ ] `cd /translator/data/orangeboard/databases/`
  - [ ] `mkdir -m 777 KG2.X.Y`
  - [ ] `scp rtxconfig@arax-databases.rtx.ai:/home/rtxconfig/KG2.X.Y/*2.X.Y* KG2.X.Y/`
- [ ] upload the new databases and their md5 checksums to ITRB's SFTP server using the steps detailed [here](https://github.com/RTXteam/RTX/wiki/Config,-databases,-and-SFTP#steps-for-all-databases-at-once)

#### 5. Rollout new KG2c version to `arax.ncats.io` development endpoints
- [ ] Notify the `#deployment` channel in the `ARAXTeam` Slack workspace that you are rolling out a new version of KG2c to the various `arax.ncats.io` development endpoints. Provide the KG2c version number in this notification.
- [ ] for the `RTXteam/RTX` project, merge the `master` branch into the branch for this KG2 version.  Record the RTX issue number (for the KG2c rollout checklist issue) in the merge message.
- [ ] for the `RTXteam/RTX` project, merge this KG2 version's branch back into the `master` branch.  Record this issue number in the merge message.
- [ ] to roll `master` out to a specific ARAX or KG2 endpoint named `/EEE`, you would do the following steps:
  - [ ] If you are offsite, log into your office VPN (there are strict IP address block restrictions on client IPs that can ssh into `arax.ncats.io`)
  - [ ] Log in to `arax.ncats.io`: `ssh arax.ncats.io` (you previously need to have set up your username, etc. in `~/.ssh/config`; see the top of this issue template for an example)
  - [ ] Enter the `rtx1` container: `sudo docker exec -it rtx1 bash`
  - [ ] Become user `rt`: `su - rt`
  - [ ] Go to the directory of the code repo for the `EEE` endpoint: `cd /mnt/data/orangeboard/EEE/RTX`
  - [ ] Make sure it is on the master branch: `git branch` (should show `* master`)
  - [ ] Stash any updated files (this is IMPORTANT): `git stash`
  - [ ] Update the code: `git pull origin master`
  - [ ] Restore updated files: `git stash pop`
  - [ ] If there have been changes to `requirements.txt`, make sure to do `pip3 install -r code/requirements.txt`
  - [ ] Become superuser: `exit` (exiting out of your shell session as user `rt` should return you to a `root` user session)
  - [ ] Restart the service: `service RTX_OpenAPI_EEE restart`
  - [ ] View the STDERR logfile as the service starts up: `tail -f /tmp/RTX_OpenAPI_EEE.elog`
  - [ ] Test the endpoint via the web browser interface to make sure it is working
  - [ ] Query the KG2c version by entering this TRAPI query JSON into the browser UI: `{"nodes": {"n00": {"ids": ["RTX:KG2c"]}}, "edges": {}}` (it should return 1 result and the name of that node gives the KG2c version that is installed in the PloverDB that is being queried by the endpoint)
  - [ ] look up `RTX:KG2` in the Synonyms tab in the UI
- [ ] roll `master` out to the various `arax.ncats.io` development endpoints. Usually in this order:
  - [ ] `devED`
  - [ ] `beta`
  - [ ] `test`
  - [ ] `devLM`
- [ ] inside the Docker `rtx1` container, run the pytest suite on the various ARAX development endpoints (that means `devED`, `devLM`, `test`, and `beta`):
  - [ ] `cd /mnt/data/orangeboard/EEE/RTX/code/ARAX/test && pytest -v`
- [ ] update our CI/CD testing instance with the new databases:
  - [ ] `ssh ubuntu@cicd.rtx.ai`
  - [ ] `cd RTX`
  - [ ] `git pull origin master`
  - [ ] If there have been changes to `requirements.txt`, make sure to do `~/venv3.9/bin/pip3 install -r requirements.txt`
  - [ ] `sudo bash`
  - [ ] `mkdir -m 777 /mnt/data/orangeboard/databases/KG2.X.Y`
  - [ ] `exit`
  - [ ] `~/venv3.9/bin/python3 code/ARAX/ARAXQuery/ARAX_database_manager.py --mnt --skip-if-exists --remove_unused`
  - [ ] run a [Test Build](https://github.com/RTXteam/RTX/actions/workflows/pytest.yml) through GitHub Actions, to ensure that the CI/CD is working with the updated databases; all of the pytest tests that are not skipped, should pass

#### 6. Final items/clean up:

- [ ] update the current RTX GitHub changelog issue (add the rollout of this KG2 version as a changelog item)
- [ ] delete the `kg2.X.Yc` branch in the RTX repo (since it has been merged into `master` at this point)
- [ ] turn off the old KG2c version's neo4j instance (if it has not already been turned off; it is likely to have been turned off when the old KG2c was rolled out)
  - [ ] determine what is the DNS A record hostname for `kg2-X-Zc.rtx.ai` (where `Z` is one less than the new minor release version): run `nslookup kg2-X-Zc.rtx.ai` (it will return either `kg2canonicalized.rtx.ai` or `kg2canonicalized2.rtx.ai`; we'll call it `kg2canonicalizedN.rtx.ai`).
  - [ ] message the `#deployment` channel in the `ARAXTeam` Slack workspace that you will be stopping the `kg2canonicalizedN.rtx.ai` Neo4j endpoint
  - [ ] `ssh ubuntu@kg2-X-Zc.rtx.ai` 
  - [ ] `sudo service neo4j stop`
  - [ ] In the AWS console, stop the instance `kg2canonicalizedN.rtx.ai`
- [ ] turn off the **old** KG2c version's plover instance (if it has not already been turned off during the previous KG2c roll-out; under normal circumstances, we turn off the self-hosted PloverDB for the new KG2c, during clean-up)
  - [ ] Determine what is the DNS A record hostname for `kg2-X-Zcplover.rtx.ai` (where `Z` is one less than the new minor release version): run `nslookup kg2-X-Zploverc.rtx.ai` (it will return either `kg2cplover.rtx.ai` or `kg2cplover3.rtx.ai`; we'll call it `kg2cploverN.rtx.ai`).
  - [ ] message the `#deployment` channel in the `ARAXTeam` Slack workspace that you will be stopping the `kg2-X-Zcplover.rtx.ai` PloverDB service
  - [ ] Log into `kg2cploverN.rtx.ai`: `ssh ubuntu@kg2cploverN.rtx.ai`
  - [ ] Stop the PloverDB container: `sudo docker stop plovercontainer2.X.Z` (if you are not sure of the container name, use `sudo docker container ls -a` to get the container name).
- [ ] turn off the new KG2pre version's Neo4j instance (Coordinate with the KG2pre team before doing this)
- [ ] deploy new PloverDB service into ITRB CI that is backed by the new KG2c database: 
    - [ ] merge PloverDB `main` branch into `kg2.X.Yc` branch (if `main` has any commits ahead of `kg2.X.Yc`). Reference this issue (via its full GitHub URL) in the merge message.
    - [ ] merge PloverDB `kg2.X.Yc` branch into `main` branch. Reference this issue (via its full GitHub URL) in the merge message.
    - [ ] wait about 70 minutes for Jenkins to build the PloverDB project and deploy it to `kg2cploverdb.ci.transltr.io`
    - [ ] verify that the CI Plover is running the new KG2 version by:
      - [ ] going to https://kg2cploverdb.ci.transltr.io/code_version and verifying that the correct nodes and edges jsonlines files were used
      - [ ] running the following test and inspecting the command line output: `cd PloverDB/test && pytest -vsk test_version --endpoint https://kg2cploverdb.ci.transltr.io`
    - [ ] run the full Plover test suite to verify everything is working: `cd PloverDB/test && pytest -v --endpoint https://kg2cploverdb.ci.transltr.io`
    - [ ] run the ARAX pytest suite using the CI KG2 Plover (locally remove the `plover_url_override` in `RTX/code/config_dbs.json` by setting it to `null`)
    - [ ] if all tests pass, update `RTX/code/config_dbs.json` in the `master` branch with your local change: (`plover_url_override: null`)
    - [ ] push the latest `master` branch code commit to the various endpoints on `arax.ncats.io` that you previously updated (this is in order to get the changed `config_dbs.json` file) and restart ARAX services
    - [ ] check the [Test Build](https://github.com/RTXteam/RTX/actions/workflows/pytest.yml) (CI/CD tests) to make sure all non-skipped pytest tests have passed
    - [ ] turn off the self-hosted plover endpoint for the new version of KG2c
      - [ ] message the `#deployment` channel to notify people what you are about to do
      - [ ] `ssh ubuntu@kg2cploverM.rtx.ai`
      - [ ] `sudo docker container ls -a` (gives you the name of the container; assume it is `plovercontainer`)
      - [ ] `sudo docker stop plovercontainer`
    - [ ] verify once more that ARAX is still working properly, even with the self-hosted new-KG2c-version PloverDB service turned off
    - [ ] delete the `kg2.X.Yc` branch in the PloverDB repo (since it has been merged into `main` at this point)
- [ ] upload the new `kg2c_lite_2.X.Y.json.gz` file to the [translator-lfs-artifacts](https://github.com/ncats/translator-lfs-artifacts/tree/main/files) repo (ask Amy Glen or Sundar Pullela, who have permission to do this)
- [ ] Download, update, and re-upload to `s3://rtx-kg2-public` the index file `index.html` to add a new section with four hyperlinks for the four information artifacts from the new build (KG2c nodes, KG2c edges, node synonymizer, and curie-to-pmids).
