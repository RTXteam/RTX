__author__ = 'Finn Womack'
__copyright__ = 'Oregon State University'
__credits__ = ['Finn Womack']
__license__ = 'MIT'
__version__ = '0.1.0'
__maintainer__ = ''
__email__ = ''
__status__ = 'Prototype'

import _mysql
import pandas as pd


class QueryUMLSSQL():

	def __init__(self, host, port, password, database):
		'''
		This initializes the class such that it will be able to connect to the umls database in mysql.
		params:
			host = A string containing the ip/url for the host that the mysql database is on (or that the docker container is on)
			port = the port opened on the host that connects to mysql
			password = the password assigned to the user assigned to the ip you are connecting from
			database = the name that the umls database is saved under
		'''
		self.db = _mysql.connect(host=host,port=int(port),passwd=password,db=database)

	def get_dataframe_from_db(self, query):
		'''
		This method sends a query to the sql database and returns the results in a pandas dataframe
		params:
			query = a string containing the mysql query
		'''
		self.db.query(query)
		r = self.db.store_result()
		if r.num_rows() >0:
			names = [i[0] for i in r.describe()]
			df = pd.DataFrame(list(r.fetch_row(0)),columns = names)
			for name in names:
				if type(df[name][0]) == bytes:
					df[name] = df[name].str.decode('utf-8')
			return df
		else:
			return None

	def get_cui_cloud_for_word(self, word):
		'''
		This sends a query that retreaves a list of cuis matching a given normalized word
		params:
			word = a string containing a normalized word
		'''
		query = "SELECT distinct CUI FROM MRXNW_ENG where NWD = '" + word + "'"
		df = self.get_dataframe_from_db(query)
		return df

	def get_cui_cloud_for_multiple_words(self, words):
		'''
		This sends a query that retreaves a list of cuis matching normalized string containing all given normalized words
		params:
			words = a list of strings containing multiple normalized words
		'''
		query = "SELECT distinct CUI FROM MRXNS_ENG where "
		for word in words:
			query += "NSTR like '%"+ word +"%' AND "
		query = query[:-4]
		df = self.get_dataframe_from_db(query)
		return df

	def get_cui_for_go_id(self,go_id):
		'''
		This gets a list of cuis associated with a given go id
		params:
			go_id = a string containing the go id formated as such: 'GO:0000000'
		'''
		query = "select distinct CUI from MRCONSO where CODE = '" + go_id + "'"
		df = self.get_dataframe_from_db(query)
		return df

	def get_cui_for_hp_id(self,hp_id):
		'''
		This gets a list of cuis associated with a given hp id
		params:
			hp_id = a string containing the go id formated as such: 'HP:0000000'
		'''
		query = "select distinct CUI from MRCONSO where CODE = '" + hp_id + "'"
		df = self.get_dataframe_from_db(query)
		return df

	def get_cui_for_omim_id(self,omim_id):
		'''
		This gets a list of cuis associated with a given omim id
		params:
			omim_id = a string containing the go id formated as such: 'OMIM:0000000' (can also take '0000000' since this is how they are stored in UMLS)
		'''
		query = "select distinct CUI from MRCONSO where CODE = '" + omim_id.replace('OMIM:', '') + "'"
		df = self.get_dataframe_from_db(query)
		return df

