import time
import asyncio
import aiohttp
import os
import sys

pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'NodeSynonymizer']))
from node_synonymizer import NodeSynonymizer  # type: ignore

syn = NodeSynonymizer(autocomplete=False, retry=False)
URL = syn.name_resolver_url + '/bulk-lookup'

NGD_DIR = os.path.dirname(os.path.abspath(__file__))
NAMES_FILE = os.path.join(NGD_DIR, "sample_names.txt")

with open(NAMES_FILE) as f:
    all_names = [line.rstrip("\n") for line in f if line.strip()]

names_batches = [all_names[i:i + 50] for i in range(0, len(all_names), 50)]

PAYLOAD_BASE = {
    'autocomplete': False,
    'highlighting': False,
    'offset': 0,
    'limit': 1,
    'biolink_types': [],
    'only_prefixes': '',
    'exclude_prefixes': '',
    'only_taxa': '',
}

print(f'{len(names_batches)} batches x 50 names = {len(all_names)} names total')
print()

# ASYNC via aiohttp with semaphore (max 5 at a time)
async def run_async():
    sem = asyncio.Semaphore(5)
    total_resolved = 0
    total_nones = 0

    async with aiohttp.ClientSession(headers={'accept': 'application/json'}) as session:
        async def fetch_batch(batch_num, batch):
            async with sem:
                print(f'Sending #{batch_num} now!')
                payload = {**PAYLOAD_BASE, 'strings': batch}
                try:
                    async with session.post(URL, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                        data = await resp.json()
                        t = len(data)
                        x = sum(1 for v in data.values() if not v)
                        resolved = t - x
                        print(f'Got #{batch_num} back! None: {x}, Resolved: {resolved}')
                        return resolved, x
                except Exception as e:
                    print(f'Got #{batch_num} back! FAILED: {e}')
                    return 0, len(batch)

        tasks = [fetch_batch(i, batch) for i, batch in enumerate(names_batches, 1)]
        results = await asyncio.gather(*tasks)
        total_resolved = sum(r for r, _ in results)
        total_nones = sum(n for _, n in results)

    return total_resolved, total_nones


start = time.time()
async_resolved, async_nones = asyncio.run(run_async())
async_elapsed = time.time() - start

print()
print(f'{"="*50}')
print(f'ASYNC SUMMARY')
print(f'{"="*50}')
print(f'  Total names:    {len(all_names)}')
print(f'  Resolved:       {async_resolved}')
print(f'  Unresolved:     {async_nones}')
print(f'  Success rate:   {async_resolved/len(all_names)*100:.1f}%')
print(f'  Wall time:      {async_elapsed:.2f}s')
print(f'  Throughput:     {len(all_names)/async_elapsed:.1f} names/sec')
