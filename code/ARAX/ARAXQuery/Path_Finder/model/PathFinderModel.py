import pickle


class PathFinderModel:

    def __init__(self, repo_name, path):
        self.repo_name = repo_name
        self.path = path

    def serialize(self):
        return pickle.dumps(self)

    @staticmethod
    def deserialize(data):
        return pickle.loads(data)
