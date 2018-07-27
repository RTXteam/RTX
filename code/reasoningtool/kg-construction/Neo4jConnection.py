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

    def get_cellular_component_nodes(self):
        with self._driver.session() as session:
            return session.write_transaction(self._get_cellular_component_nodes)

    def get_molecular_function_nodes(self):
        with self._driver.session() as session:
            return session.write_transaction(self._get_molecular_function_nodes)

    def get_metabolite_nodes(self):
        with self._driver.session() as session:
            return session.read_transaction(self._get_metabolite_nodes)

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

    def get_node(self, id):
        with self._driver.session() as session:
            return session.write_transaction(self._get_node, id)

    def update_anatomy_nodes_desc(self, nodes):
        with self._driver.session() as session:
            return session.write_transaction(self._update_anatomy_nodes_desc, nodes)

    def update_phenotype_nodes_desc(self, nodes):
        with self._driver.session() as session:
            return session.write_transaction(self._update_phenotype_nodes_desc, nodes)

    def update_microRNA_nodes_desc(self, nodes):
        with self._driver.session() as session:
            return session.write_transaction(self._update_microRNA_nodes_desc, nodes)

    def update_pathway_nodes_desc(self, nodes):
        with self._driver.session() as session:
            return session.write_transaction(self._update_pathway_nodes_desc, nodes)

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

    def update_cellular_component_nodes_desc(self, nodes):
        with self._driver.session() as session:
            return session.write_transaction(self._update_cellular_component_desc, nodes)

    def update_molecular_function_nodes_desc(self, nodes):
        with self._driver.session() as session:
            return session.write_transaction(self._update_molecular_function_desc, nodes)

    def update_protein_nodes_name(self, nodes):
        with self._driver.session() as session:
            return session.write_transaction(self._update_protein_nodes_name, nodes)

    def update_metabolite_nodes_desc(self, nodes):
        with self._driver.session() as session:
            return session.write_transaction(self._update_metabolite_desc, nodes)

    def get_node_names(self, type):
        with self._driver.session() as session:
            return session.write_transaction(self._get_node_names, type)

    def create_disease_has_phenotype(self, array):
        with self._driver.session() as session:
            return session.write_transaction(self.__create_disease_has_phenotype, array)

    def remove_duplicate_has_phenotype_relations(self):
        with self._driver.session() as session:
            return session.write_transaction(self.__remove_duplicate_has_phenotype_relations)

    def count_has_phenotype_relation(self, relation):
        """

        :param relation: {"d_id": "DOID:xxxx", "p_id": "HP:xxxx"}
        :return: count of relations between d_id and p_id
        """
        with self._driver.session() as session:
            return session.write_transaction(self.__count_has_phenotype_relation, relation)

    def remove_duplicated_react_nodes(self):
        with self._driver.session() as session:
            return session.write_transaction(self.__remove_duplicated_react_nodes)

    def count_duplicated_nodes(self):
        with self._driver.session() as session:
            return session.write_transaction(self.__count_duplicated_nodes)

    @staticmethod
    def _get_anatomy_nodes(tx):
        result = tx.run("MATCH (n:anatomical_entity) RETURN n.rtx_name")
        return [record["n.rtx_name"] for record in result]

    @staticmethod
    def _get_phenotype_nodes(tx):
        result = tx.run("MATCH (n:phenotypic_feature) RETURN n.rtx_name")
        return [record["n.rtx_name"] for record in result]

    @staticmethod
    def _get_microRNA_nodes(tx):
        result = tx.run("MATCH (n:microRNA) RETURN n.rtx_name")
        return [record["n.rtx_name"] for record in result]

    @staticmethod
    def _get_pathway_nodes(tx):
        result = tx.run("MATCH (n:pathway) RETURN n.rtx_name")
        return [record["n.rtx_name"] for record in result]

    @staticmethod
    def _get_protein_nodes(tx):
        result = tx.run("MATCH (n:protein) RETURN n.id")
        return [record["n.id"] for record in result]

    @staticmethod
    def _get_disease_nodes(tx):
        result = tx.run("MATCH (n:disease) RETURN n.rtx_name")
        return [record["n.rtx_name"] for record in result]

    @staticmethod
    def _get_chemical_substance_nodes(tx):
        result = tx.run("MATCH (n:chemical_substance) RETURN n.rtx_name")
        return [record["n.rtx_name"] for record in result]

    @staticmethod
    def _get_bio_process_nodes(tx):
        result = tx.run("MATCH (n:biological_process) RETURN n.rtx_name")
        return [record["n.rtx_name"] for record in result]

    @staticmethod
    def _get_cellular_component_nodes(tx):
        result = tx.run("MATCH (n:cellular_component) RETURN n.rtx_name")
        return [record["n.rtx_name"] for record in result]

    @staticmethod
    def _get_molecular_function_nodes(tx):
        result = tx.run("MATCH (n:molecular_function) RETURN n.rtx_name")
        return [record["n.rtx_name"] for record in result]

    @staticmethod
    def _get_metabolite_nodes(tx):
        result = tx.run("MATCH (n:metabolite) RETURN n.rtx_name")
        return [record["n.rtx_name"] for record in result]

    @staticmethod
    def _update_anatomy_nodes(tx, nodes):
        result = tx.run(
            """
            UNWIND {nodes} AS row
            WITH row.node_id AS node_id, row.extended_info_json AS extended_info_json
            MATCH (n:anatomical_entity{rtx_name:node_id})
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
            MATCH (n:phenotypic_feature{rtx_name:node_id})
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
            MATCH (n:microRNA{rtx_name:node_id})
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
            MATCH (n:pathway{rtx_name:node_id})
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
            MATCH (n:disease{rtx_name:node_id})
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
            MATCH (n:chemical_substance{rtx_name:node_id})
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
            MATCH (n:biological_process{rtx_name:node_id})
            SET n.extended_info_json=extended_info_json
            """,
            nodes=nodes,
        )
        return result

    @staticmethod
    def _get_anatomy_node(tx, id):
        result = tx.run("MATCH (n:anatomical_entity{rtx_name:'%s'}) RETURN n" % id)
        return result.single()

    @staticmethod
    def _get_phenotype_node(tx, id):
        result = tx.run("MATCH (n:phenotypic_feature{rtx_name:'%s'}) RETURN n" % id)
        return result.single()

    @staticmethod
    def _get_microRNA_node(tx, id):
        result = tx.run("MATCH (n:microRNA{rtx_name:'%s'}) RETURN n" % id)
        return result.single()

    @staticmethod
    def _get_pathway_node(tx, id):
        result = tx.run("MATCH (n:pathway{rtx_name:'%s'}) RETURN n" % id)
        return result.single()

    @staticmethod
    def _get_protein_node(tx, id):
        result = tx.run("MATCH (n:protein{id:'%s'}) RETURN n" % id)
        return result.single()

    @staticmethod
    def _get_disease_node(tx, id):
        result = tx.run("MATCH (n:disease{rtx_name:'%s'}) RETURN n" % id)
        return result.single()

    @staticmethod
    def _get_chemical_substance_node(tx, id):
        result = tx.run("MATCH (n:chemical_substance{rtx_name:'%s'}) RETURN n" % id)
        return result.single()

    @staticmethod
    def _get_bio_process_node(tx, id):
        result = tx.run("MATCH (n:biological_process{rtx_name:'%s'}) RETURN n" % id)
        return result.single()

    @staticmethod
    def _get_node(tx, id):
        result = tx.run("MATCH (n{rtx_name:'%s'}) RETURN n" % id)
        return result.single()

    @staticmethod
    def _update_anatomy_nodes_desc(tx, nodes):
        result = tx.run(
            """
            UNWIND {nodes} AS row
            WITH row.node_id AS node_id, row.desc AS description
            MATCH (n:anatomical_entity{rtx_name:node_id})
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
            MATCH (n:phenotypic_feature{rtx_name:node_id})
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
            MATCH (n:microRNA{rtx_name:node_id})
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
            MATCH (n:disease{rtx_name:node_id})
            SET n.description=description
            """,
            nodes=nodes,
        )
        return result

    @staticmethod
    def _update_pathway_nodes_desc(tx, nodes):
        result = tx.run(
            """
            UNWIND {nodes} AS row
            WITH row.node_id AS node_id, row.desc AS description
            MATCH (n:pathway{rtx_name:node_id})
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
            MATCH (n:chemical_substance{rtx_name:node_id})
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
            MATCH (n:biological_process{rtx_name:node_id})
            SET n.description=description
            """,
            nodes=nodes,
        )
        return result

    @staticmethod
    def _update_cellular_component_desc(tx, nodes):
        result = tx.run(
            """
            UNWIND {nodes} AS row
            WITH row.node_id AS node_id, row.desc AS description
            MATCH (n:cellular_component{rtx_name:node_id})
            SET n.description=description
            """,
            nodes=nodes,
        )
        return result

    @staticmethod
    def _update_molecular_function_desc(tx, nodes):
        result = tx.run(
            """
            UNWIND {nodes} AS row
            WITH row.node_id AS node_id, row.desc AS description
            MATCH (n:molecular_function{rtx_name:node_id})
            SET n.description=description
            """,
            nodes=nodes,
        )
        return result

    @staticmethod
    def _update_protein_nodes_name(tx, nodes):
        result = tx.run(
            """
            UNWIND {nodes} AS row
            WITH row.node_id AS node_id, row.name AS name
            MATCH (n:protein{id:node_id})
            SET n.name=name
            """,
            nodes=nodes,
        )
        return result

    @staticmethod
    def _update_metabolite_desc(tx, nodes):
        result = tx.run(
            """
            UNWIND {nodes} AS row
            WITH row.node_id AS node_id, row.desc AS description
            MATCH (n:metabolite{rtx_name:node_id})
            SET n.description=description
            """,
            nodes=nodes,
        )
        return result

    @staticmethod
    def _get_node_names(tx, type):
        result = tx.run("MATCH (n:%s) RETURN n.name" % type)
        return [record["n.name"] for record in result]

    @staticmethod
    def __create_disease_has_phenotype(tx, array):
        result = tx.run(
            """
            UNWIND {array} AS row
            WITH row.d_id AS d_id, row.p_id AS p_id
            MATCH (d:disease {rtx_name:d_id}), (p:phenotypic_feature {rtx_name:p_id})
            CREATE (d)-[:has_phenotype {
                source_node_uuid: d.UUID, 
                target_node_uuid: p.UUID,
                is_defined_by: \'RTX\',
                provided_by: \'BioLink\',
                predicate: \'has_phenotype\',
                seed_node_uuid: d.seed_node_uuid,
                relation: \'has_phenotype\'  
            }]->(p)
            """,
            array=array
        )
        return result

    @staticmethod
    def __remove_duplicate_has_phenotype_relations(tx):
        result = tx.run(
            """
            MATCH (a)-[r:has_phenotype]->(b)  
            WITH a, b, TAIL (COLLECT (r)) as rr  
            WHERE size(rr)>0  
            FOREACH (r IN rr | DELETE r)
            """
        )
        return result

    @staticmethod
    def __count_has_phenotype_relation(tx, relation):
        result = tx.run(
            """
            MATCH p = (a {rtx_name:$relation.d_id})-[r:has_phenotype]->(b {rtx_name:$relation.p_id})
            RETURN count(p)
            """,
            relation=relation
        )
        return result.single()['count(p)']

    @staticmethod
    def __remove_duplicated_react_nodes(tx):
        result = tx.run(
            """
            MATCH (n), (m) 
            WHERE n<>m AND n.id=m.id AND split(n.rtx_name, ':')[0] = 'REACT'
            DELETE n
            """
        )
        return result

    @staticmethod
    def __count_duplicated_nodes(tx):
        result = tx.run(
            """
            MATCH (n), (m)
            WHERE n<>m AND n.id=m.id return count(*)
            """,
        )
        return result.single()['count(*)']
