#!/usr/bin/env python3

import json
import sys
import re

if len(sys.argv) != 3:
    print("Usage: script.py input.jsonl output.tsv")
    sys.exit(1)

inp, out = sys.argv[1], sys.argv[2]

def clean(s):
    if s is None:
        return ""
    return re.sub(r"\s+", " ", str(s)).strip()

with open(inp) as fin, open(out, "w") as fout:
    fout.write("id\tname\n")
    for line in fin:
        try:
            obj = json.loads(line)
            node_id = clean(obj.get("id"))
            name = clean(obj.get("name"))
            fout.write(f"{node_id}\t{name}\n")
        except Exception:
            continue  # skip bad lines
