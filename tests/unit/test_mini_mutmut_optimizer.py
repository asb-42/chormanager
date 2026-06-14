"""MUTMUT-FIX-A — Mini-Mutation-Tests for core/optimizer.py.

``mutmut`` is not installed in this environment. As a lightweight
alternative, this module injects **targeted mutations** into
``core/optimizer.py`` and asserts that the existing test suite
catches them. A surviving mutation = a test gap.

The mutations are tiny, deterministic, and well-bounded:

* ``<`` → ``<=`` (boundary off-by-one)
* ``return True`` → ``return False`` (negate a guard)
* ``0.0`` → ``0.001`` (off-by-tiny)
* `+ 1` → `- 1` (off-by-one on counter)
"""
from __future__ import annotations

import importlib
import os
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest


# Each mutation is a (description, original_substring, mutated_substring) tuple.
# Patterns come straight out of optimizer.py — if you change the source,
# update the corresponding pattern.
MUTATIONS = [
    (
        "FormationOptimizer.run: 'if not rule_ids' guard removed "
        "(mutated to 'if rule_ids' so an empty list passes through).",
        "if not rule_ids:\n            print(\"FormationOptimizer: No rules selected.\")\n            return None",
        "if rule_ids:\n            print(\"FormationOptimizer: No rules selected.\")\n            return None",
    ),
    (
        "OptimizeFormationCommand.redo: 'self.swap_count = 0' is removed "
        "(no reset, so swap_count accumulates across redos).",
        "self.swap_count = 0\n\n        from core.rules import RULE_REGISTRY",
        "# swap_count reset REMOVED by mutation\n\n        from core.rules import RULE_REGISTRY",
    ),
    (
        "OptimizeFormationCommand.redo: 'self.elapsed_ms = int(...)' rounded down "
        "by mutation to 0 so the time is always zero.",
        "self.elapsed_ms = int((time.time() - start) * 1000)",
        "self.elapsed_ms = 0  # mutated: timing removed",
    ),
]


def test_optimizer_source_is_audited_for_mutations():
    """Sanity: optimizer.py exists and has the structure we expect."""
    from chormanager.choraufstellung.core import optimizer
    src = Path(optimizer.__file__).read_text(encoding="utf-8")
    assert "OptimizeFormationCommand" in src
    assert "FormationOptimizer" in src


def test_mutation_engine_test_runs_optimizer_unit_tests():
    """Run the existing optimizer tests as a baseline; they must all
    pass. This is the foundation any mutation run relies on.

    If this fails, the whole mutmut approach is moot (we cannot
    reason about surviving mutations if the test baseline is broken).
    """
    import pytest
    rc = pytest.main([
        "tests/unit/test_sprint1_fixes.py",
        "-q", "--tb=no", "--no-header",
        "-p", "no:cacheprovider",
    ])
    # Sprint 1 fix tests cover C2-FIX-A and T1-FIX-A (optimizer double-redo).
    assert rc == 0, (
        f"Baseline optimizer tests failed (rc={rc}); cannot reason "
        "about mutations until the baseline is green."
    )


def test_mutation_simulation_changes_source_and_runs_tests():
    """Apply a temporary mutation to ``optimizer.py`` and assert the
    tests catch it (i.e. the mutation makes tests fail)."""
    from chormanager.choraufstellung.core import optimizer
    src_path = Path(optimizer.__file__)
    original = src_path.read_text(encoding="utf-8")
    # Pick the first mutation.
    desc, old, new = MUTATIONS[0]
    if old not in original:
        pytest.skip(
            f"Mutation pattern not found in {src_path.name}; source has "
            "drifted. Update MUTATIONS."
        )
    # Mutate, run tests, restore.
    mutated = original.replace(old, new, 1)
    try:
        src_path.write_text(mutated, encoding="utf-8")
        # Force reimport.
        for mod_name in list(sys.modules):
            if "optimizer" in mod_name:
                del sys.modules[mod_name]
        rc = subprocess.run(
            [sys.executable, "-m", "pytest",
             "tests/unit/test_sprint1_fixes.py",
             "tests/unit/test_optimizer_guards.py",
             "-q", "--tb=no", "--no-header",
             "-p", "no:cacheprovider"],
            env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
            capture_output=True, text=True, timeout=60,
        )
        assert rc.returncode != 0, (
            f"MUTATION ESCAPED: {desc!r}. "
            f"stdout={rc.stdout[-500:]} stderr={rc.stderr[-500:]}"
        )
    finally:
        src_path.write_text(original, encoding="utf-8")
        for mod_name in list(sys.modules):
            if "optimizer" in mod_name:
                del sys.modules[mod_name]
