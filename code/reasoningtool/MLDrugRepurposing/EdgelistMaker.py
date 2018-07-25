"""
This script maps integers 0...n to to all nodes in the csv containging the edges for a graph.
It then saves all of these mappings and a converted graph into csvs
"""


import pandas as pd
import numpy as np

#read the graph downloaded from the neo4j instance
df = pd.read_csv('data/graph.csv')

# loads source curies into a list and removes duplicate curie ids 
sources = df['source'].unique()
targets = df['target'].unique()

# Iinitialize counter for node id
c = 0

# Initialize dict that maps curie ids to integer ids
map = {}

# Runs through list of sources and assigns ids
for x in sources:
    map[x] = c
    c += 1

# Runs through list of targets and assigns ids if not already assigned
for x in targets:
    if x not in map.keys():
        map[x] = c
        c += 1

d = 0
# Runs through rows in daraframe and converts curies to integer ids
for row in range(len(df)):
    df.at[row,'source'] = map[df['source'][row]]
    df.at[row,'target'] = map[df['target'][row]]
    d += 1
    # This prints percentage progress every 10%. Uncomment if you want this.
    #if d % int(len(df)/10 + 1) == 0:
    #    print(d/len(df))

# Saves the curie -> intiger id map and converted graph
map_df = pd.DataFrame(list(map.items()), columns = ['curie','id'])
df.to_csv('data/rel.edgelist',sep = ' ', header=False,index=False)
map_df.to_csv('data/map.csv',index=False)

