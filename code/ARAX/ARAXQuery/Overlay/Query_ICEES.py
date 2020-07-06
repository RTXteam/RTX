'''This module defines the class Query_ICEES to
communicate with the ICEES API(3.0.0) to obtain drug - chemical-substance association
between PUBCHEM:2083 and PUBCHEM:281.

'''

__author__ = 'Mayank Murali'
__copyright__ = 'The Pennsylvania State University'
__credits__ = ['Mayank Murali', 'David Koslicki']
__license__ = 'MIT'
__version__ = '0.1.0'
__maintainer__ = ''
__email__ = ''
__status__ = 'Trial'

import requests
import re
import json
import sys
import urllib.parse

#from cache_control_helper import CacheControlHelper

# json file input
with open('Input.json') as f:
    input_data = json.load(f)
#print(input_data)    

#main class 
class Query_ICEES:
    API_BASE_URL = 'http://icees.renci.org:16340/'

    HANDLER_MAP = {
        'get_feature_identifiers':               '/{table}/{feature}/identifiers',
        'get_cohort_definition':                 '/{table}/{year}/cohort/{cohort_id}',
        'get_cohort_based_feature_profile':      '/{table}/{year}/cohort/{cohort_id}/features',
        'get_cohort_dictionary':                 '/{table}/{year}/cohort/dictionary',
        'get_cohort_id_from_name':               '/{table}/name/{name}',
        'post_knowledge_graph_overlay':          '/knowledge_graph_overlay',
        'query_ICEES_kg_schema':                 '/knowledge_graph/schema',
    }
 
    
    @staticmethod
    def __access_api(handler, url_suffix, query):
        
        #requests = CacheControlHelper()
        #url = Query_ICEES.API_BASE_URL + handler + '?' + url_suffix
        url = 'http://icees.renci.org:16340/apidocs/#/default/post_knowledge_graph_overlay'
        requests.get(url, verify='/path/to/certfile')
        response_content = requests.post(url, json=query, headers={'accept': 'application/json'})
        
        status_code = response_content.status_code
        if status_code != 200:
            print("Error returned with status "+str(status_code))
        else:
            print(f"Response returned with status {status_code}")
         
        #TODO(FIX): Identify reason for error 400.
        response_dict = response_content.json()
        for message in response_dict['log']:
            if message['level'] >= 20:
                print(message['prefix']+message['message'])
                
        output_json = json.dumps(response_dict)
        return response_dict
        
    @staticmethod
    def get_feature_identifiers(table, feature):
        
        if not isinstance(table, str) or not isinstance(feature, str):
            return []
        handler = Query_ICEES.HANDLER_MAP['get_feature_identifiers']

        # TODO: Add handler and url_suffix

        res_json = Query_ICEES.__access_api(handler, url_suffix)
        results_list = []
        if res_json is not None:
            results = res_json.get('results', None)
            if results is not None and type(results) == list:
                results_list = results
        return results_list
       

    @staticmethod
    def get_cohort_definition(cohort_id, table, year):

        if not isinstance(table, str) or not isinstance(year, int) or not isinstance(cohort_id, str):
            return []
        handler = Query_ICEES.HANDLER_MAP['get_cohort_definition']

        # TODO: Add handler and url_suffix

        res_json = Query_ICEES.__access_api(handler, url_suffix)
        results_list = []
        if res_json is not None:
            results = res_json.get('results', None)
            if results is not None and type(results) == list:
                results_list = results
        return results_list

    @staticmethod
    def get_cohort_based_feature_profile( cohort_id, table, year):
        
        if not isinstance(table, str) or not isinstance(year, int) or not isinstance(cohort_id, str):
            return []
        handler = Query_ICEES.HANDLER_MAP['get_cohort_based_feature_profile']

        # TODO: Add handler and url_suffix

        res_json = Query_ICEES.__access_api(handler, url_suffix)
        results_list = []
        if res_json is not None:
            results = res_json.get('results', None)
            if results is not None and type(results) == list:
                results_list = results
        return results_list

    @staticmethod
    def get_cohort_dictionary(table, year):
                
        if not isinstance(table, str) or not isinstance(year, int):
            return []
        handler = Query_ICEES.HANDLER_MAP['get_cohort_dictionary']

        # TODO: Add handler and url_suffix

        res_json = Query_ICEES.__access_api(handler, url_suffix)
        results_list = []
        if res_json is not None:
            results = res_json.get('results', None)
            if results is not None and type(results) == list:
                results_list = results
        return results_list

    @staticmethod
    def get_cohort_id_from_name(name, table):
                        
        if not isinstance(table, str) or not isinstance(name, str):
            return []
        handler = Query_ICEES.HANDLER_MAP['get_cohort_id_from_name']

        # TODO: Add handler and url_suffix

        res_json = Query_ICEES.__access_api(handler, url_suffix)
        results_list = []
        if res_json is not None:
            results = res_json.get('results', None)
            if results is not None and type(results) == list:
                results_list = results
        return results_list

    @staticmethod
    def query_ICEES_kg_schema():
                        
        handler = Query_ICEES.HANDLER_MAP['query_ICEES_kg_schema']
        handler = 'apidocs/#/default'
        url_suffix = 'get_knowledge_graph_schema'

        res_json = Query_ICEES.__access_api(handler, url_suffix)
        results_list = []
        if res_json is not None:
            results = res_json.get('results', None)
            if results is not None and type(results) == list:
                results_list = results
        return results_list

    @staticmethod
    def post_knowledge_graph_overlay(body):
                        
        handler = Query_ICEES.HANDLER_MAP['post_knowledge_graph_overlay']
        url_suffix = ''
        Query_ICEES.__access_api(handler, url_suffix, body)


if __name__ == '__main__':
    print(Query_ICEES.post_knowledge_graph_overlay(input_data))

            
