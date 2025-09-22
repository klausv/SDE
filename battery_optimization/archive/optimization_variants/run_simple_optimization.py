#!/usr/bin/env python
"""
ENKEL MEN GRUNDIG OPTIMERING - Kjør over natten
Bruker eksisterende fungerende kode med høye iterasjoner
"""
import subprocess
import time
import pandas as pd

print("="*80)
print("🌙 STARTER NATTOPTIMERING - FLERE KJØRINGER")
print("="*80)
print(f"Start: {pd.Timestamp.now()}")
print("Kjører optimering for ulike batterikostnader...")
print("-"*80)

# Ulike batterikostnader å teste
battery_costs = [2000, 2500, 3000, 3500, 4000, 4500, 5000, 5500, 6000, 6500, 7000]

results = []
for cost in battery_costs:
    print(f"\n🔋 Kjører optimering for {cost} NOK/kWh...")

    cmd = [
        "python", "run_analysis.py",
        "--optimize",
        "--battery-cost", str(cost),
        "--format", "summary"
    ]

    try:
        start = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        elapsed = time.time() - start

        if result.returncode == 0:
            print(f"✅ Ferdig på {elapsed:.1f} sekunder")
            # Parse output to get key metrics
            output = result.stdout

            # Extract NPV if present
            if "NPV:" in output:
                npv_line = [l for l in output.split('\n') if 'NPV:' in l][0]
                npv = float(npv_line.split(':')[1].strip().replace(',', '').replace(' NOK', ''))
            else:
                npv = 0

            results.append({
                'battery_cost': cost,
                'npv': npv,
                'time': elapsed,
                'output': output[:1000]  # First 1000 chars
            })
        else:
            print(f"❌ Feilet: {result.stderr[:200]}")

    except subprocess.TimeoutExpired:
        print(f"⏰ Timeout etter 10 minutter")
    except Exception as e:
        print(f"❌ Feil: {str(e)}")

# Lagre resultater
if results:
    df = pd.DataFrame(results)
    df.to_csv('results/simple_optimization_results.csv', index=False)

    print("\n" + "="*80)
    print("📊 RESULTATER:")
    print("-"*80)
    print(df[['battery_cost', 'npv', 'time']].to_string(index=False))

    print("\n💾 Resultater lagret til: results/simple_optimization_results.csv")

print(f"\n✅ Ferdig: {pd.Timestamp.now()}")
print("="*80)