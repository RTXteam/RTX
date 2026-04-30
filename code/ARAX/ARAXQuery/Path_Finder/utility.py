import os
from RTXConfiguration import RTXConfiguration


def get_kg2c_db_path():
    pathlist = os.path.realpath(__file__).split(os.path.sep)
    RTXindex = pathlist.index("RTX")
    filepath = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'KnowledgeSources', 'KG2c'])
    sqlite_name = RTXConfiguration().kg2c_sqlite_path.split("/")[-1]
    return f"sqlite:{filepath}{os.path.sep}{sqlite_name}"


def get_curie_ngd_path():
    pathlist = os.path.realpath(__file__).split(os.path.sep)
    RTXindex = pathlist.index("RTX")
    filepath = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'KnowledgeSources', 'NormalizedGoogleDistance'])
    sqlite_name = RTXConfiguration().curie_ngd_path.split("/")[-1]
    return f"sqlite:{filepath}{os.path.sep}{sqlite_name}"

def get_gandalf_mmap_path():
    pathlist = os.path.realpath(__file__).split(os.path.sep)
    RTXindex = pathlist.index("RTX")
    fileName = RTXConfiguration().gandalf_mmap_path.split("/")[-1]
    gandalf_dir = fileName.split("_tier0")[0]
    path = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'KnowledgeSources', 'Gandalf', gandalf_dir])
    return f"gandalf:{path}"