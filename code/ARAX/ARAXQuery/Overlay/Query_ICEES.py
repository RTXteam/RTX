'''This module defines the class Query_ICEES to
communicate with the ICEES API(3.0.0).
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
import unittest

#from cache_control_helper import CacheControlHelper
   

#main class 
class Query_ICEES:
    API_BASE_URL = 'https://icees.renci.org:16340/'

    HANDLER_MAP = {
        'get_feature_identifiers':               '{table}/{feature}/identifiers',
        'get_cohort_definition':                 '{table}/{year}/cohort/{cohort_id}',
        'get_cohort_based_feature_profile':      '{table}/{year}/cohort/{cohort_id}/features',
        'get_cohort_dictionary':                 '{table}/{year}/cohort/dictionary',
        'get_cohort_id_from_name':               '{table}/name/{name}',
        'post_knowledge_graph_overlay':          'knowledge_graph_overlay',
        'query_ICEES_kg_schema':                 'knowledge_graph/schema',
    }
 
    
    @staticmethod
    def __access_api(handler, url_suffix, query):
        
        try:
            #requests = CacheControlHelper()
            url = Query_ICEES.API_BASE_URL + handler+ url_suffix
            response_content = requests.post(url, json=query, headers={'accept': 'application/json'}, verify=False)
            print(f"Executing query at {url}\nPlease wait...")
            
            status_code = response_content.status_code
            if status_code != 200:
                print("Error returned with status \n"+str(status_code))
            else:
                print(f"Response returned with status\n"+str(status_code))
         
            response_dict = response_content.json()
        
            #output_json = json.dumps(response_dict)    
            print(json.dumps(response_dict, indent=2, sort_keys=True))
            return response_dict
                
            

        except requests.exceptions.HTTPError as httpErr: 
            print ("Http Error:",httpErr) 
        except requests.exceptions.ConnectionError as connErr: 
            print ("Error Connecting:",connErr) 
        except requests.exceptions.Timeout as timeOutErr: 
            print ("Timeout Error:",timeOutErr) 
        except requests.exceptions.RequestException as reqErr: 
            print ("Something Else:",reqErr)
        
    @staticmethod
    def get_feature_identifiers(table, feature):
        
        if not isinstance(table, str) or not isinstance(feature, str):
            return []
        handler = Query_ICEES.HANDLER_MAP['get_feature_identifiers']
        url_suffix = ''

        res_json = Query_ICEES.__access_api(handler, url_suffix)
        return res_json
       

    @staticmethod
    def get_cohort_definition(cohort_id, table, year):

        if not isinstance(table, str) or not isinstance(year, int) or not isinstance(cohort_id, str):
            return []
        handler = Query_ICEES.HANDLER_MAP['get_cohort_definition']
        url_suffix = ''

        res_json = Query_ICEES.__access_api(handler, url_suffix)
        return res_json

    @staticmethod
    def get_cohort_based_feature_profile( cohort_id, table, year):
        
        if not isinstance(table, str) or not isinstance(year, int) or not isinstance(cohort_id, str):
            return []
        handler = Query_ICEES.HANDLER_MAP['get_cohort_based_feature_profile']
        url_suffix = ''

        res_json = Query_ICEES.__access_api(handler, url_suffix)
        return res_json

    @staticmethod
    def get_cohort_dictionary(table, year):
                
        if not isinstance(table, str) or not isinstance(year, int):
            return []
        handler = Query_ICEES.HANDLER_MAP['get_cohort_dictionary']
        url_suffix = ''

        res_json = Query_ICEES.__access_api(handler, url_suffix)
        return res_json

    @staticmethod
    def get_cohort_id_from_name(name, table):
                        
        if not isinstance(table, str) or not isinstance(name, str):
            return []
        handler = Query_ICEES.HANDLER_MAP['get_cohort_id_from_name']
        url_suffix = ''

        res_json = Query_ICEES.__access_api(handler, url_suffix)
        return res_json

    @staticmethod
    def query_ICEES_kg_schema():
                        
        handler = Query_ICEES.HANDLER_MAP['query_ICEES_kg_schema']
        url_suffix = ''

        res_json = Query_ICEES.__access_api(handler, url_suffix)
        return res_json

    @staticmethod
    def post_knowledge_graph_overlay(query):
        
        '''
        ICEES compatible query looks like this
        
        query =     {
                        "message": {
                            "knowledge_graph": {
                                "nodes": [
                                    {
                                        "node_id": "n00",
                                        "curie": "PUBCHEM:2083",
                                        "type": "drug"
                                    },
                                    {
                                        "node_id": "n01",
                                        "curie": "PUBCHEM:281",
                                        "type": "chemical_substance"
                                    }  
                                ],
                                "edges": [
                                    {
                                        "id": "e00",
                                        "type": "association",
                                        "source_id": "n00",
                                        "target_id": "n01"
                                    }
                                ]
                            }
                        }
                    }
        '''
        
        handler = Query_ICEES.HANDLER_MAP['post_knowledge_graph_overlay']
        url_suffix = ''
        res_json = Query_ICEES.__access_api(handler, url_suffix, query)
        return res_json

# Class to test the query output 
class test_query(unittest.TestCase):
    def test(self):
        self.assertEqual(Query_ICEES.post_knowledge_graph_overlay(input_data), output_data)


if __name__ == '__main__':
    Query_ICEES.post_knowledge_graph_overlay(query)
    
   
    
    #Testing the query 
    #unittest.main()

            
