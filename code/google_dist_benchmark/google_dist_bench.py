import sys
sys.path.append('../reasoningtool/QuestionAnswering')

from ReasoningUtilities import weight_graph_with_google_distance
from RTXConfiguration import RTXConfiguration
from bench_mark_decorator import bench_harness

class GoogleDistBenchmark:
	@bench_harness(iterations=240)
	def test_google_benchmark(self, graph=None, *args, **kwargs):
		print("Testing google weighted distance function")
		if not graph:
			return
		weight_graph_with_google_distance(graph)
if __name__ == '__main__':
	google_dist = GoogleDistBenchmark()
	google_dist.test_google_benchmark()
