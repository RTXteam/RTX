import os
import pickle
import joblib
import torch
import torch.nn as nn
import numpy as np
import sys
from typing import List, Dict, Set, Union, Optional
import logging
import collections
import argparse
from torch.autograd import Variable
import graph_tool.all as gt
from node_synonymizer import NodeSynonymizer
nodesynonymizer = NodeSynonymizer()

DUMMY_RELATION_ID = 0
SELF_LOOP_RELATION_ID = 1
DUMMY_ENTITY_ID = 0
TINY_VALUE = 1e-41

class ACDataLoader(object):
    def __init__(self, indexes, batch_size, permutation=True):
        self.indexes = np.array(indexes)
        self.num_paths = len(indexes)
        self.batch_size = batch_size
        self._permutation = permutation
        self.reset()

    def reset(self):
        if self._permutation:
            self._rand_perm = np.random.permutation(self.num_paths)
        else:
            self._rand_perm = np.array(range(self.num_paths))
        self._start_idx = 0
        self._has_next = True

    def has_next(self):
        return self._has_next

    def get_batch(self):
        if not self._has_next:
            return None
        # Multiple users per batch
        end_idx = min(self._start_idx + self.batch_size, self.num_paths)
        batch_idx = self._rand_perm[self._start_idx:end_idx]
        batch_indexes = self.indexes[batch_idx]
        self._has_next = self._has_next and end_idx < self.num_paths
        self._start_idx = end_idx
        return batch_indexes.tolist()

def load_graphsage_unsupervised_embeddings(data_path: str):
    file_path = os.path.join(data_path,'unsuprvised_graphsage_entity_embeddings.pkl')
    with open(file_path, 'rb') as infile:
        entity_embeddings_dict = pickle.load(infile)
    return entity_embeddings_dict

def load_ML_model(model_path: str):
    file_path = os.path.join(model_path,'ML_model','RF_model.pt')
    fitModel = joblib.load(file_path)
    return fitModel

def check_device(logger, use_gpu: bool = False, gpu: int = 0):
    if use_gpu and torch.cuda.is_available():
        use_gpu = True
        device = torch.device(f'cuda:{gpu}')
        torch.cuda.set_device(gpu)
    elif use_gpu:
        logger.info('No GPU is detected in this computer. Use CPU instead.')
        use_gpu = False
        device = 'cpu'
    else:
        use_gpu = False
        device = 'cpu'

    return [use_gpu, device]

def check_curie_available(logger, curie: str, available_curies_dict: dict):
    normalized_result = nodesynonymizer.get_canonical_curies(curie)[curie]
    if normalized_result:
        curie = normalized_result['preferred_curie']
    else:
        curie = curie
    
    if curie in available_curies_dict:
        return [True, curie]
    else:
        return [False, None]

def load_index(input_path: str):
    name_to_id, id_to_name = {}, {}
    with open(input_path) as f:
        for index, line in enumerate(f.readlines()):
            name, _ = line.strip().split()
            name_to_id[name] = index
            id_to_name[index] = name
    return name_to_id, id_to_name

def get_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s  [%(levelname)s]  %(message)s', datefmt="%Y-%m-%d %H:%M:%S")
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return logger

def check_curie(curie: str, entity2id):
    if curie is None:
        return (None, None)
    res = nodesynonymizer.get_canonical_curies(curie)[curie]
    if res is not None:
        preferred_curie = nodesynonymizer.get_canonical_curies(curie)[curie]['preferred_curie']
    else:
        preferred_curie = None
    if preferred_curie in entity2id:
        return (preferred_curie, entity2id[preferred_curie])
    else:
        return (preferred_curie, None)

def load_gt_kg(kg):
    G = gt.Graph()
    kg_tmp = dict()
    for source in kg.graph:
        for (relation, target) in kg.graph[source]:
            if (source, target) not in kg_tmp:
                kg_tmp[(source, target)] = set([relation])
            else:
                kg_tmp[(source, target)].update(set([relation]))
    etype = G.new_edge_property('object')
    for (source, target) in kg_tmp:
        e = G.add_edge(source,target)
        etype[e] = kg_tmp[(source, target)]
    # G.edge_properties['edge_type'] = etype
    return G, etype

def entity_load_embed(args):
    embedding_folder = os.path.join(args.data_dir, 'kg_init_embeddings')
    embeds = np.load(os.path.join(embedding_folder,'entity_embeddings.npy'))
    return torch.tensor(embeds).type(torch.float)

def relation_load_embed(args):
    embedding_folder = os.path.join(args.data_dir, 'kg_init_embeddings')
    embeds = np.load(os.path.join(embedding_folder,'relation_embeddings.npy'))
    return torch.tensor(embeds).type(torch.float)

def ones_var_cuda(s, requires_grad: bool = False, use_gpu: bool = True):
    if use_gpu is True:
        return Variable(torch.ones(s), requires_grad=requires_grad).cuda()
    else:
        return Variable(torch.ones(s), requires_grad=requires_grad).long()

def zeros_var_cuda(s, requires_grad: bool = False, use_gpu: bool = True):
    if use_gpu is True:
        return Variable(torch.zeros(s), requires_grad=requires_grad).cuda()
    else:
        return Variable(torch.zeros(s), requires_grad=requires_grad).long()

def int_var_cuda(x, requires_grad: bool = False, use_gpu: bool = True):
    if use_gpu is True:
        return Variable(x, requires_grad=requires_grad).long().cuda()
    else:
        return Variable(x, requires_grad=requires_grad).long()

def var_cuda(x, requires_grad: bool = False, use_gpu: bool = True):
    if use_gpu is True:
        return Variable(x, requires_grad=requires_grad).cuda()
    else:
        return Variable(x, requires_grad=requires_grad).long()

def set_args():
    parser = argparse.ArgumentParser()
    args = parser.parse_args()
    args.entity_dim = 100
    args.relation_dim = 100
    args.entity_type_dim = 100
    args.max_path = 3
    args.bandwidth = 3000
    args.bucket_interval = 50
    args.state_history = 2
    args.emb_dropout_rate = 0
    args.disc_hidden = [512, 512]
    args.disc_dropout_rate = 0.3
    args.metadisc_hidden = [512, 256]
    args.metadisc_dropout_rate = 0.3
    args.ac_hidden = [512, 512]
    args.actor_dropout_rate = 0.3
    args.critic_dropout_rate = 0.3
    args.act_dropout = 0.5
    args.target_update = 0.05
    args.gamma = 0.99
    args.factor = 0.9
    args.batch_size = 5000

    return args

def id_to_name(curie: str):
    if curie is None:
        return None
    if curie is not None:
        preferred_curie_name = nodesynonymizer.get_canonical_curies(curie)[curie]['preferred_name']
    else:
        preferred_curie_name = None
    return preferred_curie_name

def pad_and_cat(a, padding_value, padding_dim=1):
    max_dim_size = max([x.size()[padding_dim] for x in a])
    padded_a = []
    for x in a:
        if x.size()[padding_dim] < max_dim_size:
            res_len = max_dim_size - x.size()[1]
            pad = nn.ConstantPad1d((0, res_len), padding_value)
            padded_a.append(pad(x))
        else:
            padded_a.append(x)
    return torch.cat(padded_a, dim=0)

