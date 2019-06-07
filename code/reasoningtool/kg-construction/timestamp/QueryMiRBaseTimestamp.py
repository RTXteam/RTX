""" This module defines the class QueryMiRBaseTimestamp.
It is written to get the release date of EBIOLS Database.

http://www.mirbase.org/
"""

__author__ = ""
__copyright__ = ""
__credits__ = ['Deqing Qu', 'Stephen Ramsey']
__license__ = ""
__version__ = ""
__maintainer__ = ""
__email__ = ""
__status__ = "Prototype"

from ScrapingHelper import retrieve


class QueryMiRBaseTimestamp:

    @staticmethod
    def get_timestamp():
        url = "http://www.mirbase.org/"
        soup = retrieve(url)
        right_col_tag = soup.find(id='rightColumn')
        if right_col_tag is None or len(right_col_tag) == 0:
            return None
        date_tag = right_col_tag.findChildren('p')
        if date_tag is None or len(date_tag) == 0:
            return None
        r = date_tag[0].text.split()

        return r[-2] + ",01," + r[-1]


if __name__ == '__main__':
    print(QueryMiRBaseTimestamp.get_timestamp())


