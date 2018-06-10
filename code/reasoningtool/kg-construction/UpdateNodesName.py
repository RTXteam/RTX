''' This module defines the class UpdateNodesName. UpdateNodesName class is designed
to retrieve the node name and update the name on the Graphic model object.
The available methods include:

*   update_protein_names

    Description: retrieve names from Uniprot and update protein nodes

How to run this module
        $ cd [git repo]/code/reasoningtool/kg-construction
        $ python3 UpdateNodesName.py
'''

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

from Neo4jConnection import Neo4jConnection
from QueryUniprot import QueryUniprot
import json


class UpdateNodesName:

    @staticmethod
    def update_protein_names(protein_ids):

        from time import time
        t = time()

        nodes_array = []
        for protein_id in protein_ids:
            node = dict()
            node['node_id'] = protein_id
            node['name'] = QueryUniprot.get_protein_name(protein_id)
            nodes_array.append(node)

        print("Uniprot api pulling time: %f" % (time() - t))

        f = open('config.json', 'r')
        config_data = f.read()
        f.close()
        config = json.loads(config_data)

        conn = Neo4jConnection(config['url'], config['username'], config['password'])
        conn.update_protein_nodes_name(nodes_array)
        conn.close()

        print("total time: %f" % (time() - t))


if __name__ == '__main__':
    protein_nodes_ids = ['UniProtKB:P01358', 'UniProtKB:P20848', 'UniProtKB:Q9Y471', 'UniProtKB:O60397',
                         'UniProtKB:Q8IZJ3', 'UniProtKB:Q7Z2Y8', 'UniProtKB:Q8IWN7', 'UniProtKB:Q156A1']
    UpdateNodesName.update_protein_names(protein_nodes_ids)