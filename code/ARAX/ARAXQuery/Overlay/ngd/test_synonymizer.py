#!/usr/bin/env python3
import logging
import os
import sys
import time

logging.basicConfig(level=logging.INFO,
    format='%(asctime)s %(levelname)-7s %(name)s: %(message)s',
    datefmt='%H:%M:%S')
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('bmt').setLevel(logging.WARNING)
logging.getLogger('linkml_runtime').setLevel(logging.WARNING)
logging.getLogger('node_synonymizer').setLevel(logging.WARNING)

pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'NodeSynonymizer']))
from node_synonymizer import NodeSynonymizer  # type: ignore


def load_names(names_file: str):
    with open(names_file) as f:
        return [line.rstrip("\n") for line in f if line.strip()]


names = load_names("sample_names.txt")

syn = NodeSynonymizer(autocomplete=False, use_async=True)
syn._NR_MAX_RETRIES = 1

start = time.time()
results = syn._call_name_resolver_api(names)
elapsed = time.time() - start

resolved = sum(1 for v in results.values() if v)
print()
print("=" * 50)
print("ASYNC SUMMARY")
print("=" * 50)
print(f"  Total names:    {len(names)}")
print(f"  Resolved:       {resolved}")
print(f"  Unresolved:     {len(names) - resolved}")
print(f"  Success rate:   {resolved / len(names) * 100:.1f}%")
print(f"  Wall time:      {elapsed:.2f}s")
print(f"  Throughput:     {len(names) / elapsed:.1f} names/sec")