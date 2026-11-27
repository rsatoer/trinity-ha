"""Scherm aan of uit, en wekken bij beweging."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import TrinityConfigEntry
from .entity import TrinityEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: TrinityConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    tablet = entry.runtime_data
    async_add_entities([SchermSchakelaar(tablet, "scherm"), WekkenSchakelaar(tablet, "wekken")])


class SchermSchakelaar(TrinityEntity, SwitchEntity):
    """Aan: scherm aan en Trinity in beeld. Uit: scherm uit (vraagt apparaatbeheer op de tablet)."""

    @property
    def is_on(self) -> bool | None:
        return self.staat("scherm")

    async def async_turn_on(self, **kwargs: Any) -> None:
        self.stuur("scherm", aan=True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        self.stuur("scherm", aan=False)


class WekkenSchakelaar(TrinityEntity, SwitchEntity):
    """Wekken bij beweging. Uit: sensoren en camera zetten het scherm niet aan; Camerabeweging blijft gemeld."""

    _attr_entity_category = EntityCategory.CONFIG

    @property
    def available(self) -> bool:
        # Oudere versies van de app kennen deze schakelaar nog niet.
        return super().available and "wekken" in self._tablet.staat

    @property
    def is_on(self) -> bool | None:
        return self.staat("wekken")

    async def async_turn_on(self, **kwargs: Any) -> None:
        self.stuur("wekken", aan=True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        self.stuur("wekken", aan=False)
