"""

How to run this module
$ cd [git repo]/code/reasoningtool/kg-construction
$ python3 PatchKG.py -a         #   add_disease_has_phenotype_relations
$ python3 PatchKG.py -d         #   delete_duplicated_react_nodes
"""


# BEGIN config.json format
# {
#   "url":"bolt://localhost:7687"
#   "username":"xxx",
#   "password":"xxx"
# }
# END config.json format

__author__ = 'Deqing Qu'
__copyright__ = 'Oregon State University'
__credits__ = ['Deqing Qu', 'Stephen Ramsey']
__license__ = 'MIT'
__version__ = '0.1.0'
__maintainer__ = ''
__email__ = ''
__status__ = 'Prototype'

from QueryBioLink import QueryBioLink
from Neo4jConnection import Neo4jConnection
import json
import sys, getopt
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../")  # code directory
from RTXConfiguration import RTXConfiguration

class PatchKG:
    @staticmethod
    def add_disease_has_phenotype_relations():

        # create the RTXConfiguration object
        rtxConfig = RTXConfiguration()

        conn = Neo4jConnection(rtxConfig.neo4j_bolt, rtxConfig.neo4j_username, rtxConfig.neo4j_password)
        disease_nodes = conn.get_disease_nodes()
        print("disease nodes count: " + str(len(disease_nodes)))

        from time import time
        t = time()

        array = []
        for d_id in disease_nodes:
            hp_array = QueryBioLink.map_disease_to_phenotype(d_id)
            if hp_array:
                for hp_id in hp_array:
                    array.append({'d_id': d_id, 'p_id': hp_id})

        print("time for querying: %f" % (time() - t))
        t = time()

        print("relations count = " + str(len(array)))
        nodes_nums = len(array)
        chunk_size = 10000
        group_nums = nodes_nums // chunk_size + 1
        for i in range(group_nums):
            start = i * chunk_size
            end = (i + 1) * chunk_size if (i + 1) * chunk_size < nodes_nums else nodes_nums
            conn.create_disease_has_phenotype(array[start:end])

        print("time for creating relations: %f" % (time() - t))
        t = time()

        #   remove duplicated relations
        conn.remove_duplicate_has_phenotype_relations()
        print("time for remove duplicate relations: %f" % (time() - t))

        conn.close()

    @staticmethod
    def delete_duplicated_react_nodes():

        # create the RTXConfiguration object
        rtxConfig = RTXConfiguration()

        conn = Neo4jConnection(rtxConfig.neo4j_bolt, rtxConfig.neo4j_username, rtxConfig.neo4j_password)

        if conn.count_duplicated_nodes() != 0:
            conn.remove_duplicated_react_nodes()
            if conn.count_duplicated_nodes() != 0:
                print("Delete duplicated reactom nodes unsuccessfully")
            else:
                print("Delete duplicated reactom nodes successfully")
        else:
            print("no duplicated reactom nodes")

        conn.close()


def main(argv):
    try:
        opts, args = getopt.getopt(argv, "had", ["add_has_phenotype_relations", "delete_duplicated_react_nodes"])
    except getopt.GetoptError:
        print("Wrong parameter")
        print("PatchKG.py -a <add_has_phenotype_relations> -d <delete_duplicated_react_nodes>")
        sys.exit(2)
    if len(opts) == 0:
        print("Need parameters")
        print("PatchKG.py -a <add_has_phenotype_relations> -d <delete_duplicated_react_nodes>")
    for opt, arg in opts:
        if opt == '-h':
            print("PatchKG.py -a <add_has_phenotype_relations> -d <delete_duplicated_react_nodes>")
            sys.exit()
        elif opt in ["-a", "--add_has_phenotype_relations"]:
            PatchKG.add_disease_has_phenotype_relations()
        elif opt in ["-d", "--delete_duplicated_react_nodes"]:
            PatchKG.delete_duplicated_react_nodes()


if __name__ == '__main__':
    main(sys.argv[1:])
