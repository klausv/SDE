# FORSKJELLER MELLOM ANALYSE-SCRIPTENE

## 📊 TRE FORSKJELLIGE ANALYSER

### 1. `run_clean_analysis.py` - STANDARD ANALYSE
**Formål**: Kjør komplett analyse med faste verdier
```python
# Fast oppsett:
BATTERY_CAPACITY_KWH = 50  # Endret til 50 kWh
BATTERY_POWER_KW = 25      # Endret til 25 kW
BATTERY_COST_CURRENT = 5000
BATTERY_COST_TARGET = 3000
```

**Funksjoner**:
- ✅ Genererer simulerte data (ikke reelle API-data)
- ✅ Beregner alle 4 verdidrivere
- ✅ Kjører sensitivitetsanalyse
- ✅ Finner break-even kostnad
- ✅ Viser detaljert oppsummering

**Bruk dette når**: Du vil ha en rask, komplett analyse med standard verdier

---

### 2. `run_custom_analysis.py` - JUSTERBAR ANALYSE
**Formål**: Enkelt å endre parametere øverst i filen
```python
# ALT kan justeres øverst:
PV_CAPACITY_KWP = 138.55        # Endre meg!
INVERTER_LIMIT_KW = 110          # Endre meg!
BATTERY_CAPACITY_KWH = 50        # Endre meg!
BATTERY_POWER_KW = 25            # Endre meg!
BATTERY_COST_NOK_PER_KWH = 5000  # Endre meg!
```

**Funksjoner**:
- ✅ Alle parametere samlet øverst
- ✅ Enkel å justere og teste scenarioer
- ✅ Genererer simulerte data
- ✅ Viser NPV, IRR, break-even
- ❌ Ingen sensitivitetsanalyse (forenklet)

**Bruk dette når**: Du vil teste forskjellige batteristørrelser eller kostnader

---

### 3. `run_real_analysis.py` - DOMENE-MODELL ANALYSE
**Formål**: Bruker det refaktorerte Domain-Driven Design systemet
```python
# Bruker Value Objects og domeneklasser:
battery = Battery(BatterySpecification(
    capacity=Energy.from_kwh(100),
    max_power=Power.from_kw(50),
    efficiency=0.90
))

pv_system = PVSystem(PVSystemSpecification(
    installed_capacity=Power.from_kw(138.55),
    inverter_capacity=Power.from_kw(110)
))
```

**Funksjoner**:
- ✅ Bruker fullstendig DDD-arkitektur
- ✅ Type-safe med Value Objects (Energy, Power, Money)
- ✅ Objektmodellering av batteri og solceller
- ✅ Mer realistisk batterisimulering med state management
- ❌ Mer kompleks å justere parametere
- ❌ Krever forståelse av domenemodellen

**Bruk dette når**: Du vil bruke den "riktige" arkitekturen eller integrere med resten av systemet

---

## 🎯 HVILKEN SKAL JEG BRUKE?

| Scenario | Anbefalt script | Hvorfor |
|----------|-----------------|---------|
| **Rask test** | `run_clean_analysis.py` | Ferdig oppsatt, kjører alt |
| **Teste batteristørrelser** | `run_custom_analysis.py` | Enkelt å endre parametere |
| **Teste kostnader** | `run_custom_analysis.py` | Alt samlet øverst |
| **Produksjonssystem** | `run_real_analysis.py` | Riktig arkitektur |
| **Integrasjon med API** | `run_real_analysis.py` | Bruker domenemodeller |

## 🔧 EKSEMPEL: ENDRE BATTERISTØRRELSE

### Med `run_custom_analysis.py` (ENKLEST):
```python
# Linje 24-25: Bare endre disse
BATTERY_CAPACITY_KWH = 200  # Fra 50 til 200
BATTERY_POWER_KW = 100      # Fra 25 til 100
```

### Med `run_clean_analysis.py`:
```python
# Linje 32-33: Endre her
BATTERY_CAPACITY_KWH = 200
BATTERY_POWER_KW = 100
```

### Med `run_real_analysis.py` (AVANSERT):
```python
# Linje 40-45: Må endre Value Objects
battery_spec = BatterySpecification(
    capacity=Energy.from_kwh(200),  # Endret
    max_power=Power.from_kw(100),   # Endret
    efficiency=0.90,
    degradation_rate=0.02
)
```

## 📈 OUTPUT FORSKJELLER

### `run_clean_analysis.py`:
- Mest detaljert output
- Sensitivitetsanalyse tabell
- Månedlig avkortningsfordeling
- Full oppsummering

### `run_custom_analysis.py`:
- Fokusert output
- Direkte konklusjon (lønnsom/ulønnsom)
- Break-even margin
- Tips om justering

### `run_real_analysis.py`:
- Teknisk output med Value Objects
- Viser Energy(100.0 kWh) format
- Timesbasert simulering
- Batteritilstand tracking

## 💡 MIN ANBEFALING

**Start med**: `run_custom_analysis.py`
- Enklest å forstå
- Raskest å justere
- Gir all nødvendig info

**Gå videre til**: `run_clean_analysis.py`
- Når du vil ha sensitivitetsanalyse
- For mer detaljerte resultater

**Bruk til slutt**: `run_real_analysis.py`
- Når systemet skal i produksjon
- For integrasjon med andre systemer
- Hvis du trenger type-safety