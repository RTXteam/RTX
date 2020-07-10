## This script is used to generate random walk file (eg. walks.txt, please see https://github.com/williamleif/GraphSAGE
# for more details) via batch by batch for running Graphsage

from __future__ import print_function

import json
import numpy as np
import pandas as pd
import random
import os
import sys
import argparse
from networkx.readwrite import json_graph
import multiprocessing
from datetime import datetime
from itertools import chain

parser = argparse.ArgumentParser()
parser.add_argument("--Gjson", type=str, help="The path of G.json file")
parser.add_argument("-l", "--walk_length", type=int, help="Random walk length", default=200)
parser.add_argument("-r", "--number_of_walks", type=int, help="Number of random walks per node", default=10)
parser.add_argument("-b", "--batch_size", type=int, help="Size of batch for each run", default=100000)
parser.add_argument("-p", "--process", type=int, help="Number of processes to be used", default=-1)
parser.add_argument("-o", "--output", type=str, help="The path of output folder", default="/graphsage_input")

args = parser.parse_args()

## setting functions compatible with parallel running
def run_random_walks(this):

    pairs = []
    node, num_walks, walk_len = this

    if G.degree(node) == 0:
        pairs = pairs
    else:
        for i in range(num_walks):
            curr_node = node
            for j in range(walk_len):
                next_node = random.choice([n for n in G.neighbors(curr_node)])
                # self co-occurrences are useless
                if curr_node != node:
                    pairs.append((node, curr_node))
                curr_node = next_node
    return pairs


if __name__ == "__main__":
    # change to the current path
    current_path = os.path.split(os.path.realpath(__file__))[0]
    os.chdir(current_path)

    # check the input arguments
    if args.Gjson == None or not os.path.exists(os.path.realpath(args.Gjson)):
        sys.exit('Error Occurred! Please provide the correct path of your G.json file.')
    else:
        Gjson = args.Gjson

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
    with open(Gjson,'r') as input_file:
	    G_data = json.load(input_file)

    # transform to networkx graph format
    G = json_graph.node_link_graph(G_data)
    # pull out the training nodes and generate the training subgraph
    G_nodes = [n for n in G.nodes() if not G.nodes[n]["val"] and not G.nodes[n]["test"]]
    G = G.subgraph(G_nodes)
    del G_data ## delete variable to release ram

    # set up the batches
    batch =list(range(0,len(G_nodes),args.batch_size))
    batch.append(len(G_nodes))

    print(f'Total training data: {len(G_nodes)}')
    print(f'The number of nodes in training graph: {len(G.nodes)}')

    print(f'total batch: {len(batch)-1}')

    ## run each batch in parallel
    for i in range(len(batch)):
        if((i+1)<len(batch)):
            print(f'Here is batch{i+1}')
            start = batch[i]
            end = batch[i+1]
            if args.process == -1:
                with multiprocessing.Pool() as executor:
                    out_iters = [(node, args.number_of_walks, args.walk_length) for node in G_nodes[start:end]]
                    out_res = [elem for elem in chain.from_iterable(executor.map(run_random_walks, out_iters))]
            else:
                with multiprocessing.Pool(processes=args.process) as executor:
                    out_iters = [(node, args.number_of_walks, args.walk_length) for node in G_nodes[start:end]]
                    out_res = [elem for elem in chain.from_iterable(executor.map(run_random_walks, out_iters))]
            with open(outpath+'/data-walks.txt', "a") as fp:
                if i==0:
                    fp.write("\n".join([str(p[0]) + "\t" + str(p[1]) for p in out_res]))
                else:
                    fp.write("\n")
                    fp.write("\n".join([str(p[0]) + "\t" + str(p[1]) for p in out_res]))

