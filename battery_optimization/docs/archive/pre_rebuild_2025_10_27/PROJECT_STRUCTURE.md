# Prosjektstruktur - Battery Optimization

## 📁 Katalogstruktur

```
battery_optimization/
├── main.py                    # Hovedprogram for batterioptimalisering
├── src/                       # Kildekode (kjernefunksjonalitet)
│   ├── config.py             # Systemkonfigurasjon
│   ├── data_fetchers/        # Datahenting (ENTSO-E, PVGIS)
│   ├── optimization/         # Optimeringsmoduler
│   └── analysis/             # Analyse og visualisering
├── scripts/                   # Hjelpescripts
│   ├── analysis/             # Analysescripts
│   │   ├── analyze_pvsol_correct.py
│   │   ├── analyze_full_90mwh.py
│   │   └── ...
│   └── data_fetch/           # Datahentingsscripts
│       └── get_pvgis_data.py
├── tests/                     # Testfiler
│   ├── test_analysis.py
│   ├── test_realistic.py
│   └── test_milp_constraints.py
├── results/                   # Genererte resultater
│   ├── reports/              # HTML-rapporter
│   └── *.png                 # Grafer og figurer
├── data/                      # Bufrede data
│   └── cached_*.pkl          # PVGIS/ENTSO-E cache
└── environment.yml           # Conda miljøkonfigurasjon
```

## 🔑 Viktige filer

### Hovedprogram
- `main.py` - Kjør komplett batterianalyse med faktiske data

### Korrekte parametere (30° takvinkel, 90 MWh forbruk)
- `scripts/analysis/analyze_pvsol_correct.py` - Forenklet analyse med korrekte tall
- `scripts/analysis/analyze_full_90mwh.py` - Full time-for-time simulering

### Systemkonfigurasjon
- **PV-kapasitet**: 138.55 kWp
- **Årlig PV-produksjon**: 133 MWh
- **Årlig forbruk**: 90 MWh
- **Takvinkel**: 30°
- **Invertergrense**: 100 kW
- **Nettgrense**: 70 kW (70% av inverter)

## 🚀 Bruk

### Kjør hovedanalyse
```bash
python main.py
```

### Kjør spesifikke analyser
```bash
python scripts/analysis/analyze_pvsol_correct.py  # Forenklet med korrekte tall
python scripts/analysis/analyze_full_90mwh.py      # Full simulering 90 MWh
```

### Kjør tester
```bash
python tests/test_analysis.py
python tests/test_milp_constraints.py
```

## 📊 Resultater

Alle genererte resultater lagres i `results/`:
- PNG-filer: Grafer og figurer
- HTML-rapporter: I `results/reports/`

## 🔧 Utvikling

Ved endringer i systemparametere, oppdater:
1. `src/config.py` for permanente endringer
2. Eller overstyr i analysescripts for midlertidige tester

## 📝 Notater

- Alle scripts i `scripts/analysis/` har oppdaterte imports
- Test-filer i `tests/` bruker relativ import til `src/`
- Bufrede data i `data/` reduserer API-kall