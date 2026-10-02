#!/usr/bin/env python3
"""
Unit tests for ARAXDatabaseManager.symlink_database().

The CLI path (`python3 ARAX_database_manager.py`, run by ITRB start_app.sh, the pytest
workflow and deploy/preview/deploy.sh) used to die with "ln: ...: File exists" whenever a
link was already present. These tests check that re-linking is idempotent, that a stale or
dangling link is repointed, and that a real file is never clobbered. They only touch a
pytest tmp_path, so they need no databases and no network access.

Usage:
  pytest -v test_ARAX_database_manager.py
"""

import os
import sys

import pytest

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../ARAXQuery")
from ARAX_database_manager import ARAXDatabaseManager  # noqa: E402


@pytest.fixture
def manager():
    # symlink_database() uses no instance state; skip __init__ so the test does not
    # need RTXConfiguration or create directories inside the RTX checkout.
    return ARAXDatabaseManager.__new__(ARAXDatabaseManager)


def test_symlink_database_is_idempotent(manager, tmp_path):
    target = tmp_path / "central.sqlite"
    target.write_text("db")
    link = tmp_path / "local.sqlite"
    manager.symlink_database(symlink_path=str(link), target_path=str(target))
    manager.symlink_database(symlink_path=str(link), target_path=str(target))
    assert os.readlink(link) == str(target)


@pytest.mark.parametrize("old_target", ["old-central.sqlite", "does-not-exist.sqlite"])
def test_symlink_database_repoints_stale_link(manager, tmp_path, old_target):
    (tmp_path / "old-central.sqlite").write_text("old")
    target = tmp_path / "central.sqlite"
    target.write_text("new")
    link = tmp_path / "local.sqlite"
    os.symlink(tmp_path / old_target, link)
    manager.symlink_database(symlink_path=str(link), target_path=str(target))
    assert os.readlink(link) == str(target)


def test_symlink_database_refuses_to_overwrite_real_file(manager, tmp_path):
    target = tmp_path / "central.sqlite"
    target.write_text("db")
    real_file = tmp_path / "local.sqlite"
    real_file.write_text("local copy")
    with pytest.raises(FileExistsError):
        manager.symlink_database(symlink_path=str(real_file), target_path=str(target))
    assert not real_file.is_symlink()
    assert real_file.read_text() == "local copy"
