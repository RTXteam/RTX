
import os
import sys
import datetime
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../")

from swagger_server.models.response import Response
from swagger_server.models.result import Result
from swagger_server.models.result_graph import ResultGraph
from swagger_server.models.node import Node
from swagger_server.models.edge import Edge
from swagger_server.models.origin import Origin
from swagger_server.models.edge_attribute import EdgeAttribute
from swagger_server.models.node_attribute import NodeAttribute

class TestResponse():

    def test1(self):

        #### Create the response object and fill it with attributes about the response
        response = Response()
        response.context = "http://translator.ncats.io"
        response.id = "http://rtx.ncats.io/api/v1/response/1234"
        response.type = "medical_translator_query_response"
        response.tool_version = "RTX 0.4"
        response.schema_version = "0.5"
        response.datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        response.original_question_text = "what proteins are affected by sickle cell anemia"
        response.restated_question_text = "Which proteins are affected by sickle cell anemia?"
        response.result_code = "OK"
        response.message = "1 result found"

        #### Create a disease node
        node1 = Node()
        node1.id = "http://omim.org/entry/603903"
        node1.type = "disease"
        node1.name = "sickle cell anemia"
        node1.accession = "OMIM:603903"
        node1.description = "A disease characterized by chronic hemolytic anemia..."

        #### Create a protein node
        node2 = Node()
        node2.id = "https://www.uniprot.org/uniprot/P00738"
        node2.type = "protein"
        node2.name = "Haptoglobin"
        node2.symbol = "HP"
        node2.accession = "UNIPROT:P00738"
        node2.description = "Haptoglobin captures, and combines with free plasma hemoglobin..."

        #### Create a node attribute
        node2attribute1 = NodeAttribute()
        node2attribute1.type = "comment"
        node2attribute1.name = "Complex_description"
        node2attribute1.value = "The Hemoglobin/haptoglobin complex is composed of a haptoglobin dimer bound to two hemoglobin alpha-beta dimers"
        node2.node_attributes = [ node2attribute1 ]

        #### Create an edge between these 2 nodes
        edge1 = Edge()
        edge1.type = "is_caused_by_a_defect_in"
        edge1.source_id = node1.id
        edge1.target_id = node2.id
        edge1.confidence = 1.0

        #### Add an origin and property for the edge
        origin1 = Origin()
        origin1.id = "https://api.monarchinitiative.org/api/bioentity/disease/OMIM:603903/genes/"
        origin1.type = "Monarch_BioLink_API_Relationship"

        #### Add an attribute
        attribute1 = EdgeAttribute()
        attribute1.type = "PubMed_article"
        attribute1.name = "Orthopaedic Manifestations of Sickle Cell Disease"
        attribute1.value = None
        attribute1.url = "https://www.ncbi.nlm.nih.gov/pubmed/29309293"
        origin1.attribute_list = [ attribute1 ]
        edge1.origin_list = [ origin1 ]

        #### Create the first result (potential answer)
        result1 = Result()
        result1.id = "http://rtx.ncats.io/api/v1/response/1234/result/2345"
        result1.text = "A free text description of this result"
        result1.confidence = 0.932

        #### Create a ResultGraph object and put the list of nodes and edges into it
        result_graph = ResultGraph()
        result_graph.node_list = [ node1, node2 ]
        result_graph.edge_list = [ edge1 ]

        #### Put the ResultGraph into the first result (potential answer)
        result1.result_graph = result_graph

        #### Put the first result (potential answer) into the response
        result_list = [ result1 ]
        response.result_list = result_list

        print(response)

if __name__ == '__main__':
    test = TestResponse()
    test.test1()
