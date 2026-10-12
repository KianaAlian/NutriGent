---
name: weekly-report
description: >
  Proactive Sunday 20:00 cron (also /report). Aggregates the week into a report
  card — adherence %, average macros vs target, weight trend, safety checks run,
  food waste avoided, money spent — sends the week + month charts and the safety
  donut, runs symptom-food correlation, and optionally recalibrates the calorie
  target from the weight trend.
---

# weekly-report

## When to use
- Cron: Sunday 20:00 (user timezone).
- `/report`, tap "📑 Report".

## Procedure
1. Aggregate `food_log` + `meal_schedule` for the week:
   adherence % (cooked vs planned), avg kcal/macros vs target, # safety checks
   by verdict, estimated waste avoided, estimated spend.
2. Send visuals via `charts-dashboard`:
   ```python
   import reporting
   from telegram_io import send_photo
   send_photo(chat, reporting.week_chart(uid),  "📈 This week")
   send_photo(chat, reporting.month_chart(uid), "🗓 This month")
   send_photo(chat, reporting.week_safety_donut(uid), "🛡 Safety checks")
   ```
3. **Symptom-food correlation:** scan `symptom_log` vs that week's meals; if a
   symptom clusters after a specific ingredient, surface it gently:
   "3 of 4 bloating days followed onion-heavy dinners — want a 2-week low-FODMAP trial?"
4. **Adaptive recalibration (opt-in):** if weigh-ins exist, adjust next week's
   `daily_kcal` from the actual trend, max ±10%/week. Update `dietary_profiles`.
5. One specific suggestion for next week + "your new plan lands tomorrow 09:00".

## Files
- `shared/reporting.py`, `shared/charts.py`, `shared/nutrition.py`, `shared/db.py`
