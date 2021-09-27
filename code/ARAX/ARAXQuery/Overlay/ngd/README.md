## To build the NGD database

### First set up your environment:

You need to make your environment point to the KG2 and synonymizer you want to use.

1. **Put your `config_local.json` into place**: This config file should point to the KG2 you want to use (i.e., its neo4j endpoint) and the synonymizer you want to use (i.e., the one made from the KG2 you'll be using). Put it into `RTX/code/`.
1. **Put your synonymizer into place**: Put a copy of the synonymizer you want to use (e.g., `node_synonymizer_v1.0_KG2.6.7.sqlite`) into `RTX/code/ARAX/NodeSynonymizer/`.

### Then do the build:

You have two options: a full build or a partial build.

#### Full build

If you want to use the latest PubMed files for this NGD build or the machine you're using has never previously 
run an NGD build, do a full build:
```
cd RTX/code/ARAX/ARAXQuery/Overlay/ngd
python3 build_ngd_database.py --full
```
This will automatically download and use the latest PubMed XML files, including both the annual 'baseline' files and 
the 'update' files. Note that full builds take 8+ hours and require more than 64G of RAM.

#### Partial build

Otherwise you can just do a partial build:
```
cd RTX/code/ARAX/ARAXQuery/Overlay/ngd
python3 build_ngd_database.py
```
This will use the existing `conceptname_to_pmids.db` artifact on your machine 
(in `RTX/code/ARAX/ARAXQuery/Overlay/ngd/`), which will shave several hours off the build time. Partial builds take 
about 45 minutes and require around 60G of RAM.

The resulting database will be saved at `RTX/code/ARAX/ARAXQuery/Overlay/ngd/curie_to_pmids.sqlite`.