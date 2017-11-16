import requests
import functools
import CachedMethods


class QueryBioLink:
    API_BASE_URL = {
        "get_phenotypes_for_disease": "https://api.monarchinitiative.org/api/bioentity/disease/{disease_id}/phenotypes",
        "get_diseases_for_gene": "https://api.monarchinitiative.org/api/bioentity/gene/{gene_id}/diseases",
        "get_genes_for_disease": "https://api.monarchinitiative.org/api/bioentity/disease/{disease_id}/genes",
        "get_phenotypes_for_gene": "https://api.monarchinitiative.org/api/bioentity/gene/{gene_id}/phenotypes?exclude_automatic_assertions=true&unselect_evidence=true",
        "get_genes_for_pathway": "https://api.monarchinitiative.org/api/bioentity/pathway/{pathway_id}/genes&unselect_evidence=true",
        "get_label_for_disease": "https://api.monarchinitiative.org/api/bioentity/disease/{disease_id}",
        "get_label_for_phenotype": "https://api.monarchinitiative.org/api/bioentity/phenotype/{phenotype_id}",
        "get_anatomies_for_gene": "https://api.monarchinitiative.org/api/bioentity/gene/{gene_id}/expression/anatomy",
        "get_genes_for_anatomy": "https://api.monarchinitiative.org/api/bioentity/anatomy/{anatomy_id}/genes",
        "get_anatomies_for_phenotype": "https://api.monarchinitiative.org/api/bioentity/phenotype/{phenotype_id}/anatomy"
    }

    @staticmethod
    def __access_api(url):
        # print(url)
        res = requests.get(url)

        status_code = res.status_code

        assert 200 == status_code, "Status code result: {}; url: {}".format(status_code, url)

        return res.json()

    @staticmethod
    @CachedMethods.register
    @functools.lru_cache(maxsize=1024, typed=False)
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
    def get_diseases_for_gene_desc(gene_id):
        """for a given NCBI Entrez Gene ID, returns a ``set`` of DOI disease identifiers for the gene

        :returns: a ``set`` containing ``str`` disease ontology identifiers
        """
        url = QueryBioLink.API_BASE_URL["get_diseases_for_gene"].format(gene_id=gene_id)
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
    def get_genes_for_disease_desc(disease_id):
        url = QueryBioLink.API_BASE_URL["get_genes_for_disease"].format(disease_id=disease_id)

        results = QueryBioLink.__access_api(url)['objects']

        assert len(results) <= 100, \
            "Found {} genes for disease {}. Crossed threshold 100.".format(len(results), disease_id)

        return results

    @staticmethod
    @CachedMethods.register
    @functools.lru_cache(maxsize=1024, typed=False)
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
    @CachedMethods.register
    @functools.lru_cache(maxsize=1024, typed=False)
    def get_phenotypes_for_gene_desc(ncbi_entrez_gene_id):
        phenotype_id_set = QueryBioLink.get_phenotypes_for_gene(ncbi_entrez_gene_id)
        ret_dict = dict()
        for phenotype_id_str in phenotype_id_set:
            phenotype_label_str = QueryBioLink.get_label_for_phenotype(phenotype_id_str)
            ret_dict[phenotype_id_str] = phenotype_label_str
        return ret_dict

    @staticmethod
    @CachedMethods.register
    @functools.lru_cache(maxsize=1024, typed=False)
    def get_anatomies_for_gene(gene_id):
        """for a given NCBI Entrez Gene ID, returns a ``dict`` of Anatomy IDs and labels for the gene

        :returns: a ``dict`` of <anatomy_ID, label>
        """
        url = QueryBioLink.API_BASE_URL["get_anatomies_for_gene"].format(gene_id=gene_id)

        results = QueryBioLink.__access_api(url)['associations']
        results = dict(map(lambda r: (r["object"]["id"], r["object"]["label"]), results))

        if len(results) > 200:
            print("Warning, got {} anatomies for gene {}".format(len(results), gene_id))

        return results

    @staticmethod
    @CachedMethods.register
    @functools.lru_cache(maxsize=1024, typed=False)
    def get_genes_for_anatomy(anatomy_id):
        """for a given Anatomy ID, returns a ``list`` of Gene ID for the anatomy

        :returns: a ``list`` of gene ID
        """
        url = QueryBioLink.API_BASE_URL["get_genes_for_anatomy"].format(anatomy_id=anatomy_id)

        results = QueryBioLink.__access_api(url)['associations']
        results = list(map(lambda r: r["subject"]["id"], results))

        if len(results) > 200:
            print("Warning, got {} genes for anatomy {}".format(len(results), anatomy_id))

        return results

    @staticmethod
    @CachedMethods.register
    @functools.lru_cache(maxsize=1024, typed=False)
    def get_anatomies_for_phenotype(phenotype_id):
        """for a given phenotype ID, returns a ``dict`` of Anatomy IDs and labels for the phenotype

        :returns: a ``dict`` of <anatomy_ID, label>
        """
        url = QueryBioLink.API_BASE_URL["get_anatomies_for_phenotype"].format(phenotype_id=phenotype_id)

        results = QueryBioLink.__access_api(url)
        results = dict(map(lambda r: (r["id"], r["label"]), results))

        if len(results) > 200:
            print("Warning, got {} anatomies for phenotype {}".format(len(results), phenotype_id))

        return results

if __name__ == '__main__':
    print(QueryBioLink.get_phenotypes_for_disease_desc("OMIM:605543"))
    print(QueryBioLink.get_phenotypes_for_gene_desc("NCBIGene:1080"))  # test for issue #22
    print(QueryBioLink.get_diseases_for_gene_desc("NCBIGene:407053"))
    print(QueryBioLink.get_genes_for_disease_desc("OMIM:605543"))
    print(QueryBioLink.get_diseases_for_gene_desc("NCBIGene:100048912"))
    print(QueryBioLink.get_phenotypes_for_gene_desc("NCBIGene:4750"))
    print(QueryBioLink.get_phenotypes_for_gene("NCBIGene:4750"))
    print(QueryBioLink.get_diseases_for_gene_desc("NCBIGene:4750"))
    print(QueryBioLink.get_diseases_for_gene_desc("NCBIGene:1111111"))
    print(QueryBioLink.get_label_for_disease("DOID:1498"))
    print(QueryBioLink.get_label_for_disease("OMIM:605543"))
    print(QueryBioLink.get_label_for_phenotype("HP:0000003"))
    print(QueryBioLink.get_anatomies_for_gene("NCBIGene:407053"))
    print(QueryBioLink.get_genes_for_anatomy("UBERON:0000006"))
    print(QueryBioLink.get_anatomies_for_phenotype("HP:0000003"))
