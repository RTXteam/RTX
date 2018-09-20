import requests_cache
from QueryDGIdb import QueryDGIdb
from Neo4jConnection import Neo4jConnection

requests_cache.install_cache('orangeboard')


conn = Neo4jConnection('bolt://localhost:7687', 'neo4j', 'precisionmedicine')
disease_nodes = conn.get_disease_nodes()
drug_nodes = conn.get_chemical_substance_nodes()
protein_nodes = conn.get_protein_nodes()


def get_proteins(tx):
    result = tx.run("MATCH (n:protein) return n.id, n.UUID")
    return dict((record["n.id"], record["n.UUID"]) for record in result)


def get_drugs(tx):
    result = tx.run("MATCH (n:chemical_substance) return n.id, n.UUID")
    return dict((record["n.id"], record["n.UUID"]) for record in result)


def get_seed_node_uuid(tx):
    return next(iter(tx.run("MATCH (n:protein) return n.seed_node_uuid limit 1")))["n.seed_node_uuid"]


protein_dict = conn._driver.session().read_transaction(get_proteins)

drug_dict = conn._driver.session().read_transaction(get_drugs)

seed_node_uuid = conn._driver.session().read_transaction(get_seed_node_uuid)


def patch_kg():
    tuple_list = QueryDGIdb.read_interactions()
    for tuple_dict in tuple_list:
        chembl_id = tuple_dict['drug_chembl_id']
        uniprot_id = tuple_dict['protein_uniprot_id']
        protein_curie_id = 'UniProtKB:' + uniprot_id
        chembl_curie_id = 'CHEMBL.COMPOUND:' + chembl_id
        if protein_curie_id in protein_dict and chembl_curie_id in drug_dict:
            cypher_query = "MATCH (b:chemical_substance),(a:protein) WHERE a.id = \'" + \
                protein_curie_id + \
                "\' AND b.id=\'" + \
                chembl_curie_id + \
                "\' CREATE (b)-[r:" + \
                tuple_dict['predicate'] + \
                " { is_defined_by: \'RTX\', predicate: \'" + \
                tuple_dict['predicate'] + \
                "\', provided_by: \'DGIdb;" + \
                tuple_dict['sourcedb'] + \
                "\', relation: \'" + \
                tuple_dict['predicate_extended'] + \
                "\', seed_node_uuid: \'" + \
                seed_node_uuid + \
                "\', publications: \'" + \
                tuple_dict['pmids'] + \
                "\' } ]->(a) RETURN type(r)"
            print(cypher_query)
            conn._driver.session().write_transaction(lambda tx: tx.run(cypher_query))


patch_kg()
