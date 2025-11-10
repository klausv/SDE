# Plotly Legend Placement Guide - Norsk Solkraft

## ✅ Standard (oppdatert)

**Norsk Solkraft themes har nå legend MELLOM tittel og graf som standard!**

```python
from src.visualization.norsk_solkraft_theme import apply_dark_theme

apply_dark_theme()  # Legend er nå automatisk mellom tittel og graf!
fig = go.Figure(...)
fig.show()
```

---

## 🎯 Alle Legend-plasseringer

### **1. TOPP (mellom tittel og graf) - STANDARD** ⭐

```python
fig.update_layout(
    title=dict(
        text='Din Tittel',
        y=0.98,              # Tittel øverst
        x=0.5,
        xanchor='center',
        yanchor='top'
    ),

    legend=dict(
        orientation="h",     # Horisontal
        yanchor="bottom",
        y=1.0,               # Over graf-området
        xanchor="center",
        x=0.5
    ),

    margin=dict(t=120, b=60, l=60, r=40)  # Økt top margin!
)
```

**Når bruke:**
- ✅ Standard for alle Norsk Solkraft rapporter
- ✅ Profesjonelt og ryddig
- ✅ Ikke overlapper med data
- ✅ Fungerer best med 3-7 serier

---

### **2. BUNN (under graf)**

```python
fig.update_layout(
    legend=dict(
        orientation="h",     # Horisontal
        yanchor="top",
        y=-0.15,             # UNDER grafen (negativ!)
        xanchor="center",
        x=0.5
    ),

    margin=dict(t=80, b=100, l=60, r=40)  # Økt bottom margin!
)
```

**Når bruke:**
- 📊 Når du har lang tittel/subtitle
- 📊 Mange serier (>7)
- 📊 Figuren er veldig høy

---

### **3. HØYRE SIDE (innenfor graf)**

```python
fig.update_layout(
    legend=dict(
        orientation="v",     # Vertikal
        yanchor="top",
        y=0.99,              # Innenfor graf-området
        xanchor="right",
        x=0.99
    ),

    margin=dict(t=80, b=60, l=60, r=40)
)
```

**Når bruke:**
- 📈 Få serier (2-3)
- 📈 Mye tom plass på høyre side
- 📈 Klassisk look

---

### **4. VENSTRE SIDE (innenfor graf)**

```python
fig.update_layout(
    legend=dict(
        orientation="v",
        yanchor="top",
        y=0.99,
        xanchor="left",
        x=0.01               # Venstre hjørne
    )
)
```

**Når bruke:**
- Mye tom plass på venstre side
- Spesielle layout-behov

---

### **5. INGEN LEGEND**

```python
fig.update_layout(showlegend=False)
```

**Når bruke:**
- Kun én serie
- Forklaring i tittel/tekst
- Annotations brukes i stedet

---

## 🎨 Legend Styling

### **Bakgrunn og border:**

```python
legend=dict(
    bgcolor='rgba(33,33,33,0.95)',    # Semi-transparent
    bordercolor='#8A8A8A',            # Grå border
    borderwidth=1
)
```

### **Font:**

```python
legend=dict(
    font=dict(
        size=11,
        color='white',
        family='Arial, Helvetica, sans-serif'
    )
)
```

### **Gruppering (for mange serier):**

```python
fig.update_layout(
    legend=dict(
        tracegroupgap=10      # Avstand mellom grupper
    )
)

# I traces:
fig.add_trace(go.Scatter(..., legendgroup='group1', legendgrouptitle_text='Gruppe 1'))
```

---

## 📏 Fine-tuning

### **Justere avstand:**

```python
# Topp: Øk y for mer plass fra graf
legend=dict(y=1.05)  # Mer plass

# Bunn: Gjør y mer negativ
legend=dict(y=-0.25)  # Lengre ned

# Høyre: Flytt utenfor graf
legend=dict(x=1.02)   # Utenfor høyre kant
```

### **Kompakt layout (mange serier):**

```python
legend=dict(
    orientation="h",
    yanchor="bottom",
    y=-0.2,
    xanchor="center",
    x=0.5,

    # Kompakt styling
    itemsizing='constant',   # Konstant størrelse på symbols
    font=dict(size=10),      # Mindre font
    tracegroupgap=5          # Mindre gap
)
```

---

## 🔧 Troubleshooting

### **Problem: Legend kutter av grafen**
```python
# Løsning: Øk margin
margin=dict(t=140)  # For topp-legend
margin=dict(b=120)  # For bunn-legend
```

### **Problem: Legend overlapper med tittel**
```python
# Løsning: Flytt tittel høyere
title=dict(y=0.99)
```

### **Problem: Legend for bred (horisontal)**
```python
# Løsning 1: Kortere navn
fig.add_trace(go.Scatter(..., name='Sol'))  # Ikke "Solproduksjon (kW)"

# Løsning 2: To linjer
legend=dict(orientation="v")  # Vertikal i stedet
```

### **Problem: Legend skjuler viktige data**
```python
# Løsning: Flytt legend til topp eller bunn (utenfor)
legend=dict(y=1.0)  # Topp (anbefalt!)
```

---

## 📚 Eksempler

Se demo-filer for live eksempler:
- `demo_norsk_solkraft_dark.html` - Dark theme med topp-legend
- `demo_norsk_solkraft_light.html` - Light theme med topp-legend
- `legend_top.html` - Kun topp-plassering
- `legend_bottom.html` - Kun bunn-plassering
- `legend_right.html` - Kun høyre-plassering
- `legend_comparison.html` - Alle tre side-by-side

---

## 🎯 Anbefaling

**For Norsk Solkraft rapporter:**

1. **Standard**: Topp (mellom tittel og graf) - automatisk i themes! ⭐
2. **Alternativ**: Bunn (hvis mange serier eller lang tittel)
3. **Unngå**: Høyre side (tar plass fra grafen)

**Tips:**
- Hold serie-navn korte (under 20 tegn)
- Maks 7 serier for horisontal legend
- Bruk `tracegroupgap` for mange serier
- Test i både dark og light theme

---

**Sist oppdatert**: 2025-11-09
**Norsk Solkraft theme version**: 2.0 (med topp-legend som standard)
