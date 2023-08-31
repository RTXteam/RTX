import sys, os
import json

question_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                            'reasoningtool/QuestionAnswering')
sys.path.append(question_dir)
from Question import Question

neo4j_helper_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                                'reasoningtool/kg-construction')
sys.path.append(neo4j_helper_dir)
from Neo4jConnection import Neo4jConnection

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../")  # code directory
from RTXConfiguration import RTXConfiguration


class GenerateQuestionTerms:
    @staticmethod
    def __get_question_templates():
        question_templates = []
        with open(os.path.join(question_dir, 'Questions.tsv'), 'r') as fid:
            for line in fid.readlines():
                if line[0] == "#":
                    pass
                else:
                    question = Question(line)
                    question_templates.append(question)
        return question_templates

    @staticmethod
    def __get_node_names(type):
        # # connect to Neo4j
        # f = open(os.path.join(neo4j_helper_dir, 'config.json'), 'r')
        # config_data = f.read()
        # f.close()
        # config = json.loads(config_data)

        # create the RTXConfiguration object
        rtxConfig = RTXConfiguration()

        kg2_neo4j_info = rtxConfig.get_neo4j_info("KG2pre")

        conn = Neo4jConnection(kg2_neo4j_info['bolt'],
                               kg2_neo4j_info['username'],
                               kg2_neo4j_info['password'])
        names = conn.get_node_names(type)
        conn.close()

        return names

    @staticmethod
    def generateQuetionsToTXT():
        question_templates = GenerateQuestionTerms.__get_question_templates()

        have_writen = False
        for i, question in enumerate(question_templates):

            # retrieve the type and template from question_template
            if len(question.parameter_names) == 0:
                continue
            type = (question.parameter_names)[0]
            question_template = question.restated_question_template

            names = GenerateQuestionTerms.__get_node_names(type)

            if len(names) != 0:
                question_content = ''
                for name in names:
                    question_phase = question_template.safe_substitute({type: name})
                    question_content = question_content + question_phase + '\n'

                # write content to file
                if have_writen:
                    with open('question_terms.txt', 'a') as w_f:
                        w_f.write(question_content)
                else:
                    with open('question_terms.txt', 'w') as w_f:
                        w_f.write(question_content)
                        have_writen = True


if __name__ == '__main__':
    GenerateQuestionTerms.generateQuetionsToTXT()
