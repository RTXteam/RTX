''' This module defines the class Neo4jConnection. Neo4jConnection class is designed
to connect to Neo4j database and perform operations on a graphic model object. (e.g.,
retrieve node and update node)
'''

__author__ = 'Deqing Qu'
__copyright__ = 'Oregon State University'
__credits__ = ['Deqing Qu', 'Stephen Ramsey']
__license__ = 'MIT'
__version__ = '0.1.0'
__maintainer__ = ''
__email__ = ''
__status__ = 'Prototype'

from neo4j.v1 import GraphDatabase


class Neo4jConnection:

    def __init__(self, uri, user, password):
        self._driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self._driver.close()

    def get_anatomy_nodes(self):
        with self._driver.session() as session:
            return session.write_transaction(self._get_anatomy_nodes)

    def get_phenotype_nodes(self):
        with self._driver.session() as session:
            return session.write_transaction(self._get_phenotype_nodes)

    def get_protein_nodes(self):
        with self._driver.session() as session:
            return session.write_transaction(self._get_protein_nodes)

    def get_disease_nodes(self):
        with self._driver.session() as session:
            return session.write_transaction(self._get_disease_nodes)

    def update_anatomy_nodes(self, nodes):
        with self._driver.session() as session:
            return session.write_transaction(self._update_anatomy_nodes, nodes)

    def update_phenotype_nodes(self, nodes):
        with self._driver.session() as session:
            return session.write_transaction(self._update_phenotype_nodes, nodes)

    def update_protein_nodes(self, nodes):
        with self._driver.session() as session:
            return session.write_transaction(self._update_protein_nodes, nodes)

    def update_disease_nodes(self, nodes):
        with self._driver.session() as session:
            return session.write_transaction(self._update_disease_nodes, nodes)

    def get_anatomy_node(self, id):
        with self._driver.session() as session:
            return session.write_transaction(self._get_anatomy_node, id)

    def get_phenotype_node(self, id):
        with self._driver.session() as session:
            return session.write_transaction(self._get_phenotype_node, id)

    def get_protein_node(self, id):
        with self._driver.session() as session:
            return session.write_transaction(self._get_protein_node, id)

    def get_disease_node(self, id):
        with self._driver.session() as session:
            return session.write_transaction(self._get_disease_node, id)

    @staticmethod
    def _get_anatomy_nodes(tx):
        result = tx.run("MATCH (n:anatomical_entity) RETURN n.name LIMIT 900")
        return [record["n.name"] for record in result]

    @staticmethod
    def _get_phenotype_nodes(tx):
        result = tx.run("MATCH (n:phenotypic_feature) RETURN n.name LIMIT 900")
        return [record["n.name"] for record in result]

    @staticmethod
    def _get_protein_nodes(tx):
        result = tx.run("MATCH (n:protein) RETURN n.curie_id LIMIT 900")
        return [record["n.curie_id"] for record in result]

    @staticmethod
    def _get_disease_nodes(tx):
        result = tx.run("MATCH (n:disease) RETURN n.name LIMIT 900")
        return [record["n.name"] for record in result]

    @staticmethod
    def _update_anatomy_nodes(tx, nodes):
        result = tx.run(
            """
            UNWIND {nodes} AS row
            WITH row.node_id AS node_id, row.extended_info_json AS extended_info_json
            MATCH (n:anatomical_entity{name:node_id})
            SET n.extended_info_json=extended_info_json
            """,
            nodes=nodes,
        )
        return result

    @staticmethod
    def _update_phenotype_nodes(tx, nodes):
        result = tx.run(
            """
            UNWIND {nodes} AS row
            WITH row.node_id AS node_id, row.extended_info_json AS extended_info_json
            MATCH (n:phenotypic_feature{name:node_id})
            SET n.extended_info_json=extended_info_json
            """,
            nodes=nodes,
        )
        return result

    @staticmethod
    def _update_protein_nodes(tx, nodes):
        result = tx.run(
            """
            UNWIND {nodes} AS row
            WITH row.node_id AS node_id, row.extended_info_json AS extended_info_json
            MATCH (n:protein{curie_id:node_id})
            SET n.extended_info_json=extended_info_json
            """,
            nodes=nodes,
        )
        return result

    @staticmethod
    def _update_disease_nodes(tx, nodes):
        result = tx.run(
            """
            UNWIND {nodes} AS row
            WITH row.node_id AS node_id, row.extended_info_json AS extended_info_json
            MATCH (n:disease{name:node_id})
            SET n.extended_info_json=extended_info_json
            """,
            nodes=nodes,
        )
        return result

    @staticmethod
    def _get_anatomy_node(tx, id):
        result = tx.run("MATCH (n:anatomical_entity{name:'%s'}) RETURN n" % id)
        return result.single()

    @staticmethod
    def _get_phenotype_node(tx, id):
        result = tx.run("MATCH (n:phenotypic_feature{name:'%s'}) RETURN n" % id)
        return result.single()

    @staticmethod
    def _get_protein_node(tx, id):
        result = tx.run("MATCH (n:protein{curie_id:'%s'}) RETURN n" % id)
        return result.single()

    @staticmethod
    def _get_disease_node(tx, id):
        result = tx.run("MATCH (n:disease{name:'%s'}) RETURN n" % id)
        return result.single()