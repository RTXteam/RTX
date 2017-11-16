from Orangeboard import Orangeboard



class PathAnalyzer:
    """
    We will need Python code (probably using Cypher via neo4j.v1) that can, given a path,
      return the following information:

    (1) the relationship types of all edges in the path
    (2) the directions of all edges in the path
    (3) the node types of all nodes in the path
    (4) the source database for all edges in the path (“sourcedeb” relationship property)
    (5) the in-degree of all nodes in the path
    (6) the out-degree of all nodes in the path

    Note— if you get the node sequence you can get items (1), (2), (3), (4) from Orangeboard and node or
      relationship properties.

    For (5) and (6) you will have to use Cypher.
    """
    def __init__(self, orangeboard):
        self.orangeboard = orangeboard

    @staticmethod
    def get_all_reltypes_in_path(path):
        return list(map(lambda r: r.type, path.relationships))

    @staticmethod
    def get_all_dirs_in_path(path):
        def __generate_dirs(path):
            # There are (n+1) nodes and n relationships in a path of length n
            # type(path.nodes) == tuple
            # type(path.relationships) == tuple
            for node, rel in zip(path.nodes[0:-1], path.relationships):
                if node.id == rel.start:
                    yield "-->"
                elif node.id == rel.end:
                    yield "<--"
                else:
                    raise ValueError("Node {} is not within Rel {}".format(node.id, rel))

        return list(__generate_dirs(path))

    @staticmethod
    def get_all_nodetypes_in_path(path):
        def __exclude_base_type(node):
            # type(node.labels) == set
            # Assume that only 1 element exists in the difference
            return next(iter((node.labels - set(['Base']))))

        return list(map(__exclude_base_type, path.nodes))

    @staticmethod
    def get_all_rel_sourcedb_in_path(path):
        return list(map(lambda r: r.properties['sourcedb'], path.relationships))

    def get_all_in_degrees_in_path(self, path):
        # `MATCH (s)<-[r]-() WHERE s.UUID IN $uuid_lst RETURN count(r)` does not preserve the order of $uuid_lst
        # So here make a query for each node in the path
        def __get_in_degree(node):
            query = "MATCH (s)<-[r]-() WHERE s.UUID = $uuid RETURN count(r) AS in_degree"
            stmt_resp = self.orangeboard.neo4j_run_cypher_query(query, parameters={'uuid': node.properties['UUID']})
            return stmt_resp.single()['in_degree']

        return list(map(__get_in_degree, path.nodes))

    def get_all_out_degrees_in_path(self, path):
        # `MATCH (s)-[r]->() WHERE s.UUID IN $uuid_lst RETURN count(r)` does not preserve the order of $uuid_lst
        # So here make a query for each node in the path
        def __get_out_degree(node):
            query = "MATCH (s)-[r]->() WHERE s.UUID = $uuid RETURN count(r) AS out_degree"
            stmt_resp = self.orangeboard.neo4j_run_cypher_query(query, parameters={'uuid': node.properties['UUID']})
            return stmt_resp.single()['out_degree']

        return list(map(__get_out_degree, path.nodes))


if __name__ == '__main__':
    ob = Orangeboard(debug=False)

    master_rel_is_directed = {'disease_affects': True,
                              'is_member_of': True,
                              'is_parent_of': True,
                              'gene_assoc_with': True,
                              'phenotype_assoc_with': True,
                              'interacts_with': False,
                              'controls_expression_of': True,
                              'is_expressed_in': True,
                              'targets': True}

    ob.set_dict_reltype_dirs(master_rel_is_directed)
    ob.neo4j_set_url()
    ob.neo4j_set_auth()

    ob.neo4j_clear()

    node1 = ob.add_node('uniprot_protein', 'P16887', desc='HBB', seed_node_bool=True)
    node2 = ob.add_node('uniprot_protein', 'P09601', desc='HMOX1', seed_node_bool=True)
    ob.add_rel('interacts_with', 'reactome', node1, node2)  # bi-directional; actually 2 rels

    node3 = ob.add_node("omim_disease", "OMIM:603903", desc='sickle-cell anemia', seed_node_bool=True)
    ob.add_rel('controls_expression_of', 'OMIM', node2, node3)

    ob.neo4j_push()

    # (OMIM:603903)<-[regulates]-(P09601)-[interacts_with]->(P16887)
    path = ob.neo4j_run_cypher_query("Match p=(a:omim_disease)<--(b:uniprot_protein)-->(c:uniprot_protein) "
                                     "RETURN p LIMIT 1").single()['p']

    pa = PathAnalyzer(ob)

    print("[Rel Types]     : {}".format(PathAnalyzer.get_all_reltypes_in_path(path)))
    print("[Rel Directions]: {}".format(PathAnalyzer.get_all_dirs_in_path(path)))
    print("[Node Types]    : {}".format(PathAnalyzer.get_all_nodetypes_in_path(path)))
    print("[Rel SourceDBs] : {}".format(PathAnalyzer.get_all_rel_sourcedb_in_path(path)))
    print("[In-degrees]    : {}".format(pa.get_all_in_degrees_in_path(path)))
    print("[Out-degrees]   : {}".format(pa.get_all_out_degrees_in_path(path)))
