
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))  # ARAXQuery directory
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../")  # code directory
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/Expand/")
import expand_utilities as eu
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.knowledge_graph import KnowledgeGraph
from openapi_server.models.query_graph import QueryGraph
from openapi_server.models.q_edge import QEdge
from openapi_server.models.q_node import QNode
from openapi_server.models.edge import Edge
from openapi_server.models.query_constraint import QueryConstraint


# @ n00
query_graph_0 = QueryGraph.from_dict(
{
  "edges": {
  },
  "nodes": {
    "n00": {
      "ids": [
        "UniProtKB:O00533"
      ],
      "categories": [
        "biolink:Protein"
      ]
    }
  }
}
)

# n00  n01
# @ -- O
query_graph_1 = QueryGraph.from_dict(
{
  "edges": {
    "e00": {
      "subject": "n00",
      "object": "n01"
    }
  },
  "nodes": {
    "n00": {
      "ids": [
        "UniProtKB:O00533"
      ],
      "categories": [
        "biolink:Protein"
      ]
    },
    "n01": {
      "categories": [
        "biolink:Protein"
      ]
    }
  }
}
)

# n00  n01  n02
# @ -- O -- @
query_graph_2 = QueryGraph.from_dict(
{
  "edges": {
    "e00": {
      "subject": "n00",
      "object": "n01"
    },
    "e01": {
      "subject": "n01",
      "object": "n02"
    }
  },
  "nodes": {
    "n00": {
      "ids": [
        "FMA:74637"
      ],
      "categories": [
        "biolink:Gene"
      ]
    },
    "n01": {
      "categories": [
        "biolink:Protein"
      ]
    },
    "n02": {
      "ids": [
        "FMA:83376"
      ],
      "categories": [
        "biolink:ChemicalEntity"
      ]
    }
  }
}
)

# n00  n01  n02
# @ -- O -- @
#      |
#      O n03
query_graph_3 = QueryGraph.from_dict(
{
  "edges": {
    "e00": {
      "subject": "n00",
      "object": "n01"
    },
    "e01": {
      "subject": "n01",
      "object": "n02"
    },
    "e02": {
      "subject": "n01",
      "object": "n03"
    }
  },
  "nodes": {
    "n00": {
      "ids": [
        "FMA:74637"
      ],
      "categories": [
        "biolink:Gene"
      ]
    },
    "n01": {
      "categories": [
        "biolink:Protein"
      ]
    },
    "n02": {
      "ids": [
        "FMA:83376"
      ],
      "categories": [
        "biolink:ChemicalEntity"
      ]
    },
    "n03": {
      "categories": [
        "biolink:ChemicalEntity"
      ]
    }
  }
}
)

# n00  n01  n02
# @ -- O -- @
#      |
#      @ n03
query_graph_4 = QueryGraph.from_dict(
{
  "edges": {
    "e00": {
      "subject": "n00",
      "object": "n01"
    },
    "e01": {
      "subject": "n01",
      "object": "n02"
    },
    "e02": {
      "subject": "n01",
      "object": "n03"
    }
  },
  "nodes": {
    "n00": {
      "ids": [
        "FMA:74637"
      ],
      "categories": [
        "biolink:Gene"
      ]
    },
    "n01": {
      "categories": [
        "biolink:Protein"
      ]
    },
    "n02": {
      "ids": [
        "FMA:83376"
      ],
      "categories": [
        "biolink:ChemicalEntity"
      ]
    },
    "n03": {
      "ids": [
        "CHEMBL.COMPOUND:CHEMBL1287853"
      ],
      "categories": [
        "biolink:ChemicalEntity"
      ]
    }
  }
}
)

# n00  n01  n02
# O -- @ -- O
#      |
#      O n03
query_graph_5 = QueryGraph.from_dict(
{
  "edges": {
    "e00": {
      "subject": "n00",
      "object": "n01"
    },
    "e01": {
      "subject": "n01",
      "object": "n02"
    },
    "e02": {
      "subject": "n01",
      "object": "n03"
    }
  },
  "nodes": {
    "n00": {
      "categories": [
        "biolink:Gene"
      ]
    },
    "n01": {
      "ids": [
        "UniProtKB:O00533"
      ],
      "categories": [
        "biolink:Protein"
      ]
    },
    "n02": {
      "categories": [
        "biolink:AnatomicalEntity"
      ]
    },
    "n03": {
      "categories": [
        "biolink:ChemicalEntity"
      ]
    }
  }
}
)

# n00  n01  n02  n03
# O -- @ -- O -- O
query_graph_6 = QueryGraph.from_dict(
{
  "edges": {
    "e00": {
      "subject": "n00",
      "object": "n01"
    },
    "e01": {
      "subject": "n01",
      "object": "n02"
    },
    "e02": {
      "subject": "n01",
      "object": "n03"
    }
  },
  "nodes": {
    "n00": {
      "categories": [
        "biolink:Gene"
      ]
    },
    "n01": {
      "ids": [
        "UniProtKB:O00533"
      ],
      "categories": [
        "biolink:Protein"
      ]
    },
    "n02": {
      "categories": [
        "biolink:AnatomicalEntity"
      ]
    },
    "n03": {
      "categories": [
        "biolink:ChemicalEntity"
      ]
    }
  }
}
)

# n00  n01  n02  n03
# @ -- @ -- O -- @
query_graph_7 = QueryGraph.from_dict(
{
  "edges": {
    "e00": {
      "subject": "n00",
      "object": "n01"
    },
    "e01": {
      "subject": "n01",
      "object": "n02"
    },
    "e02": {
      "subject": "n02",
      "object": "n03"
    }
  },
  "nodes": {
    "n00": {
      "ids": [
        "FMA:74637"
      ],
      "categories": [
        "biolink:Gene"
      ]
    },
    "n01": {
      "ids": [
        "UniProtKB:O00533"
      ],
      "categories": [
        "biolink:Protein"
      ]
    },
    "n02": {
      "categories": [
        "biolink:AnatomicalEntity"
      ]
    },
    "n03": {
      "ids": [
        "FMA:83376"
      ],
      "categories": [
        "biolink:ChemicalEntity"
      ]
    }
  }
}
)

# n00  n01  n02  n03
# @ -- O -- O -- @
query_graph_8 = QueryGraph.from_dict(
{
  "edges": {
    "e00": {
      "subject": "n00",
      "object": "n01"
    },
    "e01": {
      "subject": "n01",
      "object": "n02"
    },
    "e02": {
      "subject": "n02",
      "object": "n03"
    }
  },
  "nodes": {
    "n00": {
      "ids": [
        "FMA:74637"
      ],
      "categories": [
        "biolink:Gene"
      ]
    },
    "n01": {
      "categories": [
        "biolink:Protein"
      ]
    },
    "n02": {
      "categories": [
        "biolink:AnatomicalEntity"
      ]
    },
    "n03": {
      "ids": [
        "FMA:83376"
      ],
      "categories": [
        "biolink:ChemicalEntity"
      ]
    }
  }
}
)

# n00  n01  n02  n03
# @ -- O -- O -- @
#           |
#           @ n04
query_graph_9 = QueryGraph.from_dict(
{
  "edges": {
    "e00": {
      "subject": "n00",
      "object": "n01"
    },
    "e01": {
      "subject": "n01",
      "object": "n02"
    },
    "e02": {
      "subject": "n02",
      "object": "n03"
    },
    "e03": {
      "subject": "n02",
      "object": "n04"
    }

  },
  "nodes": {
    "n00": {
      "ids": [
        "FMA:74637"
      ],
      "categories": [
        "biolink:Gene"
      ]
    },
    "n01": {
      "categories": [
        "biolink:Protein"
      ]
    },
    "n02": {
      "categories": [
        "biolink:AnatomicalEntity"
      ]
    },
    "n03": {
      "ids": [
        "FMA:83376"
      ],
      "categories": [
        "biolink:ChemicalEntity"
      ]
    },
    "n04": {
      "ids": [
        "DRUGBANK:DB00394"
      ],
      "categories": [
        "biolink:ChemicalEntity"
      ]
    }
  }
}
)

# n01 O -- @ n02
#     |    |
# n00 @ -- O n03
query_graph_10 = QueryGraph.from_dict(
{
  "edges": {
    "e00": {
      "subject": "n00",
      "object": "n01"
    },
    "e01": {
      "subject": "n01",
      "object": "n02"
    },
    "e02": {
      "subject": "n02",
      "object": "n03"
    },
    "e03": {
      "subject": "n03",
      "object": "n00"
    }
  },
  "nodes": {
    "n00": {
      "ids": [
        "FMA:74637"
      ],
      "categories": [
        "biolink:Gene"
      ]
    },
    "n01": {
      "categories": [
        "biolink:Protein"
      ]
    },
    "n02": {
      "ids": [
        "FMA:83376"
      ],
      "categories": [
        "biolink:ChemicalEntity"
      ]
    },
    "n03": {
      "categories": [
        "biolink:ChemicalEntity"
      ]
    }
  }
}
)

# n00  n01  n02  n06
# @ -- @ -- O -- @
#      |    |
#  n03 O    @ n05
#      |
#      @ n04
query_graph_11 = QueryGraph.from_dict(
{
  "edges": {
    "e00": {
      "subject": "n00",
      "object": "n01"
    },
    "e01": {
      "subject": "n01",
      "object": "n02"
    },
    "e02": {
      "subject": "n01",
      "object": "n03"
    },
    "e03": {
      "subject": "n03",
      "object": "n04"
    },
    "e04": {
      "subject": "n02",
      "object": "n05"
    },
    "e05": {
      "subject": "n02",
      "object": "n06"
    }
  },
  "nodes": {
    "n00": {
      "ids": [
        "FMA:74637"
      ],
      "categories": [
        "biolink:Gene"
      ]
    },
    "n01": {
      "ids": [
        "FMA:83376"
      ],
      "categories": [
        "biolink:Protein"
      ]
    },
    "n02": {
      "categories": [
        "biolink:ChemicalEntity"
      ]
    },
    "n03": {
      "categories": [
        "biolink:ChemicalEntity"
      ]
    },
    "n04": {
      "ids": [
        "FMA:83376"
      ],
      "categories": [
        "biolink:ChemicalEntity"
      ]
    },
    "n05": {
      "ids": [
        "FMA:83376"
      ],
      "categories": [
        "biolink:ChemicalEntity"
      ]
    },
    "n06": {
      "ids": [
        "FMA:83376"
      ],
      "categories": [
        "biolink:ChemicalEntity"
      ]
    }
  }
}
)

#  n00  n01  n02  n03  n04
#  @ -- O -- O -- O -- @
#       |\__ O __/| n05
#       \___ O __/ n06
query_graph_12 = QueryGraph.from_dict(
{
  "edges": {
    "e1": {
      "subject": "n00",
      "object": "n01"
    },
    "e2": {
      "subject": "n01",
      "object": "n02"
    },
    "e3": {
      "subject": "n02",
      "object": "n03"
    },
    "e4": {
      "subject": "n03",
      "object": "n04"
    },
    "e5": {
      "subject": "n01",
      "object": "n05"
    },
    "e6": {
      "subject": "n05",
      "object": "n03"
    },
    "e7": {
      "subject": "n01",
      "object": "n06"
    },
    "e8": {
      "subject": "n06",
      "object": "n03"
    }
  },
  "nodes": {
    "n00": {
      "ids": [
        "FMA:83376"
      ],
      "categories": [
        "biolink:ChemicalEntity"
      ]
    },
    "n01": {
      "categories": [
        "biolink:Gene"
      ]
    },
    "n02": {
      "categories": [
        "biolink:Protein"
      ]
    },
    "n03": {
      "categories": [
        "biolink:ChemicalEntity"
      ]
    },
    "n04": {
      "ids": [
        "FMA:83376"
      ],
      "categories": [
        "biolink:ChemicalEntity"
      ]
    },
    "n05": {
      "categories": [
        "biolink:ChemicalEntity"
      ]
    },
    "n06": {
      "categories": [
        "biolink:ChemicalEntity"
      ]
    }
  }
}
)

# n00  n01  n02  n03
# @ -- O -- O -- @
#     /      \
#    O -- O -- O -- O -- @
#    n04  n05  n06  n07  n08
query_graph_13 = QueryGraph.from_dict(
{
  "edges": {
    "e1": {
      "subject": "n00",
      "object": "n01"
    },
    "e2": {
      "subject": "n01",
      "object": "n02"
    },
    "e3": {
      "subject": "n02",
      "object": "n03"
    },
    "e4": {
      "subject": "n01",
      "object": "n04"
    },
    "e5": {
      "subject": "n04",
      "object": "n05"
    },
    "e6": {
      "subject": "n05",
      "object": "n06"
    },
    "e7": {
      "subject": "n02",
      "object": "n06"
    },
    "e8": {
      "subject": "n06",
      "object": "n07"
    },
    "e9": {
      "subject": "n07",
      "object": "n08"
    }
  },
  "nodes": {
    "n00": {
      "ids": [
        "FMA:83376"
      ],
      "categories": [
        "biolink:ChemicalEntity"
      ]
    },
    "n01": {
      "categories": [
        "biolink:Gene"
      ]
    },
    "n02": {
      "categories": [
        "biolink:Protein"
      ]
    },
    "n03": {
      "ids": [
        "FMA:83376"
      ],
      "categories": [
        "biolink:ChemicalEntity"
      ]
    },
    "n04": {
      "categories": [
        "biolink:ChemicalEntity"
      ]
    },
    "n05": {
      "categories": [
        "biolink:ChemicalEntity"
      ]
    },
    "n06": {
      "categories": [
        "biolink:ChemicalEntity"
      ]
    },
    "n07": {
      "categories": [
        "biolink:ChemicalEntity"
      ]
    },
    "n08": {
      "ids": [
        "FMA:83376"
      ],
      "categories": [
        "biolink:ChemicalEntity"
      ]
    }
  }
}
)

# n00  n01  n02  n03
# @ -- O -- O -- O
#           |    |
#           @ -- O -- O -- @
#           n04  n05  n06  n07
query_graph_14 = QueryGraph.from_dict(
{
  "edges": {
    "e1": {
      "subject": "n00",
      "object": "n01"
    },
    "e2": {
      "subject": "n01",
      "object": "n02"
    },
    "e3": {
      "subject": "n02",
      "object": "n04"
    },
    "e4": {
      "subject": "n02",
      "object": "n03"
    },
    "e5": {
      "subject": "n04",
      "object": "n05"
    },
    "e6": {
      "subject": "n03",
      "object": "n05"
    },
    "e7": {
      "subject": "n05",
      "object": "n06"
    },
    "e8": {
      "subject": "n06",
      "object": "n07"
    }
  },
  "nodes": {
    "n00": {
      "ids": [
        "FMA:83376"
      ],
      "categories": [
        "biolink:ChemicalEntity"
      ]
    },
    "n01": {
      "categories": [
        "biolink:Gene"
      ]
    },
    "n02": {
      "categories": [
        "biolink:Protein"
      ]
    },
    "n03": {
      "categories": [
        "biolink:ChemicalEntity"
      ]
    },
    "n04": {
      "ids": [
        "FMA:83376"
      ],
      "categories": [
        "biolink:ChemicalEntity"
      ]
    },
    "n05": {
      "categories": [
        "biolink:ChemicalEntity"
      ]
    },
    "n06": {
      "categories": [
        "biolink:ChemicalEntity"
      ]
    },
    "n07": {
      "ids": [
        "FMA:83376"
      ],
      "categories": [
        "biolink:ChemicalEntity"
      ]
    }
  }
}
)

# n00  n01  n02  n03  n04
# @ -- @ -- @ -- O -- @
#           |
#           O n05
#           |
#           @ n06
query_graph_15 = QueryGraph.from_dict(
{
  "edges": {
    "e00": {
      "subject": "n00",
      "object": "n01"
    },
    "e01": {
      "subject": "n01",
      "object": "n02"
    },
    "e02": {
      "subject": "n02",
      "object": "n03"
    },
    "e03": {
      "subject": "n03",
      "object": "n04"
    },
    "e04": {
      "subject": "n02",
      "object": "n05"
    },
    "e05": {
      "subject": "n05",
      "object": "n06"
    }
  },
  "nodes": {
    "n00": {
      "ids": [
        "FMA:74637"
      ],
      "categories": [
        "biolink:Gene"
      ]
    },
    "n01": {
      "ids": [
        "FMA:83376"
      ],
      "categories": [
        "biolink:Protein"
      ]
    },
    "n02": {
      "ids": [
        "FMA:83376"
      ],
      "categories": [
        "biolink:ChemicalEntity"
      ]
    },
    "n03": {
      "categories": [
        "biolink:ChemicalEntity"
      ]
    },
    "n04": {
      "ids": [
        "FMA:83376"
      ],
      "categories": [
        "biolink:ChemicalEntity"
      ]
    },
    "n05": {
      "categories": [
        "biolink:ChemicalEntity"
      ]
    },
    "n06": {
      "ids": [
        "FMA:83376"
      ],
      "categories": [
        "biolink:ChemicalEntity"
      ]
    }
  }
}
)

# n00  n01  n02  n03  n04
# @ -- @ -- @ -- @ -- @
#           |
#           O n05
#           |
#           @ n06
query_graph_16 = QueryGraph.from_dict(
{
  "edges": {
    "e00": {
      "subject": "n00",
      "object": "n01"
    },
    "e01": {
      "subject": "n01",
      "object": "n02"
    },
    "e02": {
      "subject": "n02",
      "object": "n03"
    },
    "e03": {
      "subject": "n03",
      "object": "n04"
    },
    "e04": {
      "subject": "n02",
      "object": "n05"
    },
    "e05": {
      "subject": "n05",
      "object": "n06"
    }
  },
  "nodes": {
    "n00": {
      "ids": [
        "FMA:74637"
      ],
      "categories": [
        "biolink:Gene"
      ]
    },
    "n01": {
      "ids": [
        "FMA:83376"
      ],
      "categories": [
        "biolink:Protein"
      ]
    },
    "n02": {
      "ids": [
        "FMA:83376"
      ],
      "categories": [
        "biolink:ChemicalEntity"
      ]
    },
    "n03": {
      "ids": [
        "FMA:83376"
      ],
      "categories": [
        "biolink:ChemicalEntity"
      ]
    },
    "n04": {
      "ids": [
        "FMA:83376"
      ],
      "categories": [
        "biolink:ChemicalEntity"
      ]
    },
    "n05": {
      "categories": [
        "biolink:ChemicalEntity"
      ]
    },
    "n06": {
      "ids": [
        "FMA:83376"
      ],
      "categories": [
        "biolink:ChemicalEntity"
      ]
    }
  }
}
)

# n00  n01  n02  n03  n04
# @ -- @ -- @ -- @ -- @
#           |
#           O n05
#           |        n07  n08
#           @ n06    @ -- O
query_graph_17 = QueryGraph.from_dict(
{
  "edges": {
    "e00": {
      "subject": "n00",
      "object": "n01"
    },
    "e01": {
      "subject": "n01",
      "object": "n02"
    },
    "e02": {
      "subject": "n02",
      "object": "n03"
    },
    "e03": {
      "subject": "n03",
      "object": "n04"
    },
    "e04": {
      "subject": "n02",
      "object": "n05"
    },
    "e05": {
      "subject": "n05",
      "object": "n06"
    },
    "e06": {
      "subject": "n07",
      "object": "n08"
    }
  },
  "nodes": {
    "n00": {
      "ids": [
        "FMA:74637"
      ],
      "categories": [
        "biolink:Gene"
      ]
    },
    "n01": {
      "ids": [
        "FMA:83376"
      ],
      "categories": [
        "biolink:Protein"
      ]
    },
    "n02": {
      "ids": [
        "FMA:83376"
      ],
      "categories": [
        "biolink:ChemicalEntity"
      ]
    },
    "n03": {
      "ids": [
        "FMA:83376"
      ],
      "categories": [
        "biolink:ChemicalEntity"
      ]
    },
    "n04": {
      "ids": [
        "FMA:83376"
      ],
      "categories": [
        "biolink:ChemicalEntity"
      ]
    },
    "n05": {
      "categories": [
        "biolink:ChemicalEntity"
      ]
    },
    "n06": {
      "ids": [
        "FMA:83376"
      ],
      "categories": [
        "biolink:ChemicalEntity"
      ]
    },
    "n07": {
      "ids": [
        "FMA:83376"
      ],
      "categories": [
        "biolink:ChemicalEntity"
      ]
    },
    "n08": {
      "categories": [
        "biolink:ChemicalEntity"
      ]
    }
  }
}
)
