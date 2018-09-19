''' This module defines the class QueryBioLink. QueryBioLink class is designed
to communicate with Monarch APIs and their corresponding data sources. The
available methods include:
    * query phenotype for disease
    * query disease for gene
    * query gene for disease
    * query phenotype for gene
    * query gene for pathway
    * query label for disease
    * query label for phenotype
    * query anatomy for gene
    * query gene for anatomy
    * query anatomy for phenotype
'''

__author__ = 'Zheng Liu'
__copyright__ = 'Oregon State University'
__credits__ = ['Zheng Liu', 'Stephen Ramsey', 'Yao Yao']
__license__ = 'MIT'
__version__ = '0.1.0'
__maintainer__ = ''
__email__ = ''
__status__ = 'Prototype'

import requests
import requests_cache
import sys
import json


class QueryBioLink:
    TIMEOUT_SEC = 120
    API_BASE_URL = 'https://api.monarchinitiative.org/api/bioentity'
    HANDLER_MAP = {
        'get_phenotypes_for_disease':  'disease/{disease_id}/phenotypes',
        'get_diseases_for_gene':       'gene/{gene_id}/diseases',
        'get_genes_for_disease':       'disease/{disease_id}/genes',
        'get_phenotypes_for_gene':     'gene/{gene_id}/phenotypes?exclude_automatic_assertions=true&unselect_evidence=true',
        'get_genes_for_pathway':       'pathway/{pathway_id}/genes&unselect_evidence=true',
        'get_label_for_disease':       'disease/{disease_id}',
        'get_label_for_phenotype':     'phenotype/{phenotype_id}',
        'get_anatomies_for_gene':      'gene/{gene_id}/expression/anatomy',
        'get_genes_for_anatomy':       'anatomy/{anatomy_id}/genes',
        'get_anatomies_for_phenotype': 'phenotype/{phenotype_id}/anatomy',
        'get_synonyms_for_disease':    '{disease_id}/associations',
        'get_anatomy':                  'anatomy/{id}',
        'get_phenotype':                'phenotype/{id}',
        'get_disease':                  'disease/{id}',
        'get_bio_process':              '{id}',
        'map_disease_to_phenotype':    'disease/{disease_id}/phenotypes'
    }

    @staticmethod
    def __access_api(handler):
        
        url = QueryBioLink.API_BASE_URL + '/' + handler
        
        try:
            res = requests.get(url, timeout=QueryBioLink.TIMEOUT_SEC)
        except requests.exceptions.Timeout:
            print(url, file=sys.stderr)
            print('Timeout in QueryBioLink for URL: ' + url, file=sys.stderr)
            return None
        except KeyboardInterrupt:
            sys.exit(0)
        except BaseException as e:
            print(url, file=sys.stderr)
            print('%s received in QueryBioLink for URL: %s' % (e, url), file=sys.stderr)
            return None
        status_code = res.status_code
        if status_code != 200:
            print(url, file=sys.stderr)
            print('Status code ' + str(status_code) + ' for url: ' + url, file=sys.stderr)
            return None

        return res.json()

    @staticmethod
    def get_label_for_disease(disease_id):
        handler = QueryBioLink.HANDLER_MAP['get_label_for_disease'].format(disease_id=disease_id)
        results = QueryBioLink.__access_api(handler)
        result_str = 'None'
        if results is not None:
            result_str = results['label']
        return result_str

    @staticmethod
    def get_phenotypes_for_disease_desc(disease_id):
        handler = QueryBioLink.HANDLER_MAP['get_phenotypes_for_disease'].format(disease_id=disease_id)
        results = QueryBioLink.__access_api(handler)
        ret_dict = dict()
        if results is None:
            return ret_dict
        res_list = results['objects']
        if len(res_list) > 200:
            print('Number of phenotypes found for disease: ' + disease_id + ' is: ' + str(len(res_list)), file=sys.stderr)
        for phenotype_id_str in res_list:
            if phenotype_id_str.startswith("AQTLTrait:"):
                continue
            phenotype_label_str = QueryBioLink.get_label_for_phenotype(phenotype_id_str)
            ret_dict[phenotype_id_str] = phenotype_label_str

        return ret_dict

    @staticmethod
    def get_diseases_for_gene_desc(gene_id):
        '''for a given NCBI Entrez Gene ID, returns a ``set`` of DOI disease identifiers for the gene

        :returns: a ``set`` containing ``str`` disease ontology identifiers
        '''
        handler = QueryBioLink.HANDLER_MAP['get_diseases_for_gene'].format(gene_id=gene_id)
        results = QueryBioLink.__access_api(handler)
        ret_data = dict()
        if results is None:
            return ret_data
        
        ret_list = results['objects']
        
        if len(ret_list) > 200:
            print('Number of diseases found for gene ' + gene_id + ' is: ' + str(len(ret_list)), file=sys.stderr)

        for disease_id in ret_list:
            if 'DOID:' in disease_id or 'OMIM:' in disease_id:
                ret_data[disease_id] = QueryBioLink.get_label_for_disease(disease_id)

        return ret_data

    @staticmethod
    def get_genes_for_disease_desc(disease_id):
        handler = QueryBioLink.HANDLER_MAP['get_genes_for_disease'].format(disease_id=disease_id)

        results = QueryBioLink.__access_api(handler)
        ret_list = []
        if results is None:
            return ret_list
        ret_list = results['objects']

        if len(ret_list) > 100:
            print('number of genes found for disease ' + disease_id + ' is: ' + str(len(ret_list)), file=sys.stderr)
        return ret_list

    @staticmethod
    def get_label_for_phenotype(phenotype_id_str):
        handler = QueryBioLink.HANDLER_MAP['get_label_for_phenotype'].format(phenotype_id=phenotype_id_str)
        results = QueryBioLink.__access_api(handler)
        result_str = 'None'
        if results is not None:
            result_str = results['label']
        return result_str

    @staticmethod
    def get_phenotypes_for_gene(gene_id):
        handler = QueryBioLink.HANDLER_MAP['get_phenotypes_for_gene'].format(gene_id=gene_id)

        results = QueryBioLink.__access_api(handler)
        ret_list = []
        if results is None:
            return ret_list
        ret_list = results['objects']

        if len(ret_list) > 200:
            print('Warning, got ' + str(len(ret_list)) + ' phenotypes for gene ' + gene_id, file=sys.stderr)

        return ret_list

    @staticmethod
    def get_phenotypes_for_gene_desc(ncbi_entrez_gene_id):
        phenotype_id_set = QueryBioLink.get_phenotypes_for_gene(ncbi_entrez_gene_id)
        ret_dict = dict()
        for phenotype_id_str in phenotype_id_set:
            phenotype_label_str = QueryBioLink.get_label_for_phenotype(phenotype_id_str)
            if 'HP:' in phenotype_id_str:
                ret_dict[phenotype_id_str] = phenotype_label_str
        return ret_dict

    @staticmethod
    def get_anatomies_for_gene(gene_id):
        '''for a given NCBI Entrez Gene ID, returns a ``dict`` of Anatomy IDs and labels for the gene

        :returns: a ``dict`` of <anatomy_ID, label>
        '''
        handler = QueryBioLink.HANDLER_MAP['get_anatomies_for_gene'].format(gene_id=gene_id)

        results = QueryBioLink.__access_api(handler)
        ret_dict = dict()
        if results is None:
            return ret_dict
        res_dict = results['associations']
        ret_dict = dict(map(lambda r: (r['object']['id'], r['object']['label']), res_dict))

        if len(ret_dict) > 200:
            print('Warning, got {} anatomies for gene {}'.format(len(ret_dict), gene_id), file=sys.stderr)

        return ret_dict

    @staticmethod
    def get_genes_for_anatomy(anatomy_id):
        '''for a given Anatomy ID, returns a ``list`` of Gene ID for the anatomy

        :returns: a ``list`` of gene ID
        '''
        handler = QueryBioLink.HANDLER_MAP['get_genes_for_anatomy'].format(anatomy_id=anatomy_id)

        results = QueryBioLink.__access_api(handler)
        ret_list = []
        if results is None:
            return ret_list
        res_dict = results['associations']
        ret_list = list(map(lambda r: r['subject']['id'], res_dict))

        if len(ret_list) > 200:
            print('Warning, got {} genes for anatomy {}'.format(len(ret_list), anatomy_id), file=sys.stderr)

        return ret_list

    @staticmethod
    def get_anatomies_for_phenotype(phenotype_id):
        '''for a given phenotype ID, returns a ``dict`` of Anatomy IDs and labels for the phenotype

        :returns: a ``dict`` of <anatomy_ID, label>
        '''
        handler = QueryBioLink.HANDLER_MAP['get_anatomies_for_phenotype'].format(phenotype_id=phenotype_id)

        results = QueryBioLink.__access_api(handler)
        ret_dict = dict()
        if results is None:
            return ret_dict
        
        ret_dict = dict(map(lambda r: (r['id'], r['label']), results))

        if len(ret_dict) > 200:
            print('Warning, got {} anatomies for phenotype {}'.format(len(ret_dict), phenotype_id), file=sys.stderr)

        return ret_dict

    @staticmethod
    def __get_entity(entity_type, entity_id):
        handler = QueryBioLink.HANDLER_MAP[entity_type].format(id=entity_id)
        results = QueryBioLink.__access_api(handler)
        result_str = 'None'
        if results is not None:
            #   remove all \n characters using json api and convert the string to one line
            result_str = json.dumps(results)
        return result_str

    @staticmethod
    def get_anatomy_entity(anatomy_id):
        return QueryBioLink.__get_entity("get_anatomy", anatomy_id)

    @staticmethod
    def get_phenotype_entity(phenotype_id):
        return QueryBioLink.__get_entity("get_phenotype", phenotype_id)

    @staticmethod
    def get_disease_entity(disease_id):
        return QueryBioLink.__get_entity("get_disease", disease_id)

    @staticmethod
    def get_bio_process_entity(bio_process_id):
        return QueryBioLink.__get_entity("get_bio_process", bio_process_id)

    @staticmethod
    def map_disease_to_phenotype(disease_id):
        """
        Mapping a disease to a list of phenotypes
        :param disease_id: The DOID / OMIM ID for a disease
        :return: A list of phenotypes HP IDs, or an empty array if no HP IDs are found
        """
        hp_array = []
        if not isinstance(disease_id, str) or (disease_id[:5] != "OMIM:" and disease_id[:5] != "DOID:"):
            return hp_array
        handler = QueryBioLink.HANDLER_MAP['map_disease_to_phenotype'].format(disease_id=disease_id)
        results = QueryBioLink.__access_api(handler)
        if results is not None:
            if 'objects' in results.keys():
                hp_array = results['objects']
        return hp_array


if __name__ == '__main__':
    # print(QueryBioLink.get_genes_for_disease_desc('MONDO:0005359'))
    # print(QueryBioLink.get_phenotypes_for_disease_desc('MONDO:0005359'))
    # print(QueryBioLink.get_phenotypes_for_disease_desc('OMIM:605543'))
    # print(QueryBioLink.get_genes_for_disease_desc('OMIM:XXXXXX'))
    # print(QueryBioLink.get_genes_for_disease_desc('OMIM:605543'))
    # print(QueryBioLink.get_phenotypes_for_gene_desc('NCBIGene:1080'))  # test for issue #22
    # print(QueryBioLink.get_diseases_for_gene_desc('NCBIGene:407053'))
    # print(QueryBioLink.get_diseases_for_gene_desc('NCBIGene:100048912'))
    # print(QueryBioLink.get_phenotypes_for_gene_desc('NCBIGene:4750'))
    # print(QueryBioLink.get_phenotypes_for_gene('NCBIGene:4750'))
    # print(QueryBioLink.get_diseases_for_gene_desc('NCBIGene:4750'))
    # print(QueryBioLink.get_diseases_for_gene_desc('NCBIGene:1111111'))
    # print(QueryBioLink.get_label_for_disease('DOID:1498'))
    # print(QueryBioLink.get_label_for_disease('OMIM:605543'))
    # print(QueryBioLink.get_label_for_phenotype('HP:0000003'))
    # print(QueryBioLink.get_anatomies_for_gene('NCBIGene:407053'))
    # print(QueryBioLink.get_genes_for_anatomy('UBERON:0000006'))
    # print(QueryBioLink.get_anatomies_for_phenotype('HP:0000003'))

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

    # save_to_test_file('UBERON:0004476', QueryBioLink.get_anatomy_entity('UBERON:0004476'))
    # save_to_test_file('HP:0011515', QueryBioLink.get_phenotype_entity('HP:0011515'))
    # save_to_test_file('DOID:3965', QueryBioLink.get_disease_entity('DOID:3965'))
    # save_to_test_file('GO:0097289', QueryBioLink.get_bio_process_entity('GO:0097289'))

    #   PARKINSON DISEASE 4
    print(QueryBioLink.map_disease_to_phenotype("OMIM:605543"))
