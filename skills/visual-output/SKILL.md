---
name: visual-output
description: >
  Cross-cutting convention: this assistant answers with VISUALS, not walls of
  text. Whenever a reply has structure — a safety verdict, today's calories, a
  meal plan, a shopping list, a profile, a weekly/monthly trend — render it as
  an image card with shared/visuals.py or a chart with shared/charts.py and send
  it via Telegram sendPhoto, with a short text caption. Use for any "show me",
  "how am I doing", verdict, plan, or summary response.
---

# visual-output

## Principle
A picture in the chat beats a paragraph. Every structured answer ships as an
image + a one-line caption. Plain text is only for short conversational replies,
questions, and the fail-safe disclaimer line.

## What renders as what
| Situation | Function | Returns |
|---|---|---|
| Safety verdict (any check) | `visuals.verdict_card(level,item,reasons)` | colored DO NOT EAT / SAFE / … card |
| Today's calories & macros | `visuals.day_dashboard(consumed,target)` | kcal ring + macro bars |
| The week's meals | `visuals.meal_plan_card(days)` | 7-day visual list |
| Shopping list | `visuals.shopping_card(sections)` | grouped, by store section |
| Profile summary | `visuals.profile_card(p)` | allergies (severity dots) + targets |
| Weekly calories | `reporting.week_chart(uid)` | bar chart |
| Monthly trend | `reporting.month_chart(uid)` | line + weight |
| Safety mix (report) | `reporting.week_safety_donut(uid)` | donut |

## Rules for images
- No emoji INSIDE images (they don't render). Use color blocks + ✓ ✗ ⚠ ● glyphs.
- Every number rounded before it's drawn.
- Color meaning is consistent everywhere: green = on target / safe, amber = under
  / caution, red = over / unsafe, gray = neutral / unverified, purple = brand/target.
- Files write to `$DIET_CHART_DIR`, named by user id to avoid collisions.
- Always send a short text caption with the photo.

## Telegram button convention
- Do not rely only on BotFather / `setMyCommands` for NutriGent usability. The user wants persistent tap buttons like a command grid, visible under the Telegram input for every user.
- Bot-wide slash commands and per-chat reply keyboards are different: `setMyCommands` affects the `/` menu for all bot users; `ReplyKeyboardMarkup` must be sent to each chat at least once (usually on `/start` and `/menu`).
- Whenever sending `/menu`, onboarding completion, or a “buttons enabled” message, attach the persistent reply keyboard from `telegram_menu.persistent_main_keyboard()` in addition to any inline menu card. Inline keyboards are good for in-message actions; persistent reply keyboards are best for common commands.

## Send pattern
```python
from telegram_io import send_photo
send_photo(chat_id, visuals.verdict_card(v.level, item, reasons), caption=v.message())
```

## Fallback when app renderers are unavailable
If `shared/visuals.py`, `shared/charts.py`, or the app DB is not accessible in the current Hermes session, still honor the visual-output convention: render a simple static PNG card/chart with PIL or matplotlib under `/tmp` (or `$DIET_CHART_DIR` if known), verify the file exists, and deliver it with `MEDIA:/absolute/path.png`. Keep the caption short and clearly label estimates. This is preferable to falling back to a wall of text for `/card`, `/today`, `/week`, `/month`, `/plan`, or `/shopping`.

## Files
- `shared/visuals.py` — the six card renderers.
- `shared/charts.py` — the four data charts.
- `shared/reporting.py` — DB → chart bridge.
- `references/telegram-buttons.md` — durable notes on bot-wide commands vs per-chat persistent reply keyboards for all users.
