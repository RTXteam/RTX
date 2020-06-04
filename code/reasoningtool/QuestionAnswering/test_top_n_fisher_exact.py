import sys
import os
pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")
dbpath = os.path.sep.join([*pathlist[:(RTXindex+1)],'code','reasoningtool','QuestionAnswering'])
sys.path.append(dbpath)
import ReasoningUtilities as RU  # Note: this is using KG1
import fisher_exact
import scipy.stats as stats

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/Feedback/")
from RTXFeedback import RTXFeedback
from actions_parser import ActionsParser
from response import Response
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../ARAX/ARAXQuery/")
from ARAX_messenger import ARAXMessenger
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../ARAX/ARAXQuery/Overlay/")
from fisher_exact_test import ComputeFTEST


## access data from database
araxdb = RTXFeedback()
message_dict = araxdb.getMessage(19)
message = ARAXMessenger().from_dict(message_dict)
input_id_list = [node.id for node in message.knowledge_graph.nodes if node.type[0] == "protein"]
input_nodes_label = "protein"
output_node_label = "biological_process"

print(f"input protein list is {input_id_list}")

(p_value_dict, biological_process_curies) = RU.top_n_fisher_exact(input_id_list, input_nodes_label, output_node_label, rel_type=None, n=5, curie_prefix=None, on_path=None, exclude=None)
print("Below is the FET result of 'RU.top_n_fisher_exact' method")
print(f"the 5 smallest p-values of biological processes associated with the input protein list is:")
print(p_value_dict)

fisher_res_dict = fisher_exact.fisher_exact(input_id_list, input_nodes_label, output_node_label)
print("Below is the FET result of 'fisher_exact.fisher_exact' method")
print(f"the 5 smallest p-values of biological processes associated with the input protein list is:")
print(dict(map(lambda y: (y[0],y[1][1]), sorted(fisher_res_dict.items(), key=lambda x: x[1][1])[:5])))

print("Manual computation:")
total_number_of_input_connected_to_GO_0019221 = 19
print(f"Total edges of input connected to GO:0019221: {total_number_of_input_connected_to_GO_0019221}")
total_number_of_input_connected_to_GO_0051092 = 13
print(f"Total edges of input connected to GO:0051092: {total_number_of_input_connected_to_GO_0051092}")
total_number_of_input_connected_to_GO_0010628 = 16
print(f"Total edges of input connected to GO:0010628: {total_number_of_input_connected_to_GO_0010628}")
total_number_of_input_connected_to_GO_0007568 = 12
print(f"Total edges of input connected to GO:0007568: {total_number_of_input_connected_to_GO_0007568}")
total_number_of_input_connected_to_GO_0070374 = 13
print(f"Total edges of input connected to GO:0070374: {total_number_of_input_connected_to_GO_0070374}")

total_number_of_protein_connected_to_GO_0019221 = 317
print(f"Total edges of protein connected to GO:0019221: {total_number_of_protein_connected_to_GO_0019221}")
total_number_of_protein_connected_to_GO_0051092 = 146
print(f"Total edges of protein connected to GO:0051092: {total_number_of_protein_connected_to_GO_0051092}")
total_number_of_protein_connected_to_GO_0010628 = 301
print(f"Total edges of protein connected to GO:0010628: {total_number_of_protein_connected_to_GO_0010628}")
total_number_of_protein_connected_to_GO_0007568 = 163
print(f"Total edges of protein connected to GO:0007568: {total_number_of_protein_connected_to_GO_0007568}")
total_number_of_protein_connected_to_GO_0070374 = 230
print(f"Total edges of protein connected to GO:0070374: {total_number_of_protein_connected_to_GO_0070374}")
total_number_of_protein_in_sample = len(input_id_list)
print(f"Total number of protein in sample is {total_number_of_protein_in_sample}")
total_number_of_protein = 20514
print(f"Total number of protein in KG1 is {total_number_of_protein}")

print(f"The p-values calculated based on different methods of constructing contingency table for each biological process:")
print(f"--GO:0019221")
_, pvalue=stats.fisher_exact([[19,317-19],[79-19,(20514-317)-(79-19)]])
print(f"The p-value calculated based on 'stats.fisher_exact([[19,317-19],[79-19,(20514-317)-(79-19)]])' is {pvalue}")
_, pvalue=stats.fisher_exact([[19,317],[79-19,20514-317]])
print(f"The p-value calculated based on 'stats.fisher_exact([[19,317],[79-19,20514-317]])' is {pvalue}")
print(f"--GO:0051092")
_, pvalue=stats.fisher_exact([[13,146-13],[79-13,(20514-146)-(79-13)]])
print(f"The p-value calculated based on 'stats.fisher_exact([[13,146-13],[79-13,(20514-146)-(79-13)]])' is {pvalue}")
_, pvalue=stats.fisher_exact([[13,146],[79-13,20514-146]])
print(f"The p-value calculated based on 'stats.fisher_exact([[13,146],[79-13,20514-146]])' is {pvalue}")
print(f"--GO:0010628")
_, pvalue=stats.fisher_exact([[16,301-16],[79-16,(20514-301)-(79-16)]])
print(f"The p-value calculated based on 'stats.fisher_exact([[16,301-16],[79-16,(20514-301)-(79-16)]])' is {pvalue}")
_, pvalue=stats.fisher_exact([[16,301],[79-16,20514-301]])
print(f"The p-value calculated based on 'stats.fisher_exact([[16,301],[79-16,20514-301]])' is {pvalue}")
print(f"--GO:0007568")
_, pvalue=stats.fisher_exact([[12,163-12],[79-12,(20514-163)-(79-12)]])
print(f"The p-value calculated based on 'stats.fisher_exact([[12,163-12],[79-12,(20514-163)-(79-12)]])' is {pvalue}")
_, pvalue=stats.fisher_exact([[12,163],[79-12,20514-163]])
print(f"The p-value calculated based on 'stats.fisher_exact([[12,163],[79-12,20514-163]])' is {pvalue}")
print(f"--GO:0070374")
_, pvalue=stats.fisher_exact([[13,230-13],[79-13,(20514-230)-(79-13)]])
print(f"The p-value calculated based on 'stats.fisher_exact([[13,230-13],[79-13,(20514-230)-(79-13)]])' is {pvalue}")
_, pvalue=stats.fisher_exact([[13,230],[79-13,20514-230]])
print(f"The p-value calculated based on 'stats.fisher_exact([[13,230],[79-13,20514-230]])' is {pvalue}")

response = Response()
actions_parser = ActionsParser()
actions_list = [
    "overlay(action=fisher_exact_test,virtual_edge_type=FET1,query_node_id=n02,adjacent_node_type=biological_process,top_n=5,added_flag=FalSE)"
]
result = actions_parser.parse(actions_list)
actions = result.data['actions']
parameter=actions[0]['parameters']
FTEST = ComputeFTEST(response, message, parameter)
response = FTEST.fisher_exact_test()
print(response.status)
pvalue_dict = dict()
for edge in message.knowledge_graph.edges:
    if edge.type == 'virtual_edge':
        if edge.target_id not in pvalue_dict:
            pvalue_dict[edge.target_id] = getattr(edge.edge_attributes[0],"value")
        else:
            continue

print("Below is the FET result of Overlay FET option")
print(f"the 5 smallest p-values of biological processes associated with the input protein list is:")
print(dict(sorted(pvalue_dict.items(), key=lambda x: x[1])))




#input_id_list = ["DOID:8398", "DOID:3222"]  # input
#input_nodes_label = "disease"  # node labels/types of the input_id_list (NOTE: bad programming style here as I could have just dynamically checked this instead of making it a required input)
#output_node_label = "phenotypic_feature"  # the thing you want FET to spit out
####################
# Using ReasoningUtilities
# gives 10 smallest p-values of phenotypic_features associated with the input diseases
#(p_value_dict, phenotype_curies) = RU.top_n_fisher_exact(input_id_list, input_nodes_label, output_node_label, rel_type=None, n=10, curie_prefix=None, on_path=None, exclude=None)

#####################
# Using fisher_exact.py
#fisher_res_dict = fisher_exact.fisher_exact(input_id_list, input_nodes_label, output_node_label)
# fisher_res_dict contains all the odds ratios and p-values for all nodes of type `output_node_label` connected to anything in `input_id_list`

# Get the associated cypher commands
#print(fisher_exact.fisher_exact(input_id_list, input_nodes_label, output_node_label, debug=True))
# results in:
# with ["DOID:8398","DOID:3222"] as inlist match (d:phenotypic_feature)-[]-(s:disease) where s.id in inlist return d.id as ident, count(*) as ct
# this command computes: for each phenotypic_feature, count the number of edges connected to diseases in `input_id_list`, only return those (and their counts) that connect to anything in `input_id_list`

# with ["DOID:8398","DOID:3222"] as inlist match (d:phenotypic_feature)-[]-(s:disease) where s.id in inlist with distinct d as d match (d)-[]-(:disease) return d.id as ident, count(*) as ct
# this command computes: for each phenotypic_feature connected to diseases in `input_id_list`, count the total number of diseases they connect to

# MATCH (n:disease) return count(distinct n)
# this command counts all the diseases in the KG1


# then head over to KG1: http://arax.rtx.ai:7474/browser/ , and you can run these commands to see them in action





