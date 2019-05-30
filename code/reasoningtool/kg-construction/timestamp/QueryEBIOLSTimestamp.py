""" This module defines the class QueryEBIOLSTimestamp.
It is written to get the release date of EBIOLS Database.

https://www.ebi.ac.uk/ols/index
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


class QueryEBIOLSTimestamp:

    @staticmethod
    def get_timestamp():
        url = "https://www.ebi.ac.uk/ols/index"
        soup = retrieve(url)
        aside_tag = soup.find('aside')
        if aside_tag is None or len(aside_tag) == 0:
            return None
        date_tag = aside_tag.findChildren('h5')
        if date_tag is None or len(date_tag) == 0:
            return None

        r = date_tag[0].text.split()
        return r[2] + "," + r[1] + ',' + r[3]


if __name__ == '__main__':
    print(QueryEBIOLSTimestamp.get_timestamp())


