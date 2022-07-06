from typing import List, Dict, Set, Union, Optional
import os
import model_utilities
import pickle
import numpy as np
import pandas as pd
import graph_tool.all as gt
import itertools
import torch
from tqdm import tqdm, trange
from knowledge_graph import KnowledgeGraph
from kg_env import KGEnvironment
from models import DiscriminatorActorCritic

class creativeDTD:

    def __init__(self, data_path: str, model_path: str, use_gpu: bool = False):

        ## set up args
        self.args = model_utilities.set_args()
        self.args.data_dir = data_path
        self.args.logger = model_utilities.get_logger()

        ## check device
        self.args.use_gpu, self.args.device = model_utilities.check_device(logger = self.args.logger, use_gpu = use_gpu)

        ## load datasets
        self.entity_embeddings_dict = model_utilities.load_graphsage_unsupervised_embeddings(self.args.data_dir)
        self.args.entity2id, self.args.id2entity = model_utilities.load_index(os.path.join(self.args.data_dir, 'entity2freq.txt'))
        self.args.relation2id, self.args.id2relation = model_utilities.load_index(os.path.join(self.args.data_dir, 'relation2freq.txt'))
        self.args.type2id, self.args.id2type = model_utilities.load_index(os.path.join(self.args.data_dir, 'type2freq.txt'))
        with open(os.path.join(self.args.data_dir, 'entity2typeid.pkl'), 'rb') as infile:
            self.args.entity2typeid = pickle.load(infile)
        drug_type = ['biolink:Drug', 'biolink:SmallMolecule']
        drug_type_ids = [self.args.type2id[x] for x in drug_type]
        self.drug_curie_ids = [self.args.id2entity[index] for index, typeid in enumerate(self.args.entity2typeid) if typeid in drug_type_ids]

        ## load ML model
        self.ML_model = model_utilities.load_ML_model(model_path)

        ## load RL model
        # self.kg = KnowledgeGraph(self.args, bandwidth=self.args.bandwidth, emb_dropout_rate=self.args.emb_dropout_rate, bucket_interval=self.args.bucket_interval, load_graph=True)
        if self.args.use_gpu:
            with open(os.path.join(data_path,'kg_gpu.pkl'),'rb') as infile:
                self.kg = pickle.load(infile)
        else:
            with open(os.path.join(data_path,'kg_cpu.pkl'),'rb') as infile:
                self.kg = pickle.load(infile)
        self.env = KGEnvironment(self.args, self.kg, max_path_len=self.args.max_path, state_pre_history=self.args.state_history)
        self.RL_model = DiscriminatorActorCritic(self.args, self.kg, self.args.state_history, self.args.gamma, self.args.target_update, self.args.ac_hidden, self.args.disc_hidden, self.args.metadisc_hidden)
        self.args.policy_net_file = os.path.join(model_path,'RL_model','RL_policy_model.pt')
        policy_net = torch.load(self.args.policy_net_file, map_location=self.args.device)
        model_temp = self.RL_model.policy_net.state_dict()
        model_temp.update(policy_net)
        self.RL_model.policy_net.load_state_dict(model_temp)
        del policy_net
        del model_temp

        ## load graph
        self.G, self.etype = model_utilities.load_gt_kg(self.kg)

        ## other variables
        self.disease_curie = None
        self.top_N_drugs = None

    def set_query_disease(self, disease_curie: str):
        bool_value, normalized_disease_curie = model_utilities.check_curie_available(logger = self.args.logger, curie = disease_curie, available_curies_dict = self.args.entity2id)
        if bool_value:
            self.disease_curie = normalized_disease_curie
        else:
            self.args.logger.warning(f"Can't find curie {disease_curie}")

    def predict_top_N_drugs(self, N: int = 50):
        self.args.logger.info(f"Predicting top{N} drugs for disease {self.disease_curie}")
        if self.disease_curie:
            X = np.vstack([np.hstack([self.entity_embeddings_dict[drug_curie_id],self.entity_embeddings_dict[self.disease_curie]]) for drug_curie_id in self.drug_curie_ids])
            res_temp = self.ML_model.predict_proba(X)
            res = pd.concat([pd.DataFrame(self.drug_curie_ids),pd.DataFrame([self.disease_curie]*len(self.drug_curie_ids)),pd.DataFrame(res_temp)], axis=1)
            res.columns = ['drug_id','disease_id','tn_score','tp_score','unknown_score']
            res = res.sort_values(by=['tp_score'],ascending=False).reset_index(drop=True)
            self.top_N_drugs = res.iloc[:N,:]
            self.top_N_drugs = self.top_N_drugs.apply(lambda row: [row[0],model_utilities.id_to_name(row[0]),row[1],model_utilities.id_to_name(row[1]),row[2],row[3],row[4]], axis=1, result_type='expand')
            self.top_N_drugs.columns = ['drug_id','drug_name','disease_id','disease_name','tn_score','tp_score','unknown_score']
            return self.top_N_drugs
        else:
            self.args.logger.warning(f"No disease curie provided!! Please run 'set_query_disease' function to set up disease curie")
            return None

    def _extract_all_paths(self):
        if self.top_N_drugs is not None:
            self.args.logger.info(f"Extracting all paths with length 3 for disease {list(set(self.top_N_drugs['disease_id']))[0]}")
            self.filtered_res_all_paths = dict()
            filter_edges = [self.args.relation2id[edge] for edge in ['biolink:related_to','biolink:coexists_with','biolink:contraindicated_for']]
            for index1 in range(len(self.top_N_drugs)):
                source, target = self.top_N_drugs.loc[index1,['drug_id','disease_id']]
                all_paths = [list(path) for path in gt.all_paths(self.G, model_utilities.check_curie(source, self.args.entity2id)[1], model_utilities.check_curie(target, self.args.entity2id)[1], cutoff=3)]
                entity_paths = []
                relation_paths = []
                for path in all_paths:
                    path_temp = []
                    for index2 in range(len(path)-1):
                        if index2 == 0:
                            path_temp += [path[index2], list(self.etype[self.G.edge(path[index2], path[index2+1])]), path[index2+1]]
                        else:
                            path_temp += [list(self.etype[self.G.edge(path[index2], path[index2+1])]), path[index2+1]]
                    flattened_paths = list(itertools.product(*map(lambda x: [x] if type(x) is not list else x, path_temp)))
                    for flattened_path in flattened_paths:
                        if len(flattened_path) == 7:
                            relation_paths += [[self.args.relation2id['SELF_LOOP_RELATION']] + [x for index3, x in enumerate(flattened_path) if index3%2==1]]
                            entity_paths += [[x for index3, x in enumerate(flattened_path) if index3%2==0]]
                        elif len(flattened_path) == 5:
                            relation_paths += [[self.args.relation2id['SELF_LOOP_RELATION']] + [x for index3, x in enumerate(flattened_path) if index3%2==1] + [self.args.relation2id['SELF_LOOP_RELATION']]]
                            entity_paths += [[x for index3, x in enumerate(flattened_path) if index3%2==0] + [flattened_path[-1]]]
                        else:
                            logger.info(f"Found weird path: {flattened_path}")
                edge_mat = torch.tensor(relation_paths)
                node_mat = torch.tensor(np.array(entity_paths).astype(int))
                temp = pd.DataFrame(edge_mat.numpy())
                if len(temp) != 0:
                    keep_index = list(temp.loc[~(temp[1].isin(filter_edges) | temp[2].isin(filter_edges) | temp[3].isin(filter_edges)),:].index)
                    self.filtered_res_all_paths[(source,target)] = [edge_mat[keep_index],node_mat[keep_index]]
            return 1
        else:
            self.args.logger.warning(f"Please run 'predict_top_N_drugs' function to predict drugs first")
            return 0

    def _make_path(self, rel_ent_score):
        rel_vec, ent_vec, score = rel_ent_score
        return ['->'.join([model_utilities.id_to_name(self.args.id2entity[ent_vec[index]])+'->'+self.args.id2relation[rel_vec[index+1]] for index in range(len(ent_vec)-1)] + [model_utilities.id_to_name(self.args.id2entity[ent_vec[len(ent_vec)-1]])]), score]

    def _batch_get_true(self, args, batch_action_spaces, batch_true_actions):
        ((batch_r_space, batch_e_space), batch_action_mask) = batch_action_spaces
        if args.use_gpu:
            true_r = batch_true_actions[0].view(-1,1).cuda()
        else:
            true_r = batch_true_actions[0].view(-1,1)
        if args.use_gpu:
            true_e = batch_true_actions[1].view(-1,1).cuda()
        else:
            true_e = batch_true_actions[1].view(-1,1)
        true_idx_in_actor = torch.where((batch_r_space == true_r) * (batch_e_space == true_e))[1]

        return true_idx_in_actor, (true_r, true_e)

    def _select_true_action(self, model, batch_state, batch_action_spaces, batch_true_actions, args):
        device = args.device
        state_inputs = model.process_state(model.history_len, batch_state).to(device)
        true_idx_in_actor, true_next_actions = self._batch_get_true(args, batch_action_spaces, batch_true_actions)

        probs, _ = model.policy_net(state_inputs, batch_action_spaces)
        if args.use_gpu:
            torch.cuda.empty_cache()
        true_idx_in_actor = true_idx_in_actor.to(device)
        true_prob = probs.gather(1, true_idx_in_actor.view(-1, 1)).view(-1)
        weighted_logprob = torch.log((true_prob.view(-1,1)+model_utilities.TINY_VALUE) * torch.count_nonzero(probs, dim=1).view(-1,1))

        return true_next_actions, weighted_logprob

    def _batch_calculate_prob_score(self, args, batch_paths, env, model):

        env.reset()
        model.policy_net.eval()
        dataloader = model_utilities.ACDataLoader(list(range(batch_paths[1].shape[0])), args.batch_size, permutation=False)

        # pbar = tqdm(total=dataloader.num_paths)
        pred_prob_scores = []
        while dataloader.has_next():

            batch_path_id = dataloader.get_batch()
            source_ids = batch_paths[1][batch_path_id][:,0]
            env.initialize_path(source_ids)
            act_num = 1

            if args.use_gpu:
                action_log_weighted_prob = model_utilities.zeros_var_cuda(len(batch_path_id), use_gpu=True)
            else:
                action_log_weighted_prob = model_utilities.zeros_var_cuda(len(batch_path_id), use_gpu=False)

            while not env._done:
                batch_true_action = [batch_paths[0][batch_path_id][:,act_num], batch_paths[1][batch_path_id][:,act_num]]
                true_next_act, weighted_logprob = self._select_true_action(model, env._batch_curr_state, env._batch_curr_action_spaces, batch_true_action, args)
                env.batch_step(true_next_act)
                if args.use_gpu:
                    torch.cuda.empty_cache()
                action_log_weighted_prob = action_log_weighted_prob.view(-1, 1) + args.factor**(act_num-1) * weighted_logprob
                if args.use_gpu:
                    torch.cuda.empty_cache()
                act_num += 1
            ### End of episodes ##

            pred_prob_scores += [action_log_weighted_prob.view(-1).cpu().detach()]
            env.reset()

            if args.use_gpu:
                torch.cuda.empty_cache()
            # pbar.update(len(source_ids))

        return np.concatenate(pred_prob_scores)


    def predict_top_M_paths(self, M: int = 10):
        if self._extract_all_paths() != 0:
            self.args.logger.info(f"Calculating all paths' scores")
            ## set up some filtering rules
            filter_edges = [self.args.relation2id[edge] for edge in ['biolink:related_to','biolink:biolink:part_of','biolink:coexists_with','biolink:contraindicated_for'] if self.args.relation2id.get(edge)]

            pbar = tqdm(total=len(self.filtered_res_all_paths))
            for (source, target) in self.filtered_res_all_paths:
                batch_paths = self.filtered_res_all_paths[(source, target)]
                if len(batch_paths[1]) == 0:
                    continue
                ## filter out some paths with unwanted predicates
                temp = pd.DataFrame(batch_paths[0].numpy())
                keep_index = list(temp.loc[~(temp[1].isin(filter_edges) | temp[2].isin(filter_edges) | temp[3].isin(filter_edges)),:].index)
                batch_paths = [batch_paths[0][keep_index],batch_paths[1][keep_index]]
                pred_prob_scores = self._batch_calculate_prob_score(self.args, batch_paths, self.env, self.RL_model)
                pred_prob_scores = torch.tensor(pred_prob_scores)
                sorted_scores, indices = torch.sort(pred_prob_scores, descending=True)
                batch_paths_sorted = [batch_paths[0][indices], batch_paths[1][indices], sorted_scores]
                ## Note that the paths with the same nodes are counted as the same path
                temp_dict = dict()
                count = 0
                top_indexes = []
                for index, x in enumerate(batch_paths_sorted[1].numpy()):
                    if tuple(x) in temp_dict:
                        top_indexes += [index]
                    else:
                        count += 1
                        temp_dict[tuple(x)] = 1
                        top_indexes += [index]
                    if count == M:
                        break
                res = [batch_paths_sorted[0][top_indexes], batch_paths_sorted[1][top_indexes], batch_paths_sorted[2][top_indexes]]
                self.filtered_res_all_paths[(source, target)] = [self._make_path([res[0][index].numpy(),res[1][index].numpy(), res[2][index].numpy().item()]) for index in range(len(res[0]))]
                pbar.update(1)

            return self.filtered_res_all_paths
        else:
            return None

