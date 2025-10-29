"""
Visualiser input-data: Solkraft, Forbruk og Spotpriser for 2024
Plotter 3 uker fra 1. juni 2024
"""
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from core.pvgis_solar import PVGISProduction
from core.price_fetcher import ENTSOEPriceFetcher
from core.consumption_profiles import ConsumptionProfile


def plot_input_data_three_weeks(start_date='2020-06-01', weeks=3):
    """
    Plotter input-data for 3 uker
    Bruker PVGIS sitt typiske år (2020) for alle data
    """
    print("="*60)
    print("LASTER INPUT-DATA (TYPISK ÅR)")
    print("="*60)

    # 1. Last solkraftproduksjon (PVGIS - typisk år, returnerer 2020-data)
    print("\n1. Solkraftproduksjon (PVGIS typisk år)...")
    pvgis = PVGISProduction(
        lat=58.97,
        lon=5.73,
        pv_capacity_kwp=138.55,
        tilt=30,
        azimuth=173,
        system_loss=14
    )
    production = pvgis.fetch_hourly_production(2024, refresh=False)  # Returnerer 2020-data
    print(f"   ✓ {len(production)} timer, sum={production.sum():.0f} kWh")

    # 2. Generer forbruk for samme år som PVGIS (2020)
    print("\n2. Forbruk (syntetisk commercial office)...")
    year = production.index[0].year  # Hent år fra PVGIS (2020)
    consumption = ConsumptionProfile.generate_annual_profile(
        profile_type='commercial_office',
        annual_kwh=300000,
        year=year
    )
    print(f"   ✓ {len(consumption)} timer, sum={consumption.sum():.0f} kWh")

    # 3. Last spotpriser for 2024 (reelle data)
    print("\n3. Spotpriser (ENTSO-E NO2 2024 - reelle data)...")
    price_fetcher = ENTSOEPriceFetcher()
    spot_prices = price_fetcher.fetch_prices(2024, 'NO2', refresh=False)
    # Konverter priser til samme år som PVGIS
    spot_prices.index = spot_prices.index.map(lambda x: x.replace(year=year))
    print(f"   ✓ {len(spot_prices)} timer, gjennomsnitt={spot_prices.mean():.2f} NOK/kWh")

    # Aligner til minimum lengde
    min_len = min(len(production), len(consumption), len(spot_prices))
    production = production[:min_len]
    consumption = consumption[:min_len]
    spot_prices = spot_prices[:min_len]
    print(f"\n   Aligned til {min_len} timer")

    # Filtrer til valgt periode
    start = pd.Timestamp(start_date)
    end = start + pd.Timedelta(days=weeks*7)

    mask = (production.index >= start) & (production.index < end)
    prod_period = production[mask]
    cons_period = consumption[mask]
    price_period = spot_prices[mask]

    print(f"\n4. Filtrert til {len(prod_period)} timer fra {start.date()} til {end.date()}")

    # PLOT
    print("\n5. Lager plot...")
    fig, ax1 = plt.subplots(figsize=(16, 8))

    # Venstre y-akse: Effekt (kW)
    color_prod = 'orange'
    color_cons = 'blue'

    ax1.set_xlabel('Dato', fontsize=12)
    ax1.set_ylabel('Effekt (kW)', fontsize=12, color='black')

    # Plot produksjon
    line1 = ax1.plot(prod_period.index, prod_period.values,
                     label='Solkraftproduksjon', color=color_prod,
                     linewidth=1.5, alpha=0.8)
    ax1.fill_between(prod_period.index, 0, prod_period.values,
                     alpha=0.3, color=color_prod)

    # Plot forbruk
    line2 = ax1.plot(cons_period.index, cons_period.values,
                     label='Forbruk', color=color_cons,
                     linewidth=1.5, alpha=0.8)
    ax1.fill_between(cons_period.index, 0, cons_period.values,
                     alpha=0.2, color=color_cons)

    ax1.tick_params(axis='y', labelcolor='black')
    ax1.grid(True, alpha=0.3)

    # Høyre y-akse: Pris (NOK/kWh)
    ax2 = ax1.twinx()
    color_price = 'green'
    ax2.set_ylabel('Spotpris (NOK/kWh)', fontsize=12, color=color_price)

    line3 = ax2.plot(price_period.index, price_period.values,
                     label='Spotpris', color=color_price,
                     linewidth=2, alpha=0.7, linestyle='--')

    ax2.tick_params(axis='y', labelcolor=color_price)

    # Kombinert legend
    lines = line1 + line2 + line3
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc='upper left', fontsize=11)

    # Formater x-akse
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
    ax1.xaxis.set_major_locator(mdates.DayLocator(interval=2))
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=10)

    # Tittel
    plt.title(f'Input-data: {weeks} uker fra {start.date()}\n'
              f'Solkraft, Forbruk og Spotpriser',
              fontsize=14, fontweight='bold')

    plt.tight_layout()

    # Lagre
    filename = f'results/plot_input_data_{start.strftime("%Y%m%d")}.png'
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    print(f"   ✓ Figur lagret: {filename}")
    plt.close()

    # Statistikk
    print("\n" + "="*60)
    print(f"STATISTIKK FOR PERIODEN ({start.date()} til {end.date()})")
    print("="*60)

    print(f"\nSolkraftproduksjon:")
    print(f"  Total:           {prod_period.sum():8.0f} kWh")
    print(f"  Gjennomsnitt:    {prod_period.mean():8.1f} kW")
    print(f"  Maks:            {prod_period.max():8.1f} kW")

    print(f"\nForbruk:")
    print(f"  Total:           {cons_period.sum():8.0f} kWh")
    print(f"  Gjennomsnitt:    {cons_period.mean():8.1f} kW")
    print(f"  Maks:            {cons_period.max():8.1f} kW")

    print(f"\nSpotpriser:")
    print(f"  Gjennomsnitt:    {price_period.mean():8.3f} NOK/kWh")
    print(f"  Min:             {price_period.min():8.3f} NOK/kWh")
    print(f"  Maks:            {price_period.max():8.3f} NOK/kWh")

    print(f"\nNetto:")
    surplus = prod_period - cons_period
    print(f"  Total overskudd: {surplus[surplus > 0].sum():8.0f} kWh")
    print(f"  Total underskudd:{-surplus[surplus < 0].sum():8.0f} kWh")

    print("\n" + "="*60)
    print("FERDIG!")
    print("="*60)


if __name__ == "__main__":
    plot_input_data_three_weeks(start_date='2020-06-01', weeks=3)
