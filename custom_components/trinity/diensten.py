"""Acties: een pagina tonen of herladen op een tablet."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv, device_registry as dr

from .const import DOMAIN
from .tablets import Tablet, Tablets

DIENST_TOON = "toon_pagina"
DIENST_HERLAAD = "herlaad_pagina"
ATTR_TABLET = "tablet"
ATTR_PAGINA = "pagina"

SCHEMA_TOON = vol.Schema({vol.Required(ATTR_TABLET): cv.string, vol.Required(ATTR_PAGINA): cv.string})
SCHEMA_HERLAAD = vol.Schema({vol.Required(ATTR_TABLET): cv.string, vol.Optional(ATTR_PAGINA): cv.string})


@callback
def async_registreer(hass: HomeAssistant) -> None:
    hass.services.async_register(DOMAIN, DIENST_TOON, _toon, schema=SCHEMA_TOON)
    hass.services.async_register(DOMAIN, DIENST_HERLAAD, _herlaad, schema=SCHEMA_HERLAAD)


def _fout(sleutel: str, **plaatshouders: str) -> ServiceValidationError:
    return ServiceValidationError(
        translation_domain=DOMAIN, translation_key=sleutel, translation_placeholders=plaatshouders
    )


def _tablet(hass: HomeAssistant, apparaat_id: str) -> Tablet:
    """Het apparaat uit de actie → de tablet, die verbonden moet zijn."""
    apparaat = dr.async_get(hass).async_get(apparaat_id)
    tablet_id = next((i for d, i in apparaat.identifiers if d == DOMAIN), None) if apparaat else None
    tablets: Tablets = hass.data[DOMAIN]
    tablet = tablets.get(tablet_id) if tablet_id else None
    if tablet is None:
        raise _fout("onbekende_tablet")
    if not tablet.verbonden:
        raise _fout("niet_verbonden", naam=tablet.naam)
    return tablet


def _pagina_id(tablet: Tablet, pagina: str) -> str:
    """Een pagina op id of op naam (hoofdletters maken niet uit)."""
    paginas = tablet.staat.get("paginas") or []
    for p in paginas:
        if str(p.get("id")) == pagina:
            return pagina
    for p in paginas:
        if str(p.get("naam", "")).casefold() == pagina.casefold():
            return str(p.get("id"))
    raise _fout("onbekende_pagina", pagina=pagina, naam=tablet.naam)


async def _toon(call: ServiceCall) -> None:
    tablet = _tablet(call.hass, call.data[ATTR_TABLET])
    tablet.stuur("pagina", id=_pagina_id(tablet, call.data[ATTR_PAGINA]))


async def _herlaad(call: ServiceCall) -> None:
    tablet = _tablet(call.hass, call.data[ATTR_TABLET])
    pagina = call.data.get(ATTR_PAGINA)
    tablet.stuur("herlaad", id=_pagina_id(tablet, pagina) if pagina else None)
