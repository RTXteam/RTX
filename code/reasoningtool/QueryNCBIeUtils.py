import requests
import urllib
import math
import sys

__author__ = 'Stephen Ramsey'
__copyright__ = 'Oregon State University'
__credits__ = ['Stephen Ramsey']
__license__ = 'MIT'
__version__ = '0.1.0'
__maintainer__ = ''
__email__ = ''
__status__ = 'Prototype'

class QueryNCBIeUtils:
    API_BASE_URL = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils'
    PUBMED_URL = API_BASE_URL + '/esearch.fcgi?db=pubmed&retmode=json&retmax=1000&term='

    @staticmethod
    def send_query_get(handler, url_suffix, retmax=1000):
        url_str = QueryNCBIeUtils.API_BASE_URL + '/' + handler + '?' + url_suffix + '&retmode=json&retmax=' + str(retmax)
#        print(url_str)
        res = requests.get(url_str, headers={'accept': 'application/json'})
        status_code = res.status_code
        if status_code != 200:
            print('HTTP response status code: ' + str(status_code) + ' for URL:\n' + url_str, file=sys.stderr)
            res = None
        return res

    def get_mesh_id_for_medgen_id(medgen_id):
        res = QueryNCBIeUtils.send_query_get('elink.fcgi',
                                             'db=mesh&dbfrom=medgen&cmd=neighbor&id=' + str(medgen_id))
        res_mesh_ids = set()
        if res is not None:
            res_json = res.json()
            res_linksets = res_json.get('linksets', None)
            if res_linksets is not None:
                for res_linkset in res_linksets:
                    res_linksetdbs = res_linkset.get('linksetdbs', None)
                    if res_linksetdbs is not None:
                        for res_linksetdb in res_linksetdbs:
                            res_meshids = res_linksetdb.get('links', None)
                            if res_meshids is not None:
                                for res_meshid in res_meshids:
                                    res_mesh_ids.add(int(res_meshid))
        return res_mesh_ids
                                             
    '''returns the NCBI MedGen UID for an OMIM ID

    :param omim_id: a string (eg: 'OMIM:1234')
    :returns: integer or None
    '''
    @staticmethod
    def get_medgen_id_for_omim_id(omim_id):
        res = QueryNCBIeUtils.send_query_get('esearch.fcgi',
                                             'db=medgen&term=' + omim_id)
        res_json = res.json()
        ret_ids = set()
        esearchresult = res_json.get('esearchresult', None)
        if esearchresult is not None:
            idlist = esearchresult.get('idlist', None)
            if idlist is not None:
                for id in idlist:
                    ret_ids.add(int(id))
        return ret_ids
    
    @staticmethod
    def get_pubmed_hits_count(term_str):
        term_str_encoded = urllib.parse.quote(term_str, safe='')
        res = QueryNCBIeUtils.send_query_get('esearch.fcgi',
                                             'db=pubmed&term=' + term_str_encoded)
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
        nij = QueryNCBIeUtils.get_pubmed_hits_count('("{mesh1}"[MeSH Terms]) AND "{mesh2}"[MeSH Terms]'.format(mesh1=mesh1_str,
                                                                                               mesh2=mesh2_str))
        N = 2.7e+7 * 20 # from PubMed home page there are 27 million articles; avg 20 MeSH terms per article
        ni = QueryNCBIeUtils.get_pubmed_hits_count('"{mesh1}"[MeSH Terms]'.format(mesh1=mesh1_str))
        nj = QueryNCBIeUtils.get_pubmed_hits_count('"{mesh2}"[MeSH Terms]'.format(mesh2=mesh2_str))
        if ni == 0 or nj == 0 or nij == 0:
            return math.nan
        numerator = max(math.log(ni), math.log(nj)) - math.log(nij)
        denominator = math.log(N) - min(math.log(ni), math.log(nj))
        ngd = numerator/denominator
        return ngd
    
    @staticmethod
    def test_ngd():
#        mesh1_str = 'Anemia, Sickle Cell'
#        mesh2_str = 'Malaria'
        omim1_str = '219700'
        omim2_str = '219550'
        print(QueryNCBIeUtils.normalized_google_distance(mesh1_str, mesh2_str))
              
if __name__ == '__main__':
    print(QueryNCBIeUtils.get_medgen_id_for_omim_id('OMIM:219700'))
    print(QueryNCBIeUtils.get_medgen_id_for_omim_id('OMIM:219550'))
    print(QueryNCBIeUtils.get_mesh_id_for_medgen_id(258573))
    
