__author__ = 'Finn Womack'
__copyright__ = 'Oregon State University'
__credits__ = ['Finn Womack']
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
from io import StringIO
import re
import pandas
import pprint
import CachedMethods
import requests_cache
import numpy
from QueryNCBIeUtils import QueryNCBIeUtils
from QueryDisont import QueryDisont #DOID -> MeSH
from QueryEBIOLS import QueryEBIOLS #UBERON -> MeSH
from QueryPubChem import QueryPubChem #ChEMBL -> PubMed id
from QueryMyChem import QueryMyChem

requests_cache.install_cache('NGDCache')




class NormGoogleDistance:

	@staticmethod
	@CachedMethods.register
	def get_mesh_term_for_all(curie_id,description):
		'''
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
		'''
		curie_list = curie_id.split(':')
		if QueryNCBIeUtils.is_mesh_term(description):
			return [description + '[MeSH Terms]']
		elif curie_list[0] == "Reactome":
			names = QueryNCBIeUtils.get_reactome_names(curie_list[1]).split('|')
			if names is not None:
				return names
		elif curie_list[0] == "GO":
			pass
		elif curie_list[0] == "UniProt":
			names = QueryNCBIeUtils.get_uniprot_names(curie_list[1]).split('|')
			if names is not None:
				return names
		elif curie_list[0] == "HP":
			names = QueryNCBIeUtils.get_mesh_terms_for_hp_id(curie_id)
			if names is not None:
				return names
		elif curie_list[0] == "UBERON":
			if curie_id.endswith('PHENOTYPE'):
				curie_id = curie_id[:-9]
			mesh_id = QueryEBIOLS.get_mesh_id_for_uberon_id(curie_id)
			names = []
			for entry in mesh_id:
				if len(entry.split('.')) > 1:
					uids=QueryNCBIeUtils.get_mesh_uids_for_mesh_tree(entry.split(':')[1])
					for uid in uids:
						uid_num = int(uid.split(':')[1][1:]) + 68000000
						names += [QueryNCBIeUtils.get_mesh_terms_for_mesh_uid(uid_num)]
				else:
					uid = entry.split(':')[1]
					uid_num = int(uid[1:]) + 68000000
					names = QueryNCBIeUtils.get_mesh_terms_for_mesh_uid(uid_num)
			if len(names) > 0:
				return names
		elif curie_list[0] == "NCBIGene":
			gene_id = curie_id.split(':')[1]
			names = QueryNCBIeUtils.get_pubmed_from_ncbi_gene(gene_id)
			if names is not None:
				return names
		elif curie_list[0] == "DOID":
			mesh_id = QueryDisont.query_disont_to_mesh_id(curie_id)
			names = []
			for uid in mesh_id:
				uid_num = int(uid[1:]) + 68000000
				name = QueryNCBIeUtils.get_mesh_terms_for_mesh_uid(uid_num)
				if name is not None:
					names += name
			if len(names)>0:
				return names
		elif curie_list[0] == "OMIM":
			names = QueryNCBIeUtils.get_mesh_terms_for_omim_id(curie_list[1])
			if names is not None:
				return names
		elif curie_list[0] == "ChEMBL":
			chembl_id = curie_id.replace(':', '').upper()
			mesh_id = QueryMyChem.get_mesh_id(chembl_id)
			if mesh_id is not None:
				mesh_id = int(mesh_id[1:]) + 68000000
				names = QueryNCBIeUtils.get_mesh_terms_for_mesh_uid(mesh_id)
				if names is not None:
					return names
		return [description.replace(';','|')]

	@staticmethod
	#@CachedMethods.register
	def get_ngd_for_all(curie_id_list,description_list):
		'''
		Takes a list of currie ids and descriptions then calculates the normalized google distance for the set of nodes.
		Params:
			curie_id_list - a list of strings containing the curie ids of the nodes. Formatted <source abbreviation>:<number> e.g. DOID:8398
			description_list - a list of strings containing the English names for the nodes
		'''
		assert len(curie_id_list) == len(description_list)
		terms = [None]*len(curie_id_list)
		for a in range(len(description_list)):
			terms[a]=NormGoogleDistance.get_mesh_term_for_all(curie_id_list[a],description_list[a])
			if type(terms[a])!=list:
				terms[a] = [terms[a]]
			if len(terms[a]) == 0:
				terms[a] = [description_list[a]]
		terms_combined = ['']*len(terms)
		mesh_flags=[True]*len(terms)
		for a in range(len(terms)):
			if len(terms[a]) > 1:
				if not terms[a][0].endswith('[uid]'):
					for b in range(len(terms[a])):
						if QueryNCBIeUtils.is_mesh_term(terms[a][b]) and not terms[a][b].endswith('[MeSH Terms]'):
							terms[a][b]+='[MeSH Terms]'
				terms_combined[a] = '|'.join(terms[a])
				mesh_flags[a] = False
			else:
				terms_combined[a] = terms[a][0]
				if terms[a][0].endswith('[MeSH Terms]'):
					terms_combined[a] = terms[a][0][:-12]
				elif not QueryNCBIeUtils.is_mesh_term(terms[a][0]):
					mesh_flags[a] = False
		ngd = QueryNCBIeUtils.multi_normalized_google_distance(terms_combined,mesh_flags)
		return ngd




if __name__ == '__main__':
	pass
