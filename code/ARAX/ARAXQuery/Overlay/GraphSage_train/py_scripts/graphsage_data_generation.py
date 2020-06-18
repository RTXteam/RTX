## This script is used to generate required input files (eg. G.json, id_map.json, class_map.json, please see https://github.com/williamleif/GraphSAGE
# for more details) as well as the mapping files for running Graphsage

from __future__ import print_function

import json
import numpy as np
import pandas as pd
import random
import os
import sys
import argparse
import multiprocessing
from itertools import chain


parser = argparse.ArgumentParser()
parser.add_argument("--graph", type=str, help="The filename or path of the graph file (.txt)")
parser.add_argument("--node_class", type=str, help="The filename or path of the node class label file (.txt)", default=None)
parser.add_argument("-s", "--seed", type=int, help="Random seed (default: 100)", default=100)
parser.add_argument("-fd", "--feature_dim", type=int, help="The node feature dimension", default=256)
parser.add_argument("-p", "--process", type=int, help="Number of processes to be used", default=-1)
parser.add_argument("-vp", "--validation_percent", type=float, help="The percentage of validation data (default: 0.2)", default=0.2)
parser.add_argument("-o", "--output", type=str, help="The path of output folder", default="/graphsage_input")

args = parser.parse_args()

## setting functions compatible with parallel running
def initialize_node(this):

    node, has_node_class = this
    if not has_node_class:
        return [{'test': False, 'id': int(node), 'feature': np.zeros(args.feature_dim).tolist(), 'label': [1], 'val': (node in valid)}]
    else:
        return [{'test': False, 'id': int(node), 'feature': np.zeros(args.feature_dim).tolist(), 'label': nodeclass_data_index[nodes[node]][1], 'val': (node in valid)}]

def initialize_edge(node):

    return [{'test_removed': False, 'train_removed': False, 'source': int(graph_data.loc[node,'id1']), 'target': int(graph_data.loc[node,'id2'])}]

if __name__ == "__main__":
    # change to the current path
    current_path = os.path.split(os.path.realpath(__file__))[0]
    os.chdir(current_path)

    # check the input arguments
    if args.graph == None or not os.path.exists(os.path.realpath(args.graph)):
        sys.exit('Error Occurred! Please provide the correct path of your graph file.')
    else:
        graphpath = args.graph
    if args.node_class == None or not os.path.exists(os.path.realpath(args.graph)):
        print('No class label file was detected. All nodes will be set to the same label.')
        node_class = None
    else:
        node_class = args.node_class

    # setting the path of output directory
    if args.output == "/graphsage_input":
        outpath = current_path + '/graphsage_input'
    else:
        outpath = os.path.realpath(args.output)

    #create output directory
    try:
        os.mkdir(outpath)
    except:
        error_type, error, _ = sys.exc_info()
        print(f'Something wrong with creating output directory! Error Message is as follow:')
        print(f'{error_type} {error}')

    #read the graph file
    with open(graphpath,'r') as f:
        graph_data = pd.read_csv(f,sep='\t')

    #read the class label file if it is provided
    if node_class != None:
        with open(node_class,'r') as f:
            nodeclass_data = pd.read_csv(f,sep='\t')

        # generate node label vector
        label_index = dict()
        for item in zip(list(set(nodeclass_data.iloc[:,1].tolist())),range(len(list(set(nodeclass_data.iloc[:,1].tolist()))))):
            label_index[item[0]] = item[1]

        nodeclass_data_index = nodeclass_data.set_index(nodeclass_data.columns[0]).to_dict()[nodeclass_data.columns[1]]
        for name, cls in nodeclass_data_index.items():
            temp = np.zeros(len(label_index)).tolist()
            temp[label_index[cls]] = temp[label_index[cls]] + 1
            nodeclass_data_index[name] = [cls, temp]


    nodes = sorted(set(list(graph_data.iloc[:,0]) + list(graph_data.iloc[:,1])))
    id_map = pd.DataFrame(zip(nodes, range(len(nodes))))
    id_map = id_map.rename(columns={0: 'curie', 1: 'id'})

    #output the id map file
    id_map.to_csv(outpath+'/id_map.txt',sep='\t',index=None)

    #output the category mapping file
    temp = dict()
    for key, value in nodeclass_data_index.items():
            if value[0] not in temp:
                temp[value[0]] = value[1]

    temp2 = [(key,value) for key, value in temp.items()]
    df = pd.DataFrame(temp2, columns = ['category','category_vec'])
    df.to_csv(outpath+'/category_map.txt',sep='\t',index=None)

    map_dict = id_map.set_index('curie')['id'].to_dict()

    graph_data = pd.concat([graph_data,graph_data.source.rename('id1').map(map_dict),graph_data.target.rename('id2').map(map_dict)],axis=1)
    graph_data = graph_data.sort_values(by=['id1','id2'])
    graph_data = graph_data.reset_index(drop=True)

    #use part of data as validation data
    id =list(range(len(nodes)))
    random.Random(args.seed).shuffle(id)
    valid = id[0:int(len(nodes)*args.validation_percent)]

    # generate Graph json file

    data = {'directed': False,
            'graph': {'name': 'disjoint_union(,)'},
            'nodes': [],
            'links': [],
            "multigraph": False
            }

    if args.process==-1:
        with multiprocessing.Pool() as executor:
            out_iters = [(node,True) for node in range(len(nodes))]
            out_res = [elem for elem in chain.from_iterable(executor.map(initialize_node, out_iters))]

        data['nodes'] = out_res
    else:
        with multiprocessing.Pool(processes=args.process) as executor:
            out_iters = [(node, True) for node in range(len(nodes))]
            out_res = [elem for elem in chain.from_iterable(executor.map(initialize_node, out_iters))]

        data['nodes'] = out_res

    if args.process == -1:
        with multiprocessing.Pool() as executor:
            out_iters = [node for node in range(graph_data.shape[0])]
            out_res = [elem for elem in chain.from_iterable(executor.map(initialize_edge, out_iters))]

        data['links'] = out_res
    else:
        with multiprocessing.Pool(processes=args.process) as executor:
            out_iters = [node for node in range(graph_data.shape[0])]
            out_res = [elem for elem in chain.from_iterable(executor.map(initialize_edge, out_iters))]

        data['links'] = out_res

    #save graph
    with open(outpath+'/data-G.json','w') as f:
        f.write(json.dumps(data))

    #generate class_label
    if node_class == None:
        class_map = {str(i):[1] for i in range(len(nodes))}
    else:
        class_map = {str(i):nodeclass_data_index[nodes[i]][1] for i in range(len(nodes))}
    #save labels
    with open(outpath+'/data-class_map.json','w') as f:
        f.write(json.dumps(class_map))

    #generate id_label
    id_map = {str(i):i for i in range(len(nodes))}
    #save nodes
    with open(outpath+'/data-id_map.json','w') as f:
        f.write(json.dumps(id_map))
