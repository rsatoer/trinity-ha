"""De camera van de tablet: live beeld via de RTSP-stream van de app, en momentopnamen."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from homeassistant.components.camera import Camera, CameraEntityFeature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import TrinityConfigEntry
from .entity import TrinityEntity
from .tablets import Tablet


async def async_setup_entry(
    hass: HomeAssistant, entry: TrinityConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([TrinityCamera(entry.runtime_data)])


def stream_url(stream: dict[str, Any]) -> str | None:
    """rtsp://gebruiker:wachtwoord@adres:poort/pad, of None als de stream uit staat."""
    if not stream.get("aan") or not stream.get("adres"):
        return None
    gebruiker = quote(str(stream.get("gebruiker", "trinity")), safe="")
    wachtwoord = quote(str(stream.get("wachtwoord", "")), safe="")
    poort = stream.get("poort", 8554)
    pad = str(stream.get("pad", "trinity")).lstrip("/")
    return f"rtsp://{gebruiker}:{wachtwoord}@{stream['adres']}:{poort}/{pad}"


class TrinityCamera(TrinityEntity, Camera):
    """Beschikbaar als de module camera op de tablet aan staat. Live beeld alleen met de stream aan."""

    def __init__(self, tablet: Tablet) -> None:
        TrinityEntity.__init__(self, tablet, "camera")
        Camera.__init__(self)
        self._url: str | None = None

    def _camera(self) -> dict[str, Any]:
        return self.staat("camera") or {}

    def _stream(self) -> dict[str, Any]:
        return self.staat("stream") or {}

    @property
    def available(self) -> bool:
        return super().available and bool(self._camera().get("aan"))

    @property
    def supported_features(self) -> CameraEntityFeature:
        if stream_url(self._stream()):
            return CameraEntityFeature.STREAM
        return CameraEntityFeature(0)

    @property
    def is_streaming(self) -> bool:
        return bool(self._stream().get("kijkers"))

    async def stream_source(self) -> str | None:
        return stream_url(self._stream())

    async def async_camera_image(self, width: int | None = None, height: int | None = None) -> bytes | None:
        return await self._tablet.foto(self.hass)

    @callback
    def _bijgewerkt(self) -> None:
        # Nieuw adres of wachtwoord: een lopende stream van HA overzetten.
        url = stream_url(self._stream())
        if url != self._url:
            self._url = url
            if url and self.stream is not None:
                self.stream.update_source(url)
        super()._bijgewerkt()
