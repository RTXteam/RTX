__author__ = 'Finn Womack'
__copyright__ = 'Oregon State University'
__credits__ = ['Finn Womack']
__license__ = 'MIT'
__version__ = '0.1.0'
__maintainer__ = ''
__email__ = ''
__status__ = 'Prototype'

import math
import sys
import time
import CachedMethods
from cache_control_helper import CacheControlHelper

from QueryNCBIeUtils import QueryNCBIeUtils
from QueryDisont import QueryDisont  # DOID -> MeSH
from QueryEBIOLS import QueryEBIOLS  # UBERON -> MeSH
from QueryMyChem import QueryMyChem
import sqlite3

# requests_cache.install_cache('NGDCache')


class NormGoogleDistance:

    @staticmethod
    @CachedMethods.register
    def query_oxo(uid):
        """
        This takes a curie id and send that id to EMBL-EBI OXO to convert to cui
        """
        url_str = 'https://www.ebi.ac.uk/spot/oxo/api/mappings?fromId=' + str(uid)
        requests = CacheControlHelper()

        try:
            res = requests.get(url_str, headers={'accept': 'application/json'}, timeout=120)
        except requests.exceptions.Timeout:
            print('HTTP timeout in NormGoogleDistance.py; URL: ' + url_str, file=sys.stderr)
            time.sleep(1)  ## take a timeout because NCBI rate-limits connections
            return None
        except requests.exceptions.ConnectionError:
            print('HTTP connection error in NormGoogleDistance.py; URL: ' + url_str, file=sys.stderr)
            time.sleep(1)  ## take a timeout because NCBI rate-limits connections
            return None
        except sqlite3.OperationalError:
            print('Error reading sqlite cache; URL: ' + url_str, file=sys.stderr)
            return None
        status_code = res.status_code
        if status_code != 200:
            print('HTTP response status code: ' + str(status_code) + ' for URL:\n' + url_str, file=sys.stderr)
            res = None
        return res

    @staticmethod
    @CachedMethods.register
    def get_mesh_from_oxo(curie_id):
        if type(curie_id) != str:
            curie_id = str(curie_id)
        if curie_id.startswith('REACT:'):
            curie_id = curie_id.replace('REACT', 'Reactome')
        res = NormGoogleDistance.query_oxo(curie_id)
        mesh_ids=None
        if res is not None:
            res = res.json()
            mesh_ids = set()
            n_res = res['page']['totalElements']
            if int(n_res) > 0:
                mappings = res['_embedded']['mappings']
                for mapping in mappings:
                    if mapping['fromTerm']['curie'].startswith('MeSH'):
                        mesh_ids |= set([mapping['fromTerm']['curie'].split(':')[1]])
                    elif mapping['toTerm']['curie'].startswith('UMLS'):
                        mesh_ids |= set([mapping['toTerm']['curie'].split(':')[1]])
            if len(mesh_ids) == 0:
                mesh_ids = None
            else:
                mesh_ids = list(mesh_ids)
        return mesh_ids

    @staticmethod
    @CachedMethods.register
    def get_mesh_term_for_all(curie_id, description):
        """
        Takes a curie ID, detects the ontology from the curie id, and then finds the mesh term
        Params:
            curie_id - A string containing the curie id of the node. Formatted <source abbreviation>:<number> e.g. DOID:8398
            description - A string containing the English name for the node
        current functionality (+ means has it, - means does not have it)
            "Reactome" +
            "GO" - found gene conversion but no biological process conversion
            "UniProt" +
            "HP" - +
            "UBERON" +
            "CL" - not supposed to be here?
            "NCBIGene" +
            "DOID" +
            "OMIM" +
            "ChEMBL" +
        """
        if type(description) != str:
            description = str(description)
        curie_list = curie_id.split(':')
        names = None
        if QueryNCBIeUtils.is_mesh_term(description):
            return [description + '[MeSH Terms]']
        names = NormGoogleDistance.get_mesh_from_oxo(curie_id)
        if names is None:
            if curie_list[0].lower().startswith("react"):
                res = QueryNCBIeUtils.get_reactome_names(curie_list[1])
                if res is not None:
                    names = res.split('|')
            elif curie_list[0] == "GO":
                pass
            elif curie_list[0].startswith("UniProt"):
                res = QueryNCBIeUtils.get_uniprot_names(curie_list[1])
                if res is not None:
                    names = res.split('|')
            elif curie_list[0] == "HP":
                names = QueryNCBIeUtils.get_mesh_terms_for_hp_id(curie_id)
            elif curie_list[0] == "UBERON":
                if curie_id.endswith('PHENOTYPE'):
                    curie_id = curie_id[:-9]
                mesh_id = QueryEBIOLS.get_mesh_id_for_uberon_id(curie_id)
                names = []
                for entry in mesh_id:
                    if len(entry.split('.')) > 1:
                        uids=QueryNCBIeUtils.get_mesh_uids_for_mesh_tree(entry.split(':')[1])
                        for uid in uids:
                            try:
                                uid_num = int(uid.split(':')[1][1:]) + 68000000
                                names += QueryNCBIeUtils.get_mesh_terms_for_mesh_uid(uid_num)
                            except IndexError:
                                uid_num = int(uid)
                                names += QueryNCBIeUtils.get_mesh_terms_for_mesh_uid(uid_num)
                    else:
                        try:
                            uid = entry.split(':')[1]
                            uid_num = int(uid[1:]) + 68000000
                            names += QueryNCBIeUtils.get_mesh_terms_for_mesh_uid(uid_num)
                        except IndexError:
                            uid_num = int(entry)
                            names += QueryNCBIeUtils.get_mesh_terms_for_mesh_uid(uid_num)
                if len(names) == 0:
                    names = None
                else:
                    names[0] = names[0] + '[MeSH Terms]'
            elif curie_list[0] == "NCBIGene":
                gene_id = curie_id.split(':')[1]
                names = QueryNCBIeUtils.get_pubmed_from_ncbi_gene(gene_id)
            elif curie_list[0] == "DOID":
                mesh_id = QueryDisont.query_disont_to_mesh_id(curie_id)
                names = []
                for uid in mesh_id:
                    uid_num = int(uid[1:]) + 68000000
                    name = QueryNCBIeUtils.get_mesh_terms_for_mesh_uid(uid_num)
                    if name is not None:
                        names += name
                if len(names) == 0:
                    names = None
                else:
                    names[0] = names[0] + '[MeSH Terms]'
            elif curie_list[0] == "OMIM":
                names = QueryNCBIeUtils.get_mesh_terms_for_omim_id(curie_list[1])
            elif curie_list[0] == "ChEMBL":
                chembl_id = curie_id.replace(':', '').upper()
                mesh_id = QueryMyChem.get_mesh_id(chembl_id)
                if mesh_id is not None:
                    mesh_id = int(mesh_id[1:]) + 68000000
                    names = QueryNCBIeUtils.get_mesh_terms_for_mesh_uid(mesh_id)
        if names is not None:
            if type(names) == list:
                for name in names:
                    if name.endswith('[MeSH Terms]'):
                        return [name]
            return names
        return [description.replace(';', '|')]

    @staticmethod
    # @CachedMethods.register
    def get_ngd_for_all(curie_id_list, description_list):
        """
        Takes a list of currie ids and descriptions then calculates the normalized google distance for the set of nodes.
        Params:
            curie_id_list - a list of strings containing the curie ids of the nodes. Formatted <source abbreviation>:<number> e.g. DOID:8398
            description_list - a list of strings containing the English names for the nodes
        """
        assert len(curie_id_list) == len(description_list)
        terms = [None] * len(curie_id_list)
        for a in range(len(description_list)):
            terms[a] = NormGoogleDistance.get_mesh_term_for_all(curie_id_list[a], description_list[a])
            if type(terms[a]) != list:
                terms[a] = [terms[a]]
            if len(terms[a]) == 0:
                terms[a] = [description_list[a]]
            if len(terms[a]) > 30:
                terms[a] = terms[a][:30]
        terms_combined = [''] * len(terms)
        mesh_flags = [True] * len(terms)
        for a in range(len(terms)):
            if len(terms[a]) > 1:
                if not terms[a][0].endswith('[uid]'):
                    for b in range(len(terms[a])):
                        if QueryNCBIeUtils.is_mesh_term(terms[a][b]) and not terms[a][b].endswith('[MeSH Terms]'):
                            terms[a][b] += '[MeSH Terms]'
                terms_combined[a] = '|'.join(terms[a])
                mesh_flags[a] = False
            else:
                terms_combined[a] = terms[a][0]
                if terms[a][0].endswith('[MeSH Terms]'):
                    terms_combined[a] = terms[a][0][:-12]
                elif not QueryNCBIeUtils.is_mesh_term(terms[a][0]):
                    mesh_flags[a] = False
        ngd = QueryNCBIeUtils.multi_normalized_google_distance(terms_combined, mesh_flags)
        return ngd

    @staticmethod
    def api_ngd(mesh_term1, mesh_term2):
        response = {}
        if not QueryNCBIeUtils.is_mesh_term(mesh_term2):
            response['message'] = "Term 2 '" + mesh_term2 + "' not found in MeSH"
        if not QueryNCBIeUtils.is_mesh_term(mesh_term1):
            if 'message' in response.keys():
                response['message'] = "Term 1 '" + mesh_term1 + "' and " + response['message']
            else:
                response['message'] = "Term 1 '" + mesh_term1 + "' not found in MeSH"
        if 'message' in response:
            response["response_code"] = "TermNotFound"
            return response
        else:
            value = QueryNCBIeUtils.multi_normalized_google_distance([mesh_term1, mesh_term2])
            print(type(value))
            if math.isnan(value):
                response['value'] = None
                response['response_code'] = "OK"
            else:
                response['response_code'] = "OK"
                response['value'] = value
        return response

    @staticmethod
    # @CachedMethods.register
    def get_pmids_for_all(curie_id_list, description_list):
        """
        Takes a list of currie ids and descriptions then calculates the normalized google distance for the set of nodes.
        Params:
            curie_id_list - a list of strings containing the curie ids of the nodes. Formatted <source abbreviation>:<number> e.g. DOID:8398
            description_list - a list of strings containing the English names for the nodes
        """
        assert len(curie_id_list) == len(description_list)
        terms = [None] * len(curie_id_list)
        for a in range(len(description_list)):
            terms[a] = NormGoogleDistance.get_mesh_term_for_all(curie_id_list[a], description_list[a])
            if type(terms[a]) != list:
                terms[a] = [terms[a]]
            if len(terms[a]) == 0:
                terms[a] = [description_list[a]]
            if len(terms[a]) > 30:
                terms[a] = terms[a][:30]
        terms_combined = [''] * len(terms)
        mesh_flags = [True] * len(terms)
        for a in range(len(terms)):
            if len(terms[a]) > 1:
                if not terms[a][0].endswith('[uid]'):
                    for b in range(len(terms[a])):
                        if QueryNCBIeUtils.is_mesh_term(terms[a][b]) and not terms[a][b].endswith('[MeSH Terms]'):
                            terms[a][b] += '[MeSH Terms]'
                terms_combined[a] = '|'.join(terms[a])
                mesh_flags[a] = False
            else:
                terms_combined[a] = terms[a][0]
                if terms[a][0].endswith('[MeSH Terms]'):
                    terms_combined[a] = terms[a][0][:-12]
                elif not QueryNCBIeUtils.is_mesh_term(terms[a][0]):
                    mesh_flags[a] = False
        pmids = QueryNCBIeUtils.multi_normalized_pmids(terms_combined, mesh_flags)
        pmids_with_prefix = []
        for lst in pmids:
            pmids_with_prefix.append([f"PMID:{x}" for x in lst])
        return pmids_with_prefix
