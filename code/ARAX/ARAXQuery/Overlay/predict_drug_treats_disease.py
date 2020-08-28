import sys
import os
import traceback
import numpy as np
import itertools
from datetime import datetime

# relative imports
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../OpenAPI/python-flask-server/")
from swagger_server.models.edge_attribute import EdgeAttribute
from swagger_server.models.edge import Edge
from swagger_server.models.q_edge import QEdge
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../reasoningtool/kg-construction/")
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from Overlay.predictor.predictor import predictor
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../NodeSynonymizer/")
from node_synonymizer import NodeSynonymizer

class PredictDrugTreatsDisease:

    #### Constructor
    def __init__(self, response, message, parameters):
        self.response = response
        self.message = message
        self.parameters = parameters
        self.global_iter = 0
        ## check if the new model files exists in /predictor/retrain_data. If not, scp it from arax.rtx.ai
        pathlist = os.path.realpath(__file__).split(os.path.sep)
        RTXindex = pathlist.index("RTX")
        filepath = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'ARAXQuery', 'Overlay', 'predictor','retrain_data'])

        ## check if there is LogModel.pkl
        pkl_file = f"{filepath}/LogModel.pkl"
        if os.path.exists(pkl_file):
            pass
        else:
            os.system("scp rtxconfig@arax.rtx.ai:/home/ubuntu/drug_repurposing_model_retrain/LogModel.pkl " + pkl_file)

        ## check if there is GRAPH.sqlite
        db_file = f"{filepath}/GRAPH.sqlite"
        if os.path.exists(db_file):
            pass
        else:
            os.system("scp rtxconfig@arax.rtx.ai:/home/ubuntu/drug_repurposing_model_retrain/GRAPH.sqlite " + db_file)

        # use NodeSynonymizer to replace map.txt
        # check if there is map.txt
        # map_file = f"{filepath}/map.txt"
        # if os.path.exists(map_file):
        #     pass
        # else:
        #     os.system("scp rtxconfig@arax.rtx.ai:/home/ubuntu/drug_repurposing_model_retrain/map.txt " + map_file)

        self.pred = predictor(model_file=pkl_file)
        self.pred.import_file(None, graph_database=db_file)
        # with open(map_file, 'r') as infile:
        #     map_file_content = infile.readlines()
        #     map_file_content.pop(0) ## remove title
        #     self.known_curies = set(line.strip().split('\t')[0] for line in map_file_content)

        self.synonymizer = NodeSynonymizer()

    def convert_to_trained_curies(self, input_curie):
        """
        Takes an input curie from the KG, uses the synonymizer, and then returns something that the map.csv can handle
        """
        normalizer_result = self.synonymizer.get_equivalent_nodes(input_curie, kg_name='KG2')
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
            # identify the nodes that we should be adding virtual edges for
            for node in self.message.knowledge_graph.nodes:
                if hasattr(node, 'qnode_ids'):
                    if parameters['source_qnode_id'] in node.qnode_ids:
                        if "drug" in node.type or "chemical_substance" in node.type:  # this is now NOT checked by ARAX_overlay
                            source_curies_to_decorate.add(node.id)
                    if parameters['target_qnode_id'] in node.qnode_ids:
                        if "disease" in node.type or "phenotypic_feature" in node.type:  # this is now NOT checked by ARAX_overlay
                            target_curies_to_decorate.add(node.id)

            added_flag = False  # check to see if any edges where added
            # iterate over all pairs of these nodes, add the virtual edge, decorate with the correct attribute

            for (source_curie, target_curie) in itertools.product(source_curies_to_decorate, target_curies_to_decorate):
                # create the edge attribute if it can be
                # loop over all equivalent curies and take the highest probability

                max_probability = 0
                converted_source_curie = self.convert_to_trained_curies(source_curie)
                converted_target_curie = self.convert_to_trained_curies(target_curie)
                if converted_source_curie is None or converted_target_curie is None:
                    continue
                res = list(itertools.product(converted_source_curie, converted_target_curie))
                if len(res) != 0:
                    all_probabilities = self.pred.prob_all(res)
                    if isinstance(all_probabilities, list):
                        max_probability = max([value for value in all_probabilities if np.isfinite(value)])

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
                    edge_type = "probably_treats"
                    qedge_ids = [parameters['virtual_relation_label']]
                    relation = parameters['virtual_relation_label']
                    is_defined_by = "ARAX"
                    defined_datetime = now.strftime("%Y-%m-%d %H:%M:%S")
                    provided_by = "ARAX"
                    confidence = None
                    weight = None  # TODO: could make the actual value of the attribute
                    source_id = source_curie
                    target_id = target_curie

                    # now actually add the virtual edges in
                    id = f"{relation}_{self.global_iter}"
                    self.global_iter += 1
                    edge = Edge(id=id, type=edge_type, relation=relation, source_id=source_id,
                                target_id=target_id,
                                is_defined_by=is_defined_by, defined_datetime=defined_datetime,
                                provided_by=provided_by,
                                confidence=confidence, weight=weight, edge_attributes=[edge_attribute], qedge_ids=qedge_ids)
                    self.message.knowledge_graph.edges.append(edge)

            # Now add a q_edge the query_graph since I've added an extra edge to the KG
            if added_flag:
                edge_type = "probably_treats"
                relation = parameters['virtual_relation_label']
                qedge_id = parameters['virtual_relation_label']
                q_edge = QEdge(id=relation, type=edge_type, relation=relation,
                               source_id=parameters['source_qnode_id'], target_id=parameters['target_qnode_id'])  # TODO: ok to make the id and type the same thing?
                self.message.query_graph.edges.append(q_edge)
            return self.response

        else:  # you want to add it for each edge in the KG
            # iterate over KG edges, add the information
            try:
                # map curies to types
                curie_to_type = dict()
                for node in self.message.knowledge_graph.nodes:
                    curie_to_type[node.id] = node.type
                # then iterate over the edges and decorate if appropriate
                for edge in self.message.knowledge_graph.edges:
                    # Make sure the edge_attributes are not None
                    if not edge.edge_attributes:
                        edge.edge_attributes = []  # should be an array, but why not a list?
                    # now go and actually get the NGD
                    source_curie = edge.source_id
                    target_curie = edge.target_id
                    source_types = curie_to_type[source_curie]
                    target_types = curie_to_type[target_curie]
                    if (("drug" in source_types) or ("chemical_substance" in source_types)) and (("disease" in target_types) or ("phenotypic_feature" in target_types)):
                        temp_value = 0
                        # loop over all pairs of equivalent curies and take the highest probability

                        max_probability = 0
                        converted_source_curie = self.convert_to_trained_curies(source_curie)
                        converted_target_curie = self.convert_to_trained_curies(target_curie)
                        if converted_source_curie is None or converted_target_curie is None:
                            continue
                        res = list(itertools.product(converted_source_curie, converted_target_curie))
                        if len(res) != 0:
                            all_probabilities = self.pred.prob_all(res)
                            if isinstance(all_probabilities, list):
                                max_probability = max([value for value in all_probabilities if np.isfinite(value)])

                        value = max_probability

                        #probability = self.pred.prob_single('ChEMBL:' + source_curie[22:], target_curie)  # FIXME: when this was trained, it was ChEMBL:123, not CHEMBL.COMPOUND:CHEMBL123
                        #if probability and np.isfinite(probability):  # finite, that's ok, otherwise, stay with default
                        #    value = probability[0]
                    elif (("drug" in target_types) or ("chemical_substance" in target_types)) and (("disease" in source_types) or ("phenotypic_feature" in source_types)):
                        #probability = self.pred.prob_single('ChEMBL:' + target_curie[22:], source_curie)  # FIXME: when this was trained, it was ChEMBL:123, not CHEMBL.COMPOUND:CHEMBL123
                        #if probability and np.isfinite(probability):  # finite, that's ok, otherwise, stay with default
                        #    value = probability[0]

                        max_probability = 0
                        converted_source_curie = self.convert_to_trained_curies(source_curie)
                        converted_target_curie = self.convert_to_trained_curies(target_curie)
                        if converted_source_curie is None or converted_target_curie is None:
                            continue
                        res = list(itertools.product(converted_target_curie, converted_source_curie))
                        if len(res) != 0:
                            all_probabilities = self.pred.prob_all(res)
                            if isinstance(all_probabilities, list):
                                max_probability = max([value for value in all_probabilities if np.isfinite(value)])

                        value = max_probability

                    else:
                        continue
                    if value != 0:
                        edge_attribute = EdgeAttribute(type=attribute_type, name=attribute_name, value=str(value), url=url)  # populate the attribute
                        edge.edge_attributes.append(edge_attribute)  # append it to the list of attributes
            except:
                tb = traceback.format_exc()
                error_type, error, _ = sys.exc_info()
                self.response.error(tb, error_code=error_type.__name__)
                self.response.error(f"Something went wrong adding the drug disease treatment probability")
            else:
                self.response.info(f"Drug disease treatment probability successfully added to edges")

            return self.response
