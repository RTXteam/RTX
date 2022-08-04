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
    - [ ] make sure there is enough disk space available on `arax.ncats.io` (need at least 80G, ideally >100G). delete old KG2 database directories from `/data/orangeboard/databases` as needed (warn the team on Slack in advance).
    - [ ] make sure to choose to build a new synonymizer in `kg2c_config.json`, as described in the how-to
  - [ ] after the build is done, verify it looks ok:
    - [ ] the 'build node' (node with ID `RTX:KG2c`) has the expected version number (KG2.X.Y)
    - [ ] `node_synonymizer.sqlite` should be around 15-20 GB
    - [ ] make sure `node_synonymizer.sqlite`'s last modified date is today (or whatever day the build was run)
    - [ ] make sure `kg2c_lite.json.gz`'s last modified date is today (or whatever day the build was run)
    - [ ] the entire build process (synonymizer + KG2c) shouldn't have taken more than ~24 hours
    - [ ] the synonymizer and KG2c artifacts should have been auto-uploaded into the proper directory on `arax.ncats.io` (`/data/orangeboard/databases/KG2.X.Y`)
- [ ] load the new KG2c into neo4j at http://kg2-X-Yc.rtx.ai:7474/browser/ (how to is [here](https://github.com/RTXteam/RTX/tree/master/code/kg2c#host-kg2canonicalized-in-neo4j))
  - [ ] copy the auto-generated KG2c dump from the Neo4j-hosting instance to `arax.ncats.io` like so:
    - `scp /home/ubuntu/kg2-build/kg2c.dump rtxconfig@arax.ncats.io:/data/orangeboard/databases/KG2.X.Y/extra_files`
- [ ] upload the new `kg2c_lite_2.X.Y.json.gz` file to the [translator-lfs-artifacts](https://github.com/ncats/translator-lfs-artifacts/tree/main/files) repo
- [ ] load the new KG2c into Plover (available at http://kg2-X-Ycplover.rtx.ai:9990)


##### 2. Initiate a config_local.json for this KG2 version

- [ ] create a copy of the current master `configv2.json` and name it `config_local.json`:
  - `scp araxconfig@araxconfig.rtx.ai:/home/araxconfig/configv2.json ./config_local.json`
- [ ] then update that `config_local.json` in the following places (note that its structure is repetitive; please update all instances of each):
  - [ ] the new KG2pre Neo4j
  - [ ] the new KG2c Neo4j
  - [ ] the paths to each of the database files that are on `arax.ncats.io` in the `/data/orangeboard/databases/KG2.X.Y` directory thus far (excluding any subdirectories)
    - [ ] while doing this, please rename each such database file so that it is in this kind of format: `mydatabase_v1.0_KG2.X.Y.sqlite`
  - [ ] the new Plover
- [ ] put this new `config_local.json` into `/data/orangeboard/databases/KG2.X.Y` on `arax.ncats.io`
  

##### 3. Rebuild downstream databases:

The following databases should be rebuilt and copies of them should be put in `/data/orangeboard/databases/KG2.X.Y` on `arax.ncats.io`. Please use this kind of naming format: `mydatabase_v1.0_KG2.X.Y.sqlite`.

- [ ] NGD database
- [ ] COHD database @chunyuma
- [ ] refreshed DTD @chunyuma
- [ ] DTD model @chunyuma _(may be skipped - depends on the KG2 version)_
- [ ] DTD database @chunyuma _(may be skipped - depends on the KG2 version)_
- [ ] XDTD database

**NOTE**: As databases are rebuilt, the new copy of `config_local.json` will need to be updated to point to their new paths! However, if the rollout of this KG2 version has already occurred, then you should update the master `configv2.json` directly. 


##### 4. Update the ARAX codebase:

All code changes should **go in the `kg2integration` branch**!

- [ ] regenerate the new test triples file and push it to `RTX/code/ARAX/KnowledgeSources/RTX_KG2c_test_triples.json` @acevedol
- [ ] update Expand code as needed
- [ ] update any other modules as needed
- [ ] test everything together:
  - [ ] locally set `force_local = True` in `ARAX_expander.py` (to avoid using the old KG2 API)
  - [ ] download the new `config_local.json`:
    - `scp rtxconfig@arax.ncats.io:/data/orangeboard/databases/KG2.X.Y/config_local.json [your_local_path_to_repo_clone]/RTX/code`
  - [ ] then run the entire ARAX pytest suite
  - [ ] address any failing tests
- [ ] update the KG2 and ARAX version numbers in the appropriate places (`openapi.yaml`, etc.) @edeutsch
  - [ ] Bump version for `RTX/code/UI/OpenAPI/python-flask-server/openapi_server/openapi/openapi.yaml` in line 12 (`version:`); the major and minor release numbers are kept synchronous with the TRAPI version; just bump the patch release version (least significant digit)
  - [ ] Bump version for `RTX/code/UI/OpenAPI/python-flask-server/KG2/openapi_server/openapi/openapi.yaml` in line 12 (`version:`); the first three digits are kept synchronous with the KG2 release version
  - [ ] Bump version number in `RTX/code/UI/OpenAPI/python-flask-server/RTX_OA3_TRAPI1.2_ARAX.yaml` on line 4 (`version:`); same as for the ARAX `openapi.yaml` file
  - [ ] Bump version number in `RTX/code/UI/OpenAPI/python-flask-server/RTX_OA3_TRAPI1.2_KG2.yaml` on line 4 (`version:`); same as for the KG2 `openapi.yaml` file

  
##### 5. Do the rollout:

- [ ] merge `master` into `kg2integration`
- [ ] merge `kg2integration` into `master`
- [ ] make `config_local.json` the new master config file on `araxconfig.rtx.ai` (rename it to `configv2.json`)
- [ ] roll `master` out to the various `arax.ncats.io` endpoints and delete their `configv2.json`s
- [ ] run the database manager
- [ ] run the pytest suite on the various endpoints
- [ ] update the CI/CD instance:
  - [ ] replace the `configv2.json` file on `cicd.rtx.ai` with the new one
  - [ ] download the new database files to `cicd.rtx.ai`


##### 6. Final items/clean up:

- [ ] generate KGX files and upload them to the KGE Archive @acevedol
- [ ] update the KG2c test triples that go in the [NCATS Testing repo](https://github.com/NCATSTranslator/testing/tree/main/onehop/test_triples/KP/Expander_Agent) (generate with [this script](https://github.com/RTXteam/RTX/blob/master/code/ARAX/KnowledgeSources/create_csv_of_kp_predicate_triples.py), using the new `config_local.json`) @acevedol
- [ ] rename the `config_local.json` on arax.ncats.io to `config_local.json_FROZEN_DO-NOT-EDIT-FURTHER` (any additional edits to the config file should be made directly to the master `configv2.json` on araxconfig.rtx.ai going forward)
- [ ] turn off the old KG2c version's neo4j instance
- [ ] turn off the old KG2c version's plover instance
- [ ] turn off the new KG2pre version's neo4j instance
- [ ] upgrade the NCATS-hosted Plover endpoint (https://kg2cploverdb.ci.transltr.io) to this KG2 version and make the KG2 API start using it (instead of our self-hosted endpoint): 
    - [ ] update `kg_config.json` in the `main` branch of the Plover repo to point to the new `kg2c_lite_2.X.Y.json.gz` file (push this change)
    - [ ] wait about 45 minutes for the endpoint to rebuild and then run Plover tests to verify it's working
    - [ ] run the ARAX pytest suite with the NCATS endpoint plugged in: use a `config_local.json` that points to it and locally set `force_local = True` in Expand
    - [ ] if all tests pass, update the master `configv2.json` on araxconfig.rtx.ai to point to this Plover endpoint
    - [ ] delete the arax.ncats.io `kg2` endpoint's `configv2.json` to force it to download the new copy and then verify it's working correctly by running a query
    - [ ] turn off our plover endpoint and verify once more that ARAX is still working ok
