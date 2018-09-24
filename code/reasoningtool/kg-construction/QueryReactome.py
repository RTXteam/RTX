""" This module defines the class QueryReactome. QueryReactome is written to
connect with APIs at https://reactome.org/ContentService, querying the pathway
information.
"""

__author__ = 'Stephen Ramsey'
__copyright__ = 'Oregon State University'
__credits__ = ['Stephen Ramsey', 'Yao Yao', 'Zheng Liu']
__license__ = 'MIT'
__version__ = '0.1.0'
__maintainer__ = ''
__email__ = ''
__status__ = 'Prototype'

import requests
import sys
import re
import requests_cache
import json


class QueryReactome:

    API_BASE_URL = 'https://reactome.org/ContentService'

    TIMEOUT_SEC = 120

    HANDLER_MAP = {
        'get_pathway': 'data/pathway/{id}/containedEvents',
        'get_pathway_desc': 'data/query/{id}'
    }

    SPECIES_MNEMONICS = ['BOVIN',
                         'ACAVI',
                         'VACCW',
                         'PLAVS',
                         'CHICK',
                         'ECOLI',
                         'HORSE',
                         'MAIZE',
                         'MOUSE',
                         'PEA',
                         'PIG',
                         'RABIT',
                         'RAT',
                         'SHEEP',
                         'SOYBN',
                         'TOBAC',
                         'WHEAT',
                         'YEAST',
                         'HV1N5',
                         'HV1H2',
                         'DANRE',
                         'XENLA',
                         'MYCTU',
                         'HHV8P',
                         'HTLV2',
                         'HHV1',
                         'HPV16',
                         '9HIV1',
                         'EBVB9',
                         'PROBE',
                         'HTL1C',
                         'I72A2',
                         'SV40',
                         'HV1B1',
                         'SCHPO',
                         'RUBV',
                         'MUS']
    
    @staticmethod
    def send_query_get(handler, url_suffix):
        url_str = QueryReactome.API_BASE_URL + '/' + handler + '/' + url_suffix
#        print(url_str)
        try:
            res = requests.get(url_str, headers={'accept': 'application/json'},
                               timeout=QueryReactome.TIMEOUT_SEC)
        except KeyboardInterrupt:
            sys.exit(0)
        except BaseException as e:
            print('%s received in QueryReactome for URL: %s' % (e, url_str), file=sys.stderr)
            return None
        status_code = res.status_code
        if status_code != 200:
            print('Status code ' + str(status_code) + ' for url: ' + url_str, file=sys.stderr)
            return None
        return res

    @staticmethod
    def __query_uniprot_to_reactome_entity_id(uniprot_id):
        res = QueryReactome.send_query_get('data/complexes/UniProt', uniprot_id)
        if res is not None:
            res_json = res.json()
            #        print(res_json)
            if type(res_json) == list:
                ret_ids = set([res_entry['stId'] for res_entry in res_json])
            else:
                ret_ids = set()
        else:
            ret_ids = set()
        return ret_ids

    @staticmethod
    def __query_uniprot_to_reactome_entity_id_desc(uniprot_id):
        res = QueryReactome.send_query_get('data/complexes/UniProt', uniprot_id)
        ret_ids = dict()
        if res is not None:
            res_json = res.json()
            if type(res_json) == list:
                for res_entry in res_json:
                    entity_id = res_entry['stId']
                    if 'R-HSA-' in entity_id:
                        ret_ids[entity_id] = res_entry['displayName']
                    else:
                        print('Non-human reactome entity ID: ' + entity_id + ' from Uniprot ID: ' + uniprot_id)
        return ret_ids

    @staticmethod
    def __query_reactome_entity_id_to_reactome_pathway_ids_desc(reactome_entity_id):
        res = QueryReactome.send_query_get('data/pathways/low/diagram/entity', reactome_entity_id + '/allForms?species=9606')
        reactome_ids_dict = dict()
        if res is not None:
            res_json = res.json()
            for res_entry in res_json:
                res_id = res_entry['stId']
                if 'R-HSA-' in res_id:
                    reactome_ids_dict[res_id] = res_entry['displayName']
                else:
                    print('Non-human Reactome pathway: ' + res_id + ' from reactome entity ID: ' + reactome_entity_id, file=sys.stderr)
        else:
            reactome_ids_dict = dict()
        return reactome_ids_dict

    ## called from BioNetExpander
    @staticmethod
    def query_uniprot_id_to_reactome_pathway_ids_desc(uniprot_id):
        reactome_entity_ids = QueryReactome.__query_uniprot_to_reactome_entity_id(uniprot_id)
        res_dict = dict()
        for reactome_entity_id in reactome_entity_ids:
            if 'R-HSA-' in reactome_entity_id:
                pathway_ids_dict = QueryReactome.__query_reactome_entity_id_to_reactome_pathway_ids_desc(reactome_entity_id)
                if len(pathway_ids_dict) > 0:
                    res_dict.update(pathway_ids_dict)
                else:
                    print('Non-human Reactome entity: ' + reactome_entity_id + ' from Uniprot ID: ' + uniprot_id, file=sys.stderr)
        return res_dict
    
    ## called from BioNetExpander
    @staticmethod
    def query_reactome_pathway_id_to_uniprot_ids_desc(reactome_pathway_id):
        res = QueryReactome.send_query_get('data/participants', reactome_pathway_id)
        ret_dict = dict()
        if res is not None:
            res_json = res.json()
            #        print(res_json)
            participant_ids_list = [refEntity['displayName'] for peDbEntry in res_json for refEntity in peDbEntry['refEntities']]
            for participant_id in participant_ids_list:
                if 'UniProt:' in participant_id:
                    uniprot_id = participant_id.split(' ')[0].split(':')[1]
                    if ' ' in participant_id:
                        prot_desc = participant_id.split(' ')[1]
                    else:
                        prot_desc = 'UNKNOWN'
                    if '-' in uniprot_id:
                        uniprot_id = uniprot_id.split('-')[0]
                    ret_dict[uniprot_id] = prot_desc
#            uniprot_ids_list = [[id.split(' ')[0].split(':')[1], id.split(' ')[1]] for id in participant_ids_list if 'UniProt:' in id]
        return ret_dict

    @staticmethod
    def is_valid_uniprot_accession(accession_str):
        return re.match("[OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2}", accession_str) is not None

    # called from BioNetExpander
    @staticmethod
    def query_uniprot_id_to_interacting_uniprot_ids_desc(uniprot_id):
        res = QueryReactome.send_query_get('interactors/static/molecule', uniprot_id + '/details')
        res_uniprot_ids = dict()
        if res is not None:
            res_json = res.json()
#            print(res_json)
            if res_json is not None:
                res_entities = res_json.get('entities', None)
                if res_entities is not None:
                    for res_entity in res_entities:
                        res_entity_interactors = res_entity.get('interactors', None)
                        if res_entity_interactors is not None:
                            for res_entity_interactor in res_entity_interactors:
                                int_uniprot_id = res_entity_interactor.get('acc', None)
                                if int_uniprot_id is not None:
                                    if 'CHEBI:' not in int_uniprot_id:
                                        if '-' in int_uniprot_id:
                                            int_uniprot_id = int_uniprot_id.split('-')[0]
                                        int_alias = res_entity_interactor.get('alias', '')
                                        alt_species = None
                                        if ' ' in int_alias:
                                            int_alias_split = int_alias.split(' ')
                                            int_alias = int_alias_split[0]
                                            alt_species = int_alias_split[1]
                                        if alt_species is None or (alt_species not in QueryReactome.SPECIES_MNEMONICS and \
                                                                   not (alt_species[0] == '9')):
                                            if alt_species is not None:
                                                if 'DNA' in int_alias_split or \
                                                   'DNA-PROBE' in int_alias_split or \
                                                   'DSDNA' in int_alias_split or \
                                                   'GENE' in int_alias_split or \
                                                   'PROMOTE' in int_alias_split or \
                                                   'PROMOTER' in int_alias_split or \
                                                   any(['-SITE' in alias_element for alias_element in int_alias_split]) or \
                                                   any(['BIND' in alias_element for alias_element in int_alias_split]):                                               
                                                    target_gene_symbol = int_alias_split[0]
                                                    int_alias = 'BINDSGENE:' + int_alias_split[0]
                                                else:
                                                    print('For query protein ' + uniprot_id + ' and interactant protein ' + int_uniprot_id + ', check for potential other species name in Reactome output: ' + alt_species, file=sys.stderr)
                                                    int_alias = None
                                        if int_alias is not None and int_alias != "" and QueryReactome.is_valid_uniprot_accession(int_uniprot_id):
                                                res_uniprot_ids[int_uniprot_id] = int_alias
        return res_uniprot_ids

    @staticmethod
    def __access_api(handler):

        url = QueryReactome.API_BASE_URL + '/' + handler

        try:
            res = requests.get(url, timeout=QueryReactome.TIMEOUT_SEC)
        except requests.exceptions.Timeout:
            print(url, file=sys.stderr)
            print('Timeout in QueryReactome for URL: ' + url, file=sys.stderr)
            return None
        except BaseException as e:
            print(url, file=sys.stderr)
            print('%s received in QueryReactome for URL: %s' % (e, url), file=sys.stderr)
            return None
        status_code = res.status_code
        if status_code != 200:
            print(url, file=sys.stderr)
            print('Status code ' + str(status_code) + ' for url: ' + url, file=sys.stderr)
            return None

        return res.text

    @staticmethod
    def __get_entity(entity_type, entity_id):
        handler = QueryReactome.HANDLER_MAP[entity_type].format(id=entity_id)
        results = QueryReactome.__access_api(handler)
        result_str = 'None'
        if results is not None:
            #   remove all \n characters using json api and convert the string to one line
            json_dict = json.loads(results)
            result_str = json.dumps(json_dict)
        return result_str

    @staticmethod
    def __get_desc(entity_type, entity_id):
        handler = QueryReactome.HANDLER_MAP[entity_type].format(id=entity_id)
        results = QueryReactome.__access_api(handler)
        result_str = 'None'
        if results is not None:
            #   remove all \n characters using json api and convert the string to one line
            json_dict = json.loads(results)
            if 'summation' in json_dict.keys():
                summation = json_dict['summation']
                if len(summation) > 0:
                    if 'text' in summation[0].keys():
                        result_str = summation[0]['text']
        return result_str

    @staticmethod
    #   example of pathway_id: REACT:R-HSA-70326
    def get_pathway_entity(pathway_id):
        if not isinstance(pathway_id, str):
            return 'None'
        if pathway_id[:6] == "REACT:":
            pathway_id = pathway_id[6:]
        return QueryReactome.__get_entity("get_pathway", pathway_id)

    @staticmethod
    #   example of pathway_id: Reactome:R-HSA-70326
    def get_pathway_desc(pathway_id):
        if not isinstance(pathway_id, str):
            return 'None'
        if pathway_id[:6] == "REACT:":
            pathway_id = pathway_id[6:]
        return QueryReactome.__get_desc("get_pathway_desc", pathway_id)

    @staticmethod
    def test():
        print(QueryReactome.query_uniprot_id_to_interacting_uniprot_ids_desc("P62991"))
        print(QueryReactome.is_valid_uniprot_accession("Q16665"))
        print(QueryReactome.is_valid_uniprot_accession("EBI"))
        print(QueryReactome.query_uniprot_id_to_interacting_uniprot_ids_desc("Q16665"))
        print(QueryReactome.query_uniprot_id_to_interacting_uniprot_ids_desc('P04150'))
        print(QueryReactome.query_uniprot_id_to_interacting_uniprot_ids_desc('Q06609'))
        print(QueryReactome.query_uniprot_id_to_interacting_uniprot_ids_desc('Q13501'))
        print(QueryReactome.query_uniprot_id_to_interacting_uniprot_ids_desc('P68871'))
        print(QueryReactome.query_uniprot_id_to_interacting_uniprot_ids_desc('O75521-2'))
        print(QueryReactome.query_reactome_pathway_id_to_uniprot_ids_desc('R-HSA-5423646'))
        print(QueryReactome.query_uniprot_id_to_interacting_uniprot_ids_desc("P68871"))
        print(QueryReactome.__query_uniprot_to_reactome_entity_id('O75521-2'))
        print(QueryReactome.__query_reactome_entity_id_to_reactome_pathway_ids_desc('R-HSA-2230989'))
        print(QueryReactome.__query_uniprot_to_reactome_entity_id_desc('P68871'))


if __name__ == '__main__':
    QueryReactome.test()

    def save_to_test_file(filename, key, value):
        f = open(filename, 'r+')
        try:
            json_data = json.load(f)
        except ValueError:
            json_data = {}
        f.seek(0)
        f.truncate()
        json_data[key] = value
        json.dump(json_data, f)
        f.close()

    save_to_test_file('tests/query_test_data.json', 'REACT:R-HSA-70326', QueryReactome.get_pathway_entity('REACT:R-HSA-70326'))
    print(QueryReactome.get_pathway_desc('REACT:R-HSA-70326'))
