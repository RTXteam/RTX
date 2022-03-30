# What is KG2canonicalized?

KG2canonicalized (KG2c) is a version of KG2 in which synonymous nodes have been merged. It is built from the [KG2pre](https://github.com/RTXteam/RTX-KG2) Neo4j endpoint and uses the [ARAX NodeSynonymizer](https://github.com/RTXteam/RTX/tree/master/code/ARAX/NodeSynonymizer) to determine which nodes are equivalent. 

### Schema

###### Example KG2c node:
```
{
  "id": "CHEMBL.COMPOUND:CHEMBL3349001",
  "name": "AVN-944",
  "category": "biolink:SmallMolecule",
  "iri": "https://identifiers.org/chembl.compound:CHEMBL3349001",
  "description": "UMLS Semantic Type: UMLSSC:T121; UMLS Semantic Type: UMLSSC:T109; AVN944 is a biotech drug that demonstrated a statistically meaningful impact on IMPDH and other proteins that are critical to activities in cancer cells, including nucleotide biosynthesis, energy and metabolism, DNA replication, apoptosis and cell cycle control. AVN944 has been associated with cancer cell death in clinical trials. It is being investigated for the treatment of patients with advanced hematologic malignancies.",
  "equivalent_curies": [
    "MESH:C526922",
    "DRUGBANK:DB05500",
    "CHEMBL.COMPOUND:CHEMBL3349001"
  ],
  "all_names": [
    "AVN-944",
    "Avn 944",
    "Avn-944"
  ],
  "all_categories": [
    "biolink:ChemicalEntity",
    "biolink:SmallMolecule"
  ],
  "publications": [
    "PMID:17462731",
    "PMID:17659481"
  ]
}
```
The node `id` is the 'preferred' curie for the group of synonymous nodes this KG2c node represents (according to the ARAX `NodeSynonymizer`). Similarly, the node `category` and `name` are the 'preferred' category/name, according to the `NodeSynonymizer`.

In the Neo4j instantiation of KG2c (see [below section](#host-kg2canonicalized-in-neo4j) for how to host KG2c in Neo4j), nodes are labeled with their `all_categories` and ancestors of those categories.

###### Example KG2c edge:
```
{
  "id": "26507826",
  "subject": "UMLS:C4683553",
  "object": "MONDO:0000001",
  "predicate": "biolink:treats",
  "knowledge_source": [
    "infores:semmeddb"
  ],
  "kg2_ids": [
    "UMLS:C4683553---SEMMEDDB:treats---UMLS:C0012634---SEMMEDDB:"
  ],
  "publications": [
    "PMID:34141790"
  ],
  "publications_info": "{'PMID:34141790': {'publication date': '2021 Jun 16', 'sentence': 'Recently, the use of ALK inhibitors for the treatment of this disease has been reported.', 'subject score': 983, 'object score': 1000}}"
}
```
In creating KG2c, edges from KG2pre are remapped to use only 'preferred' curies for their `subject` and `object`; edges with the same `subject`, `object`, and `predicate` are then merged.

The `kg2_ids` property captures the IDs of the edges in KG2pre that this KG2c edge was created from. 

# How to create it

### Build KG2canonicalized

If the machine you'll be using has never previously built a KG2c, you need to do some environmental set-up:

1. If you are creating this KG2c from a **standard KG2pre** instance (made by the RTX-KG2 team):
    1. Follow steps 1-3 in [this section](https://github.com/RTXteam/RTX/wiki/Dev-info#setting-up-for-local-dev-work-on-arax) of the ARAX dev wiki
    1. If you wish to upload your eventual output KG2c files to S3:
        1. Install AWS CLI: `sudo apt-get install -y awscli`
        1. And configure it: `aws configure`
        1. You will need read and write permission for the `rtx-kg2` S3 bucket
1. Otherwise if you are creating this KG2c from your own **custom KG2pre**:
    1. Create a copy of `configv2.json` that contains the proper secrets for your own KG2pre Neo4j endpoint

To run the build:

1. Make sure you have the **latest code** from whatever branch you'll be doing the build from (e.g., do `git pull origin master` if you're doing this build from the `master` branch)
1. Locally modify the KG2c build **config file** (`RTX/code/kg2c/kg2c_config.json`) for your particular needs:
    - `kg2pre_version`: Specify the KG2pre version you want to build this KG2c from (e.g., 2.6.7)
    - `kg2pre_neo4j_endpoint`: Should point to the Neo4j endpoint for your specified KG2pre version (e.g., `kg2endpoint-kg2-6-7.rtx.ai`)
    - `biolink_version`: Should match the Biolink version used by the KG2pre you specified (e.g., 1.8.1)
    - `upload_to_arax.ncats.io`: Specify whether build artifacts should be uploaded to arax.ncats.io (generally should be `true` unless you're doing a debugging build)
    - `upload_directory`: The path to the directory on arax.ncats.io where artifacts should be uploaded (e.g., `/translator/data/orangeboard/databases/KG2.6.7`)
        - NOTE: You must manually create this directory on `arax.ncats.io` before kicking off the build (if it doesn't already exist)
        - **WARNING**: If this is pointing to the wrong directory on arax.ncats.io, data may be overwritten! Be careful.
    - Under the `synonymizer` slot:
        - `build`: Set this to true if you want to build a **new** synonymizer (from your specified KG2pre version), false otherwise
        - `name`: The name of the synonymizer to use (if you're building a new synonymizer, it will be given this name)
            - NOTE: If you're not building a new synonymizer, you must ensure that a synonymizer with the name specified in this slot already exists in the `RTX/code/ARAX/NodeSynonymizer` directory in your clone of the repo
            - **WARNING**: Always double-check this slot; if an old synonymizer name is specified here, things can get very confusing downstream!
    - Under the `kg2c` slot:
        - `build`: Specify whether you want a KG2c to be built (sometimes it can be useful to build only a synonymizer and not a KG2c)
        - `use_nlp_to_choose_descriptions`: This should generally be set to `true`, unless you're doing a 'debugging' build that doesn't involve debugging of node descriptions. In that case you may want to set this to `false` because it will shave a few hours off the build time. (When `true`, an NLP method will be used to choose the best node descriptions; when `false`, the longest description under a certain limit will be chosen.)
        - `upload_to_s3`: Indicates whether you want the final output KG2c files (JSON and a tarball of TSVs) to automatically be uploaded to the KG2 S3 bucket (this should generally be `true` unless you're doing a 'debugging' build)
        - `start_from_kg2c_json`: Set to `true` if you want to resume a build starting with the `kg2c.json` in `RTX/code/kg2c`. (Allows partial builds starting from the point after canonicalization is done.)
        - `use_local_kg2pre_tsvs`: Set to `true` if you **don't** want the latest KG2pre TSVs to be downloaded from the `rtx-kg2` S3 bucket; if set to true, you must make sure your four Neo4j-ready KG2pre TSVs are in `RTX/code/kg2c/kg2pre_tsvs/`.
1. Then do the actual build (should take ~200GB of RAM and 2-11 hours depending on your settings in `kg2c_config.json`):
    - `python3 RTX/code/kg2c/build_kg2c.py`

In the end, KG2c will be created and stored in multiple file formats, including TSVs ready for import into Neo4j.

### Build only an ARAX NodeSynonymizer

If you want to build _only_ an ARAX NodeSynonymizer from your KG2 version, follow the same steps as in the [above section](#build-kg2canonicalized),
simply making sure to set the `kg2c` --> `build` slot in the config file to `false` and the `synonymizer` --> `build` slot to `true`.

This will build a synonymizer from the KG2pre specified in your `kg2c_config.json` and then halt before building
a KG2c. This can be very useful when debugging conflations or other synonymization issues. In particular, after your
synonymizer build is done, you may want to inspect the artifact located at `RTX/code/ARAX/NodeSynonymizer/problems.tsv`
and compare it to that of previous synonymizer builds.

If you build a synonymizer and then decide you want to move forward with a KG2c build using it, just adjust your
config file once again:
* Set the `kg2c` --> `build` slot to `true`
* Set the `synonymizer` --> `build` slot to `false`

And then once again run `python3 RTX/code/kg2c/build_kg2c.py`.

### Host KG2canonicalized in Neo4j

These instructions assume Neo4j is not already installed and that you are hosting Neo4j on an AWS instance.

(1) Clone the `RTX` repo into the instance's home directory (if you haven't already):
```
cd ~
git clone https://github.com/RTXteam/RTX.git
```

(2) Set up the instance for Neo4j:
```
python3 RTX/code/kg2c/setup_for_neo4j.py
```

(3) Load the latest KG2c into Neo4j:
```
bash -x RTX/code/kg2c/tsv-to-neo4j-canonicalized.sh
```

### Upload KG2C to KGE (Knowledge Graph Exchange)
##### Generate TSV files

The following should be run in the build system, typically `buildkg2c.rtx.ai`, in the folder where the files `nodes_c.tsv` and `edges_c.tsv` are stored. 

(1) Use python3.7 in a virtual environment and install kgx, if kgx has not yet been installed.
```
python3.7 -m venv venv
venv/bin/pip3.7 install kgx
source venv/bin/activate
```

(2) Run the script `kg2c_tsv_to_kgx_tsv.py` to generate output files `nodes.tsv` and `edges.tsv`.
```
python3.7 kg2c_tsv_to_kgx_tsv.py
```

(3) Validate output files and generate `content_metadata.json` using `kgx-validation-and-metagraph.sh`.
```
bash -x kgx-validation-and-metagraph.sh
```

##### Upload to KGE 

(4) Upload `edges.tsv`, `nodes.tsv`, and `content_metadata.json` to a public S3 bucket. 
```
aws s3 sp edges.tsv s3://rtx-kg2-public
aws s3 sp nodes.tsv s3://rtx-kg2-public
aws s3 sp content_metadata.json s3://rtx-kg2-public
```

(5) Upload `edges.tsv`, `nodes.tsv`, and `content_metadata.json` to the Knowledge Graph Exchange at `https://archive.translator.ncats.io/home`. Select `RTX_KG2c` from the dropdown next to `Choose a Knowledge Graph`. Click `Add a new file set`. Use the URLs for each file in the S3 buckets to upload to KGE. 

(6) Click `Done uploading` once all three files are uploaded. 

(7) Rename `edges.tsv`, `nodes.tsv`, and `content_metadata.json` with current version number and move to private s3 bucket, `s3://rtx-kg2`.

# Contact
## Maintainer
- Amy Glen, Oregon State University (glena@oregonstate.edu)
