"""
Realistiske forbruksprofiler for ulike bygningstyper
"""
import numpy as np
import pandas as pd


class ConsumptionProfile:
    """Generer realistiske forbruksprofiler"""

    @staticmethod
    def commercial_office(annual_kwh: float = 90000) -> dict:
        """
        Kontorbygg med normal arbeidstid
        Lunsj kl 11:30-12:30 gir dipp i forbruk
        """
        weekday = np.array([
            0.30, 0.30, 0.30, 0.30, 0.30, 0.35,  # 00-06: natt, litt oppvarming
            0.50, 0.70, 0.90, 1.00, 1.00, 0.95,  # 06-12: oppstart til full drift
            0.70, 0.75, 0.95, 1.00, 0.95, 0.80,  # 12-18: lunsj-dipp, så full drift
            0.60, 0.45, 0.35, 0.30, 0.30, 0.30   # 18-24: nedtrapping til natt
        ])

        weekend = np.array([
            0.25, 0.25, 0.25, 0.25, 0.25, 0.25,  # Helg: kun standby og
            0.25, 0.25, 0.25, 0.25, 0.25, 0.25,  # ventilasjon/kjøling
            0.25, 0.25, 0.25, 0.25, 0.25, 0.25,
            0.25, 0.25, 0.25, 0.25, 0.25, 0.25
        ])

        return {
            'weekday': weekday,
            'weekend': weekend,
            'annual_kwh': annual_kwh,
            'type': 'commercial_office',
            'lunch_dip': True,
            'lunch_hours': [12, 13]
        }

    @staticmethod
    def commercial_retail(annual_kwh: float = 90000) -> dict:
        """
        Butikk/handel - ingen lunsj-dipp!
        Høyt og jevnt forbruk i åpningstiden
        """
        weekday = np.array([
            0.20, 0.20, 0.20, 0.20, 0.20, 0.20,  # 00-06: natt
            0.30, 0.50, 0.80, 1.00, 1.00, 1.00,  # 06-12: åpning kl 9
            1.00, 1.00, 1.00, 1.00, 1.00, 0.90,  # 12-18: full drift
            0.70, 0.50, 0.30, 0.20, 0.20, 0.20   # 18-24: stenging
        ])

        weekend = weekday * 0.9  # Litt lavere i helg

        return {
            'weekday': weekday,
            'weekend': weekend,
            'annual_kwh': annual_kwh,
            'type': 'commercial_retail',
            'lunch_dip': False
        }

    @staticmethod
    def industrial(annual_kwh: float = 90000) -> dict:
        """
        Industri - jevnt høyt forbruk, skiftarbeid
        Liten lunsj-dipp pga overlappende skift
        """
        weekday = np.array([
            0.70, 0.70, 0.70, 0.70, 0.70, 0.75,  # 00-06: nattskift
            0.85, 0.95, 1.00, 1.00, 1.00, 0.95,  # 06-12: dagskift start
            0.90, 0.90, 1.00, 1.00, 1.00, 0.95,  # 12-18: full produksjon
            0.85, 0.80, 0.75, 0.70, 0.70, 0.70   # 18-24: kveldsskift
        ])

        weekend = weekday * 0.6  # Redusert i helg

        return {
            'weekday': weekday,
            'weekend': weekend,
            'annual_kwh': annual_kwh,
            'type': 'industrial',
            'lunch_dip': False
        }

    @staticmethod
    def generate_annual_profile(
        profile_type: str = 'commercial_office',
        annual_kwh: float = 90000,
        year: int = 2024
    ) -> pd.Series:
        """
        Generer full årsprofil med ukedag/helg-variasjon
        """
        # Velg profil
        if profile_type == 'commercial_office':
            profile = ConsumptionProfile.commercial_office(annual_kwh)
        elif profile_type == 'commercial_retail':
            profile = ConsumptionProfile.commercial_retail(annual_kwh)
        elif profile_type == 'industrial':
            profile = ConsumptionProfile.industrial(annual_kwh)
        else:
            raise ValueError(f"Ukjent profil: {profile_type}")

        # Generer tidsserie
        timestamps = pd.date_range(f'{year}-01-01', f'{year}-12-31 23:00', freq='h')

        consumption = []
        for ts in timestamps:
            hour = ts.hour
            weekday = ts.weekday()
            month = ts.month

            # Velg ukedag eller helg profil
            if weekday < 5:  # Mandag-fredag
                base = profile['weekday'][hour]
            else:  # Lørdag-søndag
                base = profile['weekend'][hour]

            # Sesongvariasjon (høyere vinter pga oppvarming)
            if month in [12, 1, 2]:
                season_factor = 1.15
            elif month in [6, 7, 8]:
                season_factor = 0.85
            else:
                season_factor = 1.0

            # Beregn forbruk
            # Skalér så årssummen blir riktig
            avg_hourly = annual_kwh / 8760
            # Gjennomsnittlig pattern-verdi bør være ~0.6
            avg_pattern = 0.6
            consumption_kw = base * season_factor * (avg_hourly / avg_pattern)

            consumption.append(consumption_kw)

        series = pd.Series(consumption, index=timestamps, name='consumption_kw')

        # Juster for å få nøyaktig årssum
        actual_sum = series.sum()
        scaling = annual_kwh / actual_sum
        series = series * scaling

        return series


if __name__ == "__main__":
    # Test profilene
    print("📊 TESTING AV FORBRUKSPROFILER\n" + "="*50)

    for profile_type in ['commercial_office', 'commercial_retail', 'industrial']:
        print(f"\n{profile_type.upper()}:")

        series = ConsumptionProfile.generate_annual_profile(
            profile_type=profile_type,
            annual_kwh=90000,
            year=2024
        )

        # Statistikk
        print(f"  Årsforbruk: {series.sum()/1000:.1f} MWh")
        print(f"  Maks effekt: {series.max():.1f} kW")
        print(f"  Min effekt: {series.min():.1f} kW")
        print(f"  Gjennomsnitt: {series.mean():.1f} kW")

        # Sjekk lunsj-dipp
        lunch_12 = series[series.index.hour == 12].mean()
        lunch_11 = series[series.index.hour == 11].mean()
        lunch_13 = series[series.index.hour == 13].mean()

        if lunch_12 < lunch_11 * 0.8:
            print(f"  Lunsj-dipp: JA (kl 12 = {lunch_12:.1f} kW vs kl 11 = {lunch_11:.1f} kW)")
        else:
            print(f"  Lunsj-dipp: NEI (jevnt forbruk middag)")

        # Helg vs ukedag
        weekday_avg = series[series.index.weekday < 5].mean()
        weekend_avg = series[series.index.weekday >= 5].mean()
        print(f"  Ukedag snitt: {weekday_avg:.1f} kW")
        print(f"  Helg snitt: {weekend_avg:.1f} kW ({weekend_avg/weekday_avg*100:.0f}% av ukedag)")