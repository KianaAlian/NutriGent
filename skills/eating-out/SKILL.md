---
name: eating-out
description: >
  Use when the user is at or heading to a restaurant: "eating out", "at a
  restaurant", sends a menu photo, or asks "what can I order here?". Scans the
  menu, screens every dish through the safety gate, and returns a safe-to-order
  shortlist. Also generates the translated allergy card for waiters/travel.
---

# eating-out

## When to use
- A menu photo/screenshot; "what can I order"; "I'm at <restaurant>".
- `/card` or tap "🆘 Allergy card".

## Procedure — menu scan
1. Vision model extracts each dish + described ingredients (extractor.txt → menu_items).
2. Run `safety_verdict()` per dish.
3. Reply: "✅ Safe: <dishes> · ⚠️ Ask the waiter about: <dishes + why> ·
   🛑 Avoid: <dishes + allergen>." Be specific about WHY each is risky.

## Procedure — allergy card (/card)
Generate a short paragraph in the local language (use `users.locale` or ask):
"I have a SEVERE allergy to peanuts and tree nuts. My meal must not contain or
touch them. Cross-contamination can be life-threatening. Thank you." Include the
local emergency number. Offer it as text the user can show staff.

## Rules
- Restaurant dishes are higher-uncertainty than labels → lean toward ⚠️ "ask".
- Never tell an anaphylactic user a restaurant dish is fully ✅ from a menu alone.

## Files
- `shared/safety_gate.py`, `shared/prompts/extractor.txt`, `shared/db.py`
