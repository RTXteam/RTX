""" This module defines the class QueryOMIMTimestamp.
It is written to get the release date of OMIM.
https://www.omim.org/statistics/update
The OMIM is updated every month, so the release date is set to the first day of the current month.
"""

__author__ = ""
__copyright__ = ""
__credits__ = ['Deqing Qu', 'Stephen Ramsey']
__license__ = ""
__version__ = ""
__maintainer__ = ""
__email__ = ""
__status__ = "Prototype"

import time


class QueryOMIMTimestamp:

    @staticmethod
    def get_timestamp():
        return time.strftime("%b,01,%Y", time.localtime())


if __name__ == '__main__':
    print(QueryOMIMTimestamp.get_timestamp())




