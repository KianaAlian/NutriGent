---
name: onboard-user
description: >
  Use on /start, when an unknown telegram_id sends anything, or when a user
  says "set me up" / "create my profile". Interviews the user to build their
  safety + diet profile, computes calorie targets, seeds the pantry, and writes
  the first memory entry. Run this before any other skill if no profile exists.
---

# onboard-user

## When to use
- `/start`, or any message from a telegram_id not in `users`.
- "set me up", "redo my profile".

## Procedure (button-first; one question per message)
1. Treat Telegram `/start` as an internal trigger, but make the user experience
   button-first: users should be able to tap Telegram **Start** and then use
   inline/reply keyboard buttons for choices wherever possible instead of typing
   `/commands`. Typed answers are only for free text/numbers (name, age, weight,
   address, pantry text, etc.).
   - Continue onboarding in the user's language/script once they respond (for
     example, Persian/Farsi users should get Persian onboarding prompts), while
     preserving the same one-question-at-a-time sequence.
   - If a Telegram voice note arrives as an unreliable/garbled transcript, do
     not infer profile fields from it. Briefly say the transcript is unclear and
     ask the same current onboarding question again, preferably inviting a short
     typed answer.
2. Greet as **NutriGent** (the assistant name for all purposes) with this opening
   message, or very close wording, before any profile questions:
   "Hi, I’m NutriGent — your personal diet and allergy assistant.\n\nI can help
   plan your meals, check foods for allergens, build shopping lists, track
   macros, and adapt your plan when life gets busy.\n\nI’m an assistive tool,
   not a medical device — for severe allergies, always double-check labels
   yourself.\n\nFirst, what should I call you?"
3. Ask the user's name first, save it, and address the user by that name in all
   later onboarding messages.
3. Collect, saving as you go, exactly **one question per turn**. Do **not** dump
   multiple onboarding questions in one message, and do **not** compute targets or
   write the final memory/profile card until all profile fields are collected,
   including dislikes and pantry/staples:
   - allergies → **per-allergen severity** (mild / moderate / severe / anaphylactic). If a user says “milk/lactose allergy” or similar, treat it conservatively as dairy avoidance for meal safety, but later clarify whether this is milk-protein allergy vs lactose intolerance when safety decisions depend on labels/cross-contact.
   - intolerances; religious/cultural exclusions (e.g. pork-free/halal); diet type (vegetarian/halal/keto/…); dislikes
   - goal (lose/maintain/gain/energy-health); sex, age, height, weight, activity level
   - cooking skill; max minutes/meal; budget level; reminder times; timezone
     - If a reminder time is ambiguous (e.g. "7:30"), ask AM/PM before saving.
     - If the user gives a city/country instead of an IANA timezone, resolve it to an IANA zone (e.g. Bologna → Europe/Rome) before saving.
   - optional health flags ("low ferritin", "high LDL") — supportive only
   - pantry/staples: photo or typed list
   - If the user sends a voice message and the platform transcript is garbled/low-confidence, do not guess the answer; ask them to resend shorter or type the answer.
   Use Telegram inline buttons/reply keyboards for bounded choices such as
   allergies, allergy severity, goals, activity level, cooking time, budget,
   reminder preferences, and main-menu actions.
3. Compute targets:
   ```python
   from nutrition import daily_target
   t = daily_target(sex, weight, height, age, activity, goal)
   ```
   Show them and let the user override.
4. Write `users` + `dietary_profiles` (allergies/dislikes/health flags as JSON).
5. Seed pantry: ask for a photo of staples or a typed list → `pantry` rows.
6. Register the Telegram command menu once, then send this user the persistent NutriGent reply-keyboard so buttons appear below the chat input:
   ```python
   from telegram_io import set_commands, send_menu
   from telegram_menu import COMMANDS, persistent_main_keyboard
   set_commands(COMMANDS)  # bot-wide slash menu
   send_menu(chat_id, "📋 NutriGent buttons are enabled.", persistent_main_keyboard())
   ```
   Important Telegram distinction: `setMyCommands` / BotFather commands are bot-wide, but reply keyboards are per-chat. Every new user must receive the reply-keyboard at least once during `/start` or `/menu`; sending it to one chat does not make it appear for all users.
7. Seed memory: one distilled line, e.g.
   "Sara: anaphylactic peanut, mild lactose, vegetarian, 1729 kcal, hates mushrooms, ≤30 min weekdays."
8. Confirm with a profile card + "say *plan my week* when ready" + show `main_menu()`.

## Implementation notes for Telegram buttons
- Mirror the user's language during onboarding (e.g. Persian/Farsi if the user starts in Persian) while preserving the one-question-per-turn sequence and safety disclaimer.
- Telegram voice messages may arrive as an automatic transcript rather than directly playable audio. If the transcript is garbled or semantically unclear, do not infer profile fields from it; briefly say it was not understood and ask the same onboarding question again, preferably with a short typed answer option.
- Keep onboarding choices and global NutriGent buttons in `shared/telegram_menu.py` as reusable helpers rather than hard-coding keyboards in handlers. Include a `persistent_main_keyboard()` helper that returns a Telegram `ReplyKeyboardMarkup` with `is_persistent=True`, `resize_keyboard=True`, `one_time_keyboard=False`, and buttons that send command text such as `📋 /menu`, `🔍 /check`, `📊 /today`, `🍽 /plan`, `🛒 /shopping`, `🌙 /tonight`, `✍️ /log`, `😴 /tired`, `📑 /report`, `🆘 /card`, and `⚙️ /profile`. Recommended helper shape:
  - `onboarding_severity_menu(allergen=None)` → mild / moderate / severe / anaphylactic
  - `onboarding_diet_menu()` → none / vegetarian / vegan / halal / keto / paleo / gluten-free / other
  - `onboarding_goal_menu()` → lose / maintain / gain / energy-health
  - `onboarding_activity_menu()` → sedentary / light / moderate / active / athlete
  - `onboarding_cooking_skill_menu()` → beginner / intermediate / confident
  - `onboarding_cook_time_menu()` → 15 / 30 / 45 / 60+ min
  - `onboarding_budget_menu()` → tight / normal / flexible
  - `onboarding_skip_menu(field)` for optional fields such as health flags
  - `onboarding_pantry_menu()` → send photo / type staples / skip
- Use `callback_data` with a stable `onboard:<field>:<value>` prefix so the router can dispatch all onboarding taps consistently.
- Add a small dependency-light test for the keyboard labels and callbacks (stdlib `unittest` is fine) so button regressions do not require the full visual/reporting stack.
- `/start` should greet as NutriGent and ask the name first; do not compress onboarding into a single “tell me allergies, diet, goal” prompt.
- If the user sends a Telegram voice message during onboarding, only rely on the platform-provided transcript. When the transcript is garbled or semantically unclear, do **not** guess the profile field; briefly say the voice transcription was unclear and ask the user to resend a shorter voice note or type the answer.

## Files
- `shared/nutrition.py`, `shared/db.py`, `shared/telegram_menu.py`, `shared/telegram_io.py`
