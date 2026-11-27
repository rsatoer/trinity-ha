"""Binaire sensoren: laden, en de camera en stream van de tablet."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import TrinityConfigEntry
from .entity import TrinityEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: TrinityConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    tablet = entry.runtime_data
    async_add_entities(
        [
            Laden(tablet, "laden"),
            Camerabeweging(tablet, "camerabeweging"),
            CameraActief(tablet, "camera_actief"),
            StreamActief(tablet, "stream_actief"),
        ]
    )


class Laden(TrinityEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.BATTERY_CHARGING

    @property
    def is_on(self) -> bool | None:
        return self.staat("laden")


class _CameraEntity(TrinityEntity):
    """Alleen beschikbaar als de module camera op de tablet aan staat."""

    def camera(self) -> dict:
        return self.staat("camera") or {}

    @property
    def available(self) -> bool:
        return super().available and bool(self.camera().get("aan"))


class Camerabeweging(_CameraEntity, BinarySensorEntity):
    """Beweging gezien door de camera van de tablet (boven de melddrempel)."""

    _attr_device_class = BinarySensorDeviceClass.MOTION

    @property
    def is_on(self) -> bool | None:
        return self.camera().get("beweging")


class CameraActief(_CameraEntity, BinarySensorEntity):
    """Staat de camera nu aan? Om te kijken (standaard met het scherm uit), voor de stream of een foto."""

    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def is_on(self) -> bool | None:
        return self.camera().get("actief")


class StreamActief(_CameraEntity, BinarySensorEntity):
    """Kijkt er nu iemand naar de stream (HA zelf, Frigate, VLC)? Alleen als de stream aan staat."""

    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def stream(self) -> dict:
        return self.staat("stream") or {}

    @property
    def available(self) -> bool:
        return super().available and bool(self.stream().get("aan"))

    @property
    def is_on(self) -> bool | None:
        return bool(self.stream().get("kijkers"))

    @property
    def extra_state_attributes(self) -> dict[str, int]:
        return {"kijkers": int(self.stream().get("kijkers") or 0)}
