import json 
import os 
import pandas as pd 


NODE_FILE = os.path.expanduser("~/Desktop/code/database/tier0-20260621/knowledge_graph/nodes.jsonl")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NODES_TABLE = os.path.join(BASE_DIR, "data", "nodes_table.parquet")
_GENERIC_CATS = {
    "biolink:NamedThing", "biolink:Entity", "biolink:BiologicalEntity",
    "biolink:OntologyClass", "biolink:ThingWithTaxon",
    "biolink:PhysicalEssence", "biolink:PhysicalEssenceOrOccurrent",
    "biolink:Occurrent", "biolink:PhysicalEntity",
}

def most_specific_category(cats: list[str]) -> str:
    for c in cats:
        if c in _GENERIC_CATS or "Or" in c or c.endswith("Mixin"):
            continue
        return c
    return cats[0] if cats else ""

rows = []

with open(NODE_FILE, encoding="utf-8") as nodes: 
    for line in nodes: 
        node = json.loads(line)
        name = node["name"]
        description = node.get("description")
        rows.append({
            "id": node["id"], 
            "name": name,
            "description": description,
            "most_specific_category": most_specific_category(node["category"]),
            "information_content": node.get("information_content"),
            "text": f"{name}: {description}" if description else name 
        })
        if len(rows) % 100_000 == 0:
            print(f"  {len(rows):,}")

df = pd.DataFrame.from_records(rows)
df["most_specific_category"] = df["most_specific_category"].astype("category")
df.to_parquet(NODES_TABLE, index=False)

