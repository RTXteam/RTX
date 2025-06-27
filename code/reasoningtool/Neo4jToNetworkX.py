import networkx as nx
import cypher
from collections import namedtuple

import sys, os

# Get rtxConfig
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../")  # code directory
from RTXConfiguration import RTXConfiguration
rtxConfig = RTXConfiguration()

# Connection information for the ipython-cypher package
connection = "http://" + rtxConfig.neo4j_username + ":" + rtxConfig.neo4j_password + "@" + rtxConfig.neo4j_database
DEFAULT_CONFIGURABLE = {
	"auto_limit": 0,
	"style": 'DEFAULT',
	"short_errors": True,
	"data_contents": True,
	"display_limit": 0,
	"auto_pandas": False,
	"auto_html": False,
	"auto_networkx": False,
	"rest": False,
	"feedback": False,  # turn off verbosity in ipython-cypher
	"uri": connection,
}
DefaultConfigurable = namedtuple(
	"DefaultConfigurable",
	", ".join([k for k in DEFAULT_CONFIGURABLE.keys()])
)
config = DefaultConfigurable(**DEFAULT_CONFIGURABLE)

# Convert neo4j subgraph (from cypher query) into a networkx graph
def get_graph(res, directed=True):
	"""
	This function takes the result (subgraph) of a ipython-cypher query and builds a networkx graph from it
	:param res: output from an ipython-cypher query
	:param directed: Flag indicating if the resulting graph should be treated as directed or not
	:return: networkx graph (MultiDiGraph or MultiGraph)
	"""
	if nx is None:
		raise ImportError("Try installing NetworkX first.")
	if directed:
		graph = nx.MultiDiGraph()
	else:
		graph = nx.MultiGraph()
	for item in res._results.graph:
		for node in item['nodes']:
			graph.add_node(node['id'], properties=node['properties'], labels=node['labels'], names=node['properties']['name'], description=node['properties']['description'])
		for rel in item['relationships']:
			graph.add_edge(rel['startNode'], rel['endNode'], id=rel['id'], properties=rel['properties'], type=rel['type'])
	return graph

def test_get_graph():
	query = "MATCH path=allShortestPaths((s:omim_disease)-[*1..%d]-(t:disont_disease)) " \
			"WHERE s.name='%s' AND t.name='%s' " \
			"RETURN path" % (4, 'OMIM:137920', 'DOID:11476')
	res = cypher.run(query, conn=connection, config=config)
	graph = get_graph(res, directed=True)
	if type(graph) is not nx.classes.MultiDiGraph:
		raise(Exception("A networkx graph was not returned"))
	if graph.number_of_nodes() < 1:
		raise(Exception("An empty graph was returned"))
