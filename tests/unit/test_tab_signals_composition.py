"""TDD: TabSignals (A1 composition refactor, first step).

The legacy TabRouterMixin is a God-Object helper on MainWindow.
A1-SUBPLAN-A replaces it step by step with composition. The first
step is ``TabSignals`` (QObject) and ``TabDescriptor`` (dataclass).
This module pins their behaviour.
"""
from __future__ import annotations

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys

import pytest


@pytest.fixture(scope="module")
def qapp():
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication(sys.argv)


def test_tab_descriptor_frozen():
    from chormanager.ui.tab_signals import TabDescriptor
    td = TabDescriptor(index=0, name="X", short_label="x")
    with pytest.raises(Exception):
        td.name = "Y"  # frozen dataclass must reject


def test_default_tabs_have_unique_indices():
    from chormanager.ui.tab_signals import DEFAULT_TABS
    indices = [t.index for t in DEFAULT_TABS]
    assert len(indices) == len(set(indices)), "Tab indices must be unique"


def test_get_tab_descriptor_returns_correct_tab():
    from chormanager.ui.tab_signals import (
        DEFAULT_TABS, get_tab_descriptor, TAB_PROJECTS,
    )
    td = get_tab_descriptor(TAB_PROJECTS)
    assert td is not None
    assert td.index == TAB_PROJECTS
    assert td.name == "Projekte"


def test_get_tab_descriptor_unknown_index_returns_none():
    from chormanager.ui.tab_signals import get_tab_descriptor
    assert get_tab_descriptor(9999) is None
    assert get_tab_descriptor(-1) is None


def test_tab_signals_emits_selection_changed(qapp):
    """A connected slot must receive (tab_index, selection)."""
    from chormanager.ui.tab_signals import TabSignals, TAB_PROJECTS
    sig = TabSignals()
    received = []

    def on_change(t, s):
        received.append((t, s))

    sig.selection_changed.connect(on_change)
    sig.selection_changed.emit(TAB_PROJECTS, "fake-selection")
    assert received == [(TAB_PROJECTS, "fake-selection")]


def test_tab_signals_can_be_subscribed_by_a_controller(qapp):
    """The composition pattern: a small controller connects to the
    signals without depending on MainWindow at all."""
    from chormanager.ui.tab_signals import TabSignals, TAB_SINGERS

    class _CountingController:
        def __init__(self):
            self.singer_changes = 0
            self.last_singer = None

        def on_singer_changed(self, singer):
            self.singer_changes += 1
            self.last_singer = singer

    sig = TabSignals()
    ctl = _CountingController()
    sig.singer_changed.connect(ctl.on_singer_changed)
    sig.singer_changed.emit("alice")
    sig.singer_changed.emit("bob")
    assert ctl.singer_changes == 2
    assert ctl.last_singer == "bob"


def test_tab_signals_qobject_parenting(qapp):
    """TabSignals must be a real QObject (parentable, signal-bearing)."""
    from PyQt6.QtCore import QObject
    from chormanager.ui.tab_signals import TabSignals
    sig = TabSignals()
    assert isinstance(sig, QObject)
    parent = QObject()
    child = TabSignals(parent)
    assert child.parent() is parent
