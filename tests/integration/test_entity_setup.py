"""Unit tests for the HA integration's dynamic per-zone entity setup.

The integration normally can't be imported without Home Assistant
installed, but `entity_setup` is written HA-free (HA types are
TYPE_CHECKING-only), so we load just that module by path — bypassing the
package `__init__`, which does import HA — and exercise the pure
add-new-zones logic with lightweight fakes.

This is the first automated test for the `custom_components` side, which
otherwise has no coverage. A full harness
(pytest-homeassistant-custom-component) is a recommended follow-up for
the HA-dependent code paths (coordinator SSE, entity state, config flow).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "custom_components"
    / "infinitude_direct"
    / "entity_setup.py"
)
_spec = importlib.util.spec_from_file_location("entity_setup_under_test", _MODULE_PATH)
_entity_setup = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_entity_setup)
setup_zone_entities = _entity_setup.setup_zone_entities


class FakeCoordinator:
    def __init__(self, zones):
        self.data = {"zones": zones}
        self._listeners = []

    def async_add_listener(self, cb):
        self._listeners.append(cb)
        return lambda: self._listeners.remove(cb)

    def fire(self):
        for cb in list(self._listeners):
            cb()


class FakeEntry:
    def __init__(self):
        self.unloads = []

    def async_on_unload(self, cb):
        self.unloads.append(cb)


def _harness(zones):
    coord = FakeCoordinator(zones)
    entry = FakeEntry()
    added: list = []
    setup_zone_entities(
        entry, coord, lambda ents: added.extend(ents), lambda zid: [("e", zid)]
    )
    return coord, entry, added


def test_initial_zones_create_entities():
    _, _, added = _harness([{"id": "1"}, {"id": "2"}])
    assert added == [("e", "1"), ("e", "2")]


def test_new_zone_on_refresh_adds_only_the_new_one():
    coord, _, added = _harness([{"id": "1"}])
    assert added == [("e", "1")]
    coord.data = {"zones": [{"id": "1"}, {"id": "2"}]}
    coord.fire()
    # Only zone 2 is freshly added — zone 1 is not duplicated.
    assert added == [("e", "1"), ("e", "2")]


def test_refire_with_same_zones_adds_nothing():
    coord, _, added = _harness([{"id": "1"}, {"id": "2"}])
    coord.fire()
    coord.fire()
    assert added == [("e", "1"), ("e", "2")]


def test_listener_registered_and_unsub_tied_to_entry():
    coord, entry, _ = _harness([{"id": "1"}])
    assert len(coord._listeners) == 1
    assert len(entry.unloads) == 1
    # The registered unload removes the coordinator listener.
    entry.unloads[0]()
    assert coord._listeners == []


def test_none_coordinator_data_is_safe():
    coord = FakeCoordinator([])
    coord.data = None
    entry = FakeEntry()
    added: list = []
    setup_zone_entities(
        entry, coord, lambda ents: added.extend(ents), lambda zid: [("e", zid)]
    )
    assert added == []
    # A later refresh that populates zones still works.
    coord.data = {"zones": [{"id": "9"}]}
    coord.fire()
    assert added == [("e", "9")]


def test_zone_without_id_is_skipped():
    _, _, added = _harness([{"id": "1"}, {"name": "no id"}, {"id": "3"}])
    assert added == [("e", "1"), ("e", "3")]
