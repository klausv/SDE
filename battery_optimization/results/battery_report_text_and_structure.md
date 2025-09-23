# Tekst og avsnittsstruktur (fra Markdown)

## SAMMENDRAG
## 1. Beskrivelse av anlegg
## 2. Produksjon og forbruk
### 2.1 Produksjonsprofil
### 2.2 Kraftpris og kostnad
## 3. Strømpris- og tariffanalyse
## 4. Batterioptimalisering
### 4.1 Optimal batteristørrelse
### 4.2 Økonomisk analyse
### 4.3 Verdidrivere
## 5. Sensitivitetsanalyse
## 6. Sammenligning med markedspriser
## KONKLUSJON OG ANBEFALINGER
### Hovedfunn
**1. Batterikostnad er kritisk parameter**
- Break-even ved 2500 NOK/kWh (50% under marked)
- Optimal størrelse kun 10 kWh ved dagens kostnadsstruktur
- Større batterier gir negativ marginalnytte

**2. Effekttariff dominerer verdiskapning**
- 45% av total verdi fra månedlig peak-reduksjon
- Arbitrasje bidrar 35% gjennom prisvariasjoner
- Curtailment-reduksjon kun 20% av verdien

**3. Begrenset curtailment påvirker lønnsomhet**
- 77 kW nettgrense vs 100 kW inverter gir moderat curtailment
- Hovedverdi kommer fra nettleieoptimalisering, ikke produksjonsøkning

### Anbefaling
**VENT MED INVESTERING** til batterikostnader faller under 3000 NOK/kWh eller til nye støtteordninger introduseres. Vurder alternative løsninger som lastflytting og forbruksoptimalisering for å redusere effekttariffer.

### Neste steg
1. **Overvåk batteriprisutvikling** - Følg markedstrender kvartalsvis
2. **Undersøk støtteordninger** - Enova og lokale incentiver kan endre økonomien
3. **Optimaliser forbruksprofil** - Reduser månedlige effekttopper gjennom laststyring
4. **Revurder om 12-18 måneder** - Batterikostnader faller typisk 10-15% årlig


---

# Figur- og tabellbeskrivelser (uten tall)

## Figurer

- [Celle 6] plotly-figur. Tittel: Månedlig produksjon, forbruk og curtailment. Akser: X=Måned, Y=Energi (MWh). Antall spor: 3; typer: scatter, bar.
- [Celle 6] plotly-figur. Tittel: Gjennomsnittlig døgnprofil - DC vs AC. Akser: X=Time på døgnet, Y=Effekt (kW). Antall spor: 3; typer: scatter.
- [Celle 6] plotly-figur. Tittel: Varighetskurve - DC vs AC solproduksjon. Akser: X=Timer i året, Y=Effekt (kW). Antall spor: 2; typer: scatter.
- [Celle 8] plotly-figur. Tittel: Effekttariff struktur (Lnett) - Intervallbasert. Akser: X=Effekt (kW), Y=NOK/måned. Antall spor: 2; typer: scatter.
- [Celle 8] matplotlib-figur. Tittel: (ingen tittel funnet). Akser: X=(ukjent x-akse), Y=(ukjent y-akse).
- [Celle 10] plotly-figur. Tittel: Systemanalyse Mai 2024. Akser: X=(ukjent x-akse), Y=NOK/kWh. Antall spor: 4; typer: scatter.
- [Celle 10] matplotlib-figur. Tittel: (ingen tittel funnet). Akser: X=(ukjent x-akse), Y=(ukjent y-akse).
- [Celle 10] plotly-figur. Tittel: Representativ dag - 15. juni 2024. Akser: X=(ukjent x-akse), Y=kW. Antall spor: 6; typer: scatter, bar.
- [Celle 10] matplotlib-figur. Tittel: (ingen tittel funnet). Akser: X=(ukjent x-akse), Y=(ukjent y-akse).
- [Celle 12] plotly-figur. Tittel: NPV vs Batteristørrelse. Akser: X=Batteristørrelse (kWh), Y=NPV (1000 NOK). Antall spor: 3; typer: scatter.
- [Celle 12] matplotlib-figur. Tittel: (ingen tittel funnet). Akser: X=(ukjent x-akse), Y=(ukjent y-akse).
- [Celle 14] plotly-figur. Tittel: Kontantstrøm over batteriets levetid. Akser: X=År, Y=Årlig kontantstrøm (NOK). Antall spor: 2; typer: scatter, bar.
- [Celle 14] matplotlib-figur. Tittel: (ingen tittel funnet). Akser: X=(ukjent x-akse), Y=(ukjent y-akse).
- [Celle 16] plotly-figur. Tittel: Fordeling av verdidrivere. Akser: X=(ukjent x-akse), Y=(ukjent y-akse). Antall spor: 1; typer: pie.
- [Celle 16] matplotlib-figur. Tittel: (ingen tittel funnet). Akser: X=(ukjent x-akse), Y=(ukjent y-akse).
- [Celle 18] plotly-figur. Tittel: NPV Sensitivitet - Batteristørrelse vs Kostnad. Akser: X=Batteristørrelse (kWh), Y=Batterikostnad (NOK/kWh). Antall spor: 1; typer: heatmap.
- [Celle 18] matplotlib-figur. Tittel: (ingen tittel funnet). Akser: X=(ukjent x-akse), Y=(ukjent y-akse).
- [Celle 20] plotly-figur. Tittel: NPV ved ulike batterikostnader. Akser: X=(ukjent x-akse), Y=NPV (NOK). Antall spor: 1; typer: bar.
- [Celle 20] matplotlib-figur. Tittel: (ingen tittel funnet). Akser: X=(ukjent x-akse), Y=(ukjent y-akse).
