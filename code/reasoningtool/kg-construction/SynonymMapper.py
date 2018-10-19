import sys
import os
#new_path = os.path.join(os.getcwd(), '..', 'SemMedDB')
#sys.path.insert(0, new_path)

from NormGoogleDistance import NormGoogleDistance
#from SemMedInterface import SemMedInterface
from QueryMyGene import QueryMyGene
import mygene
import requests
from QueryMyChem import QueryMyChem
import requests_cache
import pandas
#import _mysql_exceptions


class SynonymMapper():

    def __init__(self):
        #try:
        #    self.smi = SemMedInterface()
        #except _mysql_exceptions.OperationalError:
        #    print('Warning: No connection was made to the SemMEdDB MySQL server.')
        #    self.smi = None
        self.biothings_url = "http://c.biothings.io/v1/query?q="
        self.mygene_obj = mygene.MyGeneInfo()
        self.qmg = QueryMyGene()

    def prot_to_gene(self, curie_id):
        """
        This takes a uniprot curie id and converts it into a few different gene ids
        """
        if len(curie_id.split(':'))>1:
            uniprot_id = curie_id.split(':')[1]
        else:
            return None
        entrez_ids = self.qmg.convert_uniprot_id_to_entrez_gene_ID(uniprot_id)
        if entrez_ids is not None:
            entrez_ids = set(entrez_ids)
        else:
            entrez_ids = set()
        hgnc_ids = set()
        mim_ids = set()
        vega_ids = set()
        ensembl_ids = set()
        synonyms = []

        symbols = self.qmg.convert_uniprot_id_to_gene_symbol(uniprot_id)
        for symbol in symbols:
            synonyms += ['HGNC.Symbol:' + symbol]

        for gene_id in entrez_ids:
            synonyms += ['NCBIGene:' + str(gene_id)]
            try:
                res = self.mygene_obj.getgene(int(gene_id), fields = 'HGNC,MIM,Vega,ensembl', verbose = False)
            except requests.exceptions.HTTPError:
                print('HTTP error for querying uniprot to gene symbol mygene: ' + uniprot_id, file=sys.stderr)
                res = None
            if res is not None:
                hgnc_res = res.get('HGNC', None)
                mim_res = res.get('MIM', None)
                vega_res = res.get('Vega', None)
                ensembl_res = res.get('ensembl', None)
            else:
                hgnc_res = None
                mim_res = None
                vega_res = None
                ensembl_res = None
            if hgnc_res is not None:
                hgnc_ids |= set([hgnc_res])
            if mim_res is not None:
                mim_ids |= set([mim_res])
            if vega_res is not None:
                vega_ids |= set([vega_res])
            if ensembl_res is not None:
                if type(ensembl_res) == list:
                    for ens_res in ensembl_res:
                        ensembl_gene_res = ens_res.get('gene', None)
                        if ensembl_gene_res is not None:
                            ensembl_ids |= set([ensembl_gene_res])
                else:
                    ensembl_gene_res = ensembl_res.get('gene', None)
                    if ensembl_gene_res is not None:
                        ensembl_ids |= set([ensembl_gene_res])

        for hgnc_id in hgnc_ids:
            synonyms += ['HGNC:' + str(hgnc_id)]
        for mim_id in mim_ids:
            synonyms += ['OMIM:' + str(mim_id)]
        for vega_id in vega_ids:
            synonyms += ['Vega:' + str(vega_id)]
        for ensembl_id in ensembl_ids:
            synonyms += ['ensembl:' + str(ensembl_id)]

        if len(synonyms)>0:
            return synonyms
        else:
            return None

    def get_all_from_oxo(self, curie_id, map_to = None):
        """
        this takes a curie id and gets all the mappings that oxo has for the given id
        
        :param curie_id: The string for the curie id to submit to OXO (e.g. 'HP:0001947')
        :param map_to: A string containing the prefix for the resulting ids. If set to None it will return all mappings. (default is none)
        
        :return: A list of strings containing the found mapped ids or None if none where found
        """
        if map_to is None:
            map_to = ''
        if type(curie_id) != str:
            curie_id = str(curie_id)
        if curie_id.startswith('REACT:'):
            curie_id = curie_id.replace('REACT', 'Reactome')
        prefix = curie_id.split(':')[0]
        res = NormGoogleDistance.query_oxo(curie_id)
        synonym_ids=None
        if res is not None:
            res = res.json()
            synonym_ids = set()
            n_res = res['page']['totalElements']
            if int(n_res) > 0:
                mappings = res['_embedded']['mappings']
                for mapping in mappings:
                    if type(map_to) == list:
                        for elm in map_to:
                            if mapping['fromTerm']['curie'].startswith(prefix):
                                if mapping['toTerm']['curie'].startswith(elm):
                                    synonym_ids |= set([mapping['toTerm']['curie']])
                            elif mapping['toTerm']['curie'].startswith(prefix):
                                if mapping['fromTerm']['curie'].startswith(elm):
                                    synonym_ids |= set([mapping['fromTerm']['curie']])
                    else:
                        if mapping['fromTerm']['curie'].startswith(prefix):
                            if mapping['toTerm']['curie'].startswith(map_to):
                                synonym_ids |= set([mapping['toTerm']['curie']])
                        elif mapping['toTerm']['curie'].startswith(prefix):
                            if mapping['fromTerm']['curie'].startswith(map_to):
                                synonym_ids |= set([mapping['fromTerm']['curie']])
            if len(synonym_ids) == 0:
                synonym_ids = None
            else:
                synonym_ids = list(synonym_ids)
        return synonym_ids

    #def id_to_cui(self, curie_id):
    #    """
    #    this takes a currie id and finds a UMLS cui for it
    #    """
    #    assert self.smi is not None, "No connection was made to the MySQL SemMedDB server on rtxdev.saramsey.org if you want to try to connect again reinitialize the class."
    #    cuis = self.smi.get_cui_for_id(curie_id)
    #    return cuis

    def chembl_to_chebi(self, chemical_substance_id):
        """
        This takes a chembl curie id and return a chebi curie id
        """
        if chemical_substance_id[:7] == "ChEMBL:":
            chemical_substance_id = chemical_substance_id.replace("ChEMBL:", "CHEMBL")
        if chemical_substance_id.startswith('CHEMBL:CHEMBL'):
            chemical_substance_id = chemical_substance_id.replace("CHEMBL:", "")
        handler = 'chem/' + chemical_substance_id + '?fields=chebi.chebi_id'

        url = QueryMyChem.API_BASE_URL + '/' + handler

        try:
            res = requests.get(url, timeout=QueryMyChem.TIMEOUT_SEC)
        except requests.exceptions.Timeout:
            #print(url, file=sys.stderr)
            #print('Timeout in QueryMyChem for URL: ' + url, file=sys.stderr)
            return None
        if res is None:
            return None
        status_code = res.status_code
        if status_code != 200:
            #print(url, file=sys.stderr)
            #print('Status code ' + str(status_code) + ' for url: ' + url, file=sys.stderr)
            return None
        id_json = res.json()
        if 'chebi' in id_json.keys():
            return id_json['chebi']['chebi_id']
        else:
            return None




