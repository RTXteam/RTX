## generate G.json, id_map.json, class_map.json for running graphsage
## Note to know how to generate the input file (eg. graph_edges.txt and graph_nodes_label_remove_name.txt), please refer to step 0 (0_generate_graph_data_and_model_training_data.sh)
time python ~/work/RTX/code/ARAX/ARAXQuery/Overlay/GraphSage_train/py_scripts/graphsage_data_generation.py --graph graph_edges.txt --node_class graph_nodes_label_remove_name.txt --feature_dim 1 --validation_percent 0.3 --output ./graphsage_input
## generate walks.txt for running graphsage (Note: based on the run on the machine with 1TB ram and 256 threads, this step with the setting below needs to run 3-4 days. Using too many threads might run out of memory)
time python ~/work/RTX/code/ARAX/ARAXQuery/Overlay/GraphSage_train/py_scripts/generate_random_walk.py --Gjson ./graphsage_input/data-G.json --walk_length 100 --number_of_walks 10 --batch_size 200000 --process 80 --output ./graphsage_input
