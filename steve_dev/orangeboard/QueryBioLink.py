import requests
import functools
import CachedMethods


class QueryBioLink:
    API_BASE_URL = {
        "find_phenotype_by_disease": "https://api.monarchinitiative.org/api/bioentity/disease/{disease_id}/phenotypes/"
                                     "?fetch_objects=true&rows=10000",
        "find_disease_by_gene": "https://api.monarchinitiative.org/api/bioentity/gene/{gene_id}/diseases/"
                                "?fetch_objects=true&rows=10000",
        "find_gene_by_disease": "https://api.monarchinitiative.org/api/bioentity/disease/{disease_id}/genes/"
                                "?fetch_objects=true&rows=10000",
        "find_phenotype_by_gene": "https://api.monarchinitiative.org/api/bioentity/gene/{gene_id}/phenotypes/"
                                "?fetch_objects=true&rows=10000",
        "find_gene_by_pathway": "https://api.monarchinitiative.org/api/bioentity/pathway/{pathway_id}/genes/"
                                "?fetch_objects=true&rows=10000"
    }

    @staticmethod
    def __access_api(url):
        res = requests.get(url)

        assert 200 == res.status_code

        return res.json()["objects"]

    @staticmethod
    @CachedMethods.register
    @functools.lru_cache(maxsize=1024, typed=False)
    def find_phenotype_by_disease(disease_id):
        url = QueryBioLink.API_BASE_URL["find_phenotype_by_disease"].format(disease_id=disease_id)

        results = QueryBioLink.__access_api(url)

        assert len(results) <= 100, \
            "Found {} phenotypes for disease {}. Crossed threshold 100.".format(len(results), disease_id)

        return results

    @staticmethod
    @CachedMethods.register
    @functools.lru_cache(maxsize=1024, typed=False)
    def find_disease_by_gene(gene_id):
        url = QueryBioLink.API_BASE_URL["find_disease_by_gene"].format(gene_id=gene_id)

        results = QueryBioLink.__access_api(url)

        assert len(results) <= 100, \
            "Found {} diseases for gene {}. Crossed threshold 100.".format(len(results), gene_id)

        return results

    @staticmethod
    @CachedMethods.register
    @functools.lru_cache(maxsize=1024, typed=False)
    def find_gene_by_disease(disease_id):
        url = QueryBioLink.API_BASE_URL["find_gene_by_disease"].format(disease_id=disease_id)

        results = QueryBioLink.__access_api(url)

        assert len(results) <= 100, \
            "Found {} genes for disease {}. Crossed threshold 100.".format(len(results), disease_id)

        return results

    @staticmethod
    @CachedMethods.register
    @functools.lru_cache(maxsize=1024, typed=False)
    def find_phenotype_by_gene(gene_id):
        url = QueryBioLink.API_BASE_URL["find_phenotype_by_gene"].format(gene_id=gene_id)

        results = QueryBioLink.__access_api(url)

        assert len(results) <= 100, \
            "Found {} phenotypes for gene {}. Crossed threshold 100.".format(len(results), gene_id)

        return results


if __name__ == '__main__':
    print(QueryBioLink.find_phenotype_by_disease("OMIM:605543"))
    print(QueryBioLink.find_disease_by_gene("NCBIGene:4750"))
    print(QueryBioLink.find_gene_by_disease("OMIM:605543"))
    print(QueryBioLink.find_phenotype_by_gene("NCBIGene:4750"))
