""" This module defines the class QueryPharos which connects to APIs at
https://pharos.ncats.io/idg/api/v1, querying information correspondances among
drugs, dieases, targets.
"""

__author__ = ""
__copyright__ = ""
__credits__ = []
__license__ = ""
__version__ = ""
__maintainer__ = ""
__email__ = ""
__status__ = "Prototype"

import requests
import CachedMethods


class QueryPharos:

    API_BASE_URL = 'https://pharos.ncats.io/idg/api/v1'

    @staticmethod
    def send_query_get(entity, url_suffix):
        url_str = QueryPharos.API_BASE_URL + "/" + entity + url_suffix
        #print(url_str)
        res = requests.get(url_str, headers={'accept': 'application/json'})
        status_code = res.status_code
        #print("Status code="+str(status_code))
        assert status_code in [200, 404]
        if status_code == 404:
            res = None
        return res


    @staticmethod
    @CachedMethods.register
    def query_drug_name_to_targets(drug_name):
        ret_ids = []
        res = QueryPharos.send_query_get("targets","/search?q="+drug_name+"&facet=IDG%20Development%20Level%2FTclin")
        if res is not None:
            res_json = res.json()
            #print(res_json)
            if type(res_json)==dict:
                res_content = res_json['content']
                #print(res_content)
                for content_entry in res_content:
                    ret_ids.append( { 'id': content_entry['id'], 'name': content_entry['name'] } )
        return ret_ids


    @staticmethod
    @CachedMethods.register
    def query_target_to_diseases(target_id):
        ret_ids = []
        res = QueryPharos.send_query_get("targets","("+target_id+")/links(kind=ix.idg.models.Disease)")
        if res is not None:
            res_json = res.json()
            #print(res_json)
            if type(res_json) == list:
                for res_entry in res_json:
                    id = res_entry['refid']
                    name = None
                    if res_entry['properties'] is not None:
                        #print(res_entry['properties'])
                        for res_property in res_entry['properties']:
                            if res_property['label'] == 'IDG Disease':
                                name = res_property['term']
                    ret_ids.append( { 'id': id, 'name': name } )
        return ret_ids


    @staticmethod
    @CachedMethods.register
    def query_target_to_drugs(target_id):
        ret_ids = []
        res = QueryPharos.send_query_get("targets","("+target_id+")/links(kind=ix.idg.models.Ligand)")
        if res is not None:
            res_json = res.json()
            #print(res_json)
            if type(res_json)==list:
                for res_entry in res_json:
                    if res_entry['properties'] is not None:
                        #print(res_entry['properties'])
                        name = None
                        action = None
                        id = None
                        for res_property in res_entry['properties']:
                            if res_property['label'] == 'IDG Ligand':
                                name = res_property['term']
                                id = res_property['id']
                            if res_property['label'] == 'Pharmalogical Action':
                                action = res_property['term']
                        if name is not None and action is not None:
                            ret_ids.append( { 'id': id, 'name': name, 'action': action } )
        return ret_ids


    @staticmethod
    @CachedMethods.register
    def query_drug_to_targets(drug_id):
        ret_ids = []
        res = QueryPharos.send_query_get("ligands","("+drug_id+")/links(kind=ix.idg.models.Target)")
        if res is not None:
            res_json = res.json()
            #print(res_json)
            if type(res_json)==list:
                for res_entry in res_json:
                    if res_entry['properties'] is not None:
                        #print(res_entry['properties'])
                        name = None
                        id = None
                        for res_property in res_entry['properties']:
                            if res_property['label'] == 'IDG Target':
                                name = res_property['term']
                                id = res_property['id']
                        if name is not None and id is not None:
                            ret_ids.append( { 'id': id, 'name': name } )
            if type(res_json)==dict:
                if res_json['properties'] is not None:
                    #print(res_json['properties'])
                    name = None
                    id = None
                    for res_property in res_json['properties']:
                        if res_property['label'] == 'IDG Target':
                            name = res_property['term']
                            id = res_property['id']
                    if name is not None and id is not None:
                        ret_ids.append( { 'id': id, 'name': name } )
        return ret_ids


    @staticmethod
    @CachedMethods.register
    def query_target_name(target_id):
        res = QueryPharos.send_query_get("targets","("+target_id+")")
        if res is not None:
            res_json = res.json()
            #print(res_json)
            if type(res_json)==dict:
                ret_value = res_json['name']
            else:
                ret_value = None
        else:
            ret_value = None
        return ret_value


    @staticmethod
    @CachedMethods.register
    def query_target_uniprot_accession(target_id):
        res = QueryPharos.send_query_get("targets","("+target_id+")/synonyms")
        if res is not None:
            res_json = res.json()
            #print(res_json)
            if type(res_json)==list:
                for res_entry in res_json:
                    if res_entry['label'] == 'UniProt Accession':
                        return res_entry['term']   # return the first one of many
        return None


    @staticmethod
    @CachedMethods.register
    def query_disease_name(disease_id):
        res = QueryPharos.send_query_get("diseases","("+disease_id+")")
        if res is not None:
            res_json = res.json()
            #print(res_json)
            if type(res_json)==dict:
                ret_value = res_json['name']
            else:
                ret_value = None
        else:
            ret_value = None
        return ret_value


    @staticmethod
    @CachedMethods.register
    def query_drug_name(ligand_id):
        res = QueryPharos.send_query_get("ligands","("+ligand_id+")")
        if res is not None:
            res_json = res.json()
            #print(res_json)
            if type(res_json)==dict:
                ret_value = res_json['name']
            else:
                ret_value = None
        else:
            ret_value = None
        return ret_value


    @staticmethod
    @CachedMethods.register
    def query_drug_id_by_name(drug_name):
        res = QueryPharos.send_query_get("ligands","/search?q="+drug_name)
        if res is not None:
            res_json = res.json()
            #print(res_json)
            ret_value = None
            if type(res_json)==dict:
                res_content = res_json['content']
                for content_entry in res_content:
                    #print(content_entry)
                    if content_entry['name'] == drug_name:
                        ret_value = content_entry['id']
            else:
                ret_value = None
        else:
            ret_value = None
        return ret_value


    @staticmethod
    @CachedMethods.register
    def query_disease_id_by_name(disease_name):
        res = QueryPharos.send_query_get("diseases","/search?q="+disease_name)
        if res is not None:
            res_json = res.json()
            #print(res_json)
            ret_value = None
            if type(res_json)==dict:
                res_content = res_json['content']
                for content_entry in res_content:
                    #print(content_entry)
                    if content_entry['name'] == disease_name:
                        ret_value = content_entry['id']
        return ret_value

if __name__ == '__main__':
        print(QueryPharos.query_drug_id_by_name('lovastatin'))
        print(QueryPharos.query_drug_id_by_name('clothiapine'))
#        print(QueryPharos.query_drug_id_by_name("lovastatin"))
#        print(QueryPharos.query_drug_to_targets("254599"))
#        print(QueryPharos.query_drug_name_to_targets("lovastatin"))
#        print("=============")
#        print(QueryPharos.query_target_uniprot_accession("19672"))
#        print("=============")
#        print(QueryPharos.query_target_to_diseases("19672"))
