# VRU Trainer

An interactive Streamlit teaching tool for Flogistix-pattern rotary screw
**Vapor Recovery Units (VRUs)**. It models the physics, thermodynamics, and
control logic of a real field VRU skid — flash gas, working/breathing losses,
compressor sizing, discharge cooling, and PVRV venting — and pairs it with a
live, clickable 3D view of the equipment.

No AI/ML is involved anywhere in the app. Every number on screen comes from
deterministic engineering calculations (Peng-Robinson equation of state,
Rachford-Rice flash, Wilson K-values, AP-42 breathing-loss correlations,
etc.), with an ideal-gas mode available for comparison.

## Files

| File | Purpose |
|---|---|
| `vru_app.py` | Main Streamlit application — all pages, physics, and UI |
| `vru_3d_component.html` | Self-contained Three.js 3D scene, embedded into the app as a Streamlit HTML component |
| `three_min.js` | Vendored copy of the Three.js r128 library (the same build is already bundled inline inside `vru_3d_component.html`, so this file is a reference/standalone copy rather than a separate runtime dependency) |

## Running it

```bash
pip install streamlit
streamlit run vru_app.py
```

`vru_app.py` loads `vru_3d_component.html` from its own directory at
runtime, so keep the two files together.

## App pages

- **🏗️ 3D View** — Live Three.js render of the VRU skid (rotary screw
  compressor, tanks, discharge cooler, flare/vent) with orbit/pan/zoom,
  click-to-inspect equipment tags, cutaway mode, and animated flow
  particles synced to the live process state.
- **🏠 Dashboard** — At-a-glance readouts: gas generation, capture rate,
  venting, BHP load, discharge temperature, alarms.
- **🎛️ Simulator** — Guided and Expert modes for adjusting process inputs
  and watching the whole system respond.
- **🎛️ Control System** — PLC/PID-style control loop view.
- **📐 Equations** — Every formula used in the model, with live numeric
  substitution.
- **📚 Guided Lessons** — Step-by-step teaching modules from zero
  knowledge to VRU fluency, with quizzes.
- **📖 Glossary** — Plain-English explanations (with analogies) for every
  term and readout in the app.
- **⚖️ Compare Models** — Side-by-side specs and trade-offs across the
  Flogistix VRU lineup (VRX7, VRX15, VRX25, FX10V75 … FX20G).

## Physics notes

- Both an **ideal-gas** path and a **rigorous Peng-Robinson EOS** path are
  implemented, with a toggle to compare them and see where the ideal-gas
  assumption breaks down.
- Field units throughout (psia, °F/°R, MSCFD, bbl/d) to match how the
  equipment is actually specified and operated.
- Every variable in every formula is exposed as an adjustable input, with
  the effect immediately visible in the readouts and the 3D scene.

## Purpose

Built as a self-onboarding tool to learn VRU physics, combustion, and
thermodynamics from the ground up while staying accurate to the specific
VRU family used in the field.
