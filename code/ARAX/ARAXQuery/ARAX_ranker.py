#!/bin/env python3
import sys
def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

import os
import json
import ast
import re
from datetime import datetime
import numpy as np

from response import Response
from query_graph_info import QueryGraphInfo
from knowledge_graph_info import KnowledgeGraphInfo
from ARAX_messenger import ARAXMessenger

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../")
from RTXConfiguration import RTXConfiguration


class ARAXRanker:

    # #### Constructor
    def __init__(self):
        self.response = None
        self.message = None
        self.parameters = None


    # #### ############################################################################################
    # #### For each result[], aggregate all available confidence metrics and other scores to compute a final score
    def aggregate_scores(self, message, response=None):

        # #### Set up the response object if one is not already available
        if response is None:
            if self.response is None:
                response = Response()
            else:
                response = self.response
        else:
            self.response = response
        self.message = message

        # #### Compute some basic information about the query_graph
        query_graph_info = QueryGraphInfo()
        result = query_graph_info.assess(message)
        #response.merge(result)
        #if result.status != 'OK':
        #    print(response.show(level=Response.DEBUG))
        #    return response

        # DMK FIXME: This need to be refactored so that:
        #    1. The attribute names are dynamically mapped to functions that handle their weightings (for ease of renaming attribute names)
        #    2. Weighting of individual attributes (eg. "probability" should be trusted MUCH less than "probability_treats")
        #    3. Auto-handling of normalizing scores to be in [0,1] (eg. observed_expected ration \in (-inf, inf) while probability \in (0,1)
        #    4. Auto-thresholding of values (eg. if chi_square <0.05, penalize the most, if probability_treats < 0.8, penalize the most, etc.)
        #    5. Allow for ranked answers (eg. observed_expected can have a single, huge value, skewing the rest of them

        # #### Iterate through all the edges in the knowledge graph to:
        # #### 1) Create a dict of all edges by id
        # #### 2) Collect some min,max stats for edge_attributes that we may need later
        kg_edges = {}
        score_stats = {}
        for edge in message.knowledge_graph.edges:
            kg_edges[edge.id] = edge
            if edge.edge_attributes is not None:
                for edge_attribute in edge.edge_attributes:
                    # FIXME: DMK: We should probably have some some way to dynamically get the attribute names since they appear to be constantly changing
                    # DMK: Crazy idea: have the individual ARAXi commands pass along their attribute names along with what they think of is a good way to handle them
                    # DMK: eg. "higher is better" or "my range of [0, inf]" or "my value is a probability", etc.
                    for attribute_name in [ 'probability', 'normalized_google_distance', 'jaccard_index',
                                            'probability_treats', 'paired_concept_frequency',
                                            'observed_expected_ratio', 'chi_square']:
                        if edge_attribute.name == attribute_name:
                            if attribute_name not in score_stats:
                                score_stats[attribute_name] = {'minimum': None, 'maximum': None}  # FIXME: doesn't handle the case when all values are inf or NaN
                            value = float(edge_attribute.value)
                            # TODO: don't set to max here, since returning inf for some edge attributes means "I have no data"
                            #if np.isinf(value):
                            #    value = 9999
                            # initialize if not None already
                            if not np.isinf(value) and not np.isinf(-value) and not np.isnan(value):  # Ignore inf, -inf, and nan
                                if not score_stats[attribute_name]['minimum']:
                                    score_stats[attribute_name]['minimum'] = value
                                if not score_stats[attribute_name]['maximum']:
                                    score_stats[attribute_name]['maximum'] = value
                                if value > score_stats[attribute_name]['maximum']:  # DMK FIXME: expected type 'float', got 'None' instead
                                    score_stats[attribute_name]['maximum'] = value
                                if value < score_stats[attribute_name]['minimum']:  # DMK FIXME: expected type 'float', got 'None' instead
                                    score_stats[attribute_name]['minimum'] = value
        response.info(f"Summary of available edge metrics: {score_stats}")

        # #### Loop through the results[] in order to compute aggregated scores
        i_result = 0
        for result in message.results:
            #response.debug(f"Metrics for result {i_result}  {result.essence}: ")

            # #### Begin with a default score of 1.0 for everything
            score = 1.0

            # #### There are often many edges associated with a result[]. Some are great, some are terrible.
            # #### For now, the score will be based on the best one. Maybe combining probabilities in quadrature would be better
            best_probability = 0.0  # TODO: What's this? the best probability of what?

            eps = np.finfo(np.float).eps  # epsilon to avoid division by 0
            penalize_factor = 0.7  # multiplicative factor to penalize by if the KS/KP return NaN or Inf indicating they haven't seen it before

            # #### Loop through each edge in the result
            for edge in result.edge_bindings:
                kg_edge_id = edge.kg_id

                # #### Set up a string buffer to keep some debugging information that could be printed
                buf = ''

                # #### If the edge has a confidence value, then multiply that into the final score
                if kg_edges[kg_edge_id].confidence is not None:
                    buf += f" confidence={kg_edges[kg_edge_id].confidence}"
                    score *= float(kg_edges[kg_edge_id].confidence)

                # #### If the edge has attributes, loop through those looking for scores that we know how to handle
                if kg_edges[kg_edge_id].edge_attributes is not None:
                    for edge_attribute in kg_edges[kg_edge_id].edge_attributes:

                        # FIXME: These are chemical_substance->protein binding probabilities, may not want be treating them like this....
                        #### EWD: Vlado has suggested that any of these links with chemical_substance->protein binding probabilities are 
                        #### EWD: mostly junk. very low probablility of being correct. His opinion seemed to be that they shouldn't be in the KG
                        #### EWD: If we keep them, maybe their probabilities should be knocked down even further, in half, in quarter..
                        # DMK: I agree: hence why I said we should probably not be treating them like this (and not trusting them a lot)

                        # #### If the edge_attribute is named 'probability', then for now use it to record the best probability only
                        if edge_attribute.name == 'probability':
                            value = float(edge_attribute.value)
                            buf += f" probability={edge_attribute.value}"
                            if value > best_probability:
                                best_probability = value

                        # #### If the edge_attribute is named 'probability_drug_treats', then for now we won't do anything
                        # #### because this value also seems to be copied into the edge confidence field, so is already
                        # #### taken into account
                        #if edge_attribute.name == 'probability_drug_treats':               # this is already put in confidence
                        #    buf += f" probability_drug_treats={edge_attribute.value}"
                        #    score *= value
                        # DMK FIXME: Do we actually have 'probability_drug_treats' attributes?, the probability_drug_treats is *not* put in the confidence see: confidence = None in `predict_drug_treats_disease.py`
                        # DMK: also note the edge type is: edge_type = "probably_treats"

                        # If the edge_attribute is named 'probability_treats', use the value more or less as a probability
                        #### EWD says: but note that when I last worked on this, the probability_treats was repeated in an edge attribute
                        #### EWD says: as well as in the edge confidence score, so I commented out this section (see immediately above) DMK (same re: comment above :) )
                        #### EWD says: so that it wouldn't be counted twice. But that may have changed in the mean time.
                        if edge_attribute.name == "probability_treats":
                            prob_treats = float(edge_attribute.value)
                            # Don't treat as a good prediction if the ML model returns a low value
                            if prob_treats < penalize_factor:
                                factor = penalize_factor
                            else:
                                factor = prob_treats
                            score *= factor  # already a number between 0 and 1, so just multiply

                        # #### If the edge_attribute is named 'ngd', then use some hocus pocus to convert to a confidence
                        if edge_attribute.name == 'normalized_google_distance':
                            ngd = float(edge_attribute.value)
                            # If the distance is infinite, then set it to 10, a very large number in this context
                            if np.isinf(ngd):
                                ngd = 10.0
                            buf += f" ngd={ngd}"

                            # #### Apply a somewhat arbitrary transformation such that:
                            # #### NGD = 0.3 leads to a factor of 1.0. That's *really* close
                            # #### NGD = 0.5 leads to a factor of 0.88. That still a close NGD
                            # #### NGD = 0.7 leads to a factor of 0.76. Same ballpark
                            # #### NGD = 0.9 this is pretty far away. Still the factor is 0.64. Distantly related
                            # #### NGD = 1.0 is very far. Still, factor is 0.58. Grade inflation is rampant.
                            factor = 1 - ( ngd - 0.3) * 0.6

                            # Apply limits of 1.0 and 0.01 to the linear fudge
                            if factor < 0.01:
                                factor = 0.01
                            if factor > 1:
                                factor = 1.0
                            buf += f" ngd_factor={factor}"
                            score *= factor

                        # #### If the edge_attribute is named 'jaccard_index', then use some hocus pocus to convert to a confidence
                        if edge_attribute.name == 'jaccard_index':
                            jaccard = float(edge_attribute.value)
                            # If the jaccard index is infinite, set to some arbitrarily bad score
                            if np.isinf(jaccard):
                                jaccard = 0.01

                            # #### Set the confidence factor so that the best value of all results here becomes 0.95
                            # #### Why not 1.0? Seems like in scenarios where we're computing a Jaccard index, nothing is really certain
                            factor = jaccard / score_stats['jaccard_index']['maximum'] * 0.95
                            buf += f" jaccard={jaccard}, factor={factor}"
                            score *= factor

                        # If the edge_attribute is named 'paired_concept_frequency', then ...
                        if edge_attribute.name == "paired_concept_frequency":
                            paired_concept_freq = float(edge_attribute.value)
                            if np.isinf(paired_concept_freq) or np.isnan(paired_concept_freq):
                                factor = penalize_factor
                            else:
                                try:
                                    factor = paired_concept_freq / score_stats['paired_concept_frequency']['maximum']
                                except:
                                    factor = paired_concept_freq / (score_stats['paired_concept_frequency']['maximum'] + eps)
                            score *= factor
                            buf += f" paired_concept_frequency={paired_concept_freq}, factor={factor}"

                        # If the edge_attribute is named 'observed_expected_ratio', then ...
                        if edge_attribute.name == 'observed_expected_ratio':
                            obs_exp_ratio = float(edge_attribute.value)
                            if np.isinf(obs_exp_ratio) or np.isnan(obs_exp_ratio):
                                factor = penalize_factor  # Penalize for missing info
                            # Would love to throw this into a sigmoid like function customized by the max value observed
                            # for now, just throw into a sigmoid and see what happens
                            factor = 1 / float(1 + np.exp(-4*obs_exp_ratio))
                            score *= factor
                            buf += f" observed_expected_ratio={obs_exp_ratio}, factor={factor}"

                        # If the edge_attribute is named 'chi_square', then compute a factor based on the chisq and the max chisq
                        if edge_attribute.name == 'chi_square':
                            chi_square = float(edge_attribute.value)
                            if np.isinf(chi_square) or np.isnan(chi_square):
                                factor = penalize_factor
                            else:
                                try:
                                    factor = 1 - (chi_square / score_stats['chi_square']['maximum'])  # lower is better
                                except:
                                    factor = 1 - (chi_square / (score_stats['chi_square']['maximum'] + eps))  # lower is better
                            score *= factor
                            buf += f" chi_square={chi_square}, factor={factor}"

                # #### When debugging, log the edge_id and the accumulated information in the buffer
                #response.debug(f"  - {kg_edge_id}  {buf}")

            # #### If there was a best_probability recorded, then multiply into the running score
            #### EWD: This was commented out by DMK? I don't know why. I think it should be here             FIXME
            #if best_probability > 0.0:
            #    score *= best_probability
            # DMK: for some reason, this was causing my scores to be ridiculously low, so I commented it out and confidences went up "quite a bit"

            # #### Make all scores at least 0.01. This is all way low anyway, but let's not have anything that rounds to zero
            # #### This is a little bad in that 0.005 becomes better than 0.011, but this is all way low, so who cares
            if score < 0.01:
                score += 0.01

            #### Round to reasonable precision. Keep only 3 digits after the decimal 
            score = int(score * 1000 + 0.5) / 1000.0

            #response.debug(f"  ---> final score={score}")
            result.confidence = score
            result.row_data = [ score, result.essence, result.essence_type ]
            i_result += 1

        #### Add table columns name
        message.table_column_names = [ 'confidence', 'essence', 'essence_type' ]

        #### Re-sort the final results
        message.results.sort(key=lambda result: result.confidence, reverse=True)


    # #### ############################################################################################
    # #### For each result[], aggregate all available confidence metrics and other scores to compute a final score
    def sort_results_by_confidence(self, message, response=None):

        # #### Set up the response object if one is not already available
        if response is None:
            if self.response is None:
                response = Response()
            else:
                response = self.response
        else:
            self.response = response
        self.message = message

        response.info("Re-sorting results by overal confidence metrics")

        #### Dead-simple sort, probably not very robust
        message.results.sort(key=lambda result: result.confidence, reverse=True)


    # #### ############################################################################################
    # #### For each result[], create a simple tabular entry of the essence values and confidence
    def create_tabular_results(self, message, response=None):

        # #### Set up the response object if one is not already available
        if response is None:
            if self.response is None:
                response = Response()
            else:
                response = self.response
        else:
            self.response = response
        self.message = message

        response.info(f"Add simple tabular results to the Message")

        # #### Loop through the results[] adding row_data for that result
        for result in message.results:

            # #### For now, just the confidence, essence, and essence_type
            result.row_data = [ result.confidence, result.essence, result.essence_type ]

        #### Add table columns name
        message.table_column_names = [ 'confidence', 'essence', 'essence_type' ]



##########################################################################################
def main():

    #### Create a response object
    response = Response()
    ranker = ARAXRanker()

    #### Get a Message to work on
    messenger = ARAXMessenger()
    print("INFO: Fetching message to work on from arax.rtx.ai",flush=True)
    message = messenger.fetch_message('https://arax.rtx.ai/api/rtx/v1/message/2614')
    if message is None:
        print("ERROR: Unable to fetch message")
        return

    ranker.aggregate_scores(message,response=response)

    #### Show the final result
    print(response.show(level=Response.DEBUG))
    print("Results:")
    for result in message.results:
        confidence = result.confidence
        if confidence is None:
            confidence = 0.0
        print("  -" + '{:6.3f}'.format(confidence) + f"\t{result.essence}")
    #print(json.dumps(ast.literal_eval(repr(message)),sort_keys=True,indent=2))


if __name__ == "__main__": main()
