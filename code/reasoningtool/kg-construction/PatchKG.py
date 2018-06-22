"""

How to run this module
$ cd [git repo ] /cod e /reasoningtool /kg -construction
$ python3 PatchKG.py
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


class PatchKG:

    @staticmethod
    def add_disease_has_phenotype_relations():

        f = open('config.json', 'r')
        config_data = f.read()
        f.close()
        config = json.loads(config_data)

        conn = Neo4jConnection(config['url'], config['username'], config['password'])
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


if __name__ == '__main__':
    PatchKG.add_disease_has_phenotype_relations()