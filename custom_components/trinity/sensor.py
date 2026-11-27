"""Sensoren van de tablet: rol, lux, batterij en systeem."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import LIGHT_LUX, PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import TrinityConfigEntry
from .const import ROLLEN
from .entity import TrinityEntity
from .tablets import Tablet


def _systeem(sleutel: str) -> Callable[[dict[str, Any]], Any]:
    return lambda staat: (staat.get("systeem") or {}).get(sleutel)


def _datum(tekst: Any) -> date | None:
    try:
        return date.fromisoformat(str(tekst)) if tekst else None
    except ValueError:
        return None


def _tijdstip(ms: Any) -> datetime | None:
    try:
        return dt_util.utc_from_timestamp(int(ms) / 1000) if ms else None
    except (TypeError, ValueError):
        return None


def _rol(staat: dict[str, Any]) -> str | None:
    rol = staat.get("rol")
    return rol if rol in ROLLEN else None


@dataclass(frozen=True, kw_only=True)
class TrinitySensorBeschrijving(SensorEntityDescription):
    waarde: Callable[[dict[str, Any]], Any]


SENSOREN: tuple[TrinitySensorBeschrijving, ...] = (
    TrinitySensorBeschrijving(
        key="rol",
        translation_key="rol",
        device_class=SensorDeviceClass.ENUM,
        options=ROLLEN,
        waarde=_rol,
    ),
    TrinitySensorBeschrijving(
        key="lux",
        translation_key="lux",
        device_class=SensorDeviceClass.ILLUMINANCE,
        native_unit_of_measurement=LIGHT_LUX,
        state_class=SensorStateClass.MEASUREMENT,
        waarde=lambda staat: staat.get("lux"),
    ),
    TrinitySensorBeschrijving(
        key="batterij",
        translation_key="batterij",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        waarde=lambda staat: staat.get("batterij"),
    ),
    TrinitySensorBeschrijving(
        key="android",
        translation_key="android",
        entity_category=EntityCategory.DIAGNOSTIC,
        waarde=_systeem("android"),
    ),
    TrinitySensorBeschrijving(
        key="beveiligingspatch",
        translation_key="beveiligingspatch",
        device_class=SensorDeviceClass.DATE,
        entity_category=EntityCategory.DIAGNOSTIC,
        waarde=lambda staat: _datum(_systeem("patch")(staat)),
    ),
    TrinitySensorBeschrijving(
        key="opgestart",
        translation_key="opgestart",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        waarde=lambda staat: _tijdstip(_systeem("opgestart")(staat)),
    ),
    TrinitySensorBeschrijving(
        key="app_versie",
        translation_key="app_versie",
        entity_category=EntityCategory.DIAGNOSTIC,
        waarde=_systeem("app_versie"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: TrinityConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities(TrinitySensor(entry.runtime_data, b) for b in SENSOREN)


class TrinitySensor(TrinityEntity, SensorEntity):
    entity_description: TrinitySensorBeschrijving

    def __init__(self, tablet: Tablet, beschrijving: TrinitySensorBeschrijving) -> None:
        super().__init__(tablet, beschrijving.key)
        self.entity_description = beschrijving

    @property
    def native_value(self) -> Any:
        return self.entity_description.waarde(self._tablet.staat)
