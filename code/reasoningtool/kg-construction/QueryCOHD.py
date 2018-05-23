'''This module defines the class QueryCOHD. QueryCOHD class is designed to
communicate with the Columbia Open Health Dataset API (cohd.nsides.io) in order
obtain a "co-occurrence" probability between any two terms in medical records.

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
    API_BASE_URL = 'http://cohd.nsides.io/api'
    HANDLER_MAP = {
        'find_concept_id':                      'omop/findConceptIDs',
        'get_paired_concept_freq':              'frequencies/pairedConceptFreq',
        'get_individual_concept_freq':          'frequencies/singleConceptFreq',
        'get_associated_concept_domain_freq':   'frequencies/associatedConceptDomainFreq'
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

    @staticmethod
    def find_concept_ids(node_label, domain, dataset_id=1):
        """search for OMOP concepts by name

        Args:
            node_label (str): The name of the concept to search for, e.g., "cancer" or "ibuprofen"

            domain (str): The domain (e.g., "Condition", "Drug", "Procedure") to restrict the search to. If not
                specified, the search will be unrestricted.

            dataset_id (int): The dataset to reference when sorting concepts by their frequency. Default: 5-year
                dataset (1).
        Returns:
            list: a list of dictionary, including names and IDs, or an empty list if no concept IDs could be obtained
                for the given label

            example:
                [
                    {
                        "concept_class_id": "Clinical Finding",
                        "concept_code": "212602006",
                        "concept_count": 0,
                        "concept_id": 4059406,
                        "concept_name": "Ibuprofen poisoning",
                        "domain_id": "Condition",
                        "vocabulary_id": "SNOMED"
                    },
                    {
                        "concept_class_id": "Clinical Finding",
                        "concept_code": "218613000",
                        "concept_count": 0,
                        "concept_id": 4329188,
                        "concept_name": "Adverse reaction to ibuprofen",
                        "domain_id": "Condition",
                        "vocabulary_id": "SNOMED"
                    },
                    ...
                ]
        """
        if not isinstance(node_label, str) or not isinstance(dataset_id, int) or not isinstance(domain, str):
            return []
        handler = QueryCOHD.HANDLER_MAP['find_concept_id']
        url_suffix = "q=" + node_label + "&dataset_id=" + str(dataset_id) + "&domain=" + domain
        res_json = QueryCOHD.__access_api(handler, url_suffix)
        results_list = []
        if res_json is not None:
            results = res_json.get('results', None)
            if results is not None and type(results) == list:
                results_list = results
        return results_list

    @staticmethod
    def get_paired_concept_freq(concept_id1, concept_id2, dataset_id=1):
        """Retrieves observed clinical frequencies of a pair of concepts.

        Args:
            concept_id1 (str): an OMOP id, e.g., "192855"

            concept_id2 (str): an OMOP id, e.g., "2008271"

            dataset_id (str): The dataset_id of the dataset to query. Default dataset is the 5-year dataset

        Returns:
            dictionary: a dictionary which contains a numeric frequency and a numeric concept count, or None if no
            frequency data could be obtained for the given pair of concept IDs

            example:
                {
                    "concept_count": 10,
                    "concept_frequency": 0.000005585247351056813,
                    "concept_id_1": 192855,
                    "concept_id_2": 2008271,
                    "dataset_id": 1
                }
        """
        if not isinstance(concept_id1, str) or not isinstance(concept_id2, str) or not isinstance(dataset_id, int):
            return {}
        handler = QueryCOHD.HANDLER_MAP['get_paired_concept_freq']
        url_suffix = "q=" + urllib.parse.quote_plus(concept_id1 + ',' + concept_id2) + "&dataset_id=" + str(dataset_id)
        res_json = QueryCOHD.__access_api(handler, url_suffix)
        results_dict = {}
        if res_json is not None:
            results = res_json.get('results', None)
            if results is not None and type(results) == list and len(results) > 0:
                results_dict = results[0]
        return results_dict

    @staticmethod
    def get_individual_concept_freq(concept_id, dataset_id=1):
        """Retrieves observed clinical frequencies of individual concepts.

        Args:
            concept_id (str): an OMOP id, e.g., "192855"

            dataset_id (str): The dataset_id of the dataset to query. Default dataset is the 5-year dataset

        Returns:
            dictionary: a dictionary which contains a numeric frequency and a numeric concept count

            example:
                {
                    "concept_count": 368,
                    "concept_frequency": 0.0002055371025188907,
                    "concept_id": 192855,
                    "dataset_id": 1
                }
        """
        if not isinstance(concept_id, str):
            return {}
        handler = QueryCOHD.HANDLER_MAP['get_individual_concept_freq']
        url_suffix = "q=" + urllib.parse.quote_plus(concept_id) + "&dataset_id=" + str(dataset_id)
        res_json = QueryCOHD.__access_api(handler, url_suffix)
        results_dict = {}
        if res_json is not None:
            results = res_json.get('results', None)
            if results is not None and type(results) == list and len(results) > 0:
                results_dict = results[0]
        return results_dict


    @staticmethod
    def get_associated_concept_domain_freq(concept_id, domain, dataset_id=1):
        """Retrieves observed clinical frequencies of all pairs of concepts given a concept id restricted by domain of
        the associated concept_id

        Args:
            concept_id (str): an OMOP id, e.g., "192855"

            domain (str): An OMOP domain id, e.g., "Condition", "Drug", "Procedure", etc.

            dataset_id (int): The dataset_id of the dataset to query. Default dataset is the 5-year dataset (1).

        Returns:
            array: an array which contains frequency dictionaries, or an empty array if no data obtained

            example:
            [
                {
                    "associated_concept_id": 2213283,
                    "associated_concept_name": "Level IV - Surgical pathology, gross and microscopic examination Abortion - spontaneous/missed Artery, biopsy Bone marrow, biopsy Bone exostosis Brain/meninges, other than for tumor resection Breast, biopsy, not requiring microscopic evaluation of surgica",
                    "associated_domain_id": "Procedure",
                    "concept_count": 302,
                    "concept_frequency": 0.00016867447000191573,
                    "concept_id": 192855,
                    "dataset_id": 1
                },
                {
                    "associated_concept_id": 2211361,
                    "associated_concept_name": "Radiologic examination, chest, 2 views, frontal and lateral",
                    "associated_domain_id": "Procedure",
                    "concept_count": 257,
                    "concept_frequency": 0.00014354085692216007,
                    "concept_id": 192855,
                    "dataset_id": 1
                },
                ...
            ]
        """
        if not isinstance(concept_id, str) or not isinstance(domain, str) or not isinstance(dataset_id, int):
            return []
        handler = QueryCOHD.HANDLER_MAP['get_associated_concept_domain_freq']
        url_suffix = 'concept_id=' + concept_id + '&domain=' + domain
        res_json = QueryCOHD.__access_api(handler, url_suffix)
        results_array = []
        if res_json is not None:
            results_array = res_json.get('results', [])
        return results_array


if __name__ == '__main__':
    print(QueryCOHD.find_concept_ids("ibuprofen", "Condition", 1))
    print(QueryCOHD.find_concept_ids("ibuprofen", "Condition"))
    print(QueryCOHD.get_paired_concept_freq('192855', '2008271', 1))
    print(QueryCOHD.get_individual_concept_freq('192855'))
    print(QueryCOHD.get_associated_concept_domain_freq('192855', 'Procedure', 1))