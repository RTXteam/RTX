# This will be a collection of scripts that can answer various questions
# Start out with easy ones
import ReasoningUtilities as RU

# eg: what proteins does drug X target?
def one_hop_relationship_type(source_name, target_label, relationship_type):
	source_label = RU.get_node_property(source_name, "label")
	targets = RU.get_one_hop_target(source_label, source_name, target_label, relationship_type)
	results_list = list()
	for target in targets:
		results_list.append(
			{'type': 'node',
	 		'name': target,
	 		'desc': RU.get_node_property(target, "description", node_label=target_label)})
	return results_list

#########################################################
# Tests
def test_one_hop_relationship_type():
	res = one_hop_relationship_type("carbetocin", "uniprot_protein", "targets")
	assert res == [{'desc': 'OXTR', 'name': 'P30559', 'type': 'node'}]