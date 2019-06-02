""" This module defines the class QueryDisontTimestamp.
It is written to get the release date of Disease Ontology Database.

http://www.disease-ontology.org/news/
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


class QueryDisontTimestamp:

    @staticmethod
    def get_timestamp():
        url = "http://www.disease-ontology.org/news/"
        soup = retrieve(url)
        content_tag = soup.find(id='content')

        date_tag = content_tag.findChildren('p')[0]
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


if __name__ == '__main__':
    print(QueryDisontTimestamp.get_timestamp())


