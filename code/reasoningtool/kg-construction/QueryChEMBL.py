''' Queries the ChEMBL database to find target proteins for drugs.
'''

__author__ = 'Stephen Ramsey'
__copyright__ = 'Oregon State University'
__credits__ = ['Stephen Ramsey']
__license__ = 'MIT'
__version__ = '0.1.0'
__maintainer__ = ''
__email__ = ''
__status__ = 'Prototype'

import urllib
import requests
import requests_cache
import sys

from QueryUniprot import QueryUniprot

class QueryChEMBL:
    API_BASE_URL = 'https://www.ebi.ac.uk/chembl/api/data'
    TIMEOUT_SEC = 120

    @staticmethod
    def send_query_get(handler, url_suffix):
        url = QueryChEMBL.API_BASE_URL + '/' + handler + '?' + url_suffix
#        print(url)
        try:
            res = requests.get(url,
                               timeout=QueryChEMBL.TIMEOUT_SEC)
        except requests.exceptions.Timeout:
            print(url, file=sys.stderr)
            print('Timeout in QueryChEMBL for URL: ' + url, file=sys.stderr)
            return None
        except KeyboardInterrupt:
            sys.exit(0)
        except BaseException as e:
            print(url, file=sys.stderr)
            print('%s received in QueryChEMBL for URL: %s' % (e, url), file=sys.stderr)
            return None
        status_code = res.status_code
        if status_code != 200:
            print(url, file=sys.stderr)
            print('Status code ' + str(status_code) + ' for url: ' + url, file=sys.stderr)
            return None
        return res.json()

    @staticmethod
    def get_chembl_ids_for_drug(drug_name):
        if not isinstance(drug_name, str):
            return set()

        drug_name_safe = urllib.parse.quote(drug_name, safe='')
        res = QueryChEMBL.send_query_get(handler='compound_record.json',
                                         url_suffix='compound_name__iexact=' + drug_name_safe)
        res_chembl_set = set()
        if res is not None:
            compound_records = res.get('compound_records', None)
            if compound_records is not None:
                for compound_record in compound_records:
                    chembl_id = compound_record.get('molecule_chembl_id', None)
                    if chembl_id is not None:
                        res_chembl_set.add(chembl_id)
        return res_chembl_set

    @staticmethod
    def get_target_uniprot_ids_for_chembl_id(chembl_id):
        print(chembl_id, file=sys.stderr)
        if not isinstance(chembl_id, str):
            return dict()

        res_targets_dict = dict()
        
        target_mechanisms_json = QueryChEMBL.get_mechanisms_for_chembl_id(chembl_id)
        for target_mechanism in target_mechanisms_json:
            target_chembl_id = target_mechanism.get("target_chembl_id", None)
            if target_chembl_id is not None:
                target_uniprot_ids = QueryChEMBL.map_chembl_target_to_uniprot_ids(target_chembl_id)
                for target_uniprot_id in target_uniprot_ids:
                    res_targets_dict[target_uniprot_id] = float(1.0)
        
        res = QueryChEMBL.send_query_get(handler='target_prediction.json',
                                         url_suffix='molecule_chembl_id__exact=' + chembl_id + '&target_organism__exact=Homo%20sapiens')
        if res is not None:
            target_predictions_list = res.get('target_predictions', None)
            if target_predictions_list is not None:
                for target_prediction in target_predictions_list:
                    #                    print(target_prediction)
                    target_uniprot_id = target_prediction.get('target_accession', None)
                    target_probability = target_prediction.get('probability', None)
                    if target_uniprot_id is not None:
                        target_organism = target_prediction.get('target_organism', None)
                        if target_organism is not None:
                            assert target_organism == "Homo sapiens"
                        # need to get the gene ID for this Uniprot ID
                        if target_uniprot_id not in res_targets_dict:
                            res_targets_dict[target_uniprot_id] = float(target_probability)

        return res_targets_dict

    @staticmethod
    def map_chembl_target_to_uniprot_ids(target_chembl_id):
        res_json = QueryChEMBL.send_query_get(handler="target.json",
                                              url_suffix="target_chembl_id=" + target_chembl_id)
        res_set = set()
#        print(res_json)
        if res_json is not None:
            targets = res_json.get("targets", None)
            if targets is not None and len(targets) > 0:
                for target in targets:
                    components = target.get("target_components", None)
                    if components is not None:
                        for component in components:
                            xrefs = component.get("target_component_xrefs", None)
                            if xrefs is not None:
                                for xref in xrefs:
                                    if xref is not None:
                                        xref_src_db = xref.get("xref_src_db", None)
                                        if xref_src_db is not None:
                                            if xref_src_db == "UniProt":
                                                uniprot_id = xref.get("xref_id", None)
                                                if uniprot_id is not None:
                                                    uniprot_id_citeable = QueryUniprot.get_citeable_accession_for_accession(uniprot_id)
                                                    if uniprot_id_citeable is not None:
                                                        res_set |= set([uniprot_id_citeable])
        return res_set
        
    @staticmethod
    def get_target_uniprot_ids_for_drug(drug_name):
        if not isinstance(drug_name, str):
            return dict()

        chembl_ids_for_drug = QueryChEMBL.get_chembl_ids_for_drug(drug_name)
        res_uniprot_ids = dict()
        for chembl_id in chembl_ids_for_drug:
            #            print(chembl_id)
            uniprot_ids_dict = QueryChEMBL.get_target_uniprot_ids_for_chembl_id(chembl_id)
            for uniprot_id in uniprot_ids_dict.keys():
                res_uniprot_ids[uniprot_id] = uniprot_ids_dict[uniprot_id]
        return res_uniprot_ids

    @staticmethod
    def get_mechanisms_for_chembl_id(chembl_id):
        """Retrieves mechanism of action and target of each drug.

        Args:
            chembl_id (str): a ChEMBL id, e.g., "CHEMBL521"

        Returns:
            array: an array of mechanism of actions, or [] if no mechanism data could be obtained for the given
            ChEMBL ID

            example:
                [
                    {"action_type": "INHIBITOR",
                    "binding_site_comment": null,
                    "direct_interaction": true,
                    "disease_efficacy": true,
                    "max_phase": 4,
                    "mec_id": 1180,
                    "mechanism_comment": null,
                    "mechanism_of_action": "Cyclooxygenase inhibitor",
                    "mechanism_refs": [
                        {"ref_id": "0443-059748 PP. 229",
                        "ref_type": "ISBN",
                        "ref_url": "http://www.isbnsearch.org/isbn/0443059748"
                        },
                        {"ref_id": "Ibuprofen",
                        "ref_type": "Wikipedia",
                        "ref_url": "http://en.wikipedia.org/wiki/Ibuprofen"}
                        ],
                    "molecular_mechanism": true,
                    "molecule_chembl_id": "CHEMBL521",
                    "record_id": 1343587,
                    "selectivity_comment": null,
                    "site_id": null,
                    "target_chembl_id": "CHEMBL2094253"}
                ]
        """
        if not isinstance(chembl_id, str):
            return []

        res = QueryChEMBL.send_query_get(handler='mechanism.json',
                                         url_suffix='molecule_chembl_id=' + chembl_id)
        res_mechanisms_array = []
        if res is not None:
            mechanism_records = res.get('mechanisms', None)
            if mechanism_records is not None and len(mechanism_records) > 0:
                res_mechanisms_array = mechanism_records
        return res_mechanisms_array


if __name__ == '__main__':
    print(QueryChEMBL.get_target_uniprot_ids_for_chembl_id('CHEMBL521'))
    print(QueryChEMBL.get_target_uniprot_ids_for_chembl_id('CHEMBL2364648'))
#    print(QueryChEMBL.get_mechanisms_for_chembl_id("CHEMBL521"))
#    print(QueryChEMBL.map_chembl_target_to_uniprot_ids("CHEMBL2094253"))
#    print(QueryChEMBL.get_mechanisms_for_chembl_id("CHEMBL521"))
