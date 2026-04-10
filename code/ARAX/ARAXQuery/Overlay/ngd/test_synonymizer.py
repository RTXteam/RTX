#!/usr/bin/env python3
"""
Benchmark NodeSynonymizer throughput to inform build_ngd_database.py configuration.

Pulls sample names from the DB, cleans them, then sends them to
get_canonical_curies in chunks of 50 (matching the synonymizer's
internal API batch size). Shows what was sent and what came back.

Usage: python test_synonymizer.py [--names N] [--per-call P]
"""
import argparse
import json
import os
import re
import sqlite3
import sys
import time

from tqdm import tqdm

pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")

sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'NodeSynonymizer']))
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code']))
from node_synonymizer import NodeSynonymizer

NGD_DIR = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'ARAXQuery', 'Overlay', 'ngd'])
DB_PATH = os.path.join(NGD_DIR, 'conceptname_to_pmids.sqlite')

SAMPLE_SIZE = 10


def clean_name(raw):
    """Strip a raw concept name down to just the phrase."""
    if not raw:
        return None
    s = raw
    # Remove all quote characters — ASCII and Unicode smart quotes
    for ch in '"\'`\u2018\u2019\u201a\u201b\u201c\u201d\u201e\u201f':
        s = s.replace(ch, '')
    # Remove leading/trailing angle brackets (XML artifacts)
    s = s.strip('<>')
    # Collapse internal whitespace runs
    s = re.sub(r'\s+', ' ', s)
    s = s.strip()
    return s if s else None


def load_names(n):
    """Pull n concept names from the DB, cleaned and deduplicated."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for table in ['staging', 'conceptname_to_pmids']:
        try:
            cursor.execute(f"SELECT concept_name FROM {table} LIMIT ?", (n,))
            rows = cursor.fetchall()
            if rows:
                raw_names = [row[0] for row in rows if row[0]]
                cleaned = []
                dirty_count = 0
                for raw in raw_names:
                    c = clean_name(raw)
                    if c and c != raw.strip():
                        dirty_count += 1
                    if c:
                        cleaned.append(c)
                seen = set()
                names = []
                dupes = 0
                for name in cleaned:
                    if name in seen:
                        dupes += 1
                    else:
                        seen.add(name)
                        names.append(name)
                conn.close()
                print(f"Pulled {len(raw_names)} raw names from '{table}' table")
                print(f"  Cleaned: {dirty_count} had junk characters stripped")
                print(f"  Deduped: {dupes} duplicates removed")
                print(f"  Final: {len(names)} unique clean names")
                return names
        except sqlite3.OperationalError:
            continue
    conn.close()
    print("ERROR: Could not find names in either 'staging' or 'conceptname_to_pmids' table")
    sys.exit(1)


def classify_results(names, results):
    """Classify each name into recognized/null/empty/missing."""
    recognized = []
    nulls = []
    empty = []

    for name in names:
        val = results.get(name)
        if val is None:
            nulls.append(name)
        elif val.get('preferred_curie'):
            recognized.append({
                'input_name': name,
                'preferred_curie': val['preferred_curie'],
                'preferred_name': val.get('preferred_name'),
                'preferred_category': val.get('preferred_category'),
            })
        else:
            empty.append({'input_name': name, 'result': val})

    missing = [n for n in names if n not in results]
    return recognized, nulls, empty, missing


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark NodeSynonymizer for build_ngd_database.py tuning")
    parser.add_argument("--names", type=int, default=2000,
                        help="Number of concept names to pull from DB (default: 2000)")
    parser.add_argument("--per-call", type=int, default=50,
                        help="Names per get_canonical_curies call (default: 50)")
    args = parser.parse_args()

    names = load_names(args.names)
    total_names = len(names)

    synonymizer = NodeSynonymizer(autocomplete=False)
    print(f"\nName resolver URL: {synonymizer.name_resolver_url}")
    print(f"Node normalizer URL: {synonymizer.api_base_url}")
    print(f"Testing with {total_names} unique clean names, {args.per_call} per call\n")

    # Split names into chunks and process sequentially
    chunks = [names[i:i + args.per_call] for i in range(0, total_names, args.per_call)]
    results = {}
    errors = 0

    start = time.time()
    for chunk in tqdm(chunks, desc="  resolving", unit="call"):
        try:
            result = synonymizer.get_canonical_curies(names=chunk)
            if result:
                results.update(result)
        except Exception as e:
            errors += 1
            print(f"  error: {e}")
    elapsed = time.time() - start

    # Classify and display results
    recognized, nulls, empty, missing = classify_results(names, results)

    nps = total_names / elapsed if elapsed > 0 else 0
    ms_per = elapsed / total_names * 1000 if total_names > 0 else 0
    pct = len(recognized) / total_names * 100 if total_names > 0 else 0

    print(f"\n{'=' * 70}")
    print(f"RESULTS")
    print(f"{'=' * 70}")
    print(f"  Time: {elapsed:.1f}s | {nps:.0f} names/sec | {ms_per:.1f}ms/name")
    print(f"  Recognized: {len(recognized)}/{total_names} ({pct:.1f}%)")
    print(f"  Nulls: {len(nulls)} | Empty: {len(empty)} | Missing: {len(missing)} | Errors: {errors}")

    if recognized:
        print(f"\n  Sample recognized ({min(SAMPLE_SIZE, len(recognized))} of {len(recognized)}):")
        for r in recognized[:SAMPLE_SIZE]:
            print(f"    SENT: '{r['input_name']}'")
            print(f"    GOT:  {r['preferred_curie']} | {r['preferred_name']} | {r['preferred_category']}")

    if nulls:
        print(f"\n  Sample nulls ({min(SAMPLE_SIZE, len(nulls))} of {len(nulls)}):")
        for name in nulls[:SAMPLE_SIZE]:
            print(f"    SENT: '{name}'")
            print(f"    GOT:  None")

    if empty:
        print(f"\n  Sample empty ({min(SAMPLE_SIZE, len(empty))} of {len(empty)}):")
        for e in empty[:SAMPLE_SIZE]:
            print(f"    SENT: '{e['input_name']}'")
            print(f"    GOT:  {e['result']}")

    # Estimate for full 8.6M workload
    if nps > 0:
        est_minutes = 8_600_000 / nps / 60
        print(f"\n  Estimated time for 8.6M names: ~{est_minutes:.0f} min ({est_minutes/60:.1f} hours)")

    # Write full diagnostics
    output_path = os.path.join(NGD_DIR, 'diagnose_results.json')
    diag = {
        'config': {'names_per_call': args.per_call, 'total_names': total_names},
        'elapsed': round(elapsed, 2),
        'names_per_sec': round(nps, 1),
        'errors': errors,
        'recognized': recognized,
        'null_names': nulls,
        'empty_results': empty,
        'missing_names': missing,
    }
    with open(output_path, 'w') as f:
        json.dump(diag, f, indent=2)
    print(f"\n  Full diagnostics written to {output_path}")


if __name__ == '__main__':
    main()
