import json, requests

BASE = "https://arax.ncats.io/test/api/arax/v1.4/query"
DISEASE = "MONDO:0005575"                      # Colorectal Cancer (TestCase_58)
EXPECTED = ["PUBCHEM.COMPOUND:4091", "UNII:6T8C155666"]  # Metformin, Ipilimumab

query = {"message": {"query_graph": {
    "nodes": {"ON": {"ids": [DISEASE], "categories": ["biolink:Disease"]},
            "SN": {"categories": ["biolink:ChemicalEntity"]}},
    "edges": {"e01": {"object": "ON", "subject": "SN",
                    "predicates": ["biolink:treats"],
                    "knowledge_type": "inferred"}}}}}

r = requests.post(BASE, json=query, timeout=600)
r.raise_for_status()
resp = r.json()

results = resp.get("message", {}).get("results", []) or []
kg_nodes = resp.get("message", {}).get("knowledge_graph", {}).get("nodes", {}) or {}
print(f"PK: https://arax.ncats.io/test?r={resp.get('id','').split('/')[-1]}")
print(f"results returned: {len(results)}")

# 1) the filter's own log lines
print("\n--- NGD-inf / creative-mode filter log lines ---")
hits = 0
for log in resp.get("logs", []) or []:
    msg = log.get("message", "") if isinstance(log, dict) else str(log)
    if any(k in msg for k in ("NGD-inf", "creative-mode", "no results remain", "eliminated")):
        lvl = log.get("level", "") if isinstance(log, dict) else ""
        print(f"[{lvl}] {msg}")
        hits += 1
if not hits:
    print("(no matching log lines — filter debug logs may be suppressed at this log level)")

# 2) did the expected answers survive?
print("\n--- expected answers present? ---")
for cur in EXPECTED:
    in_kg = cur in kg_nodes
    print(f"  {cur:22} in knowledge_graph.nodes = {in_kg}")
