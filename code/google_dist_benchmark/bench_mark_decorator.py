import time

def bench_harness(method):
	def bench_start(*args, **kwargs):
		ts = time.time()
		result = method()
		te = time.time()
		run_time = te-ts
		print("Run time:", run_time)
	return bench_start