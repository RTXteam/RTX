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
import sys

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
        status_code = res.status_code
        if status_code != 200:
            print(url, file=sys.stderr)
            print('Status code ' + str(status_code) + ' for url: ' + url, file=sys.stderr)
            return None
        return res.json()

    @staticmethod
    def get_chembl_ids_for_drug(drug_name):
        res = QueryChEMBL.send_query_get(handler='compound_record.json',
                                         url_suffix='compound_name__iexact=' + urllib.parse.quote(drug_name, safe=''))
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
        res = QueryChEMBL.send_query_get(handler='target_prediction.json',
                                         url_suffix='molecule_chembl_id__exact=' + chembl_id + '&target_organism__exact=Homo%20sapiens')
        res_targets_set = set()
        if res is not None:
            target_predictions_list = res.get('target_predictions', None)
            if target_predictions_list is not None:
                for target_prediction in target_predictions_list:
                    target_uniprot_id = target_prediction.get('target_accession', None)
                    if target_uniprot_id is not None:
                        # need to get the gene ID for this Uniprot ID
                        res_targets_set.add(target_uniprot_id)
        return res_targets_set

    @staticmethod
    def get_target_uniprot_ids_for_drug(drug_name):
        chembl_ids_for_drug = QueryChEMBL.get_chembl_ids_for_drug(drug_name)
        res_uniprot_ids = set()
        for chembl_id in chembl_ids_for_drug:
            res_uniprot_ids |= QueryChEMBL.get_target_uniprot_ids_for_chembl_id(chembl_id)
        return res_uniprot_ids
    
    @staticmethod
    def test():
        print(QueryChEMBL.get_target_uniprot_ids_for_drug('clothiapine'))
        
if __name__ == '__main__':
    QueryChEMBL.test()
    
    
    

