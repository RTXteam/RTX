# solves the SME workflow #1: target repurposing based on rare sources

import os
import sys
import argparse
import ast
# PyCharm doesn't play well with relative imports + python console + terminal
try:
    from code.reasoningtool import ReasoningUtilities as RU
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import ReasoningUtilities as RU

import FormatOutput
import networkx as nx
try:
    from QueryCOHD import QueryCOHD
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    try:
        from QueryCOHD import QueryCOHD
    except ImportError:
        sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kg-construction'))
        from QueryCOHD import QueryCOHD

from COHDUtilities import COHDUtilities
import SimilarNodesInCommon
import CustomExceptions
import numpy as np
import fisher_exact
import NormGoogleDistance
NormGoogleDistance = NormGoogleDistance.NormGoogleDistance()
# TODO: Temp file path names etc
#sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'MLtargetRepurposing/FWPredictor'))
#import predictor
#p = predictor.predictor(model_file=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'MLtargetRepurposing/FWPredictor/LogModel.pkl'))
#p.import_file(None, graph_file=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'MLtargetRepurposing/FWPredictor/rel_max.emb.gz'), map_file=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'MLtargetRepurposing/FWPredictor/map.csv'))


class QuestionFisher:

    def __init__(self):
        None

    @staticmethod
    def answer(source_list, source_type, target_type, use_json=False, num_show=20):
        """
        Answers the question 'what pathways are most enriched by $protein_list?'
        :param source_list: A list of source node ids
        :param source_type: The source node label
        :param target_type: The target node label
        :param use_json: bool, use JSON output
        :param num_show: int, number to display
        :return: none
        """
        if RU.does_connect(source_list,source_type,target_type) != 1:
            error_message = "I found no %s connected to any element of %s" %(target_type, str(source_list))
            if not use_json:
                print(error_message)
                return
            else:
                error_code = "NoPathsFound"
                response = FormatOutput.FormatResponse(3)
                response.add_error_message(error_code, error_message)
                response.print()
                return
        (target_dict, target_list) = RU.top_n_fisher_exact(source_list, source_type, target_type, n=num_show)
        target_list.reverse()
        return (target_dict, target_list)
        
    @staticmethod
    def describe():
        output = "Answers questions of the form: 'what pathways are most enriched by $protein_list?'" + "\n"
        # TODO: subsample source nodes
        return output


def main():
    parser = argparse.ArgumentParser(description="Answers questions of the form: 'what pathways are most enriched by $protein_list?'",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-s', '--source', type=str, help="source curie ID", default="UniProtKB:Q96M43")
    parser.add_argument('-t', '--target', type=str, help="target node type", default="pathway")
    parser.add_argument('-y', '--type', type=str, help="source node type", default="protein")
    parser.add_argument('-j', '--json', action='store_true', help='Flag specifying that results should be printed in JSON format (to stdout)', default=False)
    parser.add_argument('--describe', action='store_true', help='Print a description of the question to stdout and quit', default=False)
    parser.add_argument('--num_show', type=int, help='Maximum number of results to return', default=20)

    # Parse and check args
    args = parser.parse_args()
    source_arg = args.source
    target_type = args.target
    source_type = args.type
    use_json = args.json
    describe_flag = args.describe
    num_show = args.num_show

    if source_arg[0] == "[":
        if "','" not in source_arg:
            source_arg = source_arg.replace(",", "','").replace("[", "['").replace("]", "']")
        source_list = ast.literal_eval(source_arg)
        source_list_strip = []
        for source in source_list:
            source_list_strip.append(source.strip())
        source_list = source_list_strip
    else:
        source_list = [source_arg]


    # Initialize the question class
    Q = QuestionFisher()

    if describe_flag:
        res = Q.describe()
        print(res)
    else:
        # Initialize the response class
        response = FormatOutput.FormatResponse(6)
        response.response.table_column_names = ["target name", "target ID", "P value"]
        graph_weight_tuples = []
        
        p_dict, target_list = Q.answer(source_list, source_type, target_type, use_json=use_json, num_show=num_show)
        
        # print out the results
        if not use_json:
            for target_name in target_list:
                target_description = RU.get_node_property(target_name, "name", node_label=target_type)
                print("%s %f" % (target_description, p_dict[target_name]))
        else:
            #response.response.table_column_names = ["source name", "source ID", "target name", "target ID", "path weight",
            #                                        "target source google distance",
            #                                        "ML probability target treats source"]
            for target_name in target_list:
                target_description = RU.get_node_property(target_name, "name", node_label=target_type)
                target_id_old_curie = target_name.replace("CHEMBL.COMPOUND:CHEMBL", "ChEMBL:")
                confidence = p_dict[target_name]
                # populate the graph
                graph = RU.get_graph_from_nodes([target_name])
                res = response.add_subgraph(graph.nodes(data=True), graph.edges(data=True),
                                            "The target %s is enriched by %s." % (
                                                target_description, str(source_list)), confidence,
                                            return_result=True)
                res.essence = "%s" % target_description  # populate with essence of question result
                row_data = []  # initialize the row data
                #row_data.append("%s" % source_description)
                #row_data.append("%s" % source_id)
                row_data.append("%s" % target_description)
                row_data.append("%s" % target_name)
                row_data.append("%f" % confidence)
                #row_data.append("%f" % gd)
                #row_data.append("%f" % prob)
                res.row_data = row_data
            response.print()




if __name__ == "__main__":
    main()
