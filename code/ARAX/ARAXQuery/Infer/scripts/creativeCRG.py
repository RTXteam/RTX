from typing import List, Dict, Set, Union, Optional
import os, sys
import joblib
import numpy as np
import pandas as pd
# import graph_tool.all as gt
from tqdm import tqdm, trange

pathlist = os.getcwd().split(os.path.sep)
RTXindex = pathlist.index("RTX")
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'ARAXQuery']))
from ARAX_response import ARAXResponse
from ARAX_query import ARAXQuery
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'UI', 'OpenAPI', 'python-flask-server']))
import openapi_server
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'NodeSynonymizer']))
from node_synonymizer import NodeSynonymizer
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code']))
from RTXConfiguration import RTXConfiguration
RTXConfig = RTXConfiguration()
# response = ARAXResponse()

def load_ML_CRGmodel(response: ARAXResponse, model_path: str, model_type: str):

    if response is None:
        response.error("Please give a response object, it is None now")
        return None

    if model_path:
        if model_type in ['increase', 'decrease']:
            if model_type == 'increase':
                increase_model_name = RTXConfig.xcrg_increase_model_path.split("/")[-1]
                file_path = os.path.join(model_path, increase_model_name)
                fitModel = joblib.load(file_path)
            else:
                decrease_model_name = RTXConfig.xcrg_decrease_model_path.split("/")[-1]
                file_path = os.path.join(model_path, decrease_model_name)
                fitModel = joblib.load(file_path)
            return fitModel
        else:
            response.error(f"The parameter 'model_type' allows either 'increase' or 'decrease'. But {model_type} is provided.")
            return None
    else:
        return None

def build_DSL_command(start_n: str, end_n: str, interm_len: int, M: int = 10, kp: Optional[str] = 'infores:rtx-kg2', interm_ids: Optional[List[Optional[str]]] = None, interm_names: Optional[List[Optional[str]]] = None, interm_categories: Optional[List[Optional[str]]] =None):

    action_list = []
    temp_action_list = []
    interm_ids = [None]*interm_len if not interm_ids else interm_ids
    interm_names = [None]*interm_len if not interm_names else interm_names
    interm_categories = [None]*interm_len if not interm_categories else interm_categories
    ## build actions
    action_list.append(f"add_qnode(ids={start_n}, key=n00)")
    for index, param_set in enumerate(zip(interm_ids, interm_names, interm_categories)):
        command_line = "add_qnode("
        if param_set[0]:
            command_line += f"ids={param_set[0]},"
        if param_set[1]:
            command_line += f"name={param_set[1]},"
        if param_set[2]:
            command_line += f"categories={param_set[2]},"
        command_line += f"key=n0{index+1})"
        action_list.append(command_line)
        temp_action_list.append(f"add_qedge(subject=n0{index}, object=n0{index+1}, key=e0{index})")
    action_list.append(f"add_qnode(ids={end_n}, key=n0{index+2})")
    temp_action_list.append(f"add_qedge(subject=n0{index+1}, object=n0{index+2}, key=e0{index+1})")
    action_list += temp_action_list
    if kp:
        action_list.append(f"expand(kp={kp})")
    else:
        action_list.append("expand()")
    action_list.append("resultify()")
    action_list.append(f"filter_results(action=limit_number_of_results, max_results={M})")

    return {"operations": {"actions": action_list}} 

def extract_path(path_result: openapi_server.models.result.Result, mapping: Dict[str, str]):
    res = dict()
    node_bindings = sorted(path_result.node_bindings.items(), key=lambda x: x[0])
    # FIXME: fina a better to figure out the parents in subclass reasoning
    path_result_analyses = path_result.analyses[0]
    sublcass_edge_keys = [x for x in list(path_result_analyses.edge_bindings.keys()) if 'subclass' in x]
    find_parent = dict()
    for key in sublcass_edge_keys:
        qnode_key = key.split('--')[-1]
        parent_node = path_result_analyses.edge_bindings[key][0].id.split('--')[-1]
        find_parent[qnode_key] = parent_node
    edge_bindings = sorted(path_result_analyses.edge_bindings.items(), key=lambda x: x[0])
    for index in range(len(node_bindings) - 1):
        qnode_id1, curie1 = node_bindings[index][0], node_bindings[index][1][0].id
        curie1 = find_parent[qnode_id1] if qnode_id1 in find_parent else curie1
        qnode_id2, curie2 = node_bindings[index+1][0], node_bindings[index+1][1][0].id
        curie2 = find_parent[qnode_id1] if qnode_id2 in find_parent else curie2
        qedge_id, edge_list = edge_bindings[index][0], edge_bindings[index][1]
        res.update({qnode_id1:curie1})
        filtered_edge_list = [edge.id for edge in edge_list if (curie1 in edge.id.split('--')[0] and curie2 in edge.id.split('--')[-1]) or (curie2 in edge.id.split('--')[0] and curie1 in edge.id.split('--')[-1])]
        if len(filtered_edge_list) == 0:
            return None
        else:
            res.update({qedge_id:[(edge.id, mapping[edge.id]) for edge in edge_list if (curie1 in edge.id.split('--')[0] and curie2 in edge.id.split('--')[-1]) or (curie2 in edge.id.split('--')[0] and curie1 in edge.id.split('--')[-1])]})
        res.update({qnode_id2:curie2})
    return res

class creativeCRG:

    def __init__(self, response: ARAXResponse, data_path: str):

        ## set up parameters
        self.response = response
        self.data_path = data_path
        self.chemical_type = ['biolink:ChemicalEntity', 'biolink:ChemicalMixture','biolink:SmallMolecule']
        self.gene_type = ['biolink:Gene','biolink:Protein']

        ## load datasets
        self.response.info(f"loading embeddings and models into memory")
        
        # load embeddings
        chemical_gene_embeddings_name = RTXConfig.xcrg_embeddings_path.split("/")[-1]
        npzfile = np.load(os.path.join(self.data_path, chemical_gene_embeddings_name), allow_pickle=True)
        self.chemical_curies = npzfile['chemical_curies'].tolist()
        self.chemical_curie_types = npzfile['chemical_curie_types'].tolist()
        self.chemical_embs = npzfile['chemical_embs']
        self.gene_curies = npzfile['gene_curies'].tolist()
        self.gene_curie_types = npzfile['gene_curie_types'].tolist()
        self.gene_embs = npzfile['gene_embs']


        # load ML models
        self.increase_model = load_ML_CRGmodel(self.response, self.data_path, 'increase')
        self.decrease_model = load_ML_CRGmodel(self.response, self.data_path, 'decrease')

        # initialize Node Synonymizer
        self.synonymizer = NodeSynonymizer()

        ## initialize other variables
        self.num_chemicals = len(self.chemical_curies)
        self.num_genes = len(self.gene_curies)
        self._top_N_chemicals_dict = dict()
        self._top_N_chemicals_dict['increase'] = dict()
        self._top_N_chemicals_dict['decrease'] = dict()
        self._top_N_genes_dict = dict()
        self._top_N_genes_dict['increase'] = dict()
        self._top_N_genes_dict['decrease'] = dict()

    def get_preferred_curie(self, curie: str):

        if curie:
            normalizer_res = self.synonymizer.get_canonical_curies(curie)[curie]
            if normalizer_res:
                preferred_curie = normalizer_res['preferred_curie']
                return preferred_curie
            else:
                self.response.warning(f"Cannot get the preferred curie for {curie}")
                return None        
        else:
            self.response.warning(f"Given curie is {curie}")
            return None

    def predict_top_N_chemicals(self, query_gene: str, N: int = 10, threshold: float = 0.5, model_type: str = 'increase'):

        if not query_gene or not isinstance(query_gene, str):
            self.response.warning(f"The parameter 'query_gene' should be string. But {query_gene} is provided.")
            return None        

        if not N or not isinstance(N, int):
            self.response.warning(f"The parameter 'N' should be integer. But {N} is provided.")
            return None

        if not threshold or not isinstance(threshold, float) or not (0 <= threshold <= 1):
            self.response.warning(f"The parameter 'threshold' should be float between 0 and 1. But {threshold} is provided.")
            return None   

        if query_gene:
            self.response.info(f"Predicting top{N} chemicals for gene {query_gene}")

            ## get the preferred curie
            # preferred_query_gene = self.get_preferred_curie(query_gene)
            # if not preferred_query_gene:
            #     return None
            # self.response.info(f"Use the preferred curie {preferred_query_gene} of gene {query_gene} for prediction")
            preferred_query_gene = query_gene

            if model_type not in ['increase', 'decrease']:
                self.response.warning(f"The parameter 'model_type' allows either 'increase' or 'decrease'. But {model_type} is provided.")
                return None
            if preferred_query_gene not in self._top_N_genes_dict[model_type]:
                ## check if the query gene curie was trained in the specific model and if so, get its embedding
                if preferred_query_gene not in self.gene_curies:
                    self.response.warning(f"The increase-type model was not trained with gene curie {preferred_query_gene}.")
                    return None
                else:
                    query_gene_array = np.tile(self.gene_embs[self.gene_curies.index(preferred_query_gene)].reshape(1,-1),(self.num_chemicals,1))
                ## get all chemical embeddings
                chemical_array = self.chemical_embs
                ## do prediction
                X = np.hstack([chemical_array,query_gene_array])
                if model_type == 'increase':
                    probas = self.increase_model.predict_proba(X)
                else:
                    probas = self.decrease_model.predict_proba(X)
                res = pd.concat([pd.DataFrame(self.chemical_curies),pd.DataFrame([preferred_query_gene] * self.num_chemicals),pd.DataFrame(probas)], axis=1)
                res.columns = ['chemical_id','gene_id','tn_prob','tp_prob']
                res = res.sort_values(by=['tp_prob'],ascending=False).reset_index(drop=True)
                self._top_N_genes_dict[model_type][preferred_query_gene] = res

                ## filter results according to threshold
                if threshold:
                    res = res.loc[res['tp_prob'] >= threshold,:].reset_index(drop=True)
                
                ## give warning if the number of result records is smaller than the requirement
                if len(res) == 0:
                    self.response.warning(f"No chemical-gene pair meets the requirement of threshold >={threshold}. Perhaps try using more loose threshold.")
                if len(res) < N:
                    self.response.warning(f"No chemical-gene pair meets the requirement of threshold >={threshold} and top{N}. Only has {len(res)} satisfiable results.")

                return res.iloc[:N,:]
            else:

                ## filter results according to threshold
                res = self._top_N_genes_dict[model_type][preferred_query_gene]
                if threshold:
                    res = res.loc[res['tp_prob'] >= threshold,:].reset_index(drop=True)

                ## give warning if the number of result records is smaller than the requirement
                if len(res) == 0:
                    self.response.warning(f"No chemical-gene pair meets the requirement of threshold >={threshold}. Perhaps try using more loose threshold.")
                if len(res) < N:
                    self.response.warning(f"No chemical-gene pair meets the requirement of threshold >={threshold} and top{N}. Only has {len(res)} satisfiable results.")

                return res.iloc[:N,:]
        else:
            self.response.warning(f"The parameter 'query_gene' is not provided. Please give a gene curie to the parameter 'query_gene'.")
            return None

    def predict_top_N_genes(self, query_chemical: str, N: int = 10, threshold: float = 0.5, model_type: str = 'increase'):

        if not query_chemical or not isinstance(query_chemical, str):
            self.response.warning(f"The parameter 'query_chemical' should be string. But {query_chemical} is provided.")
            return None        

        if not N or not isinstance(N, int):
            self.response.warning(f"The parameter 'N' should be integer. But {N} is provided.")
            return None

        if not threshold or not isinstance(threshold, float) or not (0 <= threshold <= 1):
            self.response.warning(f"The parameter 'threshold' should be float between 0 and 1. But {threshold} is provided.")
            return None   

        if query_chemical:
            self.response.info(f"Predicting top{N} genes for chemical {query_chemical}")

            ## get the preferred curie
            # preferred_query_chemical = self.get_preferred_curie(query_chemical)
            # if not preferred_query_chemical:
            #     return None
            # self.response.info(f"Use the preferred curie {preferred_query_chemical} of chemical {query_chemical} for prediction.")
            preferred_query_chemical = query_chemical

            if model_type not in ['increase', 'decrease']:
                self.response.warning(f"The parameter 'model_type' allows either 'increase' or 'decrease'. But {model_type} is provided.")
                return None
            if preferred_query_chemical not in self._top_N_chemicals_dict[model_type]:
                ## check if the query chemical curie was trained in the specific model and if so, get its embedding 
                if preferred_query_chemical not in self.chemical_curies:
                    self.response.warning(f"The increase-type model was not trained with chemical curie {query_chemical}.")
                    return None
                else:
                    query_chemical_array = np.tile(self.chemical_embs[self.chemical_curies.index(preferred_query_chemical)].reshape(1,-1),(self.num_genes,1))
                ## get all gene embeddings
                gene_array = self.gene_embs
                ## do prediction
                X = np.hstack([query_chemical_array,gene_array])
                if model_type == 'increase':
                    probas = self.increase_model.predict_proba(X)
                else:
                    probas = self.decrease_model.predict_proba(X)
                res = pd.concat([pd.DataFrame([preferred_query_chemical] * self.num_genes),pd.DataFrame(self.gene_curies),pd.DataFrame(probas)], axis=1)
                res.columns = ['chemical_id','gene_id','tn_prob','tp_prob']
                res = res.sort_values(by=['tp_prob'],ascending=False).reset_index(drop=True)
                self._top_N_chemicals_dict[model_type][preferred_query_chemical] = res

                ## filter results according to threshold
                if threshold:
                    res = res.loc[res['tp_prob'] >= threshold,:].reset_index(drop=True)

                ## give warning if the number of result records is smaller than the requirement
                if len(res) == 0:
                    self.response.warning(f"No chemical-gene pair meets the requirement of threshold >={threshold}. Perhaps try using more loose threshold.")
                if len(res) < N:
                    self.response.warning(f"No chemical-gene pair meets the requirement of threshold >={threshold} and top{N}. Only has {len(res)} satisfiable results.")

                return res.iloc[:N,:]
            else:

                ## filter results according to threshold
                res = self._top_N_chemicals_dict[model_type][preferred_query_chemical]

                if threshold:
                    res = res.loc[res['tp_prob'] >= threshold,:].reset_index(drop=True)

                ## give warning if the number of result records is smaller than the requirement
                if len(res) == 0:
                    self.response.warning(f"No chemical-gene pair meets the requirement of threshold >={threshold}. Perhaps try using more loose threshold.")
                if len(res) < N:
                    self.response.warning(f"No chemical-gene pair meets the requirement of threshold >={threshold} and top{N}. Only has {len(res)} satisfiable results.")

                return res.iloc[:N,:]

        else:
            self.response.warning(f"The parameter 'query_chemical' is not provided. Please assign a chemical curie to the parameter 'query_chemical'.")
            return None

    def predict_top_M_paths(self, query_chemical: Optional[str], query_gene: Optional[str], model_type: str = 'increase', N: int = 10, M: int = 10, threshold: float = 0.5, kp: Optional[str] = 'infores:rtx-kg2', path_len: int = 2, interm_ids: Optional[List[Optional[str]]] = None, interm_names: Optional[List[Optional[str]]] = None, interm_categories: Optional[List[Optional[str]]] =None):

        def _check_params(query_chemical: Optional[str], query_gene: Optional[str], model_type: str = 'increase', N: int = 10, M: int = 10, threshold: float = 0.5, path_len: int = 2, kp: Optional[str] = None, interm_ids: Optional[List[Optional[str]]] = None, interm_names: Optional[List[Optional[str]]] = None, interm_categories: Optional[List[Optional[str]]] =None): 

            ## check if query_chemical and query_gene are correct
            temp_check = True
            if query_chemical and query_gene:
                self.response.warning(f"Please predict the top M paths for either chemical {query_chemical} or gene {query_gene}， but not both")
                temp_check = False
            elif not query_chemical and not query_gene:
                self.response.warning(f"Please given either 'query_chemical' (Now is {query_chemical}) or 'query_gene' (Now is {query_gene}).")
                temp_check = False
            elif query_chemical and not isinstance(query_chemical, str):
                self.response.warning(f"The parameter 'query_chemical' should be string. But {query_chemical} is provided.")
                temp_check = False              
            elif query_gene and not isinstance(query_gene, str):
                self.response.warning(f"The parameter 'query_gene' should be string. But {query_gene} is provided.")
                temp_check = False     
            assert temp_check
    
            assert N and isinstance(N, int), f"The parameter 'N' should be integer. But {M} is provided."

            assert M and isinstance(M, int), f"The parameter 'M' should be integer. But {M} is provided."

            assert threshold and isinstance(threshold, float) and (0 <= threshold <= 1), f"The parameter 'threshold' should be float between 0 and 1. But {threshold} is provided."

            assert model_type in ['increase', 'decrease'], f"The parameter 'model_type' allows either 'increase' or 'decrease'. But '{model_type}' is provided."

            num_interm = path_len + 1 - 2
            ## check if the number of intermediate nodes is 0
            assert num_interm > 0, "the number of intermediate nodes cannot be 0"

            ## check if kp is correct
            assert kp is None or isinstance(kp, str), f"The parameter 'kp' is not None or a string"

            ## check if the length of "interm_ids“ list is the same as the number of intermediate nodes
            assert interm_ids is None or isinstance(interm_ids, list), f"The parameter 'interm_ids' is not None or a list"
            if interm_ids:
                assert len(interm_ids) == num_interm, f"the length of 'interm_ids' list (now is {len(interm_ids)}) should be the same as the number of intermediate nodes (now is {num_interm})" 

            ## check if the length of "interm_names list is the same as the number of intermediate nodes
            assert interm_names is None or isinstance(interm_names, list), f"The parameter 'interm_names' is not None or a list"
            if interm_names:
                assert len(interm_names) == num_interm, f"the length of 'interm_names' list (now is {len(interm_names)}) should be the same as the number of intermediate nodes (now is {num_interm})"

            ## check if the length of "interm_categories list is the same as the number of intermediate nodes
            assert interm_categories is None or isinstance(interm_categories, list), f"The parameter 'interm_categories' is not None or a list"
            if interm_categories:
                assert len(interm_categories) == num_interm, f"the length of 'interm_categories' list (now is {len(interm_categories)}) should be the same as the number of intermediate nodes (now is {num_interm})" 

        ## check parameters
        _check_params(query_chemical, query_gene, model_type, N, M, threshold, path_len, kp, interm_ids, interm_names, interm_categories)

        ## create DSL commands to extract paths
        if query_chemical:
            ## get the preferred curie
            # preferred_query_chemical = self.get_preferred_curie(query_chemical)
            # if not preferred_query_chemical:
            #     return None
            # self.response.info(f"Use the preferred curie {preferred_query_chemical} of chemical {query_chemical} for prediction")
            preferred_query_chemical = query_chemical

            if preferred_query_chemical not in self._top_N_chemicals_dict[model_type]:
                self.response.warning(f"No '{model_type}-type' prediction record for the chemical {preferred_query_chemical}. Please first call the 'predict_top_N_genes' method.")
                return None
            else:
                res = self._top_N_chemicals_dict[model_type][preferred_query_chemical]
                res = res.loc[res['tp_prob'] >= threshold,:].reset_index(drop=True).iloc[:N,:]
                if len(res) == 0:
                    self.response.warning(f"There is no chemical-gene pair satisfying the requirement of top {N} with threshold >={threshold}. Perhaps try using more loose threshold.")
                    return None
                else:
                    top_paths = dict()
                    for start_n, end_n in tqdm(res[['chemical_id','gene_id']].to_numpy()):
                        self.response.info(f"extract top{M} paths for the {start_n}-{end_n} pair")
                        DSL_query = build_DSL_command(start_n, end_n, path_len + 1 - 2, M, kp, interm_ids, interm_names, interm_categories)
                        araxq = ARAXQuery()
                        result = araxq.query(DSL_query)
                        message = araxq.response.envelope.message
                        mapping_edgekey_to_resource = {edge_key:[edge.sources, edge.attributes, edge.qualifiers] for edge_key, edge in message.knowledge_graph.edges.items()}

                        for result in message.results:
                            break

                        if result.status != 'OK':
                            self.response.warning(f"Get something wrong with using 'ARAXQuery' to extract paths for the {start_n}-{end_n} pair, we skip this pair.")
                            continue
                        else:
                            top_paths[(start_n, end_n)] = [extract_path(result, mapping_edgekey_to_resource) for result in message.results]
                    return top_paths
        else:

            ## get the preferred curie
            # preferred_query_gene = self.get_preferred_curie(query_gene)
            # if not preferred_query_gene:
            #     return None
            # self.response.info(f"Use the preferred curie {preferred_query_gene} of gene {preferred_query_gene} for prediction")
            preferred_query_gene = query_gene

            if preferred_query_gene not in self._top_N_genes_dict[model_type]:
                self.response.warning(f"No '{model_type}-type' prediction record for the gene {preferred_query_gene}. Please first call the 'predict_top_N_chemicals' method.")
                return None
            else:
                res = self._top_N_genes_dict[model_type][preferred_query_gene]
                res = res.loc[res['tp_prob'] >= threshold,:].reset_index(drop=True).iloc[:N,:]
                if len(res) == 0:
                    self.response.warning(f"There is no chemical-gene pair satisfying the requirement of top {N} with threshold >={threshold}. Perhaps try using more loose threshold.")
                    return None
                else:
                    top_paths = dict()
                    for start_n, end_n in tqdm(res[['chemical_id','gene_id']].to_numpy()):
                        self.response.info(f"extract top{M} paths for the {start_n}-{end_n} pair")
                        DSL_query = build_DSL_command(start_n, end_n, path_len + 1 - 2, M, kp, interm_ids, interm_names, interm_categories)
                        araxq = ARAXQuery()
                        result = araxq.query(DSL_query)
                        message = araxq.response.envelope.message
                        mapping_edgekey_to_resource = {edge_key:[edge.sources, edge.attributes, edge.qualifiers] for edge_key, edge in message.knowledge_graph.edges.items()}

                        if result.status != 'OK':
                            self.response.warning(f"Get something wrong with using 'ARAXQuery' to extract paths for the {start_n}-{end_n} pair, we skip this pair.")
                            continue
                        else:
                            top_paths[(start_n, end_n)] = [x for x in [extract_path(result, mapping_edgekey_to_resource) for result in message.results] if x]
                    return top_paths
    

