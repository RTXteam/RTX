class PathContainer:

    def __init__(self):
        self.path_dict = {}

    def add_new_path(self, new_path):
        if new_path.links:
            end_link = new_path.links[-1]
            if end_link not in self.path_dict:
                self.path_dict[end_link] = []
            self.path_dict[end_link].append(new_path)
