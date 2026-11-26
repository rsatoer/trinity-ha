"""De WebSocket-opdrachten waarmee tablets zich melden en hun staat doorgeven.

De tablet heeft al een ingelogde verbinding met HA (voor de bewegingssensoren). Daarover:

- ``trinity/verbind``: een abonnement. Het antwoord zegt of de tablet gekoppeld is, en zo
  niet, welke code hij moet tonen. Zolang het abonnement loopt, stuurt de integratie
  hierover opdrachten (scherm, helderheid, pagina).
- ``trinity/staat``: de actuele staat van de tablet, voor de entities.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.config_entries import SOURCE_INTEGRATION_DISCOVERY
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, discovery_flow

from .const import CONF_NAAM, CONF_TABLET_ID, DOMAIN
from .tablets import Tablet, Tablets


@callback
def async_registreer(hass: HomeAssistant) -> None:
    """Registreer de opdrachten (één keer, als de integratie laadt)."""
    websocket_api.async_register_command(hass, ws_verbind)
    websocket_api.async_register_command(hass, ws_staat)


@callback
def start_koppelen(hass: HomeAssistant, tablet: Tablet) -> None:
    """Zorg voor een koppelcode en laat HA de tablet als 'ontdekt' tonen."""
    if tablet.code is None:
        tablet.maak_code()
    discovery_flow.async_create_flow(
        hass,
        DOMAIN,
        context={"source": SOURCE_INTEGRATION_DISCOVERY},
        data={CONF_TABLET_ID: tablet.tablet_id, CONF_NAAM: tablet.naam},
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "trinity/verbind",
        vol.Required("tablet_id"): str,
        vol.Required("naam"): str,
        vol.Optional("merk"): str,
        vol.Optional("model"): str,
        vol.Optional("app_versie"): str,
    }
)
@callback
def ws_verbind(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Een tablet meldt zich aan en blijft luisteren naar opdrachten."""
    tablets: Tablets = hass.data[DOMAIN]
    tablet = tablets.zoek_of_maak(msg["tablet_id"], msg["naam"])
    tablet.naam = msg["naam"]
    tablet.merk = msg.get("merk", tablet.merk)
    tablet.model = msg.get("model", tablet.model)
    tablet.app_versie = msg.get("app_versie", tablet.app_versie)

    # Een nieuwe verbinding van dezelfde tablet vervangt de oude.
    tablet.verbinding = connection
    tablet.abonnement = msg["id"]

    @callback
    def afmelden() -> None:
        if tablet.verbinding is connection and tablet.abonnement == msg["id"]:
            tablet.verbinding = None
            tablet.abonnement = None
            tablets.meld(tablet)

    connection.subscriptions[msg["id"]] = afmelden

    gekoppeld = tablets.is_gekoppeld(tablet.tablet_id)
    if gekoppeld:
        tablet.code = None
        _werk_apparaat_bij(hass, tablet)
    else:
        start_koppelen(hass, tablet)

    connection.send_result(msg["id"], {"gekoppeld": gekoppeld, "code": tablet.code})
    tablets.meld(tablet)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "trinity/staat",
        vol.Required("tablet_id"): str,
        vol.Required("staat"): dict,
    }
)
@callback
def ws_staat(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """De tablet geeft zijn staat door."""
    tablets: Tablets = hass.data[DOMAIN]
    tablet = tablets.get(msg["tablet_id"])
    if tablet is None:
        connection.send_error(msg["id"], "not_found", "Tablet heeft zich nog niet gemeld")
        return
    staat: dict[str, Any] = msg["staat"]
    tablet.staat = staat
    naam = staat.get("naam")
    if isinstance(naam, str) and naam and naam != tablet.naam:
        tablet.naam = naam
        _werk_apparaat_bij(hass, tablet)
    connection.send_result(msg["id"])
    tablets.meld(tablet)


@callback
def _werk_apparaat_bij(hass: HomeAssistant, tablet: Tablet) -> None:
    """Naam en versie van het apparaat (en de titel van de koppeling) gelijk houden aan de tablet."""
    tablets: Tablets = hass.data[DOMAIN]
    entry = tablets.entry(tablet.tablet_id)
    if entry is None:
        return
    if entry.title != tablet.naam:
        hass.config_entries.async_update_entry(
            entry, title=tablet.naam, data={**entry.data, CONF_NAAM: tablet.naam}
        )
    register = dr.async_get(hass)
    apparaat = register.async_get_device(identifiers={(DOMAIN, tablet.tablet_id)})
    if apparaat is not None:
        register.async_update_device(
            apparaat.id,
            name=tablet.naam,
            manufacturer=tablet.merk,
            model=tablet.model,
            sw_version=tablet.app_versie,
        )
