## generate graph data (i.e. graph_edges.txt, graph_nodes_label_remove_name.txt) for step1 (1_graphsage_make_data.sh)
time python ~/work/RTX/code/ARAX/ARAXQuery/Overlay/GraphSage_train/py_scripts/pull_canonicalized_KG2C.py --OutFolder ~/work/RTX/code/reasoningtool/MLDrugRepurposing/Test_graphsage/kg2_6_3/kg2canonicalized_data
## generate training data for model
time python ~/work/RTX/code/ARAX/ARAXQuery/Overlay/GraphSage_train/py_scripts/generate_training_data.py
cp -r ~/work/RTX/code/reasoningtool/MLDrugRepurposing/Test_graphsage/kg2_6_3/raw_training_data ~/work/RTX/code/reasoningtool/MLDrugRepurposing/Test_graphsage/kg2_6_3/training_data
time python ~/work/RTX/code/ARAX/ARAXQuery/Overlay/GraphSage_train/py_scripts/BuildMapID.py --path ~/work/RTX/code/reasoningtool/MLDrugRepurposing/Test_graphsage/kg2_6_3/training_data