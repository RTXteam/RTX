# NOTE: dependencies have been removed

On May 15, 2025, one of the modules on which some code in this directory
depends, `RTX/code/reasoningtool/SemMedDB`, was deleted from the `RTXteam/RTX`
project area (see #2454). But if you need this code, you can obtain it from any
earlier RTXteam/RTX [release](https://github.com/RTXteam/RTX/releases).

On Oct. 9, 2025, a module,
`RTX/code/reasoningtool/kg-construction/SynonymMapper.py`, on which the
`MyChemGT.py` module in this directory depends, was deleted from the
`RTXteam/RTX` project area (see #2582). But if you need this code, you can
obtain it from any earlier RTXteam/RTX [release](https://github.com/RTXteam/RTX/releases).

# Make sure python is set up correctly

Make sure you have python3 installed and that the contents of [Requirements.txt](https://github.com/RTXteam/RTX/blob/master/requirements.txt) are installed

# Set up a local version of neo4j and import a dump of our Knowlege Graph

Knowledge graph (KG) dumps can be found [here.](http://rtxkgdump.saramsey.org/)

NOTE: Last test was run on the 07/27/18 KG dump.

# Make sure you use the correct data

After importing the KG use a cypher query (such as `match (n) where n.id =~ "(?i)CHEMBL.*" return n.id limit 5`) to look at the format of the chembl curie ids. If you get result like `CHEMBL.COMPOUND:CHEMBL153` then you can don't have to do anything. If, however, you get a result like `ChEMBL:153` then you are using an older version of the knowledge graph and need to rename the files: source_map_old.csv, target_map_old.csv, ndf_tp_old.csv, and ndf_tn_old.csv. Just remove "\_old" from the end of the file names (replacing the other files of the same name) and you will be good to go.

# Download and setup node2vec

Node2vec is a program developed by researchers at stanford to vectorize nodes in a graph. It can be found [here](https://github.com/snap-stanford/snap/tree/master/examples/node2vec). And information about it is listed [here](https://snap.stanford.edu/node2vec/).

# Download the SemMedDB MySQL dump

Download can be found here: https://skr3.nlm.nih.gov/SemMedDB/download/download.html

Download the PREDICATION table from the above link and place it into the data directory.

NOTE: Don't unzip

# Edit the MLDR.sh file variables

There are several variables at the top of the MLDR.sh bash script. They are seperated into groups and have decriptions of what they do written above them. You will need to edit some of these (like neo4j log in credentials and url:port) to fit your local system before running MLDR.sh.

### Descriptions of variables

* `py_name` - how you call python 3 using the terminal in the enviroment you will be running MLDR.sh. (most likely python or python3)

* `semmed` - The path to the SemMedDB PREDICATION table mysql dump.

* `neo4j_user` - The username used in the neo4j instance hosting the knowledge graph. (This defaults to neo4j)

* `neo4j_pass` - The password for the neo4j instance hosting the knowledge graph. (This defaults to neo4j)

* `neo4j_url` - The bolt url and port for access to the neo4j instance. (This defaults to bolt://localhost:7687)

* `PVAR`, `QVAR`, `EVAR`, `DVAR`, `LVAR`, and `RVAR` are the parameters p, q, e, d, l, & r for node2vec and decriptions for these can be found on [github](https://github.com/snap-stanford/snap/tree/master/examples/node2vec). Further reading about how node2vec works and more in depth descriptions of what these parameters do can be found [here](https://arxiv.org/abs/1607.00653).

* `cutoff` - The number of times a relationship need to be encountered in SemMedDB for it to be included in the training data. This helps cut down on some of the noise in SemMedDB.

* `roc` - True of False depending on if you want a roc curve generated for the model.

* `data_file` - Thepath to the data file you want to predict on. Decription on how to set this up in the next section.

# Make predictions using predictor.py

If you want to make predictions on a data set format it in a csv with the headers source and target using curie ids (CHEMBL for drugs and DOID/OMIM/HP) as identifiers formatted as such:

source |	target
----- | ----
ChEMBL:1622 |	DOID:399
ChEMBL:730 |	OMIM:613658
ChEMBL:1484 |	OMIM:601367
ChEMBL:1237022 |	DOID:0060407
ChEMBL:504 |	DOID:0050275
ChEMBL:714 |	DOID:9675
ChEMBL:504 |	DOID:0050638
ChEMBL:1909300 | HP:0000421

Then if you wish to make a prediction at the same time simply uncomment the predictor.py commands at the end of MLDR.sh and it do it all in one run. Otherwise, you can simply follow the skeleton of the command and just run it in the termainal after MLDR.sh has generated the model. 

