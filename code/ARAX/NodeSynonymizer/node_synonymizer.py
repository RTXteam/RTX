#!/usr/bin/env python3
#
# Class to build and query an index of nodes in the KG
#
import os
import sys
import re
import timeit
import argparse
import sqlite3
import json
import pickle
import platform
def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

#sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../")
#sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../QuestionAnswering")

#import ReasoningUtilities as RU
#from RTXConfiguration import RTXConfiguration

from sri_node_normalizer import SriNodeNormalizer

# Testing and debugging flags
DEBUG = False
TESTSUFFIX = ''
#TESTSUFFIX = '_test2'

def sizeof(obj):
    size = sys.getsizeof(obj)
    if isinstance(obj, dict): return size + sum(map(sizeof, obj.keys())) + sum(map(sizeof, obj.values()))
    if isinstance(obj, (list, tuple, set, frozenset)): return size + sum(map(sizeof, obj))
    return size


# ################################################################################################
# Main class
class NodeSynonymizer:

    # Constructor
    def __init__(self):

        self.databaseLocation = os.path.dirname(os.path.abspath(__file__))
        self.options = {}
        self.kg_map = {
            'kg_nodes': {},
            'kg_unique_concepts': {},
            'kg_curies': {},
            'kg_synonyms': {}
        }
        self.normalizer = None

        self.databaseName = "node_synonymizer.sqlite"
        self.engine_type = "sqlite"

        self.connection = None
        self.connect()


    # ############################################################################################
    # Create and store a database connection
    def connect(self):

        # If already connected, don't need to do it again
        if self.connection is not None:
            return

        # Create an engine object
        if DEBUG is True:
            print("INFO: Connecting to database")

        self.connection = sqlite3.connect(f"{self.databaseLocation}/{self.databaseName}")


    # ############################################################################################
    # Destroy the database connection
    def disconnect(self):

        if self.connection is None:
            if DEBUG is True:
                print("INFO: Skip disconnecting from database")
            return

        if DEBUG is True:
            print("INFO: Disconnecting from database")

        self.connection.close()
        self.connection = None


    # ############################################################################################
    # Delete and create the kgnode table
    def create_tables(self):

        kg_name = self.options['kg_name']
        if kg_name == 'KG1' or kg_name == 'KG2':
            kg_prefix = kg_name.lower()
        else:
            print("ERROR: kg_name must be either 'KG1' or 'KG2'")
            sys.exit(5)

        print(f"INFO: Dropping and recreating {kg_name} tables in database {self.databaseName}")

        self.connection.execute(f"DROP TABLE IF EXISTS {kg_prefix}_node{TESTSUFFIX}")
        self.connection.execute(f"CREATE TABLE {kg_prefix}_node{TESTSUFFIX}( uc_curie VARCHAR(255), curie VARCHAR(255), original_name VARCHAR(255), adjusted_name VARCHAR(255), type VARCHAR(255), unique_concept_curie VARCHAR(255), kg_presence VARCHAR(10) )" )

        self.connection.execute(f"DROP TABLE IF EXISTS {kg_prefix}_unique_concept{TESTSUFFIX}")
        self.connection.execute(f"CREATE TABLE {kg_prefix}_unique_concept{TESTSUFFIX}( uc_curie VARCHAR(255), curie VARCHAR(255), remapped_curie VARCHAR(255), kg1_best_curie VARCHAR(255), kg2_best_curie VARCHAR(255), name VARCHAR(255), type VARCHAR(255), normalizer_curie VARCHAR(255), normalizer_name VARCHAR(255), normalizer_type VARCHAR(255) )" )

        self.connection.execute(f"DROP TABLE IF EXISTS {kg_prefix}_curie{TESTSUFFIX}")
        self.connection.execute(f"CREATE TABLE {kg_prefix}_curie{TESTSUFFIX}( uc_curie VARCHAR(255), curie VARCHAR(255), unique_concept_curie VARCHAR(255), type VARCHAR(255), source VARCHAR(255) )" )

        self.connection.execute(f"DROP TABLE IF EXISTS {kg_prefix}_synonym{TESTSUFFIX}")
        self.connection.execute(f"CREATE TABLE {kg_prefix}_synonym{TESTSUFFIX}( lc_name VARCHAR(255), name VARCHAR(255), unique_concept_curie VARCHAR(255), source VARCHAR(255) )" )

        # This table should persist for a while, although eventually purged in case there's more data
        #try:
            #self.connection.execute(f"DROP TABLE IF EXISTS sri_nodata")
        #    self.connection.execute(f"CREATE TABLE sri_nodata ( curie VARCHAR(255) )" )
        #except:
        #    print("WARNING: Preserving existing sri_nodata table. This complements the requests cache to record 404s, so they won't be tried again. But if you purged the sri_normalizer requests cache, you should purge this table as well, and then rebuild.")


    # ############################################################################################
    # Create the KG node table
    def build_kg_map(self):

        kg_name = self.options['kg_name']
        kg_prefix = kg_name.lower()

        suffix = '.tsv'
        #suffix = '_TEST1.txt'

        filename = os.path.dirname(os.path.abspath(__file__)) + f"/../../../data/KGmetadata/NodeNamesDescriptions_{kg_name}{suffix}"
        filesize = os.path.getsize(filename)

        # Set up the SriNormalizer
        if self.normalizer is not None:
            normalizer = self.normalizer
        else:
            normalizer = SriNodeNormalizer()
            normalizer.load_cache()
            self.normalizer = normalizer

        normalizer_supported_types = normalizer.get_supported_types()
        if normalizer_supported_types is None:
            return
        normalizer_supported_prefixes = normalizer.get_supported_prefixes()
        if normalizer_supported_prefixes is None:
            return

        # The SRI NodeNormalizer conflates genes and proteins, so have a special lookup table to try to disambiguate them
        curie_prefix_types = {
            'NCBIGene:': 'gene',
            'ENSEMBL:ENSG': 'gene',
            'HGNC:': 'gene',
            'UniProtKB:': 'protein',
        }

        # Open the file and organize all the data
        fh = open(filename, 'r', encoding="latin-1", errors="replace")
        print(f"INFO: Reading {filename} to create the NodeSynonymizer")
        lineCounter = 0
        previous_percentage = -1
        bytes_read = 0

        # Create dicts to hold all the information
        kg_nodes = self.kg_map['kg_nodes']
        kg_unique_concepts = self.kg_map['kg_unique_concepts']
        kg_curies = self.kg_map['kg_curies']
        kg_synonyms = self.kg_map['kg_synonyms']

        # Correction for Windows line endings
        extra_bytes = 0
        if platform.system() == 'Windows':
            extra_bytes = 1

        # Loop over each line in the file
        for line in fh:
            bytes_read += len(line) + extra_bytes
            match = re.match(r'^\s*$',line)
            if match:
                continue
            columns = line.strip().split("\t")
            node_curie = columns[0]
            uc_node_curie = node_curie.upper()
            node_name = columns[1]
            node_type = columns[2]
            original_node_name = node_name

            #### For debugging problems
            debug_flag = False
            #if 'HGNC:29603' in node_curie: debug_flag = True

            if debug_flag:
                print("===============================================")
                print(f"Input: {line.strip()}")

            # Perform some data scrubbing
            scrubbed_values = self.scrub_input(node_curie, node_name, node_type, debug_flag)
            node_curie = scrubbed_values['node_curie']
            uc_node_curie = node_curie.upper()
            node_name = scrubbed_values['node_name']
            node_type = scrubbed_values['node_type']
            names = scrubbed_values['names']
            curie_prefix = node_curie.split(':')[0]
            if debug_flag:
                print(f"Final name list: ",names)

            # See if this curie is already a curie we've encountered before, figure out its unique_concept_curie
            unique_concept_curie = None
            equivalence = None
            if uc_node_curie in kg_curies:
                unique_concept_curie = kg_curies[uc_node_curie]['curie']
                uc_unique_concept_curie = kg_curies[uc_node_curie]['uc_unique_concept_curie']
                if debug_flag:
                    print(f"DEBUG: This curie was already seen. Setting to its uc_unique_concept_curie to {uc_unique_concept_curie}")

            # Otherwise look this curie up in the SRI Node Normalizer
            else:

                # Check to see if this is a supported prefix or in the translation table
                if curie_prefix in normalizer.curie_prefix_tx_arax2sri or curie_prefix in normalizer_supported_prefixes:
                    t0 = timeit.default_timer()
                    equivalence = normalizer.get_curie_equivalence(node_curie, cache_only=True)
                    t1 = timeit.default_timer()
                    if t1 - t0 > 0.1:
                        print(f"\n  PROGRESS: Took {str(t1-t0)} to retrieve SRI data for {node_curie}")
                    if debug_flag:
                        print("DEBUG: SRI normalizer returned: ", json.dumps(equivalence, indent=2, sort_keys=True))

                    # Extract the preferred designation of the normalizer
                    normalizer_curie = equivalence['preferred_curie']
                    normalizer_name = equivalence['preferred_curie_name']
                    normalizer_type = equivalence['type']

                # Else just warn that there's nothing to look for
                else:
                    if debug_flag:
                        print(f"WARNING: CURIE prefix '{curie_prefix}' not supported by normalizer. Skipped.")
                    equivalence = { 'status': 'type not supported', 'equivalent_identifiers': [], 'equivalent_names': [] }
                    normalizer_curie = ''
                    normalizer_name = ''
                    normalizer_type = ''

                # If the normalizer has something for us, then use that as the unique_concept_curie
                overridden_normalizer_type = normalizer_type
                if equivalence['status'] == 'OK':

                    # Unless the normalizer type is a gene and the current type is a protein. Then keep it a protein because proteins are the real machines
                    if normalizer_type == 'gene' and node_type == 'protein':
                        if debug_flag:
                            print(f"DEBUG: Since this is protein and the normalizer says gene, stay with this one as the unique_concept {node_curie}")
                        unique_concept_curie = node_curie
                        uc_unique_concept_curie = node_curie.upper()
                        overridden_normalizer_type = node_type
                    else:
                        if debug_flag:
                            print(f"DEBUG: Using the SRI normalizer normalized unique_concept {normalizer_curie}")
                        unique_concept_curie = normalizer_curie
                        uc_unique_concept_curie = normalizer_curie.upper()

                # And if the normalizer did not have anything for us
                else:

                    # If we've already seen this synonym, then switch to that unique concept
                    # I hope this will save RAM by not creating so many unique concepts that must be coalesced later
                    if node_name.lower() in kg_synonyms:
                        uc_unique_concept_curie = kg_synonyms[node_name.lower()]['uc_unique_concept_curie']
                        unique_concept_curie = kg_unique_concepts[uc_unique_concept_curie]['curie']
                        if debug_flag:
                            print(f"DEBUG: Found an existing unique concept by synonym as {unique_concept_curie}")

                    # Else this node becomes the unique_concept_curie
                    else:
                        if debug_flag:
                            print(f"DEBUG: This node will become its own unique concept")
                        unique_concept_curie = node_curie
                        uc_unique_concept_curie = node_curie.upper()

                # Place this curie in the index
                kg_curies[uc_node_curie] = { 
                    'curie': node_curie,
                    'uc_unique_concept_curie': uc_unique_concept_curie,
                    'type': node_type,
                    'source': kg_name,
                }

                # If this unique_concept_curie already exists, embrace it
                if uc_unique_concept_curie in kg_unique_concepts:
                    # Put the current curie in there. Names will be done below.
                    kg_unique_concepts[uc_unique_concept_curie]['all_uc_curies'][uc_node_curie] = 1

                # Otherwise, create the entry
                else:

                    # If we got something from the SRI normalizer, start with that
                    if equivalence['status'] == 'OK':
                        if debug_flag:
                            print(f"DEBUG: Create new unique concept based on SRI normalizer info")
                        kg_unique_concepts[uc_unique_concept_curie] = {
                            'curie': unique_concept_curie,
                            'remapped_curie': None,
                            'kg1_best_curie': None,
                            'kg2_best_curie': None,
                            'name': normalizer_name,
                            'type': overridden_normalizer_type,
                            'normalizer_curie': normalizer_curie,
                            'normalizer_name': normalizer_name,
                            'normalizer_type': normalizer_type,
                            'normalizer_type_list': None,                # FIXME
                            'all_uc_curies': { uc_node_curie: 1 },          # FIXME
                            'all_lc_names': { node_name.lower(): 1 }
                        }

                    # Otherwise, we use this node
                    else:
                        if debug_flag:
                            print(f"DEBUG: Create new unique concept based on this node")
                        kg_unique_concepts[uc_unique_concept_curie] = {
                            'curie': unique_concept_curie,
                            'remapped_curie': None,
                            'kg1_best_curie': None,
                            'kg2_best_curie': None,
                            'name': node_name,
                            'type': node_type,
                            'normalizer_curie': None,
                            'normalizer_name': None,
                            'normalizer_type': None,
                            'normalizer_type_list': None,                # FIXME
                            'all_uc_curies': { uc_node_curie: 1 },          # FIXME
                            'all_lc_names': { node_name.lower(): 1 }
                        }

                # Loop through the equivalent identifiers from the SRI normalizer and add those to the list
                for equivalent_identifier in equivalence['equivalent_identifiers']:

                    # Try to deconflate gene and protein
                    this_type = normalizer_type
                    if this_type == '':
                        this_type = node_type
                    for curie_prefix_type in curie_prefix_types:
                        if equivalent_identifier.startswith(curie_prefix_type):
                            this_type = curie_prefix_types[curie_prefix_type]
                    uc_equivalent_identifier = equivalent_identifier.upper()

                    # If this equivalient identifier is already there, just make sure the unique_concept_curie is the same
                    if uc_equivalent_identifier in kg_curies:
                        pass

                        # Turns out this is not always true as one would have expected. One example is HSFX1 and HSFX2 with
                        # NCBIGene:100130086 and NCBIGene:100506164 but yet they are tied by one protein UniProtKB:Q9UBD0
                        # This system will coalesce them, although the normalizer has them separate
                        if 0 and uc_unique_concept_curie != kg_curies[uc_equivalent_identifier]['uc_unique_concept_curie']:
                            print(f"ERROR 247: at node_curie={node_curie}, expected {uc_unique_concept_curie} == {kg_curies[uc_equivalent_identifier]['uc_unique_concept_curie']}, but no.")
                            if debug_flag:
                                print(f"kg_curies[{uc_equivalent_identifier}] = " + json.dumps(kg_curies[uc_equivalent_identifier], indent=2, sort_keys=True))
                                print(f"kg_unique_concepts[{uc_equivalent_identifier}] = " + json.dumps(kg_unique_concepts[uc_equivalent_identifier], indent=2, sort_keys=True))
                                sys.exit(1)

                    # If not, then create it
                    else:
                        kg_curies[uc_equivalent_identifier] = { 'curie': equivalent_identifier, 'uc_unique_concept_curie': uc_unique_concept_curie, 'type': this_type, 'source': 'SRI' }
                        kg_unique_concepts[uc_unique_concept_curie]['all_uc_curies'][uc_equivalent_identifier] = 1               # FIXME. A count would be fun

                # Loop through the equivalent names from the SRI normalizer and add those to the list
                for equivalent_name in equivalence['equivalent_names']:

                    # If this equivalent name is already there, just make sure the unique_concept_curie is the same
                    lc_equivalent_name = equivalent_name.lower()
                    if lc_equivalent_name in kg_synonyms:
                        #print(f"INFO: Adding {unique_concept_curie} to synonym {lc_equivalent_name}")
                        kg_synonyms[lc_equivalent_name]['uc_unique_concept_curies'][uc_unique_concept_curie] = 1
                    # If not, then create it
                    else:
                        kg_synonyms[lc_equivalent_name] = {
                            'name': equivalent_name,
                            'uc_unique_concept_curie': uc_unique_concept_curie,
                            'source': 'SRI',
                            'uc_unique_concept_curies': { uc_unique_concept_curie: 1 }
                        }
                        kg_unique_concepts[uc_unique_concept_curie]['all_lc_names'][lc_equivalent_name] = 1               # FIXME. A count would be fun


            # If there is already a kg_nodes entry for this curie, then assume this is a synonym
            if uc_node_curie in kg_nodes:
                uc_unique_concept_curie = kg_nodes[uc_node_curie]['uc_unique_concept_curie']

                # For now, just ignore cases where the types are different. It happens alot
                #if node_type != kg_nodes[uc_node_curie]['type']:
                #    print(f"ERROR 249: at node_curie={node_curie}, expected {node_type} == {kg_nodes[uc_node_curie]['type']}, but no.")

                # Update the KG presence. If the current value is not the current KG, then it much be both
                if kg_nodes[uc_node_curie]['kg_presence'] != kg_name:
                    kg_nodes[uc_node_curie]['kg_presence'] = 'KG1,KG2'

            # Otherwise, create the entry
            else:
                kg_nodes[uc_node_curie] = {
                    'curie': node_curie,
                    'original_name': original_node_name,
                    'adjusted_name': node_name,     # do better later? FIXME
                    'type': node_type,
                    'uc_unique_concept_curie': uc_unique_concept_curie,
                    'kg_presence': kg_name
                }

            # Loop over all scrubbed names for this node to insert synonyms
            for equivalent_name in names:
                lc_equivalent_name = equivalent_name.lower()

                # If this equivalent name is already there, just make sure the unique_concept_curie is the same
                if lc_equivalent_name in kg_synonyms:
                    if debug_flag:
                        print(f"DEBUG: Name '{lc_equivalent_name}' already in synonyms")
                    if uc_unique_concept_curie != kg_synonyms[lc_equivalent_name]['uc_unique_concept_curie']:
                        kg_synonyms[lc_equivalent_name]['uc_unique_concept_curies'][uc_unique_concept_curie] = 1
                        if debug_flag:
                            print(f"INFO: uc_unique_concept_curie={uc_unique_concept_curie}, but kg_synonym already has {kg_synonyms[lc_equivalent_name]['uc_unique_concept_curie']}. Oh well, this will be cleaned up later.")
                            print(f"INFO: * Adding {uc_unique_concept_curie} to synonym {lc_equivalent_name}")
                            print(f"INFO: **** {lc_equivalent_name} has {kg_synonyms[lc_equivalent_name]['uc_unique_concept_curies']}")

                # If not, then create it
                else:
                    if debug_flag:
                        print(f"DEBUG: Name '{lc_equivalent_name}' is not in synonyms. Add it")
                        print(f"       node_curie={node_curie}, uc_node_curie={uc_node_curie}, uc_unique_concept_curie={uc_unique_concept_curie}, lc_equivalent_name={lc_equivalent_name}")
                    kg_synonyms[lc_equivalent_name] = {
                        'name': equivalent_name,
                        'uc_unique_concept_curie': uc_unique_concept_curie,
                        'source': kg_name,
                        'uc_unique_concept_curies': { uc_unique_concept_curie: 1 }
                    }
                    kg_unique_concepts[uc_unique_concept_curie]['all_lc_names'][lc_equivalent_name] = 1               # FIXME. A count would be fun

            # Debugging
            if debug_flag:
                print(f"kg_nodes['{uc_node_curie}'] = ",json.dumps(kg_nodes[uc_node_curie], indent=2, sort_keys=True))
                print(f"kg_unique_concepts['{uc_unique_concept_curie}'] = ",json.dumps(kg_unique_concepts[uc_unique_concept_curie], indent=2, sort_keys=True))
                input("Enter to continue...")

            debug_flag = False
            lineCounter += 1
            percentage = int(bytes_read*100.0/filesize)
            if percentage > previous_percentage:
                previous_percentage = percentage
                print(str(percentage)+"%..", end='', flush=True)
                #print(f"Sizes: kg_nodes={int(sizeof(kg_nodes)/1024.0/1024)}, kg_unique_concepts={int(sizeof(kg_unique_concepts)/1024.0/1024)}, kg_curies={int(sizeof(kg_curies)/1024.0/1024)}, kg_synonyms={int(sizeof(kg_synonyms)/1024.0/1024)}")

        fh.close()
        print("")

        print(f"INFO: Reading of {self.options['kg_name']} node files complete")


    # ############################################################################################
    def save_state(self):

        kg_name = self.options['kg_name']
        kg_prefix = kg_name.lower()
        filename = f"node_synonymizer.{kg_name}_map_state.pickle"
        print(f"INFO: Writing the state to {filename}")

        try:
            with open(filename, "wb") as outfile:
                pickle.dump(self.kg_map, outfile)
            return True
        except:
            print(f"ERROR: Unable to save state to {filename}")
            return None


    # ############################################################################################
    def reload_state(self):

        kg_name = self.options['kg_name']
        kg_prefix = kg_name.lower()
        filename = f"node_synonymizer.{kg_name}_map_state.pickle"
        print(f"INFO: Loading previous data structure state from {filename}")

        try:
            with open(filename, "rb") as infile:
                self.kg_map = pickle.load(infile)
            return True
        except:
            print(f"ERROR: Unable to reload previous state from {filename}")
            return None

        print(f"INFO: Finished loading previous data structure state from {filename}. Have {len(self.kg_map[kg_nodes])} kg_nodes.")


    # ############################################################################################
    #def show_state(self, concept='insulin'):
    #    uc_unique_concept_curie = kg_synonyms[concept]['uc_unique_concept_curie']
    #    uc_node_curie = uc_unique_concept_curie
    #    if kg_unique_concepts[uc_unique_concept_curie]['remapped_curie'] is not None:
    #        uc_node_curie = kg_unique_concepts[uc_unique_concept_curie]['remapped_curie']
    #    print(f"kg_nodes['{uc_node_curie}'] = ",json.dumps(kg_nodes[uc_node_curie], indent=2, sort_keys=True))
    #    print(f"kg_unique_concepts['{uc_unique_concept_curie}'] = ",json.dumps(kg_unique_concepts[uc_unique_concept_curie], indent=2, sort_keys=True))


    # ############################################################################################
    #### Store the built-up in-memory index to the database
    def store_kg_map(self):

        kg_name = self.options['kg_name']
        kg_prefix = kg_name.lower()

        kg_nodes = self.kg_map['kg_nodes']
        kg_unique_concepts = self.kg_map['kg_unique_concepts']
        kg_curies = self.kg_map['kg_curies']
        kg_synonyms = self.kg_map['kg_synonyms']

        # Write all nodes
        n_rows = len(kg_nodes)
        i_rows = 0
        previous_percentage = -1
        rows = []
        print(f"INFO: Writing {n_rows} nodes to the database")
        for uc_curie,node in kg_nodes.items():
            rows.append( [ uc_curie, node['curie'], node['original_name'], node['adjusted_name'], node['type'], node['uc_unique_concept_curie'], node['kg_presence'] ] )
            i_rows += 1
            if i_rows == int(i_rows/5000.0)*5000 or i_rows == n_rows:
                self.connection.executemany(f"INSERT INTO {kg_prefix}_node{TESTSUFFIX} (uc_curie,curie,original_name,adjusted_name,type,unique_concept_curie,kg_presence) values (?,?,?,?,?,?,?)", rows)
                self.connection.commit()
                rows = []
                percentage = int(i_rows*100.0/n_rows)
                if percentage > previous_percentage:
                    previous_percentage = percentage
                    print(str(percentage)+"%..", end='', flush=True)

        # Write all unique concepts
        n_rows = len(kg_unique_concepts)
        i_rows = 0
        previous_percentage = -1
        rows = []
        print(f"\nINFO: Writing {n_rows} unique_concepts to the database")
        for uc_curie,concept in kg_unique_concepts.items():
            rows.append( [ uc_curie, concept['curie'], concept['remapped_curie'], concept['kg1_best_curie'], concept['kg2_best_curie'], concept['name'], concept['type'], concept['normalizer_curie'], concept['normalizer_name'], concept['normalizer_type'] ] )
            i_rows += 1
            if i_rows == int(i_rows/5000.0)*5000 or i_rows == n_rows:
                self.connection.executemany(f"INSERT INTO {kg_prefix}_unique_concept{TESTSUFFIX} (uc_curie,curie,remapped_curie,kg1_best_curie,kg2_best_curie,name,type,normalizer_curie,normalizer_name,normalizer_type) values (?,?,?,?,?,?,?,?,?,?)", rows)
                self.connection.commit()
                rows = []
                percentage = int(i_rows*100.0/n_rows)
                if percentage > previous_percentage:
                    previous_percentage = percentage
                    print(str(percentage)+"%..", end='', flush=True)

        # Write all curies
        n_rows = len(kg_curies)
        i_rows = 0
        previous_percentage = -1
        rows = []
        print(f"\nINFO: Writing {n_rows} curies to the database")
        for uc_curie,concept in kg_curies.items():
            rows.append( [ uc_curie, concept['curie'], concept['uc_unique_concept_curie'], concept['type'], concept['source'] ] )
            i_rows += 1
            if i_rows == int(i_rows/5000.0)*5000 or i_rows == n_rows:
                self.connection.executemany(f"INSERT INTO {kg_prefix}_curie{TESTSUFFIX} (uc_curie,curie,unique_concept_curie,type,source) values (?,?,?,?,?)", rows)
                self.connection.commit()
                rows = []
                percentage = int(i_rows*100.0/n_rows)
                if percentage > previous_percentage:
                    previous_percentage = percentage
                    print(str(percentage)+"%..", end='', flush=True)

        # Write all synonyms
        n_rows = len(kg_synonyms)
        i_rows = 0
        previous_percentage = -1
        rows = []
        print(f"\nINFO: Writing {n_rows} synonyms to the database")
        for lc_synonym_name,synonym in kg_synonyms.items():
            rows.append( [ lc_synonym_name, synonym['name'], synonym['uc_unique_concept_curie'], synonym['source'] ] )
            i_rows += 1
            if i_rows == int(i_rows/5000.0)*5000 or i_rows == n_rows:
                self.connection.executemany(f"INSERT INTO {kg_prefix}_synonym{TESTSUFFIX} (lc_name,name,unique_concept_curie,source) values (?,?,?,?)", rows)
                self.connection.commit()
                rows = []
                percentage = int(i_rows*100.0/n_rows)
                if percentage > previous_percentage:
                    previous_percentage = percentage
                    print(str(percentage)+"%..", end='', flush=True)


    # ############################################################################################
    #### Sift through the synonym list looking for concepts that should be merged
    def coalesce_duplicates(self):

        kg_nodes = self.kg_map['kg_nodes']
        kg_unique_concepts = self.kg_map['kg_unique_concepts']
        kg_curies = self.kg_map['kg_curies']
        kg_synonyms = self.kg_map['kg_synonyms']
        unique_concepts_to_delete = {}

        print("INFO: Coalescing concepts by identical lower-cased name")

        debug_flag = False

        # Loop over all synonyms
        for lc_synonym_name,synonym in kg_synonyms.items():

            # If there are 0 curies, this is an error. Should not happen
            if len(synonym['uc_unique_concept_curies']) == 0:
                print("ERROR: Zero length unique_concept_curies")

            # If there are multiple, coalesce them
            elif len(synonym['uc_unique_concept_curies']) > 1:
                if debug_flag:
                    print(f"INFO: Synonym '{lc_synonym_name}' maps to multiple concepts: {synonym['uc_unique_concept_curies']}.  Coalesce them.")
                scores = {}
                for uc_unique_concept_curie in synonym['uc_unique_concept_curies']:

                    # It's possible that this entry was already remapped and is no longer a kg_unique_concept. Skip if not there.
                    if uc_unique_concept_curie not in kg_unique_concepts:
                        continue

                    # Apply some arbitrary scoring
                    scores[uc_unique_concept_curie] = 0
                    if kg_unique_concepts[uc_unique_concept_curie]['normalizer_curie'] is not None and kg_unique_concepts[uc_unique_concept_curie]['normalizer_curie'] > '':
                        scores[uc_unique_concept_curie] += 100

                    # Give disease a boost over phenotypic_feature
                    if kg_unique_concepts[uc_unique_concept_curie]['type'] == 'disease':
                        scores[uc_unique_concept_curie] += 150

                    scores[uc_unique_concept_curie] += len(kg_unique_concepts[uc_unique_concept_curie]['all_uc_curies'])
                    if debug_flag:
                        print(f"  {uc_unique_concept_curie} scores {scores[uc_unique_concept_curie]}")

                # Choose the best one
                best_curie = None
                best_score = -1
                for curie,score in scores.items():
                    if score > best_score:
                        best_curie = curie
                        best_score = score
                uc_best_curie = best_curie.upper()

                # Coalece
                for uc_curie in synonym['uc_unique_concept_curies']:

                    # It's possible that this entry was already remapped and is no longer a kg_unique_concept. Skip if not there.
                    if uc_curie not in kg_unique_concepts:
                        continue

                    if uc_curie != uc_best_curie:
                        kg_unique_concepts[uc_curie]['remapped_curie'] = best_curie
                        for uc_equivalent_curie in kg_unique_concepts[uc_curie]['all_uc_curies']:
                            kg_unique_concepts[uc_best_curie]['all_uc_curies'][uc_equivalent_curie] = 1
                            if uc_equivalent_curie in kg_nodes:
                                kg_nodes[uc_equivalent_curie]['uc_unique_concept_curie'] = uc_best_curie
                            kg_curies[uc_equivalent_curie]['uc_unique_concept_curie'] = uc_best_curie
                        for equivalent_name in kg_unique_concepts[curie]['all_lc_names']:
                            kg_unique_concepts[best_curie]['all_lc_names'][equivalent_name] = 1
                        unique_concepts_to_delete[uc_curie] = uc_best_curie
                synonym['uc_unique_concept_curie'] = uc_best_curie
                synonym['uc_unique_concept_curies'] = { uc_best_curie: 12 }

                if debug_flag:
                    print(f"  --> {lc_synonym_name} now maps to {synonym['uc_unique_concept_curies']}")


        # For unique_concepts to be deleted, reassign kg_nodes pointing to it
        found_change = 1
        iterations = 0
        while found_change:
            found_change = 0
            iterations += 1
            print(f"INFO: Resolve kg_nodes remappings (iteration {iterations})")
            for uc_curie_name,kg_node in kg_nodes.items():
                if kg_node['uc_unique_concept_curie'] in unique_concepts_to_delete:
                    if debug_flag:
                        print(f"**** Reassign kg_node {uc_curie_name} unique_concept {kg_node['uc_unique_concept_curie']} to {unique_concepts_to_delete[kg_node['uc_unique_concept_curie']]}")
                    kg_node['uc_unique_concept_curie'] = unique_concepts_to_delete[kg_node['uc_unique_concept_curie']]
                    found_change += 1
            if debug_flag:
                print(f"Found {found_change} changes to make on iteration {iterations}")
            if iterations > 10:
                print(f"ERROR: Reached max iterations. Stuck in an endless loop 609?")

        # For unique_concepts to be deleted, reassign kg_curies pointing to it
        found_change = 1
        iterations = 0
        while found_change:
            found_change = 0
            iterations += 1
            print(f"INFO: Resolve kg_curies remappings (iteration {iterations})")
            for uc_curie_name,kg_curie in kg_curies.items():
                if kg_curie['uc_unique_concept_curie'] in unique_concepts_to_delete:
                    if debug_flag:
                        print(f"**** Reassign kg_curie {uc_curie_name} unique_concept {kg_curie['uc_unique_concept_curie']} to {unique_concepts_to_delete[kg_curie['uc_unique_concept_curie']]}")
                    kg_curie['uc_unique_concept_curie'] = unique_concepts_to_delete[kg_curie['uc_unique_concept_curie']]
                    found_change += 1
            if debug_flag:
                print(f"Found {found_change} changes to make on iteration {iterations}")
            if iterations > 10:
                print(f"ERROR: Reached max iterations. Stuck in an endless loop 626?")

        # For unique_concepts to be deleted, reassign kg_synonyms pointing to it
        found_change = 1
        iterations = 0
        while found_change:
            found_change = 0
            iterations += 1
            print(f"INFO: Resolve kg_synonyms remappings (iteration {iterations})")
            for uc_curie_name,kg_synonym in kg_synonyms.items():
                if kg_synonym['uc_unique_concept_curie'] in unique_concepts_to_delete:
                    if debug_flag:
                        print(f"**** Reassign kg_synonym {uc_curie_name} unique_concept {kg_synonym['uc_unique_concept_curie']} to {unique_concepts_to_delete[kg_synonym['uc_unique_concept_curie']]}")
                    kg_synonym['uc_unique_concept_curie'] = unique_concepts_to_delete[kg_synonym['uc_unique_concept_curie']]
                    found_change += 1
            if debug_flag:
                print(f"Found {found_change} changes to make on iteration {iterations}")
            if iterations > 10:
                print(f"ERROR: Reached max iterations. Stuck in an endless loop 604?")

        # Go through an delete all the unneeded unique_concepts
        # We do this afterwards because a unique concept may be needed more than once above and deleting the first time causes an error
        for uc_curie in unique_concepts_to_delete:
            del kg_unique_concepts[uc_curie]



    # ############################################################################################
    #### Go through all unique concepts and map them all to the best kg_nodes
    #### This just picks the first one. This could be a whole lot smarter. FIXME
    def remap_unique_concepts(self):

        kg_name = self.options['kg_name']
        kg_prefix = kg_name.lower()

        print("INFO: Remap the unique concepts...")

        kg_nodes = self.kg_map['kg_nodes']
        kg_unique_concepts = self.kg_map['kg_unique_concepts']
        kg_curies = self.kg_map['kg_curies']
        kg_synonyms = self.kg_map['kg_synonyms']

        uc_curie_scores = {
            'UNIPROTKB': 2000,
            'MONDO': 100,
            'DOID': 90,
            'OMIM': 80,
        }

        # Loop over all unique_concepts
        for uc_curie,concept in kg_unique_concepts.items():

            debug_flag = False
            if 'xxxxxlzheimer' in concept['name']:
                debug_flag = True

            if debug_flag:
                print("====================================================================")
                print(f"==== {uc_curie}  {concept['name']}  {concept['type']}")
                print(concept)

            # Track the best ones
            uc_best_curie = '-'
            best_curie_score = -1
            uc_best_kg1_curie = '-'
            best_kg1_curie_score = -1

            # Loop over all the equivalences, picking the best ones
            for uc_equivalent_curie in concept['all_uc_curies']:
                score = 0
                if uc_equivalent_curie in kg_nodes:

                    # If the types are the same, big boost (e.g. when diseases and phenotypic_features are equivalent)
                    if kg_nodes[uc_equivalent_curie]['type'] == concept['type']:
                        score += 1000
                    uc_curie_prefix = uc_equivalent_curie.split(':')[0]
                    if uc_curie_prefix in uc_curie_scores:
                        score += uc_curie_scores[uc_curie_prefix]

                    if uc_curie_prefix == 'UNIPROTKB':
                        if ':P' in uc_equivalent_curie: score += 2
                        if ':Q' in uc_equivalent_curie: score += 1

                    if score > best_curie_score:
                        uc_best_curie = uc_equivalent_curie
                        best_curie_score = score

                    # Compute the KG1 scores
                    if 'KG1' in kg_nodes[uc_equivalent_curie]['kg_presence'] and score > best_kg1_curie_score:
                        uc_best_kg1_curie = uc_equivalent_curie
                        best_kg1_curie_score = score

                    if debug_flag:
                        print(f"- {uc_equivalent_curie} is a node of type {kg_nodes[uc_equivalent_curie]['type']} scores {score}")

            best_curie = kg_nodes[uc_best_curie]['curie']
            concept['curie'] = best_curie
            concept['name'] = kg_nodes[uc_best_curie]['adjusted_name']
            concept['type'] = kg_nodes[uc_best_curie]['type']
            concept['remapped_curie'] = best_curie

            concept[f"kg2_best_curie"] = best_curie
            concept[f"kg1_best_curie"] = None
            if best_kg1_curie_score > -1:
                best_kg1_curie = kg_nodes[uc_best_kg1_curie]['curie']
                concept[f"kg1_best_curie"] = best_kg1_curie

            if debug_flag:
                print(f"--> Best curie is {best_curie}")
                print(json.dumps(concept, indent=2, sort_keys=True))
                input("Press [ENTER] to continue...")

        # Print the current state
        if debug_flag:
            print("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%")
            print("Current state of kg_unique_concepts:")
            for key,concept in kg_unique_concepts.items():
                print(f"- Concept key {key} has curie {concept['curie']} and remapped curie {concept['remapped_curie']}")
            for key,concept in kg_curies.items():
                print(f"- Curie {key} points to unique concept key {concept['uc_unique_concept_curie']}")
            for key,concept in kg_synonyms.items():
                print(f"- Synonym {key} points to unique concept key {concept['uc_unique_concept_curie']}")



    # ############################################################################################
    #### The input lines are a bit messy. Here is special code to tidy things up a bit using hand curated heuristics
    def scrub_input(self, node_curie, node_name, node_type, debug_flag):

        # Many MONDO names have a ' (disease)' suffix, which seems undesirable, so strip them out
        if 'MONDO:' in node_curie:
            node_name = re.sub(r'\s*\(disease\)\s*$','',node_name)
        # Many PR names have a ' (human)' suffix, which seems undesirable, so strip them out
        if 'PR:' in node_curie:
            node_name = re.sub(r'\s*\(human\)\s*$','',node_name)
        # Many ENSEMBLs have  [Source:HGNC Symbol;Acc:HGNC:29884]
        if 'ENSEMBL:' in node_curie:
            node_name = re.sub(r'\s*\[Source:HGNC.+\]\s*','',node_name)


        # Create a list of all the possible names we will add to the database
        names = { node_name: 0 }

        # OMIM often has multiple names separated by semi-colon. Separate them
        if re.match("OMIM:", node_curie):
            multipleNames = node_name.split("; ")
            if len(multipleNames) > 1:
                for possibleName in multipleNames:
                    if possibleName == multipleNames[0]:
                        next
                    names[possibleName] = 0

        # Reactome names sometimes have an abbrevation in parentheses. Extract it and store both the abbreviation and the name without it
        elif re.match("REACT:R-HSA-", node_curie):
            # Also store the path name without embedded abbreviations
            match = re.search(r' \(([A-Z0-9\-]{1,8})\)', node_name)
            if match:
                names[match.group(1)] = 0
                newName = re.sub(
                    r' \([A-Z0-9\-]{1,8}\)', "", node_name, flags=re.IGNORECASE)
                names[newName] = 0

        # If this is a UniProt identifier, add a synonym that is the naked identifier without the prefix
        elif re.match("UniProtKB:[A-Z][A-Z0-9]{5}", node_curie) or re.match("UniProtKB:A[A-Z0-9]{9}", node_curie):
            tmp = re.sub("UniProtKB:", "", node_curie)
            names[tmp] = 0

        # If this is a PR identifier, add a synonym that is the naked identifier without the prefix
        elif re.match("PR:[A-Z][A-Z0-9]{5}", node_curie) or re.match("PR:A[A-Z0-9]{9}", node_curie):
            tmp = re.sub("PR:", "", node_curie)
            names[tmp] = 0

        # Create duplicates for various DoctorName's diseases
        # Cannot add to names{} in place while looping, so put in a new dict and then append when done
        more_names = {}
        for name in names:
            if re.search("'s ", name):
                newName = re.sub("'s ", "s ", name)
                more_names[newName] = 0
                newName = re.sub("'s ", " ", name)
                more_names[newName] = 0
        for name in more_names:
            names[name] = more_names[name]

        # A few special cases
        if re.search("alzheimer ", node_name, flags=re.IGNORECASE):
            newName = re.sub("alzheimer ", "alzheimers ", node_name, flags=re.IGNORECASE)
            names[newName] = 0

            newName = re.sub("alzheimer ", "alzheimer's ", node_name, flags=re.IGNORECASE)
            names[newName] = 0

        # Define a set of names that we will supplement with another name manually
        supplemental_names = { 'insulin human': 'insulin' }
        if node_name in supplemental_names:
            names[supplemental_names[node_name]] = 1


        # Return all the values after scrubbing
        scrubbed_values = { 'node_curie': node_curie, 'node_name': node_name, 'node_type': node_type, 'names': names }
        return scrubbed_values


    # ############################################################################################
    def create_indexes(self):

        kg_name = self.options['kg_name']
        kg_prefix = kg_name.lower()

        print(f"INFO: Creating INDEXes on {kg_prefix}_node{TESTSUFFIX}")
        self.connection.execute(f"CREATE INDEX idx_{kg_prefix}_node{TESTSUFFIX}_uc_curie ON {kg_prefix}_node{TESTSUFFIX}(uc_curie)")
        self.connection.execute(f"CREATE INDEX idx_{kg_prefix}_node{TESTSUFFIX}_unique_concept_curie ON {kg_prefix}_node{TESTSUFFIX}(unique_concept_curie)")

        print(f"INFO: Creating INDEXes on {kg_prefix}_unique_concept{TESTSUFFIX}")
        self.connection.execute(f"CREATE INDEX idx_{kg_prefix}_unique_concept{TESTSUFFIX}_uc_curie ON {kg_prefix}_unique_concept{TESTSUFFIX}(uc_curie)")

        print(f"INFO: Creating INDEXes on {kg_prefix}_curie{TESTSUFFIX}")
        self.connection.execute(f"CREATE INDEX idx_{kg_prefix}_curie{TESTSUFFIX}_uc_curie ON {kg_prefix}_curie{TESTSUFFIX}(uc_curie)")
        self.connection.execute(f"CREATE INDEX idx_{kg_prefix}_curie{TESTSUFFIX}_unique_concept_curie ON {kg_prefix}_curie{TESTSUFFIX}(unique_concept_curie)")

        print(f"INFO: Creating INDEXes on {kg_prefix}_synonym{TESTSUFFIX}")
        self.connection.execute(f"CREATE INDEX idx_{kg_prefix}_synonym{TESTSUFFIX}_lc_name ON {kg_prefix}_synonym{TESTSUFFIX}(lc_name)")
        self.connection.execute(f"CREATE INDEX idx_{kg_prefix}_synonym{TESTSUFFIX}_unique_concept_curie ON {kg_prefix}_synonym{TESTSUFFIX}(unique_concept_curie)")


    # ############################################################################################
    def import_equivalencies(self):

        filename = 'kg2_equivalencies.tsv'
        if not os.path.exists(filename):
            print(f"WARNING: Did not find equivalencies file {filename}. Skipping import")
            return
        print(f"INFO: Reading equivalencies from {filename}")

        kg_curies = self.kg_map['kg_curies']

        stats = { 'already equivalent': 0, 'need to add new link': 0, 'neither curie found': 0, 'association conflict': 0 }

        iline = 0
        with open(filename) as infile:
            for line in infile:
                line = line.strip()
                if "n1.id" in line:
                    continue
                match = re.match(r'^\s*$',line)
                if match:
                    continue
                iline += 1
                #print(f"line={line}")
                columns = line.split("\t")
                node1_curie = columns[0]
                node2_curie = columns[1]
                #print(f"{node1_curie}  -  {node2_curie}")

                uc_node1_curie = node1_curie.upper()
                uc_node2_curie = node2_curie.upper()

                linking_curie = None
                uc_linking_curie = None
                if uc_node1_curie in kg_curies:
                    linking_curie = node1_curie
                    uc_linking_curie = linking_curie.upper()
                    second_curie = node2_curie
                    uc_second_curie = second_curie.upper()

                elif uc_node2_curie in kg_curies:
                    linking_curie = node2_curie
                    uc_linking_curie = linking_curie.upper()
                    second_curie = node1_curie
                    uc_second_curie = second_curie.upper()

                else:
                    print(f"ERROR: Niether {uc_node1_curie} nor {uc_node2_curie} found in kg_curies at line {iline+1}")
                    stats['neither curie found'] += 1
                    continue

                if uc_second_curie in kg_curies:
                    uc_linking_unique_concept_curie = kg_curies[uc_linking_curie]['uc_unique_concept_curie']
                    uc_second_unique_concept_curie = kg_curies[uc_second_curie]['uc_unique_concept_curie']

                    if uc_linking_unique_concept_curie == uc_second_unique_concept_curie:
                        stats['already equivalent'] += 1
                    else:
                        stats['association conflict'] += 1

                else:
                    stats['need to add new link'] += 1

                #if iline > 10:
                #    return

        print(f"INFO: Read {iline} equivalencies from {filename}")
        for stat_name,stat in stats.items():
            print(f"      - {stat_name}: {stat}")
        return


    # ############################################################################################
    def import_synonyms(self):

        filename = 'kg2_synonyms.json'
        if not os.path.exists(filename):
            print(f"WARNING: Did not find synonyms file {filename}. Skipping import")
            return
        print(f"INFO: Reading synonyms from {filename}")

        with open(filename) as infile:
            node_synonyms = json.load(infile)
            inode = 0
            for node,node_data in node_synonyms.items():
                print(f"{node} has synonyms {node_data}")
                inode += 1
                if inode > 10:
                    return

        print(f"INFO: Read {iline} equivalencies from {filename}")
        return


    # ############################################################################################

    # Access methods

    # ############################################################################################
    def get_curies_and_types(self, name, kg_name='KG2'):

        # Determine the table prefix for the knowledge graph selected
        if kg_name.upper() == 'KG1' or kg_name.upper() == 'KG2':
            kg_prefix = kg_name.lower()
        else:
            print("ERROR: kg_name must be either 'KG1' or 'KG2'")
            return None

        kg_prefix = 'kg2'

        # Set up the return list
        curies_and_types = []

        # Search the synonym table for the provided name
        cursor = self.connection.cursor()
        cursor.execute( f"SELECT unique_concept_curie FROM {kg_prefix}_synonym{TESTSUFFIX} WHERE lc_name = ?", (name.lower(),) )
        rows = cursor.fetchall()

        # If no rows came back, see if it matches a CURIE
        if len(rows) == 0:
            cursor = self.connection.cursor()
            cursor.execute( f"SELECT unique_concept_curie FROM {kg_prefix}_curie{TESTSUFFIX} WHERE uc_curie = ?", (name.upper(),) )    # FIXME: need to make curie upper()?
            rows = cursor.fetchall()

        # If there are still no rows, then just return an empty list
        if len(rows) == 0:
            return curies_and_types

        # If multiple rows come back, this is probably an error in the database
        if len(rows) > 1:
            print(f"WARNING: Search in NodeSynonymizer for '{name}' turned up more than one unique_concept. This shouldn't be.")

        # Extract the CURIE for the unique concept
        unique_concept_curie = rows[0][0]

        # Get the list of nodes that link to this concept
        cursor = self.connection.cursor()
        cursor.execute( f"SELECT * FROM {kg_prefix}_node{TESTSUFFIX} WHERE unique_concept_curie = ?", (unique_concept_curie,) )
        rows = cursor.fetchall()
        curies_and_types = []
        for row in rows:
            curies_and_types.append({"curie": row[1], "type": row[4], "name": row[3]})
        return curies_and_types



    # ############################################################################################
    def get_curies_and_types_and_names(self, name, kg_name='KG2'):

        curies_and_types = self.get_curies_and_types(name, kg_name=kg_name)

        for entity in curies_and_types:

            # Try to fetch the description from the knowledge graph
            try:
                properties = RU.get_node_properties(entity['curie'])
                if 'description' in properties:
                    entity['description'] = properties['description']
            except:
                # This will happen with this node is in KG2 but not KG1. FIXME
                pass

        return curies_and_types


    # ############################################################################################
    def get_names(self, curie, kg_name='KG2'):

        # Determine the table prefix for the knowledge graph selected
        if kg_name.upper() == 'KG1' or kg_name.upper() == 'KG2':
            kg_prefix = kg_name.lower()
        else:
            print("ERROR: kg_name must be either 'KG1' or 'KG2'")
            return None

        # Set up the return list
        names = []

        # Search the curie table for the provided curie
        cursor = self.connection.cursor()
        cursor.execute( f"SELECT unique_concept_curie FROM {kg_prefix}_curie{TESTSUFFIX} WHERE uc_curie = ?", (curie.upper(),) )    # FIXME: need to make curie upper()?
        rows = cursor.fetchall()

        # If there are still no rows, then just return an empty list
        if len(rows) == 0:
            return names

        # If multiple rows come back, this is probably an error in the database
        if len(rows) > 1:
            print(f"WARNING: Search in NodeSynonymizer for '{curie}' turned up more than one unique_concept. This shouldn't be.")

        # Extract the CURIE for the unique concept
        unique_concept_curie = rows[0][0]

        # Get the list of names that link to this concept
        cursor = self.connection.cursor()
        cursor.execute( f"SELECT * FROM {kg_prefix}_synonym{TESTSUFFIX} WHERE unique_concept_curie = ?", (unique_concept_curie,) )
        rows = cursor.fetchall()
        for row in rows:
            names.append(row[1])
        return names


    # ############################################################################################
    def get_curies(self, name, kg_name='KG2'):

        curies_and_types = self.get_curies_and_types(name, kg_name)

        if curies_and_types is None:
            return None

        # Return a list of curies
        curies = []
        for curies_and_type in curies_and_types:
            curies.append(curies_and_type['curie'])
        return curies


    # ############################################################################################
    def is_curie_present(self, curie, kg_name='KG2'):

        # Determine the table prefix for the knowledge graph selected
        if kg_name.upper() == 'KG1' or kg_name.upper() == 'KG2':
            kg_prefix = kg_name.lower()
        else:
            print("ERROR: kg_name must be either 'KG1' or 'KG2'")
            return None

        cursor = self.connection.cursor()
        cursor.execute( f"SELECT * FROM {kg_prefix}_node{TESTSUFFIX} WHERE uc_curie = ?", (curie.upper(),) )
        rows = cursor.fetchall()

        if len(rows) == 0:
            return False
        return True


    # ############################################################################################
    def get_KG1_curies(self, name):

        curies_list = self.get_curies(name, kg_name='KG2')
        return curies_list


    # ############################################################################################
    def convert_curie(self, curie, namespace):

        kg_name = 'KG2'                                                         # FIXME. hardwired to KG1 for now
        curies_and_types = self.get_curies_and_types(curie, kg_name)

        if len(curies_and_types) == 0:
            return []

        curies = {}
        curies_list = []
        for row in curies_and_types:
            curie = row['curie']
            match = re.match(namespace+':',curie)
            if match:
                if curie not in curies:
                    curies_list.append(curie)
                    curies[curie] = 1
        return curies_list



    # ############################################################################################
    def get_equivalent_curies(self, curies, kg_name='KG2'):

        return self.get_equivalent_nodes(curies, kg_name)


    # ############################################################################################
    def get_equivalent_nodes(self, curies, kg_name='KG2'):

        # If no entity was passed, then nothing to do
        if curies is None:
            return None

        # Verify that kg_name is an allowed value
        if kg_name.upper() != 'KG1' and kg_name.upper() != 'KG2':
            print("ERROR: kg_name must be either 'KG1' or 'KG2'")
            return None

        # The table prefix is always kg2 now
        kg_prefix = 'kg2'

        # If the provided value is just a string, turn it into a list
        if isinstance(curies,str):
            curies = [ curies ]

        # For now enforce a limit of 40000 in the batch. At some point, the dynamically created SQL
        # will overrun the default 1 MB SQL buffer. Not til 60,000, though, given average curie size.
        if len(curies) > 40000:
            print("ERROR: Maximum number of curies is currently 40000. Maybe the limit could be extended")
            return None

        # Make a comma-separated list string
        uc_curies = []
        results = {}
        curie_map = {}
        for curie in curies:
            uc_curie = curie.upper()
            curie_map[uc_curie] = curie
            uc_curies.append(uc_curie)
            results[curie] = []
        entities_str = "','".join(uc_curies)

        # Search the curie table for the provided curie
        cursor = self.connection.cursor()
        sql = f"""
            SELECT C.curie,C.unique_concept_curie,N.curie,N.kg_presence FROM {kg_prefix}_curie{TESTSUFFIX} AS C
             INNER JOIN {kg_prefix}_node{TESTSUFFIX} AS N ON C.unique_concept_curie == N.unique_concept_curie
             WHERE C.uc_curie in ( '{entities_str}' )"""
        #eprint(sql)
        cursor.execute(sql)
        rows = cursor.fetchall()

        # If there are still no rows, then just return the results as the input list with all null values
        if len(rows) == 0:
            return results

        # Loop through all rows, building the list
        for row in rows:

            # Only if the requested kg_name is in this row do we record a value
            if kg_name in row[3]:

                # If the curie is not found in results, try to use the curie_map{} to resolve capitalization issues
                curie = row[0]
                if curie not in results:
                    if curie.upper() in curie_map:
                        curie = curie_map[curie.upper()]

                # Now store this curie in the list
                if curie in results:
                    results[curie].append(row[2])
                else:
                    print(f"ERROR: Unable to find curie {curie}")

        return results


    # ############################################################################################
    def get_canonical_curies(self, curies=None, names=None):

        # If the provided curies or names is just a string, turn it into a list
        if isinstance(curies,str):
            curies = [ curies ]
        if isinstance(names,str):
            names = [ names ]

        # Set up containers for the batches and results
        batches = []
        results = {}

        # Make sets of comma-separated list strings for the curies and set up the results dict with all the input values
        uc_curies = []
        curie_map = {}
        batch_size = 0
        if curies is not None:
            for curie in curies:
                results[curie] = None
                uc_curie = curie.upper()
                curie_map[uc_curie] = curie
                uc_curie = re.sub(r"'","''",uc_curie)   # Replace embedded ' characters with ''
                uc_curies.append(uc_curie)
                batch_size += 1
                if batch_size > 5000:
                    batches.append( { 'batch_type': 'curies', 'batch_str': "','".join(uc_curies) } )
                    uc_curies = []
                    batch_size = 0
            if batch_size > 0:
                batches.append( { 'batch_type': 'curies', 'batch_str': "','".join(uc_curies) } )

        # Make sets of comma-separated list strings for the names
        lc_names = []
        name_map = {}
        batch_size = 0
        if names is not None:
            for name in names:
                results[name] = None
                lc_name = name.lower()
                name_map[lc_name] = name
                lc_name = re.sub(r"'","''",lc_name)   # Replace embedded ' characters with ''
                lc_names.append(lc_name)
                batch_size += 1
                if batch_size > 5000:
                    batches.append( { 'batch_type': 'names', 'batch_str': "','".join(lc_names) } )
                    lc_names = []
                    batch_size = 0
            if batch_size > 0:
                batches.append( { 'batch_type': 'names', 'batch_str': "','".join(lc_names) } )

        # Search the curie table for the provided curie
        kg_prefix = 'kg2'

        for batch in batches:
            cursor = self.connection.cursor()
            if batch['batch_type'] == 'curies':
                sql = f"""
                    SELECT C.curie,C.unique_concept_curie,U.kg2_best_curie,U.name,U.type
                      FROM {kg_prefix}_curie{TESTSUFFIX} AS C
                     INNER JOIN {kg_prefix}_unique_concept{TESTSUFFIX} AS U ON C.unique_concept_curie == U.uc_curie
                     WHERE C.uc_curie in ( '{batch['batch_str']}' )"""
            else:
                sql = f"""
                    SELECT S.name,S.unique_concept_curie,U.kg2_best_curie,U.name,U.type
                      FROM {kg_prefix}_synonym{TESTSUFFIX} AS S
                     INNER JOIN {kg_prefix}_unique_concept{TESTSUFFIX} AS U ON S.unique_concept_curie == U.uc_curie
                     WHERE S.lc_name in ( '{batch['batch_str']}' )"""
            #print(f"INFO: Processing {batch['batch_type']} batch: {batch['batch_str']}")
            cursor.execute( sql )
            rows = cursor.fetchall()

            # Loop through all rows, building the list
            for row in rows:

                # If the curie or name is not found in results, try to use the curie_map{}/name_map{} to resolve capitalization issues
                entity = row[0]
                if entity not in results:
                    if batch['batch_type'] == 'curies':
                        if entity.upper() in curie_map:
                            entity = curie_map[entity.upper()]
                    else:
                        if entity.lower() in name_map:
                            entity = name_map[entity.lower()]

                # Now store this curie in the list
                if entity in results:
                    results[entity] = {
                        'preferred_curie': row[2],
                        'preferred_name': row[3],
                        'preferred_type': row[4]
                    }
                else:
                    print(f"ERROR: Unable to find entity {entity}")


        return results


    # ############################################################################################
    # Return results in the Node Normalizer format, either from SRI or KG1 or KG2
    def get_normalizer_results(self, entities=None, kg_name='SRI'):

        # If no entity was passed, then nothing to do
        if entities is None:
            return None

        # Verify that kg_name is an allowed value
        if kg_name.upper() != 'KG1' and kg_name.upper() != 'KG2' and kg_name.upper() != 'SRI':
            print("ERROR: kg_name must be either 'KG1' or 'KG2' or 'SRI'")
            return None

        # The table prefix is always kg2 now
        kg_prefix = 'kg2'

        # If the provided value is just a string, turn it into a list
        if isinstance(entities,str):
            entities = [ entities ]

        # Loop over all entities and get the results
        results = {}
        for entity in entities:

            # If for SRI, go directly there
            if kg_name == 'SRI':
                normalizer = SriNodeNormalizer()
                result = normalizer.get_node_normalizer_results(entity)
                if result is None:
                    results[entity] = None
                else:
                    results[entity] = result[entity]
                continue

            # Otherwise for KG1 and KG2

            # Search the curie table for the provided entity
            cursor = self.connection.cursor()
            cursor.execute( f"SELECT unique_concept_curie FROM {kg_prefix}_curie{TESTSUFFIX} WHERE uc_curie = ?", (entity.upper(),) )
            rows = cursor.fetchall()

            # If no rows came back, see if it matches a name
            if len(rows) == 0:
                cursor = self.connection.cursor()
                cursor.execute( f"SELECT unique_concept_curie FROM {kg_prefix}_synonym{TESTSUFFIX} WHERE lc_name = ?", (entity.lower(),) )
                rows = cursor.fetchall()

            # If there are still no rows, then just move on
            if len(rows) == 0:
                results[entity] = None
                continue

            # If multiple rows come back, this is probably an error in the database
            if len(rows) > 1:
                print(f"ERROR: Search in NodeSynonymizer for '{entity}' turned up more than one unique_concept. This shouldn't be.")

            # Extract the CURIE for the unique concept
            unique_concept_curie = rows[0][0]

            # Get the list of nodes that link to this concept
            cursor = self.connection.cursor()
            cursor.execute( f"SELECT * FROM {kg_prefix}_node{TESTSUFFIX} WHERE unique_concept_curie = ?", (unique_concept_curie,) )
            rows = cursor.fetchall()
            nodes = []
            for row in rows:
                if kg_name in row[6]:
                    nodes.append( {'identifier': row[1], 'type': row[4], "label": row[3], 'original_label': row[2] } )

            # Get the list of curies that link to this concept
            cursor = self.connection.cursor()
            cursor.execute( f"SELECT * FROM {kg_prefix}_curie{TESTSUFFIX} WHERE unique_concept_curie = ?", (unique_concept_curie,) )
            #cursor.execute( f"SELECT * FROM {kg_prefix}_curie{TESTSUFFIX} AS C LEFT JOIN {kg_prefix}_node{TESTSUFFIX} AS N ON C.uc_curie = N.uc_curie WHERE C.unique_concept_curie = ?", (unique_concept_curie,) )
            rows = cursor.fetchall()
            curies = []
            types = {}
            for row in rows:
                curies.append( {'identifier': row[1], 'type': row[3], 'source': row[4] } )  # FIXME would be nice to know the original name here. Store it!!
                types[row[3]] = 1

            # Get the list of synonyms that link to this concept
            cursor = self.connection.cursor()
            cursor.execute( f"SELECT * FROM {kg_prefix}_synonym{TESTSUFFIX} WHERE unique_concept_curie = ?", (unique_concept_curie,) )
            rows = cursor.fetchall()
            synonyms = []
            for row in rows:
                synonyms.append( {'label': row[1], 'source': row[3] } )

            # Get the unique concept information
            cursor = self.connection.cursor()
            cursor.execute( f"SELECT * FROM {kg_prefix}_unique_concept{TESTSUFFIX} WHERE uc_curie = ?", (unique_concept_curie,) )
            rows = cursor.fetchall()

            # If multiple rows come back, this is probably an error in the database
            if len(rows) > 1:
                print(f"ERROR: Search in NodeSynonymizer for '{unique_concept_curie}' turned up more than one unique_concept. This shouldn't be.")

            # Fill in the unique identifier
            row = rows[0]
            best_curie = row[4]
            if kg_name == 'KG1':
                best_curie = row[3]
            id = {
                'identifier': best_curie,
                'label': row[5],
                'type': row[6],
                'kg1_best_curie': row[3],
                'kg2_best_curie': row[4],
                'SRI_normalizer_curie': row[7],
                'SRI_normalizer_name': row[8],
                'SRI_normalizer_type': row[9],
            }

            # Make a list of the types
            all_types = { row[6]: 1 }
            all_types_list = [ row[6] ]
            for curie in curies:
                if curie['type'] not in all_types:
                    all_types_list.append(curie['type'])
                    all_types[curie['type']] = 1

            # Add this entry to the final results dict
            results[entity] = {
                'nodes': nodes,
                'equivalent_identifiers': curies,
                'synonyms': synonyms,
                'id': id,
                'type': all_types_list
            }

        return results


    # ############################################################################################
    def get_total_entity_count(self, node_type, kg_name='KG1'):

        # Verify the kg_name and set constraints
        if kg_name.upper() == 'KG1':
            additional_constraint = 'kg1_best_curie IS NOT NULL AND '
        elif kg_name.upper() == 'KG2':
            additional_constraint = ''
        else:
            print("ERROR: kg_name must be either 'KG1' or 'KG2'")
            return None
        kg_prefix = 'kg2'

        # Just get a count of all unique_concepts 
        cursor = self.connection.cursor()
        cursor.execute( f"SELECT COUNT(*) FROM {kg_prefix}_unique_concept{TESTSUFFIX} WHERE {additional_constraint} type = ?", (node_type,) )
        rows = cursor.fetchall()

        # Return the count value
        return rows[0][0]


    # ############################################################################################
    def test_select(self):

        cursor = self.connection.cursor()
        kg_prefix = 'kg2'
        #cursor.execute( f"SELECT TOP 10 * FROM {kg_prefix}_synonym{TESTSUFFIX} WHERE synonym = ?", (name.upper(),) )
        #cursor.execute( f"SELECT * FROM {kg_prefix}_synonym{TESTSUFFIX} LIMIT 100 ")
        #cursor.execute( f"SELECT * FROM {kg_prefix}_curie{TESTSUFFIX} LIMIT 100 ")
        #cursor.execute( f"SELECT * FROM {kg_prefix}_node{TESTSUFFIX} LIMIT 100 ")
        cursor.execute( f"SELECT * FROM {kg_prefix}_unique_concept{TESTSUFFIX} WHERE kg2_best_curie IS NULL LIMIT 100 ")
        #cursor.execute( f"""
        #    SELECT C.curie,C.unique_concept_curie,N.curie,N.kg_presence FROM {kg_prefix}_curie{TESTSUFFIX} AS C
        #     INNER JOIN {kg_prefix}_node{TESTSUFFIX} AS N ON C.unique_concept_curie == N.unique_concept_curie
        #     WHERE C.uc_curie in ( 'DOID:384','DOID:13636' )""" )

        rows = cursor.fetchall()
        for row in rows:
            print(row)

        #cursor = self.connection.cursor()
        #cursor.execute( f"SELECT * FROM kg2node{TESTSUFFIX} WHERE curie = ?", (name.upper(),) )
        #rows = cursor.fetchall()
        #for row in rows:
        #    print('KG2:',row)


# ############################################################################################
def run_example_1():
    synonymizer = NodeSynonymizer()

    print("==== Testing for finding curies by name ====")
    tests = ["APS2", "phenylketonuria", "Gaucher's disease", "Gauchers disease", "Gaucher disease",
            "Alzheimer Disease", "Alzheimers disease", "Alzheimer's Disease", "kidney", "KIDney", "P06865", "HEXA",
            "UniProtKB:P12004", "rickets", "fanconi anemia", "retina", "is", "insulin"]

    # The first one takes a bit longer, so do one before starting the timer
    test = synonymizer.get_curies("ibuprofen")

    t0 = timeit.default_timer()
    for test in tests:
        curies = synonymizer.get_curies(test)
        print(test+" = "+str(curies))
    t1 = timeit.default_timer()
    print("Elapsed time: "+str(t1-t0))


# ############################################################################################
def run_example_2():
    synonymizer = NodeSynonymizer()

    print("==== Testing presence of CURIEs ============================")
    tests = ["REACT:R-HSA-2160456", "DOID:9281", "OMIM:261600", "DOID:1926xx", "HP:0002511",
            "UBERON:0002113", "UniProtKB:P06865", "P06865", "KEGG:C10399", "GO:0034187", "DOID:10652xx"]

    t0 = timeit.default_timer()
    for test in tests:
        is_present = synonymizer.is_curie_present(test)
        print(test+" = "+str(is_present))
    t1 = timeit.default_timer()
    print("Elapsed time: "+str(t1-t0))


# ############################################################################################
def run_example_3():
    synonymizer = NodeSynonymizer()

    print("==== Getting properties by CURIE ============================")
    tests = ["REACT:R-HSA-2160456", "DOID:9281",
            "OMIM:261600", "DOID:1926xx", "P06865", 'UNIProtKB:P01308']

    t0 = timeit.default_timer()
    for test in tests:
        node_properties = synonymizer.get_curies_and_types_and_names(test)
        print(test+" = "+str(node_properties))
    t1 = timeit.default_timer()
    print("Elapsed time: "+str(t1-t0))


# ############################################################################################
def run_example_4():
    synonymizer = NodeSynonymizer()

    print("==== Testing for KG1 and KG2 ============================")
    tests = ["APS2", "phenylketonuria", "Gauchers disease", "kidney", "HEXA",
            "UniProtKB:P12004", "fanconi anemia", "ibuprofen"]

    t0 = timeit.default_timer()
    for test in tests:
        curies = synonymizer.get_curies(test)
        print(test+" in KG1 = "+str(curies))
        #curies = synonymizer.get_curies(test, kg_name='KG2')
        #print(test+" in KG2 = "+str(curies))
    t1 = timeit.default_timer()
    print("Elapsed time: "+str(t1-t0))


# ############################################################################################
def run_example_5():
    synonymizer = NodeSynonymizer()

    print("==== Getting KG1 CURIEs ============================")
    tests = ["CUI:C0031485", "CUI:C0017205", "UniProtKB:P06865", "MESH:D005199", "HEXA",
            "CHEBI:5855", "fanconi anemia", "ibuprofen", 'DOID:9281']

    t0 = timeit.default_timer()
    for test in tests:
        curies = synonymizer.get_KG1_curies(test)
        print(test+" = "+str(curies))
    t1 = timeit.default_timer()
    print("Elapsed time: "+str(t1-t0))


# ############################################################################################
def run_example_6():
    synonymizer = NodeSynonymizer()

    print("==== Convert CURIEs to requested namespace ============================")
    tests = [ [ "CUI:C0031485", "DOID" ], [ "FMA:7203", "UBERON" ], [ "MESH:D005199", "DOID" ], 
            [ "CHEBI:5855", "CHEMBL.COMPOUND" ], [ "ibuprofen", "CUI" ] ]

    t0 = timeit.default_timer()
    for test in tests:
        curies = synonymizer.convert_curie(test[0], test[1])
        print(f"{test[0]} -> {test[1]} = " + str(curies))
    t1 = timeit.default_timer()
    print("Elapsed time: "+str(t1-t0))


# ############################################################################################
def run_example_6():
    synonymizer = NodeSynonymizer()

    print("==== Get all equivalent nodes in a KG for an input curie ============================")
    tests = [ "DOID:14330", "CUI:C0031485", "FMA:7203", "MESH:D005199", "CHEBI:5855", "DOID:9281" ]
    #tests = [ "DOID:9281" ]

    t0 = timeit.default_timer()
    for test in tests:
        print("--- KG1 ---")
        nodes = synonymizer.get_equivalent_nodes(test,kg_name='KG1')
        print(f"{test} = " + str(nodes))
        print("--- KG2 ---")
        nodes = synonymizer.get_equivalent_nodes(test,kg_name='KG2')
        print(f"{test} = " + str(nodes))
        print()
        #print(json.dumps(nodes,sort_keys=True,indent=2))
    t1 = timeit.default_timer()
    print("Elapsed time: "+str(t1-t0))


# ############################################################################################
def run_example_7():
    synonymizer = NodeSynonymizer()

    for kg_name in [ 'KG1', 'KG2' ]:
        print(f"==== Get total number of concepts for several types for {kg_name} ============================")
        t0 = timeit.default_timer()
        for entity_type in [ 'chemical_substance', 'drug', 'disease', 'protein', 'gene', 'cheesecake' ]:
            print(f"count({entity_type}) = {synonymizer.get_total_entity_count(entity_type, kg_name=kg_name)}")
        t1 = timeit.default_timer()
        print("Elapsed time: "+str(t1-t0))


# ############################################################################################
def run_example_8():
    synonymizer = NodeSynonymizer()

    print("==== Test SELECT ============================")
    synonymizer.test_select('phenylketonuria')
    #synonymizer.test_select('CUI:C4710278')
    #synonymizer.test_select('UniProtKB:P06865')
    #print(synonymizer.is_curie_present('CUI:C4710278'))


# ############################################################################################
def run_example_9():
    synonymizer = NodeSynonymizer()

    print("==== Get canonical curies for a set of input curies ============================")
    curies = [ "DOID:14330", "CUI:C0031485", "FMA:7203", "MESH:D005199", "CHEBI:5855", "DOID:9281xxxxx", "MONDO:0005520" ]
    names = [ "phenylketonuria", "ibuprofen", "P06865", "HEXA", "Parkinson's disease", 'supernovas', "Bob's Uncle", 'double "quotes"' ]
    combined_list = curies
    combined_list.extend(names)

    t0 = timeit.default_timer()
    canonical_curies = synonymizer.get_canonical_curies(curies=curies)
    t1 = timeit.default_timer()
    canonical_curies2 = synonymizer.get_canonical_curies(names=names)
    t2 = timeit.default_timer()
    canonical_curies3 = synonymizer.get_canonical_curies(curies=combined_list,names=combined_list)
    t3 = timeit.default_timer()
    print(json.dumps(canonical_curies,sort_keys=True,indent=2))
    print("Elapsed time: "+str(t1-t0))
    print(json.dumps(canonical_curies2,sort_keys=True,indent=2))
    print("Elapsed time: "+str(t2-t1))
    print(json.dumps(canonical_curies3,sort_keys=True,indent=2))
    print("Elapsed time: "+str(t3-t2))


# ############################################################################################
def run_example_10():
    synonymizer = NodeSynonymizer()

    print("==== Complex name query ============================")
    node_ids = ['CHEMBL.MECHANISM:potassium_channel,_inwardly_rectifying,_subfamily_j,_member_11_opener', 'CHEMBL.MECHANISM:potassium_channel,_inwardly_rectifying,_subfamily_j,_member_8_opener', 'CHEMBL.MECHANISM:endothelin_receptor,_et-a/et-b_antagonist', 'CHEMBL.MECHANISM:amylin_receptor_amy1,_calcr/ramp1_agonist', 'CHEMBL.MECHANISM:sulfonylurea_receptor_2,_kir6.2_opener', 'CHEMBL.MECHANISM:sulfonylurea_receptor_1,_kir6.2_blocker', 'CHEMBL.MECHANISM:amiloride-sensitive_sodium_channel,_enac_blocker', 'CHEMBL.MECHANISM:hepatitis_c_virus_serine_protease,_ns3/ns4a_inhibitor', 'CHEMBL.MECHANISM:1,3-beta-glucan_synthase_inhibitor', "CHEMBL.MECHANISM:3',5'-cyclic_phosphodiesterase_inhibitor", 'CHEMBL.MECHANISM:dna_topoisomerase_i,_mitochondrial_inhibitor', 'CHEMBL.MECHANISM:carbamoyl-phosphate_synthase_[ammonia],_mitochondrial_positive_allosteric_modulator', 'CHEMBL.MECHANISM:parp_1,_2_and_3_inhibitor', 'CHEMBL.MECHANISM:c-jun_n-terminal_kinase,_jnk_inhibitor', 'CHEMBL.MECHANISM:voltage-gated_potassium_channel,_kqt;_kcnq2(kv7.2)/kcnq3(kv7.3)_activator', 'CHEMBL.MECHANISM:hla_class_ii_histocompatibility_antigen,_drb1-10_beta_chain_other', 'CHEMBL.MECHANISM:hla_class_ii_histocompatibility_antigen,_drb1-15_beta_chain_modulator', 'CHEMBL.MECHANISM:indoleamine_2,3-dioxygenase_inhibitor', 'CHEMBL.MECHANISM:5,6-dihydroxyindole-2-carboxylic_acid_oxidase_other', 'CHEMBL.MECHANISM:amine_oxidase,_copper_containing_inhibitor', 'CHEMBL.MECHANISM:carnitine_o-palmitoyltransferase_1,_muscle_isoform_inhibitor', 'CHEMBL.MECHANISM:troponin,_cardiac_muscle_positive_modulator', 'CHEMBL.MECHANISM:isocitrate_dehydrogenase_[nadp],_mitochondrial_inhibitor']

    t0 = timeit.default_timer()
    canonical_curies = synonymizer.get_canonical_curies(node_ids)
    t1 = timeit.default_timer()
    print(json.dumps(canonical_curies,sort_keys=True,indent=2))
    print("Elapsed time: "+str(t1-t0))


# ############################################################################################
def run_examples():
    run_example_9()
    return
    run_example_1()
    run_example_2()
    run_example_3()
    run_example_4()
    run_example_5()
    run_example_6()
    run_example_7()
    run_example_8()
    run_example_9()
    run_example_10()


####################################################################################################
def main():

    import json

    parser = argparse.ArgumentParser(
        description="Tests or rebuilds the ARAX Node Synonymizer. Note that the build process requires 20 GB RAM.", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-b', '--build', action="store_true",
                        help="If set, (re)build the index from scratch", default=False)
    parser.add_argument('-k', '--kg_name', action="store",
                        help="Specify the KG to access (KG2 or KG1 or SRI) (default is KG1)", default='KG1')
    parser.add_argument('-s', '--save_state', action="store_true",
                        help="If set, save the state of the build hashes when done reading source data (useful for subsequent --recollate)", default=False)
    parser.add_argument('-r', '--recollate', action="store_true",
                        help="If set, try to load the previous saved state and recollate the nodes and write new tables", default=False)
    parser.add_argument('-t', '--test', action="store_true",
                        help="If set, run a test of the index by doing several lookups", default=False)
    parser.add_argument('-l', '--lookup', action="store",
                        help="If set to a curie or name, then use the NodeSynonymizer (or SRI normalizer) to lookup the equivalence information for the curie or name", default=None)
    parser.add_argument('-q', '--query', action="store_true",
                        help="If set perform the test query and return", default=None)
    parser.add_argument('-g', '--get', action="store",
                        help="Get nodes for the specified list in the specified kg_name", default=None)
    args = parser.parse_args()

    if not args.build and not args.test and not args.recollate and not args.lookup and not args.query and not args.get:
        parser.print_help()
        sys.exit(2)

    synonymizer = NodeSynonymizer()

    # If the user asks to perform the SELECT statement, do it
    if args.query:
        synonymizer.test_select()
        return

    # If the user asks to perform the SELECT statement, do it
    if args.get:
        t0 = timeit.default_timer()
        curies = args.get.split(',')
        results = synonymizer.get_equivalent_nodes(curies,kg_name=args.kg_name)
        t1 = timeit.default_timer()
        print(json.dumps(results, indent=2, sort_keys=True))
        print(f"INFO: Information retrieved in {t1-t0} sec")
        return

    # If the --lookup option is provided, this takes precedence, perform the lookup and return
    if args.lookup is not None:
        t0 = timeit.default_timer()
        entities = args.lookup.split(',')
        equivalence = synonymizer.get_normalizer_results(entities, kg_name=args.kg_name)
        t1 = timeit.default_timer()
        print(json.dumps(equivalence, indent=2, sort_keys=True))
        print(f"INFO: Information retrieved in {t1-t0} sec")
        return

    # Verify and store the current KG
    if args.kg_name == 'KG1' or args.kg_name == 'KG2' or args.kg_name == 'both':
        synonymizer.options['kg_name'] = args.kg_name
    else:
        print("ERROR: kg_name must be either 'KG1' or 'KG2' (or 'both' for building)")
        sys.exit(5)

    # Store other provided options
    synonymizer.options['save_state'] = args.save_state

    #synonymizer.create_tables()
    #return

    # If the recollate option is selected, try to load the previous state
    if args.recollate:
        synonymizer.options['kg_name'] = 'KG2'
        if not synonymizer.reload_state():
            return

    # Else if the build option is selected, build the kg_map from scratch
    elif args.build:
        if args.kg_name == 'both':
            print("WARNING: Beginning full NodeSynonymizer build process. This requires 20 GB of RAM. If you don't have 20 GB of RAM available, this would be a good time to stop the process!")
            synonymizer.options['kg_name'] = 'KG2'
            synonymizer.build_kg_map()
            synonymizer.coalesce_duplicates()
            synonymizer.remap_unique_concepts()
            synonymizer.options['kg_name'] = 'KG1'
        synonymizer.build_kg_map()

    # If either one is selected, do the collation and database writing
    if args.build or args.recollate:
        synonymizer.coalesce_duplicates()
        synonymizer.remap_unique_concepts()
        if args.kg_name == 'both':
            synonymizer.options['kg_name'] = 'KG2'

        # If the flag is set, save our state here
        if 'save_state' in synonymizer.options and synonymizer.options['save_state'] is not None and synonymizer.options['save_state']:
            if not synonymizer.save_state():
                return

        # Import synonyms and equivalencies
        synonymizer.import_equivalencies()

        # Skip writing for the moment while we test
        #synonymizer.create_tables()
        #synonymizer.store_kg_map()
        #synonymizer.create_indexes()

        print(f"INFO: Created NodeSynonymizer with\n  {len(synonymizer.kg_map['kg_nodes'])} nodes\n  {len(synonymizer.kg_map['kg_unique_concepts'])} unique concepts\n" +
            f"  {len(synonymizer.kg_map['kg_curies'])} curies\n  {len(synonymizer.kg_map['kg_synonyms'])} names and abbreviations")
        print(f"INFO: Processing complete")

    # If requested, run the test examples
    if args.test:
        run_examples()


####################################################################################################
if __name__ == "__main__":
    main()
