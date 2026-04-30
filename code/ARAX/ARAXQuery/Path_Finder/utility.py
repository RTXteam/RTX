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
    # The ARAX_database_manager.py module unpacks the tarball
    # /mnt/data/orangeboard/databases/tier0-20260408/gandalf_mmap_tier0-20260408.tar.gz"
    # into files underneath a new subdirectory "gandalf_mmap", like this:
    # /mnt/data/orangeboard/databases/tier0-20260408/gandalf_mmap/..."
    # and the database manager creates a symbolic link:
    # RTX/code/ARAX/KnowledgeSources/Gandalf/gandalf_mmap_tier0-20260408.tar.gz => \
    #     /mnt/data/orangeboard/databases/tier0-20260408/gandalf_mmap_tier0-20260408.tar.gz
    # This function is supposed to return "gandalf:/mnt/data/orangeboard/databases/tier0-20260408/gandalf_mmap"
    # but how can it construct that path?  It has to do the following:
    # (1) find the local "RTX/code/ARAX/KnowledgeSources/Gandalf" directory
    # (2) get the symbolic link "gandalf_mmap_tier0-20260408.tar.gz" from that directory
    #     (where the specific filename comes from RTXConfiguration().gandalf_mmap_path)
    # (3) resolve that symlink to absolute path
    #     /mnt/data/orangeboard/databases/tier0-20260408/gandalf_mmap_tier0-20260408.tar.gz
    # (4) remove the filename and append "/gandalf_mmap"
    gandalf_mmap_path = RTXConfiguration().gandalf_mmap_path
    gandalf_db_bundle = os.path.basename(gandalf_mmap_path)
    gandalf_dir = os.path.normpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', 'KnowledgeSources', 'Gandalf'))
    gandalf_db_bundle_local = os.path.join(gandalf_dir, gandalf_db_bundle)
    if os.path.islink(gandalf_db_bundle_local):
        gandalf_db_bundle_to_use = os.path.realpath(gandalf_db_bundle_local)
    else:
        gandalf_db_bundle_to_use = gandalf_db_bundle_local
    gandalf_mmap_dir = os.path.join(os.path.dirname(gandalf_db_bundle_to_use), 'gandalf_mmap')
    return f"gandalf:{gandalf_mmap_dir}"


def main():
    print(get_kg2c_db_path())
    print(get_curie_ngd_path())
    print(get_gandalf_mmap_path())


if __name__ == "__main__":
    main()
