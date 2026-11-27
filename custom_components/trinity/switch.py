"""Scherm aan of uit."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import TrinityConfigEntry
from .entity import TrinityEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: TrinityConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([SchermSchakelaar(entry.runtime_data, "scherm")])


class SchermSchakelaar(TrinityEntity, SwitchEntity):
    """Aan: scherm aan en Trinity in beeld. Uit: scherm uit (vraagt apparaatbeheer op de tablet)."""

    @property
    def is_on(self) -> bool | None:
        return self.staat("scherm")

    async def async_turn_on(self, **kwargs: Any) -> None:
        self.stuur("scherm", aan=True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        self.stuur("scherm", aan=False)
