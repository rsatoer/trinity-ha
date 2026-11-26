"""Trinity: wandtablets met de Trinity-app als apparaat in Home Assistant."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from . import diensten, websocket
from .const import CONF_NAAM, CONF_TABLET_ID, DOMAIN, SOORT, SOORT_TABLET
from .tablets import Tablet, Tablets

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.BINARY_SENSOR, Platform.NUMBER, Platform.SELECT, Platform.SENSOR, Platform.SWITCH]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type TrinityConfigEntry = ConfigEntry[Tablet]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Eén keer bij het laden: de opdrachten voor tablets en de acties."""
    hass.data[DOMAIN] = Tablets(hass)
    websocket.async_registreer(hass)
    diensten.async_registreer(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: TrinityConfigEntry) -> bool:
    """Een koppeling laden. De ontvangst (hub) heeft zelf geen apparaten."""
    if entry.data.get(SOORT) != SOORT_TABLET:
        return True
    tablets: Tablets = hass.data[DOMAIN]
    tablet = tablets.zoek_of_maak(entry.data[CONF_TABLET_ID], entry.data[CONF_NAAM])
    entry.runtime_data = tablet
    if tablet.code is not None:
        # Net gekoppeld: de tablet hoeft de code niet meer te tonen.
        tablet.code = None
        tablet.stuur("gekoppeld")
        _LOGGER.info("Tablet %s gekoppeld", tablet.naam)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: TrinityConfigEntry) -> bool:
    if entry.data.get(SOORT) != SOORT_TABLET:
        return True
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Een tablet ontkoppeld: hij krijgt een nieuwe code en verschijnt weer bij Ontdekt."""
    if entry.data.get(SOORT) != SOORT_TABLET:
        return
    tablets: Tablets | None = hass.data.get(DOMAIN)
    tablet = tablets.get(entry.data[CONF_TABLET_ID]) if tablets else None
    if tablet is None:
        return
    tablet.maak_code()
    if tablet.stuur("ontkoppeld", code=tablet.code):
        websocket.start_koppelen(hass, tablet)
