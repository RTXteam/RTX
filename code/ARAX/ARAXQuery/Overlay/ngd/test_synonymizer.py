#!/usr/bin/env python3
"""
Benchmark NodeSynonymizer throughput to inform build_ngd_database.py configuration.

Tests different combinations of:
  - num_workers: concurrent ThreadPoolExecutor threads (mirrors build_ngd_database.py)
  - batch_size: names per get_canonical_curies call (each call internally chunks into
    50-name API requests to /bulk-lookup)

The goal is to find the (num_workers, batch_size) combo that maximizes names/sec
without hitting API errors or timeouts, so we can configure build_ngd_database.py
for the full 8.6M name workload.

Usage: python test_synonymizer.py [--names N] [--workers W1,W2,...] [--batches B1,B2,...]
       python test_synonymizer.py --diagnose [--names N]
"""
import argparse
import concurrent.futures
import json
import os
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


def load_names(n):
    """Pull n concept names from the staging table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Try staging first (present during builds), fall back to conceptname_to_pmids
    for table in ['staging', 'conceptname_to_pmids']:
        try:
            cursor.execute(f"SELECT concept_name FROM {table} LIMIT ?", (n,))
            rows = cursor.fetchall()
            if rows:
                names = [row[0].strip() for row in rows if row[0] and row[0].strip()]
                conn.close()
                print(f"Pulled {len(names)} names from '{table}' table")
                return names
        except sqlite3.OperationalError:
            continue
    conn.close()
    print("ERROR: Could not find names in either 'staging' or 'conceptname_to_pmids' table")
    sys.exit(1)


def run_sequential(synonymizer, names, batch_size):
    """Resolve names sequentially in batches (single-threaded baseline)."""
    results = {}
    errors = 0
    batches = [names[i:i + batch_size] for i in range(0, len(names), batch_size)]

    for batch in tqdm(batches, desc="  sequential", unit="call", leave=False):
        try:
            result = synonymizer.get_canonical_curies(names=batch)
            if result:
                results.update(result)
        except Exception as e:
            errors += 1
            print(f"  error: {e}")

    return results, errors


def run_concurrent(synonymizer, names, batch_size, num_workers):
    """Resolve names using ThreadPoolExecutor (mirrors build_ngd_database.py)."""
    results = {}
    errors = 0
    batches = [names[i:i + batch_size] for i in range(0, len(names), batch_size)]

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
        future_to_batch = {
            executor.submit(synonymizer.get_canonical_curies, names=batch): batch
            for batch in batches
        }
        done_iter = concurrent.futures.as_completed(future_to_batch)
        for future in tqdm(done_iter, total=len(batches),
                           desc=f"  workers={num_workers}", unit="call", leave=False):
            try:
                result = future.result()
                if result:
                    results.update(result)
            except Exception as e:
                errors += 1
                print(f"  error: {e}")

    return results, errors


def print_stats(label, results, errors, elapsed, total_names):
    """Print a formatted stats line."""
    recognized = sum(1 for v in results.values() if v and v.get('preferred_curie'))
    nulls = sum(1 for v in results.values() if v is None)
    nps = total_names / elapsed if elapsed > 0 else 0
    ms_per = elapsed / total_names * 1000 if total_names > 0 else 0
    pct = recognized / total_names * 100 if total_names > 0 else 0

    print(f"  {label}")
    print(f"    Time: {elapsed:.1f}s | {nps:.0f} names/sec | {ms_per:.1f}ms/name")
    print(f"    Recognized: {recognized}/{total_names} ({pct:.1f}%)")
    print(f"    Nulls: {nulls} | Errors: {errors}")


def run_diagnose(synonymizer, names):
    """Run all names through get_canonical_curies and write detailed results
    so you can inspect exactly what was sent and what came back."""
    print("Running diagnostic pass (all names in one call)...\n")

    start = time.time()
    results = synonymizer.get_canonical_curies(names=names)
    elapsed = time.time() - start

    recognized = []
    nulls = []
    empty = []  # returned a dict but no preferred_curie

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

    # Names that were sent but aren't even in the results dict
    missing = [n for n in names if n not in results]

    print(f"Time: {elapsed:.1f}s")
    print(f"Recognized: {len(recognized)}/{len(names)} ({len(recognized)/len(names)*100:.1f}%)")
    print(f"Null (name resolver found nothing): {len(nulls)}")
    print(f"Empty (resolved but no preferred_curie): {len(empty)}")
    print(f"Missing from results entirely: {len(missing)}")

    # Print samples to terminal
    print(f"\n--- Sample RECOGNIZED names (first 10) ---")
    for r in recognized[:10]:
        print(f"  '{r['input_name']}' -> {r['preferred_curie']} ({r['preferred_name']})")

    print(f"\n--- Sample NULL names (first 20) ---")
    for name in nulls[:20]:
        print(f"  '{name}'")

    if empty:
        print(f"\n--- Sample EMPTY names (first 10) ---")
        for e in empty[:10]:
            print(f"  '{e['input_name']}' -> {e['result']}")

    if missing:
        print(f"\n--- Sample MISSING names (first 10) ---")
        for name in missing[:10]:
            print(f"  '{name}'")

    # Write full details to JSON for deeper inspection
    output_path = os.path.join(NGD_DIR, 'diagnose_results.json')
    diag = {
        'total_names': len(names),
        'elapsed_seconds': round(elapsed, 2),
        'recognized_count': len(recognized),
        'null_count': len(nulls),
        'empty_count': len(empty),
        'missing_count': len(missing),
        'recognized': recognized,
        'null_names': nulls,
        'empty_results': empty,
        'missing_names': missing,
    }
    with open(output_path, 'w') as f:
        json.dump(diag, f, indent=2)
    print(f"\nFull diagnostics written to {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark NodeSynonymizer for build_ngd_database.py tuning")
    parser.add_argument("--names", type=int, default=2000,
                        help="Number of concept names to test with (default: 2000)")
    parser.add_argument("--workers", type=str, default="1,5,10,15",
                        help="Comma-separated list of worker counts to test (default: 1,5,10,15)")
    parser.add_argument("--batches", type=str, default="50,250,500,1000",
                        help="Comma-separated list of batch sizes to test (default: 50,250,500,1000)")
    parser.add_argument("--diagnose", action="store_true", default=False,
                        help="Run a single batch and write detailed diagnostics to diagnose_results.json")
    args = parser.parse_args()

    names = load_names(args.names)
    total_names = len(names)

    synonymizer = NodeSynonymizer(autocomplete=False)
    print(f"\nName resolver URL: {synonymizer.name_resolver_url}")
    print(f"Node normalizer URL: {synonymizer.api_base_url}")
    print(f"Testing with {total_names} names\n")

    # ── Diagnose mode ──
    if args.diagnose:
        run_diagnose(synonymizer, names)
        return

    worker_counts = [int(x) for x in args.workers.split(",")]
    batch_sizes = [int(x) for x in args.batches.split(",")]

    # Collect results for summary table
    summary = []

    # ── Phase 1: Sequential baseline ──
    print("=" * 70)
    print("PHASE 1: Sequential baseline (single-threaded)")
    print("=" * 70)
    for batch_size in batch_sizes:
        num_batches = (total_names + batch_size - 1) // batch_size
        label = f"batch_size={batch_size} ({num_batches} calls)"
        print(f"\n--- {label} ---")

        start = time.time()
        results, errors = run_sequential(synonymizer, names, batch_size)
        elapsed = time.time() - start

        print_stats(label, results, errors, elapsed, total_names)
        nps = total_names / elapsed if elapsed > 0 else 0
        recognized = sum(1 for v in results.values() if v and v.get('preferred_curie'))
        summary.append({
            'workers': 1, 'batch_size': batch_size,
            'elapsed': elapsed, 'nps': nps,
            'recognized': recognized, 'errors': errors
        })

    # ── Phase 2: Concurrent (ThreadPoolExecutor) ──
    print(f"\n{'=' * 70}")
    print("PHASE 2: Concurrent (ThreadPoolExecutor, mirrors build_ngd_database.py)")
    print("=" * 70)
    for num_workers in worker_counts:
        if num_workers == 1:
            continue  # Already covered in phase 1
        for batch_size in batch_sizes:
            num_batches = (total_names + batch_size - 1) // batch_size
            label = f"workers={num_workers}, batch_size={batch_size} ({num_batches} batches)"
            print(f"\n--- {label} ---")

            # Fresh synonymizer to avoid cross-test cache effects
            syn = NodeSynonymizer(autocomplete=False)
            start = time.time()
            results, errors = run_concurrent(syn, names, batch_size, num_workers)
            elapsed = time.time() - start

            print_stats(label, results, errors, elapsed, total_names)
            nps = total_names / elapsed if elapsed > 0 else 0
            recognized = sum(1 for v in results.values() if v and v.get('preferred_curie'))
            summary.append({
                'workers': num_workers, 'batch_size': batch_size,
                'elapsed': elapsed, 'nps': nps,
                'recognized': recognized, 'errors': errors
            })

    # ── Summary table ──
    print(f"\n{'=' * 70}")
    print("SUMMARY (sorted by names/sec)")
    print("=" * 70)
    print(f"{'Workers':>8} {'Batch':>8} {'Time(s)':>8} {'Names/s':>8} {'Recognized':>11} {'Errors':>7}")
    print("-" * 60)
    for row in sorted(summary, key=lambda r: r['nps'], reverse=True):
        print(f"{row['workers']:>8} {row['batch_size']:>8} {row['elapsed']:>8.1f} "
              f"{row['nps']:>8.0f} {row['recognized']:>6}/{total_names:<4} {row['errors']:>7}")

    # ── Recommendation ──
    best = max(summary, key=lambda r: r['nps'])
    if best['errors'] > 0:
        # If the fastest has errors, pick the fastest error-free option
        error_free = [r for r in summary if r['errors'] == 0]
        if error_free:
            best = max(error_free, key=lambda r: r['nps'])
    print(f"\nRecommended config for build_ngd_database.py:")
    print(f"  num_workers = {best['workers']}")
    print(f"  batch_size  = {best['batch_size']}")
    print(f"  ({best['nps']:.0f} names/sec → ~{8_600_000 / best['nps'] / 60:.0f} min for 8.6M names)")


if __name__ == '__main__':
    main()
