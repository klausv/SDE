"""
Visualiser simuleringsresultater for 3 uker fra 1. juni
"""
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

def plot_three_weeks(start_date='2020-06-01', weeks=3):
    """
    Plot 3 uker med simuleringsdata

    Args:
        start_date: Startdato (YYYY-MM-DD)
        weeks: Antall uker å plotte
    """
    # Last resultater
    print("Laster resultater...")
    results_ref = pd.read_csv('results/test_strategy_reference.csv')
    results_simple = pd.read_csv('results/test_strategy_simple.csv')

    # Konverter timestamp til datetime
    results_ref['timestamp'] = pd.to_datetime(results_ref['timestamp'])
    results_simple['timestamp'] = pd.to_datetime(results_simple['timestamp'])

    # Filtrer til valgt periode
    start = pd.Timestamp(start_date)
    end = start + pd.Timedelta(days=weeks*7)

    df_ref = results_ref[(results_ref['timestamp'] >= start) & (results_ref['timestamp'] < end)]
    df_simple = results_simple[(results_simple['timestamp'] >= start) & (results_simple['timestamp'] < end)]

    print(f"Plotter {len(df_ref)} timer fra {start.date()} til {end.date()}")

    # Lag figur med 2 kolonner (referanse vs SimpleRule)
    fig, axes = plt.subplots(4, 2, figsize=(16, 12))
    fig.suptitle(f'Batterisimulering: {weeks} uker fra {start.date()}', fontsize=16, fontweight='bold')

    # Venstre kolonne: REFERANSE (uten batteri)
    # Høyre kolonne: SIMPLERULE (med batteri)

    titles = [
        'REFERANSE (uten batteri)',
        'SIMPLE RULE (100kWh/50kW batteri)'
    ]

    dataframes = [df_ref, df_simple]

    for col, (df, title) in enumerate(zip(dataframes, titles)):
        # Rad 1: Forbruk og Produksjon
        ax = axes[0, col]
        ax.plot(df['timestamp'], df['production_kw'], label='Solkraft', color='orange', linewidth=1.5, alpha=0.8)
        ax.plot(df['timestamp'], df['consumption_kw'], label='Forbruk', color='blue', linewidth=1.5, alpha=0.8)
        ax.fill_between(df['timestamp'], 0, df['production_kw'], alpha=0.3, color='orange', label='_nolegend_')
        ax.fill_between(df['timestamp'], 0, df['consumption_kw'], alpha=0.2, color='blue', label='_nolegend_')
        ax.set_ylabel('Effekt (kW)', fontsize=10)
        ax.set_title(f'{title}\nForbruk og Produksjon', fontsize=11, fontweight='bold')
        ax.legend(loc='upper right', fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.set_xticklabels([])

        # Rad 2: Nettimport/eksport
        ax = axes[1, col]
        # Split til import (positiv) og eksport (negativ)
        grid_import = df['grid_power_kw'].clip(lower=0)
        grid_export = df['grid_power_kw'].clip(upper=0)

        ax.fill_between(df['timestamp'], 0, grid_import, alpha=0.4, color='red', label='Import fra nett')
        ax.fill_between(df['timestamp'], 0, grid_export, alpha=0.4, color='green', label='Eksport til nett')
        ax.axhline(y=0, color='black', linewidth=0.5, linestyle='--')
        ax.set_ylabel('Netteffekt (kW)', fontsize=10)
        ax.set_title('Import/Eksport til nett', fontsize=11, fontweight='bold')
        ax.legend(loc='upper right', fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.set_xticklabels([])

        # Rad 3: Batteri power (kun for SimpleRule)
        ax = axes[2, col]
        if col == 1:  # Kun for SimpleRule
            battery_charge = df['battery_power_kw'].clip(lower=0)
            battery_discharge = df['battery_power_kw'].clip(upper=0)

            ax.fill_between(df['timestamp'], 0, battery_charge, alpha=0.4, color='green', label='Lading')
            ax.fill_between(df['timestamp'], 0, battery_discharge, alpha=0.4, color='red', label='Utlading')
            ax.axhline(y=0, color='black', linewidth=0.5, linestyle='--')
            ax.set_ylabel('Batterieffekt (kW)', fontsize=10)
            ax.set_title('Batterilading/utlading', fontsize=11, fontweight='bold')
            ax.legend(loc='upper right', fontsize=9)
        else:
            ax.text(0.5, 0.5, 'Ingen batteri', ha='center', va='center',
                   fontsize=14, color='gray', transform=ax.transAxes)
            ax.set_ylabel('Batterieffekt (kW)', fontsize=10)
            ax.set_title('Batterilading/utlading', fontsize=11, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.set_xticklabels([])

        # Rad 4: Battery SOC (kun for SimpleRule)
        ax = axes[3, col]
        if col == 1:  # Kun for SimpleRule
            ax.plot(df['timestamp'], df['battery_soc_kwh'], color='purple', linewidth=2)
            ax.fill_between(df['timestamp'], 0, df['battery_soc_kwh'], alpha=0.3, color='purple')
            ax.axhline(y=90, color='red', linewidth=1, linestyle='--', alpha=0.5, label='Max SOC (90%)')
            ax.axhline(y=10, color='orange', linewidth=1, linestyle='--', alpha=0.5, label='Min SOC (10%)')
            ax.set_ylabel('SOC (kWh)', fontsize=10)
            ax.set_xlabel('Dato', fontsize=10)
            ax.set_title('Battery State of Charge', fontsize=11, fontweight='bold')
            ax.legend(loc='upper right', fontsize=9)
            ax.set_ylim(0, 100)
        else:
            ax.text(0.5, 0.5, 'Ingen batteri', ha='center', va='center',
                   fontsize=14, color='gray', transform=ax.transAxes)
            ax.set_ylabel('SOC (kWh)', fontsize=10)
            ax.set_xlabel('Dato', fontsize=10)
            ax.set_title('Battery State of Charge', fontsize=11, fontweight='bold')
        ax.grid(True, alpha=0.3)

        # Formater x-akse
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=2))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=9)

    plt.tight_layout()

    # Lagre figur
    filename = f'results/plot_3_weeks_{start.strftime("%Y%m%d")}.png'
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    print(f"\n✓ Figur lagret: {filename}")
    plt.close()

    # Print statistikk for perioden
    print(f"\n{'='*60}")
    print(f"STATISTIKK FOR PERIODEN ({start.date()} til {end.date()})")
    print(f"{'='*60}")

    for name, df in [('Referanse', df_ref), ('SimpleRule', df_simple)]:
        print(f"\n{name}:")
        print(f"  Total produksjon:    {df['production_kw'].sum():8.0f} kWh")
        print(f"  Total forbruk:       {df['consumption_kw'].sum():8.0f} kWh")
        print(f"  Total nettimport:    {df[df['grid_power_kw'] > 0]['grid_power_kw'].sum():8.0f} kWh")
        print(f"  Total netteksport:   {-df[df['grid_power_kw'] < 0]['grid_power_kw'].sum():8.0f} kWh")
        print(f"  Peak nettimport:     {df['grid_power_kw'].max():8.1f} kW")

        if 'battery_soc_kwh' in df.columns and df['battery_soc_kwh'].max() > 0:
            print(f"  Batterilading:       {df[df['battery_power_kw'] > 0]['battery_power_kw'].sum():8.0f} kWh")
            print(f"  Batteriutlading:     {df[df['battery_power_kw'] < 0]['battery_power_kw'].abs().sum():8.0f} kWh")
            print(f"  SOC start/slutt:     {df['battery_soc_kwh'].iloc[0]:8.1f} / {df['battery_soc_kwh'].iloc[-1]:.1f} kWh")


if __name__ == "__main__":
    plot_three_weeks(start_date='2020-06-01', weeks=3)
