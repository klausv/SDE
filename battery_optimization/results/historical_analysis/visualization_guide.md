# Forbedret Visualisering: NO1 Kraftpriser med Innsikter

## Oversikt

Den forbedrede visualiseringen (`NO1_enhanced_analysis_with_insights.png`) inneholder 5 detaljerte paneler med notater, forklaringer og analyser fra `volatility_analysis.md`.

---

## Panel 1: Historisk Prisutvikling med Nøkkelhendelser

### Innhold:
- Gjennomsnittlig årlig pris (EUR/MWh) med standardavvik som usikerhetsområde
- **Tidsperioder fargekodet**:
  - 🟢 Grønn: 2014-2019 (Stabil periode)
  - 🟠 Oransje: 2020-2021 (Overgangsperiode)
  - 🔴 Rød: 2021-2024 (Nytt normalt)

### Annotasjoner:
1. **COVID-19 (2020)**: Etterspørselssjokk, volatilitet 89%
2. **NordLink (Mai 2021)**: 1400 MW kabel til Tyskland
3. **North Sea Link (Okt 2021)**: 1400 MW kabel til UK
4. **Single Price-Single Position (Nov 2021)**: Nordic Balancing Model reform
5. **Energikrise (2022)**: Topp på 192.5 EUR/MWh

### Innsikt:
Visuell demonstrasjon av de tre periodene og hvordan markedet endret seg strukturelt fra 2020.

---

## Panel 2: Volatilitetsutvikling - Strukturelt Skifte

### Innhold:
- Årlig volatilitet (standardavvik/gjennomsnitt) som stolpediagram
- **Fargekoding**:
  - 🟢 Grønn: Pre-2020 (normal volatilitet)
  - 🔴 Rød: 2020 (kritisk vendepunkt)
  - 🟠 Oransje: 2021-2024 (nytt høyt nivå)

### Notater:
- **Referanselinjer**:
  - 2019 nivå (21%) - grønn stiplet linje
  - 2020 topp (89%) - rød stiplet linje
- **Forklaringer**:
  - "STRUKTURELT SKIFTE: Volatilitet 4x høyere!"
  - Nordic Balancing Model reformer (Single Price-Single Position, 15-min settlement)
  - "Permanent høyt nivå (volatilitet importeres via kabler)"

### Innsikt:
Tydelig visualisering av at 2020 var et vendepunkt, ikke en midlertidig anomali.

---

## Panel 3: Negative Priser - Importert Uregulerbar Kraft

### Innhold:
- Antall timer med negative priser per år
- Fremhever 2023 toppen (381 timer, 4.3% av året)

### Annotasjoner:
- **"Første negative priser noensinne i NO1"** (2020)
- **"381 timer (4.3%): Importert volatilitet fra tysk/britisk vind+sol"** (2023)
- Vertikal linje markerer når kabler åpnet (2021)

### Innsikt:
Negative priser er et klassisk symptom på markeder med høy andel uregulerbar kraft. Norge hadde ALDRI negative priser før 2020, men nå er det vanlig - bevis på at vi importerer volatiliteten.

---

## Panel 4: Prisutvikling med Ekstremverdier

### Innhold:
- Min-max spenn (skyggelagt område)
- Gjennomsnittspris (blå linje)
- P10 og P90 persentiler (grå stiplete linjer)

### Annotasjoner:
- **Max pris**: 800 EUR/MWh (2022 energikrise)
- **Min pris**: -62 EUR/MWh (2023 overproduksjon)
- Svart horisontal linje ved 0 for å markere overgangen til negative priser

### Innsikt:
Prisvariasjonen har økt dramatisk. Før 2020: 1-115 EUR/MWh. Etter 2021: -62 til 800 EUR/MWh. Dette er en 10x økning i prisvariasjonsbredde.

---

## Panel 5: Tre Hovedårsaker (Infografikk)

### Innhold:
Tekstbokser med detaljert forklaring av de tre hovedårsakene til volatilitetsøkning:

#### 1️⃣ Markedsreformer (2020-2021) - Blå boks
- Single Price-Single Position (Nov 2021)
  - Slår sammen produksjon/forbruk ubalanser
  - Forenkler prismekanisme → mer volatilitet
- 15-minutters oppgjør (fra 2023)
  - 4x flere handelspunkter per time
- mFRR Capacity Market erstatter RKOM
  - Kapasitet flyttes til spotmarkedet

**Effekt**: Volatilitet fra 21% → 89% i 2020!

#### 2️⃣ Utenlandskabler (2021) - Gul boks
- NordLink → Tyskland (1400 MW)
  - Tysk vind+sol: 117 → 157 GW (2020-2024)
- North Sea Link → UK (1400 MW)
  - Britisk offshore vind: Massiv vekst

**Effekt**: Norge "importerer" volatilitet fra uregulerbar tysk/britisk produksjon

#### 3️⃣ Importert Volatilitet - Rød boks
**Nøkkelinnsikt**: Norge har IKKE installert mye uregulerbar kraft, men IMPORTERER volatiliteten!

- Norsk vannkraft: Stabil og regulerbar
- Tysk vind/sol: Uregulerbar og volatil
- Kablene: Kobler oss til deres volatilitet

**Bevis**:
- Negative priser: 0 → 381 timer (2023)
- Volatilitet: 21% → 79% (permanent)

---

## Bunntekst (Footer)

### Konklusjon:
Volatilitetsøkningen fra 2020 skyldes kombinasjonen av:
1. Markedsreformer (Nordic Balancing Model)
2. Nye utenlandskabler (2800 MW til DE/UK)
3. Import av volatilitet fra uregulerbar tysk/britisk produksjon

Dette representerer et **PERMANENT** skifte i markedsdynamikken.

### Implikasjon for Batterier:
Høy volatilitet = bedre business case for energilagring (større arbitrasjemuligheter)

---

## Tekniske Detaljer

### Filstørrelse og Oppløsning:
- Filnavn: `NO1_enhanced_analysis_with_insights.png`
- Størrelse: ~1.6 MB
- Oppløsning: 300 DPI (trykkekvalitet)
- Dimensjoner: 20" x 16" (6000 x 4800 piksler)

### Fargepalett:
- **Normal periode**: #2E86AB (blå)
- **Overgang**: #F18F01 (oransje)
- **Nytt normalt**: #C73E1D (rød)
- **Volatilitet**: #A23B72 (lilla)

### Layout:
- 3 rader × 2 kolonner
- Panel 1: Full bredde, topprad
- Panel 2-3: Midtre rad (delt)
- Panel 4-5: Bunnrad (delt)

---

## Hvordan Bruke Visualiseringen

### For Presentasjoner:
1. Bruk full visualisering for omfattende gjennomgang
2. Individuelt panel 2 (volatilitet) for å vise strukturelt skifte
3. Panel 5 (tre årsaker) fungerer som standalone infografikk

### For Rapporter:
- Høy oppløsning (300 DPI) egner seg for trykt materiale
- Panel 1 gir god oversikt for executive summary
- Panel 4 viser dramatisk prisutvikling for business case-argumentasjon

### For Batteriprosjektet:
- Panel 2 (volatilitet): Dokumenterer at høy volatilitet er det "nye normalet"
- Panel 4 (prisvariasjoner): Viser arbitrasjemuligheter for batterier
- Footer: Direkte implikasjon for business case

---

## Sammenligning med Original Visualisering

### Original (`NO1_historical_prices_analysis.png`):
- 4 grunnleggende paneler
- Fokus på data
- Minimal kontekst

### Forbedret (`NO1_enhanced_analysis_with_insights.png`):
- 5 paneler med dyptgående forklaringer
- Annotasjoner for nøkkelhendelser
- Tidsperioder fargekodet
- Infografikk med tre hovedårsaker
- Konklusjon og implikasjoner inkludert

**Anbefaling**: Bruk forbedret versjon for alle formål unntatt når ekstrem enkelhet er nødvendig.
