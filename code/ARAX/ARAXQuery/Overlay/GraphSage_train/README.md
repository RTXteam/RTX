# How to run GraphSage to train drug re-purposing ML model?

To run GraphSage, I recommend to use conda to set up the environment first. Since GraphSage was written by python v2.7, we need to set up two python environment separately for python v2.7 and python v3.7. I prepared two conda environment files (eg. environment_p2.7.yml and environment_p3.7.yml) that I used to set up the conda environment for running GraphSage. You can use the following commands to set up the conda environment

### NOTE: please install conda first before running the following commands
#### set up environment for python v2.7 
conda create -n test -c conda-forge -f environment_p2.7.yml
#### set up environment for python v3.7
conda create -n test -c conda-forge -f environment_p3.7.yml

After setting up the conda environment, please follow the bash scripts (eg. 1_graphsage_make_data.sh, 2_run_graphsage_unsupervised_train.sh, 3_transform_to_emb_format.sh) to prepare the input files and run GraphSage. The prefix of these scripts is the order of running these scripts. So first run 1_graphsage_make_data.sh to prepare the input files (Note: please use conda environment with python v3.7 to run this script) and then run 2_run_graphsage_unsupervised_train.sh (Note: please use conda environment with python v2.7 to run this script). Once GraphSage is done, please use 3_transform_to_emb_format.sh to transform GraphSage output format to emb format. 
