# TODO: Økonomisk modell og simuleringer

## Neste steg

Husk at jeg må lage økonomisk funksjon C(t) og kanskje en klasse.

Må formulere maxeffekt inneværende måned som en tilstandsvariabel som bringes med i neste tidsskritt.

Det kan føre til at vi bør ha månedlig tidshorisont i simuleringene, men det vil være urealistisk men teoretisk upper bound.

Lag plott med simuleringer nå som bi-directional inverter er på plass, og simuler casene:
- 0: Ingen batteri (referanse)
- Heuristisk 1: SimpleRuleStrategy
- Heuristisk 2: TBD (peak shaving? curtailment reduction?)

Før jeg går i gang med LP-modellen.

## Åpne spørsmål

1. Hva skal Heuristisk 2 strategi gjøre?
   - Peak shaving fokus?
   - Curtailment reduksjon?
   - Kombinert?

2. LP-modell horisont?
   - Månedlig (realistisk)?
   - Årlig (teoretisk upper bound)?
   - Begge?

3. Inkluder batterikostnader (investering + degradering) i økonomisk modell nå?
