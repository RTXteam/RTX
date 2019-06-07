""" This module defines the class QueryReactomeTimestamp.
It is written to get the release date of Reactome Database.

https://reactome.org/
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


class QueryReactomeTimestamp:

    @staticmethod
    def get_timestamp():
        url = "https://reactome.org/"
        soup = retrieve(url)
        main_tag = soup.find(id='fav-portfolio1')
        if main_tag is None or len(main_tag) == 0:
            return None
        date_tag = main_tag.findChildren('h3')
        if date_tag is None or len(date_tag) == 0:
            return None

        r = date_tag[0].text.split()
        return r[-3] + "," + r[-2] + r[-1]


if __name__ == '__main__':
    print(QueryReactomeTimestamp.get_timestamp())


