# VRU Trainer

Interactive teaching simulator for rotary-screw Vapor Recovery Units (VRUs), built to model Flogistix-pattern equipment. Combines a Streamlit dashboard with a Three.js 3D plant view, and exposes every underlying physics/thermo formula as an adjustable parameter.

Physics engine: Peng-Robinson EOS, Rachford-Rice flash, Wilson K-values. No AI/ML — purely deterministic field-unit calculations.

## Features

- **Dashboard** — live operating point: capture rate, vent losses, BHP, discharge temperature, CO2e
- **Simulator** — sliders for every input parameter (tank pressure, load, compressor model, slide valve, etc.) with immediate recalculation
- **How the Math Works** — full formula reference with unit derivations
- **Guided Lessons** — step-by-step onboarding to VRU physics and combustion/thermo fundamentals
- **Glossary** — searchable term reference
- **3D Plant View** — interactive Three.js scene (orbit/pan/zoom, clickable equipment tags, live state pushed from the simulator) with a real-EOS/ideal-gas toggle

## Project structure

```
vru-trainer/
├── vru_app.py               # Streamlit app — all pages, sidebar, and the solve() physics engine
├── vru_3d_component.html    # Self-contained Three.js 3D viewer, embedded via components.html
├── requirements.txt         # Python dependencies
└── docs/
    └── audit-notes.md       # Formula audit log — units checked, two open fixes flagged
```

`vru_app.py` loads `vru_3d_component.html` from its own directory at runtime (`streamlit.components.v1.components.html`), so the two files must stay side by side — don't move one without the other.

## Setup

```bash
git clone <this-repo-url>
cd vru-trainer
pip install -r requirements.txt
streamlit run vru_app.py
```

The app opens at `http://localhost:8501`.

## Known issues

See `docs/audit-notes.md` for the full formula-by-formula audit. Two real fixes are flagged and still open:

1. **Dead variable** (`vru_app.py` line 403) — `vi_eff = P_param = p["Vi"]` assigns an unused `P_param`. Cosmetic; safe to drop.
2. **Slide valve not modeled in Python** (`vru_app.py` line 403) — the Python solver always uses the full `Vi` (equivalent to slide = 100%), while the JS 3D component correctly scales `viEff` by slide position. If a `slide` parameter is ever added to the Python sidebar, apply:
   ```python
   vi_eff = 1 + (p["Vi"] - 1) * (slide / 100.0)
   ```

All six focus-area formulas (discharge temp, NTU, qWork, breathing loss, fuel MSCFD, CO2e) were audited and confirmed unit-correct in both the Python and JS implementations.
