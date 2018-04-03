class EmptyCypherError(Exception):
	def __init__(self, cypher_command):
		self.value = "No results returned in cypher query: %s" % cypher_command

	def __str__(self):
		return (repr(self.value))


class MultipleTerms(Exception):
	def __init__(self, entity_type, values):
		self.value = "Multiple terms found for %s: %s" % (entity_type, str(values))

	def __str__(self):
		return (repr(self.value))
