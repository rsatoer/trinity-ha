"""Testopzet: Home Assistant met de eigen integratie geladen."""

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture(autouse=True)
async def camera_vooraf(hass: HomeAssistant) -> None:
    """Het camera-onderdeel vóór de testverbinding laden: daarna kan het geen webadressen meer toevoegen."""
    assert await async_setup_component(hass, "camera", {})
