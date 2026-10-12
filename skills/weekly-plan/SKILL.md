---
name: weekly-plan
description: >
  Use on the Sunday 09:00 cron, on "plan my week" / /plan, or after a profile
  change that invalidates the current plan. Generates a 7-day, allergy-safe,
  macro-targeted meal plan that uses up expiring pantry items first, chains
  leftovers, and respects the calendar. Every generated recipe is re-screened
  through the safety gate before it may enter the schedule.
---

# weekly-plan

## When to use
- Cron: Sunday 09:00 (user timezone).
- "plan my week", `/plan`, tap "🍽 My plan".
- After `update-profile` changes allergies/goal.

## Procedure
1. Resolve the active user from the incoming Telegram event/chat context, not from a hard-coded/home Telegram ID. Use `telegram_id` → `users.id`; if no user/profile exists, run `onboard-user` first. Then load that user's profile, preference memory, pantry (with `expires_on`), last week's adherence,
   and (if connected) calendar events for the week — see `life-sync`.
2. Generate the plan with `shared/prompts/planner.txt` (OpenAI), OR query
   Spoonacular with allergen filters. Pass pantry + calendar as JSON inputs.
3. **Defense in depth:** screen EVERY recipe through `safety_verdict()` against
   the profile. Any recipe that isn't SAFE/LIKELY_SAFE is discarded and regenerated.
4. Apply constraints: weekly kcal ±5%; expiring items used first (spoilage routing);
   leftovers chained (big batch day N → remix day N+2); cook time ≤ max; ≤1 repeat/week
   unless the user likes repeats.
5. Write `recipes` + `meal_schedule`. Cache each recipe's gate result in `gate_screen_json`.
6. For each scheduled meal, create a preparation reminder 2–3 hours before the
   meal in the user's timezone. The reminder should name that specific food and
   include concise cooking instructions, ingredients needed, estimated time,
   allergy/safety status, and safe substitutions where useful.
7. Build the shopping list = required − pantry → `shopping_list_items` with store
   sections + estimated cost. Hand off to `shopping-assistant` to send it.
8. Reply: compact 7-day overview + "swap any meal by replying *swap Tuesday dinner*".

## Agentic behaviors to honor
- Spoilage routing, leftover alchemy, seasonal/budget preference, batch-cooking mode.
- Single-meal regeneration: if the user rejects one meal, regenerate only that slot
  and diff the shopping list — message only what changed.

## Files
- `shared/prompts/planner.txt`, `shared/safety_gate.py`, `shared/db.py`, `shared/nutrition.py`
