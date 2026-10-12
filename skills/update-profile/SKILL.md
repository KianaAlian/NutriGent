---
name: update-profile
description: >
  Use when the user changes their profile: "I'm also allergic to sesame", "new
  goal: gain muscle", "raise my calories", "I went vegan", /profile, tap
  "⚙️ Profile". Patches the profile, RE-SCREENS the active week's plan against
  the new constraints immediately, and invalidates cached recipe screens.
---

# update-profile

## When to use
- Any allergy/intolerance/diet/goal/macro change.
- `/profile`, tap "⚙️ Profile" (view, then optionally edit).

## Procedure
1. Patch `dietary_profiles` (merge JSON arrays for allergies/dislikes/health flags).
2. If a **safety-relevant** field changed (new allergy, higher severity):
   - re-run `safety_verdict()` on every recipe in this week's `meal_schedule`.
   - any recipe now UNSAFE/CAUTION → regenerate that slot (weekly-plan single-meal path)
     and diff the shopping list; message only the changes.
   - clear stale `recipes.gate_screen_json` so future screens recompute.
3. If goal/macros changed → recompute targets with `nutrition.daily_target` and
   confirm; charts and planning pick up the new target automatically.
4. Write a memory line summarizing the change. Confirm with an updated profile card.

## Safety note
Profile safety changes take effect IMMEDIATELY, not next week. Never leave an
unsafe meal on the schedule after a new allergy is added.

## Files
- `shared/db.py`, `shared/safety_gate.py`, `shared/nutrition.py`
