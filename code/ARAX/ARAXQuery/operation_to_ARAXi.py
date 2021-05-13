# This will be a translation table between the Operations JSON spec (https://github.com/NCATSTranslator/OperationsAndWorkflows/) and ARAXi
import json
import itertools

class WorkflowToARAXi:
    def __init__(self):
        self.implemented = {'overlay_compute_ngd',
                            'filter_results_top_n',
                            'bind',
                            'fill',
                            'filter_kgraph_orphans'}

    # NGD
    @staticmethod
    def __translate_overlay_compute_ngd(parameters):
        if ("virtual_relation_label" not in parameters) or ("qnode_keys" not in parameters):
            raise KeyError
        ARAXi = ""  # blank to begin with
        # loop over all pairs of qnode keys and write the ARAXi
        for source, target in itertools.combinations(parameters["qnode_keys"], 2):
            # TODO: make is so ARAX properly handles -1 as the default value (in ranker)
            command = f"overlay(action=compute_ngd,default_value=inf,virtual_relation_label={parameters['virtual_relation_label']},subject_qnode_key={source},object_qnode_key={target})"
            ARAXi += f"{command}\n"
        return ARAXi

    @staticmethod
    def __translate_filter_results_top_n(parameters):
        if 'max_results' not in parameters:
            raise KeyError
        assert type(parameters['max_results']) == int
        ARAXi = ""  # blank to begin with
        command = f"filter_results(action=limit_number_of_results,max_results={parameters['max_results']},prune_kg=true)"  # prune the kg
        ARAXi += f"{command}\n"
        return ARAXi

    @staticmethod
    def __translate_bind(parameters):
        ARAXi = ""  # blank to begin with
        command = f"resultify(ignore_edge_direction=true)"  # ignore edge directions
        ARAXi += f"{command}\n"
        return ARAXi

    @staticmethod
    def __translate_fill(parameters):
        if 'denylist' in parameters:
            raise NotImplementedError
        ARAXi = ""  # blank to begin with
        if 'allowlist' in parameters:
            for KP_name in parameters['allowlist']:
                # continue if no results, don't enforce directionality, and use synonyms
                ARAXi += f"expand(kp={KP_name},continue_if_no_results=true,enforce_directionality=false,use_synonyms=true)\n"
        else:
            ARAXi += "expand()\n"
        return ARAXi

    @staticmethod
    def __translate_filter_kgraph_orphans(parameters):
        ARAXi = ""
        ARAXi += f"filter_kg(action=remove_orphaned_nodes)\n"
        return ARAXi

    def translate(self, workflow):
        ARAXi = ""
        for operation in workflow:
            if operation['id'] not in self.implemented:
                raise NotImplementedError
            ARAXi += getattr(self, '_' + self.__class__.__name__ + '__translate_' + operation['id'])(operation['parameters'])
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
        "workflow": [{
            "id": "overlay_compute_ngd",
            "parameters": {
                "virtual_relation_label": "ngd1",
                "qnode_keys": ["drug", "type-2 diabetes"]
            }
        }]
    }"""

    test_trapi = json.loads(trapi_eg)
    print(f"Workflow: {test_trapi['workflow']}")
    W = WorkflowToARAXi()
    print(f"ARAXi: {W.translate(test_trapi['workflow'])}")

if __name__ == "__main__": main()