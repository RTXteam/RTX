import os
from RTXConfiguration import RTXConfiguration


def get_info_for_overlay_db_path():
    pathlist = os.path.realpath(__file__).split(os.path.sep)
    RTXindex = pathlist.index("RTX")
    filepath = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'KnowledgeSources', 'Tier0'])
    sqlite_name = RTXConfiguration().info_for_overlay_sqlite_path.split("/")[-1]
    return f"sqlite:{filepath}{os.path.sep}{sqlite_name}"


def get_curie_ngd_path():
    pathlist = os.path.realpath(__file__).split(os.path.sep)
    RTXindex = pathlist.index("RTX")
    filepath = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'KnowledgeSources', 'NormalizedGoogleDistance'])
    sqlite_name = RTXConfiguration().curie_ngd_path.split("/")[-1]
    return f"sqlite:{filepath}{os.path.sep}{sqlite_name}"

def get_curie_to_pmids_path():
    pathlist = os.path.realpath(__file__).split(os.path.sep)
    RTXindex = pathlist.index("RTX")
    filepath = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'KnowledgeSources', 'NormalizedGoogleDistance'])
    sqlite_name = RTXConfiguration().curie_to_pmids_path.split("/")[-1]
    return f"sqlite:{filepath}{os.path.sep}{sqlite_name}"


def main():
    print(get_info_for_overlay_db_path())
    print(get_curie_ngd_path())


if __name__ == "__main__":
    main()
