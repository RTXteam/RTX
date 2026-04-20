# `generate_fda_pickle.py`

Generates the pickled set of FDA approved drug CURIEs that ARAX uses to flag which chemical/drug nodes in a result set are FDA approved. The output is a single pickle containing a Python `set[str]` of canonical CURIEs, loaded by `ARAX_expander.py` at query time.

## Requirements

**Software**

| | |
| :--- | :--- |
| Python | 3.10+. No version specific syntax is used. |


**Hardware**

| | |
| :--- | :--- |
| RAM | 8 GB free is enough. DrugBank XML (~1.5 GB) is parsed in full via `xml.etree.ElementTree.parse`, so the parse tree sits in memory. Babel queries are point wise and add negligible overhead. |
| Cores | 1. Single process, single threaded. |
| Disk | Output pickle is ~100 KB. No significant temp space needed. |
| Wall clock | A few minutes. Dominated by the XML parse plus roughly one Babel sqlite roundtrip per approved DrugBank CURIE. |

**Filesystem and inputs**

| | |
| :--- | :--- |
| Read access | DrugBank XML dump (`drugbank.xml`, ~1.5 GB; from s3 bucket). Local Babel sqlite (hundreds of GB; opened read only). |
| Write access | output pickle path |
| Env vars | None |

## Inputs

* `--drugbank_xml` : DrugBank's full database XML dump (e.g. `drugbank.xml`). This carries per drug approval status inside each `<drug><groups>...` element.
* `--babel_db` : path to a local Babel sqlite (e.g. `babel-20250901-p1.sqlite`). Used to canonicalize each DrugBank CURIE to whatever clique representative identifier tier0 uses.

## Output

* `--output_pickle` : a pickled `set[str]` of canonical CURIEs, one per FDA approved drug.

## What the script does

1. Parse the DrugBank XML and pull every `<drug>` whose `<groups>` contains `approved`. Each one contributes its primary `drugbank-id` as a CURIE of the form `DRUGBANK:DB00123`.
2. Open the local Babel sqlite read only. For each DrugBank CURIE, map it to its synonym clique(s) via `lb.map_any_curie_to_cliques` and collect the clique's representative identifier. This is the canonicalization step, so the resulting CURIEs line up with whatever tier0 nodes refer to the same concept.
3. Write the deduplicated set of canonical CURIEs to the output pickle.

The core helpers are:

* `extract_approved_drugbank_ids(xml_path)`: DrugBank XML parse plus approval filter.
* `canonicalize_ids(curie_ids, babel_db_path)`: local Babel lookup loop that returns the dedup'd canonical set.

Prints simple progress to stdout (extraction count, canonicalization count, "Done.").

## How to run

```bash
python generate_fda_pickle.py \
    --drugbank_xml  /path/to/drugbank.xml \
    --babel_db      /path/to/babel-YYYYMMDD-pN.sqlite \
    --output_pickle /path/to/fda_approved_drugs_vX.Y.pickle
```

All three flags have defaults that match the standard kg2 build host layout, so on a provisioned build box you can omit them.

## Downstream consumer

`code/ARAX/ARAXQuery/ARAX_expander.py::_load_fda_approved_drug_ids`. It loads the pickle from `code/ARAX/KnowledgeSources/` using the filename in `rtxc.fda_approved_drugs_path` (configured in `config_dbs.json` as `fda_approved_drugs`). The loaded set is used to check which drug nodes in a query result are FDA approved.
