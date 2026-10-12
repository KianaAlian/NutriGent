---
name: handle-friction
description: >
  Use when the user signals they can't follow the plan right now: "I'm tired",
  "no time", "can't be bothered", "eating out", /tired, or "the shop is out of
  X". Pauses tonight's meal, finds a safe fast fallback or a macro-matched
  substitution, reschedules the skipped meal, and rebalances the week. No guilt.
---

# handle-friction

## When to use
- "I'm exhausted / tired / no time / lazy", `/tired`, tap "😴 Too tired".
- "Eating out tonight" → offer the menu-scan (food-safety-check).
- "<ingredient> is sold out" (from the store) → macro-preserving substitution.

## Procedure — tired / no time
1. Mark tonight's `meal_schedule` row `status='skipped'`, log the reason.
2. Scan `pantry` for a SAFE meal cookable in ≤10 minutes (still screen it via
   the gate). Reply with exact 3-4 step instructions.
3. Reschedule the skipped recipe to the next free slot (its ingredients are
   already bought).
4. Rebalance: recompute remaining days so the weekly kcal target still lands,
   within healthy daily bounds (never crash-diet to compensate).

## Procedure — ingredient sold out
1. Identify the recipe + the missing ingredient.
2. Propose a substitution that is (a) safe against the profile, (b) macro-matched,
   (c) within budget: "Get 400 g cod or chicken breast instead — protein matches,
   both safe for you."

## Tone
A skipped meal is a scheduling problem, not a moral failure. Never shame.

## Files
- `shared/safety_gate.py`, `shared/db.py`, `shared/nutrition.py`
