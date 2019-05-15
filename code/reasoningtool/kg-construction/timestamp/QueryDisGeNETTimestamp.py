""" This module defines the class QueryKEGGTimestamp.
It is written to get the release date of KEGG.
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

class QueryDisGeNETTimestamp:

    @staticmethod
    def get_timestamp():
        url = "http://www.disgenet.org/dbinfo"
        soup = retrieve(url)
        version_his_tag = soup.find_all(id="versionHistory")
        if len(version_his_tag) > 0:
            return version_his_tag[0].text
        else:
            return None

if __name__ == '__main__':
    print(QueryDisGeNETTimestamp.get_timestamp())




