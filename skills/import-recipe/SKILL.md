---
name: import-recipe
description: >
  Use when the user shares a recipe to adopt: a URL, a screenshot, a TikTok/IG
  caption, or pasted text, with intent like "can I make this?", "make this safe
  for me", "add this to my plan". Extracts the recipe, screens it through the
  safety gate, substitutes unsafe ingredients, rescales to the user's macros,
  and optionally slots it into the week.
---

# import-recipe

## When to use
- A recipe link, image, or pasted text + "safe-ify this" / "add to my plan".

## Procedure
1. Extract the recipe (title, ingredients, steps) from the URL/image/text via the model.
2. Screen with `safety_verdict()`. If UNSAFE, identify the offending ingredients.
3. Propose safe substitutions that preserve the dish:
   egg → aquafaba/flax egg; soy sauce → coconut aminos/tamari-free; milk → oat milk;
   wheat flour → certified GF blend. Re-screen the substituted version.
4. Rescale quantities to the user's per-meal calorie/macro budget; recompute nutrition.
5. Save to `recipes` (`source='import:<url>'`); offer "add to Thursday?" → `meal_schedule`.

## Rules
- Never present a substituted recipe as safe without re-running the gate on the
  final ingredient list.

## Files
- `shared/safety_gate.py`, `shared/nutrition.py`, `shared/db.py`
