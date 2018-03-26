# This script will populate Eric's standardized output object model with a given networkx neo4j instance of nodes/edges

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../")

from swagger_server.models.response import Response
from swagger_server.models.result import Result
from swagger_server.models.result_graph import ResultGraph
from swagger_server.models.node import Node
from swagger_server.models.edge import Edge
