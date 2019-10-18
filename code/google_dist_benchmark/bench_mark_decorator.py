import time
from networkx import edges
from matplotlib import pyplot as plt

def bench_harness(iterations):
	def bench_start(function):
		file_name = './benchmark_res/%s_iterations.txt' % (str(iterations))
		for iteration in range(iterations):
			run_time_res = []
			ts = time.time()
			"""
				set limit to scale linearly with number
				of iterations
			"""
			graph_weighted_dist = function(iteration)
			te = time.time()
			run_time = te-ts
			# get number of edges
			edges_for_graph = edges(graph_weighted_dist)
			run_time_res.append((edges_for_graph, run_time))
			# run matplotlib to plot the result
			with open('./benchmark_res', 'a') as f:
				for edge, run_time in run_time_res:
					edge_runtime_data = "%i\t%i" % (edge, run_time)
					f.write(edge_runtime_data)
				f.close()
	return bench_start