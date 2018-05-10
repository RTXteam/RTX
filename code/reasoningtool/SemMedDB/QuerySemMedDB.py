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


class QuerySemMedDB():

	def __init__(self, host, port, username, password, database):
		'''
		This initializes the class such that it will be able to connect to the semmeddb database in mysql.
		params:
			host = A string containing the ip/url for the host that the mysql database is on (or that the docker container is on)
			port = the port opened on the host that connects to mysql
			password = the password assigned to the user assigned to the ip you are connecting from
			database = the name that the semmeddb database is saved under
		'''
		self.db = _mysql.connect(host=host,port=int(port),user = username,passwd=password,db=database)

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

	def get_edges_for_cui(self, cui, predicate = None):
		'''
		This method gets all the subject, predicate, object tuples containing the cui
		params:
			cui = string containing the cui you wish to search for
			(optional) predicate = string containing the predicate you whish to search for
		'''
		query = "select PMID, SUBJECT_NAME, PREDICATE, OBJECT_NAME from SPLIT_PREDICATION where (OBJECT_CUI='" + cui + "' or SUBJECT_CUI='" + cui + "')"
		if predicate is not None:
			query = query + " and PREDICATE='" + predicate + "'"
		df = self.get_dataframe_from_db(query)
		return df

	def get_edges_for_subject_cui(self, cui, predicate = None):
		'''
		This method gets all the subject, predicate, object tuples containing the cui as a subject
		params:
			cui = string containing the cui you wish to search for
			(optional) predicate = string containing the predicate you whish to search for
		'''
		query = "select PMID, SUBJECT_NAME, PREDICATE, OBJECT_NAME from SPLIT_PREDICATION where SUBJECT_CUI='" + cui + "'"
		if predicate is not None:
			query = query + " and PREDICATE='" + predicate + "'"
		df = self.get_dataframe_from_db(query)
		return df

	def get_edges_for_object_cui(self, cui, predicate = None):
		'''
		This method gets all the subject, predicate, object tuples containing the cui as an object
		params:
			cui = string containing the cui you wish to search for
			(optional) predicate = string containing the predicate you whish to search for
		'''
		query = "select PMID, SUBJECT_NAME, PREDICATE, OBJECT_NAME from SPLIT_PREDICATION where OBJECT_CUI='" + cui + "'"
		if predicate is not None:
			query = query + " and PREDICATE='" + predicate + "'"
		df = self.get_dataframe_from_db(query)
		return df

	def get_edges_between_subject_object(self, cui_subject, cui_object, predicate = None, result_col = ['PMID', 'SUBJECT_NAME', 'PREDICATE', 'OBJECT_NAME']):
		'''
		This method gets all the connections of length 1 between a subject node and a n object node
		params:
			subject_cui = a string containing the subject cui
			object_cui = a string containing the object cui
			(optional) predicate = a string containing the predicate you wish to search for
		'''
		query = "select distinct " + ', '.join(result_col) + " from SPLIT_PREDICATION where (OBJECT_CUI='" + cui_object + "' and SUBJECT_CUI='" + cui_subject + "')"
		if predicate is not None:
			query = query + " and PREDICATE='" + predicate + "'"
		df = self.get_dataframe_from_db(query)
		return df

	def get_edges_between_nodes(self, cui1, cui2, predicate = None, result_col = ['PMID', 'SUBJECT_NAME', 'PREDICATE', 'OBJECT_NAME']):
		'''
		This method gets all the connections of length 1 between two nodes with desired cuis regardless of subject/object positions
		params:
			cui1 = string containing a cui you wish to search for
			cui2 = string containing a cui you wish to search for
			(optional) predicate = a string containing the predicate you wish to search for
		'''
		df1 = self.get_edges_between_subject_object(cui1,cui2,predicate, result_col)
		df2 = self.get_edges_between_subject_object(cui2,cui1,predicate, result_col)
		if df1 is not None and df2 is not None:
			df = pd.concat([df1,df2])
			return df
		else:
			if df1 is not None:
				return df1
			if df2 is not None:
				return df2
			return None

	def get_edges_between_subject_object_with_pivot(self, subject_cui, object_cui, pivot = 1, limit = 0):
		'''
		This method finds all of the connections between a subject and object with a given number of pivots such that it does not reach the object or double back to the subject before reaching the desired length
		params:
			subject_cui = a string containing the cui for the subject
			object_cui = a string containing the cui for the object
			(optional) pivots = an integer containing the nuber of pivots you wish to make (this will result in connection between nodes of length pivot + 1 and it defaults to 1)
			(optional) limit = an integer containing a limit on the number of results to return (this defaults to 0 which means no limit is placed)
		NOTE: Currently this is hardcoded to output name | predicate | name | predicate | name ... etc 
		NOTE2: this currently prevents hitting the begining or end nodes until the requested number of pivots are made. I plan on adding to this so it does not hit any nodes twice.
		'''
		query = "SELECT DISTINCT " + \
			"a.SUBJECT_NAME as element1, " + \
			"a.PREDICATE as predicate1, " + \
			"a.OBJECT_NAME as element2"
		for r in range(pivot):
			query += ", " + \
				chr(ord('b') + r) + ".PREDICATE as predicate" + str(r + 2) + ", " + \
				chr(ord('b') + r) + ".OBJECT_NAME as element" + str(r + 3)
		query += " FROM SPLIT_PREDICATION a "
		for r in range(pivot):
			query += "JOIN SPLIT_PREDICATION " + chr(ord('b') + r) + \
				" ON " + chr(ord('b') + r-1) + ".OBJECT_CUI = " + \
				chr(ord('b') + r) + ".SUBJECT_CUI "
		query += "WHERE a.SUBJECT_CUI='" + subject_cui + "' AND " + \
			chr(ord('a') + pivot) + ".OBJECT_CUI='" + object_cui + "'"
		if pivot > 1:
			for r in range(pivot - 1):
				query += " AND " + chr(ord('b') + r) + ".SUBJECT_CUI != '" + subject_cui + "'" + \
					" AND " + chr(ord('b') + r) + ".SUBJECT_CUI != '" + object_cui + "'"
		if limit > 0:
			query += " LIMIT " + str(limit)
		df = self.get_dataframe_from_db(query)
		return df

	def get_short_paths_between_subject_object(self,subject_cui,object_cui,max_length=5):
		'''
		This method finds the shortest path (or paths if there are more than one) between two nodes
		params:
			subject_cui = a string containing the cui for the subject
			object_cui = a string containing the cui for the object
			(optional) max_length = an integer containing the number langest length you wish for this to look for before giving up (this defaults to 5)
		'''
		for n in range(max_length+1):
			if n == 0:
				df = self.get_edges_between_subject_object(subject_cui, object_cui)
				if df is not None:
					return df
			else:
				df = self.get_edges_between_subject_object_with_pivot(subject_cui, object_cui, n)
				if df is not None:
					return df
		return None



if __name__=='__main__':
	pass

