BATTERIDIMENSJONERING - VISUALISERINGSPLOTT

Plottoversikt:
=============

1. npv_heatmap.png
   - Varmekart som viser NPV for alle batterikonfigurasjoner
   - Akser: Batterikapasitet (kWh) vs Batterieffekt (kW)
   - Fargekode: Grønn = bedre, rød = verre

2. savings_vs_capex.png
   - Årlige besparelser vs investeringskostnad
   - Rød linje viser break-even punkt (NPV=0)
   - Punkter over linjen ville vært lønnsomme

3. npv_by_size.png
   - NPV som funksjon av batteristørrelse
   - Separate linjer for hver batterieffekt
   - Viser hvordan NPV avtar med økende størrelse

4. payback_period_heatmap.png
   - Tilbakebetalingstid for alle konfigurasjoner
   - Referanse: Prosjektlevetid er 15 år
   - Grønn = rask tilbakebetaling, rød = lang

5. breakeven_cost.png
   - Break-even batterikostnad for å oppnå lønnsomhet
   - Sammenligning med dagens markedspris (5000 NOK/kWh)
   - Viser hvor mye prisen må falle for lønnsomhet

6. top10_comparison.png
   - Detaljert sammenligning av de 10 beste konfigurasjonene
   - Fire subplot: NPV, besparelser, CAPEX, tilbakebetalingstid

Alle plott er generert med høy oppløsning (300 DPI) for rapportbruk.
