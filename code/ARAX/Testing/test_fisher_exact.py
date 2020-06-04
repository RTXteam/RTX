import sys
import os
import scipy.stats as stats
import collections
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/Feedback/")
from RTXFeedback import RTXFeedback
from ARAX_messenger import ARAXMessenger
from ARAX_overlay import ARAXOverlay
from ARAX_query import ARAXQuery
from response import Response
from actions_parser import ActionsParser
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../ARAX/ARAXQuery/Overlay/")
from fisher_exact_test import ComputeFTEST
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../reasoningtool/QuestionAnswering/")
from fisher_exact import rtx_fisher_test
import concurrent.futures
import time
start_time = time.time()

print("start ARAX_overlay")

#### Create a response object
response = Response()

#### Create an ActionsParser object
actions_parser = ActionsParser()

#### Set a simple list of actions
actions_list = [
    "overlay(action=fisher_exact_test,query_node_type=protein,adjacent_node_type=biological_process,top_n=10,cutoff=0.05)"
]

#### Parse the action_list and print the result
result = actions_parser.parse(actions_list)

response.merge(result)

if result.status != 'OK':
    print(response.show(level=Response.DEBUG))

actions = result.data['actions']

araxdb = RTXFeedback()
overlay = ARAXOverlay()
message_dict = araxdb.getMessage(19)
message = ARAXMessenger().from_dict(message_dict)
parameter=actions[0]['parameters']
#result = overlay.apply(message, parameter, response=response)
#if result.status != 'OK':
#    print(response.show(level=Response.DEBUG))
#print(result.status)
#print(len(message.knowledge_graph.nodes))
#print(message.knowledge_graph.nodes[0])
#print(message.knowledge_graph.edges[0])

# construct the instance of ARAXQuery class
araxq = ARAXQuery()

node_id_list = ['UniProtKB:P14136','UniProtKB:P35579','UniProtKB:P02647']
adjacent_type = "biological_process"
kp = "ARAX/KG1"
rel_type= "involved_in"

query = {"previous_message_processing_plan": {"processing_actions": [
                "create_message",
#                f"add_qnode(curie={node_id_list[0]}, id=n00)",
                f"add_qnode(curie={node_id_list[1]}, id=n01)",
                f"add_qnode(type={adjacent_type}, id=n02)",
#                f"add_qedge(source_id=n02, target_id=n00, id=e00, type={rel_type})",
                f"add_qedge(source_id=n02, target_id=n01, id=e01, type={rel_type})",
                f"expand(edge_id=e01,kp={kp})",
                "resultify(ignore_edge_direction=false)",
                "return(message=true, store=false)"
            ]}}
result = araxq.query(query)
print(result.status)
for edge in araxq.message.knowledge_graph.edges:
    print(edge.id)


#for node in message.knowledge_graph.nodes:
#    print([node.id,node.qnode_id])

#### Create an overlay object and use it to apply action[0] from the list
#print("Applying action")
#overlay = ARAXOverlay()
#input_parameters=actions[0]['parameters']
#print(input_parameters) #{'action': 'add_node_pmids'}
#input_message=message

#result = overlay.apply(message, actions[0]['parameters'])
#response.merge(result)

#input_node_list = []
#for node in overlay.message.knowledge_graph.nodes:
#    if node.type[0] == 'protein':
#        input_node_list.append(node.id.replace('UniProtKB:',''))

#output = fisher_exact(input_node_list,"protein","biological_process",debug=True)
#print(output)

#araxq = ARAXQuery()
#name="UniProtKB:P14136"
#query = {"previous_message_processing_plan": {"processing_actions": [
#            "create_message",
#            "add_qnode(name="+name+", id=n00)",
#            "add_qnode(type=biological_process, id=n01)",
#            "add_qedge(source_id=n00, target_id=n01, id=e00, type=involved_in)",
#            "expand(edge_id=e00,kp=ARAX/KG1)",
#            "overlay(action=add_node_pmids)",
#            "resultify(ignore_edge_direction=false)",
#            "return(message=true, store=false)"
#        ]}}
#result = araxq.query(query)
#print(result.status)
#print(isinstance(araxq.message.knowledge_graph,dict))

#print(len(araxq.message.knowledge_graph.edges))
#for node in araxq.message.knowledge_graph.nodes:
#    print(node.id)
#print(araxq.message.knowledge_graph.edges[0])

#output = {}
#output['res1'] = stats.fisher_exact([[8, 2], [1, 5]])
#output['res2'] = stats.fisher_exact([[5, 2], [4, 5]])
#output['res3'] = stats.fisher_exact([[5, 1], [4, 5]])
#output['res4'] = stats.fisher_exact([[5, 2], [4, 8]])
#output['res5'] = stats.fisher_exact([[5, 2], [4, 6]])
#print(overlay.message.knowledge_graph.nodes[0].type[0])
#print(overlay.response.show(level=Response.DEBUG))
#print(output.items())
#print(dict(sorted(output.items(), key=lambda x: x[1][0])))
#print(dict(filter(lambda x: x[1][1]<0.05, output.items())))

#test = [1,3,4,5,6,2,3,3]
#print(list(set(test)))

#print(message.results[0])

def query_adjacent_node_based_on_edge_type(this):
    """
    Query adjacent nodes of a given node based on adjacent node type.
    :param node_id: the id of query node eg. "UniProtKB:P14136"
    :param adjacent_type: the type of adjacent node eg. "biological_process"
    :param kp: the knowledge provider to use eg. "ARAX/KG1"(default)
    :param rel_type: optional relationship type to consider, eg. "involved_in"
    :return adjacent node ids
    """
    # this contains four variables and assign them to different variables
    node_id, adjacent_type, kp, rel_type = this

    # Initialize variables
    adjacent_node_id = []

    # construct the instance of ARAXQuery class
    araxq = ARAXQuery()

    # call the method of ARAXQuery class to query adjacent node

    if rel_type:
        query = {"previous_message_processing_plan": {"processing_actions": [
            "create_message",
            "add_qnode(name=" + node_id + ", id=n00)",
            "add_qnode(type=" + adjacent_type + ", id=n01)",
            "add_qedge(source_id=n00, target_id=n01, id=e00, type=" + rel_type + ")",
            "expand(edge_id=e00,kp=" + kp + ")",
            "resultify(ignore_edge_direction=false)",
            "return(message=true, store=false)"
        ]}}
    else:
        query = {"previous_message_processing_plan": {"processing_actions": [
            "create_message",
            "add_qnode(name=" + node_id + ", id=n00)",
            "add_qnode(type=" + adjacent_type + ", id=n01)",
            "add_qedge(source_id=n00, target_id=n01, id=e00)",
            "expand(edge_id=e00,kp=" + kp + ")",
            "resultify(ignore_edge_direction=false)",
            "return(message=true, store=false)"
        ]}}

    try:
        result = araxq.query(query)
        if result.status != 'OK':
            if not isinstance(araxq.message.knowledge_graph, dict):
                for node in araxq.message.knowledge_graph.nodes:
                    if node.id != node_id:
                        adjacent_node_id.append(node.id)
                    else:
                        continue
            else:
                pass
        else:
            for node in araxq.message.knowledge_graph.nodes:
                if node.id != node_id:
                    adjacent_node_id.append(node.id)
                else:
                    continue
    except:
        pass
#        tb = traceback.format_exc()
#        error_type, error, _ = sys.exc_info()
#        self.response.error(tb, error_code=error_type.__name__)
#        self.response.error(f"Something went wrong with querying adjacent nodes from KP")
#        return None

#    return adjacent_node_id
    if node_id == 'UniProtKB:P01033':
        return "ERROR"


#query_node_list = ['UniProtKB:P04040', 'UniProtKB:P01033', 'UniProtKB:P23975', 'UniProtKB:P12821', 'UniProtKB:P02671', 'UniProtKB:O00206', 'UniProtKB:P35579', 'UniProtKB:P08253', 'UniProtKB:P01584', 'UniProtKB:P37231', 'UniProtKB:P08588', 'UniProtKB:Q15831', 'UniProtKB:P13500', 'UniProtKB:P61769', 'UniProtKB:P51168', 'UniProtKB:P06858', 'UniProtKB:Q02108', 'UniProtKB:Q04206', 'UniProtKB:P04637', 'UniProtKB:P31513', 'UniProtKB:P49841', 'UniProtKB:P11597', 'UniProtKB:Q03135', 'UniProtKB:P10275', 'UniProtKB:P00797', 'UniProtKB:P01137', 'UniProtKB:P05362', 'UniProtKB:P16520', 'UniProtKB:P02649', 'UniProtKB:O43597', 'UniProtKB:P30711', 'UniProtKB:P19099', 'UniProtKB:P05231', 'UniProtKB:P35228', 'UniProtKB:P51170', 'UniProtKB:A0A087WVP0', 'UniProtKB:P00738', 'UniProtKB:P21912', 'UniProtKB:P29279', 'UniProtKB:P0CG29', 'UniProtKB:P05305', 'UniProtKB:Q05655', 'UniProtKB:P02647', 'UniProtKB:P31040', 'UniProtKB:Q99836', 'UniProtKB:P04798', 'UniProtKB:O94761', 'UniProtKB:O95467', 'UniProtKB:P80365', 'UniProtKB:P61626', 'UniProtKB:P02751', 'UniProtKB:P05121', 'UniProtKB:P29474', 'UniProtKB:P11473', 'UniProtKB:P01019', 'UniProtKB:P02452', 'UniProtKB:P51788', 'UniProtKB:Q6FG41', 'UniProtKB:Q9NPH5', 'UniProtKB:P16671', 'UniProtKB:P10415', 'UniProtKB:P14416', 'UniProtKB:P01100', 'UniProtKB:P14780', 'UniProtKB:P05412', 'UniProtKB:P14136', 'UniProtKB:P08F94', 'UniProtKB:Q15599', 'UniProtKB:P98161', 'UniProtKB:P01275', 'UniProtKB:P02741', 'UniProtKB:P30556', 'UniProtKB:P60891', 'UniProtKB:Q99643', 'UniProtKB:P01375', 'UniProtKB:P04150', 'UniProtKB:P19320', 'UniProtKB:P01270', 'UniProtKB:P41159']
#parament_list = [(element,"biological_process","ARAX/KG1",None) for element in query_node_list]

#print(parament_list)

#with concurrent.futures.ProcessPoolExecutor() as executor:
#    res = list(executor.map(query_adjacent_node_based_on_edge_type, parament_list[:3]))

#if "ERROR" in res:
#    print('yes')

print("Finished applying action")
print("running time: %s seconds " % (time.time() - start_time))