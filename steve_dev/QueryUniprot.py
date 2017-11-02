import requests
import sys

class QueryUniprot:
    API_BASE_URL = "http://www.uniprot.org/uploadlists/"
    
    @staticmethod
    def query_uniprot_to_reactome(uniprot_id):
        """returns a ``set`` of reactome IDs of pathways associated with a given string uniprot ID

        :param uniprot_id: a ``str`` uniprot ID, like ``"P68871"``
        :returns: a ``set`` of string Reactome IDs
        """
        
        payload = { 'from':   'ACC',
                    'to':     'REACTOME_ID',
                    'format': 'tab',
                    'query':  uniprot_id }
        contact = "stephen.ramsey@oregonstate.edu"
        header = {'User-Agent': 'Python %s' % contact}
        res = requests.post(QueryUniprot.API_BASE_URL, data=payload, headers=header)
        assert 200 == res.status_code
        res_set = set()
        for line in res.text.splitlines():
            field_str = line.split("\t")[1]
            if field_str != "To":
                res_set.add(field_str)
        return res_set

    @staticmethod
    def test():
        print(QueryUniprot.query_uniprot_to_reactome("P68871"))
        
if "--test" in set(sys.argv):
    QueryUniprot.test()
      
