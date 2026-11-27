"""Koppelen: de integratie één keer toevoegen, en daarna per tablet bevestigen met een code."""

from __future__ import annotations

import hmac
import re
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.typing import DiscoveryInfoType

from .const import CONF_CODE, CONF_NAAM, CONF_TABLET_ID, DOMAIN, HUB_ID, SOORT, SOORT_HUB, SOORT_TABLET
from .tablets import Tablets


class TrinityConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow voor Trinity."""

    VERSION = 1

    def __init__(self) -> None:
        self._tablet_id: str | None = None
        self._naam: str | None = None

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """De integratie toevoegen: daarna kunnen tablets zich melden."""
        await self.async_set_unique_id(HUB_ID)
        self._abort_if_unique_id_configured()
        if user_input is not None:
            return self.async_create_entry(title="Trinity", data={SOORT: SOORT_HUB})
        return self.async_show_form(step_id="user")

    async def async_step_integration_discovery(
        self, discovery_info: DiscoveryInfoType
    ) -> ConfigFlowResult:
        """Een tablet heeft zich gemeld en is nog niet gekoppeld."""
        self._tablet_id = discovery_info[CONF_TABLET_ID]
        self._naam = discovery_info[CONF_NAAM]
        await self.async_set_unique_id(self._tablet_id)
        self._abort_if_unique_id_configured()
        self.context["title_placeholders"] = {"naam": self._naam}
        return await self.async_step_bevestig()

    async def async_step_bevestig(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Bevestigen met de code die op de tablet staat."""
        errors: dict[str, str] = {}
        if user_input is not None:
            tablets: Tablets | None = self.hass.data.get(DOMAIN)
            tablet = tablets.get(self._tablet_id) if tablets and self._tablet_id else None
            code = re.sub(r"\D", "", user_input[CONF_CODE])
            if tablet is None or tablet.code is None:
                errors["base"] = "tablet_weg"
            elif not hmac.compare_digest(code, tablet.code):
                errors[CONF_CODE] = "code_onjuist"
            else:
                return self.async_create_entry(
                    title=tablet.naam,
                    data={SOORT: SOORT_TABLET, CONF_TABLET_ID: tablet.tablet_id, CONF_NAAM: tablet.naam},
                )
        return self.async_show_form(
            step_id="bevestig",
            data_schema=vol.Schema({vol.Required(CONF_CODE): str}),
            errors=errors,
            description_placeholders={"naam": self._naam or ""},
        )
