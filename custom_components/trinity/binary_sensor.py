"""Binaire sensoren: laden, en de camera van de tablet."""

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
    """Kijkt de camera nu? (Standaard alleen met het scherm uit of gedimd.)"""

    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def is_on(self) -> bool | None:
        return self.camera().get("actief")
