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

class QueryKEGGTimestamp:

    @staticmethod
    def get_timestamp():
        url = "https://www.genome.jp/kegg/docs/relnote.html"
        soup = retrieve(url)
        main_tags = soup.find_all(id="main")
        if len(main_tags) > 0:
            main_tag = main_tags[0].text
            index = main_tag.find("Current release") + len("Current release")
            r = main_tag[index:].split()
            return r[2] + "," + r[3] + r[4]
        else:
            return None


if __name__ == '__main__':
    print(QueryKEGGTimestamp.get_timestamp())




