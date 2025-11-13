#!/usr/bin/env python3
"""
Lag konfigurasjonstabell for Snødevegen-prosjektet.
"""

import pandas as pd
from pathlib import Path

# Output directory
output_dir = Path('results/battery_dimensioning_PT60M')
output_dir.mkdir(parents=True, exist_ok=True)

# Create configuration table
data = {
    'Parameter': [
        'Installert solcelleffekt',
        'Inverterstørrelse',
        'Nettkapasitet (begrensning)',
        'Årlig forbruk',
        'Forbruksmodell',
        'Kraftpris (referanse)',
        'Nettariff',
        'Diskonteringsrente',
        'Analyseperiode',
        'Batterieffektivitet'
    ],
    'Verdi': [
        '150 kWp',
        '110 kW',
        '70 kW',
        '70 MWh/år',
        'Kommersiell profil',
        'NO2 2024 (ENTSO-E)',
        'Lnett bedrift (5 trinn)',
        '5%',
        '15 år',
        '90%'
    ],
    'Detaljer': [
        'Sør-orientert, 25° helning, Stavanger',
        'Oversizingsforhold 1.36 (150/110)',
        'Nettselskapets begrensning (ikke batteriavhengig)',
        'Typisk kommersiell bedrift',
        'Peak 06-22 ukedager, off-peak netter/helg',
        'Timespriser fra Nordpool spot NO2',
        'Progressiv struktur 48-213 NOK/kW/mnd',
        'Reell avkastningskrav for investeringsanalyse',
        'Antatt batteriets levetid',
        'Round-trip effektivitet (lade/utlade)'
    ]
}

df = pd.DataFrame(data)

# Save as CSV
csv_file = output_dir / 'snødevegen_konfigurasjon.csv'
df.to_csv(csv_file, index=False, encoding='utf-8-sig')
print(f"✓ Lagret CSV: {csv_file}")

# Save as formatted text table
txt_file = output_dir / 'snødevegen_konfigurasjon.txt'
with open(txt_file, 'w', encoding='utf-8') as f:
    f.write("=" * 100 + "\n")
    f.write("SYSTEMKONFIGURASJON - SNØDEVEGEN 122 BATTERIDIMENSJONERING\n")
    f.write("=" * 100 + "\n\n")
    f.write(df.to_string(index=False))
    f.write("\n\n")
    f.write("=" * 100 + "\n")
    f.write("NETTARIFF STRUKTUR - LNETT BEDRIFT\n")
    f.write("=" * 100 + "\n\n")

    tariff_data = {
        'Trinn': [1, 2, 3, 4, 5],
        'Effektgrense': ['0-50 kW', '50-100 kW', '100-200 kW', '200-300 kW', '>300 kW'],
        'Pris (NOK/kW/mnd)': [48, 52, 63, 121, 213]
    }
    df_tariff = pd.DataFrame(tariff_data)
    f.write(df_tariff.to_string(index=False))
    f.write("\n\n")
    f.write("Beregning: Progressiv struktur der kun effekt over hver grense\n")
    f.write("           betaler høyere pris (ikke hele effekten).\n")
    f.write("=" * 100 + "\n")

print(f"✓ Lagret TXT: {txt_file}")

# Print to console
print("\n" + "=" * 100)
print("SYSTEMKONFIGURASJON - SNØDEVEGEN 122 BATTERIDIMENSJONERING")
print("=" * 100 + "\n")
print(df.to_string(index=False))
print("\n" + "=" * 100)
print("NETTARIFF STRUKTUR - LNETT BEDRIFT")
print("=" * 100 + "\n")
df_tariff = pd.DataFrame({
    'Trinn': [1, 2, 3, 4, 5],
    'Effektgrense': ['0-50 kW', '50-100 kW', '100-200 kW', '200-300 kW', '>300 kW'],
    'Pris (NOK/kW/mnd)': [48, 52, 63, 121, 213]
})
print(df_tariff.to_string(index=False))
print("\nBeregning: Progressiv struktur der kun effekt over hver grense")
print("           betaler høyere pris (ikke hele effekten).")
print("=" * 100)
