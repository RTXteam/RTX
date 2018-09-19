
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
import sys
import json


class QueryBioLinkExtended:
    TIMEOUT_SEC = 120
    API_BASE_URL = 'https://api.monarchinitiative.org/api/bioentity'
    HANDLER_MAP = {
        'get_anatomy': 'anatomy/{id}',
        'get_phenotype': 'phenotype/{id}',
        'get_disease': 'disease/{id}',
        'get_bio_process': '{id}'
    }

    @staticmethod
    def __access_api(handler):

        url = QueryBioLinkExtended.API_BASE_URL + '/' + handler

        try:
            res = requests.get(url, timeout=QueryBioLinkExtended.TIMEOUT_SEC)
        except requests.exceptions.Timeout:
            print(url, file=sys.stderr)
            print('Timeout in QueryBioLink for URL: ' + url, file=sys.stderr)
            return None
        except BaseException as e:
            print(url, file=sys.stderr)
            print('%s received in QueryBioLink for URL: %s' % (e, url), file=sys.stderr)
            return None
        status_code = res.status_code
        if status_code != 200:
            print(url, file=sys.stderr)
            print('Status code ' + str(status_code) + ' for url: ' + url, file=sys.stderr)
            return None

        return res.text

    @staticmethod
    def __get_entity(entity_type, entity_id):
        handler = QueryBioLinkExtended.HANDLER_MAP[entity_type].format(id=entity_id)
        results = QueryBioLinkExtended.__access_api(handler)
        result_str = 'UNKNOWN'
        if results is not None:
            #   remove all \n characters using json api and convert the string to one line
            json_dict = json.loads(results)
            result_str = json.dumps(json_dict)
        return result_str

    @staticmethod
    def get_anatomy_entity(anatomy_id):
        return QueryBioLinkExtended.__get_entity("get_anatomy", anatomy_id)

    @staticmethod
    def get_phenotype_entity(phenotype_id):
        return QueryBioLinkExtended.__get_entity("get_phenotype", phenotype_id)

    @staticmethod
    def get_disease_entity(disease_id):
        return QueryBioLinkExtended.__get_entity("get_disease", disease_id)

    @staticmethod
    def get_bio_process_entity(bio_process_id):
        return QueryBioLinkExtended.__get_entity("get_bio_process", bio_process_id)


if __name__ == '__main__':

    def save_to_test_file(key, value):
        f = open('tests/query_test_data.json', 'r+')
        try:
            json_data = json.load(f)
        except ValueError:
            json_data = {}
        f.seek(0)
        f.truncate()
        json_data[key] = value
        json.dump(json_data, f)
        f.close()

    save_to_test_file('UBERON:0004476', QueryBioLinkExtended.get_anatomy_entity('UBERON:0004476'))
    save_to_test_file('HP:0011515', QueryBioLinkExtended.get_phenotype_entity('HP:0011515'))
    save_to_test_file('DOID:3965', QueryBioLinkExtended.get_disease_entity('DOID:3965'))
    save_to_test_file('GO:0097289', QueryBioLinkExtended.get_bio_process_entity('GO:0097289'))
