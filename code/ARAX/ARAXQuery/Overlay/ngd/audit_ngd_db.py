#!/usr/bin/env python3
"""
Audit curie_to_pmids.sqlite.

Runs a series of structural, distributional, and sanity checks against the
final NGD database artifact and prints a report. Exits non-zero if any
hard-failure check fails.

Usage:
    python3 audit_ngd_db.py
    python3 audit_ngd_db.py --db path/to/curie_to_pmids.sqlite
    python3 audit_ngd_db.py --sample 10000        # scan only first 10k rows
    python3 audit_ngd_db.py --count-unique-pmids  # also compute global unique pmids (memory heavy)
    python3 audit_ngd_db.py --babel-db path/to/babel.sqlite  # semantic checks + label enrichment
"""
import argparse
import json
import multiprocessing
import os
import sqlite3
import statistics
import sys
import time
from collections import Counter, defaultdict



# ---------------------------------------------------------------------------
# Report helper
# ---------------------------------------------------------------------------
class Report:
    def __init__(self):
        self.failures = 0
        self.warnings = 0

    def header(self, title):
        print()
        print("=" * 72)
        print(title)
        print("=" * 72)

    def ok(self, label, detail=""):
        print(f"  [OK]   {label}" + (f": {detail}" if detail else ""))

    def fail(self, label, detail=""):
        self.failures += 1
        print(f"  [FAIL] {label}" + (f": {detail}" if detail else ""))

    def warn(self, label, detail=""):
        self.warnings += 1
        print(f"  [WARN] {label}" + (f": {detail}" if detail else ""))

    def info(self, label, detail=""):
        print(f"  [INFO] {label}" + (f": {detail}" if detail else ""))


def human(n):
    return f"{n:,}"


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------
def check_file(report, path):
    report.header("File & schema")
    if not os.path.exists(path):
        report.fail("file exists", path)
        return False
    size_mb = os.path.getsize(path) / (1024 * 1024)
    report.ok("file exists", f"{path} ({size_mb:,.1f} MB)")
    return True


def check_schema(report, conn):
    cur = conn.cursor()
    tables = [r[0] for r in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )]
    report.info("tables", ", ".join(tables))

    if "curie_to_pmids" not in tables:
        report.fail("curie_to_pmids table", "missing")
        return False

    schema = list(cur.execute("PRAGMA table_info(curie_to_pmids)"))
    cols = {row[1]: row[2].upper() for row in schema}
    if cols != {"curie": "TEXT", "pmids": "TEXT"}:
        report.fail("schema", f"got {cols}")
    else:
        report.ok("schema", "curie TEXT PK, pmids TEXT")
    return True


def check_indexes(report, conn):
    cur = conn.cursor()
    idx = list(cur.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type='index' AND tbl_name='curie_to_pmids'"
    ))
    if not idx:
        report.info("indexes", "PRIMARY KEY only (implicit)")
    else:
        report.info("indexes", ", ".join(r[0] for r in idx))


def check_counts(report, conn):
    report.header("Row counts")
    cur = conn.cursor()
    (n_curies,) = cur.execute("SELECT COUNT(*) FROM curie_to_pmids").fetchone()
    report.info("curies", human(n_curies))

    (n_distinct,) = cur.execute(
        "SELECT COUNT(DISTINCT curie) FROM curie_to_pmids"
    ).fetchone()
    if n_distinct == n_curies:
        report.ok("curie uniqueness", f"{human(n_distinct)} distinct")
    else:
        report.fail("curie uniqueness",
                    f"{n_curies} rows, {n_distinct} distinct")

    (n_null,) = cur.execute(
        "SELECT COUNT(*) FROM curie_to_pmids WHERE curie IS NULL OR curie=''"
    ).fetchone()
    if n_null:
        report.fail("null/empty curies", human(n_null))
    else:
        report.ok("null/empty curies", "none")

    return n_curies


def scan_all_rows(report, conn, sample_limit=None, count_unique_pmids=False):
    """Full scan: parse JSON, validate types, accumulate stats."""
    report.header("PMID list validation (full scan)")
    cur = conn.cursor()

    bad_json = 0
    bad_type_rows = 0
    empty_lists = 0
    nonpos_rows = 0
    dup_within_rows = 0
    lengths = []
    prefix_counter = Counter()
    total_pmid_refs = 0
    pmid_min = None
    pmid_max = None
    unique_pmids = set() if count_unique_pmids else None

    query = "SELECT curie, pmids FROM curie_to_pmids"
    if sample_limit:
        query += f" LIMIT {int(sample_limit)}"

    start = time.perf_counter()
    n_scanned = 0
    for curie, pmids_json in cur.execute(query):
        n_scanned += 1

        if ":" in curie:
            prefix_counter[curie.split(":", 1)[0]] += 1
        else:
            prefix_counter["(no-prefix)"] += 1

        try:
            pmids = json.loads(pmids_json)
        except Exception:
            bad_json += 1
            continue

        if not isinstance(pmids, list):
            bad_type_rows += 1
            continue

        if len(pmids) == 0:
            empty_lists += 1
            continue

        # type + value + dup check
        seen_local = set()
        row_bad_type = False
        row_nonpos = False
        row_dup = False
        for p in pmids:
            if not isinstance(p, int) or isinstance(p, bool):
                row_bad_type = True
                break
            if p <= 0:
                row_nonpos = True
                break
            if p in seen_local:
                row_dup = True
            seen_local.add(p)
        if row_bad_type:
            bad_type_rows += 1
            continue
        if row_nonpos:
            nonpos_rows += 1
            continue
        if row_dup:
            dup_within_rows += 1

        n = len(pmids)
        lengths.append(n)
        total_pmid_refs += n

        rmin = min(pmids)
        rmax = max(pmids)
        if pmid_min is None or rmin < pmid_min:
            pmid_min = rmin
        if pmid_max is None or rmax > pmid_max:
            pmid_max = rmax

        if unique_pmids is not None:
            unique_pmids.update(pmids)

    elapsed = time.perf_counter() - start
    report.info("rows scanned", f"{human(n_scanned)} in {elapsed:.1f}s")

    if bad_json:
        report.fail("JSON parse", f"{human(bad_json)} rows unparseable")
    else:
        report.ok("JSON parse", "all rows valid JSON")

    if bad_type_rows:
        report.fail("pmid element types", f"{human(bad_type_rows)} rows have non-int elements")
    else:
        report.ok("pmid element types", "all ints")

    if empty_lists:
        report.fail("empty pmid lists", human(empty_lists))
    else:
        report.ok("empty pmid lists", "none")

    if nonpos_rows:
        report.fail("non-positive pmids", f"{human(nonpos_rows)} rows")
    else:
        report.ok("non-positive pmids", "none")

    if dup_within_rows:
        report.warn("duplicate pmids within a curie",
                    f"{human(dup_within_rows)} rows")
    else:
        report.ok("intra-curie dup pmids", "none")

    return {
        "lengths": lengths,
        "prefix_counter": prefix_counter,
        "total_pmid_refs": total_pmid_refs,
        "pmid_min": pmid_min,
        "pmid_max": pmid_max,
        "unique_pmids": len(unique_pmids) if unique_pmids is not None else None,
    }


def report_distributions(report, stats):
    report.header("PMID-list distribution")
    lengths = stats["lengths"]
    if not lengths:
        report.warn("no pmid lists to summarize")
        return

    n = len(lengths)
    lengths_sorted = sorted(lengths)

    def pct(p):
        i = min(n - 1, int(round(p * (n - 1))))
        return lengths_sorted[i]

    report.info("total pmid refs", human(stats["total_pmid_refs"]))
    if stats["unique_pmids"] is not None:
        report.info("unique pmids (global)", human(stats["unique_pmids"]))
    report.info("pmid value range",
                f"{stats['pmid_min']} .. {stats['pmid_max']}")
    report.info("pmids/curie min", human(min(lengths)))
    report.info("pmids/curie max", human(max(lengths)))
    report.info("pmids/curie mean", f"{statistics.mean(lengths):.2f}")
    report.info("pmids/curie median", human(int(statistics.median(lengths))))
    report.info("pmids/curie p50", human(pct(0.50)))
    report.info("pmids/curie p90", human(pct(0.90)))
    report.info("pmids/curie p95", human(pct(0.95)))
    report.info("pmids/curie p99", human(pct(0.99)))
    report.info("pmids/curie p99.9", human(pct(0.999)))

    report.header("PMID-list size buckets")
    buckets = [
        (1, 1, "exactly 1"),
        (2, 10, "2-10"),
        (11, 100, "11-100"),
        (101, 1_000, "101-1k"),
        (1_001, 10_000, "1k-10k"),
        (10_001, 100_000, "10k-100k"),
        (100_001, 10**12, "100k+"),
    ]
    for lo, hi, label in buckets:
        count = sum(1 for L in lengths if lo <= L <= hi)
        pct_ = (count / n * 100) if n else 0
        report.info(f"{label:>10}", f"{human(count):>12} curies ({pct_:5.1f}%)")


def report_prefixes(report, stats, top_n=30):
    report.header(f"CURIE prefix distribution (top {top_n})")
    total = sum(stats["prefix_counter"].values())
    for prefix, count in stats["prefix_counter"].most_common(top_n):
        pct_ = count / total * 100 if total else 0
        report.info(f"{prefix:>28}",
                    f"{human(count):>12} ({pct_:5.1f}%)")


def report_top_curies(report, conn, top_n=25):
    report.header(f"Top {top_n} curies by PMID count")
    cur = conn.cursor()
    # Fast pre-filter by JSON text length, then re-score a superset.
    rows = cur.execute(
        "SELECT curie, pmids FROM curie_to_pmids "
        "ORDER BY length(pmids) DESC LIMIT ?",
        (top_n * 5,),
    ).fetchall()
    scored = []
    for curie, pmids_json in rows:
        try:
            scored.append((curie, len(json.loads(pmids_json))))
        except Exception:
            pass
    scored.sort(key=lambda x: -x[1])
    for curie, count in scored[:top_n]:
        report.info(f"{curie:>44}", human(count))


def report_bottom_curies(report, conn, top_n=10):
    report.header(f"Sample of singleton curies (first {top_n} with 1 PMID)")
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT curie, pmids FROM curie_to_pmids "
        "WHERE length(pmids) <= 20 LIMIT 500"
    ).fetchall()
    shown = 0
    for curie, pmids_json in rows:
        try:
            pmids = json.loads(pmids_json)
        except Exception:
            continue
        if len(pmids) == 1:
            report.info(f"{curie:>44}", f"pmid {pmids[0]}")
            shown += 1
            if shown >= top_n:
                break


def spot_check_known(report, conn):
    report.header("Spot check: well-known entities")
    targets = [
        ("NCBIGene:7157",   "TP53"),
        ("NCBIGene:672",    "BRCA1"),
        ("NCBIGene:7124",   "TNF"),
        ("NCBIGene:3630",   "INS (insulin)"),
        ("NCBIGene:1956",   "EGFR"),
        ("NCBIGene:7422",   "VEGFA"),
        ("CHEBI:15365",     "aspirin"),
        ("CHEBI:28918",     "glucose"),
        ("CHEBI:16236",     "ethanol"),
        ("MESH:D000544",    "Alzheimer Disease"),
        ("MONDO:0004975",   "Alzheimer disease (MONDO)"),
        ("MESH:D009369",    "Neoplasms"),
        ("MESH:D003920",    "Diabetes Mellitus"),
        ("MESH:D006801",    "Humans"),
        ("MESH:D008297",    "Male"),
        ("MESH:D005260",    "Female"),
        ("MESH:D000086382", "COVID-19"),
        ("HP:0000118",      "Phenotypic abnormality"),
        ("UMLS:C0011849",   "Diabetes Mellitus (UMLS)"),
    ]
    cur = conn.cursor()
    hits = 0
    for curie, label in targets:
        row = cur.execute(
            "SELECT pmids FROM curie_to_pmids WHERE curie=?", (curie,)
        ).fetchone()
        if row is None:
            report.info(f"{curie:>28}", f"not present  ({label})")
            continue
        try:
            n = len(json.loads(row[0]))
        except Exception:
            report.warn(f"{curie:>28}", f"present but unparseable ({label})")
            continue
        hits += 1
        report.ok(f"{curie:>28}", f"{human(n):>10} pmids  ({label})")
    if hits == 0:
        report.warn("no spot-check entities found",
                    "Babel snapshot may use different namespaces")
    else:
        report.info("spot-check hit rate",
                    f"{hits}/{len(targets)}")


# ---------------------------------------------------------------------------
# Semantic checks that require Babel
# ---------------------------------------------------------------------------
# Names we expect any reasonable biomedical corpus to cover. We don't assume
# a namespace — we ask Babel to resolve each name and then check whether the
# resulting CURIE is in our DB. This avoids hardcoding namespace choices
# that don't match the Babel snapshot being used.
LIVE_SPOT_CHECK_NAMES = [
    # genes / proteins
    "TP53", "BRCA1", "BRCA2", "TNF", "EGFR", "VEGFA", "MYC", "KRAS",
    "insulin", "hemoglobin",
    # small molecules
    "aspirin", "glucose", "ethanol", "caffeine", "cholesterol", "dopamine",
    "serotonin", "cisplatin", "ibuprofen", "metformin",
    # diseases / phenotypes
    "Alzheimer Disease", "Diabetes Mellitus", "Breast Neoplasms",
    "Hypertension", "Asthma", "COVID-19", "Parkinson Disease",
    "Schizophrenia", "Obesity",
    # anatomy / cells
    "liver", "brain", "kidney", "T-Lymphocytes", "macrophage",
    # taxa / organisms
    "Homo sapiens", "Mus musculus", "Escherichia coli",
    # ubiquitous MeSH filters
    "Humans", "Male", "Female", "Mice", "Rats",
]


def live_spot_check(report, curie_conn, babel_conn):
    """Resolve a fixed list of names through Babel and confirm each
    resulting CURIE is present in the NGD DB with a plausible PMID count.
    """
    from stitch_proj.local_babel import map_name_to_curie

    report.header("Live spot check via Babel resolution")
    ccur = curie_conn.cursor()
    hits = 0
    misses_unresolved = 0
    misses_missing = 0
    for name in LIVE_SPOT_CHECK_NAMES:
        try:
            result = map_name_to_curie(babel_conn, name)
        except Exception as e:
            report.warn(f"{name!r}", f"resolve error: {e}")
            continue

        if not result:
            misses_unresolved += 1
            report.info(f"{name:>24}", "unresolved by Babel")
            continue

        curie, label = result
        row = ccur.execute(
            "SELECT pmids FROM curie_to_pmids WHERE curie=?", (curie,)
        ).fetchone()
        if row is None:
            misses_missing += 1
            report.warn(f"{name:>24}",
                        f"resolves to {curie} ({label}) but NOT in DB")
            continue

        try:
            n = len(json.loads(row[0]))
        except Exception:
            report.warn(f"{name:>24}",
                        f"{curie} present but pmids unparseable")
            continue

        hits += 1
        report.ok(f"{name:>24}",
                  f"{curie:<28} {human(n):>12} pmids  ({label})")

    total = len(LIVE_SPOT_CHECK_NAMES)
    report.info("hit rate",
                f"{hits}/{total} "
                f"(unresolved: {misses_unresolved}, "
                f"resolved-but-missing: {misses_missing})")
    if misses_missing:
        report.warn(
            "resolved-but-missing curies",
            "Babel mapped the name to a CURIE that isn't in the NGD DB. "
            "Usually means the raw MeSH/chemical name as it appears in "
            "PubMed XML is not matching what Babel expects — worth "
            "checking the extraction_script normalization.",
        )


def enrich_top_curies_with_labels(report, curie_conn, babel_conn, top_n=25):
    """Re-run the top-N-by-PMID-count report with labels from Babel so the
    opaque UMLS/MeSH codes are human-readable.
    """
    from stitch_proj.local_babel import get_all_names_for_curie

    report.header(f"Top {top_n} curies by PMID count (with Babel labels)")
    cur = curie_conn.cursor()
    rows = cur.execute(
        "SELECT curie, pmids FROM curie_to_pmids "
        "ORDER BY length(pmids) DESC LIMIT ?",
        (top_n * 5,),
    ).fetchall()

    scored = []
    for curie, pmids_json in rows:
        try:
            scored.append((curie, len(json.loads(pmids_json))))
        except Exception:
            pass
    scored.sort(key=lambda x: -x[1])

    for curie, count in scored[:top_n]:
        try:
            names = get_all_names_for_curie(babel_conn, curie)
        except Exception as e:
            report.warn(f"{curie}", f"label lookup failed: {e}")
            continue
        if names:
            primary = names[0]
            extra = f" (+{len(names) - 1} aliases)" if len(names) > 1 else ""
            report.info(f"{curie:>32}",
                        f"{human(count):>12}   {primary}{extra}")
        else:
            report.warn(f"{curie:>32}",
                        f"{human(count):>12}   <no label in Babel>")


# ---------------------------------------------------------------------------
# Accountability trace: which raw concept names feed a given CURIE?
# ---------------------------------------------------------------------------
_trace_babel_conn = None
_trace_targets = None


def _init_trace_worker(babel_db_path, targets):
    global _trace_babel_conn, _trace_targets
    from stitch_proj.local_babel import connect_to_db_read_only
    _trace_babel_conn = connect_to_db_read_only(babel_db_path)
    _trace_targets = targets


def _trace_one(item):
    from stitch_proj.local_babel import map_name_to_curie
    name, pmids_json = item
    try:
        result = map_name_to_curie(_trace_babel_conn, name)
    except Exception:
        return None
    if not result:
        return None
    curie = result[0]
    if curie not in _trace_targets:
        return None
    try:
        n = len(json.loads(pmids_json))
    except Exception:
        return None
    return (curie, name, n)


def _get_top_curies(conn, top_n):
    """Return [(curie, pmid_count), ...] sorted desc, length top_n.

    Uses len(pmids) text-length as pre-filter then parses for exactness.
    """
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT curie, pmids FROM curie_to_pmids "
        "ORDER BY length(pmids) DESC LIMIT ?",
        (top_n * 5,),
    ).fetchall()
    scored = []
    for curie, pmids_json in rows:
        try:
            scored.append((curie, len(json.loads(pmids_json))))
        except Exception:
            pass
    scored.sort(key=lambda x: -x[1])
    return scored[:top_n]


def trace_accountability(
    report,
    curie_conn,
    babel_db_path,
    concept_db_path,
    top_n,
    max_names_per_curie=25,
    target_curies=None,
):
    """For a set of target curies, find every raw concept name from stage 1
    that Babel maps to them, and report the per-name PMID contribution.

    If target_curies is provided, use those. Otherwise use the top-N curies
    in the NGD DB by PMID count.
    """
    report.header(
        f"Accountability trace "
        f"({'explicit curies' if target_curies else f'top {top_n}'})"
    )

    if not os.path.exists(concept_db_path):
        report.warn("concept DB missing", concept_db_path)
        return

    if target_curies:
        targets_list = list(target_curies)
        cur = curie_conn.cursor()
        target_totals = {}
        for c in targets_list:
            row = cur.execute(
                "SELECT pmids FROM curie_to_pmids WHERE curie=?", (c,)
            ).fetchone()
            if row is None:
                target_totals[c] = 0
                continue
            try:
                target_totals[c] = len(json.loads(row[0]))
            except Exception:
                target_totals[c] = 0
        ranked = sorted(target_totals.items(), key=lambda x: -x[1])
    else:
        ranked = _get_top_curies(curie_conn, top_n)
        target_totals = dict(ranked)

    target_set = frozenset(target_totals.keys())
    if not target_set:
        report.info("no targets", "")
        return

    report.info("target curies", str(len(target_set)))
    report.info("source", concept_db_path)

    # Stream concept names from stage 1. check_same_thread=False because the
    # multiprocessing Pool consumes the iterator from a helper thread.
    in_conn = sqlite3.connect(concept_db_path, check_same_thread=False)
    in_cursor = in_conn.cursor()

    per_target = defaultdict(list)  # curie -> [(name, n_pmids), ...]
    num_workers = max(1, (multiprocessing.cpu_count() or 2) - 1)
    report.info("resolver pool", f"{num_workers} workers")

    start = time.perf_counter()
    processed = 0
    matched = 0
    LOG_EVERY = 500_000

    def row_iter():
        for row in in_cursor.execute(
            "SELECT concept_name, pmids FROM conceptname_to_pmids"
        ):
            yield row

    try:
        with multiprocessing.Pool(
            num_workers,
            initializer=_init_trace_worker,
            initargs=(babel_db_path, target_set),
        ) as pool:
            for result in pool.imap_unordered(
                _trace_one, row_iter(), chunksize=500
            ):
                processed += 1
                if result is not None:
                    curie, name, n = result
                    per_target[curie].append((name, n))
                    matched += 1
                if processed % LOG_EVERY == 0:
                    elapsed = time.perf_counter() - start
                    rate = processed / elapsed if elapsed > 0 else 0
                    report.info(
                        "  progress",
                        f"{processed:,} names | "
                        f"{matched:,} matched | {rate:,.0f} names/sec",
                    )
    finally:
        in_conn.close()

    elapsed = time.perf_counter() - start
    report.info("trace done",
                f"{processed:,} names scanned in {elapsed:.1f}s, "
                f"{matched:,} contributions matched")

    # Per-target breakdown
    for curie, total_pmids in ranked:
        contributors = sorted(
            per_target.get(curie, []), key=lambda x: -x[1]
        )
        print()
        print(f"  {curie}  (DB total: {human(total_pmids)} pmids, "
              f"{len(contributors)} contributing names)")
        if not contributors:
            print("    <no contributing names found>")
            continue
        shown = contributors[:max_names_per_curie]
        contrib_sum = sum(n for _, n in contributors)
        for name, n_pmids in shown:
            pct = (n_pmids / total_pmids * 100) if total_pmids else 0
            print(f"    {n_pmids:>10,} pmids ({pct:5.1f}%)  {name!r}")
        if len(contributors) > max_names_per_curie:
            remaining = len(contributors) - max_names_per_curie
            remaining_pmids = sum(n for _, n in contributors[max_names_per_curie:])
            print(f"    ... {remaining} more contributors "
                  f"({human(remaining_pmids)} pmids combined)")
        # Note: contrib_sum can exceed total_pmids because stage-2 dedups
        # PMIDs that multiple contributor names shared.
        if contrib_sum > total_pmids * 1.05:
            overlap = contrib_sum - total_pmids
            print(f"    [info] contributors sum {human(contrib_sum)} "
                  f"> DB total → ~{human(overlap)} deduped overlaps")


def compare_with_concept_db(report, curie_conn, concept_db_path):
    report.header("Stage 1 vs stage 2 consistency")
    if not os.path.exists(concept_db_path):
        report.info("concept DB", f"{concept_db_path} not present; skipping")
        return

    ccur = curie_conn.cursor()
    (n_curies,) = ccur.execute("SELECT COUNT(*) FROM curie_to_pmids").fetchone()

    cconn = sqlite3.connect(concept_db_path)
    try:
        ccur2 = cconn.cursor()
        (n_concepts,) = ccur2.execute(
            "SELECT COUNT(*) FROM conceptname_to_pmids"
        ).fetchone()
    finally:
        cconn.close()

    report.info("stage1 concept names", human(n_concepts))
    report.info("stage2 curies", human(n_curies))
    if n_curies > 0:
        ratio = n_concepts / n_curies
        report.info("concept-names / curies", f"{ratio:.2f}")
        if ratio < 1.0:
            report.warn("ratio < 1",
                        "more curies than source concept names?")


def check_curie_format(report, conn, sample=20000):
    report.header("CURIE format sanity")
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT curie FROM curie_to_pmids LIMIT ?", (sample,)
    ).fetchall()
    no_colon = 0
    whitespace = 0
    suspicious = 0
    for (curie,) in rows:
        if ":" not in curie:
            no_colon += 1
        if any(c.isspace() for c in curie):
            whitespace += 1
        if len(curie) < 3 or len(curie) > 200:
            suspicious += 1
    if no_colon:
        report.fail(f"curies without ':' (in first {human(sample)})", human(no_colon))
    else:
        report.ok(f"curies contain ':' (first {human(sample)})", "all")
    if whitespace:
        report.fail("curies with whitespace", human(whitespace))
    else:
        report.ok("curies with whitespace", "none")
    if suspicious:
        report.warn("suspicious length curies", human(suspicious))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def _check_environment(args):
    """Verify that all required paths exist and dependencies are importable."""
    ok = True
    p = print

    # Describe the audit mode
    p("")
    p("=" * 60)
    if args.test:
        p("  NGD AUDIT — DRY RUN (--test)")
        p("  Validating paths and dependencies only.")
        p("  No audit checks will be executed.")
    else:
        features = ["structural checks", "distribution stats"]
        if args.babel_db:
            features.append("live spot checks via Babel")
        if args.concept_db:
            features.append("stage-1 vs stage-2 comparison")
        if args.trace_top > 0 or args.trace_curie:
            features.append("accountability tracing")
        p("  NGD AUDIT")
        p(f"  Will run: {', '.join(features)}.")
    p("=" * 60)

    # Paths
    p("")
    p("Paths:")

    if not os.path.isfile(args.db):
        p(f"  [FAIL] --db: {args.db} (not found)")
        ok = False
    else:
        p(f"  [ OK ] --db: {args.db}")

    if args.concept_db:
        if not os.path.isfile(args.concept_db):
            p(f"  [FAIL] --concept-db: {args.concept_db} (not found)")
            ok = False
        else:
            p(f"  [ OK ] --concept-db: {args.concept_db}")
    else:
        p("  [ -- ] --concept-db: not set (stage-1 comparison and tracing disabled)")

    if args.babel_db:
        if not os.path.isfile(args.babel_db):
            p(f"  [FAIL] --babel-db: {args.babel_db} (not found)")
            ok = False
        else:
            p(f"  [ OK ] --babel-db: {args.babel_db}")
    else:
        p("  [ -- ] --babel-db: not set (live spot checks disabled)")

    if (args.trace_top > 0 or args.trace_curie) and not args.babel_db:
        p("  [FAIL] --trace-top/--trace-curie requires --babel-db")
        ok = False
    if (args.trace_top > 0 or args.trace_curie) and not args.concept_db:
        p("  [FAIL] --trace-top/--trace-curie requires --concept-db")
        ok = False

    # Dependencies
    p("")
    p("Dependencies:")

    try:
        from stitch_proj.local_babel import connect_to_db_read_only  # noqa: F401
        p("  [ OK ] stitch_proj.local_babel")
    except ImportError:
        if args.babel_db:
            p("  [FAIL] stitch_proj — not installed (required for --babel-db)")
            ok = False
        else:
            p("  [ -- ] stitch_proj — not installed (not needed without --babel-db)")

    # Summary
    p("")
    p("-" * 60)
    if ok:
        p("  PASSED — environment is ready.")
    else:
        p("  FAILED — fix the errors above.")
    p("-" * 60)
    p("")

    return ok


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True,
                        help="Path to curie_to_pmids sqlite database.")
    parser.add_argument("--concept-db", default=None,
                        help="Path to conceptname_to_pmids sqlite for "
                             "stage-1 comparison and accountability tracing.")
    parser.add_argument("--sample", type=int, default=None,
                        help="Only scan the first N rows (faster partial audit)")
    parser.add_argument("--count-unique-pmids", action="store_true",
                        help="Also count globally-unique PMIDs (memory heavy)")
    parser.add_argument("--babel-db", default=None,
                        help="Babel sqlite path. Enables live name resolution "
                             "spot checks and label enrichment for top curies.")
    parser.add_argument("--trace-top", type=int, default=0, metavar="N",
                        help="Trace which raw concept names feed the top N "
                             "curies (requires --babel-db and --concept-db).")
    parser.add_argument("--trace-curie", action="append", default=[],
                        metavar="CURIE",
                        help="Trace contributors for a specific CURIE. "
                             "Can be repeated. Requires --babel-db and --concept-db.")
    parser.add_argument("--test", action="store_true",
                        help="Verify paths and environment without running the audit.")
    args = parser.parse_args()

    env_ok = _check_environment(args)

    if args.test:
        sys.exit(0 if env_ok else 1)

    if not env_ok:
        sys.exit(1)

    report = Report()

    if not check_file(report, args.db):
        sys.exit(2)

    conn = sqlite3.connect(args.db)
    try:
        check_schema(report, conn)
        check_indexes(report, conn)
        check_counts(report, conn)
        check_curie_format(report, conn)
        stats = scan_all_rows(
            report, conn,
            sample_limit=args.sample,
            count_unique_pmids=args.count_unique_pmids,
        )
        report_distributions(report, stats)
        report_prefixes(report, stats)
        report_top_curies(report, conn)
        report_bottom_curies(report, conn)
        spot_check_known(report, conn)

        if args.concept_db:
            compare_with_concept_db(report, conn, args.concept_db)

        if args.babel_db:
            if not os.path.exists(args.babel_db):
                report.fail("babel db", f"not found: {args.babel_db}")
            else:
                try:
                    from stitch_proj.local_babel import connect_to_db_read_only
                    babel_conn = connect_to_db_read_only(args.babel_db)
                except Exception as e:
                    report.fail("babel db connect", str(e))
                else:
                    try:
                        live_spot_check(report, conn, babel_conn)
                        enrich_top_curies_with_labels(report, conn, babel_conn)
                    finally:
                        babel_conn.close()

                # Accountability trace uses its own pool / connections.
                if args.trace_curie:
                    if not args.concept_db:
                        report.fail("--trace-curie requires --concept-db")
                    else:
                        trace_accountability(
                            report, conn, args.babel_db, args.concept_db,
                            top_n=0, target_curies=args.trace_curie,
                        )
                elif args.trace_top > 0:
                    if not args.concept_db:
                        report.fail("--trace-top requires --concept-db")
                    else:
                        trace_accountability(
                            report, conn, args.babel_db, args.concept_db,
                            top_n=args.trace_top,
                        )
        elif args.trace_top > 0 or args.trace_curie:
            report.fail("--trace-top/--trace-curie requires --babel-db")
    finally:
        conn.close()

    print()
    print("=" * 72)
    if report.failures:
        print(f"AUDIT FAILED: {report.failures} failures, "
              f"{report.warnings} warnings")
        sys.exit(1)
    print(f"AUDIT PASSED: {report.warnings} warnings")
    sys.exit(0)


if __name__ == "__main__":
    main()
