## generate graph data (i.e. graph_edges.txt, graph_nodes_label_remove_name.txt) for step1 (1_graphsage_make_data.sh)
time python ./py_scripts/pull_canonicalized_KG2_3_4C.py
## generate training data for model
time python ./py_scripts/generate_training_data.py
time python ./py_scripts/BuildMapID.py --path ~/work/RTX/code/reasoningtool/MLDrugRepurposing/Test_graphsage/kg2_3_4/raw_training_data