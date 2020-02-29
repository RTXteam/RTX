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
DEBUG = True
TESTSUFFIX = ""
#TESTSUFFIX = "_test2"


# Main class
class KGNodeIndex:

    # Constructor
    def __init__(self):
        filepath = os.path.dirname(os.path.abspath(__file__))
        self.databaseLocation = filepath

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


    # Delete and create the kgnode table
    def create_database(self):
        if DEBUG is True:
            print("INFO: Creating database "+self.databaseName)
        self.connection.execute(f"DROP TABLE IF EXISTS kgnode{TESTSUFFIX}")
        self.connection.execute(f"CREATE TABLE kgnode{TESTSUFFIX}( curie VARCHAR(255), name VARCHAR(255), type VARCHAR(255) )" )


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


    # Create the KG node table
    def create_node_table(self):

        self.create_database()

        filename = os.path.dirname(os.path.abspath(__file__)) + "/../../../data/KGmetadata/NodeNamesDescriptions.tsv"
        filesize = os.path.getsize(filename)
        previous_percentage = -1
        bytes_read = 0

        lineCounter = 0
        fh = open(filename, 'r', encoding="latin-1", errors="replace")

        # Have a dict for items already inserted so that we don't insert them twice
        # Prefill it with some abbreviations that are too common and we don't want
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

                # Add a row for this node
                rows.append([curie,name,type])
                if debug_flag: print([curie,name,type])
                if name not in namesDict:
                    namesDict[name] = {}
                namesDict[name][curie] = 1

            # Try also adding in the curie as a resolvable name
            if curie not in namesDict:
                rows.append([curie,curie,type])
                if debug_flag: print([curie,curie,type])
                if curie not in namesDict:
                    namesDict[curie] = {}
                namesDict[curie][curie] = 1

            # Commit every 10000 lines
            percentage = int(bytes_read*100.0/filesize)
            if percentage > previous_percentage:
                self.connection.executemany(f"INSERT INTO kgnode{TESTSUFFIX}(curie,name,type) values (?,?,?)", rows)
                self.connection.commit()
                rows = []
                previous_percentage = percentage
                print(str(percentage)+"%..", end='', flush=True)

            debug_flag = False
            lineCounter += 1

        # Write out the last rows
        if len(rows) > 0:
            self.connection.executemany(f"INSERT INTO kgnode{TESTSUFFIX}(curie,name,type) values (?,?,?)", rows)
            self.connection.commit()
            print("100..", end='', flush=True)

        fh.close()
        print("")


    def create_index(self):
        print(f"INFO: Creating INDEX on kgnode{TESTSUFFIX}(name)")
        self.connection.execute(f"CREATE INDEX idx_name ON kgnode{TESTSUFFIX}(name)")
        self.connection.execute(f"CREATE INDEX idx_curie ON kgnode{TESTSUFFIX}(curie)")


    def get_curies_and_types(self, name):
        cursor = self.connection.cursor()
        cursor.execute( f"SELECT * FROM kgnode{TESTSUFFIX} WHERE name = ?", (name.upper(),) )
        rows = cursor.fetchall()
        curies_and_types = []
        for row in rows:
            curies_and_types.append({"curie": row[0], "type": row[2]})
        return curies_and_types


    def get_curies_and_types_and_names(self, name):
        cursor = self.connection.cursor()
        cursor.execute( f"SELECT * FROM kgnode{TESTSUFFIX} WHERE name = ?", (name.upper(),) )
        rows = cursor.fetchall()
        curies_and_types_and_names = []
        for row in rows:
            names = self.get_names(row[0])
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


    def get_names(self, curie):
        cursor = self.connection.cursor()
        cursor.execute( f"SELECT * FROM kgnode{TESTSUFFIX} WHERE curie = ?", (curie,) )
        rows = cursor.fetchall()

        # Return a list of curies
        curies = []
        for row in rows:
            if row[1] == curie:
                continue
            curies.append(row[0])
        return curies


    def get_curies(self, name):
        curies_and_types = self.get_curies_and_types(name)

        if curies_and_types is None:
            return None

        # Return a list of curies
        curies = []
        for curies_and_type in curies_and_types:
            curies.append(curies_and_type["curie"])
        return(curies)


    def is_curie_present(self, curie):
        cursor = self.connection.cursor()
        cursor.execute( f"SELECT * FROM kgnode{TESTSUFFIX} WHERE curie = ?", (curie,) )
        rows = cursor.fetchall()

        if len(rows) == 0:
            return False
        return True


####################################################################################################
def main():
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
        kgNodeIndex.create_node_table()
        kgNodeIndex.create_index()

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


####################################################################################################
if __name__ == "__main__":
    main()
