""" This module defines the class QueryMeSH which connects to APIs at
http://eutils.ncbi.nlm.nih.gov/entrez/eutils for db=mesh, querying information
about a term of unknown origin, primarily to figure out what it is and get a
nice definition for a human.
"""

__author__ = ""
__copyright__ = ""
__credits__ = []
__license__ = ""
__version__ = ""
__maintainer__ = ""
__email__ = ""
__status__ = "Prototype"

import requests
import requests_cache
import time
import datetime

from swagger_server.models.response import Response
from swagger_server.models.result import Result
from swagger_server.models.result_graph import ResultGraph
from swagger_server.models.node import Node
from swagger_server.models.edge import Edge
from swagger_server.models.origin import Origin
from swagger_server.models.edge_attribute import EdgeAttribute
from swagger_server.models.node_attribute import NodeAttribute

def make_throttle_hook(timeout=1.0):
    """
    From: https://requests-cache.readthedocs.io/en/latest/user_guide.html#usage
    Returns a response hook function which sleeps for `timeout` seconds if
    response is not cached
    """
    def hook(response, *args, **kwargs):
        #print("In hook")
        if not getattr(response, 'from_cache', False):
            #print("sleeping "+str(timeout))
            time.sleep(timeout)
        return response
    return hook


class QueryMeSH:

    API_BASE_URL = 'http://eutils.ncbi.nlm.nih.gov/entrez/eutils'

    def __init__(self):
        requests_cache.install_cache(cache_name='QueryMeSH.requestCache', backend='sqlite', expire_after=180000)
        self.hooks = make_throttle_hook(0.5)

    def send_query_get(self, entity, url_suffix):
        url_str = self.API_BASE_URL + "/" + entity + url_suffix
        #print(url_str)
        #res = requests.get(url_str, headers={'accept': 'application/json'})
        cache = requests_cache.CachedSession()
        cache.hooks = {'response': self.hooks}
        res = cache.get(url_str, headers={'accept': 'application/json'})
        status_code = res.status_code
        #print("status_code="+str(status_code))
        assert status_code in [200, 404]
        if status_code == 404:
            res = None
        return res


    def findTermAttributesByName(self, term):
        attributes = {}
        attributes["status"] = "UnableToConnect"
        idlist = self.findPotentialTermIds(term)
        if idlist:
            id = self.findTermId(term)
        else:
            attributes["status"] = "TermNotFound"
        return attributes


    def findTermId(self, term):
        id = None
        idlist = self.findPotentialTermIds(term)
        if idlist:
            if len(idlist) == 1:
                id = idlist[0]
            else:
                print("WARNING: multiple returned ids")
                print(idlist)
        return id


    def findTermAttributesAndTypeByName(self, term):
        method = "findTermAttributesAndTypeByName"
        attributes = {}
        attributes["status"] = "UnknownTerm"
        termId = self.findTermId(term)
        if termId:
            attributes = self.findTermAttributesById(termId)
            attributes["type"] = self.findTermTypeById(attributes["parentId"])
            attributes["status"] = "OK"
        return attributes


    def createResponse(self):
        #### Create the response object and fill it with attributes about the response
        response = Response()
        response.context = "http://translator.ncats.io"
        response.id = "http://rtx.ncats.io/api/v1/response/0000"
        response.type = "medical_translator_query_response"
        response.tool_version = "RTX 0.4"
        response.schema_version = "0.5"
        response.datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        response.result_code = "OK"
        response.message = "1 result found"
        return response


    def queryTerm(self, term):
        method = "queryTerm"
        attributes = self.findTermAttributesAndTypeByName(term)
        response = self.createResponse()
        if ( attributes["status"] == 'OK' ):
            node1 = Node()
            node1.id = "https://www.ncbi.nlm.nih.gov/mesh/?term=" + attributes["id"]
            node1.type = attributes["type"]
            node1.name = attributes["name"]
            node1.accession = "MeSH:" + attributes["id"]
            node1.description = attributes["description"]

            #### Create the first result (potential answer)
            result1 = Result()
            result1.id = "http://rtx.ncats.io/api/v1/response/0000/result/0000"
            result1.text = "The term " + attributes["name"] + " refers to " + attributes["description"]
            result1.confidence = 1.0

            #### Create a ResultGraph object and put the list of nodes and edges into it
            result_graph = ResultGraph()
            result_graph.node_list = [ node1 ]

            #### Put the ResultGraph into the first result (potential answer)
            result1.result_graph = result_graph

            #### Put the first result (potential answer) into the response
            result_list = [ result1 ]
            response.result_list = result_list

        else:
            response.result_code = "TermNotFound"
            response.message = "Unable to find term '" + term + "' in MeSH. No further information is available at this time."
            response.id = None

        return response


    def findTermAttributesById(self, termId):
        method = "findPotentialTermIds"
        attributes = {}
        attributes["status"] = "UnableToConnect"

        #### Query MeSH to get information about the specified id
        content = self.send_query_get("esummary.fcgi", "?db=mesh&retmode=json&id=" + termId)
        if content is not None:
            #### Convert text content to JSON
            result = content.json()
            #print(result)
            #### Decode the result
            if type(result) == dict:
                if result["result"]:
                    if result["result"][termId]:
                        attributes["id"] = termId
                        attributes["name"] = result["result"][termId]["ds_meshterms"][0]
                        attributes["description"] = result["result"][termId]["ds_scopenote"]
                        attributes["parentId"] = str(result["result"][termId]["ds_idxlinks"][0]["parent"])
                        attributes["status"] = "OK"
                        return attributes
                    else:
                        print("ERROR: ["+method+"]: result does not have the called termId for termId=" + termId)
                        print(result)
                else:
                    print("ERROR: ["+method+"]: result is not present for term "+term)
                    print(result)
            else:
                print("ERROR: ["+method+"]: result is not a type dict as expected for term "+term)
                print(result)
        return attributes


    def findTermTypeById(self, termId):
        keepGoing = 1
        counter = 0
        while keepGoing:
            attributes = self.findTermAttributesById(termId)
            name = attributes["name"]
            if name:
                #print(attributes)
                if attributes["name"] == "Chemicals and Drugs Category":
                    type = "chemical_substance"
                    keepGoing = 0
                elif attributes["name"] == "Diseases Category":
                    type = "disease"
                    keepGoing = 0
                elif attributes["name"] == "Enzymes and Coenzymes":
                    type = "protein"
                    keepGoing = 0
                elif attributes["name"] == "Anatomy Category":
                    type = "gross_anatomical_structure"
                    keepGoing = 0
                elif attributes["name"] == "Analytical, Diagnostic and Therapeutic Techniques and Equipment Category":
                    type = "treatment"
                    keepGoing = 0
                elif attributes["name"] == "Animals":
                    type = "organism_taxon"
                    keepGoing = 0
                elif attributes["parentId"] == "1000048":
                    type = name
                    keepGoing = 0
                else:
                    type = attributes["name"]
                    termId = attributes["parentId"]
            else:
                print("No name? Time to stop?")
                keepGoing = 0
            counter += 1
            if counter > 7:
                keepGoing = 0
        return type


    def prettyPrintAttributes(self, attributes):
        buffer = ""
        if attributes["status"] == "OK":
            buffer += "<UL>"
            buffer += "<LI> <b>Name:</b> "+attributes["name"]
            buffer += "<LI> <b>Description:</b> "+attributes["description"]
            buffer += "<LI> <b>Type:</b> "+attributes["type"]
            buffer += "<UL>"
        else:
            buffer = "Unable to find that term"
        return buffer


    def findPotentialTermIds(self, term):
        method = "findPotentialTermIds"
        potentialTermIds = None

        #### Query MeSH for the specified term
        content = self.send_query_get("esearch.fcgi", "?db=mesh&retmode=json&term=" + term + '[MeSH Terms]')
        if content is not None:
            #### Convert text content to JSON
            result = content.json()
            #print(result)

            #### Decode the result
            if type(result) == dict:
                if result["esearchresult"]:
                    if result["esearchresult"]["count"] == "0":
                        return potentialTermIds
                    idlist = result["esearchresult"]["idlist"]
                    if type(idlist) == list:
                        potentialTermIds = idlist
                    else:
                        print("ERROR: ["+method+"]: idlist is not of type list for term "+term)
                        print(result)
                else:
                    print("ERROR: ["+method+"]: esearchresult is not present for term "+term)
                    print(result)
            else:
                print("ERROR: ["+method+"]: result is not a type dict as expected for term "+term)
                print(result)
        return potentialTermIds


if __name__ == '__main__':
    q = QueryMeSH()
    if 1 == 1:
        #print(q.findTermAttributesById("68008148"))
        #print(q.findPotentialTermIds("lovastatin"))
        #print(q.findPotentialTermIds("boogerstatin"))
        #termId = q.findTermId("lovastatin")
        #attributes = q.findTermAttributesAndTypeByName("malaria")
        #attributes = q.findTermAttributesAndTypeByName("phenazepam")
        #attributes = q.findTermAttributesAndTypeByName("physostigmine")
        #attributes = q.findTermAttributesAndTypeByName("heart")
        #attributes = q.findTermAttributesAndTypeByName("mouse")
        #attributes = q.findTermAttributesAndTypeByName("appendectomy")
        #attributes = q.findTermAttributesAndTypeByName("mitochondrion")
        #print(attributes)
        #print(q.prettyPrintAttributes(attributes))

        print(q.queryTerm("heart"))
        #print(q.queryTerm("snot"))
