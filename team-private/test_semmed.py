from SemMedInterface import SemMedInterface
import pandas

# The value entered on initialization dictates the timeout (seconds) on large mysql queries
# This defaults to 30
smi = SemMedInterface(20)

######################
# get_edges_for_node #
######################

print('default get_edges_for_node:')
print(smi.get_edges_for_node("ChEMBL:154", "naproxen"),'\n----------\n')

print('predicate = TREATS get_edges_for_node:')
print(smi.get_edges_for_node("ChEMBL:154", "naproxen", predicate = 'TREATS'),'\n----------\n')

############################################
# get_shortest_path_between_subject_object #
############################################

# This finds the shortest path between two nodes and then returns that path
print('get_shortest_path_between_subject_object:')
print(smi.get_shortest_path_between_subject_object("ChEMBL:154", "naproxen", "DOID:8398", "osteoarthritis", max_length = 2), '\n----------\n')
# The max_length value is 3 by default so it will return None if No path is found at that length

###########################
# get_edges_between_nodes #
###########################

# This function finds all edges between 2 nodes
print('default get_edges_between_nodes:')
print(smi.get_edges_between_nodes("ChEMBL:154", "naproxen", "DOID:8398", "osteoarthritis"), '\n----------\n')

# If set to false it can be a directional relationship i.e. naproxen is the subject and osteoarthritis is the object
print('Not bidirectional get_edges_between_nodes:')
print(smi.get_edges_between_nodes("ChEMBL:154", "naproxen", "DOID:8398", "osteoarthritis", bidirectional = False), '\n----------\n')

# You can also restrict the predicate that gets returned
print('predicate = TREATS get_edges_between_nodes:')
print(smi.get_edges_between_nodes("ChEMBL:154", "naproxen", "DOID:8398", "osteoarthritis", predicate = "TREATS"), '\n----------\n')

# You can also add more columns to be returned. The possible options are 'PMID', 'PREDICATE', 'SUBJECT__CUI', 'SUBJECT_NAME', 'SUBJECT_SEMTYPE', 'OBJECT__CUI', 'OBJECT_NAME', and 'OBJECT_SEMTYPE'
print('extra result columns get_edges_between_nodes:')
print(smi.get_edges_between_nodes("ChEMBL:154", "naproxen", "DOID:8398", "osteoarthritis", result_col = ['PMID', 'SUBJECT_NAME', 'SUBJECT_CUI', 'PREDICATE', 'OBJECT_NAME', 'OBJECT_CUI']), '\n----------\n')

# Note that this returns distinct results so if we remove the PMID result column we get much fewer rows. 
print('fewer columns get_edges_between_nodes:')
print(smi.get_edges_between_nodes("ChEMBL:154", "naproxen", "DOID:8398", "osteoarthritis", result_col = ['SUBJECT_NAME', 'PREDICATE', 'OBJECT_NAME']), '\n----------\n')

###############################################
# get_edges_between_subject_object_with_pivot #
###############################################

# This is really only if you want to specify a specific number of hops instead of finding the shortest path
print('default get_edges_between_subject_object_with_pivot:')
print(smi.get_edges_between_subject_object_with_pivot("ChEMBL:154", "naproxen", "DOID:8398", "osteoarthritis", 1), '\n----------\n')


