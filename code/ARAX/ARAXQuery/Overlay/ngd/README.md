## To build the NGD database

### First set up your environment:

_Note to ARAX team: We typically do this build on the `ngdbuild.rtx.ai` instance._

You need to make your environment point to the particular KG2pre version and synonymizer you want to use.

1. **Point to the right KG2 version**: Make sure that `RTX/code/config_dbs.json` is pointing to the KG2pre Neo4j endpoint you want to use and the synonymizer you want to use (i.e., the one made from the KG2 version you'll be using).
2. **Put your synonymizer into place**: Put a copy of the synonymizer you want to use (e.g., `node_synonymizer_v1.0_KG2.6.7.sqlite`) into `RTX/code/ARAX/NodeSynonymizer/`.
3. **Fetch the latest code**: Do `git pull origin [your-branch]` or the like to make sure you're running the latest code in whatever branch you're using.
4. **Activate virtual env**: Make sure to use a Python version [compatible with ARAX](https://github.com/RTXteam/RTX/wiki/Dev-info#setting-up-for-local-dev-work-on-arax) and run `pip install -r requirements.txt` as needed.   
    * _For ARAX team: If you're using `ngdbuild.rtx.ai`, a virtual env already exists that you can activate like so: `source ~/ngd_venv/bin/activate`_
5. **Turn on KG2pre neo4j**: If the KG2pre neo4j instance hosting the KG2 version you're building this NGD database from is not already running, turn it on and start neo4j. (e.g., do `ssh ubuntu@kg2endpointX.rtx.ai`, and then `sudo service neo4j start`)

### Then do the build:

You have two options: a full build or a partial build.

_Note to ARAX team: We typically do partial builds; we do full builds only once or twice a year to ensure we're using recent PubMed data._

#### Full build

If you want to use the latest PubMed files for this NGD build **or** the machine you're using has never previously 
run an NGD build, do a full build:
```
cd RTX/code/ARAX/ARAXQuery/Overlay/ngd
python3 build_ngd_database.py --full
```
This will automatically download and use the latest PubMed XML files, including both the annual 'baseline' files and 
the 'update' files. Note that full builds take 8+ hours and require **more than 64G of RAM**.

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
