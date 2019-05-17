""" This module defines the class QueryChEMBLTimestamp.
It is written to get the release date of ChEMBL Database.
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


class QueryChEMBLTimestamp:

    @staticmethod
    def get_timestamp():
        url = "https://chembl.gitbook.io/chembl-interface-documentation/downloads"
        soup = retrieve(url)
        tbody_tag = soup.find('tbody')
        #   release date in row 1 col 2
        i = 0
        for tr in tbody_tag.children:
            if i == 1:
                j = 0
                for td in tr.children:
                    if j == 2:
                        date = td.text
                        d = date.split()
                        if len(d) == 2:
                            return d[0] + ",1," + d[1]
                        else:
                            return None
                    j += 1
            i += 1
        return None


if __name__ == '__main__':
    print(QueryChEMBLTimestamp.get_timestamp())


