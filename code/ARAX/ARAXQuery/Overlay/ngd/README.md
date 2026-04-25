# NGD database builder

This directory builds `curie_to_pmids.sqlite`, the artifact ARAX uses to
compute Normalized Google Distance (NGD) between biomedical concepts. Each
row maps a canonical CURIE to the list of PubMed IDs whose articles mention
that concept.

## What it does

The builder runs in two stages:

1. **Concept extraction.** PubMed baseline + update XML files are parsed in
   parallel. From each article the builder pulls MeSH `DescriptorName`,
   chemical substance names (`NameOfSubstance`), gene symbols, and
   keywords. MeSH `QualifierName` is intentionally **not** extracted — see
   "Why qualifiers are excluded" below. Raw strings are normalized and
   validated by `extraction_script.py`, then written to an intermediate
   SQLite database (`conceptname_to_pmids.sqlite`) keyed by concept name.
2. **CURIE resolution + tier 0 edge harvest.** Two sources merge into the
   final database:
   - Every concept name from stage 1 is resolved to a canonical CURIE
     against a local Babel SQLite snapshot via
     `stitch_proj.local_babel.map_name_to_curie`.
   - When `--tier0-edges` is provided, every edge in the tier 0 KGX graph
     that carries `publications` contributes those PMIDs to **both** its
     subject and object CURIEs directly (no name resolution, since tier 0
     CURIEs are already canonical). This recovers the chemistry and
     protein coverage that PubMed-only resolution misses (PUBCHEM.COMPOUND,
     CHEBI, UniProtKB, etc.) and ensures CURIEs in `curie_to_pmids` align
     with tier 0's identifier space. Tier 0 nodes themselves do not carry
     a `publications` field, so only edges are scanned.

   PMIDs from both sources are deduplicated per CURIE and written to the
   final database (`curie_to_pmids.sqlite`).

No external API calls are made at build time. All resolution is local.

### Why qualifiers are excluded

MeSH headings are paired (`DescriptorName :: QualifierName`) — e.g.
`Aspirin :: adverse effects` means "this article is about adverse effects
of aspirin." The qualifier modifies the descriptor; it is not a standalone
concept. The previous version of this script extracted qualifiers
unpaired, sending strings like `"adverse effects"`, `"blood"`,
`"biosynthesis"` to the resolver as if they were biomedical entities.

Babel does name-matching, so those strings collide with real bioentities
that happen to share the name: `"blood"` resolves to `EMAPA:16332` (the
anatomical entity Blood), `"biosynthesis"` resolves to a specific
Reactome pathway, etc. PMIDs from articles that aren't biologically about
those entities then accumulate on legitimate-looking tier 0 CURIEs —
pollution that's invisible at the prefix level and silently corrupts NGD.
A scan of one PubMed baseline file (~30K articles) found 67 of 71
distinct qualifier strings resolve to such collision CURIEs.

Dropping qualifiers from extraction loses some signal but eliminates this
failure mode. Re-introduce them only with structured handling — e.g. as
qualifier-typed edges, not as standalone names sent through Babel.

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

End-to-end timing on a 24-vCPU box, with PubMed XML already on disk
(`--full --skip-download`):

| Stage | Time |
|---|---|
| PubMed XML parse (1410 files) | ~10 min |
| Stage-1 staging index + aggregation | ~33 min |
| Babel resolution of stage-1 names (~7.9M concepts) | ~4 min |
| Tier 0 edge harvest (29M edges, 6.9M with PMIDs) | ~1.5 min |
| Stage-2 staging index + aggregation | ~9 min |
| **Total (full build, skip-download)** | **~57 min** |

Add another 30-90 min if `--full` runs the PubMed mirror sync. A
resolve-only build (no `--full`) skips stages 1 entirely and finishes in
roughly 10-15 min.

## Prerequisites

Before running the build you need four things on disk:

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

### 4. Tier 0 KGX edges file (optional but strongly recommended)

A KGX-format `edges.jsonl` (or `.jsonl.gz`) for the tier 0 graph. Each
line is a JSON edge object with at least `subject`, `object`, and
`publications` (a list of `PMID:NNN` strings). When provided, every edge
with publications contributes its PMIDs to both endpoint CURIEs. Without
it, the resulting `curie_to_pmids.sqlite` covers only PubMed-name-resolved
CURIEs and overlap with tier 0 nodes will be poor (~5%).

Pass via `--tier0-edges` or `NGD_TIER0_EDGES`. The builder logs a warning
and continues if it isn't provided.

## Checking your setup

Before running a build, use `--test` to verify that all paths and
dependencies are correct. **Always do this before a real build** — a real
run will overwrite output databases.

```
# Resolve-only check:
python3 build_ngd_database.py --test \
    --babel-db /path/to/babel.sqlite \
    --tier0-edges /path/to/tier0/edges.jsonl

# Full build check:
python3 build_ngd_database.py --test --full \
    --babel-db /path/to/babel.sqlite \
    --pubmed-dir /path/to/pubmed \
    --tier0-edges /path/to/tier0/edges.jsonl

# Full build (skip download) check:
python3 build_ngd_database.py --test --full --skip-download \
    --babel-db /path/to/babel.sqlite \
    --pubmed-dir /path/to/pubmed \
    --tier0-edges /path/to/tier0/edges.jsonl
```

This checks that paths exist, dependencies are importable, and the
environment is ready. No data is read or written.

## Running the build

All paths must be passed explicitly via flags or env vars — there are no
hardcoded defaults.

```
python3 build_ngd_database.py --babel-db /path/to/babel.sqlite \
    --pubmed-dir /path/to/pubmed \
    --tier0-edges /path/to/tier0/edges.jsonl \
    [--output-dir /path/to/output] \
    [--full] [--skip-download]
```

`--output-dir` controls where the databases and logs are written. It
defaults to the script's own directory.

### Full build

A full build re-parses every PubMed XML file from scratch. Use this when
PubMed has new content, when the extraction rules have changed, or on a
machine that has never built before.

```
python3 build_ngd_database.py --full \
    --babel-db /path/to/babel.sqlite \
    --pubmed-dir /path/to/pubmed \
    --tier0-edges /path/to/tier0/edges.jsonl
```

This will incrementally sync the PubMed mirror with `wget -r -N` (only
downloading files newer than the local copy), parse every `.xml.gz` in
`baseline/` and `updatefiles/`, run the resolver, and harvest tier 0
edge publications. End-to-end timing on a 24-vCPU machine: ~57 min with
the PubMed mirror already in place; add 30-90 min for the wget sync.

If your PubMed mirror is already up to date and you want to skip the
network sync:

```
python3 build_ngd_database.py --full --skip-download \
    --babel-db /path/to/babel.sqlite \
    --pubmed-dir /path/to/pubmed \
    --tier0-edges /path/to/tier0/edges.jsonl
```

### Resolve-only build

If `conceptname_to_pmids.sqlite` already exists from a previous full build,
you can re-run just the resolver and tier 0 harvest — for example, after
upgrading the Babel snapshot or changing the tier 0 graph:

```
python3 build_ngd_database.py \
    --babel-db /path/to/babel.sqlite \
    --tier0-edges /path/to/tier0/edges.jsonl
```

This skips XML parsing entirely and finishes in ~10-15 min.

## Outputs

All output is written to `--output-dir` (defaults to this directory):

- **`curie_to_pmids.sqlite`** — the final artifact. Single table
  `curie_to_pmids(curie TEXT PRIMARY KEY, pmids TEXT)` where `pmids` is a
  JSON array of integer PMIDs.
- **`conceptname_to_pmids.sqlite`** — intermediate cache from stage 1.
  Single table `conceptname_to_pmids(concept_name TEXT PRIMARY KEY,
  pmids TEXT)` where `pmids` is a JSON array of `"PMID:NNN"` strings.
  Reused by subsequent resolve-only builds.
- **`ngdbuild.log`** — full run log, including per-stage timings, parse
  errors, and resolver progress.
- **`unrecognized_pubmed_concept_names.txt`** — every concept name from
  stage 1 that Babel could not resolve to a CURIE, sorted alphabetically.
  Useful for diagnosing coverage gaps. Regenerated on each resolve run.

## Verifying the build

`audit_ngd_db.py` runs structural, distributional, and sanity checks
against the final database. Run it after every build:

```
python3 audit_ngd_db.py --db /path/to/curie_to_pmids.sqlite
```

Check your setup first with `--test`:

```
python3 audit_ngd_db.py --db /path/to/curie_to_pmids.sqlite --test
```

Pass `--babel-db` to also run live name-resolution spot checks (confirms
that well-known entities like TP53, aspirin, and Alzheimer Disease made it
through the pipeline):

```
python3 audit_ngd_db.py --db /path/to/curie_to_pmids.sqlite \
    --babel-db /path/to/babel.sqlite
```

Pass `--concept-db` (and `--tier0-edges` if the builder used one) for
stage-1 vs stage-2 consistency checks and accountability tracing:

```
python3 audit_ngd_db.py --db /path/to/curie_to_pmids.sqlite \
    --concept-db /path/to/conceptname_to_pmids.sqlite \
    --babel-db /path/to/babel.sqlite \
    --tier0-edges /path/to/tier0/edges.jsonl \
    --trace-top 10
```

When `--tier0-edges` is provided, the consistency check accounts for
CURIEs that came from `edges.publications` (so the row count check no
longer warns spuriously about "more curies than concept names"), and the
accountability trace reports per-target tier 0 edge contributions
alongside the concept-name contributions — including the top predicates
that fed each CURIE's PMID list.

You can also trace using only tier 0 (no `--concept-db`/`--babel-db`):

```
python3 audit_ngd_db.py --db /path/to/curie_to_pmids.sqlite \
    --tier0-edges /path/to/tier0/edges.jsonl \
    --trace-top 10
```

The script exits non-zero if any hard-failure check fails. See
`python3 audit_ngd_db.py --help` for additional options.

## Concept normalization

`extraction_script.py` is the single place where raw PubMed strings are
cleaned and validated. `process_names(raw_names)` takes a list of strings
from one PubMed article and returns the cleaned, deduplicated, validated
concept names. Tune cleaning rules there rather than in the builder.

## Configuration summary

| Option | Flag | Env var | Default |
|---|---|---|---|
| PubMed mirror root | `--pubmed-dir` | `NGD_PUBMED_DIR` | *(required for `--full`)* |
| Babel sqlite path | `--babel-db` | `NGD_BABEL_DB` | *(required)* |
| Tier 0 KGX edges file | `--tier0-edges` | `NGD_TIER0_EDGES` | *(optional but strongly recommended)* |
| Output directory | `--output-dir` | `NGD_OUTPUT_DIR` | script directory |
| Full build | `--full` | — | off |
| Skip PubMed sync | `--skip-download` | — | off |
| Dry-run check | `--test` | — | off |
