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

	def __init__(self, host, port, username, password, database):
		'''
		This initializes the class such that it will be able to connect to the umls database in mysql.
		params:
			host = A string containing the ip/url for the host that the mysql database is on (or that the docker container is on)
			port = the port opened on the host that connects to mysql
			password = the password assigned to the user assigned to the ip you are connecting from
			database = the name that the umls database is saved under
		'''
		self.db = _mysql.connect(host=host,port=int(port),user = username, passwd=password,db=database)

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

	def get_cui_for_mesh_id(self,mesh_id):
		'''
		This gets a list of cuis associated with a given hp id
		params:
			mesh_id = a string containing the go id formated as such: 'HP:0000000'
		'''
		query = "select distinct CUI from MRCONSO where CODE = '" + mesh_id + "'"
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

	def get_mesh_id_for_id(self, name, uuid):
		'''
		This gets a list of mesh ids associated with a given id
		'''
		query = "select distinct b.CODE from MRCONSO a join MRCONSO b on a.CUI = b.CUI where a.SAB = '" + name + "' and b.SAB = 'MSH' and a.CODE = '" + uuid + "'"
		df = self.get_dataframe_from_db(query)
		return df

	def get_mesh_id_for_go_id(self, go_id):
		df = self.get_mesh_id_for_id('GO', go_id)
		return df

	def get_mesh_id_for_hp_id(self, hp_id):
		df = self.get_mesh_id_for_id('HP', hp_id)
		return df

	def get_mesh_id_for_omim_id(self, omim_id):
		df = self.get_mesh_id_for_id('OMIM', omim_id.replace('OMIM:', ''))
		return df

	def get_id_for_mesh_id(self, mesh_id):
		'''
		This gets a list of ids for a given mesh id
		'''
		query = "select distinct b.SAB, b.CODE from MRCONSO a join MRCONSO b on a.CUI = b.CUI where b.SAB != 'MSH' and a.SAB = 'MSH' and a.CODE = '" + mesh_id + "'"
		df = self.get_dataframe_from_db(query)
		return df


if __name__=='__main__':
	umlsdb = QueryUMLSSQL("rtxdev.saramsey.org",3406, "rtx_read","rtxd3vT3amXray","umls")
	print(umlsdb.get_cui_for_go_id('GO:0000252'))
	print(umlsdb.get_cui_for_hp_id('HP:0000176'))
	print(list(umlsdb.get_cui_for_omim_id('OMIM:300864')['CUI']))
	#print(umlsdb.get_cui_cloud_for_word('cox1'))
	#print(umlsdb.get_cui_cloud_for_word('ptgs1'))
	#print(umlsdb.get_mesh_id_for_go_id('GO:1905222'))
	#print(umlsdb.get_mesh_id_for_hp_id('HP:0000854'))
	#print(umlsdb.get_mesh_id_for_omim_id('OMIM:612634'))
	print(umlsdb.get_cui_for_mesh_id('gegegegeg') is None)