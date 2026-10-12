---
name: log-meal
description: >
  Use when the user records what they ate: /log, taps "✍️ Log meal" or "✅ ate it",
  sends a photo of their plate, a voice note describing food, or types "I had a
  chicken salad". Estimates calories/macros, writes to food_log, updates the
  pantry, and offers to show today's chart. Also handles barcode/receipt logging.
---

# log-meal

## When to use
- `/log`, "✍️ Log meal", the "✅ ate it" button under a meal reminder.
- A plate photo, a voice note, or free text describing a meal.
- A grocery receipt photo (→ pantry refill + spend tracking).

## Procedure
1. Determine source: photo / text / voice / barcode / receipt.
2. Estimate nutrition:
   - text/voice → model parses items → estimate kcal/macros (note "estimate, tap to correct").
   - **Voice transcript quality gate:** if Telegram/STT text is garbled, internally inconsistent, or not confidently parseable as foods + portions, do **not** estimate or log it. Ask the user to type the meal using a simple template (`غذا / مقدار / اضافه`) or resend a shorter voice note. Bad voice transcripts are a common source of false food logs.
   - plate photo → vision model returns items + portion estimate.
   - barcode → Open Food Facts per-serving macros (most accurate).
   - receipt → extract line items → add to `pantry`, record spend (no macros).
   - receipt → extract line items → add to `pantry`, record spend (no macros).
3. Insert into `food_log` with `verdict='logged'` and the macro fields.
4. If the meal matches a `meal_schedule` row for today, set its `status='cooked'`.
5. Reply with the running daily total vs target, e.g.
   "Logged. Today: 1240/1729 kcal · 489 to go. 💪" and offer "📊 see chart".
6. If the user logs a weight ("82.5 kg"), write `weight_log` instead.

## Connects to
- `charts-dashboard` for the "see chart" follow-up.
- `pantry-sync` reconciles anything the user didn't explicitly log.

## Files
- `shared/db.py`, `shared/nutrition.py`, `shared/reporting.py`
