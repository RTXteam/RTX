# Tier0 ARAX Rollout Procedure


## Table of contents

- [Prerequisites](#prerequisites)
  - [SSH access](#ssh-access)
  - [Example ssh config for `arax.ncats.io`](#example-ssh-config-for-araxncatsio)
  - [GitHub access](#github-access)
  - [Slack workspaces](#slack-workspaces)
- [Phase 1 ; Set up (issue + branch)](#phase-1--kick-off-issue--branch)
- [Phase 2 ; Build artifacts](#phase-2--build-artifacts)
  - [`curie_to_pmids_v1.0_tier0-MMDDYYYY.sqlite`](#curie_to_pmids)
  - [`autocomplete_v1.0_tier0-MMDDYYYY.sqlite`](#autocomplete)
  - [`tier0-info-for-overlay_v1.0_tier0-MMDDYYYY.sqlite`](#tier0-info-for-overlay)
  - [`curie_ngd_v1.0_tier0-MMDDYYYY.sqlite`](#curie_ngd)
  - [xDTD refresh (PSU team)](#xdtd-refresh)
  - [gandalf_mmap tarball refresh (PSU team)](#gandalf_mmap-refresh)
  - [Artifacts reused as-is (version invariant)](#artifacts-reused-as-is)
- [Phase 3 ; Integration](#phase-3--integration)
- [Phase 4 ; Test on dev + CI](#phase-4--test-on-dev--ci)
- [Phase 5 ; Stage artifacts](#phase-5--stage-artifacts)
- [Phase 6 ; Merge to master](#phase-6--merge-to-master)
- [Phase 7 ; Production rollout](#phase-7--production-rollout)
- [Phase 8 ; Final cleanup](#phase-8--final-cleanup)
- [Rollback procedure](#rollback-procedure)
- [Copy-pasteable issue checklist](#copy-pasteable-issue-checklist)

---

## Prerequisites

### SSH access
To complete this workflow, you will need `ssh` access to:
- [ ] `arax-databases.rtx.ai` (Contact Oregon State team for access)
- [ ] `arax.ncats.io` (Contact ITRB, via `#devops-teamexpanderagent` on Slack for access)
- [ ] `team-expander-USERNAME@sftp.ncats.io` (Contact ITRB, via `#devops-teamexpanderagent` on Slack for access)
- [ ] `cicd.rtx.ai` (Contact Oregon State team for access)
- [ ] `ngdbuild2.rtx.ai` (Contact Oregon State team for access)
- [ ] `arax.rtx.ai` (Contact Oregon State team for access)

### GitHub access
- [ ] write access to the `RTXteam/RTX` project area

### Slack workspaces
You will also need access to the following Slack workspaces:
- [ ] ARAXTeam (subscribe to `#deployment`)
- [ ] NCATSTranslator (subscribe to `#devops-teamexpanderagent`)

### Example ssh config for `arax.ncats.io`

`arax.ncats.io` is reachable only via a bastion and enforces an IP allowlist ; if you're off-site, connect to the office VPN first. A typical `~/.ssh/config` entry looks like:

```
Host arax.ncats.io
    User YOUR_USERNAME
    ProxyCommand ssh -i ~/.ssh/id_rsa_long -W %h:%p YOUR_USERNAME@BASTION_IP
    IdentityFile ~/.ssh/id_rsa_long
    Hostname INTERNAL_IP
```

You'll have to get access through ITRB to both the bastion server and the endpoint server.

---

## Phase 1 ; Kick off (issue + branch)

The very first thing you should do when completing the Tier0 ARAX workflow is to make an issue in the RTX workspace, titled something along the lines of "Attempt to build ARAX Tier0-MMDDYYYY". Then, you should make note of the issue number, and make a branch titled `issue-XXXX`, where all the dev work to complete the workflow will be merged into for validation before pushing to master.

Here is a copy and pastable checklist to put into the issue, if that is helpful: 


## Copy-pasteable issue checklist

- [ ] Build database file `curie_to_pmids_v1.0_tier0-MMDDYYYY.sqlite` (assignee: ; subissue: ) (build script: [`build_ngd_database.py`](https://github.com/RTXteam/RTX/blob/master/code/ARAX/ARAXQuery/Overlay/ngd/build_ngd_database.py))
- [ ] Build database file `autocomplete_v1.0_tier0-MMDDYYYY.sqlite` (assignee: ; subissue: ) (build script: [`create_load_db.py`](https://github.com/RTXteam/RTX/blob/master/code/autocomplete/create_load_db.py))
- [ ] Build database file `tier0-info-for-overlay_v1.0_tier0-MMDDYYYY.sqlite` (assignee: ; subissue: ) (build script: [`generate_sqlite.py`](https://github.com/RTXteam/RTX/blob/master/code/ARAX/KnowledgeSources/generate_sqlite.py))
- [ ] Build database file `curie_ngd_v1.0_tier0-MMDDYYYY.sqlite` (assignee: ; subissue: )
- [ ] xDTD refresh work. Work with PSU team on this. (assignee: ; subissue: )
- [ ] gandalf_mmap tarball refresh work. Work with PSU team on this. (assignee: ; subissue: )
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



---

## Phase 2 ; Build artifacts

The following artifacts must be rebuilt against the new Tier0 graph. Typical assignees: OSU team for DB builds; PSU team for xDTD and gandalf_mmap.

<a id="curie_to_pmids"></a>
### `curie_to_pmids_v1.0_tier0-MMDDYYYY.sqlite`

**Purpose.** Maps canonical Tier0 CURIEs to the PubMed IDs they appear in. Consumed at runtime by the NGD (Normalized Google Distance) overlay to score concept co-occurrence.

**Build script.** [`code/ARAX/ARAXQuery/Overlay/ngd/build_ngd_database.py`](https://github.com/RTXteam/RTX/blob/master/code/ARAX/ARAXQuery/Overlay/ngd/build_ngd_database.py)

**Where to build.** Recommended: `ngdbuild2.rtx.ai` (Babel and the PubMed mirror are typically already staged there). You will need to download the most recent translatorkg files (tier0) from `KGX-storage.rtx.ai` If building elsewhere, see *Inputs* and *Local-build requirements* below.

#### Inputs (all paths can be passed as CLI flags or set as env vars)

| Flag | Env var | What it is |
|---|---|---|
| `--babel-db` | `NGD_BABEL_DB` | Path to the **local Babel SQLite** used for name → CURIE resolution. Babel replaces external API calls; the build must have read access to a current snapshot. |
| `--pubmed-dir` | `NGD_PUBMED_DIR` | Root for the local PubMed mirror. `wget -r` will populate `{pubmed-dir}/ftp.ncbi.nlm.nih.gov/pubmed/{baseline,updatefiles}/`. |
| `--tier0-edges` | `NGD_TIER0_EDGES` | Path to the Tier0 KGX `edges.jsonl` (or `.jsonl.gz`). The script harvests `edge.publications` PMIDs and attaches them to both endpoint CURIEs. **If you omit this, the build emits only PubMed-scrape-derived CURIEs and will be missing the Tier0 edge-publication overlap** ; the script logs a warning but does not fail. |
| `--output-dir` | `NGD_OUTPUT_DIR` | Directory for outputs and the `ngdbuild.log` log file. Defaults to the script's directory. |

#### Outputs

Two SQLite files are written to `--output-dir`:
- `conceptname_to_pmids.sqlite` ; intermediate; concept name → PMID list. Reused by no-flag mode.
- `curie_to_pmids.sqlite` ; Rename to `curie_to_pmids_v1.0_tier0-MMDDYYYY.sqlite` before staging.

Plus a diagnostic file:
- `unrecognized_pubmed_concept_names.txt` ; concept names Babel could not resolve. 

#### Modes

The script has two stages: **stage 1** parses PubMed XML → `conceptname_to_pmids.sqlite`, **stage 2** resolves names to CURIEs via Babel and merges in Tier0 edge publications → `curie_to_pmids.sqlite`. The flags decide which stages run:

1. **`--full`** ; both stages. Mirrors PubMed via `wget -r -N` (incremental; reuses any existing local copy), then parses, then resolves. Use when you want a fresh PubMed pull.
2. **`--full --skip-download`** ; both stages, but skips the `wget`. Use when you already have a local PubMed mirror at `--pubmed-dir` and want to re-parse it (e.g. after a parser change).
3. **No flags** ; stage 2 only. Requires an existing `conceptname_to_pmids.sqlite` in `--output-dir`. Use when re-resolving against a refreshed Babel or a new `--tier0-edges` without re-parsing PubMed.

#### Local-build requirements

If you can't use `ngdbuild2.rtx.ai`, you'll need locally:
1. A current Babel SQLite (~233 GB)
2. Enough disk for the PubMed mirror (~54 GB after `wget`; compressed `.xml.gz` files in `baseline/` + `updatefiles/`)
3. Disk for the build outputs and SQLite WAL (allow ~50 GB headroom)
4. ~64 GB RAM (the resolver worker pool scales with CPU count and holds a Babel connection per worker)
5. Python deps: `lxml`, plus `stitch_proj.local_babel` and `extraction_script` on `PYTHONPATH`


#### Stage and rename

```bash
mv /data/ngd-build/MMDDYYYY/curie_to_pmids.sqlite \
   curie_to_pmids_v1.0_tier0-MMDDYYYY.sqlite
```
Then stage to the servers listed in [Phase 5](#phase-5--stage-artifacts).

<a id="autocomplete"></a>
### `autocomplete_v1.0_tier0-MMDDYYYY.sqlite`

**Purpose.** Powers term-prefix and fuzzy autocomplete in the ARAX UI. The database is a flat list of every Tier0 node name + CURIE (case-insensitive), indexed for fast `LIKE` lookups.

**Build scripts.** Two scripts run in sequence:
1. [`code/autocomplete/extract_names_ids.py`](https://github.com/RTXteam/RTX/blob/master/code/autocomplete/extract_names_ids.py) ; Tier0 KGX `nodes.jsonl` → `id\tname` TSV
2. [`code/autocomplete/create_load_db.py`](https://github.com/RTXteam/RTX/blob/master/code/autocomplete/create_load_db.py) ; TSV → SQLite

**Where to build.** This one is light enough to run anywhere with access to the Tier0 `nodes.jsonl` ; laptop, dev VM, or `ngdbuild2.rtx.ai`. No Babel or PubMed needed.

#### Inputs

| Script | Flag | What it is |
|---|---|---|
| `extract_names_ids.py` | positional `input.jsonl` | Path to the Tier0 KGX **`nodes.jsonl`**. Each line must be a JSON object with at least `id` and `name`. Bad JSON lines are skipped silently. |
| `extract_names_ids.py` | positional `output.tsv` | Path for the intermediate TSV. The first line is a `id\tname` header; remaining lines are tab-separated `(node_id, name)` pairs with whitespace collapsed. |
| `create_load_db.py` | `-i / --input` | Path to the TSV produced above. **Note:** the loader expects `curie\tname` columns and skips the header automatically (any line with fewer than 2 tab-separated fields is dropped). |
| `create_load_db.py` | `-o / --output` | Output SQLite path. If the file already exists it is **deleted and recreated** ; the script does not append. The output directory will be created if missing. |

#### Outputs

A single SQLite file at `--output`. Schema:
- `terms(term VARCHAR(255) COLLATE NOCASE)` ; one row per unique (case-insensitive) name **and** one per CURIE. Indexed on `term`.
- `cached_fragments` and `cached_fragment_terms` ; empty tables populated at runtime by the autocomplete server for fuzzy/prefix caching. Do not pre-populate.

Rename the output to `autocomplete_v1.0_tier0-MMDDYYYY.sqlite` before staging.

#### Steps

```bash
cd /path/to/RTX/code/autocomplete

# 1. Extract id/name pairs from the Tier0 nodes file.
python3 extract_names_ids.py \
    /data/tier0/nodes.jsonl \
    /tmp/tier0-MMDDYYYY-names.tsv

# 2. Build the SQLite.
python3 create_load_db.py \
    -i /tmp/tier0-MMDDYYYY-names.tsv \
    -o /tmp/autocomplete_v1.0_tier0-MMDDYYYY.sqlite
```

If `nodes.jsonl` is gzipped, decompress (or stream-decompress) it first ; `extract_names_ids.py` opens the input as plain UTF-8 text and does not auto-handle `.gz`.

#### Local-build requirements

1. Read access to the Tier0 `nodes.jsonl` (typical Tier0 node files are on the order of a few GB uncompressed)
2. ~2× the node-file size in scratch disk for the intermediate TSV
3. A few hundred MB of disk for the output SQLite
4. Stock Python 3 ; no third-party deps beyond the standard library

#### Stage and rename

```bash
mv /tmp/autocomplete_v1.0_tier0-MMDDYYYY.sqlite \
   /path/to/staging/autocomplete_v1.0_tier0-MMDDYYYY.sqlite
```
Then stage to the servers listed in [Phase 5](#phase-5--stage-artifacts).


<a id="tier0-info-for-overlay"></a>
### `tier0-info-for-overlay_v1.0_tier0-MMDDYYYY.sqlite`

**Purpose.** A minimal, ARAX-Overlay-only view of the Tier0 graph. This is **not** a full ingest of Tier0 ; anything that needs complete node/edge properties should query Tier0/Gandalf directly. The database contains only what the Overlay modules need:
- `edge_publications` ; per-edge PMID list, keyed by canonical ARAX edge key. Used by NGD-style decoration.
- `neighbors` ; per-node neighbor counts grouped by expanded Biolink category. Used by `Overlay/fisher_exact_test.py`.
- `category_counts` ; node count per expanded Biolink category. Also used by Fisher Exact Test.

**Build script.** [`code/ARAX/KnowledgeSources/generate_sqlite.py`](https://github.com/RTXteam/RTX/blob/master/code/ARAX/KnowledgeSources/generate_sqlite.py)

**Where to build.** Anywhere with read access to the Tier0 conflated nodes + edges JSONL files. Edges are streamed line-by-line, but **nodes are loaded fully into memory** (and a parallel dict of expanded Biolink ancestor labels per node is built). Plan on a node-heavy memory footprint roughly proportional to the Tier0 node count × number of expanded categories per node.

#### Inputs

| Flag | What it is |
|---|---|
| `--nodes` | Path to the **conflated** Tier0 nodes JSONL. Each line is a JSON object with at least `id` and `category` (the `category` drives Biolink ancestor expansion that feeds the `neighbors` and `category_counts` tables). |
| `--edges` | Path to the **conflated** Tier0 edges JSONL. Each line is a JSON object with `subject`, `object`, `predicate`, `sources` (used to extract the primary knowledge source), optional `publications`, and optional qualifier fields (`qualified_predicate`, `object_direction_qualifier`, `object_aspect_qualifier`). Only edges with at least one publication contribute to `edge_publications`, but all edges contribute to neighbor counts. |
| `--output-dir` | Directory to write the SQLite file into. The script composes the filename itself; you do **not** pass a final file path. |
| `--tier0-build-date` | `YYYYMMDD` stamp that goes into the output filename. |
| `--schema-version` | Schema version embedded in the filename. Defaults to `1.0` ; leave it at `1.0` unless the schema in the script has actually changed. |
| `--biolink-version` | Biolink model version for category-ancestor expansion. **Defaults to whatever ARAX is currently pinned to** via `BiolinkHelper`. Override only if you need to test a future Biolink version against the build. |

#### Outputs

A single SQLite file written to:
```
{output-dir}/tier0-info-for-overlay_v{schema-version}_tier0-{tier0-build-date}.sqlite
```
So with the defaults and `--tier0-build-date 20260408`, you get `tier0-info-for-overlay_v1.0_tier0-20260408.sqlite` ; already in the staged-artifact name format. **No rename step required.** If the output file already exists, it is deleted and recreated.

Tables:
- `edge_publications(arax_edge_key TEXT PRIMARY KEY, publications TEXT)` ; `publications` is a `ǂ`-delimited (U+01C2) string of PMID identifiers. The `arax_edge_key` is constructed to exactly match `ARAXQuery/util.get_arax_edge_key()` ; if that helper changes shape, this builder must change too or downstream lookups will silently miss.
- `neighbors(id TEXT PRIMARY KEY, neighbor_counts TEXT)` ; `neighbor_counts` is a JSON object: `{expanded_biolink_label: count}`.
- `category_counts(category TEXT PRIMARY KEY, count INTEGER)` ; `count` is the number of Tier0 nodes whose expanded ancestor set includes `category`.

#### Steps

```bash
cd /path/to/RTX/code/ARAX/KnowledgeSources

python3 generate_sqlite.py \
    --nodes /data/tier0/nodes.jsonl \
    --edges /data/tier0/edges.jsonl \
    --output-dir /tmp/tier0-overlay-MMDDYYYY \
    --tier0-build-date MMDDYYYY
```

#### Local-build requirements

1. Read access to the conflated Tier0 `nodes.jsonl` + `edges.jsonl`
2. Enough RAM to hold all Tier0 nodes plus the expanded-Biolink-label dict simultaneously (allow ~16 GB headroom; scales with Tier0 node count)
3. `BiolinkHelper` import path must resolve ; the script appends `../BiolinkHelper` to `sys.path`, so run it from inside the repo's `code/ARAX/KnowledgeSources/` directory (or set `PYTHONPATH` accordingly)
4. The Biolink model files that `BiolinkHelper` needs must be locally available (typically already in the repo)



Copy the file directly to the servers listed in [Phase 5](#phase-5--stage-artifacts).

<a id="curie_ngd"></a>
### `curie_ngd_v1.0_tier0-MMDDYYYY.sqlite`

**Purpose.** Pre-computed normalized Google distance (NGD) values for CURIE pairs. Loaded by `ARAXQuery/Path_Finder/utility.py::get_curie_ngd_path` and consumed by `ARAX_connect.py` for the connect/path-finding step.

**Owner.** This artifact does not have an in-repo build script; it is built by the PSU team (typically by @mohsenht ; see the corresponding `Build CURIE NGD database` task in the kickoff issue). Coordinate the build with them as part of [Phase 2](#phase-2--build-artifacts) so it is ready in time for [Phase 5](#phase-5--stage-artifacts).

**What PSU needs from us.**
- The Tier0 build date stamp (so the filename matches).
- Confirmation of which Tier0 graph snapshot to compute over.
- The freshly built `curie_to_pmids_v1.0_tier0-MMDDYYYY.sqlite` (PSU uses this as input).

**Output filename.** `curie_ngd_v1.0_tier0-MMDDYYYY.sqlite` ; staged into the same directory on `arax-databases.rtx.ai` as the rest of the Tier0 artifacts. Someone will then neecd to copy this from `arax-databases.rtx.ai` to the other servers as listed in [Phase 5](#phase-5--stage-artifacts)

<a id="xdtd-refresh"></a>
### xDTD refresh (PSU team)

**Purpose.** The xDTD (Explainable Drug-Target Discovery) model and its `_with_paths` database power ARAX's drug-treats-disease inference. Refresh against the new Tier0 graph at every rollout so the model and its supporting paths reflect the current edges.

**Owner.** PSU team (typically @chunyuma). Track this work as a subissue under the kickoff issue.

**Expected outputs.**
- `ExplainableDTD_tier0-MMDDYYYY-all_with_paths.db` ; the paths database referenced by `config_dbs.json` and `ARAX_database_manager.py`.
- Any companion model files PSU normally ships alongside this DB (confirm with them which paths in `config_dbs.json` need updating).

 Someone will then neecd to copy this from `arax-databases.rtx.ai` to the other servers as listed in [Phase 5](#phase-5--stage-artifacts)

**Note.** xDTD may sometimes be "may be skipped ; depends on the changes in this Tier0 version" (per the prior KG2 workflow). Confirm with @chunyuma at the start of the rollout whether a full refresh is required or whether the previous artifact can be carried forward.


<a id="gandalf_mmap-refresh"></a>
### gandalf_mmap tarball refresh (PSU team)

**Purpose.** Memory-mapped tarball backing Gandalf-based lookups in `ARAXQuery/Path_Finder/utility.py::get_gandalf_mmap_path` and used by `ARAX_connect.py`. Must be rebuilt against the new Tier0 graph so node IDs and offsets line up.

**Owner.** PSU team. Track as a subissue.

**Expected output.** `gandalf_mmap.tar.gz` ; staged into the Tier0 artifact directory on `arax-databases.rtx.ai`. Note this filename does **not** carry a Tier0 date stamp; the staged copy is overwritten per rollout. Tag the previous version on `master` (per [Phase 6](#phase-6--merge-to-master)) before overwriting so a rollback can recover the prior artifact path.

 Someone will then neecd to copy this from `arax-databases.rtx.ai` to the other servers as listed in [Phase 5](#phase-5--stage-artifacts)

<a id="artifacts-reused-as-is"></a>
### Artifacts reused as-is (version invariant)
The following artifacts are version invariant and can be reused (meaning, **DO NOT** update the DB manager paths and all will work as expected):
- `fda_approved_drugs_v1.0_tier0-MMDDYYYY.pickle` ; if a new version of DrugBank is released, this file will need to be regenerated. Build script: [`code/ARAX/KnowledgeSources/generate_fda_pickle.py`](https://github.com/RTXteam/RTX/blob/master/code/ARAX/KnowledgeSources/generate_fda_pickle.py).
- `COHD_v1.0_KG2.8.0.db` ; carried forward unchanged. The KG2.8.0 stamp is historical; this file is not regenerated as part of a Tier0 rollout.

---

## Phase 3 ; Integration

All changes go on the `issue-XXXX` branch.

#### 3a. Update database paths

- [ ] Update `code/config_dbs.json` to point at each new Tier0 artifact:
  - [ ] `curie_to_pmids` path + version
  - [ ] `autocomplete` path + version
  - [ ] `tier0_info_for_overlay` path + version (key name may differ ; match what's in the file)
  - [ ] `curie_ngd` path + version
  - [ ] `xdtd` (ExplainableDTD) path + version
  - [ ] `gandalf_mmap` path
- [ ] Update `code/ARAX/ARAXQuery/ARAX_database_manager.py` if any artifact key names changed (paths themselves should flow from `config_dbs.json` via `RTXConfiguration`)
- [ ] Verify with a grep that no path elsewhere in the repo hardcodes a previous Tier0 date stamp

#### 3b. Bump API version numbers

If this rollout includes a TRAPI or ARAX version change, bump the version field (line ~12) in each of these OpenAPI specs. If it's a pure artifact refresh with no API surface change, you can skip this ; but confirm with @edeutsch.

- [ ] `code/UI/OpenAPI/python-flask-server/openapi_server/openapi/openapi.yaml`
- [ ] `code/UI/OpenAPI/python-flask-server/KG2/openapi_server/openapi/openapi.yaml`
- [ ] `code/UI/OpenAPI/specifications/export/ARAX/1.5.0/openapi.yaml`
- [ ] `code/UI/OpenAPI/specifications/export/KG2/1.5.0/openapi.yaml`

Also bump the `biolink-version` field in each if the Tier0 build was conflated against a new Biolink version. (Cross-check against `--biolink-version` used when building `tier0-info-for-overlay`.)

---

## Phase 4 ; Test on dev + CI

- [ ] Trigger a Test Build of `issue-XXXX` on [cicd.rtx.ai](http://cicd.rtx.ai/); verify the full pytest suite under `code/ARAX/test/` passes
- [ ] Attempt to merge `master` into `issue-XXXX`
- [ ] Re-test the merged `issue-XXXX` branch:
  - [ ] Run the `code/ARAX/test/` pytest suite on a development machine
  - [ ] Run the ARAX flask server on a development machine; run all four example queries (see the ARAX UI "Examples" menu) and inspect both the results **and** the TRAPI message logs
  - [ ] Install the code on [arax.ncats.io/test](http://arax.ncats.io/test) and re-test there ; check STDERR (`/tmp/RTX_OpenAPI_test.elog`) and confirm the Background Tasker is working
  - [ ] Smoke-check the Tier0 version is the one actually loaded ; pick a known Tier0-only CURIE (or version-stamped node) and confirm it resolves; inspect the Synonyms tab in the UI

---

## Phase 5 ; Stage artifacts

> **Before staging:** make sure `arax-databases.rtx.ai` and `arax.ncats.io` each have **≥100 GB free**. Delete the oldest Tier0 (or KG2) artifact directory if needed. **Notify `#deployment` on ARAXTeam Slack before deleting anything.**

The convention is to stage all rebuilt artifacts under `/home/rtxconfig/tier0-MMDDYYYY/` on `arax-databases.rtx.ai`, then push from there to the other servers.

#### 5a. Stage to `arax-databases.rtx.ai`
- [ ] `ssh rtxconfig@arax-databases.rtx.ai`
- [ ] `mkdir -m 777 /home/rtxconfig/tier0-MMDDYYYY` (or whatever directory naming convention you've agreed on)
- [ ] Copy every rebuilt artifact into that directory. Confirm filenames match the entries you put in `config_dbs.json`.

#### 5b. Push to `arax.ncats.io` (self-hosted dev endpoints)
The dev endpoints read from `/translator/data/orangeboard/databases/`. Example:
- [ ] `ssh myuser@arax.ncats.io`
- [ ] Enter the `rtx1` container: `sudo docker exec -it rtx1 bash`
- [ ] Become user `rt`: `su - rt`
- [ ] `cd /translator/data/orangeboard/databases/`
- [ ] `mkdir -m 777 tier0-MMDDYYYY`
- [ ] `scp rtxconfig@arax-databases.rtx.ai:/home/rtxconfig/tier0-MMDDYYYY/* tier0-MMDDYYYY/`

> **Off-site note.** `arax.ncats.io` enforces IP allowlisting. If you're off-site you must be on the office VPN for the `ssh` step to succeed.

#### 5c. Upload to ITRB SFTP (production)
- [ ] Upload all artifacts and their MD5 checksums to `team-expander-USERNAME@sftp.transltr.io` following the [Config, databases, and SFTP wiki page](https://github.com/RTXteam/RTX/wiki/Config,-databases,-and-SFTP#steps-for-all-databases-at-once)

#### 5d. Push to `cicd.rtx.ai`
- [ ] `ssh ubuntu@cicd.rtx.ai`
- [ ] `cd RTX && git pull origin issue-XXXX` (or whichever branch the build is on)
- [ ] `sudo mkdir -m 777 /mnt/data/orangeboard/databases/tier0-MMDDYYYY`
- [ ] `~/venv3.9/bin/python3 code/ARAX/ARAXQuery/ARAX_database_manager.py --mnt --skip-if-exists --remove_unused`
- [ ] Run a [Test Build](https://github.com/RTXteam/RTX/actions/workflows/pytest.yml) through GitHub Actions; all non-skipped pytest tests should pass.

---

## Phase 6 ; Merge to master

- [ ] Tag head of `master` with the previous Tier0 version stamp (e.g. `tier0-PREVIOUS_MMDDYYYY`) **before merging** ; this is the rollback anchor (see [Rollback procedure](#rollback-procedure)).
- [ ] Merge `master` into `issue-XXXX` once more (catch any drift since Phase 4), record the issue number in the merge message.
- [ ] Merge `issue-XXXX` into `master`. Ideally, the following people concur before merging:
  - [ ] @hodgesf
  - [ ] @bazarkua
  - [ ] @saramsey
  - [ ] @dkoslicki
  - [ ] @edeutsch

---

## Phase 7 ; Production rollout

### 7a. Roll `master` to the `arax.ncats.io` dev endpoints

**Notify `#deployment` on ARAXTeam Slack before each endpoint rollout.** Include the Tier0 build date stamp.

- [ ] If off-site, connect to the office VPN.
- [ ] `ssh arax.ncats.io` (requires the ssh config from [Prerequisites](#prerequisites))
- [ ] Enter the `rtx1` container: `sudo docker exec -it rtx1 bash`
- [ ] Become user `rt`: `su - rt`
- [ ] `cd /mnt/data/orangeboard/ENDPOINT/RTX`
- [ ] Confirm on `master`: `git branch` → should show `* master`
- [ ] `git stash` (preserve any local edits ; **important**)
- [ ] `git pull origin master`
- [ ] `git stash pop`
- [ ] If `requirements.txt` changed: `pip3 install -r code/requirements.txt`
- [ ] Become superuser: `exit` (back to root)
- [ ] `service RTX_OpenAPI_ENDPOINT restart`
- [ ] `tail -f /tmp/RTX_OpenAPI_ENDPOINT.elog` ; watch startup for errors; confirm Background Tasker initializes
- [ ] In the browser UI, run the four ARAX example queries against this endpoint and verify results + TRAPI logs
- [ ] Verify the Tier0 version actually loaded ; run a known Tier0-only test query

After all dev endpoints are up:
- [ ] On each endpoint, inside the `rtx1` container: `cd /mnt/data/orangeboard/EEE/RTX/code/ARAX/test && pytest -v`

### 7b. Verify ITRB CI auto-deployment
- [ ] Check that ITRB CI auto-deployed the new `master`. Hit the CI ARAX endpoint and run a Tier0 verification query.
- [ ] Run the full pytest suite against the CI endpoint and confirm green.

### 7c. Progressive production rollout
- [ ] Roll the new `master` to the `arax.ncats.io` production endpoints **one at a time**, smoke-testing after each.
- [ ] **Leave at least one legacy endpoint on the previous Tier0 build** until the new build has been stable in production for at least one week.

---

## Phase 8 ; Final cleanup

- [ ] Update the current RTX GitHub changelog issue ; add an entry for this Tier0 rollout (date, build stamp, summary of what changed).
- [ ] Delete the `issue-XXXX` branch in the RTX repo (it has been merged into `master`).
- [ ] After the one-week stability window: cut the last legacy endpoint over to the new build.
- [ ] After the one-week stability window: delete the previous Tier0 artifact directory from `arax-databases.rtx.ai` and `arax.ncats.io` to reclaim disk. **Notify `#deployment` first.** Do **not** delete the ITRB SFTP copy of the previous build until the rollout after the next.
- [ ] Close the rollout issue with a short retro: what went well, what didn't, what to change next time.

---

## Rollback procedure

If the new build misbehaves after rollout:

1. **Identify the last-known-good tag.** This is the tag created in Phase 6 (head of `master` immediately before the Tier0 merge).
2. **Revert the production endpoint(s).** Redeploy the tagged commit to the affected `arax.ncats.io` endpoint(s) following the same `git stash → git checkout <tag> → service restart` procedure as Phase 7a. The legacy endpoint kept in Phase 7c should remain untouched and can absorb traffic while the others roll back.
3. **Restore DB manager paths.** If `config_dbs.json` and/or `ARAX_database_manager.py` were already updated to point at Tier0 artifacts, revert those changes on `master` (or hot-fix the deployed copy) so the rolled-back code finds the previous artifacts.
4. **Confirm the artifacts the rolled-back code expects are still present** on `arax-databases.rtx.ai` and the ITRB SFTP ; do **not** delete the previous Tier0 build's artifacts until the new build has been stable in production for at least one week.
5. **Notify `#deployment` on ARAXTeam Slack** and update the rollout issue with what failed and why.

---
