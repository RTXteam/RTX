#!/bin/bash

###################################
##### Variable Initialization #####
###################################

# The path of the python that you want to use
py_name=~/anaconda3/envs/RTX_env/bin/python

# This is that name of the file you wish to save the model as
model_file=~/work/RTX/code/reasoningtool/MLDrugRepurposing/Test_graphsage/RF_train_results/l100_r8_512dim_70training_2layer_512batch_96neighbor/a00_3_7_${type}Model_${depth}_${trees}.pkl

# This is the minimum number on entries in SemMedDB needed for a realationship to be considered a ground truth. (Higher numbers cut out noise but at the cost of a smaller training set)
cutoff="2"

# This is the maximum depth each tree and the number of trees in the random forest model
trees="2000"
depth="29"

# This indicates the type of model you wish to use (RF - randomforest and LR - logistic regression)
type="RF"

# This indicates using which method for the embedding of the pair of nodes (concatenate or hadamard)
method='hadamard'

PWD=~/work/RTX/code/reasoningtool/MLDrugRepurposing/Test_graphsage
PPWD=~/work/RTX/code/ARAX/ARAXQuery/Overlay/GraphSage_train/py_scripts

echo "Building model..."
eval "${py_name} ${PPWD}/LogReg_edited.py --tp ${PWD}/test_data/semmed_tp.txt ${PWD}/test_data/mychem_tp.txt ${PWD}/test_data/mychem_tp_umls.txt ${PWD}/test_data/ndf_tp.txt \\
                          --tn ${PWD}/test_data/semmed_tn.txt ${PWD}/test_data/mychem_tn.txt ${PWD}/test_data/mychem_tn_umls.txt ${PWD}/test_data/ndf_tn.txt \\
                          --emb ~/work/RTX/code/reasoningtool/MLDrugRepurposing/Test_graphsage/graphsage_out/graph_l100_r8_512dim_70training_2layer_512batch_96neighbor.emb \\
						  --map ~/work/RTX/code/reasoningtool/MLDrugRepurposing/Test_graphsage/graphsage_input/id_map.txt  \\
						  --drugs_path ${PWD}/test_data/drugs_in_graph_new.txt \\
						  --diseases_path ${PWD}/test_data/diseases_in_graph_new.txt \\
                          --cutoff ${cutoff} \\
                          --roc \\
                          --rand \\
                          --save ${model_file} \\
                          --depth ${depth} \\
                          --trees ${trees} \\
                          --type ${type} \\
						  --pair_emb ${method} \\
						  --output ~/work/RTX/code/reasoningtool/MLDrugRepurposing/Test_graphsage/RF_train_results/l100_r8_512dim_70training_2layer_512batch_96neighbor"
