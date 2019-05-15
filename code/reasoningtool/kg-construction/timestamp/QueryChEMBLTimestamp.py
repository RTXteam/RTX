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
        # for version_tag in soup.find_all("div", attrs={"class":"card-header"}):
        #     print(version_tag)
        return None


if __name__ == '__main__':
    print(QueryChEMBLTimestamp.get_timestamp())


