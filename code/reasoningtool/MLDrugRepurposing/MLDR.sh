#!/bin/bash

###################################
##### Variable Initialization #####
###################################

# This is the command you use to run python scripts. Most likely "python" or "python3"
py_name="python"

# This is the path to the gzipped semmeddb predication sql dump. You do not need to unzip.
semmed="data/semmedVER31_R_PREDICATION_to12312017.sql.gz"

# This is the username and password for the neo4j instance you are using to host the graph. By default the username and password are both "neo4j"
neo4j_user="neo4j"
neo4j_pass="precisionmedicine"
neo4j_url="bolt://rtxdev.saramsey.org:7687"

# This is the path to node2vec. download and install from here: https://github.com/snap-stanford/snap/tree/master/examples/node2vec
# Make sure that you run the makefile before tryig to use
node2vec_path="/home/womackf/Dropbox/pyUMLS/snap/snap-master/examples/node2vec/node2vec"

# There are the parameters used in the EMB file creation. Descriptions are listed here: https://github.com/snap-stanford/snap/tree/master/examples/node2vec
PVAR="1"
QVAR="5"
EVAR="3"
DVAR="128"
LVAR="100"
RVAR="5"

# This is the minimum number on entries in SemMedDB needed for a realationship to be considered a ground truth. (Higher numbers cut out noise but at the cost of a smaller training set)
cutoff="2"

# This indicates if you want a roc curve plotted for the end model (True for yes and False for no)
roc="True"

# The name of the csv you wish to import to predict on
data_file="data.csv"

######## WILL BE REMOVED ##############
# This is for testing right now
#path2="/home/womackf/Dropbox/pyUMLS/snap/snap-master/examples/node2vec/LogReg"
path2="data"

################
##### Code #####
################

# This section converts the gzipped mysql dump from SemMedDB to a csv
#echo "Converting SemMedDB to csv..."
#eval "zcat ${semmed} | ${py_name} mysqldump_to_csv.py"

# This section extracts, counts, and formats positive training data from SemMEdDB
#echo "Extracting positives from SemMedDB..."
#echo "pmid,relationship,subject_cui,subject_name,object_cui,object_name" > data/to_split.csv
#grep ',TREATS,' PREDICATION.csv | csvcut -c=3,4,5,6,9,10 >> data/to_split.csv
#eval "${py_name} SplitRel.py --f data/to_split.csv --s data/split.csv"
#rm data/to_split.csv
#echo "count,source,target" > data/semmed_tp.csv
#tail -n+2 data/split.csv | csvcut -c=3,5 | sort | uniq --count | sed 's/^ *//g' | sed 's/ /,/g' >> data/semmed_tp.csv
#rm data/split.csv

# This section extracts, counts, and formats negative training data from SemMEdDB
#echo "Extracting negatives from SemMedDB..."
#echo "pmid,relationship,subject_cui,subject_name,object_cui,object_name" > data/to_split.csv
#grep ',NEG_TREATS,' PREDICATION.csv | csvcut -c=3,4,5,6,9,10 >> data/to_split.csv
#eval "${py_name} SplitRel.py --f data/to_split.csv --s data/split.csv"
#rm data/to_split.csv
#echo "count,source,target" > data/semmed_tn.csv
#tail -n+2 data/split.csv | csvcut -c=3,5 | sort | uniq --count | sed 's/^ *//g' | sed 's/ /,/g' >> data/semmed_tn.csv
#rm data/split.csv

#mv PREDICATION.csv data/

# This section downloads the graph and nodes needed for cui -> curie mapping
#echo "Downloading graph..."
#eval "${py_name} PullGraph.py --user ${neo4j_user} --password ${neo4j_pass} --url ${neo4j_url}"

# This section Creates a cui -> curie map file.
# NOTE: This will only work if a couple of services are runningon our aws instances
# if you do not know if those are running simply do not uncomment this line and download the pre-
# generated file on out github.
#eval "${py_name} BuildCuiMap.py --source data/drugs.csv --target data/diseases.csv"

# This section formats the graph for ingestion by node2vec and passes it to node2vec to create vectorizations of our nodes
#echo "Converting graph to edgelist..."
#eval "${py_name} EdgelistMaker.py"
#eval "${node2vec_path} -i:${PWD}/data/rel.edgelist -o:${PWD}/data/graph.emb -q:${QVAR} -p:${PVAR} -e:${EVAR} -d:${DVAR} -l:${LVAR} -r:${RVAR} -v -dr"


# This section downloads the mychem training data
#echo "Downloading MyChem data..."
#eval "${py_name} MyChemGT.py"

# This section converts the training data csvs from cuis to curie ids
#echo "Converting cuis to curie ids..."
#eval "${py_name} ConvertCsv.py --tp data/semmed_tp.csv --tn data/semmed_tn.csv"
#eval "${py_name} ConvertCsv.py --tp data/mychem_tp_umls.csv --tn data/mychem_tn_umls.csv -t True"

# This section builds a model using logistic regression and save it to the file LogReg.pkl for prediction using Pred.py
echo "Building model..."
eval "${py_name} LogReg.py --tp ${path2}/semmed_tp.csv ${path2}/mychem_tp.csv ${path2}/mychem_tp_umls.csv ${path2}/ndf_tp.csv \\
                           --tn ${path2}/semmed_tn.csv ${path2}/mychem_tn.csv ${path2}/mychem_tn_umls.csv ${path2}/ndf_tn.csv \\
                           --emb /home/bweeder/Data/rtx_data/newer_data/q_5_p_1_e_5_e_5_d_256_l_300_r_15_undirected.emb \\
                           --map ${path2}/map.csv \\
                           -c ${cutoff} \\
                           --roc ${roc}"

# This section makes predictions and then saves them to a csv
#echo "Making predictions..."
#eval "${py_name} predictor.py --emb data/graph.emb \\
#                              --model data/LogReg.pkl \\
#                              --map data/map.csv \\
#                              --data data/${data_file} \\
#                              --save prediction.csv"

