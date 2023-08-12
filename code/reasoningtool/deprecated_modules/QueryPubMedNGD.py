import requests
import urllib
import math

__author__ = 'Stephen Ramsey'
__copyright__ = 'Oregon State University'
__credits__ = ['Stephen Ramsey']
__license__ = 'MIT'
__version__ = '0.1.0'
__maintainer__ = ''
__email__ = ''
__status__ = 'Prototype'

class QueryPubMedNGD:
    PUBMED_URL = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&retmode=json&retmax=1000&term='

    @staticmethod
    def get_pubmed_hits_count(term_str):
        term_str_encoded = urllib.parse.quote(term_str, safe='')
        url_str = QueryPubMedNGD.PUBMED_URL + term_str_encoded
        res = requests.get(url_str)
        status_code = res.status_code
        if status_code != 200:
            print('HTTP response status code: ' + str(status_code) + ' for query term string {term}'.format(term=term_str))
            return None
        return int(res.json()['esearchresult']['count'])
    
    @staticmethod
    def normalized_google_distance(mesh1_str, mesh2_str):
        '''returns the normalized Google distance for two MeSH terms
        
        :returns: NGD, as a float (or math.nan if any counts are zero, or None if HTTP error)
        '''
        nij = QueryPubMedNGD.get_pubmed_hits_count('("{mesh1}"[MeSH Terms]) AND "{mesh2}"[MeSH Terms]'.format(mesh1=mesh1_str,
                                                                                               mesh2=mesh2_str))
        N = ngd_normalizer = 3.5e+7 * 20  # From PubMed home page there are 35 million articles (based on the information on https://pubmed.ncbi.nlm.nih.gov/ on 08/09/2023); avg 20 MeSH terms per article
        ni = QueryPubMedNGD.get_pubmed_hits_count('"{mesh1}"[MeSH Terms]'.format(mesh1=mesh1_str))
        nj = QueryPubMedNGD.get_pubmed_hits_count('"{mesh2}"[MeSH Terms]'.format(mesh2=mesh2_str))
        if ni == 0 or nj == 0 or nij == 0:
            return math.nan
        numerator = max(math.log(ni), math.log(nj)) - math.log(nij)
        denominator = math.log(N) - min(math.log(ni), math.log(nj))
        ngd = numerator/denominator
        return ngd
    
    @staticmethod
    def test_ngd():
        mesh1_str = 'Anemia, Sickle Cell'
        mesh2_str = 'Malaria'
        print(QueryPubMedNGD.normalized_google_distance(mesh1_str, mesh2_str))

if __name__ == '__main__':
    QueryPubMedNGD.test_ngd()

      
