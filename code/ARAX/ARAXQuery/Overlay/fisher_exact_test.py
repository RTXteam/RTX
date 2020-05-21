#!/bin/env python3
# This class will perform fisher's exact test to evalutate the significance of connection between
# a list of nodes with certain type in KG and each of the adjacent nodes with specified type.

# relative imports
import scipy.stats as stats
from ARAX_expander import ARAXExpander
from ARAX_overlay import ARAXOverlay
from ARAX_filter_kg import ARAXFilterKG
from ARAX_resultify import ARAXResultify
from ARAX_filter_results import ARAXFilterResults
from ARAX_messenger import ARAXMessenger

class ComputeFTEST:

    #### Constructor
    def __init__(self, response, message, parameters):
        self.response = response
        self.message = message
        self.parameters = parameters

    def fisher_exact_test(self):
        """
        Iterate over all the adjacent nodes with 'compare_node_label' (e.g. "protein") type with respect to the nodes with
        'query_node_label' (e.g. "biological_process") type in the knowledge graph to compute the p-value and assign it to
        its node attribute
        :return: response
        """
        self.response.debug(f"Adding node PMIDs")
        self.response.info(f"Adding pubmed ID's to nodes based on occurrence in PubMed abstracts")
        self.response.warning(f"Utilizing API calls to NCBI eUtils, so this may take a while...")
        name = "pubmed_ids"
        type = "list of PMIDS (as a string)"
        value = ""
        url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

        # iterate over KG edges, add the information
        try:
            for node in self.message.knowledge_graph.nodes:
                # Make sure the edge_attributes are not None
                if not node.node_attributes:
                    node.node_attributes = []  # should be an array, but why not a list?
                # now go and actually get the NGD
                node_curie = node.id
                node_name = node.name
                pmids = NGD.get_pmids_for_all([node_curie], [node_name])[0]  # since the function was designed for multiple inputs, but I only want the first

                if 'max_num' in self.parameters:
                    pmids = pmids[0:self.parameters['max_num']]
                value = str(pmids)
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

    def size_of_given_type_in_KG(self,type):
