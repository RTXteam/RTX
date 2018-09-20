'''This module defines class Node, class Rel, and class Orangeboard.  The
Orangeboard class is responsible for connecting with the Neo4j database and
performing operations on a graph object model (e.g., add node, add relationship,
retrieve node information, and retrieve relationship information). Orangeboard
has a method for pushing the graph object model to the Neo4j database, using a
high-performance bulk upload operation.  This class is intended to be used as a
singleton.

'''

__author__ = 'Stephen Ramsey'
__copyright__ = 'Oregon State University'
__credits__ = ['Stephen Ramsey', 'Yao Yao', 'Zheng Liu']
__license__ = 'MIT'
__version__ = '0.1.0'
__maintainer__ = ''
__email__ = ''
__status__ = 'Prototype'

import uuid
import itertools
import pprint
import neo4j.v1
import sys
import timeit
import argparse

# NOTE to users:  neo4j password hard-coded (see NEO4J_PASSWORD below)
# nodetype+name together uniquely define a node


class Node:
    RESERVED_PROPS = {"UUID", "name", "seed_node_uuid", "expanded", "description"}

    def __init__(self, nodetype, name, seed_node):
        self.nodetype = nodetype
        self.name = name
        if seed_node is not None:
            self.seed_node = seed_node
        else:
            self.seed_node = self
        new_uuid = str(uuid.uuid1())
        self.uuid = new_uuid
#        self.out_rels = set()
#        self.in_rels = set()
        self.expanded = False
        self.extra_props = {}
        self.desc = ''

    def set_desc(self, desc):
        self.desc = desc

    def set_extra_props(self, extra_props_dict):
        assert 0 == len(extra_props_dict.keys() & self.RESERVED_PROPS)
        self.extra_props = extra_props_dict

    def get_props(self):
        basic_props = {'UUID': self.uuid,
                       'rtx_name': self.name,
                       'seed_node_uuid': self.seed_node.uuid,
                       'expanded': self.expanded,
                       'category': self.nodetype,
                       'name': self.desc}
        ret_dict = {**basic_props, **self.extra_props}
        # for key, value in ret_dict.items():
        #     if type(value) == str and any(i in value for i in ' '):
        #         ret_dict[key] = "`" + value + "`"
        return ret_dict

    def get_labels(self):
        return {'Base', self.nodetype}

    def __str__(self):
        attr_list = ['nodetype', 'name', 'uuid', 'expanded', 'desc']
        attr_dict = {attr: str(self.__getattribute__(attr)) for attr in attr_list}
        attr_dict['seed_node_uuid'] = self.seed_node.uuid
        return pprint.pformat(attr_dict)

    def simple_print(self):
        return 'node,' + self.uuid + ',' + self.nodetype + ',' + self.name


class Rel:
    def __init__(self, reltype, sourcedb, source_node, target_node, seed_node, prob=None, extended_reltype=None, publications=None):
        self.reltype = reltype
        self.sourcedb = sourcedb
        self.source_node = source_node
        self.target_node = target_node
        self.seed_node = seed_node
        self.prob = prob
        if extended_reltype is None:
            extended_reltype = reltype
        self.extended_reltype = extended_reltype
        if publications is not None:
            self.publications = publications
        else:
            self.publications = ''

    def get_props(self, reverse=False):
        extended_reltype = self.extended_reltype

        if " " in extended_reltype:
            quote_char = "`"
        else:
            quote_char = ""

        prop_dict = {'reltype': self.reltype,
                     'sourcedb': self.sourcedb,
                     'seed_node_uuid': self.seed_node.uuid,
                     'prob': self.prob,
                     'extended_reltype': quote_char + self.extended_reltype + quote_char,
                     'publications': quote_char + self.publications + quote_char}
        if not reverse:
            prop_dict['source_node_uuid'] = self.source_node.uuid
            prop_dict['target_node_uuid'] = self.target_node.uuid
        else:
            prop_dict['source_node_uuid'] = self.target_node.uuid
            prop_dict['target_node_uuid'] = self.source_node.uuid
        return prop_dict

    def __str__(self):
        attr_list = ['reltype', 'sourcedb', 'source_node', 'target_node']
        attr_dict = {attr: str(self.__getattribute__(attr))
                     for attr in attr_list}

        return pprint.pformat(attr_dict)

    def simple_print(self):
        return 'rel,' + self.source_node.uuid + ',' + self.target_node.uuid + ',' + self.sourcedb + ':' + self.reltype


class Orangeboard:
    NEO4J_USERNAME = 'neo4j'
    NEO4J_PASSWORD = 'precisionmedicine'
    DEBUG_COUNT_REPORT_GRANULARITY = 1000

    def bytesize(self):
        count = 0
        for uuid in self.dict_seed_uuid_to_list_nodes.keys():
            for node in self.dict_seed_uuid_to_list_nodes[uuid]:
                count += sys.getsizeof(node)
        for uuid in self.dict_seed_uuid_to_list_rels.keys():
            for rel in self.dict_seed_uuid_to_list_rels[uuid]:
                count += sys.getsizeof(rel)
        return count

    def __init__(self, debug=False):
        self.dict_nodetype_to_dict_name_to_node = dict()
        self.dict_reltype_to_dict_relkey_to_rel = dict()
        self.dict_nodetype_count = dict()
        self.dict_reltype_count = dict()
        self.dict_seed_uuid_to_list_nodes = dict()
        self.dict_seed_uuid_to_list_rels = dict()
        self.debug = debug
        self.seed_node = None
        self.dict_reltype_dirs = None
        self.driver = None
        self.neo4j_url = None
        self.neo4j_user = None
        self.neo4j_password = None
        if self.debug:
            self.start_time = timeit.default_timer()

    def set_dict_reltype_dirs(self, dict_reltype_dirs):
        self.dict_reltype_dirs = dict_reltype_dirs

    def neo4j_set_url(self, url='bolt://localhost:7687'):
        self.neo4j_url = url

    def neo4j_set_auth(self, user=NEO4J_USERNAME, password=NEO4J_PASSWORD):
        self.neo4j_user = user
        self.neo4j_password = password

    def simple_print_rels(self):
        rel_list = itertools.chain.from_iterable(self.dict_seed_uuid_to_list_rels.values())
        rel_strings = [rel.simple_print() for rel in rel_list]
        return '\n'.join(rel_strings) + '\n'

    def simple_print_nodes(self):
        node_list = itertools.chain.from_iterable(self.dict_seed_uuid_to_list_nodes.values())
        node_strings = [node.simple_print() for node in node_list]
        return '\n'.join(node_strings) + '\n'

    def __str__(self):
        node_list = itertools.chain.from_iterable(self.dict_seed_uuid_to_list_nodes.values())
        node_strings = [str(node) for node in node_list]

        rel_list = itertools.chain.from_iterable(self.dict_seed_uuid_to_list_rels.values())
        rel_strings = [str(rel) for rel in rel_list]

        return '\n'.join(node_strings) + '\n' + '\n'.join(rel_strings)

    def count_rels_for_node_slow(self, node):
        node_uuid = node.uuid
        count = 0
        for subdict in self.dict_reltype_to_dict_relkey_to_rel.values():
            for rel in subdict.values():
                if rel.source_node.uuid == node_uuid or rel.target_node.uuid == node_uuid:
                    count += 1
        return count

    def count_nodes(self):
        return sum(map(len, self.dict_seed_uuid_to_list_nodes.values()))

    def count_rels(self):
        return sum(map(len, self.dict_seed_uuid_to_list_rels.values()))

    def count_nodes_by_nodetype(self):
        # nodetypes = self.dict_nodetype_to_dict_name_to_node.keys()
        # print(nodetypes)
        # self.dict_nodetype_count = {str(nodetype): len(set(self.dict_nodetype_to_dict_name_to_node[nodetype].values())) for nodetype in self.dict_nodetype_to_dict_name_to_node.keys()}
        # return self.dict_nodetype_count

        results_nodetype = self.neo4j_run_cypher_query("match (n) return distinct labels(n)")
        nodetypes = [r[0][1] for r in results_nodetype]
        for nt in nodetypes:
            results_nodecount = self.neo4j_run_cypher_query("match (n:{}) return count(n)".format(nt))
            self.dict_nodetype_count[nt] = [r[0] for r in results_nodecount][0]
        return self.dict_nodetype_count

    def count_rels_by_reltype(self):
        results_reltype = self.neo4j_run_cypher_query("MATCH path=()-[r]-() RETURN distinct extract (rel in relationships(path) | type(rel) ) as types, count(*)")
        #dict_reltype_count = dict()  # defined on init
        for res in results_reltype:
            self.dict_reltype_count[res['types'][0]] = res['count(*)']
        return self.dict_reltype_count


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
        assert type(name) == str
        assert not (nodetype == "microRNA" and " " in desc)

        if seed_node_bool:
            # old_seed_node = self.seed_node
            # if old_seed_node is not None:
            #     old_seed_node_uuid = old_seed_node.uuid
            # else:
            #     old_seed_node_uuid = None
            self.set_seed_node(None)
        else:
            if self.seed_node is None:
                print('must set seed_node_bool=True for first call to add_node', file=sys.stderr)
                exit(1)
        existing_node = self.get_node(nodetype, name)
        if existing_node is None:
            # this is a new node we are adding
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
            if self.debug:
                node_count = self.count_nodes()
                if node_count % Orangeboard.DEBUG_COUNT_REPORT_GRANULARITY == 0:
                    print('Number of nodes: ' + str(node_count) + '; total elapsed time: ' + format(timeit.default_timer() - self.start_time, '.2f') + ' s')
        else:
            # node is already in the orangeboard

            # if the node object doesn't have a description but it is being
            # given one now, add the description to the existing node object
            if desc != '' and existing_node.desc == '':
                existing_node.desc = desc
                if nodetype == "protein" or nodetype == "microRNA":
                    existing_node.extra_props["symbol"] = desc

            # if seed_node_bool=True, this is a special case that must be handled
            if seed_node_bool:
                ## node is already in the orangeboard but we are updating its seed node
                ## (1) get the UUID for the existing node
                new_seed_node_uuid = existing_node.uuid
                existing_node_previous_seed_node_uuid = existing_node.seed_node.uuid
                ## (2) set the 'expanded' variable of the existing node to False
                existing_node.expanded = False
                ## (3) set the seed_node of the orangeboard to the existing_node
                self.set_seed_node(existing_node)
                ## (4) set the seed_node of the existing node to itself
                existing_node.seed_node = existing_node
                ## (5) add the existing node to the new seed-node-level list:
                new_seed_node_list = self.dict_seed_uuid_to_list_nodes.get(new_seed_node_uuid, None)
                if new_seed_node_list is None:
                    new_seed_node_list = []
                    self.dict_seed_uuid_to_list_nodes[new_seed_node_uuid] = new_seed_node_list
                new_seed_node_list.append(existing_node)
                ## (6) remove the existing node from the old seed-node-level list:
                assert existing_node_previous_seed_node_uuid is not None
                self.dict_seed_uuid_to_list_nodes[existing_node_previous_seed_node_uuid].remove(existing_node)
        return existing_node

    @staticmethod
    def make_rel_dict_key(source_uuid, target_uuid, rel_dir):
        if rel_dir or source_uuid < target_uuid:
            rel_dict_key = source_uuid + '--' + target_uuid
        else:
            assert source_uuid > target_uuid  
            rel_dict_key = target_uuid + '--' + source_uuid
        return rel_dict_key

    def get_rel(self, reltype, source_node, target_node):
        dict_reltype_dirs = self.dict_reltype_dirs
        if dict_reltype_dirs is None:
            print('Must call Orangeboard.set_dict_reltype_dirs() before you call add_rel()', file=sys.stderr)
            assert False
        reltype_dir = dict_reltype_dirs.get(reltype, None)
        if reltype_dir is None:
            print('reltype passed to add_rel is not in dict_reltype_dirs; reltype=' + reltype, file=sys.stderr)
            assert False
        ret_rel = None
        rel_dict_key = None
        subdict = self.dict_reltype_to_dict_relkey_to_rel.get(reltype, None)
        if subdict is not None:
            rel_dict_key = Orangeboard.make_rel_dict_key(source_node.uuid, target_node.uuid, reltype_dir)
            existing_rel = subdict.get(rel_dict_key, None)
            if existing_rel is not None:
                ret_rel = existing_rel
        return [ret_rel, rel_dict_key]

    def add_rel(self, reltype, sourcedb, source_node, target_node, prob=None, extended_reltype=None, publications=None):
        if source_node.uuid == target_node.uuid:
            print('Attempt to add a relationship between a node and itself, for node: ' + str(node), file=sys.stderr)
            assert False
        dict_reltype_dirs = self.dict_reltype_dirs
        if dict_reltype_dirs is None:
            print('Must call Orangeboard.set_dict_reltype_dirs() before you call add_rel()', file=sys.stderr)
            assert False
        reltype_dir = dict_reltype_dirs.get(reltype, None)
        if reltype_dir is None:
            print('reltype passed to add_rel is not in dict_reltype_dirs; reltype=' + reltype, file=sys.stderr)
            assert False
        seed_node = self.seed_node
        assert seed_node is not None
        existing_rel_list = self.get_rel(reltype, source_node, target_node)
        existing_rel = existing_rel_list[0]
        if existing_rel is None:
            subdict = self.dict_reltype_to_dict_relkey_to_rel.get(reltype, None)
            if subdict is None:
                self.dict_reltype_to_dict_relkey_to_rel[reltype] = dict()
                subdict = self.dict_reltype_to_dict_relkey_to_rel.get(reltype, None)
            new_rel = Rel(reltype, sourcedb, source_node, target_node, seed_node, prob, extended_reltype, publications)
            existing_rel = new_rel
            rel_dict_key = existing_rel_list[1]
            if rel_dict_key is None:
                rel_dict_key = Orangeboard.make_rel_dict_key(source_node.uuid, target_node.uuid, reltype_dir)
            subdict[rel_dict_key] = new_rel
            seed_node_uuid = seed_node.uuid
            sublist = self.dict_seed_uuid_to_list_rels.get(seed_node_uuid, None)
            if sublist is None:
                self.dict_seed_uuid_to_list_rels[seed_node_uuid] = []
            self.dict_seed_uuid_to_list_rels[seed_node_uuid].append(new_rel)
            if self.debug:
                rel_count = self.count_rels()
                if rel_count % Orangeboard.DEBUG_COUNT_REPORT_GRANULARITY == 0:
                    print('Number of rels: ' + str(rel_count) + '; total elapsed time: ' + format(timeit.default_timer() - self.start_time, '.2f') + ' s')
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
        return '{' + (', '.join('{!s}:{!r}'.format(key,val) for (key,val) in property_info.items())) + '}' if len(property_info) > 0 else ''

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

    def neo4j_connect(self):
        assert self.neo4j_url is not None
        assert self.neo4j_user is not None
        assert self.neo4j_password is not None

        self.driver = neo4j.v1.GraphDatabase.driver(self.neo4j_url,
                                                    auth=(self.neo4j_user,
                                                          self.neo4j_password))
    # def neo4j_shutdown(self):
    #     """shuts down the Orangeboard by disconnecting from the Neo4j database
    #
    #     :returns: nothing
    #     """
    #     self.driver.close()

    def neo4j_run_cypher_query(self, query, parameters=None):
        """runs a single cypher query in the neo4j database (without a transaction) and returns the result object

        :param query: a ``str`` object containing a single cypher query (without a semicolon)
        :param parameters: a ``dict`` object containing parameters for this query
        :returns: a `neo4j.v1.SessionResult` object resulting from executing the neo4j query
        """
        if self.debug:
            print(query)
        assert ';' not in query

        # Lazily initialize the driver
        if self.driver is None:
            self.neo4j_connect()

        session = self.driver.session()
        res = session.run(query, parameters)
        session.close()
        return res

    def neo4j_clear(self, seed_node=None):
        """deletes all nodes and relationships in the orangeboard

        :returns: nothing
        """
        if seed_node is not None:
            seed_node_uuid = seed_node.uuid
            cypher_query_middle = ':Base {seed_node_uuid: \'' + seed_node_uuid + '\'}'
        else:
            cypher_query_middle = ''

        cypher_query = 'MATCH (n' + \
                       cypher_query_middle + \
                       ') DETACH DELETE n'

        if self.debug:
            print(cypher_query)

        self.neo4j_run_cypher_query(cypher_query)

    def neo4j_push(self, seed_node=None):
        assert self.dict_reltype_dirs is not None

        self.neo4j_clear()

        nodetypes = self.get_all_nodetypes()
        for nodetype in nodetypes:
            if self.debug:
                print('Pushing nodes to Neo4j for node type: ' + nodetype)
            nodes = self.get_all_nodes_for_nodetype(nodetype)
            if seed_node is not None:
                nodes &= self.get_all_nodes_for_seed_node_uuid(seed_node.uuid)
            query_params = {'props': [node.get_props() for node in nodes]}
            node = next(iter(nodes))
            cypher_query_str = 'UNWIND $props as map\nCREATE (n' + \
                               Orangeboard.make_label_string_from_set(node.get_labels()) + \
                               ')\nSET n = map'
            if self.debug:
                print(cypher_query_str)
            res = self.neo4j_run_cypher_query(cypher_query_str, query_params)
            if self.debug:
                print(res.summary().counters)

        try:
            self.neo4j_run_cypher_query('CREATE INDEX ON :Base(UUID)')
            self.neo4j_run_cypher_query('CREATE INDEX ON :Base(seed_node_uuid)')
        except neo4j.exceptions.ClientError as e:
            print(str(e), file=sys.stderr)

        reltypes = self.get_all_reltypes()
        for reltype in reltypes:
            if self.debug:
                print('Pushing relationships to Neo4j for relationship type: ' + reltype)
            reltype_dir = self.dict_reltype_dirs[reltype]
            rels = self.get_all_rels_for_reltype(reltype)
            if seed_node is not None:
                rels &= self.get_all_rels_for_seed_node_uuid(seed_node.uuid)
            reltype_rels_params_list = [rel.get_props() for rel in rels]
            if not reltype_dir:
                reltype_rels_params_list = reltype_rels_params_list + \
                                           [rel.get_props(reverse=True) for rel in rels]
            query_params = {'rel_data_list': reltype_rels_params_list}
            cypher_query_str = 'UNWIND $rel_data_list AS rel_data_map\n' + \
                               'MATCH (n1:Base {UUID: rel_data_map.source_node_uuid}),' + \
                               '(n2:Base {UUID: rel_data_map.target_node_uuid})\n' + \
                               'CREATE (n1)-[:`' + reltype + \
                               '` { source_node_uuid: rel_data_map.source_node_uuid,' + \
                               ' target_node_uuid: rel_data_map.target_node_uuid,' + \
                               ' is_defined_by: \'RTX\',' + \
                               ' provided_by: rel_data_map.sourcedb,' + \
                               ' predicate: \'' + reltype + '\',' + \
                               ' seed_node_uuid: rel_data_map.seed_node_uuid,' + \
                               ' probability: rel_data_map.prob,' + \
                               ' publications: rel_data_map.publications,' + \
                               ' relation: rel_data_map.extended_reltype' + \
                               ' }]->(n2)'
            res = self.neo4j_run_cypher_query(cypher_query_str, query_params)
            if self.debug:
                print(res.summary().counters)

    def test_issue_66():
        ob = Orangeboard(debug=True)
        gnode = ob.add_node('footype', 'g', seed_node_bool=True)
        xnode = ob.add_node('footype', 'x', seed_node_bool=False)
        ynode = ob.add_node('footype', 'y', seed_node_bool=True)
        znode = ob.add_node('footype', 'z', seed_node_bool=True)
        ob.add_node('footype', 'g', seed_node_bool=True)
#       print(ob)

    def test_issue_104():
        ob = Orangeboard(debug=True)
        ob.set_dict_reltype_dirs({'interacts_with': False})
        node1 = ob.add_node('uniprot_protein', 'w', seed_node_bool=True)
        node2 = ob.add_node('bartype', 'x', seed_node_bool=False)
        ob.add_rel('interacts_with', 'PC2', node1, node2)
        ob.add_rel('interacts_with', 'PC2', node2, node1)
        ob.neo4j_set_url()
        ob.neo4j_set_auth()
        ob.neo4j_push()
        print(ob)

    def test_issue_120():
        ob = Orangeboard(debug=True)
        ob.set_dict_reltype_dirs({'interacts_with': False})
        node1 = ob.add_node('uniprot_protein', 'w', seed_node_bool=True)
        node2 = ob.add_node('bartype', 'x', seed_node_bool=False)
        ob.add_rel('interacts_with', 'PC2', node1, node2)
        ob.add_rel('interacts_with', 'PC2', node2, node1)
        ob.neo4j_set_url()
        ob.neo4j_set_auth()
        ob.neo4j_push()
        print(ob)

    def test_issue_130():
        ob = Orangeboard(debug=True)
        ob.set_dict_reltype_dirs({'targets': True})
        node1 = ob.add_node('drug', 'x', seed_node_bool=True)
        node2 = ob.add_node('uniprot_protein', 'w', seed_node_bool=False)
        ob.add_rel('targets', 'ChEMBL', node1, node2, prob=0.5)
        ob.neo4j_set_url()
        ob.neo4j_set_auth()
        ob.neo4j_push()
        print(ob)        

    def test_extended_reltype():
        ob = Orangeboard(debug=True)
        ob.set_dict_reltype_dirs({'targets': True, 'targets2': True})
        node1 = ob.add_node('drug', 'x', seed_node_bool=True)
        node2 = ob.add_node('uniprot_protein', 'w', seed_node_bool=False)
        ob.add_rel('targets', 'ChEMBL', node1, node2, prob=0.5)
        ob.add_rel('targets2', 'ChEMBL2', node1, node2, prob=0.5, extended_reltype="test")
        ob.neo4j_set_url()
        ob.neo4j_set_auth()
        ob.neo4j_push()
        print(ob)        

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Builds the master knowledge graph')
    parser.add_argument('--runfunc', dest='runfunc')
    args = parser.parse_args()
    args_dict = vars(args)
    if args_dict.get('runfunc', None) is not None:
        run_function_name = args_dict['runfunc']
    else:
        sys.exit("must specify --runfunc")
    run_method = getattr(Orangeboard, run_function_name, None)
    if run_method is None:
        sys.exit("function not found: " + run_function_name)
        
    running_time = timeit.timeit(lambda: run_method(), number=1)
    print('running time for function: ' + str(running_time))
                        
