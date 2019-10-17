import sys
sys.path.append('..')
sys.path.append('../reasoningtool')

from ReasoningUtilities import weight_graph_with_google_distance
from RTXConfiguration import RTXConfiguration
from neo4j.v1 import GraphDatabase, basic_auth
from bench_mark_decorator import bench_harness

class GoogleDistBenchmark:
	def __init__(self):
		rtxConfig = RTXConfiguration()
		river = GraphDatabase.driver(rtxConfig.neo4j_bolt, \
									auth=basic_auth(rtxConfig.neo4j_username, \
									rtxConfig.neo4j_password))
		self.session = driver.session()
	@bench_harness()
	def test_google_benchmark(self):
		g = self.get_subgraph()
		weight_graph_with_google_distance(g)
	def get_subgraph(self, size_sub_graph):
		DOID, num = 'DOID', 14325
		query = "match p=(s:disease{id:"%s:%i"})-[*1..2]-() return p limit %i" %(DOID, num, size_sub_graph)
		return self.session.run(query)

if __name__ == '__main__':
	google_dist = GoogleDistBenchmark()
	google_dist.test_google_benchmark()