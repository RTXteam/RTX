#!/usr/bin/python3
from __future__ import print_function
import sys
def eprint(*args, **kwargs):
        print(*args, file=sys.stderr, **kwargs)

import os
import argparse
import json
import sys
import time
import warnings
import networkx as nx

# PyCharm doesn't play well with relative imports + python console + terminal
try:
    from code.reasoningtool import ReasoningUtilities as RU
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import ReasoningUtilities as RU

import FormatOutput
import CustomExceptions

#### Import the Translator API classes
from swagger_server.models.message import Message
from swagger_server.models.result import Result
from swagger_server.models.knowledge_graph import KnowledgeGraph
from swagger_server.models.node import Node
from swagger_server.models.edge import Edge
from swagger_server.models.query_graph import QueryGraph
from swagger_server.models.q_node import QNode
from swagger_server.models.q_edge import QEdge
from swagger_server.models.edge_attribute import EdgeAttribute
from swagger_server.models.node_attribute import NodeAttribute

from KGNodeIndex import KGNodeIndex

output_formats = ['DENSE', 'MESSAGE', 'CSV', 'ANSWERS']


def cypher_prop_string(value):
    """Convert property value to cypher string representation."""
    if isinstance(value, bool):
        return str(value).lower()
    elif isinstance(value, str):
        return f"'{value}'"
    else:
        raise ValueError(f'Unsupported property type: {type(value).__name__}.')


class NodeReference():
    """Node reference object."""

    def __init__(self, node):
        """Create a node reference."""
        node = dict(node)
        name = f'{node.pop("id")}'
        label = node.pop('type', None)
        props = {}

        if label == 'biological_process':
            label = 'biological_process_or_activity'

        curie = node.pop("curie", None)
        if curie is not None:
            if isinstance(curie, str):
                props['id'] = curie
                conditions = ''
            elif isinstance(curie, list):
                conditions = []
                for ci in curie:
                    # generate curie-matching condition
                    conditions.append(f"{name}.id = '{ci}'")
                # OR curie-matching conditions together
                conditions = ' OR '.join(conditions)
            else:
                raise TypeError("Curie should be a string or list of strings.")
        else:
            conditions = ''

        node.pop('name', None)
        node.pop('set', False)
        props.update(node)

        self.name = name
        self.label = label
        self.prop_string = ' {' + ', '.join([f"`{key}`: {cypher_prop_string(props[key])}" for key in props]) + '}'
        self._conditions = conditions
        self._num = 0

    def __str__(self):
        """Return the cypher node reference."""
        self._num += 1
        if self._num == 1:
            return f'{self.name}' + \
                   f'{":" + self.label if self.label else ""}' + \
                   f'{self.prop_string}'
        return self.name

    @property
    def conditions(self):
        """Return conditions for the cypher node reference.

        To be used in a WHERE clause following the MATCH clause.
        """
        if self._num == 1:
            return self._conditions
        else:
            return ''

class EdgeReference():
    """Edge reference object."""

    def __init__(self, edge):
        """Create an edge reference."""
        name = f'{edge["id"]}'
        label = edge['type'] if 'type' in edge else None

        if 'type' in edge and edge['type'] is not None:
            if isinstance(edge['type'], str):
                label = edge['type']
                conditions = ''
            elif isinstance(edge['type'], list):
                conditions = []
                for predicate in edge['type']:
                    conditions.append(f'type({name}) = "{predicate}"')
                conditions = ' OR '.join(conditions)
                label = None
        else:
            label = None
            conditions = ''

        self.name = name
        self.label = label
        self._num = 0
        self._conditions = conditions

    def __str__(self):
        """Return the cypher edge reference."""
        self._num += 1
        if self._num == 1:
            return f'{self.name}{":" + self.label if self.label else ""}'
        else:
            return self.name

    @property
    def conditions(self):
        """Return conditions for the cypher node reference.

        To be used in a WHERE clause following the MATCH clause.
        """
        if self._num == 1:
            return self._conditions
        else:
            return ''


class QueryGraphReasoner:

    def __init__(self):
        None

    def unpack(self, *args, **kwargs):
        """Create a question.

        keyword arguments: question_graph or machine_question, knowledge_graph, answers
        """
        # initialize all properties
        self.natural_question = ''
        self.question_graph = {}
        self.knowledge_graph = None
        self.answers = None

        # apply json properties to existing attributes
        attributes = self.__dict__.keys()
        if args:
            struct = args[0]
            for key in struct:
                if key in attributes:
                    setattr(self, key, struct[key])
                elif key == 'machine_question':
                    setattr(self, 'question_graph', struct[key])
                else:
                    warnings.warn("JSON field {} ignored.".format(key))

        # override any json properties with the named ones
        for key in kwargs:
            if key in attributes:
                setattr(self, key, kwargs[key])
            elif key == 'machine_question':
                setattr(self, 'question_graph', kwargs[key])
            else:
                warnings.warn("Keyword argument {} ignored.".format(key))

        # Added this to remove values 
        if 'edges' in self.question_graph:
        	for edge in self.question_graph['edges']:
        		for edge_key in edge.keys():
        			if edge[edge_key] is None:
        				edge.pop(edge_key)
        			elif edge_key == 'edge_id':
        				edge['id'] = edge.pop(edge_key)

        # add ids to question graph edges if necessary ()
        if not any(['id' in e for e in self.question_graph['edges']]):
            for i, e in enumerate(self.question_graph['edges']):
                e['id'] = chr(ord('a') + i)

        # Added this to remove values 
        if 'nodes' in self.question_graph:
        	for node in self.question_graph['nodes']:
        		for node_key in node.keys():
        			if node[node_key] is None:
        				node.pop(node_key)
        			elif node_key == 'node_id':
        				node['id'] = node.pop(node_key)

    def cypher_query_fragment_match(self, max_connectivity=0): # cypher_match_string
        '''
        Generate a Cypher query fragment to match the nodes and edges that correspond to a question.

        This is used internally for cypher_query_answer_map and cypher_query_knowledge_graph

        Returns the query fragment as a string.
        '''

        nodes, edges = self.question_graph['nodes'], self.question_graph['edges']

        # generate internal node and edge variable names
        node_references = {n['id']: NodeReference(n) for n in nodes}
        edge_references = [EdgeReference(e) for e in edges]

        match_strings = []

        # match orphaned nodes
        def flatten(l):
            return [e for sl in l for e in sl]
        all_nodes = set([n['id'] for n in nodes])
        all_referenced_nodes = set(flatten([[e['source_id'], e['target_id']] for e in edges]))
        orphaned_nodes = all_nodes - all_referenced_nodes
        for n in orphaned_nodes:
            match_strings.append(f"MATCH ({node_references[n]})")
            if node_references[n].conditions:
                match_strings.append("WHERE " + node_references[n].conditions)

        # match edges
        include_size_constraints = bool(max_connectivity)
        for e, eref in zip(edges, edge_references):
            source_node = node_references[e['source_id']]
            target_node = node_references[e['target_id']]
            has_type = 'type' in e and e['type']
            is_directed = e.get('directed', has_type)
            if is_directed:
                match_strings.append(f"MATCH ({source_node})-[{eref}]->({target_node})")
            else:
                match_strings.append(f"MATCH ({source_node})-[{eref}]-({target_node})")
            conditions = [f'({c})' for c in [source_node.conditions, target_node.conditions, eref.conditions] if c]
            if conditions:
                match_strings.append("WHERE " + " AND ".join(conditions))
                if include_size_constraints:
                    match_strings.append(f"AND size( ({target_node})-[]-() ) < {max_connectivity}")
            else:
                if include_size_constraints:
                    match_strings.append(f"WHERE size( ({target_node})-[]-() ) < {max_connectivity}")



        match_string = ' '.join(match_strings)
        # logger.debug(match_string)
        return match_string

    def cypher_query_answer_map(self, options=None):
        '''
        Generate a Cypher query to extract the answer maps for a question.

        Returns the query as a string.
        '''

        max_connectivity = 0
        if options and 'max_connectivity' in options:
            max_connectivity = options['max_connectivity']
        
        match_string = self.cypher_query_fragment_match(max_connectivity)

        nodes, edges = self.question_graph['nodes'], self.question_graph['edges']
        # node_map = {n['id']: n for n in nodes}

        # generate internal node and edge variable names
        node_names = [f"{n['id']}" for n in nodes]
        edge_names = [f"{e['id']}" for e in edges]

        # deal with sets
        node_id_accessor = [f"collect(distinct {n['id']}.id) as {n['id']}" if 'set' in n and n['set'] else f"{n['id']}.id as {n['id']}" for n in nodes]
        edge_id_accessor = [f"collect(distinct toString(id({e['id']}))) as {e['id']}" for e in edges]
        with_string = f"WITH {', '.join(node_id_accessor+edge_id_accessor)}"

        # add bound fields and return map
        answer_return_string = f"RETURN {{{', '.join([f'{n}:{n}' for n in node_names])}}} as nodes, {{{', '.join([f'{e}:{e}' for e in edge_names])}}} as edges"

        # return answer maps matching query
        query_string = ' '.join([match_string, with_string, answer_return_string])
        if options is not None:
            if 'skip' in options:
                query_string += f' SKIP {options["skip"]}'
            if 'limit' in options:
                query_string += f' LIMIT {options["limit"]}'

        return query_string

    def cypher_query_knowledge_graph(self, options=None): #kg_query
        '''
        Generate a Cypher query to extract the knowledge graph for a question.

        Returns the query as a string.
        '''

        max_connectivity = 0
        if options and 'max_connectivity' in options:
            max_connectivity = options['max_connectivity']

        match_string = self.cypher_query_fragment_match(max_connectivity)

        nodes, edges = self.question_graph['nodes'], self.question_graph['edges']

        # generate internal node and edge variable names
        node_names = [f"{n['id']}" for n in nodes]
        edge_names = [f"{e['id']}" for e in edges]

        collection_string = "WITH "
        collection_string += ' + '.join([f'collect(distinct {n})' for n in node_names]) + ' as nodes, '
        if edge_names:
            collection_string += ' + '.join([f'collect(distinct {e})' for e in edge_names]) + ' as edges'
        else:
            collection_string += '[] as edges'
        collection_string += "\nUNWIND nodes as n WITH collect(distinct n) as nodes, edges"
        if edge_names:
            collection_string += "\nUNWIND edges as e WITH nodes, collect(distinct e) as edges"""
        support_string = """WITH
            [r in edges | r{.*, source_id:startNode(r).id, target_id:endNode(r).id, type:type(r), id:toString(id(r))}] as edges,
            [n in nodes | n{.*, type:labels(n)}] as nodes"""
        return_string = 'RETURN nodes, edges'
        query_string = "\n".join([match_string, collection_string, support_string, return_string])

        return query_string

    def answer(self, query_graph, use_json=False):
        """
        Answer a question based on the input query_graph:
        :param query_graph: QueryGraph object
        :param use_json: If the answer should be in Translator standardized API output format
        :return: Result of the query in simplified or API format
        """

        #### Interpret the query_graph object to create a cypher query and encode the result in a response




        #### Dang. I don't know how to do that, so instead do something super simple: describe qnode[0]
        # See Q3Solution.py and SimilarityQuestionSolution.py for more insight into generating 0.9.0


    #### Pull out the first node and look it up in the KGNodeIndex
        entity = query_graph.nodes[0].curie
        eprint("Looking up '%s' in KgNodeIndex" % entity)
        kgNodeIndex = KGNodeIndex()
        curies = kgNodeIndex.get_curies(entity)

        #### If not in the KG, then return no information
        if not curies:
            if not use_json:
                return None
            else:
                error_code = "TermNotFound"
                error_message = "This concept is not in our knowledge graph"
                response = FormatOutput.FormatResponse(0)
                response.add_error_message(error_code, error_message)
                return response.message

        # Get label/kind of node the source is
        eprint("Getting properties for '%s'" % curies[0])
        properties = RU.get_node_properties(curies[0])
        eprint("Properties are:")
        eprint(properties)

        #### By default, return the results just as a plain simple list of data structures
        if not use_json:
            return properties

        #### Or, if requested, format the output as the standardized API output format
        else:
            #### Create a stub Message object
            response = FormatOutput.FormatResponse(0)
            response.message.table_column_names = [ "id", "type", "name", "description", "uri" ]
            response.message.code_description = None

            #### Include the original query_graph in the envelope
            response.message.query_graph = query_graph

            #### Create a Node object and fill it
            node1 = Node()
            node1.id = properties["id"]
            node1.uri = properties["uri"]
            node1.type = [ properties["category"] ]
            node1.name = properties["name"]
            node1.description = properties["description"]

            #### Create the first result (potential answer)
            result1 = Result()
            result1.id = "http://rtx.ncats.io/api/v1/result/0000"
            result1.description = "The term %s is in our knowledge graph and is defined as %s" % ( properties["name"],properties["description"] )
            result1.confidence = 1.0
            result1.essence = properties["name"]
            result1.essence_type = properties["category"]
            node_types = ",".join(node1.type)
            result1.row_data = [ node1.id, node_types, node1.name, node1.description, node1.uri ]

            #### Create a KnowledgeGraph object and put the list of nodes and edges into it
            result_graph = KnowledgeGraph()
            result_graph.nodes = [ node1 ]

            #### Put the ResultGraph into the first result (potential answer)
            #This is legal but deprecated and discouraged in v0.9.1
            #result1.result_graph = result_graph

            #### Put the first result (potential answer) into the message
            results = [ result1 ]
            response.message.results = results

            #### Also put the union of all result_graph components into the top Message KnowledgeGraph
            #### Normally the knowledge_graph will be much more complex than this, but take a shortcut for this single-node result
            response.message.knowledge_graph = result_graph

            #### Also manufacture a query_graph post hoc
            qnode1 = QNode()
            qnode1.node_id = "n00"
            qnode1.curie = properties["id"]
            qnode1.type = None

            #### Create the corresponding knowledge_map for this result
            node_bindings = { "n00": [ properties["id"] ] }
            result1.node_bindings = node_bindings
            result1.edge_bindings = []

            return(response.message)




    def from_dict(self,query_graph_dict):
        query_graph = QueryGraph()
        query_graph.nodes = []
        query_graph.edges = []
        if "nodes" in query_graph_dict:
            for node in query_graph_dict["nodes"]:
                qnode = QNode().from_dict(node)
                query_graph.nodes.append(qnode)
        if "edges" in query_graph_dict:
            for edge in query_graph_dict["edges"]:
                qedge = QEdge().from_dict(edge)
                query_graph.edges.append(qedge)
        return query_graph


    def describe(self):
        output = "Answers questions based on an input QueryGraph object\n"
        return output


# Tests
def tests():
    result = test1_2nodes()
    return(result)


# Test 1
def test1_2nodes():
    q = QueryGraphReasoner()
    query_graph_json_stream = '''{
    "edges": [
      {
        "edge_id": "e00",
        "source_id": "n00",
        "target_id": "n01",
        "type": "physically_interacts_with"
      }
    ],
    "nodes": [
      {
        "curie": "CHEMBL.COMPOUND:CHEMBL112",
        "node_id": "n00",
        "type": "chemical_substance"
      },
      {
        "curie": null,
        "is_set": null,
        "node_id": "n01",
        "type": "protein"
      }
    ]
    }'''

    query_graph_dict = json.loads(query_graph_json_stream)
    query_graph = QueryGraphReasoner().from_dict(query_graph_dict)
    result = q.answer(query_graph, use_json=True)
    return(result)


def main():
    parser = argparse.ArgumentParser(description="Answers questions based on an input QueryGraph object'.",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-i', '--input_file', type=str, help="input file name of JSON of a serialized QueryGraph", default=False)
    parser.add_argument('-j', '--json', action='store_true', help='Flag specifying that results should be printed in Translator standard format (to stdout)', default=False)
    parser.add_argument('-d', '--describe', action='store_true', help="Describe what kinds of questions this answers.", default=False)
    parser.add_argument('-t', '--test', action='store_true', help="Run tests", default=False)

    # Parse and check args
    args = parser.parse_args()
    input_file = args.input_file
    use_json = args.json

    # Initialize the question class
    q = QueryGraphReasoner()

    if args.describe:
        result = q.describe()
        print(result)
        return()

    if args.test:
        result = tests()
        print(result)

    else:
        with open(input_file, 'r') as infile:
          query_graph_json_stream = infile.read()
        query_graph_dict = json.loads(query_graph_json_stream)
        query_graph = QueryGraphReasoner().from_dict(query_graph_dict)
        result = q.answer(query_graph, use_json=use_json)
        if use_json:
            result.print()
        else:
            print(result)


if __name__ == "__main__":
    main()
