import uuid

debug = True

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

    def get_props(self):
        return {'UUID': self.uuid, 'name': self.name, 'seed_node_uuid': self.seed_node.uuid}
        

    def get_labels(sel):
        return {'Base', self.nodetype}

class Rel:
    def __init__(self, reltype, sourcedb, source_node, target_node, directed, seed_node):
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
        return {'UUID': self.uuid, 'reltype': self.reltype, 'sourcedb': self.sourcedb, 'seed_node_uuid': self.seed_node.uuid}
    
class Orangeboard:
    def __init__(self, debug=False):
        self.dict_nodetype_to_dict_name_to_node = dict()
        self.dict_reltype_to_dict_relkey_to_rel = dict()
        self.dict_seed_uuid_to_list_nodes = dict()
        self.dict_seed_uuid_to_list_rels = dict()
        self.debug = debug
        self.seed_node = None

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

    def get_all_nodes(self):
        return self.dict_seed_uuid_to_list_nodes[self.seed_node.uuid].copy()
    
    def add_node(self, nodetype, name):
        seed_node = self.seed_node
        existing_node = self.get_node(nodetype, name)
        if existing_node is None:
            subdict = self.dict_nodetype_to_dict_name_to_node.get(nodetype, None)
            if subdict is None:
                self.dict_nodetype_to_dict_name_to_node[nodetype] = dict()
            new_node = Node(nodetype, name, seed_node)
            existing_node = new_node
            if seed_node is None:
                seed_node = new_node
                self.set_seed_node(seed_node)
            self.dict_nodetype_to_dict_name_to_node[nodetype][name] = new_node
            seed_node_uuid = seed_node.uuid
            sublist = self.dict_seed_uuid_to_list_nodes.get(seed_node_uuid, None)
            if sublist is None:
                self.dict_seed_uuid_to_list_nodes[seed_node_uuid] = list()
            self.dict_seed_uuid_to_list_nodes[seed_node.uuid].append(new_node)
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
        
    def add_rel(self, reltype, sourcedb, source_node, target_node, directed=True):
        seed_node = self.seed_node
        assert seed_node is not None
        existing_rel_list = self.get_rel(reltype, source_node, target_node)
        existing_rel = existing_rel_list[0]
        if existing_rel is None:
            subdict = self.dict_reltype_to_dict_relkey_to_rel.get(reltype, None)
            if subdict is None:
                self.dict_reltype_to_dict_relkey_to_rel[reltype] = dict()
            new_rel = Rel(reltype, sourcedb, source_node, target_node, directed, seed_node)
            existing_rel = new_rel
            rel_dict_key = existing_rel_list[1]
            if rel_dict_key is None:
                rel_dict_key = Orangeboard.make_rel_dict_key(source_node, target_node)
            self.dict_reltype_to_dict_relkey_to_rel[rel_dict_key] = new_rel
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
    
    def cypher_dump(self):
        cyph_list.append('CREATE INDEX ON :Base(UUID);')
        pass
