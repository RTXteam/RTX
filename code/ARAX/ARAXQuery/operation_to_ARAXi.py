# This will be a translation table between the Operations JSON spec (https://github.com/NCATSTranslator/OperationsAndWorkflows/) and ARAXi
import json
import itertools

class WorkflowToARAXi:
    def __init__(self):
        self.implemented = {'lookup',
                            'overlay_compute_ngd',
                            'overlay_compute_jaccard',
                            'overlay_fisher_exact_test',
                            'overlay_connect_knodes',
                            'filter_results_top_n',
                            'bind',
                            'fill',
                            'filter_kgraph_orphans',
                            'filter_kgraph_top_n',
                            'filter_kgraph_std_dev',
                            'filter_kgraph_percentile',
                            'filter_kgraph_discrete_kedge_attribute',
                            'filter_kgraph_continuous_attribute',
                            'sort_results_score',
                            'sort_results_edge_attribute',
                            'sort_results_node_attribute',
                            'annotate_nodes',
                            'score',
                            'complete_results'}

    # NGD
    @staticmethod
    def __translate_overlay_compute_ngd(parameters, query_graph, response):
        if ("virtual_relation_label" not in parameters) or ("qnode_keys" not in parameters):
            response.error("The operation overlay_compute_ngd must have the parameters virtual_relation_label and qnode_keys", error_code="KeyError")
        ARAXi = []
        # loop over all pairs of qnode keys and write the ARAXi
        for source, target in itertools.combinations(parameters["qnode_keys"], 2):
            # TODO: make is so ARAX properly handles -1 as the default value (in ranker)
            ARAXi.append(f"overlay(action=compute_ngd,default_value=inf,virtual_relation_label={parameters['virtual_relation_label']},subject_qnode_key={source},object_qnode_key={target})")
        return ARAXi

    @staticmethod
    def __translate_overlay_connect_knodes(parameters, query_graph, response):
        ARAXi = []
        if len(query['query_graph']) >= 3:
            response.warning("This query graph has 3 or more nodes. This may take a while")
        qnode_pairs = itertools.combinations(query_graph['nodes'].keys(),2)
        for qnode_pair in qnode_pairs:
            ARAXi.append(f"overlay(action=compute_ngd,default_value=inf,virtual_relation_label=connect_knodes_ngd,subject_qnode_key={qnode_pair[0]},object_qnode_key={qnode_pair[1]})")
            ARAXi.append(f"overlay(action=overlay_clinical_info,COHD_method=paired_concept_frequency,virtual_relation_label=connect_knodes_pair_frq,subject_qnode_key={qnode_pair[0]},object_qnode_key={qnode_pair[1]})")
            ARAXi.append(f"overlay(action=overlay_clinical_info,COHD_method=observed_expected_ratio,virtual_relation_label=connect_knodes_obs_exp,subject_qnode_key={qnode_pair[0]},object_qnode_key={qnode_pair[1]})")
            ARAXi.append(f"overlay(action=overlay_clinical_info,COHD_method=chi_square,virtual_relation_label=connect_knodes_chi_sqr,subject_qnode_key={qnode_pair[0]},object_qnode_key={qnode_pair[1]})")
            ARAXi.append(f"overlay(action=predict_drug_treats_disease,subject_qnode_key={qnode_pair[0]},object_qnode_key={qnode_pair[1]})")
            ARAXi.append(f"overlay(action=fisher_exact_test,virtual_relation_label=connect_knodes_fisher,subject_qnode_key={qnode_pair[0]},object_qnode_key={qnode_pair[1]})")
            ARAXi.append(f"overlay(action=fisher_exact_test,virtual_relation_label=connect_knodes_fisher,subject_qnode_key={qnode_pair[1]},object_qnode_key={qnode_pair[0]})")
        if len(query_graph['nodes']) >= 3:
            qnode_triples = itertools.combinations(query_graph['nodes'].keys(),3)
            for qnode_triple in qnode_triples:
                ARAXi.append(f"overlay(action=compute_jaccard,virtual_relation_label=connect_knodes_jaccard,start_node_key={qnode_triple[0]},end_node_key={qnode_triple[1]},intermediate_node_key={qnode_triple[2]})")
                ARAXi.append(f"overlay(action=compute_jaccard,virtual_relation_label=connect_knodes_jaccard,start_node_key={qnode_triple[2]},end_node_key={qnode_triple[0]},intermediate_node_key={qnode_triple[1]})")
                ARAXi.append(f"overlay(action=compute_jaccard,virtual_relation_label=connect_knodes_jaccard,start_node_key={qnode_triple[1]},end_node_key={qnode_triple[2]},intermediate_node_key={qnode_triple[0]})")
        return ARAXi

    @staticmethod
    def __translate_overlay_compute_jaccard(parameters, query_graph, response):
        if ("virtual_relation_label" not in parameters) or ("end_node_keys" not in parameters) or ("intermediate_node_key" not in parameters):
            response.error("The operation overlay_compute_jaccard must have the parameters virtual_relation_label, end_node_keys, and intermediate_node_key", error_code="KeyError")
        ARAXi = []
        source = parameters['end_node_keys'][0]
        target = parameters['end_node_keys'][1]
        ARAXi.append(f"overlay(action=compute_jaccard,virtual_relation_label={parameters['virtual_relation_label']},start_node_key={source},end_node_key={target},intermediate_node_key={parameters['intermediate_node_key']})")
        return ARAXi

    @staticmethod
    def __translate_overlay_fisher_exact_test(parameters, query_graph, response):
        if ("virtual_relation_label" not in parameters) or ("subject_qnode_key" not in parameters) or ("object_qnode_key" not in parameters):
            response.error("The operation overlay_fisher_exact_test must have the parameters virtual_relation_label, subject_qnode_key, and object_qnode_key", error_code="KeyError")
        ARAXi = []
        if 'rel_edge_key' not in parameters:
            ARAXi.append(f"overlay(action=fisher_exact_test,virtual_relation_label={parameters['virtual_relation_label']},subject_qnode_key={parameters['subject_qnode_key']},object_qnode_key={parameters['object_qnode_key']})")
        else:
            ARAXi.append(f"overlay(action=fisher_exact_test,virtual_relation_label={parameters['virtual_relation_label']},subject_qnode_key={parameters['subject_qnode_key']},object_qnode_key={parameters['object_qnode_key']},rel_edge_key={parameters['rel_edge_key']})")
        return ARAXi

    @staticmethod
    def __translate_filter_results_top_n(parameters, query_graph, response):
        if 'max_results' not in parameters:
            response.error("The operation filter_results_top_n must have the parameter max_results", error_code="KeyError")
        assert type(parameters['max_results']) == int
        ARAXi = []
        ARAXi.append(f"filter_results(action=limit_number_of_results,max_results={parameters['max_results']},prune_kg=true)")  # prune the kg
        return ARAXi

    @staticmethod
    def __translate_bind(parameters, query_graph, response):
        ARAXi = []
        ARAXi.append(f"scoreless_resultify(ignore_edge_direction=true)")  # ignore edge directions
        return ARAXi

    @staticmethod
    def __translate_fill(parameters, query_graph, response):
        if 'denylist' in parameters:
            response.error("ARAX has not implementer the parameter denylist", error_code="NotImplementedError")
        ARAXi = []
        if 'allowlist' in parameters:
            for KP_name in parameters['allowlist']:
                # continue if no results, don't enforce directionality, and use synonyms
                ARAXi.append(f"expand(kp={KP_name})")
        else:
            ARAXi.append("expand()")
        return ARAXi

    @staticmethod
    def __translate_filter_kgraph_orphans(parameters, query_graph, response):
        ARAXi = []
        ARAXi.append(f"filter_kg(action=remove_orphaned_nodes)")
        return ARAXi

    @staticmethod
    def __translate_filter_kgraph_top_n(parameters, query_graph, response):
        if ("edge_attribute" not in parameters):
            response.error("The operation filter_kgraph_top_n must have the parameter edge_attribute", error_code="KeyError")
        ARAXi = []
        threshold = parameters.get('max_edges',50)
        top = parameters.get('keep_top_or_bottom','top')
        if top == 'top':
            direction = 'below'
        else:
            direction = 'above'
        # FW: need to update this to handle qedge_keys and qnode_keys
        araxi_string = f"filter_kg(action=remove_edges_by_top_n,edge_attribute={parameters['edge_attribute']},n={threshold},direction={direction},top={top == 'top'}"
        if "qnode_keys" in parameters:
            araxi_string += f",remove_connected_nodes=t,qnode_keys={parameters['qnode_keys']}"
        if "qedge_keys" in parameters:
            araxi_string += f",qedge_keys={parameters['qedge_keys']}"
        araxi_string += ")"
        ARAXi.append(araxi_string)
        return ARAXi

    @staticmethod
    def __translate_filter_kgraph_std_dev(parameters, query_graph, response):
        if ("edge_attribute" not in parameters):
            response.error("The operation filter_kgraph_std_dev must have the parameter edge_attribute", error_code="KeyError")
        ARAXi = []
        threshold = parameters.get('threshold',1)
        direction = parameters.get('remove_above_or_below','below')
        top = parameters.get('keep_top_or_bottom','top')
        # FW: need to update this to handle qedge_keys and qnode_keys
        araxi_string = f"filter_kg(action=remove_edges_by_std_dev,edge_attribute={parameters['edge_attribute']},threshold={threshold},direction={direction},top={top == 'top'}"
        if "qnode_keys" in parameters:
            araxi_string += f",remove_connected_nodes=t,qnode_keys={parameters['qnode_keys']}"
        if "qedge_keys" in parameters:
            araxi_string += f",qedge_keys={parameters['qedge_keys']}"
        araxi_string += ")"
        ARAXi.append(araxi_string)
        return ARAXi

    @staticmethod
    def __translate_filter_kgraph_percentile(parameters, query_graph, response):
        if ("edge_attribute" not in parameters):
            response.error("The operation filter_kgraph_percentile must have the parameter edge_attribute", error_code="KeyError")
        ARAXi = []
        threshold = parameters.get('threshold',95)
        direction = parameters.get('remove_above_or_below','below')
        # FW: need to update this to handle qedge_keys and qnode_keys
        araxi_string = f"filter_kg(action=remove_edges_by_percentile,edge_attribute={parameters['edge_attribute']},threshold={threshold},direction={direction}"
        if "qnode_keys" in parameters:
            araxi_string += f",remove_connected_nodes=t,qnode_keys={parameters['qnode_keys']}"
        if "qedge_keys" in parameters:
            araxi_string += f",qedge_keys={parameters['qedge_keys']}"
        araxi_string += ")"
        ARAXi.append(araxi_string)
        return ARAXi

    @staticmethod
    def __translate_filter_kgraph_continuous_attribute(parameters, query_graph, response):
        if ("edge_attribute" not in parameters) or ("threshold" not in parameters) or ("remove_above_or_below" not in parameters):
            response.error("The operation kgraph_continuous_attribute must have the parameters edge_attribute, threshold, and remove_above_or_below", error_code="KeyError")
        ARAXi = []
        threshold = parameters.get('threshold',None)
        direction = parameters.get('remove_above_or_below',None)
        # FW: need to update this to handle qedge_keys and qnode_keys
        araxi_string = f"filter_kg(action=remove_edges_by_continuous_attribute,edge_attribute={parameters['edge_attribute']},threshold={threshold},direction={direction}"
        if "qnode_keys" in parameters:
            araxi_string += f",remove_connected_nodes=t,qnode_keys={parameters['qnode_keys']}"
        if "qedge_keys" in parameters:
            araxi_string += f",qedge_keys={parameters['qedge_keys']}"
        araxi_string += ")"
        ARAXi.append(araxi_string)
        return ARAXi

    @staticmethod
    def __translate_filter_kgraph_discrete_kedge_attribute(parameters, query_graph, response):
        if ("edge_attribute" not in parameters) or ("remove_value" not in parameters):
            response.error("The operation kgraph_continuous_attribute must have the parameters edge_attribute and remove_value", error_code="KeyError")
        ARAXi = []
        value = parameters.get('remove_value',None)
        # FW: need to update this to handle qedge_keys and qnode_keys
        araxi_string = f"filter_kg(action=remove_edges_by_discrete_attribute,edge_attribute={parameters['edge_attribute']},value={value}"
        if "qnode_keys" in parameters:
            araxi_string += f",remove_connected_nodes=t,qnode_keys={parameters['qnode_keys']}"
        if "qedge_keys" in parameters:
            araxi_string += f",qedge_keys={parameters['qedge_keys']}"
        araxi_string += ")"
        ARAXi.append(araxi_string)
        return ARAXi

    @staticmethod
    def __translate_sort_results_edge_attribute(parameters, query_graph, response):
        if ("edge_attribute" not in parameters) or ("ascending_or_descending" not in parameters):
            response.error("The operation sort_results_edge_attribute must have the parameters edge_attribute and ascending_or_descending", error_code="KeyError")
        ARAXi = []
        # FW: need to update this to handle qedge_keys and qnode_keys
        araxi_string = f"filter_results(action=sort_by_edge_attribute,edge_attribute={parameters['edge_attribute']},direction={ascending_or_descending}"
        if "qedge_keys" in parameters and parameters['qedge_keys'] is not None:
            araxi_string += f",qedge_keys={parameters['qedge_keys']}"
        araxi_string += ")"
        ARAXi.append(araxi_string)
        return ARAXi

    @staticmethod
    def __translate_sort_results_node_attribute(parameters, query_graph, response):
        if ("node_attribute" not in parameters) or ("ascending_or_descending" not in parameters):
            response.error("The operation sort_results_node_attribute must have the parameters node_attribute and ascending_or_descending", error_code="KeyError")
        ARAXi = []
        # FW: need to update this to handle qedge_keys and qnode_keys
        araxi_string = f"filter_results(action=sort_by_node_attribute,node_attribute={parameters['node_attribute']},direction={ascending_or_descending}"
        if "qnode_keys" in parameters and parameters['qnode_keys'] is not None:
            araxi_string += f",remove_connected_nodes=t,qnode_keys={parameters['qnode_keys']}"
        araxi_string += ")"
        ARAXi.append(araxi_string)
        return ARAXi

    @staticmethod
    def __translate_sort_results_score(parameters, query_graph, response):
        if ("ascending_or_descending" not in parameters):
            response.error("The operation sort_results_score must have the parameter ascending_or_descending", error_code="KeyError")
        ARAXi = []
        araxi_string = f"filter_results(action=sort_by_score,direction={ascending_or_descending}"
        araxi_string += ")"
        ARAXi.append(araxi_string)
        return ARAXi

    @staticmethod
    def __translate_annotate_nodes(parameters, query_graph, response):
        ARAXi = []
        attributes = parameters.get('attributes',None)
        if attributes is None or 'pmids' in attributes:
            araxi_string = f"overlay(action=add_node_pmids)"
            ARAXi.append(araxi_string)
        return ARAXi

    def translate(self, workflow, query_graph, response):
        ARAXi = []
        for operation in workflow:
            if operation['id'] not in self.implemented:
                response.error("This operation has not yet been implemented to the workflow to ARAXi translator", error_code="NotImplementedError")
            if 'parameters' in operation:
                ARAXi.extend(getattr(self, '_' + self.__class__.__name__ + '__translate_' + operation['id'])(operation['parameters'], query_graph, response))
            else:
                ARAXi.extend(getattr(self, '_' + self.__class__.__name__ + '__translate_' + operation['id'])({}, query_graph, response))
        return ARAXi

    @staticmethod
    def __translate_score(parameters, query_graph, response):
        ARAXi = []
        ARAXi.append(f"rank_results()")
        return ARAXi

    @staticmethod
    def __translate_complete_results(parameters, query_graph, response):
        ARAXi = []
        ARAXi.append(f"scoreless_resultify(ignore_edge_direction=true)")  # ignore edge directions
        return ARAXi

    @staticmethod
    def __translate_lookup(parameters, query_graph, response):
        ARAXi = []
        ARAXi.append("expand()")
        ARAXi.append(f"scoreless_resultify(ignore_edge_direction=true)")  # ignore edge directions
        return ARAXi



def main():
    trapi_eg = """{
        "query_graph": {
            "nodes": {
                "type-2 diabetes": {
                    "id": "MONDO:0005148"
                },
                "drug": {
                    "category": "biolink:ChemicalSubstance"
                }
            },
            "edges": {
                "treats": {
                    "subject": "drug",
                    "predicate": "biolink:treats",
                    "object": "type-2 diabetes"
                }
            }
        },
        "knowledge_graph": {
            "nodes": {
                "MONDO:0005148": {"name": "type-2 diabetes"},
                "CHEBI:6801": {
                    "name": "metformin",
                    "category": "biolink:ChemicalSubstance"
                },
                "CHEBI:5441": {
                    "name": "glyburide",
                    "category": "biolink:ChemicalSubstance"
                }
            },
            "edges": {
                "df87ff82": {
                    "subject": "CHEBI:6801",
                    "predicate": "biolink:treats",
                    "object": "MONDO:0005148"
                },
                "5133c100": {
                    "subject": "CHEBI:5441",
                    "predicate": "biolink:treats",
                    "object": "MONDO:0005148"
                }
            }
        },
        "results": [
            {
                "node_bindings": {
                    "type-2 diabetes": [{"id": "MONDO:0005148"}],
                    "drug": [{"id": "CHEBI:6801"}]
                },
                "edge_bindings": {
                    "treats": [{"id": "df87ff82"}]
                }
            }
        ],
        "workflow": [
          {
            "id": "overlay_compute_ngd",
            "parameters": {
                "virtual_relation_label": "ngd1",
                "qnode_keys": ["drug", "type-2 diabetes"]
            }
          },
          {
            "id": "filter_results_top_n",
            "parameters": {
                "max_results": 12
            }
          }
        ]
    }"""

    test_trapi = json.loads(trapi_eg)
    print(f"Workflow: {test_trapi['workflow']}")
    W = WorkflowToARAXi()
    print(f"ARAXi: {W.translate(test_trapi['workflow'])}")

if __name__ == "__main__": main()
