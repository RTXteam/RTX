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
import ast
import math
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


class QueryGraphReasoner:

    def __init__(self):
        None


    def answer(self, query_graph, TxltrApiFormat=False):
        """
        Answer a question based on the input query_graph:
        :param query_graph: QueryGraph object
        :param TxltrApiFormat: Set to true if the answer should be in Translator standardized API output format
        :return: Result of the query in native or API format
        """

        #### Create a stub Message object
        response = FormatOutput.FormatResponse(0)

        #### Include the original query_graph in the envelope
        response.message.query_graph = query_graph

        #### Perform some basic validation of the query graph before sending to the server
        result = self.validate_query_graph(query_graph)
        if result["message_code"] != "OK":
          response.add_error_message(result["message_code"], result["code_description"])
          return(response.message)

        #### Insert some dummy question stuff
        response.message.original_question = "Input via Query Graph"
        response.message.restated_question = "No restatement for QueryGraph yet"

        #### Preprocess query_graph object
        query_graph, sort_flags, res_limit, ascending_flag = self.preprocess_query_graph(query_graph)

        #### Interpret the query_graph object to create a cypher query and encode the result in a response
        try:
            query_gen = RU.get_cypher_from_question_graph({'question_graph':query_graph})
            answer_graph_cypher = query_gen.cypher_query_answer_map()
            knowledge_graph_cypher = query_gen.cypher_query_knowledge_graph()
        except Exception as error:
            response.add_error_message("CypherGenerationError", format(error))
            return(response.message)

        #### The Robokop code renames stuff in the query_graph for strange reasons. Rename them back.
        #### It would be better to not make the changes in the first place. FIXME
        #for node in response.message.query_graph["nodes"]:
        #    node["node_id"] = node["id"]
        #    node.pop("id", None)
        #for edge in response.message.query_graph["edges"]:
        #    edge["edge_id"] = edge["id"]
        #    edge.pop("id", None)
 
        #### Execute the cypher to obtain results[]. Return an error if there are no results, or otherwise extract the list
        try:
            with RU.driver.session() as session:
                result = session.run(answer_graph_cypher)
            answer_graph_list = result.data()
        except Exception as error:
            response.add_error_message("QueryGraphError", format(error))
            return(response.message)

        if len(answer_graph_list) == 0:
            response.add_error_message("NoPathsFound", "No paths satisfying this query graph were found")
            return(response.message)

        #### Execute the knowledge_graph cypher. Return an error if there are no results, or otherwise extract the dict
        try:
            with RU.driver.session() as session:
                result = session.run(knowledge_graph_cypher)
            result_data = result.data()
        except Exception as error:
            response.add_error_message("QueryGraphError", format(error))
            return(response.message)

        if len(result_data) == 0:
            response.add_error_message("NoPathsFound", "No paths satisfying this query graph were found")
            return(response.message)
        knowledge_graph_dict = result_data[0]

        #### If TxltrApiFormat was not specified, just return a single data structure with the results
        if not TxltrApiFormat:
            return {'answer_subgraphs': answer_graph_list, 'knowledge_graph':knowledge_graph_dict}

        #### Add the knowledge_graph and bindings to the Message
        response.add_split_results(knowledge_graph_dict, answer_graph_list)
        #response.message.table_column_names = [ "id", "type", "name", "description", "uri" ]
        #response.message.code_description = None

        #### Enrich the Message Results with some inferred information
        response.infer_result_information()

        #### Return the final result message
        return(response.message)


    def validate_query_graph(self, query_graph):
        """
        Check to make sure that the query_graph has no known flaws:
        :param query_graph: QueryGraph object        :param TxltrApiFormat: Set to true if the answer should be in Translator standardized API output format
        :return: { "message_code": "OK|someErrorCode", "code_description": "description of the problem" }
        """

        nodes = query_graph["nodes"]
        edges = query_graph["edges"]
        n_nodes = len(nodes)
        n_edges = len(edges)
        #eprint("DEBUG: n_nodes = %d, n_edges = %d" % (n_nodes,n_edges))

        #### Handle 0 nodes case
        if n_nodes == 0:
          return( { "message_code": "QueryGraphZeroNodes", "code_description": "Submitted QueryGraph has 0 nodes. At least 1 node is required" } )

        #### Get a list of nodes referenced in edges
        referenced_nodes = {}
        for edge in query_graph["edges"]:
          if "id" not in edge or edge["id"] is None:
            return( { "message_code": "QueryGraphMissingEdgeId", "code_description": "Submitted QueryGraph has an edge with a missing id" } )
          if "source_id" in edge and edge["source_id"] is not None:
            referenced_nodes[edge["source_id"]] = 1
          else:
            return( { "message_code": "QueryGraphMissingSourceId", "code_description": "Submitted QueryGraph has an edge with a missing source_id" } )
          if "target_id" in edge and edge["target_id"] is not None:
            referenced_nodes[edge["target_id"]] = 1
          else:
            return( { "message_code": "QueryGraphMissingSourceId", "code_description": "Submitted QueryGraph has an edge with a missing target_id" } )

        #### Make sure any unbound nodes have an edge
        for node in query_graph["nodes"]:
          if "id" not in node or node["id"] is None:
            return( { "message_code": "QueryGraphMissingNodeId", "code_description": "Submitted QueryGraph has an node with a missing id" } )
          if node["id"] not in referenced_nodes and ( "curie" not in node or node["curie"] is None ):
            return( { "message_code": "QueryGraphUnboundEdglessNode", "code_description": "You smell the odor of burning silicon and a muffled boom. Please adjust your Query Graph so that any edgeless nodes have a specific identifier, otherwise thousands of nodes are involved." } )

        #### Remove any unapproved keys in the query_graph
        approved_node_keys = { "curie": 1, "is_set": 1, "id": 1, "type": 1, "name": 1 , "require_all" : 1}
        approved_edge_keys = { "id": 1, "source_id": 1, "target_id": 1, "type": 1, "negated": 1, "relation": 1 }
        for node in query_graph["nodes"]:
          #### Iterate on a copy of the node dict because python doesn't allow changing while iterating
          for key in node.copy():
            if key not in approved_node_keys:
              node.pop(key, None)
        for edge in query_graph["edges"]:
          #### Iterate on a copy of the edge dict because python doesn't allow changing while iterating
          for key in edge.copy():
            if key not in approved_edge_keys:
              edge.pop(key, None)


        return( {"message_code": "OK", "code_description": "QueryGraph passes basic checks" } )

    def preprocess_query_graph(self, query_graph):
        """
        This processes options for the query_graph and gets it ready to be converted into a cypher query
        
        :param query_graph: QueryGraph object
        :return: (query_graph, sort_flag, res_limit)
        """
        sort_flags = {} 
        res_limit = 0
        ascending_flag = False
        if 'nodes' in query_graph:
            #### Break up list nodes when require_all is True
            split_nodes=[]
            for node_idx in range(len(query_graph['nodes'])):
                if 'require_all' in query_graph['nodes'][node_idx]:
                    if 'curie' in query_graph['nodes'][node_idx]:
                        if isinstance(query_graph['nodes'][node_idx]['curie'],list) and query_graph['nodes'][node_idx]['require_all'] == True:
                            split_nodes.append(node_idx)
                    del query_graph['nodes'][node_idx]['require_all']
            for node_idx in sorted(split_nodes, reverse=True):
                split_edges = []
                node_id = query_graph['nodes'][node_idx]['id']
                if 'edges' in query_graph:
                    for edge_idx in range(len(query_graph['edges'])):
                        source_id = query_graph['edges'][edge_idx]['source_id']
                        target_id = query_graph['edges'][edge_idx]['target_id']
                        if source_id == node_id or target_id == node_id:
                            split_edges.append(edge_idx)
                added_nodes = 0
                added_edges = 0
                for curie in query_graph['nodes'][node_idx]['curie']:
                    query_graph['nodes'].append(query_graph['nodes'][node_idx].copy())
                    query_graph['nodes'][-1]['curie'] = curie
                    query_graph['nodes'][-1]['id'] = node_id + '_spl' + str(added_nodes)
                    for edge_idx in split_edges:
                        query_graph['edges'].append(query_graph['edges'][edge_idx].copy())
                        query_graph['edges'][-1]['id'] = query_graph['edges'][edge_idx]['id'] + '_spl' + str(added_edges)
                        added_edges += 1
                        if query_graph['edges'][-1]['source_id'] == node_id:
                            query_graph['edges'][-1]['source_id'] = node_id + '_spl' + str(added_nodes)
                        if query_graph['edges'][-1]['target_id'] == node_id:
                            query_graph['edges'][-1]['target_id'] = node_id + '_spl' + str(added_nodes)
                    added_nodes += 1
                for edge_idx in sorted(split_edges, reverse=True):
                    del query_graph['edges'][edge_idx]
                del query_graph['nodes'][node_idx]
            #### todo: This will parse the query graph keys and set flags for sorting
            for node in query_graph['nodes']:
                node_id = node['id']
                set_flag = False
                if 'is_set' in node:
                    set_flag=True
                    del node['is_set']
                if 'sort_type' in node:
                    if set_flag:
                        if node['sort_type'] == "jaccard":
                            sort_flags[node_id]="jaccard"
                        elif node['sort_type'] == "fisher":
                            sort_flags[node_id]="fisher"
                        elif node['sort_type'] == "top":
                            sort_flags[node_id]="top"
                    del node['sort_type']
                if 'limit_set' in node:
                    if set_flag and node_id in sort_flags:
                        res_limit = max(node['limit_set'],res_limit)
                    del node['limit_set']

        return (query_graph, sort_flags, res_limit, ascending_flag)

    def postprocess_results(self, results, sort_flags, res_limit, ascending_flag):
        #### todo: write this function
        return results


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


################################################################################
# Tests
def tests(TxltrApiFormat=False):
    result = test1_2nodes_1(TxltrApiFormat=TxltrApiFormat)
    if TxltrApiFormat:
        print(json.dumps(ast.literal_eval(repr(result)),sort_keys=True,indent=2))
    else:
        print(json.dumps(result,sort_keys=True,indent=2))

# Test 1
def test1_2nodes_1(TxltrApiFormat=False):
    q = QueryGraphReasoner()
    query_graph_json_stream = '''{
    "edges": [
      {
        "id": "e00",
        "source_id": "n00",
        "target_id": "n01",
        "type": "physically_interacts_with",
        "bannanas": "are_ripe"
      }
    ],
    "nodes": [
      {
        "curie": "CHEMBL.COMPOUND:CHEMBL112",
        "id": "n00",
        "type": "chemical_substance"
      },
      {
        "curie": null,
        "is_set": null,
        "id": "n01",
        "type": "metabolite",
        "apples": "are_red"
      }
    ]
    }'''

    query_graph_dict = json.loads(query_graph_json_stream)
    #query_graph = QueryGraphReasoner().from_dict(query_graph_dict)
    result = q.answer(query_graph_dict, TxltrApiFormat=TxltrApiFormat)
    return(result)


def test1_2nodes_2(TxltrApiFormat=False):
    q = QueryGraphReasoner()
    query_graph_json_stream = '''{
      "edges": [
        {
          "id": "e3",
          "source_id": "n1",
          "target_id": "n2",
          "type": "indicated_for"
        }
      ],
      "nodes": [
        {
          "id": "n1",
          "name": "ibuprofen",
          "curie": "CHEMBL.COMPOUND:CHEMBL521",
          "type": "chemical_substance"
        },
        {
          "id": "n2",
          "type": "disease"
        }
      ]
    }'''

    query_graph_dict = json.loads(query_graph_json_stream)
    #query_graph = QueryGraphReasoner().from_dict(query_graph_dict)
    result = q.answer(query_graph_dict, TxltrApiFormat=TxltrApiFormat)
    return(result)


def test1_2nodes_3(TxltrApiFormat=False):
    q = QueryGraphReasoner()
    query_graph_json_stream = '''{
      "edges": [      ],
      "nodes": [
        {
          "id": "n1",
          "type": "metabolite"
        }
      ]
    }'''

    query_graph_dict = json.loads(query_graph_json_stream)
    #query_graph = QueryGraphReasoner().from_dict(query_graph_dict)
    result = q.answer(query_graph_dict, TxltrApiFormat=TxltrApiFormat)
    return(result)

def test_2sets(TxltrApiFormat=False):
    q = QueryGraphReasoner()
    query_graph_dict = {
        'edges': [
            {'id': 'e00', 'source_id': 'n00', 'target_id': 'n01'}, 
            {'id': 'e01', 'source_id': 'n01', 'target_id': 'n02'}, 
            {'id': 'e02',  'source_id': 'n02', 'target_id': 'n03'}], 
        'nodes': [
            {'curie': ['DOID:12365','DOID:8398'], 'id': 'n00', 'type': 'disease'}, 
            {'id': 'n01', 'type': 'protein'}, 
            {'id': 'n02', 'type': 'pathway'}, 
            {'curie': ['UniProtKB:Q06278','UniProtKB:Q12756'], 'id': 'n03', 'type': 'protein'}
        ]}
    result = q.answer(query_graph_dict, TxltrApiFormat=TxltrApiFormat)
    return(result)

def test_2sets_require(TxltrApiFormat=False):
    q = QueryGraphReasoner()
    query_graph_dict = {
        'edges': [
            {'id': 'e00', 'source_id': 'n00', 'target_id': 'n01'}, 
            {'id': 'e01', 'source_id': 'n01', 'target_id': 'n02'}, 
            {'id': 'e02',  'source_id': 'n02', 'target_id': 'n03'}], 
        'nodes': [
            {'curie': ['DOID:12365','DOID:8398'], 'id': 'n00', 'type': 'disease'}, 
            {'id': 'n01', 'type': 'protein'}, 
            {'id': 'n02', 'type': 'pathway'}, 
            {'curie': ['UniProtKB:Q06278','UniProtKB:Q12756'], 'id': 'n03', 'type': 'protein', 'require_all': True}
        ]}
    result = q.answer(query_graph_dict, TxltrApiFormat=TxltrApiFormat)
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
    TxltrApiFormat = args.json

    # Initialize the question class
    q = QueryGraphReasoner()

    if args.describe:
        result = q.describe()
        print(result)
        return()

    if args.test:
        tests(TxltrApiFormat=TxltrApiFormat)
        return()

    else:
        with open(input_file, 'r') as infile:
          query_graph_json_stream = infile.read()
        query_graph_dict = json.loads(query_graph_json_stream)
        query_graph = QueryGraphReasoner().from_dict(query_graph_dict)
        result = q.answer(query_graph, TxltrApiFormat=TxltrApiFormat)
        if TxltrApiFormat:
            result.print()
        else:
            print(result)


if __name__ == "__main__":
    main()
