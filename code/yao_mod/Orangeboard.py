# An implementation of a Blackboard class
# Author: Yao Yao, OSU

import uuid
import neo4j.v1
from .OrangeboardNode import OrangeboardNode


class Orangeboard:
    NEO4J_USERNAME = "neo4j"
    NEO4J_PASSWORD = "precisionmedicine"
    NEO4J_URL = "bolt://localhost:7687"

    def __init__(self, debug=False):
        self.debug = debug

        self.driver = neo4j.v1.GraphDatabase.driver(Orangeboard.NEO4J_URL,
                                                    auth=(Orangeboard.NEO4J_USERNAME,
                                                          Orangeboard.NEO4J_PASSWORD))
        self.session = self.driver.session()

    def shutdown(self):
        """shuts down the Orangeboard by disconnecting from the Neo4j database

        :returns: nothing
        """
        self.session.close()
        self.driver.close()

    def run_cypher_query(self, query_string):
        """runs a single cypher query in the neo4j database (without a transaction) and returns the result object

        :param query_string: a ``str`` object containing a single cypher query (without a semicolon)
        :returns: a `neo4j.v1.SessionResult` object resulting from executing the neo4j query
        """
        if self.debug:
            print("[Orangeboard::Debug] " + query_string)

        assert (';' not in query_string)

        return self.session.run(query_string)

    @staticmethod
    def make_property_string_from_dict(property_info):
        """takes a ``dict`` of property key-value pairs and converts it into a string in Neo4j format

        :param property_info: a ``dict`` of property key-value pairs
        :returns: a string representaiotn of the property key-value pairs, in Neo4j format like this:
        UUID:'97b47364-b9c2-11e7-ac88-a820660158fd', name:'prot1'
        """
        if len(property_info) > 0:
            return "{" + (', '.join("{!s}:{!r}".format(key, val) for (key, val) in property_info.items())) + "}"
        else:
            return ''

    @staticmethod
    def make_label_string_from_set(node_labels):
        if len(node_labels) > 0:
            return ':' + ':'.join(node_labels)
        else:
            return ''

    @staticmethod
    def make_dir_string_from_bool(rel_is_directed):
        return '>' if rel_is_directed else ''

    def create_uuid_index(self):
        """creates a neo4j index on the node property UUID for node label Base

        :returns: nothing
        """
        self.run_cypher_query("CREATE INDEX ON :Base(UUID)")

    def clear(self):
        """deletes all nodes and relationships in the orangeboard

        :returns: nothing
        """
        self.run_cypher_query("MATCH (n) DETACH DELETE n")

    def add_rel(self, node1_uuid, node2_uuid, rel_type_name, rel_is_directed, rel_properties=None):
        """creates one relationship (either directed or undirected) for two nodes (specified by UUID) with user-defined type name and properties

        :param node1_uuid: ``str``, the UUID property of node 1
        :param node2_uuid: ``str``, the UUID property of node 2
        :param rel_type_name: ``str``, the relationship type name (must be a valid Neo4j relationship name)
        :param rel_is_directed: ``bool``, ``True`` means the relationship is directed (``node1``->``node2``), ``False`` means the relationship is undirected
        :param rel_properties: ``dict``, containing the relationship properties (the keys of the ``dict`` should be valid Neo4j property names; the dict cannot contain an entry with the name ``UUID``)
        :returns: nothing
        """
        if rel_properties is None:
            rel_properties = dict()

        assert type(node1_uuid) == str
        assert type(node2_uuid) == str
        assert type(rel_type_name) == str
        assert type(rel_properties) == dict
        assert "UUID" not in rel_properties.keys()
        assert type(rel_is_directed) == bool

        rel_uuid = str(uuid.uuid1())
        rel_properties['UUID'] = rel_uuid
        property_string = Orangeboard.make_property_string_from_dict(rel_properties)
        dir_string = Orangeboard.make_dir_string_from_bool(rel_is_directed)
        cypher_query = ("MATCH (n1:Base {UUID:'" + node1_uuid + "'}), (n2:Base {UUID:'" + node2_uuid + "'}) " +
                        "CREATE (n1)-[:" + rel_type_name + property_string + "]-" + dir_string + "(n2)")

        self.run_cypher_query(cypher_query)

        return rel_uuid

    # See https://github.com/neo4j/neo4j-python-driver/blob/1.6/neo4j/v1/api.py#L636 for more methods of StatementResult
    def query_rel_by_uuid(self, rel_uuid):
        """returns a neo4j relationship object specified by UUID"""
        assert type(rel_uuid) == str

        cypher_query = "MATCH (n:Base)-[r]-(m:Base) WHERE r.UUID='" + rel_uuid + "' AND ID(n)>ID(m) RETURN r"
        res = self.run_cypher_query(cypher_query)
        record = res.single()
        return record['r']

    # See https://github.com/neo4j/neo4j-python-driver/blob/1.6/neo4j/v1/api.py#L636 for more methods of StatementResult
    def query_node_by_uuid(self, node_uuid):
        """returns a OrangeboardNode object specified by UUID
        """
        assert type(node_uuid) == str
        assert len(node_uuid) > 0

        cypher_query = "MATCH (n:Base) WHERE n.UUID='" + node_uuid + "' RETURN n"
        res = self.run_cypher_query(cypher_query)
        record = res.single()
        return OrangeboardNode(record["n"])

    def add_node(self, node_labels=None, node_properties=None):
        """creates one node in the neo4j database, with user-defined labels and properties

        :param node_labels: a ``set`` containing strings which are to be the node labels (which cannot contain the string "Base"); strings must be valid neo4j label names (for no labels, pass an empty ``set``)
        :param node_properties: a ``dict`` containing property key-value pairs (which cannot contain the string "UUID"); keys must be valid neo4j property key names (for no properties, pass an empty ``dict``)
        :returns: a ``neo4j.v1.Record`` containing the UUID of the node that has been added ``<Record n.UUID=uuid_str>`` where for instance, ``uuid_str`` could be 'db07f364-b99f-11e7-b456-a820660158fd'.
        """

        if node_labels is None:
            node_labels = set()

        if node_properties is None:
            node_properties = dict()

        assert type(node_labels) == set
        assert "Base" not in node_labels
        assert type(node_properties) == dict
        assert "UUID" not in node_properties.keys()

        node_labels.add("Base")

        node_uuid = str(uuid.uuid1())
        node_properties['UUID'] = node_uuid

        # construct the label clause of the cypher query
        label_string = Orangeboard.make_label_string_from_set(node_labels)
        # construct the properties clause of the cypher query
        property_string = Orangeboard.make_property_string_from_dict(node_properties)

        cypher_query = "CREATE (n" + label_string + " " + property_string + ")"
        self.run_cypher_query(cypher_query)

        return node_uuid

    def set_node_property(self, node_uuid, property_name, property_value):
        """sets a single property value on a single node; intended to be used to set the property "expanded" to "true"
        
        :param node_uuid: a ``string`` containing the UUID of the node
        :param property_name: a ``string`` containing the name of the property (must be a valid Neo4j property name);
        this string parameter cannot have the value "UUID" since the Orangeboard won't allow a UUID to be changed
        :param property_value: a ``string`` containing the name of the property "value"
        :returns: nothing
        """
        assert type(node_uuid) == str
        assert type(property_name) == str
        assert property_name != "UUID"
        assert type(property_value) == str

        cypher_query = "MATCH (n {{UUID: '{node_uuid}'}}) SET n.{property_name} = '{property_value}'"\
            .format(node_uuid=node_uuid, property_name=property_name, property_value=property_value)

        self.run_cypher_query(cypher_query)

    def get_all_nodes(self):
        """returns a list of ``OrangeboardNode`` objects describing all nodes in the Orangeboard

        :returns: a ``list`` of ``OrangeboardNode`` objects, each describing the labels and attributes of a node
        """
        cypher_query = "MATCH (n) RETURN n"
        res = self.run_cypher_query(cypher_query)
        neo4j_node_list = [record['n'] for record in res]
        ob_node_list = [OrangeboardNode(neo4j_node) for neo4j_node in neo4j_node_list]

        return ob_node_list

    @staticmethod
    def test():
        # function to put a node in Neo4j
        ob = Orangeboard(debug=True)
        ob.clear()
        ob.create_uuid_index()

        node1_uuid = ob.add_node({"uniprot"}, {"name": "prot1"})
        node2_uuid = ob.add_node({"reactome"}, {"name": "prot2"})
        node1 = ob.query_node_by_uuid(node1_uuid)
        node2 = ob.query_node_by_uuid(node2_uuid)

        assert node1.get_bioname() == "prot1"
        assert node1.get_biotype() == "uniprot"
        assert node1.get_uuid() == node1_uuid
        assert node2.get_bioname() == "prot2"
        assert node2.get_biotype() == "reactome"
        assert node2.get_uuid() == node2_uuid

        rel_uuid = ob.add_rel(node1_uuid, node2_uuid, "regulates", True)
        rel = ob.query_rel_by_uuid(rel_uuid)

        assert rel.type == 'regulates'
        assert rel.properties['UUID'] == rel_uuid

        all_nodes = ob.get_all_nodes()
        assert node1 in all_nodes
        assert node2 in all_nodes

        ob.shutdown()

        print("----- All assertions hold! -----")
