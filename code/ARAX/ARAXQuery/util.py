import heapq
import os
import pathlib
import sqlite3
import sys
from typing import Iterable

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.edge import Edge


def summarize_set_elements(x: Iterable[str],
                           max_elem: int = 10) -> str:
    """
    Return a comma-delimited representation of the first max_elem elements of Iterable[str].

    - If the iterable has fewer than max_elem + 1 elements, return all elements.
    - Otherwise return the first max_elem elements in lexicographic order followed by an ellipsis.
    """
    sorted_x = heapq.nsmallest(max_elem + 1, x)
    if len(sorted_x) <= max_elem:
        return "[" + ", ".join(sorted_x) + "]"
    return "[" + ", ".join(sorted_x[:max_elem]) + ", ... ]"


def get_arax_edge_key(edge: Edge) -> str:
    """
    Build the canonical ARAX edge key for a TRAPI Edge.

    The key must stay byte-identical to the value written into the
    `arax_edge_key` column of the tier0-info-for-overlay sqlite by
    KnowledgeSources/generate_sqlite.py, otherwise lookups will miss.
    """
    qualifiers_dict = (
        {q.qualifier_type_id: q.qualifier_value for q in edge.qualifiers}
        if edge.qualifiers else {}
    )
    qualified_predicate = qualifiers_dict.get("biolink:qualified_predicate", "")
    object_direction_qualifier = qualifiers_dict.get("biolink:object_direction_qualifier", "")
    object_aspect_qualifier = qualifiers_dict.get("biolink:object_aspect_qualifier", "")

    primary_ks_sources = (
        [s.resource_id for s in edge.sources if s.resource_role == "primary_knowledge_source"]
        if edge.sources else []
    )
    primary_knowledge_source = primary_ks_sources[0] if primary_ks_sources else ""

    qualified_portion = f"{qualified_predicate}--{object_direction_qualifier}--{object_aspect_qualifier}"
    return f"{edge.subject}--{edge.predicate}--{qualified_portion}--{edge.object}--{primary_knowledge_source}"


def connect_to_sqlite_read_only(sqlite_file_path: str,
                                cache_size_mib: int = 64,
                                mmap_size_mib: int = 1024) -> sqlite3.Connection:
    """
    Open one of ARAX's never-written sqlite databases for reading, as cheaply as the file allows.

    ARAX answers each query in its own forked process, so on a busy instance dozens of
    processes open these same multi-GB files at the same time. Opening read-write (which is
    what plain `sqlite3.connect()` does) makes every one of them create, lock and then delete
    the write-ahead-log index files that sit alongside the database -- shared filesystem state
    that nothing here needs, because ARAX only ever reads these snapshots. `mode=ro` drops
    those writes and `immutable=1` additionally lets sqlite skip file locking entirely.

    `immutable=1` promises sqlite that the file cannot change while it is open, and part of
    what sqlite does with that promise is ignore any write-ahead log next to the database.
    That is only safe when the log holds no un-checkpointed frames, so this looks for a
    non-empty `-wal` file first and settles for plain `mode=ro` if it finds one. The check
    runs against the resolved path, since these databases are usually symlinks into a
    separate database directory and the `-wal` file lives beside the real file.

    Any failure to open via the URI form falls back to a plain connect, so an unusual path can
    never turn a readable database into an unreadable one.

    :param sqlite_file_path: path to the database file (a symlink to it is fine)
    :param cache_size_mib: per-connection page cache, in MiB
    :param mmap_size_mib: how much of the file sqlite may memory-map, in MiB; keep this well
        under the per-query address-space limit, since it is charged against it
    :return: an open connection
    """
    try:
        resolved_path = pathlib.Path(sqlite_file_path).resolve()
        wal_path = resolved_path.with_name(resolved_path.name + "-wal")
        has_pending_wal = wal_path.is_file() and wal_path.stat().st_size > 0
        uri = resolved_path.as_uri() + ("?mode=ro" if has_pending_wal else "?mode=ro&immutable=1")
        connection = sqlite3.connect(uri, uri=True)
    except Exception:
        connection = sqlite3.connect(sqlite_file_path)

    # sqlite's default page cache is 2 MB, which is nothing next to these files; a real cache
    # and a memory-mapped window keep repeated lookups within one query off the syscall path.
    try:
        cursor = connection.cursor()
        cursor.execute(f"PRAGMA cache_size = -{cache_size_mib * 1024}")  # negative means KiB, not pages
        cursor.execute(f"PRAGMA mmap_size = {mmap_size_mib * 1024 * 1024}")
        cursor.execute("PRAGMA temp_store = MEMORY")
        cursor.close()
    except Exception:
        pass  # pragmas are an optimization; a database that opened is still perfectly usable

    return connection
