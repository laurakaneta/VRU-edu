"""
VRU Trainer — Streamlit Web App
Flogistix-pattern rotary screw vapor recovery unit interactive teaching simulator.
Physics: Peng-Robinson EOS, Rachford-Rice flash, Wilson K-values.
No AI/ML — purely deterministic field-unit calculations.
"""

import math
import streamlit as st

# ─────────────────────────────────────────────────────────────────────────────
# Page config (must be first Streamlit call)
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="VRU Trainer",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# Global CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* metric cards */
[data-testid="metric-container"] {
    background: #1B2530;
    border: 1px solid #2E3B49;
    border-radius: 8px;
    padding: 0.6rem 0.8rem;
}
/* alarm banners */
.alarm-red  { background:#3A140A; border-left:4px solid #E4572E;
              color:#F5B9A6; padding:8px 12px; border-radius:4px; margin-bottom:6px; font-size:0.85rem; }
.alarm-warn { background:#3A2A0E; border-left:4px solid #F0A227;
              color:#F2CE8C; padding:8px 12px; border-radius:4px; margin-bottom:6px; font-size:0.85rem; }
.alarm-ok   { background:#0E2B14; border-left:4px solid #6FBF73;
              color:#A8D8A8; padding:8px 12px; border-radius:4px; margin-bottom:6px; font-size:0.85rem; }
/* section headers */
.sec-header { font-size:0.75rem; letter-spacing:0.14em; text-transform:uppercase;
              color:#F0A227; font-weight:600; margin-bottom:4px; }
/* readout rows */
.rrow { display:flex; justify-content:space-between; border-bottom:1px solid #1B2530;
        padding:3px 0; font-size:0.82rem; }
.rrow .lbl { color:#8A9AA8; }
.rrow .val { color:#E6EDF3; font-family:monospace; }
.rrow .hot { color:#E4572E; font-family:monospace; font-weight:600; }
.rrow .good{ color:#6FBF73; font-family:monospace; }
.rrow .amb { color:#F0A227; font-family:monospace; }
/* formula box */
.formula-box { background:#0E1822; border:1px solid #2E3B49; border-left:3px solid #4FD1C5;
               border-radius:4px; padding:10px 14px; font-family:monospace;
               font-size:0.82rem; color:#E6EDF3; margin:6px 0; white-space:pre-wrap; }
.numbox      { background:#0E1822; border:1px solid #2E3B49; border-left:3px solid #F0A227;
               border-radius:4px; padding:8px 12px; font-family:monospace;
               font-size:0.82rem; color:#F0A227; margin:4px 0; }
/* lesson card */
.lesson-card { background:#1B2530; border:1px solid #2E3B49; border-left:3px solid #F0A227;
               border-radius:6px; padding:12px 16px; margin-bottom:8px; }
.lesson-card h4 { color:#E6EDF3; font-size:0.95rem; margin:0 0 4px; }
.lesson-card p  { color:#8A9AA8; font-size:0.82rem; margin:0; }
/* glossary */
.gterm  { color:#F0A227; font-family:monospace; font-size:0.82rem; font-weight:600; }
.gplain { color:#E6EDF3; font-size:0.88rem; margin:4px 0; }
.ganalogy { color:#63727F; font-size:0.82rem; font-style:italic; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Physical constants (field units)
# ─────────────────────────────────────────────────────────────────────────────
R_FT3   = 10.7316   # psia·ft³/(lbmol·°R)
R_BTU   = 1.98588   # Btu/(lbmol·°R)
R_FTLBF = 1545.35   # ft·lbf/(lbmol·°R)
MOLVOL  = 379.48    # scf/lbmol @ 14.696 psia, 60 °F
MW_AIR  = 28.9625
PSTD    = 14.696    # psia
TSTD    = 519.67    # 60 °F in °R
OZ      = 16.0      # oz/in² per psi
SQ2     = math.sqrt(2)

def F2R(f): return f + 459.67
def R2F(r): return r - 459.67

# ─────────────────────────────────────────────────────────────────────────────
# Plain-English explanations for every output key shown in the UI
# ─────────────────────────────────────────────────────────────────────────────
READOUT_HELP = {
    # Vapour source
    "qFlash":   "Flash gas (MSCFD) — gas released the instant oil drops from high separator pressure to low tank pressure. Usually the dominant vapour source and the first knob to turn when a VRU is overloaded.",
    "qWork":    "Working loss (MSCFD) — gas displaced by incoming oil filling the tank. Every barrel entering pushes out an equal volume of saturated vapour. Only tank management reduces this.",
    "qBreath":  "Breathing loss (MSCFD) — gas vented as the vapour space expands in daytime heat and contracts at night. Bigger tanks and wider temperature swings make this worse.",
    "qBlank":   "Blanket / leak-in gas (MSCFD) — gas deliberately injected to keep air out, plus any gas-lift leak-in. Adds directly to compressor load.",
    "qGen":     "Total gas generated (MSCFD) — sum of all four sources above. This is what the VRU must capture every minute to keep the tank below the PVRV setting.",
    "tvp":      "True Vapour Pressure (psia) — the bubble-point pressure of the stock-tank liquid at current temperature. High TVP means more flash gas and working loss.",
    "stbbl":    "Stock-tank barrels per day (bbl/d) — oil flowing into the tanks after the separator and VRT. Sets the working-loss rate.",
    "zVap":     "Z-factor of tank vapour — real-gas correction at tank conditions. Near 1.0 at low tank pressure; deviates slightly for heavy vapours.",
    "vSpace":   "Vapour space volume (ft³) — total head space above the liquid in all tanks. Larger vapour space means slower pressure swings, which is good for control stability.",
    "kE":       "K_E breathing coefficient — proportional to the diurnal temperature swing divided by absolute vapour temperature. Scales the AP-42 breathing loss.",
    # Tank
    "pTankOz":  "Tank pressure (oz/in²) — the single most important live measurement. Must be held between the vacuum breaker (typically −6 oz) and the PVRV pop (typically +16 oz).",
    "tVap":     "Vapour space temperature (°R) — drives K-values and breathing loss. Rises through the day as the sun heats the tank shell.",
    "pTankAbs": "Tank absolute pressure (psia) — tank gauge pressure converted to absolute for thermodynamic calculations.",
    "qVent":    "Venting rate (MSCFD) — gas escaping through the thief hatch / PVRV to atmosphere. Any value above zero is lost revenue and a reportable emission.",
    "qAir":     "Air in-leakage (MSCFD) — outside air drawn in through the vacuum breaker when the compressor pulls the tank below the vacuum setting. Creates a flammable mixture risk.",
    # Compressor
    "Ps":       "Suction pressure (psia) — absolute pressure at the compressor inlet after suction-line losses. Governs the mass of gas the machine can move.",
    "Pd":       "Discharge pressure (psia) — absolute pressure at the compressor outlet. Set by the sales line or separator back-pressure.",
    "r":        "Pressure ratio (Pd/Ps) — how hard the compressor is working. Higher ratios need more horsepower and produce hotter discharge gas.",
    "rInt":     "Internal pressure ratio (Vᵢᵏ) — the pressure ratio the rotor geometry actually compresses to before the discharge port opens. Should match the system r for best efficiency.",
    "viEff":    "Effective built-in volume ratio — the Vᵢ actually in use, accounting for slide-valve position.",
    "k":        "Isentropic exponent k = Cp/Cv — governs how much the gas heats up during compression. Rich vapour has k closer to 1.1 vs methane's 1.30.",
    "etaV":     "Volumetric efficiency — fraction of displacement actually delivered as net flow. Reduced by rotor-tip leakage (slip), which is roughly constant with speed, so efficiency collapses at low rpm.",
    "dispCfm":  "Displacement rate (CFM) — theoretical swept volume per minute at current speed. Sets the ceiling on capacity before slip losses.",
    "qSlip":    "Slip flow (CFM) — gas leaking back through rotor clearances. Nearly independent of speed, which is why turndown hurts volumetric efficiency so much.",
    "etaPort":  "Port efficiency — how well the compressor's internal pressure ratio matches the system ratio. Below 1.0 means either over- or under-compression wastes shaft work.",
    "etaTot":   "Total isentropic efficiency (η_isen × η_port) — overall thermodynamic efficiency of the compression process.",
    "underComp":"Under-compression flag — true when system pressure ratio exceeds the internal ratio (Vᵢᵏ), meaning the discharge port opens before compression is complete and high-pressure gas blows back.",
    "zAvg":     "Average Z-factor across the compression path — used in the head calculation to account for real-gas deviation.",
    "head":     "Isentropic head (ft·lbf/lbm) — reversible work per pound of gas. Multiplied by mass flow and divided by efficiency to get shaft power.",
    "mDot":     "Mass flow rate (lb/min) — actual gas mass the compressor is moving. Combines capacity (MSCFD), vapour MW, and molar volume.",
    "rpm":      "Shaft speed (rpm) — current operating speed. On a VFD unit this is the primary capacity control.",
    "bhpGas":   "Gas-compression BHP — shaft power consumed by the gas compression alone, before mechanical losses and oil-pump load.",
    "bhp":      "Total shaft power (BHP) — includes gas compression, mechanical/bearing losses, and oil circulation pump. This is what the motor or engine must deliver.",
    "hpPct":    "Load on driver (%) — BHP as a fraction of the nameplate rating. Above 100% trips the overload.",
    "flowPct":  "Flow vs. nameplate (%) — current recovery rate as a fraction of the unit's rated max throughput.",
    "specPower":"Specific power (BHP/MMSCFD) — efficiency scorecard. Lower is better. Increases when Vᵢ mismatches the pressure ratio, when speed is low, or when suction pressure is lost.",
    # Discharge temperature
    "td":       "Oil-flooded discharge temperature (°F) — actual mixed temperature of gas and oil leaving the compressor. Injected oil absorbs heat of compression, making single-stage high-ratio compression possible.",
    "tdDry":    "Dry adiabatic discharge temperature (°F) — what the gas temperature would be with no oil injection. Illustrates why oil-flooded screws survive pressure ratios that would destroy a dry machine.",
    "cpG":      "Gas specific heat at constant pressure (Btu/lb·°F) — used in the discharge temperature and aftercooler energy balances.",
    # Aftercooler
    "ntu":      "Number of Transfer Units (NTU) — a dimensionless measure of aftercooler size. Higher NTU = more cooling. NTU = UA / (ṁ·cp).",
    "effHX":    "Aftercooler effectiveness ε = 1 − e^(−NTU) — fraction of maximum possible heat removed. 0.90 means you cool 90% of the way to ambient.",
    "tCool":    "Cooler outlet temperature (°F) — gas temperature entering the knockout drum. If below the hydrocarbon dew point, liquid condenses and you make free barrels.",
    "duty":     "Cooler heat duty (Btu/hr) — total heat removed by the air-cooled aftercooler. Drives fan and fin-tube sizing.",
    "dewPd":    "Hydrocarbon dew point at discharge pressure (°F) — temperature where the compressed vapour starts to condense. If cooler outlet is below this, condensate forms.",
    "nglBbl":   "Condensate / NGL recovered (bbl/d) — liquid hydrocarbons knocked out in the aftercooler separator. Often worth more per day than the gas revenue.",
    "qResid":   "Residue gas to sales (MSCFD) — gas remaining after condensate dropout. This is what the sales meter sees.",
    # Combustion
    "lhv":      "Lower Heating Value (Btu/scf) — energy released per standard cubic foot of vapour when burned, not counting water condensation. Tank vapour LHV is 1200–2000 Btu/scf vs pipeline gas ~1000.",
    "hhv":      "Higher Heating Value (Btu/scf) — LHV plus heat of water condensation. Used in Wobbe index and some reporting.",
    "wobbe":    "Wobbe Index — HHV divided by √SG. Two gases with the same Wobbe deliver the same heat through a fixed orifice at fixed pressure. Rich tank vapour has Wobbe near 2000 vs pipeline gas ~1350.",
    "sgVap":    "Vapour specific gravity — ratio of vapour MW to air MW (28.96). Rich tank vapour SG is 0.9–1.2 vs methane's 0.55.",
    "o2Stoich": "Stoichiometric oxygen demand (mol O₂/mol fuel) — oxygen needed to burn one mole of vapour completely.",
    "afStoichMol": "Stoichiometric air-fuel ratio (mol/mol) — moles of air needed per mole of fuel at perfect combustion.",
    "afStoichMass":"Stoichiometric air-fuel ratio (lb/lb) — mass of air per mass of fuel at perfect combustion.",
    "afActual": "Actual air-fuel ratio (lb/lb) — stoichiometric ratio multiplied by excess-air ratio λ. λ>1 means lean burn.",
    "tFlame":   "Adiabatic flame temperature (°F) — theoretical maximum flame temperature. Lean-burn engines target 2200–2600 °F to limit NOx.",
    "mn":       "Methane number — knock-resistance rating analogous to octane for gasoline. Heavy ends (C4+) severely degrade it. Below the engine's minimum requirement → knock damage.",
    "fuelMscfd":"Driver fuel consumption (MSCFD) — gas consumed by a gas-engine driver. Zero for electric units.",
    "kW":       "Electrical power draw (kW) — power consumed by an electric driver. Zero for gas-engine units.",
    "parasitic":"Parasitic fuel fraction (%) — percentage of recovered gas burned by the gas-engine driver. High parasitic erodes the economic case.",
    # Emissions & money
    "qNet":     "Net gas to sales (MSCFD) — residue gas minus driver fuel. This is the monetised product.",
    "ch4Vent":  "Methane vented (t/d) — actual methane mass escaping through the PVRV.",
    "ch4Slip":  "Engine methane slip (t/d) — unburned methane passing through a gas engine uncombusted. Small but counted in regulatory reports.",
    "co2eVru":  "CO₂-equivalent emissions with VRU operating (t CO₂e/d) — includes venting and engine slip methane (×GWP) plus combustion CO₂.",
    "co2eVent": "CO₂-equivalent if all gas vented (t CO₂e/d) — baseline if no recovery at all. Dominated by methane GWP.",
    "co2eFlare":"CO₂-equivalent if all gas flared (t CO₂e/d) — baseline with a flare. Better than venting because combustion converts CH₄ to CO₂, but DRE <100% means some CH₄ escapes.",
    "co2eAvoid":"Avoided CO₂-equivalent emissions (t CO₂e/d) — the environmental credit of running the VRU vs venting everything.",
    "revGas":   "Gas revenue ($/day) — net sales-gas volume times gas price.",
    "revNgl":   "NGL / condensate revenue ($/day) — knocked-out liquid volume times condensate price. Often the largest revenue line on a rich stream.",
    "costPwr":  "Electricity cost ($/day) — kW draw times hours times electricity price.",
    "costRent": "Package rental cost ($/day) — monthly rental rate prorated to daily.",
    "credit":   "Carbon / methane fee credit ($/day) — avoided CO₂e tonnes times carbon price. Zero if no carbon programme.",
    "netDay":   "Net daily margin ($/day) — total revenue plus credits minus operating costs. The single number that gets a VRU approved.",
    "lostDay":  "Value lost to venting ($/day) — gas escaping the PVRV, priced at the gas sales rate.",
}

# ─────────────────────────────────────────────────────────────────────────────
# Pure component library
# ─────────────────────────────────────────────────────────────────────────────
COMPS = [
    {"id":"N2",  "name":"Nitrogen",   "MW":28.014, "Tc":227.16, "Pc":493.0,  "w":0.0403, "LHV":0,      "HHV":0,      "nC":0,    "nH":0,  "cpA":6.75,  "cpB":0.00035},
    {"id":"CO2", "name":"CO2",        "MW":44.010, "Tc":547.56, "Pc":1071.0, "w":0.2276, "LHV":0,      "HHV":0,      "nC":0,    "nH":0,  "cpA":6.85,  "cpB":0.00330},
    {"id":"C1",  "name":"Methane",    "MW":16.043, "Tc":343.01, "Pc":666.4,  "w":0.0115, "LHV":909.4,  "HHV":1010.0, "nC":1,    "nH":4,  "cpA":6.90,  "cpB":0.00320},
    {"id":"C2",  "name":"Ethane",     "MW":30.070, "Tc":549.58, "Pc":706.5,  "w":0.0995, "LHV":1618.7, "HHV":1769.6, "nC":2,    "nH":6,  "cpA":8.10,  "cpB":0.00810},
    {"id":"C3",  "name":"Propane",    "MW":44.097, "Tc":665.69, "Pc":616.0,  "w":0.1523, "LHV":2314.9, "HHV":2516.1, "nC":3,    "nH":8,  "cpA":9.80,  "cpB":0.01230},
    {"id":"iC4", "name":"i-Butane",   "MW":58.123, "Tc":734.13, "Pc":527.9,  "w":0.1770, "LHV":3000.4, "HHV":3251.9, "nC":4,    "nH":10, "cpA":12.30, "cpB":0.01610},
    {"id":"nC4", "name":"n-Butane",   "MW":58.123, "Tc":765.29, "Pc":550.6,  "w":0.2002, "LHV":3010.8, "HHV":3262.3, "nC":4,    "nH":10, "cpA":12.60, "cpB":0.01620},
    {"id":"iC5", "name":"i-Pentane",  "MW":72.150, "Tc":828.77, "Pc":490.4,  "w":0.2275, "LHV":3699.0, "HHV":4000.9, "nC":5,    "nH":12, "cpA":15.10, "cpB":0.02010},
    {"id":"nC5", "name":"n-Pentane",  "MW":72.150, "Tc":845.47, "Pc":488.6,  "w":0.2515, "LHV":3706.9, "HHV":4008.9, "nC":5,    "nH":12, "cpA":15.40, "cpB":0.02020},
    {"id":"C6",  "name":"Hexane",     "MW":86.177, "Tc":913.27, "Pc":436.9,  "w":0.3013, "LHV":4403.8, "HHV":4755.9, "nC":6,    "nH":14, "cpA":18.10, "cpB":0.02410},
    {"id":"C7+", "name":"Heptanes+",  "MW":190.00, "Tc":1235.0, "Pc":240.0,  "w":0.6500, "LHV":9650.0, "HHV":10400.0,"nC":13.5, "nH":29, "cpA":38.00, "cpB":0.05200},
]
NC = len(COMPS)
IDX = {c["id"]: i for i, c in enumerate(COMPS)}

# Binary interaction parameters
def _build_kij():
    k = [[0.0]*NC for _ in range(NC)]
    n2_hc  = [0.0311,0.0515,0.0852,0.1033,0.0800,0.0922,0.1000,0.1496,0.1700]
    co2_hc = [0.0919,0.1322,0.1241,0.1200,0.1333,0.1219,0.1222,0.1100,0.1050]
    hc_ids = ["C1","C2","C3","iC4","nC4","iC5","nC5","C6","C7+"]
    for hi, hid in enumerate(hc_ids):
        i, j = IDX["N2"], IDX[hid]
        k[i][j] = k[j][i] = n2_hc[hi]
        i, j = IDX["CO2"], IDX[hid]
        k[i][j] = k[j][i] = co2_hc[hi]
    i, j = IDX["N2"], IDX["CO2"]
    k[i][j] = k[j][i] = -0.0170
    return k
KIJ = _build_kij()

FEED_DEFAULT = {"N2":0.25,"CO2":0.85,"C1":28.0,"C2":8.5,"C3":6.0,
                "iC4":1.1,"nC4":2.8,"iC5":1.1,"nC5":1.4,"C6":1.8,"C7+":48.2}

# ─────────────────────────────────────────────────────────────────────────────
# Unit models  (confirmed vs flowco-inc.com, July 2026)
# ─────────────────────────────────────────────────────────────────────────────
# Fields:
#   hp        — nameplate motor/engine horsepower
#   driver    — "electric" or "gas"
#   pdMax     — maximum discharge pressure (psig)
#   rpmRated  — rated shaft speed (rpm) — representative; actual varies by gear ratio
#   disp      — rotor displacement (ft³/rev) — representative for this frame
#   Vi        — built-in volume ratio — nominal for standard rotor set
#   oilGpm    — oil circulation rate (gpm)
#   msMax     — rated maximum capacity (MSCFD) at rated conditions
# ─────────────────────────────────────────────────────────────────────────────
MODELS = {
    # ── VRX Electric Series — marginal-well, 230 psig ──────────────────────
    "VRX7":     {"label":"VRX7 (7.5 hp)",       "hp":7.5,  "driver":"electric", "pdMax":230, "rpmRated":3550, "disp":0.0210, "Vi":2.2, "oilGpm":1.5, "msMax":40},
    "VRX15":    {"label":"VRX15 (15 hp)",        "hp":15,   "driver":"electric", "pdMax":230, "rpmRated":3550, "disp":0.0440, "Vi":2.4, "oilGpm":2.5, "msMax":75},
    "VRX25":    {"label":"VRX25 (25 hp)",        "hp":25,   "driver":"electric", "pdMax":230, "rpmRated":1750, "disp":0.0884, "Vi":2.6, "oilGpm":4,   "msMax":170},   # was 150 — corrected
    # ── FX Electric Series — 350 psig ─────────────────────────────────────
    "FX10V75":  {"label":"FX10V75 (75 hp)",      "hp":75,   "driver":"electric", "pdMax":350, "rpmRated":3550, "disp":0.0920, "Vi":3.2, "oilGpm":8,   "msMax":450},
    "FX12V125": {"label":"FX12V125 (75/125 hp)", "hp":125,  "driver":"electric", "pdMax":350, "rpmRated":3550, "disp":0.1612, "Vi":3.5, "oilGpm":12,  "msMax":850},   # was 750 — corrected
    "FX17V150": {"label":"FX17V150 (150 hp)",    "hp":150,  "driver":"electric", "pdMax":350, "rpmRated":3550, "disp":0.2600, "Vi":3.8, "oilGpm":16,  "msMax":1200},
    "FX20V300": {"label":"FX20V300 (300 hp)",    "hp":300,  "driver":"electric", "pdMax":350, "rpmRated":3550, "disp":0.4100, "Vi":4.0, "oilGpm":22,  "msMax":2000},
    # ── FX Gas Engine Series ───────────────────────────────────────────────
    "FX8G":     {"label":"FX8 gas (72 hp)",      "hp":72,   "driver":"gas",      "pdMax":230, "rpmRated":1800, "disp":0.0920, "Vi":2.8, "oilGpm":6,   "msMax":150},
    "FX10G":    {"label":"FX10 gas (92 hp)",     "hp":92,   "driver":"gas",      "pdMax":350, "rpmRated":1800, "disp":0.1600, "Vi":3.2, "oilGpm":8,   "msMax":450},
    "FX12G":    {"label":"FX12 gas (92/135 hp)", "hp":135,  "driver":"gas",      "pdMax":350, "rpmRated":1800, "disp":0.3176, "Vi":3.5, "oilGpm":12,  "msMax":750},
    "FX17G":    {"label":"FX17 gas (188 hp)",    "hp":188,  "driver":"gas",      "pdMax":350, "rpmRated":1800, "disp":0.4200, "Vi":3.8, "oilGpm":18,  "msMax":1200},
    "FX20G":    {"label":"FX20 gas (276 hp)",    "hp":276,  "driver":"gas",      "pdMax":350, "rpmRated":1800, "disp":0.5800, "Vi":4.0, "oilGpm":22,  "msMax":2000},
}

# ─────────────────────────────────────────────────────────────────────────────
# Mixture property helpers
# ─────────────────────────────────────────────────────────────────────────────
def normalize(y):
    s = sum(y)
    return [v/s for v in y] if s > 0 else list(y)

def mix_mw(y):    return sum(y[i]*COMPS[i]["MW"] for i in range(NC))
def mix_sg(y):    return mix_mw(y)/MW_AIR
def mix_lhv(y):   return sum(y[i]*COMPS[i]["LHV"] for i in range(NC))
def mix_hhv(y):   return sum(y[i]*COMPS[i]["HHV"] for i in range(NC))
def wobbe(y):
    sg = mix_sg(y)
    return mix_hhv(y)/math.sqrt(sg) if sg > 0 else 0.0

def mix_cp_molar(y, T):
    return sum(y[i]*(COMPS[i]["cpA"] + COMPS[i]["cpB"]*T) for i in range(NC))

def mix_cp_mass(y, T):
    return mix_cp_molar(y, T)/mix_mw(y)

def kappa_k(y, T):
    cp = mix_cp_molar(y, T)
    return cp/(cp - R_BTU)

# ─────────────────────────────────────────────────────────────────────────────
# Peng-Robinson EOS
# ─────────────────────────────────────────────────────────────────────────────
PR_A_CONST = 0.457235529
PR_B_CONST = 0.077796074

def pr_pure(i, T):
    c = COMPS[i]
    a  = PR_A_CONST * R_FT3**2 * c["Tc"]**2 / c["Pc"]
    b  = PR_B_CONST * R_FT3 * c["Tc"] / c["Pc"]
    kap = 0.37464 + 1.54226*c["w"] - 0.26992*c["w"]**2
    alpha = (1 + kap*(1 - math.sqrt(T/c["Tc"])))**2
    return {"a":a, "b":b, "alpha":alpha, "aa":a*alpha}

def pr_mix(y, T):
    p = [pr_pure(i, T) for i in range(NC)]
    aa, b = 0.0, 0.0
    for i in range(NC):
        b += y[i]*p[i]["b"]
        for j in range(NC):
            aa += y[i]*y[j]*math.sqrt(p[i]["aa"]*p[j]["aa"])*(1 - KIJ[i][j])
    return aa, b, p

def cubic_roots(b, c, d):
    """Solve z^3 + b*z^2 + c*z + d = 0, return real roots."""
    p = c - b*b/3
    q = 2*b**3/27 - b*c/3 + d
    disc = q*q/4 + p**3/27
    out = []
    if disc > 0:
        sq = math.sqrt(disc)
        def cbrt(x): return math.copysign(abs(x)**(1/3), x)
        s = cbrt(-q/2 + sq) + cbrt(-q/2 - sq)
        out.append(s - b/3)
    else:
        r   = math.sqrt(-p**3/27)
        phi = math.acos(max(-1, min(1, -q/(2*r))))
        m   = 2*math.sqrt(-p/3)
        for ki in range(3):
            out.append(m*math.cos((phi + 2*math.pi*ki)/3) - b/3)
    return out

def z_factor(y, T, P_abs, use_real, phase):
    if not use_real:
        return 1.0
    aa, b, _ = pr_mix(y, T)
    A = aa*P_abs/(R_FT3**2 * T**2)
    B = b*P_abs/(R_FT3*T)
    roots = [z for z in cubic_roots(-(1-B), A - 2*B - 3*B**2, -(A*B - B**2 - B**3))
             if z > B + 1e-9 and math.isfinite(z)]
    if not roots:
        return 1.0
    return max(roots) if phase == "V" else min(roots)

def gas_density(y, T, P_abs, use_real):
    Z = z_factor(y, T, P_abs, use_real, "V")
    n_v = P_abs/(Z*R_FT3*T)
    return {"Z": Z, "molar": n_v, "mass": n_v*mix_mw(y)}

# ─────────────────────────────────────────────────────────────────────────────
# Flash calculations
# ─────────────────────────────────────────────────────────────────────────────
def wilson_K(T, P_abs):
    return [(COMPS[i]["Pc"]/P_abs)*math.exp(5.37*(1+COMPS[i]["w"])*(1 - COMPS[i]["Tc"]/T))
            for i in range(NC)]

def rachford_rice(z, K):
    def f(beta):
        return sum(z[i]*(K[i]-1)/(1+beta*(K[i]-1)) for i in range(NC))
    if f(0) <= 0:
        return {"beta":0.0, "x":list(z), "y":normalize([z[i]*K[i] for i in range(NC)])}
    if f(1) >= 0:
        return {"beta":1.0, "x":normalize([z[i]/K[i] for i in range(NC)]), "y":list(z)}
    lo, hi = 0.0, 1.0
    for _ in range(80):
        beta = 0.5*(lo+hi)
        if f(beta) > 0: lo = beta
        else:           hi = beta
    beta = 0.5*(lo+hi)
    x = [z[i]/(1+beta*(K[i]-1)) for i in range(NC)]
    yv = [x[i]*K[i] for i in range(NC)]
    return {"beta":beta, "x":normalize(x), "y":normalize(yv)}

def ln_phi(y, T, P_abs, phase):
    aa, b, p = pr_mix(y, T)
    A = aa*P_abs/(R_FT3**2 * T**2)
    B = b*P_abs/(R_FT3*T)
    roots = [z for z in cubic_roots(-(1-B), A - 2*B - 3*B**2, -(A*B - B**2 - B**3))
             if z > B + 1e-9 and math.isfinite(z)]
    if not roots:
        return None, None
    Z = max(roots) if phase == "V" else min(roots)
    t = math.log(max(1e-12, (Z + (1+SQ2)*B)/(Z + (1-SQ2)*B)))
    # cross terms
    aaij = [[math.sqrt(p[i]["aa"]*p[j]["aa"])*(1-KIJ[i][j]) for j in range(NC)] for i in range(NC)]
    out = []
    for i in range(NC):
        s = sum(y[j]*aaij[i][j] for j in range(NC))
        phi_i = (p[i]["b"]/b*(Z-1) - math.log(max(1e-12, Z - B))
                 - A/(2*SQ2*B)*(2*s/aa - p[i]["b"]/b)*t)
        out.append(phi_i)
    return out, Z

def stage_flash(z, T, P_abs):
    """Full successive-substitution PR flash."""
    K = wilson_K(T, P_abs)
    res = rachford_rice(z, K)
    for _ in range(40):
        lnphi_L, _ = ln_phi(res["x"], T, P_abs, "L")
        lnphi_V, _ = ln_phi(res["y"], T, P_abs, "V")
        if lnphi_L is None or lnphi_V is None:
            break
        max_d = 0.0
        Kn = []
        for i in range(NC):
            kni = math.exp(lnphi_L[i] - lnphi_V[i])
            max_d = max(max_d, abs(math.log(kni/K[i])))
            Kn.append(kni)
        K = Kn
        res = rachford_rice(z, K)
        if max_d < 1e-9:
            break
    max_ln_k = max(abs(math.log(ki)) for ki in K)
    if max_ln_k < 1e-4:
        return {"beta":1.0, "x":list(z), "y":list(z), "K":K, "trivial":True}
    res["K"] = K
    return res

def bubble_P(x, T):
    """True vapour pressure of stock-tank liquid."""
    def g(P_abs):
        K = wilson_K(T, P_abs)
        return sum(x[i]*K[i] for i in range(NC)) - 1
    lo, hi = 0.05, 2000.0
    if g(lo) < 0: return lo
    if g(hi) > 0: return hi
    for _ in range(70):
        m = 0.5*(lo+hi)
        if g(m) > 0: lo = m
        else:        hi = m
    return 0.5*(lo+hi)

def practical_dew(y, P_abs):
    """Temperature at which 0.5% of stream has condensed."""
    def g(T):
        return stage_flash(y, T, P_abs)["beta"]
    lo, hi = F2R(-60), F2R(520)
    if g(hi) < 0.995:
        return hi
    for _ in range(22):
        m = 0.5*(lo+hi)
        if g(m) >= 0.995: hi = m
        else:              lo = m
    return 0.5*(lo+hi)

# ─────────────────────────────────────────────────────────────────────────────
# Main plant solver
# ─────────────────────────────────────────────────────────────────────────────
def solve(p, feed_pct, use_real=True):
    """
    Full one-pass evaluation of the VRU plant.
    p  — dict of all parameter values
    feed_pct — list of 11 mole-% values (un-normalised OK)
    Returns a flat dict of all computed outputs.
    """
    M = MODELS[p["model"]]
    z = normalize(feed_pct)
    o = {"M": M, "z": z}

    # ── 1. Separation train ────────────────────────────────────────────────
    Tsep  = F2R(p["tSep"])
    Psep  = p["pSep"] + PSTD
    st1   = stage_flash(z, Tsep, Psep)
    o["st1"] = st1

    sg_oil  = 141.5/(131.5 + p["api"])
    rho_oil = sg_oil * 62.37
    m_feed  = p["qLiq"] * 5.6146 * rho_oil
    n_feed  = m_feed / mix_mw(z)
    n_liq1  = n_feed * (1 - st1["beta"])

    pTankAbs = PSTD + p["pTankOz"]/OZ
    tVap     = F2R(p["tTank"])
    st2      = stage_flash(st1["x"], tVap, pTankAbs)
    o["st2"] = st2
    o["tVap"] = tVap
    o["pTankAbs"] = pTankAbs

    y_vap   = st2["y"] if st2["beta"] > 1e-9 else st1["x"]
    o["yVap"]  = y_vap
    o["xTank"] = st2["x"]

    n_vap2   = n_liq1 * st2["beta"]
    o["qFlash"] = n_vap2 * MOLVOL / 1000      # MSCFD

    # ── 2. AP-42 working & breathing losses ───────────────────────────────
    mw_vap = mix_mw(y_vap)
    tvp    = bubble_P(st2["x"], tVap)
    o["tvp"] = tvp

    n_liq2  = n_liq1*(1 - st2["beta"])
    mw_liq  = mix_mw(st2["x"])
    # stbbl: convert lbmol/d of stock-tank liquid to bbl/d using liquid density
    # 0.30 + 0.0030*MW approximates SG of NGL-type liquids (matches JS exactly)
    o["stbbl"] = n_liq2*mw_liq/(max(0.55, 0.30 + 0.0030*mw_liq)*62.37*5.6146)
    dens   = gas_density(y_vap, tVap, pTankAbs, use_real)
    o["zVap"] = dens["Z"]
    o["qWork"] = (o["stbbl"]*5.6146*(pTankAbs/PSTD)*(TSTD/tVap)/dens["Z"]
                  * p["turnKn"] * p["prodKp"] / 1000)

    v_space = p["nTank"]*math.pi/4*p["dTank"]**2*p["hTank"]*(1 - p["level"]/100)
    o["vSpace"] = v_space
    kE       = p["dTdiur"]/tVap * p["ventKe"]
    o["kE"]  = kE
    lS       = 365 * v_space * dens["mass"] * kE
    o["qBreath"] = (lS/365/mw_vap)*MOLVOL/1000

    o["qGen"] = o["qFlash"] + o["qWork"] + o["qBreath"] + p["qBlank"]

    # ── 3. Rotary screw compressor ─────────────────────────────────────────
    Ps   = max(PSTD - 0.45, pTankAbs - p["dpSuct"]/OZ)
    Pd   = p["pSales"] + PSTD
    r    = Pd/Ps
    Ts   = tVap
    k    = kappa_k(y_vap, Ts)
    o.update({"Ps":Ps, "Pd":Pd, "r":r, "k":k, "Ts":Ts})

    rpm   = M["rpmRated"] * p["load"]/100
    slide = 100.0
    o["rpm"]   = rpm
    o["slide"] = slide

    rho_s  = max(1e-4, gas_density(y_vap, Ts, Ps, use_real)["mass"])
    q_slip  = p["kSlip"] * math.sqrt(max(0, Pd - Ps)/rho_s)
    disp_cfm = p["disp"] * rpm * (slide/100)
    o["dispCfm"] = disp_cfm
    o["qSlip"]   = q_slip
    eta_V = (min(0.985, max(0, 1 - q_slip/disp_cfm))
             if p["running"] and disp_cfm > 0 else 0.0)
    o["etaV"] = eta_V

    acfm  = disp_cfm * eta_V
    z_s   = max(0.4, gas_density(y_vap, Ts, Ps, use_real)["Z"])
    scfm  = acfm*(Ps/PSTD)*(TSTD/Ts)/z_s
    o["qCap"] = max(0, scfm*1440/1000)

    # ── 4. Port mismatch and shaft power ──────────────────────────────────
    vi_eff = p["Vi"]
    o["viEff"] = vi_eff
    r_int  = vi_eff**k
    o["rInt"] = r_int
    w_comp = (Ps/(k-1))*(vi_eff**(k-1) - 1)
    p_int  = Ps*r_int
    w_port = (Pd - p_int)/vi_eff
    w_ind  = w_comp + w_port
    w_isen = (k/(k-1))*Ps*(r**((k-1)/k) - 1)
    eta_port = (min(1, max(0.2, w_isen/w_ind)) if w_ind > 1e-9 else 0.0)
    o["etaPort"]    = eta_port
    o["underComp"]  = r > r_int
    o["etaTot"]     = p["etaIs"] * eta_port

    z_avg = 0.5*(gas_density(y_vap,Ts,Ps,use_real)["Z"]
                 + gas_density(y_vap, Ts*r**((k-1)/k), Pd, use_real)["Z"])
    o["zAvg"] = z_avg
    o["head"] = (R_FTLBF/mw_vap)*Ts*z_avg*(k/(k-1))*(r**((k-1)/k) - 1)

    m_dot = o["qCap"]*1000/1440*mw_vap/MOLVOL
    o["mDot"] = m_dot
    o["bhpGas"] = m_dot*o["head"]/(33000*max(0.05, o["etaTot"]))
    o["bhp"]    = o["bhpGas"]/(1 - p["mechL"]) + (0.35*p["oilGpm"] if p["running"] else 0)
    o["hpPct"]  = 100*o["bhp"]/M["hp"]
    o["flowPct"]= 100*o["qCap"]/M["msMax"]

    # ── 5. Discharge temperature (oil-flooded) ────────────────────────────
    # Energy balance: shaft work + gas enthalpy in + oil enthalpy in = mixed enthalpy out
    # W_btu in Btu/min (1 hp = 42.408 Btu/min)
    # m_dot in lb/min, cp_g in Btu/(lb·°R), T in °R → Btu/min per °R · °R = Btu/min ✓
    # m_oil in lb/min, cpOil in Btu/(lb·°F), T in °R → consistent since ΔT °R = ΔT °F ✓
    o["tdDry"] = Ts * r**((k-1)/k)     # isentropic (dry) discharge temp, °R
    cp_g   = mix_cp_mass(y_vap, Ts)    # Btu/(lb·°R)
    m_oil  = p["oilGpm"] * 7.25        # lb/min  (oil SG ≈ 0.87, 7.25 lb/gal)
    W_btu  = o["bhp"] * 42.408         # Btu/min shaft work
    o["td"] = ((W_btu + m_dot*cp_g*Ts + m_oil*p["cpOil"]*F2R(p["tOil"]))
               / max(1e-6, m_dot*cp_g + m_oil*p["cpOil"]))
    if not p["running"] or m_dot < 1e-6:
        o["td"]    = F2R(p["tAir"])
        o["tdDry"] = F2R(p["tAir"])
    o["cpG"] = cp_g
    o["specPower"] = o["bhp"] / (o["qCap"] / 1000) if o["qCap"] > 0.01 else 0.0  # BHP/MMSCFD

    # ── 6. Aftercooler + condensate ───────────────────────────────────────
    # NTU = UA / (ṁ·cp)_min
    # uaCool is Btu/hr·°F; c_min must also be per-hour: m_dot(lb/min)*60*cp_g = Btu/hr·°F
    c_min_hr = max(1e-6, m_dot * 60 * cp_g)   # Btu/hr·°F
    o["ntu"]   = p["uaCool"] / c_min_hr
    o["effHX"] = 1 - math.exp(-o["ntu"])
    o["tCool"] = o["td"] - o["effHX"] * (o["td"] - F2R(p["tAir"]))
    o["duty"]  = c_min_hr * (o["td"] - o["tCool"])  # Btu/hr

    st_ko  = stage_flash(y_vap, o["tCool"], Pd)
    o["dewPd"]  = practical_dew(y_vap, Pd)
    n_gas   = o["qCap"]*1000/MOLVOL
    n_liq_ko = n_gas*(1 - st_ko["beta"])
    mw_ko  = mix_mw(st_ko["x"])
    sg_ko  = max(0.45, 0.30 + 0.0055*mw_ko)
    o["nglBbl"] = n_liq_ko*mw_ko/(sg_ko*62.37*5.6146)
    o["qResid"] = max(0, o["qCap"] - n_liq_ko*MOLVOL/1000)
    o["yResid"] = st_ko["y"] if st_ko["beta"] > 1e-6 else y_vap

    # ── 7. Relief and vacuum ──────────────────────────────────────────────
    over  = p["pTankOz"] - p["pPvrv"]
    o["qVent"] = p["cvVent"]*math.sqrt(over)/1000 if over > 0 else 0.0
    under = p["pVac"] - p["pTankOz"]
    o["qAir"]  = p["cvVac"]*math.sqrt(under) if under > 0 else 0.0

    # ── 8. Combustion ─────────────────────────────────────────────────────
    o["lhv"]   = mix_lhv(y_vap)
    o["hhv"]   = mix_hhv(y_vap)
    o["wobbe"] = wobbe(y_vap)
    o["sgVap"] = mix_sg(y_vap)

    o2, nC_bar, nH_bar = 0.0, 0.0, 0.0
    for i in range(NC):
        o2    += y_vap[i]*(COMPS[i]["nC"] + COMPS[i]["nH"]/4)
        nC_bar += y_vap[i]*COMPS[i]["nC"]
        nH_bar += y_vap[i]*COMPS[i]["nH"]
    o["o2Stoich"]     = o2
    o["afStoichMol"]  = o2/0.2095
    o["afStoichMass"] = o["afStoichMol"]*MW_AIR/mw_vap
    o["afActual"]     = o["afStoichMass"]*p["lambda"]
    o["nCbar"] = nC_bar

    n_prod = (nC_bar + nH_bar/2 + (p["lambda"]-1)*o2
              + o["afStoichMol"]*p["lambda"]*0.7808 + y_vap[IDX["N2"]])
    cp_prod = 8.9
    o["tFlame"] = F2R(p["tIntake"]) + (o["lhv"]*MOLVOL)/(max(1e-6, n_prod)*cp_prod)

    o["mn"] = (137.78*y_vap[IDX["C1"]] + 29.948*y_vap[IDX["C2"]]
               - 18.193*y_vap[IDX["C3"]]
               - 167.062*(y_vap[IDX["iC4"]]+y_vap[IDX["nC4"]]
                          +y_vap[IDX["iC5"]]+y_vap[IDX["nC5"]]
                          +y_vap[IDX["C6"]]+y_vap[IDX["C7+"]])
               + 181.233*y_vap[IDX["CO2"]] + 26.994*y_vap[IDX["N2"]])

    o["fuelMscfd"] = (o["bhp"]*p["bsfc"]*24/o["lhv"]/1000
                      if M["driver"] == "gas" and p["running"] and o["lhv"] > 1 else 0.0)
    o["kW"]        = (o["bhp"]*0.7457/p["etaMot"]
                      if M["driver"] == "electric" and p["running"] else 0.0)
    o["parasitic"] = 100*o["fuelMscfd"]/o["qCap"] if o["qCap"] > 0 else 0.0
    o["qNet"]      = max(0, o["qResid"] - o["fuelMscfd"])

    # ── 9. Emissions ──────────────────────────────────────────────────────
    def ch4_mass(q_mscfd):
        return q_mscfd*1000/MOLVOL*y_vap[IDX["C1"]]*COMPS[IDX["C1"]]["MW"]/2204.62

    o["ch4Vent"]   = ch4_mass(o["qVent"])
    o["ch4Slip"]   = ch4_mass(o["fuelMscfd"]*p["slipPct"]/100)
    o["co2eVru"]   = ((o["ch4Vent"] + o["ch4Slip"])*p["gwp"]
                      + o["fuelMscfd"]*1000/MOLVOL*nC_bar*44.01/2204.62)
    o["co2eVent"]  = ch4_mass(o["qGen"])*p["gwp"]
    o["co2eFlare"] = (ch4_mass(o["qGen"]*(1-p["dre"]/100))*p["gwp"]
                      + o["qGen"]*(p["dre"]/100)*1000/MOLVOL*nC_bar*44.01/2204.62)
    o["co2eAvoid"] = o["co2eVent"] - o["co2eVru"]

    # ── 10. Economics ─────────────────────────────────────────────────────
    o["revGas"]   = o["qNet"]*p["pxGas"]
    o["revNgl"]   = o["nglBbl"]*p["pxNgl"]
    o["costPwr"]  = o["kW"]*24*p["pxKwh"]
    o["costRent"] = p["rent"]*12/365
    o["credit"]   = o["co2eAvoid"]*p["co2Tax"]
    o["netDay"]   = o["revGas"] + o["revNgl"] + o["credit"] - o["costPwr"] - o["costRent"]
    o["lostDay"]  = o["qVent"]*p["pxGas"]

    return o


# ─────────────────────────────────────────────────────────────────────────────
# Session state bootstrap
# ─────────────────────────────────────────────────────────────────────────────
def default_params():
    return {
        # source
        "qLiq":4000.0, "api":38.0, "pSep":60.0, "tSep":95.0,
        "tTank":88.0, "dTdiur":24.0,
        # tank
        "nTank":3, "dTank":15.5, "hTank":16.0, "level":45.0,
        "turnKn":1.0, "prodKp":0.75, "ventKe":1.0, "qBlank":8.0,
        "pPvrv":16.0, "pVac":-6.0, "cvVent":420.0, "cvVac":900.0,
        # screw
        "disp":0.1612, "Vi":3.5, "kSlip":1.55, "etaIs":0.74,
        "mechL":0.045, "oilGpm":12.0, "tOil":150.0, "cpOil":0.46,
        "dpSuct":4.0,
        # thermal
        "uaCool":2600.0, "tAir":92.0, "scrubEff":99.0,
        # control
        "pSet":6.0, "load":100.0, "pSales":65.0,
        # combustion
        "lambda":1.60, "bsfc":8200.0, "tIntake":110.0, "mnReq":52.0,
        "slipPct":1.1, "dre":98.0, "gwp":28.0,
        # economics
        "pxGas":3.10, "pxNgl":38.0, "pxKwh":0.095, "etaMot":0.93,
        "rent":9500.0, "co2Tax":0.0,
        # state
        "pTankOz":6.0, "running":True, "model":"FX12V125",
        "use_real":True,
    }

if "p" not in st.session_state:
    st.session_state["p"] = default_params()

if "feed_pct" not in st.session_state:
    st.session_state["feed_pct"] = [FEED_DEFAULT.get(c["id"], 0.0) for c in COMPS]

if "page" not in st.session_state:
    st.session_state["page"] = "dashboard"

p        = st.session_state["p"]
feed_pct = st.session_state["feed_pct"]


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar navigation
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ VRU Trainer")
    st.caption("Flogistix-pattern rotary screw vapor recovery")
    st.divider()

    nav_pages = [
        ("🏗️", "3D View",        "3d"),
        ("🏠", "Dashboard",      "dashboard"),
        ("🎛️", "Simulator",      "simulator"),
        ("🎛️", "Control System", "controls"),
        ("📐", "Equations",      "equations"),
        ("📚", "Guided Lessons", "lessons"),
        ("📖", "Glossary",       "glossary"),
    ]
    for icon, label, key in nav_pages:
        if st.button(f"{icon}  {label}", key=f"nav_{key}", use_container_width=True):
            st.session_state["page"] = key
            st.rerun()

    st.divider()
    st.caption(f"Model: **{p['model']}**")
    st.caption(f"EOS: {'Peng-Robinson' if p['use_real'] else 'Ideal gas'}")

page = st.session_state["page"]

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def f(x, d=2):
    try:
        return f"{x:.{d}f}" if math.isfinite(x) else "—"
    except Exception:
        return "—"

def rrow(label, value, style="", key=None):
    cls = style if style else "val"
    tip = ""
    if key and key in READOUT_HELP:
        # Escape quotes in tooltip text
        tip_text = READOUT_HELP[key].replace('"', '&quot;')
        tip = f' title="{tip_text}" style="cursor:help;border-bottom:1px dotted #4E5C6A"'
    return (f'<div class="rrow">'
            f'<span class="lbl"{tip}>{label}</span>'
            f'<span class="{cls}">{value}</span>'
            f'</div>')

def alarm_html(msg, kind="red"):
    cls = {"red":"alarm-red","warn":"alarm-warn","ok":"alarm-ok"}.get(kind,"alarm-red")
    return f'<div class="{cls}">{msg}</div>'

def sec(title):
    st.markdown(f'<div class="sec-header">{title}</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Page: Dashboard
# ─────────────────────────────────────────────────────────────────────────────
def page_dashboard():
    st.title("⚙️ VRU Trainer — Dashboard")
    st.caption("Live plant overview. Adjust parameters on the **Simulator** page.")

    # Run the solver once with current state
    R = solve(p, feed_pct, p["use_real"])

    # ── Alarms ──
    alarms_html = ""
    if R["qVent"] > 0.05:
        alarms_html += alarm_html(f"🚨 VENTING {f(R['qVent'],1)} MSCFD to atmosphere — {f(R['lostDay'],0)} $/day lost", "red")
    if p["pTankOz"] < p["pVac"] + 0.5:
        alarms_html += alarm_html("⚠️ Tank near vacuum — vacuum breaker admitting air", "warn")
    if R["hpPct"] > 100:
        alarms_html += alarm_html(f"⚠️ Driver overload — {f(R['bhp'],0)} BHP vs {R['M']['hp']} hp rated", "warn")
    if R2F(R["td"]) > 340:
        alarms_html += alarm_html(f"⚠️ Discharge temperature {f(R2F(R['td']),0)} °F — check oil circulation", "warn")
    if R["M"]["driver"] == "gas" and R["mn"] < p["mnReq"]:
        alarms_html += alarm_html(f"⚠️ Methane number {f(R['mn'],1)} < required {p['mnReq']} — knock risk", "warn")
    if not alarms_html:
        alarms_html = alarm_html("✅ All systems normal", "ok")
    st.markdown(alarms_html, unsafe_allow_html=True)
    st.divider()

    # ── Top KPI metrics ──
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Tank Pressure",   f"{f(p['pTankOz'],1)} oz",  f"{f(p['pTankOz']-p['pSet'],1)} oz vs setpoint")
    c2.metric("Recovered",       f"{f(R['qNet'],1)} MSCFD")
    c3.metric("Generated",       f"{f(R['qGen'],1)} MSCFD")
    c4.metric("Shaft Power",     f"{f(R['bhp'],0)} BHP",      f"{f(R['hpPct'],0)}% of {R['M']['hp']} hp")
    c5.metric("Net Revenue",     f"${f(R['netDay'],0)}/day")
    c6.metric("Condensate",      f"{f(R['nglBbl'],2)} bbl/d")

    st.divider()
    col_l, col_m, col_r = st.columns(3)

    # ── Vapour source breakdown ──
    with col_l:
        sec("Vapour Source")
        html = ""
        html += rrow("Flash gas",      f"{f(R['qFlash'],1)} MSCFD",  "amb", "qFlash")
        html += rrow("Working loss",   f"{f(R['qWork'],2)} MSCFD",   "",    "qWork")
        html += rrow("Breathing loss", f"{f(R['qBreath'],2)} MSCFD", "",    "qBreath")
        html += rrow("Blanket/leak-in",f"{f(p['qBlank'],1)} MSCFD",  "",    "qBlank")
        html += rrow("TOTAL generated",f"{f(R['qGen'],1)} MSCFD",   "amb", "qGen")
        html += rrow("Vapour MW",      f"{f(mix_mw(R['yVap']),1)} lb/lbmol")
        html += rrow("TVP",            f"{f(R['tvp'],2)} psia",      "",    "tvp")
        st.markdown(html, unsafe_allow_html=True)

    # ── Compressor ──
    with col_m:
        sec("Compressor")
        hp_style = "hot" if R["hpPct"] > 100 else "amb"
        td_style = "hot" if R2F(R["td"]) > 340 else "good"
        html = ""
        html += rrow("Suction pressure",  f"{f(R['Ps'],2)} psia",              "",       "Ps")
        html += rrow("Discharge pressure",f"{f(R['Pd']-PSTD,0)} psig",         "",       "Pd")
        html += rrow("Pressure ratio",    f"{f(R['r'],2)}",                     "",       "r")
        html += rrow("Volumetric eff.",   f"{f(R['etaV']*100,1)} %",
                     "good" if R["etaV"] > 0.8 else "amb",                               "etaV")
        html += rrow("Port efficiency",   f"{f(R['etaPort']*100,1)} %",
                     "good" if R["etaPort"] > 0.9 else "amb",                            "etaPort")
        html += rrow("Shaft power",       f"{f(R['bhp'],1)} BHP",              hp_style, "bhp")
        html += rrow("Specific power",    f"{f(R['specPower'],0)} BHP/MMSCFD", "",       "specPower")
        html += rrow("Discharge temp",    f"{f(R2F(R['td']),0)} °F",           td_style, "td")
        html += rrow("Dry adiabatic",     f"{f(R2F(R['tdDry']),0)} °F",        "",       "tdDry")
        html += rrow("Condensate",        f"{f(R['nglBbl'],2)} bbl/d",         "amb",    "nglBbl")
        st.markdown(html, unsafe_allow_html=True)

    # ── Emissions & economics ──
    with col_r:
        sec("Emissions & Economics")
        net_style = "good" if R["netDay"] > 0 else "hot"
        html = ""
        html += rrow("Net to sales",     f"{f(R['qNet'],1)} MSCFD",        "amb",  "qNet")
        html += rrow("Gas revenue",      f"${f(R['revGas'],0)}/d",         "",     "revGas")
        html += rrow("NGL revenue",      f"${f(R['revNgl'],0)}/d",         "",     "revNgl")
        html += rrow("Power cost",       f"−${f(R['costPwr'],0)}/d",       "",     "costPwr")
        html += rrow("Rental",           f"−${f(R['costRent'],0)}/d",      "",     "costRent")
        html += rrow("Net margin",       f"${f(R['netDay'],0)}/d",         net_style, "netDay")
        html += rrow("CO₂e avoided",     f"{f(R['co2eAvoid']*365,0)} t/yr","good", "co2eAvoid")
        html += rrow("CO₂e (vent all)",  f"{f(R['co2eVent'],2)} t/d",      "",     "co2eVent")
        html += rrow("CO₂e (with VRU)",  f"{f(R['co2eVru'],3)} t/d",       "good", "co2eVru")
        st.markdown(html, unsafe_allow_html=True)

    st.divider()
    # ── Combustion & gas quality ──
    sec("Gas Quality & Combustion")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("LHV",          f"{f(R['lhv'],0)} Btu/scf")
    c2.metric("Wobbe Index",  f"{f(R['wobbe'],0)}")
    mn_delta = R["mn"] - p["mnReq"]
    c3.metric("Methane Number", f"{f(R['mn'],1)}", f"{f(mn_delta,1)} vs req. {p['mnReq']}")
    c4.metric("Flame Temp",   f"{f(R2F(R['tFlame']),0)} °F")


# ─────────────────────────────────────────────────────────────────────────────
# Page: Simulator
# ─────────────────────────────────────────────────────────────────────────────
def page_simulator():
    st.title("🎛️ Simulator")

    # ── Guided / Expert mode toggle ──────────────────────────────────────────
    mode_col, _, run_col = st.columns([2, 3, 2])
    with mode_col:
        sim_mode = st.radio("Mode", ["🟢 Guided", "⚙️ Expert"], horizontal=True,
                            key="sim_mode",
                            help="Guided: 8 key controls only. Expert: every parameter.")
    with run_col:
        running = st.toggle("Compressor Running", value=p["running"])
        p["running"] = running

    guided = sim_mode == "🟢 Guided"

    if guided:
        st.caption("Guided mode — the 8 parameters that drive 90% of outcomes. Master these first.")
    else:
        st.caption("Expert mode — every plant parameter exposed. Use the tabs below.")

    st.divider()

    # ── Model selector (always visible) ─────────────────────────────────────
    model_keys = list(MODELS.keys())
    model = st.selectbox(
        "★ Unit Model",
        model_keys,
        index=model_keys.index(p["model"]),
        format_func=lambda k: MODELS[k]["label"],
        help="Select the Flogistix model. This sets nameplate hp, max capacity, rotor geometry, and pressure rating."
    )
    if model != p["model"]:
        p["model"] = model
        M = MODELS[model]
        p["disp"] = M["disp"]; p["Vi"] = M["Vi"]; p["oilGpm"] = M["oilGpm"]
    M = MODELS[p["model"]]

    # ════════════════════════════════════════════════════════════════════════
    # GUIDED MODE — 8 high-leverage controls with inline context
    # ════════════════════════════════════════════════════════════════════════
    if guided:
        st.markdown('<div class="sec-header" style="color:#5B9BD5">★ Primary Controls — Source & Separation</div>', unsafe_allow_html=True)
        g1, g2 = st.columns(2)
        with g1:
            p["pSep"] = st.slider(
                "★ Separator pressure (psig)",
                15, 250, int(p["pSep"]), 5,
                help="The single biggest lever on VRU load. Drop this → less flash gas."
            )
            st.caption("↑ Drop this to cut flash gas — the cheapest 'bigger VRU' is often a lower separator pressure.")
            p["qLiq"] = st.slider(
                "★ Liquid production rate (bbl/d)",
                50, 30000, int(p["qLiq"]), 100,
                help="Well throughput. More oil → more flash and working-loss gas."
            )
            st.caption("↑ Sets working loss and flash gas volume directly.")
            p["api"] = st.slider(
                "Stock-tank oil gravity (°API)",
                22.0, 48.0, float(p["api"]), 0.5,
                help="Lighter oil (higher API) has more dissolved gas and higher TVP."
            )
        with g2:
            p["pTankOz"] = st.slider(
                "★ Tank pressure (oz/in²)",
                -10.0, 30.0, float(p["pTankOz"]), 0.25,
                help="Must stay between vacuum breaker (−6 oz) and PVRV (16 oz). The VRU holds this line."
            )
            st.caption(f"↑ Operating band: {p['pVac']:.1f} oz (vacuum) to {p['pPvrv']:.1f} oz (PVRV). Margin: {p['pPvrv']-p['pTankOz']:.1f} oz.")
            p["pSales"] = st.slider(
                "★ Sales / discharge pressure (psig)",
                20, 400, int(p["pSales"]), 5,
                help="The back-pressure the compressor works against. Higher = more hp required."
            )
            st.caption("↑ Governs pressure ratio and horsepower. Set by the pipeline or separator you're compressing into.")
            p["tAir"] = st.slider(
                "Ambient temperature (°F)",
                -10, 120, int(p["tAir"]), 1,
                help="Drives breathing loss and aftercooler performance. Hot days = more venting risk."
            )
            p["tTank"] = st.slider(
                "Tank vapour temperature (°F)",
                50, 130, int(p["tTank"]), 1,
                help="Hot tanks have higher TVP → more flash and working loss."
            )

    # ════════════════════════════════════════════════════════════════════════
    # EXPERT MODE — full parameter tabs
    # ════════════════════════════════════════════════════════════════════════
    else:
        use_real = st.toggle("Peng-Robinson EOS", value=p["use_real"])
        p["use_real"] = use_real

    # ── Parameter tabs (Expert only) ─────────────────────────────────────────
    if not guided:
        tabs = st.tabs(["🛢️ Source & Tank", "🔩 Compressor", "🌡️ Thermal & Control",
                        "🔥 Combustion", "💰 Economics", "⚗️ Composition"])

        # ── Tab 0: Source & Tank ──
        with tabs[0]:
            c1, c2 = st.columns(2)
            with c1:
                sec("★ Well Stream & Separator")
                p["qLiq"]   = st.slider("★ Well-stream liquid (bbl/d)", 50, 30000, int(p["qLiq"]), 50)
                p["api"]    = st.slider("Stock-tank oil gravity (°API)", 22.0, 48.0, float(p["api"]), 0.5)
                p["pSep"]   = st.slider("★ Separator pressure (psig)", 15, 250, int(p["pSep"]), 1)
                p["tSep"]   = st.slider("Separator temperature (°F)", 60, 160, int(p["tSep"]), 1)
                p["tTank"]  = st.slider("Tank liquid temperature (°F)", 50, 130, int(p["tTank"]), 1)
                p["dTdiur"] = st.slider("Diurnal vapour-space swing (°F)", 0, 50, int(p["dTdiur"]), 1)
                p["qBlank"] = st.slider("Blanket / gas-lift leak-in (MSCFD)", 0, 120, int(p["qBlank"]), 1)
            with c2:
                sec("Tank Battery Geometry")
                p["nTank"]  = st.slider("Number of stock tanks", 1, 6, int(p["nTank"]), 1)
                p["dTank"]  = st.slider("Tank diameter (ft)", 8.0, 24.0, float(p["dTank"]), 0.5)
                p["hTank"]  = st.slider("Tank shell height (ft)", 8.0, 32.0, float(p["hTank"]), 0.5)
                p["level"]  = st.slider("Average liquid level (%)", 5, 90, int(p["level"]), 1)
                p["turnKn"] = st.slider("Turnover factor K_N", 0.20, 1.00, float(p["turnKn"]), 0.01)
                p["prodKp"] = st.slider("Product factor K_P", 0.50, 1.00, float(p["prodKp"]), 0.01)
                p["ventKe"] = st.slider("Breathing-loss multiplier", 0.0, 3.0, float(p["ventKe"]), 0.05)
                p["pPvrv"]  = st.slider("★ Thief hatch / PVRV pop (oz)", 6.0, 40.0, float(p["pPvrv"]), 0.5)
                p["pVac"]   = st.slider("Vacuum breaker setting (oz)", -12.0, -1.0, float(p["pVac"]), 0.5)
                p["pTankOz"]= st.slider("★ Tank pressure (oz)", -10.0, 30.0, float(p["pTankOz"]), 0.25)

        # ── Tab 1: Compressor ──
        with tabs[1]:
            c1, c2 = st.columns(2)
            with c1:
                sec("Screw Geometry & Internals")
                p["disp"]   = st.slider("Rotor displacement (ft³/rev)", 0.02, 0.80, float(p["disp"]), 0.002)
                p["Vi"]     = st.slider("★ Built-in volume ratio Vᵢ", 1.6, 5.5, float(p["Vi"]), 0.05)
                p["kSlip"]  = st.slider("Clearance slip coefficient", 0.0, 6.0, float(p["kSlip"]), 0.05)
                p["load"]   = st.slider("★ Speed / load (%)", 0.0, 100.0, float(p["load"]), 1.0)
            with c2:
                sec("Performance & Oil System")
                p["etaIs"]  = st.slider("Baseline isentropic efficiency", 0.45, 0.90, float(p["etaIs"]), 0.005)
                p["mechL"]  = st.slider("Mechanical / bearing loss", 0.01, 0.12, float(p["mechL"]), 0.005)
                p["oilGpm"] = st.slider("Injected oil circulation (gpm)", 0.0, 40.0, float(p["oilGpm"]), 0.5)
                p["tOil"]   = st.slider("Oil inlet temperature (°F)", 90, 210, int(p["tOil"]), 1)
                p["cpOil"]  = st.slider("Oil specific heat (Btu/lb·°F)", 0.35, 0.60, float(p["cpOil"]), 0.005)
                p["dpSuct"] = st.slider("Suction line + scrubber loss (oz)", 0.0, 24.0, float(p["dpSuct"]), 0.5)
                p["pSales"] = st.slider("★ Sales / discharge pressure (psig)", 20, 400, int(p["pSales"]), 5)

        # ── Tab 2: Thermal & Control ──
        with tabs[2]:
            c1, c2 = st.columns(2)
            with c1:
                sec("Aftercooler")
                p["uaCool"]  = st.slider("Aftercooler UA (Btu/hr·°F)", 200, 9000, int(p["uaCool"]), 50)
                p["tAir"]    = st.slider("Ambient air temperature (°F)", -10, 120, int(p["tAir"]), 1)
                p["scrubEff"]= st.slider("Inlet scrubber separation (%)", 80.0, 100.0, float(p["scrubEff"]), 0.1)
            with c2:
                sec("Pressure Setpoint")
                p["pSet"]    = st.slider("Suction pressure setpoint (oz)", -2.0, 24.0, float(p["pSet"]), 0.25)
                p["cvVent"]  = st.slider("PVRV relief coefficient", 50, 1200, int(p["cvVent"]), 10)
                p["cvVac"]   = st.slider("Vacuum breaker capacity (MSCFD/√oz)", 20, 2000, int(p["cvVac"]), 20)

        # ── Tab 3: Combustion ──
        with tabs[3]:
            c1, c2 = st.columns(2)
            with c1:
                sec("Engine / Burner")
                p["lambda"]  = st.slider("Excess-air ratio λ", 1.0, 2.2, float(p["lambda"]), 0.01)
                p["bsfc"]    = st.slider("Driver heat rate BSFC (Btu/bhp·hr)", 6000, 12000, int(p["bsfc"]), 50)
                p["tIntake"] = st.slider("Combustion air inlet temperature (°F)", 40, 180, int(p["tIntake"]), 1)
                p["mnReq"]   = st.slider("Engine methane-number requirement", 30, 80, int(p["mnReq"]), 1)
            with c2:
                sec("Emissions")
                p["slipPct"] = st.slider("Engine methane slip (% of fuel)", 0.0, 4.0, float(p["slipPct"]), 0.05)
                p["dre"]     = st.slider("Flare destruction efficiency (%)", 90.0, 99.9, float(p["dre"]), 0.1)
                p["gwp"]     = st.slider("Methane GWP (100-yr)", 20, 86, int(p["gwp"]), 1)

        # ── Tab 4: Economics ──
        with tabs[4]:
            c1, c2 = st.columns(2)
            with c1:
                sec("Revenue")
                p["pxGas"]   = st.slider("Residue gas price ($/Mcf)", 0.5, 12.0, float(p["pxGas"]), 0.05)
                p["pxNgl"]   = st.slider("Condensate / NGL price ($/bbl)", 5, 90, int(p["pxNgl"]), 1)
            with c2:
                sec("Operating Cost")
                p["pxKwh"]   = st.slider("Electricity price ($/kWh)", 0.02, 0.30, float(p["pxKwh"]), 0.005)
                p["etaMot"]  = st.slider("Motor + drive efficiency", 0.80, 0.98, float(p["etaMot"]), 0.005)
                p["rent"]    = st.slider("Package rental rate ($/month)", 0, 30000, int(p["rent"]), 250)
                p["co2Tax"]  = st.slider("Methane fee / carbon value ($/tonne CO₂e)", 0, 200, int(p["co2Tax"]), 5)

        # ── Tab 5: Composition ──
        with tabs[5]:
            sec("Well-Stream Composition (mole %)")
            st.caption("Drag freely — values are normalised internally.")
            cols = st.columns(3)
            for i, comp in enumerate(COMPS):
                with cols[i % 3]:
                    feed_pct[i] = st.slider(
                        f"{comp['id']} — {comp['name']}",
                        0.0, 80.0, float(feed_pct[i]), 0.05,
                        key=f"comp_{i}"
                    )
            z = normalize(feed_pct)
            tot = sum(feed_pct)
            st.caption(f"Entered total: {f(tot,2)} mol%  ·  Vapour MW: **{f(mix_mw(normalize(feed_pct)),1)}** lb/lbmol  ·  SG: **{f(mix_sg(z),3)}**")

    st.divider()

    # ── Live results (always shown) ──────────────────────────────────────────
    R = solve(p, feed_pct, p["use_real"])
    sec("Live Results")

    html = ""
    if R["qVent"] > 0.05:
        html += alarm_html(f"🚨 VENTING {f(R['qVent'],1)} MSCFD — {f(R['lostDay'],0)} $/day to atmosphere", "red")
    if p["pTankOz"] < p["pVac"] + 0.5:
        html += alarm_html("⚠️ Tank near vacuum — check minimum load settings", "warn")
    if R["hpPct"] > 100:
        html += alarm_html(f"⚠️ Driver overload: {f(R['bhp'],0)} BHP / {R['M']['hp']} hp", "warn")
    if R2F(R["td"]) > 340:
        html += alarm_html(f"⚠️ Discharge temperature {f(R2F(R['td']),0)} °F", "warn")
    if R["M"]["driver"] == "gas" and R["mn"] < p["mnReq"]:
        html += alarm_html(f"⚠️ Methane number {f(R['mn'],1)} < required {p['mnReq']}", "warn")
    if not html:
        html = alarm_html("✅ All systems normal", "ok")
    st.markdown(html, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        sec("Vapour Generation")
        rows = [
            ("Flash gas",         f"{f(R['qFlash'],1)} MSCFD"),
            ("Working loss",      f"{f(R['qWork'],2)} MSCFD"),
            ("Breathing loss",    f"{f(R['qBreath'],2)} MSCFD"),
            ("Blanket/leak-in",   f"{f(p['qBlank'],1)} MSCFD"),
            ("TOTAL generated",   f"{f(R['qGen'],1)} MSCFD"),
            ("Vapour MW",         f"{f(mix_mw(R['yVap']),1)} lb/lbmol"),
            ("Tank TVP",          f"{f(R['tvp'],2)} psia"),
            ("Compressibility Z", f"{f(R['zVap'],4)}"),
            ("Vapour space",      f"{f(R['vSpace'],0)} ft³"),
        ]
        st.markdown("".join(rrow(l, v) for l, v in rows), unsafe_allow_html=True)

    with c2:
        sec("Compressor & Cooling")
        rows = [
            ("Suction pressure",   f"{f(R['Ps'],2)} psia"),
            ("Discharge pressure", f"{f(R['Pd']-PSTD,0)} psig"),
            ("Pressure ratio",     f"{f(R['r'],2)}"),
            ("Internal ratio Vᵢᵏ", f"{f(R['rInt'],2)}"),
            ("k (Cp/Cv)",          f"{f(R['k'],4)}"),
            ("Volumetric eff.",    f"{f(R['etaV']*100,1)} %"),
            ("Port efficiency",    f"{f(R['etaPort']*100,1)} %"),
            ("Shaft power",        f"{f(R['bhp'],1)} BHP ({f(R['hpPct'],0)} %)"),
            ("Isentropic head",    f"{f(R['head'],0)} ft·lbf/lbm"),
            ("Mass flow",          f"{f(R['mDot'],2)} lb/min"),
            ("Discharge temp",     f"{f(R2F(R['td']),0)} °F"),
            ("Dry adiabatic",      f"{f(R2F(R['tdDry']),0)} °F"),
            ("Cooler outlet",      f"{f(R2F(R['tCool']),0)} °F"),
            ("Dew point @ Pd",     f"{f(R2F(R['dewPd']),0)} °F"),
            ("Condensate",         f"{f(R['nglBbl'],2)} bbl/d"),
            ("Residue gas",        f"{f(R['qResid'],1)} MSCFD"),
        ]
        st.markdown("".join(rrow(l, v) for l, v in rows), unsafe_allow_html=True)

    with c3:
        sec("Combustion, Emissions & Money")
        rows = [
            ("LHV",             f"{f(R['lhv'],0)} Btu/scf"),
            ("HHV",             f"{f(R['hhv'],0)} Btu/scf"),
            ("Wobbe index",     f"{f(R['wobbe'],0)}"),
            ("A/F stoich",      f"{f(R['afStoichMass'],2)} lb/lb"),
            ("Flame temp",      f"{f(R2F(R['tFlame']),0)} °F"),
            ("Methane number",  f"{f(R['mn'],1)}"),
            ("Driver fuel",     f"{f(R['fuelMscfd'],1)} MSCFD"),
            ("Electrical draw", f"{f(R['kW'],1)} kW"),
            ("Net to sales",    f"{f(R['qNet'],1)} MSCFD"),
            ("CO₂e — vent all", f"{f(R['co2eVent'],2)} t/d"),
            ("CO₂e — with VRU", f"{f(R['co2eVru'],3)} t/d"),
            ("CO₂e avoided",    f"{f(R['co2eAvoid']*365,0)} t/yr"),
            ("Gas revenue",     f"${f(R['revGas'],0)}/d"),
            ("NGL revenue",     f"${f(R['revNgl'],0)}/d"),
            ("Power cost",      f"−${f(R['costPwr'],0)}/d"),
            ("Rental",          f"−${f(R['costRent'],0)}/d"),
            ("Net margin",      f"${f(R['netDay'],0)}/d"),
        ]
        st.markdown("".join(rrow(l, v) for l, v in rows), unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Sensitivity chart helper — renders an inline mini-chart for each formula card
# ─────────────────────────────────────────────────────────────────────────────
def sens_chart(label, x_vals, y_vals, x_current, y_current, x_unit="", y_unit="", takeaway=""):
    """
    Renders a compact sensitivity chart using Streamlit's line_chart.
    x_vals / y_vals — lists of equal length
    x_current / y_current — current operating point (highlighted as a metric)
    """
    import pandas as pd
    df = pd.DataFrame({"x": x_vals, label: y_vals}).set_index("x")
    st.markdown(f"**📈 Sensitivity — how {label} responds to {label.split('(')[0].strip()}:**")
    st.line_chart(df, height=160, use_container_width=True)
    col_a, col_b = st.columns(2)
    col_a.metric(f"Current {x_unit}", f"{x_current:.2g}")
    col_b.metric(f"Current output {y_unit}", f"{y_current:.3g}")
    if takeaway:
        st.caption(f"💡 {takeaway}")


def _chart_flash_vs_sep(p, feed_pct):
    import pandas as pd
    xs = list(range(15, 251, 10))
    ys = []
    for ps in xs:
        pp = dict(p); pp["pSep"] = ps
        try:
            r = solve(pp, feed_pct, False)
            ys.append(round(r["qFlash"], 2))
        except Exception:
            ys.append(None)
    df = pd.DataFrame({"Separator pressure (psig)": xs, "Flash gas (MSCFD)": ys}).set_index("Separator pressure (psig)")
    st.markdown("**📈 Flash gas vs separator pressure** — hold everything else constant:")
    st.line_chart(df, height=160, use_container_width=True)
    col_a, col_b = st.columns(2)
    col_a.metric("Current sep pressure", f"{p['pSep']} psig")
    col_b.metric("Current flash gas", f"{solve(p, feed_pct, False)['qFlash']:.2f} MSCFD")
    st.caption("💡 Dropping separator pressure is often the cheapest way to reduce VRU load — no new equipment needed.")


def _chart_etav_vs_speed(p, feed_pct):
    import pandas as pd
    xs = list(range(10, 101, 5))
    ys = []
    M = MODELS[p["model"]]
    for spd in xs:
        pp = dict(p); pp["load"] = spd
        try:
            rpm = M["rpmRated"] * spd / 100
            Ps = max(PSTD - 0.45, (PSTD + p["pTankOz"] / OZ) - p["dpSuct"] / OZ)
            Pd = p["pSales"] + PSTD
            rho_s = max(1e-4, gas_density(normalize(feed_pct), F2R(p["tTank"]), Ps, False)["mass"])
            q_slip = p["kSlip"] * math.sqrt(max(0, Pd - Ps) / rho_s)
            disp_cfm = p["disp"] * rpm
            eta_v = max(0, 1 - q_slip / disp_cfm) if disp_cfm > 0 else 0
            ys.append(round(eta_v * 100, 1))
        except Exception:
            ys.append(None)
    df = pd.DataFrame({"Speed (%rated)": xs, "Volumetric eff. (%)": ys}).set_index("Speed (%rated)")
    st.markdown("**📈 Volumetric efficiency vs shaft speed** — slip is nearly constant, so turndown kills efficiency:")
    st.line_chart(df, height=160, use_container_width=True)
    col_a, col_b = st.columns(2)
    col_a.metric("Current speed", f"{p['load']:.0f}%")
    col_b.metric("Current η_V", f"{solve(p, feed_pct, False)['etaV']*100:.1f}%")
    st.caption("💡 Below ~40% speed, slip exceeds displacement and the machine barely moves gas. This sets the real minimum load.")


def _chart_bhp_vs_pr(p, feed_pct):
    import pandas as pd
    xs = [round(1.5 + i * 0.5, 1) for i in range(20)]
    ys = []
    for pr in xs:
        target_pd = pr * (PSTD + p["pTankOz"] / OZ) - PSTD
        pp = dict(p); pp["pSales"] = max(20, int(target_pd))
        try:
            r = solve(pp, feed_pct, False)
            ys.append(round(r["bhp"], 1))
        except Exception:
            ys.append(None)
    df = pd.DataFrame({"Pressure ratio": xs, "Shaft power (BHP)": ys}).set_index("Pressure ratio")
    st.markdown("**📈 Shaft power vs pressure ratio** — power rises steeply at high ratios:")
    st.line_chart(df, height=160, use_container_width=True)
    col_a, col_b = st.columns(2)
    col_a.metric("Current ratio", f"{solve(p, feed_pct, False)['r']:.2f}")
    col_b.metric("Current BHP", f"{solve(p, feed_pct, False)['bhp']:.0f}")
    st.caption("💡 BHP scales roughly as r^((k-1)/k). Doubling the pressure ratio doesn't double BHP — it's worse than that.")


def _chart_td_vs_oilgpm(p, feed_pct):
    import pandas as pd
    xs = [round(i * 0.5, 1) for i in range(0, 41)]
    ys = []
    for gpm in xs:
        pp = dict(p); pp["oilGpm"] = gpm
        try:
            r = solve(pp, feed_pct, False)
            ys.append(round(R2F(r["td"]), 0))
        except Exception:
            ys.append(None)
    df = pd.DataFrame({"Oil circulation (gpm)": xs, "Discharge temp (°F)": ys}).set_index("Oil circulation (gpm)")
    st.markdown("**📈 Discharge temperature vs oil circulation** — injected oil absorbs compression heat:")
    st.line_chart(df, height=160, use_container_width=True)
    r_now = solve(p, feed_pct, False)
    col_a, col_b = st.columns(2)
    col_a.metric("Current oil flow", f"{p['oilGpm']:.1f} gpm")
    col_b.metric("Current disch. temp", f"{R2F(r_now['td']):.0f} °F")
    st.caption(f"💡 With zero oil: {R2F(r_now['tdDry']):.0f} °F dry adiabatic. Oil injection drops this to a survivable level.")


# ─────────────────────────────────────────────────────────────────────────────
# Page: Equations
# ─────────────────────────────────────────────────────────────────────────────
def page_equations():
    st.title("📐 How the Math Works")
    st.caption("Every calculation explained in plain English — what each symbol means, what the formula does, and what the live number tells you right now.")

    R = solve(p, feed_pct, p["use_real"])

    def card(title, what_it_calculates, symbols_explained, formula_lines, live_value, real_world, chart_fn=None):
        with st.expander(f"**{title}**", expanded=False):
            st.markdown(f"**🎯 What this calculates:** {what_it_calculates}")
            st.divider()
            st.markdown("**🔤 What each symbol means:**")
            for line in symbols_explained:
                st.markdown(f"- {line}")
            st.divider()
            st.markdown("**📝 The formula:**")
            st.markdown(f'<div class="formula-box">{chr(10).join(formula_lines)}</div>', unsafe_allow_html=True)
            st.markdown("**📊 Live numbers right now:**")
            st.markdown(f'<div class="numbox">▶ {live_value}</div>', unsafe_allow_html=True)
            if chart_fn:
                st.divider()
                chart_fn()
            st.divider()
            st.markdown(f"**🌍 What this means in the real world:** {real_world}")


    tabs = st.tabs(["⛽ Gas Properties", "💨 Vapour Generation", "🛢️ Tank & Relief",
                    "🔩 Compressor", "🌡️ Heat & Condensate", "🔥 Combustion", "💰 Emissions & Money"])

    # ── Tab 0: Gas Properties ──────────────────────────────────────────────
    with tabs[0]:
        st.info("These calculations describe the GAS ITSELF — how heavy it is, how it behaves under pressure, and how it splits between liquid and vapour.")

        card(
            "How heavy is the gas mixture?",
            "Takes all the different gas molecules in our mixture, weights them by how much of each we have, and gives us one average 'heaviness' number.",
            [
                "**M_mix** = the average molecular weight of the gas mixture (how heavy the molecules are, in lb per lbmol). Pure methane is 16. Tank vapour is typically 28–40 because heavier molecules are mixed in.",
                "**yᵢ** = the fraction of molecule type i in the gas (e.g. y_C1 = 0.28 means 28% methane). All fractions add up to 1.0.",
                "**Mᵢ** = the molecular weight of each individual component (methane=16, propane=44, etc.)",
                "**SG** = Specific Gravity — how heavy the gas is compared to plain air (air=1.0). Pipeline methane is 0.55. Tank vapour is often 0.9–1.3.",
                "**28.9625** = molecular weight of air, used as the reference.",
            ],
            ["M_mix = sum of (fraction of each component × its molecular weight)",
             "SG    = M_mix ÷ 28.9625"],
            f"Right now:  M = {f(mix_mw(R['yVap']))} lb/lbmol   |   SG = {f(mix_sg(R['yVap']),3)}   |   (pure methane for comparison: 16.04 / 0.554)",
            "Tank vapour is much heavier than pipeline gas because the heavier molecules (propane, butane, pentane) concentrate in the liquid and then boil off at tank pressure. The heavier the vapour, the more energy it carries — which means more revenue, but also more load on the compressor."
        )

        card(
            "The Real Gas Correction (Z-factor)",
            "Gases don't behave perfectly at high pressure — molecules bump into each other and take up space. Z is a correction factor that accounts for this. Z=1.0 means perfect gas behaviour. Z<1.0 means the gas is more compressed than a perfect gas would be.",
            [
                "**Z** = compressibility factor — the ratio of 'how the real gas actually behaves' to 'how a perfect textbook gas would behave'. If Z=0.95, the gas is 5% denser than the simple formula predicts.",
                "**P** = pressure (psia — pounds per square inch absolute)",
                "**v** = volume per mole of gas (ft³/lbmol)",
                "**R** = the universal gas constant = 10.7316 psia·ft³/(lbmol·°R) — a fixed number from physics",
                "**T** = temperature in Rankine (°R = °F + 459.67). We must use absolute temperature in gas equations.",
                "**a, b** = constants that describe how strongly the molecules attract each other (a) and how much space they physically take up (b). Different for each molecule type.",
                "**α (alpha)** = a temperature correction on the attraction term — attraction weakens at high temperatures",
                "**ω (omega)** = acentric factor — a number that describes how non-spherical the molecule is (methane ≈ 0.01, heavier molecules ≈ 0.2–0.65)",
                "**Tc, Pc** = critical temperature and pressure — the point beyond which gas and liquid become indistinguishable",
            ],
            ["Simplified: P·v = Z·R·T   (Z=1 gives the ideal gas law P·v = R·T)",
             "Z comes from solving a cubic equation built from the PR equation of state"],
            f"Z at suction ({f(R['Ps'],1)} psia): {f(z_factor(R['yVap'],R['Ts'],R['Ps'],True,'V'),4)}  |  Z at discharge ({f(R['Pd']-PSTD,0)} psig): {f(z_factor(R['yVap'],R['Ts']*R['r']**((R['k']-1)/R['k']),R['Pd'],True,'V'),4)}",
            "At low tank pressure (~15 psia), Z is very close to 1.0 — the simple gas law works fine. At 350 psig discharge with rich vapour, Z drops to ~0.93, meaning the gas is 7% denser than a simple calculation would predict. Ignore this and your horsepower estimate will be off."
        )

        card(
            "k — How much does the gas heat up when compressed?",
            "When you squeeze a gas, it heats up. The 'k' value tells us how much. High k = lots of heating. Low k = less heating. This controls discharge temperature and horsepower.",
            [
                "**k** = isentropic exponent (also called the heat capacity ratio or Cp/Cv). Pure methane ≈ 1.30. Rich tank vapour ≈ 1.10–1.20. Lower k is actually better for a compressor — cooler discharge.",
                "**Cp°** = heat capacity at constant pressure — how much energy it takes to heat 1 lbmol of gas by 1°R. Units: Btu/(lbmol·°R).",
                "**R** = gas constant = 1.986 Btu/(lbmol·°R) in heat units",
                "**aᵢ, bᵢ** = simple coefficients for each component's heat capacity curve (not the same a,b as in the EOS above — just a naming coincidence)",
                "**T** = temperature in Rankine",
            ],
            ["Cp° = sum of (fraction of each component × its heat capacity)",
             "k   = Cp° ÷ (Cp° − 1.986)"],
            f"Cp° = {f(mix_cp_molar(R['yVap'],R['Ts']),3)} Btu/lbmol·°R   →   k = {f(R['k'],4)}",
            "Rich tank vapour has a lower k than pipeline methane. This means it heats up less per unit of pressure increase — so the compressor discharge temperature is lower and you don't need as much cooling. It's one of the reasons VRU compressors can operate at high pressure ratios."
        )

        card(
            "K-values — Does each molecule prefer to be gas or liquid?",
            "At any given temperature and pressure, each type of molecule has a preference for being in the gas phase vs staying in the liquid. K is that preference ratio. K=1 means it's indifferent. K>>1 strongly prefers gas. K<<1 strongly prefers liquid.",
            [
                "**K_i** = equilibrium ratio for component i. K > 1 means it prefers vapour. K < 1 means it prefers liquid.",
                "**Pc,i** = critical pressure of component i (psia)",
                "**P** = current pressure (psia)",
                "**ωᵢ** = acentric factor of component i",
                "**Tc,i** = critical temperature of component i (°R)",
                "**T** = current temperature (°R)",
                "**exp[...]** = e raised to the power of what's in the brackets — a standard math function",
            ],
            ["K_i = (Pc,i ÷ P) × exp[ 5.37 × (1 + ωᵢ) × (1 − Tc,i ÷ T) ]"],
            (lambda K: f"At tank conditions:  K(methane C1) = {f(K[IDX['C1']],1)}  |  K(propane C3) = {f(K[IDX['C3']],2)}  |  K(heptanes+ C7+) = {f(K[IDX['C7+']],5)}")(wilson_K(R["tVap"], R["pTankAbs"])),
            "Methane's K-value at tank conditions is in the thousands — almost all of it instantly flashes to gas. Heptanes+ K is near 0.00001 — almost all of it stays liquid. This is why the vapour coming off the tank is rich in lighter molecules even though the oil itself is mostly heavy ends."
        )

        card(
            "β (beta) — What fraction of the liquid turns to gas?",
            "When oil drops from high separator pressure to low tank pressure, some of it flashes to gas. Beta (β) is the fraction that becomes gas. β=0 means nothing flashed. β=1 means everything became gas. In practice the tank flash β is tiny but acts on thousands of barrels per day.",
            [
                "**β** = vapour fraction (0 to 1). β=0.05 means 5% of the moles became vapour.",
                "**zᵢ** = feed composition — fraction of each component in the incoming stream",
                "**Kᵢ** = K-value for each component (from the formula above)",
                "**xᵢ** = fraction of component i in the liquid phase after flashing",
                "**yᵢ** = fraction of component i in the vapour phase after flashing",
                "The equation is solved by trial and error — try different β values until the equation balances.",
            ],
            ["Find β such that:  Σ [ zᵢ × (Kᵢ−1) ÷ (1 + β×(Kᵢ−1)) ] = 0",
             "Then:  xᵢ = zᵢ ÷ (1 + β×(Kᵢ−1))   and   yᵢ = Kᵢ × xᵢ"],
            f"Separator β = {f(R['st1']['beta'],4)} ({f(R['st1']['beta']*100,2)}% flashes to gas at separator)  |  Tank β = {f(R['st2']['beta'],5)} ({f(R['st2']['beta']*100,3)}% flashes to gas at tank)  →  {f(R['qFlash'],1)} MSCFD flash gas",
            "The tank β looks tiny but remember it acts on every barrel of oil flowing into the tank every day. Even 0.1% of a 10,000 bbl/d stream is 10 bbl/d worth of gas. That's the whole reason the VRU exists."
        )

    # ── Tab 1: Vapour Generation ───────────────────────────────────────────
    with tabs[1]:
        st.info("These calculations figure out HOW MUCH GAS is showing up at the tank each day — and where it's coming from. This is the load the VRU has to handle.")

        card(
            "Total gas the VRU must handle",
            "Adds up all four sources of gas arriving at the tank. This total is what the compressor must capture every minute or the tank pressure rises until the hatch pops.",
            [
                "**Q_gen** = total gas generated (MSCFD = thousand standard cubic feet per day)",
                "**Q_flash** = gas that flashes off when oil drops from separator pressure to tank pressure",
                "**Q_work** = gas displaced by incoming oil filling up the tank (like pushing air out of a bottle)",
                "**Q_breathe** = gas that escapes as the tank heats up during the day and expands",
                "**Q_blanket** = gas deliberately added to keep air out, plus any leaks into the vapour space",
            ],
            ["Q_gen = Q_flash + Q_work + Q_breathe + Q_blanket"],
            f"Right now:  {f(R['qFlash'],1)} (flash) + {f(R['qWork'],1)} (working) + {f(R['qBreath'],1)} (breathing) + {f(p['qBlank'],1)} (blanket) = {f(R['qGen'],1)} MSCFD total",
            "Flash gas is almost always the biggest piece and it responds directly to separator pressure. Drop the separator from 180 psig to 40 psig and the flash gas — and your VRU load — can fall by half. That's a process fix, not a compressor fix."
        )

        sg_oil = 141.5/(131.5 + p["api"])
        card(
            "Flash gas — converting barrels of oil into MSCFD of gas",
            "Takes the liquid oil flow rate in barrels per day and converts it through a chain of physics to get the gas rate in MSCFD. Each step converts units from one system to another.",
            [
                "**ṅ_feed** = molar flow rate of the well-stream (lbmol/day) — how many 'packages' of molecules flow in per day",
                "**q_liq** = liquid flow rate into the separator (bbl/day — barrels per day)",
                "**5.6146** = conversion factor: 1 barrel = 5.6146 cubic feet",
                "**γₒ** = oil specific gravity = 141.5 ÷ (131.5 + API gravity). For 38 API oil, γₒ ≈ 0.835",
                "**62.37** = density of water in lb/ft³ — used because specific gravity is relative to water",
                "**M_feed** = molecular weight of the live oil mixture",
                "**β₁** = vapour fraction at the separator (most gas leaves here)",
                "**β₂** = vapour fraction at the tank (the small remainder that flashes at tank pressure)",
                "**379.48** = standard cubic feet per lbmol at 14.696 psia and 60°F — converts moles to gas volume",
                "**÷ 1000** = converts scf/day to Mscf/day (thousands of cubic feet per day)",
            ],
            ["ṅ_feed = q_liq × 5.6146 × γₒ × 62.37 ÷ M_feed     (barrels → lbmol/day)",
             "Q_flash = ṅ_feed × (1−β₁) × β₂ × 379.48 ÷ 1000    (lbmol/day → MSCFD)"],
            f"γₒ = {f(sg_oil,4)}  |  ṅ_feed = {f(p['qLiq']*5.6146*sg_oil*62.37/mix_mw(R['z']),0)} lbmol/day  →  Flash gas = {f(R['qFlash'],1)} MSCFD",
            "This is a long chain of unit conversions. The key insight is that 'barrels per day of oil' and 'thousand cubic feet per day of gas' are measuring the same physical stream in completely different units — this formula is how you get from one to the other.",
            chart_fn=lambda: _chart_flash_vs_sep(p, feed_pct)
        )

        card(
            "Working loss — gas pushed out by incoming oil",
            "Every barrel of oil flowing into the tank physically displaces a barrel of gas-saturated vapour space. Like filling a bottle with water — the air has to go somewhere. This is unavoidable and only tank management can reduce it.",
            [
                "**Q_work** = working loss in MSCFD",
                "**q_ST** = stock-tank oil rate (bbl/day) — oil actually filling the tanks",
                "**5.6146** = ft³ per barrel (unit conversion)",
                "**P_tank / P_std** = pressure correction — gas at tank pressure occupies less volume than at standard conditions",
                "**T_std / T_vap** = temperature correction — hot gas occupies more volume than cold gas",
                "**1/Z** = real-gas correction (the Z-factor from earlier)",
                "**K_N** = turnover factor — accounts for the fact that the vapour space isn't always fully saturated (typically 0.75–1.0)",
                "**K_P** = product factor — crude oil doesn't saturate the vapour space as fully as refined products",
                "**÷ 1000** = converts to MSCFD",
            ],
            ["Q_work = q_ST × 5.6146 × (P_tank÷P_std) × (T_std÷T_vap) × (1÷Z) × K_N × K_P ÷ 1000"],
            f"Stock-tank oil = {f(R['stbbl'],0)} bbl/day → {f(R['stbbl']*5.6146,0)} ft³/day displaced → {f(R['qWork'],2)} MSCFD",
            "You can't eliminate working loss without reducing throughput. But you can capture it — that displaced vapour is exactly what the VRU header collects."
        )

        card(
            "Breathing loss — the tank inhaling and exhaling with temperature",
            "As the sun heats the tank shell during the day, the gas inside expands and some escapes. At night it cools and contracts (which can cause a vacuum). This daily breathing is entirely driven by temperature swings.",
            [
                "**L_S** = standing (breathing) loss in lb/year",
                "**V_V** = vapour space volume (ft³) — the empty space above the liquid in all tanks",
                "**π/4 × d² × h** = formula for the volume of a cylinder: π/4 times diameter² times height",
                "**(1 − level/100)** = fraction of tank that's vapour (if tank is 45% full of liquid, 55% is vapour space)",
                "**n_tanks** = number of tanks",
                "**W_V** = vapour density (lb/ft³) — how heavy the gas is per cubic foot at tank conditions",
                "**K_E** = daily temperature swing ÷ absolute temperature — how much the vapour space expands each day",
                "**× 1.0** = no additional scaling factor in this simplified form",
                "**÷ mw_vap × 379.48 ÷ 1000** = converts lb/year → lbmol/day → scf/day → MSCFD",
            ],
            ["V_V  = (π÷4) × diameter² × height × (1 − level%) × number_of_tanks",
             "K_E  = temperature_swing_per_day ÷ absolute_temperature",
             "L_S  = 365 × V_V × W_V × K_E   (lb/year)",
             "Q_breathe = L_S ÷ 365 ÷ MW_vapour × 379.48 ÷ 1000  (MSCFD)"],
            f"Vapour space V_V = {f(R['vSpace'],0)} ft³  |  Density W_V = {f(gas_density(R['yVap'],R['tVap'],R['pTankAbs'],p['use_real'])['mass'],4)} lb/ft³  |  K_E = {f(R['kE'],4)}  →  Breathing = {f(R['qBreath'],2)} MSCFD",
            "A big tank battery on a hot Texas day with a 30°F temperature swing can breathe more gas than a small well produces from flash. This is why painting tanks white and insulating them actually reduces VRU load."
        )

    # ── Tab 2: Tank & Relief ──────────────────────────────────────────────
    with tabs[2]:
        st.info("These calculations describe the PRESSURE INSIDE THE TANK and what happens when it gets too high or too low.")

        card(
            "Why does tank pressure change? (The pressure equation)",
            "Tank pressure rises when more gas flows in than the compressor can remove. It falls when the compressor removes more than is being generated. This formula calculates exactly how fast pressure moves.",
            [
                "**dP/dt** = rate of pressure change (psi per minute). 'd' just means 'tiny change in'.",
                "**Z** = real-gas correction factor (from earlier)",
                "**R** = gas constant = 10.7316",
                "**T** = temperature of the vapour space (°R)",
                "**V_V** = vapour space volume (ft³) — the critical denominator. Smaller vapour space = faster pressure swings.",
                "**ṅ_gen** = moles of gas being generated per minute (from flash, working loss, etc.)",
                "**ṅ_air** = moles of air leaking in through the vacuum breaker (ideally zero)",
                "**ṅ_VRU** = moles per minute the compressor is removing",
                "**ṅ_vent** = moles escaping through the PVRV hatch (ideally zero)",
                "**P/T × dT/dt** = extra pressure change from temperature alone — the tank breathes even without any flow",
            ],
            ["dP/dt = (Z×R×T ÷ V_V) × (gas_in − gas_out) + (P÷T) × temperature_change_rate"],
            (lambda g, o: f"Gas in = {f(g,4)} lbmol/min  |  Gas out = {f(o,4)} lbmol/min  |  Net = {f(g-o,4)} lbmol/min")(
                R["qGen"]*1000/MOLVOL/1440, (R["qCap"]+R["qVent"])*1000/MOLVOL/1440),
            "The V_V (vapour space) in the denominator is everything. If your tanks are nearly full of liquid, V_V is tiny — a small gas imbalance moves pressure violently. Full tanks are twitchy tanks. This is why VRU operators watch liquid level carefully."
        )

        card(
            "PVRV — the safety hatch that pops when pressure gets too high",
            "When tank pressure exceeds the PVRV (Pressure-Vacuum Relief Valve) setting, gas escapes to atmosphere. The flow rate depends on how far over the limit you are.",
            [
                "**Q_vent** = venting rate in MSCFD",
                "**C_v** = valve flow coefficient — a fixed number for each valve that describes how much gas can flow through it",
                "**P_tank** = current tank pressure (oz/in²). Note: tanks use ounces, not pounds — 16 oz = 1 psi",
                "**P_pop** = the pressure setting where the valve opens (oz/in²). Typically 16 oz = 1 psi.",
                "**√** = square root. Gas flow through a restriction follows the square root of the pressure difference.",
                "**÷ 1000** = converts to MSCFD",
                "The formula only applies when P_tank > P_pop. When tank pressure is below the pop setting, the valve is closed and Q_vent = 0.",
            ],
            ["Q_vent = C_v × √(P_tank − P_pop) ÷ 1000    (only when P_tank > P_pop)"],
            (f"⚠️ VENTING {f(R['qVent'],1)} MSCFD  |  Losing ${f(R['lostDay'],0)}/day to atmosphere"
             if R["qVent"] > 0 else f"✅ Valve closed  |  {f(p['pPvrv']-p['pTankOz'],2)} oz of margin before it pops"),
            "Every cubic foot that escapes through this valve is gas you were trying to capture and sell. It's also a regulatory emission event. The VRU's entire job is to keep tank pressure low enough that this valve never opens."
        )

        card(
            "Vacuum breaker — what happens if the compressor pulls too hard",
            "If the compressor removes gas faster than it's generated, tank pressure drops below atmospheric. At the vacuum setting, a check valve opens and sucks in outside air. Air + hydrocarbon vapour = potentially explosive mixture.",
            [
                "**Q_air** = air in-leakage rate (MSCFD)",
                "**C_v** = vacuum breaker flow coefficient",
                "**P_vac** = vacuum breaker setting (oz) — typically −6 oz (slightly below atmospheric)",
                "**P_tank** = current tank pressure (oz)",
                "**√** = square root (same physics as the PVRV above)",
                "**LEL** = Lower Explosive Limit — the minimum concentration of hydrocarbon in air to ignite (5% for methane)",
                "**UEL** = Upper Explosive Limit — above this concentration there's not enough oxygen to burn (15% for methane)",
                "A tank vapour space is normally far ABOVE the UEL (too rich to ignite). Admitting air walks the mixture DOWN through the explosive range.",
            ],
            ["Q_air = C_v × √(P_vac − P_tank)    (only when P_tank < P_vac)"],
            f"Q_air = {f(R['qAir'],2)} MSCFD  |  Tank pressure = {f(p['pTankOz'],2)} oz  |  Vacuum setting = {f(p['pVac'],1)} oz",
            "This is the failure mode that makes vapour recovery a safety system, not just a money-saving exercise. An oversized VRU on a marginal well can pull tanks into vacuum repeatedly. That's why the VRX series of small units exists for low-production wells."
        )

    # ── Tab 3: Compressor ──────────────────────────────────────────────────
    with tabs[3]:
        st.info("These calculations describe HOW THE COMPRESSOR WORKS — how much gas it moves, how much power it needs, and why it gets hot.")

        card(
            "How much gas can the compressor actually move?",
            "The compressor has a theoretical maximum (displacement) based on its physical size and speed. But gas leaks back through the tiny gaps between the rotors, reducing actual delivery. Volumetric efficiency is how much you actually get vs how much you theoretically could get.",
            [
                "**V̇_disp** = displacement rate (CFM = cubic feet per minute) — how much volume the rotors sweep per minute if there were no leakage",
                "**V_rev** = displacement per revolution (ft³/rev) — a fixed property of the rotor size",
                "**N** = shaft speed (rpm = revolutions per minute)",
                "**slide/100** = slide valve position as a fraction (100% = fully open, 50% = half capacity)",
                "**η_V** = volumetric efficiency — the fraction of displacement that's actually delivered (0 to 1, or 0% to 100%)",
                "**Q_slip** = slip flow (CFM) — gas leaking backward through rotor tip clearances. This is nearly CONSTANT regardless of speed, which is why slowing down hurts efficiency so much.",
                "**K_s** = slip coefficient — a fixed property of this rotor design",
                "**P_d, P_s** = discharge and suction pressure (psia)",
                "**ρ_s** = gas density at suction conditions (lb/ft³)",
            ],
            ["V̇_disp = V_rev × speed_rpm × (slide_valve ÷ 100)     (theoretical displacement)",
             "Q_slip  = K_s × √( (P_discharge − P_suction) ÷ gas_density )   (leakage back)",
             "η_V     = 1 − (Q_slip ÷ V̇_disp)                               (efficiency)",
             "Q_cap   = V̇_disp × η_V × (pressure correction) × (temperature correction) ÷ 1000   (MSCFD)"],
            f"Displacement = {f(R['dispCfm'],1)} CFM  |  Slip = {f(R['qSlip'],1)} CFM  |  η_V = {f(R['etaV']*100,1)}%  →  Capacity = {f(R['qCap'],1)} MSCFD",
            "The slip is nearly constant with speed. So if you halve the speed, displacement halves but slip stays the same — efficiency collapses. This is the opposite of a piston compressor and it's why screw VRUs need a minimum speed to work properly.",
            chart_fn=lambda: _chart_etav_vs_speed(p, feed_pct)
        )

        card(
            "Vᵢ (built-in volume ratio) — does the compressor match the job?",
            "A screw compressor compresses gas to a ratio set by its physical geometry BEFORE the discharge port opens. If that internal ratio doesn't match what the system actually needs, energy is wasted. This is the most unique — and most misunderstood — aspect of screw compressors.",
            [
                "**Vᵢ** = built-in volume ratio — a fixed geometric property of the rotor design. It's the ratio of the pocket volume when it opens to suction vs when it opens to discharge.",
                "**r_int = Vᵢᵏ** = the pressure ratio the rotors actually compress to internally",
                "**r** = actual system pressure ratio (discharge pressure ÷ suction pressure) — what the system demands",
                "**w_ind** = indicated work per unit volume — energy actually used (includes the mismatch penalty)",
                "**w_isen** = isentropic work — minimum theoretical energy needed",
                "**η_port** = port efficiency = w_isen ÷ w_ind. If r_int = r, η_port = 1.0 (perfect match). Any mismatch reduces it.",
                "**Under-compression**: r > r_int means the gas wasn't compressed enough internally — high-pressure gas blows back when the port opens",
                "**Over-compression**: r < r_int means the gas was compressed too much — energy wasted squeezing it past what was needed",
            ],
            ["r_int  = Vᵢᵏ                    (internal pressure ratio from geometry)",
             "η_port = w_isen ÷ w_ind          (1.0 = perfect, <1.0 = mismatch penalty)",
             "Peak efficiency when: r_int = r  (geometry matches the job)"],
            f"Vᵢ = {f(p['Vi'],2)}  |  Internal ratio = {f(R['rInt'],2)}  |  System ratio = {f(R['r'],2)}  |  Port efficiency = {f(R['etaPort']*100,1)}%  |  {'⚠️ UNDER-compressing' if R['underComp'] else 'Over-compressing'}",
            "This is why a VRU is specified for a specific pressure ratio, not just a flow rate. The same physical machine can be very efficient on a 150 psig sales line and wasteful on a 350 psig line. You can't fix this without changing the rotor set."
        )

        card(
            "Shaft power — how many horsepower does the motor need to supply?",
            "Takes the gas flow rate and the work needed per pound of gas, divides by efficiency, and gives the horsepower the motor or engine must deliver. Exceed the nameplate rating and the overload trips.",
            [
                "**BHP** = brake horsepower — actual shaft power needed at the coupling",
                "**ṁ** = mass flow rate (lb/min) — pounds of gas moving per minute",
                "**H_isen** = isentropic head (ft·lbf/lbm) — the reversible work per pound of gas. Think of it as 'how hard is the compression job'.",
                "**33,000** = conversion factor: 1 horsepower = 33,000 ft·lbf/min",
                "**η_isen** = isentropic efficiency of the compression process (typically 0.70–0.80)",
                "**η_port** = port efficiency from above",
                "**ℓ_mech** = mechanical losses fraction — bearing friction, seal drag, etc. (typically 4–5%)",
                "**BHP_oil** = extra power to circulate the injection oil (small, ~0.35 × gpm)",
                "**H = (R/M) × T_s × Z_avg × (k/(k-1)) × (r^((k-1)/k) − 1)** — the head formula in full",
            ],
            ["H    = (1545 ÷ MW) × T_suction × Z_avg × (k÷(k−1)) × ( (Pd÷Ps)^((k−1)/k) − 1 )",
             "BHP  = (ṁ × H) ÷ (33000 × η_isen × η_port) ÷ (1 − ℓ_mech) + BHP_oil"],
            f"ṁ = {f(R['mDot'],2)} lb/min  |  H = {f(R['head'],0)} ft·lbf/lbm  |  η_total = {f(R['etaTot']*100,1)}%  |  BHP = {f(R['bhp'],1)} of {R['M']['hp']} hp rated ({f(R['hpPct'],0)}%)",
            "This is the number that sizes the motor and the power service. Every inefficiency upstream — mismatched Vᵢ, lost suction pressure, poor volumetric efficiency — shows up here as extra horsepower required.",
            chart_fn=lambda: _chart_bhp_vs_pr(p, feed_pct)
        )

        card(
            "Discharge temperature — why oil-flooded screws can do what dry machines can't",
            "When you compress a gas, it heats up dramatically. Without oil injection, compressing to 350 psig from near-atmospheric would produce temperatures that destroy seals and coke the lubricant. The injected oil absorbs the heat inside the compression chamber, making extreme ratios survivable in one stage.",
            [
                "**T_d** = oil-flooded discharge temperature (°R, subtract 459.67 for °F)",
                "**T_dry** = what the temperature would be with NO oil — the 'dry adiabatic' temperature. For a 20:1 pressure ratio, this is often 500–700°F.",
                "**ṁ_g** = gas mass flow rate (lb/min)",
                "**cp_g** = gas specific heat (Btu/lb·°F) — energy to heat 1 lb of gas by 1°F",
                "**T_s** = suction temperature (°R)",
                "**ṁ_o** = oil mass flow rate (lb/min) = gpm × 7.25 (oil weighs about 7.25 lb/gallon)",
                "**cp_o** = oil specific heat (Btu/lb·°F) — typically 0.46",
                "**T_oil** = oil inlet temperature (°R)",
                "**W_shaft** = shaft work in Btu/min = BHP × 42.408 (1 hp = 42.408 Btu/min)",
                "**The formula is just an energy balance**: all energy in = all energy out",
            ],
            ["T_dry = T_suction × (Pd÷Ps)^((k−1)÷k)          (no oil — would be very hot)",
             "T_d   = (W_shaft + ṁ_gas×cp_gas×T_suction + ṁ_oil×cp_oil×T_oil)",
             "        ÷ (ṁ_gas×cp_gas + ṁ_oil×cp_oil)         (with oil — much cooler)"],
            f"Without oil: {f(R2F(R['tdDry']),0)} °F  |  With oil injection at {f(p['oilGpm'],1)} gpm: {f(R2F(R['td']),0)} °F  |  Oil absorbs the difference",
            "Try dragging the oil circulation slider to zero on the Simulator page. The discharge temperature shoots up toward the dry adiabatic value and the temperature alarm fires. That's exactly why oil-flooded screws dominate vapour recovery — they handle pressure ratios that no dry single-stage machine could survive.",
            chart_fn=lambda: _chart_td_vs_oilgpm(p, feed_pct)
        )

    # ── Tab 4: Heat & Condensate ──────────────────────────────────────────
    with tabs[4]:
        st.info("These calculations describe the AFTERCOOLER — cooling the hot compressed gas and collecting the liquid hydrocarbons that fall out.")

        card(
            "The aftercooler — how well does it cool the gas?",
            "Hot compressed gas passes through a heat exchanger where air cools it down. NTU and effectiveness are standard engineering ways to describe how good that cooling is.",
            [
                "**NTU** = Number of Transfer Units — a dimensionless score for the cooler's size. Higher = more cooling ability. NTU of 1.0 is modest, 3.0 is excellent.",
                "**UA** = U × A — the product of heat transfer coefficient (U, how easily heat flows through the wall) and area (A, how much surface there is). The parameter 'uaCool' in the simulator is this combined value in Btu/hr·°F.",
                "**ṁ·cp** = mass flow rate × specific heat = the gas stream's 'heat capacity rate' (Btu/hr·°F) — how much heat it carries per degree",
                "**ε (epsilon)** = effectiveness — fraction of maximum possible cooling achieved. ε=0.85 means you cool 85% of the way from hot discharge temperature to ambient air temperature.",
                "**T_out** = cooler outlet temperature (°F) — if this is below the hydrocarbon dew point, liquid condenses",
                "**T_air** = ambient air temperature (°F) — the cooler can never cool the gas below this",
                "**Approach temperature** = T_out − T_air. The smaller this gap, the bigger and more expensive the cooler.",
            ],
            ["NTU   = UA ÷ (ṁ × cp)_gas                     (cooler size score)",
             "ε     = 1 − e^(−NTU)                           (effectiveness, 0 to 1)",
             "T_out = T_discharge − ε × (T_discharge − T_air) (outlet temperature)"],
            f"NTU = {f(R['ntu'],2)}  |  Effectiveness = {f(R['effHX']*100,1)}%  |  {f(R2F(R['td']),0)}°F → {f(R2F(R['tCool']),0)}°F  |  Duty = {f(R['duty']/1000,1)} MBtu/hr",
            "In August in Texas, ambient air temperature might be 110°F. That's the floor — no matter how big you build the cooler, you can't get the gas below the air temperature. This is why summer operations produce fewer condensate barrels than winter."
        )

        card(
            "Free barrels — liquid hydrocarbons that fall out of the gas",
            "After compressing and cooling the rich vapour, the heavy molecules (butane, pentane, hexane) prefer to be liquid at the new conditions. They condense in the knockout drum and you collect them as valuable liquid. This is often the best economic justification for a VRU.",
            [
                "**Dew point** = the temperature at which the compressed gas first starts forming liquid droplets — just like the dew point for water in weather forecasts, but for hydrocarbons",
                "**If T_out < dew point** = you are condensing — liquid is forming and you're making barrels",
                "**If T_out > dew point** = all gas, no liquid knockout",
                "**ṅ_liq** = moles per day of liquid condensed (from the flash calculation at cooler exit conditions)",
                "**M_liq** = molecular weight of the condensed liquid",
                "**γ_NGL** = specific gravity of the NGL liquid (typically 0.55–0.70)",
                "**62.37** = density of water (lb/ft³)",
                "**5.6146** = cubic feet per barrel",
                "**q_NGL** = condensate rate in barrels per day",
            ],
            ["Flash the vapour at (T_cooler_outlet, P_discharge) → get liquid fraction",
             "q_NGL = moles_liquid × MW_liquid ÷ (SG_liquid × 62.37 × 5.6146)   (bbl/day)"],
            f"Dew point at {f(R['Pd']-PSTD,0)} psig = {f(R2F(R['dewPd']),0)}°F  |  Cooler outlet = {f(R2F(R['tCool']),0)}°F  |  Condensate = {f(R['nglBbl'],2)} bbl/day = ${f(R['revNgl'],0)}/day",
            "On a rich stream the condensate revenue often exceeds the gas revenue. A VRU that looks marginal on gas price alone can be very profitable when you count the barrels it makes. This is why the aftercooler is not an accessory — it's a revenue-generating separator."
        )

    # ── Tab 5: Combustion ────────────────────────────────────────────────
    with tabs[5]:
        st.info("These calculations apply when the recovered gas is BURNED — either in a gas-engine driver or a flare.")

        card(
            "Heating value — how much energy is in the gas?",
            "Heating value measures how much heat is released when you burn the gas. Tank vapour is much richer in energy than pipeline gas because it contains heavier molecules.",
            [
                "**LHV** = Lower Heating Value (Btu/scf) — energy released per cubic foot of gas, NOT counting the heat from water vapour condensing. This is what engines use.",
                "**HHV** = Higher Heating Value (Btu/scf) — same but DOES count water condensation heat. Usually 5–10% higher than LHV.",
                "**Wobbe Index** = HHV ÷ √SG — a measure of the heat delivered through a fixed orifice. Two gases with the same Wobbe deliver the same heat to a burner. Pipeline gas ≈ 1350. Rich tank vapour ≈ 1800–2200.",
                "**yᵢ** = mole fraction of each component",
                "**LHVᵢ** = heating value of pure component i (methane = 909 Btu/scf, propane = 2315, etc.)",
                "**SG** = specific gravity (from the first tab)",
            ],
            ["LHV_mix = sum of (fraction × heating_value) for each component",
             "HHV_mix = same but using higher heating values",
             "Wobbe   = HHV_mix ÷ √SG"],
            f"LHV = {f(R['lhv'],0)} Btu/scf  |  HHV = {f(R['hhv'],0)} Btu/scf  |  SG = {f(R['sgVap'],3)}  |  Wobbe = {f(R['wobbe'],0)}  (pipeline gas ≈ 1350)",
            "The high Wobbe index of tank vapour is why you can't just pipe it directly into an engine tuned for pipeline gas — it would deliver far too much heat per stroke and potentially damage the engine."
        )

        card(
            "Methane number — will this gas knock the engine?",
            "Just like gasoline has an octane rating to prevent engine knock, gas engines have a methane number requirement. Rich tank vapour rates poorly because heavy hydrocarbons (C4+) cause knock. Below the requirement, the engine self-destructs within days.",
            [
                "**MN** = Methane number — knock resistance rating. Pure methane = 100. Hydrogen = 0. Rich tank vapour = often 30–60.",
                "**y_C1** = methane fraction in the vapour (higher methane = better knock resistance = higher MN)",
                "**y_C2** = ethane fraction (small positive contribution)",
                "**y_C3** = propane fraction (small negative — slightly hurts knock resistance)",
                "**y_C4+** = butane and heavier fraction (large negative — C4+ molecules strongly promote knock)",
                "**y_CO2** = CO2 fraction (positive — inert gases help knock resistance by slowing the flame)",
                "**y_N2** = nitrogen fraction (also positive for same reason)",
                "**Engine requirement (mnReq)** = the minimum MN the engine manufacturer specifies. Typically 50–70.",
            ],
            ["MN ≈ 137.78×methane + 29.95×ethane − 18.19×propane",
             "   − 167.06×(butanes+pentanes+hexane+C7+)",
             "   + 181.23×CO2 + 26.99×N2"],
            f"MN = {f(R['mn'],1)}  |  Engine requires ≥ {p['mnReq']}  |  {'⚠️ KNOCK RISK — derate or blend lean gas' if R['mn'] < p['mnReq'] else '✅ Acceptable'}",
            "This is the hard wall on gas-engine VRUs. The richer the tank vapour (more C4+), the worse the methane number. Solutions: blend with lean pipeline gas, derate the engine compression ratio, or switch to an electric motor. This is why the electric FX/VRX units exist alongside the gas-engine models."
        )

        card(
            "Air-fuel ratio — how much air does the burner need?",
            "Complete combustion requires exactly the right amount of oxygen. Too little and you get soot and CO. Too much and you waste heat but reduce NOx emissions. Lambda (λ) is the ratio of actual air to theoretically perfect air.",
            [
                "**λ (lambda)** = excess air ratio. λ=1.0 means exactly the right amount of air (stoichiometric). λ=1.6 means 60% excess air — common for lean-burn engines to reduce NOx.",
                "**A/F_stoich** = stoichiometric air-fuel ratio — the exact amount of air for perfect combustion",
                "**O₂ demand** = moles of oxygen needed to burn one mole of fuel completely",
                "**0.2095** = fraction of oxygen in dry air (about 21%)",
                "**nC, nH** = number of carbon and hydrogen atoms in each molecule (methane CH4: nC=1, nH=4)",
                "**The combustion reaction**: each carbon atom needs one O₂ to become CO₂. Each pair of hydrogen atoms needs half an O₂ to become H₂O.",
            ],
            ["O₂_needed = sum of (fraction × (carbons + hydrogens÷4)) for each component",
             "A/F_stoich = O₂_needed ÷ 0.2095   (mol air per mol fuel)",
             "A/F_actual = A/F_stoich × λ"],
            f"O₂ demand = {f(R['o2Stoich'],3)} mol/mol  |  A/F stoich = {f(R['afStoichMass'],2)} lb/lb  |  At λ={f(p['lambda'],2)}: {f(R['afActual'],2)} lb air per lb fuel",
            "Rich tank vapour has a higher O₂ demand than pipeline gas because it contains more carbon and hydrogen per mole. An engine sized for pipeline gas will run fuel-rich (not enough air) on tank vapour unless the air system is recalibrated."
        )

    # ── Tab 6: Emissions & Money ──────────────────────────────────────────
    with tabs[6]:
        st.info("These calculations compare the ENVIRONMENTAL IMPACT and ECONOMICS of three options: vent everything, flare everything, or run the VRU.")

        card(
            "CO₂-equivalent — converting methane leaks into a common currency",
            "Methane is a much more potent greenhouse gas than CO₂, but they're measured differently. CO₂-equivalent (CO₂e) converts everything to 'how bad would this be if it were CO₂ instead'. This lets you compare a methane leak to a CO₂ emission.",
            [
                "**CO₂e** = CO₂-equivalent emissions in tonnes per day",
                "**ṁ_CH4** = mass of methane emitted (tonnes/day)",
                "**GWP** = Global Warming Potential of methane = 28 (over 100 years, methane traps 28× more heat than CO₂ per tonne). Over 20 years it's ~82.",
                "**ṁ_CO2,combustion** = CO₂ from burning the gas (each carbon atom in the fuel becomes one CO₂ molecule)",
                "**DRE** = Destruction/Removal Efficiency of the flare. 98% DRE means 2% of the methane escapes unburned.",
                "Three scenarios are compared:",
                "  1. **Vent all** = just open the hatch and release everything. Worst case.",
                "  2. **Flare all** = burn it all at the stack. Better — converts CH4 to CO2 — but imperfect DRE still lets some methane escape.",
                "  3. **Run VRU** = capture and sell the gas. Best case, with only venting losses and engine slip as emissions.",
            ],
            ["CO₂e = methane_mass × GWP + CO₂_from_combustion",
             "Avoided = CO₂e_if_venting − CO₂e_with_VRU"],
            f"If venting all: {f(R['co2eVent'],2)} t CO₂e/day  |  If flaring all: {f(R['co2eFlare'],3)} t CO₂e/day  |  With VRU: {f(R['co2eVru'],3)} t CO₂e/day  |  Avoided: {f(R['co2eAvoid']*365,0)} t/year",
            "The VRU typically avoids 95%+ of the emissions compared to venting. That avoided amount has a dollar value under methane fee programmes — you can see it in the carbon credit line of the economics calculation below."
        )

        card(
            "Daily margin — does this VRU make money?",
            "Takes all the revenue streams (gas sales + condensate + carbon credits) and subtracts all the costs (power + rental). If this number is positive, the VRU pays for itself.",
            [
                "**q_net** = net gas to sales (MSCFD) — recovered gas minus what the engine burns as fuel",
                "**π_gas** = gas price ($/Mcf — dollars per thousand cubic feet)",
                "**q_NGL** = condensate rate (bbl/day)",
                "**π_NGL** = condensate price ($/barrel)",
                "**CO₂e_avoid** = avoided emissions (tonnes CO₂e/day)",
                "**π_CO2** = carbon credit value ($/tonne CO₂e). Zero in most US programmes today, but growing.",
                "**kW** = electrical power draw of the compressor motor",
                "**24** = hours per day",
                "**π_kWh** = electricity price ($/kWh)",
                "**rent × 12/365** = monthly rental rate converted to daily cost",
                "**Net margin** = everything you earn minus everything you spend, per day",
            ],
            ["Net = (gas_sales × gas_price) + (NGL_bbl × NGL_price) + (avoided_CO2e × carbon_price)",
             "    − (kW × 24 × electricity_price) − (monthly_rent × 12 ÷ 365)"],
            f"Gas ${f(R['revGas'],0)} + NGL ${f(R['revNgl'],0)} + carbon ${f(R['credit'],0)} − power ${f(R['costPwr'],0)} − rental ${f(R['costRent'],0)} = **${f(R['netDay'],0)}/day**",
            "The condensate line surprises most people — on a rich stream it often exceeds the gas revenue. A VRU that looks borderline at $3/Mcf gas becomes obviously profitable when you count the barrels of condensate it knocks out of the stream. This is why the aftercooler size matters economically, not just thermally."
        )


# ─────────────────────────────────────────────────────────────────────────────
# Page: Guided Lessons
# ─────────────────────────────────────────────────────────────────────────────
LESSONS = [
    {
        "title": "1 · What is in the vapour",
        "desc":  "Rich tank vapour vs lean pipeline gas.",
        "setup": {"model":"FX12V125","pSep":60,"tSep":95,"tTank":88,"pSales":65,"qLiq":12000,"nTank":6},
        "comp":  None,
        "text": """
**The gas properties tab** will show you something surprising: the live-oil feed is mostly C6+,
but the vapour reaching the VRU is a completely different fluid — around **28–34 lb/lbmol**
compared to methane's 16.

This happens because K-values sort the components: methane's K is in the thousands so almost all
of it leaves the liquid, while C7+ sits near 10⁻⁵ and stays behind.

**Watch:** Drag C3 and nC4 up in the Composition tab. Three things move together:
vapour MW rises, k falls toward 1.1, and LHV climbs past 1600 Btu/scf.
That single composition change is the reason a VRU behaves nothing like a gas-lift compressor.
""",
        "checkpoint": {
            "q": "If you increase propane (C3) in the composition, what happens to vapour MW?",
            "choices": [
                "It increases — heavier molecules raise the average",
                "It decreases — more C3 dilutes the heavy ends",
                "It stays the same — MW is fixed by oil API",
            ],
            "answer": 0,
        },
    },
    {
        "title": "2 · Separator pressure sets your load",
        "desc":  "The cheapest fix for an overloaded VRU isn't a bigger VRU.",
        "setup": {"model":"FX12V125","pSep":180,"tSep":110,"qLiq":12000,"pSales":65,"nTank":6},
        "comp":  None,
        "text": """
Separator is at **180 psig**. Look at the flash-gas figure in the results.

Now drag **Separator pressure** down toward 40 psig. Flash gas collapses — sometimes by half.

**Why:** Gas that stays in solution at high separator pressure has to come out *somewhere*.
If it isn't released at the separator, it shows up in your tank, on the VRU's suction.

This is the most valuable insight in this simulator. When a VRU is chronically overloaded,
the first question is not "what size unit?" — it is "what is the separator doing?"
Every psi you drop there is flash gas captured at high pressure for free
instead of low pressure through a compressor.
""",
        "checkpoint": {
            "q": "If you drop separator pressure from 180 psig to 40 psig, flash gas will:",
            "choices": [
                "Decrease — less pressure differential means less flashing",
                "Increase — lower pressure releases more dissolved gas",
                "Stay the same — flash gas depends only on oil rate",
            ],
            "answer": 1,
        },
    },
    {
        "title": "3 · Ounces, not psi",
        "desc":  "Why nobody in vapour recovery talks in psi.",
        "setup": {"model":"VRX25","pSet":6.0,"pPvrv":16.0,"pVac":-6.0,"qLiq":1200,"pSep":45,"nTank":2},
        "comp":  None,
        "text": """
The entire operating band of this plant is **−6 oz to +16 oz** — from vacuum breaker to thief
hatch. That is **1.4 psi total**.

An atmospheric tank shell yields at a couple of psig. There is no room. So the industry works
in ounces, sixteen to the psi, and a controller that would be considered absurdly tight anywhere
else is just normal here.

Look at the **Tank pressure** readout on the dashboard and notice how close it sits to both
the PVRV setting and the vacuum setting simultaneously. Everything in this system is a fight
to keep that number between the lines.
""",
        "checkpoint": {
            "q": "Why do VRU operators measure tank pressure in ounces, not psi?",
            "choices": [
                "Atmospheric tanks are so thin that the safe operating band is less than 2 psi total — ounces give finer resolution",
                "Ounces are the industry standard for all compression equipment",
                "It is a historical convention with no physical reason",
            ],
            "answer": 0,
        },
    },
    {
        "title": "4 · Undersize it and the hatch pops",
        "desc":  "What insufficient capacity actually looks like.",
        "setup": {"model":"VRX25","qLiq":12000,"pSep":150,"tSep":120,"qBlank":40,
                  "pSet":6.0,"pPvrv":16.0,"nTank":4,"pSales":65},
        "comp":  None,
        "text": """
A **VRX25** (25 hp, ~150 MSCFD rated) has just been handed roughly 500 MSCFD of generation.

Look at the results: load is 100%, capacity is maxed, but it isn't enough. Tank pressure
exceeds the hatch setting at 16 oz and the **VENTING alarm** fires. The dollar figure beside
it is product going to atmosphere per day.

Now change the model to **FX12V125** without touching anything else. Pressure recovers and
venting stops. That gap between the two models is the entire sizing conversation.
""",
        "checkpoint": {
            "q": "When the VRU capacity is less than gas generated, what happens first?",
            "choices": [
                "Tank pressure rises until the PVRV pops, venting gas to atmosphere",
                "The compressor automatically increases speed above rated",
                "The vacuum breaker opens and admits air",
            ],
            "answer": 0,
        },
    },
    {
        "title": "5 · The screw's sweet spot",
        "desc":  "Built-in volume ratio and port mismatch.",
        "setup": {"model":"FX12V125","Vi":3.5,"pSales":150,"pSep":60,"qLiq":12000,"nTank":6},
        "comp":  None,
        "text": """
A screw compresses each pocket of gas to a ratio fixed by its **geometry** — r_int = Vᵢᵏ.
Then the discharge port uncovers, and whatever the system pressure is, the gas equalises
to it instantly. If system pressure is higher, the gas gets compressed the rest of the way
at constant volume — thermodynamically wasteful. If lower, high-pressure gas blows back.

**Go to the Equations → Compressor tab.** Find the port mismatch card.

Experiment:
1. Drag **Vᵢ** from 1.6 to 5.5 and watch `η_port` in the results.
2. Change **discharge pressure** and watch the efficiency peak shift.

A package perfect on a 180 psig sales line is mediocre on 350 psig — same machine, same gas.
""",
    },
    {
        "title": "6 · Why screws won vapour recovery",
        "desc":  "Oil-flooded discharge temperature.",
        "setup": {"model":"FX12V125","pSales":350,"oilGpm":12,"tOil":150,"pSep":60,"qLiq":12000,"nTank":6},
        "comp":  None,
        "text": """
Discharge is at **350 psig** against near-atmospheric suction — a pressure ratio above 20 in
one stage. Look at the two temperatures in the Simulator results:

- **Dry adiabatic** — what the gas would reach with no oil: far past the point where lube cokes,
  seals fail, and you have a fire.
- **Oil-flooded actual** — injected oil absorbs the heat of compression *as it is generated*,
  landing the discharge temperature somewhere survivable.

**Drag oil circulation (oilGpm) to zero.** Watch the actual temperature climb toward the dry
value and the temperature alarm fire. Put it back.

That oil circuit is why single-stage ratios above 20 are routine for a screw, and impossible
for a dry machine. It is also why oil carryover and cooler fouling are the top maintenance items.
""",
    },
    {
        "title": "7 · Slip, and why turndown hurts",
        "desc":  "Volumetric efficiency in a machine with no clearance volume.",
        "setup": {"model":"FX12V125","pSales":250,"kSlip":1.55,"pSep":60,"qLiq":12000,"nTank":6,"load":100},
        "comp":  None,
        "text": """
A screw has no clearance volume. Its losses are **leakage past the rotor tips**, and that
leakage depends on differential pressure and gas density — not speed.

Watch the **Volumetric efficiency** readout:

1. Drag **Speed / load** from 100% down to 30%.
2. Displacement falls in proportion, but slip barely changes.
3. η_V collapses. You lose throughput twice.

This is the opposite of a reciprocating compressor, where volumetric efficiency is roughly
speed-independent. It sets the practical turndown limit and explains why minimum load exists
as a real parameter rather than a formality.
""",
    },
    {
        "title": "8 · VFD against slide valve",
        "desc":  "Two ways to unload, two different bills.",
        "setup": {"model":"FX12V125","pSales":200,"pSep":60,"qLiq":12000,"nTank":6,"load":50},
        "comp":  None,
        "text": """
Both controls cut capacity. They do not cost the same.

**VFD (speed reduction):**
- Displacement falls with speed
- Slip fraction grows (η_V drops)
- Vᵢ stays fixed → η_port stays near peak

**Slide valve:**
- Returns gas to suction *before* compression starts
- Shortens the working rotor, lowering the *effective* Vᵢ
- Drifts off the port-match peak → η_port falls

**Try it:** Set load to 50%. Note *specific power* (BHP/MMSCFD) in the results.
Then change Vᵢ to 1.6 (simulating slide-valve unloading shifting the match point) and compare.

The VFD wins on part-load efficiency. The slide valve wins on cost and simplicity.
That trade-off is why the electric FX/VRX series is built around variable speed.
""",
    },
    {
        "title": "9 · The vacuum trap",
        "desc":  "The failure mode that makes this a safety system.",
        "setup": {"model":"FX20V300","qLiq":400,"pSep":35,"tSep":80,"qBlank":0,
                  "pSet":2.0,"pVac":-6.0,"load":100,"nTank":2},
        "comp":  None,
        "text": """
A 300 hp package on a battery making almost nothing, running at full load.

**Drag tank pressure (pTankOz) down toward −6 oz.** This simulates the compressor pulling
the tank into vacuum faster than gas is generated.

At −6 oz the vacuum breaker opens and admits **air** into a vessel full of hydrocarbon vapour.

A tank vapour space normally sits far *above* the upper explosive limit — too rich to burn.
Admitting air walks the mixture **down** through the flammable range.
Methane's window is 5% to 15%.

This is why oversizing a VRU is not the conservative choice, and why the VRX series exists
for marginal wells rather than fitting everyone with a large unit.
""",
    },
    {
        "title": "10 · How wrong is Z = 1?",
        "desc":  "Ideal gas against Peng-Robinson, in horsepower.",
        "setup": {"model":"FX12V125","pSales":350,"pSep":80,"qLiq":12000,"nTank":6},
        "comp":  {"N2":0.2,"CO2":0.7,"C1":16.0,"C2":9.0,"C3":10.0,"iC4":3.0,"nC4":6.0,
                  "iC5":2.4,"nC5":2.6,"C6":2.2,"C7+":47.9},
        "text": """
A rich vapour compressed to 350 psig. Note the shaft power and Z values in the results.

Now **toggle Peng-Robinson EOS off** (use Ideal) in the Simulator top controls.
Every Z becomes exactly 1.0.

**What changes:**
- At suction (~15 psia) almost anything is nearly ideal — Z ≈ 1.
- At discharge (350 psig) with a rich vapour, Z is noticeably below 1.
- Because ρ = PM/(ZRT), an error in Z is a direct error in the mass you're moving —
  which propagates into head, horsepower, and discharge temperature.

At this duty Z_avg lands near **0.94**. The ideal assumption over-predicts horsepower
by ~5% while under-predicting capacity by ~2%. Five percent is inside most design margins —
but note that the sign depends on composition, pressure, and temperature all at once.
With ideal gas you don't know which way you're wrong.
""",
    },
    {
        "title": "11 · Free barrels",
        "desc":  "Retrograde condensation in the aftercooler.",
        "setup": {"model":"FX12V125","pSales":300,"tAir":70,"uaCool":5000,"pSep":60,"qLiq":14000,"nTank":6},
        "comp":  None,
        "text": """
Compress a rich vapour and cool it, and the heavy ends fall out as liquid.

Look at the **Dew point @ Pd** and **Cooler outlet** values in the results.
If the outlet is below the dew point, you are condensing — and making free barrels.

Note the **Condensate** line: bbl/d, and the NGL revenue beside it.
On a rich stream that number frequently *exceeds* the gas revenue.

**Experiment:**
1. Drag **ambient air temperature** up to 110 °F (August afternoon). Barrels fall.
2. Drag **aftercooler UA** down. They fall further.

The cooler is not an accessory — it is a revenue-generating separator, and it is why
cooler fouling shows up as a liquids problem before it shows up as a temperature alarm.
""",
    },
    {
        "title": "12 · Burning your own product",
        "desc":  "Gas-engine parasitic load and the methane number wall.",
        "setup": {"model":"FX12G","pSales":120,"bsfc":8200,"lambda":1.6,"mnReq":52,
                  "pSep":55,"qLiq":9000,"nTank":6},
        "comp":  None,
        "text": """
Switched to the **gas-driven FX12**. No power needed at the pad — the engine burns
recovered vapour instead. Look at the **Driver fuel** and **Parasitic** readouts.
A real fraction of what you captured goes back into the driver.

Now look at **Methane number**. Rich tank vapour rates terribly because the C4+ term
in that correlation carries a large negative coefficient.
Compare MN against the engine requirement — if you're below it, the knock alarm fires,
and a knocking engine destroys itself in days.

**Drag the composition heavier (more C3, C4, C5)** and watch MN fall further.

This is the hard wall on gas-driven vapour recovery: the fuel you're trying to burn is
the wrong fuel for the engine. Blending with lean residue, derating, or going electric
are the three ways out — which is exactly why the product line splits into electric
VRX/FX and gas FX.
""",
    },
    {
        "title": "13 · The Logix PLC and VFD",
        "desc":  "How the machine controls itself.",
        "setup": {"model": "FX12V125", "pSales": 150, "pSet": 6.0, "pTankOz": 6.0,
                  "load": 75, "qLiq": 8000, "nTank": 4, "pSep": 60},
        "comp":  None,
        "text": """
The Logix PLC is the brain. PT-101 reads tank pressure every second.

**The closed loop:**
1. Tank pressure drifts above setpoint (more gas arriving than leaving)
2. PT-101 signal rises → Logix PLC detects positive error
3. PLC increases VFD frequency → motor speeds up → more displacement → more gas captured
4. Tank pressure returns to setpoint

The reverse happens if pressure drops toward vacuum.

**VFD advantage:** speed changes are smooth and continuous — no banging solenoids, no on/off cycling that hammers the rotor.

**Versatrol** is the backup: a recycle valve the PLC cracks open when even minimum speed is too much capacity for the well — it recirculates compressed gas back to suction, allowing true 100% turndown without stalling.

**Try it:** Set Speed/load to 30% on the Simulator. Watch volumetric efficiency collapse. That collapse is why the PLC never commands below ~40% without also opening Versatrol.
""",
        "checkpoint": {
            "q": "What does the Logix PLC do when tank pressure rises above setpoint?",
            "choices": [
                "Sends a higher speed command to the VFD, increasing compressor throughput",
                "Opens the PVRV to vent excess gas",
                "Reduces VFD speed to avoid overloading the motor",
            ],
            "answer": 0,
        },
    },
    {
        "title": "14 · Multi-Stream™ — two pressures, one unit",
        "desc":  "Flogistix patent: capturing gas from separator and tank simultaneously.",
        "setup": {"model": "FX12V125", "pSales": 200, "pSep": 120, "pTankOz": 6.0,
                  "qLiq": 10000, "nTank": 4, "load": 100},
        "comp":  None,
        "text": """
A typical lease produces gas at two very different pressures simultaneously:
- **Separator gas**: 60–200 psig — from the production separator
- **Tank vapour**: near atmospheric (a few ounces) — from the stock tanks

Traditionally you needed two compressors or wasted energy by throttling the separator gas down to tank pressure before compressing it.

**Multi-Stream™** (Flogistix patent, administered through the Logix PLC):
- Two independent suction headers with separate pressure targets
- The PLC controls a manifold that lets the compressor draw from both sources
- Each stream has its own pressure setpoint; the PLC balances the draw to hold both
- No backflow between streams — the separator cannot blow into the tank header

**The economic case:** one FX12V125 doing the work of two smaller units. Lower rental cost, smaller pad footprint, and the PLC handles the balancing automatically as the well profile changes through the day.

**Notice** in the Dashboard: the total generated gas is the sum of both streams. Multi-Stream captures all of it through a single discharge to the sales line.
""",
        "checkpoint": {
            "q": "What is the key advantage of Multi-Stream™ vs two separate compressors?",
            "choices": [
                "One unit handles both pressure levels simultaneously — lower cost and footprint",
                "Two compressors are always more efficient than one",
                "Multi-Stream only works with gas-engine drivers",
            ],
            "answer": 0,
        },
    },
]

def apply_lesson_setup(lesson):
    setup = lesson["setup"]
    for k, v in setup.items():
        p[k] = v
        if k == "model":
            M = MODELS[v]
            p["disp"] = M["disp"]; p["Vi"] = M["Vi"]; p["oilGpm"] = M["oilGpm"]
    if lesson["comp"]:
        for i, c in enumerate(COMPS):
            feed_pct[i] = lesson["comp"].get(c["id"], feed_pct[i])

def page_lessons():
    st.title("📚 Guided Lessons")
    st.caption("Twelve scenarios in order. Each one isolates a single mechanism so it is unmistakable.")

    if "lesson_idx" not in st.session_state:
        st.session_state["lesson_idx"] = None
    if "completed_lessons" not in st.session_state:
        st.session_state["completed_lessons"] = set()

    col_l, col_r = st.columns([1, 2])

    with col_l:
        st.markdown("**Select a lesson:**")
        for i, lesson in enumerate(LESSONS):
            is_active = st.session_state["lesson_idx"] == i
            done_badge = " ✓" if i in st.session_state["completed_lessons"] else ""
            btn_label = f"{'▶ ' if is_active else ''}{lesson['title']}{done_badge}"
            if st.button(btn_label, key=f"lesson_{i}", use_container_width=True,
                         type="primary" if is_active else "secondary"):
                st.session_state["lesson_idx"] = i
                apply_lesson_setup(lesson)
                st.rerun()

    with col_r:
        idx = st.session_state["lesson_idx"]
        if idx is None:
            st.info("👈 Select a lesson from the list to get started.")
            st.markdown("""
**How to use guided lessons:**
1. Click a lesson title on the left
2. The simulator parameters are automatically configured
3. Read the explanation here
4. Switch to the **Simulator** or **Dashboard** page to interact with the live results
5. Come back here to read the next lesson
""")
        else:
            lesson = LESSONS[idx]
            st.markdown(f"### {lesson['title']}")
            st.caption(lesson["desc"])
            st.divider()
            st.markdown(lesson["text"])
            st.divider()

            # Checkpoint quiz
            if "checkpoint" in lesson:
                chk = lesson["checkpoint"]
                st.markdown("#### 🎯 Checkpoint")
                answer_idx = st.radio(
                    chk["q"],
                    options=list(range(len(chk["choices"]))),
                    format_func=lambda x, c=chk["choices"]: c[x],
                    key=f"chk_{idx}",
                    index=None,
                )
                if answer_idx is not None:
                    if answer_idx == chk["answer"]:
                        st.success("✅ Correct!")
                        st.session_state["completed_lessons"].add(idx)
                    else:
                        st.error("❌ Not quite — review the lesson text and try again.")
                st.divider()

            # Show key live outputs for this lesson
            R = solve(p, feed_pct, p["use_real"])
            st.markdown("**Live results with this lesson's parameters:**")
            c1, c2, c3 = st.columns(3)
            c1.metric("Generated",    f"{f(R['qGen'],1)} MSCFD")
            c2.metric("Recovered",    f"{f(R['qNet'],1)} MSCFD")
            c3.metric("Net margin",   f"${f(R['netDay'],0)}/day")
            c1, c2, c3 = st.columns(3)
            c1.metric("Shaft power",  f"{f(R['bhp'],0)} BHP ({f(R['hpPct'],0)}%)")
            c2.metric("Disch. temp",  f"{f(R2F(R['td']),0)} °F")
            c3.metric("Condensate",   f"{f(R['nglBbl'],2)} bbl/d")

            # Nav buttons
            prev_col, next_col = st.columns(2)
            if idx > 0:
                if prev_col.button("← Previous lesson", use_container_width=True):
                    st.session_state["lesson_idx"] = idx - 1
                    apply_lesson_setup(LESSONS[idx - 1])
                    st.rerun()
            if idx < len(LESSONS) - 1:
                if next_col.button("Next lesson →", use_container_width=True, type="primary"):
                    st.session_state["lesson_idx"] = idx + 1
                    apply_lesson_setup(LESSONS[idx + 1])
                    st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# Page: Glossary
# ─────────────────────────────────────────────────────────────────────────────
GLOSSARY = [
    ("The gas itself", None, None, None),
    ("k — Isentropic exponent",
     "How much a gas heats up when you squish it. Think of a bike pump: pump it fast and the barrel gets hot — that's this number at work.",
     "Lower k = the gas stays cooler when compressed. Rich tank vapour has a lower k than plain methane, which is actually good news for the compressor.",
     None),
    ("M / SG — Molar mass / specific gravity",
     "How heavy the gas molecules are on average, compared to plain air.",
     "Tank vapour is a mix of light gas and heavier stuff, so it weighs more per breath than pipeline gas does.",
     None),
    ("Z — Compressibility factor",
     "A correction number that says 'the simple gas math is off by this much.'",
     "Z below 1 means the real gas is more tightly packed than the textbook formula assumes — so more gas is moving through the pipe than the simple math would guess.",
     None),
    ("K-values / β (beta)",
     "How much of the liquid in the tank turns into gas.",
     "Like popping the cap on a soda — some of what was dissolved in the liquid escapes as gas the instant the pressure drops.",
     None),
    ("Dew point",
     "The temperature where gas starts turning back into liquid droplets.",
     "Same idea as fog forming on a cold window.",
     None),

    ("Where the gas comes from", None, None, None),
    ("Q_gen — Total gas generated",
     "All the gas showing up at the tank, added together from four sources below.",
     None, None),
    ("Q_flash — Flash gas",
     "Gas released the instant oil drops from high pressure (the separator) to low pressure (the tank). Usually the biggest source.",
     None, None),
    ("Q_work — Working loss",
     "Gas pushed out simply because new oil is filling up the tank and shoving the existing vapour out.",
     None, None),
    ("Q_breathe — Breathing loss",
     "Gas that escapes because the tank heats up in the sun and cools at night, like a balloon expanding and shrinking.",
     None, None),
    ("Q_blanket — Blanket gas",
     "Gas deliberately fed into the tank to keep air out, which adds a little extra load.",
     None, None),

    ("The tank", None, None, None),
    ("Ounces vs psi",
     "Storage tanks are built so thin that pressure is measured in ounces, not pounds — 16 ounces to one psi. There's barely half a pound of pressure to work with before something has to give.",
     "It's the difference between measuring with a bathroom scale and a kitchen scale — the tank needs the more sensitive one.",
     None),
    ("PVRV / venting",
     "The tank's safety pop-off valve. If pressure builds too high, it opens and lets gas escape to the air.",
     "Same job as the whistle on a pressure cooker — except every bit of gas that escapes is money and product lost.",
     None),
    ("Vacuum trap / air in-leak",
     "If the compressor pulls too hard it can suck the tank into vacuum and drag outside air in through a breaker valve — dangerous, because now there is oxygen mixed with hydrocarbon vapour.",
     None, None),

    ("The compressor", None, None, None),
    ("Displacement / volumetric efficiency",
     "Displacement is how much gas the compressor could move if nothing leaked. Volumetric efficiency is how much it actually moves once you subtract the gas that slips back past the rotors internally.",
     None, None),
    ("Vᵢ — Built-in volume ratio",
     "How much the compressor's internal shape squeezes the gas before it even opens the exit port. If this doesn't match how much squeezing the job actually needs, energy gets wasted.",
     None, None),
    ("Head",
     "How much work it takes to compress one pound of gas. This is the number that horsepower is built from.",
     None, None),
    ("BHP — Brake horsepower",
     "The actual muscle the motor or engine has to supply to do the compressing.",
     None, None),
    ("Oil-flooded discharge temperature",
     "Screw compressors spray oil inside while compressing, which soaks up the heat like a coolant. That's why they can squeeze gas much harder in one step than a dry compressor could without overheating.",
     None, None),

    ("Cooling & liquids", None, None, None),
    ("NTU / effectiveness",
     "Standard heat-exchanger terms for how good the aftercooler is at pulling heat out of the hot compressed gas using outside air.",
     None, None),
    ("NGL / condensate",
     "As the gas cools and compresses, some of the heavier hydrocarbons fall out as liquid — often valuable, sellable liquid.",
     "Like water condensing on the outside of a cold soda can, except this condensate is worth money.",
     None),
    ("Scrubber",
     "A filter that catches liquid droplets before they can hit and damage the compressor.",
     None, None),

    ("The control system", None, None, None),
    ("PI control (Kp, Ki)",
     "The autopilot that speeds the compressor up or down to hold tank pressure steady. Kp reacts to how far off target you are right now; Ki reacts to how long you've been off target.",
     None, None),
    ("Deadband",
     "A buffer zone around the setpoint so the compressor doesn't switch on and off too rapidly, which would wear it out.",
     None, None),

    ("Burning the gas", None, None, None),
    ("LHV / HHV / Wobbe index",
     "Measures of how much energy is packed into the gas and how a burner will respond to it. Tank vapour is much richer in energy than normal pipeline gas.",
     None, None),
    ("Lambda (λ) / air-fuel ratio",
     "How much air gets mixed with the fuel gas before burning it.",
     None, None),
    ("Flame temperature",
     "How hot the flame burns — hotter flames create more pollution (NOx), so engines add extra air specifically to cool the flame down.",
     None, None),
    ("Methane number",
     "A rating of how likely the gas is to cause engine knock — the same idea as octane rating for gasoline. Rich tank vapour has a low, knock-prone rating.",
     None, None),

    ("Money & emissions", None, None, None),
    ("CO₂e / GWP",
     "A way of converting a methane leak into 'equivalent' CO₂ for reporting, because methane traps far more heat per pound than CO₂ does.",
     None, None),
    ("DRE — Destruction/removal efficiency",
     "How much of the methane a flare actually burns up completely versus lets escape unburned.",
     None, None),
    ("Daily margin",
     "The bottom line: money made from recovered gas and liquid, minus what it costs to run the compressor, per day.",
     None, None),
    ("Specific power (BHP per MMSCFD)",
     "An efficiency scorecard — how much horsepower it costs to move a given amount of gas. Lower is better.",
     None, None),
]

def page_glossary():
    st.title("📖 Glossary")
    st.caption("Plain-English explanations — no equations, just what each term means and why it matters.")

    search = st.text_input("🔍 Search glossary", "").strip().lower()

    for entry in GLOSSARY:
        term, plain, analogy, _ = entry
        # Section headers have no plain text
        if plain is None:
            st.markdown(f"### {term}")
            continue
        if search and search not in term.lower() and search not in plain.lower():
            continue
        with st.expander(f"**{term}**"):
            st.markdown(f'<div class="gplain">{plain}</div>', unsafe_allow_html=True)
            if analogy:
                st.markdown(f'<div class="ganalogy">💡 {analogy}</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Page: 3D View
# ─────────────────────────────────────────────────────────────────────────────
def page_3d():
    import streamlit.components.v1 as components
    import os, json

    st.title("🏗️ 3D Plant View")
    st.caption("Interactive Three.js scene — orbit, pan, zoom, click equipment for tag info.")

    # Load the 3D component HTML
    html_path = os.path.join(os.path.dirname(__file__), "vru_3d_component.html")
    if not os.path.exists(html_path):
        st.error(f"3D component file not found: {html_path}")
        return

    with open(html_path, "r", encoding="utf-8") as fh:
        html_src = fh.read()

    # Inject postMessage call so Streamlit sends live state into the iframe
    R = solve(p, feed_pct, p["use_real"])
    state_json = json.dumps({
        "vru": {
            "pTankOz":   round(p["pTankOz"], 2),
            "qCap":      round(R["qCap"], 1),
            "qVent":     round(R["qVent"], 2),
            "bhp":       round(R["bhp"], 1),
            "td_f":      round(R2F(R["td"]), 1),
            "tCool_f":   round(R2F(R["tCool"]), 1),
            "hpPct":     round(R["hpPct"], 1),
            "load_pct":  round(p["load"], 1),
            "nTank":     int(p["nTank"]),
            "level_pct": round(p["level"], 1),
            "running":   bool(p["running"]),
            "model":     p["model"],
            "pPvrv":     round(p["pPvrv"], 1),
            "pVac":      round(p["pVac"], 1),
            "pSep":      round(p["pSep"], 1),
            "qGen":      round(R["qGen"], 1),
        }
    })
    # Append a tiny script that posts state once the iframe loads
    inject = f"""
<script>
(function sendState() {{
  const payload = {state_json};
  // post to self (the component is in the same document context)
  window.dispatchEvent(new MessageEvent('message', {{data: payload}}));
  // also try parent frames
  try {{ window.parent.postMessage(payload, '*'); }} catch(e) {{}}
}})();
</script>"""
    html_with_state = html_src.replace("</body>", inject + "\n</body>")

    components.html(html_with_state, height=580, scrolling=False)

    st.divider()
    # Live status strip below the 3D view
    st.caption("**Live plant status**")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Tank pressure",  f"{f(p['pTankOz'],1)} oz")
    c2.metric("Recovered",      f"{f(R['qCap'],1)} MSCFD")
    c3.metric("Shaft power",    f"{f(R['bhp'],0)} BHP")
    c4.metric("Disch. temp",    f"{f(R2F(R['td']),0)} °F")
    c5.metric("Venting",        f"{f(R['qVent'],1)} MSCFD",
              delta_color="inverse")
    if R["qVent"] > 0.05:
        st.markdown(
            f'<div class="alarm-red">🚨 VENTING {f(R["qVent"],1)} MSCFD to atmosphere</div>',
            unsafe_allow_html=True
        )


# ─────────────────────────────────────────────────────────────────────────────
# Page: Control System
# ─────────────────────────────────────────────────────────────────────────────
def page_controls():
    st.title("🎛️ Control System")
    st.caption("How the Logix PLC, VFD, and Versatrol work together to hold tank pressure steady.")

    R = solve(p, feed_pct, p["use_real"])
    M = MODELS[p["model"]]

    # ── Status chips ──────────────────────────────────────────────────────────
    chip_css = lambda color, bg: f"background:{bg};border:1px solid {color};color:{color};padding:4px 12px;border-radius:3px;font-size:0.78rem;font-family:monospace;letter-spacing:.08em;margin-right:6px;"
    plc_color  = "#6FBF73" if p["running"] else "#E4572E"
    plc_bg     = "#0E2B14" if p["running"] else "#3A140A"
    vfd_color  = "#F0A227" if p["load"] < 100 else "#6FBF73"
    flux_color = "#5B9BD5"
    chips_html = (
        f'<span style="{chip_css(plc_color, plc_bg)}">⬤ LOGIX PLC — {"RUNNING" if p["running"] else "STOPPED"}</span>'
        f'<span style="{chip_css(flux_color, "#0D1E2F")}">⬤ FLUX SCADA — CONNECTED</span>'
        f'<span style="{chip_css(vfd_color, "#1E1500")}">⬤ VFD — {p["load"]:.0f}% SPEED</span>'
        f'<span style="{chip_css("#8A9AA8", "#1B2530")}">⬤ VERSATROL — {"ACTIVE" if p["load"] < 100 else "FULL LOAD"}</span>'
    )
    st.markdown(chips_html, unsafe_allow_html=True)
    st.divider()

    # ── P&ID schematic (SVG) ──────────────────────────────────────────────────
    tank_pct  = p["pTankOz"]
    tank_col  = "#E4572E" if tank_pct > p["pPvrv"] or tank_pct < p["pVac"] else ("#F0A227" if abs(tank_pct - p["pSet"]) > 4 else "#6FBF73")
    comp_col  = "#E4572E" if R["hpPct"] > 100 else ("#F0A227" if R["hpPct"] > 85 else "#6FBF73")
    td_col    = "#E4572E" if R2F(R["td"]) > 340 else ("#F0A227" if R2F(R["td"]) > 280 else "#6FBF73")
    cool_col  = "#5B9BD5"

    svg = f"""
<svg viewBox="0 0 820 420" xmlns="http://www.w3.org/2000/svg"
     style="width:100%;background:#0C1218;border-radius:6px;border:1px solid #2E3B49">
  <defs>
    <marker id="arr" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
      <polygon points="0 0, 8 3, 0 6" fill="#4FD1C5"/>
    </marker>
    <marker id="arr2" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
      <polygon points="0 0, 8 3, 0 6" fill="#F0A227"/>
    </marker>
  </defs>

  <!-- Tank battery -->
  <rect x="30" y="140" width="90" height="120" rx="4" fill="#1B2530" stroke="{tank_col}" stroke-width="2"/>
  <text x="75" y="135" fill="#8A9AA8" font-size="10" text-anchor="middle" font-family="monospace">TANK BATTERY</text>
  <text x="75" y="175" fill="{tank_col}" font-size="13" text-anchor="middle" font-family="monospace" font-weight="bold">{p['pTankOz']:.1f} oz</text>
  <text x="75" y="192" fill="#8A9AA8" font-size="9" text-anchor="middle" font-family="monospace">tank pressure</text>
  <text x="75" y="218" fill="#8A9AA8" font-size="9" text-anchor="middle" font-family="monospace">PVRV: {p['pPvrv']:.0f} oz</text>
  <text x="75" y="232" fill="#8A9AA8" font-size="9" text-anchor="middle" font-family="monospace">Vac: {p['pVac']:.0f} oz</text>
  <text x="75" y="248" fill="#8A9AA8" font-size="9" text-anchor="middle" font-family="monospace">Set: {p['pSet']:.0f} oz</text>

  <!-- PT transmitter -->
  <circle cx="75" cy="290" r="14" fill="#1B2530" stroke="#F0A227" stroke-width="1.5"/>
  <text x="75" y="295" fill="#F0A227" font-size="9" text-anchor="middle" font-family="monospace">PT-101</text>
  <line x1="75" y1="260" x2="75" y2="276" stroke="#F0A227" stroke-width="1.5"/>

  <!-- Signal line PT → PLC -->
  <line x1="89" y1="290" x2="310" y2="350" stroke="#F0A227" stroke-width="1" stroke-dasharray="4,3"/>
  <text x="185" y="338" fill="#F0A227" font-size="8" font-family="monospace">4-20 mA signal</text>

  <!-- Logix PLC box -->
  <rect x="280" y="340" width="120" height="55" rx="4" fill="#1B2530" stroke="#F0A227" stroke-width="2"/>
  <text x="340" y="358" fill="#F0A227" font-size="10" text-anchor="middle" font-family="monospace" font-weight="bold">LOGIX PLC</text>
  <text x="340" y="372" fill="#8A9AA8" font-size="8" text-anchor="middle" font-family="monospace">Cl.1 Div.2</text>
  <text x="340" y="386" fill="#8A9AA8" font-size="8" text-anchor="middle" font-family="monospace">PID control</text>

  <!-- PLC → VFD signal -->
  <line x1="400" y1="367" x2="490" y2="367" stroke="#4FD1C5" stroke-width="1.5" stroke-dasharray="4,3" marker-end="url(#arr)"/>
  <text x="442" y="360" fill="#4FD1C5" font-size="8" font-family="monospace">speed cmd</text>

  <!-- VFD box -->
  <rect x="490" y="340" width="90" height="55" rx="4" fill="#1B2530" stroke="#4FD1C5" stroke-width="1.5"/>
  <text x="535" y="358" fill="#4FD1C5" font-size="10" text-anchor="middle" font-family="monospace" font-weight="bold">VFD</text>
  <text x="535" y="372" fill="#8A9AA8" font-size="8" text-anchor="middle" font-family="monospace">{p['load']:.0f}% speed</text>
  <text x="535" y="386" fill="#8A9AA8" font-size="8" text-anchor="middle" font-family="monospace">{R['kW']:.0f} kW draw</text>

  <!-- VFD → Motor -->
  <line x1="535" y1="340" x2="535" y2="290" stroke="#4FD1C5" stroke-width="1.5" marker-end="url(#arr)"/>

  <!-- Vapour header pipe: tank → scrubber -->
  <line x1="120" y1="200" x2="240" y2="200" stroke="#4FD1C5" stroke-width="3" marker-end="url(#arr)"/>
  <text x="178" y="193" fill="#4FD1C5" font-size="8" font-family="monospace">{R['qGen']:.1f} MSCFD</text>

  <!-- Scrubber V-201 -->
  <rect x="240" y="165" width="55" height="75" rx="26" fill="#1B2530" stroke="#7A8794" stroke-width="1.5"/>
  <text x="267" y="196" fill="#8A9AA8" font-size="9" text-anchor="middle" font-family="monospace">V-201</text>
  <text x="267" y="210" fill="#8A9AA8" font-size="8" text-anchor="middle" font-family="monospace">scrubber</text>

  <!-- Scrubber → Compressor -->
  <line x1="295" y1="200" x2="390" y2="200" stroke="#4FD1C5" stroke-width="3" marker-end="url(#arr)"/>
  <text x="337" y="193" fill="#4FD1C5" font-size="8" font-family="monospace">{R['Ps']:.1f} psia</text>

  <!-- Compressor C-301 -->
  <ellipse cx="430" cy="200" rx="38" ry="38" fill="#1B2530" stroke="{comp_col}" stroke-width="2"/>
  <text x="430" y="196" fill="{comp_col}" font-size="10" text-anchor="middle" font-family="monospace" font-weight="bold">C-301</text>
  <text x="430" y="210" fill="#8A9AA8" font-size="8" text-anchor="middle" font-family="monospace">{R['bhp']:.0f} BHP</text>
  <text x="430" y="222" fill="#8A9AA8" font-size="8" text-anchor="middle" font-family="monospace">{R['hpPct']:.0f}%</text>

  <!-- Compressor → Aftercooler (hot discharge) -->
  <line x1="468" y1="200" x2="570" y2="200" stroke="#E4572E" stroke-width="3" marker-end="url(#arr)"/>
  <text x="512" y="190" fill="#E4572E" font-size="8" font-family="monospace">{R2F(R['td']):.0f}°F</text>
  <text x="512" y="216" fill="#8A9AA8" font-size="8" font-family="monospace">{R['Pd']-PSTD:.0f} psig</text>

  <!-- Aftercooler E-401 -->
  <rect x="570" y="165" width="80" height="70" rx="4" fill="#1B2530" stroke="{cool_col}" stroke-width="1.5"/>
  <text x="610" y="193" fill="{cool_col}" font-size="9" text-anchor="middle" font-family="monospace">E-401</text>
  <text x="610" y="206" fill="{cool_col}" font-size="8" text-anchor="middle" font-family="monospace">aftercooler</text>
  <text x="610" y="219" fill="#8A9AA8" font-size="8" text-anchor="middle" font-family="monospace">{R2F(R['tCool']):.0f}°F out</text>
  <text x="610" y="229" fill="#8A9AA8" font-size="7" text-anchor="middle" font-family="monospace">ε={R['effHX']*100:.0f}%</text>

  <!-- Aftercooler → Sales -->
  <line x1="650" y1="200" x2="750" y2="200" stroke="#4FD1C5" stroke-width="3" marker-end="url(#arr)"/>
  <text x="698" y="190" fill="#4FD1C5" font-size="8" font-family="monospace">{R['qNet']:.1f} MSCFD</text>
  <text x="750" y="196" fill="#4FD1C5" font-size="9" font-family="monospace">→ SALES</text>

  <!-- NGL drop leg -->
  <line x1="610" y1="235" x2="610" y2="290" stroke="#C2703F" stroke-width="2" marker-end="url(#arr)"/>
  <text x="620" y="270" fill="#C2703F" font-size="8" font-family="monospace">{R['nglBbl']:.2f} bbl/d</text>
  <text x="620" y="282" fill="#C2703F" font-size="8" font-family="monospace">NGL</text>

  <!-- Motor M-301 -->
  <rect x="490" y="255" width="90" height="40" rx="4" fill="#1B2530" stroke="#5B9BD5" stroke-width="1.5"/>
  <text x="535" y="271" fill="#5B9BD5" font-size="9" text-anchor="middle" font-family="monospace">M-301</text>
  <text x="535" y="284" fill="#8A9AA8" font-size="8" text-anchor="middle" font-family="monospace">{M['hp']} hp motor</text>
  <!-- Motor shaft to compressor -->
  <line x1="490" y1="275" x2="468" y2="215" stroke="#5B9BD5" stroke-width="1.5" stroke-dasharray="3,2"/>

  <!-- Flux cloud -->
  <ellipse cx="700" cy="360" rx="70" ry="30" fill="#0D1E2F" stroke="#5B9BD5" stroke-width="1.5" stroke-dasharray="4,3"/>
  <text x="700" y="355" fill="#5B9BD5" font-size="10" text-anchor="middle" font-family="monospace" font-weight="bold">FLUX SCADA</text>
  <text x="700" y="370" fill="#8A9AA8" font-size="8" text-anchor="middle" font-family="monospace">300 KPIs · remote</text>
  <!-- PLC → Flux -->
  <line x1="400" y1="375" x2="628" y2="365" stroke="#5B9BD5" stroke-width="1" stroke-dasharray="3,2"/>

  <!-- Legend -->
  <line x1="30" y1="400" x2="55" y2="400" stroke="#4FD1C5" stroke-width="2.5"/>
  <text x="60" y="404" fill="#4FD1C5" font-size="8" font-family="monospace">vapour / gas</text>
  <line x1="140" y1="400" x2="165" y2="400" stroke="#E4572E" stroke-width="2.5"/>
  <text x="170" y="404" fill="#E4572E" font-size="8" font-family="monospace">hot discharge</text>
  <line x1="260" y1="400" x2="285" y2="400" stroke="#F0A227" stroke-width="1.5" stroke-dasharray="4,3"/>
  <text x="290" y="404" fill="#F0A227" font-size="8" font-family="monospace">4-20mA signal</text>
  <line x1="390" y1="400" x2="415" y2="400" stroke="#5B9BD5" stroke-width="1.5" stroke-dasharray="3,2"/>
  <text x="420" y="404" fill="#5B9BD5" font-size="8" font-family="monospace">comms / data</text>
</svg>"""

    svg = "\n".join(line.strip() for line in svg.splitlines())
    st.markdown(svg, unsafe_allow_html=True)
    st.divider()

    # ── Control loop explainer ────────────────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### How the control loop works")
        st.markdown("""
**1. Sense** — Pressure transmitter PT-101 reads tank pressure every second and sends a 4–20 mA signal to the Logix PLC.

**2. Compare** — The PLC compares the measured pressure to the setpoint (typically +6 oz). The error drives a PID algorithm.

**3. Act** — The PLC sends a speed command to the Variable Frequency Drive (VFD). The VFD changes motor frequency → shaft speed changes → more or less gas is compressed per minute.

**4. Result** — Tank pressure returns toward setpoint. This loop runs continuously, correcting within seconds.

**Versatrol** adds a second unloading path: a recycle valve that bypasses compressed gas back to suction, allowing 100% turndown without stalling the rotor.
""")
    with col2:
        st.markdown("#### Multi-Stream™")
        st.markdown("""
**The problem:** a typical lease has both a production separator (60–200 psig) and a tank battery (near atmosphere). These two sources are at completely different pressures.

**Old approach:** use two separate compressors, or throttle everything to the lower pressure (wasteful).

**Multi-Stream™ (Flogistix patent):** a single Logix PLC controls two independent suction headers at different pressure targets. The compressor uses its Versatrol/VFD to serve both streams simultaneously, pulling down the tank vapour header while also accepting higher-pressure separator gas — without either stream backflowing into the other.

**Why it matters:** one unit does the job of two. Lower capital cost, lower footprint, and the PLC automatically adjusts each stream's contribution as conditions change throughout the day.
""")

    st.divider()
    st.markdown("#### Live control parameters")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tank pressure", f"{p['pTankOz']:.1f} oz", f"{p['pTankOz']-p['pSet']:.1f} oz vs setpoint")
    c2.metric("VFD speed", f"{p['load']:.0f}%", f"{R['rpm']:.0f} rpm")
    c3.metric("Compressor load", f"{R['hpPct']:.0f}%", f"{R['bhp']:.0f} / {M['hp']} hp")
    c4.metric("Flux KPIs", "300 tracked", "98% uptime SLA")


# ─────────────────────────────────────────────────────────────────────────────
# Router
# ─────────────────────────────────────────────────────────────────────────────
if page == "3d":
    page_3d()
elif page == "dashboard":
    page_dashboard()
elif page == "simulator":
    page_simulator()
elif page == "controls":
    page_controls()
elif page == "equations":
    page_equations()
elif page == "lessons":
    page_lessons()
elif page == "glossary":
    page_glossary()
else:
    page_dashboard()
