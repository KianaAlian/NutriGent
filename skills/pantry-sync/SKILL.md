---
name: pantry-sync
description: >
  Autonomous background skill on a cron (Mon/Wed/Fri/Sun 23:00). Reconciles the
  meal schedule with reality, subtracts cooked meals' ingredients from the
  pantry, flags expiring and low-stock items, and writes distilled learnings to
  memory 4x/week. Runs silently unless it needs a quick confirmation.
---

# pantry-sync

## When to use
- Cron: Monday, Wednesday, Friday, Sunday at 23:00 — for every active user.
- This is the 4x/week memory-update cadence.

## Procedure
1. For each `meal_schedule` row since the last sync with `status='planned'`:
   - if the user gave a signal (cooked/skipped) → apply it.
   - else use the onboarding default (assume cooked / assume skipped) OR ask one
     batched question: "Did Tue dinner & Wed lunch happen?" with yes/no buttons.
2. Subtract cooked meals' ingredients from `pantry` (clamp at zero).
3. Expiry pass: items expiring ≤48h → flag for tomorrow's plan (spoilage routing).
4. Low-stock staples (oil, rice, salt) → draft into next week's shopping list.
5. **Memory write (the 4x/week requirement):** append distilled facts only —
   preference events since last sync, adherence %, pantry anomalies
   ("never finishes cucumbers — buy 1 not 3"). Never store raw logs or images.

## Rules
- Stay silent if nothing needs the user. One batched question at most.
- Only conclusions go to memory, keeping it small and privacy-clean.

## Files
- `shared/db.py`
