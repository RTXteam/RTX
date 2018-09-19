
''' This module defines the class QueryBioLinkExtended. QueryBioLinkExtended class is designed
to communicate with Monarch APIs and their corresponding data sources. The
available methods include:
    * query anatomy entity by ID
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
import urllib.parse
import sys
import json


class QueryEBIOLSExtended:
    TIMEOUT_SEC = 120
    API_BASE_URL = 'https://www.ebi.ac.uk/ols/api/ontologies'
    HANDLER_MAP = {
        'get_anatomy': '{ontology}/terms/{id}',
        'get_phenotype': '{ontology}/terms/{id}',
        'get_disease': '{ontology}/terms/{id}',
        'get_bio_process': '{ontology}/terms/{id}',
        'get_cellular_component': '{ontology}/terms/{id}',
        'get_molecular_function': '{ontology}/terms/{id}'
    }

    @staticmethod
    def __access_api(handler):

        url = QueryEBIOLSExtended.API_BASE_URL + '/' + handler
        # print(url)
        try:
            res = requests.get(url, timeout=QueryEBIOLSExtended.TIMEOUT_SEC)
        except requests.exceptions.Timeout:
            print(url, file=sys.stderr)
            print('Timeout in QueryEBIOLSExtended for URL: ' + url, file=sys.stderr)
            return None
        except BaseException as e:
            print(url, file=sys.stderr)
            print('%s received in QueryEBIOLSExtended for URL: %s' % (e, url), file=sys.stderr)
            return None
        status_code = res.status_code
        if status_code != 200:
            print(url, file=sys.stderr)
            print('Status code ' + str(status_code) + ' for url: ' + url, file=sys.stderr)
            return None

        return res.text

    @staticmethod
    def __get_entity(entity_type, entity_id):
        ontology_id = entity_id[:entity_id.find(":")]
        iri = "http://purl.obolibrary.org/obo/" + entity_id.replace(":", "_")
        iri_double_encoded = urllib.parse.quote_plus(urllib.parse.quote_plus(iri))
        handler = QueryEBIOLSExtended.HANDLER_MAP[entity_type].format(ontology=ontology_id.lower(), id=iri_double_encoded)
        results = QueryEBIOLSExtended.__access_api(handler)
        result_str = "None"
        if results is not None:
            res_json = json.loads(results)
            # print(res_json)
            res_description = res_json.get("description", None)
            if res_description is not None:
                if len(res_description) > 0:
                    result_str = res_description[0]
        return result_str

    @staticmethod
    def get_anatomy_description(anatomy_id):
        return QueryEBIOLSExtended.__get_entity("get_anatomy", anatomy_id)

    @staticmethod
    def get_bio_process_description(bio_process_id):
        return QueryEBIOLSExtended.__get_entity("get_bio_process", bio_process_id)

    @staticmethod
    def get_phenotype_description(phenotype_id):
        return QueryEBIOLSExtended.__get_entity("get_phenotype", phenotype_id)

    @staticmethod
    def get_disease_description(disease_id):
        return QueryEBIOLSExtended.__get_entity("get_disease", disease_id)

    @staticmethod
    def get_cellular_component_description(cc_id):
        return QueryEBIOLSExtended.__get_entity("get_cellular_component", cc_id)

    @staticmethod
    def get_molecular_function_description(mf_id):
        return QueryEBIOLSExtended.__get_entity("get_molecular_function", mf_id)

if __name__ == '__main__':

    def save_to_test_file(key, value):
        f = open('tests/query_desc_test_data.json', 'r+')
        try:
            json_data = json.load(f)
        except ValueError:
            json_data = {}
        f.seek(0)
        f.truncate()
        json_data[key] = value
        json.dump(json_data, f)
        f.close()

    save_to_test_file('UBERON:0004476', QueryEBIOLSExtended.get_anatomy_description('UBERON:0004476'))
    save_to_test_file('UBERON:00044760', QueryEBIOLSExtended.get_anatomy_description('UBERON:00044760'))
    save_to_test_file('CL:0000038', QueryEBIOLSExtended.get_anatomy_description('CL:0000038'))
    save_to_test_file('CL:00000380', QueryEBIOLSExtended.get_anatomy_description('CL:00000380'))
    save_to_test_file('GO:0042535', QueryEBIOLSExtended.get_bio_process_description('GO:0042535'))
    save_to_test_file('GO:00425350', QueryEBIOLSExtended.get_bio_process_description('GO:00425350'))
    save_to_test_file('HP:0011105', QueryEBIOLSExtended.get_phenotype_description('HP:0011105'))
    save_to_test_file('HP:00111050', QueryEBIOLSExtended.get_phenotype_description('HP:00111050'))
    save_to_test_file('GO:0005573', QueryEBIOLSExtended.get_cellular_component_description('GO:0005573'))
    save_to_test_file('GO:00055730', QueryEBIOLSExtended.get_cellular_component_description('GO:00055730'))
    save_to_test_file('GO:0004689', QueryEBIOLSExtended.get_molecular_function_description('GO:0004689'))
    save_to_test_file('GO:00046890', QueryEBIOLSExtended.get_molecular_function_description('GO:00046890'))
    save_to_test_file('OMIM:613573', QueryEBIOLSExtended.get_disease_description('OMIM:613573'))
    save_to_test_file('OMIM:6135730', QueryEBIOLSExtended.get_disease_description('OMIM:6135730'))
