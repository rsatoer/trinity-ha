"""Wat de integratie per tablet bijhoudt: gegevens, staat en de open verbinding."""

from __future__ import annotations

from dataclasses import dataclass, field
import secrets
from typing import Any

from homeassistant.components import websocket_api
from homeassistant.config_entries import SOURCE_IGNORE, ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import DOMAIN, SIGNAAL_TABLET


@dataclass
class Tablet:
    """Eén tablet, gekoppeld of nog niet."""

    tablet_id: str
    naam: str
    merk: str | None = None
    model: str | None = None
    app_versie: str | None = None
    staat: dict[str, Any] = field(default_factory=dict)
    # Koppelcode zolang de tablet nog niet gekoppeld is; de tablet toont hem.
    code: str | None = None
    verbinding: websocket_api.ActiveConnection | None = None
    abonnement: int | None = None

    @property
    def verbonden(self) -> bool:
        """Heeft de tablet nu een open verbinding?"""
        return self.verbinding is not None and self.abonnement is not None

    @callback
    def stuur(self, opdracht: str, **gegevens: Any) -> bool:
        """Stuur een opdracht naar de tablet. False als hij niet verbonden is."""
        if self.verbinding is None or self.abonnement is None:
            return False
        self.verbinding.send_message(
            websocket_api.event_message(self.abonnement, {"opdracht": opdracht, **gegevens})
        )
        return True

    def maak_code(self) -> str:
        """Een nieuwe zescijferige koppelcode."""
        self.code = f"{secrets.randbelow(1_000_000):06d}"
        return self.code


class Tablets:
    """Alle tablets die zich bij deze HA hebben gemeld."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        self._tablets: dict[str, Tablet] = {}

    def get(self, tablet_id: str) -> Tablet | None:
        return self._tablets.get(tablet_id)

    def zoek_of_maak(self, tablet_id: str, naam: str) -> Tablet:
        tablet = self._tablets.get(tablet_id)
        if tablet is None:
            tablet = Tablet(tablet_id=tablet_id, naam=naam)
            self._tablets[tablet_id] = tablet
        return tablet

    def entry(self, tablet_id: str) -> ConfigEntry | None:
        """De config entry van een gekoppelde tablet (niet als hij genegeerd is)."""
        entry = self._hass.config_entries.async_entry_for_domain_unique_id(DOMAIN, tablet_id)
        if entry is None or entry.source == SOURCE_IGNORE:
            return None
        return entry

    def is_gekoppeld(self, tablet_id: str) -> bool:
        return self.entry(tablet_id) is not None

    @callback
    def meld(self, tablet: Tablet) -> None:
        """Laat de entities van deze tablet weten dat er iets veranderd is."""
        async_dispatcher_send(self._hass, SIGNAAL_TABLET.format(tablet.tablet_id))
