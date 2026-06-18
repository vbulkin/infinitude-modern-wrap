"""Shared helper for dynamically adding per-zone entities.

Platforms that create per-zone entities (climate, sensor) call
:func:`setup_zone_entities` instead of enumerating
``coordinator.data["zones"]` once. The helper:

  * creates entities for every zone the coordinator currently knows
    about, and
  * registers a coordinator listener so zones that appear *after* setup
    get their entities created without an integration reload.

Why this matters: a zone enabled on the thermostat post-install — or any
zone not yet present during the cold-start window before the first
config POST lands — would otherwise stay invisible in HA until the user
reloaded the integration.

This module deliberately imports Home Assistant types only under
``TYPE_CHECKING`` so the pure add-new-zones logic can be unit-tested
without a full HA test harness.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Iterable

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.helpers.entity import Entity
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import InfinitudeDataCoordinator


def setup_zone_entities(
    entry: "ConfigEntry",
    coordinator: "InfinitudeDataCoordinator",
    async_add_entities: "AddEntitiesCallback",
    factory: "Callable[[str], Iterable[Entity]]",
) -> None:
    """Create per-zone entities now and on every later zone appearance.

    ``factory(zone_id)`` returns the entities for a single zone. Each
    zone id is tracked so a coordinator refresh that re-reports existing
    zones doesn't create duplicates; only ids never seen before produce
    new entities.
    """
    known: set[str] = set()

    def _add_new_zones() -> None:
        data = coordinator.data or {}
        fresh: list = []
        for zone in data.get("zones", []):
            zid = zone.get("id")
            if zid is None or zid in known:
                continue
            known.add(zid)
            fresh.extend(factory(zid))
        if fresh:
            async_add_entities(fresh)

    # Initial population.
    _add_new_zones()
    # Future zones — unsubscribe is tied to the config entry so the
    # listener is removed cleanly on unload.
    entry.async_on_unload(coordinator.async_add_listener(_add_new_zones))
