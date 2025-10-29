"""
Visualiser batterisimulering: Input-data + Batteri-resultater
3 uker fra 1. juni
"""
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


def plot_battery_simulation(start_date='2020-06-01', weeks=3):
    """
    Plot input-data + batterisimulering for 3 uker

    Graf 1: Solkraft, Forbruk, Spotpriser (som før)
    Graf 2: SOC, Charge/Discharge, Import/Eksport
    """
    print("="*60)
    print("LASTER SIMULERINGSRESULTATER")
    print("="*60)

    # Last simuleringer
    print("\n1. Laster SimpleRule simulering...")
    df = pd.read_csv('results/test_strategy_simple.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Filtrer til valgt periode
    start = pd.Timestamp(start_date)
    end = start + pd.Timedelta(days=weeks*7)

    mask = (df['timestamp'] >= start) & (df['timestamp'] < end)
    df_period = df[mask].copy()

    print(f"   ✓ {len(df_period)} timer fra {start.date()} til {end.date()}")

    # Lag figur med 2 rader
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10), sharex=True)
    fig.suptitle(f'Batterisimulering: {weeks} uker fra {start.date()}\n'
                 f'SimpleRule (20kWh/10kW batteri)',
                 fontsize=14, fontweight='bold')

    # ==========================================
    # GRAF 1: Input-data (Solkraft, Forbruk, Spotpriser)
    # ==========================================

    # Venstre y-akse: Effekt (kW)
    color_prod = 'orange'
    color_cons = 'blue'

    ax1.set_ylabel('Effekt (kW)', fontsize=11, color='black')

    # Get production column - use AC if available
    prod_col = 'production_ac_kw' if 'production_ac_kw' in df_period.columns else 'production_kw'

    # Plot produksjon
    line1 = ax1.plot(df_period['timestamp'], df_period[prod_col],
                     label='Solkraftproduksjon (AC)', color=color_prod,
                     linewidth=1.5, alpha=0.8)
    ax1.fill_between(df_period['timestamp'], 0, df_period[prod_col],
                     alpha=0.3, color=color_prod)

    # Plot forbruk
    line2 = ax1.plot(df_period['timestamp'], df_period['consumption_kw'],
                     label='Forbruk', color=color_cons,
                     linewidth=1.5, alpha=0.8)
    ax1.fill_between(df_period['timestamp'], 0, df_period['consumption_kw'],
                     alpha=0.2, color=color_cons)

    ax1.tick_params(axis='y', labelcolor='black')
    ax1.grid(True, alpha=0.3)
    ax1.set_title('Input-data: Solkraft, Forbruk og Spotpriser',
                  fontsize=12, fontweight='bold', loc='left')

    # Høyre y-akse: Pris (NOK/kWh)
    ax1_right = ax1.twinx()
    color_price = 'green'
    ax1_right.set_ylabel('Spotpris (NOK/kWh)', fontsize=11, color=color_price)

    line3 = ax1_right.plot(df_period['timestamp'], df_period['spot_price'],
                          label='Spotpris', color=color_price,
                          linewidth=2, alpha=0.7, linestyle='--')

    ax1_right.tick_params(axis='y', labelcolor=color_price)

    # Kombinert legend for graf 1
    lines = line1 + line2 + line3
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc='upper left', fontsize=10)

    # ==========================================
    # GRAF 2: Batteri (SOC, Charge/Discharge, Import/Eksport)
    # ==========================================

    # Venstre y-akse: Effekt (kW)
    ax2.set_ylabel('Effekt (kW)', fontsize=11, color='black')
    ax2.set_xlabel('Dato', fontsize=11)

    # Use AC power for battery if available, else DC
    battery_col = 'battery_power_ac_kw' if 'battery_power_ac_kw' in df_period.columns else 'battery_power_kw'

    # Split batteri og grid til positive/negative
    battery_charge = df_period[battery_col].clip(lower=0)
    battery_discharge = df_period[battery_col].clip(upper=0)
    grid_import = df_period['grid_power_kw'].clip(lower=0)
    grid_export = df_period['grid_power_kw'].clip(upper=0)

    # Plot batteri
    ax2.fill_between(df_period['timestamp'], 0, battery_charge,
                    alpha=0.4, color='green', label='Batteri lading')
    ax2.fill_between(df_period['timestamp'], 0, battery_discharge,
                    alpha=0.4, color='red', label='Batteri utlading')

    # Plot nett
    ax2.fill_between(df_period['timestamp'], 0, grid_import,
                    alpha=0.3, color='darkred', label='Nettimport', hatch='//')
    ax2.fill_between(df_period['timestamp'], 0, grid_export,
                    alpha=0.3, color='darkgreen', label='Netteksport', hatch='\\\\')

    ax2.axhline(y=0, color='black', linewidth=0.5, linestyle='--')
    ax2.tick_params(axis='y', labelcolor='black')
    ax2.grid(True, alpha=0.3)
    ax2.set_title('Batteri og Nett: SOC, Lading/Utlading, Import/Eksport',
                  fontsize=12, fontweight='bold', loc='left')

    # Høyre y-akse: SOC (kWh)
    ax2_right = ax2.twinx()
    color_soc = 'purple'
    ax2_right.set_ylabel('SOC (kWh)', fontsize=11, color=color_soc)

    line_soc = ax2_right.plot(df_period['timestamp'], df_period['battery_soc_kwh'],
                             label='Battery SOC', color=color_soc,
                             linewidth=2.5, alpha=0.9)
    ax2_right.axhline(y=90, color='red', linewidth=1, linestyle=':', alpha=0.5)
    ax2_right.axhline(y=10, color='orange', linewidth=1, linestyle=':', alpha=0.5)
    ax2_right.set_ylim(0, 100)
    ax2_right.tick_params(axis='y', labelcolor=color_soc)

    # Kombinert legend for graf 2
    handles1, labels1 = ax2.get_legend_handles_labels()
    handles2, labels2 = ax2_right.get_legend_handles_labels()
    ax2.legend(handles1 + handles2, labels1 + labels2,
              loc='upper left', fontsize=10, ncol=2)

    # Formater x-akse (kun på nederste plot)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
    ax2.xaxis.set_major_locator(mdates.DayLocator(interval=2))
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=10)

    plt.tight_layout()

    # Lagre
    filename = f'results/plot_battery_sim_{start.strftime("%Y%m%d")}.png'
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    print(f"\n   ✓ Figur lagret: {filename}")
    plt.close()

    # Statistikk
    print("\n" + "="*60)
    print(f"STATISTIKK FOR PERIODEN ({start.date()} til {end.date()})")
    print("="*60)

    # Get production column - use AC if available
    prod_col = 'production_ac_kw' if 'production_ac_kw' in df_period.columns else 'production_kw'

    print(f"\nEnergi:")
    print(f"  Solkraftproduksjon:  {df_period[prod_col].sum():8.0f} kWh AC")
    if 'inverter_clipping_kw' in df_period.columns:
        print(f"  Inverter clipping:   {df_period['inverter_clipping_kw'].sum():8.0f} kWh")
    print(f"  Forbruk:             {df_period['consumption_kw'].sum():8.0f} kWh")
    print(f"  Batterilading:       {battery_charge.sum():8.0f} kWh")
    print(f"  Batteriutlading:     {battery_discharge.abs().sum():8.0f} kWh")
    print(f"  Nettimport:          {grid_import.sum():8.0f} kWh")
    print(f"  Netteksport:         {grid_export.abs().sum():8.0f} kWh")
    if 'curtailment_kw' in df_period.columns:
        print(f"  Curtailment:         {df_period['curtailment_kw'].sum():8.0f} kWh")

    print(f"\nEffekt:")
    print(f"  Peak solkraft:       {df_period[prod_col].max():8.1f} kW")
    print(f"  Peak forbruk:        {df_period['consumption_kw'].max():8.1f} kW")
    print(f"  Peak batterilading:  {battery_charge.max():8.1f} kW")
    print(f"  Peak batteriutl.:    {battery_discharge.abs().max():8.1f} kW")
    print(f"  Peak nettimport:     {grid_import.max():8.1f} kW")
    print(f"  Peak netteksport:    {grid_export.abs().max():8.1f} kW")

    print(f"\nBatteri:")
    print(f"  SOC start:           {df_period['battery_soc_kwh'].iloc[0]:8.1f} kWh")
    print(f"  SOC slutt:           {df_period['battery_soc_kwh'].iloc[-1]:8.1f} kWh")
    print(f"  SOC min:             {df_period['battery_soc_kwh'].min():8.1f} kWh")
    print(f"  SOC maks:            {df_period['battery_soc_kwh'].max():8.1f} kWh")

    cycles = battery_discharge.abs().sum() / 20  # 20 kWh kapasitet
    print(f"  Sykluser (periode):  {cycles:8.2f}")

    print("\n" + "="*60)
    print("FERDIG!")
    print("="*60)


if __name__ == "__main__":
    plot_battery_simulation(start_date='2020-06-01', weeks=3)
