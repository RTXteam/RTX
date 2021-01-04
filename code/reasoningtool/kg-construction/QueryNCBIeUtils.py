__author__ = 'Stephen Ramsey'
__copyright__ = 'Oregon State University'
__credits__ = ['Stephen Ramsey', 'Finn Womack']
__license__ = 'MIT'
__version__ = '0.1.0'
__maintainer__ = ''
__email__ = ''
__status__ = 'Prototype'

# import requests
import urllib
import math
import sys
import time
from io import StringIO
import re
import pandas
import CachedMethods
# import requests_cache
from cache_control_helper import CacheControlHelper
# import requests

# requests_cache.install_cache('QueryNCBIeUtilsCache')
import numpy

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
    @CachedMethods.register
    def send_query_get(handler, url_suffix, retmax=1000, retry_flag = True):

        requests = CacheControlHelper()
        url_str = QueryNCBIeUtils.API_BASE_URL + '/' + handler + '?' + url_suffix + '&retmode=json&retmax=' + str(retmax)
#        print(url_str)
        try:
            res = requests.get(url_str, headers={'accept': 'application/json', 'User-Agent': 'Mozilla/5.0'}, timeout=QueryNCBIeUtils.TIMEOUT_SEC)
        except requests.exceptions.Timeout:
            print('HTTP timeout in QueryNCBIeUtils.py; URL: ' + url_str, file=sys.stderr)
            time.sleep(1)  ## take a timeout because NCBI rate-limits connections
            return None
        except requests.exceptions.ConnectionError:
            print('HTTP connection error in QueryNCBIeUtils.py; URL: ' + url_str, file=sys.stderr)
            time.sleep(1)  ## take a timeout because NCBI rate-limits connections
            return None
        except BaseException as e:
            print(url_str, file=sys.stderr)
            print('%s received in QueryMiRGate for URL: %s' % (e, url_str), file=sys.stderr)
            return None
        status_code = res.status_code
        if status_code != 200:
            if status_code == 429 and retry_flag:
                time.sleep(1)
                res = QueryNCBIeUtils.send_query_get(handler, url_suffix, retmax, False)
            else:
                print('HTTP response status code: ' + str(status_code) + ' for URL:\n' + url_str, file=sys.stderr)
                res = None
        return res

    @staticmethod
    #@CachedMethods.register
    def send_query_post(handler, params, retmax = 1000):

        requests = CacheControlHelper()
        url_str = QueryNCBIeUtils.API_BASE_URL + '/' + handler
        params['retmax'] = str(retmax)
        params['retmode'] = 'json'
#        print(url_str)
        try:
            res = requests.post(url_str, data=params, timeout=QueryNCBIeUtils.TIMEOUT_SEC)
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
    @CachedMethods.register
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
    
    '''returns a set of mesh UIDs for a given disease name

    '''
    @staticmethod
    @CachedMethods.register
    def get_mesh_uids_for_disease_or_phenotype_string(disphen_str):
        res = QueryNCBIeUtils.send_query_get('esearch.fcgi',
                                             'db=mesh&term=' + urllib.parse.quote(disphen_str + '[disease/phenotype]',safe=''))
        res_set = set()
        if res is not None:
            res_json = res.json()
            esr = res_json.get('esearchresult', None)
            if esr is not None:
                idlist = esr.get('idlist', None)
                if idlist is not None:
                    res_set |= set([int(uid_str) for uid_str in idlist])
        return res_set
    
    
    '''returns a list of mesh UIDs for a given mesh tree number

    '''
    @staticmethod
    @CachedMethods.register
    def get_mesh_uids_for_mesh_tree(mesh_term):
        res = QueryNCBIeUtils.send_query_get('esearch.fcgi',
                                             'db=mesh&term=' +  urllib.parse.quote(mesh_term, safe=''))
        res_list = []
        if res is not None:
            res_json = res.json()
            res_esr = res_json.get('esearchresult', None)
            if res_esr is not None:
                res_idlist = res_esr.get('idlist', None)
                if res_idlist is not None:
                    res_list += res_idlist
        return res_list
    
    '''returns a list of mesh UIDs for a given mesh term query

    '''
    @staticmethod
    @CachedMethods.register
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
    @CachedMethods.register
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

    :param mesh_uid: int (take the "D012345" form of the MeSH UID, remove the "D", convert to an integer, and add 
                     68,000,000 to the integer; then pass that integer as "mesh_uid" to this function)
    :returns: list(str) of MeSH terms
    '''
    @staticmethod
    #@CachedMethods.register
    def get_mesh_terms_for_mesh_uid(mesh_uid):
        assert type(mesh_uid)==int
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
    @CachedMethods.register
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
    @CachedMethods.register
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
    @CachedMethods.register
    def get_pubmed_hits_count(term_str, joint=False):
        term_str_encoded = urllib.parse.quote(term_str, safe='')
        res = QueryNCBIeUtils.send_query_get('esearch.fcgi',
                                             'db=pubmed&term=' + term_str_encoded)
        res_int = None
        if res is not None:
            status_code = res.status_code
            if status_code == 200:
                res_int = int(res.json()['esearchresult']['count'])
                if joint:
                    res_int = [res_int]
                    if 'errorlist' in res.json()['esearchresult'].keys():
                        if 'phrasesnotfound' in res.json()['esearchresult']['errorlist'].keys():
                                if len(res.json()['esearchresult']['errorlist']['phrasesnotfound']) == 1:
                                    res_int += 2*res.json()['esearchresult']['errorlist']['phrasesnotfound']
                                else:
                                    res_int += res.json()['esearchresult']['errorlist']['phrasesnotfound']
                    else:
                        res_int += [int(res.json()['esearchresult']['translationstack'][0]['count'])]
                        res_int += [int(res.json()['esearchresult']['translationstack'][1]['count'])]
            else:
                print('HTTP response status code: ' + str(status_code) + ' for query term string {term}'.format(term=term_str))
        return res_int

    @staticmethod
    @CachedMethods.register
    def normalized_google_distance(mesh1_str, mesh2_str, mesh1=True, mesh2=True):
        """
        returns the normalized Google distance for two MeSH terms
        :param mesh1_str_decorated: mesh string
        :param mesh2_str_decorated: mesh string
        :param mesh1: flag if mesh1_str is a MeSH term
        :param mesh2: flag if mesh2_str is a MeSH term
        :returns: NGD, as a float (or math.nan if any counts are zero, or None if HTTP error)
        """

        if mesh1:  # checks mesh flag then converts to mesh term search
            mesh1_str_decorated = mesh1_str + '[MeSH Terms]'
        else:
            mesh1_str_decorated = mesh1_str

        if mesh2:  # checks mesh flag then converts to mesh term search
            mesh2_str_decorated = mesh2_str + '[MeSH Terms]'
        else:
            mesh2_str_decorated = mesh2_str

        if mesh1 and mesh2:
            [nij, ni, nj] = QueryNCBIeUtils.get_pubmed_hits_count('({mesh1}) AND ({mesh2})'.format(mesh1=mesh1_str_decorated,
                                                                                     mesh2=mesh2_str_decorated),joint=True)
            if type(ni) == str:
                if mesh1_str_decorated == ni:
                    mesh1_str_decorated = ni[:-12]
                if mesh2_str_decorated == nj:
                    mesh2_str_decorated = nj[:-12]
                [nij, ni, nj] = QueryNCBIeUtils.get_pubmed_hits_count('({mesh1}) AND ({mesh2})'.format(mesh1=mesh1_str_decorated,
                                                                                         mesh2=mesh2_str_decorated), joint=True)

        else:
            nij = QueryNCBIeUtils.get_pubmed_hits_count('({mesh1}) AND ({mesh2})'.format(mesh1=mesh1_str_decorated,
                                                                                         mesh2=mesh2_str_decorated))
            ni = QueryNCBIeUtils.get_pubmed_hits_count('{mesh1}'.format(mesh1=mesh1_str_decorated))
            nj = QueryNCBIeUtils.get_pubmed_hits_count('{mesh2}'.format(mesh2=mesh2_str_decorated))
            if (ni == 0 and mesh1) or (nj == 0 and mesh2):
                if (ni == 0 and mesh1):
                    mesh1_str_decorated = mesh1_str
                if (nj == 0 and mesh2):
                    mesh2_str_decorated = mesh2_str
                nij = QueryNCBIeUtils.get_pubmed_hits_count('({mesh1}) AND ({mesh2})'.format(mesh1=mesh1_str_decorated,
                                                                                         mesh2=mesh2_str_decorated))
                ni = QueryNCBIeUtils.get_pubmed_hits_count('{mesh1}'.format(mesh1=mesh1_str_decorated))
                nj = QueryNCBIeUtils.get_pubmed_hits_count('{mesh2}'.format(mesh2=mesh2_str_decorated))
        N = 2.7e+7 * 20  # from PubMed home page there are 27 million articles; avg 20 MeSH terms per article
        if ni is None or nj is None or nij is None:
            return math.nan
        if ni == 0 or nj == 0 or nij == 0:
            return math.nan
        numerator = max(math.log(ni), math.log(nj)) - math.log(nij)
        denominator = math.log(N) - min(math.log(ni), math.log(nj))
        ngd = numerator/denominator
        return ngd

    @staticmethod
    def multi_pubmed_hits_count(term_str, n_terms = 1):
        '''
        This is almost the same as the above get_pubmed_hit_counts but is made to work with multi_normalized_google_distance
        '''
        term_str_encoded = urllib.parse.quote(term_str, safe='')
        res = QueryNCBIeUtils.send_query_get('esearch.fcgi',
                                             'db=pubmed&term=' + term_str_encoded)
        if res is None:
            params = {
                'db':'pubmed',
                'term' : term_str
            }
            res = QueryNCBIeUtils.send_query_post('esearch.fcgi',
                                                 params)
        res_int = None
        if res is not None:
            status_code = res.status_code
            if status_code == 200:
                if 'esearchresult' in res.json().keys():
                    if 'count' in res.json()['esearchresult'].keys():
                        res_int = [int(res.json()['esearchresult']['count'])]
                        if n_terms >= 2:
                            if 'errorlist' in res.json()['esearchresult'].keys():
                                if 'phrasesnotfound' in res.json()['esearchresult']['errorlist'].keys():
                                    if res.json()['esearchresult']['errorlist']['phrasesnotfound'] != []:
                                        res_int += res.json()['esearchresult']['errorlist']['phrasesnotfound']
                                    elif 'translationstack' in res.json()['esearchresult'].keys():
                                        for a in range(len(res.json()['esearchresult']['translationstack'])):
                                            if type(res.json()['esearchresult']['translationstack'][a]) == dict:
                                                res_int += [int(res.json()['esearchresult']['translationstack'][a]['count'])]
                                            elif res.json()['esearchresult']['translationstack'][a] == 'OR':
                                                res_int = [res_int[0]]
                                                res_int += ['null_flag']
                                                return res_int
                            else:
                                for a in range(len(res.json()['esearchresult']['translationstack'])):
                                    if type(res.json()['esearchresult']['translationstack'][a]) == dict:
                                        res_int += [int(res.json()['esearchresult']['translationstack'][a]['count'])]
                                    elif res.json()['esearchresult']['translationstack'][a] == 'OR':
                                        res_int = [res_int[0]]
                                        res_int += ['null_flag']
                                        return res_int
                    else:
                        return [0]*n_terms
            else:
                print('HTTP response status code: ' + str(status_code) + ' for query term string {term}'.format(term=term_str))
        if res_int is None:
            res_int = [0]*n_terms
        return res_int

    @staticmethod
    def multi_normalized_google_distance(name_list, mesh_flags = None):
        """
        returns the normalized Google distance for a list of n MeSH Terms
        :param name_list: a list of strings containing search terms for each node
        :param mesh_flags: a list of boolean values indicating which terms need [MeSH Terms] appended to it.
        :returns: NGD, as a float (or math.nan if any counts are zero, or None if HTTP error)
        """

        if mesh_flags is None:
            mesh_flags = [True]*len(name_list)
        elif len(name_list) != len(mesh_flags):
            print('Warning: mismatching lengths for input lists of names and flags returning None...')
            return None

        search_string='('

        if sum(mesh_flags) == len(mesh_flags):
            search_string += '[MeSH Terms]) AND ('.join(name_list) + '[MeSH Terms])'
            counts = QueryNCBIeUtils.multi_pubmed_hits_count(search_string, n_terms=len(name_list))
        else:
            for a in range(len(name_list)):
                search_string += name_list[a]
                if mesh_flags[a]:
                    search_string += "[MeSH Terms]"
                if a < len(name_list)-1:
                    search_string += ') AND ('
            search_string += ')'
            counts = QueryNCBIeUtils.multi_pubmed_hits_count(search_string, n_terms =1)
            for a in range(len(name_list)):
                name = name_list[a]
                if mesh_flags[a]:
                    name += "[MeSH Terms]"
                counts += QueryNCBIeUtils.multi_pubmed_hits_count(name, n_terms = 1)

        if type(counts[1]) == str:
            if counts[1] == 'null_flag':
                missed_names = [name + '[MeSH Terms]' for name in name_list]
            else:
                missed_names = counts[1:]
            counts = [counts[0]]
            for name in name_list:
                name_decorated = name + '[MeSH Terms]'
                if name_decorated in missed_names:
                    counts += QueryNCBIeUtils.multi_pubmed_hits_count(name, n_terms=1)
                else:
                    counts += QueryNCBIeUtils.multi_pubmed_hits_count(name_decorated, n_terms=1)

        N = 2.7e+7 * 20  # from PubMed home page there are 27 million articles; avg 20 MeSH terms per article
        if None in counts:
            return math.nan
        if 0 in counts:
            return math.nan
        numerator = max([math.log(x) for x in counts[1:]]) - math.log(counts[0])
        denominator = math.log(N) - min([ math.log(x) for x in counts[1:]])
        ngd = numerator/denominator
        return ngd

    @staticmethod
    @CachedMethods.register
    def get_pubmed_from_ncbi_gene(gene_id):
        '''
        Returns a list of pubmed ids associated with a given ncbi gene id
        :param gene_id: A string containing the ncbi gene id
        '''
        res = QueryNCBIeUtils.send_query_get('elink.fcgi',
                                             'db=pubmed&dbfrom=gene&id=' + str(gene_id))
        ret_pubmed_ids = set()
        pubmed_list = None

        if res is not None:
            res_json = res.json()
            res_linksets = res_json.get('linksets', None)
            if res_linksets is not None:
                for res_linkset in res_linksets:
                    res_linksetdbs = res_linkset.get('linksetdbs', None)
                    if res_linksetdbs is not None:
                        for res_linksetdb in res_linksetdbs:
                            res_pubmed_ids = res_linksetdb.get('links', None)
                            if res_pubmed_ids is not None:
                                ret_pubmed_ids |= set(res_pubmed_ids)
        if len(ret_pubmed_ids) > 0:
            pubmed_list = [ str(x) + '[uid]' for x in ret_pubmed_ids]
        return pubmed_list


    @staticmethod
    @CachedMethods.register
    def is_mesh_term(mesh_term):
        ret_list = QueryNCBIeUtils.get_mesh_uids_for_mesh_term(mesh_term)
        return ret_list is not None and len(ret_list) > 0

    @staticmethod
    #@CachedMethods.register
    def get_mesh_terms_for_hp_id(hp_id):
        '''
        This takes a hp id and converts it into a list of mesh term strings with [MeSH Terms] appened to the end
        :param hp_id: a string containing the hp id formatted as follows: "HP:000000"
        '''
        if(hp_id[0])!='"':
            hp_id = '"' + hp_id + '"'
        hp_id+= "[Source ID]"
        res = QueryNCBIeUtils.send_query_get('esearch.fcgi',
                                             'db=medgen&term=' + str(hp_id))
        ret_medgen_ids = set()

        if res is not None:
            res_json = res.json()
            res_result = res_json.get('esearchresult', None)
            if res_result is not None:
                res_idlist = res_result.get('idlist', None)
                if res_idlist is not None:
                    ret_medgen_ids |= set(res_idlist)
        mesh_ids = set()
        for medgen_id in ret_medgen_ids:
            res = QueryNCBIeUtils.send_query_get('elink.fcgi',
                                             'dbfrom=medgen&db=mesh&id=' + str(medgen_id))
            if res is not None:
                res_json = res.json()
                res_linksets = res_json.get('linksets', None)
                if res_linksets is not None:
                    for res_linkset in res_linksets:
                        res_linksetdbs = res_linkset.get('linksetdbs', None)
                        if res_linksetdbs is not None:
                            for res_linksetdb in res_linksetdbs:
                                res_mesh_ids = res_linksetdb.get('links', None)
                                if res_mesh_ids is not None:
                                    mesh_ids |= set(res_mesh_ids)
        mesh_terms = set()
        if len(mesh_ids) > 0:
            for mesh_id in mesh_ids:
                mesh_terms|= set(QueryNCBIeUtils.get_mesh_terms_for_mesh_uid(int(mesh_id)))
        if len(mesh_terms) > 0:
            mesh_terms = [mesh_term + '[MeSH Terms]' for mesh_term in mesh_terms]
            return mesh_terms
        else:
            return None
    
    @staticmethod
    def test_ngd():
        #mesh1_str = 'Anemia, Sickle Cell'
        #mesh2_str = 'Malaria'
        omim1_str = '219700'
        omim2_str = '219550'
        print(QueryNCBIeUtils.normalized_google_distance(mesh1_str, mesh2_str))

    @staticmethod
    @CachedMethods.register
    def get_uniprot_names(id):
        """
        Takes a uniprot id then return a string containing all synonyms listed on uniprot seperated by the deliminator |
        :param id: a string containing the uniprot id
        :returns: a string containing all synonyms uniprot lists for
        """
        # We want the actual uniprot name P176..., not the curie UniProtKB:P176...
        if "UniProtKB:" in id:
            id = ":".join(id.split(":")[1:])
        url = 'https://www.uniprot.org/uniprot/?query=id:' + id + '&sort=score&columns=entry name,protein names,genes&format=tab' # hardcoded url for uniprot data
        requests = CacheControlHelper()
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})  # send get request
        if r.status_code != 200:  # checks for error
            print('HTTP response status code: ' + str(r.status_code) + ' for URL:\n' + url, file=sys.stderr)
            return None
        if r.content.decode('utf-8') == '':
            return None
        df = pandas.read_csv(StringIO(r.content.decode('utf-8')), sep='\t')
        search = df.loc[0, 'Entry name']  # initializes search term variable
        if type(df.loc[0, 'Protein names']) == str:
            for name in re.compile("[()\[\]]").split(df.loc[0, 'Protein names']):  # checks for protein section
                if len(name) > 1:
                    if QueryNCBIeUtils.is_mesh_term(name):
                        search += '|' + name + '[MeSH Terms]'
                    else:
                        search += '|' + name
        if type(df.loc[0, 'Gene names']) == str:
            for name in df.loc[0, 'Gene names'].split(' '):
                if len(name) > 1:
                    if QueryNCBIeUtils.is_mesh_term(name):
                        search += '|' + name + '[MeSH Terms]'
                    else:
                        search += '|' + name
        return search

    @staticmethod
    @CachedMethods.register
    def get_reactome_names(id):
        '''
        Takes a reactome id then return a string containing all synonyms listed on reactome seperated by the deliminator |
        However, If it finds a MeSH terms in the list it will return the search term as a mesh term serach
        e.g. it will return something like '(IGF1R)[MeSH Terms]' 

        This can be inputed into the google function as a non mesh term and will search as a mesh term. 
        This is so that we do not need to handle the output of this function any differently it can all be input as non mesh terms

        Parameters:
            id - a string containing the reactome id

        Output:
            search - a string containing all synonyms of the reactome id or a mesh term formatted for the google distance function
        '''
        # We want the actual reactome name R-HSA..., not the curie REACT:R-HSA...
        if "REACT:" in id:
            id = ":".join(id.split(":")[1:])
        url = 'https://reactome.org/ContentService/data/query/'+id+'/name'  # hardcoded url for reactiome names
        requests = CacheControlHelper()
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})  # sends get request that returns a string
        if r.status_code != 200:
            print('HTTP response status code: ' + str(r.status_code) + ' for URL:\n' + url, file=sys.stderr)
            return None
        nameList = r.text.split('\n')  # splits returned string by line
        search = ''  # initializes search term variable
        for name in nameList:
            if len(name) > 0:  # removes blank lines at beginning and end of response
                if len(re.compile("[()]").split(name)) > 1:  # check for parenthesis
                    for n in re.compile("[()]").split(name):  # splits on either "(" or ")"
                        if len(n) > 0:  # removes banks generated by split
                            if QueryNCBIeUtils.is_mesh_term(n):  # check for mesh term
                                search += '|' + n + '[MeSH Terms]'
                            else:
                                search += '|' + n
                elif len(name.split('ecNumber')) > 1:  # checks for ec number
                    if QueryNCBIeUtils.is_mesh_term(name.split('ecNumber')[0]):
                        search += '|' + name.split('ecNumber')[0] + '[MeSH Terms]'
                    else:
                        search += '|' + name.split('ecNumber')[0]
                    search += '|' + name.split('ecNumber')[1][:-1] + '[EC/RN Number]'  # removes trailing "/" and formats as ec search term
                else:
                    if QueryNCBIeUtils.is_mesh_term(name):
                        search += '|' + name + '[MeSH Terms]'
                    else:
                        search += '|' + name
        search = search[1:]  # removes leading |
        return search

    
    '''Returns a set of mesh ids for a given clinvar id

    '''
    @staticmethod
    @CachedMethods.register
    def get_mesh_id_for_clinvar_uid(clinvar_id):
        # This checks for a straight clinvar id -> mesh id conversion:
        res = QueryNCBIeUtils.send_query_get('elink.fcgi',
                                             'db=mesh&dbfrom=clinvar&id=' + str(clinvar_id))
        res_set = set()
        if res is not None:
            res_json = res.json()
            linksets = res_json.get('linksets', None)
            if linksets is not None:
                link = linksets[0]
                if link is not None:
                    dbs = link.get('linksetdbs', None)
                    if dbs is not None:
                        mesh_db = dbs[0]
                        if mesh_db is not None:
                            ids = mesh_db.get('links', None)
                            res_set |= set([int(uid_str) for uid_str in ids])

        # if there are no mesh ids returned above then this finds clinvar -> medgen -> mesh canversions:
        if len(res_set) == 0:
            res = QueryNCBIeUtils.send_query_get('elink.fcgi',
                                             'db=medgen&dbfrom=clinvar&id=' + str(clinvar_id))
            if res is not None:
                res_json = res.json()
                linksets = res_json.get('linksets', None)
                if linksets is not None:
                    link = linksets[0]
                    if link is not None:
                        dbs = link.get('linksetdbs', None)
                        if dbs is not None:
                            medgen = dbs[0]
                            if medgen is not None:
                                ids = medgen.get('links', None)
                                if ids is not None:
                                    for medgen_id in ids:
                                        res2 = QueryNCBIeUtils.send_query_get('elink.fcgi',
                                            'db=mesh&dbfrom=medgen&id=' + str(medgen_id))
                                        res2_json = res2.json()
                                        linksets2 = res2_json.get('linksets', None)
                                        if linksets2 is not None:
                                            link2 = linksets2[0]
                                            if link2 is not None:
                                                dbs2 = link2.get('linksetdbs', None)
                                                if dbs2 is not None:
                                                    mesh_data = dbs2[0]
                                                    if mesh_data is not None:
                                                        mesh_ids = mesh_data.get('links', None)
                                                        res_set |= set([int(uid_str) for uid_str in mesh_ids])
        return res_set

    @staticmethod
    def multi_pubmed_pmids(term_str, n_terms=1):
        '''
        This is almost the same as the above get_pubmed_hit_counts but is made to work with multi_normalized_google_distance
        '''
        term_str_encoded = urllib.parse.quote(term_str, safe='')
        res = QueryNCBIeUtils.send_query_get('esearch.fcgi',
                                             'db=pubmed&term=' + term_str_encoded)
        if res is None:
            params = {
                'db': 'pubmed',
                'term': term_str
            }
            res = QueryNCBIeUtils.send_query_post('esearch.fcgi',
                                                  params)
        res_pmids = []
        if res is not None:
            status_code = res.status_code
            if status_code == 200:
                res_pmids = [res.json()['esearchresult']['idlist']]
                if n_terms >= 2:
                    if 'errorlist' in res.json()['esearchresult'].keys():
                        if 'phrasesnotfound' in res.json()['esearchresult']['errorlist'].keys():
                            #res_int += res.json()['esearchresult']['errorlist']['phrasesnotfound']
                            pass
                    else:
                        for a in range(len(res.json()['esearchresult']['translationstack'])):
                            if type(res.json()['esearchresult']['translationstack'][a]) == dict:
                                #print(res.json()['esearchresult']['translationstack'][a])  # FIXME this returns a dict that looks like
                                #{'term': '"hypertension"[MeSH Terms]', 'field': 'MeSH Terms', 'count': '250821','explode': 'Y'}
                                #{'term': '"neutropenia"[MeSH Terms]', 'field': 'MeSH Terms', 'count': '18429','explode': 'Y'}
                                #{'term': '"leukopenia"[MeSH Terms]', 'field': 'MeSH Terms', 'count': '36815','explode': 'Y'}
                                #res_pmids += [res.json()['esearchresult']['translationstack'][a]['idlist']]  # FIXME: so can't get an idlist
                                pass
                            elif res.json()['esearchresult']['translationstack'][a] == 'OR':
                                res_pmids = [res_pmids[0]]
                                res_pmids += ['null_flag']
                                return res_pmids

            else:
                print('HTTP response status code: ' + str(status_code) + ' for query term string {term}'.format(
                    term=term_str))
        return res_pmids

    @staticmethod
    def multi_normalized_pmids(name_list, mesh_flags=None):
        """
        returns the normalized Google distance for a list of n MeSH Terms
        :param name_list: a list of strings containing search terms for each node
        :param mesh_flags: a list of boolean values indicating which terms need [MeSH Terms] appended to it.
        :returns: list of pmids
        """

        if mesh_flags is None:
            mesh_flags = [True] * len(name_list)
        elif len(name_list) != len(mesh_flags):
            print('Warning: mismatching lengths for input lists of names and flags returning None...')
            return None

        search_string = '('

        if sum(mesh_flags) == len(mesh_flags):
            search_string += '[MeSH Terms]) AND ('.join(name_list) + '[MeSH Terms])'
            pmids = QueryNCBIeUtils.multi_pubmed_pmids(search_string, n_terms=len(name_list))
        else:
            for a in range(len(name_list)):
                search_string += name_list[a]
                if mesh_flags[a]:
                    search_string += "[MeSH Terms]"
                if a < len(name_list) - 1:
                    search_string += ') AND ('
            search_string += ')'
            pmids = QueryNCBIeUtils.multi_pubmed_pmids(search_string, n_terms=1)
            for a in range(len(name_list)):
                name = name_list[a]
                if mesh_flags[a]:
                    name += "[MeSH Terms]"
                pmids += QueryNCBIeUtils.multi_pubmed_pmids(name, n_terms=1)

        if len(pmids) > 1 and type(pmids[1]) == str:
            if pmids[1] == 'null_flag':
                missed_names = [name + '[MeSH Terms]' for name in name_list]
            else:
                missed_names = pmids[1:]
            pmids = [pmids[0]]
            for name in name_list:
                name_decorated = name + '[MeSH Terms]'
                if name_decorated in missed_names:
                    pmids += QueryNCBIeUtils.multi_pubmed_pmids(name, n_terms=1)
                else:
                    pmids += QueryNCBIeUtils.multi_pubmed_pmids(name_decorated, n_terms=1)

        return pmids


def test_phrase_not_found():
        print('----------')
        print('Result and time for 1st error (joint search):')
        print('----------')
        t0 = time.time()
        print(QueryNCBIeUtils.normalized_google_distance('lymph nodes','IL6'))
        print(time.time() - t0)
        print('----------')
        print('Result and time for 2nd error (individual search):')
        print('----------')
        t0 = time.time()
        print(QueryNCBIeUtils.normalized_google_distance('IL6','lymph nodes[MeSH Terms]',mesh2=False))
        print(time.time() - t0)
        print('Result and time for potential curve ball:')
        print('----------')
        t0 = time.time()
        print(QueryNCBIeUtils.normalized_google_distance('IL6','lymph node[MeSH Terms]|Naprosyn[MeSH Terms]|asdasdjkahfjkaf|flu|cold',mesh2=False))
        print(time.time() - t0)
        print('----------')
        print('Time with no error:')
        print('----------')
        t0 = time.time()
        QueryNCBIeUtils.normalized_google_distance('Naprosyn','lymph nodes')
        print(time.time() - t0)
              
              
if __name__ == '__main__':
    pass
    #print(QueryNCBIeUtils.get_clinvar_uids_for_disease_or_phenotype_string('hypercholesterolemia'))
    #print(QueryNCBIeUtils.get_mesh_uids_for_mesh_term('Anorexia Nervosa'))
    #print(QueryNCBIeUtils.get_mesh_uids_for_mesh_term('Leukemia, Promyelocytic, Acute'))
    #print(QueryNCBIeUtils.get_mesh_uids_for_mesh_term('Leukemia, Myeloid, Acute'))
    
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
              
    #print(QueryNCBIeUtils.normalized_google_distance(
    #    QueryNCBIeUtils.get_mesh_terms_for_omim_id(219700)[0],
    #    "Cholera"))
    




    #reactome_list = [
    #"R-HSA-5626467",
    #"R-HSA-5627083",
    #"R-HSA-447115",
    #"R-HSA-5579012",
    #"R-HSA-199992",
    #"R-HSA-3000170",
    #"R-HSA-5683371",
    #"R-HSA-5619058",
    #"R-HSA-5579006",
    #"R-HSA-2404192",
    #]
    #
    #for ids in reactome_list:
    #    t0 = time.time()
    #    searchTerm = QueryNCBIeUtils.get_reactome_names(ids)
    #    print(searchTerm)
    #    print(QueryNCBIeUtils.normalized_google_distance(
    #        searchTerm,
    #        'Human',
    #        mesh1 = False
    #        ))
    #    t1 = time.time()
    #    print(t1-t0)
    #
    #uniprot_list = [
    #"Q15699",
    #"A0A0G2JJD3",
    #"Q9NR22",
    #"Q92949",
    #"Q12996",
    #"Q92544",
    #"Q14789",
    #"Q9NRN5",
    #"Q9BXW9",
    #"P56556",
    #"P23219"
    #]
    #
    #for ids in uniprot_list:
    #    t0 = time.time()
    #    searchTerm = QueryNCBIeUtils.get_uniprot_names(ids)
    #    print(searchTerm)
    #    print(QueryNCBIeUtils.normalized_google_distance(
    #        searchTerm,
    #        'Human',
    #        mesh1 = False
    #        ))
    #    t1 = time.time()
    #    print(t1-t0)

    #print(QueryNCBIeUtils.normalized_google_distance("acetaminophen","liver"))
    #print(QueryNCBIeUtils.normalized_google_distance(QueryNCBIeUtils.get_uniprot_names('P23219'), 'Naprosyn', mesh1=False))
    #print(QueryNCBIeUtils.get_mesh_terms_for_mesh_uid(68014059))
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

