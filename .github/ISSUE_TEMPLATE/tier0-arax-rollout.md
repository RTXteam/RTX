---
name: ARAX rollout
about: Checklist for rolling out ARAX to Tier 0
title: "YYYYMMDD ARAX Rollout"
labels: ""
assignees: ""
---



- [ ] Build database file `curie_to_pmids_v1.0_tier0-MMDDYYYY.sqlite` (assignee: ; subissue: ) (build script: [`build_ngd_database.py`](https://github.com/RTXteam/RTX/blob/master/code/ARAX/ARAXQuery/Overlay/ngd/build_ngd_database.py))
- [ ] Build database file `autocomplete_v1.0_tier0-MMDDYYYY.sqlite` (assignee: ; subissue: ) (build script: [`create_load_db.py`](https://github.com/RTXteam/RTX/blob/master/code/autocomplete/create_load_db.py))
- [ ] Build database file `tier0-info-for-overlay_v1.0_tier0-MMDDYYYY.sqlite` (assignee: ; subissue: ) (build script: [`generate_sqlite.py`](https://github.com/RTXteam/RTX/blob/master/code/ARAX/KnowledgeSources/generate_sqlite.py))
- [ ] Build database file `curie_ngd_v1.0_tier0-MMDDYYYY.sqlite` (assignee: ; subissue: )
- [ ] Build database file `ExplainableDTD_v1.0_tier0-MMDDYYYY-all_with_paths.db` (assignee: ; subissue: )
- [ ] Update ARAX `config_dbs.json` for the new database files. (assignee: ; subissue: )
- [ ] Update `ARAX_database_manager.py` for the new database files. (assignee: ; subissue: )
- [ ] Stage all rebuilt Tier0 KG-based ARAX database files on the following servers: (assignee: ; subissue: )
    - [ ] `team-expander-USERNAME@sftp.transltr.io`
    - [ ] `ARAX-databases.rtx.ai`
    - [ ] `arax.ncats.io`
    - [ ] `CICD.rtx.ai`
- [ ] Trigger a Test Build of `issue-XXXX` branch on [cicd.rtx.ai](http://cicd.rtx.ai/); verify pytests are all passing (assignee: ; subissue: )
- [ ] Attempt to merge `master` branch into `issue-XXXX` branch (assignee: ; subissue: )
- [ ] Test the newly merged `issue-XXXX` branch (assignee: ; subissue: )
    - [ ] Run pytest suite on a development machine
    - [ ] Run ARAX flask server on a development machine; run all four example queries and inspect both the results _and_ the TRAPI message logs
    - [ ] Install the code on [arax.ncats.io/test](http://arax.ncats.io/test) and re-test there (check STDERR and make sure the Background Tasker is working)
- [ ] Tag head of master branch with the previous Tier0 version in case quick reverting is needed.
- [ ] Merge of the `issue-XXXX` branch to master; (assignee: ; subissue: ) (ideally, the following people would concur that we are ready, before we do this):
  - [ ] @hodgesf
  - [ ] @bazarkua
  - [ ] @saramsey
  - [ ] @dkoslicki
  - [ ] @edeutsch
- [ ] Roll out the new `master` branch to [arax.ncats.io/test](http://arax.ncats.io/test) and re-test everything (pytest, flask application, etc.)
- [ ] Test ARAX in ITRB CI to see if the auto-deployment worked
- [ ] Roll out the new `master` branch progressively to different [arax.ncats.io](http://arax.ncats.io/) endpoints, leaving _at least one legacy endpoint_


For a detailed guide on how to complete the above checklist, checkout the [Rollout Procedure Wiki](https://github.com/RTXteam/RTX/wiki/Rollout-Procedure#table-of-contents)
