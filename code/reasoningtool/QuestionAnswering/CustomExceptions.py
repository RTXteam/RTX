class EmptyCypherError(Exception):
	def __init__(self, cypher_command):
		self.value = "No results returned in cypher query: %s" % cypher_command

	def __str__(self):
		return (repr(self.value))
