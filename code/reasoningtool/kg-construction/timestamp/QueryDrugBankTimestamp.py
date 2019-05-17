""" This module defines the class QueryDrugBankTimestamp.
It is written to get the release date of DrugBank.
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

class QueryDrugBankTimestamp:

    @staticmethod
    def get_timestamp():
        url = "https://www.drugbank.ca/release_notes"
        soup = retrieve(url)
        version_tags = soup.find_all("div", attrs={"class": "card-header"})
        if len(version_tags) > 0:
            version_tag = version_tags[0].text
            r = version_tag.split()
            return r[-3] + "," + r[-2] + r[-1]
        else:
            return None


if __name__ == '__main__':
    print(QueryDrugBankTimestamp.get_timestamp())




