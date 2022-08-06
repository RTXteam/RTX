import collections
import os
import pickle

import torch
import torch.nn as nn
import pandas as pd
import model_utilities

class KnowledgeGraph(nn.Module):
    """
    The knowledge graph is stored with an adjacency list.
    """
    def __init__(self, args, bandwidth=3000, emb_dropout_rate=0, bucket_interval=50, load_graph=True):
        super(KnowledgeGraph, self).__init__()
        
        ## basic params:
        self.args = args
        self.logger = args.logger
        
        ## knowledge graph specific params:
        self.adj_list = None
        self.bandwidth = bandwidth
        self.data_dir = args.data_dir
        self.bucket_interval = bucket_interval
        self.use_gpu = args.use_gpu
        self.load_graph = load_graph

        self.action_space = None
        self.action_space_buckets = None
        self.train_targets = None
        self.val_targets = None
        self.all_targets = None
        self.train_target_vectors = None
        self.val_target_vectors = None
        self.all_target_vectors = None
        self.graph = dict()

        self.args.logger.info('Create knowledge graph')
        self.load_graph_data()

        # Define entity embeds and relation embeds
        self.entity_dim = None
        self.entity_type_dim = None
        self.relation_dim = None
        self.emb_dropout_rate = emb_dropout_rate
        self.entity_embeddings = None
        self.entity_type_embeddings = None
        self.relation_embeddings = None
        self.EDropout = None
        self.ETDropout = None
        self.RDropout = None
        self.define_modules()

    def load_graph_data(self):
        # Load indices
        self.entity2id, self.id2entity = self.args.entity2id, self.args.id2entity
        self.type2id, self.id2type = self.args.type2id, self.args.id2type
        self.entity2typeid = self.args.entity2typeid
        self.relation2id, self.id2relation = self.args.relation2id, self.args.id2relation
       
        # Load graph structures
        if self.load_graph: 
            # Base graph structure used for training and test
            adj_list_path = os.path.join(self.data_dir, 'adj_list.pkl')
            with open(adj_list_path, 'rb') as f:
                self.adj_list = pickle.load(f)
            self.vectorize_action_space()

    def vectorize_action_space(self):
        """
        Pre-process and numericalize the knowledge graph structure.
        """
        def load_page_rank_scores(input_path):
            pgrk_scores = collections.defaultdict(float)
            with open(input_path) as f:
                for line in f:
                    entity, score = line.strip().split('\t')
                    entity_id = self.entity2id[entity.strip()]
                    score = float(score)
                    pgrk_scores[entity_id] = score
            return pgrk_scores
                            
        def get_action_space(source):
            action_space = []
            if source in self.adj_list:
                for relation in self.adj_list[source]:
                    targets = self.adj_list[source][relation]
                    for target in targets:
                        action_space.append((relation, target))
                if len(action_space) + 1 >= self.bandwidth:
                    sorted_action_space = sorted(action_space, key=lambda x: page_rank_scores[x[1]], reverse=True)
                    action_space = sorted_action_space[:self.bandwidth]
            action_space.insert(0, (self.self_edge, source))
            return action_space

        def vectorize_action_space(action_space_list, action_space_size):
            bucket_size = len(action_space_list)
            r_space = torch.zeros(bucket_size, action_space_size)
            e_space = torch.zeros(bucket_size, action_space_size)
            action_mask = torch.zeros(bucket_size, action_space_size)
            for i, action_space in enumerate(action_space_list):
                for j, (r, e) in enumerate(action_space):
                    r_space[i, j] = r
                    e_space[i, j] = e
                    action_mask[i, j] = 1

            if self.use_gpu:
                r_space = model_utilities.int_var_cuda(r_space, use_gpu=True)
                e_space = model_utilities.int_var_cuda(e_space, use_gpu=True)
                action_mask = model_utilities.var_cuda(action_mask, use_gpu=True)
            else:
                r_space = model_utilities.int_var_cuda(r_space, use_gpu=False)
                e_space = model_utilities.int_var_cuda(e_space, use_gpu=False)
                action_mask = model_utilities.var_cuda(action_mask, use_gpu=False)     

            return ((r_space, e_space), action_mask)

        ## compute graph statistics
        num_triples = 0
        self.out_degrees = collections.defaultdict(int)
        for source in self.adj_list:
            for relation in self.adj_list[source]:
                num_triples += len(self.adj_list[source][relation])
                self.out_degrees[source] += len(self.adj_list[source][relation])
        self.logger.info(f"{num_triples} facts in knowledge graph")
        stats = dict(pd.Series(list(self.out_degrees.values())).describe())
        msg = ''
        for key in stats:
            if key != 'count':
                msg += f' {key} {stats[key]}'
        self.logger.info(f"stats of out degree: {msg}")

        # load page rank scores
        page_rank_scores = load_page_rank_scores(os.path.join(self.data_dir, 'kg.pgrk'))

        # Store action spaces in buckets.
        self.logger.info("Storing action spaces in buckets")
        self.action_space_buckets = {}
        action_space_buckets_discrete = collections.defaultdict(list)
        self.entity2bucketid = torch.zeros(self.num_entities, 2).long()
        for source in range(self.num_entities):
            # Base graph pruning and adding self-loop edges
            action_space = get_action_space(source)
            self.graph[source] = action_space
            key = int(len(action_space) / self.bucket_interval) + 1
            self.entity2bucketid[source, 0] = key
            self.entity2bucketid[source, 1] = len(action_space_buckets_discrete[key])
            action_space_buckets_discrete[key].append(action_space)
        for key in action_space_buckets_discrete:
            self.logger.info(f'Vectorizing action spaces bucket {key}...')
            self.action_space_buckets[key] = vectorize_action_space(action_space_buckets_discrete[key], key * self.bucket_interval)

    def get_all_entity_embeddings(self):
        return self.EDropout(self.entity_embeddings.weight)

    def get_entity_embeddings(self, e):
        return self.EDropout(self.entity_embeddings(e))

    def get_all_relation_embeddings(self):
        return self.RDropout(self.relation_embeddings.weight)

    def get_relation_embeddings(self, r):
        return self.RDropout(self.relation_embeddings(r))

    def id2triples(self, triple):
        source, target, relation = triple
        return self.id2entity[source], self.id2entity[target], self.id2relation[relation]

    def triple2ids(self, triple):
        source, target, relation = triple
        return self.entity2id[source], self.entity2id[target], self.relation2id[relation]

    def define_modules(self):
        self.logger.info('Use pretrain entity embedding as entity embedding')
        entity_embeds = model_utilities.entity_load_embed(self.args)
        entity_embeds = torch.cat([torch.zeros(entity_embeds.shape[1]).view(1,-1),entity_embeds]) # add dummy entity embedding 
        self.entity_embeddings = nn.Embedding(entity_embeds.shape[0], entity_embeds.shape[1], padding_idx=0, _weight=entity_embeds)
        assert self.num_entities == self.entity_embeddings.weight.shape[0]
        self.entity_embeddings.weight.requires_grad = False
        self.EDropout = nn.Dropout(self.emb_dropout_rate)

        self.logger.info('Use one-hot encoding as relation embedding')
        relation_embeds = model_utilities.relation_load_embed(self.args)
        relation_embeds = torch.cat([torch.zeros(relation_embeds.shape[1]).view(1,-1),relation_embeds]) # add dummy relation embedding
        self.relation_embeddings = nn.Embedding(relation_embeds.shape[0], relation_embeds.shape[1], padding_idx=0, _weight=relation_embeds)
        assert self.num_relations == self.relation_embeddings.weight.shape[0]
        self.relation_embeddings.weight.requires_grad = False
        self.RDropout = nn.Dropout(self.emb_dropout_rate)

    @property
    def num_entities(self):
        return len(self.entity2id)

    @property
    def num_entity_types(self):
        return len(self.type2id)

    @property
    def num_relations(self):
        return len(self.relation2id)

    @property
    def self_edge(self):
        return model_utilities.SELF_LOOP_RELATION_ID       

    @property
    def dummy_r(self):
        return model_utilities.DUMMY_RELATION_ID

    @property
    def dummy_e(self):
        return model_utilities.DUMMY_ENTITY_ID
