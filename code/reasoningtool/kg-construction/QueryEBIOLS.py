__author__ = 'Stephen Ramsey'
__copyright__ = 'Oregon State University'
__credits__ = ['Stephen Ramsey']
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
import time

class QueryEBIOLS:
    TIMEOUT_SEC = 120
    API_BASE_URL = "https://www.ebi.ac.uk/ols/api/ontologies"
    HANDLER_MAP = {
        'get_anatomy': '{ontology}/terms/{id}',
        'get_phenotype': '{ontology}/terms/{id}',
        'get_disease': '{ontology}/terms/{id}',
        'get_bio_process': '{ontology}/terms/{id}',
        'get_cellular_component': '{ontology}/terms/{id}',
        'get_molecular_function': '{ontology}/terms/{id}'
    }

    @staticmethod
    def send_query_get(handler, url_suffix):
        url_str = QueryEBIOLS.API_BASE_URL + '/' + handler + "/" + url_suffix
#        print(url_str)
        try:
            res = requests.get(url_str, headers={'Accept': 'application/json'}, timeout=QueryEBIOLS.TIMEOUT_SEC)
        except requests.exceptions.Timeout:
            print('HTTP timeout in QueryNCBIeUtils.py; URL: ' + url_str, file=sys.stderr)
            time.sleep(1)  # take a timeout because NCBI rate-limits connections
            return None
        except requests.exceptions.ConnectionError:
            print('HTTP connection error in QueryNCBIeUtils.py; URL: ' + url_str, file=sys.stderr)
            time.sleep(1)  # take a timeout because NCBI rate-limits connections
            return None
        status_code = res.status_code
        if status_code != 200:
            print('HTTP response status code: ' + str(status_code) + ' for URL:\n' + url_str, file=sys.stderr)
            res = None
        return res

    @staticmethod
    def get_bto_term_for_bto_id(bto_curie_id):
        """
        Converts an anatomy BTO ID to the BTO term
        :param bto_curie_id: eg. "BTO:0001259"
        :return: a set of BTO terms (eg. {"blood"})
        """
        bto_iri = "http://purl.obolibrary.org/obo/" + bto_curie_id.replace(":", "_")
        bto_iri_double_encoded = urllib.parse.quote_plus(urllib.parse.quote_plus(bto_iri))
        res = QueryEBIOLS.send_query_get("bto/terms/", bto_iri_double_encoded)
        ret_label = None
        if res is not None:
            res_json = res.json()
            ret_label = res_json.get("label", None)
        return ret_label
    
    @staticmethod
    def get_bto_id_for_uberon_id(uberon_curie_id):
        """
        Converts an anatomy uberon ID to BTO id
        :param uberon_curie_id: eg. "UBERON:0001259"
        :return: a set of BTO id's (eg. {"BTO:D008099"})
        """
        uberon_iri = "http://purl.obolibrary.org/obo/" + uberon_curie_id.replace(":", "_")
        uberon_iri_double_encoded = urllib.parse.quote_plus(urllib.parse.quote_plus(uberon_iri))
        res = QueryEBIOLS.send_query_get("uberon/terms/", uberon_iri_double_encoded)
        ret_list = list()
        if res is not None:
            res_json = res.json()
            res_annotation = res_json.get("annotation", None)
            if res_annotation is not None:
                db_x_refs = res_annotation.get("database_cross_reference", None)
                if db_x_refs is not None:
                    ret_list = [bto_id for bto_id in db_x_refs if "BTO:" in bto_id]
        return set(ret_list)
    
    @staticmethod
    def get_mesh_id_for_uberon_id(uberon_curie_id):
        """
        Converts an anatomy uberon ID to MeSH id
        :param uberon_curie_id: eg. "UBERON:0001259"
        :return: a set of MeSH id's (eg. {"MESH:D008099"})
        """
        uberon_iri = "http://purl.obolibrary.org/obo/" + uberon_curie_id.replace(":", "_")
        uberon_iri_double_encoded = urllib.parse.quote_plus(urllib.parse.quote_plus(uberon_iri))
        res = QueryEBIOLS.send_query_get("uberon/terms/", uberon_iri_double_encoded)
        ret_list = list()
        if res is not None:
            res_json = res.json()
            res_annotation = res_json.get("annotation", None)
            if res_annotation is not None:
                db_x_refs = res_annotation.get("database_cross_reference", None)
                if db_x_refs is not None:
                    ret_list = [mesh_id for mesh_id in db_x_refs if "MESH:" in mesh_id]
        return set(ret_list)

    @staticmethod
    def __access_api(handler):

        url = QueryEBIOLS.API_BASE_URL + '/' + handler
        # print(url)
        try:
            res = requests.get(url, timeout=QueryEBIOLS.TIMEOUT_SEC)
        except requests.exceptions.Timeout:
            print(url, file=sys.stderr)
            print('Timeout in QueryEBIOLSExtended for URL: ' + url, file=sys.stderr)
            return None
        except KeyboardInterrupt:
            sys.exit(0)
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
        handler = QueryEBIOLS.HANDLER_MAP[entity_type].format(ontology=ontology_id.lower(), id=iri_double_encoded)
        results = QueryEBIOLS.__access_api(handler)
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
        return QueryEBIOLS.__get_entity("get_anatomy", anatomy_id)

    @staticmethod
    def get_bio_process_description(bio_process_id):
        return QueryEBIOLS.__get_entity("get_bio_process", bio_process_id)

    @staticmethod
    def get_phenotype_description(phenotype_id):
        return QueryEBIOLS.__get_entity("get_phenotype", phenotype_id)

    @staticmethod
    def get_disease_description(disease_id):
        return QueryEBIOLS.__get_entity("get_disease", disease_id)

    @staticmethod
    def get_cellular_component_description(cc_id):
        return QueryEBIOLS.__get_entity("get_cellular_component", cc_id)

    @staticmethod
    def get_molecular_function_description(mf_id):
        return QueryEBIOLS.__get_entity("get_molecular_function", mf_id)


if __name__ == "__main__":
    print(QueryEBIOLS.get_bto_id_for_uberon_id("UBERON:0000178"))
    print(QueryEBIOLS.get_bto_term_for_bto_id("BTO:0000089"))
    print(QueryEBIOLS.get_mesh_id_for_uberon_id("UBERON:0002107"))
    print(QueryEBIOLS.get_mesh_id_for_uberon_id("UBERON:0001162"))

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

    save_to_test_file('UBERON:0004476', QueryEBIOLS.get_anatomy_description('UBERON:0004476'))
    save_to_test_file('CL:0000038', QueryEBIOLS.get_anatomy_description('CL:0000038'))
    save_to_test_file('GO:0042535', QueryEBIOLS.get_bio_process_description('GO:0042535'))
    save_to_test_file('HP:0011105', QueryEBIOLS.get_phenotype_description('HP:0011105'))
    save_to_test_file('GO:0005573', QueryEBIOLS.get_cellular_component_description('GO:0005573'))
    save_to_test_file('GO:0004689', QueryEBIOLS.get_molecular_function_description('GO:0004689'))
    save_to_test_file('OMIM:604348', QueryEBIOLS.get_disease_description('OMIM:604348'))
