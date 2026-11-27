"""Vaste waarden voor de Trinity-integratie."""

from __future__ import annotations

DOMAIN = "trinity"

# Twee soorten config entries: één "ontvangst" (hub) die de integratie laadt,
# en één per gekoppelde tablet.
SOORT = "soort"
SOORT_HUB = "hub"
SOORT_TABLET = "tablet"
HUB_ID = "trinity_hub"

CONF_TABLET_ID = "tablet_id"
CONF_NAAM = "naam"
CONF_CODE = "code"

# Wordt verstuurd als de staat of de verbinding van een tablet verandert.
SIGNAAL_TABLET = "trinity_tablet_{}"

ROLLEN = ["kiosk", "achtergrond", "smartspeaker"]
