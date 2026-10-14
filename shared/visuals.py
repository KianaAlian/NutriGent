"""
Rich VISUAL CARDS the bot sends to users as images (PNG via Telegram sendPhoto).
Beyond the calorie charts in charts.py, this renders:
  - verdict_card     : a big colored safety verdict (DO NOT EAT / SAFE / ...)
  - meal_plan_card   : the week of meals as a visual grid
  - profile_card     : the user's safety + goal summary
  - shopping_card    : the grocery list grouped by store section
  - day_dashboard    : a compact "today" summary card (kcal ring + macros)
No emoji inside images (they don't render); we use color blocks + ✓ ✗ ⚠ glyphs.
"""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle, Wedge, Rectangle
import os, textwrap

OUT = os.environ.get("DIET_CHART_DIR", "/tmp/diet_charts")
os.makedirs(OUT, exist_ok=True)

INK, MUTE, LINE = "#2C2C2A", "#5F5E5A", "#D3D1C7"
# verdict level -> (band color, light bg, glyph, headline)
LEVELS = {
    "UNSAFE":      ("#E24B4A", "#FCEBEB", "✗", "DO NOT EAT"),
    "CAUTION":     ("#EF9F27", "#FAEEDA", "⚠", "CAUTION"),
    "SAFE":        ("#1D9E75", "#E1F5EE", "✓", "SAFE"),
    "LIKELY_SAFE": ("#1D9E75", "#E1F5EE", "✓", "LIKELY SAFE"),
    "UNVERIFIED":  ("#888780", "#F1EFE8", "?", "CAN'T VERIFY"),
}

def _save(fig, name):
    p = os.path.join(OUT, name)
    fig.savefig(p, dpi=150, bbox_inches="tight", facecolor="white"); plt.close(fig)
    return p

def _card(ax, x, y, w, h, fc="white", ec=LINE, lw=1.0, rad=0.02):
    ax.add_patch(FancyBboxPatch((x, y), w, h, fc=fc, ec=ec, lw=lw,
        boxstyle=f"round,pad=0,rounding_size={rad}", mutation_aspect=1))

REASON_WIDTH = 46  # characters per line that fit the verdict card at 12.5 pt

def wrap_reasons(reasons):
    """-> [(first_line_of_a_reason, text)] so long reasons wrap instead of running off the card."""
    return [(i == 0, line) for r in reasons for i, line in enumerate(textwrap.wrap(r, REASON_WIDTH, break_on_hyphens=False))]

def verdict_card(level, item, reasons, name="verdict.png"):
    band, bg, glyph, head = LEVELS.get(level, LEVELS["UNVERIFIED"])
    fig, ax = plt.subplots(figsize=(6.4, 3.4)); ax.set_xlim(0,1); ax.set_ylim(0,1); ax.axis("off")
    _card(ax, 0.02, 0.02, 0.96, 0.96, fc=bg, ec=band, lw=2)
    ax.add_patch(Rectangle((0.02, 0.74), 0.96, 0.24, fc=band, ec="none"))
    ax.text(0.10, 0.86, glyph, fontsize=40, color="white", ha="center", va="center", weight="bold")
    ax.text(0.20, 0.86, head, fontsize=27, color="white", va="center", weight="bold")
    ax.text(0.06, 0.66, item[:48], fontsize=15, color=INK, va="center", weight="medium")
    y = 0.56
    for first, line in wrap_reasons(reasons)[:5]:
        if first: ax.text(0.06, y, "•", fontsize=14, color=band, va="center", weight="bold")
        ax.text(0.10, y, line, fontsize=12.5, color=INK, va="center"); y -= 0.085
    ax.text(0.06, 0.07, "Assistive tool, not a medical device.\nFor reactions, use emergency meds and call emergency services.",
            fontsize=8, color=MUTE, va="center", style="italic")
    return _save(fig, name)

def day_dashboard(consumed, target, name="dash.png"):
    kc, tk = consumed.get("kcal",0), target.get("daily_kcal",1) or 1
    pct = min(kc/tk, 1.3)
    ring = "#1D9E75" if 0.85 <= kc/tk <= 1.15 else ("#EF9F27" if kc/tk < 0.85 else "#E24B4A")
    fig, ax = plt.subplots(figsize=(6.4, 3.0)); ax.set_xlim(0,2.1); ax.set_ylim(0,1); ax.axis("off")
    cx, cy, R = 0.5, 0.5, 0.36
    ax.add_patch(Wedge((cx,cy), R, 0, 360, width=0.10, fc="#EDEBE3"))
    ax.add_patch(Wedge((cx,cy), R, 90, 90-360*min(pct,1.0), width=0.10, fc=ring))
    ax.text(cx, cy+0.04, f"{kc:.0f}", fontsize=23, ha="center", va="center", color=INK, weight="bold")
    ax.text(cx, cy-0.12, f"/ {tk:.0f} kcal", fontsize=11, ha="center", va="center", color=MUTE)
    macros = [("Protein", consumed.get("protein_g",0), target.get("protein_g",1),"#534AB7"),
              ("Carbs",   consumed.get("carbs_g",0),   target.get("carbs_g",1),  "#185FA5"),
              ("Fat",     consumed.get("fat_g",0),     target.get("fat_g",1),    "#BA7517")]
    y = 0.78
    for lbl, c, t, col in macros:
        ax.text(1.06, y+0.03, lbl, fontsize=11, color=MUTE)
        ax.text(2.02, y+0.03, f"{c:.0f}/{t:.0f} g", fontsize=11, color=INK, ha="right")
        ax.add_patch(Rectangle((1.06, y-0.04), 0.96, 0.035, fc="#EDEBE3"))
        ax.add_patch(Rectangle((1.06, y-0.04), 0.96*min(c/(t or 1),1.0), 0.035, fc=col))
        y -= 0.22
    ax.text(0.04, 0.96, "Today", fontsize=14, color=INK, weight="medium", va="top")
    return _save(fig, name)

def meal_plan_card(days, name="plan.png"):
    """days: [{'day':'Mon','title':..,'kcal':..,'minutes':..,'tag':'leftover'|None}]"""
    n = len(days); fig, ax = plt.subplots(figsize=(6.6, 0.62*n+0.7))
    ax.set_xlim(0,1); ax.set_ylim(0,n); ax.axis("off")
    ax.text(0.03, n+0.35, "Your week", fontsize=15, color=INK, weight="medium")
    for i, d in enumerate(days):
        y = n-1-i
        _card(ax, 0.02, y+0.08, 0.96, 0.82, fc="white", ec=LINE, lw=0.8, rad=0.015)
        ax.add_patch(Rectangle((0.02, y+0.08), 0.012, 0.82, fc="#534AB7", ec="none"))
        ax.text(0.06, y+0.5, d["day"][:3], fontsize=12, color="#534AB7", va="center", weight="bold")
        ax.text(0.17, y+0.58, d["title"][:40], fontsize=12, color=INK, va="center", weight="medium")
        sub = f"{d.get('minutes','?')} min  ·  {d.get('kcal','?')} kcal"
        if d.get("tag"): sub += f"  ·  {d['tag']}"
        ax.text(0.17, y+0.30, sub, fontsize=9.5, color=MUTE, va="center")
    return _save(fig, name)

def profile_card(p, name="profile.png"):
    allergies = p.get("allergies", [])
    fig, ax = plt.subplots(figsize=(6.4, 3.6)); ax.set_xlim(0,1); ax.set_ylim(0,1); ax.axis("off")
    _card(ax, 0.02, 0.02, 0.96, 0.96, fc="white", ec=LINE, lw=1)
    ax.add_patch(Rectangle((0.02, 0.80), 0.96, 0.18, fc="#534AB7", ec="none"))
    ax.text(0.06, 0.89, p.get("name","Your profile"), fontsize=18, color="white", va="center", weight="bold")
    sev_col = {"anaphylactic":"#E24B4A","severe":"#E24B4A","moderate":"#EF9F27","mild":"#BA7517"}
    ax.text(0.06, 0.71, "Allergies", fontsize=11, color=MUTE, va="center", weight="medium")
    x = 0.06; yy = 0.62
    for a in allergies[:8]:
        c = sev_col.get(a.get("severity","moderate"), "#888780")
        label = f"{a['allergen']} ({a.get('severity','?')[:4]})"
        chip_w = 0.035 + len(label)*0.0145 + 0.025
        if x + chip_w > 0.94:
            x = 0.06; yy -= 0.10
        ax.add_patch(Circle((x+0.012, yy), 0.011, fc=c, ec="none"))
        ax.text(x+0.035, yy, label, fontsize=10.5, color=INK, va="center")
        x += chip_w
    rows = [("Diet", p.get("diet_type","—")), ("Goal", p.get("goal","—")),
            ("Daily target", f"{p.get('daily_kcal','—')} kcal"),
            ("Macros", f"P{p.get('protein_g','—')} C{p.get('carbs_g','—')} F{p.get('fat_g','—')} g"),
            ("Max cook time", f"{p.get('max_cook_minutes','—')} min")]
    y = 0.40
    for k,v in rows:
        ax.text(0.06, y, k, fontsize=11, color=MUTE, va="center")
        ax.text(0.94, y, str(v), fontsize=11, color=INK, va="center", ha="right", weight="medium")
        ax.plot([0.06,0.94],[y-0.035,y-0.035], color="#F1EFE8", lw=0.8); y -= 0.072
    return _save(fig, name)

def shopping_card(sections, name="shop.png"):
    """sections: {'Produce':[('spinach','200 g'),...], 'Dairy':[...]}"""
    total = sum(len(v) for v in sections.values())
    fig, ax = plt.subplots(figsize=(6.4, 0.34*total + 0.42*len(sections) + 0.7))
    H = total*0.34 + len(sections)*0.42 + 0.6
    ax.set_xlim(0,1); ax.set_ylim(0,H); ax.axis("off")
    ax.text(0.04, H-0.3, "Shopping list", fontsize=15, color=INK, weight="medium")
    y = H-0.7
    for sec, items in sections.items():
        ax.add_patch(Rectangle((0.03,y-0.02),0.94,0.30, fc="#F1EFE8", ec="none"))
        ax.text(0.05, y+0.13, sec, fontsize=11.5, color="#534AB7", va="center", weight="bold")
        y -= 0.42
        for nm, qty in items:
            ax.text(0.07, y, "○", fontsize=11, color=MUTE, va="center")
            ax.text(0.11, y, nm[:34], fontsize=11, color=INK, va="center")
            ax.text(0.95, y, qty, fontsize=10.5, color=MUTE, va="center", ha="right")
            y -= 0.34
    return _save(fig, name)
