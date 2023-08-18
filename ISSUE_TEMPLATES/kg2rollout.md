_NOTE: To create a new issue based on this template, simply go to: https://github.com/RTXteam/RTX/issues/new?template=kg2rollout.md_

**THE BRANCH FOR THIS ROLLOUT IS: `________`**
**THE ARAX-DATABASES.RTX.AI DIRECTORY FOR THIS ROLLOUT IS: `/home/rtxconfig/KG2_____`**

#### 1. Build and load KG2c:

- [ ] merge `master` into the branch being used for this KG2 version (which would typically be named like `KG2.X.Yc`).
- [ ] update the four hardcoded biolink version numbers in the branch (as needed):
  - [ ] in `code/UI/OpenAPI/python-flask-server/openapi_server/openapi/openapi.yaml` ([github](https://github.com/RTXteam/RTX/tree/master/code/UI/OpenAPI/python-flask-server/openapi_server/openapi/openapi.yaml#L18); [local](../code/UI/OpenAPI/python-flask-server/openapi_server/openapi/openapi.yaml))
  - [ ] in `code/UI/OpenAPI/python-flask-server/KG2/openapi_server/openapi/openapi.yaml` ([github](https://github.com/RTXteam/RTX/tree/master/code/UI/OpenAPI/python-flask-server/KG2/openapi_server/openapi/openapi.yaml#L18); [local](../code/UI/OpenAPI/python-flask-server/KG2/openapi_server/openapi/openapi.yaml))
  - [ ] in `code/UI/OpenAPI/python-flask-server/RTX_OA3_TRAPI1.4_ARAX.yaml` ([github](https://github.com/RTXteam/RTX/tree/master/code/UI/OpenAPI/python-flask-server/RTX_OA3_TRAPI1.4_ARAX.yaml#L17); [local](../code/UI/OpenAPI/python-flask-server/RTX_OA3_TRAPI1.4_ARAX.yaml))
  - [ ] in `code/UI/OpenAPI/python-flask-server/RTX_OA3_TRAPI1.4_KG2.yaml` ([github](https://github.com/RTXteam/RTX/tree/master/code/UI/OpenAPI/python-flask-server/RTX_OA3_TRAPI1.4_KG2.yaml#L17); [local](../code/UI/OpenAPI/python-flask-server/RTX_OA3_TRAPI1.4_KG2.yaml))
- [ ] build a new KG2c on `buildkg2c.rtx.ai` from the branch (how-to is [here](https://github.com/RTXteam/RTX/tree/master/code/kg2c#build-kg2canonicalized))
  - [ ] before starting the build:
    - [ ] make sure there is enough disk space available on `arax-databases.rtx.ai` (need at least 100G, ideally >120G). delete old KG2 database directories as needed (warn the team on Slack in advance).
    - [ ] make sure to choose to build a new synonymizer in `kg2c_config.json`, as described in the how-to
  - [ ] after the build is done, verify it looks ok:
    - [ ] `node_synonymizer.sqlite` should be around 8-15 GB
    - [ ] make sure `node_synonymizer.sqlite`'s last modified date is today (or whatever day the build was run)
    - [ ] make sure `kg2c_lite.json.gz`'s last modified date is today (or whatever day the build was run)
    - [ ] the entire build runtime (synonymizer + KG2c) shouldn't have been more than 24 hours
    - [ ] the synonymizer and KG2c artifacts should have been auto-uploaded into the proper directory on `arax-databases.rtx.ai` (`/home/rtxconfig/KG2.X.Y`)
- [ ] load the new KG2c into neo4j at http://kg2-X-Yc.rtx.ai:7474/browser/ (how to is [here](https://github.com/RTXteam/RTX/tree/master/code/kg2c#host-kg2canonicalized-in-neo4j))
  - [ ] verify the correct KG2 version was uploaded by running this query: `match (n {id:"RTX:KG2c"}) return n`
- [ ] update `RTX/code/config_dbs.json` in the branch:
  - [ ] update the synonymizer version number/path
  - [ ] update the fda_approved_drugs version number/path
  - [ ] update the autocomplete version number/path
  - [ ] update the meta_kg version number/path
  - [ ] update the kg2c sqlite version number/path
  - [ ] update the KG2pre and KG2c Neo4j endpoints
- [ ] upload the new `kg2c_lite_2.X.Y.json.gz` file to the [translator-lfs-artifacts](https://github.com/ncats/translator-lfs-artifacts/tree/main/files) repo
- [ ] upload the new `kg2_nodes_not_in_sri_nn.tsv` file to the [translator-lfs-artifacts](https://github.com/ncats/translator-lfs-artifacts/tree/main/files) repo
- [ ] load the new KG2c into Plover (how-to is [here](https://github.com/RTXteam/PloverDB/wiki/Deployment-how-tos#to-build-plover-from-a-new-kg2-version))
- [ ] update `config_dbs.json` in the branch for this KG2 version in the RTX repo to point to the new Plover **for the 'dev' maturity level**


#### 2. Rebuild downstream databases:

The following databases should be rebuilt and copies of them should be put in `/home/rtxconfig/KG2.X.Y` on `arax-databases.rtx.ai`. Please use this kind of naming format: `mydatabase_v1.0_KG2.X.Y.sqlite`.

- [ ] NGD database (how-to is [here](https://github.com/RTXteam/RTX/blob/master/code/ARAX/ARAXQuery/Overlay/ngd/README.md))
- [ ] refreshed DTD @chunyuma
- [ ] DTD model @chunyuma _(may be skipped - depends on the changes in this KG2 version)_
- [ ] DTD database @chunyuma _(may be skipped - depends on the changes in this KG2 version)_
- [ ] XDTD database @chunyuma

**NOTE**: As databases are rebuilt, `RTX/code/config_dbs.json` will need to be updated to point to their new paths! Push these changes to the branch for this KG2 version, unless the rollout of this KG2 version has already occurred, in which case you should push to `master` (but first follow the steps described [here](https://github.com/RTXteam/RTX/wiki/Config,-databases,-and-SFTP#config_dbsjson)). 


#### 3. Update the ARAX codebase:

All code changes should **go in the branch for this KG2 version**!

- [ ] regenerate the KG2c test triples file in the branch for this KG2 version @acevedol
  - [ ] ensure the new KG2c Neo4j is currently running
  - [ ] check out the branch and pull to get the latest changes (this is important for ensuring the correct KG2c Neo4j is used)
  - [ ] run [create_json_of_kp_predicate_triples.py](https://github.com/RTXteam/RTX/blob/master/code/ARAX/KnowledgeSources/create_json_of_kp_predicate_triples.py)
  - [ ] push the regenerated file to `RTX/code/ARAX/KnowledgeSources/RTX_KG2c_test_triples.json`
- [ ] update Expand code as needed
- [ ] update any other modules as needed
- [ ] test everything together:
  - [ ] check out the branch and pull to get the latest changes
  - [ ] locally set `force_local = True` in `ARAX_expander.py` (to avoid using the old KG2 API)
  - [ ] then run the entire ARAX pytest suite (i.e., `pytest -v`)
  - [ ] address any failing tests
- [ ] update the KG2 and ARAX version numbers in the appropriate places (in the branch for this KG2 version)
  - [ ] Bump version on line 12 in `RTX/code/UI/OpenAPI/python-flask-server/openapi_server/openapi/openapi.yaml` ([github](https://github.com/RTXteam/RTX/blob/master/code/UI/OpenAPI/python-flask-server/openapi_server/openapi/openapi.yaml#L12); [local](../code/UI/OpenAPI/python-flask-server/openapi_server/openapi/openapi.yaml)); the major and minor release numbers are kept synchronous with the TRAPI version; just bump the patch release version (least significant digit)
  - [ ] Bump version on line 12 in `RTX/code/UI/OpenAPI/python-flask-server/KG2/openapi_server/openapi/openapi.yaml` ([github](https://github.com/RTXteam/RTX/blob/master/code/UI/OpenAPI/python-flask-server/KG2/openapi_server/openapi/openapi.yaml#L12); [local](../code/UI/OpenAPI/python-flask-server/KG2/openapi_server/openapi/openapi.yaml)); the first three digits are kept synchronous with the KG2 release version
  - [ ] Bump version on line 4 in `RTX/code/UI/OpenAPI/python-flask-server/RTX_OA3_TRAPI1.4_ARAX.yaml` ([github](https://github.com/RTXteam/RTX/blob/master/code/UI/OpenAPI/python-flask-server/RTX_OA3_TRAPI1.4_ARAX.yaml#L4); [local](../code/UI/OpenAPI/python-flask-server/RTX_OA3_TRAPI1.4_ARAX.yaml)); same as for the ARAX `openapi.yaml` file
  - [ ] Bump version on line 4 in `RTX/code/UI/OpenAPI/python-flask-server/RTX_OA3_TRAPI1.4_KG2.yaml` ([github](https://github.com/RTXteam/RTX/blob/master/code/UI/OpenAPI/python-flask-server/RTX_OA3_TRAPI1.4_KG2.yaml#L4); [local](../code/UI/OpenAPI/python-flask-server/RTX_OA3_TRAPI1.4_KG2.yaml)); same as for the KG2 `openapi.yaml` file
  

#### 4. Pre-upload databases:

Before rolling out, we need to pre-upload the new databases (referenced in `config_dbs.json`) to `arax.ncats.io` and the ITRB SFTP server. These steps can be done well in advance of the rollout; it doesn't hurt anything to do them early.

- [ ] make sure `arax.ncats.io` has at least 100G of disk space free; delete old KG2 databases to free up space as needed (warn the team on slack first)
- [ ] copy the new databases from `arax-databases.rtx.ai` to `arax.ncats.io:/data/orangeboard/databases/KG2.X.Y`; example for KG2.8.0:
  - [ ] `ssh myuser@arax.ncats.io`
  - [ ] `cd /data/orangeboard/databases/`
  - [ ] `mkdir -m 777 KG2.8.0`
  - [ ] `scp rtxconfig@arax-databases.rtx.ai:/home/rtxconfig/KG2.8.0/*2.8.0* KG2.8.0/`
- [ ] upload the new databases and their md5 checksums to ITRB's SFTP server using the steps detailed [here](https://github.com/RTXteam/RTX/wiki/Config,-databases,-and-SFTP#steps-for-all-databases-at-once)



#### 5. Rollout new KG2c version to `arax.ncats.io` development endpoints
- [ ] Notify the `#deployment` channel in the `ARAXTeam` Slack workspace that you are rolling out a new version of KG2c to the various `arax.ncats.io` development endpoints.
- [ ] merge `master` into the branch for this KG2 version
- [ ] merge the branch into `master`
- [ ] roll `master` out to the various `arax.ncats.io` development endpoints. Usually in this order:
  - [ ] `devED`
  - [ ] `kg2beta`
  - [ ] `beta`
  - [ ] `test`
  - [ ] `devLM`
- [ ] to roll `master` out to a specific endpoint `/EEE`, you would do the following steps:
  - [ ] If you are offsite, log into your office VPN (there are strict IP address block restrictions on client IPs that can ssh into `arax.ncats.io`)
  - [ ] Log in to `arax.ncats.io`: `ssh arax.ncats.io` (you previously need to have set up your username, etc. in `~/.ssh/config`; see bottom of this issue template for an example)
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
- [ ] run the pytest suite on the various endpoints
- [ ] update our CI/CD testing instance with the new databases:
  - [ ] `ssh ubuntu@cicd.rtx.ai`
  - [ ] `cd RTX`
  - [ ] `git pull origin master`
  - [ ] If there have been changes to `requirements.txt`, make sure to do `~/venv3.9/bin/pip3 install -r code/requirements.txt`
  - [ ]  `sudo bash`
  - [ ] `mkdir -m 777 /mnt/data/orangeboard/databases/KG2.X.Y`
  - [ ] `exit`
  - [ ] `~/venv3.9/bin/python3 code/ARAX/ARAXQuery/ARAX_database_manager.py --mnt --skip-if-exists --remove_unused`

#### 6. Final items/clean up:

- [ ] turn off the old KG2c version's neo4j instance
  - [ ] determine what is the DNS A record hostname for `kg2-X-Zc.rtx.ai` (where `Z` is one less than the new minor release version): run `nslookup kg2-X-Zc.rtx.ai` (it will return either `kg2canonicalized.rtx.ai` or `kg2canonicalized2.rtx.ai`; we'll call it `kg2canonicalizedN.rtx.ai`).
  - [ ] message the `#deployment` channel in the `ARAXTeam` Slack workspace that you will be stopping the `kg2canonicalizedN.rtx.ai` Neo4j endpoint
  - [ ] `ssh ubuntu@kg2-X-Zc.rtx.ai` 
  - [ ] `sudo service neo4j stop`
  - [ ] In the AWS console, stop the instance `kg2canonicalizedN.rtx.ai`
- [ ] turn off the old KG2c version's plover instance
  - [ ] Determine what is the DNS A record hostname for `kg2-X-Zcplover.rtx.ai` (where `Z` is one less than the new minor release version): run `nslookup kg2-X-Zploverc.rtx.ai` (it will return either `kg2cplover.rtx.ai`, `kg2cplover2.rtx.ai`, or `kg2cplover3.rtx.ai`; we'll call it `kg2cploverN.rtx.ai`).
  - [ ] message the `#deployment` channel in the `ARAXTeam` Slack workspace that you will be stopping the `kg2-X-Zcplover.rtx.ai` PloverDB service
  - [ ] Log into `kg2cploverN.rtx.ai`: `ssh ubuntu@kg2cploverN.rtx.ai`
  - [ ] Stop the PloverDB container: `sudo docker stop plovercontainer2.X.Z` (if you are not sure of the container name, try `sudo docker container ls -a`).
- [ ] turn off the new KG2pre version's neo4j instance (Coordinate with the KG2pre team before doing this)
- [ ] upgrade the ITRB Plover endpoint (https://kg2cploverdb.ci.transltr.io) to this KG2 version and make the KG2 API start using it (instead of our self-hosted endpoint): 
    - [ ] update `kg_config.json` in the `main` branch of the Plover repo to point to the new `kg2c_lite_2.X.Y.json.gz` file (push this change)
    - [ ] wait about 60 minutes for the endpoint to rebuild and then run Plover tests to verify it's working
    - [ ] run the ARAX pytest suite with the NCATS endpoint plugged in (locally change the URL in `RTX/code/config_dbs.json` and set `force_local = True` in Expand)
    - [ ] if all tests pass, update `config_dbs.json` in `master` to point to the ITRB Plover endpoints (all maturity levels): (`dev`: `kg2cploverdb.ci.transltr.io`; `test`: `kg2cploverdb.test.transltr.io`; `prod`: `kg2cploverdb.transltr.io`)
    - [ ] push latest `master` branch code to the various endpoints on `arax.ncats.io` that you previously updated (to get the changed `config_dbs.json` file) and restart services
    - [ ] turn off the self-hosted plover endpoint for the new version of KG2c
      - [ ] message the `#deployment` channel to notify people what you are about to do
      - [ ] `ssh ubuntu@kg2cploverM.rtx.ai`
      - [ ] `sudo docker container ls -a` (gives you the name of the container)
      - [ ] `sudo docker stop plovercontainer2.X.Y`
    - [ ] verify once more that ARAX is still working properly, even with the self-hosted new-KG2c-version PloverDB service turned off

#### 7. Roll-out to ITRB TEST 
- [ ] Merge `master` to `itrb-test`.
- [ ] Put in request to Sarah Stemann to open a ticket to re-deploy ARAX, RTX-KG2, and PloverDB to ITRB test
- [ ] Track roll-out to ensure that the build and deployment succeeded
- [ ] Test out the updated services in ITRB test to verify they are working correctly

#### 8. Roll-out to ITRB PRODUCTION
- [ ] Merge `master` to `production`
- [ ] Put in request to Sarah Stemann to open a ticket to re-deploy ARAX, RTX-KG2, and PloverDB to ITRB production
- [ ] Track roll-out to ensure that the build and deployment succeeded
- [ ] Test out the updated services in ITRB test to verify they are working correctly

#### Example ssh config for setting up login into `arax.ncats.io`:
```
Host arax.ncats.io
    User stephenr
    ProxyCommand ssh -i ~/.ssh/id_rsa_long -W %h:%p stephenr@35.87.194.254
    IdentityFile ~/.ssh/id_rsa_long
    Hostname 172.31.53.16
```
