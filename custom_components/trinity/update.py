"""De app op de tablet bijwerken vanuit Home Assistant."""

from __future__ import annotations

from typing import Any

from homeassistant.components.update import UpdateEntity, UpdateEntityFeature
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import TrinityConfigEntry
from .const import DOMAIN, SIGNAAL_RELEASES
from .entity import TrinityEntity
from .releases import Release, Releases, versie_getallen
from .tablets import Tablet, Tablets

# Fasen die de tablet meldt terwijl hij bijwerkt.
BEZIG = {"downloaden", "installeren", "bevestigen"}


async def async_setup_entry(
    hass: HomeAssistant, entry: TrinityConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([AppUpdate(entry.runtime_data)])


class AppUpdate(TrinityEntity, UpdateEntity):
    """Nieuwe versie van Trinity voor deze tablet. Alleen beschikbaar met een GitHub-token bij de integratie."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_supported_features = (
        UpdateEntityFeature.INSTALL | UpdateEntityFeature.PROGRESS | UpdateEntityFeature.RELEASE_NOTES
    )
    _attr_title = "Trinity"

    def __init__(self, tablet: Tablet) -> None:
        super().__init__(tablet, "app")

    def _releases(self) -> Releases | None:
        tablets: Tablets = self.hass.data[DOMAIN]
        return tablets.releases

    def _release(self) -> Release | None:
        r = self._releases()
        return r.data if r else None

    def _bijwerken(self) -> dict[str, Any]:
        return self.staat("update") or {}

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(async_dispatcher_connect(self.hass, SIGNAAL_RELEASES, self._bijgewerkt))

    @property
    def available(self) -> bool:
        return super().available and self._release() is not None

    @property
    def installed_version(self) -> str | None:
        return (self.staat("systeem") or {}).get("app_versie") or self._tablet.app_versie

    @property
    def latest_version(self) -> str | None:
        r = self._release()
        return r.versie if r else None

    @property
    def release_url(self) -> str | None:
        r = self._release()
        return r.url if r else None

    @property
    def release_summary(self) -> str | None:
        r = self._release()
        return r.titel[:255] if r else None

    @property
    def in_progress(self) -> bool:
        return self._bijwerken().get("fase") in BEZIG

    @property
    def update_percentage(self) -> int | None:
        b = self._bijwerken()
        if b.get("fase") != "downloaden":
            return None
        return b.get("voortgang")

    def version_is_newer(self, latest_version: str, installed_version: str) -> bool:
        # De app heet bijvoorbeeld "0.0.41-test"; de uitgave "0.0.45". Alleen de getallen tellen.
        return versie_getallen(latest_version) > versie_getallen(installed_version)

    async def async_release_notes(self) -> str | None:
        r = self._release()
        return r.notities if r else None

    async def async_install(self, version: str | None, backup: bool, **kwargs: Any) -> None:
        releases = self._releases()
        r = self._release()
        if releases is None or r is None:
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key="geen_update")
        pad, sha = await releases.apk(r)
        self.stuur("update", versie=r.versie, pad=pad, sha256=sha)

    @callback
    def _bijgewerkt(self) -> None:
        self.async_write_ha_state()
