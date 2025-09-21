#!/usr/bin/env python
"""
Oppdater metadata for eksisterende cache-filer
"""
import json
from pathlib import Path
from datetime import datetime
import os

# Cache directory
cache_dir = Path("data/spot_prices")
metadata_file = cache_dir / "cache_metadata.json"

# Create metadata for existing files
metadata = {}

# Check existing cache files
for file in cache_dir.glob("*.csv"):
    # Get file stats
    stats = os.stat(file)
    modified_time = datetime.fromtimestamp(stats.st_mtime)

    # Parse filename
    parts = file.stem.replace("_real", "").split("_")

    if file.stem == "NO2_2024_real":
        metadata["NO2_2024"] = {
            "area": "NO2",
            "year": 2024,
            "source": "generated",
            "fetched_date": modified_time.strftime('%Y-%m-%d %H:%M:%S'),
            "note": "Generert basert på kjente 2024 månedspriser med intradag-variasjon"
        }
    elif file.stem == "spot_NO2_2023":
        metadata["NO2_2023"] = {
            "area": "NO2",
            "year": 2023,
            "source": "generated",
            "fetched_date": modified_time.strftime('%Y-%m-%d %H:%M:%S'),
            "note": "Simulert basert på NO2 mønstre"
        }

# Save metadata
with open(metadata_file, 'w') as f:
    json.dump(metadata, f, indent=2)

print(f"✅ Metadata oppdatert for {len(metadata)} cache-filer")
print(f"   Lagret til: {metadata_file}")

# Show content
print("\n📋 Metadata innhold:")
for key, value in metadata.items():
    print(f"   • {key}:")
    print(f"     - Hentet: {value['fetched_date']}")
    print(f"     - Kilde: {value['source']}")
    print(f"     - Note: {value['note']}")