##### 1. Build and load KG2c:

- [ ] build a synonymizer from the new KG2
- [ ] build a new KG2c (neo4j available at http://kg2-X-Yc.rtx.ai:7474/browser/)
- [ ] load it into plover (available at http://kg2-X-Ycplover.rtx.ai:9990)

##### 2. Rebuild downstream databases:

Copies of all of these should be put in `/data/orangeboard/databases/KG2.X.Y` on arax.ncats.io.

- [ ] configv2.json (should point to the new KG2/KG2c/plover)
    - note: save this as `config_local.json`, since we want it to be used over `configv2.json` during testing
- [ ] NodeSynonymizer
- [ ] KG2c meta knowledge graph
- [ ] KG2c sqlite
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

- [ ] update the Biolink version number and KG2 version number in the openapi yaml @edeutsch?
- [ ] update Expand code as needed
- [ ] update any other modules as needed
- [ ] test everything together (entire ARAX pytest suite should pass when using the new `config_local.json` - must locally set `force_local = True` in `ARAX_expander.py` to avoid using the old KG2 API)

##### 4. Do the rollout:

- [ ] merge `master` into `kg2integration`
- [ ] merge `kg2integration` into `master`
- [ ] make `config_local.json` the new master config file on araxconfig.rtx.ai
- [ ] roll `master` out to the various arax.ncats.io endpoints and delete their `configv2.json`s
- [ ] run the pytest suite on the various endpoints

##### 5. Final items:

- [ ] update SmartAPI registration for ARAX @edeutsch
- [ ] update the test triples that go in some NCATS repo @finnagin
- [ ] rename the `config_local.json` on arax.ncats.io to `config_local.json_FROZEN_DO-NOT-EDIT-FURTHER` (any additional edits to the config file should be made directly to the master `configv2.json` on araxconfig.rtx.ai going forward)