## This bash script is to run graphsage

## set graphsage folder
graphsage_folder=~/work/Graphsage/GraphSAGE

## set your working path
work_path=~/work/RTX/code/reasoningtool/MLDrugRepurposing/Test_graphsage

## set python path (Please use python 2.7 to run graphsage as graphsage was written by python2.7)
ppath=~/anaconda3/envs/graphsage_p2.7env/bin/python

## set model name
model='graphsage_mean'
## model option:
#graphsage_mean -- GraphSage with mean-based aggregator
#graphsage_seq -- GraphSage with LSTM-based aggregator
#graphsage_maxpool -- GraphSage with max-pooling aggregator
#graphsage_meanpool -- GraphSage with mean-pooling aggregator
#gcn -- GraphSage with GCN-based aggregator
#n2v -- an implementation of DeepWalk

## set data input folder and training data prefix
train_prefix=~/work/RTX/code/reasoningtool/MLDrugRepurposing/Test_graphsage/graphsage_input/data #note: here 'data' is the training data prefix

## other parameters
model_size='big' #Can be big or small
learning_rate=0.001 #test 0.01 and 0.001, 'initial learning rate'
epochs=10 #test 5 and 10, 'number of epochs to train'
samples_1=96 #suggest 15-25, based on the paper, bigger is better
samples_2=96 #script only allows to set K=2, the same as samples_1
dim_1=256 #Size of output dim (final is 2x this)
dim_2=256
max_total_steps=500 #Maximum total number of iterations
validate_iter=5000 #how often to run a validation minibatch
identity_dim=50 #Set to positive value to use identity embedding features of that dimension. Default 0
batch_size=512 #minibatch size
max_degree=96 #maximum node degree

## create a soft link to graphsage modules
if ! [ -d ${work_path}/graphsage ]; then
	ln -s ${graphsage_folder}/graphsage ${work_path}/graphsage
fi

## run graphsage unsupervised model
$ppath -m graphsage.unsupervised_train --train_prefix ${train_prefix} --model_size ${model_size} --learning_rate ${learning_rate} --epochs ${epochs} --samples_1 ${samples_1} --samples_2 ${samples_2} --dim_1 ${dim_1} --dim_2 ${dim_2} --model ${model} --max_total_steps ${max_total_steps} --validate_iter ${validate_iter} --identity_dim ${identity_dim} --batch_size ${batch_size} --max_degree ${max_degree}

