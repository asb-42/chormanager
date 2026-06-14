"""TDD RED: Regression tests for m8-FIX-A — YAML-Fallback in config.py.

``load_voice_groups``, ``load_fields`` and ``load_app_config`` must NOT
crash with a bare ``FileNotFoundError`` / ``yaml.YAMLError`` if the
shipped YAML file is missing or malformed. They must return a safe
default and log a warning instead.
"""
from __future__ import annotations

import logging
import os
from unittest import mock

import pytest


@pytest.fixture(autouse=True)
def _clear_caches():
    """Always start each test with cleared lru_caches."""
    from chormanager import config
    if hasattr(config.load_voice_groups, "cache_clear"):
        config.load_voice_groups.cache_clear()
    if hasattr(config.load_fields, "cache_clear"):
        config.load_fields.cache_clear()
    if hasattr(config.load_app_config, "cache_clear"):
        config.load_app_config.cache_clear()
    yield
    if hasattr(config.load_voice_groups, "cache_clear"):
        config.load_voice_groups.cache_clear()
    if hasattr(config.load_fields, "cache_clear"):
        config.load_fields.cache_clear()
    if hasattr(config.load_app_config, "cache_clear"):
        config.load_app_config.cache_clear()


def test_load_voice_groups_returns_list_when_yaml_missing(tmp_path, caplog):
    from chormanager import config
    missing = tmp_path / "voice_groups.yaml"
    with mock.patch.object(config, "CONFIG_DIR", tmp_path):
        with caplog.at_level(logging.WARNING):
            groups = config.load_voice_groups()
    assert isinstance(groups, list)
    # A warning must have been logged.
    assert any("voice_groups" in r.message or "missing" in r.message.lower()
               or "fallback" in r.message.lower() for r in caplog.records)


def test_load_fields_returns_list_when_yaml_missing(tmp_path, caplog):
    from chormanager import config
    with mock.patch.object(config, "CONFIG_DIR", tmp_path):
        with caplog.at_level(logging.WARNING):
            fields = config.load_fields()
    assert isinstance(fields, list)
    assert any("fields" in r.message or "missing" in r.message.lower()
               or "fallback" in r.message.lower() for r in caplog.records)


def test_load_app_config_returns_dict_when_yaml_missing(tmp_path, caplog):
    from chormanager import config
    with mock.patch.object(config, "CONFIG_DIR", tmp_path):
        with caplog.at_level(logging.WARNING):
            cfg = config.load_app_config()
    assert isinstance(cfg, dict)
    assert any("app_config" in r.message or "missing" in r.message.lower()
               or "fallback" in r.message.lower() for r in caplog.records)


# Inputs below are genuine yaml.scanner.ParserError / ScannerError.
# (A scalar like ":[invalid" is *valid* YAML and returns a str -- that's
#  handled by the isinstance check, not the exception handler.)


def test_load_voice_groups_returns_list_on_yaml_error(tmp_path, caplog):
    """If the YAML is malformed, we should get a list, not a crash."""
    from chormanager import config
    bad = tmp_path / "voice_groups.yaml"
    bad.write_text("this is: : not valid: yaml: ::\n  - {name: x, order: 1}: extra", encoding="utf-8")
    with mock.patch.object(config, "CONFIG_DIR", tmp_path):
        with caplog.at_level(logging.WARNING):
            groups = config.load_voice_groups()
    assert isinstance(groups, list)
    assert any("YAML" in r.message or "yaml" in r.message.lower() or "error" in r.message.lower()
               for r in caplog.records)


def test_load_fields_returns_list_on_yaml_error(tmp_path, caplog):
    from chormanager import config
    bad = tmp_path / "fields.yaml"
    bad.write_text(":\n  - broken\n  : : extra", encoding="utf-8")
    with mock.patch.object(config, "CONFIG_DIR", tmp_path):
        with caplog.at_level(logging.WARNING):
            fields = config.load_fields()
    assert isinstance(fields, list)
    assert any("YAML" in r.message or "yaml" in r.message.lower() or "error" in r.message.lower()
               for r in caplog.records)


def test_load_app_config_returns_dict_on_yaml_error(tmp_path, caplog):
    from chormanager import config
    bad = tmp_path / "app.yaml"
    bad.write_text(":\n  - broken\n  : : extra", encoding="utf-8")
    with mock.patch.object(config, "CONFIG_DIR", tmp_path):
        with caplog.at_level(logging.WARNING):
            cfg = config.load_app_config()
    assert isinstance(cfg, dict)
    assert any("YAML" in r.message or "yaml" in r.message.lower() or "error" in r.message.lower()
               for r in caplog.records)


# Additional: when YAML is *valid* but a scalar (not a mapping), we still
# return the default without raising. This is the silent-recovery path
# (no warning, because the file parsed fine).
def test_load_fields_returns_list_on_scalar_yaml(tmp_path, caplog):
    from chormanager import config
    bad = tmp_path / "fields.yaml"
    bad.write_text(":[invalid", encoding="utf-8")  # valid scalar
    with mock.patch.object(config, "CONFIG_DIR", tmp_path):
        with caplog.at_level(logging.WARNING):
            fields = config.load_fields()
    assert isinstance(fields, list)
    assert fields == []


def test_load_voice_groups_returns_list_on_scalar_yaml(tmp_path, caplog):
    from chormanager import config
    bad = tmp_path / "voice_groups.yaml"
    bad.write_text(":[invalid", encoding="utf-8")
    with mock.patch.object(config, "CONFIG_DIR", tmp_path):
        with caplog.at_level(logging.WARNING):
            groups = config.load_voice_groups()
    assert isinstance(groups, list)
    assert groups == []


def test_load_app_config_returns_dict_on_scalar_yaml(tmp_path, caplog):
    from chormanager import config
    bad = tmp_path / "app.yaml"
    bad.write_text(":[invalid", encoding="utf-8")
    with mock.patch.object(config, "CONFIG_DIR", tmp_path):
        with caplog.at_level(logging.WARNING):
            cfg = config.load_app_config()
    assert isinstance(cfg, dict)
    assert cfg == {}


def test_load_voice_groups_still_works_with_valid_yaml(tmp_path):
    """Sanity check: a valid YAML in the patched CONFIG_DIR is returned."""
    from chormanager import config
    good = tmp_path / "voice_groups.yaml"
    good.write_text(
        "voice_groups:\n"
        "  - {name: Sopran, order: 1}\n"
        "  - {name: Bass, order: 2}\n",
        encoding="utf-8",
    )
    with mock.patch.object(config, "CONFIG_DIR", tmp_path):
        groups = config.load_voice_groups()
    assert [g["name"] for g in groups] == ["Sopran", "Bass"]


def test_load_fields_still_works_with_valid_yaml(tmp_path):
    from chormanager import config
    good = tmp_path / "fields.yaml"
    good.write_text(
        "fields:\n"
        "  - {name: full_name, order: 1, required: true}\n",
        encoding="utf-8",
    )
    with mock.patch.object(config, "CONFIG_DIR", tmp_path):
        fields = config.load_fields()
    assert fields and fields[0]["name"] == "full_name"


def test_load_app_config_still_works_with_valid_yaml(tmp_path):
    from chormanager import config
    good = tmp_path / "app.yaml"
    good.write_text("app:\n  name: ChorManager\n", encoding="utf-8")
    with mock.patch.object(config, "CONFIG_DIR", tmp_path):
        cfg = config.load_app_config()
    assert cfg == {"app": {"name": "ChorManager"}}
