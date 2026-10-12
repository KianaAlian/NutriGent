---
name: food-safety-check
description: >
  Use whenever a user wants to know if a food is safe for their allergies/diet.
  Triggers: any incoming photo of food, an ingredient label, a barcode, or a
  menu; the /check command; or text like "can I eat X?", "is this safe?",
  "does this have nuts?". This is the SAFETY-CRITICAL skill. The LLM only
  EXTRACTS ingredients; the deterministic safety_gate.py issues the verdict.
  Never declare a food safe without running the gate.
---

# food-safety-check

## When to use
- Any image arrives (photo, label, barcode, menu screenshot).
- `/check` command or a tap on "🔍 Check a food".
- Free text asking whether something is edible for the user.

## Golden rule
**The LLM proposes, the code disposes.** Your job (the model) is to read the
image/text and list ingredients HONESTLY, including uncertainty. The final
verdict comes only from `shared/safety_gate.py`. You never override it, never
soften a 🛑/❓, never invent ingredients to look complete.

## Procedure
1. Resolve the user: `db.user_by_telegram(telegram_id)` → `db.get_profile(uid)`.
   If no profile, run the `onboard-user` skill first.
2. Decide the input path:
   - **Barcode visible** → decode locally (`pyzbar`) → look up Open Food Facts
     `https://world.openfoodfacts.org/api/v2/product/{barcode}.json` → build an
     `extraction` dict from its `ingredients_text` + `traces` fields, set
     `image_type="ingredient_label"`, `readability=1.0`. Prefer this path: it is
     free and exact.
   - **Photo / menu** → send the image to the OpenAI vision model with
     `shared/prompts/extractor.txt`. Parse the strict JSON it returns.
   - **Text only** ("can I eat tiramisu?") → ask the model to decompose the dish
     into typical + likely-hidden ingredients in the same JSON shape;
     set `image_type="prepared_food"`.
3. Call the gate:
   ```python
   from safety_gate import safety_verdict
   verdict = safety_verdict(extraction, profile)
   ```
4. Reply with `verdict.message()` verbatim as the first lines. You may add ONE
   friendly follow-up line (e.g. "Want me to log it? ~310 kcal").
5. Log it: insert into `food_log` (source, item, verdict, flagged_json, kcal).
6. For a `menu` image, run the gate per dish and reply: "✅ safe: 2, 5, 9 ·
   ⚠️ ask about: 3 · 🛑 avoid: 4 (cream), 7 (peanut sauce)."

## Verdict meanings (from the gate)
- 🛑 UNSAFE — a declared allergen (or, at anaphylactic/severe level, a trace) was found.
- ⚠️ CAUTION — "may contain" / likely-hidden allergen at non-severe level, or a
  cooked dish whose hidden contents a photo can't prove.
- ✅ SAFE / LIKELY_SAFE — nothing from the profile detected.
- ❓ UNVERIFIED — fail-closed: unreadable, cropped, or not food. Treat as NOT safe.

## Hard safety rules
- A photo of a COOKED dish can never earn a full ✅ for an anaphylactic user — max ⚠️.
- Readability below 0.85 on a label → ❓, always.
- If the user reports reaction symptoms, tell them to use emergency medication
  and call emergency services immediately. You are not a doctor.

## Files
- `shared/safety_gate.py` — the gate (don't modify the policy casually).
- `shared/prompts/extractor.txt` — the vision system prompt.
- `shared/db.py` — `get_profile`, `user_by_telegram`.

## Tests
`tests/test_safety_gate.py` must stay green (12/12), including false-positive
guards (coconut milk ≠ dairy) and Worcestershire → anchovy → fish.
