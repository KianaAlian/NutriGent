---
name: daily-nudge
description: >
  Cron-driven proactive skill. Runs at 16:00, 17:30 and 21:30 (user timezone)
  to tell the user what to cook tonight, deliver the scaled recipe, and log the
  result. Also answers /tonight on demand. This is what makes the system feel
  agentic — it messages the user without being asked.
---

# daily-nudge

## When to use
- Cron 16:00 — preview + confirm/swap/tired buttons.
- Cron 17:30 — full recipe with scaled ingredients + numbered steps.
- Cron 21:30 — single gentle nudge if no response; then leave it for pantry-sync.
- `/tonight` or tap "🌙 Tonight" — run the 16:00 step on demand.

## Procedure (16:00)
1. Read tonight's `meal_schedule` row + recipe.
2. Send: "🌙 Tonight: <title> (<min> min, <kcal> kcal). Cooking it, or want the
   10-minute backup?" with `telegram_menu.tonight_actions(date, meal)`.
3. Handle taps:
   - ✅ cook → status stays planned→cooked (confirmed at log time).
   - 🔁 swap → regenerate this one slot (see weekly-plan single-meal regeneration).
   - 😴 tired → hand off to `handle-friction`.

## Procedure (17:30)
1. Send the recipe: ingredients scaled to the user's portion, each checked
   against pantry (✓ have / 🛒 need), numbered steps, one plating tip.
2. Footer: "press ✅ when eaten so I log macros & update your pantry."

## Rules
- One nudge maximum at 21:30. Never spam. Silence → `status='unknown'` for sync.
- Respect `eating_window` and any calendar "eating out" event (skip cooking).

## Files
- `shared/db.py`, `shared/telegram_menu.py`, `shared/telegram_io.py`
