__author__ = 'Stephen Ramsey'
__copyright__ = 'Oregon State University'
__credits__ = ['Stephen Ramsey']
__license__ = 'MIT'
__version__ = '0.1.0'
__maintainer__ = ''
__email__ = ''
__status__ = 'Prototype'

import requests
import urllib
import math
import sys
import time

# MeSH Terms for Q1 diseases: (see git/q1/README.md)
#   Osteoporosis
#   HIV Infections
#   Cholera
#   Ebola Infection
#   Malaria
#   Osteomalacia
#   Hypercholesterolemia
#   Diabetes Mellitus, Type 2
#   Asthma
#   Pancreatitis, Chronic
#   Alzheimer Disease
#   Myocardial Infarction
#   Muscular Dystrophy, Duchenne
#   NGLY1 protein, human
#   Alcoholism
#   Depressive Disorder, Major
#   Niemann-Pick Disease, Type C
#   Huntington Disease
#   Alkaptonuria
#   Anemia, Sickle Cell
#   Stress Disorders, Post-Traumatic

class QueryNCBIeUtils:
    TIMEOUT_SEC = 120
    API_BASE_URL = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils'

    '''runs a query against eUtils (hard-coded for JSON response) and returns the results as a ``requests`` object
    
    :param handler: str handler, like ``elink.fcgi``
    :param url_suffix: str suffix to be appended on the URL after the "?" character
    :param retmax: int to specify the maximum number of records to return (default here 
                   is 1000, which is more useful than the NCBI default of 20)
    '''
    @staticmethod
    def send_query_get(handler, url_suffix, retmax=1000):
        url_str = QueryNCBIeUtils.API_BASE_URL + '/' + handler + '?' + url_suffix + '&retmode=json&retmax=' + str(retmax)
#        print(url_str)
        try:
            res = requests.get(url_str, headers={'accept': 'application/json'}, timeout=QueryNCBIeUtils.TIMEOUT_SEC)
        except requests.exceptions.Timeout:
            print('HTTP timeout in QueryNCBIeUtils.py; URL: ' + url_str, file=sys.stderr)
            time.sleep(1)  ## take a timeout because NCBI rate-limits connections
            return None
        except requests.exceptions.ConnectionError:
            print('HTTP connection error in QueryNCBIeUtils.py; URL: ' + url_str, file=sys.stderr)
            time.sleep(1)  ## take a timeout because NCBI rate-limits connections
            return None
        status_code = res.status_code
        if status_code != 200:
            print('HTTP response status code: ' + str(status_code) + ' for URL:\n' + url_str, file=sys.stderr)
            res = None
        return res

    @staticmethod
    def get_clinvar_uids_for_disease_or_phenotype_string(disphen_str):
        res = QueryNCBIeUtils.send_query_get('esearch.fcgi',
                                             'term=' + disphen_str + '[disease/phenotype]')
        res_set = set()
        if res is not None:
            res_json = res.json()
            esr = res_json.get('esearchresult', None)
            if esr is not None:
                idlist = esr.get('idlist', None)
                if idlist is not None:
                    res_set |= set([int(uid_str) for uid_str in idlist])
        return res_set
    
    '''returns a list of mesh UIDs for a given mesh term query

    '''
    @staticmethod
    def get_mesh_uids_for_mesh_term(mesh_term):
        res = QueryNCBIeUtils.send_query_get('esearch.fcgi',
                                             'db=mesh&term=' +  urllib.parse.quote(mesh_term + '[MeSH Terms]', safe=''))
        res_list = []
        if res is not None:
            res_json = res.json()
            res_esr = res_json.get('esearchresult', None)
            if res_esr is not None:
                res_idlist = res_esr.get('idlist', None)
                if res_idlist is not None:
                    res_list += res_idlist
        return res_list
        
    '''returns the mesh UID for a given medgen UID

    :param medgen_uid: integer
    :returns: set(integers) or ``None``
    '''
    @staticmethod
    def get_mesh_uid_for_medgen_uid(medgen_uid):
        res = QueryNCBIeUtils.send_query_get('elink.fcgi',
                                             'db=mesh&dbfrom=medgen&cmd=neighbor&id=' + str(medgen_uid))
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

    '''returns the mesh terms for a given MeSH Entrez UID

    :param mesh_uid: str
    :returns: list(str) of MeSH terms
    '''
    @staticmethod
    def get_mesh_terms_for_mesh_uid(mesh_uid):
        res = QueryNCBIeUtils.send_query_get('esummary.fcgi',
                                             'db=mesh&id=' + str(mesh_uid))
        ret_mesh = []
        if res is not None:
            res_json = res.json()
            res_result = res_json.get('result', None)
            if res_result is not None:
                uids = res_result.get('uids', None)
                if uids is not None:
                    assert type(uids)==list
                    for uid in uids:
                        assert type(uid)==str
                        res_uid = res_result.get(uid, None)
                        if res_uid is not None:
                            res_dsm = res_uid.get('ds_meshterms', None)
                            if res_dsm is not None:
                                assert type(res_dsm)==list
                                ret_mesh += res_dsm
        return ret_mesh
    
    '''returns the NCBI MedGen UID for an OMIM ID

    :param omim_id: integer
    :returns: set(integers) or None
    '''
    @staticmethod
    def get_medgen_uid_for_omim_id(omim_id):
        res = QueryNCBIeUtils.send_query_get('elink.fcgi',
                                             'db=medgen&dbfrom=omim&cmd=neighbor&id=' + str(omim_id))
        ret_medgen_ids = set()

        if res is not None:
            res_json = res.json()
            res_linksets = res_json.get('linksets', None)
            if res_linksets is not None:
                for res_linkset in res_linksets:
                    res_linksetdbs = res_linkset.get('linksetdbs', None)
                    if res_linksetdbs is not None:
                        for res_linksetdb in res_linksetdbs:
                            res_medgenids = res_linksetdb.get('links', None)
                            if res_medgenids is not None:
                                ret_medgen_ids |= set(res_medgenids)
        return ret_medgen_ids

    @staticmethod
    def get_mesh_terms_for_omim_id(omim_id):
        medgen_uids = QueryNCBIeUtils.get_medgen_uid_for_omim_id(omim_id)
        ret_mesh_terms = []
        for medgen_uid in medgen_uids:
            mesh_uids = QueryNCBIeUtils.get_mesh_uid_for_medgen_uid(medgen_uid)
            for mesh_uid in mesh_uids:
                mesh_terms = QueryNCBIeUtils.get_mesh_terms_for_mesh_uid(mesh_uid)
                ret_mesh_terms += list(mesh_terms)
        return ret_mesh_terms
        
    @staticmethod
    def get_pubmed_hits_count(term_str):
        term_str_encoded = urllib.parse.quote(term_str, safe='')
        res = QueryNCBIeUtils.send_query_get('esearch.fcgi',
                                             'db=pubmed&term=' + term_str_encoded)
        res_int = None
        if res is not None:
            status_code = res.status_code
            if status_code == 200:
                res_int = int(res.json()['esearchresult']['count'])
            else:
                print('HTTP response status code: ' + str(status_code) + ' for query term string {term}'.format(term=term_str))
        return res_int

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
    def is_mesh_term(mesh_term):
        ret_list = QueryNCBIeUtils.get_mesh_uids_for_mesh_term(mesh_term)
        return ret_list is not None and len(ret_list) > 0
    
    @staticmethod
    def test_ngd():
#        mesh1_str = 'Anemia, Sickle Cell'
#        mesh2_str = 'Malaria'
        omim1_str = '219700'
        omim2_str = '219550'
        print(QueryNCBIeUtils.normalized_google_distance(mesh1_str, mesh2_str))
              
if __name__ == '__main__':
#    print(QueryNCBIeUtils.get_clinvar_uids_for_disease_or_phenotype_string('hypercholesterolemia'))
#    print(QueryNCBIeUtils.get_mesh_uids_for_mesh_term('Anorexia Nervosa'))    
#    print(QueryNCBIeUtils.get_mesh_uids_for_mesh_term('Leukemia, Promyelocytic, Acute'))
#    print(QueryNCBIeUtils.get_mesh_uids_for_mesh_term('Leukemia, Myeloid, Acute'))
    
    # for mesh_term in ['Osteoporosis',
    #                   'HIV Infections',
    #                   'Cholera',
    #                   'Ebola Infection',
    #                   'Malaria',
    #                   'Osteomalacia',
    #                   'Hypercholesterolemia',
    #                   'Diabetes Mellitus, Type 2',
    #                   'Asthma',
    #                   'Pancreatitis, Chronic',
    #                   'Alzheimer Disease',
    #                   'Myocardial Infarction',
    #                   'Muscular Dystrophy, Duchenne',
    #                   'NGLY1 protein, human',
    #                   'Alcoholism',
    #                   'Depressive Disorder, Major',
    #                   'Niemann-Pick Disease, Type C',
    #                   'Huntington Disease',
    #                   'Alkaptonuria',
    #                   'Anemia, Sickle Cell',
    #                   'Stress Disorders, Post-Traumatic']:
    #     print(QueryNCBIeUtils.normalized_google_distance(mesh_term, QueryNCBIeUtils.get_mesh_terms_for_omim_id(219700)[0]))
              
    print(QueryNCBIeUtils.normalized_google_distance(
        QueryNCBIeUtils.get_mesh_terms_for_omim_id(219700)[0],
        "Cholera"))
              
    # print(QueryNCBIeUtils.get_mesh_terms_for_omim_id(219700)) # OMIM preferred name: "CYSTIC FIBROSIS"
    # print(QueryNCBIeUtils.get_mesh_terms_for_omim_id(125050)) # OMIM preferred name: "DEAFNESS WITH ANHIDROTIC ECTODERMAL DYSPLASIA"
    # print(QueryNCBIeUtils.get_mesh_terms_for_omim_id(310350)) # OMIM preferred name: "MYELOLYMPHATIC INSUFFICIENCY"
    # print(QueryNCBIeUtils.get_mesh_terms_for_omim_id(603903)) # OMIM preferred name: "SICKLE CELL ANEMIA"
    # print(QueryNCBIeUtils.get_mesh_terms_for_omim_id(612067)) # OMIM preferred name: "DYSTONIA 16; DYT16"
    # print(QueryNCBIeUtils.get_mesh_terms_for_omim_id(615113)) # OMIM preferred name: "MICROPHTHALMIA, ISOLATED 8; MCOP8"
    # print(QueryNCBIeUtils.get_mesh_terms_for_omim_id(615860)) # OMIM preferred name: "CONE-ROD DYSTROPHY 19; CORD19"
    # print(QueryNCBIeUtils.get_mesh_terms_for_omim_id(180200)) # OMIM preferred name: "RETINOBLASTOMA; RB1"
    # print(QueryNCBIeUtils.get_mesh_terms_for_omim_id(617062)) # OMIM preferred name: "OKUR-CHUNG NEURODEVELOPMENTAL SYNDROME; OCNDS"
    # print(QueryNCBIeUtils.get_mesh_terms_for_omim_id(617698)) # OMIM preferred name: "3-METHYLGLUTACONIC ACIDURIA, TYPE IX; MGCA9"
    # print(QueryNCBIeUtils.get_mesh_terms_for_mesh_uid(68003550))
    # print(QueryNCBIeUtils.get_medgen_uid_for_omim_id(219550))
    # print(QueryNCBIeUtils.get_mesh_uid_for_medgen_uid(41393))
    
