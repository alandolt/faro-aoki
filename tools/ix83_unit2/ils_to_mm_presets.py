"""Convert MetaMorph illumination settings (.ILS) into a Micro-Manager "Channel" config group.

Usage:
    python ils_to_mm_presets.py illuminationsettings.ILS IX83Lumencor2.cfg

Edits the cfg in place: relabels Dichroic 1/2, Filter Wheel 1/2 and Polarizer with the
names from the MetaMorph hardware profile (see NAMES), applies the fixes listed at
"Fixes applied to the MetaMorph settings" and
(re)writes the System/Startup preset (opens EpiShutter 1/2, camera port), the Binning and
Objective groups (objective + condenser DIC prism, see OBJECTIVES) and the Channel group
(all illumination settings) under "# Configuration presets". The per-experiment subset
groups FRET and Multicolor are off (see EXPERIMENT_GROUPS).
Safe to rerun: the block between the generated header and end marker is replaced.
Warnings about settings that could not be mapped are printed.
"""

import re, sys

ils, cfg = sys.argv[1], sys.argv[2]
HEADER = "# Channel presets converted from MetaMorph illuminationsettings.ILS"
END = "# End of presets converted from MetaMorph"
txt = open(ils, encoding="latin-1").read()
settings = {}
for m in re.finditer(r'"Setting", \d+, "(.*?)"\s*$', txt, re.M):
    parts = m.group(1).split("*")
    name = None
    comps = {}
    for p in parts:
        if p.startswith("stSettingName^"):
            name = p.split("^", 1)[1]
        elif p.startswith("ComponentName^"):
            f = p.split("^")
            d = dict(zip(f[0::2], f[1::2]))
            comps[d["ComponentName"]] = float(d["ComponentState"])
    if comps:
        settings[name] = comps

POS = {
    "Olympus Mirror Unit 1": "Dichroic 1",
    "Olympus Mirror Unit 2": "Dichroic 2",
    "Olympus Fast Filter Wheel 1": "Filter Wheel 1",
    "Olympus Fast Filter Wheel 2": "Filter Wheel 2",
}
LE = {"Red": "Red", "Green": "Green", "Cyan": "Cyan", "UV": "Violet", "Blue": "Blue"}

# Position names from the live MetaMorph hardware profile C:\MM\Hardware\Default\hwprofile.xml
# (POSLABEL-1..n, index 0 = position 1). Empty list = no names there, use Pos-N.
NAMES = {
    # Mirror Unit 1: no labels in MetaMorph; checked on the scope: only pos 8 holds a cube
    "Dichroic 1": ["Empty"] * 7 + ["IX3-FDICT"],
    "Dichroic 2": [
        "Others-Di01",
        "Glass-BK7",
        "FF458-Di02",
        "NONE",
        "NONE",
        "NONE",
        "NONE",
        "NONE",
    ],
    "Filter Wheel 1": ["Pos 1", "543/3", "580/20", "Pos 4", "Pos 5", "Pos 6", "Pos 7"],
    "Filter Wheel 2": [
        "445/40",
        "483/32",
        "520/28",
        "563/9",
        "641/75",
        "664over",
        "free",
    ],
    "Polarizer": ["In", "Out"],
}


def label(dev, idx):
    names = NAMES[dev]
    return f"{idx + 1}-{names[idx]}" if idx < len(names) else f"Pos-{idx + 1}"


LEVEL_MAX = 99  # Spectra <Color>_Level range in Micro-Manager is 0-99
# False: presets only select the LED (<Color>_Enable); the power (<Color>_Level) is set
# per experiment (faro PowerChannel), not stored in the cfg. True: copy MetaMorph's intensities.
WRITE_LEVELS = False
LAMP = "TransmittedIllumination 2"  # halogen (DIA2 in Olympus.ini), Brightness 0-255

# Fixes applied to the MetaMorph settings before the conversion (were hand edits in
# testv1pvcamix83.cfg). Cube/filter positions checked against AokiLab_Microscope.xlsx,
# sheet IX83-弐号機.
MU1, MU2 = "Olympus Mirror Unit 1", "Olympus Mirror Unit 2"
FW1, FW2 = "Olympus Fast Filter Wheel 1", "Olympus Fast Filter Wheel 2"
MU2_DEFAULT = (
    0  # 1-Others-Di01 multiband, the cube of the plain (non _glass/_Di02) settings
)
FW2_OPEN = 6  # 7-free, no emission filter
GLASS_COPIES = [
    "BFP_pHluorin2",
    "GFP_QUEEN",
]  # also add <name>_glass (Dichroic 2 = 2-Glass-BK7)
fixes = []
POL = "Olympus Polarizer"
# napari-micromanager (pymmcore-widgets PresetsWidget) drops every (device, property) that the
# first preset of a group does not set, so all presets of a group must set the same properties.
# Values for the properties a setting does not care about:
FW1_OPEN = 0  # 1-Pos 1, no excitation filter (transmitted light)
POL_OUT = 1  # 2-Out (fluorescence)
for name, c in settings.items():
    if c.get("Olympus Trans Shutter", 0) >= 1:
        # transmitted light: open excitation and emission wheel
        if c.get(FW1, FW1_OPEN) != FW1_OPEN or FW1 not in c:
            c[FW1] = FW1_OPEN
            fixes.append(f"{name}: Filter Wheel 1 set to 1-Pos 1 (transmitted light)")
        if FW2 not in c:
            c[FW2] = FW2_OPEN
            fixes.append(f"{name}: Filter Wheel 2 set to 7-free")
    else:
        if MU2 not in c:
            c[MU2] = MU2_DEFAULT
            fixes.append(
                f"{name}: Mirror Unit 2 not set in MetaMorph, set to 1-Others-Di01"
            )
        c.setdefault(POL, POL_OUT)
    # Mirror Unit 1 pos 1-7 are all empty: use pos 1 so the turret does not move between channels
    if MU1 in c and c[MU1] != 0 and NAMES["Dichroic 1"][int(c[MU1])] == "Empty":
        fixes.append(
            f"{name}: Dichroic 1 {label('Dichroic 1', int(c[MU1]))} -> 1-Empty"
        )
        c[MU1] = 0
for name in GLASS_COPIES:
    settings[f"{name}_glass"] = {**settings[name], MU2: 1}
    fixes.append(f"{name}_glass: added, copy of {name} on 2-Glass-BK7")
# No phase annulus in the condenser and no phase objective: MetaMorph's Trans_PH is brightfield.
# Brightfield = polarizer and analyzer (Dichroic 1 8-IX3-FDICT) out. The condenser DIC prism
# set by the Objective group can stay in: its shear is below the resolution limit.
if "Trans_PH" in settings:
    bf = settings.pop("Trans_PH")
    bf["Olympus Polarizer"] = 1
    bf[MU1] = 0
    settings["Trans_BF"] = bf
    fixes.append(
        "Trans_PH: renamed to Trans_BF, Polarizer 2-Out, Dichroic 1 1-Empty (no analyzer)"
    )

# Objective group: objective + its condenser DIC prism (the prism must match the objective).
# Channel presets do not touch objective or condenser, so both groups combine freely.
# Labels are the ones the stand reports (Objective 6 hand-fixed to UPLXAPO100XO in the cfg).
OBJECTIVES = {  # preset: (Objective label, Condenser turret label)
    "10x": ("1-UPLXAPO10X", "1-NONE"),  # no DIC prism for the 10x
    "20x": ("2-UPLXAPO20X", "3-IX2-DIC20"),
    "40x": ("3-UPLXAPO40X", "4-IX2-DIC40"),
    "60xO": ("4-UPLXAPO60XO", "5-IX2-DIC60"),
    "40xO": (
        "5-UPLXAPO40XO",
        "4-IX2-DIC40",
    ),  # to check on the scope: is DIC40 right for the oil 40x?
    "100xO": ("6-UPLXAPO100XO", "6-IX2-DIC100"),
}

lines = [
    HEADER,
    "# Turret/wheel positions are index-exact; names from MetaMorph hwprofile.xml (Pos-N = no name known).",
    (
        f"# Lumencor intensity: MetaMorph 0-255 converted to Spectra <Color>_Level 0-{LEVEL_MAX}."
        if WRITE_LEVELS
        else "# Lumencor power is not stored here: presets only select the LED, set <Color>_Level per experiment."
    ),
    "",
    "# MetaMorph keeps Olympus Fluor Shutter 1+2 always open and switches the LEDs:",
    "# open both epi shutters at startup, the Spectra is the core shutter for fluorescence.",
    "ConfigGroup,System,Startup,EpiShutter 1,State,1",
    "ConfigGroup,System,Startup,EpiShutter 2,State,1",
    "# Halogen dark at startup (the adapter has no on/off, only Brightness 0-255). Set one",
    "# brightness at the start of an experiment (Halogen slider in faro-napari) and keep it;",
    "# BF and DIC differ by exposure time. DiaShutter closed: the Trans_* presets open it.",
    f"ConfigGroup,System,Startup,{LAMP},Brightness,0",
    "ConfigGroup,System,Startup,DiaShutter,State,0",
    "# Camera is on the left port; the eyepiece or 50/50 port would image black or at half intensity.",
    "ConfigGroup,System,Startup,Light Path,Label,1-LeftPort",
    "",
    "ConfigGroup,Binning,1x1,Camera-1,Binning,1x1",
    "ConfigGroup,Binning,2x2,Camera-1,Binning,2x2",
    "",
    "# ===== Group Objective: objective + matching condenser DIC prism =====",
    *[
        l
        for p, (obj, cond) in OBJECTIVES.items()
        for l in (
            f"ConfigGroup,Objective,{p},Objective,Label,{obj}",
            f"ConfigGroup,Objective,{p},Condenser turret,Label,{cond}",
        )
    ],
    "",
]
warn = []
VARIANT = {"": 0, "glass": 1, "Di02": 2}


def order(name):
    """Fluorescence sorted by emission filter, then base name, then plain/glass/Di02; transmitted last."""
    c = settings[name]
    trans = c.get("Olympus Trans Shutter", 0) >= 1
    em = int(c.get("Olympus Fast Filter Wheel 2", 99))
    base, _, var = (
        name.rpartition("_") if name.rsplit("_", 1)[-1] in VARIANT else (name, "", "")
    )
    return (trans, em, base.lower(), VARIANT.get(var, 0), name.lower())


# Off: napari-micromanager cannot mix channel groups in one acquisition, so every channel
# is picked from "Channel" (it already holds all presets). Set to EXPERIMENT_GROUPS_SUBSETS
# to write the subset groups again.
EXPERIMENT_GROUPS_SUBSETS = {
    "FRET": (
        "CFP/YFP FRET biosensor on FF458-Di02, plus markers on Multi/Glass",
        [
            "CFP_Di02",
            "FRET_Di02",
            "GFP",
            "RFP",
            "RFP_glass",
            "iRFP",
            "iRFP_Di02",
            "Trans_DIC",
        ],
    ),
    "Multicolor": (
        "multicolour on the Others-Di01 multiband dichroic",
        [
            "BFP",
            "GFP",
            "RFP",
            "iRFP",
            "405ex_520em",
            "Trans_DIC",
            "Trans_DIC_G",
            "Photoconversion_UV",
        ],
    ),
}
EXPERIMENT_GROUPS = {}

# Channel groups: group: (description, include transmitted-light presets, halogen State or None).
# None: presets do not touch the halogen. The IX83 adapter has no lamp on/off property
# (TransmittedIllumination 2 only has Brightness), so the lamp is dark after Startup
# (Brightness 0); the user sets one brightness per experiment and never per frame.
# The halogen burns during the fluorescence frames too, so every epi preset closes
# DiaShutter (else stray transmitted light if it was left open, e.g. by hand or after
# startup). Trans_* presets open it, so live view keeps its light when switching presets;
# in an MDA autoshutter closes it again after the frame.
CHANNEL_GROUPS = {
    "Channel": (
        "all channels (epi + BF/DIC); halogen at one brightness per experiment, "
        "DiaShutter closed by the epi presets",
        True,
        None,
    ),
}

presets = (
    {}
)  # name: (section header, transmitted?, [(device, property, value)] without the halogen State)
for name in sorted(settings, key=order):
    c = settings[name]
    out = []
    trans, em = order(name)[:2]
    head = (
        "# --- Transmitted light ---"
        if trans
        else (
            f"# --- Emission {NAMES['Filter Wheel 2'][em]} ---"
            if em < 99
            else "# --- No emission filter set ---"
        )
    )
    out.append(("Polarizer", "Label", label("Polarizer", int(c[POL]))))
    for k, dev in POS.items():
        out.append((dev, "Label", label(dev, int(c[k]))))
    active = [col for col in LE if c.get(f"Lumencor {col} Shutter") == 1]
    if active or not trans:
        if not active:
            warn.append(f"{name}: fluorescence setting without an active LED")
        out.append(("Core", "Shutter", "Spectra"))
    else:
        out.append(("Core", "Shutter", "DiaShutter"))
    out.append(("DiaShutter", "State", "1" if trans and not active else "0"))
    for col in ["Red", "Green", "Cyan", "UV", "Blue"]:
        out.append(("Spectra", f"{LE[col]}_Enable", "1" if col in active else "0"))
    out.append(("Spectra", "Teal_Enable", "0"))
    if active:
        for col in active if WRITE_LEVELS else []:
            k = f"Lumencor {col} Intensity"
            if k in c:
                out.append(
                    ("Spectra", f"{LE[col]}_Level", str(round(c[k] / 255 * LEVEL_MAX)))
                )
            else:
                warn.append(f"{name}: no intensity stored for active {col} line")
        for k in c if WRITE_LEVELS else []:
            if k.endswith("Intensity") and k.split()[1] not in active:
                warn.append(
                    f"{name}: has {k}={c[k]:g} but that line is not active (ignored)"
                )
    elif (
        WRITE_LEVELS and "Olympus Halogen Light Level" in c
    ):  # MetaMorph percent -> IX83 0-255
        out.append(
            (
                LAMP,
                "Brightness",
                str(round(c["Olympus Halogen Light Level"] / 100 * 255)),
            )
        )
    same = [n for n, (_, _, o) in presets.items() if o == out]
    if (
        same
    ):  # kept: the names are used by experiments; napari-micromanager shows the first match
        warn.append(
            f"{name}: same hardware settings as {same[0]} (MetaMorph only differed in power)"
        )
    presets[name] = (head, trans, out)

for group, (desc, with_trans, lamp) in CHANNEL_GROUPS.items():
    lines += [f"# ===== Group {group}: {desc} ====="]
    section = None
    for name, (head, trans, out) in presets.items():
        if trans and not with_trans:
            continue
        if head != section:
            lines.append(head)
            section = head
        for dev, prop, val in out + (
            [(LAMP, "State", lamp)] if lamp is not None else []
        ):
            lines.append(f"ConfigGroup,{group},{name},{dev},{prop},{val}")
        lines.append("")
    lines.append("")

# Per-experiment channel groups, from the channel combinations in the saved MetaMorph
# MDA states (mm\NDSTATE\<user>\*.MDS). Same presets as in Channel, only a subset.
for group, (desc, names) in EXPERIMENT_GROUPS.items():
    lines += ["", f"# ===== Group {group}: {desc} ====="]
    for name in names:
        if name not in presets:
            sys.exit(f"{group}: preset {name} not in {ils}")
        for dev, prop, val in presets[name][2]:
            lines.append(f"ConfigGroup,{group},{name},{dev},{prop},{val}")
        lines.append("")
lines.append(END)

src = open(cfg, encoding="utf-8").read().splitlines()
# drop the block written by a previous run (HEADER ... END)
if HEADER in src:
    if END not in src:
        sys.exit(
            f"{cfg}: found '{HEADER}' but no '{END}', fix by hand or start from the original cfg"
        )
    src = src[: src.index(HEADER)] + src[src.index(END) + 1 :]
if "# Configuration presets" not in src:
    sys.exit(f"{cfg}: no '# Configuration presets' line, nothing would be written")
if END in src:
    sys.exit(f"{cfg}: stray '{END}' without '{HEADER}', fix by hand")
new = []
for l in src:
    m = re.match(r"Label,(Dichroic [12]|Filter Wheel [12]|Polarizer),(\d+),", l)
    if m:
        l = f"Label,{m.group(1)},{m.group(2)},{label(m.group(1), int(m.group(2)))}"
    new.append(l)
    if l == "# Configuration presets":
        new += lines
# every Label a preset uses must exist in the cfg, else Micro-Manager fails to load it
known = set(re.findall(r"^Label,(.+?),\d+,(.+)$", "\n".join(new), re.M))
used = set(
    re.findall(r"^ConfigGroup,[^,]+,[^,]+,(.+?),Label,(.+)$", "\n".join(lines), re.M)
)
if used - known:
    sys.exit(f"{cfg}: presets use unknown labels: {sorted(used - known)}")
# every preset of a group must set the same (device, property) set (see POL above)
props = {}
for g, p, d, pr in re.findall(
    r"^ConfigGroup,([^,]+),([^,]+),(.+?),([^,]+),[^,]*$", "\n".join(lines), re.M
):
    props.setdefault(g, {}).setdefault(p, set()).add((d, pr))
for g, ps in props.items():
    first = next(iter(ps.values()))
    bad = {p: sorted(s ^ first) for p, s in ps.items() if s != first}
    if bad:
        sys.exit(f"{cfg}: group {g} has presets with different properties: {bad}")
open(cfg, "w", encoding="utf-8", newline="\r\n").write("\n".join(new) + "\n")
for title, msgs in [("Fixes", fixes), ("Warnings", warn)]:
    if msgs:
        print(f"{title}:\n  " + "\n  ".join(msgs))
