import pandas as pd
import sys 
import os

pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code']))
from RTXConfiguration import RTXConfiguration
RTXConfig = RTXConfiguration()
RTXConfig.live = "Production"

pred_path = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'KnowledgeSources', 'Prediction'])
rel_max_path = os.path.sep.join([pred_path,self.RTXConfig.rel_max_path.split('/')[-1]])
map_txt_path = os.path.sep.join([pred_path,self.RTXConfig.map_txt_path.split('/')[-1]])


graph = pd.read_csv(rel_max_path, sep=' ', skiprows=1, header=None, index_col=None)
graph = graph.sort_values(0).reset_index(drop=True)
map_df = pd.read_csv(map_txt_path, sep='\t', index_col=None)
graph.loc[:, 0] = map_df.loc[:, 'curie']
graph = graph.set_index([0])

drug_id = pd.read_csv('drug_ids.txt', sep='\t', index_col=None)
disease_id = pd.read_csv('disease_ids.txt', sep='\t', index_col=None)
all_drug_disease_ids = set()
all_drug_disease_ids.update(set(drug_id['id']))
all_drug_disease_ids.update(set(disease_id['id']))
graph = graph.loc[list(all_drug_disease_ids),:].reset_index()
graph.to_csv('disease_drug_only.txt', sep='\t', index=None, header=False)