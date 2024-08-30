# What is KG2canonicalized?

RTX-KG2canonicalized (RTX-KG2c, or simply KG2c) is a version of RTX-KG2 in which synonymous nodes have been merged. 
Its build process consists of:
1) [building a NodeSynonymizer](https://github.com/RTXteam/RTX/tree/master/code/kg2c/synonymizer_build) based on information in [RTX-KG2pre](https://github.com/RTXteam/RTX-KG2) as well as two other sources,
1) using that NodeSynonymizer to identify synonymous nodes in [RTX-KG2pre](https://github.com/RTXteam/RTX-KG2), and
1) merging the synonymous nodes (i.e., doing entity resolution).

### Graph schema

Like RTX-KG2pre, KG2c adheres to the [Biolink model](https://github.com/biolink/biolink-model) for its semantic layer and schema.

###### Example KG2c node:
```
{
  "id": "CHEBI:40116",
  "name": "propyl acetate",
  "category": "biolink:SmallMolecule",
  "iri": "http://purl.obolibrary.org/obo/CHEBI_40116",
  "description": "Propyl acetate, also known as 1-acetoxypropane or propyl ethanoate, belongs to the class of organic compounds known as carboxylic acid esters. These are carboxylic acid derivatives in which the carbon atom from the carbonyl group is attached to an alkyl or an aryl moiety through an oxygen atom (forming an ester group). It is formed by the esterification of acetic acid and 1-propanol (known as a condensation reaction), often via Fischer–Speier esterification, with sulfuric acid as a catalyst and water produced as a byproduct. This clear, colorless liquid is known by its characteristic odor of pears. Propyl acetate is a drug. Propyl acetate is a bitter, celery, and fruity tasting compound. It has been detected, but not quantified, in several different foods, such as muskmelons, figs, apples, pineapples, and cocoa beans. Due to this fact, it is commonly used in fragrances and as a flavor additive. Propyl acetate has been found to be associated with the diseases such as nonalcoholic fatty liver disease; also propyl acetate has been linked to the inborn metabolic disorders including celiac disease.",
  "equivalent_curies": [
    "RXNORM:1649519",
    "MESH:C026498",
    "UMLS:C0072214",
    "UNII:4AWM8C91G6",
    "DRUGBANK:DB01670",
    "RXCUI:1649519",
    "CHEMBL.COMPOUND:CHEMBL44857",
    "CHEBI:40116",
    "HMDB:HMDB0034237",
    "PUBCHEM.COMPOUND:7997",
    "CAS:109-60-4",
    "INCHIKEY:YKYONYBAUNKHLG-UHFFFAOYSA-N"
  ],
  "all_names": [
    "propyl acetate",
    "ACETIC ACID PROPYL ESTER",
    "Propyl acetate"
  ],
  "all_categories": [
    "biolink:SmallMolecule",
    "biolink:Drug"
  ],
  "publications": [
    "PMID:2033592",
    "PMID:15857133"
  ]
}
```
The node `id` is the 'preferred' curie for the group of synonymous nodes this KG2c node represents (according to the `NodeSynonymizer`). Similarly, the node `category` and `name` are the 'preferred' category/name, according to the `NodeSynonymizer`.

In the Neo4j instantiation of KG2c (see [below section](#host-kg2canonicalized-in-neo4j) for how to host KG2c in Neo4j), nodes are labeled with their `all_categories` and ancestors of those categories.

###### Example KG2c edge:
```
{
  "id": "26507826",
  "subject": "UMLS:C4683553",
  "object": "MONDO:0000001",
  "predicate": "biolink:treats",
  "primary_knowledge_source": "infores:semmeddb"
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

# How to build KG2c

### Initial set up

If the machine you'll be using has never previously built a KG2c, you need to do some environmental set-up:

1. If you are creating this KG2c from a **standard KG2pre** instance (made by the RTX-KG2 team):
    1. Follow steps 1-3 in [this section](https://github.com/RTXteam/RTX/wiki/Dev-info#setting-up-for-local-dev-work-on-arax) of the ARAX dev wiki
    1. If you wish to upload your eventual output KG2c files to S3:
        1. Install AWS CLI: `sudo apt-get install -y awscli`
        1. And configure it: `aws configure`
        1. You will need read and write permission for the `rtx-kg2` S3 bucket
1. Otherwise if you are creating this KG2c from your own **custom KG2pre**:
    1. Create a copy of `config_secrets.json` that contains the proper secrets for your own KG2pre Neo4j endpoint
1. Make sure you've installed packages from **both** of these requirements.txt files:
   1. `pip install -r RTX/requirements.txt`
   2. `pip install -r RTX/code/kg2c/requirements.txt`

### Building KG2c

#### Recommended steps

At a high level, building KG2c consists of running **two scripts**: one to build the NodeSynonymizer and one to build 
the actual KG2c graph. It requires ~200GB of RAM; we run the build on an `r5a.8xlarge` AWS EC2 instance 
(`buildkg2c.rtx.ai`).

The steps we recommend to do the build are listed below; we are pretending that the KG2pre version we want to build
this KG2c from is 2.10.0, the Biolink model version that that KG2pre uses is 4.2.0, and the 'sub-version' for this 
build is v1.0. See the [Build options section](#build-options) for an explanation of the sub-version and other 
flags/options.

1. Make sure you have the **latest code** from whatever branch of the **RTX** repo you'll be doing the build from
(e.g., do `git checkout kg2.10.0c` and `git pull origin kg2.10.0c` if want to do this build from the `kg2.10.0c` branch)
1. **Build the synonymizer**:
   1. `screen -S synonymizer`
   1. `pyenv activate rtx` if you're using buildkg2c.rtx.ai; otherwise activate your python environment however necessary
   1. `cd RTX/code/kg2c/synonymizer_build`
   2. `python build_synonymizer.py 2.10.0 v1.0 --downloadkg2pre --uploadartifacts`
   1. once the build finishes, run the regression test suite:
      1. `pytest -vs test_synonymizer.py --synonymizername node_synonymizer_v1.0_KG2.X.Y.sqlite`
1. **Do a test KG2c build**: If you're satisfied with the synonymizer, proceed with a test KG2c build:
   2. `screen -S kg2c`
   3. `pyenv activate rtx` if you're using buildkg2c.rtx.ai; otherwise activate your python environment however necessary
   1. `cd RTX/code/kg2c`
   4. `python build_kg2c.py 2.10.0 v1.0 4.2.0 --uploadartifacts --test`
1. **Do the full KG2c build**: Then, if everything went smoothly, do the full build (we're assuming you're in the same `screen` session):
   4. `python build_kg2c.py 2.10.0 v1.0 4.2.0 --uploadartifacts`

The synonymizer build should take around 5 hours and the KG2c build should take around 10 hours.

In the end, KG2c will be created and stored in multiple file formats, including TSVs ready for import into Neo4j.

#### Build options

You can see explanations for the different **synonymizer build** options by running 
`python RTX/code/kg2c/synonymizer_build/build_synonymizer.py --help`, which spits this info out to the command line:
```commandline
usage: build_synonymizer.py [-h] [-d] [-u] kg2pre_version sub_version [start_at]

positional arguments:
  kg2pre_version        The version of KG2pre to build this synonymizer from (e.g., 2.10.0).
  sub_version           The sub-version for this KG2c build (e.g., v1.0); we always use v1.0 the
                        first time we are building KG2c from a given KG2pre version; if we do a
                        second build of KG2c from that *same* KG2pre version, we would use v1.1,
                        and so on.
  start_at              Optional parameter that specifies the step in the synonymizer build to
                        begin at (default is 1; valid values are 1-5). Allows partial builds of
                        the synonymizer; used only for development purposes. Step 1 is building
                        the KG2pre match graph, 2 is building the SRI NodeNormalizer match graph,
                        3 is merging the match graphs, 4 is clustering the merged match graph,
                        and 5 is creating the final synonymizer sqlite and build reports.

optional arguments:
  -h, --help            show this help message and exit
  -d, --downloadkg2pre  Specifies that the KG2pre TSV files should be downloaded from S3. If this
                        flag is not set, local KG2pre TSVs will be used.
  -u, --uploadartifacts
                        Specifies that artifacts of the build should be uploaded to the ARAX
                        databases server.
```

Similarly, you can see explanations for the different **KG2c build** options by running 
`python RTX/code/kg2c/build_kg2c.py --help`, which spits this info out to the command line:

```commandline
usage: build_kg2c.py [-h] [-d] [-u] [-t]
                     kg2pre_version sub_version biolink_version [synonymizer_override]

positional arguments:
  kg2pre_version        The version of KG2pre to build this KG2c from (e.g., 2.10.0).
  sub_version           The sub-version for this KG2c build (e.g., v1.0); we always use v1.0 the first
                        time we are building KG2c from a given KG2pre version; if we do a second build
                        of KG2c from that *same* KG2pre version, we would use v1.1, and so on.
  biolink_version       The Biolink version that the given KG2pre version uses (e.g., 4.2.0). You can
                        look this up on the KG2pre versions markdown page at: github.com/RTXteam/RTX-
                        KG2/blob/master/docs/kg2-versions.md
  synonymizer_override  Optional parameter that specifies the file name of the synonymizer you want to
                        force this KG2c build to use (e.g., node_synonymizer_v1.0_KG2.9.0.sqlite); used
                        for development work. The file you specify must be present in the
                        RTX/code/ARAX/NodeSynonymizer subdir locally. By default, the build will
                        determine the synonymizer file name based on the kg2pre_version and sub_version
                        parameters, but you can override that with this optional parameter.

optional arguments:
  -h, --help            show this help message and exit
  -d, --downloadkg2pre  Specifies that the KG2pre TSV files should be downloaded from S3. If this flag
                        is not set, local KG2pre TSVs will be used.
  -u, --uploadartifacts
                        Specifies that artifacts of the build should be uploaded to the ARAX databases
                        server and to the RTX-KG2 S3 bucket.
  -t, --test            Specifies whether to do a test build. Test builds create a smaller version of
                        the KG2pre TSVs and do a KG2c build off of those. They ensure that the test
                        graph does not include any orphan edges. All output files from test builds are
                        named with a '_TEST' suffix.
```



### Hosting KG2c in Neo4j
The Neo4j instances are usually present on the AWS EC2 instances `KG2canonicalized.rtx.ai` and `KG2canonicalized2.rtx.ai`.  
Please check the **CNAME** to **ANAME** mapping on **AWS Lightsail** to verify what EC2 instance's Neo4j to update with the latest KG2c version. 

If you are using an already deployed instance, pull the latest code from the `master` branch into the instance and run the following command:  
**NOTE:** Once the below command is executed, you will not be able to downgrade the KG2c version.  
```
bash -x RTX/code/kg2c/tsv-to-neo4j-canonicalized.sh
```
If Neo4j is not already installed and that you are hosting Neo4j on an AWS **Ubuntu 18** EC2 instance. (You are expected to have AWS credentials to access the instance).

If this is a brand-new Ubuntu 18.04 instance, you will need to make sure that `gcc`
is installed (`which gcc`) and if it is not installed, install it using `sudo apt-get install -y gcc`.

(1) Clone the `RTX` repo into the instance's home directory (if you haven't already):
```
cd ~
git clone https://github.com/RTXteam/RTX.git
```

(2) Clone the `RTX-KG2` repo into the instance's `/home/ubuntu` directory:
```
git clone https://github.com/RTXteam/RTX-KG2.git
```

(3) Set up the instance for Neo4j:
```
python3 RTX/code/kg2c/setup_for_neo4j.py
```

(4) Load the latest KG2c into Neo4j:
```
bash -x RTX/code/kg2c/tsv-to-neo4j-canonicalized.sh
```


# Contact
## Maintainer
- Amy Glen, Oregon State University (glena@oregonstate.edu)
- Sundareswar Pullela, Oregon State University (pullelas@oregonstate.edu)
