import os
import pandas as pd
import sqlite3
import itertools
import sys
import time
import numpy as np
import argparse
import warnings
warnings.filterwarnings('ignore')

sys.path.append('/home/cqm5886/work/RTX/code/ARAX/ARAXQuery/Overlay/predictor')
from predictor import predictor

parser = argparse.ArgumentParser()
parser.add_argument("-e", "--embfile", type=str, help="The path of .emb file")
parser.add_argument("-dgf", "--drugfile", type=str, help="The path of drug id file")
parser.add_argument("-dsf", "--diseasefile", type=str, help="The path of one disease id file")
parser.add_argument("-mf", "--modelfile", type=str, help="The path of model file")
parser.add_argument("-o", "--outpath", type=str, help="The output path")

args = parser.parse_args()

graph = pd.read_csv(args.embfile, sep='\t', header=None)
graph = graph.set_index([0])
drug_curie_list = list(pd.read_csv(args.drugfile, sep='\t', header=0)['id'])
disease_curie_list = list(pd.read_csv(args.diseasefile, sep='\t', header=None)[0])

## build up the prediction model
pred = predictor(model_file=args.modelfile)

## pre-create an array of all drugs which will be used in create_array function.
drug_array = graph.loc[drug_curie_list, :].to_numpy()

def create_array(curie):

    #print(curie, flush=True)
    disease_array = graph.loc[[curie for _ in range(len(drug_curie_list))], :].to_numpy()
    return np.multiply(disease_array, drug_array)


array_list = [elem for elem in map(create_array, disease_curie_list)]
X = np.concatenate(array_list)
all_prob = list(pred.prob(X)[:, 1])
disease_col = list(itertools.chain.from_iterable(itertools.repeat(x, len(drug_curie_list)) for x in disease_curie_list))
drug_col = drug_curie_list * len(disease_curie_list)
prob_col = [prob for prob in all_prob if prob >= 0.8]
bool_list = [True if prob >= 0.8 else False for prob in all_prob]
disease_col = list(itertools.compress(disease_col, bool_list))
drug_col = list(itertools.compress(drug_col, bool_list))
rows = list(zip(disease_col, drug_col, prob_col))
if len(rows) != 0:
    disease_curie = disease_curie_list[0]
    pd.DataFrame(rows,columns=['disease','drug','prob']).to_csv(args.outpath+"/"+disease_curie+".txt",sep='\t',index=False,header=False)
