''' This module defines the class Neo4jConnection. Neo4jConnection class is designed
to connect to Neo4j database and perform operations on a graphic model object. (e.g.,
retrieve node and update node) The available methods include:

    get_xxx_nodes : query all xxx nodes
    update_xxx_nodes : update xxx nodes by an array 'nodes', which contain two properties 'node_id'
                            and 'extended_info_json' for each node
    get_xxx_node : query xxx node by ID

    xxx is the type of nodes. (e.g., anatomy, phenotype, microRNA, pathway, protein, disease)

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

    def get_microRNA_nodes(self):
        with self._driver.session() as session:
            return session.write_transaction(self._get_microRNA_nodes)

    def get_pathway_nodes(self):
        with self._driver.session() as session:
            return session.write_transaction(self._get_pathway_nodes)

    def get_protein_nodes(self):
        with self._driver.session() as session:
            return session.write_transaction(self._get_protein_nodes)

    def get_disease_nodes(self):
        with self._driver.session() as session:
            return session.write_transaction(self._get_disease_nodes)

    def get_chemical_substance_nodes(self):
        with self._driver.session() as session:
            return session.write_transaction(self._get_chemical_substance_nodes)

    def get_bio_process_nodes(self):
        with self._driver.session() as session:
            return session.write_transaction(self._get_bio_process_nodes)

    def update_anatomy_nodes(self, nodes):
        with self._driver.session() as session:
            return session.write_transaction(self._update_anatomy_nodes, nodes)

    def update_phenotype_nodes(self, nodes):
        with self._driver.session() as session:
            return session.write_transaction(self._update_phenotype_nodes, nodes)

    def update_microRNA_nodes(self, nodes):
        with self._driver.session() as session:
            return session.write_transaction(self._update_microRNA_nodes, nodes)

    def update_pathway_nodes(self, nodes):
        with self._driver.session() as session:
            return session.write_transaction(self._update_pathway_nodes, nodes)

    def update_protein_nodes(self, nodes):
        with self._driver.session() as session:
            return session.write_transaction(self._update_protein_nodes, nodes)

    def update_disease_nodes(self, nodes):
        with self._driver.session() as session:
            return session.write_transaction(self._update_disease_nodes, nodes)

    def update_chemical_substance_nodes(self, nodes):
        with self._driver.session() as session:
            return session.write_transaction(self._update_chemical_substance_nodes, nodes)

    def update_bio_process_nodes(self, nodes):
        with self._driver.session() as session:
            return session.write_transaction(self._update_bio_process_nodes, nodes)

    def get_anatomy_node(self, id):
        with self._driver.session() as session:
            return session.write_transaction(self._get_anatomy_node, id)

    def get_phenotype_node(self, id):
        with self._driver.session() as session:
            return session.write_transaction(self._get_phenotype_node, id)

    def get_microRNA_node(self, id):
        with self._driver.session() as session:
            return session.write_transaction(self._get_microRNA_node, id)

    def get_pathway_node(self, id):
        with self._driver.session() as session:
            return session.write_transaction(self._get_pathway_node, id)

    def get_protein_node(self, id):
        with self._driver.session() as session:
            return session.write_transaction(self._get_protein_node, id)

    def get_disease_node(self, id):
        with self._driver.session() as session:
            return session.write_transaction(self._get_disease_node, id)

    def get_chemical_substance_node(self, id):
        with self._driver.session() as session:
            return session.write_transaction(self._get_chemical_substance_node, id)

    def get_bio_process_node(self, id):
        with self._driver.session() as session:
            return session.write_transaction(self._get_bio_process_node, id)

    def update_anatomy_nodes_desc(self, nodes):
        with self._driver.session() as session:
            return session.write_transaction(self._update_anatomy_nodes_desc, nodes)

    def update_phenotype_nodes_desc(self, nodes):
        with self._driver.session() as session:
            return session.write_transaction(self._update_phenotype_nodes_desc, nodes)

    def update_microRNA_nodes_desc(self, nodes):
        with self._driver.session() as session:
            return session.write_transaction(self._update_microRNA_nodes_desc, nodes)

    def update_protein_nodes_desc(self, nodes):
        with self._driver.session() as session:
            return session.write_transaction(self._update_protein_nodes_desc, nodes)

    def update_disease_nodes_desc(self, nodes):
        with self._driver.session() as session:
            return session.write_transaction(self._update_disease_nodes_desc, nodes)

    def update_chemical_substance_nodes_desc(self, nodes):
        with self._driver.session() as session:
            return session.write_transaction(self._update_chemical_substance_nodes_desc, nodes)

    def update_bio_process_nodes_desc(self, nodes):
        with self._driver.session() as session:
            return session.write_transaction(self._update_bio_process_nodes_desc, nodes)

    @staticmethod
    def _get_anatomy_nodes(tx):
        result = tx.run("MATCH (n:anatomical_entity) RETURN n.id")
        return [record["n.id"] for record in result]

    @staticmethod
    def _get_phenotype_nodes(tx):
        result = tx.run("MATCH (n:phenotypic_feature) RETURN n.id")
        return [record["n.id"] for record in result]

    @staticmethod
    def _get_microRNA_nodes(tx):
        result = tx.run("MATCH (n:microRNA) RETURN n.id")
        return [record["n.id"] for record in result]

    @staticmethod
    def _get_pathway_nodes(tx):
        result = tx.run("MATCH (n:pathway) RETURN n.id")
        return [record["n.id"] for record in result]

    @staticmethod
    def _get_protein_nodes(tx):
        result = tx.run("MATCH (n:protein) RETURN n.id")
        return [record["n.id"] for record in result]

    @staticmethod
    def _get_disease_nodes(tx):
        result = tx.run("MATCH (n:disease) RETURN n.id")
        return [record["n.id"] for record in result]

    @staticmethod
    def _get_chemical_substance_nodes(tx):
        result = tx.run("MATCH (n:chemical_substance) RETURN n.id")
        return [record["n.id"] for record in result]

    @staticmethod
    def _get_bio_process_nodes(tx):
        result = tx.run("MATCH (n:biological_process) RETURN n.id")
        return [record["n.id"] for record in result]

    @staticmethod
    def _update_anatomy_nodes(tx, nodes):
        result = tx.run(
            """
            UNWIND {nodes} AS row
            WITH row.node_id AS node_id, row.extended_info_json AS extended_info_json
            MATCH (n:anatomical_entity{id:node_id})
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
            MATCH (n:phenotypic_feature{id:node_id})
            SET n.extended_info_json=extended_info_json
            """,
            nodes=nodes,
        )
        return result

    @staticmethod
    def _update_microRNA_nodes(tx, nodes):
        result = tx.run(
            """
            UNWIND {nodes} AS row
            WITH row.node_id AS node_id, row.extended_info_json AS extended_info_json
            MATCH (n:microRNA{id:node_id})
            SET n.extended_info_json=extended_info_json
            """,
            nodes=nodes,
        )
        return result

    @staticmethod
    def _update_pathway_nodes(tx, nodes):
        result = tx.run(
            """
            UNWIND {nodes} AS row
            WITH row.node_id AS node_id, row.extended_info_json AS extended_info_json
            MATCH (n:pathway{id:node_id})
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
            MATCH (n:protein{id:node_id})
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
            MATCH (n:disease{id:node_id})
            SET n.extended_info_json=extended_info_json
            """,
            nodes=nodes,
        )
        return result

    @staticmethod
    def _update_chemical_substance_nodes(tx, nodes):
        result = tx.run(
            """
            UNWIND {nodes} AS row
            WITH row.node_id AS node_id, row.extended_info_json AS extended_info_json
            MATCH (n:chemical_substance{id:node_id})
            SET n.extended_info_json=extended_info_json
            """,
            nodes=nodes,
        )
        return result

    @staticmethod
    def _update_bio_process_nodes(tx, nodes):
        result = tx.run(
            """
            UNWIND {nodes} AS row
            WITH row.node_id AS node_id, row.extended_info_json AS extended_info_json
            MATCH (n:biological_process{id:node_id})
            SET n.extended_info_json=extended_info_json
            """,
            nodes=nodes,
        )
        return result

    @staticmethod
    def _get_anatomy_node(tx, id):
        result = tx.run("MATCH (n:anatomical_entity{id:'%s'}) RETURN n" % id)
        return result.single()

    @staticmethod
    def _get_phenotype_node(tx, id):
        result = tx.run("MATCH (n:phenotypic_feature{id:'%s'}) RETURN n" % id)
        return result.single()

    @staticmethod
    def _get_microRNA_node(tx, id):
        result = tx.run("MATCH (n:microRNA{id:'%s'}) RETURN n" % id)
        return result.single()

    @staticmethod
    def _get_pathway_node(tx, id):
        result = tx.run("MATCH (n:pathway{id:'%s'}) RETURN n" % id)
        return result.single()

    @staticmethod
    def _get_protein_node(tx, id):
        result = tx.run("MATCH (n:protein{id:'%s'}) RETURN n" % id)
        return result.single()

    @staticmethod
    def _get_disease_node(tx, id):
        result = tx.run("MATCH (n:disease{id:'%s'}) RETURN n" % id)
        return result.single()

    @staticmethod
    def _get_chemical_substance_node(tx, id):
        result = tx.run("MATCH (n:chemical_substance{id:'%s'}) RETURN n" % id)
        return result.single()

    @staticmethod
    def _get_bio_process_node(tx, id):
        result = tx.run("MATCH (n:biological_process{id:'%s'}) RETURN n" % id)
        return result.single()

    @staticmethod
    def _update_anatomy_nodes_desc(tx, nodes):
        result = tx.run(
            """
            UNWIND {nodes} AS row
            WITH row.node_id AS node_id, row.desc AS description
            MATCH (n:anatomical_entity{id:node_id})
            SET n.description=description
            """,
            nodes=nodes,
        )
        return result

    @staticmethod
    def _update_phenotype_nodes_desc(tx, nodes):
        result = tx.run(
            """
            UNWIND {nodes} AS row
            WITH row.node_id AS node_id, row.desc AS description
            MATCH (n:phenotypic_feature{id:node_id})
            SET n.description=description
            """,
            nodes=nodes,
        )
        return result

    @staticmethod
    def _update_microRNA_nodes_desc(tx, nodes):
        result = tx.run(
            """
            UNWIND {nodes} AS row
            WITH row.node_id AS node_id, row.desc AS description
            MATCH (n:microRNA{id:node_id})
            SET n.description=description
            """,
            nodes=nodes,
        )
        return result

    @staticmethod
    def _update_disease_nodes_desc(tx, nodes):
        result = tx.run(
            """
            UNWIND {nodes} AS row
            WITH row.node_id AS node_id, row.desc AS description
            MATCH (n:disease{id:node_id})
            SET n.description=description
            """,
            nodes=nodes,
        )
        return result

    @staticmethod
    def _update_protein_nodes_desc(tx, nodes):
        result = tx.run(
            """
            UNWIND {nodes} AS row
            WITH row.node_id AS node_id, row.desc AS description
            MATCH (n:protein{id:node_id})
            SET n.description=description
            """,
            nodes=nodes,
        )
        return result

    @staticmethod
    def _update_chemical_substance_nodes_desc(tx, nodes):
        result = tx.run(
            """
            UNWIND {nodes} AS row
            WITH row.node_id AS node_id, row.desc AS description
            MATCH (n:chemical_substance{id:node_id})
            SET n.description=description
            """,
            nodes=nodes,
        )
        return result

    @staticmethod
    def _update_bio_process_nodes_desc(tx, nodes):
        result = tx.run(
            """
            UNWIND {nodes} AS row
            WITH row.node_id AS node_id, row.desc AS description
            MATCH (n:biological_process{id:node_id})
            SET n.description=description
            """,
            nodes=nodes,
        )
        return result