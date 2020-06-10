## generate G.json, id_map.json, class_map.json for running graphsage
## Note for the input file (eg. graph_edges.txt and graph_nodes_label_remove_name.txt), please refer to
time python ./py_scripts/graphsage_data_generation.py --graph graph_edges.txt --node_class graph_nodes_label_remove_name.txt --feature_dim 256 --validation_percent 0.2 --output ./graphsage_input
## generate walks.txt for running graphsage
time python ./py_scripts/generate_random_walk.py --Gjson ./graphsage_input/data-G.json --walk_length 200 --number_of_walks 10 --batch_size 250000 --process 100 --output ./graphsage_input
