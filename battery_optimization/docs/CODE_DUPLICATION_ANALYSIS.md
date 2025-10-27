# Kodeduplikasjon - Analyse og Opprydding

**Dato**: 2025-10-27
**Problem**: Overlappende funksjonalitet i flere moduler
**Status**: ⚠️ Kritisk duplikasjon oppdaget

---

## 🔍 Oppdagede Duplikasjoner

### 1. Forbruksprofil-generering

**Overlapp mellom**:
- `core/data_generators.py` → `generate_consumption_profile()`
- `core/consumption_profiles.py` → `ConsumptionProfile.generate_annual_profile()`

**Analyse**:

| Fil | Funksjonalitet | Profiler | Kvalitet |
|-----|---------------|----------|----------|
| `data_generators.py` | Enkel generering | commercial, residential, industrial | Basic |
| `consumption_profiles.py` | Detaljert modellering | commercial_office, commercial_retail, industrial | Høy ✅ |

**Forskjeller**:

**data_generators.py** (enkel):
```python
# Generisk "commercial" profil
if weekday:
    if 7 <= hour <= 17:
        load_factor = 1.5  # Flat faktor
```

**consumption_profiles.py** (realistisk):
```python
# Spesifikk "commercial_office" med lunsj-dipp
weekday = np.array([
    0.30, 0.30, ..., 0.50, 0.70, 0.90, 1.00, 1.00, 0.95,  # Oppstart
    0.70, 0.75, 0.95, 1.00, ...  # LUNSJ-DIPP kl 12!
])
```

**Vinner**: `consumption_profiles.py` ✅
- Mer realistiske profiler
- Lunsj-dipp modellering
- Bedre strukturert
- Dedicated testing i main-blokk

---

### 2. Solproduksjon-generering

**Overlapp mellom**:
- `core/data_generators.py` → `generate_solar_production()`
- `core/solar.py` → `SolarSystem.generate_production()`
- `core/pvgis_solar.py` → `PVGISProduction._generate_synthetic_production()` (fallback)

**Analyse**:

| Fil | Metode | Kvalitet | Når brukt |
|-----|--------|----------|-----------|
| `data_generators.py` | Pattern-based | Basic | Uspesifisert |
| `solar.py` | Pattern-based | Basic | Fallback |
| `pvgis_solar.py` | pvlib/pattern | Medium/High | PVGIS API fallback |

**Alle tre gjør SAMME ting**:
- Sesongvariasjon (månedlige faktorer)
- Daglig mønster (time-faktorer)
- Værvariaasjon (tilfeldig)
- Inverter-klipping

**Problem**: 3 implementasjoner, ingen koordinering!

**Anbefaling**:
- Behold `pvgis_solar.py` (har best fallback med pvlib)
- Slett duplikatene i `data_generators.py` og `solar.py`

---

### 3. Strømpris-generering

**Kun i**:
- `core/data_generators.py` → `generate_electricity_prices()`

**Men vi har også**:
- `core/price_fetcher.py` → `fetch_prices()` (EKTE data fra ENTSO-E ✅)

**Analyse**:
- `data_generators.py`: Syntetiske priser (mønster-basert)
- `price_fetcher.py`: Ekte ENTSO-E API-data

**Anbefaling**:
- Behold `price_fetcher.py` (EKTE data)
- Slett syntetisk prisgenerator (eller flytt til test/utviklingsscript)

---

### 4. Konfigurasjon

**Overlapp mellom**:
- `config.yaml` (YAML-basert)
- `config.py` (Python dataclasses)

**Analyse**:

| Fil | Format | Fordel | Ulempe |
|-----|--------|--------|--------|
| `config.yaml` | YAML | Enkel å redigere | Ingen type-validering |
| `config.py` | Python dataclasses | Type-sikker, IDE-støtte | Litt mer verbose |

**Parametere**:

```yaml
# config.yaml
solar:
  pv_capacity_kwp: 138.55
  inverter_limit_kw: 110
  tilt_degrees: 30        # ❌ FEIL!
  azimuth_degrees: 180    # ❌ FEIL!
```

```python
# config.py (KORREKT)
@dataclass
class SolarSystemConfig:
    pv_capacity_kwp: float = 138.55
    inverter_capacity_kw: float = 100   # ✅ RIKTIG!
    tilt_degrees: float = 15.0          # ✅ RIKTIG (faktisk takhelning)
    azimuth_degrees: float = 173.0      # ✅ RIKTIG
```

**Problem**: `config.yaml` har FEIL verdier!
- Tilt: 30° (yaml) vs 15° (python) ← Faktisk verdi er 15°
- Azimuth: 180° (yaml) vs 173° (python) ← Faktisk verdi er 173°
- Inverter: 110 kW (yaml) vs 100 kW (python) ← Faktisk verdi er 100 kW

**Vinner**: `config.py` ✅
- Korrekte verdier
- Type-sikkerhet
- Bedre dokumentert
- Brukes i tester

---

## 📊 Oppsummering Duplikasjon

| Funksjonalitet | Filer | Anbefaling |
|---------------|-------|------------|
| Forbruksprofiler | 2 filer | Behold `consumption_profiles.py` |
| Solproduksjon | 3 filer | Behold `pvgis_solar.py`, slett andre |
| Strømpriser | 2 filer | Behold `price_fetcher.py` (ekte data) |
| Konfigurasjon | 2 filer | Behold `config.py`, arkiver `config.yaml` |

---

## 🎯 Anbefalinger

### Prioritet 1: Kritisk (Feil data)
1. **Arkiver config.yaml**
   - Har feil verdier for tilt, azimuth, inverter
   - Kan føre til feil i analyser
   - Action: `mv config.yaml archive/old_config/`

### Prioritet 2: Viktig (Forvirring)
2. **Konsolider forbruksprofiler**
   - Slett `generate_consumption_profile()` fra `data_generators.py`
   - Behold `consumption_profiles.py` (bedre kvalitet)

3. **Konsolider solproduksjon**
   - Slett `generate_solar_production()` fra `data_generators.py`
   - Vurder å slette `solar.py` (duplikat av pvgis_solar fallback)
   - Behold kun `pvgis_solar.py` (best implementasjon)

### Prioritet 3: Rydding (Syntetiske data)
4. **Håndter syntetiske data**
   - `generate_electricity_prices()` - Flytt til `tests/` hvis nødvendig
   - `generate_complete_dataset()` - Kan være nyttig for testing
   - Vurder: Behold `data_generators.py` KUN for testing/utvikling

---

## 📋 Detaljert Handlingsplan

### Scenario A: Aggressiv Rydding (Anbefalt)

**Slett/Arkiver**:
```bash
# Arkiver gammel config
mv config.yaml archive/old_config/

# Slett duplikater
rm core/data_generators.py   # Erstattes av spesialiserte moduler
rm core/solar.py              # Erstattes av pvgis_solar.py
```

**Resultat**:
- ✅ `consumption_profiles.py` → Forbruk
- ✅ `pvgis_solar.py` → Solproduksjon (API + fallback)
- ✅ `price_fetcher.py` → Strømpriser (API + fallback)
- ✅ `config.py` → Konfigurasjon

**Fordeler**:
- Ingen duplikasjon
- Klar ansvar per modul
- Kun EKTE data (ikke syntetisk)

**Ulemper**:
- Mister `generate_complete_dataset()` for testing

---

### Scenario B: Bevaring av Testdata

**Behold `data_generators.py` MEN**:
- Flytt til `tests/test_data_generators.py`
- Merk klart at det er KUN for testing
- Slett overlappende funksjoner

**Refaktor**:
```python
# tests/test_data_generators.py
"""
TESTING ONLY - Synthetic data generation for unit tests
NOT FOR PRODUCTION USE - Use real data from APIs instead!
"""

def generate_test_consumption(...):
    """Generate synthetic consumption for testing"""
    # Simplified version

def generate_test_production(...):
    """Generate synthetic production for testing"""
    # Simplified version

def generate_complete_test_dataset(...):
    """Generate complete synthetic dataset for integration tests"""
    # Combines test data
```

**Produksjonsmoduler**:
```python
# core/consumption_profiles.py → Ekte forbruksprofiler
# core/pvgis_solar.py → PVGIS API + fallback
# core/price_fetcher.py → ENTSO-E API + fallback
# config.py → Korrekt konfigurasjon
```

---

## 🔍 Analyse per fil

### `core/data_generators.py` - Vurdering

**Innhold**:
- `generate_solar_production()` → Duplikat av `solar.py` og `pvgis_solar.py`
- `generate_consumption_profile()` → Enklere enn `consumption_profiles.py`
- `generate_electricity_prices()` → Syntetisk (ikke ekte ENTSO-E data)
- `generate_complete_dataset()` → Nyttig for testing
- `calculate_curtailment()` → Duplikat av `solar.py`

**Anbefaling**: ⚠️ **Refaktorer til test-modul**
- Flytt til `tests/test_data_generators.py`
- Bruk KUN for testing
- Produktsjonskode skal bruke ekte API-data

---

### `core/consumption_profiles.py` - Vurdering

**Innhold**:
- `commercial_office()` → Detaljert profil med lunsj-dipp ✅
- `commercial_retail()` → Uten lunsj-dipp (butikk) ✅
- `industrial()` → Skiftarbeid-mønster ✅
- `generate_annual_profile()` → Generer full årsprofil ✅

**Anbefaling**: ✅ **BEHOLD**
- Høy kvalitet
- Realistiske profiler
- Godt dokumentert
- Har testing i `__main__`

---

### `core/solar.py` - Vurdering

**Innhold**:
- `SolarSystem.generate_production()` → Duplikat av pvgis fallback
- `calculate_curtailment()` → Duplikat av data_generators

**Anbefaling**: ❌ **SLETT**
- Alt finnes i `pvgis_solar.py` (bedre implementasjon)
- Ingen unik funksjonalitet
- Kun 80 linjer kode

---

### `core/pvgis_solar.py` - Vurdering

**Innhold**:
- PVGIS API integration ✅
- Caching ✅
- Fallback til pvlib (best) ✅
- Fallback til pattern (ok) ✅

**Anbefaling**: ✅ **BEHOLD**
- Høyeste kvalitet
- Ekte PVGIS data
- Best fallback-hierarki
- Allerede testet (19/19 tests pass)

---

### `config.yaml` - Vurdering

**Innhold**:
- Gammel YAML konfigurasjon
- **FEIL verdier** (tilt 30° vs 15°, azimuth 180° vs 173°)

**Anbefaling**: 🗄️ **ARKIVER**
- Feil data kan føre til feilanalyser
- `config.py` har korrekte verdier
- YAML brukes ikke lenger

---

### `config.py` - Vurdering

**Innhold**:
- `LocationConfig` ✅
- `SolarSystemConfig` ✅ (korrekte verdier!)
- `ConsumptionConfig` ✅
- `BatteryConfig` ✅
- `TariffConfig` ✅
- `EconomicConfig` ✅

**Anbefaling**: ✅ **BEHOLD**
- Korrekte verdier
- Type-sikkerhet
- Godt dokumentert
- Brukes i alle tester

---

## 🚀 Implementasjonsplan

### Fase 1: Sikkerhet (Arkiver gammel config)
```bash
mkdir -p archive/old_config
mv config.yaml archive/old_config/config.yaml.deprecated
echo "DEPRECATED: Use config.py instead" > archive/old_config/README.md
```

### Fase 2: Test Scenario A (Slett duplikater)
```bash
# Sikkerhetskopi først
mkdir -p archive/deprecated_generators
cp core/data_generators.py archive/deprecated_generators/
cp core/solar.py archive/deprecated_generators/

# Slett duplikater
rm core/data_generators.py
rm core/solar.py

# Test at alt fortsatt virker
python -m pytest tests/ -v
```

### Fase 3: Oppdater imports (hvis nødvendig)
```bash
# Sjekk for imports av slettede moduler
grep -r "from core.data_generators" . --include="*.py"
grep -r "from core.solar import" . --include="*.py"
grep -r "import yaml" . --include="*.py"

# Oppdater til:
# from core.consumption_profiles import ConsumptionProfile
# from core.pvgis_solar import PVGISProduction
# from config import SolarSystemConfig (ikke yaml!)
```

---

## ✅ Forventet Resultat

**Før opprydding**:
- 7 filer med overlappende funksjonalitet
- 2 konfig-filer med ULIKE verdier
- Forvirring om hvilken som er "korrekt"
- Risiko for feil pga feil config-verdier

**Etter opprydding**:
- 4 klare moduler med distinkt ansvar
- 1 konfig-fil (config.py) med korrekte verdier
- Ingen duplikasjon
- Klar struktur:
  - `consumption_profiles.py` → Forbruk
  - `pvgis_solar.py` → Sol (API + fallback)
  - `price_fetcher.py` → Priser (API + fallback)
  - `config.py` → Konfigurasjon

---

## 📊 Risiko-analyse

### Lav Risiko ✅
- Slette `config.yaml` (ikke brukt, feil verdier)
- Slette `solar.py` (alt finnes i pvgis_solar.py)

### Moderat Risiko ⚠️
- Slette `data_generators.py`
  - Kan brytes hvis noen bruker `generate_complete_dataset()`
  - Løsning: Flytt til test-modul hvis nødvendig

### Validering
```bash
# Test at ingenting er ødelagt
python -m pytest tests/test_price_data_fetching.py -v
python -m pytest tests/test_solar_production.py -v

# Kjør hovedsimulering
python run_simulation.py
```

---

**Konklusjon**: Vi har betydelig kodeduplikasjon som skaper forvirring og risiko for feil. Anbefaler aggressiv opprydding for å:
1. Eliminere duplikasjon
2. Bruke korrekte verdier (fra config.py)
3. Klargjøre ansvar per modul
4. Redusere vedlikeholdsbyrde

**Neste steg**: Få godkjenning fra Klaus for scenario A (aggressiv rydding) eller B (bevare testdata).
