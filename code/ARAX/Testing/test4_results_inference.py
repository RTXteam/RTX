#!/usr/bin/python3
import sys
def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

import os
import json
import ast

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../ARAXQuery")
from ARAX_messenger import ARAXMessenger
from knowledge_graph_info import KnowledgeGraphInfo
from query_graph_info import QueryGraphInfo
from response import Response


def main():

    #### Create a response object
    response = Response()

    #### Read message #2 from the database. This should be the acetaminophen proteins query result message
    sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/Feedback")
    from RTXFeedback import RTXFeedback
    araxdb = RTXFeedback()
    message_dict = araxdb.getMessage(2)

    #### The stored message comes back as a dict. Transform it to objects
    messenger = ARAXMessenger()
    message = messenger.from_dict(message_dict)
 
    #### Asses some information about the QueryGraph
    query_graph_info = QueryGraphInfo()
    result = query_graph_info.assess(message)
    response.merge(result)
    if result.status != 'OK':
        print(response.show(level=Response.DEBUG))
        return response
    #print(json.dumps(ast.literal_eval(repr(query_graph_info.node_order)),sort_keys=True,indent=2))

    #### Try to add query_graph_ids to the KnowledgeGraph
    knowledge_graph_info = KnowledgeGraphInfo()
    result = knowledge_graph_info.add_query_graph_tags(message,query_graph_info)
    response.merge(result)
    if result.status != 'OK':
        print(response.show(level=Response.DEBUG))
        return response

    #### Reassess some information about the KnowledgeGraph
    result = knowledge_graph_info.check_for_query_graph_tags(message,query_graph_info)
    response.merge(result)
    if result.status != 'OK':
        print(response.show(level=Response.DEBUG))
        return response

    #### Try to re-create the results list
    result = messenger.generate_results(message)
    response.merge(result)
    if result.status != 'OK':
        print(response.show(level=Response.DEBUG))
        return response


    print(response.show(level=Response.DEBUG))

    tmp = { 'query_graph_id_node_status': knowledge_graph_info.query_graph_id_node_status, 'query_graph_id_edge_status': knowledge_graph_info.query_graph_id_edge_status, 
        'n_nodes': knowledge_graph_info.n_nodes, 'n_edges': knowledge_graph_info.n_edges }
    #print(json.dumps(message.to_dict(),sort_keys=True,indent=2))
    print(json.dumps(ast.literal_eval(repr(tmp)),sort_keys=True,indent=2))




if __name__ == "__main__": main()
