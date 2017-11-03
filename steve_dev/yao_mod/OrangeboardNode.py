class OrangeboardNode:
    def __init__(self, neo4j_node):
        # Delegate neo4j.v1.types.Node
        self.neo4j_node = neo4j_node

    def __getattr__(self, attr_name):
        """
        `__getattr__` is called when an attribute lookup FAILS.

        If that happens, look up into the inner `neo4j_node`.

        `foo.__getattribute__("bar")` is equal to `foo.bar`.
        """
        return self.neo4j_node.__getattribute__(attr_name)

    def __repr__(self):
        return repr(self.neo4j_node)

    def __str__(self):
        return str(self.neo4j_node)

    def __eq__(self, other):
        # Great! neo4j node implemented `__eq__`
        if type(other) != OrangeboardNode:
            return False
        else:
            return self.neo4j_node == other.neo4j_node

    def __hash__(self):
        return hash(self.neo4j_node)

    def get_biotype(self):
        labels = self.labels.copy()
        labels.remove("Base")
        assert len(labels) == 1
        return list(labels)[0]

    def get_bioname(self):
        return self.properties["name"]

    def is_expanded(self):
        return self.properties["expanded"] == "true"

    def get_uuid(self):
        return self.properties["UUID"]
