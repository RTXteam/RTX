""" This module defines the class QueryMyGeneTimestamp.
It is written to get the release date of MyGene Database.

https://mygene.info/v3/metadata
"""

__author__ = ""
__copyright__ = ""
__credits__ = ['Deqing Qu', 'Stephen Ramsey']
__license__ = ""
__version__ = ""
__maintainer__ = ""
__email__ = ""
__status__ = "Prototype"

import requests
import sys
import json
from datetime import datetime


class QueryMyGeneTimestamp:
    TIMEOUT_SEC = 120

    @staticmethod
    def get_timestamp():
        url = "https://mygene.info/v3/metadata"

        try:
            res = requests.get(url, timeout=QueryMyGeneTimestamp.TIMEOUT_SEC)
        except BaseException as e:
            print(url, file=sys.stderr)
            print('%s received for URL: %s' % (e, url), file=sys.stderr)
            return None

        status_code = res.status_code
        if status_code != 200:
            print(url, file=sys.stderr)
            print('Status code ' + str(status_code) + ' for url: ' + url, file=sys.stderr)
            return None

        if res is None:
            return None
        #   remove all \n characters using json api and convert the string to one line
        json_dict = json.loads(res.text)
        if 'build_date' in json_dict.keys():
            build_date = json_dict['build_date'][:10]
            r = build_date.split('-')
            d = datetime(int(r[0]), int(r[1]), int(r[2]))
            return d.strftime("%b,%d,%Y")
        else:
            return None


if __name__ == '__main__':
    print(QueryMyGeneTimestamp.get_timestamp())


