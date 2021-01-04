#PBS -W umask=0007
#PBS -W group_list=sam77_collab
#PBS -l walltime=30:00:00
#PBS -l nodes=1:ppn=20
#PBS -j oe
#PBS -A sam77_b_g_hc_default
#PBS -l mem=500gb

#!/bin/bash

###################################
##### Variable Initialization #####
###################################

# The path of the python that you want to use
py_name=~/anaconda3/envs/RTX_env/bin/python

# This is that name of the file you wish to save the model as
model_file=~/work/RTX/code/reasoningtool/MLDrugRepurposing/Test_graphsage/kg2_3_4/RF_train_results/l100_r10_512dim_70training_2layer_512batch_96neighbor_kg2canonical_2_3_4_tp8_tn2/a00_3_7_${type}Model_${depth}_${trees}.pkl

# This is the minimum number on entries in SemMedDB needed for a realationship to be considered a ground truth. (Higher numbers cut out noise but at the cost of a smaller training set)
tncutoff="2"
tpcutoff="8"

# This is the maximum depth each tree and the number of trees in the random forest model
trees="2000"
depth="29"

# This indicates the type of model you wish to use (RF - randomforest and LR - logistic regression)
type="RF"

# This indicates using which method for the embedding of the pair of nodes (concatenate or hadamard)
method='hadamard'

PWD=~/work/RTX/code/reasoningtool/MLDrugRepurposing/Test_graphsage/kg2_3_4
PPWD=~/work/RTX/code/reasoningtool/MLDrugRepurposing/Test_graphsage/kg2_3_4/test_scripts

echo "Building model..."
eval "${py_name} ${PPWD}/LogReg.py --tp ${PWD}/training_data/semmed_tp.txt ${PWD}/training_data/mychem_tp.txt ${PWD}/training_data/ndf_tp.txt ${PWD}/training_data/mychem_tp_umls.txt\\
                          --tn ${PWD}/training_data/semmed_tn.txt ${PWD}/training_data/mychem_tn.txt ${PWD}/training_data/ndf_tn.txt ${PWD}/training_data/mychem_tn_umls.txt\\
                          --emb ${PWD}/graphsage_out/graphsage_mean_big_0.001000_l100_r10_512dim_70training_2layer_512batch_96neighbor_kg2canonical_2_3_4.emb \\
						  --map ${PWD}/graphsage_input/id_map.txt  \\
						  --drugs_path ${PWD}/kg2canonicalized_data/drugs_in_graph.txt \\
						  --diseases_path ${PWD}/kg2canonicalized_data/diseases_in_graph.txt \\
                          --tpcutoff ${tpcutoff} \\
                          --tncutoff ${tncutoff} \\
                          --roc \\
                          --rand \\
                          --save ${model_file} \\
                          --depth ${depth} \\
                          --trees ${trees} \\
                          --type ${type} \\
						  --pair_emb ${method} \\
						  --output ${PWD}/RF_train_results/l100_r10_512dim_70training_2layer_512batch_96neighbor_kg2canonical_2_3_4_tp8_tn2"
