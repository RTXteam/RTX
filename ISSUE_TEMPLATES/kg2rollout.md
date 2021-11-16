##### 1. Build and load KG2c:

- [ ] update the synonymizer's and BiolinkHelper's biolink version number (as applicable)
- [ ] build a synonymizer from the new KG2
- [ ] build a new KG2c
- [ ] load the new KG2c into neo4j at http://kg2-X-Yc.rtx.ai:7474/browser/
- [ ] upload the new `kg2c_lite_2.X.Y.json.gz` file to the [translator-lfs-artifacts](https://github.com/ncats/translator-lfs-artifacts/tree/main/files) repo
- [ ] load the new KG2c into plover (available at http://kg2-X-Ycplover.rtx.ai:9990)

##### 2. Rebuild downstream databases:

Copies of all of these should be put in `/data/orangeboard/databases/KG2.X.Y` on arax.ncats.io.

- [ ] configv2.json (should point to the new KG2/KG2c/plover)
    - note: save this as `config_local.json`, since we want it to be used over `configv2.json` during testing
- [ ] NodeSynonymizer
- [ ] KG2c meta knowledge graph
- [ ] KG2c sqlite
- [ ] KG2c TSV tarball
- [ ] KG2c neo4j dump (this is created on the neo4j hosting instance when loading KG2c, at `/home/ubuntu/kg2-build/kg2c.dump`)
- [ ] FDA-approved drugs pickle
- [ ] NGD database
- [ ] COHD database @chunyuma
- [ ] refreshed DTD @chunyuma
- [ ] DTD model @chunyuma _(may be skipped - depends on the KG2 version)_
- [ ] DTD database @chunyuma _(may be skipped - depends on the KG2 version)_
- [ ] 'slim' databases (used for Travis) @chunyuma / @finnagin

**NOTE**: As databases are rebuilt, the new copy of `config_local.json` will need to be updated to point to their new paths. However, if the rollout of KG2 has already occurred, then you should update the master `configv2.json` directly. 

##### 3. Update the ARAX codebase:

Associated code changes should go in the `kg2integration` branch.

- [ ] update Expand code as needed
- [ ] update any other modules as needed
- [ ] test everything together (entire ARAX pytest suite should pass when using the new `config_local.json` - must locally set `force_local = True` in `ARAX_expander.py` to avoid using the old KG2 API)
- [ ] update the ARAX, KG2, and Biolink version numbers in openapi yaml files @edeutsch

##### 4. Do the rollout:

- [ ] merge `master` into `kg2integration`
- [ ] merge `kg2integration` into `master`
- [ ] make `config_local.json` the new master config file on araxconfig.rtx.ai (rename it to `configv2.json`)
- [ ] roll `master` out to the various arax.ncats.io endpoints and delete their `configv2.json`s
- [ ] run the database manager
- [ ] run the pytest suite on the various endpoints

##### 5. Final items/clean up:

- [ ] update SmartAPI registration for KG2 @edeutsch
- [ ] update the test triples that go in some NCATS repo @finnagin
- [ ] rename the `config_local.json` on arax.ncats.io to `config_local.json_FROZEN_DO-NOT-EDIT-FURTHER` (any additional edits to the config file should be made directly to the master `configv2.json` on araxconfig.rtx.ai going forward)
- [ ] turn off the old KG2c version's neo4j instance
- [ ] turn off the old KG2pre version's neo4j instance
- [ ] turn off the old KG2 version's plover instance
- [ ] upgrade the NCATS-hosted Plover endpoint (https://kg2cploverdb.ci.transltr.io) to this KG2 version and make the KG2 API start using it (instead of our self-hosted endpoint): 
    - [ ] update `kg_config.json` in the `main` branch of the Plover repo to point to the new `kg2c_lite_2.X.Y.json.gz` file (push this change)
    - [ ] wait about 45 minutes for the endpoint to rebuild and then run Plover tests to verify it's working
    - [ ] run the ARAX pytest suite with the NCATS endpoint plugged in: use a `config_local.json` that points to it and locally set `force_local = True` in Expand
    - [ ] if all tests pass, update the master `configv2.json` on araxconfig.rtx.ai to point to this Plover endpoint
    - [ ] delete the arax.ncats.io `kg2` endpoint's `configv2.json` to force it to download the new copy and then verify it's working correctly by running a query
    - [ ] turn off our plover endpoint and verify once more that ARAX is still working ok