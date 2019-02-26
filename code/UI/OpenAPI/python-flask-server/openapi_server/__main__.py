#!/usr/bin/env python3

import connexion

from openapi_server import encoder

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../../reasoningtool/QuestionAnswering")
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../../reasoningtool/kg-construction")
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../Feedback")

def main():
    app = connexion.App(__name__, specification_dir='./openapi/')
    app.app.json_encoder = encoder.JSONEncoder
    app.add_api('openapi.yaml', arguments={'title': 'OpenAPI for NCATS Biomedical Translator Reasoners'})
    app.run(port=5001, threaded=True)


if __name__ == '__main__':
    main()
