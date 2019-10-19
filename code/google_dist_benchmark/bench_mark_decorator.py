import time
import cypher

from networkx import edges,nodes
from matplotlib import pyplot as plt
from ReasoningUtilities import defaults
from ReasoningUtilities import connection
from ReasoningUtilities import get_graph

"""
	Name: bench_harness
	input:
		iterations:int
	output:
		function: test_google_benchmark
	description:
		This is the decorator function
		used as our testing harness
"""
def bench_harness(iterations):
	def bench_start(function, *args, **kwargs):
		file_name = './benchmark_res/benchmark_res.txt'
		f = open(file_name, 'a')
		for i in range(240,iterations+1, 100):
			run_time_res = []
			"""
				set limit in the neo4j parameter
				to scale linearly with number
				of iterations
			"""
			graph_weighted_dist = run_cipher(i)
			# bench mark out function and calculate our runtime
			ts = time.time()
			function(None,graph=graph_weighted_dist, *args, **kwargs)
			te = time.time()
			run_time = te-ts
			# get number of edges and nodes
			edges_for_graph, nodes_for_graph = get_edges_nodes(graph_weighted_dist)
			num_nodes,num_edges - get_num_edges_nodes(nodes_in_graph, edges_in_graph)
			# write the result into a text file
			edge_runtime_data = "%i\t%f\n" % (num_edges, float(run_time))
			f.write(edge_runtime_data)
			output_msg = "Currently at iteration %i with %i edges and %i nodes" % (i, num_edges, num_nodes)
			print(output_msg)
		f.close()
		return function
	def run_cipher(i):
		query = 'match p=(s:disease{id:"DOID:12365"})-[*1..2]-() return p limit %i' %(i)
		res = cypher.run(query, conn=connection, config=defaults)
		return get_graph(res, directed=True)
	def get_edges_nodes(graph):
		return graph.edges(), nodes(graph)
	def get_num_edges_nodes(nodes_in_graph, edges_in_graph):
		return len(list(nodes_in_graph)), len(list(edges_in_graph))
	return bench_start