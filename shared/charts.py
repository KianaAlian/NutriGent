"""
Matplotlib visuals for Telegram. Every function returns a PNG path the bot
sends with send_photo. Headless backend so it runs on a server with no display.
Palette is colorblind-safe; target line is dashed.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import os, datetime as dt

OUT = os.environ.get("DIET_CHART_DIR", "/tmp/diet_charts")
os.makedirs(OUT, exist_ok=True)
OK, OVER, UNDER, TARGET, INK = "#1D9E75", "#E24B4A", "#EF9F27", "#534AB7", "#444441"

def _bar_color(v, target, lo=0.85, hi=1.15):
    if v == 0: return "#D3D1C7"
    r = v/target if target else 0
    return UNDER if r < lo else OVER if r > hi else OK

def _save(fig, name):
    p = os.path.join(OUT, name); fig.savefig(p, dpi=150, bbox_inches="tight",
                                             facecolor="white"); plt.close(fig); return p

def daily_macro_chart(consumed, target, name="today.png"):
    """Horizontal bars: kcal/protein/carbs/fat consumed vs target."""
    # consumed uses 'kcal'; target stores it as 'daily_kcal' — map it here
    keys = [("kcal","daily_kcal","Calories"),("protein_g","protein_g","Protein"),
            ("carbs_g","carbs_g","Carbs"),("fat_g","fat_g","Fat")]
    fig, ax = plt.subplots(figsize=(7,3.2))
    ys = range(len(keys))
    for i,(ck,tk,lbl) in enumerate(keys):
        t = target.get(tk,0); c = consumed.get(ck,0)
        ax.barh(i, t, color="#EDEBE3", height=0.55, zorder=1)
        ax.barh(i, c, color=_bar_color(c,t), height=0.55, zorder=2)
        ax.text(max(c,t)*1.02, i, f"{c:.0f}/{t:.0f}", va="center", fontsize=10, color=INK)
    ax.set_yticks(list(ys)); ax.set_yticklabels([l for *_,l in keys])
    ax.invert_yaxis(); ax.set_xlabel("amount (kcal / grams)")
    ax.set_title("Today's intake vs target", fontsize=13, color=INK, weight="medium")
    for s in ("top","right"): ax.spines[s].set_visible(False)
    return _save(fig, name)

def weekly_calorie_chart(days, kcals, target, name="week.png"):
    """Vertical bars, one per day, dashed target line."""
    fig, ax = plt.subplots(figsize=(7.5,3.6))
    colors = [_bar_color(v, target) for v in kcals]
    ax.bar(days, kcals, color=colors, zorder=2, width=0.6)
    ax.axhline(target, ls="--", lw=1.4, color=TARGET, zorder=3,
               label=f"target {target} kcal")
    avg = round(sum(kcals)/len([k for k in kcals if k]) ) if any(kcals) else 0
    ax.set_title(f"This week — daily calories (avg {avg})", fontsize=13, color=INK, weight="medium")
    ax.set_ylabel("kcal"); ax.legend(frameon=False, fontsize=9)
    for s in ("top","right"): ax.spines[s].set_visible(False)
    for i,v in enumerate(kcals):
        if v: ax.text(i, v+target*0.02, f"{v:.0f}", ha="center", fontsize=9, color=INK)
    return _save(fig, name)

def monthly_trend_chart(dates, kcals, target, weights=None, name="month.png"):
    """Line: daily kcal over the month + 7-day rolling avg; optional weight on twin axis."""
    fig, ax = plt.subplots(figsize=(8,3.8))
    ax.plot(dates, kcals, color="#B4B2A9", lw=1, marker="o", ms=3, label="daily kcal", zorder=2)
    roll = _rolling(kcals, 7)
    ax.plot(dates, roll, color=TARGET, lw=2.2, label="7-day avg", zorder=3)
    ax.axhline(target, ls="--", lw=1.2, color=OK, label=f"target {target}", zorder=1)
    ax.set_ylabel("kcal"); ax.set_title("This month — calorie trend", fontsize=13, color=INK, weight="medium")
    ax.xaxis.set_major_locator(MaxNLocator(8)); ax.tick_params(axis="x", rotation=45, labelsize=8)
    for s in ("top","right"): ax.spines[s].set_visible(False)
    if weights and any(weights):
        ax2 = ax.twinx(); ax2.plot(dates, weights, color=OVER, lw=1.6, marker="s",
                                   ms=3, label="weight (kg)"); ax2.set_ylabel("kg", color=OVER)
        for s in ("top",): ax2.spines[s].set_visible(False)
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    return _save(fig, name)

def adherence_donut(safe, caution, unsafe, name="adherence.png"):
    """Safety-check breakdown for the weekly report card."""
    fig, ax = plt.subplots(figsize=(4.2,4.2))
    vals=[safe,caution,unsafe]; cols=[OK,OVER,UNDER]; labs=["safe","caution","unsafe"]
    vals2=[(v,c,l) for v,c,l in zip(vals,cols,labs) if v>0] or [(1,"#D3D1C7","none")]
    v,c,l=zip(*vals2)
    ax.pie(v, colors=c, wedgeprops=dict(width=0.42, edgecolor="white"),
           startangle=90, labels=l, textprops=dict(fontsize=10,color=INK))
    ax.text(0,0,f"{sum(vals)}\nchecks", ha="center", va="center", fontsize=13, color=INK)
    ax.set_title("Safety checks this week", fontsize=12, color=INK, weight="medium")
    return _save(fig, name)

def _rolling(xs, w):
    out=[]
    for i in range(len(xs)):
        win=[x for x in xs[max(0,i-w+1):i+1] if x]
        out.append(sum(win)/len(win) if win else None)
    return out
