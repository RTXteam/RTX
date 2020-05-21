import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/Feedback/")
from RTXFeedback import RTXFeedback
from ARAX_messenger import ARAXMessenger
from ARAX_overlay import ARAXOverlay
from response import Response
from actions_parser import ActionsParser

print("start ARAX_overlay")

#### Create a response object
response = Response()

#### Create an ActionsParser object
actions_parser = ActionsParser()

#### Set a simple list of actions
actions_list = [
#    "overlay(compute_confidence_scores=true)",
#    "overlay(action=compute_ngd)",
#    "overlay(action=overlay_clinical_info,chi_square=true)",
#    "overlay(action=predict_drug_treats_disease)",
    "overlay(action=overlay_clinical_info, observed_expected_ratio=true)",
    "return(message=true,store=false)"
]

#### Parse the action_list and print the result
result = actions_parser.parse(actions_list)

response.merge(result)

if result.status != 'OK':
    print(response.show(level=Response.DEBUG))

actions = result.data['actions']

araxdb = RTXFeedback()
message_dict = araxdb.getMessage(19)
message = ARAXMessenger().from_dict(message_dict)

#### Create an overlay object and use it to apply action[0] from the list
print("Applying action")
overlay = ARAXOverlay()
input_parameters=actions[0]['parameters']
print(input_parameters) #{'action': 'add_node_pmids'}
input_message=message
result = overlay.apply(message, actions[0]['parameters'])
response.merge(result)

nodes=overlay.message.knowledge_graph.edges[0]
print(nodes)
#print(overlay.message.knowledge_graph.nodes[0].type[0])
#print(overlay.response.show(level=Response.DEBUG))

#print(message.results[0])
print("Finished applying action")

