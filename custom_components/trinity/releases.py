"""Nieuwe versies van de Trinity-app: uitgaven van de (privé) GitHub-repo, gelezen met een token.

Home Assistant haalt de APK zelf op en geeft hem via een eigen adres (met inloggen) aan de tablets.
Zo hoeft het token nooit naar een tablet.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import timedelta
import hashlib
import logging
from pathlib import Path
import re
from typing import Any

from aiohttp import ClientError, ClientTimeout, web

from homeassistant.components.http import KEY_HASS, HomeAssistantView
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import APK_PAD, APP_REPO, DOMAIN

_LOGGER = logging.getLogger(__name__)

API = "https://api.github.com"
BESTAND = re.compile(r"trinity-(\d+\.\d+\.\d+)\.apk")


@dataclass(frozen=True)
class Release:
    """De nieuwste uitgave van de app."""

    versie: str
    titel: str
    notities: str
    url: str
    apk_url: str


class GeenToegang(HomeAssistantError):
    """GitHub kent het token niet, of het kan niet bij de repo."""


def koppen(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


async def controleer_token(hass: HomeAssistant, token: str) -> str | None:
    """Kan dit token bij de repo? Een foutsleutel voor het formulier, of None als het goed is."""
    sessie = async_get_clientsession(hass)
    try:
        async with sessie.get(f"{API}/repos/{APP_REPO}", headers=koppen(token), timeout=ClientTimeout(total=15)) as r:
            if r.status == 401:
                return "invalid_auth"
            if r.status in (403, 404):
                return "geen_toegang"
            if r.status != 200:
                return "cannot_connect"
    except (ClientError, TimeoutError):
        return "cannot_connect"
    return None


def versie_getallen(versie: str | None) -> tuple[int, ...]:
    """'0.0.41-test' en 'v0.0.41' worden (0, 0, 41)."""
    if not versie:
        return ()
    m = re.match(r"v?(\d+(?:\.\d+)*)", versie.strip())
    return tuple(int(x) for x in m.group(1).split(".")) if m else ()


class Releases(DataUpdateCoordinator[Release | None]):
    """Kijkt elke zes uur of er een nieuwe uitgave is, en haalt de APK op als een tablet hem wil."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, token: str) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name="Trinity-updates",
            update_interval=timedelta(hours=6),
        )
        self._token = token
        self._map = Path(hass.config.path(DOMAIN))
        self._sha: dict[str, str] = {}
        self._slot = asyncio.Lock()

    async def _async_update_data(self) -> Release | None:
        sessie = async_get_clientsession(self.hass)
        try:
            async with sessie.get(
                f"{API}/repos/{APP_REPO}/releases/latest",
                headers=koppen(self._token),
                timeout=ClientTimeout(total=30),
            ) as r:
                if r.status in (401, 403):
                    raise UpdateFailed("GitHub weigert het token")
                if r.status == 404:
                    return None  # nog geen uitgave
                r.raise_for_status()
                data: dict[str, Any] = await r.json()
        except (ClientError, TimeoutError) as err:
            raise UpdateFailed(f"GitHub is niet bereikbaar: {err}") from err
        apk = next((a for a in data.get("assets", []) if str(a.get("name", "")).endswith(".apk")), None)
        versie = ".".join(str(x) for x in versie_getallen(data.get("tag_name")))
        if apk is None or not versie:
            return None
        return Release(
            versie=versie,
            titel=data.get("name") or f"Trinity {versie}",
            notities=data.get("body") or "",
            url=data.get("html_url") or f"https://github.com/{APP_REPO}/releases",
            apk_url=apk["url"],
        )

    def bestand(self, naam: str) -> Path | None:
        """Een opgehaalde APK, alleen met een geldige naam."""
        if not BESTAND.fullmatch(naam):
            return None
        pad = self._map / naam
        return pad if pad.is_file() else None

    async def apk(self, release: Release) -> tuple[str, str]:
        """Haal de APK op (één keer per versie). Geeft het adres voor de tablet en de SHA-256."""
        naam = f"trinity-{release.versie}.apk"
        async with self._slot:
            pad = self._map / naam
            sha = self._sha.get(naam)
            if sha is None or not await self.hass.async_add_executor_job(pad.is_file):
                data = await self._download(release.apk_url)
                sha = hashlib.sha256(data).hexdigest()
                await self.hass.async_add_executor_job(self._bewaar, naam, data)
                self._sha = {naam: sha}
                _LOGGER.info("Trinity %s opgehaald (%d bytes)", release.versie, len(data))
        return f"{APK_PAD}/{naam}", sha

    async def _download(self, url: str) -> bytes:
        """GitHub stuurt door naar een tijdelijk adres; daar gaat het token niet mee naartoe."""
        sessie = async_get_clientsession(self.hass)
        try:
            async with sessie.get(
                url,
                headers={**koppen(self._token), "Accept": "application/octet-stream"},
                allow_redirects=False,
                timeout=ClientTimeout(total=60),
            ) as r:
                if r.status == 200:
                    return await r.read()
                if r.status not in (301, 302, 303, 307, 308) or "Location" not in r.headers:
                    raise HomeAssistantError(f"GitHub antwoordt met {r.status}")
                doel = r.headers["Location"]
            async with sessie.get(doel, timeout=ClientTimeout(total=300)) as r:
                r.raise_for_status()
                return await r.read()
        except (ClientError, TimeoutError) as err:
            raise HomeAssistantError(f"Downloaden lukte niet: {err}") from err

    def _bewaar(self, naam: str, data: bytes) -> None:
        """Alleen de nieuwste APK bewaren."""
        self._map.mkdir(parents=True, exist_ok=True)
        for oud in self._map.glob("trinity-*.apk"):
            if oud.name != naam:
                oud.unlink(missing_ok=True)
        tijdelijk = self._map / f"{naam}.deel"
        tijdelijk.write_bytes(data)
        tijdelijk.replace(self._map / naam)


class ApkView(HomeAssistantView):
    """De APK voor de tablets; alleen met inloggen (de tablet gebruikt zijn eigen HA-sessie)."""

    url = APK_PAD + "/{naam}"
    name = "api:trinity:apk"
    requires_auth = True

    async def get(self, request: web.Request, naam: str) -> web.StreamResponse:
        hass = request.app[KEY_HASS]
        releases: Releases | None = hass.data[DOMAIN].releases
        pad = await hass.async_add_executor_job(releases.bestand, naam) if releases else None
        if pad is None:
            return web.Response(status=404)
        return web.FileResponse(pad, headers={"Content-Type": "application/vnd.android.package-archive"})
