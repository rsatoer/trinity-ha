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
# Wordt verstuurd als er nieuwe informatie over app-versies is (of het token verandert).
SIGNAAL_RELEASES = "trinity_releases"

# Updates van de app: de (privé) repo op GitHub, gelezen met een token uit de opties van de hub.
CONF_GITHUB_TOKEN = "github_token"
APP_REPO = "rsatoer/trinity-app"
APK_PAD = "/api/trinity/apk"

ROLLEN = ["kiosk", "achtergrond", "smartspeaker"]
