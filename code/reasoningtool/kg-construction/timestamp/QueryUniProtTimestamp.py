""" This module defines the class QueryUniProtTimestamp.
It is written to get the release date of UniProt Database.
"""

__author__ = ""
__copyright__ = ""
__credits__ = ['Deqing Qu', 'Stephen Ramsey']
__license__ = ""
__version__ = ""
__maintainer__ = ""
__email__ = ""
__status__ = "Prototype"

import requests

class QueryChEMBLTimestamp:

    @staticmethod
    def get_timestamp():
        url = "ftp://ftp.uniprot.org/pub/databases/uniprot/relnotes.txt"
        r = requests.get(url)

        return r


if __name__ == '__main__':
    print(QueryChEMBLTimestamp.get_timestamp())


