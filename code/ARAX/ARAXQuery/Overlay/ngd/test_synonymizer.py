#!/usr/bin/env python3
"""
Performance test for batched concurrent name resolution
(ThreadPoolExecutor, 50 names/batch, 10 workers).

Generate the input file first:
    python extract_sample_names.py

Usage:
    python test_synonymizer.py [--names-file PATH]
"""
import argparse
import concurrent.futures
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
    parser = argparse.ArgumentParser(description="Name resolver performance test")
    parser.add_argument(
        "--names-file", type=str,
        default=os.path.join(NGD_DIR, "sample_names.txt"),
    )
    args = parser.parse_args()

    names = load_names(args.names_file)
    synonymizer = NodeSynonymizer(autocomplete=False)

    batch_size = 50
    num_workers = 10
    batches = [names[i:i + batch_size]
               for i in range(0, len(names), batch_size)]

    print(f"Running batched concurrent: {len(batches)} batches x {batch_size} names, {num_workers} workers...")
    name_to_curie = {}
    start = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
        future_to_batch = {
            executor.submit(synonymizer._call_name_resolver_api, batch): batch
            for batch in batches
        }
        for future in concurrent.futures.as_completed(future_to_batch):
            result = future.result()
            if result:
                name_to_curie.update(result)

    elapsed = time.time() - start
    resolved = sum(1 for v in name_to_curie.values() if v)

    print(f"\n{'='*50}")
    print(f"  Total names:   {len(names)}")
    print(f"  Resolved:      {resolved}/{len(names)} ({resolved/len(names)*100:.1f}%)")
    print(f"  Wall time:     {elapsed:.2f}s")
    print(f"  Throughput:    {len(names)/elapsed:.1f} names/sec")

    # Show sample results
    ok = [(n, c) for n, c in name_to_curie.items() if c]
    null = [n for n, c in name_to_curie.items() if not c]

    if ok:
        print(f"\n--- Sample resolved (first 10) ---")
        for name, curie in ok[:10]:
            print(f"  \"{name}\" -> {curie}")

    if null:
        print(f"\n--- Sample unresolved (first 10) ---")
        for name in null[:10]:
            print(f"  \"{name}\"")


if __name__ == "__main__":
    main()
