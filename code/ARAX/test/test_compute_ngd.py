#!/usr/bin/env python3
"""
Unit tests for the NGD calculation in Overlay/compute_ngd.py.

These exercise the calculation directly against an injected PMID map, so they need neither
the multi-GB curie_to_pmids sqlite database nor any network access, and they run in about a
second. The end-to-end behaviour of `overlay(action=compute_ngd)` is covered by
test_ARAX_overlay.py.

Every test that checks a value checks it against `_reference_ngd` below, which is the
calculation exactly as it stood before PMID sets were cached (issue #2879). The point of that
change was to stop rebuilding the same sets thousands of times, not to compute anything
different, so "identical to the old implementation" is the specification.

Usage:
  pytest -v test_compute_ngd.py
"""

import math
import os
import sqlite3
import sys
from collections import OrderedDict

import pytest

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../ARAXQuery/Overlay")
from compute_ngd import ComputeNGD
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../ARAXQuery")
from util import connect_to_sqlite_read_only

NGD_NORMALIZER = 3.5e+7 * 20


# ---------------------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------------------

def _reference_ngd(pmid_map, subject_curie, object_curie):
    """The pre-#2879 calculation, kept verbatim as the thing the current code must match."""
    if subject_curie not in pmid_map or object_curie not in pmid_map:
        return math.nan, set()
    pubmed_id_sets = [set(pmid_map[subject_curie]), set(pmid_map[object_curie])]
    joint_pubmed_ids = pubmed_id_sets[0].intersection(pubmed_id_sets[1])
    marginal_counts = [len(s) for s in pubmed_id_sets]
    joint_count = len(joint_pubmed_ids)
    if 0 in marginal_counts or joint_count == 0:
        return math.nan, joint_pubmed_ids
    value = ((max(math.log(count) for count in marginal_counts) - math.log(joint_count)) /
             (math.log(NGD_NORMALIZER) - min(math.log(count) for count in marginal_counts)))
    return value, joint_pubmed_ids


class _SilentResponse:
    """Stands in for ARAXResponse; calculate_ngd_fast only ever logs on it."""
    def debug(self, *args, **kwargs):
        pass


class _CountingPmidMap(dict):
    """A PMID map that records every lookup, so tests can count how often a set gets built."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lookups = []

    def __getitem__(self, key):
        self.lookups.append(key)
        return super().__getitem__(key)


def _make_computer(pmid_map, cache_max_pmids=None):
    """Build a ComputeNGD without running __init__, which would open the real sqlite database."""
    computer = ComputeNGD.__new__(ComputeNGD)
    computer.response = _SilentResponse()
    computer.curie_to_pmids_map = pmid_map
    computer.pmid_set_cache = OrderedDict()
    computer.pmid_set_cache_n_pmids = 0
    computer.ngd_normalizer = NGD_NORMALIZER
    computer.first_ngd_log = True
    if cache_max_pmids is not None:
        computer.PMID_SET_CACHE_MAX_PMIDS = cache_max_pmids
    return computer


def _assert_matches_reference(computer, pmid_map, pairs):
    for subject_curie, object_curie in pairs:
        actual_value, actual_pmids = computer.calculate_ngd_fast(subject_curie, object_curie)
        expected_value, expected_pmids = _reference_ngd(pmid_map, subject_curie, object_curie)

        if math.isnan(expected_value):
            assert math.isnan(actual_value), f"{subject_curie}--{object_curie} should be nan"
        else:
            assert actual_value == expected_value, f"{subject_curie}--{object_curie} value changed"

        # The publications attribute samples at most 30 of the shared PMIDs; which 30 depends on
        # set iteration order, so compare the count and membership rather than the exact sample.
        assert len(actual_pmids) == min(len(expected_pmids), 30)
        assert set(actual_pmids) <= expected_pmids


def _hub_and_spokes_map():
    """One heavily-cited curie plus many lightly-cited ones -- the creative-mode shape."""
    pmid_map = {"MONDO:hub": list(range(0, 4000))}
    for index in range(60):
        start = index * 37
        pmid_map[f"CHEBI:{index}"] = list(range(start, start + 120))
    pmid_map["CHEBI:disjoint"] = list(range(900000, 900050))
    pmid_map["CHEBI:empty"] = []
    return pmid_map


def _all_pairs_map(n_nodes=6, hub_size=3000):
    """N comparably expensive curies, to be scored against each other in every combination."""
    return {f"NCBIGene:{index}": list(range(index * 500, index * 500 + hub_size))
            for index in range(n_nodes)}


def _all_pairs(curies):
    return [(a, b) for i, a in enumerate(curies) for b in curies[i + 1:]]


# ---------------------------------------------------------------------------------------
# The calculation still produces the same numbers
# ---------------------------------------------------------------------------------------

def test_hub_and_spokes_matches_reference():
    """One pinned curie against many candidates -- what a creative-mode 'treats' query does."""
    pmid_map = _hub_and_spokes_map()
    computer = _make_computer(pmid_map)
    pairs = [("MONDO:hub", curie) for curie in pmid_map if curie != "MONDO:hub"]
    _assert_matches_reference(computer, pmid_map, pairs)


def test_all_pairs_matches_reference():
    """Six comparable curies scored against each other -- no single obvious hub to cache."""
    pmid_map = _all_pairs_map(n_nodes=6)
    computer = _make_computer(pmid_map)
    _assert_matches_reference(computer, pmid_map, _all_pairs(sorted(pmid_map)))


def test_reversed_argument_order_gives_the_same_value():
    """NGD is symmetric, and which side is bigger must not change the answer."""
    pmid_map = _hub_and_spokes_map()
    computer = _make_computer(pmid_map)
    forward, forward_pmids = computer.calculate_ngd_fast("MONDO:hub", "CHEBI:3")
    backward, backward_pmids = computer.calculate_ngd_fast("CHEBI:3", "MONDO:hub")
    assert forward == backward
    assert len(forward_pmids) == len(backward_pmids)


def test_duplicate_pmids_do_not_inflate_the_counts():
    """Marginals are deduplicated counts; a list that repeats a PMID must not score differently."""
    clean_map = {"A": [1, 2, 3, 4, 5, 6], "B": [4, 5, 6, 7, 8]}
    dupey_map = {"A": [1, 2, 3, 4, 5, 6, 6, 3], "B": [4, 5, 6, 7, 8, 8]}

    clean_value, _ = _make_computer(clean_map).calculate_ngd_fast("A", "B")
    dupey_value, dupey_pmids = _make_computer(dupey_map).calculate_ngd_fast("A", "B")

    assert dupey_value == clean_value
    assert dupey_pmids == {4, 5, 6}
    _assert_matches_reference(_make_computer(dupey_map), dupey_map, [("A", "B")])


def test_no_shared_pmids_is_nan():
    pmid_map = _hub_and_spokes_map()
    computer = _make_computer(pmid_map)
    value, pmids = computer.calculate_ngd_fast("MONDO:hub", "CHEBI:disjoint")
    assert math.isnan(value)
    assert len(pmids) == 0


def test_curie_with_no_pmids_is_nan():
    pmid_map = _hub_and_spokes_map()
    computer = _make_computer(pmid_map)
    value, _ = computer.calculate_ngd_fast("MONDO:hub", "CHEBI:empty")
    assert math.isnan(value)


def test_curie_absent_from_the_map_is_nan():
    computer = _make_computer(_hub_and_spokes_map())
    value, pmids = computer.calculate_ngd_fast("MONDO:hub", "CHEBI:never-loaded")
    assert math.isnan(value)
    assert len(pmids) == 0


def test_publications_are_capped_at_thirty():
    """The edge's publications attribute samples the shared PMIDs; the NGD value uses all of them."""
    pmid_map = {"A": list(range(1000)), "B": list(range(500, 1500))}
    computer = _make_computer(pmid_map)
    value, pmids = computer.calculate_ngd_fast("A", "B")
    assert len(pmids) == 30
    assert pmids <= set(range(500, 1000))
    expected_value, _ = _reference_ngd(pmid_map, "A", "B")
    assert value == expected_value  # capping the sample must not change the score


# ---------------------------------------------------------------------------------------
# The PMID set cache
# ---------------------------------------------------------------------------------------

def test_cache_builds_each_hub_set_once_for_the_pinned_node_shape():
    pmid_map = _CountingPmidMap(_hub_and_spokes_map())
    computer = _make_computer(pmid_map)
    spokes = [curie for curie in sorted(pmid_map) if curie != "MONDO:hub"]
    for spoke in spokes:
        computer.calculate_ngd_fast("MONDO:hub", spoke)
    assert pmid_map.lookups.count("MONDO:hub") == 1, "the pinned curie's set was rebuilt"
    assert len(pmid_map.lookups) == 1 + len(spokes), "every set should be built exactly once"


def test_cache_builds_each_set_once_for_the_all_pairs_shape():
    """The case the ordering exists for: N comparable curies, every pair, arbitrary arrival order."""
    pmid_map = _CountingPmidMap(_all_pairs_map(n_nodes=8))
    computer = _make_computer(pmid_map)
    curies = sorted(pmid_map)
    # Deliberately shuffled relative to the grouping the ordering would produce.
    pairs = set(_all_pairs(curies))
    for subject_curie, object_curie in computer._order_node_pairs(pairs, {}):
        computer.calculate_ngd_fast(subject_curie, object_curie)
    assert len(pmid_map.lookups) == len(curies), "each curie's set should be built exactly once"


def test_cache_stays_within_its_pmid_budget():
    pmid_map = _all_pairs_map(n_nodes=12, hub_size=3000)
    computer = _make_computer(pmid_map, cache_max_pmids=5000)
    for subject_curie, object_curie in _all_pairs(sorted(pmid_map)):
        computer.calculate_ngd_fast(subject_curie, object_curie)
        # Two entries are always kept so the pair being scored cannot evict itself; beyond that
        # the cache must respect the budget.
        assert (computer.pmid_set_cache_n_pmids <= computer.PMID_SET_CACHE_MAX_PMIDS
                or len(computer.pmid_set_cache) <= 2)
    assert computer.pmid_set_cache_n_pmids == sum(len(s) for s in computer.pmid_set_cache.values())


def test_eviction_does_not_change_any_result():
    """A cache too small to hold the working set must still give the old implementation's answers."""
    pmid_map = _all_pairs_map(n_nodes=7, hub_size=2000)
    computer = _make_computer(pmid_map, cache_max_pmids=1)
    _assert_matches_reference(computer, pmid_map, _all_pairs(sorted(pmid_map)))


def test_cached_set_is_reused_not_copied():
    computer = _make_computer(_hub_and_spokes_map())
    first = computer._get_pmid_set("MONDO:hub")
    second = computer._get_pmid_set("MONDO:hub")
    assert first is second


def test_returned_publications_are_not_a_cached_set():
    """The caller truncates the shared-PMID set, so it must never be handed a cached one."""
    pmid_map = {"A": list(range(100)), "B": list(range(100))}
    computer = _make_computer(pmid_map)
    _, pmids = computer.calculate_ngd_fast("A", "B")
    assert pmids is not computer.pmid_set_cache["A"]
    assert pmids is not computer.pmid_set_cache["B"]
    assert len(computer.pmid_set_cache["A"]) == 100, "the cached set was mutated"


# ---------------------------------------------------------------------------------------
# Pair ordering
# ---------------------------------------------------------------------------------------

def test_ordering_preserves_exactly_the_pairs_it_was_given():
    pmid_map = _hub_and_spokes_map()
    computer = _make_computer(pmid_map)
    pairs = {("MONDO:hub", curie) for curie in pmid_map if curie != "MONDO:hub"}
    ordered = computer._order_node_pairs(pairs, {})
    assert len(ordered) == len(pairs)
    assert set(ordered) == pairs


def test_ordering_is_deterministic():
    pmid_map = _all_pairs_map(n_nodes=6)
    computer = _make_computer(pmid_map)
    pairs = set(_all_pairs(sorted(pmid_map)))
    assert computer._order_node_pairs(pairs, {}) == computer._order_node_pairs(pairs, {})


def test_ordering_groups_pairs_that_share_their_expensive_curie():
    """Every run of pairs sharing an anchor must be contiguous, or the cache cannot help."""
    pmid_map = _all_pairs_map(n_nodes=6, hub_size=3000)
    pmid_map["MONDO:hub"] = list(range(50000))
    computer = _make_computer(pmid_map)
    pairs = set(_all_pairs(sorted(pmid_map)))

    ordered = computer._order_node_pairs(pairs, {})
    anchors = [computer._pair_sort_key(a, b, {})[1] for a, b in ordered]
    first_seen = {}
    for position, anchor in enumerate(anchors):
        if anchor in first_seen:
            assert anchors[position - 1] == anchor, f"anchor {anchor} is not contiguous"
        else:
            first_seen[anchor] = position
    # The most expensive curie anchors the first group, so its set is built first and held.
    assert anchors[0] == "MONDO:hub"


def test_ordering_maps_through_the_canonical_curie_lookup():
    """Pairs arrive as raw curies; PMID counts are only known for canonical ones."""
    pmid_map = {"CANON:big": list(range(5000)), "CANON:small": list(range(10))}
    lookup = {"RAW:big": "CANON:big", "RAW:small": "CANON:small"}
    computer = _make_computer(pmid_map)
    key = computer._pair_sort_key("RAW:small", "RAW:big", lookup)
    assert key == (-5000, "RAW:big", "RAW:small"), "the larger curie should anchor the pair"


def test_ordering_tolerates_curies_with_no_pmid_data():
    pmid_map = {"A": [1, 2, 3]}
    computer = _make_computer(pmid_map)
    ordered = computer._order_node_pairs({("A", "MISSING"), ("MISSING", "ALSO_MISSING")}, {})
    assert len(ordered) == 2


# ---------------------------------------------------------------------------------------
# Read-only sqlite connections
# ---------------------------------------------------------------------------------------

def _make_sqlite_fixture(path, journal_mode="delete"):
    connection = sqlite3.connect(str(path))
    connection.execute(f"PRAGMA journal_mode = {journal_mode}")
    connection.execute("CREATE TABLE curie_to_pmids (curie TEXT PRIMARY KEY, pmids TEXT)")
    connection.execute("INSERT INTO curie_to_pmids VALUES ('CHEBI:1', '[1, 2, 3]')")
    connection.commit()
    connection.close()


def test_read_only_connection_reads_rows(tmp_path):
    db_path = tmp_path / "curie_to_pmids.sqlite"
    _make_sqlite_fixture(db_path)
    connection = connect_to_sqlite_read_only(str(db_path))
    try:
        assert connection.execute("SELECT pmids FROM curie_to_pmids WHERE curie = 'CHEBI:1'") \
                         .fetchone() == ('[1, 2, 3]',)
    finally:
        connection.close()


def test_read_only_connection_refuses_writes(tmp_path):
    db_path = tmp_path / "curie_to_pmids.sqlite"
    _make_sqlite_fixture(db_path)
    connection = connect_to_sqlite_read_only(str(db_path))
    try:
        with pytest.raises(sqlite3.OperationalError):
            connection.execute("INSERT INTO curie_to_pmids VALUES ('CHEBI:2', '[]')")
    finally:
        connection.close()


def test_read_only_connection_follows_a_symlink(tmp_path):
    """The databases ARAX opens are symlinks into a separate database directory."""
    db_path = tmp_path / "real.sqlite"
    _make_sqlite_fixture(db_path)
    link_path = tmp_path / "link.sqlite"
    link_path.symlink_to(db_path)
    connection = connect_to_sqlite_read_only(str(link_path))
    try:
        assert connection.execute("SELECT COUNT(*) FROM curie_to_pmids").fetchone() == (1,)
    finally:
        connection.close()


def test_read_only_connection_sees_rows_still_sitting_in_a_write_ahead_log(tmp_path):
    """
    The immutable=1 fast path makes sqlite ignore the WAL, so it must be skipped when the WAL
    holds un-checkpointed frames. Holding a writer open keeps them there.
    """
    db_path = tmp_path / "curie_to_pmids.sqlite"
    _make_sqlite_fixture(db_path, journal_mode="wal")
    writer = sqlite3.connect(str(db_path))
    writer.execute("PRAGMA wal_autocheckpoint = 0")
    writer.execute("INSERT INTO curie_to_pmids VALUES ('CHEBI:2', '[4, 5]')")
    writer.commit()
    try:
        assert (db_path.parent / (db_path.name + "-wal")).stat().st_size > 0, "no WAL to test with"
        connection = connect_to_sqlite_read_only(str(db_path))
        try:
            assert connection.execute("SELECT COUNT(*) FROM curie_to_pmids").fetchone() == (2,), \
                "a row committed to the WAL was not visible"
        finally:
            connection.close()
    finally:
        writer.close()


def test_read_only_connection_falls_back_for_an_unopenable_path(tmp_path):
    """A path that cannot be opened read-only must behave as plain sqlite3.connect() used to."""
    connection = connect_to_sqlite_read_only(str(tmp_path / "does_not_exist.sqlite"))
    assert connection is not None
    connection.close()
