# import requests_cache
# import CachedMethods
from NormGoogleDistance import NormGoogleDistance
import time
import pandas
import csv

df = pandas.read_csv('nodes_id_name.csv')

for a in range(len(df['id'])):
	b = NormGoogleDistance.get_mesh_term_for_all(df['id'][a],df['name'][a])

