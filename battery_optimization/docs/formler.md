omplett matematisk formulering:

  1. Beslutningsvariabler (5T + 1 + N variabler)
    - Ladeeffekt, utladingseffekt, nettimport/eksport
    - Batterienergi, toppeffekt, effekttariff-trinn
  2. Objektivfunksjon
    - Energikostnad: $C_{\text{energi}} = \sum_{t=1}^{T} [c_{\text{import},t} \cdot P_{\text{grid,import},t} - c_{\text{export},t} \cdot P_{\text{grid,export},t}] \cdot \Delta t$
    - Effektkostnad: $C_{\text{effekt}} = \sum_{i=1}^{N} c_{\text{trinn},i} \cdot z_i$
  3. Bibetingelser
    - Likheter: Energibalanse, batteridynamikk, effekttariff-definisjon
    - Ulikheter: Toppeffekt-sporing, ordnet trinn-aktivering
    - Boksbetingelser: SOC-grenser (10%-90%), effektgrenser
  4. Økonomisk analyse
    - NPV-beregning
    - Break-even analyse
    - Annuitetsfaktor
  5. Eksempelkode
    - Initialisering av optimizer
    - Visualiseringsfunksjoner
    - Kjøringseksempler