# This will be a translation table between the Operations JSON spec (https://github.com/NCATSTranslator/OperationsAndWorkflows/) and ARAXi
import json
import itertools

class WorkflowToARAXi:
    def __init__(self):
        self.implemented = {'overlay_compute_ngd',
                            'overlay_compute_jaccard',
                            'overlay_fisher_exact_test',
                            #'overlay_connect_knodes',
                            'filter_results_top_n',
                            'bind',
                            'fill',
                            'filter_kgraph_orphans',
                            'filter_kgraph_top_n',
                            'filter_kgraph_std_dev',
                            'filter_kgraph_percentile',
                            'filter_kgraph_discrete_kedge_attribute',
                            'filter_kgraph_continuous_attribute',
                            'score',
                            'complete_results'}

    # NGD
    @staticmethod
    def __translate_overlay_compute_ngd(parameters):
        if ("virtual_relation_label" not in parameters) or ("qnode_keys" not in parameters):
            raise KeyError
        ARAXi = []
        # loop over all pairs of qnode keys and write the ARAXi
        for source, target in itertools.combinations(parameters["qnode_keys"], 2):
            # TODO: make is so ARAX properly handles -1 as the default value (in ranker)
            ARAXi.append(f"overlay(action=compute_ngd,default_value=inf,virtual_relation_label={parameters['virtual_relation_label']},subject_qnode_key={source},object_qnode_key={target})")
        return ARAXi

    @staticmethod
    def __translate_overlay_connect_knodes(parameters):
        ARAXi = []
        ARAXi.append(f"overlay(action=compute_ngd,default_value=inf)")
        ARAXi.append(f"overlay(action=overlay_clinical_info,COHD_method=paired_concept_frequency)")
        ARAXi.append(f"overlay(action=overlay_clinical_info,COHD_method=observed_expected_ratio)")
        ARAXi.append(f"overlay(action=overlay_clinical_info,COHD_method=chi_square)")
        ARAXi.append(f"overlay(action=predict_drug_treats_disease)")
        return ARAXi

    @staticmethod
    def __translate_overlay_compute_jaccard(parameters):
        if ("virtual_relation_label" not in parameters) or ("end_node_keys" not in parameters) or ("intermediate_node_key" not in parameters):
            raise KeyError
        ARAXi = []
        source = parameters['end_node_keys'][0]
        target = parameters['end_node_keys'][1]
        ARAXi.append(f"overlay(action=compute_jaccard,virtual_relation_label={parameters['virtual_relation_label']},start_node_key={source},end_node_key={target},intermediate_node_key={parameters['intermediate_node_key']})")
        return ARAXi

    @staticmethod
    def __translate_overlay_fisher_exact_test(parameters):
        if ("virtual_relation_label" not in parameters) or ("subject_qnode_key" not in parameters) or ("object_qnode_key" not in parameters):
            raise KeyError
        ARAXi = []
        if 'rel_edge_key' not in parameters:
            ARAXi.append(f"overlay(action=fisher_exact_test,virtual_relation_label={parameters['virtual_relation_label']},subject_qnode_key={parameters['subject_qnode_key']},object_qnode_key={parameters['object_qnode_key']},intermediate_node_key={parameters['intermediate_node_key']})")
        else:
            ARAXi.append(f"overlay(action=fisher_exact_test,virtual_relation_label={parameters['virtual_relation_label']},subject_qnode_key={parameters['subject_qnode_key']},object_qnode_key={parameters['object_qnode_key']},intermediate_node_key={parameters['intermediate_node_key']},rel_edge_key={parameters['rel_edge_key']})")
        return ARAXi

    @staticmethod
    def __translate_filter_results_top_n(parameters):
        if 'max_results' not in parameters:
            raise KeyError
        assert type(parameters['max_results']) == int
        ARAXi = []
        ARAXi.append(f"filter_results(action=limit_number_of_results,max_results={parameters['max_results']},prune_kg=true)")  # prune the kg
        return ARAXi

    @staticmethod
    def __translate_bind(parameters):
        ARAXi = []
        ARAXi.append(f"resultify(ignore_edge_direction=true)")  # ignore edge directions
        return ARAXi

    @staticmethod
    def __translate_fill(parameters):
        if 'denylist' in parameters:
            raise NotImplementedError
        ARAXi = []
        if 'allowlist' in parameters:
            for KP_name in parameters['allowlist']:
                # continue if no results, don't enforce directionality, and use synonyms
                ARAXi.append(f"expand(kp={KP_name})")
        else:
            ARAXi.append("expand()")
        return ARAXi

    @staticmethod
    def __translate_filter_kgraph_orphans(parameters):
        ARAXi = []
        ARAXi.append(f"filter_kg(action=remove_orphaned_nodes)")
        return ARAXi

    @staticmethod
    def __translate_filter_kgraph_top_n(parameters):
        if ("edge_attribute" not in parameters):
            raise KeyError
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
    def __translate_filter_kgraph_std_dev(parameters):
        if ("edge_attribute" not in parameters):
            raise KeyError
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
    def __translate_filter_kgraph_percentile(parameters):
        if ("edge_attribute" not in parameters):
            raise KeyError
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
    def __translate_filter_kgraph_continuous_attribute(parameters):
        if ("edge_attribute" not in parameters) or ("threshold" not in parameters) or ("remove_above_or_below" not in parameters):
            raise KeyError
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
    def __translate_filter_kgraph_discrete_kedge_attribute(parameters):
        if ("edge_attribute" not in parameters) or ("remove_value" not in parameters):
            raise KeyError
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

    def translate(self, workflow):
        ARAXi = []
        for operation in workflow:
            if operation['id'] not in self.implemented:
                raise NotImplementedError
            if 'parameters' in operation:
                ARAXi.extend(getattr(self, '_' + self.__class__.__name__ + '__translate_' + operation['id'])(operation['parameters']))
            else:
                ARAXi.extend(getattr(self, '_' + self.__class__.__name__ + '__translate_' + operation['id'])({}))
        return ARAXi

    @staticmethod
    def __translate_score(parameters):
        ARAXi = []
        ARAXi.append(f"resultify(ignore_edge_direction=true)")  # ignore edge directions
        return ARAXi

    @staticmethod
    def __translate_complete_results(parameters):
        ARAXi = []
        ARAXi.append(f"resultify(ignore_edge_direction=true)")  # ignore edge directions
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
