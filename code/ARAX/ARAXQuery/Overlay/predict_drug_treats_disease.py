import sys
import os
import traceback
import numpy as np
import itertools
from datetime import datetime

# relative imports
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../OpenAPI/python-flask-server/")
from openapi_server.models.attribute import Attribute as EdgeAttribute
from openapi_server.models.edge import Edge
from openapi_server.models.q_edge import QEdge
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../reasoningtool/kg-construction/")
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from Overlay.predictor.predictor import predictor
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../NodeSynonymizer/")
from node_synonymizer import NodeSynonymizer
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import overlay_utilities as ou

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../")
from RTXConfiguration import RTXConfiguration
RTXConfig = RTXConfiguration()
RTXConfig.live = "Production"

class PredictDrugTreatsDisease:

    #### Constructor
    def __init__(self, response, message, parameters):
        self.response = response
        self.message = message
        self.parameters = parameters
        self.global_iter = 0
        ## check if the new model files exists in /predictor/retrain_data. If not, scp it from arax.ncats.io
        pathlist = os.path.realpath(__file__).split(os.path.sep)
        RTXindex = pathlist.index("RTX")
        filepath = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'KnowledgeSources', 'Prediction'])

        ## check if there is LogModel.pkl
        log_model_name = RTXConfig.log_model_path.split("/")[-1]
        pkl_file = f"{filepath}{os.path.sep}{log_model_name}"
        if os.path.exists(pkl_file):
            pass
        else:
            #os.system("scp rtxconfig@arax.ncats.io:/data/orangeboard/databases/KG2.3.4/LogModel.pkl " + pkl_file)
            os.system(f"scp {RTXConfig.log_model_username}@{RTXConfig.log_model_host}:{RTXConfig.log_model_path} {pkl_file}")


        ## check if there is GRAPH.sqlite
        graph_database_name = RTXConfig.graph_database_path.split("/")[-1]
        db_file = f"{filepath}{os.path.sep}{graph_database_name}"
        if os.path.exists(db_file):
            pass
        else:
            #os.system("scp rtxconfig@arax.ncats.io:/data/orangeboard/databases/KG2.3.4/GRAPH.sqlite " + db_file)
            os.system(f"scp {RTXConfig.graph_database_username}@{RTXConfig.graph_database_host}:{RTXConfig.graph_database_path} {db_file}")

        ## check if there is DTD_probability_database.db
        DTD_prob_db_file = f"{filepath}{os.path.sep}{RTXConfig.dtd_prob_path.split('/')[-1]}"
        if os.path.exists(DTD_prob_db_file):
            pass
        else:
            #os.system("scp rtxconfig@arax.ncats.io:/data/orangeboard/databases/KG2.3.4/DTD_probability_database_v1.0.db " + DTD_prob_db_file)
            os.system(f"scp {RTXConfig.dtd_prob_username}@{RTXConfig.dtd_prob_host}:{RTXConfig.dtd_prob_path} {DTD_prob_db_file}")

        # use NodeSynonymizer to replace map.txt
        # check if there is map.txt
        # map_file = f"{filepath}/map.txt"
        # if os.path.exists(map_file):
        #     pass
        # else:
        #     os.system("scp rtxconfig@arax.ncats.io:/home/ubuntu/drug_repurposing_model_retrain/map.txt " + map_file)

        self.use_prob_db = True
        if self.use_prob_db is True:
            try:
                self.pred = predictor(DTD_prob_file=DTD_prob_db_file, use_prob_db=True)
            except:
                tb = traceback.format_exc()
                error_type, error, _ = sys.exc_info()
                self.response.error(tb, error_code=error_type.__name__)
                self.response.error(f"Internal Error encountered connecting to the local DTD prediction database.")
        else:
            try:
                self.pred = predictor(model_file=pkl_file, use_prob_db=False)
            except:
                tb = traceback.format_exc()
                error_type, error, _ = sys.exc_info()
                self.response.error(tb, error_code=error_type.__name__)
                self.response.error(f"Internal Error encountered connecting to the local LogModel.pkl file.")
            try:
                self.pred.import_file(None, graph_database=db_file)
            except:
                tb = traceback.format_exc()
                error_type, error, _ = sys.exc_info()
                self.response.error(tb, error_code=error_type.__name__)
                self.response.error(f"Internal Error encountered connecting to the local graph database file.")
        # with open(map_file, 'r') as infile:
        #     map_file_content = infile.readlines()
        #     map_file_content.pop(0) ## remove title
        #     self.known_curies = set(line.strip().split('\t')[0] for line in map_file_content)

        self.synonymizer = NodeSynonymizer()

    def convert_to_trained_curies(self, input_curie):
        """
        Takes an input curie from the KG, uses the synonymizer, and then returns something that the map.csv can handle
        """
        normalizer_result = self.synonymizer.get_canonical_curies(input_curie)
        curies_in_model = normalizer_result[input_curie]
        # curies_in_model = [curie for curie in curies_in_model if curie in self.known_curies]
        # equivalent_curies = []  # start with empty equivalent_curies
        # try:
        #     equivalent_curies = [x['identifier'] for x in normalizer_result[input_curie]['equivalent_identifiers']]
        # except:
        #     self.response.warning(f"NodeSynonmizer could not find curies for {input_curie}, skipping this one.")
        # for curie in equivalent_curies:
        #     curie_prefix = curie.split(':')[0]
        #     # FIXME: fix this when re-training the ML model, as when this was originally trained, it was ChEMBL:123, not CHEMBL.COMPOUND:CHEMBL123
        #     if curie_prefix == "CHEMBL.COMPOUND":
        #         chembl_fix = 'ChEMBL:' + curie[22:]
        #         if chembl_fix in self.known_curies:
        #             curies_in_model.add(chembl_fix)
        #     elif curie in self.known_curies:
        #         curies_in_model.add(curie)
        return curies_in_model

    def predict_drug_treats_disease(self):
        """
        Iterate over all the edges in the knowledge graph, add the drug-disease treatment probability for appropriate edges
        on the edge_attributes
        :return: response
        """
        parameters = self.parameters
        self.response.debug(f"Computing drug disease treatment probability based on a machine learning model")
        self.response.info(f"Computing drug disease treatment probability based on a machine learning model: See [this publication](https://doi.org/10.1101/765305) for more details about how this is accomplished.")

        attribute_name = "probability_treats"
        attribute_type = "EDAM:data_0951"
        value = 0  # this will be the default value. If the model returns 0, or the default is there, don't include that edge
        url = "https://doi.org/10.1101/765305"

        # if you want to add virtual edges, identify the source/targets, decorate the edges, add them to the KG, and then add one to the QG corresponding to them
        if 'virtual_relation_label' in parameters:
            source_curies_to_decorate = set()
            target_curies_to_decorate = set()
            curie_to_name = dict()
            # identify the nodes that we should be adding virtual edges for
            for node_key, node in self.message.knowledge_graph.nodes.items():
                if hasattr(node, 'qnode_keys'):
                    if parameters['subject_qnode_key'] in node.qnode_keys:
                        if "drug" in node.category or "chemical_substance" in node.category or "biolink:Drug" in node.category or "biolink:ChemicalSubstance" in node.category:  # this is now NOT checked by ARAX_overlay
                            source_curies_to_decorate.add(node_key)
                            curie_to_name[node_key] = node.name
                    if parameters['object_qnode_key'] in node.qnode_keys:
                        if "disease" in node.category or "phenotypic_feature" in node.category or "biolink:Disease" in node.category or "biolink:PhenotypicFeature" in node.category:  # this is now NOT checked by ARAX_overlay
                            target_curies_to_decorate.add(node_key)
                            curie_to_name[node_key] = node.name

            added_flag = False  # check to see if any edges where added
            # iterate over all pairs of these nodes, add the virtual edge, decorate with the correct attribute

            for (source_curie, target_curie) in itertools.product(source_curies_to_decorate, target_curies_to_decorate):
                self.response.debug(f"Predicting probability that {curie_to_name[source_curie]} treats {curie_to_name[target_curie]}")
                # create the edge attribute if it can be
                # loop over all equivalent curies and take the highest probability

                max_probability = 0
                converted_source_curie = self.convert_to_trained_curies(source_curie)
                if converted_source_curie is None:
                    continue
                else:
                    preferred_type = converted_source_curie['preferred_type']
                    if preferred_type == "drug" or preferred_type == "chemical_substance" or preferred_type == "biolink:Drug" or preferred_type == "biolink:ChemicalSubstance":
                        converted_source_curie = converted_source_curie['preferred_curie']
                    else:
                        continue
                converted_target_curie = self.convert_to_trained_curies(target_curie)
                if converted_target_curie is None:
                    continue
                else:
                    preferred_type = converted_target_curie['preferred_type']
                    if preferred_type == "disease" or preferred_type == "phenotypic_feature" or preferred_type == "biolink:Disease" or preferred_type == "biolink:PhenotypicFeature":
                        converted_target_curie = converted_target_curie['preferred_curie']
                    else:
                        continue
                if self.use_prob_db is True:
                    probability = self.pred.get_prob_from_DTD_db(converted_source_curie, converted_target_curie)
                    if probability is not None:
                        if np.isfinite(probability):
                            max_probability = probability
                else:
                    probability = self.pred.prob_single(converted_source_curie, converted_target_curie)
                    if probability is not None:
                        probability = probability[0]
                        if np.isfinite(probability):
                            max_probability = probability
                # if len(res) != 0:
                #     all_probabilities = self.pred.prob_all(res)
                #     if isinstance(all_probabilities, list):
                #         max_probability = max([value for value in all_probabilities if np.isfinite(value)])

                value = max_probability

                #probability = self.pred.prob_single('ChEMBL:' + source_curie[22:], target_curie)  # FIXME: when this was trained, it was ChEMBL:123, not CHEMBL.COMPOUND:CHEMBL123
                #if probability and np.isfinite(probability):  # finite, that's ok, otherwise, stay with default
                #    value = probability[0]
                edge_attribute = EdgeAttribute(type=attribute_type, name=attribute_name, value=str(value), url=url)  # populate the edge attribute
                if edge_attribute and value != 0:
                    added_flag = True
                    # make the edge, add the attribute

                    # edge properties
                    now = datetime.now()
                    edge_type = "biolink:probably_treats"
                    qedge_keys = [parameters['virtual_relation_label']]
                    relation = parameters['virtual_relation_label']
                    is_defined_by = "ARAX"
                    defined_datetime = now.strftime("%Y-%m-%d %H:%M:%S")
                    provided_by = "ARAX"
                    confidence = None
                    weight = None  # TODO: could make the actual value of the attribute
                    subject_key = source_curie
                    object_key = target_curie

                    # now actually add the virtual edges in
                    id = f"{relation}_{self.global_iter}"
                    self.global_iter += 1
                    edge_attribute_list = [
                        edge_attribute,
                        EdgeAttribute(name="is_defined_by", value=is_defined_by, type="ARAX_TYPE_PLACEHOLDER"),
                        EdgeAttribute(name="defined_datetime", value=defined_datetime, type="metatype:Datetime"),
                        EdgeAttribute(name="provided_by", value=provided_by, type="biolink:provided_by"),
                        #EdgeAttribute(name="confidence", value=confidence, type="biolink:ConfidenceLevel"),
                        #EdgeAttribute(name="weight", value=weight, type="metatype:Float")
                    ]
                    edge = Edge(predicate=edge_type, subject=subject_key, object=object_key, relation=relation,
                                attributes=edge_attribute_list)
                    edge.qedge_keys = qedge_keys
                    self.message.knowledge_graph.edges[id] = edge

            # Now add a q_edge the query_graph since I've added an extra edge to the KG
            if added_flag:
                edge_type = "biolink:probably_treats"
                relation = parameters['virtual_relation_label']
                subject_qnode_key = parameters['subject_qnode_key']
                object_qnode_key = parameters['object_qnode_key']
                option_group_id = ou.determine_virtual_qedge_option_group(subject_qnode_key, object_qnode_key, self.message.query_graph, self.response)
                q_edge = QEdge(predicate=edge_type, relation=relation, subject=subject_qnode_key, object=object_qnode_key, option_group_id=option_group_id)
                self.message.query_graph.edges[relation] = q_edge
            return self.response

        else:  # you want to add it for each edge in the KG
            # iterate over KG edges, add the information
            try:
                # map curies to types
                curie_to_type = dict()
                curie_to_name = dict()
                for node_key, node in self.message.knowledge_graph.nodes.items():
                    curie_to_type[node_key] = node.category
                    curie_to_name[node_key] = node.name
                # then iterate over the edges and decorate if appropriate
                for edge_key, edge in self.message.knowledge_graph.edges.items():
                    # Make sure the edge_attributes are not None
                    if not edge.attributes:
                        edge.attributes = []  # should be an array, but why not a list?
                    # now go and actually get the probability
                    source_curie = edge.subject
                    target_curie = edge.object
                    source_types = curie_to_type[source_curie]
                    target_types = curie_to_type[target_curie]
                    if (("drug" in source_types) or ("chemical_substance" in source_types) or ("biolink:Drug" in source_types) or ("biolink:ChemicalSubstance" in source_types)) and (("disease" in target_types) or ("phenotypic_feature" in target_types) or ("biolink:Disease" in target_types) or ("biolink:PhenotypicFeature" in target_types)):
                        # loop over all pairs of equivalent curies and take the highest probability
                        self.response.debug(f"Predicting treatment probability between {curie_to_name[source_curie]} and {curie_to_name[target_curie]}")
                        max_probability = 0
                        converted_source_curie = self.convert_to_trained_curies(source_curie)
                        if converted_source_curie is None:
                            continue
                        else:
                            preferred_type = converted_source_curie['preferred_type']
                            if preferred_type == "drug" or preferred_type == "chemical_substance" or preferred_type == "biolink:Drug" or preferred_type == "biolink:ChemicalSubstance":
                                converted_source_curie = converted_source_curie['preferred_curie']
                            else:
                                continue
                        converted_target_curie = self.convert_to_trained_curies(target_curie)
                        if converted_target_curie is None:
                            continue
                        else:
                            preferred_type = converted_target_curie['preferred_type']
                            if preferred_type == "disease" or preferred_type == "phenotypic_feature" or preferred_type == "biolink:Disease" or preferred_type == "biolink:PhenotypicFeature":
                                converted_target_curie = converted_target_curie['preferred_curie']
                            else:
                                continue
                        if self.use_prob_db is True:
                            probability = self.pred.get_prob_from_DTD_db(converted_source_curie, converted_target_curie)
                            if probability is not None:
                                if np.isfinite(probability):
                                    max_probability = probability
                        else:
                            probability = self.pred.prob_single(converted_source_curie, converted_target_curie)
                            if probability is not None:
                                probability = probability[0]
                                if np.isfinite(probability):
                                    max_probability = probability
                        # res = list(itertools.product(converted_source_curie, converted_target_curie))
                        # if len(res) != 0:
                        #     all_probabilities = self.pred.prob_all(res)
                        #     if isinstance(all_probabilities, list):
                        #         max_probability = max([value for value in all_probabilities if np.isfinite(value)])

                        value = max_probability

                        #probability = self.pred.prob_single('ChEMBL:' + source_curie[22:], target_curie)  # FIXME: when this was trained, it was ChEMBL:123, not CHEMBL.COMPOUND:CHEMBL123
                        #if probability and np.isfinite(probability):  # finite, that's ok, otherwise, stay with default
                        #    value = probability[0]
                    elif (("drug" in target_types) or ("chemical_substance" in target_types) or ("biolink:Drug" in target_types) or ("biolink:ChemicalSubstance" in target_types)) and (("disease" in source_types) or ("phenotypic_feature" in source_types) or ("biolink:Disease" in source_types) or ("biolink:PhenotypicFeature" in source_types)):
                        #probability = self.pred.prob_single('ChEMBL:' + target_curie[22:], source_curie)  # FIXME: when this was trained, it was ChEMBL:123, not CHEMBL.COMPOUND:CHEMBL123
                        #if probability and np.isfinite(probability):  # finite, that's ok, otherwise, stay with default
                        #    value = probability[0]
                        self.response.debug(f"Predicting treatment probability between {curie_to_name[source_curie]} and {curie_to_name[target_curie]}")
                        max_probability = 0
                        converted_source_curie = self.convert_to_trained_curies(source_curie)
                        if converted_source_curie is None:
                            continue
                        else:
                            preferred_type = converted_source_curie['preferred_type']
                            if preferred_type == "disease" or preferred_type == "phenotypic_feature" or preferred_type == "biolink:Disease" or preferred_type == "biolink:PhenotypicFeature":
                                converted_source_curie = converted_source_curie['preferred_curie']
                            else:
                                continue
                        converted_target_curie = self.convert_to_trained_curies(target_curie)
                        if converted_target_curie is None:
                            continue
                        else:
                            preferred_type = converted_target_curie['preferred_type']
                            if preferred_type == "drug" or preferred_type == "chemical_substance" or preferred_type == "biolink:Drug" or preferred_type == "biolink:ChemicalSubstance":
                                converted_target_curie = converted_target_curie['preferred_curie']
                            else:
                                continue

                        if self.use_prob_db is True:
                            probability = self.pred.get_prob_from_DTD_db(converted_target_curie, converted_source_curie)
                            if probability is not None:
                                if np.isfinite(probability):
                                    max_probability = probability
                        else:
                            probability = self.pred.prob_single(converted_target_curie, converted_source_curie)
                            if probability is not None:
                                probability = probability[0]
                                if np.isfinite(probability):
                                    max_probability = probability
                        # res = list(itertools.product(converted_target_curie, converted_source_curie))
                        # if len(res) != 0:
                        #     all_probabilities = self.pred.prob_all(res)
                        #     if isinstance(all_probabilities, list):
                        #         max_probability = max([value for value in all_probabilities if np.isfinite(value)])

                        value = max_probability

                    else:
                        continue
                    if value != 0:
                        edge_attribute = EdgeAttribute(type=attribute_type, name=attribute_name, value=str(value), url=url)  # populate the attribute
                        edge.attributes.append(edge_attribute)  # append it to the list of attributes
            except:
                tb = traceback.format_exc()
                error_type, error, _ = sys.exc_info()
                self.response.error(tb, error_code=error_type.__name__)
                self.response.error(f"Something went wrong adding the drug disease treatment probability")
            else:
                self.response.info(f"Drug disease treatment probability successfully added to edges")

            return self.response
