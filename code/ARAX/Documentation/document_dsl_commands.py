import sys
import os
import importlib
from tomark import Tomark
import re
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../ARAXQuery")
modules = ["ARAX_overlay", "ARAX_filter_kg"]
classes = ["ARAXOverlay", "ARAXFilterKG"]
modules_to_command_name = {'ARAX_overlay': '`overlay()`', 'ARAX_filter_kg': '`filter_kg()`'}
to_print = ""
header_info = """
- [Domain Specific Langauage (DSL) description](#domain-specific-langauage--dsl--description)
- [Full documentation of current DSL commands](#full-documentation-of-current-dsl-commands)
  * [ARAX_overlay](#arax-overlay)
    + [`overlay(action=add_node_pmids)`](#-overlay-action-add-node-pmids--)
    + [`overlay(action=compute_ngd)`](#-overlay-action-compute-ngd--)
    + [`overlay(action=overlay_clinical_info)`](#-overlay-action-overlay-clinical-info--)
    + [`overlay(action=compute_jaccard)`](#-overlay-action-compute-jaccard--)
  * [ARAX_filter_kg](#arax-filter-kg)
    + [`filter_kg(action=remove_edges_by_attribute)`](#-filter-kg-action-remove-edges-by-attribute--)
    + [`filter_kg(action=remove_edges_by_type)`](#-filter-kg-action-remove-edges-by-type--)
    + [`filter_kg(action=remove_edges_by_property)`](#-filter-kg-action-remove-edges-by-property--)
    + [`filter_kg(action=remove_nodes_by_type)`](#-filter-kg-action-remove-nodes-by-type--)


# Domain Specific Langauage (DSL) description
This document describes the features and components of the DSL developed for the ARA Expander team.

Full documentation is given below, but an example can help: in the API specification, there is field called `Query.previous_message_processing_plan.processing_actions:`,
while initially an empty list, a set of processing actions can be applied with something along the lines of:

```
[
"add_qnode(name=hypertension, id=n00)",  # add a new node to the query graph
"add_qnode(type=protein, is_set=True, id=n01)",  # add a new set of nodes of a certain type to the query graph
"add_qedge(source_id=n01, target_id=n00, id=e00)",  # add an edge connecting these two nodes
"expand(edge_id=e00)",  # reach out to knowledge providers to find all subgraphs that satisfy these new query nodes/edges
"overlay(action=compute_ngd)",  # overlay each edge with the normalized Google distance (a metric based on Edge.source_id and Edge.target_id co-occurrence frequency in all PubMed abstracts)
"filter_kg(action=remove_edges_by_attribute, edge_attribute=ngd, direction=above, threshold=0.85, remove_connected_nodes=t, qnode_id=n01)",  # remove all edges with normalized google distance above 0.85 as well as the connected protein
"return(message=true, store=false)"  # return the message to the ARS
]
```
 
# Full documentation of current DSL commands
"""
to_print += header_info
#for (module, cls) in zip(modules, classes):
#    m = importlib.import_module(module)
#    #print(getattr(m, cls)().describe_me())
#    dsl_name = modules_to_command_name[module]
#    to_print += f"# {module}\n"
#    to_print += f"|{dsl_name} DSL commands\n"
#    for dic in getattr(m, cls)().describe_me():
#        #to_print += Tomark.table([dic])
#        #to_print += "\n"
#        temp_table = Tomark.table([dic])
#        temp_table_split = temp_table.split("\n")
#        better_table = f"|{dsl_name} DSL commands" + ('|' * temp_table_split[0].count('|')) + '\n'
#        better_table += temp_table_split[1] + '-----|\n'
#        better_table += '|**DSL parameters**' + temp_table_split[0] + "\n"
#        better_table += '|**DSL arguments**' + temp_table_split[2] + "\n"
#        to_print += better_table + '\n'

for (module, cls) in zip(modules, classes):
    m = importlib.import_module(module)
    dsl_name = modules_to_command_name[module]
    to_print += f"## {module}\n"
    for dic in getattr(m, cls)().describe_me():
        action = dic['action'].pop()
        del dic['action']
        to_print += '### ' + re.sub('\(\)',f'(action={action})', dsl_name) + '\n'
        if 'brief_description' in dic:
            to_print += dic['brief_description'] + '\n\n'
            del dic['brief_description']
        temp_table = Tomark.table([dic])
        temp_table_split = temp_table.split("\n")
        #better_table = "|"+re.sub('\(\)',f'(action={action})', dsl_name) + ('|' * temp_table_split[0].count('|')) + '\n'
        better_table = ('|' * (temp_table_split[0].count('|')+1)) + '\n'
        better_table += temp_table_split[1] + '-----|\n'
        better_table += '|_DSL parameters_' + temp_table_split[0] + "\n"
        better_table += '|_DSL arguments_' + temp_table_split[2] + "\n"
        to_print += better_table + '\n'

fid = open('DSL_Documentation.md', 'w')
fid.write(to_print)
fid.close()
