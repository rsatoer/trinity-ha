"""Helderheid van het scherm."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import TrinityConfigEntry
from .entity import TrinityEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: TrinityConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([Helderheid(entry.runtime_data, "helderheid")])


class Helderheid(TrinityEntity, NumberEntity):
    """De helderheid die de tablet nu gebruikt. Instellen zet de tablet op een vaste helderheid."""

    _attr_native_min_value = 1
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_mode = NumberMode.SLIDER

    @property
    def native_value(self) -> float | None:
        return self.staat("helderheid")

    async def async_set_native_value(self, value: float) -> None:
        self.stuur("helderheid", waarde=round(value))
