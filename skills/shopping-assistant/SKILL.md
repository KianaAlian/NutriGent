---
name: shopping-assistant
description: >
  Use to build and manage the weekly grocery list: /shopping, tap "🛒 Shopping",
  "what do I need to buy", or right after weekly-plan generates a plan. Produces
  a pantry-aware list grouped by store section with tappable "got it" buttons,
  estimated cost, and a Saturday reminder. Handles "bought it" / "out of stock".
---

# shopping-assistant

## When to use
- After `weekly-plan` writes `shopping_list_items`.
- `/shopping`, "🛒 Shopping", "what do I need".
- Saturday evening cron — the buy reminder (your "remind me to buy" requirement).

## Procedure
1. Resolve the active user from the Telegram event (`telegram_id`/chat context) and read `shopping_list_items` for that user's current week (`status='pending'`). Never use a hard-coded/home chat ID when multiple pilot users exist.
2. Group by `store_section` (produce / dairy / dry goods / frozen / other).
3. Send one message per section; each item carries
   `telegram_menu.shopping_item_button(item_id, name)`:
   "🛒 Got it" → `status='bought'`; "❌ Unavailable" → `status='unavailable'`
   and trigger `handle-friction` substitution.
4. Footer: estimated total cost; if over budget, offer cheaper swaps (budget mode).
5. Saturday 18:00 cron: if pending items remain, send a reminder with the list.

## Pantry Math
The list already excludes what's in `pantry`. When an item is marked bought,
optionally add it to `pantry` so the next plan accounts for it.

## Files
- `shared/db.py`, `shared/telegram_menu.py`, `shared/telegram_io.py`
