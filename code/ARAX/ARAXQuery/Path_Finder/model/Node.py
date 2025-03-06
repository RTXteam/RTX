import pickle
class Node:

    def __init__(self, id, weight=float('inf'), name="", degree=0, category=""):
        self.id = id
        self.weight = weight
        self.name = name
        self.degree = degree
        self.category = category

    def __eq__(self, other):
        if isinstance(other, Node):
            return self.id == other.id
        return False

    def __str__(self):
        return self.id

    def __hash__(self):
        return hash(self.id)

    def copy(self):
        return Node(self.id, self.weight, self.name, self.degree, self.category)

    def serialize(self):
        return pickle.dumps(self)

    @staticmethod
    def deserialize(data):
        return pickle.loads(data)
