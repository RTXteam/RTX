import uuid
import pprint
import neo4j.v1


class Node:
    def __init__(self, nodetype, name, seed_node):
        self.nodetype = nodetype
        self.name = name
        if seed_node is not None:
            self.seed_node = seed_node
        else:
            self.seed_node = self
        new_uuid = str(uuid.uuid1())
        self.uuid = new_uuid
        self.out_rels = set()
        self.in_rels = set()
        self.expanded = False
        self.desc = ''

    def set_desc(self, desc):
        self.desc = desc

    def get_props(self):
        return {'UUID': self.uuid,
                'name': self.name,
                'seed_node_uuid': self.seed_node.uuid,
                'expanded': self.expanded,
                'description': self.desc}

    def get_labels(self):
        return {'Base', self.nodetype}

    def __str__(self):
        attr_list = ["nodetype", "name", "uuid", "expanded", "desc"]
        attr_dict = {attr: str(self.__getattribute__(attr)) for attr in attr_list}

        return pprint.pformat(attr_dict)


class Rel:
    def __init__(self, reltype, sourcedb, source_node, target_node, seed_node):
        self.reltype = reltype
        self.sourcedb = sourcedb
        self.source_node = source_node
        self.target_node = target_node
        self.seed_node = seed_node
        new_uuid = str(uuid.uuid1())
        self.uuid = new_uuid
        source_node.out_rels.add(self)
        target_node.in_rels.add(self)

    def get_props(self):
        return {'UUID': self.uuid,
                'reltype': self.reltype,
                'sourcedb': self.sourcedb,
                'seed_node_uuid': self.seed_node.uuid,
                'source_node_uuid': self.source_node.uuid,
                'target_node_uuid': self.target_node.uuid}

    def __str__(self):
        attr_list = ["reltype", "sourcedb", "uuid", "source_node", "target_node"]
        attr_dict = {attr: str(self.__getattribute__(attr)) for attr in attr_list}

        return pprint.pformat(attr_dict)


class Orangeboard:
    NEO4J_USERNAME = "neo4j"
    NEO4J_PASSWORD = "precisionmedicine"
    NEO4J_URL = "bolt://localhost:7687"

    def __init__(self, dict_reltype_dirs, debug=False):
        self.dict_nodetype_to_dict_name_to_node = dict()
        self.dict_reltype_to_dict_relkey_to_rel = dict()
        self.dict_seed_uuid_to_list_nodes = dict()
        self.dict_seed_uuid_to_list_rels = dict()
        self.debug = debug
        self.seed_node = None
        self.dict_reltype_dirs = dict_reltype_dirs

    def count_rels_for_node_slow(self, node):
        node_uuid = node.uuid
        count = 0
        for subdict in self.dict_reltype_to_dict_relkey_to_rel.values():
            for rel in subdict.values():
                if rel.source_node.uuid == node_uuid or rel.target_node.uuid == node_uuid:
                    count += 1
        return count
        
    def count_nodes(self):
        count = 0
        for seed_uuid in self.dict_seed_uuid_to_list_nodes.keys():
            count += len(self.dict_seed_uuid_to_list_nodes[seed_uuid])
        return count

    def count_rels(self):
        count = 0
        for seed_uuid in self.dict_seed_uuid_to_list_rels.keys():
            count += len(self.dict_seed_uuid_to_list_rels[seed_uuid])
        return count

    def set_seed_node(self, seed_node):
        self.seed_node = seed_node
        
    def get_node(self, nodetype, name):
        subdict = self.dict_nodetype_to_dict_name_to_node.get(nodetype, None)
        ret_node = None
        if subdict is not None:
            existing_node_match = subdict.get(name, None)
            if existing_node_match is not None:
                ## this node already exists, return the Node
                ret_node = existing_node_match
        return ret_node

    def get_all_nodes_for_seed_node_uuid(self, seed_node_uuid):
        return set(self.dict_seed_uuid_to_list_nodes[seed_node_uuid])

    def get_all_rels_for_seed_node_uuid(self, seed_node_uuid):
        list_rels = self.dict_seed_uuid_to_list_rels.get(seed_node_uuid, None)
        if list_rels is not None:
            return set(list_rels)
        else:
            return set()
    
    def get_all_nodes_for_current_seed_node(self):
        return self.get_all_nodes_for_seed_node_uuid(self.seed_node.uuid)

    def get_all_reltypes(self):
        return self.dict_reltype_to_dict_relkey_to_rel.keys()

    def get_all_rels_for_reltype(self, reltype):
        return set(self.dict_reltype_to_dict_relkey_to_rel[reltype].values())
    
    def get_all_nodetypes(self):
        return self.dict_nodetype_to_dict_name_to_node.keys()
        
    def get_all_nodes_for_nodetype(self, nodetype):
        return set(self.dict_nodetype_to_dict_name_to_node[nodetype].values())
    
    def add_node(self, nodetype, name, seed_node_bool=False, desc=''):
        if seed_node_bool:
            self.set_seed_node(None)
        else:
            if self.seed_node is None:
                print("must set seed_node_bool=True for first call to add_node")
                exit(1)
        existing_node = self.get_node(nodetype, name)
        if existing_node is None:
            subdict = self.dict_nodetype_to_dict_name_to_node.get(nodetype, None)
            if subdict is None:
                self.dict_nodetype_to_dict_name_to_node[nodetype] = dict()
            new_node = Node(nodetype, name, self.seed_node)
            new_node.desc = desc
            existing_node = new_node
            if seed_node_bool:
                self.set_seed_node(new_node)
            self.dict_nodetype_to_dict_name_to_node[nodetype][name] = new_node
            seed_node_uuid = self.seed_node.uuid
            sublist = self.dict_seed_uuid_to_list_nodes.get(seed_node_uuid, None)
            if sublist is None:
                self.dict_seed_uuid_to_list_nodes[seed_node_uuid] = list()
            self.dict_seed_uuid_to_list_nodes[seed_node_uuid].append(new_node)
        else:
            if desc != '' and existing_node.desc == '':
                existing_node.desc = desc
            if seed_node_bool:
                existing_node.expanded = False
        if self.debug:
            print("Number of nodes: " + str(self.count_nodes()))
        return existing_node

    @staticmethod
    def make_rel_dict_key(source_node, target_node):
        source_uuid = source_node.uuid
        target_uuid = target_node.uuid
        if source_uuid < target_uuid:
            rel_dict_key = source_uuid + "--" + target_uuid
        else:
            assert source_uuid > target_uuid
            rel_dict_key = target_uuid + "--" + source_uuid
        return rel_dict_key
    
    def get_rel(self, reltype, source_node, target_node):
        ret_rel = None
        rel_dict_key = None
        subdict = self.dict_reltype_to_dict_relkey_to_rel.get(reltype, None)
        if subdict is not None:
            rel_dict_key = Orangeboard.make_rel_dict_key(source_node, target_node)
            existing_rel = subdict.get(rel_dict_key, None)
            if existing_rel is not None:
                ret_rel = existing_rel
        return [ret_rel, rel_dict_key]
        
    def add_rel(self, reltype, sourcedb, source_node, target_node):
        seed_node = self.seed_node
        assert seed_node is not None
        existing_rel_list = self.get_rel(reltype, source_node, target_node)
        existing_rel = existing_rel_list[0]
        if existing_rel is None:
            subdict = self.dict_reltype_to_dict_relkey_to_rel.get(reltype, None)
            if subdict is None:
                self.dict_reltype_to_dict_relkey_to_rel[reltype] = dict()
                subdict = self.dict_reltype_to_dict_relkey_to_rel.get(reltype, None)
            new_rel = Rel(reltype, sourcedb, source_node, target_node, seed_node)
            existing_rel = new_rel
            rel_dict_key = existing_rel_list[1]
            if rel_dict_key is None:
                rel_dict_key = Orangeboard.make_rel_dict_key(source_node, target_node)
            subdict[rel_dict_key] = new_rel
            seed_node_uuid = seed_node.uuid
            sublist = self.dict_seed_uuid_to_list_rels.get(seed_node_uuid, None)
            if sublist is None:
                self.dict_seed_uuid_to_list_rels[seed_node_uuid] = []
            self.dict_seed_uuid_to_list_rels[seed_node_uuid].append(new_rel)
        if self.debug:
            print("Number of rels: " + str(self.count_rels()))
        return existing_rel

    @staticmethod
    def make_label_string_from_set(node_labels):
        if len(node_labels) > 0:
            return ':' + ':'.join(node_labels)
        else:
            return ''

    @staticmethod
    def make_property_string_from_dict(property_info):
        """takes a ``dict`` of property key-value pairs and converts it into a string in Neo4j format

        :param property_info: a ``dict`` of property key-value pairs
        :returns: a string representaiotn of the property key-value pairs, in Neo4j format like this:
        UUID:'97b47364-b9c2-11e7-ac88-a820660158fd', name:'prot1'
        """
        return "{" + (', '.join("{!s}:{!r}".format(key,val) for (key,val) in property_info.items())) + "}" if len(property_info) > 0 else ''

    def clear_from_seed_node_uuid(self, seed_node_uuid):
        dict_reltype_to_dict_relkey_to_rel = self.dict_reltype_to_dict_relkey_to_rel
        for reltype in dict_reltype_to_dict_relkey_to_rel.keys():
            dict_relkey_to_rel = dict_reltype_to_dict_relkey_to_rel[reltype]
            for relkey in dict_relkey_to_rel.copy().keys():
                rel = dict_relkey_to_rel[relkey]
                if rel.seed_node.uuid == seed_node_uuid:
                    rel.source_node = None
                    rel.target_node = None
                    del dict_relkey_to_rel[relkey]                   
        del self.dict_seed_uuid_to_list_rels[seed_node_uuid][:]
        del self.dict_seed_uuid_to_list_rels[seed_node_uuid]
        dict_nodetype_to_dict_name_to_node = self.dict_nodetype_to_dict_name_to_node
        for nodetype in dict_nodetype_to_dict_name_to_node.keys():
            dict_name_to_node = dict_nodetype_to_dict_name_to_node[nodetype]
            for name in dict_name_to_node.copy().keys():
                node = dict_name_to_node[name]
                if node.seed_node.uuid == seed_node_uuid:
                    del dict_name_to_node[name]
        del self.dict_seed_uuid_to_list_nodes[seed_node_uuid][:]
        del self.dict_seed_uuid_to_list_nodes[seed_node_uuid]

    def clear_from_seed_node(self, seed_node):
        self.clear_from_seed_node_uuid(seed_node.uuid)
        
    def clear_all(self):
        for seed_node_uuid in self.dict_seed_uuid_to_list_nodes.keys():
            self.clear_from_seed_node_uuid(seed_node_uuid)
        self.seed_node = None
        
    def neo4j_shutdown(self):
        """shuts down the Orangeboard by disconnecting from the Neo4j database

        :returns: nothing
        """
        self.driver.close()
        
    def neo4j_connect(self):
        self.driver = neo4j.v1.GraphDatabase.driver(Orangeboard.NEO4J_URL,
                                                    auth=(Orangeboard.NEO4J_USERNAME,
                                                          Orangeboard.NEO4J_PASSWORD))

    def neo4j_run_cypher_query(self, session, query_string, parameters=None):
        """runs a single cypher query in the neo4j database (without a transaction) and returns the result object

        :param query_string: a ``str`` object containing a single cypher query (without a semicolon)
        :returns: a `neo4j.v1.SessionResult` object resulting from executing the neo4j query
        """
        if (self.debug): print(query_string)
        assert (';' not in query_string)
        return session.run(query_string, parameters)
        
    def neo4j_clear(self, session=None, seed_node=None):
        """deletes all nodes and relationships in the orangeboard

        :returns: nothing
        """
        if session is None:
            use_session = self.driver.session()
        else:
            use_session = session
        if seed_node is not None:
            seed_node_uuid = seed_node.uuid
            cypher_query_middle = ":Base {seed_node_uuid: \'" + seed_node_uuid + "\'}"
        else:
            cypher_query_middle = ''
        cypher_query = "MATCH (n" + \
                       cypher_query_middle + \
                       ") DETACH DELETE n"
        if self.debug:
            print(cypher_query)
        self.neo4j_run_cypher_query(use_session, cypher_query)
        use_session.send()
        if session is None:
            use_session.close()

   
    def neo4j_push(self, seed_node=None):
        assert self.dict_reltype_dirs is not None
        nodetypes = self.get_all_nodetypes()
        self.neo4j_connect()
        with self.driver.session() as session:
            self.neo4j_clear(session)
            for nodetype in nodetypes:
                if self.debug:
                    print("Pushing nodes to Neo4j for node type: " + nodetype)
                nodes = self.get_all_nodes_for_nodetype(nodetype)
                if seed_node is not None:
                    nodes &= self.get_all_nodes_for_seed_node_uuid(seed_node.uuid)
                query_params = { 'props': [ node.get_props() for node in nodes ] }
                first_node = None
                node = next(iter(nodes))
                cypher_query_str = 'UNWIND $props as map\nCREATE (n' + \
                                   Orangeboard.make_label_string_from_set(node.get_labels()) + \
                                   ')\nSET n = map'
                if self.debug:
#                    print(query_params)
                    print(cypher_query_str)
                res = self.neo4j_run_cypher_query(session, cypher_query_str, query_params)
                if self.debug:
                    print(res.summary())
            self.neo4j_run_cypher_query(session, "CREATE INDEX ON :Base(UUID)")
            self.neo4j_run_cypher_query(session, "CREATE INDEX ON :Base(seed_node_uuid)")
            reltypes = self.get_all_reltypes()
            session.send()
            for reltype in reltypes:
                if self.debug:
                    print("Pushing relationships to Neo4j for relationship type: " + reltype)
                reltype_dir = self.dict_reltype_dirs[reltype]
                rels = self.get_all_rels_for_reltype(reltype)
                if seed_node is not None:
                    rels &= self.get_all_rels_for_seed_node_uuid(seed_node.uuid)
                reltype_rels_params_list = [ rel.get_props() for rel in rels ]
                dir_string = '>' if reltype_dir else ''
                query_params = { 'rel_data_list': reltype_rels_params_list }
                cypher_query_str = "UNWIND $rel_data_list AS rel_data_map\n" + \
                                   "MATCH (n1:Base {UUID: rel_data_map.source_node_uuid})," + \
                                   "(n2:Base {UUID: rel_data_map.target_node_uuid})\n" + \
                                   "CREATE (n1)-[:" + reltype + \
                                   " { source_node_uuid: rel_data_map.source_node_uuid," + \
                                   " target_node_uuid: rel_data_map.target_node_uuid," + \
                                   " sourcedb: rel_data_map.sourcedb," + \
                                   " seed_node_uuid: rel_data_map.seed_node_uuid," + \
                                   " UUID: rel_data_map.UUID }]-" + dir_string + "(n2)"
                if self.debug:
#                    print(query_params)
                    print(cypher_query_str)
                res = self.neo4j_run_cypher_query(session, cypher_query_str, query_params)
                if self.debug:
                    print(res.summary())
            session.send()
            session.close()
