"""Regression tests added after MUTMUT-FIX-A found a test gap.

``FormationOptimizer.run`` has an early-return guard for empty
``rule_ids`` and for the case when no rules resolve. The first
mutation we tried (``if not rule_ids`` flipped to ``if rule_ids``)
**escaped** the test suite. This test pins both guards so a future
regression is caught.
"""
from __future__ import annotations

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest


class _FakeRule:
    def __init__(self, name: str, is_primary: bool = True):
        self._name = name
        self.is_primary = is_primary

    def apply(self, singers, rows, cols, staggered=False):
        class _R:
            swap_count = 0
        return _R()


def _grid():
    class _G:
        rows = 2
        cols = 2
        staggered = False
        singers = []
        undo_stack = None
    return _G()


def test_run_returns_none_for_empty_rule_ids():
    from chormanager.choraufstellung.core.optimizer import FormationOptimizer
    assert FormationOptimizer.run(_grid(), []) is None


def test_run_returns_none_for_all_empty_string_rule_ids():
    from chormanager.choraufstellung.core.optimizer import FormationOptimizer
    assert FormationOptimizer.run(_grid(), ["", "", ""]) is None


def test_run_returns_command_for_valid_rule(monkeypatch):
    """Sanity: a known rule yields a command (not None)."""
    from chormanager.choraufstellung.core import optimizer as opt_mod
    from chormanager.choraufstellung.core import rules

    # Register a fake rule.
    fake = _FakeRule("FakeRule")
    rules.RULE_REGISTRY["__fake_mut_test__"] = fake
    try:
        cmd = opt_mod.FormationOptimizer.run(_grid(), ["__fake_mut_test__"])
        assert cmd is not None
        assert isinstance(cmd, opt_mod.OptimizeFormationCommand)
    finally:
        rules.RULE_REGISTRY.pop("__fake_mut_test__", None)
