import requests
import sys

class QueryReactome:

    API_BASE_URL = 'https://reactome.org/ContentService'

    @staticmethod
    def send_query_get(handler, url_suffix):  ## :WEIRD: Reactome REST API GET syntax doesn't want a question mark in the URL
        url_str = QueryReactome.API_BASE_URL + "/" + handler + "/" + url_suffix
        print(url_str)
        res = requests.get(url_str, headers={'accept': 'application/json'})
        status_code = res.status_code
        assert status_code in [200, 404]
        return res

    @staticmethod
    def query_uniprot_to_reactome_entity_id(uniprot_id):
        res_json = QueryReactome.send_query_get("data/complexes/UniProt", uniprot_id).json()
        if type(res_json)==list:
            ret_ids = set([res_entry["stId"] for res_entry in res_json])
        else:
            ret_ids = set()
        return ret_ids

    @staticmethod
    def query_reactome_entity_id_to_reactome_pathway_ids(reactome_entity_id):
        res_json = QueryReactome.send_query_get("data/pathways/low/diagram/entity", reactome_entity_id + "/allForms?species=9606").json()
        reactome_ids_list = [res_entry["stId"] for res_entry in res_json]
        return set(reactome_ids_list)

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
    def query_reactome_pathway_id_to_uniprot_ids(reactome_pathway_id):
        res_json = QueryReactome.send_query_get("data/participants", reactome_pathway_id).json()
        participant_ids_list = [refEntity["displayName"] for peDbEntry in res_json for refEntity in peDbEntry["refEntities"]]
        uniprot_ids_list = [id.split(" ")[0].split(":")[1] for id in participant_ids_list if "UniProt" in id]
        return set(uniprot_ids_list)
    
    # @staticmethod
    # def uniprot_to_reactome_entity_id(uniprot_id):
    #     handler = 'data/complexes/UniProt'
    #     url_suffix = uniprot_id
    #     res = QueryReactome.send_query_get(handler, url_suffix)
    #     return res.json()

    @staticmethod
    def test():
        print(QueryReactome.query_uniprot_to_reactome_entity_id("P68871"))
        print(QueryReactome.query_uniprot_to_reactome_entity_id("O75521-2"))
        print(QueryReactome.query_reactome_entity_id_to_reactome_pathway_ids("R-HSA-2230989"))
        print(QueryReactome.query_uniprot_id_to_reactome_pathway_ids("P68871"))
        print(QueryReactome.query_reactome_pathway_id_to_uniprot_ids("R-HSA-5423646"))
        
if "--test" in set(sys.argv):
    QueryReactome.test()
        
