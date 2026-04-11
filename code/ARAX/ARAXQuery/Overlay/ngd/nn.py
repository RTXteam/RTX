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

# SYNC via NodeSynonymizer
start = time.time()
sync_resolved = 0
for i, batch in enumerate(names_batches, 1):
    print(f'Sending batch #{i}! Here is the sample: {batch}')
    result = syn._call_name_resolver_api(batch)
    print(f'Got back batch #{i}! Here it is: {result}')
    sync_resolved += sum(1 for v in result.values() if v)
sync_elapsed = time.time() - start
print(f'SYNC (sequential):  {sync_elapsed:.2f}s  resolved {sync_resolved}/{len(all_names)}')

# ASYNC via aiohttp with semaphore (max 5 at a time)
async def run_async():
    sem = asyncio.Semaphore(5)
    total_resolved = 0

    async with aiohttp.ClientSession(headers={'accept': 'application/json'}) as session:
        async def fetch_batch(batch):
            async with sem:
                payload = {**PAYLOAD_BASE, 'strings': batch}
                async with session.post(URL, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    data = await resp.json()
                    return sum(1 for v in data.values() if v)

        tasks = [fetch_batch(batch) for batch in names_batches]
        results = await asyncio.gather(*tasks)
        total_resolved = sum(results)

    return total_resolved


start = time.time()
async_resolved = asyncio.run(run_async())
async_elapsed = time.time() - start
print(f'ASYNC (concurrent): {async_elapsed:.2f}s  resolved {async_resolved}/{len(all_names)}')

print()
print(f'Speedup: {sync_elapsed / async_elapsed:.1f}x')
