#!/usr/bin/env python3
"""Benchmark NodeSynonymizer at different batch sizes and concurrency levels."""
import concurrent.futures
import os
import sqlite3
import sys
import time
import threading

from tqdm import tqdm

pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")

sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'NodeSynonymizer']))
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code']))
from node_synonymizer import NodeSynonymizer

# Grab 100,000 concept names from the staging table
NGD_DIR = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'ARAXQuery', 'Overlay', 'ngd'])
db_path = os.path.join(NGD_DIR, 'conceptname_to_pmids.sqlite')

# Test configs: (batch_size, num_workers, total_names)
# Focus on the realistic batch=1000 case with a worker sweep
# to find the best concurrency for the NGD build script.
# batch=100 with workers is included as a comparison point.
test_configs = [
    # batch_size 100 reference points
    (100,  1,  10000),
    (100,  5,  10000),
    (100,  10, 10000),
    # batch_size 1000 worker sweep
    (1000, 1,  10000),
    (1000, 5,  10000),
    (1000, 6,  10000),
    (1000, 7,  10000),
    (1000, 8,  10000),
    (1000, 10, 10000),
]

# Pull enough names so each test gets a unique slice (avoid server-side caching)
total_needed = sum(cfg[2] for cfg in test_configs)
print(f"Need {total_needed} unique names across {len(test_configs)} tests")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT concept_name FROM staging LIMIT ?", (total_needed,))
names = [row[0] for row in cursor.fetchall()]
conn.close()
print(f"Sampled {len(names)} concept names\n")

if len(names) < total_needed:
    print(f"ERROR: Only got {len(names)} names but need {total_needed}")
    sys.exit(1)

bench_results = []
name_offset = 0

for batch_size, num_workers, total_names in test_configs:
    test_names = names[name_offset:name_offset + total_names]
    name_offset += total_names
    name_batches = [test_names[i:i + batch_size]
                    for i in range(0, total_names, batch_size)]
    num_batches = len(name_batches)

    # Fresh synonymizer each time so cache doesn't help.
    # Opt into all the new robustness flags so failures
    # are visible and concurrent calls don't double-fetch.
    synonymizer = NodeSynonymizer(
        autocomplete=False,
        thread_safe=(num_workers > 1),
        log_api_failures=True,
        max_api_retries=5,
        retry_backoff=True,
        name_resolver_batch_size=200,
        name_resolver_timeout=120,
    )

    label = f"batch={batch_size}, workers={num_workers}"
    print(f"--- {label} ({num_batches} API calls for {total_names} names) ---")

    results = {}
    results_lock = threading.Lock()
    errors = 0
    empty_results = 0  # diagnostic: API returned but with nothing useful
    start = time.time()

    def resolve_batch(batch):
        try:
            return synonymizer.get_canonical_curies(
                names=batch, skip_malformed=True)
        except Exception:
            return "ERROR"

    if num_workers == 1:
        # Sequential
        for batch in tqdm(name_batches, desc=f"  {label}", unit="call"):
            result = resolve_batch(batch)
            if result == "ERROR":
                errors += 1
            elif not result:
                empty_results += 1
            else:
                results.update(result)
    else:
        # Concurrent
        pbar = tqdm(total=num_batches, desc=f"  {label}", unit="call")
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = {executor.submit(resolve_batch, batch): batch
                       for batch in name_batches}
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result == "ERROR":
                    errors += 1
                elif not result:
                    empty_results += 1
                else:
                    with results_lock:
                        results.update(result)
                pbar.update(1)
        pbar.close()

    elapsed = time.time() - start
    recognized = sum(1 for v in results.values() if v and v.get('preferred_curie'))
    returned_no_curie = sum(1 for v in results.values() if v and not v.get('preferred_curie'))
    none_values = sum(1 for v in results.values() if v is None)  # silent API failures

    bench_results.append({
        "batch_size": batch_size,
        "workers": num_workers,
        "total_names": total_names,
        "num_calls": num_batches,
        "total_time": elapsed,
        "names_per_sec": total_names / elapsed,
        "avg_time_per_name": elapsed / total_names,
        "recognized": recognized,
        "no_curie": returned_no_curie,
        "none_values": none_values,
        "errors": errors,
        "empty": empty_results,
    })
    print(f"  -> {recognized} recognized, {returned_no_curie} returned-no-curie, "
          f"{none_values} None values (silent API failures), "
          f"{errors} errors, {empty_results} empty responses\n")

# Summary report
print("=" * 130)
print("BENCHMARK SUMMARY")
print("=" * 130)
print(f"{'Batch':>6} {'Workers':>8} {'Names':>8} {'Calls':>8} {'Total (s)':>10} "
      f"{'Names/sec':>10} {'ms/name':>10} {'Recognized':>14} {'NoCurie':>10} {'NullVals':>10} {'Errors':>8}")
print("-" * 130)
for r in bench_results:
    print(f"{r['batch_size']:>6} {r['workers']:>8} {r['total_names']:>8} {r['num_calls']:>8} "
          f"{r['total_time']:>10.1f} {r['names_per_sec']:>10.1f} {r['avg_time_per_name']*1000:>10.2f} "
          f"{r['recognized']}/{r['total_names']:<6} {r['no_curie']:>10} {r['none_values']:>10} {r['errors']:>8}")
print("=" * 130)
