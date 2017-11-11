import requests
import functools
import CachedMethods

class QueryBioLink:
    API_BASE_URL = {
        "get_phenotypes_for_disease": "https://api.monarchinitiative.org/api/bioentity/disease/{disease_id}/phenotypes/"
                                     "?fetch_objects=true&rows=10000",
        "find_disease_by_gene": "https://api.monarchinitiative.org/api/bioentity/gene/{gene_id}/diseases/"
                                "?fetch_objects=true&rows=10000",
        "find_gene_by_disease": "https://api.monarchinitiative.org/api/bioentity/disease/{disease_id}/genes/"
                                "?fetch_objects=true&rows=10000",
        "get_phenotypes_for_gene": "https://api.monarchinitiative.org/api/bioentity/gene/{gene_id}/phenotypes/"
                                "?fetch_objects=true&rows=10000",
        "find_gene_by_pathway": "https://api.monarchinitiative.org/api/bioentity/pathway/{pathway_id}/genes/"
                                "?fetch_objects=true&rows=10000",
        "get_label_for_disease": "https://api.monarchinitiative.org/api/bioentity/disease/{disease_id}",
        "get_label_for_phenotype": "https://api.monarchinitiative.org/api/bioentity/phenotype/{phenotype_id}"
    }

    @staticmethod
    def __access_api(url):
        print(url)
        res = requests.get(url)
        assert 200 == res.status_code
        return res.json()

    @staticmethod
    def get_label_for_disease(disease_id):
        url = QueryBioLink.API_BASE_URL["get_label_for_disease"].format(disease_id=disease_id)
        results = QueryBioLink.__access_api(url)
        result_str = 'UNKNOWN'
        if results is not None:
            result_str = results['label']
        return result_str
        
    @staticmethod
    @CachedMethods.register
    @functools.lru_cache(maxsize=1024, typed=False)
    def get_phenotypes_for_disease_desc(disease_id):
        url = QueryBioLink.API_BASE_URL["get_phenotypes_for_disease"].format(disease_id=disease_id)
        results = QueryBioLink.__access_api(url)['objects']
        if len(results) > 200:
            print('Number of phenotypes found for disease: ' + disease_id + ' is: ' + str(len(results)))
        ret_dict = dict()
        for phenotype_id_str in results:
            phenotype_label_str = QueryBioLink.get_label_for_phenotype(phenotype_id_str)
            ret_dict[phenotype_id_str] = phenotype_label_str

        return ret_dict
       
    @staticmethod
    @CachedMethods.register
    @functools.lru_cache(maxsize=1024, typed=False)
    def find_diseases_by_gene(gene_id):
        '''for a given NCBI Entrez Gene ID, returns a ``set`` of DOI disease identifiers for the gene

        :returns: a ``set`` containing ``str`` disease ontology identifiers
        '''
        url = QueryBioLink.API_BASE_URL["find_disease_by_gene"].format(gene_id=gene_id)

        results = QueryBioLink.__access_api(url)['objects']

        if len(results) > 200:
            print('Number of diseases found for gene ' + gene_id + ' is: ' + str(len(results)))

        ret_data = dict()
        for disease_id in results:
            if 'DOID:' in disease_id or 'OMIM:' in disease_id:
                ret_data[disease_id] = QueryBioLink.get_label_for_disease(disease_id)

        return ret_data

    @staticmethod
    @CachedMethods.register
    @functools.lru_cache(maxsize=1024, typed=False)
    def find_gene_by_disease(disease_id):
        url = QueryBioLink.API_BASE_URL["find_gene_by_disease"].format(disease_id=disease_id)

        results = QueryBioLink.__access_api(url)['objects']

        assert len(results) <= 100, \
            "Found {} genes for disease {}. Crossed threshold 100.".format(len(results), disease_id)

        return results

    @staticmethod
    def get_label_for_phenotype(phenotype_id_str):
        url = QueryBioLink.API_BASE_URL["get_label_for_phenotype"].format(phenotype_id=phenotype_id_str)
        results = QueryBioLink.__access_api(url)
        result_str = 'UNKNOWN'
        if results is not None:
            result_str = results['label']
        return result_str

    @staticmethod
    @CachedMethods.register
    @functools.lru_cache(maxsize=1024, typed=False)
    def get_phenotypes_for_gene(gene_id):
        url = QueryBioLink.API_BASE_URL["get_phenotypes_for_gene"].format(gene_id=gene_id)

        results = QueryBioLink.__access_api(url)['objects']

        if len(results) > 200:
            print("Warning, got " + str(len(results)) + " phenotypes for gene " + gene_id)
            
        return results

    @staticmethod
    def get_phenotypes_for_gene_desc(ncbi_entrez_gene_id):
        phenotype_id_set = QueryBioLink.get_phenotypes_for_gene(ncbi_entrez_gene_id)
        ret_dict = dict()
        for phenotype_id_str in phenotype_id_set:
            phenotype_label_str = QueryBioLink.get_label_for_phenotype(phenotype_id_str)
            ret_dict[phenotype_id_str] = phenotype_label_str
        return ret_dict

if __name__ == '__main__':
    print(QueryBioLink.get_phenotypes_for_disease_desc("OMIM:605543"))
    print(QueryBioLink.get_phenotypes_for_gene_desc("NCBIGene:4750"))
    print(QueryBioLink.get_phenotypes_for_gene("NCBIGene:4750"))
    print(QueryBioLink.find_diseases_by_gene("NCBIGene:4750"))
    print(QueryBioLink.find_diseases_by_gene("NCBIGene:1111111"))
    print(QueryBioLink.find_gene_by_disease("OMIM:605543"))
    print(QueryBioLink.get_label_for_disease("DOID:1498"))
    print(QueryBioLink.get_label_for_disease("OMIM:605543"))
    print(QueryBioLink.get_label_for_phenotype("HP:0000003"))
    
