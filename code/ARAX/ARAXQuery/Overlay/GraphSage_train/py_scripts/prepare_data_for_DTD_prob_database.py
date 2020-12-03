import pandas as pd

graph = pd.read_csv("rel_max.emb.gz", sep=' ', skiprows=1, header=None, index_col=None)
graph = graph.sort_values(0).reset_index(drop=True)
map_df = pd.read_csv('map.txt', sep='\t', index_col=None)
graph.loc[:, 0] = map_df.loc[:, 'curie']
graph = graph.set_index([0])

drug_id = pd.read_csv('drug_ids.txt', sep='\t', index_col=None)
disease_id = pd.read_csv('disease_ids.txt', sep='\t', index_col=None)
all_drug_disease_ids = set()
all_drug_disease_ids.update(set(drug_id['id']))
all_drug_disease_ids.update(set(disease_id['id']))
graph = graph.loc[list(all_drug_disease_ids),:].reset_index()
graph.to_csv('disease_drug_only.txt', sep='\t', index=None, header=False)