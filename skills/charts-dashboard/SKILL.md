---
name: charts-dashboard
description: >
  Use whenever the user wants to SEE their nutrition data as a visual: the
  /today, /week, /month commands; taps on "📊 Today", "📈 Week", "🗓 Month";
  or phrases like "show my calories", "how am I doing this week", "graph my
  intake", "my macros today". Generates PNG charts with matplotlib and sends
  them to Telegram. Also produces the safety-check donut for the weekly report.
---

# charts-dashboard

## When to use
- `/today` → daily macro bars (calories/protein/carbs/fat vs target).
- `/week` → 7 vertical bars, one per day, dashed target line, weekly average.
- `/month` → 30-day calorie line + 7-day rolling average + weight trend.
- Inside `weekly-report` → the safety-check donut.

## Procedure
```python
import reporting
from telegram_io import send_photo, send_text

# Daily
path, consumed = reporting.today_chart(uid)
send_photo(chat_id, path,
    caption=f"📊 {consumed['kcal']} kcal so far · "
            f"P{consumed['protein_g']} C{consumed['carbs_g']} F{consumed['fat_g']}")

# Weekly
send_photo(chat_id, reporting.week_chart(uid), caption="📈 This week's calories")

# Monthly (with weight overlay if weight_log has data)
send_photo(chat_id, reporting.month_chart(uid), caption="🗓 Your month at a glance")
```

## Color meaning (consistent across every chart)
- 🟢 green bar = within 85–115% of target (on track)
- 🟠 amber bar = under target
- 🔴 red bar = over target
- purple dashed line = your target; purple solid line = 7-day rolling average

## Design notes
- `matplotlib.use("Agg")` — headless, runs on a server with no display.
- Colorblind-safe palette; every number is rounded before it hits the image.
- Charts write to `$DIET_CHART_DIR` (default `/tmp/diet_charts`), filename keyed
  by user id so concurrent users don't collide.
- All data comes from the `food_log` and `weight_log` tables — never hardcoded.

## Files
- `shared/charts.py` — the four plotting functions.
- `shared/reporting.py` — pulls rows from the DB and feeds charts.
- `shared/nutrition.py` — target math (used to draw the target line).

## Proactive use
The `weekly-report` skill calls these on a Sunday cron so the user gets their
week/month charts pushed automatically — they never have to ask.
