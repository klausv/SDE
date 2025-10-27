# Erfaringer fra Battery Optimization Prosjekt
**Dato:** 22. desember 2024
**Prosjekt:** Batterioptimalisering Snødevegen 122

## Hovedutfordringer og Læringspunkter

### 1. Jupyter Lab og WSL vs Windows

#### Hva som IKKE fungerte:
- **WSL Jupyter → Windows Browser**: Tilkoblingsproblemer (ERR_CONNECTION_REFUSED)
  - localhost:8888 fra WSL nås ikke automatisk i Windows
  - Må bruke `--ip=0.0.0.0` flagg eller kjøre Jupyter direkte i Windows
  - IP-binding mellom WSL og Windows er inkonsistent

- **PDF-eksport uten LaTeX**:
  - `nbconvert --to pdf` krever full LaTeX installasjon (texlive-xetex)
  - Tar 500+ MB diskplass og lang installasjonstid
  - Genererte PDF-er ble uansett dårlige

- **Plotly-grafer i statisk HTML**:
  - Plotly krever JavaScript for visualisering
  - `nbconvert --to html --no-input` fjerner koden men også grafene!
  - Ingen god måte å få interaktive grafer i statisk eksport

#### Hva som fungerte:
- **Kjør Jupyter direkte i Windows**: Mest stabil løsning
- **VS Code med Jupyter extension**: Bedre integrasjon enn standalone Jupyter
- **HTML eksport fra Jupyter Lab**: Bevarer Plotly-grafer med JavaScript

### 2. Dataflyt og Hardkodede Verdier

#### Kritiske problemer:
1. **Hardkodede tall overalt**:
   - Samme verdi (f.eks. 138.55 kWp) definert 5+ steder
   - Ingen single source of truth før config.py ble laget
   - Endringer ett sted propagerte ikke til andre moduler

2. **Inkonsistente beregninger**:
   - Tariffberegning var fundamentalt feil (progressiv vs intervall)
   - Feilen eksisterte i minst 6 forskjellige filer
   - Måtte manuelt fikse hver enkelt fil

3. **Manglende datavalidering**:
   - Simuleringer brukte forskjellige verdier for samme parameter
   - Ingen sjekk på om input-data matcher systemkonfigurasjon
   - Resultater varierte vilkårlig mellom kjøringer

### 3. Kodeduplikasjon og Struktur

#### Omfattende duplikasjon:
- **27+ versjoner av analyse-scripts**:
  - `analyze_prices.py`, `final_correct_calculation.py`, `comprehensive_correct_analysis.py`
  - Alle gjorde essensielt samme ting med små variasjoner
  - Umulig å vite hvilken som var "riktig"

- **9 forskjellige notebook-versjoner**:
  - COMPLETE, DYNAMIC, FINAL, FIXED, RESTORED...
  - Hver "fix" skapte ny versjon i stedet for å oppdatere eksisterende
  - Resulterte i 1.8MB+ notebooks med masse duplisert kode

- **Manglende modularisering**:
  - Copy-paste av hele funksjoner mellom filer
  - Ingen gjenbruk av felles logikk
  - Hver fil reimplementerte samme beregninger

### 4. Modelleringsproblemer

#### Fundamentale svakheter:
1. **Oversimplifisert optimalisering**:
   - Bruker kun enkel differential evolution
   - Ingen tidssekvensielle constraints
   - Ignorerer battery degradation og temperatureffekter

2. **Manglende realisme**:
   - Perfekt prognose antagelse
   - Ingen usikkerhet i forbruk eller produksjon
   - Idealiserte arbitrasjemuligheter

3. **Feil økonomiske forutsetninger**:
   - NPV-beregning ignorerer vedlikeholdskostnader
   - Ingen sensitivitet for strømprisutvikling
   - Break-even analyse basert på statiske forutsetninger

### 5. Rapportering og Visualisering

#### Utfordringer:
- **Format-kaos**: HTML, PDF, PNG, Jupyter - ingen fungerte perfekt
- **Plotly vs Matplotlib**: Interaktivitet vs portabilitet
- **Manglende standardisering**: Hver rapport så forskjellig ut
- **Ingen automatisering**: Manuell prosess for hver rapport

#### Løsninger som fungerte delvis:
- Jupyter Lab for interaktiv utforskning
- HTML med embedded Plotly for deling (krever JavaScript)
- Matplotlib for statiske rapporter (men mindre pen)

## Konkrete Forbedringsforslag

### Umiddelbare tiltak:
1. **En sentral config.yaml** som ALLE moduler leser fra
2. **Fjern ALL hardkoding** - bruk kun config-verdier
3. **En notebook som master** - slett alle duplikater
4. **Standardiser dataflyt**: input → processing → output
5. **Implementer logging**: Spor hvilke verdier som brukes hvor

### Langsiktige forbedringer:
1. **Vurder PyPSA framework**:
   - Bedre dokumentert
   - Aktivt vedlikeholdt
   - Brukt i faktiske prosjekter
   - Håndterer kompleksitet bedre

2. **Implementer testing**:
   - Unit tests for hver beregningsmodul
   - Integration tests for hele pipeline
   - Valideringstests mot kjente resultater

3. **Profesjonaliser rapportering**:
   - LaTeX-mal for PDF-generering
   - Dash/Streamlit for interaktiv web-app
   - Automatisert rapport-pipeline

## Tekniske Lærdommer

### WSL-spesifikke problemer:
- Conda environments i Windows er ikke tilgjengelige i WSL
- Path-problemer mellom Windows (`C:\`) og WSL (`/mnt/c/`)
- Forskjellige Python-versjoner kan gi inkompatibilitet
- Jupyter kernel må matche Python-miljøet

### Jupyter-spesifikke problemer:
- Kernel dør ved store datasett (>100MB)
- Plotly-grafer kan ikke eksporteres statisk uten kaleido/orca
- `%matplotlib inline` vs `%matplotlib widget` forvirring
- Notebook-størrelse eksploderer med output (>5MB blir tregt)

## Veien Videre

### Prioritet 1: Stabilisering
- Fiks alle kjente bugs
- Fjern hardkoding
- Standardiser dataflyt

### Prioritet 2: Validering
- Sammenlign med kommersielle verktøy
- Verifiser mot faktiske prosjektdata
- Peer review av metode

### Prioritet 3: Profesjonalisering
- Migrere til PyPSA eller lignende
- Implementer CI/CD
- Lag ordentlig dokumentasjon

## Andre Viktige Erfaringer fra Dagens Økt

### Claude Code som Utviklingsverktøy

#### Styrker:
- **Rask prototyping**: Fikk laget fungerende modell på kort tid
- **Feilsøking**: Fant og rettet tariffberegningsfeilen effektivt
- **Refaktorering**: Klarte å rydde opp 20+ duplikatfiler

#### Svakheter:
- **Manglende kontekst**: Glemte ofte tidligere rettelser
- **Inkonsistent fiksing**: Rettet feil ett sted men ikke overalt
- **Overivrig fillaging**: Skapte nye versjoner i stedet for å oppdatere
- **Kontekstvindu-begrensninger**: Mistet oversikt over store endringer

### Norsk vs Engelsk i Kode

**Problem:** Blanding av norsk og engelsk skapte forvirring
- Variabelnavn: `nettleie` vs `grid_tariff`
- Kommentarer på norsk, kode på engelsk
- Rapporter på norsk med engelske tekniske termer

**Læring:** Hold ett språk konsistent per kontekst

### Git og Versjonskontroll

**Feil tilnærming:**
- Committet for sjelden under utvikling
- Ingen feature branches for eksperimentering
- Alt direkte på master

**Konsekvens:** Vanskelig å rulle tilbake feilaktige endringer

### Datatilgang og API-er

#### PVGIS API (fungerte bra):
- Gratis og pålitelig
- God dokumentasjon
- Realistiske produksjonsdata

#### ENTSO-E API (tungvint):
- Krever registrering og API-nøkkel
- Kompleks datastruktur
- Ofte timeout-problemer

### Økonomisk Modellering

**Største misforståelse:** Lnett tariffstruktur
- Trodde det var progressiv (som skatt)
- Faktisk intervallbasert (du betaler kun for ditt intervall)
- Førte til 10x feil i besparelsesberegninger

**Viktig læring:** ALLTID verifiser forretningslogikk med faktiske tariffer

### Python Miljø-helvete

**Problem:** Flere Python-installasjoner
- Windows Anaconda
- WSL Miniconda
- System Python
- VS Code Python

**Konsekvens:**
- `ModuleNotFoundError` konstant
- Forskjellige pakke-versjoner
- Jupyter kernel-problemer

**Løsning:** Standardiser på ETT miljø (helst conda)

### Simulering vs Optimalisering

**Forvirring:** Blandet sammen to konsepter
1. **Simulering**: Hva skjer med gitt batteristørrelse?
2. **Optimalisering**: Hvilken batteristørrelse er best?

**Problem:** Koden gjorde begge deler samtidig uten klar separasjon

### Visuell Kommunikasjon

**Fiasko:** SVG-diagram som ikke vises
- Forskjellige paths i Windows vs WSL
- Relative vs absolutte stier
- Ingen fallback hvis fil mangler

**Suksess:** Plotly interaktive grafer (når de virket)
- Zoom og pan funksjonalitet
- Hover-info med detaljer
- Men: Eksportproblemer

### Tallforståelse og Enheter

**Kritisk feil:** Inkonsistente enheter
- kW vs kWh forveksling
- MW vs kW i beregninger
- NOK/kWh vs NOK/MWh

**Mangel:** Ingen enhetsvalidering i koden

### Brukeropplevelse

**Frustrasjon:** "Det fungerer på min maskin"
- WSL-spesifikke paths
- Hardkodede filstier
- Miljøavhengigheter ikke dokumentert

**Læring:** Test på ren installasjon

## Konklusjon og Viktigste Lærdommer

### Top 5 Takeaways:

1. **Single Source of Truth**: ALL konfigurasjon i ÉN fil
2. **Test Alt**: Spesielt forretningslogikk og beregninger
3. **Commit Ofte**: Små, hyppige commits > store endringer
4. **Dokumenter Underveis**: Ikke vent til slutten
5. **KISS-prinsippet**: Start enkelt, øk kompleksitet gradvis

### For Neste Prosjekt:

**Setup:**
```bash
1. Lag requirements.txt FØRST
2. Sett opp git med .gitignore FØRST
3. Lag config.yaml FØRST
4. Skriv README.md FØRST
5. DERETTER begynn koding
```

**Arkitektur:**
```
project/
├── config/           # All konfigurasjon
├── data/            # Input/output data
├── src/             # Kildekode
│   ├── models/      # Kjerne-logikk
│   ├── utils/       # Hjelpefunksjoner
│   └── viz/         # Visualisering
├── tests/           # Tester
├── docs/            # Dokumentasjon
└── reports/         # Genererte rapporter
```

## Oppsummering

Prosjektet fungerer som **proof of concept** men har fundamentale strukturproblemer som gjør det uegnet for produksjon. Hovedproblemet er manglende separasjon mellom data, logikk og presentasjon, kombinert med omfattende kodeduplikasjon og hardkodede verdier.

**Anbefaling:** Start på nytt med PyPSA eller lignende framework fremfor å fortsette å lappe på eksisterende kode. Den tekniske gjelden er for stor til at refaktorering er verdt det.

**Viktigste erfaring:** Planlegging og struktur fra start sparer enormt med tid. "Measure twice, cut once" gjelder definitivt for programmering.

---
*Erfaring notert av Klaus Vogstad og Claude, 22.12.2024*