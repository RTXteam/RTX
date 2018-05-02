'''This module defines the class QueryCOHD. QueryCOHD class is designed to
communicate with the Columbia Open Health Dataset API (cohd.nsides.io) in order
obtain a "co-occurrence" probability between any two terms in medical records.

*   find_concept_ids(node_label)
    Description:
        search for OMOP concepts
    Args:
        node_label (string): The name of the concept to search for, e.g., "cancer" or "ibuprofen"
    Returns:
        set: a set of concept IDs, or an empty set if no concept IDs could be obtained for the given label

*   get_paired_concept_freq(concept_id1, concept_id2)
    Description:
        Retrieves observed clinical frequencies of a pair of concepts.
    Args:
        concept_id1 (string): an OMOP id, e.g., "192855"
        concept_id2 (string): an OMOP id, e.g., "2008271"
    Returns:
        double: a numeric frequency for pairewise occurrence of the two concepts, or None if no frequency data could be
        obtained for the given pair of concept IDs

*   get_individual_concept_freq(concept_id)
    Description:
        Retrieves observed clinical frequencies of individual concepts. Multiple concepts may be requested in a comma
        separated list.
    Args:
        concept_id (string): an OMOP id, e.g., "192855"
    Returns:
        double: returns a numeric frequency for clinical frequency of individual concept, or none if no frequency data
        could be obtained for the concept ID

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
import sys
import urllib.parse


class QueryCOHD:
    TIMEOUT_SEC = 120
    API_BASE_URL = 'http://cohd.nsides.io/api/v1'
    HANDLER_MAP = {
        'find_concept_id':             'omop/findConceptIDs',
        'get_paired_concept_freq':     'frequencies/pairedConceptFreq',
        'get_individual_concept_freq': 'frequencies/singleConceptFreq'
    }

    @staticmethod
    def __access_api(handler, url_suffix):
        
        url = QueryCOHD.API_BASE_URL + '/' + handler + '?q=' + url_suffix
        
        try:
            res = requests.get(url, timeout=QueryCOHD.TIMEOUT_SEC)
        except requests.exceptions.Timeout:
            print(url, file=sys.stderr)
            print('Timeout in QueryCOHD for URL: ' + url, file=sys.stderr)
            return None
        status_code = res.status_code
        if status_code != 200:
            print(url, file=sys.stderr)
            print('Status code ' + str(status_code) + ' for url: ' + url, file=sys.stderr)
            return None
        return res.json()

    # returns a set of integer concept IDs, based on a single node label like "acetaminophen" or "heart disease"
    # or an empty set if no concept IDs could be obtained for the given label

    @staticmethod
    def find_concept_ids(node_label):
        if not isinstance(node_label, str):
            return None
        handler = QueryCOHD.HANDLER_MAP['find_concept_id']
        url_suffix = urllib.parse.quote_plus(node_label)
        res_json = QueryCOHD.__access_api(handler, url_suffix)
        result_set = set()
        if res_json is not None:
            results = res_json.get('results', None)
            if results is not None and type(results) == list:
                for results_dict in results:
                    results_id = results_dict.get("concept_id", None)
                    if results_id is not None:
                        result_set.add(str(results_id))
        return result_set

    # returns a numeric frequency for pairewise occurrence of the two concepts,
    # or none if no frequency data could be obtained for the given pair of concept IDs
    @staticmethod
    def get_paired_concept_freq(concept_id1, concept_id2):
        if not isinstance(concept_id1, str) or not isinstance(concept_id2, str):
            return None
        handler = QueryCOHD.HANDLER_MAP['get_paired_concept_freq']
        url_suffix = urllib.parse.quote_plus(concept_id1 + ',' +
                                             concept_id2)
        res_json = QueryCOHD.__access_api(handler, url_suffix)
        freq = None
        if res_json is not None:
            results = res_json.get('results', None)
            if results is not None and type(results) == list and len(results) > 0:
                if 'concept_frequency' in results[0].keys():
                    freq = results[0]["concept_frequency"]
        return freq

    # returns a numeric frequency for clinical frequency of individual concept,
    # or none if no frequency data could be obtained for the concept ID
    @staticmethod
    def get_individual_concept_freq(concept_id):
        if not isinstance(concept_id, str):
            return None
        handler = QueryCOHD.HANDLER_MAP['get_individual_concept_freq']
        url_suffix = urllib.parse.quote_plus(concept_id)
        res_json = QueryCOHD.__access_api(handler, url_suffix)
        freq = None
        if res_json is not None:
            results = res_json.get('results', None)
            if results is not None and type(results) == list and len(results) > 0:
                if 'concept_frequency' in results[0].keys():
                    freq = results[0]["concept_frequency"]
        return freq

if __name__ == '__main__':
    print(QueryCOHD.find_concept_ids("cancer"))
    print(QueryCOHD.get_paired_concept_freq('192855', '2008271'))
    print(QueryCOHD.get_individual_concept_freq('192855'))
