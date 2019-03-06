#!/usr/bin/python3

# sharedtrunk.py: accept a Translator result-set in API v0.9 format and count up
# the number of times each edge appears among all the results. Print out a list
# of all edges, sorted by count in reverse order. Filter the resulting list of
# edges by minimum count (default 2). Result-set is provided as a URL (a "GET"
# assumed).

# Usage:
# sharedtrunk.py [--mincount=2] url

import requests
import requests_testadapter
import argparse
import json
import os
import collections

parser = argparse.ArgumentParser(description='sharedtrunk')
parser.add_argument('--mincount', type=int, help='whole number', nargs=1, default=2)
parser.add_argument('url', type=str, nargs=1)

# usage: sharedtrunk.py URL 
mincount = 2

from requests_testadapter import Resp

class LocalFileAdapter(requests.adapters.HTTPAdapter):
    def build_response_from_file(self, request):
        file_path = request.url[7:]
        with open(file_path, 'rb') as file:
            buff = bytearray(os.path.getsize(file_path))
            file.readinto(buff)
            resp = Resp(buff)
            r = self.build_response(request, resp)
            return r

    def send(self, request, stream=False, timeout=None,
             verify=True, cert=None, proxies=None):
        return self.build_response_from_file(request)


requests_session = requests.session()
requests_session.mount('file://', LocalFileAdapter())
args = parser.parse_args()
assert len(args.url) == 1, "need to specify url as the first argument"
url = args.url[0]
req_res = requests_session.get(url)
input_json = req_res.json()

res_list = input_json['result_list']
res_iter = iter(res_list)
master_graph = next(res_iter)['result_graph']
master_nodes_list = master_graph['node_list']
master_edges_list = master_graph['edge_list']

node_ctr = collections.Counter()
edge_ctr = collections.Counter()

master_nodes_dict = dict()
master_edges_dict = dict()

def make_key(source_curie: str, target_curie: str):
    return source_curie + '---' + target_curie

for node in master_nodes_list:
    curie = node['id']
    name = node['name']
    master_nodes_dict[curie] = node

for edge in master_edges_list:
    source_curie = edge['source_id']
    target_curie = edge['target_id']
    key = make_key(source_curie, target_curie)
    master_edges_dict[key] = edge
    
for result in res_iter:
    res_graph = result['result_graph']
    for node in res_graph['node_list']:
        curie = node['id']
        node_ctr[curie] += 1
    for edge in res_graph['edge_list']:
        source_curie = edge['source_id']
        target_curie = edge['target_id']
        key = make_key(source_curie, target_curie)
        edge_ctr[key] += 1

counts_inorder = node_ctr.most_common()
counts_inorder_filt = [(node_id, node_count) for (node_id, node_count) in counts_inorder if node_count >= mincount]
nodes_matched_filt_set = set([node_id for (node_id, node_count) in counts_inorder_filt])
shared_edges = set()

for node1 in nodes_matched_filt_set:
    for node2 in nodes_matched_filt_set:
        key = make_key(node1, node2)
        if key in master_edges_dict:
            shared_edges.add(key)

edge_count = [(key, count) for (key, count) in edge_ctr.most_common() if key in shared_edges]

res_data = {'node_count': counts_inorder_filt,
            'edge_count': edge_count}

print(json.dumps(res_data))

    







