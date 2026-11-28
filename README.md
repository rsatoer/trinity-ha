# Trinity voor Home Assistant

De Home Assistant-integratie voor de **Trinity**-app: wandtablets met Trinity worden een apparaat in Home Assistant, met entities en acties.

## Hoe het werkt

De tablet heeft al een ingelogde verbinding met Home Assistant (voor de bewegingssensoren die het scherm wekken). Over die verbinding meldt de tablet zich bij deze integratie. Voor de koppeling is dus geen extra server of poort op de tablet nodig. Alleen het live camerabeeld komt via een eigen stream van de tablet (RTSP, poort 8554, alleen op het eigen netwerk); het adres en wachtwoord daarvan krijgt de integratie vanzelf.

1. Je voegt de integratie één keer toe.
2. Een tablet met Trinity die bij deze Home Assistant is ingelogd, meldt zich vanzelf en verschijnt bij **Ontdekt**.
3. Je bevestigt met de zescijferige code die op de tablet staat. Die zie je in Trinity › Instellingen › Geavanceerd › Integratie, of in de melding van Trinity.

## Installeren

1. In HACS: **⋮ › Aangepaste repositories**, voeg `https://github.com/rsatoer/trinity-ha` toe met type **Integratie**.
2. Installeer **Trinity** en herstart Home Assistant.
3. **Instellingen › Apparaten en diensten › Integratie toevoegen › Trinity**.
4. Wacht tot de tablet bij **Ontdekt** verschijnt (dat kan tot twee minuten duren). Kies **Toevoegen** en vul de code van de tablet in.

## Wat je krijgt per tablet

| Entity | Soort | Wat |
| --- | --- | --- |
| Scherm | switch | Scherm aan (Trinity in beeld) of uit. Voor uit is apparaatbeheer op de tablet nodig. |
| Wekken bij beweging | switch (configuratie) | Uit: bewegingssensoren en de camera zetten het scherm niet meer aan. Camerabeweging blijft gemeld. |
| Camera | camera | Momentopname van de camera van de tablet; live beeld als op de tablet Geavanceerd › Camerastream aan staat. Alleen als de camera op de tablet aan staat. |
| Helderheid | number | De helderheid die de tablet nu gebruikt. Instellen zet de tablet op een vaste helderheid. |
| Pagina | select | De pagina die in beeld is; kies een andere om te wisselen. |
| Rol | sensor | Wandpaneel, achtergrond of smartspeaker |
| Lichtsterkte | sensor | De lichtsensor van de tablet (lux) |
| Batterij | sensor | Batterijpercentage |
| Laden | binary_sensor | Of de tablet laadt |
| Camerabeweging | binary_sensor | Beweging gezien door de camera van de tablet (boven de melddrempel). Alleen als de camera op de tablet aan staat. |
| Camera actief | binary_sensor (diagnose) | Of de camera nu aan staat: om te kijken (standaard alleen met het scherm uit of gedimd), voor de stream of voor een foto |
| Trinity-app | update | Een nieuwe versie van de app installeren op de tablet. Alleen met een GitHub-token bij de opties (zie Updates). |
| Stream bekeken | binary_sensor (diagnose) | Of iemand nu naar de stream kijkt (HA zelf, Frigate, VLC), met het aantal kijkers. Alleen als de stream aan staat. |
| Android-versie, Beveiligingspatch, Laatste herstart, App-versie | sensor (diagnose) | Systeeminformatie, bijvoorbeeld voor een melding na een herstart |

### Acties

- **Trinity: Toon pagina** (`trinity.toon_pagina`): toont een pagina, gekozen op naam of id. De rotatie gaat daarna vanaf die pagina verder.
- **Trinity: Herlaad pagina** (`trinity.herlaad_pagina`): laadt een pagina opnieuw. Laat je de pagina leeg, dan herlaadt de pagina die nu in beeld is.

```yaml
action: trinity.toon_pagina
data:
  tablet: <apparaat-id van de tablet>
  pagina: Dashboard
```

## Camera

Een momentopname vraagt de integratie aan de tablet; die zet de camera daarvoor zo nodig even aan. Een foto van minder dan vijf seconden oud gaat opnieuw mee, zodat een dashboard de camera niet steeds aanzet.

Live beeld komt van de stream van de tablet. Zet die aan in Trinity › Instellingen › Geavanceerd › Camerastream. Daar staat ook het adres met wachtwoord, en een voorbeeld voor Frigate. Zet poort 8554 nooit open naar internet.

## Updates van de app

De Trinity-app staat in een privé-repo. Om nieuwe versies op te halen heeft Home Assistant een GitHub-token nodig:

1. Maak op github.com een **fine-grained token** (Settings › Developer settings › Personal access tokens › Fine-grained tokens), alleen voor de repo `rsatoer/trinity-app`, met de rechten **Contents: Read-only**.
2. Ga in HA naar Instellingen › Apparaten en diensten › Trinity › ⚙ (opties) en plak het token.

Daarna kijkt HA elke zes uur of er een nieuwe uitgave is. Elke tablet krijgt een update-entity **Trinity-app**. Installeren haalt de APK één keer op in HA (map `trinity` in de configuratie) en stuurt de tablet een opdracht. De tablet downloadt de APK bij HA met zijn eigen inlog, controleert de SHA-256 en installeert hem. Het token gaat nooit naar een tablet.

De eerste keer vraagt Android op de tablet om bevestiging; daarna (Android 12 en nieuwer) meestal niet meer.

## Ontkoppelen

Verwijder de koppeling van de tablet in Home Assistant. De tablet krijgt dan een nieuwe code en verschijnt weer bij Ontdekt.

## Ontwikkelen

GitHub Actions controleert elke wijziging met:

- hassfest: de regels van Home Assistant
- de HACS-controle
- tests met een echte Home Assistant: koppelen, staat, opdrachten, camera en ontkoppelen

De tests draai je zelf met:

```bash
pip install -r requirements_test.txt
pytest
```
