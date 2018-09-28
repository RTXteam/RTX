''' This module defines the class QueryProteinEntity. QueryProteinEntity class is designed
to query protein entity from mygene library. The
available methods include:

    get_protein_entity : query protein properties by ID
    get_microRNA_entity : query micro properties by ID

'''

__author__ = 'Deqing Qu'
__copyright__ = 'Oregon State University'
__credits__ = ['Deqing Qu', 'Stephen Ramsey']
__license__ = 'MIT'
__version__ = '0.1.0'
__maintainer__ = ''
__email__ = ''
__status__ = 'Prototype'

import mygene
import requests_cache
import json

class QueryMyGeneExtended:

    @staticmethod
    def get_protein_entity(protein_id):
        mg = mygene.MyGeneInfo()
        results = str(mg.query(protein_id.replace('UniProtKB', 'UniProt'), fields='all', return_raw='True', verbose=False))
        result_str = 'None'
        if len(results) > 100:
            json_dict = json.loads(results)
            result_str = json.dumps(json_dict)
        return result_str

    @staticmethod
    def get_microRNA_entity(microrna_id):
        mg = mygene.MyGeneInfo()
        results = str(mg.query(microrna_id.replace('NCBIGene', 'entrezgene'), fields='all', return_raw='True', verbose=False))
        result_str = 'None'
        if len(results) > 100:
            json_dict = json.loads(results)
            result_str = json.dumps(json_dict)
        return result_str

    @staticmethod
    def get_protein_desc(protein_id):
        result_str = QueryMyGeneExtended.get_protein_entity(protein_id)
        desc = "None"
        if result_str != "None":
            result_dict = json.loads(result_str)
            if "hits" in result_dict.keys():
                if len(result_dict["hits"]) > 0:
                    if "summary" in result_dict["hits"][0].keys():
                        desc = result_dict["hits"][0]["summary"]
        return desc

    @staticmethod
    def get_microRNA_desc(protein_id):
        result_str = QueryMyGeneExtended.get_microRNA_entity(protein_id)
        desc = "None"
        if result_str != "None":
            result_dict = json.loads(result_str)
            if "hits" in result_dict.keys():
                if len(result_dict["hits"]) > 0:
                    if "summary" in result_dict["hits"][0].keys():
                        desc = result_dict["hits"][0]["summary"]
        return desc

if __name__ == '__main__':

    def save_to_test_file(filename, key, value):
        f = open(filename, 'r+')
        try:
            json_data = json.load(f)
        except ValueError:
            json_data = {}
        f.seek(0)
        f.truncate()
        json_data[key] = value
        json.dump(json_data, f)
        f.close()

    save_to_test_file('tests/query_test_data.json', 'UniProtKB:O60884', QueryMyGeneExtended.get_protein_entity("UniProtKB:O60884"))
    save_to_test_file('tests/query_test_data.json', 'NCBIGene: 100847086', QueryMyGeneExtended.get_microRNA_entity("NCBIGene: 100847086"))
    save_to_test_file('tests/query_desc_test_data.json', 'UniProtKB:O60884', QueryMyGeneExtended.get_protein_desc("UniProtKB:O60884"))
    save_to_test_file('tests/query_desc_test_data.json', 'UniProtKB:O608840', QueryMyGeneExtended.get_protein_desc("UniProtKB:O608840"))
    save_to_test_file('tests/query_desc_test_data.json', 'NCBIGene: 100847086', QueryMyGeneExtended.get_microRNA_desc("NCBIGene:100847086"))
    save_to_test_file('tests/query_desc_test_data.json', 'NCBIGene: 1008470860', QueryMyGeneExtended.get_microRNA_desc("NCBIGene:1008470860"))
    print(QueryMyGeneExtended.get_protein_desc("UniProtKB:O60884"))
    # print(QueryMyGeneExtended.get_microRNA_desc("NCBIGene:1008470860"))
