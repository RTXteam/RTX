__author__ = 'Finn Womack'
__copyright__ = 'Oregon State University'
__credits__ = ['Finn Womack']
__license__ = 'MIT'
__version__ = '0.1.0'
__maintainer__ = ''
__email__ = ''
__status__ = 'Prototype'

import pandas
import requests
import sys
import time
import math
from io import StringIO
import re
import os
import CachedMethods
import requests_cache
import json
requests_cache.install_cache('QueryPubChemCache')

class QueryPubChem:


	@staticmethod
	#@CachedMethods.register
	def get_pubchem_id_for_chembl_id(chembl_id):
		'''
		This takes a chembl id and then looks up the corresponding pubchem id from a pre-generated .tsv

		NOTE: pubchem-chembl mappings .tsv generated using https://pubchem.ncbi.nlm.nih.gov/idexchange/idexchange.cgi
		it took ~3 or so seconds to map all ids in the KG (2226 ids) and not all ids were successful (missed 204 terms -> ~91% success rate)
		'''
		df = pandas.read_csv('chemblMap.tsv', sep='\t', index_col=0, header=None)
		try:
			ans = df.loc[chembl_id].iloc[0]
		except KeyError:
			return None
		if math.isnan(ans):
			return None
		else:
			return str(int(ans))

	@staticmethod
	#@CachedMethods.register
	def get_pubmed_id_for_pubchem_id(pubchem_id):
		'''
		This takes a PubChem id and then gets the PMIDs for articles on PubMed from PubChem which include this entity.
		'''
		r = requests.get('https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/' + str(pubchem_id) + '/xrefs/PubMedID/JSON', timeout = 10)
		if r is not None:
			if 'Fault' in r.json().keys():
				return None
			else:
				ans = [str(x) + '[uid]' for x in r.json()['InformationList']['Information'][0]['PubMedID']]
				return ans
		else:
			return None


if __name__=='__main__':
	pass
