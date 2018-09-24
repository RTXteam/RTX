__author__ = 'Stephen Ramsey'
__copyright__ = 'Oregon State University'
__credits__ = ['Stephen Ramsey', 'Finn Womack']
__license__ = 'MIT'
__version__ = '0.1.0'
__maintainer__ = ''
__email__ = ''
__status__ = 'Prototype'

import urllib
import pandas
import requests
import sys
import time
import math
from io import StringIO
import re
import os
import CachedMethods
import requests_cache
import json


class QueryPubChem:
    API_BASE_URL = 'https://pubchem.ncbi.nlm.nih.gov/rest/pug'
    TIMEOUT_SEC = 120
    HANDLER_MAP = {
        'get_pubchem_cid':      'substance/sid/{sid}/JSON',
        'get_description_url':  'compound/cid/{cid}/description/JSON'
    }

    @staticmethod
    def __access_api(handler):
        url = QueryPubChem.API_BASE_URL + '/' + handler
        # print(url)
        try:
            res = requests.get(url, timeout=QueryPubChem.TIMEOUT_SEC)
        except requests.exceptions.Timeout:
            print(url, file=sys.stderr)
            print('Timeout in QueryPubChem for URL: ' + url, file=sys.stderr)
            return None
        except KeyboardInterrupt:
            sys.exit(0)
        except BaseException as e:
            print(url, file=sys.stderr)
            print('%s received in QueryPubChem for URL: %s' % (e, url), file=sys.stderr)
            return None
        status_code = res.status_code
        if status_code != 200:
            print(url, file=sys.stderr)
            print('Status code ' + str(status_code) + ' for url: ' + url, file=sys.stderr)
            return None
        return res.json()

    @staticmethod
    def send_query_get(handler, url_suffix):
        url = QueryPubChem.API_BASE_URL + '/' + handler + '/' + url_suffix
        # print(url)
        try:
            res = requests.get(url,
                               timeout=QueryPubChem.TIMEOUT_SEC)
        except requests.exceptions.Timeout:
            print(url, file=sys.stderr)
            print('Timeout in QueryPubChem for URL: ' + url, file=sys.stderr)
            return None
        except BaseException as e:
            print(url, file=sys.stderr)
            print('%s received in QueryPubChem for URL: %s' % (e, url), file=sys.stderr)
            return None
        status_code = res.status_code
        if status_code != 200:
            print(url, file=sys.stderr)
            print('Status code ' + str(status_code) + ' for url: ' + url, file=sys.stderr)
            return None
        return res.json()

    @staticmethod
    def get_chembl_ids_for_drug(drug_name):
        drug_name_safe = urllib.parse.quote(drug_name, safe='')
        res = QueryPubChem.send_query_get(handler='compound/name',
                                          url_suffix=drug_name_safe + '/synonyms/JSON')
        res_chembl_set = set()
        if res is not None:
            information_list_dict = res.get('InformationList', None)
            if information_list_dict is not None:
                information_list = information_list_dict.get('Information', None)
                if information_list is not None:
                    for information_dict in information_list:
                        synonyms = information_dict.get('Synonym', None)
                        if synonyms is not None:
                            for syn in synonyms:
                                if syn.startswith('CHEMBL'):
                                    res_chembl_set.add(syn)
                                    # res_chembl_set.add('ChEMBL:' + syn.replace('CHEMBL', ''))
        return res_chembl_set

    # @staticmethod
    # def test():
    #     print(QueryPubChem.get_chembl_ids_for_drug('gne-493'))
    #     print(QueryChEMBL.get_target_uniprot_ids_for_drug('clothiapine'))

    @staticmethod
    # @CachedMethods.register
    def get_pubchem_id_for_chembl_id(chembl_id):
        """This takes a chembl id and then looks up the corresponding pubchem id from a pre-generated .tsv

        NOTE: pubchem-chembl mappings .tsv generated using https://pubchem.ncbi.nlm.nih.gov/idexchange/idexchange.cgi
        it took ~3 or so seconds to map all ids in the KG (2226 ids) and not all ids were successful (missed 204 terms -> ~91% success rate)
        """
        dir_path = os.path.dirname(os.path.realpath(__file__))
        df = pandas.read_csv(dir_path + '/chemblMap.tsv', sep='\t', index_col=0, header=None)
        try:
            ans = df.loc[chembl_id].iloc[0]
        except KeyError:
            return None
        if math.isnan(ans):
            return None
        else:
            return str(int(ans))

    @staticmethod
    # @CachedMethods.register
    def get_pubmed_id_for_pubchem_id(pubchem_id):
        """
        This takes a PubChem id and then gets the PMIDs for articles on PubMed from PubChem which include this entity.
        """
        if not isinstance(pubchem_id, str):
            return None

        url = 'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/' + str(pubchem_id) + '/xrefs/PubMedID/JSON'
        try:
            r = requests.get(url, timeout=10)
        except requests.exceptions.Timeout:
            print(url, file=sys.stderr)
            print('Timeout in QueryPubChem for URL: ' + url, file=sys.stderr)
            return None
        except BaseException as e:
            print(url, file=sys.stderr)
            print('%s received in QueryPubChem for URL: %s' % (e, url), file=sys.stderr)
            return None
        if r is not None:
            if 'Fault' in r.json().keys():
                return None
            else:
                ans = [str(x) + '[uid]' for x in r.json()['InformationList']['Information'][0]['PubMedID']]
                return ans
        else:
            return None

    @staticmethod
    def get_pubchem_cid(pubchem_sid):
        pubchem_cid = None
        if not isinstance(pubchem_sid, str):
            return pubchem_cid
        handler = QueryPubChem.HANDLER_MAP['get_pubchem_cid'].format(sid=pubchem_sid)
        res = QueryPubChem.__access_api(handler)
        if res is not None:
            if 'PC_Substances' in res.keys():
                substance = res['PC_Substances'][0]
                if len(substance) > 0:
                    if 'compound' in substance.keys():
                        compounds = substance['compound']
                        if len(compounds) > 1:
                            compound = compounds[1]
                            if 'id' in compound.keys():
                                obj = compound['id']
                                if 'id' in obj.keys():
                                    id_obj = obj['id']
                                    if 'cid' in id_obj.keys():
                                        pubchem_cid = str(id_obj['cid'])
        return pubchem_cid


    @staticmethod
    def get_description_url_from_cid(pubchem_cid):
        """	query the description URL from HMDB
        Args:
            pubchem_cid (str): PubChem CID, e.g. 123689
        Returns:
            desc_url (str): the URL of HMDB website, which contains the description of the compound
        """
        res_url = None
        if not isinstance(pubchem_cid, str):
            return res_url
        handler = QueryPubChem.HANDLER_MAP['get_description_url'].format(cid=pubchem_cid)
        res = QueryPubChem.__access_api(handler)
        if res is not None:
            if 'InformationList' in res.keys():
                info_list = res['InformationList']
                if 'Information' in info_list.keys():
                    infos = info_list['Information']
                    for info in infos:
                        if 'DescriptionSourceName' in info.keys() and 'DescriptionURL' in info.keys():
                            if info['DescriptionSourceName'] == "Human Metabolome Database (HMDB)":
                                return info['DescriptionURL']
        return res_url


    @staticmethod
    def get_description_url(pubchem_sid):
        res_url = None
        if not isinstance(pubchem_sid, str):
            return res_url
        pubchem_cid = QueryPubChem.get_pubchem_cid(pubchem_sid)
        if pubchem_cid is not None:
            res_url = QueryPubChem.get_description_url_from_cid(pubchem_cid)
        return res_url

if __name__ == '__main__':
    # print(QueryPubChem.get_chembl_ids_for_drug('gne-493'))
    # print(QueryPubChem.get_pubchem_id_for_chembl_id('CHEMBL521'))
    # print(QueryPubChem.get_pubchem_id_for_chembl_id('chembl521'))
    # print(QueryPubChem.get_pubchem_id_for_chembl_id('3400'))
    # print(QueryPubChem.get_pubmed_id_for_pubchem_id('3672'))
    # print(QueryPubChem.get_pubmed_id_for_pubchem_id('3500'))
    # print(QueryPubChem.get_pubmed_id_for_pubchem_id('3400'))
    print(QueryPubChem.get_description_url('6921'))
    print(QueryPubChem.get_description_url('3500'))
    print(QueryPubChem.get_description_url('3400'))
    print(QueryPubChem.get_description_url(3400))
    print(QueryPubChem.get_description_url('3324'))

