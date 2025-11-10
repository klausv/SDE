# Matematisk Formulering: 24-Timers Rolling Horizon Optimeringsmodell

**Dokumentasjon for battery optimization rolling horizon optimizer**

Basert på implementasjonen i `battery_optimization/core/rolling_horizon_optimizer.py`

---

## SCQA INTRODUKSJON

**Situasjon**: Rolling horizon-optimering er en strategisk tilnærming for batteristyring hvor systemet kontinuerlig re-optimerer over en 24-timers horisont basert på spotprisprognose, solproduksjon, og forbruksmønstre.

**Komplikasjon**: Batteristyring under usikkerhet krever samtidig optimering av tre motstridende mål: minimere energikostnader (arbitrage), redusere effekttariff (peak shaving), og begrense batteridegradation (levetid). Feil balanseføring gir enten suboptimale inntekter eller akselerert batterislitasje.

**Spørsmål**: Hvordan formuleres det matematiske optimeringsproblemet som balanserer økonomisk gevinst og degradering over en 24-timers horisont med 15-minutters oppløsning?

**Svar (HOVEDBUDSKAP)**:

Et lineært program (LP) med 1067 variabler minimerer total kostnad $J = J_{\text{energy}} + J_{\text{degradation}} + J_{\text{tariff}}$ gjennom optimering av batterilading/utlading $P_{\text{charge},t}, P_{\text{discharge},t}$ over 96 timesteg ($T = 96$, $\Delta t = 0.25$ timer), underlagt energibalanse, batteridynamikk, degraderingsbetingelser (LFP dual-mode: syklisk vs kalendarisk), og progressiv effekttariff-struktur (10 Lnett brackets). Solveren (HiGHS) løser problemet på 0.5-2 sekunder og returnerer optimal kontrollaksjon $P_{\text{battery}}^{\text{setpoint}}$ for neste timestep.

---

## HOVEDBUDSKAP: DET KOMPLETTE OPTIMERINGSPROBLEMET

Minimerer total kostnad over 24-timers horisont ($T = 96$ timesteg, $\Delta t = 0.25$ timer):

$$
\boxed{
\begin{aligned}
\min_{P, E, DP, z} \quad J = &\sum_{t=0}^{T-1} \Bigg[ c_{\text{import},t} P_{\text{grid},t}^{\text{import}} \Delta t - c_{\text{export},t} P_{\text{grid},t}^{\text{export}} \Delta t \\
&\quad + c_{\text{deg}}^{\text{percent}} DP_{\text{total},t} + 0.01 P_{\text{curtail},t} \Bigg] \\
&+ \sum_{i=0}^{N_{\text{trinn}}-1} c_{\text{trinn},i} z_i - c_{\text{baseline}}^{\text{tariff}}
\end{aligned}
}
$$

Underlagt følgende betingelser:

**Energibalanse** ($T$ betingelser):
$$
P_{\text{grid},t}^{\text{import}} - P_{\text{grid},t}^{\text{export}} - P_{\text{charge},t} + P_{\text{discharge},t} - P_{\text{curtail},t} = \text{Load}_t - \text{PV}_t
$$

**Batteridynamikk** ($T$ betingelser):
$$
E_{\text{battery},t} = E_{\text{battery},t-1} + \left( \eta_{\text{charge}} P_{\text{charge},t-1} - \frac{P_{\text{discharge},t-1}}{\eta_{\text{discharge}}} \right) \Delta t, \quad E_{\text{battery},0} = E_{\text{initial}}
$$

**Degradering - Dual-Mode LFP** ($5T$ betingelser):
$$
\begin{aligned}
DP_{\text{cyc},t} &= \rho_{\text{constant}} \cdot \text{DOD}_{\text{abs},t}, \quad \text{DOD}_{\text{abs},t} = \frac{E_{\Delta,t}^{+} + E_{\Delta,t}^{-}}{E_{\text{nom}}} \\
DP_{\text{total},t} &\geq \max\left(DP_{\text{cyc},t}, dp_{\text{cal}}^{\text{timestep}}\right)
\end{aligned}
$$

**Progressiv Effekttariff** ($1 + N_{\text{trinn}}$ betingelser):
$$
P_{\text{peak}}^{\text{new}} = \sum_{i=0}^{N_{\text{trinn}}-1} p_{\text{trinn},i} z_i, \quad P_{\text{grid},t}^{\text{import}} \leq P_{\text{peak}}^{\text{new}}, \quad z_i \leq z_{i-1}
$$

**Variabelbetingelser**:
- $P_{\text{charge},t}, P_{\text{discharge},t} \in [0, P_{\text{max}}]$
- $P_{\text{grid},t}^{\text{import}}, P_{\text{grid},t}^{\text{export}} \in [0, 70 \text{ kW}]$
- $E_{\text{battery},t} \in [\text{SOC}_{\min} E_{\text{nom}}, \text{SOC}_{\max} E_{\text{nom}}]$
- $z_i \in [0, 1]$

**Fortolkning**: Dette LP-problemet med 1067 variabler og 778 betingelser balanserer tre kostnadskomponenter: energikostnad (arbitrage gjennom import/eksport-optimering), degraderingskostnad (LFP dual-mode: maksimum av syklisk og kalendarisk slitasje), og effekttariff (10 progressive Lnett brackets). Solveren HiGHS løser problemet på 0.5-2 sekunder og returnerer optimal batterikontroll for neste timestep: $P_{\text{battery}}^{\text{setpoint}} = P_{\text{charge},0} - P_{\text{discharge},0}$ [kW].

---

## ARGUMENTASJON

### Kapittel 1: Objektfunksjon - Tre Kostnadskomponenter

Objektfunksjonen minimerer total kostnad over 24-timers horisont gjennom tre komponenter:

$$
\boxed{
J = J_{\text{energy}} + J_{\text{degradation}} + J_{\text{tariff}} + J_{\text{curtailment}}
}
$$

#### 1.1 Energikostnad - Import/Eksport-Arbitrage

**Energikostnad** representerer netto kostnad for nettimport minus inntekt fra netteksport:

$$
J_{\text{energy}} = \sum_{t=0}^{T-1} \left[ c_{\text{import},t} P_{\text{grid},t}^{\text{import}} \Delta t - c_{\text{export},t} P_{\text{grid},t}^{\text{export}} \Delta t \right]
$$

**Importkostnad** består av tre komponenter:

$$
c_{\text{import},t} = p_{\text{spot},t} + c_{\text{energy},t} + c_{\text{tax},t}
$$

hvor:
- $p_{\text{spot},t}$: Nordpool spotpris [NOK/kWh]
- $c_{\text{energy},t}$: Energitariff, 0.296 NOK/kWh peak hours (Man-Fre 06:00-22:00), 0.176 NOK/kWh off-peak
- $c_{\text{tax},t} = 0.15$ NOK/kWh: Forbruksavgift

**Eksportinntekt**:

$$
c_{\text{export},t} = p_{\text{spot},t} + 0.04 \text{ NOK/kWh}
$$

Eksportpremien på 0.04 NOK/kWh kompenserer for nettariffentitet.

#### 1.2 Degraderingskostnad - Batterislitasje

**Degraderingskostnad** måler verdireduksjon av batteriet grunnet slitasje:

$$
J_{\text{degradation}} = \sum_{t=0}^{T-1} c_{\text{deg}}^{\text{percent}} DP_{\text{total},t}
$$

**Degraderingskostnad per prosentpoeng**:

$$
c_{\text{deg}}^{\text{percent}} = \frac{c_{\text{battery}} \times E_{\text{nom}}}{\text{EOL}_{\text{deg}}}
$$

Med standardverdier:
- $c_{\text{battery}} = 3054$ NOK/kWh (batterikostnad)
- $E_{\text{nom}} = 80$ kWh (batterikapasitet)
- $\text{EOL}_{\text{deg}} = 20\%$ (end-of-life degradering)

gir $c_{\text{deg}}^{\text{percent}} = (3054 \times 80) / 20 = 12{,}216$ NOK/%.

**Økonomisk tolkning**: Hvert prosentpoeng degradering koster 12,216 NOK. Ved 0.01% degradering per dag (typisk ved lav aktivitet): 122 NOK/dag degraderingskostnad. Årlig degradering ved kun kalendarisk slitasje: $0.714\% \times 12{,}216 = 8{,}722$ NOK/år.

#### 1.3 Effekttariffkostnad - Progressiv Bracket-Struktur

**Effekttariffkostnad** bruker progressiv LP-tilnærming (analog med skattemodeller):

$$
J_{\text{tariff}} = \sum_{i=0}^{N_{\text{trinn}}-1} c_{\text{trinn},i} z_i - c_{\text{baseline}}^{\text{tariff}}
$$

hvor:
- $c_{\text{trinn},i}$: Inkrementell kostnad per bracket [NOK/kWh/måned]
- $z_i \in [0, 1]$: Fyllingsnivå for bracket $i$ ($z_i = 0$: tom, $z_i = 1$: full)
- $c_{\text{baseline}}^{\text{tariff}}$: Gjeldende tariffkostnad (baseline)

Objektfunksjonen minimerer **marginal økning** i effekttariff utover baseline.

**Lnett commercial tariff-struktur** (faktisk progressiv struktur):

| Bracket $i$ | Fra [kW] | Til [kW] | Bredde $p_{\text{trinn},i}$ [kW] | Kumulativ [NOK/mnd] | Inkr. $c_{\text{trinn},i}$ [NOK/mnd] |
|-------------|----------|----------|----------------------------------|---------------------|--------------------------------------|
| 0 | 0 | 2 | 2 | 136 | 136 |
| 1 | 2 | 5 | 3 | 232 | 96 |
| 2 | 5 | 10 | 5 | 372 | 140 |
| 3 | 10 | 15 | 5 | 572 | 200 |
| 4 | 15 | 20 | 5 | 772 | 200 |
| 5 | 20 | 25 | 5 | 972 | 200 |
| 6 | 25 | 50 | 25 | 1772 | 800 |
| 7 | 50 | 75 | 25 | 2572 | 800 |
| 8 | 75 | 100 | 25 | 3372 | 800 |
| 9 | 100+ | ∞ | - | 5600 (@ 100 kW) | 2228 |

**Eksempel 1**: Ved effekttopp 12 kW:
- Bracket 0 (0-2 kW): $z_0 = 1.0$ (full), bidrar 136 NOK/måned
- Bracket 1 (2-5 kW): $z_1 = 1.0$ (full), bidrar 96 NOK/måned
- Bracket 2 (5-10 kW): $z_2 = 1.0$ (full), bidrar 140 NOK/måned
- Bracket 3 (10-15 kW): $z_3 = 0.4$ (2 kW av 5 kW), bidrar $200 \times 0.4 = 80$ NOK/måned
- **Total**: $P_{\text{peak}}^{\text{new}} = 12$ kW, kostnad $= 136 + 96 + 140 + 80 = 452$ NOK/måned

**Eksempel 2**: Ved effekttopp 75 kW:
- Brackets 0-6 (0-50 kW): Alle fulle, bidrar $136+96+140+200+200+200+800 = 1{,}772$ NOK/måned
- Bracket 7 (50-75 kW): $z_7 = 1.0$ (25 kW full), bidrar 800 NOK/måned
- **Total**: $P_{\text{peak}}^{\text{new}} = 75$ kW, kostnad $= 2{,}572$ NOK/måned (verifiserer kumulativ kolonne)

#### 1.4 Curtailment-Straff - Unngå Unødvendig Avskjæring

**Curtailment-straff** ($0.01$ NOK/kW) unngår unødvendig solkraftavskjæring:

$$
J_{\text{curtailment}} = 0.01 \sum_{t=0}^{T-1} P_{\text{curtail},t}
$$

Straffeledd sikrer at LP-solveren kun bruker curtailment når absolutt nødvendig (f.eks. batteriet fullt, netteksport maksimal). Lav straff (0.01 NOK/kW) påvirker ikke økonomisk optimering vesentlig, men gir preferanse for å unngå curtailment når alternativer finnes.

---

### Kapittel 2: Fysiske Betingelser - Energi og Batteri

#### 2.1 Energibalanse - Kirchhoffs Første Lov

For hvert timesteg $t \in \{0, 1, \ldots, T-1\}$ må energibalansen holde:

$$
\boxed{
P_{\text{grid},t}^{\text{import}} - P_{\text{grid},t}^{\text{export}} - P_{\text{charge},t} + P_{\text{discharge},t} - P_{\text{curtail},t} = \text{Load}_t - \text{PV}_t
}
$$

**Fysisk tolkning**:
- **Venstre side**: Tilgjengelig energi (nettimport - netteksport - batterilading + batteriutlading - curtailment)
- **Høyre side**: Netto last (forbruk - solproduksjon)

**Variabelroller**:
- $P_{\text{grid},t}^{\text{import}} \in [0, 70]$ kW: Import fra nett
- $P_{\text{grid},t}^{\text{export}} \in [0, 70]$ kW: Eksport til nett
- $P_{\text{charge},t} \in [0, P_{\text{max}}^{\text{charge}}]$ kW: Batterilading (typisk 60 kW)
- $P_{\text{discharge},t} \in [0, P_{\text{max}}^{\text{discharge}}]$ kW: Batteriutlading (typisk 60 kW)
- $P_{\text{curtail},t} \geq 0$ kW: Solkraftavskjæring (kun ved nødvendighet)

**Input-data**:
- $\text{PV}_t$: Solkraftproduksjon [kW] (PVGIS/PVLib)
- $\text{Load}_t$: Forbruk [kW] (målt/prognostisert)

#### 2.2 Batteridynamikk - Tilstandslikevekt

Batterienergi ved neste timesteg er lik forrige energi pluss ladeenergi (med ladetap) minus utladingsenergi (med utladingstap).

**Dynamisk likevekt** ($T-1$ betingelser) for $t \in \{1, 2, \ldots, T-1\}$:

$$
\boxed{
E_{\text{battery},t} = E_{\text{battery},t-1} + \left( \eta_{\text{charge}} P_{\text{charge},t-1} - \frac{P_{\text{discharge},t-1}}{\eta_{\text{discharge}}} \right) \Delta t
}
$$

**Initialbetingelse** (1 betingelse):

$$
\boxed{
E_{\text{battery},0} = E_{\text{initial}}
}
$$

**Parameterverdier**:
- $\eta_{\text{charge}} = \eta_{\text{discharge}} = 0.95$ (95% roundtrip efficiency per retning)
- $E_{\text{nom}} = 80$ kWh (nominell batterikapasitet)
- $\text{SOC}_{\min} = 0.1$, $\text{SOC}_{\max} = 0.9$ (operasjonelle SOC-grenser)
- $E_{\text{battery},t} \in [0.1 \times 80, 0.9 \times 80] = [8, 72]$ kWh

**Energitap-eksempel**:
- Lading: Når $P_{\text{charge},t} = 60$ kW lagres kun $0.95 \times 60 = 57$ kW i batteriet (5% tap)
- Utlading: For å levere $P_{\text{discharge},t} = 60$ kW må batteriet gi $(60 / 0.95) = 63.16$ kW (5% tap)

#### 2.3 Nettbegrensninger - Grid Limits

Nettet begrenser import og eksport til maksimal verdi:

$$
\boxed{
P_{\text{grid}}^{\text{import}} \leq 70 \text{ kW}, \quad P_{\text{grid}}^{\text{export}} \leq 70 \text{ kW}
}
$$

Grensen på 70 kW reflekterer inverterkapasitet (110 kW) × 70%-regel (norsk nettstandard for PV-anlegg). Full PV-produksjon (150 kWp) kan generere 150+ kW ved optimale forhold, men netteksport er begrenset til 70 kW. Overskuddsproduksjon må lagres i batteri eller curtails.

---

### Kapittel 3: Degraderingsmodell - LFP Dual-Mode

LFP-batterier degraderer primært av den **dominerende mekanismen** ved hvert tidspunkt: ved høy syklisk aktivitet dominerer syklisk degradering, ved lav/ingen aktivitet dominerer kalendarisk degradering.

#### 3.1 Syklisk Degradering - Aktivitetsbasert Slitasje

Syklisk degradering bruker **absolutt DOD** (Depth of Discharge) som proxy for rainflow-sykler-telling:

$$
\boxed{
DP_{\text{cyc},t} = \rho_{\text{constant}} \cdot \text{DOD}_{\text{abs},t}
}
$$

hvor:

$$
\text{DOD}_{\text{abs},t} = \frac{E_{\Delta,t}^{+} + E_{\Delta,t}^{-}}{E_{\text{nom}}}
$$

**Degraderingskonstant**:

$$
\rho_{\text{constant}} = \frac{\text{EOL}_{\text{deg}}}{\text{cycle}_{\text{life}}^{\text{full DOD}}} = \frac{20\%}{5000} = 0.004 \text{ \%/syklus}
$$

**Parameterverdier**:
- $\text{cycle}_{\text{life}}^{\text{full DOD}} = 5000$ sykluser (100% DOD, LFP standard)
- $\text{EOL}_{\text{deg}} = 20\%$ (end-of-life degradering)
- $\rho_{\text{constant}} = 0.004$ %/syklus

**Absolutt energiendring** implementeres ved LP-dekomposisjon:

**Energi-delta balanse** for $t = 0$:

$$
E_{\Delta,0}^{+} - E_{\Delta,0}^{-} - E_{\text{battery},0} = -E_{\text{initial}}
$$

For $t \in \{1, 2, \ldots, T-1\}$:

$$
E_{\Delta,t}^{+} - E_{\Delta,t}^{-} - E_{\text{battery},t} + E_{\text{battery},t-1} = 0
$$

Relasjonen $E_{\Delta,t}^{+} - E_{\Delta,t}^{-} = \Delta E_t$ dekomponeres som:
- **Lading** ($\Delta E_t > 0$): $E_{\Delta,t}^{+} = \Delta E_t$, $E_{\Delta,t}^{-} = 0$
- **Utlading** ($\Delta E_t < 0$): $E_{\Delta,t}^{+} = 0$, $E_{\Delta,t}^{-} = |\Delta E_t|$

**DOD-definisjon** ($T$ betingelser):

$$
\boxed{
\text{DOD}_{\text{abs},t} = \frac{E_{\Delta,t}^{+} + E_{\Delta,t}^{-}}{E_{\text{nom}}}
}
$$

**Ekvivalente full-sykluser over 24 timer**:

$$
\text{Cycles}_{\text{eq}}^{24h} = \sum_{t=0}^{T-1} \text{DOD}_{\text{abs},t}
$$

**Eksempel**: Ved 0.5 ekvivalente sykluser per dag (typisk ved aktiv arbitrage):
- Syklisk degradering: $0.5 \times 0.004\% = 0.002\%$ per dag
- Årlig degradering: $0.002\% \times 365 = 0.73\%$ per år
- Levetid: $20\% / 0.73\% = 27.4$ år

#### 3.2 Kalendarisk Degradering - Tidsbasert Slitasje

Kalendarisk degradering per timesteg:

$$
\boxed{
dp_{\text{cal}}^{\text{timestep}} = \frac{\text{EOL}_{\text{deg}}}{\text{cal}_{\text{life}} \times 365 \times 24} \times \Delta t
}
$$

**Parameterverdier**:
- $\text{cal}_{\text{life}} = 28$ år (kalendarisk levetid, LFP standard)
- $\text{EOL}_{\text{deg}} = 20\%$ (end-of-life degradering)
- $\Delta t = 0.25$ timer (15-minutters timesteg)

$$
dp_{\text{cal}}^{\text{timestep}} = \frac{20\%}{28 \times 365 \times 24} \times 0.25 = 0.000204 \text{ \%/timestep}
$$

**Årlig kalendarisk degradering**: $20\% / 28 \text{ år} = 0.714\%$ per år.

**Kalendarisk kostnad per dag** (ved ingen aktivitet):
- Degradering: $0.000204\% \times 96 \text{ timesteg} = 0.0196\%$ per dag
- Kostnad: $0.0196\% \times 12{,}216 \text{ NOK/\%} = 239$ NOK/dag
- Årlig: $239 \text{ NOK/dag} \times 365 = 87{,}235$ NOK/år

#### 3.3 Total Degradering - Maksimum-Funksjon

Total degradering er **maksimum** av syklisk og kalendarisk degradering ved hvert timesteg:

$$
\boxed{
DP_{\text{total},t} = \max\left(DP_{\text{cyc},t}, dp_{\text{cal}}^{\text{timestep}}\right)
}
$$

**LP-implementasjon** bruker to ulikhetsbetingelser:

**Constraint 1**: Total ≥ Syklisk ($T$ betingelser):

$$
DP_{\text{total},t} \geq DP_{\text{cyc},t}
$$

**Constraint 2**: Total ≥ Kalendarisk ($T$ betingelser):

$$
DP_{\text{total},t} \geq dp_{\text{cal}}^{\text{timestep}}
$$

LP-solveren vil automatisk sette $DP_{\text{total},t}$ til **minste verdien** som tilfredsstiller begge betingelsene, dvs. **maksimum-verdien** av de to.

**Degraderingskostnad**:

$$
C_{\text{degradation}} = \sum_{t=0}^{T-1} c_{\text{deg}}^{\text{percent}} \cdot DP_{\text{total},t}
$$

Med $c_{\text{deg}}^{\text{percent}} = 12{,}216$ NOK/%.

**Fysisk tolkning**: Ved høy aktivitet (f.eks. $\text{DOD}_{\text{abs},t} = 0.1$, dvs. 10% DOD):
- Syklisk: $DP_{\text{cyc},t} = 0.004\% \times 0.1 = 0.0004\%$ (0.04% per timestep)
- Kalendarisk: $dp_{\text{cal}}^{\text{timestep}} = 0.000204\%$
- Total: $DP_{\text{total},t} = \max(0.0004\%, 0.000204\%) = 0.0004\%$ (syklisk dominerer)

Ved ingen aktivitet ($\text{DOD}_{\text{abs},t} = 0$):
- Syklisk: $DP_{\text{cyc},t} = 0\%$
- Kalendarisk: $dp_{\text{cal}}^{\text{timestep}} = 0.000204\%$
- Total: $DP_{\text{total},t} = \max(0\%, 0.000204\%) = 0.000204\%$ (kalendarisk dominerer)

---

### Kapittel 4: Økonomisk Modell - Progressiv Effekttariff

Effekttariffen implementeres som **progressiv bracket-struktur** (analog med skattemodeller). Kontinuerlige variabler $z_i \in [0, 1]$ representerer fyllingsnivå for bracket $i$, med progressiv aktivering $z_i \leq z_{i-1}$ som sikrer at lavere brackets fylles først.

#### 4.1 Effekttopp-Definisjon

Den nye månedlige effekttoppen defineres som summen av fylte bracket-bredder:

$$
\boxed{
P_{\text{peak}}^{\text{new}} = \sum_{i=0}^{N_{\text{trinn}}-1} p_{\text{trinn},i} z_i
}
$$

**Lnett commercial tariff-struktur** (10 progressive brackets):

| Bracket $i$ | Fra [kW] | Til [kW] | Bredde $p_{\text{trinn},i}$ [kW] | Kumulativ [NOK/mnd] | Inkr. $c_{\text{trinn},i}$ [NOK/mnd] |
|-------------|----------|----------|----------------------------------|---------------------|--------------------------------------|
| 0 | 0 | 2 | 2 | 136 | 136 |
| 1 | 2 | 5 | 3 | 232 | 96 |
| 2 | 5 | 10 | 5 | 372 | 140 |
| 3 | 10 | 15 | 5 | 572 | 200 |
| 4 | 15 | 20 | 5 | 772 | 200 |
| 5 | 20 | 25 | 5 | 972 | 200 |
| 6 | 25 | 50 | 25 | 1772 | 800 |
| 7 | 50 | 75 | 25 | 2572 | 800 |
| 8 | 75 | 100 | 25 | 3372 | 800 |
| 9 | 100+ | ∞ | - | 5600 (@ 100 kW) | 2228 |

**Eksempel 1**: Effekttopp 12 kW
- Bracket 0-2: Fulle ($z_0=z_1=z_2=1.0$), bidrar 2+3+5=10 kW, kostnad 136+96+140=372 NOK
- Bracket 3: $z_3 = 0.4$ (2 av 5 kW), bidrar 2 kW, kostnad 80 NOK
- **Total**: $P_{\text{peak}}^{\text{new}} = 12$ kW, kostnad $= 452$ NOK/måned

**Eksempel 2**: Effekttopp 75 kW
- Brackets 0-6: Fulle, bidrar 50 kW, kostnad 1,772 NOK
- Bracket 7: Full ($z_7=1.0$), bidrar 25 kW, kostnad 800 NOK
- **Total**: $P_{\text{peak}}^{\text{new}} = 75$ kW, kostnad $= 2{,}572$ NOK/måned

#### 4.2 Effekttopp-Tracking

For hvert timesteg $t$ må den nye effekttoppen være minst lik nettimporten:

$$
\boxed{
P_{\text{grid},t}^{\text{import}} \leq P_{\text{peak}}^{\text{new}}
}
$$

Dette sikrer at LP-variabelen $P_{\text{peak}}^{\text{new}}$ automatisk settes til:

$$
P_{\text{peak}}^{\text{new}} = \max\left(P_{\text{peak}}^{\text{current}}, \max_{t} P_{\text{grid},t}^{\text{import}}\right)
$$

**Tolkning**: Effekttoppen er maksimum av gjeldende baseline ($P_{\text{peak}}^{\text{current}}$) og maksimal nettimport i 24-timers vinduet. LP-solveren finner automatisk optimal balanse mellom å redusere effekttopp (via batterilading/utlading) og å akseptere høyere effekttopp når kostnadene for peak shaving overstiger tariffkostnaden.

#### 4.3 Ordnet Bracket-Aktivering

For $i \in \{1, 2, \ldots, N_{\text{trinn}}-1\}$:

$$
\boxed{
z_i \leq z_{i-1}
}
$$

Høyere brackets kan kun fylles hvis lavere brackets er fylte (progressiv skattestruktur).

**Gyldig løsning**: $z_0 = 1.0$, $z_1 = 0.8$, $z_2 = 0.3$ (tilfredsstiller $1.0 \geq 0.8 \geq 0.3$)

**Ugyldig løsning**: $z_0 = 0.5$, $z_1 = 1.0$ (bryter $z_1 \leq z_0$)

#### 4.4 Progressiv Tariffkostnad

$$
\boxed{
C_{\text{tariff}}^{\text{progressive}} = \sum_{i=0}^{N_{\text{trinn}}-1} c_{\text{trinn},i} z_i
}
$$

**Hvorfor progressiv LP-tilnærming fremfor MILP?**

1. **Rask løsningstid**: LP løses på ~1 sekund vs potensielt minutter med MILP (Mixed-Integer Linear Programming)
2. **Korrekt optimeringsretning**: Progressiv tilnærming gir riktig insentiv til å redusere effekttopp
3. **Tilstrekkelig nøyaktighet**: For operational control med hyppig re-optimering (hver 15-60 min) er nøyaktighet tilstrekkelig
4. **Konservativ undervurdering**: Progressiv < steg-funksjon, men korrigeres i post-processing for rapportering
5. **Robusthet**: Rolling horizon re-optimerer kontinuerlig, så unøyaktigheter korrigeres raskt

**Objektfunksjon**: Minimerer **marginal økning** i tariffkostnad:

$$
J_{\text{tariff}} = \sum_{i=0}^{N_{\text{trinn}}-1} c_{\text{trinn},i} z_i - c_{\text{baseline}}^{\text{tariff}}
$$

hvor $c_{\text{baseline}}^{\text{tariff}} = f_{\text{tariff}}(P_{\text{peak}}^{\text{current}})$ er gjeldende tariffkostnad. Dette minimerer den **marginale økningen** i effekttariff utover baseline.

---

## BEVISFØRING (Appendices)

### Appendix A: Komplette Parametre og Variabler

#### A.1 Indekser og Tidssteg

Optimaliseringsproblemet opererer over en 24-timers horisont med $T = 96$ timesteg (15-minutters oppløsning) der $t \in \{0, 1, \ldots, 95\}$ og tidssteg-størrelse $\Delta t = 0.25$ timer.

#### A.2 Batteriparametre

| Parameter | Symbol | Verdi | Enhet |
|-----------|--------|-------|-------|
| Nominell kapasitet | $E_{\text{nom}}$ | 80 | kWh |
| Maks ladeeffekt | $P_{\text{max}}^{\text{charge}}$ | 60 | kW |
| Maks utladingseffekt | $P_{\text{max}}^{\text{discharge}}$ | 60 | kW |
| Ladevirkningsgrad | $\eta_{\text{charge}}$ | 0.95 | - |
| Utladingsvirkningsgrad | $\eta_{\text{discharge}}$ | 0.95 | - |
| Roundtrip efficiency | $\eta_{\text{charge}} \times \eta_{\text{discharge}}$ | 0.9025 | - |
| Min SOC | $\text{SOC}_{\min}$ | 0.1 | - |
| Maks SOC | $\text{SOC}_{\max}$ | 0.9 | - |

#### A.3 Nett- og Tariffparametre

| Parameter | Symbol | Verdi | Enhet |
|-----------|--------|-------|-------|
| Maks nettimport | $P_{\text{grid}}^{\text{import,max}}$ | 70 | kW |
| Maks netteksport | $P_{\text{grid}}^{\text{export,max}}$ | 70 | kW |
| Energitariff peak | $c_{\text{energy}}^{\text{peak}}$ | 0.296 | NOK/kWh |
| Energitariff off-peak | $c_{\text{energy}}^{\text{off-peak}}$ | 0.176 | NOK/kWh |
| Forbruksavgift | $c_{\text{tax}}$ | 0.15 | NOK/kWh |
| Eksportpremie | - | 0.04 | NOK/kWh |
| Antall effekttariff-brackets | $N_{\text{trinn}}$ | 10 | - |
| Bracket-bredder | $p_{\text{trinn},i}$ | 2, 3, 5, 5, 5, 5, 25, 25, 25, ∞ | kW |
| Inkrementelle kostnader | $c_{\text{trinn},i}$ | 136, 96, 140, 200, 200, 200, 800, 800, 800, 2228 | NOK/måned |

#### A.4 Degraderingsparametre (LFP-batteri)

| Parameter | Symbol | Verdi | Enhet |
|-----------|--------|-------|-------|
| Syklisk levetid (100% DOD) | $\text{cycle}_{\text{life}}^{\text{full DOD}}$ | 5000 | sykluser |
| Kalendarisk levetid | $\text{cal}_{\text{life}}$ | 28 | år |
| End-of-life degradering | $\text{EOL}_{\text{deg}}$ | 20 | % |
| Syklisk degraderingskonstant | $\rho_{\text{constant}}$ | 0.004 | %/syklus |
| Kalendarisk degradering per timestep | $dp_{\text{cal}}^{\text{timestep}}$ | 0.000204 | %/timestep |
| Batterikostnad | $c_{\text{battery}}$ | 3054 | NOK/kWh |
| Degraderingskostnad per % | $c_{\text{deg}}^{\text{percent}}$ | 12,216 | NOK/% |

#### A.5 Tilstandsavhengige Parametre

| Parameter | Symbol | Enhet | Beskrivelse |
|-----------|--------|-------|-------------|
| Initial batterienergi | $E_{\text{initial}}$ | kWh | Nåværende batterienergitilstand |
| Gjeldende effekttopp | $P_{\text{peak}}^{\text{current}}$ | kW | Månedlig effekttopp (baseline) |

#### A.6 Tidsserie-Input

| Parameter | Symbol | Enhet | Kilde |
|-----------|--------|-------|-------|
| Solkraftproduksjon | $\text{PV}_t$ | kW | PVGIS/PVLib |
| Forbruk | $\text{Load}_t$ | kW | Målt/prognostisert |
| Spotpris | $p_{\text{spot},t}$ | NOK/kWh | Nordpool |

#### A.7 Beslutningsvariabler - Fullstendig Liste

Problemet har totalt $11T + 1 + N_{\text{trinn}} = 1056 + 1 + 10 = 1067$ kontinuerlige variabler.

**Fysiske variabler** ($6T = 576$ variabler):

| Variabel | Symbol | Grenser | Enhet | Beskrivelse |
|----------|--------|---------|-------|-------------|
| Ladeeffekt | $P_{\text{charge},t}$ | $[0, 60]$ | kW | Batterilading |
| Utladingseffekt | $P_{\text{discharge},t}$ | $[0, 60]$ | kW | Batteriutlading |
| Nettimport | $P_{\text{grid},t}^{\text{import}}$ | $[0, 70]$ | kW | Import fra nett |
| Netteksport | $P_{\text{grid},t}^{\text{export}}$ | $[0, 70]$ | kW | Eksport til nett |
| Batterienergi | $E_{\text{battery},t}$ | $[8, 72]$ | kWh | Energitilstand |
| Solkraftavskjæring | $P_{\text{curtail},t}$ | $[0, \infty)$ | kW | Curtailment |

**Degraderingsvariabler** ($5T = 480$ variabler):

| Variabel | Symbol | Grenser | Enhet | Beskrivelse |
|----------|--------|---------|-------|-------------|
| Positiv energiendring | $E_{\Delta,t}^{+}$ | $[0, 80]$ | kWh | Lading (absolutt) |
| Negativ energiendring | $E_{\Delta,t}^{-}$ | $[0, 80]$ | kWh | Utlading (absolutt) |
| Absolutt DOD | $\text{DOD}_{\text{abs},t}$ | $[0, 1]$ | - | Utladingsdybde (normalisert) |
| Syklisk degradering | $DP_{\text{cyc},t}$ | $[0, 20]$ | % | Aktivitetsbasert slitasje |
| Total degradering | $DP_{\text{total},t}$ | $[0, 20]$ | % | Maksimum (syklisk, kalendarisk) |

**Effekttariff-variabler** ($1 + N_{\text{trinn}} = 11$ variabler):

| Variabel | Symbol | Grenser | Enhet | Beskrivelse |
|----------|--------|---------|-------|-------------|
| Ny effekttopp | $P_{\text{peak}}^{\text{new}}$ | $[\geq P_{\text{peak}}^{\text{current}}]$ | kW | Månedlig maksimum |
| Bracket-fyllingsnivå | $z_i$ | $[0, 1]$ | - | Fyllingsnivå for bracket $i$ |

---

### Appendix B: LP Standard Form og Implementeringsdetaljer

#### B.1 LP Standard Form

Standard LP-problemformulering:

$$
\begin{aligned}
\min_{x} \quad & c^T x \\
\text{subject to} \quad & A_{\text{eq}} x = b_{\text{eq}} \\
& A_{\text{ub}} x \leq b_{\text{ub}} \\
& l \leq x \leq u
\end{aligned}
$$

hvor:
- $x \in \mathbb{R}^{1067}$: Vektor med alle beslutningsvariabler
- $c \in \mathbb{R}^{1067}$: Objektfunksjon-koeffisienter
- $A_{\text{eq}} \in \mathbb{R}^{481 \times 1067}$: Likhetsbetingelser-matrise
- $b_{\text{eq}} \in \mathbb{R}^{481}$: Likhetsbetingelser-vektor
- $A_{\text{ub}} \in \mathbb{R}^{297 \times 1067}$: Ulikhetsbetingelser-matrise
- $b_{\text{ub}} \in \mathbb{R}^{297}$: Ulikhetsbetingelser-vektor
- $l, u \in \mathbb{R}^{1067}$: Variabelgrenser

#### B.2 Problemstørrelse

**Med $T = 96$ timesteg, $N_{\text{trinn}} = 10$ brackets**:

| Komponent | Antall | Beskrivelse |
|-----------|--------|-------------|
| **Variabler** | $11T + 1 + N_{\text{trinn}} = 1067$ | Beslutningsvariabler |
| **Equality constraints** | $5T + 1 = 481$ | Energibalanse, batteridynamikk, degradering |
| **Inequality constraints** | $3T + N_{\text{trinn}} - 1 = 297$ | Effekttopp-tracking, bracket-aktivering, maks-funksjon |

**Detaljert breakdown - Equality constraints ($5T + 1 = 481$)**:
- Energibalanse: $T = 96$ betingelser
- Batteridynamikk: $T = 96$ betingelser (inkl. initialbetingelse)
- Energi-delta balanse: $T = 96$ betingelser
- DOD-definisjon: $T = 96$ betingelser
- Syklisk degradering: $T = 96$ betingelser
- Effekttopp-definisjon: $1$ betingelse

**Detaljert breakdown - Inequality constraints ($3T + N_{\text{trinn}} - 1 = 297$)**:
- Effekttopp-tracking: $T = 96$ betingelser
- Total degradering ≥ Syklisk: $T = 96$ betingelser
- Total degradering ≥ Kalendarisk: $T = 96$ betingelser
- Ordnet bracket-aktivering: $N_{\text{trinn}} - 1 = 9$ betingelser

#### B.3 Sparse Matrix Struktur

Constraint-matrisen er **svært sparse** (~1% non-zero elementer):
- $A_{\text{eq}}$ ($481 \times 1067$): ~2000 non-zero elementer (~0.4%)
- $A_{\text{ub}}$ ($297 \times 1067$): ~310 non-zero elementer (~0.1%)

HiGHS solver utnytter denne sparsiteten effektivt gjennom sparse matrix representations og algoritmer.

#### B.4 Løsningsmetode

**Solver**: HiGHS via `scipy.optimize.linprog`

HiGHS bruker en **hybrid adaptive algorithm** som automatisk velger mellom:
1. **Simplex method**: Effektiv for små-mellomstore problemer, garanterer optimal løsning
2. **Interior-point method**: Skalerer bedre for store problemer, raskere for enkelte problemtyper
3. **Crossover**: Konverterer interior-point løsning til simplex basis for robusthet

**Ytelse**:
- Løsningstid: 0.5-2 sekunder per 24-timers optimering
- Memory usage: ~50 MB
- Re-optimering: Hver 15-60 minutt
- Horisont: 24 timer (perfekt foresight)

**Implementeringsfiler**:
- `battery_optimization/core/rolling_horizon_optimizer.py`
- `battery_optimization/configs/rolling_horizon_realtime.yaml`
- `battery_optimization/main.py`

**Design-dokumenter**:
- `OPERATIONAL_OPTIMIZATION_STRATEGY.md`
- `PEAK_PENALTY_METHODOLOGY.md`
- `COMMERCIAL_SYSTEMS_COMPARISON.md`

**Standard config**:
- 80 kWh batteri @ 60 kW
- 90.25% roundtrip efficiency
- SOC [10%, 90%]
- 5000 cycle life @ 100% DOD
- 28 år calendar life
- 20% EOL degradation
- 70 kW grid limits
- Lnett commercial tariff structure

---

### Appendix C: Output og Nøkkelmetrikker

#### C.1 Optimal Kontrollaksjon

**Optimal kontrollaksjon** (neste timestep):

$$
\boxed{
P_{\text{battery}}^{\text{setpoint}} = P_{\text{charge},0} - P_{\text{discharge},0} \quad \text{[kW]}
}
$$

**Tolkning**:
- Positiv verdi ($P_{\text{battery}}^{\text{setpoint}} > 0$): Lad batteriet
- Negativ verdi ($P_{\text{battery}}^{\text{setpoint}} < 0$): Utlad batteriet
- Null ($P_{\text{battery}}^{\text{setpoint}} = 0$): Hvilemodus (ingen aktivitet)

#### C.2 Økonomiske Nøkkeltall (24-timers aggregering)

**Energikostnad**:

$$
C_{\text{energy}}^{24h} = \sum_{t=0}^{95} \left[ c_{\text{import},t} P_{\text{grid},t}^{\text{import}} - c_{\text{export},t} P_{\text{grid},t}^{\text{export}} \right] \Delta t
$$

**Degraderingskostnad**:

$$
C_{\text{degradation}}^{24h} = \sum_{t=0}^{95} c_{\text{deg}}^{\text{percent}} DP_{\text{total},t}
$$

**Marginal tariffkostnad**:

$$
\Delta C_{\text{tariff}}^{\text{progressive}} = \sum_{i=0}^{N_{\text{trinn}}-1} c_{\text{trinn},i} z_i - c_{\text{baseline}}^{\text{tariff}}
$$

#### C.3 Degraderingsmetrikker

**Ekvivalente full-sykluser**:

$$
\boxed{
\text{Cycles}_{\text{eq}}^{24h} = \sum_{t=0}^{95} \text{DOD}_{\text{abs},t}
}
$$

**Total degradering**:

$$
DP_{\text{total}}^{24h} = \sum_{t=0}^{95} DP_{\text{total},t} \quad [\%]
$$

**Årlig degraderingsrate (ekstrapolert)**:

$$
\text{Degradation rate}_{\text{annual}} = DP_{\text{total}}^{24h} \times 365 \quad [\%/\text{år}]
$$

**Estimert levetid**:

$$
\text{Estimated lifetime} = \frac{\text{EOL}_{\text{deg}}}{\text{Degradation rate}_{\text{annual}}} \quad [\text{år}]
$$

**Eksempel-beregning**:
- Ved $DP_{\text{total}}^{24h} = 0.002\%$ per dag (typisk ved moderat aktivitet)
- Årlig degradering: $0.002\% \times 365 = 0.73\%$ per år
- Estimert levetid: $20\% / 0.73\% = 27.4$ år

---

**Dokumentasjon generert:** 2025-01-09
**Kildekode:** `battery_optimization/core/rolling_horizon_optimizer.py:1-784`
**Forfatter:** Klaus (Battery Optimization System)
