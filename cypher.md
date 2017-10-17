# Reasoning Tool Team to share Cypher queries here

# Q1 Team Queries that we are using:

- If you want to find the ID of a node of type `disease` for which attribute `attr1` has value `abc` (limiting to one node):

        MATCH (n:disease) WHERE n.attr1=abc RETURN ID(n) LIMIT 1

- If you want to find the shortest-undirected-path (max 3 steps) form node 12345 to node 23456:

        START start_node=NODE(12345), end_node=NODE(23456) MATCH path=shortestPath((start_node)-[r*0..3]-(end_node)) \
        RETURN path

- If you want to find the shortest-undirected-path (max 3 steps) from node 12345 to node 23456 excluding edges of type `isDefinedBy`:

        START start_node=NODE(12345), end_node=NODE(23456) MATCH path=shortestPath((start_node)-[r*0..3]-(end_node)) \
        WHERE NONE (rel in r WHERE type(rel)='isDefinedBy') RETURN path

        
# Q2 Team Queries that we are using:

    FILL IN CYPHER QUERIES HERE
    

