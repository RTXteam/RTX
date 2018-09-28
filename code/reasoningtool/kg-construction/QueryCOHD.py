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

# configure requests package to use the "QueryCOHD.sqlite" cache
# requests_cache.install_cache('QueryCOHD')


class QueryCOHD:
    TIMEOUT_SEC = 120
    API_BASE_URL = 'http://cohd.nsides.io/api'
    HANDLER_MAP = {
        'find_concept_id':                      'omop/findConceptIDs',
        'get_paired_concept_freq':              'frequencies/pairedConceptFreq',
        'get_individual_concept_freq':          'frequencies/singleConceptFreq',
        'get_associated_concept_domain_freq':   'frequencies/associatedConceptDomainFreq',
        'get_concepts':                         'omop/concepts',
        'get_xref_from_OMOP':                   'omop/xrefFromOMOP',
        'get_xref_to_OMOP':                     'omop/xrefToOMOP',
        'get_map_from_standard_concept_id':     'omop/mapFromStandardConceptID',
        'get_map_to_standard_concept_id':       'omop/mapToStandardConceptID',
        'get_vocabularies':                     'omop/vocabularies',
        'get_associated_concept_freq':          'frequencies/associatedConceptFreq',
        'get_most_frequent_concepts':           'frequencies/mostFrequentConcepts',
        'get_chi_square':                       'association/chiSquare',
        'get_obs_exp_ratio':                    'association/obsExpRatio',
        'get_relative_frequency':               'association/relativeFrequency',
        'get_datasets':                         'metadata/datasets',
        'get_domain_counts':                    'metadata/domainCounts',
        'get_domain_pair_counts':               'metadata/domainPairCounts',
        'get_patient_count':                    'metadata/patientCount',
        'get_concept_ancestors':                '/omop/conceptAncestors',
        'get_concept_descendants':              '/omop/conceptDescendants'
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
        except KeyboardInterrupt:
            sys.exit(0)
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
    def find_concept_ids(node_label, domain="", dataset_id=1, min_count=1):
        """search for OMOP concepts by name

        Args:
            node_label (str): The name of the concept to search for, e.g., "cancer" or "ibuprofen"

            domain (str): The domain (e.g., "Condition", "Drug", "Procedure") to restrict the search to. If not
                specified, the search will be unrestricted.

            dataset_id (int): The dataset to reference when sorting concepts by their frequency. Default: 5-year
                dataset (1).

            min_count (int): The minimum concept count (inclusive) to include a concept in the search results. Setting
             the min_count to 0 will cause findConceptIDs to return all matching standard OMOP concepts (this can be
             slow). Setting the min_count to 1 will cause findConceptIDs to only return concepts with count data
             (much faster). Default: 1.

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
        url_suffix = "q=" + node_label + "&dataset_id=" + str(dataset_id) + "&min_count=" + str(min_count)
        if domain != "":
            url_suffix += "&domain=" + domain
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
        url_suffix = 'concept_id=' + concept_id + '&domain=' + domain + '&dataset_id=' + str(dataset_id)
        res_json = QueryCOHD.__access_api(handler, url_suffix)
        results_array = []
        if res_json is not None:
            results_array = res_json.get('results', [])
        return results_array

    @staticmethod
    def get_xref_from_OMOP(concept_id, mapping_targets, distance=2):
        """Cross-reference from an ontology to OMOP standard concepts

        Attempts to map a concept from an external ontology to an OMOP standard concept ID using the EMBL-EBI
        Ontology Xref Service (OxO): https://www.ebi.ac.uk/spot/oxo/index. This method maps from the OMOP standard
        concept to an intermediate vocabulary included is OxO (ICD9CM, ICD10CM, SNOMEDCT, and MeSH), then uses the OxO
        API to map to other ontologies. Multiple mappings may be returned. Results are sorted by total_distance (OxO
        distance + OMOP distance) in ascending order.

        Args:
            concept_id (str): OMOP standard concept_id to map, e.g., "192855"

            mapping_targets (str): Target ontologies for OxO. Comma separated target prefixes, e.g., "DOID, UMLS"

            distance (int): Mapping distance for OxO. Note: this is the distance used in the OxO API to map from an
            ICD9CM, ICD10CM, SNOMEDCT, or MeSH concept to the desired ontology. One additional step may be taken by the
            COHD API to map to the OMOP standard concept to ICD9CM, ICD10CM, SNOMEDCT, or MeSH. Default: 2.

        Returns:
            array: an array which contains cross-reference dictionaries, or an empty array if no data obtained.

            example:
            [
                {
                  "intermediate_omop_concept_code": "92546004",
                  "intermediate_omop_concept_id": 192855,
                  "intermediate_omop_concept_name": "Cancer in situ of urinary bladder",
                  "intermediate_omop_vocabulary_id": "SNOMED",
                  "intermediate_oxo_curie": "SNOMEDCT:92546004",
                  "intermediate_oxo_label": "Cancer in situ of urinary bladder",
                  "omop_distance": 0,
                  "oxo_distance": 1,
                  "source_omop_concept_code": "92546004",
                  "source_omop_concept_id": 192855,
                  "source_omop_concept_name": "Cancer in situ of urinary bladder",
                  "source_omop_vocabulary_id": "SNOMED",
                  "target_curie": "UMLS:C0154091",
                  "target_label": "Cancer in situ of urinary bladder",
                  "total_distance": 1
                },
                {
                  "intermediate_omop_concept_code": "D09.0",
                  "intermediate_omop_concept_id": 35206494,
                  "intermediate_omop_concept_name": "Carcinoma in situ of bladder",
                  "intermediate_omop_vocabulary_id": "ICD10CM",
                  "intermediate_oxo_curie": "ICD10CM:D09.0",
                  "intermediate_oxo_label": "Carcinoma in situ of bladder",
                  "omop_distance": 1,
                  "oxo_distance": 1,
                  "source_omop_concept_code": "92546004",
                  "source_omop_concept_id": 192855,
                  "source_omop_concept_name": "Cancer in situ of urinary bladder",
                  "source_omop_vocabulary_id": "SNOMED",
                  "target_curie": "UMLS:C0154091",
                  "target_label": "Cancer in situ of urinary bladder",
                  "total_distance": 2
                },
                ...
            ]
        """
        if not isinstance(concept_id, str) or not isinstance(mapping_targets, str) or not isinstance(distance, int):
            return []
        handler = QueryCOHD.HANDLER_MAP['get_xref_from_OMOP']
        url_suffix = 'concept_id=' + concept_id + '&mapping_targets=' + mapping_targets + "&distance=" + str(distance)
        res_json = QueryCOHD.__access_api(handler, url_suffix)
        results_array = []
        if res_json is not None:
            results_array = res_json.get('results', [])
        return results_array

    @staticmethod
    def get_xref_to_OMOP(curie, distance=2):
        """Cross-reference from an ontology to OMOP standard concepts

        Attempts to map a concept from an external ontology to an OMOP standard concept ID using the EMBL-EBI
        Ontology Xref Service (OxO): https://www.ebi.ac.uk/spot/oxo/index. This method attempts to use OxO to map from
        the original ontology to an intermediate ontology that is included in OMOP (ICD9CM, ICD10CM, SNOMEDCT, and
        MeSH), then uses the OMOP mappings to the standard concepts. Multiple mappings may be returned. Results are
        sorted by total_distance (OxO distance + OMOP distance) in ascending order.

        Args:
            curie (str): Compacy URI (CURIE) of the concept to map, e.g., "DOID:8398"

            distance (str): Mapping distance for OxO. Note: this is the distance used in the OxO API to map from the
            original concept to an ICD9CM, ICD10CM, SNOMEDCT, or MeSH concept. One additional step may be taken by the
            COHD API to map to the OMOP standard concept. Default: 2.

        Returns:
            array: an array which contains cross-reference dictionaries, or an empty array if no data obtained.

            example:
            [
                {
                  "intermediate_oxo_id": "ICD9CM:715.3",
                  "intermediate_oxo_label": "",
                  "omop_concept_name": "Localized osteoarthrosis uncertain if primary OR secondary",
                  "omop_distance": 1,
                  "omop_domain_id": "Condition",
                  "omop_standard_concept_id": 72990,
                  "oxo_distance": 1,
                  "source_oxo_id": "DOID:8398",
                  "source_oxo_label": "osteoarthritis",
                  "total_distance": 2
                },
                {
                  "intermediate_oxo_id": "SNOMEDCT:396275006",
                  "intermediate_oxo_label": "Osteoarthritis",
                  "omop_concept_name": "Osteoarthritis",
                  "omop_distance": 0,
                  "omop_domain_id": "Condition",
                  "omop_standard_concept_id": 80180,
                  "oxo_distance": 2,
                  "source_oxo_id": "DOID:8398",
                  "source_oxo_label": "osteoarthritis",
                  "total_distance": 2
                },
                ...
            ]

        """
        if not isinstance(curie, str) or not isinstance(distance, int):
            return []
        handler = QueryCOHD.HANDLER_MAP['get_xref_to_OMOP']
        url_suffix = 'curie=' + curie + "&distance=" + str(distance)
        res_json = QueryCOHD.__access_api(handler, url_suffix)
        results_array = []
        if res_json is not None:
            results_array = res_json.get('results', [])
        return results_array

    @staticmethod
    def get_concepts(concept_ids):
        """Concept definitions from concept ID

        Returns the OMOP concept names and domains for the given list of concept IDs.

        Args:
            concept_ids (array): concept id array,  e.g., ["192855", "2008271"]

        Returns:
            array: an array which contains concept name, domain id and etc., or an empty array if no data obtained

            example:
            [
                {
                    "concept_class_id": "Clinical Finding",
                    "concept_code": "92546004",
                    "concept_id": 192855,
                    "concept_name": "Cancer in situ of urinary bladder",
                    "domain_id": "Condition",
                    "vocabulary_id": "SNOMED"
                },
                {
                    "concept_class_id": "4-dig billing code",
                    "concept_code": "99.25",
                    "concept_id": 2008271,
                    "concept_name": "Injection or infusion of cancer chemotherapeutic substance",
                    "domain_id": "Procedure",
                    "vocabulary_id": "ICD9Proc"
                },
                ...
              ]
        """
        if not isinstance(concept_ids, list) or len(concept_ids) <= 0:
            return []
        for concept_id in concept_ids:
            if not isinstance(concept_id, str):
                return []
        handler = QueryCOHD.HANDLER_MAP['get_concepts']
        concept_ids_str = concept_ids[0]
        for i, concept_id in enumerate(concept_ids):
            if i > 0:
                concept_ids_str += "," + concept_id
        url_suffix = 'q=' + urllib.parse.quote_plus(concept_ids_str)
        res_json = QueryCOHD.__access_api(handler, url_suffix)
        results_array = []
        if res_json is not None:
            results_array = res_json.get('results', [])
        return results_array

    @staticmethod
    def get_map_from_standard_concept_id(concept_id, vocabulary_id=""):
        """Map from a standard concept ID to concept code(s) in an external vocabulary.

        Uses the OMOP concept_relationship table to map from a standard concept ID (e.g., 72990) to concept code(s)
        (e.g., ICD9CM 715.3, 715.31, 715.32, etc.). An OMOP standard concept ID may map to many concepts in the external
         vocabulary.

        Args:
            concept_id (str): The standard OMOP concept id to map from, e.g., "72990"

            vocabulary_id (str): The vocabulary (e.g., "ICD9CM") to map to. If this parameter is not specified, the
            method will return mappings to any matching vocabularies. See /omop/vocabularies for the list of supported
            vocabularies.

        Returns:
            array: an array which contains mapping concepts from external vocabularies.

            example:
            [
                {
                  "concept_class_id": "4-dig nonbill code",
                  "concept_code": "715.3",
                  "concept_id": 44834979,
                  "concept_name": "Osteoarthrosis, localized, not specified whether primary or secondary",
                  "domain_id": "Condition",
                  "standard_concept": null,
                  "vocabulary_id": "ICD9CM"
                },
                {
                  "concept_class_id": "5-dig billing code",
                  "concept_code": "715.30",
                  "concept_id": 44828036,
                  "concept_name": "Osteoarthrosis, localized, not specified whether primary or secondary, site unspecified",
                  "domain_id": "Condition",
                  "standard_concept": null,
                  "vocabulary_id": "ICD9CM"
                },
                ...
            ]
        """
        if not isinstance(concept_id, str) or not isinstance(vocabulary_id, str):
            return []
        handler = QueryCOHD.HANDLER_MAP['get_map_from_standard_concept_id']
        url_suffix = 'concept_id=' + concept_id
        if vocabulary_id != "":
            url_suffix += "&vocabulary_id=" + vocabulary_id
        res_json = QueryCOHD.__access_api(handler, url_suffix)
        results_array = []
        if res_json is not None:
            results_array = res_json.get('results', [])
        return results_array

    @staticmethod
    def get_map_to_standard_concept_id(concept_code, vocabulary_id=""):
        """Map from a non-standard concept code to a standard OMOP concept ID.

        Args:
            concept_code (str): The concept code to map from, e.g., "715.3"

            vocabulary_id (str): The vocabulary (e.g., "ICD9CM") that the concept code belongs to. If this parameter is
            not specified, the method will return mappings from any source vocabulary with matching concept code. See
            /omop/vocabularies for the list of supported vocabularies.

        Returns:
            array: an array which contains standard OMOP concept IDs

            example:
             [
                {
                  "source_concept_code": "715.3",
                  "source_concept_id": 44834979,
                  "source_concept_name": "Osteoarthrosis, localized, not specified whether primary or secondary",
                  "source_vocabulary_id": "ICD9CM",
                  "standard_concept_id": 72990,
                  "standard_concept_name": "Localized osteoarthrosis uncertain if primary OR secondary",
                  "standard_domain_id": "Condition"
                },
                ...
             ]

        """
        if not isinstance(concept_code, str) or not isinstance(vocabulary_id, str):
            return []
        handler = QueryCOHD.HANDLER_MAP['get_map_to_standard_concept_id']
        url_suffix = 'concept_code=' + concept_code
        if vocabulary_id != "":
            url_suffix += "&vocabulary_id=" + vocabulary_id
        res_json = QueryCOHD.__access_api(handler, url_suffix)
        results_array = []
        if res_json is not None:
            results_array = res_json.get('results', [])
        return results_array

    @staticmethod
    def get_vocabularies():
        """List of vocabularies.

        List of vocabulary_ids. Useful if you need to use /omop/mapToStandardConceptID to map a concept code from a source vocabulary to the OMOP standard vocabulary.

        Returns:
            array: an array of all vocabularies

            example:
            [
                {
                  "vocabulary_id": "ABMS"
                },
                {
                  "vocabulary_id": "AMT"
                },
                {
                  "vocabulary_id": "APC"
                },
                ...
            ]
        """
        handler = QueryCOHD.HANDLER_MAP['get_vocabularies']
        url_suffix = ''
        res_json = QueryCOHD.__access_api(handler, url_suffix)
        results_array = []
        if res_json is not None:
            results_array = res_json.get('results', [])
        return results_array

    @staticmethod
    def get_associated_concept_freq(concept_id, dataset_id=1):
        """Retrieves observed clinical frequencies of all pairs of concepts given a concept id. Results are returned in
        descending order of paired concept count. Note that the largest paired concept counts are often dominated by
        associated concepts with high prevalence.

        Args:
            concept_id (str): An OMOP concept id, e.g., "192855"

            dataset_id (int): The dataset_id of the dataset to query. Default dataset is the 5-year dataset (1).

        Returns:
            array: an array which contains frequency dictionaries, or an empty array if no data obtained

            example:
            [
                {
                  "associated_concept_id": 2213216,
                  "associated_concept_name": "Cytopathology, selective cellular enhancement technique with interpretation (eg, liquid based slide preparation method), except cervical or vaginal",
                  "associated_domain_id": "Measurement",
                  "concept_count": 330,
                  "concept_frequency": 0.0001843131625848748,
                  "concept_id": 192855,
                  "dataset_id": 1
                },
                {
                  "associated_concept_id": 4214956,
                  "associated_concept_name": "History of clinical finding in subject",
                  "associated_domain_id": "Observation",
                  "concept_count": 329,
                  "concept_frequency": 0.00018375463784976913,
                  "concept_id": 192855,
                  "dataset_id": 1
                },
                ...
            ]
        """
        if not isinstance(concept_id, str) or not isinstance(dataset_id, int):
            return []
        handler = QueryCOHD.HANDLER_MAP['get_associated_concept_freq']
        url_suffix = 'q=' + concept_id + '&dataset_id=' + str(dataset_id)
        res_json = QueryCOHD.__access_api(handler, url_suffix)
        results_array = []
        if res_json is not None:
            results_array = res_json.get('results', [])
        return results_array

    @staticmethod
    def get_most_frequent_concepts(num, domain="", dataset_id=1):
        """Retrieves the most frequent concepts.

        Args:
            num (int): The number of concepts to retreieve, e.g., "10"

            domain (str): (Optional) The domain_id to restrict to, e.g., "Condition", "Drug", "Procedure"

            dataset_id (int): The dataset_id of the dataset to query. Default dataset is the 5-year dataset.

        Returns:
            array: an array which contains frequency dictionaries

            example:
            [
                {
                  "concept_class_id": "Clinical Finding",
                  "concept_count": 233790,
                  "concept_frequency": 0.1305774978203572,
                  "concept_id": 320128,
                  "concept_name": "Essential hypertension",
                  "dataset_id": 1,
                  "domain_id": "Condition",
                  "vocabulary_id": "SNOMED"
                },
                {
                  "concept_class_id": "Clinical Finding",
                  "concept_count": 152005,
                  "concept_frequency": 0.08489855235973907,
                  "concept_id": 77670,
                  "concept_name": "Chest pain",
                  "dataset_id": 1,
                  "domain_id": "Condition",
                  "vocabulary_id": "SNOMED"
                },
            ]
        """
        if not isinstance(num, int) or not isinstance(domain, str) or not isinstance(dataset_id, int) or num < 0:
            return []
        handler = QueryCOHD.HANDLER_MAP['get_most_frequent_concepts']
        url_suffix = 'q=' + str(num) + '&dataset_id=' + str(dataset_id)
        if domain != "":
            url_suffix += "&domain=" + domain
        res_json = QueryCOHD.__access_api(handler, url_suffix)
        results_array = []
        if res_json is not None:
            results_array = res_json.get('results', [])
        return results_array

    @staticmethod
    def get_chi_square(concept_id_1, concept_id_2='', domain='', dataset_id=1):
        """Returns the chi-square statistic and p-value between pairs of concepts. Results are returned in descending
        order of the chi-square statistic. Note that due to large sample sizes, the chi-square can become very large.

        The expected frequencies for the chi-square analysis are calculated based on the single concept frequencies and
        assuming independence between concepts. P-value is calculated with 1 DOF.

        This method has overloaded behavior based on the specified parameters:

            1. concept_id_1 and concept_id_2: Result for the pair (concept_id_1, concept_id_2)
            2. concept_id_1: Results for all pairs of concepts that include concept_id_1
            3. concept_id_1 and domain: Results for all pairs of concepts including concept_id_1 and where concept_id_2
                belongs to the specified domain

        Args:
            concept_id_1 (str): An OMOP concept id, e.g., "192855"

            concept_id_2 (str): An OMOP concept id, e.g., "2008271". If this parameter is specified, then the chi-square
                between concept_id_1 and concept_id_2 is returned. If this parameter is not specified, then a list of
                chi-squared results between concept_id_1 and other concepts is returned.

            domain (str): An OMOP domain id, e.g., "Condition", "Drug", "Procedure", etc., to restrict the associated
                concept (concept_id_2) to. If this parameter is not specified, then the domain is unrestricted.

            dataset_id (int): The dataset_id of the dataset to query. Default dataset is the 5-year dataset (1).

        Returns:
            array: an array of chi-square dictionaries.

            example:
            [
                {
                  "chi_square": 306.2816108187519,
                  "concept_id_1": 192855,
                  "concept_id_2": 2008271,
                  "dataset_id": 1,
                  "p-value": 1.4101531778039801e-68
                }
            ]

        """
        if not isinstance(concept_id_1, str) or not isinstance(concept_id_2, str) or not isinstance(domain, str) or not isinstance(dataset_id, int):
            return []
        handler = QueryCOHD.HANDLER_MAP['get_chi_square']
        url_suffix = 'concept_id_1=' + concept_id_1 + '&dataset_id=' + str(dataset_id)
        if domain != "":
            url_suffix += "&domain=" + domain
        if concept_id_2 != "":
            url_suffix += "&concept_id_2=" + concept_id_2
        res_json = QueryCOHD.__access_api(handler, url_suffix)
        results_array = []
        if res_json is not None:
            results_array = res_json.get('results', [])
        return results_array

    @staticmethod
    def get_obs_exp_ratio(concept_id_1, concept_id_2="", domain="", dataset_id=1):
        """Returns the natural logarithm of the ratio between the observed count and expected count. Expected count is
         calculated from the single concept frequencies and assuming independence between the concepts. Results are
         returned in descending order of ln_ratio.

        expected_count = Count_1_and_2 * num_patients / (Count_1 * Count_2)

        ln_ratio = ln( expected_count )

        This method has overloaded behavior based on the specified parameters:

            1. concept_id_1 and concept_id_2: Results for the pair (concept_id_1, concept_id_2)
            2. concept_id_1: Results for all pairs of concepts that include concept_id_1
            3. concept_id_1 and domain: Results for all pairs of concepts including concept_id_1 and where concept_id_2
                belongs to the specified domain

        Args:
            concept_id_1 (str): An OMOP concept id, e.g., "192855"

            concept_id_2 (str): An OMOP concept id, e.g., "2008271". If concept_id_2 is unspecified, then this method
                will return all pairs of concepts with concept_id_1.

            domain (str): An OMOP domain id, e.g., "Condition", "Drug", "Procedure", etc., to restrict the associated
                concept (concept_id_2) to. If this parameter is not specified, then the domain is unrestricted.

            dataset_id (int): The dataset_id of the dataset to query. Default dataset is the 5-year dataset (1).

        Returns:
            array: an array of dictionaries which contains  the natural logarithm of the ratio between the observed
                count and expected count

            example:
            [
                {
                  "concept_id_1": 192855,
                  "concept_id_2": 2008271,
                  "dataset_id": 1,
                  "expected_count": 0.3070724311632227,
                  "ln_ratio": 3.483256720088832,
                  "observed_count": 10
                }
            ]
        """
        if not isinstance(concept_id_1, str) or not isinstance(concept_id_2, str) or not isinstance(domain, str) or not isinstance(dataset_id, int):
            return []
        handler = QueryCOHD.HANDLER_MAP['get_obs_exp_ratio']
        url_suffix = 'concept_id_1=' + concept_id_1 + '&dataset_id=' + str(dataset_id)
        if domain != "":
            url_suffix += "&domain=" + domain
        if concept_id_2 != "":
            url_suffix += "&concept_id_2=" + concept_id_2
        res_json = QueryCOHD.__access_api(handler, url_suffix)
        results_array = []
        if res_json is not None:
            results_array = res_json.get('results', [])
        return results_array

    @staticmethod
    def get_relative_frequency(concept_id_1, concept_id_2="", domain="", dataset_id=1):
        """Relative frequency between pairs of concepts

        Calculates the relative frequency (i.e., conditional probability) between pairs of concepts. Results are
        returned in descending order of relative frequency. Note that due to the randomization of the counts, the
        calcaulted relative frequencies can exceed the limit of 1.0.

        Relative Frequency = Count_1_and_2 / Count_2

        This method has overloaded behavior based on the specified parameters:

            1. concept_id_1 and concept_id_2: Result for the pair (concept_id_1, concept_id_2)
            2. concept_id_1: Results for all pairs of concepts that include concept_id_1
            3. concept_id_1 and domain: Results for all pairs of concepts including concept_id_1 and where concept_id_2
                belongs to the specified domain

        Args:
            concept_id_1 (str): An OMOP concept id, e.g., "192855"

            concept_id_2 (str): An OMOP concept id, e.g., "2008271". If concept_id_2 is unspecified, then this method
                will return all pairs of concepts with concept_id_1.

            domain (str): An OMOP domain id, e.g., "Condition", "Drug", "Procedure", etc., to restrict the associated
                concept (concept_id_2) to. If this parameter is not specified, then the domain is unrestricted.

            dataset_id (int): The dataset_id of the dataset to query. Default dataset is the 5-year dataset (1).

        Returns:
            array: an array of dictionaries which contains the relative frequency between pairs of concepts

            example:
            [
                {
                  "concept_2_count": 1494,
                  "concept_id_1": 192855,
                  "concept_id_2": 2008271,
                  "concept_pair_count": 10,
                  "dataset_id": 1,
                  "relative_frequency": 0.006693440428380187
                }
            ]
        """
        if not isinstance(concept_id_1, str) or not isinstance(concept_id_2, str) or not isinstance(domain, str) or not isinstance(dataset_id, int):
            return []
        handler = QueryCOHD.HANDLER_MAP['get_relative_frequency']
        url_suffix = 'concept_id_1=' + concept_id_1 + '&dataset_id=' + str(dataset_id)
        if domain != "":
            url_suffix += "&domain=" + domain
        if concept_id_2 != "":
            url_suffix += "&concept_id_2=" + concept_id_2
        res_json = QueryCOHD.__access_api(handler, url_suffix)
        results_array = []
        if res_json is not None:
            results_array = res_json.get('results', [])
        return results_array

    @staticmethod
    def get_datasets():
        """Enumerates the datasets available in COHD

        Returns:
            array: a list of datasets, including dataset ID, name, and description.

            example:
                [
                    {'dataset_description': "Clinical data from 2013-2017. Each concept's count reflects "
                                                          "the use of that specific concept.",
                     'dataset_id': 1,
                     'dataset_name': "5-year non-hierarchical"},
                    {'dataset_description': "Clinical data from all years in the database. Each concept's"
                                                          " count reflects the use of that specific concept.",
                     'dataset_id': 2,
                     'dataset_name': "Lifetime non-hierarchical"},
                    {"dataset_description": "Clinical data from 2013-2017. Each concept's count includes"
                                                           " use of that concept and descendant concepts.",
                     "dataset_id": 3,
                     "dataset_name": "5-year hierarchical"}
                ]
        """
        handler = QueryCOHD.HANDLER_MAP['get_datasets']
        url_suffix = ''
        res_json = QueryCOHD.__access_api(handler, url_suffix)
        results_array = []
        if res_json is not None:
            results_array = res_json.get('results', [])
        return results_array

    @staticmethod
    def get_domain_counts(dataset_id=1):
        """The number of concepts in each domain

        Args:
            dataset_id (int): The dataset_id of the dataset to query. Default dataset is the 5-year dataset (1).

        Returns:
            array: a list of domains and the number of concepts in each domain.
        """
        if not isinstance(dataset_id, int) or dataset_id <= 0:
            return []
        handler = QueryCOHD.HANDLER_MAP['get_domain_counts']
        url_suffix = 'dataset_id=' + str(dataset_id)
        res_json = QueryCOHD.__access_api(handler, url_suffix)
        results_array = []
        if res_json is not None:
            results_array = res_json.get('results', [])
        return results_array

    @staticmethod
    def get_domain_pair_counts(dataset_id=1):
        """The number of pairs of concepts in each pair of domains

            Args:
                dataset_id (int): The dataset_id of the dataset to query. Default dataset is the 5-year dataset (1).

            Returns:
                array:  a list of pairs of domains and the number of pairs of concepts in each.
        """
        if not isinstance(dataset_id, int) or dataset_id <= 0:
            return []
        handler = QueryCOHD.HANDLER_MAP['get_domain_pair_counts']
        url_suffix = 'dataset_id=' + str(dataset_id)
        res_json = QueryCOHD.__access_api(handler, url_suffix)
        results_array = []
        if res_json is not None:
            results_array = res_json.get('results', [])
        return results_array

    @staticmethod
    def get_patient_count(dataset_id=1):
        """The number of patients in the dataset

            Args:
                dataset_id (int): The dataset_id of the dataset to query. Default dataset is the 5-year dataset (1).

            Returns:
                array:  a list of dictionaries which contains the number of patients

                example:
                [
                    {
                      "count": 1790431,
                      "dataset_id": 1
                    }
                ]
        """
        if not isinstance(dataset_id, int) or dataset_id <= 0:
            return {}
        handler = QueryCOHD.HANDLER_MAP['get_patient_count']
        url_suffix = 'dataset_id=' + str(dataset_id)
        res_json = QueryCOHD.__access_api(handler, url_suffix)
        results_dict = {}
        if res_json is not None:
            results = res_json.get('results', [])
            if results is not None and type(results) == list and len(results) > 0:
                results_dict = results[0]
        return results_dict

    @staticmethod
    def get_concept_ancestors(concept_id, vocabulary_id='', concept_class_id='', dataset_id=3):
        """Retrieves the given concept's hierarchical ancestors and their counts.

            Args:
                concept_id (str): An OMOP concept id, e.g., "19019073"

                vocabulary_id (int): The vocabulary_id to restrict ancestors to. For conditions, SNOMED and MedDRA are
                used. For drugs, RxNorm (only and ATC are used. For procedures, SNOMED, MedDRA, and ICD10PCS are used.
                Default: unrestricted.

                concept_class_id(str): The concept_class_id to restrict ancestors to. Only certain hierarchical concept_
                class_ids are used in each vocabuarly: ATC {ATC 1st, ATC 2nd, ATC 3rd, ATC 4th, ATC 5th}; MedDRA {PT,
                HLT, HLGT, SOC}; RxNorm {Ingredient, Clinical Drug Form, Clinical Drug Comp, Clinical Drug}.
                Default: unrestricted.

                dataset_id(int): The dataset_id to retrieve counts from. Default: 3 (5-year hierarchical data set)

            Returns:
                array:  a list of dictionaries which contains the number of patients

                example:
                [
                    {
                      "ancestor_concept_id": 19019073,
                      "concept_class_id": "Clinical Drug",
                      "concept_code": "197806",
                      "concept_count": 121104,
                      "concept_name": "Ibuprofen 600 MG Oral Tablet",
                      "domain_id": "Drug",
                      "max_levels_of_separation": 0,
                      "min_levels_of_separation": 0,
                      "standard_concept": "S",
                      "vocabulary_id": "RxNorm"
                    },
                    {
                      "ancestor_concept_id": 19081499,
                      "concept_class_id": "Clinical Drug Comp",
                      "concept_code": "316077",
                      "concept_count": 121202,
                      "concept_name": "Ibuprofen 600 MG",
                      "domain_id": "Drug",
                      "max_levels_of_separation": 1,
                      "min_levels_of_separation": 1,
                      "standard_concept": "S",
                      "vocabulary_id": "RxNorm"
                    },
                    ...
                ]
        """
        if not isinstance(concept_id, str) or not isinstance(vocabulary_id, str) \
            or not isinstance(concept_class_id, str) or not isinstance(dataset_id, int) or dataset_id <= 0:
            return []
        handler = QueryCOHD.HANDLER_MAP['get_concept_ancestors']
        url_suffix = 'concept_id=' + concept_id + '&dataset_id=' + str(dataset_id)
        if vocabulary_id != '':
            url_suffix += '&vocabulary_id=' + vocabulary_id
        if concept_class_id != '':
            url_suffix += '&concept_class_id=' + concept_class_id
        res_json = QueryCOHD.__access_api(handler, url_suffix)
        results_list = []
        if res_json is not None:
            results = res_json.get('results', [])
            if results is not None and type(results) == list and len(results) > 0:
                results_list = results
        return results_list

    @staticmethod
    def get_concept_descendants(concept_id, vocabulary_id='', concept_class_id='', dataset_id=3):
        """Retrieves the given concept's hierarchical ancestors and their counts.

            Args:
                concept_id (str): An OMOP concept id, e.g., "19019073"

                vocabulary_id (int): The vocabulary_id to restrict ancestors to. For conditions, SNOMED and MedDRA are
                used. For drugs, RxNorm (only and ATC are used. For procedures, SNOMED, MedDRA, and ICD10PCS are used.
                Default: unrestricted.

                concept_class_id(str): The concept_class_id to restrict ancestors to. Only certain hierarchical concept_
                class_ids are used in each vocabuarly: ATC {ATC 1st, ATC 2nd, ATC 3rd, ATC 4th, ATC 5th}; MedDRA {PT,
                HLT, HLGT, SOC}; RxNorm {Ingredient, Clinical Drug Form, Clinical Drug Comp, Clinical Drug}.
                Default: unrestricted.

                dataset_id(int): The dataset_id to retrieve counts from. Default: 3 (5-year hierarchical data set)

            Returns:
                array:  a list of dictionaries which contains the number of patients

                example:
                [
                    {
                      "concept_class_id": "Clinical Drug",
                      "concept_code": "197806",
                      "concept_count": 121104,
                      "concept_name": "Ibuprofen 600 MG Oral Tablet",
                      "descendant_concept_id": 19019073,
                      "domain_id": "Drug",
                      "max_levels_of_separation": 0,
                      "min_levels_of_separation": 0,
                      "standard_concept": "S",
                      "vocabulary_id": "RxNorm"
                    },
                    {
                      "concept_class_id": "Branded Drug",
                      "concept_code": "206913",
                      "concept_count": 14853,
                      "concept_name": "Ibuprofen 600 MG Oral Tablet [Ibu]",
                      "descendant_concept_id": 19033921,
                      "domain_id": "Drug",
                      "max_levels_of_separation": 0,
                      "min_levels_of_separation": 0,
                      "standard_concept": "S",
                      "vocabulary_id": "RxNorm"
                    },
                    ...
                ]
        """
        if not isinstance(concept_id, str) or not isinstance(vocabulary_id, str) \
            or not isinstance(concept_class_id, str) or not isinstance(dataset_id, int) or dataset_id <= 0:
            return []
        handler = QueryCOHD.HANDLER_MAP['get_concept_descendants']
        url_suffix = 'concept_id=' + concept_id + '&dataset_id=' + str(dataset_id)
        if vocabulary_id != '':
            url_suffix += '&vocabulary_id=' + vocabulary_id
        if concept_class_id != '':
            url_suffix += '&concept_class_id=' + concept_class_id
        res_json = QueryCOHD.__access_api(handler, url_suffix)
        results_list = []
        if res_json is not None:
            results = res_json.get('results', [])
            if results is not None and type(results) == list and len(results) > 0:
                results_list = results
        return results_list


# if __name__ == '__main__':
    # print(QueryCOHD.find_concept_ids("cancer", "Condition", 1))
    # print(QueryCOHD.find_concept_ids("cancer", "Condition"))
    # print(QueryCOHD.find_concept_ids("cancer"))
    # print(QueryCOHD.get_paired_concept_freq('192855', '2008271', 1))
    # print(QueryCOHD.get_individual_concept_freq('192855'))
    # print(QueryCOHD.get_associated_concept_domain_freq('192855', 'Procedure', 1))
    # print(QueryCOHD.get_concepts(["192855"]))
    # print(QueryCOHD.get_concepts(["192855", "2008271"]))
    # print(QueryCOHD.get_xref_from_OMOP("192855", "UMLS", 2))
    # print(QueryCOHD.get_xref_to_OMOP("DOID:8398", 2))
    # print(QueryCOHD.get_map_from_standard_concept_id("72990", "ICD9CM"))
    # print(QueryCOHD.get_map_from_standard_concept_id("72990"))
    # print(QueryCOHD.get_map_to_standard_concept_id("715.3", "ICD9CM"))
    # print(QueryCOHD.get_vocabularies())
    # print(QueryCOHD.get_associated_concept_freq("192855"))
    # print(QueryCOHD.get_associated_concept_freq("192855", 2))
    # print(QueryCOHD.get_most_frequent_concepts(2))
    # print(QueryCOHD.get_most_frequent_concepts(2, 'Condition'))
    # print(QueryCOHD.get_most_frequent_concepts(2, 'Condition', 2))
    # print(QueryCOHD.get_most_frequent_concepts(2, '', 2))
    # print(QueryCOHD.get_chi_square("192855", "2008271", "Condition", 2))
    # print(QueryCOHD.get_chi_square("192855", "2008271", "Condition"))
    # print(QueryCOHD.get_chi_square("192855", "2008271"))
    # print(len(QueryCOHD.get_chi_square("192855")))
    # print(len(QueryCOHD.get_chi_square("192855", "", "Condition")))
    # print(len(QueryCOHD.get_chi_square("192855", "", "Condition", 2)))
    # print(len(QueryCOHD.get_chi_square("192855", "", "", 2)))
    # print(QueryCOHD.get_obs_exp_ratio("192855", "2008271", "Procedure"))
    # print(QueryCOHD.get_obs_exp_ratio("192855", "2008271", "Procedure", 2))
    # print(QueryCOHD.get_obs_exp_ratio("192855", "2008271", ""))
    # print(QueryCOHD.get_obs_exp_ratio("192855", "2008271", "", 2))
    # print(len(QueryCOHD.get_obs_exp_ratio("192855")))
    # print(len(QueryCOHD.get_obs_exp_ratio("192855", "", "", 2)))
    # print(len(QueryCOHD.get_obs_exp_ratio("192855", "", "Procedure")))
    # print(len(QueryCOHD.get_obs_exp_ratio("192855", "", "Procedure", 2)))
    # print(QueryCOHD.get_relative_frequency("192855", "2008271", "Procedure"))
    # print(QueryCOHD.get_relative_frequency("192855", "2008271", "Procedure", 2))
    # print(QueryCOHD.get_relative_frequency("192855", "2008271", ""))
    # print(QueryCOHD.get_relative_frequency("192855", "2008271", "", 2))
    # print(len(QueryCOHD.get_relative_frequency("192855")))
    # print(len(QueryCOHD.get_relative_frequency("192855", "", "", 2)))
    # print(len(QueryCOHD.get_relative_frequency("192855", "", "Procedure")))
    # print(len(QueryCOHD.get_relative_frequency("192855", "", "Procedure", 2)))
    # print(QueryCOHD.get_datasets())
    # print(QueryCOHD.get_domain_counts())
    # print(QueryCOHD.get_domain_counts(2))
    # print(QueryCOHD.get_domain_pair_counts())
    # print(QueryCOHD.get_domain_pair_counts(2))
    # print(QueryCOHD.get_patient_count())
    # print(QueryCOHD.get_patient_count(2))
    # ancestors = QueryCOHD.get_concept_ancestors('19019073', 'RxNorm', 'Ingredient', 1)
    # print(ancestors)
    # descendants = QueryCOHD.get_concept_descendants('19019073') #   , 'RxNorm', 'Ingredient', 1
    # print(len(descendants))