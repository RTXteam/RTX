## Development python script for NCATS Translator Reasoning Tool Q1
## Author: Stephen Ramsey, OSU

import neo4j.v1
import uuid;

class Orangeboard:
    ORANGEBOARD_NEO4J_USERNAME="neo4j"
    ORANGEBOARD_NEO4J_PASSWORD="precisionmedicine"
    ORANGEBOARD_NEO4J_URL="bolt://localhost:7687"
    debug=True

    def __init__(self):
        self.driver = neo4j.v1.GraphDatabase.driver(self.ORANGEBOARD_NEO4J_URL,
                                                    auth=(self.ORANGEBOARD_NEO4J_USERNAME,
                                                          self.ORANGEBOARD_NEO4J_PASSWORD))
        self.session = self.driver.session()

    def __del__(self):
        self.driver.close()
        
    def run_cypher_query(self, query_string):
        """runs a single cypher query in the neo4j database (without a transaction) and returns the result object
        :param query_string: a ``str`` object containing a single cypher query (without a semicolon)
        :returns: a `neo4j.v1.SessionResult` object resulting from executing the neo4j query
        """
        assert (';' not in query_string)
        if (self.debug): print(query_string)
        return(self.driver.session().run(query_string))

    def make_property_string_from_dict(property_info):
        """takes a ``dict`` of property key-value pairs and converts it into a string in Neo4j format

        :param property_info: a ``dict`` of property key-value pairs
        :returns: a string representaiotn of the property key-value pairs, in Neo4j format like this:
        UUID:'97b47364-b9c2-11e7-ac88-a820660158fd', name:'prot1'
        """
        return("{" + (', '.join("{!s}:{!r}".format(key,val) for (key,val) in property_info.items())) + "}" if len(property_info) > 0 else '')

    def create_uuid_index(self):
        """creates a neo4j index on the node property UUID for node label Base

        :returns: nothing
        """
        self.run_cypher_query("CREATE INDEX ON :Base(UUID)")
        
    def clear_orangeboard(self):
        """deletes all nodes and relationships in the orangeboard

        :returns: nothing
        """
        self.run_cypher_query("MATCH (n) DETACH DELETE n")
    
    def add_rel(self, node1_uuid, node2_uuid, rel_type_name, rel_is_directed, rel_properties=dict()):
        """creates one relationship (either directed or undirected) for two nodes (specified by UUID) with user-defined type name and properties

        :param node1_uuid: ``str``, the UUID property of node 1
        :param node2_uuid: ``str``, the UUID property of node 2
        :param rel_type_name: ``str``, the relationship type name (must be a valid Neo4j relationship name)
        :param rel_is_directed: ``bool``, ``True`` means the relationship is directed (``node1``->``node2``), ``False`` means the relationship is undirected
        :param rel_properties: ``dict``, containing the relationship properties (the keys of the ``dict`` should be valid Neo4j property names; the dict cannot contain an entry with the name ``UUID``)
        :returns: nothing
        """
        rel_properties = dict(rel_properties)
        assert type(node1_uuid) == str
        assert type(node2_uuid) == str
        assert type(rel_type_name) == str
        assert type(rel_properties) == dict
        assert "UUID" not in rel_properties.keys()
        assert type(rel_is_directed) == bool
        rel_uuid = str(uuid.uuid1())
        rel_properties['UUID']=rel_uuid
        property_string = Orangeboard.make_property_string_from_dict(rel_properties)
        dir_string = '>' if rel_is_directed else ''
        cypher_query = ("MATCH (n1:Base {UUID:'" + node1_uuid + "'}), (n2:Base {UUID:'" + node2_uuid + "'}) " + 
                        "CREATE (n1)-[:" + rel_type_name + property_string + "]-" + dir_string + "(n2)")

        ## run the query
        self.run_cypher_query(cypher_query)
        
        return(rel_uuid)

    def query_rel_by_uuid(self, rel_uuid):
        """returns a ``list`` of information about a user-specified relationship (specified by UUID)
        :param rel_uuid: a ``str`` specifying the UUID of the relationship to query
        :returns: a ``list`` with information about a relationship, in this format:
        [('r', <Relationship id=160 start=249 end=58 type='regulates' properties={'UUID': '8a09aa3a-b9c1-11e7-a4b2-a820660158fd'}>)]
        """
        assert type(rel_uuid)==str
        cypher_query="MATCH (n:Base)-[r]-(m:Base) WHERE r.UUID='" + rel_uuid + "' AND ID(n)>ID(m) RETURN r"
        res = self.run_cypher_query(cypher_query)
        record = res.single()
        return(list(record.items()))
        
    def query_node_by_uuid(self, node_uuid):
        """returns a ``list`` of information about a user-specified node (specified by UUID)
        
        :param node_uuid: type ``str``, contains the UUID of the node about which you want to query
        :returns: a ``list`` with information about the node, in this format:
        ``[('n', <Node id=193 labels={'Base'} properties={'UUID': '6f34c368-b9bd-11e7-a1dc-a820660158fd', 'name': 'prot1'}>)]``
        """
        assert type(node_uuid)==str
        assert len(node_uuid) > 0
        cypher_query = "MATCH (n:Base) WHERE n.UUID='" + node_uuid + "' RETURN n"
        res = self.run_cypher_query(cypher_query)
        record = res.single()
        return(list(record.items()))
        
    def add_node(self, node_labels=set(), node_properties=dict()):
        """creates one node in the neo4j database, with user-defined labels and properties

        :param node_labels: a ``set`` containing strings which are to be the node labels (which cannot contain the string "Base"); strings must be valid neo4j label names (for no labels, pass an empty ``set``)
        :param node_properties: a ``dict`` containing property key-value pairs (which cannot contain the string "UUID"); keys must be valid neo4j property key names (for no properties, pass an empty ``dict``)
        :returns: a ``neo4j.v1.Record`` containing the UUID of the node that has been added ``<Record n.UUID=uuid_str>`` where for instance, ``uuid_str`` could be 'db07f364-b99f-11e7-b456-a820660158fd'.
        """

        node_labels = node_labels.copy()
        node_properties = node_properties.copy()
        
        assert type(node_labels) == set
        print(node_labels)
        assert "Base" not in node_labels.copy()
        assert type(node_properties) == dict
        assert "UUID" not in node_properties.keys()
        node_labels.add("Base")
        node_uuid=str(uuid.uuid1())
        node_properties['UUID']=node_uuid
        ## construct the label clause of the cypher query
        label_string = ':' + ':'.join(node_labels) if len(node_labels) > 0 else ''
        ## construct the properties clause of the cypher query
        property_string =  Orangeboard.make_property_string_from_dict(node_properties) 
        cypher_query = "CREATE (n" + label_string + " " + property_string + ")"
        ## run the query
        self.run_cypher_query(cypher_query)
        return(node_uuid)

        
## function to put a node in Neo4j
ob = Orangeboard()
ob.clear_orangeboard()
ob.create_uuid_index()
node1_uuid = ob.add_node(set(), {"name": "prot1"})
node2_uuid = ob.add_node(set(), {"name": "prot2"})
rel_uuid = ob.add_rel(node1_uuid, node2_uuid, "regulates", True)
print(ob.query_node_by_uuid(node1_uuid))
print(ob.query_rel_by_uuid(rel_uuid))
