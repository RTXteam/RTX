import sys
sys.path.append('../reasoningtool/QuestionAnswering')

from ReasoningUtilities import weight_graph_with_google_distance
from RTXConfiguration import RTXConfiguration
from neo4j.v1 import GraphDatabase, basic_auth
from bench_mark_decorator import bench_harness
from networkx import edges

class GoogleDistBenchmark:
	@bench_harness(iterations=100)
	def test_google_benchmark(self, limit=1):
		rtxConfig = RTXConfiguration()
		driver = GraphDatabase.driver(rtxConfig.neo4j_bolt, \
									auth=basic_auth(rtxConfig.neo4j_username, \
									rtxConfig.neo4j_password))
		session = driver.session()
		print("limited:", limit)
		query = 'match p=(s:disease{id:"DOID:14325"})-[*1..2]-() return p limit %i' %(limit)
		print(query)
		g = session.run(query)
		# remember to count the number of
		# edges!
		weight_graph_with_google_distance(g)
		print(g)
		return g
if __name__ == '__main__':
	google_dist = GoogleDistBenchmark()
	google_dist.test_google_benchmark()