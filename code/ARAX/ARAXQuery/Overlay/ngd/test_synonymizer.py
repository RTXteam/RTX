#!/usr/bin/env python3
"""Comprehensive NodeSynonymizer benchmark.

Loads names from sample_names.txt and runs them through the synonymizer in
both sync and async modes, printing a start/finish summary for each.

Usage:
    python test_synonymizer.py                        # use default URL
    python test_synonymizer.py --url https://...     # override URL
    python test_synonymizer.py --names-file other.txt
    python test_synonymizer.py --skip-sync
"""
import argparse
import logging
import os
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-7s %(name)s: %(message)s',
    datefmt='%H:%M:%S',
)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('bmt').setLevel(logging.WARNING)
logging.getLogger('linkml_runtime').setLevel(logging.WARNING)
logging.getLogger('node_synonymizer').setLevel(logging.INFO)

pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")
sys.path.append(os.path.sep.join(
    [*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'NodeSynonymizer']))
from node_synonymizer import NodeSynonymizer  # type: ignore  # noqa: E402


def load_names(names_file: str) -> list[str]:
    with open(names_file) as f:
        return [line.rstrip("\n") for line in f if line.strip()]


def print_header(title: str) -> None:
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)



def print_start(mode: str, syn: NodeSynonymizer, num_names: int) -> None:
    batch_size = syn._NR_BATCH_SIZE
    num_batches = (num_names + batch_size - 1) // batch_size
    print_header(f"STARTING — {mode}")
    print(f"  Total names:     {num_names}")
    print(f"  Batch size:      {batch_size}")
    print(f"  Num batches:     {num_batches}")
    print(f"  Max retries:     {syn._NR_MAX_RETRIES}")
    print(f"  Request timeout: {syn._NR_REQUEST_TIMEOUT}s")
    if mode == 'async':
        print(f"  Max concurrent:  {syn._NR_MAX_CONCURRENT}")
    print(f"  Endpoint:        {syn.name_resolver_url}")
    print()


def print_summary(
    mode: str, num_names: int, results: dict, elapsed: float,
) -> None:
    resolved = sum(1 for v in results.values() if v)
    unresolved = num_names - resolved
    pct = (resolved / num_names * 100) if num_names else 0.0
    throughput = (num_names / elapsed) if elapsed > 0 else 0.0
    print_header(f"{mode} SUMMARY")
    print(f"  Total names:    {num_names}")
    print(f"  Resolved:       {resolved}")
    print(f"  Unresolved:     {unresolved}")
    print(f"  Success rate:   {pct:.1f}%")
    print(f"  Wall time:      {elapsed:.2f}s")
    print(f"  Throughput:     {throughput:.1f} names/sec")
    print()


def run_mode(
    mode: str, names: list[str], url: str | None,
) -> tuple[float, int]:
    use_async = (mode == 'async')
    syn = NodeSynonymizer(autocomplete=False, use_async=use_async)
    if url:
        syn.name_resolver_url = url
    syn._NR_MAX_RETRIES = 1
    syn._NR_REQUEST_TIMEOUT = 60
    syn._NR_MAX_CONCURRENT = 5

    print_start(mode, syn, len(names))

    start = time.time()
    results = syn._call_name_resolver_api(names)
    elapsed = time.time() - start

    print_summary(mode, len(names), results, elapsed)
    resolved = sum(1 for v in results.values() if v)
    return elapsed, resolved


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark NodeSynonymizer name resolution")
    parser.add_argument(
        '--url', type=str, default=None,
        help="Override name_resolver_url (default: synonymizer's default)")
    parser.add_argument(
        '--names-file', type=str, default='sample_names.txt',
        help="Path to file with one name per line")
    parser.add_argument(
        '--skip-sync', action='store_true',
        help="Skip the sync run")
    parser.add_argument(
        '--skip-async', action='store_true',
        help="Skip the async run")
    args = parser.parse_args()

    names = load_names(args.names_file)
    if not names:
        print(f"ERROR: no names loaded from {args.names_file}")
        sys.exit(1)

    print(f"Loaded {len(names)} names from {args.names_file}")
    if args.url:
        print(f"URL override: {args.url}")

    sync_elapsed = async_elapsed = None
    sync_resolved = async_resolved = None

    if not args.skip_sync:
        sync_elapsed, sync_resolved = run_mode('sync', names, args.url)

    if not args.skip_async:
        async_elapsed, async_resolved = run_mode('async', names, args.url)

    if sync_elapsed is not None and async_elapsed is not None:
        print_header("COMPARISON")
        print(f"  Sync:   {sync_elapsed:6.2f}s  "
              f"{sync_resolved}/{len(names)} resolved")
        print(f"  Async:  {async_elapsed:6.2f}s  "
              f"{async_resolved}/{len(names)} resolved")
        if async_elapsed > 0:
            print(f"  Speedup: {sync_elapsed / async_elapsed:.1f}x")
        print()


if __name__ == '__main__':
    main()
