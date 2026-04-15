# NGD database builder

This directory builds `curie_to_pmids.sqlite`, the artifact ARAX uses to
compute Normalized Google Distance (NGD) between biomedical concepts. Each
row maps a canonical CURIE to the list of PubMed IDs whose articles mention
that concept.

## What it does

The builder runs in two stages:

1. **Concept extraction.** PubMed baseline + update XML files are parsed in
   parallel. From each article the builder pulls MeSH descriptors and
   qualifiers, chemical substance names, gene symbols, and keywords. These
   raw strings are normalized and validated by `extraction_script.py`, then
   written to an intermediate SQLite database
   (`conceptname_to_pmids.sqlite`) keyed by concept name.
2. **CURIE resolution.** Every concept name is resolved to a canonical CURIE
   against a local Babel SQLite snapshot via
   `stitch_proj.local_babel.map_name_to_curie`. PMIDs are re-grouped by
   CURIE and written to the final database (`curie_to_pmids.sqlite`).

No external API calls are made at build time. All resolution is local.

## Recommended build environment

The full build is I/O- and CPU-heavy. The reference build host is:

| | |
|---|---|
| Instance | `m5a.8xlarge` (32 vCPU, 128 GB RAM) |
| OS | Ubuntu 22.04 LTS |
| Python | 3.12 |
| Disk | 400 GB free |
| RAM (full build) | 128 GB recommended, 64 GB minimum |
| RAM (resolve-only) | 32 GB |

## Prerequisites

Before running the build you need three things on disk:

### 1. Python environment

A virtualenv with `lxml` and `stitch_proj` installed. `stitch_proj` provides
the `local_babel` module the resolver depends on.

```
python3 -m venv venv
source venv/bin/activate
pip install lxml stitch_proj
```

### 2. Babel SQLite snapshot

A Babel SQLite file (e.g. `babel-20250901-p1.sqlite`). This is the
authoritative name → CURIE map used during stage 2. Place it anywhere on
the build host and either:

- pass its path on the command line with `--babel-db`, or
- export `NGD_BABEL_DB=/path/to/babel.sqlite`.

### 3. PubMed XML mirror

A local mirror of `ftp://ftp.ncbi.nlm.nih.gov/pubmed`. The builder can
fetch this for you (see "Full build" below), or you can pre-stage it. The
expected layout is:

```
<pubmed-dir>/
  ftp.ncbi.nlm.nih.gov/
    pubmed/
      baseline/
        pubmed25n0001.xml.gz
        ...
      updatefiles/
        pubmed25n1500.xml.gz
        ...
```

Point the builder at this directory with `--pubmed-dir` or
`NGD_PUBMED_DIR`.

## Running the build

From this directory:

```
python3 build_ngd_database.py [--full] [--skip-download] \
    [--pubmed-dir PATH] [--babel-db PATH]
```

### Full build

A full build re-parses every PubMed XML file from scratch. Use this when
PubMed has new content, when the extraction rules have changed, or on a
machine that has never built before.

```
python3 build_ngd_database.py --full
```

This will incrementally sync the PubMed mirror with `wget -r -N` (only
downloading files newer than the local copy), parse every `.xml.gz` in
`baseline/` and `updatefiles/`, then run the resolver. A full build on the
recommended instance takes around 2-3 hours end-to-end.

If your PubMed mirror is already up to date and you want to skip the
network sync:

```
python3 build_ngd_database.py --full --skip-download
```

### Resolve-only build

If `conceptname_to_pmids.sqlite` already exists from a previous full build,
you can re-run just the resolver — for example, after upgrading the Babel
snapshot:

```
python3 build_ngd_database.py
```

This skips XML parsing entirely and finishes in roughly an hour.

## Outputs

All output is written to this directory:

- **`curie_to_pmids.sqlite`** — the final artifact. Single table
  `curie_to_pmids(curie TEXT PRIMARY KEY, pmids TEXT)` where `pmids` is a
  JSON array of integer PMIDs.
- **`conceptname_to_pmids.sqlite`** — intermediate cache from stage 1.
  Single table `conceptname_to_pmids(concept_name TEXT PRIMARY KEY,
  pmids TEXT)` where `pmids` is a JSON array of `"PMID:NNN"` strings.
  Reused by subsequent resolve-only builds.
- **`ngdbuild.log`** — full run log, including per-stage timings, parse
  errors, and resolver progress.

## Concept normalization

`extraction_script.py` is the single place where raw PubMed strings are
cleaned and validated. `process_names(raw_names)` takes a list of strings
from one PubMed article and returns the cleaned, deduplicated, validated
concept names. Tune cleaning rules there rather than in the builder.

## Configuration summary

| Option | Flag | Env var | Default |
|---|---|---|---|
| PubMed mirror root | `--pubmed-dir` | `NGD_PUBMED_DIR` | `/home/hodgesf/Desktop/code/data/pubmed_xml_files` |
| Babel sqlite path | `--babel-db` | `NGD_BABEL_DB` | `/home/hodgesf/Desktop/code/data/babel-20250901-p1.sqlite` |
| Full build | `--full` | — | off |
| Skip PubMed sync | `--skip-download` | — | off |

The defaults are placeholders for the current development host. Always set
`--pubmed-dir` and `--babel-db` (or the equivalent env vars) on a new
machine.
