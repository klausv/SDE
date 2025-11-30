# 🔋 Batterioptimalisering - Prosjektoversikt

## 📌 Hva er Prosjektet?

Et omfattende system for å analysere den økonomiske lønnsomheten av batterilagring for et **150 kWp solcelleanlegg i Stavanger**. Prosjektet evaluerer fire hovedstrategier:

1. **Curtailment-unngåelse** - Lagre overskuddsproduksjon når produksjon > 77 kW nettgrense
2. **Energiarbitrasje** - Kjøp billig (natt), selg dyrt (peak)
3. **Effekttariff-reduksjon** - Minimere månedlig effekttopp-kostnader
4. **Egenforbruk** - Maksimere bruk av egen solproduksjon

---

## 🏗️ Systemarkitektur (Nylig Refaktorert)

Prosjektet har gjennomgått en omfattende 4-fase refaktorering til en ren lagdelt arkitektur:

```
┌─────────────────────────────────────────┐
│    Application Layer (Orchestration)    │  ← Simulation orchestrators, CLI
│  - RollingHorizonOrchestrator           │
│  - MonthlyOrchestrator                  │
│  - YearlyOrchestrator                   │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│      Domain Layer (Optimization)        │  ← Battery optimization algorithms
│  - OptimizerRegistry (traceability)     │
│  - OptimizerFactory (creation)          │
│  - BaseOptimizer interface              │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│   Infrastructure Layer (Data Services)  │  ← Shared data infrastructure
│  - PriceLoader (ENTSO-E API)            │
│  - SolarProductionLoader (PVGIS)        │
│  - TariffLoader (YAML configs)          │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│    Persistence Layer (Storage)          │  ← Result storage & metadata
│  - ResultStorage (Pickle/JSON/Parquet)  │
│  - MetadataBuilder (traceability)       │
│  - CLI reporting tool                   │
└─────────────────────────────────────────┘
```

---

## 📂 Prosjektstruktur (Renset og Organisert)

### Root Directory (Kun 2 filer)
```
main.py          # Hovedinngangspunkt
config.py        # Kjernekonfigurasjon
```

### Moduler (src/)
```
src/
├── config/                    # Konfigurasjonssystem
│   ├── simulation_config.py   # Dataclass-basert config
│   └── legacy_config_adapter.py
│
├── infrastructure/            # Delt datainfrastruktur
│   ├── pricing/              # Strømpriser (ENTSO-E)
│   │   ├── price_loader.py
│   │   └── entsoe_client.py
│   ├── weather/              # Solproduksjon (PVGIS)
│   │   └── solar_loader.py
│   └── tariffs/              # Nettleie (YAML)
│       └── loader.py
│
├── optimization/             # Optimaliseringsalgoritmer
│   ├── optimizer_registry.py # Metode-traceability
│   ├── optimizer_factory.py  # Factory pattern
│   ├── base_optimizer.py     # Abstrakt interface
│   ├── rolling_horizon_adapter.py  # 24t rullende horisont
│   ├── monthly_lp_adapter.py       # Månedlig LP
│   └── weekly_optimizer.py         # Ukentlig (yearly mode)
│
├── simulation/               # Orkestreringslaag
│   ├── simulation_results.py
│   ├── rolling_horizon_orchestrator.py
│   ├── monthly_orchestrator.py
│   └── yearly_orchestrator.py
│
├── persistence/              # Resultatlagring
│   ├── result_storage.py     # Multi-format storage
│   └── metadata_builder.py   # Metadata tracking
│
└── operational/              # Batteristyring
    └── state_manager.py
```

### Scripts og Eksempler
```
examples/                      # Eksempelscripts (3)
├── example_infrastructure_usage.py
├── example_optimizer_registry.py
└── example_persistence_usage.py

scripts/
├── analysis/                 # Analysescripts (5)
│   ├── calculate_breakeven_battery.py
│   ├── compare_15min_vs_60min.py
│   └── ...
├── data/                     # Data-henting (2)
│   ├── fetch_historical_prices_no1.py
│   └── get_hourly_mai_des.py
├── visualization/            # Plotting (10)
│   ├── create_detailed_plots.py
│   └── ...
└── report_cli.py             # CLI rapporteringsverktøy

tests/                        # Validering (7)
├── validate_module_structure.py
├── validate_economic_refactor.py
└── ...

archive/                      # Historiske scripts
├── simulations/              # Gamle simuleringer (12)
└── quick_tools/              # Temp utviklingsverktøy (4)
```

---

## 🔧 Tekniske Spesifikasjoner

### Solcelleanlegg
- **Installert effekt**: 150 kWp
- **Orientering**: Sør
- **Helningsvinkel**: 25°
- **Vekselretter**: 110 kW (oversizing ratio 1.36)
- **Nettgrense**: 77 kW (70% av vekselretter)
- **Lokasjon**: Stavanger (58.97°N, 5.73°E)

### Økonomiske Forutsetninger
- **Diskonteringsrente**: 5%
- **Batteriets levetid**: 15 år
- **EUR/NOK**: 11.5
- **Batterivirkningsgrad**: 90%

### Nettleie (Lnett Kommersiell)
- **Peak (Man-Fre 06-22)**: 0.296 kr/kWh
- **Off-peak (Natt/helg)**: 0.176 kr/kWh
- **Effekttariff**: Progressive trinn basert på månedlig toppeffekt

---

## 🚀 Bruk av Systemet

### 1. Installasjon
```bash
cd battery_optimization
conda env create -f environment.yml
conda activate battery_opt
```

### 2. Konfigurer API-nøkkel
```bash
echo "ENTSOE_API_KEY=your_key_here" > .env
```

### 3. Kjør Simulering

#### Via YAML (Anbefalt)
```bash
python main.py run --config configs/rolling_horizon.yaml
```

#### Via CLI
```bash
# Rullende horisont (sanntid)
python main.py rolling --battery-kwh 80 --battery-kw 60

# Månedlig analyse
python main.py monthly --months 1,2,3 --resolution PT60M

# Årlig investeringsanalyse
python main.py yearly --weeks 52 --resolution PT60M
```

### 4. Generer Rapporter (Uten Re-simulering!)

```bash
# List lagrede resultater
python scripts/report_cli.py list

# Vis detaljer
python scripts/report_cli.py show <result_id>

# Generer rapport
python scripts/report_cli.py report <result_id> -o report.md

# Generer plott
python scripts/report_cli.py plots <result_id> -o plots/

# Sammenlign resultater
python scripts/report_cli.py compare <id1> <id2>
```

---

## 📊 Optimaliseringsmetoder

### 1. **Baseline** (Ingen batteri) - **NY i v2.0**
- **Horisont**: 1-8760 timer
- **Solver**: Ingen (direkte beregning)
- **Bruksområde**: Økonomisk baseline for ROI-sammenligning
- **Beregnetid**: ~0.001s (**instant!**)
- **Viktighet**: Kritisk referansepunkt for batteriinvestering

### 2. Rolling Horizon MPC (Sanntid)
- **Horisont**: 24-168 timer
- **Solver**: HiGHS (LP)
- **Bruksområde**: Sanntids batteristyring
- **Beregnetid**: ~1-2 minutter/simulering

### 3. Monthly LP (Månedlig analyse)
- **Horisont**: 720 timer (1 måned)
- **Solver**: HiGHS (LP)
- **Bruksområde**: Månedlig ytelsesanalyse
- **Beregnetid**: ~5-10 minutter

### 4. Yearly (Investeringsanalyse)
- **Horisont**: 52 uker
- **Solver**: HiGHS (LP)
- **Bruksområde**: Økonomisk analyse over hele året
- **Beregnetid**: ~10-20 minutter

---

## 📈 Viktige Resultater fra Analyser

### Break-even Analyse
- **Optimal batteristørrelse**: ~80-100 kWh @ 40-60 kW
- **Break-even kostnad**: ~2500-3500 NOK/kWh
- **Nåværende markedspris**: ~5000 NOK/kWh
- **Konklusjon**: Batterier må bli 40-50% billigere for lønnsomhet

### Tidsoppløsning (15 min vs 60 min)
- **PT15M**: Mer nøyaktig, fanger opp kortvarige topper
- **PT60M**: Raskere beregning, tilstrekkelig for årlige analyser
- **Anbefaling**: PT15M for sanntid, PT60M for langsiktige analyser

---

## 🎯 Nylige Forbedringer (Refaktorering v2.0)

### Phase 1: Infrastructure Modules
✅ Ekstrahert pricing infrastructure (PriceLoader, ENTSOEClient)
✅ Ekstrahert weather infrastructure (SolarProductionLoader)
✅ Ekstrahert tariff infrastructure (TariffLoader)
✅ Dataclass-basert arkitektur med type-sikkerhet

### Phase 2: Persistence & Reporting
✅ Implementert ResultStorage med 3 formater (Pickle/JSON/Parquet)
✅ Lagt til MetadataBuilder for omfattende tracking
✅ Utvidet SimulationResults med persistence-funksjoner
✅ Opprettet CLI reporting tool med 8 kommandoer

### Phase 3: Optimizer Registry
✅ Implementert OptimizerRegistry for metode-traceability
✅ Lagt til rik metadata (solver type, capabilities, references)
✅ Opprettet clean public API i src/__init__.py
✅ Etablert lagdelt arkitektur

### Phase 4: Project Cleanup
✅ Organisert 43 spredte Python-filer
✅ Renset root directory (45 → 2 filer)
✅ Opprettet logisk mappestruktur
✅ Flyttet alle scripts til riktige lokasjoner

---

## 📚 Dokumentasjon

- **ARCHITECTURE.md** - Komplett systemarkitektur (~450 linjer)
- **QUICKSTART.md** - Rask oppstartsguide (~280 linjer)
- **CLEANUP_SUMMARY.md** - Detaljer om reorganisering
- **README.md** - Grunnleggende bruksveiledning

---

## 🧪 Testing og Validering

### Validering
```bash
# Kjør full modulstruktur-validering
python tests/validate_module_structure.py

# Status: 7/7 tester bestått ✅
```

### Test Coverage
- ✓ Public API Imports
- ✓ Module Boundaries
- ✓ Optimizer Registry
- ✓ Configuration System
- ✓ Persistence System
- ✓ Version Information
- ✓ Minimal Workflow

---

## 🔮 Fremtidig Utvikling

### Planlagte Forbedringer
1. **Sanntidsintegrasjon** - Koble til faktiske batteristyringssystemer
2. **Prognoseinintegrasjon** - Vær- og pris-prognose APIer
3. **Multi-objektiv optimalisering** - Pareto-fronter for avveininger
4. **Usikkerhetskvantifisering** - Stokastiske optimalisering-varianter
5. **Webgrensesnitt** - Interaktivt dashboard for konfigurasjon og analyse

---

## 🛠️ Teknisk Stack

### Kjerneteknologier
- **Python 3.10+**
- **NumPy/Pandas** - Databehandling
- **SciPy** - Numeriske beregninger
- **PuLP + HiGHS** - Lineær programmering
- **Matplotlib/Plotly** - Visualisering
- **PyYAML** - Konfigurasjon
- **Dataclasses** - Type-sikker konfigurasjon

### Datakilder
- **ENTSO-E Transparency Platform** - Strømpriser (gratis API)
- **PVGIS** - Solproduksjonsdata (gratis API)
- **Lnett** - Nettleie-tariffstruktur

---

## 📞 Support

Ved problemer eller spørsmål:
1. Sjekk `docs/ARCHITECTURE.md` for design-detaljer
2. Se eksempelscripts for bruksmønstre
3. Inspiser enhetstester for edge cases
4. Undersøk kildekode for implementasjonsdetaljer

---

**Versjon**: 2.0.0  
**Forfatter**: Klaus  
**Sist oppdatert**: 2025-11-29
