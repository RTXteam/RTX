_NOTE: To create a new issue based on this template, simply go to: https://github.com/RTXteam/RTX/issues/new?template=kg2rollout.md_

##### 1. Build and load KG2c:

- [ ] merge `master` into the `kg2integration` branch
- [ ] update the four hardcoded biolink version numbers in the `kg2integration` branch (as needed):
  - [ ] in [code/UI/OpenAPI/python-flask-server/openapi_server/openapi/openapi.yaml](../code/UI/OpenAPI/python-flask-server/openapi_server/openapi/openapi.yaml)
  - [ ] in [code/UI/OpenAPI/python-flask-server/KG2/openapi_server/openapi/openapi.yaml](../code/UI/OpenAPI/python-flask-server/KG2/openapi_server/openapi/openapi.yaml)
  - [ ] in [code/UI/OpenAPI/python-flask-server/RTX_OA3_TRAPI1.2_ARAX.yaml](../code/UI/OpenAPI/python-flask-server/RTX_OA3_TRAPI1.2_ARAX.yaml)
  - [ ] in [code/UI/OpenAPI/python-flask-server/RTX_OA3_TRAPI1.2_KG2.yaml](../code/UI/OpenAPI/python-flask-server/RTX_OA3_TRAPI1.2_KG2.yaml)
- [ ] build a new KG2c on `buildkg2c.rtx.ai` from the `kg2integration` branch (how-to is [here](https://github.com/RTXteam/RTX/tree/master/code/kg2c#build-kg2canonicalized))
  - [ ] before starting the build:
    - [ ] make sure there is enough disk space available on `arax-databases.rtx.ai` (need at least 100G, ideally >120G). delete old KG2 database directories as needed (warn the team on Slack in advance).
    - [ ] make sure to choose to build a new synonymizer in `kg2c_config.json`, as described in the how-to
  - [ ] after the build is done, verify it looks ok:
    - [ ] the 'build node' (node with ID `RTX:KG2c`) has the expected version number (KG2.X.Y)
    - [ ] `node_synonymizer.sqlite` should be around 15-20 GB
    - [ ] make sure `node_synonymizer.sqlite`'s last modified date is today (or whatever day the build was run)
    - [ ] make sure `kg2c_lite.json.gz`'s last modified date is today (or whatever day the build was run)
    - [ ] the entire build runtime (synonymizer + KG2c) shouldn't have been more than 24 hours
    - [ ] the synonymizer and KG2c artifacts should have been auto-uploaded into the proper directory on `arax-databases.rtx.ai` (`/home/rtxconfig/KG2.X.Y`)
- [ ] load the new KG2c into neo4j at http://kg2-X-Yc.rtx.ai:7474/browser/ (how to is [here](https://github.com/RTXteam/RTX/tree/master/code/kg2c#host-kg2canonicalized-in-neo4j))
  - [ ] verify the correct KG2 version was uploaded by running this query: `match (n {id:"RTX:KG2c"}) return n`
  - [ ] copy the auto-generated KG2c dump from the Neo4j-hosting instance to the database server like so:
    - `scp /home/ubuntu/kg2-build/kg2c.dump rtxconfig@arax-databases.rtx.ai:/home/rtxconfig/KG2.X.Y/extra_files`
  - [ ] update the KG2pre and KG2c Neo4j endpoints in `RTX/code/config_dbs.json` (push to `kg2integration` branch)
- [ ] upload the new `kg2c_lite_2.X.Y.json.gz` file to the [translator-lfs-artifacts](https://github.com/ncats/translator-lfs-artifacts/tree/main/files) repo
- [ ] load the new KG2c into Plover (available at http://kg2cplover.rtx.ai:9990)
  - [ ] update `config_dbs.json` to point to this new Plover (all maturity levels should point to it for now)
  

##### 2. Rebuild downstream databases:

The following databases should be rebuilt and copies of them should be put in `/home/rtxconfig/KG2.X.Y` on `arax-databases.rtx.ai`. Please use this kind of naming format: `mydatabase_v1.0_KG2.X.Y.sqlite`.

- [ ] NGD database
- [ ] refreshed DTD @chunyuma
- [ ] DTD model @chunyuma _(may be skipped - depends on the changes in this KG2 version)_
- [ ] DTD database @chunyuma _(may be skipped - depends on the changes in this KG2 version)_
- [ ] XDTD database

**NOTE**: As databases are rebuilt, `RTX/code/config_dbs.json` will need to be updated to point to their new paths! Push these changes to the `kg2integration` branch, unless the rollout of this KG2 version has already occurred, in which case you should push to `master` (but first follow the steps described [here](https://github.com/RTXteam/RTX/wiki/Config,-databases,-and-SFTP#config_dbsjson)). 


##### 3. Update the ARAX codebase:

All code changes should **go in the `kg2integration` branch**!

- [ ] regenerate the KG2c test triples file @acevedol
  - [ ] ensure the new KG2c Neo4j is currently running
  - [ ] check out the `kg2integration` branch and pull to get the latest changes (this is important for ensuring the correct KG2c Neo4j is used)
  - [ ] run [this script](https://github.com/RTXteam/RTX/blob/master/code/ARAX/KnowledgeSources/create_csv_of_kp_predicate_triples.py)
  - [ ] push the regenerated file to `RTX/code/ARAX/KnowledgeSources/RTX_KG2c_test_triples.json` (in the `kg2integration` branch)
- [ ] update Expand code as needed
- [ ] update any other modules as needed
- [ ] test everything together:
  - [ ] check out the `kg2integration` branch and pull to get the latest changes
  - [ ] locally set `force_local = True` in `ARAX_expander.py` (to avoid using the old KG2 API)
  - [ ] then run the entire ARAX pytest suite
  - [ ] address any failing tests
- [ ] update the KG2 and ARAX version numbers in the appropriate places (`openapi.yaml`, etc.) @edeutsch
  - [ ] Bump version for `RTX/code/UI/OpenAPI/python-flask-server/openapi_server/openapi/openapi.yaml` in line 12 (`version:`); the major and minor release numbers are kept synchronous with the TRAPI version; just bump the patch release version (least significant digit)
  - [ ] Bump version for `RTX/code/UI/OpenAPI/python-flask-server/KG2/openapi_server/openapi/openapi.yaml` in line 12 (`version:`); the first three digits are kept synchronous with the KG2 release version
  - [ ] Bump version number in `RTX/code/UI/OpenAPI/python-flask-server/RTX_OA3_TRAPI1.3_ARAX.yaml` on line 4 (`version:`); same as for the ARAX `openapi.yaml` file
  - [ ] Bump version number in `RTX/code/UI/OpenAPI/python-flask-server/RTX_OA3_TRAPI1.3_KG2.yaml` on line 4 (`version:`); same as for the KG2 `openapi.yaml` file
  

##### 4. Do the rollout:

- [ ] upload the new databases (referenced in `config_dbs.json`) to ITRB's SFTP server using the steps detailed [here](https://github.com/RTXteam/RTX/wiki/Config,-databases,-and-SFTP#uploading-databases-to-itrbs-sftp-server)
  - make sure to do this **before** proceeding with the below steps; this can be done well in advance of the actual roll-out (it doesn't hurt anything to do it early)
- [ ] merge `master` into `kg2integration`
- [ ] merge `kg2integration` into `master`
- [ ] roll `master` out to the various `arax.ncats.io` endpoints
- [ ] run the database manager
- [ ] run the pytest suite on the various endpoints
- [ ] verify each endpoint is running the new KG2 version by running the following JSON query and inspecting the returned node:
  - `{"nodes": {"n00": {"ids": ["RTX:KG2c"]}}, "edges": {}}`
- [ ] update our CI/CD testing instance with the new databases:
  - [ ] `ssh ubuntu@cicd.rtx.ai`
  - [ ] `cd RTX`
  - [ ] `git pull origin master`
  - [ ] `python3 code/ARAX/ARAXQuery/ARAX_database_manager.py --mnt --skip-if-exists --remove_unused`


##### 5. Final items/clean up:

- [ ] generate KGX files and upload them to the KGE Archive @acevedol
- [ ] turn off the old KG2c version's neo4j instance
- [ ] turn off the old KG2c version's plover instance
- [ ] turn off the new KG2pre version's neo4j instance
- [ ] upgrade the ITRB Plover endpoint (https://kg2cploverdb.ci.transltr.io) to this KG2 version and make the KG2 API start using it (instead of our self-hosted endpoint): 
    - [ ] update `kg_config.json` in the `main` branch of the Plover repo to point to the new `kg2c_lite_2.X.Y.json.gz` file (push this change)
    - [ ] wait about 45 minutes for the endpoint to rebuild and then run Plover tests to verify it's working
    - [ ] run the ARAX pytest suite with the NCATS endpoint plugged in (locally change the URL in `config_dbs.json` and set `force_local = True` in Expand)
    - [ ] if all tests pass, update `config_dbs.json` in `master` to point to the ITRB Plover endpoints (all maturity levels)
    - [ ] roll `master` out to the various endpoints on arax.ncats.io
    - [ ] turn off our plover endpoint and verify once more that ARAX is still working ok
