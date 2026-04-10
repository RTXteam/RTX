#!/usr/bin/env python3
"""
Read concept names from a text file (one per line), send each one-by-one
to _call_name_resolver_api (skipping the redundant Node Normalizer step),
and report success/null rates with full results for visual inspection.

Generate the input file first:
    python extract_sample_names.py

Usage:
    python test_synonymizer_sample.py [--names-file PATH]
"""
import argparse
import csv
import os
import sys
import time

pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'NodeSynonymizer']))
from node_synonymizer import NodeSynonymizer

NGD_DIR = os.path.dirname(os.path.abspath(__file__))


def load_names(names_file: str):
    if not os.path.exists(names_file):
        print(f"ERROR: Names file not found at {names_file}")
        print("Run extract_sample_names.py first to generate it.")
        sys.exit(1)

    with open(names_file) as f:
        names = [line.rstrip("\n") for line in f if line.strip()]

    print(f"Loaded {len(names):,} names from {names_file}\n")
    return names


def main():
    parser = argparse.ArgumentParser(description="One-by-one name resolver test")
    parser.add_argument(
        "--names-file", type=str,
        default=os.path.join(NGD_DIR, "sample_names.txt"),
    )
    args = parser.parse_args()

    names = load_names(args.names_file)
    synonymizer = NodeSynonymizer(autocomplete=False)

    results = []
    recognized = 0
    unrecognized = 0
    errors = 0
    start_all = time.time()

    print(f"{'#':<6} {'Status':<8} {'Time':>6}  {'Input Name':<40} {'Resolved CURIE'}")
    print("-" * 110)

    for i, name in enumerate(names):
        t0 = time.time()
        try:
            resp = synonymizer._call_name_resolver_api([name])
            elapsed = time.time() - t0
            curie = resp.get(name)

            if curie:
                status = "OK"
                recognized += 1
            else:
                status = "NULL"
                unrecognized += 1
                curie = None

        except Exception as e:
            elapsed = time.time() - t0
            status = "ERROR"
            errors += 1
            curie = None

        results.append({
            "index": i + 1,
            "name": name,
            "status": status,
            "resolved_curie": curie,
            "elapsed": elapsed,
        })

        display_input = name[:38] + ".." if len(name) > 40 else name
        display_curie = (curie or "")[:50]
        print(f"{i+1:<6} {status:<8} {elapsed:>5.1f}s  {display_input:<40} {display_curie}")

        if (i + 1) % 100 == 0:
            elapsed_total = time.time() - start_all
            rate = (i + 1) / elapsed_total
            eta = (len(names) - i - 1) / rate if rate > 0 else 0
            print(f"  --- {i+1}/{len(names)} done, {rate:.1f} names/sec, ETA {eta:.0f}s ---")

    total_time = time.time() - start_all
    total = len(results)

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Total names:       {total}")
    print(f"  Recognized (OK):   {recognized}  ({recognized/total*100:.1f}%)")
    print(f"  Unrecognized:      {unrecognized}  ({unrecognized/total*100:.1f}%)")
    print(f"  Errors:            {errors}  ({errors/total*100:.1f}%)")
    print(f"  Total wall time:   {total_time:.1f}s")
    print(f"  Avg time/name:     {total_time/total:.2f}s")
    print(f"  Throughput:        {total/total_time:.1f} names/sec")

    csv_path = os.path.join(NGD_DIR, "synonymizer_sample_results.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "index", "name", "status",
            "resolved_curie", "elapsed",
        ])
        writer.writeheader()
        writer.writerows(results)
    print(f"\n  Full results written to: {csv_path}")

    ok_rows = [r for r in results if r["status"] == "OK"]
    null_rows = [r for r in results if r["status"] == "NULL"]
    error_rows = [r for r in results if r["status"] == "ERROR"]

    if ok_rows:
        print(f"\n--- Sample RECOGNIZED names (first 10) ---")
        for r in ok_rows[:10]:
            print(f"  \"{r['name']}\" -> {r['resolved_curie']}")

    if null_rows:
        print(f"\n--- Sample UNRECOGNIZED names (first 10) ---")
        for r in null_rows[:10]:
            print(f"  \"{r['name']}\"")

    if error_rows:
        print(f"\n--- Sample ERROR names (first 10) ---")
        for r in error_rows[:10]:
            print(f"  \"{r['name']}\"")


if __name__ == "__main__":
    main()
