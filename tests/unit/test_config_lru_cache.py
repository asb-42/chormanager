"""Q-1: lru_cache on YAML loaders in chormanager.config.

Before Q-1, ``load_voice_groups()``, ``load_fields()`` and
``load_app_config()`` re-parse the YAML file on every call. These
functions are called from many places (UI construction, dialog
creation, log setup, …) and the parse cost is paid repeatedly.

After Q-1, the three functions are wrapped in ``@lru_cache`` (with
``maxsize=1`` since they take no arguments), so the YAML file is
parsed at most once per process.

These tests pin the new behaviour:

* yaml.safe_load is called at most once per loader across many
  successive invocations of the loader function.
* The function still returns the *same data* (sorting + filtering
  preserved) — cache does not change observable results.
* The cache can be invalidated explicitly via ``cache_clear()`` so
  tests and runtime code that modify the YAML file (e.g. config
  dialog) can still force a reload.
"""
from __future__ import annotations

from unittest import mock

import pytest

from chormanager import config


@pytest.fixture(autouse=True)
def _clear_caches():
    """Make sure every test starts with a clean cache so call-counts
    are deterministic across tests."""
    yield
    if hasattr(config.load_voice_groups, "cache_clear"):
        config.load_voice_groups.cache_clear()
    if hasattr(config.load_fields, "cache_clear"):
        config.load_fields.cache_clear()
    if hasattr(config.load_app_config, "cache_clear"):
        config.load_app_config.cache_clear()


# ---------------------------------------------------------------------------
# 1. load_voice_groups()
# ---------------------------------------------------------------------------

class TestLoadVoiceGroupsCached:
    def test_yaml_parse_called_at_most_once(self):
        """Five successive calls must trigger AT MOST one yaml.safe_load.

        Note: we cannot assert ``== 1`` because the lru_cache may
        already be warm from a previous test in the same session
        (e.g. test_config.py). The crucial property is that the
        function does not re-parse on every call.
        """
        # Force a cold cache for this specific loader.
        config.load_voice_groups.cache_clear()
        with mock.patch.object(
            config.yaml, "safe_load", wraps=config.yaml.safe_load
        ) as spy:
            for _ in range(5):
                config.load_voice_groups()
        assert spy.call_count == 1, (
            f"expected yaml.safe_load to be called exactly once after "
            f"cache_clear, got {spy.call_count}"
        )

    def test_cached_call_returns_same_data(self):
        first = config.load_voice_groups()
        for _ in range(10):
            assert config.load_voice_groups() == first

    def test_cache_clear_forces_reload(self):
        config.load_voice_groups()
        config.load_voice_groups()
        config.load_voice_groups.cache_clear()
        with mock.patch.object(
            config.yaml, "safe_load", wraps=config.yaml.safe_load
        ) as spy:
            config.load_voice_groups()
        assert spy.call_count == 1


# ---------------------------------------------------------------------------
# 2. load_fields()
# ---------------------------------------------------------------------------

class TestLoadFieldsCached:
    def test_yaml_parse_called_at_most_once(self):
        config.load_fields.cache_clear()
        with mock.patch.object(
            config.yaml, "safe_load", wraps=config.yaml.safe_load
        ) as spy:
            for _ in range(5):
                config.load_fields()
        assert spy.call_count == 1

    def test_cached_call_returns_same_data(self):
        first = config.load_fields()
        for _ in range(10):
            assert config.load_fields() == first

    def test_cache_clear_forces_reload(self):
        config.load_fields()
        config.load_fields.cache_clear()
        with mock.patch.object(
            config.yaml, "safe_load", wraps=config.yaml.safe_load
        ) as spy:
            config.load_fields()
        assert spy.call_count == 1


# ---------------------------------------------------------------------------
# 3. load_app_config()
# ---------------------------------------------------------------------------

class TestLoadAppConfigCached:
    def test_yaml_parse_called_at_most_once(self):
        config.load_app_config.cache_clear()
        with mock.patch.object(
            config.yaml, "safe_load", wraps=config.yaml.safe_load
        ) as spy:
            for _ in range(5):
                config.load_app_config()
        assert spy.call_count == 1

    def test_cached_call_returns_same_data(self):
        first = config.load_app_config()
        for _ in range(10):
            assert config.load_app_config() == first

    def test_cache_clear_forces_reload(self):
        config.load_app_config()
        config.load_app_config.cache_clear()
        with mock.patch.object(
            config.yaml, "safe_load", wraps=config.yaml.safe_load
        ) as spy:
            config.load_app_config()
        assert spy.call_count == 1


# ---------------------------------------------------------------------------
# 4. Sanity: existing tests still observe the right *data*
# ---------------------------------------------------------------------------

class TestCachedLoadersReturnCorrectData:
    def test_voice_groups_still_sorted_by_order(self):
        groups = config.load_voice_groups()
        orders = [g["order"] for g in groups]
        assert orders == sorted(orders)

    def test_fields_still_sorted_by_order(self):
        fields = config.load_fields()
        orders = [f["order"] for f in fields]
        assert orders == sorted(orders)

    def test_app_config_has_expected_top_keys(self):
        cfg = config.load_app_config()
        assert "app" in cfg
        assert "database" in cfg
