#!/usr/bin/env python3
"""
Summary of DC vs AC production differences
"""

import pickle
import pandas as pd
import numpy as np

# Load results
with open('results/simulation_results_dc.pkl', 'rb') as f:
    results = pickle.load(f)

production_dc = results['production_dc']
production_ac = results['production_ac']
inverter_clipping = results['inverter_clipping']
base_results = results['base_results']

# Calculate key metrics
total_dc = production_dc.sum()
total_ac = production_ac.sum()
max_dc = production_dc.max()
max_ac = production_ac.max()
inverter_losses = inverter_clipping.sum()
grid_losses = base_results['grid_curtailment'].sum()

# Hours above limits
hours_above_inverter = (production_dc * 0.98 > 100).sum()  # DC * efficiency > inverter limit
hours_above_grid = (production_ac > 77).sum()

# Monthly analysis
monthly_stats = pd.DataFrame({
    'DC_MWh': production_dc.resample('ME').sum() / 1000,
    'AC_MWh': production_ac.resample('ME').sum() / 1000,
    'Inverter_Loss_MWh': inverter_clipping.resample('ME').sum() / 1000,
    'Grid_Loss_MWh': base_results['grid_curtailment'].resample('ME').sum() / 1000
})
monthly_stats.index = ['Jan', 'Feb', 'Mar', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Des']

print("="*70)
print("DC vs AC PRODUKSJONSANALYSE - SNØDEVEGEN 122")
print("="*70)
print("\n📊 ÅRLIGE TOTALER:")
print(f"  DC produksjon (før inverter):     {total_dc:,.0f} kWh")
print(f"  AC produksjon (etter inverter):   {total_ac:,.0f} kWh")
print(f"  Invertertap (DC→AC konvertering):  {total_dc - total_ac - inverter_losses:,.0f} kWh (2% effektivitetstap)")
print(f"  Inverter clipping (over 100 kW):   {inverter_losses:,.0f} kWh")
print(f"  Grid curtailment (over 77 kW):     {grid_losses:,.0f} kWh")
print(f"  TOTALE TAP:                        {total_dc - total_ac + grid_losses:,.0f} kWh")

print("\n⚡ MAKSIMALVERDIER:")
print(f"  Maks DC produksjon:   {max_dc:.1f} kW (av 138.55 kWp installert)")
print(f"  Maks AC produksjon:   {max_ac:.1f} kW (begrenset av 100 kW inverter)")
print(f"  Utnyttelse av DC:     {max_dc/138.55*100:.1f}%")

print("\n⏰ TIMER OVER KAPASITETSGRENSER:")
print(f"  Timer DC > inverter (100 kW):  {hours_above_inverter:,} timer ({hours_above_inverter/8760*100:.1f}%)")
print(f"  Timer AC > nettgrense (77 kW): {hours_above_grid:,} timer ({hours_above_grid/8760*100:.1f}%)")

print("\n📅 MÅNEDLIG FORDELING:")
print(monthly_stats.round(1).to_string())

print("\n💡 KONKLUSJON:")
print(f"  • Invertertap utgjør {inverter_losses/total_dc*100:.1f}% av DC-produksjonen")
print(f"  • Grid curtailment utgjør {grid_losses/total_ac*100:.1f}% av AC-produksjonen")
print(f"  • Totalt går {(inverter_losses + grid_losses)/total_dc*100:.1f}% av DC-produksjonen tapt")
print(f"  • Batteri kan primært redusere grid curtailment ({grid_losses:.0f} kWh)")
print(f"  • Inverter clipping ({inverter_losses:.0f} kWh) kan kun løses med større inverter")

# Economic impact
spot_price = 0.85  # NOK/kWh average
print(f"\n💰 ØKONOMISK VERDI AV TAP:")
print(f"  Invertertap:     {inverter_losses * spot_price:,.0f} NOK/år")
print(f"  Grid curtailment: {grid_losses * spot_price:,.0f} NOK/år")
print(f"  TOTAL TAPT VERDI: {(inverter_losses + grid_losses) * spot_price:,.0f} NOK/år")