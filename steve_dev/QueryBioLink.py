import requests


class QueryBioLink:
    API_BASE_URL = {
        "disease-phenotype": "https://api.monarchinitiative.org/api/bioentity/disease/{disease_id}/phenotypes/"
                             "?fetch_objects=true&rows=100",
        "gene-disease": "https://api.monarchinitiative.org/api/bioentity/gene/{gene_id}/diseases/"
                        "?fetch_objects=true&rows=100"
    }

    def find_phenotype_by_disease(self, disease_id):
        url = self.API_BASE_URL["disease-phenotype"].format(disease_id=disease_id)

        res = requests.get(url)

        assert 200 == res.status_code

        return res.json()["objects"]

    def find_disease_by_gene(self, gene_id):
        url = self.API_BASE_URL["gene-disease"].format(gene_id=gene_id)

        res = requests.get(url)

        assert 200 == res.status_code

        return res.json()["objects"]

if __name__ == '__main__':
    qbl = QueryBioLink()

    print(qbl.find_phenotype_by_disease("OMIM:605543"))
    print(qbl.find_disease_by_gene("NCBIGene:4750"))
