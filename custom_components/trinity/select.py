"""De pagina die op het paneel in beeld is."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import TrinityConfigEntry
from .entity import TrinityEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: TrinityConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([HuidigePagina(entry.runtime_data, "pagina")])


def paginanamen(paginas: list[dict]) -> dict[str, str]:
    """Naam → id. Dubbele namen krijgen een nummer, zodat elke keuze uniek is."""
    namen: dict[str, str] = {}
    for p in paginas:
        naam = str(p.get("naam") or p.get("id"))
        uniek, n = naam, 2
        while uniek in namen:
            uniek, n = f"{naam} ({n})", n + 1
        namen[uniek] = str(p.get("id"))
    return namen


class HuidigePagina(TrinityEntity, SelectEntity):
    """Lezen welke pagina in beeld is, en een andere pagina kiezen."""

    def _namen(self) -> dict[str, str]:
        return paginanamen(self.staat("paginas") or [])

    @property
    def options(self) -> list[str]:
        return list(self._namen())

    @property
    def current_option(self) -> str | None:
        huidig = self.staat("pagina")
        return next((naam for naam, pid in self._namen().items() if pid == huidig), None)

    async def async_select_option(self, option: str) -> None:
        self.stuur("pagina", id=self._namen()[option])
