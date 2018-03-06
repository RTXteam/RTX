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
	 		'desc': RU.get_node_property(target, "description", node_label=target_label),
			 'prob': 1})  # All these are known to be true
	return results_list

#########################################################
# Tests
def test_one_hop_relationship_type():
	res = one_hop_relationship_type("carbetocin", "uniprot_protein", "targets")
	assert res == [{'desc': 'OXTR', 'name': 'P30559', 'type': 'node','prob': 1}]
	res = one_hop_relationship_type("OMIM:263200", "uniprot_protein", "disease_affects")
	known_res = [{'desc': 'PKHD1', 'name': 'P08F94', 'type': 'node','prob': 1}, {'desc': 'DZIP1L', 'name': 'Q8IYY4', 'type': 'node','prob': 1}]
	for item in res:
		assert item in known_res
	for item in known_res:
		assert item in res
	res = one_hop_relationship_type("OMIM:263200", "ncbigene_microrna", "gene_assoc_with")
	assert res == [{'desc': 'MIR1225', 'name': 'NCBIGene:100188847', 'type': 'node','prob': 1}]


def test_suite():
	test_one_hop_relationship_type()