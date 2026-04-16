import requests
import json

# This is from Kevin Xin from team orange.
# It performs MOD1 and MOD2 (annotation and scoring modules) of workflow 1
# input std API response format
# output std API response format

def annotate_drug(drug_id, id_type):
    """
    Provide annotation for drug

    """
    if id_type == 'chembl':
        query_template = 'http://mychem.info/v1/query?q=drugcentral.xref.chembl_id:{{drug_id}}&fields=drugcentral'
    elif id_type == 'chebi':
        query_template = 'http://mychem.info/v1/query?q=drugcentral.xref.chebi:"{{drug_id}}"&fields=drugcentral'
    query_url = query_template.replace('{{drug_id}}', drug_id)
    results = {'annotate': {'common_side_effects': None, 'approval': None, 'indication': None, 'EPC': None}}
    api_response = requests.get(query_url).json()

    # get drug approval information from mychem
    approval = DictQuery(api_response).get("hits/drugcentral/approval")
    if approval:
        results['annotate']['approval'] = 'Yes'
    # get drug approved indication information
    indication = DictQuery(api_response).get("hits/drugcentral/drug_use/indication")
    if len(indication) > 0 and indication[0] and not isinstance(indication[0], list):
        results['annotate']['indication'] = [_doc['snomed_full_name'] for _doc in indication if
                                             'snomed_full_name' in _doc]
    elif len(indication) > 0 and indication[0]:
        results['annotate']['indication'] = [_doc['snomed_full_name'] for _doc in indication[0] if
                                             'snomed_full_name' in _doc]
        # get drug established pharm class information
    epc = DictQuery(api_response).get("hits/drugcentral/pharmacology_class/fda_epc")
    if len(epc) > 0 and epc[0] and not isinstance(epc[0], list):
        results['annotate']['EPC'] = [_doc['description'] for _doc in epc if 'description' in _doc]
    elif len(epc) > 0 and epc[0]:
        results['annotate']['EPC'] = [_doc['description'] for _doc in epc[0] if 'description' in _doc]
        # get drug common side effects
    side_effects = DictQuery(api_response).get("hits/drugcentral/fda_adverse_event")
    if len(side_effects) > 0 and side_effects[0]:
        if isinstance(side_effects[0], list):
            # only keep side effects with likelihood higher than the threshold
            results['annotate']['common_side_effects'] = [_doc['meddra_term'] for _doc in side_effects[0] if
                                                          _doc['llr'] > _doc['llr_threshold']]
            if len(results['annotate']['common_side_effects']) > 10:
                results['annotate']['common_side_effects'] = results['annotate']['common_side_effects'][:10]
        elif isinstance(side_effects[0], dict) and 'meddra_term' in side_effects[0]:
            results['annotate']['common_side_effects'] = side_effects[0]['meddra_term']
    return unlist(results)


"""
Helper functions
"""
def unlist(d):
    """
    If the list contain only one element, unlist it
    """
    for key, val in d.items():
            if isinstance(val, list):
                if len(val) == 1:
                    d[key] = val[0]
            elif isinstance(val, dict):
                unlist(val)
    return d

class DictQuery(dict):
    """
    Helper function to fetch value from a python dictionary
    """
    def get(self, path, default = None):
        keys = path.split("/")
        val = None

        for key in keys:
            if val:
                if isinstance(val, list):
                    val = [ v.get(key, default) if v else None for v in val]
                else:
                    val = val.get(key, default)
            else:
                val = dict.get(self, key, default)

            if not val:
                break;

        return val

def annotate_std_results(input_json_doc):
    """
    Annotate results from reasoner's standard output
    """
    for _doc in input_json_doc['result_list']:
        for _node in _doc['result_graph']['node_list']:
            if _node['id'].startswith('CHEMBL'):
                _drug = _node['id'].split(':')[-1]
                _node['node_attributes'] = annotate_drug(_drug, 'chembl')
            elif _node['id'].startswith("CHEBI:"):
                _node['node_attributes'] = annotate_drug(_node['id'], 'chebi')
    return input_json_doc

# This is the main thing to run
json_doc_path = '/home/dkoslicki/Dropbox/OtherOSU/WF1MOD1-MOD2_results_DOID9352.json'
with open(json_doc_path) as f:
    data = json.load(f)
annotate_std_results(data)

