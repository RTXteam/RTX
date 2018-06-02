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

# configure requests package to use the "orangeboard.sqlite" cache
requests_cache.install_cache('orangeboard')

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
        except BaseException as e:
            print(url, file=sys.stderr)
            print('%s received in QueryCOHD for URL: %s' % (e, url), file=sys.stderr)
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
        if not isinstance(chembl_id, str):
            return dict()

        res = QueryChEMBL.send_query_get(handler='target_prediction.json',
                                         url_suffix='molecule_chembl_id__exact=' + chembl_id + '&target_organism__exact=Homo%20sapiens')
        res_targets_dict = dict()
        if res is not None:
            target_predictions_list = res.get('target_predictions', None)
            if target_predictions_list is not None:
                for target_prediction in target_predictions_list:
#                    print(target_prediction)
                    target_uniprot_id = target_prediction.get('target_accession', None)
                    target_probability = target_prediction.get('probability', None)
                    if target_uniprot_id is not None:
                        # need to get the gene ID for this Uniprot ID
                        res_targets_dict[target_uniprot_id] = float(target_probability)
        return res_targets_dict

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
    def test():
        # print(QueryChEMBL.get_chembl_ids_for_drug('acetaminophen'))
        print(QueryChEMBL.get_target_uniprot_ids_for_chembl_id('CHEMBL304902'))
        
if __name__ == '__main__':
    QueryChEMBL.test()
    
    

