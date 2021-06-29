## To build the NGD database

### First set up your environment:

You need to make your environment point to the KG2 and synonymizer you want to use.

1. **Put your `config_local.json` into place**: This config file should point to the KG2 you want to use (i.e., its neo4j endpoint) and the synonymizer you want to use (i.e., the one made from the KG2 you'll be using). Put it into `RTX/code/`.
1. **Put your synonymizer into place**: Put a copy of the synonymizer you want to use (e.g., `node_synonymizer_v1.0_KG2.6.7.sqlite`) into `RTX/code/ARAX/NodeSynonymizer/`.

### Then do the build:

If `conceptname_to_pmids.db` doesn't already exist on the machine you'll be running this build on (or it's due for a refresh - it should be refreshed maybe twice a year or so):
1. Download the PubMed XML files (into whatever directory you want)
1. Do a full build by running: `python build_ngd_database.py [path_to_your_pubmed_xml_directory] --full`

Otherwise if you already have a `conceptname_to_pmids.db` you want to use:

1. Do a partial build by running `python build_ngd_database.py [path_to_your_pubmed_xml_directory]`