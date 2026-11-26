# Trinity voor Home Assistant

De Home Assistant-integratie voor de **Trinity**-app: wandtablets met Trinity worden een apparaat in Home Assistant, met entities en acties.

## Hoe het werkt

De tablet heeft al een ingelogde verbinding met Home Assistant (voor de bewegingssensoren die het scherm wekken). Over die verbinding meldt de tablet zich bij deze integratie. Er is dus geen extra server of poort op de tablet nodig.

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
| Helderheid | number | De helderheid die de tablet nu gebruikt. Instellen zet de tablet op een vaste helderheid. |
| Pagina | select | De pagina die in beeld is; kies een andere om te wisselen. |
| Rol | sensor | Wandpaneel, achtergrond of smartspeaker |
| Lichtsterkte | sensor | De lichtsensor van de tablet (lux) |
| Batterij | sensor | Batterijpercentage |
| Laden | binary_sensor | Of de tablet laadt |
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

## Ontkoppelen

Verwijder de koppeling van de tablet in Home Assistant. De tablet krijgt dan een nieuwe code en verschijnt weer bij Ontdekt.

## Ontwikkelen

GitHub Actions controleert elke wijziging met:

- hassfest: de regels van Home Assistant
- de HACS-controle
- tests met een echte Home Assistant: koppelen, staat, opdrachten en ontkoppelen

De tests draai je zelf met:

```bash
pip install -r requirements_test.txt
pytest
```
