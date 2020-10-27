# How to run GraphSage to train drug re-purposing ML model?

To run GraphSage, I recommend to use conda to set up the environment first. Since GraphSage was written by python v2.7, we need to set up two python environment separately for python v2.7 and python v3.7. I prepared two conda environment files (eg. environment_p2.7.yml and environment_p3.7.yml) that I used to set up the conda environment for running GraphSage. You can use the following commands to set up the conda environment

### NOTE: please install conda first before running the following commands
#### set up environment for python v2.7 
conda create -n test -c conda-forge -f environment_p2.7.yml
#### set up environment for python v3.7
conda create -n test -c conda-forge -f environment_p3.7.yml

After setting up the conda environment, please follow the bash scripts (eg. 0_generate_graph_data_and_model_training_data.sh, 1_graphsage_make_data.sh, 2_run_graphsage_unsupervised_train.sh, 3_transform_to_emb_format.sh, 4_build_emb_sqlite_database.sh) to train DTD model. The prefix of these scripts is the order of running these scripts. 

0_generate_graph_data_and_model_training_data.sh: This script is used to generate to pull the graph data from Neo4j server and automatically generate the training data.

1_graphsage_make_data.sh: This script is used to prepare the input files. (Note: please use conda environment with python v3.7 to run this script)

2_run_graphsage_unsupervised_train.sh: This script is used to run GraphSage to geneate the embedding vectors. (Note: please use conda environment with python v2.7 to run this script)

3_transform_to_emb_format.sh: This script is used to transform GraphSage output format to emb format. 

4_build_emb_sqlite_database.sh: This script is used to build MySQL database for emb file.

