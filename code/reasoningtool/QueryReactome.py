""" This module defines the class QueryReactome. QueryReactome is written to
connect with APIs at https://reactome.org/ContentService, querying the pathway
information.
"""

__author__ = 'Stephen Ramsey'
__copyright__ = 'Oregon State University'
__credits__ = ['Stephen Ramsey', 'Yao Yao', 'Zheng Liu']
__license__ = 'MIT'
__version__ = '0.1.0'
__maintainer__ = ''
__email__ = ''
__status__ = 'Prototype'

import requests
import sys

class QueryReactome:

    API_BASE_URL = 'https://reactome.org/ContentService'

    @staticmethod
    def send_query_get(handler, url_suffix):
        url_str = QueryReactome.API_BASE_URL + "/" + handler + "/" + url_suffix
#        print(url_str)
        res = requests.get(url_str, headers={'accept': 'application/json'})
        status_code = res.status_code
        if status_code != 200:
            print("HTTP response status code: " + str(status_code) + " for URL:\n" + url_str, file=sys.stderr)
            res = None
        return res

    @staticmethod
    def query_uniprot_id_to_interacting_uniprot_ids(uniprot_id):
        res = QueryReactome.send_query_get("interactors/static/molecule", uniprot_id + "/details").json()
        res_uniprot_ids = dict()
        if res is not None:
            res_entities = res.get('entities', None)
            if res_entities is not None:
                for res_entity in res_entities:
                    res_entity_interactors = res_entity.get('interactors', None)
                    if res_entity_interactors is not None:
                        for res_entity_interactor in res_entity_interactors:
                            int_uniprot_id = res_entity_interactor.get('acc', None)
                            if int_uniprot_id is not None:
                                if 'CHEBI:' not in int_uniprot_id:
                                    int_alias = res_entity_interactor.get('alias', '')
                                    res_uniprot_ids[int_uniprot_id] = int_alias
        return res_uniprot_ids

    @staticmethod
    def query_uniprot_to_reactome_entity_id(uniprot_id):
        res = QueryReactome.send_query_get("data/complexes/UniProt", uniprot_id)
        if res is not None:
            res_json = res.json()
            #        print(res_json)
            if type(res_json)==list:
                ret_ids = set([res_entry["stId"] for res_entry in res_json])
            else:
                ret_ids = set()
        else:
            ret_ids = set()
        return ret_ids

    @staticmethod
    def query_uniprot_to_reactome_entity_id_desc(uniprot_id):
        res = QueryReactome.send_query_get("data/complexes/UniProt", uniprot_id)
        ret_ids = dict()
        if res is not None:
            res_json = res.json()
            if type(res_json)==list:
                ret_ids = dict([[res_entry["stId"], res_entry["displayName"]] for res_entry in res_json])
        return ret_ids

    @staticmethod
    def query_reactome_entity_id_to_reactome_pathway_ids(reactome_entity_id):
        res = QueryReactome.send_query_get("data/pathways/low/diagram/entity", reactome_entity_id + "/allForms?species=9606")
        if res is not None:
            res_json = res.json()
            reactome_ids_list = [res_entry["stId"] for res_entry in res_json]
            ret_set = set(reactome_ids_list)
        else:
            ret_set = set()
        return ret_set

    @staticmethod
    def query_reactome_entity_id_to_reactome_pathway_ids_desc(reactome_entity_id):
        res = QueryReactome.send_query_get("data/pathways/low/diagram/entity", reactome_entity_id + "/allForms?species=9606")
        if res is not None:
            res_json = res.json()
            reactome_ids_dict = dict([[res_entry["stId"], res_entry["displayName"]] for res_entry in res_json])
        else:
            reactome_ids_dict = dict()
        return reactome_ids_dict

    @staticmethod
    def query_uniprot_id_to_reactome_pathway_ids(uniprot_id):
        reactome_entity_ids = QueryReactome.query_uniprot_to_reactome_entity_id(uniprot_id)
        res_set = set()
        for reactome_entity_id in reactome_entity_ids:
            pathway_ids_set = QueryReactome.query_reactome_entity_id_to_reactome_pathway_ids(reactome_entity_id)
            if len(pathway_ids_set) > 0:
                res_set |= pathway_ids_set
        return res_set

    @staticmethod
    def query_uniprot_id_to_reactome_pathway_ids_desc(uniprot_id):
        reactome_entity_ids = QueryReactome.query_uniprot_to_reactome_entity_id(uniprot_id)
        res_dict = dict()
        for reactome_entity_id in reactome_entity_ids:
            pathway_ids_dict = QueryReactome.query_reactome_entity_id_to_reactome_pathway_ids_desc(reactome_entity_id)
            if len(pathway_ids_dict) > 0:
                res_dict.update(pathway_ids_dict)
        return res_dict

    @staticmethod
    def query_reactome_pathway_id_to_uniprot_ids(reactome_pathway_id):
        res = QueryReactome.send_query_get("data/participants", reactome_pathway_id)
        uniprot_ids_set = set()
        if res is not None:
            res_json = res.json()
            participant_ids_list = [refEntity["displayName"] for peDbEntry in res_json for refEntity in peDbEntry["refEntities"]]
            uniprot_ids_list = [id.split(" ")[0].split(":")[1] for id in participant_ids_list if "UniProt" in id]
            uniprot_ids_set = set(uniprot_ids_list)
        return uniprot_ids_set

    @staticmethod
    def query_reactome_pathway_id_to_uniprot_ids_desc(reactome_pathway_id):
        res = QueryReactome.send_query_get("data/participants", reactome_pathway_id)
        ret_dict = dict()
        if res is not None:
            res_json = res.json()
            #        print(res_json)
            participant_ids_list = [refEntity["displayName"] for peDbEntry in res_json for refEntity in peDbEntry["refEntities"]]
            uniprot_ids_list = [[id.split(" ")[0].split(":")[1], id.split(" ")[1]] for id in participant_ids_list if "UniProt" in id]
            ret_dict = dict(uniprot_ids_list)
        return ret_dict

if __name__ == '__main__':
    print(QueryReactome.query_uniprot_to_reactome_entity_id("P68871"))
    print(QueryReactome.query_uniprot_to_reactome_entity_id("O75521-2"))
    print(QueryReactome.query_reactome_entity_id_to_reactome_pathway_ids_desc("R-HSA-2230989"))
    print(QueryReactome.query_uniprot_id_to_interacting_uniprot_ids("Q13501"))
    print(QueryReactome.query_uniprot_id_to_reactome_pathway_ids_desc("P68871"))
    print(QueryReactome.query_reactome_pathway_id_to_uniprot_ids_desc("R-HSA-5423646"))
