'''This module defines the class QueryCOHD. QueryCOHD class is designed to
communicate with the Columbia Open Health Dataset API (cohd.nsides.io) in order
obtain a "co-occurrence" probability between any two terms in medical records.

*   find_concept_ids(node_label)

    Description:
        search for OMOP concepts

    Args:
        node_label (str): The name of the concept to search for, e.g., "cancer" or "ibuprofen"

    Returns:
        list: a list of dictionary, which contains a concept ID and a concept name, or an empty list if no concept IDs
        could be obtained for the given label

        dictionary parameters:
            - 'concept_id' (str): a concept ID
            - 'concept_name' (str): a concept name

        example:
            [
                {
                    'concept_id': '192855',
                    'concept_name': 'Cancer in situ of urinary bladder'
                },
                {
                    'concept_id': '2008271',
                     'concept_name': 'Injection or infusion of cancer chemotherapeutic substance'
                }
            ]

*   get_paired_concept_freq(concept_id1, concept_id2)

    Description:
        Retrieves observed clinical frequencies of a pair of concepts.

    Args:
        concept_id1 (str): an OMOP id, e.g., "192855"
        concept_id2 (str): an OMOP id, e.g., "2008271"

    Returns:
        dictionary: a dictionary which contains a numeric frequency and a numeric concept count, or None if no frequency
         data could be obtained for the given pair of concept IDs

        dictionary parameters:
            - 'concept_count' (int): a concept count
            - 'concept_frequency' (double): a numeric frequency

        example:
            {
                'concept_count': 27,
                'concept_frequency': 5.066514896398214e-06
            }

*   get_individual_concept_freq(concept_id)

    Description:
        Retrieves observed clinical frequencies of individual concepts. Multiple concepts may be requested in a comma
        separated list.

    Args:
        concept_id (str): an OMOP id, e.g., "192855"

    Returns:
        dictionary: a dictionary which contains a numeric frequency and a numeric concept count

        dictionary parameters:
            - 'concept_count' (int): a concept count
            - 'concept_frequency' (double): a numeric frequency

        example:
            {
                'concept_count': 2042,
                'concept_frequency': 0.0003831786451275983
            }

*   get_associated_concept_domain_freq(concept_id, domain)

    Description:
        Retrieves observed clinical frequencies of all pairs of concepts given a concept id restricted by domain of
        the associated concept_id

    Args:
        concept_id (str): an OMOP id, e.g., "192855"
        domain (str): An OMOP domain id, e.g., "Condition", "Drug", "Procedure", etc.

    Returns:
        array: an array which contains frequency dictionaries, or an empty array if no data obtained

        example:
        [
            {
                "associated_concept_id": 19041324,
                "associated_concept_name": "Acetaminophen 325 MG Oral Tablet [Tylenol]",
                "concept_count": 380,
                "concept_frequency": 0.0000713065059493082,
                "concept_id": 192855
            },
            {
                "associated_concept_id": 40231925,
                "associated_concept_name": "Acetaminophen 325 MG / Oxycodone Hydrochloride 5 MG Oral Tablet",
                "concept_count": 356,
                "concept_frequency": 0.0000668029371525098,
                "concept_id": 192855
            }
        ]


Test Cases in
    [repo]/code/reasoningtool/kg-construction/tests/QueryCOHDTests.py

'''

__author__ = 'Deqing Qu'
__copyright__ = 'Oregon State University'
__credits__ = ['Deqing Qu', 'Stephen Ramsey']
__license__ = 'MIT'
__version__ = '0.1.0'
__maintainer__ = ''
__email__ = ''
__status__ = 'Prototype'

import requests
import requests_cache
import sys
import urllib.parse

# configure requests package to use the "orangeboard.sqlite" cache
requests_cache.install_cache('orangeboard')

class QueryCOHD:
    TIMEOUT_SEC = 120
    API_BASE_URL = 'http://cohd.nsides.io/api/v1'
    HANDLER_MAP = {
        'find_concept_id':                      'omop/findConceptIDs',
        'get_paired_concept_freq':              'frequencies/pairedConceptFreq',
        'get_individual_concept_freq':          'frequencies/singleConceptFreq',
        'get_associated_concept_domain_freq':   '/frequencies/associatedConceptDomainFreq'
    }

    @staticmethod
    def __access_api(handler, url_suffix):
        
        url = QueryCOHD.API_BASE_URL + '/' + handler + '?' + url_suffix
        
        try:
            res = requests.get(url, timeout=QueryCOHD.TIMEOUT_SEC)
        except requests.exceptions.Timeout:
            print(url, file=sys.stderr)
            print('Timeout in QueryCOHD for URL: ' + url, file=sys.stderr)
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

    # returns a list of dictionary, which contains a concept ID and a concept name, based on a single node label
    # like "acetaminophen" or "heart disease", or an empty list if no concept IDs could be obtained for the given label
    @staticmethod
    def find_concept_ids(node_label):
        if not isinstance(node_label, str):
            return None
        handler = QueryCOHD.HANDLER_MAP['find_concept_id']
        url_suffix = "q=" + urllib.parse.quote_plus(node_label)
        res_json = QueryCOHD.__access_api(handler, url_suffix)
        results_list = list()
        if res_json is not None:
            results = res_json.get('results', None)
            if results is not None and type(results) == list:
                results_list = results
                for obj in results:
                    obj['concept_id'] = str(obj['concept_id'])
        return results_list

    # returns a dictionary, which contains a numeric frequency and a numeric concept count, for pairewise occurrence of
    # the two concepts, or None if no frequency data could be obtained for the given pair of concept IDs
    @staticmethod
    def get_paired_concept_freq(concept_id1, concept_id2):
        if not isinstance(concept_id1, str) or not isinstance(concept_id2, str):
            return None
        handler = QueryCOHD.HANDLER_MAP['get_paired_concept_freq']
        url_suffix = "q=" + urllib.parse.quote_plus(concept_id1 + ',' + concept_id2)
        res_json = QueryCOHD.__access_api(handler, url_suffix)
        results_dict = None
        if res_json is not None:
            results = res_json.get('results', None)
            if results is not None and type(results) == list and len(results) > 0:
                results_dict = results[0]
                del results_dict['concept_id_1']
                del results_dict['concept_id_2']
        return results_dict

    # returns a dictionary, which contains a numeric frequency and a numeric concept count, for clinical frequency of
    # individual concept, or none if no data could be obtained for the concept ID
    @staticmethod
    def get_individual_concept_freq(concept_id):
        if not isinstance(concept_id, str):
            return None
        handler = QueryCOHD.HANDLER_MAP['get_individual_concept_freq']
        url_suffix = "q=" + urllib.parse.quote_plus(concept_id)
        res_json = QueryCOHD.__access_api(handler, url_suffix)
        results_dict = None
        if res_json is not None:
            results = res_json.get('results', None)
            if results is not None and type(results) == list and len(results) > 0:
                results_dict = results[0]
                del results_dict['concept_id']
        return results_dict


    @staticmethod
    def get_associated_concept_domain_freq(concept_id, domain):
        if not isinstance(concept_id, str) or not isinstance(domain, str):
            return []
        handler = QueryCOHD.HANDLER_MAP['get_associated_concept_domain_freq']
        url_suffix = 'concept_id=' + concept_id + '&domain=' + domain
        res_json = QueryCOHD.__access_api(handler, url_suffix)
        results_array = []
        if res_json is not None:
            results_array = res_json.get('results', [])
        return results_array


if __name__ == '__main__':
    print(QueryCOHD.find_concept_ids("cancer"))
    print(QueryCOHD.get_paired_concept_freq('192855', '2008271'))
    print(QueryCOHD.get_individual_concept_freq('2008271'))
    print(QueryCOHD.get_associated_concept_domain_freq('192855', 'drug'))