# Report Generation Guide for Battery Optimization Analysis

## Oversikt
Denne guiden gir detaljerte instruksjoner for å fylle ut `battery_optimization_report_template.ipynb` med analyseresultater fra batterioptimaliseringsprosjektet.

## Generelle retningslinjer

### Kodevisning
- **SKJUL ALL KODE** i den endelige rapporten
- Bruk `%%capture` magic eller konfigurer notebook til å skjule input-celler
- Vis kun resultater, grafer og tabeller

### Formatering
- Bruk norsk språk i all tekst som vises til bruker
- Hold profesjonell tone
- Bruk konsistente farger i grafer (blå for produksjon, rød for curtailment, grønn for batterilading)
- Alle monetære verdier i NOK med tusen-separator

### Visualisering
- Preferert bibliotek: `plotly.express` for interaktive grafer, alternativt `matplotlib`/`seaborn`
- Figurstørrelse: width=10, height=6 som standard
- Inkluder grid, labels og legendes på alle grafer
- Bruk subplot når flere relaterte grafer skal vises sammen

## Seksjonsspesifikke instruksjoner

### Executive Summary
```python
# Eksempel format:
summary_points = [
    f"• Optimal batteristørrelse: {optimal_kwh:.0f} kWh @ {optimal_kw:.0f} kW",
    f"• NPV ved optimal størrelse: {npv_optimal:,.0f} NOK",
    f"• Payback periode: {payback:.1f} år",
    f"• Break-even batterikostnad: {breakeven:,.0f} NOK/kWh",
    f"• Hovedverdidriver: {main_driver}"
]
```

### 1. Systemkonfigurasjon
```python
import pandas as pd

# Lag strukturert tabell
config_data = {
    'Parameter': ['PV Kapasitet', 'Inverter', 'Grid Limit', 'Lokasjon', 'Orientering', 'Helning'],
    'Verdi': ['150 kWp', '110 kW', '77 kW', 'Stavanger', 'Sør', '25°'],
    'Kommentar': ['Installert DC kapasitet', 'AC inverter kapasitet', '70% av inverter',
                  '58.97°N, 5.73°E', 'Azimuth 180°', 'Optimal for årsproduksjon']
}
pd.DataFrame(config_data).style.hide(axis='index')
```

### 2. Produksjonsanalyse
```python
# Varighetskurve eksempel
import numpy as np
import plotly.graph_objects as go

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=np.arange(len(production_sorted))/len(production_sorted)*100,
    y=production_sorted,
    name='Produksjon',
    fill='tozeroy'
))
fig.add_hline(y=77, line_dash="dash", line_color="red",
              annotation_text="Grid limit (77 kW)")
fig.update_layout(
    title="Varighetskurve - Timesproduksjon",
    xaxis_title="Andel av året (%)",
    yaxis_title="Effekt (kW)"
)
```

### 3. Prisanalyse
```python
# Vis prisvariasjoner med peak/off-peak perioder
fig, axes = plt.subplots(2, 1, figsize=(12, 8))

# Spotpriser
axes[0].plot(dates, spot_prices, alpha=0.7)
axes[0].set_title('Spotpriser NO2 - 2024')
axes[0].set_ylabel('NOK/kWh')

# Nettleie med fargekoding for peak/off-peak
colors = ['red' if is_peak else 'blue' for is_peak in peak_hours]
axes[1].scatter(dates, total_tariff, c=colors, alpha=0.3, s=1)
axes[1].set_title('Total nettleie (peak=rød, off-peak=blå)')
```

### 4. Batterioptimalisering
```python
# NPV-kurve med optimal punkt markert
fig = px.line(results_df, x='battery_kwh', y='npv',
              title='NPV vs Batteristørrelse',
              labels={'battery_kwh': 'Batteristørrelse (kWh)', 'npv': 'NPV (NOK)'})
fig.add_scatter(x=[optimal_kwh], y=[optimal_npv],
                mode='markers', marker=dict(size=15, color='red'),
                name=f'Optimal: {optimal_kwh:.0f} kWh')
fig.update_traces(hovertemplate='%{y:,.0f} NOK ved %{x:.0f} kWh')
```

### 5. Sensitivitetsanalyse
```python
# Heatmap eksempel
import seaborn as sns

fig, ax = plt.subplots(figsize=(12, 8))
sns.heatmap(npv_matrix,
            xticklabels=[f'{x:.0f}' for x in battery_sizes],
            yticklabels=[f'{y:.0f}' for y in battery_costs],
            annot=True, fmt='.0f', cmap='RdYlGn', center=0,
            cbar_kws={'label': 'NPV (NOK)'})
ax.set_xlabel('Batteristørrelse (kWh)')
ax.set_ylabel('Batterikostnad (NOK/kWh)')
plt.title('NPV Sensitivitet - Batteristørrelse vs Kostnad')
```

### 6. Markedssammenligning
```python
# Sammenligningstabel
comparison = pd.DataFrame({
    'Scenario': ['Markedspris', 'Break-even', 'Differanse'],
    'Batterikostnad (NOK/kWh)': [5000, breakeven_cost, 5000-breakeven_cost],
    'NPV (NOK)': [npv_market, 0, npv_market],
    'Kommentar': ['Dagens pris', 'Null-NPV punkt', 'Kostreduksjon kreves']
})
display(comparison.style.format({'Batterikostnad (NOK/kWh)': '{:,.0f}',
                                 'NPV (NOK)': '{:,.0f}'}))
```

## Datakilder og import

### Hente reelle data
```python
# Fra eksisterende analyse-filer
from battery_optimization.core.pvgis_solar import get_pvgis_production
from battery_optimization.core.entso_e_prices import get_prices_2024
from battery_optimization.core.consumption_profiles import ConsumptionProfile

# Last inn cached resultater hvis tilgjengelig
import pickle
try:
    with open('battery_optimization/results/optimization_results.pkl', 'rb') as f:
        cached_results = pickle.load(f)
except FileNotFoundError:
    # Kjør ny optimalisering
    pass
```

### Standardverdier hvis data mangler
```python
# Fallback verdier basert på tidligere analyser
DEFAULT_OPTIMAL_BATTERY = 80  # kWh
DEFAULT_OPTIMAL_POWER = 50    # kW
DEFAULT_BREAKEVEN = 3500       # NOK/kWh
DEFAULT_NPV_AT_5000 = -500000  # NOK
```

## Feilhåndtering

```python
import warnings
warnings.filterwarnings('ignore')  # Skjul advarsler i rapport

# Wrap kritisk kode
try:
    # Kjør analyse
    results = run_optimization()
except Exception as e:
    # Bruk fallback verdier og informer
    print(f"Bruker cached resultater grunnet: {e}")
    results = load_cached_results()
```

## Eksportering

### Lagre som HTML (for deling)
```bash
jupyter nbconvert battery_optimization_report.ipynb --to html --no-input
```

### Lagre som PDF
```bash
jupyter nbconvert battery_optimization_report.ipynb --to pdf --no-input
```

## Sjekkliste før ferdigstilling

- [ ] All kode er skjult
- [ ] Alle grafer har titler og akselabels
- [ ] Executive summary er konsis og informativ
- [ ] Konklusjoner er basert på faktiske resultater
- [ ] Alle NOK-verdier har tusen-separator
- [ ] Ingen feilmeldinger eller advarsler vises
- [ ] Notebook kjører fra topp til bunn uten feil

## Claude-spesifikke instruksjoner

Når du fyller ut notebooken:
1. Les denne guiden først
2. Bruk `NotebookEdit` tool med `edit_mode="replace"` for hver celle
3. Test at koden kjører før du setter inn i notebook
4. Fokuser på visuelle resultater fremfor tekniske detaljer
5. Hold språket konsist (norsk) og profesjonelt