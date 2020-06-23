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

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../")
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../QuestionAnswering")
import ReasoningUtilities as RU
#from RTXConfiguration import RTXConfiguration

# Testing and debugging flags
DEBUG = False
TESTSUFFIX = ""
#TESTSUFFIX = "_test2"


# Main class
class KGNodeIndex:

    # Constructor
    def __init__(self):
        filepath = os.path.dirname(os.path.abspath(__file__))
        self.databaseLocation = filepath
        self.lookup_table = {}

        #self.databaseLocation = 'C:/Users/ericd/Documents/zztmp'
        #print(f"INFO: Temporarily using filepath {self.databaseLocation}")

        is_rtx_production = False
        #if re.match("/mnt/data/orangeboard", filepath):
        #    is_rtx_production = True
        #if DEBUG:
        #    print("INFO: is_rtx_production="+str(is_rtx_production))

        if is_rtx_production:
            self.databaseName = "RTXFeedback"
            self.engine_type = "mysql"
        else:
            self.databaseName = "KGNodeIndex.sqlite"
            self.engine_type = "sqlite"
        self.connection = None
        self.connect()


    # Destructor
    def __del__(self):
        if self.engine_type == "mysql":
            self.disconnect()
        else:
            pass


    # Create and store a database connection
    def connect(self):
        # If already connected, don't need to do it again
        if self.connection is not None:
            return
        # Create an engine object
        if DEBUG is True:
            print("INFO: Connecting to database")
        if self.engine_type == "sqlite":
            self.connection = sqlite3.connect(f"{self.databaseLocation}/{self.databaseName}")
        else:
            pass
            #rtxConfig = RTXConfiguration()
            #engine = create_engine("mysql+pymysql://" + rtxConfig.mysql_feedback_username + ":" +
            #                       rtxConfig.mysql_feedback_password + "@" + rtxConfig.mysql_feedback_host + "/" + self.databaseName)


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


    # Delete and create the kgnode table
    def create_tables(self):
        if DEBUG is True:
            print("INFO: Creating database "+self.databaseName)
        self.connection.execute(f"DROP TABLE IF EXISTS kgnode{TESTSUFFIX}")
        self.connection.execute(f"DROP TABLE IF EXISTS kg1node{TESTSUFFIX}")
        self.connection.execute(f"CREATE TABLE kg1node{TESTSUFFIX}( curie VARCHAR(255), name VARCHAR(255), type VARCHAR(255), reference_curie VARCHAR(255) )" )
        self.connection.execute(f"DROP TABLE IF EXISTS kg2node{TESTSUFFIX}")
        self.connection.execute(f"CREATE TABLE kg2node{TESTSUFFIX}( curie VARCHAR(255), name VARCHAR(255), type VARCHAR(255), reference_curie VARCHAR(255) )" )


    # Create the KG node table
    def populate_table(self, kg_name):

        if kg_name == 'KG1':
            table_name = 'kg1node'
            file_suffix = '_KG1'
        elif kg_name == 'KG2':
            table_name = 'kg2node'
            file_suffix = '_KG2'
        else:
            print("ERROR: kg_name must be either 'KG1' or 'KG2'")
            sys.exit(5)

        filename = os.path.dirname(os.path.abspath(__file__)) + f"/../../../data/KGmetadata/NodeNamesDescriptions{file_suffix}.tsv"
        filesize = os.path.getsize(filename)
        previous_percentage = -1
        bytes_read = 0

        lineCounter = 0
        fh = open(filename, 'r', encoding="latin-1", errors="replace")
        print(f"INFO: Populating table {table_name}")

        # Have a dict for items already inserted so that we don't insert them twice
        namesDict = {}
        rows = []

        for line in fh:
            bytes_read += len(line)
            columns = line.strip().split("\t")
            curie = columns[0]
            name = columns[1]
            type = columns[2]

            #### For debugging problems
            debug_flag = False
            #if 'P06865' in curie: debug_flag = True

            # Some cleanup

            # Many MONDO names have a ' (disease)' suffix, which seems undesirable, so strip them out
            if 'MONDO:' in curie:
                name = re.sub(r'\s*\(disease\)\s*$','',name)
            # Many PR names have a ' (human)' suffix, which seems undesirable, so strip them out
            if 'PR:' in curie:
                name = re.sub(r'\s*\(human\)\s*$','',name)

            # Create a list of all the possible names we will add to the database
            names = [name]

            if re.match("OMIM:", curie):
                multipleNames = name.split("; ")
                if len(multipleNames) > 1:
                    for possibleName in multipleNames:
                        if possibleName == multipleNames[0]:
                            next
                        names.append(possibleName)

            elif re.match("R-HSA-", curie):
                # Also store the path name without embedded abbreviations
                if re.search(r' \([A-Z0-9]{1,8}\)', name):
                    newName = re.sub(
                        r' \([A-Z0-9]{1,8}\)', "", name, flags=re.IGNORECASE)
                    names.append(newName)

            # If this is a UniProt identifier, also add the CURIE and the naked identifier without the prefix
            elif re.match("UniProtKB:[A-Z][A-Z0-9]{5}", curie) or re.match("UniProtKB:A[A-Z0-9]{9}", curie):
                tmp = re.sub("UniProtKB:", "", curie)
                names.append(tmp)

            # If this is a PR identifier, also add the CURIE and the naked identifier without the prefix
            elif re.match("PR:[A-Z][A-Z0-9]{5}", curie) or re.match("PR:A[A-Z0-9]{9}", curie):
                tmp = re.sub("PR:", "", curie)
                names.append(tmp)

            # Create duplicates for various DoctorName's diseases
            for name in names:
                if re.search("'s ", name):
                    newName = re.sub("'s ", "s ", name)
                    names.append(newName)
                    #print("  duplicated _"+name+"_ to _"+newName+"_")
                    newName = re.sub("'s ", " ", name)
                    names.append(newName)
                    #print("  duplicated _"+name+"_ to _"+newName+"_")

            # A few special cases
            if re.search("alzheimer ", name, flags=re.IGNORECASE):
                newName = re.sub("alzheimer ", "alzheimers ",
                                 name, flags=re.IGNORECASE)
                names.append(newName)
                #print("  duplicated _"+name+"_ to _"+newName+"_")

                newName = re.sub("alzheimer ", "alzheimer's ",
                                 name, flags=re.IGNORECASE)
                names.append(newName)
                #print("  duplicated _"+name+"_ to _"+newName+"_")

            # Add all the possible names to the database
            if debug_flag:
                print()
                print(names)

            for name in names:
                name = name.upper()
                if name in namesDict and curie in namesDict[name]:
                    continue

                # Hard-coded list of short abbreviations to ignore because they're also English
                if name == "IS":
                    continue
                if name == "AS":
                    continue

                # Check and add an entry to the lookup table
                reference_curie = None
                if name in self.lookup_table:
                    reference_curie = self.lookup_table[name]
                    if curie not in self.lookup_table:
                        self.lookup_table[curie] = reference_curie
                else:
                    reference_curie = curie
                    if curie in self.lookup_table:
                        self.lookup_table[name] = reference_curie
                    else:
                        self.lookup_table[curie] = reference_curie
                        self.lookup_table[name] = reference_curie
                if debug_flag: print(f"reference_curie for {name} is {reference_curie}")

                # Add a row for this node
                rows.append([curie,name,type,reference_curie])
                if debug_flag: print([curie,name,type,reference_curie])
                if name not in namesDict:
                    namesDict[name] = {}
                namesDict[name][curie] = 1

            # Try also adding in the curie as a resolvable name
            if curie not in namesDict:
                if debug_flag: print(f"reference_curie for {curie} is {reference_curie}")
                rows.append([curie,curie.upper(),type,reference_curie])
                if debug_flag: print([curie,curie.upper(),type,reference_curie])
                if curie not in namesDict:
                    namesDict[curie] = {}
                namesDict[curie][curie] = 1

            # Commit every 10000 lines
            percentage = int(bytes_read*100.0/filesize)
            if percentage > previous_percentage:
                self.connection.executemany(f"INSERT INTO {table_name}{TESTSUFFIX}(curie,name,type,reference_curie) values (?,?,?,?)", rows)
                self.connection.commit()
                rows = []
                previous_percentage = percentage
                print(str(percentage)+"%..", end='', flush=True)

            debug_flag = False
            lineCounter += 1

        # Write out the last rows
        if len(rows) > 0:
            self.connection.executemany(f"INSERT INTO {table_name}{TESTSUFFIX}(curie,name,type,reference_curie) values (?,?,?,?)", rows)
            self.connection.commit()
            print("100..", end='', flush=True)

        fh.close()
        print("")


    def create_indexes(self, kg_name):

        if kg_name == 'KG1':
            table_name = 'kg1node'
        elif kg_name == 'KG2':
            table_name = 'kg2node'
        else:
            print("ERROR: kg_name must be either 'KG1' or 'KG2'")
            sys.exit(5)

        print(f"INFO: Creating INDEXes on {table_name}{TESTSUFFIX}")
        self.connection.execute(f"CREATE INDEX idx_{table_name}{TESTSUFFIX}_name ON {table_name}{TESTSUFFIX}(name)")
        self.connection.execute(f"CREATE INDEX idx_{table_name}{TESTSUFFIX}_curie ON {table_name}{TESTSUFFIX}(curie)")
        self.connection.execute(f"CREATE INDEX idx_{table_name}{TESTSUFFIX}_reference_curie ON {table_name}{TESTSUFFIX}(reference_curie)")


    def get_curies_and_types(self, name, kg_name='KG1'):

        table_name = 'kg1node'
        if kg_name.upper() == 'KG2':
            table_name = 'kg2node'

        cursor = self.connection.cursor()
        cursor.execute( f"SELECT * FROM {table_name}{TESTSUFFIX} WHERE name = ?", (name.upper(),) )
        rows = cursor.fetchall()
        curies_and_types = []
        for row in rows:
            curies_and_types.append({"curie": row[0], "type": row[2]})
        return curies_and_types


    def get_curies_and_types_and_names(self, name, kg_name='KG1'):

        table_name = 'kg1node'
        if kg_name.upper() == 'KG2':
            table_name = 'kg2node'

        cursor = self.connection.cursor()
        cursor.execute( f"SELECT * FROM {table_name}{TESTSUFFIX} WHERE name = ?", (name.upper(),) )
        rows = cursor.fetchall()
        curies_and_types_and_names = []
        for row in rows:
            names = self.get_names(row[0],kg_name=kg_name)
            best_name = "?"
            if names is not None:
                best_name = names[0]
            entity = {"curie": row[0],
                      "type": row[2], "name": best_name}

            # Also try to fetch the description from the knowledge graph
            try:
                properties = RU.get_node_properties(row[0])
                if 'description' in properties:
                    entity['description'] = properties['description']
            except:
                # This will happen with this node is in KG2 but not KG1. FIXME
                pass
            curies_and_types_and_names.append(entity)

        return curies_and_types_and_names


    def get_names(self, curie, kg_name='KG1'):

        table_name = 'kg1node'
        if kg_name.upper() == 'KG2':
            table_name = 'kg2node'

        cursor = self.connection.cursor()
        cursor.execute( f"SELECT * FROM {table_name}{TESTSUFFIX} WHERE curie = ?", (curie,) )
        rows = cursor.fetchall()

        # Return a list of curies
        curies = []
        for row in rows:
            if row[1] == curie:
                continue
            curies.append(row[0])
        return curies


    def get_curies(self, name, kg_name='KG1'):
        curies_and_types = self.get_curies_and_types(name, kg_name)

        if curies_and_types is None:
            return None

        # Return a list of curies
        curies = []
        for curies_and_type in curies_and_types:
            curies.append(curies_and_type["curie"])
        return(curies)


    def is_curie_present(self, curie, kg_name='KG1'):

        table_name = 'kg1node'
        if kg_name.upper() == 'KG2':
            table_name = 'kg2node'

        cursor = self.connection.cursor()
        cursor.execute( f"SELECT * FROM {table_name}{TESTSUFFIX} WHERE curie = ?", (curie,) )
        rows = cursor.fetchall()

        if len(rows) == 0:
            return False
        return True


    def get_KG1_curies(self, name):

        cursor = self.connection.cursor()
        cursor.execute( f"SELECT * FROM kg1node{TESTSUFFIX} WHERE name = ?", (name.upper(),) )
        rows = cursor.fetchall()

        if len(rows) == 0:
            cursor = self.connection.cursor()
            cursor.execute( f"SELECT * FROM kg2node{TESTSUFFIX} WHERE name = ?", (name.upper(),) )
            rows = cursor.fetchall()

        curies = {}
        curies_list = []
        for row in rows:
            curie = row[3]
            if curie not in curies:
                if self.is_curie_present(curie):
                    curies_list.append(curie)
                    curies[curie] = 1
        return curies_list


    def convert_curie(self, curie, namespace):

        cursor = self.connection.cursor()
        cursor.execute( f"SELECT * FROM kg2node{TESTSUFFIX} WHERE name = ?", (curie.upper(),) )
        rows = cursor.fetchall()

        if len(rows) == 0: return []

        reference_curie = rows[0][3]

        cursor = self.connection.cursor()
        cursor.execute( f"SELECT * FROM kg2node{TESTSUFFIX} WHERE reference_curie = ?", (reference_curie,) )
        rows = cursor.fetchall()

        curies = {}
        curies_list = []
        for row in rows:
            curie = row[0]
            match = re.match(namespace+':',curie)
            if match:
                if curie not in curies:
                    curies_list.append(curie)
                    curies[curie] = 1
        return curies_list


    def get_equivalent_curies(self, curie, kg_name='KG2'):

        table_name = 'kg1node'
        if kg_name.upper() == 'KG2':
            table_name = 'kg2node'

        cursor = self.connection.cursor()
        cursor.execute( f"SELECT * FROM {table_name}{TESTSUFFIX} WHERE curie = ?", (curie,) )
        rows = cursor.fetchall()

        if len(rows) == 0: return []

        reference_curies = {}
        reference_curie = None
        for row in rows:
            reference_curies[row[3]] = 1
            reference_curie = row[3]

        cursor = self.connection.cursor()
        cursor.execute( f"SELECT * FROM {table_name}{TESTSUFFIX} WHERE reference_curie = ?", (reference_curie,) )
        rows = cursor.fetchall()

        curies = {}
        for row in rows:
            curies[row[0]] = 1

        return list(curies.keys())


    def get_equivalent_entities(self, curie, kg_name='KG2'):

        table_name = 'kg1node'
        if kg_name.upper() == 'KG2':
            table_name = 'kg2node'

        equivalence = { curie: { } }

        cursor = self.connection.cursor()
        cursor.execute( f"SELECT * FROM {table_name}{TESTSUFFIX} WHERE curie = ?", (curie,) )
        rows = cursor.fetchall()

        if len(rows) == 0: return equivalence

        reference_curie = rows[0][3]
        equivalence[curie]['id'] = { 'identifier': reference_curie }
        equivalence[curie]['equivalent_identifiers'] = []
        equivalence[curie]['type'] = [ rows[0][2]]

        # What if there are multiple rows returned, this is not handled. FIXME
        #reference_curies = {}
        #for row in rows:
        #    reference_curies[row[3]] = 1

        cursor = self.connection.cursor()
        cursor.execute( f"SELECT * FROM {table_name}{TESTSUFFIX} WHERE reference_curie = ?", (reference_curie,) )
        rows = cursor.fetchall()

        curies = {}
        for row in rows:
            row_curie = row[0]
            if row_curie not in curies:
                equivalence[curie]['equivalent_identifiers'].append( { 'identifier': row_curie, 'label': row[1] } )
                if row_curie == curie:
                    equivalence[curie]['id']['label'] = row[1]
                curies[row_curie] = 1

        return equivalence


    def get_total_entity_count(self, type, kg_name='KG1'):

        table_name = 'kg1node'
        if kg_name.upper() == 'KG2':
            table_name = 'kg2node'

        count = None

        cursor = self.connection.cursor()
        cursor.execute( f"SELECT COUNT(DISTINCT reference_curie) FROM {table_name}{TESTSUFFIX} WHERE type = ?", (type,) )
        rows = cursor.fetchall()

        if len(rows) == 0:
            return count

        return rows[0][0]



    def test_select(self, name):

        cursor = self.connection.cursor()
        cursor.execute( f"SELECT * FROM kg1node{TESTSUFFIX} WHERE curie = ?", (name.upper(),) )
        rows = cursor.fetchall()
        for row in rows:
            print('KG1:',row)

        cursor = self.connection.cursor()
        cursor.execute( f"SELECT * FROM kg2node{TESTSUFFIX} WHERE curie = ?", (name.upper(),) )
        rows = cursor.fetchall()
        for row in rows:
            print('KG2:',row)


####################################################################################################
def main():

    import json

    parser = argparse.ArgumentParser(
        description="Tests or rebuilds the KG Node Index", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-b', '--build', action="store_true",
                        help="If set, (re)build the index from scratch", default=False)
    parser.add_argument('-t', '--test', action="store_true",
                        help="If set, run a test of the index by doing several lookups", default=False)
    args = parser.parse_args()

    if not args.build and not args.test:
        parser.print_help()
        sys.exit(2)

    kgNodeIndex = KGNodeIndex()

    # To (re)build
    if args.build:
        kgNodeIndex.create_tables()
        kgNodeIndex.populate_table(kg_name='KG1')
        kgNodeIndex.create_indexes(kg_name='KG1')
        kgNodeIndex.populate_table(kg_name='KG2')
        kgNodeIndex.create_indexes(kg_name='KG2')

    # Exit here if tests are not requested
    if not args.test:
        return

    print("==== Testing for finding curies by name ====")
    tests = ["APS2", "phenylketonuria", "Gaucher's disease", "Gauchers disease", "Gaucher disease",
             "Alzheimer Disease", "Alzheimers disease", "Alzheimer's Disease", "kidney", "KIDney", "P06865", "HEXA",
             "UniProtKB:P12004", "rickets", "fanconi anemia", "retina", "is"]

    # The first one takes a bit longer, so do one before starting the timer
    test = kgNodeIndex.get_curies("ibuprofen")

    t0 = timeit.default_timer()
    for test in tests:
        curies = kgNodeIndex.get_curies(test)
        print(test+" = "+str(curies))
    t1 = timeit.default_timer()
    print("Elapsed time: "+str(t1-t0))


    print("==== Testing presence of CURIEs ============================")
    tests = ["REACT:R-HSA-2160456", "DOID:9281", "OMIM:261600", "DOID:1926xx", "HP:0002511",
             "UBERON:0002113", "UniProtKB:P06865", "P06865", "KEGG:C10399", "GO:0034187", "DOID:10652xx"]

    t0 = timeit.default_timer()
    for test in tests:
        is_present = kgNodeIndex.is_curie_present(test)
        print(test+" = "+str(is_present))
    t1 = timeit.default_timer()
    print("Elapsed time: "+str(t1-t0))


    print("==== Getting properties by CURIE ============================")
    tests = ["REACT:R-HSA-2160456", "DOID:9281",
             "OMIM:261600", "DOID:1926xx", "P06865"]

    t0 = timeit.default_timer()
    for test in tests:
        node_properties = kgNodeIndex.get_curies_and_types_and_names(test)
        print(test+" = "+str(node_properties))
    t1 = timeit.default_timer()
    print("Elapsed time: "+str(t1-t0))


    print("==== Testing for KG1 and KG2 ============================")
    tests = ["APS2", "phenylketonuria", "Gauchers disease", "kidney", "HEXA",
             "UniProtKB:P12004", "fanconi anemia", "ibuprofen"]

    t0 = timeit.default_timer()
    for test in tests:
        curies = kgNodeIndex.get_curies(test)
        print(test+" in KG1 = "+str(curies))
        curies = kgNodeIndex.get_curies(test, kg_name='KG2')
        print(test+" in KG2 = "+str(curies))
    t1 = timeit.default_timer()
    print("Elapsed time: "+str(t1-t0))


    print("==== Getting KG1 CURIEs ============================")
    tests = ["CUI:C0031485", "CUI:C0017205", "UniProtKB:P06865", "MESH:D005199", "HEXA",
             "CHEBI:5855", "fanconi anemia", "ibuprofen", 'DOID:9281']

    t0 = timeit.default_timer()
    for test in tests:
        curies = kgNodeIndex.get_KG1_curies(test)
        print(test+" = "+str(curies))
    t1 = timeit.default_timer()
    print("Elapsed time: "+str(t1-t0))

    print("==== Convert CURIEs to requested namespace ============================")
    tests = [ [ "CUI:C0031485", "DOID" ], [ "FMA:7203", "UBERON" ], [ "MESH:D005199", "DOID" ], 
             [ "CHEBI:5855", "CHEMBL.COMPOUND" ], [ "ibuprofen", "CUI" ] ]

    t0 = timeit.default_timer()
    for test in tests:
        curies = kgNodeIndex.convert_curie(test[0], test[1])
        print(f"{test[0]} -> {test[1]} = " + str(curies))
    t1 = timeit.default_timer()
    print("Elapsed time: "+str(t1-t0))

    print("==== Get all known synonyms of a CURIE using KG2 index ============================")
    tests = [ "DOID:14330", "CUI:C0031485", "FMA:7203", "MESH:D005199", "CHEBI:5855", "DOID:9281" ]
    tests = [ "DOID:9281" ]

    t0 = timeit.default_timer()
    for test in tests:
        curies = kgNodeIndex.get_equivalent_curies(test,kg_name='KG1')
        print(f"{test} = " + str(curies))
        curies = kgNodeIndex.get_equivalent_curies(test,kg_name='KG2')
        print(f"{test} = " + str(curies))
        equivalence_mapping = kgNodeIndex.get_equivalent_entities(test,kg_name='KG1')
        print(json.dumps(equivalence_mapping,sort_keys=True,indent=2))
        equivalence_mapping = kgNodeIndex.get_equivalent_entities(test,kg_name='KG2')
        print(json.dumps(equivalence_mapping,sort_keys=True,indent=2))
    t1 = timeit.default_timer()
    print("Elapsed time: "+str(t1-t0))

    print("==== Get total number of drug nodes and disease nodes ============================")
    t0 = timeit.default_timer()
    kg = 'KG1'
    print(kgNodeIndex.get_total_entity_count('chemical_substance', kg_name=kg))
    print(kgNodeIndex.get_total_entity_count('disease', kg_name=kg))
    print(kgNodeIndex.get_total_entity_count('protein', kg_name=kg))
    print(kgNodeIndex.get_total_entity_count('drug', kg_name=kg))
    print(kgNodeIndex.get_total_entity_count('cheesecake', kg_name=kg))
    t1 = timeit.default_timer()
    print("Elapsed time: "+str(t1-t0))

    #print("==== Test SELECT ============================")
    #kgNodeIndex.test_select('phenylketonuria')
    #kgNodeIndex.test_select('CUI:C4710278')
    #kgNodeIndex.test_select('UniProtKB:P06865')
    #print(kgNodeIndex.is_curie_present('CUI:C4710278'))

####################################################################################################
if __name__ == "__main__":
    main()
