## generate G.json, id_map.json, class_map.json for running graphsage
## Note to know how to generate the input file (eg. graph_edges.txt and graph_nodes_label_remove_name.txt), please refer to ./py_scripts/pull_KG2.py
time python ./py_scripts/graphsage_data_generation.py --graph graph_edges.txt --node_class graph_nodes_label_remove_name.txt --feature_dim 50 --validation_percent 0.3 --output ./graphsage_input
## generate walks.txt for running graphsage (Note: based on the run on the machine with 1TB ram and 256 threads, this step with the setting below needs to run 3-4 days. Using too many threads might run out of memory)
time python ./py_scripts/generate_random_walk.py --Gjson ./graphsage_input/data-G.json --walk_length 200 --number_of_walks 10 --batch_size 100000 --process 60 --output ./graphsage_input
