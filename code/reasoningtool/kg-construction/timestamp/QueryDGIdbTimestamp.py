""" This module defines the class QueryDGIdbTimestamp.
It is written to get the release date of DGIdb.

http://www.dgidb.org/downloads
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
from datetime import datetime

class QueryDGIdbTimestamp:

    @staticmethod
    def get_timestamp():
        url = "http://www.dgidb.org/downloads"
        soup = retrieve(url)
        footer_tag = soup.find(id="footer")
        if footer_tag:
            date_tag = footer_tag.findChildren("p")[0]
            if date_tag:
                date = date_tag.text.split()[-1]
                r = date.split('-')
                if len(r) == 3:
                    d = datetime(int(r[0]), int(r[1]), int(r[2]))
                    return d.strftime("%b,%d,%Y")
                else:
                    return None
            else:
                return None
        else:
            return None


if __name__ == '__main__':
    print(QueryDGIdbTimestamp.get_timestamp())



