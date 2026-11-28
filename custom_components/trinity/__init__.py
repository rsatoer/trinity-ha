"""Trinity: wandtablets met de Trinity-app als apparaat in Home Assistant."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.typing import ConfigType

from . import diensten, websocket
from .const import CONF_GITHUB_TOKEN, CONF_NAAM, CONF_TABLET_ID, DOMAIN, SIGNAAL_RELEASES, SOORT, SOORT_TABLET
from .releases import ApkView, Releases
from .tablets import Tablet, Tablets

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.CAMERA,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.UPDATE,
]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type TrinityConfigEntry = ConfigEntry[Tablet]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Eén keer bij het laden: de opdrachten voor tablets en de acties."""
    hass.data[DOMAIN] = Tablets(hass)
    websocket.async_registreer(hass)
    diensten.async_registreer(hass)
    hass.http.register_view(ApkView())
    return True


async def async_setup_entry(hass: HomeAssistant, entry: TrinityConfigEntry) -> bool:
    """Een koppeling laden. De ontvangst (hub) heeft zelf geen apparaten, wel de updates van de app."""
    if entry.data.get(SOORT) != SOORT_TABLET:
        await _start_releases(hass, entry)
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
        tablets: Tablets = hass.data[DOMAIN]
        tablets.releases = None
        async_dispatcher_send(hass, SIGNAAL_RELEASES)
        return True
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _start_releases(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Met een GitHub-token in de opties: kijken of er een nieuwe versie van de app is."""
    entry.async_on_unload(entry.add_update_listener(_opties_gewijzigd))
    token = entry.options.get(CONF_GITHUB_TOKEN)
    if not token:
        return
    releases = Releases(hass, entry, token)
    tablets: Tablets = hass.data[DOMAIN]
    tablets.releases = releases
    entry.async_on_unload(releases.async_add_listener(lambda: async_dispatcher_send(hass, SIGNAAL_RELEASES)))
    # Niet blijven hangen als GitHub even weg is: de update-entities tonen dan nog niets.
    await releases.async_refresh()
    async_dispatcher_send(hass, SIGNAAL_RELEASES)


async def _opties_gewijzigd(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


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
