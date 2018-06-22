from unittest import TestCase

import os,sys
import json
import random

parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,parentdir)

from Neo4jConnection import Neo4jConnection
from QueryBioLink import QueryBioLink


def random_int_list(start, stop, length):
    start, stop = (int(start), int(stop)) if start <= stop else (int(stop), int(start))
    length = int(abs(length)) if length else 0
    random_list = []
    for i in range(length):
        random_list.append(random.randint(start, stop))
    return random_list


class TestPatchKG(TestCase):
    def test_add_disease_has_phenotype_relations(self):

        f = open('config.json', 'r')
        config_data = f.read()
        f.close()
        config = json.loads(config_data)

        conn = Neo4jConnection(config['url'], config['username'], config['password'])
        disease_nodes = conn.get_disease_nodes()

        # generate random number array
        random_indexes = random_int_list(0, len(disease_nodes) - 1, 10)

        #   query BioLink
        relation_array = []
        for random_index in random_indexes:
            d_id = disease_nodes[random_index]
            hp_array = QueryBioLink.map_disease_to_phenotype(d_id)
            for hp_id in hp_array:
                relation_array.append({"d_id": d_id, "p_id": hp_id})

        #   query Neo4j Database
        for relation_item in relation_array:
            result = conn.count_has_phenotype_relation(relation_item)
            self.assertEqual(result, 1)

        conn.close()
