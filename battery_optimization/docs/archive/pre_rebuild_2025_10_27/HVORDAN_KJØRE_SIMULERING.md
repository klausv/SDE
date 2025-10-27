# HVORDAN KJØRE BATTERISIMULERING

## 🚀 RASK START - 3 MÅTER

### 1. ENKEL ANALYSE (Anbefalt start)
```bash
python run_clean_analysis.py
```
Dette kjører standard analyse med:
- 100 kWh batteri
- 50 kW effekt
- 5000 NOK/kWh kostnad

### 2. JUSTERE PARAMETERE
Rediger `run_clean_analysis.py` linje 27-32:
```python
# ENDRE DISSE VERDIENE:
PV_CAPACITY_KWP = 138.55      # Solcellestørrelse
ANNUAL_CONSUMPTION_KWH = 90000 # Årsforbruk
GRID_LIMIT_KW = 77            # Nettbegrensning
BATTERY_CAPACITY_KWH = 100    # Batteristørrelse (kWh)
BATTERY_POWER_KW = 50         # Batterieffekt (kW)
```

### 3. ENDRE BATTERIKOSTNAD
Rediger linje 84-85:
```python
BATTERY_COST_CURRENT = 5000  # NOK/kWh dagens pris
BATTERY_COST_TARGET = 3000   # NOK/kWh målpris
```

## 📊 HVA PROGRAMMET GJØR

### Steg 1: DATAGENERING
- Genererer 8760 timer (hele året) med:
  - Solproduksjon basert på Stavanger
  - Forbruksprofil (kommersielt anlegg)
  - Spotpriser for strøm

### Steg 2: VERDIDRIVER-BEREGNING
Beregner 4 inntektskilder:
1. **Avkortning**: Unngått tapt produksjon når sol > 77 kW
2. **Arbitrasje**: Kjøp billig strøm om natten, selg dyrt om dagen
3. **Effekttariff**: Redusert nettleie ved lavere toppeffekt
4. **Selvforsyning**: Mindre kjøp fra nettet

### Steg 3: ØKONOMISK ANALYSE
- NPV (netto nåverdi)
- IRR (internrente)
- Tilbakebetalingstid
- Break-even batterikostnad

## 🔧 EKSEMPLER PÅ KJØRING

### Eksempel 1: Test mindre batteri (50 kWh)
```python
# Rediger linje 31 i run_clean_analysis.py:
BATTERY_CAPACITY_KWH = 50
BATTERY_POWER_KW = 25

# Kjør:
python run_clean_analysis.py
```

### Eksempel 2: Test billigere batterikostnad
```python
# Rediger linje 84:
BATTERY_COST_CURRENT = 3000  # Fremtidig målpris

# Kjør:
python run_clean_analysis.py
```

### Eksempel 3: Test større solcelleanlegg
```python
# Rediger linje 28:
PV_CAPACITY_KWP = 200  # Større anlegg

# Kjør:
python run_clean_analysis.py
```

## 📈 TOLKE RESULTATENE

### Hvis NPV > 0:
✅ **LØNNSOMT** - Investeringen gir positiv avkastning

### Hvis NPV < 0:
❌ **ULØNNSOMT** - Tap på investeringen

### Break-even kostnad:
Dette er maksimal batteripris hvor NPV = 0
- Hvis markedspris > break-even → VENT
- Hvis markedspris < break-even → INVESTER

## 💡 VIKTIGE TALL FRA SISTE KJØRING

- **Avkortning**: 14,156 kWh/år (7.6% av produksjon)
- **Total årlig verdi**: 72,375 NOK
- **Break-even**: 6,533 NOK/kWh
- **NPV ved 5000 NOK/kWh**: 153,282 NOK (✅ lønnsomt)
- **NPV ved 3000 NOK/kWh**: 353,282 NOK (✅ meget lønnsomt)

## 🏃 KJØR NÅ!

1. Åpne terminal
2. Naviger til: `cd /mnt/c/Users/klaus/klauspython/offgrid2/battery_optimization`
3. Kjør: `python run_clean_analysis.py`
4. Se resultatene!

## 📁 FILSTRUKTUR

```
battery_optimization/
├── run_clean_analysis.py      # HOVEDPROGRAM - START HER!
├── analysis/
│   ├── data_generators.py     # Genererer data
│   ├── value_drivers.py       # Beregner verdidrivere
│   └── economic_analysis.py   # Økonomisk analyse
└── HVORDAN_KJØRE_SIMULERING.md  # Denne filen
```