import sys
pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")
dbpath = os.path.sep.join([*pathlist[:(RTXindex+1)],'code','reasoningtool','QuestionAnswering'])
sys.path.append(dbpath)

import ReasoningUtilities as RU  # Note: this is using KG1
import fisher_exact


input_id_list = ["DOID:8398", "DOID:3222"]  # input
input_nodes_label = "disease"  # node labels/types of the input_id_list (NOTE: bad programming style here as I could have just dynamically checked this instead of making it a required input)
output_node_label = "phenotypic_feature"  # the thing you want FET to spit out
####################
# Using ReasoningUtilities
# gives 10 smallest p-values of phenotypic_features associated with the input diseases
(p_value_dict, phenotype_curies) = RU.top_n_fisher_exact(input_id_list, input_nodes_label, output_node_label, rel_type=None, n=10, curie_prefix=None, on_path=None, exclude=None)

#####################
# Using fisher_exact.py
fisher_res_dict = fisher_exact.fisher_exact(input_id_list, input_nodes_label, output_node_label)
# fisher_res_dict contains all the odds ratios and p-values for all nodes of type `output_node_label` connected to anything in `input_id_list`

# Get the associated cypher commands
print(fisher_exact.fisher_exact(input_id_list, input_nodes_label, output_node_label, debug=True))
# results in:
# with ["DOID:8398","DOID:3222"] as inlist match (d:phenotypic_feature)-[]-(s:disease) where s.id in inlist return d.id as ident, count(*) as ct
# this command computes: for each phenotypic_feature, count the number of edges connected to diseases in `input_id_list`, only return those (and their counts) that connect to anything in `input_id_list`

# with ["DOID:8398","DOID:3222"] as inlist match (d:phenotypic_feature)-[]-(s:disease) where s.id in inlist with distinct d as d match (d)-[]-(:disease) return d.id as ident, count(*) as ct
# this command computes: for each phenotypic_feature connected to diseases in `input_id_list`, count the total number of diseases they connect to

# MATCH (n:disease) return count(distinct n)
# this command counts all the diseases in the KG1


# then head over to KG1: http://arax.rtx.ai:7474/browser/ , and you can run these commands to see them in action





