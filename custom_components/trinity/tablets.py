"""Wat de integratie per tablet bijhoudt: gegevens, staat en de open verbinding."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import secrets
import time
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
    # Momentopnamen: openstaande verzoeken en de laatste foto.
    fotos: dict[str, asyncio.Future[bytes | None]] = field(default_factory=dict)
    laatste_foto: bytes | None = None
    laatste_foto_tijd: float = 0.0

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

    async def foto(self, hass: HomeAssistant, wacht: float = 10.0) -> bytes | None:
        """Een momentopname van de camera van de tablet.

        Een foto van minder dan vijf seconden oud gaat opnieuw mee: een dashboard vraagt er
        vaak om, en elke nieuwe zet de camera van de tablet even aan. Lukt het niet, dan de
        laatste foto (of None).
        """
        if self.laatste_foto is not None and time.monotonic() - self.laatste_foto_tijd < 5:
            return self.laatste_foto
        lopend = next((f for f in self.fotos.values() if not f.done()), None)
        if lopend is not None:
            try:
                async with asyncio.timeout(wacht):
                    return await asyncio.shield(lopend) or self.laatste_foto
            except TimeoutError:
                return self.laatste_foto
        verzoek = secrets.token_hex(8)
        toekomst: asyncio.Future[bytes | None] = hass.loop.create_future()
        self.fotos[verzoek] = toekomst
        try:
            if not self.stuur("foto", verzoek=verzoek):
                return self.laatste_foto
            async with asyncio.timeout(wacht):
                return await asyncio.shield(toekomst) or self.laatste_foto
        except TimeoutError:
            return self.laatste_foto
        finally:
            self.fotos.pop(verzoek, None)
            if not toekomst.done():
                toekomst.set_result(None)

    @callback
    def foto_ontvangen(self, verzoek: str, jpeg: bytes) -> None:
        """De tablet stuurt een foto terug."""
        self.laatste_foto = jpeg
        self.laatste_foto_tijd = time.monotonic()
        toekomst = self.fotos.get(verzoek)
        if toekomst is not None and not toekomst.done():
            toekomst.set_result(jpeg)

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
