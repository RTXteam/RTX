
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
