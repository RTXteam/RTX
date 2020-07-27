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
#import unittest
from collections import OrderedDict
#from cache_control_helper import CacheControlHelper
from deepdiff import DeepDiff  # For Deep Difference of 2 objects
#from deepdiff import grep, DeepSearch  # For finding if item exists in an object
#from deepdiff import DeepHash  # For hashing objects based on their contents   
#import jsondiff 
#from recursive_diff import recursive_eq    

#main class 
class Query_ICEES:
    API_BASE_URL = 'https://icees.renci.org:16340/'

    HANDLER_MAP = {
        'get_feature_identifiers':               '{table}/{feature}/identifiers',
        'get_cohort_definition':                 '{table}/{year}/cohort/{cohort_id}',
        'get_cohort_based_feature_profile':      '{table}/{year}/cohort/{cohort_id}/features',
        'get_cohort_dictionary':                 '{table}/{year}/cohort/dictionary',
        'get_cohort_id_from_name':               '{table}/name/{name}',
        'post_knowledge_graph_one_hop':          'knowledge_graph_one_hop',
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
         
            response_json = response_content.json()
        
            #output_json = json.dumps(response_json)    
            #print(json.dumps(response_json, indent=2, sort_keys=True))
            #print(json.dumps(OrderedDict(response_json)))
            #res = jsondiff.diff(json.dumps(OrderedDict(expected_json), indent=2, sort_keys=True), json.dumps(OrderedDict(response_json), indent=2, sort_keys=True))
            
            return response_json    

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
    def post_knowledge_graph_one_hop():

        handler = Query_ICEES.HANDLER_MAP['post_knowledge_graph_one_hop']
        url_suffix = ''
        res_json = Query_ICEES.__access_api(handler, url_suffix, query)
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
class test_query():
    
    def test(expected_json, response_json):
        '''
        Args:
            query:          input JSON query 
            expected_json:  expected JSON result
        '''
        #Compares the query outout and expected JSON printing the difference from the 
        ddiff = DeepDiff(expected_json, response_json, ignore_order=True, report_repetition=True, exclude_paths={"root['terms and conditions']"})
        print(ddiff)
        
        #self.assertAlmostEqual(str(Query_ICEES.post_knowledge_graph_overlay()), str(expected_json), places = None, msg = None, delta = 900000)
        #self.assertEqual(Query_ICEES.post_knowledge_graph_overlay(), expected_json)
    
        #recursive_eq(Query_ICEES.post_knowledge_graph_overlay(), expected_json, abs_tol=.1)


if __name__ == '__main__':
    res_json = Query_ICEES.post_knowledge_graph_overlay(query)

    #Testing the query (pass exptected JSON here)
    test_query.test(expected_json, res_json)
