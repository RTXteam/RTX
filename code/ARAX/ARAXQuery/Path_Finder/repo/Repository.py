from abc import ABC, abstractmethod


class Repository(ABC):

    @abstractmethod
    def get_neighbors(self, node, limit):
        pass
