#!/usr/bin/env python
"""
Hent EKTE spotpriser fra ENTSO-E eller Nord Pool
INGEN generering av falske data!
"""
import os
import pandas as pd
import requests
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET


def fetch_entsoe_prices(year: int, area: str = 'NO2', api_key: str = None):
    """
    Hent EKTE priser fra ENTSO-E Transparency Platform

    Krever API key fra: https://transparency.entsoe.eu/
    """
    if not api_key:
        api_key = os.getenv('ENTSOE_API_KEY')

    if not api_key:
        raise ValueError("ENTSOE_API_KEY må settes!")

    # ENTSO-E domain codes
    domains = {
        'NO1': '10YNO-1--------2',
        'NO2': '10YNO-2--------T',
        'NO3': '10YNO-3--------J',
        'NO4': '10YNO-4--------9',
        'NO5': '10Y1001A1001A48H'
    }

    domain = domains.get(area, '10YNO-2--------T')

    # API endpoint
    url = 'https://web-api.tp.entsoe.eu/api'

    # Fetch data month by month (API limit)
    all_prices = []

    for month in range(1, 13):
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)

        params = {
            'securityToken': api_key,
            'documentType': 'A44',  # Day-ahead prices
            'in_Domain': domain,
            'out_Domain': domain,
            'periodStart': start_date.strftime('%Y%m%d%H%M'),
            'periodEnd': (end_date - timedelta(hours=1)).strftime('%Y%m%d%H%M')
        }

        print(f"Henter {area} priser for {start_date.strftime('%B %Y')}...")

        response = requests.get(url, params=params)

        if response.status_code != 200:
            print(f"Feil: {response.status_code} - {response.text[:200]}")
            continue

        # Parse XML response
        root = ET.fromstring(response.content)

        # Extract time series
        ns = {'ns': 'urn:iec62325.351:tc57wg16:451-3:publicationdocument:7:3'}

        for ts in root.findall('.//ns:TimeSeries', ns):
            period = ts.find('.//ns:Period', ns)
            if period is None:
                continue

            start = period.find('ns:timeInterval/ns:start', ns).text
            resolution = period.find('ns:resolution', ns).text

            # Parse start time
            start_time = pd.Timestamp(start[:-1], tz='UTC')

            # Get points
            points = period.findall('ns:Point', ns)

            for point in points:
                position = int(point.find('ns:position', ns).text)
                price = float(point.find('ns:price.amount', ns).text)

                # Calculate timestamp (position is 1-indexed)
                timestamp = start_time + pd.Timedelta(hours=position-1)

                # Convert EUR/MWh to NOK/kWh
                price_nok = price * 11.5 / 1000  # 11.5 NOK/EUR, divide by 1000 for kWh

                all_prices.append({
                    'timestamp': timestamp.tz_convert('Europe/Oslo'),
                    'price_nok': price_nok
                })

    # Create DataFrame
    df = pd.DataFrame(all_prices)
    df.set_index('timestamp', inplace=True)
    df = df.sort_index()

    # Remove duplicates
    df = df[~df.index.duplicated(keep='first')]

    # Resample to ensure hourly data
    df = df.resample('h').mean().interpolate()

    return df['price_nok']


def fetch_nordpool_prices(year: int, area: str = 'NO2'):
    """
    Alternativ: Hent fra Nord Pool API
    """
    # Nord Pool har begrenset gratis API
    # Kan bruke nordpool-library: pip install nordpool
    try:
        from nordpool import elspot
        prices = elspot.Prices()
        hourly = prices.hourly(end_date=f"{year}-12-31", areas=[area])

        # Convert to pandas Series
        timestamps = []
        values = []
        for item in hourly['areas'][area]['values']:
            timestamps.append(pd.Timestamp(item['start']))
            values.append(item['value'] / 1000)  # Convert to NOK/kWh

        return pd.Series(values, index=timestamps, name='price_nok')
    except ImportError:
        print("nordpool bibliotek ikke installert")
        return None


def download_historical_prices(year: int, area: str = 'NO2'):
    """
    Last ned historiske priser fra tilgjengelige kilder
    """
    cache_file = f"data/spot_prices/REAL_{area}_{year}.csv"

    if os.path.exists(cache_file):
        print(f"📁 Bruker cached EKTE priser: {cache_file}")
        df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
        return df['price_nok']

    print(f"📡 Henter EKTE historiske priser for {area} {year}...")

    # Try ENTSO-E first
    api_key = os.getenv('ENTSOE_API_KEY')
    if api_key:
        try:
            prices = fetch_entsoe_prices(year, area, api_key)
            os.makedirs(os.path.dirname(cache_file), exist_ok=True)
            prices.to_frame().to_csv(cache_file)
            print(f"💾 Lagret EKTE priser til {cache_file}")
            return prices
        except Exception as e:
            print(f"ENTSO-E feil: {e}")

    # Try Nord Pool
    prices = fetch_nordpool_prices(year, area)
    if prices is not None:
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        prices.to_frame().to_csv(cache_file)
        print(f"💾 Lagret EKTE priser til {cache_file}")
        return prices

    # Last resort: Use pre-downloaded data if available
    backup_file = f"data/historical_prices/{area}_{year}.csv"
    if os.path.exists(backup_file):
        print(f"📁 Bruker historiske priser fra backup: {backup_file}")
        df = pd.read_csv(backup_file, index_col=0, parse_dates=True)
        return df['price_nok']

    raise ValueError(f"Kan ikke hente EKTE priser for {area} {year}. Sett ENTSOE_API_KEY!")


if __name__ == "__main__":
    # Test
    try:
        prices = download_historical_prices(2023, 'NO2')
        print(f"\n📊 EKTE prisstatistikk:")
        print(f"  Gjennomsnitt: {prices.mean():.3f} NOK/kWh")
        print(f"  Min: {prices.min():.3f} NOK/kWh")
        print(f"  Max: {prices.max():.3f} NOK/kWh")
        print(f"  Median: {prices.median():.3f} NOK/kWh")
    except Exception as e:
        print(f"❌ Feil: {e}")