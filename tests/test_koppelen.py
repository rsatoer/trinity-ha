"""Koppelen, staat en opdrachten van een tablet, zoals de Trinity-app het doet."""

from __future__ import annotations

import base64

import pytest

from homeassistant import config_entries
from homeassistant.components import camera
from homeassistant.components.camera import CameraEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry as dr, entity_registry as er

from custom_components.trinity.const import DOMAIN

TABLET = {
    "tablet_id": "abc-123",
    "naam": "Wandpaneel",
    "merk": "OnePlus",
    "model": "OPD2480",
    "app_versie": "0.0.30-test",
}

STAAT = {
    "naam": "Wandpaneel",
    "rol": "kiosk",
    "scherm": True,
    "helderheid": 70,
    "helderheid_modus": "vast",
    "pagina": "p1",
    "paginas": [{"id": "p1", "naam": "Dashboard"}, {"id": "p2", "naam": "nu.nl"}],
    "lux": 120,
    "batterij": 85,
    "laden": True,
    "wekken": True,
    "camera": {"aan": True, "actief": True, "beweging": False},
    "stream": {"aan": False},
    "systeem": {
        "android": "16",
        "patch": "2026-10-01",
        "opgestart": 1764180000000,
        "app_versie": "0.0.30-test",
        "merk": "OnePlus",
        "model": "OPD2480",
    },
}


async def _hub(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()


def _ontdekt(hass: HomeAssistant) -> list[dict]:
    return [
        f
        for f in hass.config_entries.flow.async_progress_by_handler(DOMAIN)
        if f["context"]["source"] == config_entries.SOURCE_INTEGRATION_DISCOVERY
    ]


def _apparaat(hass: HomeAssistant) -> dr.DeviceEntry:
    """Het apparaat van de tablet, via een van zijn entities."""
    entity = er.async_get(hass).async_get(_entity(hass, "switch", "scherm"))
    apparaat = dr.async_get(hass).async_get(entity.device_id)
    assert apparaat is not None
    return apparaat


def _entity(hass: HomeAssistant, platform: str, sleutel: str) -> str:
    entity_id = er.async_get(hass).async_get_entity_id(platform, DOMAIN, f"abc-123_{sleutel}")
    assert entity_id, f"{platform} {sleutel} ontbreekt"
    return entity_id


async def _koppel(hass: HomeAssistant, hass_ws_client):
    """Hub toevoegen, tablet meldt zich, code bevestigen. Geeft de websocket van de tablet terug."""
    await _hub(hass)
    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "trinity/verbind", **TABLET})
    msg = await client.receive_json()
    assert msg["success"], msg
    assert msg["result"]["gekoppeld"] is False
    code = msg["result"]["code"]
    assert len(code) == 6 and code.isdigit()
    await hass.async_block_till_done()

    flows = _ontdekt(hass)
    assert len(flows) == 1
    flow_id = flows[0]["flow_id"]

    fout = "000000" if code != "000000" else "111111"
    result = await hass.config_entries.flow.async_configure(flow_id, {"code": fout})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"code": "code_onjuist"}

    # Met een spatie, zoals de tablet hem toont.
    result = await hass.config_entries.flow.async_configure(flow_id, {"code": f"{code[:3]} {code[3:]}"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Wandpaneel"
    await hass.async_block_till_done()

    msg = await client.receive_json()
    assert msg == {"id": 1, "type": "event", "event": {"opdracht": "gekoppeld"}}
    return client, result["result"]


async def test_hub_maar_een_keer(hass: HomeAssistant) -> None:
    await _hub(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "hub_bestaat"


async def test_staat_en_opdrachten(hass: HomeAssistant, hass_ws_client) -> None:
    client, _ = await _koppel(hass, hass_ws_client)

    await client.send_json({"id": 2, "type": "trinity/staat", "tablet_id": "abc-123", "staat": STAAT})
    msg = await client.receive_json()
    assert msg["success"], msg
    await hass.async_block_till_done()

    schakelaar = _entity(hass, "switch", "scherm")
    helderheid = _entity(hass, "number", "helderheid")
    pagina = _entity(hass, "select", "pagina")
    assert hass.states.get(schakelaar).state == "on"
    assert float(hass.states.get(helderheid).state) == 70
    assert hass.states.get(pagina).state == "Dashboard"
    assert hass.states.get(pagina).attributes["options"] == ["Dashboard", "nu.nl"]
    assert hass.states.get(_entity(hass, "binary_sensor", "laden")).state == "on"
    assert hass.states.get(_entity(hass, "sensor", "batterij")).state == "85"
    assert hass.states.get(_entity(hass, "sensor", "lux")).state == "120"
    assert hass.states.get(_entity(hass, "sensor", "rol")).state == "kiosk"
    assert hass.states.get(_entity(hass, "sensor", "android")).state == "16"
    assert hass.states.get(_entity(hass, "sensor", "beveiligingspatch")).state == "2026-10-01"
    assert hass.states.get(_entity(hass, "sensor", "opgestart")).state.startswith("2025-11-26T")
    assert hass.states.get(_entity(hass, "sensor", "app_versie")).state == "0.0.30-test"
    beweging = _entity(hass, "binary_sensor", "camerabeweging")
    actief = _entity(hass, "binary_sensor", "camera_actief")
    assert hass.states.get(beweging).state == "off"
    assert hass.states.get(actief).state == "on"

    apparaat = _apparaat(hass)
    assert (DOMAIN, "abc-123") in apparaat.identifiers
    assert apparaat.name == "Wandpaneel"
    assert apparaat.model == "OPD2480"

    # Camera ziet beweging; daarna de module uit: de camera-entities zijn dan niet beschikbaar.
    await client.send_json({"id": 3, "type": "trinity/staat", "tablet_id": "abc-123",
                            "staat": {**STAAT, "camera": {"aan": True, "actief": True, "beweging": True}}})
    assert (await client.receive_json())["success"]
    await hass.async_block_till_done()
    assert hass.states.get(beweging).state == "on"
    await client.send_json({"id": 4, "type": "trinity/staat", "tablet_id": "abc-123",
                            "staat": {**STAAT, "camera": {"aan": False, "actief": False, "beweging": False}}})
    assert (await client.receive_json())["success"]
    await hass.async_block_till_done()
    assert hass.states.get(beweging).state == "unavailable"
    assert hass.states.get(actief).state == "unavailable"

    # Opdrachten van HA naar de tablet.
    await hass.services.async_call("switch", "turn_off", {"entity_id": schakelaar}, blocking=True)
    assert (await client.receive_json())["event"] == {"opdracht": "scherm", "aan": False}

    await hass.services.async_call("number", "set_value", {"entity_id": helderheid, "value": 55}, blocking=True)
    assert (await client.receive_json())["event"] == {"opdracht": "helderheid", "waarde": 55}

    await hass.services.async_call("select", "select_option", {"entity_id": pagina, "option": "nu.nl"}, blocking=True)
    assert (await client.receive_json())["event"] == {"opdracht": "pagina", "id": "p2"}

    await hass.services.async_call(DOMAIN, "toon_pagina", {"tablet": apparaat.id, "pagina": "DASHBOARD"}, blocking=True)
    assert (await client.receive_json())["event"] == {"opdracht": "pagina", "id": "p1"}

    await hass.services.async_call(DOMAIN, "herlaad_pagina", {"tablet": apparaat.id}, blocking=True)
    assert (await client.receive_json())["event"] == {"opdracht": "herlaad", "id": None}

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(DOMAIN, "toon_pagina", {"tablet": apparaat.id, "pagina": "bestaat niet"}, blocking=True)

    # Nieuwe naam op de tablet: apparaat en koppeling volgen.
    await client.send_json({"id": 5, "type": "trinity/staat", "tablet_id": "abc-123", "staat": {**STAAT, "naam": "Keuken"}})
    assert (await client.receive_json())["success"]
    await hass.async_block_till_done()
    assert _apparaat(hass).name == "Keuken"
    assert hass.config_entries.async_entry_for_domain_unique_id(DOMAIN, "abc-123").title == "Keuken"

    # Verbinding weg: entities niet beschikbaar.
    await client.close()
    await hass.async_block_till_done()
    assert hass.states.get(schakelaar).state == "unavailable"


async def test_gekoppelde_tablet_meldt_zich_opnieuw(hass: HomeAssistant, hass_ws_client) -> None:
    client, _ = await _koppel(hass, hass_ws_client)
    await client.close()
    await hass.async_block_till_done()

    nieuw = await hass_ws_client(hass)
    await nieuw.send_json({"id": 1, "type": "trinity/verbind", **TABLET})
    msg = await nieuw.receive_json()
    assert msg["success"]
    assert msg["result"] == {"gekoppeld": True, "code": None}
    await hass.async_block_till_done()
    assert _ontdekt(hass) == []


async def test_ontkoppelen(hass: HomeAssistant, hass_ws_client) -> None:
    client, entry = await _koppel(hass, hass_ws_client)
    assert await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()

    msg = await client.receive_json()
    assert msg["event"]["opdracht"] == "ontkoppeld"
    assert len(msg["event"]["code"]) == 6
    assert len(_ontdekt(hass)) == 1


async def test_staat_van_onbekende_tablet(hass: HomeAssistant, hass_ws_client) -> None:
    await _hub(hass)
    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "trinity/staat", "tablet_id": "onbekend", "staat": STAAT})
    msg = await client.receive_json()
    assert not msg["success"]
    assert msg["error"]["code"] == "not_found"


async def _staat(client, nummer: int, staat: dict) -> None:
    await client.send_json({"id": nummer, "type": "trinity/staat", "tablet_id": "abc-123", "staat": staat})
    assert (await client.receive_json())["success"]


async def test_wekken(hass: HomeAssistant, hass_ws_client) -> None:
    client, _ = await _koppel(hass, hass_ws_client)
    await _staat(client, 2, STAAT)
    await hass.async_block_till_done()

    wekken = _entity(hass, "switch", "wekken")
    assert hass.states.get(wekken).state == "on"
    await hass.services.async_call("switch", "turn_off", {"entity_id": wekken}, blocking=True)
    assert (await client.receive_json())["event"] == {"opdracht": "wekken", "aan": False}

    # Een oudere app zonder deze schakelaar: niet beschikbaar.
    zonder = {k: v for k, v in STAAT.items() if k != "wekken"}
    await _staat(client, 3, zonder)
    await hass.async_block_till_done()
    assert hass.states.get(wekken).state == "unavailable"


async def test_camera_stream_en_foto(hass: HomeAssistant, hass_ws_client) -> None:
    client, _ = await _koppel(hass, hass_ws_client)
    stream = {
        "aan": True,
        "adres": "192.168.1.50",
        "poort": 8554,
        "pad": "trinity",
        "gebruiker": "trinity",
        "wachtwoord": "ge/heim+",
        "kijkers": 0,
    }
    await _staat(client, 2, {**STAAT, "stream": stream})
    await hass.async_block_till_done()

    cam = _entity(hass, "camera", "camera")
    toestand = hass.states.get(cam)
    assert toestand.state == "idle"
    assert toestand.attributes["supported_features"] == CameraEntityFeature.STREAM
    assert await camera.async_get_stream_source(hass, cam) == "rtsp://trinity:ge%2Fheim%2B@192.168.1.50:8554/trinity"
    bekeken = _entity(hass, "binary_sensor", "stream_actief")
    assert hass.states.get(bekeken).state == "off"

    # Momentopname: HA vraagt, de tablet antwoordt over dezelfde verbinding.
    taak = hass.async_create_task(camera.async_get_image(hass, cam))
    msg = await client.receive_json()
    assert msg["event"]["opdracht"] == "foto"
    jpeg = b"\xff\xd8\xff\xe0nep\xff\xd9"
    await client.send_json(
        {
            "id": 3,
            "type": "trinity/foto",
            "tablet_id": "abc-123",
            "verzoek": msg["event"]["verzoek"],
            "jpeg": base64.b64encode(jpeg).decode(),
        }
    )
    assert (await client.receive_json())["success"]
    assert (await taak).content == jpeg
    # Kort daarna dezelfde foto, zonder de tablet opnieuw te vragen.
    assert (await camera.async_get_image(hass, cam)).content == jpeg

    # Een andere verbinding mag geen foto voor deze tablet sturen.
    ander = await hass_ws_client(hass)
    await ander.send_json({"id": 1, "type": "trinity/foto", "tablet_id": "abc-123", "verzoek": "x", "jpeg": ""})
    assert not (await ander.receive_json())["success"]

    # Iemand kijkt.
    await _staat(client, 4, {**STAAT, "stream": {**stream, "kijkers": 1}})
    await hass.async_block_till_done()
    assert hass.states.get(bekeken).state == "on"
    assert hass.states.get(cam).state == "streaming"

    # Stream uit: geen live beeld, wel de camera voor foto's.
    await _staat(client, 5, STAAT)
    await hass.async_block_till_done()
    assert hass.states.get(cam).attributes["supported_features"] == 0
    assert await camera.async_get_stream_source(hass, cam) is None
    assert hass.states.get(bekeken).state == "unavailable"

    # Module camera uit: niet beschikbaar.
    await _staat(client, 6, {**STAAT, "camera": {"aan": False, "actief": False, "beweging": False}})
    await hass.async_block_till_done()
    assert hass.states.get(cam).state == "unavailable"
