""" This module defines the class QueryHMDBTimestamp.
It is written to get the release date of HMDB Database.

http://www.hmdb.ca/release-notes
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


class QueryHMDBTimestamp:

    @staticmethod
    def get_timestamp():
        url = "http://www.hmdb.ca/release-notes"
        soup = retrieve(url)
        main_tag = soup.find('main')
        if main_tag is None or len(main_tag) == 0:
            return None
        date_tag = main_tag.findChildren('h2')
        if date_tag is None or len(date_tag) == 0:
            return None

        r = date_tag[0].text.split()
        return r[-2] + "01," + r[-1]


if __name__ == '__main__':
    print(QueryHMDBTimestamp.get_timestamp())


