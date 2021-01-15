# This class will overlay the normalized google distance on a message (all edges)
#!/bin/env python3
import sys
import os
import traceback
import numpy as np

# relative imports
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../OpenAPI/python-flask-server/")
from swagger_server.models.attribute import Attribute as NodeAttribute
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../reasoningtool/kg-construction/")
from NormGoogleDistance import NormGoogleDistance as NGD


class AddNodePMIDS:

    #### Constructor
    def __init__(self, response, message, parameters):
        self.response = response
        self.message = message
        self.parameters = parameters

    def add_node_pmids(self):
        """
        Iterate over all the nodes in the knowledge graph, decorate with PMID's from pubmed abstracts
        :return: response
        """
        self.response.debug(f"Adding node PMIDs")
        self.response.info(f"Adding pubmed ID's to nodes based on occurrence in PubMed abstracts")
        self.response.warning(f"Utilizing API calls to NCBI eUtils, so this may take a while...")
        name = "pubmed_ids"
        type = "EDAM:data_0971"
        value = ""
        url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

        # iterate over KG edges, add the information
        try:
            for key, node in self.message.knowledge_graph.nodes.items():
                # Make sure the edge_attributes are not None
                if not node.node_attributes:
                    node.node_attributes = []  # should be an array, but why not a list?
                # now go and actually get the NGD
                node_curie = key
                node_name = node.name
                pmids = NGD.get_pmids_for_all([node_curie], [node_name])[0]  # since the function was designed for multiple inputs, but I only want the first

                if 'max_num' in self.parameters:
                    pmids = pmids[0:self.parameters['max_num']]
                value = pmids
                ngd_edge_attribute = NodeAttribute(type=type, name=name, value=value, url=url)  # populate the NGD edge attribute
                node.node_attributes.append(ngd_edge_attribute)  # append it to the list of attributes
        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(tb, error_code=error_type.__name__)
            self.response.error(f"Something went wrong adding the PubMed ID attributes")
        else:
            self.response.info(f"PubMed ID's successfully added to nodes")

        return self.response