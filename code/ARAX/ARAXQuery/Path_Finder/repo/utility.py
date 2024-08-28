import os
from RTXConfiguration import RTXConfiguration


def get_kg2c_db_path():
    pathlist = os.path.realpath(__file__).split(os.path.sep)
    RTXindex = pathlist.index("RTX")
    filepath = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'KnowledgeSources', 'KG2c'])
    sqlite_name = RTXConfiguration().kg2c_sqlite_path.split("/")[-1]
    return f"{filepath}{os.path.sep}{sqlite_name}"


def get_curie_ngd_path():
    pathlist = os.path.realpath(__file__).split(os.path.sep)
    RTXindex = pathlist.index("RTX")
    filepath = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'KnowledgeSources', 'NormalizedGoogleDistance'])
    sqlite_name = RTXConfiguration().curie_ngd_path.split("/")[-1]
    return f"{filepath}{os.path.sep}{sqlite_name}"
