_NOTE: To create a new issue based on this template, simply go to: https://github.com/RTXteam/RTX/issues/new?template=kg2rollout.md_

##### 1. Build and load KG2c:

- [ ] merge `master` into the `kg2integration` branch
- [ ] update the four hardcoded biolink version numbers in the `kg2integration` branch (as needed):
  - [ ] in [code/UI/OpenAPI/python-flask-server/openapi_server/openapi/openapi.yaml](../code/UI/OpenAPI/python-flask-server/openapi_server/openapi/openapi.yaml)
  - [ ] in [code/UI/OpenAPI/python-flask-server/KG2/openapi_server/openapi/openapi.yaml](../code/UI/OpenAPI/python-flask-server/KG2/openapi_server/openapi/openapi.yaml)
  - [ ] in [code/UI/OpenAPI/python-flask-server/RTX_OA3_TRAPI1.2_ARAX.yaml](../code/UI/OpenAPI/python-flask-server/RTX_OA3_TRAPI1.2_ARAX.yaml)
  - [ ] in [code/UI/OpenAPI/python-flask-server/RTX_OA3_TRAPI1.2_KG2.yaml](../code/UI/OpenAPI/python-flask-server/RTX_OA3_TRAPI1.2_KG2.yaml)
- [ ] build a new KG2c on `buildkg2c.rtx.ai` from the `kg2integration` branch (how-to is [here](https://github.com/RTXteam/RTX/tree/master/code/kg2c#build-kg2canonicalized))
  - [ ] make sure there is enough disk space available on `arax.ncats.io` (need at least 80G, ideally >100G). delete old KG2 database directories from `/data/orangeboard/databases` as needed (warn the team on Slack in advance).
  - [ ] make sure to choose to build a new synonymizer in `kg2c_config.json`, as described in the how-to
  - [ ] verify the build looks ok:
    - [ ] the synonymizer sqlite should be around 15-20 GB
    - [ ] the entire build process (synonymizer + KG2c) shouldn't have taken more than ~24 hours
    - [ ] the synonymizer and KG2c artifacts should have been auto-uploaded into the proper directory on `arax.ncats.io` (`/data/orangeboard/databases/KG2.X.Y`)
- [ ] load the new KG2c into neo4j at http://kg2-X-Yc.rtx.ai:7474/browser/ (how to is [here](https://github.com/RTXteam/RTX/tree/master/code/kg2c#host-kg2canonicalized-in-neo4j))
- [ ] upload the new `kg2c_lite_2.X.Y.json.gz` file to the [translator-lfs-artifacts](https://github.com/ncats/translator-lfs-artifacts/tree/main/files) repo
- [ ] load the new KG2c into plover (available at http://kg2-X-Ycplover.rtx.ai:9990)

##### 2. Rebuild downstream databases:

Copies of all of these should be put in `/data/orangeboard/databases/KG2.X.Y` on arax.ncats.io.

- [ ] configv2.json (should point to the new KG2pre/KG2c/plover)
    - note: save this as `config_local.json`, since we want it to be used over `configv2.json` during testing
- [ ] NodeSynonymizer
- [ ] KG2c meta knowledge graph
- [ ] KG2c sqlite
- [ ] KG2c TSV tarball
- [ ] KG2c neo4j dump (this is created on the neo4j hosting instance when loading KG2c, at `/home/ubuntu/kg2-build/kg2c.dump`)
- [ ] FDA-approved drugs pickle
- [ ] autocomplete sqlite
- [ ] NGD database
- [ ] COHD database @chunyuma
- [ ] refreshed DTD @chunyuma
- [ ] DTD model @chunyuma _(may be skipped - depends on the KG2 version)_
- [ ] DTD database @chunyuma _(may be skipped - depends on the KG2 version)_

**NOTE**: As databases are rebuilt, the new copy of `config_local.json` will need to be updated to point to their new paths. However, if the rollout of KG2 has already occurred, then you should update the master `configv2.json` directly. 

##### 3. Update the ARAX codebase:

All code changes should go in the `kg2integration` branch.

- [ ] update Expand code as needed
- [ ] update any other modules as needed
- [ ] test everything together (entire ARAX pytest suite should pass when using the new `config_local.json` - must locally set `force_local = True` in `ARAX_expander.py` to avoid using the old KG2 API)
- [ ] update the KG2 and ARAX version numbers in the appropriate places (`openapi.yaml`, etc.) @edeutsch

##### 4. Do the rollout:

- [ ] merge `master` into `kg2integration`
- [ ] merge `kg2integration` into `master`
- [ ] make `config_local.json` the new master config file on `araxconfig.rtx.ai` (rename it to `configv2.json`)
- [ ] roll `master` out to the various `arax.ncats.io` endpoints and delete their `configv2.json`s
- [ ] run the database manager
- [ ] run the pytest suite on the various endpoints
- [ ] update the CI/CD instance:
  - [ ] replace the `configv2.json` file on `cicd.rtx.ai` with the new one
  - [ ] download the new database files to `cicd.rtx.ai`

##### 5. Final items/clean up:

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
