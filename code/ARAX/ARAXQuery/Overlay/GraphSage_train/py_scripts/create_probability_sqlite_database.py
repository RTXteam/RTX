import os
import pandas as pd
import sqlite3
import itertools
import sys
import time
import numpy as np
pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'ARAXQuery']))
from Overlay.predictor.predictor import predictor
filepath = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'ARAXQuery', 'Overlay', 'predictor', 'retrain_data'])

## check if there is LogModel.pkl
pkl_file = f"{filepath}/LogModel.pkl"
if os.path.exists(pkl_file):
    pass
else:
    os.system("scp rtxconfig@arax.rtx.ai:/home/ubuntu/drug_repurposing_model_retrain/LogModel.pkl " + pkl_file)

## check if there is rel_max.emb.gz
emb_file = f"{filepath}/rel_max.emb.gz"
if os.path.exists(emb_file):
    pass
else:
    os.system("scp rtxconfig@arax.rtx.ai:/home/ubuntu/drug_repurposing_model_retrain/rel_max.emb.gz " + emb_file)

## check if there is NodeNamesDescriptions_KG2.tsv.
pre_path = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'data', 'KGmetadata'])
fpath = pre_path + "/NodeNamesDescriptions_KG2.tsv"
try:
    kpdata = pd.read_csv(fpath, sep="\t", header=None, names=['curie', 'name', 'type'])
except FileNotFoundError:
    raise FileNotFoundError("Please go to $RTX/data/KGmetadata and run 'python3 dumpdata.py' first")

# check if there is map.txt
map_file = f"{filepath}/map.txt"
if os.path.exists(map_file):
    pass
else:
    os.system("scp rtxconfig@arax.rtx.ai:/home/ubuntu/drug_repurposing_model_retrain/map.txt " + map_file)

# with open(map_file, 'r') as infile:
#     map_file_content = infile.readlines()
#     map_file_content.pop(0) ## remove title
#     known_curies = set(line.strip().split('\t')[0] for line in map_file_content)

graph = pd.read_csv(emb_file, sep=' ', skiprows=1, header=None, index_col=None)
graph = graph.sort_values(0).reset_index(drop=True)
map_df = pd.read_csv(map_file, sep='\t',index_col=None)
graph.loc[:,0] = map_df.loc[:,'curie']
graph = graph.set_index([0])

known_curies = set(map_df['curie'])
all_set = set(kpdata.loc[(kpdata['type']=="drug") | (kpdata['type']=="chemical_substance") | (kpdata['type']=="disease") | (kpdata['type']=="phenotypic_feature"), "curie"])
intersect = all_set.intersection(known_curies)
graph = graph.loc[intersect, :]

## get drug/chemical_substance curie ids from KG2
drug_curie_list = set(kpdata.loc[(kpdata['type']=="drug") | (kpdata['type']=="chemical_substance"), "curie"])
drug_curie_list = list(known_curies.intersection(drug_curie_list)) ## filter out the isolated nodes

## get disease/phenotypic_feature curie ids from KG2
disease_curie_list = set(kpdata.loc[(kpdata['type']=="disease") | (kpdata['type']=="phenotypic_feature"), "curie"])
disease_curie_list = list(known_curies.intersection(disease_curie_list)) ## filter out the isolated nodes

## build up the prediction model
pred = predictor(model_file=pkl_file)

# connect to database and create SQL table
conn = sqlite3.connect('DISEASE_DRUG_PROBABILITY.sqlite')
print("INFO: Creating database DISEASE_DRUG_PROBABILITY", flush=True)
conn.execute(f"DROP TABLE IF EXISTs PROBABILITY")

insert_command1 = f"CREATE TABLE PROBABILITY(disease VARCHAR(255), drug VARCHAR(255), probability INT)"
conn.execute(insert_command1)

start_time = time.time()

print("start")

print(f"INFO: Populating table PROBABILITY",flush=True)
print(f"Total diseases: {len(disease_curie_list)}")
for curie in disease_curie_list:

    print(curie,flush=True)
    test1 = graph.loc[[curie for _ in range(len(drug_curie_list))], :].to_numpy()
    test2 = graph.loc[drug_curie_list, :].to_numpy()
    X = np.multiply(test1, test2)
    all_prob = list(pred.prob(X)[:, 1])
    bool_list = [True if prob >= 0.8 else False for prob in all_prob]
    all_prob_threshold = list(itertools.compress(all_prob, bool_list))
    drug_curie_list_selected = list(itertools.compress(drug_curie_list, bool_list))
    if len(all_prob_threshold)>1:
        rows = list(zip(itertools.cycle([curie]), drug_curie_list_selected, all_prob_threshold))
    elif len(all_prob_threshold)==1:
        rows = list(zip([curie], drug_curie_list_selected, all_prob_threshold))
    else:
        continue
    conn.executemany("INSERT INTO PROBABILITY VALUES (?, ?, ?)", rows)
    conn.commit()

print(f"INFO: Creating INDEXes on PROBABILITY", flush=True)
conn.execute(f"CREATE INDEX idx_PROBABILITY_disease ON PROBABILITY(disease)")
conn.execute(f"CREATE INDEX idx_PROBABILITY_drug ON PROBABILITY(drug)")

print("Finished applying action")
print("running time: %s seconds " % (time.time() - start_time))