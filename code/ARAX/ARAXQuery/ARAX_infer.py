#!/bin/env python3
"""
ARAX Infer Module -- Inference engine for drug-disease treatment and chemical-gene regulation prediction.

This module provides two main inference actions:
  1. drug_treatment_graph_expansion: Predicts drug-disease treatment relationships using the xDTD model.
     Given a drug and/or disease CURIE, returns predicted treatment pairs with explanation paths.
  2. chemical_gene_regulation_graph_expansion: Predicts chemical-gene regulation relationships using the xCRG model.
     Given a chemical or gene CURIE, returns predicted regulation pairs with explanation paths.

Notes:
  - The drug_treatment_graph_expansion action queries the precomputed xDTD prediction results that are stored in the ExplainableDTD database.
  - The chemical_gene_regulation_graph_expansion action executes the xCRG model on the fly to predict the regulation relationship between chemicals and genes.

"""

import sys
import os
from collections import Counter

from ARAX_response import ARAXResponse

pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'UI', 'OpenAPI', 'python-flask-server']))
from openapi_server.models.qualifier import Qualifier
from openapi_server.models.qualifier_constraint import QualifierConstraint as QConstraint

sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'NodeSynonymizer']))
from node_synonymizer import NodeSynonymizer

sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'ARAXQuery', 'Infer', 'scripts']))
from infer_utilities import InferUtilities
from creativeCRG import creativeCRG
from ExplianableDTD_db import ExplainableDTD


# --- Limits for results returned to keep API response times reasonable ---
MAX_DRUGS = 50
MAX_DISEASES = 50
MAX_PATHS = 25


class ARAXInfer:
    """
    ARAXInfer implements the ARAX 'infer' DSL command.

    It supports two actions:
      - drug_treatment_graph_expansion: xDTD-based drug-disease treatment prediction
      - chemical_gene_regulation_graph_expansion: xCRG-based chemical-gene regulation prediction

    Usage: ARAXInfer().apply(response, input_parameters)
    """

    def __init__(self):
        self.kedge_global_iter = 0
        self.qedge_global_iter = 0
        self.qnode_global_iter = 0
        self.option_global_iter = 0
        self.response = None
        self.message = None
        self.parameters = None
        self.allowable_actions = {
            'drug_treatment_graph_expansion',
            'chemical_gene_regulation_graph_expansion'
        }
        self.report_stats = False

        # --- xDTD parameter descriptors ---
        self.xdtd_drug_curie_info = {
            "is_required": True,
            "examples": ["CHEMBL.COMPOUND:CHEMBL55643", "CHEBI:8378", "RXNORM:1011"],
            "type": "string",
            "description": "The CURIE for a drug node (subject) used to predict potential treatable diseases."
        }
        self.xdtd_disease_curie_info = {
            "is_required": True,
            "examples": ["DOID:9352", "MONDO:0005306", "HP:0001945"],
            "type": "string",
            "description": "The CURIE for a disease node (object) used to predict potential treating drugs."
        }
        self.xdtd_qedge_id_info = {
            "is_required": False,
            "examples": ["qedge_id_1", "qedge_id_2", "qedge_id_3"],
            "type": "string",
            "description": "The id of the qedge you wish to perform the drug-disease treatment inference expansion."
        }
        self.xdtd_n_drugs_info = {
            "is_required": False,
            "examples": [5, 15, 25],
            "default": MAX_DRUGS,
            "type": "integer",
            "description": f"Number of drug nodes to return for a disease query. Default {MAX_DRUGS}, max {MAX_DRUGS}."
        }
        self.xdtd_n_diseases_info = {
            "is_required": False,
            "examples": [5, 15, 25],
            "default": MAX_DISEASES,
            "type": "integer",
            "description": f"Number of disease nodes to return for a drug query. Default {MAX_DISEASES}, max {MAX_DISEASES}."
        }
        self.xdtd_n_paths_info = {
            "is_required": False,
            "examples": [5, 15, 25],
            "default": MAX_PATHS,
            "type": "integer",
            "description": f"Number of explanation paths per result node. Default {MAX_PATHS}, max {MAX_PATHS}."
        }

        # --- xCRG parameter descriptors ---
        self.xcrg_subject_curie_info = {
            "is_required": True,
            "examples": ["UMLS:C1440117", "MESH:D007053", "CHEMBL.COMPOUND:CHEMBL33884"],
            'type': 'string',
            'description': """The chemical curie, a curie with category of either 'biolink:ChemicalEntity', 'biolink:ChemicalMixture', or 'biolink:SmallMolecule'. 
                **Note that it is required only when the `query_graph` is None, only either this parameter or `object_curie` is required, not both**""",
        }
        self.xcrg_object_curie_info = {
            "is_required": True,
            "examples": ["UniProtKB:Q96P20", "UniProtKB:O75807", "NCBIGene:406983"],
            'type': 'string',
            'description': """The gene curie, a curie with category of either 'biolink:Gene' or 'biolink:Protein'. 
                **Note that it is required only when the `query_graph` is None, only either this parameter or `subject_curie` is required, not both**""",
        }
        self.xcrg_subject_qnode_id = {
            "is_required": True,
            "examples": ["n01","n02"],
            "type": "string",
            "description": """The query node ID of a chemical of interest.
                **Note that it is required only when the `query_graph` is NOT None, and only either this parameter or `object_qnode_id` is required, not both**"""
        }
        self.xcrg_object_qnode_id = {
            "is_required": True,
            "examples": ["n01","n02"],
            "type": "string",
            "description": """The query node ID of a gene of interest.
                **Note that it is required only when the `query_graph` is NOT None, and only either this parameter or `subject_qnode_id` is required, not both**"""
        }
        self.xcrg_qedge_id_info = {
            "is_required": False,
            "examples": ["qedge_id_1","qedge_id_2","qedge_id_3"],
            "type": "string",
            "description": "The id of the qedge you wish to perform the chemical-gene regulation inference expansion."
        }
        self.xcrg_regulation_type = {
            "is_required": False,
            "examples": ["n01","n02"],
            "default": "increase",
            "type": "string",
            "description": "What model (increased prediction or decreased prediction) to consult."
        }
        self.xcrg_n_result_curies_info = {
            "is_required": False,
            "examples": [5,50,100],
            "default": 10,
            "type": "integer",
            "description": "The number of top predicted result nodes to return. If not provided defaults to 10."
        }
        self.xcrg_threshold = {
            "is_required": False,
            "examples": [0.3,0.5,0.8],
            "default": 0.5,
            "type": "float",
            "description": "Threshold to filter the prediction probability. If not provided defaults to 0.5."
        }
        self.xcrg_kp = {
            "is_required": False,
            "examples": ['infores:rtx-kg2',None],
            "default": 'infores:rtx-kg2',
            "type": "string",
            "description": "KP to use in path extraction. If not provided defaults to 'infores:rtx-kg2'."
        }
        self.xcrg_path_len = {
            "is_required": False,
            "examples": [2,3,4],
            "default": 2,
            "type": "integer",
            "description": "The length of paths for prediction. If not provided defaults to 2."
        }
        self.xcrg_n_paths_info = {
            "is_required": False,
            "examples": [5,50,100],
            "default": 10,
            "type": "integer",
            "description": "The number of paths connecting to each returned node. If not provided defaults to 10."
        }

        # --- Command definitions for DSL help/describe ---
        self.command_definitions = {
            "drug_treatment_graph_expansion": {
                "dsl_command": "infer(action=drug_treatment_graph_expansion)",
                "description": """
`drug_treatment_graph_expansion` predicts drug-disease treatment relationships using the xDTD model:

- Given a 'disease' CURIE, predicts what 'drugs' can treat this disease.
- Given a 'drug' CURIE, predicts what 'diseases' this drug can treat.
- Given both, predicts whether they have a treatment relationship.

Returns top-n results with predicted paths. Use `n_drugs`, `n_diseases`, `n_paths` to control limits.

Valid drug categories: biolink:Drug, biolink:ChemicalEntity, biolink:SmallMolecule.
Valid disease categories: biolink:Disease, biolink:PhenotypicFeature.

**Note:** The `infer` and `expand` modules should not be used together in the same query.
                """,'brief_description': "Predicts drug/disease treatment relationships for a given disease/drug CURIE with predicted paths.",
                "parameters": {
                    "drug_curie": self.xdtd_drug_curie_info,
                    "disease_curie": self.xdtd_disease_curie_info,
                    "qedge_id": self.xdtd_qedge_id_info,
                    "n_drugs": self.xdtd_n_drugs_info,
                    "n_diseases": self.xdtd_n_diseases_info,
                    "n_paths": self.xdtd_n_paths_info
                }
            },
            "chemical_gene_regulation_graph_expansion": {
                "dsl_command": "infer(action=chemical_gene_regulation_graph_expansion)",
                "description": """
`chemical_gene_regulation_graph_expansion` predicts the regulation relationship (increase/decrease activity) between chemicals and  genes. It returns the top n results along with predicted graph explinations.  
            
You can limit the maximum number of result nodes to return (via `n_result_curies=<n>`)
            
This function can be applied to  any arbitrary node CURIE, but it will not yield meaningful results if the query subject doesn't belong to the category 'chemicalentity/chemicalmixture/smallmodule' or the query object doesn't belong to the category 'gene/protein".' 

**Notes:**

**- the 'subject_curie' and 'object_curie' are not allowed to be sepcified in the same time, that is, if you give a curie to either one, the other should be omitted. However, when a query graph (i.e., the object `query_graph`) exists, the parameters 'subject_curie' and 'object_curie' become invalid. Instead, use 'subject_qnode_id' or 'object_qnode_id' to specify the query gene or chemical of interest.**

**- The `infer` and `expand` modules are not recommended to be used together in a query because it may cause some errors due to the different qnodes generated from both the `infer` and `expand` modules for the same query node.**
                    """,
                'brief_description': """
chemical_gene_regulation_graph_expansion predicts the regulation relationship between chemicals and genes and provides along with an explination graph for each prediction. 
                    """,
                "parameters": {
                    "subject_curie": self.xcrg_subject_curie_info,
                    "object_curie": self.xcrg_object_curie_info,
                    "subject_qnode_id": self.xcrg_subject_qnode_id,
                    "object_qnode_id": self.xcrg_object_qnode_id,
                    "qedge_id": self.xcrg_qedge_id_info,
                    "threshold": self.xcrg_threshold,
                    "kp": self.xcrg_kp,
                    "path_len": self.xcrg_path_len,
                    "regulation_type": self.xcrg_regulation_type,
                    "n_result_curies": self.xcrg_n_result_curies_info,
                    "n_paths": self.xcrg_n_paths_info
                }
            }
        }

    # ──────────────────────────────────────────────────────────────────────────
    #  Helper methods
    # ──────────────────────────────────────────────────────────────────────────

    def _normalize_curie(self, curie):
        """Resolve a curie to its preferred canonical form via the NodeSynonymizer.
        Returns (preferred_curie, was_normalized) tuple."""
        result = self.synonymizer.get_canonical_curies(curie)[curie]
        if result:
            return result['preferred_curie'], True
        return curie, False

    def _validate_int_param(self, param_name, default, max_val=None):
        """Validate and coerce an integer parameter with optional ceiling.
        Sets self.parameters[param_name] to the validated value or default."""
        params = self.parameters
        if param_name in params and params[param_name]:
            try:
                params[param_name] = int(params[param_name])
            except (ValueError, TypeError):
                self.response.error(
                    f"`{param_name}` must be a positive integer. Got: {params[param_name]}.",
                    error_code="ValueError")
                return
            if params[param_name] <= 0:
                self.response.error(
                    f"`{param_name}` must be > 0. Got: {params[param_name]}.",
                    error_code="ValueError")
                return
            if max_val and params[param_name] > max_val:
                self.response.warning(
                    f"`{param_name}` was {params[param_name]}, clamped to max {max_val}.")
                params[param_name] = max_val
        else:
            params[param_name] = default

    def _validate_float_param(self, param_name, default, min_val=0, max_val=1):
        """Validate and coerce a float parameter within [min_val, max_val]."""
        params = self.parameters
        if param_name in params:
            if isinstance(params[param_name], str):
                try:
                    params[param_name] = float(params[param_name])
                except ValueError:
                    self.response.error(
                        f"`{param_name}` must be a float. Got: {params[param_name]}.",
                        error_code="ValueError")
                    return
            if isinstance(params[param_name], int):
                params[param_name] = float(params[param_name])
            if not isinstance(params[param_name], float) or params[param_name] > max_val or params[param_name] < min_val:
                self.response.error(
                    f"`{param_name}` must be a float between {min_val} and {max_val}. Got: {params[param_name]}.",
                    error_code="ValueError")
        else:
            params[param_name] = default

    def report_response_stats(self, response):
        """Log KG/QG statistics to the debug stream for diagnostics."""
        message = self.message
        if not self.report_stats:
            return response
        if hasattr(message, 'query_graph') and message.query_graph:
            response.debug(f"Query graph is {message.query_graph}")
        kg = getattr(message, 'knowledge_graph', None)
        if kg and getattr(kg, 'nodes', None) and getattr(kg, 'edges', None):
            response.debug(f"Number of nodes in KG is {len(kg.nodes)}")
            response.debug(f"Number of nodes in KG by type is {Counter([x.categories[0] for x in kg.nodes.values()])}")
            response.debug(f"Number of edges in KG is {len(kg.edges)}")
            response.debug(f"Number of edges in KG by type is {Counter([x.predicate for x in kg.edges.values()])}")
            response.debug(f"Number of edges in KG with attributes is {len([x for x in kg.edges.values() if x.attributes])}")
            attribute_names = []
            for x in kg.edges.values():
                if x.attributes:
                    for attr in x.attributes:
                        if hasattr(attr, "original_attribute_name"):
                            attribute_names.append(attr.original_attribute_name)
                        if hasattr(attr, "attribute_type_id"):
                            attribute_names.append(attr.attribute_type_id)
            response.debug(f"Number of edges in KG by attribute {Counter(attribute_names)}")
        return response

    def describe_me(self):
        """Return command definitions for all supported infer actions."""
        return list(self.command_definitions.values())

    def check_params(self, allowable_parameters):
        """Validate that all supplied parameters are within the allowable set.
        Returns -1 on error, None on success."""
        for key, item in self.parameters.items():
            if key not in allowable_parameters:
                self.response.error(
                    f"Supplied parameter {key} is not permitted. Allowable: {list(allowable_parameters.keys())}",
                    error_code="UnknownParameter")
                return -1
            elif isinstance(item, (list, set)):
                for item_val in item:
                    if item_val not in allowable_parameters[key]:
                        self.response.error(
                            f"Supplied value {item_val} is not permitted for {key}. "
                            f"Allowable: {list(allowable_parameters[key])}")
                        return -1
            elif item not in allowable_parameters[key]:
                # Accept numeric types, None, and free-form curie/kp strings
                if any(isinstance(x, float) for x in allowable_parameters[key]):
                    continue
                elif any(isinstance(x, int) for x in allowable_parameters[key]):
                    continue
                elif any(x is None for x in allowable_parameters[key]):
                    continue
                elif key in ("drug_curie", "disease_curie", "subject_curie",
                             "object_curie", "subject_qnode_id", "object_qnode_id", "kp"):
                    continue
                else:
                    self.response.error(
                        f"Supplied value {item} is not permitted for {key}. "
                        f"Allowable: {list(allowable_parameters[key])}")
                    return -1

    # ──────────────────────────────────────────────────────────────────────────
    #  Top-level dispatch
    # ──────────────────────────────────────────────────────────────────────────

    def apply(self, response, input_parameters):
        """
        Main entry point. Validates input_parameters and dispatches to the appropriate action handler.

        Args:
            response: ARAXResponse object carrying the TRAPI message.
            input_parameters: dict with 'action' key and action-specific parameters.
        Returns:
            Updated ARAXResponse.
        """
        if response is None:
            response = ARAXResponse()
        self.response = response
        self.message = response.envelope.message
        self.synonymizer = NodeSynonymizer()

        if not isinstance(input_parameters, dict):
            self.response.error("Provided parameters is not a dict", error_code="ParametersNotDict")
            return self.response

        allowable_actions = self.allowable_actions
        if 'action' not in input_parameters:
            self.response.error(f"Must supply an action. Allowable: {allowable_actions}", error_code="MissingAction")
        elif input_parameters['action'] not in allowable_actions:
            self.response.error(f"Action {input_parameters['action']} is not permitted. Allowable: {allowable_actions}", error_code="UnknownAction")

        if self.response.status != 'OK':
            return self.response

        parameters = dict(input_parameters)
        self.response.data['parameters'] = parameters
        self.parameters = parameters

        # Dynamically dispatch to __drug_treatment_graph_expansion or __chemical_gene_regulation_graph_expansion
        getattr(self, '_' + self.__class__.__name__ + '__' + parameters['action'])() # thank you https://stackoverflow.com/questions/11649848/call-methods-by-string

        self.response.debug(f"Applying Infer to Message with parameters {parameters}")  # TODO: re-write this to be more specific about the actual action being performed

        if self.report_stats:
            self.response = self.report_response_stats(self.response)
        return self.response

    # ──────────────────────────────────────────────────────────────────────────
    #  Action: drug_treatment_graph_expansion (xDTD)
    # ──────────────────────────────────────────────────────────────────────────

    def __drug_treatment_graph_expansion(self, describe=False):
        """
        Predict drug-disease treatment relationships using the xDTD model.

        Workflow:
          1. Validate and normalize drug/disease CURIEs via NodeSynonymizer.
          2. Query ExplainableDTD database for prediction scores and explanation paths.
          3. Delegate to InferUtilities.genrete_treat_subgraphs to build TRAPI subgraph.
        """
        message = self.message
        parameters = self.parameters
        XDTD = ExplainableDTD()

        # Build allowable parameters based on whether a query graph exists
        if message and parameters and hasattr(message, 'query_graph') and hasattr(message.query_graph, 'nodes'):
            allowable_parameters = {
                'action': {'drug_treatment_graph_expansion'},
                'drug_curie': {str()},
                'disease_curie': {str()},
                'qedge_id': set(self.message.query_graph.edges.keys()),
                'n_drugs': {int()},
                'n_diseases': {int()},
                'n_paths': {int()}
            }
        else:
            allowable_parameters = {
                'action': {'drug_treatment_graph_expansion'},
                'drug_curie': {'Drug CURIE for treatment prediction.'},
                'disease_curie': {'Disease CURIE for treatment prediction.'},
                'qedge_id': {'Query edge id for inference.'},
                'n_drugs': {f'Number of drugs to return. Default {MAX_DRUGS}, max {MAX_DRUGS}.'},
                'n_diseases': {f'Number of diseases to return. Default {MAX_DISEASES}, max {MAX_DISEASES}.'},
                'n_paths': {f'Number of paths per result. Default {MAX_PATHS}, max {MAX_PATHS}.'}
            }

        if describe:
            allowable_parameters['brief_description'] = self.command_definitions['drug_treatment_graph_expansion']
            return allowable_parameters

        resp = self.check_params(allowable_parameters)

        # Validate numeric parameters with ceiling enforcement
        self._validate_int_param('n_drugs', default=MAX_DRUGS, max_val=MAX_DRUGS)
        self._validate_int_param('n_diseases', default=MAX_DISEASES, max_val=MAX_DISEASES)
        self._validate_int_param('n_paths', default=MAX_PATHS, max_val=MAX_PATHS)

        if self.response.status != 'OK':
            return self.response

        # --- Resolve preferred CURIEs ---
        # Two paths: (A) query_graph exists => CURIEs must be in the QG; (B) no QG => CURIEs supplied directly
        preferred_drug_curie = None
        preferred_disease_curie = None
        
        if hasattr(message, 'query_graph') and hasattr(message.query_graph, 'nodes') and message.query_graph.nodes:
            # Path A: Query graph exists -- validate CURIEs against QG nodes
            qnodes = message.query_graph.nodes
            all_qnode_curie_ids = [cid for qn in qnodes.values() if qn.ids for cid in qn.ids]

            if 'drug_curie' not in parameters and 'disease_curie' not in parameters:
                self.response.error("query_graph detected; specify at least 'drug_curie' or 'disease_curie'.")
                return self.response

            if 'drug_curie' in parameters and parameters['drug_curie']:
                if parameters['drug_curie'] not in all_qnode_curie_ids:
                    self.response.error(f"drug_curie '{parameters['drug_curie']}' not found in query graph")
                    return self.response
                preferred_drug_curie, _ = self._normalize_curie(parameters['drug_curie'])

            if 'disease_curie' in parameters and parameters['disease_curie']:
                if parameters['disease_curie'] not in all_qnode_curie_ids:
                    self.response.error(f"disease_curie '{parameters['disease_curie']}' not found in query graph")
                    return self.response
                preferred_disease_curie, _ = self._normalize_curie(parameters['disease_curie'])

            if not preferred_drug_curie and not preferred_disease_curie:
                self.response.error("At least one of 'drug_curie' or 'disease_curie' must have a non-empty value")
                return self.response

            # Mark all query edges as inferred treats
            for qedge in message.query_graph.edges.values():
                qedge.knowledge_type = "inferred"
                qedge.predicates = ["biolink:treats"]

        else:
            # Path B: No query graph -- CURIEs supplied directly as parameters
            if 'drug_curie' not in parameters and 'disease_curie' not in parameters:
                self.response.error("No query_graph found; specify 'drug_curie' or 'disease_curie'.")
                return self.response

            if 'drug_curie' in parameters:
                raw = parameters['drug_curie']
                parameters['drug_curie'] = None if raw == 'None' else raw
                if parameters['drug_curie']:
                    preferred_drug_curie, normalized = self._normalize_curie(parameters['drug_curie'])
                    if normalized:
                        self.response.debug(f"Normalized drug curie {parameters['drug_curie']} -> {preferred_drug_curie}")
                    else:
                        self.response.warning(f"Could not normalize drug curie {parameters['drug_curie']}, using as-is")

            if 'disease_curie' in parameters:
                raw = parameters['disease_curie']
                parameters['disease_curie'] = None if raw == 'None' else raw
                if parameters['disease_curie']:
                    preferred_disease_curie, normalized = self._normalize_curie(parameters['disease_curie'])
                    if normalized:
                        self.response.debug(f"Normalized disease curie {parameters['disease_curie']} -> {preferred_disease_curie}")
                    else:
                        self.response.warning(f"Could not normalize disease curie {parameters['disease_curie']}, using as-is")

            if not preferred_drug_curie and not preferred_disease_curie:
                self.response.error("At least one of 'drug_curie' or 'disease_curie' must have a non-empty value")
                return self.response

        if self.response.status != 'OK' or resp == -1:
            return self.response

        # --- Query the ExplainableDTD database ---
        try:
            top_scores = XDTD.get_score_table(drug_curie_ids=preferred_drug_curie, disease_curie_ids=preferred_disease_curie)
            top_paths = XDTD.get_top_path(drug_curie_ids=preferred_drug_curie, disease_curie_ids=preferred_disease_curie)
        except Exception as e:
            self.response.warning(f"Database query failed for drug={preferred_drug_curie}, disease={preferred_disease_curie}: {e}")
            return self.response

        # Validate results and apply N limits
        if preferred_drug_curie and preferred_disease_curie:
            if len(top_scores) == 0:
                self.response.warning(f"No predicted scores for drug={preferred_drug_curie}, disease={preferred_disease_curie}. "
                                      "Likely the model was not trained with this drug-disease pair, or score < 0.3.")
                return self.response
            if len(top_paths) == 0:
                self.response.warning(f"No predicted paths for drug={preferred_drug_curie}, disease={preferred_disease_curie}. "
                                      "Likely the model considers there is no reasonable path for this drug-disease pair.")
        elif preferred_drug_curie:
            if len(top_scores) == 0:
                self.response.warning(f"No predicted diseases for drug={preferred_drug_curie}." 
                                      "Likely the model was not trained with this drug, or score < 0.3.")
                return self.response
            if len(top_paths) == 0:
                self.response.warning(f"No predicted paths for drug={preferred_drug_curie}." 
                                      "Likely the model considers there is no reasonable path for this drug.")
            top_scores = top_scores.iloc[:parameters['n_diseases'], :].reset_index(drop=True)
        elif preferred_disease_curie:
            if len(top_scores) == 0:
                self.response.warning(f"No predicted drugs for disease={preferred_disease_curie}.")
                return self.response
            if len(top_paths) == 0:
                self.response.warning(f"No predicted paths for disease={preferred_disease_curie}.")
            top_scores = top_scores.iloc[:parameters['n_drugs'], :].reset_index(drop=True)

        # Limit paths per drug-disease pair to n_paths
        top_paths = {
            (row[0], row[2]): top_paths[(row[0], row[2])][:parameters['n_paths']]
            for row in top_scores.to_numpy()
            if (row[0], row[2]) in top_paths
        }

        # --- Build TRAPI subgraph ---
        iu = InferUtilities()
        qedge_id = parameters.get('qedge_id')
        self.response, self.kedge_global_iter, self.qedge_global_iter, self.qnode_global_iter, self.option_global_iter = \
            iu.genrete_treat_subgraphs(self.response, top_scores, top_paths, preferred_drug_curie, preferred_disease_curie, qedge_id)

        return self.response

    # ──────────────────────────────────────────────────────────────────────────
    #  Action: chemical_gene_regulation_graph_expansion (xCRG)
    # ──────────────────────────────────────────────────────────────────────────

    def __chemical_gene_regulation_graph_expansion(self, describe=False):
        """
        Run "chemical_gene_regulation_graph_expansion" action.
        Allowable parameters: {'subject_curie': str, 
                                'object_curie': str,
                                'subject_qnode_id': str,
                                'object_qnode_id': str,
                                'qedge_id' str,
                                'regulation_type': {'increase', 'decrease'},
                                'threshold': float,
                                'kp': str,
                                'path_len': int,
                                'n_result_curies': int,
                                'n_paths': int}
        :return:
        """
        message = self.message
        parameters = self.parameters
        XCRG = creativeCRG(self.response, os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'ARAXQuery', 'Infer', 'data', 'xCRG_data']))
        # make a list of the allowable parameters (keys), and their possible values (values). Note that the action and corresponding name will always be in the allowable parameters
        if message and parameters and hasattr(message, 'query_graph') and hasattr(message.query_graph, 'nodes'):
            allowable_parameters = {'action': {'chemical_gene_regulation_graph_expansion'},
                                    'subject_curie': {str()},
                                    'object_curie': {str()},
                                    'subject_qnode_id': {str()},
                                    'object_qnode_id': {str()},
                                    'qedge_id': set([key for key in self.message.query_graph.edges.keys()]),
                                    'regulation_type': ['increase', 'decrease'],
                                    'threshold': {float()},
                                    'kp': {str()},
                                    'path_len': {int()},
                                    'n_result_curies': {int()},
                                    'n_paths': {int()}
                                }
        else:
            allowable_parameters = {'action': {'chemical_gene_regulation_graph_expansion'},
                                    'subject_curie': {'The chemical curie used for gene regulation.'},
                                    'object_curie': {'The gene curie used to predict what chemicals can regulate it.'},
                                    'subject_qnode_id': {'The query graph node ID of a chemical. (If `query_graph` exists, either this parameter or `object_qnode_id` is required.)'},
                                    'object_qnode_id': {'The query graph node ID of a gene. (If `query_graph` exists, either this parameter or `subject_qnode_id` is required.)'},
                                    'qedge_id': {'The edge to place the predicted mechanism of action on. If none is provided, the query graph must be empty and a new one will be inserted.'},
                                    'regulation_type': {"What model (increased prediction or decreased prediction) to consult. Two options: 'increase', 'decrease'."},
                                    'threshold': {"Threshold to filter the prediction probability. If not provided defaults to 0.5."},
                                    'kp': {"KP to use in path extraction. If not provided defaults to 'infores:rtx-kg2'."},
                                    'path_len': {"The length of paths for prediction. If not provided defaults to 2."},
                                    'n_result_curies': {'The number of top predicted result nodes to return. Defaults to 10.'},
                                    'n_paths': {'The number of paths connecting to each returned node. Defaults to 10.'}
                                }

        # A little function to describe what this thing does
        if describe:
            allowable_parameters['brief_description'] = self.command_definitions['connect_nodes']
            return allowable_parameters

        # Make sure only allowable parameters and values have been passed
        resp = self.check_params(allowable_parameters)

        # Set defaults and check parameters:
        if 'regulation_type' in self.parameters:
            self.parameters['regulation_type'] = self.parameters['regulation_type'].lower()
            if self.parameters['regulation_type'] not in ['increase', 'decrease']:
                self.response.error(
                f"The `regulation_type` value must be either 'increase' or 'decrease'. The provided value was {self.parameters['regulation_type']}.",
                error_code="ValueError")
        else:
            self.parameters['regulation_type'] = 'increase'
            
        if 'threshold' in self.parameters:
            if isinstance(self.parameters['threshold'], str):
                self.parameters['threshold'] = eval(self.parameters['threshold'])
            if isinstance(self.parameters['threshold'], int):
                if self.parameters['threshold'].is_float():
                    self.parameters['threshold'] = float(self.parameters['threshold'])
            if not isinstance(self.parameters['threshold'], float) or self.parameters['threshold'] > 1 or self.parameters['threshold'] < 0:
                self.response.error(
                f"The `threshold` value must be a positive float between 0 and 1. The provided value was {self.parameters['threshold']}.",
                error_code="ValueError")
        else:
            self.parameters['threshold'] = 0.5   

        if 'kp' in self.parameters:
            if not isinstance(self.parameters['kp'], str) or not (self.parameters['kp'] is None):
                self.response.error(
                f"The `kp` value must be None or a specific kp. The provided value was {self.parameters['kp']}.",
                error_code="ValueError")
        else:
            self.parameters['kp'] = 'infores:rtx-kg2'

        if 'path_len' in self.parameters:
            if isinstance(self.parameters['path_len'], str):
                self.parameters['path_len'] = eval(self.parameters['path_len'])
            if isinstance(self.parameters['path_len'], float):
                if self.parameters['path_len'].is_integer():
                    self.parameters['path_len'] = int(self.parameters['path_len'])
            if not isinstance(self.parameters['path_len'], int) or self.parameters['path_len'] < 1:
                self.response.error(
                f"The `path_len` value must be a positive integer. The provided value was {self.parameters['path_len']}.",
                error_code="ValueError")
        else:
            self.parameters['path_len'] = 2

        if 'n_result_curies' in self.parameters:
            if isinstance(self.parameters['n_result_curies'], str):
                self.parameters['n_result_curies'] = eval(self.parameters['n_result_curies'])
            if isinstance(self.parameters['n_result_curies'], float):
                if self.parameters['n_result_curies'].is_integer():
                    self.parameters['n_result_curies'] = int(self.parameters['n_result_curies'])
            if not isinstance(self.parameters['n_result_curies'], int) or self.parameters['n_result_curies'] < 1:
                self.response.error(
                f"The `n_result_curies` value must be a positive integer. The provided value was {self.parameters['n_result_curies']}.",
                error_code="ValueError")
        else:
            self.parameters['n_result_curies'] = 30

        if 'n_paths' in self.parameters:
            if isinstance(self.parameters['n_paths'], str):
                self.parameters['n_paths'] = eval(self.parameters['n_paths'])
            if isinstance(self.parameters['n_paths'], float):
                if self.parameters['n_paths'].is_integer():
                    self.parameters['n_paths'] = int(self.parameters['n_paths'])
            if not isinstance(self.parameters['n_paths'], int) or self.parameters['n_paths'] < 1:
                self.response.error(
                f"The `n_paths` value must be a positive integer. The provided value was {self.parameters['n_paths']}.",
                error_code="ValueError")
        else:
            self.parameters['n_paths'] = 10

        if self.response.status != 'OK':
            return self.response

        # Make sure that if at least subject node or object node is provided. If it is provided, check if it also exists in the query graph        
        if hasattr(message, 'query_graph') and hasattr(message.query_graph, 'nodes') and message.query_graph.nodes:
            qnodes = message.query_graph.nodes
            if 'subject_qnode_id' in parameters or 'object_qnode_id' in parameters:
                if 'subject_qnode_id' in parameters:
                    if parameters['subject_qnode_id'] in qnodes:
                        if not qnodes[parameters['subject_qnode_id']].ids:
                            self.response.error(f"The corresponding ids of subject_qnode_id '{parameters['subject_qnode_id']}' is None")
                            return self.response
                        subject_curie = qnodes[parameters['subject_qnode_id']].ids[0]
                        normalized_subject_curie = self.synonymizer.get_canonical_curies(subject_curie)[subject_curie]
                        if normalized_subject_curie:
                            preferred_subject_curie = normalized_subject_curie['preferred_curie']
                        else:
                            preferred_subject_curie = subject_curie
                    else:
                        self.response.error(f"Could not find subject_qnode_id '{parameters['subject_qnode_id']}' in the query graph")
                        return self.response
                else:
                    preferred_subject_curie = None

                if 'object_qnode_id' in parameters:
                    if parameters['object_qnode_id'] in qnodes:
                        if not qnodes[parameters['object_qnode_id']].ids:
                            self.response.error(f"The corresponding ids of object_qnode_id '{parameters['object_qnode_id']}' is None")
                            return self.response
                        object_curie = qnodes[parameters['object_qnode_id']].ids[0]
                        normalized_object_curie = self.synonymizer.get_canonical_curies(object_curie)[object_curie]
                        if normalized_object_curie:
                            preferred_object_curie = normalized_object_curie['preferred_curie']
                        else:
                            preferred_object_curie = subject_curie
                    else:
                        self.response.error(f"Could not find object_qnode_id '{parameters['object_qnode_id']}' in the query graph")
                        return self.response
                else:
                    preferred_object_curie = None

                if preferred_subject_curie and preferred_object_curie:
                    self.response.error(f"The parameters 'subject_curie' and 'object_curie' in infer action 'chemical_gene_regulation_graph_expansion' can't be specified in the same time.")
                    return self.response

                if not preferred_subject_curie and not preferred_object_curie:
                    self.response.error(f"Both parameters 'subject_curie' and 'object_curie' are not provided. Please provide the curie for either one of them")
                    return self.response
                qedges = message.query_graph.edges
                

            else:
                self.response.error(f"The 'query_graph' is detected. Either one of 'subject_qnode_id' or 'object_qnode_id' should be specified.")
            
            if self.parameters['regulation_type'] == 'increase':
                edge_qualifier_direction = 'increased'
            else:
                edge_qualifier_direction = 'decreased'
            edge_qualifier_list = [
                Qualifier(qualifier_type_id='biolink:object_aspect_qualifier', qualifier_value='activity_or_abundance'),
                Qualifier(qualifier_type_id='biolink:object_direction_qualifier', qualifier_value=edge_qualifier_direction)]
                
            for qedge in qedges:
                edge = message.query_graph.edges[qedge]
                edge.knowledge_type = "inferred"
                edge.predicates = ["biolink:affects"]
                edge.qualifier_constraints = [QConstraint(qualifier_set=edge_qualifier_list)]
                   

        else:
            if 'subject_curie' in parameters or 'object_curie' in parameters:
                if 'subject_curie' in parameters:
                    parameters['subject_curie'] = eval(parameters['subject_curie']) if parameters['subject_curie'] == 'None' else parameters['subject_curie']
                    if parameters['subject_curie']:
                        ## if 'subject_curie' passes, return its normalized curie
                        normalized_subject_curie = self.synonymizer.get_canonical_curies(self.parameters['subject_curie'])[self.parameters['subject_curie']]
                        if normalized_subject_curie:
                            preferred_subject_curie = normalized_subject_curie['preferred_curie']
                            self.response.debug(f"Get a preferred sysnonym {preferred_subject_curie} from Node Synonymizer for subject curie {self.parameters['subject_curie']}")
                        else:
                            preferred_subject_curie = self.parameters['subject_curie']
                            self.response.warning(f"Could not get a preferred sysnonym for the queried chemical {self.parameters['subject_curie']} and thus keep it as it")
                    else:
                        preferred_subject_curie = None
                else:
                    preferred_subject_curie = None

                if 'object_curie' in parameters:
                    parameters['object_curie'] = eval(parameters['object_curie']) if parameters['object_curie'] == 'None' else parameters['object_curie']
                    if parameters['object_curie']:
                        ## if 'object_curie' passes, return its normalized curie
                        normalized_object_curie = self.synonymizer.get_canonical_curies(self.parameters['object_curie'])[self.parameters['object_curie']]
                        if normalized_object_curie:
                            preferred_object_curie = normalized_object_curie['preferred_curie']
                            self.response.debug(f"Get a preferred sysnonym {preferred_object_curie} from Node Synonymizer for object curie {self.parameters['object_curie']}")
                        else:
                            preferred_object_curie = self.parameters['object_curie']
                            self.response.warning(f"Could not get a preferred sysnonym for the queried gene {self.parameters['object_curie']}")
                    else:
                        preferred_object_curie = None
                else:
                    preferred_object_curie = None


                if preferred_subject_curie and preferred_object_curie:
                    self.response.error(f"The parameters 'subject_curie' and 'object_curie' in infer action 'chemical_gene_regulation_graph_expansion' can't be specified in the same time.")
                    return self.response

                if not preferred_subject_curie and not preferred_object_curie:
                    self.response.error(f"Both parameters 'subject_curie' and 'object_curie' are not provided. Please provide the curie for either one of them")
                    return self.response
            else:
                self.response.error(f"No 'query_graph' is found and thus either 'subject_curie' or 'object_curie' should be specified.")

        # return if bad parameters have been passed
        if self.response.status != 'OK' or resp == -1:
            return self.response


        if preferred_subject_curie and not preferred_object_curie:
            try:
                top_predictions = XCRG.predict_top_N_genes(query_chemical=preferred_subject_curie, N=self.parameters['n_result_curies'], threshold=self.parameters['threshold'], model_type=self.parameters['regulation_type'])
                top_paths = XCRG.predict_top_M_paths(query_chemical=preferred_subject_curie, query_gene=None, model_type=self.parameters['regulation_type'], N=self.parameters['n_result_curies'], M=self.parameters['n_paths'], threshold=self.parameters['threshold'], kp=self.parameters['kp'], path_len=self.parameters['path_len'], interm_ids=None, interm_names= None, interm_categories=None)
            except Exception as e:
                error_type = type(e).__name__  # Get the type of the exception
                error_message = str(e)  # Get the exception message
                self.response.error(f"An error of type {error_type} occurred while trying to get top genes or paths for chemical {preferred_subject_curie}. Error message: {error_message}", error_code="ValueError")
                return self.response
            if top_predictions is None or len(top_predictions) == 0:
                self.response.warning(f"Could not get predicted genes for chemical {preferred_subject_curie}. Likely the model was not trained with this chemical.")
                return self.response
            if top_paths is None or len(top_paths) == 0:
                self.response.warning(f"Could not get any predicted paths for chemical {preferred_subject_curie}. Either Plover is not reachable or no paths found")

            iu = InferUtilities()
            qedge_id = self.parameters.get('qedge_id')
            
            
            self.response, self.kedge_global_iter, self.qedge_global_iter, self.qnode_global_iter, self.option_global_iter = iu.genrete_regulate_subgraphs(self.response, preferred_subject_curie, top_predictions, top_paths, qedge_id, self.parameters['regulation_type'])
        elif not preferred_subject_curie and preferred_object_curie:
            try:
                top_predictions = XCRG.predict_top_N_chemicals(query_gene=preferred_object_curie, N=self.parameters['n_result_curies'], threshold=self.parameters['threshold'], model_type=self.parameters['regulation_type'])
                top_paths = XCRG.predict_top_M_paths(query_chemical=None, query_gene=preferred_object_curie, model_type=self.parameters['regulation_type'], N=self.parameters['n_result_curies'], M=self.parameters['n_paths'], threshold=self.parameters['threshold'], kp=self.parameters['kp'], path_len=self.parameters['path_len'], interm_ids=None, interm_names= None, interm_categories=None)
            except Exception as e:
                error_type = type(e).__name__  # Get the type of the exception
                error_message = str(e)  # Get the exception message
                self.response.error(f"An error of type {error_type} occurred while trying to get top chemicals or paths for gene {preferred_object_curie}. Error message: {error_message}", error_code="ValueError")
                return self.response
            if top_predictions is None or len(top_predictions) == 0:
                self.response.warning(f"Could not get predicted chemicals for gene {preferred_object_curie}. Likely the model was not trained with this gene.")
                return self.response
            if top_paths is None or len(top_paths) == 0:
                self.response.warning(f"Could not get any predicted paths for gene {preferred_object_curie}. Either Plover is not reachable or no paths found")
                return self.response
            iu = InferUtilities()
            qedge_id = self.parameters.get('qedge_id')
            
            self.response, self.kedge_global_iter, self.qedge_global_iter, self.qnode_global_iter, self.option_global_iter = iu.genrete_regulate_subgraphs(self.response, None, top_predictions, top_paths, qedge_id, self.parameters['regulation_type'])

        return self.response


##########################################################################################
def main():
    pass


if __name__ == "__main__": main()
