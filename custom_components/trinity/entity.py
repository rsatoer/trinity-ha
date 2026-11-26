"""Basis voor de entities van een tablet."""

from __future__ import annotations

from typing import Any

from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity

from .const import DOMAIN, SIGNAAL_TABLET
from .tablets import Tablet


class TrinityEntity(Entity):
    """Een entity van één tablet. De tablet duwt zijn staat; HA hoeft niets op te vragen."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, tablet: Tablet, sleutel: str) -> None:
        self._tablet = tablet
        self._attr_unique_id = f"{tablet.tablet_id}_{sleutel}"
        self._attr_translation_key = sleutel
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, tablet.tablet_id)},
            name=tablet.naam,
            manufacturer=tablet.merk or "Trinity",
            model=tablet.model,
            sw_version=tablet.app_versie,
        )

    @property
    def available(self) -> bool:
        return self._tablet.verbonden and bool(self._tablet.staat)

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAAL_TABLET.format(self._tablet.tablet_id), self._bijgewerkt
            )
        )

    @callback
    def _bijgewerkt(self) -> None:
        self.async_write_ha_state()

    def staat(self, sleutel: str, standaard: Any = None) -> Any:
        return self._tablet.staat.get(sleutel, standaard)

    def stuur(self, opdracht: str, **gegevens: Any) -> None:
        """Stuur een opdracht; een foutmelding als de tablet niet verbonden is."""
        if not self._tablet.stuur(opdracht, **gegevens):
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="niet_verbonden",
                translation_placeholders={"naam": self._tablet.naam},
            )
